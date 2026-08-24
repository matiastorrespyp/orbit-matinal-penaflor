# -*- coding: utf-8 -*-
"""
MOTOR AUTORITATIVO DE COBERTURA 11 TITULARES — ORBIT Matinal Peñaflor
=====================================================================

FUENTE ÚNICA DE VERDAD del 11T. Todo módulo que muestre 11 Titulares (dashboard vivo,
KPI "11T ✓", "Marcas 11T", /api/gerencia/11t_empresa, mod_11t_acum.csv, cierre mensual)
tiene que pasar por acá. No duplicar la regla en ningún otro archivo.

REGLA OFICIAL (validada contra el resultado informado por el proveedor, 2026-08-05)
----------------------------------------------------------------------------------
El 11T es COBERTURA, no CCC comercial. Un cliente cubre un titular cuando, DESPUÉS de
consolidar todas sus líneas válidas del período, alcanza el mínimo de botellas de su
segmento:

    Tradicional (Almacén / Despensa / Kiosco / Maxikiosco) ...  3 botellas
    Autoservicio (incl. Cadenas Regionales / Large Format) ...  6 botellas

El mínimo se aplica SIEMPRE después de sumar. Un cliente se cuenta una sola vez por
titular, por más comprobantes o SKU distintos que tenga.

  NO CONFUNDIR CON EL CCC COMERCIAL. El CCC (cliente con compra, neto>0, sin mínimo)
  sigue definido en server_orbit.py y este motor no lo toca. Contar "cualquier cliente
  con neto>0" como cubierto era el bug: daba 51 clientes en Gordon's julio-2026 contra
  los 32 reales.

SUPERFICIE DE MEDICIÓN (validada con el usuario 2026-07-06)
-----------------------------------------------------------
El 11T se mide SOLO en Autoservicio + Almacén + Kiosco. Todo lo demás (On Premise,
Vinotecas, Bar/Restaurant, Mayoristas, Cash&Carry, Proximity, Fiambrería, Carnicería,
Panadería, "Resto de Tradicionales") queda FUERA DE SUPERFICIE: no se mide y se informa
como excepción — nunca se descarta en silencio.

IDENTIFICACIÓN DEL TITULAR
--------------------------
Por CÓDIGO DE ARTÍCULO exacto contra la matriz oficial
`01_INPUTS/11 titulares autoservicio/11_titulares_autoservicios_match_codigos.xlsx`
(hoja DETALLE_SKU_11T_AS). El texto de `Marca` se usa SOLO como respaldo controlado por
igualdad exacta y SOLO cuando la línea no trae código de artículo.

  PROHIBIDO el match amplio por descripción (`str.contains("GORDON")`). Era lo que metía
  GORDON'S GIN (30075) y GORDON'S TONIC (35107) dentro de Gordon's Flavours, cuyo universo
  oficial son únicamente 30134 (Pink Gin) y 30139 (Tropical Fruits).

Un SKU que no resuelve contra la matriz se reporta en `excepciones()`, no se adivina.

UNIDAD DE CANTIDAD
------------------
`CantBase` ya viene en BOTELLAS/UNIDADES, no en cajas. Confirmado contra el maestro 04D:
`_litros_por_linea()` calcula litros como `CantBase x (Lts_caja / UxC)`, es decir
CantBase x litros-por-botella. NO se vuelve a multiplicar por unidades por caja.
Las notas de crédito traen CantBase negativa, así que la suma da botellas NETAS.

VENDEDOR Y EXCLUSIONES — DOS UNIVERSOS
--------------------------------------
El cliente pertenece a la cartera del PADRÓN (`clientes.xlsx.codven`), no al vendedor que
emitió la factura. Las exclusiones se aplican sobre el vendedor del padrón.

Cada fila del detalle trae `universo`, y cae en EXACTAMENTE UNO:

    VENDEDORES  cliente de la cartera de un vendedor de ruta. El único que va a
                rankings, cartera, selectores y cumplimiento individual.
    DEPOSITO    cliente del Depósito / venta directa (codven V1/V20). Vende de verdad,
                pero no es un vendedor: sin cartera, sin ranking, sin objetivo propio.
    SIN_CARTERA cliente SIN codven o sin asignación válida en el padrón. NO es Depósito:
                es un hueco del ERP. Se separa a propósito para que se vea y se corrija.

Los TRES suman al total de EMPRESA. `BAJA` (V2/V5) no es un universo: queda fuera de todo.

`cuenta_vendedor` (bool) se mantiene como atajo de `universo == "VENDEDORES"`.

No hay doble conteo posible: el padrón deja UNA fila por cliente (ver `motor_padron`), así
que cada cliente cae en exactamente un universo. Vale la identidad, testeada:

    cubiertos_empresa = cubiertos_vendedores + cubiertos_deposito + cubiertos_sin_cartera

POR QUÉ DEPOSITO Y SIN_CARTERA NO SON LO MISMO
-----------------------------------------------
Los dos quedan fuera de los rankings, así que es tentador meterlos en la misma bolsa. No
lo son, y confundirlos esconde un problema:

  DEPOSITO    es una decisión comercial. Está bien que exista. No hay nada que corregir.
  SIN_CARTERA es un dato faltante del ERP. Alguien tiene que asignarle cartera.

Etiquetar un cliente sin `codven` como "Depósito" lo hace pasar por venta directa legítima
y el hueco no se arregla nunca. Por eso `SIN_CARTERA` sale listado, cliente por cliente,
en las excepciones y en `mod_11t_detalle.csv`.

  Por qué importa: en julio-2026 el cliente 15 (BELTRAMO, DUTTO Y DUTTO — Autoservicio de
  la cartera de V8) compró 60 botellas de Gordon's facturadas por V20 Depósito. Filtrando
  por el vendedor de la FACTURA, ese cliente desaparecía de la cobertura de la empresa y
  Gordon's Autoservicio daba 6 en vez de 7. V20 no es un vendedor de ruta: es un canal de
  facturación de la misma entidad física, igual que P&P Logística en `_LEEME_EMPRESA`.
  V20 sigue excluido de las métricas CON OBJETIVO por vendedor; acá no se le atribuye nada,
  solo se consolida la venta en el cliente que corresponde.

  El caso simétrico: el cliente 2508 (CLIENTES VARIOS, mostrador del depósito) pertenece al
  bucket `codven=1 deposito`. No es de nadie, así que no puede ir a un ranking — pero si
  compra 6 botellas de un titular, ESO ES VENTA DE LA DISTRIBUIDORA y tiene que estar en el
  total de empresa. Hasta 2026-08-05 se descartaba por el mismo filtro que sacaba a V20 de
  los rankings. Hoy entra al universo EMPRESA como `DEPOSITO`.

CASO DE REGRESIÓN OBLIGATORIO
-----------------------------
Gordon's Flavours, julio 2026, `01_INPUTS/cierres mes/ventas_acumulada_072026.csv`:
    Tradicional 25 · Autoservicio 7 · TOTAL 32
Se calcula, no se hardcodea. Ver `test_motor_11t.py`.
"""
from __future__ import annotations

import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

import motor_padron          # regla única de pertenencia de cartera (duplicados del padrón)

BASE = Path(__file__).resolve().parent
INPUTS = BASE / "01_INPUTS"
MATRIZ_11T_PATH = INPUTS / "11 titulares autoservicio" / "11_titulares_autoservicios_match_codigos.xlsx"
MATRIZ_11T_HOJA = "DETALLE_SKU_11T_AS"
CLIENTES_PATH = INPUTS / "clientes.xlsx"

# ─────────────────────────────────────────────────────────────────────────────
# REGLAS
# ─────────────────────────────────────────────────────────────────────────────

#: Mínimo de botellas acumuladas por segmento para dar el titular por cubierto.
UMBRALES_11T = {
    "AUTOSERVICIO": 6,
    "TRADICIONAL": 3,
}

# ── DOS UNIVERSOS (regla definitiva 2026-08-05) ──────────────────────────────
# El 11T se lee en dos universos distintos y NO son el mismo filtro:
#
#   EMPRESA    : todo lo que integra el total comercial de la distribuidora,
#                INCLUIDO el Depósito / venta directa. Es el número que se compara
#                contra el objetivo de la empresa y contra el reporte del proveedor.
#   VENDEDORES : sólo los vendedores de ruta. Alimenta rankings, cartera, selectores,
#                cumplimiento individual y cualquier promedio entre vendedores.
#
# Tener un solo filtro para las dos cosas era el bug: al excluir el Depósito del
# universo VENDEDORES (correcto) se lo excluía también del total de EMPRESA (incorrecto),
# y la venta directa desaparecía del 11T de la distribuidora.

#: Bajas: fuera de TODO, de los dos universos. V2 y V5 no operan (regla Peñaflor).
VENDEDORES_BAJA = (2, 5)

#: Depósito / venta directa: códigos con los que opera el Depósito. NO son vendedores de
#: ruta: no tienen cartera, no van a rankings ni a selectores y no generan cumplimiento
#: individual. Sus ventas válidas SÍ suman al universo EMPRESA. V1 es el bucket "deposito"
#: del padrón (27 clientes: CLIENTES VARIOS, DELFIN S.A., mostradores) y V20 es el código
#: con el que el Depósito factura. Son la misma entidad física, igual que P&P Logística en
#: `_LEEME_EMPRESA`: distinto canal de facturación, misma distribuidora.
#:
#: OJO: acá van SÓLO los códigos del Depósito. Un cliente sin `codven` NO es Depósito
#: (ver UNIVERSO_SIN_CARTERA): es un cliente al que le falta asignación en el ERP.
VENDEDORES_DEPOSITO = (1, 20)

#: Quiénes NO son vendedores de ruta = universo VENDEDORES por complemento.
#: Se conserva el nombre histórico porque varios módulos ya lo importan.
VENDEDORES_EXCLUIDOS_11T = VENDEDORES_BAJA + VENDEDORES_DEPOSITO

# ── Etiquetas de universo (una fila cae en EXACTAMENTE una) ──────────────────
#: Cliente de la cartera de un vendedor de ruta. Único universo que va a rankings.
UNIVERSO_VENDEDORES = "VENDEDORES"
#: Cliente del Depósito / venta directa (codven en VENDEDORES_DEPOSITO). Es una
#: decisión comercial: el Depósito existe y vende, simplemente no es un vendedor.
UNIVERSO_DEPOSITO = "DEPOSITO"
#: Cliente SIN `codven` o sin asignación válida en el padrón. NO es Depósito: es un
#: hueco del ERP. Se separa a propósito para que se vea y se corrija, en vez de quedar
#: escondido dentro de "Depósito" como si fuera venta directa legítima.
#: Caso testigo: #786 ANSELMI Y CIA (Autoservicio grande, 1.560 botellas de Smirnoff
#: Flavours en julio-2026). Suma al total de empresa, no va a ningún ranking, y queda
#: listado en la salida auditable hasta que el ERP le asigne cartera.
UNIVERSO_SIN_CARTERA = "SIN_CARTERA"
#: Los tres universos que suman al total de EMPRESA, en orden de reporte.
UNIVERSOS_EMPRESA = (UNIVERSO_VENDEDORES, UNIVERSO_DEPOSITO, UNIVERSO_SIN_CARTERA)

#: Segmento asignado a lo que queda fuera de la superficie del 11T.
FUERA_DE_SUPERFICIE = "FUERA_DE_SUPERFICIE"
SIN_PADRON = "SIN_PADRON"

# Vocabulario del ERP normalizado (sin tildes, mayúsculas, sin espacios sobrantes).
# El SubSegmento manda sobre el Ramo: el ERP mete carnicerías y verdulerías bajo
# Ramo = AWAY FROM HOME (ver _clasificar en generar_datasets_acum.py).
_AS_KEYS = ("AUTOSERVICIO", "AUTOSERVICIOS", "CADENA REGIONAL", "CADENAS REGIONALES",
            "LARGE FORMAT", "SAR")
# Mayorista y Cash&Carry NO son Autoservicio para el 11T (validado 2026-07-06).
_NO_AS_KEYS = ("MAYORISTA", "CASH&CARRY", "CASH & CARRY", "CASH AND CARRY")
# "KIOSK" cubre KIOSCO y KIOSKO, las dos grafías que usa el ERP.
_TRAD_KEYS = ("ALMACEN", "ALMACENES", "DESPENSA", "KIOSK", "MAXIKIOSCO")


def _norm(txt) -> str:
    """Normaliza texto de segmento: sin tildes, mayúsculas, espacios colapsados."""
    s = str(txt or "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def normalizar_segmento_11t(ramo, subsegmento) -> str:
    """Segmento del 11T: AUTOSERVICIO, TRADICIONAL o FUERA_DE_SUPERFICIE.

    El SubSegmento decide solo; el Ramo es el fallback. Mayoristas y Cash&Carry quedan
    fuera aunque el texto diga "autoservicio". Todo lo que no sea AS/Almacén/Kiosco cae
    en FUERA_DE_SUPERFICIE y se informa como excepción (no se mide, no se descarta)."""
    s, r = _norm(subsegmento), _norm(ramo)
    combinado = f"{s} | {r}"
    if any(k in combinado for k in _NO_AS_KEYS):
        return FUERA_DE_SUPERFICIE
    for texto in (s, r):                      # el SubSegmento decide solo
        if any(k in texto for k in _AS_KEYS):
            return "AUTOSERVICIO"
        if any(k in texto for k in _TRAD_KEYS):
            return "TRADICIONAL"
    return FUERA_DE_SUPERFICIE


# Las normalizaciones de código viven en motor_padron: una sola definición para todo el
# sistema. Se re-exportan acá porque varios módulos ya las importan desde motor_11t.
normalizar_codigo_vendedor = motor_padron.normalizar_codigo_vendedor
normalizar_codigo_cliente = motor_padron.normalizar_codigo_cliente


# ─────────────────────────────────────────────────────────────────────────────
# MATRIZ OFICIAL DE TITULARES (única — no duplicar la lista en otros módulos)
# ─────────────────────────────────────────────────────────────────────────────

_MATRIZ_CACHE = {"mtime": None, "data": None}
#: Nombre de línea en la matriz -> marca canónica que usa el resto del sistema.
_NORM_TITULAR = {"SMF ICE": "SMIRNOFF ICE"}


import motor_codigos   # equivalencias codigo catalogo -> codigo ERP


def cargar_matriz_11t(path=None) -> pd.DataFrame:
    """Matriz oficial SKU -> titular. Cacheada por mtime.

    Devuelve DataFrame [codigo_articulo:int, titular:str, descripcion:str].
    Si el archivo no está, devuelve vacío: el motor NO inventa titulares."""
    p = Path(path) if path else MATRIZ_11T_PATH
    if not p.exists():
        return pd.DataFrame(columns=["codigo_articulo", "titular", "descripcion"])
    try:
        mt = p.stat().st_mtime
    except OSError:
        mt = 0
    if _MATRIZ_CACHE["data"] is not None and _MATRIZ_CACHE["mtime"] == mt:
        return _MATRIZ_CACHE["data"].copy()

    d = pd.read_excel(p, sheet_name=MATRIZ_11T_HOJA)
    cod = pd.to_numeric(d.get("codigo_articulo"), errors="coerce")
    tit = d.get("linea_comercial_11t", pd.Series("", index=d.index)).astype(str).map(_norm)
    tit = tit.map(lambda x: _NORM_TITULAR.get(x, x))
    out = pd.DataFrame({
        "codigo_articulo": cod,
        "titular": tit,
        "descripcion": d.get("descripcion_articulo", pd.Series("", index=d.index)).astype(str),
    })
    out = out[out["codigo_articulo"].notna() & out["titular"].ne("") & out["titular"].ne("NAN")]
    out["codigo_articulo"] = out["codigo_articulo"].astype(int)
    # El código de la matriz es el del CATÁLOGO DEL PROVEEDOR, que no siempre coincide con
    # el que usa nuestro ERP para el mismo producto. Sin esto, la venta de ese SKU no le
    # suma al titular y en la pantalla Stock figura como "no está en el archivo de stock",
    # que se lee como "no tenemos" en vez de "estamos mirando el código equivocado".
    out["codigo_articulo"] = motor_codigos.canonizar_serie(out["codigo_articulo"])
    out = out.drop_duplicates(subset=["codigo_articulo"], keep="first").reset_index(drop=True)
    _MATRIZ_CACHE.update({"mtime": mt, "data": out})
    return out.copy()


def titulares_oficiales(path=None) -> list:
    """Los titulares vigentes según la matriz. Única fuente de la lista de marcas."""
    return sorted(cargar_matriz_11t(path)["titular"].unique().tolist())


def _mapa_sku_titular(path=None) -> dict:
    m = cargar_matriz_11t(path)
    return dict(zip(m["codigo_articulo"], m["titular"]))


def _mapa_alias_marca(path=None) -> dict:
    """Respaldo controlado: texto EXACTO de `Marca` -> titular, derivado de la propia
    matriz (no una lista paralela). Solo se usa cuando la línea no trae código."""
    m = cargar_matriz_11t(path)
    return {t: t for t in m["titular"].unique()}


# ─────────────────────────────────────────────────────────────────────────────
# PADRÓN DE CLIENTES (fuente autoritativa de segmento y de cartera)
# ─────────────────────────────────────────────────────────────────────────────

_PADRON_CACHE = {"mtime": None, "data": None}
_PADRON_INCIDENCIAS = {"data": None}


def cargar_padron_clientes(path=None) -> pd.DataFrame:
    """Padrón normalizado: [cliente_id, cliente_nombre, vendedor_codigo, vendedor_nombre,
    segmento_11t, ramo, subsegmento, duplicado_padron].

    Los duplicados los resuelve `motor_padron.resolver_padron` — regla única de todo el
    sistema. Para los clientes cargados a la vez en V3 y V8 prevalece **V8**, con su fila
    entera (incluidos DiasVisita y Orden). Antes acá se elegía el menor `codven`, que era
    una regla arbitraria y mandaba esos 10 clientes a la cartera equivocada (V3)."""
    p = Path(path) if path else CLIENTES_PATH
    if not p.exists():
        return pd.DataFrame(columns=["cliente_id", "cliente_nombre", "vendedor_codigo",
                                     "vendedor_nombre", "segmento_11t", "ramo",
                                     "subsegmento", "duplicado_padron"])
    try:
        mt = p.stat().st_mtime
    except OSError:
        mt = 0
    if _PADRON_CACHE["data"] is not None and _PADRON_CACHE["mtime"] == mt:
        return _PADRON_CACHE["data"].copy()

    c = pd.read_excel(p)
    sub_col = next((x for x in c.columns
                    if "subseg" in str(x).lower() or "subramo" in str(x).lower()), None)
    nom_col = next((x for x in c.columns
                    if str(x).lower().replace("_", "") in ("razonsocial", "nombre", "cliente")), None)
    out = pd.DataFrame({
        "cliente_id": c["Codigo"].map(normalizar_codigo_cliente),
        "cliente_nombre": c[nom_col].astype(str) if nom_col else "",
        "vendedor_codigo": c["codven"].map(normalizar_codigo_vendedor),
        "vendedor_nombre": c["Vendedor"].astype(str) if "Vendedor" in c.columns else "",
        "ramo": c["Ramo"].astype(str) if "Ramo" in c.columns else "",
        "subsegmento": c[sub_col].astype(str) if sub_col else "",
    })
    out = out[out["cliente_id"].notna()].copy()
    out["cliente_id"] = out["cliente_id"].astype(int)
    out["segmento_11t"] = [normalizar_segmento_11t(r, s)
                           for r, s in zip(out["ramo"], out["subsegmento"])]
    out["duplicado_padron"] = out["cliente_id"].duplicated(keep=False)
    out, inc = motor_padron.resolver_padron(
        out, col_codigo="cliente_id", col_vendedor="vendedor_codigo",
        col_nombre="cliente_nombre", origen="motor_11t")
    motor_padron.avisar_incidencias(inc, "motor_11t")
    out = out.reset_index(drop=True)
    _PADRON_INCIDENCIAS["data"] = inc
    _PADRON_CACHE.update({"mtime": mt, "data": out})
    return out.copy()


def incidencias_padron() -> pd.DataFrame:
    """Duplicados detectados en la última carga del padrón (resueltos y sin regla).
    Se expone para que los reportes puedan mostrarlos como excepción auditable."""
    inc = _PADRON_INCIDENCIAS.get("data")
    return inc.copy() if inc is not None else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# MOTOR
# ─────────────────────────────────────────────────────────────────────────────

_COLS_DETALLE = [
    "periodo_desde", "periodo_hasta", "cliente_id", "cliente_nombre", "vendedor_codigo",
    "vendedor_id", "vendedor_nombre", "universo", "cuenta_vendedor",
    "segmento_11t", "titular", "skus",
    "botellas_positivas", "botellas_devueltas", "botellas_netas", "umbral",
    "cumple", "motivo",
]


def cobertura_11t(ventas,
                  *,
                  clientes=None,
                  matriz=None,
                  desde=None,
                  hasta=None,
                  vendedores_excluidos=VENDEDORES_BAJA,
                  vendedores_deposito=VENDEDORES_DEPOSITO,
                  umbrales=None,
                  col_fecha="FechaComprobante",
                  dayfirst=True):
    """Cobertura 11T: una fila por (cliente, titular) medida en botellas netas.

    Parámetros
    ----------
    ventas : DataFrame de ventas del ERP. Necesita Cliente, Codigo, CantBase,
             ImporteNetoItem y, para acotar el período, `col_fecha`.
    clientes : padrón. None = `01_INPUTS/clientes.xlsx`. Fuente autoritativa del
             segmento y del vendedor de cartera.
    matriz : matriz SKU->titular. None = matriz oficial del proyecto.
    desde / hasta : período medido (inclusive). None = sin acotar por ese lado.
             El período se devuelve en cada fila para que la pantalla lo pueda mostrar.
    vendedores_excluidos : códigos DEL PADRÓN dados de baja. Se descartan de los DOS
             universos (empresa y vendedores). Default: `VENDEDORES_BAJA` = V2/V5.
    vendedores_deposito : códigos del Depósito / venta directa. NO se descartan: suman
             al universo EMPRESA como `DEPOSITO`, y nunca aparecen en un ranking ni en un
             cumplimiento individual. Default: `VENDEDORES_DEPOSITO` = V1/V20.
             Un cliente sin `codven` NO entra acá: va a `SIN_CARTERA`.
    umbrales : {segmento: mínimo de botellas}. None = UMBRALES_11T (3 trad / 6 AS).

    Devuelve
    --------
    (detalle, excepciones) — dos DataFrames.
    `detalle` trae `_COLS_DETALLE`; `cumple` es booleano y ya tiene el mínimo aplicado
    DESPUÉS de consolidar, `universo` es VENDEDORES / DEPOSITO / SIN_CARTERA (mutuamente
    excluyentes) y `cuenta_vendedor` es el atajo `universo == VENDEDORES`.
    `excepciones` lista lo que no se pudo medir o se midió aparte (SKU fuera de la matriz,
    cliente sin padrón, segmento fuera de superficie, vendedor de baja, DEPOSITO y
    CLIENTE_SIN_CARTERA — este último con los códigos de cliente, para trazabilidad).
    """
    umbrales = dict(umbrales or UMBRALES_11T)
    padron = cargar_padron_clientes() if clientes is None else clientes.copy()
    mapa_sku = (dict(zip(matriz["codigo_articulo"], matriz["titular"]))
                if matriz is not None else _mapa_sku_titular())
    alias_marca = ({t: t for t in matriz["titular"].unique()}
                   if matriz is not None else _mapa_alias_marca())

    vacio_det = pd.DataFrame(columns=_COLS_DETALLE)
    vacio_exc = pd.DataFrame(columns=["tipo", "clave", "detalle", "filas", "botellas"])
    if ventas is None or len(ventas) == 0:
        return vacio_det, vacio_exc

    v = ventas.copy()
    v.columns = [str(c).strip().lstrip("﻿") for c in v.columns]

    # ── período ──────────────────────────────────────────────────────────────
    if col_fecha in v.columns:
        fechas = pd.to_datetime(v[col_fecha], dayfirst=dayfirst, errors="coerce", format="mixed")
    else:
        fechas = pd.Series(pd.NaT, index=v.index)
    if desde is not None:
        v = v[fechas >= pd.Timestamp(desde)]
        fechas = fechas.loc[v.index]
    if hasta is not None:
        # `hasta` inclusive: se compara contra el fin del día.
        tope = pd.Timestamp(hasta) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        v = v[fechas <= tope]
        fechas = fechas.loc[v.index]
    per_desde = str(pd.Timestamp(desde).date()) if desde is not None else (
        str(fechas.min().date()) if fechas.notna().any() else "")
    per_hasta = str(pd.Timestamp(hasta).date()) if hasta is not None else (
        str(fechas.max().date()) if fechas.notna().any() else "")
    if v.empty:
        return vacio_det, vacio_exc

    # ── numéricos ────────────────────────────────────────────────────────────
    # CantBase ya está en botellas/unidades; las NC vienen en negativo -> suma = neto.
    v["_cant"] = pd.to_numeric(
        v["CantBase"].astype(str).str.strip().str.strip('"').str.replace(",", ".", regex=False),
        errors="coerce").fillna(0.0)
    v["_neto"] = pd.to_numeric(
        v["ImporteNetoItem"].astype(str).str.strip().str.strip('"').str.replace(",", ".", regex=False),
        errors="coerce").fillna(0.0)
    v["_cli"] = v["Cliente"].map(normalizar_codigo_cliente)
    v["_cod"] = pd.to_numeric(v.get("Codigo"), errors="coerce")

    excepciones = []

    # ── líneas comerciales válidas ───────────────────────────────────────────
    # Se conservan las devoluciones (neto<0, CantBase<0) para que resten botellas.
    # Se descartan las de neto == 0: son sin cargo / bonificaciones (Descuento 100%),
    # que no computan cobertura con el criterio comercial vigente.
    sin_cargo = v[v["_neto"] == 0]
    if len(sin_cargo):
        excepciones.append({"tipo": "LINEA_SIN_CARGO_NETO_CERO", "clave": "",
                            "detalle": "neto=0 (bonificacion/sin cargo): no computa cobertura",
                            "filas": len(sin_cargo), "botellas": float(sin_cargo["_cant"].sum())})
    v = v[v["_neto"] != 0].copy()
    if v.empty:
        return vacio_det, pd.DataFrame(excepciones)

    # ── titular por SKU (matriz oficial) + respaldo exacto por Marca ─────────
    v["titular"] = v["_cod"].map(mapa_sku)
    sin_codigo = v["_cod"].isna() & v["titular"].isna()
    if sin_codigo.any() and "Marca" in v.columns:
        # Respaldo controlado: igualdad EXACTA del texto de Marca, solo sin código.
        v.loc[sin_codigo, "titular"] = v.loc[sin_codigo, "Marca"].map(_norm).map(alias_marca)

    no_resuelto = v[v["titular"].isna() & v["_cod"].notna()]
    if len(no_resuelto):
        agg = (no_resuelto.groupby(["_cod"])
               .agg(filas=("_cant", "size"), botellas=("_cant", "sum"),
                    desc=("Articulo", "first") if "Articulo" in v.columns else ("_cod", "first"))
               .reset_index())
        for _, r in agg.iterrows():
            excepciones.append({"tipo": "SKU_SIN_MATCH_EN_MATRIZ", "clave": int(r["_cod"]),
                                "detalle": f"{r['desc']} — no pertenece a ningun titular oficial",
                                "filas": int(r["filas"]), "botellas": float(r["botellas"])})
    v = v[v["titular"].notna()].copy()
    if v.empty:
        return vacio_det, pd.DataFrame(excepciones)

    # ── cliente: segmento y cartera desde el padrón ──────────────────────────
    p = padron.set_index("cliente_id")
    v["cliente_nombre"] = v["_cli"].map(p["cliente_nombre"]).fillna("")
    v["vendedor_codigo"] = v["_cli"].map(p["vendedor_codigo"])
    v["vendedor_nombre"] = v["_cli"].map(p["vendedor_nombre"]).fillna("")
    v["segmento_11t"] = v["_cli"].map(p["segmento_11t"]).fillna(SIN_PADRON)

    fuera_padron = v[v["segmento_11t"] == SIN_PADRON]
    if len(fuera_padron):
        excepciones.append({"tipo": "CLIENTE_SIN_PADRON", "clave": "",
                            "detalle": "cliente no esta en clientes.xlsx: sin segmento ni cartera",
                            "filas": len(fuera_padron),
                            "botellas": float(fuera_padron["_cant"].sum())})
    dup = padron[padron.get("duplicado_padron", False) == True]["cliente_id"].tolist()  # noqa: E712
    if dup:
        excepciones.append({"tipo": "CLIENTE_DUPLICADO_EN_PADRON", "clave": ",".join(map(str, sorted(dup))),
                            "detalle": ("cargado mas de una vez en clientes.xlsx; resuelto por "
                                        "motor_padron (V3/V8 -> V8). Corregir la cartera en el ERP"),
                            "filas": len(dup), "botellas": 0.0})

    # Bajas: fuera de los dos universos, se descartan.
    baja = {normalizar_codigo_vendedor(x) for x in (vendedores_excluidos or ())}
    es_baja = v["vendedor_codigo"].isin(baja)
    if es_baja.any():
        excepciones.append({"tipo": "VENDEDOR_DE_BAJA", "clave": ",".join(map(str, sorted(baja))),
                            "detalle": "cliente de cartera dada de baja (padron): fuera de empresa y de vendedores",
                            "filas": int(es_baja.sum()),
                            "botellas": float(v.loc[es_baja, "_cant"].sum())})
    v = v[~es_baja & (v["segmento_11t"] != SIN_PADRON)].copy()

    # ── Universo: VENDEDORES / DEPOSITO / SIN_CARTERA ────────────────────────
    # Ninguno se descarta: los tres suman a EMPRESA. Lo que cambia es quién puede ir a un
    # ranking. Las tres categorías son mutuamente excluyentes (se asignan con un where
    # encadenado sobre la misma columna), así que no hay doble conteo posible.
    dep_cods = {normalizar_codigo_vendedor(x) for x in (vendedores_deposito or ())}
    es_dep = v["vendedor_codigo"].isin(dep_cods)
    # Sin codven o sin asignación válida. NO es Depósito: es un hueco del ERP.
    es_sin_cart = v["vendedor_codigo"].isna() & ~es_dep
    v["universo"] = UNIVERSO_VENDEDORES
    v.loc[es_dep, "universo"] = UNIVERSO_DEPOSITO
    v.loc[es_sin_cart, "universo"] = UNIVERSO_SIN_CARTERA
    v["cuenta_vendedor"] = v["universo"] == UNIVERSO_VENDEDORES

    if es_dep.any():
        excepciones.append({"tipo": "DEPOSITO", "clave": ",".join(map(str, sorted(dep_cods))),
                            "detalle": ("deposito/venta directa (V1/V20): SUMA al total de empresa, "
                                        "sin cartera ni ranking ni cumplimiento individual. "
                                        "Es una decision comercial, no hay nada que corregir"),
                            "filas": int(es_dep.sum()),
                            "botellas": float(v.loc[es_dep, "_cant"].sum())})
    if es_sin_cart.any():
        # Trazabilidad explícita: se listan los códigos de cliente, no un total anónimo.
        # Es el hueco que alguien tiene que cerrar en el ERP.
        _ids = sorted({int(c) for c in v.loc[es_sin_cart, "_cli"].dropna().unique()})
        excepciones.append({"tipo": "CLIENTE_SIN_CARTERA", "clave": ",".join(map(str, _ids)),
                            "detalle": ("cliente sin codven o sin asignacion valida en el padron: "
                                        "SUMA al total de empresa, fuera de rankings y objetivos "
                                        "individuales. NO es deposito — asignar cartera en el ERP"),
                            "filas": int(es_sin_cart.sum()),
                            "botellas": float(v.loc[es_sin_cart, "_cant"].sum())})

    fuera_sup = v[v["segmento_11t"] == FUERA_DE_SUPERFICIE]
    if len(fuera_sup):
        det_sup = (fuera_sup.groupby("_cli")["_cant"].sum())
        excepciones.append({"tipo": "SEGMENTO_FUERA_DE_SUPERFICIE", "clave": "",
                            "detalle": ("On Premise/Vinoteca/Mayorista/Proximity/resto: el 11T mide "
                                        "solo Autoservicio + Almacen + Kiosco"),
                            "filas": int(len(det_sup)), "botellas": float(fuera_sup["_cant"].sum())})
    v = v[v["segmento_11t"] != FUERA_DE_SUPERFICIE].copy()
    if v.empty:
        return vacio_det, pd.DataFrame(excepciones)

    # ── consolidación por cliente x titular, y RECIÉN AHÍ el mínimo ──────────
    v["_pos"] = v["_cant"].clip(lower=0)
    v["_neg"] = v["_cant"].clip(upper=0)
    det = (v.groupby(["_cli", "cliente_nombre", "vendedor_codigo", "vendedor_nombre",
                      "segmento_11t", "titular", "universo", "cuenta_vendedor"], dropna=False)
             .agg(botellas_positivas=("_pos", "sum"),
                  botellas_devueltas=("_neg", "sum"),
                  botellas_netas=("_cant", "sum"),
                  skus=("_cod", lambda s: ",".join(
                      sorted({str(int(x)) for x in s.dropna().unique()}))))
             .reset_index()
             .rename(columns={"_cli": "cliente_id"}))

    det["umbral"] = det["segmento_11t"].map(umbrales)
    det["cumple"] = det["botellas_netas"] >= det["umbral"]
    det["vendedor_codigo"] = det["vendedor_codigo"].astype("Int64")
    det["cuenta_vendedor"] = det["cuenta_vendedor"].astype(bool)
    # El identificador dice de qué universo es la fila: si sale a pantalla o a un CSV no
    # puede leerse como un vendedor más, y SIN_CARTERA no puede disfrazarse de DEPOSITO.
    det["vendedor_id"] = [
        f"V{int(c)}" if u == UNIVERSO_VENDEDORES and pd.notna(c) else u
        for c, u in zip(det["vendedor_codigo"], det["universo"])
    ]
    det["periodo_desde"] = per_desde
    det["periodo_hasta"] = per_hasta
    det["motivo"] = [
        (f"cubre: {n:g} botellas netas >= minimo {u:g} de {s}" if c
         else f"no cubre: {n:g} botellas netas < minimo {u:g} de {s}")
        for c, n, u, s in zip(det["cumple"], det["botellas_netas"], det["umbral"], det["segmento_11t"])
    ]
    det = det[_COLS_DETALLE].sort_values(["titular", "segmento_11t", "cliente_id"]).reset_index(drop=True)
    return det, pd.DataFrame(excepciones)


# ─────────────────────────────────────────────────────────────────────────────
# RESÚMENES (todos derivan del mismo `detalle`: no puede haber dos verdades)
# ─────────────────────────────────────────────────────────────────────────────

def resumen_por_titular(detalle, objetivos=None) -> pd.DataFrame:
    """Cobertura por titular en el universo EMPRESA: clientes cubiertos, medidos y
    apertura trad/AS.

    `cubiertos` es el total de la distribuidora e INCLUYE Depósito y Sin Cartera: es el
    número que se compara contra el objetivo de empresa. Se devuelve además abierto en
    `cubiertos_vendedores` + `cubiertos_deposito` + `cubiertos_sin_cartera`, que suman
    exactamente `cubiertos` (un cliente pertenece a un solo universo — ver
    `test_motor_11t.SinDobleConteo`). Para rankings y cumplimiento individual usar
    `resumen_por_vendedor`, que sólo mira el universo VENDEDORES."""
    cols = ["titular", "cubiertos", "cubiertos_vendedores", "cubiertos_deposito",
            "cubiertos_sin_cartera", "cubiertos_tradicional", "cubiertos_autoservicio",
            "medidos", "objetivo", "pct_objetivo"]
    if detalle is None or detalle.empty:
        return pd.DataFrame(columns=cols)
    d = detalle
    ok = d[d["cumple"]]
    r = (d.groupby("titular")
           .agg(medidos=("cliente_id", "nunique")).reset_index())
    r["cubiertos"] = r["titular"].map(ok.groupby("titular")["cliente_id"].nunique()).fillna(0).astype(int)
    # Apertura por universo. `universo` puede no estar si llega un detalle viejo: en ese
    # caso se cae a `cuenta_vendedor`, y si tampoco está, todo se cuenta como VENDEDORES.
    if "universo" in ok.columns:
        _uni = ok["universo"]
    elif "cuenta_vendedor" in ok.columns:
        _uni = ok["cuenta_vendedor"].map({True: UNIVERSO_VENDEDORES, False: UNIVERSO_DEPOSITO})
    else:
        _uni = pd.Series(UNIVERSO_VENDEDORES, index=ok.index)
    for uni, col in ((UNIVERSO_VENDEDORES, "cubiertos_vendedores"),
                     (UNIVERSO_DEPOSITO, "cubiertos_deposito"),
                     (UNIVERSO_SIN_CARTERA, "cubiertos_sin_cartera")):
        s = ok[_uni == uni].groupby("titular")["cliente_id"].nunique()
        r[col] = r["titular"].map(s).fillna(0).astype(int)
    for seg, col in (("TRADICIONAL", "cubiertos_tradicional"), ("AUTOSERVICIO", "cubiertos_autoservicio")):
        s = ok[ok["segmento_11t"] == seg].groupby("titular")["cliente_id"].nunique()
        r[col] = r["titular"].map(s).fillna(0).astype(int)
    objetivos = objetivos or {}
    r["objetivo"] = r["titular"].map(objetivos)
    r["pct_objetivo"] = [round(c / o * 100, 1) if o else None
                         for c, o in zip(r["cubiertos"], r["objetivo"])]
    return r[cols].sort_values("cubiertos", ascending=False).reset_index(drop=True)


def solo_vendedores(detalle) -> pd.DataFrame:
    """Universo VENDEDORES: descarta DEPOSITO y SIN_CARTERA.

    Es el filtro que tiene que aplicar TODO lo que sea ranking, cartera, selector de
    vendedores, cumplimiento individual o promedio entre vendedores."""
    if detalle is None or detalle.empty:
        return detalle
    if "universo" in detalle.columns:
        return detalle[detalle["universo"] == UNIVERSO_VENDEDORES]
    if "cuenta_vendedor" in detalle.columns:
        return detalle[detalle["cuenta_vendedor"]]
    return detalle


def clientes_sin_cartera(detalle) -> pd.DataFrame:
    """Salida auditable de los clientes SIN_CARTERA: quién es, cuánto movió y en qué
    titulares. Es el hueco del ERP que hay que cerrar — no es venta directa del Depósito.

    Una fila por cliente, con los titulares que cubre y las botellas netas totales."""
    cols = ["cliente_id", "cliente_nombre", "segmento_11t", "titulares_cubiertos",
            "titulares", "botellas_netas"]
    if detalle is None or detalle.empty or "universo" not in detalle.columns:
        return pd.DataFrame(columns=cols)
    d = detalle[detalle["universo"] == UNIVERSO_SIN_CARTERA]
    if d.empty:
        return pd.DataFrame(columns=cols)
    r = (d.groupby(["cliente_id", "cliente_nombre", "segmento_11t"], dropna=False)
           .agg(titulares_cubiertos=("cumple", "sum"),
                titulares=("titular", lambda s: ", ".join(sorted(set(s)))),
                botellas_netas=("botellas_netas", "sum"))
           .reset_index())
    r["titulares_cubiertos"] = r["titulares_cubiertos"].astype(int)
    return r[cols].sort_values("botellas_netas", ascending=False).reset_index(drop=True)


def resumen_por_vendedor(detalle) -> pd.DataFrame:
    """Cobertura por vendedor de cartera x titular — universo VENDEDORES.

    El Depósito NO genera fila acá: no tiene cartera ni cumplimiento individual."""
    cols = ["vendedor_codigo", "vendedor_id", "vendedor_nombre", "titular",
            "cartera_medida", "cubiertos"]
    if detalle is None or detalle.empty:
        return pd.DataFrame(columns=cols)
    detalle = solo_vendedores(detalle)
    if detalle.empty:
        return pd.DataFrame(columns=cols)
    r = (detalle.groupby(["vendedor_codigo", "vendedor_id", "vendedor_nombre", "titular"],
                         dropna=False)
                .agg(cartera_medida=("cliente_id", "nunique"),
                     cubiertos=("cumple", "sum")).reset_index())
    r["cubiertos"] = r["cubiertos"].astype(int)
    return r[cols].sort_values(["vendedor_codigo", "titular"]).reset_index(drop=True)


def marcas_cubiertas_por_vendedor(detalle) -> dict:
    """{vendedor_codigo: cantidad de titulares con al menos un cliente cubierto}.

    Alimenta el KPI "Marcas 11T" / "11T ✓". Cuenta TITULARES, no pares cliente-marca:
    antes sumaba `tiene_flag` (pares) bajo una etiqueta que se lee como marcas.

    Universo VENDEDORES: el Depósito no tiene KPI propio."""
    if detalle is None or detalle.empty:
        return {}
    detalle = solo_vendedores(detalle)
    if detalle.empty:
        return {}
    ok = detalle[detalle["cumple"]]
    if ok.empty:
        return {}
    return {int(k): int(v) for k, v in
            ok.groupby("vendedor_codigo")["titular"].nunique().items() if pd.notna(k)}


def periodo_trimestre_en_curso(hoy=None):
    """(desde, hasta) del trimestre calendario en curso. El 11T resetea en enero/abril/
    julio/octubre (regla vigente del negocio)."""
    hoy = hoy or datetime.now()
    ini = pd.Timestamp(hoy.year, ((hoy.month - 1) // 3) * 3 + 1, 1)
    fin = ini + pd.offsets.QuarterEnd(0)
    return ini.date(), fin.date()


def periodo_mes(anio, mes):
    """(desde, hasta) de un mes calendario. Usado por el cierre: un cierre de julio no
    puede incorporar ventas de agosto."""
    ini = pd.Timestamp(anio, mes, 1)
    return ini.date(), (ini + pd.offsets.MonthEnd(0)).date()
