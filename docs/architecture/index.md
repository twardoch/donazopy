# Architecture

donazopy is a small, layered CLI. This page maps the package, traces the data flow of a typical command, summarizes the typing conventions, and indexes the 12-chapter design spec.

## Package layout

```text
src/donazopy/
├── __init__.py        # package version (re-exported as donazopy.__version__)
├── __main__.py        # console-script entry point (-> main())
├── cli.py             # the Donazopy class: every CLI command is a method
├── models.py          # ProviderCapability, ProviderSpec dataclasses
├── target.py          # Target dataclass + parse_target / resolve_provider_key
├── zonefile.py         # zone-file engine: parse / normalize / filter / diff / safe-write
└── providers/
    ├── __init__.py
    ├── base.py        # capabilities, credential loading, ProviderError types,
    │                  #   DNSHostingProvider / RegistrarProvider protocols
    ├── registry.py    # operational-provider registry + adapter factories
    ├── cloudflare.py  # operational adapter (CloudflareProvider)
    ├── godaddy.py     # operational adapter (GoDaddyProvider)
    ├── ionos.py       # operational adapter (IonosProvider)
    ├── joker.py       # operational adapter (JokerProvider)
    └── <provider>.py  # documented-only ProviderSpec stubs (aws, azure, namecheap, …)
```

Tests mirror `src/` under `tests/` (`test_cli.py`, `test_zonefile.py`, `test_cloudflare_provider.py`, `test_godaddy_provider.py`, `test_ionos_provider.py`, `test_joker_provider.py`, `test_registry.py`, `test_provider_base.py`, `test_package.py`).

## Layers

1. **CLI layer** (`cli.py`, `__main__.py`) — `Donazopy` is a plain class whose methods are commands; `fire.Fire(Donazopy)` turns it into a CLI. Methods do argument plumbing only: parse the target, resolve the provider, call the engine/adapter, return a JSON-serializable value.
1. **Target layer** (`target.py`) — turns a `[provider/][domain][:type][:host][:value]` string into a typed `Target`, and resolves which operational provider to use when the prefix is omitted. Also decides whether a string is a local file path (for `diff`).
1. **Provider layer** (`providers/`) — `registry.py` knows which providers are *operational* and constructs adapters; `base.py` defines the capability constants, credential loading (`python-dotenv` + env, redacted status), the `ProviderError` hierarchy, and the `DNSHostingProvider` / `RegistrarProvider` protocols; each `providers/<key>.py` either implements an adapter (`cloudflare.py`, `godaddy.py`, `ionos.py`, `joker.py`) or just declares a `ProviderSpec`.
1. **Zone engine** (`zonefile.py`) — pure, network-free. Parses BIND text with `dnspython`, normalizes records, filters them, diffs two record sets, and writes files safely (never overwriting without permission).

## Data flow of a command

`donazopy export cloudflare/example.com --output=out.zone --skip-ns --dotenv-path=.env`:

```text
CLI (Donazopy.export)
  └─ parse_target("cloudflare/example.com")          → Target(provider="cloudflare", domain="example.com", …)
  └─ resolve_provider_key(target, operational_keys)  → "cloudflare"
  └─ get_provider("cloudflare")                      → ProviderSpec
  └─ require_provider_credentials(spec, dotenv_path=.env)
        └─ dotenv_environment(...)                   → merged {.env, environ}, raises if CLOUDFLARE_DNS_TOKEN missing
  └─ create_dns_provider("cloudflare", creds)        → CloudflareProvider
  └─ CloudflareProvider.export_zone("example.com")
        └─ GET /zones?name=example.com               → zone id
        └─ GET /zones/{id}/dns_records/export        → BIND text
  └─ zonefile.filter_zone_text(text, origin, skip_ns=True)
        └─ parse → records → drop NS (keep apex SOA) → re-serialize canonical
  └─ zonefile.write_text_safely(Path("out.zone"), text, overwrite=False)
        └─ raises if out.zone exists and --overwrite not given
  └─ return the zone text  → Fire prints it
```

`donazopy diff a.zone cloudflare/example.com --origin=example.com.` follows the same shape but each side is resolved independently — a local path is read and parsed, a target is fetched via an adapter — and the two normalized record sets are passed to `diff_zone_records`.

## Typing and boundary conventions

- **Parse, don't validate.** Raw zone text and raw provider JSON are converted at the boundary into typed values (`NormalizedRecord`, `Target`, `ProviderSpec`, `CredentialStatus`). Internal code works with those, not strings/dicts.
- **Frozen dataclasses with `slots`.** `ProviderSpec`, `ProviderCapability`, `Target`, `NormalizedRecord`, `ZoneChange`, `ZoneDiff`, `CredentialStatus`, `LoadedCredentials` are all immutable.
- **Errors as typed exceptions, raised at the edge.** `TargetError`, `ZoneFileError`, `ProviderError` (with `ProviderCredentialError`, `ProviderAPIError`). Fire turns an uncaught exception into a non-zero exit with a traceback.
- **`Protocol`s for adapters.** `DNSHostingProvider` / `RegistrarProvider` are `runtime_checkable` protocols, so adapters are structurally typed — no base class to inherit.
- **Provider isolation.** One module per provider; nothing outside `providers/<key>.py` and `registry.py` knows provider-specific details.
- **No secrets in output.** Credential status is redacted; adapters must not put tokens into error messages or logs.

Strict typing is configured: `mypy --strict` and Pyright `standard` mode over `src` and `tests`. Ruff (line length 120) lints with `E,W,F,I,B,C4,UP,SIM`.

## Specification chapters

The full design lives in `spec/00-toc.md` plus `spec/01.md` … `spec/12.md`. The implemented code follows it partially today (the zone engine, the provider protocol, and the Cloudflare adapter are done; the broader write/migration and delegation workflows are specified but not yet exposed).

| Chapter | Title                                 | TL;DR                                                                                                                                                                                                                                                                        |
| ------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 01      | Vision and Scope                      | A zone-file-first CLI for DNS zones, provider records, and registrar delegation — an audit/migration/backup/sync tool, not a magic layer. The first release scaffolds the registry and ships the local engine + verified adapters only.                                      |
| 02      | Domain Model                          | Zones, records, providers, capabilities, credentials, sync plans, verification results. Provider-neutral record model; capability checks fail early; plans are the unit of review.                                                                                           |
| 03      | Zone File Engine                      | `dnspython` is the authoritative parser/serializer. Require an origin when it can't be inferred; normalize names/TTLs/classes; stable serialization; explicit SOA-serial handling; diff produces a plan with conflicts surfaced as warnings/errors.                          |
| 04      | Provider Architecture                 | One module per provider, explicit capabilities, small adapter surface. API behavior must be confirmed against official docs before live writes; researched placeholders may exist but must not claim tested write support.                                                   |
| 05      | Credential and Configuration Model    | Credentials from env vars or ignored local config; never committed/printed/logged. Each adapter declares its credential names; missing credentials fail before network calls; redaction is tested.                                                                           |
| 06      | CLI Experience                        | Fire-based, discoverable commands mapping to common workflows. Output names the files/providers/zones involved; dry-run/plan output is human-readable; write commands need explicit confirmation.                                                                            |
| 07      | Read, Export, and Dump Workflows      | Read provider state and dump it to stable BIND zone files for backup/audit/migration. Prefer native zone export when complete and documented, then re-validate it through the same engine.                                                                                   |
| 08      | Write, Import, and Sync Workflows     | Writes are plan-first: read local + provider state, compute creates/updates/deletes/no-ops/warnings, block unsafe changes by default, then apply in a safe order; export-before-import for native importers; idempotent re-applies.                                          |
| 09      | Nameserver and Registrar Workflows    | Delegation is a registrar/parent-zone concern — editing zone-file NS records is *not* sufficient. A reassignment plan reads current NS, validates target syntax/glue, updates via the domain API, then verifies via RDAP/WHOIS/DNS. DNS-only providers refuse registrar ops. |
| 10      | Safety, Validation, and Observability | Validate before writes, dry-run for destructive ops, block unsupported capabilities, confirm unsafe changes; categorize provider errors; redact secrets; verification failures must not look like successful applies.                                                        |
| 11      | Testing Strategy                      | Deterministic local zone tests → mocked provider contract tests (auth, bodies, pagination, errors, rate limits, idempotency) → opt-in, gated live tests on disposable zones.                                                                                                 |
| 12      | Implementation Roadmap                | Build in safety-first slices: scaffold → zone engine → provider protocols → high-confidence providers (Cloudflare, IONOS, Joker, Route 53, DNSimple, one DNS-only) → migration/delegation → provider expansion. Each phase leaves a working CLI and passing tests.           |

## See also

- [Providers](https://github.com/twardoch/donazopy/providers/index.md) — the provider model in detail and how to add one.
- [Zone files](https://github.com/twardoch/donazopy/zonefiles/index.md) — the zone engine.
- [Contributing](https://github.com/twardoch/donazopy/contributing/index.md) — the development workflow.
