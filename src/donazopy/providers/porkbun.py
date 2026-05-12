# this_file: src/donazopy/providers/porkbun.py

from donazopy.models import ProviderSpec
from donazopy.providers.base import DNS_AND_REGISTRAR

PROVIDER = ProviderSpec(
    key="porkbun",
    display_name="Porkbun",
    category="dns_and_registrar",
    docs_url="https://porkbun.com/api/json/v3/documentation",
    credentials=("PORKBUN_API_KEY", "PORKBUN_SECRET_API_KEY"),
    capabilities=DNS_AND_REGISTRAR,
    notes="Porkbun has JSON APIs for DNS records and nameserver operations on domains registered with Porkbun.",
)
