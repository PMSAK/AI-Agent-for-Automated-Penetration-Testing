"""Nmap adapter for the single registered operation `nmap.service_scan`.

Flow: validate_scope (existing gate) -> build fixed argv -> subprocess (no shell) ->
parse XML -> structured ScannerExecutionResult. Nothing runs at import time, and
nothing here authorizes targets: scope comes only from the ScopeConfig.

Defaults (Phase 4A decisions; the spec defines none): service/version detection
(`-sV --version-intensity 2`) on the nmap top 100 ports unless a validated `ports`
parameter is given; no NSE scripts, no OS detection, no host-discovery override.
"""
import logging
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.scope import ScopeConfig, TargetError, ValidationResult, execute_validated, parse_target

logger = logging.getLogger(__name__)

SCANNER = "nmap"
OPERATION = "service_scan"
DEFAULT_TIMEOUT = 300
MAX_PREVIEW = 2000

# Execution statuses follow spec 08 §8; "Rejected" = never executed (validation failed).
COMPLETED, FAILED, TIMED_OUT, REJECTED = "Completed", "Failed", "Timed Out", "Rejected"


@dataclass
class ScannerExecutionResult:
    scanner: str
    operation: str
    target: str | None
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    parsed_output: dict = field(default_factory=dict)   # normalized: hosts, services, nmap_version
    findings: list = field(default_factory=list)        # always empty: discovery is not a vulnerability
    error: str | None = None                            # safe, user-displayable message
    error_code: str | None = None
    exit_code: int | None = None
    raw_output: str = ""                                # raw XML, kept separate from parsed_output
    stderr: str = ""

    def as_dict(self, include_raw: bool = False) -> dict:
        d = dict(self.__dict__)
        if include_raw:
            return d
        d["raw_output"] = f"<{len(self.raw_output)} chars omitted>" if self.raw_output else ""
        d["stderr"] = self.stderr[:MAX_PREVIEW]
        return d


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def find_nmap(configured_path: str = "") -> str | None:
    """Configured path (from settings/.env only, never from a request) or PATH lookup."""
    return configured_path or shutil.which("nmap")


def build_args(executable: str, host: str, ports: str | None, timeout: int) -> list[str]:
    """The only place an Nmap argv is built. `host`/`ports` are already validated."""
    args = [executable, "-sV", "--version-intensity", "2", "-oX", "-", "--no-stylesheet",
            "--host-timeout", f"{max(timeout - 10, 10)}s"]
    args += ["-p", ports] if ports else ["--top-ports", "100"]
    if ":" in host:
        args.append("-6")
    return args + ["--", host]


def parse_nmap_xml(xml_text: str) -> dict:
    """Parse Nmap XML into {nmap_version, hosts, services}. Raises ValueError if invalid."""
    if not xml_text or not xml_text.strip():
        raise ValueError("empty output")
    if "<!ENTITY" in xml_text:  # stdlib parser is not entity-bomb safe; Nmap never emits these
        raise ValueError("XML entity declarations are not accepted")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"invalid XML: {exc}") from exc
    if root.tag != "nmaprun":
        raise ValueError("not an Nmap XML document")

    hosts, services = [], []
    for h in root.findall("host"):
        status = h.find("status")
        addrs = [{"addr": a.get("addr"), "type": a.get("addrtype")} for a in h.findall("address")]
        names = [n.get("name") for n in h.findall("hostnames/hostname") if n.get("name")]
        ip = next((a["addr"] for a in addrs if a["type"] in ("ipv4", "ipv6")), None)
        ports = []
        for p in h.findall("ports/port"):
            st, sv = p.find("state"), p.find("service")
            port = {
                "port": int(p.get("portid")), "protocol": p.get("protocol"),
                "state": st.get("state") if st is not None else None,
                "service": sv.get("name") if sv is not None else None,
                "product": sv.get("product") if sv is not None else None,
                "version": sv.get("version") if sv is not None else None,
                "extrainfo": sv.get("extrainfo") if sv is not None else None,
            }
            ports.append(port)
            services.append({"address": ip, **port})
        hosts.append({"status": status.get("state") if status is not None else None,
                      "addresses": addrs, "address": ip, "hostnames": names, "ports": ports})
    return {"nmap_version": root.get("version"), "hosts": hosts, "services": services}


def _text(value) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value


def _execute(vr: ValidationResult, configured_path: str, timeout: int) -> ScannerExecutionResult:
    """Run Nmap for an ACCEPTED request. Never raises."""
    res = ScannerExecutionResult(SCANNER, OPERATION, vr.target, FAILED)
    start = _now()
    res.started_at = _iso(start)

    def finish(status, code=None, message=None):
        end = _now()
        res.status, res.error_code, res.error = status, code, message
        res.completed_at, res.duration_seconds = _iso(end), round((end - start).total_seconds(), 2)
        logger.info("nmap %s target=%s status=%s code=%s", OPERATION, vr.target, status, code)
        return res

    exe = find_nmap(configured_path)
    if not exe:
        return finish(FAILED, "NMAP_NOT_FOUND", "Nmap executable was not found. Install Nmap or set NMAP_PATH.")
    target_obj = parse_target(vr.target)
    # An explicit/implied port in the target (host:port, or URL incl. default 80/443) is the
    # port to scan; it is never silently ignored or widened to the top-100 default.
    ports = vr.parameters.get("ports") or (str(target_obj.port) if target_obj.port else None)
    args = build_args(exe, target_obj.host, ports, timeout)
    logger.info("Starting nmap scan of %s (timeout %ss)", vr.target, timeout)

    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                              shell=False, stdin=subprocess.DEVNULL, check=False)
    except subprocess.TimeoutExpired as exc:
        res.raw_output, res.stderr = _text(exc.stdout), _text(exc.stderr)
        return finish(TIMED_OUT, "TIMEOUT", f"Nmap did not finish within {timeout} seconds.")
    except FileNotFoundError:
        return finish(FAILED, "NMAP_NOT_FOUND", "Nmap executable was not found. Install Nmap or set NMAP_PATH.")
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("nmap process error: %s", exc)
        return finish(FAILED, "PROCESS_ERROR", "Nmap could not be started.")

    res.raw_output, res.stderr, res.exit_code = proc.stdout or "", proc.stderr or "", proc.returncode
    if proc.returncode != 0:
        return finish(FAILED, "NONZERO_EXIT", f"Nmap exited with status {proc.returncode}.")
    if not res.raw_output.strip():
        return finish(FAILED, "EMPTY_OUTPUT", "Nmap produced no output.")
    try:
        res.parsed_output = parse_nmap_xml(res.raw_output)
    except ValueError as exc:
        return finish(FAILED, "INVALID_XML", f"Nmap output could not be parsed ({exc}).")
    except Exception:  # noqa: BLE001 - never crash the app on parser bugs
        logger.exception("Unexpected nmap parser error")
        return finish(FAILED, "PARSER_ERROR", "Unexpected error while parsing Nmap output.")
    return finish(COMPLETED)


def run_service_scan(target, parameters: dict | None, scope: ScopeConfig,
                     nmap_path: str = "", timeout: int = DEFAULT_TIMEOUT) -> ScannerExecutionResult:
    """Validate through the existing gate, then (only if accepted) run Nmap."""
    try:  # a target port and a different `ports` parameter conflict: reject, don't pick one
        t = parse_target(target)
        given = (parameters or {}).get("ports") if isinstance(parameters, dict) else None
        if t.port is not None and given not in (None, "") and given != str(t.port):
            logger.info("nmap request rejected: PORT_CONFLICT")
            return ScannerExecutionResult(
                SCANNER, OPERATION, t.normalized, REJECTED, error_code="PORT_CONFLICT",
                error=f"Target specifies port {t.port} but ports parameter is {given!r}; "
                      "remove one or make them match.")
    except TargetError:
        pass  # the gate reports the precise rejection reason
    vr, out = execute_validated(target, SCANNER, OPERATION, parameters, scope,
                                lambda v: _execute(v, nmap_path, timeout))
    if out is not None:
        return out
    logger.info("nmap request rejected: %s", vr.code)
    return ScannerExecutionResult(SCANNER, OPERATION, vr.target, REJECTED,
                                  error=vr.reason, error_code=vr.code)

