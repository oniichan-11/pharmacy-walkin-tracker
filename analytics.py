"""
Pure analytics helpers over the requests DataFrame.

Kept separate from any Streamlit widgets so the same functions could feed a
report, a scheduled email, or a different UI later. Every function takes an
already-typed frame (as returned by data.get_requests()) and returns plain
pandas objects.
"""

from __future__ import annotations

import pandas as pd

import config


def filter_requests(
    df: pd.DataFrame,
    *,
    start=None,
    end=None,
    branches=None,
    categories=None,
    statuses=None,
    unresolved_only: bool = False,
) -> pd.DataFrame:
    out = df.copy()
    if start is not None:
        out = out[out["date"] >= start]
    if end is not None:
        out = out[out["date"] <= end]
    if branches:
        out = out[out["branch"].isin(branches)]
    if categories:
        out = out[out["category"].isin(categories)]
    if statuses:
        out = out[out["status"].isin(statuses)]
    if unresolved_only:
        out = out[~out["resolved"]]
    return out


def kpis(df: pd.DataFrame) -> dict:
    """Headline numbers for the dashboard tiles."""
    total = len(df)
    unique_items = df["match_key"].nunique() if total else 0
    restock = int((df["status"] == config.STATUS_RESTOCK).sum())
    new_range = int((df["status"] == config.STATUS_NEW_RANGE).sum())
    open_items = int((~df["resolved"]).sum())
    missed_value = df["est_value"].dropna().sum() if total else 0.0
    return {
        "total": total,
        "unique_items": unique_items,
        "restock": restock,
        "new_range": new_range,
        "open_items": open_items,
        "missed_value": float(missed_value),
    }


def top_items(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """Most-requested items, aggregated case-insensitively.

    Returns one row per item with: item (display), requests, quantity,
    dominant status, branches touched, last requested date.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["item", "requests", "quantity", "status", "branches", "last"]
        )

    def agg(group: pd.DataFrame) -> pd.Series:
        display = group["item_clean"].mode()
        display = display.iloc[0] if not display.empty else group["item_clean"].iloc[0]
        status = group["status"].mode()
        status = status.iloc[0] if not status.empty else ""
        return pd.Series(
            {
                "item": display,
                "requests": len(group),
                "quantity": int(group["quantity"].sum()),
                "status": status,
                "branches": group["branch"].nunique(),
                "last": group["date"].max(),
            }
        )

    result = (
        df.groupby("match_key", sort=False)
        .apply(agg, include_groups=False)
        .reset_index(drop=True)
        .sort_values(["requests", "quantity"], ascending=False)
    )
    return result.head(n).reset_index(drop=True)


def requests_over_time(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    """Time series of request counts. freq: 'D' daily, 'W' weekly."""
    if df.empty:
        return pd.DataFrame(columns=["period", "requests"])
    s = (
        df.dropna(subset=["timestamp"])
        .set_index("timestamp")
        .resample(freq)
        .size()
        .rename("requests")
        .reset_index()
        .rename(columns={"timestamp": "period"})
    )
    return s


def by_dimension(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Request counts grouped by a single column (branch, category, status)."""
    if df.empty:
        return pd.DataFrame(columns=[column, "requests"])
    return (
        df.groupby(column, sort=False)
        .size()
        .rename("requests")
        .reset_index()
        .sort_values("requests", ascending=False)
    )


def priority_list(df: pd.DataFrame, status: str, n: int = 20) -> pd.DataFrame:
    """Ranked action list for one stock status (restock vs add-to-range),
    counting only unresolved requests so the list is a live to-do."""
    subset = df[(df["status"] == status) & (~df["resolved"])]
    ranked = top_items(subset, n=n)
    return ranked
