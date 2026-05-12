# this_file: tests/test_cli.py

from pathlib import Path

import pytest

from donazopy.cli import Donazopy
from donazopy.zonefile import ZoneFileError, validate_zone_file

ZONE_TEXT = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ns1.example.com. hostmaster.example.com. 2026051201 7200 3600 1209600 3600
@ IN NS ns1.example.com.
ns1 IN A 192.0.2.10
www IN A 192.0.2.20
"""


def test_providers_when_called_then_lists_only_operational_provider_keys() -> None:
    providers = Donazopy().providers()

    assert providers == ["cloudflare"]


def test_provider_when_known_key_then_returns_serializable_metadata() -> None:
    provider = Donazopy().provider("cloudflare")

    assert provider["key"] == "cloudflare"
    assert "zone_read" in provider["capabilities"]
    assert "CLOUDFLARE_API_TOKEN" in provider["credentials"]


def test_validate_zone_file_when_valid_zone_then_reports_origin_and_nodes(tmp_path: Path) -> None:
    zone_path = tmp_path / "example.com.zone"
    zone_path.write_text(ZONE_TEXT, encoding="utf-8")

    result = validate_zone_file(zone_path, origin="example.com.")

    assert result.startswith("valid zone example.com.")
    assert "nodes" in result


def test_validate_zone_file_when_empty_then_raises_zone_error(tmp_path: Path) -> None:
    zone_path = tmp_path / "empty.zone"
    zone_path.write_text("", encoding="utf-8")

    with pytest.raises(ZoneFileError, match="zone text is empty"):
        validate_zone_file(zone_path, origin="example.com.")


def test_zone_normalize_when_output_requested_then_writes_file(tmp_path: Path) -> None:
    zone_path = tmp_path / "example.com.zone"
    output_path = tmp_path / "normalized.zone"
    zone_path.write_text(ZONE_TEXT, encoding="utf-8")

    result = Donazopy().zone_normalize(str(zone_path), origin="example.com.", output=str(output_path))

    assert "www.example.com. 3600 IN A 192.0.2.20" in result
    assert output_path.read_text(encoding="utf-8") == result


def test_zone_diff_when_called_then_returns_summary_and_changes(tmp_path: Path) -> None:
    before_path = tmp_path / "before.zone"
    after_path = tmp_path / "after.zone"
    before_path.write_text(ZONE_TEXT, encoding="utf-8")
    after_path.write_text(ZONE_TEXT.replace("192.0.2.20", "192.0.2.30"), encoding="utf-8")

    result = Donazopy().zone_diff(str(before_path), str(after_path), origin="example.com.")

    assert result["summary"] == "creates=0 updates=1 deletes=0 unchanged=3"
    assert result["changes"]


def test_provider_status_when_called_then_loads_dotenv_and_redacts_credentials(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("CLOUDFLARE_API_TOKEN=token\n", encoding="utf-8")

    status = Donazopy().provider_status("cloudflare", dotenv_path=str(dotenv_path))

    assert status["complete"] is True
    assert status["redacted"] == {"CLOUDFLARE_API_TOKEN": "***"}
