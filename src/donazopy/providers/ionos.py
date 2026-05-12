# this_file: src/donazopy/providers/ionos.py
from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderSpec

PROVIDER = ProviderSpec(
    key="ionos",
    display_name="IONOS",
    category="dns_and_registrar",
    docs_url="https://developer.hosting.ionos.com/docs/dns",
    credentials=("IONOS_API_PUBLIC", "IONOS_API_SECRET"),
    capabilities=DNS_AND_REGISTRAR,
    notes="IONOS DNS zone-file endpoints are distinct from domain and registrar delegation endpoints.",
)
