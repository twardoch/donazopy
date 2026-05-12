# this_file: src/donazopy/cli.py

from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

from donazopy import __version__
from donazopy.providers.base import credential_status, require_provider_credentials
from donazopy.providers.registry import create_dns_provider, create_registrar_provider, get_provider, list_providers
from donazopy.zonefile import diff_zone_files, normalize_zone_file, validate_zone_file, write_text_safely


class ProviderMetadata(TypedDict):
    key: str
    display_name: str
    category: str
    docs_url: str
    credentials: list[str]
    capabilities: list[str]
    notes: str


class Donazopy:
    def version(self) -> str:
        return __version__

    def providers(self) -> list[str]:
        return [provider.key for provider in list_providers()]

    def provider(self, key: str) -> ProviderMetadata:
        provider = get_provider(key)
        return {
            "key": provider.key,
            "display_name": provider.display_name,
            "category": provider.category,
            "docs_url": provider.docs_url,
            "credentials": list(provider.credentials),
            "capabilities": [capability.name for capability in provider.capabilities],
            "notes": provider.notes,
        }

    def provider_status(self, key: str, dotenv_path: str | None = None) -> dict[str, object]:
        provider = get_provider(key)
        status = credential_status(provider, dotenv_path=None if dotenv_path is None else Path(dotenv_path))
        return status.to_dict()

    def provider_records(self, key: str, domain: str, dotenv_path: str | None = None) -> list[Mapping[str, object]]:
        provider = get_provider(key)
        credentials = require_provider_credentials(provider, dotenv_path=None if dotenv_path is None else Path(dotenv_path))
        return create_dns_provider(key, credentials).list_records(domain)

    def provider_export_zone(
        self,
        key: str,
        domain: str,
        dotenv_path: str | None = None,
        output: str | None = None,
        overwrite: bool = False,
    ) -> str:
        provider = get_provider(key)
        credentials = require_provider_credentials(provider, dotenv_path=None if dotenv_path is None else Path(dotenv_path))
        zone_text = create_dns_provider(key, credentials).export_zone(domain)
        if output is not None:
            write_text_safely(Path(output), zone_text, overwrite=overwrite)
        return zone_text

    def provider_import_zone(
        self,
        key: str,
        domain: str,
        path: str,
        dotenv_path: str | None = None,
        proxied: bool | None = None,
    ) -> Mapping[str, object]:
        provider = get_provider(key)
        credentials = require_provider_credentials(provider, dotenv_path=None if dotenv_path is None else Path(dotenv_path))
        zone_text = Path(path).read_text(encoding="utf-8")
        return create_dns_provider(key, credentials).import_zone(domain, zone_text, proxied=proxied)

    def provider_nameservers(self, key: str, domain: str, dotenv_path: str | None = None) -> list[str]:
        provider = get_provider(key)
        credentials = require_provider_credentials(provider, dotenv_path=None if dotenv_path is None else Path(dotenv_path))
        return list(create_registrar_provider(key, credentials).read_nameservers(domain))

    def validate_zone(self, path: str, origin: str | None = None) -> str:
        return validate_zone_file(Path(path), origin)

    def zone_normalize(
        self,
        path: str,
        origin: str | None = None,
        output: str | None = None,
        overwrite: bool = False,
    ) -> str:
        normalized = normalize_zone_file(Path(path), origin)
        if output is not None:
            write_text_safely(Path(output), normalized, overwrite=overwrite)
        return normalized

    def zone_dump(
        self,
        path: str,
        origin: str | None = None,
        output: str | None = None,
        overwrite: bool = False,
    ) -> str:
        return self.zone_normalize(path, origin=origin, output=output, overwrite=overwrite)

    def zone_diff(self, before: str, after: str, origin: str | None = None) -> dict[str, object]:
        diff = diff_zone_files(Path(before), Path(after), origin)
        return {"summary": diff.summary(), "changes": diff.to_dict()}
