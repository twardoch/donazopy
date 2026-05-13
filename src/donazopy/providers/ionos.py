# this_file: src/donazopy/providers/ionos.py
"""IONOS DNS adapter built on the IONOS DNS API (api.hosting.ionos.com/dns/v1)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import httpx

from donazopy.providers.base import DNS_AND_REGISTRAR_READ, ProviderAPIError, ProviderSpec
from donazopy.zonefile import NormalizedRecord, build_bind_zone, records_from_zone_text

PROVIDER = ProviderSpec(
    key="ionos",
    display_name="IONOS",
    category="dns_and_registrar",
    docs_url="https://developer.hosting.ionos.com/docs/dns",
    credentials=("IONOS_API_PUBLIC", "IONOS_API_SECRET"),
    capabilities=DNS_AND_REGISTRAR_READ,
    notes=(
        "Operational DNS adapter for IONOS zones: list records, export/import BIND zones, "
        "and read apex nameservers. Registrar delegation changes are not exposed by the "
        "IONOS DNS API."
    ),
)

# IONOS manages the SOA record itself; it is read-only and must not be re-imported.
_MANAGED_TYPES = {"SOA"}


class IonosProvider:
    api_base = "https://api.hosting.ionos.com/dns/v1"
    spec = PROVIDER

    def __init__(self, credentials: Mapping[str, str], *, client: httpx.Client | None = None) -> None:
        public = credentials.get("IONOS_API_PUBLIC")
        secret = credentials.get("IONOS_API_SECRET")
        if not public or not secret:
            missing = ", ".join(
                name for name, value in (("IONOS_API_PUBLIC", public), ("IONOS_API_SECRET", secret)) if not value
            )
            raise ProviderAPIError(f"missing required credentials for ionos: {missing}")
        self._client = client or httpx.Client(timeout=30.0)
        self._headers = {"X-API-Key": f"{public}.{secret}"}

    # -- public API -------------------------------------------------------

    def list_zones(self) -> list[str]:
        return [str(zone["name"]) for zone in self._zones() if zone.get("name")]

    def create_zone(self, domain: str) -> Mapping[str, object]:
        msg = (
            "creating zones is not supported by the IONOS DNS adapter: a DNS zone is created "
            f"automatically when the domain {domain!r} is added to the IONOS account. Add the "
            "domain in the IONOS domain management area first."
        )
        raise ProviderAPIError(msg)

    def list_records(self, domain: str) -> list[Mapping[str, object]]:
        return self._records_of(self._zone_detail(domain))

    def export_zone(self, domain: str) -> str:
        detail = self._zone_detail(domain)
        origin = str(detail.get("name") or domain).rstrip(".") + "."
        return build_bind_zone(origin, self._records_of(detail))

    def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> Mapping[str, object]:
        detail = self._zone_detail(domain)
        origin = str(detail.get("name") or domain).rstrip(".") + "."
        payload = [
            self._to_ionos_record(record)
            for record in records_from_zone_text(zone_text, origin)
            if record.record_type.upper() not in _MANAGED_TYPES
        ]
        if not payload:
            return {"created": 0}
        zone_id = detail["id"]
        try:
            self._request("POST", f"/zones/{zone_id}/records", json=payload)
            return {"created": len(payload)}
        except ProviderAPIError as batch_error:
            # IONOS rejects the whole batch when even one record is invalid.
            # Retry per-record so we import what we can and surface what we cannot.
            created = 0
            rejected: list[Mapping[str, object]] = []
            for record in payload:
                try:
                    self._request("POST", f"/zones/{zone_id}/records", json=[record])
                    created += 1
                except ProviderAPIError as single_error:
                    rejected.append(
                        {
                            "name": record["name"],
                            "type": record["type"],
                            "content": record["content"],
                            "error": str(single_error),
                        }
                    )
            if rejected and created == 0:
                # Nothing went through — preserve the original error context.
                summary = "; ".join(
                    f"{entry['name']} {entry['type']} ({entry['content']!r})" for entry in rejected[:5]
                )
                msg = (
                    f"IONOS rejected every record. First {min(5, len(rejected))} of "
                    f"{len(rejected)}: {summary}. Original batch error: {batch_error}"
                )
                raise ProviderAPIError(msg) from batch_error
            return {"created": created, "rejected": rejected}

    def delete_all_records(self, domain: str) -> Mapping[str, object]:
        detail = self._zone_detail(domain)
        zone_id = detail["id"]
        deleted = 0
        failed = 0
        for record in self._records_of(detail):
            if str(record.get("type", "")).upper() in _MANAGED_TYPES:
                continue
            record_id = record.get("id")
            if not record_id:
                continue
            response = self._client.request(
                "DELETE", f"{self.api_base}/zones/{zone_id}/records/{record_id}", headers=self._headers
            )
            if response.status_code >= 400:
                failed += 1
            else:
                deleted += 1
        return {"deleted": deleted, "failed": failed}

    def read_nameservers(self, domain: str) -> tuple[str, ...]:
        name = domain.rstrip(".")
        nameservers = [
            str(record.get("content", "")).rstrip(".")
            for record in self._records_of(self._zone_detail(domain))
            if str(record.get("type", "")).upper() == "NS" and str(record.get("name", "")).rstrip(".") == name
        ]
        return tuple(dict.fromkeys(nameserver for nameserver in nameservers if nameserver))

    def assign_nameservers(self, domain: str, nameservers: Sequence[str]) -> Mapping[str, object]:
        msg = (
            "nameserver assignment is not supported by the IONOS DNS adapter: the IONOS DNS "
            f"API cannot change registrar delegation for {domain!r}. Update the delegation in "
            "the IONOS domain management area or via the IONOS domains API. Use the "
            "'nameservers' command without arguments to read the zone's NS records."
        )
        raise ProviderAPIError(msg)

    # -- internals --------------------------------------------------------

    def _zones(self) -> list[Mapping[str, object]]:
        payload = self._request("GET", "/zones")
        if not isinstance(payload, list):
            raise ProviderAPIError("IONOS zones response was not a JSON array")
        return [zone for zone in payload if isinstance(zone, dict)]

    def _zone_id(self, domain: str) -> str:
        name = domain.rstrip(".")
        for zone in self._zones():
            if str(zone.get("name", "")).rstrip(".") == name and zone.get("id"):
                return str(zone["id"])
        raise ProviderAPIError(f"IONOS zone not found: {name}")

    def _zone_detail(self, domain: str) -> Mapping[str, object]:
        payload = self._request("GET", f"/zones/{self._zone_id(domain)}")
        if not isinstance(payload, dict) or not payload.get("id"):
            raise ProviderAPIError(f"IONOS zone detail response was malformed for {domain}")
        records = payload.get("records")
        if records is not None and not isinstance(records, list):
            raise ProviderAPIError(f"IONOS zone detail records were malformed for {domain}")
        return payload

    @staticmethod
    def _records_of(detail: Mapping[str, object]) -> list[Mapping[str, object]]:
        records = detail.get("records")
        if not isinstance(records, list):
            return []
        return [record for record in records if isinstance(record, dict)]

    @staticmethod
    def _to_ionos_record(record: NormalizedRecord) -> dict[str, object]:
        rtype = record.record_type.upper()
        content = record.value
        prio = 0
        if rtype in {"MX", "SRV"}:
            head, _, rest = record.value.partition(" ")
            if head.isdigit():
                prio = int(head)
                content = rest.strip()
        if rtype == "TXT":
            content = _unquote_txt(content)
        return {
            "name": record.owner.rstrip("."),
            "type": rtype,
            "content": content,
            "ttl": int(record.ttl),
            "prio": prio,
            "disabled": False,
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        json: object | None = None,
    ) -> object:
        response = self._client.request(
            method, f"{self.api_base}{path}", headers=self._headers, params=params, json=json
        )
        if response.status_code >= 400:
            raise ProviderAPIError(_ionos_error_message(response))
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as error:
            raise ProviderAPIError("IONOS response was not valid JSON") from error


def _unquote_txt(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\"', '"')
    return value


def _ionos_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"IONOS API error {response.status_code}: {response.text[:200]}"
    if isinstance(payload, list):
        messages = [str(item.get("message", item)) for item in payload if isinstance(item, dict)]
        if messages:
            return "IONOS API error: " + "; ".join(messages)
    if isinstance(payload, dict):
        return "IONOS API error: " + str(payload.get("message", payload))
    return f"IONOS API error {response.status_code}"
