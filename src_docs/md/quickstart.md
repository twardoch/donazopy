---
title: Quick start
this_file: src_docs/md/quickstart.md
---

# Quick start

This page walks through the core workflows end to end. It assumes you have
donazopy installed (see [Installation](installation.md)) and that you can run it
as `donazopy ...` or `uv run donazopy ...`.

## 1. Credentials

Provider credentials are loaded with [`python-dotenv`](https://pypi.org/project/python-dotenv/):

1. donazopy discovers a `.env` file starting from the current working directory.
2. You can point at an explicit file with `--dotenv-path=path/to/.env`.
3. Real environment variables **override** values from `.env`.
4. Status output reports only *presence* and *source* — it never prints secret
   values.

For Cloudflare, create an ignored `.env` file:

```dotenv title=".env"
CLOUDFLARE_API_TOKEN=your-cloudflare-api-token
```

!!! warning "Never commit secrets"
    `.env`, `.pypirc`, provider tokens, and private research are all
    ignored/forbidden in this repo. Keep secrets in local environment variables
    or ignored config files only.

The Cloudflare token needs the right scopes for what you run:

- **Zone → DNS → Read** for `records`, `export`, and `nameservers`.
- **Zone → DNS → Edit** for `import-zone`.

## 2. Discover providers

```bash
donazopy providers
# ['cloudflare']
```

Only providers with a working adapter are listed. To see details and credential
requirements:

```bash
donazopy providers          # just the keys
donazopy status cloudflare  # redacted credential status for one provider
```

`status` (without a target) reports which credential variables are present, from
which source, and whether the set is complete — never the values themselves.

## 3. Inspect a Cloudflare zone

Check that your token works and that the zone exists:

```bash
donazopy status cloudflare --dotenv-path=.env
```

List all DNS records for a domain:

```bash
donazopy records cloudflare/example.com --dotenv-path=.env
```

The output is JSON (Fire renders the return value), one object per Cloudflare DNS
record, with the raw Cloudflare fields (`type`, `name`, `content`, `ttl`,
`proxied`, …).

## 4. Export the zone to a BIND file

```bash
donazopy export cloudflare/example.com --output=example.com.zone --overwrite --dotenv-path=.env
```

Without `--output`, the zone text is returned (printed) instead of written.
`--overwrite` is required if the file already exists. You can also trim the
export:

```bash
# drop NS records (the apex SOA is always kept) and skip A/AAAA records
donazopy export cloudflare/example.com --output=clean.zone --skip-ns --skip-types=A,AAAA --dotenv-path=.env
```

## 5. Edit the zone file

Open `example.com.zone` in your editor and make changes — add a TXT record, fix a
CNAME, bump a TTL. Then validate and normalize it locally before pushing:

```bash
donazopy validate example.com.zone --origin=example.com.
donazopy normalize example.com.zone --origin=example.com.
```

Want to see exactly what will change relative to what Cloudflare currently has?

```bash
donazopy diff cloudflare/example.com example.com.zone --origin=example.com.
```

`diff` accepts a provider target *or* a local zone-file path on either side.
Here it compares the live Cloudflare zone (`before`) against your edited file
(`after`) and prints a `creates` / `updates` / `deletes` / `unchanged` plan.

## 6. Import the zone back into Cloudflare

```bash
donazopy import-zone cloudflare/example.com example.com.zone --dotenv-path=.env
```

This uses Cloudflare's native zone-import endpoint. Pass `--proxied` to mark
imported proxiable records as proxied.

!!! tip "Back up first"
    Run an `export` to a file before an `import-zone` so you always have the
    previous state on disk.

## 7. Read the assigned nameservers

```bash
donazopy nameservers cloudflare/example.com --dotenv-path=.env
# ['xyz.ns.cloudflare.com', 'abc.ns.cloudflare.com']
```

This reads the nameservers Cloudflare has assigned to the zone. donazopy does
**not** reassign your domain's registrar-level delegation — that is a
registrar/parent-zone operation and is out of scope today (see
[Providers](providers.md#nameservers-and-delegation)).

## 8. Copy a zone between domains (optional)

```bash
donazopy copy cloudflare/source.example cloudflare/dest.example --skip-ns --replace --dotenv-path=.env
```

`copy` exports the source zone and imports it into the destination, optionally
filtering records (`--skip-ns`, `--skip-types=...`) and replacing the
destination's records (`--replace`).

---

Next: the full [CLI reference](cli.md), or the [Target notation](targets.md)
grammar that all the `provider/domain` arguments above follow.
