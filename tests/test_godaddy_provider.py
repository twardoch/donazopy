# this_file: tests/test_godaddy_provider.py

import json as jsonlib
from collections.abc import Callable

import httpx
import pytest

from donazopy.providers.base import ProviderAPIError
from donazopy.providers.godaddy import GoDaddyProvider
from donazopy.zonefile import records_from_zone_text

CREDS = {"GODADDY_API_KEY": "key", "GODADDY_API_SECRET": "secret"}


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def records_payload() -> list[dict[str, object]]:
    return [
        {"type": "SOA", "name": "@", "data": "ns01.domaincontrol.com.", "ttl": 3600},
        {"type": "NS", "name": "@", "data": "ns01.domaincontrol.com", "ttl": 3600},
        {"type": "NS", "name": "@", "data": "ns02.domaincontrol.com", "ttl": 3600},
        {"type": "A", "name": "@", "data": "203.0.113.4", "ttl": 600},
        {"type": "A", "name": "www", "data": "203.0.113.4", "ttl": 600},
        {"type": "MX", "name": "@", "data": "mail.example.com", "ttl": 3600, "priority": 10},
        {"type": "TXT", "name": "@", "data": "v=spf1 -all", "ttl": 3600},
    ]


def base_handler(
    extra: Callable[[httpx.Request], httpx.Response] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "sso-key key:secret"
        path = request.url.path
        if path == "/v1/domains" and request.method == "GET":
            return httpx.Response(200, json=[{"domain": "example.com", "status": "ACTIVE"}, {"domain": "example.net"}])
        if path == "/v1/domains/example.com/records" and request.method == "GET":
            return httpx.Response(200, json=records_payload())
        if path == "/v1/domains/example.com" and request.method == "GET":
            return httpx.Response(
                200, json={"domain": "example.com", "nameServers": ["ns01.domaincontrol.com", "ns02.domaincontrol.com"]}
            )
        if extra is not None:
            return extra(request)
        return httpx.Response(404, json={"code": "NOT_FOUND", "message": "not found"})

    return handler


def provider(handler: Callable[[httpx.Request], httpx.Response]) -> GoDaddyProvider:
    return GoDaddyProvider(CREDS, client=make_client(handler))


def test_init_when_missing_credentials_then_raises() -> None:
    with pytest.raises(ProviderAPIError, match="GODADDY_API_SECRET"):
        GoDaddyProvider({"GODADDY_API_KEY": "key"}, client=make_client(lambda request: httpx.Response(200, json=[])))


def test_list_zones_when_called_then_returns_domains() -> None:
    assert provider(base_handler()).list_zones() == ["example.com", "example.net"]


def test_list_records_when_called_then_returns_records() -> None:
    types = sorted({str(record["type"]) for record in provider(base_handler()).list_records("example.com")})
    assert types == ["A", "MX", "NS", "SOA", "TXT"]


def test_export_zone_when_called_then_returns_parseable_bind_text() -> None:
    text = provider(base_handler()).export_zone("example.com")
    triples = {
        (record.owner, record.record_type, record.value) for record in records_from_zone_text(text, "example.com.")
    }

    assert ("example.com.", "A", "203.0.113.4") in triples
    assert ("www.example.com.", "A", "203.0.113.4") in triples
    assert ("example.com.", "MX", "10 mail.example.com.") in triples
    assert ("example.com.", "TXT", '"v=spf1 -all"') in triples
    assert sorted(value for _, rtype, value in triples if rtype == "NS") == [
        "ns01.domaincontrol.com.",
        "ns02.domaincontrol.com.",
    ]


def test_read_nameservers_when_called_then_returns_registrar_delegation() -> None:
    assert provider(base_handler()).read_nameservers("example.com") == (
        "ns01.domaincontrol.com",
        "ns02.domaincontrol.com",
    )


def test_import_zone_when_called_then_patches_records_without_soa() -> None:
    captured: dict[str, object] = {}

    def extra(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/domains/example.com/records" and request.method == "PATCH":
            captured["body"] = jsonlib.loads(request.content)
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"code": "NOT_FOUND", "message": "not found"})

    zone_text = (
        "$ORIGIN example.com.\n$TTL 3600\n"
        "example.com. 3600 IN SOA a.invalid. hostmaster.example.com. 1 7200 3600 1209600 3600\n"
        "example.com. 3600 IN NS ns01.domaincontrol.com.\n"
        "shop 600 IN A 198.51.100.20\n"
        "example.com. 3600 IN MX 5 mail.example.com.\n"
        'example.com. 3600 IN TXT "hello world"\n'
    )

    result = provider(base_handler(extra)).import_zone("example.com", zone_text)

    sent = captured["body"]
    assert isinstance(sent, list)
    assert all(record["type"] != "SOA" for record in sent)
    assert {"type": "A", "name": "shop", "ttl": 600, "data": "198.51.100.20"} in sent
    mx = next(record for record in sent if record["type"] == "MX")
    assert mx == {"type": "MX", "name": "@", "ttl": 3600, "priority": 5, "data": "mail.example.com."}
    txt = next(record for record in sent if record["type"] == "TXT")
    assert txt == {"type": "TXT", "name": "@", "ttl": 3600, "data": "hello world"}
    assert result == {"added": len(sent)}


def test_delete_all_records_when_called_then_deletes_each_type_name_group() -> None:
    deleted: list[str] = []

    def extra(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE" and request.url.path.startswith("/v1/domains/example.com/records/"):
            deleted.append(request.url.path.removeprefix("/v1/domains/example.com/records/"))
            return httpx.Response(204)
        return httpx.Response(404, json={"code": "NOT_FOUND", "message": "not found"})

    result = provider(base_handler(extra)).delete_all_records("example.com")

    # SOA and apex NS are preserved; A@, Awww, MX@, TXT@ are deleted.
    assert sorted(deleted) == ["A/@", "A/www", "MX/@", "TXT/@"]
    assert result == {"deleted": 4, "failed": 0}


def test_assign_nameservers_when_called_then_puts_domain_nameservers() -> None:
    captured: dict[str, object] = {}

    def extra(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/domains/example.com" and request.method == "PUT":
            captured["body"] = jsonlib.loads(request.content)
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"code": "NOT_FOUND", "message": "not found"})

    result = provider(base_handler(extra)).assign_nameservers("example.com", ["ns1.example.net.", "ns2.example.net"])

    assert captured["body"] == {"nameServers": ["ns1.example.net", "ns2.example.net"]}
    assert result == {"domain": "example.com", "nameservers": ["ns1.example.net", "ns2.example.net"]}


def test_assign_nameservers_when_empty_then_raises() -> None:
    with pytest.raises(ProviderAPIError, match="at least one nameserver"):
        provider(base_handler()).assign_nameservers("example.com", [""])


def test_api_error_when_godaddy_returns_error_then_raises_with_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"code": "ACCESS_DENIED", "message": "Authenticated user is not allowed access"}
        )

    with pytest.raises(ProviderAPIError, match="not allowed access"):
        provider(handler).list_zones()
