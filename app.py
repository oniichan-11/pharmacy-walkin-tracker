"""
Pharmacy Direct — Walk-In Demand Tracker
========================================

A Streamlit app for logging items that walk-in customers ask for but you can't
sell them, across multiple branches, and turning that into live "unmet demand"
metrics for buying decisions.

Run locally:      streamlit run app.py
Deploy:           push to GitHub, connect on share.streamlit.io (see README).

Everything sector-specific lives in config.py; storage in data.py; sign-in in
auth.py; charts in views/. This file only wires them together.
"""

from __future__ import annotations

import streamlit as st

import auth
import config
import data
import theme
from views import browse, dashboard, log_request

st.set_page_config(
    page_title=config.APP_NAME,
    page_icon=theme.LOGO_PATH if theme.logo_exists() else config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


def _sidebar_context() -> None:
    branch, staff = auth.current_context()
    with st.sidebar:
        if theme.logo_exists():
            st.image(theme.LOGO_PATH, use_container_width=True)
        else:
            st.markdown(f"### {config.APP_ICON} {config.ORG_NAME}")

        st.markdown(
            f'<div class="pd-side-meta">'
            f'<div class="k">Branch</div><div class="v">{branch}</div>'
            f'<div class="k">Signed in as</div><div class="v">{staff}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        if auth.is_admin():
            st.caption("🔓 Admin mode")
        st.caption(f"Storage · {data.backend_name()}")
        if st.button("Sign out", use_container_width=True):
            auth.logout()
            st.rerun()


def main() -> None:
    theme.apply()

    # 1. Gate: branch PIN, then staff name.
    if not auth.require_login():
        st.stop()
    if not auth.pick_staff():
        st.stop()

    # 2. Signed in — show context and navigation.
    _sidebar_context()

    # Explicit url_path per page: all three view callables are named `render`,
    # so Streamlit would otherwise infer the same (colliding) URL path for each.
    pages = [
        st.Page(log_request.render, title="Log a request", icon="📝",
                url_path="log", default=True),
        st.Page(dashboard.render, title="Dashboard", icon="📊", url_path="dashboard"),
        st.Page(browse.render, title="Browse & resolve", icon="🗂️", url_path="browse"),
    ]
    st.navigation(pages).run()


if __name__ == "__main__":
    main()
