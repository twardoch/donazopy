# this_file: src/donazopy/providers/registry.py

from __future__ import annotations

from collections.abc import Mapping

import httpx

from donazopy.models import ProviderSpec
from donazopy.providers import cloudflare
from donazopy.providers.base import DNSHostingProvider, RegistrarProvider

_OPERATIONAL_PROVIDERS: tuple[ProviderSpec, ...] = (cloudflare.PROVIDER,)
_PROVIDERS_BY_KEY = {provider.key: provider for provider in _OPERATIONAL_PROVIDERS}


def list_providers() -> tuple[ProviderSpec, ...]:
    return tuple(sorted(_OPERATIONAL_PROVIDERS, key=lambda provider: provider.key))


def get_provider(key: str) -> ProviderSpec:
    try:
        return _PROVIDERS_BY_KEY[key]
    except KeyError as error:
        available = ", ".join(sorted(_PROVIDERS_BY_KEY))
        raise KeyError(f"unknown operational provider {key!r}; available providers: {available}") from error


def create_dns_provider(
    key: str,
    credentials: Mapping[str, str],
    *,
    client: httpx.Client | None = None,
) -> DNSHostingProvider:
    if key == cloudflare.PROVIDER.key:
        return cloudflare.CloudflareProvider(credentials, client=client)
    raise KeyError(f"unknown operational DNS provider {key!r}")


def create_registrar_provider(
    key: str,
    credentials: Mapping[str, str],
    *,
    client: httpx.Client | None = None,
) -> RegistrarProvider:
    if key == cloudflare.PROVIDER.key:
        return cloudflare.CloudflareProvider(credentials, client=client)
    raise KeyError(f"unknown operational registrar provider {key!r}")
