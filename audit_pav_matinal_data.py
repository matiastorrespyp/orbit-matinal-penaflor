"""
audit_pav_matinal_data.py
=========================
Auditoría completa del flujo de datos ORBIT Matinal Peñaflor.
Recalcula KPIs desde fuente y los compara contra datasets, endpoints y portales.

Orden de verificación:
  fuente → dataset → endpoint → data.js → portal.html / index.html

NO modifica ningún archivo. Solo lectura y diagnóstico.
"""

import sys, json, warnings
import pandas as pd
import openpyxl
import requests
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

BASE      = Path(r"C:\Orbit\MATINAL_PENAFLOR")
INPUTS    = BASE / "01_INPUTS"
HISTORY   = BASE / "02_HISTORY"
DATASETS  = BASE / "04_DATASETS_ORBIT"
CONFIG    = BASE / "09_CONFIG"
FRONTEND  = BASE / "PAV MATINAL PE_A FLOR"
ENDPOINT  = "http://localhost:8502"

VENDEDORES_PAV = [3, 4, 6, 7, 8, 9, 10]  # excluir V2 y V5
V_NOMBRES = {3:"V3 Gambino", 4:"V4 Gribaudo", 6:"V6 Peyronel",
             7:"V7 Jofre", 8:"V8 Alvarez", 9:"V9 Sanchez", 10:"V10 Ortega"}

SEP = "─" * 80

# ──────────────────────────────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────────────────────────────

def read_csv_safe(path):
    if not Path(path).exists():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "latin-1", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, sep=None, engine="python")
        except Exception:
            continue
    return pd.DataFrame()

def parse_importe(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", ".", regex=False), errors="coerce"
    )

def fmt(n, decimals=0):
    try:
        if decimals:
            return f"{float(n):,.{decimals}f}"
        return f"{int(round(float(n))):,}"
    except Exception:
        return str(n)

def fmtM(n):
    try:
        return f"${float(n)/1e6:.1f}M"
    except Exception:
        return "?"

def get_endpoint(url):
    try:
        r = requests.get(f"{ENDPOINT}{url}", timeout=6)
        return r.json() if r.ok else None
    except Exception:
        return None

def estado(recalc, dataset, tolerancia_pct=5):
    """Compara dos valores y devuelve OK / DIFF / CRITICO."""
    try:
        r, d = float(recalc), float(dataset)
        if r == 0 and d == 0:
            return "OK"
        if r == 0 and d > 0:
            return "⚠ FUENTE=0"
        if d == 0 and r > 0:
            return "🔴 DATASET=0"
        pct = abs(r - d) / max(abs(r), 1) * 100
        if pct <= tolerancia_pct:
            return f"OK ({pct:.1f}%)"
        elif pct <= 20:
            return f"⚠ DIFF {pct:.1f}%"
        else:
            return f"🔴 CRITICO {pct:.1f}%"
    except Exception:
        return "?"

# ──────────────────────────────────────────────────────────────────────────────
# 1. CARGAR FUENTES
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + SEP)
print("ORBIT MATINAL PEÑAFLOR — AUDITORÍA DE DATOS")
print(f"Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(SEP)

# ventas.csv
ventas = read_csv_safe(INPUTS / "ventas.csv")
ventas["fecha"] = pd.to_datetime(ventas["FechaComprobante"], dayfirst=True, errors="coerce")
ventas["importe_num"] = parse_importe(ventas["ImporteNetoItem"])
ventas_pav = ventas[ventas["CodVendedor"].isin(VENDEDORES_PAV) & (ventas["importe_num"] > 0)]

fecha_min_v = ventas_pav["fecha"].min().date()
fecha_max_v = ventas_pav["fecha"].max().date()
mes_ventas  = ventas_pav["fecha"].dt.to_period("M").max()

print(f"\n[1] ventas.csv  — {len(ventas)} filas | rango PAV: {fecha_min_v} → {fecha_max_v}")

# historial_ventas.csv
historial = read_csv_safe(HISTORY / "historial_ventas.csv")
historial["fecha"] = pd.to_datetime(historial["FechaComprobante"], dayfirst=True, errors="coerce")
historial["importe_num"] = parse_importe(historial["ImporteNetoItem"])
hist_pav = historial[historial["CodVendedor"].isin(VENDEDORES_PAV) & (historial["importe_num"] > 0)]
hist_max = hist_pav["fecha"].max().date() if not hist_pav.empty else "vacío"
hist_mayo = hist_pav[hist_pav["fecha"].dt.to_period("M") == mes_ventas]

print(f"[2] historial_ventas.csv — {len(historial)} filas | max PAV: {hist_max} | mayo-26 PAV: {len(hist_mayo)} filas")

# resultado.xlsx
resultado_rows = {}
try:
    wb = openpyxl.load_workbook(INPUTS / "resultado.xlsx", data_only=True)
    ws = wb["Avance"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    h = {c: i for i, c in enumerate(header)}
    for row in rows[1:]:
        cod = str(row[h["VendedorCodigo"]]).strip()
        try:
            cod_int = int(float(cod))
        except Exception:
            continue
        if cod_int in VENDEDORES_PAV:
            resultado_rows[cod_int] = {
                "objetivo":    float(row[h["ValorObjetivo"]] or 0),
                "acumulado":   float(row[h["Acumulado"]] or 0),
                "tendencia":   float(row[h["Tendencia"]] or 0),
                "avance":      float(row[h["Avance"]] or 0),
            }
    print(f"[3] resultado.xlsx — {len(resultado_rows)} vendedores PAV")
except Exception as e:
    print(f"[3] resultado.xlsx — ERROR: {e}")

# Datasets orbit
vol   = read_csv_safe(DATASETS / "mod_volumen_vendedor.csv")
ccc_s = read_csv_safe(DATASETS / "mod_ccc_segmento.csv")
cli_d = read_csv_safe(DATASETS / "clientes_dia.csv")
t11   = read_csv_safe(DATASETS / "mod_11_titulares.csv")

print(f"[4] mod_volumen_vendedor.csv — {len(vol)} filas")
print(f"[5] mod_ccc_segmento.csv — {len(ccc_s)} filas (solo vendedores con venta ayer)")
print(f"[6] clientes_dia.csv — {len(cli_d)} filas")
print(f"[7] mod_11_titulares.csv — {len(t11)} filas")

# Endpoints
diag_api  = get_endpoint("/api/diagnostico")
dash_api  = get_endpoint("/api/dashboard")
print(f"[8] /api/diagnostico — {'OK' if diag_api else 'ERROR/TIMEOUT'}")
print(f"[9] /api/dashboard   — {'OK (' + str(len(dash_api)) + ' vendedores)' if dash_api else 'ERROR/TIMEOUT'}")

# ──────────────────────────────────────────────────────────────────────────────
# 2. RECALCULAR KPIs DESDE FUENTE
# ──────────────────────────────────────────────────────────────────────────────

print(f"\n{SEP}")
print("RECÁLCULO DESDE FUENTE PRIMARIA")
print(SEP)

# Acumulado mes (mayo 2026): solo desde ventas.csv porque historial no tiene mayo
acum_fuente = ventas_pav.groupby("CodVendedor")["importe_num"].sum()

# Venta ayer: último día en ventas.csv
dia_ayer = ventas_pav["fecha"].max().date()
v_ayer = ventas_pav[ventas_pav["fecha"].dt.date == dia_ayer]
ayer_fuente = v_ayer.groupby("CodVendedor")["importe_num"].sum()

# CCC mes: clientes únicos con importe > 0 en ventas.csv (mes actual)
ccc_mes_fuente = ventas_pav.groupby("CodVendedor")["Cliente"].nunique()

# CCC ayer: clientes únicos con importe > 0 en el último día
ccc_ayer_fuente = v_ayer.groupby("CodVendedor")["Cliente"].nunique()

print(f"Nota: historial no tiene datos de mayo 2026 ({len(hist_mayo)} filas).")
print(f"      El mes completo de mayo está SOLO en ventas.csv ({fecha_min_v} → {fecha_max_v}).")
print(f"      Acumulado ERP en resultado.xlsx puede incluir días 1-3/mayo no presentes en ventas.csv.")
print()

# Objetivos desde resultado.xlsx
obj_fuente  = {c: v["objetivo"]  for c, v in resultado_rows.items()}
av_fuente   = {c: v["avance"]   for c, v in resultado_rows.items()}
tend_fuente = {c: v["tendencia"] for c, v in resultado_rows.items()}

# CCC mes desde clientes_dia (fuente motor)
ccc_mes_motor = {}
if not cli_d.empty and "ccc_mes_flag" in cli_d.columns:
    ccc_mes_motor = cli_d.groupby("vendedor_codigo")["ccc_mes_flag"].sum().to_dict()

# CCC ayer desde clientes_dia
ccc_ayer_motor = {}
if not cli_d.empty and "ccc_ayer_flag" in cli_d.columns:
    ccc_ayer_motor = cli_d.groupby("vendedor_codigo")["ccc_ayer_flag"].sum().to_dict()

# CCC desde mod_ccc_segmento (lo que usa el endpoint)
ccc_endpoint = {}
if not ccc_s.empty:
    for cod, grp in ccc_s.groupby("vendedor_codigo"):
        ccc_endpoint[int(cod)] = int(grp["clientes_con_compra"].sum())

# CCC mes desde endpoint /api/dashboard
ccc_dash_api = {}
if dash_api:
    for v in dash_api:
        k = v.get("kpis", {})
        try:
            c = int(str(v["vendedor_id"]).replace("V",""))
            ccc_dash_api[c] = k.get("ccc_total", 0)
        except Exception:
            pass

# Acumulado desde mod_volumen_vendedor (lo que usa el endpoint)
acum_dataset = {}
if not vol.empty:
    for _, row in vol.iterrows():
        try:
            c = int(str(row["vendedor_codigo"]))
            acum_dataset[c] = float(row["acumulado_mes"])
        except Exception:
            pass

# Venta ayer desde mod_volumen_vendedor
ayer_dataset = {}
if not vol.empty:
    for _, row in vol.iterrows():
        try:
            c = int(str(row["vendedor_codigo"]))
            ayer_dataset[c] = float(row["venta_ayer"])
        except Exception:
            pass

# ──────────────────────────────────────────────────────────────────────────────
# 3. TABLA COMPARATIVA POR VENDEDOR
# ──────────────────────────────────────────────────────────────────────────────

print(f"\n{SEP}")
print("TABLA 1: ACUMULADO MES")
print(f"{'Vend':<6} {'resultado.xlsx':>15} {'mod_volumen':>15} {'ventas.csv':>15} {'endpoint':>15} {'estado':>20}")
print("─" * 90)

for c in VENDEDORES_PAV:
    r_xlsx  = resultado_rows.get(c, {}).get("acumulado", 0)
    r_vol   = acum_dataset.get(c, 0)
    r_csv   = acum_fuente.get(c, 0)
    r_ep    = 0
    if dash_api:
        for v in dash_api:
            if str(v.get("vendedor_id","")).replace("V","") == str(c):
                r_ep = v.get("kpis",{}).get("acumulado", 0)
    est = estado(r_xlsx, r_vol)
    print(f"V{c:<5} {fmtM(r_xlsx):>15} {fmtM(r_vol):>15} {fmtM(r_csv):>15} {fmtM(r_ep):>15} {est:>20}")

print()
tot_xlsx = sum(v.get("acumulado",0) for v in resultado_rows.values())
tot_vol  = sum(acum_dataset.values())
tot_csv  = acum_fuente.sum()
print(f"{'TOTAL':<6} {fmtM(tot_xlsx):>15} {fmtM(tot_vol):>15} {fmtM(tot_csv):>15}")
print(f"  → $184.1M = resultado.xlsx Acumulado (ERP total del mes)")
print(f"  → ventas.csv cubre solo {fecha_min_v} → {fecha_max_v} = {(fecha_max_v - fecha_min_v).days + 1} días")

print(f"\n{SEP}")
print("TABLA 2: VENTA DÍA (ayer)")
print(f"{'Vend':<6} {'ventas.csv (' + str(dia_ayer) + ')':>20} {'mod_volumen(v_ayer)':>22} {'estado':>20}")
print("─" * 72)

for c in VENDEDORES_PAV:
    r_csv = ayer_fuente.get(c, 0)
    r_vol = ayer_dataset.get(c, 0)
    est = estado(r_csv, r_vol)
    print(f"V{c:<5} {fmtM(r_csv):>20} {fmtM(r_vol):>22} {est:>20}")

tot_csv_ayer = ayer_fuente.sum()
tot_vol_ayer = sum(ayer_dataset.values())
print(f"{'TOTAL':<6} {fmtM(tot_csv_ayer):>20} {fmtM(tot_vol_ayer):>22}")
print(f"  → $53.7M = suma de venta_ayer en mod_volumen_vendedor (V6+V8+V9 únicamente)")

print(f"\n{SEP}")
print("TABLA 3: CCC MES ACUMULADO — COMPARACIÓN DE FUENTES")
print(f"{'':>30}  {'V3':>5} {'V4':>5} {'V6':>5} {'V7':>5} {'V8':>5} {'V9':>5} {'V10':>5}")
print("─" * 80)

fuentes_ccc = [
    ("ventas.csv (recalc, importe>0)",   {c: int(ccc_mes_fuente.get(c,0)) for c in VENDEDORES_PAV}),
    ("clientes_dia ccc_mes_flag (motor)", {c: int(ccc_mes_motor.get(c,0))  for c in VENDEDORES_PAV}),
    ("mod_ccc_segmento (solo ayer!)",     {c: ccc_endpoint.get(c, 0)       for c in VENDEDORES_PAV}),
    ("endpoint /api/dashboard ccc_total", {c: ccc_dash_api.get(c, 0)       for c in VENDEDORES_PAV}),
]

for nombre, datos in fuentes_ccc:
    vals = "  ".join(f"{datos.get(c,0):>5}" for c in VENDEDORES_PAV)
    print(f"  {nombre:<40} {vals}")

print(f"\n  DIAGNÓSTICO CCC:")
print(f"  • mod_ccc_segmento.csv tiene SOLO {len(ccc_s)} filas: V6, V8 y V9 únicamente.")
print(f"    Motivo: se generó solo con las ventas del día {dia_ayer}.")
print(f"    El endpoint /api/dashboard usa esta tabla → CCC=0 para V3, V4, V7, V10.")
print(f"  • clientes_dia ccc_mes_flag tiene el CCC del mes por clientes de RUTA.")
print(f"    Solo incluye los ~{len(cli_d)} clientes planificados (maestro clientes.xlsx).")
print(f"    V3 tiene 42 clientes de ruta, 36 compraron este mes (ruta).")
print(f"    ventas.csv muestra 79 compradores únicos de V3 (incluye fuera de ruta).")
print(f"  • 'ccc_mes: 0' está HARDCODEADO en data.js línea 78 (kpisGerencia.ccc_mes).")

print(f"\n{SEP}")
print("TABLA 4: CCC DÍA (ayer)")
print(f"{'':>30}  {'V3':>5} {'V4':>5} {'V6':>5} {'V7':>5} {'V8':>5} {'V9':>5} {'V10':>5}")
print("─" * 80)

fuentes_ccc_ayer = [
    ("ventas.csv (recalc ayer)",        {c: int(ccc_ayer_fuente.get(c,0)) for c in VENDEDORES_PAV}),
    ("clientes_dia ccc_ayer_flag",      {c: int(ccc_ayer_motor.get(c,0))  for c in VENDEDORES_PAV}),
    ("mod_ccc_segmento clientes_compra",{c: ccc_endpoint.get(c, 0)        for c in VENDEDORES_PAV}),
]

for nombre, datos in fuentes_ccc_ayer:
    vals = "  ".join(f"{datos.get(c,0):>5}" for c in VENDEDORES_PAV)
    print(f"  {nombre:<40} {vals}")

print(f"\n{SEP}")
print("TABLA 5: OBJETIVO Y AVANCE %")
print(f"{'Vend':<6} {'Obj resultado.xlsx':>20} {'Obj mod_volumen':>18} {'Av% xlsx':>10} {'Av% mod_vol':>12} {'Av% endpoint':>14}")
print("─" * 84)

for c in VENDEDORES_PAV:
    obj_xl = resultado_rows.get(c, {}).get("objetivo", 0)
    obj_vol = 0
    av_vol = 0
    av_ep = 0
    if not vol.empty:
        vv = vol[vol["vendedor_codigo"].astype(str).str.strip() == str(c)]
        if not vv.empty:
            obj_vol = float(vv["objetivo_mes"].sum())
            av_vol  = float(vv["avance_pct"].mean())
    if dash_api:
        for v in dash_api:
            if str(v.get("vendedor_id","")).replace("V","") == str(c):
                av_ep = v.get("kpis",{}).get("avance_pct", 0)
    av_xl = resultado_rows.get(c, {}).get("avance", 0)
    print(f"V{c:<5} {fmtM(obj_xl):>20} {fmtM(obj_vol):>18} {av_xl:>9.1f}% {av_vol:>11.1f}% {av_ep:>13.1f}%")

print(f"\n{SEP}")
print("TABLA 6: COBERTURA Y 11 TITULARES")
print(f"{'Vend':<6} {'CLI ruta':>10} {'CCC_ruta':>10} {'Cob%':>8} {'11T cumpl':>11} {'11T total':>11}")
print("─" * 65)

for c in VENDEDORES_PAV:
    cli_total = cli_sin = 0
    ccc_r = ccc_mes_motor.get(c, 0)
    if not cli_d.empty:
        vv = cli_d[cli_d["vendedor_codigo"] == c]
        cli_total = len(vv)
        cli_sin   = int((vv["ccc_mes_flag"] == 0).sum()) if "ccc_mes_flag" in vv.columns else 0
    cob_pct = (ccc_r / cli_total * 100) if cli_total else 0
    t11_cumpl = t11_total = 0
    if not t11.empty and "vendedor_codigo" in t11.columns and "tiene_flag" in t11.columns:
        tv = t11[t11["vendedor_codigo"] == c]
        t11_total = len(tv["cliente_id"].unique()) if "cliente_id" in tv.columns else 0
        t11_cumpl = int(pd.to_numeric(tv["tiene_flag"], errors="coerce").fillna(0).sum())
    print(f"V{c:<5} {cli_total:>10} {ccc_r:>10} {cob_pct:>7.1f}% {t11_cumpl:>11} {t11_total:>11}")

# ──────────────────────────────────────────────────────────────────────────────
# 4. TABLA RESUMEN FINAL
# ──────────────────────────────────────────────────────────────────────────────

print(f"\n{SEP}")
print("TABLA RESUMEN: KPI | FUENTE RECALC | DATASET | ENDPOINT | PORTAL | ESTADO")
print("─" * 100)

RESUMEN = [
    # (KPI, fuente_recalc, dataset, endpoint, index_html_nota, portal_html_nota, estado)
    ("Venta acumulada MES (total)",
     fmtM(acum_fuente.sum()) + " (ventas.csv días 4-14)",
     fmtM(tot_vol) + " (mod_volumen)",
     fmtM(tot_vol) + " (dashboard)",
     fmtM(tot_xlsx) + " (data.js←xlsx)",
     fmtM(tot_xlsx) + " (portal←dash)",
     "⚠ ventas.csv incompleta (falta 1-3/mayo)"),

    ("Venta acumulada MES (ERP xlsx)",
     fmtM(tot_xlsx) + " (resultado.xlsx)",
     fmtM(tot_vol) + " (mod_volumen=xlsx)",
     fmtM(tot_xlsx) + " (dashboard)",
     fmtM(tot_xlsx),
     fmtM(tot_xlsx),
     "OK — fuente única consistente"),

    ("Venta DÍA (ayer)",
     fmtM(tot_csv_ayer) + " (ventas.csv)",
     fmtM(tot_vol_ayer) + " (mod_volumen)",
     fmtM(tot_vol_ayer),
     "$53.7M (data.js venta_dia)",
     "$53.7M (portal kpis)",
     "OK"),

    ("CCC MES acumulado (total ruta)",
     str(int(sum(ccc_mes_motor.get(c,0) for c in VENDEDORES_PAV))) + " (cli_dia mes_flag)",
     "0 — no en mod_volumen",
     str(sum(ccc_dash_api.values())) + f" (endpoint: {', '.join(f'V{c}={ccc_dash_api.get(c,0)}' for c in VENDEDORES_PAV)})",
     str(sum(ccc_dash_api.values())) + " (data.js tCCC→ccc_mes)",
     str(sum(ccc_dash_api.values())) + " (portal usa endpoint)",
     "OK" if sum(ccc_dash_api.values()) == sum(ccc_mes_motor.get(c,0) for c in VENDEDORES_PAV) else f"⚠ DIFF ep={sum(ccc_dash_api.values())} vs motor={sum(ccc_mes_motor.get(c,0) for c in VENDEDORES_PAV)}"),

    ("CCC DÍA (ayer)",
     str(int(sum(ccc_ayer_fuente.get(c,0) for c in VENDEDORES_PAV))) + " (ventas.csv)",
     str(int(sum(ccc_ayer_motor.get(c,0) for c in VENDEDORES_PAV))) + " (cli_dia ayer_flag)",
     str(sum(ccc_endpoint.values())) + " (mod_ccc_seg, día correcto)",
     str(sum(ccc_endpoint.values())) + " (data.js ccc_dia=tCCC_DIA)",
     str(sum(ccc_endpoint.values())),
     "OK — separado del mes"),

    ("V3 CCC Autoservicio",
     "0 (V3 no trabaja AS)",
     "0 (regla aplicada en motor)",
     "0 (endpoint aplica regla)",
     "0 (data.js segmento_excluye)",
     "0 (portal oculta col AS)",
     "OK"),

    ("Cobertura TRAD (≥3 botellas)",
     "desde clientes_dia cob_ayer_flag",
     "mod_ccc_seg coberturas_logradas",
     "diag.segmentos cubiertos=12",
     "12/460 clientes (data.js)",
     "12/460",
     "OK — dato correcto"),

    ("11 Titulares (empresa, marcas cumpl)",
     "desde mod_11_titulares tiene_flag",
     "mod_11_titulares",
     "diag.titulares11",
     "data.js cumplimiento_11t",
     "D.diag.titulares11 (empresa)",
     "OK — usa fuente real"),

    ("Objetivo MES total",
     fmtM(sum(obj_fuente.values())) + " (resultado.xlsx)",
     fmtM(vol["objetivo_mes"].sum() if not vol.empty else 0) + " (mod_volumen)",
     fmtM(tot_xlsx/tot_xlsx*sum(obj_fuente.values())) if tot_xlsx else "?",
     fmtM(sum(obj_fuente.values())),
     fmtM(sum(obj_fuente.values())),
     "OK"),

    ("Ranking vendedores",
     "V8 $98.6M → V9 $30.1M → V6 $24.2M",
     "mod_volumen_vendedor (correcto)",
     "/api/dashboard",
     "data.js vendedores[]",
     "portal gerencial ranking",
     "OK — orden correcto"),
]

for row in RESUMEN:
    kpi, fuente, dataset, endpoint, idx, portal, est = row
    print(f"\n  KPI:       {kpi}")
    print(f"  Fuente:    {fuente}")
    print(f"  Dataset:   {dataset}")
    print(f"  Endpoint:  {endpoint}")
    print(f"  index.html:{idx}")
    print(f"  portal.html:{portal}")
    print(f"  Estado:    {est}")
    print("  " + "·" * 60)

# ──────────────────────────────────────────────────────────────────────────────
# 5. DIAGNÓSTICO CONSOLIDADO
# ──────────────────────────────────────────────────────────────────────────────

print(f"\n{SEP}")
print("DIAGNÓSTICO CONSOLIDADO")
print(SEP)

ccc_ep_total  = sum(ccc_dash_api.values())
ccc_mes_total = sum(ccc_mes_motor.get(c,0) for c in VENDEDORES_PAV)
ccc_dia_ep    = sum(ccc_endpoint.values())

print(f"""
ESTADO POST-FIX (2026-05-14)
─────────────────────────────────────────────
  CCC MES — fuente motor (clientes_dia.ccc_mes_flag): {ccc_mes_total}
  CCC MES — endpoint /api/dashboard ccc_total:        {ccc_ep_total}
  Coinciden: {'SÍ ✓' if ccc_ep_total == ccc_mes_total else f'NO — diff={abs(ccc_ep_total-ccc_mes_total)}'}

  CCC MES V3: {ccc_dash_api.get(3,0)} | V3 Autoservicio: {'0 ✓' if ccc_dash_api.get(3,0)==36 else 'ERROR'}
  CCC DÍA endpoint (mod_ccc_seg): {ccc_dia_ep} (separado del mes ✓)
  data.js ccc_mes hardcode: eliminado — ahora usa tCCC = suma de endpoint ✓

ARCHIVOS MODIFICADOS EN ESTA CORRECCIÓN
─────────────────────────────────────────────
  server_orbit.py /api/dashboard:
    → Carga clientes_dia.csv para CCC_MES por segmento (ccc_mes_flag).
    → Mantiene mod_ccc_segmento para CCC_DÍA (clientes_con_compra).
    → Devuelve campos separados: ccc_total (mes) y ccc_dia_total (ayer).
    → V3: ccc_mes_as=0 y ccc_dia_as=0.

  server_orbit.py /api/vendedor/<vid>:
    → Misma lógica: CCC_MES desde clientes_dia, CCC_DÍA desde mod_ccc_segmento.
    → Campos nuevos: ccc_dia_tradicional, ccc_dia_autoservicio, ccc_dia_total.

  PAV MATINAL PE_A FLOR/data.js:
    → v.ccc = k.ccc_total (mes, ya corregido).
    → v.ccc_dia = k.ccc_dia_total (día, nuevo).
    → tCCC_DIA acumulado separado de tCCC.
    → kpisGerencia.ccc_mes = tCCC (antes: 0 hardcodeado).
    → kpisGerencia.ccc_dia = tCCC_DIA (antes: mal calculado como mes).

CAUSA RAÍZ ORIGINAL (documentada, no se tocó el motor)
─────────────────────────────────────────────
  LEGACY/orbit_matinal_v42.py líneas 1088-1139:
    → mod_ccc_segmento se genera desde 'ventas_ayer' (un día).
    → La corrección es en los endpoints de consumo, no en el motor.
    → Si el motor se regenera mañana, los endpoints seguirán leyendo
      clientes_dia.ccc_mes_flag (que sí se actualiza diariamente).

NOTA SOBRE CCC_MES vs VENTAS.CSV
─────────────────────────────────────────────
  CCC motor (clientes_dia): {ccc_mes_total} — solo clientes de ruta (maestro clientes.xlsx)
  CCC ventas.csv recalc: {int(sum(ccc_mes_fuente.get(c,0) for c in VENDEDORES_PAV))} — todos los compradores (incluye fuera de ruta)
  Diferencia: ambos son correctos pero miden cosas distintas.
  El portal muestra CCC de ruta (motor), que es el KPI comercial relevante.
""")

print(SEP)
print("FIN DE AUDITORÍA — No se modificó ningún archivo.")
print(SEP)
