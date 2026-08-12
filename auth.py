"""
Sign-in for the Walk-In Demand Tracker.

Model (optimised for counter speed):
  * No sign-in PIN. Staff just pick their branch and enter their name, which is
    stored against every request they log for attribution.
  * A separate admin PIN still guards the destructive edit/delete controls on
    the Browse screen (that is a data-integrity gate, not a sign-in barrier).

The admin PIN comes from st.secrets when present, else a dev fallback.
"""

from __future__ import annotations

import streamlit as st

import config
import data
import theme

# Fallback admin PIN for local/dev use only (used by the edit/delete screen).
_DEV_ADMIN_PIN = "9999"


def _secret_admin_pin() -> str | None:
    try:
        return st.secrets["branch_pins"].get("admin_pin")
    except Exception:
        return None


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
    """Render the single sign-in screen (branch + name, no PIN).

    Returns True once branch + name are set; call at the top of the app and
    stop rendering if it returns False.
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
            f"Choose your branch and enter your name to start logging "
            f"{config.LABELS['records']}.</p>",
            unsafe_allow_html=True,
        )

        with st.form("signin"):
            branch = st.selectbox("Branch", config.BRANCHES)
            name = _name_widget(branch)
            submitted = st.form_submit_button(
                "Start logging", use_container_width=True, type="primary"
            )

    if submitted:
        name = (name or "").strip()
        if not name:
            st.error("Please enter your name so entries can be attributed to you.")
        else:
            st.session_state["authed"] = True
            st.session_state["branch"] = branch
            st.session_state["staff"] = name
            st.rerun()
    return False


_NEW_NAME = "➕ New name…"


def _known_names(branch: str) -> list[str]:
    """Quick-pick roster: any names configured for the branch, plus everyone who
    has signed in before (from the data), de-duplicated case-insensitively."""
    seen: dict[str, str] = {}
    for name in list(config.STAFF_BY_BRANCH.get(branch, [])) + data.known_staff():
        key = name.casefold()
        if key and key not in seen:
            seen[key] = name
    return list(seen.values())


def _name_widget(branch: str) -> str:
    """Name entry. Returning staff pick themselves from the list (no retyping);
    new staff choose 'New name…' and type it once — it then appears next time."""
    known = _known_names(branch)
    if not known:
        return st.text_input("Your name", placeholder="e.g. Ama Boateng")

    choice = st.selectbox(
        "Your name",
        known + [_NEW_NAME],
        index=None,
        placeholder="Select your name (or add a new one)",
    )
    new = st.text_input(
        "New name", placeholder="Only if you're not in the list above"
    )
    if choice in (None, _NEW_NAME):
        return new
    return choice
