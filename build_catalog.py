"""
Build the app's product catalog from the Adenta stock-taking master list.

The deployed app (Streamlit Cloud) can only read files inside its own repo, so
we snapshot the spreadsheet into `data/catalog.csv`, which IS committed. Re-run
this whenever you complete a new stock-take, then commit the refreshed CSV.

    python build_catalog.py
    python build_catalog.py --source "path/to/Master_Inventory_List.xlsx"

Source of truth: "Adenta Stock-taking 28 April List/Master_Inventory_List.xlsx"
— 1,391 unique products compiled from 12 shelf sheets, duplicates merged. The
Adenta shelves also cover ~95% of what the Atomic branch carries, so the same
catalog serves both branches.
"""

from __future__ import annotations

import argparse
import os

import pandas as pd

import config

DEFAULT_SOURCE = os.path.join(
    "..", "Adenta Stock-taking 28 April List", "Master_Inventory_List.xlsx"
)
SHEET = "Master Inventory List"
HEADER_ROW = 4  # 0-indexed: rows 0-3 are title/description/blank


def build(source: str) -> pd.DataFrame:
    df = pd.read_excel(source, sheet_name=SHEET, header=HEADER_ROW, dtype=str)
    df = df.rename(
        columns={"Product Name": "product_name", "Category / Shelf": "category_shelf"}
    )
    df = df[["product_name", "category_shelf"]].copy()

    # Drop blanks and any stray repeated header/total rows.
    df["product_name"] = df["product_name"].astype(str).str.strip()
    df["category_shelf"] = df["category_shelf"].astype(str).str.strip()
    df = df[df["product_name"].notna()]
    df = df[~df["product_name"].isin(["", "nan", "None", "Product Name"])]
    df = df[~df["product_name"].str.upper().eq("TOTAL")]

    # Collapse internal whitespace; de-duplicate case-insensitively.
    df["product_name"] = df["product_name"].str.split().str.join(" ")
    df["match_key"] = df["product_name"].str.casefold()
    df = df.drop_duplicates(subset="match_key", keep="first")

    df = df.sort_values("product_name").reset_index(drop=True)
    return df[["product_name", "category_shelf", "match_key"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--out", default=config.CATALOG_CSV_PATH)
    args = ap.parse_args()

    if not os.path.exists(args.source):
        raise SystemExit(f"Source spreadsheet not found: {args.source}")

    df = build(args.source)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df.to_csv(args.out, index=False)

    print(f"Wrote {len(df)} unique products to {args.out}")
    print("\nItems per category / shelf:")
    counts = df["category_shelf"].value_counts()
    for cat, n in counts.items():
        print(f"  {n:>5}  {cat}")


if __name__ == "__main__":
    main()
