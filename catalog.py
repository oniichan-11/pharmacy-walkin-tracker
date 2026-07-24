"""
Product catalog lookup — the bridge between what a customer asks for and what
Pharmacy Direct actually stocks.

Backed by `data/catalog.csv`, generated from the Adenta stock-taking master
list by `build_catalog.py`. The Adenta shelves cover ~95% of the Atomic branch
too, so one catalog serves both.

Its job is to answer two questions:
  1. Is this item on our shelves?  -> decides "Out of stock" vs "Not in range"
  2. What shelf/category is it on?  -> auto-fills the category field

Crucially, an item that matches nothing is a valid, expected outcome — those
are exactly the range-expansion opportunities this whole app exists to find.
"""

from __future__ import annotations

import difflib
import os
from functools import lru_cache

import pandas as pd
import streamlit as st

import config


@st.cache_data(show_spinner=False)
def load() -> pd.DataFrame:
    """The catalog as a DataFrame: product_name, category_shelf, match_key.
    Returns an empty frame (never raises) if the catalog hasn't been built."""
    if not os.path.exists(config.CATALOG_CSV_PATH):
        return pd.DataFrame(columns=["product_name", "category_shelf", "match_key"])
    df = pd.read_csv(config.CATALOG_CSV_PATH, dtype=str, keep_default_na=False)
    return df


def is_available() -> bool:
    return not load().empty


def size() -> int:
    return len(load())


def names() -> list[str]:
    """Product names for the picker, alphabetical."""
    return load()["product_name"].tolist()


@lru_cache(maxsize=1)
def _index() -> dict[str, tuple[str, str]]:
    """match_key -> (product_name, category_shelf). Cached for fast lookups."""
    df = load()
    return {
        r.match_key: (r.product_name, r.category_shelf)
        for r in df.itertuples(index=False)
    }


def lookup(item: str) -> tuple[str, str] | None:
    """Exact (case-insensitive) catalog hit, or None."""
    if not item:
        return None
    return _index().get(" ".join(str(item).split()).strip().casefold())


def suggest(text: str, n: int | None = None, cutoff: float | None = None) -> list[str]:
    """Fuzzy near-matches for a free-typed item.

    Guards against wrongly tagging something as 'Not in range' because of a
    typo or a slightly different wording ("panadol extra" vs "Panadol Extra
    24's"). Returns catalog product names, closest first.
    """
    text = " ".join(str(text or "").split()).strip()
    if not text:
        return []
    n = config.FUZZY_SUGGESTIONS if n is None else n
    cutoff = config.FUZZY_CUTOFF if cutoff is None else cutoff

    idx = _index()
    keys = difflib.get_close_matches(text.casefold(), list(idx.keys()), n=n, cutoff=cutoff)
    hits = [idx[k][0] for k in keys]

    # difflib compares whole strings, so it misses substring hits like
    # "panadol" inside "Panadol Extra 24's". Backfill with prefix/contains.
    if len(hits) < n:
        needle = text.casefold()
        for key, (name, _) in idx.items():
            if len(hits) >= n:
                break
            if needle in key and name not in hits:
                hits.append(name)
    return hits


def classify(item: str) -> dict:
    """Everything the entry form needs to auto-tag one typed/picked item.

    Returns:
        in_catalog     bool  — exact catalog hit
        catalog_match  str   — the canonical catalog name ('' if none)
        category       str   — shelf category, or the fallback category
        status         str   — suggested stock status (staff can override)
        suggestions    list  — fuzzy near-matches, only when not an exact hit
    """
    hit = lookup(item)
    if hit:
        name, shelf = hit
        category = shelf if shelf in config.CATEGORIES else config.CATEGORY_FALLBACK
        return {
            "in_catalog": True,
            "catalog_match": name,
            "category": category,
            "status": config.STATUS_RESTOCK,
            "suggestions": [],
        }
    return {
        "in_catalog": False,
        "catalog_match": "",
        "category": config.CATEGORY_FALLBACK,
        "status": config.STATUS_NEW_RANGE,
        "suggestions": suggest(item),
    }
