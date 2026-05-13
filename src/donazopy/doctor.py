# this_file: src/donazopy/doctor.py
"""DNS zone diagnostics and (optional) automated remediation.

The ``donazopy doctor`` command analyzes a TARGET (provider-qualified domain or
local BIND zone file), reports issues, and with ``--fix`` applies safe
auto-fixes. It operates on the existing :class:`NormalizedRecord` model so
the same engine works for live provider zones and local files.

The engine is intentionally static-first: every check operates on the parsed
record list without network calls. The only optional live signal is the
current provider's nameservers (read via the registrar protocol) which the
NS-migration check uses when available.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from donazopy.zonefile import (
    NormalizedRecord,
    build_bind_zone,
    records_from_zone_file,
    records_from_zone_text,
    serialize_records,
    write_text_safely,
)

Severity = Literal["error", "warning", "info"]


# Pattern fragments that identify a provider's authoritative nameservers.
# Used by the migration-NS check to flag apex NS records pointing at a
# provider different from the one currently hosting the zone.
PROVIDER_NS_PATTERNS: dict[str, tuple[str, ...]] = {
    "cloudflare": ("ns.cloudflare.com",),
    "ionos": ("ui-dns.de", "ui-dns.com", "ui-dns.org", "ui-dns.biz"),
    "godaddy": ("domaincontrol.com",),
    "aws": ("awsdns-",),
    "google": ("googledomains.com", "google.com"),
    "azure": ("azure-dns.com", "azure-dns.net", "azure-dns.org", "azure-dns.info"),
    "namecheap": ("registrar-servers.com",),
    "joker": ("joker.com",),
    "dnsimple": ("dnsimple.com",),
    "gandi": ("gandi.net",),
    "porkbun": ("porkbun.com",),
    "vercel": ("vercel-dns.com",),
    "digitalocean": ("digitalocean.com",),
    "hetzner": ("hetzner.com", "your-server.de"),
    "linode": ("linode.com",),
    "vultr": ("vultr.com",),
}


@dataclass(frozen=True)
class Issue:
    """A single problem discovered by a doctor check."""

    code: str
    severity: Severity
    category: str
    message: str
    details: str
    affected: tuple[str, ...]
    fixable: bool
    fix_description: str = ""
    suggested_record: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "affected": list(self.affected),
            "fixable": self.fixable,
            "fix_description": self.fix_description,
            "suggested_record": self.suggested_record,
        }


@dataclass
class DoctorReport:
    """Aggregated findings + optional fix-plan / fix-results."""

    target: str
    domain: str | None
    provider_key: str | None
    issues: list[Issue] = field(default_factory=list)
    fixed: list[Issue] = field(default_factory=list)
    backup_path: str | None = None

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "info")

    @property
    def fixable_count(self) -> int:
        return sum(1 for issue in self.issues if issue.fixable)

    def summary(self) -> str:
        return (
            f"errors={self.error_count} warnings={self.warning_count} "
            f"info={self.info_count} fixable={self.fixable_count} fixed={len(self.fixed)}"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "domain": self.domain,
            "provider_key": self.provider_key,
            "summary": self.summary(),
            "counts": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
                "fixable": self.fixable_count,
                "fixed": len(self.fixed),
            },
            "issues": [issue.to_dict() for issue in self.issues],
            "fixed": [issue.to_dict() for issue in self.fixed],
            "backup_path": self.backup_path,
        }

    def format_text(self) -> str:
        lines = [f"DNS Doctor Report: {self.target}", "=" * 40, self.summary(), ""]
        if not self.issues:
            lines.append("No issues found.")
        for issue in self.issues:
            tag = {"error": "[ERROR]", "warning": "[WARNING]", "info": "[INFO]"}[issue.severity]
            fix_tag = " (fixable)" if issue.fixable else ""
            lines.append(f"{tag} {issue.code}: {issue.message}{fix_tag}")
            if issue.details:
                lines.append(f"  {issue.details}")
            for affected in issue.affected:
                lines.append(f"    - {affected}")
            if issue.suggested_record:
                lines.append(f"  Suggested: {issue.suggested_record}")
            lines.append("")
        if self.fixed:
            lines.append("Applied fixes:")
            for issue in self.fixed:
                lines.append(f"  - {issue.code}: {issue.fix_description}")
        if self.backup_path:
            lines.append(f"Backup: {self.backup_path}")
        return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Record helpers
# ---------------------------------------------------------------------------


_TXT_QUOTE_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _txt_payload(value: str) -> str:
    """Return the semantic concatenated character-string payload of a TXT value.

    DNS TXT rdata is one or more quoted character-strings; the semantic
    payload is the concatenation of those strings. This collapses both
    presentation variants in the example given by the user:

    - ``"v=spf1 include:_spf-us.ionos.com ~all"``
    - ``"\"v=spf1 include:_spf-us.ionos.com ~all\""`` (escaped/double-quoted)
    """
    text = value.strip()
    matches = _TXT_QUOTE_RE.findall(text)
    payload = "".join(match.replace('\\"', '"').replace("\\\\", "\\") for match in matches) if matches else text
    # If after one unquote pass we still see literal escaped quotes wrapping
    # the whole payload, unwrap once more.
    if payload.startswith('"') and payload.endswith('"') and len(payload) >= 2:
        inner = payload[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        # Only collapse if the inner string looks like a complete value.
        if inner:
            payload = inner
    return " ".join(payload.split())


def _short_owner(owner: str, domain: str | None) -> str:
    name = owner.rstrip(".")
    if domain and name == domain.rstrip("."):
        return "@"
    if domain and name.endswith("." + domain.rstrip(".")):
        return name[: -(len(domain.rstrip(".")) + 1)]
    return owner


def _which_provider_owns_ns(hostname: str) -> str | None:
    host = hostname.rstrip(".").lower()
    for key, patterns in PROVIDER_NS_PATTERNS.items():
        if any(pattern in host for pattern in patterns):
            return key
    return None


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckContext:
    records: tuple[NormalizedRecord, ...]
    domain: str | None
    provider_key: str | None
    origin: str  # absolute origin with trailing dot, e.g. ``example.com.``


def check_migration_ns(ctx: CheckContext) -> list[Issue]:
    """Flag apex NS records pointing to a provider different from the host."""
    if ctx.provider_key is None:
        return []
    apex_ns = [r for r in ctx.records if r.owner == ctx.origin and r.record_type == "NS"]
    foreign: list[tuple[NormalizedRecord, str]] = []
    for record in apex_ns:
        owner_provider = _which_provider_owns_ns(record.value)
        if owner_provider is not None and owner_provider != ctx.provider_key:
            foreign.append((record, owner_provider))
    if not foreign:
        return []
    affected = tuple(f"{r.owner} {r.ttl} IN NS {r.value} (owned by {owner})" for r, owner in foreign)
    return [
        Issue(
            code="NS_MIGRATION_ARTIFACT",
            severity="error",
            category="ns",
            message=(
                f"{len(foreign)} apex NS record(s) point to a different provider than "
                f"{ctx.provider_key!r}"
            ),
            details=(
                "These NS records likely remain from a previous provider after a zone "
                "copy. Resolvers ignore apex NS in some providers but they can also "
                "confuse delegation checks and downstream tooling. Removing them is "
                "safe when the registrar's delegation already points at the current "
                "provider."
            ),
            affected=affected,
            fixable=True,
            fix_description=f"Remove {len(foreign)} foreign NS record(s) from the zone apex.",
        )
    ]


def check_txt_semantic_duplicates(ctx: CheckContext) -> list[Issue]:
    """Detect TXT records that are semantically identical after unquoting."""
    by_owner: dict[str, list[NormalizedRecord]] = {}
    for record in ctx.records:
        if record.record_type == "TXT":
            by_owner.setdefault(record.owner, []).append(record)

    issues: list[Issue] = []
    for owner, recs in by_owner.items():
        groups: dict[str, list[NormalizedRecord]] = {}
        for record in recs:
            groups.setdefault(_txt_payload(record.value), []).append(record)
        for payload, group in groups.items():
            if len(group) <= 1:
                continue
            affected = tuple(f"{r.owner} {r.ttl} IN TXT {r.value}" for r in group)
            issues.append(
                Issue(
                    code="TXT_SEMANTIC_DUPLICATE",
                    severity="error",
                    category="txt",
                    message=(
                        f"{len(group)} TXT records at {_short_owner(owner, ctx.domain)} share the "
                        "same payload after unquoting"
                    ),
                    details=(
                        f"Semantic payload: {payload!r}. Duplicate TXT entries typically come from "
                        "import/export quoting mismatches (literal escaped quotes vs. canonical "
                        "form). Keeping only the canonical record removes ambiguity."
                    ),
                    affected=affected,
                    fixable=True,
                    fix_description="Keep one canonical TXT and drop the duplicates.",
                )
            )
    return issues


def check_multiple_spf(ctx: CheckContext) -> list[Issue]:
    by_owner: dict[str, list[NormalizedRecord]] = {}
    for record in ctx.records:
        if record.record_type != "TXT":
            continue
        if "v=spf1" in _txt_payload(record.value).lower():
            by_owner.setdefault(record.owner, []).append(record)
    issues: list[Issue] = []
    for owner, recs in by_owner.items():
        # Only flag truly distinct SPF entries (semantic dedupe is handled above).
        unique = {_txt_payload(r.value) for r in recs}
        if len(unique) > 1:
            affected = tuple(f"{r.owner} {r.ttl} IN TXT {r.value}" for r in recs)
            issues.append(
                Issue(
                    code="SPF_MULTIPLE",
                    severity="error",
                    category="email",
                    message=f"Multiple distinct SPF records found at {_short_owner(owner, ctx.domain)}",
                    details=(
                        "RFC 7208 forbids more than one SPF record at the same owner; receivers "
                        "must treat the result as PermError. Merge the includes/mechanisms into a "
                        "single record."
                    ),
                    affected=affected,
                    fixable=False,
                    fix_description="Manual: merge includes into a single 'v=spf1 ...' record.",
                )
            )
    return issues


def _has_mx(records: Iterable[NormalizedRecord]) -> bool:
    return any(r.record_type == "MX" for r in records)


def _has_spf(records: Iterable[NormalizedRecord]) -> bool:
    return any(r.record_type == "TXT" and "v=spf1" in _txt_payload(r.value).lower() for r in records)


def _has_dmarc(records: Iterable[NormalizedRecord], origin: str) -> bool:
    dmarc_owner = f"_dmarc.{origin.lstrip('.')}"
    return any(
        r.record_type == "TXT" and r.owner.lower() == dmarc_owner.lower() for r in records
    )


def check_missing_spf(ctx: CheckContext) -> list[Issue]:
    if not _has_mx(ctx.records) or _has_spf(ctx.records):
        return []
    return [
        Issue(
            code="SPF_MISSING",
            severity="warning",
            category="email",
            message="No SPF record found despite MX records being present",
            details=(
                "Without an SPF record, receivers cannot validate which servers may send "
                "email for this domain. Add a TXT record at the apex listing authorized "
                "senders."
            ),
            affected=(ctx.origin,),
            fixable=False,
            fix_description="Manual: add a TXT record with 'v=spf1 include:... ~all'.",
            suggested_record=f'{ctx.origin} 3600 IN TXT "v=spf1 include:_spf.your-provider.com ~all"',
        )
    ]


def check_missing_dmarc(ctx: CheckContext) -> list[Issue]:
    if not _has_mx(ctx.records) or _has_dmarc(ctx.records, ctx.origin):
        return []
    suggested = f'_dmarc.{ctx.origin} 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@{ctx.origin.rstrip(".")}"'
    return [
        Issue(
            code="DMARC_MISSING",
            severity="warning",
            category="email",
            message="No DMARC record at _dmarc despite MX records being present",
            details=(
                "DMARC tells receivers what to do with messages that fail SPF/DKIM. "
                "Starting with a monitoring-only policy (p=none) is safe and produces "
                "actionable reports."
            ),
            affected=(f"_dmarc.{ctx.origin}",),
            fixable=True,
            fix_description="Add a TXT record at _dmarc with a monitoring-only DMARC policy.",
            suggested_record=suggested,
        )
    ]


def check_missing_caa(ctx: CheckContext) -> list[Issue]:
    if any(r.record_type == "CAA" and r.owner == ctx.origin for r in ctx.records):
        return []
    return [
        Issue(
            code="CAA_MISSING",
            severity="info",
            category="security",
            message="No CAA records at the zone apex",
            details=(
                "CAA records restrict which Certificate Authorities may issue "
                "certificates for the domain, mitigating mis-issuance attacks."
            ),
            affected=(ctx.origin,),
            fixable=False,
            fix_description="Manual: publish CAA records at the apex.",
            suggested_record=f'{ctx.origin} 3600 IN CAA 0 issue "letsencrypt.org"',
        )
    ]


def check_cname_conflicts(ctx: CheckContext) -> list[Issue]:
    by_owner: dict[str, list[NormalizedRecord]] = {}
    for record in ctx.records:
        by_owner.setdefault(record.owner, []).append(record)
    issues: list[Issue] = []
    for owner, recs in by_owner.items():
        types = {r.record_type for r in recs}
        if "CNAME" in types and types - {"CNAME", "RRSIG", "NSEC"}:
            affected = tuple(f"{r.owner} {r.ttl} IN {r.record_type} {r.value}" for r in recs)
            issues.append(
                Issue(
                    code="CNAME_COLLISION",
                    severity="error",
                    category="structure",
                    message=f"CNAME at {_short_owner(owner, ctx.domain)} coexists with other record types",
                    details=(
                        "RFC 1912 §2.4: a CNAME may not exist at the same owner name as any "
                        "other record. Remove either the CNAME or the conflicting records."
                    ),
                    affected=affected,
                    fixable=False,
                    fix_description="Manual: remove the CNAME or the conflicting records.",
                )
            )
        if "CNAME" in types and owner == ctx.origin:
            cname_records = tuple(
                f"{r.owner} {r.ttl} IN CNAME {r.value}" for r in recs if r.record_type == "CNAME"
            )
            issues.append(
                Issue(
                    code="CNAME_AT_APEX",
                    severity="error",
                    category="structure",
                    message="CNAME present at the zone apex",
                    details=(
                        "RFC 1034/1912: the apex must contain SOA and NS records, so a CNAME "
                        "there is invalid. Use an A/AAAA record (or an ALIAS/ANAME if the "
                        "provider supports flattening)."
                    ),
                    affected=cname_records,
                    fixable=False,
                    fix_description="Manual: replace apex CNAME with A/AAAA or provider ALIAS.",
                )
            )
    return issues


DEFAULT_CHECKS = (
    check_migration_ns,
    check_txt_semantic_duplicates,
    check_multiple_spf,
    check_missing_spf,
    check_missing_dmarc,
    check_missing_caa,
    check_cname_conflicts,
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def analyze_records(
    records: tuple[NormalizedRecord, ...],
    *,
    domain: str | None,
    provider_key: str | None,
    origin: str | None = None,
    checks: Iterable = DEFAULT_CHECKS,
) -> list[Issue]:
    """Run every check against ``records`` and return the aggregated issues."""
    if origin is None:
        if domain is None:
            msg = "analyze_records requires either origin or domain"
            raise ValueError(msg)
        origin = domain.rstrip(".") + "."
    if not origin.endswith("."):
        origin = origin + "."
    ctx = CheckContext(records=records, domain=domain, provider_key=provider_key, origin=origin)
    issues: list[Issue] = []
    for check in checks:
        issues.extend(check(ctx))
    return issues


def plan_fix_records(
    records: tuple[NormalizedRecord, ...],
    issues: Iterable[Issue],
    *,
    origin: str,
) -> tuple[tuple[NormalizedRecord, ...], list[Issue]]:
    """Apply auto-fixable issues to ``records`` and return (new_records, fixed_issues).

    The returned record tuple is what the zone should contain after the
    fixes; callers persist it (via provider import or local zone write).
    """
    fixed: list[Issue] = []
    keep = list(records)
    for issue in issues:
        if not issue.fixable:
            continue
        if issue.code == "NS_MIGRATION_ARTIFACT":
            # Each affected line has the form "owner ttl IN NS value (owned by ...)".
            to_drop: set[tuple[str, int, str, str, str]] = set()
            for entry in issue.affected:
                parts = entry.split(" ")
                if len(parts) < 5:
                    continue
                owner, ttl, _in, rtype, value = parts[0], parts[1], parts[2], parts[3], parts[4]
                to_drop.add((owner, int(ttl), _in, rtype, value))
            keep = [r for r in keep if r.exact_key not in to_drop]
            fixed.append(issue)
        elif issue.code == "TXT_SEMANTIC_DUPLICATE":
            # Group by owner+payload, keep the canonical (shortest unquoted) version.
            owners_payloads: dict[tuple[str, str], list[NormalizedRecord]] = {}
            for record in keep:
                if record.record_type != "TXT":
                    continue
                owners_payloads.setdefault((record.owner, _txt_payload(record.value)), []).append(record)
            survivors: set[tuple] = set()
            drop: set[tuple] = set()
            for group in owners_payloads.values():
                if len(group) <= 1:
                    continue
                canonical = min(group, key=lambda r: (len(r.value), r.value))
                survivors.add(canonical.exact_key)
                for record in group:
                    if record.exact_key != canonical.exact_key:
                        drop.add(record.exact_key)
            keep = [r for r in keep if r.exact_key not in drop]
            fixed.append(issue)
        elif issue.code == "DMARC_MISSING":
            # Synthesize a monitoring-only DMARC TXT record.
            owner = f"_dmarc.{origin}"
            value = f'"v=DMARC1; p=none; rua=mailto:dmarc@{origin.rstrip(".")}"'
            new = NormalizedRecord(
                owner=owner,
                ttl=3600,
                record_class="IN",
                record_type="TXT",
                value=value,
                source_order=len(keep),
            )
            keep.append(new)
            fixed.append(issue)
    return tuple(sorted(keep)), fixed


# ---------------------------------------------------------------------------
# Top-level entry points
# ---------------------------------------------------------------------------


def analyze_zone_file(path: Path, *, origin: str | None = None) -> DoctorReport:
    """Analyze a local zone file and return a :class:`DoctorReport`."""
    records = records_from_zone_file(path, origin)
    effective_origin = (origin or path.stem).rstrip(".") + "."
    domain = effective_origin.rstrip(".") or None
    issues = analyze_records(records, domain=domain, provider_key=None, origin=effective_origin)
    return DoctorReport(target=str(path), domain=domain, provider_key=None, issues=issues)


def fix_zone_file(
    path: Path,
    *,
    origin: str | None = None,
    overwrite: bool = False,
) -> DoctorReport:
    """Analyze a zone file, apply auto-fixes, write a backup + cleaned output."""
    records = records_from_zone_file(path, origin)
    effective_origin = (origin or path.stem).rstrip(".") + "."
    domain = effective_origin.rstrip(".") or None
    issues = analyze_records(records, domain=domain, provider_key=None, origin=effective_origin)
    new_records, fixed = plan_fix_records(records, issues, origin=effective_origin)
    backup_path = _write_backup(path, serialize_records(records))
    write_text_safely(path, serialize_records(new_records), overwrite=overwrite or True)
    return DoctorReport(
        target=str(path),
        domain=domain,
        provider_key=None,
        issues=issues,
        fixed=fixed,
        backup_path=str(backup_path),
    )


def analyze_provider_records(
    provider_records: list[Mapping[str, object]],
    *,
    domain: str,
    provider_key: str,
) -> DoctorReport:
    """Analyze provider records (the dict shape returned by ``list_records``)."""
    origin = domain.rstrip(".") + "."
    zone_text = build_bind_zone(origin, provider_records)
    records = records_from_zone_text(zone_text, origin)
    issues = analyze_records(records, domain=domain, provider_key=provider_key, origin=origin)
    return DoctorReport(
        target=f"{provider_key}/{domain}",
        domain=domain,
        provider_key=provider_key,
        issues=issues,
    )


def fix_provider_zone(
    provider,
    *,
    domain: str,
    provider_key: str,
    backup_dir: Path | None = None,
) -> DoctorReport:
    """Analyze a provider zone, then export/clean/delete-all/import to apply fixes.

    The provider must satisfy the standard DNS protocol methods
    (``export_zone``, ``import_zone``, ``delete_all_records``).
    """
    origin = domain.rstrip(".") + "."
    zone_text = provider.export_zone(domain)
    records = records_from_zone_text(zone_text, origin)
    issues = analyze_records(records, domain=domain, provider_key=provider_key, origin=origin)
    new_records, fixed = plan_fix_records(records, issues, origin=origin)
    backup_path = _write_backup(
        (backup_dir or Path("artifacts")) / f"doctor-{domain}-{_timestamp()}.zone",
        zone_text,
        create_parents=True,
    )
    if fixed:
        cleaned_text = serialize_records(new_records)
        # Replace the live zone with the cleaned record set.
        provider.delete_all_records(domain)
        provider.import_zone(domain, cleaned_text)
    return DoctorReport(
        target=f"{provider_key}/{domain}",
        domain=domain,
        provider_key=provider_key,
        issues=issues,
        fixed=fixed,
        backup_path=str(backup_path),
    )


def _timestamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S")


def _write_backup(path: Path, text: str, *, create_parents: bool = False) -> Path:
    if create_parents:
        path.parent.mkdir(parents=True, exist_ok=True)
    base = path.parent / f"{path.stem}.bak{path.suffix or '.zone'}"
    index = 0
    candidate = base
    while candidate.exists():
        index += 1
        candidate = path.parent / f"{path.stem}.bak{index}{path.suffix or '.zone'}"
    candidate.write_text(text, encoding="utf-8")
    return candidate


__all__ = [
    "DEFAULT_CHECKS",
    "CheckContext",
    "DoctorReport",
    "Issue",
    "PROVIDER_NS_PATTERNS",
    "Severity",
    "analyze_provider_records",
    "analyze_records",
    "analyze_zone_file",
    "fix_provider_zone",
    "fix_zone_file",
    "plan_fix_records",
]
