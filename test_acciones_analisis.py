# -*- coding: utf-8 -*-
"""Pruebas de la tarjeta "Análisis de la acción".

La lógica pura se prueba con datos sintéticos (así se puede forzar un cliente con exactamente
19 cajas o dos acciones indistinguibles, que en los datos reales no se dan a pedido) y el
cableado se prueba contra las fuentes reales del repo. Sin mocks de negocio: los sintéticos
son casos, no datos inventados que se publiquen en ningún lado.

Ejecutar:  python test_acciones_analisis.py
"""
import sys
from datetime import date

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
    return {"action_id": action_id, "subcategoria": action_id, "mecanica": "test",
            "productos": [{"nombre": p} for p in productos],
            "segmentos": [{"canal": canal, "segmentos_cliente": segmentos,
                           "escalas": [{"descuento": d} for d in descuentos]}]}


CANON = lambda ss: S._acc_seg_canon(" | ".join(ss), "")

#: Escala de cajas tal como la escribe el libro del mes: "1 a 9", "10 a 20" y "20 o más".
#: El solapamiento en 20 es exactamente lo que resuelve `normalizar_tramos`.
def escalas_cajas():
    return [{"min": 1,  "max": 9,    "descuento": 0.04, "unidad": "caja", "texto": "1 a 9 cajas · 4%"},
            {"min": 10, "max": 20,   "descuento": 0.06, "unidad": "caja", "texto": "10 a 20 cajas · 6%"},
            {"min": 20, "max": None, "descuento": 0.08, "unidad": "caja", "texto": "20 cajas o más · 8%"}]


# ═══════════════════════════════════════════════════════
print("\n── 1-5. Escalas: tramos 10-19 y 20+ ──")

esc = M.normalizar_tramos(escalas_cajas())
chk("1. El primer tramo cierra en 19, no en 20", esc[1]["max"] == 19,
    f"min={esc[1]['min']} max={esc[1]['max']}")
chk("1b. El texto visible acompaña al número", esc[1]["texto"] == "10 a 19 cajas · 6%",
    esc[1]["texto"])
chk("1c. Desaparece la marca de solapamiento",
    not esc[1].get("solapa") and not esc[2].get("solapa"))
chk("2. El segundo tramo arranca en 20 y no tiene techo",
    esc[2]["min"] == 20 and esc[2]["max"] is None)

for cajas, esperado in [(10, 10), (15, 10), (19, 10), (20, 20), (25, 20), (9, 1), (0, None)]:
    actual, _sig, _f = M.tramo_de(cajas, esc)
    got = actual["min"] if actual else None
    if cajas == 19:
        chk("3. Cliente con 19 cajas cae en el primer tramo (10-19)", got == 10, f"tramo min={got}")
    elif cajas == 20:
        chk("4. Cliente con 20 cajas cae en el segundo tramo (20+)", got == 20, f"tramo min={got}")
    else:
        chk(f"2b. {cajas} cajas -> tramo {esperado}", got == esperado, f"tramo min={got}")

_a, sig, faltan = M.tramo_de(17, esc)
chk("5. Cajas faltantes para el próximo tramo", sig["min"] == 20 and faltan == 3,
    f"faltan {faltan} para {sig['min']}")
chk("5b. Motivo legible del tramo",
    "con 3 más llega al tramo de 20" in M.motivo_tramo(17, 3, 20, 0.08),
    M.motivo_tramo(17, 3, 20, 0.08))
_a2, sig2, faltan2 = M.tramo_de(25, esc)
chk("5c. En el último tramo no hay siguiente", sig2 is None and faltan2 is None)


# ═══════════════════════════════════════════════════════
print("\n── 6-10. Movimiento de compradores ──")

cl = M.clasificar_clientes(
    ids_accion={1, 2, 3, 4},
    ids_marca_comparado={4},          # el 4 ya compraba las marcas
    ids_marca_ventana={3, 4},         # el 3 las compró en los 12 meses previos
    ids_historial_completo={2, 3, 4})  # el 1 no compró NUNCA nada

chk("6. Incorporado (no compró las marcas ni antes ni en el comparable)",
    cl[1]["grupo"] == "incorporado" and cl[2]["grupo"] == "incorporado")
chk("7. Reactivado (las compró en los 12 meses previos, no en el comparable)",
    cl[3]["grupo"] == "reactivado")
chk("8. Recurrente (ya las compraba en el comparable)", cl[4]["grupo"] == "recurrente")
chk("9. Nuevo para Peñaflor real = sin ninguna compra en todo el historial",
    cl[1]["nuevo_penaflor_real"] and not cl[2]["nuevo_penaflor_real"],
    "el 2 es incorporado pero ya era cliente")
chk("9b. Nuevo real es un dato aparte, no un cuarto grupo",
    cl[1]["grupo"] == "incorporado")
chk("10. Los tres grupos son mutuamente excluyentes",
    all(sum(1 for g in M.GRUPOS_MOVIMIENTO if v[g]) == 1 for v in cl.values()))
cnt = M.contar_clasificacion(cl)
chk("10b. Los tres grupos suman el total de clientes",
    cnt["incorporado"] + cnt["reactivado"] + cnt["recurrente"] == 4, str(cnt))


# ═══════════════════════════════════════════════════════
print("\n── 11-12. Días comerciales ──")

act, cmp_ = S._acc_an_periodos("mes_anterior")
chk("11. Mes parcial vs igual cantidad de días comerciales",
    act["dias_comerciales"] == cmp_["dias_comerciales"],
    f"{act['desde']}→{act['hasta']} ({act['dias_comerciales']}d) vs "
    f"{cmp_['desde']}→{cmp_['hasta']} ({cmp_['dias_comerciales']}d)")
chk("11b. Se informan las fechas exactas usadas",
    all(act.get(k) and cmp_.get(k) for k in ("desde", "hasta")))
act_a, cmp_a = S._acc_an_periodos("anio_anterior")
chk("11c. Año anterior: mismo mes, un año antes",
    cmp_a["periodo"][5:7] == act_a["periodo"][5:7] and
    int(cmp_a["periodo"][:4]) == int(act_a["periodo"][:4]) - 1,
    f"{act_a['periodo']} vs {cmp_a['periodo']}")

# Agosto 2026: del 1 al 18 hay 18 días corridos, 3 domingos (2, 9, 16) y el feriado del 17.
d_ago = S._acc_an_dias_comerciales(date(2026, 8, 1), date(2026, 8, 18))
chk("12. Domingos y feriados fuera del conteo", d_ago == 14,
    f"18 corridos - 3 domingos - 1 feriado (17/08 San Martín) = {d_ago}")
chk("12b. Un domingo solo no cuenta", S._acc_an_dias_comerciales(date(2026, 8, 9), date(2026, 8, 9)) == 0)
chk("12c. El feriado de feriados.csv no cuenta",
    S._acc_an_dias_comerciales(date(2026, 8, 17), date(2026, 8, 17)) == 0,
    "17/08/2026 San Martín")
chk("12d. Un sábado sí cuenta", S._acc_an_dias_comerciales(date(2026, 8, 8), date(2026, 8, 8)) == 1)
chk("12e. Los feriados no están cableados",
    "2026-08-17" not in open(S.__file__, encoding="utf-8").read(),
    "salen de 09_CONFIG/feriados.csv")


# ═══════════════════════════════════════════════════════
print("\n── 13-15. Reglas comerciales y fecha ──")

crudo = pd.DataFrame({
    "Cliente": ["1", "2", "3", "4", "5"],
    "CodVendedor": ["4", "2", "5", "20", "3"],
    "FechaComprobante": ["05/08/2026"] * 5,
    "FechaCarga": ["05/07/2026"] * 5,
    "FechaEntrega": ["05/09/2026"] * 5,
    "ImporteNetoItem": ["1000"] * 5, "ImporteItem": ["1210"] * 5,
    "CantBase": ["3"] * 5, "Codigo": ["74210"] * 5,
    "Articulo": ["ALMA MORA MALBEC 6X750"] * 5, "Marca": ["Alma Mora"] * 5,
    "valorDescuento": ["50"] * 5, "Ramo": ["TRADITIONAL TRADE"] * 5,
    "Subramo": ["ALMACEN"] * 5, "NroComprobante": ["F1"] * 5, "PesoKg": ["4.5"] * 5,
})
prep = S._acc_preparar_from_df(crudo)
vends = set(prep["_vend"].dropna().astype(int))
chk("13. V2 y V5 excluidos", not (vends & {2, 5}), f"vendedores={sorted(vends)}")
chk("13b. Depósito V1/V20 fuera del análisis", not (vends & {1, 20}))
chk("13c. Sólo vendedores activos", vends <= {3, 4, 6, 7, 8, 9, 10}, str(sorted(vends)))

chk("14. V3 no recibe universo de Autoservicio",
    S._acc_an_universo_potencial({"AUTOSERVICIO"}, "V3") == 0,
    f"V4 en cambio tiene {S._acc_an_universo_potencial({'AUTOSERVICIO'}, 'V4')}")

chk("15. El período sale de FechaComprobante", set(prep["_mes"].astype(str)) == {"2026-08"},
    "FechaCarga era 07/2026 y FechaEntrega 09/2026")
iso = crudo.copy()
iso["FechaComprobante"] = ["2026-07-05"] * 5
chk("15b. Fuente en ISO (cierre versionado) se parsea bien",
    set(S._acc_preparar_from_df(iso)["_mes"].astype(str)) == {"2026-07"})


# ═══════════════════════════════════════════════════════
print("\n── 16-18. Tops y oportunidades ──")

filas = [linea(cli=i, nro=f"F{i}", litros=i * 1.5, neto=i * 100.0) for i in range(1, 12)]
clasif = M.clasificar_clientes(set(range(1, 12)), set(), set(), set())
top = M.top_clientes(df(*filas), clasif)
chk("16. Top resultados acotado a 5", len(top) == 5, f"{len(filas)} clientes -> {len(top)}")
chk("16b. Ordenado por litros descendente",
    [t["litros"] for t in top] == sorted([t["litros"] for t in top], reverse=True))

cands = ([{"cliente_id": i, "volumen": 100 - i, "prioridad": M.OPORTUNIDAD_LAPSED} for i in range(8)]
         + [{"cliente_id": 50, "volumen": 5, "prioridad": M.OPORTUNIDAD_VOLUMEN}]
         + [{"cliente_id": 60, "volumen": 1, "prioridad": M.OPORTUNIDAD_TRAMO}])
opo = M.top_oportunidades(cands)
chk("16c. Top oportunidades acotado a 5", len(opo) == 5)
chk("16d. Los tres tipos de oportunidad quedan representados",
    {c["prioridad"] for c in opo} == {1, 2, 3},
    "sin cupo, el balde de 'dejó de comprar' se quedaba con los 5 lugares")
chk("16e. Con un solo tipo, la lista sale entera de ése",
    {c["prioridad"] for c in M.top_oportunidades(cands[:8])} == {1})

res = S._acciones_analisis("AGO26-VDA-SUP", "mes_anterior", "V8")
pay = res[0] if isinstance(res, tuple) else res
opos = pay["top_oportunidades"]
chk("17. Las oportunidades son del vendedor consultado",
    all(o["vendedor_id"] == "V8" for o in opos), str({o["vendedor_id"] for o in opos}))
cli_m = S._clientes_maestro()
segs_ok = set(cli_m.loc[cli_m["_vend_id"] == "V8", "_cliente_id"])
chk("17b. Las oportunidades son de la cartera real del vendedor",
    all(o["cliente_id"] in segs_ok for o in opos))
chk("17c. Cada oportunidad trae un motivo concreto",
    all(o.get("motivo") for o in opos), str([o["motivo"][:35] for o in opos][:2]))

# 18. elegible que no usó la acción: está en el universo pero no en los KPI de uso
eleg = S._trad_nc_elegibles(mes=S._acc_explorador().get("mes"), vid=None, detalle=False)
res_tnc = S._acciones_analisis("AGO26-TRAD-NC", "mes_anterior", None)
p_tnc = res_tnc[0] if isinstance(res_tnc, tuple) else res_tnc
chk("18. Ser elegible no cuenta como usar la acción",
    eleg["elegibles"] > p_tnc["resultado"]["clientes"],
    f"{eleg['elegibles']} elegibles vs {p_tnc['resultado']['clientes']} que usaron")
chk("18b. Los elegibles no entran en movimiento",
    (p_tnc["movimiento"]["incorporados"] + p_tnc["movimiento"]["reactivados"]
     + p_tnc["movimiento"]["recurrentes"]) == p_tnc["resultado"]["clientes"])


# ═══════════════════════════════════════════════════════
print("\n── 19-21. Atribución, objetivo y proyección ──")

a1 = sub("A1", ["Alma Mora"], [0.15], ["Tradicional"])
a2 = sub("A2", ["Alma Mora"], [0.15], ["Tradicional"])
a3 = sub("A3", ["Frizze"], [0.07], ["Tradicional"])
r = M.resolver_atribucion(a1, [a2, a3], CANON)
chk("19. Dos acciones indistinguibles -> ambiguous",
    r["metodo"] == M.METODO_AMBIGUO and r["colisiones"] == ["A2"], str(r["colisiones"]))
chk("19b. La advertencia nombra la colisión", "A2" in (r["advertencia"] or ""))
chk("19c. Sin colisión -> rule_discount",
    M.resolver_atribucion(a1, [a3], CANON)["metodo"] == M.METODO_REGLA)
chk("19d. Con tag exacto -> exact_tag",
    M.resolver_atribucion(a1, [a2], CANON, tags_encontrados=3)["metodo"] == M.METODO_TAG)

obj_vacio = M.evaluar_objetivo(None, {"litros": 186}, 14, 25)
chk("20. Objetivo no configurado no inventa nada",
    obj_vacio["configurado"] is False and obj_vacio["cumplimiento_pct"] is None
    and obj_vacio["nota"] == "Objetivo comercial no configurado")
chk("20b. Tampoco muestra 0%", obj_vacio["cumplimiento_pct"] != 0
    and obj_vacio["proyeccion_pct"] != 0)
chk("20c. Un objetivo en 0 se trata como no configurado",
    M.evaluar_objetivo({"tipo": "volumen", "valor": 0}, {"litros": 5}, 14, 25)["configurado"] is False)
chk("20d. Un tipo desconocido no se acepta",
    "inexistente" not in M.OBJETIVO_TIPOS)
chk("20e. Hoy ninguna acción tiene objetivo cargado",
    S._acc_an_objetivos() == {},
    "09_CONFIG/objetivos_acciones.csv está vacío; la tarjeta lo dice")

o = M.evaluar_objetivo({"tipo": "volumen", "valor": 300, "unidad": "litros"},
                       {"litros": 186}, 14, 25)
chk("21. Cumplimiento actual = logrado / objetivo", o["cumplimiento_pct"] == 62.0,
    f"186/300 = {o['cumplimiento_pct']}%")
chk("21b. Proyección al cierre por días comerciales",
    o["proyeccion_valor"] == 332.1 and o["proyeccion_pct"] == 110.7,
    f"186/14*25 = {o['proyeccion_valor']} ({o['proyeccion_pct']}%)")
chk("21c. Cumplimiento y proyección son campos distintos",
    o["cumplimiento_pct"] != o["proyeccion_pct"])
chk("21d. El objetivo de captación se mide en clientes, no en litros",
    M.evaluar_objetivo({"tipo": "captacion", "valor": 10},
                       {"litros": 999, "incorporados": 5}, 14, 25)["cumplimiento_pct"] == 50.0)
chk("21e. El objetivo de 11T se mide en impactos habilitados",
    M.evaluar_objetivo({"tipo": "once_titulares", "valor": 20},
                       {"impactos_habilitados": 10}, 14, 25)["cumplimiento_pct"] == 50.0)


# ═══════════════════════════════════════════════════════
print("\n── 22. Endpoint sin listas masivas ──")

import json as _json
txt = _json.dumps(p_tnc, ensure_ascii=False)
chk("22. El payload no trae listas masivas de clientes",
    "clientes_potenciales" not in p_tnc and len(txt) < 12000, f"{len(txt)} bytes")
chk("22b. Los dos tops están acotados a 5",
    len(p_tnc["top_resultados"]) <= 5 and len(p_tnc["top_oportunidades"]) <= 5)
chk("22c. El universo viaja como cantidad, en el detalle",
    isinstance(p_tnc["detalle"]["universo"]["universo_potencial"], int)
    and "universo" not in p_tnc.get("resultado", {}))
chk("22d. La estructura es la de la tarjeta nueva",
    set(p_tnc) >= {"accion", "periodos", "resultado", "movimiento", "comparacion",
                   "top_resultados", "top_oportunidades", "detalle"},
    ", ".join(sorted(p_tnc)))


# ═══════════════════════════════════════════════════════
print("\n── Regresión: caja mixta, 11T y avisos ──")

MARCA = S._acc_an_marca_trad_nc
d = df(linea(cli=1, nro="F1", cant=3, marca="ALMA MORA"),
       linea(cli=1, nro="F1", cant=3, marca="FRIZZE", art="FRIZZE BLUE X1000", cod="14583"))
chk("R1. 3+3 de dos marcas distintas es válida", len(M.comprobantes_caja_mixta(d, MARCA)) == 1)
chk("R2. 6 de una sola marca no es válida",
    len(M.comprobantes_caja_mixta(df(linea(cli=1, nro="F2", cant=6)), MARCA)) == 0)
d = df(linea(cli=1, nro="F3", cant=3), linea(cli=1, nro="F4", cant=3, marca="FRIZZE",
                                             art="FRIZZE BLUE X1000", cod="14583"))
chk("R3. 3+3 en comprobantes distintos no es válida",
    len(M.comprobantes_caja_mixta(d, MARCA)) == 0)

d11 = df(linea(cli=1, nro="F1", cant=3, cod="74210"),
         linea(cli=2, nro="F2", cant=3, cod="74210"),
         linea(cli=2, nro="F3", cant=3, cod="74210", pct=0.0, desc=0.0))
m_acc = pd.Series([True, True, False], index=d11.index)
r11 = M.impacto_once_titulares(d11, m_acc, {74210: "ALMA MORA"},
                               {1: "TRADICIONAL", 2: "TRADICIONAL"}, S.motor_11t.UMBRALES_11T)
chk("R4. 11T habilitado vs acompañado",
    r11["impactos_habilitados"] == 1 and r11["impactos_acompanados"] == 1, str(r11))
chk("R5. Sin matriz oficial, 11T no aplica",
    M.impacto_once_titulares(d11, m_acc, {}, {}, S.motor_11t.UMBRALES_11T)["aplica"] is False)

avisos = [{"severidad": "ALTA", "tema": "Escalas AS de 20 cajas",
           "hallazgo": "La fuente escribe 10 a 20 y 20 o más",
           "accion": "Claude debe revisar el comportamiento actual"},
          {"severidad": "MEDIA", "tema": "Terminología",
           "hallazgo": "La fuente alterna Trad y Almacenes", "accion": "Mapear aliases"}]
san = M.sanear_avisos(avisos)
chk("R6. Los avisos que nombran herramientas no llegan al portal",
    len(san) == 1 and san[0]["tema"] == "Terminología")
expl = S._acc_explorador()
todo = _json.dumps(expl, ensure_ascii=False).upper()
chk("R7. El catálogo publicado no menciona agentes ni herramientas",
    not any(t in todo for t in ("CLAUDE", "CODEX", "CHATGPT")))
chk("R8. El catálogo publicado no tiene escalas superpuestas",
    not expl.get("conflictos") and
    not any(e.get("solapa") for c in expl["categorias"] for s in c["subcategorias"]
            for g in s["segmentos"] for e in g["escalas"]))


print("\n" + "=" * 55)
print(f"{OK} OK, {len(FALLOS)} fallas")
for f in FALLOS:
    print("  -", f)
sys.exit(1 if FALLOS else 0)
