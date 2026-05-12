# this_file: src/donazopy/providers/azure.py
from donazopy.providers.base import DNS_ONLY, ProviderSpec

PROVIDER = ProviderSpec(
    key="azure",
    display_name="Azure DNS",
    category="dns_host",
    docs_url="https://learn.microsoft.com/en-us/rest/api/dns/",
    credentials=("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_SUBSCRIPTION_ID"),
    capabilities=DNS_ONLY,
    notes="Azure DNS manages hosted zones and record sets; registrar delegation is handled elsewhere.",
)
