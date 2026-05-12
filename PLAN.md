# PLAN

Concise forward plan for `donazopy`. Each phase maps to flat `- [ ]` items in `TODO.md`.

---

## Phase 1 — Foundation hardening

**Goal:** make the project releasable as a pre-alpha package with a clean CI gate.

- Confirm and lock the public CLI name (`donazopy`) and PyPI package name before the first tagged release.
- Add a GitHub Actions workflow that runs Ruff, pytest (via Hatch), Pyright, and `hatch build` on every push.
- Add a release checklist script that validates `hatch-vcs` version derivation from git tags before `publish.sh` is called.

---

## Phase 2 — Zone file engine completeness

**Goal:** cover all common DNS record types and edge-case zone inputs with tests.

- Tests for AAAA, CNAME, MX, TXT, SRV, CAA, DNSSEC record types.
- Tests for invalid zones: missing SOA/NS, bad TTL, duplicate CNAME, malformed owner names, unsupported classes.
- Property-style round-trip tests (parse → serialize → parse → compare).
- Comment-preserving round-trip mode if user-facing zone edits require it.
- Explicit SOA serial update strategy for programmatically generated zone changes.

---

## Phase 3 — Cloudflare write/sync workflows

**Goal:** close the loop between a zone diff and live DNS mutations on Cloudflare.

- Design and implement safe-change protections (confirmation prompt, export-before-write backup).
- Implement Cloudflare create/update/delete record synchronization driven by `diff` output.
- Add mocked HTTP tests for all Cloudflare write paths.
- Add opt-in live integration tests gated by `DONAZOPY_LIVE_TESTS=1` and a disposable Cloudflare test zone.

---

## Phase 4 — Additional provider adapters

**Goal:** add at least two registrar-capable providers (for real `assign_nameservers`) and two DNS-only providers.

Recommended priority order based on market share and API quality:

1. **IONOS** — DNS zone-file get/put + registrar delegation.
2. **Namecheap** — domain/DNS adapter including real `assign_nameservers`.
3. **AWS Route 53** — hosted-zone sync + document Route 53 Registrar delegation.
4. **Google Cloud DNS** — hosted-zone sync; document Cloud Domains delegation limitations.
5. **Azure DNS** — hosted-zone sync.
6. **GoDaddy, DNSimple, Gandi, Porkbun, Dynadot** — domain/DNS adapters.
7. **Vercel, DigitalOcean, Hetzner, Linode, Vultr** — DNS-only adapters.
8. **Hosting.com, Hostinger, Bluehost** — research API capabilities first; enable only if confirmed.

Every adapter requires mocked HTTP tests before live integration tests.

---

## Phase 5 — Migration and sync workflows

**Goal:** support zero-downtime DNS migrations with safety rails.

- Provider-to-provider migration using zone file as intermediate source of truth (export → review → import).
- Registrar nameserver reassignment workflow with pre- and post-delegation parent-zone verification via RDAP/WHOIS.
- Rollback guidance: export-before-write snapshot, diff report, restore command.
- Confirmation prompt for all CLI operations that can mutate live DNS.
- Credential/token redaction in all log output.

---

## Phase 6 — Type checker and test quality cleanup

**Goal:** zero pyright errors across `src/` and `tests/`.

- Fix `FakeDNSProvider` / `FakeRegistrarProvider` in `tests/test_cli.py` to fully satisfy `DNSHostingProvider` / `RegistrarProvider` Protocols (currently produces pyright warnings about missing `spec` members).
- Audit and wire or remove `pymdownx.snippets` partials; remove the extension from `mkdocs/mkdocs.yml` if unused.

---

## Phase 7 — Documentation polish

**Goal:** docs site is complete enough to replace inline README for non-developer users.

- Provider-specific credential and permission setup guides.
- Migration cookbook: step-by-step zero-downtime DNS move between two providers.
- Troubleshooting guide: API errors, validation failures, nameserver propagation delays.
- Confirm `materialx` version and feature set in developer tooling notes; ensure it is listed correctly in the `docs` dependency group.
- Keep `CHANGELOG.md` and `TODO.md` in sync after each implementation loop.

---

## Architectural decisions (recorded)

- **Target notation** is the single unifying abstraction across all commands. Adding a new provider does not require new top-level commands — it just becomes a valid `provider/` prefix.
- **Zone file as source of truth** for all cross-provider migrations: export → normalize → review → import. No direct provider-to-provider API bridging.
- **Functional provider registry**: only providers with real adapters and at least mocked tests appear in `donazopy providers`. Stubs are never exposed.
- **`assign_nameservers` separation**: DNS hosting providers (like Cloudflare) cannot set registrar delegation; this requires a separate `RegistrarProvider` implementation. The Cloudflare implementation intentionally raises "not supported" with a clear message.
- **Docs site committed**: pre-built `docs/` is committed so the site is browsable from the repo without a build step; `./docs.sh build` refreshes it.
