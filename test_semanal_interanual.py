# -*- coding: utf-8 -*-
"""Pruebas del interanual de litros por canal y categoría (pantalla Semanal).

Las funciones puras se prueban con DataFrames controlados (así se puede forzar un cliente
perdido o un alta sin base, que en los datos reales no se dan a pedido) y la conciliación
final se hace contra las fuentes reales del repo. Sin mocks: los sintéticos son casos de
borde, no datos que se publiquen en ningún lado.

Ejecutar:  python test_semanal_interanual.py
"""
import sys
from datetime import date

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


def fila(cli=1, litros=10.0, canal="Tradicionales", cat="Vinos del año", seg="Alto",
         lin="Alma Mora", marca="ALMA MORA", razon="CLIENTE", vend=4, cod="74210",
         art="ALMA MORA MALBEC", fecha="2026-08-05"):
    return {"cli": cli, "razon": razon, "fecha": pd.Timestamp(fecha),
            "periodo": pd.Period(fecha[:7], freq="M"), "litros": litros, "canal": canal,
            "categoria": cat, "segmento": seg, "linea": lin, "marca": marca,
            "cod": cod, "articulo": art, "vend": vend}


def df(*filas):
    return pd.DataFrame(list(filas)) if filas else pd.DataFrame(
        columns=["cli", "razon", "fecha", "periodo", "litros", "canal", "categoria",
                 "segmento", "linea", "marca", "cod", "articulo", "vend"])


# ═══════════════════════════════════════════════════════
print("\n── 1-3. Fuentes por período ──")

vivo = S._ia_mes_vivo()
chk("1. Hay mes vivo detectado", vivo is not None, str(vivo))

p_act, e_act = S._ia_fuente_de(vivo)
chk("1b. Mes en curso -> 01_INPUTS/ventas.csv", p_act.name == "ventas.csv", e_act)
chk("1c. El mes en curso NO sale de un cierre anticipado", p_act.parent.name != "cierres mes")

p_jul, e_jul = S._ia_fuente_de(pd.Period("2026-07", freq="M"))
chk("2. Mes cerrado con cierre versionado -> cierres mes/",
    p_jul.name == "ventas_mes_072026.csv", e_jul)

for per in ("2025-08", "2025-07"):
    p_ly, e_ly = S._ia_fuente_de(pd.Period(per, freq="M"))
    chk(f"3. {per} -> historial_ventas.csv", p_ly.name == "historial_ventas.csv", e_ly)

d_ly, _ = S._ia_rango(pd.Period("2025-08", freq="M"))
chk("3b. El historial trae agosto 2025 con datos", len(d_ly) > 0, f"{len(d_ly)} líneas")
chk("3c. Una fuente por período, sin concatenar",
    set(d_ly["periodo"].astype(str).unique()) == {"2025-08"})


# ═══════════════════════════════════════════════════════
print("\n── 4-5. FechaComprobante y exclusiones ──")

crudo = pd.DataFrame({
    "Cliente": ["1", "2", "3", "4", "5", "6"],
    "RazonSocial": ["A", "B", "C", "D", "E", "F"],
    "CodVendedor": ["4", "2", "5", "20", "1", "3"],
    "FechaComprobante": ["05/08/2026"] * 6,
    "FechaCarga": ["05/07/2026"] * 6,
    "FechaEntrega": ["05/09/2026"] * 6,
    "ImporteNetoItem": ["1000", "1000", "1000", "1000", "1000", "-500"],
    "CantBase": ["6"] * 6, "Codigo": ["74210"] * 6,
    "Articulo": ["ALMA MORA MALBEC 6X750"] * 6, "Marca": ["Alma Mora"] * 6,
    "Ramo": ["TRADITIONAL TRADE"] * 6, "Subramo": ["ALMACEN"] * 6,
    "PesoKg": ["4.5"] * 6, "Vendedor": ["V"] * 6,
})
import io
tmp = S.BASE / "99_LOGS_ORBIT" / "_test_ia_fuente.csv"
tmp.parent.mkdir(exist_ok=True)
crudo.to_csv(tmp, sep=";", index=False, encoding="utf-8-sig")
prep = S._ia_leer(tmp)
tmp.unlink(missing_ok=True)

chk("4. El período sale de FechaComprobante",
    set(prep["periodo"].astype(str)) == {"2026-08"},
    "FechaCarga era 07/2026 y FechaEntrega 09/2026")
vends = set(prep["vend"].dropna().astype(int))
chk("5. V2 y V5 excluidos", not (vends & {2, 5}), f"vendedores={sorted(vends)}")
chk("5b. El Depósito V1/V20 SÍ entra (universo empresa, igual que Semanal)",
    {1, 20} <= vends, f"vendedores={sorted(vends)}")
chk("5c. Las líneas con neto <= 0 quedan fuera (devoluciones no restan)",
    6 not in set(prep["cli"]), "mismo criterio que _semanal_leer")
chk("5d. Los litros salen de la cascada oficial", float(prep["litros"].sum()) > 0,
    f"{round(float(prep['litros'].sum()),1)} L de 4 clientes válidos")


# ═══════════════════════════════════════════════════════
print("\n── 6-8. Días comerciales y proyección ──")

# Agosto 2026: 18 corridos - 3 domingos (2, 9, 16) - 1 feriado (17, San Martín) = 14
chk("6. Días comerciales al corte", S._dias_comerciales(date(2026, 8, 1), date(2026, 8, 18)) == 14,
    "lunes a sábado, sin domingos ni feriados")
chk("6b. El feriado 2026-08-17 no cuenta",
    S._dias_comerciales(date(2026, 8, 17), date(2026, 8, 17)) == 0, "San Martín, de feriados.csv")
chk("6c. Un domingo no cuenta", S._dias_comerciales(date(2026, 8, 9), date(2026, 8, 9)) == 0)
chk("6d. Un sábado sí cuenta", S._dias_comerciales(date(2026, 8, 8), date(2026, 8, 8)) == 1)
chk("6e. Los feriados no están cableados",
    "2026-08-17" not in open(S.__file__, encoding="utf-8").read(),
    "salen de 09_CONFIG/feriados.csv")

p = S._ia_cacheado()
a = p["actual"]
chk("7. La proyección usa días comerciales",
    abs(a["litros_proyectados"] - a["litros_actual_mtd"] / a["dias_transcurridos"]
        * a["dias_totales"]) < 0.5,
    f"{a['litros_actual_mtd']}/{a['dias_transcurridos']}*{a['dias_totales']} = {a['litros_proyectados']}")
chk("7b. El corte es la última FechaComprobante, no la fecha del servidor",
    a["corte_actual"] == str(S._ia_leer(S.INPUTS / "ventas.csv")
                             .query("periodo == @S._ia_mes_vivo()")["fecha"].max().date()),
    a["corte_actual"])
chk("8. El corte LY comparable usa la misma cantidad de días comerciales",
    S._dias_comerciales(pd.Period(a["periodo_ly"], freq="M").start_time.date(),
                        pd.Timestamp(a["corte_ly_comparable"]).date()) == a["dias_transcurridos"],
    f"{a['corte_actual']} ({a['dias_transcurridos']}d) vs {a['corte_ly_comparable']}")
chk("8b. Se exponen las cuatro fechas del corte",
    all(a.get(k) for k in ("periodo", "corte_actual", "periodo_ly", "corte_ly_comparable")))


# ═══════════════════════════════════════════════════════
print("\n── 9-11. Rankings de clientes (outer join) ──")

# cli 1: compra ahora y compraba LY -> variación
# cli 2: compraba LY y NO compra ahora -> caída completa (Perdido)
# cli 3: compra ahora y NO compraba LY -> alta (Nuevo, delta_pct null)
act = df(fila(cli=1, litros=100.0), fila(cli=3, litros=50.0))
ly = df(fila(cli=1, litros=80.0, fecha="2025-08-05"),
        fila(cli=2, litros=200.0, fecha="2025-08-05"))
caidas, crec = S._ia_tops(act, ly)

chk("9. El cliente con venta LY y cero actual aparece como caída",
    any(f["cliente_id"] == 2 for f in caidas), f"caídas: {[f['cliente_id'] for f in caidas]}")
perdido = next(f for f in caidas if f["cliente_id"] == 2)
chk("9b. Su actual es 0 y su delta es la pérdida completa",
    perdido["litros_actual"] == 0 and perdido["delta"] == -200.0)
chk("9c. Su estado es 'Perdido'", perdido["estado"] == "Perdido")
chk("9d. No se pierde por un inner join", 2 not in set(act["cli"]),
    "el cliente 2 no existe en el frame actual y aun así está en el ranking")

chk("10. El cliente nuevo aparece como crecimiento",
    any(f["cliente_id"] == 3 for f in crec))
nuevo = next(f for f in crec if f["cliente_id"] == 3)
chk("10b. Con delta_pct null, sin porcentaje infinito", nuevo["delta_pct"] is None)
chk("10c. Y estado 'Nuevo'", nuevo["estado"] == "Nuevo", str(nuevo["estado"]))

chk("11. Caídas ordenadas por delta ascendente",
    [f["delta"] for f in caidas] == sorted(f["delta"] for f in caidas))
chk("11b. Crecimientos ordenados por delta descendente",
    [f["delta"] for f in crec] == sorted((f["delta"] for f in crec), reverse=True))

muchos_a = df(*[fila(cli=i, litros=float(i)) for i in range(1, 21)])
muchos_l = df(*[fila(cli=i, litros=float(100 - i), fecha="2025-08-05") for i in range(1, 21)])
c5, g5 = S._ia_tops(muchos_a, muchos_l)
chk("11c. Top 5 devuelve exactamente cinco filas", len(c5) == 5, f"de 20 clientes -> {len(c5)}")

# Con factor de proyección, el ranking compara proyectado contra LY mes completo
cp, gp = S._ia_tops(act, ly, factor=2.0, df_ly_completo=ly)
uno = next(f for f in (cp + gp) if f["cliente_id"] == 1)
chk("11d. Con proyección, el delta es proyectado - LY completo",
    uno["litros_proyectados"] == 200.0 and uno["delta"] == 120.0,
    f"100x2 - 80 = {uno['delta']}")


# ═══════════════════════════════════════════════════════
print("\n── 12-14. Reconciliación con datos reales ──")

for vista, d in (("actual", p["actual"]), ("cerrado", p["cerrado_anterior"])):
    total = d["litros_actual_mtd"] if vista == "actual" else d["litros"]
    suma_can = sum(n["litros_actual"] for n in d["por_canal"] if n["nivel"] == "canal")
    chk(f"12. [{vista}] Los canales reconcilian con el total",
        abs(suma_can - total) < 0.5, f"{round(suma_can,1)} vs {total}")
    suma_cat = sum(n["litros_actual"] for n in d["por_categoria"])
    chk(f"13. [{vista}] Las categorías reconcilian con el total",
        abs(suma_cat - total) < 0.5, f"{round(suma_cat,1)} vs {total}")
    hijos = [n for n in d["por_categoria"] if n.get("hijos")]
    if hijos:
        n0 = hijos[0]
        chk(f"13b. [{vista}] Los hijos reconcilian con su padre",
            abs(sum(h["litros_actual"] for h in n0["hijos"]) - n0["litros_actual"]) < 0.5,
            f"{n0['clave']}")

sinc = [n for n in p["actual"]["por_categoria"] if n["clave"] == S._IA_SIN_CLASIF]
chk("14. 'Sin clasificación' queda visible y cuantificado, no descartado",
    bool(sinc) or p["diagnostico"]["litros_sin_categoria"] == 0,
    f"{p['diagnostico']['litros_sin_categoria']} L · "
    f"{p['diagnostico']['skus_sin_maestro_total']} SKU fuera del maestro")
chk("14b. El diagnóstico lista los SKU sin maestro",
    isinstance(p["diagnostico"]["skus_sin_maestro"], list))

# El agregado On Premise + VTK es una fila aparte, no reemplaza a los tres canales
agg = [n for n in p["actual"]["por_canal"] if n["nivel"] == "canal_agregado"]
if agg:
    comp = agg[0]["componentes"]
    suma = sum(n["litros_actual"] for n in p["actual"]["por_canal"] if n["clave"] in comp)
    chk("14c. 'On Premise + VTK' suma sus tres componentes",
        abs(suma - agg[0]["litros_actual"]) < 0.5, str(comp))
    chk("14d. Los tres canales siguen disponibles por separado",
        all(any(n["clave"] == c for n in p["actual"]["por_canal"]) for c in comp))


# ═══════════════════════════════════════════════════════
print("\n── 15-17. Cascada de litros, jerarquía y caché ──")

d_act, _ = S._ia_rango(S._ia_mes_vivo())
crudo_act = S._leer_ventas_min(S.INPUTS / "ventas.csv", S._IA_COLS)
chk("15. Los litros usan la misma cascada que Semanal y Sell Out",
    "_litros_por_linea" in open(S.__file__, encoding="utf-8").read().split("def _ia_leer")[1][:3000],
    "_ia_leer llama a _litros_por_linea, no reimplementa el cálculo")

niveles = {n["nivel"] for n in p["actual"]["por_categoria"]}
chk("16. El primer nivel de la jerarquía es Categoría", niveles == {"categoria"}, str(niveles))
n0 = p["actual"]["por_categoria"][0]
ruta = []
nodo = n0
while nodo:
    ruta.append(nodo["nivel"])
    nodo = (nodo.get("hijos") or [None])[0]
chk("16b. La jerarquía es Categoría → Segmento → Línea → Marca",
    ruta[:4] == list(S._IA_NIVELES), " → ".join(ruta))
chk("16c. Los tops sólo viajan en el primer nivel",
    "top_caidas" in n0 and all("top_caidas" not in h for h in (n0.get("hijos") or [])),
    "los niveles profundos se piden al endpoint de detalle")

import time
t = time.time(); S._ia_cacheado(); dt = time.time() - t
chk("17. La segunda llamada sale de caché", dt < 0.2, f"{dt:.3f}s")
chk("17b. La clave de caché incluye fuentes y maestro",
    len(S._ia_sig()) == 2 and len(S._ia_sig()[1]) == 3,
    "ventas + historial + cierres, y maestro/feriados/clientes")


# ═══════════════════════════════════════════════════════
print("\n── 18. El endpoint Semanal existente no cambia ──")

sem = S._semanal_actual()
hist = S._semanal_historico()
chk("18. /api/gerencia/semanal sigue calculando igual",
    isinstance(sem, dict) and "periodo" in sem and isinstance(hist.get("meses"), list),
    f"mes en curso {sem.get('periodo')} · {len(hist.get('meses') or [])} meses cerrados")
chk("18b. El interanual no toca los KPI de Semanal",
    [k["id"] for k in S._SEMANAL_KPIS] ==
    ["facturacion", "litros", "ccc_tradicional", "ccc_autoservicio", "ccc_onpremise"])


print("\n" + "=" * 55)
print(f"{OK} OK, {len(FALLOS)} fallas")
for f in FALLOS:
    print("  -", f)
sys.exit(1 if FALLOS else 0)
