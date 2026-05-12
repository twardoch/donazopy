# this_file: src/donazopy/providers/aws.py
from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderSpec

PROVIDER = ProviderSpec(
    key="aws",
    display_name="AWS Route 53",
    category="dns_and_registrar",
    docs_url="https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/route53.html",
    credentials=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"),
    capabilities=DNS_AND_REGISTRAR,
    notes="Route 53 separates hosted-zone record changes from domain registration and nameserver operations.",
)
