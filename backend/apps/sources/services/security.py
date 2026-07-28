from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from apps.sources.models import Source


class UnsafeURL(ValueError):
    """Raised when a collection URL violates the source security policy."""


def normalized_domain(value: str) -> str:
    return value.strip().lower().rstrip(".")


def allowed_domains_for(source: Source) -> set[str]:
    domains = {normalized_domain(source.official_domain)}
    domains.update(normalized_domain(item) for item in source.allowed_domains if str(item).strip())
    return domains


def hostname_matches(hostname: str, allowed_domain: str) -> bool:
    return hostname == allowed_domain or hostname.endswith(f".{allowed_domain}")


def _reject_non_public_addresses(hostname: str) -> None:
    try:
        records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURL(f"Could not resolve hostname: {hostname}") from exc

    addresses = {record[4][0] for record in records}
    if not addresses:
        raise UnsafeURL(f"Hostname returned no addresses: {hostname}")

    for raw_address in addresses:
        address = ipaddress.ip_address(raw_address)
        if not address.is_global:
            raise UnsafeURL(f"Collection target resolves to a non-public address: {raw_address}")


def validate_collection_url(url: str, source: Source) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURL("Only HTTP and HTTPS URLs are supported.")
    if parsed.username or parsed.password:
        raise UnsafeURL("Credentials are not allowed in collection URLs.")
    if parsed.port not in {None, 80, 443}:
        raise UnsafeURL("Non-standard URL ports are not allowed.")

    hostname = normalized_domain(parsed.hostname or "")
    if not hostname:
        raise UnsafeURL("The URL does not contain a hostname.")

    allowed = allowed_domains_for(source)
    if not any(hostname_matches(hostname, domain) for domain in allowed):
        raise UnsafeURL(
            f"Hostname {hostname!r} is outside the source allow-list: {sorted(allowed)}"
        )

    _reject_non_public_addresses(hostname)
    return url
