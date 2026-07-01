#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validador de consistencia para el Cierre del Dia.

Frena el cierre (exit 1) cuando resultado.xlsx y ventas.csv estan
desincronizados a nivel vendedor. El caso tipico: un vendedor figura con
Acumulado > 0 en resultado.xlsx (hoja Avance) pero NO tiene ninguna linea
de venta en ventas.csv del mes. Eso es matematicamente imposible (no hay
venta NETA sin ninguna linea BRUTA) y produce en el portal la contradiccion
"tiene ventas pero ningun cliente con compra" (avance disparado, ej. 368%).

Regla comercial Penaflor:
- Se validan solo los vendedores con objetivo (los que estan en la hoja
  Avance de resultado.xlsx). V2, V5 y V20 no tienen objetivo y no aparecen
  ahi, asi que quedan fuera de forma natural.
- Fecha de facturacion = FechaComprobante (nunca FechaEntrega/FechaCarga).

Uso:  python validar_consistencia_cierre.py
Salida: 0 = consistente / 1 = inconsistente (frena el cierre)
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RESULTADO = BASE / "01_INPUTS" / "resultado.xlsx"
VENTAS = BASE / "01_INPUTS" / "ventas.csv"

# Un vendedor con acumulado por encima de esto pero sin ninguna linea de
# venta se considera desincronizado. Umbral en $ para tolerar ruido de floats.
UMBRAL_ACUM = 1.0


def _leer_ventas() -> pd.DataFrame:
    if not VENTAS.exists():
        print(f"ERROR: no existe {VENTAS}")
        sys.exit(1)
    df = pd.read_csv(VENTAS, sep=";", encoding="latin1")
    df.columns = [c.lstrip("﻿").strip() for c in df.columns]
    return df


def _leer_avance() -> pd.DataFrame:
    if not RESULTADO.exists():
        print(f"ERROR: no existe {RESULTADO}")
        sys.exit(1)
    return pd.read_excel(RESULTADO, sheet_name="Avance")


def _cod(x) -> str:
    """Normaliza un codigo de vendedor a solo digitos ('V9' -> '9')."""
    s = str(x).strip().upper()
    return "".join(ch for ch in s if ch.isdigit())


def main() -> int:
    print("Validando consistencia resultado.xlsx <-> ventas.csv...")

    ventas = _leer_ventas()
    avance = _leer_avance()

    # Lineas de venta por vendedor en ventas.csv (mes vivo).
    ventas["_cod"] = ventas["CodVendedor"].map(_cod)
    lineas_por_vend = ventas.groupby("_cod").size().to_dict()

    inconsistencias = []
    for _, row in avance.iterrows():
        cod = _cod(row.get("VendedorCodigo", ""))
        if not cod:
            continue
        try:
            acum = float(row.get("Acumulado", 0) or 0)
        except (TypeError, ValueError):
            acum = 0.0
        nombre = str(row.get("VendedorNombre", "")).strip()
        n_lineas = int(lineas_por_vend.get(cod, 0))

        if acum > UMBRAL_ACUM and n_lineas == 0:
            inconsistencias.append((cod, nombre, acum))

    if inconsistencias:
        print()
        print("============================================================")
        print("ERROR: resultado.xlsx y ventas.csv NO coinciden.")
        print("Estos vendedores tienen Acumulado > 0 pero 0 lineas en ventas.csv:")
        print()
        for cod, nombre, acum in inconsistencias:
            print(f"  V{cod:<3} {nombre:<28} Acumulado ${acum:,.2f}  |  0 lineas en ventas.csv")
        print()
        print("Es imposible tener venta neta sin ninguna linea de detalle.")
        print("Uno de los dos exports quedo viejo. Re-exporta resultado.xlsx")
        print("y ventas.csv del MISMO corte del ERP y reintenta el cierre.")
        print("============================================================")
        return 1

    print("OK: resultado.xlsx y ventas.csv son consistentes por vendedor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
