---
title: Providers
this_file: src_docs/md/providers.md
---

# Providers

donazopy keeps a hard line between two kinds of providers:

- **Operational providers** — they have a real, tested adapter and are exposed
  by `donazopy providers`. You can run `records`, `export`, `import-zone`,
  `nameservers`, etc. against them. Today that is **only Cloudflare**.
- **Documented providers** — researched in [`spec/`](architecture.md#specification-chapters)
  and tracked in `TODO.md`, with a `ProviderSpec` describing their metadata and
  required credentials, but **no adapter yet**. They are deliberately *not*
  listed by `donazopy providers` so the CLI never advertises behavior it cannot
  perform.

## The provider model

Each provider lives in its own module under `src/donazopy/providers/`
(`cloudflare.py`, `namecheap.py`, `google_cloud.py`, …). Shared contracts live
in `base.py`; the registry is `registry.py`.

### `ProviderSpec` — static metadata

Every provider module exposes a `PROVIDER = ProviderSpec(...)` value:

| Field | Meaning |
| --- | --- |
| `key` | The CLI key, e.g. `"cloudflare"`. Lowercase, no dot. |
| `display_name` | Human name, e.g. `"AWS Route 53"`. |
| `category` | `"dns_host"`, `"dns_and_registrar"`, etc. |
| `docs_url` | Link to the provider's official API docs. |
| `credentials` | Tuple of environment-variable names this provider needs. |
| `capabilities` | Tuple of `ProviderCapability` values it advertises. |
| `notes` | A short caveat / description. |

`ProviderSpec.supports("zone_write")` answers capability questions.

### Capabilities

Capabilities are named constants in `providers/base.py`:

| Capability | Meaning |
| --- | --- |
| `zone_read` | Read hosted DNS zones and records. |
| `zone_write` | Create / update / delete / import hosted DNS records. |
| `zone_export` | Export DNS config to BIND-compatible zone text. |
| `zone_import` | Import / synchronize DNS config from zone text. |
| `delegation_read` | Read registrar-level nameserver delegation. |
| `domain_read` | List or inspect registered domains. |

Bundles: `DNS_ONLY = (zone_read, zone_write, zone_export, zone_import)`;
`DNS_AND_REGISTRAR_READ = DNS_ONLY + (domain_read, delegation_read)`;
`DNS_AND_REGISTRAR` is the same set today.

### Adapter contracts

Two `Protocol`s define what an adapter must implement:

```python
class DNSHostingProvider(Protocol):
    spec: ProviderSpec
    def export_zone(self, domain: str) -> str: ...
    def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> Mapping[str, object]: ...
    def list_records(self, domain: str) -> list[Mapping[str, object]]: ...

class RegistrarProvider(Protocol):
    spec: ProviderSpec
    def read_nameservers(self, domain: str) -> tuple[str, ...]: ...
```

A provider can implement either or both. Unsupported operations should fail
clearly, not silently no-op.

### Credential loading

Credentials are loaded with `python-dotenv` plus the environment, in this order
(later wins):

1. A discovered `.env` (searched upward from the current working directory).
2. An explicit `.env` passed via `--dotenv-path`.
3. Real environment variables.

`credential_status(spec, ...)` returns a `CredentialStatus` with `required`,
`present`, `missing`, `complete`, and `sources` — and `to_dict()` adds a
`redacted` map (`{name: "***"}`). **Secret values are never returned.**
`require_provider_credentials(spec, ...)` raises `ProviderCredentialError` if any
required variable is missing, before any network call.

## Operational provider: Cloudflare

| Field | Value |
| --- | --- |
| Key | `cloudflare` |
| Category | `dns_and_registrar` |
| API base | `https://api.cloudflare.com/client/v4` |
| Docs | <https://developers.cloudflare.com/api/> |
| Credentials | `CLOUDFLARE_API_TOKEN` |
| Capabilities | `zone_read`, `zone_write`, `zone_export`, `zone_import`, `domain_read`, `delegation_read` |

### What it does

- `records` → `GET /zones/{id}/dns_records` (paginated, 100/page).
- `export` → `GET /zones/{id}/dns_records/export` (Cloudflare's native BIND
  export); the result is returned (and optionally written / filtered).
- `import-zone` → `POST /zones/{id}/dns_records/import` with the zone file as a
  multipart upload; `--proxied` sets the `proxied` form field.
- `nameservers` (read) → the `name_servers` field on the zone object from
  `GET /zones?name=...`.

Zone lookup is by name: `GET /zones?name=example.com&per_page=1`. A missing
zone, a malformed response, or any `4xx`/`5xx` raises `ProviderAPIError` with the
Cloudflare error message(s) extracted from the response.

### Token scopes

| Operation | Required Cloudflare token permission |
| --- | --- |
| `records`, `export`, `nameservers` | Zone → DNS → **Read** |
| `import-zone` | Zone → DNS → **Edit** |

Create a scoped API token in the Cloudflare dashboard (My Profile → API Tokens),
restricted to the specific zone(s) you operate on, and put it in `.env`:

```dotenv title=".env"
CLOUDFLARE_API_TOKEN=your-scoped-token
```

### Nameservers and delegation

`donazopy nameservers cloudflare/example.com` **reads** the nameservers
Cloudflare assigned to the zone. It does **not** change your domain's
registrar-level delegation. Reassigning a domain's authoritative nameservers is a
*parent-zone / registrar* operation (the registrar that holds the domain
registration), not a hosted-zone one — see [spec chapter 09](architecture.md#specification-chapters).
That workflow is out of scope today; it will only be exposed when there is a real
registrar adapter with mocked/live tests behind it.

## Documented (planned) providers

These have a `ProviderSpec` and research notes but **no adapter** — they are not
exposed by `donazopy providers` and cannot be used operationally yet.

| Key | Display name | Category | Required credentials | Docs |
| --- | --- | --- | --- | --- |
| `aws` | AWS Route 53 | dns_and_registrar | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | [boto3 Route 53](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/route53.html) |
| `azure` | Azure DNS | dns_host | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SUBSCRIPTION_ID` | [Azure DNS REST](https://learn.microsoft.com/en-us/rest/api/dns/) |
| `bluehost` | Bluehost | dns_and_registrar | `BLUEHOST_API_TOKEN` | [bluehost.com](https://www.bluehost.com/) |
| `digitalocean` | DigitalOcean DNS | dns_host | `DIGITALOCEAN_TOKEN` | [DO Domains API](https://docs.digitalocean.com/reference/api/api-reference/#tag/Domains) |
| `dnsimple` | DNSimple | dns_and_registrar | `DNSIMPLE_TOKEN`, `DNSIMPLE_ACCOUNT_ID` | [developer.dnsimple.com](https://developer.dnsimple.com/) |
| `dynadot` | Dynadot | dns_and_registrar | `DYNADOT_API_KEY` | [Dynadot API](https://www.dynadot.com/domain/api.html) |
| `gandi` | Gandi | dns_and_registrar | `GANDI_API_KEY` | [api.gandi.net](https://api.gandi.net/docs/) |
| `godaddy` | GoDaddy | dns_and_registrar | `GODADDY_API_KEY`, `GODADDY_API_SECRET` | [developer.godaddy.com](https://developer.godaddy.com/doc/endpoint/domains) |
| `google_cloud` | Google Cloud DNS | dns_host | `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT` | [Cloud DNS v1](https://cloud.google.com/dns/docs/reference/v1/) |
| `hetzner` | Hetzner DNS | dns_host | `HETZNER_DNS_TOKEN` | [dns.hetzner.com](https://dns.hetzner.com/api-docs/) |
| `hosting_com` | Hosting.com | dns_and_registrar | `HOSTING_COM_TOKEN` | [hosting.com](https://www.hosting.com/) |
| `hostinger` | Hostinger | dns_and_registrar | `HOSTINGER_API_TOKEN` | [developers.hostinger.com](https://developers.hostinger.com/) |
| `ionos` | IONOS | dns_and_registrar | `IONOS_API_PUBLIC`, `IONOS_API_SECRET` | [IONOS DNS](https://developer.hosting.ionos.com/docs/dns) |
| `joker` | Joker.com DMAPI | dns_and_registrar | `JOKER_USERNAME`, `JOKER_PASSWORD` | [Joker DMAPI](https://joker.com/faq/content/6/496/en/what-is-dmapi.html) |
| `linode` | Linode DNS | dns_host | `LINODE_TOKEN` | [Linode API](https://techdocs.akamai.com/linode-api/reference/get-domains) |
| `namecheap` | Namecheap | dns_and_registrar | `NAMECHEAP_API_USER`, `NAMECHEAP_API_KEY`, `NAMECHEAP_USERNAME`, `NAMECHEAP_CLIENT_IP` | [Namecheap API](https://www.namecheap.com/support/api/intro/) |
| `porkbun` | Porkbun | dns_and_registrar | `PORKBUN_API_KEY`, `PORKBUN_SECRET_API_KEY` | [Porkbun API v3](https://porkbun.com/api/json/v3/documentation) |
| `vercel` | Vercel | dns_host | `VERCEL_TOKEN` | [Vercel DNS API](https://vercel.com/docs/rest-api/reference/endpoints/dns) |
| `vultr` | Vultr DNS | dns_host | `VULTR_API_KEY` | [Vultr API](https://www.vultr.com/api/) |

!!! note
    `category: dns_host` providers manage hosted zones and records only;
    registrar-level delegation for those domains lives elsewhere.
    `category: dns_and_registrar` providers *also* (per their docs) expose
    domain/delegation APIs — but donazopy will only act on those once a tested
    adapter exists.

## Adding a new provider

1. **Read the official API docs first.** Do not guess endpoints, field names, or
   auth schemes.
2. **Create a module** `src/donazopy/providers/<key>.py` with a `# this_file:`
   marker and a `PROVIDER = ProviderSpec(...)` describing key, display name,
   category, docs URL, required credential variable names, capabilities, and
   notes. (Many of these spec stubs already exist.)
3. **Implement an adapter class** satisfying `DNSHostingProvider` and/or
   `RegistrarProvider` from `providers/base.py`. Use `httpx` for HTTP. Raise
   `ProviderAPIError` / `ProviderCredentialError` for failures; never leak
   tokens into error messages or logs.
4. **Register it** in `providers/registry.py`: add the spec to
   `_OPERATIONAL_PROVIDERS` and wire `create_dns_provider` /
   `create_registrar_provider` to construct your adapter.
5. **Add mocked HTTP tests** under `tests/test_<key>_provider.py` covering auth
   headers, request bodies, pagination, API validation errors, and idempotent
   no-change behavior. Live tests, if any, must be opt-in via explicit
   environment variables and disposable zones — never run by default.
6. Only after the tests pass is the provider "operational". Move the completed
   `TODO.md` items into `CHANGELOG.md`.

See [Architecture](architecture.md) and [Contributing](contributing.md) for the
surrounding conventions.
