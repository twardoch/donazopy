# this_file: tests/test_joker_provider.py

from collections.abc import Callable
from urllib.parse import parse_qs

import httpx
import pytest

from donazopy.providers.base import ProviderAPIError
from donazopy.providers.joker import JokerProvider
from donazopy.zonefile import records_from_zone_text

CREDS = {"JOKER_API_KEY": "key-123"}
API_BASE = "https://dmapi.test/request"

OK_HEADERS = "Version: 1.2.0\nStatus-Code: 0\nStatus-Text: OK\n\n"
LOGIN_RESPONSE = "Version: 1.2.0\nStatus-Code: 0\nStatus-Text: OK\nAuth-Sid: SID-XYZ\n\ncom\nnet\n"
ZONE_TEXT = (
    "@ A 0 192.0.2.1 86400 0 0\n"
    "www CNAME 0 example.com. 86400 0 0\n"
    "@ MX 10 mail.example.com. 86400 0 0\n"
    '@ TXT 0 "v=spf1 -all" 86400 0 0\n'
    "@ NS 0 a.ns.joker.com. 86400 0 0\n"
    "@ NS 0 b.ns.joker.com. 86400 0 0\n"
)


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def form(request: httpx.Request) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(request.content.decode(), keep_blank_values=True).items()}


def provider(handler: Callable[[httpx.Request], httpx.Response]) -> JokerProvider:
    return JokerProvider(CREDS, client=make_client(handler), api_base=API_BASE)


def base_handler(
    extra: Callable[[httpx.Request], httpx.Response] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/request/login":
            assert form(request)["api-key"] == "key-123"
            return httpx.Response(200, text=LOGIN_RESPONSE)
        body = form(request)
        if path != "/request/login":
            assert body["auth-sid"] == "SID-XYZ"
        if path == "/request/dns-zone-get":
            return httpx.Response(200, text=OK_HEADERS + ZONE_TEXT)
        if path == "/request/query-domain-list":
            return httpx.Response(
                200, text=OK_HEADERS + "example.com 2030-01-01 active\nexample.net 2029-06-01 active\n"
            )
        if extra is not None:
            return extra(request)
        return httpx.Response(200, text=OK_HEADERS)

    return handler


def test_init_when_missing_api_key_then_raises() -> None:
    with pytest.raises(ProviderAPIError, match="JOKER_API_KEY"):
        JokerProvider({}, client=make_client(lambda request: httpx.Response(200, text=OK_HEADERS)))


def test_list_zones_when_called_then_returns_domains() -> None:
    assert provider(base_handler()).list_zones() == ["example.com", "example.net"]


def test_login_failure_when_status_nonzero_then_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Version: 1\nStatus-Code: 2304\nStatus-Text: Authorization failed\n\n")

    with pytest.raises(ProviderAPIError, match="Authorization failed"):
        provider(handler).list_zones()


def test_export_zone_when_called_then_returns_parseable_bind_text() -> None:
    text = provider(base_handler()).export_zone("example.com")
    records = records_from_zone_text(text, "example.com.")
    triples = {(record.owner, record.record_type, record.value) for record in records}

    assert ("example.com.", "A", "192.0.2.1") in triples
    assert ("www.example.com.", "CNAME", "example.com.") in triples
    assert ("example.com.", "MX", "10 mail.example.com.") in triples
    assert ("example.com.", "TXT", '"v=spf1 -all"') in triples
    # Joker omits the SOA; build_bind_zone synthesizes one so the text parses.
    assert any(rtype == "SOA" for _, rtype, _ in triples)
    assert sorted(value for owner, rtype, value in triples if rtype == "NS") == [
        "a.ns.joker.com.",
        "b.ns.joker.com.",
    ]


def test_read_nameservers_when_called_then_returns_apex_ns() -> None:
    assert provider(base_handler()).read_nameservers("example.com") == ("a.ns.joker.com", "b.ns.joker.com")


def test_import_zone_when_called_then_puts_zone_without_soa() -> None:
    captured: dict[str, str] = {}

    def extra(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/request/dns-zone-put":
            captured.update(form(request))
            return httpx.Response(200, text=OK_HEADERS)
        return httpx.Response(404, text="Version: 1\nStatus-Code: 2306\nStatus-Text: not found\n\n")

    zone_text = (
        "$ORIGIN example.com.\n$TTL 3600\n"
        "example.com. 3600 IN SOA a.invalid. hostmaster.example.com. 1 7200 3600 1209600 3600\n"
        "example.com. 3600 IN NS a.ns.joker.com.\n"
        "blog 3600 IN A 198.51.100.5\n"
        "example.com. 3600 IN MX 20 alt.mail.example.com.\n"
    )

    result = provider(base_handler(extra)).import_zone("example.com", zone_text)

    sent_lines = captured["zone"].splitlines()
    assert all(" SOA " not in line for line in sent_lines)
    assert "blog A 0 198.51.100.5 3600" in sent_lines
    assert "@ MX 20 alt.mail.example.com. 3600" in sent_lines
    assert "@ NS 0 a.ns.joker.com. 3600" in sent_lines
    assert result == {"records": len(sent_lines), "added": len(sent_lines)}


def test_delete_all_records_when_called_then_puts_empty_zone() -> None:
    captured: dict[str, str] = {}

    def extra(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/request/dns-zone-put":
            captured.update(form(request))
            return httpx.Response(200, text=OK_HEADERS)
        return httpx.Response(404)

    result = provider(base_handler(extra)).delete_all_records("example.com")

    assert captured["zone"] == ""
    assert result == {"deleted": 6, "remaining": 0}


def test_assign_nameservers_when_called_then_calls_domain_modify() -> None:
    captured: dict[str, str] = {}

    def extra(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/request/domain-modify":
            captured.update(form(request))
            return httpx.Response(200, text=OK_HEADERS)
        return httpx.Response(404)

    result = provider(base_handler(extra)).assign_nameservers("example.com", ["ns1.example.net.", "ns2.example.net"])

    assert captured["domain"] == "example.com"
    assert captured["ns-list"] == "ns1.example.net:ns2.example.net"
    assert result == {"domain": "example.com", "nameservers": ["ns1.example.net", "ns2.example.net"]}


def test_assign_nameservers_when_empty_then_raises() -> None:
    with pytest.raises(ProviderAPIError, match="at least one nameserver"):
        provider(base_handler()).assign_nameservers("example.com", ["  "])
