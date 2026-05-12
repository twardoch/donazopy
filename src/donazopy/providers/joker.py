# this_file: src/donazopy/providers/joker.py
from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderSpec

PROVIDER = ProviderSpec(
    key="joker",
    display_name="Joker.com DMAPI",
    category="dns_and_registrar",
    docs_url="https://joker.com/faq/content/6/496/en/what-is-dmapi.html",
    credentials=("JOKER_USERNAME", "JOKER_PASSWORD"),
    capabilities=DNS_AND_REGISTRAR,
    notes="Joker DMAPI supports domain delegation operations and virtual DNS zone get/put workflows.",
)
