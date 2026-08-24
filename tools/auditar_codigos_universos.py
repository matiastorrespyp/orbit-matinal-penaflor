# -*- coding: utf-8 -*-
"""Audita los codigos de los 3 universos de producto contra stock y ventas reales.

    python tools/auditar_codigos_universos.py

POR QUE EXISTE
--------------
La matriz 11T, mpa_codigos.csv y el maestro 04D se arman con el catalogo del proveedor
(RAW_PRODUCTOS, hoja "Cluster 25"), y el proveedor no siempre usa el mismo codigo que
nuestro ERP para el mismo producto. Cuando no coincide, el universo mide contra un SKU
que nuestras ventas y nuestro stock no conocen: el producto figura como "no esta en el
archivo de stock" y su venta no le suma al titular.

No se ve como un error. Se ve como un producto sin stock. Por eso hay que buscarlo a
proposito. Caso testigo 2026-08-24: Antares Kolsch, Scotch y Caravana, con 150, 102 y 96
unidades en deposito, figuraban en cero (ver 00_OBSIDIAN_ORBIT/BITACORA_2026-08-24b.md).

COMO SE LEE LA SALIDA
---------------------
Un codigo sin stock ni ventas NO es automaticamente un codigo viejo: puede ser un producto
que sencillamente no trabajamos. Por eso hay dos bloques separados:

  (2) REEMPLAZO PROBABLE     -> hay un producto vivo con el mismo nombre y presentacion
                                bajo otro codigo. Esto SI es un codigo a corregir: se
                                agrega la fila en 09_CONFIG/codigos_equivalencias.csv
                                DESPUES de verificarlo a mano.
  (3) SIN REEMPLAZO          -> no hay equivalente vivo. Lo mas probable es que no lo
                                trabajemos. Tiene que seguir mostrandose como "sin
                                existencia", porque es la verdad.

Nunca se corrige automaticamente: la sugerencia es por similitud de texto, y adivinar por
texto es lo que metio GORDON'S GIN y TONIC dentro de Gordon's Flavours (ver CLAUDE.md).
El script sugiere; la fila la agrega una persona.
"""
import re
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import motor_11t          # noqa: E402
import server_orbit as S  # noqa: E402

INPUTS = S.INPUTS
FUERA = {"LATA", "BOTELLA", "X", "DE", "LA", "EL", "GRS", "GR", "L", "ML", "CC"}


def _norm(t):
    """Normaliza una descripcion para comparar entre fuentes: saca el codigo entre
    parentesis (el catalogo lo pega al nombre), la unidad y la puntuacion."""
    t = str(t).upper()
    t = re.sub(r"\(\s*\d{4,6}\s*\)", " ", t)
    t = re.sub(r"\bNEW\b", " ", t)
    t = t.replace("ML", " ").replace("CC", " ")
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", t).split())


def _tokens(t):
    """Palabras significativas: sin formato (6X473), sin numeros sueltos, sin ruido."""
    out = set()
    for w in _norm(t).split():
        if re.fullmatch(r"\d+", w) or re.fullmatch(r"\d+X\d+", w) or w in FUERA:
            continue
        out.add(w)
    return out


def universos():
    """{nombre: {codigo: descripcion}} de los 3 universos de la pantalla Stock."""
    u = {}
    m = motor_11t.cargar_matriz_11t()
    u["11T"] = {int(r.codigo_articulo): str(r.descripcion) for r in m.itertuples()}
    u["Innovaciones"] = {int(p["codigo"]): p["nombre"]
                         for p in S._innovaciones_codigos_todas()}
    cod2nom, _ = S._mpa_universo()
    u["MPA"] = {int(c): n for c, n in cod2nom.items()}
    return u


def stock_real():
    """{codigo: {desc, PyP, VSB}} sumando los dos depositos."""
    out = {}
    for cfg in S._STOCK_BLOQUES:
        d = pd.read_excel(INPUTS / "Stock" / cfg["archivo"], sheet_name="Principal")
        for _, r in d.iterrows():
            c = int(r["Codigo"])
            e = out.setdefault(c, {"desc": str(r["Descripcion"]), "PyP": 0.0, "VSB": 0.0})
            e[cfg["label"]] = e.get(cfg["label"], 0.0) + float(r["UniTotalDisponible"] or 0)
    return out


def ventas_reales():
    """{codigo: {desc, unidades}} de ventas_acumulada.csv (la ventana mas ancha)."""
    v = pd.read_csv(INPUTS / "ventas_acumulada.csv", sep=";", encoding="latin1",
                    low_memory=False, usecols=["Codigo", "Articulo", "CantBase"])
    v["cod"] = pd.to_numeric(v["Codigo"], errors="coerce")
    g = v.dropna(subset=["cod"]).groupby("cod").agg(desc=("Articulo", "first"),
                                                    und=("CantBase", "sum"))
    return {int(c): {"desc": str(r["desc"]), "und": float(r["und"])} for c, r in g.iterrows()}


def main():
    uni, stock, ventas = universos(), stock_real(), ventas_reales()
    vivos = {c: e["desc"] for c, e in stock.items()}
    for c, r in ventas.items():
        vivos.setdefault(c, r["desc"])

    huerfanos = [(u, c, d) for u, mapa in uni.items() for c, d in sorted(mapa.items())
                 if c not in stock and c not in ventas]

    print("=" * 100)
    print("1) CODIGOS DEL UNIVERSO QUE NO FIGURAN NI EN STOCK NI EN VENTAS")
    print("=" * 100)
    for u, c, d in huerfanos:
        print(f"{u:14} {c:>7}  {d}")
    print(f"\nTOTAL: {len(huerfanos)}")

    print()
    print("=" * 100)
    print("2) REEMPLAZO PROBABLE  -> revisar y, si se confirma, agregar la fila en")
    print("   09_CONFIG/codigos_equivalencias.csv")
    print("=" * 100)
    sugeridos = set()
    for u, c, d in huerfanos:
        t = _tokens(d)
        if not t:
            continue
        mejor = None
        for c2, d2 in vivos.items():
            if c2 in uni[u]:
                continue
            t2 = _tokens(d2)
            if not t2:
                continue
            inter = len(t & t2)
            jac = inter / len(t | t2)
            if inter >= 2 and jac >= 0.6:
                st = stock.get(c2, {})
                und = ventas.get(c2, {}).get("und", 0.0)
                peso = (jac, st.get("PyP", 0) + st.get("VSB", 0) + und)
                if mejor is None or peso > mejor[0]:
                    mejor = (peso, c2, d2, st, und)
        if mejor:
            _, c2, d2, st, und = mejor
            sugeridos.add((u, c))
            tot = st.get("PyP", 0) + st.get("VSB", 0)
            print(f"{u:12} {c:>6} {d[:40]:40} -> {c2:>6} {d2[:36]:36} "
                  f"stock {tot:>6.0f}  vendido {und:>7.0f}")
    print(f"\nTOTAL: {len(sugeridos)}")
    if not sugeridos:
        print("(ninguno: no hay codigos del universo con un gemelo vivo)")

    print()
    print("=" * 100)
    print("3) SIN REEMPLAZO EVIDENTE  -> probablemente productos que no trabajamos.")
    print("   Tienen que seguir figurando como 'sin existencia': es la verdad.")
    print("=" * 100)
    for u, c, d in huerfanos:
        if (u, c) not in sugeridos:
            print(f"{u:14} {c:>7}  {d}")

    print()
    print("=" * 100)
    print("4) RESUMEN")
    print("=" * 100)
    print(f'{"Universo":14} {"codigos":>8} {"en stock":>9} {"en ventas":>10} {"huerfanos":>10}')
    for u, mapa in uni.items():
        cs = set(mapa)
        print(f"{u:14} {len(cs):>8} {len(cs & set(stock)):>9} {len(cs & set(ventas)):>10} "
              f"{sum(1 for h in huerfanos if h[0] == u):>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
