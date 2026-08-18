# -*- coding: utf-8 -*-
"""Casos obligatorios de AGO26-TRAD-NC contra datos REALES (sin mocks).

Ejecutar:  python test_acciones_trad_nc.py
"""
import sys

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


def main():
    mes = S._acc_explorador().get("mes")
    r = S._trad_nc_elegibles(mes=mes, vid=None, detalle=True)
    print(f"\nmes={r['mes']} fuente={r['fuente']}")
    print(f"cartera_tradicional={r['cartera_tradicional']} elegibles={r['elegibles']} "
          f"no_elegibles={r['no_elegibles']} sin_compras={r['sin_compras_penaflor']} "
          f"compro_otros={r['compro_otros']}\n")

    assert r["nota"] is None, r["nota"]
    elegibles = {c["cliente_id"] for c in r["clientes"]}

    # Fuente cruda, recalculada aparte para no validar el motor contra sí mismo.
    v = S._acc_preparar_ventas("ventas.csv")
    per = pd.Period(r["mes"], freq="M")
    vm = v[(v["_mes"] == per) & (v["_imp_neto"] > 0)]
    compradas = S._trad_nc_marcas_compradas(vm)
    compradores = set().union(*compradas.values())
    con_compra = set(vm["_cli"].dropna().astype(int))

    cli = S._clientes_maestro().copy()
    cli["_seg"] = [S._clasificar_segmento(a, b)
                   for a, b in zip(cli.get("Ramo", ""), cli.get("SubSegmento", ""))]
    trad = cli[(cli["_seg"] == "TRADICIONAL")
               & (cli["_vend_id"].isin(S._VENDEDORES_ACTIVOS_PLAN))]
    ids_trad = set(trad["_cliente_id"])

    print("--- Casos de elegibilidad ---")

    # 1. Tradicional sin ninguna compra Peñaflor en agosto -> elegible
    c1 = sorted(ids_trad - con_compra)
    chk("Tradicional sin compras Peñaflor es elegible",
        bool(c1) and all(c in elegibles for c in c1[:200]),
        f"{len(c1)} clientes, testigo #{c1[0] if c1 else '-'}")

    # 2. Tradicional que compró SOLO productos ajenos a las 10 marcas -> elegible
    c2 = sorted((ids_trad & con_compra) - compradores)
    chk("Tradicional con compras fuera de las 10 marcas es elegible",
        bool(c2) and all(c in elegibles for c in c2),
        f"{len(c2)} clientes, testigo #{c2[0] if c2 else '-'}")

    # 3. Tradicional que compró alguna de las 10 marcas -> NO elegible
    c3 = sorted(ids_trad & compradores)
    chk("Tradicional que compró una marca elegible NO es elegible",
        bool(c3) and not (set(c3) & elegibles),
        f"{len(c3)} clientes, testigo #{c3[0] if c3 else '-'}")

    # 4. Cliente no Tradicional -> NO elegible (aunque no haya comprado nada)
    no_trad = set(cli[cli["_seg"] != "TRADICIONAL"]["_cliente_id"])
    chk("Cliente no Tradicional NO es elegible",
        bool(no_trad) and not (no_trad & elegibles),
        f"{len(no_trad)} clientes de otros canales")

    # 5. V2 / V5 excluidos de punta a punta
    vends = {c["vendedor_id"] for c in r["clientes"]}
    chk("V2/V5 excluidos", not (vends & {"V2", "V5"}), f"vendedores presentes: {sorted(vends)}")
    chk("Sólo vendedores activos de ruta", vends <= S._VENDEDORES_ACTIVOS_PLAN,
        "sin depósito V1/V20 ni bajas")

    # 6. Coherencia de los contadores publicados
    chk("elegibles + no_elegibles = cartera Tradicional",
        r["elegibles"] + r["no_elegibles"] == r["cartera_tradicional"])
    chk("sin_compras + compro_otros = elegibles",
        r["sin_compras_penaflor"] + r["compro_otros"] == r["elegibles"])
    chk("la lista detallada tiene tantas filas como elegibles",
        len(r["clientes"]) == r["elegibles"], f"{len(r['clientes'])} filas")
    chk("por_vendedor suma el total",
        sum(x["elegibles"] for x in r["por_vendedor"]) == r["elegibles"])

    # 7. Período por FechaComprobante: nada fuera de agosto entra en el cálculo
    fuera = v[v["_mes"] != per]
    chk("El cálculo usa sólo el mes del catálogo (FechaComprobante)",
        len(vm) + len(fuera) == len(v) and (vm["_mes"] == per).all(),
        f"{len(vm)} líneas de {r['mes']}, {len(fuera)} fuera")

    print("\n--- Mecánica 3+3 (declarada en la escala del catálogo) ---")
    sub = None
    for cat in S._acc_explorador()["categorias"]:
        for s in cat["subcategorias"]:
            if s["action_id"] == S.TRAD_NC_ACTION_ID:
                sub = s
    chk("La acción está en el explorador", sub is not None)
    esc = sub["segmentos"][0]["escalas"][0]
    chk("Descuento 15%", esc["descuento"] == 0.15)
    chk("Caja de 6 botellas", esc["unidad"] == "botella" and esc["min"] == 6 and esc["max"] == 6)
    chk("Mezcla 3+3 de dos marcas distintas es válida", "3 + 3" in esc["texto"], esc["texto"])
    chk("6 botellas de una sola marca NO califica",
        "6 de una sola marca no califica" in (esc["observacion"] or ""))
    chk("Las 10 marcas elegibles están publicadas",
        [p["nombre"] for p in sub["productos"]] == [m for m, _ in S._TRAD_NC_MARCAS],
        str(len(sub["productos"])) + " marcas")

    print("\n--- Innovaciones: SKU Alma Mora Low separados ---")
    innov = [s for c in S._acc_explorador()["categorias"] for s in c["subcategorias"]
             if s["action_id"] == "AGO26-INNOV"][0]
    nombres = [p["nombre"] for p in innov["productos"]]
    chk("SKU 74827 visible en Innovaciones", any(n.startswith("74827") for n in nombres))
    chk("SKU 74887 visible en Innovaciones", any(n.startswith("74887") for n in nombres))
    chk("La entrada genérica 'Alma Mora Low' ya no está", "Alma Mora Low" not in nombres)
    escalas_innov = [(e["min"], e["max"], e["descuento"]) for e in innov["segmentos"][0]["escalas"]]
    chk("Escalas de Innovaciones intactas (3u 18% / 5 bultos 20%)",
        escalas_innov == [(3, 3, 0.18), (5, None, 0.20)], str(escalas_innov))

    print("\n--- Filtro por vendedor ---")
    rv = S._trad_nc_elegibles(mes=mes, vid="V3", detalle=True)
    chk("El scope de vendedor devuelve sólo su cartera",
        {c["vendedor_id"] for c in rv["clientes"]} == {"V3"},
        f"V3: {rv['elegibles']} elegibles de {rv['cartera_tradicional']}")
    chk("El total de V3 coincide con el desglose de gerencia",
        rv["elegibles"] == [x for x in r["por_vendedor"] if x["vendedor_id"] == "V3"][0]["elegibles"])

    print(f"\n{'=' * 50}\n{OK} OK, {len(FALLOS)} fallas")
    if FALLOS:
        for f in FALLOS:
            print("  -", f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
