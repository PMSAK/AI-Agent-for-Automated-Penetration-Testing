"""Streamlit entry point: streamlit run app.py"""
import streamlit as st

from src.ui.startup import render

st.set_page_config(page_title="Unified VAPT Agent", page_icon="🛡️")
render()

