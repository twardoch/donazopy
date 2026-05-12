# Changelog

The authoritative, always-current changelog lives in the repository: [`CHANGELOG.md`](https://github.com/twardoch/donazopy/blob/main/CHANGELOG.md). It follows [Keep a Changelog](https://keepachangelog.com/), and the project uses git-tag-derived semantic versions via `hatch-vcs`.

## Highlights so far

### Unreleased / current

**Added**

- Initial Hatch/uv Python package scaffold for `donazopy`.
- Fire-based CLI: version reporting, provider listing, provider information, redacted credential status, zone validation, zone normalization, zone dump, and zone diff planning.
- `python-dotenv` credential loading from discovered or explicit `.env` files, with real environment variables taking precedence; redacted status output that reports presence and source but never secret values.
- Operational **Cloudflare** DNS support: record listing, native BIND zone export, BIND zone import, and assigned-nameserver reads.
- Zone-file engine on `dnspython`: parsing, validation, normalization, deterministic dump, safe output writing (no overwrite without an explicit flag), and before/after diffing.
- The 12-chapter project specification under `spec/`, and the implementation task list in `TODO.md`.
- Build and publish scripts; this documentation site (ProtoDocs + MaterialX, sources in `src_docs/`, compiled into `docs/`).
- Pyright configuration and tests for package metadata, the operational provider registry, CLI metadata, zone validation/normalization/diffing, dotenv credential redaction, and Cloudflare API operations with mocked HTTP.

**Changed**

- The runtime provider registry is limited to *functional* operational providers; Cloudflare is currently the only one exposed.
- The README is a focused user/developer guide covering dotenv credentials, local zone commands, Cloudflare operations, and the safety model.
- Package metadata corrected to the Apache Software License classifier.

**Removed**

- Provider dry-run-plan and adapter-stub surfaces that advertised behavior without performing real operations.
- Nonfunctional providers from the runtime provider list (they remain documented in `spec/` and tracked in `TODO.md`).

______________________________________________________________________

For the complete, line-by-line history, see the repository [`CHANGELOG.md`](https://github.com/twardoch/donazopy/blob/main/CHANGELOG.md).
