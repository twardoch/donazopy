# this_file: tests/test_cli.py

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from donazopy.cli import Donazopy
from donazopy.providers.base import ProviderAPIError
from donazopy.target import TargetError

ZONE_TEXT = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ns1.example.com. hostmaster.example.com. 2026051201 7200 3600 1209600 3600
@ IN NS ns1.example.com.
ns1 IN A 192.0.2.10
www IN A 192.0.2.20
txt IN TXT "hello world"
"""


class FakeDNSProvider:
    """A minimal in-memory DNS provider for offline CLI tests."""

    def __init__(self, *, zone_text: str = ZONE_TEXT) -> None:
        self.zone_text = zone_text
        self.imported: list[tuple[str, str]] = []
        self.deleted: list[str] = []
        self.records: list[Mapping[str, object]] = [
            {"id": "1", "type": "A", "name": "www.example.com", "content": "192.0.2.20"},
            {"id": "2", "type": "TXT", "name": "txt.example.com", "content": "hello world"},
        ]

    def export_zone(self, domain: str) -> str:
        return self.zone_text

    def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> Mapping[str, object]:
        self.imported.append((domain, zone_text))
        return {"recs_added": zone_text.count("\n")}

    def list_records(self, domain: str) -> list[Mapping[str, object]]:
        return list(self.records)

    def delete_all_records(self, domain: str) -> Mapping[str, object]:
        self.deleted.append(domain)
        return {"deleted": len(self.records), "failed": 0}

    def list_zones(self) -> list[str]:
        return ["example.com"]


class FakeRegistrarProvider:
    def __init__(self) -> None:
        self.assigned: list[tuple[str, list[str]]] = []

    def read_nameservers(self, domain: str) -> tuple[str, ...]:
        return ("ns1.example.com", "ns2.example.com")

    def assign_nameservers(self, domain: str, nameservers: Sequence[str]) -> Mapping[str, object]:
        self.assigned.append((domain, list(nameservers)))
        return {"assigned": list(nameservers)}


@pytest.fixture
def dns_provider() -> FakeDNSProvider:
    return FakeDNSProvider()


@pytest.fixture
def registrar_provider() -> FakeRegistrarProvider:
    return FakeRegistrarProvider()


@pytest.fixture
def cli(
    dns_provider: FakeDNSProvider, registrar_provider: FakeRegistrarProvider, monkeypatch: pytest.MonkeyPatch
) -> Donazopy:
    # Make credential loading offline-friendly.
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    return Donazopy(
        dns_factory=lambda key, credentials, **_: dns_provider,
        registrar_factory=lambda key, credentials, **_: registrar_provider,
    )


def test_version_when_called_then_returns_string() -> None:
    assert isinstance(Donazopy().version(), str)


def test_providers_when_called_then_lists_operational_keys() -> None:
    assert Donazopy().providers() == ["cloudflare", "godaddy", "ionos", "joker"]


def test_status_when_no_target_then_returns_entry_per_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    result = Donazopy().status()

    assert set(result) == {"cloudflare", "godaddy", "ionos", "joker"}
    assert result["cloudflare"]["metadata"]["key"] == "cloudflare"
    assert "credential_status" in result["cloudflare"]


def test_status_when_provider_key_then_returns_single_entry(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("CLOUDFLARE_API_TOKEN=token\n", encoding="utf-8")

    result = Donazopy().status("cloudflare", dotenv_path=str(dotenv_path))

    assert result["metadata"]["key"] == "cloudflare"
    assert result["credential_status"]["complete"] is True


def test_status_when_full_target_then_resolves_provider(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("CLOUDFLARE_API_TOKEN=token\n", encoding="utf-8")

    result = Donazopy().status("cloudflare/example.com:A", dotenv_path=str(dotenv_path))

    assert result["metadata"]["key"] == "cloudflare"


def test_records_when_target_filters_type_then_returns_matching_records(cli: Donazopy) -> None:
    records = cli.records("cloudflare/example.com:TXT")

    assert [record["id"] for record in records] == ["2"]


def test_export_when_skip_ns_and_skip_types_then_filters_zone(cli: Donazopy) -> None:
    result = cli.export("cloudflare/example.com", skip_ns=True, skip_types="TXT")

    assert "NS" not in result
    assert "TXT" not in result
    assert "192.0.2.20" in result
    assert "SOA" in result  # apex SOA is preserved


def test_export_when_output_requested_then_writes_file(cli: Donazopy, tmp_path: Path) -> None:
    output_path = tmp_path / "out.zone"

    result = cli.export("cloudflare/example.com", output=str(output_path))

    assert output_path.read_text(encoding="utf-8") == result


def test_import_zone_when_path_given_then_calls_provider(
    cli: Donazopy, dns_provider: FakeDNSProvider, tmp_path: Path
) -> None:
    zone_path = tmp_path / "example.com.zone"
    zone_path.write_text(ZONE_TEXT, encoding="utf-8")

    cli.import_zone("cloudflare/example.com", str(zone_path))

    assert dns_provider.imported and dns_provider.imported[0][0] == "example.com"


def test_copy_when_replace_then_deletes_then_imports(cli: Donazopy, dns_provider: FakeDNSProvider) -> None:
    result = cli.copy("cloudflare/example.com", "cloudflare/*", replace=True, skip_ns=True)

    assert dns_provider.deleted == ["example.com"]
    assert result["dest"]["domain"] == "example.com"
    assert result["replaced"] == {"deleted": 2, "failed": 0}
    assert result["exported_records"] > 0
    assert dns_provider.imported


def test_nameservers_when_no_args_then_reads(cli: Donazopy) -> None:
    assert cli.nameservers("cloudflare/example.com") == ["ns1.example.com", "ns2.example.com"]


def test_nameservers_when_values_given_then_assigns(cli: Donazopy, registrar_provider: FakeRegistrarProvider) -> None:
    result = cli.nameservers("cloudflare/example.com", "a.iana-servers.net", "b.iana-servers.net")

    assert result == {"assigned": ["a.iana-servers.net", "b.iana-servers.net"]}
    assert registrar_provider.assigned == [("example.com", ["a.iana-servers.net", "b.iana-servers.net"])]


def test_diff_when_two_files_then_returns_summary(tmp_path: Path) -> None:
    before = tmp_path / "before.zone"
    after = tmp_path / "after.zone"
    before.write_text(ZONE_TEXT, encoding="utf-8")
    after.write_text(ZONE_TEXT.replace("192.0.2.20", "192.0.2.30"), encoding="utf-8")

    result = Donazopy().diff(str(before), str(after), origin="example.com.")

    assert result["summary"] == "creates=0 updates=1 deletes=0 unchanged=4"


def test_diff_when_target_versus_file_then_returns_summary(cli: Donazopy, tmp_path: Path) -> None:
    file_path = tmp_path / "snapshot.zone"
    file_path.write_text(ZONE_TEXT, encoding="utf-8")

    result = cli.diff("cloudflare/example.com", str(file_path), origin="example.com.")

    assert result["summary"].startswith("creates=0 updates=0 deletes=0")


def test_validate_when_valid_zone_then_reports_origin(tmp_path: Path) -> None:
    zone_path = tmp_path / "example.com.zone"
    zone_path.write_text(ZONE_TEXT, encoding="utf-8")

    result = Donazopy().validate(str(zone_path), origin="example.com.")

    assert result.startswith("valid zone example.com.")


def test_normalize_when_output_requested_then_writes_file(tmp_path: Path) -> None:
    zone_path = tmp_path / "example.com.zone"
    output_path = tmp_path / "normalized.zone"
    zone_path.write_text(ZONE_TEXT, encoding="utf-8")

    result = Donazopy().normalize(str(zone_path), origin="example.com.", output=str(output_path))

    assert "www.example.com. 3600 IN A 192.0.2.20" in result
    assert output_path.read_text(encoding="utf-8") == result


def test_records_when_no_provider_and_ambiguous_target_then_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch the operational provider list to be empty to force ambiguity.
    import donazopy.cli as cli_module

    monkeypatch.setattr(cli_module, "_operational_keys", lambda: ())
    with pytest.raises(TargetError, match="prefix the target with 'provider/'"):
        Donazopy().records("example.com")


def test_export_when_assign_unsupported_via_cloudflare_then_documented() -> None:
    # Sanity check that the Cloudflare adapter raises a clear error (uses real provider class).
    import httpx

    from donazopy.providers.cloudflare import CloudflareProvider

    provider = CloudflareProvider(
        {"CLOUDFLARE_API_TOKEN": "token"},
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(404))),
    )
    with pytest.raises(ProviderAPIError, match="not supported"):
        provider.assign_nameservers("example.com", ["a.ns", "b.ns"])
