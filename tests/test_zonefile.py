# this_file: tests/test_zonefile.py

from pathlib import Path

import pytest

from donazopy.zonefile import (
    ZoneFileError,
    diff_zone_files,
    filter_records,
    filter_zone_text,
    normalize_zone_file,
    records_from_zone_file,
    records_from_zone_text,
    write_text_safely,
)

BEFORE_ZONE = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ns1.example.com. hostmaster.example.com. 2026051201 7200 3600 1209600 3600
@ IN NS ns1.example.com.
ns1 IN A 192.0.2.10
www IN A 192.0.2.20
old IN TXT "remove me"
"""

AFTER_ZONE = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ns1.example.com. hostmaster.example.com. 2026051201 7200 3600 1209600 3600
@ IN NS ns1.example.com.
ns1 IN A 192.0.2.10
www IN A 192.0.2.30
api IN A 192.0.2.40
"""


def write_zone(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_normalize_zone_file_when_valid_then_returns_stable_absolute_records(tmp_path: Path) -> None:
    zone_path = write_zone(tmp_path, "example.com.zone", BEFORE_ZONE)

    normalized = normalize_zone_file(zone_path, origin="example.com.")

    assert "example.com. 3600 IN NS ns1.example.com." in normalized
    assert "www.example.com. 3600 IN A 192.0.2.20" in normalized
    assert normalized.endswith("\n")


def test_records_from_zone_file_when_valid_then_preserves_record_metadata(tmp_path: Path) -> None:
    zone_path = write_zone(tmp_path, "example.com.zone", BEFORE_ZONE)

    records = records_from_zone_file(zone_path, origin="example.com.")

    www_record = next(record for record in records if record.owner == "www.example.com.")
    assert www_record.ttl == 3600
    assert www_record.record_class == "IN"
    assert www_record.record_type == "A"
    assert www_record.value == "192.0.2.20"


def test_diff_zone_files_when_records_change_then_groups_safe_plan(tmp_path: Path) -> None:
    before_path = write_zone(tmp_path, "before.zone", BEFORE_ZONE)
    after_path = write_zone(tmp_path, "after.zone", AFTER_ZONE)

    diff = diff_zone_files(before_path, after_path, origin="example.com.")

    assert diff.summary() == "creates=1 updates=1 deletes=1 unchanged=3"
    assert diff.creates[0].after is not None
    assert diff.creates[0].after.owner == "api.example.com."
    assert diff.updates[0].before is not None
    assert diff.updates[0].before.owner == "www.example.com."
    assert diff.deletes[0].before is not None
    assert diff.deletes[0].before.owner == "old.example.com."


def test_filter_zone_text_when_skip_ns_then_drops_ns_but_keeps_soa() -> None:
    result = filter_zone_text(BEFORE_ZONE, "example.com.", skip_ns=True)

    assert " NS " not in result
    assert " SOA " in result
    assert "www.example.com. 3600 IN A 192.0.2.20" in result


def test_filter_zone_text_when_skip_types_then_drops_those_types() -> None:
    result = filter_zone_text(BEFORE_ZONE, "example.com.", skip_types=["txt"])

    assert " TXT " not in result
    assert "ns1.example.com. 3600 IN A 192.0.2.10" in result


def test_filter_records_when_skip_ns_and_types_then_filters() -> None:
    records = records_from_zone_text(BEFORE_ZONE, "example.com.")

    filtered = filter_records(records, skip_ns=True, skip_types=["A"])
    types = {record.record_type for record in filtered}

    assert "NS" not in types
    assert "A" not in types
    assert "SOA" in types
    assert "TXT" in types


def test_records_from_zone_text_when_valid_then_returns_records() -> None:
    records = records_from_zone_text(BEFORE_ZONE, "example.com.")

    assert any(record.owner == "www.example.com." and record.record_type == "A" for record in records)


def test_records_from_zone_text_when_strict_parse_fails_then_lenient_fallback() -> None:
    """Regression: ionos.import_zone (and any caller) round-tripping
    Cloudflare exports through ``records_from_zone_text`` must not crash
    on out-of-origin SOA entries. The lenient fallback parses the rest."""
    text = """$ORIGIN example.com.
$TTL 3600
example.com. 3600 IN SOA ns1.example.com. hostmaster.example.com. 1 7200 3600 1209600 3600
example.com. 3600 IN NS ns1.example.com.
www.example.com. 3600 IN A 192.0.2.20
unexpected.other-zone.tld. 3600 IN SOA something. else. 1 2 3 4 5
"""

    records = records_from_zone_text(text, "example.com.")

    record_types = {r.record_type for r in records}
    assert "A" in record_types
    assert "NS" in record_types
    assert any(r.owner == "www.example.com." and r.value == "192.0.2.20" for r in records)


def test_filter_zone_text_when_strict_parse_fails_then_lenient_fallback() -> None:
    """Real-world: Cloudflare exports occasionally trip dnspython with a
    ``non-origin SOA`` ValueError. The filter must still drop NS records via
    a line-based fallback instead of crashing the caller."""
    text = """$ORIGIN example.com.
$TTL 3600
example.com. 3600 IN SOA ns1.example.com. hostmaster.example.com. 1 7200 3600 1209600 3600
example.com. 3600 IN NS ns1.example.com.
example.com. 3600 IN NS ns-foreign.somewhere-else.tld.
www.example.com. 3600 IN A 192.0.2.20
unexpected.other-zone.tld. 3600 IN SOA something. else. 1 2 3 4 5
"""

    result = filter_zone_text(text, "example.com.", skip_ns=True)

    assert " NS " not in result
    assert "www.example.com. 3600 IN A 192.0.2.20" in result
    assert " SOA " in result  # SOA is always preserved


def test_write_text_safely_when_target_exists_without_overwrite_then_raises(tmp_path: Path) -> None:
    output_path = tmp_path / "existing.zone"
    output_path.write_text("existing", encoding="utf-8")

    with pytest.raises(ZoneFileError, match="refusing to overwrite"):
        write_text_safely(output_path, "new")

    write_text_safely(output_path, "new", overwrite=True)
    assert output_path.read_text(encoding="utf-8") == "new"
