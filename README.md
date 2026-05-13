# donazopy

> **Pre-release / pre-alpha.** The command surface changed in this revision (issue 203) — old commands have been removed and replaced with a unified target notation.

`donazopy` is a focused Python CLI for local DNS zone-file work and real provider operations.

Supported workflows:

1. **Local zone files** — validate, normalize, compare two zones as a change summary.
2. **Provider DNS** — load credentials from `.env` or environment, list/export/import records, copy zones between providers, read/assign nameservers, diff a live zone against a file.

Operational providers today: **Cloudflare**, **GoDaddy**, **IONOS**, and **Joker.com (DMAPI)**. Further providers are tracked in `TODO.md`.

## Installation

```bash
uv sync
```

Python 3.12+, Hatch + `hatch-vcs` for git-tag-derived versions.

## Credentials

Credentials are loaded with [`python-dotenv`](https://pypi.org/project/python-dotenv/):

- `donazopy` auto-discovers `.env` from the current working directory.
- Pass an explicit file with `--dotenv-path=path/to/.env`.
- Real environment variables override `.env` values.
- Status output shows presence and source only — secret values are never printed.

Create an ignored `.env` with the credentials for the provider(s) you use:

```dotenv
CLOUDFLARE_DNS_TOKEN=your-token          # Cloudflare (DNS Read for list/export, DNS Edit for import/copy, Zone Edit for create-zone)
CLOUDFLARE_DNS_ACCOUNT=your-account-id    # Cloudflare, optional — only needed for create-zone when the token spans multiple accounts
GODADDY_API_KEY=your-key                 # GoDaddy
GODADDY_API_SECRET=your-secret
IONOS_API_PUBLIC=your-public-prefix      # IONOS (combined as "{public}.{secret}" in the X-API-Key header)
IONOS_API_SECRET=your-secret
JOKER_API_KEY=your-dmapi-api-key         # Joker.com DMAPI
```

Run `donazopy status` to see, per provider, which variables are present and where they came from (values are never printed).

## Target notation

Most commands accept a `TARGET` argument using the notation:

```
[provider/][domain][:record_type][:host_name][:value]
```

| Example | Meaning |
| --- | --- |
| `example.com` | that domain on whichever sole operational provider manages it |
| `cloudflare/example.com` | `example.com` on Cloudflare specifically |
| `cloudflare/*` | all domains on Cloudflare |
| `cloudflare/example.com:A` | A records for `example.com` |
| `cloudflare/example.com:A:www:1.2.3.4` | filtered to a specific host and value |
| `example.com.zone` | a local zone file (resolved by extension / path heuristics) |

`*` in any filter segment means "no filter". A trailing `:TYPE:host:value` tuple is optional and defaults to no filtering.

## Quick start

```bash
# Tool version and operational providers
uv run donazopy version
uv run donazopy providers

# Domains a provider manages
uv run donazopy domains ionos --dotenv-path=.env

# Provider metadata and credential status
uv run donazopy status
uv run donazopy status cloudflare
uv run donazopy status cloudflare/example.com --dotenv-path=.env

# DNS records (with optional record-level filters)
uv run donazopy records cloudflare/example.com --dotenv-path=.env
uv run donazopy records cloudflare/example.com:A --dotenv-path=.env

# Export a live zone as BIND text
uv run donazopy export cloudflare/example.com --dotenv-path=.env
uv run donazopy export cloudflare/example.com --output=example.com.zone --overwrite --skip-ns

# Import BIND zone text into a provider
uv run donazopy import-zone cloudflare/example.com example.com.zone --dotenv-path=.env

# Copy a zone from one provider target to another
uv run donazopy copy cloudflare/example.com cloudflare/example-staging.com --skip-ns
uv run donazopy copy cloudflare/example.com cloudflare/example.com --replace  # wipe dest first
uv run donazopy copy ionos/example.com cloudflare/example.com --skip-ns --replace  # migrate IONOS -> Cloudflare (creates the CF zone if missing)

# Create a hosted zone (Cloudflare)
uv run donazopy create-zone cloudflare/example.com --dotenv-path=.env

# Read or assign nameservers
uv run donazopy nameservers cloudflare/example.com --dotenv-path=.env
uv run donazopy nameservers godaddy/* --dotenv-path=.env          # {domain: [nameserver, ...]} for every domain
uv run donazopy nameservers godaddy/example.com ns1.example.net ns2.example.net   # assign (GoDaddy/Joker only)

# Validate and normalize a local zone file
uv run donazopy validate example.com.zone --origin=example.com.
uv run donazopy normalize example.com.zone --origin=example.com.
uv run donazopy normalize example.com.zone --output=normalized.zone --overwrite

# Diff two zones — each side can be a file path or a provider target
uv run donazopy diff before.zone after.zone --origin=example.com.
uv run donazopy diff cloudflare/example.com example.com.zone
```

## Command reference

| Command | Description |
| --- | --- |
| `donazopy version` | Print installed version |
| `donazopy providers` | List operational provider keys |
| `donazopy domains PROVIDER [--dotenv-path=PATH]` | List the domains/zones a provider manages (`PROVIDER` may be `ionos` or `ionos/*`) |
| `donazopy status [TARGET] [--dotenv-path=PATH]` | Provider metadata + credential status |
| `donazopy records TARGET [--dotenv-path=PATH]` | List DNS records (target may include record filters) |
| `donazopy export TARGET [--output=PATH] [--overwrite] [--skip-ns] [--skip-types=A,AAAA,...] [--dotenv-path=PATH]` | Export zone as BIND text |
| `donazopy import-zone TARGET PATH [--proxied] [--dotenv-path=PATH]` | Import BIND zone file into provider |
| `donazopy create-zone TARGET [--dotenv-path=PATH]` | Create a hosted zone for the domain (Cloudflare; idempotent). Other providers raise "not supported" — the zone exists with the domain. |
| `donazopy copy SOURCE DEST [--skip-ns] [--skip-types=...] [--replace] [--create=BOOL] [--dotenv-path=PATH]` | Copy zone between provider targets; by default the destination zone is created if missing (`--create=False` to skip) |
| `donazopy nameservers TARGET [NS1 NS2 ...] [--dotenv-path=PATH]` | Read or assign nameservers |
| `donazopy diff A B [--origin=...] [--dotenv-path=PATH]` | Diff two zones (file paths or provider targets) |
| `donazopy validate PATH [--origin=...]` | Validate a local BIND zone file |
| `donazopy normalize PATH [--origin=...] [--output=PATH] [--overwrite]` | Normalize a local BIND zone file |

## Provider matrix

| Provider | Status |
| --- | --- |
| Cloudflare | Operational: record listing, BIND export/import, zone copy, nameserver read, credential status. `assign_nameservers` is "not supported" (Cloudflare DNS cannot set registrar delegation). |
| GoDaddy | Operational: domain list, record listing, BIND export, record import (PATCH/append), `delete_all_records`, registrar nameserver read **and** assignment. |
| IONOS | Operational: zone list, record listing, BIND export/import, `delete_all_records`, apex nameserver read. `assign_nameservers` is "not supported" (the IONOS DNS API cannot change registrar delegation). |
| Joker.com (DMAPI) | Operational: domain list, virtual DNS zone export/import (Joker↔BIND), `delete_all_records`, registrar nameserver read **and** assignment. |
| AWS Route 53, Google Cloud DNS, Azure DNS, Namecheap, DNSimple, Gandi, Porkbun, Dynadot, Vercel, DigitalOcean, Hetzner, Linode, Vultr, Hosting.com, Hostinger, Bluehost | Planned only — not exposed until real adapters and tests exist. |

## Safety model

- Zone-file operations are local and deterministic.
- Output writes refuse to overwrite existing files unless `--overwrite` is passed.
- `copy --replace` deletes all destination records before importing; use with care.
- Credentials are loaded through `python-dotenv` and environment variables, then redacted in status output.
- Unsupported providers are not exposed by `donazopy providers`; only providers with a real adapter and tests appear.
- `assign_nameservers` raises a clear "not supported" error on DNS-only delegation surfaces (Cloudflare, IONOS); use a registrar-capable provider (GoDaddy, Joker) to change delegation.

## Documentation

Full docs are built from `src_docs/md/` with MkDocs + ProtoDocs + MaterialX:

```bash
./docs.sh serve   # live preview at http://127.0.0.1:8000
./docs.sh build   # write static output to docs/
```

Config: `mkdocs/mkdocs.yml`. Pre-built output is committed to `docs/`.

## Development commands

```bash
uv sync
uvx hatch test
uvx ruff check .
uvx --with pytest --with dnspython --with fire --with httpx --with python-dotenv pyright src tests
python -m compileall src tests
./build.sh
```

`./build.sh` runs `uvx hatch clean` and `uvx hatch build`. `./publish.sh` runs `uvx hatch clean`, `uvx gitnextver`, `uvx hatch build`, then `uv publish`.

Do not commit provider credentials, `.env`, `.pypirc`, or private research material.
