# -------------------------
# LOAD CSS
# -------------------------

from pathlib import Path

import streamlit as st


def load_css() -> None:
    css_path = Path(__file__).resolve().parents[2] / "styles.css"

    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    else:
        st.error(f"styles.css blev ikke fundet: {css_path}")