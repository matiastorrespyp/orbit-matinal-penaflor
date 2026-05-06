# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import json
import re
from datetime import datetime

BASE = Path(__file__).resolve().parent

D_DATASETS = BASE / "04_DATASETS_ORBIT"
D_INTEL = BASE / "05_INTELLIGENCE_ORBIT"
D_KERNEL = BASE / "06_KERNEL_OUTPUT"
D_APP = BASE / "06_APP_DATA"
D_HISTORY = BASE / "02_HISTORY"

D_APP.mkdir(exist_ok=True)

P_CLIENTES_DIA = D_DATASETS / "clientes_dia.csv"
P_VOL_VENDEDOR = D_DATASETS / "mod_volumen_vendedor.csv"
P_CCC_SEGMENTO = D_DATASETS / "mod_ccc_segmento.csv"
P_11T = D_DATASETS / "mod_11_titulares.csv"
P_DESC = D_DATASETS / "mod_alertas_descuentos.csv"
P_INVERSION = D_DATASETS / "mod_inversion_desc.csv"
P_REINTEGROS = D_DATASETS / "mod_reintegros_ctrl.csv"
P_HIST_MES = D_DATASETS / "hist_cliente_mes.csv"

P_ALERTAS_REALES = D_INTEL / "alertas_reales.csv"
P_ALERTAS_RESUMEN_VEND = D_INTEL / "alertas_reales_resumen_vendedor.csv"
P_KERNEL = D_KERNEL / "kernel_output.csv"
P_KERNEL_RESUMEN = D_KERNEL / "kernel_resumen_vendedor.csv"

DIAS_ORDEN = ["LU", "MA", "MI", "JU", "VI", "SA"]
VENDEDORES_EXCLUIR = {"V2", "V5"}
VENDEDOR_NOMBRE_OVERRIDE = {"V3": "NADIA GAMBINO"}


# =========================================================
# HELPERS
# =========================================================

def safe_text(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).strip()


def norm_col(c):
    s = str(c).strip().lower()
    s = s.replace(" ", "_")
    s = s.replace(".", "_")
    s = s.replace("-", "_")
    s = s.replace("/", "_")
    s = s.replace("%", "pct")
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def dedupe_columns(df):
    if df.empty:
        return df
    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]
    df = df.loc[:, ~pd.Index(df.columns).duplicated()]
    return df


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        for sep in (";", ",", "\t"):
            try:
                df = pd.read_csv(path, dtype=str, encoding=enc, sep=sep)
                if len(df.columns) > 1:
                    return dedupe_columns(df)
            except Exception:
                pass

    return pd.DataFrame()


def parse_num(v) -> float:
    s = safe_text(v)
    if not s or s.lower() == "nan":
        return 0.0

    s = s.replace("$", "").replace("%", "").replace(" ", "")

    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")

    try:
        return float(s)
    except Exception:
        return 0.0


def to_num(series) -> pd.Series:
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    return series.apply(parse_num)


def first_col(df: pd.DataFrame, candidates):
    if df.empty:
        return ""
    cols = set(df.columns)
    for c in candidates:
        c = norm_col(c)
        if c in cols:
            return c
    return ""


def get_value(row, col, default=""):
    if not col:
        return default
    try:
        v = row[col]
        if isinstance(v, pd.Series):
            return v.iloc[0] if len(v) else default
        return v
    except Exception:
        return default


def norm_vendor(v):
    s = safe_text(v).upper().replace(" ", "")
    if re.fullmatch(r"V\d+", s):
        return s
    if re.fullmatch(r"\d+", s):
        return f"V{s}"
    return ""


def normalize_day(v):
    s = safe_text(v).upper()
    s = s.replace("MIÉRCOLES", "MIERCOLES")
    s = s.replace("SÁBADO", "SABADO")

    if re.search(r"\bLU\b", s) or "LUNES" in s:
        return "LU"
    if re.search(r"\bMA\b", s) or "MARTES" in s:
        return "MA"
    if re.search(r"\bMI\b", s) or "MIERCOLES" in s:
        return "MI"
    if re.search(r"\bJU\b", s) or "JUEVES" in s:
        return "JU"
    if re.search(r"\bVI\b", s) or "VIERNES" in s:
        return "VI"
    if re.search(r"\bSA\b", s) or "SABADO" in s:
        return "SA"
    return ""


def clean_zone(z):
    s = safe_text(z).upper()
    s = s.replace("MIÉRCOLES", "MIERCOLES")
    s = s.replace("SÁBADO", "SABADO")

    for token in [
        "LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO",
        "LU", "MA", "MI", "JU", "VI", "SA"
    ]:
        s = re.sub(rf"\b{token}\b", "", s)

    s = re.sub(r"\bV\d+\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def infer_day_from_date(value):
    try:
        ts = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(ts):
            return ""
        weekday = int(ts.weekday())
        return {
            0: "LU",
            1: "MA",
            2: "MI",
            3: "JU",
            4: "VI",
            5: "SA"
        }.get(weekday, "")
    except Exception:
        return ""


def fmt_money(v):
    return float(parse_num(v))


# =========================================================
# BASE CLIENTES DEL DÍA DESDE ARQUITECTURA ORBIT
# =========================================================

def build_base_clientes(clientes_dia: pd.DataFrame) -> pd.DataFrame:
    if clientes_dia.empty:
        raise Exception("No existe o está vacío 04_DATASETS_ORBIT/clientes_dia.csv")

    df = clientes_dia.copy()

    c_cliente = first_col(df, ["cliente_id", "codigo_cliente", "cliente_codigo", "cod_cliente", "cliente"])
    c_nombre = first_col(df, ["cliente_nombre", "nombre_cliente", "razon_social", "nombre"])
    c_vendedor = first_col(df, ["vendedor_codigo", "codigo_vendedor", "vendedor_id", "vendedor", "cod_vendedor"])
    c_vendedor_nombre = first_col(df, ["vendedor_nombre", "nombre_vendedor"])
    c_zona = first_col(df, ["ruta", "zona", "localidad"])
    c_dia = first_col(df, ["dia_visita", "dia", "dia_objetivo", "fecha_objetivo", "fecha_ejecucion"])
    c_segmento = first_col(df, ["segmento_operativo", "segmento", "ramo"])
    c_subcanal = first_col(df, ["subsegmento", "subcanal", "subramo", "segmento_11t"])

    c_compra = first_col(df, ["compra_mes_flag", "compra_mes", "cliente_con_compra", "ccc_flag"])
    c_ccc = first_col(df, ["ccc_mes_flag", "ccc", "cliente_con_compra"])
    c_cobertura = first_col(df, ["cobertura_mes_flag", "cobertura_real", "cobertura"])
    c_umbral = first_col(df, ["umbral_cobertura", "cobertura_objetivo", "objetivo_cobertura"])
    c_importe = first_col(df, ["importe_mes", "venta_mes_actual", "mes_actual", "importe"])
    c_hoy = first_col(df, ["importe_hoy", "venta_hoy", "real_dia", "venta_dia"])
    c_estado = first_col(df, ["estado_cliente", "estado"])

    rows = []

    for _, r in df.iterrows():
        cliente_id = safe_text(get_value(r, c_cliente))
        if not cliente_id:
            continue

        vendedor_id = norm_vendor(get_value(r, c_vendedor))
        if not vendedor_id or vendedor_id in VENDEDORES_EXCLUIR:
            continue

        vendedor_nombre = safe_text(get_value(r, c_vendedor_nombre))
        vendedor_nombre = VENDEDOR_NOMBRE_OVERRIDE.get(vendedor_id, vendedor_nombre)

        zona_raw = safe_text(get_value(r, c_zona))
        dia_raw = safe_text(get_value(r, c_dia))
        dia = normalize_day(dia_raw) or normalize_day(zona_raw) or infer_day_from_date(dia_raw)

        rows.append({
            "cliente_id": cliente_id,
            "cliente_nombre": safe_text(get_value(r, c_nombre)),
            "vendedor_id": vendedor_id,
            "vendedor_nombre": vendedor_nombre,
            "zona": clean_zone(zona_raw),
            "dia_visita": dia,
            "segmento": safe_text(get_value(r, c_segmento)),
            "subcanal": safe_text(get_value(r, c_subcanal)),
            "estado": safe_text(get_value(r, c_estado)),
            "venta_hoy": parse_num(get_value(r, c_hoy, 0)),
            "venta_mes_actual": parse_num(get_value(r, c_importe, 0)),
            "venta_mes_anterior": 0.0,
            "compra_mes": parse_num(get_value(r, c_compra, 0)),
            "ccc": parse_num(get_value(r, c_ccc, 0)),
            "cobertura_real": parse_num(get_value(r, c_cobertura, 0)),
            "cobertura_objetivo": parse_num(get_value(r, c_umbral, 0)),
        })

    out = pd.DataFrame(rows)

    if out.empty:
        raise Exception("clientes_dia.csv fue leído, pero no se pudo construir base de clientes válida.")

    out["dia_visita"] = out["dia_visita"].replace("", "SIN_DIA")
    out = out.drop_duplicates(subset=["cliente_id", "vendedor_id", "dia_visita", "zona"])
    return out


# =========================================================
# HISTÓRICO MES ANTERIOR
# =========================================================

def enrich_mes_anterior(base: pd.DataFrame, hist_mes: pd.DataFrame) -> pd.DataFrame:
    if hist_mes.empty:
        return base

    h = hist_mes.copy()
    c_cliente = first_col(h, ["cliente_id", "codigo_cliente", "cliente_codigo", "cliente"])
    c_importe = first_col(h, ["importe", "importe_mes", "venta_mes", "venta_neta", "neto"])
    c_periodo = first_col(h, ["periodo", "periodo_mes", "yyyymm", "anio_mes", "mes_ano"])
    c_fecha = first_col(h, ["fecha", "fecha_mes"])
    c_anio = first_col(h, ["anio", "año", "year"])
    c_mes = first_col(h, ["mes", "month", "mes_num"])

    if not c_cliente or not c_importe:
        return base

    h["cliente_id"] = h[c_cliente].astype(str).str.strip()
    h["importe_hist"] = to_num(h[c_importe])

    if c_anio and c_mes:
        h["_anio"] = to_num(h[c_anio]).astype(int)
        h["_mes"] = to_num(h[c_mes]).astype(int)
    elif c_periodo:
        def parse_period(v):
            s = safe_text(v)
            m = re.match(r"^(\d{4})(\d{2})$", s)
            if m:
                return int(m.group(1)), int(m.group(2))
            m = re.match(r"^(\d{4})[-/](\d{1,2})$", s)
            if m:
                return int(m.group(1)), int(m.group(2))
            m = re.match(r"^(\d{1,2})[-/](\d{4})$", s)
            if m:
                return int(m.group(2)), int(m.group(1))
            return 0, 0

        parsed = h[c_periodo].apply(parse_period)
        h["_anio"] = parsed.apply(lambda x: x[0])
        h["_mes"] = parsed.apply(lambda x: x[1])
    elif c_fecha:
        ts = pd.to_datetime(h[c_fecha], errors="coerce", dayfirst=True)
        h["_anio"] = ts.dt.year.fillna(0).astype(int)
        h["_mes"] = ts.dt.month.fillna(0).astype(int)
    else:
        return base

    current_date = pd.Timestamp.today()
    prev = current_date - pd.DateOffset(months=1)

    prev_df = h[(h["_anio"] == int(prev.year)) & (h["_mes"] == int(prev.month))].copy()
    if prev_df.empty:
        return base

    agg = prev_df.groupby("cliente_id", as_index=False).agg(
        venta_mes_anterior_hist=("importe_hist", "sum")
    )

    out = base.merge(agg, on="cliente_id", how="left")
    out["venta_mes_anterior"] = pd.to_numeric(out["venta_mes_anterior_hist"], errors="coerce").fillna(out["venta_mes_anterior"])
    out = out.drop(columns=["venta_mes_anterior_hist"])
    return out


# =========================================================
# KERNEL
# =========================================================

def enrich_kernel(base: pd.DataFrame, kernel: pd.DataFrame) -> pd.DataFrame:
    base = base.copy()

    if kernel.empty or "cliente_id" not in kernel.columns:
        base["prioridad"] = 0
        base["prioridad_label"] = ""
        base["kernel_motivo"] = ""
        base["kernel_accion"] = ""
        base["faltan_11t"] = 0
        base["alertas"] = 0
        base["foco_top20"] = 0
        return base

    k = pd.DataFrame()
    k["cliente_id"] = kernel["cliente_id"].astype(str).str.strip()
    k["prioridad"] = to_num(kernel["score"]) if "score" in kernel.columns else 0
    k["prioridad_label"] = kernel["prioridad"].astype(str) if "prioridad" in kernel.columns else ""
    k["kernel_motivo"] = kernel["motivo_principal"].astype(str) if "motivo_principal" in kernel.columns else ""
    k["kernel_accion"] = kernel["decision"].astype(str) if "decision" in kernel.columns else ""
    k["faltan_11t"] = to_num(kernel["faltantes_11t"]) if "faltantes_11t" in kernel.columns else 0
    k["alertas"] = to_num(kernel["alertas_total"]) if "alertas_total" in kernel.columns else 0
    k["foco_top20"] = to_num(kernel["foco_top20_flag"]) if "foco_top20_flag" in kernel.columns else 0
    k = k.drop_duplicates("cliente_id")

    out = base.merge(k, on="cliente_id", how="left")

    for c in ["prioridad", "faltan_11t", "alertas", "foco_top20"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

    for c in ["prioridad_label", "kernel_motivo", "kernel_accion"]:
        out[c] = out[c].fillna("").astype(str)

    return out


# =========================================================
# 11 TITULARES
# =========================================================

def enrich_11t(base: pd.DataFrame, t11: pd.DataFrame) -> pd.DataFrame:
    base = base.copy()

    if t11.empty or "cliente_id" not in t11.columns:
        base["once_titulares"] = 0
        if "faltan_11t" not in base.columns:
            base["faltan_11t"] = 0
        return base

    t = t11.copy()
    t["cliente_id"] = t["cliente_id"].astype(str).str.strip()
    c_tiene = first_col(t, ["tiene_flag", "tiene", "cumple_flag"])
    c_falta = first_col(t, ["falta_flag", "faltante_flag", "falta"])

    t["tiene_num"] = to_num(t[c_tiene]) if c_tiene else 0
    t["falta_num"] = to_num(t[c_falta]) if c_falta else 0

    agg = t.groupby("cliente_id", as_index=False).agg(
        once_titulares_agg=("tiene_num", "sum"),
        faltan_11t_agg=("falta_num", "sum")
    )

    out = base.merge(agg, on="cliente_id", how="left")
    out["once_titulares"] = pd.to_numeric(out["once_titulares_agg"], errors="coerce").fillna(0)

    if "faltan_11t" not in out.columns:
        out["faltan_11t"] = 0

    mask = pd.to_numeric(out["faltan_11t"], errors="coerce").fillna(0) <= 0
    out.loc[mask, "faltan_11t"] = pd.to_numeric(out.loc[mask, "faltan_11t_agg"], errors="coerce").fillna(0)

    out = out.drop(columns=["once_titulares_agg", "faltan_11t_agg"])
    return out


# =========================================================
# ALERTAS DESCUENTOS / ALERTAS REALES
# =========================================================

def enrich_descuentos(base: pd.DataFrame, desc: pd.DataFrame, alertas_reales: pd.DataFrame) -> pd.DataFrame:
    base = base.copy()
    base["alerta_descuento"] = ""
    base["alerta_real_detalle"] = ""
    base["impacto_alertas_ars"] = 0.0

    frames = []

    if not desc.empty and "cliente_id" in desc.columns:
        d = desc.copy()
        d["cliente_id"] = d["cliente_id"].astype(str).str.strip()

        def build_msg(r):
            marca = safe_text(r.get("marca", ""))
            aplicado = safe_text(r.get("descuento_aplicado_pct", ""))
            exceso = safe_text(r.get("exceso_pct", ""))
            return f"{marca} | desc {aplicado}% | exceso {exceso}%".strip()

        d["msg"] = d.apply(build_msg, axis=1)
        dd = d.groupby("cliente_id", as_index=False).agg(
            alerta_descuento_tmp=("msg", lambda x: " | ".join([safe_text(v) for v in x if safe_text(v)][:3]))
        )
        frames.append(dd)

    if frames:
        out = base.merge(frames[0], on="cliente_id", how="left")
        out["alerta_descuento"] = out["alerta_descuento_tmp"].fillna("")
        out = out.drop(columns=["alerta_descuento_tmp"])
    else:
        out = base

    if not alertas_reales.empty and "cliente_id" in alertas_reales.columns:
        ar = alertas_reales.copy()
        ar["cliente_id"] = ar["cliente_id"].astype(str).str.strip()

        c_tipo = first_col(ar, ["tipo_alerta", "tipo", "alerta"])
        c_det = first_col(ar, ["detalle", "descripcion", "motivo"])
        c_impacto = first_col(ar, ["impacto_ars", "impacto_alerta_ars", "impacto", "importe"])

        if c_tipo or c_det:
            ar["detalle_alerta"] = ar.apply(
                lambda r: " - ".join([safe_text(get_value(r, c_tipo)), safe_text(get_value(r, c_det))]).strip(" -"),
                axis=1
            )
        else:
            ar["detalle_alerta"] = ""

        ar["impacto_num"] = to_num(ar[c_impacto]) if c_impacto else 0

        agg = ar.groupby("cliente_id", as_index=False).agg(
            alerta_real_detalle=("detalle_alerta", lambda x: " | ".join([safe_text(v) for v in x if safe_text(v)][:3])),
            impacto_alertas_ars=("impacto_num", "sum")
        )
        out = out.merge(agg, on="cliente_id", how="left", suffixes=("", "_ar"))
        out["alerta_real_detalle"] = out["alerta_real_detalle_ar"].fillna(out["alerta_real_detalle"]) if "alerta_real_detalle_ar" in out.columns else out["alerta_real_detalle"].fillna("")
        out["impacto_alertas_ars"] = pd.to_numeric(out["impacto_alertas_ars_ar"], errors="coerce").fillna(out["impacto_alertas_ars"]) if "impacto_alertas_ars_ar" in out.columns else pd.to_numeric(out["impacto_alertas_ars"], errors="coerce").fillna(0)
        out = out.drop(columns=[c for c in ["alerta_real_detalle_ar", "impacto_alertas_ars_ar"] if c in out.columns])

    out["alerta_real_detalle"] = out["alerta_real_detalle"].fillna("")
    out["impacto_alertas_ars"] = pd.to_numeric(out["impacto_alertas_ars"], errors="coerce").fillna(0)
    return out


# =========================================================
# INVERSIÓN / REINTEGROS / SIN CARGO
# =========================================================

def build_extra_metrics(base: pd.DataFrame, inversion: pd.DataFrame, reintegros: pd.DataFrame) -> pd.DataFrame:
    base = base.copy()
    base["inversion_desc_ars"] = 0.0
    base["sin_cargo_ars"] = 0.0
    base["sin_cargo_detalle"] = ""

    if not inversion.empty and "cliente_id" in inversion.columns:
        inv = inversion.copy()
        inv["cliente_id"] = inv["cliente_id"].astype(str).str.strip()
        c_imp = first_col(inv, ["inversion_ars", "inversion", "importe_descuento", "impacto_ars", "importe"])
        inv["inversion_num"] = to_num(inv[c_imp]) if c_imp else 0
        agg = inv.groupby("cliente_id", as_index=False).agg(inversion_desc_ars=("inversion_num", "sum"))
        base = base.merge(agg, on="cliente_id", how="left", suffixes=("", "_inv"))
        base["inversion_desc_ars"] = pd.to_numeric(base["inversion_desc_ars_inv"], errors="coerce").fillna(base["inversion_desc_ars"]) if "inversion_desc_ars_inv" in base.columns else pd.to_numeric(base["inversion_desc_ars"], errors="coerce").fillna(0)
        base = base.drop(columns=[c for c in ["inversion_desc_ars_inv"] if c in base.columns])

    if not reintegros.empty and "cliente_id" in reintegros.columns:
        rg = reintegros.copy()
        rg["cliente_id"] = rg["cliente_id"].astype(str).str.strip()
        c_imp = first_col(rg, ["importe", "importe_ars", "sin_cargo_ars", "impacto_ars"])
        c_det = first_col(rg, ["detalle", "producto", "descripcion"])
        rg["sin_cargo_num"] = to_num(rg[c_imp]) if c_imp else 0
        rg["detalle_sc"] = rg[c_det].astype(str) if c_det else ""
        agg = rg.groupby("cliente_id", as_index=False).agg(
            sin_cargo_ars=("sin_cargo_num", "sum"),
            sin_cargo_detalle=("detalle_sc", lambda x: " | ".join([safe_text(v) for v in x if safe_text(v)][:3]))
        )
        base = base.merge(agg, on="cliente_id", how="left", suffixes=("", "_sc"))
        if "sin_cargo_ars_sc" in base.columns:
            base["sin_cargo_ars"] = pd.to_numeric(base["sin_cargo_ars_sc"], errors="coerce").fillna(base["sin_cargo_ars"])
        if "sin_cargo_detalle_sc" in base.columns:
            base["sin_cargo_detalle"] = base["sin_cargo_detalle_sc"].fillna(base["sin_cargo_detalle"])
        base = base.drop(columns=[c for c in ["sin_cargo_ars_sc", "sin_cargo_detalle_sc"] if c in base.columns])

    base["inversion_desc_ars"] = pd.to_numeric(base["inversion_desc_ars"], errors="coerce").fillna(0)
    base["sin_cargo_ars"] = pd.to_numeric(base["sin_cargo_ars"], errors="coerce").fillna(0)
    base["sin_cargo_detalle"] = base["sin_cargo_detalle"].fillna("")
    return base


# =========================================================
# AVANCE / DASHBOARD
# =========================================================

def build_avance_map(vol_vendedor: pd.DataFrame, kernel_resumen: pd.DataFrame) -> dict:
    source = vol_vendedor if not vol_vendedor.empty else kernel_resumen
    if source.empty:
        return {}

    df = source.copy()
    c_v = first_col(df, ["vendedor_codigo", "codigo_vendedor", "vendedor_id", "vendedor", "codigo"])
    c_obj = first_col(df, ["objetivo", "objetivo_mes", "meta", "objetivo_ars"])
    c_acum = first_col(df, ["acumulado_mes", "acumulado", "resultado", "real", "venta_mes", "importe_mes", "mes_actual"])
    c_av = first_col(df, ["avance", "avance_pct", "cumplimiento", "cumplimiento_pct"])

    out = {}

    for _, r in df.iterrows():
        vendedor = norm_vendor(get_value(r, c_v))
        if not vendedor or vendedor in VENDEDORES_EXCLUIR:
            continue

        objetivo = parse_num(get_value(r, c_obj, 0))
        acumulado = parse_num(get_value(r, c_acum, 0))
        avance = parse_num(get_value(r, c_av, 0))

        if 0 < avance <= 1:
            avance *= 100
        if avance <= 0 and objetivo > 0:
            avance = acumulado / objetivo * 100

        out[vendedor] = {
            "objetivo": objetivo,
            "acumulado": acumulado,
            "avance_pct": avance
        }

    return out


# =========================================================
# FINALIZE
# =========================================================

def finalize(base: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    out = dedupe_columns(out)

    numeric_cols = [
        "venta_hoy", "venta_mes_actual", "venta_mes_anterior",
        "compra_mes", "ccc", "cobertura_real", "cobertura_objetivo",
        "prioridad", "faltan_11t", "alertas", "foco_top20",
        "once_titulares", "impacto_alertas_ars", "inversion_desc_ars", "sin_cargo_ars"
    ]

    for c in numeric_cols:
        if c not in out.columns:
            out[c] = 0
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

    text_cols = [
        "cliente_id", "cliente_nombre", "vendedor_id", "vendedor_nombre",
        "zona", "dia_visita", "segmento", "subcanal", "estado",
        "prioridad_label", "kernel_motivo", "kernel_accion",
        "alerta_descuento", "alerta_real_detalle", "sin_cargo_detalle"
    ]

    for c in text_cols:
        if c not in out.columns:
            out[c] = ""
        out[c] = out[c].fillna("").astype(str)

    out["vendedor_id"] = out["vendedor_id"].apply(norm_vendor)
    out = out[out["vendedor_id"] != ""].copy()
    out = out[~out["vendedor_id"].isin(VENDEDORES_EXCLUIR)].copy()

    out["vendedor_nombre"] = out.apply(
        lambda r: VENDEDOR_NOMBRE_OVERRIDE.get(r["vendedor_id"], r["vendedor_nombre"]),
        axis=1
    )

    out["dia_visita"] = out["dia_visita"].apply(lambda x: normalize_day(x) or safe_text(x))
    out["zona"] = out["zona"].apply(clean_zone)

    out["variacion_vs_mes_anterior"] = out["venta_mes_actual"] - out["venta_mes_anterior"]

    def calc_pct(r):
        actual = float(r["venta_mes_actual"])
        anterior = float(r["venta_mes_anterior"])
        if anterior > 0:
            return ((actual - anterior) / anterior) * 100
        if actual > 0 and anterior <= 0:
            return 100.0
        return 0.0

    out["variacion_vs_mes_anterior_pct"] = out.apply(calc_pct, axis=1)

    def build_alerta(r):
        parts = []
        if safe_text(r["alerta_descuento"]):
            parts.append(f"Descuento: {safe_text(r['alerta_descuento'])}")
        if safe_text(r["alerta_real_detalle"]):
            parts.append(safe_text(r["alerta_real_detalle"]))
        if safe_text(r["kernel_motivo"]):
            parts.append(safe_text(r["kernel_motivo"]))
        if float(r["faltan_11t"]) > 0:
            parts.append("Faltan 11T")
        if float(r["alertas"]) > 0:
            parts.append(f"Alertas: {int(float(r['alertas']))}")
        return " | ".join(parts[:4])

    out["alerta_resumen"] = out.apply(build_alerta, axis=1)
    out["recomendacion"] = out["kernel_accion"].where(out["kernel_accion"] != "", out["kernel_motivo"])

    out["mes_pasado_vs_actual_texto"] = out.apply(
        lambda r: (
            f"Mes actual: {int(float(r['venta_mes_actual']))} | "
            f"Mes anterior: {int(float(r['venta_mes_anterior']))} | "
            f"Var: {round(float(r['variacion_vs_mes_anterior_pct']), 1)}%"
        ),
        axis=1
    )

    out["detalle_automatizado"] = out.apply(
        lambda r: (
            f"Score Orbit: {round(float(r['prioridad']), 1)} | "
            f"Prioridad: {safe_text(r['prioridad_label'])} | "
            f"Motivo: {safe_text(r['kernel_motivo'])} | "
            f"Acción: {safe_text(r['kernel_accion'])}"
        ),
        axis=1
    )

    out = out.drop_duplicates(subset=["cliente_id", "vendedor_id", "dia_visita", "zona"])
    out = out.sort_values(
        by=["vendedor_id", "dia_visita", "prioridad", "venta_mes_actual", "cliente_nombre"],
        ascending=[True, True, False, False, True]
    )

    return out


# =========================================================
# EXPORT
# =========================================================

def export_json(base: pd.DataFrame, avance_map: dict):
    cols = [
        "cliente_id", "cliente_nombre", "segmento", "subcanal",
        "vendedor_id", "vendedor_nombre", "zona", "dia_visita",
        "prioridad", "prioridad_label", "estado", "venta_hoy",
        "cobertura_objetivo", "cobertura_real", "alertas",
        "alerta_descuento", "alerta_real_detalle", "alerta_resumen",
        "ultima_visita", "segunda_ultima_visita",
        "venta_mes_actual", "venta_mes_anterior",
        "variacion_vs_mes_anterior", "variacion_vs_mes_anterior_pct",
        "once_titulares", "faltan_11t", "compra_mes", "ccc",
        "inversion_desc_ars", "sin_cargo_ars", "sin_cargo_detalle",
        "impacto_alertas_ars", "recomendacion", "kernel_motivo", "kernel_accion",
        "mes_pasado_vs_actual_texto", "detalle_automatizado", "foco_top20"
    ]

    export = base.copy()
    for c in cols:
        if c not in export.columns:
            export[c] = ""

    export = export[cols].copy()

    export.to_json(D_APP / "clientes_hoy.json", orient="records", indent=2, force_ascii=False)
    export.to_json(D_APP / "cliente_detalle.json", orient="records", indent=2, force_ascii=False)

    dashboard = []

    for v in sorted(export["vendedor_id"].unique()):
        sub = export[export["vendedor_id"] == v].copy()
        av = avance_map.get(v, {"objetivo": 0, "acumulado": 0, "avance_pct": 0})

        dashboard.append({
            "vendedor_id": v,
            "vendedor_nombre": sub["vendedor_nombre"].iloc[0] if len(sub) else v,
            "zona": " / ".join([d for d in DIAS_ORDEN if d in list(sub["dia_visita"].unique())]),
            "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "kpis": {
                "clientes_total": int(len(sub)),
                "clientes_visitados": int((pd.to_numeric(sub["compra_mes"], errors="coerce").fillna(0) > 0).sum()),
                "clientes_pendientes": int((pd.to_numeric(sub["compra_mes"], errors="coerce").fillna(0) <= 0).sum()),
                "cobertura_pct": round(
                    (pd.to_numeric(sub["cobertura_real"], errors="coerce").fillna(0).gt(0).sum() / len(sub) * 100),
                    2
                ) if len(sub) else 0,
                "avance_pct": float(av["avance_pct"]),
                "objetivo": float(av["objetivo"]),
                "acumulado": float(av["acumulado"]),
                "alertas_criticas": int((sub["alerta_resumen"].astype(str).str.len() > 0).sum()),
                "oportunidades": int((pd.to_numeric(sub["prioridad"], errors="coerce").fillna(0) >= 80).sum()),
                "ccc": int(pd.to_numeric(sub["ccc"], errors="coerce").fillna(0).sum()),
                "once_titulares": int(pd.to_numeric(sub["once_titulares"], errors="coerce").fillna(0).sum()),
                "venta_hoy_total": float(pd.to_numeric(sub["venta_hoy"], errors="coerce").fillna(0).sum()),
                "venta_mes_actual": float(pd.to_numeric(sub["venta_mes_actual"], errors="coerce").fillna(0).sum()),
                "venta_mes_anterior": float(pd.to_numeric(sub["venta_mes_anterior"], errors="coerce").fillna(0).sum()),
                "inversion_desc_ars": float(pd.to_numeric(sub["inversion_desc_ars"], errors="coerce").fillna(0).sum()),
                "sin_cargo_ars": float(pd.to_numeric(sub["sin_cargo_ars"], errors="coerce").fillna(0).sum()),
                "impacto_alertas_ars": float(pd.to_numeric(sub["impacto_alertas_ars"], errors="coerce").fillna(0).sum())
            }
        })

    with open(D_APP / "dashboard_vendedor.json", "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)

    alertas = []

    for _, r in export.iterrows():
        alerta_resumen = safe_text(r.get("alerta_resumen", ""))
        if not alerta_resumen:
            continue

        prioridad = parse_num(r.get("prioridad", 0))
        alerta_descuento = safe_text(r.get("alerta_descuento", ""))

        alertas.append({
            "cliente_id": safe_text(r.get("cliente_id", "")),
            "cliente_nombre": safe_text(r.get("cliente_nombre", "")),
            "vendedor_id": safe_text(r.get("vendedor_id", "")),
            "tipo": "descuento" if alerta_descuento else ("critica" if prioridad >= 80 else "comercial"),
            "titulo": alerta_descuento or safe_text(r.get("kernel_motivo", "")) or "Alerta Orbit",
            "detalle": safe_text(r.get("detalle_automatizado", "")) + " | " + alerta_resumen,
            "accion": safe_text(r.get("recomendacion", ""))
        })

    pd.DataFrame(alertas).to_json(
        D_APP / "alertas_app.json",
        orient="records",
        indent=2,
        force_ascii=False
    )

    charts = build_charts_json(export, dashboard)
    with open(D_APP / "charts_app.json", "w", encoding="utf-8") as f:
        json.dump(charts, f, indent=2, ensure_ascii=False)


def build_charts_json(export: pd.DataFrame, dashboard: list) -> dict:
    df = export.copy()

    for c in [
        "venta_hoy", "venta_mes_actual", "venta_mes_anterior", "inversion_desc_ars",
        "sin_cargo_ars", "ccc", "once_titulares", "cobertura_real"
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    ventas_vendedor = []
    for v, sub in df.groupby(["vendedor_id", "vendedor_nombre"], dropna=False):
        vendedor_id, vendedor_nombre = v
        ventas_vendedor.append({
            "vendedor_id": vendedor_id,
            "vendedor_nombre": vendedor_nombre,
            "venta_hoy": float(sub["venta_hoy"].sum()),
            "mes_actual": float(sub["venta_mes_actual"].sum()),
            "mes_anterior": float(sub["venta_mes_anterior"].sum()),
            "inversion": float(sub["inversion_desc_ars"].sum()),
            "sin_cargo": float(sub["sin_cargo_ars"].sum()),
            "ccc": int(sub["ccc"].sum()),
            "once_titulares": int(sub["once_titulares"].sum())
        })

    cobertura_segmento = []
    for seg, sub in df.groupby("segmento", dropna=False):
        total = len(sub)
        cubiertos = int((sub["cobertura_real"] > 0).sum())
        cobertura_segmento.append({
            "segmento": safe_text(seg) or "SIN_SEGMENTO",
            "clientes": int(total),
            "cubiertos": cubiertos,
            "pct": round(cubiertos / total * 100, 2) if total else 0
        })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ventas_vendedor": ventas_vendedor,
        "cobertura_segmento": cobertura_segmento,
        "dashboard": dashboard
    }


# =========================================================
# MAIN
# =========================================================

def main():
    print("===== ORBIT APP PUBLISH INTEGRADO A ARQUITECTURA =====")

    clientes_dia = read_csv_safe(P_CLIENTES_DIA)
    kernel = read_csv_safe(P_KERNEL)
    t11 = read_csv_safe(P_11T)
    desc = read_csv_safe(P_DESC)
    alertas_reales = read_csv_safe(P_ALERTAS_REALES)
    inversion = read_csv_safe(P_INVERSION)
    reintegros = read_csv_safe(P_REINTEGROS)
    hist_mes = read_csv_safe(P_HIST_MES)
    vol_vendedor = read_csv_safe(P_VOL_VENDEDOR)
    kernel_resumen = read_csv_safe(P_KERNEL_RESUMEN)

    avance_map = build_avance_map(vol_vendedor, kernel_resumen)

    base = build_base_clientes(clientes_dia)
    base = enrich_mes_anterior(base, hist_mes)
    base = enrich_kernel(base, kernel)
    base = enrich_11t(base, t11)
    base = enrich_descuentos(base, desc, alertas_reales)
    base = build_extra_metrics(base, inversion, reintegros)
    base = finalize(base)

    export_json(base, avance_map)

    print("OK → JSON APP generados desde arquitectura Orbit")
    print(f"Clientes publicados: {len(base)}")
    print(f"Vendedores publicados: {base['vendedor_id'].nunique()}")
    print(f"Salida: {D_APP}")


if __name__ == "__main__":
    main()