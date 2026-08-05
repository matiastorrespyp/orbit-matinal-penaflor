"""
generar_datasets_acum.py
Genera tres datasets desde ventas_acumulada.csv + fuentes secundarias.
Salidas en 04_DATASETS_ORBIT/:
  mod_cobertura_acum.csv  — cobertura por segmento (periodo acumulado)
  mod_11t_acum.csv        — 11 Titulares acumulado (autoservicio + tradicional)
  mod_planes_as.csv       — Planes AS: facturacion, cajas ganadas, sin cargo enviado
"""
import sys
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

import motor_11t          # motor autoritativo de cobertura 11T (única fuente de la regla)
import motor_padron       # regla única de pertenencia de cartera (duplicados del padrón)

BASE = Path(__file__).parent
OUT  = BASE / "04_DATASETS_ORBIT"
OUT.mkdir(exist_ok=True)

VENDEDORES_EXCLUIDOS = {1, 2, 5, 20}

# SubSegmentos que identifican AUTOSERVICIO (fuente autoritativa: clientes.xlsx columna SubSegmento)
_AS_SUBSEG = {
    "AUTOSERVICIO TRADICIONAL", "AUTOSERVICIO",
    "CADENA REGIONAL", "CADENAS REGIONALES (SAR)", "CADENAS REGIONALES (BAR)",
    "LARGE FORMAT",
}
# SubSegmentos/Ramos que identifican MAYORISTA (canal separado — NO es AUTOSERVICIO)
_MAY_SUBSEG = {
    "MAYORISTAS", "MAYORISTA", "MAYORISTA REGIONALES",
    "CASH&CARRY", "CASH & CARRY",
}
# Claves ON_PREMISE
_OP_KEYWORDS = {
    "ON PREMISE", "AWAY FROM HOME", "VINOTECA", "VINOTECAS", "BAR",
    "RESTAURANT", "RESTAURANTE", "EVENTOS",
    "TEMPORADA", "CATERING", "ON DIA", "ON NOCHE",
}
# Claves PROXIMITY (estaciones de servicio) — canal propio por decisión del negocio
# 2026-07-30. No son On Premise ni Autoservicio: se miden aparte, con umbral 6.
_PROX_KEYWORDS = {
    "PROXIMITY", "ESTACION DE SERVICIO", "ESTACIONES DE SERVICIO",
}
# Claves TRADICIONAL. "KIOSK" cubre las dos grafías del ERP (KIOSCO y KIOSKO).
_TR_KEYWORDS = {
    "TRADITIONAL TRADE", "ALMACEN", "DESPENSA", "KIOSCO", "KIOSK", "MAXIKIOSCO",
    "FIAMBRERIA", "CARNICERIA", "GRANJA", "PANADERIA", "CASA DE PASTAS",
    "VERDULERIA", "TRADICIONAL",
}

def _clasificar(ramo: str, subseg: str) -> str:
    """EL SUBSEGMENTO MANDA SOBRE EL RAMO. El ERP mete carnicerías, verdulerías y
    panaderías bajo Ramo = AWAY FROM HOME: si se mira el Ramo primero, un almacén de
    barrio termina clasificado On Premise y se le mide cobertura con 6 botellas en vez
    de 3 (corregido 2026-07-30). Mismo criterio que ya regía para AUTOSERVICIO."""
    s = str(subseg).upper().strip()
    r = str(ramo).upper().strip()
    # MAYORISTA: va primero para que nunca caiga en AUTOSERVICIO
    if s in _MAY_SUBSEG or r in {"CASH&CARRY", "MAYORISTAS", "MAYORISTA"}:
        return "MAYORISTA"
    # AUTOSERVICIO: SubSegmento como fuente primaria (regla de negocio).
    # "CADENAS REGIONALES" tiene que resolverse acá: `CADENAS REGIONALES (BAR)` es un formato
    # de supermercado grande, no un bar, y más abajo el `(BAR)` matchearía la clave "BAR".
    if (s in _AS_SUBSEG or r in {"AUTOSERVICIO", "LARGE FORMAT"}
            or "CADENA REGIONAL" in s or "CADENAS REGIONALES" in s
            or "CADENA REGIONAL" in r or "CADENAS REGIONALES" in r):
        return "AUTOSERVICIO"
    # PROXIMITY antes que On Premise: el SubSegmento dice "Estacion de Servicio - AXION",
    # que matchea las claves de OP si se lo deja pasar.
    if any(k in s for k in _PROX_KEYWORDS) or any(k in r for k in _PROX_KEYWORDS):
        return "PROXIMITY"
    # SubSegmento (dato fino del ERP): decide solo, sin mirar el Ramo
    if any(k in s for k in _OP_KEYWORDS):
        return "ON_PREMISE"
    if any(k in s for k in _TR_KEYWORDS):
        return "TRADICIONAL"
    # Recién ahora el Ramo, como fallback para los que no traen SubSegmento útil
    if any(k in r for k in _OP_KEYWORDS):
        return "ON_PREMISE"
    if any(k in r for k in _TR_KEYWORDS):
        return "TRADICIONAL"
    return "OTROS"

def _clasificar_subcanal(ramo: str, subseg: str) -> str:
    """Subcanal fino para Innovaciones (5 grupos: AUTOSERVICIO, ALMACEN, KIOSCO,
    ON_PREMISE, MAYORISTA). Deriva de _clasificar() y parte TRADICIONAL en KIOSCO
    (kiosco/maxikiosco) vs ALMACEN (resto de tradicionales — decisión usuario 2026-06-23).
    Agrega de vuelta exacto a _seg: ALMACEN + KIOSCO == TRADICIONAL."""
    base = _clasificar(ramo, subseg)
    if base == "TRADICIONAL":
        s = str(subseg).upper(); r = str(ramo).upper()
        if "KIOSC" in s or "KIOSK" in s or "KIOSC" in r or "KIOSK" in r:
            return "KIOSCO"
        return "ALMACEN"
    return base

UMBRAL = {
    "AUTOSERVICIO": 6,
    "TRADICIONAL":  3,
    "ON_PREMISE":   6,
    "VINOTECAS":    6,
    "MAYORISTA":    6,
    "PROXIMITY":    6,   # estaciones de servicio (decisión del negocio 2026-07-30)
}

# Los 11 Titulares y su universo de SKU salen de la MATRIZ OFICIAL, vía motor_11t.
# Acá NO se repite la lista: tener una copia local fue lo que dejó a Gordon's, Antares y
# Smirnoff Flavours en 0 durante meses (el ERP escribe `GORDON'S FLAVORS`, `SMIRNOFF` y
# `ANTARES ESPECIALES`, que ninguna tabla de alias local contemplaba).
# Ver motor_11t.titulares_oficiales() y motor_11t.cargar_matriz_11t().
#
# ELIMINADOS 2026-08-05: _ONCE_TITULARES, MAP_11T, MARCA_ALIASES y ALIAS_LOOKUP.
# El match del 11T es por código de artículo contra la matriz; el texto de `Marca` solo
# vale como respaldo exacto y lo resuelve el motor.

# Innovaciones: codigo_articulo → nombre_comercial.
# Lista por defecto (fallback). La fuente OFICIAL es 01_INPUTS/INNOVACIONES/Innovaciones.xlsx
# (formato "CODIGO - NOMBRE"); _cargar_inov_productos() la lee al iniciar.
_INOV_PRODUCTOS_DEFAULT = {
    14620: "FRIZZE MANXANA POP 6X1000",
    60020: "ANTARES XPA LATA 6X473",
    74813: "DADA EXTRA BRUT 6X750",
    80094: "NC SPARK EXTRA BRUT LATA 4X6X355",
    14619: "FRIZZE BUBBLE MOOD 6X1000",
    74830: "DADA SIDRA 6X750",
    30139: "GORDONS TROPICAL FRUITS 6X700",
    74749: "INTOCABLES DOUBLE OAK 6X750",
    44396: "BLEND DE EXTREMOS PN 6X750",
    14425: "TERMIDOR BLANCO DULCE 12X1LT",
    42376: "DON DAVID RED BLEND 6X750",
    74814: "CAZADOR MALBEC 6X750",
    74815: "CAZADOR CAB SAU 6X750",
    74816: "CAZADOR BLANCO DULCE 6X750",
    74827: "ALMA MORA BLANCO DULCE LOW 6X750",
    74840: "TRAPICHE DULCE COSECHA TINTO 6X750",
    74786: "EL BAUTISMO CABERNET 6X750",
    60021: "ANTARES LAGER PORRON 6X330",
    74884: "DADA LATA TINTO VERANO 4X6X355",
    60022: "ANTARES LAGER 660 6X660",
}

def _cargar_inov_productos():
    """Productos innovación (codigo→nombre) desde 01_INPUTS/INNOVACIONES/Innovaciones.xlsx
    (formato 'CODIGO - NOMBRE', una por fila). Fuente única para la pantalla de innovaciones
    de ambos perfiles. Si falta el archivo o no se puede leer, usa la lista por defecto."""
    p = BASE / "01_INPUTS" / "INNOVACIONES" / "Innovaciones.xlsx"
    if not p.exists():
        return dict(_INOV_PRODUCTOS_DEFAULT)
    try:
        df = pd.read_excel(p, sheet_name=0, header=None, dtype=str)
        out = {}
        for val in df.stack().dropna().astype(str):
            cod_part, sep, nombre = val.partition("-")
            cod = cod_part.strip().lstrip("0")
            if sep and cod.isdigit():
                out[int(cod)] = nombre.strip()
        if out:
            print(f"  Innovaciones desde: {p.name} ({len(out)} productos)")
            return out
    except Exception as e:
        print(f"  [AVISO] innovaciones {p.name}: {e}")
    return dict(_INOV_PRODUCTOS_DEFAULT)

INOV_PRODUCTOS = _cargar_inov_productos()
VENDEDORES_ACTIVOS_INOV = [3, 4, 6, 7, 8, 9, 10]

# Canales que trabaja V3 (Nadia): Tradicional y Proximity. No AS, On Premise ni Mayorista.
# En subcanal fino, TRADICIONAL se abre en ALMACEN + KIOSCO.
_V3_SEGMENTOS  = {"TRADICIONAL", "PROXIMITY"}
_V3_SUBCANALES = {"ALMACEN", "KIOSCO", "PROXIMITY"}


# ─────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────

def _parsear_ventas_csv(p):
    """Carga y normaliza un CSV de ventas (sep=;, latin1, decimales con coma)."""
    df = pd.read_csv(p, encoding="latin1", sep=";", engine="python")
    df["CantBase"] = pd.to_numeric(df["CantBase"], errors="coerce").fillna(0)
    df["ImporteNetoItem"] = (
        df["ImporteNetoItem"].astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["ImporteNetoItem"] = pd.to_numeric(df["ImporteNetoItem"], errors="coerce").fillna(0)
    df["Descuento_pct"] = (
        df["Descuento"].astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["Descuento_pct"] = pd.to_numeric(df["Descuento_pct"], errors="coerce").fillna(0)
    df["CodVendedor"] = pd.to_numeric(df["CodVendedor"], errors="coerce")
    df["Cliente"] = pd.to_numeric(df["Cliente"], errors="coerce")
    df = df[~df["CodVendedor"].isin(VENDEDORES_EXCLUIDOS)]
    return df


def cargar_ventas_acum():
    """Ventas del periodo reciente (ventas.csv) — para cobertura, 11T, acciones."""
    return _parsear_ventas_csv(BASE / "01_INPUTS" / "ventas.csv")


def cargar_ventas_acumulada():
    """Ventas acumuladas del mes completo (ventas_acumulada.csv) — para innovaciones.
    Si no existe, cae a ventas.csv con advertencia."""
    p = BASE / "01_INPUTS" / "ventas_acumulada.csv"
    if not p.exists():
        print(f"  [AVISO] ventas_acumulada.csv no encontrado, usando ventas.csv para innovaciones")
        return cargar_ventas_acum()
    return _parsear_ventas_csv(p)


def cargar_ventas_acumulada_11t():
    """ventas_acumulada.csv SIN filtrar vendedores — para el motor de cobertura 11T.

    El 11T mide CLIENTES, y el cliente pertenece a la cartera del padrón, no al vendedor
    que emitió la factura. Si acá se descartaran las filas de V20 (como hace
    `_parsear_ventas_csv`), una compra del Depósito borraría al cliente de la cobertura de
    la empresa: en julio-2026 el cliente 15 (Autoservicio de V8, 60 botellas de Gordon's
    facturadas por V20) hacía que Gordon's AS diera 6 en vez de 7.
    La exclusión de V1/V2/V5/V20 la aplica el motor sobre el vendedor del PADRÓN."""
    p = BASE / "01_INPUTS" / "ventas_acumulada.csv"
    if not p.exists():
        p = BASE / "01_INPUTS" / "ventas.csv"
    return pd.read_csv(p, encoding="latin1", sep=";", engine="python")


def snapshot_acumulado_resultado(ventas):
    """Snapshot diario del Acumulado por vendedor desde resultado.xlsx → para el real del día
    (= acumulado hoy − ayer) en Plan vs Real. Append a 02_HISTORY/acumulado_resultado_historico.csv,
    deduplicando por fecha (si se re-corre el mismo día, reescribe)."""
    rp = BASE / "01_INPUTS" / "resultado.xlsx"
    hp = BASE / "02_HISTORY" / "acumulado_resultado_historico.csv"
    if not rp.exists():
        print("  [AVISO] resultado.xlsx no existe; sin snapshot de acumulado")
        return
    try:
        av = pd.read_excel(rp, sheet_name="Avance")
    except Exception as e:
        print(f"  [AVISO] snapshot acumulado: {e}")
        return
    av.columns = [str(c).strip() for c in av.columns]
    f = (pd.to_datetime(ventas.get("FechaComprobante"), dayfirst=True, errors="coerce")
         if "FechaComprobante" in ventas.columns else None)
    fecha = (f.max().strftime("%Y-%m-%d") if (f is not None and f.notna().any())
             else datetime.now().strftime("%Y-%m-%d"))
    snap = pd.DataFrame({
        "fecha": fecha,
        "vendedor_codigo": pd.to_numeric(av["VendedorCodigo"], errors="coerce"),
        "vendedor_nombre": av["VendedorNombre"].astype(str),
        "acumulado": pd.to_numeric(av["Acumulado"], errors="coerce"),
        "objetivo": pd.to_numeric(av.get("ValorObjetivo"), errors="coerce"),
        "tendencia": pd.to_numeric(av.get("Tendencia"), errors="coerce"),
    }).dropna(subset=["vendedor_codigo"])
    snap["vendedor_codigo"] = snap["vendedor_codigo"].astype(int)
    hist = pd.DataFrame()
    if hp.exists():
        try:
            hist = pd.read_csv(hp)
            hist["fecha"] = hist["fecha"].astype(str)
            hist = hist[hist["fecha"] != fecha]
        except Exception:
            hist = pd.DataFrame()
    comb = pd.concat([hist, snap], ignore_index=True) if not hist.empty else snap
    comb = comb.sort_values(["fecha", "vendedor_codigo"])
    hp.parent.mkdir(parents=True, exist_ok=True)
    comb.to_csv(hp, index=False, encoding="utf-8-sig")
    print(f"  Snapshot acumulado resultado.xlsx -> {fecha} ({len(snap)} vendedores)")


def _dedup_clientes(df, origen=""):
    """Un cliente = una fila. El ERP exporta algunos clientes DOS veces (una por cada ruta
    en la que quedaron cargados) y, al estar en las dos carteras, inflaban el denominador de
    cobertura, CCC y planes sin que nada lo avisara — el error más caro de encontrar porque
    no rompe nada, sólo empeora los porcentajes.

    La resolución la hace `motor_padron.resolver_padron`, que es la regla única del sistema:
    V3 + V8 → prevalece V8 (decisión comercial 2026-08-05); cualquier otra colisión queda
    reportada para revisión manual, no se resuelve sola.

    Hasta 2026-08-05 acá se dejaba "la primera fila", que en la práctica mandaba los 10
    clientes duplicados a V3 según el orden de exportación del Excel."""
    df, inc = motor_padron.resolver_padron(df, col_codigo="Codigo", col_vendedor="codven",
                                           origen=origen or "generar_datasets_acum")
    motor_padron.avisar_incidencias(inc, origen or "generar_datasets_acum")
    return df


def cargar_clientes():
    p = BASE / "01_INPUTS" / "clientes.xlsx"
    df = pd.read_excel(p)
    df["codven"] = pd.to_numeric(df["codven"], errors="coerce")
    df["Codigo"] = pd.to_numeric(df["Codigo"], errors="coerce")
    df = _dedup_clientes(df, "generar_datasets_acum")
    df = df[~df["codven"].isin(VENDEDORES_EXCLUIDOS)]
    sub_col = next((c for c in df.columns if "subseg" in c.lower() or "subramo" in c.lower()), None)
    df["_seg"] = df.apply(
        lambda r: _clasificar(str(r.get("Ramo", "")), str(r.get(sub_col, "") if sub_col else "")), axis=1
    )
    df["_subcanal"] = df.apply(
        lambda r: _clasificar_subcanal(str(r.get("Ramo", "")), str(r.get(sub_col, "") if sub_col else "")), axis=1
    )
    return df


_MESES_ES = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def _ordenar_por_mes(candidatos, mes_idx=None):
    """Ordena Paths cuyo nombre incluye el mes en español (escalajulio.xlsx,
    sincargosjunio.xlsx, ...) poniendo PRIMERO el del mes ACTUAL y el resto por mtime
    (respaldo). Regla operativa: el archivo mensual se elige por el MES que dice su nombre,
    no por fecha de modificación — así el sistema pasa solo de <algo>junio.xlsx a
    <algo>julio.xlsx cuando cambia el mes, sin tocar código. Si ninguno matchea el mes en
    curso quedan todos por mtime (fail-safe: la pantalla de Planes nunca se queda sin datos)."""
    cands = list(candidatos)
    if not cands:
        return []
    mes = _MESES_ES[(mes_idx if mes_idx is not None else datetime.now().month - 1)]
    del_mes = sorted([c for c in cands if mes in c.name.lower()],
                     key=lambda f: f.stat().st_mtime, reverse=True)
    resto = sorted([c for c in cands if c not in del_mes],
                   key=lambda f: f.stat().st_mtime, reverse=True)
    return del_mes + resto


def _archivo_del_mes(candidatos, mes_idx=None):
    """Como _ordenar_por_mes pero devuelve sólo el archivo elegido para el mes (o None)."""
    orden = _ordenar_por_mes(candidatos, mes_idx)
    return orden[0] if orden else None


def _cargar_escala_df():
    """Escala del Plan AS. Prioriza 01_INPUTS/PLANES_AS/escala_*.xlsx (mensual: elige el
    archivo cuyo nombre trae el MES actual → escalajulio.xlsx en julio, escalaagosto.xlsx
    en agosto, subiendo el archivo con ese nombre). Cae a la hoja 'ESCALA' de
    Reconocimiento Plan As.xlsx. Mapea columnas por NOMBRE de encabezado (robusto a la posición).
    Devuelve DataFrame con: escala_num, thresh_gold, thresh_silver, thresh_inicial."""
    pdir = BASE / "01_INPUTS" / "PLANES_AS"
    pdir2 = BASE / "01_INPUTS" / "Planes AASS"
    candidatos = []
    for d, pat in ((pdir, "escala_*.xlsx"), (pdir2, "escala*.xlsx")):
        if d.exists():
            candidatos += list(d.glob(pat))
    # El del mes en curso primero; el resto por mtime como respaldo; luego la hoja ESCALA.
    orden = _ordenar_por_mes(set(candidatos))
    fuentes = [(c, 0) for c in orden] + [(pdir / "Reconocimiento Plan As.xlsx", "ESCALA")]
    for path, sheet in fuentes:
        if not path.exists():
            continue
        try:
            raw = pd.read_excel(path, sheet_name=sheet, header=None)
            hdr_idx = None
            for i in range(min(8, len(raw))):
                vals = [str(x).strip().upper() for x in raw.iloc[i].tolist()]
                if "ESCALA" in vals and any("GOLD" in v for v in vals):
                    hdr_idx = i
                    break
            if hdr_idx is None:
                continue
            hdr = [str(x).strip().upper() for x in raw.iloc[hdr_idx].tolist()]
            def _find(name):
                return next((j for j, h in enumerate(hdr) if h == name), None)
            c_esc, c_gold, c_silver, c_inic = _find("ESCALA"), _find("GOLD"), _find("SILVER"), _find("INICIAL")
            if None in (c_esc, c_gold, c_silver, c_inic):
                continue
            data = raw.iloc[hdr_idx + 1:]
            out = pd.DataFrame({
                "escala_num":     pd.to_numeric(data[c_esc], errors="coerce"),
                "thresh_gold":    pd.to_numeric(data[c_gold], errors="coerce"),
                "thresh_silver":  pd.to_numeric(data[c_silver], errors="coerce"),
                "thresh_inicial": pd.to_numeric(data[c_inic], errors="coerce"),
            }).dropna(subset=["escala_num"])
            if not out.empty:
                etiqueta = path.name + (f" [{sheet}]" if isinstance(sheet, str) else "")
                print(f"  Escala Plan AS desde: {etiqueta}")
                return out
        except Exception as e:
            print(f"  [AVISO] escala {path.name}: {e}")
            continue
    print("  [AVISO] No se pudo leer ninguna escala (escala_*.xlsx ni hoja ESCALA).")
    return pd.DataFrame(columns=["escala_num", "thresh_gold", "thresh_silver", "thresh_inicial"])


def _cargar_sincargos_mes():
    """Sin cargos ASIGNADOS del mes desde 01_INPUTS/Planes AASS/sincargos*.xlsx
    (elige por el MES del nombre → sincargosjulio.xlsx en julio; fallback a mtime).

    Hoja 'Planes AASS': columna código + 'Cjas Sin Cargos' (total del mes) + tabla escala
    (ESCALA 1..N → LC = marca). La escala es ACUMULATIVA: para N cajas se toman las primeras
    N posiciones de la escala y se cuentan por marca. Ej: 9 cajas con escala
    1-4 Alaris, 5-8 Alma Mora, 9 Frizze → 4 Alaris + 4 Alma Mora + 1 Frizze.

    Devuelve {cliente_id: {sc_alaris, sc_alma_mora, sc_frizze, sc_antares_ipa,
    sc_smf_flavours, sc_total_ganado}}. Si no hay archivo válido devuelve {} y el motor
    cae al cálculo por facturación (fail-safe)."""
    pdir = BASE / "01_INPUTS" / "Planes AASS"
    if not pdir.exists():
        return {}
    # marca de la escala (LC) → columna sc_* del dataset
    MARCA_COL = {
        "alaris":    "sc_alaris",
        "alma mora": "sc_alma_mora",
        "frizze":    "sc_frizze",
        "antares":   "sc_antares_ipa",
        "smirnoff":  "sc_smf_flavours",
    }
    SC_COLS = ["sc_alaris", "sc_alma_mora", "sc_frizze", "sc_antares_ipa", "sc_smf_flavours"]
    cand = _ordenar_por_mes(pdir.glob("sincargos*.xlsx"))
    for path in cand:
        try:
            df = pd.read_excel(path, sheet_name="Planes AASS", header=0)
            df.columns = [str(c).strip() for c in df.columns]
            ccol = next((c for c in df.columns
                         if c.lower().replace("í", "i").replace("�", "")
                         .strip() in ("codigo", "cdigo", "código", "cod", "cliente")), None)
            qcol = next((c for c in df.columns if "sin cargo" in c.lower()), None)
            ecol = next((c for c in df.columns if c.strip().upper() == "ESCALA"), None)
            lcol = next((c for c in df.columns if c.strip().upper() == "LC"), None)
            if not (ccol and qcol and ecol and lcol):
                print(f"  [AVISO] sincargos {path.name}: faltan columnas "
                      f"(codigo={ccol}, sincargo={qcol}, ESCALA={ecol}, LC={lcol})")
                continue
            # Tabla escala ordenada por posición → columna sc_* (None si la marca no mapea)
            esc = df[[ecol, lcol]].copy()
            esc[ecol] = pd.to_numeric(esc[ecol], errors="coerce")
            esc = esc.dropna(subset=[ecol]).sort_values(ecol)
            pos_to_col = []
            for _, r in esc.iterrows():
                marca = str(r[lcol]).strip().lower()
                pos_to_col.append(next((v for k, v in MARCA_COL.items() if k in marca), None))
            # Asignación por cliente
            out = {}
            for _, r in df[[ccol, qcol]].dropna(subset=[ccol]).iterrows():
                cid = pd.to_numeric(r[ccol], errors="coerce")
                n = pd.to_numeric(r[qcol], errors="coerce")
                if pd.isna(cid) or pd.isna(n):
                    continue
                cid, n = int(cid), int(n)
                alloc = {c: 0 for c in SC_COLS}
                for i in range(min(n, len(pos_to_col))):
                    col = pos_to_col[i]
                    if col:
                        alloc[col] += 1
                alloc["sc_total_ganado"] = sum(alloc[c] for c in SC_COLS)
                out[cid] = alloc
            if out:
                print(f"  Sin cargos del mes desde: {path.name} ({len(out)} clientes)")
                return out
        except Exception as e:
            print(f"  [AVISO] sincargos {path.name}: {e}")
    return {}


def _cargar_planfrio_mes():
    """Plan frío del mes: clientes que tienen 1 Six Pack Smirnoff ICE sin cargo.
    Hoja 'plan frío' de Planes AASS/sincargos*.xlsx (columna 'clientes' con los códigos).
    Devuelve set de cliente_id. Si no hay archivo/hoja válida devuelve set vacío."""
    pdir = BASE / "01_INPUTS" / "Planes AASS"
    if not pdir.exists():
        return set()
    cand = _ordenar_por_mes(pdir.glob("sincargos*.xlsx"))
    for path in cand:
        try:
            xl = pd.ExcelFile(path)
            hoja = next((s for s in xl.sheet_names
                         if "fr" in s.lower() and "plan" in s.lower()), None)
            if hoja is None:
                continue
            raw = xl.parse(hoja, header=None)
            # Header: fila con 'clientes'. Los códigos están en esa columna, filas siguientes.
            hdr_idx, ccol = None, None
            for i in range(min(6, len(raw))):
                for j, x in enumerate(raw.iloc[i].tolist()):
                    if str(x).strip().lower() == "clientes":
                        hdr_idx, ccol = i, j
                        break
                if hdr_idx is not None:
                    break
            if hdr_idx is None:
                continue
            cods = pd.to_numeric(raw.iloc[hdr_idx + 1:, ccol], errors="coerce").dropna()
            out = set(int(c) for c in cods)
            if out:
                print(f"  Plan frío (Six Pack Smirnoff ICE) desde: {path.name} ({len(out)} clientes)")
                return out
        except Exception as e:
            print(f"  [AVISO] plan frío {path.name}: {e}")
    return set()


def _cargar_puntera_mes():
    """Puntera del mes: cajas de un vino (cualquier varietal) sin cargo por cliente.
    Hoja 'Puntera' de Planes AASS/sincargos*.xlsx (columna código + 'Cjas Sin Cargos (<Producto>)').
    El PRODUCTO sale del encabezado de esa columna (texto entre paréntesis), así se puede cambiar
    desde el Excel sin tocar código: la etiqueta que muestra el portal y el criterio de detección
    del enviado (marca en el Articulo del ERP) siguen a ese nombre. Requisito: el nombre entre
    paréntesis debe aparecer tal cual en el Articulo del ERP (ej. 'Los Arboles' → 'LOS ARBOLES ...').
    Devuelve ({cliente_id: cajas}, producto). Si no hay archivo/hoja válida devuelve ({}, "")."""
    pdir = BASE / "01_INPUTS" / "Planes AASS"
    if not pdir.exists():
        return {}, ""
    cand = _ordenar_por_mes(pdir.glob("sincargos*.xlsx"))
    for path in cand:
        try:
            xl = pd.ExcelFile(path)
            hoja = next((s for s in xl.sheet_names if "puntera" in s.lower()), None)
            if hoja is None:
                continue
            raw = xl.parse(hoja, header=None)
            # Fila header: la que tiene 'código' (col código) y 'sin cargo' (col cajas).
            # Los headers del Excel traen mojibake (código → 'c�digo'); se normaliza dejando
            # sólo ASCII para no depender del carácter roto exacto.
            _ascii = lambda s: "".join(c for c in str(s).strip().lower() if c.isascii())
            hdr_idx = ccol = qcol = None
            for i in range(min(6, len(raw))):
                for j, x in enumerate(raw.iloc[i].tolist()):
                    xa = _ascii(x)
                    if xa in ("codigo", "cdigo", "cod", "cliente"):
                        ccol = j
                    if "sin cargo" in xa:
                        qcol = j
                if ccol is not None and qcol is not None:
                    hdr_idx = i
                    break
            if hdr_idx is None or ccol is None or qcol is None:
                continue
            # Producto = texto entre paréntesis del encabezado de la columna de cajas.
            hdr_txt = str(raw.iloc[hdr_idx, qcol])
            m = re.search(r"\(([^)]+)\)", hdr_txt)
            producto = m.group(1).strip() if m and m.group(1).strip() else "Puntera"
            out = {}
            for _, r in raw.iloc[hdr_idx + 1:].iterrows():
                cid = pd.to_numeric(r.iloc[ccol], errors="coerce")
                n = pd.to_numeric(r.iloc[qcol], errors="coerce")
                if pd.isna(cid) or pd.isna(n) or int(n) <= 0:
                    continue
                out[int(cid)] = int(n)
            if out:
                print(f"  Puntera ({producto}) desde: {path.name} ({len(out)} clientes)")
                return out, producto
        except Exception as e:
            print(f"  [AVISO] puntera {path.name}: {e}")
    return {}, ""


def _calc_escala_actual(plan_as, fact, esc_df):
    """Escala alcanzada = mayor escala cuyo umbral (según plan Gold/Silver/Inicial) es <= facturado."""
    if esc_df is None or esc_df.empty:
        return 0
    plan = str(plan_as).strip().lower()
    fact = float(fact or 0)
    if "gold" in plan:
        col = "thresh_gold"
    elif "silver" in plan:
        col = "thresh_silver"
    else:
        col = "thresh_inicial"
    validas = esc_df[esc_df[col].notna() & (esc_df[col] <= fact)]
    if validas.empty:
        return 0
    return int(validas["escala_num"].max())


def _bbdd_desde_sincargos():
    """Base de clientes Plan AS desde Planes AASS/sincargos*.xlsx cuando falta el
    Reconocimiento. Provee cliente_id, cliente_nombre, plan_as; el resto en 0.
    Facturado se recalcula de ventas.csv en generar_planes_as; sc_* se sobreescriben
    desde sincargos; dcto_plan/cant_cajas/tope no se muestran en el portal."""
    cols0 = ["total_facturado", "dcto_plan", "cant_cajas", "tope", "cant_cajas_tope",
             "sc_alaris", "sc_alma_mora", "sc_frizze", "sc_antares_ipa",
             "sc_smf_flavours", "sc_total_ganado"]
    pdir = BASE / "01_INPUTS" / "Planes AASS"
    cand = _ordenar_por_mes(pdir.glob("sincargos*.xlsx")) if pdir.exists() else []
    for path in cand:
        try:
            df = pd.read_excel(path, sheet_name="Planes AASS", header=0)
            df.columns = [str(c).strip() for c in df.columns]
            ccol = next((c for c in df.columns if c.lower().replace("í", "i").replace("�", "")
                         .strip() in ("codigo", "cdigo", "código", "cod", "cliente")), None)
            pcol = next((c for c in df.columns if c.strip().lower() == "plan"), None)
            ncol = next((c for c in df.columns if "raz" in c.lower()), None)
            if not ccol:
                continue
            base = pd.DataFrame()
            base["cliente_id"] = pd.to_numeric(df[ccol], errors="coerce")
            base["cliente_nombre"] = df[ncol].astype(str).str.strip() if ncol else ""
            base["plan_as"] = df[pcol].astype(str).str.strip() if pcol else "Inicial"
            base = base.dropna(subset=["cliente_id"]).drop_duplicates(subset=["cliente_id"])
            base["cliente_id"] = base["cliente_id"].astype(int)
            for c in cols0:
                base[c] = 0
            print(f"  [Plan AS] Base desde {path.name} (sin Reconocimiento): {len(base)} clientes")
            return base.reset_index(drop=True)
        except Exception as e:
            print(f"  [AVISO] base sincargos {path.name}: {e}")
    return pd.DataFrame(columns=["cliente_id", "cliente_nombre", "plan_as"] + cols0)


def _aplicar_escala(df):
    """Calcula escala_actual (provisoria, con el facturado disponible) y escala_max según
    plan, desde escala_*.xlsx. generar_planes_as recalcula escala_actual con la venta real
    de ventas.csv (regla 3.10)."""
    try:
        esc_df = _cargar_escala_df()
        if esc_df.empty:
            raise ValueError("escala vacía")
        df["escala_actual"] = df.apply(
            lambda r: _calc_escala_actual(r["plan_as"], r["total_facturado"], esc_df), axis=1)
        df["escala_max"] = df["plan_as"].str.lower().apply(
            lambda p: int(esc_df[esc_df["thresh_gold"].notna()]["escala_num"].max()) if "gold" in p
            else int(esc_df[esc_df["thresh_silver"].notna()]["escala_num"].max()) if "silver" in p
            else int(esc_df[esc_df["thresh_inicial"].notna()]["escala_num"].max())
        )
    except Exception as e:
        print(f"  Advertencia escala: {e}")
        df["escala_actual"] = 0
        df["escala_max"] = 0
    return df


def cargar_planes_as_bbdd():
    p = BASE / "01_INPUTS" / "PLANES_AS" / "Reconocimiento Plan As.xlsx"
    if not p.exists():
        # Sin Reconocimiento: base desde Planes AASS/sincargos*.xlsx (fallback operativo).
        df = _bbdd_desde_sincargos()
        if df.empty:
            print("  [AVISO] Plan AS: sin Reconocimiento ni sincargos; dataset vacío.")
            return df
        return _aplicar_escala(df)
    raw = pd.read_excel(p, sheet_name="BBDD", header=None)
    # Header real en fila indice 2; datos desde indice 3
    data = raw.iloc[3:].copy()
    data.columns = range(data.shape[1])
    col_map = {
        1:  "cliente_id",
        3:  "cliente_nombre",
        8:  "plan_as",
        14: "total_facturado",
        15: "dcto_plan",
        16: "cant_cajas",
        17: "tope",
        18: "cant_cajas_tope",
        19: "sc_alaris",
        20: "sc_alma_mora",
        21: "sc_frizze",
        22: "sc_antares_ipa",
        23: "sc_smf_flavours",
        24: "sc_total_ganado",
    }
    df = data[list(col_map.keys())].rename(columns=col_map)
    df["cliente_id"] = pd.to_numeric(df["cliente_id"], errors="coerce")
    for c in ["total_facturado", "dcto_plan", "cant_cajas", "tope",
              "cant_cajas_tope", "sc_alaris", "sc_alma_mora", "sc_frizze",
              "sc_antares_ipa", "sc_smf_flavours", "sc_total_ganado"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df = df.dropna(subset=["cliente_id"])
    df["cliente_id"] = df["cliente_id"].astype(int)
    df["cliente_nombre"] = df["cliente_nombre"].astype(str).str.strip()
    df["plan_as"] = df["plan_as"].astype(str).str.strip()
    return _aplicar_escala(df)


def _maestro_mes_productos():
    """Maestro del MES (01_INPUTS/RAW_PRODUCTOS/productos<mes>.xlsx) con el mismo shape que el
    04D. El 04D quedó congelado y le faltan SKU vigentes que sí se venden; sin categoría, esas
    líneas se DESCARTAN del sell out (`Categoria.notna()`) y aportan 0 litros. Devuelve DataFrame
    vacío si no hay archivo del mes. Ver el gemelo `_maestro_mes_productos` en server_orbit.py."""
    base = BASE / "01_INPUTS" / "RAW_PRODUCTOS"
    if not base.exists():
        return pd.DataFrame()
    # Ignora los `_NO_USAR_*` (exports viejos/inflados): uno con mtime nuevo seria elegido
    # como maestro del mes y cuelga el cierre. Mismo criterio que server_orbit.py.
    xls = [p for p in base.glob("*.xlsx")
           if not p.name.startswith("~$") and not p.name.startswith("_NO_USAR_")]
    if not xls:
        return pd.DataFrame()
    meses = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio",
             8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
    mes = meses.get(datetime.now().month, "")
    cand = [p for p in xls if mes and mes in p.name.lower()] or xls
    src = max(cand, key=lambda p: p.stat().st_mtime)
    try:
        raw = pd.read_excel(src, header=None, dtype=str)
        hdr = None
        for i, row in raw.iterrows():
            vals = [str(x).strip() for x in row.tolist()]
            if (any(v.startswith(("Código Art", "Codigo Art")) for v in vals)
                    and any(v.startswith("Descripci") for v in vals)):
                hdr = i
                break
        if hdr is None:
            return pd.DataFrame()
        cols = [str(x).strip() for x in raw.iloc[hdr].tolist()]
        df = raw.iloc[hdr + 1:].copy()
        df.columns = cols
        pick = lambda pred: next((c for c in cols if pred(c)), None)
        c_cod = pick(lambda c: c.startswith(("Código Art", "Codigo Art")))
        c_cat = pick(lambda c: c.startswith("Categor"))
        c_seg = pick(lambda c: c.strip().lower() == "segmento")
        c_lin = pick(lambda c: c.strip().lower().startswith("linea comercial"))
        c_des = pick(lambda c: c.startswith("Descripci"))
        c_lxc = pick(lambda c: "lts" in c.lower() and "caja" in c.lower())
        c_uxc = pick(lambda c: "unidad" in c.lower() and "caja" in c.lower())
        out = pd.DataFrame({
            "Bodega":          df.get("Bodega", ""),
            "Segmento":        df[c_seg] if c_seg else "",
            "Linea_Comercial": df[c_lin] if c_lin else "",
            "Codigo":          pd.to_numeric(df[c_cod], errors="coerce"),
            "Categoria":       df[c_cat] if c_cat else None,
            "Descripcion":     df[c_des] if c_des else "",
            "Lts_caja":        pd.to_numeric(df[c_lxc], errors="coerce").fillna(0) if c_lxc else 0,
            "UxC":             pd.to_numeric(df[c_uxc], errors="coerce") if c_uxc else None,
        })
        return out.dropna(subset=["Codigo"])
    except Exception as e:
        print(f"  [WARN] maestro del mes no se pudo leer ({src.name}): {e}")
        return pd.DataFrame()


def _cargar_04D():
    """04D en el mismo shape para las dos fuentes. Prefiere el CSV liviano de 09_CONFIG (es el
    que lee server_orbit y donde se dan de alta los códigos a mano); cae al xlsx si no está.
    Leer fuentes distintas en el server y en el generador hacía que un alta en el CSV no llegara
    a los datasets."""
    csv_path  = BASE / "09_CONFIG" / "maestro_04D_productos.csv"
    xlsx_path = BASE / "01_INPUTS" / "04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx"
    if csv_path.exists():
        c = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
        c.columns = [x.strip() for x in c.columns]
        return pd.DataFrame({
            "Bodega":          "",
            "Segmento":        c.get("Segmento", ""),
            "Linea_Comercial": c.get("Linea Comercial", ""),
            "Codigo":          pd.to_numeric(c["Codigo"], errors="coerce"),
            "Categoria":       c.get("Categoria"),
            "Descripcion":     "",
            "Lts_caja":        pd.to_numeric(c.get("Lts x caja"), errors="coerce").fillna(0),
            "UxC":             pd.to_numeric(c.get("UxC"), errors="coerce"),
        })
    df = pd.read_excel(xlsx_path, header=2).iloc[1:].copy()
    df.columns = ["Bodega", "Segmento", "Linea_Comercial", "Codigo", "Categoria", "Descripcion", "Lts_caja", "UxC"]
    df["Codigo"] = pd.to_numeric(df["Codigo"], errors="coerce")
    df["Lts_caja"] = pd.to_numeric(df["Lts_caja"], errors="coerce").fillna(0)
    return df


def cargar_maestro_productos():
    """Maestro 04D COMPLETADO con el maestro del mes: el 04D manda donde tiene el código, y el
    export del mes agrega los SKU vigentes que el 04D no trae (si no, sus ventas quedan sin
    categoría → fuera del sell out → y con 0 litros)."""
    df = _cargar_04D()
    df = df.dropna(subset=["Codigo"])

    mes = _maestro_mes_productos()
    if not mes.empty:
        faltan = mes[~mes["Codigo"].isin(set(df["Codigo"]))]
        if len(faltan):
            print(f"  Maestro 04D: {len(df)} codigos + {len(faltan)} completados desde el maestro del mes")
            df = pd.concat([df, faltan[df.columns]], ignore_index=True)
    return df


# ─────────────────────────────────────────────
# MOD COBERTURA ACUM
# ─────────────────────────────────────────────

def generar_cobertura_acum(ventas, clientes):
    sub_col = next((c for c in clientes.columns if "subseg" in c.lower() or "subramo" in c.lower()), None)
    cols = ["Codigo", "codven", "Vendedor", "_seg", "Razon_Social", "Localidad"]
    if sub_col:
        cols.append(sub_col)
    cart = clientes[cols].rename(
        columns={"Codigo": "cliente_id", "codven": "vendedor_codigo",
                 "Vendedor": "vendedor_nombre", "_seg": "segmento",
                 "Razon_Social": "cliente_nombre", "Localidad": "localidad",
                 **({sub_col: "subseg"} if sub_col else {})}
    ).copy()
    cart = cart[cart["segmento"] != "OTROS"]
    # V3 (Nadia) trabaja Tradicional y Proximity (no AS, On Premise ni Mayorista).
    # Alcanza con el segmento: hasta 2026-07-30 esto además exigía que el SubSegmento
    # dijera ALMACEN/DESPENSA/KIOSCO, y esa lista blanca se comía las carnicerías,
    # verdulerías y panaderías de su ruta — clientes tradicionales que V3 sí atiende.
    cart = cart[(cart["vendedor_codigo"] != 3) | (cart["segmento"].isin(_V3_SEGMENTOS))]
    if "subseg" in cart.columns:
        cart = cart.drop(columns=["subseg"])

    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v_agg = (v.groupby(["Cliente", "CodVendedor"])["CantBase"]
               .sum().reset_index()
               .rename(columns={"Cliente": "cliente_id", "CodVendedor": "vendedor_codigo",
                                "CantBase": "cant_base_acum"}))

    merged = cart.merge(v_agg, on=["cliente_id", "vendedor_codigo"], how="left")
    merged["cant_base_acum"] = merged["cant_base_acum"].fillna(0)
    merged["umbral"] = merged["segmento"].map(UMBRAL).fillna(3)
    merged["cubierto"] = (merged["cant_base_acum"] >= merged["umbral"]).astype(int)

    fecha = datetime.now().strftime("%Y-%m-%d")
    agg = merged.groupby(["vendedor_codigo", "vendedor_nombre", "segmento"]).agg(
        cartera=("cliente_id", "count"),
        cubiertos=("cubierto", "sum"),
    ).reset_index()
    agg["sin_cobertura"] = agg["cartera"] - agg["cubiertos"]
    agg["pct_cobertura"] = (agg["cubiertos"] / agg["cartera"].replace(0, np.nan)).round(4).fillna(0)
    agg["fecha_calculo"] = fecha
    agg = agg.sort_values(["vendedor_codigo", "segmento"])

    # Detalle de faltantes: clientes en cartera que NO alcanzaron el umbral en el acumulado.
    # Alimenta el drill-down de la tarjeta de cobertura (gerencia y vendedor).
    det = merged[merged["cubierto"] == 0].copy()
    det["fecha_calculo"] = fecha
    det["cliente_id"] = pd.to_numeric(det["cliente_id"], errors="coerce").astype("Int64")
    det["cliente_nombre"] = det["cliente_nombre"].fillna("").astype(str)
    det["localidad"] = det["localidad"].fillna("").astype(str)
    det["cant_base_acum"] = pd.to_numeric(det["cant_base_acum"], errors="coerce").fillna(0).round(1)
    det["umbral"] = pd.to_numeric(det["umbral"], errors="coerce").fillna(0).astype(int)
    det = det.sort_values(["vendedor_codigo", "segmento", "cliente_nombre"])
    det = det[["fecha_calculo", "vendedor_codigo", "vendedor_nombre", "segmento",
               "cliente_id", "cliente_nombre", "localidad", "cant_base_acum", "umbral"]]
    return agg, det


# ─────────────────────────────────────────────
# MOD 11T ACUM
# ─────────────────────────────────────────────

def generar_11t_acum(ventas, clientes, desde=None, hasta=None):
    """mod_11t_acum.csv — grilla cartera x titular con la cobertura del motor autoritativo.

    LA REGLA VIVE EN motor_11t.py, no acá. Esta función solo arma la grilla que consume el
    portal (`/api/gerencia/11t_acum`, KPI "11T ✓", "Marcas 11T") y le pega el resultado.

    Hasta 2026-08-05 resolvía el titular por TEXTO de `Marca` contra ALIAS_LOOKUP, y los
    valores reales del ERP no estaban en esa tabla: `SMIRNOFF`, `SMIRNOFF ICE FLAVOURS`,
    `CHAMPAÑA DADA`, `ANTARES ESPECIALES`, `GORDON'S FLAVORS` (grafía US). Resultado:
    Gordon's, Antares y Smirnoff Flavours quedaban en 0 y Smirnoff Ice al 13%. Ahora el
    match es por CÓDIGO DE ARTÍCULO contra la matriz oficial.

    Además consolida la venta del cliente sin importar qué vendedor la facturó (el cliente
    pertenece a la cartera del padrón), así una compra facturada por V20 Depósito ya no
    borra al cliente de la cobertura de la empresa.

    Devuelve (grilla, detalle, excepciones)."""
    det, exc = motor_11t.cobertura_11t(ventas, desde=desde, hasta=hasta)

    padron = motor_11t.cargar_padron_clientes()
    cart = padron[padron["segmento_11t"].isin(["AUTOSERVICIO", "TRADICIONAL"])].copy()
    cart = cart[~cart["vendedor_codigo"].isin(motor_11t.VENDEDORES_EXCLUIDOS_11T)]
    # V3 no trabaja autoservicio (regla de negocio): no se le mide cartera AS en el 11T.
    cart = cart[~((cart["vendedor_codigo"] == 3) & (cart["segmento_11t"] == "AUTOSERVICIO"))]

    titulares = motor_11t.titulares_oficiales()
    fecha = datetime.now().strftime("%Y-%m-%d")
    if cart.empty or not titulares:
        vacio = pd.DataFrame(columns=["fecha_calculo", "vendedor_codigo", "vendedor_nombre",
                                      "cliente_id", "segmento_11t", "marca_objetivo",
                                      "cant_base_acum", "tiene_flag", "falta_flag"])
        return vacio, det, exc

    # Grilla cartera x titular: mantiene el significado de `cartera` en el endpoint.
    grilla = cart[["cliente_id", "vendedor_codigo", "vendedor_nombre", "segmento_11t"]].merge(
        pd.DataFrame({"marca_objetivo": titulares}), how="cross")

    logrado = det[["cliente_id", "titular", "botellas_netas", "cumple"]].rename(
        columns={"titular": "marca_objetivo"})
    grilla = grilla.merge(logrado, on=["cliente_id", "marca_objetivo"], how="left")
    grilla["cant_base_acum"] = pd.to_numeric(grilla["botellas_netas"], errors="coerce").fillna(0)
    grilla["tiene_flag"] = (grilla["cumple"] == True).astype(int)   # noqa: E712 — NaN -> 0
    grilla["falta_flag"] = 1 - grilla["tiene_flag"]
    grilla["fecha_calculo"] = fecha
    grilla = grilla[["fecha_calculo", "vendedor_codigo", "vendedor_nombre", "cliente_id",
                     "segmento_11t", "marca_objetivo", "cant_base_acum",
                     "tiene_flag", "falta_flag"]]
    return grilla, det, exc


# ─────────────────────────────────────────────
# MOD PLANES AS
# ─────────────────────────────────────────────

def generar_planes_as(ventas, bbdd, clientes):
    # Vendedor por cliente AS: maestro clientes.xlsx (cartera real, autoritativo).
    # Fallback a ventas.csv (vendedor que más le vendió) solo si el cliente no está en el maestro.
    # Antes se deducía SOLO de ventas.csv → los clientes AS que aún no compraron en el mes
    # quedaban sin vendedor y no aparecían en la pestaña de su vendedor.
    vmaster = clientes[["Codigo", "codven", "Vendedor"]].copy()
    vmaster["cliente_id"] = pd.to_numeric(vmaster["Codigo"], errors="coerce")
    vmaster["vendedor_codigo"] = pd.to_numeric(vmaster["codven"], errors="coerce")
    vmaster = (vmaster.dropna(subset=["cliente_id", "vendedor_codigo"])
               .drop_duplicates(subset=["cliente_id"])
               .rename(columns={"Vendedor": "vendedor_nombre"})
               [["cliente_id", "vendedor_codigo", "vendedor_nombre"]])

    v_norm = ventas[ventas["ImporteNetoItem"] > 0].copy()
    vventas = (v_norm.groupby(["Cliente", "CodVendedor", "Vendedor"])
               .size().reset_index(name="n")
               .sort_values("n", ascending=False)
               .drop_duplicates(subset=["Cliente"])
               .rename(columns={"Cliente": "cliente_id", "CodVendedor": "vendedor_codigo",
                                "Vendedor": "vendedor_nombre"})[["cliente_id", "vendedor_codigo", "vendedor_nombre"]])

    faltan = vventas[~vventas["cliente_id"].isin(vmaster["cliente_id"])]
    vend_cli = pd.concat([vmaster, faltan], ignore_index=True)

    # Sin cargo: filas con 100% descuento
    sc = ventas[ventas["Descuento_pct"] >= 99.9].copy()

    # Resumen sin cargo enviado por cliente × marca
    sc_det = (sc.groupby(["Cliente", "Marca"])["CantBase"]
              .sum().reset_index()
              .rename(columns={"Cliente": "cliente_id", "Marca": "marca", "CantBase": "cajas"}))

    sc_pivot = sc_det.pivot_table(
        index="cliente_id", columns="marca", values="cajas", aggfunc="sum", fill_value=0
    ).reset_index()
    sc_pivot.columns.name = None
    sc_pivot = sc_pivot.rename(columns=lambda c: f"sc_env_{c.lower().replace(' ','_').replace('(','').replace(')','')}"
                               if c != "cliente_id" else c)

    sc_total_env = sc.groupby("Cliente")["CantBase"].sum().reset_index().rename(
        columns={"Cliente": "cliente_id", "CantBase": "sc_cajas_enviadas_total"}
    )

    # SC enviados por producto Plan AS (solo productos del plan)
    # REGLA: detectar marca desde columna Articulo (fuente primaria, más confiable).
    # Marca del ERP tiene errores conocidos:
    #   - COD 74510 "F. LAS MORAS ROSADO" tiene Marca="Alaris" → falso positivo si usamos Marca
    #   - COD 14619/14620 "FRIZZE..." tiene Marca=NaN → falso negativo si usamos solo Marca
    #   - COD 35103/35104/35105 "SMF ICE..." tiene Marca="Smirnoff Ice Flavours" → correcto,
    #     pero Articulo usa abreviatura "SMF" no "SMIRNOFF", por eso se incluye "smf ice".
    _AS_MARCAS = {
        "alaris": "sc_env_alaris",
        "alma mora": "sc_env_alma_mora",
        "frizze": "sc_env_frizze",
        "antares": "sc_env_antares_ipa",
        "smirnoff": "sc_env_smf_flavours",
    }
    _ARTICULO_AS = {
        "sc_env_alaris":       ["alaris"],
        "sc_env_alma_mora":    ["alma mora"],
        "sc_env_frizze":       ["frizze"],
        "sc_env_antares_ipa":  ["antares"],
        "sc_env_smf_flavours": ["smirnoff", "smf ice"],
    }

    def _detectar_prod_as(row):
        # Fuente: SOLO Articulo. Sin fallback a Marca.
        # Marca tiene errores conocidos en el ERP (ej: COD 74510 "F. LAS MORAS ROSADO"
        # con Marca="Alaris" → falso positivo). Si el Articulo no dice explícitamente
        # el nombre de la marca del plan, no se cuenta como sin cargo del plan.
        art = str(row.get("Articulo", "")).lower()
        for prod_col, kws in _ARTICULO_AS.items():
            if any(kw in art for kw in kws):
                return prod_col
        return None

    sc_copy = sc.copy()
    sc_copy["_prod_as"] = sc_copy.apply(_detectar_prod_as, axis=1)
    sc_plan = sc_copy[sc_copy["_prod_as"].notna()]
    sc_env_prod = {}
    for prod_col in _AS_MARCAS.values():
        sub = sc_plan[sc_plan["_prod_as"] == prod_col]
        grp = sub.groupby("Cliente")["CantBase"].sum().reset_index().rename(
            columns={"Cliente": "cliente_id", "CantBase": prod_col}
        )
        sc_env_prod[prod_col] = grp

    # Join
    df = bbdd.merge(vend_cli, on="cliente_id", how="left")
    df = df.merge(sc_total_env, on="cliente_id", how="left")
    df["sc_cajas_enviadas_total"] = df["sc_cajas_enviadas_total"].fillna(0)

    for prod_col, grp in sc_env_prod.items():
        df = df.merge(grp, on="cliente_id", how="left")
        df[prod_col] = df[prod_col].fillna(0)

    # OVERRIDE del DISPONIBLE de sin cargos desde sincargos*.xlsx (fuente mensual curada).
    # La pantalla de Planes AS (cliente / plan / facturado / escala_actual) NO cambia.
    # Sólo el bloque de sin cargo (disponible/enviado/pendiente) y el Estado pasan a regirse
    # por este Excel. Clientes no listados este mes → sin cargos disponibles = 0.
    # Si el Excel falta o falla, se conserva el disponible calculado por facturación (fail-safe).
    _SC_COLS = ["sc_alaris", "sc_alma_mora", "sc_frizze", "sc_antares_ipa", "sc_smf_flavours"]
    sc_mes = _cargar_sincargos_mes()
    if sc_mes:
        for col in _SC_COLS + ["sc_total_ganado"]:
            if col in df.columns:
                df[col] = 0
        for cid, alloc in sc_mes.items():
            mask = df["cliente_id"] == cid
            if mask.any():
                for col in _SC_COLS:
                    df.loc[mask, col] = alloc.get(col, 0)
                df.loc[mask, "sc_total_ganado"] = alloc.get("sc_total_ganado", 0)
        df["sc_origen_disponible"] = "sincargos_mes"
    else:
        df["sc_origen_disponible"] = "facturacion"

    # sc_pendiente por producto Plan AS
    df["sc_pend_alaris"] = (df["sc_alaris"] - df.get("sc_env_alaris", 0)).clip(lower=0)
    df["sc_pend_alma_mora"] = (df["sc_alma_mora"] - df.get("sc_env_alma_mora", 0)).clip(lower=0)
    df["sc_pend_frizze"] = (df["sc_frizze"] - df.get("sc_env_frizze", 0)).clip(lower=0)
    df["sc_pend_antares_ipa"] = (df["sc_antares_ipa"] - df.get("sc_env_antares_ipa", 0)).clip(lower=0)
    df["sc_pend_smf_flavours"] = (df["sc_smf_flavours"] - df.get("sc_env_smf_flavours", 0)).clip(lower=0)
    df["sc_pendiente"] = (df["sc_pend_alaris"] + df["sc_pend_alma_mora"] + df["sc_pend_frizze"]
                          + df["sc_pend_antares_ipa"] + df["sc_pend_smf_flavours"])

    # Estado del cliente: 'enviados' (todo entregado), 'pendiente' (falta algo),
    # '' (sin sin cargos asignados este mes → la tarjeta no pinta chip de estado).
    df["sc_estado"] = df.apply(
        lambda r: "enviados" if (r["sc_total_ganado"] > 0 and r["sc_pendiente"] == 0)
        else ("pendiente" if r["sc_pendiente"] > 0 else ""), axis=1)

    # ── PLAN FRÍO: 1 Six Pack Smirnoff ICE sin cargo por cliente listado en la hoja 'plan frío'.
    # Disponible = lista del Excel. Entregado (binario) = el cliente tiene alguna línea 100%
    # descuento de Smirnoff ICE EN LATA en ventas.csv. Se detecta por ARTICULO, no por Marca:
    # las latas Smirnoff BC (Bitter Citric, COD 35108/35109) tienen Marca='Smirnoff Ice Flavours'
    # en el ERP pero NO son plan frío — pertenecen a una acción comercial del mes. Su Articulo
    # dice 'BC' y NO 'ICE', así que filtrar por Articulo con 'ICE' + (SMIRNOFF/SMF) las excluye.
    # Tampoco se confunde con la escala 'Smirnoff Flavours' (botella) ni con Smirnoff vodka.
    pf_clientes = _cargar_planfrio_mes()
    _art_sc = sc["Articulo"].astype(str).str.upper()
    _es_ice = (_art_sc.str.contains("ICE", regex=False, na=False)
               & (_art_sc.str.contains("SMIRNOFF", regex=False, na=False)
                  | _art_sc.str.contains("SMF", regex=False, na=False)))
    pf_env_ids = set(pd.to_numeric(
        sc.loc[_es_ice, "Cliente"], errors="coerce").dropna().astype(int))
    df["pf_disponible"] = df["cliente_id"].isin(pf_clientes).astype(int)
    df["pf_enviado"] = (df["pf_disponible"].eq(1) & df["cliente_id"].isin(pf_env_ids)).astype(int)
    df["pf_estado"] = df.apply(
        lambda r: ("entregado" if r["pf_enviado"] else "pendiente") if r["pf_disponible"] else "",
        axis=1)

    # ── PUNTERA: cajas de un vino (cualquier varietal) sin cargo por cliente listado en la hoja
    # 'Puntera'. El PRODUCTO sale del encabezado del Excel (ver _cargar_puntera_mes), no del código.
    # Disponible = cajas del Excel. Enviado = cajas 100% descuento de ese producto en ventas.csv
    # (detección por Articulo que contiene el nombre del producto en mayúsculas, ej. 'LOS ARBOLES').
    pt_clientes, pt_producto = _cargar_puntera_mes()
    _pt_key = (pt_producto or "").upper().strip()
    _es_caz = (sc["Articulo"].astype(str).str.upper().str.contains(_pt_key, regex=False, na=False)
               if _pt_key else pd.Series(False, index=sc.index))
    pt_env = (sc[_es_caz].groupby("Cliente")["CantBase"].sum()
              if _es_caz.any() else pd.Series(dtype=float))
    df["pt_disponible"] = df["cliente_id"].map(pt_clientes).fillna(0).astype(int)
    df["pt_enviado"] = df["cliente_id"].map(pt_env).fillna(0)
    # sólo cuenta el enviado de clientes CON puntera disponible (igual que plan frío)
    df["pt_enviado"] = (df["pt_enviado"] * df["pt_disponible"].gt(0)).clip(lower=0).astype(int)
    df["pt_pendiente"] = (df["pt_disponible"] - df["pt_enviado"]).clip(lower=0).astype(int)
    df["pt_estado"] = df.apply(
        lambda r: ("entregado" if r["pt_pendiente"] == 0 else "pendiente") if r["pt_disponible"] > 0 else "",
        axis=1)
    # Nombre del producto de puntera (del Excel) → columna para que el portal lo muestre sin cablearlo.
    df["pt_producto"] = pt_producto

    # ── DETALLE de envíos de sin cargo (fecha de cada entrega) → mod_sincargos_envios.csv.
    # Alimenta la tarjeta desplegable al clickear un sin cargo en el portal. Fecha =
    # FechaComprobante (regla de facturación). Una fila por cliente × producto × fecha.
    _PROD_LABEL = {"sc_env_alaris": "Alaris", "sc_env_alma_mora": "Alma Mora",
                   "sc_env_frizze": "Frizze", "sc_env_antares_ipa": "Antares IPA",
                   "sc_env_smf_flavours": "Smirnoff Flavours"}
    det_rows = []
    if not sc_plan.empty:
        _f = pd.to_datetime(sc_plan["FechaComprobante"], dayfirst=True, errors="coerce")
        tmp = sc_plan.assign(_fecha=_f.dt.strftime("%Y-%m-%d")).dropna(subset=["_fecha"])
        for _, r in tmp.groupby(["Cliente", "_prod_as", "_fecha"])["CantBase"].sum().reset_index().iterrows():
            det_rows.append({"cliente_id": int(r["Cliente"]), "categoria": "escala",
                             "producto": _PROD_LABEL.get(r["_prod_as"], r["_prod_as"]),
                             "fecha": r["_fecha"], "cajas": int(r["CantBase"])})
    pf_lines = sc[_es_ice].copy()
    if not pf_lines.empty:
        _f2 = pd.to_datetime(pf_lines["FechaComprobante"], dayfirst=True, errors="coerce")
        pf_lines = pf_lines.assign(_fecha=_f2.dt.strftime("%Y-%m-%d")).dropna(subset=["_fecha"])
        for _, r in pf_lines.groupby(["Cliente", "_fecha"])["CantBase"].sum().reset_index().iterrows():
            if int(r["Cliente"]) in pf_clientes:
                det_rows.append({"cliente_id": int(r["Cliente"]), "categoria": "plan_frio",
                                 "producto": "Six Pack Smirnoff ICE",
                                 "fecha": r["_fecha"], "cajas": int(r["CantBase"])})
    pt_lines = sc[_es_caz].copy()
    if not pt_lines.empty:
        _f3 = pd.to_datetime(pt_lines["FechaComprobante"], dayfirst=True, errors="coerce")
        pt_lines = pt_lines.assign(_fecha=_f3.dt.strftime("%Y-%m-%d")).dropna(subset=["_fecha"])
        for _, r in pt_lines.groupby(["Cliente", "_fecha"])["CantBase"].sum().reset_index().iterrows():
            if int(r["Cliente"]) in pt_clientes:
                det_rows.append({"cliente_id": int(r["Cliente"]), "categoria": "puntera",
                                 "producto": pt_producto,
                                 "fecha": r["_fecha"], "cajas": int(r["CantBase"])})
    pd.DataFrame(det_rows, columns=["cliente_id", "categoria", "producto", "fecha", "cajas"]) \
        .to_csv(OUT / "mod_sincargos_envios.csv", index=False, encoding="utf-8-sig")

    # Nombre y dirección desde el maestro clientes.xlsx (el nombre de la BBDD tiene mojibake).
    # Fallback al nombre de la BBDD si el cliente no está en el maestro.
    cli_idx = clientes.copy()
    cli_idx["cliente_id"] = pd.to_numeric(cli_idx["Codigo"], errors="coerce")
    nombre_master = dict(zip(cli_idx["cliente_id"], cli_idx.get("Razon_Social")))
    direccion_master = dict(zip(cli_idx["cliente_id"], cli_idx.get("Direccion")))
    df["cliente_nombre"] = df["cliente_id"].map(nombre_master).fillna(df["cliente_nombre"])
    df["direccion"] = df["cliente_id"].map(direccion_master).fillna("")

    # REGLA 3.10 — la "venta" del Plan AS sale de ventas.csv (venta neta válida del cliente,
    # ImporteNetoItem > 0), NO de la columna del Excel de Reconocimiento. La escala alcanzada
    # se recalcula con esa venta real contra escala_*.xlsx.
    fact_ventas = (ventas[ventas["ImporteNetoItem"] > 0]
                   .groupby("Cliente")["ImporteNetoItem"].sum())
    df["total_facturado"] = pd.to_numeric(
        df["cliente_id"].map(fact_ventas), errors="coerce").fillna(0.0)
    esc_df = _cargar_escala_df()
    df["escala_actual"] = df.apply(
        lambda r: _calc_escala_actual(r["plan_as"], r["total_facturado"], esc_df), axis=1)

    df["fecha_calculo"] = datetime.now().strftime("%Y-%m-%d")

    cols_out = [
        "fecha_calculo", "cliente_id", "cliente_nombre", "direccion", "vendedor_codigo", "vendedor_nombre",
        "plan_as", "escala_actual", "escala_max", "total_facturado", "dcto_plan",
        "cant_cajas", "tope", "cant_cajas_tope",
        "sc_alaris", "sc_alma_mora", "sc_frizze", "sc_antares_ipa", "sc_smf_flavours",
        "sc_total_ganado",
        "sc_env_alaris", "sc_env_alma_mora", "sc_env_frizze", "sc_env_antares_ipa", "sc_env_smf_flavours",
        "sc_pend_alaris", "sc_pend_alma_mora", "sc_pend_frizze", "sc_pend_antares_ipa", "sc_pend_smf_flavours",
        "sc_cajas_enviadas_total", "sc_pendiente", "sc_estado", "sc_origen_disponible",
        "pf_disponible", "pf_enviado", "pf_estado",
        "pt_disponible", "pt_enviado", "pt_pendiente", "pt_estado", "pt_producto",
    ]
    return df[[c for c in cols_out if c in df.columns]]


# ─────────────────────────────────────────────
# MOD INNOVACIONES SEGMENTO
# ─────────────────────────────────────────────

def generar_innovaciones_segmento(ventas, clientes):
    """
    CCC de los productos innovación (lista de Innovaciones.xlsx) por vendedor × SUBCANAL.
    Subcanales (6): AUTOSERVICIO, ALMACEN, KIOSCO, ON_PREMISE, MAYORISTA, PROXIMITY.
    Fuente: ventas.csv (MES VIVO). No se filtra por Empresa (ver comentario abajo).
    V3 solo Tradicional (ALMACEN + KIOSCO) y Proximity: sin AS, Mayorista ni On Premise.
    El CSV mantiene la columna 'segmento' (ahora con el subcanal) por compat con el portal.

    LA COMPRA CUENTA PARA EL VENDEDOR QUE LA FACTURÓ, no para el dueño de la cartera
    (definición del negocio, 2026-07-30). Antes se cruzaba "clientes que le compraron a
    ese vendedor" ∩ "cartera de ese vendedor", así que una venta hecha por V8 sobre un
    cliente de la cartera de V3 no le sumaba a nadie y se perdía del total de gerencia.
    El cliente se ubica en el subcanal que dice el maestro, esté o no en la cartera del
    vendedor que le vendió. Dos consecuencias buscadas:
      - 'clientes_compraron' puede incluir clientes fuera de la cartera del vendedor
        (mide lo que vendió, no a quién tiene asignado).
      - 'clientes_faltantes' (plan de acción) descuenta a los que ya compraron el producto
        A CUALQUIER VENDEDOR: no se manda a visitar a un cliente que ya lo tiene.
    """
    SUBCANALES = ["AUTOSERVICIO", "ALMACEN", "KIOSCO", "ON_PREMISE", "MAYORISTA", "PROXIMITY"]

    # Cartera por vendedor × subcanal
    cart = clientes[["Codigo", "codven", "Vendedor", "_subcanal"]].rename(
        columns={"Codigo": "cliente_id", "codven": "vendedor_codigo",
                 "Vendedor": "vendedor_nombre", "_subcanal": "segmento"}
    ).copy()
    cart = cart[cart["segmento"].isin(SUBCANALES)]
    cart = cart[cart["vendedor_codigo"].isin(VENDEDORES_ACTIVOS_INOV)]
    # V3 solo Tradicional (Almacén + Kiosco)
    cart = cart[~((cart["vendedor_codigo"] == 3) & (~cart["segmento"].isin(_V3_SUBCANALES)))]

    # Ventas de productos innovación. No se filtra por Empresa: P&P Logística es nuestra
    # segunda razón social, no otro distribuidor (Proveedor = GRUPO PEÑAFLOR SA en el 100%
    # de las filas). Medimos siempre con las dos empresas.
    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v["_cod"] = pd.to_numeric(v["Codigo"], errors="coerce")
    v_inov = v[v["_cod"].isin(INOV_PRODUCTOS.keys()) &
               v["CodVendedor"].isin(VENDEDORES_ACTIVOS_INOV)].copy()
    v_inov = v_inov.dropna(subset=["_cod", "Cliente", "CodVendedor"])
    # Un par (producto, cliente) le cuenta a UN solo vendedor. Si dos vendedores le
    # facturaron el mismo producto al mismo cliente, se lo queda el de mayor volumen:
    # de lo contrario el total de gerencia (suma por vendedor) contaría dos veces al cliente.
    v_inov = (v_inov.groupby(["_cod", "Cliente", "CodVendedor"], as_index=False)["CantBase"].sum()
                    .sort_values("CantBase", ascending=False)
                    .drop_duplicates(subset=["_cod", "Cliente"]))

    # Subcanal del cliente según el maestro: ubica la compra en su segmento aunque el
    # cliente no esté en la cartera del vendedor que la facturó.
    cli_seg = clientes[["Codigo", "_subcanal"]].dropna(subset=["Codigo"]).drop_duplicates(subset=["Codigo"])
    SEG_DE_CLIENTE = {int(c): s for c, s in zip(cli_seg["Codigo"], cli_seg["_subcanal"])}

    compras_vend = {}      # (producto, vendedor) → set de clientes a los que ESE vendedor le vendió
    compradores = {}       # producto → set de clientes que lo compraron, a cualquier vendedor
    for cod_p, cli, vend in zip(v_inov["_cod"], v_inov["Cliente"], v_inov["CodVendedor"]):
        cod_p, cli, vend = int(cod_p), int(cli), int(vend)
        compras_vend.setdefault((cod_p, vend), set()).add(cli)
        compradores.setdefault(cod_p, set()).add(cli)

    fecha = datetime.now().strftime("%Y-%m-%d")
    filas = []
    for vend_cod, grp_vend in cart.groupby("vendedor_codigo"):
        vend_cod = int(vend_cod)
        vend_nombre = grp_vend["vendedor_nombre"].iloc[0]
        for seg in SUBCANALES:
            # V3 no trabaja AS / On Premise / Mayorista: esas filas no existen para ella.
            if vend_cod == 3 and seg not in _V3_SUBCANALES:
                continue
            grp_seg = grp_vend[grp_vend["segmento"] == seg]
            cartera_ids = set(grp_seg["cliente_id"].dropna().astype(int))
            # Clientes de este subcanal a los que el vendedor le facturó alguna innovación,
            # tenga o no cartera propia acá (si no, la venta se volvería a perder).
            vendio_en_seg = {c for (p, vv), cs in compras_vend.items() if vv == vend_cod
                             for c in cs if SEG_DE_CLIENTE.get(c) == seg}
            if not cartera_ids and not vendio_en_seg:
                continue
            for cod, nombre in INOV_PRODUCTOS.items():
                compraron_ids = {c for c in compras_vend.get((cod, vend_cod), set())
                                 if SEG_DE_CLIENTE.get(c) == seg}
                faltantes = sorted(cartera_ids - compradores.get(cod, set()))
                filas.append({
                    "fecha_ejecucion": fecha,
                    "vendedor_codigo": int(vend_cod),
                    "vendedor_nombre": vend_nombre,
                    "segmento": seg,
                    "producto_codigo": cod,
                    "producto_nombre": nombre,
                    "clientes_cartera": len(cartera_ids),
                    "clientes_compraron": len(compraron_ids),
                    "clientes_no_compraron": len(faltantes),
                    "pct_cobertura": round(len(compraron_ids) / len(cartera_ids), 4) if cartera_ids else 0.0,
                    "clientes_faltantes": "|".join(str(x) for x in faltantes),
                })
    df = pd.DataFrame(filas)
    if not df.empty:
        df = df.sort_values(["vendedor_codigo", "segmento", "producto_codigo"]).reset_index(drop=True)
    return df


def generar_innovaciones_plan_as(ventas, bbdd):
    """
    Por cliente AS: cuántas y cuáles innovaciones compró en el periodo acumulado.
    """
    PENDIENTE_STOCK = "Antares P770|Antares P330"

    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    # No se filtra por Empresa: medimos con las dos razones sociales (ver generar_11t_acum).
    v["_cod"] = pd.to_numeric(v["Codigo"], errors="coerce")
    v_inov = v[v["_cod"].isin(INOV_PRODUCTOS.keys())].copy()

    total_activas = len(INOV_PRODUCTOS)
    fecha = datetime.now().strftime("%Y-%m-%d")
    filas = []
    for _, row in bbdd.iterrows():
        cid = int(row["cliente_id"])
        compras = set(v_inov[v_inov["Cliente"] == cid]["_cod"].dropna().astype(int))
        compradas = compras & set(INOV_PRODUCTOS.keys())
        faltantes = [INOV_PRODUCTOS[c] for c in INOV_PRODUCTOS if c not in compradas]
        filas.append({
            "fecha_ejecucion": fecha,
            "cliente_id": cid,
            "cliente_nombre": str(row.get("cliente_nombre", "")),
            "vendedor_codigo": row.get("vendedor_codigo", ""),
            "plan_as": str(row.get("plan_as", "")),
            "innovaciones_activas": total_activas,
            "innovaciones_compradas": len(compradas),
            "pct_avance": round(len(compradas) / total_activas, 4),
            "productos_faltantes": "|".join(faltantes),
            "productos_pendiente_stock": PENDIENTE_STOCK,
        })
    return pd.DataFrame(filas)


# ─────────────────────────────────────────────
# MOD SELLOUT CATEGORIA
# ─────────────────────────────────────────────

def generar_sellout_categoria(ventas, maestro):
    """Ventas acumuladas en litros × categoría de bebida (col E maestro) × segmento (col B maestro)."""
    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v["_cod"] = pd.to_numeric(v["Codigo"], errors="coerce")
    merged = v.merge(
        maestro[["Codigo", "Segmento", "Categoria", "Lts_caja"]],
        left_on="_cod", right_on="Codigo", how="left"
    )
    merged["_litros"] = merged["CantBase"] * merged["Lts_caja"].fillna(0)
    merged = merged[merged["Categoria"].notna()]
    agg = merged.groupby(["Categoria", "Segmento"]).agg(
        litros=("_litros", "sum"),
        cajas=("CantBase", "sum"),
        importe=("ImporteNetoItem", "sum"),
        clientes=("Cliente", "nunique"),
    ).reset_index()
    agg["litros"] = agg["litros"].round(1)
    agg["importe"] = agg["importe"].round(0).astype("int64")
    agg["fecha_calculo"] = datetime.now().strftime("%Y-%m-%d")
    return agg.sort_values(["Categoria", "litros"], ascending=[True, False]).reset_index(drop=True)


# ─────────────────────────────────────────────
# MOD ACCIONES RANKING
# ─────────────────────────────────────────────

# Mapeo: categoria de regla → Categoria del maestro de productos
# NOTA: los valores deben coincidir EXACTAMENTE (case-sensitive) con la columna Categoria
#       del maestro 04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx
_REGLA_CAT_MAP = {
    "VDA/VDG/ESPUMANTES/SIDRA": ["Vinos del año", "Vinos de guarda", "Espumantes", "SIDRA"],
    "VDA":                       ["Vinos del año", "Vinos de guarda"],
    "RTD":                       ["RTD", "RTD (S)", "Primary (S)", "Standard (S)", "Premium (S)", "Super Premium (S)"],
    "RTD LATAS":                 ["RTD", "RTD (S)", "Primary (S)", "Standard (S)", "Premium (S)", "Super Premium (S)"],
    "RTD ICE":                   ["RTD", "RTD (S)"],                  # Smirnoff ICE (refina con _ARTICULO_CAT_MAP)
    "SPIRITS LOCALES":           ["Gin", "Vodka", "Ron", "Licores"],
    "SPIRITS IMPORTADOS":        ["Whisky", "Whisky (Maltas)", "Bourbon"],
    "SPIRITS":                   ["Gin", "Vodka", "Ron", "Licores", "Whisky", "Whisky (Maltas)", "Bourbon"],
    "ESPUMANTES":                ["Espumantes"],
    "TERMIDOR":                  ["Vinos de Mesa"],                   # refina con _ARTICULO_CAT_MAP
}

# Filtro adicional por keyword en Articulo para categorías que necesitan precisión de producto.
# Cuando cat_key aparece aquí, se aplica ADEMÁS del filtro de Categoria del maestro.
# Razón: RTD/RTD LATAS/RTD ICE comparten la misma Categoria ("RTD (S)") en el maestro;
# sin este filtro las tres acciones producirían filas idénticas.
# Termidor: está en "Vinos de Mesa" pero la acción es específica de esa marca.
_ARTICULO_CAT_MAP = {
    "RTD":       ["frizze"],                           # solo Frizze (botellas)
    "RTD LATAS": ["gordons", "smf bc", "antares"],     # Gordons Tonic / Smirnoff BC / Antares (NO SMF ICE)
    "RTD ICE":   ["smirnoff ice", "smf ice"],          # Smirnoff ICE exclusivamente (Imagen 7: 25% dto)
    "TERMIDOR":  ["termidor"],                         # Termidor Blanco / Tinto (Imagen 8)
}

# Mapeo: canal de regla → segmentos de clientes (_seg)  None = sin filtro
_REGLA_CANAL_SEG_MAP = {
    "AUTOSERVICIOS":           ["AUTOSERVICIO"],
    "TRAD+KIOSCO+ON PREMISE":  ["TRADICIONAL", "ON_PREMISE"],
    "VTK/TDB":                 ["ON_PREMISE"],
    "TODOS":                   None,
    "ON PREMISE NOCHE; BARES": ["ON_PREMISE"],
    "PETIT MAYORISTAS":        ["MAYORISTA"],
}

def _preparar_ventas_acciones(ventas, clientes, maestro):
    """Prepara el dataframe de ventas para el análisis de acciones (reutilizable)."""
    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v["_cod"] = pd.to_numeric(v["Codigo"], errors="coerce")
    v["_cli"] = pd.to_numeric(v["Cliente"], errors="coerce")
    # Filtro de acción comercial: solo ventas con descuento explícito en el ERP.
    # Descuento_pct ya está limpio desde _parsear_ventas_csv.
    # NO usar ImporteItem - ImporteNetoItem: incluye diferencias de precio de lista que no son acciones.
    v = v[v["Descuento_pct"] > 0].copy()
    # Inversión = ImporteItem (bruto) - ImporteNetoItem. ImporteItem puede tener coma decimal.
    _imp_raw = v["ImporteItem"].astype(str) if "ImporteItem" in v.columns else pd.Series(["0"] * len(v), index=v.index)
    _imp_raw = _imp_raw.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    v["_imp_item"] = pd.to_numeric(_imp_raw, errors="coerce").fillna(0)
    v["_descuento_p"] = (v["_imp_item"] - v["ImporteNetoItem"]).clip(lower=0)
    v = v.merge(maestro[["Codigo", "Categoria", "Lts_caja"]], left_on="_cod", right_on="Codigo", how="left")
    v["_litros"] = v["CantBase"] * v["Lts_caja"].fillna(0)
    cli_seg = clientes[["Codigo", "_seg"]].copy()
    cli_seg["Codigo"] = pd.to_numeric(cli_seg["Codigo"], errors="coerce")
    v = v.merge(cli_seg.rename(columns={"Codigo": "cli_id"}), left_on="_cli", right_on="cli_id", how="left")
    return v


def _filtrar_ventas_accion(v, canal, cat_key, segs):
    """Aplica filtros de canal + categoría + Articulo sobre el df preparado."""
    mask = pd.Series(True, index=v.index)
    if segs is not None:
        mask &= v["_seg"].isin(segs)
    if cat_key == "INNOVACIONES":
        mask &= v["_cod"].isin(set(INOV_PRODUCTOS.keys()))
    else:
        maestro_cats = _REGLA_CAT_MAP.get(cat_key)
        if maestro_cats is None:
            return None
        mask &= v["Categoria"].isin(maestro_cats)
        if cat_key in _ARTICULO_CAT_MAP:
            kws = _ARTICULO_CAT_MAP[cat_key]
            art_l = v["Articulo"].astype(str).str.lower()
            mask &= art_l.apply(lambda a, kws=kws: any(kw in a for kw in kws))
    return v[mask]


def generar_acciones_ranking(ventas, clientes, maestro):
    """
    Detalle de acciones comerciales del mes, una fila por acción (accion_grupo).
    Incluye accion_nombre legible y conjunto de clientes para análisis posterior.
    Retorna: (DataFrame detalle, dict {accion_grupo: set(cli_ids)})
    """
    p = BASE / "09_CONFIG" / "reglas_acciones_mayo_2026_orbit.csv"
    if not p.exists():
        return pd.DataFrame(), {}
    reglas = pd.read_csv(p, encoding="utf-8-sig")
    reglas.columns = [c.strip() for c in reglas.columns]

    v = _preparar_ventas_acciones(ventas, clientes, maestro)

    seen: set = set()
    filas = []
    clientes_por_accion: dict = {}   # accion_grupo → set de cliente_ids

    for _, r in reglas.iterrows():
        canal    = str(r.get("canal", "")).strip()
        cat_key  = str(r.get("categoria", "")).strip().upper()
        grupo    = str(r.get("accion_grupo", f"{canal}|{cat_key}")).strip()
        nombre   = str(r.get("accion_nombre", grupo)).strip()
        tipo     = str(r.get("tipo_accion", "")).strip()

        if grupo in seen:
            continue
        seen.add(grupo)

        # Excluir PLANES AASS (cubierto por mod_planes_as) y RESTO SKU
        if canal == "PLANES AASS" or cat_key == "RESTO SKU":
            continue
        if canal not in _REGLA_CANAL_SEG_MAP:
            continue

        segs  = _REGLA_CANAL_SEG_MAP[canal]
        v_m   = _filtrar_ventas_accion(v, canal, cat_key, segs)
        if v_m is None or v_m.empty:
            continue

        clientes_por_accion[grupo] = set(v_m["_cli"].dropna().astype(int).tolist())

        # Rango de descuentos aplicados en esta acción
        desc_vals = sorted(v_m["Descuento_pct"].dropna().unique())
        if desc_vals:
            desc_min = round(min(desc_vals), 0)
            desc_max = round(max(desc_vals), 0)
            desc_display = (f"{int(desc_min)}%" if desc_min == desc_max
                            else f"{int(desc_min)}-{int(desc_max)}%")
        else:
            desc_display = "–"

        filas.append({
            "accion_grupo":       grupo,
            "accion_nombre":      nombre,
            "tipo_accion":        tipo,
            "canal":              canal,
            "categoria":          cat_key,
            "descuento_display":  desc_display,
            "litros_vendidos":    round(float(v_m["_litros"].sum()), 1),
            "cajas_vendidas":     int(v_m["CantBase"].sum()),
            "inversion_pesos":    round(float(v_m["_descuento_p"].sum()), 0),
            "importe_neto":       round(float(v_m["ImporteNetoItem"].sum()), 0),
            "clientes_afectados": int(v_m["_cli"].nunique()),
            "fecha_calculo":      datetime.now().strftime("%Y-%m-%d"),
        })

    df = pd.DataFrame(filas)
    if not df.empty:
        df = df.sort_values("inversion_pesos", ascending=False).reset_index(drop=True)
    return df, clientes_por_accion


def generar_acciones_analisis(ventas, historial_path, clientes, maestro, clientes_por_accion: dict):
    """
    Análisis de retorno por acción comercial vs mes anterior.
    Para cada acción calcula:
    - clientes_mes_actual: compraron con descuento en categoría este mes
    - clientes_cat_mes_ant: compraron la misma categoría el mes anterior (cualquier precio)
    - clientes_nuevos_cat: en actual pero NO en mes anterior → activados por la acción
    - litros_mes_actual, litros_mes_anterior: comparativo de volumen
    - costo_por_cliente_nuevo: inversión / clientes_nuevos_cat
    """
    if not clientes_por_accion:
        return pd.DataFrame()

    p_reglas = BASE / "09_CONFIG" / "reglas_acciones_mayo_2026_orbit.csv"
    if not p_reglas.exists():
        return pd.DataFrame()
    reglas = pd.read_csv(p_reglas, encoding="utf-8-sig")
    reglas.columns = [c.strip() for c in reglas.columns]
    reglas_map = {}
    for _, r in reglas.iterrows():
        g = str(r.get("accion_grupo", "")).strip()
        if g and g not in reglas_map:
            reglas_map[g] = r

    # Cargar historial (ventas reales históricas)
    if not historial_path.exists():
        return pd.DataFrame()
    hist = pd.read_csv(historial_path, encoding="latin1", sep=";", engine="python",
                       on_bad_lines="skip")
    hist.columns = [c.strip() for c in hist.columns]
    hist["FechaComprobante"] = pd.to_datetime(hist["FechaComprobante"], dayfirst=True, errors="coerce")
    hist["ImporteNetoItem"] = (hist["ImporteNetoItem"].astype(str)
                               .str.replace(".", "", regex=False)
                               .str.replace(",", ".", regex=False))
    hist["ImporteNetoItem"] = pd.to_numeric(hist["ImporteNetoItem"], errors="coerce").fillna(0)
    hist["CantBase"] = pd.to_numeric(hist["CantBase"], errors="coerce").fillna(0)
    hist["_cod"] = pd.to_numeric(hist["Codigo"], errors="coerce")
    hist["_cli"] = pd.to_numeric(hist["Cliente"], errors="coerce")
    hist = hist[hist["ImporteNetoItem"] > 0]
    hist = hist.merge(maestro[["Codigo", "Categoria", "Lts_caja"]], left_on="_cod", right_on="Codigo", how="left")
    hist["_litros"] = hist["CantBase"] * hist["Lts_caja"].fillna(0)

    # Determinar mes actual y mes anterior desde ventas
    ventas["FechaComprobante"] = pd.to_datetime(ventas["FechaComprobante"], dayfirst=True, errors="coerce")
    mes_actual  = ventas["FechaComprobante"].dt.to_period("M").dropna().max()
    mes_anterior = mes_actual - 1

    hist_ant = hist[hist["FechaComprobante"].dt.to_period("M") == mes_anterior].copy()
    hist_act = hist[hist["FechaComprobante"].dt.to_period("M") == mes_actual].copy()

    v_act = _preparar_ventas_acciones(ventas, clientes, maestro)

    filas = []
    for grupo, clis_accion in clientes_por_accion.items():
        r_reg = reglas_map.get(grupo)
        if r_reg is None:
            continue
        canal   = str(r_reg.get("canal", "")).strip()
        cat_key = str(r_reg.get("categoria", "")).strip().upper()
        nombre  = str(r_reg.get("accion_nombre", grupo)).strip()

        if canal not in _REGLA_CANAL_SEG_MAP:
            continue
        segs = _REGLA_CANAL_SEG_MAP[canal]

        # Litros MES ANTERIOR — mismo canal+categoría, sin filtro de descuento
        if cat_key == "INNOVACIONES":
            cat_mask_ant = hist_ant["_cod"].isin(set(INOV_PRODUCTOS.keys()))
        else:
            maestro_cats = _REGLA_CAT_MAP.get(cat_key)
            if maestro_cats is None:
                continue
            cat_mask_ant = hist_ant["Categoria"].isin(maestro_cats)
            if cat_key in _ARTICULO_CAT_MAP:
                kws = _ARTICULO_CAT_MAP[cat_key]
                art_l_ant = hist_ant["Articulo"].astype(str).str.lower()
                cat_mask_ant &= art_l_ant.apply(lambda a, kws=kws: any(kw in a for kw in kws))

        # Filtro de segmento (canal) sobre historial anterior
        if segs is not None and "Ramo" in hist_ant.columns and "Subramo" in hist_ant.columns:
            sub_ant = hist_ant["Subramo"].astype(str).str.upper().str.strip()
            ram_ant = hist_ant["Ramo"].astype(str).str.upper().str.strip()
            # Mapeo inverso simplificado: si segs incluye AUTOSERVICIO → filtrar por esos ramos
            seg_mask_ant = pd.Series(False, index=hist_ant.index)
            for sg in segs:
                if sg == "AUTOSERVICIO":
                    seg_mask_ant |= sub_ant.isin(_AS_SUBSEG) | ram_ant.isin({"AUTOSERVICIO", "LARGE FORMAT"})
                elif sg == "MAYORISTA":
                    seg_mask_ant |= sub_ant.isin(_MAY_SUBSEG) | ram_ant.isin({"CASH&CARRY", "MAYORISTAS"})
                elif sg == "ON_PREMISE":
                    seg_mask_ant |= sub_ant.apply(lambda s: any(k in s for k in _OP_KEYWORDS))
                elif sg == "TRADICIONAL":
                    seg_mask_ant |= sub_ant.apply(lambda s: any(k in s for k in _TR_KEYWORDS))
            h_ant = hist_ant[cat_mask_ant & seg_mask_ant]
        else:
            h_ant = hist_ant[cat_mask_ant]

        litros_ant = float(h_ant["_litros"].sum())
        clis_cat_ant = set(h_ant["_cli"].dropna().astype(int).tolist())

        # Litros MES ACTUAL (misma base que acciones ranking)
        v_m_act = _filtrar_ventas_accion(v_act, canal, cat_key, segs)
        if v_m_act is None or v_m_act.empty:
            litros_act = 0.0
        else:
            litros_act = float(v_m_act["_litros"].sum())

        # Clientes nuevos en la categoría = compraron con esta acción pero NO compraron la categoría en mes anterior
        clis_nuevos_cat  = clis_accion - clis_cat_ant
        clis_retorno     = clis_accion & clis_cat_ant
        n_cli_accion     = len(clis_accion)
        n_nuevos_cat     = len(clis_nuevos_cat)
        n_retorno        = len(clis_retorno)
        pct_nuevos       = round(n_nuevos_cat / max(n_cli_accion, 1) * 100, 1)
        delta_l_pct      = round((litros_act - litros_ant) / max(litros_ant, 1) * 100, 1)

        # Inversión de la acción (desde detalle)
        v_inv = _filtrar_ventas_accion(v_act, canal, cat_key, segs)
        inversion = float(v_inv["_descuento_p"].sum()) if v_inv is not None and not v_inv.empty else 0.0
        costo_activacion = round(inversion / max(n_nuevos_cat, 1), 0)

        filas.append({
            "accion_grupo":          grupo,
            "accion_nombre":         nombre,
            "canal":                 canal,
            "categoria":             cat_key,
            "clientes_mes_actual":   n_cli_accion,
            "clientes_cat_mes_ant":  len(clis_cat_ant),
            "clientes_nuevos_cat":   n_nuevos_cat,
            "clientes_retorno":      n_retorno,
            "pct_clientes_nuevos":   pct_nuevos,
            "litros_mes_actual":     round(litros_act, 1),
            "litros_mes_anterior":   round(litros_ant, 1),
            "delta_litros_pct":      delta_l_pct,
            "inversion_pesos":       round(inversion, 0),
            "costo_activacion":      costo_activacion,
            "mes_actual":            str(mes_actual),
            "mes_anterior":          str(mes_anterior),
            "fecha_calculo":         datetime.now().strftime("%Y-%m-%d"),
        })

    df = pd.DataFrame(filas)
    if not df.empty:
        df = df.sort_values("inversion_pesos", ascending=False).reset_index(drop=True)
    return df


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 50)
    print("generar_datasets_acum.py")
    print("=" * 50)

    print("\nCargando fuentes...")
    ventas   = cargar_ventas_acum()
    ventas_acum_full = cargar_ventas_acumulada()   # periodo completo para innovaciones
    clientes = cargar_clientes()
    bbdd     = cargar_planes_as_bbdd()
    maestro  = cargar_maestro_productos()
    print(f"  ventas (reciente)  : {len(ventas):>6} filas")
    print(f"  ventas (acum full) : {len(ventas_acum_full):>6} filas")
    print(f"  clientes           : {len(clientes):>6} filas")
    print(f"  planes_as BBDD     : {len(bbdd):>6} clientes AS")
    print(f"  maestro productos  : {len(maestro):>6} productos")

    # Snapshot del acumulado (resultado.xlsx) para el real del día en Plan vs Real
    snapshot_acumulado_resultado(ventas)

    # ── Cobertura ──
    print("\n[1/3] Generando mod_cobertura_acum.csv ...")
    cob, cob_det = generar_cobertura_acum(ventas, clientes)
    cob.to_csv(OUT / "mod_cobertura_acum.csv", index=False, encoding="utf-8-sig")
    cob_det.to_csv(OUT / "mod_cobertura_acum_detalle.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(cob)} filas (+ {len(cob_det)} faltantes en mod_cobertura_acum_detalle.csv)")
    print(cob[["vendedor_codigo", "segmento", "cartera", "cubiertos", "pct_cobertura"]].to_string(index=False))

    # ── 11 Titulares ──
    # REGLA 11T: se mide con ventas_acumulada.csv (período comercial completo).
    # NO usar ventas.csv (mes vivo): el 11T es cobertura acumulada, no del mes en curso.
    # El período se acota al TRIMESTRE en curso (el 11T resetea en ene/abr/jul/oct) para que
    # el dataset y el dashboard midan exactamente lo mismo y quede explícito desde/hasta.
    print("\n[2/3] Generando mod_11t_acum.csv ...")
    _desde, _hasta = motor_11t.periodo_trimestre_en_curso()
    # Fuente SIN filtrar vendedores: el motor excluye por el vendedor del padrón, no por el
    # de la factura (ver cargar_ventas_acumulada_11t).
    t11, t11_det, t11_exc = generar_11t_acum(cargar_ventas_acumulada_11t(), clientes,
                                             desde=_desde, hasta=_hasta)
    t11.to_csv(OUT / "mod_11t_acum.csv", index=False, encoding="utf-8-sig")
    # Salida auditable: una fila por cliente x titular con botellas netas y motivo.
    t11_det.to_csv(OUT / "mod_11t_detalle.csv", index=False, encoding="utf-8-sig")
    t11_exc.to_csv(OUT / "mod_11t_excepciones.csv", index=False, encoding="utf-8-sig")
    tiene = int(t11["tiene_flag"].sum())
    total = len(t11)
    print(f"  periodo medido: {_desde} -> {_hasta}")
    print(f"  OK: {total} filas / {tiene} tienen ({round(100*tiene/total,1) if total else 0}%) / {total - tiene} faltan")
    print(f"  + mod_11t_detalle.csv ({len(t11_det)} filas cliente x titular)"
          f" + mod_11t_excepciones.csv ({len(t11_exc)} filas)")
    resumen_11t = (t11.groupby("marca_objetivo")
                   .agg(cartera=("cliente_id","count"), tienen=("tiene_flag","sum"))
                   .reset_index())
    resumen_11t["pct"] = (resumen_11t["tienen"] / resumen_11t["cartera"] * 100).round(1)
    print(resumen_11t.to_string(index=False))

    # ── Planes AS ──
    print("\n[3/5] Generando mod_planes_as.csv ...")
    # REGLA: sin cargos enviados se calculan SOLO desde ventas.csv (período mensual activo).
    # El archivo Reconocimiento Plan As.xlsx se renueva cada mes → define lo adeudado este mes.
    # ventas_acumulada NO aplica: pertenece a un período comercial anterior.
    pas = generar_planes_as(ventas, bbdd, clientes)
    pas.to_csv(OUT / "mod_planes_as.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(pas)} clientes AS")
    cols_show = ["cliente_id", "cliente_nombre", "plan_as", "total_facturado",
                 "sc_total_ganado", "sc_cajas_enviadas_total", "sc_pendiente"]
    print(pas[[c for c in cols_show if c in pas.columns]].to_string(index=False))

    # ── Innovaciones Segmento ──
    print("\n[4/5] Generando mod_innovaciones_segmento.csv ...")
    # MES VIVO: cobertura de innovaciones de ESTE mes desde ventas.csv.
    # NO usar ventas_acumulada (arrastra el mes anterior → cobertura inflada con compras viejas).
    inov_seg = generar_innovaciones_segmento(ventas, clientes)
    inov_seg.to_csv(OUT / "mod_innovaciones_segmento.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(inov_seg)} filas ({inov_seg['producto_nombre'].nunique()} productos x {inov_seg['vendedor_codigo'].nunique()} vendedores x segmentos)")
    resumen_inov = (inov_seg.groupby("producto_nombre")
                    .agg(total_cartera=("clientes_cartera","max"),
                         total_compraron=("clientes_compraron","sum"))
                    .reset_index())
    resumen_inov["pct"] = (resumen_inov["total_compraron"] / resumen_inov["total_cartera"].replace(0, np.nan) * 100).round(1).fillna(0)
    print(resumen_inov.to_string(index=False))

    # ── Innovaciones Plan AS ──
    print("\n[5/7] Generando mod_innovaciones_plan_as.csv ...")
    inov_pas = generar_innovaciones_plan_as(ventas_acum_full, bbdd)  # usa ventas acumuladas completas
    inov_pas.to_csv(OUT / "mod_innovaciones_plan_as.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(inov_pas)} clientes AS")

    # ── Sellout por Categoría ──
    print("\n[6/7] Generando mod_sellout_categoria.csv ...")
    sellout = generar_sellout_categoria(ventas, maestro)
    sellout.to_csv(OUT / "mod_sellout_categoria.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(sellout)} filas ({sellout['Categoria'].nunique()} categorias x {sellout['Segmento'].nunique()} segmentos)")
    resumen_sell = (sellout.groupby("Categoria")
                    .agg(litros_total=("litros","sum"), cajas_total=("cajas","sum"), clientes=("clientes","sum"))
                    .reset_index()
                    .sort_values("litros_total", ascending=False))
    resumen_sell["litros_total"] = resumen_sell["litros_total"].round(1)
    print(resumen_sell.to_string(index=False))

    # ── Acciones Detalle + Análisis ──
    print("\n[7/9] Generando mod_acciones_ranking.csv (detalle por acción) ...")
    acc, clis_por_accion = generar_acciones_ranking(ventas, clientes, maestro)
    acc.to_csv(OUT / "mod_acciones_ranking.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(acc)} acciones")
    if not acc.empty:
        print(acc[["accion_nombre","descuento_display","litros_vendidos","inversion_pesos","clientes_afectados"]].to_string(index=False))

    print("\n[8/9] Generando mod_acciones_analisis.csv (comparativo mes anterior) ...")
    hist_path = BASE / "02_HISTORY" / "historial_ventas.csv"
    analisis = generar_acciones_analisis(ventas, hist_path, clientes, maestro, clis_por_accion)
    analisis.to_csv(OUT / "mod_acciones_analisis.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(analisis)} acciones analizadas")
    if not analisis.empty:
        cols_show = ["accion_nombre","clientes_mes_actual","clientes_nuevos_cat",
                     "pct_clientes_nuevos","delta_litros_pct","costo_activacion"]
        print(analisis[[c for c in cols_show if c in analisis.columns]].to_string(index=False))

    print("\n[OK] Datasets generados en 04_DATASETS_ORBIT/")
    print("     mod_cobertura_acum.csv")
    print("     mod_cobertura_acum_detalle.csv")
    print("     mod_11t_acum.csv")
    print("     mod_planes_as.csv")
    print("     mod_innovaciones_segmento.csv")
    print("     mod_innovaciones_plan_as.csv")
    print("     mod_sellout_categoria.csv")
    print("     mod_acciones_ranking.csv")
    print("     mod_acciones_analisis.csv")


if __name__ == "__main__":
    main()
