from types import SimpleNamespace

import pytest
import requests

from src.scanners import zap_adapter as za
from src.scanners.zap_adapter import ZapConfig, check_zap_availability, normalize_alert, parse_alerts, run_passive_scan
from src.scope import ScopeConfig, validate_scope

SCOPE = ScopeConfig.from_entries(
    authorized=["http://127.0.0.1:8080", "http://lab.example.test", "http://127.0.0.1:3000"],
    excluded=["http://blocked.lab.example.test"],
)

SAMPLE_ALERTS = [
    {
        "alert": "Cross Site Scripting (Reflected)",
        "name": "Cross Site Scripting (Reflected)",
        "risk": "High",
        "riskcode": "3",
        "confidence": "Medium",
        "url": "http://127.0.0.1:8080/search?q=test",
        "method": "GET",
        "param": "q",
        "evidence": "<script>alert(1)</script>",
        "cweid": "79",
        "pluginId": "40012",
        "description": "Reflected XSS vulnerability in query parameter.",
        "solution": "Sanitize and encode all untrusted input.",
        "reference": "<p>https://owasp.org/www-community/attacks/xss/</p>",
    },
    {
        "alert": "Missing Anti-clickjacking Header",
        "risk": "Medium",
        "riskcode": "2",
        "confidence": "High",
        "url": "http://127.0.0.1:8080/login",
        "method": "GET",
        "param": "",
        "evidence": "",
        "cweid": "1021",
        "pluginId": "10020",
        "description": "X-Frame-Options header is not set.",
        "solution": "Add X-Frame-Options: DENY or SAMEORIGIN.",
        "reference": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options",
    },
]


class FakeResponse:
    def __init__(self, data=None, text="", status_code=200):
        self._data = data
        self.text = text if text else ("" if data is None else "json")
        self.status_code = status_code

    def json(self):
        if self._data is not None:
            return self._data
        if self.text == "":
            raise ValueError("empty")
        import json
        return json.loads(self.text)


class FakeSessionGet:
    def __init__(self, responses=None, raises=None):
        self.responses = responses or {}
        self.raises = raises
        self.calls = []

    def __call__(self, url, params=None, headers=None, timeout=None, allow_redirects=False):
        self.calls.append({
            "url": url,
            "params": params,
            "headers": headers,
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        })
        if self.raises:
            raise self.raises

        for path_pattern, resp in self.responses.items():
            if path_pattern in url:
                if isinstance(resp, Exception):
                    raise resp
                if callable(resp):
                    return resp(url, params, headers)
                return resp

        return FakeResponse({"result": "OK"}, status_code=200)


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """Guard fixture: ensure real network calls are blocked by default."""
    def boom(*a, **k):
        raise AssertionError("Real network requests are forbidden in unit tests")
    monkeypatch.setattr(za, "_http_get", boom)


def patch_zap_api(monkeypatch, alerts=None, queue_states=None, version="2.17.0", raises=None):
    alerts = alerts if alerts is not None else SAMPLE_ALERTS
    queue_iter = iter(queue_states or ["0"])

    def queue_responder(url, params, headers):
        val = next(queue_iter, "0")
        return FakeResponse({"recordsToScan": str(val)})

    responses = {
        "/JSON/core/view/version/": FakeResponse({"version": version}),
        "/JSON/core/action/accessUrl/": FakeResponse({"result": "OK"}),
        "/JSON/pscan/view/recordsToScan/": queue_responder,
        "/JSON/core/view/alerts/": FakeResponse({"alerts": alerts}),
    }
    fake = FakeSessionGet(responses=responses, raises=raises)
    monkeypatch.setattr(za, "_http_get", fake)
    return fake


# ---- 1. Config & Validation Tests ----

def test_zap_config_hides_api_key():
    cfg = ZapConfig(api_key="super_secret_key_123")
    assert "super_secret_key_123" not in repr(cfg)
    assert "api_key_set=True" in repr(cfg)


def test_zap_config_from_settings():
    settings = SimpleNamespace(
        zap_api_url="http://127.0.0.1:8090",
        zap_api_key="key",
        zap_timeout_seconds=120,
    )
    cfg = ZapConfig.from_settings(settings)
    assert cfg.api_url == "http://127.0.0.1:8090"
    assert cfg.api_key == "key"
    assert cfg.timeout == 120


def test_non_loopback_api_url_rejected():
    cfg = ZapConfig(api_url="http://192.168.1.100:8090")
    r = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE, cfg)
    assert r.status == "Failed"
    assert r.error_code == "ZAP_CONFIG_INVALID"
    assert "loopback" in r.error


def test_https_api_url_rejected():
    cfg = ZapConfig(api_url="https://127.0.0.1:8090")
    r = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE, cfg)
    assert r.status == "Failed"
    assert r.error_code == "ZAP_CONFIG_INVALID"


# ---- 2. Successful Execution & Parsing Tests ----

def test_successful_passive_scan_execution(monkeypatch):
    fake = patch_zap_api(monkeypatch)
    cfg = ZapConfig(api_key="test_key", poll_interval=0.01)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE, cfg)

    assert res.status == "Completed"
    assert res.scanner == "zap"
    assert res.operation == "passive_scan"
    assert res.target == "http://127.0.0.1:8080"
    assert res.error is None
    assert res.started_at is not None
    assert res.completed_at is not None
    assert res.duration_seconds is not None

    # Check findings normalized
    assert len(res.findings) == 2
    f1 = res.findings[0]
    assert f1["scanner"] == "zap"
    assert f1["title"] == "Cross Site Scripting (Reflected)"
    assert f1["severity"] == "High"
    assert f1["confidence"] == "Medium"
    assert f1["verification_status"] == "Unverified"
    assert f1["cwe_id"] == 79
    assert f1["cve_id"] is None
    assert f1["cvss_score"] is None
    assert f1["remediation_source"] == "Scanner"
    assert "https://owasp.org/www-community/attacks/xss/" in f1["references"]

    f2 = res.findings[1]
    assert f2["title"] == "Missing Anti-clickjacking Header"
    assert f2["severity"] == "Medium"
    assert f2["confidence"] == "High"
    assert f2["cwe_id"] == 1021

    # Check parsed_output stats
    assert res.parsed_output["zap_version"] == "2.17.0"
    assert res.parsed_output["alerts_received"] == 2
    assert res.parsed_output["malformed_alerts"] == 0
    assert res.parsed_output["off_target_alerts_dropped"] == 0

    # Raw output preserved
    assert "Cross Site Scripting" in res.raw_output
    assert "<" in res.as_dict()["raw_output"]  # omitted in UI dict
    assert "Cross Site Scripting" in res.as_dict(include_raw=True)["raw_output"]

    # Check headers sent
    auth_headers = [c["headers"] for c in fake.calls if c["headers"]]
    assert all(h.get("X-ZAP-API-Key") == "test_key" for h in auth_headers)


def test_passive_scan_queue_polling(monkeypatch):
    patch_zap_api(monkeypatch, queue_states=["3", "1", "0"])
    cfg = ZapConfig(poll_interval=0.01)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE, cfg)
    assert res.status == "Completed"


# ---- 3. Failure & Error Handling Tests ----

def test_zap_unavailable_connection_error(monkeypatch):
    patch_zap_api(monkeypatch, raises=requests.ConnectionError("Connection refused"))
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE)
    assert res.status == "Failed"
    assert res.error_code == "ZAP_UNAVAILABLE"
    assert "Cannot connect to the ZAP API" in res.error


def test_zap_connect_timeout(monkeypatch):
    patch_zap_api(monkeypatch, raises=requests.exceptions.ConnectTimeout("Connect timed out"))
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE)
    assert res.status == "Failed"
    assert res.error_code == "ZAP_UNAVAILABLE"


def test_zap_auth_failed_401(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse(status_code=401)})
    monkeypatch.setattr(za, "_http_get", fake)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE, ZapConfig(api_key="bad_key"))
    assert res.status == "Failed"
    assert res.error_code == "ZAP_AUTH_FAILED"
    assert "bad_key" not in res.error


def test_zap_auth_failed_403(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse(status_code=403)})
    monkeypatch.setattr(za, "_http_get", fake)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE)
    assert res.status == "Failed"
    assert res.error_code == "ZAP_AUTH_FAILED"


def test_zap_api_500_error(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse(status_code=500)})
    monkeypatch.setattr(za, "_http_get", fake)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE)
    assert res.status == "Failed"
    assert res.error_code == "ZAP_API_ERROR"
    assert "HTTP 500" in res.error


def test_zap_timeout_waiting_for_queue(monkeypatch):
    # Queue never reaches 0
    patch_zap_api(monkeypatch, queue_states=["5", "5", "5", "5"])
    cfg = ZapConfig(timeout=1, poll_interval=0.5)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE, cfg)
    assert res.status == "Timed Out"
    assert res.error_code == "TIMEOUT"


def test_zap_empty_response(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse(text="  ")})
    monkeypatch.setattr(za, "_http_get", fake)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE)
    assert res.status == "Failed"
    assert res.error_code == "EMPTY_OUTPUT"


def test_zap_non_json_response(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse(text="<html>Bad Gateway</html>")})
    monkeypatch.setattr(za, "_http_get", fake)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE)
    assert res.status == "Failed"
    assert res.error_code == "INVALID_OUTPUT"


def test_zap_malformed_alerts_payload(monkeypatch):
    fake = FakeSessionGet(responses={
        "/JSON/core/view/version/": FakeResponse({"version": "2.17.0"}),
        "/JSON/core/action/accessUrl/": FakeResponse({"result": "OK"}),
        "/JSON/pscan/view/recordsToScan/": FakeResponse({"recordsToScan": "0"}),
        "/JSON/core/view/alerts/": FakeResponse({"not_alerts": "missing"}),
    })
    monkeypatch.setattr(za, "_http_get", fake)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE, ZapConfig(poll_interval=0.01))
    assert res.status == "Failed"
    assert res.error_code == "INVALID_OUTPUT"


def test_malformed_alert_item_yields_partial_results(monkeypatch):
    alerts = [
        {"alert": "Valid Alert", "risk": "Low", "url": "http://127.0.0.1:8080/"},
        {"alert": "", "risk": "Low", "url": "http://127.0.0.1:8080/"},  # malformed (no title)
    ]
    patch_zap_api(monkeypatch, alerts=alerts)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE, ZapConfig(poll_interval=0.01))
    assert res.status == "Partial"
    assert res.error_code == "PARTIAL_RESULTS"
    assert len(res.findings) == 1
    assert res.parsed_output["malformed_alerts"] == 1


def test_off_target_alerts_dropped_and_cannot_expand_scope(monkeypatch):
    alerts = [
        {"alert": "On Target Alert", "risk": "Low", "url": "http://127.0.0.1:8080/home"},
        {"alert": "Off Target Alert 1", "risk": "High", "url": "http://evil.com/leak"},
        {"alert": "Off Target Alert 2", "risk": "High", "url": "http://127.0.0.1:9090/other"},
    ]
    patch_zap_api(monkeypatch, alerts=alerts)
    res = run_passive_scan("http://127.0.0.1:8080", {}, SCOPE, ZapConfig(poll_interval=0.01))
    assert res.status == "Completed"
    assert len(res.findings) == 1
    assert res.findings[0]["title"] == "On Target Alert"
    assert res.parsed_output["off_target_alerts_dropped"] == 2

    # Verify scope validator still blocks the reported off-target targets
    assert validate_scope("http://evil.com/leak", "zap", "passive_scan", {}, SCOPE).code == "TARGET_NOT_AUTHORIZED"
    assert validate_scope("http://127.0.0.1:9090", "zap", "passive_scan", {}, SCOPE).code == "TARGET_NOT_AUTHORIZED"


def test_missing_optional_fields_in_alerts():
    raw = {"alert": "Minimal Alert", "url": "http://127.0.0.1:8080"}
    f = normalize_alert(raw)
    assert f is not None
    assert f["title"] == "Minimal Alert"
    assert f["severity"] == "Unknown"
    assert f["confidence"] == "Unknown"
    assert f["cwe_id"] is None
    assert f["remediation"] is None
    assert f["references"] == []


# ---- 4. Security & Gate Enforcement Tests ----

@pytest.mark.parametrize("target,params,code", [
    ("http://unauthorized.example.com", {}, "TARGET_NOT_AUTHORIZED"),
    ("http://blocked.lab.example.test", {}, "TARGET_EXCLUDED"),
    ("127.0.0.1", {}, "TARGET_TYPE_UNSUPPORTED"),  # host target rejected (URL required)
    ("http://127.0.0.1:8080; id", {}, "ILLEGAL_CHARACTERS"),
    ("ftp://127.0.0.1:8080", {}, "UNSUPPORTED_SCHEME"),
    ("http://127.0.0.1:8080", {"flags": "-sV"}, "INVALID_PARAMETERS"),
    ("http://127.0.0.1:8080", {"spider": True}, "INVALID_PARAMETERS"),
])
def test_security_rejections_never_call_zap_api(monkeypatch, target, params, code):
    # If the network primitive is called, no_real_network fixture will raise AssertionError
    res = run_passive_scan(target, params, SCOPE)
    assert res.status == "Rejected"
    assert res.error_code == code


def test_unsupported_operation_rejected():
    res = validate_scope("http://127.0.0.1:8080", "zap", "unknown_op", {}, SCOPE)
    assert not res.accepted
    assert res.code == "UNSUPPORTED_OPERATION"


def test_active_scan_requires_approval():
    res = validate_scope("http://127.0.0.1:8080", "zap", "active_scan", {}, SCOPE)
    assert res.accepted
    assert res.requires_approval is True
    assert res.risk_level == "High"


# ---- 5. Availability Check Tests ----

def test_check_zap_availability_reachable(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse({"version": "2.17.0"})})
    monkeypatch.setattr(za, "_http_get", fake)
    status = check_zap_availability("http://127.0.0.1:8090", api_key="k")
    assert status["api_reachable"] is True
    assert status["daemon_listening"] is True
    assert status["auth_failed"] is False
    assert status["version"] == "2.17.0"
    assert status["error"] is None


def test_check_zap_availability_uppercase_version(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse({"Version": "2.17.0"})})
    monkeypatch.setattr(za, "_http_get", fake)
    status = check_zap_availability("http://127.0.0.1:8090", api_key="k")
    assert status["api_reachable"] is True
    assert status["daemon_listening"] is True
    assert status["auth_failed"] is False
    assert status["version"] == "2.17.0"
    assert status["error"] is None


def test_check_zap_availability_unreachable(monkeypatch):
    fake = FakeSessionGet(raises=requests.ConnectionError("Refused"))
    monkeypatch.setattr(za, "_http_get", fake)
    status = check_zap_availability("http://127.0.0.1:8090")
    assert status["api_reachable"] is False
    assert status["daemon_listening"] is False
    assert status["auth_failed"] is False
    assert status["version"] is None
    assert "Cannot connect" in status["error"]


def test_check_zap_availability_auth_failed_http_401(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse(text="Unauthorized", status_code=401)})
    monkeypatch.setattr(za, "_http_get", fake)
    status = check_zap_availability("http://127.0.0.1:8090", api_key="wrong_key")
    assert status["api_reachable"] is False
    assert status["daemon_listening"] is True
    assert status["auth_failed"] is True
    assert status["version"] is None
    assert "authentication failed" in status["error"].lower()


def test_check_zap_availability_auth_failed_http_403(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse(text="Forbidden", status_code=403)})
    monkeypatch.setattr(za, "_http_get", fake)
    status = check_zap_availability("http://127.0.0.1:8090", api_key="wrong_key")
    assert status["api_reachable"] is False
    assert status["daemon_listening"] is True
    assert status["auth_failed"] is True
    assert status["version"] is None
    assert "authentication failed" in status["error"].lower()


def test_check_zap_availability_auth_failed_remote_disconnected(monkeypatch):
    # Simulates ZAP terminating connection on missing or bad API key
    fake = FakeSessionGet(raises=requests.ConnectionError("Connection aborted: RemoteDisconnected"))
    monkeypatch.setattr(za, "_http_get", fake)
    status = check_zap_availability("http://127.0.0.1:8090")
    assert status["api_reachable"] is False
    assert status["daemon_listening"] is True
    assert status["auth_failed"] is True
    assert status["version"] is None
    assert "API key missing or rejected" in status["error"]


def test_check_zap_availability_unexpected_response_shape(monkeypatch):
    fake = FakeSessionGet(responses={"/JSON/core/view/version/": FakeResponse(data={"other_key": 123})})
    monkeypatch.setattr(za, "_http_get", fake)
    status = check_zap_availability("http://127.0.0.1:8090", api_key="k")
    assert status["api_reachable"] is False
    assert status["daemon_listening"] is True
    assert status["auth_failed"] is False
    assert status["version"] is None
    assert "Unexpected ZAP API response format" in status["error"]


def test_check_zap_availability_not_installed(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr("pathlib.Path.is_file", lambda _: False)
    fake = FakeSessionGet(raises=requests.ConnectionError("Refused"))
    monkeypatch.setattr(za, "_http_get", fake)
    status = check_zap_availability("http://127.0.0.1:8090")
    assert status["installed"] is False
    assert status["executable_path"] is None
    assert status["api_reachable"] is False

