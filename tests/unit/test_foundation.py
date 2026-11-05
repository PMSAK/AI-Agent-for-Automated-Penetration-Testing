from pathlib import Path

from src.config import check_scanner_availability, load_settings


def test_settings_load_without_exposing_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    s = load_settings()
    assert s.api_key_configured
    assert "sk-test-secret" not in repr(s)


def test_scanner_check_returns_bool_map():
    result = check_scanner_availability()
    assert set(result) == {"nmap", "nikto"}
    assert all(isinstance(v, bool) for v in result.values())


def test_startup_page_renders():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py")).run(timeout=30)
    assert not at.exception
    assert at.title[0].value == "Unified VAPT Agent"


def test_scope_form_validates_without_executing(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("AUTHORIZED_TARGETS", "http://127.0.0.1:8080")
    at = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py")).run(timeout=30)
    at.text_input(key="scope_target").set_value("http://127.0.0.1:8080")
    at.selectbox(key="scope_operation").select("zap.passive_scan")
    at.button(key="scope_validate").click().run(timeout=30)
    assert not at.exception and any("Accepted" in s.value for s in at.success)
    at.text_input(key="scope_target").set_value("http://evil.test")
    at.button(key="scope_validate").click().run(timeout=30)
    assert any("TARGET_NOT_AUTHORIZED" in e.value for e in at.error)


def test_zap_ui_renders_and_validates(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("AUTHORIZED_TARGETS", "http://127.0.0.1:8080")
    at = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py")).run(timeout=30)
    assert not at.exception
    # Ensure ZAP UI elements are rendered
    assert any(b.key == "zap_run" for b in at.button)
    assert any(b.key == "zap_validate" for b in at.button)
    # Validate target via ZAP UI form
    at.text_input(key="zap_target").set_value("http://127.0.0.1:8080")
    at.button(key="zap_validate").click().run(timeout=30)
    assert not at.exception and any("Accepted" in s.value for s in at.success)
    # Reject unauthorized target via ZAP UI form
    at.text_input(key="zap_target").set_value("http://unauthorized.test")
    at.button(key="zap_validate").click().run(timeout=30)
    assert any("TARGET_NOT_AUTHORIZED" in e.value for e in at.error)

