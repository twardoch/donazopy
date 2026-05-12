# this_file: src/donazopy/providers/gandi.py

from donazopy.models import ProviderSpec
from donazopy.providers.base import DNS_AND_REGISTRAR

PROVIDER = ProviderSpec(
    key="gandi",
    display_name="Gandi",
    category="dns_and_registrar",
    docs_url="https://api.gandi.net/docs/",
    credentials=("GANDI_API_KEY",),
    capabilities=DNS_AND_REGISTRAR,
    notes="Gandi combines domain registration with LiveDNS zone and record APIs; delegation changes must use domain APIs.",
)
