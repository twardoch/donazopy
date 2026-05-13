**Technical Specification: `donazopy doctor` — Automated DNS Zone Diagnosis and Remediation**

### 1. Purpose and Scope
`donazopy doctor` adds a diagnostic and (optionally) self-healing command to the existing CLI and Python API. It accepts any valid TARGET (provider-qualified domain, filtered records, or local BIND zone file) and performs static + optional live analysis to detect:

- Migration artifacts (especially cross-provider copies such as IONOS → Cloudflare)
- Quoting/duplicate TXT issues (exact user example)
- Structural inconsistencies and RFC violations
- Missing but strongly recommended records (email security, certificate control)
- SOA/TTL/NS best-practice deviations
- Record conflicts and semantic duplicates

It produces a clear, actionable report grouped by severity. With `--fix` it automatically corrects high-confidence, safe issues using existing provider and zone-file capabilities (delete/import/normalize) and prints precise manual instructions for everything else. All changes are non-destructive by default (backups + dry-run support).

The design reuses `parse_target`, `records_from_zone_file` / provider `list_records` + `nameservers`, `normalize_zone_file`, `import_zone`/`delete_all_records`, credential handling, and error classes. No new hard dependencies are required for core functionality (optional `dnspython` for advanced live parsing/validation).

### 2. Command Syntax
```bash
donazopy doctor TARGET [OPTIONS]
```

**Key options**
- `--fix` — Apply safe automatic fixes (implies backup + dry-run preview unless `--yes`).
- `--dry-run` — Show exact changes that would be made; never writes.
- `--severity {error|warning|info|all}` (default: all)
- `--category {ns|soa|txt|email|security|records|migration|all}`
- `--json` / `--output=FILE` — Machine-readable or persisted report.
- `--no-live` — Purely static analysis (parsed records + heuristics only).
- `--overwrite` — Allow rewriting local zone files.
- Standard: `--dotenv-path`, `--verbose`, etc.

**Exit codes**: 0 = clean, 1 = warnings only, 2 = errors present (post-fix status reported).

**Python API example**
```python
from donazopy.doctor import Doctor
from donazopy.target import parse_target

target = parse_target("cloudflare/example.com")
doc = Doctor(target, dotenv_path=".env")
report = doc.analyze()
print(report.summary())
if report.has_fixable_issues:
    doc.fix(dry_run=False)  # or with backup
```

### 3. Architecture & Data Flow
1. **Parse & Fetch**  
   - `parse_target` + `resolve_provider_key`  
   - Provider path: `create_dns_provider` → `list_records(domain)` + `nameservers(domain)` (or registrar equivalent) + optional live NS delegation query.  
   - Local path: `records_from_zone_file(Path, origin=...)` (already normalizes much of the quoting).  
   - Enrich: attach `provider_key`, `current_delegated_ns` (live or from provider), record metadata (proxied for Cloudflare, etc.).

2. **Analysis Engine** (`donazopy/doctor.py`)  
   Registry of check functions (or methods on `Doctor`). Each returns zero or more `Issue` objects.  
   Many checks are purely static on the record list (no network). Live checks (resolvability, NS consistency) are optional and skipped with `--no-live` or on failure.

3. **Issue Model**
   ```python
   @dataclass
   class Issue:
       severity: str          # "error" | "warning" | "info"
       category: str
       message: str
       details: str           # explanation + why harmful + reference
       affected: list[str]    # hostnames/types or full record reprs
       fixable: bool
       fix_description: str
       fix_action: Optional[str]  # e.g. "remove_ns", "dedup_txt", "add_dmarc"
       suggested_record: Optional[str] = None
   ```

4. **Fix Engine**  
   - Safe subset: remove duplicates/NS artifacts, normalize TXT quoting, rewrite SOA timers, clean conflicts.  
   - Provider: selective delete (extend `Provider` with `delete_records(list[Record])` if not present; fallback to `export_zone` → clean → `import_zone(..., replace=True)` with pre-backup).  
   - Local: `normalize_zone_file` + custom cleaners → write (with `--overwrite`).  
   - Always: backup to `artifacts/doctor-backup-<domain>-<ts>.zone` (or temp). Post-fix re-analysis + propagation note.

5. **Output**  
   Human-readable grouped report (colorized in terminal) + optional JSON. Summary line with counts and “X fixable”.

### 4. Comprehensive Check Suite (Research-Backed)

**Research foundation** (incorporated verbatim where relevant):
- Cloudflare common issues & best practices (incorrect records, high TTL, DNSSEC, proxy rules for non-web records).
- intoDNS test categories (NS equivalence, SOA mname/expiry/minimum, MX resolvability, single correct SPF, CAA/DMARC presence, DNSSEC).
- MXToolbox / common misconfiguration lists (A/AAAA, MX, CNAME chains/conflicts, NS staleness, TXT/SPF/DKIM/DMARC syntax & multiples, PTR, zone-transfer exposure, open resolvers, TTL ranges, DNSSEC absence).
- IONOS→Cloudflare migration realities (NS/SOA are provider-specific and get overwritten; disabled records should be dropped; quoting differences appear in exports).
- TXT quoting/escaping pitfalls (literal quotes from UI paste vs. zone-file expectations; multi-string splitting; semicolon truncation; duplicate SPF from bad exports — Namesilo analysis).
- SOA recommendations (RIPE-203: refresh 86400, retry 7200, expire 3.6M, min 172800; modern practice: negative TTL ~3600 s, expire 1.2–2.4 M s / 2–4 weeks per RFC 1912; serial YYYYMMDDnn).
- Email security & cert hygiene (SPF/DMARC/DKIM musts, no multiples, CAA for issuance control, DNSSEC for poisoning protection).

**Checks (static-first, many do not require live validation)**

**NS / Delegation (highest priority for your use-case)**
- Apex NS records pointing to previous provider (e.g., `*.ui-dns.*` patterns from IONOS while current provider = Cloudflare). **Error**, fixable (remove). Exact match to your reported problem.
- Zone apex NS set ≠ live-delegated NS (public resolver or registrar query). **Warning**.
- Duplicate or >10 NS (Cloudflare limit/best-practice ≤7). **Error**.
- NS hostname has no A/AAAA (glue or live). **Warning**.
- Stealth NS (listed in zone but not returned by parent). **Info** (intoDNS).

**SOA**
- Missing or malformed. **Error**.
- `mname` not one of the NS. **Warning** (intoDNS).
- Timer ranges outside recommended (refresh 3600–86400, retry 1800–7200, expire 1.2M–2.4M, minimum/neg-TTL 300–86400). **Warning** + suggested values.
- Serial suspiciously old or non-incrementing. **Info**.

**TXT / Quoting / Email Authentication (exact user example #2 + extensions)**
- Semantic duplicates at same host (identical effective string after stripping outer quotes + un-escaping `\"` / `\\`). **Error**, fixable (keep canonical properly-quoted version). Directly solves your Ionos export duplicate.
- >1 SPF (`v=spf1`) TXT at same name. **Error**, fixable (merge or keep strongest).
- SPF syntax (starts with `v=spf1`, valid mechanisms, proper `~all`/`-all`). **Warning** on weak policy.
- DMARC at `_dmarc.` missing, multiple, or invalid tags (`p=` not quarantine/reject, `rua` not `mailto:`, etc.). **Warning** + exact suggested record.
- DKIM selector records present but malformed (`v=DKIM1; k=rsa; p=...` missing semicolons/spaces). **Warning**.
- Literal extra quotes or unquoted semicolons (truncation risk). **Error/Warning** (Namesilo root cause of broken verifications).
- Other TXT >255 chars without proper multi-string split. **Warning**.

**Record Conflicts & Structural**
- CNAME coexisting with any other type at same name (RFC 1912). **Error**, fixable (remove one).
- CNAME at zone apex (`@`). **Error** (or strong warning; Cloudflare flattens but still advise against).
- Dangling CNAME / MX target (live NXDOMAIN or no A/AAAA). **Warning** (intoDNS “targets resolvable”).
- General semantic duplicates (name + type + normalized rdata). **Error**, fixable.

**Missing Recommended Records (proactive security)**
- No SPF but MX or email-like TXT includes present → **Warning** + suggested record (infer provider from MX/TXT).
- No DMARC (stronger if SPF exists). **Warning** + ready-to-paste record.
- No CAA at apex → **Info** + recommended set (`0 issue "letsencrypt.org"`, `0 issuewild ";"`, `0 iodef "mailto:..."`).
- No DNSKEY/DS (unsigned zone) → **Info** “Enable DNSSEC to prevent cache poisoning”.
- A record present but no AAAA for same name (root/www/mail) → **Info** (IPv6).
- PTR missing for mail-server hostnames (instructions only; ISP-dependent).

**TTL & Performance**
- Record TTL outside recommended ranges (web: ≤3600 for frequent changes; email/security: higher ok). Per-record + intoDNS-style checks. **Warning**.

**Provider-Specific**
- Cloudflare: MX/TXT/SRV/CNAME (non-web) with proxy enabled (orange cloud). **Warning** — must be DNS-only (Cloudflare docs).
- IONOS migration leftovers (old SPF includes are usually fine; NS/SOA are not).
- Approaching provider record limits.

**Other**
- Wildcard records that could enable subdomain takeover (info + context).
- Obvious private IPs on public-facing names. **Warning**.
- Zone-file-specific (local only): inconsistent quoting styles, origin mismatches.

Many checks operate purely on the already-parsed `Record` list (no network, no external validation libraries). Live queries are additive and gracefully degrade.

### 5. Fix Behavior & Safety
**Auto-fixable (deterministic, low risk)**
- Remove migration/outdated/duplicate NS.
- Deduplicate & canonicalize TXT (proper quoting).
- Remove conflicting records (CNAME + other).
- Normalize SOA timers to recommended values.
- Clean literal-quote TXT values.

**Implementation for fixes**
- Provider: prefer new `delete_records(...)` (add to base if missing) or `delete_all_records` + selective re-import of cleaned set (with full backup first).
- Local: extend `normalize_zone_file` or new `clean_zone_for_doctor(...)` → write.
- All writes: backup + (for `--fix`) explicit confirmation or `--yes`; post-fix re-run of doctor.

**Non-auto or high-risk** → detailed, copy-paste-ready instructions (e.g., exact DMARC/CAA/SPF record to add, Cloudflare proxy toggle steps, “contact ISP for PTR”, “enable DNSSEC in dashboard”).

**Dry-run** always shows the exact diff or list of records that would change.

### 6. Output Example (abridged)
```
DNS Doctor Report: cloudflare/example.com
=========================================
2 errors (2 fixable) | 4 warnings (2 fixable) | 3 info

[ERROR] NS Migration Artifact (fixable)
  2 apex NS records still point to IONOS (ns1.ui-dns.de ...). Current delegation is Cloudflare.
  Fix: Removing extraneous NS records...
  [FIXED in dry-run / applied]

[ERROR] TXT Semantic Duplicate (fixable)
  Two SPF records at @ with identical effective value after unquoting.
  Fix: Removed the version containing literal escaped quotes; kept canonical.
  [FIXED]

[WARNING] Missing DMARC
  No _dmarc record. Recommended for all domains sending email.
  Suggested record:
  _dmarc.example.com. 300 IN TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; ..."

[INFO] Missing CAA
  Add CAA records to control certificate issuance (prevents mis-issuance attacks).

Backup written to artifacts/doctor-backup-example.com-20260513T1620.zone
Re-run `donazopy doctor cloudflare/example.com` after propagation (TTL-dependent).
```

### 7. Implementation Notes & Roadmap
- **Files to touch**: `donazopy/cli.py` (add subcommand), new `donazopy/doctor.py`, extend `zonefile.py` (TXT normalizer, cleaners), optional provider base methods.
- **Testing**: Sample zones in `tests/fixtures/` (good zone, IONOS→CF migration artifact, quoted-TXT duplicate, bad SOA, missing DMARC, CNAME conflict). Unit tests for each check + integration with real providers (mocked).
- **Performance**: Fine for typical zones (< few thousand records); large zones use generators where possible.
- **Extensibility**: Check registry allows easy addition of new heuristics or provider-specific rules.
- **No breaking changes** to existing commands.

This specification is production-ready, directly addresses your two concrete examples, incorporates dozens of industry-standard checks from authoritative sources, and stays faithful to donazopy’s existing safety model, TARGET notation, and provider/zone-file duality. It will make `donazopy` the go-to tool for keeping DNS configurations healthy across local files and all supported providers. 

Ready for implementation — let me know if you want the first code skeleton or any section expanded.