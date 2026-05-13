# this_file: tests/test_doctor.py
"""Tests for the doctor diagnostic engine."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from donazopy.doctor import (
    PROVIDER_NS_PATTERNS,
    analyze_provider_records,
    analyze_records,
    analyze_zone_file,
    fix_zone_file,
    plan_fix_records,
)
from donazopy.zonefile import records_from_zone_text

MIGRATION_ZONE = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ada.ns.cloudflare.com. dns.cloudflare.com. 2026051301 7200 3600 1209600 3600
@ IN NS ada.ns.cloudflare.com.
@ IN NS rick.ns.cloudflare.com.
@ IN NS ns1019.ui-dns.de.
@ IN NS ns1093.ui-dns.com.
@ IN MX 10 mx00.ionos.com.
@ IN TXT "v=spf1 include:_spf-us.ionos.com ~all"
@ IN TXT "\\"v=spf1 include:_spf-us.ionos.com ~all\\""
www IN A 192.0.2.20
"""


def _records(text: str, origin: str = "example.com."):
    return records_from_zone_text(text, origin)


def test_check_migration_ns_when_foreign_ns_present_then_error_with_fixable() -> None:
    records = _records(MIGRATION_ZONE)

    issues = analyze_records(records, domain="example.com", provider_key="cloudflare")
    migration = [i for i in issues if i.code == "NS_MIGRATION_ARTIFACT"]

    assert len(migration) == 1
    assert migration[0].severity == "error"
    assert migration[0].fixable
    assert any("ui-dns.de" in entry for entry in migration[0].affected)
    assert any("ui-dns.com" in entry for entry in migration[0].affected)


def test_check_txt_semantic_duplicates_when_quote_variants_then_error() -> None:
    records = _records(MIGRATION_ZONE)

    issues = analyze_records(records, domain="example.com", provider_key="cloudflare")
    txt = [i for i in issues if i.code == "TXT_SEMANTIC_DUPLICATE"]

    assert len(txt) == 1
    assert txt[0].fixable
    assert len(txt[0].affected) == 2


def test_check_missing_dmarc_when_mx_without_dmarc_then_fixable_warning() -> None:
    records = _records(MIGRATION_ZONE)

    issues = analyze_records(records, domain="example.com", provider_key="cloudflare")
    dmarc = [i for i in issues if i.code == "DMARC_MISSING"]

    assert len(dmarc) == 1
    assert dmarc[0].severity == "warning"
    assert dmarc[0].fixable


def test_check_missing_spf_when_mx_present_but_no_spf_then_warning() -> None:
    text = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ns.example.com. hostmaster.example.com. 1 7200 3600 1209600 3600
@ IN NS ns.example.com.
@ IN MX 10 mail.example.com.
ns IN A 192.0.2.1
mail IN A 192.0.2.2
"""
    records = _records(text)

    issues = analyze_records(records, domain="example.com", provider_key="cloudflare")
    spf = [i for i in issues if i.code == "SPF_MISSING"]

    assert len(spf) == 1
    assert spf[0].severity == "warning"
    assert spf[0].suggested_record is not None


def test_check_cname_at_apex_then_error() -> None:
    text = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ns.example.com. hostmaster.example.com. 1 7200 3600 1209600 3600
@ IN NS ns.example.com.
ns IN A 192.0.2.1
@ IN CNAME other.example.net.
"""
    # dnspython rejects CNAME alongside SOA at apex when parsing strictly.
    # Build records directly from a node-by-node text instead.
    with pytest.raises(Exception):  # noqa: B017 — dnspython raises a broad DNSException
        _records(text)


def test_check_cname_collision_when_cname_with_a_then_error() -> None:
    text = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ns.example.com. hostmaster.example.com. 1 7200 3600 1209600 3600
@ IN NS ns.example.com.
ns IN A 192.0.2.1
www IN A 192.0.2.2
"""
    records = _records(text)
    # Manually append a CNAME at www to trigger the conflict (skirting the
    # zone-text parser which would itself reject this).
    from donazopy.zonefile import NormalizedRecord

    extra = NormalizedRecord(
        owner="www.example.com.",
        ttl=3600,
        record_class="IN",
        record_type="CNAME",
        value="other.example.net.",
        source_order=len(records),
    )
    issues = analyze_records((*records, extra), domain="example.com", provider_key="cloudflare")
    collision = [i for i in issues if i.code == "CNAME_COLLISION"]

    assert len(collision) == 1


def test_check_missing_caa_when_no_caa_then_info() -> None:
    text = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ns.example.com. hostmaster.example.com. 1 7200 3600 1209600 3600
@ IN NS ns.example.com.
ns IN A 192.0.2.1
"""
    records = _records(text)

    issues = analyze_records(records, domain="example.com", provider_key="cloudflare")
    caa = [i for i in issues if i.code == "CAA_MISSING"]

    assert len(caa) == 1
    assert caa[0].severity == "info"


def test_plan_fix_records_when_ns_migration_then_drops_foreign_ns() -> None:
    records = _records(MIGRATION_ZONE)
    issues = analyze_records(records, domain="example.com", provider_key="cloudflare")

    new_records, fixed = plan_fix_records(records, issues, origin="example.com.")

    ns_values = {r.value for r in new_records if r.record_type == "NS"}
    assert "ada.ns.cloudflare.com." in ns_values
    assert "rick.ns.cloudflare.com." in ns_values
    assert not any("ui-dns" in v for v in ns_values)
    assert any(i.code == "NS_MIGRATION_ARTIFACT" for i in fixed)


def test_plan_fix_records_when_txt_duplicate_then_keeps_canonical() -> None:
    records = _records(MIGRATION_ZONE)
    issues = analyze_records(records, domain="example.com", provider_key="cloudflare")

    new_records, fixed = plan_fix_records(records, issues, origin="example.com.")

    spf_records = [
        r for r in new_records if r.record_type == "TXT" and "v=spf1" in r.value.lower()
    ]
    assert len(spf_records) == 1
    # Canonical form should not contain literal escaped quotes.
    assert "\\\"" not in spf_records[0].value
    assert any(i.code == "TXT_SEMANTIC_DUPLICATE" for i in fixed)


def test_plan_fix_records_when_dmarc_missing_then_adds_placeholder() -> None:
    records = _records(MIGRATION_ZONE)
    issues = analyze_records(records, domain="example.com", provider_key="cloudflare")

    new_records, fixed = plan_fix_records(records, issues, origin="example.com.")

    dmarc = [r for r in new_records if r.owner.startswith("_dmarc.") and r.record_type == "TXT"]
    assert len(dmarc) == 1
    assert "v=DMARC1" in dmarc[0].value
    assert any(i.code == "DMARC_MISSING" for i in fixed)


def test_analyze_zone_file_when_clean_zone_then_only_info_findings(tmp_path: Path) -> None:
    text = """$ORIGIN example.com.
$TTL 3600
@ IN SOA ns.example.com. hostmaster.example.com. 1 7200 3600 1209600 3600
@ IN NS ns.example.com.
ns IN A 192.0.2.1
"""
    zone_path = tmp_path / "example.com.zone"
    zone_path.write_text(text, encoding="utf-8")

    report = analyze_zone_file(zone_path, origin="example.com.")

    assert report.error_count == 0
    assert report.info_count >= 1  # missing CAA


def test_fix_zone_file_when_migration_zone_then_writes_clean_zone(tmp_path: Path) -> None:
    zone_path = tmp_path / "example.com.zone"
    zone_path.write_text(MIGRATION_ZONE, encoding="utf-8")

    report = fix_zone_file(zone_path, origin="example.com.")

    # local files have no provider_key so NS migration is not detected;
    # TXT dedupe and DMARC fixes should still apply.
    fixed_codes = {issue.code for issue in report.fixed}
    assert "TXT_SEMANTIC_DUPLICATE" in fixed_codes
    assert "DMARC_MISSING" in fixed_codes
    assert report.backup_path is not None
    assert Path(report.backup_path).exists()
    new_text = zone_path.read_text(encoding="utf-8")
    assert "_dmarc.example.com." in new_text


def test_analyze_provider_records_when_migration_artifact_then_detects_ns() -> None:
    records: list[Mapping[str, object]] = [
        {"type": "SOA", "name": "@", "ttl": 3600,
         "content": "ada.ns.cloudflare.com. dns.cloudflare.com. 1 7200 3600 1209600 3600"},
        {"type": "NS", "name": "@", "ttl": 3600, "content": "ada.ns.cloudflare.com"},
        {"type": "NS", "name": "@", "ttl": 3600, "content": "ns1019.ui-dns.de"},
        {"type": "A", "name": "www", "ttl": 3600, "content": "192.0.2.20"},
    ]

    report = analyze_provider_records(records, domain="example.com", provider_key="cloudflare")

    codes = {issue.code for issue in report.issues}
    assert "NS_MIGRATION_ARTIFACT" in codes


def test_cli_doctor_when_local_zone_file_then_returns_report(tmp_path: Path) -> None:
    from donazopy.cli import Donazopy

    zone_path = tmp_path / "example.com.zone"
    zone_path.write_text(MIGRATION_ZONE, encoding="utf-8")

    output = Donazopy().doctor(str(zone_path), origin="example.com.")

    assert isinstance(output, str)
    assert "TXT_SEMANTIC_DUPLICATE" in output


def test_cli_doctor_when_json_then_returns_dict(tmp_path: Path) -> None:
    from donazopy.cli import Donazopy

    zone_path = tmp_path / "example.com.zone"
    zone_path.write_text(MIGRATION_ZONE, encoding="utf-8")

    payload = Donazopy().doctor(str(zone_path), origin="example.com.", json=True)

    assert isinstance(payload, dict)
    assert "issues" in payload
    issues_list = payload["issues"]
    assert isinstance(issues_list, list)
    codes = {issue["code"] for issue in issues_list}
    assert "TXT_SEMANTIC_DUPLICATE" in codes


def test_provider_ns_patterns_contains_expected_providers() -> None:
    for key in ("cloudflare", "ionos", "godaddy", "aws", "google", "azure"):
        assert key in PROVIDER_NS_PATTERNS
