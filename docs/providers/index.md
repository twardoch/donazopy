# Providers

donazopy keeps a hard line between two kinds of providers:

- **Operational providers** — they have a real, tested adapter and are exposed by `donazopy providers`. You can run `records`, `export`, `import-zone`, `nameservers`, etc. against them. Today those are **Cloudflare**, **GoDaddy**, **IONOS**, and **Joker.com (DMAPI)**.
- **Documented providers** — researched in [`spec/`](https://github.com/twardoch/donazopy/architecture/#specification-chapters) and tracked in `TODO.md`, with a `ProviderSpec` describing their metadata and required credentials, but **no adapter yet**. They are deliberately *not* listed by `donazopy providers` so the CLI never advertises behavior it cannot perform.

## The provider model

Each provider lives in its own module under `src/donazopy/providers/` (`cloudflare.py`, `namecheap.py`, `google_cloud.py`, …). Shared contracts live in `base.py`; the registry is `registry.py`.

### `ProviderSpec` — static metadata

Every provider module exposes a `PROVIDER = ProviderSpec(...)` value:

| Field          | Meaning                                                  |
| -------------- | -------------------------------------------------------- |
| `key`          | The CLI key, e.g. `"cloudflare"`. Lowercase, no dot.     |
| `display_name` | Human name, e.g. `"AWS Route 53"`.                       |
| `category`     | `"dns_host"`, `"dns_and_registrar"`, etc.                |
| `docs_url`     | Link to the provider's official API docs.                |
| `credentials`  | Tuple of environment-variable names this provider needs. |
| `capabilities` | Tuple of `ProviderCapability` values it advertises.      |
| `notes`        | A short caveat / description.                            |

`ProviderSpec.supports("zone_write")` answers capability questions.

### Capabilities

Capabilities are named constants in `providers/base.py`:

| Capability        | Meaning                                               |
| ----------------- | ----------------------------------------------------- |
| `zone_read`       | Read hosted DNS zones and records.                    |
| `zone_write`      | Create / update / delete / import hosted DNS records. |
| `zone_export`     | Export DNS config to BIND-compatible zone text.       |
| `zone_import`     | Import / synchronize DNS config from zone text.       |
| `delegation_read` | Read registrar-level nameserver delegation.           |
| `domain_read`     | List or inspect registered domains.                   |

Bundles: `DNS_ONLY = (zone_read, zone_write, zone_export, zone_import)`; `DNS_AND_REGISTRAR_READ = DNS_ONLY + (domain_read, delegation_read)`; `DNS_AND_REGISTRAR` is the same set today.

### Adapter contracts

Two `Protocol`s define what an adapter must implement:

```python
class DNSHostingProvider(Protocol):
    spec: ProviderSpec
    def export_zone(self, domain: str) -> str: ...
    def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> Mapping[str, object]: ...
    def list_records(self, domain: str) -> list[Mapping[str, object]]: ...
    def delete_all_records(self, domain: str) -> Mapping[str, object]: ...
    def list_zones(self) -> list[str]: ...

class RegistrarProvider(Protocol):
    spec: ProviderSpec
    def read_nameservers(self, domain: str) -> tuple[str, ...]: ...
    def assign_nameservers(self, domain: str, nameservers: Sequence[str]) -> Mapping[str, object]: ...
```

A provider can implement either or both. Unsupported operations should fail clearly, not silently no-op.

### Credential loading

Credentials are loaded with `python-dotenv` plus the environment, in this order (later wins):

1. A discovered `.env` (searched upward from the current working directory).
1. An explicit `.env` passed via `--dotenv-path`.
1. Real environment variables.

`credential_status(spec, ...)` returns a `CredentialStatus` with `required`, `present`, `missing`, `complete`, and `sources` — and `to_dict()` adds a `redacted` map (`{name: "***"}`). **Secret values are never returned.** `require_provider_credentials(spec, ...)` raises `ProviderCredentialError` if any required variable is missing, before any network call.

## Operational provider: Cloudflare

| Field        | Value                                                                                     |
| ------------ | ----------------------------------------------------------------------------------------- |
| Key          | `cloudflare`                                                                              |
| Category     | `dns_and_registrar`                                                                       |
| API base     | `https://api.cloudflare.com/client/v4`                                                    |
| Docs         | <https://developers.cloudflare.com/api/>                                                  |
| Credentials  | `CLOUDFLARE_API_TOKEN`                                                                    |
| Capabilities | `zone_read`, `zone_write`, `zone_export`, `zone_import`, `domain_read`, `delegation_read` |

### What it does

- `records` → `GET /zones/{id}/dns_records` (paginated, 100/page).
- `export` → `GET /zones/{id}/dns_records/export` (Cloudflare's native BIND export); the result is returned (and optionally written / filtered).
- `import-zone` → `POST /zones/{id}/dns_records/import` with the zone file as a multipart upload; `--proxied` sets the `proxied` form field.
- `nameservers` (read) → the `name_servers` field on the zone object from `GET /zones?name=...`.

Zone lookup is by name: `GET /zones?name=example.com&per_page=1`. A missing zone, a malformed response, or any `4xx`/`5xx` raises `ProviderAPIError` with the Cloudflare error message(s) extracted from the response.

### Token scopes

| Operation                          | Required Cloudflare token permission |
| ---------------------------------- | ------------------------------------ |
| `records`, `export`, `nameservers` | Zone → DNS → **Read**                |
| `import-zone`                      | Zone → DNS → **Edit**                |

Create a scoped API token in the Cloudflare dashboard (My Profile → API Tokens), restricted to the specific zone(s) you operate on, and put it in `.env`:

.env

```text
CLOUDFLARE_API_TOKEN=your-scoped-token
```

### Nameservers and delegation

`donazopy nameservers cloudflare/example.com` **reads** the nameservers Cloudflare assigned to the zone. It does **not** change your domain's registrar-level delegation. Reassigning a domain's authoritative nameservers is a *parent-zone / registrar* operation (the registrar that holds the domain registration), not a hosted-zone one — see [spec chapter 09](https://github.com/twardoch/donazopy/architecture/#specification-chapters). That workflow is out of scope today; it will only be exposed when there is a real registrar adapter with mocked/live tests behind it.

## Operational provider: GoDaddy

| Field       | Value                                                |
| ----------- | ---------------------------------------------------- |
| Key         | `godaddy`                                            |
| Category    | `dns_and_registrar`                                  |
| API base    | `https://api.godaddy.com/v1`                         |
| Docs        | <https://developer.godaddy.com/doc/endpoint/domains> |
| Credentials | `GODADDY_API_KEY`, `GODADDY_API_SECRET`              |
| Auth        | `Authorization: sso-key {key}:{secret}`              |

- `records` / `export` → `GET /v1/domains/{domain}/records`; records are relative (`@` for the apex). GoDaddy keeps `MX`/`SRV` priority (and `SRV` weight/port) in dedicated fields, which the adapter folds back into BIND rdata. GoDaddy's `SOA` carries only the primary nameserver, so a synthetic SOA is generated on export.
- `import-zone` → `PATCH /v1/domains/{domain}/records` (appends the parsed records; the GoDaddy-managed `SOA` is never re-sent).
- `copy --replace` / `delete_all_records` → `DELETE /v1/domains/{domain}/records/{type}/{name}` per type+name group, preserving the apex `NS` and `SOA`.
- `nameservers` (read) → the `nameServers` field on `GET /v1/domains/{domain}`.
- `nameservers NS1 NS2 ...` (assign) → `PUT /v1/domains/{domain}` with `{"nameServers": [...]}` — a real registrar delegation change.

GoDaddy's production API restricts some domain endpoints by account size/plan; those limits surface as `ProviderAPIError` with the GoDaddy message.

## Operational provider: IONOS

| Field       | Value                                          |
| ----------- | ---------------------------------------------- |
| Key         | `ionos`                                        |
| Category    | `dns_and_registrar`                            |
| API base    | `https://api.hosting.ionos.com/dns/v1`         |
| Docs        | <https://developer.hosting.ionos.com/docs/dns> |
| Credentials | `IONOS_API_PUBLIC`, `IONOS_API_SECRET`         |
| Auth        | `X-API-Key: {public}.{secret}`                 |

- `list_zones` → `GET /zones`; the zone is resolved by name, then `GET /zones/{id}` returns its records (`disabled` records are dropped on export). IONOS includes the real `SOA` and `NS` records, so the BIND export is a complete standalone zone.
- `import-zone` → `POST /zones/{id}/records` with the parsed records; the IONOS-managed `SOA` is never re-sent.
- `delete_all_records` → `DELETE /zones/{id}/records/{recordId}` for every non-`SOA` record.
- `nameservers` (read) → the apex `NS` records in the zone.
- `nameservers NS1 NS2 ...` (assign) → **not supported**: the IONOS DNS API cannot change registrar delegation. Update it in the IONOS domain management area / domains API.

## Operational provider: Joker.com (DMAPI)

| Field       | Value                                                              |
| ----------- | ------------------------------------------------------------------ |
| Key         | `joker`                                                            |
| Category    | `dns_and_registrar`                                                |
| API base    | `https://dmapi.joker.com/request/`                                 |
| Docs        | <https://dmapi.joker.com/>                                         |
| Credentials | `JOKER_API_KEY`                                                    |
| Auth        | `login` with `api-key` → `Auth-Sid` header, reused for the session |

DMAPI is a request/response HTTP API: each response is `Key: Value` headers, a blank line, then an optional body; `Status-Code: 0` means success.

- `list_zones` → `query-domain-list` (first token of each line is the domain).
- `records` / `export` → `dns-zone-get` returns Joker's line format (`<label> <type> <pri> <target> <ttl> ...`, `@` for the apex, TXT targets double-quoted); the adapter converts it to BIND and synthesizes the `SOA` (Joker manages the SOA, so it is never in a zone-get).
- `import-zone` / `copy` / `delete_all_records` → `dns-zone-put` with the converted zone text (the `SOA` is never sent).
- `nameservers` (read) → the apex `NS` records in the virtual zone.
- `nameservers NS1 NS2 ...` (assign) → `domain-modify` with a colon-separated `ns-list` — a real registrar delegation change.

## Documented (planned) providers

These have a `ProviderSpec` and research notes but **no adapter** — they are not exposed by `donazopy providers` and cannot be used operationally yet.

| Key            | Display name     | Category          | Required credentials                                                                   | Docs                                                                                                      |
| -------------- | ---------------- | ----------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `aws`          | AWS Route 53     | dns_and_registrar | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`                             | [boto3 Route 53](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/route53.html) |
| `azure`        | Azure DNS        | dns_host          | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SUBSCRIPTION_ID`   | [Azure DNS REST](https://learn.microsoft.com/en-us/rest/api/dns/)                                         |
| `bluehost`     | Bluehost         | dns_and_registrar | `BLUEHOST_API_TOKEN`                                                                   | [bluehost.com](https://www.bluehost.com/)                                                                 |
| `digitalocean` | DigitalOcean DNS | dns_host          | `DIGITALOCEAN_TOKEN`                                                                   | [DO Domains API](https://docs.digitalocean.com/reference/api/api-reference/#tag/Domains)                  |
| `dnsimple`     | DNSimple         | dns_and_registrar | `DNSIMPLE_TOKEN`, `DNSIMPLE_ACCOUNT_ID`                                                | [developer.dnsimple.com](https://developer.dnsimple.com/)                                                 |
| `dynadot`      | Dynadot          | dns_and_registrar | `DYNADOT_API_KEY`                                                                      | [Dynadot API](https://www.dynadot.com/domain/api.html)                                                    |
| `gandi`        | Gandi            | dns_and_registrar | `GANDI_API_KEY`                                                                        | [api.gandi.net](https://api.gandi.net/docs/)                                                              |
| `google_cloud` | Google Cloud DNS | dns_host          | `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`                               | [Cloud DNS v1](https://cloud.google.com/dns/docs/reference/v1/)                                           |
| `hetzner`      | Hetzner DNS      | dns_host          | `HETZNER_DNS_TOKEN`                                                                    | [dns.hetzner.com](https://dns.hetzner.com/api-docs/)                                                      |
| `hosting_com`  | Hosting.com      | dns_and_registrar | `HOSTING_COM_TOKEN`                                                                    | [hosting.com](https://www.hosting.com/)                                                                   |
| `hostinger`    | Hostinger        | dns_and_registrar | `HOSTINGER_API_TOKEN`                                                                  | [developers.hostinger.com](https://developers.hostinger.com/)                                             |
| `linode`       | Linode DNS       | dns_host          | `LINODE_TOKEN`                                                                         | [Linode API](https://techdocs.akamai.com/linode-api/reference/get-domains)                                |
| `namecheap`    | Namecheap        | dns_and_registrar | `NAMECHEAP_API_USER`, `NAMECHEAP_API_KEY`, `NAMECHEAP_USERNAME`, `NAMECHEAP_CLIENT_IP` | [Namecheap API](https://www.namecheap.com/support/api/intro/)                                             |
| `porkbun`      | Porkbun          | dns_and_registrar | `PORKBUN_API_KEY`, `PORKBUN_SECRET_API_KEY`                                            | [Porkbun API v3](https://porkbun.com/api/json/v3/documentation)                                           |
| `vercel`       | Vercel           | dns_host          | `VERCEL_TOKEN`                                                                         | [Vercel DNS API](https://vercel.com/docs/rest-api/reference/endpoints/dns)                                |
| `vultr`        | Vultr DNS        | dns_host          | `VULTR_API_KEY`                                                                        | [Vultr API](https://www.vultr.com/api/)                                                                   |

Note

`category: dns_host` providers manage hosted zones and records only; registrar-level delegation for those domains lives elsewhere. `category: dns_and_registrar` providers *also* (per their docs) expose domain/delegation APIs — but donazopy will only act on those once a tested adapter exists.

## Adding a new provider

1. **Read the official API docs first.** Do not guess endpoints, field names, or auth schemes.
1. **Create a module** `src/donazopy/providers/<key>.py` with a `# this_file:` marker and a `PROVIDER = ProviderSpec(...)` describing key, display name, category, docs URL, required credential variable names, capabilities, and notes. (Many of these spec stubs already exist.)
1. **Implement an adapter class** satisfying `DNSHostingProvider` and/or `RegistrarProvider` from `providers/base.py`. Use `httpx` for HTTP. Raise `ProviderAPIError` / `ProviderCredentialError` for failures; never leak tokens into error messages or logs.
1. **Register it** in `providers/registry.py`: add the spec to `_OPERATIONAL_PROVIDERS` and the adapter class to `_PROVIDER_FACTORIES` (the shared table behind `create_dns_provider` / `create_registrar_provider`).
1. **Add mocked HTTP tests** under `tests/test_<key>_provider.py` covering auth headers, request bodies, pagination, API validation errors, and idempotent no-change behavior. Live tests, if any, must be opt-in via explicit environment variables and disposable zones — never run by default.
1. Only after the tests pass is the provider "operational". Move the completed `TODO.md` items into `CHANGELOG.md`.

See [Architecture](https://github.com/twardoch/donazopy/architecture/index.md) and [Contributing](https://github.com/twardoch/donazopy/contributing/index.md) for the surrounding conventions.
