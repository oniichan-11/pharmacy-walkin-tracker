# Walk-In Demand Tracker

A Python-native Streamlit app for **Pharmacy Direct** to log the items walk-in
customers ask for that you *can't* sell them — across both branches — and turn
that into live **unmet-demand** metrics for restocking and range decisions.

> The most valuable data a shop never captures is the sale it *didn't* make.
> This app captures it in a few seconds at the counter.

---

## What it does

- **Fast counter entry** — a staff member logs an item, type, quantity, and
  whether you normally carry it, in seconds, from a phone or the counter PC.
- **Two-branch aware** — every entry is stamped with branch + staff for
  accountability, and metrics can be sliced per branch.
- **Live dashboard** — most-requested items, restock-vs-new-range split,
  trend over time, breakdown by branch and item type, and estimated missed
  revenue.
- **Action lists** — a ranked "restock priorities" list (things you carry but
  ran out of) and a "new-range candidates" list (things you've never stocked),
  counting only *open* requests so they work as a live to-do.
- **Browse, edit, resolve, export** — an admin view to correct entries, mark
  requests handled, delete, and download everything as CSV or Excel.

---

## Screens

| Screen | Who | Purpose |
|---|---|---|
| **Log a request** | Any staff | The default counter screen. |
| **Dashboard** | Manager / analyst | Live metrics and action lists. |
| **Browse & resolve** | Anyone (view) / Admin (edit) | Full table, export, edit/resolve/delete behind the admin PIN. |

---

## Run it locally (5 minutes, no Google account needed)

```bash
cd walk-in-demand-tracker
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

python build_catalog.py           # build the product catalog (see below)
python seed_demo.py               # optional: fills the dashboard with demo data
streamlit run app.py
```

> If `pip install` fails with an SSL certificate error (common on corporate
> networks), add:
> `--trusted-host pypi.org --trusted-host files.pythonhosted.org`

Open http://localhost:8501. With no secrets file present, the app runs in
**development mode**: it stores data in `data/requests.csv`, any branch PIN is
`0000`, and the admin PIN is `9999`. A banner reminds you of this.

---

## The product catalog

Item entry is backed by a catalog of **1,391 products**, built from
`Adenta Stock-taking 28 April List/Master_Inventory_List.xlsx` (12 shelf sheets,
duplicates merged). The Adenta shelves also cover ~95% of what Atomic carries,
so one catalog serves both branches.

```bash
python build_catalog.py            # regenerate data/catalog.csv
```

`data/catalog.csv` **is committed on purpose** — Streamlit Cloud can only read
files inside the repo, so it cannot reach your OneDrive spreadsheets. Re-run the
script after each stock-take and commit the refreshed file.

### How entry and auto-tagging work

There are two equally valid entry paths, because plenty of requests are for
things you've never stocked — that's the entire point of the app:

| Path | Staff action | Auto-tagged as |
|---|---|---|
| **On our shelves** | Search the catalog and pick the product | `Out of stock` + the product's real shelf category |
| **Not on our shelves** | Type it into the free-text box | `Not in range` + `Other / Not on our shelves` |

Both tags are **overridable** — tick *"Set category / stock status manually"* in
the entry form for edge cases (e.g. a discontinued line).

**Typo guard.** If a free-typed item closely resembles something you *do* stock,
the app still saves it but warns with the near-matches — so a misspelling never
silently inflates your new-range numbers. Typing `panadol` logs the request and
flags that `Panadol ActiFast 24'S`, `Panadol Extra (Haleon)` and
`Panadol Extra 500mg (Haleon)` are on your shelves.

Two columns record the outcome for analysis: `in_catalog` (bool) and
`catalog_match` (the canonical product name when matched).

## Design & branding

The UI follows the Pharmacy Direct logo: **amber `#F6A925`** and **navy `#01528A`**
(sampled from `assets/logo.png`, which is the trimmed logo committed for use in
the sidebar, sign-in screen, and browser tab icon).

**Chrome vs. chart colours are deliberately different values.** The raw brand
colours are used for headers, sidebar, and buttons, but they are *not* legal as
chart marks — amber sits at OKLCH L 0.79 (only 1.93:1 contrast on white) and
navy at L 0.428, both outside the 0.43–0.77 lightness band for data marks. The
chart palette holds each brand hue and chroma and moves only lightness:

| Role | Light | Dark | 
|---|---|---|
| Out of stock (amber) | `#CD8300` | `#CA8000` |
| Not in range (navy) | `#02538B` | `#5598D5` |
| Not sure (neutral) | `#8A8F98` | `#9AA0A6` |

Both modes pass the full check set — lightness band, chroma floor, colourblind
separation (ΔE 28.2 protan / 35.3 normal-vision in light), and ≥3:1 contrast.
**If you change a chart colour, re-validate rather than eyeballing it**; the
values and their rationale are documented in `config.py`.

Other charting rules the dashboard follows, worth preserving if you extend it:

- Colour encodes **status (identity)**, never magnitude — bar length already
  shows magnitude, so colouring by value would waste the identity channel.
- A status keeps its hue under every filter, so "amber = out of stock" stays
  learnable.
- Single-series charts use one colour and no legend; the title names them.
- Every chart has a **"Show as table"** twin — no value is reachable only by
  hovering.
- All filters live in **one row above** the charts, never inside a chart card.
- Bars are capped at 22px with a 4px rounded data-end; gridlines are solid
  hairlines; value labels use ink tokens, never the series colour.

Restyling for another brand is a `config.py` edit: change `BRAND_*`,
`STATUS_COLORS`, and the ink/surface tokens. `theme.py` derives all CSS and
chart defaults from those values and hard-codes no hex of its own.

## Make it yours

Everything sector-specific lives in **`config.py`** — edit it, nothing else:

- `BRANCHES` — your real branch names.
- `STAFF_BY_BRANCH` — staff first names per branch (an "Other" option is always
  added, so no one is ever blocked).
- `CATEGORIES` — the item types you want to slice demand by.
- `TIMEZONE`, `CURRENCY_SYMBOL` — defaults are Ghana (`Africa/Accra`, `₵`).
- `LABELS` — wording (e.g. "customer" vs "client", "item" vs "product") so the
  same app re-skins for a supermarket, hardware store, clinic front desk, etc.

---

## Go live: Supabase (Postgres) + Streamlit Community Cloud

Storage must survive Streamlit Cloud redeploys (its filesystem is wiped on every
reboot, so a plain CSV/SQLite file there silently loses data). The recommended
backend is **Supabase** — free hosted Postgres, no card required, and it doesn't
depend on Google (many Google orgs now block the service-account keys the Sheets
backend needs). Setup is one-time, ~10 minutes.

The app picks its backend automatically from secrets:
**Supabase** (if configured) → **Google Sheets** (if configured) → local CSV.

### 1. Create the Supabase project + table
1. Sign up at <https://supabase.com> (free) → **New project** (pick any region;
   remember the database password, though the app doesn't need it).
2. Open the **SQL Editor** → run this once to create the table:

   ```sql
   create table if not exists requests (
     request_id text primary key,
     timestamp_iso text,
     branch text,
     staff text,
     item_raw text,
     item_clean text,
     in_catalog boolean,
     catalog_match text,
     category text,
     quantity integer,
     status text,
     est_value numeric,
     customer_contact text,
     notify_customer boolean,
     notes text,
     resolved boolean,
     resolved_at text
   );
   ```

### 2. Get the credentials
In **Project Settings**:
- **Data API → Project URL** → this is `url`.
- **API Keys → `service_role`** (reveal + copy) → this is `key`. It's a secret
  used only server-side by the app (Streamlit secrets are never sent to the
  browser); it bypasses row-level security so no policies are needed.

### 3. Configure secrets
Put the following in the app's Secrets (or a git-ignored
`.streamlit/secrets.toml` for local runs):

```toml
[supabase]
url   = "https://YOUR-PROJECT-REF.supabase.co"
key   = "YOUR-SERVICE-ROLE-KEY"
table = "requests"

[branch_pins]
admin_pin = "4321"   # optional; guards the edit/delete controls only
```

Run `streamlit run app.py` — the sidebar should read **"Storage · Supabase"**.

### 4. Deploy to Streamlit Community Cloud (free)
1. Push this folder to a **GitHub** repo. `.gitignore` excludes `secrets.toml`
   and the local CSV, so no secrets are committed.
2. <https://share.streamlit.io> → **New app** → pick the repo/branch, `app.py`.
3. App **Settings → Secrets** → paste the block from step 3 → **Save**.
4. Done. Log a test request, then check the `requests` table in Supabase.

### Getting your data as a spreadsheet
The **Browse & resolve** screen has **CSV** and **Excel** download buttons that
export what's on screen (apply filters first to export a slice, or none for
everything). So you keep spreadsheet access without Google Sheets.

---

## How the data is stored

One row per request, in the `requests` table (Supabase) / worksheet (Sheets) /
CSV (local) — same columns everywhere:

| column | meaning |
|---|---|
| `request_id` | unique id (primary key) |
| `timestamp_iso` | when it was logged (local timezone) |
| `branch`, `staff` | who/where |
| `item_raw`, `item_clean` | what was asked for (raw + whitespace-normalised) |
| `category` | item type |
| `quantity` | how many they wanted |
| `status` | Out of stock / Not in range / Not sure |
| `est_value` | optional value of the missed sale |
| `customer_contact`, `notify_customer` | optional callback details |
| `notes` | free text |
| `resolved`, `resolved_at` | has the GM actioned it |

Export any time from the **Browse & resolve** screen (CSV / Excel), or view the
rows directly in the Supabase Table Editor.

---

## Project layout

```
walk-in-demand-tracker/
├── app.py              # entry point: auth gate + navigation wiring
├── config.py           # ← the ONE file you edit to adapt/re-skin
├── auth.py             # branch-PIN + staff-pick sign-in, admin unlock
├── data.py             # storage layer (Supabase / Google Sheets / local CSV)
├── catalog.py          # catalog lookup, fuzzy matching, auto-tagging
├── build_catalog.py    # rebuild data/catalog.csv from the stock-take xlsx
├── theme.py            # brand CSS + Altair chart defaults (reads config.py)
├── assets/logo.png     # trimmed Pharmacy Direct logo
├── analytics.py        # pure metric functions over the data
├── views/
│   ├── log_request.py  # Screen 1 — counter entry
│   ├── dashboard.py    # Screen 2 — live metrics + action lists
│   └── browse.py       # Screen 3 — browse / export / edit / resolve
├── seed_demo.py        # generate demo data into the local CSV
├── requirements.txt
└── .streamlit/
    ├── config.toml            # theme
    └── secrets.toml.example   # copy → secrets.toml, fill in
```

---

## Roadmap / next steps

- **Per-branch catalogs**: Atomic currently shares the Adenta catalog (~95%
  overlap). If the ranges diverge, `build_catalog.py` can emit one CSV per
  branch and `catalog.py` can select on the signed-in branch.
- **Scheduled digest**: email the manager a weekly "top unmet demand" summary
  (the functions in `analytics.py` are UI-free and ready to reuse).
- **Fulfilment loop**: when a `notify_customer` item is marked resolved, surface
  the callback list.
```
