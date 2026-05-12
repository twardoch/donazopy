# this_file: tests/test_registry.py

import pytest

from donazopy.providers.registry import get_provider, list_providers


def test_list_providers_when_called_then_keys_are_unique_sorted_and_operational() -> None:
    keys = [provider.key for provider in list_providers()]

    assert keys == ["cloudflare"]


def test_get_provider_when_unknown_then_lists_available_keys() -> None:
    with pytest.raises(KeyError, match="unknown operational provider"):
        get_provider("missing")
