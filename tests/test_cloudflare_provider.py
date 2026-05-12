# this_file: tests/test_cloudflare_provider.py

from collections.abc import Callable

import httpx
import pytest

from donazopy.providers.base import ProviderAPIError
from donazopy.providers.cloudflare import CloudflareProvider


def make_cloudflare_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def zone_payload() -> dict[str, object]:
    return {
        "success": True,
        "result": [
            {
                "id": "zone-id",
                "name": "example.com",
                "name_servers": ["alice.ns.cloudflare.com", "bob.ns.cloudflare.com"],
            }
        ],
    }


def test_list_records_when_zone_exists_then_reads_all_pages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones":
            assert request.headers["Authorization"] == "Bearer token"
            return httpx.Response(200, json=zone_payload())
        if request.url.path == "/client/v4/zones/zone-id/dns_records":
            page = request.url.params.get("page")
            if page == "1":
                return httpx.Response(
                    200,
                    json={
                        "success": True,
                        "result": [{"id": "record-1", "type": "A", "name": "www.example.com", "content": "192.0.2.1"}],
                        "result_info": {"total_pages": 2},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": [{"id": "record-2", "type": "TXT", "name": "example.com", "content": "hello"}],
                    "result_info": {"total_pages": 2},
                },
            )
        return httpx.Response(404, json={"success": False, "errors": [{"message": "not found"}]})

    provider = CloudflareProvider({"CLOUDFLARE_API_TOKEN": "token"}, client=make_cloudflare_client(handler))

    records = provider.list_records("example.com")

    assert [record["id"] for record in records] == ["record-1", "record-2"]


def test_export_zone_when_cloudflare_returns_bind_text_then_returns_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones":
            return httpx.Response(200, json=zone_payload())
        if request.url.path == "/client/v4/zones/zone-id/dns_records/export":
            return httpx.Response(200, text="$ORIGIN example.com.\nwww 3600 IN A 192.0.2.1\n")
        return httpx.Response(404)

    provider = CloudflareProvider({"CLOUDFLARE_API_TOKEN": "token"}, client=make_cloudflare_client(handler))

    assert "www 3600 IN A 192.0.2.1" in provider.export_zone("example.com.")


def test_import_zone_when_cloudflare_accepts_file_then_returns_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones":
            return httpx.Response(200, json=zone_payload())
        if request.url.path == "/client/v4/zones/zone-id/dns_records/import":
            assert request.method == "POST"
            return httpx.Response(200, json={"success": True, "result": {"recs_added": 2, "total_records_parsed": 2}})
        return httpx.Response(404)

    provider = CloudflareProvider({"CLOUDFLARE_API_TOKEN": "token"}, client=make_cloudflare_client(handler))

    result = provider.import_zone("example.com", "$ORIGIN example.com.\n", proxied=False)

    assert result == {"recs_added": 2, "total_records_parsed": 2}


def test_read_nameservers_when_zone_exists_then_returns_assigned_nameservers() -> None:
    provider = CloudflareProvider(
        {"CLOUDFLARE_API_TOKEN": "token"},
        client=make_cloudflare_client(lambda request: httpx.Response(200, json=zone_payload())),
    )

    assert provider.read_nameservers("example.com") == ("alice.ns.cloudflare.com", "bob.ns.cloudflare.com")


def test_cloudflare_error_when_api_returns_error_then_raises_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"success": False, "errors": [{"message": "permission denied"}]})

    provider = CloudflareProvider({"CLOUDFLARE_API_TOKEN": "token"}, client=make_cloudflare_client(handler))

    with pytest.raises(ProviderAPIError, match="permission denied"):
        provider.export_zone("example.com")
