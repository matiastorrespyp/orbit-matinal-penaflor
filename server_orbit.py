"""
ORBIT Server v3 — Flask API con diagnóstico, CCC real, 11T real, sin mock
"""
from flask import Flask, jsonify, request, send_from_directory, make_response
import json, sqlite3, pandas as pd, math
from pathlib import Path
from datetime import datetime, timedelta, timezone

_ARG_TZ = timezone(timedelta(hours=-3))
def _now_ar():
    """Hora actual en Argentina (UTC-3) como string 'YYYY-MM-DD HH:MM:SS'."""
    return datetime.now(_ARG_TZ).strftime("%Y-%m-%d %H:%M:%S")

import os, shutil, csv as _csv
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
DB_PATH = Path(os.environ.get("ORBIT_DB_PATH", str(BASE / "orbit.db")))
if DB_PATH.parent != BASE:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
PLAN_BACKUP_DIR = Path(os.environ.get(
    "ORBIT_PLAN_BACKUP_DIR",
    str((BASE / "99_BACKUPS_ORBIT" / "planificacion") if DB_PATH.parent == BASE else (DB_PATH.parent / "planificacion"))
))
PLAN_CSV_LATEST = PLAN_BACKUP_DIR / "planificacion_latest.csv"

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
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    repo_db = BASE / "orbit.db"
    if DB_PATH != repo_db and not DB_PATH.exists() and repo_db.exists():
        try:
            shutil.copy2(str(repo_db), str(DB_PATH))
            print(f"[ORBIT] Seed DB persistente desde repo -> {DB_PATH}")
        except Exception as e:
            print(f"[WARN] seed orbit.db persistente: {e}")
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

def backup_orbit_db():
    """Copia orbit.db con timestamp antes de cada arranque del servidor."""
    if not DB_PATH.exists():
        return
    try:
        PLAN_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = PLAN_BACKUP_DIR / f"orbit_{ts}.db"
        shutil.copy2(str(DB_PATH), str(dest))
        print(f"[ORBIT] Backup orbit.db -> {dest.name}")
    except Exception as e:
        print(f"[WARN] backup_orbit_db: {e}")

def export_planificacion_csv():
    """Exporta la tabla planificacion a CSV de seguridad tras cada escritura."""
    try:
        PLAN_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM planificacion ORDER BY fecha, vendedor_id").fetchall()
        conn.close()
        if not rows:
            return
        cols = rows[0].keys()
        with open(str(PLAN_CSV_LATEST), "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows([dict(r) for r in rows])
        print(f"[ORBIT] Planificacion -> CSV seguridad ({len(rows)} registros)")
    except Exception as e:
        print(f"[WARN] export_planificacion_csv: {e}")

def restore_planificacion_if_empty():
    """Si planificacion está vacía y existe CSV de backup, restaura los datos automáticamente."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        count = conn.execute("SELECT COUNT(*) FROM planificacion").fetchone()[0]
        conn.close()
        if count > 0 or not PLAN_CSV_LATEST.exists():
            return
        with open(str(PLAN_CSV_LATEST), "r", encoding="utf-8") as f:
            rows = list(_csv.DictReader(f))
        if not rows:
            return
        conn = sqlite3.connect(str(DB_PATH))
        restored = 0
        for row in rows:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO planificacion
                      (id, fecha, vendedor_id, zona, dia_visita, venta_esperada,
                       ccc_tradicional, ccc_autoservicio, ccc_onpremise,
                       once_t, marcas, clientes_clave, acciones, estado,
                       editado_por, comentario_gerencia, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    row.get("id") or None,
                    row.get("fecha"), row.get("vendedor_id"),
                    row.get("zona") or None, row.get("dia_visita") or None,
                    float(row["venta_esperada"]) if row.get("venta_esperada") else None,
                    int(row["ccc_tradicional"]) if row.get("ccc_tradicional") else None,
                    int(row["ccc_autoservicio"]) if row.get("ccc_autoservicio") else None,
                    int(row["ccc_onpremise"]) if row.get("ccc_onpremise") else None,
                    int(row["once_t"]) if row.get("once_t") else None,
                    row.get("marcas") or None, row.get("clientes_clave") or None,
                    row.get("acciones") or None, row.get("estado") or "enviada",
                    row.get("editado_por") or None, row.get("comentario_gerencia") or None,
                    row.get("created_at") or None, row.get("updated_at") or None,
                ))
                restored += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        print(f"[ORBIT] AUTO-RESTORE: {restored} planes recuperados desde CSV de seguridad")
    except Exception as e:
        print(f"[WARN] restore_planificacion_if_empty: {e}")

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

def _feriados_config():
    path = CONFIG / "feriados.csv"
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path)
        col = "fecha" if "fecha" in df.columns else df.columns[0]
        fechas = pd.to_datetime(df[col], errors="coerce").dropna()
        return {d.date() for d in fechas}
    except Exception:
        return set()

def _es_dia_operativo(d):
    # Matinal Penaflor opera lunes a sabado; domingos y feriados no cuentan.
    return d.weekday() != 6 and d not in _feriados_config()

def _siguiente_dia_operativo(d):
    nxt = d + timedelta(days=1)
    while not _es_dia_operativo(nxt):
        nxt += timedelta(days=1)
    return nxt

def _fecha_planificacion_default(now=None):
    """Fecha objetivo para planes enviados por vendedores."""
    now = now or datetime.now(_ARG_TZ)
    hoy = now.date()
    if now.hour >= 12 or not _es_dia_operativo(hoy):
        return _siguiente_dia_operativo(hoy).isoformat()
    return hoy.isoformat()

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

def _cargar_ventas_dia(fecha_str: str = None):
    """
    Lee ventas.csv filtrado para UN día (fecha_str 'YYYY-MM-DD', o el día más reciente si None).
    Devuelve (DataFrame, fecha_usada_str).
    Columnas: cliente_id, vendedor_codigo, importe_neto, segmento_operativo.
    Excluye V2/V5/V20. Aplica regla V3 sin autoservicio en el resultado del llamador.
    """
    path = INPUTS / "ventas.csv"
    if not path.exists():
        return pd.DataFrame(), ""

    df = pd.DataFrame()
    for enc in ("latin1", "utf-8-sig", "utf-8"):
        try:
            df = pd.read_csv(path, sep=";", encoding=enc)
            break
        except Exception:
            continue

    if df.empty:
        return pd.DataFrame(), ""

    req = {"Cliente", "CodVendedor", "ImporteNetoItem", "FechaComprobante", "Ramo", "Subramo"}
    if not req.issubset(set(df.columns)):
        return pd.DataFrame(), ""

    df = df.copy()
    df["cliente_id"]         = pd.to_numeric(df["Cliente"], errors="coerce")
    df["vendedor_codigo"]    = pd.to_numeric(df["CodVendedor"], errors="coerce")
    df["importe_neto"]       = df["ImporteNetoItem"].apply(_parse_num_ar)
    df["fecha"]              = pd.to_datetime(df["FechaComprobante"], dayfirst=True, errors="coerce")
    df["segmento_operativo"] = df.apply(
        lambda r: _clasificar_segmento(str(r.get("Ramo", "")), str(r.get("Subramo", ""))), axis=1
    )
    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
    df = df.dropna(subset=["cliente_id", "vendedor_codigo", "fecha"])
    df = df[df["importe_neto"] > 0]

    if fecha_str:
        target = pd.to_datetime(fecha_str).date()
    else:
        if df.empty:
            return pd.DataFrame(), ""
        target = df["fecha"].dt.date.max()

    df_dia = df[df["fecha"].dt.date == target].copy()
    fecha_usada = str(target)
    if df_dia.empty:
        return pd.DataFrame(), fecha_usada
    return df_dia[["cliente_id", "vendedor_codigo", "importe_neto", "segmento_operativo"]].copy(), fecha_usada

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
@app.route("/portal.html")
def portal_html():
    """Sirve portal.html sin ETag ni Last-Modified para evitar cache en móviles."""
    try:
        content = (FRONTEND / "portal.html").read_bytes()
        resp = make_response(content)
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    except Exception as e:
        return f"Error sirviendo portal: {e}", 500

@app.route("/<path:filename>")
def frontend(filename):
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

# ====== HEALTHCHECK (Render / UptimeRobot) ======
@app.route("/api/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "orbit-penaflor-pav", "healthcheck": True}), 200

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

    # dia_operativo y fecha_corte siempre en tiempo real (no del dataset estático)
    _DIAS_AR = {0:'LU', 1:'MA', 2:'MI', 3:'JU', 4:'VI', 5:'SA', 6:'DO'}
    _now_diag = datetime.now(_ARG_TZ)
    dia_op       = _DIAS_AR[_now_diag.weekday()]
    fecha_corte_rt = _now_diag.strftime("%Y-%m-%d")

    # fecha_datos = cuándo fue generado el último dataset (para transparencia)
    fecha_datos = fecha_corte_rt  # fallback: hoy
    fecha_obj_str = None
    modo_fecha = "SIN_DATOS"
    if not vol.empty:
        try:
            if "fecha_ejecucion" in vol.columns:
                fecha_datos = str(vol["fecha_ejecucion"].iloc[0])  # fecha del último regenerar
            if "fecha_objetivo" in vol.columns:
                fecha_obj_str = str(vol["fecha_objetivo"].iloc[0])
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
        "fecha_datos": fecha_datos,          # cuándo se regeneraron los datasets (puede ser de ayer)
        "fecha_corte": fecha_corte_rt,       # hoy real-time (siempre actualizado)
        "fecha_objetivo": fecha_obj_str,
        "fecha_matinal": fecha_corte_rt,     # hoy real-time
        "fecha_planificacion_default": _fecha_planificacion_default(_now_diag),
        "dia_operativo": dia_op,             # día actual real-time (LU/MA/MI/JU/VI/SA)
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

    # Corridos: usar última fecha con datos reales en ventas.csv, no datetime.now()
    # Si ventas.csv tiene datos hasta June 1 y hoy es June 2, corridos=1 (no 2)
    _fecha_corte_ventas = None
    try:
        _src_v = INPUTS / "ventas.csv"
        if _src_v.exists():
            _dv = _preparar_df_ventas(_src_v)
            if not _dv.empty and "FechaComprobante" in _dv.columns:
                _ultima = pd.to_datetime(_dv["FechaComprobante"], dayfirst=True, errors="coerce").max()
                if pd.notna(_ultima):
                    _fecha_corte_ventas = _ultima.to_pydatetime()
    except Exception:
        pass
    dias = contar_dias_habiles(fecha_corte=_fecha_corte_ventas)
    _corridos = max(dias["corridos"], 1)
    _total    = dias["total"]

    # Venta ayer live — desde ventas.csv (día más reciente), evita depender del CSV estático
    _ventas_dia_live, _ = _cargar_ventas_dia()
    _venta_ayer_live = {}
    if not _ventas_dia_live.empty:
        for _cv, _grp in _ventas_dia_live.groupby("vendedor_codigo"):
            _venta_ayer_live[int(_cv)] = round(float(_grp["importe_neto"].sum()), 2)

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

        cod_int = int(cn) if cn.isdigit() else 0

        # resultado.xlsx es la fuente primaria para obj/acum/avance
        # (se actualiza diariamente sin necesidad de regenerar el motor)
        # mod_volumen_vendedor.csv es el fallback si resultado.xlsx no tiene al vendedor
        sin_maestro = False
        if cn in resultado_fallback:
            fb = resultado_fallback[cn]
            obj  = fb["objetivo"]
            acum = fb["acumulado"]
            av   = fb["avance"]
        elif not vv.empty:
            obj  = float(vv["objetivo_mes"].sum())
            acum = float(vv["acumulado_mes"].sum())
            av   = float(vv["avance_pct"].mean())
        else:
            obj = acum = av = 0
            sin_maestro = True

        # venta_ayer live desde ventas.csv; fallback al CSV estático
        venta_ayer = _venta_ayer_live.get(cod_int, float(vv["venta_ayer"].sum()) if not vv.empty else 0)

        # tendencia_pct: recalcular siempre con acum/obj reales
        tendencia_pct = round((acum / _corridos) * _total / obj * 100, 2) if obj else 0
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
    limit_q = (request.args.get("limit") or "").strip().lower()
    conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    if request.method == "POST":
        d = request.get_json() or {}
        _ip = request.remote_addr or "?"
        _ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _log_line = f"{_ts} | IP={_ip} | payload={d}\n"
        try:
            with open(str(BASE / "99_LOGS_ORBIT" / "planificacion_post.log"), "a", encoding="utf-8") as _lf:
                _lf.write(_log_line)
        except Exception:
            pass
        print(f"[PLAN POST] {_log_line.strip()}")

        # Normalizar y validar vendedor_id
        vid_raw = normalizar_vendedor_codigo(d.get("vendedor_id",""))
        if vid_raw not in _VENDEDORES_ACTIVOS_PLAN:
            conn.close()
            return jsonify({"ok": False, "error": f"Vendedor {vid_raw} no autorizado"}), 400

        # Regla: V3 no trabaja autoservicio
        ccc_as = 0 if vid_raw == "V3" else int(d.get("ccc_autoservicio") or 0)
        fecha_raw = str(d.get("fecha") or "").strip().lower()
        fecha  = _fecha_planificacion_default() if fecha_raw in ("", "auto", "default") else d.get("fecha")
        _ts    = _now_ar()  # hora Argentina para ambos timestamps

        conn.execute("""
            INSERT INTO planificacion
              (fecha, vendedor_id, zona, dia_visita, venta_esperada,
               ccc_tradicional, ccc_autoservicio, ccc_onpremise,
               once_t, marcas, clientes_clave, acciones, estado, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'enviada',?,?)
            ON CONFLICT(fecha, vendedor_id) DO UPDATE SET
              zona=excluded.zona, dia_visita=excluded.dia_visita,
              venta_esperada=excluded.venta_esperada,
              ccc_tradicional=excluded.ccc_tradicional,
              ccc_autoservicio=excluded.ccc_autoservicio,
              ccc_onpremise=excluded.ccc_onpremise,
              once_t=excluded.once_t, marcas=excluded.marcas,
              clientes_clave=excluded.clientes_clave, acciones=excluded.acciones,
              estado='enviada', updated_at=excluded.updated_at""",
            (fecha, vid_raw, d.get("zona"), d.get("dia_visita"),
             float(d.get("venta_esperada") or 0),
             int(d.get("ccc_tradicional") or 0), ccc_as,
             int(d.get("ccc_onpremise") or 0), int(d.get("once_t") or 0),
             d.get("marcas"), d.get("clientes_clave"), d.get("acciones"),
             _ts, _ts))
        conn.commit(); conn.close()
        export_planificacion_csv()
        return jsonify({"ok": True, "vendedor_id": vid_raw, "fecha": fecha, "hora_envio": _ts})

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
        if limit_q == "all":
            rows = conn.execute(
                "SELECT * FROM planificacion ORDER BY fecha DESC, vendedor_id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM planificacion ORDER BY fecha DESC, vendedor_id LIMIT 500").fetchall()
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
    export_planificacion_csv()
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

# ====== MATINAL RESUMEN: plan vs real ======
@app.route("/api/matinal/resumen")
def matinal_resumen():
    """
    Compara plan vs real. El PLAN ancla la fecha (no ventas.csv).
    - fecha_plan = parámetro ?fecha, o la fecha más reciente con planes en orbit.db.
    - real = ventas de esa misma fecha en ventas.csv. Si no existe todavía → tiene_real=False.

    Flujo:
      Mañana matinal → muestra planes aprobados, real = '–' (ventas aún no actualizadas).
      Después del .bat → ventas.csv se actualiza → real aparece solo, sin tocar nada más.
      Planes del día siguiente → tienen otra fecha, no pisan estos.
    """
    fecha_param = request.args.get("fecha")
    modo = (request.args.get("modo") or "cierre").strip().lower()

    # PASO 1: Determinar fecha_plan desde orbit.db
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    if fecha_param:
        fecha_plan = fecha_param
    else:
        today_ar = _now_ar()[:10]
        # Ventana acotada: evita que un plan viejo de prueba ancle Plan vs Real indefinidamente.
        cutoff = (datetime.now(_ARG_TZ) - timedelta(days=10)).strftime("%Y-%m-%d")
        if modo in ("actual", "ultimo", "plan"):
            row = conn.execute(
                "SELECT fecha FROM planificacion WHERE fecha >= ? ORDER BY fecha DESC LIMIT 1",
                (cutoff,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT fecha FROM planificacion WHERE fecha < ? AND fecha >= ? ORDER BY fecha DESC LIMIT 1",
                (today_ar, cutoff)
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT fecha FROM planificacion WHERE fecha >= ? ORDER BY fecha DESC LIMIT 1",
                    (cutoff,)
                ).fetchone()
        fecha_plan = row["fecha"] if row else today_ar

    planes = {row["vendedor_id"]: dict(row)
              for row in conn.execute(
                  "SELECT * FROM planificacion WHERE fecha=?", (fecha_plan,)).fetchall()}
    conn.close()

    # PASO 2: Buscar real para esa misma fecha en ventas.csv (puede no existir aún)
    ventas_dia, fecha_real = _cargar_ventas_dia(fecha_plan)
    tiene_real = not ventas_dia.empty  # False = aún no se corrió el .bat con ese día

    # PASO 3: Calcular real_map solo si hay datos de ventas
    real_map = {}
    if tiene_real:
        for cod_v, grp in ventas_dia.groupby("vendedor_codigo"):
            cod_int = int(cod_v)
            ccc_t = int(grp[grp["segmento_operativo"] == "TRADICIONAL"]["cliente_id"].nunique())
            ccc_a = int(grp[grp["segmento_operativo"] == "AUTOSERVICIO"]["cliente_id"].nunique())
            ccc_o = int(grp[grp["segmento_operativo"] == "ON_PREMISE_VTK"]["cliente_id"].nunique())
            if cod_int == 3:
                ccc_a = 0
            real_map[cod_int] = {
                "venta":     round(float(grp["importe_neto"].sum()), 2),
                "ccc_trad":  ccc_t,
                "ccc_as":    ccc_a,
                "ccc_op":    ccc_o,
                "ccc_total": int(grp["cliente_id"].nunique()),
            }

    vend = read_csv(CONFIG / "vendedores_activos.csv")
    resultado = []
    if not vend.empty:
        for _, v in vend[vend["activo"] == 1].iterrows():
            cod     = str(v["codigo_vendedor"]).strip()
            cn      = clean_code(cod)
            nombre  = str(v["nombre_vendedor"]).strip()
            cod_int = int(cn) if cn.isdigit() else 0

            real       = real_map.get(cod_int, {})
            real_venta = float(real.get("venta") or 0)

            plan       = planes.get(cod, {})
            plan_venta = float(plan.get("venta_esperada") or 0)
            delta      = real_venta - plan_venta
            pct        = round(real_venta / plan_venta * 100, 1) if plan_venta else None

            resultado.append({
                "vendedor_id":      cod,
                "vendedor_nombre":  nombre,
                "fecha_plan":       fecha_plan,
                "fecha_real":       fecha_real,
                "plan_venta":       plan_venta,
                "real_ayer":        real_venta,
                "delta":            round(delta, 2),
                "pct_cumplimiento": pct,
                "plan_ccc_trad":    int(plan.get("ccc_tradicional") or 0),
                "plan_ccc_as":      int(plan.get("ccc_autoservicio") or 0),
                "plan_ccc_op":      int(plan.get("ccc_onpremise") or 0),
                "plan_once_t":      int(plan.get("once_t") or 0),
                "real_ccc_trad":    real.get("ccc_trad", 0),
                "real_ccc_as":      real.get("ccc_as", 0),
                "real_ccc_op":      real.get("ccc_op", 0),
                "real_ccc_total":   real.get("ccc_total", 0),
                "plan_acciones":    plan.get("acciones") or "",
                "plan_estado":      plan.get("estado") or "sin_plan",
                "plan_id":          plan.get("id"),
                "tiene_plan":       bool(plan),
                "tiene_real":       bool(real),
            })

    return jsonify({
        "fecha_plan":  fecha_plan,
        "fecha_real":  fecha_real or None,
        "tiene_real":  tiene_real,
        "modo":        modo,
        "fuente_real": "ventas.csv",
        "generado_en": _now_ar(),
        "resumen":     resultado,
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
    """Fallback: infiere litros/unidad desde el nombre (ej: 6X750 → 0.75)."""
    matches = _re.findall(r'[X\s](\d{3,4})\b', str(nombre).upper())
    if matches:
        ml = int(matches[-1])
        if 100 <= ml <= 9999:
            return ml / 1000.0
    return 0.0


def _cargar_maestro_04D():
    """
    Carga maestro de productos 04D. Prefiere CSV liviano (09_CONFIG/maestro_04D_productos.csv)
    sobre el xlsx original (19MB con imágenes, tarda ~40s). Fallback al xlsx si el CSV no existe.
    Devuelve cuatro dicts keyed por Código Art. (str, upper, sin .0):
      cod2cat   → Categoria
      cod2seg   → Segmento  (Nacional/Importados spirits; Alto/Medio Alto/Superior/Medio VDA)
      cod2lxu   → litros por unidad (Lts x caja / UxC)
      cod2linea → Linea Comercial (marca canónica)
    """
    cod2cat, cod2seg, cod2lxu, cod2linea = {}, {}, {}, {}
    csv_path  = CONFIG / "maestro_04D_productos.csv"
    xlsx_path = INPUTS / "04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx"

    try:
        if csv_path.exists():
            df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
            df.columns = [c.strip() for c in df.columns]
            df["_cod"] = df["Codigo"].astype(str).str.strip().str.upper().str.replace(r"\.0$", "", regex=True)
            lxc = pd.to_numeric(df.get("Lts x caja", pd.Series(dtype=float)), errors="coerce").fillna(0)
            uxc = pd.to_numeric(df.get("UxC", pd.Series(dtype=float)), errors="coerce").fillna(0)
            df["_lxu"] = (lxc / uxc).where(uxc > 0, 0.0)
        elif xlsx_path.exists():
            df = pd.read_excel(xlsx_path, header=3)
            df.columns = [c.strip() for c in df.columns]
            col_cod = next((c for c in df.columns if "dig" in c.lower() or ("c" in c.lower() and "art" in c.lower())), None)
            if not col_cod:
                return cod2cat, cod2seg, cod2lxu, cod2linea
            df["_cod"] = df[col_cod].astype(str).str.strip().str.upper().str.replace(r"\.0$", "", regex=True)
            lxc = pd.to_numeric(df["Lts x caja"] if "Lts x caja" in df.columns else pd.Series(dtype=float), errors="coerce").fillna(0)
            uxc = pd.to_numeric(df["UxC"] if "UxC" in df.columns else pd.Series(dtype=float), errors="coerce").fillna(0)
            df["_lxu"] = (lxc / uxc).where(uxc > 0, 0.0)
            if "Linea Comercial" not in df.columns:
                col_linea = next((c for c in df.columns if "linea" in c.lower() and "comercial" in c.lower()), None)
                if col_linea:
                    df = df.rename(columns={col_linea: "Linea Comercial"})
        else:
            return cod2cat, cod2seg, cod2lxu, cod2linea

        cod2cat   = df.set_index("_cod")["Categoria"].to_dict()
        cod2seg   = df.set_index("_cod")["Segmento"].to_dict()
        cod2lxu   = df.set_index("_cod")["_lxu"].to_dict()
        if "Linea Comercial" in df.columns:
            cod2linea = df.set_index("_cod")["Linea Comercial"].to_dict()
    except Exception:
        pass
    return cod2cat, cod2seg, cod2lxu, cod2linea


# Mapeo Categoria 04D → bucket sell out
_SO_CAT_MAP = {
    "vinos del año": "VINOS DEL AÑO",
    "vinos del a\xf1o": "VINOS DEL AÑO",
    "vinos de mesa": "VINOS DEL AÑO",
    "vinos de guarda": "VINOS DE GUARDA",
    "espumantes": "CHAMPAÑA",
    "sidra": "CHAMPAÑA",
    "cerveza artesanal": "CERVEZA ARTESANAL",
    "rtd (s)": "RTD",
    "rtd": "RTD",
    "whisky": "SPIRITS",
    "whisky (maltas)": "SPIRITS",
    "gin": "SPIRITS",
    "ron": "SPIRITS",
    "vodka": "SPIRITS",
    "licores": "SPIRITS",
    "bourbon": "SPIRITS",
}

# Mapeo Segmento 04D → tier sell out
_SO_SEG_VDA = {"Alto": "Alto", "Medio Alto": "Medio Alto", "Superior": "Superior", "Medio": "Medio", "Vinos de Mesa": "Medio"}
_SO_SEG_SPIRITS = {"Nacional": "Nacionales", "Importados": "Importados"}


def _sellout_desde_ventas(df_raw: pd.DataFrame) -> list:
    """
    Calcula sell out en litros por categoría desde un DataFrame de ventas ya filtrado
    (excl V2/V5/V20, importe > 0). Fuente de clasificación: 04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx.

    Litros por línea = CantBase × (Lts x caja / UxC) del maestro 04D.
    Fallback si sin match en maestro: PesoKg (ya en litros en el ERP).
    Fallback final: inferir ml del nombre del artículo.

    Spirits NO están en maestro 04D (son Diageo/P&P) → clasificar por keyword en Artículo:
      Nacional  = SMIRNOFF, GORDON, WHITE HORSE, J&B
      Importados = resto de spirits

    Devuelve lista de dicts con estructura:
      [{categoria, litros, objetivo, alcance_pct, clientes,
        subcategorias: [{nombre, litros, objetivo, alcance_pct, clientes,
                         marcas: [{marca, litros}]}]}]
    """
    OBJ = {
        "VINOS DEL AÑO":    {"total": 19015, "sub": {"Alto": 11792, "Medio Alto": 4651, "Superior": 2171, "Medio": 401}},
        "VINOS DE GUARDA":  {"total": 678,   "sub": {}},
        "SPIRITS":          {"total": 17752,  "sub": {"Nacionales": 17045, "Importados": 707}},
        "RTD":              {"total": 9999,   "sub": {}},
        "CHAMPAÑA":         {"total": 686,    "sub": {}},
        "CERVEZA ARTESANAL":{"total": 405,    "sub": {}},
    }
    _NAC_KW = ("SMIRNOFF", "GORDON", "WHITE HORSE", "J&B", "JYB")

    df = df_raw.copy()

    # ── Código artículo normalizado (strip + quitar ".0" de floats: "14605.0" → "14605")
    df["_cod"] = df["Codigo"].astype(str).str.strip().str.upper() if "Codigo" in df.columns else ""
    df["_cod"] = df["_cod"].str.replace(r"\.0$", "", regex=True)

    # ── Cargar maestro 04D (categoría, segmento, litros/unidad, linea comercial)
    cod2cat_04d, cod2seg_04d, cod2lxu_04d, cod2linea_04d = _cargar_maestro_04D()

    # ── Litros: CantBase × lxu maestro 04D (fuente primaria)
    #           → PesoKg si sin maestro  → inferir del nombre
    df["_lxu"] = df["_cod"].map(cod2lxu_04d).fillna(0)
    df["litros"] = df["CantBase"] * df["_lxu"]
    # Para productos sin lxu en maestro: usar PesoKg
    no_lxu = df["litros"] == 0
    if no_lxu.any():
        df.loc[no_lxu, "litros"] = df.loc[no_lxu, "PesoKg"]
    # Para productos con PesoKg=0 también: inferir del nombre
    still_zero = df["litros"] == 0
    if still_zero.any() and "Articulo" in df.columns:
        infer_l = df["Articulo"].apply(_infer_litros_por_nombre) * df["CantBase"]
        df["litros"] = df["litros"].where(~still_zero, infer_l)

    # ── Categoría: maestro 04D → fallback Rubro (where() para evitar loc parcial en pandas 3.x)
    cat_maestro = df["_cod"].map(cod2cat_04d).astype(object)
    cat_maestro_norm = cat_maestro.str.strip().str.lower().map(_SO_CAT_MAP) if cat_maestro.notna().any() else cat_maestro
    cat_rubro = df["Rubro"].astype(str).str.strip().str.lower().map(_SO_CAT_MAP) if "Rubro" in df.columns else pd.Series(None, index=df.index, dtype=object)
    df["_cat"] = cat_maestro_norm.where(cat_maestro_norm.notna(), cat_rubro)

    # ── Segmento VDA: maestro 04D
    df["_seg"] = df["_cod"].map(cod2seg_04d).astype(str).str.strip()

    # ── Linea Comercial (marca): maestro 04D → Linea de ventas.csv → Marca de ventas.csv
    # Usar where() para evitar asignación parcial sobre columna float64 (pandas 3.x)
    linea_maestro = df["_cod"].map(cod2linea_04d)
    # Fallback chain: maestro Linea Comercial > Linea ERP > Marca ERP
    if "Linea" in df.columns:
        fallback = df["Linea"].astype(str).str.strip()
    elif "Marca" in df.columns:
        fallback = df["Marca"].astype(str).str.strip()
    else:
        fallback = pd.Series("", index=df.index)
    df["_linea"] = linea_maestro.where(linea_maestro.notna(), fallback)
    df["_linea"] = df["_linea"].fillna("").astype(str).str.strip()

    resultado = []
    for cat, obj_info in OBJ.items():
        grp = df[df["_cat"] == cat]
        litros   = round(float(grp["litros"].sum()), 1)
        clientes = int(grp["Cliente"].nunique()) if "Cliente" in grp.columns else 0
        obj_total = obj_info["total"]
        alcance   = round(litros / obj_total * 100, 1) if obj_total else 0.0
        subs = []

        if cat == "VINOS DEL AÑO":
            for sn, so_v in obj_info["sub"].items():
                # Segmento del maestro 04D: Alto / Medio Alto / Superior / Medio
                sg = grp[grp["_seg"].map(_SO_SEG_VDA) == sn]
                sl = round(float(sg["litros"].sum()), 1)
                sc = int(sg["Cliente"].nunique()) if "Cliente" in sg.columns else 0
                marcas = _marcas_de_grupo(sg)
                subs.append({"nombre": sn, "litros": sl, "objetivo": so_v,
                             "alcance_pct": round(sl/so_v*100,1) if so_v else 0.0,
                             "clientes": sc, "marcas": marcas})

        elif cat == "SPIRITS":
            # Spirits NO están en maestro 04D → keyword por nombre de artículo
            _art = grp["Articulo"].astype(str).str.upper() if "Articulo" in grp.columns else pd.Series("", index=grp.index)
            mask_nac = _art.str.contains("|".join(_NAC_KW), na=False)
            for sn, mask_s, so_v in [("Nacionales", mask_nac, obj_info["sub"]["Nacionales"]),
                                      ("Importados", ~mask_nac, obj_info["sub"]["Importados"])]:
                sg = grp[mask_s]
                sl = round(float(sg["litros"].sum()), 1)
                sc = int(sg["Cliente"].nunique()) if "Cliente" in sg.columns else 0
                marcas = _marcas_de_grupo(sg)
                subs.append({"nombre": sn, "litros": sl, "objetivo": so_v,
                             "alcance_pct": round(sl/so_v*100,1) if so_v else 0.0,
                             "clientes": sc, "marcas": marcas})

        resultado.append({
            "categoria": cat, "litros": litros, "objetivo": obj_total,
            "alcance_pct": alcance, "clientes": clientes, "subcategorias": subs,
            "marcas": _marcas_de_grupo(grp),
        })
    return resultado


def _marcas_de_grupo(sg: pd.DataFrame) -> list:
    """Devuelve lista [{marca, litros}] ordenada desc. Usa _linea (Linea Comercial del maestro 04D); fallback Marca."""
    col = "_linea" if "_linea" in sg.columns else ("Marca" if "Marca" in sg.columns else None)
    if col is None:
        return []
    return [{"marca": str(mk), "litros": round(float(mv), 1)}
            for mk, mv in sg.groupby(col)["litros"].sum()
            .sort_values(ascending=False).items() if mv > 0 and str(mk).strip()]


def _preparar_df_ventas(src_path) -> pd.DataFrame:
    """Lee ventas.csv, parsea columnas numéricas, excluye V2/V5/V20, filtra importe > 0."""
    df = None
    for enc in ("utf-8-sig", "latin-1", "windows-1252"):
        try:
            df = pd.read_csv(src_path, sep=None, engine="python", encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        return pd.DataFrame()
    df.columns = [c.strip() for c in df.columns]
    for col in ("PesoKg", "CantBase", "ImporteNetoItem", "CodVendedor"):
        if col not in df.columns:
            df[col] = 0.0
        elif df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(",", ".", regex=False).pipe(pd.to_numeric, errors="coerce").fillna(0)
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df[~df["CodVendedor"].isin({2, 5, 20}) & (df["ImporteNetoItem"] > 0)].copy()
    return df


def _leer_ventas_mes_csv(src_path) -> pd.DataFrame:
    """Lee ventas_mes.csv con sep=',' y quotechar='"' explícitos.
    sep=None con engine='python' usa csv.Sniffer que falla en Linux con decimales europeos
    entre comillas (ej: "6620,94"), parseando mal ImporteNetoItem y filtrando casi todas las filas."""
    df = None
    for enc in ("utf-8-sig", "latin-1", "windows-1252"):
        try:
            df = pd.read_csv(src_path, sep=",", quotechar='"', encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        return pd.DataFrame()
    df.columns = [c.strip() for c in df.columns]
    for col in ("PesoKg", "CantBase", "ImporteNetoItem", "CodVendedor"):
        if col not in df.columns:
            df[col] = 0.0
        elif df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(",", ".", regex=False).pipe(pd.to_numeric, errors="coerce").fillna(0)
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df[~df["CodVendedor"].isin({2, 5, 20}) & (df["ImporteNetoItem"] > 0)].copy()
    return df



@app.route("/api/gerencia/sellout_litros")
def gerencia_sellout_litros():
    """Sellout en litros vs objetivos. Fuente: ventas.csv × maestro_04D_productos.csv."""
    src = INPUTS / "ventas.csv"
    if not src.exists():
        return jsonify({"error": "ventas.csv no encontrado en 01_INPUTS"}), 404
    df = _preparar_df_ventas(src)
    if df.empty:
        return jsonify({"error": "No se pudo leer ventas.csv"}), 500
    resultado = _sellout_desde_ventas(df)
    return jsonify({
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fuente":      "ventas.csv + maestro_04D_productos.csv",
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


# ====== CIERRE DE MES ======
@app.route("/api/gerencia/cierre_mes")
def gerencia_cierre_mes():
    """
    Resumen de cierre mensual por vendedor y empresa.
    ?mes=YYYY-MM  (default: mes anterior al actual)
    Fuente $:   resultado.xlsx hoja Avance
    Fuente CCC: ventas_acumulada.csv filtrado al mes
    """
    from calendar import monthrange

    MESES_ES = {
        1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
        7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"
    }

    hoy = datetime.now()
    mes_param = request.args.get("mes", "")
    if mes_param:
        try:
            año, mes = map(int, mes_param.split("-"))
        except Exception:
            return jsonify({"error": "Formato inválido. Use YYYY-MM"}), 400
    else:
        if hoy.month == 1:
            año, mes = hoy.year - 1, 12
        else:
            año, mes = hoy.year, hoy.month - 1

    ultimo_dia = monthrange(año, mes)[1]
    fecha_cierre = datetime(año, mes, ultimo_dia, 23, 59, 59)
    nombre_mes = f"{MESES_ES.get(mes, str(mes))} {año}"

    # Calendario del mes cerrado
    cal = contar_dias_habiles(fecha_corte=fecha_cierre)

    # Objetivos y acumulado desde resultado.xlsx (fuente primaria)
    obj_por_vend = {}
    resultado_path = INPUTS / "resultado.xlsx"
    if resultado_path.exists():
        try:
            avance_df = pd.read_excel(resultado_path, sheet_name="Avance")
            for _, r in avance_df.iterrows():
                cn = clean_code(str(r.get("VendedorCodigo", "")))
                if not cn or int(cn) in _VENDEDORES_EXCLUIDOS:
                    continue
                obj_por_vend[cn] = {
                    "nombre": str(r.get("VendedorNombre", "")).strip().title(),
                    "objetivo": float(r.get("ValorObjetivo", 0) or 0),
                    "acumulado": float(r.get("Acumulado", 0) or 0),
                }
        except Exception:
            pass

    # CCC desde ventas_acumulada.csv filtrado al mes cerrado
    ccc_por_vend = {}
    vac_path = INPUTS / "ventas_acumulada.csv"
    if vac_path.exists():
        try:
            vac = pd.read_csv(vac_path, sep=";", encoding="latin1")
            vac["fecha"]    = pd.to_datetime(vac["FechaComprobante"], dayfirst=True, errors="coerce")
            vac["importe"]  = vac["ImporteNetoItem"].apply(_parse_num_ar)
            vac["vend_cod"] = pd.to_numeric(vac["CodVendedor"], errors="coerce")
            mes_ini = datetime(año, mes, 1)
            # Filtrar solo ventas Peñaflor (Empresa='Empresa'), no P&P Logística
            empresa_ok = (vac["Empresa"] == "Empresa") if "Empresa" in vac.columns else pd.Series(True, index=vac.index)
            vac = vac[
                empresa_ok &
                (vac["fecha"] >= mes_ini) & (vac["fecha"] <= fecha_cierre) &
                (vac["importe"] > 0) & (~vac["vend_cod"].isin(_VENDEDORES_EXCLUIDOS))
            ].copy()
            vac["segmento"] = vac.apply(
                lambda r: _clasificar_segmento(str(r.get("Ramo", "")), str(r.get("Subramo", ""))), axis=1
            )
            for (vend_cod, seg), grp in vac.groupby(["vend_cod", "segmento"]):
                cn = clean_code(str(int(vend_cod)))
                if cn not in ccc_por_vend:
                    ccc_por_vend[cn] = {"TRADICIONAL": 0, "AUTOSERVICIO": 0, "ON_PREMISE_VTK": 0, "OTROS": 0}
                ccc_por_vend[cn][seg] = int(grp["Cliente"].nunique())
        except Exception:
            pass

    # Vendedores activos
    vend_df = read_csv(CONFIG / "vendedores_activos.csv")
    vend_activos = {}
    if not vend_df.empty:
        for _, v in vend_df[vend_df["activo"] == 1].iterrows():
            cn = clean_code(str(v["codigo_vendedor"]))
            if int(cn) not in _VENDEDORES_EXCLUIDOS:
                vend_activos[cn] = str(v["nombre_vendedor"]).strip()

    vendedores = []
    for cn, nombre_config in vend_activos.items():
        ob  = obj_por_vend.get(cn, {})
        ccc = ccc_por_vend.get(cn, {})

        objetivo   = ob.get("objetivo", 0)
        acumulado  = ob.get("acumulado", 0)
        avance_pct = round(acumulado / objetivo * 100, 2) if objetivo else 0
        nombre     = ob.get("nombre") or nombre_config

        ccc_trad  = ccc.get("TRADICIONAL", 0)
        ccc_auto  = 0 if cn == "3" else ccc.get("AUTOSERVICIO", 0)
        ccc_op    = ccc.get("ON_PREMISE_VTK", 0)
        ccc_total = ccc_trad + ccc_auto + ccc_op + ccc.get("OTROS", 0)

        vendedores.append({
            "codigo":           cn,
            "nombre":           nombre,
            "objetivo":         objetivo,
            "acumulado":        acumulado,
            "avance_pct":       avance_pct,
            "ccc_total":        ccc_total,
            "ccc_tradicional":  ccc_trad,
            "ccc_autoservicio": ccc_auto,
            "ccc_onpremise":    ccc_op,
        })

    vendedores.sort(key=lambda x: x["avance_pct"], reverse=True)

    empresa = {
        "objetivo":         sum(v["objetivo"]         for v in vendedores),
        "acumulado":        sum(v["acumulado"]         for v in vendedores),
        "ccc_total":        sum(v["ccc_total"]         for v in vendedores),
        "ccc_tradicional":  sum(v["ccc_tradicional"]  for v in vendedores),
        "ccc_autoservicio": sum(v["ccc_autoservicio"] for v in vendedores),
        "ccc_onpremise":    sum(v["ccc_onpremise"]    for v in vendedores),
    }
    empresa["avance_pct"] = round(
        empresa["acumulado"] / empresa["objetivo"] * 100, 2
    ) if empresa["objetivo"] else 0

    # ── 11 Titulares (totales empresa, sin apertura por vendedor) ──
    # ── 11 Titulares: CCC por marca vs objetivo CCC (mismo cálculo que /api/gerencia/once_titulares) ──
    # Fuente CCC: ventas_acumulada filtrado al mes cerrado
    # Fuente objetivo: objetivo 11T.xlsx
    once_titulares = {"marcas": [], "empresa": {}}
    try:
        _MARCA_LKP = {
            "ALMA MORA": "ALMA MORA", "ALARIS": "ALARIS", "TRAPICHE ALARIS": "ALARIS",
            "DON DAVID": "DON DAVID", "DADA": "DADA", "LOS ARBOLES": "LOS ARBOLES",
            "FINCA LAS MORAS": "FINCA LAS MORAS", "F LAS MORAS": "FINCA LAS MORAS",
            "TRAPICHE RESERVA": "TRAPICHE RESERVA",
            "FOND DE CAVE": "FOND DE CAVE", "FOND CAVE": "FOND DE CAVE",
            "CAZADOR": "CAZADOR", "ANTARES": "ANTARES",
            "GORDON'S FLAVOURS": "GORDON'S FLAVOURS", "GORDONS FLAVOURS": "GORDON'S FLAVOURS",
            "GORDONS": "GORDON'S FLAVOURS", "GORDON'S": "GORDON'S FLAVOURS",
            "SMIRNOFF": "SMIRNOFF FLAVOURS", "SMIRNOFF FLAVOURS": "SMIRNOFF FLAVOURS",
            "SMIRNOFF ICE": "SMIRNOFF ICE",
            "JW BLACK": "JW BLACK", "JW RED": "JW RED",
            "MASCOTA": "MASCOTA", "NC ESPUMANTES": "NC ESPUMANTES",
            "TRAPICHE MEDALLA": "TRAPICHE MEDALLA",
        }
        _ART_KW_11T = [
            ("SMIRNOFF ICE", "SMIRNOFF ICE"), ("SMF ICE", "SMIRNOFF ICE"),
            ("SMIRNOFF", "SMIRNOFF FLAVOURS"), ("GORDON", "GORDON'S FLAVOURS"),
            ("ANTARES", "ANTARES"), ("CAZADOR", "CAZADOR"),
            ("FOND DE CAVE", "FOND DE CAVE"), ("ALMA MORA", "ALMA MORA"),
            ("LOS ARBOLES", "LOS ARBOLES"), ("DADA", "DADA"),
            ("FINCA LAS MORAS", "FINCA LAS MORAS"), ("DON DAVID", "DON DAVID"),
            ("ALARIS", "ALARIS"), ("TRAPICHE RESERVA", "TRAPICHE RESERVA"),
            ("JW BLACK", "JW BLACK"), ("JW RED", "JW RED"),
        ]
        _OBJ_ALIAS_11T = {
            "ALMA MORA": "ALMA MORA", "TRAPICHE RESERVA": "TRAPICHE RESERVA",
            "FINCA LAS MORAS": "FINCA LAS MORAS", "FINCA LAS MORAS": "FINCA LAS MORAS",
            "ALARIS": "ALARIS", "DON DAVID": "DON DAVID", "DADA": "DADA",
            "SIMRNOFF FLAVORS": "SMIRNOFF FLAVOURS", "SMIRNOFF FLAVORS": "SMIRNOFF FLAVOURS",
            "SMIRNOFF FLAVOURS": "SMIRNOFF FLAVOURS",
            "LOS ARBOLES": "LOS ARBOLES", "ANTARES": "ANTARES",
            "SMIRNOFF ICE": "SMIRNOFF ICE", "SMF ICE": "SMIRNOFF ICE",
            "GORDONS FLAVOURS": "GORDON'S FLAVOURS", "GORDONS FLAVORS": "GORDON'S FLAVOURS",
            "GORDON'S FLAVOURS": "GORDON'S FLAVOURS",
        }

        # Objetivos desde objetivo 11T.xlsx
        obj_map_11t = {}
        try:
            obj_df = pd.read_excel(INPUTS / "objetivo 11T.xlsx", header=1)
            obj_df = obj_df.dropna(subset=obj_df.columns[1:2])
            for _, row in obj_df.iterrows():
                raw = str(row.iloc[1]).upper().strip()
                mk = _OBJ_ALIAS_11T.get(raw, raw)
                try:
                    obj_map_11t[mk] = int(float(row.iloc[2]))
                except (ValueError, TypeError):
                    pass
        except Exception:
            pass

        # CCC por marca desde ventas_acumulada COMPLETO (sin filtro de fecha)
        # — mismo criterio que el dashboard /api/gerencia/once_titulares
        ccc_map_11t = {}
        vac_path_11t = INPUTS / "ventas_acumulada.csv"
        if vac_path_11t.exists():
            try:
                vac11 = pd.read_csv(vac_path_11t, sep=";", encoding="latin1", low_memory=False)
                vac11["importe"] = pd.to_numeric(
                    vac11["ImporteNetoItem"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
                vac11 = vac11[
                    (~vac11["CodVendedor"].isin(_VENDEDORES_EXCLUIDOS)) &
                    (vac11["importe"] > 0)
                ]
                vac11["marca_objetivo"] = vac11["Marca"].astype(str).str.upper().str.strip().map(_MARCA_LKP)
                unresolved = vac11["marca_objetivo"].isna()
                if unresolved.any():
                    for kw, mo in _ART_KW_11T:
                        still = vac11["marca_objetivo"].isna()
                        if not still.any():
                            break
                        hits = vac11.loc[still, "Articulo"].astype(str).str.upper().str.contains(kw, regex=False, na=False)
                        vac11.loc[still & hits, "marca_objetivo"] = mo
                ccc_map_11t = (vac11[vac11["marca_objetivo"].notna()]
                               .groupby("marca_objetivo")["Cliente"].nunique().to_dict())
            except Exception:
                pass

        # Construir resultado — solo marcas con objetivo definido
        marcas_11t = []
        total_ccc = 0
        total_obj = 0
        for mk in sorted(obj_map_11t.keys(), key=lambda x: ccc_map_11t.get(x, 0), reverse=True):
            ccc_v = ccc_map_11t.get(mk, 0)
            obj_v = obj_map_11t[mk]
            pct   = round(ccc_v / obj_v * 100, 1) if obj_v else None
            marcas_11t.append({"marca": mk, "ccc": ccc_v, "objetivo": obj_v, "pct": pct})
            total_ccc += ccc_v
            total_obj += obj_v

        once_titulares["marcas"] = marcas_11t
        once_titulares["empresa"] = {
            "ccc_total": total_ccc,
            "objetivo_total": total_obj,
            "pct": round(total_ccc / total_obj * 100, 1) if total_obj else 0,
            "marcas_sobre_objetivo": sum(1 for m in marcas_11t if (m["pct"] or 0) >= 100),
            "total_marcas": len(marcas_11t),
        }
    except Exception:
        pass

    # ── Innovaciones (denominador = CCC Mes: clientes con compra en el mes) ──
    innovaciones = {"resumen": {}, "por_producto": []}
    try:
        innov = read_csv(DATASETS / "mod_innovaciones_segmento.csv")
        if not innov.empty:
            # CCC Mes: clientes únicos con compra en el mes cerrado (fuente ventas_acumulada sin filtro empresa)
            ccc_mes_total = 0
            vac_path2 = INPUTS / "ventas_acumulada.csv"
            if vac_path2.exists():
                try:
                    _v2 = pd.read_csv(vac_path2, sep=";", encoding="latin1",
                                      usecols=["FechaComprobante", "ImporteNetoItem", "CodVendedor", "Cliente"])
                    _v2["fecha"]   = pd.to_datetime(_v2["FechaComprobante"], dayfirst=True, errors="coerce")
                    _v2["importe"] = _v2["ImporteNetoItem"].apply(_parse_num_ar)
                    _v2["vend_c"]  = pd.to_numeric(_v2["CodVendedor"], errors="coerce")
                    _v2 = _v2[
                        (_v2["fecha"] >= datetime(año, mes, 1)) & (_v2["fecha"] <= fecha_cierre) &
                        (_v2["importe"] > 0) & (~_v2["vend_c"].isin(_VENDEDORES_EXCLUIDOS))
                    ]
                    ccc_mes_total = int(_v2["Cliente"].nunique())
                except Exception:
                    pass

            denom = ccc_mes_total if ccc_mes_total > 0 else None
            pp = (innov.groupby(["producto_codigo", "producto_nombre"])
                  .agg(compraron=("clientes_compraron", "sum"))
                  .reset_index())
            if denom:
                pp["pct"] = (pp["compraron"] / denom * 100).round(1)
            else:
                pp["pct"] = 0.0
            innovaciones["resumen"] = {
                "productos": int(pp["producto_codigo"].nunique()),
                "compraron_total": int(pp["compraron"].sum()),
                "ccc_mes": ccc_mes_total,
                "pct_promedio": round(pp["pct"].mean(), 1) if denom else 0,
            }
            innovaciones["por_producto"] = (
                pp.sort_values("pct", ascending=False).head(20).to_dict("records")
            )
    except Exception:
        pass

    # ── Sell Out cierre: ventas_mes.csv + maestro 04D. Misma lógica que auditoría.
    # Sin fallback a ventas.csv. Si ventas_mes.csv no existe → disponible: False.
    sellout = {"categorias": [], "fuente": "ventas_mes.csv"}
    so_src = INPUTS / "ventas_mes.csv"
    if not so_src.exists():
        sellout["disponible"] = False
        sellout["error"] = "ventas_mes.csv no encontrado en 01_INPUTS"
    else:
        # Leer ventas_mes.csv con lector específico (sep=',' explícito, no sep=None)
        so_df = _leer_ventas_mes_csv(so_src)
        sellout["filas_ventas_mes"] = len(so_df)
        if so_df.empty:
            sellout["error"] = "ventas_mes.csv sin filas válidas (importe>0, excl V2/V5/V20)"
        else:
            # Mismo cruce ventas × maestro 04D que generó auditoria_sellout_cierre_mes.csv
            try:
                sellout["categorias"] = _sellout_desde_ventas(so_df)
            except Exception as _e:
                sellout["error"] = str(_e)

    # ── Planes AS ──
    planes_as = {"resumen": {}, "por_plan": []}
    try:
        pa = read_csv(DATASETS / "mod_planes_as.csv")
        if not pa.empty:
            planes_as["resumen"] = {
                "clientes": int(len(pa)),
                "facturado": round(float(pa["total_facturado"].sum()), 0),
                "sc_ganado": int(pa["sc_total_ganado"].sum()),
                "sc_enviado": int(pa["sc_cajas_enviadas_total"].sum()),
            }
            pp = pa.groupby("plan_as").agg(
                clientes=("cliente_id", "count"),
                facturado=("total_facturado", "sum"),
                sc_ganado=("sc_total_ganado", "sum"),
            ).reset_index()
            planes_as["por_plan"] = pp.to_dict("records")
    except Exception:
        pass

    # ── Acciones Comerciales ──
    acciones = {"resumen": {}, "detalle": []}
    try:
        ac = read_csv(DATASETS / "mod_acciones_ranking.csv")
        if not ac.empty:
            acciones["resumen"] = {
                "total_acciones": int(len(ac)),
                "inversion_total": round(float(ac["inversion_pesos"].sum()), 0),
                "clientes_afectados": int(ac["clientes_afectados"].sum()),
                "importe_neto": round(float(ac["importe_neto"].sum()), 0),
            }
            top = ac.sort_values("inversion_pesos", ascending=False).head(10)
            acciones["detalle"] = [
                {
                    "nombre": r["accion_nombre"],
                    "tipo": r.get("tipo_accion", ""),
                    "canal": r.get("canal", ""),
                    "categoria": r.get("categoria", ""),
                    "descuento": r.get("descuento_display", ""),
                    "litros": round(float(r.get("litros_vendidos", 0)), 1),
                    "inversion": round(float(r["inversion_pesos"]), 0),
                    "importe_neto": round(float(r.get("importe_neto", 0)), 0),
                    "clientes": int(r.get("clientes_afectados", 0)),
                }
                for _, r in top.iterrows()
            ]
    except Exception:
        pass

    return jsonify({
        "mes":              f"{año:04d}-{mes:02d}",
        "nombre_mes":       nombre_mes,
        "calendario":       cal,
        "empresa":          empresa,
        "vendedores":       vendedores,
        "once_titulares":   once_titulares,
        "innovaciones":     innovaciones,
        "sellout":          sellout,
        "planes_as":        planes_as,
        "acciones":         acciones,
        "fuente_objetivos": "resultado.xlsx",
        "fuente_ccc":       "ventas_acumulada.csv",
    })


# ====== DEBUG TEMPORAL — diagnóstico ventas_mes.csv en Render ======
@app.route("/api/debug/ventas_mes")
def debug_ventas_mes():
    """Endpoint temporal para diagnosticar ventas_mes.csv en Render.
    No expone datos de clientes, importes ni nombres."""
    import hashlib, subprocess

    src = INPUTS / "ventas_mes.csv"
    info = {"ruta": str(src), "existe": src.exists()}

    if not src.exists():
        return jsonify(info)

    # Tamaño
    info["tamanio_bytes"] = src.stat().st_size

    # MD5
    try:
        h = hashlib.md5(src.read_bytes()).hexdigest()
        info["md5"] = h
    except Exception as e:
        info["md5"] = f"error: {e}"

    # Git commit
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H %ai"],
            cwd=str(BASE), capture_output=True, text=True, timeout=5
        )
        info["git_commit"] = result.stdout.strip() if result.returncode == 0 else "no disponible"
    except Exception:
        info["git_commit"] = "no disponible"

    # Leer CSV — solo columnas de diagnóstico, sin datos sensibles
    df_raw = pd.DataFrame()
    for enc in ("utf-8-sig", "latin-1", "windows-1252"):
        try:
            df_raw = pd.read_csv(src, sep=",", quotechar='"', encoding=enc,
                                 usecols=lambda c: c.strip() in
                                 ("FechaComprobante", "ImporteNetoItem", "CodVendedor"))
            df_raw.columns = [c.strip() for c in df_raw.columns]
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            info["error_lectura"] = str(e)
            break

    info["filas_raw"] = len(df_raw)

    if df_raw.empty:
        info["filas_validas"] = 0
        return jsonify(info)

    # Fechas (sin importes ni clientes)
    if "FechaComprobante" in df_raw.columns:
        fechas = pd.to_datetime(df_raw["FechaComprobante"], dayfirst=True, errors="coerce").dropna()
        fechas_sorted = fechas.sort_values()
        info["primeras_3_fechas"] = [str(f.date()) for f in fechas_sorted.head(3)]
        info["ultimas_3_fechas"]  = [str(f.date()) for f in fechas_sorted.tail(3)]

    # Filas válidas (misma lógica que _leer_ventas_mes_csv)
    for col in ("ImporteNetoItem", "CodVendedor"):
        if col not in df_raw.columns:
            df_raw[col] = 0.0
        elif df_raw[col].dtype == object:
            df_raw[col] = df_raw[col].astype(str).str.replace(",", ".", regex=False).pipe(pd.to_numeric, errors="coerce").fillna(0)
        else:
            df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce").fillna(0)

    df_valid = df_raw[~df_raw["CodVendedor"].isin({2, 5, 20}) & (df_raw["ImporteNetoItem"] > 0)]
    info["filas_validas"] = int(len(df_valid))

    return jsonify(info)


# ====== STARTUP (gunicorn + __main__) ======
# Se ejecuta cuando gunicorn importa el módulo, no solo en __main__
backup_orbit_db()         # 1. copia orbit.db antes de cualquier cambio
init_db()                 # 2. crea/migra tablas
restore_planificacion_if_empty()  # 3. recupera desde CSV si la tabla quedó vacía
export_planificacion_csv()        # 4. actualiza CSV de seguridad con estado actual

if __name__ == "__main__":
    print("\n===== ORBIT SERVER v3 =====")
    print("Diagnóstico: http://localhost:8502/api/diagnostico")
    print("Dashboard:   http://localhost:8502/api/dashboard")
    print("Portal:      http://localhost:8502/index.html")
    print("===============================\n")
    port = int(os.environ.get("PORT", 8502))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
