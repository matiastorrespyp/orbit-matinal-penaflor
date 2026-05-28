"""
ORBIT Server v3 — Flask API con diagnóstico, CCC real, 11T real, sin mock
"""
from flask import Flask, jsonify, request, send_from_directory
import json, sqlite3, pandas as pd, math
from pathlib import Path
from datetime import datetime, timedelta

import os
app = Flask(__name__, static_folder=None)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0   # sin cache en portal.html

@app.after_request
def no_cache_portal(response):
    """Fuerza no-store en portal.html para que el browser siempre descargue la version nueva."""
    if response.content_type and "text/html" in response.content_type:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response
BASE = Path(__file__).parent
APP_DATA = BASE / "06_APP_DATA"
CONFIG = BASE / "09_CONFIG"
DATASETS = BASE / "04_DATASETS_ORBIT"
INPUTS = BASE / "01_INPUTS"
FRONTEND = BASE / "PAV MATINAL PE_A FLOR"
DB_PATH = BASE / "orbit.db"

USERS = {
    "v3":{"pwd":"pav2026","rol":"vendedor","nombre":"Nadia Gambino"},
    "v4":{"pwd":"pav2026","rol":"vendedor","nombre":"Angel Gribaudo"},
    "v6":{"pwd":"pav2026","rol":"vendedor","nombre":"Andrea Peyronel"},
    "v7":{"pwd":"pav2026","rol":"vendedor","nombre":"Guillermo Jofre"},
    "v8":{"pwd":"pav2026","rol":"vendedor","nombre":"Vanesa Alvarez"},
    "v9":{"pwd":"pav2026","rol":"vendedor","nombre":"Fernando Sanchez"},
    "v10":{"pwd":"pav2026","rol":"vendedor","nombre":"Milagros Ortega"},
    "gerencia":{"pwd":"gerencia2026","rol":"gerencia","nombre":"Gerencia"},
}

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS planificacion(
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, vendedor_id TEXT NOT NULL,
        zona TEXT, dia_visita TEXT, venta_esperada REAL, ccc_tradicional INTEGER,
        ccc_autoservicio INTEGER, ccc_onpremise INTEGER, once_t INTEGER,
        marcas TEXT, clientes_clave TEXT, acciones TEXT, estado TEXT DEFAULT 'enviada',
        editado_por TEXT, comentario_gerencia TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    # Migración: agregar columnas si no existen (tabla puede ser anterior)
    for col, defn in [("editado_por", "TEXT"), ("comentario_gerencia", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE planificacion ADD COLUMN {col} {defn}")
        except Exception:
            pass
    # Unique constraint para UPSERT por (fecha, vendedor_id)
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_plan_fecha_vend ON planificacion(fecha, vendedor_id)")
    except Exception:
        pass
    c.execute("""CREATE TABLE IF NOT EXISTS mensajes(
        id INTEGER PRIMARY KEY AUTOINCREMENT, vendedor_id TEXT NOT NULL,
        mensaje TEXT NOT NULL, leido INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()

def clean_code(v):
    s = str(v).upper().replace("V","").strip()
    return "".join(filter(str.isdigit, s))

def normalizar_vendedor_codigo(valor):
    if valor is None:
        return ""
    s = str(valor).strip().upper()
    if not s or s in ("NONE", "NAN"):
        return ""
    if s.startswith("V"):
        n = s[1:].strip()
    else:
        n = s
    try:
        return f"V{int(float(n))}"
    except Exception:
        return s

def read_csv(path):
    if not path.exists(): return pd.DataFrame()
    try: return pd.read_csv(path, encoding="utf-8-sig")
    except:
        try: return pd.read_csv(path, encoding="latin1")
        except: return pd.read_csv(path, encoding="utf-8")

_VENDEDORES_EXCLUIDOS = {2, 5, 20}
_VENDEDORES_ACTIVOS_PLAN = {"V3","V4","V6","V7","V8","V9","V10"}

def _parse_num_ar(valor):
    """Parsea número en formato argentino (punto=miles, coma=decimal)."""
    try:
        s = str(valor).strip().replace(" ", "")
        s = s.replace(".", "").replace(",", ".")
        return float(s)
    except Exception:
        return 0.0

def _clasificar_segmento(ramo: str, subsegmento: str) -> str:
    texto = f"{str(ramo).upper()} | {str(subsegmento).upper()}"
    auto = ["AUTOSERVICIO","CADENA REGIONAL","SAR","LARGE FORMAT","PROXIMITY",
            "CASH&CARRY","CASH & CARRY","MAYORISTA","MAYORISTAS","TIENDA DE BEBIDAS"]
    if any(k in texto for k in auto):
        return "AUTOSERVICIO"
    on = ["ON PREMISE","AWAY FROM HOME","VINOTECA","VINOTECAS","BAR",
          "RESTAURANT","RESTAURANTE","ESTACION DE SERVICIO","ESTACIONES DE SERVICIO",
          "EVENTOS","TEMPORADA","CATERING","ON DIA","ON NOCHE"]
    if any(k in texto for k in on):
        return "ON_PREMISE_VTK"
    trad = ["TRADITIONAL TRADE","ALMACEN","DESPENSA","KIOSCO","MAXIKIOSCO",
            "FIAMBRERIA","CARNICERIA","GRANJA","PANADERIA","CASA DE PASTAS","TRADICIONAL"]
    if any(k in texto for k in trad):
        return "TRADICIONAL"
    return "OTROS"

def _cargar_ventas_mes_actual() -> pd.DataFrame:
    """
    Lee ventas.csv, filtra al mes calendario actual, ImporteNetoItem > 0,
    excluye vendedores 2 y 5.
    Devuelve DataFrame con: cliente_id, vendedor_codigo, segmento_operativo.
    """
    path = INPUTS / "ventas.csv"
    if not path.exists():
        return pd.DataFrame()

    df = pd.DataFrame()
    for enc in ("latin1", "utf-8-sig", "utf-8"):
        try:
            df = pd.read_csv(path, sep=";", encoding=enc)
            break
        except Exception:
            continue

    if df.empty:
        return pd.DataFrame()

    req = {"Cliente", "CodVendedor", "ImporteNetoItem", "FechaComprobante", "Ramo", "Subramo"}
    if not req.issubset(set(df.columns)):
        return pd.DataFrame()

    df = df.copy()
    df["cliente_id"]      = pd.to_numeric(df["Cliente"], errors="coerce")
    df["vendedor_codigo"] = pd.to_numeric(df["CodVendedor"], errors="coerce")
    df["importe_neto"]    = df["ImporteNetoItem"].apply(_parse_num_ar)
    df["fecha"]           = pd.to_datetime(df["FechaComprobante"], dayfirst=True, errors="coerce")
    df["segmento_operativo"] = df.apply(
        lambda r: _clasificar_segmento(str(r.get("Ramo", "")), str(r.get("Subramo", ""))), axis=1
    )

    hoy       = datetime.now()
    mes_inicio = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    df = df[df["fecha"] >= mes_inicio]
    df = df[df["importe_neto"] > 0]
    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
    df = df.dropna(subset=["cliente_id", "vendedor_codigo"])

    return df[["cliente_id", "vendedor_codigo", "segmento_operativo"]].copy()

def _ccc_mes_por_vendedor(ventas_mes: pd.DataFrame) -> dict:
    """
    Calcula CCC Compradores Mes por vendedor y segmento.
    Retorna dict keyed por int(vendedor_codigo):
      {tradicional, autoservicio, onpremise, total}
    V3 tiene autoservicio=0 por regla de negocio.
    """
    if ventas_mes.empty:
        return {}

    # Un cliente puede aparecer en múltiples líneas → deduplicate por cliente+vendedor
    buyers = ventas_mes.drop_duplicates(subset=["cliente_id", "vendedor_codigo"]).copy()

    result = {}
    for cod, grp in buyers.groupby("vendedor_codigo"):
        cod_int = int(cod)
        trad  = int((grp["segmento_operativo"] == "TRADICIONAL").sum())
        aas   = int((grp["segmento_operativo"] == "AUTOSERVICIO").sum())
        op    = int((grp["segmento_operativo"] == "ON_PREMISE_VTK").sum())
        if cod_int == 3:  # V3 no trabaja autoservicio
            aas = 0
        result[cod_int] = {
            "tradicional": trad,
            "autoservicio": aas,
            "onpremise":   op,
            "total":       trad + aas + op,
        }
    return result

def _clientes_por_dia(dia: str) -> pd.DataFrame:
    """Calcula cartera del día desde clientes.xlsx + compra_mes_flag desde ventas.csv."""
    cli_path = INPUTS / "clientes.xlsx"
    if not cli_path.exists():
        return pd.DataFrame()
    try:
        cli = pd.read_excel(cli_path)
    except Exception:
        return pd.DataFrame()

    dia_cap = dia.capitalize()
    cli = cli[cli["DiasVisita"].astype(str).str.strip() == dia_cap]
    cli = cli[~cli["codven"].isin([2, 5, 20])]
    if cli.empty:
        return pd.DataFrame()

    ventas_mes = _cargar_ventas_mes_actual()
    ccc_ids = set(ventas_mes["cliente_id"].dropna().astype(int)) if not ventas_mes.empty else set()

    sub_col = next((c for c in cli.columns if "subseg" in c.lower() or "subramo" in c.lower()), None)
    nombre_col = next(
        (c for c in cli.columns if c.lower().replace("_","").replace(" ","") in ("razonsocial","nombre","cliente")),
        next((c for c in cli.columns if "razon" in c.lower() or "nombre" in c.lower()), None)
    )

    rows = []
    for _, row in cli.iterrows():
        cid_raw = row.get("Codigo")
        vcod_raw = row.get("codven")
        if pd.isna(cid_raw) or pd.isna(vcod_raw):
            continue
        cid = int(cid_raw)
        vcod = int(vcod_raw)
        seg = _clasificar_segmento(str(row.get("Ramo", "")),
                                   str(row.get(sub_col, "") if sub_col else ""))
        compra_mes = 1 if cid in ccc_ids else 0
        estado = "SIN_COMPRA_MES" if compra_mes == 0 else "COBERTURA_OK"
        rows.append({
            "cliente_id": cid,
            "cliente_nombre": str(row[nombre_col]) if (nombre_col and pd.notna(row.get(nombre_col))) else str(cid),
            "vendedor_codigo": vcod,
            "vendedor_id": f"V{vcod}",
            "dias_visita": dia_cap,
            "segmento": seg,
            "segmento_operativo": seg,
            "compra_mes_flag": compra_mes,
            "compra_ayer_flag": 0,
            "estado": estado,
            "estado_cliente": estado,
            "prioridad_label": "ALTA" if compra_mes == 0 else "NORMAL",
            "importe_mes": 0.0,
            "botellas_mes": 0,
            "ultima_compra_fecha": None,
            "ultima_compra_importe": None,
        })
    df = pd.DataFrame(rows)

    # Enriquecer con última compra
    try:
        hist = read_csv(BASE / "02_HISTORY" / "historial_ventas_cliente.csv")
        if not hist.empty:
            hist.columns = [c.lstrip("﻿") for c in hist.columns]
            f_col = next((c for c in hist.columns if "fecha" in c.lower()), None)
            i_col = next((c for c in hist.columns if "importe" in c.lower() or "neto" in c.lower()), None)
            id_col = next((c for c in hist.columns if c.lower() in ("cliente", "cliente_id", "cod_cliente")), None)
            if all([f_col, i_col, id_col]):
                hist[id_col] = pd.to_numeric(hist[id_col], errors="coerce")
                hist[i_col] = pd.to_numeric(hist[i_col], errors="coerce")
                ultima = (hist.sort_values(f_col, ascending=False)
                          .drop_duplicates(subset=[id_col])[[id_col, f_col, i_col]]
                          .rename(columns={id_col: "cliente_id", f_col: "ultima_compra_fecha",
                                           i_col: "ultima_compra_importe"}))
                ultima["cliente_id"] = pd.to_numeric(ultima["cliente_id"], errors="coerce")
                df["cliente_id"] = pd.to_numeric(df["cliente_id"], errors="coerce")
                df = df.merge(ultima, on="cliente_id", how="left", suffixes=("", "_h"))
                if "ultima_compra_fecha_h" in df.columns:
                    df["ultima_compra_fecha"] = df["ultima_compra_fecha_h"].fillna(df["ultima_compra_fecha"])
                    df["ultima_compra_importe"] = df["ultima_compra_importe_h"].fillna(df["ultima_compra_importe"])
                    df.drop(columns=["ultima_compra_fecha_h", "ultima_compra_importe_h"], inplace=True, errors="ignore")
    except Exception:
        pass

    records = df.to_dict(orient="records")
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float) and not math.isfinite(v):
                rec[k] = None
    return pd.DataFrame(records)


def _cargar_feriados():
    import csv
    p = CONFIG / "feriados.csv"
    if not p.exists():
        return set()
    with open(p, encoding="utf-8-sig") as f:
        return {row["fecha"] for row in csv.DictReader(f)}

def contar_dias_habiles(fecha_corte=None):
    if fecha_corte is None:
        fecha_corte = datetime.now()
    feriados = _cargar_feriados()
    inicio = datetime(fecha_corte.year, fecha_corte.month, 1)
    fin_mes = datetime(fecha_corte.year, fecha_corte.month + 1, 1) - timedelta(days=1)
    total, corridos = 0, 0
    feriados_del_mes = []
    d = inicio
    while d <= fin_mes:
        fecha_str = d.strftime("%Y-%m-%d")
        es_domingo = d.weekday() == 6
        es_feriado = fecha_str in feriados
        if es_feriado:
            feriados_del_mes.append(fecha_str)
        if not es_domingo and not es_feriado:
            total += 1
            if d <= fecha_corte:
                corridos += 1
        d += timedelta(days=1)
    print(f"[ORBIT calendario] fecha_corte={fecha_corte.strftime('%Y-%m-%d')} | "
          f"total_comerciales={total} | corridos={corridos} | "
          f"feriados_mes={feriados_del_mes}")
    return {
        "total": total,
        "corridos": corridos,
        "restantes": total - corridos,
        "fecha_corte": fecha_corte.strftime("%Y-%m-%d"),
        "total_dias_comerciales_mes": total,
        "dias_comerciales_corridos": corridos,
        "feriados_detectados_del_mes": feriados_del_mes,
        "fecha_corte_calendario": fecha_corte.strftime("%Y-%m-%d"),
    }

@app.route("/favicon.ico")
def favicon():
    return "", 204

# ====== STATIC ======
@app.route("/")
@app.route("/<path:filename>")
def frontend(filename="portal.html"):
    return send_from_directory(str(FRONTEND), filename)

# ====== AUTH ======
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    user = (data.get("user") or "").lower().strip()
    u = USERS.get(user)
    if u and u["pwd"] == data.get("pwd",""):
        return jsonify({"ok":True,"rol":u["rol"],"nombre":u["nombre"],"vendedor_id":user.upper()})
    return jsonify({"ok":False,"error":"Credenciales inválidas"}), 401

# ====== DIAGNÓSTICO ======
@app.route("/api/diagnostico")
def diagnostico():
    vol = read_csv(DATASETS / "mod_volumen_vendedor.csv")
    ccc_df = read_csv(DATASETS / "mod_ccc_segmento.csv")
    t11_df = read_csv(DATASETS / "mod_11_titulares.csv")
    vend = read_csv(CONFIG / "vendedores_activos.csv")

    fuentes = []
    for nombre, path in [("volumen", DATASETS / "mod_volumen_vendedor.csv"),
                          ("ccc", DATASETS / "mod_ccc_segmento.csv"),
                          ("11t", DATASETS / "mod_11_titulares.csv"),
                          ("vendedores", CONFIG / "vendedores_activos.csv")]:
        if path.exists():
            fuentes.append({"archivo": nombre, "path": str(path), "filas": len(read_csv(path)), "estado": "OK"})
        else:
            fuentes.append({"archivo": nombre, "path": str(path), "filas": 0, "estado": "NO ENCONTRADO"})

    vendedores_detectados = []
    if not vend.empty:
        vend_activos = vend[vend["activo"]==1]
        for _, v in vend_activos.iterrows():
            cod = str(v["codigo_vendedor"]).strip()
            vv = vol[vol["vendedor_codigo"].astype(str).apply(clean_code) == clean_code(cod)] if not vol.empty else pd.DataFrame()
            obj = float(vv["objetivo_mes"].sum()) if not vv.empty else 0
            acum = float(vv["acumulado_mes"].sum()) if not vv.empty else 0
            vendedores_detectados.append({"codigo": cod, "nombre": str(v["nombre_vendedor"]), "objetivo": obj, "acumulado": acum})

    dias = contar_dias_habiles()
    total_acum = sum(v["acumulado"] for v in vendedores_detectados)

    # Segmentos: denominadores desde cartera real (clientes.xlsx); cubiertos desde mod_ccc_segmento (ayer)
    seg_ids = [
        ("TRADICIONAL",    "Tradicional",          3,  "#5BC23A"),
        ("AUTOSERVICIO",   "Autoservicio",          6,  "#4DA3FF"),
        ("ON_PREMISE_VTK", "On Premise / Vinoteca", 6,  "#9B7BFF"),
    ]
    cartera_real_total = 0
    cartera_segs_real = {sid: 0 for sid, *_ in seg_ids}
    cli_path = INPUTS / "clientes.xlsx"
    if cli_path.exists():
        try:
            cli_df = pd.read_excel(cli_path)
            cli_df.columns = cli_df.columns.str.strip()
            vcol = next((c for c in cli_df.columns if "cod" in c.lower() and "vend" in c.lower()), None)
            if vcol is None:
                vcol = next((c for c in cli_df.columns if "vend" in c.lower()), None)
            ramo_col = next((c for c in cli_df.columns if c.lower() == "ramo"), None)
            sub_col  = next((c for c in cli_df.columns if "subramo" in c.lower() or "subseg" in c.lower()), None)
            if vcol:
                cli_df["_vnum"] = pd.to_numeric(cli_df[vcol], errors="coerce")
                cli_df = cli_df[~cli_df["_vnum"].isin(_VENDEDORES_EXCLUIDOS)]
                cartera_real_total = len(cli_df)
                if ramo_col:
                    cli_df["_seg"] = cli_df.apply(
                        lambda r: _clasificar_segmento(
                            str(r.get(ramo_col, "")),
                            str(r.get(sub_col, "") if sub_col else "")
                        ), axis=1
                    )
                    for sid, *_ in seg_ids:
                        cartera_segs_real[sid] = int((cli_df["_seg"] == sid).sum())
        except Exception:
            pass
    cdia_df = read_csv(DATASETS / "clientes_dia.csv")
    segmentos = []
    for sid, snombre, req, color in seg_ids:
        total_cli = cartera_segs_real.get(sid) or \
                    (int((cdia_df["segmento_operativo"] == sid).sum()) if not cdia_df.empty else 0)
        cubiertos = int(
            ccc_df.loc[ccc_df["segmento_operativo"] == sid, "coberturas_logradas"]
            .apply(pd.to_numeric, errors="coerce").sum()
        ) if not ccc_df.empty else 0
        segmentos.append({"id": sid, "nombre": snombre, "req": req,
                          "clientes": total_cli, "cubiertos": cubiertos, "color": color,
                          "cubiertos_label": "ayer"})

    # Titulares11: agrega tiene_flag por marca desde mod_11_titulares
    titulares11 = []
    if not t11_df.empty and "marca_objetivo" in t11_df.columns and "tiene_flag" in t11_df.columns:
        t11_df["tiene_flag"] = pd.to_numeric(t11_df["tiene_flag"], errors="coerce").fillna(0)
        agg = (t11_df.groupby("marca_objetivo", dropna=False)
               .agg(objetivo=("tiene_flag", "count"), cubiertos=("tiene_flag", "sum"))
               .reset_index())
        agg["cubiertos"] = agg["cubiertos"].astype(int)
        for _, row in agg.iterrows():
            titulares11.append({"marca": row["marca_objetivo"],
                                 "objetivo": int(row["objetivo"]),
                                 "cubiertos": row["cubiertos"]})
        titulares11.sort(key=lambda x: -x["cubiertos"])

    botellas_dia = int(pd.to_numeric(ccc_df["botellas_vendidas"], errors="coerce").sum()) if not ccc_df.empty and "botellas_vendidas" in ccc_df.columns else 0
    botellas_mes = None
    try:
        hv_path = BASE / "02_HISTORY" / "historial_ventas_cliente.csv"
        if hv_path.exists():
            hv = read_csv(hv_path)
            if not hv.empty and "cant_base" in hv.columns and "importe_neto" in hv.columns:
                hoy = datetime.now()
                mes_str = hoy.strftime("%Y-%m")
                hv["_fecha"] = hv["fecha_comprobante"].astype(str).str[:7]
                hv["_importe"] = pd.to_numeric(hv["importe_neto"], errors="coerce").fillna(0)
                hv["_cant"] = pd.to_numeric(hv["cant_base"], errors="coerce").fillna(0)
                hv["_vend"] = pd.to_numeric(hv["vendedor_codigo"], errors="coerce").fillna(0).astype(int)
                mes_df = hv[(hv["_fecha"] == mes_str) & (hv["_importe"] > 0) & (~hv["_vend"].isin(_VENDEDORES_EXCLUIDOS))]
                botellas_mes = int(mes_df["_cant"].sum())
    except Exception:
        botellas_mes = None

    fecha_datos = None
    fecha_obj_str = None
    dia_op = None
    modo_fecha = "SIN_DATOS"
    if not vol.empty:
        try:
            if "fecha_ejecucion" in vol.columns:
                fecha_datos = str(vol["fecha_ejecucion"].iloc[0])
            if "fecha_objetivo" in vol.columns:
                fecha_obj_str = str(vol["fecha_objetivo"].iloc[0])
            if "dia_objetivo" in vol.columns:
                dia_op = str(vol["dia_objetivo"].iloc[0]).upper()
            modo_fecha = "REAL"
        except Exception:
            pass

    return jsonify({
        "modo_datos": "REAL",
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "calendario": dias,
        "fuentes": fuentes,
        "vendedores_detectados": vendedores_detectados,
        "total_acumulado_csv": total_acum,
        "excluidos": ["V2", "V5"],
        "advertencias": [] if fuentes[0]["estado"] == "OK" else ["Faltan archivos de datos"],
        "v3_autoservicio": False,
        "segmentos": segmentos,
        "titulares11": titulares11,
        "botellas_dia": botellas_dia,
        "botellas_mes": botellas_mes,
        "cartera_real_total": cartera_real_total,
        "dia_snapshot": dia_op,
        "fecha_datos": fecha_datos,
        "fecha_corte": fecha_datos,
        "fecha_objetivo": fecha_obj_str,
        "fecha_matinal": fecha_obj_str,
        "dia_operativo": dia_op,
        "modo_fecha": modo_fecha,
    })

# ====== DASHBOARD REAL ======
@app.route("/api/dashboard")
def dashboard():
    dia_param = request.args.get("dia", "").strip()

    # Precompute day-specific client counts when a day is requested
    clientes_dia_map = {}  # {cn: {total, sin_compra}}
    if dia_param:
        cli_dia_df = _clientes_por_dia(dia_param)
        if cli_dia_df is not None and not cli_dia_df.empty and "vendedor_codigo" in cli_dia_df.columns:
            cli_dia_df["_cn"] = cli_dia_df["vendedor_codigo"].astype(str).apply(clean_code)
            for vcn, grp in cli_dia_df.groupby("_cn"):
                clientes_dia_map[vcn] = {
                    "total": len(grp),
                    "sin_compra": int((grp["compra_mes_flag"] == 0).sum()),
                }

    vol     = read_csv(DATASETS / "mod_volumen_vendedor.csv")
    vend    = read_csv(CONFIG  / "vendedores_activos.csv")
    ccc_df  = read_csv(DATASETS / "mod_ccc_segmento.csv")   # CCC día (ayer)
    t11_df  = read_csv(DATASETS / "mod_11_titulares.csv")
    cdia_df = read_csv(DATASETS / "clientes_dia.csv")        # para oportunidades (día base)

    # CCC Compradores Mes — desde ventas.csv del mes actual (no clientes_dia)
    ventas_mes = _cargar_ventas_mes_actual()
    ccc_mes_map = _ccc_mes_por_vendedor(ventas_mes)
    dias = contar_dias_habiles()
    _corridos = max(dias["corridos"], 1)
    _total    = dias["total"]

    # Fallback: objetivo/acumulado/avance desde resultado.xlsx para vendedores sin maestro de clientes
    resultado_fallback = {}
    resultado_path = INPUTS / "resultado.xlsx"
    if resultado_path.exists():
        try:
            avance_df = pd.read_excel(resultado_path, sheet_name="Avance")
            for _, r in avance_df.iterrows():
                cn_r = clean_code(str(r.get("VendedorCodigo", "")))
                if cn_r:
                    resultado_fallback[cn_r] = {
                        "objetivo": float(r.get("ValorObjetivo", 0) or 0),
                        "acumulado": float(r.get("Acumulado", 0) or 0),
                        "avance": float(r.get("Avance", 0) or 0),
                    }
        except Exception:
            pass

    if vol.empty:
        return jsonify({"error": "No se encontró mod_volumen_vendedor.csv", "modo_datos": "SIN_DATOS"}), 500

    vend = vend[vend["activo"] == 1]
    result = []
    for _, v in vend.iterrows():
        cod = str(v["codigo_vendedor"]).strip()
        nombre = str(v["nombre_vendedor"]).strip()
        cn = clean_code(cod)

        vv = vol[vol["vendedor_codigo"].astype(str).apply(clean_code) == cn] if not vol.empty else pd.DataFrame()
        cv = ccc_df[ccc_df["vendedor_codigo"].astype(str).apply(clean_code) == cn] if not ccc_df.empty else pd.DataFrame()
        tv = t11_df[t11_df["vendedor_codigo"].astype(str).apply(clean_code) == cn] if not t11_df.empty else pd.DataFrame()

        obj = float(vv["objetivo_mes"].sum()) if not vv.empty else 0
        acum = float(vv["acumulado_mes"].sum()) if not vv.empty else 0
        av = float(vv["avance_pct"].mean()) if not vv.empty else 0
        venta_ayer = float(vv["venta_ayer"].sum()) if not vv.empty else 0

        sin_maestro = False
        if vv.empty and cn in resultado_fallback:
            fb = resultado_fallback[cn]
            obj = fb["objetivo"]
            acum = fb["acumulado"]
            av = fb["avance"]
            sin_maestro = True
        # Usar avance_pct del ERP (= tendencia_mes/objetivo*100) cuando está disponible.
        # Fallback al recálculo dinámico solo si no hay dato oficial (sin_maestro o av==0).
        tendencia_pct = round(av, 2) if (not vv.empty and av > 0) else (
            round((acum / _corridos) * _total / obj * 100, 2) if obj else 0
        )
        cli_total = int(vv["clientes_planificados"].sum()) if not vv.empty and "clientes_planificados" in vv.columns else 0
        cli_sin = int(vv["clientes_sin_compra_mes"].sum()) if not vv.empty and "clientes_sin_compra_mes" in vv.columns else 0
        # Override with day-specific counts when dia requested (0 if vendor not scheduled that day)
        if dia_param:
            day_data = clientes_dia_map.get(cn, {"total": 0, "sin_compra": 0})
            cli_total = day_data["total"]
            cli_sin   = day_data["sin_compra"]

        # CCC Compradores Mes — desde ventas.csv del mes actual
        cod_int = int(cn) if cn.isdigit() else 0
        ccc_mes = ccc_mes_map.get(cod_int, {"tradicional": 0, "autoservicio": 0, "onpremise": 0, "total": 0})
        ccc_mes_trad = ccc_mes["tradicional"]
        ccc_mes_as   = ccc_mes["autoservicio"]   # ya es 0 para V3 por regla en _ccc_mes_por_vendedor
        ccc_mes_op   = ccc_mes["onpremise"]

        # CCC DÍA — desde mod_ccc_segmento (clientes con compra ayer)
        def _ccc_dia_seg(df, seg_pattern):
            if df.empty:
                return 0
            mask = df["segmento_operativo"].astype(str).str.upper().str.contains(seg_pattern, na=False)
            return int(df.loc[mask, "clientes_con_compra"].sum())

        ccc_dia_trad = _ccc_dia_seg(cv, "TRADICIONAL")
        ccc_dia_as   = _ccc_dia_seg(cv, "AUTOSERVICIO")
        ccc_dia_op   = _ccc_dia_seg(cv, "ON_PREMISE|VTK")

        t11_cumplidos = int(tv["tiene_flag"].sum()) if not tv.empty and "tiene_flag" in tv.columns else 0
        t11_total = len(tv)

        # V3 no trabaja autoservicio (ccc_mes_as ya es 0; refuerzo ccc_dia)
        if cod.upper() == "V3":
            ccc_dia_as = 0

        # Oportunidades: clientes sin compra del día (V3 excluye AS)
        oportunidades = 0
        if dia_param:
            oportunidades = clientes_dia_map.get(cn, {"sin_compra": 0})["sin_compra"]
        elif not cdia_df.empty and "estado_cliente" in cdia_df.columns and "vendedor_codigo" in cdia_df.columns:
            opv = cdia_df[cdia_df["vendedor_codigo"].astype(str).apply(clean_code) == cn]
            omask = opv["estado_cliente"].astype(str).str.lower().str.contains("sin", na=False)
            if cod.upper() == "V3" and "segmento_operativo" in opv.columns:
                omask = omask & (opv["segmento_operativo"].astype(str).str.upper() != "AUTOSERVICIO")
            oportunidades = int(omask.sum())

        result.append({
            "vendedor_id": cod,
            "vendedor_nombre": nombre,
            "sin_maestro": sin_maestro,
            "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "kpis": {
                "objetivo": obj, "acumulado": acum, "avance_pct": av, "tendencia_pct": tendencia_pct,
                "venta_hoy_total": venta_ayer, "venta_mes_actual": acum,
                "clientes_total": cli_total, "clientes_pendientes": cli_sin,
                # CCC Compradores Mes — fuente: ventas.csv mes actual, ImporteNetoItem > 0
                "ccc_tradicional": ccc_mes_trad, "ccc_autoservicio": ccc_mes_as, "ccc_onpremise": ccc_mes_op,
                "ccc_total": ccc_mes_trad + ccc_mes_as + ccc_mes_op,
                # CCC Compradores Día — fuente: mod_ccc_segmento (ayer)
                "ccc_dia_tradicional": ccc_dia_trad, "ccc_dia_autoservicio": ccc_dia_as, "ccc_dia_onpremise": ccc_dia_op,
                "ccc_dia_total": ccc_dia_trad + ccc_dia_as + ccc_dia_op,
                "once_titulares_cumplidos": t11_cumplidos, "once_titulares_total": t11_total,
                "cobertura_pct": cli_total and (100 - (cli_sin/cli_total*100)) or 0,
                "alertas_criticas": 0, "oportunidades": oportunidades,
                "inversion_desc_ars": 0.0, "sin_cargo_ars": 0.0,
                "impacto_alertas_ars": 0.0, "venta_mes_anterior": 0.0,
                "trabaja_autoservicio": cod.upper() != "V3"
            }
        })
    return jsonify(result)

# ====== CLIENTES, ALERTAS ======
@app.route("/api/clientes")
def clientes():
    dia_param = request.args.get("dia", "").strip()
    if dia_param:
        df = _clientes_por_dia(dia_param)
        if df is None or df.empty:
            return jsonify([])
        records = df.to_dict(orient="records")
        for rec in records:
            for k, v in rec.items():
                if isinstance(v, float) and not math.isfinite(v):
                    rec[k] = None
        return jsonify(records)
    df = read_csv(DATASETS / "clientes_dia.csv")
    if df.empty: return jsonify([])
    df.columns = [c.lstrip("﻿") for c in df.columns]
    for col in ["vendedor_codigo", "cliente_id", "botellas_ayer", "botellas_mes",
                "importe_ayer", "importe_mes", "compra_ayer_flag", "compra_mes_flag",
                "ccc_ayer_flag", "ccc_mes_flag", "cobertura_ayer_flag", "cobertura_mes_flag"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["vendedor_id"] = "V" + df["vendedor_codigo"].astype("Int64").astype(str)
    df["segmento"] = df["segmento_operativo"]
    df["estado"] = df["estado_cliente"]
    df["prioridad_label"] = df["prioridad_comercial"]
    df["impacto_alertas_ars"] = df["importe_mes"].fillna(0)
    df["faltan_11t"] = 11
    df["kernel_accion"] = ""

    # Enriquecer con última compra desde historial
    try:
        hist = read_csv(BASE / "02_HISTORY" / "historial_ventas_cliente.csv")
        if not hist.empty:
            hist.columns = [c.lstrip("﻿") for c in hist.columns]
            fecha_col = next((c for c in hist.columns if "fecha" in c.lower()), None)
            imp_col = next((c for c in hist.columns if "importe" in c.lower() or "neto" in c.lower()), None)
            id_col = next((c for c in hist.columns if c.lower() in ("cliente", "cliente_id", "cod_cliente")), None)
            if all([fecha_col, imp_col, id_col]):
                hist[id_col] = pd.to_numeric(hist[id_col], errors="coerce")
                hist[imp_col] = pd.to_numeric(hist[imp_col], errors="coerce")
                ultima = (hist.sort_values(fecha_col, ascending=False)
                          .drop_duplicates(subset=[id_col])[[id_col, fecha_col, imp_col]]
                          .rename(columns={id_col: "cliente_id", fecha_col: "ultima_compra_fecha", imp_col: "ultima_compra_importe"}))
                ultima["cliente_id"] = pd.to_numeric(ultima["cliente_id"], errors="coerce")
                df["cliente_id"] = pd.to_numeric(df["cliente_id"], errors="coerce")
                df = df.merge(ultima, on="cliente_id", how="left")
    except Exception:
        pass

    records = df.to_dict(orient="records")
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float) and not math.isfinite(v):
                rec[k] = None
    return jsonify(records)

@app.route("/api/alertas")
def alertas():
    df = read_csv(DATASETS / "mod_alertas_descuentos.csv")
    if df.empty: return jsonify([])
    df.columns = [c.lstrip("﻿") for c in df.columns]
    for col in ["vendedor_codigo", "cliente_id", "cant_base", "cajas_eq",
                "descuento_aplicado_pct", "descuento_maximo_pct", "exceso_pct",
                "importe_neto", "valor_descuento"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Excluir alertas de Plan AS: su descuento base es 10%; solo alerta si supera ese umbral
    pas = read_csv(DATASETS / "mod_planes_as.csv")
    if not pas.empty:
        pas_ids = set(pd.to_numeric(pas["cliente_id"], errors="coerce").dropna().astype(int))
        is_plan_as = df["cliente_id"].isin(pas_ids)
        descuento_ok = df["descuento_aplicado_pct"] <= 10
        df = df[~(is_plan_as & descuento_ok)]

    # Excluir alertas de 11 Titulares con ≤10%: hay una acción comercial de 10% dto en las 11T
    _11T_MARCAS = {
        "ALMA MORA", "DADA", "LOS ARBOLES", "TRAPICHE RESERVA", "ALARIS",
        "FINCA LAS MORAS", "DON DAVID", "GORDON'S FLAVOURS", "SMIRNOFF FLAVOURS",
        "ANTARES", "SMIRNOFF ICE", "FOND DE CAVE", "CAZADOR", "JW BLACK", "JW RED",
        "MASCOTA", "NC ESPUMANTES", "TRAPICHE MEDALLA",
    }
    if "marca" in df.columns:
        is_11t = df["marca"].astype(str).str.upper().str.strip().isin(_11T_MARCAS)
        descuento_11t_ok = df["descuento_aplicado_pct"] <= 10
        df = df[~(is_11t & descuento_11t_ok)]

    df["vendedor_id"] = "V" + df["vendedor_codigo"].astype("Int64").astype(str)
    df["prioridad"] = "alta"
    df["tipo"] = "descuento"
    df["titulo"] = df["cliente_nombre"]
    df["detalle"] = (df["articulo"].fillna("") + " — descuento aplicado: " +
                     df["descuento_aplicado_pct"].fillna(0).astype(str) + "% / máximo: " +
                     df["descuento_maximo_pct"].fillna(0).astype(str) + "%")
    df["accion"] = "Revisar descuento con " + df["fuente_regla"].fillna("regla fallback")
    df["impacto_alertas_ars"] = (df["valor_descuento"].fillna(0) * df["cant_base"].fillna(0))
    return jsonify(df.where(pd.notnull(df), None).to_dict(orient="records"))

# ====== DETALLE VENDEDOR ======
@app.route("/api/vendedor/<vid>")
def vendedor_detalle(vid):
    vid_norm = normalizar_vendedor_codigo(vid)
    cn = clean_code(vid_norm)

    vend = read_csv(CONFIG / "vendedores_activos.csv")
    nombre = vid_norm
    if not vend.empty:
        activos = vend[vend["activo"] == 1]
        fila = activos[activos["codigo_vendedor"].astype(str).apply(clean_code) == cn]
        if fila.empty:
            return jsonify({"error": f"Vendedor {vid} no encontrado o inactivo"}), 404
        nombre = str(fila.iloc[0]["nombre_vendedor"])

    # Regla de negocio: V3 no trabaja autoservicio
    trabaja_as = (vid_norm != "V3")

    # KPIs volumen
    vol = read_csv(DATASETS / "mod_volumen_vendedor.csv")
    vv = vol[vol["vendedor_codigo"].astype(str).apply(clean_code) == cn] if not vol.empty else pd.DataFrame()
    obj   = float(vv["objetivo_mes"].sum())          if not vv.empty else 0
    acum  = float(vv["acumulado_mes"].sum())         if not vv.empty else 0
    av    = float(vv["avance_pct"].mean())           if not vv.empty else 0
    venta_hoy = float(vv["venta_ayer"].sum())        if not vv.empty else 0
    cli_total = int(vv["clientes_planificados"].sum()) if not vv.empty and "clientes_planificados" in vv.columns else 0
    cli_sin   = int(vv["clientes_sin_compra_mes"].sum()) if not vv.empty and "clientes_sin_compra_mes" in vv.columns else 0
    dias_vd          = contar_dias_habiles()
    tendencia_pct_vd = round((acum / max(dias_vd["corridos"], 1)) * dias_vd["total"] / obj * 100, 2) if obj else 0

    # CCC Compradores Mes — desde ventas.csv del mes actual
    ventas_mes_vd = _cargar_ventas_mes_actual()
    ccc_mes_map_vd = _ccc_mes_por_vendedor(ventas_mes_vd)
    cod_int = int(cn) if cn.isdigit() else 0
    ccc_mes_vd = ccc_mes_map_vd.get(cod_int, {"tradicional": 0, "autoservicio": 0, "onpremise": 0, "total": 0})
    ccc_trad = ccc_mes_vd["tradicional"]
    ccc_as   = ccc_mes_vd["autoservicio"]   # ya es 0 para V3
    ccc_op   = ccc_mes_vd["onpremise"]

    # CCC Compradores Día — desde mod_ccc_segmento (ayer)
    ccc_df = read_csv(DATASETS / "mod_ccc_segmento.csv")
    cv = ccc_df[ccc_df["vendedor_codigo"].astype(str).apply(clean_code) == cn] if not ccc_df.empty else pd.DataFrame()

    def _ccc_dia(df, pat):
        if df.empty:
            return 0
        return int(df.loc[df["segmento_operativo"].astype(str).str.upper().str.contains(pat, na=False), "clientes_con_compra"].sum())

    ccc_dia_trad = _ccc_dia(cv, "TRADICIONAL")
    ccc_dia_as   = _ccc_dia(cv, "AUTOSERVICIO")
    ccc_dia_op   = _ccc_dia(cv, "ON_PREMISE|VTK")

    # V3 no trabaja autoservicio (ccc_as ya es 0; refuerzo ccc_dia)
    if vid_norm == "V3":
        ccc_dia_as = 0

    # 11 Titulares por vendedor — agrupados por marca
    t11_df = read_csv(DATASETS / "mod_11_titulares.csv")
    tv = t11_df[t11_df["vendedor_codigo"].astype(str).apply(clean_code) == cn] if not t11_df.empty else pd.DataFrame()
    titulares11 = []
    if not tv.empty and "marca_objetivo" in tv.columns and "tiene_flag" in tv.columns:
        tv = tv.copy()
        tv["tiene_flag"] = pd.to_numeric(tv["tiene_flag"], errors="coerce").fillna(0)
        agg = (tv.groupby("marca_objetivo", dropna=False)
                 .agg(objetivo=("tiene_flag", "count"), cubiertos=("tiene_flag", "sum"))
                 .reset_index())
        agg["cubiertos"] = agg["cubiertos"].astype(int)
        for _, row in agg.iterrows():
            titulares11.append({"marca": row["marca_objetivo"],
                                 "objetivo": int(row["objetivo"]),
                                 "cubiertos": row["cubiertos"]})
        titulares11.sort(key=lambda x: -x["cubiertos"])

    once_t_cumplidos = sum(1 for t in titulares11 if t["cubiertos"] > 0)
    once_t_total     = len(titulares11)

    return jsonify({
        "vendedor_id":       vid_norm,
        "vendedor_nombre":   nombre,
        "trabaja_autoservicio": trabaja_as,
        "objetivo":          obj,
        "acumulado":         acum,
        "avance_pct":        round(av, 2),
        "tendencia_pct":    tendencia_pct_vd,
        "venta_hoy":         venta_hoy,
        "clientes_total":    cli_total,
        "clientes_pendientes": cli_sin,
        # CCC Compradores Mes — fuente: ventas.csv mes actual, ImporteNetoItem > 0
        "ccc_tradicional":   ccc_trad,
        "ccc_autoservicio":  ccc_as,
        "ccc_onpremise":     ccc_op,
        "ccc_total":         ccc_trad + ccc_as + ccc_op,
        # CCC Compradores Día — fuente: mod_ccc_segmento (ayer)
        "ccc_dia_tradicional": ccc_dia_trad,
        "ccc_dia_autoservicio": ccc_dia_as,
        "ccc_dia_onpremise": ccc_dia_op,
        "ccc_dia_total":     ccc_dia_trad + ccc_dia_as + ccc_dia_op,
        "once_t_cumplidos":  once_t_cumplidos,
        "once_t_total":      once_t_total,
        "titulares11":       titulares11,
        "modo_datos":        "REAL",
        "generado_en":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

@app.route("/api/planificacion", methods=["GET","POST"])
def planificacion():
    fecha_q = request.args.get("fecha")
    vid_q   = request.args.get("vendedor_id")
    conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    if request.method == "POST":
        d = request.get_json() or {}

        # Normalizar y validar vendedor_id
        vid_raw = normalizar_vendedor_codigo(d.get("vendedor_id",""))
        if vid_raw not in _VENDEDORES_ACTIVOS_PLAN:
            conn.close()
            return jsonify({"ok": False, "error": f"Vendedor {vid_raw} no autorizado"}), 400

        # Regla: V3 no trabaja autoservicio
        ccc_as = 0 if vid_raw == "V3" else int(d.get("ccc_autoservicio") or 0)
        fecha  = d.get("fecha") or datetime.now().strftime("%Y-%m-%d")

        conn.execute("""
            INSERT INTO planificacion
              (fecha, vendedor_id, zona, dia_visita, venta_esperada,
               ccc_tradicional, ccc_autoservicio, ccc_onpremise,
               once_t, marcas, clientes_clave, acciones, estado, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'enviada',CURRENT_TIMESTAMP)
            ON CONFLICT(fecha, vendedor_id) DO UPDATE SET
              zona=excluded.zona, dia_visita=excluded.dia_visita,
              venta_esperada=excluded.venta_esperada,
              ccc_tradicional=excluded.ccc_tradicional,
              ccc_autoservicio=excluded.ccc_autoservicio,
              ccc_onpremise=excluded.ccc_onpremise,
              once_t=excluded.once_t, marcas=excluded.marcas,
              clientes_clave=excluded.clientes_clave, acciones=excluded.acciones,
              estado='enviada', updated_at=CURRENT_TIMESTAMP""",
            (fecha, vid_raw, d.get("zona"), d.get("dia_visita"),
             float(d.get("venta_esperada") or 0),
             int(d.get("ccc_tradicional") or 0), ccc_as,
             int(d.get("ccc_onpremise") or 0), int(d.get("once_t") or 0),
             d.get("marcas"), d.get("clientes_clave"), d.get("acciones")))
        conn.commit(); conn.close()
        return jsonify({"ok": True, "vendedor_id": vid_raw, "fecha": fecha})

    # GET — filtros opcionales por fecha y/o vendedor_id
    if fecha_q and vid_q:
        rows = conn.execute(
            "SELECT * FROM planificacion WHERE fecha=? AND vendedor_id=? ORDER BY updated_at DESC",
            (fecha_q, vid_q.upper())).fetchall()
    elif fecha_q:
        rows = conn.execute(
            "SELECT * FROM planificacion WHERE fecha=? ORDER BY vendedor_id",
            (fecha_q,)).fetchall()
    elif vid_q:
        rows = conn.execute(
            "SELECT * FROM planificacion WHERE vendedor_id=? ORDER BY fecha DESC LIMIT 30",
            (vid_q.upper(),)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM planificacion ORDER BY fecha DESC, vendedor_id LIMIT 100").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/planificacion/<int:plan_id>", methods=["PATCH"])
def planificacion_patch(plan_id):
    d = request.get_json() or {}
    _ESTADOS = {"enviada", "modificada", "aprobada"}

    estado = d.get("estado")
    if estado and estado not in _ESTADOS:
        return jsonify({"ok": False, "error": f"Estado '{estado}' inválido. Válidos: {sorted(_ESTADOS)}"}), 400

    conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM planificacion WHERE id=?", (plan_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": f"Plan {plan_id} no encontrado"}), 404

    vid_row = (dict(row).get("vendedor_id") or "").upper()
    fields, vals = [], []

    for f in ["zona","dia_visita","venta_esperada","ccc_tradicional",
              "ccc_onpremise","once_t","marcas","clientes_clave","acciones"]:
        if f in d:
            fields.append(f"{f}=?"); vals.append(d[f])

    if "ccc_autoservicio" in d:
        val_as = 0 if vid_row == "V3" else int(d.get("ccc_autoservicio") or 0)
        fields.append("ccc_autoservicio=?"); vals.append(val_as)

    if estado:
        fields.append("estado=?"); vals.append(estado)
    if "editado_por" in d:
        fields.append("editado_por=?"); vals.append(d["editado_por"])
    if "comentario_gerencia" in d:
        fields.append("comentario_gerencia=?"); vals.append(d["comentario_gerencia"])

    fields.append("updated_at=CURRENT_TIMESTAMP")
    conn.execute(f"UPDATE planificacion SET {', '.join(fields)} WHERE id=?", vals + [plan_id])
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM planificacion WHERE id=?", (plan_id,)).fetchone())
    conn.close()
    return jsonify({"ok": True, "plan": updated})

@app.route("/api/mensajes", methods=["GET","POST"])
def mensajes():
    vid = request.args.get("vendedor_id")
    conn = sqlite3.connect(str(DB_PATH)); conn.row_factory = sqlite3.Row
    if request.method == "POST":
        d = request.get_json()
        conn.execute("INSERT INTO mensajes(vendedor_id,mensaje) VALUES(?,?)", (d.get("vendedor_id"), d.get("mensaje")))
        conn.commit(); conn.close()
        return jsonify({"ok":True})
    if vid:
        rows = conn.execute("SELECT * FROM mensajes WHERE vendedor_id=? ORDER BY created_at DESC", (vid,)).fetchall()
        conn.execute("UPDATE mensajes SET leido=1 WHERE vendedor_id=? AND leido=0", (vid,))
    else:
        rows = conn.execute("SELECT * FROM mensajes ORDER BY created_at DESC").fetchall()
    conn.commit(); conn.close()
    return jsonify([dict(r) for r in rows])

# ====== GASTOS POR ACCION COMERCIAL ======
@app.route("/api/gastos_accion")
def gastos_accion():
    df = read_csv(DATASETS / "mod_gastos_accion.csv")
    if df.empty:
        return jsonify({"modo_datos": "SIN_DATOS", "detalle": [], "resumen": {}, "top_acciones": [], "top_vendedores": []})

    for col in ["gasto_real_total", "gasto_teorico_total", "exceso_pesos_total", "exceso_pct_promedio",
                "clientes_afectados", "lineas_alertadas", "vendedor_codigo"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    resumen = {
        "filas_con_exceso":      int(len(df)),
        "gasto_real_total":      round(float(df["gasto_real_total"].sum()), 2),
        "gasto_teorico_total":   round(float(df["gasto_teorico_total"].sum()), 2),
        "exceso_pesos_total":    round(float(df["exceso_pesos_total"].sum()), 2),
        "exceso_pct_promedio":   round(float(df["exceso_pct_promedio"].mean()), 2),
        "vendedores_alertados":  int(df["vendedor_codigo"].nunique()),
        "clientes_afectados_total": int(df["clientes_afectados"].sum()),
        "acciones_csv":          int(df["es_regla_csv"].astype(str).str.upper().eq("TRUE").sum()),
        "acciones_fallback":     int(df["es_regla_csv"].astype(str).str.upper().ne("TRUE").sum()),
    }

    top_acc = (
        df.groupby(["accion_id", "canal", "categoria"], dropna=False)
        .agg(
            gasto_real_total   =("gasto_real_total",    "sum"),
            gasto_teorico_total=("gasto_teorico_total", "sum"),
            exceso_pesos_total =("exceso_pesos_total",  "sum"),
            clientes_afectados =("clientes_afectados",  "sum"),
            lineas_alertadas   =("lineas_alertadas",    "sum"),
            vendedores         =("vendedor_codigo",     "nunique"),
        )
        .reset_index()
        .sort_values("exceso_pesos_total", ascending=False)
        .head(5)
    )
    top_acciones = [
        {
            "accion_id":          str(r["accion_id"]),
            "canal":              str(r["canal"]),
            "categoria":          str(r["categoria"]),
            "gasto_real_total":   round(float(r["gasto_real_total"]), 2),
            "gasto_teorico_total":round(float(r["gasto_teorico_total"]), 2),
            "exceso_pesos_total": round(float(r["exceso_pesos_total"]), 2),
            "clientes_afectados": int(r["clientes_afectados"]),
            "lineas_alertadas":   int(r["lineas_alertadas"]),
            "vendedores":         int(r["vendedores"]),
        }
        for _, r in top_acc.iterrows()
    ]

    top_vend = (
        df.groupby(["vendedor_codigo", "vendedor_nombre"], dropna=False)
        .agg(
            gasto_real_total   =("gasto_real_total",   "sum"),
            gasto_teorico_total=("gasto_teorico_total","sum"),
            exceso_pesos_total =("exceso_pesos_total", "sum"),
            acciones_con_exceso=("accion_id",          "count"),
        )
        .reset_index()
        .sort_values("exceso_pesos_total", ascending=False)
        .head(5)
    )
    top_vendedores = [
        {
            "vendedor_codigo":    normalizar_vendedor_codigo(r["vendedor_codigo"]),
            "vendedor_nombre":    str(r["vendedor_nombre"]),
            "gasto_real_total":   round(float(r["gasto_real_total"]), 2),
            "gasto_teorico_total":round(float(r["gasto_teorico_total"]), 2),
            "exceso_pesos_total": round(float(r["exceso_pesos_total"]), 2),
            "acciones_con_exceso":int(r["acciones_con_exceso"]),
        }
        for _, r in top_vend.iterrows()
    ]

    detalle = df.replace({float("nan"): None}).to_dict(orient="records")

    return jsonify({
        "modo_datos":    "REAL",
        "generado_en":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "resumen":       resumen,
        "top_acciones":  top_acciones,
        "top_vendedores":top_vendedores,
        "detalle":       detalle,
    })

# ====== ORBIT DATA para el frontend ======
@app.route("/api/orbit-data")
def orbit_data():
    p = APP_DATA / "orbit_portal_data.json"
    if not p.exists():
        return jsonify({"error": "orbit_portal_data.json no encontrado. Ejecute tools/orbit_truth_audit.py primero."}), 503
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

# ====== MATINAL RESUMEN: plan ayer vs real ayer ======
@app.route("/api/matinal/resumen")
def matinal_resumen():
    """Compara plan de fecha solicitada (default: ayer) con venta_ayer del CSV."""
    ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    fecha_plan = request.args.get("fecha", ayer)

    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    planes = {row["vendedor_id"]: dict(row)
              for row in conn.execute(
                  "SELECT * FROM planificacion WHERE fecha=?", (fecha_plan,)).fetchall()}
    conn.close()

    vol  = read_csv(DATASETS / "mod_volumen_vendedor.csv")
    vend = read_csv(CONFIG   / "vendedores_activos.csv")

    resultado = []
    if not vend.empty:
        for _, v in vend[vend["activo"] == 1].iterrows():
            cod    = str(v["codigo_vendedor"]).strip()
            cn     = clean_code(cod)
            nombre = str(v["nombre_vendedor"]).strip()

            vv = vol[vol["vendedor_codigo"].astype(str).apply(clean_code) == cn] \
                 if not vol.empty else pd.DataFrame()
            real_ayer = float(vv["venta_ayer"].sum()) if not vv.empty else 0

            plan = planes.get(cod, {})
            plan_venta = float(plan.get("venta_esperada") or 0)
            delta = real_ayer - plan_venta
            pct   = round(real_ayer / plan_venta * 100, 1) if plan_venta else None

            resultado.append({
                "vendedor_id":      cod,
                "vendedor_nombre":  nombre,
                "fecha_plan":       fecha_plan,
                "plan_venta":       plan_venta,
                "real_ayer":        round(real_ayer, 2),
                "delta":            round(delta, 2),
                "pct_cumplimiento": pct,
                "plan_ccc_trad":    int(plan.get("ccc_tradicional") or 0),
                "plan_ccc_as":      int(plan.get("ccc_autoservicio") or 0),
                "plan_ccc_op":      int(plan.get("ccc_onpremise") or 0),
                "plan_once_t":      int(plan.get("once_t") or 0),
                "plan_acciones":    plan.get("acciones") or "",
                "plan_estado":      plan.get("estado") or "sin_plan",
                "plan_id":          plan.get("id"),
                "tiene_plan":       bool(plan),
            })

    return jsonify({
        "fecha_plan":   fecha_plan,
        "generado_en":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "resumen":      resultado,
    })


# ====== GERENCIA: CCC EMPRESA ======
@app.route("/api/gerencia/ccc_empresa")
def gerencia_ccc_empresa():
    """CCC mensual total empresa y por segmento, desglosado por vendedor activo.
    Fuente: ventas.csv (mes actual, ImporteNetoItem > 0). V3 sin AUTOSERVICIO."""
    ventas_mes = _cargar_ventas_mes_actual()
    ccc_map    = _ccc_mes_por_vendedor(ventas_mes)

    vend = read_csv(CONFIG / "vendedores_activos.csv")
    por_vendedor = []
    tot_trad, tot_as, tot_op = 0, 0, 0

    if not vend.empty:
        for _, v in vend[vend["activo"] == 1].iterrows():
            cn     = clean_code(str(v["codigo_vendedor"]))
            cod_int = int(cn) if cn.isdigit() else 0
            if cod_int in _VENDEDORES_EXCLUIDOS:
                continue
            nombre = str(v["nombre_vendedor"]).strip()
            ccc    = ccc_map.get(cod_int, {"tradicional": 0, "autoservicio": 0, "onpremise": 0, "total": 0})
            por_vendedor.append({
                "vendedor_id":   f"V{cn}",
                "vendedor_nombre": nombre,
                "tradicional":  ccc["tradicional"],
                "autoservicio": ccc["autoservicio"],
                "onpremise":    ccc["onpremise"],
                "total":        ccc["total"],
            })
            tot_trad += ccc["tradicional"]
            tot_as   += ccc["autoservicio"]
            tot_op   += ccc["onpremise"]

    return jsonify({
        "generado_en":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "empresa": {
            "tradicional":  tot_trad,
            "autoservicio": tot_as,
            "onpremise":    tot_op,
            "total":        tot_trad + tot_as + tot_op,
        },
        "por_vendedor": por_vendedor,
    })


# ====== GERENCIA: 11 TITULARES POR MARCA ======
@app.route("/api/gerencia/once_titulares")
def gerencia_once_titulares():
    """11 Titulares: CCC acumulado vs objetivo CCC.
    Fuente primaria : ventas_acumulada.csv (importeNeto > 0, excluye V2/V5/V20).
    Fuente fallback : mod_11_titulares.csv  (tiene_flag = 1).
    Fuente objetivo : objetivo 11T.xlsx."""

    # ── Brand alias lookup ──
    _MARCA_LOOKUP = {
        "ALMA MORA": "ALMA MORA", "ALARIS": "ALARIS", "TRAPICHE ALARIS": "ALARIS",
        "DON DAVID": "DON DAVID", "DADA": "DADA", "LOS ARBOLES": "LOS ARBOLES",
        "FINCA LAS MORAS": "FINCA LAS MORAS", "F LAS MORAS": "FINCA LAS MORAS",
        "TRAPICHE RESERVA": "TRAPICHE RESERVA",
        "FOND DE CAVE": "FOND DE CAVE", "FOND CAVE": "FOND DE CAVE",
        "CAZADOR": "CAZADOR", "ANTARES": "ANTARES",
        "GORDON'S FLAVOURS": "GORDON'S FLAVOURS", "GORDONS FLAVOURS": "GORDON'S FLAVOURS",
        "GORDON'S": "GORDON'S FLAVOURS", "GORDONS": "GORDON'S FLAVOURS",
        "GORDON S": "GORDON'S FLAVOURS",
        "SMIRNOFF": "SMIRNOFF FLAVOURS",
        "SMIRNOFF FLAVOURS": "SMIRNOFF FLAVOURS",
        "SMIRNOFF ICE FLAVOURS": "SMIRNOFF ICE",
        "SMIRNOFF ICE": "SMIRNOFF ICE",
        "JW": "JW BLACK", "JW BLACK": "JW BLACK", "JW RED": "JW RED",
        "MASCOTA": "MASCOTA", "LA MASCOTA": "MASCOTA",
        "NC ESPUMANTES": "NC ESPUMANTES", "NAVARRO CORREAS": "NC ESPUMANTES",
        "TRAPICHE MEDALLA": "TRAPICHE MEDALLA", "GRAN MEDALLA": "TRAPICHE MEDALLA",
    }
    _ART_KW = [
        ("SMIRNOFF ICE", "SMIRNOFF ICE"), ("SMF ICE", "SMIRNOFF ICE"),
        ("SMIRNOFF", "SMIRNOFF FLAVOURS"), ("GORDON", "GORDON'S FLAVOURS"),
        ("ANTARES", "ANTARES"), ("CAZADOR", "CAZADOR"),
        ("FOND DE CAVE", "FOND DE CAVE"), ("ALMA MORA", "ALMA MORA"),
        ("LOS ARBOLES", "LOS ARBOLES"), ("DADA", "DADA"),
        ("FINCA LAS MORAS", "FINCA LAS MORAS"), ("F.LAS MORAS", "FINCA LAS MORAS"),
        ("DON DAVID", "DON DAVID"), ("ALARIS", "ALARIS"),
        ("TRAPICHE RESERVA", "TRAPICHE RESERVA"),
        ("JW BLACK", "JW BLACK"), ("JW RED", "JW RED"),
    ]

    ccc_map = {}
    fuente = ""

    # ── Fuente primaria: ventas_acumulada.csv ──
    vac_path = INPUTS / "ventas_acumulada.csv"
    if vac_path.exists():
        try:
            vac = pd.read_csv(vac_path, sep=";", encoding="latin1", low_memory=False)
            vac["ImporteNetoItem"] = pd.to_numeric(
                vac["ImporteNetoItem"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
            vac = vac[~vac["CodVendedor"].isin(_VENDEDORES_EXCLUIDOS)]
            vac = vac[vac["ImporteNetoItem"] > 0]
            vac["marca_upper"] = vac["Marca"].astype(str).str.upper().str.strip()
            vac["marca_objetivo"] = vac["marca_upper"].map(_MARCA_LOOKUP)
            unresolved = vac["marca_objetivo"].isna()
            if unresolved.any():
                for kw, mo in _ART_KW:
                    still = vac["marca_objetivo"].isna() & unresolved
                    if not still.any():
                        break
                    hits = vac.loc[still, "Articulo"].astype(str).str.upper().str.contains(kw, regex=False, na=False)
                    vac.loc[still & hits, "marca_objetivo"] = mo
            ccc_map = (vac[vac["marca_objetivo"].notna()]
                       .groupby("marca_objetivo")["Cliente"]
                       .nunique().to_dict())
            fuente = "ventas_acumulada.csv"
        except Exception:
            ccc_map = {}

    # ── Fuente fallback: mod_11_titulares.csv (si la primaria no está disponible) ──
    if not ccc_map:
        t11_path = DATASETS / "mod_11_titulares.csv"
        if t11_path.exists():
            try:
                t11 = pd.read_csv(t11_path, sep=",", encoding="utf-8-sig", low_memory=False)
                t11["vendedor_codigo"] = pd.to_numeric(t11["vendedor_codigo"], errors="coerce")
                t11 = t11[~t11["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
                t11_ok = t11[t11["tiene_flag"].astype(str) == "1"]
                ccc_map = t11_ok.groupby("marca_objetivo")["cliente_id"].nunique().to_dict()
                fuente = "mod_11_titulares.csv (parcial)"
            except Exception:
                ccc_map = {}

    if not ccc_map:
        return jsonify({"error": "Sin fuente de CCC disponible", "marcas": [], "fuente": "N/A"}), 200

    # ── Objetivos: objetivo 11T.xlsx ──
    _OBJ_ALIAS = {
        "ALMA MORA": "ALMA MORA", "TRAPICHE RESERVA": "TRAPICHE RESERVA",
        "FINCA LAS MORAS": "FINCA LAS MORAS",
        "ALARIS": "ALARIS", "DON DAVID": "DON DAVID", "DADA": "DADA",
        "SIMRNOFF FLAVORS": "SMIRNOFF FLAVOURS", "SMIRNOFF FLAVORS": "SMIRNOFF FLAVOURS",
        "SMIRNOFF FLAVOURS": "SMIRNOFF FLAVOURS",
        "LOS ARBOLES": "LOS ARBOLES", "ANTARES": "ANTARES",
        "SMIRNOFF ICE": "SMIRNOFF ICE", "SMF ICE": "SMIRNOFF ICE",
        "GORDONS FLAVOURS": "GORDON'S FLAVOURS", "GORDONS FLAVORS": "GORDON'S FLAVOURS",
        "GORDON'S FLAVOURS": "GORDON'S FLAVOURS",
    }
    obj_map = {}
    try:
        obj_df = pd.read_excel(INPUTS / "objetivo 11T.xlsx", header=1)
        obj_df = obj_df.dropna(subset=obj_df.columns[1:2])
        for _, row in obj_df.iterrows():
            raw = str(row.iloc[1]).upper().strip()
            marca_key = _OBJ_ALIAS.get(raw, raw)
            try:
                obj_map[marca_key] = int(float(row.iloc[2]))
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    # ── Resultado: por marca, ordenado por CCC desc ──
    marcas = []
    for marca_obj in sorted(obj_map.keys(), key=lambda x: ccc_map.get(x, 0), reverse=True):
        ccc = ccc_map.get(marca_obj, 0)
        obj = obj_map[marca_obj]
        pct = round(ccc / obj * 100, 1) if obj else None
        marcas.append({"marca": marca_obj, "ccc": ccc, "objetivo_ccc": obj, "pct_objetivo": pct})

    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fuente": fuente,
        "total_marcas": len(marcas),
        "marcas": marcas,
    })


# ====== GERENCIA: 11 TITULARES CCC ZONA DEL DÍA ======
@app.route("/api/gerencia/once_titulares_zona")
def gerencia_once_titulares_zona():
    """11 Titulares: CCC por marca para los clientes de la zona del día.
    Sin objetivos — muestra penetración dentro de la zona.
    Fuente ventas : ventas_acumulada.csv
    Fuente zona   : clientes.xlsx (DiasVisita == dia)"""
    dia_raw = request.args.get("dia", "").strip()
    dia_key = dia_raw.lower()[:2] if dia_raw else ""   # "LU"→"lu", "Ma"→"ma"

    _MARCA_LOOKUP = {
        "ALMA MORA":"ALMA MORA","ALARIS":"ALARIS","TRAPICHE ALARIS":"ALARIS",
        "DON DAVID":"DON DAVID","DADA":"DADA","LOS ARBOLES":"LOS ARBOLES",
        "FINCA LAS MORAS":"FINCA LAS MORAS","F LAS MORAS":"FINCA LAS MORAS",
        "TRAPICHE RESERVA":"TRAPICHE RESERVA",
        "FOND DE CAVE":"FOND DE CAVE","FOND CAVE":"FOND DE CAVE",
        "CAZADOR":"CAZADOR","ANTARES":"ANTARES",
        "GORDON'S FLAVOURS":"GORDON'S FLAVOURS","GORDONS FLAVOURS":"GORDON'S FLAVOURS",
        "GORDON'S":"GORDON'S FLAVOURS","GORDONS":"GORDON'S FLAVOURS","GORDON S":"GORDON'S FLAVOURS",
        "SMIRNOFF":"SMIRNOFF FLAVOURS","SMIRNOFF FLAVOURS":"SMIRNOFF FLAVOURS",
        "SMIRNOFF ICE FLAVOURS":"SMIRNOFF ICE","SMIRNOFF ICE":"SMIRNOFF ICE",
        "JW":"JW BLACK","JW BLACK":"JW BLACK","JW RED":"JW RED",
        "MASCOTA":"MASCOTA","LA MASCOTA":"MASCOTA",
        "NC ESPUMANTES":"NC ESPUMANTES","NAVARRO CORREAS":"NC ESPUMANTES",
        "TRAPICHE MEDALLA":"TRAPICHE MEDALLA","GRAN MEDALLA":"TRAPICHE MEDALLA",
    }
    _ART_KW = [
        ("SMIRNOFF ICE","SMIRNOFF ICE"),("SMF ICE","SMIRNOFF ICE"),
        ("SMIRNOFF","SMIRNOFF FLAVOURS"),("GORDON","GORDON'S FLAVOURS"),
        ("ANTARES","ANTARES"),("CAZADOR","CAZADOR"),
        ("FOND DE CAVE","FOND DE CAVE"),("ALMA MORA","ALMA MORA"),
        ("LOS ARBOLES","LOS ARBOLES"),("DADA","DADA"),
        ("FINCA LAS MORAS","FINCA LAS MORAS"),("F.LAS MORAS","FINCA LAS MORAS"),
        ("DON DAVID","DON DAVID"),("ALARIS","ALARIS"),
        ("TRAPICHE RESERVA","TRAPICHE RESERVA"),
        ("JW BLACK","JW BLACK"),("JW RED","JW RED"),
    ]
    _OBJ_ALIAS = {
        "ALMA MORA":"ALMA MORA","TRAPICHE RESERVA":"TRAPICHE RESERVA",
        "FINCA LAS MORAS":"FINCA LAS MORAS","ALARIS":"ALARIS",
        "DON DAVID":"DON DAVID","DADA":"DADA",
        "SIMRNOFF FLAVORS":"SMIRNOFF FLAVOURS","SMIRNOFF FLAVORS":"SMIRNOFF FLAVOURS",
        "SMIRNOFF FLAVOURS":"SMIRNOFF FLAVOURS","LOS ARBOLES":"LOS ARBOLES",
        "ANTARES":"ANTARES","SMIRNOFF ICE":"SMIRNOFF ICE","SMF ICE":"SMIRNOFF ICE",
        "GORDONS FLAVOURS":"GORDON'S FLAVOURS","GORDONS FLAVORS":"GORDON'S FLAVOURS",
        "GORDON'S FLAVOURS":"GORDON'S FLAVOURS",
    }

    # ── Ventas acumuladas ──
    vac_path = INPUTS / "ventas_acumulada.csv"
    if not vac_path.exists():
        return jsonify({"error": "ventas_acumulada.csv no encontrado", "marcas": [], "dia": dia_raw}), 200
    try:
        vac = pd.read_csv(vac_path, sep=";", encoding="latin1", low_memory=False)
        vac["ImporteNetoItem"] = pd.to_numeric(
            vac["ImporteNetoItem"].astype(str).str.replace(",",".",regex=False), errors="coerce")
        vac = vac[~vac["CodVendedor"].isin(_VENDEDORES_EXCLUIDOS)]
        vac = vac[vac["ImporteNetoItem"] > 0]
    except Exception as e:
        return jsonify({"error": str(e), "marcas": [], "dia": dia_raw}), 200

    # ── Clientes de la zona del día ──
    zona_ids = set()
    cli_total = 0
    try:
        cli_path = INPUTS / "clientes.xlsx"
        if cli_path.exists():
            cli_df = pd.read_excel(cli_path)
            dias_col = next((c for c in cli_df.columns if "diasvisita" in c.lower().replace(" ","")), None)
            cod_col  = next((c for c in cli_df.columns if c.lower() in ("codigo","cod","id")), None)
            vend_col = next((c for c in cli_df.columns if c.lower() == "codven"), None)
            if dias_col and cod_col:
                if vend_col:
                    cli_df = cli_df[~pd.to_numeric(cli_df[vend_col], errors="coerce").isin(_VENDEDORES_EXCLUIDOS)]
                if dia_key:
                    cli_df = cli_df[cli_df[dias_col].astype(str).str.strip().str.lower() == dia_key]
                zona_ids = set(pd.to_numeric(cli_df[cod_col], errors="coerce").dropna().astype(int))
                cli_total = len(zona_ids)
    except Exception:
        pass

    # ── Filtrar ventas a zona ──
    if zona_ids:
        vac = vac[vac["Cliente"].isin(zona_ids)]

    # ── Normalizar marcas ──
    vac["marca_upper"] = vac["Marca"].astype(str).str.upper().str.strip()
    vac["marca_objetivo"] = vac["marca_upper"].map(_MARCA_LOOKUP)
    unresolved = vac["marca_objetivo"].isna()
    if unresolved.any():
        for kw, mo in _ART_KW:
            still = vac["marca_objetivo"].isna() & unresolved
            if not still.any():
                break
            hits = vac.loc[still, "Articulo"].astype(str).str.upper().str.contains(kw, regex=False, na=False)
            vac.loc[still & hits, "marca_objetivo"] = mo

    # CCC por marca en la zona
    ccc_map = (vac[vac["marca_objetivo"].notna()]
               .groupby("marca_objetivo")["Cliente"]
               .nunique().to_dict())

    # Orden oficial desde objetivo 11T.xlsx
    marcas_orden = []
    try:
        obj_df = pd.read_excel(INPUTS / "objetivo 11T.xlsx", header=1)
        obj_df = obj_df.dropna(subset=obj_df.columns[1:2])
        for _, row in obj_df.iterrows():
            raw = str(row.iloc[1]).upper().strip()
            mk = _OBJ_ALIAS.get(raw, raw)
            if mk and mk not in marcas_orden:
                marcas_orden.append(mk)
    except Exception:
        pass
    if not marcas_orden:
        marcas_orden = sorted(ccc_map.keys(), key=lambda x: ccc_map.get(x, 0), reverse=True)

    marcas = [{"marca": m, "ccc": ccc_map.get(m, 0)} for m in marcas_orden]

    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dia": dia_raw.upper() if dia_raw else "TODOS",
        "total_clientes_zona": cli_total,
        "fuente": "ventas_acumulada.csv",
        "marcas": marcas,
    })


# ====== GERENCIA: RANKING RECHAZOS ======
@app.route("/api/gerencia/ranking_rechazos")
def gerencia_ranking_rechazos():
    """Ranking de % rechazo por vendedor.
    Fuente: 01_INPUTS/resultado.xlsx hoja Rechazos.
    Filtra: solo Origen == Vendedor, excluye V2/V5/V20."""
    try:
        df = pd.read_excel(INPUTS / "resultado.xlsx", sheet_name="Rechazos")
    except Exception as e:
        return jsonify({"error": str(e), "vendedores": []}), 200

    df.columns = [c.strip() for c in df.columns]

    # Solo vendedores (excluir filas de supervisores)
    if "Origen" in df.columns:
        df = df[df["Origen"].astype(str).str.strip().str.lower() == "vendedor"]

    df["VendedorCodigo"] = pd.to_numeric(df["VendedorCodigo"], errors="coerce")
    df = df[~df["VendedorCodigo"].isin(_VENDEDORES_EXCLUIDOS)]
    df["PorcRechazo"] = pd.to_numeric(df["PorcRechazo"], errors="coerce").fillna(0)

    resultado = []
    for _, row in df.iterrows():
        cod = int(row["VendedorCodigo"])
        nombre = str(row.get("VendedorNombre", f"V{cod}")).strip()
        pct = round(float(row["PorcRechazo"]), 1)
        resultado.append({
            "vendedor_id":     f"V{cod}",
            "vendedor_nombre": nombre,
            "rechazo_pct":     pct,
        })

    resultado.sort(key=lambda x: x["rechazo_pct"], reverse=True)
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fuente":      "resultado.xlsx · hoja Rechazos",
        "vendedores":  resultado,
    })


# ====== GERENCIA: 11T RESUMEN DISTRIBUIDORA ======
@app.route("/api/gerencia/11t_empresa")
def gerencia_11t_empresa():
    """11T distribuidora: por marca, clientes con/sin cada titular (todos los vendedores).
    Fuente: mod_11_titulares.csv  — columnas tiene_flag / falta_flag."""
    df = read_csv(DATASETS / "mod_11_titulares.csv")
    if df.empty:
        return jsonify({"marcas": [], "error": "Sin datos en mod_11_titulares.csv"}), 200

    df.columns = [c.lstrip("﻿").strip() for c in df.columns]
    df["vendedor_codigo"] = pd.to_numeric(df["vendedor_codigo"], errors="coerce")
    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]

    for col in ("tiene_flag", "falta_flag"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    vendedores_activos = sorted(df["vendedor_codigo"].dropna().unique())

    result = []
    for marca, grp in df.groupby("marca_objetivo"):
        con   = int(grp["tiene_flag"].sum())
        sin   = int(grp["falta_flag"].sum())
        total = con + sin
        pct   = round(con / total * 100, 1) if total else 0.0

        por_vendedor = {}
        for v in vendedores_activos:
            vg  = grp[grp["vendedor_codigo"] == v]
            vc  = int(vg["tiene_flag"].sum())
            vs  = int(vg["falta_flag"].sum())
            vt  = vc + vs
            por_vendedor[f"V{int(v)}"] = {
                "con": vc, "sin": vs, "total": vt,
                "pct": round(vc / vt * 100, 1) if vt else 0.0,
            }

        result.append({
            "marca":        str(marca),
            "con":          con,
            "sin":          sin,
            "total":        total,
            "pct":          pct,
            "por_vendedor": por_vendedor,
        })

    result.sort(key=lambda x: x["pct"], reverse=True)
    return jsonify({
        "generado_en":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fuente":         "mod_11_titulares.csv",
        "total_marcas":   len(result),
        "vendedores":     [f"V{int(v)}" for v in vendedores_activos],
        "marcas":         result,
    })


# ====== GERENCIA: 11T POR VENDEDOR ======
@app.route("/api/gerencia/11t_vendedor")
def gerencia_11t_vendedor():
    """11T detalle de un vendedor específico.
    Parámetro: vendedor=V3 (o 3). Fuente: mod_11_titulares.csv."""
    import re as _re
    vend_raw = request.args.get("vendedor", "").strip().upper()
    m = _re.search(r"\d+", vend_raw)
    if not m:
        return jsonify({"marcas": [], "error": "Parámetro vendedor inválido"}), 200
    cod = int(m.group())

    df = read_csv(DATASETS / "mod_11_titulares.csv")
    if df.empty:
        return jsonify({"marcas": [], "error": "Sin datos"}), 200

    df.columns = [c.lstrip("﻿").strip() for c in df.columns]
    df["vendedor_codigo"] = pd.to_numeric(df["vendedor_codigo"], errors="coerce")
    df = df[df["vendedor_codigo"] == cod]

    if df.empty:
        return jsonify({"marcas": [], "vendedor": f"V{cod}", "error": "Sin datos para este vendedor"}), 200

    for col in ("tiene_flag", "falta_flag"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    nombre = str(df["vendedor_nombre"].iloc[0]) if "vendedor_nombre" in df.columns else f"V{cod}"

    result = []
    for marca, grp in df.groupby("marca_objetivo"):
        con   = int(grp["tiene_flag"].sum())
        sin   = int(grp["falta_flag"].sum())
        total = con + sin
        pct   = round(con / total * 100, 1) if total else 0.0
        result.append({
            "marca": str(marca), "con": con, "sin": sin, "total": total, "pct": pct
        })

    result.sort(key=lambda x: x["pct"], reverse=True)
    return jsonify({
        "generado_en":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fuente":           "mod_11_titulares.csv",
        "vendedor":         f"V{cod}",
        "vendedor_nombre":  nombre,
        "total_marcas":     len(result),
        "marcas":           result,
    })


# ====== GERENCIA: COBERTURA POR SEGMENTO ======
@app.route("/api/gerencia/cobertura_segmento")
def gerencia_cobertura_segmento():
    """Cobertura acumulada del mes por vendedor × segmento.
    Fuente: clientes_dia.csv (cobertura_mes_flag).
    Excluye V2, V5, V20. V3 sin AUTOSERVICIO."""
    df = read_csv(DATASETS / "clientes_dia.csv")
    if df.empty:
        return jsonify({"generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "vendedores": []})

    df.columns = [c.lstrip("﻿") for c in df.columns]
    for col in ["vendedor_codigo", "cobertura_mes_flag"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
    # V3 no trabaja autoservicio
    mask_v3_as = (df["vendedor_codigo"] == 3) & (df["segmento_operativo"].astype(str).str.upper() == "AUTOSERVICIO")
    df = df[~mask_v3_as]

    if "segmento_operativo" not in df.columns or "cobertura_mes_flag" not in df.columns:
        return jsonify({"error": "Columnas esperadas no encontradas", "columnas": list(df.columns)}), 500

    resultado = []
    for (cod, seg), grp in df.groupby(["vendedor_codigo", "segmento_operativo"]):
        cod_int = int(cod) if pd.notnull(cod) else 0
        total      = len(grp)
        con_cob    = int(grp["cobertura_mes_flag"].fillna(0).sum())
        pct        = round(con_cob / total * 100, 1) if total else 0
        nombre_col = str(grp.iloc[0].get("vendedor_nombre", f"V{cod_int}")) if "vendedor_nombre" in grp.columns else f"V{cod_int}"
        resultado.append({
            "vendedor_id":      f"V{cod_int}",
            "vendedor_nombre":  nombre_col,
            "segmento":         str(seg),
            "total_clientes":   total,
            "con_cobertura":    con_cob,
            "pct_cobertura":    pct,
        })

    resultado.sort(key=lambda x: (x["vendedor_id"], x["segmento"]))
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cobertura": resultado,
    })


# ====== GERENCIA: REAL AYER POR SEGMENTO ======
@app.route("/api/gerencia/real_ayer_segmento")
def gerencia_real_ayer_segmento():
    """Real del día anterior por vendedor × segmento.
    Fuente: mod_ccc_segmento.csv. Vendedores sin venta ayer aparecen con cero.
    V3 sin AUTOSERVICIO."""
    ccc_df = read_csv(DATASETS / "mod_ccc_segmento.csv")
    vend   = read_csv(CONFIG / "vendedores_activos.csv")

    ccc_df.columns = [c.lstrip("﻿") for c in ccc_df.columns] if not ccc_df.empty else []
    for col in ["vendedor_codigo", "clientes_con_compra", "coberturas_logradas", "botellas_vendidas", "venta_neta"]:
        if not ccc_df.empty and col in ccc_df.columns:
            ccc_df[col] = pd.to_numeric(ccc_df[col], errors="coerce")

    # Construir índice: (cod_int, segmento) → datos
    ccc_idx = {}
    if not ccc_df.empty:
        for _, row in ccc_df.iterrows():
            cod_int = int(row["vendedor_codigo"]) if pd.notnull(row.get("vendedor_codigo")) else 0
            seg     = str(row.get("segmento_operativo", "")).upper()
            ccc_idx[(cod_int, seg)] = {
                "clientes_con_compra": int(row.get("clientes_con_compra", 0) or 0),
                "coberturas_logradas": int(row.get("coberturas_logradas", 0) or 0),
                "botellas_vendidas":   int(row.get("botellas_vendidas", 0) or 0),
                "venta_neta":          round(float(row.get("venta_neta", 0) or 0), 2),
            }

    SEGMENTOS_POSIBLES = ["TRADICIONAL", "AUTOSERVICIO", "ON_PREMISE_VTK"]
    _cero = {"clientes_con_compra": 0, "coberturas_logradas": 0, "botellas_vendidas": 0, "venta_neta": 0.0}

    resultado = []
    if not vend.empty:
        for _, v in vend[vend["activo"] == 1].iterrows():
            cn      = clean_code(str(v["codigo_vendedor"]))
            cod_int = int(cn) if cn.isdigit() else 0
            if cod_int in _VENDEDORES_EXCLUIDOS:
                continue
            nombre = str(v["nombre_vendedor"]).strip()
            es_v3  = (cod_int == 3)
            segs   = []
            for seg in SEGMENTOS_POSIBLES:
                if es_v3 and seg == "AUTOSERVICIO":
                    continue
                datos = ccc_idx.get((cod_int, seg), _cero).copy()
                datos["segmento"] = seg
                segs.append(datos)
            resultado.append({
                "vendedor_id":      f"V{cn}",
                "vendedor_nombre":  nombre,
                "venta_total_ayer": round(sum(s["venta_neta"] for s in segs), 2),
                "segmentos":        segs,
            })

    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vendedores":  resultado,
    })


# ====== GERENCIA: PLANES AUTOSERVICIO ======
@app.route("/api/gerencia/planes_autoservicio")
def gerencia_planes_autoservicio():
    """Acciones en canal AUTOSERVICIOS con gasto real vs teórico.
    ADVERTENCIA: no existe fuente de 'planes formales' ni sin cargos detallados.
    Esta respuesta expone mod_gastos_accion.csv filtrado por canal AUTOSERVICIOS.
    V3 excluida. Excluye V2, V5, V20."""
    df = read_csv(DATASETS / "mod_gastos_accion.csv")
    if df.empty:
        return jsonify({
            "fuente_limitada": True,
            "advertencia": "mod_gastos_accion.csv no encontrado o vacío.",
            "acciones": [],
        })

    df.columns = [c.lstrip("﻿") for c in df.columns]
    for col in ["vendedor_codigo", "clientes_afectados", "lineas_alertadas",
                "gasto_real_total", "gasto_teorico_total", "exceso_pesos_total", "exceso_pct_promedio"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Excluir V3 (no trabaja AS), V2, V5, V20
    excluir = _VENDEDORES_EXCLUIDOS | {3}
    df = df[~df["vendedor_codigo"].isin(excluir)]

    # Filtrar canal AUTOSERVICIOS
    if "canal" in df.columns:
        df = df[df["canal"].astype(str).str.upper().str.contains("AUTOSERVICIO", na=False)]

    acciones = df.where(pd.notnull(df), None).to_dict(orient="records")

    return jsonify({
        "fuente_limitada": True,
        "advertencia": (
            "Sin cargos formales no disponibles: no existe tabla de sin cargos en este sistema. "
            "Se muestran únicamente acciones con canal AUTOSERVICIOS de mod_gastos_accion.csv."
        ),
        "total_acciones": len(acciones),
        "acciones": acciones,
    })


# ====== GERENCIA: INNOVACIONES POR SEGMENTO ======
@app.route("/api/gerencia/innovaciones_segmento")
def gerencia_innovaciones_segmento():
    """Frizze Manxana (14620) y Antares XPA (60020) por segmento, empresa completa.
    Fuente: mod_innovaciones_segmento.csv. Excluye V2, V5, V20 y V3/AUTOSERVICIO."""
    df = read_csv(DATASETS / "mod_innovaciones_segmento.csv")
    if df.empty:
        return jsonify({
            "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fuente": "mod_innovaciones_segmento.csv",
            "advertencia": "Dato no disponible",
            "resumen_empresa": [], "por_vendedor": [],
        })
    df.columns = [c.lstrip("﻿") for c in df.columns]
    for col in ["vendedor_codigo", "producto_codigo", "clientes_cartera", "clientes_compraron", "pct_cobertura"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
    df = df[~((df["vendedor_codigo"] == 3) & (df["segmento"].astype(str).str.upper() == "AUTOSERVICIO"))].copy()
    fecha_ej = str(df["fecha_ejecucion"].iloc[0]) if "fecha_ejecucion" in df.columns and not df.empty else None
    agg = (df.groupby(["producto_codigo", "producto_nombre", "segmento"], dropna=False)
             .agg(clientes_cartera=("clientes_cartera", "sum"),
                  clientes_compraron=("clientes_compraron", "sum"))
             .reset_index())
    resumen_empresa = []
    for _, row in agg.iterrows():
        cartera = int(row["clientes_cartera"]); compraron = int(row["clientes_compraron"])
        resumen_empresa.append({
            "producto_codigo": int(row["producto_codigo"]), "producto_nombre": str(row["producto_nombre"]),
            "segmento": str(row["segmento"]), "clientes_cartera": cartera,
            "clientes_compraron": compraron,
            "pct_cobertura": round(compraron / cartera, 4) if cartera else 0.0,
        })
    resumen_empresa.sort(key=lambda x: (x["producto_codigo"], x["segmento"]))
    por_vendedor = []
    for cod, grp in df.groupby("vendedor_codigo"):
        cod_int = int(cod); nombre = str(grp["vendedor_nombre"].iloc[0])
        productos = []
        for _, row in grp.iterrows():
            cartera = int(row["clientes_cartera"]); compraron = int(row["clientes_compraron"])
            faltantes_raw = str(row.get("clientes_faltantes", "") or "")
            faltantes = [int(x) for x in faltantes_raw.split("|") if x.strip().isdigit()]
            productos.append({
                "segmento": str(row["segmento"]), "producto_codigo": int(row["producto_codigo"]),
                "producto_nombre": str(row["producto_nombre"]), "clientes_cartera": cartera,
                "clientes_compraron": compraron,
                "pct_cobertura": round(compraron / cartera, 4) if cartera else 0.0,
                "clientes_faltantes": faltantes,
            })
        productos.sort(key=lambda x: (x["segmento"], x["producto_codigo"]))
        por_vendedor.append({"vendedor_id": f"V{cod_int}", "vendedor_nombre": nombre, "productos": productos})
    por_vendedor.sort(key=lambda x: x["vendedor_id"])
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fuente": "mod_innovaciones_segmento.csv",
        "fecha_ejecucion": fecha_ej,
        "resumen_empresa": resumen_empresa,
        "por_vendedor": por_vendedor,
    })


# ====== VENDEDOR: INNOVACIONES POR SEGMENTO ======
@app.route("/api/vendedor/<vid>/innovaciones_segmento")
def vendedor_innovaciones_segmento(vid):
    """Cobertura de innovaciones por segmento para un vendedor específico.
    Fuente: mod_innovaciones_segmento.csv. V3 sin AUTOSERVICIO."""
    vid_norm = normalizar_vendedor_codigo(vid)
    cn = clean_code(vid_norm)
    cod_int = int(cn) if cn.isdigit() else 0
    if cod_int in _VENDEDORES_EXCLUIDOS:
        return jsonify({"error": f"Vendedor {vid_norm} excluido"}), 403
    vend = read_csv(CONFIG / "vendedores_activos.csv")
    nombre = vid_norm
    if not vend.empty:
        mask = (vend["activo"] == 1) & (vend["codigo_vendedor"].astype(str).apply(clean_code) == cn)
        fila = vend[mask]
        if fila.empty:
            return jsonify({"error": f"Vendedor {vid_norm} no encontrado o inactivo"}), 404
        nombre = str(fila.iloc[0]["nombre_vendedor"])
    df = read_csv(DATASETS / "mod_innovaciones_segmento.csv")
    if df.empty:
        return jsonify({
            "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "vendedor_id": vid_norm, "vendedor_nombre": nombre,
            "fuente": "mod_innovaciones_segmento.csv",
            "advertencia": "Dato no disponible", "productos": [],
        })
    df.columns = [c.lstrip("﻿") for c in df.columns]
    for col in ["vendedor_codigo", "producto_codigo", "clientes_cartera", "clientes_compraron"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    dv = df[df["vendedor_codigo"] == cod_int].copy()
    if cod_int == 3:
        dv = dv[dv["segmento"].astype(str).str.upper() != "AUTOSERVICIO"]
    fecha_ej = str(dv["fecha_ejecucion"].iloc[0]) if "fecha_ejecucion" in dv.columns and not dv.empty else None
    productos = []
    for _, row in dv.iterrows():
        cartera = int(row["clientes_cartera"]); compraron = int(row["clientes_compraron"])
        faltantes_raw = str(row.get("clientes_faltantes", "") or "")
        faltantes = [int(x) for x in faltantes_raw.split("|") if x.strip().isdigit()]
        productos.append({
            "segmento": str(row["segmento"]), "producto_codigo": int(row["producto_codigo"]),
            "producto_nombre": str(row["producto_nombre"]), "clientes_cartera": cartera,
            "clientes_compraron": compraron,
            "pct_cobertura": round(compraron / cartera, 4) if cartera else 0.0,
            "clientes_faltantes": faltantes,
        })
    productos.sort(key=lambda x: (x["segmento"], x["producto_codigo"]))
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vendedor_id": vid_norm, "vendedor_nombre": nombre,
        "fuente": "mod_innovaciones_segmento.csv",
        "fecha_ejecucion": fecha_ej, "productos": productos,
    })


# ====== VENDEDOR: PLAN DE ACCIÓN INNOVACIONES ======
@app.route("/api/vendedor/<vid>/plan_innovaciones")
def vendedor_plan_innovaciones(vid):
    """Faltantes de Innovaciones enriquecidos con datos de cliente para plan de acción.
    Fuente: mod_innovaciones_segmento.csv + clientes_dia.csv + clientes_master.csv.
    V3 sin AUTOSERVICIO. Excluye V2, V5, V20."""
    def parse_clientes_faltantes(v):
        if isinstance(v, list):
            result = []
            for x in v:
                try: result.append(int(x))
                except (ValueError, TypeError): pass
            return result
        s = str(v or "").strip()
        if not s or s in ("nan", "None", "[]"):
            return []
        s = s.strip("[]")
        sep = "|" if "|" in s else ","
        result = []
        for x in s.split(sep):
            x = x.strip()
            if x.isdigit():
                result.append(int(x))
        return result

    vid_norm = normalizar_vendedor_codigo(vid)
    cn = clean_code(vid_norm)
    cod_int = int(cn) if cn.isdigit() else 0
    if cod_int in _VENDEDORES_EXCLUIDOS:
        return jsonify({"error": f"Vendedor {vid_norm} excluido"}), 403
    vend = read_csv(CONFIG / "vendedores_activos.csv")
    nombre = vid_norm
    if not vend.empty:
        mask = (vend["activo"] == 1) & (vend["codigo_vendedor"].astype(str).apply(clean_code) == cn)
        fila = vend[mask]
        if fila.empty:
            return jsonify({"error": f"Vendedor {vid_norm} no encontrado o inactivo"}), 404
        nombre = str(fila.iloc[0]["nombre_vendedor"])
    df = read_csv(DATASETS / "mod_innovaciones_segmento.csv")
    if df.empty:
        return jsonify({
            "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "vendedor_id": vid_norm, "vendedor_nombre": nombre,
            "advertencia": "Dato no disponible", "productos": [],
        })
    df.columns = [str(c).lstrip(chr(65279)).strip() for c in df.columns]
    for col in ["vendedor_codigo", "producto_codigo", "clientes_cartera", "clientes_compraron"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    dv = df[df["vendedor_codigo"] == cod_int].copy()
    if cod_int == 3:
        dv = dv[dv["segmento"].astype(str).str.upper() != "AUTOSERVICIO"]
    if dv.empty:
        return jsonify({
            "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "vendedor_id": vid_norm, "vendedor_nombre": nombre,
            "advertencia": "Sin datos de innovaciones para este vendedor", "productos": [],
        })
    cli_dia = read_csv(DATASETS / "clientes_dia.csv")
    cli_dia_idx = {}
    if not cli_dia.empty:
        cli_dia["cliente_id"] = pd.to_numeric(cli_dia["cliente_id"], errors="coerce")
        if "vendedor_codigo" in cli_dia.columns:
            cli_dia["vendedor_codigo"] = pd.to_numeric(cli_dia["vendedor_codigo"], errors="coerce")
            cli_dia = cli_dia[cli_dia["vendedor_codigo"] == cod_int]
        for _, r in cli_dia.iterrows():
            cid = int(r["cliente_id"]) if not pd.isna(r["cliente_id"]) else None
            if cid is not None:
                cli_dia_idx[cid] = r
    cli_master = read_csv(BASE / "05_MASTER_DATA" / "clientes_master.csv")
    cli_master_idx = {}
    if not cli_master.empty:
        cli_master.columns = [str(c).lstrip(chr(65279)).strip() for c in cli_master.columns]
        cli_master["cliente_id"] = pd.to_numeric(cli_master["cliente_id"], errors="coerce")
        for _, r in cli_master.iterrows():
            cid = int(r["cliente_id"]) if not pd.isna(r["cliente_id"]) else None
            if cid is not None:
                cli_master_idx[cid] = r
    PRIO_ORD = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
    productos = []
    for _, row in dv.iterrows():
        cartera = int(row["clientes_cartera"]); compraron = int(row["clientes_compraron"])
        faltantes_ids = parse_clientes_faltantes(row.get("clientes_faltantes", ""))
        plan = []
        for cid in faltantes_ids:
            if cid in cli_dia_idx:
                r = cli_dia_idx[cid]
                plan.append({
                    "cliente_id": cid,
                    "cliente_nombre": str(r.get("cliente_nombre", "") or ""),
                    "segmento": str(r.get("segmento_operativo", r.get("segmento", "")) or ""),
                    "localidad": str(r.get("localidad", "") or ""),
                    "ruta": str(r.get("ruta", "") or ""),
                    "dias_visita": str(r.get("dias_visita", "") or ""),
                    "prioridad": str(r.get("prioridad_comercial", "") or "") or None,
                    "en_zona_hoy": True,
                    "enriquecimiento": "completo",
                })
            elif cid in cli_master_idx:
                r = cli_master_idx[cid]
                plan.append({
                    "cliente_id": cid,
                    "cliente_nombre": str(r.get("cliente_nombre", "") or ""),
                    "segmento": str(r.get("segmento", "") or ""),
                    "localidad": str(r.get("localidad", "") or ""),
                    "ruta": None,
                    "dias_visita": None,
                    "prioridad": None,
                    "en_zona_hoy": False,
                    "enriquecimiento": "parcial",
                })
            else:
                plan.append({
                    "cliente_id": cid,
                    "cliente_nombre": None,
                    "segmento": None, "localidad": None,
                    "ruta": None, "dias_visita": None, "prioridad": None,
                    "en_zona_hoy": False,
                    "enriquecimiento": "sin_datos",
                })
        plan.sort(key=lambda x: (
            0 if x["en_zona_hoy"] else 1,
            PRIO_ORD.get(x.get("prioridad") or "", 9),
            x.get("cliente_nombre") or "",
        ))
        productos.append({
            "segmento": str(row["segmento"]),
            "producto_codigo": int(row["producto_codigo"]),
            "producto_nombre": str(row["producto_nombre"]),
            "clientes_cartera": cartera,
            "clientes_compraron": compraron,
            "pct_cobertura": round(compraron / cartera, 4) if cartera else 0.0,
            "total_faltantes": len(plan),
            "en_zona_hoy": sum(1 for c in plan if c["en_zona_hoy"]),
            "plan": plan,
        })
    productos.sort(key=lambda x: (x["segmento"], x["producto_codigo"]))
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vendedor_id": vid_norm, "vendedor_nombre": nombre,
        "fuente": "mod_innovaciones_segmento.csv + clientes_dia.csv + clientes_master.csv",
        "productos": productos,
    })


# ====== COBERTURA ACUMULADA ======
@app.route("/api/gerencia/cobertura_acum")
def gerencia_cobertura_acum():
    df = read_csv(DATASETS / "mod_cobertura_acum.csv")
    if df.empty:
        return jsonify({"error": "Sin datos"}), 404
    df["vendedor_codigo"] = pd.to_numeric(df["vendedor_codigo"], errors="coerce")
    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
    for c in ["cartera", "cubiertos", "sin_cobertura"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    df["pct_cobertura"] = pd.to_numeric(df.get("pct_cobertura", 0), errors="coerce").fillna(0)
    fecha = str(df["fecha_calculo"].iloc[0]) if "fecha_calculo" in df.columns else ""
    por_vendedor = {}
    for _, row in df.iterrows():
        vid = f"V{int(row['vendedor_codigo'])}"
        if vid not in por_vendedor:
            por_vendedor[vid] = {"vendedor_id": vid, "vendedor_nombre": str(row.get("vendedor_nombre", "")), "segmentos": []}
        por_vendedor[vid]["segmentos"].append({
            "segmento": str(row["segmento"]),
            "cartera": int(row["cartera"]),
            "cubiertos": int(row["cubiertos"]),
            "sin_cobertura": int(row["sin_cobertura"]),
            "pct_cobertura": round(float(row["pct_cobertura"]), 4),
        })
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_calculo": fecha,
        "fuente": "mod_cobertura_acum.csv",
        "por_vendedor": list(por_vendedor.values()),
    })


# ====== 11T ACUMULADO ======
@app.route("/api/gerencia/11t_acum")
def gerencia_11t_acum():
    df = read_csv(DATASETS / "mod_11t_acum.csv")
    if df.empty:
        return jsonify({"error": "Sin datos"}), 404
    df["vendedor_codigo"] = pd.to_numeric(df["vendedor_codigo"], errors="coerce")
    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
    df["tiene_flag"] = pd.to_numeric(df["tiene_flag"], errors="coerce").fillna(0)
    # Resumen por marca (distribuidora total)
    por_marca = (df.groupby("marca_objetivo")
                 .agg(cartera=("cliente_id", "count"), cubiertos=("tiene_flag", "sum"))
                 .reset_index())
    por_marca["cubiertos"] = por_marca["cubiertos"].astype(int)
    por_marca["pct"] = (por_marca["cubiertos"] / por_marca["cartera"].replace(0, 1) * 100).round(1)
    por_marca = por_marca.sort_values("cubiertos", ascending=False)
    # Resumen por vendedor × marca
    por_vend = (df.groupby(["vendedor_codigo", "vendedor_nombre", "marca_objetivo"])
                .agg(cartera=("cliente_id", "count"), cubiertos=("tiene_flag", "sum"))
                .reset_index())
    por_vend["cubiertos"] = por_vend["cubiertos"].astype(int)
    por_vend["vendedor_id"] = "V" + por_vend["vendedor_codigo"].astype(int).astype(str)
    fecha = str(df["fecha_calculo"].iloc[0]) if "fecha_calculo" in df.columns else ""
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_calculo": fecha,
        "fuente": "mod_11t_acum.csv",
        "por_marca": por_marca[["marca_objetivo", "cartera", "cubiertos", "pct"]].to_dict("records"),
        "por_vendedor": por_vend[["vendedor_id", "vendedor_nombre", "marca_objetivo",
                                   "cartera", "cubiertos"]].to_dict("records"),
    })


# ====== INNOVACIONES TOTAL GERENCIA ======
@app.route("/api/gerencia/innovaciones_total")
def gerencia_innovaciones_total():
    """Cobertura de innovaciones. Acepta ?dia=MA para agregar compraron_dia por producto."""
    dia_param = request.args.get("dia", "").strip().capitalize()
    df = read_csv(DATASETS / "mod_innovaciones_segmento.csv")
    if df.empty:
        return jsonify({"error": "Sin datos"}), 404
    df["vendedor_codigo"] = pd.to_numeric(df["vendedor_codigo"], errors="coerce")
    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
    df["clientes_cartera"]  = pd.to_numeric(df["clientes_cartera"],  errors="coerce").fillna(0)
    df["clientes_compraron"] = pd.to_numeric(df["clientes_compraron"], errors="coerce").fillna(0)
    df["producto_codigo"] = pd.to_numeric(df["producto_codigo"], errors="coerce").fillna(0).astype(int)
    # Total por producto × segmento (toda la distribuidora)
    tot = (df.groupby(["producto_codigo", "producto_nombre", "segmento"])
           .agg(cartera_total=("clientes_cartera", "sum"),
                compraron_total=("clientes_compraron", "sum"))
           .reset_index())
    tot["pct_cobertura"] = (tot["compraron_total"] / tot["cartera_total"].replace(0, 1) * 100).round(1)
    # compraron_dia: clientes del día que compraron el producto (ventas_acumulada × clientes del día)
    compraron_dia_map = {}   # producto_codigo → count
    if dia_param:
        try:
            acum_path = INPUTS / "ventas_acumulada.csv"
            if acum_path.exists():
                acum = pd.read_csv(acum_path, encoding="latin1", sep=";", engine="python")
                acum["Codigo"]         = pd.to_numeric(acum["Codigo"], errors="coerce")
                acum["Cliente"]        = pd.to_numeric(acum["Cliente"], errors="coerce")
                acum["ImporteNetoItem"] = (acum["ImporteNetoItem"].astype(str)
                                           .str.replace(".", "", regex=False)
                                           .str.replace(",", ".", regex=False))
                acum["ImporteNetoItem"] = pd.to_numeric(acum["ImporteNetoItem"], errors="coerce").fillna(0)
                acum = acum[acum["ImporteNetoItem"] > 0]
                cli_dia = _clientes_por_dia(dia_param)
                if not cli_dia.empty and "cliente_id" in cli_dia.columns:
                    dia_ids = set(cli_dia["cliente_id"].dropna().astype(int))
                    prod_codes = set(df["producto_codigo"].dropna().astype(int).tolist())
                    for cod in prod_codes:
                        compraron_dia_map[int(cod)] = int(
                            acum[(acum["Codigo"] == cod) & (acum["Cliente"].isin(dia_ids))]
                            ["Cliente"].nunique()
                        )
        except Exception as e:
            print(f"[WARN] innovaciones_total ?dia: {e}")
    records = []
    for _, row in tot.iterrows():
        pcod = int(row["producto_codigo"])
        rec = {
            "producto_codigo": pcod,
            "producto_nombre": str(row["producto_nombre"]),
            "segmento": str(row["segmento"]),
            "cartera_total": int(row["cartera_total"]),
            "compraron_total": int(row["compraron_total"]),
            "pct_cobertura": float(row["pct_cobertura"]),
            "compraron_dia": compraron_dia_map.get(pcod, 0),
        }
        records.append(rec)
    # Por vendedor (sin desglose en portal, se mantiene para API externa)
    por_v = df[["vendedor_codigo", "vendedor_nombre", "segmento",
                "producto_codigo", "producto_nombre",
                "clientes_cartera", "clientes_compraron", "pct_cobertura"]].copy()
    por_v["vendedor_id"] = "V" + por_v["vendedor_codigo"].astype(int).astype(str)
    fecha = str(df["fecha_ejecucion"].iloc[0]) if "fecha_ejecucion" in df.columns else ""
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_ejecucion": fecha,
        "fuente": "mod_innovaciones_segmento.csv",
        "dia": dia_param or None,
        "por_producto": records,
        "por_vendedor": por_v[["vendedor_id", "vendedor_nombre", "segmento",
                                "producto_codigo", "producto_nombre",
                                "clientes_cartera", "clientes_compraron"]].to_dict("records"),
    })


# ====== PLANES AS — GERENCIA ======
@app.route("/api/gerencia/planes_as")
def gerencia_planes_as():
    df = read_csv(DATASETS / "mod_planes_as.csv")
    if df.empty:
        return jsonify({"error": "Sin datos"}), 404
    _num_cols = ["total_facturado", "dcto_plan", "cant_cajas", "tope", "escala_actual", "escala_max",
                 "sc_alaris", "sc_alma_mora", "sc_frizze", "sc_antares_ipa", "sc_smf_flavours",
                 "sc_total_ganado", "sc_cajas_enviadas_total", "sc_pendiente",
                 "sc_env_alaris", "sc_env_alma_mora", "sc_env_frizze", "sc_env_antares_ipa", "sc_env_smf_flavours",
                 "sc_pend_alaris", "sc_pend_alma_mora", "sc_pend_frizze", "sc_pend_antares_ipa", "sc_pend_smf_flavours"]
    for c in _num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Join con clientes.xlsx para obtener localidad y dia_visita
    _cli_info = {}   # cliente_id → {localidad, dia_visita}
    try:
        cli_path = INPUTS / "clientes.xlsx"
        if cli_path.exists():
            cli_xl = pd.read_excel(cli_path, usecols=lambda c: c.strip() in
                                   ("Codigo","Localidad","DiasVisita","Direccion"))
            cli_xl.columns = cli_xl.columns.str.strip()
            cli_xl["Codigo"] = pd.to_numeric(cli_xl["Codigo"], errors="coerce")
            for _, r in cli_xl.dropna(subset=["Codigo"]).iterrows():
                _cli_info[int(r["Codigo"])] = {
                    "localidad":   str(r.get("Localidad", "") or "").strip(),
                    "dia_visita":  str(r.get("DiasVisita", "") or "").strip(),
                }
    except Exception as e:
        print(f"[WARN] planes_as join clientes: {e}")

    def _int(v): return int(v) if pd.notna(v) else 0
    registros = []
    for _, row in df.iterrows():
        cid = int(row["cliente_id"]) if pd.notna(row["cliente_id"]) else None
        ci  = _cli_info.get(cid, {})
        registros.append({
            "cliente_id":      cid,
            "cliente_nombre":  str(row.get("cliente_nombre", "")),
            "localidad":       ci.get("localidad", ""),
            "dia_visita":      ci.get("dia_visita", ""),
            "vendedor_id":     f"V{int(row['vendedor_codigo'])}" if pd.notna(row.get("vendedor_codigo")) else None,
            "vendedor_nombre": str(row.get("vendedor_nombre", "")),
            "plan_as":         str(row.get("plan_as", "")),
            "escala_actual":   _int(row.get("escala_actual", 0)),
            "escala_max":      _int(row.get("escala_max", 0)),
            "total_facturado": round(float(row["total_facturado"]), 2),
            "dcto_plan":       round(float(row["dcto_plan"]), 2),
            "cant_cajas":      _int(row["cant_cajas"]),
            "tope":            _int(row["tope"]),
            "sc_alaris":       _int(row["sc_alaris"]),
            "sc_alma_mora":    _int(row["sc_alma_mora"]),
            "sc_frizze":       _int(row["sc_frizze"]),
            "sc_antares_ipa":  _int(row["sc_antares_ipa"]),
            "sc_smf_flavours": _int(row["sc_smf_flavours"]),
            "sc_total_ganado": _int(row["sc_total_ganado"]),
            "sc_env_alaris":   _int(row.get("sc_env_alaris", 0)),
            "sc_env_alma_mora":_int(row.get("sc_env_alma_mora", 0)),
            "sc_env_frizze":   _int(row.get("sc_env_frizze", 0)),
            "sc_env_antares_ipa": _int(row.get("sc_env_antares_ipa", 0)),
            "sc_env_smf_flavours": _int(row.get("sc_env_smf_flavours", 0)),
            "sc_pend_alaris":  _int(row.get("sc_pend_alaris", 0)),
            "sc_pend_alma_mora": _int(row.get("sc_pend_alma_mora", 0)),
            "sc_pend_frizze":  _int(row.get("sc_pend_frizze", 0)),
            "sc_pend_antares_ipa": _int(row.get("sc_pend_antares_ipa", 0)),
            "sc_pend_smf_flavours": _int(row.get("sc_pend_smf_flavours", 0)),
            "sc_enviadas_total": _int(row["sc_cajas_enviadas_total"]),
            "sc_pendiente":    _int(row["sc_pendiente"]),
        })
    fecha = str(df["fecha_calculo"].iloc[0]) if "fecha_calculo" in df.columns else ""
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_calculo": fecha,
        "fuente": "mod_planes_as.csv",
        "total_clientes": len(registros),
        "clientes": registros,
    })


# ====== ACCIONES VIGENTES (todos los roles) ======
@app.route("/api/acciones_vigentes")
def acciones_vigentes():
    """
    Acciones comerciales del mes con tramos de descuento y marcas.
    Lee el CSV de reglas (fuente de verdad) para devolver info completa al vendedor.
    Excluye PLAN_AS (tiene su propia pestaña).
    """
    # Buscar el CSV de reglas más reciente en 09_CONFIG/
    archivos = sorted(CONFIG.glob("reglas_acciones_*.csv"))
    if not archivos:
        return jsonify([])

    try:
        df = pd.read_csv(str(archivos[-1]), encoding="utf-8-sig")
    except Exception as e:
        print(f"[WARN] acciones_vigentes: {e}")
        return jsonify([])

    if df.empty:
        return jsonify([])

    # Excluir Plan AS: tiene pestaña propia
    if "tipo_accion" in df.columns:
        df = df[df["tipo_accion"] != "PLAN_AS"]

    grupos = {}
    orden  = []

    for _, row in df.iterrows():
        grupo = str(row.get("accion_grupo", "") or "").strip()
        if not grupo:
            continue

        if grupo not in grupos:
            lineas = str(row.get("lineas_segmentos", "") or "").strip()
            grupos[grupo] = {
                "accion_grupo":     grupo,
                "accion_nombre":    str(row.get("accion_nombre",    "") or "").strip(),
                "canal":            str(row.get("canal",            "") or "").strip(),
                "tipo_accion":      str(row.get("tipo_accion",      "") or "").strip(),
                "categoria":        str(row.get("categoria",        "") or "").strip(),
                "lineas_segmentos": lineas,
                "tramos":           [],
            }
            orden.append(grupo)

        # Construir tramo desde condicion_original
        condicion = str(row.get("condicion_original", "") or "").strip()
        if not condicion:
            continue

        dto_raw  = row.get("descuento_pct")
        cant_min = row.get("cantidad_min")
        cant_max = row.get("cantidad_max")
        bonif_e  = row.get("bonif_entrega_cajas")
        unidad   = str(row.get("unidad_condicion", "") or "").strip()

        grupos[grupo]["tramos"].append({
            "condicion":     condicion.replace("->", "→"),
            "descuento_pct": round(float(dto_raw) * 100, 1) if pd.notna(dto_raw) and dto_raw else None,
            "cant_min":      int(cant_min) if pd.notna(cant_min) else None,
            "cant_max":      int(cant_max) if pd.notna(cant_max) else None,
            "bonif_cajas":   int(bonif_e)  if pd.notna(bonif_e)  else None,
            "unidad":        unidad,
        })

    return jsonify([grupos[g] for g in orden])


# ====== PLANES AS — VENDEDOR ======
@app.route("/api/vendedor/<vid>/planes_as")
def vendedor_planes_as(vid):
    vid_norm = normalizar_vendedor_codigo(vid)
    if vid_norm in ("V2", "V5", "V20"):
        return jsonify({"error": "Vendedor no autorizado"}), 403
    try:
        cod = int(vid_norm.replace("V", ""))
    except Exception:
        return jsonify({"error": "ID inválido"}), 400
    df = read_csv(DATASETS / "mod_planes_as.csv")
    if df.empty:
        return jsonify({"clientes": []}), 200
    df["vendedor_codigo"] = pd.to_numeric(df["vendedor_codigo"], errors="coerce")
    df = df[df["vendedor_codigo"] == cod]
    _num = ["total_facturado", "dcto_plan", "cant_cajas", "tope", "escala_actual", "escala_max",
            "sc_alaris", "sc_alma_mora", "sc_frizze", "sc_antares_ipa", "sc_smf_flavours",
            "sc_total_ganado", "sc_cajas_enviadas_total", "sc_pendiente",
            "sc_env_alaris", "sc_env_alma_mora", "sc_env_frizze", "sc_env_antares_ipa", "sc_env_smf_flavours",
            "sc_pend_alaris", "sc_pend_alma_mora", "sc_pend_frizze", "sc_pend_antares_ipa", "sc_pend_smf_flavours"]
    for c in _num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    def _i(row, k): return int(row[k]) if k in row.index and pd.notna(row[k]) else 0
    registros = []
    for _, row in df.iterrows():
        registros.append({
            "cliente_id":      int(row["cliente_id"]) if pd.notna(row["cliente_id"]) else None,
            "cliente_nombre":  str(row.get("cliente_nombre", "")),
            "plan_as":         str(row.get("plan_as", "")),
            "total_facturado": round(float(row["total_facturado"]), 2),
            "dcto_plan":       round(float(row["dcto_plan"]), 2),
            "cant_cajas":      _i(row, "cant_cajas"),
            "tope":            _i(row, "tope"),
            "escala_actual":   _i(row, "escala_actual"),
            "escala_max":      _i(row, "escala_max"),
            "sc_alaris":       _i(row, "sc_alaris"),
            "sc_alma_mora":    _i(row, "sc_alma_mora"),
            "sc_frizze":       _i(row, "sc_frizze"),
            "sc_antares_ipa":  _i(row, "sc_antares_ipa"),
            "sc_smf_flavours": _i(row, "sc_smf_flavours"),
            "sc_total_ganado": _i(row, "sc_total_ganado"),
            "sc_enviadas_total": _i(row, "sc_cajas_enviadas_total"),
            "sc_pendiente":    _i(row, "sc_pendiente"),
            # por producto: enviados y pendientes
            "sc_env_alaris":       _i(row, "sc_env_alaris"),
            "sc_env_alma_mora":    _i(row, "sc_env_alma_mora"),
            "sc_env_frizze":       _i(row, "sc_env_frizze"),
            "sc_env_antares_ipa":  _i(row, "sc_env_antares_ipa"),
            "sc_env_smf_flavours": _i(row, "sc_env_smf_flavours"),
            "sc_pend_alaris":      _i(row, "sc_pend_alaris"),
            "sc_pend_alma_mora":   _i(row, "sc_pend_alma_mora"),
            "sc_pend_frizze":      _i(row, "sc_pend_frizze"),
            "sc_pend_antares_ipa": _i(row, "sc_pend_antares_ipa"),
            "sc_pend_smf_flavours":_i(row, "sc_pend_smf_flavours"),
        })
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vendedor_id": vid_norm,
        "fuente": "mod_planes_as.csv",
        "total_clientes": len(registros),
        "clientes": registros,
    })


# ====== SELLOUT POR CATEGORÍA ======
# REGLA FIJA: Sellout usa ventas.csv (período comercial actual).
# NO cambiar a ventas_acumulada.csv. Validado por usuario 2026-05-23.
@app.route("/api/gerencia/sellout_categoria")
def gerencia_sellout_categoria():
    df = read_csv(DATASETS / "mod_sellout_categoria.csv")
    if df.empty:
        return jsonify({"error": "Sin datos"}), 404
    df.columns = [c.lstrip("﻿") for c in df.columns]
    for c in ["litros", "cajas", "importe", "clientes"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    fecha = str(df["fecha_calculo"].iloc[0]) if "fecha_calculo" in df.columns and len(df) else ""

    por_cat = {}
    for cat, grp in df.groupby("Categoria"):
        segs = []
        for _, row in grp.iterrows():
            segs.append({
                "segmento":  str(row.get("Segmento", "")),
                "litros":    round(float(row["litros"]), 1),
                "cajas":     int(row["cajas"]),
                "importe":   int(row["importe"]),
                "clientes":  int(row["clientes"]),
            })
        segs.sort(key=lambda x: x["litros"], reverse=True)
        por_cat[cat] = {
            "categoria":    cat,
            "litros_total": round(float(grp["litros"].sum()), 1),
            "cajas_total":  int(grp["cajas"].sum()),
            "clientes":     int(grp["clientes"].sum()),
            "por_segmento": segs,
        }
    categorias = sorted(por_cat.values(), key=lambda x: x["litros_total"], reverse=True)
    return jsonify({
        "generado_en":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fuente":        "mod_sellout_categoria.csv",
        "fecha_calculo": fecha,
        "por_categoria": categorias,
    })


# ====== SELLOUT EN LITROS CON OBJETIVOS ======
import re as _re

def _infer_litros_por_nombre(nombre: str) -> float:
    """Fallback nivel 2: infiere litros/unidad desde el nombre del artículo.
    Busca el último grupo de 3-4 dígitos precedido por X o espacio (ej: 6X750 → 0.75).
    """
    matches = _re.findall(r'[X\s](\d{3,4})\b', str(nombre).upper())
    if matches:
        ml = int(matches[-1])
        if 100 <= ml <= 9999:
            return ml / 1000.0
    return 0.0


@app.route("/api/gerencia/sellout_litros")
def gerencia_sellout_litros():
    """
    Sellout acumulado en litros vs objetivos del mes por categoría.
    Fuente: 01_INPUTS/ventas.csv (período comercial vigente)
    Litros: PesoKg del CSV (precomputado).
      Fallback 1: PesoKg=0 → CantBase × LitrosXunidad de producto activos.xlsx
      Fallback 2: sin match en maestro → infiere ml del nombre del artículo
    Excluye V2, V5, V20. Solo ImporteNetoItem > 0.
    Objetivos hardcoded de obj sell out.jpeg.
    """
    _EXCL = {2, 5, 20}

    # Objetivos en litros — fuente: obj sell out.jpeg
    OBJ = {
        "VINOS DEL AÑO":    {"total": 19015, "sub": {"Alto": 11792, "Medio": 401, "Medio Alto": 4651, "Superior": 2171}},
        "VINOS DE GUARDA":  {"total": 678,   "sub": {}},
        "SPIRITS":          {"total": 17752,  "sub": {"Importados": 707, "Nacionales": 17045}},
        "RTD":              {"total": 9999,   "sub": {}},
        "CHAMPAÑA":         {"total": 686,    "sub": {}},
        "CERVEZA ARTESANAL":{"total": 405,    "sub": {}},
    }

    RUBRO_CAT = {
        "Vinos del Año":    "VINOS DEL AÑO",
        "Vino de Guarda":   "VINOS DE GUARDA",
        "Espumantes":       "CHAMPAÑA",
        "CERVEZA ARTESANAL":"CERVEZA ARTESANAL",
        "RTD (S)":          "RTD",
        "Whisky":           "SPIRITS",
        "Gin":              "SPIRITS",
        "Ron":              "SPIRITS",
        "Whisky (Maltas)":  "SPIRITS",
        "Vodka":            "SPIRITS",
        "Licores":          "SPIRITS",
    }
    SPIRITS_IMP = {"Whisky", "Gin", "Ron", "Whisky (Maltas)"}
    SPIRITS_NAC = {"Vodka", "Licores"}

    # — Leer ventas.csv —
    src = INPUTS / "ventas.csv"
    if not src.exists():
        return jsonify({"error": "ventas.csv no encontrado en 01_INPUTS"}), 404

    df = None
    for enc in ("utf-8-sig", "latin-1", "windows-1252"):
        try:
            df = pd.read_csv(src, sep=None, engine="python", encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        return jsonify({"error": "No se pudo leer ventas.csv"}), 500

    df.columns = [c.strip() for c in df.columns]

    for col in ("PesoKg", "CantBase", "ImporteNetoItem", "CodVendedor"):
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = (df[col].astype(str).str.replace(",", ".", regex=False)
                           .apply(pd.to_numeric, errors="coerce").fillna(0))
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0.0

    df = df[~df["CodVendedor"].isin(_EXCL)]
    df = df[df["ImporteNetoItem"] > 0]

    # — Fallback 1: maestro de productos para PesoKg=0 —
    prod_src = INPUTS / "producto activos.xlsx"
    cod2lxu = {}
    if prod_src.exists():
        try:
            prod = pd.read_excel(prod_src, header=3)
            prod.columns = [c.strip() for c in prod.columns]
            # Buscar columnas por posición si los nombres tienen tildes
            col_cod = next((c for c in prod.columns if "d" in c.lower() and "art" in c.lower()), None)
            col_lxu = next((c for c in prod.columns if "litro" in c.lower() and "unidad" in c.lower()), None)
            if col_cod and col_lxu:
                prod["_cod"] = prod[col_cod].astype(str).str.strip().str.upper()
                prod["_lxu"] = pd.to_numeric(prod[col_lxu], errors="coerce").fillna(0)
                cod2lxu = prod.set_index("_cod")["_lxu"].to_dict()
        except Exception:
            pass

    df["_cod"] = df["Codigo"].astype(str).str.strip().str.upper() if "Codigo" in df.columns else ""

    mask0 = df["PesoKg"] == 0
    if mask0.any() and cod2lxu:
        df["_lxu_fb"] = df["_cod"].map(cod2lxu).fillna(0)
        # Fallback 2: infiere del nombre del artículo donde no hubo match
        still_zero = mask0 & (df["_lxu_fb"] == 0)
        if still_zero.any() and "Articulo" in df.columns:
            df.loc[still_zero, "_lxu_fb"] = df.loc[still_zero, "Articulo"].apply(_infer_litros_por_nombre)
        df.loc[mask0, "PesoKg"] = df.loc[mask0, "CantBase"] * df.loc[mask0, "_lxu_fb"]

    # — Categoría display: usa Categoria del maestro como fuente primaria —
    # Fija errores de clasificación donde el Rubro en ventas.csv difiere del maestro
    # Ej: LOS ARBOLES / TRAPICHE ALARIS están en Rubro=Vino de Guarda pero maestro=Vinos del año
    CAT_MAESTRO_DISP = {
        "Vinos del año":    "VINOS DEL AÑO",
        "Vinos de guarda":  "VINOS DE GUARDA",
        "Espumantes":       "CHAMPAÑA",
        "Cerveza Artesanal":"CERVEZA ARTESANAL",
        "RTD (S)":          "RTD",
        "RTD":              "RTD",
        "Whisky":           "SPIRITS",
        "Gin":              "SPIRITS",
        "Ron":              "SPIRITS",
        "Licores":          "SPIRITS",
        "Vodka":            "SPIRITS",
        "Whisky (Maltas)":  "SPIRITS",
    }
    # Join con maestro para traer Categoria
    if prod_src.exists() and cod2lxu:
        try:
            prod_cat = pd.read_excel(prod_src, header=3)
            prod_cat.columns = [c.strip() for c in prod_cat.columns]
            col_cod2 = next((c for c in prod_cat.columns if "d" in c.lower() and "art" in c.lower()), None)
            col_cat  = next((c for c in prod_cat.columns if c.strip().lower() == "categoria"), None)
            if col_cod2 and col_cat:
                prod_cat["_cod"] = prod_cat[col_cod2].astype(str).str.strip().str.upper()
                cod2cat = prod_cat.set_index("_cod")[col_cat].to_dict()
                df["_cat_maestro"] = df["_cod"].map(cod2cat)
                df["_cat"] = df["_cat_maestro"].map(CAT_MAESTRO_DISP)
        except Exception:
            df["_cat"] = None
    # Fallback: si no hubo match en maestro, usar Rubro
    no_cat = df["_cat"].isna()
    df.loc[no_cat, "_cat"] = df.loc[no_cat, "Rubro"].astype(str).str.strip().map(RUBRO_CAT)

    df["_rub"] = df["Rubro"].astype(str).str.strip()
    df["_lin"] = df["Linea"].astype(str).str.strip() if "Linea" in df.columns else ""

    resultado = []
    for cat, obj_info in OBJ.items():
        grp = df[df["_cat"] == cat]
        litros   = round(float(grp["PesoKg"].sum()), 1)
        clientes = int(grp["Cliente"].nunique()) if "Cliente" in grp.columns else 0
        objetivo = obj_info["total"]
        alcance  = round(litros / objetivo * 100, 1) if objetivo > 0 else 0.0

        subs = []
        if cat == "VINOS DEL AÑO":
            for sn, so in obj_info["sub"].items():
                sg = grp[grp["_lin"].str.lower() == sn.lower()]
                sl = round(float(sg["PesoKg"].sum()), 1)
                sc = int(sg["Cliente"].nunique()) if "Cliente" in sg.columns else 0
                sa = round(sl / so * 100, 1) if so > 0 else 0.0
                subs.append({"nombre": sn, "litros": sl, "objetivo": so, "alcance_pct": sa, "clientes": sc})
        elif cat == "SPIRITS":
            # Importados = Premium (S) + Super Premium (S) — regla Diageo Argentina
            # Nacionales = Standard (S) (Smirnoff, JW Red, White Horse, Gordon's Standard, etc.)
            _lin_imp = {"Premium (S)", "Super Premium (S)"}
            mask_imp = grp["_lin"].isin(_lin_imp)
            for sn, mask_s, so in [
                ("Importados", mask_imp,  obj_info["sub"]["Importados"]),
                ("Nacionales", ~mask_imp, obj_info["sub"]["Nacionales"]),
            ]:
                sg = grp[mask_s]
                sl = round(float(sg["PesoKg"].sum()), 1)
                sc = int(sg["Cliente"].nunique()) if "Cliente" in sg.columns else 0
                sa = round(sl / so * 100, 1) if so > 0 else 0.0
                subs.append({"nombre": sn, "litros": sl, "objetivo": so, "alcance_pct": sa, "clientes": sc})

        resultado.append({
            "categoria":     cat,
            "litros":        litros,
            "objetivo":      objetivo,
            "alcance_pct":   alcance,
            "clientes":      clientes,
            "subcategorias": subs,
        })

    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fuente":      "ventas.csv · 01_INPUTS (con fallback maestro productos)",
        "categorias":  resultado,
    })


# ====== ACCIONES COMERCIALES RANKING ======
@app.route("/api/gerencia/acciones_ranking")
def gerencia_acciones_ranking():
    """
    Detalle de acciones comerciales del mes, enriquecido con análisis comparativo
    vs mes anterior (clientes nuevos en categoría, delta litros, costo de activación).
    Lee mod_acciones_ranking.csv (detalle) + mod_acciones_analisis.csv (análisis).
    """
    df = read_csv(DATASETS / "mod_acciones_ranking.csv")
    if df.empty:
        return jsonify({"error": "Sin datos"}), 404
    df.columns = [c.strip() for c in df.columns]

    num_cols_det = ["litros_vendidos", "cajas_vendidas", "inversion_pesos",
                    "importe_neto", "clientes_afectados"]
    for c in num_cols_det:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    fecha = str(df["fecha_calculo"].iloc[0]) if "fecha_calculo" in df.columns and len(df) else ""

    # Cargar análisis histórico si existe
    df_an = read_csv(DATASETS / "mod_acciones_analisis.csv")
    analisis_map = {}
    if not df_an.empty:
        df_an.columns = [c.strip() for c in df_an.columns]
        num_cols_an = ["clientes_mes_actual", "clientes_cat_mes_ant", "clientes_nuevos_cat",
                       "clientes_retorno", "pct_clientes_nuevos", "litros_mes_actual",
                       "litros_mes_anterior", "delta_litros_pct", "inversion_pesos",
                       "costo_activacion"]
        for c in num_cols_an:
            if c in df_an.columns:
                df_an[c] = pd.to_numeric(df_an[c], errors="coerce").fillna(0)
        for _, row in df_an.iterrows():
            g = str(row.get("accion_grupo", "")).strip()
            if g:
                analisis_map[g] = {
                    "clientes_nuevos_cat":   int(row.get("clientes_nuevos_cat", 0)),
                    "clientes_retorno":      int(row.get("clientes_retorno", 0)),
                    "clientes_cat_mes_ant":  int(row.get("clientes_cat_mes_ant", 0)),
                    "pct_clientes_nuevos":   round(float(row.get("pct_clientes_nuevos", 0)), 1),
                    "litros_mes_actual":     round(float(row.get("litros_mes_actual", 0)), 1),
                    "litros_mes_anterior":   round(float(row.get("litros_mes_anterior", 0)), 1),
                    "delta_litros_pct":      round(float(row.get("delta_litros_pct", 0)), 1),
                    "costo_activacion":      int(row.get("costo_activacion", 0)),
                    "mes_anterior":          str(row.get("mes_anterior", "")),
                }

    acciones = []
    for _, row in df.iterrows():
        grupo  = str(row.get("accion_grupo", "")).strip()
        nombre = str(row.get("accion_nombre", row.get("canal", ""))).strip()
        an     = analisis_map.get(grupo, {})
        # Cap delta_litros a ±9999% para evitar valores sin sentido (ej: Termidor vs 0 litros)
        delta_l = an.get("delta_litros_pct", 0)
        if abs(delta_l) > 9999:
            delta_l = None
        acciones.append({
            "accion_grupo":         grupo,
            "accion_nombre":        nombre,
            "tipo_accion":          str(row.get("tipo_accion", "")),
            "canal":                str(row.get("canal", "")),
            "categoria":            str(row.get("categoria", "")),
            "descuento_display":    str(row.get("descuento_display", "")),
            "litros_vendidos":      round(float(row["litros_vendidos"]), 1),
            "cajas_vendidas":       int(row["cajas_vendidas"]),
            "inversion_pesos":      int(row["inversion_pesos"]),
            "importe_neto":         int(row["importe_neto"]),
            "clientes_afectados":   int(row["clientes_afectados"]),
            # análisis comparativo
            "clientes_nuevos_cat":  an.get("clientes_nuevos_cat"),
            "clientes_retorno":     an.get("clientes_retorno"),
            "clientes_cat_mes_ant": an.get("clientes_cat_mes_ant"),
            "pct_clientes_nuevos":  an.get("pct_clientes_nuevos"),
            "litros_mes_anterior":  an.get("litros_mes_anterior"),
            "delta_litros_pct":     delta_l,
            "costo_activacion":     an.get("costo_activacion"),
            "mes_anterior":         an.get("mes_anterior", ""),
        })
    acciones.sort(key=lambda x: x["inversion_pesos"], reverse=True)
    return jsonify({
        "generado_en":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fuente":        "mod_acciones_ranking.csv + mod_acciones_analisis.csv",
        "fecha_calculo": fecha,
        "acciones":      acciones,
    })


# ====== ALERTAS CAÍDA: clientes dormidos ======
@app.route("/api/gerencia/alertas_caida")
def gerencia_alertas_caida():
    """Clientes que compraron en período anterior pero NO en el período actual.
    Período anterior: fechas en historial_ventas_cliente.csv antes del inicio de ventas.csv.
    Período actual: ventas.csv (ImporteNetoItem > 0).
    Excluye V2, V5, V20.
    """
    EXCLUIR = [2, 5, 20]
    HIST_PATH = BASE / "02_HISTORY" / "historial_ventas_cliente.csv"
    VTAS_PATH = INPUTS / "ventas.csv"

    if not HIST_PATH.exists() or not VTAS_PATH.exists():
        return jsonify({"error": "Fuente no disponible"}), 404

    try:
        hc = pd.read_csv(HIST_PATH, encoding="utf-8-sig", sep=None, engine="python")
        hc["fecha"] = pd.to_datetime(hc["fecha_comprobante"], errors="coerce")
        hc = hc[~hc["vendedor_codigo"].isin(EXCLUIR) & hc["importe_neto"].notna()].copy()
        hc = hc[hc["importe_neto"] > 0]

        v = pd.read_csv(VTAS_PATH, encoding="latin1", sep=";", engine="python")
        v["fecha"] = pd.to_datetime(v["FechaComprobante"], dayfirst=True, errors="coerce")
        v["importe"] = pd.to_numeric(
            v["ImporteNetoItem"].astype(str).str.replace(",", ".", regex=False), errors="coerce"
        )
        v = v[~v["CodVendedor"].isin(EXCLUIR) & (v["importe"] > 0)]

        inicio_actual = v["fecha"].min()
        if pd.isna(inicio_actual):
            return jsonify({"error": "ventas.csv sin fechas válidas"}), 500

        # Período anterior: historial antes del inicio del período actual
        hc_prev = hc[hc["fecha"] < inicio_actual].copy()
        clientes_actuales = set(v["Cliente"].unique())

        dormidos_df = hc_prev[~hc_prev["cliente_id"].isin(clientes_actuales)]
        if dormidos_df.empty:
            return jsonify({
                "resumen": {"total_dormidos": 0, "importe_en_riesgo": 0},
                "por_vendedor": [], "detalle": []
            })

        hoy = pd.Timestamp.today().normalize()

        resumen_cli = (
            dormidos_df
            .groupby(["cliente_id", "cliente_nombre", "vendedor_codigo", "vendedor_nombre"])
            .agg(ultima_compra=("fecha", "max"), importe_anterior=("importe_neto", "sum"))
            .reset_index()
        )
        resumen_cli["dias_sin_compra"] = (hoy - resumen_cli["ultima_compra"]).dt.days
        resumen_cli["vendedor_codigo_str"] = "V" + resumen_cli["vendedor_codigo"].astype(str)
        resumen_cli = resumen_cli.sort_values("importe_anterior", ascending=False)

        # Resumen por vendedor
        por_vend = (
            resumen_cli.groupby(["vendedor_codigo_str", "vendedor_nombre"])
            .agg(dormidos=("cliente_id", "count"), importe_en_riesgo=("importe_anterior", "sum"))
            .reset_index()
            .rename(columns={"vendedor_codigo_str": "vendedor_codigo"})
            .sort_values("importe_en_riesgo", ascending=False)
        )
        top_por_vend = []
        for _, row in por_vend.iterrows():
            vc = row["vendedor_codigo"]
            top = resumen_cli[resumen_cli["vendedor_codigo_str"] == vc].head(5)
            top_por_vend.append({
                "vendedor_codigo": vc,
                "vendedor_nombre": row["vendedor_nombre"],
                "dormidos": int(row["dormidos"]),
                "importe_en_riesgo": round(float(row["importe_en_riesgo"]), 0),
                "top_clientes": [
                    {
                        "cliente_id": int(r["cliente_id"]),
                        "cliente_nombre": r["cliente_nombre"],
                        "ultima_compra": r["ultima_compra"].strftime("%Y-%m-%d"),
                        "importe_anterior": round(float(r["importe_anterior"]), 0),
                        "dias_sin_compra": int(r["dias_sin_compra"]),
                    }
                    for _, r in top.iterrows()
                ],
            })

        detalle = [
            {
                "cliente_id": int(r["cliente_id"]),
                "cliente_nombre": r["cliente_nombre"],
                "vendedor_codigo": r["vendedor_codigo_str"],
                "vendedor_nombre": r["vendedor_nombre"],
                "ultima_compra": r["ultima_compra"].strftime("%Y-%m-%d"),
                "importe_anterior": round(float(r["importe_anterior"]), 0),
                "dias_sin_compra": int(r["dias_sin_compra"]),
            }
            for _, r in resumen_cli.iterrows()
        ]

        total_riesgo = float(resumen_cli["importe_anterior"].sum())
        return jsonify({
            "resumen": {
                "total_dormidos": len(resumen_cli),
                "importe_en_riesgo": round(total_riesgo, 0),
                "inicio_periodo_actual": inicio_actual.strftime("%Y-%m-%d"),
                "fin_periodo_actual": v["fecha"].max().strftime("%Y-%m-%d"),
                "fuente_historial": "historial_ventas_cliente.csv",
                "fuente_actual": "ventas.csv",
            },
            "por_vendedor": top_por_vend,
            "detalle": detalle,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ====== STARTUP (gunicorn + __main__) ======
# Se ejecuta cuando gunicorn importa el módulo, no solo en __main__
init_db()

if __name__ == "__main__":
    print("\n===== ORBIT SERVER v3 =====")
    print("Diagnóstico: http://localhost:8502/api/diagnostico")
    print("Dashboard:   http://localhost:8502/api/dashboard")
    print("Portal:      http://localhost:8502/index.html")
    print("===============================\n")
    port = int(os.environ.get("PORT", 8502))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)