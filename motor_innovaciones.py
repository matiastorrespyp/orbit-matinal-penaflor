# -*- coding: utf-8 -*-
"""Lector único de la lista de innovaciones (01_INPUTS/INNOVACIONES/Innovaciones.xlsx).

POR QUÉ EXISTE ESTO
-------------------
Había cuatro lectores del mismo Excel (pantalla Innovaciones, universos/días de stock,
acciones comerciales y cierre de mes), cada uno con su propio parseo. Cuando el negocio
cargó las altas de septiembre 2026 (El Último Tramo, Frizze Man-Go, Edmundo) con el código
en su propia celda en lugar de "código - nombre", los cuatro las ignoraron en silencio. El
del cierre, además, buscaba un formato viejo ("000000...") y no leía NINGUNA innovación.

FORMATOS ACEPTADOS (una innovación por fila, primera hoja)
----------------------------------------------------------
  - `74813 - DADA EXTRA BRUT 6X750`            (código y nombre en la misma celda)
  - `74901` | `EL ULTIMO TRAMO MALBEC 6X750`   (código en una celda, nombre en la siguiente)
Ceros a la izquierda y `.0` de Excel se toleran. La marca `x` en cualquier celda de la fila
es la columna "AASS c/plan": la innovación se sigue en Planes AS.
"""
import re
from pathlib import Path

import pandas as pd

_RE_COD_NOMBRE = re.compile(r"^0*(\d{4,6})\s*-\s*(.+)$")
_RE_COD_SOLO = re.compile(r"^0*(\d{4,6})(?:\.0)?$")


def _limpio(s):
    return re.sub(r"\s+", " ", str(s).replace("\xa0", " ")).strip()


def leer_innovaciones(path):
    """[{codigo:int, nombre:str, plan_as:bool}] en el orden del Excel, sin duplicados.
    [] si el archivo no existe. Los errores de lectura se propagan: cada consumidor decide
    su fallback (y lo loguea) como antes."""
    p = Path(path)
    if not p.exists():
        return []
    df = pd.read_excel(p, sheet_name=0, header=None, dtype=str)
    out, vistos = [], set()
    for _, fila in df.iterrows():
        celdas = [_limpio(v) for v in fila.tolist() if pd.notna(v) and _limpio(v)]
        plan_as = any(c.lower() == "x" for c in celdas)
        cod, nombre = None, ""
        for i, c in enumerate(celdas):
            m = _RE_COD_NOMBRE.match(c)
            if m:
                cod, nombre = int(m.group(1)), _limpio(m.group(2))
                break
            m = _RE_COD_SOLO.match(c)
            if m:
                cod = int(m.group(1))
                resto = [x for x in celdas[i + 1:] if x.lower() != "x"]
                nombre = resto[0] if resto else ""
                break
        if cod is None or cod in vistos:
            continue
        vistos.add(cod)
        out.append({"codigo": cod, "nombre": nombre, "plan_as": plan_as})
    return out
