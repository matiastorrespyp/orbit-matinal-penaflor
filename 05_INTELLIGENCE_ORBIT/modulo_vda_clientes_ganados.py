"""
_tmp_auditoria_vda.py
Módulo VDA - Validar productos y crear datasets Vinos del Año
Orbit Matinal Peñaflor · 2026-05-12

Solo lectura + generación de datasets.
No modifica portal, Flask, AppScript ni archivos principales.
"""

import json
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

# ============================================================
# RUTAS
# ============================================================
BASE           = Path(r"C:\Orbit\MATINAL_PENAFLOR")
PRODUCTOS_PATH = BASE / "01_INPUTS" / "producto activos.xlsx"
VENTAS_PATH    = BASE / "01_INPUTS" / "ventas.csv"
HISTORIAL_PATH = BASE / "02_HISTORY" / "historial_ventas.csv"
CLIENTES_PATH  = BASE / "01_INPUTS" / "clientes.xlsx"
DATASETS_OUT   = BASE / "04_DATASETS_ORBIT"
APPDATA_OUT    = BASE / "06_APP_DATA"

VENDEDORES_EXCLUIDOS = {2, 5}
FECHA_AUDITORIA      = "2026-05-12"
VDA_CAT_NORM         = "vinos del ano"   # normalizado sin tildes/ñ

def log(msg):
    # Forzar encoding seguro para terminal Windows (cp1252)
    safe = str(msg).encode("cp1252", errors="replace").decode("cp1252")
    print(f"[VDA] {safe}", flush=True)

def normalizar(s):
    """Lowercase + elimina diacríticos para comparar sin problemas de encoding."""
    if pd.isna(s):
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def read_csv_safe(path, cols=None):
    """Lee CSV con sep ';' y decimal ',' (formato argentino) probando encodings."""
    kwargs = dict(sep=";", low_memory=False, decimal=",")
    if cols:
        kwargs["usecols"] = cols
    for enc in ("utf-8-sig", "latin1", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError(f"No se pudo leer {path}")

def safe_json_default(obj):
    if isinstance(obj, (np.integer,)):  return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, (np.bool_,)):    return bool(obj)
    if isinstance(obj, pd.Period):      return str(obj)
    return str(obj)

# ============================================================
# TAREA 1a — LEER Y DIAGNOSTICAR MAESTRO DE PRODUCTOS
# ============================================================
log("=== TAREA 1: Diagnóstico producto activos.xlsx ===")

prod_raw = pd.read_excel(PRODUCTOS_PATH, header=3)
prod_raw.columns = [str(c).strip() for c in prod_raw.columns]

# Renombrar columnas por posición (evita problemas de encoding en nombres)
prod_raw.columns = ["bodega", "segmento", "linea_comercial",
                    "codigo_producto", "categoria", "descripcion_art",
                    "lts_x_caja", "uxc"]

prod_raw["codigo_producto"] = pd.to_numeric(prod_raw["codigo_producto"], errors="coerce")
prod_raw = prod_raw.dropna(subset=["codigo_producto"]).copy()
prod_raw["codigo_producto"] = prod_raw["codigo_producto"].astype(int)
prod_raw["lts_x_caja"]      = pd.to_numeric(prod_raw["lts_x_caja"], errors="coerce").fillna(0)
prod_raw["uxc"]             = pd.to_numeric(prod_raw["uxc"], errors="coerce").replace(0, np.nan).fillna(1)
prod_raw["cat_norm"]        = prod_raw["categoria"].apply(normalizar)
prod_raw["lts_por_unidad"]  = (prod_raw["lts_x_caja"] / prod_raw["uxc"]).round(4)

total_prods = len(prod_raw)
cat_counts  = prod_raw["categoria"].value_counts()
seg_counts  = prod_raw["segmento"].value_counts()
bod_counts  = prod_raw["bodega"].value_counts()

log(f"  Total productos con código: {total_prods}")
log(f"  Categorías: {dict(cat_counts)}")

# Dicts rápidos para lookup
lts_dict  = dict(zip(prod_raw["codigo_producto"], prod_raw["lts_por_unidad"]))
cat_dict  = dict(zip(prod_raw["codigo_producto"], prod_raw["cat_norm"]))
desc_dict = dict(zip(prod_raw["codigo_producto"], prod_raw["descripcion_art"]))

vda_mask = prod_raw["cat_norm"] == VDA_CAT_NORM
prod_vda    = prod_raw[vda_mask].copy()
prod_no_vda = prod_raw[~vda_mask].copy()

log(f"  Productos VDA (Vinos del año): {len(prod_vda)}")
log(f"  Bodegas VDA: {dict(prod_vda['bodega'].value_counts())}")

# ============================================================
# TAREA 2 — CLASIFICAR PRODUCTOS VDA -> mod_vda_productos.csv
# ============================================================
log("=== TAREA 2: Exportar mod_vda_productos.csv ===")

mod_vda_productos = prod_vda[[
    "codigo_producto", "descripcion_art", "bodega", "segmento",
    "linea_comercial", "categoria", "lts_x_caja", "uxc", "lts_por_unidad"
]].copy()
mod_vda_productos["clasificacion_vda"]    = "VDA"
mod_vda_productos["fuente_clasificacion"] = "maestro_productos_categoria"

mod_vda_productos.to_csv(DATASETS_OUT / "mod_vda_productos.csv",
                          index=False, encoding="utf-8-sig")
log(f"  -> mod_vda_productos.csv: {len(mod_vda_productos)} productos")

mod_vda_revision = prod_no_vda[[
    "codigo_producto", "descripcion_art", "bodega", "segmento",
    "linea_comercial", "categoria"
]].copy()
mod_vda_revision["criterio_faltante"] = "Categoria no es 'Vinos del año'; validar contra Tags Gescom"
mod_vda_revision.to_csv(DATASETS_OUT / "mod_vda_productos_revision_necesaria.csv",
                          index=False, encoding="utf-8-sig")
log(f"  -> mod_vda_productos_revision_necesaria.csv: {len(mod_vda_revision)} no-VDA")

# ============================================================
# TAREA 3 — CONSOLIDAR VENTAS VDA
# ============================================================
log("=== TAREA 3: Consolidar ventas VDA ===")

COLS_CSV = [
    "NroComprobante", "FechaComprobante",
    "Cliente", "RazonSocial", "CodVendedor", "Vendedor",
    "Localidad", "Ramo",
    "Codigo", "Articulo", "Marca", "Familia", "Rubro", "Tags",
    "CantBase", "ImporteNetoItem", "valorDescuento", "Descuento",
    "TipoDeVenta",
]

log("  Leyendo historial_ventas.csv (63 MB, ~129k filas)...")
hist = read_csv_safe(HISTORIAL_PATH, cols=COLS_CSV)
log(f"  historial_ventas.csv: {len(hist):,} filas leídas")

log("  Leyendo ventas.csv...")
vta = read_csv_safe(VENTAS_PATH, cols=COLS_CSV)
log(f"  ventas.csv: {len(vta):,} filas leídas")

# Combinar y deduplicar por NroComprobante + Codigo
# (historial primero — se preserva ante duplicados con ventas.csv)
combined = pd.concat([hist, vta], ignore_index=True)
log(f"  Combinado pre-dedup: {len(combined):,} filas")

combined["_key"] = combined["NroComprobante"].astype(str) + "||" + combined["Codigo"].astype(str)
combined = combined.drop_duplicates(subset="_key", keep="first").drop(columns="_key")
log(f"  Combinado post-dedup: {len(combined):,} filas ({len(hist)+len(vta)-len(combined):,} duplicados eliminados)")

# Parsear fecha y limpiar
combined["FechaComprobante"] = pd.to_datetime(
    combined["FechaComprobante"], dayfirst=True, errors="coerce"
)
combined = combined.dropna(subset=["FechaComprobante"])

combined["CodVendedor"]     = pd.to_numeric(combined["CodVendedor"], errors="coerce")
combined["ImporteNetoItem"] = pd.to_numeric(combined["ImporteNetoItem"], errors="coerce").fillna(0)
combined["CantBase"]        = pd.to_numeric(combined["CantBase"], errors="coerce").fillna(0)
combined["Codigo"]          = pd.to_numeric(combined["Codigo"], errors="coerce")

# Excluir V2, V5 y devoluciones
combined = combined[~combined["CodVendedor"].isin(VENDEDORES_EXCLUIDOS)]
combined = combined[combined["ImporteNetoItem"] > 0]
log(f"  Filas válidas (excl. V2/V5, excl. devoluciones): {len(combined):,}")

# Clasificar VDA
combined["cat_maestro"] = combined["Codigo"].map(cat_dict).fillna("")
combined["lts_por_uni"] = combined["Codigo"].map(lts_dict).fillna(0)
combined["tags_norm"]   = combined["Tags"].apply(normalizar)

vda_maestro = combined["cat_maestro"] == VDA_CAT_NORM
vda_tags    = (~vda_maestro) & combined["tags_norm"].str.contains("vinos del ano", na=False)

combined["es_vda"]      = vda_maestro | vda_tags
combined["fuente_vda"]  = ""
combined.loc[vda_maestro, "fuente_vda"] = "maestro_productos"
combined.loc[vda_tags,    "fuente_vda"] = "tags_gescom"

ventas_vda = combined[combined["es_vda"]].copy()
ventas_vda["litros"]   = (ventas_vda["CantBase"] * ventas_vda["lts_por_uni"]).round(3)
ventas_vda["anio_mes"] = ventas_vda["FechaComprobante"].dt.to_period("M")

log(f"  Filas VDA: {len(ventas_vda):,}  (maestro: {vda_maestro.sum():,} | tags: {vda_tags.sum():,})")

# Guardar base VDA
cols_base = [
    "FechaComprobante", "anio_mes", "NroComprobante",
    "Cliente", "RazonSocial", "CodVendedor", "Vendedor",
    "Localidad", "Ramo", "Codigo", "Articulo", "Marca",
    "CantBase", "litros", "ImporteNetoItem",
    "fuente_vda", "TipoDeVenta",
]
ventas_vda[cols_base].to_csv(DATASETS_OUT / "mod_vda_ventas_base.csv",
                               index=False, encoding="utf-8-sig")
log(f"  -> mod_vda_ventas_base.csv: {len(ventas_vda):,} filas VDA")

# ============================================================
# DETERMINAR MES ACTUAL Y MES ANTERIOR
# ============================================================
max_fecha   = ventas_vda["FechaComprobante"].max()
mes_actual  = max_fecha.to_period("M")
mes_anterior = mes_actual - 1
log(f"  Mes actual detectado: {mes_actual} | Mes anterior: {mes_anterior}")

vda_act = ventas_vda[ventas_vda["anio_mes"] == mes_actual].copy()
vda_ant = ventas_vda[ventas_vda["anio_mes"] == mes_anterior].copy()
log(f"  Filas VDA mes actual: {len(vda_act):,} | mes anterior: {len(vda_ant):,}")

# ============================================================
# TAREA 4 — RESUMEN MENSUAL VDA
# ============================================================
log("=== TAREA 4: Resumen mensual VDA ===")

# Usar int para evitar mismatch float/str en comparaciones
cli_act = set(vda_act["Cliente"].dropna().astype(int))
cli_ant = set(vda_ant["Cliente"].dropna().astype(int))

ganados   = cli_act - cli_ant
perdidos  = cli_ant - cli_act
retenidos = cli_act & cli_ant

resumen = {
    "fecha_auditoria":                  FECHA_AUDITORIA,
    "mes_actual":                       str(mes_actual),
    "mes_anterior":                     str(mes_anterior),
    "clientes_vda_mes_actual":          len(cli_act),
    "clientes_vda_mes_anterior":        len(cli_ant),
    "clientes_ganados_o_recuperados_vda": len(ganados),
    "clientes_perdidos_vda":            len(perdidos),
    "clientes_retenidos_vda":           len(retenidos),
    "balance_neto_clientes_vda":        len(ganados) - len(perdidos),
    "litros_vda_mes_actual":            round(float(vda_act["litros"].sum()), 2),
    "litros_vda_mes_anterior":          round(float(vda_ant["litros"].sum()), 2),
    "venta_neta_vda_mes_actual":        round(float(vda_act["ImporteNetoItem"].sum()), 2),
    "venta_neta_vda_mes_anterior":      round(float(vda_ant["ImporteNetoItem"].sum()), 2),
}
log(f"  {resumen}")

pd.DataFrame([resumen]).to_csv(DATASETS_OUT / "mod_vda_resumen_mensual.csv",
                                index=False, encoding="utf-8-sig")
log("  -> mod_vda_resumen_mensual.csv generado")

# ============================================================
# TAREA 5 — DETALLE CLIENTES VDA
# ============================================================
log("=== TAREA 5: Detalle clientes VDA ===")

def agg_mes(df):
    """Agrupa VDA por cliente normalizando el ID a int para evitar mismatch de tipos."""
    grp = df.groupby("Cliente").agg(
        razon_social    =("RazonSocial",     "first"),
        vendedor_codigo =("CodVendedor",     "first"),
        vendedor_nombre =("Vendedor",        "first"),
        localidad       =("Localidad",       "first"),
        segmento        =("Ramo",            "first"),
        litros          =("litros",          "sum"),
        venta_neta      =("ImporteNetoItem", "sum"),
    ).reset_index().rename(columns={"Cliente": "cliente"})
    # Normalizar cliente a int para comparaciones seguras
    grp["cliente"] = pd.to_numeric(grp["cliente"], errors="coerce").dropna().astype(int)
    grp = grp.dropna(subset=["cliente"])
    grp["cliente"] = grp["cliente"].astype(int)
    return grp

ag_act = agg_mes(vda_act)
ag_ant = agg_mes(vda_ant)

# Construir detalle desde cero con todos los clientes que tuvieron actividad VDA
# en alguno de los dos meses. Usar los sets de int ya definidos arriba.

# Perfil de clientes: preferir act (más reciente), fallback a ant
perfil_act = ag_act[["cliente","razon_social","vendedor_codigo","vendedor_nombre","localidad","segmento"]].copy()
perfil_ant = ag_ant[["cliente","razon_social","vendedor_codigo","vendedor_nombre","localidad","segmento"]].copy()
todos_clientes = set(ag_act["cliente"]) | set(ag_ant["cliente"])

perfil = pd.concat([perfil_act, perfil_ant], ignore_index=True)
perfil = perfil.drop_duplicates(subset="cliente", keep="first")   # act tiene prioridad

# Métricas del mes actual
metr_act = ag_act[["cliente","litros","venta_neta"]].rename(
    columns={"litros":"litros_mes_actual","venta_neta":"venta_neta_mes_actual"})
# Métricas del mes anterior
metr_ant = ag_ant[["cliente","litros","venta_neta"]].rename(
    columns={"litros":"litros_mes_anterior","venta_neta":"venta_neta_mes_anterior"})

detalle = (perfil
    .merge(metr_act, on="cliente", how="left")
    .merge(metr_ant, on="cliente", how="left")
)

# Flags de compra (ambos sets son int, detalle["cliente"] es int → isin funciona)
detalle["compro_vda_mes_actual"]   = detalle["cliente"].isin(cli_act).astype(int)
detalle["compro_vda_mes_anterior"] = detalle["cliente"].isin(cli_ant).astype(int)

# Rellenar NaN numéricos
for col in ["litros_mes_actual", "litros_mes_anterior",
            "venta_neta_mes_actual", "venta_neta_mes_anterior"]:
    detalle[col] = pd.to_numeric(detalle[col], errors="coerce").fillna(0).round(2)

# Estado VDA
def estado(row):
    if row["compro_vda_mes_actual"] == 1 and row["compro_vda_mes_anterior"] == 1:
        return "retenido"
    if row["compro_vda_mes_actual"] == 1 and row["compro_vda_mes_anterior"] == 0:
        return "ganado_o_recuperado"
    if row["compro_vda_mes_actual"] == 0 and row["compro_vda_mes_anterior"] == 1:
        return "perdido"
    return "sin_compra_vda"

detalle["estado_vda"]           = detalle.apply(estado, axis=1)
detalle["diferencia_litros"]    = (detalle["litros_mes_actual"]    - detalle["litros_mes_anterior"]).round(2)
detalle["diferencia_venta_neta"] = (detalle["venta_neta_mes_actual"] - detalle["venta_neta_mes_anterior"]).round(2)

cols_detalle = [
    "cliente", "razon_social", "vendedor_codigo", "vendedor_nombre",
    "localidad", "segmento",
    "compro_vda_mes_actual", "compro_vda_mes_anterior", "estado_vda",
    "litros_mes_actual", "litros_mes_anterior",
    "venta_neta_mes_actual", "venta_neta_mes_anterior",
    "diferencia_litros", "diferencia_venta_neta",
]
detalle[cols_detalle].sort_values(
    ["estado_vda", "venta_neta_mes_actual"], ascending=[True, False]
).to_csv(DATASETS_OUT / "mod_vda_clientes_detalle.csv",
         index=False, encoding="utf-8-sig")

estado_counts = detalle["estado_vda"].value_counts().to_dict()
log(f"  -> mod_vda_clientes_detalle.csv: {len(detalle)} clientes")
log(f"    {estado_counts}")

# ============================================================
# TAREA 6 — RANKING POR VENDEDOR
# ============================================================
log("=== TAREA 6: Ranking por vendedor ===")

ranking_rows = []
for vend_cod, grp in detalle.groupby("vendedor_codigo"):
    try:
        vc_int = int(float(vend_cod))
    except (ValueError, TypeError):
        continue
    if vc_int in VENDEDORES_EXCLUIDOS:
        continue
    nombre = grp["vendedor_nombre"].iloc[0] if len(grp) > 0 else ""
    ranking_rows.append({
        "vendedor_codigo":           f"V{vc_int}",
        "vendedor_nombre":           nombre,
        "clientes_vda_mes_actual":   int((grp["compro_vda_mes_actual"] == 1).sum()),
        "clientes_vda_mes_anterior": int((grp["compro_vda_mes_anterior"] == 1).sum()),
        "ganados_o_recuperados":     int((grp["estado_vda"] == "ganado_o_recuperado").sum()),
        "perdidos":                  int((grp["estado_vda"] == "perdido").sum()),
        "retenidos":                 int((grp["estado_vda"] == "retenido").sum()),
        "balance_neto":              int((grp["estado_vda"] == "ganado_o_recuperado").sum()
                                        - (grp["estado_vda"] == "perdido").sum()),
        "litros_mes_actual":         round(float(grp["litros_mes_actual"].sum()), 2),
        "venta_neta_mes_actual":     round(float(grp["venta_neta_mes_actual"].sum()), 2),
    })

ranking_df = pd.DataFrame(ranking_rows).sort_values("venta_neta_mes_actual", ascending=False)
ranking_df.to_csv(DATASETS_OUT / "mod_vda_ranking_vendedor.csv",
                  index=False, encoding="utf-8-sig")
log(f"  -> mod_vda_ranking_vendedor.csv: {len(ranking_df)} vendedores")
for _, r in ranking_df.iterrows():
    log(f"    {r['vendedor_codigo']} | act={r['clientes_vda_mes_actual']:3d} | ant={r['clientes_vda_mes_anterior']:3d}"
        f" | +{r['ganados_o_recuperados']} -{r['perdidos']} ={r['balance_neto']:+d}"
        f" | ${r['venta_neta_mes_actual']:>14,.0f}")

# ============================================================
# TAREA 7 — JSON PORTAL GERENCIAL
# ============================================================
log("=== TAREA 7: JSON portal gerencial ===")

alertas_json = []
if resumen["clientes_ganados_o_recuperados_vda"] > 0:
    alertas_json.append({
        "tipo": "oportunidad",
        "prioridad": "media",
        "mensaje": f"{resumen['clientes_ganados_o_recuperados_vda']} clientes ganados/recuperados VDA en {mes_actual}"
    })
if resumen["clientes_perdidos_vda"] > 0:
    alertas_json.append({
        "tipo": "riesgo",
        "prioridad": "alta",
        "mensaje": f"{resumen['clientes_perdidos_vda']} clientes perdidos VDA vs {mes_anterior}"
    })
if resumen["balance_neto_clientes_vda"] < 0:
    alertas_json.append({
        "tipo": "critico",
        "prioridad": "alta",
        "mensaje": f"Balance neto VDA negativo: {resumen['balance_neto_clientes_vda']:+d} clientes"
    })

def detalle_to_records(df_subset, cols):
    return df_subset[cols].replace({np.nan: None}).to_dict(orient="records")

ganados_cols   = ["cliente", "razon_social", "vendedor_codigo", "vendedor_nombre",
                   "localidad", "segmento", "litros_mes_actual", "venta_neta_mes_actual"]
perdidos_cols  = ["cliente", "razon_social", "vendedor_codigo", "vendedor_nombre",
                   "localidad", "segmento", "litros_mes_anterior", "venta_neta_mes_anterior"]
retenidos_cols = ["cliente", "razon_social", "vendedor_codigo", "vendedor_nombre",
                   "localidad", "segmento",
                   "litros_mes_actual", "venta_neta_mes_actual",
                   "litros_mes_anterior", "venta_neta_mes_anterior",
                   "diferencia_litros", "diferencia_venta_neta"]

vda_json = {
    "meta": {
        "fecha_auditoria":      FECHA_AUDITORIA,
        "generado_en":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mes_actual":           str(mes_actual),
        "mes_anterior":         str(mes_anterior),
        "modo_datos":           "REAL",
        "fuente_productos":     "01_INPUTS/producto activos.xlsx — Categoria=Vinos del año (93 productos)",
        "fuente_ventas":        "02_HISTORY/historial_ventas.csv + 01_INPUTS/ventas.csv",
        "total_productos_vda":  len(prod_vda),
        "total_filas_vda":      len(ventas_vda),
        "excluidos":            ["V2", "V5"],
        "criterio_ccc":         "ImporteNetoItem > 0",
    },
    "resumen_mensual": resumen,
    "ranking_vendedor": ranking_df.to_dict(orient="records"),
    "clientes_ganados_o_recuperados": detalle_to_records(
        detalle[detalle["estado_vda"] == "ganado_o_recuperado"]
        .sort_values("venta_neta_mes_actual", ascending=False),
        ganados_cols
    ),
    "clientes_perdidos": detalle_to_records(
        detalle[detalle["estado_vda"] == "perdido"]
        .sort_values("venta_neta_mes_anterior", ascending=False),
        perdidos_cols
    ),
    "clientes_retenidos": detalle_to_records(
        detalle[detalle["estado_vda"] == "retenido"]
        .sort_values("venta_neta_mes_actual", ascending=False)
        .head(100),
        retenidos_cols
    ),
    "alertas": alertas_json,
    "notas_metodologicas": [
        "VDA = productos con Categoria 'Vinos del año' en maestro de productos (93 productos).",
        "Fallback: campo Tags='Vinos del Año' en Gescom para filas sin código en maestro.",
        "Litros = CantBase × (Lts_x_caja / UxC). Cero si el producto no está en el maestro.",
        "Mes actual determinado dinámicamente: max(FechaComprobante) en ventas VDA.",
        "Deduplicación historial+ventas por NroComprobante||Codigo (historial tiene prioridad).",
        "V2 y V5 excluidos en todas las métricas.",
        "V3 (Nadia Gambino): VDA no es segmento sino categoría de producto; sin filtro adicional.",
        "CCC VDA = cliente con ImporteNetoItem > 0 en al menos una línea VDA en el período.",
    ]
}

with open(APPDATA_OUT / "vda_clientes_ganados.json", "w", encoding="utf-8") as f:
    json.dump(vda_json, f, ensure_ascii=False, indent=2, default=safe_json_default)
log("  -> vda_clientes_ganados.json generado")

# ============================================================
# TAREA 1b — DIAGNÓSTICO MD
# ============================================================
log("=== TAREA 1b: diagnostico_productos_activos.md ===")

bodegas_vda   = prod_vda["bodega"].value_counts()
lineas_vda    = prod_vda["linea_comercial"].value_counts()
segmentos_vda = prod_vda["segmento"].value_counts()

diag_lines = [
    f"# Diagnóstico: producto activos.xlsx",
    f"Fecha: {FECHA_AUDITORIA}\n",
    f"## Archivo",
    f"- Ruta: `01_INPUTS/producto activos.xlsx`",
    f"- Header real: fila 3 (filas 0-2 son metadatos del archivo de referencia)",
    f"- Total productos con código numérico: **{total_prods}**\n",
    f"## Columnas (8 columnas)",
    f"| # | Columna original | Nombre normalizado | Descripción |",
    f"|---|---|---|---|",
    f"| 1 | Bodega | bodega | Bodega/empresa proveedora |",
    f"| 2 | Segmento | segmento | Segmento de precio (Premium, Alto, Superior...) |",
    f"| 3 | Linea Comercial | linea_comercial | Línea comercial específica |",
    f"| 4 | Código Art. | codigo_producto | Código numérico — clave de cruce con ventas.csv:Codigo |",
    f"| 5 | Categoria | categoria | **Categoría comercial — fuente de clasificación VDA/VDG/etc.** |",
    f"| 6 | Descripción Art. | descripcion_art | Nombre del artículo |",
    f"| 7 | Lts x caja | lts_x_caja | Litros totales por caja/envase |",
    f"| 8 | UxC | uxc | Unidades por caja (para calcular lts/unidad = lts_x_caja / uxc) |\n",
    f"## Distribución por Categoría",
]
for cat, cnt in cat_counts.items():
    diag_lines.append(f"- `{cat}`: {cnt} productos")

diag_lines += [f"\n## Distribución por Segmento"]
for seg, cnt in seg_counts.items():
    diag_lines.append(f"- `{seg}`: {cnt}")

diag_lines += [f"\n## Distribución por Bodega"]
for bod, cnt in bod_counts.items():
    diag_lines.append(f"- `{bod}`: {cnt}")

diag_lines += [
    f"\n## Productos VDA (Vinos del año): {len(prod_vda)}",
    f"**Criterio:** `categoria == 'Vinos del año'` (normalizado: sin tildes/ñ)\n",
    f"### Bodegas VDA",
]
for b, c in bodegas_vda.items():
    diag_lines.append(f"- `{b}`: {c}")

diag_lines += [f"\n### Segmentos VDA"]
for s, c in segmentos_vda.items():
    diag_lines.append(f"- `{s}`: {c}")

diag_lines += [f"\n### Líneas Comerciales VDA (top 10)"]
for l, c in lineas_vda.head(10).items():
    diag_lines.append(f"- `{l}`: {c}")

diag_lines += [
    f"\n## Clasificaciones disponibles desde el maestro",
    f"| Clasificación | Criterio | Productos |",
    f"|---|---|---|",
    f"| VDA | `categoria == 'Vinos del año'` | {len(prod_vda)} |",
    f"| VDG | `categoria == 'Vinos de guarda'` | {cat_counts.get('Vinos de guarda', 0)} |",
    f"| Espumantes | `categoria == 'Espumantes'` | {cat_counts.get('Espumantes', 0)} |",
    f"| Whisky | `categoria in ['Whisky', 'Whisky (Maltas)']` | {cat_counts.get('Whisky',0) + cat_counts.get('Whisky (Maltas)',0)} |",
    f"| Cerveza Artesanal | `categoria == 'Cerveza Artesanal'` | {cat_counts.get('Cerveza Artesanal',0)} |",
    f"| Vodka | `categoria == 'Vodka'` | {cat_counts.get('Vodka',0)} |",
    f"| Gin | `categoria == 'Gin'` | {cat_counts.get('Gin',0)} |",
    f"| Vinos de Mesa | `categoria == 'Vinos de Mesa'` | {cat_counts.get('Vinos de Mesa',0)} |",
    f"\n## Nota: Tags en ventas.csv / historial_ventas.csv",
    f"El campo `Tags` de Gescom contiene valores como `Vinos del Año`, `PEÑAFLOR GRUPO OBJETIVO`, etc.",
    f"Se usa como **fallback** de clasificación VDA para filas cuyo `Codigo` no figura en el maestro.",
    f"La fuente oficial es siempre el maestro de productos.\n",
    f"## Nota: Encoding",
    f"El archivo tiene un problema de codificación interna (caracteres `ñ`, `á` aparecen como `?` al leer con Python).",
    f"El procesamiento usa `unicodedata.normalize` para comparar sin diacríticos.",
    f"Se recomienda exportar una versión limpia desde Gescom o guardar el Excel con encoding UTF-8.\n",
    f"## Archivos generados",
    f"- `04_DATASETS_ORBIT/mod_vda_productos.csv` — {len(prod_vda)} productos VDA",
    f"- `04_DATASETS_ORBIT/mod_vda_productos_revision_necesaria.csv` — {len(prod_no_vda)} no-VDA (referencia)",
]

with open(DATASETS_OUT / "diagnostico_productos_activos.md", "w", encoding="utf-8") as f:
    f.write("\n".join(diag_lines))
log("  -> diagnostico_productos_activos.md generado")

# ============================================================
# TAREA 8 — REPORTE FINAL
# ============================================================
log("=== TAREA 8: Reporte final MODULO_VDA_CLIENTES_GANADOS_2026-05-12.md ===")

top_ganados  = detalle[detalle["estado_vda"] == "ganado_o_recuperado"].sort_values("venta_neta_mes_actual",  ascending=False).head(15)
top_perdidos = detalle[detalle["estado_vda"] == "perdido"].sort_values("venta_neta_mes_anterior", ascending=False).head(15)

def tabla_clientes(df_sub, cols_show):
    if len(df_sub) == 0:
        return "*(sin datos)*\n"
    lines = []
    for _, r in df_sub.iterrows():
        row_vals = []
        for c in cols_show:
            v = r.get(c, "")
            if isinstance(v, float):
                row_vals.append(f"${v:,.0f}" if "venta" in c else f"{v:,.1f}" if "litro" in c else str(round(v, 2)))
            else:
                row_vals.append(str(v)[:35] if isinstance(v, str) else str(v))
        lines.append("| " + " | ".join(row_vals) + " |")
    return "\n".join(lines) + "\n"

ranking_tabla = ""
for _, r in ranking_df.iterrows():
    ranking_tabla += (
        f"| {r['vendedor_codigo']} | {str(r['vendedor_nombre'])[:25]} "
        f"| {r['clientes_vda_mes_actual']} | {r['clientes_vda_mes_anterior']} "
        f"| {r['ganados_o_recuperados']:+d} | {r['perdidos']:+d} | {r['balance_neto']:+d} "
        f"| {r['litros_mes_actual']:,.1f} | ${r['venta_neta_mes_actual']:,.0f} |\n"
    )

ganados_tabla  = tabla_clientes(top_ganados,  ["cliente","razon_social","vendedor_codigo","localidad","litros_mes_actual","venta_neta_mes_actual"])
perdidos_tabla = tabla_clientes(top_perdidos, ["cliente","razon_social","vendedor_codigo","localidad","litros_mes_anterior","venta_neta_mes_anterior"])

fecha_min_vda = ventas_vda["FechaComprobante"].min().strftime("%Y-%m-%d")
fecha_max_vda = ventas_vda["FechaComprobante"].max().strftime("%Y-%m-%d")

reporte = f"""# MÓDULO VDA — CLIENTES GANADOS
## Orbit Matinal Peñaflor · {FECHA_AUDITORIA}

---

## Diagnóstico del maestro de productos

| Atributo | Valor |
|---|---|
| Archivo | `01_INPUTS/producto activos.xlsx` |
| Header real | Fila 3 (filas 0-2 son metadatos) |
| Total productos | **{total_prods}** |
| Columnas | bodega, segmento, linea_comercial, codigo_producto, categoria, descripcion_art, lts_x_caja, uxc |
| Productos VDA | **{len(prod_vda)}** (`categoria == "Vinos del año"`) |
| Productos VDG | {cat_counts.get('Vinos de guarda', 0)} |
| Espumantes | {cat_counts.get('Espumantes', 0)} |
| Whisky | {cat_counts.get('Whisky',0) + cat_counts.get('Whisky (Maltas)',0)} |
| Cerveza Artesanal | {cat_counts.get('Cerveza Artesanal',0)} |
| Encoding | Problema detectado (ñ/á aparecen como ?) — procesado con normalización unicode |

## Criterio VDA

**Fuente primaria:** `categoria == "Vinos del año"` en `producto activos.xlsx` (cruce por `Codigo` = `código_producto`).
**Fallback:** `Tags == "Vinos del Año"` en Gescom para filas cuyo código no figura en el maestro.
**CCC VDA:** cliente con `ImporteNetoItem > 0` en al menos una línea VDA en el período.
**Litros VDA:** `CantBase × (lts_x_caja / uxc)`.

## Fuentes usadas

| Fuente | Ruta | Filas / Tamaño | Período |
|---|---|---|---|
| Maestro productos | `01_INPUTS/producto activos.xlsx` | {total_prods} productos | — |
| Historial ventas | `02_HISTORY/historial_ventas.csv` | ~129.080 filas / 63 MB | 2024-03-01 a 2026-05-04 |
| Ventas actuales | `01_INPUTS/ventas.csv` | ~962 filas | hasta 2026-05-11 |
| Maestro clientes | `01_INPUTS/clientes.xlsx` | 2.001 clientes | — |

**Deduplicación:** por `NroComprobante||Codigo` al combinar historial + ventas. El historial tiene prioridad.
**Excluidos:** V2 y V5 en todas las métricas.

## Rango de fechas analizado

- Rango VDA total: `{fecha_min_vda}` a `{fecha_max_vda}`
- **Mes actual:** {mes_actual}
- **Mes anterior:** {mes_anterior}
- Total filas VDA procesadas: **{len(ventas_vda):,}** (maestro: {vda_maestro.sum():,} | tags fallback: {vda_tags.sum():,})

## Productos VDA detectados

- **{len(prod_vda)} productos** con `categoria = "Vinos del año"`
- Bodegas: {", ".join([f"{b} ({c})" for b, c in bodegas_vda.head(8).items()])}
- Top líneas: {", ".join(lineas_vda.head(5).index.tolist())}

---

## Resumen ejecutivo

| Métrica | Mes actual ({mes_actual}) | Mes anterior ({mes_anterior}) | Variación |
|---|---|---|---|
| Clientes VDA | **{resumen['clientes_vda_mes_actual']}** | {resumen['clientes_vda_mes_anterior']} | {resumen['clientes_vda_mes_actual'] - resumen['clientes_vda_mes_anterior']:+d} |
| Litros VDA | **{resumen['litros_vda_mes_actual']:,.1f}** | {resumen['litros_vda_mes_anterior']:,.1f} | {resumen['litros_vda_mes_actual'] - resumen['litros_vda_mes_anterior']:+,.1f} |
| Venta Neta VDA | **${resumen['venta_neta_vda_mes_actual']:,.0f}** | ${resumen['venta_neta_vda_mes_anterior']:,.0f} | ${resumen['venta_neta_vda_mes_actual'] - resumen['venta_neta_vda_mes_anterior']:+,.0f} |
| **Ganados/recuperados** | **{resumen['clientes_ganados_o_recuperados_vda']}** | — | — |
| **Perdidos** | **{resumen['clientes_perdidos_vda']}** | — | — |
| **Retenidos** | **{resumen['clientes_retenidos_vda']}** | — | — |
| **Balance neto** | **{resumen['balance_neto_clientes_vda']:+d}** | — | — |

> ⚠ El mes actual ({mes_actual}) está **incompleto** (datos hasta {fecha_max_vda}).
> Las métricas de clientes actuales crecerán hasta el cierre del mes.

---

## Clientes ganados o recuperados VDA (top 15 por venta neta)

| Cliente | Razón Social | Vendedor | Localidad | Litros | Venta Neta |
|---|---|---|---|---|---|
{ganados_tabla}

---

## Clientes perdidos VDA (top 15 por venta neta anterior)

| Cliente | Razón Social | Vendedor | Localidad | Litros ant. | Venta Neta ant. |
|---|---|---|---|---|---|
{perdidos_tabla}

---

## Ranking por vendedor

| Vendedor | Nombre | Act. | Ant. | Ganados | Perdidos | Balance | Litros | Venta Neta |
|---|---|---|---|---|---|---|---|---|
{ranking_tabla}

---

## Problemas detectados

1. **Encoding roto en `producto activos.xlsx`** — `ñ`, `á`, `é` aparecen como `?` al leer con Python. El procesamiento usa normalización unicode para comparar categorías correctamente. Recomendación: exportar desde Gescom con UTF-8.

2. **Mes actual incompleto** — Datos VDA del mes actual hasta {fecha_max_vda}. Las métricas de clientes actuales, litros y venta neta son parciales. El balance neto puede cambiar.

3. **Litros = 0 para VDA por Tags** — Los {vda_tags.sum():,} registros identificados por fallback (Tags) no tienen `lts_x_caja` disponible en el maestro -> `litros = 0`. Se puede resolver enriqueciendo el maestro o cruzando por descripción de artículo.

4. **Sin segmento del cliente en la base VDA** — El campo `Ramo` en ventas.csv representa el ramo del cliente tal como aparece en la transacción, no el segmento normalizado del maestro de clientes. Para segmentar correctamente hay que cruzar con `clientes.xlsx`.

---

## Validaciones pendientes

1. Confirmar que `Codigo` en ventas.csv = `codigo_producto` en maestro (cruce 1:1).
2. Revisar los {vda_tags.sum():,} registros VDA por Tags — ¿están todos en el maestro bajo otro código?
3. Validar litros calculados para un vendedor muestra contra registro físico.
4. Cruzar marcas VDA del maestro contra `MAP_11T_FINE` en `orbit_matinal_v42.py` — verificar coherencia.
5. Confirmar el criterio de "cliente recuperado" vs "cliente ganado" (¿tiene historia VDA anterior al mes anterior?).

---

## Próximos pasos

1. Integrar `mod_vda_ventas_base.csv` en `orbit_matinal_v42.py` como módulo oficial del pipeline diario.
2. Agregar hoja `mod_vda` en `MATINAL_PENA_V42.xlsx` para que `datasets_orbit.py` la exporte automáticamente.
3. Exponer `/api/vda` en `server_orbit.py` sirviendo `vda_clientes_ganados.json`.
4. Integrar panel VDA en el portal gerencial (pantalla de evolución de clientes).
5. Resolver encoding de `producto activos.xlsx` — exportar desde Gescom con UTF-8.

---

## Archivos generados por este módulo

| Archivo | Filas/Contenido | Descripción |
|---|---|---|
| `04_DATASETS_ORBIT/diagnostico_productos_activos.md` | — | Diagnóstico completo del maestro de productos |
| `04_DATASETS_ORBIT/mod_vda_productos.csv` | {len(mod_vda_productos)} | Productos VDA confirmados con litros/unidad |
| `04_DATASETS_ORBIT/mod_vda_productos_revision_necesaria.csv` | {len(mod_vda_revision)} | Productos no-VDA (referencia) |
| `04_DATASETS_ORBIT/mod_vda_ventas_base.csv` | {len(ventas_vda):,} | Todas las ventas VDA históricas + actuales |
| `04_DATASETS_ORBIT/mod_vda_resumen_mensual.csv` | 1 | Resumen mensual VDA |
| `04_DATASETS_ORBIT/mod_vda_clientes_detalle.csv` | {len(detalle)} | Detalle por cliente con estado VDA |
| `04_DATASETS_ORBIT/mod_vda_ranking_vendedor.csv` | {len(ranking_df)} | Ranking por vendedor |
| `06_APP_DATA/vda_clientes_ganados.json` | — | JSON para portal gerencial futuro |
| `MODULO_VDA_CLIENTES_GANADOS_2026-05-12.md` | — | Este reporte |

*Generado por `_tmp_auditoria_vda.py` · Sin modificación de portal, Flask, AppScript ni código principal.*
"""

with open(BASE / "MODULO_VDA_CLIENTES_GANADOS_2026-05-12.md", "w", encoding="utf-8") as f:
    f.write(reporte)
log("  -> MODULO_VDA_CLIENTES_GANADOS_2026-05-12.md generado")

# ============================================================
# RESUMEN FINAL EN CONSOLA
# ============================================================
log("")
log("=" * 60)
log("MÓDULO VDA COMPLETADO")
log("=" * 60)
log(f"  Productos VDA en maestro:   {len(prod_vda)}")
log(f"  Filas VDA totales:          {len(ventas_vda):,}")
log(f"  Mes actual ({mes_actual}):  {len(cli_act)} clientes")
log(f"  Mes anterior ({mes_anterior}): {len(cli_ant)} clientes")
log(f"  Ganados/recuperados:        {len(ganados)}")
log(f"  Perdidos:                   {len(perdidos)}")
log(f"  Retenidos:                  {len(retenidos)}")
log(f"  Balance neto:               {len(ganados)-len(perdidos):+d}")
log(f"  Litros mes actual:          {resumen['litros_vda_mes_actual']:,.1f}")
log(f"  Venta neta mes actual:      ${resumen['venta_neta_vda_mes_actual']:,.0f}")
log("=" * 60)
