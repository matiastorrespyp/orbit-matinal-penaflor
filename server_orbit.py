"""
ORBIT Server v3 — Flask API con diagnóstico, CCC real, 11T real, sin mock
"""
from flask import Flask, jsonify, request, send_from_directory, make_response, send_file
import json, sqlite3, pandas as pd, math
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta, timezone

_ARG_TZ = timezone(timedelta(hours=-3))
def _now_ar():
    """Hora actual en Argentina (UTC-3) como string 'YYYY-MM-DD HH:MM:SS'."""
    return datetime.now(_ARG_TZ).strftime("%Y-%m-%d %H:%M:%S")

import os, shutil, csv as _csv, threading
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
    # Seguimiento gerencial de alertas: nota por alerta (clave = vendedor|cliente|articulo)
    c.execute("""CREATE TABLE IF NOT EXISTS alerta_seguimiento(
        clave TEXT PRIMARY KEY, mensaje TEXT, autor TEXT, updated_at TEXT)""")
    conn.commit()
    conn.close()

def backup_orbit_db():
    """Copia orbit.db con timestamp antes de cada arranque del servidor."""
    if not DB_PATH.exists():
        return
    try:
        PLAN_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = _now_ar().replace("-","").replace(":","").replace(" ","_")
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

# ====== GOOGLE SHEETS — fuente de verdad de planificaciones ======
# SQLite es solo cache. La fuente de verdad es Google Sheets.
# Credenciales: NUNCA en Git. Se inyectan por variable de entorno en Render.
#   GSHEETS_SPREADSHEET_ID   = id del spreadsheet (cadena en la URL)
#   GSHEETS_SHEET_NAME       = nombre de la pestaña (default "planificaciones")
#   GSHEETS_CREDENTIALS_JSON = JSON del service account (o base64 del JSON)
_GSHEETS_SPREADSHEET_ID = os.environ.get("GSHEETS_SPREADSHEET_ID", "").strip()
_GSHEETS_SHEET_NAME     = os.environ.get("GSHEETS_SHEET_NAME", "planificaciones").strip() or "planificaciones"
_GSHEETS_SCOPES         = ["https://www.googleapis.com/auth/spreadsheets"]

# Orden canónico de columnas en la hoja (orden aprobado).
PLAN_SHEET_COLS = [
    "id", "fecha", "vendedor_id", "zona", "dia_visita", "venta_esperada",
    "ccc_tradicional", "ccc_autoservicio", "ccc_onpremise", "once_t",
    "marcas", "clientes_clave", "acciones", "estado",
    "created_at", "updated_at", "editado_por", "comentario_gerencia",
]

def _plan_id(fecha, vendedor_id):
    """ID determinístico del plan: fecha + '_' + vendedor_id. Ej: 2026-06-04_V8"""
    return f"{str(fecha).strip()}_{str(vendedor_id).strip().upper()}"

def _gsheet_cell(v):
    """Normaliza un valor de plan a celda de hoja (None -> '')."""
    return "" if v is None else v

def _gsheets_credentials_info():
    """Devuelve el dict de credenciales del service account o None."""
    raw = os.environ.get("GSHEETS_CREDENTIALS_JSON", "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        try:
            import base64
            return json.loads(base64.b64decode(raw).decode("utf-8"))
        except Exception:
            return None

def gsheets_enabled():
    """True si hay id de hoja y credenciales configuradas."""
    return bool(_GSHEETS_SPREADSHEET_ID) and _gsheets_credentials_info() is not None

def _gsheets_get_worksheet():
    """Devuelve (worksheet, None) o (None, mensaje_error). Crea la pestaña/header si falta."""
    if not _GSHEETS_SPREADSHEET_ID:
        return None, "GSHEETS_SPREADSHEET_ID no configurado"
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception as e:
        return None, f"gspread/google-auth no disponible: {e}"
    info = _gsheets_credentials_info()
    if not info:
        return None, "GSHEETS_CREDENTIALS_JSON no configurado o inválido"
    try:
        creds = Credentials.from_service_account_info(info, scopes=_GSHEETS_SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(_GSHEETS_SPREADSHEET_ID)
        try:
            ws = sh.worksheet(_GSHEETS_SHEET_NAME)
        except Exception:
            ws = sh.add_worksheet(title=_GSHEETS_SHEET_NAME,
                                  rows=1000, cols=len(PLAN_SHEET_COLS))
            ws.update(range_name="A1", values=[PLAN_SHEET_COLS])
            return ws, None
        if not ws.row_values(1):   # header faltante
            ws.update(range_name="A1", values=[PLAN_SHEET_COLS])
        return ws, None
    except Exception as e:
        return None, f"error abriendo Google Sheet: {e}"

def _gsheets_find_row(values, header, plan_id):
    """Devuelve (num_fila_1based, fila_existente) buscando por columna 'id'. (None, None) si no está."""
    idx = {name: i for i, name in enumerate(header)}
    id_i = idx.get("id")
    if id_i is None:
        return None, None
    for r in range(1, len(values)):
        row = values[r]
        if len(row) > id_i and str(row[id_i]).strip() == str(plan_id).strip():
            return r + 1, row
    return None, None

def gsheets_upsert_plan(plan):
    """Inserta o actualiza una fila por 'id' (= fecha_vendedor_id).
    Devuelve (True, None) o (False, error). Preserva created_at en re-envíos."""
    ws, err = _gsheets_get_worksheet()
    if err:
        return False, err
    try:
        plan = dict(plan)
        plan["id"] = _plan_id(plan.get("fecha"), plan.get("vendedor_id"))
        values = ws.get_all_values()
        header = values[0] if values else list(PLAN_SHEET_COLS)
        row_num, existing = _gsheets_find_row(values, header, plan["id"])
        idx = {name: i for i, name in enumerate(header)}
        # No pisar created_at en re-envíos: conservar el de la hoja si existe.
        if row_num and existing and "created_at" in idx:
            ci = idx["created_at"]
            ex_created = existing[ci] if len(existing) > ci else ""
            if ex_created:
                plan["created_at"] = ex_created
        ordered = [_gsheet_cell(plan.get(c)) for c in header]
        if row_num:
            ws.update(range_name=f"A{row_num}", values=[ordered])
        else:
            ws.append_row(ordered, value_input_option="RAW")
        return True, None
    except Exception as e:
        return False, str(e)

def gsheets_verify_plan(plan_id, expected):
    """Relee la fila por 'id' y verifica que los campos esperados coinciden. True/False."""
    ws, err = _gsheets_get_worksheet()
    if err:
        return False
    try:
        values = ws.get_all_values()
        if not values:
            return False
        header = values[0]
        idx = {name: i for i, name in enumerate(header)}
        _, row = _gsheets_find_row(values, header, plan_id)
        if not row:
            return False
        for k, v in (expected or {}).items():
            if k in idx:
                cell = row[idx[k]] if len(row) > idx[k] else ""
                if str(cell).strip() != str(v).strip():
                    return False
        return True
    except Exception:
        return False

def gsheets_read_all():
    """Lee todas las filas de la hoja como lista de dicts. [] si no hay/no disponible."""
    ws, err = _gsheets_get_worksheet()
    if err:
        return []
    try:
        values = ws.get_all_values()
        if len(values) < 2:
            return []
        header = values[0]
        out = []
        for r in range(1, len(values)):
            row = values[r]
            d = {header[i]: (row[i] if i < len(row) else "") for i in range(len(header))}
            if str(d.get("fecha", "")).strip() and str(d.get("vendedor_id", "")).strip():
                out.append(d)
        return out
    except Exception:
        return []

def hydrate_planificacion_from_sheets():
    """Carga la cache SQLite desde Google Sheets (fuente de verdad). Devuelve nº de filas."""
    rows = gsheets_read_all()
    if not rows:
        return 0
    def _num(v, cast):
        try:
            return cast(v) if str(v).strip() != "" else None
        except Exception:
            return None
    conn = sqlite3.connect(str(DB_PATH))
    inserted = 0
    for row in rows:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO planificacion
                  (fecha, vendedor_id, zona, dia_visita, venta_esperada,
                   ccc_tradicional, ccc_autoservicio, ccc_onpremise,
                   once_t, marcas, clientes_clave, acciones, estado,
                   editado_por, comentario_gerencia, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                str(row.get("fecha", "")).strip(),
                str(row.get("vendedor_id", "")).strip().upper(),
                row.get("zona") or None, row.get("dia_visita") or None,
                _num(row.get("venta_esperada"), float),
                _num(row.get("ccc_tradicional"), int),
                _num(row.get("ccc_autoservicio"), int),
                _num(row.get("ccc_onpremise"), int),
                _num(row.get("once_t"), int),
                row.get("marcas") or None, row.get("clientes_clave") or None,
                row.get("acciones") or None, row.get("estado") or "enviada",
                row.get("editado_por") or None, row.get("comentario_gerencia") or None,
                row.get("created_at") or None, row.get("updated_at") or None,
            ))
            inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    print(f"[ORBIT] Cache hidratada desde Google Sheets: {inserted} planes")
    return inserted

def restore_planificacion_if_empty():
    """Si planificacion está vacía: restaura desde CSV de backup; si no hay CSV,
    restaura desde Google Sheets (fuente de verdad)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        count = conn.execute("SELECT COUNT(*) FROM planificacion").fetchone()[0]
        conn.close()
        if count > 0:
            return
        if not PLAN_CSV_LATEST.exists():
            # No hay CSV local: intentar fuente de verdad (Google Sheets).
            if gsheets_enabled():
                hydrate_planificacion_from_sheets()
            return
        with open(str(PLAN_CSV_LATEST), "r", encoding="utf-8") as f:
            rows = list(_csv.DictReader(f))
        if not rows:
            # CSV existe pero está vacío: intentar fuente de verdad (Google Sheets).
            if gsheets_enabled():
                hydrate_planificacion_from_sheets()
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

_READ_CSV_CACHE = {}

def read_csv(path):
    """Lee un CSV cacheando el parseo por (ruta, mtime). Devuelve una COPIA para que los
    endpoints puedan agregar/transformar columnas sin contaminar el caché. Evita re-parsear
    los datasets en cada request — clave para la velocidad del portal en Render."""
    if not path.exists(): return pd.DataFrame()
    try:
        key = (str(path), os.path.getmtime(path))
    except OSError:
        key = (str(path), 0)
    cached = _READ_CSV_CACHE.get(key)
    if cached is not None:
        return cached.copy()
    df = None
    for enc in ("utf-8-sig", "latin1", "utf-8"):
        try:
            df = pd.read_csv(path, encoding=enc); break
        except Exception:
            continue
    if df is None:
        return pd.DataFrame()
    _READ_CSV_CACHE[key] = df
    # No acumular versiones viejas del mismo archivo (mtime distinto)
    for k in [k for k in _READ_CSV_CACHE if k[0] == str(path) and k != key]:
        _READ_CSV_CACHE.pop(k, None)
    return df.copy()

_VENDEDORES_EXCLUIDOS = {1, 2, 5, 20}
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

_VENTAS_PARSED_CACHE = {}

def _ventas_parsed() -> pd.DataFrame:
    """ventas.csv parseado UNA sola vez por mtime (numérico + segmento vectorizado).
    Todos los endpoints filtran sobre este DataFrame en vez de releer/reparsear el CSV
    en cada request — clave para la velocidad del portal en Render (CPU limitada).
    Columnas: cliente_id, vendedor_codigo, importe_neto, fecha, segmento_operativo."""
    path = INPUTS / "ventas.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        key = os.path.getmtime(path)
    except OSError:
        key = 0
    cached = _VENTAS_PARSED_CACHE.get(key)
    if cached is not None:
        return cached
    df = pd.DataFrame()
    for enc in ("latin1", "utf-8-sig", "utf-8"):
        try:
            # dtype=str: parseo determinístico en Render (la inferencia de coma decimal
            # difiere entre versiones de pandas). El importe se convierte con _parse_num_ar.
            df = pd.read_csv(path, sep=";", encoding=enc, dtype=str, low_memory=False)
            break
        except Exception:
            continue
    req = {"Cliente", "CodVendedor", "ImporteNetoItem", "FechaComprobante", "Ramo", "Subramo"}
    if df.empty or not req.issubset(set(df.columns)):
        return pd.DataFrame()
    df["cliente_id"]      = pd.to_numeric(df["Cliente"], errors="coerce")
    df["vendedor_codigo"] = pd.to_numeric(df["CodVendedor"], errors="coerce")
    df["importe_neto"]    = df["ImporteNetoItem"].apply(_parse_num_ar)
    df["fecha"]           = pd.to_datetime(df["FechaComprobante"], dayfirst=True, errors="coerce")
    # Segmento vectorizado: clasificar SÓLO las combinaciones únicas (Ramo, Subramo)
    # y mapear — evita el .apply() fila por fila sobre miles de filas en cada request.
    rm = df["Ramo"].fillna("").astype(str)
    sb = df["Subramo"].fillna("").astype(str)
    seg_map = {par: _clasificar_segmento(par[0], par[1]) for par in set(zip(rm, sb))}
    df["segmento_operativo"] = [seg_map[(a, b)] for a, b in zip(rm, sb)]
    _VENTAS_PARSED_CACHE.clear()
    _VENTAS_PARSED_CACHE[key] = df
    return df

def _cargar_ventas_mes_actual() -> pd.DataFrame:
    """Ventas del mes calendario actual, ImporteNetoItem > 0, sin vendedores excluidos.
    Filtra sobre _ventas_parsed() (cacheado). Columnas: cliente_id, vendedor_codigo, segmento_operativo."""
    df = _ventas_parsed()
    if df.empty:
        return pd.DataFrame()
    hoy = datetime.now()
    mes_inicio = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    d = df[(df["fecha"] >= mes_inicio) & (df["importe_neto"] > 0)
           & (~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS))]
    d = d.dropna(subset=["cliente_id", "vendedor_codigo"])
    return d[["cliente_id", "vendedor_codigo", "segmento_operativo"]].copy()

def _cargar_ventas_dia(fecha_str: str = None):
    """Ventas de UN día (fecha_str 'YYYY-MM-DD', o el más reciente si None).
    Filtra sobre _ventas_parsed() (cacheado). Excluye V2/V5/V20.
    Devuelve (DataFrame[cliente_id, vendedor_codigo, importe_neto, segmento_operativo], fecha_usada)."""
    df = _ventas_parsed()
    if df.empty:
        return pd.DataFrame(), ""
    df = df[(~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)) & (df["importe_neto"] > 0)]
    df = df.dropna(subset=["cliente_id", "vendedor_codigo", "fecha"])
    if df.empty:
        return pd.DataFrame(), ""
    target = pd.to_datetime(fecha_str).date() if fecha_str else df["fecha"].dt.date.max()
    df_dia = df[df["fecha"].dt.date == target]
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
        if cod_int == 3:  # V3 no trabaja autoservicio ni on premise (regla de negocio)
            aas = 0
            op  = 0
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
        # V3 (Nadia) solo trabaja Tradicional almacén/despensa/kiosco
        if vcod == 3:
            _ss = str(row.get(sub_col, "")).upper() if sub_col else ""
            if seg != "TRADICIONAL" or not any(k in _ss for k in ("ALMACEN", "DESPENSA", "KIOSCO")):
                continue
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

    # fecha_corte desde ventas.csv con sep=";" explícito.
    # sep=None falla en Linux (mismo patrón que ventas_mes.csv): columnas mal alineadas,
    # filas del día más reciente quedan con ImporteNetoItem=0 y se pierden.
    _fecha_corte_datos = None
    try:
        _sv = INPUTS / "ventas.csv"
        if _sv.exists():
            _dv2 = pd.DataFrame()
            for _enc in ("latin1", "utf-8-sig", "utf-8"):
                try:
                    _dv2 = pd.read_csv(_sv, sep=";", encoding=_enc,
                                       usecols=["FechaComprobante"], low_memory=False)
                    break
                except (UnicodeDecodeError, ValueError):
                    continue
            if not _dv2.empty:
                _ult = pd.to_datetime(_dv2["FechaComprobante"], format="%d/%m/%Y", errors="coerce").max()
                if pd.notna(_ult):
                    _fecha_corte_datos = _ult.to_pydatetime()
    except Exception:
        pass
    if _fecha_corte_datos is None:
        _fecha_corte_datos = datetime.now(_ARG_TZ).replace(tzinfo=None) - timedelta(days=1)
    dias = contar_dias_habiles(fecha_corte=_fecha_corte_datos)
    total_acum = sum(v["acumulado"] for v in vendedores_detectados)

    # Segmentos: denominadores desde cartera real (clientes.xlsx); cubiertos desde mod_ccc_segmento (ayer)
    seg_ids = [
        ("TRADICIONAL",    "Tradicional",          3,  "#5BC23A"),
        ("AUTOSERVICIO",   "Autoservicio",          6,  "#4DA3FF"),
        ("ON_PREMISE_VTK", "On Premise / Vinoteca", 6,  "#9B7BFF"),
    ]
    cartera_real_total = 0
    cartera_segs_real = {sid: 0 for sid, *_ in seg_ids}
    # Cartera real desde clientes.xlsx CACHEADO (_clientes_maestro, ya excluye V2/V5/V20).
    cli_df = _clientes_maestro()
    if not cli_df.empty:
        try:
            cartera_real_total = len(cli_df)
            ramo_col = next((c for c in cli_df.columns if c.lower() == "ramo"), None)
            sub_col  = next((c for c in cli_df.columns if "subramo" in c.lower() or "subseg" in c.lower()), None)
            if ramo_col:
                rm = cli_df[ramo_col].fillna("").astype(str)
                sb = cli_df[sub_col].fillna("").astype(str) if sub_col else pd.Series([""] * len(cli_df), index=cli_df.index)
                seg_map = {par: _clasificar_segmento(par[0], par[1]) for par in set(zip(rm, sb))}
                _seg = pd.Series([seg_map[(a, b)] for a, b in zip(rm, sb)], index=cli_df.index)
                for sid, *_ in seg_ids:
                    cartera_segs_real[sid] = int((_seg == sid).sum())
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

    # dia_operativo = próxima matinal (siguiente día operativo desde hoy AR)
    _DIAS_AR = {0:'LU', 1:'MA', 2:'MI', 3:'JU', 4:'VI', 5:'SA', 6:'DO'}
    _now_diag = datetime.now(_ARG_TZ)
    dia_op       = _DIAS_AR[_now_diag.weekday()]
    fecha_corte_rt = _now_diag.strftime("%Y-%m-%d")
    _sig_matinal   = _siguiente_dia_operativo(_fecha_corte_datos.date())
    dia_op_matinal = _DIAS_AR[_sig_matinal.weekday()]

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
        "generado_en": _now_ar(),
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
        "fecha_corte": _fecha_corte_datos.strftime("%Y-%m-%d"),  # última fecha de datos en ventas.csv
        "fecha_objetivo": fecha_obj_str,
        "fecha_matinal": _sig_matinal.isoformat(),  # próxima matinal = siguiente día operativo
        "fecha_planificacion_default": _fecha_planificacion_default(_now_diag),
        "dia_operativo": dia_op_matinal,     # día de la próxima matinal (siguiente día operativo)
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

    # 11T cumplidos por vendedor: desde mod_11t_acum.csv (cobertura acumulada con mínimo).
    # mod_11_titulares.csv (objetivo del día) llega del motor con tiene_flag/botellas en 0,
    # por eso el KPI "11T ✓" daba 0 para todos. mod_11t_acum sí está poblado.
    t11_acum_map = {}
    try:
        _t11a = read_csv(DATASETS / "mod_11t_acum.csv")
        if not _t11a.empty and {"vendedor_codigo", "tiene_flag"}.issubset(_t11a.columns):
            _t11a["_tf"] = pd.to_numeric(_t11a["tiene_flag"], errors="coerce").fillna(0)
            _t11a["_cn"] = _t11a["vendedor_codigo"].astype(str).apply(clean_code)
            for _cnk, _g in _t11a.groupby("_cn"):
                t11_acum_map[_cnk] = {"cumplidos": int(_g["_tf"].sum()), "total": int(len(_g))}
    except Exception:
        pass

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

        # tendencia_pct = Avance de resultado.xlsx (Tendencia/Objetivo) cuando hay fuente;
        # para vendedores sin resultado.xlsx (fallback mod_volumen) se proyecta por días hábiles.
        if cn in resultado_fallback:
            tendencia_pct = round(av, 2)
        else:
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

        # 11T cumplidos desde mod_11t_acum (cobertura real); fallback a mod_11_titulares.
        _t11v = t11_acum_map.get(cn)
        if _t11v is not None:
            t11_cumplidos = _t11v["cumplidos"]
            t11_total = _t11v["total"]
        else:
            t11_cumplidos = int(tv["tiene_flag"].sum()) if not tv.empty and "tiene_flag" in tv.columns else 0
            t11_total = len(tv)

        # V3 no trabaja autoservicio ni on premise (ccc_mes ya es 0; refuerzo ccc_dia)
        if cod.upper() == "V3":
            ccc_dia_as = 0
            ccc_dia_op = 0

        # Oportunidades: clientes sin compra del día (V3 excluye AS)
        oportunidades = 0
        if dia_param:
            oportunidades = clientes_dia_map.get(cn, {"sin_compra": 0})["sin_compra"]
        elif not cdia_df.empty and "estado_cliente" in cdia_df.columns and "vendedor_codigo" in cdia_df.columns:
            opv = cdia_df[cdia_df["vendedor_codigo"].astype(str).apply(clean_code) == cn]
            omask = opv["estado_cliente"].astype(str).str.lower().str.contains("sin", na=False)
            if cod.upper() == "V3" and "segmento_operativo" in opv.columns:
                _segu = opv["segmento_operativo"].astype(str).str.upper()
                omask = omask & (_segu != "AUTOSERVICIO") & (~_segu.str.contains("ON_PREMISE|VTK", na=False))
            oportunidades = int(omask.sum())

        result.append({
            "vendedor_id": cod,
            "vendedor_nombre": nombre,
            "sin_maestro": sin_maestro,
            "last_sync": _now_ar(),
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
                "trabaja_autoservicio": cod.upper() != "V3",
                "trabaja_onpremise": cod.upper() != "V3"
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
    # V3 (Nadia) solo Tradicional (no AS / On Premise / Mayorista)
    df = df[~((df["vendedor_id"] == "V3") & (df["segmento"].astype(str).str.upper() != "TRADICIONAL"))]

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

_CLIENTES_MAESTRO_CACHE = {}

def _clientes_maestro(incluir_deposito=False):
    """Cartera real desde clientes.xlsx, sin vendedores excluidos.

    En el maestro el Depósito (V20 en ventas) figura como codven=1 y por defecto
    queda excluido como el resto de las métricas con objetivo. incluir_deposito=True
    lo conserva SOLO para la pantalla de Clientes de gerencia (buscar/ficha); no
    afecta cobertura, planes AS ni ninguna métrica con objetivo."""
    p = INPUTS / "clientes.xlsx"
    if not p.exists():
        return pd.DataFrame()
    try:
        key = os.path.getmtime(p)
    except OSError:
        key = 0
    df = _CLIENTES_MAESTRO_CACHE.get(key)
    if df is None:
        try:
            df = pd.read_excel(p)
        except Exception:
            return pd.DataFrame()
        df.columns = [str(c).strip() for c in df.columns]
        if "Codigo" not in df.columns:
            return pd.DataFrame()
        df["_cliente_id"] = pd.to_numeric(df["Codigo"], errors="coerce")
        df["_vend"] = pd.to_numeric(df.get("codven"), errors="coerce")
        df = df.dropna(subset=["_cliente_id"]).copy()
        df["_cliente_id"] = df["_cliente_id"].astype(int)
        df["_vend_id"] = df["_vend"].apply(lambda x: f"V{int(x)}" if pd.notna(x) else "")
        _CLIENTES_MAESTRO_CACHE.clear()
        _CLIENTES_MAESTRO_CACHE[key] = df
    # Depósito = codven 1; el resto de excluidos (2/5/20) nunca se muestran.
    excluir = _VENDEDORES_EXCLUIDOS - {1} if incluir_deposito else _VENDEDORES_EXCLUIDOS
    return df[~df["_vend"].isin(excluir)].copy()


_CLIENTE_VENTAS_CACHE = {}

def _cliente_ventas_base():
    """Ventas vivas disponibles para ficha cliente. Usa PesoKg como litros, igual que Sell Out."""
    paths = [INPUTS / "ventas_acumulada.csv", INPUTS / "ventas.csv"]
    key = tuple((str(p), os.path.getmtime(p) if p.exists() else 0) for p in paths)
    df = _CLIENTE_VENTAS_CACHE.get(key)
    if df is not None:
        return df
    frames = []
    for p in paths:
        if p.exists():
            v = _preparar_df_ventas(p)
            if not v.empty:
                frames.append(v)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df.columns = [str(c).strip() for c in df.columns]
    df["_cli"] = pd.to_numeric(df.get("Cliente"), errors="coerce")
    df["_vend"] = pd.to_numeric(df.get("CodVendedor"), errors="coerce")
    df["_fecha"] = pd.to_datetime(df.get("FechaComprobante"), dayfirst=True, errors="coerce")
    df["_litros"] = pd.to_numeric(df.get("PesoKg"), errors="coerce").fillna(0)
    df["_importe"] = pd.to_numeric(df.get("ImporteNetoItem"), errors="coerce").fillna(0)
    df["_marca"] = df.get("Marca", pd.Series([""] * len(df), index=df.index)).astype(str).str.strip()
    df["_linea"] = df.get("Linea", pd.Series([""] * len(df), index=df.index)).astype(str).str.strip()
    df = df.dropna(subset=["_cli", "_vend", "_fecha"])
    if "NroComprobante" in df.columns and "Codigo" in df.columns:
        df = df.drop_duplicates(subset=["NroComprobante", "Cliente", "Codigo", "CantBase", "ImporteNetoItem"])
    else:
        df = df.drop_duplicates()
    df["_cli"] = df["_cli"].astype(int)
    df["_vend"] = df["_vend"].astype(int)
    _CLIENTE_VENTAS_CACHE.clear()
    _CLIENTE_VENTAS_CACHE[key] = df
    return df


def _cliente_row_to_dict(row):
    vend = int(row.get("_vend")) if pd.notna(row.get("_vend")) else None
    return {
        "cliente_id": int(row.get("_cliente_id")),
        "nombre": str(row.get("Razon_Social", row.get("_cliente_id", ""))).strip(),
        "direccion": str(row.get("Direccion", "")).strip(),
        "localidad": str(row.get("Localidad", "")).strip(),
        "telefono": "" if pd.isna(row.get("Telefono", "")) else str(row.get("Telefono", "")).strip(),
        "vendedor_codigo": vend,
        "vendedor_id": f"V{vend}" if vend is not None else "",
        "vendedor_nombre": str(row.get("Vendedor", "")).strip(),
        "dia_visita": str(row.get("DiasVisita", "")).strip(),
        "frecuencia_visita": str(row.get("Frecuencia", "")).strip(),
        "subcanal": str(row.get("SubSegmento", row.get("Ramo", ""))).strip(),
        "ramo": str(row.get("Ramo", "")).strip(),
    }


@app.route("/api/clientes/buscar")
def clientes_buscar():
    q = (request.args.get("q") or "").strip().upper()
    vend = normalizar_vendedor_codigo(request.args.get("vendedor") or "")
    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 50)
    except Exception:
        limit = 20
    df = _clientes_maestro(incluir_deposito=True)
    if df.empty:
        return jsonify([])
    if vend:
        df = df[df["_vend_id"] == vend]
    if q:
        nom = df.get("Razon_Social", pd.Series([""] * len(df), index=df.index)).astype(str).str.upper()
        cid = df["_cliente_id"].astype(str)
        loc = df.get("Localidad", pd.Series([""] * len(df), index=df.index)).astype(str).str.upper()
        df = df[nom.str.contains(q, na=False) | cid.str.contains(q, na=False) | loc.str.contains(q, na=False)]
    df = df.sort_values(["Razon_Social", "_cliente_id"], na_position="last").head(limit)
    return jsonify(_to_native([_cliente_row_to_dict(r) for _, r in df.iterrows()]))


@app.route("/api/clientes/<int:cliente_id>/ficha")
def cliente_ficha(cliente_id):
    vend = normalizar_vendedor_codigo(request.args.get("vendedor") or "")
    cli = _clientes_maestro(incluir_deposito=True)
    if cli.empty:
        return jsonify({"error": "clientes.xlsx no disponible"}), 404
    row_df = cli[cli["_cliente_id"] == int(cliente_id)]
    if row_df.empty:
        return jsonify({"error": "cliente no encontrado"}), 404
    row = row_df.iloc[0]
    base = _cliente_row_to_dict(row)
    if vend and base.get("vendedor_id") != vend:
        return jsonify({"error": "cliente fuera de la cartera del vendedor"}), 403

    ventas = _cliente_ventas_base()
    vc = ventas[ventas["_cli"] == int(cliente_id)].copy() if not ventas.empty else pd.DataFrame()
    if vc.empty:
        base.update({
            "marcas_mes": [],
            "ventas_mensuales": [],
            "frecuencia_compra_mensual": 0,
            "fecha_ultima_compra": None,
            "promedio_12m": {"litros": 0, "importe": 0, "meses_con_datos": 0, "meses_ventana": 12},
            "posibilidad_venta": {"litros": 0, "importe": 0, "criterio": "sin ventas disponibles"},
            "fuente": "clientes.xlsx + ventas_acumulada.csv/ventas.csv",
        })
        return jsonify(_to_native(base))

    latest = vc["_fecha"].max()
    periodo_actual = latest.to_period("M")
    inicio_12 = (periodo_actual - 11).to_timestamp()
    vc12 = vc[vc["_fecha"] >= inicio_12].copy()
    vc12["_periodo"] = vc12["_fecha"].dt.to_period("M").astype(str)
    mes_actual = vc12[vc12["_fecha"].dt.to_period("M") == periodo_actual]

    marca_col = "_marca"
    marcas = []
    if not mes_actual.empty:
        mm = (mes_actual.groupby(marca_col, dropna=False)
              .agg(litros=("_litros", "sum"), importe=("_importe", "sum"))
              .reset_index())
        for _, r in mm.sort_values("litros", ascending=False).iterrows():
            nombre = str(r[marca_col]).strip() or "Sin marca"
            marcas.append({
                "marca": nombre,
                "litros": round(float(r["litros"]), 1),
                "importe": round(float(r["importe"]), 0),
            })

    mensual = (vc12.groupby("_periodo")
               .agg(litros=("_litros", "sum"), importe=("_importe", "sum"),
                    compras=("_fecha", lambda s: int(s.dt.date.nunique())))
               .reset_index()
               .sort_values("_periodo"))
    ventas_mensuales = []
    prev_litros = None
    for _, r in mensual.iterrows():
        litros = round(float(r["litros"]), 1)
        if prev_litros is None:
            tendencia = "neutro"
        elif litros > prev_litros:
            tendencia = "verde"
        elif litros < prev_litros:
            tendencia = "rojo"
        else:
            tendencia = "neutro"
        ventas_mensuales.append({
            "periodo": str(r["_periodo"]),
            "litros": litros,
            "importe": round(float(r["importe"]), 0),
            "compras": int(r["compras"]),
            "tendencia_litros": tendencia,
        })
        prev_litros = litros

    meses_con_datos = int(len(mensual))
    promedio_litros = float(mensual["litros"].mean()) if meses_con_datos else 0
    promedio_importe = float(mensual["importe"].mean()) if meses_con_datos else 0
    litros_mes = float(mes_actual["_litros"].sum()) if not mes_actual.empty else 0
    importe_mes = float(mes_actual["_importe"].sum()) if not mes_actual.empty else 0
    frecuencia = float(mensual["compras"].mean()) if meses_con_datos else 0

    base.update({
        "periodo_mes": str(periodo_actual),
        "marcas_mes": marcas,
        "ventas_mensuales": ventas_mensuales,
        "frecuencia_compra_mensual": round(frecuencia, 1),
        "fecha_ultima_compra": latest.strftime("%Y-%m-%d") if pd.notna(latest) else None,
        "venta_mes": {"litros": round(litros_mes, 1), "importe": round(importe_mes, 0)},
        "promedio_12m": {
            "litros": round(promedio_litros, 1),
            "importe": round(promedio_importe, 0),
            "meses_con_datos": meses_con_datos,
            "meses_ventana": 12,
        },
        "posibilidad_venta": {
            "litros": round(max(0, promedio_litros - litros_mes), 1),
            "importe": round(max(0, promedio_importe - importe_mes), 0),
            "criterio": "promedio mensual de los meses disponibles dentro de la ventana de 12 meses",
        },
        "fuente": "clientes.xlsx + ventas_acumulada.csv/ventas.csv",
    })
    return jsonify(_to_native(base))

def _v3_clientes_tradicional():
    """Set de cliente_id de V3 que son Tradicional almacén/despensa/kiosco (su único canal).
    Devuelve None si no hay maestro (no filtrar)."""
    m = _clientes_maestro()
    if m is None or m.empty:
        return None
    sub_col = next((c for c in m.columns if "subseg" in c.lower() or "subramo" in c.lower()), None)
    v3 = m[m["_vend"] == 3]
    out = set()
    for _, r in v3.iterrows():
        seg = _clasificar_segmento(str(r.get("Ramo", "")), str(r.get(sub_col, "") if sub_col else ""))
        sub = str(r.get(sub_col, "")).upper() if sub_col else ""
        if seg == "TRADICIONAL" and any(k in sub for k in ("ALMACEN", "DESPENSA", "KIOSCO")):
            out.add(int(r["_cliente_id"]))
    return out


@app.route("/api/alertas")
def alertas():
    # Alertas en vivo desde el catálogo de acciones del mes (acciones_comerciales_<mes>_penaflor.csv):
    #  - descuento: % aplicado supera el tramo máximo de la acción (Plan AS / 11T contemplados).
    #  - tope: cajas/mes por cliente superan el tope mensual de la acción (combinable entre marcas).
    data = _alertas_descuento_mes() + _alertas_tope_cajas_mes()
    # V3 (Nadia) solo Tradicional almacén/despensa/kiosco: descartar alertas de clientes de otros canales
    v3_ok = _v3_clientes_tradicional()
    if v3_ok is not None:
        def _keep(a):
            es_v3 = str(a.get("vendedor_id") or "").upper() == "V3" or str(a.get("vendedor_codigo")) == "3"
            if not es_v3:
                return True
            try:
                return int(a.get("cliente_id")) in v3_ok
            except (TypeError, ValueError):
                return True
        data = [a for a in data if _keep(a)]
    return jsonify(data)


# ====== SEGUIMIENTO GERENCIAL DE ALERTAS ======
@app.route("/api/alertas/seguimiento", methods=["GET", "POST"])
def alertas_seguimiento():
    """Nota gerencial por alerta (si fue vista y hablada con el vendedor).
    Clave estable = 'vendedor_id|cliente_id|articulo'. Persiste en orbit.db (disco persistente)."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        if request.method == "POST":
            d = request.get_json(silent=True) or {}
            clave = str(d.get("clave", "")).strip()
            if not clave:
                return jsonify({"error": "falta 'clave'"}), 400
            mensaje = str(d.get("mensaje", "")).strip()
            autor = str(d.get("autor", "Gerencia")).strip() or "Gerencia"
            ts = _now_ar()
            if mensaje:
                conn.execute(
                    """INSERT INTO alerta_seguimiento(clave, mensaje, autor, updated_at)
                       VALUES(?,?,?,?)
                       ON CONFLICT(clave) DO UPDATE SET mensaje=excluded.mensaje,
                           autor=excluded.autor, updated_at=excluded.updated_at""",
                    (clave, mensaje, autor, ts))
            else:
                conn.execute("DELETE FROM alerta_seguimiento WHERE clave=?", (clave,))
            conn.commit()
            return jsonify({"ok": True, "clave": clave, "mensaje": mensaje,
                            "autor": autor, "updated_at": ts})
        # GET: devuelve todas las notas {clave: {mensaje, autor, updated_at}}
        rows = conn.execute("SELECT clave, mensaje, autor, updated_at FROM alerta_seguimiento").fetchall()
        return jsonify({r["clave"]: {"mensaje": r["mensaje"], "autor": r["autor"],
                                     "updated_at": r["updated_at"]} for r in rows})
    finally:
        conn.close()


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

    # Regla de negocio: V3 no trabaja autoservicio ni on premise
    trabaja_as = (vid_norm != "V3")
    trabaja_op = (vid_norm != "V3")

    # Clientes / venta del día — desde el motor (mod_volumen_vendedor.csv)
    vol = read_csv(DATASETS / "mod_volumen_vendedor.csv")
    vv = vol[vol["vendedor_codigo"].astype(str).apply(clean_code) == cn] if not vol.empty else pd.DataFrame()
    venta_hoy = float(vv["venta_ayer"].sum())        if not vv.empty else 0
    cli_total = int(vv["clientes_planificados"].sum()) if not vv.empty and "clientes_planificados" in vv.columns else 0
    cli_sin   = int(vv["clientes_sin_compra_mes"].sum()) if not vv.empty and "clientes_sin_compra_mes" in vv.columns else 0

    # objetivo/acumulado/avance — fuente primaria resultado.xlsx (igual que /api/dashboard);
    # se actualiza a diario sin regenerar el motor. Fallback a mod_volumen_vendedor.csv.
    obj = acum = av = 0.0
    _usa_resultado = False
    _resultado_path = INPUTS / "resultado.xlsx"
    if _resultado_path.exists():
        try:
            _adf = pd.read_excel(_resultado_path, sheet_name="Avance")
            _row = _adf[_adf["VendedorCodigo"].astype(str).apply(clean_code) == cn]
            if not _row.empty:
                _r = _row.iloc[0]
                obj  = float(_r.get("ValorObjetivo", 0) or 0)
                acum = float(_r.get("Acumulado", 0) or 0)
                av   = float(_r.get("Avance", 0) or 0)   # Avance = Tendencia/Objetivo*100 (regla Peñaflor)
                _usa_resultado = True
        except Exception:
            pass
    if not _usa_resultado:
        obj  = float(vv["objetivo_mes"].sum())  if not vv.empty else 0
        acum = float(vv["acumulado_mes"].sum()) if not vv.empty else 0
        av   = float(vv["avance_pct"].mean())   if not vv.empty else 0

    # tendencia_pct = Avance de resultado.xlsx (Tendencia/Objetivo); sin recálculo por días para
    # no divergir del dashboard. Fallback: proyección por días hábiles si no hay resultado.xlsx.
    if _usa_resultado:
        tendencia_pct_vd = round(av, 2)
    else:
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

    # V3 no trabaja autoservicio ni on premise (ccc_as/ccc_op ya son 0; refuerzo ccc_dia)
    if vid_norm == "V3":
        ccc_dia_as = 0
        ccc_dia_op = 0

    # 11 Titulares por vendedor — cantidad de clientes a los que logró vender cada marca:
    # cubiertos_dia = clientes de la ZONA DEL DÍA; cubiertos = total de todas las zonas.
    # Fuente: mod_11t_acum.csv (tiene_flag poblado por cliente). mod_11_titulares.csv viene en 0.
    dia_req = request.args.get("dia", "").strip()
    if not dia_req:
        _DIAS_AR = {0: "LU", 1: "MA", 2: "MI", 3: "JU", 4: "VI", 5: "SA", 6: "DO"}
        dia_req = _DIAS_AR[datetime.now(_ARG_TZ).weekday()]
    dia_ids = set()
    try:
        cd = _clientes_por_dia(dia_req)
        if not cd.empty and "cliente_id" in cd.columns:
            dia_ids = set(pd.to_numeric(cd["cliente_id"], errors="coerce").dropna().astype(int))
    except Exception:
        pass

    titulares11 = []
    t11a = read_csv(DATASETS / "mod_11t_acum.csv")
    if not t11a.empty and "marca_objetivo" in t11a.columns and "tiene_flag" in t11a.columns:
        tv = t11a[t11a["vendedor_codigo"].astype(str).apply(clean_code) == cn].copy()
        if not tv.empty:
            tv["tiene_flag"] = pd.to_numeric(tv["tiene_flag"], errors="coerce").fillna(0)
            tv["cliente_id"] = pd.to_numeric(tv["cliente_id"], errors="coerce")
            for marca, grp in tv.groupby("marca_objetivo", dropna=False):
                cli_si = set(grp[grp["tiene_flag"] == 1]["cliente_id"].dropna().astype(int))
                titulares11.append({"marca": marca,
                                    "cubiertos_dia": len(cli_si & dia_ids),
                                    "cubiertos": len(cli_si),
                                    "dia_zona": dia_req})
            titulares11.sort(key=lambda x: -x["cubiertos"])

    once_t_cumplidos = sum(1 for t in titulares11 if t["cubiertos"] > 0)
    once_t_total     = len(titulares11)

    return jsonify({
        "vendedor_id":       vid_norm,
        "vendedor_nombre":   nombre,
        "trabaja_autoservicio": trabaja_as,
        "trabaja_onpremise": trabaja_op,
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
        "generado_en": _now_ar(),
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
        _ts = _now_ar()
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

        # Regla: V3 no trabaja autoservicio ni on premise
        ccc_as = 0 if vid_raw == "V3" else int(d.get("ccc_autoservicio") or 0)
        ccc_op = 0 if vid_raw == "V3" else int(d.get("ccc_onpremise") or 0)
        fecha_raw = str(d.get("fecha") or "").strip().lower()
        fecha  = _fecha_planificacion_default() if fecha_raw in ("", "auto", "default") else d.get("fecha")
        _ts    = _now_ar()  # hora Argentina para ambos timestamps

        # FAIL-CLOSED: Google Sheets es la fuente de verdad. Si no guarda y verifica,
        # no se toca SQLite y se devuelve 503. SQLite queda solo como cache.
        plan = {
            "fecha": fecha, "vendedor_id": vid_raw,
            "zona": d.get("zona"), "dia_visita": d.get("dia_visita"),
            "venta_esperada": float(d.get("venta_esperada") or 0),
            "ccc_tradicional": int(d.get("ccc_tradicional") or 0),
            "ccc_autoservicio": ccc_as,
            "ccc_onpremise": ccc_op,
            "once_t": int(d.get("once_t") or 0),
            "marcas": d.get("marcas"), "clientes_clave": d.get("clientes_clave"),
            "acciones": d.get("acciones"), "estado": "enviada",
            "created_at": _ts, "updated_at": _ts,
        }
        ok_w, gerr = gsheets_upsert_plan(plan)
        if not ok_w:
            conn.close()
            return jsonify({"ok": False,
                            "error": f"No se pudo guardar en Google Sheets: {gerr}"}), 503
        if not gsheets_verify_plan(_plan_id(fecha, vid_raw), {"updated_at": _ts}):
            conn.close()
            return jsonify({"ok": False,
                            "error": "Guardado no verificado en Google Sheets"}), 503

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
             ccc_op, int(d.get("once_t") or 0),
             d.get("marcas"), d.get("clientes_clave"), d.get("acciones"),
             _ts, _ts))
        conn.commit(); conn.close()
        export_planificacion_csv()
        return jsonify({"ok": True, "vendedor_id": vid_raw, "fecha": fecha, "hora_envio": _ts})

    # GET — lee SQLite (cache) si tiene datos; si está vacío, hidrata desde Google Sheets.
    total = conn.execute("SELECT COUNT(*) FROM planificacion").fetchone()[0]
    if total == 0 and gsheets_enabled():
        conn.close()
        hydrate_planificacion_from_sheets()
        conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row

    # filtros opcionales por fecha y/o vendedor_id
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

    row_d = dict(row)
    vid_row = (row_d.get("vendedor_id") or "").upper()
    fields, vals = [], []
    # row_merge: estado del plan tras aplicar el patch (payload para Google Sheets).
    row_merge = dict(row_d)

    for f in ["zona","dia_visita","venta_esperada","ccc_tradicional",
              "once_t","marcas","clientes_clave","acciones"]:
        if f in d:
            fields.append(f"{f}=?"); vals.append(d[f]); row_merge[f] = d[f]

    if "ccc_autoservicio" in d:
        val_as = 0 if vid_row == "V3" else int(d.get("ccc_autoservicio") or 0)
        fields.append("ccc_autoservicio=?"); vals.append(val_as); row_merge["ccc_autoservicio"] = val_as

    # V3 no trabaja on premise → su CCC On Premise planificado siempre 0
    if "ccc_onpremise" in d:
        val_op = 0 if vid_row == "V3" else int(d.get("ccc_onpremise") or 0)
        fields.append("ccc_onpremise=?"); vals.append(val_op); row_merge["ccc_onpremise"] = val_op

    if estado:
        fields.append("estado=?"); vals.append(estado); row_merge["estado"] = estado
    if "editado_por" in d:
        fields.append("editado_por=?"); vals.append(d["editado_por"]); row_merge["editado_por"] = d["editado_por"]
    if "comentario_gerencia" in d:
        fields.append("comentario_gerencia=?"); vals.append(d["comentario_gerencia"]); row_merge["comentario_gerencia"] = d["comentario_gerencia"]

    new_ts = _now_ar()
    fields.append("updated_at=?")
    vals.append(new_ts)
    row_merge["updated_at"] = new_ts

    # FAIL-CLOSED: escribir y verificar en Google Sheets antes de tocar SQLite (cache).
    pid = _plan_id(row_merge.get("fecha"), row_merge.get("vendedor_id"))
    ok_w, gerr = gsheets_upsert_plan(row_merge)
    if not ok_w:
        conn.close()
        return jsonify({"ok": False,
                        "error": f"No se pudo guardar en Google Sheets: {gerr}"}), 503
    if not gsheets_verify_plan(pid, {"updated_at": new_ts}):
        conn.close()
        return jsonify({"ok": False,
                        "error": "Cambio no verificado en Google Sheets"}), 503

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
        conn.execute("INSERT INTO mensajes(vendedor_id,mensaje,created_at) VALUES(?,?,?)", (d.get("vendedor_id"), d.get("mensaje"), _now_ar()))
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
        "generado_en": _now_ar(),
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
def _real_dia_resultado(fecha_objetivo=None):
    """Real del día por vendedor = Acumulado(fecha) − Acumulado(día anterior del MISMO mes),
    desde 02_HISTORY/acumulado_resultado_historico.csv (snapshots diarios de resultado.xlsx).
    Es la forma correcta del 'real del día' (diferencia de acumulado), robusta a la FechaComprobante.
    Devuelve (dict {vendedor_codigo:int -> real_$}, fecha_hoy, fecha_ayer)."""
    p = BASE / "02_HISTORY" / "acumulado_resultado_historico.csv"
    if not p.exists():
        return {}, None, None
    df = read_csv(p)
    if df.empty or "fecha" not in df.columns:
        return {}, None, None
    df["fecha"] = df["fecha"].astype(str)
    df["vc"] = pd.to_numeric(df["vendedor_codigo"], errors="coerce")
    df["ac"] = pd.to_numeric(df["acumulado"], errors="coerce").fillna(0.0)
    df = df.dropna(subset=["vc"])
    fechas = sorted(df["fecha"].dropna().unique())
    if not fechas:
        return {}, None, None
    cand = [f for f in fechas if (not fecha_objetivo or f <= fecha_objetivo)]
    f_hoy = cand[-1] if cand else fechas[-1]
    prev = [f for f in fechas if f < f_hoy and f[:7] == f_hoy[:7]]   # mismo mes (evita borde de mes)
    f_ayer = prev[-1] if prev else None
    hoy  = dict(zip(df[df["fecha"] == f_hoy]["vc"].astype(int), df[df["fecha"] == f_hoy]["ac"]))
    ayer = (dict(zip(df[df["fecha"] == f_ayer]["vc"].astype(int), df[df["fecha"] == f_ayer]["ac"]))
            if f_ayer else {})
    real = {}
    for vc, a in hoy.items():
        d = float(a) - float(ayer.get(vc, 0.0))
        real[int(vc)] = round(d if d > 0 else 0.0, 2)   # negativo (reset) -> 0
    return real, f_hoy, f_ayer


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
            # modo "cierre": anclar en el ÚLTIMO día con cierre hecho (último snapshot
            # disponible), no en `fecha < hoy`. El cierre del día agrega el snapshot de
            # hoy a acumulado_resultado_historico.csv; recién entonces Plan vs Real debe
            # mostrar plan(hoy) vs real(hoy), y mantenerlo hasta el próximo cierre.
            _, last_snap, _ = _real_dia_resultado()
            anchor = last_snap or (datetime.now(_ARG_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
            row = conn.execute(
                "SELECT fecha FROM planificacion WHERE fecha <= ? AND fecha >= ? ORDER BY fecha DESC LIMIT 1",
                (anchor, cutoff)
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

    # PASO 2: Buscar real para esa misma fecha en ventas.csv (CCC) + real $ por diferencia de acumulado
    ventas_dia, fecha_real = _cargar_ventas_dia(fecha_plan)
    tiene_real = not ventas_dia.empty  # False = aún no se corrió el .bat con ese día
    # Real del día ($) = Acumulado(hoy) − Acumulado(ayer) desde resultado.xlsx (snapshots).
    real_dia_map, f_real_hoy, f_real_ayer = _real_dia_resultado(fecha_plan)
    usa_resultado = (f_real_hoy == fecha_plan) and (f_real_ayer is not None) and bool(real_dia_map)
    if usa_resultado:
        tiene_real = True
        fecha_real = f_real_hoy

    # PASO 3: Calcular real_map solo si hay datos de ventas
    real_map = {}
    if tiene_real:
        for cod_v, grp in ventas_dia.groupby("vendedor_codigo"):
            cod_int = int(cod_v)
            ccc_t = int(grp[grp["segmento_operativo"] == "TRADICIONAL"]["cliente_id"].nunique())
            ccc_a = int(grp[grp["segmento_operativo"] == "AUTOSERVICIO"]["cliente_id"].nunique())
            ccc_o = int(grp[grp["segmento_operativo"] == "ON_PREMISE_VTK"]["cliente_id"].nunique())
            if cod_int == 3:           # V3 no trabaja autoservicio ni on premise
                ccc_a = 0
                ccc_o = 0
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
            # Venta real del día: diferencia de acumulado (resultado.xlsx); fallback a ventas.csv
            if usa_resultado and cod_int in real_dia_map:
                real_venta = float(real_dia_map[cod_int])
                v_tiene_real = True
            else:
                real_venta = float(real.get("venta") or 0)
                v_tiene_real = bool(real)

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
                "tiene_real":       v_tiene_real,
            })

    return jsonify({
        "fecha_plan":  fecha_plan,
        "fecha_real":  fecha_real or None,
        "tiene_real":  tiene_real,
        "modo":        modo,
        "fuente_real": ("resultado.xlsx (acumulado hoy − ayer)" if usa_resultado else "ventas.csv"),
        "fecha_real_ayer": f_real_ayer if usa_resultado else None,
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
        "generado_en": _now_ar(),
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
    REGLA (corregida 2026-06-18 contra reporte de la empresa):
      - Período = TRIMESTRE calendario en curso (ene-mar / abr-jun / jul-sep / oct-dic);
        en julio arranca de cero. Se filtra por FechaComprobante >= inicio del trimestre.
      - Solo ventas PEÑAFLOR (Empresa == 'Empresa'); se EXCLUYE P&P LOGISTICA (otro
        distribuidor) — antes se sumaba e inflaba el CCC ~15-35%.
      - CCC = clientes únicos con compra válida (neto>0) por marca titular; excluye V2/V5/V20.
    Fuente primaria : ventas_acumulada.csv.
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
    ccc_dep_map = {}   # CCC del Depósito (V20), bloque aparte sin objetivo
    fuente = ""

    # ── Fuente primaria: ventas_acumulada.csv ──
    vac_path = INPUTS / "ventas_acumulada.csv"
    if vac_path.exists():
        try:
            vac = pd.read_csv(vac_path, sep=";", encoding="latin1", low_memory=False)
            vac["ImporteNetoItem"] = pd.to_numeric(
                vac["ImporteNetoItem"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
            # Ruta: solo Peñaflor (excluye P&P Logística), excluye V1/V2/V5, neto>0.
            # V20 (Depósito) se CONSERVA aunque facture vía P&P, para su CCC aparte
            # (mismo criterio que el sell out / conciliación con el proveedor).
            if "Empresa" in vac.columns:
                vac = vac[(vac["Empresa"].astype(str).str.strip() == "Empresa")
                          | (vac["CodVendedor"] == 20)]
            vac = vac[~vac["CodVendedor"].isin(_VENDEDORES_EXCLUIDOS - {20})]
            vac = vac[vac["ImporteNetoItem"] > 0]
            # Período = trimestre calendario en curso (en julio arranca de cero)
            _f = pd.to_datetime(vac.get("FechaComprobante"), dayfirst=True, errors="coerce")
            if _f.notna().any():
                _hoy = datetime.now(_ARG_TZ)
                _ini_trim = pd.Timestamp(_hoy.year, ((_hoy.month - 1) // 3) * 3 + 1, 1)
                vac = vac[_f >= _ini_trim]
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
            _es_dep = vac["CodVendedor"] == 20
            ccc_map = (vac[~_es_dep & vac["marca_objetivo"].notna()]
                       .groupby("marca_objetivo")["Cliente"]
                       .nunique().to_dict())
            ccc_dep_map = (vac[_es_dep & vac["marca_objetivo"].notna()]
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
        ccc = int(ccc_map.get(marca_obj, 0))
        obj = obj_map[marca_obj]
        pct = round(ccc / obj * 100, 1) if obj else None
        # Depósito (V20): CCC logrado aparte; no suma al objetivo ni al avance de ruta.
        ccc_dep = int(ccc_dep_map.get(marca_obj, 0))
        marcas.append({"marca": marca_obj, "ccc": ccc, "objetivo_ccc": obj,
                       "pct_objetivo": pct, "ccc_deposito": ccc_dep})

    return jsonify({
        "generado_en": _now_ar(),
        "fuente": fuente,
        "total_marcas": len(marcas),
        "marcas": marcas,
        "ccc_deposito_total": int(sum(ccc_dep_map.values())),
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
        # Solo Peñaflor (excluye P&P Logística) — igual criterio que /api/gerencia/once_titulares
        if "Empresa" in vac.columns:
            vac = vac[vac["Empresa"].astype(str).str.strip() == "Empresa"]
        vac = vac[~vac["CodVendedor"].isin(_VENDEDORES_EXCLUIDOS)]
        vac = vac[vac["ImporteNetoItem"] > 0]
        # Período = trimestre calendario en curso (en julio arranca de cero)
        _f = pd.to_datetime(vac.get("FechaComprobante"), dayfirst=True, errors="coerce")
        if _f.notna().any():
            _hoy = datetime.now(_ARG_TZ)
            _ini_trim = pd.Timestamp(_hoy.year, ((_hoy.month - 1) // 3) * 3 + 1, 1)
            vac = vac[_f >= _ini_trim]
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
        "generado_en": _now_ar(),
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

    # Supervisores: filas Origen == Supervisor (rechazo total por supervisor)
    supervisores = []
    if "Origen" in df.columns and "SupervisorNombre" in df.columns:
        sup = df[df["Origen"].astype(str).str.strip().str.lower() == "supervisor"]
        for _, row in sup.iterrows():
            nom_full = str(row.get("SupervisorNombre", "")).strip()
            if not nom_full or nom_full.lower() == "nan":
                continue
            pct = round(float(pd.to_numeric(row.get("PorcRechazo"), errors="coerce") or 0), 1)
            nombre_corto = nom_full.title().split()[-1] if nom_full.split() else nom_full.title()
            supervisores.append({
                "supervisor_nombre": nom_full.title(),
                "nombre":            nombre_corto,   # nombre de pila (ej. Esteban, Raul)
                "rechazo_pct":       pct,
            })
        supervisores.sort(key=lambda x: x["rechazo_pct"], reverse=True)

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
        "generado_en":  _now_ar(),
        "fuente":       "resultado.xlsx · hoja Rechazos",
        "supervisores": supervisores,
        "vendedores":   resultado,
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
        "generado_en": _now_ar(),
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
        "generado_en": _now_ar(),
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
        return jsonify({"generado_en": _now_ar(), "vendedores": []})

    df.columns = [c.lstrip("﻿") for c in df.columns]
    for col in ["vendedor_codigo", "cobertura_mes_flag"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
    # V3 no trabaja autoservicio ni on premise
    _segu = df["segmento_operativo"].astype(str).str.upper()
    mask_v3 = (df["vendedor_codigo"] == 3) & (_segu.isin(["AUTOSERVICIO", "ON_PREMISE_VTK"]))
    df = df[~mask_v3]

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
        "generado_en": _now_ar(),
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
        "generado_en": _now_ar(),
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
            "generado_en": _now_ar(),
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

    # ── Depósito (V20): CCC de innovación LOGRADO, aparte (sin cartera ni faltantes) ──
    deposito = []
    try:
        cods = df[["producto_codigo", "producto_nombre"]].drop_duplicates()
        cod2nom = {int(c): str(n) for c, n in zip(cods["producto_codigo"], cods["producto_nombre"])
                   if pd.notnull(c)}
        vd = _df_deposito_ventas()
        if cod2nom and not vd.empty:
            vd = vd.copy()
            vd["_cod"] = pd.to_numeric(vd["Codigo"], errors="coerce")
            for pc, nom in sorted(cod2nom.items()):
                sub = vd[vd["_cod"] == pc]
                cc = int(sub["Cliente"].nunique()) if not sub.empty else 0
                if cc > 0:
                    deposito.append({"producto_codigo": pc, "producto_nombre": nom,
                                     "clientes_compraron": cc})
    except Exception:
        deposito = []

    return jsonify({
        "generado_en": _now_ar(),
        "fuente": "mod_innovaciones_segmento.csv",
        "fecha_ejecucion": fecha_ej,
        "resumen_empresa": resumen_empresa,
        "por_vendedor": por_vendedor,
        "deposito": deposito,
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
            "generado_en": _now_ar(),
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
        "generado_en": _now_ar(),
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
            "generado_en": _now_ar(),
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
            "generado_en": _now_ar(),
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
        "generado_en": _now_ar(),
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
    # ── Depósito (V20): informativo, clientes/botellas con compra (sin cartera ni %) ──
    deposito = None
    try:
        vd = _df_deposito_ventas()
        if not vd.empty:
            deposito = {
                "vendedor_id": "V20",
                "vendedor_nombre": "Depósito (venta directa)",
                "clientes": int(vd["Cliente"].nunique()),
                "botellas": round(float(vd["CantBase"].sum()), 1),
            }
    except Exception:
        deposito = None

    return jsonify({
        "generado_en": _now_ar(),
        "fecha_calculo": fecha,
        "fuente": "mod_cobertura_acum.csv",
        "por_vendedor": list(por_vendedor.values()),
        "deposito": deposito,
    })


def _cobertura_faltantes_rows(df, cod=None):
    """Normaliza mod_cobertura_acum_detalle.csv. Si cod, filtra a ese vendedor.
    Devuelve dict {(vid, segmento): [clientes faltantes]}."""
    out = {}
    if df.empty:
        return out
    df.columns = [c.lstrip("﻿") for c in df.columns]
    df["vendedor_codigo"] = pd.to_numeric(df["vendedor_codigo"], errors="coerce")
    df = df[~df["vendedor_codigo"].isin(_VENDEDORES_EXCLUIDOS)]
    if cod is not None:
        df = df[df["vendedor_codigo"] == cod]
    for _, row in df.iterrows():
        vid = f"V{int(row['vendedor_codigo'])}" if pd.notnull(row.get("vendedor_codigo")) else "V0"
        seg = str(row.get("segmento", ""))
        out.setdefault((vid, seg), []).append({
            "cliente_id":     int(row["cliente_id"]) if pd.notnull(row.get("cliente_id")) else None,
            "cliente_nombre": str(row.get("cliente_nombre", "") or ""),
            "localidad":      str(row.get("localidad", "") or ""),
            "botellas":       round(float(row.get("cant_base_acum", 0) or 0), 1),
            "umbral":         int(row.get("umbral", 0) or 0),
        })
    return out


# ====== GERENCIA: FALTANTES DE COBERTURA POR SEGMENTO (drill-down) ======
@app.route("/api/gerencia/cobertura_acum_faltantes")
def gerencia_cobertura_acum_faltantes():
    """Clientes que aún no lograron cobertura (acumulado) por vendedor, para un segmento.
    Fuente: mod_cobertura_acum_detalle.csv. Excluye V2, V5, V20."""
    seg = request.args.get("segmento", "").strip()
    df = read_csv(DATASETS / "mod_cobertura_acum_detalle.csv")
    rows = _cobertura_faltantes_rows(df)
    por_vendedor = {}
    for (vid, segk), clientes in rows.items():
        if seg and segk.upper() != seg.upper():
            continue
        v = por_vendedor.setdefault(vid, {"vendedor_id": vid, "vendedor_nombre": "", "faltantes": []})
        v["faltantes"].extend(clientes)
    # vendedor_nombre desde el primer registro disponible
    if not df.empty:
        df.columns = [c.lstrip("﻿") for c in df.columns]
        for _, r in df.iterrows():
            vid = f"V{int(r['vendedor_codigo'])}" if pd.notnull(r.get("vendedor_codigo")) else None
            if vid in por_vendedor and not por_vendedor[vid]["vendedor_nombre"]:
                por_vendedor[vid]["vendedor_nombre"] = str(r.get("vendedor_nombre", "") or "")
    res = sorted(por_vendedor.values(),
                 key=lambda x: int(x["vendedor_id"][1:]) if x["vendedor_id"][1:].isdigit() else 999)
    return jsonify({
        "generado_en": _now_ar(),
        "segmento": seg,
        "fuente": "mod_cobertura_acum_detalle.csv",
        "por_vendedor": res,
    })


# ====== VENDEDOR: COBERTURA ACUMULADA PROPIA + FALTANTES ======
@app.route("/api/vendedor/<vid>/cobertura_acum")
def vendedor_cobertura_acum(vid):
    """Cobertura acumulada del mes del vendedor por segmento, con clientes faltantes.
    Fuente: mod_cobertura_acum.csv (agregado) + mod_cobertura_acum_detalle.csv (faltantes).
    Solo devuelve datos del propio vendedor (sin exponer a otros)."""
    try:
        cod = int(str(vid).upper().replace("V", ""))
    except ValueError:
        return jsonify({"error": "vendedor inválido"}), 400

    agg = read_csv(DATASETS / "mod_cobertura_acum.csv")
    det = read_csv(DATASETS / "mod_cobertura_acum_detalle.csv")
    falt = _cobertura_faltantes_rows(det, cod=cod)

    fecha = ""
    segmentos = []
    if not agg.empty:
        agg.columns = [c.lstrip("﻿") for c in agg.columns]
        agg["vendedor_codigo"] = pd.to_numeric(agg["vendedor_codigo"], errors="coerce")
        a = agg[agg["vendedor_codigo"] == cod].copy()
        if "fecha_calculo" in a.columns and not a.empty:
            fecha = str(a["fecha_calculo"].iloc[0])
        for _, row in a.sort_values("segmento").iterrows():
            segk = str(row["segmento"])
            segmentos.append({
                "segmento":      segk,
                "cartera":       int(row.get("cartera", 0) or 0),
                "cubiertos":     int(row.get("cubiertos", 0) or 0),
                "sin_cobertura": int(row.get("sin_cobertura", 0) or 0),
                "pct_cobertura": round(float(row.get("pct_cobertura", 0) or 0), 4),
                "faltantes":     falt.get((f"V{cod}", segk), []),
            })
    return jsonify({
        "generado_en": _now_ar(),
        "vendedor_id": f"V{cod}",
        "fecha_calculo": fecha,
        "fuente": "mod_cobertura_acum.csv",
        "segmentos": segmentos,
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
        "generado_en": _now_ar(),
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
    # compraron_dia: clientes del día que compraron el producto (ventas.csv MES VIVO × clientes del día)
    compraron_dia_map = {}   # producto_codigo → count
    if dia_param:
        try:
            acum_path = INPUTS / "ventas.csv"
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

    # ── Depósito (V20): CCC de innovación LOGRADO, aparte (sin cartera ni faltantes) ──
    deposito = []
    try:
        cod2nom = {int(c): str(n) for c, n in zip(df["producto_codigo"], df["producto_nombre"])
                   if pd.notnull(c)}
        vd = _df_deposito_ventas()
        if cod2nom and not vd.empty:
            vd = vd.copy()
            vd["_cod"] = pd.to_numeric(vd["Codigo"], errors="coerce")
            for pc, nom in sorted(cod2nom.items()):
                sub = vd[vd["_cod"] == pc]
                cc = int(sub["Cliente"].nunique()) if not sub.empty else 0
                if cc > 0:
                    deposito.append({"producto_codigo": pc, "producto_nombre": nom,
                                     "clientes_compraron": cc})
    except Exception:
        deposito = []

    return jsonify({
        "generado_en": _now_ar(),
        "fecha_ejecucion": fecha,
        "fuente": "mod_innovaciones_segmento.csv",
        "dia": dia_param or None,
        "por_producto": records,
        "deposito": deposito,
        "por_vendedor": por_v[["vendedor_id", "vendedor_nombre", "segmento",
                                "producto_codigo", "producto_nombre",
                                "clientes_cartera", "clientes_compraron"]].to_dict("records"),
    })


# ====== PLANES AS — GERENCIA ======
def _cargar_sincargos_envios():
    """Detalle de envíos de sin cargo por cliente desde mod_sincargos_envios.csv.
    Devuelve {cliente_id: [{producto, fecha, cajas, categoria}, ...]} para la tarjeta
    desplegable del portal (fecha en que se envió cada sin cargo)."""
    df = read_csv(DATASETS / "mod_sincargos_envios.csv")
    out = {}
    if df.empty:
        return out
    df["cliente_id"] = pd.to_numeric(df["cliente_id"], errors="coerce")
    for _, r in df.dropna(subset=["cliente_id"]).iterrows():
        out.setdefault(int(r["cliente_id"]), []).append({
            "producto":  str(r.get("producto", "")),
            "fecha":     str(r.get("fecha", "")),
            "cajas":     int(pd.to_numeric(r.get("cajas", 0), errors="coerce") or 0),
            "categoria": str(r.get("categoria", "")),
        })
    return out


@app.route("/api/gerencia/planes_as")
def gerencia_planes_as():
    df = read_csv(DATASETS / "mod_planes_as.csv")
    if df.empty:
        return jsonify({"error": "Sin datos"}), 404
    envios_map = _cargar_sincargos_envios()
    _num_cols = ["total_facturado", "dcto_plan", "cant_cajas", "tope", "escala_actual", "escala_max",
                 "sc_alaris", "sc_alma_mora", "sc_frizze", "sc_antares_ipa", "sc_smf_flavours",
                 "sc_total_ganado", "sc_cajas_enviadas_total", "sc_pendiente",
                 "sc_env_alaris", "sc_env_alma_mora", "sc_env_frizze", "sc_env_antares_ipa", "sc_env_smf_flavours",
                 "sc_pend_alaris", "sc_pend_alma_mora", "sc_pend_frizze", "sc_pend_antares_ipa", "sc_pend_smf_flavours"]
    for c in _num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Join con clientes.xlsx CACHEADO (_clientes_maestro) para localidad y dia_visita
    _cli_info = {}   # cliente_id → {localidad, dia_visita}
    try:
        cli_xl = _clientes_maestro()
        if not cli_xl.empty and "Codigo" in cli_xl.columns:
            for _, r in cli_xl.iterrows():
                cidx = pd.to_numeric(r.get("Codigo"), errors="coerce")
                if pd.notna(cidx):
                    _cli_info[int(cidx)] = {
                        "localidad":   str(r.get("Localidad", "") or "").strip(),
                        "dia_visita":  str(r.get("DiasVisita", "") or "").strip(),
                        "direccion":   str(r.get("Direccion", "") or "").strip(),
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
            "direccion":       str(row.get("direccion", "") or ci.get("direccion", "")),
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
            "pf_disponible":   _int(row.get("pf_disponible", 0)),
            "pf_enviado":      _int(row.get("pf_enviado", 0)),
            "pf_estado":       str(row.get("pf_estado", "")),
            "envios":          envios_map.get(cid, []),
        })
    fecha = str(df["fecha_calculo"].iloc[0]) if "fecha_calculo" in df.columns else ""
    return jsonify({
        "generado_en": _now_ar(),
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


# ====== ACCIONES COMERCIALES DEL MES (catálogo mensual × ventas) ======
# Fuente oficial: 01_INPUTS/ACCIONES COMERCIALES/<YYYY-MM>/acciones_comerciales_<mes>_<año>_penaflor.csv
# Calcula por acción: inversión real (ImporteItem-ImporteNetoItem en líneas con descuento),
# litros, clientes alcanzados, clientes nuevos (no compraron esas marcas el mes anterior).
# Display desde el catálogo: segmento, tipo (descuento/sin cargo), escala, marcas, topes.
_ACC_CAT_CANON = [
    (("VINOS DEL AÑO", "VINOS DEL ANO", "VDA"), "VDA"),
    (("VINOS DE GUARDA", "VDG"), "VDG"),
    (("VINOS DE MESA", "VDM"), "VDM"),
    (("ESPUMANTE",), "ESPUMANTES"),
    (("SIDRA",), "SIDRA"),
    (("SPIRIT",), "SPIRITS"),
    (("RTD",), "RTD"),
    (("CERVEZA",), "CERVEZA"),
]
_ACC_LINEA_TOK = {"VDA": "VDA", "VDG": "VDG", "VDM": "VDM",
                  "ESPUMANTE": "ESPUMANTES", "ESPUMANTES": "ESPUMANTES",
                  "SIDRA": "SIDRA", "SPIRIT": "SPIRITS", "SPIRITS": "SPIRITS"}
_ACC_PROD_GENERICOS = {"", "SEGUN MAESTRO PRODUCTOS ACTIVOS", "RESTO SKU", "RESTO",
                       "TODOS", "TODOS_ACTIVOS", "LISTA CERRADA DE INNOVACIONES JUNIO 2026"}
_ACC_11T_CACHE = None
_ACC_INNOV_CACHE = None
_ACC_PLAN_AS_CACHE = None


def _acc_canon_cat(c):
    u = str(c or "").strip().upper()
    for kws, canon in _ACC_CAT_CANON:
        if any(k in u for k in kws):
            return canon
    return u or None


def _acc_catalogo_mes():
    """Auto-detecta el catálogo del mes más reciente. Devuelve (mes, fuente, lista_reglas)."""
    import csv as _csvm
    base = INPUTS / "ACCIONES COMERCIALES"
    if not base.exists():
        return None, None, []
    cands = []
    for sub in base.iterdir():
        if sub.is_dir() and _re.match(r"^\d{4}-\d{2}$", sub.name):
            for c in sorted(sub.glob("*.csv")):
                if "salida" in str(c).lower() or "_backup" in str(c).lower():
                    continue
                cands.append((sub.name, c)); break
    if not cands:
        return None, None, []
    cands.sort(key=lambda x: x[0])
    mes, fuente = cands[-1]
    try:
        with open(fuente, encoding="utf-8-sig", newline="") as f:
            reglas = list(_csvm.DictReader(f, delimiter=";"))
    except Exception:
        return mes, fuente.name, []
    return mes, fuente.name, reglas


def _acc_seg_canon(seg_text, canal_text):
    t = (str(seg_text or "") + " | " + str(canal_text or "")).upper()
    out = set()
    if "TRADICIONAL" in t or "TRAD" in t or "KIOSCO" in t:
        out.add("TRADICIONAL")
    if "AUTOSERVICIO" in t or _re.search(r"\bAS\b", t):
        out.add("AUTOSERVICIO")
    if "ON PREMISE" in t or "ON_PREMISE" in t or "VTK" in t or "TDB" in t or "VINOTECA" in t:
        out.add("ON_PREMISE_VTK")
    if "MAYORISTA" in t:
        out.add("AUTOSERVICIO")
    if not out:
        out = {"TRADICIONAL", "AUTOSERVICIO", "ON_PREMISE_VTK", "OTROS"}
    return out


# Subtipos de tradicional para acciones que aplican SOLO a almacén/despensa/kiosco.
# Despensa = Almacén (regla de negocio): se canoniza a "ALMACEN" en todas las estadísticas.
_ACC_SUBSEG_TRAD = {"ALMACEN": "ALMACEN", "ALMACENES": "ALMACEN", "DESPENSA": "ALMACEN",
                    "KIOSCO": "KIOSCO", "MAXIKIOSCO": "KIOSCO"}


def _acc_subseg_filtro(seg_text, canal_text):
    """Sub-filtro dentro del canon TRADICIONAL por Subramo de la venta.
    Si la regla nombra subtipos específicos (almacén/despensa/kiosco) SIN el genérico
    de canal ('tradicional'/'trad'), devuelve el set de tokens permitidos; si no, None
    (la regla aplica a todo el canal tradicional, sin sub-restricción)."""
    t = _acc_norm(str(seg_text or "") + " " + str(canal_text or ""))
    if (_re.search(r"\bTRADICIONAL(?:ES)?\b", t) or _re.search(r"\bTRADITIONAL\b", t)
            or _re.search(r"\bTRAD\b", t)):
        return None
    allowed = {tok for kw, tok in _ACC_SUBSEG_TRAD.items() if kw in t}
    return allowed or None


def _acc_norm(s):
    """Normaliza para matchear marcas: mayúsculas, sin acentos, sin puntuación (apóstrofes/´)."""
    import unicodedata
    s = str(s or "").upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = _re.sub(r"[^A-Z0-9 ]", " ", s)
    return _re.sub(r"\s+", " ", s).strip()


def _acc_lineas_de_marca(token, all_lineas):
    """Devuelve set de líneas comerciales (NORMALIZADAS) que corresponden a la marca del token."""
    base = _acc_norm(token.replace(" VINO", ""))
    wine_only = token.upper().endswith(" VINO") or token.upper().strip() == "VINO"
    out = set()
    if not base:
        return out
    for ln in all_lineas:
        lnn = _acc_norm(ln)
        if lnn == base or lnn.startswith(base + " "):
            if wine_only and ("SIDRA" in lnn or "CHAMPA" in lnn or "ESPUMA" in lnn):
                continue
            out.add(lnn)
    return out


def _acc_once_titulares_tokens():
    """Marcas 11T vigentes desde objetivo 11T.xlsx, normalizadas para match contra ventas.csv."""
    global _ACC_11T_CACHE
    if _ACC_11T_CACHE is not None:
        return _ACC_11T_CACHE
    toks = []
    p = INPUTS / "objetivo 11T.xlsx"
    if p.exists():
        try:
            df = pd.read_excel(p)
            col = next((c for c in df.columns if "linea" in str(c).lower()), None)
            if col is None and len(df.columns) > 1:
                col = df.columns[1]
            vals = df[col].dropna().tolist() if col is not None else []
            for v in vals:
                n = _acc_norm(v).replace("SIMRNOFF", "SMIRNOFF")
                if n and n != "LINEA COMERCIAL":
                    toks.append(n)
        except Exception:
            toks = []
    if not toks:
        toks = [_acc_norm(x) for x in [
            "Alma Mora", "Trapiche Reserva", "Finca Las Moras", "Alaris", "Don David",
            "Dada", "Smirnoff Flavors", "Los Arboles", "Antares", "Smirnoff Ice",
            "Gordons Flavours",
        ]]
    _ACC_11T_CACHE = set(toks)
    return _ACC_11T_CACHE


def _acc_innovaciones_codigos():
    """Codigos de la lista cerrada de Innovaciones.xlsx."""
    global _ACC_INNOV_CACHE
    if _ACC_INNOV_CACHE is not None:
        return _ACC_INNOV_CACHE
    out = set()
    p = INPUTS / "INNOVACIONES" / "Innovaciones.xlsx"
    if p.exists():
        try:
            df = pd.read_excel(p, sheet_name=0, header=None, dtype=str)
            for val in df.stack().dropna().astype(str):
                for m in _re.finditer(r"(?:0{3,})?(\d{5})\s*-", val):
                    out.add(m.group(1).lstrip("0"))
        except Exception:
            out = set()
    _ACC_INNOV_CACHE = out
    return _ACC_INNOV_CACHE


def _acc_plan_as_clientes():
    """Clientes con Plan AS vigente desde mod_planes_as.csv."""
    global _ACC_PLAN_AS_CACHE
    if _ACC_PLAN_AS_CACHE is not None:
        return _ACC_PLAN_AS_CACHE
    df = read_csv(DATASETS / "mod_planes_as.csv")
    if df.empty or "cliente_id" not in df.columns:
        _ACC_PLAN_AS_CACHE = set()
    else:
        _ACC_PLAN_AS_CACHE = set(pd.to_numeric(df["cliente_id"], errors="coerce").dropna().astype(int))
    return _ACC_PLAN_AS_CACHE


def _acc_product_pred(rule, all_lineas):
    """Devuelve función(cat_canon, linea, articulo, marca, cod=None)->bool para esta regla."""
    regla_txt = _acc_norm(" ".join(str(rule.get(k, "")) for k in (
        "categoria", "subcategoria", "productos_marcas", "lineas_comerciales", "tipo_regla"
    )))
    if "11 TITULARES" in regla_txt:
        marcas_11t = _acc_once_titulares_tokens()
        def pred_11t(cat_canon, linea, articulo, marca, cod=None):
            txt = _acc_norm(f"{linea or ''} {articulo or ''} {marca or ''}")
            return any(tok in txt for tok in marcas_11t)
        return pred_11t
    if "LISTA CERRADA DE INNOVACIONES JUNIO 2026" in regla_txt or "INNOVACIONES LISTADAS" in regla_txt:
        codigos = _acc_innovaciones_codigos()
        def pred_innov(cat_canon, linea, articulo, marca, cod=None):
            return bool(codigos) and cod is not None and str(cod).strip() in codigos
        return pred_innov

    raw = (str(rule.get("productos_marcas", "")) + ";" + str(rule.get("lineas_comerciales", ""))).upper()
    toks = [t.strip() for t in raw.replace(",", ";").split(";") if t.strip()]
    line_cats, brand_lineas = set(), set()
    brand_toks = []
    code_set = set()   # códigos de producto exactos (ej. "35103"): acción dirigida a un SKU
    has_resto = any("RESTO" in t for t in toks)
    for t in toks:
        if t.isdigit():   # token numérico = código de producto exacto
            code_set.add(t)
            continue
        if (t in _ACC_PROD_GENERICOS or "MAESTRO" in t or "LISTA CERRADA" in t
                or "RESTO" in t or t in ("TODOS", "TODOS_ACTIVOS")):
            continue
        mapped = _ACC_LINEA_TOK.get(t)   # match exacto de token de línea (no substring)
        if mapped:
            line_cats.add(mapped)
        else:
            brand_toks.append(t.replace(" VINO", "").strip())
            brand_lineas |= _acc_lineas_de_marca(t, all_lineas)

    brand_norm = [b for b in (_acc_norm(x) for x in brand_toks) if b]

    def pred(cat_canon, linea, articulo, marca, cod=None):
        if code_set and cod is not None and str(cod).strip() in code_set:
            return True
        if has_resto and not brand_toks and not line_cats and not code_set:
            return True
        if brand_lineas or brand_norm:
            if linea and brand_lineas and _acc_norm(linea) in brand_lineas:
                return True
            am = _acc_norm(str(articulo or "") + " " + str(marca or ""))
            return any(bt in am for bt in brand_norm)
        if line_cats:
            return cat_canon in line_cats
        return False
    return pred


_ACC_VENTAS_CACHE = {}
def _acc_preparar_from_df(df):
    """Computa las columnas de acciones/alertas (_cli,_vend,_cat,_linea,_seg,_subseg,
    _litros,_desc,_pct,_imp_neto,_cant,_mes,_fcomp,...) a partir de un df crudo de ventas
    (cualquier fuente: ventas.csv viva o ventas_mes versionado del cierre). Sin caché ni I/O."""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    if "Empresa" in df.columns:
        df = df[df["Empresa"].astype(str).str.strip() == "Empresa"]
    cod2cat, cod2seg, cod2lxu, cod2linea = _cargar_maestro_04D()
    def _n(s):
        return pd.to_numeric(s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                             errors="coerce").fillna(0)
    out = pd.DataFrame()
    out["_cli"]  = pd.to_numeric(df.get("Cliente"), errors="coerce")
    out["_vend"] = pd.to_numeric(df.get("CodVendedor"), errors="coerce")
    out["_cod"]  = df.get("Codigo", "").astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    out["_imp_neto"] = _n(df.get("ImporteNetoItem", pd.Series(["0"] * len(df))))
    out["_imp_item"] = _n(df.get("ImporteItem", pd.Series(["0"] * len(df))))
    out["_cant"] = _n(df.get("CantBase", pd.Series(["0"] * len(df))))
    # Descuento REAL = valorDescuento (por unidad) × CantBase.
    # NO usar ImporteItem-ImporteNetoItem: esa diferencia es IVA (~17.4% en TODAS las líneas), no descuento.
    out["_vd"] = _n(df.get("valorDescuento", pd.Series(["0"] * len(df))))
    out["_desc"] = (out["_vd"] * out["_cant"]).clip(lower=0)
    out["_pct"] = (out["_desc"] / (out["_imp_neto"] + out["_desc"]).replace(0, pd.NA) * 100).fillna(0).round(1)
    out["_lxu"]  = out["_cod"].map(cod2lxu).fillna(0)
    out["_litros"] = out["_cant"] * out["_lxu"]
    out["_cat"]  = out["_cod"].map(cod2cat).map(_acc_canon_cat)
    out["_linea"] = out["_cod"].map(cod2linea).astype(str).str.upper().str.strip()
    out["_art"]  = df.get("Articulo", "").astype(str).str.upper()
    out["_marca"] = df.get("Marca", "").astype(str).str.upper()
    out["_clinom"] = (df["RazonSocial"].astype(str) if "RazonSocial" in df.columns
                      else df.get("Cliente", pd.Series([""] * len(df))).astype(str))
    out["_dir"] = df.get("Direccion", pd.Series([""] * len(df))).astype(str)
    out["_loc"] = df.get("Localidad", pd.Series([""] * len(df))).astype(str)
    out["_vnom"] = (df["Vendedor"].astype(str) if "Vendedor" in df.columns
                    else pd.Series([""] * len(df), index=df.index))
    _subr = df.get("Subramo", pd.Series([""] * len(df)))
    out["_seg"]  = [
        _clasificar_segmento(str(r), str(s))
        for r, s in zip(df.get("Ramo", pd.Series([""] * len(df))), _subr)
    ]
    # Subramo normalizado: sub-filtro de acciones acotadas a almacén/kiosco.
    # Despensa = Almacén (regla de negocio): se canoniza despensa→almacén en todas las estadísticas.
    out["_subseg"] = [_acc_norm(s).replace("DESPENSA", "ALMACEN") for s in _subr]
    _fc = pd.to_datetime(df.get("FechaComprobante"), dayfirst=True, errors="coerce")
    out["_mes"]  = _fc.dt.to_period("M")
    out["_fcomp"] = _fc.dt.strftime("%d/%m/%Y").fillna("")
    out["_fcarga"] = (pd.to_datetime(df.get("FechaCarga"), dayfirst=True, errors="coerce")
                      .dt.strftime("%d/%m/%Y").fillna(""))
    out = out[(out["_imp_neto"] > 0) & (~out["_vend"].isin(_VENDEDORES_EXCLUIDOS))]
    return out


def _acc_preparar_ventas(nombre="ventas.csv"):
    """Ventas preparadas para acciones/alertas desde 01_INPUTS/<nombre> (sep=';', mes vivo).
    Por defecto ventas.csv. ventas_acumulada.csv solo para el comparativo de 'clientes nuevos'."""
    p = INPUTS / nombre
    if not p.exists():
        return pd.DataFrame()
    try:
        key = (nombre, os.path.getmtime(p))
    except OSError:
        key = (nombre, 0)
    cached = _ACC_VENTAS_CACHE.get(key)
    if cached is not None:
        return cached
    df = None
    for enc in ("latin1", "utf-8-sig", "windows-1252"):
        try:
            df = pd.read_csv(p, sep=";", encoding=enc, dtype=str, low_memory=False)
            break
        except (UnicodeDecodeError, ValueError):
            continue
    out = _acc_preparar_from_df(df)
    # cachear por (archivo, mtime); purgar mtimes viejos del mismo archivo
    for k in [k for k in _ACC_VENTAS_CACHE if k[0] == nombre]:
        _ACC_VENTAS_CACHE.pop(k, None)
    _ACC_VENTAS_CACHE[key] = out
    return out


def _acc_preparar_ventas_mes_versionado(path):
    """Igual que _acc_preparar_ventas pero sobre el ventas_mes CONGELADO del cierre
    (01_INPUTS/cierres mes/ventas_mes_<MMAAAA>.csv, sep=',', utf-8-sig). Cacheado por path+mtime."""
    try:
        key = ("cierre:" + str(path), os.path.getmtime(path))
    except OSError:
        key = ("cierre:" + str(path), 0)
    cached = _ACC_VENTAS_CACHE.get(key)
    if cached is not None:
        return cached
    df = None
    for enc in ("utf-8-sig", "latin1", "windows-1252"):
        try:
            df = pd.read_csv(path, sep=",", quotechar='"', engine="python", dtype=str, encoding=enc)
            break
        except (UnicodeDecodeError, ValueError):
            continue
    out = _acc_preparar_from_df(df)
    _ACC_VENTAS_CACHE[key] = out
    return out


_ACC_MES_CACHE = {}
def _acc_mes_sig():
    """Firma de invalidación del payload de acciones: mtime de las fuentes reales."""
    sig = []
    for p in (INPUTS / "ventas.csv", INPUTS / "ventas_acumulada.csv",
              DATASETS / "mod_planes_as.csv", CONFIG / "maestro_04D_productos.csv",
              INPUTS / "04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx"):
        try:
            sig.append((p.name, os.path.getmtime(p) if p.exists() else 0))
        except OSError:
            sig.append((p.name, 0))
    base = INPUTS / "ACCIONES COMERCIALES"
    try:
        cat = max((os.path.getmtime(c) for sub in base.iterdir() if sub.is_dir()
                   for c in sub.glob("*.csv")), default=0) if base.exists() else 0
    except OSError:
        cat = 0
    sig.append(("acc_cat", cat))
    return tuple(sig)


def _acciones_mes_payload(vid_filtro=None):
    """Wrapper cacheado por (firma de fuentes, vendedor). Evita recalcular el payload
    (lectura de ventas + apply por regla, ~18s) en cada login; el cómputo real está en
    _acciones_mes_payload_uncached. Se invalida cuando cambia el mtime de alguna fuente."""
    ckey = (_acc_mes_sig(), vid_filtro)
    cached = _ACC_MES_CACHE.get(ckey)
    if cached is not None:
        return cached
    payload = _acciones_mes_payload_uncached(vid_filtro)
    # purgar firmas viejas; conservar variantes por vendedor de la firma actual
    for k in [k for k in _ACC_MES_CACHE if k[0] != ckey[0]]:
        _ACC_MES_CACHE.pop(k, None)
    _ACC_MES_CACHE[ckey] = payload
    return payload


def _acciones_mes_payload_uncached(vid_filtro=None):
    mes, fuente, reglas = _acc_catalogo_mes()
    if not reglas:
        return {"mes": mes, "fuente": fuente, "acciones": [], "nota": "Sin catálogo de acciones del mes."}
    v_cur = _acc_preparar_ventas("ventas.csv")   # MES VIVO
    if v_cur.empty:
        return {"mes": mes, "fuente": fuente, "acciones": [], "nota": "Sin ventas para calcular."}
    # ventas_acumulada solo aporta el mes ANTERIOR para el comparativo de clientes nuevos
    v_acum = _acc_preparar_ventas("ventas_acumulada.csv")

    # mes objetivo = el del catálogo; mes anterior = el previo
    try:
        per_actual = pd.Period(mes, freq="M")
    except Exception:
        per_actual = v_cur["_mes"].max()
    per_ant = per_actual - 1
    v_act = v_cur[v_cur["_mes"] == per_actual]
    if v_act.empty:
        v_act = v_cur   # ventas.csv ya es el mes vivo
    v_ant = v_acum[v_acum["_mes"] == per_ant] if not v_acum.empty else v_cur.iloc[0:0]
    _lin = [v_cur["_linea"]] + ([v_acum["_linea"]] if not v_acum.empty else [])
    all_lineas = set(l for l in pd.concat(_lin).dropna().unique() if l and l != "NAN")
    plan_as_clientes = _acc_plan_as_clientes()

    def _detalle_clientes(df, nuevos=None):
        if df.empty:
            return []
        nuevos = set(nuevos or [])
        rows = []
        for cli, g in df.groupby("_cli", dropna=True):
            try:
                cli_int = int(cli)
            except Exception:
                continue
            vend = pd.to_numeric(g["_vend"], errors="coerce").dropna()
            vend_int = int(vend.iloc[0]) if not vend.empty else None
            fechas = pd.to_datetime(g["_fcomp"], dayfirst=True, errors="coerce")
            ult = fechas.max()
            rows.append({
                "cliente_id": cli_int,
                "cliente_nombre": str(g["_clinom"].iloc[0]),
                "direccion": str(g["_dir"].iloc[0]) if "_dir" in g.columns else "",
                "localidad": str(g["_loc"].iloc[0]) if "_loc" in g.columns else "",
                "vendedor_codigo": vend_int,
                "vendedor_id": f"V{vend_int}" if vend_int is not None else "",
                "vendedor_nombre": str(g["_vnom"].iloc[0]) if "_vnom" in g.columns else "",
                "lineas": int(len(g)),
                "importe_neto": round(float(g["_imp_neto"].sum()), 0),
                "descuento_pesos": round(float(g["_desc"].sum()), 0),
                "litros": round(float(g["_litros"].sum()), 1),
                "cant_base": round(float(g["_cant"].sum()), 1),
                "fecha_ultima": ult.strftime("%d/%m/%Y") if pd.notna(ult) else "",
                "nuevo": cli_int in nuevos,
            })
        rows.sort(key=lambda x: (not x["nuevo"], -x["importe_neto"], x["cliente_nombre"]))
        return rows

    acciones = []
    # Union de líneas de venta que caen bajo AL MENOS una acción (dedup por índice de
    # fila). El total NO es la suma de litros por acción: una misma línea matchea varias
    # acciones (canal + Plan AASS + 11 Titulares + Innovaciones) y se contaría 2-4 veces.
    matched_idx = set()
    prev_idx = set()
    for r in reglas:
        vends_raw = str(r.get("vendedores_aplica", "")).upper()
        if "TODOS" in vends_raw:
            vend_set = set(_VENDEDORES_ACTIVOS_PLAN)
        else:
            vend_set = set(_re.findall(r"V\s*\d+", vends_raw))
            vend_set = {"V" + _re.sub(r"\D", "", x) for x in vend_set}
        vend_codes = {int(x[1:]) for x in vend_set if x[1:].isdigit()} & {3, 4, 6, 7, 8, 9, 10}

        seg_set = _acc_seg_canon(r.get("segmento_cliente_aplica"), r.get("canal_aplica"))
        sub_allowed = _acc_subseg_filtro(r.get("segmento_cliente_aplica"), r.get("canal_aplica"))
        pred = _acc_product_pred(r, all_lineas)
        regla_txt = _acc_norm(" ".join(str(r.get(k, "")) for k in (
            "categoria", "canal_aplica", "segmento_cliente_aplica"
        )))
        requiere_plan_as = "PLANES AASS" in regla_txt or "PLAN AASS" in regla_txt

        # filtro por vendedor (vista vendedor) + regla V3 sin autoservicio
        codes = vend_codes
        seg_use = set(seg_set)
        if vid_filtro is not None:
            vnum = int(_re.sub(r"\D", "", vid_filtro) or 0)
            if vnum not in vend_codes:
                continue  # esta acción no aplica a este vendedor
            codes = {vnum}
            if vnum == 3:
                # V3 (Nadia) solo trabaja Tradicional almacén/despensa/kiosco:
                # descarta AS / On Premise / Mayorista. Si la acción no aplica a
                # tradicional, no se le muestra; la footprint se restringe a almacén/kiosco.
                seg_use &= {"TRADICIONAL"}
                if not seg_use:
                    continue
                if sub_allowed is None:
                    sub_allowed = {"ALMACEN", "KIOSCO"}

        def _match(df, sub_allowed=sub_allowed):
            if df.empty:
                return df
            m = df["_vend"].isin(codes) & df["_seg"].isin(seg_use)
            if sub_allowed is not None:
                # el sub-filtro almacén/kiosco SOLO restringe el canon TRADICIONAL;
                # Autoservicio / On Premise no se filtran por subramo (acción multicanal).
                is_trad = df["_seg"].astype(str).str.upper().eq("TRADICIONAL")
                sub_ok = df["_subseg"].apply(lambda s: any(tok in s for tok in sub_allowed))
                m = m & (~is_trad | sub_ok)
            if not m.any():
                return df.iloc[0:0]
            sub = df[m]
            # pred() depende SOLO de (_cat,_linea,_art,_marca,_cod): se evalúa una vez por
            # combinación única y se mapea a cada fila. Evita el apply fila-por-fila (~5s en
            # la vista gerencia, que en Render 0.5 vCPU supera el timeout del worker y daba
            # 500). Resultado idéntico, mucho más rápido.
            keys = list(zip(sub["_cat"], sub["_linea"], sub["_art"], sub["_marca"], sub["_cod"]))
            predcache = {}
            keep_vals = []
            for k in keys:
                if k not in predcache:
                    predcache[k] = bool(pred(*k))
                keep_vals.append(predcache[k])
            keep = pd.Series(keep_vals, index=sub.index, dtype=bool)
            sub = sub[keep]
            if requiere_plan_as:
                sub = sub[pd.to_numeric(sub["_cli"], errors="coerce").isin(plan_as_clientes)]
            return sub

        # Footprint comercial = ventas netas que matchean la accion.
        # La inversion se calcula aparte con descuento real (valorDescuento > 0).
        cur = _match(v_act)
        matched_idx |= set(cur.index)
        cur_desc = cur[cur["_desc"] > 0]
        clientes_act = set(cur["_cli"].dropna().astype(int))
        prev = _match(v_ant)
        prev_idx |= set(prev.index)
        clientes_ant = set(prev["_cli"].dropna().astype(int))
        nuevos = clientes_act - clientes_ant
        clientes_desc = set(cur_desc["_cli"].dropna().astype(int))

        tipo_raw = str(r.get("tipo_regla", "")).upper()
        tipo = "Sin cargo" if ("SIN_CARGO" in tipo_raw or "BONIFIC" in tipo_raw) else "Descuento"
        detalle = _detalle_clientes(cur, nuevos)
        detalle_nuevos = [d for d in detalle if d["nuevo"]]

        acciones.append({
            "id_accion":     str(r.get("id_accion", "")).strip(),
            "tipo":          tipo,
            "tipo_regla":    str(r.get("tipo_regla", "")).strip(),
            "segmento":      str(r.get("segmento_cliente_aplica", "")).strip(),
            "canal":         str(r.get("canal_aplica", "")).strip(),
            "vendedores":    sorted(vend_set),
            "marcas":        str(r.get("productos_marcas", "")).strip(),
            "escala":        str(r.get("condicion_compra", "")).strip(),
            "descuento_pct": str(r.get("descuento_pct", "")).strip(),
            "tope":          str(r.get("tope", "")).strip(),
            "observaciones": str(r.get("observaciones", "")).strip(),
            # computado
            "inversion_pesos":   round(float(cur_desc["_desc"].sum()), 0),
            "litros":            round(float(cur["_litros"].sum()), 1),
            "importe_neto":       round(float(cur["_imp_neto"].sum()), 0),
            "clientes_alcanzados": int(len(clientes_act)),
            "clientes_nuevos":   int(len(nuevos)),
            "clientes_con_descuento": int(len(clientes_desc)),
            "clientes_detalle": detalle,
            "clientes_nuevos_detalle": detalle_nuevos,
            "nota_calculo": "clientes desde ventas.csv con ImporteNetoItem > 0; inversion desde valorDescuento x CantBase",
        })

    # Totales reales = sobre la UNION de líneas (sin doble conteo entre acciones).
    uni = v_act.loc[v_act.index.isin(matched_idx)] if matched_idx else v_act.iloc[0:0]
    uni_desc = uni[uni["_desc"] > 0]
    uni_prev = v_ant.loc[v_ant.index.isin(prev_idx)] if prev_idx else v_ant.iloc[0:0]
    cli_act_union = set(uni["_cli"].dropna().astype(int))
    cli_ant_union = set(uni_prev["_cli"].dropna().astype(int))
    totales = {
        "litros":                 round(float(uni["_litros"].sum()), 1),
        "importe_neto":           round(float(uni["_imp_neto"].sum()), 0),
        "inversion_pesos":        round(float(uni_desc["_desc"].sum()), 0),
        "clientes_alcanzados":    int(len(cli_act_union)),
        "clientes_nuevos":        int(len(cli_act_union - cli_ant_union)),
        "clientes_con_descuento": int(uni_desc["_cli"].dropna().astype(int).nunique()),
    }
    return {"mes": mes, "fuente": fuente, "periodo": str(per_actual),
            "generado_en": _now_ar(), "acciones": acciones, "totales": totales}


def _alertas_descuento_mes():
    """Alertas de descuento del MES EN CURSO desde el catálogo de acciones (no mayo).
    Línea con descuento = alerta si el % aplicado supera el tramo MÁS ALTO de la acción
    del catálogo que aplica (vendedor+segmento+marca). Sin acción aplicable → máximo 0."""
    mes, fuente, reglas = _acc_catalogo_mes()
    v = _acc_preparar_ventas("ventas.csv")   # MES VIVO: evita arrastrar mayo de ventas_acumulada
    if v.empty or not reglas:
        return []
    try:
        per = pd.Period(mes, freq="M")
    except Exception:
        per = v["_mes"].max()
    cur = v[(v["_mes"] == per) & (v["_desc"] > 0)].copy()
    if cur.empty:
        return []
    all_lineas = set(l for l in v["_linea"].dropna().unique() if l and l != "NAN")

    parsed = []
    for r in reglas:
        vends_raw = str(r.get("vendedores_aplica", "")).upper()
        if "TODOS" in vends_raw:
            codes = {3, 4, 6, 7, 8, 9, 10}
        else:
            codes = {int(_re.sub(r"\D", "", x)) for x in _re.findall(r"V\s*\d+", vends_raw)} & {3, 4, 6, 7, 8, 9, 10}
        seg = _acc_seg_canon(r.get("segmento_cliente_aplica"), r.get("canal_aplica"))
        sub_allowed = _acc_subseg_filtro(r.get("segmento_cliente_aplica"), r.get("canal_aplica"))
        pred = _acc_product_pred(r, all_lineas)
        tipo = str(r.get("tipo_regla", "")).upper()
        tramos = [float(x) for x in str(r.get("descuento_pct", "")).replace(",", ".").split("|")
                  if x.strip().replace(".", "").isdigit()]
        maxpct = 100.0 if ("BONIFIC" in tipo or "SIN_CARGO" in tipo) else (max(tramos) if tramos else 0.0)
        parsed.append((str(r.get("id_accion", "")).strip(), codes, seg, sub_allowed, pred, maxpct))

    # Clientes Plan AS: tienen 10% de descuento en factura SIEMPRE → piso permitido = 10%.
    pas = read_csv(DATASETS / "mod_planes_as.csv")
    pas_ids = (set(pd.to_numeric(pas["cliente_id"], errors="coerce").dropna().astype(int))
               if not pas.empty and "cliente_id" in pas.columns else set())

    alerts = []
    for _, row in cur.iterrows():
        desc = float(row["_desc"])
        apl = round(float(row["_pct"]), 1)   # % descuento real (valorDescuento), no IVA
        if apl <= 0:
            continue
        vend = row["_vend"]; seg_v = row["_seg"]
        allowed, fuente_id = 0.0, None
        for rid, codes, seg, sub_allowed, pred, maxpct in parsed:
            # el sub-filtro almacén/kiosco SOLO restringe el canon TRADICIONAL
            if (sub_allowed is not None and str(row["_seg"]).upper() == "TRADICIONAL"
                    and not any(tok in row["_subseg"] for tok in sub_allowed)):
                continue
            if (vend in codes) and (seg_v in seg) and pred(row["_cat"], row["_linea"], row["_art"], row["_marca"], row["_cod"]):
                if maxpct > allowed:
                    allowed, fuente_id = maxpct, rid
        try: cli_int = int(row["_cli"])
        except Exception: cli_int = None
        # Piso 10% para clientes Plan AS (descuento de factura)
        if cli_int is not None and cli_int in pas_ids and allowed < 10.0:
            allowed = 10.0
            if not fuente_id:
                fuente_id = "Plan AS (10% factura)"
        exceso = round(apl - allowed, 1)
        if exceso <= 0:   # sin tolerancia: cualquier descuento que supere el permitido alerta
            continue
        try: cod_int = int(vend)
        except Exception: cod_int = 0
        fr = fuente_id or "sin acción aplicable"
        alerts.append({
            "vendedor_codigo": cod_int, "vendedor_nombre": str(row["_vnom"]),
            "vendedor_id": "V" + str(cod_int), "cliente_id": cli_int,
            "cliente_nombre": str(row["_clinom"]), "articulo": str(row["_art"]), "marca": str(row["_marca"]),
            "fecha_pedido": str(row.get("_fcomp", "")), "fecha_carga": str(row.get("_fcarga", "")),
            "cant_base": round(float(row["_cant"]), 1), "cajas_eq": round(float(row["_cant"]), 1),
            "descuento_aplicado_pct": apl, "descuento_maximo_pct": allowed, "exceso_pct": exceso,
            "fuente_regla": fr, "importe_neto": round(float(row["_imp_neto"]), 0),
            "valor_descuento": round(desc, 0),
            "prioridad": "alta", "tipo": "descuento", "titulo": str(row["_clinom"]),
            "detalle": f"{row['_art']} — descuento aplicado: {apl}% / máximo: {allowed}%",
            "accion": f"Revisar descuento ({fr})",
            "impacto_alertas_ars": round(desc, 0),
        })
    alerts.sort(key=lambda a: a["exceso_pct"], reverse=True)
    return alerts


def _acc_botellas_por_caja(articulo):
    """Botellas por caja desde el formato del artículo (ej. 'ALMA MORA MALBEC 6X750' -> 6).
    Default 6 (formato estándar de estas líneas). CantBase viene en botellas (lxu=0.75 L)."""
    m = _re.search(r"(\d+)\s*[xX]\s*\d+", str(articulo or ""))
    if m:
        n = int(m.group(1))
        if 1 <= n <= 48:
            return n
    return 6


def _alertas_tope_cajas_mes():
    """Alerta por exceso del TOPE MENSUAL DE CAJAS por cliente (combinable entre marcas).
    Aplica a acciones del catálogo con tope mensual en cajas: `maximo` numérico +
    `unidad_maximo` con 'caja' y 'mes' (ej. ACJ26-017: maximo=2, unidad_maximo='cajas en el mes').
    Caja = botellas/caja del artículo (6X750 -> 6). Footprint = líneas que matchean la acción
    (vendedor + segmento + sub-segmento + marca) con descuento real (>0); se suman las cajas
    por cliente en el mes y se alerta si superan el tope."""
    mes, fuente, reglas = _acc_catalogo_mes()
    v = _acc_preparar_ventas("ventas.csv")   # MES VIVO
    if v.empty or not reglas:
        return []
    try:
        per = pd.Period(mes, freq="M")
    except Exception:
        per = v["_mes"].max()
    cur = v[(v["_mes"] == per) & (v["_desc"] > 0)].copy()
    if cur.empty:
        return []
    all_lineas = set(l for l in v["_linea"].dropna().unique() if l and l != "NAN")
    cur["_cajas"] = [float(c) / _acc_botellas_por_caja(a) for c, a in zip(cur["_cant"], cur["_art"])]

    alerts = []
    for r in reglas:
        try:
            tope_cajas = float(str(r.get("maximo", "")).replace(",", ".").strip())
        except (ValueError, TypeError):
            continue
        um = _acc_norm(r.get("unidad_maximo"))
        if tope_cajas <= 0 or "CAJA" not in um or "MES" not in um:
            continue   # solo acciones con tope mensual en cajas
        rid = str(r.get("id_accion", "")).strip()
        vends_raw = str(r.get("vendedores_aplica", "")).upper()
        if "TODOS" in vends_raw:
            codes = {3, 4, 6, 7, 8, 9, 10}
        else:
            codes = {int(_re.sub(r"\D", "", x)) for x in _re.findall(r"V\s*\d+", vends_raw)} & {3, 4, 6, 7, 8, 9, 10}
        seg = _acc_seg_canon(r.get("segmento_cliente_aplica"), r.get("canal_aplica"))
        sub_allowed = _acc_subseg_filtro(r.get("segmento_cliente_aplica"), r.get("canal_aplica"))
        pred = _acc_product_pred(r, all_lineas)

        m = cur["_vend"].isin(codes) & cur["_seg"].isin(seg)
        if sub_allowed is not None:
            is_trad = cur["_seg"].astype(str).str.upper().eq("TRADICIONAL")
            sub_ok = cur["_subseg"].apply(lambda s: any(tok in s for tok in sub_allowed))
            m = m & (~is_trad | sub_ok)
        sub = cur[m]
        if sub.empty:
            continue
        keep = sub.apply(lambda x: pred(x["_cat"], x["_linea"], x["_art"], x["_marca"], x["_cod"]), axis=1)
        sub = sub[keep]
        if sub.empty:
            continue

        for cli, grp in sub.groupby("_cli"):
            cajas = round(float(grp["_cajas"].sum()), 2)
            if cajas <= tope_cajas + 1e-9:
                continue
            exceso = round(cajas - tope_cajas, 2)
            try: cli_int = int(cli)
            except Exception: cli_int = None
            try: cod_int = int(grp["_vend"].iloc[0])
            except Exception: cod_int = 0
            desc_total = round(float(grp["_desc"].sum()), 0)
            marcas_txt = ", ".join(sorted({str(x) for x in grp["_marca"].dropna() if str(x).strip()}))
            cnom = str(grp["_clinom"].iloc[0]); vnom = str(grp["_vnom"].iloc[0])
            fcarga = next((f for f in grp["_fcarga"][::-1] if str(f).strip()), "")
            tope_txt = (f"{tope_cajas:g}").rstrip()
            alerts.append({
                "vendedor_codigo": cod_int, "vendedor_nombre": vnom,
                "vendedor_id": "V" + str(cod_int), "cliente_id": cli_int,
                "cliente_nombre": cnom, "articulo": f"TOPE {rid}", "marca": marcas_txt,
                "fecha_pedido": "", "fecha_carga": str(fcarga),
                "cajas_mes": cajas, "cajas_tope": tope_cajas, "exceso_cajas": exceso,
                "fuente_regla": rid, "valor_descuento": desc_total,
                "prioridad": "alta", "tipo": "tope", "titulo": cnom,
                "detalle": (f"Tope {tope_txt} cajas/mes superado en {marcas_txt or 'marcas de la acción'}: "
                            f"{cajas:g} cajas con descuento (acción {rid}). Exceso {exceso:g} cajas."),
                "accion": f"Revisar tope de cajas ({rid})",
                "impacto_alertas_ars": desc_total,
            })
    alerts.sort(key=lambda a: a["exceso_cajas"], reverse=True)
    return alerts


@app.route("/api/gerencia/acciones_mes")
def gerencia_acciones_mes():
    return jsonify(_acciones_mes_payload(None))


@app.route("/api/vendedor/<vid>/acciones_mes")
def vendedor_acciones_mes(vid):
    vid_norm = normalizar_vendedor_codigo(vid)
    if vid_norm in ("V2", "V5", "V20"):
        return jsonify({"error": "Vendedor no autorizado"}), 403
    return jsonify(_acciones_mes_payload(vid_norm))


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
    envios_map = _cargar_sincargos_envios()
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
            "direccion":       str(row.get("direccion", "")),
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
            "pf_disponible":       _i(row, "pf_disponible"),
            "pf_enviado":          _i(row, "pf_enviado"),
            "pf_estado":           str(row.get("pf_estado", "")),
            "envios":              envios_map.get(int(row["cliente_id"]) if pd.notna(row["cliente_id"]) else -1, []),
        })
    return jsonify({
        "generado_en": _now_ar(),
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
        "generado_en": _now_ar(),
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


_MAESTRO_04D_CACHE = {}
def _cargar_maestro_04D():
    """Wrapper cacheado por mtime del maestro 04D (CSV preferido, xlsx fallback).
    El cómputo real está en _cargar_maestro_04D_uncached; cachear evita reconstruir
    los 4 dicts en cada request (lo usan acciones, dashboard, sellout, alertas)."""
    csv_path  = CONFIG / "maestro_04D_productos.csv"
    xlsx_path = INPUTS / "04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx"
    src = csv_path if csv_path.exists() else (xlsx_path if xlsx_path.exists() else None)
    try:
        key = (str(src), os.path.getmtime(src)) if src else None
    except OSError:
        key = None
    if key is not None and key in _MAESTRO_04D_CACHE:
        return _MAESTRO_04D_CACHE[key]
    result = _cargar_maestro_04D_uncached()
    if key is not None:
        _MAESTRO_04D_CACHE.clear()
        _MAESTRO_04D_CACHE[key] = result
    return result


def _cargar_maestro_04D_uncached():
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


# Normalización de la categoría del OBJSELLOUT.xlsx → categoría de la tarjeta.
# 'rtd (s)' no es categoría aparte: es un subgrupo de RTD (igual que en _SO_CAT_MAP).
_OBJ_CAT_NORM = {"RTD (S)": "RTD"}

def _cargar_objetivos_sellout() -> dict:
    """Lee 01_INPUTS/OBJSELLOUT.xlsx → {CATEGORIA_UPPER: {"total": litros, "subs": {grupo_pbp: litros}}}.
    Fuente única de objetivos de sell out. El archivo abre el objetivo por 'Grupo PBP'
    (subgrupo de precio/origen) dentro de cada categoría + una fila 'Total' por categoría.
    Columnas: categoria | Grupo PBP | objetivo en litros. Devuelve {} si falta o falla.
    Clave = categoría en mayúsculas (coincide con los buckets de _sellout_desde_ventas);
    subs por nombre de Grupo PBP (Alto/Medio Alto/Superior/Medio, Nacionales/Importados, ...)."""
    path = INPUTS / "OBJSELLOUT.xlsx"
    out = {}
    if not path.exists():
        return out
    try:
        df = pd.read_excel(path, header=1)
        df.columns = [str(c).strip().lower() for c in df.columns]
        cat_col = next((c for c in df.columns if "categor" in c), df.columns[0])
        grp_col = next((c for c in df.columns if "pbp" in c or "grupo" in c), None)
        obj_col = next((c for c in df.columns if "objetivo" in c or "litro" in c), df.columns[-1])
        rows = {}      # card_cat -> [(cat_orig, grupo_pbp, val)]
        totals = {}    # card_cat -> val (fila 'Total')
        for _, r in df.iterrows():
            cat_orig = str(r[cat_col]).strip()
            if not cat_orig or cat_orig.lower() in ("total", "nan"):
                continue
            val = pd.to_numeric(r[obj_col], errors="coerce")
            if pd.isna(val):
                continue
            val = int(round(float(val)))
            card = _OBJ_CAT_NORM.get(cat_orig.upper(), cat_orig.upper())
            grupo = str(r[grp_col]).strip() if grp_col is not None else ""
            if grupo.lower() == "total":
                totals[card] = val
            elif grupo and grupo.lower() != "nan":
                rows.setdefault(card, []).append((cat_orig, grupo, val))
        for card, rs in rows.items():
            grupos = [g for _, g, _ in rs]
            # Si dos filas comparten Grupo PBP (caso RTD: 'rtd' y 'rtd (s)' ambos PBP 'RTD'),
            # se etiqueta el subgrupo por el nombre de categoría para no pisarse.
            use_cat = len(set(grupos)) < len(grupos)
            subs = {}
            for cat_orig, grupo, val in rs:
                label = cat_orig.upper() if use_cat else grupo
                subs[label] = subs.get(label, 0) + val
            total = totals.get(card)
            if total is None:
                total = sum(subs.values()) if subs else None
            out[card] = {"total": total, "subs": subs}
        for card, t in totals.items():           # categorías que sólo tenían fila 'Total'
            out.setdefault(card, {"total": t, "subs": {}})
    except Exception:
        pass
    return out


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
    # Objetivos por categoría: fuente única OBJSELLOUT.xlsx (no hardcode).
    obj_file = _cargar_objetivos_sellout()
    # Estructura de subcategorías (solo nombres). OBJSELLOUT.xlsx trae objetivo
    # SOLO a nivel categoría → las subcategorías muestran litros SIN objetivo.
    SUBS = {
        "VINOS DEL AÑO":     ["Alto", "Medio Alto", "Superior", "Medio"],
        "VINOS DE GUARDA":   [],
        "SPIRITS":           ["Nacionales", "Importados"],
        "RTD":               ["RTD", "RTD (S)"],
        "CHAMPAÑA":          [],
        "CERVEZA ARTESANAL": [],
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
    # Categoría CRUDA del maestro (sin colapsar) para abrir RTD vs RTD (S)
    df["_cat_raw"] = cat_maestro.astype(str).str.strip().str.upper()

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
    for cat, sub_names in SUBS.items():
        grp = df[df["_cat"] == cat]
        litros   = round(float(grp["litros"].sum()), 1)
        clientes = int(grp["Cliente"].nunique()) if "Cliente" in grp.columns else 0
        obj_cat   = obj_file.get(cat, {})
        obj_total = obj_cat.get("total")            # None si la categoría no está en OBJSELLOUT.xlsx
        obj_subs  = obj_cat.get("subs", {})         # objetivo por Grupo PBP
        alcance   = round(litros / obj_total * 100, 1) if obj_total else None
        subs = []

        def _obj_sub(nombre):
            """Objetivo del subgrupo por nombre de Grupo PBP (match case-insensitive)."""
            if nombre in obj_subs:
                return obj_subs[nombre]
            return next((v for k, v in obj_subs.items() if k.lower() == nombre.lower()), None)

        if cat == "VINOS DEL AÑO":
            for sn in sub_names:
                # Segmento del maestro 04D: Alto / Medio Alto / Superior / Medio
                sg = grp[grp["_seg"].map(_SO_SEG_VDA) == sn]
                sl = round(float(sg["litros"].sum()), 1)
                sc = int(sg["Cliente"].nunique()) if "Cliente" in sg.columns else 0
                marcas = _marcas_de_grupo(sg)
                osub = _obj_sub(sn)
                subs.append({"nombre": sn, "litros": sl, "objetivo": osub,
                             "alcance_pct": round(sl / osub * 100, 1) if osub else None,
                             "clientes": sc, "marcas": marcas})

        elif cat == "SPIRITS":
            # Spirits NO están en maestro 04D → keyword por nombre de artículo
            _art = grp["Articulo"].astype(str).str.upper() if "Articulo" in grp.columns else pd.Series("", index=grp.index)
            mask_nac = _art.str.contains("|".join(_NAC_KW), na=False)
            for sn, mask_s in [("Nacionales", mask_nac), ("Importados", ~mask_nac)]:
                sg = grp[mask_s]
                sl = round(float(sg["litros"].sum()), 1)
                sc = int(sg["Cliente"].nunique()) if "Cliente" in sg.columns else 0
                marcas = _marcas_de_grupo(sg)
                osub = _obj_sub(sn)
                subs.append({"nombre": sn, "litros": sl, "objetivo": osub,
                             "alcance_pct": round(sl / osub * 100, 1) if osub else None,
                             "clientes": sc, "marcas": marcas})

        elif cat == "RTD":
            # RTD se abre en RTD (regular) y RTD (S), por la categoría cruda del maestro 04D.
            is_s = grp["_cat_raw"].astype(str).str.upper().str.replace(" ", "", regex=False) == "RTD(S)"
            for sn, mask_s in [("RTD", ~is_s), ("RTD (S)", is_s)]:
                sg = grp[mask_s]
                sl = round(float(sg["litros"].sum()), 1)
                sc = int(sg["Cliente"].nunique()) if "Cliente" in sg.columns else 0
                marcas = _marcas_de_grupo(sg)
                osub = _obj_sub(sn)
                subs.append({"nombre": sn, "litros": sl, "objetivo": osub,
                             "alcance_pct": round(sl / osub * 100, 1) if osub else None,
                             "clientes": sc, "marcas": marcas})

        resultado.append({
            "categoria": cat, "litros": litros, "objetivo": obj_total,
            "alcance_pct": alcance, "clientes": clientes, "subcategorias": subs,
            "marcas": _marcas_de_grupo(grp),
        })
    return resultado


def _marcas_de_grupo(sg: pd.DataFrame) -> list:
    """Devuelve lista [{marca, litros, varietales:[{nombre, litros}]}] ordenada desc.
    Marca   = _linea (Linea Comercial del maestro 04D); fallback Marca.
    Varietales = desglose por Articulo (SKU) dentro de la marca, ordenado desc."""
    col = "_linea" if "_linea" in sg.columns else ("Marca" if "Marca" in sg.columns else None)
    if col is None:
        return []
    art_col = "Articulo" if "Articulo" in sg.columns else None
    out = []
    for mk, sub in sg.groupby(col):
        mv = round(float(sub["litros"].sum()), 1)
        if mv <= 0 or not str(mk).strip():
            continue
        varietales = []
        if art_col:
            for av, lv in (sub.groupby(art_col)["litros"].sum()
                           .sort_values(ascending=False).items()):
                if lv > 0 and str(av).strip():
                    varietales.append({"nombre": str(av).strip(), "litros": round(float(lv), 1)})
        out.append({"marca": str(mk), "litros": mv, "varietales": varietales})
    out.sort(key=lambda x: x["litros"], reverse=True)
    return out


def _preparar_df_ventas(src_path, incluir_deposito=False) -> pd.DataFrame:
    """Lee ventas.csv, parsea columnas numéricas, excluye V2/V5 (+V20 salvo incluir_deposito),
    filtra importe > 0.
    incluir_deposito=True conserva V20 (Depósito / venta directa) para separarlo aguas abajo.
    sep=";" explícito: sep=None/engine=python sniffea mal el separador en Linux (Render)
    → columnas desalineadas, ImporteNetoItem=0, se pierden filas (mismo patrón que diagnóstico)."""
    df = None
    for enc in ("utf-8-sig", "latin-1", "windows-1252"):
        try:
            # dtype=str: no dejar que pandas infiera. En Render la inferencia de columnas
            # con coma decimal ("15800,82") difiere y casi todo quedaba en 0 (mismo patrón
            # que _leer_ventas_mes_csv, que sí funciona en Render).
            df = pd.read_csv(src_path, sep=";", encoding=enc, dtype=str, low_memory=False)
            break
        except (UnicodeDecodeError, ValueError):
            continue
    if df is None:
        return pd.DataFrame()
    df.columns = [c.strip() for c in df.columns]
    for col in ("PesoKg", "CantBase", "ImporteNetoItem", "CodVendedor"):
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = (df[col].astype(str)
                              .str.strip()
                              .str.strip('"')
                              .str.replace(",", ".", regex=False)
                              .pipe(pd.to_numeric, errors="coerce")
                              .fillna(0))
    _excl = {2, 5} if incluir_deposito else {2, 5, 20}
    df = df[~df["CodVendedor"].isin(_excl) & (df["ImporteNetoItem"] > 0)].copy()
    return df


_DEPOSITO_VENTAS_CACHE = {}
def _df_deposito_ventas() -> pd.DataFrame:
    """ventas.csv (mes vivo) SOLO Depósito V20 (venta directa), neto>0.
    Alimenta los bloques 'depósito' aparte de gerencia (innovaciones, cobertura).
    NO filtra por Empresa: el depósito factura parte de su venta directa vía
    P&P Logística, pero es la misma entidad física V20 (igual criterio que el sell out
    y la conciliación con el proveedor).
    Cacheado por mtime de ventas.csv: lo invocan 2 endpoints por carga de gerencia y
    en Render (0.5 vCPU) releer el CSV de 3MB cada vez pesa."""
    src = INPUTS / "ventas.csv"
    if not src.exists():
        return pd.DataFrame()
    try:
        key = src.stat().st_mtime
    except OSError:
        key = 0
    cached = _DEPOSITO_VENTAS_CACHE.get("df")
    if cached is not None and _DEPOSITO_VENTAS_CACHE.get("key") == key:
        return cached
    vd = _preparar_df_ventas(src, incluir_deposito=True)
    vd = vd if vd.empty else vd[vd["CodVendedor"] == 20].copy()
    _DEPOSITO_VENTAS_CACHE.clear()
    _DEPOSITO_VENTAS_CACHE.update({"key": key, "df": vd})
    return vd


def _leer_ventas_mes_csv(src_path, incluir_deposito=False) -> pd.DataFrame:
    """Lee ventas_mes.csv robusto para Windows (CRLF) y Linux (LF).
    - sep=',' + quotechar='"' + engine='python' + dtype=str evita que el motor C
      de pandas deje comillas residuales en campos como "6620,94" al leer en Linux.
    - strip('"') elimina cualquier comilla residual antes de la conversión numérica.
    incluir_deposito=True conserva V20 (Depósito) para separarlo aguas abajo (sell out cierre)."""
    df = None
    for enc in ("utf-8-sig", "latin-1", "windows-1252"):
        try:
            df = pd.read_csv(src_path, sep=",", quotechar='"',
                             engine="python", dtype=str, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        return pd.DataFrame()
    df.columns = [c.strip() for c in df.columns]
    for col in ("PesoKg", "CantBase", "ImporteNetoItem", "CodVendedor"):
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = (df[col].astype(str)
                               .str.strip()
                               .str.strip('"')
                               .str.replace(",", ".", regex=False)
                               .pipe(pd.to_numeric, errors="coerce")
                               .fillna(0))
    _excl = {2, 5} if incluir_deposito else {2, 5, 20}
    df = df[~df["CodVendedor"].isin(_excl) & (df["ImporteNetoItem"] > 0)].copy()
    return df


def _sellout_con_deposito(df_full) -> dict:
    """Dado un df de ventas con V20 conservado, separa ruta (6 cat. con objetivo) y
    Depósito V20 (mismas cat., SIN objetivo/avance). Devuelve el dict de sell out con
    `categorias`, `deposito`, `total_ruta`, `total_deposito`, `total_general`.
    Usado por el sell out vivo y por el del cierre de mes (paridad)."""
    df_ruta = df_full[df_full["CodVendedor"] != 20]
    df_dep  = df_full[df_full["CodVendedor"] == 20]
    categorias = _sellout_desde_ventas(df_ruta)
    deposito   = _sellout_desde_ventas(df_dep) if not df_dep.empty else []
    for c in deposito:
        c["objetivo"], c["alcance_pct"] = None, None
        for s in c.get("subcategorias", []):
            s["objetivo"], s["alcance_pct"] = None, None
    total_ruta     = round(sum(float(c["litros"]) for c in categorias), 1)
    total_deposito = round(sum(float(c["litros"]) for c in deposito), 1)
    return {
        "categorias":     categorias,
        "deposito":       deposito,
        "total_ruta":     total_ruta,
        "total_deposito": total_deposito,
        "total_general":  round(total_ruta + total_deposito, 1),
    }


@app.route("/api/gerencia/sellout_litros")
def gerencia_sellout_litros():
    """Sellout en litros vs objetivos. Fuente: ventas.csv × maestro_04D_productos.csv.
    El objetivo de Sell Out es de la EMPRESA (independiente del vendedor): se agrupa TODA
    la venta —ruta (7 activos) + V20 Depósito (venta directa)— y se mide contra el objetivo.
    Por eso se incluye V20 en cada categoría; el total concilia con el reporte del proveedor."""
    src = INPUTS / "ventas.csv"
    if not src.exists():
        return jsonify({"error": "ventas.csv no encontrado en 01_INPUTS"}), 404
    df = _preparar_df_ventas(src, incluir_deposito=True)  # incluye V20: objetivo de empresa
    if df.empty:
        return jsonify({"error": "No se pudo leer ventas.csv"}), 500
    categorias = _sellout_desde_ventas(df)               # agrupa ruta + V20 vs objetivo
    so = {
        "categorias":      categorias,
        "total_litros":    round(sum(float(c["litros"]) for c in categorias), 1),
        "incluye_deposito": True,
        "generado_en":     _now_ar(),
        "fuente":          "ventas.csv (incl. V20 Depósito) + maestro_04D_productos.csv",
    }
    return jsonify(so)


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
        "generado_en": _now_ar(),
        "fuente":        "mod_acciones_ranking.csv + mod_acciones_analisis.csv",
        "fecha_calculo": fecha,
        "acciones":      acciones,
    })


# ====== ALERTAS CAÍDA: clientes dormidos ======
def _litros_por_unidad(articulo):
    """Litros por unidad base a partir del nombre del artículo (ej. '6X750'->0.75, '12X1LT'->1,
    '4X6X473'->0.473). Default 0.75 L si no se puede parsear."""
    s = str(articulo).upper()
    matches = _re.findall(r"X\s*(\d+(?:[.,]\d+)?)\s*(LT|L|ML|CC)?", s)
    if not matches:
        return 0.75
    num, unit = matches[-1]
    try:
        val = float(num.replace(",", "."))
    except ValueError:
        return 0.75
    if unit in ("LT", "L"):
        return val
    return val / 1000.0   # ml/cc o sin unidad


def _dormidos_payload():
    """Clientes DORMIDOS: sin compra hace MÁS de 60 días (criterio por días).
    Última compra por cliente = max fecha en historial_ventas_cliente.csv + ventas.csv.
    Riesgo = importe_neto y litros acumulados del cliente. Excluye V2, V5, V20.
    Devuelve dict {resumen, por_vendedor, detalle}; lanza FileNotFoundError si falta la fuente.
    """
    EXCLUIR = [2, 5, 20]
    DIAS_DORMIDO = 60
    HIST_PATH = BASE / "02_HISTORY" / "historial_ventas_cliente.csv"
    VTAS_PATH = INPUTS / "ventas.csv"

    if not HIST_PATH.exists():
        raise FileNotFoundError("Fuente no disponible")

    def _vacio():
        return {"resumen": {"total_dormidos": 0, "importe_en_riesgo": 0,
                            "litros_en_riesgo": 0, "criterio_dias": DIAS_DORMIDO},
                "por_vendedor": [], "detalle": []}
    try:
        # ── Historial ──
        hc = pd.read_csv(HIST_PATH, encoding="utf-8-sig", sep=None, engine="python")
        hc["fecha"] = pd.to_datetime(hc["fecha_comprobante"], errors="coerce")
        hc["importe"] = pd.to_numeric(hc["importe_neto"], errors="coerce")
        hc["cant"] = pd.to_numeric(hc.get("cant_base", 0), errors="coerce").fillna(0)
        hc = hc[~hc["vendedor_codigo"].isin(EXCLUIR) & hc["importe"].notna() & (hc["importe"] > 0)].copy()
        hc["litros"] = hc["cant"] * hc["articulo"].map(_litros_por_unidad)
        partes = [hc[["cliente_id", "cliente_nombre", "vendedor_codigo", "vendedor_nombre",
                      "fecha", "importe", "litros"]]]

        # ── ventas.csv (mes vivo: evita marcar dormido a quien compró ahora) ──
        if VTAS_PATH.exists():
            v = pd.read_csv(VTAS_PATH, encoding="latin1", sep=";", engine="python")
            v["fecha"] = pd.to_datetime(v["FechaComprobante"], dayfirst=True, errors="coerce")
            v["importe"] = pd.to_numeric(v["ImporteNetoItem"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
            v["cant"] = pd.to_numeric(v.get("CantBase", pd.Series(["0"] * len(v))).astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0)
            v = v[~v["CodVendedor"].isin(EXCLUIR) & v["importe"].notna() & (v["importe"] > 0)].copy()
            if not v.empty:
                v["litros"] = v["cant"] * v["Articulo"].map(_litros_por_unidad)
                partes.append(pd.DataFrame({
                    "cliente_id": pd.to_numeric(v["Cliente"], errors="coerce"),
                    "cliente_nombre": v["RazonSocial"].astype(str) if "RazonSocial" in v.columns else "",
                    "vendedor_codigo": pd.to_numeric(v["CodVendedor"], errors="coerce"),
                    "vendedor_nombre": v["Vendedor"].astype(str) if "Vendedor" in v.columns else "",
                    "fecha": v["fecha"], "importe": v["importe"], "litros": v["litros"],
                }))

        allp = pd.concat(partes, ignore_index=True).dropna(subset=["cliente_id", "fecha"])
        if allp.empty:
            return _vacio()
        allp["cliente_id"] = allp["cliente_id"].astype(int)

        hoy = pd.Timestamp.today().normalize()
        allp = allp.sort_values("fecha")
        last = allp.groupby("cliente_id").tail(1).set_index("cliente_id")   # último comprobante (vendedor/nombre)
        agg = (allp.groupby("cliente_id")
               .agg(ultima_compra=("fecha", "max"),
                    importe_anterior=("importe", "sum"),
                    litros_anterior=("litros", "sum"))
               .reset_index())
        agg["dias_sin_compra"] = (hoy - agg["ultima_compra"]).dt.days
        dorm = agg[agg["dias_sin_compra"] > DIAS_DORMIDO].copy()
        if dorm.empty:
            return _vacio()

        dorm["cliente_nombre"]  = dorm["cliente_id"].map(last["cliente_nombre"])
        dorm["vendedor_codigo"] = pd.to_numeric(dorm["cliente_id"].map(last["vendedor_codigo"]), errors="coerce").fillna(0).astype(int)
        dorm["vendedor_nombre"] = dorm["cliente_id"].map(last["vendedor_nombre"])
        dorm["vendedor_codigo_str"] = "V" + dorm["vendedor_codigo"].astype(str)
        dorm = dorm.sort_values("importe_anterior", ascending=False)

        por_vend = (dorm.groupby(["vendedor_codigo_str", "vendedor_nombre"])
                    .agg(dormidos=("cliente_id", "count"),
                         importe_en_riesgo=("importe_anterior", "sum"),
                         litros_en_riesgo=("litros_anterior", "sum"))
                    .reset_index().rename(columns={"vendedor_codigo_str": "vendedor_codigo"})
                    .sort_values("importe_en_riesgo", ascending=False))
        top_por_vend = []
        for _, row in por_vend.iterrows():
            vc = row["vendedor_codigo"]
            top = dorm[dorm["vendedor_codigo_str"] == vc].head(3)   # top 3 por mayor volumen ($)
            top_por_vend.append({
                "vendedor_codigo": vc,
                "vendedor_nombre": row["vendedor_nombre"],
                "dormidos": int(row["dormidos"]),
                "importe_en_riesgo": round(float(row["importe_en_riesgo"]), 0),
                "litros_en_riesgo": round(float(row["litros_en_riesgo"]), 1),
                "top_clientes": [
                    {
                        "cliente_id": int(r["cliente_id"]),
                        "cliente_nombre": r["cliente_nombre"],
                        "ultima_compra": r["ultima_compra"].strftime("%Y-%m-%d"),
                        "importe_anterior": round(float(r["importe_anterior"]), 0),
                        "litros_anterior": round(float(r["litros_anterior"]), 1),
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
                "litros_anterior": round(float(r["litros_anterior"]), 1),
                "dias_sin_compra": int(r["dias_sin_compra"]),
            }
            for _, r in dorm.iterrows()
        ]

        return {
            "resumen": {
                "total_dormidos": len(dorm),
                "importe_en_riesgo": round(float(dorm["importe_anterior"].sum()), 0),
                "litros_en_riesgo": round(float(dorm["litros_anterior"].sum()), 1),
                "criterio_dias": DIAS_DORMIDO,
                "fecha_corte": hoy.strftime("%Y-%m-%d"),
                "fuente_historial": "historial_ventas_cliente.csv",
                "fuente_actual": "ventas.csv",
            },
            "por_vendedor": top_por_vend,
            "detalle": detalle,
        }
    except Exception:
        raise   # propaga al route, que responde 500 con el mensaje


@app.route("/api/gerencia/alertas_caida")
def gerencia_alertas_caida():
    """Clientes dormidos (JSON). `detalle` trae el listado COMPLETO."""
    try:
        return jsonify(_dormidos_payload())
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/gerencia/alertas_caida/export")
def gerencia_alertas_caida_export():
    """Descarga Excel (.xlsx) con el listado COMPLETO de clientes dormidos."""
    try:
        data = _dormidos_payload()
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    cols = ["cliente_id", "cliente_nombre", "vendedor_codigo", "vendedor_nombre",
            "ultima_compra", "dias_sin_compra", "importe_anterior", "litros_anterior"]
    df = pd.DataFrame(data.get("detalle", []), columns=cols).rename(columns={
        "cliente_id": "Cliente ID", "cliente_nombre": "Cliente",
        "vendedor_codigo": "Vendedor", "vendedor_nombre": "Nombre vendedor",
        "ultima_compra": "Última compra", "dias_sin_compra": "Días sin compra",
        "importe_anterior": "Importe anterior $", "litros_anterior": "Litros anteriores",
    })

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        df.to_excel(xl, index=False, sheet_name="Dormidos")
        ws = xl.sheets["Dormidos"]
        for i, col in enumerate(df.columns, start=1):
            if len(df):
                ancho = max(len(str(col)), int(df.iloc[:, i - 1].astype(str).map(len).max()))
            else:
                ancho = len(str(col))
            ws.column_dimensions[chr(64 + i)].width = min(max(ancho + 2, 10), 50)
    buf.seek(0)

    corte = data.get("resumen", {}).get("fecha_corte", "")
    fname = f"clientes_dormidos_{corte}.xlsx" if corte else "clientes_dormidos.xlsx"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ====== RUTA DEL DÍA (vendedor) ======
# 11 Titulares (marcas) — fuente ventas.csv (mes vivo). Mismos para Trad y Autoservicio.
_RUTA_ONCE = ["ALMA MORA", "TRAPICHE RESERVA", "FINCA LAS MORAS", "ALARIS", "DON DAVID",
              "DADA", "SMIRNOFF FLAVOURS", "LOS ARBOLES", "ANTARES", "SMIRNOFF ICE", "GORDON'S FLAVOURS"]
_RUTA_MARCA = {
    "ALMA MORA": "ALMA MORA", "ALARIS": "ALARIS", "TRAPICHE ALARIS": "ALARIS",
    "DON DAVID": "DON DAVID", "DADA": "DADA", "LOS ARBOLES": "LOS ARBOLES",
    "FINCA LAS MORAS": "FINCA LAS MORAS", "F LAS MORAS": "FINCA LAS MORAS",
    "TRAPICHE RESERVA": "TRAPICHE RESERVA", "ANTARES": "ANTARES",
    "GORDON'S FLAVOURS": "GORDON'S FLAVOURS", "GORDONS FLAVOURS": "GORDON'S FLAVOURS",
    "GORDON'S": "GORDON'S FLAVOURS", "GORDONS": "GORDON'S FLAVOURS",
    "SMIRNOFF": "SMIRNOFF FLAVOURS", "SMIRNOFF FLAVOURS": "SMIRNOFF FLAVOURS",
    "SMIRNOFF ICE FLAVOURS": "SMIRNOFF ICE", "SMIRNOFF ICE": "SMIRNOFF ICE",
}
_RUTA_ART = [
    ("SMIRNOFF ICE", "SMIRNOFF ICE"), ("SMF ICE", "SMIRNOFF ICE"),
    ("SMIRNOFF", "SMIRNOFF FLAVOURS"), ("GORDON", "GORDON'S FLAVOURS"),
    ("ANTARES", "ANTARES"), ("ALMA MORA", "ALMA MORA"), ("LOS ARBOLES", "LOS ARBOLES"),
    ("DADA", "DADA"), ("FINCA LAS MORAS", "FINCA LAS MORAS"), ("F.LAS MORAS", "FINCA LAS MORAS"),
    ("DON DAVID", "DON DAVID"), ("ALARIS", "ALARIS"), ("TRAPICHE RESERVA", "TRAPICHE RESERVA"),
]


def _ruta_titular(marca, articulo):
    m = str(marca).upper().strip()
    if m in _RUTA_MARCA:
        return _RUTA_MARCA[m]
    a = str(articulo).upper()
    for kw, t in _RUTA_ART:
        if kw in a:
            return t
    return None


@app.route("/api/vendedor/<vid>/ruta")
def vendedor_ruta(vid):
    """Ruta del día del vendedor. Cartera de clientes.xlsx (DiasVisita = día), con compra/sin
    compra y 11 Titulares faltantes calculados desde ventas.csv (mes vivo). Solo los 11 titulares."""
    vid_norm = normalizar_vendedor_codigo(vid)
    cn = clean_code(vid_norm)
    out = {"vendedor_id": vid_norm, "dia": "", "clientes": [], "total": 0,
           "con_compra": 0, "sin_compra": 0}
    cli_path = INPUTS / "clientes.xlsx"
    if not cli_path.exists():
        return jsonify(out), 200
    dia_req = request.args.get("dia", "").strip()
    if not dia_req:
        _DIAS_AR = {0: "LU", 1: "MA", 2: "MI", 3: "JU", 4: "VI", 5: "SA", 6: "DO"}
        dia_req = _DIAS_AR[datetime.now(_ARG_TZ).weekday()]
    out["dia"] = dia_req
    try:
        cli = pd.read_excel(cli_path)
    except Exception:
        return jsonify(out), 200
    cli.columns = [str(c).strip() for c in cli.columns]
    if not {"DiasVisita", "Codigo", "codven"}.issubset(cli.columns):
        return jsonify(out), 200
    cli = cli[cli["DiasVisita"].astype(str).str.strip().str.upper() == dia_req.upper()]
    cli = cli[cli["codven"].astype(str).apply(clean_code) == cn]
    if cli.empty:
        return jsonify(out), 200

    # Catálogo de innovaciones por segmento (fuente oficial: mod_innovaciones_segmento.csv)
    inov_seg = read_csv(DATASETS / "mod_innovaciones_segmento.csv")
    inov_by_seg = {}   # segmento -> {producto_codigo: producto_nombre}
    if not inov_seg.empty:
        inov_seg.columns = [c.lstrip("﻿") for c in inov_seg.columns]
        for _, ir in inov_seg.iterrows():
            cod_i = pd.to_numeric(ir.get("producto_codigo"), errors="coerce")
            if pd.isna(cod_i):
                continue
            segn = str(ir.get("segmento", "")).upper()
            inov_by_seg.setdefault(segn, {})[int(cod_i)] = str(ir.get("producto_nombre", "") or int(cod_i))
    inov_codes = set().union(*[set(d) for d in inov_by_seg.values()]) if inov_by_seg else set()

    # ventas.csv (mes vivo): clientes con compra + titulares e innovaciones compradas por cliente
    bought_clients, tit_cli, inov_cli = set(), {}, {}
    vpath = INPUTS / "ventas.csv"
    if vpath.exists():
        try:
            v = pd.read_csv(vpath, sep=";", encoding="latin1", engine="python")
            v["imp"] = pd.to_numeric(v["ImporteNetoItem"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
            # Solo Peñaflor (excluye P&P Logística) y vendedores no de ruta (V1/V2/V5/V20)
            if "Empresa" in v.columns:
                v = v[v["Empresa"].astype(str).str.strip() == "Empresa"]
            v = v[(v["imp"] > 0) & (~v["CodVendedor"].isin(_VENDEDORES_EXCLUIDOS))]
            v["cli"] = pd.to_numeric(v["Cliente"], errors="coerce")
            bought_clients = set(v["cli"].dropna().astype(int))
            v["_tit"] = [_ruta_titular(m, a) for m, a in zip(v.get("Marca", ""), v.get("Articulo", ""))]
            for cid, grp in v[v["_tit"].notna()].dropna(subset=["cli"]).groupby("cli"):
                tit_cli[int(cid)] = set(grp["_tit"])
            if inov_codes:
                v["_cod"] = pd.to_numeric(v.get("Codigo"), errors="coerce")
                for cid, grp in v[v["_cod"].isin(inov_codes)].dropna(subset=["cli"]).groupby("cli"):
                    inov_cli[int(cid)] = set(grp["_cod"].dropna().astype(int))
        except Exception:
            pass

    sub_col = next((c for c in cli.columns if "subseg" in c.lower() or "subramo" in c.lower()), None)
    nombre_col = next((c for c in cli.columns if c.lower().replace("_", "") in ("razonsocial", "nombre")), None)
    once_set = set(_RUTA_ONCE)
    clientes = []
    for _, r in cli.iterrows():
        if pd.isna(r.get("Codigo")):
            continue
        cid = int(r["Codigo"])
        seg = _clasificar_segmento(str(r.get("Ramo", "")), str(r.get(sub_col, "") if sub_col else ""))
        # V3 (Nadia): solo Tradicional almacén/despensa/kiosco. Quedan fuera AS, On Premise
        # y también los tradicionales que NO son almacén/despensa/kiosco (fiambrería, resto).
        if vid_norm == "V3":
            subseg = str(r.get(sub_col, "")).upper() if sub_col else ""
            es_alm_kio = any(k in subseg for k in ("ALMACEN", "DESPENSA", "KIOSCO"))
            if seg.upper() != "TRADICIONAL" or not es_alm_kio:
                continue
        comp = cid in bought_clients
        tb = tit_cli.get(cid, set()) & once_set
        comp_11 = [t for t in _RUTA_ONCE if t in tb]
        faltan = [t for t in _RUTA_ONCE if t not in tb]
        # Innovaciones aplicables al segmento del cliente (V3 sin AUTOSERVICIO)
        seg_u = seg.upper()
        cat_inov = {} if (vid_norm == "V3" and seg_u == "AUTOSERVICIO") else inov_by_seg.get(seg_u, {})
        bought_inov = inov_cli.get(cid, set())
        inov_comp = sorted({cat_inov[c] for c in cat_inov if c in bought_inov})
        inov_falt = sorted({cat_inov[c] for c in cat_inov if c not in bought_inov})
        orden_val = pd.to_numeric(r.get("Orden"), errors="coerce")
        clientes.append({
            "cliente_id": cid,
            "cliente_nombre": str(r.get(nombre_col, "") or cid) if nombre_col else str(cid),
            "vendedor_id": vid_norm,
            "dia_visita": dia_req,
            "segmento": seg,
            "orden": int(orden_val) if pd.notnull(orden_val) else None,
            "estado": "COBERTURA_OK" if comp else "SIN_COMPRA_MES",
            "compra_mes_flag": 1 if comp else 0,
            "once_t_comprados": len(tb),
            "once_t_total": len(_RUTA_ONCE),
            "titulares_comprados": comp_11,
            "faltan_11t": len(faltan),
            "titulares_faltantes": faltan,
            "inov_comprados": inov_comp,
            "inov_faltantes": inov_falt,
            "inov_comprados_n": len(inov_comp),
            "inov_total": len(cat_inov),
        })
    # Orden de visita (columna Orden de clientes.xlsx). Orden<=0 = sin asignar → al final.
    def _orden_key(c):
        o = c["orden"]
        tiene = o is not None and o > 0
        return (not tiene, o if tiene else 0, c["cliente_nombre"])
    clientes.sort(key=_orden_key)
    out["clientes"] = clientes
    out["total"] = len(clientes)
    out["con_compra"] = sum(1 for c in clientes if c["compra_mes_flag"])
    out["sin_compra"] = sum(1 for c in clientes if not c["compra_mes_flag"])
    return jsonify(out), 200


# ====== OPORTUNIDADES DEL DÍA: innovaciones ======
@app.route("/api/vendedor/<vid>/oportunidades_innovacion")
def vendedor_oportunidades_innovacion(vid):
    """3 clientes de la ZONA DE HOY que compraron el mes pasado y este mes, pero NUNCA
    innovaciones (ni el mes anterior ni el actual). Fuente: ventas_acumulada.csv (mayo+junio)."""
    import random as _random
    vid_norm = normalizar_vendedor_codigo(vid)
    cn = clean_code(vid_norm)
    vacio = {"vendedor_nombre": vid_norm, "clientes": [], "innovaciones": [], "texto": ""}
    if vid_norm in ("V2", "V5", "V20"):
        return jsonify(vacio), 200

    # nombre del vendedor
    vendedor_nombre = vid_norm
    vend = read_csv(CONFIG / "vendedores_activos.csv")
    if not vend.empty and "codigo_vendedor" in vend.columns:
        fila = vend[vend["codigo_vendedor"].astype(str).apply(clean_code) == cn]
        if not fila.empty:
            col_n = next((c for c in ("nombre", "nombre_vendedor", "vendedor") if c in fila.columns), None)
            if col_n:
                vendedor_nombre = str(fila.iloc[0][col_n])
    vacio["vendedor_nombre"] = vendedor_nombre

    inv = read_csv(DATASETS / "mod_innovaciones_segmento.csv")
    vac_path = INPUTS / "ventas_acumulada.csv"
    if inv.empty or not vac_path.exists():
        return jsonify(vacio), 200
    innov_codes = set(pd.to_numeric(inv["producto_codigo"], errors="coerce").dropna().astype(int))
    innov_names = sorted(set(str(x) for x in inv["producto_nombre"].dropna() if str(x).strip()))

    try:
        vac = pd.read_csv(vac_path, sep=";", encoding="latin1", low_memory=False)
    except Exception:
        return jsonify(vacio), 200
    vac["imp"] = pd.to_numeric(vac["ImporteNetoItem"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    if "Empresa" in vac.columns:  # solo Peñaflor, excluye P&P Logística
        vac = vac[vac["Empresa"].astype(str).str.strip() == "Empresa"]
    vac = vac[(vac["imp"] > 0) & (vac["CodVendedor"].astype(str).apply(clean_code) == cn)]
    if vac.empty:
        return jsonify(vacio), 200
    vac["cod"] = pd.to_numeric(vac["Codigo"], errors="coerce")
    vac["cli"] = pd.to_numeric(vac["Cliente"], errors="coerce")
    vac["mes"] = pd.to_datetime(vac["FechaComprobante"], dayfirst=True, errors="coerce").dt.to_period("M")
    per_act = vac["mes"].max()
    per_ant = per_act - 1
    cur, prev = vac[vac["mes"] == per_act], vac[vac["mes"] == per_ant]
    prev_any = set(prev["cli"].dropna().astype(int))
    prev_inov = set(prev[prev["cod"].isin(innov_codes)]["cli"].dropna().astype(int))
    cur_any = set(cur["cli"].dropna().astype(int))
    cur_inov = set(cur[cur["cod"].isin(innov_codes)]["cli"].dropna().astype(int))
    # compró ambos meses, pero sin innovaciones en ninguno
    cand = (prev_any - prev_inov) & (cur_any - cur_inov)

    # clientes de la zona de HOY
    dia_req = request.args.get("dia", "").strip()
    if not dia_req:
        _DIAS_AR = {0: "LU", 1: "MA", 2: "MI", 3: "JU", 4: "VI", 5: "SA", 6: "DO"}
        dia_req = _DIAS_AR[datetime.now(_ARG_TZ).weekday()]
    try:
        cd = _clientes_por_dia(dia_req)
        if not cd.empty and "cliente_id" in cd.columns:
            dia_ids = set(pd.to_numeric(cd["cliente_id"], errors="coerce").dropna().astype(int))
            cand = cand & dia_ids
    except Exception:
        pass

    innov3 = _random.sample(innov_names, min(3, len(innov_names))) if innov_names else []
    if not cand:
        return jsonify({"vendedor_nombre": vendedor_nombre, "dia": dia_req,
                        "clientes": [], "innovaciones": innov3, "texto": ""}), 200

    # top 3 por volumen ($ acumulado mayo+junio)
    vol = vac[vac["cli"].isin(cand)].groupby("cli")["imp"].sum().sort_values(ascending=False)
    nm = vac[vac["cli"].isin(cand)].dropna(subset=["cli"]).drop_duplicates("cli")
    nombres = dict(zip(nm["cli"].astype(int), nm["RazonSocial"].astype(str))) if "RazonSocial" in vac.columns else {}
    top3 = [int(c) for c in vol.index[:3]]
    clientes = [{"cliente_id": cid, "cliente_nombre": nombres.get(cid, str(cid)),
                 "importe": round(float(vol.get(cid, 0)), 0)} for cid in top3]

    nombres_cli = ", ".join(c["cliente_nombre"] for c in clientes)
    marcas_txt = ", ".join(innov3)
    texto = (f"Hoy {vendedor_nombre}, andá a venderles innovaciones a estos {len(clientes)} clientes: "
             f"{nombres_cli}. El mes pasado hicieron compra, al igual que este mes, pero todavía "
             f"no compraron estas marcas: {marcas_txt}.")
    return jsonify({"vendedor_nombre": vendedor_nombre, "dia": dia_req,
                    "clientes": clientes, "innovaciones": innov3, "texto": texto}), 200


# ====== INCENTIVO CLUB FARO ======
# Objetivos: 01_INPUTS/incentivo_club_faro*.xlsx (3 categorías × vendedor + supervisores).
# Avance (logrado) y no-compradores: ventas_acumulada.csv filtrado a mayo+junio.
# Segmento por Ramo+Subramo de la venta (Autoservicio = autoservicio + autoservicio tradicional).
#   alaris_flm → Tradicional, umbral 3 botellas, 1 CCC/cliente (Marca ALARIS/FINCA LAS MORAS/PAZ DE FLM)
#   antares    → Autoservicio, cobertura POR SKU sin umbral; XPA/Porrón330/Botella660 (60020/21/22) doble
#   smirnoff   → Autoservicio, umbral 6, 1 CCC/cliente (familia Smirnoff botella 700cc, excluye RTD/Ice)
_FARO_SUP_MAP = {"Esteban": [3, 4, 6, 8, 10], "Raul": [7, 9]}
_FARO_CATS = ("alaris_flm", "antares", "smirnoff")
_FARO_CAT_NOMBRE = {"alaris_flm": "Alaris + Finca Las Moras", "antares": "Antares", "smirnoff": "Familia Smirnoff"}
_FARO_CAT_SEG = {"alaris_flm": "TRADICIONAL", "antares": "AUTOSERVICIO", "smirnoff": "AUTOSERVICIO"}
_FARO_CAT_UMBRAL = {"alaris_flm": 3, "antares": 6, "smirnoff": 6}
# Antares: cobertura por SKU (sin umbral). XPA / Lager Porrón 330 / Lager Botella 660 suman doble.
_FARO_ANTARES_DOBLE = {"60020", "60021", "60022"}
# Premios por defecto (millas) si no se pueden parsear del xlsx (fila "PREMIOS").
_FARO_PREMIOS_DEFAULT = {"alaris_flm": 2000, "antares": 1000, "smirnoff": 1000}


def _faro_xlsx_path():
    cands = sorted(INPUTS.glob("incentivo_club_faro*.xlsx"))
    return cands[0] if cands else None


def _faro_objetivos():
    """{cod_vend(int): {alaris_flm, antares, smirnoff}} desde el xlsx (filas vendedor)."""
    p = _faro_xlsx_path()
    obj = {}
    if not p:
        return obj
    try:
        raw = pd.read_excel(p, sheet_name="Hoja1", header=None, dtype=str)
        for ri in range(3, 10):
            c0 = str(raw.iat[ri, 0]).strip()
            if not c0.isdigit():
                continue
            obj[int(c0)] = {
                "alaris_flm": int(float(raw.iat[ri, 1])),
                "antares":    int(float(raw.iat[ri, 2])),
                "smirnoff":   int(float(raw.iat[ri, 3])),
            }
    except Exception:
        pass
    return obj


def _faro_premios():
    """Millas por categoría desde la fila 'PREMIOS' del xlsx (texto libre).
    Ej: 'PREMIOS: ... FAMILIA SMIRNOFF (1000 MILLAS), ANTARES (1000 MILLAS) Y ALARIS +FLM (2000 MILLAS)'.
    Devuelve {cat: millas}. Si no se puede parsear → _FARO_PREMIOS_DEFAULT."""
    import re as _re
    p = _faro_xlsx_path()
    premios = dict(_FARO_PREMIOS_DEFAULT)
    if not p:
        return premios
    try:
        raw = pd.read_excel(p, sheet_name="Hoja1", header=None, dtype=str)
        txt = " ".join(str(v) for v in raw.values.ravel()
                       if pd.notna(v) and "MILLA" in str(v).upper())
        if not txt:
            return premios
        found = {}
        # Cada bloque "<etiqueta> (<n> MILLAS)"
        for etq, num in _re.findall(r"([A-Za-zÁÉÍÓÚÑ +&]+?)\s*\(\s*([\d.]+)\s*MILLAS\)", txt, _re.IGNORECASE):
            e = etq.upper()
            millas = int(float(num.replace(".", "")))
            if "SMIRNOFF" in e:
                found["smirnoff"] = millas
            elif "ANTARES" in e:
                found["antares"] = millas
            elif "ALARIS" in e or "FLM" in e or "FINCA" in e:
                found["alaris_flm"] = millas
        if found:
            premios.update(found)
    except Exception:
        pass
    return premios


_FARO_VENTAS_CACHE = {}
def _faro_ventas():
    """ventas_acumulada.csv (mayo+junio) preparada para FARO, cacheada por mtime.
    Columnas calc: _neto,_cant,_vend,_cli,_seg,_cat,_w (peso Antares),_clinom,_loc."""
    p = INPUTS / "ventas_acumulada.csv"
    if not p.exists():
        return pd.DataFrame()
    try:
        key = os.path.getmtime(p)
    except OSError:
        key = 0
    df = _FARO_VENTAS_CACHE.get(key)
    if df is not None:
        return df
    df = pd.read_csv(p, sep=";", encoding="latin1", low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df["_fecha"] = pd.to_datetime(df.get("FechaComprobante"), dayfirst=True, errors="coerce")
    df["_neto"] = pd.to_numeric(df["ImporteNetoItem"].astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0)
    df["_cant"] = pd.to_numeric(df["CantBase"].astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0)
    df["_vend"] = pd.to_numeric(df["CodVendedor"], errors="coerce")
    df["_cli"]  = pd.to_numeric(df["Cliente"], errors="coerce")
    df = df[(df["_neto"] > 0) & (~df["_vend"].isin(_VENDEDORES_EXCLUIDOS))].copy()
    df = df[df["_fecha"].dt.month.isin([5, 6])].copy()
    df["_seg"] = [_clasificar_segmento(str(r), str(s))
                  for r, s in zip(df.get("Ramo", ""), df.get("Subramo", ""))]
    mu = df["Marca"].astype(str).str.upper().str.strip()
    au = df["Articulo"].astype(str).str.upper()
    cod = df.get("Codigo", pd.Series([""] * len(df), index=df.index)).astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df["_cod"] = cod   # código de SKU normalizado, para el conteo Antares por SKU
    cat = pd.Series([None] * len(df), index=df.index, dtype=object)
    cat[mu.isin(["ALARIS", "FINCA LAS MORAS", "PAZ DE FINCA LAS MORAS"])] = "alaris_flm"
    cat[mu.str.startswith("ANTARES")] = "antares"
    smirnoff_700 = (mu == "SMIRNOFF") & au.str.contains("700", regex=False, na=False)
    cat[smirnoff_700] = "smirnoff"   # familia Smirnoff botella 700cc; excluye SMIRNOFF ICE / RTD lata
    df["_cat"] = cat
    # Antares: XPA (60020) / Lager Porrón 330 (60021) / Lager Botella 660 (60022) suman doble.
    doble_antares = mu.str.startswith("ANTARES") & cod.isin(_FARO_ANTARES_DOBLE)
    df["_w"] = [2 if x else 1 for x in doble_antares]
    df["_art"] = au   # nombre de artículo (para drill-down de SKU)
    df["_clinom"] = (df["RazonSocial"].astype(str) if "RazonSocial" in df.columns else df["Cliente"].astype(str))
    df["_loc"] = (df["Localidad"].astype(str) if "Localidad" in df.columns else pd.Series([""] * len(df), index=df.index))
    _FARO_VENTAS_CACHE.clear()
    _FARO_VENTAS_CACHE[key] = df
    return df


def _faro_detalle_vendedor(df, cod):
    """Por categoría: {logrado, no_compradores:[...]} para un vendedor (CodVendedor=cod).
    Logrado: alaris_flm/smirnoff = 1 CCC por cliente que alcanza el umbral; antares = por SKU
    SIN umbral — cada SKU distinto de Antares que el cliente compró suma 1, y XPA/Porrón330/
    Botella660 (60020/21/22) suman 2, sin tope por cliente. No-compradores = clientes del canal
    a los que el vendedor vendió en el bimestre y NO cubrieron la marca (Antares: 0 SKU)."""
    out = {}
    dv = df[df["_vend"] == cod] if not df.empty else df
    for cat in _FARO_CATS:
        seg = _FARO_CAT_SEG[cat]
        um  = _FARO_CAT_UMBRAL[cat]
        canal = dv[dv["_seg"] == seg]
        canal_ids = set(canal["_cli"].dropna().astype(int))
        marca = canal[canal["_cat"] == cat]
        bot_cli = marca.groupby("_cli")["_cant"].sum()
        cubiertos = set(bot_cli[bot_cli >= um].index.astype(int))
        meta = canal.groupby("_cli").agg(nom=("_clinom", "first"), loc=("_loc", "first"))
        bot_map = bot_cli.to_dict()
        def _cli_row(cid):
            return {
                "cliente":        int(cid),
                "razon_social":   str(meta["nom"].get(cid, "")).strip()[:45],
                "localidad":      str(meta["loc"].get(cid, "")).strip()[:25],
                "botellas_marca": round(float(bot_map.get(cid, 0)), 1),
                "peso":           1,
            }
        if cat == "antares":
            # Cobertura por SKU, SIN umbral: cada SKU distinto de Antares que el cliente
            # compró suma 1; XPA / Lager Porrón 330 / Lager Botella 660 (60020/21/22) suman 2.
            # Sin tope por cliente (ej: 1 Lager lata + 1 XPA = 1 + 2 = 3 coberturas).
            sku = marca.drop_duplicates(subset=["_cli", "_cod"])
            peso_cli = sku.groupby("_cli")["_w"].sum()          # cobertura total por cliente
            cubiertos = set(peso_cli.index.dropna().astype(int)) # clientes con ≥1 SKU Antares
            ach_ids = cubiertos
            logrado = int(peso_cli.sum())
            pesomap = peso_cli.to_dict()
            compradores = sorted(
                ({**_cli_row(c), "peso": int(pesomap.get(c, 1))} for c in cubiertos),
                key=lambda x: (-x["peso"], -x["botellas_marca"], x["cliente"]))
        else:
            logrado = len(cubiertos)
            ach_ids = cubiertos
            # Clientes CON cobertura lograda (drill-down de gerencia/vendedor)
            compradores = sorted((_cli_row(c) for c in ach_ids),
                                 key=lambda x: (-x["botellas_marca"], x["cliente"]))
        # No-compradores: clientes del canal del vendedor que no cubrieron la marca
        no_comp = sorted((_cli_row(c) for c in (canal_ids - cubiertos)),
                         key=lambda x: (-x["botellas_marca"], x["cliente"]))
        out[cat] = {
            "logrado": logrado,
            "clientes_cubiertos": int(len(ach_ids)),
            "compradores": compradores,
            "no_compradores": no_comp,
        }
    return out


def _faro_nombres_vendedores():
    vend = read_csv(CONFIG / "vendedores_activos.csv")
    m = {}
    if not vend.empty:
        for _, v in vend.iterrows():
            try:
                m[int(clean_code(str(v["codigo_vendedor"])))] = str(v["nombre_vendedor"]).strip()
            except (ValueError, TypeError):
                pass
    return m


@app.route("/api/gerencia/incentivo_faro")
def gerencia_incentivo_faro():
    """Incentivo Club FARO — objetivo vs logrado por vendedor y supervisor (gerencia)."""
    obj = _faro_objetivos()
    df = _faro_ventas()
    nombres = _faro_nombres_vendedores()
    premios = _faro_premios()
    logr = {cod: _faro_detalle_vendedor(df, cod) for cod in obj}

    def _cat_block(o_dict, l_dict):
        b = {"_millas_alcanzadas": 0, "_millas_posibles": 0}
        for cat in _FARO_CATS:
            o = o_dict.get(cat, 0)
            l = l_dict.get(cat, {}).get("logrado", 0)
            millas = premios.get(cat, 0)
            alcanzado = bool(o) and l >= o
            if o:   # solo categorías en juego (con objetivo asignado) cuentan para millas posibles
                b["_millas_posibles"] += millas
                if alcanzado:
                    b["_millas_alcanzadas"] += millas
            b[cat] = {"objetivo": o, "logrado": l, "pct": round(l / o * 100, 1) if o else None,
                      "premio_millas": millas, "alcanzado": alcanzado,
                      "clientes_cubiertos": l_dict.get(cat, {}).get("clientes_cubiertos", 0),
                      "compradores": l_dict.get(cat, {}).get("compradores", [])}
        return b

    def _finalize(row, b):
        row["millas_alcanzadas"] = b.pop("_millas_alcanzadas")
        row["millas_posibles"]   = b.pop("_millas_posibles")
        row.update(b)
        return row

    vendedores = []
    for cod in sorted(obj):
        row = {"codigo": cod, "nombre": nombres.get(cod, f"V{cod}"), "tipo": "vendedor"}
        vendedores.append(_finalize(row, _cat_block(obj[cod], logr.get(cod, {}))))

    supervisores = []
    for nom, vends in _FARO_SUP_MAP.items():
        o_sum = {cat: sum(obj.get(v, {}).get(cat, 0) for v in vends) for cat in _FARO_CATS}
        l_sum = {cat: {"logrado": sum(logr.get(v, {}).get(cat, {}).get("logrado", 0) for v in vends)} for cat in _FARO_CATS}
        row = {"nombre": nom, "tipo": "supervisor", "vendedores": [f"V{v}" for v in vends]}
        supervisores.append(_finalize(row, _cat_block(o_sum, l_sum)))

    return jsonify(_to_native({
        "vendedores": vendedores, "supervisores": supervisores,
        "categorias": _FARO_CAT_NOMBRE, "premios": premios, "fuente": "ventas_acumulada.csv",
        "periodo": "mayo-junio", "objetivo_fuente": (_faro_xlsx_path().name if _faro_xlsx_path() else None),
    }))


@app.route("/api/vendedor/<vid>/incentivo_faro")
def vendedor_incentivo_faro(vid):
    """Incentivo Club FARO del vendedor: objetivo vs logrado + clientes no compradores por categoría."""
    import re as _re
    cod = int(_re.sub(r"\D", "", vid) or 0)
    obj = _faro_objetivos().get(cod, {c: 0 for c in _FARO_CATS})
    df = _faro_ventas()
    premios = _faro_premios()
    det = _faro_detalle_vendedor(df, cod)
    es_v3 = (cod == 3)
    categorias = []
    millas_alcanzadas = 0
    millas_posibles = 0
    for cat in _FARO_CATS:
        # V3 no trabaja Autoservicio → solo categorías de canal tradicional
        if es_v3 and _FARO_CAT_SEG[cat] != "TRADICIONAL":
            continue
        o = obj.get(cat, 0)
        l = det.get(cat, {}).get("logrado", 0)
        millas = premios.get(cat, 0)
        alcanzado = bool(o) and l >= o
        if o:   # solo categorías con objetivo asignado cuentan para millas posibles
            millas_posibles += millas
            if alcanzado:
                millas_alcanzadas += millas
        categorias.append({
            "cat": cat, "nombre": _FARO_CAT_NOMBRE[cat],
            "segmento": "Tradicional" if cat == "alaris_flm" else "Autoservicio",
            "umbral": (None if cat == "antares" else _FARO_CAT_UMBRAL[cat]),
            "objetivo": o, "logrado": l, "pct": round(l / o * 100, 1) if o else None,
            "premio_millas": millas, "alcanzado": alcanzado,
            "clientes_cubiertos": det.get(cat, {}).get("clientes_cubiertos", 0),
            "compradores": det.get(cat, {}).get("compradores", []),
            "no_compradores": det.get(cat, {}).get("no_compradores", []),
        })
    return jsonify(_to_native({
        "vendedor": vid, "codigo": cod, "categorias": categorias,
        "millas_alcanzadas": millas_alcanzadas, "millas_posibles": millas_posibles,
        "premios": premios, "fuente": "ventas_acumulada.csv", "periodo": "mayo-junio",
    }))


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

    # Objetivos y acumulado del MES CERRADO desde resultado_mes.xlsx (fuente primaria).
    # resultado_mes.xlsx = acumulado congelado del mes cerrado (Acumulado == Tendencia).
    # resultado.xlsx (vivo, mes en curso) solo se usa como fallback si no existe el cierre.
    obj_por_vend = {}
    fuente_objetivos = None
    resultado_mes_path = INPUTS / "resultado_mes.xlsx"
    resultado_path     = INPUTS / "resultado.xlsx"
    fuente_path = resultado_mes_path if resultado_mes_path.exists() else resultado_path
    if fuente_path.exists():
        try:
            avance_df = pd.read_excel(fuente_path, sheet_name="Avance")
            for _, r in avance_df.iterrows():
                cn = clean_code(str(r.get("VendedorCodigo", "")))
                if not cn or int(cn) in _VENDEDORES_EXCLUIDOS:
                    continue
                obj_por_vend[cn] = {
                    "nombre": str(r.get("VendedorNombre", "")).strip().title(),
                    "objetivo": float(r.get("ValorObjetivo", 0) or 0),
                    "acumulado": float(r.get("Acumulado", 0) or 0),
                }
            fuente_objetivos = fuente_path.name
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
        # Leer ventas_mes.csv con lector específico (sep=',' explícito, no sep=None).
        # incluir_deposito=True: conserva V20 para separar ruta vs Depósito (paridad con el vivo).
        so_df = _leer_ventas_mes_csv(so_src, incluir_deposito=True)
        sellout["filas_ventas_mes"] = len(so_df)
        if so_df.empty:
            sellout["error"] = "ventas_mes.csv sin filas válidas (importe>0, excl V2/V5)"
        else:
            # Mismo cruce ventas × maestro 04D que generó auditoria_sellout_cierre_mes.csv,
            # más el bloque Depósito V20 aparte (sin objetivo).
            try:
                sellout.update(_sellout_con_deposito(so_df))
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
        "fuente_objetivos": fuente_objetivos or "resultado.xlsx",
        "fuente_ccc":       "ventas_acumulada.csv",
    })


# ====== CIERRE VERSIONADO POR CARPETA (01_INPUTS/cierres mes/) ======
# Cada cierre es autocontenido en 3 archivos versionados por _MMAAAA:
#   resultado_mes_<MMAAAA>.xlsx   → objetivo/acumulado/avance por vendedor
#   ventas_mes_<MMAAAA>.csv       → CCC, 11T (y luego sell-out/planes/acciones/innov)
#   objetivo 11T_<MMAAAA>.xlsx    → objetivo del 11T por marca
# Catálogos compartidos (maestro 04D, escala, acciones, innovaciones) NO van acá.
CIERRES_MES_DIR = INPUTS / "cierres mes"

_MARCA_LKP_CIERRE = {
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
_ART_KW_11T_CIERRE = [
    ("SMIRNOFF ICE", "SMIRNOFF ICE"), ("SMF ICE", "SMIRNOFF ICE"),
    ("SMIRNOFF", "SMIRNOFF FLAVOURS"), ("GORDON", "GORDON'S FLAVOURS"),
    ("ANTARES", "ANTARES"), ("CAZADOR", "CAZADOR"),
    ("FOND DE CAVE", "FOND DE CAVE"), ("ALMA MORA", "ALMA MORA"),
    ("LOS ARBOLES", "LOS ARBOLES"), ("DADA", "DADA"),
    ("FINCA LAS MORAS", "FINCA LAS MORAS"), ("DON DAVID", "DON DAVID"),
    ("ALARIS", "ALARIS"), ("TRAPICHE RESERVA", "TRAPICHE RESERVA"),
    ("JW BLACK", "JW BLACK"), ("JW RED", "JW RED"),
]
_OBJ_ALIAS_11T_CIERRE = {
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


_VENTAS_MES_CACHE = {}
def _leer_ventas_mes_cacheado(path, incluir_deposito=False):
    """Lee ventas_mes versionado con caché (archivos del cierre = inmutables, clave path+mtime).
    Evita releer el CSV (3MB, parser python) varias veces por request → era la causa de los ~31s.
    incluir_deposito entra en la clave de caché: la variante con V20 (sell out) no contamina
    la variante sin V20 que usan CCC/once_titulares/ranking del cierre."""
    try:
        key = (str(path), os.path.getmtime(path), incluir_deposito)
    except OSError:
        key = (str(path), 0, incluir_deposito)
    df = _VENTAS_MES_CACHE.get(key)
    if df is None:
        df = _leer_ventas_mes_csv(path, incluir_deposito=incluir_deposito)
        _VENTAS_MES_CACHE[key] = df
    return df


def _to_native(o):
    """Convierte recursivamente numpy/pandas → tipos nativos de Python. El JSON provider de
    Flask no serializa numpy.int64/float64 (causaba HTTP 500 en Render aunque local funcionara)."""
    import numpy as _np
    if isinstance(o, dict):
        return {k: _to_native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_to_native(x) for x in o]
    if isinstance(o, _np.generic):
        return o.item()
    return o


def _cierre_archivos_mes(periodo):
    """periodo 'AAAA-MM' → dict con los 3 archivos del cierre versionado, o None si faltan."""
    try:
        y, m = periodo.split("-")
        mmaaaa = f"{int(m):02d}{int(y)}"
    except Exception:
        return None
    res   = CIERRES_MES_DIR / f"resultado_mes_{mmaaaa}.xlsx"
    vmes  = CIERRES_MES_DIR / f"ventas_mes_{mmaaaa}.csv"
    obj11 = CIERRES_MES_DIR / f"objetivo 11T_{mmaaaa}.xlsx"
    # 11T es bimestral → su fuente es ventas_acumulada_<MMAAAA>.csv (2 meses). Opcional:
    # si no existe, _cierre_once_titulares cae a ventas_mes (1 mes).
    vacum = CIERRES_MES_DIR / f"ventas_acumulada_{mmaaaa}.csv"
    if res.exists() and vmes.exists() and obj11.exists():
        return {"resultado": res, "ventas_mes": vmes, "objetivo_11t": obj11, "mmaaaa": mmaaaa,
                "ventas_acumulada": vacum if vacum.exists() else None}
    return None


def _cierre_ccc_por_vend_segmento(vmes_df):
    """CCC (clientes únicos, neto>0) por vendedor × segmento desde ventas_mes del cierre.
    Solo Peñaflor (Empresa=='Empresa'). V2/V5/V20 ya excluidos por _leer_ventas_mes_csv."""
    out = {}
    if vmes_df.empty:
        return out
    df = vmes_df
    if "Empresa" in df.columns:
        df = df[df["Empresa"].astype(str).str.strip() == "Empresa"]
    df = df.copy()
    df["_cli"]  = pd.to_numeric(df["Cliente"], errors="coerce")
    df["_vend"] = pd.to_numeric(df["CodVendedor"], errors="coerce")
    df["_seg"]  = [
        _clasificar_segmento(str(r), str(s))
        for r, s in zip(df.get("Ramo", pd.Series([""] * len(df))),
                        df.get("Subramo", pd.Series([""] * len(df))))
    ]
    df = df.dropna(subset=["_cli", "_vend"])
    for (vend, seg), grp in df.groupby([df["_vend"].astype(int), "_seg"]):
        cn = clean_code(str(int(vend)))
        out.setdefault(cn, {"TRADICIONAL": 0, "AUTOSERVICIO": 0, "ON_PREMISE_VTK": 0, "OTROS": 0})
        out[cn][seg] = int(grp["_cli"].nunique())
    return out


def _cierre_objetivos_avance(files):
    """objetivos_avance del cierre desde resultado_mes_<MMAAAA>.xlsx (obj/acum) + ventas_mes (CCC)."""
    obj_por_vend = {}
    av = pd.read_excel(files["resultado"], sheet_name="Avance")
    for _, r in av.iterrows():
        cn = clean_code(str(r.get("VendedorCodigo", "")))
        if not cn or int(cn) in _VENDEDORES_EXCLUIDOS:
            continue
        obj_por_vend[cn] = {
            "nombre":    str(r.get("VendedorNombre", "")).strip().title(),
            "objetivo":  float(r.get("ValorObjetivo", 0) or 0),
            "acumulado": float(r.get("Acumulado", 0) or 0),
        }

    ccc_por_vend = _cierre_ccc_por_vend_segmento(_leer_ventas_mes_cacheado(files["ventas_mes"]))

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
        ccc_trad = ccc.get("TRADICIONAL", 0)
        ccc_auto = 0 if cn == "3" else ccc.get("AUTOSERVICIO", 0)   # V3 no AS
        ccc_op   = 0 if cn == "3" else ccc.get("ON_PREMISE_VTK", 0) # V3 no On Premise
        ccc_total = ccc_trad + ccc_auto + ccc_op + ccc.get("OTROS", 0)
        vendedores.append({
            "codigo": cn, "nombre": ob.get("nombre") or nombre_config,
            "objetivo": objetivo, "acumulado": acumulado, "avance_pct": avance_pct,
            "faltante": round(objetivo - acumulado, 2),
            "ccc_total": ccc_total, "ccc_tradicional": ccc_trad,
            "ccc_autoservicio": ccc_auto, "ccc_onpremise": ccc_op,
        })
    vendedores.sort(key=lambda x: x["avance_pct"], reverse=True)

    empresa = {k: sum(v[k] for v in vendedores) for k in
               ("objetivo", "acumulado", "ccc_total", "ccc_tradicional",
                "ccc_autoservicio", "ccc_onpremise")}
    empresa["avance_pct"] = round(empresa["acumulado"] / empresa["objetivo"] * 100, 2) if empresa["objetivo"] else 0
    empresa["faltante"]   = round(empresa["objetivo"] - empresa["acumulado"], 2)

    dias_habiles = None
    try:
        from calendar import monthrange
        y, m = int(files["mmaaaa"][2:]), int(files["mmaaaa"][:2])
        cal = contar_dias_habiles(fecha_corte=datetime(y, m, monthrange(y, m)[1], 23, 59, 59))
        dias_habiles = cal.get("total")
    except Exception:
        pass

    return {
        "dias_habiles":     dias_habiles,
        "empresa":          empresa,
        "vendedores":       vendedores,
        "fuente_objetivos": files["resultado"].name,
        "fuente_acumulado": files["resultado"].name,
        "fuente_ccc":       files["ventas_mes"].name,
        "congelado_desde":  "01_INPUTS/cierres mes/ (versionado por archivo)",
    }


_VACUM_CIERRE_CACHE = {}
def _leer_ventas_acum_cierre(path):
    """Lee ventas_acumulada_<MMAAAA>.csv del cierre (sep=';', latin1) con caché.
    Mismo criterio que /api/gerencia/once_titulares: solo Peñaflor (Empresa=='Empresa',
    excluye P&P Logística), excluye V2/V5/V20 y filtra neto>0."""
    try:
        key = (str(path), os.path.getmtime(path))
    except OSError:
        key = (str(path), 0)
    df = _VACUM_CIERRE_CACHE.get(key)
    if df is None:
        df = pd.read_csv(path, sep=";", encoding="latin1", low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        df["ImporteNetoItem"] = pd.to_numeric(
            df["ImporteNetoItem"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
        if "Empresa" in df.columns:
            df = df[df["Empresa"].astype(str).str.strip() == "Empresa"]
        cv = pd.to_numeric(df["CodVendedor"], errors="coerce")
        df = df[(~cv.isin(_VENDEDORES_EXCLUIDOS)) & (df["ImporteNetoItem"] > 0)].copy()
        _VACUM_CIERRE_CACHE[key] = df
    return df


def _cierre_once_titulares(files):
    """11T CCC vs Objetivo del cierre. CCC = clientes únicos (neto>0) por marca titular,
    MISMO criterio que /api/gerencia/once_titulares. Fuente: ventas_acumulada_<MMAAAA>.csv
    (bimestral — el 11T se mide en 2 meses); fallback a ventas_mes si no existe la acumulada.
    Objetivo: objetivo 11T_<MMAAAA>.xlsx."""
    obj_map = {}
    try:
        odf = pd.read_excel(files["objetivo_11t"], header=1)
        odf = odf.dropna(subset=odf.columns[1:2])
        for _, r in odf.iterrows():
            raw = str(r.iloc[1]).upper().strip()
            mk = _OBJ_ALIAS_11T_CIERRE.get(raw, raw)
            try:
                obj_map[mk] = int(float(r.iloc[2]))
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    ccc_map = {}
    # Fuente bimestral (ventas_acumulada) si está; si no, ventas_mes (1 mes). Ambos lectores
    # ya filtran neto>0, excluyen V2/V5/V20 y SOLO Peñaflor (Empresa=='Empresa', sin P&P
    # Logística) — igual criterio que el dashboard /api/gerencia/once_titulares.
    src_acum = files.get("ventas_acumulada")
    df = _leer_ventas_acum_cierre(src_acum) if src_acum is not None else _leer_ventas_mes_cacheado(files["ventas_mes"])
    if not df.empty:
        df = df.copy()
        # Garantizar solo Peñaflor con cualquier fuente (el lector de ventas_mes no filtra Empresa)
        if "Empresa" in df.columns:
            df = df[df["Empresa"].astype(str).str.strip() == "Empresa"]
        df["mo"] = df["Marca"].astype(str).str.upper().str.strip().map(_MARCA_LKP_CIERRE)
        for kw, mo in _ART_KW_11T_CIERRE:
            still = df["mo"].isna()
            if not still.any():
                break
            hits = df.loc[still, "Articulo"].astype(str).str.upper().str.contains(kw, regex=False, na=False)
            df.loc[still & hits, "mo"] = mo
        df["_cli"] = pd.to_numeric(df["Cliente"], errors="coerce")
        ccc_map = df[df["mo"].notna()].groupby("mo")["_cli"].nunique().to_dict()

    marcas, tot_ccc, tot_obj = [], 0, 0
    for mk in sorted(obj_map, key=lambda x: ccc_map.get(x, 0), reverse=True):
        ccc_v = int(ccc_map.get(mk, 0))
        obj_v = obj_map[mk]
        pct   = round(ccc_v / obj_v * 100, 1) if obj_v else None
        marcas.append({"marca": mk, "ccc": ccc_v, "objetivo": obj_v, "pct": pct})
        tot_ccc += ccc_v
        tot_obj += obj_v
    return {
        "marcas": marcas,
        "empresa": {
            "ccc_total": tot_ccc, "objetivo_total": tot_obj,
            "pct": round(tot_ccc / tot_obj * 100, 1) if tot_obj else 0,
            "marcas_sobre_objetivo": sum(1 for m in marcas if (m["pct"] or 0) >= 100),
            "total_marcas": len(marcas),
        },
    }


_GCM_MODULE = None
def _gcm():
    """Importa (cacheado) tools/generar_cierre_mensual.py para reutilizar el motor oficial
    de cálculo del cierre (litros, 11T, innovaciones, ranking) sobre un DataFrame."""
    global _GCM_MODULE
    if _GCM_MODULE is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "generar_cierre_mensual", str(BASE / "tools" / "generar_cierre_mensual.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _GCM_MODULE = mod
    return _GCM_MODULE


_GDA_MODULE = None
def _gda():
    """Importa (cacheado) generar_datasets_acum.py para reutilizar el catálogo y el matching
    de acciones comerciales (_REGLA_CANAL_SEG_MAP, _filtrar_ventas_accion, INOV_PRODUCTOS,
    cargar_clientes). Solo define funciones/constantes al import (sin I/O ni main())."""
    global _GDA_MODULE
    if _GDA_MODULE is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "generar_datasets_acum", str(BASE / "generar_datasets_acum.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _GDA_MODULE = mod
    return _GDA_MODULE


_GCM_VENTAS_CACHE = {}
def _gcm_leer_ventas_cacheado(path):
    """DataFrame de ventas_mes leído por el motor oficial (filtra activos, V3 solo trad), cacheado."""
    try:
        key = (str(path), os.path.getmtime(path))
    except OSError:
        key = (str(path), 0)
    df = _GCM_VENTAS_CACHE.get(key)
    if df is None:
        df = _gcm()._leer_ventas(path)
        _GCM_VENTAS_CACHE[key] = df
    return df


def _cierre_ranking_payload(rank, avance_map=None):
    """Transforma la lista de ranking en {ranking_top3, ranking, ganadores} para el portal.
    Si avance_map (codigo_str -> avance_pct) viene dado, el 'mejor en VOLUMEN' se determina por
    ALCANCE DEL OBJETIVO MENSUAL (avance vs objetivo), NO por litros+dinero. Solo cambia esa
    dimensión y su etiqueta; el score general y el resto del ranking quedan intactos."""
    rank = [dict(r) for r in rank]  # copia: no mutar el input cacheado

    if avance_map:
        def _av(r):
            v = avance_map.get(str(r.get("vendedor_codigo", "")).lstrip("Vv"))
            return float(v) if v is not None else -1.0
        for r in rank:
            a = _av(r)
            r["alcance_objetivo_pct"] = a if a >= 0 else None
        # Re-rankear la dimensión volumen por alcance de objetivo (desc) y rehacer su etiqueta.
        for i, r in enumerate(sorted(rank, key=lambda r: -_av(r))):
            r["ranking_volumen_dinero"] = i + 1
        for r in rank:
            etiq = [e for e in str(r.get("etiqueta_destacada", "")).split("|")
                    if e and e != "MEJOR_VOLUMEN_DINERO"]
            if r.get("ranking_volumen_dinero") == 1:
                etiq.append("MEJOR_VOLUMEN_DINERO")
            r["etiqueta_destacada"] = "|".join(etiq)

    top3 = sorted(rank, key=lambda r: r.get("ranking_general", 99))[:3]
    ranking_top3 = [{
        "ranking_general":       r.get("ranking_general"),
        "vendedor_codigo":       r.get("vendedor_codigo"),
        "vendedor_nombre":       r.get("vendedor_nombre"),
        "score_total":           r.get("score_total"),
        "clientes_11_titulares": r.get("clientes_11_titulares"),
        "clientes_innovaciones": r.get("clientes_innovaciones"),
        "etiqueta_destacada":    r.get("etiqueta_destacada", ""),
    } for r in top3]
    ranking = [{
        "vendedor_codigo":        r.get("vendedor_codigo"),
        "vendedor_nombre":        r.get("vendedor_nombre"),
        "dinero_vendido":         r.get("dinero_vendido"),
        "litros_vendidos":        r.get("litros_vendidos"),
        "clientes_11_titulares":  r.get("clientes_11_titulares"),
        "clientes_innovaciones":  r.get("clientes_innovaciones"),
        "alcance_objetivo_pct":   r.get("alcance_objetivo_pct"),
        "score_total":            r.get("score_total"),
        "ranking_general":        r.get("ranking_general"),
        "ranking_volumen_dinero": r.get("ranking_volumen_dinero"),
        "ranking_11_titulares":   r.get("ranking_11_titulares"),
        "ranking_innovaciones":   r.get("ranking_innovaciones"),
        "etiqueta_destacada":     r.get("etiqueta_destacada", ""),
    } for r in sorted(rank, key=lambda r: r.get("ranking_general", 99))]

    def _ganador(campo, metrica):
        for r in rank:
            if r.get(campo) == 1:
                return {"vendedor_codigo": r.get("vendedor_codigo"),
                        "vendedor_nombre": r.get("vendedor_nombre"),
                        "score_total": r.get("score_total"),
                        "metrica": r.get(metrica)}
        return None
    # Ganador de volumen: si hay avance_map, la métrica es el alcance del objetivo (%), no $.
    gan_vol = _ganador("ranking_volumen_dinero", "alcance_objetivo_pct" if avance_map else "dinero_vendido")
    if gan_vol is not None:
        gan_vol["base"] = "alcance_objetivo" if avance_map else "dinero_vendido"
    ganadores = {
        "general":        _ganador("ranking_general",        "score_total"),
        "volumen_dinero": gan_vol,
        "once_titulares": _ganador("ranking_11_titulares",   "clientes_11_titulares"),
        "innovaciones":   _ganador("ranking_innovaciones",   "clientes_innovaciones"),
    }
    return {"ranking_top3": ranking_top3, "ranking": ranking, "ganadores": ganadores}


def _cierre_extras_versionado(files):
    """Sell-Out, Innovaciones y Ranking del cierre desde ventas_mes_<MMAAAA>.csv,
    reutilizando el motor oficial. Catálogos compartidos: 04D, Innovaciones.xlsx, vendedores.
    Devuelve todo casteado a tipos nativos (jsonify-safe)."""
    out = {}
    # Sell-Out: TODA la venta agrupada (ruta + V20 Depósito) vs objetivo de EMPRESA, igual
    # criterio que el sell out vivo (/api/gerencia/sellout_litros). categorias ya incluye V20;
    # `deposito` queda como desglose informativo (ya está sumado en categorias).
    try:
        so_df = _leer_ventas_mes_cacheado(files["ventas_mes"], incluir_deposito=True)
        if so_df.empty:
            out["sellout"] = {"fuente": files["ventas_mes"].name, "filas_ventas_mes": 0,
                              "categorias": [], "deposito": [], "incluye_deposito": True}
        else:
            categorias = _sellout_desde_ventas(so_df)             # ruta + V20 vs objetivo
            dep_df = so_df[so_df["CodVendedor"] == 20]
            deposito = _sellout_desde_ventas(dep_df) if not dep_df.empty else []
            for c in deposito:                                    # depósito: sin objetivo propio
                c["objetivo"], c["alcance_pct"] = None, None
                for sub in c.get("subcategorias", []):
                    sub["objetivo"], sub["alcance_pct"] = None, None
            out["sellout"] = {
                "fuente": files["ventas_mes"].name,
                "filas_ventas_mes": int(len(so_df)),
                "categorias":       categorias,
                "total_litros":     round(sum(float(c["litros"]) for c in categorias), 1),
                "incluye_deposito": True,
                "deposito":         deposito,
                "total_deposito":   round(sum(float(c["litros"]) for c in deposito), 1),
            }
    except Exception as e:
        out["sellout"] = {"error": str(e), "categorias": []}

    # Innovaciones + Ranking (motor oficial sobre el ventas_mes versionado)
    try:
        gcm = _gcm()
        df = _gcm_leer_ventas_cacheado(files["ventas_mes"])
        vn = gcm._leer_vendedores(CONFIG / "vendedores_activos.csv")
        # Códigos de innovación desde el loader oficial (mismo que el dashboard: formato
        # "CODIGO - NOMBRE", 22 productos). El parser viejo gcm._leer_innovaciones quedó en 0
        # al cambiar el formato del xlsx → ranking marcaba "mejor innovaciones" con 0 clientes.
        cod_inov = set(_gda().INOV_PRODUCTOS.keys())

        ccc_mes = int(df["Cliente"].nunique()) if not df.empty else 0
        prod = {}
        for r in gcm._inov_detalle(df, cod_inov, vn):
            k = (int(r["producto_codigo"]), str(r["producto_nombre"]))
            prod[k] = prod.get(k, 0) + int(r["clientes_compraron"])
        por_producto = [{
            "producto_codigo": cod, "producto_nombre": nom,
            "compraron": int(comp), "pct": round(comp / ccc_mes * 100, 1) if ccc_mes else 0.0,
        } for (cod, nom), comp in prod.items()]
        por_producto.sort(key=lambda x: -x["pct"])
        out["innovaciones"] = {
            "resumen": {
                "productos":       len(por_producto),
                "compraron_total": int(sum(p["compraron"] for p in por_producto)),
                "ccc_mes":         ccc_mes,
                "pct_promedio":    round(sum(p["pct"] for p in por_producto) / len(por_producto), 1) if por_producto else 0,
            },
            "por_producto": por_producto[:20],
        }

        # Ranking — litros desde el maestro 04D CSV liviano (el xlsx de 19MB tarda ~40s).
        # castear litros/dinero a float nativo (groupby.to_dict() devuelve numpy)
        _, _, cod2lxu, _ = _cargar_maestro_04D()
        dfl = df.copy()
        dfl["_lxu"] = (dfl["Codigo"].astype(str).str.strip().str.upper()
                       .str.replace(r"\.0$", "", regex=True).map(cod2lxu).fillna(0.0))
        dfl["litros"] = dfl["CantBase"] * dfl["_lxu"]
        litros = {int(k): float(v) for k, v in dfl.groupby("CodVendedor")["litros"].sum().items()}
        dinero = {int(k): float(v) for k, v in df.groupby("CodVendedor")["ImporteNetoItem"].sum().items()}
        c11t   = {int(k): int(v) for k, v in gcm._11t_por_vend(df).items()}
        inov   = {int(k): int(v) for k, v in gcm._inov_por_vend(df, cod_inov).items()}
        out["ranking"] = gcm._ranking(litros, dinero, c11t, inov, vn)
    except Exception as e:
        out["_warn"] = "extras versionado (sellout/innov/ranking): " + str(e)

    return _to_native(out)


# Catálogo de reglas de acciones por período (esquema MAYO, en 09_CONFIG). Mayo usa este path.
# Junio en adelante: el catálogo viaja versionado en 01_INPUTS/cierres mes/acciones_<MMAAAA>.csv
# (esquema nuevo ACCIONES COMERCIALES) y lo procesa _cierre_acciones_junio_schema.
_ACC_REGLAS_POR_MMAAAA = {"052026": "reglas_acciones_mayo_2026_orbit.csv"}


def _cierre_acciones_junio_schema(files, reglas):
    """Acciones del cierre con el catálogo en esquema NUEVO (ACCIONES COMERCIALES/<mes>/,
    p.ej. junio 2026: canal_aplica/segmento_cliente_aplica/tipo_regla/productos_marcas).
    Reúsa el matching del motor live (_acc_seg_canon/_acc_subseg_filtro/_acc_product_pred)
    sobre el ventas_mes CONGELADO del cierre. Inversión = valorDescuento × CantBase.
    Totales sobre la UNIÓN de líneas (sin doble conteo entre acciones). Devuelve
    {resumen, detalle} jsonify-safe, o None si no hay ventas/catálogo."""
    v = _acc_preparar_ventas_mes_versionado(files["ventas_mes"])
    if v.empty or not reglas:
        return None
    all_lineas = set(l for l in v["_linea"].dropna().unique() if l and l != "NAN")
    plan_as_clientes = _acc_plan_as_clientes()

    def _match(r):
        vends_raw = str(r.get("vendedores_aplica", "")).upper()
        if "TODOS" in vends_raw:
            codes = {3, 4, 6, 7, 8, 9, 10}
        else:
            codes = {int(_re.sub(r"\D", "", x)) for x in _re.findall(r"V\s*\d+", vends_raw)} & {3, 4, 6, 7, 8, 9, 10}
        seg_set = _acc_seg_canon(r.get("segmento_cliente_aplica"), r.get("canal_aplica"))
        sub_allowed = _acc_subseg_filtro(r.get("segmento_cliente_aplica"), r.get("canal_aplica"))
        pred = _acc_product_pred(r, all_lineas)
        regla_txt = _acc_norm(" ".join(str(r.get(k, "")) for k in
                                       ("categoria", "canal_aplica", "segmento_cliente_aplica")))
        requiere_plan_as = "PLANES AASS" in regla_txt or "PLAN AASS" in regla_txt
        m = v["_vend"].isin(codes) & v["_seg"].isin(seg_set)
        if sub_allowed is not None:
            is_trad = v["_seg"].astype(str).str.upper().eq("TRADICIONAL")
            sub_ok = v["_subseg"].apply(lambda s: any(tok in s for tok in sub_allowed))
            m = m & (~is_trad | sub_ok)
        sub = v[m]
        if sub.empty:
            return sub
        keys = list(zip(sub["_cat"], sub["_linea"], sub["_art"], sub["_marca"], sub["_cod"]))
        predcache, keep = {}, []
        for k in keys:
            if k not in predcache:
                predcache[k] = bool(pred(*k))
            keep.append(predcache[k])
        sub = sub[pd.Series(keep, index=sub.index, dtype=bool)]
        if requiere_plan_as:
            sub = sub[pd.to_numeric(sub["_cli"], errors="coerce").isin(plan_as_clientes)]
        return sub

    detalle, matched_idx, cli_union = [], set(), set()
    for r in reglas:
        cur = _match(r)
        if cur.empty:
            continue
        matched_idx |= set(cur.index)
        cli_ids = set(cur["_cli"].dropna().astype(int))
        cli_union |= cli_ids
        cur_desc = cur[cur["_desc"] > 0]
        tipo_raw = str(r.get("tipo_regla", "")).upper()
        tipo = "Sin cargo" if ("SIN_CARGO" in tipo_raw or "BONIFIC" in tipo_raw) else "Descuento"
        nombre = (str(r.get("observaciones", "")).strip().split(".")[0]
                  or str(r.get("id_accion", "")).strip()
                  or f"{r.get('canal_aplica', '')}|{r.get('categoria', '')}")
        detalle.append({
            "nombre":       nombre[:80],
            "tipo":         tipo,
            "canal":        str(r.get("canal_aplica", "")).strip(),
            "categoria":    str(r.get("categoria", "")).strip().upper(),
            "descuento":    (str(r.get("descuento_pct", "")).strip() + "%") if str(r.get("descuento_pct", "")).strip() else "–",
            "litros":       round(float(cur["_litros"].sum()), 1),
            "inversion":    round(float(cur_desc["_desc"].sum()), 0),
            "importe_neto": round(float(cur["_imp_neto"].sum()), 0),
            "clientes":     int(len(cli_ids)),
        })
    if not detalle:
        return None
    detalle.sort(key=lambda a: -a["inversion"])
    uni = v.loc[v.index.isin(matched_idx)]
    uni_desc = uni[uni["_desc"] > 0]
    resumen = {
        "total_acciones":     len(detalle),
        "inversion_total":    round(float(uni_desc["_desc"].sum()), 0),
        "importe_neto":       round(float(uni["_imp_neto"].sum()), 0),
        "clientes_afectados": int(len(cli_union)),
    }
    return _to_native({"resumen": resumen, "detalle": detalle[:10],
                       "fuente": files["ventas_mes"].name, "catalogo": f"acciones_{files.get('mmaaaa', '')}.csv"})


def _cierre_acciones_versionado(files):
    """Acciones Comerciales del cierre desde ventas_mes_<MMAAAA>.csv.
    Inversión = valorDescuento × CantBase (descuento REAL; NO ImporteItem-ImporteNetoItem,
    que es IVA ~21%). Matching de catálogo idéntico a generar_acciones_ranking (reutiliza
    _REGLA_CANAL_SEG_MAP / _filtrar_ventas_accion / INOV_PRODUCTOS). Maestro vía CSV liviano
    (no el xlsx de 19MB). Devuelve {resumen, detalle} jsonify-safe, o None si no hay catálogo/ventas."""
    reglas_name = _ACC_REGLAS_POR_MMAAAA.get(files.get("mmaaaa", ""))
    if not reglas_name:
        # Sin catálogo mayo-schema registrado: usar el catálogo versionado del cierre
        # (esquema nuevo ACCIONES COMERCIALES, p.ej. junio) sobre el ventas_mes congelado.
        acc_path = CIERRES_MES_DIR / f"acciones_{files.get('mmaaaa', '')}.csv"
        if acc_path.exists():
            try:
                rdf = pd.read_csv(acc_path, sep=";", encoding="utf-8-sig", dtype=str)
                rdf.columns = [c.strip() for c in rdf.columns]
                if "canal_aplica" in rdf.columns:
                    return _cierre_acciones_junio_schema(files, rdf.to_dict("records"))
            except Exception:
                return None
        return None
    reglas_path = CONFIG / reglas_name
    if not reglas_path.exists():
        return None
    gda = _gda()
    df = _leer_ventas_mes_cacheado(files["ventas_mes"]).copy()   # neto>0, excl V2/V5/V20
    if df.empty:
        return None

    # Preparación (réplica de _preparar_ventas_acciones pero con inversión correcta = vd×CantBase)
    cod2cat, _cod2seg, cod2lxu, _cod2linea = _cargar_maestro_04D()
    clientes = gda.cargar_clientes()   # clientes.xlsx (liviano) → _seg oficial por cliente
    df["_cod"] = pd.to_numeric(df["Codigo"], errors="coerce")
    df["_cli"] = pd.to_numeric(df["Cliente"], errors="coerce")
    df["_codstr"] = (df["Codigo"].astype(str).str.strip().str.upper().str.replace(r"\.0$", "", regex=True))
    df["_vd"] = pd.to_numeric(df["valorDescuento"].astype(str).str.replace(",", ".", regex=False),
                              errors="coerce").fillna(0)
    df["Descuento_pct"] = pd.to_numeric(
        df["Descuento"].astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce").fillna(0)
    v = df[df["Descuento_pct"] > 0].copy()
    if v.empty:
        return None
    v["_descuento_p"] = (v["_vd"] * v["CantBase"]).clip(lower=0)      # inversión real
    v["Categoria"] = v["_codstr"].map(cod2cat)
    v["_litros"] = v["CantBase"] * v["_codstr"].map(cod2lxu).fillna(0.0)
    cs = clientes[["Codigo", "_seg"]].copy()
    cs["Codigo"] = pd.to_numeric(cs["Codigo"], errors="coerce")
    v = v.merge(cs.rename(columns={"Codigo": "cli_id"}), left_on="_cli", right_on="cli_id", how="left")

    reglas = pd.read_csv(reglas_path, encoding="utf-8-sig")
    reglas.columns = [c.strip() for c in reglas.columns]

    seen, detalle, cli_union = set(), [], set()
    for _, r in reglas.iterrows():
        canal = str(r.get("canal", "")).strip()
        cat   = str(r.get("categoria", "")).strip().upper()
        grupo = str(r.get("accion_grupo", f"{canal}|{cat}")).strip()
        if grupo in seen:
            continue
        seen.add(grupo)
        if canal == "PLANES AASS" or cat == "RESTO SKU" or canal not in gda._REGLA_CANAL_SEG_MAP:
            continue
        vm = gda._filtrar_ventas_accion(v, canal, cat, gda._REGLA_CANAL_SEG_MAP[canal])
        if vm is None or vm.empty:
            continue
        desc_vals = sorted(vm["Descuento_pct"].dropna().unique())
        if desc_vals:
            lo, hi = round(min(desc_vals)), round(max(desc_vals))
            desc_disp = f"{int(lo)}%" if lo == hi else f"{int(lo)}-{int(hi)}%"
        else:
            desc_disp = "–"
        cli_ids = set(vm["_cli"].dropna().astype(int))
        cli_union |= cli_ids
        detalle.append({
            "nombre":       str(r.get("accion_nombre", grupo)).strip(),
            "tipo":         str(r.get("tipo_accion", "")).strip(),
            "canal":        canal,
            "categoria":    cat,
            "descuento":    desc_disp,
            "litros":       round(float(vm["_litros"].sum()), 1),
            "inversion":    round(float(vm["_descuento_p"].sum()), 0),
            "importe_neto": round(float(vm["ImporteNetoItem"].sum()), 0),
            "clientes":     int(len(cli_ids)),
        })

    if not detalle:
        return None
    detalle.sort(key=lambda a: -a["inversion"])
    resumen = {
        "total_acciones":     len(detalle),
        "inversion_total":    round(sum(a["inversion"] for a in detalle), 0),
        "importe_neto":       round(sum(a["importe_neto"] for a in detalle), 0),
        "clientes_afectados": int(len(cli_union)),
    }
    return _to_native({"resumen": resumen, "detalle": detalle[:10],
                       "fuente": files["ventas_mes"].name, "catalogo": reglas_name})


def _cierre_manifest_versionado(files):
    """Manifest minimo para cierres descubiertos por carpeta (01_INPUTS/cierres mes/) que NO
    tienen carpeta en 07_CIERRES_MENSUALES/. Reusa el motor oficial para filas/fechas/
    vendedores/V3, mismo criterio que generar_cierre_mensual.py (activos, V3 solo trad)."""
    gcm = _gcm()
    src = files["ventas_mes"]
    df  = _gcm_leer_ventas_cacheado(src)
    excl = sorted(gcm._raw_codigos(src) - gcm.VENDEDORES_ACTIVOS)
    fmin = df["FechaComprobante"].min() if not df.empty else None
    fmax = df["FechaComprobante"].max() if not df.empty else None
    vdet = sorted(int(x) for x in df["CodVendedor"].unique()) if not df.empty else []
    v3   = df[df["CodVendedor"] == 3] if not df.empty else df
    v3ok = bool((v3["segmento"] == "TRADICIONAL").all()) if not v3.empty else True
    return {
        "filas_leidas":             int(len(df)),
        "fecha_min":                fmin.strftime("%Y-%m-%d") if pd.notna(fmin) else None,
        "fecha_max":                fmax.strftime("%Y-%m-%d") if pd.notna(fmax) else None,
        "vendedores_detectados":    [f"V{c}" for c in vdet],
        "vendedores_excluidos_csv": [f"V{c}" for c in excl],
        "v3_solo_tradicional_pass": v3ok,
        "fuente_ventas":            "01_INPUTS/cierres mes/" + src.name,
        "estado":                   "PASS",
    }


# ====== CIERRES HISTORICOS ======
@app.route("/api/gerencia/cierres_historicos")
def gerencia_cierres_historicos():
    """Lista de cierres mensuales historicos generados en 07_CIERRES_MENSUALES/.
    Solo lectura. No genera cierres nuevos. No toca ventas_mes.csv ni ningun input.
    """
    cierres_dir = BASE / "07_CIERRES_MENSUALES"
    idx_path    = cierres_dir / "index_cierres_mensuales.json"

    indice = []
    if idx_path.exists():
        try:
            with open(idx_path, encoding="utf-8") as f:
                indice = json.load(f)
        except Exception as e:
            return jsonify({"cierres": [], "estado": "ERROR",
                            "error": "No se pudo leer el indice: " + str(e)}), 500

    # Descubrir cierres versionados por carpeta (01_INPUTS/cierres mes/) que NO esten en el
    # indice 07. Asi cada cierre que genera CIERRE_MES_ORBIT.bat aparece solo y el selector de
    # mes del portal crece con cada mes, sin depender de 07_CIERRES_MENSUALES/.
    periodos_idx = {str(e.get("periodo", "")) for e in indice}
    for vm in sorted(CIERRES_MES_DIR.glob("ventas_mes_*.csv")):
        mmaaaa = vm.stem.replace("ventas_mes_", "")
        if len(mmaaaa) != 6 or not mmaaaa.isdigit():
            continue
        periodo = f"{mmaaaa[2:]}-{mmaaaa[:2]}"
        if periodo in periodos_idx:
            continue
        try:
            ts = datetime.fromtimestamp(vm.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S-03:00")
        except Exception:
            ts = ""
        indice.append({"periodo": periodo, "version": "version_001", "carpeta": "",
                       "timestamp_argentina": ts, "estado": "PASS", "_versionado_only": True})

    if not indice:
        return jsonify({"cierres": [], "estado": "SIN_CIERRES",
                        "nota": "No hay cierres en 07_CIERRES_MENSUALES/ ni en 01_INPUTS/cierres mes/"})

    cierres = []
    for entrada in indice:
        periodo  = entrada.get("periodo", "")
        version  = entrada.get("version", "")
        vonly    = bool(entrada.get("_versionado_only"))
        # Cierres descubiertos por carpeta no tienen carpeta en 07_CIERRES_MENSUALES/: apuntamos
        # a una ruta inexistente para que las lecturas legacy (.exists()) den False sin romper;
        # el manifest y los bloques se reconstruyen desde el cierre versionado mas abajo.
        carpeta  = (cierres_dir / periodo / "__versionado__") if vonly \
                   else (cierres_dir.parent / Path(entrada.get("carpeta", "").replace("\\", "/")))
        ts_ar    = entrada.get("timestamp_argentina", "")
        estado   = entrada.get("estado", "")

        cierre = {
            "periodo":             periodo,
            "version":             version,
            "timestamp_argentina": ts_ar,
            "estado":              estado,
            "manifest":            None,
            "empresa":             None,
            "ranking_top3":        [],
            "ranking":             [],
            "ganadores":           {},
            "objetivos_avance":    None,
            "ccc_segmentos":       None,
            "once_titulares":      None,
            "innovaciones":        None,
            "sellout":             None,
            "planes_as":           None,
            "acciones_comerciales": None,
            "warn":                [],
        }

        manifest_path = carpeta / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    m = json.load(f)
                cierre["manifest"] = {
                    "filas_leidas":            m.get("filas_leidas"),
                    "fecha_min":               m.get("fecha_min"),
                    "fecha_max":               m.get("fecha_max"),
                    "vendedores_detectados":   m.get("vendedores_detectados", []),
                    "vendedores_excluidos_csv": m.get("vendedores_excluidos_csv", []),
                    "v3_solo_tradicional_pass": m.get("v3_solo_tradicional_pass"),
                    "fuente_ventas":           m.get("fuente_ventas"),
                    "fuente_ventas_hash_head": m.get("fuente_ventas_hash_head"),
                    "estado":                  m.get("estado"),
                }
            except Exception as e:
                cierre["warn"].append("manifest.json no legible: " + str(e))
        else:
            cierre["warn"].append("manifest.json no encontrado")

        ranking_path = carpeta / "ranking_vendedores_mes.json"
        if ranking_path.exists():
            try:
                with open(ranking_path, encoding="utf-8") as f:
                    rank = json.load(f)
                top3 = sorted(rank, key=lambda r: r.get("ranking_general", 99))[:3]
                cierre["ranking_top3"] = [
                    {
                        "ranking_general":    r.get("ranking_general"),
                        "vendedor_codigo":    r.get("vendedor_codigo"),
                        "vendedor_nombre":    r.get("vendedor_nombre"),
                        "score_total":        r.get("score_total"),
                        "clientes_11_titulares":  r.get("clientes_11_titulares"),
                        "clientes_innovaciones":  r.get("clientes_innovaciones"),
                        "etiqueta_destacada": r.get("etiqueta_destacada", ""),
                    }
                    for r in top3
                ]
                # Ranking completo (todos los vendedores del cierre), ordenado por ranking_general.
                # Solo campos del cierre versionado; sin CantBase ni botellas.
                cierre["ranking"] = [
                    {
                        "vendedor_codigo":        r.get("vendedor_codigo"),
                        "vendedor_nombre":        r.get("vendedor_nombre"),
                        "dinero_vendido":         r.get("dinero_vendido"),
                        "litros_vendidos":        r.get("litros_vendidos"),
                        "clientes_11_titulares":  r.get("clientes_11_titulares"),
                        "clientes_innovaciones":  r.get("clientes_innovaciones"),
                        "score_total":            r.get("score_total"),
                        "ranking_general":        r.get("ranking_general"),
                        "ranking_volumen_dinero": r.get("ranking_volumen_dinero"),
                        "ranking_11_titulares":   r.get("ranking_11_titulares"),
                        "ranking_innovaciones":   r.get("ranking_innovaciones"),
                        "etiqueta_destacada":     r.get("etiqueta_destacada", ""),
                    }
                    for r in sorted(rank, key=lambda r: r.get("ranking_general", 99))
                ]
                # Ganadores por categoria = vendedor con ranking_X == 1 en cada eje.
                def _ganador(campo, metrica):
                    for r in rank:
                        if r.get(campo) == 1:
                            return {
                                "vendedor_codigo": r.get("vendedor_codigo"),
                                "vendedor_nombre": r.get("vendedor_nombre"),
                                "score_total":     r.get("score_total"),
                                "metrica":         r.get(metrica),
                            }
                    return None
                cierre["ganadores"] = {
                    "general":        _ganador("ranking_general",        "score_total"),
                    "volumen_dinero": _ganador("ranking_volumen_dinero", "dinero_vendido"),
                    "once_titulares": _ganador("ranking_11_titulares",   "clientes_11_titulares"),
                    "innovaciones":   _ganador("ranking_innovaciones",   "clientes_innovaciones"),
                }
            except Exception as e:
                cierre["warn"].append("ranking_vendedores_mes.json no legible: " + str(e))
        else:
            cierre["warn"].append("ranking_vendedores_mes.json no encontrado")

        # Resumen empresa del cierre (solo lectura de cierre_mensual_resumen.json).
        resumen_path = carpeta / "cierre_mensual_resumen.json"
        if resumen_path.exists():
            try:
                with open(resumen_path, encoding="utf-8") as f:
                    res = json.load(f)
                emp = res.get("empresa", {}) or {}
                cierre["empresa"] = {
                    "importe_neto_total":   emp.get("importe_neto_total"),
                    "litros_total":         emp.get("litros_total"),
                    "ccc_total":            emp.get("ccc_total"),
                    "filas_ventas_mes":     emp.get("filas_ventas_mes"),
                    "vendedores_incluidos": emp.get("vendedores_incluidos", []),
                }
            except Exception as e:
                cierre["warn"].append("cierre_mensual_resumen.json no legible: " + str(e))
        else:
            cierre["warn"].append("cierre_mensual_resumen.json no encontrado")

        # ── Bloques de detalle congelados (artefactos versionados del cierre) ──
        # Solo lectura de JSON ya generados en la carpeta del cierre. No recalcula.
        def _load_art(nombre):
            ruta = carpeta / nombre
            if not ruta.exists():
                return None
            try:
                with open(ruta, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                cierre["warn"].append(f"{nombre} no legible: {e}")
                return None

        oa = _load_art("cierre_objetivos_avance.json")
        if oa is not None:
            cierre["objetivos_avance"] = oa
            # ccc_segmentos derivado del mismo artefacto (empresa + por vendedor), sin duplicar archivo
            emp_oa = oa.get("empresa", {}) or {}
            cierre["ccc_segmentos"] = {
                "empresa": {
                    "ccc_total":        emp_oa.get("ccc_total"),
                    "ccc_tradicional":  emp_oa.get("ccc_tradicional"),
                    "ccc_autoservicio": emp_oa.get("ccc_autoservicio"),
                    "ccc_onpremise":    emp_oa.get("ccc_onpremise"),
                },
                "vendedores": [
                    {
                        "codigo":           v.get("codigo"),
                        "nombre":           v.get("nombre"),
                        "ccc_total":        v.get("ccc_total"),
                        "ccc_tradicional":  v.get("ccc_tradicional"),
                        "ccc_autoservicio": v.get("ccc_autoservicio"),
                        "ccc_onpremise":    v.get("ccc_onpremise"),
                    }
                    for v in (oa.get("vendedores", []) or [])
                ],
            }
        cierre["once_titulares"]       = _load_art("cierre_11_titulares_detalle.json")
        cierre["innovaciones"]         = _load_art("cierre_innovaciones_detalle.json")
        cierre["sellout"]              = _load_art("cierre_sellout.json")
        cierre["planes_as"]            = _load_art("cierre_planes_as.json")
        cierre["acciones_comerciales"] = _load_art("cierre_acciones_comerciales.json")

        # ── Cierre versionado por carpeta (01_INPUTS/cierres mes/) — FASE 1 ──
        # Si existen los 3 archivos del mes, objetivos/avance + 11T se calculan desde ellos
        # (fuente única y versionada), sustituyendo a los artefactos congelados.
        _files = _cierre_archivos_mes(periodo)
        if _files:
            # Manifest: para cierres descubiertos por carpeta (sin 07/) se reconstruye desde el
            # ventas_mes versionado; para los del indice 07 se respeta el manifest.json legacy.
            if cierre["manifest"] is None:
                try:
                    cierre["manifest"] = _cierre_manifest_versionado(_files)
                except Exception as e:
                    cierre["warn"].append("manifest versionado: " + str(e))
            try:
                oa = _cierre_objetivos_avance(_files)
                cierre["objetivos_avance"] = oa
                emp_oa = oa.get("empresa", {}) or {}
                cierre["ccc_segmentos"] = {
                    "empresa": {
                        "ccc_total":        emp_oa.get("ccc_total"),
                        "ccc_tradicional":  emp_oa.get("ccc_tradicional"),
                        "ccc_autoservicio": emp_oa.get("ccc_autoservicio"),
                        "ccc_onpremise":    emp_oa.get("ccc_onpremise"),
                    },
                    "vendedores": [
                        {"codigo": v.get("codigo"), "nombre": v.get("nombre"),
                         "ccc_total": v.get("ccc_total"), "ccc_tradicional": v.get("ccc_tradicional"),
                         "ccc_autoservicio": v.get("ccc_autoservicio"), "ccc_onpremise": v.get("ccc_onpremise")}
                        for v in oa.get("vendedores", [])
                    ],
                }
                cierre["once_titulares"] = _cierre_once_titulares(_files)
                cierre["fuente_cierre_versionado"] = "01_INPUTS/cierres mes/"
            except Exception as e:
                cierre["warn"].append("recálculo cierre versionado (objetivos/11T): " + str(e))
            # Sell-Out + Innovaciones + Ranking desde el ventas_mes versionado (FASE 2a)
            try:
                _ex = _cierre_extras_versionado(_files)
                if _ex.get("sellout") is not None:
                    cierre["sellout"] = _ex["sellout"]
                if _ex.get("innovaciones") is not None:
                    cierre["innovaciones"] = _ex["innovaciones"]
                if _ex.get("ranking"):
                    # Mejor en VOLUMEN = mayor alcance del objetivo mensual (avance vs objetivo),
                    # no litros+dinero. avance_map desde objetivos_avance ya calculado arriba.
                    _oa = cierre.get("objetivos_avance") or {}
                    _avance_map = {str(v.get("codigo")): v.get("avance_pct")
                                   for v in _oa.get("vendedores", []) if v.get("codigo") is not None}
                    _rk = _cierre_ranking_payload(_ex["ranking"], _avance_map or None)
                    cierre["ranking_top3"] = _rk["ranking_top3"]
                    cierre["ranking"]      = _rk["ranking"]
                    cierre["ganadores"]    = _rk["ganadores"]
                if _ex.get("_warn"):
                    cierre["warn"].append(_ex["_warn"])
            except Exception as e:
                cierre["warn"].append("recálculo cierre versionado (sellout/innov/ranking): " + str(e))
            # Acciones Comerciales desde ventas_mes versionado (FASE 2b) — inversión real (vd×CantBase),
            # NO IVA. Solo si hay catálogo del mes; si no, queda el artefacto congelado.
            try:
                _acc = _cierre_acciones_versionado(_files)
                if _acc is not None:
                    cierre["acciones_comerciales"] = _acc
            except Exception as e:
                cierre["warn"].append("recálculo cierre versionado (acciones): " + str(e))

        # Cierres descubiertos por carpeta no tienen artefactos 07/: descartar el ruido legacy
        # ("no encontrado"/"no legible"); ya se reconstruyo todo desde el cierre versionado.
        if vonly:
            cierre["warn"] = [w for w in cierre["warn"]
                              if "no encontrado" not in w and "no legible" not in w]

        if not cierre["warn"]:
            cierre.pop("warn")

        cierres.append(cierre)

    cierres.sort(key=lambda c: (c.get("periodo",""), c.get("version","")), reverse=True)

    return jsonify({
        "cierres":       cierres,
        "total_cierres": len(cierres),
        "estado":        "OK",
        "nota":          "Solo lectura. No recalcula ni modifica datos.",
    })


# ====== STARTUP (gunicorn + __main__) ======
# Se ejecuta cuando gunicorn importa el módulo, no solo en __main__
backup_orbit_db()         # 1. copia orbit.db antes de cualquier cambio
init_db()                 # 2. crea/migra tablas
restore_planificacion_if_empty()  # 3. recupera desde CSV si la tabla quedó vacía
export_planificacion_csv()        # 4. actualiza CSV de seguridad con estado actual


def _warm_caches():
    """Precalienta en background el payload pesado de Acciones Comerciales (vista
    gerencia, sin filtro). En Render (0.5 vCPU) ese cómputo puede acercarse al timeout
    del worker; al calcularlo en un hilo al arranque (sin timeout HTTP) queda cacheado
    y la primera request del gerente cae en caché. No bloquea el arranque ni el request."""
    try:
        _acciones_mes_payload(None)
    except Exception as e:  # nunca tumbar el arranque por el warmup
        try:
            print(f"[ORBIT] warmup acciones_mes fallo (no fatal): {e}")
        except Exception:
            pass


threading.Thread(target=_warm_caches, name="orbit-warmup", daemon=True).start()

if __name__ == "__main__":
    print("\n===== ORBIT SERVER v3 =====")
    print("Diagnóstico: http://localhost:8502/api/diagnostico")
    print("Dashboard:   http://localhost:8502/api/dashboard")
    print("Portal:      http://localhost:8502/index.html")
    print("===============================\n")
    port = int(os.environ.get("PORT", 8502))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
