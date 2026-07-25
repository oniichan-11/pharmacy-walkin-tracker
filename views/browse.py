"""Screen 3 — Browse every request, export it, and (as admin) edit/resolve/delete."""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

import analytics
import auth
import config
import data
import theme

# Fields an admin may edit inline. Everything else is read-only for audit safety.
_EDITABLE = ["item_clean", "category", "quantity", "status", "notes", "resolved"]


def render() -> None:
    df = data.get_requests()
    theme.header(
        "Browse & resolve",
        "Every logged request — search, export, and mark items handled.",
    )

    if df.empty:
        st.info("Nothing logged yet.")
        return

    flt = _filters(df)
    view = analytics.filter_requests(df, **flt).sort_values("timestamp", ascending=False)

    st.caption(f"Showing **{len(view):,}** of {len(df):,} total {config.LABELS['records']}.")
    _export_buttons(view)

    if not auth.is_admin():
        _read_only_table(view)
        _admin_unlock()
        return

    _editor(df, view)


def _filters(df: pd.DataFrame) -> dict:
    with st.expander("Filters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            branches = st.multiselect("Branch", config.BRANCHES, key="br_b")
        with c2:
            categories = st.multiselect("Item type", config.CATEGORIES, key="br_c")
        with c3:
            statuses = st.multiselect("Stock status", config.STATUSES, key="br_s")
        with c4:
            open_only = st.toggle("Open (unresolved) only", value=False)
        search = st.text_input("Search item / notes", placeholder="type to filter…")

    out = dict(
        branches=branches or None,
        categories=categories or None,
        statuses=statuses or None,
        unresolved_only=open_only,
    )
    st.session_state["_browse_search"] = search.strip().casefold()
    return out


def _apply_search(view: pd.DataFrame) -> pd.DataFrame:
    q = st.session_state.get("_browse_search", "")
    if not q:
        return view
    mask = (
        view["item_clean"].str.casefold().str.contains(q, na=False)
        | view["notes"].str.casefold().str.contains(q, na=False)
    )
    return view[mask]


def _display_columns(view: pd.DataFrame) -> pd.DataFrame:
    view = _apply_search(view)
    cols = [
        "request_id", "timestamp", "branch", "staff", "item_clean",
        "category", "quantity", "status", "resolved", "notes",
        "customer_contact", "notify_customer", "est_value",
    ]
    return view.loc[:, [c for c in cols if c in view.columns]].copy()


def _read_only_table(view: pd.DataFrame) -> None:
    show = _display_columns(view)
    st.dataframe(
        show,
        hide_index=True,
        use_container_width=True,
        column_config={
            "request_id": None,  # hide
            "timestamp": st.column_config.DatetimeColumn("When", format="YYYY-MM-DD HH:mm"),
            "item_clean": "Item",
            "notify_customer": st.column_config.CheckboxColumn("Callback?"),
            "resolved": st.column_config.CheckboxColumn("Resolved"),
            "est_value": st.column_config.NumberColumn(
                f"Est. value ({config.CURRENCY_SYMBOL})", format="%.0f"
            ),
        },
    )


def _admin_unlock() -> None:
    with st.expander("🔒 Admin — edit, resolve & delete"):
        with st.form("admin"):
            pin = st.text_input("Admin PIN", type="password")
            ok = st.form_submit_button("Unlock")
        if ok:
            if auth.check_admin_pin(pin):
                st.success("Admin unlocked.")
                st.rerun()
            else:
                st.error("Wrong admin PIN.")


def _editor(master: pd.DataFrame, view: pd.DataFrame) -> None:
    st.success("Admin mode — edit cells, tick **Resolved**, or tick **Delete**, then save.")
    show = _display_columns(view)
    show.insert(len(show.columns), "Delete", False)

    edited = st.data_editor(
        show,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="editor",
        column_config={
            "request_id": None,
            "timestamp": st.column_config.DatetimeColumn(
                "When", format="YYYY-MM-DD HH:mm", disabled=True
            ),
            "branch": st.column_config.TextColumn("Branch", disabled=True),
            "staff": st.column_config.TextColumn("Staff", disabled=True),
            "item_clean": st.column_config.TextColumn("Item"),
            "category": st.column_config.SelectboxColumn("Type", options=config.CATEGORIES),
            "quantity": st.column_config.NumberColumn("Qty", min_value=1, step=1),
            "status": st.column_config.SelectboxColumn("Stock status", options=config.STATUSES),
            "resolved": st.column_config.CheckboxColumn("Resolved"),
            "notes": st.column_config.TextColumn("Notes"),
            "customer_contact": st.column_config.TextColumn("Contact", disabled=True),
            "notify_customer": st.column_config.CheckboxColumn("Callback?", disabled=True),
            "est_value": st.column_config.NumberColumn(
                f"Est. value ({config.CURRENCY_SYMBOL})", format="%.0f"
            ),
        },
    )

    c1, c2 = st.columns([1, 3])
    with c1:
        save = st.button("💾 Save changes", type="primary", use_container_width=True)
    with c2:
        st.caption("Changes write straight to the shared store. Deletes cannot be undone.")

    if save:
        _persist(master, edited)


def _persist(master: pd.DataFrame, edited: pd.DataFrame) -> None:
    store = master.set_index("request_id")
    now_iso = data.now_local().isoformat(timespec="seconds")
    deletes, updates = [], 0

    for _, row in edited.iterrows():
        rid = row["request_id"]
        if rid not in store.index:
            continue
        if bool(row.get("Delete")):
            deletes.append(rid)
            continue
        for col in _EDITABLE:
            if col not in row:
                continue
            new_val = row[col]
            if col == "resolved":
                was = bool(store.at[rid, "resolved"])
                now = bool(new_val)
                if now and not was:
                    store.at[rid, "resolved_at"] = now_iso
                elif not now and was:
                    store.at[rid, "resolved_at"] = ""
                store.at[rid, "resolved"] = now
            else:
                store.at[rid, col] = new_val
        updates += 1

    if deletes:
        store = store.drop(index=deletes)

    out = store.reset_index()[config.COLUMNS]
    data.save_requests(out)
    msg = f"Saved {updates} row(s)."
    if deletes:
        msg += f" Deleted {len(deletes)}."
    st.success(msg)
    st.rerun()


def _export_buttons(view: pd.DataFrame) -> None:
    export = _display_columns(view).drop(columns=["request_id"], errors="ignore")
    csv = export.to_csv(index=False).encode("utf-8")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        export.to_excel(writer, index=False, sheet_name="requests")

    stamp = data.now_local().strftime("%Y%m%d")
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        st.download_button(
            "⬇️ CSV", csv, file_name=f"walkin_requests_{stamp}.csv",
            mime="text/csv", use_container_width=True,
        )
    with c2:
        st.download_button(
            "⬇️ Excel", buf.getvalue(), file_name=f"walkin_requests_{stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
