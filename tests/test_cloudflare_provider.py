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

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    records = provider.list_records("example.com")

    assert [record["id"] for record in records] == ["record-1", "record-2"]


def test_export_zone_when_cloudflare_returns_bind_text_then_returns_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones":
            return httpx.Response(200, json=zone_payload())
        if request.url.path == "/client/v4/zones/zone-id/dns_records/export":
            return httpx.Response(200, text="$ORIGIN example.com.\nwww 3600 IN A 192.0.2.1\n")
        return httpx.Response(404)

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    assert "www 3600 IN A 192.0.2.1" in provider.export_zone("example.com.")


def test_import_zone_when_cloudflare_accepts_file_then_returns_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones":
            return httpx.Response(200, json=zone_payload())
        if request.url.path == "/client/v4/zones/zone-id/dns_records/import":
            assert request.method == "POST"
            return httpx.Response(200, json={"success": True, "result": {"recs_added": 2, "total_records_parsed": 2}})
        return httpx.Response(404)

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    result = provider.import_zone("example.com", "$ORIGIN example.com.\n", proxied=False)

    assert result == {"recs_added": 2, "total_records_parsed": 2}


def test_read_nameservers_when_zone_exists_then_returns_assigned_nameservers() -> None:
    provider = CloudflareProvider(
        {"CLOUDFLARE_DNS_TOKEN": "token"},
        client=make_cloudflare_client(lambda request: httpx.Response(200, json=zone_payload())),
    )

    assert provider.read_nameservers("example.com") == ("alice.ns.cloudflare.com", "bob.ns.cloudflare.com")


def test_cloudflare_error_when_api_returns_error_then_raises_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"success": False, "errors": [{"message": "permission denied"}]})

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    with pytest.raises(ProviderAPIError, match="permission denied"):
        provider.export_zone("example.com")


def test_delete_all_records_when_records_exist_then_deletes_each_and_counts() -> None:
    deleted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones":
            return httpx.Response(200, json=zone_payload())
        if request.url.path == "/client/v4/zones/zone-id/dns_records" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": [
                        {"id": "record-1", "type": "A", "name": "www.example.com", "content": "192.0.2.1"},
                        {"id": "record-2", "type": "TXT", "name": "example.com", "content": "hello"},
                        {"id": "record-3", "type": "NS", "name": "example.com", "content": "ns.cloudflare.com"},
                    ],
                    "result_info": {"total_pages": 1},
                },
            )
        if request.url.path.startswith("/client/v4/zones/zone-id/dns_records/") and request.method == "DELETE":
            record_id = request.url.path.rsplit("/", 1)[-1]
            if record_id == "record-3":
                return httpx.Response(400, json={"success": False, "errors": [{"message": "cannot delete NS"}]})
            deleted.append(record_id)
            return httpx.Response(200, json={"success": True, "result": {"id": record_id}})
        return httpx.Response(404, json={"success": False, "errors": [{"message": "not found"}]})

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    result = provider.delete_all_records("example.com")

    assert sorted(deleted) == ["record-1", "record-2"]
    assert result == {"deleted": 2, "failed": 1}


def test_assign_nameservers_when_called_then_raises_unsupported() -> None:
    provider = CloudflareProvider(
        {"CLOUDFLARE_DNS_TOKEN": "token"},
        client=make_cloudflare_client(lambda request: httpx.Response(404)),
    )

    with pytest.raises(ProviderAPIError, match="not supported"):
        provider.assign_nameservers("example.com", ["a.iana-servers.net", "b.iana-servers.net"])


def test_list_zones_when_multiple_pages_then_returns_all_names() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones":
            page = request.url.params.get("page")
            if page == "1":
                return httpx.Response(
                    200,
                    json={
                        "success": True,
                        "result": [{"id": "a", "name": "alpha.example"}],
                        "result_info": {"total_pages": 2},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": [{"id": "b", "name": "beta.example"}],
                    "result_info": {"total_pages": 2},
                },
            )
        return httpx.Response(404)

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    assert provider.list_zones() == ["alpha.example", "beta.example"]


def test_create_zone_when_account_id_env_set_then_posts_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_DNS_ACCOUNT", "acct-123")
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones" and request.method == "POST":
            import json as _json

            captured["body"] = _json.loads(request.content)
            return httpx.Response(200, json={"success": True, "result": {"id": "new-zone", "name": "new.example"}})
        return httpx.Response(404, json={"success": False, "errors": [{"message": "not found"}]})

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    result = provider.create_zone("new.example.")

    assert captured["body"] == {"name": "new.example", "account": {"id": "acct-123"}}
    assert result == {"id": "new-zone", "name": "new.example"}


def test_create_zone_when_no_account_id_then_auto_detects_single_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_DNS_ACCOUNT", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/accounts" and request.method == "GET":
            return httpx.Response(200, json={"success": True, "result": [{"id": "only-acct", "name": "Solo"}]})
        if request.url.path == "/client/v4/zones" and request.method == "POST":
            return httpx.Response(200, json={"success": True, "result": {"id": "z", "name": "new.example"}})
        return httpx.Response(404, json={"success": False, "errors": [{"message": "not found"}]})

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    assert provider.create_zone("new.example") == {"id": "z", "name": "new.example"}


def test_create_zone_when_zone_exists_then_returns_existing_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_DNS_ACCOUNT", "acct-123")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones" and request.method == "POST":
            return httpx.Response(
                400, json={"success": False, "errors": [{"code": 1061, "message": "the zone already exists"}]}
            )
        if request.url.path == "/client/v4/zones" and request.method == "GET":
            return httpx.Response(200, json=zone_payload())
        return httpx.Response(404, json={"success": False, "errors": [{"message": "not found"}]})

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    result = provider.create_zone("example.com")

    assert result["id"] == "zone-id"
    assert result["name"] == "example.com"


def test_create_record_when_called_then_posts_single_record() -> None:
    import json as _json

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/client/v4/zones" and request.method == "GET":
            return httpx.Response(200, json=zone_payload())
        if request.url.path == "/client/v4/zones/zone-id/dns_records" and request.method == "POST":
            captured["body"] = _json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {"id": "new-record-id", "type": "TXT", "name": "auth.example.com"},
                },
            )
        return httpx.Response(404, json={"success": False, "errors": [{"message": "not found"}]})

    provider = CloudflareProvider({"CLOUDFLARE_DNS_TOKEN": "token"}, client=make_cloudflare_client(handler))

    result = provider.create_record(
        "example.com",
        {"type": "TXT", "name": "auth", "content": "v=DMARC1;", "ttl": 3600},
    )

    assert result["id"] == "new-record-id"
    assert captured["body"] == {
        "type": "TXT",
        "name": "auth",
        "content": "v=DMARC1;",
        "ttl": 3600,
    }
