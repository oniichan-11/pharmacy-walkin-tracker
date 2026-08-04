"""
Build the app's product catalog from the Complete Adenta Inventory export.

The deployed app (Streamlit Cloud) can only read files inside its own repo, so
we snapshot the inventory into `data/catalog.csv`, which IS committed. Re-run
this whenever you export a fresh inventory, then commit the refreshed CSV.

    python build_catalog.py
    python build_catalog.py --source "path/to/Complete Adenta Inventory.csv"

Source of truth: "Complete Adenta Inventory.csv" — the pharmacy's full product
export (~2,870 products). The Adenta range also covers ~95% of the Atomic
branch, so the same catalog serves both branches.

Source columns: id** , name* , category , sale_form , sale_price , qty , expiry
We keep only the product name and a cleaned-up category; price/qty/expiry are
inventory-management fields the demand tracker doesn't need.
"""

from __future__ import annotations

import argparse
import os
import re

import pandas as pd

import config

DEFAULT_SOURCE = os.path.join("..", "Complete Adenta Inventory.csv")

# Raw source categories are inconsistent (case variants, synonyms, blanks).
# Map every raw value onto one clean, deduplicated bucket. Keys are compared
# case-insensitively and trimmed. Anything unmapped falls back to CATEGORY_FALLBACK.
CATEGORY_NORMALISE = {
    "otc": "OTC",
    "pharmacy": "Pharmacy medicine",
    "pharmacy only": "Pharmacy medicine",
    "prescription": "Prescription medicine",
    "restricted": "Restricted medicine",
    "cosmetics": "Cosmetics",
    "herbal": "Herbal",
    "baby essentials": "Baby & infant",
    "food and essentials": "Food, drinks & essentials",
    "food & drink": "Food, drinks & essentials",
    "drinks": "Food, drinks & essentials",
}


def _normalise_category(raw: str) -> str:
    key = " ".join(str(raw or "").split()).strip().casefold()
    return CATEGORY_NORMALISE.get(key, config.CATEGORY_FALLBACK)


def _read_source(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    # Backwards-compatible with the old xlsx master list.
    return pd.read_excel(path, dtype=str)


def build(source: str) -> pd.DataFrame:
    df = _read_source(source)

    # Tolerate the source's exact header names (name* , category).
    name_col = next((c for c in df.columns if c.strip().lower().startswith("name")), None)
    cat_col = next((c for c in df.columns if c.strip().lower() == "category"), None)
    if name_col is None:
        raise SystemExit(f"Could not find a product-name column in {source}: {list(df.columns)}")

    out = pd.DataFrame()
    out["product_name"] = df[name_col].astype(str).str.split().str.join(" ").str.strip()
    out["category_shelf"] = (
        df[cat_col].map(_normalise_category) if cat_col else config.CATEGORY_FALLBACK
    )

    # Drop blanks / stray header rows / junk (names with <2 alphanumerics, e.g.
    # a lone "."), then de-duplicate case-insensitively.
    out = out[out["product_name"].notna()]
    out = out[~out["product_name"].isin(["", "nan", "None"])]
    out = out[~out["product_name"].str.lower().isin(["name", "name*", "product name"])]
    out = out[out["product_name"].apply(lambda s: len(re.sub(r"[^A-Za-z0-9]", "", s)) >= 2)]
    out["match_key"] = out["product_name"].str.casefold()
    out = out.drop_duplicates(subset="match_key", keep="first")

    out = out.sort_values("product_name").reset_index(drop=True)
    return out[["product_name", "category_shelf", "match_key"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--out", default=config.CATALOG_CSV_PATH)
    args = ap.parse_args()

    if not os.path.exists(args.source):
        raise SystemExit(f"Source inventory not found: {args.source}")

    df = build(args.source)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df.to_csv(args.out, index=False)

    print(f"Wrote {len(df)} unique products to {args.out}")
    print("\nItems per category:")
    for cat, n in df["category_shelf"].value_counts().items():
        print(f"  {n:>5}  {cat}")


if __name__ == "__main__":
    main()
