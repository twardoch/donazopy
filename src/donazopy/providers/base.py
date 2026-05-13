# this_file: src/donazopy/providers/base.py

from __future__ import annotations

import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import httpx
from dotenv import dotenv_values, find_dotenv

from donazopy.models import ProviderCapability, ProviderSpec

TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_RETRY_MAX_ATTEMPTS = 4
_RETRY_BASE_DELAY_SECONDS = 1.0


def http_request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    **kwargs: object,
) -> httpx.Response:
    """Send an HTTP request, retrying transient 429 / 5xx responses with exponential backoff.

    Used by every provider adapter so bulk runs (``donazopy copy cloudflare/* …``,
    ``doctor cloudflare/*``) survive transient infrastructure blips and per-API
    rate limits without aborting on the first failure.
    """
    last_response: httpx.Response | None = None
    for attempt in range(_RETRY_MAX_ATTEMPTS + 1):
        response = client.request(method, url, **kwargs)  # type: ignore[arg-type]
        last_response = response
        if response.status_code not in TRANSIENT_STATUS_CODES:
            return response
        if attempt == _RETRY_MAX_ATTEMPTS:
            break
        time.sleep(_RETRY_BASE_DELAY_SECONDS * (2 ** attempt))
    assert last_response is not None
    return last_response


ZONE_READ = ProviderCapability("zone_read", "Read hosted DNS zones and records.")
ZONE_WRITE = ProviderCapability("zone_write", "Create, update, delete, or import hosted DNS records.")
ZONE_EXPORT = ProviderCapability("zone_export", "Export DNS configuration to BIND-compatible zone text.")
ZONE_IMPORT = ProviderCapability("zone_import", "Import or synchronize DNS configuration from zone text.")
DELEGATION_READ = ProviderCapability("delegation_read", "Read registrar-level nameserver delegation.")
DOMAIN_READ = ProviderCapability("domain_read", "List or inspect registered domains.")

DNS_ONLY = (ZONE_READ, ZONE_WRITE, ZONE_EXPORT, ZONE_IMPORT)
DNS_AND_REGISTRAR_READ = DNS_ONLY + (DOMAIN_READ, DELEGATION_READ)
DNS_AND_REGISTRAR = DNS_AND_REGISTRAR_READ


class ProviderError(RuntimeError):
    pass


class ProviderCredentialError(ProviderError):
    pass


class ProviderAPIError(ProviderError):
    pass


@dataclass(frozen=True, slots=True)
class CredentialStatus:
    provider_key: str
    required: tuple[str, ...]
    present: tuple[str, ...]
    missing: tuple[str, ...]
    sources: Mapping[str, str]

    @property
    def is_complete(self) -> bool:
        return not self.missing

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_key": self.provider_key,
            "required": list(self.required),
            "present": list(self.present),
            "missing": list(self.missing),
            "complete": self.is_complete,
            "sources": dict(self.sources),
            "redacted": dict.fromkeys(self.present, "***"),
        }


@dataclass(frozen=True, slots=True)
class LoadedCredentials:
    values: Mapping[str, str]
    sources: Mapping[str, str]


@runtime_checkable
class DNSHostingProvider(Protocol):
    spec: ProviderSpec

    def export_zone(self, domain: str) -> str: ...

    def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> Mapping[str, object]: ...

    def list_records(self, domain: str) -> list[Mapping[str, object]]: ...

    def delete_all_records(self, domain: str) -> Mapping[str, object]:
        """Delete every deletable record in a zone.

        Implementations that cannot do this should raise :class:`ProviderAPIError`.
        """
        ...

    def list_zones(self) -> list[str]:
        """Return all zone names hosted by the provider.

        Implementations that cannot enumerate zones should raise :class:`ProviderAPIError`.
        """
        ...

    def create_zone(self, domain: str) -> Mapping[str, object]:
        """Create a hosted zone for ``domain`` and return the provider's zone object.

        Implementations should be idempotent (returning the existing zone if it already
        exists) and should raise :class:`ProviderAPIError` if they cannot create zones.
        """
        ...


@runtime_checkable
class RegistrarProvider(Protocol):
    spec: ProviderSpec

    def read_nameservers(self, domain: str) -> tuple[str, ...]: ...

    def assign_nameservers(self, domain: str, nameservers: Sequence[str]) -> Mapping[str, object]:
        """Set registrar nameserver delegation for a domain.

        Implementations that cannot do this should raise :class:`ProviderAPIError`.
        """
        ...


def dotenv_environment(
    *,
    dotenv_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    discover: bool = True,
) -> LoadedCredentials:
    merged: dict[str, str] = {}
    sources: dict[str, str] = {}

    discovered = find_dotenv(usecwd=True) if discover else ""
    dotenv_files = [Path(discovered)] if discovered else []
    if dotenv_path is not None:
        dotenv_files.append(dotenv_path)

    for path in dotenv_files:
        if path.exists():
            for key, value in dotenv_values(path).items():
                if value:
                    merged[key] = value
                    sources[key] = str(path)

    environment = os.environ if env is None else env
    for key, value in environment.items():
        if value:
            merged[key] = value
            sources[key] = "environment"

    return LoadedCredentials(values=merged, sources=sources)


def load_provider_credentials(
    spec: ProviderSpec,
    *,
    dotenv_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    discover: bool = True,
) -> dict[str, str]:
    loaded = dotenv_environment(dotenv_path=dotenv_path, env=env, discover=discover)
    return {name: loaded.values[name] for name in spec.credentials if loaded.values.get(name)}


def credential_status(
    spec: ProviderSpec,
    *,
    dotenv_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    discover: bool = True,
) -> CredentialStatus:
    loaded = dotenv_environment(dotenv_path=dotenv_path, env=env, discover=discover)
    credentials = {name: loaded.values[name] for name in spec.credentials if loaded.values.get(name)}
    present = tuple(name for name in spec.credentials if name in credentials)
    missing = tuple(name for name in spec.credentials if name not in credentials)
    sources = {name: loaded.sources[name] for name in present if name in loaded.sources}
    return CredentialStatus(
        provider_key=spec.key, required=spec.credentials, present=present, missing=missing, sources=sources
    )


def require_provider_credentials(
    spec: ProviderSpec,
    *,
    dotenv_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    discover: bool = True,
) -> dict[str, str]:
    status = credential_status(spec, dotenv_path=dotenv_path, env=env, discover=discover)
    if not status.is_complete:
        missing = ", ".join(status.missing)
        raise ProviderCredentialError(f"missing required credentials for {spec.key}: {missing}")
    return load_provider_credentials(spec, dotenv_path=dotenv_path, env=env, discover=discover)


__all__ = [
    "CredentialStatus",
    "DELEGATION_READ",
    "DNSHostingProvider",
    "DNS_AND_REGISTRAR",
    "DNS_AND_REGISTRAR_READ",
    "DNS_ONLY",
    "DOMAIN_READ",
    "LoadedCredentials",
    "ProviderAPIError",
    "ProviderCapability",
    "ProviderCredentialError",
    "ProviderError",
    "ProviderSpec",
    "RegistrarProvider",
    "ZONE_EXPORT",
    "ZONE_IMPORT",
    "ZONE_READ",
    "ZONE_WRITE",
    "credential_status",
    "dotenv_environment",
    "load_provider_credentials",
    "require_provider_credentials",
]
