"""
Central configuration for the Walk-In Demand Tracker.

This is the ONE file you edit to adapt the app to your own operation, or to
re-skin it entirely for a different sector (a supermarket, a hardware store,
a clinic front desk...). Nothing sector-specific should live outside this file.

Everything here is plain Python data, so it is safe to hand to a non-developer.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# 1. Identity / branding
# --------------------------------------------------------------------------- #
APP_NAME = "Pharmacy Direct — Walk-In Demand Tracker"
APP_ICON = "💊"
ORG_NAME = "Pharmacy Direct"

# Local timezone used for every timestamp the app writes and displays.
# Ghana = "Africa/Accra". Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
TIMEZONE = "Africa/Accra"

# Currency for the optional "estimated value of the sale you missed" field.
CURRENCY_CODE = "GHS"
CURRENCY_SYMBOL = "₵"

# --------------------------------------------------------------------------- #
# 2. Branches
#    >>> EDIT THESE to your real branch names. Keep them stable once staff
#        start logging, because past records store the name as text.
# --------------------------------------------------------------------------- #
BRANCHES = [
    "Adenta Branch",
    "Atomic Branch",
]

# --------------------------------------------------------------------------- #
# 3. Staff, per branch
#    Staff pick their name from a dropdown after entering the branch PIN.
#    "Other" is always appended automatically so nobody is ever blocked.
#    >>> EDIT THESE with real first names / initials.
# --------------------------------------------------------------------------- #
# Optional known-staff rosters per branch. Leave a branch's list empty to make
# the sign-in a free-text "Your name" box (no pre-selected default). Populate a
# list to offer those names as quick-pick options instead.
STAFF_BY_BRANCH = {
    "Adenta Branch": [],
    "Atomic Branch": [],
}

# --------------------------------------------------------------------------- #
# 4. What kind of item was requested (buying-decision categories)
# --------------------------------------------------------------------------- #
# The cleaned category taxonomy the app uses everywhere. build_catalog.py
# normalises the raw inventory's messy categories (case variants, synonyms,
# blanks) onto exactly these buckets, so a category auto-filled from the catalog
# and one picked by hand share the same vocabulary. Keep the two in sync.
CATEGORIES = [
    "OTC",
    "Pharmacy medicine",
    "Prescription medicine",
    "Restricted medicine",
    "Cosmetics",
    "Herbal",
    "Baby & infant",
    "Food, drinks & essentials",
    "Other / uncategorised",
]
CATEGORY_FALLBACK = CATEGORIES[-1]

# --------------------------------------------------------------------------- #
# 5. Stock status of the requested item.
#    This is the single most valuable field for buying decisions:
#      - "Out of stock"  -> you carry it, you just ran out  -> RESTOCK faster
#      - "Not in range"  -> you have never stocked it        -> consider ADDING
#    While catalog auto-matching is off, staff choose this by hand.
#    The first entry is treated as the default in the form.
# --------------------------------------------------------------------------- #
STATUSES = [
    "Out of stock (we normally carry it)",
    "Not in range (we've never stocked it)",
    "Not sure",
]
STATUS_RESTOCK = STATUSES[0]
STATUS_NEW_RANGE = STATUSES[1]

# Short labels used on charts so the axis stays readable.
STATUS_SHORT = {
    STATUSES[0]: "Out of stock",
    STATUSES[1]: "Not in range",
    STATUSES[2]: "Not sure",
}

# --------------------------------------------------------------------------- #
# 5b. Brand & chart palette
#
# Taken from the Pharmacy Direct logo: amber #F6A925 and navy #01528A.
#
# The raw brand colours are used for UI chrome (headers, sidebar, buttons) but
# they are NOT legal as chart marks: amber sits at OKLCH L 0.79 (only 1.93:1 on
# white) and navy at L 0.428 — both outside the 0.43–0.77 lightness band. The
# chart values below hold the brand hue and chroma and move only lightness
# ("snap to passing"), then pass all six data-viz checks:
#
#   light  #CD8300 / #02538B — CVD ΔE 28.2 protan, 35.3 normal, contrast ≥3:1
#   dark   #CA8000 / #5598D5 — CVD ΔE 23.4 protan, 25.8 normal, contrast ≥3:1
#
# Re-validate with the dataviz skill's scripts/validate_palette.js if you
# change any of these. Do not eyeball replacements.
# --------------------------------------------------------------------------- #
BRAND_AMBER = "#F6A925"   # logo gold — UI accents only, never a chart fill
BRAND_NAVY = "#01528A"    # logo navy — headers, sidebar, primary text
BRAND_NAVY_DARK = "#013A62"
BRAND_NAVY_TINT = "#E8F0F7"
BRAND_AMBER_TINT = "#FDF3E0"

INK = "#16202B"           # primary text
INK_MUTED = "#5B6B7C"     # secondary/axis text
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F5F8FB"
BORDER = "#DEE6EE"

# Chart marks. "Not sure" is deliberately a neutral: it is an unknown/residual
# bucket, not an identity hue, so it stays recessive rather than competing.
STATUS_COLORS = {
    "Out of stock": "#CD8300",   # brand amber, snapped into the lightness band
    "Not in range": "#02538B",   # brand navy, snapped into the lightness band
    "Not sure": "#8A8F98",       # neutral — unknown, not a third identity hue
}

# Dark-mode steps, validated against surface #12181F. Kept here so a future
# dark theme uses selected steps rather than an automatic flip of the above.
STATUS_COLORS_DARK = {
    "Out of stock": "#CA8000",
    "Not in range": "#5598D5",
    "Not sure": "#9AA0A6",
}

# Single-series charts use one colour (never a value-ramp across nominal bars).
SERIES_PRIMARY = "#02538B"
GRID_COLOR = "#E9EEF4"

# --------------------------------------------------------------------------- #
# 6. Wording (kept in one place so the app can be re-skinned for other sectors
#    without touching any logic — e.g. "client"/"customer", "item"/"product").
# --------------------------------------------------------------------------- #
LABELS = {
    "record": "request",          # one logged event
    "records": "requests",
    "item": "item",               # the thing the customer asked for
    "customer": "customer",
    "log_verb": "Log",            # button/menu verb
}

# --------------------------------------------------------------------------- #
# 7. Storage (Google Sheet worksheet / local CSV filename).
#    The spreadsheet URL + service-account credentials live in secrets, not here.
# --------------------------------------------------------------------------- #
WORKSHEET_NAME = "requests"
LOCAL_CSV_PATH = "data/requests.csv"   # used automatically when no cloud secrets exist

# Product catalog used for autocomplete + auto-tagging. Generated from the
# Adenta stock-taking master list by `python build_catalog.py`. This file IS
# committed, because Streamlit Cloud can only read files inside the repo.
CATALOG_CSV_PATH = "data/catalog.csv"

# Sentinel shown at the top of the catalog picker for items we don't stock at
# all. Staff type those in the free-text box instead — never a dead end.
CATALOG_NOT_LISTED = "🆕 Not in our catalog — type it below"

# How many fuzzy "did you mean…?" suggestions to offer on a free-text entry,
# and how close a match must be (0-1) to be worth showing.
FUZZY_SUGGESTIONS = 3
FUZZY_CUTOFF = 0.72

# --------------------------------------------------------------------------- #
# 8. Canonical column order for every stored record. Do not reorder casually —
#    the Google Sheet header row is written from this list.
# --------------------------------------------------------------------------- #
COLUMNS = [
    "request_id",       # uuid, primary key
    "timestamp_iso",    # when it was logged (local tz, ISO 8601)
    "branch",
    "staff",
    "item_raw",         # exactly what staff typed
    "item_clean",       # whitespace-normalised display form
    "in_catalog",       # bool: matched a product on our shelves
    "catalog_match",    # canonical catalog name when matched, else ""
    "category",
    "quantity",
    "status",           # one of STATUSES
    "est_value",        # optional: value of the missed sale, in CURRENCY_CODE
    "customer_contact", # optional: phone, for "we've got it now" callback
    "notify_customer",  # bool: customer asked to be told when it arrives
    "notes",
    "resolved",         # bool: GM has actioned this (restocked / added to range)
    "resolved_at",      # ISO timestamp when marked resolved, else ""
]
