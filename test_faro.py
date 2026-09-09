# -*- coding: utf-8 -*-
"""Pruebas del Incentivo Club FARO.

Todo se prueba con hojas y ventas SINTÉTICAS: la definición del incentivo cambia cada bimestre
y `ventas_acumulada.csv` solo tiene el bimestre vivo, así que los casos de mayo-junio (que ya no
existen en los datos) no se pueden armar de otra forma. Los sintéticos son CASOS, no datos que se
publiquen en ningún lado: ningún archivo real se lee ni se escribe.

Dos escenarios:
  - septiembre-octubre: la campaña VIGENTE. Blinda lo ya validado (V9 Frizze 4 coberturas /
    4 clientes, exclusiones de Smirnoff BC / 21 / lata).
  - mayo-junio: escenario HISTÓRICO de regresión. Es la hoja que no declara el período en el
    título, la que une dos marcas en una categoría ("alaris + finca las moras") y la que pondera
    doble algunos SKUs de Antares.

Ejecutar:  python test_faro.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

import server_orbit as S

OK, FALLOS = 0, []


def chk(nombre, cond, detalle=""):
    global OK
    if cond:
        OK += 1
        print(f"  [OK]    {nombre}" + (f"  ({detalle})" if detalle else ""))
    else:
        FALLOS.append(nombre)
        print(f"  [FALLA] {nombre}  ({detalle})")


# ─────────────────────────── armado del escenario sintético ───────────────────────────
VENTAS_COLS = ["FechaComprobante", "Cliente", "RazonSocial", "Localidad", "CodVendedor",
               "Ramo", "Subramo", "Codigo", "Articulo", "CantBase", "ImporteNetoItem"]


def venta(fecha, cli, vend, ramo, sub, cod, art, cant, neto=1000.0):
    return {"FechaComprobante": fecha, "Cliente": cli, "RazonSocial": f"PDV {cli}",
            "Localidad": "PENAFLOR", "CodVendedor": vend, "Ramo": ramo, "Subramo": sub,
            "Codigo": cod, "Articulo": art, "CantBase": cant, "ImporteNetoItem": neto}


def escribir_escenario(dirp, filas_hoja, ventas):
    """Deja incentivo_club_faro.xlsx + ventas_acumulada.csv sintéticos en `dirp` y apunta ahí
    el módulo (S.INPUTS), limpiando las cachés por mtime."""
    dirp = Path(dirp)
    ancho = max(len(f) for f in filas_hoja)
    hoja = pd.DataFrame([list(f) + [None] * (ancho - len(f)) for f in filas_hoja])
    hoja.to_excel(dirp / "incentivo_club_faro.xlsx", header=False, index=False)
    pd.DataFrame(ventas, columns=VENTAS_COLS).to_csv(
        dirp / "ventas_acumulada.csv", sep=";", index=False, encoding="latin1")
    S.INPUTS = dirp
    S._FARO_CFG_CACHE.clear()
    S._FARO_VENTAS_CACHE.clear()


# ───────────────────────────────── hojas de los bimestres ─────────────────────────────────
# Copia fiel de la hoja vigente (01_INPUTS/incentivo_club_faro .xlsx).
HOJA_SEP_OCT = [
    ["incentivo Club FARO (septiembre-octubre)"],
    ["", "kiosco + almacén", "Autoservicios", ""],
    ["vendedores", "Familia Smirnoff", "Blancos Dulces", "familia frizze"],
    ["3", "86", "0", "0"],
    ["4", "40", "31", "15"],
    ["6", "40", "31", "15"],
    ["7", "40", "31", "15"],
    ["8", "36", "31", "16"],
    ["9", "40", "31", "15"],
    ["10", "40", "31", "15"],
    ["supervisor"],
    ["Esteban", "242", "124", "61"],
    ["Raul", "76", "62", "30"],
    ["Regla"],
    ["en el periodo de septiembre - octubre el cliente debe comprar al menos una vez la cantidad "
     "mínima de botellas para cobertura (3 en kiosco+almacén y 6 en autoservicio)"],
    [""],
    ["Familia frizze: Cada PDV contabiliza 1 CCC por la compra en autoservicio de productos frizze "
     "(14620, 14621, 14583, 14619 y 14594), por cada pdv suma solo 1 cobertura por más que compre "
     "todas las variedades."],
    ["Vinos Blancos dulces: Cada SKU suma 1 CCC (74188, 74840, 74509, 74882, 74816, 42113, 74827, "
     "74397 y 74886) en autoservicio con mínimo 6 botellas."],
    ["Familia Smirnoff: En kioskos y tradicionales, suma 1 CCC por cualquier SKU participante (no "
     "entran BC y 21), no puede acumular un cliente más de una cobertura por más que haya comprado "
     "toda la variedad. Es solo en botella."],
    ["Supervisores: Esteban acumula las coberturas de los vendedores (3, 4, 6, 8 y 10) y Raúl de "
     "los vendedores (7 y 9)"],
    [""],
    ["PREMIOS: 1) FAMILIA Frizze (1000 MILLAS), Blancos Dulces (1000 MILLAS) Y familia smirnoff "
     "(2000 MILLAS)"],
]

# Hoja del bimestre mayo-junio. El título NO dice el período (solo lo dice la regla): es
# justamente el caso que antes se leía como "el bimestre de hoy". La regla de Smirnoff escribe la
# presentación con el vocabulario que la hoja ya usa ("solo en botella … cc", "no entra …").
HOJA_MAY_JUN = [
    ["incentivo Club FARO"],
    ["", "kiosco + almacén", "Autoservicios", ""],
    ["vendedores", "alaris + finca las moras", "Antares", "familia smirnoff"],
    ["3", "100", "0", "0"],
    ["4", "85", "8", "26"],
    ["6", "86", "8", "21"],
    ["7", "86", "7", "21"],
    ["8", "65", "10", "25"],
    ["9", "86", "9", "21"],
    ["10", "86", "7", "18"],
    ["supervisor"],
    ["Esteban", "422", "33", "90"],
    ["Raul", "172", "16", "42"],
    ["Regla"],
    ["en el periodo de mayo y junio el cliente debe comprar al menos una vez la cantidad mínima de "
     "botellas para cobertura (3 en kiosco+almacén y 6 en autoservicio)"],
    [""],
    ["Familia Smirnoff: Cada PDV contabiliza 1 CCC por la compra de productos Smirnoff (Vodka N°21, "
     "Flavors, Bitter Citric), sin importar si adquiere uno, dos o los tres SKUs. Es solo en botella "
     "700 cc, no entra Ice."],
    ["Antares: Cada SKU suma 1 CCC, pero XPA y Lager botella suman doble."],
    ["Alaris + FLM: En kioskos y tradicionales, cada operación suma 1 CCC por cualquier SKU "
     "participante, sin acumular más de uno por compra."],
    ["Supervisores: Esteban acumula las coberturas de los vendedores (3, 4, 6, 8 y 10) y Raúl de "
     "los vendedores (7 y 9)"],
]

# Hoja rota a propósito: ni el título ni la regla nombran un mes.
HOJA_SIN_PERIODO = [
    ["incentivo Club FARO"],
    ["", "kiosco + almacén", "", ""],
    ["vendedores", "Familia Smirnoff"],
    ["3", "10"],
    ["4", "10"],
    ["Regla"],
    ["el cliente debe comprar al menos una vez la cantidad mínima de botellas para cobertura"],
]

KIO = ("TRADITIONAL TRADE", "KIOSCO")
ALM = ("TRADITIONAL TRADE", "ALMACEN")
DES = ("TRADITIONAL TRADE", "DESPENSA")
AUT = ("AUTOSERVICIO", "AUTOSERVICIO")

# ── Ventas septiembre-octubre ────────────────────────────────────────────────────────────
# V9 Frizze: cuatro PDV de autoservicio con ≥6 botellas → 4 coberturas / 4 clientes (el 201
# compra dos variedades y aun así suma 1: es el tope que la hoja declara).
VENTAS_SEP_OCT = [
    venta("15/09/2026", 201, 9, *AUT, "14620", "FRIZZE MANXANA POP 6X1000", 6),
    venta("15/09/2026", 201, 9, *AUT, "14619", "FRIZZE BUBBLE MOOD 6X1000", 6),
    venta("15/09/2026", 202, 9, *AUT, "14620", "FRIZZE MANXANA POP 6X1000", 6),
    venta("16/09/2026", 203, 9, *AUT, "14583", "FRIZZE EVOL BLUE NEW X1000", 8),
    venta("17/09/2026", 204, 9, *AUT, "14594", "FRIZZE BLUE LATA X473", 6),
    venta("17/09/2026", 205, 9, *AUT, "14620", "FRIZZE MANXANA POP 6X1000", 5),   # no llega al mínimo
    # Smirnoff tradicional: tope 1 por cliente aunque califiquen dos SKUs.
    venta("15/09/2026", 101, 9, *KIO, "30131", "SMIRNOFF TROPICAL FRUITS 6X700", 3),
    venta("15/09/2026", 101, 9, *KIO, "30065", "SMIRNOFF WATERMELON 6X700", 3),
    # Smirnoff excluidos por la hoja: BC, 21 y lata.
    venta("15/09/2026", 102, 9, *ALM, "35101", "SMIRNOFF BC ORANGE & LIME 6X700", 6),
    venta("15/09/2026", 102, 9, *ALM, "30019", "SMIRNOFF 21 DO 12X700", 6),
    venta("15/09/2026", 102, 9, *ALM, "35103", "SMIRNOFF ICE LATA 4X6X473", 12),
    # Blancos dulces en autoservicio: sin tope, cada SKU suma.
    venta("15/09/2026", 301, 8, *AUT, "74188", "TRAPICHE ALARIS DULCE COSECHA 6X750", 6),
    venta("15/09/2026", 301, 8, *AUT, "74840", "ALARIS D.COSECHA TINTO 6X750", 6),
    # Fuera del período (julio) → no se cuenta.
    venta("15/07/2026", 206, 9, *AUT, "14620", "FRIZZE MANXANA POP 6X1000", 12),
    # V2 y V5 nunca entran.
    venta("15/09/2026", 900, 2, *KIO, "30131", "SMIRNOFF TROPICAL FRUITS 6X700", 12),
    venta("15/09/2026", 901, 5, *AUT, "14620", "FRIZZE MANXANA POP 6X1000", 12),
    # V3 trabaja tradicional; su compra de autoservicio no debe generarle categoría de AS.
    venta("15/09/2026", 110, 3, *KIO, "30131", "SMIRNOFF TROPICAL FRUITS 6X700", 3),
]

# ── Ventas mayo-junio ────────────────────────────────────────────────────────────────────
# V4 Antares = 6 coberturas / 2 clientes: 401 (XPA 2 + Lager 660 2) y 402 (Lager 330 2).
VENTAS_MAY_JUN = [
    venta("15/05/2026", 401, 4, *AUT, "60020", "ANTARES XPA LATA  6X473", 6),
    venta("15/05/2026", 401, 4, *AUT, "60022", "ANTARES LAGER BOTELLA 6X660", 6),
    venta("16/05/2026", 402, 4, *AUT, "60021", "ANTARES LAGER PORRON 6X330", 6),
    venta("16/05/2026", 404, 4, *AUT, "60020", "ANTARES XPA LATA  6X473", 5),      # no llega al mínimo
    # V6: las demás Antares ponderan 1. El PDV 402 también le compra a V6 (mismo cliente,
    # dos carteras) → el supervisor no puede contarlo dos veces.
    venta("15/06/2026", 403, 6, *AUT, "60018", "ANTARES LAGER LATA 6X473", 6),
    venta("15/06/2026", 403, 6, *AUT, "60017", "ANTARES IPA LATA 6X473 (NEW)", 6),
    venta("15/06/2026", 402, 6, *AUT, "60020", "ANTARES XPA LATA  6X473", 6),
    # Alaris + Finca Las Moras: unión de las dos marcas, en Almacén, Despensa y Kiosco.
    venta("15/05/2026", 501, 4, *ALM, "71704", "TRAPICHE ALARIS MALBEC 6X750", 3),
    venta("15/05/2026", 502, 4, *DES, "72859", "F.LAS MORAS MALBEC 6X750", 3),
    venta("15/05/2026", 503, 4, *KIO, "74509", "F. LAS MORAS BCO DULCE 6X750", 3),
    venta("15/05/2026", 503, 4, *KIO, "74058", "TRAPICHE ALARIS SYRAH 6X750", 3),
    # Smirnoff mayo-junio: el 21 SÍ entra (a diferencia de sept-oct) y el tope es 1 por PDV.
    venta("15/05/2026", 601, 4, *AUT, "30019", "SMIRNOFF 21 DO 12X700", 6),
    venta("15/05/2026", 601, 4, *AUT, "30131", "SMIRNOFF TROPICAL FRUITS 6X700", 6),
    venta("15/05/2026", 602, 4, *AUT, "35103", "SMIRNOFF ICE LATA 4X6X473", 12),   # Ice: fuera
    # Fuera del período (julio) → no se cuenta.
    venta("15/07/2026", 405, 4, *AUT, "60020", "ANTARES XPA LATA  6X473", 12),
    # V2 y V5 nunca entran.
    venta("15/05/2026", 902, 2, *AUT, "60020", "ANTARES XPA LATA  6X473", 12),
    venta("15/05/2026", 903, 5, *ALM, "71704", "TRAPICHE ALARIS MALBEC 6X750", 12),
]


def det(cfg, cod):
    return S._faro_detalle_vendedor(S._faro_ventas(cfg), cod, cfg)


# ───────────────────────────────────── septiembre-octubre ─────────────────────────────────────
def test_sep_oct(tmp):
    print("\n[septiembre-octubre — campaña vigente]")
    escribir_escenario(tmp, HOJA_SEP_OCT, VENTAS_SEP_OCT)
    cfg = S._faro_config()
    chk("período leído del título", cfg["meses"] == (9, 10), f"meses={cfg['meses']}")
    chk("período sin error", cfg.get("periodo_error") is None, cfg["periodo"])
    chk("categorías de la hoja",
        cfg["cats"] == ["familia_smirnoff", "blancos_dulces", "familia_frizze"], str(cfg["cats"]))
    chk("umbral por canal", cfg["cat_umbral"] == {"familia_smirnoff": 3, "blancos_dulces": 6,
                                                  "familia_frizze": 6}, str(cfg["cat_umbral"]))
    chk("tope de Frizze y Smirnoff = 1, Blancos Dulces sin tope",
        cfg["cat_cap"] == {"familia_smirnoff": 1, "blancos_dulces": None, "familia_frizze": 1},
        str(cfg["cat_cap"]))
    chk("exclusiones de Smirnoff BC / 21 / lata",
        cfg["cat_excl"]["familia_smirnoff"] == {"bc", "21", "lata"},
        str(cfg["cat_excl"]["familia_smirnoff"]))

    d9 = det(cfg, 9)
    chk("V9 Frizze = 4 coberturas",
        d9["familia_frizze"]["logrado"] == 4, str(d9["familia_frizze"]["logrado"]))
    chk("V9 Frizze = 4 clientes",
        d9["familia_frizze"]["clientes_cubiertos"] == 4,
        str(d9["familia_frizze"]["clientes_cubiertos"]))
    chk("Smirnoff topea en 1 cobertura por cliente",
        d9["familia_smirnoff"]["logrado"] == 1 and d9["familia_smirnoff"]["clientes_cubiertos"] == 1,
        f"logrado={d9['familia_smirnoff']['logrado']}")
    chk("el PDV que solo compra BC / 21 / lata no cubre",
        102 not in d9["familia_smirnoff"]["clientes_ids"],
        str(d9["familia_smirnoff"]["clientes_ids"]))
    d8 = det(cfg, 8)
    chk("Blancos Dulces sin tope: 2 SKUs = 2 coberturas en 1 cliente",
        (d8["blancos_dulces"]["logrado"], d8["blancos_dulces"]["clientes_cubiertos"]) == (2, 1),
        str((d8["blancos_dulces"]["logrado"], d8["blancos_dulces"]["clientes_cubiertos"])))

    df = S._faro_ventas(cfg)
    chk("V2 y V5 fuera de las ventas FARO", df["_vend"].isin([2, 5]).sum() == 0)
    chk("solo meses del período", set(df["_fecha"].dt.month.unique()) <= {9, 10},
        str(sorted(df["_fecha"].dt.month.unique())))
    chk("todas las coberturas ponderan 1 (la hoja no dice 'doble')",
        set(df["_peso"].unique()) == {1}, str(sorted(df["_peso"].unique())))


# ───────────────────────────────────── mayo-junio (regresión) ─────────────────────────────────
def test_may_jun(tmp):
    print("\n[mayo-junio — regresión histórica]")
    escribir_escenario(tmp, HOJA_MAY_JUN, VENTAS_MAY_JUN)
    cfg = S._faro_config()
    chk("período leído de la regla aunque el título no lo diga",
        cfg["meses"] == (5, 6), f"meses={cfg['meses']} periodo={cfg['periodo']}")
    chk("NO cae al bimestre en curso", cfg["periodo"] == "mayo-junio", cfg["periodo"])
    chk("categorías de la hoja",
        cfg["cats"] == ["alaris_finca_las_moras", "antares", "familia_smirnoff"], str(cfg["cats"]))

    df = S._faro_ventas(cfg)
    chk("V2 y V5 fuera de las ventas FARO", df["_vend"].isin([2, 5]).sum() == 0)
    chk("solo meses del período", set(df["_fecha"].dt.month.unique()) <= {5, 6},
        str(sorted(df["_fecha"].dt.month.unique())))

    # ── Antares: ponderación doble ──
    d4 = det(cfg, 4)
    ant4 = d4["antares"]
    chk("CONTROL V4 Antares = 6 coberturas", ant4["logrado"] == 6, str(ant4["logrado"]))
    chk("CONTROL V4 Antares = 2 clientes únicos",
        ant4["clientes_cubiertos"] == 2, str(ant4["clientes_ids"]))
    d6 = det(cfg, 6)
    chk("las demás Antares ponderan 1 (lata Lager + lata IPA = 2 en el PDV 403)",
        any(c["cliente"] == 403 and c["peso"] == 2 for c in d6["antares"]["compradores"]),
        str([(c["cliente"], c["peso"]) for c in d6["antares"]["compradores"]]))
    pes = df[df["_cat"] == "antares"].groupby("_art")["_peso"].max().to_dict()
    chk("XPA pondera doble", pes.get("ANTARES XPA LATA  6X473") == 2, str(pes))
    chk("Lager 660 pondera doble", pes.get("ANTARES LAGER BOTELLA 6X660") == 2)
    chk("Lager 330 pondera doble", pes.get("ANTARES LAGER PORRON 6X330") == 2)
    chk("Lager lata NO pondera doble", pes.get("ANTARES LAGER LATA 6X473") == 1)
    chk("IPA lata NO pondera doble", pes.get("ANTARES IPA LATA 6X473 (NEW)") == 1)

    # ── Alaris + Finca Las Moras: unión de marcas ──
    alm = d4["alaris_finca_las_moras"]
    chk("Alaris + FLM = unión de ambas marcas (4 coberturas, 3 clientes)",
        (alm["logrado"], alm["clientes_cubiertos"]) == (4, 3),
        str((alm["logrado"], alm["clientes_cubiertos"])))
    chk("no exige que las dos marcas estén en el mismo artículo",
        set(alm["clientes_ids"]) == {501, 502, 503}, str(alm["clientes_ids"]))
    arts = set(df[df["_cat"] == "alaris_finca_las_moras"]["_art"])
    chk("Alaris solo entra como Alaris", "TRAPICHE ALARIS MALBEC 6X750" in arts)
    chk("F. LAS MORAS entra pese a la abreviatura del ERP",
        "F.LAS MORAS MALBEC 6X750" in arts, str(sorted(arts)))
    chk("aplica en Almacén, Despensa y Kiosco",
        set(df[df["_cat"] == "alaris_finca_las_moras"]["_seg"]) == {"TRADICIONAL"})
    chk("mínimo 3 en canal tradicional", cfg["cat_umbral"]["alaris_finca_las_moras"] == 3,
        str(cfg["cat_umbral"]["alaris_finca_las_moras"]))

    # ── Smirnoff: 700 cc, sin Ice, tope 1 por cliente ──
    smi = d4["familia_smirnoff"]
    chk("Smirnoff topea 1 cobertura por cliente (no 1 por SKU)",
        (smi["logrado"], smi["clientes_cubiertos"]) == (1, 1),
        str((smi["logrado"], smi["clientes_cubiertos"])))
    sarts = set(df[df["_cat"] == "familia_smirnoff"]["_art"])
    chk("Smirnoff Ice queda afuera", "SMIRNOFF ICE LATA 4X6X473" not in sarts, str(sorted(sarts)))
    chk("solo entra la presentación 700 cc",
        all("700" in a for a in sarts), str(sorted(sarts)))
    chk("en mayo-junio el 21 SÍ participa", "SMIRNOFF 21 DO 12X700" in sarts)


# ─────────────────────────────── período indeterminable ───────────────────────────────
def test_periodo_indeterminable(tmp):
    print("\n[hoja sin período — diagnóstico explícito]")
    escribir_escenario(tmp, HOJA_SIN_PERIODO, VENTAS_SEP_OCT)
    cfg = S._faro_config()
    chk("no inventa el bimestre en curso", cfg["meses"] == (), str(cfg["meses"]))
    chk("deja un diagnóstico explícito", bool(cfg.get("periodo_error")),
        (cfg.get("periodo_error") or "")[:60])
    cli = S.app.test_client()
    jg = cli.get("/api/gerencia/incentivo_faro").get_json()
    chk("gerencia informa el problema y no publica números",
        bool(jg.get("error")) and jg.get("vendedores") == [], str(jg.get("error"))[:50])
    jv = cli.get("/api/vendedor/V9/incentivo_faro").get_json()
    chk("vendedor informa el problema y no publica números",
        bool(jv.get("error")) and jv.get("categorias") == [], str(jv.get("error"))[:50])


# ───────────────────────────────────── endpoints ─────────────────────────────────────
ROSTER = [3, 4, 6, 7, 8, 9, 10]


def test_endpoints(tmp):
    print("\n[endpoints gerencia y vendedor — septiembre-octubre]")
    escribir_escenario(tmp, HOJA_SEP_OCT, VENTAS_SEP_OCT)
    cli = S.app.test_client()

    r = cli.get("/api/gerencia/incentivo_faro")
    chk("gerencia responde 200", r.status_code == 200, str(r.status_code))
    j = r.get_json()
    chk("gerencia sin error", not j.get("error"), str(j.get("error"))[:60])
    cods = [v["codigo"] for v in j["vendedores"]]
    chk("roster exacto V3 V4 V6 V7 V8 V9 V10", cods == ROSTER, str(cods))
    chk("V2 y V5 ausentes de gerencia", not ({2, 5} & set(cods)), str(cods))
    chk("gerencia informa septiembre-octubre", j["periodo"] == "septiembre-octubre", j["periodo"])
    chk("categorias_meta expone el tope dinámico",
        j["categorias_meta"]["familia_frizze"]["tope"] == 1
        and j["categorias_meta"]["blancos_dulces"]["tope"] is None,
        str({c: m["tope"] for c, m in j["categorias_meta"].items()}))

    v9 = next(v for v in j["vendedores"] if v["codigo"] == 9)
    chk("gerencia: V9 Frizze 4 coberturas / 4 clientes",
        (v9["familia_frizze"]["logrado"], v9["familia_frizze"]["clientes_cubiertos"]) == (4, 4),
        str((v9["familia_frizze"]["logrado"], v9["familia_frizze"]["clientes_cubiertos"])))

    sups = {s["nombre"]: s for s in j["supervisores"]}
    chk("supervisores de la hoja", set(sups) == {"Esteban", "Raul"}, str(sorted(sups)))
    raul = sups["Raul"]
    chk("supervisor suma coberturas de su equipo",
        raul["familia_frizze"]["logrado"]
        == sum(v["familia_frizze"]["logrado"] for v in j["vendedores"] if v["codigo"] in (7, 9)),
        str(raul["familia_frizze"]["logrado"]))
    chk("supervisor AGREGA clientes_cubiertos (no queda en 0 habiendo coberturas)",
        raul["familia_frizze"]["clientes_cubiertos"] == 4,
        str(raul["familia_frizze"]["clientes_cubiertos"]))
    chk("clientes del supervisor reconcilian con sus vendedores",
        all(s[c]["clientes_cubiertos"] > 0 or s[c]["logrado"] == 0
            for s in j["supervisores"] for c in j["categorias_orden"]),
        str({s["nombre"]: {c: (s[c]["logrado"], s[c]["clientes_cubiertos"])
                           for c in j["categorias_orden"]} for s in j["supervisores"]}))

    r9 = cli.get("/api/vendedor/V9/incentivo_faro")
    chk("vendedor responde 200", r9.status_code == 200, str(r9.status_code))
    jv = r9.get_json()
    chk("vendedor sin error", not jv.get("error"), str(jv.get("error"))[:60])
    chk("vendedor informa septiembre-octubre", jv["periodo"] == "septiembre-octubre", jv["periodo"])
    cf = next(c for c in jv["categorias"] if c["cat"] == "familia_frizze")
    chk("vendedor: V9 Frizze 4 coberturas / 4 clientes",
        (cf["logrado"], cf["clientes_cubiertos"]) == (4, 4),
        str((cf["logrado"], cf["clientes_cubiertos"])))
    chk("vendedor expone el tope dinámico", cf["tope"] == 1, str(cf["tope"]))
    chk("vendedor conserva el drill-down",
        len(cf["compradores"]) == 4 and "no_compradores" in cf,
        f"compradores={len(cf['compradores'])}")
    chk("gerencia y vendedor muestran la misma regla",
        (cf["umbral"], cf["tope"]) == (j["categorias_meta"]["familia_frizze"]["umbral"],
                                       j["categorias_meta"]["familia_frizze"]["tope"]))

    j3 = cli.get("/api/vendedor/V3/incentivo_faro").get_json()
    segs3 = {c["segmento"] for c in j3["categorias"]}
    chk("V3 no recibe categorías de Autoservicio", segs3 <= {"Tradicional"}, str(segs3))

    for cod in (2, 5):
        jx = cli.get(f"/api/vendedor/V{cod}/incentivo_faro").get_json()
        chk(f"V{cod} sin coberturas (excluido)",
            all(c["logrado"] == 0 for c in jx["categorias"]),
            str([(c["cat"], c["logrado"]) for c in jx["categorias"]]))


def main():
    inputs_orig = S.INPUTS
    tmp = tempfile.mkdtemp(prefix="faro_test_")
    try:
        test_sep_oct(tmp)
        test_may_jun(tmp)
        test_periodo_indeterminable(tmp)
        test_endpoints(tmp)
    finally:
        S.INPUTS = inputs_orig
        S._FARO_CFG_CACHE.clear()
        S._FARO_VENTAS_CACHE.clear()
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{'='*70}\nOK: {OK}   FALLAS: {len(FALLOS)}")
    for f in FALLOS:
        print(f"  - {f}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
