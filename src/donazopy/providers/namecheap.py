# this_file: src/donazopy/providers/namecheap.py
from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderSpec

PROVIDER = ProviderSpec(
    key="namecheap",
    display_name="Namecheap",
    category="dns_and_registrar",
    docs_url="https://www.namecheap.com/support/api/intro/",
    credentials=("NAMECHEAP_API_USER", "NAMECHEAP_API_KEY", "NAMECHEAP_USERNAME", "NAMECHEAP_CLIENT_IP"),
    capabilities=DNS_AND_REGISTRAR,
    notes="Namecheap API has separate domains DNS host-record endpoints and nameserver/delegation endpoints.",
)
