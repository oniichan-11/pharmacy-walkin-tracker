"""Screen 1 — Log a walk-in request. Optimised for a few seconds at the counter.

Entry has two equally valid paths, because plenty of requests are for things we
have never stocked (that's the point of the app):

  A. Pick from the catalog  -> we stock it, so this is an OUT-OF-STOCK event.
  B. Type it free-hand      -> not on our shelves, so a NEW-RANGE candidate.

Both auto-tag the stock status and category, and both stay overridable. A fuzzy
"did you mean…?" check on path B stops a typo being miscounted as new range.
"""

from __future__ import annotations

import streamlit as st

import auth
import catalog
import config
import data
import theme


def render() -> None:
    branch, staff = auth.current_context()
    df = data.get_requests()

    theme.header(
        f"{config.LABELS['log_verb']} a walk-in {config.LABELS['record']}",
        f"{branch} · {staff} — record anything a {config.LABELS['customer']} "
        f"asked for that you couldn't sell.",
    )

    if not catalog.is_available():
        st.warning(
            "Product catalog not found — run `python build_catalog.py` to enable "
            "autocomplete and auto-tagging. You can still log requests as free text.",
            icon="⚠️",
        )

    _entry_form(branch, staff, df)
    _recent_panel(data.get_requests(), branch, staff)


def _entry_form(branch: str, staff: str, df) -> None:
    catalog_names = catalog.names()
    options = [config.CATALOG_NOT_LISTED] + catalog_names

    with st.form("log", clear_on_submit=True):
        st.markdown("**What did they ask for?**")
        picked = st.selectbox(
            f"Search our shelves ({catalog.size():,} products)",
            options,
            index=0,
            help="Type any part of the name to search. If it isn't here, leave "
                 "this as-is and type the item in the box below.",
        )
        typed = st.text_input(
            "Item not in our catalog",
            placeholder="e.g. Ozempic 1mg pen — something we don't stock",
            help="Use this for anything the search above doesn't cover. These "
                 "become your new-range candidates.",
        )

        st.markdown("**Details**")
        c1, c2 = st.columns(2)
        with c1:
            quantity = st.number_input(
                "How many did they want?", min_value=1, max_value=1000, value=1, step=1
            )
        with c2:
            est_value = st.number_input(
                f"Est. value of missed sale ({config.CURRENCY_SYMBOL}, optional)",
                min_value=0.0, value=0.0, step=1.0,
            )

        # Feature: log several items the same customer asked for, in one go, so a
        # single callback (name + phone below) covers all of them.
        more_items = st.text_area(
            "More items from the same customer (optional) — one per line",
            placeholder="Metformin 1g\nGlucometer test strips\n…",
            help="Each line is logged as its own request but shares the customer "
                 "and callback details you enter below.",
        )

        with st.expander("Override auto-tagging, or add callback details"):
            st.caption(
                "Category and stock status are filled in automatically from the "
                "catalog. Change them here only if the automatic choice is wrong."
            )
            override = st.checkbox("Set category / stock status manually")
            oc1, oc2 = st.columns(2)
            with oc1:
                manual_category = st.selectbox("Category", config.CATEGORIES)
            with oc2:
                manual_status = st.selectbox("Stock status", config.STATUSES)

            st.markdown(f"**{config.LABELS['customer'].capitalize()} & callback**")
            cn1, cn2 = st.columns(2)
            with cn1:
                customer_name = st.text_input(
                    f"{config.LABELS['customer'].capitalize()} name (optional)",
                    placeholder="Who to ask for on the callback",
                )
            with cn2:
                customer_contact = st.text_input(
                    f"{config.LABELS['customer'].capitalize()} phone (optional)",
                    placeholder="For a callback when it's in stock",
                )
            notify = st.checkbox("Wants a callback")
            notes = st.text_area(
                "Notes", placeholder="Brand insistence, dosage, alternatives offered…"
            )

        submitted = st.form_submit_button(
            f"✅ Save {config.LABELS['record']}", use_container_width=True, type="primary"
        )

    if not submitted:
        return

    # Assemble every item: the primary (catalog pick or typed) + each extra line.
    items: list[str] = []
    from_catalog = picked != config.CATALOG_NOT_LISTED
    primary = picked if from_catalog else typed.strip()
    if primary:
        items.append(primary)
    for line in (more_items or "").splitlines():
        line = line.strip()
        if line:
            items.append(line)
    # De-duplicate case-insensitively while preserving order.
    seen, unique_items = set(), []
    for it in items:
        if it.casefold() not in seen:
            seen.add(it.casefold())
            unique_items.append(it)

    if not unique_items:
        st.error(
            f"Please pick or type at least one {config.LABELS['item']} "
            "(the search, the free-text box, or the 'more items' list)."
        )
        return

    # One shared timestamp so a multi-item request reads as a single visit.
    shared_ts = data.now_local().isoformat(timespec="seconds")
    close_matches: list[str] = []

    for idx, item in enumerate(unique_items):
        tag = catalog.classify(item)
        category = manual_category if override else tag["category"]
        status = manual_status if override else tag["status"]
        row = data.new_request_row(
            branch=branch,
            staff=staff,
            item_raw=item,
            category=category,
            quantity=int(quantity) if idx == 0 else 1,   # primary keeps the qty
            status=status,
            in_catalog=tag["in_catalog"],
            catalog_match=tag["catalog_match"],
            est_value=(est_value if (idx == 0 and est_value > 0) else None),
            customer_name=customer_name,
            customer_contact=customer_contact,
            notify_customer=notify,
            notes=notes,
            timestamp_iso=shared_ts,
        )
        data.add_request(row)
        if not tag["in_catalog"] and tag["suggestions"]:
            close_matches.append(f"**{item}** → {', '.join(tag['suggestions'][:3])}")

    if len(unique_items) == 1:
        st.success(f"Saved **{unique_items[0]}**.")
    else:
        st.success(
            f"Saved **{len(unique_items)} items** for this "
            f"{config.LABELS['customer']}"
            + (f" ({customer_name.strip()})" if customer_name.strip() else "")
            + "."
        )
    st.toast("Logged ✔", icon="✅")

    # Aggregate the typo-guard: any free-typed items that resemble stocked lines.
    if close_matches:
        st.warning(
            "Heads up — these were logged as **not in our range**, but look close "
            "to things we stock:\n\n"
            + "\n".join(f"- {m}" for m in close_matches)
            + "\n\nIf any is what they meant, fix it on **Browse & resolve** so it "
            "counts as out-of-stock instead.",
            icon="💡",
        )


def _recent_panel(df, branch, staff) -> None:
    st.divider()
    st.markdown("**Your recent entries today**")
    if df.empty:
        st.caption("No requests logged yet.")
        return
    today = data.now_local().date()
    mine = df[(df["branch"] == branch) & (df["staff"] == staff) & (df["date"] == today)]
    if mine.empty:
        st.caption("Nothing logged by you yet today.")
        return
    show = (
        mine.sort_values("timestamp", ascending=False)
        .loc[:, ["timestamp", "item_clean", "category", "status", "quantity"]]
        .head(8)
        .rename(
            columns={
                "timestamp": "Time",
                "item_clean": config.LABELS["item"].capitalize(),
                "category": "Category",
                "status": "Stock status",
                "quantity": "Qty",
            }
        )
    )
    show["Time"] = show["Time"].dt.strftime("%H:%M")
    st.dataframe(show, hide_index=True, use_container_width=True)
