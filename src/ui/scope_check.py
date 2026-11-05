"""Minimal scope-validation form. Validates only; never executes a scanner."""
import streamlit as st

from src.config import load_settings
from src.scope import ScopeConfig, list_operations, validate_scope


def render_scope_check() -> None:
    st.subheader("Scope validation")
    scope = ScopeConfig.from_settings(load_settings())
    if not scope.authorized:
        st.warning("No authorized targets configured. Set AUTHORIZED_TARGETS in .env "
                   "(comma-separated hosts, IPs or URLs); until then every target is rejected.")

    ops = {op.key: op for op in list_operations()}
    target = st.text_input("Target", key="scope_target", placeholder="http://127.0.0.1:8080")
    op_key = st.selectbox("Operation", list(ops), key="scope_operation")
    ports = st.text_input("Ports (nmap only, optional)", key="scope_ports")

    if st.button("Validate", key="scope_validate"):
        op = ops[op_key]
        params = {"ports": ports.strip()} if ports.strip() else {}
        result = validate_scope(target, op.scanner, op.operation, params, scope)
        if result.accepted:
            st.success(f"Accepted: {result.target} ({op_key}). {result.reason}")
            if result.requires_approval:
                st.info("This operation will require approval (not implemented yet).")
        else:
            st.error(f"Rejected [{result.code}]: {result.reason}")
        st.json(result.as_dict())
        st.caption("Validation only. No scanner was executed.")

