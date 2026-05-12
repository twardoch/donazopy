# this_file: src/donazopy/models.py
"""Shared data models for provider metadata and DNS operation boundaries."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    """A named provider capability exposed by a DNS or registrar integration."""

    name: str
    description: str


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Static metadata describing a provider integration module."""

    key: str
    display_name: str
    category: str
    docs_url: str
    credentials: tuple[str, ...]
    capabilities: tuple[ProviderCapability, ...]
    notes: str

    def supports(self, capability_name: str) -> bool:
        """Return whether this provider advertises a capability by name."""
        return any(capability.name == capability_name for capability in self.capabilities)
