---
title: Target notation
this_file: src_docs/md/targets.md
---

# Target notation

Most donazopy commands take a **target** — a compact string that names a
provider, a domain, and (optionally) a record-level filter. One grammar is used
everywhere a `TARGET` appears in the [CLI reference](cli.md).

## Grammar

```text
target  ::= [ provider "/" ] domain [ ":" record_type [ ":" host_name [ ":" value ] ] ]

provider     ::= a provider key, e.g. "cloudflare"        (optional)
domain       ::= a domain name, e.g. "example.com", or "*" for "all domains"
record_type  ::= a DNS type, e.g. "A", "TXT", "MX", or "*" for "no type filter"
host_name    ::= a record owner name, e.g. "www" or "_dmarc", or "*"
value        ::= a record value/content, or "*"
```

In words: **`[provider/][domain][:record_type][:host_name][:value]`**.

- The `provider/` prefix is optional.
- Up to **four** `:`-separated segments after the (optional) provider: domain,
  type, host, value. More than four segments is an error.
- A `*` (or an empty segment) in the `record_type`, `host_name`, or `value`
  slots means "no filter on this".
- A `*` in the **domain** slot is special: it means "all domains on the
  provider" (it is *not* treated as "no filter").
- `record_type` is matched case-insensitively (normalized to uppercase).

## Examples

| Target | Meaning |
| --- | --- |
| `example.com` | The domain `example.com` on whichever **operational** provider manages it (works when there is exactly one operational provider). |
| `cloudflare/example.com` | `example.com` on Cloudflare, all records. |
| `cloudflare/example.com:*` | Same as above (the `:*` adds no filter). |
| `cloudflare/example.com:*:*:*` | Same again — three wildcard filter segments. |
| `cloudflare/*` | **All domains** on Cloudflare. |
| `cloudflare/example.com:A` | Only `A` records of `example.com` on Cloudflare. |
| `cloudflare/example.com:TXT:_dmarc` | Only the `_dmarc` `TXT` record(s). |
| `cloudflare/example.com:CNAME:www:example.com.` | Only a `CNAME` named `www` whose value is `example.com.`. |
| `cloudflare/example.com:*:www` | Any record type owned by `www`. |

## Provider resolution (when the prefix is omitted)

When you write a bare `domain` (no `provider/`), donazopy must pick a provider:

- If there is **exactly one** operational provider, that one is used.
- If there is more than one (or none), donazopy raises an error telling you to
  prefix the target with `provider/`.

Today the only operational provider is `cloudflare`, so `example.com` resolves
to `cloudflare/example.com`. If you name a provider explicitly that is *not*
operational (e.g. `godaddy/example.com`), donazopy raises an error listing the
available operational providers.

## Record-level filters

The `:record_type:host_name:value` tail filters records *client-side* — donazopy
fetches the zone from the provider and then keeps only matching records.

Matching rules (a record is a mapping with `type`, `name`, `content`):

- `record_type` — `record["type"]` upper-cased must equal the filter.
- `host_name` — `record["name"]` must equal the filter, ignoring a trailing dot
  on either side (`www` matches `www.example.com.` only if the names are equal
  after stripping trailing dots — i.e. the comparison is on the literal stored
  owner name).
- `value` — `record["content"]` must equal the filter exactly.

A `None` filter (empty or `*`) on any of these always matches. Non-mapping
records always match (the filter is a no-op on them).

## Local-path detection

The `diff`, `validate`, and `normalize` commands work with local zone **files**.
`validate` and `normalize` always take a path. `diff` takes two arguments that
may each be *either* a path or a target, so donazopy has to tell them apart.

A string is treated as a **local path** (not a target) when:

- it contains a path separator (`/` or `\`) **and** looks path-like — e.g. it
  starts with `/`, `./`, `../`, `~`, or its first `/`-segment contains a `.`
  (so `zones/example.com.zone` is a path, but `cloudflare/example.com` is a
  provider target because `cloudflare` has no dot); or
- it ends with `.zone` or `.txt`; or
- it points at a file that actually exists on disk.

So:

| String | Treated as |
| --- | --- |
| `example.com.zone` | local path (ends in `.zone`) |
| `./example.com` | local path (starts with `./`) |
| `zones/db.example` | local path (first segment `zones` has no dot... actually has no dot — wait: `zones` has no dot, so this is a path only if `zones/db.example` exists on disk; otherwise it parses as provider `zones`, domain `db.example`) |
| `cloudflare/example.com` | provider target (`cloudflare` is a known-style provider key, no dot) |
| `/etc/zones/example.com` | local path (absolute) |

!!! tip
    When in doubt, give `diff` an unambiguous path — anything with a directory
    component, a `./` prefix, or a `.zone`/`.txt` extension is unambiguously a
    file.

## Errors you might see

- `target is empty; expected '[provider/][domain][:record_type][:host_name][:value]'`
  — you passed an empty or whitespace-only target.
- `target 'X' has an empty provider before '/'; use 'provider/domain'` — you
  wrote `/example.com`.
- `target 'X' has too many ':' segments; expected at most 'domain:record_type:host_name:value'`
  — more than four `:`-separated segments.
- `target 'X' has no provider and no domain; ...` — nothing usable in the string.
- `provider 'X' is not an operational provider; available: cloudflare` — you
  named a documented-but-not-implemented provider.
- `target 'X' does not specify a provider and there is not exactly one
  operational provider ...` — ambiguous; add a `provider/` prefix.

## See also

- [CLI reference](cli.md) — every command that takes a target.
- [Providers](providers.md) — which providers are operational.
- [Zone files](zonefiles.md) — what `diff` / `validate` / `normalize` do with files.
