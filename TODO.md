# TODO

Verified-solved items are moved into `CHANGELOG.md` under `[Unreleased]` after each implementation loop.

## Doctor (issue #205) — follow-up

Initial v1 shipped under `[Unreleased]` in CHANGELOG. Follow-up tasks:

- [ ] Add live-DNS checks (parent-vs-zone NS comparison, dangling CNAME resolution) gated behind `--live`.
- [ ] Add provider-specific selective `delete_record(...)` instead of the current export → delete_all → import for cleaner partial fixes (Cloudflare API supports this directly).
- [ ] Add fixture-based golden-output tests for the human-readable report formatter.
- [ ] Add `--severity` and `--category` filters to the CLI subcommand.
- [ ] Add DKIM presence inference from common selectors (`default._domainkey`, `google._domainkey`).

## Foundation

- [ ] Confirm project name, package name, and public CLI command before first release.
- [ ] Add CI workflow running Ruff, pytest, type checks, and Hatch build.
- [ ] Add release checklist that validates git tag versioning through `hatch-vcs`.

## Zone File Engine

- [ ] Write tests for additional record types: AAAA, CNAME, MX, TXT, SRV, CAA, and DNSSEC records.
- [ ] Write tests for invalid zones: missing SOA, missing NS, bad TTL, duplicate CNAME conflicts, malformed owner names, and unsupported classes.
- [ ] Add comment-preserving round-trip support if `dnspython` parsing is not sufficient for user-facing edits.
- [ ] Add explicit SOA serial update strategy for generated zone changes.
- [ ] Add property-style tests for zone parse/serialize round trips.

## Provider Implementations

- [ ] Add Cloudflare create/update/delete record synchronization from zone diffs after unsafe-change protections are designed.
- [ ] Add mocked and opt-in live tests for Cloudflare imports against a disposable zone before broad write workflows are promoted.
- [ ] Wire IONOS registrar delegation (`assign_nameservers`) via the IONOS domains API; the DNS adapter currently raises "not supported".
- [ ] Add opt-in live integration tests for the GoDaddy, IONOS, and Joker adapters gated by explicit environment variables.
- [ ] Implement AWS Route 53 hosted-zone sync and registrar delegation flows.
- [ ] Implement Google Cloud DNS hosted-zone sync and document Cloud Domains delegation limitations.
- [ ] Implement Azure DNS hosted-zone sync.
- [ ] Implement Namecheap, DNSimple, Gandi, Porkbun, and Dynadot domain/DNS adapters.
- [ ] Implement DNS-only adapters for Vercel, DigitalOcean, Hetzner, Linode, and Vultr.
- [ ] Research and validate Hosting.com, Hostinger, and Bluehost API capabilities before enabling operations.
- [ ] Add mocked HTTP tests for every provider adapter before live integration tests.
- [ ] Add optional live integration tests gated by explicit environment variables.

## Migration and Sync Workflows

- [ ] Implement provider-to-provider migration workflow using zone file as intermediate source of truth.
- [ ] Implement registrar nameserver reassignment workflow with parent-zone verification.
- [ ] Add RDAP/WHOIS verification after delegation changes.
- [ ] Add rollback guidance and export-before-write safeguards for destructive changes.
- [ ] Ensure all write operations support confirmation in CLI mode when they can mutate live DNS.
- [ ] Ensure logs redact tokens, secrets, authorization headers, and provider account identifiers where sensitive.

## Type Checking / Test Quality

- [ ] Fix `tests/test_cli.py` fakes (`FakeDNSProvider`, `FakeRegistrarProvider`) to fully satisfy the `DNSHostingProvider` / `RegistrarProvider` Protocols so pyright reports no errors.
- [ ] Review and wire or remove `pymdownx.snippets` partials in `src_docs/`; remove the extension from `mkdocs/mkdocs.yml` if unused to avoid build warnings.

## Documentation

- [ ] Add provider-specific setup documentation for credentials and permissions.
- [ ] Add migration cookbook for zero-downtime DNS moves.
- [ ] Add troubleshooting guide for API errors, validation failures, and delegation propagation delays.
- [ ] Document `materialx` usage in developer tooling notes and confirm it is listed in the docs dependency group.
- [ ] Keep `CHANGELOG.md` updated by moving verified-solved TODO items into `[Unreleased]` entries after each implementation loop.

