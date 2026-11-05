"""Controlled Nmap service-scan panel. Scans run only on an explicit button click."""
import streamlit as st

from src.config import load_settings
from src.scanners import run_service_scan
from src.scope import ScopeConfig, validate_scope


def render_nmap_scan() -> None:
    st.subheader("Nmap service scan")
    settings = load_settings()
    scope = ScopeConfig.from_settings(settings)

    target = st.text_input("Target", key="nmap_target", placeholder="127.0.0.1")
    ports = st.text_input("Ports (optional, e.g. 80,443,8000-8100)", key="nmap_ports",
                          help="Empty = Nmap top 100 ports, unless the target itself has a port "
                               "(127.0.0.1:8080 or http://host) - then only that port is scanned.")
    params = {"ports": ports.strip()} if ports.strip() else {}
    st.caption("Service/version detection only. Sends network probes to the target; "
               "use only on targets you are authorized to test.")

    c1, c2 = st.columns(2)
    if c1.button("Validate request", key="nmap_validate"):
        vr = validate_scope(target, "nmap", "service_scan", params, scope)
        (st.success if vr.accepted else st.error)(
            f"{'Accepted' if vr.accepted else 'Rejected'} [{vr.code}]: {vr.reason}")
    if c2.button("Run service scan", key="nmap_run", type="primary"):
        with st.spinner("Running Nmap..."):
            result = run_service_scan(target, params, scope, settings.nmap_path,
                                      settings.nmap_timeout_seconds)
        if result.status == "Completed":
            st.success(f"Completed in {result.duration_seconds}s")
            services = result.parsed_output.get("services", [])
            if services:
                st.dataframe(services, use_container_width=True)
            else:
                st.info("Scan completed; no ports were reported.")
        else:
            st.error(f"{result.status} [{result.error_code}]: {result.error}")
        st.json(result.as_dict())  # raw output omitted

