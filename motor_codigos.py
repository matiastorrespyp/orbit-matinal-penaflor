# -*- coding: utf-8 -*-
"""Equivalencias de código de artículo: catálogo del proveedor -> código del ERP.

POR QUÉ EXISTE ESTO
-------------------
Peñaflor nos entrega el catálogo `Cluster 25` (`RAW_PRODUCTOS/productos<mes>.xlsx`) y de ahí
salen la matriz 11T, el maestro 04D y el mapeo de MPA. Pero **el proveedor y nuestro ERP no
siempre usan el mismo código para el mismo producto**. Cuando eso pasa, todo lo que se arma
con el código del catálogo mide contra un SKU que nuestras ventas y nuestro stock no conocen:
el producto aparece como "no figura en el archivo de stock" y su venta no le suma al titular.

No se ve como un error. Se ve como un producto sin stock — que es exactamente lo que pasó con
tres Antares que sí teníamos en depósito (caso testigo: Kolsch, Scotch y Caravana, 2026-08-24).

CÓMO SE RESUELVE
----------------
`09_CONFIG/codigos_equivalencias.csv` es un puente **revisado a mano**, igual que
`mpa_codigos.csv`. Cada fila afirma "el código X del catálogo es el código Y de nuestro ERP",
y sólo se agrega cuando se verificó que el código del catálogo **no tiene ni una línea de
venta ni una unidad de stock** y que el del ERP sí, para el mismo producto y presentación.

Deliberadamente NO se adivina por texto. Un `contains` sobre la descripción es lo que en su
momento metió GORDON'S GIN y GORDON'S TONIC dentro de Gordon's Flavours (ver CLAUDE.md).

QUÉ **NO** ES ESTO
------------------
Un código del catálogo sin stock ni ventas **no es automáticamente un código viejo**: puede
ser un producto que sencillamente no trabajamos. En la auditoría del 2026-08-24, de 9
huérfanos sólo 3 eran códigos equivocados; los otros 6 (Antares Honey y Playa Grande,
D.David Tannat, Trapiche Reserva Syrah y Merlot, Trapiche Dulce Cosecha Rosé) no tienen
ningún equivalente vivo: no los compramos. Ésos tienen que seguir mostrándose como "sin
existencia", porque es la verdad.
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
EQUIV_PATH = BASE / "09_CONFIG" / "codigos_equivalencias.csv"

_CACHE = {"mtime": None, "data": None}


def equivalencias(path=None) -> dict:
    """{codigo_catalogo: codigo_erp}. Cacheado por mtime.

    Sin archivo devuelve {} — o sea, todo queda como está. Nunca inventa una equivalencia."""
    p = Path(path) if path else EQUIV_PATH
    if not p.exists():
        return {}
    try:
        mt = p.stat().st_mtime
    except OSError:
        mt = 0
    if _CACHE["data"] is not None and _CACHE["mtime"] == mt:
        return dict(_CACHE["data"])

    out = {}
    try:
        d = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        viejo = pd.to_numeric(d.get("codigo_catalogo"), errors="coerce")
        nuevo = pd.to_numeric(d.get("codigo_erp"), errors="coerce")
        for a, b in zip(viejo, nuevo):
            if pd.isna(a) or pd.isna(b) or int(a) == int(b):
                continue
            out[int(a)] = int(b)
    except Exception as e:
        print(f"[AVISO] codigos_equivalencias.csv: {e}")
        return {}

    _CACHE.update({"mtime": mt, "data": dict(out)})
    return out


def canonizar(codigo, path=None):
    """Código del ERP para un código del catálogo. Si no hay equivalencia, lo devuelve igual."""
    try:
        c = int(codigo)
    except (TypeError, ValueError):
        return codigo
    return equivalencias(path).get(c, c)


def canonizar_serie(serie, path=None) -> pd.Series:
    """Versión vectorizada de `canonizar` para una columna de códigos."""
    eq = equivalencias(path)
    if not eq:
        return serie
    return serie.map(lambda c: eq.get(c, c))
