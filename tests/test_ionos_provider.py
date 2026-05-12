# this_file: tests/test_ionos_provider.py

from collections.abc import Callable

import httpx
import pytest

from donazopy.providers.base import ProviderAPIError
from donazopy.providers.ionos import IonosProvider
from donazopy.zonefile import records_from_zone_text

CREDS = {"IONOS_API_PUBLIC": "pub", "IONOS_API_SECRET": "sec"}


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def zones_list() -> list[dict[str, object]]:
    return [{"id": "zone-1", "name": "example.com", "type": "NATIVE"}]


def zone_detail() -> dict[str, object]:
    return {
        "id": "zone-1",
        "name": "example.com",
        "type": "NATIVE",
        "records": [
            {
                "id": "r-soa",
                "name": "example.com",
                "type": "SOA",
                "content": "ns1.ui-dns.de hostmaster.example.com 2024010101 28800 7200 604800 3600",
                "ttl": 3600,
                "disabled": False,
            },
            {"id": "r-ns1", "name": "example.com", "type": "NS", "content": "ns1.ui-dns.de", "ttl": 3600},
            {"id": "r-ns2", "name": "example.com", "type": "NS", "content": "ns2.ui-dns.de", "ttl": 3600},
            {"id": "r-a", "name": "www.example.com", "type": "A", "content": "192.0.2.10", "ttl": 3600},
            {"id": "r-mx", "name": "example.com", "type": "MX", "content": "mail.example.com", "ttl": 3600, "prio": 10},
            {"id": "r-txt", "name": "example.com", "type": "TXT", "content": "v=spf1 -all", "ttl": 3600},
            {
                "id": "r-off",
                "name": "old.example.com",
                "type": "A",
                "content": "203.0.113.9",
                "ttl": 60,
                "disabled": True,
            },
        ],
    }


def detail_handler(
    extra: Callable[[httpx.Request], httpx.Response] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "pub.sec"
        if request.url.path == "/dns/v1/zones" and request.method == "GET":
            return httpx.Response(200, json=zones_list())
        if request.url.path == "/dns/v1/zones/zone-1" and request.method == "GET":
            return httpx.Response(200, json=zone_detail())
        if extra is not None:
            return extra(request)
        return httpx.Response(404, json=[{"message": "not found"}])

    return handler


def test_init_when_missing_credentials_then_raises() -> None:
    with pytest.raises(ProviderAPIError, match="IONOS_API_SECRET"):
        IonosProvider({"IONOS_API_PUBLIC": "pub"}, client=make_client(lambda request: httpx.Response(200, json=[])))


def test_list_zones_when_called_then_returns_zone_names() -> None:
    provider = IonosProvider(CREDS, client=make_client(detail_handler()))
    assert provider.list_zones() == ["example.com"]


def test_list_records_when_zone_exists_then_returns_records() -> None:
    provider = IonosProvider(CREDS, client=make_client(detail_handler()))
    types = sorted({str(record["type"]) for record in provider.list_records("example.com")})
    assert types == ["A", "MX", "NS", "SOA", "TXT"]


def test_export_zone_when_called_then_returns_parseable_bind_text() -> None:
    provider = IonosProvider(CREDS, client=make_client(detail_handler()))

    text = provider.export_zone("example.com.")
    records = records_from_zone_text(text, "example.com.")

    by_type = {(record.owner, record.record_type): record.value for record in records}
    assert by_type[("www.example.com.", "A")] == "192.0.2.10"
    assert by_type[("example.com.", "MX")] == "10 mail.example.com."
    assert by_type[("example.com.", "TXT")] == '"v=spf1 -all"'
    # disabled records are not exported
    assert ("old.example.com.", "A") not in by_type


def test_read_nameservers_when_zone_exists_then_returns_apex_ns() -> None:
    provider = IonosProvider(CREDS, client=make_client(detail_handler()))
    assert provider.read_nameservers("example.com") == ("ns1.ui-dns.de", "ns2.ui-dns.de")


def test_import_zone_when_called_then_posts_records_without_soa() -> None:
    captured: dict[str, object] = {}

    def extra(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/dns/v1/zones/zone-1/records" and request.method == "POST":
            import json as _json

            captured["body"] = _json.loads(request.content)
            return httpx.Response(201, json=[])
        return httpx.Response(404, json=[{"message": "not found"}])

    provider = IonosProvider(CREDS, client=make_client(detail_handler(extra)))
    zone_text = "$ORIGIN example.com.\n$TTL 3600\nexample.com. 3600 IN SOA a.invalid. hostmaster.example.com. 1 7200 3600 1209600 3600\nexample.com. 3600 IN NS ns1.ui-dns.de.\nwww 3600 IN A 198.51.100.7\nexample.com. 3600 IN MX 5 mail.example.com.\n"

    result = provider.import_zone("example.com", zone_text)

    sent = captured["body"]
    assert isinstance(sent, list)
    assert all(record["type"] != "SOA" for record in sent)
    a_record = next(record for record in sent if record["type"] == "A")
    assert a_record == {
        "name": "www.example.com",
        "type": "A",
        "content": "198.51.100.7",
        "ttl": 3600,
        "prio": 0,
        "disabled": False,
    }
    mx_record = next(record for record in sent if record["type"] == "MX")
    assert mx_record["prio"] == 5
    assert mx_record["content"] == "mail.example.com."
    assert result == {"created": len(sent)}


def test_delete_all_records_when_called_then_deletes_non_soa_records() -> None:
    deleted: list[str] = []

    def extra(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE" and request.url.path.startswith("/dns/v1/zones/zone-1/records/"):
            deleted.append(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(204)
        return httpx.Response(404, json=[{"message": "not found"}])

    provider = IonosProvider(CREDS, client=make_client(detail_handler(extra)))

    result = provider.delete_all_records("example.com")

    assert "r-soa" not in deleted
    assert set(deleted) == {"r-ns1", "r-ns2", "r-a", "r-mx", "r-txt", "r-off"}
    assert result == {"deleted": 6, "failed": 0}


def test_assign_nameservers_when_called_then_raises_unsupported() -> None:
    provider = IonosProvider(CREDS, client=make_client(detail_handler()))
    with pytest.raises(ProviderAPIError, match="not supported"):
        provider.assign_nameservers("example.com", ["ns1.example.net", "ns2.example.net"])


def test_zone_not_found_when_unknown_domain_then_raises() -> None:
    provider = IonosProvider(CREDS, client=make_client(detail_handler()))
    with pytest.raises(ProviderAPIError, match="zone not found"):
        provider.export_zone("missing.example")


def test_api_error_when_zones_endpoint_fails_then_raises_with_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json=[{"message": "forbidden"}])

    provider = IonosProvider(CREDS, client=make_client(handler))
    with pytest.raises(ProviderAPIError, match="forbidden"):
        provider.list_zones()
