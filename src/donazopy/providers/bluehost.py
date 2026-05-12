# this_file: src/donazopy/providers/bluehost.py
from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderSpec

PROVIDER = ProviderSpec(
    key="bluehost",
    display_name="Bluehost",
    category="dns_and_registrar",
    docs_url="https://www.bluehost.com/",
    credentials=("BLUEHOST_API_TOKEN",),
    capabilities=DNS_AND_REGISTRAR,
    notes="Bluehost automation may require account-specific APIs or registrar workflows; verify before enabling writes.",
)
