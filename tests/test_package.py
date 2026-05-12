# this_file: tests/test_package.py

from donazopy import __version__


def test_version_when_package_not_installed_then_has_string_fallback() -> None:
    assert isinstance(__version__, str)
    assert __version__
