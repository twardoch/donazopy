# this_file: src/donazopy/providers/vercel.py
from donazopy.providers.base import DNS_ONLY, ProviderSpec

PROVIDER = ProviderSpec(
    key="vercel",
    display_name="Vercel",
    category="dns_host",
    docs_url="https://vercel.com/docs/rest-api/reference/endpoints/dns",
    credentials=("VERCEL_TOKEN",),
    capabilities=DNS_ONLY,
    notes="Vercel DNS is a hosted DNS API; registrar-level delegation usually remains with the domain registrar.",
)
