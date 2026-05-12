# this_file: src/donazopy/providers/google_cloud.py
from donazopy.providers.base import DNS_ONLY, ProviderSpec

PROVIDER = ProviderSpec(
    key="google_cloud",
    display_name="Google Cloud DNS",
    category="dns_host",
    docs_url="https://cloud.google.com/dns/docs/reference/v1/",
    credentials=("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT"),
    capabilities=DNS_ONLY,
    notes="Cloud DNS provides managed-zone and record-set changes; Cloud Domains delegation belongs to a separate API surface.",
)
