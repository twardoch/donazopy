# donazopy

**donazopy** is a focused Python command-line tool for local DNS zone-file work and for real, *implemented-and-tested* DNS-provider operations. It deliberately avoids pretending to support things it does not: every provider you see exposed in the CLI has a working adapter behind it.

One sentence

Parse, validate, normalize, and diff BIND zone files locally — and read, export, and import DNS zones on providers that actually have a tested adapter (today: Cloudflare).

## What it does today

donazopy currently supports two practical workflows:

1. **Local BIND-style zone files** — validate a zone, normalize it to a stable canonical form, write the normalized output safely (never overwriting without an explicit flag), and compare two zones as a structured create/update/delete/unchanged plan.
1. **Cloudflare DNS zones** — load credentials from a `.env` file or the environment, list DNS records, export a Cloudflare zone as BIND text, import BIND zone text into Cloudflare, and read the nameservers Cloudflare has assigned to a zone.

A larger set of providers is *documented* in [`spec/`](https://github.com/twardoch/donazopy/architecture/#specification-chapters) and tracked in `TODO.md`, but those are intentionally **not** exposed as operational CLI providers until they have real adapters and mocked or live tests. See [Providers](https://github.com/twardoch/donazopy/providers/index.md) for the full status table.

## Philosophy

- **Safety first.** Zone-file operations are local and deterministic. Output writes refuse to clobber existing files unless you pass `--overwrite`. Destructive provider work must be backed by tests, explicit commands, and credential redaction before it ships.
- **Parse, don't validate.** Raw zone text is parsed once, at the boundary, into a normalized record model (`dnspython` does the heavy lifting). After that, the rest of the code works with typed, canonical records — not strings.
- **Real, implemented-only providers.** `donazopy providers` lists only providers with a working adapter. No stubs, no placeholders that advertise behavior they cannot perform.
- **Secrets stay secret.** Credentials are loaded through `python-dotenv` and environment variables, then *redacted* in status output — `donazopy status` reports presence and source, never the value.

## Feature matrix

| Capability                     | Local zone files         | Cloudflare                                                       |
| ------------------------------ | ------------------------ | ---------------------------------------------------------------- |
| Validate / normalize / dump    | ✅                       | —                                                                |
| Diff two zones                 | ✅ (`diff` on two paths) | ✅ (`diff` path vs provider, or provider vs provider)            |
| List records                   | —                        | ✅ `records`                                                     |
| Export zone to BIND text       | —                        | ✅ `export`                                                      |
| Import BIND zone into provider | —                        | ✅ `import-zone`                                                 |
| Read assigned nameservers      | —                        | ✅ `nameservers`                                                 |
| Reassign registrar nameservers | —                        | ❌ not supported (registrar/parent-zone API; out of scope today) |
| Credential status (redacted)   | n/a                      | ✅ `status`                                                      |

## Where to go next

- New here? Start with [Installation](https://github.com/twardoch/donazopy/installation/index.md), then the [Quick start](https://github.com/twardoch/donazopy/quickstart/index.md).
- Want the full command list? See the [CLI reference](https://github.com/twardoch/donazopy/cli/index.md).
- Curious about `cloudflare/example.com:TXT:_dmarc:*`? Read [Target notation](https://github.com/twardoch/donazopy/targets/index.md).
- Working with zone files? See [Zone files](https://github.com/twardoch/donazopy/zonefiles/index.md).
- Want to add a provider or hack on the code? See [Architecture](https://github.com/twardoch/donazopy/architecture/index.md) and [Contributing](https://github.com/twardoch/donazopy/contributing/index.md).
