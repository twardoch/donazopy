# this_file: tests/test_target.py

from __future__ import annotations

from pathlib import Path

import pytest

from donazopy.target import Target, TargetError, looks_like_path, parse_target, resolve_provider_key


def test_parse_target_when_bare_domain_then_no_provider_or_filters() -> None:
    target = parse_target("example.com")

    assert target == Target(
        provider=None,
        domain="example.com",
        record_type=None,
        host_name=None,
        value=None,
        raw="example.com",
    )


def test_parse_target_when_provider_and_domain_then_explicit_provider() -> None:
    target = parse_target("cloudflare/example.com")

    assert target.provider == "cloudflare"
    assert target.domain == "example.com"
    assert target.record_type is None


def test_parse_target_when_wildcard_segments_then_treated_as_none() -> None:
    target = parse_target("cloudflare/example.com:*:*:*")

    assert target.provider == "cloudflare"
    assert target.domain == "example.com"
    assert target.record_type is None
    assert target.host_name is None
    assert target.value is None


def test_parse_target_when_provider_star_then_all_domains() -> None:
    target = parse_target("cloudflare/*")

    assert target.provider == "cloudflare"
    assert target.domain == "*"
    assert target.is_all_domains is True


def test_parse_target_when_record_filters_then_record_type_uppercased() -> None:
    target = parse_target("cloudflare/example.com:a:www:192.0.2.1")

    assert target.record_type == "A"
    assert target.host_name == "www"
    assert target.value == "192.0.2.1"


def test_parse_target_when_partial_filters_then_missing_segments_are_none() -> None:
    target = parse_target("example.com:TXT")

    assert target.record_type == "TXT"
    assert target.host_name is None
    assert target.value is None


def test_parse_target_when_empty_then_raises() -> None:
    with pytest.raises(TargetError, match="target is empty"):
        parse_target("")


def test_parse_target_when_whitespace_only_then_raises() -> None:
    with pytest.raises(TargetError, match="target is empty"):
        parse_target("   ")


def test_parse_target_when_empty_provider_then_raises() -> None:
    with pytest.raises(TargetError, match="empty provider"):
        parse_target("/example.com")


def test_parse_target_when_too_many_segments_then_raises() -> None:
    with pytest.raises(TargetError, match="too many ':' segments"):
        parse_target("example.com:A:www:1.2.3.4:extra")


def test_parse_target_when_only_provider_slash_wildcard_then_ok() -> None:
    target = parse_target("cloudflare/*:*:*:*")

    assert target.provider == "cloudflare"
    assert target.domain == "*"


def test_looks_like_path_when_has_separator_then_true(tmp_path: Path) -> None:
    assert looks_like_path("zones/example.com.zone") is True
    assert looks_like_path("./relative.txt") is True


def test_looks_like_path_when_zone_or_txt_extension_then_true() -> None:
    assert looks_like_path("example.com.zone") is True
    assert looks_like_path("dump.txt") is True


def test_looks_like_path_when_existing_file_then_true(tmp_path: Path) -> None:
    f = tmp_path / "data"
    f.write_text("x", encoding="utf-8")
    assert looks_like_path(str(f)) is True


def test_looks_like_path_when_plain_domain_then_false() -> None:
    assert looks_like_path("example.com") is False
    # A single 'provider/domain' style slash is a target, not a path.
    assert looks_like_path("cloudflare/example.com") is False
    # Two or more slashes look like a real path.
    assert looks_like_path("a/b/c") is True


def test_target_is_local_path_property_when_path_then_true() -> None:
    assert parse_target("zones/x.zone").is_local_path is True


def test_resolve_provider_key_when_explicit_then_returns_it() -> None:
    target = parse_target("cloudflare/example.com")
    assert resolve_provider_key(target, ("cloudflare",)) == "cloudflare"


def test_resolve_provider_key_when_none_and_single_provider_then_returns_it() -> None:
    target = parse_target("example.com")
    assert resolve_provider_key(target, ("cloudflare",)) == "cloudflare"


def test_resolve_provider_key_when_none_and_zero_providers_then_raises() -> None:
    target = parse_target("example.com")
    with pytest.raises(TargetError, match="prefix the target with 'provider/'"):
        resolve_provider_key(target, ())


def test_resolve_provider_key_when_none_and_many_providers_then_raises() -> None:
    target = parse_target("example.com")
    with pytest.raises(TargetError, match="prefix the target with 'provider/'"):
        resolve_provider_key(target, ("cloudflare", "route53"))


def test_resolve_provider_key_when_explicit_unknown_then_raises() -> None:
    target = parse_target("route53/example.com")
    with pytest.raises(TargetError, match="not an operational provider"):
        resolve_provider_key(target, ("cloudflare",))


def test_target_matches_record_when_type_filter_then_filters() -> None:
    target = parse_target("example.com:A")
    assert target.matches_record({"type": "A", "name": "www.example.com", "content": "1.2.3.4"}) is True
    assert target.matches_record({"type": "TXT", "name": "www.example.com", "content": "x"}) is False


def test_target_matches_record_when_no_filters_then_true() -> None:
    target = parse_target("example.com")
    assert target.matches_record({"type": "A"}) is True
