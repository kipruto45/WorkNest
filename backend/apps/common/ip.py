from __future__ import annotations

from ipaddress import ip_address


def normalize_client_ip(value: str | None) -> str | None:
    if not value:
        return None

    for candidate in str(value).split(","):
        normalized = _normalize_single_ip(candidate.strip())
        if normalized:
            return normalized
    return None


def _normalize_single_ip(value: str) -> str | None:
    if not value:
        return None

    candidate = value
    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1 : candidate.index("]")]
    elif candidate.count(":") == 1 and "." in candidate:
        # Some proxies append the remote port to IPv4 addresses.
        candidate = candidate.rsplit(":", 1)[0]

    try:
        return ip_address(candidate).compressed
    except ValueError:
        return None
