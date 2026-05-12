# this_file: src/donazopy/providers/hetzner.py
from donazopy.providers.base import DNS_ONLY, ProviderSpec

PROVIDER = ProviderSpec(
    key="hetzner",
    display_name="Hetzner DNS",
    category="dns_host",
    docs_url="https://dns.hetzner.com/api-docs/",
    credentials=("HETZNER_DNS_TOKEN",),
    capabilities=DNS_ONLY,
    notes="Hetzner DNS provides zone and record APIs, including zone import/export workflows.",
)
