"""Deterministic scope + operation validation (spec 11 §6, plan Milestone 2).

Inputs are plain strings/dicts. Nothing in this module consults an LLM, the
network, scanner output, or a shell. The only way to reach an executor is
`execute_validated`, which calls the executor only for accepted requests.
"""
from dataclasses import dataclass, field
from typing import Callable

from src.scope.operations import REGISTRY, get_operation, validate_parameters
from src.scope.target import Target, TargetError, parse_target


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    code: str                      # "OK" or a stable rejection code
    reason: str
    target: str | None = None      # normalized target (set once the target parses)
    scanner: str | None = None
    operation: str | None = None
    parameters: dict = field(default_factory=dict)
    risk_level: str | None = None
    requires_approval: bool = False  # informational only; approvals are a later phase
    restrictions: tuple = ()

    def as_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ScopeConfig:
    """Explicit allowlist. Empty authorized list means nothing is authorized."""
    authorized: tuple = ()
    excluded: tuple = ()
    allowed_operations: frozenset | None = None   # None = every registry operation
    errors: tuple = ()                            # config problems; any error blocks everything

    @classmethod
    def from_entries(cls, authorized=(), excluded=(), allowed_operations=()) -> "ScopeConfig":
        errors = []

        def parse(entries, label):
            out = []
            for e in entries:
                try:
                    t = parse_target(e)
                    if t.path:
                        raise TargetError("MALFORMED", "scope entries cannot contain a path")
                    out.append(t)
                except TargetError as exc:
                    errors.append(f"{label} entry '{e}' rejected: {exc.message}")
            return tuple(out)

        auth, excl = parse(authorized, "authorized"), parse(excluded, "excluded")
        ops = None
        if allowed_operations:
            ops = frozenset(allowed_operations)
            for key in sorted(ops):
                if key not in {f"{s}.{o}" for s, o in REGISTRY}:
                    errors.append(f"allowed operation '{key}' is not in the registry")
        return cls(auth, excl, ops, tuple(errors))

    @classmethod
    def from_settings(cls, settings) -> "ScopeConfig":
        return cls.from_entries(settings.authorized_targets, settings.excluded_targets,
                                settings.allowed_operations)


def _covers(entry: Target, target: Target) -> bool:
    """Same host; an entry without a port covers any port, otherwise the port must match."""
    return entry.host == target.host and (entry.port is None or entry.port == target.port)


def validate_scope(target, scanner, operation, parameters, scope: ScopeConfig) -> ValidationResult:
    """Validate a requested target + operation. Never raises for bad input."""
    base = dict(scanner=scanner if isinstance(scanner, str) else None,
                operation=operation if isinstance(operation, str) else None)

    def reject(code, reason, **extra):
        return ValidationResult(False, code, reason, **{**base, **extra})

    try:
        parsed = parse_target(target)
    except TargetError as exc:
        return reject(exc.code, exc.message)
    base["target"] = parsed.normalized

    if scope.errors:
        return reject("SCOPE_INVALID", "Scope configuration is invalid or ambiguous: "
                      + "; ".join(scope.errors))

    op = get_operation(scanner, operation)
    if op is None:
        known_scanner = isinstance(scanner, str) and any(s == scanner for s, _ in REGISTRY)
        if not known_scanner:
            return reject("UNKNOWN_SCANNER", f"Scanner {scanner!r} is not supported")
        return reject("UNSUPPORTED_OPERATION",
                      f"Operation {operation!r} is not supported for scanner '{scanner}'")

    if scope.allowed_operations is not None and op.key not in scope.allowed_operations:
        return reject("OPERATION_NOT_IN_SCOPE", f"{op.key} is not permitted by the assessment scope")

    if parsed.kind not in op.target_kinds:
        return reject("TARGET_TYPE_UNSUPPORTED",
                      f"{op.key} requires a target of type: {', '.join(sorted(op.target_kinds))}")

    problems = validate_parameters(op, parameters)
    if problems:
        return reject("INVALID_PARAMETERS", "; ".join(problems))

    if any(_covers(e, parsed) for e in scope.excluded):
        return reject("TARGET_EXCLUDED", f"{parsed.normalized} is explicitly excluded from scope")
    if not any(_covers(a, parsed) for a in scope.authorized):
        return reject("TARGET_NOT_AUTHORIZED",
                      f"{parsed.normalized} is not in the authorized scope")

    return ValidationResult(
        True, "OK", "Target and operation are within the authorized scope",
        target=parsed.normalized, scanner=op.scanner, operation=op.operation,
        parameters=dict(parameters or {}), risk_level=op.risk_level,
        requires_approval=op.requires_approval,
        restrictions=tuple(f"excluded: {e.normalized}" for e in scope.excluded),
    )


def execute_validated(target, scanner, operation, parameters, scope: ScopeConfig,
                      executor: Callable[[ValidationResult], object]):
    """Single gate to scanner execution: runs `executor` only for an accepted result.

    Returns (result, executor_output). executor_output is None when rejected.
    """
    result = validate_scope(target, scanner, operation, parameters, scope)
    if not result.accepted:
        return result, None
    return result, executor(result)

