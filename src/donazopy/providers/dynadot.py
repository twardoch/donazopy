# this_file: src/donazopy/providers/dynadot.py

from donazopy.models import ProviderSpec
from donazopy.providers.base import DNS_AND_REGISTRAR

PROVIDER = ProviderSpec(
    key="dynadot",
    display_name="Dynadot",
    category="dns_and_registrar",
    docs_url="https://www.dynadot.com/domain/api.html",
    credentials=("DYNADOT_API_KEY",),
    capabilities=DNS_AND_REGISTRAR,
    notes="Dynadot exposes domain and DNS commands through its API; endpoint behavior needs contract tests before writes.",
)
