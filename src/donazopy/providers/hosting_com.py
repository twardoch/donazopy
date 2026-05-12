# this_file: src/donazopy/providers/hosting_com.py
from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderSpec

PROVIDER = ProviderSpec(
    key="hosting_com",
    display_name="Hosting.com",
    category="dns_and_registrar",
    docs_url="https://www.hosting.com/",
    credentials=("HOSTING_COM_TOKEN",),
    capabilities=DNS_AND_REGISTRAR,
    notes="Provider research is required before live API work; keep adapter isolated behind explicit credentials.",
)
