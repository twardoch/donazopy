# this_file: src/donazopy/providers/dnsimple.py
from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderSpec

PROVIDER = ProviderSpec(
    key="dnsimple",
    display_name="DNSimple",
    category="dns_and_registrar",
    docs_url="https://developer.dnsimple.com/",
    credentials=("DNSIMPLE_TOKEN", "DNSIMPLE_ACCOUNT_ID"),
    capabilities=DNS_AND_REGISTRAR,
    notes="DNSimple has well-documented domain, DNS record, zone-file, and delegation API surfaces.",
)
