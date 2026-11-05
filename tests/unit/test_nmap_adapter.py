import subprocess
from types import SimpleNamespace

import pytest

from src.scanners import nmap_adapter as na
from src.scanners import run_service_scan
from src.scope import ScopeConfig, validate_scope

SCOPE = ScopeConfig.from_entries(authorized=["127.0.0.1", "lab.example.test", "::1"],
                                 excluded=["blocked.lab.example.test"])

XML = """<?xml version="1.0"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" version="7.95" start="1700000000">
<host><status state="up" reason="syn-ack"/>
<address addr="127.0.0.1" addrtype="ipv4"/>
<hostnames><hostname name="localhost" type="PTR"/></hostnames>
<ports>
<port protocol="tcp" portid="80"><state state="open"/><service name="http" product="nginx" version="1.25.0" extrainfo="Ubuntu"/></port>
<port protocol="tcp" portid="22"><state state="closed"/><service name="ssh"/></port>
</ports></host>
<host><status state="up"/><address addr="10.9.9.9" addrtype="ipv4"/></host>
</nmaprun>"""


class FakeRun:
    """Records calls instead of running anything."""
    def __init__(self, stdout=XML, stderr="", returncode=0, raises=None):
        self.calls, self.kw = [], []
        self.result = SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)
        self.raises = raises

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        self.kw.append(kwargs)
        if self.raises:
            raise self.raises
        return self.result


@pytest.fixture(autouse=True)
def no_real_process(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("real subprocess must never run in tests")
    monkeypatch.setattr(na.subprocess, "run", boom)
    monkeypatch.setattr(na.shutil, "which", lambda n: "C:/fake/nmap.exe")


def patch_run(monkeypatch, **kw):
    fake = FakeRun(**kw)
    monkeypatch.setattr(na.subprocess, "run", fake)
    return fake


def scan(target="127.0.0.1", params=None, scope=SCOPE, **kw):
    return run_service_scan(target, params, scope, **kw)


# ---- adapter behaviour
def test_successful_scan_and_argument_list(monkeypatch):
    fake = patch_run(monkeypatch)
    r = scan(params={"ports": "22,80"}, timeout=120)
    assert r.status == "Completed" and r.error is None and r.findings == []
    assert r.scanner == "nmap" and r.operation == "service_scan" and r.target == "127.0.0.1"
    assert r.started_at and r.completed_at and r.duration_seconds is not None
    args = fake.calls[0]
    assert isinstance(args, list) and args[0] == "C:/fake/nmap.exe"
    assert args[-2:] == ["--", "127.0.0.1"]
    assert args[args.index("-p") + 1] == "22,80" and "--top-ports" not in args
    assert "-sV" in args and "-oX" in args and "-" in args
    assert not any("script" in a or a == "-A" or a == "-sC" for a in args)
    kw = fake.kw[0]
    assert kw["shell"] is False and kw["timeout"] == 120 and kw["capture_output"] is True


def test_default_ports_are_conservative(monkeypatch):
    fake = patch_run(monkeypatch)
    scan()
    args = fake.calls[0]
    assert args[args.index("--top-ports") + 1] == "100" and "-p" not in args


def test_url_target_passes_only_host_and_ipv6_flag(monkeypatch):
    fake = patch_run(monkeypatch)
    scan("http://127.0.0.1:8080")
    assert fake.calls[0][-1] == "127.0.0.1"
    fake = patch_run(monkeypatch)
    scan("::1")
    assert "-6" in fake.calls[0] and fake.calls[0][-1] == "::1"


def test_xml_parsing_hosts_and_services(monkeypatch):
    patch_run(monkeypatch)
    out = scan().parsed_output
    assert out["nmap_version"] == "7.95"
    h = out["hosts"][0]
    assert h["status"] == "up" and h["address"] == "127.0.0.1" and h["hostnames"] == ["localhost"]
    web = next(s for s in out["services"] if s["port"] == 80)
    assert (web["protocol"], web["state"], web["service"], web["product"], web["version"]) == \
        ("tcp", "open", "http", "nginx", "1.25.0")
    ssh = next(s for s in out["services"] if s["port"] == 22)
    assert ssh["state"] == "closed" and ssh["version"] is None and ssh["product"] is None  # not invented


def test_raw_output_kept_separate_and_omitted_in_ui_dict(monkeypatch):
    patch_run(monkeypatch)
    r = scan()
    assert "<nmaprun" in r.raw_output and "raw_output" not in r.parsed_output
    assert "<nmaprun" not in r.as_dict()["raw_output"]
    assert "<nmaprun" in r.as_dict(include_raw=True)["raw_output"]


def test_empty_output(monkeypatch):
    patch_run(monkeypatch, stdout="  ")
    r = scan()
    assert r.status == "Failed" and r.error_code == "EMPTY_OUTPUT"


@pytest.mark.parametrize("bad", ["<nmaprun><host>", "not xml", "<other/>",
                                 '<!DOCTYPE x [<!ENTITY a "b">]><nmaprun/>'])
def test_invalid_xml(monkeypatch, bad):
    patch_run(monkeypatch, stdout=bad)
    r = scan()
    assert r.status == "Failed" and r.error_code == "INVALID_XML" and r.parsed_output == {}


def test_missing_executable(monkeypatch):
    monkeypatch.setattr(na.shutil, "which", lambda n: None)
    r = scan()  # subprocess.run is the boom stub: reaching it would fail the test
    assert r.status == "Failed" and r.error_code == "NMAP_NOT_FOUND"


def test_executable_vanishes_at_launch(monkeypatch):
    patch_run(monkeypatch, raises=FileNotFoundError("nmap"))
    assert scan().error_code == "NMAP_NOT_FOUND"


def test_timeout_preserves_partial_output(monkeypatch):
    patch_run(monkeypatch, raises=subprocess.TimeoutExpired("nmap", 5, output=b"<nmaprun>", stderr=b"slow"))
    r = scan(timeout=5)
    assert r.status == "Timed Out" and r.error_code == "TIMEOUT"
    assert r.raw_output == "<nmaprun>" and r.stderr == "slow"


def test_nonzero_exit(monkeypatch):
    patch_run(monkeypatch, stdout="", stderr="Failed to resolve", returncode=1)
    r = scan()
    assert r.status == "Failed" and r.error_code == "NONZERO_EXIT" and r.exit_code == 1
    assert r.stderr == "Failed to resolve"


def test_process_failure_has_safe_message(monkeypatch):
    patch_run(monkeypatch, raises=PermissionError("C:/secret/path denied"))
    r = scan()
    assert r.status == "Failed" and r.error_code == "PROCESS_ERROR"
    assert "secret" not in r.error and "Traceback" not in r.error


def test_configured_path_used_not_request(monkeypatch):
    fake = patch_run(monkeypatch)
    scan(nmap_path="C:/tools/nmap.exe")
    assert fake.calls[0][0] == "C:/tools/nmap.exe"
    r = scan(params={"executable": "C:/evil.exe"})
    assert r.status == "Rejected" and len(fake.calls) == 1


# ---- security: rejected requests never reach subprocess
@pytest.mark.parametrize("target,scope,params,code", [
    ("evil.example.com", SCOPE, None, "TARGET_NOT_AUTHORIZED"),
    ("blocked.lab.example.test", SCOPE, None, "TARGET_EXCLUDED"),
    ("127.0.0.1; rm -rf /", SCOPE, None, "ILLEGAL_CHARACTERS"),
    ("", SCOPE, None, "EMPTY"),
    ("ftp://127.0.0.1", SCOPE, None, "UNSUPPORTED_SCHEME"),
    ("127.0.0.1", SCOPE, {"ports": "80; id"}, "INVALID_PARAMETERS"),
    ("127.0.0.1", SCOPE, {"ports": "1-100000"}, "INVALID_PARAMETERS"),
    ("127.0.0.1", SCOPE, {"flags": "-sV --script vuln"}, "INVALID_PARAMETERS"),
    ("127.0.0.1", SCOPE, {"scripts": "default"}, "INVALID_PARAMETERS"),
    ("127.0.0.1", ScopeConfig(), None, "TARGET_NOT_AUTHORIZED"),
    ("127.0.0.1", ScopeConfig.from_entries(authorized=["10.0.0.0/8"]), None, "SCOPE_INVALID"),
    ("127.0.0.1", ScopeConfig.from_entries(authorized=["127.0.0.1"],
                                           allowed_operations=["zap.passive_scan"]),
     None, "OPERATION_NOT_IN_SCOPE"),
])
def test_rejections_never_execute(target, scope, params, code):
    # autouse fixture makes any subprocess.run call raise AssertionError
    r = scan(target, params, scope)
    assert r.status == "Rejected" and r.error_code == code
    assert r.started_at is None and r.parsed_output == {} and r.error


def test_argument_injection_is_impossible(monkeypatch):
    fake = patch_run(monkeypatch)
    for evil in ("-oN /tmp/x", "--script=vuln", "-sV 127.0.0.1", "127.0.0.1 -A"):
        assert scan(evil).status == "Rejected"
    assert fake.calls == []
    assert scan("lab.example.test").status == "Completed"
    assert fake.calls[0][-2:] == ["--", "lab.example.test"]


def test_invalid_operation_rejected_by_gate_before_execution():
    # The adapter has no operation parameter; the registry gate rejects anything else.
    assert validate_scope("127.0.0.1", "nmap", "vuln_scan", {}, SCOPE).code == "UNSUPPORTED_OPERATION"


def test_nmap_output_cannot_authorize_new_targets(monkeypatch):
    fake = patch_run(monkeypatch)
    r = scan()
    assert any(h["address"] == "10.9.9.9" for h in r.parsed_output["hosts"])  # reported, not trusted
    assert validate_scope("10.9.9.9", "nmap", "service_scan", {}, SCOPE).code == "TARGET_NOT_AUTHORIZED"
    assert scan("10.9.9.9").status == "Rejected" and len(fake.calls) == 1


def test_adapter_runs_only_after_gate_accepts(monkeypatch):
    order = []
    real_validate = na.execute_validated

    def spy(*a, **k):
        order.append("gate")
        return real_validate(*a, **k)
    monkeypatch.setattr(na, "execute_validated", spy)
    fake = patch_run(monkeypatch)
    monkeypatch.setattr(fake, "raises", None)
    orig = fake.__call__
    scan("evil.example.com")
    assert order == ["gate"] and fake.calls == []
    scan("127.0.0.1")
    assert order == ["gate", "gate"] and len(fake.calls) == 1


def test_import_and_ui_do_not_scan_on_load(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    # subprocess.run is the boom stub; rendering the page must not call it.
    at = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py")).run(timeout=30)
    assert not at.exception
    assert any(b.key == "nmap_run" for b in at.button)



# ---- Phase 4A.1: explicit port handling and Windows path
@pytest.mark.parametrize("target,expected", [
    ("127.0.0.1:8080", "8080"), ("http://127.0.0.1:8080", "8080"),
    ("http://127.0.0.1", "80"), ("https://127.0.0.1", "443"),
])
def test_target_port_is_scanned_not_ignored(monkeypatch, target, expected):
    fake = patch_run(monkeypatch)
    assert scan(target).status == "Completed"
    args = fake.calls[0]
    assert args[args.index("-p") + 1] == expected and "--top-ports" not in args
    assert args[-1] == "127.0.0.1"


def test_bare_host_without_port_uses_default_top_ports(monkeypatch):
    fake = patch_run(monkeypatch)
    scan("127.0.0.1")
    assert "--top-ports" in fake.calls[0] and "-p" not in fake.calls[0]


def test_matching_ports_parameter_is_accepted(monkeypatch):
    fake = patch_run(monkeypatch)
    assert scan("127.0.0.1:8080", {"ports": "8080"}).status == "Completed"
    assert fake.calls[0][fake.calls[0].index("-p") + 1] == "8080"


def test_conflicting_port_is_rejected_before_execution():
    r = scan("127.0.0.1:8080", {"ports": "22,80"})  # boom stub proves no execution
    assert r.status == "Rejected" and r.error_code == "PORT_CONFLICT"
    r = scan("http://127.0.0.1", {"ports": "8080"})
    assert r.error_code == "PORT_CONFLICT"


def test_port_in_scope_still_enforced_with_target_port():
    scoped = ScopeConfig.from_entries(authorized=["127.0.0.1:8080"])
    assert scan("127.0.0.1:9090", None, scoped).error_code == "TARGET_NOT_AUTHORIZED"
    assert scan("127.0.0.1", None, scoped).error_code == "TARGET_NOT_AUTHORIZED"


def test_executable_path_with_spaces_stays_one_argv_element(monkeypatch):
    fake = patch_run(monkeypatch)
    path = r"C:\Program Files (x86)\Nmap\nmap.exe"
    scan(nmap_path=path)
    assert fake.calls[0][0] == path and fake.kw[0]["shell"] is False


def test_real_nmap_output_shape_regression():
    """Sanitized from a real local 127.0.0.1 scan (Nmap 7.993, Windows)."""
    xml = ('<?xml version="1.0"?>\n<!DOCTYPE nmaprun>\n<nmaprun scanner="nmap" version="7.993">'
           '<host><status state="up" reason="localhost-response" reason_ttl="0"/>'
           '<address addr="127.0.0.1" addrtype="ipv4"/><hostnames><hostname name="localhost" type="PTR"/></hostnames>'
           '<ports><extraports state="closed" count="96"><extrareasons reason="reset" count="96"/></extraports>'
           '<port protocol="tcp" portid="135"><state state="open" reason="syn-ack" reason_ttl="128"/>'
           '<service name="msrpc" product="Microsoft Windows RPC" ostype="Windows" method="probed" conf="10">'
           '<cpe>cpe:/o:microsoft:windows</cpe></service></port>'
           '<port protocol="tcp" portid="3306"><state state="open"/>'
           '<service name="mysql" product="MySQL" version="8.0.44" method="probed" conf="10"/></port>'
           '</ports></host></nmaprun>')
    out = na.parse_nmap_xml(xml)
    assert [s["port"] for s in out["services"]] == [135, 3306]  # extraports is not a port
    assert out["services"][0]["version"] is None and out["services"][1]["version"] == "8.0.44"
    assert out["hosts"][0]["hostnames"] == ["localhost"]
