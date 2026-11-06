"""Minimal startup page (Phase 1-4)."""
import logging

import streamlit as st

from src.config import check_scanner_availability, load_settings, setup_logging
from src.scanners import check_zap_availability
from src.ui.nmap_scan import render_nmap_scan
from src.ui.scope_check import render_scope_check
from src.ui.zap_scan import render_zap_scan

logger = logging.getLogger(__name__)


def render() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    logger.info("Startup page rendered")

    st.title("Unified VAPT Agent")
    st.caption("Phase 1-4 VAPT Foundation: Nmap & OWASP ZAP integrations.")

    if settings.api_key_configured:
        st.success("OpenAI API key is configured.")
    else:
        st.error("OPENAI_API_KEY is missing. Add it to the .env file.")

    st.subheader("Scanner availability")
    for name, found in check_scanner_availability().items():
        st.write(f"{'✅' if found else '⚠️'} {name}: {'found' if found else 'not found on PATH'}")

    zap_avail = check_zap_availability(settings.zap_api_url, settings.zap_api_key, timeout=1.0)
    if zap_avail["api_reachable"]:
        st.write(f"✅ zap: API reachable at {settings.zap_api_url} (v{zap_avail['version']})")
    elif zap_avail.get("auth_failed"):
        st.write(f"⚠️ zap: daemon is running at {settings.zap_api_url}, but API authentication failed (check ZAP_API_KEY in .env)")
    elif zap_avail["installed"]:
        st.write(f"⚠️ zap: installed locally ({zap_avail['executable_path']}), but daemon is not running on {settings.zap_api_url}")
    else:
        st.write(f"⚠️ zap: not detected on PATH or default directory; API not reachable on {settings.zap_api_url}")

    render_scope_check()
    render_nmap_scan()
    render_zap_scan()
