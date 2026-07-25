"""Screen 2 — Live demand dashboard for the manager/analyst.

Chart decisions worth knowing:
  * Colour encodes stock status (identity), never magnitude — bar length already
    carries magnitude, so a value-ramp would waste the identity channel.
  * A status keeps its hue under every filter, so "amber = out of stock" stays
    learnable. Colours are the validated brand steps in config.py.
  * Single-series charts use one colour and no legend; the title names them.
  * Every chart has a table twin, so no value is reachable only by hovering.
  * All filters live in ONE row above the charts, never inside a chart card.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

import analytics
import config
import data
import theme


def render() -> None:
    df = data.get_requests()
    theme.header(
        "Walk-in demand dashboard",
        "What customers asked for that you couldn't sell them.",
    )

    if df.empty:
        st.info("No requests logged yet. Head to **Log a request** to add the first one.")
        return

    flt, freq = _filter_row(df)
    view = analytics.filter_requests(df, **flt)

    if view.empty:
        st.warning("No requests match the current filters.")
        return

    _kpi_row(view)
    st.write("")
    _top_items(view)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        _branch_status(view)
    with c2:
        _category_chart(view)
    st.write("")
    _trend(view, freq)
    st.write("")
    _priority_lists(view)


# --------------------------------------------------------------------------- #
# Filters — one row, scoping every chart below
# --------------------------------------------------------------------------- #
def _filter_row(df: pd.DataFrame) -> tuple[dict, str]:
    with st.expander("Filters", expanded=False):
        min_d, max_d = df["date"].min(), df["date"].max()
        c1, c2, c3, c4 = st.columns([2, 1.4, 1.4, 1.2])
        with c1:
            date_range = st.date_input(
                "Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d
            )
        with c2:
            branches = st.multiselect("Branch", config.BRANCHES)
        with c3:
            statuses = st.multiselect("Stock status", config.STATUSES)
        with c4:
            freq_label = st.selectbox("Trend by", ["Day", "Week"])
        categories = st.multiselect("Category", config.CATEGORIES)

    start = end = None
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start, end = date_range
    elif date_range and not isinstance(date_range, (tuple, list)):
        start = end = date_range

    flt = dict(
        start=start,
        end=end,
        branches=branches or None,
        categories=categories or None,
        statuses=statuses or None,
    )
    return flt, ("D" if freq_label == "Day" else "W")


# --------------------------------------------------------------------------- #
# Stat tiles
# --------------------------------------------------------------------------- #
def _kpi_row(df: pd.DataFrame) -> None:
    k = analytics.kpis(df)
    c = st.columns(5)
    c[0].metric("Total requests", f"{k['total']:,}")
    c[1].metric("Distinct items", f"{k['unique_items']:,}")
    c[2].metric("Restock signals", f"{k['restock']:,}")
    c[3].metric("New-range signals", f"{k['new_range']:,}")
    missed = k["missed_value"]
    c[4].metric(
        "Est. missed sales",
        f"{config.CURRENCY_SYMBOL}{missed:,.0f}" if missed else "—",
        help="Sum of the estimated values staff entered. Only some requests "
             "carry a value, so read this as a floor, not a total.",
    )


def _table_twin(frame: pd.DataFrame, label: str = "Show as table") -> None:
    """Every chart gets one: no value is reachable only by hovering."""
    with st.expander(label):
        st.dataframe(frame, hide_index=True, use_container_width=True)


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def _top_items(df: pd.DataFrame) -> None:
    theme.eyebrow("Where the demand is")
    st.markdown("**Most-requested items**")
    top = analytics.top_items(df, n=12)
    if top.empty:
        st.caption("No items to show.")
        return

    top = top.copy()
    top["status_short"] = top["status"].map(config.STATUS_SHORT).fillna(top["status"])

    bars = (
        alt.Chart(top)
        .mark_bar(size=theme.BAR_SIZE, cornerRadiusEnd=theme.CORNER_RADIUS)
        .encode(
            x=alt.X("requests:Q", title="Requests", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("item:N", sort="-x", title=None,
                    axis=alt.Axis(labelLimit=240, labelFontSize=12)),
            color=alt.Color(
                "status_short:N",
                scale=theme.status_scale(),
                legend=alt.Legend(title="Stock status", orient="top", direction="horizontal"),
            ),
            tooltip=[
                alt.Tooltip("item:N", title="Item"),
                alt.Tooltip("status_short:N", title="Status"),
                alt.Tooltip("requests:Q", title="Requests"),
                alt.Tooltip("quantity:Q", title="Total qty wanted"),
                alt.Tooltip("branches:Q", title="Branches"),
                alt.Tooltip("last:T", title="Last asked"),
            ],
        )
    )
    # Direct-label the value at each bar tip (ink, never the series colour).
    labels = bars.mark_text(
        align="left", dx=6, fontSize=12, color=config.INK_MUTED
    ).encode(text="requests:Q", color=alt.value(config.INK_MUTED))

    st.altair_chart((bars + labels).properties(height=34 * len(top) + 30),
                    use_container_width=True)

    _table_twin(
        top[["item", "status_short", "requests", "quantity", "branches", "last"]].rename(
            columns={"item": "Item", "status_short": "Status", "requests": "Requests",
                     "quantity": "Qty wanted", "branches": "Branches", "last": "Last asked"}
        )
    )


def _branch_status(df: pd.DataFrame) -> None:
    """Grouped bars: which branch is losing what kind of sale.

    Replaces an earlier donut, which only restated the stat tiles above.
    """
    st.markdown("**Requests by branch and status**")
    g = (
        df.assign(status_short=df["status"].map(config.STATUS_SHORT).fillna(df["status"]))
        .groupby(["branch", "status_short"], sort=False)
        .size()
        .rename("requests")
        .reset_index()
    )
    if g.empty:
        st.caption("No data.")
        return

    chart = (
        alt.Chart(g)
        .mark_bar(size=theme.BAR_SIZE, cornerRadiusEnd=theme.CORNER_RADIUS)
        .encode(
            x=alt.X("requests:Q", title="Requests", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("status_short:N", title=None, sort="-x"),
            yOffset=alt.YOffset("branch:N"),
            color=alt.Color("status_short:N", scale=theme.status_scale(), legend=None),
            opacity=alt.Opacity(
                "branch:N",
                scale=alt.Scale(domain=config.BRANCHES, range=[1.0, 0.55]),
                legend=alt.Legend(title="Branch", orient="top", direction="horizontal"),
            ),
            tooltip=[
                alt.Tooltip("branch:N", title="Branch"),
                alt.Tooltip("status_short:N", title="Status"),
                alt.Tooltip("requests:Q", title="Requests"),
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)
    _table_twin(
        g.rename(columns={"branch": "Branch", "status_short": "Status", "requests": "Requests"})
    )


def _category_chart(df: pd.DataFrame) -> None:
    """Single series, nominal categories -> one colour, no legend."""
    st.markdown("**Requests by category**")
    dim = analytics.by_dimension(df, "category").head(8)
    if dim.empty:
        st.caption("No data.")
        return
    chart = (
        alt.Chart(dim)
        .mark_bar(size=theme.BAR_SIZE, cornerRadiusEnd=theme.CORNER_RADIUS,
                  color=config.SERIES_PRIMARY)
        .encode(
            x=alt.X("requests:Q", title="Requests", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("category:N", sort="-x", title=None,
                    axis=alt.Axis(labelLimit=200)),
            tooltip=[alt.Tooltip("category:N", title="Category"),
                     alt.Tooltip("requests:Q", title="Requests")],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)
    _table_twin(dim.rename(columns={"category": "Category", "requests": "Requests"}))


def _trend(df: pd.DataFrame, freq: str) -> None:
    theme.eyebrow("Direction of travel")
    st.markdown(f"**Requests over time** ({'daily' if freq == 'D' else 'weekly'})")
    ts = analytics.requests_over_time(df, freq=freq)
    if ts.empty or len(ts) < 2:
        st.caption("Not enough data yet to show a trend.")
        return

    base = alt.Chart(ts)
    area = base.mark_area(color=config.SERIES_PRIMARY, opacity=0.10).encode(
        x=alt.X("period:T", title=None), y=alt.Y("requests:Q", title="Requests")
    )
    line = base.mark_line(
        color=config.SERIES_PRIMARY, strokeWidth=theme.LINE_WIDTH
    ).encode(x="period:T", y="requests:Q")
    pts = base.mark_point(
        color=config.SERIES_PRIMARY, size=theme.POINT_SIZE, filled=True,
        stroke=config.SURFACE, strokeWidth=2,       # 2px surface ring
    ).encode(
        x="period:T", y="requests:Q",
        tooltip=[alt.Tooltip("period:T", title="Period"),
                 alt.Tooltip("requests:Q", title="Requests")],
    )
    st.altair_chart((area + line + pts).properties(height=260), use_container_width=True)

    tbl = ts.copy()
    tbl["period"] = tbl["period"].dt.strftime("%Y-%m-%d")
    _table_twin(tbl.rename(columns={"period": "Period", "requests": "Requests"}))


# --------------------------------------------------------------------------- #
# Action lists
# --------------------------------------------------------------------------- #
def _priority_lists(df: pd.DataFrame) -> None:
    theme.eyebrow("What to do about it")
    st.markdown("**Action lists** — open (unresolved) requests only")
    st.caption(
        "Ranked by how often customers asked. Mark items handled on the "
        "**Browse & resolve** screen and they drop off these lists."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"<span style='color:{config.STATUS_COLORS['Out of stock']};font-weight:700'>●</span> "
            "**Restock priorities** — we carry these",
            unsafe_allow_html=True,
        )
        _priority_table(df, config.STATUS_RESTOCK)
    with c2:
        st.markdown(
            f"<span style='color:{config.STATUS_COLORS['Not in range']};font-weight:700'>●</span> "
            "**New-range candidates** — we've never stocked these",
            unsafe_allow_html=True,
        )
        _priority_table(df, config.STATUS_NEW_RANGE)


def _priority_table(df: pd.DataFrame, status: str) -> None:
    ranked = analytics.priority_list(df, status, n=15)
    if ranked.empty:
        st.caption("Nothing open here. 👍")
        return
    show = ranked.loc[:, ["item", "requests", "quantity", "branches", "last"]].rename(
        columns={"item": config.LABELS["item"].capitalize(), "requests": "Requests",
                 "quantity": "Qty wanted", "branches": "Branches", "last": "Last asked"}
    )
    st.dataframe(show, hide_index=True, use_container_width=True)
