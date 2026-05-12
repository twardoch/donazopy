# this_file: tests/test_provider_base.py

from pathlib import Path

import pytest

from donazopy.providers.base import ProviderCredentialError, credential_status, load_provider_credentials
from donazopy.providers.registry import get_provider


def test_credential_status_when_dotenv_has_token_then_redacts_value(tmp_path: Path) -> None:
    provider = get_provider("cloudflare")
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("CLOUDFLARE_API_TOKEN=dotenv-token\n", encoding="utf-8")

    status = credential_status(provider, dotenv_path=dotenv_path, env={}, discover=False)

    assert status.is_complete is True
    assert status.present == ("CLOUDFLARE_API_TOKEN",)
    assert status.missing == ()
    assert status.to_dict()["redacted"] == {"CLOUDFLARE_API_TOKEN": "***"}
    assert status.sources["CLOUDFLARE_API_TOKEN"] == str(dotenv_path)


def test_load_provider_credentials_when_env_and_dotenv_have_token_then_env_wins(tmp_path: Path) -> None:
    provider = get_provider("cloudflare")
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("CLOUDFLARE_API_TOKEN=dotenv-token\n", encoding="utf-8")

    credentials = load_provider_credentials(
        provider,
        dotenv_path=dotenv_path,
        env={"CLOUDFLARE_API_TOKEN": "environment-token"},
        discover=False,
    )

    assert credentials == {"CLOUDFLARE_API_TOKEN": "environment-token"}


def test_credential_status_when_token_missing_then_reports_missing() -> None:
    provider = get_provider("cloudflare")

    status = credential_status(provider, env={}, discover=False)

    assert status.is_complete is False
    assert status.missing == ("CLOUDFLARE_API_TOKEN",)


def test_provider_status_when_credentials_required_then_raise_clear_error() -> None:
    provider = get_provider("cloudflare")

    with pytest.raises(
        ProviderCredentialError, match="missing required credentials for cloudflare: CLOUDFLARE_API_TOKEN"
    ):
        from donazopy.providers.base import require_provider_credentials

        require_provider_credentials(provider, env={}, discover=False)
