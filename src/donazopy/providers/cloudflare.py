# this_file: src/donazopy/providers/cloudflare.py

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

import httpx

from donazopy.providers.base import (
    DNS_AND_REGISTRAR_READ,
    ProviderAPIError,
    ProviderSpec,
)
from donazopy.providers.base import (
    http_request_with_retry as _request_with_retry,
)

PROVIDER = ProviderSpec(
    key="cloudflare",
    display_name="Cloudflare",
    category="dns_and_registrar",
    docs_url="https://developers.cloudflare.com/api/",
    credentials=("CLOUDFLARE_DNS_TOKEN",),
    capabilities=DNS_AND_REGISTRAR_READ,
    notes="Operational DNS adapter for Cloudflare zones: list records, export/import BIND zones, and read assigned nameservers.",
)


class CloudflareProvider:
    api_base = "https://api.cloudflare.com/client/v4"
    spec = PROVIDER

    def __init__(self, credentials: Mapping[str, str], *, client: httpx.Client | None = None) -> None:
        token = credentials.get("CLOUDFLARE_DNS_TOKEN")
        if not token:
            msg = "missing required credentials for cloudflare: CLOUDFLARE_DNS_TOKEN"
            raise ProviderAPIError(msg)
        self._client = client or httpx.Client(timeout=30.0)
        self._headers = {"Authorization": f"Bearer {token}"}

    def list_records(self, domain: str) -> list[Mapping[str, object]]:
        zone = self._zone(domain)
        records: list[Mapping[str, object]] = []
        page = 1
        while True:
            payload = self._request(
                "GET",
                f"/zones/{zone['id']}/dns_records",
                params={"page": page, "per_page": 100},
            )
            result = payload.get("result", [])
            if not isinstance(result, list):
                raise ProviderAPIError("Cloudflare DNS record response did not contain a result list")
            records.extend(record for record in result if isinstance(record, dict))
            info = payload.get("result_info", {})
            if not isinstance(info, dict) or page >= int(info.get("total_pages", 1)):
                break
            page += 1
        return records

    def export_zone(self, domain: str) -> str:
        zone = self._zone(domain)
        response = _request_with_retry(
            self._client,
            "GET",
            f"{self.api_base}/zones/{zone['id']}/dns_records/export",
            headers=self._headers,
        )
        if response.status_code >= 400:
            raise ProviderAPIError(_cloudflare_error_message(response))
        return response.text

    def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> Mapping[str, object]:
        zone = self._zone(domain)
        files = {"file": (f"{domain.rstrip('.')}.zone", zone_text.encode("utf-8"), "text/plain")}
        data = {} if proxied is None else {"proxied": str(proxied).lower()}
        payload = self._request("POST", f"/zones/{zone['id']}/dns_records/import", files=files, data=data)
        result = payload.get("result", {})
        return result if isinstance(result, dict) else {"result": result}

    def read_nameservers(self, domain: str) -> tuple[str, ...]:
        zone = self._zone(domain)
        nameservers = zone.get("name_servers", ())
        if not isinstance(nameservers, list):
            return ()
        return tuple(str(nameserver) for nameserver in nameservers)

    def assign_nameservers(self, domain: str, nameservers: Sequence[str]) -> Mapping[str, object]:
        msg = (
            "nameserver assignment is not supported by the Cloudflare adapter: the "
            "Cloudflare DNS API cannot set registrar delegation for a zone. Update the "
            f"delegation for {domain!r} at the registrar that holds the domain. "
            "Use the 'nameservers' command without arguments to read Cloudflare's "
            "assigned nameservers."
        )
        raise ProviderAPIError(msg)

    def list_zones(self) -> list[str]:
        names: list[str] = []
        page = 1
        while True:
            payload = self._request("GET", "/zones", params={"page": page, "per_page": 50})
            result = payload.get("result", [])
            if not isinstance(result, list):
                raise ProviderAPIError("Cloudflare zones response did not contain a result list")
            names.extend(str(zone["name"]) for zone in result if isinstance(zone, dict) and zone.get("name"))
            info = payload.get("result_info", {})
            if not isinstance(info, dict) or page >= int(info.get("total_pages", 1)):
                break
            page += 1
        return names

    def create_zone(self, domain: str) -> Mapping[str, object]:
        """Create a Cloudflare zone for ``domain`` (idempotent: returns the existing zone if present).

        The Cloudflare account is taken from ``CLOUDFLARE_DNS_ACCOUNT`` if set, otherwise it is
        auto-detected when the API token has access to exactly one account.
        """
        name = domain.rstrip(".")
        try:
            return self._zone(name)
        except ProviderAPIError:
            pass  # zone does not exist yet — create it below
        try:
            payload = self._request("POST", "/zones", json={"name": name, "account": {"id": self._account_id()}})
        except ProviderAPIError as error:
            message = str(error).lower()
            if "already exists" in message or "1061" in message:
                return self._zone(name)
            raise
        result = payload.get("result", {})
        return result if isinstance(result, dict) else {"result": result}

    def _account_id(self) -> str:
        configured = os.environ.get("CLOUDFLARE_DNS_ACCOUNT")
        if configured:
            return configured
        payload = self._request("GET", "/accounts", params={"per_page": 50})
        result = payload.get("result", [])
        accounts = (
            [account for account in result if isinstance(account, dict) and account.get("id")]
            if isinstance(result, list)
            else []
        )
        if len(accounts) == 1:
            return str(accounts[0]["id"])
        if not accounts:
            raise ProviderAPIError(
                "could not determine a Cloudflare account for zone creation: the API token cannot "
                "list accounts. Set CLOUDFLARE_DNS_ACCOUNT."
            )
        raise ProviderAPIError(
            "the Cloudflare API token has access to multiple accounts; set CLOUDFLARE_DNS_ACCOUNT "
            "to choose one for zone creation."
        )

    def delete_record(self, domain: str, record_id: str) -> Mapping[str, object]:
        """Delete a single DNS record by its Cloudflare id."""
        zone = self._zone(domain)
        response = _request_with_retry(
            self._client,
            "DELETE",
            f"{self.api_base}/zones/{zone['id']}/dns_records/{record_id}",
            headers=self._headers,
        )
        if response.status_code >= 400:
            raise ProviderAPIError(_cloudflare_error_message(response))
        payload = response.json()
        if not isinstance(payload, dict):
            raise ProviderAPIError("Cloudflare response was not a JSON object")
        result = payload.get("result", {})
        return result if isinstance(result, dict) else {"result": result}

    def create_record(self, domain: str, record: Mapping[str, object]) -> Mapping[str, object]:
        """Create a single DNS record in ``domain``.

        ``record`` is a Cloudflare-shaped dict (``type``, ``name``, ``content``,
        optionally ``ttl``, ``proxied``, ``priority``). Idempotent only at the
        API level: Cloudflare rejects exact duplicates with a 81057 error.
        """
        zone = self._zone(domain)
        payload = self._request("POST", f"/zones/{zone['id']}/dns_records", json=dict(record))
        result = payload.get("result", {})
        return result if isinstance(result, dict) else {"result": result}

    def delete_all_records(self, domain: str) -> Mapping[str, object]:
        zone = self._zone(domain)
        zone_id = zone["id"]
        deleted = 0
        failed = 0
        for record in self.list_records(domain):
            record_id = record.get("id")
            if not record_id:
                continue
            response = self._client.request(
                "DELETE",
                f"{self.api_base}/zones/{zone_id}/dns_records/{record_id}",
                headers=self._headers,
            )
            if response.status_code >= 400:
                failed += 1
                continue
            deleted += 1
        return {"deleted": deleted, "failed": failed}

    def _zone(self, domain: str) -> Mapping[str, object]:
        name = domain.rstrip(".")
        payload = self._request("GET", "/zones", params={"name": name, "per_page": 1})
        result = payload.get("result", [])
        if not isinstance(result, list) or not result:
            raise ProviderAPIError(f"Cloudflare zone not found: {name}")
        zone = result[0]
        if not isinstance(zone, dict) or not zone.get("id"):
            raise ProviderAPIError(f"Cloudflare zone response was malformed for {name}")
        return zone

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        data: Mapping[str, str] | None = None,
        files: Mapping[str, tuple[str, bytes, str]] | None = None,
        json: object | None = None,
    ) -> Mapping[str, object]:
        response = _request_with_retry(
            self._client,
            method,
            f"{self.api_base}{path}",
            headers=self._headers,
            params=params,
            data=data,
            files=files,
            json=json,
        )
        if response.status_code >= 400:
            raise ProviderAPIError(_cloudflare_error_message(response))
        payload = response.json()
        if not isinstance(payload, dict):
            raise ProviderAPIError("Cloudflare response was not a JSON object")
        success = payload.get("success", True)
        if success is False:
            raise ProviderAPIError(_cloudflare_payload_error(payload))
        return payload


def _cloudflare_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"Cloudflare API error {response.status_code}: {response.text}"
    if isinstance(payload, dict):
        return _cloudflare_payload_error(payload)
    return f"Cloudflare API error {response.status_code}"


def _cloudflare_payload_error(payload: Mapping[str, object]) -> str:
    errors = payload.get("errors", [])
    if isinstance(errors, list) and errors:
        messages = []
        for error in errors:
            if isinstance(error, dict):
                messages.append(str(error.get("message", error)))
            else:
                messages.append(str(error))
        return "Cloudflare API error: " + "; ".join(messages)
    return "Cloudflare API error"
