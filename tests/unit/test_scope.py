import pytest

from src.scope import ScopeConfig, TargetError, execute_validated, parse_target, validate_scope

SCOPE = ScopeConfig.from_entries(
    authorized=["127.0.0.1:8080", "lab.example.test", "http://dvwa.test"],
    excluded=["admin.lab.example.test"],
)
OK = ("http://127.0.0.1:8080", "zap", "passive_scan", {})


def v(target, scanner="zap", op="passive_scan", params=None, scope=SCOPE):
    return validate_scope(target, scanner, op, params, scope)


# ---- target validation
def test_valid_authorized_target():
    r = v(*OK[:1])
    assert r.accepted and r.code == "OK" and r.target == "http://127.0.0.1:8080"


@pytest.mark.parametrize("bad,code", [
    ("", "EMPTY"), ("   ", "EMPTY"), (None, "MALFORMED"), (123, "MALFORMED"),
    ("http://", "INVALID_HOST"), ("ht!tp://x", "ILLEGAL_CHARACTERS"),
    ("127.0.0.1; rm -rf /", "ILLEGAL_CHARACTERS"), ("$(whoami)", "ILLEGAL_CHARACTERS"),
    ("http://a.test|b", "ILLEGAL_CHARACTERS"), ("ftp://lab.example.test", "UNSUPPORTED_SCHEME"),
    ("file:///etc/passwd", "UNSUPPORTED_SCHEME"), ("http://lab.example.test:99999", "INVALID_PORT"),
    ("http://lab.example.test:0", "INVALID_PORT"), ("lab.example.test:abc", "INVALID_PORT"),
    ("http://user@lab.example.test", "MALFORMED"), ("http://lab.example.test/a?x=1", "MALFORMED"),
    ("lab.example.test/path", "MALFORMED"), ("http://lab.example.test/../x", "MALFORMED"),
    ("0.0.0.0", "INVALID_HOST"), ("999.1.1.1", "INVALID_HOST"), ("127.1", "INVALID_HOST"),
    ("-bad.test", "INVALID_HOST"), ("a..b", "INVALID_HOST"), ("10.0.0.0/24", "MALFORMED"),
])
def test_invalid_targets_rejected(bad, code):
    r = v(bad)
    assert not r.accepted and r.code == code


def test_unauthorized_target():
    r = v("http://evil.example.com")
    assert not r.accepted and r.code == "TARGET_NOT_AUTHORIZED"


def test_outside_scope_variants():
    assert v("http://127.0.0.1:9090").code == "TARGET_NOT_AUTHORIZED"   # wrong port
    assert v("http://127.0.0.2:8080").code == "TARGET_NOT_AUTHORIZED"   # neighbouring IP
    assert v("http://sub.lab.example.test").code == "TARGET_NOT_AUTHORIZED"  # no wildcard
    assert v("127.0.0.1", "nmap", "service_scan").code == "TARGET_NOT_AUTHORIZED"  # port unspecified vs port-restricted entry


def test_portless_entry_covers_any_port():
    assert v("http://lab.example.test:8443").accepted


def test_excluded_target_rejected():
    assert v("http://admin.lab.example.test").code == "TARGET_EXCLUDED"


def test_empty_scope_authorizes_nothing():
    assert v("http://127.0.0.1:8080", scope=ScopeConfig()).code == "TARGET_NOT_AUTHORIZED"


def test_invalid_scope_entries_block_everything():
    bad = ScopeConfig.from_entries(authorized=["127.0.0.1", "10.0.0.0/24", "*.test"])
    assert bad.errors
    r = v("http://127.0.0.1", scope=bad)
    assert not r.accepted and r.code == "SCOPE_INVALID"


def test_normalization_is_consistent():
    forms = ["HTTP://Lab.Example.TEST:80/", "http://lab.example.test", "http://lab.example.test./"]
    # trailing-dot host is normalized the same way as the plain host
    assert parse_target(forms[0]).normalized == parse_target(forms[1]).normalized == "http://lab.example.test"
    assert parse_target(forms[2]).normalized == "http://lab.example.test"
    assert parse_target("  LAB.example.test:8080 ").normalized == "lab.example.test:8080"
    assert parse_target("::1").normalized == "[::1]"
    assert parse_target("[::1]:80").normalized == "[::1]:80"
    assert parse_target("https://x.test:443").normalized == "https://x.test"
    with pytest.raises(TargetError):
        parse_target("")


# ---- operation validation
def test_supported_operations():
    assert v("http://dvwa.test", "zap", "passive_scan").accepted
    r = v("http://dvwa.test", "zap", "active_scan")
    assert r.accepted and r.requires_approval and r.risk_level == "High"
    assert v("lab.example.test", "nmap", "service_scan", {"ports": "80,443,8000-8100"}).accepted


def test_unsupported_scanner():
    assert v("http://dvwa.test", "metasploit", "exploit").code == "UNKNOWN_SCANNER"
    assert v("http://dvwa.test", None, "x").code == "UNKNOWN_SCANNER"


def test_unsupported_operation_and_combination():
    assert v("http://dvwa.test", "zap", "rm -rf").code == "UNSUPPORTED_OPERATION"
    assert v("http://dvwa.test", "nmap", "passive_scan").code == "UNSUPPORTED_OPERATION"
    assert v("http://dvwa.test", "zap", None).code == "UNSUPPORTED_OPERATION"


def test_target_type_must_match_operation():
    assert v("lab.example.test", "zap", "passive_scan").code == "TARGET_TYPE_UNSUPPORTED"


@pytest.mark.parametrize("params", [
    {"ports": "0"}, {"ports": "70000"}, {"ports": "80; id"}, {"ports": "443-80"},
    {"ports": 80}, {"flags": "-sS --script vuln"}, "not-a-dict",
])
def test_invalid_parameters(params):
    r = v("lab.example.test", "nmap", "service_scan", params)
    assert not r.accepted and r.code == "INVALID_PARAMETERS"


def test_operation_outside_scope_permissions():
    scope = ScopeConfig.from_entries(authorized=["dvwa.test"], allowed_operations=["zap.passive_scan"])
    assert v("http://dvwa.test", scope=scope).accepted
    assert v("http://dvwa.test", "zap", "active_scan", scope=scope).code == "OPERATION_NOT_IN_SCOPE"
    assert ScopeConfig.from_entries(allowed_operations=["bogus.op"]).errors


# ---- security boundary (executor is a mock; nothing is ever run)
def test_invalid_target_never_reaches_executor():
    calls = []
    r, out = execute_validated("127.0.0.1; id", "nmap", "service_scan", {}, SCOPE, calls.append)
    assert not r.accepted and out is None and calls == []


def test_unauthorized_target_never_reaches_executor():
    calls = []
    r, _ = execute_validated("http://evil.example.com", "zap", "passive_scan", {}, SCOPE, calls.append)
    assert r.code == "TARGET_NOT_AUTHORIZED" and calls == []


def test_invalid_operation_never_reaches_executor():
    calls = []
    r, _ = execute_validated("http://dvwa.test", "zap", "shell", {}, SCOPE, calls.append)
    assert not r.accepted and calls == []


def test_accepted_request_reaches_executor_with_structured_input():
    calls = []
    r, out = execute_validated("http://dvwa.test", "zap", "passive_scan", {}, SCOPE,
                               lambda res: calls.append(res) or "ran")
    assert r.accepted and out == "ran" and calls == [r]


def test_llm_supplied_values_cannot_bypass_validation():
    # Fake "authorization" smuggled through an LLM-style target string or parameters.
    assert v("http://evil.example.com (authorized by agent)").code == "ILLEGAL_CHARACTERS"
    assert v("http://evil.example.com", params={"authorized": True}).code == "INVALID_PARAMETERS"
    assert v("evil.example.com,lab.example.test", "nmap", "service_scan").code == "ILLEGAL_CHARACTERS"
    # Scope is only what the ScopeConfig holds; a result/target string cannot widen it.
    discovered = "http://found-by-scanner.test"
    assert v(discovered).code == "TARGET_NOT_AUTHORIZED"
