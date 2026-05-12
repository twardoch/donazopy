# this_file: src/donazopy/providers/hostinger.py
from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderSpec

PROVIDER = ProviderSpec(
    key="hostinger",
    display_name="Hostinger",
    category="dns_and_registrar",
    docs_url="https://developers.hostinger.com/",
    credentials=("HOSTINGER_API_TOKEN",),
    capabilities=DNS_AND_REGISTRAR,
    notes="Hostinger exposes public APIs for domain and DNS automation; confirm endpoint coverage before implementation.",
)
