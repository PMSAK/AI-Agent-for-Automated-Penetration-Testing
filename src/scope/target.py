"""Deterministic target parsing and normalization. No network access, no shell."""
import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_PORTS = {"http": 80, "https": 443}
MAX_LENGTH = 2048

_SHELL_META = set(";|&$`<>\\'\"(){}*!^%,")
_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
_PATH = re.compile(r"^[A-Za-z0-9._~/\-]*$")


class TargetError(ValueError):
    """Target rejected. `code` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Target:
    kind: str            # "url" (scheme given) or "host" (hostname/IP, optional port)
    host: str            # lower-case hostname or compressed IP
    port: int | None     # URL targets always carry an effective port; bare hosts may be None
    scheme: str | None = None
    path: str = ""

    @property
    def normalized(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        if self.kind == "url":
            default = DEFAULT_PORTS[self.scheme] == self.port
            return f"{self.scheme}://{host}{'' if default else f':{self.port}'}{self.path}"
        return f"{host}:{self.port}" if self.port is not None else host


def _parse_port(text: str) -> int:
    if not text.isascii() or not text.isdigit():
        raise TargetError("INVALID_PORT", f"Port '{text}' is not a number")
    port = int(text)
    if not 1 <= port <= 65535:
        raise TargetError("INVALID_PORT", f"Port {port} is outside 1-65535")
    return port


def _normalize_host(host: str) -> str:
    if not host:
        raise TargetError("INVALID_HOST", "Host is empty")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if ip.is_unspecified or ip.is_multicast or str(ip) == "255.255.255.255":
            raise TargetError("INVALID_HOST", f"Address {host} is not a valid scan target")
        return str(ip)
    host = host.lower().rstrip(".") if host.endswith(".") else host.lower()
    if re.fullmatch(r"[0-9.]+", host):
        raise TargetError("INVALID_HOST", f"'{host}' is not a valid IPv4 address")
    if len(host) > 253 or not all(_LABEL.match(lbl) for lbl in host.split(".")):
        raise TargetError("INVALID_HOST", f"'{host}' is not a valid hostname")
    return host


def parse_target(raw) -> Target:
    """Parse and normalize user input into a Target, or raise TargetError."""
    if not isinstance(raw, str):
        raise TargetError("MALFORMED", "Target must be a string")
    text = raw.strip()
    if not text:
        raise TargetError("EMPTY", "Target is empty")
    if len(text) > MAX_LENGTH:
        raise TargetError("MALFORMED", "Target is too long")
    if not text.isascii() or any(c.isspace() or ord(c) < 32 or c in _SHELL_META for c in text):
        raise TargetError("ILLEGAL_CHARACTERS", "Target contains whitespace, non-ASCII or shell characters")
    if "?" in text or "#" in text:
        raise TargetError("MALFORMED", "Query strings and fragments are not allowed")

    if "://" in text:
        scheme = text.split("://", 1)[0].lower()
        if scheme not in DEFAULT_PORTS:
            raise TargetError("UNSUPPORTED_SCHEME", f"Scheme '{scheme}' is not supported (http/https only)")
        try:
            parts = urlsplit(text)
            raw_port = parts.port
        except ValueError:
            raise TargetError("INVALID_PORT", "Invalid port or malformed URL") from None
        if "@" in parts.netloc:
            raise TargetError("MALFORMED", "User info in URLs is not allowed")
        if raw_port == 0:
            raise TargetError("INVALID_PORT", "Port 0 is not valid")
        path = parts.path
        if not _PATH.match(path) or ".." in path.split("/"):
            raise TargetError("MALFORMED", "URL path contains illegal segments")
        path = path.rstrip("/")
        return Target("url", _normalize_host(parts.hostname or ""),
                      raw_port or DEFAULT_PORTS[scheme], scheme, path)

    if "/" in text:
        raise TargetError("MALFORMED", "Paths require an explicit http:// or https:// scheme")
    if text.startswith("["):  # [IPv6]:port
        end = text.find("]")
        if end == -1:
            raise TargetError("MALFORMED", "Unbalanced IPv6 brackets")
        host, rest = text[1:end], text[end + 1:]
        if rest and not rest.startswith(":"):
            raise TargetError("MALFORMED", "Unexpected text after IPv6 address")
        port = _parse_port(rest[1:]) if rest else None
        return Target("host", _normalize_host(host), port)
    try:
        ipaddress.ip_address(text)  # bare IPv6 without port
        return Target("host", _normalize_host(text), None)
    except ValueError:
        pass
    if text.count(":") > 1:
        raise TargetError("MALFORMED", "Ambiguous colon usage; wrap IPv6 in brackets")
    host, _, port_text = text.partition(":")
    port = _parse_port(port_text) if ":" in text else None
    return Target("host", _normalize_host(host), port)

