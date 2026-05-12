# this_file: src/donazopy/providers/linode.py
from donazopy.providers.base import DNS_ONLY, ProviderSpec

PROVIDER = ProviderSpec(
    key="linode",
    display_name="Linode DNS",
    category="dns_host",
    docs_url="https://techdocs.akamai.com/linode-api/reference/get-domains",
    credentials=("LINODE_TOKEN",),
    capabilities=DNS_ONLY,
    notes="Linode DNS exposes domain and record APIs for hosted-zone management.",
)
