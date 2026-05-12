# this_file: src/donazopy/__init__.py
"""DNS and domain-provider management CLI package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("donazopy")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
