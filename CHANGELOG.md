# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog, and this project uses git-tag-derived semantic versions through `hatch-vcs`.

## [Unreleased]

### Fixed — `doctor` no longer crashes on CNAME-and-other-data zones (issue #205 follow-up)

- `analyze_provider_records` / `fix_provider_zone` previously round-tripped provider records through `build_bind_zone` + `records_from_zone_text`, whose strict dnspython parser raises `dns.zonefile.CNAMEAndOtherData` when a CNAME coexists with another type at the same owner — exactly the misconfiguration the doctor needs to *report*. Both functions now use the new `records_from_provider_dicts` converter, which builds `NormalizedRecord` tuples directly from provider dicts (no parser round-trip) and surfaces the conflict as the existing `CNAME_COLLISION` finding.
- `src/donazopy/zonefile.py`: added `records_from_provider_dicts(records, *, origin, default_ttl=3600)` that reuses the existing `_absolute_owner` / `_rdata_for_bind` / `_normalize_soa_content` helpers and never raises on coexistence misconfigurations.

### Added — `donazopy doctor cloudflare/* --fix` iterates every zone on the provider

- Wildcard target (`provider/*` or `provider/`) walks every zone the provider manages, running the same diagnostics (and `--fix`) on each one. The default text output is each zone's report concatenated; `--json` returns `{"reports": [...], "count": N}`.

### Added — `donazopy copy cloudflare/* ionos/` for bulk cross-provider migration

- Wildcard source targets iterate every zone the source provider manages and copy each to the destination provider. The destination target must omit the domain (or use `*`) so each source zone maps to the same-named zone on the destination. The return value is `{"copied": [...per-zone result dicts], "count": N}`.
- Combines with the existing `--clean` / `--replace`, `--skip-ns`, `--skip-types`, and `--create=BOOL` flags: e.g. `donazopy copy cloudflare/* ionos/ --clean --skip-ns` migrates every Cloudflare zone to IONOS, wiping any existing IONOS records first and dropping Cloudflare-managed apex NS from the export.
- Mixing wildcard source with a concrete destination domain raises a clear `TargetError` so the per-zone-name semantics stay explicit.

### Added — `donazopy export cloudflare/*` writes one zone file per domain

- Wildcard export targets iterate every zone the provider manages. The CLI now requires `--output=DIR` for wildcards and writes each zone to `DIR/<domain>.zone` (creating the directory if needed). The return value is a `{domain: path}` map so callers can see exactly what was written.
- For single-domain targets, `--output` may now be a directory: when the path exists as a directory (or is a non-existent path without a suffix), the CLI autogenerates `<output>/<domain>.zone`. Plain file paths still work as before.

### Fixed — `donazopy export --skip-ns` survives unparseable Cloudflare zones

- `filter_zone_text` previously crashed with `ValueError: add() has non-origin SOA` (and a handful of similar dnspython errors) whenever a provider's BIND export included an out-of-zone or otherwise borderline record. Real-world Cloudflare exports for migrated zones triggered this regularly, making `donazopy export --skip-ns cloudflare/<domain>` unusable in bulk loops.
- Added `filter_zone_text_lenient` — a line-based filter that respects `$ORIGIN` / `$TTL` directives and comments, identifies the type column heuristically (looking for `IN` then a known DNS type, with a fallback to any known type token), and drops records whose type matches the skip set. `SOA` is never dropped.
- `filter_zone_text` now wraps its strict parse in `try`/`except` and falls back to the lenient filter on any `ZoneFileError` / `dns.exception.DNSException` / `ValueError`, so `donazopy export ... --skip-ns` and `donazopy copy ... --skip-ns` keep working even on quirky zones.

### Added — `--clean` on `import-zone` and `copy`

- `donazopy import-zone TARGET PATH --clean` calls `delete_all_records` on the target before importing. Use when the imported BIND file is meant to be the complete state of the zone (Cloudflare's BIND import is otherwise additive).
- `donazopy copy SOURCE DEST --clean` is a synonym for `--replace`: wipes the destination zone before importing the copied records.

### Fixed — `doctor --fix` uses granular create/delete on the primary zone too (issue #205)

- `fix_provider_zone` previously did `delete_all_records` + `import_zone` on the zone being fixed. Cloudflare's BIND import strips proxied state and rejects records it cannot parse, so a long zone could be silently slimmed down even when only a couple of records actually needed changing.
- The doctor now detects when the provider exposes both `create_record` and `delete_record` (Cloudflare does) and applies a targeted diff: only the records that need to change are POSTed or DELETEd individually. Proxied state, comments, tags, and any record the BIND parser would have rejected all stay untouched.
- `src/donazopy/providers/cloudflare.py`: added `delete_record(domain, record_id)`.
- For providers without per-record APIs (Joker etc.), the destructive replace remains as a fallback with a clear `delete_all_records` + `import_zone` path.

### Fixed — `doctor --fix` no longer wipes the receiver zone (issue #205 critical regression)

- The previous external-DMARC fix path used `delete_all_records` + `import_zone` on the *receiver* zone. Cloudflare's BIND import endpoint silently drops every proxied state and any record its parser rejects, so receivers like `fontlab.com` were left with only the records that round-tripped cleanly through BIND. The user did not opt into mutating those zones, so the destruction was a critical regression.
- `_ensure_external_dmarc_auth` now uses a single-record-add API: the doctor calls `provider.create_record(receiver, {...})` when present and skips otherwise. The receiver zone is never re-imported in bulk. Backups for receiver zones are no longer needed (and no longer taken).
- `src/donazopy/providers/cloudflare.py`: added `create_record(domain, record)` that POSTs the single record to `/zones/{id}/dns_records`.
- For providers that lack `create_record` (Joker, etc.), the doctor leaves the issue unresolved and prints the suggested record so the user adds it manually.
- Tests: `test_fix_provider_zone_when_external_receiver_on_same_provider_then_authorizes` now asserts the auth record is added via `create_record` and that the receiver is *not* deleted/re-imported; new `test_fix_provider_zone_when_provider_lacks_create_record_then_unfixed` covers the safe fallback; new `test_create_record_when_called_then_posts_single_record` covers the Cloudflare adapter.

### Fixed — `CNAME_COLLISION` / `CNAME_AT_APEX` now auto-fixable (issue #205 follow-up)

- Both checks now set `fixable=True`; `plan_fix_records` resolves them by dropping the CNAME record(s) and keeping every coexisting record. This matches the RFC 1912 §2.4 rule that the CNAME is the violator when other types share the same owner (e.g. an `_dmarc.*` zone with both a CNAME pointing to `dmarc.ionos.com.` and a proper DMARC TXT — the TXT is preserved). Apex CNAMEs are dropped in favor of the mandatory SOA/NS records.

### Added — `doctor --dmarc-email=ADDR` and automatic external-destination authorization (issue #205 follow-up)

- The `doctor` CLI and `analyze_records` / `plan_fix_records` / `analyze_zone_file` / `fix_zone_file` / `analyze_provider_records` / `fix_provider_zone` Python APIs accept a `dmarc_email` parameter; the synthesized DMARC record uses `rua=mailto:<dmarc_email>` instead of the default `dmarc@<zone>`.
- New `DMARC_EXTERNAL_DESTINATION` check scans every existing DMARC record's `rua=mailto:` addresses (and the proposed `--dmarc-email`, if any) and emits one finding per external receiver domain — the authorization record that domain must publish so mail servers will actually deliver reports.
- The provider-aware fix path automatically resolves `DMARC_EXTERNAL_DESTINATION` issues when the receiver domain is hosted on the same provider: `fix_provider_zone` checks `provider.list_zones()`, fetches the receiver zone's records, and adds `"<source>._report._dmarc.<receiver>." IN TXT "v=DMARC1;"` via export → augment → `delete_all_records` + `import_zone` (with a backup written to the same artifacts dir). Receivers on a different provider are left as warnings with the copy-paste record the user must add manually.

### Added — `donazopy doctor` diagnostic command (issue #205)

- `src/donazopy/doctor.py`: new diagnostic engine with an `Issue` model, a `DoctorReport` aggregator, and a registry of static checks that operate on the existing `NormalizedRecord` model so the same engine analyses provider-hosted zones and local BIND files. Default checks: `NS_MIGRATION_ARTIFACT` (apex NS records pointing at a foreign provider — the IONOS-in-Cloudflare case), `TXT_SEMANTIC_DUPLICATE` (TXT entries that collapse to the same payload once outer quotes and `\"` escapes are normalized — the literal-quote duplicate case), `SPF_MULTIPLE`, `SPF_MISSING` (when MX present), `DMARC_MISSING`, `CAA_MISSING`, `CNAME_AT_APEX`, and `CNAME_COLLISION`.
- Auto-fix engine (`plan_fix_records`, `fix_zone_file`, `fix_provider_zone`): removes migration-artifact NS records, keeps the canonical TXT and drops semantic duplicates, and synthesizes a monitoring-only DMARC record. Provider fixes go through export → clean → `delete_all_records` + `import_zone` with a timestamped backup written to `artifacts/doctor-<domain>-<ts>.zone`; local file fixes write `.bak` siblings before rewriting.
- `src/donazopy/cli.py`: new `donazopy doctor TARGET [--fix] [--json] [--output=...]` subcommand that accepts either a provider target or a local zone-file path, returns a human-readable report by default, and emits a JSON dictionary with `--json`.
- Provider-nameserver pattern map covers Cloudflare, IONOS, GoDaddy, AWS, Google, Azure, Namecheap, Joker, DNSimple, Gandi, Porkbun, Vercel, DigitalOcean, Hetzner, Linode, and Vultr — used by the migration-NS check to identify foreign authoritative servers without any live query.
- Tests: `tests/test_doctor.py` exercises every check, the fix planner, the local-file fix path, and the CLI integration.

### Added — operational GoDaddy, IONOS, and Joker provider adapters

- `donazopy providers` (and `status`, target notation, every command) now exposes four operational providers: `cloudflare`, `godaddy`, `ionos`, `joker`.
- `src/donazopy/providers/godaddy.py`: real `GoDaddyProvider` adapter over the GoDaddy API (`api.godaddy.com/v1`, `Authorization: sso-key {key}:{secret}`). Implements `list_zones` (`GET /domains`), `list_records` / `export_zone` (`GET /domains/{d}/records`, folding GoDaddy's separate `MX`/`SRV` priority/weight/port fields back into BIND rdata, synthesizing a SOA since GoDaddy's SOA carries only the primary nameserver), `import_zone` (`PATCH /domains/{d}/records`, never re-sends the GoDaddy-managed SOA), `delete_all_records` (`DELETE /domains/{d}/records/{type}/{name}` per group, keeping apex NS/SOA), `read_nameservers` (`GET /domains/{d}` → `nameServers`), and a real `assign_nameservers` (`PUT /domains/{d}` with `{"nameServers": [...]}`). Credentials: `GODADDY_API_KEY`, `GODADDY_API_SECRET`.
- `src/donazopy/providers/ionos.py`: real `IonosProvider` adapter over the IONOS DNS API (`api.hosting.ionos.com/dns/v1`, `X-API-Key: {public}.{secret}`). Implements `list_zones`, `list_records`, `export_zone` (BIND text), `import_zone` (POSTs records, never re-sends the IONOS-managed SOA), `delete_all_records`, `read_nameservers` (apex NS records). `assign_nameservers` raises a clear "not supported" error because the IONOS DNS API cannot change registrar delegation. Credentials: `IONOS_API_PUBLIC`, `IONOS_API_SECRET`.
- `src/donazopy/providers/joker.py`: real `JokerProvider` adapter over the Joker.com DMAPI (`https://dmapi.joker.com/request/`). Opens a session via `login` with `JOKER_API_KEY` → `Auth-Sid`, then implements `list_zones` (`query-domain-list`), `list_records` / `export_zone` / `import_zone` / `delete_all_records` (`dns-zone-get` / `dns-zone-put`, converting between Joker's `<label> <type> <pri> <target> <ttl>` line format and BIND, synthesizing a placeholder SOA on export since Joker manages it), `read_nameservers` (apex NS), and `assign_nameservers` (`domain-modify` with `ns-list`). Credentials: `JOKER_API_KEY` (replaces the previous `JOKER_USERNAME` / `JOKER_PASSWORD` stub).
- `src/donazopy/zonefile.py`: added `build_bind_zone(origin, records, *, default_ttl, synthetic_nameserver)` — constructs parseable BIND zone text from generic provider record mappings (handles `MX`/`SRV` priority folding, TXT quoting, FQDN normalization for `CNAME`/`NS`/`PTR`/`DNAME`, SOA mname/rname dotting, treats a partial/short SOA as absent, and synthesizes a missing SOA and/or apex NS so the output always round-trips through `parse_zone_text`).
- `src/donazopy/providers/registry.py`: `GoDaddyProvider`, `IonosProvider`, and `JokerProvider` registered as operational; `create_dns_provider` / `create_registrar_provider` resolve all four providers via a shared `_PROVIDER_FACTORIES` table.
- Tests: `tests/test_godaddy_provider.py`, `tests/test_ionos_provider.py`, `tests/test_joker_provider.py` (mocked `httpx.MockTransport` coverage of every adapter method, error paths, and BIND round-trips); updated `tests/test_registry.py` and `tests/test_cli.py` for the four-provider list.
- Docs: `src_docs/md/providers.md` and `src_docs/md/architecture.md` updated (new operational-provider sections, planned-table trimmed) and the `docs/` site rebuilt; `README.md` provider matrix and credentials section updated.

### Added — `domains` command and bulk nameserver reads

- `donazopy domains PROVIDER` lists the domains/zones a provider manages. `PROVIDER` may be a provider key (`ionos`) or a target with a wildcard domain (`ionos/*`).
- `donazopy nameservers PROVIDER/*` now reads nameservers for every domain the provider manages and returns a `{domain: [nameserver, ...]}` map (previously a wildcard domain errored). Assigning nameservers still requires a single concrete domain.
- The "target must name a single domain" error now points users at `donazopy domains <provider>`.

### Added — zone creation (`create-zone`, `copy --create`)

- `DNSHostingProvider` Protocol gained `create_zone(domain)` (idempotent where supported; `ProviderAPIError` otherwise).
- `CloudflareProvider.create_zone(domain)` → `POST /zones` (idempotent: returns the existing zone on the "already exists" / code 1061 error). The Cloudflare account is taken from `CLOUDFLARE_DNS_ACCOUNT` when set, otherwise auto-detected via `GET /accounts` when the token spans exactly one account; `CLOUDFLARE_DNS_ACCOUNT` is a new *optional* environment variable.
- `IonosProvider`, `GoDaddyProvider`, `JokerProvider` `create_zone` raise a clear "not supported" error — those providers create the DNS zone implicitly with the domain registration.
- New `donazopy create-zone TARGET` command.
- `donazopy copy SOURCE DEST` now creates the destination zone first when it is missing and the provider supports it (default `--create=True`; pass `--create=False` to skip). Destinations whose DNS zone exists implicitly with the domain registration are tolerated — the create step is skipped, not an error. The `copy` result now includes a `"created"` entry alongside `"replaced"`. Cloudflare's `create_zone` checks for the existing zone first, so `copy` between existing Cloudflare zones does not need account-level token permissions.

### Added (issue 203 — unified target notation, CLI restructure, docs site)

#### Unified target notation (`src/donazopy/target.py`)
- Added new module `src/donazopy/target.py` implementing `parse_target`, `resolve_provider_key`, `looks_like_path`, and the frozen `Target` dataclass.
- Target notation: `[provider/][domain][:record_type][:host_name][:value]`. Each segment defaults to "no filter"; `*` is also accepted as an explicit wildcard.
- `example.com` resolves to whichever sole operational provider manages it; if there are multiple, the command errors and asks for an explicit `provider/` prefix.
- `cloudflare/example.com` (and `:*:*:*` variants) selects that domain on that provider.
- `cloudflare/*` selects all domains on the provider.
- Trailing `:TYPE:host:value` segments are record-level filters; `*` means no filter on that field.
- `looks_like_path` distinguishes local zone-file paths from provider targets by extension, prefix, and path-separator heuristics.

#### Simplified and renamed CLI command set
- Added `donazopy status [TARGET] [--dotenv-path]` (replaces `provider` and `provider-status`).
- Added `donazopy records TARGET [--dotenv-path]` (replaces `provider-records`).
- Added `donazopy export TARGET [--output] [--overwrite] [--skip-ns] [--skip-types] [--dotenv-path]` (replaces `provider-export-zone`).
- Added `donazopy import-zone TARGET PATH [--proxied] [--dotenv-path]` (replaces `provider-import-zone`).
- Added `donazopy nameservers TARGET [NS...] [--dotenv-path]` (replaces `provider-nameservers`; now also accepts new nameservers as positional args to assign them).
- Added `donazopy diff A B [--origin] [--dotenv-path]` (replaces `zone-diff`; each side may be a local zone-file path or a provider target).
- Added `donazopy validate PATH [--origin]` (replaces `validate-zone`).
- Added `donazopy normalize PATH [--origin] [--output] [--overwrite]` (replaces `zone-normalize` / `zone-dump`).
- Added `donazopy copy SOURCE DEST [--skip-ns] [--skip-types] [--replace] [--dotenv-path]` — new command, copies a zone from one provider target to another, with optional `--skip-ns` / `--skip-types` filtering and `--replace` to wipe destination records first.

#### Export / copy filtering
- `export` and `copy` both accept `--skip-ns` (drop NS records) and `--skip-types=A,AAAA,...` (drop a comma-separated list of record types).
- `copy --replace` calls `delete_all_records` on the destination domain before importing.

#### Cloudflare provider additions
- Added `list_zones` to enumerate all zones on the account.
- Added `delete_all_records(domain)` used by `copy --replace` to wipe destination records.
- Added `assign_nameservers(domain, nameservers)` — raises a clear "not supported" error because the Cloudflare DNS API cannot set registrar delegation; documented as a placeholder for registrar-capable providers.

#### Zone-file helpers
- Added `filter_zone_text(text, origin, skip_ns, skip_types)` to drop NS or given-type records from raw BIND text.
- Added `filter_records(records, skip_ns, skip_types)` for record-list filtering.
- Added `records_from_zone_text(text, origin)` for in-memory zone parsing without a file.

#### Documentation site
- Added ProtoDocs (`properdocs`) + MaterialX (`mkdocs-materialx`) documentation site.
- Source pages in `src_docs/md/`: index, installation, quickstart, cli, targets, providers, zonefiles, architecture, contributing, changelog.
- MkDocs config at `mkdocs/mkdocs.yml`.
- Pre-built static output committed to `docs/`.
- Build and serve via `./docs.sh build` / `./docs.sh serve`.
- Docs dependencies added to `pyproject.toml` under `[dependency-groups] docs`.

### Changed (issue 203)
- CLI is now a single unified `Donazopy` Fire class; all commands use the target notation instead of separate provider/zone command namespaces.
- `diff` now accepts provider targets as well as local zone file paths on either side.
- README rewritten to document the new command surface, target notation, and documentation site.

### Removed (issue 203 — clean break from old command names)
- Removed `provider` (show provider info) — replaced by `status`.
- Removed `provider-status` — replaced by `status`.
- Removed `provider-records` — replaced by `records`.
- Removed `provider-export-zone` — replaced by `export`.
- Removed `provider-import-zone` — replaced by `import-zone`.
- Removed `provider-nameservers` — replaced by `nameservers`.
- Removed `validate-zone` — replaced by `validate`.
- Removed `zone-normalize` / `zone-dump` — replaced by `normalize`.
- Removed `zone-diff` — replaced by `diff`.

---

### Added (earlier work)
- Added the initial Hatch/uv Python package scaffold for `donazopy`.
- Added Fire-based CLI entry points for version, provider listing, provider information, and zone validation.
- Added Fire-based CLI entry points for zone normalization, zone dump output, and zone diff planning.
- Added `python-dotenv` support for provider credential loading from discovered or explicit `.env` files, with real environment variables taking precedence.
- Added redacted provider credential status output that reports presence and source without printing secret values.
- Added operational Cloudflare DNS support for record listing, BIND zone export, BIND zone import, and assigned nameserver reads.
- Added zone-file parsing, validation, normalization, deterministic dump, safe output writing, and before/after diff helpers built on `dnspython`.
- Added the 12-chapter project specification under `spec/`.
- Added the implementation task list in `TODO.md`.
- Added build and publish scripts matching the project brief.
- Added Pyright configuration and tests for package metadata, operational provider registry behavior, CLI metadata, zone validation, zone normalization, zone diffing, dotenv credential redaction, and Cloudflare API operations with mocked HTTP.

### Changed (earlier work)
- Limited the runtime provider registry to functional operational providers only; Cloudflare is currently the only exposed provider.
- Expanded the README into a focused user/developer guide covering dotenv credentials, local zone commands, Cloudflare operations, safety behavior, and the functional provider matrix.
- Corrected package metadata to use the Apache Software License classifier, matching `LICENSE`.
- Moved verified-solved setup, zone-engine, dotenv credential-loading, Cloudflare-provider, and documentation tasks out of `TODO.md` so it only tracks remaining work.

### Removed (earlier work)
- Removed provider dry-run plan and adapter-stub surfaces that advertised behavior without performing real provider operations.
- Removed nonfunctional providers from the runtime provider list until they have real adapters and tests.
