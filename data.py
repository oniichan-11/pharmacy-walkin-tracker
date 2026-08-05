"""
Storage layer for the Walk-In Demand Tracker.

Two interchangeable backends behind one small interface:

  * GoogleSheetBackend  — used automatically when Google credentials are present
                          in st.secrets. Survives Streamlit Cloud redeploys and
                          is directly viewable/editable as a normal spreadsheet.
  * LocalCsvBackend     — used automatically when there are no cloud secrets.
                          Writes data/requests.csv so you can run and demo the
                          app on your laptop with zero setup.

The rest of the app never imports gspread or pandas-io directly; it only calls
the module-level helpers get_requests(), add_request(), save_requests().
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import config


# --------------------------------------------------------------------------- #
# Small shared helpers
# --------------------------------------------------------------------------- #
def now_local() -> datetime:
    """Timezone-aware 'now' in the configured local timezone."""
    return datetime.now(ZoneInfo(config.TIMEZONE))


def normalize_item(raw: str) -> str:
    """Collapse whitespace and trim. Deliberately does NOT change case, so
    product names like 'Benylin 4Flu 200mL' survive intact."""
    return " ".join(str(raw).split()).strip()


def match_key(item: str) -> str:
    """Grouping key so 'Panadol', 'panadol ' and 'PANADOL' count as one item."""
    return normalize_item(item).casefold()


def new_request_row(
    *,
    branch: str,
    staff: str,
    item_raw: str,
    category: str,
    quantity: int,
    status: str,
    in_catalog: bool = False,
    catalog_match: str = "",
    est_value: Optional[float] = None,
    customer_contact: str = "",
    notify_customer: bool = False,
    notes: str = "",
) -> dict:
    """Build one fully-formed record dict matching config.COLUMNS."""
    clean = normalize_item(item_raw)
    return {
        "request_id": uuid.uuid4().hex,
        "timestamp_iso": now_local().isoformat(timespec="seconds"),
        "branch": branch,
        "staff": staff,
        "item_raw": item_raw,
        "item_clean": clean,
        "in_catalog": bool(in_catalog),
        "catalog_match": catalog_match,
        "category": category,
        "quantity": int(quantity),
        "status": status,
        "est_value": "" if est_value in (None, "") else float(est_value),
        "customer_contact": customer_contact.strip(),
        "notify_customer": bool(notify_customer),
        "notes": notes.strip(),
        "resolved": False,
        "resolved_at": "",
    }


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=config.COLUMNS)


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Make a raw frame (from Sheets or CSV, all strings) analysis-ready."""
    if df.empty:
        return _empty_frame()

    # Guarantee every canonical column exists, in order.
    for col in config.COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[config.COLUMNS].copy()

    # Parse via UTC (handles varying offsets / DST safely), then present in the
    # configured local timezone so 'date' and displayed times are local.
    ts = pd.to_datetime(df["timestamp_iso"], errors="coerce", utc=True)
    try:
        ts = ts.dt.tz_convert(config.TIMEZONE)
    except Exception:
        pass
    df["timestamp"] = ts
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
    df["est_value"] = pd.to_numeric(df["est_value"], errors="coerce")

    for boolcol in ("notify_customer", "resolved", "in_catalog"):
        df[boolcol] = (
            df[boolcol].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])
        )

    df["item_clean"] = df["item_clean"].where(
        df["item_clean"].astype(str).str.strip() != "",
        df["item_raw"].map(normalize_item),
    )
    df["match_key"] = df["item_clean"].map(match_key)
    df["date"] = df["timestamp"].dt.date
    return df


# --------------------------------------------------------------------------- #
# Backend selection
# --------------------------------------------------------------------------- #
def _has_supabase_secrets() -> bool:
    try:
        conf = st.secrets["supabase"]
        return bool(conf.get("url")) and bool(conf.get("key"))
    except Exception:
        return False


def _has_gsheet_secrets() -> bool:
    try:
        return "gcp_service_account" in st.secrets and "gsheets" in st.secrets
    except Exception:
        return False


class LocalCsvBackend:
    """Development / offline backend. One CSV on the local filesystem."""

    name = "Local CSV"

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def read(self) -> pd.DataFrame:
        if not os.path.exists(self.path):
            return _empty_frame()
        return pd.read_csv(self.path, dtype=str, keep_default_na=False)

    def append(self, row: dict) -> None:
        df = self.read()
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        self.overwrite(df)

    def overwrite(self, df: pd.DataFrame) -> None:
        out = df.reindex(columns=config.COLUMNS)
        out.to_csv(self.path, index=False)


class GoogleSheetBackend:
    """Production backend. A single worksheet in a Google Sheet, via gspread."""

    name = "Google Sheets"

    def __init__(self):
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        client = gspread.authorize(creds)

        gs_conf = st.secrets["gsheets"]
        spreadsheet = gs_conf.get("spreadsheet") or gs_conf.get("spreadsheet_url")
        if spreadsheet and spreadsheet.startswith("http"):
            sh = client.open_by_url(spreadsheet)
        elif spreadsheet:
            sh = client.open_by_key(spreadsheet)
        else:
            raise RuntimeError("Set [gsheets].spreadsheet in secrets (URL or key).")

        wsname = gs_conf.get("worksheet", config.WORKSHEET_NAME)
        try:
            self.ws = sh.worksheet(wsname)
        except Exception:
            self.ws = sh.add_worksheet(title=wsname, rows=1000, cols=len(config.COLUMNS))

        self._ensure_header()

    def _ensure_header(self) -> None:
        header = self.ws.row_values(1)
        if header != config.COLUMNS:
            self.ws.update([config.COLUMNS], "A1")

    def read(self) -> pd.DataFrame:
        records = self.ws.get_all_records(expected_headers=config.COLUMNS)
        if not records:
            return _empty_frame()
        return pd.DataFrame(records, dtype=str)

    def append(self, row: dict) -> None:
        values = [_cell(row.get(c, "")) for c in config.COLUMNS]
        self.ws.append_row(values, value_input_option="USER_ENTERED")

    def overwrite(self, df: pd.DataFrame) -> None:
        out = df.reindex(columns=config.COLUMNS).fillna("")
        payload = [config.COLUMNS] + [
            [_cell(v) for v in row] for row in out.itertuples(index=False)
        ]
        self.ws.clear()
        self.ws.update(payload, "A1", value_input_option="USER_ENTERED")


def _cell(v) -> str:
    """Serialise a Python value into a spreadsheet-friendly string."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    return str(v)


# --------------------------------------------------------------------------- #
# Supabase (hosted Postgres) — the recommended cloud backend. Uses the REST
# client over HTTPS, so it avoids the IPv4/IPv6 direct-connection issues that
# plague raw Postgres connections from Streamlit Cloud.
# --------------------------------------------------------------------------- #
_TEXT_COLS = [
    "request_id", "timestamp_iso", "branch", "staff", "item_raw", "item_clean",
    "catalog_match", "category", "status", "customer_contact", "notes", "resolved_at",
]
_BOOL_COLS = ["in_catalog", "notify_customer", "resolved"]


def _to_pg(row: dict) -> dict:
    """Serialise one record into JSON types Postgres will accept: proper bools,
    an int quantity, a null (not '') est_value, and strings elsewhere."""
    import math

    def is_nan(v):
        return isinstance(v, float) and math.isnan(v)

    out = {c: row.get(c) for c in config.COLUMNS}

    ev = out.get("est_value")
    out["est_value"] = None if (ev is None or ev == "" or is_nan(ev)) else float(ev)

    try:
        out["quantity"] = int(out.get("quantity") or 1)
    except (TypeError, ValueError):
        out["quantity"] = 1

    for b in _BOOL_COLS:
        v = out.get(b)
        out[b] = v.strip().lower() in ("true", "1", "yes") if isinstance(v, str) else bool(v)

    for s in _TEXT_COLS:
        v = out.get(s)
        out[s] = "" if (v is None or is_nan(v)) else str(v)

    return out


class StorageError(RuntimeError):
    """A storage backend failed in a way the user should see plainly (rather
    than as Streamlit's redacted crash). Carries a safe, actionable message —
    PostgREST error bodies describe schema/auth, never row data."""


def _supabase_guard(op, what: str):
    """Run a Supabase call; on failure raise StorageError with the real reason."""
    try:
        return op()
    except Exception as e:  # noqa: BLE001 — we deliberately surface everything
        code = getattr(e, "code", None)
        msg = getattr(e, "message", None) or str(e) or type(e).__name__
        hint = getattr(e, "hint", None)
        detail = f"Supabase {what} failed"
        if code:
            detail += f" [{code}]"
        detail += f": {msg}"
        if hint:
            detail += f" — hint: {hint}"
        raise StorageError(detail) from None


class SupabaseBackend:
    """Hosted-Postgres backend via the Supabase REST client."""

    name = "Supabase"

    def __init__(self):
        from supabase import create_client

        conf = st.secrets["supabase"]
        self.table_name = conf.get("table", config.WORKSHEET_NAME)
        self.client = create_client(conf["url"], conf["key"])

    def _table(self):
        return self.client.table(self.table_name)

    def read(self) -> pd.DataFrame:
        res = _supabase_guard(lambda: self._table().select("*").execute(), "read")
        rows = res.data or []
        if not rows:
            return _empty_frame()
        return pd.DataFrame(rows)

    def append(self, row: dict) -> None:
        _supabase_guard(lambda: self._table().insert(_to_pg(row)).execute(), "write")

    def overwrite(self, df: pd.DataFrame) -> None:
        """Reconcile the store to `df`: upsert every desired row (by request_id),
        then delete any rows that are no longer present. Avoids the data-loss
        window of a delete-all-then-reinsert."""
        out = df.reindex(columns=config.COLUMNS)
        records = [_to_pg(r) for r in out.to_dict("records")]
        desired = {r["request_id"] for r in records if r.get("request_id")}

        if records:
            _supabase_guard(
                lambda: self._table().upsert(records, on_conflict="request_id").execute(),
                "save",
            )

        current = self.read()
        if not current.empty:
            for rid in current["request_id"].tolist():
                if rid not in desired:
                    _supabase_guard(
                        lambda rid=rid: self._table().delete().eq("request_id", rid).execute(),
                        "delete",
                    )


@st.cache_resource(show_spinner=False)
def _get_backend():
    # Priority: Supabase (recommended cloud DB) -> Google Sheets -> local CSV.
    if _has_supabase_secrets():
        return SupabaseBackend()
    if _has_gsheet_secrets():
        return GoogleSheetBackend()
    return LocalCsvBackend(config.LOCAL_CSV_PATH)


def backend_name() -> str:
    return _get_backend().name


# --------------------------------------------------------------------------- #
# Public interface used by the views
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=30, show_spinner=False)
def get_requests() -> pd.DataFrame:
    """All logged requests, typed and analysis-ready. Cached for 30s; call
    refresh() after any write to see changes immediately."""
    raw = _get_backend().read()
    return _coerce_types(raw)


def refresh() -> None:
    """Invalidate the read cache after a write."""
    get_requests.clear()


def add_request(row: dict) -> None:
    _get_backend().append(row)
    refresh()


def save_requests(df: pd.DataFrame) -> None:
    """Overwrite the whole store (used by the edit/resolve screen)."""
    _get_backend().overwrite(df)
    refresh()
