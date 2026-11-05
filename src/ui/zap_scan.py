"""Controlled OWASP ZAP passive-scan panel. Scans run only on an explicit button click."""
import streamlit as st

from src.config import load_settings
from src.scanners import ZapConfig, check_zap_availability, run_passive_scan
from src.scope import ScopeConfig, validate_scope


def render_zap_scan() -> None:
    st.subheader("OWASP ZAP passive scan")
    settings = load_settings()
    scope = ScopeConfig.from_settings(settings)

    target = st.text_input("Target URL", key="zap_target", placeholder="http://127.0.0.1:8080")
    st.caption(
        "Passive analysis only: inspects a single HTTP response through ZAP's passive scanning rules. "
        "No spidering, no crawling, no active attack payloads. Use only on authorized web targets."
    )

    zap_avail = check_zap_availability(settings.zap_api_url, settings.zap_api_key, timeout=0.2)
    if zap_avail["api_reachable"]:
        st.success(f"ZAP API connected at {settings.zap_api_url} (v{zap_avail['version']})")
    elif zap_avail["installed"]:
        st.info(
            f"ZAP is installed locally ({zap_avail['executable_path']}), "
            f"but the API daemon is not reachable at {settings.zap_api_url}. "
            "To perform live scans, start ZAP in daemon or desktop mode."
        )
    else:
        st.warning(
            f"ZAP is not reachable at {settings.zap_api_url}. "
            "Ensure ZAP is installed and running."
        )

    c1, c2 = st.columns(2)
    if c1.button("Validate request", key="zap_validate"):
        vr = validate_scope(target, "zap", "passive_scan", {}, scope)
        (st.success if vr.accepted else st.error)(
            f"{'Accepted' if vr.accepted else 'Rejected'} [{vr.code}]: {vr.reason}"
        )
    if c2.button("Run passive scan", key="zap_run", type="primary"):
        cfg = ZapConfig.from_settings(settings)
        with st.spinner("Running ZAP passive scan..."):
            result = run_passive_scan(target, {}, scope, cfg)

        if result.status == "Completed":
            st.success(f"Completed in {result.duration_seconds}s")
            findings = result.findings
            if findings:
                st.write(f"**Found {len(findings)} normalized alert(s):**")
                preview_data = [
                    {
                        "Title": f.get("title"),
                        "Severity": f.get("severity"),
                        "Confidence": f.get("confidence"),
                        "URL": f.get("affected_url"),
                        "Param": f.get("parameter") or "-",
                        "CWE": f.get("cwe_id") or "-",
                    }
                    for f in findings
                ]
                st.dataframe(preview_data, use_container_width=True)
                with st.expander("Detailed Findings & Evidence"):
                    for idx, f in enumerate(findings, 1):
                        st.markdown(f"**{idx}. {f.get('title')}** ({f.get('severity')})")
                        st.write(f"**Description:** {f.get('description')}")
                        if f.get("evidence"):
                            st.code(f.get("evidence"), language="text")
                        if f.get("remediation"):
                            st.write(f"**Remediation:** {f.get('remediation')}")
                        st.divider()
            else:
                st.info("Passive scan completed; no alerts were reported for this target.")
        elif result.status == "Partial":
            st.warning(f"Partial results [{result.error_code}]: {result.error}")
        else:
            st.error(f"{result.status} [{result.error_code}]: {result.error}")

        st.json(result.as_dict())  # raw output omitted
