---
title: CLI reference
this_file: src_docs/md/cli.md
---

# CLI reference

donazopy is built on [Python Fire](https://github.com/google/python-fire), so
every command returns a Python value that Fire renders (strings print as text;
dicts and lists print as JSON-ish structures). Run any command with `--help` to
see Fire's auto-generated usage.

!!! note "Command surface"
    This page documents the **current** command surface. Commands take a
    [target](targets.md) (`[provider/][domain][:type][:host][:value]`) or a
    local zone-file path where noted. The `--dotenv-path` flag is accepted by
    every command that talks to a provider.

## Conventions

| Notation | Meaning |
| --- | --- |
| `TARGET` | A [target string](targets.md), e.g. `cloudflare/example.com`. |
| `PATH` | A path to a local BIND zone file. |
| `[...]` | Optional argument or flag. |
| `--flag=VALUE` | A Fire keyword flag. Boolean flags also accept the bare `--flag` form. |
| `--dotenv-path=PATH` | Explicit `.env` file for credential loading (overrides discovery). |

Exit behavior: a successful command returns its value and exits `0`. Errors
(bad target, missing credentials, provider API failure, refusing to overwrite a
file, invalid zone) raise an exception, which Fire prints as a traceback and
exits non-zero.

---

## `version`

```bash
donazopy version
```

Prints the installed package version (derived from git tags via `hatch-vcs`).
No arguments. Returns a string.

```text
$ donazopy version
1.0.2
```

---

## `providers`

```bash
donazopy providers
```

Lists the **operational** provider keys — providers that have a working adapter
behind them. No arguments. Returns a list of strings.

```text
$ donazopy providers
['cloudflare', 'godaddy', 'ionos', 'joker']
```

Providers documented in `spec/` but not yet implemented are deliberately *not*
listed here. See [Providers](providers.md) for the full table.

---

## `domains`

```bash
donazopy domains PROVIDER [--dotenv-path=PATH]
```

Lists the domains/zones a provider manages. `PROVIDER` is a provider key
(`ionos`) or a target with a wildcard domain (`ionos/*`). Returns a list of
domain names.

```text
$ donazopy domains ionos
['example.com', 'example.net']
```

---

## `status`

```bash
donazopy status [TARGET] [--dotenv-path=PATH]
```

Reports **redacted** credential status. Given a provider (via `TARGET`, e.g.
`cloudflare` or `cloudflare/example.com`), it loads credentials from `.env` and
the environment and reports:

- `required` — the credential variable names this provider needs.
- `present` — which of those were found.
- `missing` — which are still needed.
- `complete` — whether the full set is present.
- `sources` — for each present credential, where it came from (a `.env` path or
  `"environment"`).
- `redacted` — `{name: "***"}` for each present credential. Secret values are
  **never** printed.

```text
$ donazopy status cloudflare --dotenv-path=.env
{
  "provider_key": "cloudflare",
  "required": ["CLOUDFLARE_API_TOKEN"],
  "present": ["CLOUDFLARE_API_TOKEN"],
  "missing": [],
  "complete": true,
  "sources": {"CLOUDFLARE_API_TOKEN": ".env"},
  "redacted": {"CLOUDFLARE_API_TOKEN": "***"}
}
```

---

## `records`

```bash
donazopy records TARGET [--dotenv-path=PATH]
```

Lists every DNS record in the target zone on the target provider. Requires the
provider's credentials to be complete. Returns a list of record mappings — the
raw provider fields (for Cloudflare: `id`, `type`, `name`, `content`, `ttl`,
`proxied`, `priority`, …).

```bash
donazopy records cloudflare/example.com --dotenv-path=.env
```

The `:type:host:value` segments of the target act as **client-side filters** on
the returned records (see [Target notation](targets.md#record-level-filters)).

---

## `export`

```bash
donazopy export TARGET [--output=PATH] [--overwrite] [--skip-ns] [--skip-types=A,AAAA,...] [--dotenv-path=PATH]
```

Exports the target zone as BIND-compatible zone text using the provider's native
export endpoint where available (Cloudflare has one).

| Flag | Effect |
| --- | --- |
| `--output=PATH` | Write the zone text to `PATH`. Without it, the text is returned/printed. |
| `--overwrite` | Allow overwriting an existing `--output` file. Without it, an existing file is an error. |
| `--skip-ns` | Drop `NS` records from the output. The apex `SOA` is always kept. |
| `--skip-types=A,AAAA,...` | Comma-separated record types to drop entirely (case-insensitive). |
| `--dotenv-path=PATH` | Explicit `.env` for credentials. |

```bash
# print to stdout
donazopy export cloudflare/example.com --dotenv-path=.env

# write a trimmed copy
donazopy export cloudflare/example.com --output=example.com.zone --overwrite --skip-ns --skip-types=A,AAAA --dotenv-path=.env
```

Returns the zone text (a string), even when `--output` is given.

---

## `import-zone`

```bash
donazopy import-zone TARGET PATH [--proxied] [--dotenv-path=PATH]
```

Reads BIND zone text from `PATH` and imports it into the target zone on the
provider using the provider's native zone-import endpoint.

| Argument / flag | Meaning |
| --- | --- |
| `TARGET` | The provider zone to import into, e.g. `cloudflare/example.com`. |
| `PATH` | Local BIND zone file to read. |
| `--proxied` | Mark imported proxiable records as proxied (Cloudflare). Omit to leave the provider default. |
| `--dotenv-path=PATH` | Explicit `.env` for credentials. |

```bash
donazopy import-zone cloudflare/example.com example.com.zone --dotenv-path=.env
```

Returns the provider's import-result mapping (record counts, etc.).

!!! warning "Run an export first"
    `import-zone` changes live DNS. Always `export` the current zone to a file
    beforehand so you have a backup.

---

## `copy`

```bash
donazopy copy SOURCE DEST [--skip-ns] [--skip-types=...] [--replace] [--dotenv-path=PATH]
```

Exports the `SOURCE` zone and imports it into the `DEST` zone — a convenience for
migrating or cloning zones (typically within the same provider).

| Flag | Effect |
| --- | --- |
| `--skip-ns` | Drop `NS` records from what gets copied (apex `SOA` kept). |
| `--skip-types=...` | Comma-separated record types to drop. |
| `--replace` | Replace the destination zone's records instead of merging. |
| `--dotenv-path=PATH` | Explicit `.env` for credentials. |

```bash
donazopy copy cloudflare/old.example cloudflare/new.example --skip-ns --replace --dotenv-path=.env
```

---

## `nameservers`

```bash
donazopy nameservers TARGET [NS1 NS2 ...] [--dotenv-path=PATH]
```

With no `NS` arguments, **reads** the nameservers the provider has assigned to
the target zone and returns them as a list of strings.

```text
$ donazopy nameservers cloudflare/example.com --dotenv-path=.env
['ada.ns.cloudflare.com', 'bob.ns.cloudflare.com']
```

A wildcard domain (`provider/*`) reads nameservers for every domain the provider
manages and returns a `{domain: [nameserver, ...]}` map:

```text
$ donazopy nameservers godaddy/* --dotenv-path=.env
{'example.com': ['ns01.domaincontrol.com', 'ns02.domaincontrol.com'], 'example.net': [...]}
```

Passing `NS1 NS2 ...` *sets* registrar-level nameservers for the target domain.
This is a real registrar delegation change on registrar-capable providers
(GoDaddy, Joker); on DNS-only delegation surfaces (Cloudflare, IONOS) it raises a
clear "not supported" error. See
[Providers → Nameservers and delegation](providers.md#nameservers-and-delegation).

---

## `diff`

```bash
donazopy diff A B [--origin=ORIGIN] [--dotenv-path=PATH]
```

Compares two zones and returns a structured change plan. `A` and `B` may each be
**either** a local zone-file path **or** a provider target — donazopy detects
which (see [Target notation → local-path detection](targets.md#local-path-detection)).

| Argument / flag | Meaning |
| --- | --- |
| `A`, `B` | Zone-file paths or provider targets. `A` is "before", `B` is "after". |
| `--origin=ORIGIN` | Zone origin (e.g. `example.com.`) used when parsing zone *files*. Inferred from the filename stem if omitted. |
| `--dotenv-path=PATH` | Explicit `.env`, used if either side is a provider target. |

Returns:

```json
{
  "summary": "creates=1 updates=0 deletes=2 unchanged=14",
  "changes": {
    "creates":   [ { "kind": "create",   "before": null, "after": { ... } } ],
    "updates":   [ { "kind": "update",   "before": { ... }, "after": { ... } } ],
    "deletes":   [ { "kind": "delete",   "before": { ... }, "after": null } ],
    "unchanged": [ { "kind": "unchanged", "before": { ... }, "after": { ... } } ]
  }
}
```

Each record object has `owner`, `ttl`, `record_class`, `record_type`, `value`,
and `source_order`. See [Zone files → the diff algorithm](zonefiles.md#the-diff-algorithm) for how the
plan is computed (identity vs exact key).

```bash
# two local files
donazopy diff before.zone after.zone --origin=example.com.

# provider vs local file
donazopy diff cloudflare/example.com edited.zone --origin=example.com. --dotenv-path=.env

# provider vs provider
donazopy diff cloudflare/a.example cloudflare/b.example --dotenv-path=.env
```

---

## `validate`

```bash
donazopy validate PATH [--origin=ORIGIN]
```

Parses a local BIND zone file and returns a short success message, or raises if
the zone is invalid (empty text, malformed records, SOA/NS problems).

```text
$ donazopy validate example.com.zone --origin=example.com.
valid zone example.com.: 12 nodes
```

`--origin` is the zone origin (with trailing dot, e.g. `example.com.`). If
omitted, donazopy infers it from the filename stem (`example.com.zone` →
`example.com`).

---

## `normalize`

```bash
donazopy normalize PATH [--origin=ORIGIN] [--output=PATH] [--overwrite]
```

Parses a zone file and returns its **canonical** form: every record on one line,
deterministically ordered (`owner`, `type`, `value`, `ttl`), with a trailing
newline. This is the form to commit to version control and to diff against.

| Flag | Effect |
| --- | --- |
| `--origin=ORIGIN` | Zone origin; inferred from the filename stem if omitted. |
| `--output=PATH` | Write the normalized text to `PATH` instead of returning it. |
| `--overwrite` | Allow overwriting an existing `--output` file. |

```bash
donazopy normalize messy.zone --origin=example.com.
donazopy normalize messy.zone --origin=example.com. --output=clean.zone --overwrite
```

Returns the normalized text (a string).

---

## See also

- [Target notation](targets.md) — the grammar for the `TARGET` arguments above.
- [Zone files](zonefiles.md) — how validate / normalize / diff work under the hood.
- [Providers](providers.md) — which providers are operational and what they support.
