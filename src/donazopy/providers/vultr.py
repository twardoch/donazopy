# this_file: src/donazopy/providers/vultr.py

from donazopy.models import ProviderSpec
from donazopy.providers.base import DNS_ONLY

PROVIDER = ProviderSpec(
    key="vultr",
    display_name="Vultr DNS",
    category="dns_host",
    docs_url="https://www.vultr.com/api/",
    credentials=("VULTR_API_KEY",),
    capabilities=DNS_ONLY,
    notes="Vultr exposes hosted DNS domain and record APIs; registrar delegation is handled outside Vultr DNS.",
)
