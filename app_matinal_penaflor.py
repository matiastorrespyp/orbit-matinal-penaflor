"""
ORBIT Matinal PAV Peñaflor — App web completa.
Vendedores: teléfono, ven su zona y envían planificación.
Gerencia: panel completo — objetivos, segmentos, 11T, descuentos, plan vs real.

Contraseñas: vendedores=pav2026 / gerencia=gerencia2026
Orbit © 2026 · Propiedad de Torres Matías
"""

from __future__ import annotations

import json
import math
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# ─────────────────────────────── RUTAS ────────────────────────────────
BASE     = Path(r"C:\Orbit\MATINAL_PENAFLOR")
APP_DATA = BASE / "06_APP_DATA"
CFG      = BASE / "09_CONFIG"
ASSETS   = BASE / "assets"
DS       = BASE / "04_DATASETS_ORBIT"
INT      = BASE / "05_INTELLIGENCE_ORBIT"
INPUTS   = BASE / "01_INPUTS"
HIST     = BASE / "02_HISTORY"

DASHBOARD_JSON = APP_DATA / "dashboard_vendedor.json"
CLIENTES_JSON  = APP_DATA / "cliente_detalle.json"
ALERTAS_JSON   = APP_DATA / "alertas_app.json"
PLAN_JSON      = APP_DATA / "planificacion.json"
VENDEDORES_CSV = CFG / "vendedores_activos.csv"
LOGO_FULL      = ASSETS / "orbit-logo-full.png"
LOGO_MARK      = ASSETS / "orbit-mark.png"

PASS_VENDEDOR = "pav2026"
PASS_GERENCIA = "gerencia2026"

DIAS = {"LU":"Lunes","MA":"Martes","MI":"Miércoles","JU":"Jueves","VI":"Viernes","SA":"Sábado"}

# Mapeo código numérico ↔ clave V-string
VMAP     = {"V3":3,"V4":4,"V6":6,"V7":7,"V8":8,"V9":9,"V10":10}
VMAP_INV = {v:k for k,v in VMAP.items()}
VALID_CODES = set(VMAP.values())

# ─────────────────────────── PAGE CONFIG ──────────────────────────────
st.set_page_config(page_title="ORBIT · Matinal PAV", page_icon="🟢",
                   layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────── CSS ──────────────────────────────────
st.markdown("""
<style>
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main{
  background:#0B0B0B!important;color:#E0E0E0!important;
  font-family:'Inter','Segoe UI',sans-serif;}
[data-testid="stSidebar"]{background:#0f0f0f!important;}
[data-testid="stToolbar"],#MainMenu,footer,header{display:none!important;}
h1,h2,h3,h4{color:#6EC531!important;font-weight:700!important;}
hr{border:none;border-top:1px solid #1E1E1E!important;margin:14px 0;}

/* Login */
.login-wrap{max-width:420px;margin:0 auto;padding:20px 0 60px;}
.login-card{background:#111;border:1px solid #1E1E1E;border-radius:20px;padding:36px 32px 28px;margin-top:16px;}
.login-tagline{color:#555;font-size:.8rem;text-align:center;margin-bottom:28px;letter-spacing:.05em;}

/* Hero */
.hero{background:linear-gradient(135deg,#0d1f00 0%,#111 60%);border:1px solid #2a4a0d;
  border-radius:16px;padding:22px 24px;margin-bottom:16px;}
.hero-avance{font-size:3rem;font-weight:900;line-height:1;color:#6EC531;}
.hero-avance.warn{color:#F5A623;}.hero-avance.danger{color:#E05252;}
.hero-label{font-size:.72rem;color:#555;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;}
.hero-sub{font-size:.78rem;color:#888;margin-top:6px;}

/* KPI pills */
.kpi-row{display:flex;gap:8px;margin-bottom:16px;}
.kpi-pill{flex:1;background:#111;border:1px solid #1E1E1E;border-radius:12px;padding:12px 10px;text-align:center;}
.kpi-pill-val{font-size:1.3rem;font-weight:700;color:#6EC531;line-height:1.1;}
.kpi-pill-val.warn{color:#F5A623;}.kpi-pill-val.danger{color:#E05252;}
.kpi-pill-lbl{font-size:.65rem;color:#555;text-transform:uppercase;letter-spacing:.06em;margin-top:3px;}

/* Progress bar */
.pbar-wrap{background:#1a1a1a;border-radius:4px;height:5px;margin-top:6px;overflow:hidden;}
.pbar-fill{height:100%;border-radius:4px;}
.pg{background:#6EC531;}.pw{background:#F5A623;}.pr{background:#E05252;}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"]{
  background:#111!important;border-radius:12px;padding:4px;gap:2px;border:1px solid #1E1E1E;}
[data-testid="stTabs"] [data-baseweb="tab"]{
  background:transparent!important;color:#666!important;border-radius:10px!important;
  font-size:.8rem!important;padding:7px 12px!important;}
[data-testid="stTabs"] [aria-selected="true"]{background:#6EC531!important;color:#000!important;font-weight:700!important;}
[data-testid="stTabPanel"]{padding-top:14px!important;}

/* Cliente cards */
.cli-card{display:flex;align-items:stretch;border-radius:12px;overflow:hidden;margin-bottom:7px;
  background:#111;border:1px solid #1E1E1E;}
.cli-bar{width:4px;flex-shrink:0;}
.cli-body{padding:11px 14px;flex:1;}
.cli-nombre{font-size:.86rem;font-weight:600;color:#DDD;}
.cli-meta{font-size:.72rem;color:#555;margin-top:2px;}
.cli-action{font-size:.72rem;color:#6EC531;margin-top:4px;}
.cli-badge{display:inline-block;font-size:.63rem;font-weight:700;padding:2px 8px;border-radius:20px;margin-left:6px;}
.br{background:#3a0000;color:#FF6B6B;}.ba{background:#2a1900;color:#F5A623;}.bg{background:#0a2500;color:#6EC531;}

/* Alertas */
.alert-card{background:#130000;border-left:3px solid #E05252;border-radius:0 10px 10px 0;padding:11px 14px;margin-bottom:7px;}
.alert-card.opor{background:#0a1400;border-left-color:#6EC531;}
.alert-title{font-size:.78rem;color:#FF6B6B;font-weight:600;}
.alert-card.opor .alert-title{color:#6EC531;}
.alert-cliente{font-size:.84rem;font-weight:600;color:#DDD;}
.alert-accion{font-size:.72rem;color:#666;margin-top:3px;}

/* Plan */
.plan-enviado{background:#0a1a00;border:1px solid #6EC531;border-radius:12px;padding:16px 18px;margin-bottom:12px;}
.plan-pendiente{background:#161616;border:1px dashed #333;border-radius:12px;padding:12px 16px;margin-bottom:7px;color:#555;font-size:.84rem;}

/* Tablas comparativas */
.gtable{width:100%;border-collapse:collapse;font-size:.8rem;margin:10px 0;}
.gtable th{background:#111;color:#555;font-size:.67rem;text-transform:uppercase;
  letter-spacing:.07em;padding:8px 10px;border-bottom:1px solid #1E1E1E;text-align:right;}
.gtable th:first-child{text-align:left;}
.gtable td{padding:8px 10px;border-bottom:1px solid #141414;text-align:right;vertical-align:middle;}
.gtable td:first-child{text-align:left;color:#888;font-weight:500;}
.gtable tr:hover td{background:#111;}
.t-plan{color:#aaa;}.t-real{color:#6EC531;font-weight:600;}
.t-pos{color:#6EC531;}.t-neg{color:#E05252;}.t-neu{color:#555;}
.t-head{font-size:.7rem;color:#444;}

/* Vendedor rows */
.vrow{background:#111;border:1px solid #1A1A1A;border-radius:12px;padding:12px 16px;margin-bottom:8px;
  display:flex;align-items:center;gap:12px;}
.vrow-name{flex:1;font-weight:600;font-size:.88rem;}
.vrow-meta{font-size:.71rem;color:#555;}
.vrow-av{font-size:1.1rem;font-weight:800;min-width:60px;text-align:right;}

/* KPI gerencia */
.kger{background:#111;border:1px solid #1E1E1E;border-radius:14px;padding:18px 14px;text-align:center;margin-bottom:10px;}
.kger-val{font-size:1.6rem;font-weight:800;color:#6EC531;line-height:1.1;}
.kger-val.warn{color:#F5A623;}.kger-val.danger{color:#E05252;}
.kger-lbl{font-size:.67rem;color:#555;text-transform:uppercase;letter-spacing:.07em;margin-bottom:5px;}
.kger-sub{font-size:.69rem;color:#444;margin-top:4px;}

/* Sección headers */
.sec-header{font-size:.7rem;color:#444;text-transform:uppercase;letter-spacing:.1em;
  padding:6px 0;margin:16px 0 8px;border-bottom:1px solid #1A1A1A;}

/* Descuento marca row */
.desc-row{background:#111;border:1px solid #1A1A1A;border-radius:10px;padding:10px 14px;
  margin-bottom:6px;display:flex;align-items:center;gap:10px;}
.desc-marca{flex:1;font-weight:600;font-size:.84rem;}
.desc-inv{color:#F5A623;font-weight:700;font-size:.9rem;min-width:90px;text-align:right;}
.desc-roi{font-size:.72rem;color:#555;}

/* Sin cargo badge */
.sc-row{background:#130a00;border:1px solid #3a2000;border-radius:10px;padding:10px 14px;margin-bottom:6px;}
.sc-cliente{font-weight:600;font-size:.84rem;color:#DDD;}
.sc-meta{font-size:.71rem;color:#666;margin-top:2px;}

/* ── Objetivos cards ── */
.vobj-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:4px;}
.vobj-card{background:#111;border:1px solid #1E1E1E;border-radius:18px;overflow:hidden;
  transition:border-color .2s;}
.vobj-card:hover{border-color:#2a2a2a;}
.vobj-head{display:flex;align-items:center;gap:8px;padding:11px 15px;
  background:#0d0d0d;border-bottom:1px solid #161616;}
.vobj-badge{font-weight:900;font-size:.76rem;padding:3px 11px;border-radius:20px;letter-spacing:.02em;}
.vobj-name{flex:1;font-weight:700;font-size:.86rem;color:#CCC;letter-spacing:.01em;}
.vobj-zona-tag{font-size:.66rem;color:#444;background:#141414;padding:2px 9px;
  border-radius:10px;border:1px solid #1E1E1E;}
.vobj-body{display:flex;}
.vobj-main{flex:1;padding:14px 15px 13px;}
.vobj-avrow{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:7px;}
.vobj-pct{font-size:2.6rem;font-weight:900;line-height:1;letter-spacing:-.02em;}
.vobj-brecha-box{text-align:right;}
.vobj-br-lbl{font-size:.59rem;color:#333;text-transform:uppercase;letter-spacing:.07em;}
.vobj-br-val{font-size:.92rem;font-weight:700;margin-top:1px;}
.vobj-pbar{background:#181818;border-radius:3px;height:3px;margin-bottom:13px;overflow:hidden;}
.vobj-pbar-fill{height:100%;border-radius:3px;}
.vobj-m4{display:grid;grid-template-columns:1fr 1fr;gap:5px;}
.vobj-m4-item{background:#0d0d0d;border:1px solid #161616;border-radius:9px;padding:7px 10px;}
.vobj-m4-val{font-size:.84rem;font-weight:700;color:#CCC;}
.vobj-m4-lbl{font-size:.59rem;color:#393939;text-transform:uppercase;letter-spacing:.06em;margin-top:2px;}
.vobj-spark{width:115px;flex-shrink:0;padding:12px 12px 10px;border-left:1px solid #161616;
  display:flex;flex-direction:column;}
.vobj-sp-title{font-size:.59rem;color:#2e2e2e;text-transform:uppercase;letter-spacing:.09em;margin-bottom:7px;}
.vobj-tend{font-size:1rem;text-align:center;margin-top:5px;}

/* ── Resumen objetivos banner ── */
.obj-banner{background:linear-gradient(135deg,#0c1a00 0%,#101010 70%);
  border:1px solid #1E2E0E;border-radius:14px;padding:14px 20px;
  display:flex;gap:0;margin-bottom:16px;}
.obj-ban-item{flex:1;text-align:center;padding:0 10px;}
.obj-ban-item+.obj-ban-item{border-left:1px solid #1A2A0A;}
.obj-ban-val{font-size:1.4rem;font-weight:800;color:#6EC531;line-height:1.1;}
.obj-ban-val.warn{color:#F5A623;}.obj-ban-val.danger{color:#E05252;}
.obj-ban-lbl{font-size:.62rem;color:#3a3a3a;text-transform:uppercase;letter-spacing:.08em;margin-top:3px;}

/* ── Segment breakdown cards ── */
.seg-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:8px;margin:10px 0 14px;}
.seg-card{background:#111;border:1px solid #1E1E1E;border-radius:12px;padding:11px 12px;}
.seg-card-title{font-size:.61rem;color:#444;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;}
.seg-cmp{font-size:1.4rem;font-weight:900;color:#6EC531;line-height:1;}
.seg-ncmp{font-size:1.4rem;font-weight:900;color:#E05252;line-height:1;}
.seg-lbl{font-size:.6rem;color:#2E2E2E;margin-top:1px;}

/* ── 11T client rows ── */
.t11-row{background:#111;border:1px solid #1A1A1A;border-radius:10px;padding:10px 13px;margin-bottom:5px;}
.t11-nombre{font-size:.84rem;font-weight:600;color:#DDD;}
.t11-marcas{font-size:.72rem;color:#F5A623;margin-top:4px;line-height:1.6;}
.t11-ok{font-size:.72rem;color:#6EC531;margin-top:3px;}

/* ── Gerencia zona/dia ── */
.vger-card{background:#111;border:1px solid #1A1A1A;border-radius:14px;padding:14px 16px;margin-bottom:10px;}
.vger-head{display:flex;align-items:center;gap:10px;margin-bottom:10px;}
.vger-vid{font-weight:900;font-size:.84rem;padding:3px 12px;border-radius:20px;}
.vger-name{flex:1;font-weight:700;font-size:.88rem;color:#CCC;}
.perdida-row{background:#130000;border-left:3px solid #E05252;border-radius:0 10px 10px 0;
  padding:10px 14px;margin-bottom:5px;}
.perdida-cli{font-size:.84rem;font-weight:600;color:#DDD;}
.perdida-meta{font-size:.71rem;color:#666;margin-top:2px;}

/* Footer */
.orbit-footer{text-align:center;color:#2a2a2a;font-size:.68rem;margin-top:50px;
  padding-top:14px;border-top:1px solid #141414;}

/* Streamlit elements */
.stButton>button{background:#6EC531!important;color:#000!important;font-weight:700!important;
  border:none!important;border-radius:10px!important;width:100%;padding:10px!important;}
.stButton>button:hover{background:#5aaa27!important;}
.stTextInput input,.stNumberInput input,.stTextArea textarea,[data-baseweb="select"]{
  background:#161616!important;color:#EEE!important;border-color:#2a2a2a!important;border-radius:10px!important;}
label{color:#888!important;font-size:.8rem!important;}
[data-testid="stExpander"]{background:#111!important;border:1px solid #1E1E1E!important;border-radius:12px!important;}
[data-testid="stMetricValue"]{color:#6EC531!important;font-weight:700!important;}
[data-testid="stMetricLabel"]{color:#555!important;}
[data-testid="stMetric"]{background:#111;border-radius:10px;padding:12px;border:1px solid #1E1E1E;}
</style>
""", unsafe_allow_html=True)


# ─────────────────────── HELPERS GENERALES ────────────────────────────

def sf(v, d=0.0):
    if v is None: return d
    try:
        f = float(v); return d if math.isnan(f) else f
    except: return d

def sb(v): return bool(sf(v))

def ss(v, d=""):
    if v is None: return d
    if isinstance(v, float): return d if math.isnan(v) else (str(int(v)) if v == int(v) else str(v))
    return str(v)

def fmt(v, d=0.0):
    v = sf(v, d)
    if v >= 1_000_000: return f"$ {v/1_000_000:.1f}M"
    if v >= 1_000: return f"$ {v/1_000:.0f}K"
    return f"$ {int(v):,}"

def pct_str(v): return f"{sf(v):.1f}%"

def av_cls(p):
    p = sf(p)
    return "" if p >= 85 else ("warn" if p >= 60 else "danger")

def pbar(p):
    w = min(max(sf(p), 0), 100)
    c = "pg" if w >= 85 else ("pw" if w >= 60 else "pr")
    return f'<div class="pbar-wrap"><div class="pbar-fill {c}" style="width:{w}%"></div></div>'

def dsv_html(real, plan, fmt_fn=None):
    d = sf(real) - sf(plan)
    if sf(plan) == 0: return '<span class="t-neu">—</span>'
    pct = d / sf(plan) * 100
    fn = fmt_fn or (lambda x: str(abs(int(x))))
    v = fn(abs(d))
    pct_s = f" ({pct:+.1f}%)"
    if d >= 0: return f'<span class="t-pos">+{v}{pct_s}</span>'
    return f'<span class="t-neg">-{v}{pct_s}</span>'


# ─────────────────────── CARGA DE DATOS ───────────────────────────────

@st.cache_data(ttl=30)
def load_json_file(path: Path):
    if not path.exists(): return []
    with open(path, encoding="utf-8") as f: return json.load(f)


def _read_csv(path: Path, enc="utf-8-sig") -> pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    try: return pd.read_csv(path, encoding=enc, sep=None, engine="python")
    except: return pd.DataFrame()


@st.cache_data(ttl=60)
def load_volumen() -> pd.DataFrame:
    df = _read_csv(DS / "mod_volumen_vendedor.csv")
    df.columns = df.columns.str.lstrip("﻿").str.strip()
    for c in ["objetivo_mes","acumulado_mes","tendencia_mes","avance_pct",
              "promedio_dia","media_necesaria","venta_ayer"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=60)
def load_ventas_mes() -> pd.DataFrame:
    df = _read_csv(INPUTS / "ventas.csv", enc="latin-1")
    if df.empty: return df
    # REGLA PEÑAFLOR: fecha válida = FechaComprobante (facturación), no FechaEntrega
    df["FechaComprobante"] = pd.to_datetime(df["FechaComprobante"], dayfirst=True, errors="coerce")
    for c in ["ImporteNetoItem","valorDescuento","CantBase"]:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(".", "", regex=False).str.replace(",", "."),
                errors="coerce").fillna(0)
    return df[df["CodVendedor"].isin(VALID_CODES)]


@st.cache_data(ttl=3600)
def load_historial() -> pd.DataFrame:
    df = _read_csv(HIST / "historial_ventas.csv", enc="latin-1")
    if df.empty: return df
    # REGLA PEÑAFLOR: fecha válida = FechaComprobante (facturación), no FechaEntrega
    df["FechaComprobante"] = pd.to_datetime(df["FechaComprobante"], dayfirst=True, errors="coerce")
    df["ImporteNetoItem"] = pd.to_numeric(
        df["ImporteNetoItem"].astype(str).str.replace(".", "", regex=False).str.replace(",", "."),
        errors="coerce").fillna(0)
    return df[df["CodVendedor"].isin(VALID_CODES)]


@st.cache_data(ttl=60)
def load_ccc_seg() -> pd.DataFrame:
    df = _read_csv(DS / "mod_ccc_segmento.csv")
    df.columns = df.columns.str.lstrip("﻿").str.strip()
    for c in ["clientes_con_compra","coberturas_logradas","venta_neta"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=60)
def load_11t() -> pd.DataFrame:
    df = _read_csv(DS / "mod_11_titulares.csv")
    df.columns = df.columns.str.lstrip("﻿").str.strip()
    for c in ["tiene_flag","falta_flag","botellas_mes","importe_mes"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=60)
def load_inversiones() -> pd.DataFrame:
    df = _read_csv(DS / "mod_inversion_desc.csv")
    df.columns = df.columns.str.lstrip("﻿").str.strip()
    for c in ["inversion_total","venta_total","roi_comercial","articulos_con_desc"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=60)
def load_reintegros() -> pd.DataFrame:
    df = _read_csv(DS / "mod_reintegros_ctrl.csv")
    df.columns = df.columns.str.lstrip("﻿").str.strip()
    for c in ["inversion_descuento","venta_generada"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=60)
def load_eficiencia() -> pd.DataFrame:
    df = _read_csv(DS / "mod_eficiencia_desc.csv")
    df.columns = df.columns.str.lstrip("﻿").str.strip()
    for c in ["descuento_pct","valor_descuento","importe_neto"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=60)
def load_real_dia() -> pd.DataFrame:
    """Ventas reales del último día disponible en ventas.csv.
    Fuente de verdad para 'real logrado' cuando no hay snapshot diario."""
    df = _read_csv(INPUTS / "ventas.csv", enc="latin-1")
    if df.empty: return pd.DataFrame()
    # REGLA PEÑAFLOR: fecha válida = FechaComprobante (facturación), no FechaEntrega
    df["FechaComprobante"] = pd.to_datetime(df["FechaComprobante"], dayfirst=True, errors="coerce")
    for c in ["ImporteNetoItem", "CantBase"]:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(".", "", regex=False).str.replace(",", "."),
                errors="coerce").fillna(0)
    df = df[df["CodVendedor"].isin(VALID_CODES)]
    if df.empty: return pd.DataFrame()
    ultima = df["FechaComprobante"].max()
    df_dia = df[df["FechaComprobante"] == ultima].copy()
    rows = []
    for code in VALID_CODES:
        vid = VMAP_INV.get(code)
        if not vid: continue
        sub = df_dia[df_dia["CodVendedor"] == code]
        rows.append({
            "vid":      vid,
            "fecha_real": ultima.strftime("%d/%m/%Y") if pd.notna(ultima) else "—",
            "venta_dia":  float(sub[sub["ImporteNetoItem"] > 0]["ImporteNetoItem"].sum()),
            "ccc_dia":    int(sub[sub["ImporteNetoItem"] > 0]["Cliente"].nunique()),
            "bots_dia":   float(sub["CantBase"].sum()),
            "n_compras":  len(sub[sub["ImporteNetoItem"] > 0]),
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_clientes_hoy() -> list[dict]:
    """clientes_hoy.json — datos enriquecidos por cliente (zona, localidad, estado, kernel)."""
    p = APP_DATA / "clientes_hoy.json"
    if not p.exists(): return load_json_file(CLIENTES_JSON)   # fallback
    with open(p, encoding="utf-8") as f: return json.load(f)


def get_vol_row(df_vol: "pd.DataFrame", vid: str) -> dict:
    """Retorna la fila de mod_volumen_vendedor para un vendedor, o {} si no existe."""
    if df_vol.empty or "vid" not in df_vol.columns: return {}
    sub = df_vol[df_vol["vid"] == vid]
    return sub.iloc[0].to_dict() if not sub.empty else {}


def load_vendedores() -> dict[str, str]:
    if not VENDEDORES_CSV.exists(): return {}
    import csv
    out = {}
    with open(VENDEDORES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("activo","1") == "1":
                out[row["codigo_vendedor"]] = row["nombre_vendedor"].title()
    return out


def get_plan_hoy(vid: str) -> dict | None:
    hoy = date.today().isoformat()
    for p in load_json_file(PLAN_JSON):
        if p.get("vendedor_id") == vid and p.get("fecha") == hoy:
            return p
    return None


def planes_hoy() -> list[dict]:
    hoy = date.today().isoformat()
    return [p for p in load_json_file(PLAN_JSON) if p.get("fecha") == hoy]


def save_plan(plan: dict) -> None:
    planes: list = []
    if PLAN_JSON.exists():
        with open(PLAN_JSON, encoding="utf-8") as f: planes = json.load(f)
    hoy = date.today().isoformat()
    planes = [p for p in planes if not (
        p.get("vendedor_id") == plan["vendedor_id"] and p.get("fecha") == hoy)]
    planes.append(plan)
    with open(PLAN_JSON, "w", encoding="utf-8") as f:
        json.dump(planes, f, ensure_ascii=False, indent=2)


# ─────────── HELPERS PANEL ZONA / DÍA ────────────────────────────────

def _cli_card_vendedor(c: dict, vid: str) -> None:
    """Renderiza tarjeta de cliente para el panel vendedor."""
    nombre    = ss(c.get("cliente_nombre"), "—")
    seg       = ss(c.get("segmento") or c.get("segmento_operativo"), "").replace("_", " ")
    venta     = sf(c.get("venta_mes_actual") or c.get("importe_mes"))
    venta_ant = sf(c.get("venta_mes_anterior"))
    fn        = int(sf(c.get("faltan_11t")))
    cok       = sf(c.get("ccc")) > 0
    accion    = ss(c.get("recomendacion") or c.get("kernel_accion"))
    alerta_d  = ss(c.get("alerta_descuento", ""))
    if vid == "V3" and "AUTO" in seg.upper(): return
    if not cok:   bar, badge = "#E05252", '<span class="cli-badge br">Sin CCC</span>'
    elif fn > 0:  bar, badge = "#F5A623", f'<span class="cli-badge ba">Falta {fn} 11T</span>'
    else:         bar, badge = "#6EC531", '<span class="cli-badge bg">✓ Completo</span>'
    meta_parts = [p for p in [
        seg,
        (fmt(venta) if venta > 0 else (f"Ant: {fmt(venta_ant)}" if venta_ant > 0 else "")),
    ] if p]
    meta     = " · ".join(meta_parts)
    accion_h = f'<div class="cli-action">→ {accion[:120]}</div>' if accion else ""
    alerta_h = f'<div style="font-size:.68rem;color:#F5A623;margin-top:2px">⚠ {alerta_d}</div>' if alerta_d else ""
    st.markdown(
        f'<div class="cli-card" translate="no"><div class="cli-bar" style="background:{bar}"></div>'
        f'<div class="cli-body"><div class="cli-nombre">{nombre}{badge}</div>'
        f'<div class="cli-meta">{meta}</div>{accion_h}{alerta_h}</div></div>',
        unsafe_allow_html=True)


def _render_seg_cards(vid: str, clientes_dia: list) -> None:
    """Tarjetas de desglose por segmento para el día seleccionado."""
    SEGS_MAP = [
        ("TOTAL",          "Total zona",       None),
        ("TRADICIONAL",    "Tradicional",      "TRADICIONAL"),
        ("AUTOSERVICIO",   "Autoservicio",     "AUTOSERVICIO"),
        ("ON_PREMISE_VTK", "On Premise / VTK", "ON_PREMISE_VTK"),
    ]
    html = '<div class="seg-row" translate="no">'
    for _key, titulo, sf_filter in SEGS_MAP:
        if vid == "V3" and sf_filter == "AUTOSERVICIO": continue
        lst  = clientes_dia if sf_filter is None else [c for c in clientes_dia if c.get("segmento") == sf_filter]
        tot  = len(lst)
        cmp  = sum(1 for c in lst if sf(c.get("ccc")) > 0)
        noc  = tot - cmp
        pct  = (cmp / tot * 100) if tot else 0
        bc   = "pg" if pct >= 70 else ("pw" if pct >= 40 else "pr")
        html += f"""
<div class="seg-card">
  <div class="seg-card-title">{titulo}</div>
  <div style="display:flex;align-items:flex-end;gap:10px;margin:4px 0 7px">
    <div><div class="seg-cmp">{cmp}</div><div class="seg-lbl">compraron</div></div>
    <div style="flex:1;height:1px;background:#1E1E1E;margin-bottom:8px"></div>
    <div><div class="seg-ncmp">{noc}</div><div class="seg-lbl">sin compra</div></div>
  </div>
  <div class="pbar-wrap"><div class="pbar-fill {bc}" style="width:{pct:.0f}%"></div></div>
  <div style="font-size:.61rem;color:#2E2E2E;margin-top:3px">{tot} total · {pct:.0f}%</div>
</div>"""
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def _render_11t_dia(vid: str, clientes_dia: list, df_11t: "pd.DataFrame") -> None:
    """11 Titulares por cliente para el día seleccionado."""
    if df_11t.empty or not clientes_dia:
        st.info("Sin datos de 11T para este día.")
        return
    vcode = VMAP.get(vid)
    cli_ids_dia = {str(c.get("cliente_id","")) for c in clientes_dia if c.get("cliente_id")}
    if not cli_ids_dia:
        st.info("Sin identificadores de cliente para cruzar con 11T.")
        return
    df_11t_cols = df_11t.columns.tolist()
    if "vendedor_codigo" not in df_11t_cols or "cliente_id" not in df_11t_cols:
        st.info("Datos de 11T incompletos.")
        return
    df_v   = df_11t[df_11t["vendedor_codigo"] == vcode].copy()
    df_v["_cli_str"] = df_v["cliente_id"].astype(str)
    df_dia = df_v[df_v["_cli_str"].isin(cli_ids_dia)]
    if df_dia.empty:
        st.info("Sin registros 11T para los clientes de este día.")
        return
    missing = df_dia[df_dia["falta_flag"] == 1]
    cli_con_falta = missing["_cli_str"].nunique() if not missing.empty else 0
    cli_ok        = len(cli_ids_dia) - cli_con_falta
    st.markdown(
        f'<div class="seg-row" translate="no">'
        f'<div class="seg-card"><div class="seg-card-title">Con 11T completos</div>'
        f'<div class="seg-cmp" style="font-size:1.8rem">{cli_ok}</div></div>'
        f'<div class="seg-card"><div class="seg-card-title">Les faltan marcas</div>'
        f'<div class="seg-ncmp" style="font-size:1.8rem">{cli_con_falta}</div></div>'
        f'</div>', unsafe_allow_html=True)
    if missing.empty:
        st.success("✅ Todos los clientes del día tienen sus 11 titulares completos.")
        return
    by_cli = (missing.groupby(["_cli_str","cliente_nombre"])["marca_objetivo"]
              .apply(list).reset_index())
    st.markdown('<div class="sec-header">CLIENTES CON MARCAS FALTANTES</div>', unsafe_allow_html=True)
    for _, r in by_cli.iterrows():
        cli_n  = ss(r.get("cliente_nombre","—"))
        marcas = r.get("marca_objetivo", [])
        n_m    = len(marcas)
        marcas_str = " · ".join(str(m) for m in marcas) if marcas else "—"
        st.markdown(
            f'<div class="t11-row" translate="no">'
            f'<div class="t11-nombre">{cli_n} '
            f'<span class="cli-badge ba">Faltan {n_m}</span></div>'
            f'<div class="t11-marcas">📦 {marcas_str}</div>'
            f'</div>', unsafe_allow_html=True)


def _render_sin_cargos(vid: str, df_rei: "pd.DataFrame") -> None:
    """Reintegros / sin cargos pendientes para el vendedor."""
    if df_rei.empty or "vendedor_codigo" not in df_rei.columns:
        st.info("Sin datos de reintegros.")
        return
    vcode = VMAP.get(vid)
    df_v  = df_rei[df_rei["vendedor_codigo"] == vcode]
    if df_v.empty:
        st.success("✅ Sin cargos pendientes para este vendedor.")
        return
    n_ops   = len(df_v)
    tot_inv = sf(df_v["inversion_descuento"].sum()) if "inversion_descuento" in df_v.columns else 0.0
    tot_ven = sf(df_v["venta_generada"].sum())      if "venta_generada"       in df_v.columns else 0.0
    st.markdown(
        f'<div class="kpi-row" translate="no">'
        f'<div class="kpi-pill"><div class="kpi-pill-val danger">{n_ops}</div>'
        f'<div class="kpi-pill-lbl">Pendientes</div></div>'
        f'<div class="kpi-pill"><div class="kpi-pill-val warn">{fmt(tot_inv)}</div>'
        f'<div class="kpi-pill-lbl">Inversión</div></div>'
        f'<div class="kpi-pill"><div class="kpi-pill-val">{fmt(tot_ven)}</div>'
        f'<div class="kpi-pill-lbl">Venta vinculada</div></div>'
        f'</div>', unsafe_allow_html=True)
    if "marca" in df_v.columns:
        st.markdown('<div class="sec-header">MARCAS SIN CARGO</div>', unsafe_allow_html=True)
        marcas_cnt = df_v["marca"].value_counts()
        pills = "".join(
            f'<span style="background:#2a1900;color:#F5A623;padding:3px 11px;'
            f'border-radius:20px;font-size:.72rem;font-weight:700">{m} ({n})</span>'
            for m, n in marcas_cnt.items())
        st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">{pills}</div>',
                    unsafe_allow_html=True)
    st.markdown('<div class="sec-header">DETALLE POR CLIENTE</div>', unsafe_allow_html=True)
    for _, r in df_v.iterrows():
        cli_n   = ss(r.get("cliente_nombre","—"))
        marca   = ss(r.get("marca","—"))
        inv     = sf(r.get("inversion_descuento"))
        ven     = sf(r.get("venta_generada"))
        per_or  = ss(r.get("periodo_origen",""))
        st.markdown(
            f'<div class="sc-row" translate="no">'
            f'<div class="sc-cliente">{cli_n}'
            f'<span style="color:#555;font-size:.7rem"> · {marca}</span></div>'
            f'<div class="sc-meta">Desc pendiente: <span style="color:#F5A623;font-weight:700">{fmt(inv)}</span>'
            f' · Venta: {fmt(ven)}'
            f'{f" · Per. origen: {per_or}" if per_or else ""}</div>'
            f'</div>', unsafe_allow_html=True)


# ─────────────────────────── LOGIN ────────────────────────────────────

def render_login() -> None:
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    if LOGO_FULL.exists(): st.image(str(LOGO_FULL), width=220)
    else: st.markdown('<div style="font-size:2rem;font-weight:900;color:#6EC531;text-align:center">ORBIT</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<p class="login-tagline">MATINAL PAV · PEÑAFLOR</p>', unsafe_allow_html=True)

    vendedores = load_vendedores()
    GERENCIA_OPT = "👔 GERENCIA"
    labels_v = [f"{k} · {v}" for k, v in vendedores.items()]
    sel = st.selectbox("Perfil", ["— Seleccioná —", GERENCIA_OPT] + labels_v, key="sel_login")
    pwd = st.text_input("Contraseña", type="password", placeholder="Ingresá tu clave", key="pwd_login")
    st.markdown(
        '<div style="font-size:.69rem;color:#444;margin-top:-8px;margin-bottom:12px">'
        f'Vendedores: <code>{PASS_VENDEDOR}</code> · Gerencia: <code>{PASS_GERENCIA}</code>'
        '</div>', unsafe_allow_html=True)

    if st.button("Entrar →", key="btn_login"):
        if sel == "— Seleccioná —":
            st.error("Seleccioná un perfil.")
        elif sel == GERENCIA_OPT:
            if pwd == PASS_GERENCIA:
                st.session_state.update(role="gerencia"); st.rerun()
            else:
                st.error("Clave gerencia incorrecta.")
        else:
            vid = sel.split(" · ")[0]
            if pwd == PASS_VENDEDOR:
                st.session_state.update(role="vendedor", vid=vid, vname=vendedores[vid]); st.rerun()
            elif pwd == PASS_GERENCIA:
                st.session_state.update(role="gerencia"); st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="orbit-footer">Orbit © 2026 · Propiedad de Torres Matías</div>', unsafe_allow_html=True)


# ─────────────────────── VISTA VENDEDOR ───────────────────────────────

def render_vendedor(vid: str, vname: str) -> None:
    # ── Datos base ──
    dash           = next((v for v in load_json_file(DASHBOARD_JSON) if v.get("vendedor_id") == vid), {})
    clientes_todos = [c for c in load_clientes_hoy() if c.get("vendedor_id") == vid]
    kpis           = dash.get("kpis", {})

    # ── Fuente de verdad financiera: mod_volumen_vendedor.csv ──
    df_vol_v = load_volumen()
    if not df_vol_v.empty and "vendedor_codigo" in df_vol_v.columns:
        df_vol_v["vid"] = df_vol_v["vendedor_codigo"].map(VMAP_INV).fillna("")
    vrow = get_vol_row(df_vol_v, vid)

    obj       = sf(vrow.get("objetivo_mes"))    or sf(kpis.get("objetivo"))
    acum      = sf(vrow.get("acumulado_mes"))   or sf(kpis.get("venta_mes_actual"))
    av        = sf(vrow.get("avance_pct"))      or sf(kpis.get("avance_pct"))
    media_nec = sf(vrow.get("media_necesaria"))
    tendencia = sf(vrow.get("tendencia_mes"))   or acum
    av_calc   = (tendencia / obj * 100) if obj > 0 else av

    # Operativos del JSON (CCC, 11T — correctos)
    ccc = int(sf(kpis.get("ccc")))
    onc = int(sf(kpis.get("once_titulares")))

    # Real del día (ventas.csv)
    df_rd  = load_real_dia()
    rd_row = df_rd[df_rd["vid"] == vid].iloc[0].to_dict() if not df_rd.empty and vid in df_rd["vid"].values else {}
    vr_dia     = sf(rd_row.get("venta_dia"))
    fecha_real = ss(rd_row.get("fecha_real", "—"))

    df_11t_all = load_11t()
    df_rei     = load_reintegros()
    sync       = dash.get("last_sync","")[:16]

    # ── Top bar ──
    c1, c2, c3 = st.columns([1, 6, 1])
    with c1:
        if LOGO_MARK.exists(): st.image(str(LOGO_MARK), width=36)
    with c2:
        st.markdown(
            f'<div style="padding-top:3px"><b style="color:#DDD">{vname}</b></div>'
            f'<div style="color:#444;font-size:.67rem">Datos al: {sync or fecha_real}</div>',
            unsafe_allow_html=True)
    with c3:
        if st.button("✕", key="logout_v"):
            for k in ["role","vid","vname","edit_plan"]: st.session_state.pop(k, None)
            st.rerun()
    st.markdown("---")

    # ── KPI strip mensual ──
    brecha     = acum - obj
    brecha_c   = "#6EC531" if brecha >= 0 else "#E05252"
    brecha_lbl = "excedente" if brecha >= 0 else "faltante"
    st.markdown(f"""
<div class="kpi-row" translate="no">
  <div class="kpi-pill">
    <div class="kpi-pill-val {av_cls(av_calc)}">{av_calc:.1f}%</div>
    <div class="kpi-pill-lbl">Avance mes</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val">{fmt(acum)}</div>
    <div class="kpi-pill-lbl">Acumulado</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val">{fmt(obj)}</div>
    <div class="kpi-pill-lbl">Objetivo</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val" style="color:{brecha_c}">{fmt(abs(brecha))}</div>
    <div class="kpi-pill-lbl">{brecha_lbl}</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val warn">{fmt(media_nec) if media_nec else "—"}</div>
    <div class="kpi-pill-lbl">Media nec/día</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val">{fmt(vr_dia)}</div>
    <div class="kpi-pill-lbl">Real ({fecha_real})</div>
  </div>
</div>
    """, unsafe_allow_html=True)
    pbar_html = pbar(av_calc)
    st.markdown(pbar_html, unsafe_allow_html=True)

    # ── Selector de día — siempre los 6 días disponibles ──
    TODOS_DIAS = ["LU", "MA", "MI", "JU", "VI", "SA"]
    dow_map    = {0:"LU",1:"MA",2:"MI",3:"JU",4:"VI",5:"SA",6:"SA"}
    hoy_dia    = dow_map.get(date.today().weekday(),"LU")
    default_ix = TODOS_DIAS.index(hoy_dia)

    st.markdown('<div class="sec-header">📅 DÍA DE ZONA</div>', unsafe_allow_html=True)
    dia_sel = st.radio(
        "Día de zona", TODOS_DIAS,
        format_func=lambda d: DIAS.get(d, d),
        horizontal=True,
        index=default_ix,
        label_visibility="collapsed",
        key=f"dia_v_{vid}")

    clientes_dia = [c for c in clientes_todos if c.get("dia_visita") == dia_sel]
    # Si no hay clientes para el día exacto, mostrar todos (datos aún sin asignación día)
    sin_asignacion = len(clientes_dia) == 0
    if sin_asignacion:
        clientes_dia = clientes_todos  # fallback: todos los clientes del vendedor
    zona_nombre  = clientes_dia[0].get("zona","—") if clientes_dia else "—"
    n_total  = len(clientes_dia)
    n_comp   = sum(1 for c in clientes_dia if sf(c.get("ccc")) > 0)
    n_nocomp = n_total - n_comp

    # ── Zona banner ──
    nota_asignacion = (
        ' <span style="color:#555;font-size:.67rem">(sin asignación de día — mostrando cartera completa)</span>'
        if sin_asignacion else "")
    st.markdown(
        f'<div style="background:#0d1a00;border:1px solid #1E2E0E;border-radius:12px;'
        f'padding:11px 18px;margin:6px 0 14px;display:flex;align-items:center;gap:14px" translate="no">'
        f'<div style="font-size:1.5rem;font-weight:900;color:#6EC531;min-width:36px">'
        f'{DIAS.get(dia_sel, dia_sel)[:2]}</div>'
        f'<div style="flex:1">'
        f'<div style="font-size:.84rem;font-weight:600;color:#CCC">'
        f'{DIAS.get(dia_sel, dia_sel)} · Zona: {zona_nombre}{nota_asignacion}</div>'
        f'<div style="font-size:.71rem;color:#555">'
        f'{n_total} clientes · <span style="color:#6EC531">{n_comp} compraron</span> · '
        f'<span style="color:#E05252">{n_nocomp} sin compra</span>'
        f'</div></div>'
        f'</div>',
        unsafe_allow_html=True)

    # ── Tabs del día ──
    t_cli, t_11t, t_sc, t_plan = st.tabs([
        f"👥 Clientes ({n_total})", "⭐ 11 Titulares", "📦 Sin Cargos", "📝 Planificación"])

    with t_cli:
        _render_seg_cards(vid, clientes_dia)
        st.markdown('<div class="sec-header">CLIENTES DEL DÍA</div>', unsafe_allow_html=True)
        sin_comp = sorted([c for c in clientes_dia if sf(c.get("ccc")) == 0],
                          key=lambda x: sf(x.get("venta_mes_anterior")), reverse=True)
        con_comp = sorted([c for c in clientes_dia if sf(c.get("ccc")) > 0],
                          key=lambda x: sf(x.get("venta_mes_actual")), reverse=True)
        if sin_comp:
            st.markdown(f"#### 🔴 Sin compra del mes — {len(sin_comp)}")
            for c in sin_comp:
                _cli_card_vendedor(c, vid)
        if con_comp:
            st.markdown(f"#### 🟢 Compraron este mes — {len(con_comp)}")
            for c in con_comp:
                _cli_card_vendedor(c, vid)
        if not clientes_dia:
            st.info(f"No hay clientes asignados para {DIAS.get(dia_sel, dia_sel)}.")

    with t_11t:
        _render_11t_dia(vid, clientes_dia, df_11t_all)

    with t_sc:
        _render_sin_cargos(vid, df_rei)

    with t_plan:
        plan    = get_plan_hoy(vid)
        hoy_str = date.today().strftime("%d/%m/%Y")
        if plan and not st.session_state.get("edit_plan"):
            st.success(f"✅ Planificación enviada — {hoy_str}")
            vp = sf(plan.get("venta_esperada"))
            cp = int(sf(plan.get("ccc_tradicional")))
            tp = int(sf(plan.get("once_t_comprometidos")))
            st.markdown(f"""
            <table class="gtable"><thead><tr>
              <th style="text-align:left">Métrica</th><th>Comprometido</th><th>Real día</th><th>Dispersión</th>
            </tr></thead><tbody>
            <tr><td>Venta</td><td class="t-plan">{fmt(vp)}</td><td class="t-real">{fmt(vr_dia)}</td>
                <td>{dsv_html(vr_dia,vp,fmt)}</td></tr>
            <tr><td>CCC</td><td class="t-plan">{cp}</td><td class="t-real">{ccc}</td>
                <td>{dsv_html(ccc,cp)}</td></tr>
            <tr><td>11T</td><td class="t-plan">{tp}</td><td class="t-real">{onc}</td>
                <td>{dsv_html(onc,tp)}</td></tr>
            </tbody></table>""", unsafe_allow_html=True)
            if plan.get("clientes_clave"): st.markdown(f"**Clientes clave:** {plan['clientes_clave']}")
            if plan.get("acciones"):       st.markdown(f"**Acciones:** {plan['acciones']}")
            st.caption(f"Enviado: {plan.get('submitted_at','')}")
            if st.button("✏️ Corregir", key="btn_edit"):
                st.session_state["edit_plan"] = True; st.rerun()
        else:
            st.markdown(f"#### 📝 Comprometido del día — {hoy_str}")
            st.caption("Llega al panel de gerencia en tiempo real.")
            with st.form("form_plan"):
                default_venta = int(media_nec) if media_nec > 0 else (int(obj * 0.04) if obj else 0)
                venta_esp = st.number_input("Venta comprometida ($)", min_value=0, step=50_000,
                                            value=default_venta)
                c1, c2 = st.columns(2)
                with c1: ccc_trad = st.number_input("CCC Tradicional", min_value=0, step=1)
                with c2:
                    if vid == "V3": ccc_as = 0; st.caption("*V3 no trabaja Autoservicio*")
                    else: ccc_as = st.number_input("CCC AS / On Premise", min_value=0, step=1)
                once_t_c  = st.number_input("11T comprometidos", min_value=0, step=1, value=min(onc+1,11))
                cli_clave = st.text_input("Clientes clave a recuperar", placeholder="Nombre, ...")
                acciones  = st.text_area("Acciones concretas", placeholder="Qué vas a hacer diferente...", height=80)
                enviado   = st.form_submit_button("📤 Enviar a gerencia")
            if enviado:
                save_plan({"fecha":date.today().isoformat(),"vendedor_id":vid,"vendedor_nombre":vname,
                           "submitted_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           "venta_esperada":float(venta_esp),"ccc_tradicional":int(ccc_trad),
                           "ccc_as_op":int(ccc_as),"once_t_comprometidos":int(once_t_c),
                           "clientes_clave":cli_clave,"acciones":acciones})
                st.session_state.pop("edit_plan", None); load_json_file.clear()
                st.success("✅ Enviado."); st.rerun()

    st.markdown('<div class="orbit-footer">Orbit © 2026 · Propiedad de Torres Matías</div>', unsafe_allow_html=True)


# ─────────────────────── VISTA GERENCIAL ──────────────────────────────

def render_gerencia() -> None:
    vendedores = load_vendedores()
    dashboard  = load_json_file(DASHBOARD_JSON)
    dash_vid   = {v["vendedor_id"]: v for v in dashboard}
    ph         = planes_hoy()
    plan_vid   = {p["vendedor_id"]: p for p in ph}

    # Datasets CSV
    df_vol  = load_volumen()
    df_ven  = load_ventas_mes()
    df_ccc  = load_ccc_seg()
    df_11t  = load_11t()
    df_inv  = load_inversiones()
    df_rei  = load_reintegros()
    df_ef   = load_eficiencia()
    df_hist = load_historial()

    # vol por VID string
    if not df_vol.empty and "vendedor_codigo" in df_vol.columns:
        df_vol["vid"] = df_vol["vendedor_codigo"].map(VMAP_INV).fillna("")

    # Header
    c1, c2, c3 = st.columns([1,7,1])
    with c1:
        if LOGO_MARK.exists(): st.image(str(LOGO_MARK), width=40)
    with c2:
        hoy_str = date.today().strftime("%A %d de %B de %Y").title()
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#0d1f00,#111);border:1px solid #2a4a0d;'
            f'border-radius:14px;padding:16px 22px;text-align:center">'
            f'<div style="font-size:1.4rem;font-weight:900;color:#6EC531">🌅 MATINAL PAV · PEÑAFLOR</div>'
            f'<div style="color:#555;font-size:.78rem;margin-top:3px">{hoy_str}</div>'
            f'</div>', unsafe_allow_html=True)
    with c3:
        if st.button("✕", key="logout_g"):
            st.session_state.pop("role", None); st.rerun()

    # ── KPIs globales — fuente de verdad: mod_volumen_vendedor.csv ──
    # acumulado_mes del CSV es correcto; kpis.venta_mes_actual del JSON está desactualizado
    if not df_vol.empty and "acumulado_mes" in df_vol.columns:
        tot_fact = float(df_vol[df_vol["vid"].isin(VMAP.keys())]["acumulado_mes"].sum())
        tot_obj  = float(df_vol[df_vol["vid"].isin(VMAP.keys())]["objetivo_mes"].sum())
    else:
        tot_fact = sum(sf(v.get("kpis",{}).get("acumulado", 0) or
                          v.get("kpis",{}).get("venta_mes_actual", 0)) for v in dashboard)
        tot_obj  = sum(sf(v.get("kpis",{}).get("objetivo")) for v in dashboard)
    # CCC y clientes: correcto en el JSON
    tot_ccc  = sum(int(sf(v.get("kpis",{}).get("ccc"))) for v in dashboard)
    tot_cli  = sum(int(sf(v.get("kpis",{}).get("clientes_total"))) for v in dashboard)
    av_gral  = (tot_fact / tot_obj * 100) if tot_obj else 0
    n_planes = len(ph); n_vend = len(vendedores)

    # Real del día consolidado
    df_rd_g = load_real_dia()
    tot_real_dia   = float(df_rd_g["venta_dia"].sum())  if not df_rd_g.empty else 0.0
    tot_ccc_dia    = int(df_rd_g["ccc_dia"].sum())       if not df_rd_g.empty else 0
    fecha_real_g   = ss(df_rd_g["fecha_real"].iloc[0])  if not df_rd_g.empty else "—"

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, val, lbl, sub, cls in [
        (c1, fmt(tot_fact),           "Acumulado mes",     f"Obj: {fmt(tot_obj)}",           av_cls(av_gral)),
        (c2, f"{av_gral:.1f}%",       "Avance global",     pbar(av_gral),                    av_cls(av_gral)),
        (c3, fmt(tot_real_dia),       "Real último día",   f"Fecha: {fecha_real_g}",          ""),
        (c4, f"{tot_ccc}/{tot_cli}",  "CCC total mes",     "clientes con compra",             ""),
        (c5, f"{n_planes}/{n_vend}",  "Planificaciones",   "recibidas hoy",                   "" if n_planes==n_vend else "warn"),
    ]:
        with col:
            st.markdown(
                f'<div class="kger"><div class="kger-lbl">{lbl}</div>'
                f'<div class="kger-val {cls}" translate="no">{val}</div>'
                f'<div class="kger-sub">{sub}</div></div>',
                unsafe_allow_html=True)

    st.markdown("---")

    # ── TABS GERENCIA ──
    t_mat, t_plan, t_obj, t_seg, t_11t, t_desc, t_zon, t_cli = st.tabs([
        "📊 Matinal", "📝 Plan vs Real", "🎯 Objetivos", "👥 CCC Segmentos",
        "⭐ 11 Titulares", "💰 Descuentos", "📅 Zona / Día", "🔍 Clientes"
    ])

    # ─────────── TAB MATINAL ───────────
    with t_mat:
        st.markdown('<div class="sec-header">ESTADO DEL EQUIPO HOY</div>', unsafe_allow_html=True)
        # Ordenar por avance desc usando df_vol (fuente correcta)
        def _get_av(dash_entry):
            vv = get_vol_row(df_vol, dash_entry.get("vendedor_id",""))
            return sf(vv.get("avance_pct")) or sf(dash_entry.get("kpis",{}).get("avance_pct"))
        sorted_dash = sorted(dashboard, key=_get_av, reverse=True)

        for v in sorted_dash:
            vid    = v.get("vendedor_id","")
            if vid not in vendedores: continue   # excluir V2/V5
            nombre = vendedores.get(vid, vid)
            kpis   = v.get("kpis",{})

            # Datos financieros desde mod_volumen_vendedor (fuente de verdad)
            vrow_g = get_vol_row(df_vol, vid)
            av     = sf(vrow_g.get("avance_pct"))  or sf(kpis.get("avance_pct"))
            fact   = sf(vrow_g.get("acumulado_mes")) or sf(kpis.get("venta_mes_actual"))
            obj    = sf(vrow_g.get("objetivo_mes")) or sf(kpis.get("objetivo"))
            media  = sf(vrow_g.get("media_necesaria"))
            v_ayer = sf(vrow_g.get("venta_ayer"))

            # Operativos desde JSON (correcto)
            ccc    = int(sf(kpis.get("ccc"))); cli = int(sf(kpis.get("clientes_total")))
            zona   = DIAS.get(v.get("zona",""), v.get("zona","—"))
            has_p  = vid in plan_vid
            col_av = "#6EC531" if av>=85 else ("#F5A623" if av>=60 else "#E05252")
            brecha = fact - obj
            brecha_c = "#6EC531" if brecha >= 0 else "#E05252"

            # Real del día para este vendedor
            rd_v = df_rd_g[df_rd_g["vid"]==vid].iloc[0].to_dict() if not df_rd_g.empty and vid in df_rd_g["vid"].values else {}
            real_dia = sf(rd_v.get("venta_dia"))

            st.markdown(
                f'<div class="vrow" translate="no">'
                f'<div style="font-size:1rem;min-width:22px">{"✅" if has_p else "⏳"}</div>'
                f'<div style="flex:1">'
                f'<div class="vrow-name">{vid} · {nombre} <span style="color:#444;font-size:.72rem">({zona})</span></div>'
                f'<div class="vrow-meta">'
                f'Acum: <b style="color:#CCC">{fmt(fact)}</b> / Obj: {fmt(obj)} · '
                f'<span style="color:{brecha_c}">{"+" if brecha>=0 else ""}{fmt(brecha)}</span> · '
                f'Real día: <b style="color:#6EC531">{fmt(real_dia)}</b> · '
                f'Media nec: {fmt(media)} · Ayer: {fmt(v_ayer)}'
                f'</div>'
                f'<div class="vrow-meta">CCC: {ccc}/{cli}</div>'
                f'{pbar(av)}'
                f'</div>'
                f'<div class="vrow-av" style="color:{col_av}">{av:.1f}%</div>'
                f'</div>', unsafe_allow_html=True)

    # ─────────── TAB PLAN VS REAL ───────────
    with t_plan:
        st.markdown('<div class="sec-header">COMPARATIVA PLANIFICADO VS REAL — HOY</div>', unsafe_allow_html=True)

        if not ph:
            st.warning("⏳ Ningún vendedor envió planificación todavía.")
        else:
            st.markdown("""
            <table class="gtable"><thead><tr>
              <th>Vendedor</th>
              <th>Venta Plan</th><th>Venta Real</th><th>Dispersión</th>
              <th>CCC Plan</th><th>CCC Real</th><th>Disp.</th>
              <th>11T Plan</th><th>11T Real</th><th>Disp.</th>
            </tr></thead><tbody>""", unsafe_allow_html=True)

            for p in sorted(ph, key=lambda x: x.get("vendedor_id","")):
                vid    = p.get("vendedor_id","")
                nombre = vendedores.get(vid, vid)
                dv     = dash_vid.get(vid,{})
                kpis   = dv.get("kpis",{})
                vp = sf(p.get("venta_esperada"))
                # Real: usar ventas.csv (fuente de verdad para real del día)
                rd_pv = df_rd_g[df_rd_g["vid"]==vid].iloc[0].to_dict() if not df_rd_g.empty and vid in df_rd_g["vid"].values else {}
                vr = sf(rd_pv.get("venta_dia"))   # CORRECTO: no usa kpis.venta_hoy_total (siempre 0)
                cp = int(sf(p.get("ccc_tradicional")))
                cr = int(rd_pv.get("ccc_dia", 0)) or int(sf(kpis.get("ccc")))
                tp = int(sf(p.get("once_t_comprometidos")))
                tr = int(sf(kpis.get("once_titulares")))
                st.markdown(
                    f'<tr translate="no"><td><b>{vid}</b><br><span class="t-head">{nombre}</span></td>'
                    f'<td class="t-plan">{fmt(vp)}</td><td class="t-real">{fmt(vr)}</td><td>{dsv_html(vr,vp,fmt)}</td>'
                    f'<td class="t-plan">{cp}</td><td class="t-real">{cr}</td><td>{dsv_html(cr,cp)}</td>'
                    f'<td class="t-plan">{tp}</td><td class="t-real">{tr}</td><td>{dsv_html(tr,tp)}</td>'
                    f'</tr>', unsafe_allow_html=True)

            st.markdown("</tbody></table>", unsafe_allow_html=True)

        # Pendientes
        ids_con = {p["vendedor_id"] for p in ph}
        sin = [v for v in vendedores if v not in ids_con]
        if sin:
            st.markdown('<div class="sec-header">SIN PLANIFICACIÓN</div>', unsafe_allow_html=True)
            for vid in sin:
                st.markdown(f'<div class="plan-pendiente">⏳ {vid} · {vendedores[vid]}</div>', unsafe_allow_html=True)

    # ─────────── TAB OBJETIVOS ───────────
    with t_obj:

        # ── Calcular semanas históricas ──
        sem_data: dict[str, dict] = {}
        hist_caption = ""
        # REGLA PEÑAFLOR: semanas históricas por FechaComprobante (facturación)
        if not df_hist.empty and "FechaComprobante" in df_hist.columns:
            ultimo = df_hist["FechaComprobante"].max().date()
            hist_caption = ultimo.strftime("%d/%m/%Y")
            for i, (ini, fin) in enumerate([
                (ultimo - timedelta(days=20), ultimo - timedelta(days=14)),
                (ultimo - timedelta(days=13), ultimo - timedelta(days=7)),
                (ultimo - timedelta(days=6),  ultimo),
            ]):
                mask = (df_hist["FechaComprobante"].dt.date >= ini) & (df_hist["FechaComprobante"].dt.date <= fin)
                gr = df_hist[mask].groupby("CodVendedor")["ImporteNetoItem"].sum()
                for code, val in gr.items():
                    vid_k = VMAP_INV.get(code)
                    if vid_k:
                        if vid_k not in sem_data: sem_data[vid_k] = {}
                        sem_data[vid_k][f"sem{i}"] = val

        # ── Banner resumen equipo ──
        tot_obj_b  = sum(sf(df_vol[df_vol["vid"]==v].iloc[0].get("objetivo_mes")) for v in vendedores if not df_vol.empty and "vid" in df_vol.columns and len(df_vol[df_vol["vid"]==v]))
        tot_acum_b = sum(sf(df_vol[df_vol["vid"]==v].iloc[0].get("acumulado_mes")) for v in vendedores if not df_vol.empty and "vid" in df_vol.columns and len(df_vol[df_vol["vid"]==v]))
        av_gral_b  = (tot_acum_b / tot_obj_b * 100) if tot_obj_b else 0
        av_b_cls   = "" if av_gral_b >= 85 else ("warn" if av_gral_b >= 60 else "danger")
        brecha_b   = tot_acum_b - tot_obj_b
        brecha_b_c = "#6EC531" if brecha_b >= 0 else "#E05252"
        st.markdown(f"""
        <div class="obj-banner" translate="no">
          <div class="obj-ban-item">
            <div class="obj-ban-val">{fmt(tot_obj_b)}</div>
            <div class="obj-ban-lbl">Objetivo equipo</div>
          </div>
          <div class="obj-ban-item">
            <div class="obj-ban-val">{fmt(tot_acum_b)}</div>
            <div class="obj-ban-lbl">Acumulado equipo</div>
          </div>
          <div class="obj-ban-item">
            <div class="obj-ban-val {av_b_cls}">{av_gral_b:.1f}%</div>
            <div class="obj-ban-lbl">Avance global</div>
          </div>
          <div class="obj-ban-item">
            <div class="obj-ban-val" style="color:{brecha_b_c}">{fmt(abs(brecha_b))}</div>
            <div class="obj-ban-lbl">{"Excedente" if brecha_b>=0 else "Brecha total"}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Construir tarjeta por vendedor ──
        def obj_card(vid: str) -> str:
            nombre  = vendedores.get(vid, vid)
            vrow    = df_vol[df_vol["vid"]==vid] if not df_vol.empty and "vid" in df_vol.columns else pd.DataFrame()
            has_row = not vrow.empty
            r       = vrow.iloc[0] if has_row else None

            obj_  = sf(r.get("objetivo_mes"))  if has_row else sf(dash_vid.get(vid,{}).get("kpis",{}).get("objetivo"))
            acum_ = sf(r.get("acumulado_mes")) if has_row else sf(dash_vid.get(vid,{}).get("kpis",{}).get("venta_mes_actual"))
            av_   = sf(r.get("avance_pct"))    if has_row else sf(dash_vid.get(vid,{}).get("kpis",{}).get("avance_pct"))
            med_  = sf(r.get("media_necesaria")) if has_row else 0.0
            prom_ = sf(r.get("promedio_dia"))    if has_row else 0.0
            ayer_ = sf(r.get("venta_ayer"))      if has_row else 0.0

            brecha = acum_ - obj_
            col_av = "#6EC531" if av_ >= 85 else ("#F5A623" if av_ >= 60 else "#E05252")
            bar_w  = min(max(av_, 0), 100)
            zona   = DIAS.get(dash_vid.get(vid,{}).get("zona",""), dash_vid.get(vid,{}).get("zona","—"))

            # Badge color: verde cuando supera, naranja intermedio, rojo crítico
            badge_bg = col_av; badge_fg = "#000"

            # Brecha HTML
            brecha_c = "#6EC531" if brecha >= 0 else "#E05252"
            brecha_s = f'{"+" if brecha>=0 else ""}{fmt(brecha)}'

            # ── Sparkline barras (últimas 3 semanas) ──
            sd    = sem_data.get(vid, {})
            s_v   = [sd.get(f"sem{i}", 0) for i in range(3)]
            s_max = max(s_v) if any(x > 0 for x in s_v) else 1
            lbl_s = ["S-2", "S-1", "Rec"]

            bar_colors = [
                "#1a2e0a" if col_av=="#6EC531" else ("#2e1e06" if col_av=="#F5A623" else "#2a0a0a"),
                "#233b0d" if col_av=="#6EC531" else ("#3a2508" if col_av=="#F5A623" else "#360d0d"),
                col_av,
            ]
            spark_cols = ""
            for i in range(3):
                ratio    = s_v[i] / s_max if s_max > 0 else 0
                bar_h    = max(int(ratio * 44), 2)
                space_h  = 44 - bar_h
                val_s    = fmt(s_v[i]) if s_v[i] > 0 else "—"
                spark_cols += (
                    f'<div style="display:flex;flex-direction:column;flex:1;align-items:stretch;">'
                    f'  <div style="height:{space_h}px"></div>'
                    f'  <div style="height:{bar_h}px;background:{bar_colors[i]};border-radius:3px 3px 0 0;min-height:2px"></div>'
                    f'  <div style="font-size:.58rem;color:#2e2e2e;text-align:center;margin-top:3px;white-space:nowrap;overflow:hidden">{val_s}</div>'
                    f'  <div style="font-size:.56rem;color:#222;text-align:center">{lbl_s[i]}</div>'
                    f'</div>'
                )

            tend = ("↑" if s_v[2] > s_v[1]*1.05 else ("↓" if s_v[2] < s_v[1]*0.95 else "→")) if s_v[1] > 0 else "—"
            tend_c = "#6EC531" if tend=="↑" else ("#E05252" if tend=="↓" else "#555")

            return f"""
<div class="vobj-card" translate="no">
  <div class="vobj-head">
    <span class="vobj-badge" style="background:{badge_bg};color:{badge_fg}">{vid}</span>
    <span class="vobj-name">{nombre}</span>
    <span class="vobj-zona-tag">{zona}</span>
  </div>
  <div class="vobj-body">
    <div class="vobj-main">
      <div class="vobj-avrow">
        <div class="vobj-pct" style="color:{col_av}">{av_:.1f}%</div>
        <div class="vobj-brecha-box">
          <div class="vobj-br-lbl">Brecha mes</div>
          <div class="vobj-br-val" style="color:{brecha_c}">{brecha_s}</div>
        </div>
      </div>
      <div class="vobj-pbar"><div class="vobj-pbar-fill" style="width:{bar_w}%;background:{col_av}"></div></div>
      <div class="vobj-m4">
        <div class="vobj-m4-item">
          <div class="vobj-m4-val">{fmt(obj_)}</div>
          <div class="vobj-m4-lbl">Objetivo</div>
        </div>
        <div class="vobj-m4-item">
          <div class="vobj-m4-val" style="color:{col_av}">{fmt(acum_)}</div>
          <div class="vobj-m4-lbl">Acumulado</div>
        </div>
        <div class="vobj-m4-item">
          <div class="vobj-m4-val">{fmt(med_) if med_ else "—"}</div>
          <div class="vobj-m4-lbl">M / dia</div>
        </div>
        <div class="vobj-m4-item">
          <div class="vobj-m4-val">{fmt(ayer_) if ayer_ else "—"}</div>
          <div class="vobj-m4-lbl">Ayer</div>
        </div>
      </div>
    </div>
    <div class="vobj-spark">
      <div class="vobj-sp-title">Sem. hist.</div>
      <div style="display:flex;gap:5px;flex:1;align-items:stretch">{spark_cols}</div>
      <div class="vobj-tend" style="color:{tend_c}">{tend}</div>
    </div>
  </div>
</div>"""

        # ── Ordenar por avance desc y renderizar en 2 columnas ──
        def _av(v):
            rv = df_vol[df_vol["vid"]==v] if not df_vol.empty and "vid" in df_vol.columns else pd.DataFrame()
            return sf(rv.iloc[0].get("avance_pct")) if not rv.empty else sf(dash_vid.get(v,{}).get("kpis",{}).get("avance_pct"))

        vids_sorted = sorted(vendedores.keys(), key=_av, reverse=True)
        cols_obj    = st.columns(2, gap="small")
        for idx, v in enumerate(vids_sorted):
            with cols_obj[idx % 2]:
                st.markdown(obj_card(v), unsafe_allow_html=True)

        if hist_caption:
            st.caption(f"Historial hasta {hist_caption}")

    # ─────────── TAB CCC SEGMENTOS ───────────
    with t_seg:
        st.markdown('<div class="sec-header">CCC POR SEGMENTO — REAL vs PLANIFICADO</div>', unsafe_allow_html=True)

        # Segmentos reales del mes actual desde ventas.csv
        if not df_ven.empty:
            # Normalizar ramo → segmento
            def norm_seg(ramo):
                ramo = str(ramo).upper()
                if "AUTOSERV" in ramo or "CASH" in ramo or "CADENA" in ramo or "SAR" in ramo or "BAR" in ramo: return "AUTOSERVICIO"
                if "PREMISE" in ramo or "VINOTEC" in ramo or "NOCHE" in ramo or "AWAY" in ramo: return "ON PREMISE"
                return "TRADICIONAL"
            df_ven_s = df_ven.copy()
            df_ven_s["seg_n"] = df_ven_s.get("Ramo", pd.Series(dtype=str)).apply(norm_seg)

            ccc_real = (df_ven_s[df_ven_s["ImporteNetoItem"]>0]
                        .groupby(["CodVendedor","seg_n"])["Cliente"]
                        .nunique().reset_index()
                        .rename(columns={"Cliente":"ccc_real"}))
            ccc_real["vid"] = ccc_real["CodVendedor"].map(VMAP_INV)
        else:
            ccc_real = pd.DataFrame()

        # Datos del mod_ccc_segmento (del motor)
        if not df_ccc.empty and "vendedor_codigo" in df_ccc.columns:
            df_ccc["vid"] = df_ccc["vendedor_codigo"].map(VMAP_INV)

        SEGS = ["TRADICIONAL","AUTOSERVICIO","ON PREMISE"]
        for seg in SEGS:
            st.markdown(f'<div class="sec-header">{seg}</div>', unsafe_allow_html=True)
            st.markdown("""
            <table class="gtable"><thead><tr>
              <th>Vendedor</th>
              <th>Clientes zona</th>
              <th>CCC real mes</th>
              <th>CCC comprometido</th>
              <th>Brecha</th>
            </tr></thead><tbody>""", unsafe_allow_html=True)

            total_cli_seg=0; total_ccc_seg=0; total_plan_seg=0
            for vid in sorted(vendedores.keys()):
                nombre = vendedores[vid]
                code   = VMAP.get(vid)

                # clientes del segmento desde mod_volumen
                row_v = df_vol[df_vol["vid"]==vid].iloc[0] if not df_vol.empty and "vid" in df_vol.columns and len(df_vol[df_vol["vid"]==vid]) else None
                if seg=="TRADICIONAL": n_cli = int(sf(row_v.get("clientes_trad",0))) if row_v is not None else 0
                elif seg=="AUTOSERVICIO": n_cli = int(sf(row_v.get("clientes_auto",0))) if row_v is not None else 0
                else: n_cli = int(sf(row_v.get("clientes_on",0))) if row_v is not None else 0

                # CCC real desde ventas.csv
                if not ccc_real.empty and "vid" in ccc_real.columns:
                    row_cr = ccc_real[(ccc_real["vid"]==vid) & (ccc_real["seg_n"]==seg)]
                    n_ccc_r = int(row_cr["ccc_real"].sum()) if not row_cr.empty else 0
                else:
                    # fallback mod_ccc_segmento
                    seg_k = "AUTOSERVICIO" if seg=="AUTOSERVICIO" else ("ON_PREMISE_VTK" if seg=="ON PREMISE" else "TRADICIONAL")
                    row_ccc = df_ccc[(df_ccc["vid"]==vid) & (df_ccc["segmento_operativo"].str.upper().str.contains(seg_k[:6], na=False))] if not df_ccc.empty and "vid" in df_ccc.columns else pd.DataFrame()
                    n_ccc_r = int(row_ccc["clientes_con_compra"].sum()) if not row_ccc.empty else 0

                # Planificado
                p = plan_vid.get(vid)
                if p:
                    if seg=="TRADICIONAL":   n_plan = int(sf(p.get("ccc_tradicional",0)))
                    elif seg=="AUTOSERVICIO": n_plan = int(sf(p.get("ccc_as_op",0)))
                    else:                    n_plan = 0
                else:
                    n_plan = 0

                total_cli_seg+=n_cli; total_ccc_seg+=n_ccc_r; total_plan_seg+=n_plan
                brecha = n_ccc_r - n_plan
                b_c = "t-pos" if brecha>=0 else "t-neg"

                if vid == "V3" and seg == "AUTOSERVICIO":
                    st.markdown(f'<tr><td><b>{vid}</b> {nombre}</td><td>—</td><td>—</td><td colspan="2" style="color:#444;font-size:.72rem">V3 no trabaja AS</td></tr>', unsafe_allow_html=True)
                    continue

                st.markdown(
                    f'<tr><td><b>{vid}</b><br><span class="t-head">{nombre}</span></td>'
                    f'<td>{n_cli}</td><td class="t-real">{n_ccc_r}</td>'
                    f'<td class="t-plan">{"—" if not p else n_plan}</td>'
                    f'<td class="{b_c}">{brecha:+d}</td>'
                    f'</tr>', unsafe_allow_html=True)

            st.markdown(
                f'<tr style="border-top:2px solid #2a2a2a;font-weight:700">'
                f'<td>TOTAL</td><td>{total_cli_seg}</td>'
                f'<td class="t-real">{total_ccc_seg}</td>'
                f'<td class="t-plan">{total_plan_seg}</td>'
                f'<td class="{"t-pos" if total_ccc_seg>=total_plan_seg else "t-neg"}">{total_ccc_seg-total_plan_seg:+d}</td>'
                f'</tr></tbody></table>', unsafe_allow_html=True)

    # ─────────── TAB 11 TITULARES ───────────
    with t_11t:
        st.markdown('<div class="sec-header">11 TITULARES — COBERTURA POR MARCA Y VENDEDOR</div>', unsafe_allow_html=True)

        if df_11t.empty:
            st.warning("Sin datos de 11T disponibles.")
        else:
            # Por marca: total tienen vs total deben
            if "marca_objetivo" in df_11t.columns:
                gm = df_11t.groupby("marca_objetivo").agg(
                    tienen=("tiene_flag","sum"),
                    faltan=("falta_flag","sum"),
                ).reset_index()
                gm["total"] = gm["tienen"] + gm["faltan"]
                gm["pct"]   = (gm["tienen"] / gm["total"] * 100).round(1)
                gm = gm.sort_values("pct", ascending=False)

                st.markdown("#### Por marca — compañía completa")
                st.markdown("""
                <table class="gtable"><thead><tr>
                  <th>Marca</th><th>Tienen</th><th>Faltan</th><th>Total</th><th>Cobertura %</th>
                </tr></thead><tbody>""", unsafe_allow_html=True)
                for _, r in gm.iterrows():
                    p = r["pct"]; c = "#6EC531" if p>=80 else ("#F5A623" if p>=50 else "#E05252")
                    st.markdown(
                        f'<tr><td>{r["marca_objetivo"]}</td>'
                        f'<td class="t-real">{int(r["tienen"])}</td>'
                        f'<td class="t-neg">{int(r["faltan"])}</td>'
                        f'<td>{int(r["total"])}</td>'
                        f'<td style="color:{c};font-weight:700">{p:.1f}%</td>'
                        f'</tr>', unsafe_allow_html=True)
                st.markdown("</tbody></table>", unsafe_allow_html=True)

            # Por vendedor
            if "vendedor_codigo" in df_11t.columns:
                df_11t["vid"] = df_11t["vendedor_codigo"].map(VMAP_INV)
                gv = df_11t.groupby("vid").agg(
                    tienen=("tiene_flag","sum"),
                    faltan=("falta_flag","sum"),
                ).reset_index()
                gv["total"] = gv["tienen"] + gv["faltan"]
                gv["pct"]   = (gv["tienen"] / gv["total"] * 100).round(1)

                st.markdown("#### Por vendedor")
                st.markdown("""
                <table class="gtable"><thead><tr>
                  <th>Vendedor</th><th>Tienen 11T</th><th>Faltan</th><th>Cobertura %</th>
                </tr></thead><tbody>""", unsafe_allow_html=True)
                for _, r in gv.sort_values("pct", ascending=False).iterrows():
                    vid = r.get("vid",""); nombre = vendedores.get(vid, vid)
                    if not vid: continue
                    p = r["pct"]; c = "#6EC531" if p>=80 else ("#F5A623" if p>=50 else "#E05252")
                    st.markdown(
                        f'<tr><td><b>{vid}</b> {nombre}</td>'
                        f'<td class="t-real">{int(r["tienen"])}</td>'
                        f'<td class="t-neg">{int(r["faltan"])}</td>'
                        f'<td style="color:{c};font-weight:700">{p:.1f}%</td>'
                        f'</tr>', unsafe_allow_html=True)
                st.markdown("</tbody></table>", unsafe_allow_html=True)

    # ─────────── TAB DESCUENTOS ───────────
    with t_desc:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown('<div class="sec-header">INVERSIÓN EN DESCUENTOS POR MARCA</div>', unsafe_allow_html=True)
            if not df_inv.empty and "marca" in df_inv.columns:
                gm_inv = df_inv.groupby("marca").agg(
                    inversion=("inversion_total","sum"),
                    venta=("venta_total","sum"),
                    roi=("roi_comercial","mean"),
                ).reset_index().sort_values("inversion", ascending=False)
                for _, r in gm_inv.iterrows():
                    roi = sf(r.get("roi"))
                    roi_c = "#6EC531" if roi >= 30 else ("#F5A623" if roi >= 10 else "#E05252")
                    st.markdown(
                        f'<div class="desc-row">'
                        f'<div class="desc-marca">{r["marca"]}</div>'
                        f'<div>'
                        f'<div class="desc-inv">{fmt(sf(r["inversion"]))}</div>'
                        f'<div class="desc-roi">ROI: <span style="color:{roi_c}">{roi:.1f}x</span>'
                        f' · Venta gen: {fmt(sf(r["venta"]))}</div>'
                        f'</div></div>', unsafe_allow_html=True)
            else:
                # Fallback: calcular desde ventas.csv
                if not df_ven.empty and "valorDescuento" in df_ven.columns:
                    gd = (df_ven[df_ven["valorDescuento"]>0]
                          .groupby("Marca")["valorDescuento"].sum()
                          .sort_values(ascending=False).head(15))
                    for marca, inv in gd.items():
                        st.markdown(
                            f'<div class="desc-row"><div class="desc-marca">{marca}</div>'
                            f'<div class="desc-inv">{fmt(inv)}</div></div>',
                            unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="sec-header">DESCUENTOS POR VENDEDOR</div>', unsafe_allow_html=True)
            if not df_ven.empty and "valorDescuento" in df_ven.columns:
                gv_d = (df_ven[df_ven["valorDescuento"]>0]
                        .groupby("CodVendedor")
                        .agg(descuento=("valorDescuento","sum"), articulos=("valorDescuento","count"))
                        .reset_index())
                gv_d["vid"] = gv_d["CodVendedor"].map(VMAP_INV)

                st.markdown("""
                <table class="gtable"><thead><tr>
                  <th>Vendedor</th><th>Total desc.</th><th>Artículos</th>
                </tr></thead><tbody>""", unsafe_allow_html=True)
                tot_desc = 0
                for _, r in gv_d.sort_values("descuento", ascending=False).iterrows():
                    vid = ss(r.get("vid",""))
                    if not vid: continue
                    nombre = vendedores.get(vid, vid)
                    inv = sf(r["descuento"]); art = int(r["articulos"]); tot_desc += inv
                    st.markdown(
                        f'<tr><td><b>{vid}</b> {nombre}</td>'
                        f'<td class="t-neg">{fmt(inv)}</td><td>{art}</td></tr>',
                        unsafe_allow_html=True)
                st.markdown(
                    f'<tr style="font-weight:700;border-top:2px solid #2a2a2a">'
                    f'<td>TOTAL</td><td class="t-neg">{fmt(tot_desc)}</td><td></td></tr>'
                    f'</tbody></table>', unsafe_allow_html=True)

        # Sin cargos / Reintegros
        st.markdown('<div class="sec-header">SIN CARGOS / REINTEGROS PENDIENTES</div>', unsafe_allow_html=True)
        if not df_rei.empty:
            gr = df_rei.groupby(["vendedor_codigo","vendedor_nombre"]).agg(
                operaciones=("inversion_descuento","count"),
                total_inversion=("inversion_descuento","sum"),
                total_venta=("venta_generada","sum"),
            ).reset_index()
            gr["vid"] = gr["vendedor_codigo"].map(VMAP_INV)

            c1i, c2i = st.columns(2)
            with c1i:
                for _, r in gr.iterrows():
                    vid = ss(r.get("vid",""))
                    nombre = vendedores.get(vid, r.get("vendedor_nombre",""))
                    st.markdown(
                        f'<div class="sc-row">'
                        f'<div class="sc-cliente">{vid} · {nombre}</div>'
                        f'<div class="sc-meta">Operaciones: {int(r["operaciones"])} · '
                        f'Inversión: {fmt(sf(r["total_inversion"]))} · '
                        f'Venta generada: {fmt(sf(r["total_venta"]))}</div>'
                        f'</div>', unsafe_allow_html=True)
            with c2i:
                if "estado_reintegro" in df_rei.columns:
                    est = df_rei.groupby("estado_reintegro").agg(
                        n=("inversion_descuento","count"),
                        total=("inversion_descuento","sum")).reset_index()
                    for _, r in est.iterrows():
                        st.metric(ss(r["estado_reintegro"]), f"{int(r['n'])} operac.", fmt(sf(r["total"])))

            # Detalle top sin cargos
            with st.expander("Ver detalle de sin cargos"):
                df_rei["vid"] = df_rei["vendedor_codigo"].map(VMAP_INV)
                for _, r in df_rei.head(20).iterrows():
                    vid = ss(r.get("vid",""))
                    st.markdown(
                        f'<div class="sc-row"><div class="sc-cliente">{r.get("cliente_nombre","—")} '
                        f'<span style="color:#555;font-size:.72rem">({vid} · {r.get("marca","—")})</span></div>'
                        f'<div class="sc-meta">Inversión: {fmt(sf(r.get("inversion_descuento")))} · '
                        f'Venta: {fmt(sf(r.get("venta_generada")))} · Estado: {r.get("estado_reintegro","—")}</div>'
                        f'</div>', unsafe_allow_html=True)
        else:
            st.info("Sin datos de reintegros.")

        # Eficiencia descuentos
        st.markdown('<div class="sec-header">EFICIENCIA DE DESCUENTOS</div>', unsafe_allow_html=True)
        if not df_ef.empty and "estado_eficiencia" in df_ef.columns:
            est_ef = df_ef["estado_eficiencia"].value_counts()
            c1e, c2e, c3e = st.columns(3)
            for col, est, lbl, color in [
                (c1e,"OK","OK","#6EC531"),
                (c2e,"SIN_BASE_HISTORICA","Sin base hist.","#F5A623"),
                (c3e,"SOLO_HISTORICO_CON_DESCUENTO","Solo c/desc.","#E05252"),
            ]:
                n = int(est_ef.get(est, 0))
                with col:
                    st.markdown(
                        f'<div class="kger" style="border-color:{color}22">'
                        f'<div class="kger-lbl">{lbl}</div>'
                        f'<div class="kger-val" style="color:{color}">{n}</div>'
                        f'<div class="kger-sub">descuentos</div></div>',
                        unsafe_allow_html=True)

    # ─────────── TAB ZONA / DÍA ───────────
    with t_zon:
        clientes_all_g = load_clientes_hoy()
        df_11t_g       = load_11t()
        df_rei_g       = load_reintegros()

        # Selector de día global — siempre los 6 días
        TODOS_DIAS_G = ["LU", "MA", "MI", "JU", "VI", "SA"]
        dow_map_g    = {0:"LU",1:"MA",2:"MI",3:"JU",4:"VI",5:"SA",6:"SA"}
        hoy_dia_g    = dow_map_g.get(date.today().weekday(),"LU")
        default_ix_g = TODOS_DIAS_G.index(hoy_dia_g)

        st.markdown('<div class="sec-header">📅 SELECCIONÁ EL DÍA PARA VER LA ZONA DE CADA VENDEDOR</div>',
                    unsafe_allow_html=True)
        dia_sel_g = st.radio(
            "Día de zona gerencia", TODOS_DIAS_G,
            format_func=lambda d: DIAS.get(d, d),
            horizontal=True,
            index=default_ix_g,
            label_visibility="collapsed",
            key="dia_ger")

        # Resumen: cuántos clientes por vendedor en el día
        cols_g_hdr = st.columns(len(vendedores))
        for idx_g, (vid_g, nombre_g) in enumerate(vendedores.items()):
            cli_v_dia = [c for c in clientes_all_g
                         if c.get("vendedor_id") == vid_g and c.get("dia_visita") == dia_sel_g]
            n_tot_g = len(cli_v_dia)
            n_cmp_g = sum(1 for c in cli_v_dia if sf(c.get("ccc")) > 0)
            vrow_g2 = get_vol_row(df_vol, vid_g)
            av_g2   = sf(vrow_g2.get("avance_pct"))
            col_av_g2 = "#6EC531" if av_g2 >= 85 else ("#F5A623" if av_g2 >= 60 else "#E05252")
            with cols_g_hdr[idx_g]:
                st.markdown(
                    f'<div class="kger" style="padding:12px 8px" translate="no">'
                    f'<div class="kger-lbl">{vid_g} · {nombre_g.split()[0]}</div>'
                    f'<div class="kger-val" style="color:{col_av_g2};font-size:1.3rem">{av_g2:.0f}%</div>'
                    f'<div class="kger-sub">{n_cmp_g}/{n_tot_g} CCC día</div>'
                    f'</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Por vendedor: detalle expandible
        for vid_g, nombre_g in vendedores.items():
            cli_v_dia = [c for c in clientes_all_g
                         if c.get("vendedor_id") == vid_g and c.get("dia_visita") == dia_sel_g]
            n_tot_g  = len(cli_v_dia)
            n_cmp_g  = sum(1 for c in cli_v_dia if sf(c.get("ccc")) > 0)
            n_noc_g  = n_tot_g - n_cmp_g
            zona_g   = cli_v_dia[0].get("zona","—") if cli_v_dia else "—"
            vrow_g2  = get_vol_row(df_vol, vid_g)
            av_g2    = sf(vrow_g2.get("avance_pct"))
            obj_g2   = sf(vrow_g2.get("objetivo_mes"))
            acum_g2  = sf(vrow_g2.get("acumulado_mes"))
            med_g2   = sf(vrow_g2.get("media_necesaria"))
            col_av_g2= "#6EC531" if av_g2 >= 85 else ("#F5A623" if av_g2 >= 60 else "#E05252")

            # Real del día
            rd_vg = df_rd_g[df_rd_g["vid"]==vid_g].iloc[0].to_dict() if not df_rd_g.empty and vid_g in df_rd_g["vid"].values else {}
            real_g = sf(rd_vg.get("venta_dia"))

            label_exp = (f"{vid_g} · {nombre_g} · Zona {zona_g} · "
                        f"{n_cmp_g}/{n_tot_g} CCC · {av_g2:.0f}% avance")
            with st.expander(label_exp, expanded=False):
                # KPI strip vendedor
                brecha_g2 = acum_g2 - obj_g2
                bc_g2     = "#6EC531" if brecha_g2 >= 0 else "#E05252"
                st.markdown(f"""
<div class="kpi-row" translate="no">
  <div class="kpi-pill">
    <div class="kpi-pill-val" style="color:{col_av_g2}">{av_g2:.1f}%</div>
    <div class="kpi-pill-lbl">Avance</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val">{fmt(acum_g2)}</div>
    <div class="kpi-pill-lbl">Acumulado</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val">{fmt(obj_g2)}</div>
    <div class="kpi-pill-lbl">Objetivo</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val" style="color:{bc_g2}">{fmt(abs(brecha_g2))}</div>
    <div class="kpi-pill-lbl">{"Excedente" if brecha_g2>=0 else "Faltante"}</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val warn">{fmt(med_g2) if med_g2 else "—"}</div>
    <div class="kpi-pill-lbl">Media nec/día</div>
  </div>
  <div class="kpi-pill">
    <div class="kpi-pill-val">{fmt(real_g)}</div>
    <div class="kpi-pill-lbl">Real último día</div>
  </div>
</div>""", unsafe_allow_html=True)

                # Segment cards
                _render_seg_cards(vid_g, cli_v_dia)

                # 11T para el día
                t_11tg, t_scg, t_aleg, t_perg = st.tabs([
                    "⭐ 11 Titulares", "📦 Sin Cargos", "⚠ Alertas Descuento", "📉 Pérdida Ventas"])

                with t_11tg:
                    _render_11t_dia(vid_g, cli_v_dia, df_11t_g)

                with t_scg:
                    _render_sin_cargos(vid_g, df_rei_g)

                with t_aleg:
                    st.markdown('<div class="sec-header">CLIENTES CON ALERTA DE DESCUENTO</div>',
                                unsafe_allow_html=True)
                    alerta_cli = [c for c in cli_v_dia if c.get("alerta_descuento","")]
                    if not alerta_cli:
                        st.success("✅ Sin alertas de descuento en el día.")
                    else:
                        for c in alerta_cli:
                            nom = ss(c.get("cliente_nombre","—"))
                            alerta_txt = ss(c.get("alerta_descuento",""))
                            inv  = sf(c.get("inversion_desc_ars"))
                            sc   = sf(c.get("sin_cargo_ars"))
                            st.markdown(
                                f'<div class="alert-card" translate="no">'
                                f'<div class="alert-cliente">{nom}</div>'
                                f'<div class="alert-title">⚠ {alerta_txt}</div>'
                                f'<div class="alert-accion">'
                                f'Invers. desc: {fmt(inv)}'
                                f'{f" · Sin cargo: {fmt(sc)}" if sc > 0 else ""}'
                                f'</div></div>',
                                unsafe_allow_html=True)
                        # También mostrar todos los sin_cargo del vendedor con detalle
                        if not df_rei_g.empty and "vendedor_codigo" in df_rei_g.columns:
                            vcode_g = VMAP.get(vid_g)
                            df_rei_vg = df_rei_g[df_rei_g["vendedor_codigo"] == vcode_g]
                            if not df_rei_vg.empty:
                                tot_sc_g = sf(df_rei_vg["inversion_descuento"].sum()) if "inversion_descuento" in df_rei_vg.columns else 0
                                st.markdown(
                                    f'<div class="sec-header">SIN CARGOS PENDIENTES: {len(df_rei_vg)} operaciones · {fmt(tot_sc_g)}</div>',
                                    unsafe_allow_html=True)

                with t_perg:
                    st.markdown('<div class="sec-header">PÉRDIDA VS MES ANTERIOR — CLIENTES DEL DÍA</div>',
                                unsafe_allow_html=True)
                    # Clientes que compraron antes y no ahora, o con variación negativa
                    perdidas = sorted(
                        [c for c in cli_v_dia
                         if sf(c.get("variacion_vs_mes_anterior")) < 0 or
                            (sf(c.get("venta_mes_anterior")) > 0 and sf(c.get("ccc")) == 0)],
                        key=lambda x: sf(x.get("variacion_vs_mes_anterior")))
                    if not perdidas:
                        st.success("✅ Sin pérdidas significativas en el día.")
                    else:
                        for c in perdidas:
                            nom     = ss(c.get("cliente_nombre","—"))
                            var     = sf(c.get("variacion_vs_mes_anterior"))
                            ant     = sf(c.get("venta_mes_anterior"))
                            act     = sf(c.get("venta_mes_actual"))
                            var_pct = sf(c.get("variacion_vs_mes_anterior_pct"))
                            seg_p   = ss(c.get("segmento","")).replace("_"," ")
                            motivo  = ss(c.get("kernel_motivo",""))
                            st.markdown(
                                f'<div class="perdida-row" translate="no">'
                                f'<div class="perdida-cli">{nom}'
                                f'<span style="color:#555;font-size:.7rem"> · {seg_p}</span></div>'
                                f'<div class="perdida-meta">'
                                f'Mes ant: {fmt(ant)} → Actual: {fmt(act)} · '
                                f'<span style="color:#E05252">{fmt(abs(var))} menos ({var_pct:.0f}%)</span>'
                                f'{f" · {motivo[:80]}" if motivo else ""}'
                                f'</div></div>',
                                unsafe_allow_html=True)

    # ─────────── TAB CLIENTES ───────────
    with t_cli:
        st.markdown('<div class="sec-header">BÚSQUEDA DE CLIENTES</div>', unsafe_allow_html=True)
        q = st.text_input("Buscar por nombre de cliente", placeholder="2+ letras...", key="q_ger")
        clientes_all = load_json_file(CLIENTES_JSON)
        if q and len(q) >= 2:
            found = [c for c in clientes_all if q.upper() in ss(c.get("cliente_nombre")).upper()]
            st.caption(f"{len(found)} resultado(s)")
            for c in found[:30]:
                vid = c.get("vendedor_id",""); vn = vendedores.get(vid, vid)
                cok = sb(c.get("ccc")); fn = int(sf(c.get("faltan_11t")))
                ico = "🟢" if cok and fn==0 else ("🟡" if cok else "🔴")
                with st.expander(f"{ico} {ss(c.get('cliente_nombre','—'))} · {vid} · {vn}"):
                    c1x, c2x = st.columns(2)
                    with c1x:
                        st.markdown(f"**Segmento:** {ss(c.get('segmento','—')).replace('_',' ')}")
                        st.markdown(f"**Venta mes:** {fmt(sf(c.get('venta_mes_actual')))}")
                        st.markdown(f"**CCC:** {'Sí' if cok else 'No'}")
                    with c2x:
                        st.markdown(f"**Falta 11T:** {fn} productos")
                        accion = ss(c.get("recomendacion") or c.get("kernel_accion"))
                        if accion: st.markdown(f"**Acción:** {accion}")
        else:
            st.caption("Escribí 2+ letras para buscar.")

        st.markdown('<div class="sec-header">TOP 25 CRÍTICOS — SIN CCC, MAYOR POTENCIAL</div>', unsafe_allow_html=True)
        sin_ccc = sorted([c for c in clientes_all if not sb(c.get("ccc"))],
                         key=lambda x: sf(x.get("venta_mes_anterior")), reverse=True)
        for c in sin_ccc[:25]:
            vid = c.get("vendedor_id",""); vn = vendedores.get(vid, vid)
            st.markdown(
                f'<div class="cli-card"><div class="cli-bar" style="background:#E05252"></div>'
                f'<div class="cli-body"><div class="cli-nombre">{ss(c.get("cliente_nombre","—"))}'
                f'<span class="cli-badge br">Sin CCC</span></div>'
                f'<div class="cli-meta">{vid} · {vn} · Ant: {fmt(sf(c.get("venta_mes_anterior")))}</div>'
                f'</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="orbit-footer">Orbit © 2026 · Propiedad de Torres Matías</div>', unsafe_allow_html=True)


# ─────────────────────────── MAIN ─────────────────────────────────────

def main() -> None:
    role = st.session_state.get("role")
    if   role == "vendedor": render_vendedor(st.session_state["vid"], st.session_state["vname"])
    elif role == "gerencia": render_gerencia()
    else: render_login()


if __name__ == "__main__":
    main()
