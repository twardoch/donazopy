---
title: Zone files
this_file: src_docs/md/zonefiles.md
---

# Zone files

donazopy treats **local BIND-style zone files as the portable source of truth**.
All zone-file work goes through one engine (`src/donazopy/zonefile.py`) built on
[`dnspython`](https://www.dnspython.org/), which does the parsing and
serialization. This page explains the model and the four operations exposed on
the CLI: `validate`, `normalize` (also `dump`), `diff`, and the safe-write
behavior shared by `export`/`normalize`.

## The record model

When a zone is parsed, every resource record becomes a `NormalizedRecord`:

| Field | Meaning |
| --- | --- |
| `owner` | Absolute owner name with a trailing dot (e.g. `www.example.com.`). |
| `ttl` | TTL in seconds (int). |
| `record_class` | DNS class text, almost always `IN`. |
| `record_type` | DNS type text, e.g. `A`, `AAAA`, `CNAME`, `MX`, `TXT`, `SOA`, `NS`, `SRV`, `CAA`, `PTR`. |
| `value` | Stable, origin-derelativized text of the record data. |
| `source_order` | Index of the record as it appeared in the source (kept for reference; not used for identity). |

Two derived keys drive diffing:

- **`identity`** = `(owner, record_class, record_type)` — "the same kind of
  record at the same name". Used to pair *changed* records into updates.
- **`exact_key`** = `(owner, ttl, record_class, record_type, value)` — the full
  fingerprint. Used to detect records that are byte-for-byte unchanged.

Records are always returned **sorted** by `(owner, record_type, value, ttl)`, so
the output is deterministic regardless of provider response ordering or source
line order.

## Parsing

- Input can be a file (`parse_zone_file`) or text (`parse_zone_text`).
- An **origin** is required to parse. From the CLI, pass `--origin=example.com.`
  (trailing dot). If omitted, donazopy infers the origin from the **filename
  stem** — `example.com.zone` → `example.com`.
- Empty/whitespace-only text is rejected (`ZoneFileError: zone text is empty`).
- `dnspython` parse failures are wrapped as `ZoneFileError` with a readable
  message: `invalid zone for example.com.: <details>`.
- `check_origin=True` is used, so SOA/NS expectations at the apex are enforced.

## `validate`

```bash
donazopy validate PATH [--origin=ORIGIN]
```

Parses the file and returns `valid zone <origin>: <N> nodes`, or raises
`ZoneFileError` if it doesn't parse. Use it as a quick CI gate before pushing a
zone to a provider.

## `normalize` / `dump`

```bash
donazopy normalize PATH [--origin=ORIGIN] [--output=PATH] [--overwrite]
```

Returns the **canonical** form of the zone: one record per line as
`owner ttl class type value`, sorted deterministically, with a trailing newline.
This is the form to:

- commit to version control (stable, reviewable diffs),
- feed to `donazopy diff`,
- hand to a provider import after review.

`dump` is an alias for `normalize` with the same options.

Example canonical output:

```text
example.com. 3600 IN A 203.0.113.10
example.com. 3600 IN MX 10 mail.example.com.
example.com. 3600 IN NS ada.ns.cloudflare.com.
example.com. 3600 IN NS bob.ns.cloudflare.com.
example.com. 3600 IN SOA ada.ns.cloudflare.com. dns.cloudflare.com. 2034010101 10000 2400 604800 3600
www.example.com. 3600 IN CNAME example.com.
```

!!! note "SOA serials"
    donazopy preserves SOA serials by default — it does not silently invent or
    bump production serials. (Serial-bump-on-change is a documented future
    behavior; see [spec chapter 03](architecture.md#specification-chapters).)

## Filtering (`--skip-ns`, `--skip-types`)

`export` (and the internal copy/import path) can drop records before writing or
sending them:

- `--skip-ns` — drop all `NS` records. **The apex `SOA` record is always kept**
  regardless of any filter.
- `--skip-types=A,AAAA,...` — drop records whose type matches any of the given
  types (comma-separated, case-insensitive).

These filters operate on the normalized record set, then the result is
re-serialized to canonical BIND text. Typical use: produce a "DNS records only,
no delegation" copy with `--skip-ns`, or a "no host records" copy for a partial
migration with `--skip-types=A,AAAA,CNAME`.

## `diff`

```bash
donazopy diff A B [--origin=ORIGIN] [--dotenv-path=PATH]
```

`A` and `B` may each be a local zone-file path **or** a provider target (see
[Target notation → local-path detection](targets.md#local-path-detection)).
`diff` normalizes both sides into record sets and produces a `ZoneDiff`:

```json
{
  "summary": "creates=1 updates=2 deletes=0 unchanged=11",
  "changes": {
    "creates":   [ ... ],
    "updates":   [ ... ],
    "deletes":   [ ... ],
    "unchanged": [ ... ]
  }
}
```

Each entry is a `ZoneChange` with a `kind` (`create` / `update` / `delete` /
`unchanged`) and `before` / `after` record objects (one of which is `null` for
creates and deletes).

### The diff algorithm

1. **Exact match → unchanged.** Records whose `exact_key` appears in *both* sides
   are emitted as `unchanged`. They are removed from further consideration.
2. **Group the rest by `identity`** (`owner, class, type`) on each side.
3. For each identity present on either side:
   - **Both sides have records** → pair them positionally (sorted by
     `exact_key`): the first `min(len(before), len(after))` pairs become
     `update` changes; any extra `before` records become `delete`s; any extra
     `after` records become `create`s.
   - **Only `before`** → all become `delete`s.
   - **Only `after`** → all become `create`s.
4. The plan is sorted for stable output.

So a TTL change on an `A` record is an `update` (same identity, different
`exact_key`); adding a second `A` record at the same name is a `create`; removing
a `TXT` record is a `delete`; an identical record on both sides is `unchanged`.

The diff is independent of input ordering — it only depends on the normalized
record sets — which makes it safe to compare a provider's API response against a
file in version control.

## Safe writes

Any command that writes a file (`export --output`, `normalize --output`) uses
`write_text_safely`:

- If the target file **exists** and you did **not** pass `--overwrite`, it
  raises `ZoneFileError: refusing to overwrite existing file without
  overwrite=True: <path>`.
- Parent directories are created as needed.
- The file is written UTF-8 with the canonical trailing newline.

This is the single most important safety property of the local engine: you never
clobber a backup or a working file by accident.

## Errors

| Error | Cause |
| --- | --- |
| `zone text is empty` | The file/text had no records. |
| `zone file does not exist: <path>` | Wrong path. |
| `invalid zone for <origin>: ...` | `dnspython` couldn't parse it (bad records, SOA/NS problems). |
| `refusing to overwrite existing file without overwrite=True: <path>` | `--output` points at an existing file and `--overwrite` was not given. |

## See also

- [CLI reference](cli.md) — `validate`, `normalize`, `diff`, `export`.
- [Target notation](targets.md) — how `diff` tells a path from a provider target.
- [Architecture](architecture.md) — where the zone engine sits in the package.
