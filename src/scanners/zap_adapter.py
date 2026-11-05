"""ZAP adapter for the registered operation `zap.passive_scan` (API method).

Integration: a locally running ZAP daemon is reached through its REST API
(ZAP_API_URL, loopback only). The adapter never launches ZAP or any process.

Passive scan, as implemented here and bounded on purpose: ONE request to the
already-validated URL is proxied through ZAP (redirects NOT followed), ZAP's passive
rules analyse the response, and the resulting alerts for that origin are fetched.
No spider, no active scan, no attack payloads. `zap.active_scan` stays unimplemented
(High risk / approval-required).

Flow: validate (existing gate) -> API check -> access URL -> wait for passive queue ->
fetch alerts -> normalize. Alert URLs are data only and never extend scope.
"""
import json
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import requests

from src.scanners.nmap_adapter import (  # shared result contract (spec 08 §8)
    COMPLETED, FAILED, REJECTED, TIMED_OUT, ScannerExecutionResult, _iso, _now,
)
from src.scope import ScopeConfig, TargetError, ValidationResult, execute_validated, parse_target

logger = logging.getLogger(__name__)

SCANNER, OPERATION = "zap", "passive_scan"
PARTIAL = "Partial"
MAX_ALERTS = 500
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_SEVERITY = {"informational": "Informational", "low": "Low", "medium": "Medium", "high": "High"}
_RISKCODE = {"0": "Informational", "1": "Low", "2": "Medium", "3": "High"}
_CONFIDENCE = {"high": "High", "confirmed": "High", "medium": "Medium", "low": "Low",
               "false positive": "Low"}


@dataclass(frozen=True)
class ZapConfig:
    api_url: str = "http://127.0.0.1:8090"
    api_key: str = ""          # secret: sent only as a header, never logged or returned
    timeout: int = 300
    poll_interval: float = 1.0

    def __repr__(self) -> str:
        return f"ZapConfig(api_url={self.api_url!r}, api_key_set={bool(self.api_key)})"

    @classmethod
    def from_settings(cls, settings) -> "ZapConfig":
        return cls(settings.zap_api_url, settings.zap_api_key, settings.zap_timeout_seconds)


class _ZapError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _http_get(url, params, headers, timeout):
    """Single network primitive (patched in tests). Never follows redirects or proxies."""
    with requests.Session() as s:
        s.trust_env = False
        return s.get(url, params=params, headers=headers, timeout=timeout, allow_redirects=False)


def check_zap_availability(api_url: str = "http://127.0.0.1:8090", api_key: str = "", timeout: float = 0.2) -> dict:
    """Check if ZAP is installed locally and/or its REST API daemon is reachable."""
    common_paths = [
        r"C:\Program Files\ZAP\Zed Attack Proxy\zap.bat",
        r"C:\Program Files\ZAP\Zed Attack Proxy\ZAP.exe",
        r"C:\Program Files (x86)\ZAP\Zed Attack Proxy\zap.bat",
        "/usr/bin/zap.sh",
        "/usr/local/bin/zap.sh",
    ]
    exe = shutil.which("zap") or shutil.which("zap.bat")
    if not exe:
        for p in common_paths:
            if Path(p).is_file():
                exe = p
                break

    api_reachable, version, err = False, None, None
    try:
        headers = {"X-ZAP-API-Key": api_key} if api_key else {}
        resp = _http_get(api_url.rstrip("/") + "/JSON/core/view/version/", {}, headers, timeout)
        if resp.status_code == 200:
            api_reachable = True
            version = resp.json().get("version")
        elif resp.status_code in (401, 403):
            err = "ZAP API key authentication failed"
        else:
            err = f"ZAP API returned HTTP {resp.status_code}"
    except Exception as exc:
        err = f"Cannot connect to ZAP API: {type(exc).__name__}"

    return {
        "installed": bool(exe),
        "executable_path": exe,
        "api_reachable": api_reachable,
        "version": version,
        "error": err,
    }


def _api(cfg: ZapConfig, path: str, params: dict, deadline: float) -> dict:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise _ZapError(TIMED_OUT, "TIMEOUT", f"ZAP did not finish within {cfg.timeout} seconds.")
    headers = {"X-ZAP-API-Key": cfg.api_key} if cfg.api_key else {}
    try:
        resp = _http_get(cfg.api_url.rstrip("/") + path, params, headers, min(30, remaining))
    except requests.exceptions.ConnectTimeout:
        raise _ZapError(FAILED, "ZAP_UNAVAILABLE",
                        "Cannot connect to the ZAP API. Is the ZAP daemon running at the configured address?") from None
    except requests.Timeout:
        raise _ZapError(TIMED_OUT, "TIMEOUT", "ZAP API request timed out.") from None
    except requests.ConnectionError:
        raise _ZapError(FAILED, "ZAP_UNAVAILABLE",
                        "Cannot connect to the ZAP API. Is the ZAP daemon running at the configured address?") from None
    except requests.RequestException as exc:
        logger.error("ZAP request error: %s", type(exc).__name__)
        raise _ZapError(FAILED, "ZAP_API_ERROR", "ZAP API request failed.") from None
    if resp.status_code in (401, 403):
        raise _ZapError(FAILED, "ZAP_AUTH_FAILED", "ZAP rejected the API key (check ZAP_API_KEY).")
    if resp.status_code != 200:
        raise _ZapError(FAILED, "ZAP_API_ERROR", f"ZAP API returned HTTP {resp.status_code}.")
    if not (resp.text or "").strip():
        raise _ZapError(FAILED, "EMPTY_OUTPUT", "ZAP returned an empty response.")
    try:
        data = resp.json()
    except ValueError:
        raise _ZapError(FAILED, "INVALID_OUTPUT", "ZAP returned a non-JSON response.") from None
    if not isinstance(data, dict):
        raise _ZapError(FAILED, "INVALID_OUTPUT", "Unexpected ZAP response structure.")
    return data


def _split_references(text) -> list[str]:
    return [r for r in str(text or "").replace("<p>", "\n").replace("</p>", "\n").split()
            if r.startswith(("http://", "https://"))]


def _alert_host_and_port(url_str: str) -> tuple[str, int | None] | None:
    """Extract (lowercase host, effective port) from an alert URL. Handles query strings/fragments."""
    if not isinstance(url_str, str) or not url_str.strip():
        return None
    try:
        parts = urlsplit(url_str)
        if not parts.hostname:
            return None
        host = parts.hostname.lower().rstrip(".")
        port = parts.port or (80 if parts.scheme == "http" else 443 if parts.scheme == "https" else None)
        return host, port
    except Exception:
        return None


def normalize_alert(raw) -> dict | None:
    """ZAP alert -> finding dict (spec 09 field names). None if malformed. Nothing is invented."""
    if not isinstance(raw, dict):
        return None
    title = raw.get("alert") or raw.get("name")
    if not isinstance(title, str) or not title.strip():
        return None
    risk = str(raw.get("risk") or "").strip()
    severity = _SEVERITY.get(risk.lower()) or _RISKCODE.get(str(raw.get("riskcode")), "Unknown")
    conf = str(raw.get("confidence") or "").strip()
    cwe = str(raw.get("cweid") or "").strip()
    solution = (raw.get("solution") or "").strip() or None
    return {
        "scanner": "zap", "record_type": "Scanner Alert",
        "scanner_finding_id": str(raw.get("pluginId") or raw.get("alertRef") or "") or None,
        "title": title.strip(), "description": raw.get("description") or "",
        "affected_url": raw.get("url") or None, "http_method": raw.get("method") or None,
        "parameter": raw.get("param") or None, "evidence": raw.get("evidence") or None,
        "severity": severity, "original_severity": risk or None, "severity_source": "Scanner",
        "confidence": _CONFIDENCE.get(conf.lower(), "Unknown"), "original_confidence": conf or None,
        "verification_status": "Unverified",       # a scanner alert is never auto-confirmed
        "cwe_id": int(cwe) if cwe.isdigit() and int(cwe) > 0 else None,
        "cve_id": None, "cvss_score": None,        # ZAP does not supply these; never invented
        "remediation": solution, "remediation_source": "Scanner" if solution else None,
        "references": _split_references(raw.get("reference")),
        "raw": raw,                                 # original alert preserved (spec 08 §6.5)
    }


def parse_alerts(payload, target) -> tuple[list[dict], dict]:
    """Return (findings, stats). Raises ValueError if the payload is not an alerts document.

    Alerts whose URL is not on the scanned host:port are dropped (counted, never trusted).
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("alerts"), list):
        raise ValueError("missing 'alerts' list")
    findings, malformed, off_target = [], 0, 0
    for raw in payload["alerts"]:
        f = normalize_alert(raw)
        if f is None:
            malformed += 1
            continue
        alert_hp = _alert_host_and_port(f["affected_url"] or "")
        same = alert_hp is not None and alert_hp == (target.host, target.port)
        if not same:
            off_target += 1
            continue
        findings.append(f)
    return findings, {"alerts_received": len(payload["alerts"]), "malformed_alerts": malformed,
                      "off_target_alerts_dropped": off_target}


def _execute(vr: ValidationResult, cfg: ZapConfig) -> ScannerExecutionResult:
    """Run the passive scan for an ACCEPTED request. Never raises."""
    res = ScannerExecutionResult(SCANNER, OPERATION, vr.target, FAILED)
    start = _now()
    res.started_at = _iso(start)

    def finish(status, code=None, message=None):
        end = _now()
        res.status, res.error_code, res.error = status, code, message
        res.completed_at, res.duration_seconds = _iso(end), round((end - start).total_seconds(), 2)
        logger.info("zap %s target=%s status=%s code=%s", OPERATION, vr.target, status, code)
        return res

    api = urlsplit(cfg.api_url)
    if api.scheme != "http" or (api.hostname or "") not in LOCAL_HOSTS:
        return finish(FAILED, "ZAP_CONFIG_INVALID", "ZAP_API_URL must be an http loopback address.")

    target = parse_target(vr.target)
    deadline = time.monotonic() + cfg.timeout
    try:
        version = _api(cfg, "/JSON/core/view/version/", {}, deadline).get("version")
        _api(cfg, "/JSON/core/action/accessUrl/", {"url": vr.target, "followRedirects": "false"}, deadline)
        while True:  # wait for ZAP's passive-scan queue to drain
            queue = _api(cfg, "/JSON/pscan/view/recordsToScan/", {}, deadline).get("recordsToScan")
            try:
                if int(queue) == 0:
                    break
            except (TypeError, ValueError):
                raise _ZapError(FAILED, "INVALID_OUTPUT", "Unexpected passive-scan status from ZAP.") from None
            if time.monotonic() + cfg.poll_interval >= deadline:
                raise _ZapError(TIMED_OUT, "TIMEOUT", f"ZAP did not finish within {cfg.timeout} seconds.")
            time.sleep(cfg.poll_interval)
        base = f"{target.scheme}://{vr.target.split('://', 1)[1].split('/', 1)[0]}"
        payload = _api(cfg, "/JSON/core/view/alerts/",
                       {"baseurl": base, "start": 0, "count": MAX_ALERTS}, deadline)
        res.raw_output = json.dumps(payload)
    except _ZapError as exc:
        return finish(exc.status, exc.code, exc.message)
    except Exception:  # noqa: BLE001 - never crash the app
        logger.exception("Unexpected ZAP adapter error")
        return finish(FAILED, "ADAPTER_ERROR", "Unexpected error while running the ZAP scan.")

    try:
        res.findings, stats = parse_alerts(payload, target)
    except ValueError as exc:
        return finish(FAILED, "INVALID_OUTPUT", f"ZAP alerts could not be parsed ({exc}).")
    res.parsed_output = {"zap_version": version, "scan_type": "passive (single request, no spider)",
                         **stats}
    if stats["malformed_alerts"] or stats["alerts_received"] >= MAX_ALERTS:
        return finish(PARTIAL, "PARTIAL_RESULTS", "Some alerts were malformed or the alert limit was reached.")
    return finish(COMPLETED)


def run_passive_scan(target, parameters: dict | None, scope: ScopeConfig,
                     cfg: ZapConfig | None = None) -> ScannerExecutionResult:
    """Validate through the existing gate, then (only if accepted) run the ZAP passive scan."""
    cfg = cfg or ZapConfig()
    vr, out = execute_validated(target, SCANNER, OPERATION, parameters, scope,
                                lambda v: _execute(v, cfg))
    if out is not None:
        return out
    logger.info("zap request rejected: %s", vr.code)
    return ScannerExecutionResult(SCANNER, OPERATION, vr.target, REJECTED,
                                  error=vr.reason, error_code=vr.code)
