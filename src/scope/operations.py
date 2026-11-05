"""Allowlisted scanner operation registry and parameter validation.

The spec (08/11) requires a registry but does not name concrete operations; the
minimal set below is a Phase 3 decision. Nothing here executes a scanner.
"""
import re
from dataclasses import dataclass

_PORTS_RE = re.compile(r"^\d{1,5}(-\d{1,5})?(,\d{1,5}(-\d{1,5})?){0,49}$")


def _valid_ports(value) -> str | None:
    """Return an error message, or None if `value` is a valid port list/range."""
    if not isinstance(value, str) or not _PORTS_RE.match(value):
        return "must be a comma-separated list of ports or ranges, e.g. '80,443,8000-8100'"
    for item in value.split(","):
        for p in item.split("-"):
            if not 1 <= int(p) <= 65535:
                return f"port {p} is outside 1-65535"
        if "-" in item:
            lo, hi = (int(x) for x in item.split("-"))
            if lo > hi:
                return f"range '{item}' is reversed"
    return None


@dataclass(frozen=True)
class Operation:
    scanner: str
    operation: str
    description: str
    target_kinds: frozenset      # subset of {"host", "url"}
    risk_level: str
    requires_approval: bool
    parameters: dict             # name -> validator(value) -> error message | None

    @property
    def key(self) -> str:
        return f"{self.scanner}.{self.operation}"


_OPS = [
    Operation("nmap", "service_scan", "Service/version discovery on a host",
              frozenset({"host", "url"}), "Low", False, {"ports": _valid_ports}),
    Operation("zap", "passive_scan", "ZAP passive web analysis",
              frozenset({"url"}), "Low", False, {}),
    Operation("zap", "active_scan", "ZAP active web testing",
              frozenset({"url"}), "High", True, {}),
    Operation("nikto", "web_scan", "Nikto web server scan",
              frozenset({"host", "url"}), "Medium", True, {}),
]
REGISTRY: dict[tuple[str, str], Operation] = {(o.scanner, o.operation): o for o in _OPS}
SCANNERS = frozenset(s for s, _ in REGISTRY)


def list_operations() -> list[Operation]:
    return list(REGISTRY.values())


def get_operation(scanner, operation) -> Operation | None:
    return REGISTRY.get((scanner, operation)) if isinstance(scanner, str) and isinstance(operation, str) else None


def validate_parameters(op: Operation, params) -> list[str]:
    """Return a list of problems (empty if valid). Unknown parameters are rejected."""
    if params is None:
        return []
    if not isinstance(params, dict):
        return ["parameters must be a dictionary"]
    problems = []
    for name, value in params.items():
        check = op.parameters.get(name)
        if check is None:
            problems.append(f"unknown parameter '{name}' for {op.key}")
        else:
            err = check(value)
            if err:
                problems.append(f"parameter '{name}': {err}")
    return problems

