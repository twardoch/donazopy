# this_file: src/donazopy/providers/godaddy.py
"""GoDaddy DNS and domains adapter built on the GoDaddy API (api.godaddy.com/v1).

Reference: https://developer.godaddy.com/doc/endpoint/domains

Auth uses the ``Authorization: sso-key {key}:{secret}`` header. Records are
relative to the domain (``@`` for the apex). GoDaddy keeps ``MX``/``SRV``
priority (and ``SRV`` weight/port) in dedicated fields rather than in the rdata.
The ``SOA`` record is managed by GoDaddy and must not be re-imported.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import httpx

from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderAPIError, ProviderSpec
from donazopy.zonefile import NormalizedRecord, build_bind_zone, records_from_zone_text

PROVIDER = ProviderSpec(
    key="godaddy",
    display_name="GoDaddy",
    category="dns_and_registrar",
    docs_url="https://developer.godaddy.com/doc/endpoint/domains",
    credentials=("GODADDY_API_KEY", "GODADDY_API_SECRET"),
    capabilities=DNS_AND_REGISTRAR,
    notes=(
        "Operational adapter for GoDaddy: list domains, export/import DNS records, and read "
        "or assign registrar nameservers. The SOA record is managed by GoDaddy."
    ),
)

# GoDaddy manages the SOA record; it is read-only and must not be re-imported.
_MANAGED_TYPES = {"SOA"}


class GoDaddyProvider:
    api_base = "https://api.godaddy.com/v1"
    spec = PROVIDER

    def __init__(self, credentials: Mapping[str, str], *, client: httpx.Client | None = None) -> None:
        key = credentials.get("GODADDY_API_KEY")
        secret = credentials.get("GODADDY_API_SECRET")
        if not key or not secret:
            missing = ", ".join(
                name for name, value in (("GODADDY_API_KEY", key), ("GODADDY_API_SECRET", secret)) if not value
            )
            raise ProviderAPIError(f"missing required credentials for godaddy: {missing}")
        self._client = client or httpx.Client(timeout=30.0)
        self._headers = {"Authorization": f"sso-key {key}:{secret}", "Accept": "application/json"}

    # -- public API -------------------------------------------------------

    def list_zones(self) -> list[str]:
        payload = self._request("GET", "/domains", params={"limit": 1000})
        if not isinstance(payload, list):
            raise ProviderAPIError("GoDaddy domains response was not a JSON array")
        return [str(item["domain"]) for item in payload if isinstance(item, dict) and item.get("domain")]

    def create_zone(self, domain: str) -> Mapping[str, object]:
        msg = (
            "creating zones is not supported by the GoDaddy adapter: the DNS zone for a domain "
            f"exists once the domain is registered with GoDaddy. Register {domain!r} first, then "
            "use 'import-zone' to populate its records."
        )
        raise ProviderAPIError(msg)

    def list_records(self, domain: str) -> list[Mapping[str, object]]:
        return self._records(domain)

    def export_zone(self, domain: str) -> str:
        origin = domain.rstrip(".") + "."
        return build_bind_zone(
            origin, [{**record, "content": record.get("data", "")} for record in self._records(domain)]
        )

    def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> Mapping[str, object]:
        origin = domain.rstrip(".") + "."
        payload = [
            self._to_godaddy_record(record, origin)
            for record in records_from_zone_text(zone_text, origin)
            if record.record_type.upper() not in _MANAGED_TYPES
        ]
        if not payload:
            return {"added": 0}
        # PATCH appends the given records to the existing record set.
        self._request("PATCH", f"/domains/{domain.rstrip('.')}/records", json=payload)
        return {"added": len(payload)}

    def delete_all_records(self, domain: str) -> Mapping[str, object]:
        targets: list[tuple[str, str]] = []
        for record in self._records(domain):
            rtype = str(record.get("type", "")).upper()
            name = str(record.get("name", "@")) or "@"
            if rtype in _MANAGED_TYPES or (rtype == "NS" and name == "@"):
                continue
            if (rtype, name) not in targets:
                targets.append((rtype, name))
        deleted = 0
        failed = 0
        for rtype, name in targets:
            response = self._client.request(
                "DELETE", f"{self.api_base}/domains/{domain.rstrip('.')}/records/{rtype}/{name}", headers=self._headers
            )
            if response.status_code >= 400:
                failed += 1
            else:
                deleted += 1
        return {"deleted": deleted, "failed": failed}

    def read_nameservers(self, domain: str) -> tuple[str, ...]:
        payload = self._request("GET", f"/domains/{domain.rstrip('.')}")
        if not isinstance(payload, dict):
            raise ProviderAPIError(f"GoDaddy domain response was malformed for {domain}")
        nameservers = payload.get("nameServers", [])
        if not isinstance(nameservers, list):
            return ()
        return tuple(str(nameserver).rstrip(".") for nameserver in nameservers if nameserver)

    def assign_nameservers(self, domain: str, nameservers: Sequence[str]) -> Mapping[str, object]:
        cleaned = [nameserver.strip().rstrip(".") for nameserver in nameservers if nameserver.strip()]
        if not cleaned:
            raise ProviderAPIError("assign_nameservers requires at least one nameserver")
        self._request("PUT", f"/domains/{domain.rstrip('.')}", json={"nameServers": cleaned})
        return {"domain": domain.rstrip("."), "nameservers": cleaned}

    # -- internals --------------------------------------------------------

    def _records(self, domain: str) -> list[Mapping[str, object]]:
        payload = self._request("GET", f"/domains/{domain.rstrip('.')}/records")
        if not isinstance(payload, list):
            raise ProviderAPIError(f"GoDaddy records response was not a JSON array for {domain}")
        return [record for record in payload if isinstance(record, dict)]

    @staticmethod
    def _to_godaddy_record(record: NormalizedRecord, origin: str) -> dict[str, object]:
        rtype = record.record_type.upper()
        bare_origin = origin.rstrip(".")
        owner = record.owner.rstrip(".")
        if owner in {bare_origin, ""}:
            name = "@"
        elif owner.endswith("." + bare_origin):
            name = owner[: -len(bare_origin) - 1]
        else:
            name = owner
        entry: dict[str, object] = {"type": rtype, "name": name, "ttl": int(record.ttl)}
        parts = record.value.split()
        if rtype == "MX" and len(parts) >= 2 and parts[0].isdigit():
            entry["priority"] = int(parts[0])
            entry["data"] = " ".join(parts[1:])
        elif rtype == "SRV" and len(parts) >= 4 and all(part.isdigit() for part in parts[:3]):
            entry["priority"] = int(parts[0])
            entry["weight"] = int(parts[1])
            entry["port"] = int(parts[2])
            entry["data"] = " ".join(parts[3:])
        elif rtype == "TXT":
            entry["data"] = _unquote_txt(record.value)
        else:
            entry["data"] = record.value
        return entry

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        json: object | None = None,
    ) -> object:
        headers = dict(self._headers)
        if json is not None:
            headers["Content-Type"] = "application/json"
        response = self._client.request(method, f"{self.api_base}{path}", headers=headers, params=params, json=json)
        if response.status_code >= 400:
            raise ProviderAPIError(_godaddy_error_message(response))
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as error:
            raise ProviderAPIError("GoDaddy response was not valid JSON") from error


def _unquote_txt(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\"', '"')
    return value


def _godaddy_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"GoDaddy API error {response.status_code}: {response.text[:200]}"
    if isinstance(payload, dict):
        message = payload.get("message")
        fields = payload.get("fields")
        if isinstance(fields, list) and fields:
            details = "; ".join(str(field.get("message", field)) for field in fields if isinstance(field, dict))
            return f"GoDaddy API error: {message or 'invalid request'} ({details})"
        if message:
            return f"GoDaddy API error: {message}"
    return f"GoDaddy API error {response.status_code}"
