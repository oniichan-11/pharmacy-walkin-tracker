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
            "title": {"font": "Sora, Inter, sans-serif", "fontWeight": 600,
                      "color": config.INK, "fontSize": 14, "anchor": "start"},
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@400;500;600;700&display=swap');

/* Body = clean grotesque (Inter); display/headings = geometric (Sora).
   A two-face pairing, echoing the display+text split of premium pharma sites,
   in the Pharmacy Direct navy/amber palette. */
html, body, [class*="st-"], button, input, textarea, select {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}}

/* White-dominant canvas: structure comes from whitespace + hairlines, not
   grey fills. */
.stApp {{ background: {c.SURFACE}; }}

.block-container {{
    padding-top: 2.4rem;
    padding-bottom: 4rem;
    max-width: 1220px;
}}

/* Airy, light-weight display headings. High-specificity selectors so they win
   over Streamlit's default heading styles. */
h1, h2, h3, h4,
[data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3, [data-testid="stMarkdownContainer"] h4,
[data-testid="stHeading"] {{
    font-family: 'Sora', 'Inter', system-ui, sans-serif !important;
    color: {c.INK}; letter-spacing: -0.02em; font-weight: 600;
}}
[data-testid="stMarkdownContainer"] h2 {{ font-size: 1.5rem; }}
[data-testid="stMarkdownContainer"] h3 {{ font-size: 1.18rem; }}
p, span, label, li {{ font-weight: 400; }}

/* ---- Brand hero header ------------------------------------------------- */
.pd-header {{
    position: relative; overflow: hidden;
    display: flex; align-items: center; gap: 1.1rem;
    background: linear-gradient(100deg, {c.BRAND_NAVY} 0%, {c.BRAND_NAVY_DARK} 100%);
    border-radius: 20px;
    padding: 1.5rem 1.9rem;
    margin-bottom: 1.8rem;
    box-shadow: 0 10px 30px -12px rgba(1,82,138,0.45);
}}
/* soft amber glow, top-right — a quiet nod to the logo's second colour */
.pd-header::after {{
    content: ""; position: absolute; top: -60%; right: -8%;
    width: 320px; height: 320px; border-radius: 50%;
    background: radial-gradient(circle, {c.BRAND_AMBER}33 0%, transparent 70%);
}}
.pd-header .pd-bar {{
    width: 6px; align-self: stretch; border-radius: 6px;
    background: {c.BRAND_AMBER}; flex: none;
}}
.pd-header h1 {{
    font-family: 'Sora', sans-serif;
    color: #fff; font-size: 1.7rem; font-weight: 600; margin: 0;
    line-height: 1.15; letter-spacing: -0.02em;
}}
.pd-header p {{
    color: rgba(255,255,255,0.82); font-size: 0.92rem; margin: 0.35rem 0 0 0;
    max-width: 60ch;
}}

/* ---- Sidebar ---------------------------------------------------------- */
section[data-testid="stSidebar"] {{
    background: #fff;
    border-right: 1px solid {c.BORDER};
}}
section[data-testid="stSidebar"] .pd-side-meta {{
    background: {c.SURFACE_ALT};
    border: 1px solid {c.BORDER};
    border-radius: 14px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.6rem;
}}
section[data-testid="stSidebar"] .pd-side-meta .k {{
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.07em;
    color: {c.INK_MUTED}; font-weight: 600;
}}
section[data-testid="stSidebar"] .pd-side-meta .v {{
    font-size: 0.95rem; color: {c.INK}; font-weight: 600; margin-bottom: 0.5rem;
}}
section[data-testid="stSidebar"] .pd-side-meta .v:last-child {{ margin-bottom: 0; }}

/* ---- Stat tiles ------------------------------------------------------- */
div[data-testid="stMetric"] {{
    background: #fff;
    border: 1px solid {c.BORDER};
    border-radius: 18px;
    padding: 1.15rem 1.25rem 1rem;
    box-shadow: 0 6px 20px -14px rgba(22,32,43,0.4);
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}}
div[data-testid="stMetric"]:hover {{
    box-shadow: 0 10px 26px -14px rgba(1,82,138,0.5);
    transform: translateY(-2px);
}}
div[data-testid="stMetric"]::before {{
    content: ""; display: block; width: 26px; height: 3px; border-radius: 3px;
    background: {c.BRAND_NAVY}; margin-bottom: 0.7rem;
}}
div[data-testid="stMetric"] label p {{
    font-size: 0.74rem !important; color: {c.INK_MUTED} !important;
    font-weight: 600 !important; letter-spacing: 0.02em; text-transform: uppercase;
}}
div[data-testid="stMetricValue"] {{
    font-family: 'Sora', sans-serif !important;
    font-size: 2rem !important; font-weight: 600 !important; color: {c.INK} !important;
    font-variant-numeric: proportional-nums;   /* never tabular on big numbers */
    line-height: 1.1;
}}
/* Accent the top keyline of the two tiles that drive buying decisions */
div[data-testid="stColumn"]:nth-child(3) div[data-testid="stMetric"]::before {{
    background: {config.STATUS_COLORS['Out of stock']};
}}
div[data-testid="stColumn"]:nth-child(4) div[data-testid="stMetric"]::before {{
    background: {config.STATUS_COLORS['Not in range']};
}}

/* ---- Panels & tables --------------------------------------------------- */
div[data-testid="stExpander"] {{
    border: 1px solid {c.BORDER}; border-radius: 16px; background: #fff;
    box-shadow: 0 4px 16px -14px rgba(22,32,43,0.35);
}}
div[data-testid="stExpander"] summary {{ font-weight: 500; }}
div[data-testid="stDataFrame"], div[data-testid="stTable"] {{
    border: 1px solid {c.BORDER}; border-radius: 14px; overflow: hidden;
}}

/* ---- Buttons — the pill (fully rounded, light weight, generous padding) - */
.stButton button, .stFormSubmitButton button, div[data-testid="stFormSubmitButton"] button {{
    border-radius: 999px !important;
    padding: 0.6rem 1.5rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em;
    transition: all 0.15s ease;
}}
button[kind="primary"], button[kind="primaryFormSubmit"] {{
    background: {c.BRAND_NAVY} !important;
    color: #fff !important;
    border: 1.6px solid {c.BRAND_NAVY} !important;
    box-shadow: 0 6px 18px -8px rgba(1,82,138,0.55);
}}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {{
    background: {c.BRAND_NAVY_DARK} !important;
    border-color: {c.BRAND_NAVY_DARK} !important;
    transform: translateY(-1px);
    box-shadow: 0 10px 22px -8px rgba(1,82,138,0.6);
}}
button[kind="secondary"], button[kind="secondaryFormSubmit"] {{
    background: #fff !important;
    color: {c.BRAND_NAVY} !important;
    border: 1.6px solid {c.BORDER} !important;
}}
button[kind="secondary"]:hover, button[kind="secondaryFormSubmit"]:hover {{
    border-color: {c.BRAND_NAVY} !important;
    color: {c.BRAND_NAVY_DARK} !important;
}}

/* Inputs: rounded, hairline, navy focus ring */
div[data-baseweb="input"], div[data-baseweb="select"] > div, .stTextArea textarea {{
    border-radius: 11px !important;
}}

/* ---- Nav ---------------------------------------------------------------- */
section[data-testid="stSidebarNav"] a {{ border-radius: 999px; }}
section[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background: {c.BRAND_NAVY_TINT} !important;
    font-weight: 600;
}}
section[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: {c.BRAND_NAVY} !important; }}

/* ---- Section eyebrow label --------------------------------------------- */
.pd-eyebrow {{
    display: inline-block;
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
    color: {c.BRAND_NAVY}; font-weight: 700; margin: 0 0 0.4rem 0;
    padding: 0.15rem 0.6rem; border-radius: 999px;
    background: {c.BRAND_NAVY_TINT};
}}

/* ---- Alerts ------------------------------------------------------------- */
div[data-testid="stAlert"] {{ border-radius: 14px; }}
</style>
"""


def apply() -> None:
    """Inject CSS and register the chart theme. Call once, early in app.py."""
    st.markdown(_css(), unsafe_allow_html=True)
    register_altair()


def header(title: str, subtitle: str = "") -> None:
    """Brand hero header — navy block, amber keyline + glow, airy Sora title."""
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
