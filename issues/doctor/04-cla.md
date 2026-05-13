# Technical Specification: `donazopy doctor` — A DNS Zone Audit and Auto-Remediation Subcommand

## 1. Goals, non-goals, design philosophy

### 1.1 Goals
`donazopy doctor TARGET [--fix]` performs a comprehensive audit of a DNS zone, combining authoritative-record inspection (data the tool already has via provider APIs or BIND zone files) with live DNS resolution and external probes (HTTPS, SMTP, CT logs, takeover fingerprints). It produces structured Findings of categorized severity, and with `--fix` it remediates as many as possible — either via the tool's own provider/registrar APIs (add/remove/modify records, reassign nameservers) or by printing precise manual instructions when remediation requires action outside donazopy's reach.

The tool's reason to exist is to catch the **structural and migration-artifact issues** that surface during real multi-provider DNS work — the kind of issues that don't fail `named-checkzone` but quietly break delivery, fail to enforce policy, or leak old delegation. The two motivating examples drive design decisions: (a) leftover NS records from a previous provider after copying a zone to a new one, and (b) duplicate TXT records that differ only in escape level.

### 1.2 Non-goals
The doctor is **not** a DNSSEC validator built from scratch — it delegates cryptographic validation to dnspython. It is **not** a full TLS scanner — it borrows from sslyze/sslscan idioms but does not replace SSL Labs-grade probing. It is **not** a registrar-side automation tool: while it can drive `assign_nameservers()` on the registrar abstraction, it cannot perform DNSSEC DS submission, EPP transfers, or registrant-data changes. It does not maintain a long-running daemon, queue, or report database — every run is stateless except for an opt-in disk cache for live lookups.

### 1.3 Design philosophy
Three principles govern the design.

**Authoritative-first, live-augmented.** Every check first inspects the records donazopy already has in hand (from provider list_records or a parsed BIND file). Only after exhausting that source does it issue live DNS / HTTPS / SMTP queries. This makes the bulk of the audit fast, deterministic, offline-capable, and provider-API-friendly (no per-finding extra API call).

**Each finding is a transaction.** Every Finding carries enough metadata to reproduce, severity-classify, and remediate it. Fixes are described declaratively as record-level operations (`create`, `delete`, `modify`, `replace_rrset`), not procedural code. The fixer engine consumes that declarative description and dispatches to the appropriate provider API.

**Idempotency, dry-run, and reversibility.** `--fix` runs through a planning phase, prints the plan, and only applies it on confirmation (`--yes` skips prompts). Every applied change is journaled with the prior record state so `donazopy doctor TARGET --undo \<run-id\>` can roll back where the provider API permits.

## 2. CLI surface and target/option semantics

### 2.1 Synopsis
```
donazopy doctor TARGET
                [--fix] [--yes] [--undo RUN_ID]
                [--severity LEVEL] [--only CHECKS] [--skip CHECKS]
                [--live / --no-live] [--resolvers LIST]
                [--report FORMAT] [--output PATH]
                [--cache-dir DIR] [--no-cache]
                [--profile PROFILE] [--config PATH]
                [--workers N] [--timeout SECONDS]
                [--include-private] [--strict-rfc]
```

`TARGET` follows existing donazopy notation `[provider/][domain][:record_type][:host_name][:value]`. For doctor, the meaningful axes are `provider/domain` (the entire zone) or `provider/domain:host_name` (audit one label). When `provider/` is omitted, donazopy infers it by querying live NS records and matching against the provider-NS-suffix registry; if no match is found, the audit runs in **live-only** mode (no authoritative record set is available, so structural checks operate on what live queries return).

### 2.2 Options
`--fix` enables remediation. Without it the tool is read-only. Combined with `--yes`, all prompts are skipped — equivalent to `apt-get -y`. Without `--yes`, every fix presents `[Y/n/a/q/?]` (yes / no / all-remaining-yes / quit / explain).

`--severity LEVEL` filters output to a minimum severity (`hint`, `info`, `warning`, `error`, `critical`). Default is `info`. `--strict-rfc` raises every RFC-violation finding to at least `error`.

`--only CHECKS` and `--skip CHECKS` accept comma-separated check IDs or category prefixes (e.g., `--only spf,dmarc` or `--skip ZONE.*,LIVE.takeover`).

`--live / --no-live` toggles the live-lookup subsystem. `--no-live` makes the run fully offline — all checks restricted to authoritative-record inspection.

`--resolvers` overrides the default resolver triplet (1.1.1.1, 8.8.8.8, 9.9.9.9). Use `--resolvers system` to use the OS stub. Use `--resolvers authoritative` to query only the zone's own NS (useful when comparing parent-vs-child).

`--report FORMAT` ∈ `text` (default, TTY), `json`, `sarif`, `markdown`, `html`. `--output PATH` writes to file. `--profile PROFILE` selects predefined check bundles: `email-only`, `web-only`, `migration-audit`, `pre-go-live`, `full` (default).

`--workers N` caps asyncio concurrency for live checks (default 50). `--timeout SECONDS` is the per-query DNS/HTTP timeout (default 5s).

### 2.3 Exit codes
`0` = clean (no finding ≥ severity threshold). `1` = warnings only. `2` = at least one error. `3` = at least one critical. `4` = fixable findings remained unfixed (e.g., `--fix` not given, or fix rejected at prompt). `64+` = donazopy internal errors (config, API auth, etc.) per `sysexits.h`.

## 3. Architecture: checks, findings, severity, fixer pipeline

### 3.1 High-level flow
A run proceeds through six phases. **Phase 1 — context build**: resolve TARGET, load authoritative records (provider API list_records, or zone-file parse, or AXFR if available), identify the hosting provider, identify the registrar. **Phase 2 — offline checks**: every Check class declared `requires_live=False` runs over the in-memory zone. **Phase 3 — live discovery**: parallel resolution of apex NS, MX, TXT, DMARC, DKIM-selector probes, MTA-STS policy fetch, etc.; results are cached in the Context. **Phase 4 — live checks**: every Check with `requires_live=True` runs over the live results. **Phase 5 — synthesis**: Findings are deduplicated, cross-correlated (e.g., an MTA-STS check that depends on the DMARC check's result), and ranked. **Phase 6 — fix planning and application** (only with `--fix`): the FixPlanner builds an ordered list of FixActions, prompts as needed, and applies them through provider APIs.

### 3.2 Core data types

```python
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Iterable, Literal, Optional
import dns.rrset, dns.name

class Severity(IntEnum):
    HINT     = 10   # stylistic, e.g. TTL hygiene
    INFO     = 20   # best practice, e.g. missing CAA
    WARNING  = 30   # likely misconfig, e.g. leftover IONOS NS in Cloudflare
    ERROR    = 40   # protocol violation, e.g. CNAME at apex
    CRITICAL = 50   # outage-level, e.g. broken DNSSEC chain

class Fixability(IntEnum):
    AUTO_SAFE        = 1  # idempotent, semantic-preserving
    AUTO_DEFAULTS    = 2  # tool inserts a sensible default record
    AUTO_INTERACTIVE = 3  # tool can fix but asks first
    MANUAL_ONLY      = 4  # tool prints instructions

@dataclass(frozen=True)
class RecordRef:
    """Identifies an RRset or single record within a zone."""
    zone: str               # e.g. "example.com."
    name: str               # FQDN incl. apex
    rtype: str              # "TXT","NS","A",...
    ttl: Optional[int] = None
    rdata: tuple[str, ...] = ()   # canonical wire-form strings

@dataclass
class FixAction:
    op: Literal["create","delete","modify","replace_rrset",
                "assign_nameservers","manual"]
    target: RecordRef
    new_rdata: tuple[str, ...] = ()
    new_ttl: Optional[int] = None
    manual_instructions: str = ""
    rollback_state: Optional["FixAction"] = None  # auto-generated inverse
    requires_confirmation: bool = True

@dataclass
class Finding:
    check_id: str            # e.g. "MIGRATE.leftover_ns"
    severity: Severity
    fixability: Fixability
    title: str               # one-line summary, TTY-colorable
    description: str         # paragraph, may include RFC refs
    evidence: dict[str, Any] # raw data: offending records, dig output, URLs
    rfc_refs: tuple[str, ...] = ()
    fix_actions: tuple[FixAction, ...] = ()
    suppression_key: Optional[str] = None  # for .donazopy-doctor-ignore

class Check:
    id: str                  # "MIGRATE.leftover_ns"
    category: str            # "migration" | "email" | "dnssec" | ...
    requires_live: bool = False
    requires_provider_api: bool = False
    depends_on: tuple[str, ...] = ()

    def run(self, ctx: "AuditContext") -> Iterable[Finding]: ...

class AuditContext:
    """Single source of truth shared by every check during a run."""
    target: Target
    zone: dns.zone.Zone | None            # authoritative records, if available
    provider: DNSHostingProvider | None
    registrar: RegistrarProvider | None
    live: "LiveLookupCache"               # see §6
    settings: AuditSettings
    findings: list[Finding] = field(default_factory=list)
```

### 3.3 Check registry
Checks register themselves via a decorator into a global registry, allowing third-party plugins:

```python
_registry: dict[str, type[Check]] = {}

def register(cls: type[Check]) -> type[Check]:
    if cls.id in _registry:
        raise ValueError(f"duplicate check id {cls.id}")
    _registry[cls.id] = cls
    return cls

@register
class LeftoverNSCheck(Check):
    id = "MIGRATE.leftover_ns"
    category = "migration"
    requires_live = False
    ...
```

### 3.4 Fixer pipeline
The `FixPlanner` consumes the Findings list, gathers their `fix_actions`, topologically sorts them (e.g., creating a new SPF must precede deleting the old one if the user wants atomic replacement; deleting leftover NS records is independent), batches them by provider (to amortize API calls), and produces a `FixPlan`. The plan is printed, optionally diff-rendered, and applied. Each successful `FixAction` writes a journal entry `{action, prior_state, timestamp}` to `~/.donazopy/journal/<run-id>.jsonl` for `--undo`.

## 4. Complete catalog of checks

The catalog below uses identifiers organized by the user's category letters. Each entry gives: detection (authoritative and/or live), severity, fixability, fix description. Where two algorithms exist (offline + online), both are described.

### Category A — Zone hygiene / structural

**A1 `ZONE.duplicate_record_byte_identical`** — Identical RRs within an RRset (RFC 2181 §5 says behavior undefined). Detection: hash canonical wire-form of every (name, type, rdata) and count. Severity: WARNING. Fixability: AUTO_SAFE — delete duplicates, keep one. Fix: provider.delete_record on duplicates.

**A2 `ZONE.duplicate_txt_semantic`** — TXT records semantically equal but textually differ. Normalization: strip leading/trailing whitespace, remove inter-string whitespace from multi-string TXT (RFC 1035), unescape `\"`, unescape `\\`, strip surrounding `"` if the entire value is wrapped, normalize Unicode NFC, lowercase known-case-insensitive prefixes (`v=spf1`, `v=DKIM1`, `v=DMARC1`, `google-site-verification=`). Two TXT records are semantic-duplicates if their normalized forms match. Severity: WARNING. Fixability: AUTO_INTERACTIVE. Fix: keep the canonically-formatted record (no escapes, no surrounding quotes, single string ≤255 or properly split), delete the others. **This is the user's example 2.**

**A3 `ZONE.txt_escape_artifacts`** — A TXT record whose value begins with literal `\"` or `"` followed by content — indicates broken import/export. Detection: regex on rdata string `^\\"|^"v=`. Severity: WARNING. Fixability: AUTO_SAFE. Fix: strip the artifacts, replace with normalized value.

**A4 `ZONE.txt_split_with_space`** — Multi-string TXT where consumers will receive a stray space inside the concatenated logical value (DKIM signature would break). Detection: parse rdata as `dns.rdata` and check that joined character-strings produce a value with whitespace at the join boundary that looks meaningful (e.g., inside a base64 blob the `=` padding is followed by space then more base64). Severity: ERROR for DKIM, WARNING otherwise. Fix: AUTO_SAFE; rewrite as proper 255-byte split.

**A5 `ZONE.cname_at_apex`** — CNAME RR at the zone apex (RFC 1034 §3.6.2, RFC 1912 §2.4). Detection: scan zone for owner == zone origin and type == CNAME. Severity: ERROR. Fixability: AUTO_INTERACTIVE — replace with A/AAAA from CNAME target, or HTTPS/SVCB AliasMode (RFC 9460), or provider-specific ALIAS/ANAME if supported. Fix: resolve target's A/AAAA live, create those at apex, delete CNAME. Where provider supports ANAME/ALIAS, prefer that.

**A6 `ZONE.cname_coexists_other`** — CNAME at a name that also has other record types (RFC 2181 §10.1; RRSIG/NSEC/NSEC3/DNAME excepted). Severity: ERROR. Fix: AUTO_INTERACTIVE — present user with both sides, ask which to delete.

**A7 `ZONE.cname_chain_long`** — CNAME chain ≥5 (WARNING) or ≥8 (ERROR). Detection: walk CNAME chain in authoritative records or live. Fix: MANUAL_ONLY — point original to terminal target.

**A8 `ZONE.cname_loop`** — Cycle in CNAME chain. Severity: CRITICAL. Fix: AUTO_INTERACTIVE — break the cycle by deleting one CNAME (must be user-chosen).

**A9 `ZONE.mx_target_cname`** — MX target is a CNAME (RFC 2181 §10.3, RFC 5321 §5.1). Severity: ERROR. Fix: AUTO_INTERACTIVE — replace MX with A/AAAA-holding hostname, or move target to non-aliased name.

**A10 `ZONE.ns_target_cname`** — NS target is a CNAME (RFC 2181 §10.3). Severity: ERROR. Fix: AUTO_INTERACTIVE — same shape as A9.

**A11 `ZONE.srv_target_cname`** — SRV target is CNAME (BIND `named-checkzone -S`). Severity: WARNING. Fix: AUTO_INTERACTIVE.

**A12 `ZONE.srv_target_dot_with_other_targets`** — SRV with target `.` (meaning "service unavailable") coexisting with another SRV of the same name. Severity: ERROR. Fix: AUTO_INTERACTIVE — keep one.

**A13 `ZONE.srv_dangling_target`** — SRV target name does not resolve. Detection: live resolve target A/AAAA. Severity: WARNING. Fix: MANUAL_ONLY.

**A14 `ZONE.dangling_cname_internal`** — CNAME target inside the same zone but the target name has no records. Detection: scan zone for missing terminal. Severity: WARNING. Fix: AUTO_INTERACTIVE — delete or create target.

**A15 `LIVE.stale_cname_takeover_risk`** — CNAME points to a known-vulnerable hosted-service domain (Heroku, S3, Azure, etc.) AND the target either NXDOMAIN's or returns a takeover fingerprint. Detection: match CNAME target against the regularly-refreshed `can-i-take-over-xyz/fingerprints.json` provider-suffix list; if matched, resolve target. If NXDOMAIN for an "nxdomain: true" service → flag. Else HTTPS GET and regex-match service fingerprint. Severity: CRITICAL if `vulnerable: true, cicd_pass: true`; ERROR if `vulnerable: true`; WARNING if `edge case`. Fixability: AUTO_INTERACTIVE — recommend deletion. Never auto-claim the orphaned service. Fix actions: `delete CNAME` + manual instruction "either reclaim the resource at {target} or remove this record."

**A16 `ZONE.ttl_not_uniform_in_rrset`** — Records in same (name, class, type) RRset have different TTLs (RFC 2181 §5.2). Severity: WARNING. Fix: AUTO_SAFE — set all to min(TTLs) (resolver behavior).

**A17 `ZONE.ttl_too_low`** — TTL <30s on stable record types (NS, SOA, A at apex). Severity: HINT. Fix: AUTO_DEFAULTS — raise to 300.

**A18 `ZONE.ttl_too_high`** — TTL >604800 (1 week) blocks emergency change. Severity: HINT. Fix: AUTO_DEFAULTS — lower to 86400.

**A19 `ZONE.ttl_zero`** — TTL=0 in production. Severity: WARNING. Fix: AUTO_DEFAULTS — set to 300.

**A20 `ZONE.soa_serial_format`** — SOA serial not in YYYYMMDDnn format and not Unix-epoch-shaped (i.e., neither a date nor a monotonic int). Severity: HINT. Fix: AUTO_DEFAULTS — rewrite serial as today's date + 01.

**A21 `ZONE.soa_refresh_out_of_range`** — Refresh <1200 or >86400 (RFC 1912 §2.2). Severity: HINT. Fix: AUTO_DEFAULTS — set to 3600.

**A22 `ZONE.soa_retry_invalid`** — Retry ≥ refresh or <180. Severity: WARNING. Fix: AUTO_DEFAULTS — set to 900.

**A23 `ZONE.soa_expire_invalid`** — Expire <604800 or ≤ refresh+retry. Severity: WARNING. Fix: AUTO_DEFAULTS — set to 1209600.

**A24 `ZONE.soa_minimum_invalid`** — Negative-cache TTL not in 300–86400. Severity: HINT. Fix: AUTO_DEFAULTS — set to 3600.

**A25 `ZONE.soa_mname_not_in_ns`** — SOA MNAME not present in apex NS RRset. May be hidden-master. Severity: HINT. Fix: MANUAL_ONLY.

**A26 `ZONE.soa_rname_invalid`** — Contains literal `@` (should be `.`), or first label contains undotted local-part with embedded `.` not escaped. Severity: WARNING. Fix: AUTO_DEFAULTS — rewrite as `hostmaster.<zone>`.

**A27 `ZONE.aaaa_missing`** — A record exists but no AAAA at same name. Severity: INFO. Fix: MANUAL_ONLY — instruct user to either dual-stack or document the choice.

**A28 `ZONE.a_aaaa_inconsistent`** — A and AAAA both present but resolve to hosts that serve different content (live HEAD comparison of HTML title or content-hash on `/`). Severity: INFO. Fix: MANUAL_ONLY.

**A29 `ZONE.private_ip_in_public_zone`** — A/AAAA contains RFC 1918, ULA fc00::/7, link-local, or unspecified address. Severity: WARNING (ERROR if zone is publicly delegated). Detection: `ipaddress.ip_address(rdata).is_private or .is_link_local or .is_unspecified`. Fix: AUTO_INTERACTIVE — delete or replace.

**A30 `ZONE.wildcard_masked`** — Wildcard `*` at one level masked by explicit deeper records (RFC 4592 §2.2.2). Severity: WARNING. Fix: MANUAL_ONLY.

**A31 `ZONE.wildcard_at_non_leftmost`** — `*` not in leftmost label position. Severity: ERROR. Fix: AUTO_INTERACTIVE — delete (it's not a valid wildcard, just a literal `*` label).

**A32 `ZONE.label_too_long`** — Any label >63 octets. Severity: ERROR. Fix: MANUAL_ONLY.

**A33 `ZONE.fqdn_too_long`** — FQDN wire-form >255. Severity: ERROR. Fix: MANUAL_ONLY.

**A34 `ZONE.label_invalid_chars`** — Label contains characters outside LDH (after IDNA conversion if applicable) at a position where hostname rules apply (A/AAAA/MX/NS targets). Severity: ERROR. Fix: MANUAL_ONLY.

**A35 `ZONE.label_leading_or_trailing_hyphen`** — Severity: ERROR. Fix: MANUAL_ONLY.

**A36 `ZONE.idn_normalization`** — Label is U-label that doesn't NFC-normalize, or IDNA2003-vs-2008 produces different A-labels. Severity: WARNING. Fix: AUTO_SAFE — rewrite owner to canonical A-label.

**A37 `ZONE.idn_homoglyph`** — Mixed-script confusable detected (UTS #39). Severity: WARNING. Fix: MANUAL_ONLY.

**A38 `ZONE.reserved_name`** — Owner or target in RFC 6761 reserved namespace (`localhost`, `.invalid`, `.test`, `.local`, `.onion`, `home.arpa`, `.alt`). Severity: ERROR. Fix: MANUAL_ONLY.

**A39 `ZONE.empty_rdata`** — Record with zero-length rdata where the type requires content. Severity: ERROR. Fix: AUTO_INTERACTIVE — delete.

**A40 `ZONE.trailing_whitespace`** — Record values containing trailing spaces or unprintable characters. Severity: HINT. Fix: AUTO_SAFE — strip.

### Category B — Email authentication and deliverability

**SPF**

**B1 `SPF.missing`** — No TXT starting with `v=spf1` at apex. Severity: WARNING. Fix: AUTO_DEFAULTS. Default = `v=spf1 -all` for non-sending domains, or includes inferred from existing MX (e.g., `aspmx.l.google.com` MX → `include:_spf.google.com`; `*.protection.outlook.com` MX → `include:spf.protection.outlook.com`). The default is `~all` for cautious rollout, `-all` if `--strict-rfc`.

**B2 `SPF.multiple_records`** — More than one `v=spf1` TXT at apex (RFC 7208 §3.2 → permerror). Severity: ERROR. Fix: AUTO_INTERACTIVE — merge mechanisms into one record by union, then delete the extras.

**B3 `SPF.too_many_lookups`** — Recursive count of `include`, `a`, `mx`, `ptr`, `exists`, `redirect` exceeds 10 (RFC 7208 §4.6.4). Algorithm: recursive descent through `include`/`redirect` with cycle detection (per the pseudocode in research). Severity: ERROR. Fix: AUTO_INTERACTIVE — propose flattening (resolve `include`s to `ip4:`/`ip6:` ranges) and removing obvious stale includes (those returning permerror).

**B4 `SPF.void_lookups_exceeded`** — More than 2 lookups returning NXDOMAIN or NODATA (RFC 7208 §4.6.4). Severity: ERROR. Fix: AUTO_INTERACTIVE — remove offending mechanisms.

**B5 `SPF.uses_ptr_mechanism`** — `ptr` present (deprecated, RFC 7208 §5.5). Severity: WARNING. Fix: AUTO_INTERACTIVE — remove `ptr`.

**B6 `SPF.permissive_all`** — `+all` or `?all`. Severity: ERROR for `+all`, WARNING for `?all`. Fix: AUTO_INTERACTIVE — replace with `~all` (testing) or `-all` (strict).

**B7 `SPF.missing_all`** — No terminating `all`. Severity: WARNING. Fix: AUTO_DEFAULTS — append ` ~all`.

**B8 `SPF.deprecated_rr_type`** — Type 99 SPF record exists (RFC 6686, 7208 §3.1). Severity: ERROR. Fix: AUTO_SAFE — delete the type-99 RR.

**B9 `SPF.macro_syntax`** — Invalid macro construction (parse `%{...}` and validate letters s/l/o/d/i/p/h/c/r/t/v and modifiers). Severity: ERROR. Fix: MANUAL_ONLY.

**B10 `SPF.include_chain_permerror`** — A recursive include returns permerror. Severity: ERROR. Fix: AUTO_INTERACTIVE — remove broken include.

**B11 `SPF.stale_include`** — Include targets `_spf.salesforce.com`, `spf.mtasv.net`, `_netblocks.mimecast.com`, etc., but no current MX or DKIM evidence the service is in use. Heuristic only. Severity: HINT. Fix: AUTO_INTERACTIVE — propose removal.

**B12 `SPF.wrong_location`** — `v=spf1` TXT at `_spf.<domain>` or a subdomain instead of apex. Severity: WARNING. Fix: AUTO_INTERACTIVE — move to apex.

**B13 `SPF.spf2_syntax`** — Record starts with `spf2.0/` (obsolete Sender ID). Severity: WARNING. Fix: AUTO_SAFE — delete.

**B14 `SPF.unreachable_after_all`** — Mechanism appears after a terminating `all`. Severity: WARNING. Fix: AUTO_SAFE — drop unreachable mechanisms.

**DKIM**

**B20 `DKIM.discovery`** — Enumerate selectors at `<selector>._domainkey.<domain>` for the comprehensive selector wordlist (the table from research: `google`, `google2048`, `selector1`, `selector2`, `k1`–`k3`, `s1`, `s2`, `mandrill`, `mxvault`, `mailo`, `smtp`, `pm`, `default`, `dkim`, `mail`, `protonmail`, `fm1`–`fm3`, `mimecast`, `scph0316`/`scph0517`/`scph1019`, plus date-pattern selectors, plus 1000+ entries from the prove.email archive cached as a local file). Live probe runs in parallel with concurrency 50. Severity: INFO when no selectors found (purely informational since DKIM selectors aren't enumerable). Fix: none.

**B21 `DKIM.weak_key`** — Public-key modulus <1024 bits (CRITICAL) or 1024–2047 (WARNING). Detection: base64-decode `p=`, parse DER SubjectPublicKeyInfo via `cryptography.hazmat.primitives.serialization.load_der_public_key`, read `key.key_size`. Severity: as above. Fix: MANUAL_ONLY — instruct user to regenerate at the ESP.

**B22 `DKIM.revoked_key_at_active_selector`** — `p=` empty AND selector still referenced in `DKIM-Signature` headers from recent outbound mail (when SMTP test-send is available) or selector appears in a recent DMARC aggregate report. Severity: ERROR. Fix: MANUAL_ONLY.

**B23 `DKIM.testing_flag`** — `t=y` present. Severity: WARNING. Fix: AUTO_INTERACTIVE — delete `t=y`.

**B24 `DKIM.sha1_only`** — `h=sha1` without `sha256` (RFC 8301 deprecates SHA-1). Severity: WARNING. Fix: AUTO_DEFAULTS — remove `h=` (default permits sha256).

**B25 `DKIM.multiple_records_at_selector`** — More than one TXT at same `<selector>._domainkey`. Severity: ERROR. Fix: AUTO_INTERACTIVE.

**B26 `DKIM.malformed_key`** — `p=` not valid DER. Severity: ERROR. Fix: MANUAL_ONLY.

**B27 `DKIM.tag_order_v_not_first`** — `v=DKIM1` present but not first. Severity: WARNING. Fix: AUTO_SAFE — reorder.

**B28 `DKIM.obsolete_g_tag`** — `g=` present with restrictive value. Severity: HINT. Fix: AUTO_SAFE — remove.

**B29 `DKIM.stale_selector`** — Selector record exists but `_domainkey` rotation history (or DMARC reports) suggests selector is no longer signing. Severity: HINT. Fix: AUTO_INTERACTIVE — propose deletion (or keep with empty `p=` if rotation <7d).

**DMARC**

**B30 `DMARC.missing`** — No TXT at `_dmarc.<domain>`. Severity: WARNING. Fix: AUTO_DEFAULTS. Default = `v=DMARC1; p=none; rua=mailto:dmarc@<domain>; fo=1; adkim=r; aspf=r` for monitoring rollout. The tool prints recommended advancement steps in the finding's description.

**B31 `DMARC.multiple_records`** — More than one DMARC TXT. Severity: ERROR. Fix: AUTO_INTERACTIVE — merge and delete extras.

**B32 `DMARC.tag_order`** — `v=` not first or `p=` not second (RFC 7489 §6.3). Severity: ERROR. Fix: AUTO_SAFE — reorder.

**B33 `DMARC.policy_none`** — `p=none` (monitoring only). Severity: WARNING after 60 days, INFO otherwise. Heuristic for "after 60 days" uses the SOA serial date if YYYYMMDDnn format, else the find-first-observed cache. Fix: AUTO_INTERACTIVE — propose advancement to quarantine.

**B34 `DMARC.no_rua`** — Missing aggregate-report destination. Severity: WARNING. Fix: AUTO_DEFAULTS — add `rua=mailto:dmarc@<domain>`.

**B35 `DMARC.invalid_mailto`** — `rua=` or `ruf=` value doesn't begin with a valid scheme. Severity: ERROR. Fix: AUTO_INTERACTIVE.

**B36 `DMARC.external_destination_unauthorized`** — `rua=mailto:reports@other.com` with no corresponding `<source>._report._dmarc.other.com` TXT containing `v=DMARC1` (RFC 7489 §7.1). Detection: live lookup. Severity: ERROR — reports never sent. Fix: MANUAL_ONLY — instruct user to add the auth record at the destination domain.

**B37 `DMARC.missing_sp`** — Parent-domain DMARC without explicit `sp=`. Severity: INFO. Fix: AUTO_DEFAULTS — add `sp=` matching `p=`.

**B38 `DMARC.missing_np`** — DMARCbis era, `np=` not set. Severity: INFO. Fix: AUTO_DEFAULTS — add `np=reject`.

**B39 `DMARC.pct_inconsistent`** — `pct<100` with `p=reject` (operationally inconsistent; deprecated in DMARCbis). Severity: WARNING. Fix: AUTO_INTERACTIVE — remove `pct` or set to 100.

**B40 `DMARC.deprecated_tags`** — `rf`, `ri`, `pct` present (DMARCbis removed). Severity: HINT. Fix: AUTO_SAFE — remove.

**B41 `DMARC.ruf_https_in_rfc7489_era`** — `ruf=https:` (only mailto in RFC 7489). Severity: WARNING. Fix: AUTO_INTERACTIVE.

**B42 `DMARC.no_reporting_addresses`** — Both `rua=` and `ruf=` missing (no visibility). Severity: WARNING. Fix: AUTO_DEFAULTS.

**MTA-STS**

**B50 `MTA_STS.dns_missing`** — No TXT at `_mta-sts.<domain>` but MX exists. Severity: INFO. Fix: AUTO_DEFAULTS — add `v=STSv1; id=YYYYMMDDhhmmssZ`; emit MANUAL_ONLY instruction to publish the policy file at `https://mta-sts.<domain>/.well-known/mta-sts.txt`.

**B51 `MTA_STS.policy_file_unreachable`** — DNS record present but `https://mta-sts.<domain>/.well-known/mta-sts.txt` returns non-200, redirect, wrong content-type, or TLS error. Severity: ERROR. Fix: MANUAL_ONLY.

**B52 `MTA_STS.id_unchanged_on_policy_update`** — Local cache shows policy file content changed but `id=` did not change. (Only available if the tool was run on this zone previously and cached the prior policy.) Severity: WARNING. Fix: AUTO_INTERACTIVE — bump `id=`.

**B53 `MTA_STS.invalid_mode`** — `mode` ∉ {none, testing, enforce}. Severity: ERROR. Fix: MANUAL_ONLY.

**B54 `MTA_STS.mx_pattern_mismatch`** — One of the actual MX hosts isn't covered by any `mx:` pattern in the policy. Severity: ERROR in enforce mode, WARNING in testing. Fix: AUTO_INTERACTIVE — add the missing pattern (after manual confirmation, since policy file is HTTP-served, not provider-managed).

**B55 `MTA_STS.max_age_out_of_range`** — `max_age` <86400 or >31557600. Severity: WARNING. Fix: MANUAL_ONLY.

**B56 `MTA_STS.cert_invalid`** — TLS certificate at `mta-sts.<domain>` doesn't validate. Severity: ERROR. Fix: MANUAL_ONLY.

**TLS-RPT**

**B60 `TLS_RPT.missing`** — No TXT at `_smtp._tls.<domain>`. Severity: INFO. Fix: AUTO_DEFAULTS — add `v=TLSRPTv1; rua=mailto:tlsrpt@<domain>`.

**B61 `TLS_RPT.invalid_rua`** — `rua=` value not a valid scheme. Severity: ERROR. Fix: AUTO_INTERACTIVE.

**BIMI**

**B70 `BIMI.dmarc_not_enforcing`** — BIMI TXT exists but DMARC `p=` ∈ {none}. Severity: WARNING. Fix: MANUAL_ONLY — strengthen DMARC first.

**B71 `BIMI.svg_invalid`** — Logo doesn't conform to SVG Tiny PS profile (root has `width`/`height`/`x`/`y`, contains `<script>`, contains `<image href=...>`, contains animation, >32KB, missing `<title>`). Detection: HTTPS-fetch `l=` URL, parse with lxml, run profile validator. Severity: ERROR. Fix: MANUAL_ONLY.

**B72 `BIMI.vmc_invalid`** — VMC PEM doesn't chain to approved BIMI roots, SAN doesn't match, expired, or logotype-extension SHA-256 doesn't match served SVG. Severity: ERROR. Fix: MANUAL_ONLY.

**Null MX, autoconfig, DANE, generic mail**

**B80 `MAIL.no_mx_no_null_mx`** — No MX at all (and no `MX 0 .`). Severity: INFO. Fix: AUTO_INTERACTIVE — ask: "Does this domain receive mail? If not, add null MX." If "no" → add `0 .`.

**B81 `MAIL.null_mx_with_other_mx`** — `0 .` present alongside other MX. Severity: ERROR. Fix: AUTO_INTERACTIVE — keep one strategy.

**B82 `MAIL.mx_loopback_or_private`** — MX target resolves to 127.0.0.1, 0.0.0.0, RFC 1918, or ULA. Severity: ERROR. Fix: AUTO_INTERACTIVE — delete.

**B83 `MAIL.mx_ip_literal`** — MX exchange is an IP literal. Severity: ERROR. Fix: AUTO_INTERACTIVE.

**B84 `MAIL.autoconfig_missing`** — No `autoconfig.<domain>` A/CNAME and no SRV; user opts-in via profile `--profile self-hosted-mail`. Severity: INFO. Fix: MANUAL_ONLY.

**B85 `MAIL.autodiscover_missing`** — No `autodiscover.<domain>` and no `_autodiscover._tcp.<domain>` SRV. Severity: INFO. Fix: MANUAL_ONLY.

**B86 `MAIL.srv_mail_misconfigured`** — RFC 6186 SRVs point to dead targets, or `_pop3s._tcp` priority 0 but `_submissions._tcp` priority 0 0 0 . (disabled). Detection: live SRV resolve and check target reachability on declared port. Severity: WARNING. Fix: MANUAL_ONLY.

**B90 `DANE.tlsa_present_without_dnssec`** — TLSA records at `_25._tcp.<mx>` but the MX hostname's zone is unsigned. Severity: CRITICAL — TLSA silently ignored. Fix: MANUAL_ONLY — sign the zone or remove TLSA.

**B91 `DANE.usage_invalid_for_smtp`** — TLSA with usage 0 or 1 (PKIX-TA/EE) for SMTP (RFC 7672 §3.1.3 forbids). Severity: ERROR. Fix: AUTO_INTERACTIVE — convert to DANE-EE(3) or DANE-TA(2).

**B92 `DANE.tlsa_mismatch`** — TLSA hash doesn't match presented MX cert/key. Severity: ERROR — STARTTLS will fail under DANE. Detection: live STARTTLS handshake, capture cert, compute SPKI SHA-256, compare. Fix: MANUAL_ONLY.

**B93 `DANE.no_rollover`** — Only one TLSA per MX (cert renewal will outage). Severity: HINT. Fix: MANUAL_ONLY.

### Category C — NS / SOA / delegation / glue

**C1 `DELEGATION.lame`** — A parent-delegated NS doesn't respond authoritatively (timeout, no AA flag, REFUSED, or returns no SOA). Detection: for each NS, `dig @ns +norecurse <zone> SOA`. Severity: ERROR. Fix: AUTO_INTERACTIVE — remove lame NS from apex (if user controls child) or instruct registrar update.

**C2 `DELEGATION.parent_child_ns_mismatch`** — Parent referral NS RRset ≠ child apex NS RRset. Detection: query parent's authoritative NS (e.g., gTLD servers) directly for the zone's NS RRset; query child's apex NS RRset; diff. Severity: WARNING. Fix: MANUAL_ONLY (registrar) for parent side; AUTO_SAFE for child side via existing donazopy `assign_nameservers()`.

**C3 `MIGRATE.leftover_ns`** — Apex NS RRset contains NS records pointing to a different provider than the one currently hosting the zone. Detection algorithm — **this is the user's example 1**:

1. Identify the current authoritative provider — by matching ≥1 NS against `NS_PROVIDER_PATTERNS` from research (Cloudflare = `*.ns.cloudflare.com`, IONOS = `ns*.ui-dns.{com,net,org,de,biz,info}`, etc.).
2. The "host provider" is the one whose pattern matches the **majority** of the NS RRset OR is the `TARGET`'s explicit `provider/` prefix.
3. For each remaining NS, attempt to match against any other entry in `NS_PROVIDER_PATTERNS`. Any NS that matches a *different* provider is flagged.

Severity: WARNING. Fixability: AUTO_INTERACTIVE — propose `provider.delete_record` on each leftover NS. With `--yes`, applies without prompt. Example: zone hosted at Cloudflare contains `ns1045.ui-dns.com`, `ns1045.ui-dns.org`, `ns1045.ui-dns.de`, `ns1045.ui-dns.biz` → 4 findings, one fix-action each, batched into one Cloudflare API call cluster.

```python
@register
class LeftoverNSCheck(Check):
    id = "MIGRATE.leftover_ns"
    category = "migration"

    def run(self, ctx):
        ns_rrset = ctx.zone.find_rrset(ctx.zone.origin, dns.rdatatype.NS)
        # identify host provider
        host = None
        for ns in ns_rrset:
            target = str(ns.target).lower().rstrip(".")
            for prov, pat in NS_PROVIDER_PATTERNS.items():
                if re.match(pat, target):
                    host = host or prov
                    break
        if not host and ctx.target.provider:
            host = ctx.target.provider.canonical_name
        if not host:
            return

        for ns in ns_rrset:
            target = str(ns.target).lower().rstrip(".")
            for prov, pat in NS_PROVIDER_PATTERNS.items():
                if prov != host and re.match(pat, target):
                    yield Finding(
                        check_id=self.id,
                        severity=Severity.WARNING,
                        fixability=Fixability.AUTO_INTERACTIVE,
                        title=f"Leftover {prov} NS in {host}-hosted zone",
                        description=(
                            f"Apex NS RRset contains {target} which matches the "
                            f"{prov} nameserver pattern, but this zone is hosted "
                            f"at {host}. This NS record was likely left over "
                            f"after a migration."),
                        evidence={"ns_target": target, "host_provider": host,
                                  "matched_provider": prov,
                                  "all_ns": [str(r.target) for r in ns_rrset]},
                        rfc_refs=("RFC 1034 §4.1",),
                        fix_actions=(FixAction(
                            op="delete",
                            target=RecordRef(
                                zone=str(ctx.zone.origin),
                                name=str(ctx.zone.origin),
                                rtype="NS",
                                rdata=(target,)),
                            requires_confirmation=True),))
                    break
```

**C4 `DELEGATION.glue_missing`** — In-domain NS lacks A/AAAA glue at parent (RFC 9471). Detection: query the parent zone's NS for the referral; inspect additional section; assert glue present for every in-bailiwick NS. Severity: ERROR. Fix: MANUAL_ONLY (registrar interaction).

**C5 `DELEGATION.glue_mismatch`** — Parent-side glue A/AAAA differs from child-side authoritative A/AAAA. Severity: ERROR. Fix: MANUAL_ONLY (registrar).

**C6 `DELEGATION.under_two_ns`** — Fewer than 2 NS at apex (RFC 2182). Severity: WARNING. Fix: MANUAL_ONLY.

**C7 `DELEGATION.no_as_diversity`** — All NS resolve to IPs in one ASN (Team Cymru `origin.asn.cymru.com` lookup). Severity: HINT. Fix: MANUAL_ONLY.

**C8 `DELEGATION.no_subnet_diversity`** — All NS in single /24 IPv4 or /48 IPv6. Severity: HINT. Fix: MANUAL_ONLY.

**C9 `DELEGATION.no_geographic_diversity`** — All NS IPs geolocate to same country/region (best-effort using free GeoIP service). Severity: HINT. Fix: MANUAL_ONLY.

**C10 `NS.serial_inconsistent`** — SOA serials across NSes differ beyond a tolerance window. Severity: WARNING. Fix: MANUAL_ONLY.

**C11 `NS.open_recursion`** — Authoritative NS answers a recursive query for an unrelated domain. Detection: query NS for an unrelated name (`donazopy-recursion-test.invalid`) with RD bit; recursion-allowed if response is not REFUSED and contains recursion-available bit. Severity: WARNING. Fix: MANUAL_ONLY.

**C12 `NS.axfr_open`** — AXFR succeeds from public internet. Severity: WARNING. Fix: MANUAL_ONLY.

**C13 `NS.ipv4_unreachable`** / **C14 `NS.ipv6_unreachable`** — UDP/53 or TCP/53 timeout. Severity: ERROR if all NS unreachable on a family, WARNING if some. Fix: MANUAL_ONLY.

**C15 `NS.no_ipv6_for_any`** — No NS has AAAA. Severity: INFO. Fix: MANUAL_ONLY.

**C16 `NS.fcrdns_missing`** — NS IP has no PTR or PTR doesn't match NS name. Severity: INFO. Fix: MANUAL_ONLY.

### Category D — DNSSEC

**D1 `DNSSEC.unsigned_but_ds_present`** — DS at parent, no DNSKEY at child. CRITICAL outage. Fix: MANUAL_ONLY (registrar/parent).

**D2 `DNSSEC.signed_no_ds`** — DNSKEY at child, no DS at parent → zone treated as Insecure. Severity: WARNING. Fix: AUTO_INTERACTIVE if `registrar.read_nameservers` indicates DS-submission support (then suggest reading CDS/CDNSKEY and posting to registrar), else MANUAL_ONLY.

**D3 `DNSSEC.ds_hash_mismatch`** — DS digest doesn't match any child DNSKEY. CRITICAL. Fix: MANUAL_ONLY.

**D4 `DNSSEC.weak_algorithm_signing`** — Active signing key uses algorithm 1/3/5/6/7 (RFC 8624 / 9904). Severity: WARNING. Fix: MANUAL_ONLY — rollover guidance.

**D5 `DNSSEC.weak_rsa_keylength`** — RSA DNSKEY <2048 bits. Severity: WARNING. Fix: MANUAL_ONLY.

**D6 `DNSSEC.algorithm_completeness`** — RFC 6840 §5.11 — for every algorithm in DNSKEY RRset, every RRset must have at least one RRSIG of that algorithm. Detection: enumerate DNSKEY algorithms, AXFR or walk zone, validate each RRset. Severity: ERROR. Fix: MANUAL_ONLY.

**D7 `DNSSEC.rrsig_expired`** — Any RRSIG `Expiration < now`. CRITICAL. Fix: MANUAL_ONLY.

**D8 `DNSSEC.rrsig_near_expiry`** — `Expiration - now < 3 days`. Severity: WARNING. Fix: MANUAL_ONLY.

**D9 `DNSSEC.rrsig_inception_future`** — Clock skew or future-dated signature. Severity: WARNING. Fix: MANUAL_ONLY.

**D10 `DNSSEC.rrsig_validity_too_long`** — `Expiration - Inception > 90 days`. Severity: HINT. Fix: MANUAL_ONLY.

**D11 `DNSSEC.nsec3_iterations_nonzero`** — NSEC3PARAM iterations ≠ 0 (RFC 9276). Severity: WARNING. Fix: MANUAL_ONLY — provider-specific re-signing.

**D12 `DNSSEC.nsec3_salt_nonempty`** — NSEC3PARAM salt length > 0. Severity: HINT. Fix: MANUAL_ONLY.

**D13 `DNSSEC.nsec3_opt_out_unwarranted`** — Opt-out flag set on a small zone (heuristic: <10000 records). Severity: HINT. Fix: MANUAL_ONLY.

**D14 `DNSSEC.no_denial_records`** — Neither NSEC nor NSEC3 present in a signed zone. Severity: ERROR. Fix: MANUAL_ONLY.

**D15 `DNSSEC.ds_sha1_only`** — Only SHA-1 DS digest at parent (RFC 8624 says MUST NOT generate). Severity: WARNING. Fix: MANUAL_ONLY (registrar).

**D16 `DNSSEC.cds_inconsistent`** — CDS / CDNSKEY records don't match published DNSKEY (RFC 7344). Severity: WARNING. Fix: MANUAL_ONLY.

**D17 `DNSSEC.chain_validation`** — Full chain validation via dnspython `dns.dnssec.validate` against root trust anchor. Severity: CRITICAL on bogus. Fix: MANUAL_ONLY.

### Category E — CAA

**E1 `CAA.missing_at_apex`** — No CAA at the apex, none found via tree-walk. Severity: INFO. Fix: AUTO_DEFAULTS. Default: query crt.sh for current issuers of the domain, build a CAA RRset that permits each detected CA plus Let's Encrypt; add `0 iodef "mailto:security@<domain>"` if `security@` mailbox exists (best-effort MX check), else omit iodef.

**E2 `CAA.conflicts_with_issued_cert`** — CT-log query of `<domain>` returns an active cert from issuer X, but CAA `issue` doesn't include X. Severity: ERROR. Fix: AUTO_INTERACTIVE — propose adding X.

**E3 `CAA.permissive_alongside_restrictive`** — Pattern documented as "NotCVE-2026-0001" — a record `0 issue "letsencrypt.org"` (permissive — any account) coexists with `0 issue "letsencrypt.org; accounturi=https://..."` (restrictive). The permissive one nullifies the restriction. Severity: WARNING. Fix: AUTO_INTERACTIVE — remove the permissive one.

**E4 `CAA.iodef_invalid`** — iodef URL scheme ∉ {mailto, http, https}. Severity: WARNING. Fix: AUTO_INTERACTIVE.

**E5 `CAA.issuer_typo`** — `issue "lets-encrypt.org"`, `"letsencrypt.com"`, `"digicert.net"`, etc. — match each `issue` value against canonical CA-identifier list (letsencrypt.org, pki.goog, digicert.com, sectigo.com, comodoca.com, globalsign.com, amazon.com, amazontrust.com, ssl.com, entrust.net, buypass.com, zerossl.com, actalis.it, certum.pl, harica.gr). Severity: ERROR. Fix: AUTO_INTERACTIVE — propose typo correction.

**E6 `CAA.critical_flag_on_standard_tag`** — Flag bit 128 set on `issue`/`issuewild`/`iodef`. Severity: WARNING. Fix: AUTO_INTERACTIVE — clear bit 128.

**E7 `CAA.empty_issue_blocks_all`** — `issue ";"` alone — blocks all issuance, likely a typo. Severity: WARNING. Fix: AUTO_INTERACTIVE — prompt user.

**E8 `CAA.dnssec_required_but_unsigned`** — CAA exists but zone is not DNSSEC-signed; CA/B Forum allows but CAA cannot be relied on for security against MITM. Severity: HINT. Fix: MANUAL_ONLY.

### Category F — Web/HTTPS-adjacent

**F1 `WEB.https_record_missing_alpn`** — HTTPS RR exists but `alpn` SvcParam absent. Severity: HINT. Fix: AUTO_INTERACTIVE — add `alpn=h3,h2`.

**F2 `WEB.https_record_no_default_alpn_without_alpn`** — `no-default-alpn` set without any `alpn` (no protocol usable). Severity: ERROR. Fix: AUTO_INTERACTIVE — remove `no-default-alpn` or add `alpn=`.

**F3 `WEB.https_ip_hints_disagree_a_aaaa`** — `ipv4hint`/`ipv6hint` IPs not in actual A/AAAA RRsets. Severity: WARNING. Fix: AUTO_INTERACTIVE — sync hints.

**F4 `WEB.www_missing`** — A/AAAA at apex but no `www` (or `www` doesn't resolve). Severity: INFO. Fix: AUTO_INTERACTIVE — create `www CNAME <apex>` or A records mirroring apex.

**F5 `WEB.tls_cert_invalid`** — HTTPS-fetch apex `:443` and `www:443`, validate cert chain, name match, expiry. Severity: ERROR. Fix: MANUAL_ONLY.

**F6 `WEB.http_no_https_redirect`** — `http://<apex>` returns 200 instead of 301/302/308 to https. Severity: WARNING. Fix: MANUAL_ONLY (out-of-DNS).

**F7 `WEB.hsts_missing`** — Live HTTPS GET; no `Strict-Transport-Security` header. Severity: INFO. Fix: MANUAL_ONLY.

**F8 `WEB.dname_unexpected`** — DNAME at apex coexists with NS (RFC 6672 has subtle interactions). Severity: INFO. Fix: MANUAL_ONLY.

### Category G — Service discovery / well-known leftovers

**G1 `WK.acme_challenge_leftover`** — `_acme-challenge.<name>` TXT exists and is >30 days old (heuristic by recent zone-edit time). Severity: HINT. Fix: AUTO_INTERACTIVE — delete.

**G2 `WK.domainconnect_orphan`** — `_domainconnect` CNAME present, pointing to `_domainconnect.1and1.com` or `_domainconnect.<provider>.com`, but zone is hosted elsewhere. Severity: HINT. Fix: AUTO_INTERACTIVE — delete.

**G3 `WK.srv_dead_target`** — `_kerberos`, `_ldap`, `_xmpp`, `_sip`, `_minecraft`, etc. SRV with non-resolving or non-connectable target. Severity: WARNING. Fix: AUTO_INTERACTIVE — delete.

### Category H — Live / external

**H1 `LIVE.resolver_consistency`** — Query A/AAAA/MX/NS/TXT/CAA/DS/DNSKEY at 1.1.1.1, 8.8.8.8, 9.9.9.9, and the zone's own NS; diff the answers. Severity: WARNING on mismatch. Fix: MANUAL_ONLY (propagation).

**H2 `LIVE.fcrdns_mx`** — Each MX IP must have PTR resolving back to the MX hostname (forward-confirmed reverse DNS). Severity: WARNING. Fix: MANUAL_ONLY.

**H3 `LIVE.mx_dnsbl`** — Each MX A IP looked up against Spamhaus ZEN, Barracuda, SORBS-DUL, SpamCop. If any list answers ≠ NXDOMAIN → flag. Severity: ERROR. Fix: MANUAL_ONLY.

**H4 `LIVE.https_reachable`** — Each A/AAAA at apex and `www` connectable on 443; valid TLS cert with matching SAN. Severity: ERROR if unreachable. Fix: MANUAL_ONLY.

**H5 `LIVE.smtp_starttls`** — Each MX IP connectable on 25 within 10s, supports STARTTLS, presents trusted cert matching MX hostname. Severity: WARNING/ERROR depending on MTA-STS mode. Fix: MANUAL_ONLY.

**H6 `LIVE.mta_sts_fetch`** — Full live verification (described in B51).

**H7 `LIVE.bimi_vmc_fetch`** — Full live verification (described in B71/B72).

**H8 `LIVE.takeover_probe`** — Described in A15.

**H9 `LIVE.ct_log_unauthorized_issuer`** — Described in E2.

**H10 `LIVE.dnssec_chain`** — Full DNSSEC chain validation from root trust anchor.

### Category I — RFC compliance / format
Already covered: A32–A38, plus per-record numeric range checks (MX preference, SRV uint16 fields, IPv6 RFC 5952 canonicalization).

### Category J — Provider-migration heuristics

**J1 `MIGRATE.leftover_ns`** — see C3.

**J2 `MIGRATE.stale_verification_token`** — TXT records matching `TXT_VERIFICATION_PATTERNS` whose corresponding service is no longer in use. "No longer in use" is best-effort: e.g., a `google-site-verification=` exists but Google Workspace MX (`*.aspmx.l.google.com`) is absent and SPF doesn't include `_spf.google.com`. Severity: HINT. Fix: AUTO_INTERACTIVE — propose deletion; never auto-delete without confirmation since some verifications are required even when the service appears unused.

**J3 `MIGRATE.parking_artifact`** — A records in parking ranges (GoDaddy `3.33.130.190` / `15.197.148.33`, IONOS `217.160.0.0/16`, Sedo `64.190.62.x`, Afternic `91.195.241.x`, loopback `127.0.0.1`, `0.0.0.0`) coexisting with real records. Severity: WARNING. Fix: AUTO_INTERACTIVE — delete the parking record.

**J4 `MIGRATE.stale_dkim_selector`** — `<selector>._domainkey.<domain>` exists, value parseable, but `selector` corresponds to a known ESP whose SPF include is missing from current SPF (e.g., `mandrill._domainkey` exists but no `servers.mcsv.net` include or current Mailchimp activity). Severity: HINT. Fix: AUTO_INTERACTIVE.

**J5 `MIGRATE.txt_escape_quote_duplicate`** — see A2. **This is the user's example 2** in canonical form: TXT value `v=spf1 include:_spf-us.ionos.com ~all` and TXT value `\"v=spf1 include:_spf-us.ionos.com ~all\"` co-exist; the second has surrounding `\"` plus backslash-escapes — clearly a re-import artifact. The deduplicator normalizes both, sees them equal, keeps the cleaner one.

### Category K — Auto-fix taxonomy summary
Per-Finding, `fixability` is set as described above. The FixPlanner groups by Fixability and respects the user's confirmation policy:
- `AUTO_SAFE`: apply without prompt, even without `--yes`.
- `AUTO_DEFAULTS`: show the default record diff and prompt unless `--yes`.
- `AUTO_INTERACTIVE`: always prompt unless `--yes`.
- `MANUAL_ONLY`: never auto-applied; printed to output, suggested commands shown.

### Category L — Severity mapping summary
Used consistently: HINT for style, INFO for missing-best-practice, WARNING for likely-misconfig, ERROR for protocol violation, CRITICAL for outage-class. `--strict-rfc` upgrades all protocol-violation findings (those carrying any `rfc_refs`) to ERROR.

## 5. Auto-fix engine design

### 5.1 Planning
The FixPlanner constructs a directed graph of FixActions with these edges: (a) create-before-delete when an old record is being replaced by a new one and atomicity matters (e.g., SPF merge); (b) per-provider serialization (most provider APIs do not support transactions, so we group operations by provider and order them within each group); (c) DNS dependency (e.g., assign apex NS at registrar only AFTER child zone exists at the new provider — though `donazopy doctor` typically operates on already-hosted zones so this rarely arises). Cycles → flagged and the user is asked.

### 5.2 Dry-run
`--fix --dry-run` prints the plan with a unified-diff representation of every record change. Each FixAction renders as:

```
  CHANGE: example.com. CNAME @ (apex)
- example.com.       300 IN CNAME target.cdn.example.net.
+ example.com.       300 IN A     192.0.2.10
+ example.com.       300 IN AAAA  2001:db8::10
  reason: A5 cname_at_apex (ERROR)
```

### 5.3 Prompting
Each non-`AUTO_SAFE` FixAction shows:
- The finding title and severity (colored).
- A diff block (as above).
- The prompt `Apply? [y/N/a/q/?]` where `a` = all-remaining-yes, `q` = quit, `?` = show the full Finding description.

### 5.4 Transactional semantics
Provider APIs are mostly non-transactional. The engine implements "best-effort atomic" by:
- Issuing all `create` operations first (so a partial failure leaves the zone over-rather-than-under-recorded).
- Then `modify` operations.
- Then `delete` operations last.
- On any error, abort remaining actions, write the journal entry indicating the failure point, and exit non-zero. The user can then `donazopy doctor TARGET --undo <run-id>` to reverse what was already applied.

### 5.5 Idempotency
Every FixAction includes the exact prior rdata (`rollback_state` field). The engine reads the current state before applying — if it doesn't match `prior_state` (someone else changed the zone since planning), the action is skipped with a WARNING, not aborted. This makes re-running `--fix` safe.

### 5.6 Rollback
`donazopy doctor TARGET --undo <run-id>` reads `~/.donazopy/journal/<run-id>.jsonl` and applies the inverse of each FixAction in reverse order.

### 5.7 Rate-limiting
Each provider's API client maintains a token bucket. Cloudflare = 1200 req/5min/user → 4 req/s sustained. IONOS = ~100 req/min. GoDaddy = 60 req/min/IP. Joker DMAPI = sequential session-bound. The engine respects these and uses exponential backoff on 429/5xx with jitter.

## 6. Live-lookup subsystem

### 6.1 Resolver stack
A `LiveLookupCache` wraps `dns.asyncresolver.Resolver` instances pinned to three resolvers (1.1.1.1, 8.8.8.8, 9.9.9.9 by default; configurable). For comparison queries, all three are issued in parallel and answers diffed. The cache key is `(qname, rdtype, resolver_ip)`; TTLs are honored within a single run unless `--no-cache`.

### 6.2 Parallelism
Default `--workers 50`. The cache uses `asyncio.Semaphore(50)`. Each Check that issues live lookups awaits results from the cache, which dedupes concurrent in-flight lookups via `asyncio.Future` sharing.

### 6.3 Timeouts
Default 5s per query (`dns.resolver.Resolver.timeout = 5, lifetime = 10`). HTTPS fetches use httpx with `timeout=httpx.Timeout(connect=5, read=10, write=10, pool=5)`. SMTP STARTTLS probes time out at 10s.

### 6.4 DNSSEC validation
When `--live` and the zone is signed, the cache uses `dns.dnssec.validate` to validate every RRset against the chain to the root. Root trust anchor is loaded from the IANA-published `root-anchors.xml` (bundled and refreshable).

### 6.5 Cached probes
HTTPS-fetch results, SMTP banners, takeover-fingerprint matches, CT-log queries to crt.sh, and DNSBL queries cache to `~/.donazopy/doctor-cache/<sha256(probe_key)>.json` with a 24-hour TTL. `--no-cache` disables.

### 6.6 Optional probes
`--include-dnsbl`, `--include-ct-logs`, `--include-takeover`, `--include-tls-scan` toggle the slower external probes individually. Default `--profile full` enables all of them.

## 7. Required additions to donazopy provider API surface

The existing `DNSHostingProvider` ABC exposes `list_records`, `import_zone`, `export_zone`, `create_zone`, `delete_all_records`, `list_zones`. The doctor's fix engine needs finer-grained CRUD. Required additions:

```python
class DNSHostingProvider(Protocol):
    # existing
    def list_records(self, zone: str) -> list[Record]: ...
    def import_zone(self, zone: str, records: list[Record]) -> None: ...
    def export_zone(self, zone: str) -> str: ...
    def create_zone(self, zone: str) -> None: ...
    def delete_all_records(self, zone: str) -> None: ...
    def list_zones(self) -> list[str]: ...

    # NEW — required for doctor --fix
    def create_record(self, zone: str, record: Record) -> RecordId: ...
    def delete_record(self, zone: str, record_id: RecordId) -> None: ...
    def update_record(self, zone: str, record_id: RecordId, new: Record) -> None: ...
    def replace_rrset(self, zone: str, name: str, rtype: str,
                       new_rdata: list[str], ttl: int) -> None: ...

    # NEW — capability discovery
    @property
    def capabilities(self) -> ProviderCapabilities: ...

class ProviderCapabilities(TypedDict):
    supports_create_record: bool
    supports_delete_record: bool
    supports_update_record: bool
    supports_aname_alias: bool          # for apex CNAME workaround
    supports_https_svcb: bool
    supports_caa: bool
    supports_dnssec: bool
    supports_dns_record_comments: bool  # Cloudflare has comments
    rate_limit_per_minute: int
    txt_quoting_style: Literal["raw", "quoted", "auto"]
    auto_chunks_long_txt: bool
```

Per-provider implementation notes:

**Cloudflare**: API is record-level (`POST /zones/{id}/dns_records`); `txt_quoting_style="raw"`, `auto_chunks_long_txt=True`. Returns stable record IDs.

**IONOS**: Cloud DNS API supports `PATCH /zones/{zoneId}/records/{recordId}`. The current donazopy IONOS backend uses bulk-replace on PUT to `/zones/{id}`; the doctor needs the patch endpoint or it falls back to read-modify-write of the full RRset.

**GoDaddy**: API is RRset-level (`PUT /v1/domains/{domain}/records/{type}/{name}`). `replace_rrset` maps cleanly; `create_record` and `delete_record` are emulated by reading the current RRset, modifying, and writing back.

**Joker.com**: DMAPI is text-protocol; record updates are issued via `dns-zone` (full zone replace). The doctor uses `replace_rrset` semantics: it reads the zone, edits in-memory, and writes back atomically.

Capability flags let the doctor degrade gracefully — if a provider lacks `supports_caa`, CAA-adding fixes are downgraded to MANUAL_ONLY with the message "your provider does not support CAA records; migrate or contact provider."

A `Record` dataclass:
```python
@dataclass
class Record:
    name: str            # FQDN
    rtype: str           # "TXT","NS",...
    ttl: int
    rdata: tuple[str,...]
    record_id: Optional[str] = None   # provider-assigned
    raw_provider_data: dict[str,Any] = field(default_factory=dict)
```

## 8. Output formats and exit codes

### 8.1 Text
Default. TTY-aware coloring (`rich`). Findings grouped by severity then category. Each finding renders title, severity badge, location (the offending records), description, RFC refs, and "fix" block.

### 8.2 JSON
Stable schema versioned `donazopy.doctor.v1`:
```json
{
  "schema_version": "donazopy.doctor.v1",
  "target": "cloudflare/example.com",
  "ran_at": "2026-05-13T12:34:56Z",
  "summary": {"critical":0,"error":2,"warning":5,"info":3,"hint":1},
  "findings": [
    { "check_id":"MIGRATE.leftover_ns", "severity":"warning",
      "fixability":"auto_interactive",
      "title":"...", "description":"...",
      "evidence":{...}, "rfc_refs":[...], "fix_actions":[...] }
  ],
  "applied_fixes": [...],
  "skipped_fixes": [...]
}
```

### 8.3 SARIF
For CI integration (GitHub Code Scanning). Each Finding → a `result` object with `ruleId = check_id`, `level` mapped from severity.

### 8.4 Markdown
For human-readable PR comments / runbooks.

### 8.5 Exit codes
As §2.3.

## 9. Testing strategy

### 9.1 Fixture zones
Under `tests/fixtures/zones/` — one BIND file per check ID with at least one positive (offending) variant and one clean variant: `MIGRATE.leftover_ns.bad.zone`, `MIGRATE.leftover_ns.good.zone`. The bad variant contains a Cloudflare-hosted zone with IONOS NS leftovers; the test asserts exactly one finding with the right title.

### 9.2 Golden-output tests
For each fixture, store the expected JSON output in `tests/golden/<fixture>.json`. Tests run `donazopy doctor --report json` against the fixture, then assert equality. Updates require an explicit `--update-golden` flag.

### 9.3 Mock provider
`tests/mock_provider.py` implements the full `DNSHostingProvider` against an in-memory dict. The fix engine is tested against this provider; assertions check the final dict state.

### 9.4 Live-check tests
A separate suite `tests/live/` requires a sandbox domain (set via `DONAZOPY_TEST_DOMAIN`) and is opt-in. CI runs only the offline suite by default.

### 9.5 Property tests
For deduplication and normalization (A1–A4): hypothesis-generated TXT variants asserted to all normalize to the same value.

### 9.6 RFC-conformance tests
Each detection algorithm has a unit test citing the RFC paragraph it implements, with the example records taken from the RFC where available.

## 10. Phased implementation roadmap

**Phase 1 — MVP (2–3 weeks).** Goal: deliver the two user-mentioned cases. Checks: A1, A2, A3, A4, MIGRATE.leftover_ns (C3/J1), and the supporting infra (Check registry, Finding/FixAction dataclasses, FixPlanner skeleton). Text output only. `--fix --yes` only — no interactive prompting yet. New provider API methods: `create_record`, `delete_record`. Cloudflare backend first.

**Phase 2 — Zone hygiene complete (2 weeks).** All Category A and I checks. JSON output. Interactive prompting. IONOS and GoDaddy backends finished.

**Phase 3 — Email auth complete (2 weeks).** Categories B (SPF + DKIM + DMARC). DKIM-selector wordlist seeded from prove.email and the research-supplied catalog. Live mode introduced (Phase 6 components below) but limited to record presence/syntax probes, no SMTP. SARIF and Markdown output.

**Phase 4 — Live subsystem (2 weeks).** Concurrency, caching, multi-resolver consistency (H1, H10), takeover (A15/H8), CT logs (E2/H9), DNSBL (H3), HTTPS reachability (H4), STARTTLS (H5). Add `--no-live`.

**Phase 5 — DNSSEC + CAA + glue (1–2 weeks).** Categories D, E, C4–C5. Joker backend finished.

**Phase 6 — MTA-STS, TLS-RPT, BIMI, DANE (1 week).** Categories B50–B92. Live HTTPS for MTA-STS policy and BIMI assets.

**Phase 7 — Web/HTTPS-adjacent + service discovery + remaining migration heuristics (1 week).** Categories F, G, J2–J5.

**Phase 8 — Polish (1 week).** `--undo`, registrar integration for parent-NS fixes, custom check plugins, profiles, configuration file (`~/.donazopy/doctor.toml`), suppression file (`.donazopy-doctor-ignore`).

## 11. References and prior-art table

| Category | Tool / Spec | Used for |
|---|---|---|
| Test taxonomy | Zonemaster (IIS/AFNIC) Test Case IDs | Severity model, NAMESERVER/DELEGATION/CONSISTENCY/SYNTAX/ZONE test families |
| DNSSEC | DNSViz | Chain validation, NSEC3 hygiene UI patterns |
| Holistic audit | internet.nl | Mail/Web split, REQUIRED/RECOMMENDED tiering |
| Propagation | DNSChecker.org | Multi-resolver consistency design |
| Comprehensive mail | MXToolbox, mail-tester, dmarcian, Postmark | DMARC report consumption, deliverability checks |
| MTA-STS | CheckTLS | Live HTTPS fetch + cert validation flow |
| Web TLS | SSL Labs | TLS protocol/cipher grading conventions |
| Subdomain takeover | can-i-take-over-xyz, subjack, subzy, nuclei templates | Fingerprint JSON consumption |
| CAA | caa-cli, jamescun/caa, sslmate | Tag parsing, tree-walk algorithm |
| Zone validation | named-checkzone, ldns-verify-zone | RRset duplicate detection, MX/SRV/NS-as-CNAME rules |
| RFC corpus | RFC 1034, 1035, 1912, 2181, 2182, 2308, 4592, 5321, 5891, 6376, 6698, 6761, 6840, 7208, 7489, 7505, 7672, 8461, 8460, 8624, 8657, 8659, 9276, 9460, 9471, 9499, 9904 | Detection algorithms throughout |
| Python | dnspython 2.7+, cryptography 42+, httpx 0.27+, idna 3.7+, tldextract 5.1+, confusable_homoglyphs 3.3+, pydantic 2.7+, typer 0.12+, rich 13.7+ | Implementation stack |
| Fingerprints | NetSPI Resolve-DnsDomainValidationToken.ps1, prove.email DKIM archive, indianajson/cloudflare-nameservers, EdOverflow/can-i-take-over-xyz/fingerprints.json | Provider/service fingerprint databases |
| CT logs | crt.sh JSON API, SSLMate Cert Spotter | CAA cross-check, mis-issuance detection |

This specification is comprehensive enough for direct implementation by a senior engineer. The two user-motivating examples are first-class citizens in the catalog as `MIGRATE.leftover_ns` (with the full detection algorithm in §4 Category C/J) and `ZONE.duplicate_txt_semantic`/`ZONE.txt_escape_artifacts` (Category A1–A4), with concrete Python detection code and FixAction definitions shown. The phased roadmap delivers those two cases as the MVP within 2–3 weeks while laying the foundation for all 160+ catalogued checks.