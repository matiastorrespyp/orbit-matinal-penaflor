# -*- coding: utf-8 -*-
"""Pruebas de la tarjeta "Análisis de la acción".

La lógica pura se prueba con datos sintéticos (así se puede forzar un 3+3 partido en dos
comprobantes o dos acciones indistinguibles, que en los datos reales no se dan a pedido) y el
cableado se prueba contra las fuentes reales del repo. Sin mocks de negocio: los sintéticos
son casos, no datos inventados que se publiquen en ningún lado.

Ejecutar:  python test_acciones_analisis.py
"""
import sys

import pandas as pd

import motor_acciones_analisis as M
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


def linea(cli=1, nro="A1", cant=3, pct=15.0, marca="ALMA MORA", art="ALMA MORA MALBEC 6X750",
          cod="74210", cat="VDA", seg="TRADICIONAL", litros=2.25, neto=1000.0, desc=150.0,
          linea_c="ALMA MORA", nombre="CLIENTE", vend=4):
    return {"_cli": cli, "_nro": nro, "_cant": cant, "_pct": pct, "_desc": desc,
            "_marca": marca, "_art": art, "_cod": cod, "_cat": cat, "_linea": linea_c,
            "_seg": seg, "_litros": litros, "_imp_neto": neto, "_clinom": nombre,
            "_vnom": f"V{vend}", "_vend": vend}


def df(*filas):
    return pd.DataFrame(list(filas))


def sub(action_id, productos, descuentos, segmentos, canal="Tradicional"):
    return {
        "action_id": action_id, "subcategoria": action_id, "mecanica": "test",
        "productos": [{"nombre": p} for p in productos],
        "segmentos": [{"canal": canal, "segmentos_cliente": segmentos,
                       "escalas": [{"descuento": d} for d in descuentos]}],
    }


CANON = lambda ss: S._acc_seg_canon(" | ".join(ss), "")


# ═══════════════════════════════════════════════════════
print("\n── 1-3. Atribución ──")

a1 = sub("A1", ["Alma Mora"], [0.15], ["Tradicional"])
a2 = sub("A2", ["Alma Mora"], [0.15], ["Tradicional"])      # indistinguible de a1
a3 = sub("A3", ["Frizze"], [0.07], ["Tradicional"])

# 1. atribución exacta por tag (hoy el ERP no la emite; se fuerza el hallazgo)
r = M.resolver_atribucion(a1, [a3], CANON, tags_encontrados=5)
chk("1. Tag exacto -> exact_tag", r["metodo"] == M.METODO_TAG and r["advertencia"] is None)

d_tags = df(linea()); d_tags["_tags"] = ["PROMO A1 GRUPO"]
chk("1b. buscar_tag_accion encuentra el id cuando está",
    M.buscar_tag_accion(d_tags, "A1") == 1)
chk("1c. Ninguna columna del ERP real trae el action_id",
    M.buscar_tag_accion(S._acc_preparar_ventas("ventas.csv"), "AGO26-TRAD-NC") == 0,
    "confirmado sobre ventas.csv")

# 2. atribución por regla
r = M.resolver_atribucion(a1, [a3], CANON)
chk("2. Productos+canal+descuento -> rule_discount",
    r["metodo"] == M.METODO_REGLA and not r["colisiones"])

# 3. dos acciones indistinguibles
r = M.resolver_atribucion(a1, [a2, a3], CANON)
chk("3. Acciones indistinguibles -> ambiguous",
    r["metodo"] == M.METODO_AMBIGUO and r["colisiones"] == ["A2"], str(r["colisiones"]))
chk("3b. La advertencia nombra la colisión", "A2" in (r["advertencia"] or ""))

# sin doble conteo: la misma línea evaluada por las dos acciones es UNA línea
d = df(linea(cli=1, nro="F1"))
m1 = M.mask_descuento(d, M.tramos_de(a1))
m2 = M.mask_descuento(d, M.tramos_de(a2))
chk("3c. Sin doble conteo: la línea es una sola en ambas acciones",
    int(m1.sum()) == 1 and int(m2.sum()) == 1 and int((m1 & m2).sum()) == 1)


# ═══════════════════════════════════════════════════════
print("\n── 4-7. Caja mixta 3+3 (AGO26-TRAD-NC) ──")

MARCA = S._acc_an_marca_trad_nc

# 4. 3+3 de marcas distintas, mismo comprobante, 15%
d = df(linea(cli=1, nro="F1", cant=3, marca="ALMA MORA"),
       linea(cli=1, nro="F1", cant=3, marca="FRIZZE", art="FRIZZE BLUE X1000", cod="14583"))
ok = M.comprobantes_caja_mixta(d, MARCA)
chk("4. 3+3 de dos marcas distintas es válida", len(ok) == 1 and ok.iloc[0]["botellas_accion"] == 6)

# 5. seis botellas de una sola marca
d = df(linea(cli=1, nro="F2", cant=6, marca="ALMA MORA"))
chk("5. 6 botellas de una sola marca NO es válida",
    len(M.comprobantes_caja_mixta(d, MARCA)) == 0)

# 6. 3+3 en comprobantes diferentes
d = df(linea(cli=1, nro="F3", cant=3, marca="ALMA MORA"),
       linea(cli=1, nro="F4", cant=3, marca="FRIZZE", art="FRIZZE BLUE X1000", cod="14583"))
chk("6. 3+3 en comprobantes distintos NO es válida",
    len(M.comprobantes_caja_mixta(d, MARCA)) == 0)

# 7. descuento distinto al 15%
d = df(linea(cli=1, nro="F5", cant=3, marca="ALMA MORA", pct=10.0),
       linea(cli=1, nro="F5", cant=3, marca="FRIZZE", art="FRIZZE BLUE X1000", cod="14583", pct=10.0))
chk("7. Descuento distinto de 15% NO es válido",
    len(M.comprobantes_caja_mixta(d, MARCA)) == 0)

d = df(linea(cli=1, nro="F6", cant=2, marca="ALMA MORA"),
       linea(cli=1, nro="F6", cant=3, marca="FRIZZE", art="FRIZZE BLUE X1000", cod="14583"))
chk("7b. Menos de 3 botellas de una marca NO es válida",
    len(M.comprobantes_caja_mixta(d, MARCA)) == 0)

d = df(linea(cli=1, nro="F7", cant=2, marca="ALMA MORA"),
       linea(cli=1, nro="F7", cant=1, marca="ALMA MORA", art="ALMA MORA SYRAH 6X750", cod="74209"),
       linea(cli=1, nro="F7", cant=3, marca="FRIZZE", art="FRIZZE BLUE X1000", cod="14583"))
chk("7c. Dos SKU de la misma marca suman para llegar a 3",
    len(M.comprobantes_caja_mixta(d, MARCA)) == 1)


# ═══════════════════════════════════════════════════════
print("\n── 8-12. Clasificación de clientes ──")

cl = M.clasificar_clientes(
    ids_accion={1, 2, 3, 4, 5},
    ids_comparado_todo={4, 5},          # compraron en el período comparado
    ids_comparado_categoria={5},        # sólo el 5 compró la categoría
    ids_comparado_marca={5},            # sólo el 5 compró la marca
    ids_ventana_historica={3, 4, 5})    # el 3 compró antes, pero no en el comparado

chk("8. Nuevo Peñaflor (ni comparado ni 12 meses)", cl[1]["nuevo_penaflor"] and cl[2]["nuevo_penaflor"])
chk("9. Nuevo en categoría", cl[4]["nuevo_categoria"] and not cl[5]["nuevo_categoria"])
chk("10. Nuevo en marca", cl[4]["nuevo_marca"] and not cl[5]["nuevo_marca"])
chk("11. Reactivado (sin compra en el comparado, con compra en 12 meses)",
    cl[3]["reactivado"] and not cl[3]["nuevo_penaflor"])
chk("12. Recurrente (compró en el comparado)", cl[4]["recurrente"] and cl[5]["recurrente"])
chk("12b. Nuevo y reactivado son excluyentes",
    all(not (v["nuevo_penaflor"] and v["reactivado"]) for v in cl.values()))
chk("12c. Estar en el universo elegible no clasifica a nadie",
    99 not in cl, "sólo entran los que usaron la acción")
cnt = M.contar_clasificacion(cl)
chk("12d. Los totales cierran contra la cantidad de clientes",
    cnt["nuevo_penaflor"] + cnt["reactivado"] + cnt["recurrente"] == 5, str(cnt))


# ═══════════════════════════════════════════════════════
print("\n── 13-15. Reglas comerciales y fecha ──")

crudo = pd.DataFrame({
    "Cliente": ["1", "2", "3", "4", "5"],
    "CodVendedor": ["4", "2", "5", "20", "3"],
    "FechaComprobante": ["05/08/2026"] * 5,
    "FechaCarga": ["05/07/2026"] * 5,
    "FechaEntrega": ["05/09/2026"] * 5,
    "ImporteNetoItem": ["1000"] * 5,
    "ImporteItem": ["1210"] * 5, "CantBase": ["3"] * 5, "Codigo": ["74210"] * 5,
    "Articulo": ["ALMA MORA MALBEC 6X750"] * 5, "Marca": ["Alma Mora"] * 5,
    "valorDescuento": ["50"] * 5, "Ramo": ["TRADITIONAL TRADE"] * 5,
    "Subramo": ["ALMACEN"] * 5, "NroComprobante": ["F1"] * 5, "PesoKg": ["4.5"] * 5,
})
prep = S._acc_preparar_from_df(crudo)
vends = set(prep["_vend"].dropna().astype(int))
chk("13. V2 y V5 excluidos", not (vends & {2, 5}), f"vendedores={sorted(vends)}")
chk("13b. Depósito V1/V20 fuera del análisis", 20 not in vends and 1 not in vends)
chk("13c. Sólo quedan vendedores activos", vends <= {3, 4, 6, 7, 8, 9, 10}, str(sorted(vends)))

# 14. V3 no trabaja Autoservicio
uni_v3 = S._acc_an_universo_potencial({"AUTOSERVICIO"}, "V3")
uni_v4 = S._acc_an_universo_potencial({"AUTOSERVICIO"}, "V4")
chk("14. V3 sin universo de Autoservicio", uni_v3 == 0, f"V3={uni_v3} vs V4={uni_v4}")

# 15. período por FechaComprobante, nunca por FechaCarga/FechaEntrega
chk("15. El período sale de FechaComprobante",
    set(prep["_mes"].astype(str)) == {"2026-08"},
    "FechaCarga era 07/2026 y FechaEntrega 09/2026")

iso = crudo.copy()
iso["FechaComprobante"] = ["2026-07-05"] * 5
chk("15b. Fuente en ISO (cierre versionado) se parsea bien",
    set(S._acc_preparar_from_df(iso)["_mes"].astype(str)) == {"2026-07"})


# ═══════════════════════════════════════════════════════
print("\n── 16-17. Períodos y fuentes ──")

act, cmp_ = S._acc_an_periodos("mes_anterior")
chk("16. Mes parcial se compara contra corte equivalente",
    act["dias_comerciales"] == cmp_["dias_comerciales"],
    f"{act['desde']}→{act['hasta']} ({act['dias_comerciales']}d) vs "
    f"{cmp_['desde']}→{cmp_['hasta']} ({cmp_['dias_comerciales']}d)")
chk("16b. Se informa que el mes está en curso", act["parcial"] is True)
chk("16c. El total cerrado del mes comparado viaja aparte",
    cmp_["mes_completo_hasta"] > cmp_["hasta"], cmp_["mes_completo_hasta"])
act_a, cmp_a = S._acc_an_periodos("anio_anterior")
chk("16d. Año anterior compara el mismo mes",
    cmp_a["periodo"][5:7] == act_a["periodo"][5:7] and
    int(cmp_a["periodo"][:4]) == int(act_a["periodo"][:4]) - 1,
    f"{act_a['periodo']} vs {cmp_a['periodo']}")

vivo = S._acc_an_mes_vivo()
p_vivo, e_vivo = S._acc_an_fuente(vivo)
chk("17. Mes en curso -> ventas.csv", p_vivo.name == "ventas.csv", e_vivo)
p_jul, e_jul = S._acc_an_fuente(pd.Period("2026-07", freq="M"))
chk("17b. Mes cerrado con cierre versionado -> cierres mes/",
    p_jul.name == "ventas_mes_072026.csv", e_jul)
p_ago25, e_ago25 = S._acc_an_fuente(pd.Period("2025-08", freq="M"))
chk("17c. Mes cerrado sin cierre versionado -> historial",
    p_ago25.name == "historial_ventas.csv", e_ago25)
chk("17d. Un cierre del mes en curso NO se usa por adelantado",
    p_vivo.parent.name != "cierres mes",
    "el mes vivo siempre sale de ventas.csv aunque exista el cierre")


# ═══════════════════════════════════════════════════════
print("\n── 18-19. Salidas acotadas ──")

filas = [linea(cli=i, nro=f"F{i}", litros=i * 1.5, neto=i * 100.0) for i in range(1, 12)]
clasif = M.clasificar_clientes(set(range(1, 12)), set(), set(), set(), set())
top = M.top_clientes(df(*filas), clasif)
chk("18. Top compradores acotado a 5", len(top) == 5, f"{len(filas)} clientes -> {len(top)}")
chk("18b. Ordenado por litros descendente",
    [t["litros"] for t in top] == sorted([t["litros"] for t in top], reverse=True))
top_i = M.top_clientes(df(*filas), clasif, "incorporaciones")
chk("18c. Top incorporaciones también acotado a 5", len(top_i) == 5)

res = S._acciones_analisis("AGO26-TRAD-NC", "mes_anterior", None)
pay = res[0] if isinstance(res, tuple) else res
chk("19. El payload del análisis no trae listado de potenciales",
    "clientes" not in pay and "clientes_potenciales" not in pay,
    "claves: " + ", ".join(sorted(pay.keys())))
chk("19b. Top del payload acotado a 5",
    len(pay["top_clientes"]["compradores"]) <= 5 and len(pay["top_clientes"]["incorporaciones"]) <= 5)
chk("19c. El embudo informa el universo como cantidad",
    isinstance(pay["embudo"]["universo_potencial"], int))
eleg = S._trad_nc_elegibles(mes=S._acc_explorador().get("mes"), vid=None, detalle=False)
chk("19d. Elegibilidad sin detalle no devuelve la lista",
    eleg["clientes"] == [] and eleg["elegibles"] > 0, f"{eleg['elegibles']} elegibles")


# ═══════════════════════════════════════════════════════
print("\n── 20. 11 Titulares ──")

# cliente 1 (Tradicional, umbral 3): 3 botellas y las 3 son de la acción -> habilitado
# cliente 2: 6 botellas, 3 de la acción -> llegaba igual -> acompañado
# cliente 3: 2 botellas de la acción -> no cubre -> no cuenta
d11 = df(linea(cli=1, nro="F1", cant=3, cod="74210"),
         linea(cli=2, nro="F2", cant=3, cod="74210"),
         linea(cli=2, nro="F3", cant=3, cod="74210", pct=0.0, desc=0.0),
         linea(cli=3, nro="F4", cant=2, cod="74210"))
m_acc = pd.Series([True, True, False, True], index=d11.index)
segs = {1: "TRADICIONAL", 2: "TRADICIONAL", 3: "TRADICIONAL"}
r11 = M.impacto_once_titulares(d11, m_acc, {74210: "ALMA MORA"}, segs, S.motor_11t.UMBRALES_11T)
chk("20. Impacto habilitado (no llegaba sin la acción)", r11["impactos_habilitados"] == 1, str(r11))
chk("20b. Impacto acompañado (llegaba igual)", r11["impactos_acompanados"] == 1)
chk("20c. Asociados = habilitados + acompañados",
    r11["impactos_asociados"] == r11["impactos_habilitados"] + r11["impactos_acompanados"])
chk("20d. El que no alcanza el umbral no suma impacto", r11["impactos_asociados"] == 2)

r11_no = M.impacto_once_titulares(d11, m_acc, {}, segs, S.motor_11t.UMBRALES_11T)
chk("20e. Sin matriz 11T -> no aplica y todo en null",
    r11_no["aplica"] is False and r11_no["impactos_asociados"] is None)

r11_fuera = M.impacto_once_titulares(d11, m_acc, {74210: "ALMA MORA"},
                                     {1: "ON_PREMISE_VTK", 2: "ON_PREMISE_VTK", 3: "OTROS"},
                                     S.motor_11t.UMBRALES_11T)
chk("20f. Segmento sin umbral 11T no genera impactos", r11_fuera["impactos_asociados"] == 0)

chk("20g. El titular sale de la matriz oficial, no del nombre de marca",
    M.impacto_once_titulares(d11, m_acc, {99999: "OTRA"}, segs,
                             S.motor_11t.UMBRALES_11T)["aplica"] is False,
    "SKU fuera de la matriz no es 11T")


# ═══════════════════════════════════════════════════════
print("\n── 21. Sin doble conteo ──")

d = df(linea(cli=1, nro="F1", cant=3, marca="ALMA MORA"),
       linea(cli=1, nro="F1", cant=3, marca="FRIZZE", art="FRIZZE BLUE X1000", cod="14583"),
       linea(cli=1, nro="F1", cant=3, marca="ALARIS", art="TRAPICHE ALARIS MALBEC", cod="71704"))
ok = M.comprobantes_caja_mixta(d, MARCA)
chk("21. Un comprobante con tres marcas cuenta UNA vez", len(ok) == 1, f"{len(ok)} filas")
chk("21b. Las botellas del comprobante no se duplican",
    ok.iloc[0]["botellas_accion"] == 9)

chk("21c. Comprobantes de la acción = nunique, no cantidad de líneas",
    pay["kpis"]["comprobantes_accion"] <= pay["kpis"]["clientes_accion"] * 10)
chk("21d. Clientes de la acción = únicos",
    pay["kpis"]["clientes_accion"] == len({t["cliente_id"] for t in pay["top_clientes"]["compradores"]})
    or pay["kpis"]["clientes_accion"] > 5)

# el mismo cliente en dos comprobantes válidos es UN cliente y DOS comprobantes
d = df(linea(cli=7, nro="G1", cant=3, marca="ALMA MORA"),
       linea(cli=7, nro="G1", cant=3, marca="FRIZZE", art="FRIZZE BLUE X1000", cod="14583"),
       linea(cli=7, nro="G2", cant=3, marca="ALMA MORA"),
       linea(cli=7, nro="G2", cant=3, marca="DADA", art="DADA 7 SWEET 6X750", cod="74446"))
ok = M.comprobantes_caja_mixta(d, MARCA)
chk("21e. Dos comprobantes del mismo cliente: 1 cliente, 2 comprobantes",
    len(ok) == 2 and ok["_cli"].nunique() == 1)


print("\n" + "=" * 55)
print(f"{OK} OK, {len(FALLOS)} fallas")
for f in FALLOS:
    print("  -", f)
sys.exit(1 if FALLOS else 0)
