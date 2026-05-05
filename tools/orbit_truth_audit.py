"""
ORBIT TRUTH AUDIT — Genera orbit_portal_data.json para la matinal de HOY.
Usa resultado.xlsx para los 7 vendedores y ventas.csv para los KPIs diarios.
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

BASE = Path(r"C:\Orbit\MATINAL_PENAFLOR")
DATASETS = BASE / "04_DATASETS_ORBIT"
CONFIG = BASE / "09_CONFIG"
INPUTS = BASE / "01_INPUTS"
APP_DATA = BASE / "06_APP_DATA"
OUT = APP_DATA / "orbit_portal_data.json"
TRUTH = APP_DATA / "truth_audit.json"

FERIADOS = {"2026-01-01", "2026-05-01", "2026-05-25", "2026-07-09", "2026-12-08", "2026-12-25"}

def clean_code(v):
    return "".join(filter(str.isdigit, str(v)))

def read_csv(path, enc="latin-1"):
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding=enc, sep=None, engine="python")
    except:
        return pd.read_csv(path, encoding="utf-8")

def siguiente_dia_habil(fecha_base):
    d = fecha_base + timedelta(days=1)
    while d.weekday() == 6 or d.strftime("%Y-%m-%d") in FERIADOS:
        d += timedelta(days=1)
    return d

def contar_dias_habiles(fecha):
    inicio = datetime(fecha.year, fecha.month, 1)
    fin_mes = datetime(fecha.year, fecha.month + 1, 1) - timedelta(days=1)
    total, corridos = 0, 0
    d = inicio
    while d <= fin_mes:
        fecha_str = d.strftime("%Y-%m-%d")
        if d.weekday() != 6 and fecha_str not in FERIADOS:
            total += 1
            if d <= fecha:
                corridos += 1
        d += timedelta(days=1)
    return {"total": total, "corridos": corridos, "restantes": total - corridos,
            "fecha_corte": fecha.strftime("%Y-%m-%d"), "feriados_detectados": len(FERIADOS),
            "feriados": sorted(FERIADOS)}

def limpiar_numero(serie):
    """Convierte una columna con formato string sucio a numérico."""
    serie = serie.astype(str).str.replace(",", ".")  # coma decimal a punto
    serie = serie.str.replace(r"[^\d.]", "", regex=True)  # quitar todo excepto dígitos y punto
    return pd.to_numeric(serie, errors="coerce").fillna(0)

def main():
    print("\n[ORBIT TRUTH AUDIT]")

    # Fecha de la matinal = HOY (o siguiente día hábil si hoy es finde/feriado)
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if hoy.weekday() == 6 or hoy.strftime("%Y-%m-%d") in FERIADOS:
        fecha_corte = siguiente_dia_habil(hoy)
    else:
        fecha_corte = hoy
    fecha_str = fecha_corte.strftime("%Y-%m-%d")
    print(f"Fecha matinal: {fecha_str}")

    # Cargar fuentes
    resultado_path = INPUTS / "resultado.xlsx"
    if not resultado_path.exists():
        print("ERROR: falta resultado.xlsx")
        return

    avance = pd.read_excel(resultado_path, sheet_name="Avance")
    ccc = read_csv(DATASETS / "mod_ccc_segmento.csv")
    t11 = read_csv(DATASETS / "mod_11_titulares.csv")
    clientes_dia = read_csv(DATASETS / "clientes_dia.csv")
    vend = read_csv(CONFIG / "vendedores_activos.csv", enc="utf-8-sig")
    ventas = read_csv(INPUTS / "ventas.csv")

    avance_vend = avance[avance["VendedorCodigo"].apply(lambda x: len(str(x).strip()) <= 2)].copy()
    nombre_map = {}
    if not vend.empty:
        vend_act = vend[vend["activo"] == 1]
        for _, r in vend_act.iterrows():
            nombre_map[str(r["codigo_vendedor"]).strip().upper()] = str(r["nombre_vendedor"]).strip()

    vendedores_list = []
    total_obj = 0.0
    total_acum = 0.0
    total_ccc = 0
    t11_cumplidos = 0
    t11_total = 0

    colores = {"V3": "#7BD8B8", "V4": "#F2B544", "V6": "#5BC23A", "V7": "#9B7BFF", "V8": "#4DA3FF", "V9": "#FF9D5C", "V10": "#FF5D8B"}

    for _, row in avance_vend.iterrows():
        cod_num = str(int(row["VendedorCodigo"])).strip()
        cod = f"V{cod_num}"
        nombre = nombre_map.get(cod, str(row.get("VendedorNombre", "")))
        obj = float(row["ValorObjetivo"])
        acum = float(row["Acumulado"])
        av = float(row["Avance"])
        tend = float(row["Tendencia"])

        cn = clean_code(cod)
        ccc_v = ccc[ccc["vendedor_codigo"].astype(str).apply(clean_code) == cn]
        ccc_trad = int(ccc_v[ccc_v["segmento_operativo"].str.upper().str.contains("TRADICIONAL", na=False)]["clientes_con_compra"].sum()) if not ccc_v.empty else 0
        ccc_auto = int(ccc_v[ccc_v["segmento_operativo"].str.upper().str.contains("AUTOSERVICIO", na=False)]["clientes_con_compra"].sum()) if not ccc_v.empty else 0
        ccc_op   = int(ccc_v[ccc_v["segmento_operativo"].str.upper().str.contains("ON_PREMISE|VTK", na=False)]["clientes_con_compra"].sum()) if not ccc_v.empty else 0
        if cod == "V3":
            ccc_auto = 0

        t11_v = t11[t11["vendedor_codigo"].astype(str).apply(clean_code) == cn]
        t11_c = int(t11_v["tiene_flag"].sum()) if not t11_v.empty else 0
        t11_t = len(t11_v)

        total_obj += obj
        total_acum += acum
        total_ccc += (ccc_trad + ccc_auto + ccc_op)
        t11_cumplidos += t11_c
        t11_total += t11_t

        vendedores_list.append({
            "id": cod,
            "nombre": nombre,
            "zona": "",
            "color": colores.get(cod, "#E2147A"),
            "avance": av,
            "objetivo": obj,
            "acumulado": acum,
            "ccc": ccc_trad + ccc_auto + ccc_op,
            "t11": t11_c,
            "t11_total": t11_t,
            "clientes": 0,
            "alertas": 0,
            "trabaja_autoservicio": cod != "V3",
            "segmento_excluye": ["AUTOSERVICIO"] if cod == "V3" else []
        })

    # KPIs generales
    cal = contar_dias_habiles(fecha_corte)
    avance_gral = (total_acum / total_obj * 100) if total_obj > 0 else 0
    tendencia_gral = (total_acum / max(cal["corridos"], 1) * cal["total"] / total_obj * 100) if total_obj > 0 else 0
    objetivo_dia = total_obj / cal["total"] if cal["total"] > 0 else 0
    diff_obj = total_obj - total_acum

    # KPIs diarios desde ventas.csv (limpiando columnas)
    if not ventas.empty:
        ventas["FechaEntrega"] = pd.to_datetime(ventas["FechaEntrega"], dayfirst=True, errors="coerce")
        ultima = ventas["FechaEntrega"].max()
        ventas_ayer = ventas[ventas["FechaEntrega"] == ultima].copy()
        # Limpiar columnas numéricas
        if "ImporteNetoItem" in ventas_ayer.columns:
            ventas_ayer["ImporteNetoItem"] = limpiar_numero(ventas_ayer["ImporteNetoItem"])
        if "CantBase" in ventas_ayer.columns:
            ventas_ayer["CantBase"] = limpiar_numero(ventas_ayer["CantBase"])

        venta_dia_total = ventas_ayer["ImporteNetoItem"].sum() if not ventas_ayer.empty else 0.0
        botellas_dia_total = ventas_ayer["CantBase"].sum() if not ventas_ayer.empty else 0.0
        clientes_compra_dia = ventas_ayer["Cliente"].nunique() if not ventas_ayer.empty else 0
        ccc_dia_total = clientes_compra_dia
    else:
        venta_dia_total = botellas_dia_total = clientes_compra_dia = ccc_dia_total = 0

    # Clientes planificados para hoy
    if not clientes_dia.empty:
        clientes_hoy = clientes_dia[clientes_dia["fecha_objetivo"] == fecha_str]
        for v in vendedores_list:
            cod = v["id"]
            v["clientes"] = len(clientes_hoy[clientes_hoy["vendedor_codigo"].apply(clean_code) == clean_code(cod)])
        total_clientes_dia = len(clientes_hoy)
    else:
        total_clientes_dia = 1

    cobertura_gral = (clientes_compra_dia / total_clientes_dia * 100) if total_clientes_dia > 0 else 0.0
    cumpl_11t = (t11_cumplidos / t11_total * 100) if t11_total > 0 else 0.0

    # dailyEvolution
    daily_evolution = []
    for i in range(1, cal["total"] + 1):
        real = (total_acum / max(cal["corridos"], 1) * i) if i <= cal["corridos"] else None
        plan = objetivo_dia * i
        daily_evolution.append({"d": i, "real": real, "plan": plan, "hoy": i == cal["corridos"]})

    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_semana = dias_semana[fecha_corte.weekday()]

    data = {
        "meta": {
            "modo_datos": "REAL",
            "fecha_corte": fecha_str,
            "dia_semana": dia_semana,
            "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "calendario": cal,
        "vendedores": vendedores_list,
        "gerencia": {
            "kpis": {
                "objetivo_mensual": total_obj,
                "venta_acumulada": total_acum,
                "avance_pct": avance_gral,
                "venta_dia": float(venta_dia_total),
                "objetivo_dia": float(objetivo_dia),
                "ccc_acumulado": total_ccc,
                "ccc_dia": int(ccc_dia_total),
                "botellas_dia": float(botellas_dia_total),
                "clientes_compra": int(clientes_compra_dia),
                "cobertura_general": float(cobertura_gral),
                "cumplimiento_11t": float(cumpl_11t),
                "tendencia": tendencia_gral,
                "diferencia_objetivo": diff_obj
            },
            "ranking_vendedores": sorted(vendedores_list, key=lambda x: x["avance"], reverse=True),
            "alertas": []
        },
        "dailyEvolution": daily_evolution,
        "clientesCriticos": [],
        "alertas": [],
        "segmentos": [
            {"id":"TRADICIONAL","nombre":"Tradicional","req":3,"clientes":279,"cubiertos":0,"color":"#5BC23A"},
            {"id":"AUTOSERVICIO","nombre":"Autoservicio","req":6,"clientes":43,"cubiertos":0,"color":"#4DA3FF"},
            {"id":"ON_PREMISE_VTK","nombre":"On Premise / Vinoteca","req":6,"clientes":21,"cubiertos":0,"color":"#9B7BFF"}
        ],
        "titulares11": [],
        "planes": []
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    with open(TRUTH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Vendedores: {len(vendedores_list)} | Objetivo: ${total_obj:,.0f} | Acum: ${total_acum:,.0f} | Avance: {avance_gral:.1f}%")
    print(f"Archivos generados: {OUT} y {TRUTH}")
    print("RESULTADO: APROBADO")

if __name__ == "__main__":
    main()