# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog, and this project uses git-tag-derived semantic versions through `hatch-vcs`.

## [Unreleased]

### Added
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

### Changed
- Limited the runtime provider registry to functional operational providers only; Cloudflare is currently the only exposed provider.
- Expanded the README into a focused user/developer guide covering dotenv credentials, local zone commands, Cloudflare operations, safety behavior, and the functional provider matrix.
- Corrected package metadata to use the Apache Software License classifier, matching `LICENSE`.
- Moved verified-solved setup, zone-engine, dotenv credential-loading, Cloudflare-provider, and documentation tasks out of `TODO.md` so it only tracks remaining work.

### Removed
- Removed provider dry-run plan and adapter-stub surfaces that advertised behavior without performing real provider operations.
- Removed nonfunctional providers from the runtime provider list until they have real adapters and tests.

### Fixed
- No prior TODO entries existed before the first implementation loop, so there were no historical verified-solved items to move from `TODO.md` into this changelog.
