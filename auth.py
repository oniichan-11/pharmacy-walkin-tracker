"""
Lightweight access control for the Walk-In Demand Tracker.

Model (chosen for counter speed, not high security):
  1. Staff pick their branch and type that branch's shared PIN.
  2. They then pick their name (or 'Other' + type it) for attribution.
  3. An optional admin PIN unlocks the edit/resolve screen.

PINs live in st.secrets so they are not committed to the repo. For pure local
testing with no secrets file, DEV fallback PINs are used and a clear warning is
shown. Never rely on the DEV PINs for a live, shared URL.
"""

from __future__ import annotations

import streamlit as st

import config
import theme

# Fallback PINs for offline/local development ONLY.
_DEV_BRANCH_PIN = "0000"
_DEV_ADMIN_PIN = "9999"


def _secret_branch_pin(branch: str) -> str | None:
    try:
        pins = st.secrets["branch_pins"]
    except Exception:
        return None
    return pins.get(branch)


def _secret_admin_pin() -> str | None:
    try:
        return st.secrets["branch_pins"].get("admin_pin")
    except Exception:
        return None


def using_dev_pins() -> bool:
    try:
        return "branch_pins" not in st.secrets
    except Exception:
        return True


def is_admin() -> bool:
    return bool(st.session_state.get("is_admin"))


def check_admin_pin(entered: str) -> bool:
    expected = _secret_admin_pin() or _DEV_ADMIN_PIN
    ok = entered.strip() == str(expected).strip()
    st.session_state["is_admin"] = ok
    return ok


def logout() -> None:
    for key in ("authed", "branch", "staff", "is_admin"):
        st.session_state.pop(key, None)


def current_context() -> tuple[str, str]:
    """(branch, staff) for the signed-in session. Assumes require_login() passed."""
    return st.session_state.get("branch", ""), st.session_state.get("staff", "")


def require_login() -> bool:
    """Render the sign-in gate. Returns True once a branch+staff session exists.

    Call at the very top of the app; if it returns False, stop rendering.
    """
    if st.session_state.get("authed"):
        return True

    # Centre the sign-in card rather than stretching it across a wide layout.
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        if theme.logo_exists():
            lc1, lc2, lc3 = st.columns([1, 2, 1])
            with lc2:
                st.image(theme.LOGO_PATH, use_container_width=True)
        st.markdown(
            f"<h3 style='text-align:center;margin-bottom:0.2rem'>Walk-In Demand Tracker</h3>"
            f"<p style='text-align:center;color:{config.INK_MUTED};margin-top:0'>"
            f"Sign in to log walk-in {config.LABELS['records']}.</p>",
            unsafe_allow_html=True,
        )

        if using_dev_pins():
            st.warning(
                f"**Development mode** — no PIN secrets found, so any branch PIN "
                f"is `{_DEV_BRANCH_PIN}` and the admin PIN is `{_DEV_ADMIN_PIN}`. "
                "Set real PINs in `.streamlit/secrets.toml` before sharing the URL.",
                icon="⚠️",
            )

        with st.form("login"):
            branch = st.selectbox("Branch", config.BRANCHES)
            pin = st.text_input("Branch PIN", type="password", max_chars=12)
            submitted = st.form_submit_button(
                "Continue", use_container_width=True, type="primary"
            )

    if submitted:
        expected = _secret_branch_pin(branch) or _DEV_BRANCH_PIN
        if pin.strip() == str(expected).strip():
            st.session_state["authed"] = True
            st.session_state["branch"] = branch
            st.rerun()
        else:
            st.error("Incorrect PIN for this branch.")
    return False


def pick_staff() -> str:
    """Ensure a staff name is set for attribution. Returns the chosen name."""
    if st.session_state.get("staff"):
        return st.session_state["staff"]

    branch = st.session_state.get("branch", "")
    roster = list(config.STAFF_BY_BRANCH.get(branch, [])) + ["Other"]

    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        if theme.logo_exists():
            lc1, lc2, lc3 = st.columns([1, 2, 1])
            with lc2:
                st.image(theme.LOGO_PATH, use_container_width=True)
        st.info(f"Signed in at **{branch}**. Who's logging? Entries are attributed to you.")
        with st.form("who"):
            choice = st.selectbox("Your name", roster)
            other = st.text_input("If 'Other', type your name")
            ok = st.form_submit_button(
                "Start logging", use_container_width=True, type="primary"
            )
    if ok:
        name = other.strip() if choice == "Other" else choice
        if not name:
            st.error("Please enter your name.")
        else:
            st.session_state["staff"] = name
            st.rerun()
    return ""
