# this_file: src/donazopy/providers/godaddy.py
from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderSpec

PROVIDER = ProviderSpec(
    key="godaddy",
    display_name="GoDaddy",
    category="dns_and_registrar",
    docs_url="https://developer.godaddy.com/doc/endpoint/domains",
    credentials=("GODADDY_API_KEY", "GODADDY_API_SECRET"),
    capabilities=DNS_AND_REGISTRAR,
    notes="GoDaddy exposes domain and record APIs, with nameserver changes tied to domain registration endpoints.",
)
