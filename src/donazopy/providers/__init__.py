# this_file: src/donazopy/providers/__init__.py
"""Provider integration modules for DNS hosts and domain registrars."""

from donazopy.providers.registry import get_provider, list_providers

__all__ = ["get_provider", "list_providers"]
