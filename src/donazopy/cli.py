# this_file: src/donazopy/cli.py
"""Fire-powered donazopy CLI built around the unified target notation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from donazopy import __version__
from donazopy.doctor import (
    analyze_provider_records,
    analyze_zone_file,
    fix_provider_zone,
    fix_zone_file,
)
from donazopy.providers.base import (
    DNSHostingProvider,
    ProviderAPIError,
    RegistrarProvider,
    credential_status,
    require_provider_credentials,
)
from donazopy.providers.registry import (
    create_dns_provider,
    create_registrar_provider,
    get_provider,
    list_providers,
)
from donazopy.target import Target, TargetError, looks_like_path, parse_target, resolve_provider_key
from donazopy.zonefile import (
    diff_zone_records,
    filter_zone_text,
    normalize_zone_file,
    records_from_zone_file,
    records_from_zone_text,
    validate_zone_file,
    write_text_safely,
)

DnsFactory = Callable[..., DNSHostingProvider]
RegistrarFactory = Callable[..., RegistrarProvider]


def _operational_keys() -> tuple[str, ...]:
    return tuple(provider.key for provider in list_providers())


def _split_types(skip_types: str | None) -> tuple[str, ...]:
    if not skip_types:
        return ()
    return tuple(part.strip() for part in skip_types.split(",") if part.strip())


def _dotenv(dotenv_path: str | None) -> Path | None:
    return None if dotenv_path is None else Path(dotenv_path)


class Donazopy:
    """donazopy CLI: DNS and domain-provider management."""

    def __init__(
        self,
        *,
        dns_factory: DnsFactory = create_dns_provider,
        registrar_factory: RegistrarFactory = create_registrar_provider,
    ) -> None:
        self._dns_factory = dns_factory
        self._registrar_factory = registrar_factory

    # -- internal helpers -------------------------------------------------

    def _resolve_target(self, text: str) -> tuple[str, Target]:
        target = parse_target(text)
        key = resolve_provider_key(target, _operational_keys())
        return key, target

    def _dns_provider(self, key: str, dotenv_path: str | None) -> DNSHostingProvider:
        spec = get_provider(key)
        credentials = require_provider_credentials(spec, dotenv_path=_dotenv(dotenv_path))
        return self._dns_factory(key, credentials)

    def _registrar_provider(self, key: str, dotenv_path: str | None) -> RegistrarProvider:
        spec = get_provider(key)
        credentials = require_provider_credentials(spec, dotenv_path=_dotenv(dotenv_path))
        return self._registrar_factory(key, credentials)

    @staticmethod
    def _require_domain(target: Target) -> str:
        if target.domain is None or target.domain == "*":
            msg = (
                f"target {target.raw!r} must name a single domain for this operation; "
                "use 'donazopy domains <provider>' to list a provider's domains"
            )
            raise TargetError(msg)
        return target.domain

    def _provider_key(self, provider: str) -> str:
        """Resolve a provider key from a bare key (``ionos``) or a target (``ionos/*``)."""
        if provider in _operational_keys():
            return provider
        key, _ = self._resolve_target(provider)
        return key

    def _provider_info(self, key: str, dotenv_path: str | None) -> dict[str, object]:
        spec = get_provider(key)
        metadata = {
            "key": spec.key,
            "display_name": spec.display_name,
            "category": spec.category,
            "docs_url": spec.docs_url,
            "credentials": list(spec.credentials),
            "capabilities": [capability.name for capability in spec.capabilities],
            "notes": spec.notes,
        }
        status = credential_status(spec, dotenv_path=_dotenv(dotenv_path))
        return {"metadata": metadata, "credential_status": status.to_dict()}

    def _records_from_side(self, text: str, origin: str | None, dotenv_path: str | None) -> tuple:
        if looks_like_path(text):
            return records_from_zone_file(Path(text), origin)
        key, target = self._resolve_target(text)
        domain = self._require_domain(target)
        zone_text = self._dns_provider(key, dotenv_path).export_zone(domain)
        return records_from_zone_text(zone_text, origin or domain.rstrip(".") + ".")

    # -- commands ---------------------------------------------------------

    def version(self) -> str:
        """Return the installed donazopy version."""
        return __version__

    def providers(self) -> list[str]:
        """List the operational provider keys."""
        return list(_operational_keys())

    def domains(self, provider: str, dotenv_path: str | None = None) -> list[str]:
        """List the domains/zones managed by a provider.

        ``provider`` is a provider key (e.g. ``ionos``) or a target like ``ionos/*``.
        """
        key = self._provider_key(provider)
        return self._dns_provider(key, dotenv_path).list_zones()

    def status(self, target: str | None = None, dotenv_path: str | None = None) -> dict[str, object]:
        """Show provider metadata and credential status.

        With no argument, returns one entry per operational provider. With a provider
        key or full target string, returns just that provider's entry.
        """
        if target is None:
            return {key: self._provider_info(key, dotenv_path) for key in _operational_keys()}
        operational = _operational_keys()
        if target in operational:
            return self._provider_info(target, dotenv_path)
        key, _ = self._resolve_target(target)
        return self._provider_info(key, dotenv_path)

    def records(self, target: str, dotenv_path: str | None = None) -> list[Mapping[str, object]]:
        """List DNS records for the domain in ``target``, applying record-level filters."""
        key, parsed = self._resolve_target(target)
        domain = self._require_domain(parsed)
        records = self._dns_provider(key, dotenv_path).list_records(domain)
        return [record for record in records if parsed.matches_record(record)]

    def export(
        self,
        target: str,
        dotenv_path: str | None = None,
        output: str | None = None,
        overwrite: bool = False,
        skip_ns: bool = False,
        skip_types: str | None = None,
    ) -> str:
        """Export a zone as BIND text, optionally dropping NS records or given types."""
        key, parsed = self._resolve_target(target)
        domain = self._require_domain(parsed)
        zone_text = self._dns_provider(key, dotenv_path).export_zone(domain)
        origin = domain.rstrip(".") + "."
        filtered = filter_zone_text(zone_text, origin, skip_ns=skip_ns, skip_types=_split_types(skip_types))
        if output is not None:
            write_text_safely(Path(output), filtered, overwrite=overwrite)
        return filtered

    def import_zone(
        self,
        target: str,
        path: str,
        dotenv_path: str | None = None,
        proxied: bool | None = None,
    ) -> Mapping[str, object]:
        """Import BIND zone text from ``path`` into the domain in ``target``."""
        key, parsed = self._resolve_target(target)
        domain = self._require_domain(parsed)
        zone_text = Path(path).read_text(encoding="utf-8")
        return self._dns_provider(key, dotenv_path).import_zone(domain, zone_text, proxied=proxied)

    def create_zone(self, target: str, dotenv_path: str | None = None) -> Mapping[str, object]:
        """Create a hosted zone for the domain in ``target`` on its provider.

        Idempotent where the provider supports it (returns the existing zone). Providers
        that cannot create zones (the zone exists with the domain registration) raise a
        clear "not supported" error.
        """
        key, parsed = self._resolve_target(target)
        domain = self._require_domain(parsed)
        return self._dns_provider(key, dotenv_path).create_zone(domain)

    def copy(
        self,
        source: str,
        dest: str,
        dotenv_path: str | None = None,
        skip_ns: bool = False,
        skip_types: str | None = None,
        replace: bool = False,
        create: bool = True,
    ) -> Mapping[str, object]:
        """Copy a zone from ``source`` to ``dest``, optionally replacing existing records.

        ``source`` and ``dest`` are full targets. If the destination domain is ``*`` or
        omitted, it defaults to the source domain. By default the destination zone is
        created first if it does not exist and the provider supports it (useful when
        migrating a domain to a new DNS host); pass ``--create=False`` to skip that. The
        result's ``created`` entry is the created/existing zone object, or ``None`` when
        the destination provider does not support zone creation.
        """
        source_key, source_target = self._resolve_target(source)
        source_domain = self._require_domain(source_target)
        dest_key, dest_target = self._resolve_target(dest)
        dest_domain = source_domain if dest_target.domain in (None, "*") else dest_target.domain

        source_zone_text = self._dns_provider(source_key, dotenv_path).export_zone(source_domain)
        origin = source_domain.rstrip(".") + "."
        filtered = filter_zone_text(source_zone_text, origin, skip_ns=skip_ns, skip_types=_split_types(skip_types))
        exported_records = len([line for line in filtered.splitlines() if line.strip()])

        dest_provider = self._dns_provider(dest_key, dotenv_path)
        created: Mapping[str, object] | None = None
        if create:
            try:
                created = dest_provider.create_zone(dest_domain)
            except ProviderAPIError as error:
                # Some providers create the DNS zone with the domain registration; tolerate that.
                if "not supported" not in str(error).lower():
                    raise
        replaced: Mapping[str, object] | None = None
        if replace:
            replaced = dest_provider.delete_all_records(dest_domain)
        import_result = dest_provider.import_zone(dest_domain, filtered)
        return {
            "source": source_target.to_dict(),
            "dest": {**dest_target.to_dict(), "domain": dest_domain},
            "exported_records": exported_records,
            "created": created,
            "replaced": replaced,
            "import_result": import_result,
        }

    def nameservers(
        self,
        target: str,
        *new_nameservers: str,
        dotenv_path: str | None = None,
    ) -> object:
        """Read nameservers for a domain, or assign them when values are given.

        ``target`` with a wildcard domain (``provider/*``) reads nameservers for every
        domain the provider manages and returns a ``{domain: [nameserver, ...]}`` map.
        Assigning nameservers always requires a single concrete domain.
        """
        key, parsed = self._resolve_target(target)
        provider = self._registrar_provider(key, dotenv_path)
        if parsed.domain in (None, "*"):
            if new_nameservers:
                self._require_domain(parsed)  # raise the standard "single domain" error
            dns_provider = self._dns_provider(key, dotenv_path)
            return {domain: list(provider.read_nameservers(domain)) for domain in dns_provider.list_zones()}
        domain = self._require_domain(parsed)
        if not new_nameservers:
            return list(provider.read_nameservers(domain))
        return provider.assign_nameservers(domain, list(new_nameservers))

    def diff(
        self,
        a: str,
        b: str,
        origin: str | None = None,
        dotenv_path: str | None = None,
    ) -> dict[str, object]:
        """Diff two zones; each side is a local zone file path or a provider target."""
        before = self._records_from_side(a, origin, dotenv_path)
        after = self._records_from_side(b, origin, dotenv_path)
        zone_diff = diff_zone_records(before, after)
        return {"summary": zone_diff.summary(), "changes": zone_diff.to_dict()}

    def validate(self, path: str, origin: str | None = None) -> str:
        """Validate a local BIND zone file."""
        return validate_zone_file(Path(path), origin)

    def normalize(
        self,
        path: str,
        origin: str | None = None,
        output: str | None = None,
        overwrite: bool = False,
    ) -> str:
        """Return (and optionally write) a canonical normalized dump of a zone file."""
        normalized = normalize_zone_file(Path(path), origin)
        if output is not None:
            write_text_safely(Path(output), normalized, overwrite=overwrite)
        return normalized

    def doctor(
        self,
        target: str,
        fix: bool = False,
        dotenv_path: str | None = None,
        origin: str | None = None,
        json: bool = False,
        output: str | None = None,
        overwrite: bool = False,
        dmarc_email: str | None = None,
    ) -> str | dict[str, object]:
        """Diagnose a zone (provider target or local zone file) for common problems.

        With ``--fix``, apply safe automatic fixes: remove migration-artifact NS
        records pointing at a foreign provider, deduplicate semantically identical
        TXT records, and add a monitoring-only DMARC record when MX records are
        present. Other findings (missing SPF/CAA, CNAME conflicts, multiple SPF)
        are reported with copy-paste instructions.

        ``--dmarc-email=ADDR`` plugs ``ADDR`` into the suggested/applied DMARC
        record (``rua=mailto:ADDR``). When ``ADDR``'s domain differs from the
        zone, the report includes the external-destination authorization TXT
        record the receiving domain must publish so mail servers will deliver
        reports.
        """
        if looks_like_path(target):
            path = Path(target)
            report = (
                fix_zone_file(path, origin=origin, overwrite=overwrite, dmarc_email=dmarc_email)
                if fix
                else analyze_zone_file(path, origin=origin, dmarc_email=dmarc_email)
            )
        else:
            key, parsed = self._resolve_target(target)
            domain = self._require_domain(parsed)
            provider = self._dns_provider(key, dotenv_path)
            if fix:
                report = fix_provider_zone(
                    provider, domain=domain, provider_key=key, dmarc_email=dmarc_email
                )
            else:
                records = provider.list_records(domain)
                report = analyze_provider_records(
                    list(records), domain=domain, provider_key=key, dmarc_email=dmarc_email
                )
        if output is not None:
            write_text_safely(Path(output), report.format_text(), overwrite=overwrite)
        if json:
            return report.to_dict()
        return report.format_text()
