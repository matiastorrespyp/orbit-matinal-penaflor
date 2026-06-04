import os
import re
from datetime import timedelta
import pandas as pd
import numpy as np

# ============================================================
# ORBIT MATINAL PEÑA - V4.2
# Entradas:
#   01_INPUTS/clientes.xlsx
#   01_INPUTS/ventas.csv
#   01_INPUTS/resultado.xlsx
#   01_INPUTS/producto activos.xlsx
# Salida:
#   03_OUTPUTS/MATINAL_PENA_V42.xlsx
# Historial:
#   02_HISTORY/historial_ventas_cliente.csv
# ============================================================

INPUT_CLIENTES = r"01_INPUTS/clientes.xlsx"
INPUT_VENTAS = r"01_INPUTS/ventas.csv"
INPUT_RESULTADO = r"01_INPUTS/resultado.xlsx"
INPUT_PRODUCTOS = r"01_INPUTS/producto activos.xlsx"

OUTPUT_DIR = r"03_OUTPUTS"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "MATINAL_PENA_V42.xlsx")

HISTORY_DIR = r"02_HISTORY"
HISTORY_FILE = os.path.join(HISTORY_DIR, "historial_ventas_cliente.csv")

FERIADOS_PATH = "09_CONFIG/feriados.csv"

NEGOCIO_ID = "PENIAFLOR"
NEGOCIO_NOMBRE = "Peñaflor"

VENDEDORES_EXCLUIDOS = [2, 5, 20]
TOLERANCIA_EXCESO_PCT = 0.20

INPUT_INNOVACIONES = r"01_INPUTS/INNOVACIONES/Innovaciones.xlsx"
_INOV_TEXTO_A_CODIGO = {"Frizze M": 14620, "Antares XPA": 60020}
_INOV_PENDIENTE_STOCK = {"Antares P 770", "Antares P 330"}
_INOV2_PRODUCTOS = {
    14620: "FRIZZE MANXANA",
    60020: "ANTARES XPA",
    74813: "DADA EXTRA BRUT 6X750",
    80094: "NC SPARK EXTRA BRUT LATA 4X6X355",
    14619: "FRIZZE BUBBLE MOOD 6X1000",
    74830: "DADA SIDRA 6X750",
    30139: "GORDON'S TROPICAL FRUITS 6x700",
    74749: "INTOCABLES DOUBLE OAK 6x750",
    44396: "BLEND DE EXTREMOS PN PN 6X750",
    14425: "TERMIDOR TRAD B-D SLIM 12X1L",
    42376: "DON DAVID RED BLEND 6X750",
    74814: "CAZADOR MALBEC 6X750",
    74815: "CAZADOR CAB. SAU 6X750",
    74816: "CAZADOR BLANCO DULCE 6X750",
    74827: "ALMA MORA BLANCO DULCE LOW 6X750",
    74840: "TRAPICHE DULCE COSECHA TINTO 6X750",
    74786: "EL BAUTISMO CABERNET 6X750",
}

_EXCLUIDOS_CLI_IDS = None

def _cargar_clientes_excluidos() -> set:
    global _EXCLUIDOS_CLI_IDS
    if _EXCLUIDOS_CLI_IDS is not None:
        return _EXCLUIDOS_CLI_IDS
    path = os.path.join("09_CONFIG", "clientes_excluidos.csv")
    if not os.path.exists(path):
        _EXCLUIDOS_CLI_IDS = set()
        return _EXCLUIDOS_CLI_IDS
    try:
        df = pd.read_csv(path, sep=",", encoding="utf-8", dtype={"cliente_id": str})
        ids = pd.to_numeric(df["cliente_id"], errors="coerce").dropna().astype(int)
        _EXCLUIDOS_CLI_IDS = set(ids.tolist())
    except Exception:
        _EXCLUIDOS_CLI_IDS = set()
    return _EXCLUIDOS_CLI_IDS

# ============================================================
# 11 TITULARES FINOS
# ============================================================

MAP_11T_FINE = {
    "ON_DIA": [
        "ALMA MORA", "DON DAVID", "FOND DE CAVE", "FOND DE CAVE RVA", "CAZADOR",
        "JW BLACK", "JW RED", "MASCOTA", "NC ESPUMANTES", "TRAPICHE MEDALLA", "TRAPICHE RESERVA",
    ],
    "ON_NOCHE": [
        "ALARIS", "ALMA MORA", "GORDONS", "JW BLACK", "JW GOLD",
        "JW RED", "LOS INTOCABLES", "NC ESPUMANTES", "SMIRNOFF", "SMIRNOFF FLAVOURS", "TANQUERAY",
    ],
    "VINOTECAS": [
        "BLEND EXTREMOS", "EL ESTECO", "FOND DE CAVE RVA", "COSTA&PAMPA", "JW BLACK",
        "JW GOLD", "LA MASCOTA", "NC ESPUMANTES", "TANQUERAY", "TRAPICHE MEDALLA", "TRAPICHE RESERVA",
    ],
    "TIENDA_BEBIDAS": [
        "ALMA MORA", "ANTARES", "DADA", "FOND DE CAVE", "FOND DE CAVE RVA",
        "GORDONS", "JW RED", "LOS INTOCABLES", "SMIRNOFF FLAVOURS", "SMIRNOFF ICE", "CAZADOR",
    ],
    "CATERING": [
        "ALMA MORA", "FOND DE CAVE", "GORDON'S", "JW RED", "JW BLACK",
        "LOS INTOCABLES", "MEDALLA", "NC ESPUMANTES", "SMIRNOFF", "TANQUERAY", "TRAPICHE RESERVA",
    ],
    "AUTOSERVICIO": [
        "ALMA MORA", "DADA", "LOS ARBOLES", "TRAPICHE RESERVA", "ALARIS",
        "FINCA LAS MORAS", "DON DAVID", "GORDON'S FLAVOURS", "SMIRNOFF FLAVOURS", "ANTARES", "SMF ICE",
    ],
    "TRADICIONAL": [
        "ALMA MORA", "DON DAVID", "FOND DE CAVE", "FOND DE CAVE RVA", "CAZADOR",
        "JW BLACK", "JW RED", "MASCOTA", "NC ESPUMANTES", "TRAPICHE MEDALLA", "TRAPICHE RESERVA",
    ],
    "OTROS": [
        "ALMA MORA", "FOND DE CAVE", "TRAPICHE RESERVA",
    ],
}

# Alias de marcas para matching flexible
MARCA_ALIASES = {
    "ALMA MORA": ["ALMA MORA", "AM"],
    "DON DAVID": ["DON DAVID"],
    "FOND DE CAVE": ["FOND DE CAVE", "FOND CAVE"],
    "FOND DE CAVE RVA": ["FOND DE CAVE RVA", "FOND CAVE RVA", "FOND CAVE G. RVA", "FOND CAVE G RVA"],
    "CAZADOR": ["CAZADOR"],
    "JW BLACK": ["JW BLACK", "JOHNNIE WALKER BLACK"],
    "JW RED": ["JW RED", "JOHNNIE WALKER RED"],
    "JW GOLD": ["JW GOLD", "JOHNNIE WALKER GOLD"],
    "MASCOTA": ["MASCOTA", "LA MASCOTA"],
    "NC ESPUMANTES": ["NC ESPUMANTES", "NAVARRO CORREAS", "NC SPARK", "NC BRUT", "NC NATURE", "NC ROSE"],
    "TRAPICHE MEDALLA": ["TRAPICHE MEDALLA", "GRAN MEDALLA", "MEDALLA"],
    "TRAPICHE RESERVA": ["TRAPICHE RESERVA"],
    "ALARIS": ["ALARIS", "TRAPICHE ALARIS"],
    "GORDONS": ["GORDONS", "GORDON'S"],
    "GORDON'S": ["GORDONS", "GORDON'S"],
    "GORDON'S FLAVOURS": ["GORDON'S FLAVOURS", "GORDONS FLAVOURS", "GORDON'S PINK", "GORDONS PINK"],
    "LOS INTOCABLES": ["LOS INTOCABLES"],
    "SMIRNOFF": ["SMIRNOFF", "SMIR"],
    "SMIRNOFF FLAVOURS": ["SMIRNOFF FLAVOURS", "SMIRNOFF SANDIA", "SMIRNOFF MANZANA", "SMIRNOFF RASPBERRY", "SMIRNOFF GREENAPPLE"],
    "SMIRNOFF ICE": ["SMIRNOFF ICE", "SMF ICE", "SMIR ICE"],
    "ANTARES": ["ANTARES"],
    "DADA": ["DADA"],
    "LOS ARBOLES": ["LOS ARBOLES"],
    "FINCA LAS MORAS": ["FINCA LAS MORAS", "F LAS MORAS", "FLM"],
    "EL ESTECO": ["EL ESTECO"],
    "COSTA&PAMPA": ["COSTA&PAMPA", "COSTA Y PAMPA", "COSTA PAMPA"],
    "TANQUERAY": ["TANQUERAY"],
    "BLEND EXTREMOS": ["BLEND EXTREMOS"],
    "WHITE HORSE": ["WHITE HORSE"],
    "J&B": ["J&B", "J B"],
    "OLD PARR": ["OLD PARR"],
    "SINGLETON": ["SINGLETON"],
    "ZACAPA": ["ZACAPA"],
    "VAT 69": ["VAT 69"],
    "EL BAUTISMO": ["EL BAUTISMO"],
    "ELEMENTOS": ["ELEMENTOS"],
    "SUTER": ["SUTER"],
    "SAN TELMO": ["SAN TELMO"],
    "HEREFORD": ["HEREFORD"],
    "LA GRAN NACHA": ["LA GRAN NACHA"],
    "DOLORES": ["DOLORES"],
}

# ============================================================
# REGLAS DE DESCUENTO
# ============================================================

REGLAS_PRODUCTO_EXACTAS = {
    "BUCHANANAS DELUXE 12X750": 5,
    "ALEGORIA CHARDO 6X750": 10,
    "ALEGORIA MALBEC 6X750": 10,
    "ALMA MORA SEL RVE CHARDO 6X750": 10,
    "COLECCION PRIVADA BLEND 6X750": 10,
    "COLECCION PRIVADA MERLOT 6X750": 10,
    "EL BAUTISMO ROSADO 6X750": 10,
    "EL ESTECO BLANC DE BLANC 4X750": 10,
    "EL ESTECO CABERNET SAUV 6X750": 10,
    "FINCA NOTABLES MALBEC .6X750": 10,
    "FLM GRAN SYRAH 6X750": 10,
    "FOND CAVE G. RVA CABSAU 6 X 750": 10,
    "FOND CAVE RVA COS TARDIA 6 X 500": 10,
    "FOND CAVE RVA SAUVIGNON 6X750": 10,
    "GRAN MEDALLA PINOT NOIR 6X750": 10,
    "J DE DIOS NC BLEND": 10,
    "J&B YELLOW 6X750": 10,
    "LA MASCOTA MALBEC 6X750": 10,
    "LA MASCOTA SPARK BL NOIR 6X750": 10,
    "MARANTIQUA MALBEC 6X750": 10,
    "OLD PARR 12YO 12X750": 10,
    "PAZ DE FLM CAB FRANC 6X750": 10,
    "PAZ DE FLM SAUV BLANC 6X750": 10,
    "PERFILES MB TEXTURA FINA 6X 750": 10,
    "SINGLETON 12 YO 6X700": 10,
    "SINGLETON 18 YO 6X700": 10,
    "TRAPICHE ALARIS SBLANC 6X750": 10,
    "TRAPICHE IMPURO CAB.SAUV 6X750": 10,
    "VAT 69 APPLE X700": 10,
    "ZACAPA CENT XO 6X750": 10,
    "DOLORES ESPUMANTE DULCE 6X750": 20,
    "DOLORES ESPUMANTE ROSE 6X750": 20,
    "NC SPARK BRUT ROSE 6X750": 20,
    "NC SPARK NATURE 6X750 PREM": 20,
    "EL REGRESO SEM-CHEN X750": 30,
    "PIMMS BITTER 12X750": 30,
    "SAN TELMO SPARK EXT DULCE 6X75 MA": 30,
    "SUTER CHAMPAÑA E.BRUT 6X750": 30,
    "SUTER ETIQ MARRON NEW PIN 6X750": 30,
    "SUTER VARIETAL TARDIO6X750": 30,
    "HEREFORD BCO 6X750": 50,
    "LA GRAN NACHA X750": 50,
}

REGLAS_PRODUCTO_FLEX = {
    "DADA": 13,
    "ELEMENTOS": 13,
    "FINCA LAS MORAS": 13,
    "F.LAS MORAS": 13,
    "LOS ARBOLES": 13,
    "ALMA MORA": 13,
    "ALARIS": 13,
    "SUTER ELEMENTS": 15,
    "EL BAUTISMO MALBEC": 10,
    "F LAS MORAS RED BLEND": 10,
}

# ============================================================
# HELPERS
# ============================================================

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def build_log(log_rows, detalle: str, valor="") -> None:
    log_rows.append({"DETALLE": detalle, "VALOR": valor})

def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    if s.upper() in {"NAN", "NONE", "#¿NOMBRE?", "#NOMBRE?", "#NAME?", "NULL"}:
        return ""
    return s

def normalize_upper(value) -> str:
    return normalize_text(value).upper()

def normalize_spaces_upper(value) -> str:
    return re.sub(r"\s+", " ", normalize_upper(value)).strip()

def parse_num_ar(value):
    if pd.isna(value):
        return 0.0
    s = str(value).strip()
    if s == "":
        return 0.0
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def parse_pct(value):
    if pd.isna(value):
        return 0.0
    s = str(value).strip().replace("%", "")
    s = s.replace(".", "").replace(",", ".")
    if s == "":
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

def map_day_abbr(fecha: pd.Timestamp) -> str:
    return {0: "Lu", 1: "Ma", 2: "Mi", 3: "Ju", 4: "Vi", 5: "Sa", 6: "Do"}.get(fecha.weekday(), "")

def cargar_feriados() -> set:
    try:
        df = pd.read_csv(FERIADOS_PATH, parse_dates=["fecha"])
        return set(df["fecha"].dt.date)
    except Exception:
        return set()

def siguiente_dia_operativo(
    fecha: pd.Timestamp,
    clientes_df: pd.DataFrame,
    feriados_set: set
) -> pd.Timestamp:
    tiene_sabado = (
        clientes_df["dias_visita"]
        .astype(str)
        .str.upper()
        .str.contains(r"\bSA\b", regex=True)
        .any()
    )
    candidate = fecha + timedelta(days=1)
    for _ in range(14):
        wd = candidate.weekday()
        if wd == 6:
            candidate += timedelta(days=1)
            continue
        if candidate.date() in feriados_set:
            candidate += timedelta(days=1)
            continue
        if wd == 5 and not tiene_sabado:
            candidate += timedelta(days=1)
            continue
        return candidate
    return candidate

def limpiar_texto_comercial(value: str) -> str:
    s = normalize_spaces_upper(value)
    s = s.replace("´", "'")
    s = re.sub(r"[^\w\s&'/.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def detectar_marca_desde_texto(texto: str) -> str:
    txt = limpiar_texto_comercial(texto)
    for marca_canonica, aliases in MARCA_ALIASES.items():
        for a in aliases:
            if limpiar_texto_comercial(a) in txt:
                return marca_canonica
    return ""

def clasificar_segmento_operativo(ramo: str, subsegmento: str) -> str:
    texto = f"{normalize_upper(ramo)} | {normalize_upper(subsegmento)}"

    claves_auto = [
        "AUTOSERVICIO", "CADENA REGIONAL", "SAR", "LARGE FORMAT", "PROXIMITY",
        "CASH&CARRY", "CASH & CARRY", "MAYORISTA", "MAYORISTAS", "TIENDA DE BEBIDAS",
    ]
    if any(k in texto for k in claves_auto):
        return "AUTOSERVICIO"

    claves_on = [
        "ON PREMISE", "AWAY FROM HOME", "VINOTECA", "VINOTECAS", "BAR",
        "RESTAURANT", "RESTAURANTE", "ESTACION DE SERVICIO", "ESTACIONES DE SERVICIO",
        "EVENTOS", "TEMPORADA", "CATERING", "ON DIA", "ON NOCHE",
    ]
    if any(k in texto for k in claves_on):
        return "ON_PREMISE_VTK"

    claves_trad = [
        "TRADITIONAL TRADE", "ALMACEN", "DESPENSA", "KIOSCO", "MAXIKIOSCO",
        "FIAMBRERIA", "CARNICERIA", "GRANJA", "PANADERIA", "CASA DE PASTAS", "TRADICIONAL",
    ]
    if any(k in texto for k in claves_trad):
        return "TRADICIONAL"

    return "OTROS"

def clasificar_segmento_11t(ramo: str, subsegmento: str, segmento_operativo: str) -> str:
    texto = f"{normalize_upper(ramo)} | {normalize_upper(subsegmento)}"

    if "VINOTECA" in texto:
        return "VINOTECAS"
    if "CATERING" in texto:
        return "CATERING"
    if "TIENDA DE BEBIDAS" in texto or "TDB" in texto:
        return "TIENDA_BEBIDAS"
    if "ON NOCHE" in texto or "NOCHE" in texto or "BOLICHE" in texto or "PUB" in texto:
        return "ON_NOCHE"
    if "ON DIA" in texto:
        return "ON_DIA"
    if segmento_operativo == "AUTOSERVICIO":
        return "AUTOSERVICIO"
    if segmento_operativo == "ON_PREMISE_VTK":
        return "ON_DIA"
    if segmento_operativo == "TRADICIONAL":
        return "TRADICIONAL"
    return "OTROS"

def threshold_cobertura(segmento_operativo: str) -> int:
    return 6 if segmento_operativo in {"AUTOSERVICIO", "ON_PREMISE_VTK"} else 3

def prioridad_11t(tiene_flag: int, botellas_mes: float) -> str:
    if tiene_flag == 0:
        return "ALTA"
    if botellas_mes <= 6:
        return "MEDIA"
    return "BAJA"

def extraer_unidades_por_caja(articulo: str) -> int:
    texto = normalize_upper(articulo)
    nums = re.findall(r"(\d+)\s*X", texto)
    if not nums:
        return 1
    unidades = 1
    try:
        for n in nums:
            unidades *= int(n)
        return max(unidades, 1)
    except Exception:
        return 1

def cajas_equivalentes(cant_base: float, articulo: str) -> float:
    unidades = extraer_unidades_por_caja(articulo)
    if unidades <= 0:
        unidades = 1
    return cant_base / unidades

def es_vinos_vda_vdg_esp_sidra(articulo: str, marca: str, ramo: str, subramo: str) -> bool:
    txt = " | ".join([
        normalize_upper(articulo),
        normalize_upper(marca),
        normalize_upper(ramo),
        normalize_upper(subramo),
    ])
    claves = [
        "MALBEC", "CABERNET", "MERLOT", "SYRAH", "BLEND", "SAUV", "PINOT", "CHARD",
        "RIESLING", "TORRONTES", "VIOGNIER", "RESERVA", "MEDALLA", "ESPUMANTE",
        "SPARK", "SIDRA", "ALMA MORA", "TRAPICHE", "DON DAVID", "FINCA LAS MORAS",
        "FOND DE CAVE", "DADA", "ALARIS", "LOS ARBOLES", "EL ESTECO", "SUTER",
        "SAN TELMO", "LA MASCOTA", "MEDALLA", "ELEMENTOS", "EL BAUTISMO"
    ]
    return any(k in txt for k in claves)

def es_frizze(articulo: str, marca: str) -> bool:
    return "FRIZZE" in f"{normalize_upper(articulo)} | {normalize_upper(marca)}"

def es_rtd_latas(articulo: str, marca: str) -> bool:
    txt = f"{normalize_upper(articulo)} | {normalize_upper(marca)}"
    return any(k in txt for k in ["GORDONS TONIC", "SMIR BC", "SMIRNOFF BC", "ANTARES", "SMF ICE"])

def es_spirits_locales(articulo: str, marca: str) -> bool:
    txt = f"{normalize_upper(articulo)} | {normalize_upper(marca)}"
    return any(k in txt for k in ["SMIRNOFF", "GORDON", "WHITE HORSE", "J&B"])

def es_spirits_importados(articulo: str, marca: str) -> bool:
    txt = f"{normalize_upper(articulo)} | {normalize_upper(marca)}"
    claves = ["JW ", "JOHNNIE", "BUCHANAN", "OLD PARR", "SINGLETON", "ZACAPA", "TANQUERAY", "PIMMS", "VAT 69"]
    return any(k in txt for k in claves)

def construir_aliases_marca_objetivo(marca_obj: str):
    aliases = [limpiar_texto_comercial(marca_obj)]
    if marca_obj in MARCA_ALIASES:
        aliases.extend([limpiar_texto_comercial(x) for x in MARCA_ALIASES[marca_obj]])
    return list(dict.fromkeys([a for a in aliases if a]))

def match_marca_objetivo(marca_real: str, articulo_real: str, marca_obj: str) -> bool:
    txt = f"{limpiar_texto_comercial(marca_real)} | {limpiar_texto_comercial(articulo_real)}"
    aliases = construir_aliases_marca_objetivo(marca_obj)
    return any(alias in txt for alias in aliases)

def es_11t_por_segmento(articulo: str, marca: str, segmento_11t: str) -> bool:
    marcas = MAP_11T_FINE.get(segmento_11t, [])
    return any(match_marca_objetivo(marca, articulo, m) for m in marcas)

# ============================================================
# REGLAS COMERCIALES DESDE CSV
# ============================================================

_REGLAS_CSV_PATH = r"09_CONFIG/reglas_acciones_mayo_2026_orbit.csv"
_REGLAS_CSV_DF = None

def _cargar_reglas_csv() -> pd.DataFrame:
    global _REGLAS_CSV_DF
    if _REGLAS_CSV_DF is not None:
        return _REGLAS_CSV_DF
    if not os.path.exists(_REGLAS_CSV_PATH):
        _REGLAS_CSV_DF = pd.DataFrame()
        return _REGLAS_CSV_DF
    df = pd.read_csv(_REGLAS_CSV_PATH, encoding="utf-8-sig")
    df["cantidad_min"] = pd.to_numeric(df["cantidad_min"], errors="coerce").fillna(0)
    df["cantidad_max"] = pd.to_numeric(df["cantidad_max"], errors="coerce")
    df["descuento_pct"] = pd.to_numeric(df["descuento_pct"], errors="coerce").fillna(0)
    df["prioridad_regla"] = pd.to_numeric(df["prioridad_regla"], errors="coerce").fillna(99)
    df = df[df["beneficio_tipo"] == "DESCUENTO"].copy()
    _REGLAS_CSV_DF = df.reset_index(drop=True)
    return _REGLAS_CSV_DF

_SEG_A_CANALES_CSV = {
    "AUTOSERVICIO":   ["AUTOSERVICIOS"],
    "TRADICIONAL":    ["TRAD+KIOSCO+ON PREMISE"],
    "ON_DIA":         ["TRAD+KIOSCO+ON PREMISE"],
    "ON_NOCHE":       ["ON PREMISE NOCHE; BARES"],
    "CATERING":       ["TRAD+KIOSCO+ON PREMISE"],
    "VINOTECAS":      ["VTK/TDB"],
    "TIENDA_BEBIDAS": ["VTK/TDB"],
}

def _cats_comerciales(articulo: str, marca: str, ramo: str, subramo: str) -> list:
    cats = []
    if es_vinos_vda_vdg_esp_sidra(articulo, marca, ramo, subramo):
        cats.append("VDA/VDG/ESPUMANTES/SIDRA")
    if es_frizze(articulo, marca):
        cats.append("RTD")
    if es_rtd_latas(articulo, marca):
        cats.append("RTD LATAS")
    if es_spirits_importados(articulo, marca):
        cats.extend(["SPIRITS IMPORTADOS", "SPIRITS"])
    if es_spirits_locales(articulo, marca):
        cats.extend(["SPIRITS LOCALES", "SPIRITS"])
    return cats

def _buscar_regla_csv(seg: str, articulo: str, marca: str, ramo: str, subramo: str, cajas: float) -> tuple:
    reglas = _cargar_reglas_csv()
    if reglas.empty:
        return None, ""
    cats = _cats_comerciales(articulo, marca, ramo, subramo)
    if not cats:
        return None, ""
    canales = _SEG_A_CANALES_CSV.get(seg, []) + ["TODOS"]
    mask = (
        reglas["canal"].isin(canales)
        & reglas["categoria"].str.upper().isin([c.upper() for c in cats])
        & (reglas["cantidad_min"] <= cajas)
        & (reglas["cantidad_max"].isna() | (reglas["cantidad_max"] >= cajas))
    )
    candidatas = reglas[mask].copy()
    if candidatas.empty:
        return None, ""
    candidatas["_canal_ord"] = candidatas["canal"].apply(lambda c: 0 if c != "TODOS" else 1)
    candidatas = candidatas.sort_values(["prioridad_regla", "_canal_ord"])
    best = candidatas.iloc[0]
    pct_raw = float(best["descuento_pct"])
    pct = pct_raw * 100 if pct_raw <= 1 else pct_raw  # CSV usa decimales (0.06 → 6.0)
    return pct, str(best["accion_id"])

def calcular_descuento_maximo(row) -> tuple:
    articulo = normalize_spaces_upper(row["articulo_final"])
    marca = normalize_spaces_upper(row["marca_final"])
    ramo = normalize_spaces_upper(row["ramo"])
    subramo = normalize_spaces_upper(row["subramo"])
    seg = row.get("segmento_11t", "")  # segmento_11t — único en ventas_alerta (merge línea 1065)
    cajas = float(row.get("cajas_eq", 0))

    # CSV lookup primario: canal + categoría + cajas_eq en rango
    pct_csv, accion_id = _buscar_regla_csv(seg, articulo, marca, ramo, subramo, cajas)
    if pct_csv is not None:
        return pct_csv, accion_id

    # Fallback: reglas hardcodeadas por producto específico
    for clave, pct in REGLAS_PRODUCTO_FLEX.items():
        if normalize_spaces_upper(clave) in articulo:
            return float(pct), "PRODUCTO_FLEX"

    for art_exacto, pct in REGLAS_PRODUCTO_EXACTAS.items():
        if normalize_spaces_upper(art_exacto) in articulo:
            return float(pct), "PRODUCTO_EXACTO"

    especiales_15 = ["CAZADOR", "BAUTISMO CABERNET", "ALMA MORA LOW", "ALARIS DULCE COSECHA TINTO", "SIDRA DADA", "NC LATA"]
    if any(k in articulo for k in especiales_15):
        return 15.0, "ESPECIAL_15"

    blancos_dulces = ["SUTER ELEMENTS", "ALARIS", "ALMA MORA", "FINCA LAS MORAS", "ELEMENTOS", "LOS ARBOLES"]
    if any(k in articulo for k in blancos_dulces):
        if cajas >= 5:
            return 15.0, "BLANCOS_DULCES_15"
        if cajas >= 1:
            return 13.0, "BLANCOS_DULCES_13"

    if es_vinos_vda_vdg_esp_sidra(articulo, marca, ramo, subramo):
        if seg == "AUTOSERVICIO":
            if cajas >= 20:
                return 10.0, "AS_PLAN_20+"
            if cajas >= 10:
                return 10.0, "AS_PLAN_10+"
            if cajas >= 1:
                return 10.0, "AS_PLAN_1+"
        elif seg in {"TRADICIONAL", "ON_DIA", "ON_NOCHE", "CATERING"}:
            if cajas >= 4:
                return 10.0, "TRAD_ON_VDA_4+"
            return 6.0, "TRAD_ON_VDA_0_3"
        elif seg in {"VINOTECAS", "TIENDA_BEBIDAS"}:
            if cajas >= 6:
                return 10.0, "VTK_TDB_VDA_6+"
            if cajas >= 1:
                return 8.0, "VTK_TDB_VDA_1_5"

    if es_frizze(articulo, marca):
        return 5.0, "FRIZZE"
    if es_rtd_latas(articulo, marca):
        return 5.0, "RTD_LATAS"
    if es_spirits_locales(articulo, marca):
        return 6.0, "SPIRITS_LOCALES"
    if es_spirits_importados(articulo, marca):
        return 3.0, "SPIRITS_IMPORTADOS"

    if seg == "AUTOSERVICIO":
        if es_spirits_locales(articulo, marca):
            return 10.0, "AASS_SPIRITS_10"
        if any(k in articulo for k in ["SUTER", "SAN TELMO", "DADA", "ESPUMANTE", "SPARK"]):
            return 7.0, "AASS_ESPUMANTES_7"
        if es_vinos_vda_vdg_esp_sidra(articulo, marca, ramo, subramo):
            return 10.0, "AASS_VDA_10"
        return 6.0, "AASS_RESTO_6"

    return np.nan, ""

def factor_volumen_necesario(descuento_pct: float) -> float:
    if descuento_pct <= 0:
        return 1.0
    if descuento_pct >= 100:
        return np.nan
    return 1.0 / (1.0 - descuento_pct / 100.0)

# ============================================================
# MÓDULO INNOVACIONES + PLAN AS
# ============================================================

def generar_mod_innovaciones_plan_as(ventas_validas, clientes, fecha_ejecucion):
    """
    Seguimiento de 17 innovaciones activas por cliente Plan AS (28 clientes PYP).
    Cruza con ventas reales del mes actual. Antares P770/P330 excluidos del
    denominador (pendiente stock).
    """
    if not os.path.exists(INPUT_INNOVACIONES):
        return pd.DataFrame()

    df_inov = pd.read_excel(INPUT_INNOVACIONES, sheet_name="Cuadro Inov", header=4)
    df_inov = df_inov[pd.to_numeric(df_inov["Cod C"], errors="coerce").notna()].copy()
    df_inov["cliente_id"] = pd.to_numeric(df_inov["Cod C"], errors="coerce").astype(int)
    df_inov["plan_as"] = df_inov["Plan AS "].fillna("").str.strip()

    # Clasificar columnas: EAN (extraído del nombre), texto (mapeado), pendiente stock (omitir)
    ean_cols = {}
    texto_cols = {}
    for col in df_inov.columns:
        s = str(col).strip()
        if s in _INOV_PENDIENTE_STOCK:
            continue
        if s in _INOV_TEXTO_A_CODIGO:
            texto_cols[col] = _INOV_TEXTO_A_CODIGO[s]
            continue
        m = re.match(r'^(\d{6,})\s*-', s)
        if m:
            ean_cols[col] = int(m.group(1))
    activas = {**ean_cols, **texto_cols}

    # Ventas del mes actual desde ventas_validas (Timestamps)
    primer_dia_ts = fecha_ejecucion.replace(day=1)
    vmes = ventas_validas.loc[
        (ventas_validas["fecha_comprobante"] >= primer_dia_ts) &
        (ventas_validas["fecha_comprobante"] <= fecha_ejecucion) &
        (ventas_validas["importe_neto"] > 0)
    ].copy()
    vmes["_codigo_int"] = pd.to_numeric(vmes["Codigo"], errors="coerce").astype("Int64")
    vmes_clean = vmes.dropna(subset=["cliente_id", "_codigo_int"])
    compras = set(zip(vmes_clean["cliente_id"].astype(int), vmes_clean["_codigo_int"].astype(int)))

    # Lookup vendedor desde maestro de clientes
    cli_map = (
        clientes[["cliente_id", "cliente_nombre", "vendedor_codigo"]]
        .drop_duplicates("cliente_id")
        .set_index("cliente_id")
    )

    filas = []
    for _, row in df_inov.iterrows():
        cli_id = int(row["cliente_id"])
        plan = row["plan_as"]
        inov_activas = 0
        inov_compradas = 0
        faltantes = []

        for col, codigo in activas.items():
            val = row.get(col, None)
            if pd.isna(val):
                continue  # producto no aplica para este cliente
            inov_activas += 1
            if (cli_id, codigo) in compras:
                inov_compradas += 1
            else:
                label = str(col).split(" - ", 1)[-1].strip() if " - " in str(col) else str(col).strip()
                faltantes.append(label)

        pct = round(inov_compradas / inov_activas, 4) if inov_activas > 0 else 0.0

        if cli_id in cli_map.index:
            cli_nombre = cli_map.loc[cli_id, "cliente_nombre"]
            vend_cod = cli_map.loc[cli_id, "vendedor_codigo"]
        else:
            cli_nombre = str(row.get("Concatenado ", "")).replace("PYP - ", "").strip()
            vend_cod = None

        filas.append({
            "cliente_id": cli_id,
            "cliente_nombre": cli_nombre,
            "vendedor_codigo": vend_cod,
            "plan_as": plan,
            "innovaciones_activas": inov_activas,
            "innovaciones_compradas": inov_compradas,
            "pct_avance": pct,
            "productos_faltantes": "|".join(faltantes),
            "productos_pendiente_stock": "Antares P770|Antares P330",
        })

    df_out = pd.DataFrame(filas)
    if not df_out.empty:
        df_out.sort_values(["vendedor_codigo", "pct_avance"], ascending=[True, True], inplace=True)
        df_out.reset_index(drop=True, inplace=True)
    return df_out


def generar_mod_innovaciones_segmento(ventas_validas, clientes, fecha_ejecucion):
    """
    CCC de Frizze Manxana (14620) y Antares XPA (60020) por vendedor x segmento.
    Mes actual hasta fecha_ejecucion. V3 no aplica Autoservicio.
    Solo vendedores activos Peñaflor: V3,V4,V6,V7,V8,V9,V10.
    """
    SEGMENTOS = ["TRADICIONAL", "AUTOSERVICIO"]
    VENDEDORES_ACTIVOS = [3, 4, 6, 7, 8, 9, 10]

    primer_dia_ts = fecha_ejecucion.replace(day=1)
    vmes = ventas_validas.loc[
        (ventas_validas["fecha_comprobante"] >= primer_dia_ts) &
        (ventas_validas["fecha_comprobante"] <= fecha_ejecucion) &
        (ventas_validas["importe_neto"] > 0)
    ].copy()
    vmes["_codigo_int"] = pd.to_numeric(vmes["Codigo"], errors="coerce").astype("Int64")
    vmes_inov = vmes[
        vmes["_codigo_int"].isin(_INOV2_PRODUCTOS.keys()) &
        vmes["vendedor_codigo"].isin(VENDEDORES_ACTIVOS)
    ].copy()

    cli_seg = clientes[
        clientes["segmento_operativo"].isin(SEGMENTOS) &
        clientes["vendedor_codigo"].isin(VENDEDORES_ACTIVOS)
    ][["cliente_id", "vendedor_codigo", "vendedor_nombre", "segmento_operativo"]].copy()

    # V3 no aplica para Autoservicio
    cli_seg = cli_seg[~(
        (cli_seg["vendedor_codigo"] == 3) &
        (cli_seg["segmento_operativo"] == "AUTOSERVICIO")
    )].copy()

    filas = []
    for vend_cod, grp_vend in cli_seg.groupby("vendedor_codigo"):
        vend_nombre = grp_vend["vendedor_nombre"].iloc[0]
        for seg in SEGMENTOS:
            grp_seg = grp_vend[grp_vend["segmento_operativo"] == seg]
            if grp_seg.empty:
                continue
            cartera_ids = set(grp_seg["cliente_id"].dropna().astype(int))
            for cod, nombre in _INOV2_PRODUCTOS.items():
                compraron_ids = set(
                    vmes_inov[
                        (vmes_inov["vendedor_codigo"] == vend_cod) &
                        (vmes_inov["_codigo_int"] == cod)
                    ]["cliente_id"].dropna().astype(int)
                )
                compraron = compraron_ids & cartera_ids
                faltantes = cartera_ids - compraron
                filas.append({
                    "fecha_ejecucion": fecha_ejecucion.date(),
                    "vendedor_codigo": int(vend_cod),
                    "vendedor_nombre": vend_nombre,
                    "segmento": seg,
                    "producto_codigo": cod,
                    "producto_nombre": nombre,
                    "clientes_cartera": len(cartera_ids),
                    "clientes_compraron": len(compraron),
                    "pct_cobertura": round(len(compraron) / len(cartera_ids), 4) if cartera_ids else 0.0,
                    "clientes_faltantes": "|".join(str(x) for x in sorted(faltantes)),
                })

    df_out = pd.DataFrame(filas)
    if not df_out.empty:
        df_out.sort_values(["vendedor_codigo", "segmento", "producto_codigo"], inplace=True)
        df_out.reset_index(drop=True, inplace=True)
    return df_out


# ============================================================
# CARGA DE ARCHIVOS
# ============================================================

def cargar_clientes(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)

    columnas_esperadas = [
        "Codigo", "Razon_Social", "Direccion", "Localidad", "codven", "Vendedor",
        "CodigoRuta", "Ruta", "Orden", "DiasVisita", "Ramo", "SubSegmento"
    ]
    faltantes = [c for c in columnas_esperadas if c not in df.columns]
    if faltantes:
        raise ValueError(f"clientes.xlsx no tiene columnas esperadas: {faltantes}")

    df = df.copy()
    df["cliente_id"] = pd.to_numeric(df["Codigo"], errors="coerce").astype("Int64")
    df["cliente_nombre"] = df["Razon_Social"].astype(str).str.strip()
    df["direccion"] = df["Direccion"].astype(str).fillna("").str.strip()
    df["localidad"] = df["Localidad"].astype(str).fillna("").str.strip()
    df["vendedor_codigo"] = pd.to_numeric(df["codven"], errors="coerce").astype("Int64")
    df["vendedor_nombre"] = df["Vendedor"].astype(str).fillna("").str.strip()
    df["codigo_ruta"] = df["CodigoRuta"].astype(str).fillna("").str.strip()
    df["ruta"] = df["Ruta"].astype(str).fillna("").str.strip()
    df["orden"] = pd.to_numeric(df["Orden"], errors="coerce")
    df["dias_visita"] = df["DiasVisita"].astype(str).fillna("").str.strip()
    df["ramo"] = df["Ramo"].astype(str).fillna("").str.strip()
    df["subsegmento"] = df["SubSegmento"].astype(str).fillna("").str.strip()

    df = df.loc[~df["vendedor_codigo"].isin(VENDEDORES_EXCLUIDOS)].copy()
    df = df.loc[~df["cliente_id"].isin(_cargar_clientes_excluidos())].copy()
    # Exclusión dinámica: sin DiasVisita y Ruta contiene DEPOSITO → no son clientes de ruta programada
    mask_deposito_sin_dia = (
        df["ruta"].str.contains("DEPOSITO", case=False, na=False) &
        df["dias_visita"].isin(["", "nan", "NaN", "None", "<NA>"])
    )
    df = df.loc[~mask_deposito_sin_dia].copy()
    df["segmento_operativo"] = df.apply(lambda r: clasificar_segmento_operativo(r["ramo"], r["subsegmento"]), axis=1)
    df["segmento_11t"] = df.apply(lambda r: clasificar_segmento_11t(r["ramo"], r["subsegmento"], r["segmento_operativo"]), axis=1)
    df["umbral_cobertura"] = df["segmento_operativo"].map(threshold_cobertura)

    mask_vend3_auto = ((df["vendedor_codigo"] == 3) & (df["segmento_operativo"] == "AUTOSERVICIO"))
    df = df.loc[~mask_vend3_auto].copy()
    return df

def cargar_ventas(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="latin1")

    columnas_esperadas = [
        "Cliente", "FechaComprobante", "CantBase", "ImporteNetoItem",
        "ImporteItem", "RazonSocial", "MotivoDevolucion", "Descuento",
        "CodVendedor", "Vendedor", "RutaPreventa", "Articulo",
        "NetoItem", "Ramo", "Subramo", "valorDescuento", "Marca"
    ]
    faltantes = [c for c in columnas_esperadas if c not in df.columns]
    if faltantes:
        raise ValueError(f"ventas.csv no tiene columnas esperadas: {faltantes}")

    df = df.copy()
    df["cliente_id"] = pd.to_numeric(df["Cliente"], errors="coerce").astype("Int64")
    df["vendedor_codigo"] = pd.to_numeric(df["CodVendedor"], errors="coerce").astype("Int64")
    df["vendedor_nombre"] = df["Vendedor"].astype(str).fillna("").str.strip()
    df["cliente_nombre"] = df["RazonSocial"].astype(str).fillna("").str.strip()

    df["fecha_comprobante"] = pd.to_datetime(df["FechaComprobante"], dayfirst=True, errors="coerce").dt.normalize()
    df["cant_base"] = df["CantBase"].apply(parse_num_ar)
    df["importe_neto"] = df["ImporteNetoItem"].apply(parse_num_ar)
    df["importe_item"] = df["ImporteItem"].apply(parse_num_ar)
    df["neto_item"] = df["NetoItem"].apply(parse_num_ar)
    df["valor_descuento"] = df["valorDescuento"].apply(parse_num_ar)
    df["descuento_pct"] = df["Descuento"].apply(parse_pct)

    df["motivo_devolucion"] = df["MotivoDevolucion"].fillna("").astype(str).str.strip()
    df["ramo"] = df["Ramo"].astype(str).fillna("").str.strip()
    df["subramo"] = df["Subramo"].astype(str).fillna("").str.strip()
    df["marca"] = df["Marca"].astype(str).fillna("").str.strip()
    df["articulo"] = df["Articulo"].astype(str).fillna("").str.strip()
    df["ruta_preventa"] = df["RutaPreventa"].astype(str).fillna("").str.strip()

    df = df.loc[~df["vendedor_codigo"].isin(VENDEDORES_EXCLUIDOS)].copy()
    df = df.loc[~df["cliente_id"].isin(_cargar_clientes_excluidos())].copy()

    df["marca_limpia"] = df["marca"].apply(limpiar_texto_comercial)
    df["articulo_limpio"] = df["articulo"].apply(limpiar_texto_comercial)

    df["venta_valida"] = (
        (df["cant_base"] > 0) &
        (df["importe_neto"] > 0) &
        (df["motivo_devolucion"] == "")
    )
    return df

def cargar_resultado(path: str):
    xls = pd.ExcelFile(path)
    if "Avance" not in xls.sheet_names:
        raise ValueError("resultado.xlsx no contiene la hoja 'Avance'")
    if "Rechazos" not in xls.sheet_names:
        raise ValueError("resultado.xlsx no contiene la hoja 'Rechazos'")

    avance = pd.read_excel(path, sheet_name="Avance")
    rechazos = pd.read_excel(path, sheet_name="Rechazos")

    avance["VendedorCodigo"] = pd.to_numeric(avance["VendedorCodigo"], errors="coerce").astype("Int64")
    rechazos["VendedorCodigo"] = pd.to_numeric(rechazos["VendedorCodigo"], errors="coerce").astype("Int64")

    avance = avance.loc[~avance["VendedorCodigo"].isin(VENDEDORES_EXCLUIDOS)].copy()
    rechazos = rechazos.loc[~rechazos["VendedorCodigo"].isin(VENDEDORES_EXCLUIDOS)].copy()
    return avance, rechazos

def cargar_productos(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()

    try:
        xl = pd.ExcelFile(path)
    except Exception:
        return pd.DataFrame()

    frames = []
    for sh in xl.sheet_names:
        try:
            tmp = pd.read_excel(path, sheet_name=sh)
            if not tmp.empty:
                tmp["__sheet__"] = sh
                frames.append(tmp)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.copy()
    cols_lower = {c: str(c).strip().lower() for c in df.columns}
    df.rename(columns=cols_lower, inplace=True)

    # candidatos flexibles
    col_cod = None
    col_desc = None
    col_marca = None

    for c in df.columns:
        c_low = str(c).lower()
        if col_cod is None and any(k in c_low for k in ["codigo", "cod", "articulo", "sku", "item"]):
            col_cod = c
        if col_desc is None and any(k in c_low for k in ["descripcion", "desc", "producto", "articulo"]):
            col_desc = c
        if col_marca is None and "marca" in c_low:
            col_marca = c

    if col_cod is None and len(df.columns) > 0:
        col_cod = df.columns[0]
    if col_desc is None and len(df.columns) > 1:
        col_desc = df.columns[1]

    producto_codigo_ref = pd.to_numeric(df[col_cod], errors="coerce") if col_cod else np.nan
    producto_desc_ref = df[col_desc].astype(str).fillna("").apply(limpiar_texto_comercial) if col_desc else ""
    producto_marca_ref = df[col_marca].astype(str).fillna("").apply(limpiar_texto_comercial) if col_marca else ""

    prod = pd.DataFrame({
        "producto_codigo_ref": producto_codigo_ref,
        "producto_desc_ref": producto_desc_ref,
        "producto_marca_ref": producto_marca_ref,
    })

    # si la marca viene vacía, la derivamos desde la descripción
    prod["producto_marca_ref"] = np.where(
        prod["producto_marca_ref"].fillna("") != "",
        prod["producto_marca_ref"],
        prod["producto_desc_ref"].apply(detectar_marca_desde_texto)
    )

    prod = prod.loc[
        (prod["producto_desc_ref"].fillna("") != "") | (prod["producto_marca_ref"].fillna("") != "")
    ].drop_duplicates().copy()

    return prod

# ============================================================
# HISTORIAL
# ============================================================

def actualizar_historial_ventas(ventas_validas: pd.DataFrame) -> pd.DataFrame:
    ensure_dir(HISTORY_DIR)

    cols_hist = [
        "fecha_comprobante", "cliente_id", "cliente_nombre", "vendedor_codigo", "vendedor_nombre",
        "articulo_final", "marca_final", "ramo", "subramo", "cant_base", "importe_neto",
        "valor_descuento", "descuento_pct"
    ]

    actual = ventas_validas[cols_hist].copy()
    actual.rename(columns={"articulo_final": "articulo", "marca_final": "marca"}, inplace=True)
    actual["fecha_comprobante"] = pd.to_datetime(actual["fecha_comprobante"], errors="coerce").dt.date

    if os.path.exists(HISTORY_FILE):
        try:
            hist = pd.read_csv(HISTORY_FILE)
            if "fecha_comprobante" in hist.columns:
                hist["fecha_comprobante"] = pd.to_datetime(hist["fecha_comprobante"], errors="coerce").dt.date
        except Exception:
            hist = pd.DataFrame(columns=[
                "fecha_comprobante", "cliente_id", "cliente_nombre", "vendedor_codigo", "vendedor_nombre",
                "articulo", "marca", "ramo", "subramo", "cant_base", "importe_neto",
                "valor_descuento", "descuento_pct"
            ])
    else:
        hist = pd.DataFrame(columns=[
            "fecha_comprobante", "cliente_id", "cliente_nombre", "vendedor_codigo", "vendedor_nombre",
            "articulo", "marca", "ramo", "subramo", "cant_base", "importe_neto",
            "valor_descuento", "descuento_pct"
        ])

    combinado = pd.concat([hist, actual], ignore_index=True)

    dedup_cols = [
        "fecha_comprobante", "cliente_id", "vendedor_codigo", "articulo",
        "cant_base", "importe_neto", "descuento_pct"
    ]
    combinado = combinado.drop_duplicates(subset=dedup_cols, keep="last").copy()

    # Retención: mantener solo los últimos 90 días (ventana móvil).
    # Antes no había tope → el historial crecía sin límite. 90 días alcanza para
    # el criterio de clientes dormidos (+60 días) con margen.
    RETENCION_DIAS = 90
    _f = pd.to_datetime(combinado["fecha_comprobante"], errors="coerce")
    if _f.notna().any():
        corte = _f.max() - pd.Timedelta(days=RETENCION_DIAS)
        combinado = combinado[_f >= corte].copy()

    combinado.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
    return combinado

# ============================================================
# ENRIQUECIMIENTO PRODUCTOS
# ============================================================

def enriquecer_ventas_con_productos(ventas_df: pd.DataFrame, productos_df: pd.DataFrame) -> pd.DataFrame:
    df = ventas_df.copy()

    # Base inicial por texto y detección desde artículo
    df["marca_final"] = np.where(
        df["marca_limpia"].fillna("") != "",
        df["marca_limpia"],
        df["articulo_limpio"].apply(detectar_marca_desde_texto)
    )
    df["articulo_final"] = df["articulo_limpio"]

    if productos_df is None or productos_df.empty:
        # segunda pasada: si sigue vacía la marca, derivarla otra vez
        df["marca_final"] = np.where(
            df["marca_final"].fillna("") != "",
            df["marca_final"],
            df["articulo_final"].apply(detectar_marca_desde_texto)
        )
        return df

    prod = productos_df.copy()

    # match por descripción exacta limpia
    desc_map = prod[["producto_desc_ref", "producto_marca_ref"]].drop_duplicates().copy()

    df = df.merge(
        desc_map,
        how="left",
        left_on="articulo_limpio",
        right_on="producto_desc_ref"
    )

    df["marca_final"] = np.where(
        df["producto_marca_ref"].fillna("") != "",
        df["producto_marca_ref"],
        df["marca_final"]
    )

    # si aún sigue vacía, intentamos por contains entre descripción de producto y artículo de ventas
    faltan = df["marca_final"].fillna("") == ""
    if faltan.any():
        prod_valid = prod.loc[prod["producto_desc_ref"].fillna("") != ""].copy()
        prod_valid = prod_valid.sort_values(by="producto_desc_ref", key=lambda s: s.str.len(), ascending=False)

        for idx in df.index[faltan]:
            art = df.at[idx, "articulo_limpio"]
            if not art:
                continue

            match = prod_valid.loc[
                prod_valid["producto_desc_ref"].apply(lambda x: x in art if isinstance(x, str) and x != "" else False)
            ]
            if len(match) > 0:
                marca_match = match.iloc[0]["producto_marca_ref"]
                if isinstance(marca_match, str) and marca_match.strip() != "":
                    df.at[idx, "marca_final"] = marca_match

    # última pasada: derivación desde artículo
    df["marca_final"] = np.where(
        df["marca_final"].fillna("") != "",
        df["marca_final"],
        df["articulo_limpio"].apply(detectar_marca_desde_texto)
    )

    df["marca_final"] = df["marca_final"].fillna("")
    df["articulo_final"] = df["articulo_final"].fillna("")

    return df

# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def main():
    log_rows = []
    ensure_dir(OUTPUT_DIR)
    ensure_dir(HISTORY_DIR)

    build_log(log_rows, "INICIO_PROCESO", "ORBIT MATINAL PEÑA V4.2")

    clientes = cargar_clientes(INPUT_CLIENTES)
    build_log(log_rows, "CLIENTES_CARGADOS", len(clientes))

    ventas = cargar_ventas(INPUT_VENTAS)
    build_log(log_rows, "VENTAS_CARGADAS", len(ventas))

    avance, rechazos = cargar_resultado(INPUT_RESULTADO)
    build_log(log_rows, "AVANCE_CARGADO", len(avance))
    build_log(log_rows, "RECHAZOS_CARGADO", len(rechazos))

    productos = cargar_productos(INPUT_PRODUCTOS)
    build_log(log_rows, "PRODUCTOS_CARGADOS", len(productos))

    ventas = enriquecer_ventas_con_productos(ventas, productos)
    build_log(log_rows, "VENTAS_ENRIQUECIDAS", len(ventas))

    fecha_ejecucion = ventas["fecha_comprobante"].max()
    if pd.isna(fecha_ejecucion):
        raise ValueError("No se pudo detectar fecha_ejecucion desde ventas.csv")

    feriados_set = cargar_feriados()
    fecha_objetivo = siguiente_dia_operativo(fecha_ejecucion, clientes, feriados_set)
    dia_objetivo_abbr = map_day_abbr(fecha_objetivo)

    build_log(log_rows, "FECHA_EJECUCION", fecha_ejecucion.strftime("%Y-%m-%d"))
    build_log(log_rows, "FECHA_OBJETIVO", fecha_objetivo.strftime("%Y-%m-%d"))
    build_log(log_rows, "DIA_OBJETIVO", dia_objetivo_abbr)

    ventas_validas = ventas.loc[ventas["venta_valida"]].copy()
    build_log(log_rows, "VENTAS_VALIDAS", len(ventas_validas))

    historial_ventas = actualizar_historial_ventas(ventas_validas)
    build_log(log_rows, "HISTORIAL_VENTAS_FILAS", len(historial_ventas))

    ventas_ayer = ventas_validas.loc[ventas_validas["fecha_comprobante"] == fecha_ejecucion].copy()
    build_log(log_rows, "VENTAS_VALIDAS_DIA", len(ventas_ayer))

    _primer_dia_mes = fecha_ejecucion.replace(day=1).date()
    ventas_mes = historial_ventas.loc[
        (historial_ventas["fecha_comprobante"] >= _primer_dia_mes) &
        (historial_ventas["fecha_comprobante"] <= fecha_ejecucion.date())
    ].copy().rename(columns={"marca": "marca_final", "articulo": "articulo_final"})
    build_log(log_rows, "VENTAS_VALIDAS_MES", len(ventas_mes))

    # =========================
    # CLIENTES DEL DIA
    # =========================

    clientes_dia = clientes.loc[clientes["dias_visita"] == dia_objetivo_abbr].copy()
    build_log(log_rows, "CLIENTES_DIA_OBJETIVO", len(clientes_dia))

    agg_ayer = (
        ventas_ayer.groupby(["cliente_id", "vendedor_codigo"], dropna=False)
        .agg(botellas_ayer=("cant_base", "sum"), importe_ayer=("importe_neto", "sum"))
        .reset_index()
    )

    agg_mes = (
        ventas_mes.groupby(["cliente_id", "vendedor_codigo"], dropna=False)
        .agg(botellas_mes=("cant_base", "sum"), importe_mes=("importe_neto", "sum"))
        .reset_index()
    )

    clientes_dia = clientes_dia.merge(agg_ayer, how="left", on=["cliente_id", "vendedor_codigo"])
    clientes_dia = clientes_dia.merge(agg_mes, how="left", on=["cliente_id", "vendedor_codigo"])

    for c in ["botellas_ayer", "importe_ayer", "botellas_mes", "importe_mes"]:
        clientes_dia[c] = clientes_dia[c].fillna(0.0)

    clientes_dia["compra_ayer_flag"] = (clientes_dia["importe_ayer"] > 0).astype(int)
    clientes_dia["ccc_ayer_flag"] = (clientes_dia["importe_ayer"] > 0).astype(int)
    clientes_dia["cobertura_ayer_flag"] = (clientes_dia["botellas_ayer"] >= clientes_dia["umbral_cobertura"]).astype(int)

    clientes_dia["compra_mes_flag"] = (clientes_dia["importe_mes"] > 0).astype(int)
    clientes_dia["ccc_mes_flag"] = (clientes_dia["importe_mes"] > 0).astype(int)
    clientes_dia["cobertura_mes_flag"] = (clientes_dia["botellas_mes"] >= clientes_dia["umbral_cobertura"]).astype(int)

    def estado_cliente(row):
        if row["ccc_mes_flag"] == 0:
            return "SIN_COMPRA_MES"
        if row["ccc_mes_flag"] == 1 and row["cobertura_mes_flag"] == 0:
            return "CCC_SIN_COBERTURA"
        if row["cobertura_mes_flag"] == 1:
            return "COBERTURA_OK"
        return "REVISAR"

    def prioridad_comercial(row):
        if row["ccc_mes_flag"] == 0:
            return "ALTA"
        if row["ccc_mes_flag"] == 1 and row["cobertura_mes_flag"] == 0:
            return "ALTA"
        return "MEDIA"

    clientes_dia["estado_cliente"] = clientes_dia.apply(estado_cliente, axis=1)
    clientes_dia["prioridad_comercial"] = clientes_dia.apply(prioridad_comercial, axis=1)
    clientes_dia["fecha_ejecucion"] = fecha_ejecucion.date()
    clientes_dia["fecha_objetivo"] = fecha_objetivo.date()
    clientes_dia["dia_objetivo"] = dia_objetivo_abbr
    clientes_dia["negocio_id"] = NEGOCIO_ID
    clientes_dia["negocio_nombre"] = NEGOCIO_NOMBRE

    clientes_dia = clientes_dia[
        [
            "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
            "vendedor_codigo","vendedor_nombre","cliente_id","cliente_nombre","localidad","direccion",
            "codigo_ruta","ruta","orden","dias_visita","ramo","subsegmento","segmento_operativo",
            "segmento_11t","umbral_cobertura","botellas_ayer","importe_ayer","compra_ayer_flag",
            "ccc_ayer_flag","cobertura_ayer_flag","botellas_mes","importe_mes","compra_mes_flag",
            "ccc_mes_flag","cobertura_mes_flag","estado_cliente","prioridad_comercial"
        ]
    ].copy()

    clientes_dia.sort_values(by=["vendedor_codigo", "ruta", "orden", "cliente_nombre"], inplace=True, na_position="last")
    build_log(log_rows, "CLIENTES_DIA_GENERADOS", len(clientes_dia))

    # =========================
    # MOD VOLUMEN VENDEDOR
    # =========================

    clientes_resumen = (
        clientes_dia.groupby(["vendedor_codigo", "vendedor_nombre"], dropna=False)
        .agg(
            clientes_planificados=("cliente_id", "nunique"),
            clientes_trad=("segmento_operativo", lambda s: int((s == "TRADICIONAL").sum())),
            clientes_auto=("segmento_operativo", lambda s: int((s == "AUTOSERVICIO").sum())),
            clientes_on=("segmento_operativo", lambda s: int((s == "ON_PREMISE_VTK").sum())),
            clientes_cobertura_mes_ok=("cobertura_mes_flag", "sum"),
            clientes_sin_compra_mes=("ccc_mes_flag", lambda s: int((s == 0).sum())),
        )
        .reset_index()
    )

    real_ayer_vendedor = (
        ventas_ayer.groupby(["vendedor_codigo", "vendedor_nombre"], dropna=False)
        .agg(
            venta_ayer=("importe_neto", "sum"),
            botellas_ayer=("cant_base", "sum"),
            clientes_compra_ayer=("cliente_id", "nunique"),
        )
        .reset_index()
    )

    avance_sel = avance[
        ["VendedorCodigo","VendedorNombre","ValorObjetivo","Acumulado","Tendencia","Avance","Promedio","MediaNecesaria","Real"]
    ].copy()

    avance_sel.rename(columns={
        "VendedorCodigo": "vendedor_codigo",
        "VendedorNombre": "vendedor_nombre_resultado",
        "ValorObjetivo": "objetivo_mes",
        "Acumulado": "acumulado_mes",
        "Tendencia": "tendencia_mes",
        "Avance": "avance_pct",
        "Promedio": "promedio_dia",
        "MediaNecesaria": "media_necesaria",
        "Real": "real_resultado",
    }, inplace=True)

    if "PorcCambio" not in rechazos.columns:
        rechazos["PorcCambio"] = 0.0
    rechazos_sel = rechazos[["VendedorCodigo", "PorcRechazo", "PorcCambio"]].copy()
    rechazos_sel.rename(columns={
        "VendedorCodigo": "vendedor_codigo",
        "PorcRechazo": "rechazo_pct",
        "PorcCambio": "cambio_pct",
    }, inplace=True)

    mod_volumen_vendedor = clientes_resumen.merge(real_ayer_vendedor, how="left", on=["vendedor_codigo", "vendedor_nombre"])
    mod_volumen_vendedor = mod_volumen_vendedor.merge(avance_sel, how="left", on="vendedor_codigo")
    mod_volumen_vendedor = mod_volumen_vendedor.merge(rechazos_sel, how="left", on="vendedor_codigo")

    for c in [
        "venta_ayer","botellas_ayer","clientes_compra_ayer","objetivo_mes","acumulado_mes",
        "tendencia_mes","avance_pct","promedio_dia","media_necesaria","real_resultado",
        "rechazo_pct","cambio_pct"
    ]:
        if c in mod_volumen_vendedor.columns:
            mod_volumen_vendedor[c] = mod_volumen_vendedor[c].fillna(0)

    mod_volumen_vendedor["vendedor_nombre_final"] = np.where(
        mod_volumen_vendedor["vendedor_nombre"].astype(str).str.strip() != "",
        mod_volumen_vendedor["vendedor_nombre"],
        mod_volumen_vendedor["vendedor_nombre_resultado"]
    )

    mod_volumen_vendedor["fecha_ejecucion"] = fecha_ejecucion.date()
    mod_volumen_vendedor["fecha_objetivo"] = fecha_objetivo.date()
    mod_volumen_vendedor["dia_objetivo"] = dia_objetivo_abbr
    mod_volumen_vendedor["negocio_id"] = NEGOCIO_ID
    mod_volumen_vendedor["negocio_nombre"] = NEGOCIO_NOMBRE

    mod_volumen_vendedor = mod_volumen_vendedor[
        [
            "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
            "vendedor_codigo","vendedor_nombre_final","clientes_planificados","clientes_trad",
            "clientes_auto","clientes_on","clientes_cobertura_mes_ok","clientes_sin_compra_mes",
            "clientes_compra_ayer","botellas_ayer","venta_ayer","objetivo_mes","acumulado_mes",
            "tendencia_mes","avance_pct","promedio_dia","media_necesaria","real_resultado",
            "rechazo_pct","cambio_pct"
        ]
    ].copy()

    mod_volumen_vendedor.rename(columns={"vendedor_nombre_final": "vendedor_nombre"}, inplace=True)
    mod_volumen_vendedor.sort_values(by=["vendedor_codigo"], inplace=True)
    build_log(log_rows, "MOD_VOLUMEN_VENDEDOR_GENERADO", len(mod_volumen_vendedor))

    # =========================
    # MOD CCC SEGMENTO
    # =========================

    ventas_ayer_seg = ventas_ayer.merge(
        clientes[["cliente_id", "vendedor_codigo", "segmento_operativo"]].drop_duplicates(),
        how="left", on=["cliente_id", "vendedor_codigo"]
    )
    ventas_ayer_seg["segmento_operativo"] = ventas_ayer_seg["segmento_operativo"].fillna("OTROS")

    ccc_seg = (
        ventas_ayer_seg.groupby(["vendedor_codigo", "vendedor_nombre", "segmento_operativo"], dropna=False)
        .agg(
            clientes_con_compra=("cliente_id", "nunique"),
            botellas_vendidas=("cant_base", "sum"),
            venta_neta=("importe_neto", "sum"),
        )
        .reset_index()
    )

    cobertura_cli_seg = (
        ventas_ayer_seg.groupby(["vendedor_codigo","vendedor_nombre","segmento_operativo","cliente_id"], dropna=False)
        .agg(botellas_cliente=("cant_base", "sum"), venta_cliente=("importe_neto", "sum"))
        .reset_index()
    )

    cobertura_cli_seg["umbral"] = cobertura_cli_seg["segmento_operativo"].map(threshold_cobertura)
    cobertura_cli_seg["cobertura_ok"] = (
        (cobertura_cli_seg["venta_cliente"] > 0) &
        (cobertura_cli_seg["botellas_cliente"] >= cobertura_cli_seg["umbral"])
    ).astype(int)

    cobertura_seg = (
        cobertura_cli_seg.groupby(["vendedor_codigo","vendedor_nombre","segmento_operativo"], dropna=False)
        .agg(coberturas_logradas=("cobertura_ok", "sum"))
        .reset_index()
    )

    mod_ccc_segmento = ccc_seg.merge(cobertura_seg, how="left", on=["vendedor_codigo","vendedor_nombre","segmento_operativo"])
    mod_ccc_segmento["coberturas_logradas"] = mod_ccc_segmento["coberturas_logradas"].fillna(0).astype(int)
    mod_ccc_segmento["fecha_ejecucion"] = fecha_ejecucion.date()
    mod_ccc_segmento["fecha_objetivo"] = fecha_objetivo.date()
    mod_ccc_segmento["dia_objetivo"] = dia_objetivo_abbr
    mod_ccc_segmento["negocio_id"] = NEGOCIO_ID
    mod_ccc_segmento["negocio_nombre"] = NEGOCIO_NOMBRE

    mod_ccc_segmento = mod_ccc_segmento[
        [
            "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
            "vendedor_codigo","vendedor_nombre","segmento_operativo","clientes_con_compra",
            "coberturas_logradas","botellas_vendidas","venta_neta"
        ]
    ].copy()

    mod_ccc_segmento.sort_values(by=["vendedor_codigo", "segmento_operativo"], inplace=True)
    build_log(log_rows, "MOD_CCC_SEGMENTO_GENERADO", len(mod_ccc_segmento))

    # =========================
    # MOD 11 TITULARES
    # =========================

    marcas_mes = (
        ventas_mes.groupby(["cliente_id","vendedor_codigo","marca_final","articulo_final"], dropna=False)
        .agg(botellas_mes=("cant_base", "sum"), importe_mes=("importe_neto", "sum"))
        .reset_index()
    )

    filas_11t = []
    for _, row in clientes_dia.iterrows():
        segmento_cli = row["segmento_11t"]
        lista_marcas = MAP_11T_FINE.get(segmento_cli, MAP_11T_FINE["OTROS"])

        for marca_obj in lista_marcas:
            mask = marcas_mes.apply(
                lambda x: (
                    x["cliente_id"] == row["cliente_id"] and
                    x["vendedor_codigo"] == row["vendedor_codigo"] and
                    match_marca_objetivo(x["marca_final"], x["articulo_final"], marca_obj)
                ),
                axis=1
            )
            match = marcas_mes.loc[mask].copy()

            tiene_flag = 1 if len(match) > 0 else 0
            botellas_m = float(match["botellas_mes"].sum()) if len(match) > 0 else 0.0
            importe_m = float(match["importe_mes"].sum()) if len(match) > 0 else 0.0

            filas_11t.append({
                "fecha_ejecucion": fecha_ejecucion.date(),
                "fecha_objetivo": fecha_objetivo.date(),
                "dia_objetivo": dia_objetivo_abbr,
                "negocio_id": NEGOCIO_ID,
                "negocio_nombre": NEGOCIO_NOMBRE,
                "vendedor_codigo": row["vendedor_codigo"],
                "vendedor_nombre": row["vendedor_nombre"],
                "cliente_id": row["cliente_id"],
                "cliente_nombre": row["cliente_nombre"],
                "segmento_operativo": row["segmento_operativo"],
                "segmento_11t": segmento_cli,
                "marca_objetivo": marca_obj,
                "tiene_flag": tiene_flag,
                "falta_flag": 1 - tiene_flag,
                "botellas_mes": botellas_m,
                "importe_mes": importe_m,
                "prioridad_marca": prioridad_11t(tiene_flag, botellas_m),
            })

    mod_11_titulares = pd.DataFrame(filas_11t)
    mod_11_titulares.sort_values(by=["vendedor_codigo", "cliente_nombre", "marca_objetivo"], inplace=True)
    build_log(log_rows, "MOD_11_TITULARES_GENERADO", len(mod_11_titulares))

    # =========================
    # MOD ALERTAS DESCUENTOS
    # =========================

    ventas_alerta = ventas_ayer.merge(
        clientes[["cliente_id","vendedor_codigo","segmento_11t"]].drop_duplicates(),
        how="left", on=["cliente_id", "vendedor_codigo"]
    )
    ventas_alerta["segmento_11t"] = ventas_alerta["segmento_11t"].fillna("OTROS")
    ventas_alerta["cajas_eq"] = ventas_alerta.apply(lambda r: cajas_equivalentes(r["cant_base"], r["articulo_final"]), axis=1)

    maximos = ventas_alerta.apply(calcular_descuento_maximo, axis=1)
    ventas_alerta["descuento_maximo_pct"] = [m[0] for m in maximos]
    ventas_alerta["fuente_regla"] = [m[1] for m in maximos]
    ventas_alerta["regla_encontrada"] = ~ventas_alerta["descuento_maximo_pct"].isna()
    ventas_alerta["exceso_pct"] = ventas_alerta["descuento_pct"] - ventas_alerta["descuento_maximo_pct"]

    ventas_alertadas = ventas_alerta.loc[
        (ventas_alerta["regla_encontrada"]) &
        (ventas_alerta["exceso_pct"] > TOLERANCIA_EXCESO_PCT)
    ].copy()

    mod_alertas_descuentos = pd.DataFrame(columns=[
        "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
        "vendedor_codigo","vendedor_nombre","cliente_id","cliente_nombre","segmento_11t",
        "articulo","marca","cant_base","cajas_eq","descuento_aplicado_pct","descuento_maximo_pct",
        "exceso_pct","fuente_regla","importe_neto","valor_descuento"
    ])

    if len(ventas_alertadas) > 0:
        mod_alertas_descuentos = ventas_alertadas.rename(columns={"descuento_pct": "descuento_aplicado_pct"})[
            [
                "cliente_id","cliente_nombre","vendedor_codigo","vendedor_nombre","segmento_11t",
                "articulo_final","marca_final","cant_base","cajas_eq","descuento_aplicado_pct","descuento_maximo_pct",
                "exceso_pct","fuente_regla","importe_neto","valor_descuento"
            ]
        ].copy()

        mod_alertas_descuentos.rename(columns={"articulo_final": "articulo", "marca_final": "marca"}, inplace=True)

        mod_alertas_descuentos["fecha_ejecucion"] = fecha_ejecucion.date()
        mod_alertas_descuentos["fecha_objetivo"] = fecha_objetivo.date()
        mod_alertas_descuentos["dia_objetivo"] = dia_objetivo_abbr
        mod_alertas_descuentos["negocio_id"] = NEGOCIO_ID
        mod_alertas_descuentos["negocio_nombre"] = NEGOCIO_NOMBRE

        mod_alertas_descuentos = mod_alertas_descuentos[
            [
                "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
                "vendedor_codigo","vendedor_nombre","cliente_id","cliente_nombre","segmento_11t",
                "articulo","marca","cant_base","cajas_eq","descuento_aplicado_pct","descuento_maximo_pct",
                "exceso_pct","fuente_regla","importe_neto","valor_descuento"
            ]
        ].copy()

        mod_alertas_descuentos.sort_values(by=["vendedor_codigo", "cliente_nombre", "articulo"], inplace=True)

    build_log(log_rows, "MOD_ALERTAS_DESCUENTOS_GENERADO", len(mod_alertas_descuentos))

    # =========================
    # MOD GASTOS POR ACCION
    # =========================

    mod_gastos_accion = pd.DataFrame(columns=[
        "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
        "accion_id","es_regla_csv","canal","categoria",
        "vendedor_codigo","vendedor_nombre",
        "clientes_afectados","lineas_alertadas",
        "gasto_real_total","gasto_teorico_total","exceso_pesos_total","exceso_pct_promedio"
    ])

    if len(mod_alertas_descuentos) > 0:
        gasto_src = mod_alertas_descuentos.copy()

        # valor_descuento del ERP es por unidad; cant_base da el total de la línea (neto de IVA)
        gasto_src["gasto_real"]    = gasto_src["valor_descuento"] * gasto_src["cant_base"]
        # gasto_teorico usando la misma base bruta implícita (escala proporcional al pct máximo)
        gasto_src["gasto_teorico"] = gasto_src["gasto_real"] * (
            gasto_src["descuento_maximo_pct"] / gasto_src["descuento_aplicado_pct"].replace(0, np.nan)
        )
        gasto_src["exceso_pesos"]  = gasto_src["gasto_real"] - gasto_src["gasto_teorico"]

        grp = (
            gasto_src.groupby(["fuente_regla", "vendedor_codigo", "vendedor_nombre"], dropna=False)
            .agg(
                clientes_afectados=("cliente_id", "nunique"),
                lineas_alertadas=("articulo", "count"),
                gasto_real_total=("gasto_real", "sum"),
                gasto_teorico_total=("gasto_teorico", "sum"),
                exceso_pesos_total=("exceso_pesos", "sum"),
                exceso_pct_promedio=("exceso_pct", "mean"),
            )
            .reset_index()
        )

        grp = grp[grp["exceso_pesos_total"] > 0].copy()

        reglas_ref = _cargar_reglas_csv()
        if not reglas_ref.empty and "accion_id" in reglas_ref.columns:
            canal_map     = reglas_ref.drop_duplicates("accion_id").set_index("accion_id")["canal"].to_dict()
            categoria_map = reglas_ref.drop_duplicates("accion_id").set_index("accion_id")["categoria"].to_dict()
        else:
            canal_map = {}
            categoria_map = {}

        grp["accion_id"]    = grp["fuente_regla"]
        grp["es_regla_csv"] = grp["fuente_regla"].str.startswith("MAY26-")
        grp["canal"]        = grp["fuente_regla"].map(canal_map).fillna("FALLBACK")
        grp["categoria"]    = grp["fuente_regla"].map(categoria_map).fillna("")

        grp["fecha_ejecucion"] = fecha_ejecucion.date()
        grp["fecha_objetivo"]  = fecha_objetivo.date()
        grp["dia_objetivo"]    = dia_objetivo_abbr
        grp["negocio_id"]      = NEGOCIO_ID
        grp["negocio_nombre"]  = NEGOCIO_NOMBRE

        mod_gastos_accion = grp[[
            "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
            "accion_id","es_regla_csv","canal","categoria",
            "vendedor_codigo","vendedor_nombre",
            "clientes_afectados","lineas_alertadas",
            "gasto_real_total","gasto_teorico_total","exceso_pesos_total","exceso_pct_promedio"
        ]].copy()

        mod_gastos_accion.sort_values(by=["exceso_pesos_total"], ascending=False, inplace=True)

    build_log(log_rows, "MOD_GASTOS_ACCION_GENERADO", len(mod_gastos_accion))

    # =========================
    # RESUMEN ALERTAS VENDEDOR
    # =========================

    resumen_alertas_vendedor = pd.DataFrame(columns=[
        "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
        "vendedor_codigo","vendedor_nombre","cantidad_alertas","exceso_pct_total","exceso_pct_promedio"
    ])

    if len(mod_alertas_descuentos) > 0:
        resumen_alertas_vendedor = (
            mod_alertas_descuentos.groupby(["vendedor_codigo","vendedor_nombre"], dropna=False)
            .agg(
                cantidad_alertas=("articulo", "count"),
                exceso_pct_total=("exceso_pct", "sum"),
                exceso_pct_promedio=("exceso_pct", "mean"),
            )
            .reset_index()
        )

        resumen_alertas_vendedor["fecha_ejecucion"] = fecha_ejecucion.date()
        resumen_alertas_vendedor["fecha_objetivo"] = fecha_objetivo.date()
        resumen_alertas_vendedor["dia_objetivo"] = dia_objetivo_abbr
        resumen_alertas_vendedor["negocio_id"] = NEGOCIO_ID
        resumen_alertas_vendedor["negocio_nombre"] = NEGOCIO_NOMBRE

        resumen_alertas_vendedor = resumen_alertas_vendedor[
            [
                "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
                "vendedor_codigo","vendedor_nombre","cantidad_alertas","exceso_pct_total","exceso_pct_promedio"
            ]
        ].copy()

        resumen_alertas_vendedor.sort_values(by=["cantidad_alertas", "exceso_pct_total"], ascending=[False, False], inplace=True)

    build_log(log_rows, "RESUMEN_ALERTAS_VENDEDOR_GENERADO", len(resumen_alertas_vendedor))

    # =========================
    # MOD INVERSION DESCUENTOS
    # =========================

    ventas_inversion = ventas_ayer.merge(
        clientes[["cliente_id","vendedor_codigo","segmento_11t","segmento_operativo"]].drop_duplicates(),
        how="left", on=["cliente_id", "vendedor_codigo"]
    )

    ventas_inversion["segmento_11t"] = ventas_inversion["segmento_11t"].fillna("OTROS")
    ventas_inversion["segmento_operativo"] = ventas_inversion["segmento_operativo"].fillna("OTROS")

    ventas_con_desc = ventas_inversion.loc[
        (ventas_inversion["descuento_pct"] > 0) | (ventas_inversion["valor_descuento"] > 0)
    ].copy()

    mod_inversion_descuentos = pd.DataFrame(columns=[
        "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
        "vendedor_codigo","vendedor_nombre","segmento_operativo","segmento_11t","marca",
        "clientes_con_compra","articulos_con_desc","inversion_total","venta_total","botellas_total","roi_comercial"
    ])

    if len(ventas_con_desc) > 0:
        mod_inversion_descuentos = (
            ventas_con_desc.groupby(
                ["vendedor_codigo","vendedor_nombre","segmento_operativo","segmento_11t","marca_final"],
                dropna=False
            )
            .agg(
                clientes_con_compra=("cliente_id", "nunique"),
                articulos_con_desc=("articulo_final", "count"),
                inversion_total=("valor_descuento", "sum"),
                venta_total=("importe_neto", "sum"),
                botellas_total=("cant_base", "sum"),
            )
            .reset_index()
        )

        mod_inversion_descuentos["roi_comercial"] = np.where(
            mod_inversion_descuentos["inversion_total"] > 0,
            mod_inversion_descuentos["venta_total"] / mod_inversion_descuentos["inversion_total"],
            np.nan
        )

        mod_inversion_descuentos["fecha_ejecucion"] = fecha_ejecucion.date()
        mod_inversion_descuentos["fecha_objetivo"] = fecha_objetivo.date()
        mod_inversion_descuentos["dia_objetivo"] = dia_objetivo_abbr
        mod_inversion_descuentos["negocio_id"] = NEGOCIO_ID
        mod_inversion_descuentos["negocio_nombre"] = NEGOCIO_NOMBRE

        mod_inversion_descuentos.rename(columns={"marca_final": "marca"}, inplace=True)

        mod_inversion_descuentos = mod_inversion_descuentos[
            [
                "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
                "vendedor_codigo","vendedor_nombre","segmento_operativo","segmento_11t","marca",
                "clientes_con_compra","articulos_con_desc","inversion_total","venta_total","botellas_total","roi_comercial"
            ]
        ].copy()

        mod_inversion_descuentos.sort_values(by=["inversion_total", "venta_total"], ascending=[False, False], inplace=True)

    build_log(log_rows, "MOD_INVERSION_DESCUENTOS_GENERADO", len(mod_inversion_descuentos))

    # =========================
    # MOD CLIENTES COMPRA 11T CON 10%
    # =========================

    ventas_11t_desc = ventas_ayer.merge(
        clientes[["cliente_id","vendedor_codigo","segmento_11t","segmento_operativo"]].drop_duplicates(),
        how="left", on=["cliente_id", "vendedor_codigo"]
    )

    ventas_11t_desc["segmento_11t"] = ventas_11t_desc["segmento_11t"].fillna("OTROS")
    ventas_11t_desc["segmento_operativo"] = ventas_11t_desc["segmento_operativo"].fillna("OTROS")

    mask_trad_kiosco = ventas_11t_desc["segmento_operativo"] == "TRADICIONAL"
    mask_desc_10 = ventas_11t_desc["descuento_pct"] >= 10

    ventas_11t_desc["es_11t_marca"] = ventas_11t_desc.apply(
        lambda r: es_11t_por_segmento(r["articulo_final"], r["marca_final"], r["segmento_11t"]),
        axis=1
    )

    ventas_11t_10 = ventas_11t_desc.loc[
        mask_trad_kiosco & mask_desc_10 & ventas_11t_desc["es_11t_marca"]
    ].copy()

    mod_clientes_compra_11t_desc = pd.DataFrame(columns=[
        "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
        "marca","clientes_con_compra","venta_total","botellas_total","inversion_total","descuento_promedio_pct"
    ])

    if len(ventas_11t_10) > 0:
        def marca_objetivo_detectada(row):
            seg = row["segmento_11t"]
            candidatos = MAP_11T_FINE.get(seg, [])
            for m in candidatos:
                if match_marca_objetivo(row["marca_final"], row["articulo_final"], m):
                    return m
            return row["marca_final"]

        ventas_11t_10["marca_objetivo_detectada"] = ventas_11t_10.apply(marca_objetivo_detectada, axis=1)

        mod_clientes_compra_11t_desc = (
            ventas_11t_10.groupby(["marca_objetivo_detectada"], dropna=False)
            .agg(
                clientes_con_compra=("cliente_id", "nunique"),
                venta_total=("importe_neto", "sum"),
                botellas_total=("cant_base", "sum"),
                inversion_total=("valor_descuento", "sum"),
                descuento_promedio_pct=("descuento_pct", "mean"),
            )
            .reset_index()
        )

        mod_clientes_compra_11t_desc.rename(columns={"marca_objetivo_detectada": "marca"}, inplace=True)

        mod_clientes_compra_11t_desc["fecha_ejecucion"] = fecha_ejecucion.date()
        mod_clientes_compra_11t_desc["fecha_objetivo"] = fecha_objetivo.date()
        mod_clientes_compra_11t_desc["dia_objetivo"] = dia_objetivo_abbr
        mod_clientes_compra_11t_desc["negocio_id"] = NEGOCIO_ID
        mod_clientes_compra_11t_desc["negocio_nombre"] = NEGOCIO_NOMBRE

        mod_clientes_compra_11t_desc = mod_clientes_compra_11t_desc[
            [
                "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
                "marca","clientes_con_compra","venta_total","botellas_total","inversion_total","descuento_promedio_pct"
            ]
        ].copy()

        mod_clientes_compra_11t_desc.sort_values(by=["clientes_con_compra", "venta_total"], ascending=[False, False], inplace=True)

    build_log(log_rows, "MOD_CLIENTES_COMPRA_11T_DESC_GENERADO", len(mod_clientes_compra_11t_desc))

    # =========================
    # MOD EFICIENCIA DESCUENTO
    # =========================

    hist = historial_ventas.copy()
    hist["fecha_comprobante"] = pd.to_datetime(hist["fecha_comprobante"], errors="coerce").dt.date

    fecha_ejec_date = fecha_ejecucion.date()
    hist_prev = hist.loc[hist["fecha_comprobante"] < fecha_ejec_date].copy()

    hist_prev["descuento_pct"] = hist_prev["descuento_pct"].apply(parse_num_ar)
    hist_prev["marca"] = hist_prev["marca"].astype(str).fillna("").apply(limpiar_texto_comercial)
    hist_prev["articulo"] = hist_prev["articulo"].astype(str).fillna("").apply(limpiar_texto_comercial)

    base_sin_desc = hist_prev.loc[hist_prev["descuento_pct"] <= 0].copy()
    base_solo_desc = hist_prev.loc[hist_prev["descuento_pct"] > 0].copy()

    baseline_no_desc = (
        base_sin_desc.groupby(["cliente_id", "marca"], dropna=False)
        .agg(
            baseline_botellas_sin_desc=("cant_base", "mean"),
            baseline_venta_sin_desc=("importe_neto", "mean"),
            baseline_visitas_sin_desc=("fecha_comprobante", "nunique"),
        )
        .reset_index()
    )

    baseline_desc = (
        base_solo_desc.groupby(["cliente_id", "marca"], dropna=False)
        .agg(
            hist_desc_botellas=("cant_base", "mean"),
            hist_desc_visitas=("fecha_comprobante", "nunique"),
        )
        .reset_index()
    )

    ventas_desc_hoy = ventas_ayer.loc[
        (ventas_ayer["descuento_pct"] > 0) | (ventas_ayer["valor_descuento"] > 0)
    ].copy()

    ventas_desc_hoy = ventas_desc_hoy.merge(
        clientes[["cliente_id","vendedor_codigo","segmento_11t","segmento_operativo"]].drop_duplicates(),
        how="left", on=["cliente_id", "vendedor_codigo"]
    )
    ventas_desc_hoy["segmento_11t"] = ventas_desc_hoy["segmento_11t"].fillna("OTROS")
    ventas_desc_hoy["segmento_operativo"] = ventas_desc_hoy["segmento_operativo"].fillna("OTROS")

    mod_eficiencia_desc = pd.DataFrame(columns=[
        "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
        "vendedor_codigo","vendedor_nombre","cliente_id","cliente_nombre","segmento_operativo","segmento_11t",
        "marca","articulo","descuento_pct","valor_descuento","importe_neto","cant_base",
        "factor_volumen_necesario","crecimiento_min_pct",
        "baseline_botellas_sin_desc","baseline_venta_sin_desc","baseline_visitas_sin_desc",
        "volumen_objetivo_compensar","indice_compensacion","estado_eficiencia"
    ])

    if len(ventas_desc_hoy) > 0:
        ventas_desc_hoy = ventas_desc_hoy.copy()
        ventas_desc_hoy["marca_hist_key"] = ventas_desc_hoy["marca_final"]

        mod_eficiencia_desc = ventas_desc_hoy.merge(
            baseline_no_desc, how="left", left_on=["cliente_id", "marca_hist_key"], right_on=["cliente_id", "marca"]
        ).merge(
            baseline_desc, how="left", left_on=["cliente_id", "marca_hist_key"], right_on=["cliente_id", "marca"], suffixes=("", "_histdesc")
        )

        mod_eficiencia_desc["factor_volumen_necesario"] = mod_eficiencia_desc["descuento_pct"].apply(factor_volumen_necesario)
        mod_eficiencia_desc["crecimiento_min_pct"] = mod_eficiencia_desc["factor_volumen_necesario"] - 1.0
        mod_eficiencia_desc["volumen_objetivo_compensar"] = (
            mod_eficiencia_desc["baseline_botellas_sin_desc"] * mod_eficiencia_desc["factor_volumen_necesario"]
        )

        mod_eficiencia_desc["indice_compensacion"] = np.where(
            mod_eficiencia_desc["volumen_objetivo_compensar"] > 0,
            mod_eficiencia_desc["cant_base"] / mod_eficiencia_desc["volumen_objetivo_compensar"],
            np.nan
        )

        def estado_eficiencia(row):
            base = row["baseline_botellas_sin_desc"]
            hist_desc = row.get("hist_desc_visitas", np.nan)

            if pd.isna(base) or base <= 0:
                if not pd.isna(hist_desc) and hist_desc > 0:
                    return "SOLO_HISTORICO_CON_DESCUENTO"
                return "SIN_BASE_HISTORICA"

            if pd.isna(row["indice_compensacion"]):
                return "SIN_BASE_HISTORICA"

            if row["indice_compensacion"] >= 1:
                return "OK"

            return "NO_OK"

        mod_eficiencia_desc["estado_eficiencia"] = mod_eficiencia_desc.apply(estado_eficiencia, axis=1)

        mod_eficiencia_desc["fecha_ejecucion"] = fecha_ejec_date
        mod_eficiencia_desc["fecha_objetivo"] = fecha_objetivo.date()
        mod_eficiencia_desc["dia_objetivo"] = dia_objetivo_abbr
        mod_eficiencia_desc["negocio_id"] = NEGOCIO_ID
        mod_eficiencia_desc["negocio_nombre"] = NEGOCIO_NOMBRE
        mod_eficiencia_desc["marca"] = mod_eficiencia_desc["marca_final"]
        mod_eficiencia_desc["articulo"] = mod_eficiencia_desc["articulo_final"]

        mod_eficiencia_desc = mod_eficiencia_desc[
            [
                "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
                "vendedor_codigo","vendedor_nombre","cliente_id","cliente_nombre","segmento_operativo","segmento_11t",
                "marca","articulo","descuento_pct","valor_descuento","importe_neto","cant_base",
                "factor_volumen_necesario","crecimiento_min_pct",
                "baseline_botellas_sin_desc","baseline_venta_sin_desc","baseline_visitas_sin_desc",
                "volumen_objetivo_compensar","indice_compensacion","estado_eficiencia"
            ]
        ].copy()

        mod_eficiencia_desc.sort_values(by=["estado_eficiencia", "vendedor_codigo", "cliente_nombre"], inplace=True)

    build_log(log_rows, "MOD_EFICIENCIA_DESC_GENERADO", len(mod_eficiencia_desc))

    # =========================
    # MOD REINTEGROS CONTROL
    # =========================

    mod_reintegros_control = pd.DataFrame(columns=[
        "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
        "periodo_origen","periodo_reintegro_esperado",
        "vendedor_codigo","vendedor_nombre","cliente_id","cliente_nombre","marca",
        "inversion_descuento","venta_generada","estado_reintegro"
    ])

    if len(ventas_con_desc) > 0:
        periodo_origen = fecha_ejecucion.strftime("%Y-%m")
        periodo_reintegro_esperado = (fecha_ejecucion + pd.offsets.MonthBegin(1)).strftime("%Y-%m")

        mod_reintegros_control = (
            ventas_con_desc.groupby(
                ["vendedor_codigo","vendedor_nombre","cliente_id","cliente_nombre","marca_final"],
                dropna=False
            )
            .agg(
                inversion_descuento=("valor_descuento", "sum"),
                venta_generada=("importe_neto", "sum"),
            )
            .reset_index()
        )

        mod_reintegros_control.rename(columns={"marca_final": "marca"}, inplace=True)

        mod_reintegros_control["fecha_ejecucion"] = fecha_ejec_date
        mod_reintegros_control["fecha_objetivo"] = fecha_objetivo.date()
        mod_reintegros_control["dia_objetivo"] = dia_objetivo_abbr
        mod_reintegros_control["negocio_id"] = NEGOCIO_ID
        mod_reintegros_control["negocio_nombre"] = NEGOCIO_NOMBRE
        mod_reintegros_control["periodo_origen"] = periodo_origen
        mod_reintegros_control["periodo_reintegro_esperado"] = periodo_reintegro_esperado
        mod_reintegros_control["estado_reintegro"] = "PENDIENTE_CONTROL"

        mod_reintegros_control = mod_reintegros_control[
            [
                "fecha_ejecucion","fecha_objetivo","dia_objetivo","negocio_id","negocio_nombre",
                "periodo_origen","periodo_reintegro_esperado",
                "vendedor_codigo","vendedor_nombre","cliente_id","cliente_nombre","marca",
                "inversion_descuento","venta_generada","estado_reintegro"
            ]
        ].copy()

        mod_reintegros_control.sort_values(by=["inversion_descuento", "venta_generada"], ascending=[False, False], inplace=True)

    build_log(log_rows, "MOD_REINTEGROS_CONTROL_GENERADO", len(mod_reintegros_control))

    # =========================
    # MOD INNOVACIONES PLAN AS
    # =========================
    mod_innovaciones_plan_as = generar_mod_innovaciones_plan_as(ventas_validas, clientes, fecha_ejecucion)
    build_log(log_rows, "MOD_INNOVACIONES_PLAN_AS", len(mod_innovaciones_plan_as))

    # =========================
    # MOD INNOVACIONES SEGMENTO
    # =========================
    mod_innovaciones_segmento = generar_mod_innovaciones_segmento(ventas_validas, clientes, fecha_ejecucion)
    build_log(log_rows, "MOD_INNOVACIONES_SEGMENTO", len(mod_innovaciones_segmento))

    # =========================
    # LOG MOTOR
    # =========================

    log_motor = pd.DataFrame(log_rows)
    log_motor.insert(0, "TIMESTAMP", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))

    # =========================
    # EXPORT FINAL
    # =========================

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        clientes_dia.to_excel(writer, sheet_name="clientes_dia", index=False)
        mod_volumen_vendedor.to_excel(writer, sheet_name="mod_volumen_vendedor", index=False)
        mod_ccc_segmento.to_excel(writer, sheet_name="mod_ccc_segmento", index=False)
        mod_11_titulares.to_excel(writer, sheet_name="mod_11_titulares", index=False)
        mod_alertas_descuentos.to_excel(writer, sheet_name="mod_alertas_descuentos", index=False)
        resumen_alertas_vendedor.to_excel(writer, sheet_name="resumen_alertas_vend", index=False)
        mod_inversion_descuentos.to_excel(writer, sheet_name="mod_inversion_desc", index=False)
        mod_clientes_compra_11t_desc.to_excel(writer, sheet_name="mod_clientes_11t_10", index=False)
        mod_eficiencia_desc.to_excel(writer, sheet_name="mod_eficiencia_desc", index=False)
        mod_reintegros_control.to_excel(writer, sheet_name="mod_reintegros_ctrl", index=False)
        mod_gastos_accion.to_excel(writer, sheet_name="mod_gastos_accion", index=False)
        mod_innovaciones_plan_as.to_excel(writer, sheet_name="mod_innovaciones_plan_as", index=False)
        mod_innovaciones_segmento.to_excel(writer, sheet_name="mod_innovaciones_segmento", index=False)
        log_motor.to_excel(writer, sheet_name="log_motor", index=False)

    print("OK - Archivo generado correctamente:")
    print(OUTPUT_FILE)
    print("")
    print(f"Fecha ejecución detectada              : {fecha_ejecucion.date()}")
    print(f"Fecha objetivo calculada               : {fecha_objetivo.date()}")
    print(f"Día objetivo                           : {dia_objetivo_abbr}")
    print(f"Ventas válidas                         : {len(ventas_validas)}")
    print(f"Ventas válidas del día                 : {len(ventas_ayer)}")
    print(f"Clientes del día                       : {len(clientes_dia)}")
    print(f"Vendedores resumidos                   : {len(mod_volumen_vendedor)}")
    print(f"CCC por segmento filas                 : {len(mod_ccc_segmento)}")
    print(f"11 titulares filas                     : {len(mod_11_titulares)}")
    print(f"Alertas de descuentos                  : {len(mod_alertas_descuentos)}")
    print(f"Resumen alertas vendedor               : {len(resumen_alertas_vendedor)}")
    print(f"Inversión descuentos filas             : {len(mod_inversion_descuentos)}")
    print(f"Clientes compra 11T con 10% filas      : {len(mod_clientes_compra_11t_desc)}")
    print(f"Eficiencia descuento filas             : {len(mod_eficiencia_desc)}")
    print(f"Reintegros control filas               : {len(mod_reintegros_control)}")
    print(f"Innovaciones Plan AS filas             : {len(mod_innovaciones_plan_as)}")
    print(f"Innovaciones segmento filas            : {len(mod_innovaciones_segmento)}")
    print(f"Historial ventas archivo               : {HISTORY_FILE}")

if __name__ == "__main__":
    main()