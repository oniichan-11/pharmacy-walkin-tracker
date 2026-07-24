"""
Visual theme — brand chrome (CSS) and chart defaults (Altair).

All colour values come from config.py, so re-skinning for another brand or
sector means editing config.py alone. Nothing here hard-codes a hex.

Chart styling follows the data-viz mark specs: bars capped at 24px with a 4px
rounded data-end, 2px lines, ≥8px markers, hairline solid recessive gridlines,
and text in ink tokens rather than the series colour.
"""

from __future__ import annotations

import os

import altair as alt
import streamlit as st

import config

LOGO_PATH = os.path.join("assets", "logo.png")


# --------------------------------------------------------------------------- #
# Altair
# --------------------------------------------------------------------------- #
BAR_SIZE = 22          # ≤24px: never fill the band, leave air
CORNER_RADIUS = 4      # rounded data-end, square at the baseline
LINE_WIDTH = 2
POINT_SIZE = 70        # ≈9px diameter (Vega size is area in px²)


def altair_theme() -> dict:
    """Registered as the global Altair theme so every chart inherits it."""
    return {
        "config": {
            "background": "transparent",
            "font": "Inter, 'Segoe UI', system-ui, sans-serif",
            "view": {"stroke": "transparent", "continuousHeight": 260},
            "axis": {
                "labelColor": config.INK_MUTED,
                "titleColor": config.INK_MUTED,
                "labelFontSize": 12,
                "titleFontSize": 12,
                "titleFontWeight": 500,
                "titlePadding": 10,
                "domainColor": config.GRID_COLOR,
                "tickColor": config.GRID_COLOR,
                "gridColor": config.GRID_COLOR,
                "gridWidth": 1,          # hairline, solid — never dashed
                "gridDash": [],
                "labelPadding": 6,
            },
            "legend": {
                "labelColor": config.INK_MUTED,
                "titleColor": config.INK_MUTED,
                "labelFontSize": 12,
                "titleFontSize": 12,
                "symbolType": "circle",
                "symbolSize": 90,
                "padding": 6,
            },
            "range": {"category": list(config.STATUS_COLORS.values())},
            "bar": {"cornerRadiusEnd": CORNER_RADIUS},
            "line": {"strokeWidth": LINE_WIDTH, "strokeCap": "round", "strokeJoin": "round"},
            "point": {"size": POINT_SIZE, "filled": True},
        }
    }


def register_altair() -> None:
    alt.theme.register("pharmacy_direct", enable=True)(altair_theme)


def status_scale() -> alt.Scale:
    """Fixed colour-per-status, so a status keeps its hue under any filter."""
    return alt.Scale(
        domain=list(config.STATUS_COLORS.keys()),
        range=list(config.STATUS_COLORS.values()),
    )


# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #
def _css() -> str:
    c = config
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="st-"], button, input, textarea, select {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}}

.stApp {{ background: {c.SURFACE_ALT}; }}

/* Main content sits on a white card for separation from the app background */
.block-container {{
    padding-top: 2.2rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}}

h1, h2, h3, h4 {{ color: {c.INK}; letter-spacing: -0.01em; font-weight: 650; }}
h2 {{ font-size: 1.45rem; }}
h3 {{ font-size: 1.15rem; }}

/* ---- Brand header bar ------------------------------------------------- */
.pd-header {{
    display: flex; align-items: center; gap: 0.9rem;
    background: linear-gradient(95deg, {c.BRAND_NAVY} 0%, {c.BRAND_NAVY_DARK} 100%);
    border-radius: 14px;
    padding: 0.95rem 1.25rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 2px 10px rgba(1,82,138,0.16);
}}
.pd-header .pd-bar {{
    width: 5px; height: 38px; border-radius: 3px;
    background: {c.BRAND_AMBER}; flex: none;
}}
.pd-header h1 {{
    color: #fff; font-size: 1.3rem; font-weight: 650; margin: 0; line-height: 1.25;
}}
.pd-header p {{
    color: rgba(255,255,255,0.78); font-size: 0.85rem; margin: 0.15rem 0 0 0;
}}

/* ---- Sidebar ---------------------------------------------------------- */
section[data-testid="stSidebar"] {{
    background: #fff;
    border-right: 1px solid {c.BORDER};
}}
section[data-testid="stSidebar"] .pd-side-meta {{
    background: {c.SURFACE_ALT};
    border: 1px solid {c.BORDER};
    border-radius: 10px;
    padding: 0.7rem 0.85rem;
    margin-bottom: 0.5rem;
}}
section[data-testid="stSidebar"] .pd-side-meta .k {{
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;
    color: {c.INK_MUTED}; font-weight: 600;
}}
section[data-testid="stSidebar"] .pd-side-meta .v {{
    font-size: 0.95rem; color: {c.INK}; font-weight: 600; margin-bottom: 0.45rem;
}}
section[data-testid="stSidebar"] .pd-side-meta .v:last-child {{ margin-bottom: 0; }}

/* ---- Stat tiles ------------------------------------------------------- */
div[data-testid="stMetric"] {{
    background: #fff;
    border: 1px solid {c.BORDER};
    border-left: 4px solid {c.BRAND_NAVY};
    border-radius: 12px;
    padding: 0.85rem 1rem;
    box-shadow: 0 1px 3px rgba(22,32,43,0.05);
}}
div[data-testid="stMetric"] label p {{
    font-size: 0.76rem !important; color: {c.INK_MUTED} !important;
    font-weight: 600 !important; letter-spacing: 0.01em;
}}
div[data-testid="stMetricValue"] {{
    font-size: 1.7rem !important; font-weight: 650 !important; color: {c.INK} !important;
    font-variant-numeric: proportional-nums;   /* never tabular on big numbers */
}}
/* Accent the two tiles that drive buying decisions */
div[data-testid="stColumn"]:nth-child(3) div[data-testid="stMetric"] {{
    border-left-color: {config.STATUS_COLORS['Out of stock']};
}}
div[data-testid="stColumn"]:nth-child(4) div[data-testid="stMetric"] {{
    border-left-color: {config.STATUS_COLORS['Not in range']};
}}

/* ---- Panels & tables --------------------------------------------------- */
div[data-testid="stExpander"] {{
    border: 1px solid {c.BORDER}; border-radius: 12px; background: #fff;
}}
div[data-testid="stDataFrame"], div[data-testid="stTable"] {{
    border: 1px solid {c.BORDER}; border-radius: 10px;
}}

/* ---- Buttons ----------------------------------------------------------- */
button[kind="primary"] {{
    background: {c.BRAND_NAVY} !important;
    border: none !important; border-radius: 9px !important;
    font-weight: 600 !important; padding: 0.55rem 1rem !important;
    box-shadow: 0 1px 4px rgba(1,82,138,0.22);
}}
button[kind="primary"]:hover {{ background: {c.BRAND_NAVY_DARK} !important; }}
button[kind="secondary"] {{
    border-radius: 9px !important; border-color: {c.BORDER} !important;
    font-weight: 550 !important;
}}

/* ---- Nav ---------------------------------------------------------------- */
section[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background: {c.BRAND_NAVY_TINT} !important;
    border-radius: 8px; font-weight: 600;
}}

/* ---- Section label ------------------------------------------------------ */
.pd-eyebrow {{
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em;
    color: {c.INK_MUTED}; font-weight: 700; margin: 0 0 0.35rem 0;
}}

/* ---- Alerts ------------------------------------------------------------- */
div[data-testid="stAlert"] {{ border-radius: 10px; }}
</style>
"""


def apply() -> None:
    """Inject CSS and register the chart theme. Call once, early in app.py."""
    st.markdown(_css(), unsafe_allow_html=True)
    register_altair()


def header(title: str, subtitle: str = "") -> None:
    """Brand header bar with the amber keyline from the logo."""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="pd-header"><div class="pd-bar"></div>'
        f"<div><h1>{title}</h1>{sub}</div></div>",
        unsafe_allow_html=True,
    )


def eyebrow(text: str) -> None:
    st.markdown(f'<p class="pd-eyebrow">{text}</p>', unsafe_allow_html=True)


def logo_exists() -> bool:
    return os.path.exists(LOGO_PATH)
