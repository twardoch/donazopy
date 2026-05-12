# this_file: src/donazopy/providers/registry.py

from __future__ import annotations

from collections.abc import Mapping

import httpx

from donazopy.models import ProviderSpec
from donazopy.providers import cloudflare, godaddy, ionos, joker
from donazopy.providers.base import DNSHostingProvider, RegistrarProvider

_OPERATIONAL_PROVIDERS: tuple[ProviderSpec, ...] = (
    cloudflare.PROVIDER,
    godaddy.PROVIDER,
    ionos.PROVIDER,
    joker.PROVIDER,
)
_PROVIDERS_BY_KEY = {provider.key: provider for provider in _OPERATIONAL_PROVIDERS}

# Every operational provider currently implements both the DNS hosting and registrar
# Protocols, so a single factory table serves both creation entry points.
_PROVIDER_FACTORIES = {
    cloudflare.PROVIDER.key: cloudflare.CloudflareProvider,
    godaddy.PROVIDER.key: godaddy.GoDaddyProvider,
    ionos.PROVIDER.key: ionos.IonosProvider,
    joker.PROVIDER.key: joker.JokerProvider,
}


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
    try:
        factory = _PROVIDER_FACTORIES[key]
    except KeyError as error:
        raise KeyError(f"unknown operational DNS provider {key!r}") from error
    return factory(credentials, client=client)


def create_registrar_provider(
    key: str,
    credentials: Mapping[str, str],
    *,
    client: httpx.Client | None = None,
) -> RegistrarProvider:
    try:
        factory = _PROVIDER_FACTORIES[key]
    except KeyError as error:
        raise KeyError(f"unknown operational registrar provider {key!r}") from error
    return factory(credentials, client=client)
