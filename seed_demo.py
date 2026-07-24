"""
Generate realistic demo data into the LOCAL CSV so you can explore the
dashboard before wiring up Google Sheets.

    python seed_demo.py            # ~180 requests over the last 30 days
    python seed_demo.py --rows 400 --days 60

Safe: it only ever writes to data/requests.csv (the local backend). It refuses
to run if Google Sheets secrets are configured, so you can't pollute live data.
"""

from __future__ import annotations

import argparse
import os
import random
import uuid
from datetime import timedelta
from zoneinfo import ZoneInfo
from datetime import datetime

import pandas as pd

import config

# Off-catalog items — things a customer might ask for that we've never stocked.
# These become the "new-range candidate" side of the demo data.
_OFF_CATALOG = [
    "Ozempic 1mg pen",
    "Nicotine patches 21mg",
    "Reusable menstrual cup",
    "Blood pressure monitor (digital, upper arm)",
    "Continuous glucose monitor sensor",
    "Infant nasal aspirator",
    "Gluten-free protein powder",
    "Melatonin 5mg gummies",
]


def _catalog_pool() -> list[tuple[str, str]]:
    """(product_name, category) drawn from the real catalog, if it's been built."""
    path = config.CATALOG_CSV_PATH
    if not os.path.exists(path):
        return []
    cat = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = list(zip(cat["product_name"], cat["category_shelf"]))
    return [(n, c if c in config.CATEGORIES else config.CATEGORY_FALLBACK) for n, c in rows]


def _staff_for(branch: str) -> str:
    return random.choice(config.STAFF_BY_BRANCH.get(branch, ["Staff"]))


def build(rows: int, days: int) -> pd.DataFrame:
    tz = ZoneInfo(config.TIMEZONE)
    now = datetime.now(tz)

    stocked = _catalog_pool()
    if not stocked:
        raise SystemExit(
            "No catalog found. Run `python build_catalog.py` first so the demo "
            "data uses your real product names."
        )
    # A realistic long tail: a small set of items drives most requests.
    hot = random.sample(stocked, k=min(12, len(stocked)))
    warm = random.sample(stocked, k=min(60, len(stocked)))

    records = []
    for _ in range(rows):
        roll = random.random()
        if roll < 0.30:                      # off-catalog -> new-range candidate
            item = random.choice(_OFF_CATALOG)
            category = config.CATEGORY_FALLBACK
            in_catalog, status = False, config.STATUS_NEW_RANGE
        else:                                # stocked -> out-of-stock event
            item, category = random.choice(hot if roll < 0.70 else warm)
            in_catalog, status = True, config.STATUS_RESTOCK
        if random.random() < 0.06:
            status = "Not sure"

        ts = now - timedelta(
            days=random.randint(0, days - 1),
            hours=random.randint(8, 19),
            minutes=random.randint(0, 59),
        )
        branch = random.choice(config.BRANCHES)
        qty = random.choices([1, 1, 1, 2, 3, 5], k=1)[0]
        est = random.choice(["", "", 15, 25, 40, 60, 120])
        resolved = random.random() < 0.25
        records.append(
            {
                "request_id": uuid.uuid4().hex,
                "timestamp_iso": ts.isoformat(timespec="seconds"),
                "branch": branch,
                "staff": _staff_for(branch),
                "item_raw": item,
                "item_clean": item,
                "in_catalog": in_catalog,
                "catalog_match": item if in_catalog else "",
                "category": category,
                "quantity": qty,
                "status": status,
                "est_value": est,
                "customer_contact": "",
                "notify_customer": random.random() < 0.15,
                "notes": "",
                "resolved": resolved,
                "resolved_at": ts.isoformat(timespec="seconds") if resolved else "",
            }
        )
    return pd.DataFrame(records)[config.COLUMNS]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=180)
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()

    # Guard: refuse to run if real Google secrets exist.
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8") as fh:
            if "gcp_service_account" in fh.read():
                raise SystemExit(
                    "Google Sheets secrets detected — refusing to seed demo data. "
                    "Remove them first if you really want local demo data."
                )

    df = build(args.rows, args.days)
    os.makedirs(os.path.dirname(config.LOCAL_CSV_PATH) or ".", exist_ok=True)
    df.to_csv(config.LOCAL_CSV_PATH, index=False)
    print(f"Wrote {len(df)} demo requests to {config.LOCAL_CSV_PATH}")


if __name__ == "__main__":
    main()
