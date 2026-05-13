# this_file: src/donazopy/zonefile.py
"""Zone-file parsing, validation, normalization, and diff helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import dns.exception
import dns.name
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.zone

ZoneChangeKind = Literal["create", "update", "delete", "unchanged"]


class ZoneFileError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class NormalizedRecord:
    """Canonical representation of one DNS record from a zone file."""

    owner: str
    ttl: int
    record_class: str
    record_type: str
    value: str
    source_order: int

    @property
    def identity(self) -> tuple[str, str, str]:
        """Return the identity used to detect record updates."""
        return (self.owner, self.record_class, self.record_type)

    @property
    def exact_key(self) -> tuple[str, int, str, str, str]:
        """Return the full key used to detect unchanged records."""
        return (self.owner, self.ttl, self.record_class, self.record_type, self.value)

    def to_zone_line(self) -> str:
        """Serialize the normalized record to a stable BIND-style line."""
        return f"{self.owner} {self.ttl} {self.record_class} {self.record_type} {self.value}"

    def to_dict(self) -> dict[str, str | int]:
        """Return a JSON-serializable mapping."""
        return asdict(self)


@dataclass(frozen=True)
class ZoneChange:
    """One diff entry between two normalized zones."""

    kind: ZoneChangeKind
    before: NormalizedRecord | None
    after: NormalizedRecord | None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable mapping."""
        return {
            "kind": self.kind,
            "before": None if self.before is None else self.before.to_dict(),
            "after": None if self.after is None else self.after.to_dict(),
        }


@dataclass(frozen=True)
class ZoneDiff:
    """A complete create/update/delete/unchanged plan for two zones."""

    creates: tuple[ZoneChange, ...]
    updates: tuple[ZoneChange, ...]
    deletes: tuple[ZoneChange, ...]
    unchanged: tuple[ZoneChange, ...]

    def to_dict(self) -> dict[str, list[dict[str, object]]]:
        """Return a JSON-serializable diff grouped by change kind."""
        return {
            "creates": [change.to_dict() for change in self.creates],
            "updates": [change.to_dict() for change in self.updates],
            "deletes": [change.to_dict() for change in self.deletes],
            "unchanged": [change.to_dict() for change in self.unchanged],
        }

    def summary(self) -> str:
        """Return a compact human-readable summary."""
        return (
            f"creates={len(self.creates)} updates={len(self.updates)} "
            f"deletes={len(self.deletes)} unchanged={len(self.unchanged)}"
        )


def parse_zone_text(text: str, origin: str, *, relativize: bool = False) -> dns.zone.Zone:
    """Parse BIND zone text using dnspython with explicit origin handling."""
    if not text.strip():
        msg = "zone text is empty"
        raise ZoneFileError(msg)
    try:
        zone = dns.zone.from_text(text, origin=origin, relativize=relativize, check_origin=True)
    except dns.exception.DNSException as exc:
        msg = f"invalid zone for {origin}: {exc}"
        raise ZoneFileError(msg) from exc
    return zone


def parse_zone_file(path: Path, origin: str | None = None, *, relativize: bool = False) -> dns.zone.Zone:
    """Parse a BIND zone file from disk."""
    if not path.exists():
        msg = f"zone file does not exist: {path}"
        raise ZoneFileError(msg)
    inferred_origin = origin or path.stem
    return parse_zone_text(path.read_text(encoding="utf-8"), inferred_origin, relativize=relativize)


def zone_to_text(zone: dns.zone.Zone) -> str:
    """Serialize a parsed zone back to BIND-compatible text."""
    return zone.to_text(relativize=False)


_RDATA_NEEDS_FQDN = {"CNAME", "NS", "PTR", "DNAME"}
_DEFAULT_SYNTHETIC_NS = "ns.invalid."


def _absolute_owner(name: str, origin_abs: str) -> str:
    """Return an absolute owner name with a trailing dot for a provider record name."""
    name = (name or "").strip()
    bare_origin = origin_abs.rstrip(".")
    if not name or name == "@":
        return origin_abs
    if name.endswith("."):
        return name
    if name == bare_origin or name.endswith("." + bare_origin):
        return name + "."
    return f"{name}.{origin_abs}"


def _ensure_dot(value: str) -> str:
    value = value.strip()
    return value if not value or value.endswith(".") else value + "."


def _normalize_soa_content(content: str) -> str:
    parts = content.split()
    if len(parts) < 7:
        return content
    return " ".join([_ensure_dot(parts[0]), _ensure_dot(parts[1]), *parts[2:7]])


def _coerce_int(value: object, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _rdata_for_bind(rtype: str, content: str, prio: object) -> str:
    content = content.strip()
    if rtype in {"MX", "SRV"}:
        head = content.split(" ", 1)[0]
        if prio is not None and not head.isdigit():
            content = f"{_coerce_int(prio, 0)} {content}"
    if rtype == "TXT" and not content.startswith('"'):
        return '"' + content.replace('"', '\\"') + '"'
    if rtype in _RDATA_NEEDS_FQDN:
        return _ensure_dot(content)
    if rtype == "MX":
        head, _, rest = content.partition(" ")
        if head.isdigit() and rest:
            return f"{head} {_ensure_dot(rest)}"
        return _ensure_dot(content)
    return content


def records_from_provider_dicts(
    provider_records: Iterable[Mapping[str, object]],
    *,
    origin: str,
    default_ttl: int = 3600,
) -> tuple[NormalizedRecord, ...]:
    """Convert provider record mappings to NormalizedRecord tuples without dnspython.

    Unlike :func:`build_bind_zone` + :func:`parse_zone_text`, this never raises
    on misconfigurations such as a CNAME coexisting with another type at the
    same owner — those situations are exactly what diagnostic tooling needs to
    inspect. SOA records whose ``content`` lacks the full 7-field rdata are
    skipped (they are an artifact of providers that expose only the primary
    nameserver), matching the behavior of :func:`build_bind_zone`.
    """
    origin_abs = origin if origin.endswith(".") else f"{origin}."
    records: list[NormalizedRecord] = []
    for index, record in enumerate(provider_records):
        if record.get("disabled"):
            continue
        rtype = str(record.get("type") or "").strip().upper()
        if not rtype:
            continue
        owner = _absolute_owner(str(record.get("name") or "@"), origin_abs)
        ttl = _coerce_int(record.get("ttl"), default_ttl)
        raw_content = str(record.get("content") or record.get("value") or "").strip()
        prio = record.get("prio")
        if prio is None:
            prio = record.get("priority")
        if rtype == "SOA":
            if len(raw_content.split()) < 7:
                continue
            value = _normalize_soa_content(raw_content)
        else:
            value = _rdata_for_bind(rtype, raw_content, prio)
        records.append(
            NormalizedRecord(
                owner=owner,
                ttl=ttl,
                record_class="IN",
                record_type=rtype,
                value=value,
                source_order=index,
            )
        )
    return tuple(sorted(records, key=lambda r: (r.owner, r.record_type, r.value, r.ttl)))


def build_bind_zone(
    origin: str,
    records: Iterable[Mapping[str, object]],
    *,
    default_ttl: int = 3600,
    synthetic_nameserver: str = _DEFAULT_SYNTHETIC_NS,
) -> str:
    """Build BIND-compatible zone text from provider record mappings.

    Each mapping should provide ``type`` and ``content`` (rdata text), plus optionally
    ``name`` (FQDN, relative label, or ``"@"`` for the apex; defaults to the apex),
    ``ttl``, ``prio`` (folded into the rdata for ``MX``/``SRV`` when ``content`` does
    not already begin with the priority), and ``disabled`` (records are skipped when
    truthy). A synthetic ``SOA`` and/or apex ``NS`` record is generated only when the
    provider omits one, so the result always parses with :func:`parse_zone_text`.
    """
    origin_abs = origin if origin.endswith(".") else f"{origin}."
    body: list[str] = []
    has_soa = False
    has_apex_ns = False
    for record in records:
        if record.get("disabled"):
            continue
        rtype = str(record.get("type") or "").strip().upper()
        if not rtype:
            continue
        owner = _absolute_owner(str(record.get("name") or "@"), origin_abs)
        ttl = _coerce_int(record.get("ttl"), default_ttl)
        raw_content = str(record.get("content") or record.get("value") or "").strip()
        prio = record.get("prio")
        if prio is None:
            prio = record.get("priority")
        if rtype == "SOA":
            # Some providers expose only the primary nameserver in their SOA "content"
            # rather than the full 7-field rdata; treat those as absent so a synthetic
            # SOA is generated instead of emitting an unparseable record.
            if len(raw_content.split()) < 7:
                continue
            has_soa = True
            body.append(f"{owner}\t{ttl}\tIN\tSOA\t{_normalize_soa_content(raw_content)}")
            continue
        rdata = _rdata_for_bind(rtype, raw_content, prio)
        if rtype == "NS" and owner == origin_abs:
            has_apex_ns = True
        body.append(f"{owner}\t{ttl}\tIN\t{rtype}\t{rdata}")
    prefix: list[str] = []
    if not has_soa:
        prefix.append(
            f"{origin_abs}\t{default_ttl}\tIN\tSOA\t"
            f"{synthetic_nameserver} hostmaster.{origin_abs} 1 7200 3600 1209600 3600"
        )
    if not has_apex_ns:
        prefix.append(f"{origin_abs}\t{default_ttl}\tIN\tNS\t{synthetic_nameserver}")
    header = [f"$ORIGIN {origin_abs}", f"$TTL {default_ttl}"]
    return "\n".join([*header, *prefix, *body]) + "\n"


def validate_zone_file(path: Path, origin: str | None = None) -> str:
    """Validate a zone file and return a human-readable success message."""
    zone = parse_zone_file(path, origin)
    return f"valid zone {zone.origin}: {len(list(zone.nodes))} nodes"


def normalize_owner_name(name: dns.name.Name, origin: dns.name.Name) -> str:
    """Return an absolute owner name with a trailing dot."""
    return name.derelativize(origin).to_text()


def normalize_rdata_text(rdata: dns.rdata.Rdata, origin: dns.name.Name) -> str:
    """Return stable text for one dnspython rdata object."""
    try:
        return str(rdata.to_text(origin=origin, relativize=False))
    except TypeError:
        return str(rdata.to_text())


def records_from_zone(zone: dns.zone.Zone) -> tuple[NormalizedRecord, ...]:
    """Extract stable normalized records from a parsed zone."""
    origin = zone.origin or dns.name.root
    records: list[NormalizedRecord] = []
    for order, (name, ttl, rdata) in enumerate(zone.iterate_rdatas()):
        records.append(
            NormalizedRecord(
                owner=normalize_owner_name(name, origin),
                ttl=int(ttl),
                record_class=dns.rdataclass.to_text(rdata.rdclass),
                record_type=dns.rdatatype.to_text(rdata.rdtype),
                value=normalize_rdata_text(rdata, origin),
                source_order=order,
            )
        )
    return tuple(sorted(records, key=lambda record: (record.owner, record.record_type, record.value, record.ttl)))


def records_from_zone_file(path: Path, origin: str | None = None) -> tuple[NormalizedRecord, ...]:
    """Parse a zone file and return normalized records."""
    return records_from_zone(parse_zone_file(path, origin))


def records_from_zone_text(text: str, origin: str) -> tuple[NormalizedRecord, ...]:
    """Parse zone text and return normalized records."""
    return records_from_zone(parse_zone_text(text, origin))


def normalize_zone_text(text: str, origin: str) -> str:
    """Parse zone text and return canonical BIND-style record lines."""
    return serialize_records(records_from_zone(parse_zone_text(text, origin)))


def filter_records(
    records: Iterable[NormalizedRecord],
    *,
    skip_ns: bool = False,
    skip_types: Iterable[str] = (),
) -> tuple[NormalizedRecord, ...]:
    """Drop NS records (except the apex SOA stays) and records of skipped types.

    Args:
        records: normalized records to filter.
        skip_ns: when true, drop NS records. The apex SOA record is never dropped.
        skip_types: record types (case-insensitive) to drop entirely.
    """
    skip_upper = {record_type.strip().upper() for record_type in skip_types if record_type.strip()}
    kept: list[NormalizedRecord] = []
    for record in records:
        record_type = record.record_type.upper()
        if record_type == "SOA":
            kept.append(record)
            continue
        if skip_ns and record_type == "NS":
            continue
        if record_type in skip_upper:
            continue
        kept.append(record)
    return tuple(kept)


_DNS_TYPES_FOR_FILTER = {
    "A", "AAAA", "CAA", "CDNSKEY", "CDS", "CERT", "CNAME", "CSYNC", "DHCID",
    "DLV", "DNAME", "DNSKEY", "DS", "EUI48", "EUI64", "HINFO", "HIP", "HTTPS",
    "IPSECKEY", "KEY", "KX", "LOC", "MX", "NAPTR", "NS", "NSEC", "NSEC3",
    "NSEC3PARAM", "OPENPGPKEY", "PTR", "RP", "RRSIG", "SMIMEA", "SOA", "SPF",
    "SRV", "SSHFP", "SVCB", "TLSA", "TXT", "URI",
}


def _line_record_type(line: str) -> str | None:
    """Heuristically extract the DNS type token from one BIND-style line."""
    tokens = line.split()
    for index, token in enumerate(tokens):
        if token.upper() == "IN" and index + 1 < len(tokens):
            candidate = tokens[index + 1].upper()
            if candidate in _DNS_TYPES_FOR_FILTER:
                return candidate
    for token in tokens:
        upper = token.upper()
        if upper in _DNS_TYPES_FOR_FILTER:
            return upper
    return None


def filter_zone_text_lenient(
    text: str,
    *,
    skip_ns: bool = False,
    skip_types: Iterable[str] = (),
) -> str:
    """Drop NS / unwanted types from BIND text using a line-based heuristic.

    Used as a fallback when strict dnspython parsing rejects the input (e.g.
    Cloudflare exports that include records dnspython considers out-of-zone).
    Preserves comments, ``$ORIGIN`` / ``$TTL`` directives, blank lines, and
    every record whose type is not skipped. Always keeps ``SOA`` records.
    """
    skip_upper = {entry.strip().upper() for entry in skip_types if entry.strip()}
    if skip_ns:
        skip_upper.add("NS")
    skip_upper.discard("SOA")
    out: list[str] = []
    for raw_line in text.splitlines():
        body = raw_line.split(";", 1)[0].strip()
        if not body or body.startswith("$"):
            out.append(raw_line)
            continue
        rtype = _line_record_type(body)
        if rtype is not None and rtype in skip_upper:
            continue
        out.append(raw_line)
    return "\n".join(out) + ("\n" if not text.endswith("\n") else "")


def filter_zone_text(
    text: str,
    origin: str,
    *,
    skip_ns: bool = False,
    skip_types: Iterable[str] = (),
) -> str:
    """Parse BIND zone text, apply NS/type filters, and return canonical BIND text.

    Falls back to a line-based filter when strict dnspython parsing rejects
    the input (e.g. provider exports that include out-of-zone records).
    """
    try:
        records = records_from_zone(parse_zone_text(text, origin))
    except (ZoneFileError, dns.exception.DNSException, ValueError):
        return filter_zone_text_lenient(text, skip_ns=skip_ns, skip_types=skip_types)
    filtered = filter_records(records, skip_ns=skip_ns, skip_types=skip_types)
    return serialize_records(tuple(sorted(filtered)))


def normalize_zone_file(path: Path, origin: str | None = None) -> str:
    """Parse a zone file and return canonical BIND-style record lines."""
    return serialize_records(records_from_zone_file(path, origin))


def dump_zone_file(path: Path, origin: str | None = None, output_path: Path | None = None) -> str:
    """Return or safely write a canonical dump of a zone file."""
    text = normalize_zone_file(path, origin)
    if output_path is not None:
        write_text_safely(output_path, text)
    return text


def serialize_records(records: tuple[NormalizedRecord, ...]) -> str:
    """Serialize normalized records with deterministic ordering and final newline."""
    lines = [record.to_zone_line() for record in records]
    return "\n".join(lines) + ("\n" if lines else "")


def write_text_safely(path: Path, text: str, *, overwrite: bool = False) -> None:
    """Write text without overwriting existing files unless explicitly allowed."""
    if path.exists() and not overwrite:
        msg = f"refusing to overwrite existing file without overwrite=True: {path}"
        raise ZoneFileError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def diff_zone_records(before: tuple[NormalizedRecord, ...], after: tuple[NormalizedRecord, ...]) -> ZoneDiff:
    """Create a safe zone change plan between two normalized record sets."""
    before_exact = {record.exact_key: record for record in before}
    after_exact = {record.exact_key: record for record in after}
    unchanged_keys = set(before_exact) & set(after_exact)

    before_changed = [record for record in before if record.exact_key not in unchanged_keys]
    after_changed = [record for record in after if record.exact_key not in unchanged_keys]

    before_by_identity = _group_by_identity(before_changed)
    after_by_identity = _group_by_identity(after_changed)

    updates: list[ZoneChange] = []
    deletes: list[ZoneChange] = []
    creates: list[ZoneChange] = []

    for identity in sorted(set(before_by_identity) | set(after_by_identity)):
        before_group = before_by_identity.get(identity, [])
        after_group = after_by_identity.get(identity, [])
        if before_group and after_group:
            max_pairs = min(len(before_group), len(after_group))
            updates.extend(ZoneChange("update", before_group[index], after_group[index]) for index in range(max_pairs))
            deletes.extend(ZoneChange("delete", record, None) for record in before_group[max_pairs:])
            creates.extend(ZoneChange("create", None, record) for record in after_group[max_pairs:])
        elif before_group:
            deletes.extend(ZoneChange("delete", record, None) for record in before_group)
        else:
            creates.extend(ZoneChange("create", None, record) for record in after_group)

    unchanged = tuple(ZoneChange("unchanged", before_exact[key], after_exact[key]) for key in sorted(unchanged_keys))
    return ZoneDiff(
        creates=tuple(creates),
        updates=tuple(updates),
        deletes=tuple(deletes),
        unchanged=unchanged,
    )


def diff_zone_files(before_path: Path, after_path: Path, origin: str | None = None) -> ZoneDiff:
    """Diff two zone files using normalized DNS records."""
    return diff_zone_records(records_from_zone_file(before_path, origin), records_from_zone_file(after_path, origin))


def _group_by_identity(records: list[NormalizedRecord]) -> dict[tuple[str, str, str], list[NormalizedRecord]]:
    grouped: dict[tuple[str, str, str], list[NormalizedRecord]] = {}
    for record in records:
        grouped.setdefault(record.identity, []).append(record)
    for values in grouped.values():
        values.sort(key=lambda record: record.exact_key)
    return grouped
