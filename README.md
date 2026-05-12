# donazopy

`donazopy` is a focused Python CLI for local DNS zone-file work and real provider operations that are implemented and tested.

The project currently supports two useful workflows:

1. Local BIND-style zone files: validate, normalize/dump, safely write normalized output, and compare two zones as a change summary.
2. Cloudflare DNS zones: load credentials from `.env` or environment variables, list DNS records, export a Cloudflare zone as BIND text, import BIND zone text into Cloudflare, and read Cloudflare-assigned nameservers.

Other providers are documented in `spec/` and tracked in `TODO.md`, but they are not exposed as functional CLI providers until they have real adapters and tests.

## Installation for development

```bash
uv sync
```

The package targets Python 3.12+ and uses Hatch plus `hatch-vcs` for git-tag-derived versions.

## Credentials

Provider credentials are loaded with [`python-dotenv`](https://pypi.org/project/python-dotenv/):

- `donazopy` discovers a local `.env` from the current working directory.
- You can pass an explicit `.env` file with `--dotenv-path=path/to/.env`.
- Real environment variables override `.env` values.
- CLI status output only reports presence and source; it never prints secret values.

For Cloudflare, create an ignored `.env` file like:

```dotenv
CLOUDFLARE_API_TOKEN=your-token
```

The token needs permissions for the operation you run, such as DNS read for record listing/export and DNS edit for imports.

## Quick start

List operational providers:

```bash
uv run donazopy providers
# ['cloudflare']
```

Inspect Cloudflare metadata and credential status:

```bash
uv run donazopy provider cloudflare
uv run donazopy provider-status cloudflare --dotenv-path=.env
```

Validate and normalize a zone file:

```bash
uv run donazopy validate-zone example.zone --origin=example.com.
uv run donazopy zone-normalize example.zone --origin=example.com.
uv run donazopy zone-normalize example.zone --origin=example.com. --output=normalized.zone --overwrite
```

Compare two zone files:

```bash
uv run donazopy zone-diff before.zone after.zone --origin=example.com.
```

Use Cloudflare DNS operations:

```bash
uv run donazopy provider-records cloudflare example.com --dotenv-path=.env
uv run donazopy provider-export-zone cloudflare example.com --dotenv-path=.env --output=example.com.zone --overwrite
uv run donazopy provider-import-zone cloudflare example.com example.com.zone --dotenv-path=.env
uv run donazopy provider-nameservers cloudflare example.com --dotenv-path=.env
```

## Provider matrix

| Provider | Functional status |
| --- | --- |
| Cloudflare | Implemented for DNS record listing, BIND zone export/import, credential status, and assigned nameserver reads. |
| IONOS, Joker, AWS Route 53, Google Cloud DNS, Azure DNS, Namecheap, GoDaddy, DNSimple, Gandi, Porkbun, Dynadot, Vercel, DigitalOcean, Hetzner, Linode, Vultr, Hosting.com, Hostinger, Bluehost | Planned only. Not exposed as operational providers until real adapters and mocked/live tests are added. |

## Safety model

- Zone-file operations are local and deterministic.
- Output writes refuse to overwrite existing files unless `--overwrite` is passed.
- Provider credentials are loaded through `python-dotenv` and environment variables, then redacted in status output.
- Unsupported providers are not exposed by `donazopy providers`; this avoids placeholder/stub behavior.
- Destructive provider work must be backed by tests, clear CLI commands, and credential redaction before it is exposed.

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
