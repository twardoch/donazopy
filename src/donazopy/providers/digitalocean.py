# this_file: src/donazopy/providers/digitalocean.py
from donazopy.providers.base import DNS_ONLY, ProviderSpec

PROVIDER = ProviderSpec(
    key="digitalocean",
    display_name="DigitalOcean DNS",
    category="dns_host",
    docs_url="https://docs.digitalocean.com/reference/api/api-reference/#tag/Domains",
    credentials=("DIGITALOCEAN_TOKEN",),
    capabilities=DNS_ONLY,
    notes="DigitalOcean manages DNS domains and records but not registrar-level delegation for most domains.",
)
