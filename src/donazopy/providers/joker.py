# this_file: src/donazopy/providers/joker.py
"""Joker.com DMAPI adapter for registrar delegation and virtual DNS zones.

Reference: https://dmapi.joker.com/ (DMAPI request endpoints).

DMAPI is an HTTP request/response API. Each response is a block of ``Key: Value``
headers, a blank line, then an optional body. ``Status-Code: 0`` means success.
A session is opened by posting an ``api-key`` to ``/request/login`` which returns
an ``Auth-Sid`` header used for subsequent calls.

Virtual DNS zones are exchanged in Joker's own line format:
``<label> <type> <pri> <target> <ttl> <valid-from> <valid-to> [<param>]``
where ``label`` is relative to the domain (``@`` for the apex) and TXT targets are
double-quoted. Joker manages the ``SOA`` record itself, so it is never present in a
zone-get and must not be sent in a zone-put.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

import httpx

from donazopy.providers.base import DNS_AND_REGISTRAR, ProviderAPIError, ProviderSpec
from donazopy.zonefile import NormalizedRecord, build_bind_zone, records_from_zone_text

PROVIDER = ProviderSpec(
    key="joker",
    display_name="Joker.com DMAPI",
    category="dns_and_registrar",
    docs_url="https://dmapi.joker.com/",
    credentials=("JOKER_API_KEY",),
    capabilities=DNS_AND_REGISTRAR,
    notes=(
        "Operational DMAPI adapter for Joker.com: list domains, export/import virtual DNS "
        "zones, and read or assign registrar nameservers. Joker manages the SOA record."
    ),
)

_API_BASE = "https://dmapi.joker.com/request"
# Joker manages the SOA record; it never appears in a zone-get and must not be put.
_MANAGED_TYPES = {"SOA"}
# label, type, pri are plain tokens; target may be a double-quoted string; the rest is plain.
_ZONE_LINE = re.compile(r'^(\S+)\s+(\S+)\s+(\S+)\s+("(?:[^"\\]|\\.)*"|\S+)\s*(.*)$')


class JokerProvider:
    spec = PROVIDER

    def __init__(
        self,
        credentials: Mapping[str, str],
        *,
        client: httpx.Client | None = None,
        api_base: str = _API_BASE,
    ) -> None:
        api_key = credentials.get("JOKER_API_KEY")
        if not api_key:
            raise ProviderAPIError("missing required credentials for joker: JOKER_API_KEY")
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")
        self._client = client or httpx.Client(timeout=30.0)
        self._auth_sid: str | None = None

    # -- public API -------------------------------------------------------

    def list_zones(self) -> list[str]:
        body = self._call("query-domain-list", {})
        domains: list[str] = []
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            domains.append(line.split()[0])
        return domains

    def create_zone(self, domain: str) -> Mapping[str, object]:
        msg = (
            "creating zones is not supported by the Joker DMAPI adapter: a virtual DNS zone "
            f"exists for a domain once it is registered or managed at Joker. Use 'import-zone' "
            f"to populate the zone for {domain!r}."
        )
        raise ProviderAPIError(msg)

    def list_records(self, domain: str) -> list[Mapping[str, object]]:
        return [self._joker_line_to_record(line, domain) for line in self._zone_lines(domain)]

    def export_zone(self, domain: str) -> str:
        origin = domain.rstrip(".") + "."
        records = [self._joker_line_to_record(line, domain) for line in self._zone_lines(domain)]
        return build_bind_zone(origin, records)

    def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> Mapping[str, object]:
        origin = domain.rstrip(".") + "."
        kept = [line for line in self._zone_lines(domain) if self._is_managed(line)]
        added = [
            self._record_to_joker_line(record, origin)
            for record in records_from_zone_text(zone_text, origin)
            if record.record_type.upper() not in _MANAGED_TYPES
        ]
        merged = kept + added
        self._call("dns-zone-put", {"domain": domain.rstrip("."), "zone": "\n".join(merged)})
        return {"records": len(merged), "added": len(added)}

    def delete_all_records(self, domain: str) -> Mapping[str, object]:
        lines = self._zone_lines(domain)
        kept = [line for line in lines if self._is_managed(line)]
        self._call("dns-zone-put", {"domain": domain.rstrip("."), "zone": "\n".join(kept)})
        return {"deleted": len(lines) - len(kept), "remaining": len(kept)}

    def read_nameservers(self, domain: str) -> tuple[str, ...]:
        name = domain.rstrip(".")
        nameservers: list[str] = []
        for line in self._zone_lines(domain):
            parts = _split_zone_line(line)
            if len(parts) >= 4 and parts[1].upper() == "NS" and parts[0] in {"@", name, name + "."}:
                nameservers.append(parts[3].rstrip("."))
        return tuple(dict.fromkeys(nameserver for nameserver in nameservers if nameserver))

    def assign_nameservers(self, domain: str, nameservers: Sequence[str]) -> Mapping[str, object]:
        cleaned = [nameserver.strip().rstrip(".") for nameserver in nameservers if nameserver.strip()]
        if not cleaned:
            raise ProviderAPIError("assign_nameservers requires at least one nameserver")
        self._call("domain-modify", {"domain": domain.rstrip("."), "ns-list": ":".join(cleaned)})
        return {"domain": domain.rstrip("."), "nameservers": cleaned}

    # -- internals --------------------------------------------------------

    def _zone_lines(self, domain: str) -> list[str]:
        body = self._call("dns-zone-get", {"domain": domain.rstrip(".")})
        return [line.strip() for line in body.splitlines() if line.strip()]

    @staticmethod
    def _is_managed(line: str) -> bool:
        parts = line.split()
        return len(parts) >= 2 and parts[1].upper() in _MANAGED_TYPES

    @staticmethod
    def _joker_line_to_record(line: str, domain: str) -> dict[str, object]:
        parts = _split_zone_line(line)
        label = parts[0] if parts else "@"
        rtype = parts[1].upper() if len(parts) > 1 else ""
        prio_text = parts[2] if len(parts) > 2 else "0"
        target = parts[3] if len(parts) > 3 else ""
        ttl_text = parts[4] if len(parts) > 4 else "3600"
        prio = int(prio_text) if prio_text.isdigit() else 0
        content = f"{prio} {target}" if rtype in {"MX", "SRV"} and prio_text.isdigit() else target
        bare_domain = domain.rstrip(".")
        name = bare_domain if label in {"@", bare_domain, bare_domain + "."} else f"{label}.{bare_domain}"
        try:
            ttl = int(ttl_text)
        except ValueError:
            ttl = 3600
        return {"name": name, "type": rtype, "content": content, "ttl": ttl, "prio": prio}

    @staticmethod
    def _record_to_joker_line(record: NormalizedRecord, origin: str) -> str:
        rtype = record.record_type.upper()
        bare_origin = origin.rstrip(".")
        owner = record.owner.rstrip(".")
        if owner in {bare_origin, ""}:
            label = "@"
        elif owner.endswith("." + bare_origin):
            label = owner[: -len(bare_origin) - 1]
        else:
            label = owner
        prio = 0
        target = record.value
        if rtype in {"MX", "SRV"}:
            head, _, rest = record.value.partition(" ")
            if head.isdigit():
                prio = int(head)
                target = rest.strip()
        return f"{label} {rtype} {prio} {target} {int(record.ttl)}"

    def _login(self) -> str:
        if self._auth_sid:
            return self._auth_sid
        response = self._client.post(f"{self._api_base}/login", data={"api-key": self._api_key})
        headers, _ = _parse_dmapi_response(response, action="login")
        sid = headers.get("auth-sid")
        if not sid:
            raise ProviderAPIError("Joker login did not return an Auth-Sid")
        self._auth_sid = sid
        return sid

    def _call(self, action: str, params: Mapping[str, str]) -> str:
        response = self._client.post(f"{self._api_base}/{action}", data={"auth-sid": self._login(), **params})
        _, body = _parse_dmapi_response(response, action=action)
        return body


def _split_zone_line(line: str) -> list[str]:
    match = _ZONE_LINE.match(line.strip())
    if not match:
        return line.split()
    label, rtype, prio, target, rest = match.groups()
    return [label, rtype, prio, target, *rest.split()]


def _parse_dmapi_response(response: httpx.Response, *, action: str) -> tuple[dict[str, str], str]:
    if response.status_code >= 400:
        raise ProviderAPIError(f"Joker DMAPI {action} HTTP error {response.status_code}: {response.text[:200]}")
    head, _, body = response.text.partition("\n\n")
    headers: dict[str, str] = {}
    for line in head.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    status_code = headers.get("status-code")
    if status_code not in (None, "0"):
        detail = headers.get("status-text") or headers.get("error") or status_code
        raise ProviderAPIError(f"Joker DMAPI {action} failed (status {status_code}): {detail}")
    return headers, body.strip("\n")
