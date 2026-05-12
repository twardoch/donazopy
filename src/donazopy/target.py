# this_file: src/donazopy/target.py
"""Unified target notation: ``[provider/][domain][:record_type][:host_name][:value]``."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class TargetError(ValueError):
    """Raised when a target string is malformed or cannot be resolved."""


_WILDCARD = "*"


def _none_if_wildcard(segment: str | None) -> str | None:
    """Return ``None`` for empty or ``*`` segments, otherwise the stripped value."""
    if segment is None:
        return None
    cleaned = segment.strip()
    if not cleaned or cleaned == _WILDCARD:
        return None
    return cleaned


@dataclass(frozen=True, slots=True)
class Target:
    """A parsed reference to a provider/domain and optional record-level filters.

    ``provider`` of ``None`` means "use the operational provider that manages it".
    ``domain`` of ``"*"`` means "all domains on the provider".
    """

    provider: str | None
    domain: str | None
    record_type: str | None
    host_name: str | None
    value: str | None
    raw: str

    @property
    def is_all_domains(self) -> bool:
        """Return whether the target refers to every domain on the provider."""
        return self.domain == _WILDCARD

    @property
    def is_local_path(self) -> bool:
        """Return whether the raw target looks like a local zone-file path."""
        return looks_like_path(self.raw)

    def matches_record(self, record: object) -> bool:
        """Return whether a mapping-like DNS record matches the record-level filters."""
        if not isinstance(record, dict):
            return True
        if self.record_type is not None:
            record_type = str(record.get("type", "")).upper()
            if record_type != self.record_type:
                return False
        if self.host_name is not None:
            name = str(record.get("name", ""))
            if name.rstrip(".") != self.host_name.rstrip("."):
                return False
        if self.value is not None:
            content = str(record.get("content", ""))
            if content != self.value:
                return False
        return True

    def to_dict(self) -> dict[str, str | None]:
        """Return a JSON-serializable mapping of the target."""
        return {
            "provider": self.provider,
            "domain": self.domain,
            "record_type": self.record_type,
            "host_name": self.host_name,
            "value": self.value,
            "raw": self.raw,
        }


def looks_like_path(text: str) -> bool:
    """Return whether ``text`` looks like a local file path rather than a target.

    Heuristics, in order:
    - ends in ``.zone`` / ``.txt`` -> path;
    - starts with ``/``, ``./``, ``../``, ``~``, or contains a backslash -> path;
    - points at an existing file on disk -> path;
    - contains two or more ``/`` separators -> path;
    - a single ``/`` separator -> treated as ``provider/domain`` (NOT a path).
    """
    if not text:
        return False
    lowered = text.lower()
    if lowered.endswith((".zone", ".txt")):
        return True
    if text.startswith(("/", "./", "../", "~", ".\\", "..\\")) or "\\" in text:
        return True
    try:
        if Path(text).is_file():
            return True
    except OSError:
        pass
    return text.count("/") >= 2


def parse_target(text: str) -> Target:
    """Parse a target string into a :class:`Target`.

    Notation: ``[provider/][domain][:record_type][:host_name][:value]``.

    Raises:
        TargetError: if the input is empty, has an empty provider, or has more than
            four ``:`` separated segments.
    """
    if text is None:
        msg = "target is empty; expected '[provider/][domain][:record_type][:host_name][:value]'"
        raise TargetError(msg)
    raw = text
    stripped = text.strip()
    if not stripped:
        msg = "target is empty; expected '[provider/][domain][:record_type][:host_name][:value]'"
        raise TargetError(msg)

    provider: str | None = None
    remainder = stripped
    if "/" in stripped and not _is_path_like_prefix(stripped):
        provider_part, _, remainder = stripped.partition("/")
        provider_clean = provider_part.strip()
        if not provider_clean:
            msg = f"target {raw!r} has an empty provider before '/'; use 'provider/domain'"
            raise TargetError(msg)
        provider = provider_clean

    segments = remainder.split(":")
    if len(segments) > 4:
        msg = f"target {raw!r} has too many ':' segments; expected at most 'domain:record_type:host_name:value'"
        raise TargetError(msg)

    while len(segments) < 4:
        segments.append("")

    # The domain slot keeps a literal '*' (meaning "all domains on the provider")
    # but an empty slot becomes None.
    raw_domain = segments[0].strip()
    domain: str | None = raw_domain if raw_domain else None

    record_type = _none_if_wildcard(segments[1])
    if record_type is not None:
        record_type = record_type.upper()
    host_name = _none_if_wildcard(segments[2])
    value = _none_if_wildcard(segments[3])

    if provider is None and domain is None:
        msg = (
            f"target {raw!r} has no provider and no domain; expected "
            "'[provider/][domain][:record_type][:host_name][:value]'"
        )
        raise TargetError(msg)

    return Target(
        provider=provider,
        domain=domain,
        record_type=record_type,
        host_name=host_name,
        value=value,
        raw=raw,
    )


def _is_path_like_prefix(text: str) -> bool:
    """Return whether ``text`` should be treated as a path (so '/' is not a provider sep).

    Note: a bare leading ``/`` is *not* treated as a path here so that ``/domain``
    surfaces a clear "empty provider" error; callers that want path detection use
    :func:`looks_like_path` first.
    """
    if text.startswith(("./", "../", "~", ".\\", "..\\")):
        return True
    if "\\" in text:
        return True
    if os.sep != "/" and os.sep in text:
        return True
    if text.count("/") >= 2:
        return True
    if "/" in text:
        head = text.split("/", 1)[0]
        try:
            if Path(text).is_file():
                return True
        except OSError:
            pass
        # "zones/file.zone" style: head looks like a directory, not a provider key.
        if "." in head:
            return True
        if text.lower().endswith((".zone", ".txt")):
            return True
    return False


def resolve_provider_key(target: Target, operational_keys: tuple[str, ...]) -> str:
    """Resolve the provider key for an operation that needs one.

    Args:
        target: the parsed target.
        operational_keys: keys of providers that can perform live operations.

    Returns:
        The explicit provider key, or the sole operational provider key.

    Raises:
        TargetError: if no provider is given and there is not exactly one candidate,
            or if an explicit provider is not operational.
    """
    if target.provider is not None:
        if target.provider not in operational_keys:
            available = ", ".join(sorted(operational_keys)) or "(none)"
            msg = f"provider {target.provider!r} is not an operational provider; available: {available}"
            raise TargetError(msg)
        return target.provider
    if len(operational_keys) == 1:
        return operational_keys[0]
    available = ", ".join(sorted(operational_keys)) or "(none)"
    msg = (
        f"target {target.raw!r} does not specify a provider and there is not exactly "
        f"one operational provider (have: {available}); prefix the target with 'provider/'"
    )
    raise TargetError(msg)


__all__ = [
    "Target",
    "TargetError",
    "looks_like_path",
    "parse_target",
    "resolve_provider_key",
]
