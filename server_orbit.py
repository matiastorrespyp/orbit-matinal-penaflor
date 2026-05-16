"""
ORBIT Server v3 — Flask API con diagnóstico, CCC real, 11T real, sin mock
"""
from flask import Flask, jsonify, request, send_from_directory
import json, sqlite3, pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__, static_folder=None)
BASE = Path(r"C:\Orbit\MATINAL_PENAFLOR")
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
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

_VENDEDORES_EXCLUIDOS = {2, 5}

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

# ====== STATIC ======
@app.route("/")
@app.route("/<path:filename>")
def frontend(filename="index.html"):
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
    botellas_mes = None  # clientes_dia es solo zona Vi; omitir para evitar botellas_dia > botellas_mes

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
    vol     = read_csv(DATASETS / "mod_volumen_vendedor.csv")
    vend    = read_csv(CONFIG  / "vendedores_activos.csv")
    ccc_df  = read_csv(DATASETS / "mod_ccc_segmento.csv")   # CCC día (ayer)
    t11_df  = read_csv(DATASETS / "mod_11_titulares.csv")

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
        tendencia_pct = round((acum / _corridos) * _total / obj * 100, 2) if obj else 0
        cli_total = int(vv["clientes_planificados"].sum()) if not vv.empty and "clientes_planificados" in vv.columns else 0
        cli_sin = int(vv["clientes_sin_compra_mes"].sum()) if not vv.empty and "clientes_sin_compra_mes" in vv.columns else 0

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
                "alertas_criticas": 0, "oportunidades": 0,
                "inversion_desc_ars": 0.0, "sin_cargo_ars": 0.0,
                "impacto_alertas_ars": 0.0, "venta_mes_anterior": 0.0,
                "trabaja_autoservicio": cod.upper() != "V3"
            }
        })
    return jsonify(result)

# ====== CLIENTES, ALERTAS ======
@app.route("/api/clientes")
def clientes():
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
    return jsonify(df.where(pd.notnull(df), None).to_dict(orient="records"))

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
    vid = request.args.get("vendedor_id")
    conn = sqlite3.connect(str(DB_PATH)); conn.row_factory = sqlite3.Row
    if request.method == "POST":
        d = request.get_json()
        conn.execute("""INSERT INTO planificacion (fecha,vendedor_id,zona,dia_visita,venta_esperada,
            ccc_tradicional,ccc_autoservicio,ccc_onpremise,once_t,marcas,clientes_clave,acciones)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d.get("fecha",datetime.now().strftime("%Y-%m-%d")), d.get("vendedor_id"), d.get("zona"),
             d.get("dia_visita"), d.get("venta_esperada"), d.get("ccc_tradicional"),
             d.get("ccc_autoservicio"), d.get("ccc_onpremise"), d.get("once_t"),
             d.get("marcas"), d.get("clientes_clave"), d.get("acciones")))
        conn.commit(); conn.close()
        return jsonify({"ok":True})
    if vid:
        rows = conn.execute("SELECT * FROM planificacion WHERE vendedor_id=? ORDER BY fecha DESC", (vid,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM planificacion ORDER BY fecha DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

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

# ====== MAIN ======
if __name__ == "__main__":
    init_db()
    print("\n===== ORBIT SERVER v3 =====")
    print("Diagnóstico: http://localhost:8502/api/diagnostico")
    print("Dashboard:   http://localhost:8502/api/dashboard")
    print("Portal:      http://localhost:8502/index.html")
    print("===============================\n")
    app.run(host="0.0.0.0", port=8502, debug=True)