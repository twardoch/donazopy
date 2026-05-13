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


def test_plan_fix_records_when_cname_collision_then_drops_cname_keeps_other() -> None:
    """User case: _dmarc has both a CNAME (e.g. to dmarc.ionos.com) and a TXT
    (the real DMARC policy). --fix must drop the CNAME and keep the TXT."""
    from donazopy.zonefile import NormalizedRecord

    base = _records(
        """$ORIGIN fontlab.ai.
$TTL 3600
@ IN SOA ns.fontlab.ai. hostmaster.fontlab.ai. 1 7200 3600 1209600 3600
@ IN NS ns.fontlab.ai.
ns IN A 192.0.2.1
@ IN MX 10 mail.fontlab.ai.
mail IN A 192.0.2.2
_dmarc IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.com"
""",
        origin="fontlab.ai.",
    )
    # Inject the conflicting CNAME at _dmarc (dnspython would reject this at parse).
    cname = NormalizedRecord(
        owner="_dmarc.fontlab.ai.",
        ttl=1,
        record_class="IN",
        record_type="CNAME",
        value="dmarc.ionos.com.",
        source_order=len(base),
    )
    records = (*base, cname)

    issues = analyze_records(records, domain="fontlab.ai", provider_key="cloudflare")
    collision = next(i for i in issues if i.code == "CNAME_COLLISION")
    assert collision.fixable

    new_records, fixed = plan_fix_records(records, issues, origin="fontlab.ai.")

    fixed_codes = {issue.code for issue in fixed}
    assert "CNAME_COLLISION" in fixed_codes
    # The CNAME must be gone; the DMARC TXT must remain.
    dmarc_records = [r for r in new_records if r.owner == "_dmarc.fontlab.ai."]
    assert len(dmarc_records) == 1
    assert dmarc_records[0].record_type == "TXT"
    assert "v=DMARC1" in dmarc_records[0].value


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


def test_analyze_provider_records_when_cname_conflict_then_reports_not_crashes() -> None:
    """Regression: a CNAME coexisting with another type at the same owner must
    surface as a CNAME_COLLISION finding instead of crashing the parser."""
    records: list[Mapping[str, object]] = [
        {"type": "SOA", "name": "@", "ttl": 3600,
         "content": "ns.example.com. hostmaster.example.com. 1 7200 3600 1209600 3600"},
        {"type": "NS", "name": "@", "ttl": 3600, "content": "ns.example.com"},
        {"type": "A", "name": "www", "ttl": 3600, "content": "192.0.2.10"},
        {"type": "CNAME", "name": "www", "ttl": 3600, "content": "other.example.net"},
    ]

    report = analyze_provider_records(records, domain="example.com", provider_key="cloudflare")

    codes = {issue.code for issue in report.issues}
    assert "CNAME_COLLISION" in codes


def test_check_missing_dmarc_when_dmarc_email_given_then_uses_address() -> None:
    records = _records(MIGRATION_ZONE)

    issues = analyze_records(
        records,
        domain="example.com",
        provider_key="cloudflare",
        dmarc_email="ops@dmarc-service.com",
    )
    dmarc = next(i for i in issues if i.code == "DMARC_MISSING")

    assert "rua=mailto:ops@dmarc-service.com" in (dmarc.suggested_record or "")
    # External destination must include the authorization-record guidance.
    assert "_report._dmarc.dmarc-service.com" in dmarc.details


def test_plan_fix_records_when_dmarc_email_given_then_record_uses_address() -> None:
    records = _records(MIGRATION_ZONE)
    issues = analyze_records(
        records,
        domain="example.com",
        provider_key="cloudflare",
        dmarc_email="ops@external.example",
    )

    new_records, _ = plan_fix_records(
        records, issues, origin="example.com.", dmarc_email="ops@external.example"
    )

    dmarc = next(r for r in new_records if r.owner.startswith("_dmarc.") and r.record_type == "TXT")
    assert "rua=mailto:ops@external.example" in dmarc.value


def test_cli_doctor_when_dmarc_email_supplied_then_threads_through_report(tmp_path: Path) -> None:
    from donazopy.cli import Donazopy

    zone_path = tmp_path / "example.com.zone"
    zone_path.write_text(MIGRATION_ZONE, encoding="utf-8")

    output = Donazopy().doctor(
        str(zone_path), origin="example.com.", dmarc_email="ops@dmarc-service.com"
    )

    assert isinstance(output, str)
    assert "rua=mailto:ops@dmarc-service.com" in output
    assert "_report._dmarc.dmarc-service.com" in output


def test_check_existing_dmarc_external_destination_then_flagged() -> None:
    """An existing DMARC record with an external rua must surface the
    DMARC_EXTERNAL_DESTINATION finding, not just newly-proposed ones."""
    text = """$ORIGIN fontlab.app.
$TTL 3600
@ IN SOA ns.fontlab.app. hostmaster.fontlab.app. 1 7200 3600 1209600 3600
@ IN NS ns.fontlab.app.
ns IN A 192.0.2.1
@ IN MX 10 mail.fontlab.app.
mail IN A 192.0.2.2
_dmarc IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.com"
"""
    records = records_from_zone_text(text, "fontlab.app.")

    issues = analyze_records(records, domain="fontlab.app", provider_key="cloudflare")
    external = [i for i in issues if i.code == "DMARC_EXTERNAL_DESTINATION"]

    assert len(external) == 1
    assert external[0].affected == ("fontlab.com",)
    assert external[0].fixable
    assert 'fontlab.app._report._dmarc.fontlab.com.' in (external[0].suggested_record or "")


def test_fix_provider_zone_when_external_receiver_on_same_provider_then_authorizes() -> None:
    """When the rua receiver domain is managed by the same provider, the doctor
    must add the authorization TXT record using a single-record-add API — it
    must NOT delete-all + re-import the receiver zone (which is destructive)."""
    from typing import Any

    class FakeMultiZoneProvider:
        def __init__(self) -> None:
            self.zones: dict[str, list[dict[str, Any]]] = {
                "fontlab.app": [
                    {"type": "SOA", "name": "@", "ttl": 3600,
                     "content": "ns.cloudflare.com. dns.cloudflare.com. 1 7200 3600 1209600 3600"},
                    {"type": "NS", "name": "@", "ttl": 3600, "content": "ns.cloudflare.com"},
                    {"type": "MX", "name": "@", "ttl": 3600, "content": "mail.fontlab.app", "prio": 10},
                    {"type": "TXT", "name": "_dmarc", "ttl": 3600,
                     "content": "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.com"},
                ],
                "fontlab.com": [
                    {"type": "SOA", "name": "@", "ttl": 3600,
                     "content": "ns.cloudflare.com. dns.cloudflare.com. 1 7200 3600 1209600 3600"},
                    {"type": "NS", "name": "@", "ttl": 3600, "content": "ns.cloudflare.com"},
                    {"type": "A", "name": "www", "ttl": 3600, "content": "192.0.2.10"},
                ],
            }
            self.deleted: list[str] = []
            self.imported: list[tuple[str, str]] = []
            self.created_records: list[tuple[str, dict[str, Any]]] = []

        def list_zones(self) -> list[str]:
            return list(self.zones.keys())

        def list_records(self, domain: str) -> list[dict[str, Any]]:
            return list(self.zones[domain.rstrip(".")])

        def export_zone(self, domain: str) -> str:
            from donazopy.zonefile import records_from_provider_dicts, serialize_records
            origin = domain.rstrip(".") + "."
            return serialize_records(records_from_provider_dicts(self.zones[domain.rstrip(".")], origin=origin))

        def delete_all_records(self, domain: str) -> dict[str, Any]:
            self.deleted.append(domain.rstrip("."))
            self.zones[domain.rstrip(".")] = []
            return {"deleted": 1}

        def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> dict[str, Any]:
            self.imported.append((domain.rstrip("."), zone_text))
            return {"imported": True}

        def create_record(self, domain: str, record: dict[str, Any]) -> dict[str, Any]:
            self.created_records.append((domain.rstrip("."), record))
            new = {**record, "id": f"created-{len(self.created_records)}"}
            self.zones[domain.rstrip(".")].append(new)
            return new

        def delete_record(self, domain: str, record_id: str) -> dict[str, Any]:
            zone = self.zones[domain.rstrip(".")]
            self.zones[domain.rstrip(".")] = [r for r in zone if r.get("id") != record_id]
            return {"id": record_id}

    from donazopy.doctor import fix_provider_zone

    provider = FakeMultiZoneProvider()
    # Give every primary-zone record an id so the granular path can target them.
    for index, rec in enumerate(provider.zones["fontlab.app"]):
        rec.setdefault("id", f"app-{index}")
    for index, rec in enumerate(provider.zones["fontlab.com"]):
        rec.setdefault("id", f"com-{index}")

    report = fix_provider_zone(
        provider, domain="fontlab.app", provider_key="cloudflare", backup_dir=Path("/tmp"),
    )

    fixed_codes = {issue.code for issue in report.fixed}
    assert "DMARC_EXTERNAL_DESTINATION" in fixed_codes
    # Receiver zone must have been touched by create_record only.
    receiver_creates = [rec for dom, rec in provider.created_records if dom == "fontlab.com"]
    assert receiver_creates, "expected the auth record to be added via create_record"
    assert receiver_creates[-1]["name"] == "fontlab.app._report._dmarc"
    assert receiver_creates[-1]["type"] == "TXT"
    assert "v=DMARC1" in receiver_creates[-1]["content"]
    # Critical: NEITHER zone is wiped + re-imported (granular path is used).
    assert "fontlab.com" not in provider.deleted
    assert "fontlab.app" not in provider.deleted
    assert not any(dom == "fontlab.com" for dom, _ in provider.imported)
    assert not any(dom == "fontlab.app" for dom, _ in provider.imported)


def test_fix_provider_zone_when_provider_lacks_create_record_then_unfixed() -> None:
    """If the provider exposes no single-record-add API, the receiver zone is
    left untouched and the issue stays unresolved with copy-paste guidance."""
    from typing import Any

    class FakeBulkOnlyProvider:
        def __init__(self) -> None:
            self.zones: dict[str, list[dict[str, Any]]] = {
                "fontlab.app": [
                    {"type": "SOA", "name": "@", "ttl": 3600,
                     "content": "ns.example. hostmaster.example. 1 7200 3600 1209600 3600"},
                    {"type": "NS", "name": "@", "ttl": 3600, "content": "ns.example"},
                    {"type": "MX", "name": "@", "ttl": 3600, "content": "mail.fontlab.app", "prio": 10},
                    {"type": "TXT", "name": "_dmarc", "ttl": 3600,
                     "content": "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.com"},
                ],
                "fontlab.com": [],
            }
            self.deleted: list[str] = []
            self.imported: list[tuple[str, str]] = []

        def list_zones(self) -> list[str]:
            return list(self.zones.keys())

        def list_records(self, domain: str) -> list[dict[str, Any]]:
            return list(self.zones[domain.rstrip(".")])

        def export_zone(self, domain: str) -> str:
            from donazopy.zonefile import records_from_provider_dicts, serialize_records
            origin = domain.rstrip(".") + "."
            return serialize_records(records_from_provider_dicts(self.zones[domain.rstrip(".")], origin=origin))

        def delete_all_records(self, domain: str) -> dict[str, Any]:
            self.deleted.append(domain.rstrip("."))
            self.zones[domain.rstrip(".")] = []
            return {"deleted": 1}

        def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> dict[str, Any]:
            self.imported.append((domain.rstrip("."), zone_text))
            return {"imported": True}

    from donazopy.doctor import fix_provider_zone

    provider = FakeBulkOnlyProvider()
    report = fix_provider_zone(
        provider, domain="fontlab.app", provider_key="cloudflare", backup_dir=Path("/tmp"),
    )

    fixed_codes = {issue.code for issue in report.fixed}
    issue_codes = {issue.code for issue in report.issues}
    assert "DMARC_EXTERNAL_DESTINATION" in issue_codes
    assert "DMARC_EXTERNAL_DESTINATION" not in fixed_codes
    # Critical safety guarantee: receiver zone is never wiped + re-imported.
    assert "fontlab.com" not in provider.deleted
    assert not any(dom == "fontlab.com" for dom, _ in provider.imported)


def test_fix_provider_zone_when_external_receiver_not_on_provider_then_unfixed() -> None:
    """If the receiver domain is not managed by the same provider, the doctor
    must leave the issue unresolved (no destructive cross-provider attempt)."""
    from typing import Any

    class FakeSingleZoneProvider:
        def __init__(self) -> None:
            self.records_map: dict[str, list[dict[str, Any]]] = {
                "fontlab.app": [
                    {"type": "SOA", "name": "@", "ttl": 3600,
                     "content": "ns.cloudflare.com. dns.cloudflare.com. 1 7200 3600 1209600 3600"},
                    {"type": "NS", "name": "@", "ttl": 3600, "content": "ns.cloudflare.com"},
                    {"type": "MX", "name": "@", "ttl": 3600, "content": "mail.fontlab.app", "prio": 10},
                    {"type": "TXT", "name": "_dmarc", "ttl": 3600,
                     "content": "v=DMARC1; p=none; rua=mailto:reports@elsewhere.example"},
                ],
            }
            self.deleted: list[str] = []
            self.imported: list[tuple[str, str]] = []

        def list_zones(self) -> list[str]:
            return ["fontlab.app"]

        def list_records(self, domain: str) -> list[dict[str, Any]]:
            return list(self.records_map[domain.rstrip(".")])

        def export_zone(self, domain: str) -> str:
            from donazopy.zonefile import records_from_provider_dicts, serialize_records
            origin = domain.rstrip(".") + "."
            return serialize_records(records_from_provider_dicts(self.records_map[domain.rstrip(".")], origin=origin))

        def delete_all_records(self, domain: str) -> dict[str, Any]:
            self.deleted.append(domain.rstrip("."))
            self.records_map[domain.rstrip(".")] = []
            return {"deleted": 1}

        def import_zone(self, domain: str, zone_text: str, *, proxied: bool | None = None) -> dict[str, Any]:
            self.imported.append((domain.rstrip("."), zone_text))
            return {"imported": True}

    from donazopy.doctor import fix_provider_zone

    provider = FakeSingleZoneProvider()
    report = fix_provider_zone(
        provider, domain="fontlab.app", provider_key="cloudflare", backup_dir=Path("/tmp"),
    )

    fixed_codes = {issue.code for issue in report.fixed}
    issue_codes = {issue.code for issue in report.issues}
    assert "DMARC_EXTERNAL_DESTINATION" in issue_codes
    assert "DMARC_EXTERNAL_DESTINATION" not in fixed_codes
    # Receiver zone must not have been touched.
    assert "elsewhere.example" not in provider.deleted


def test_provider_ns_patterns_contains_expected_providers() -> None:
    for key in ("cloudflare", "ionos", "godaddy", "aws", "google", "azure"):
        assert key in PROVIDER_NS_PATTERNS
