# -*- coding: utf-8 -*-
"""
MOTOR DE ANÁLISIS DE ACCIONES COMERCIALES — ORBIT Matinal Peñaflor
==================================================================

Responde "¿qué pasó con esta acción?" para la tarjeta *Análisis de la acción* del Explorador.

QUÉ ES Y QUÉ NO ES
------------------
Esto NO es una tercera lógica de acciones. Es la capa de análisis que se apoya en las dos que
ya existen y no las reemplaza:

  * el **catálogo de reglas** del mes (`mod_acciones_explorador.json`, armado del Excel) dice
    QUÉ ofrece cada acción: canal, productos, escalas y descuentos. De ahí sale la regla.
  * la **preparación de ventas** (`server_orbit._acc_preparar_from_df`) es la única lectura
    del ERP: `_pct`, `_desc`, `_litros`, `_cat`, `_marca`, `_nro`, `_seg`... De ahí salen los
    datos. Este módulo no vuelve a parsear nada.

Acá vive sólo la parte pura: recibe DataFrames ya preparados y devuelve números. Sin Flask,
sin I/O y sin rutas — igual que `motor_11t` y `motor_padron`. Eso es lo que lo hace testeable
con datos sintéticos sin levantar el servidor.

ATRIBUCIÓN: POR QUÉ NO HAY TAG EXACTO
-------------------------------------
Se auditaron las columnas del ERP buscando un identificador inequívoco de acción
(2026-08-18, sobre ventas.csv de agosto):

  * `Promociones` tiene 2 valores: **19 = Spirits/Diageo** (Gordon's, Smirnoff, JW, Tanqueray)
    y **21 = resto del portfolio**. Es la agrupación del proveedor, no la acción: el 21 solo
    aparece con 17 porcentajes de descuento distintos.
  * `Tags` / `EtiquetaItem` traen `%10` / `%20` + "PEÑAFLOR GRUPO OBJETIVO". El `%20` aparece
    con TODOS los descuentos de 0 a 100, así que tampoco marca la acción.
  * `ComboCodigo` y `Etiqueta` vienen vacías en el 100% de las filas.

Conclusión: hoy la atribución sólo puede ser por REGLA (canal + productos + cantidades +
descuento). `buscar_tag_accion()` queda implementada igual para que, si mañana el ERP empieza
a emitir el código de la acción, la atribución exacta entre sola sin tocar el resto.

Por eso el payload informa siempre `metodo`:

    exact_tag      el ERP identificó la acción (hoy no ocurre)
    rule_discount  coincidencia verificable de canal + productos + descuento
    ambiguous      hay otra acción del mes indistinguible con esos mismos criterios

Y por eso los textos dicen "ventas asociadas a la acción" y "clientes incorporados dentro del
alcance", nunca que la acción causó el crecimiento: con atribución por regla hay asociación,
no causalidad demostrada.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

# Métodos de atribución, de mayor a menor confianza.
METODO_TAG = "exact_tag"
METODO_REGLA = "rule_discount"
METODO_AMBIGUO = "ambiguous"

#: Tolerancia al comparar el % de descuento de la línea contra el de la escala. El ERP
#: redondea a 1 decimal y `_pct` se calcula desde valorDescuento; 0.6 pp cubre el redondeo
#: sin llegar a confundir tramos vecinos (el más angosto del mes es 4% vs 5%).
TOL_PCT = 0.6

#: Prioridad al etiquetar un cliente con UNA sola clasificación (Top 5). Las categorías no
#: son excluyentes entre sí —alguien nuevo para Peñaflor es también nuevo para la marca— así
#: que se muestra la más informativa.
ORDEN_CLASIFICACION = ("nuevo_penaflor", "reactivado", "nuevo_categoria",
                       "nuevo_marca", "recurrente")

ETIQUETA_CLASIFICACION = {
    "nuevo_penaflor":  "Nuevo",
    "reactivado":      "Reactivado",
    "nuevo_categoria": "Nuevo en categoría",
    "nuevo_marca":     "Nuevo en marca",
    "recurrente":      "Recurrente",
}


def norm(s) -> str:
    """Mayúsculas, sin acentos, sin puntuación. Espejo de `server_orbit._acc_norm`:
    los apóstrofes se ELIMINAN para que Gordon's / Gordon´s / Gordons matcheen igual."""
    s = str(s or "").upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[\'’‘´`]", "", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ─────────────────────────────────────────────
# REGLA DE LA ACCIÓN (leída del catálogo del explorador)
# ─────────────────────────────────────────────

def tramos_de(sub) -> list:
    """Porcentajes de descuento declarados por la acción, en 0-100.

    Sale de las escalas del catálogo, no de una lista paralela: si el Excel cambia el
    descuento el mes que viene, la atribución lo sigue solo. Las escalas de bonificación
    (5+1, sin cargo) no tienen % y no aportan tramo."""
    out = []
    for seg in sub.get("segmentos") or []:
        for e in seg.get("escalas") or []:
            d = e.get("descuento")
            if d is None:
                continue
            try:
                out.append(round(float(d) * 100, 2))
            except (TypeError, ValueError):
                continue
    return sorted(set(out))


def marcas_de(sub) -> list:
    """Nombres de producto/marca/línea del catálogo de la acción, tal como los declara el
    Excel. No se resuelven a SKU acá: eso lo hace el predicado, que necesita el maestro."""
    out = []
    for p in sub.get("productos") or []:
        n = (p.get("nombre") or "").strip()
        if n:
            out.append(n)
    return out


def segmentos_de(sub) -> list:
    """Segmentos de cliente que declara la acción (texto del Excel, sin canonizar)."""
    out = []
    for seg in sub.get("segmentos") or []:
        out.extend(seg.get("segmentos_cliente") or [])
        if seg.get("canal"):
            out.append(seg["canal"])
    return sorted(set(x for x in out if x))


def firma_regla(sub, canon_segmento) -> tuple:
    """Huella de la acción para detectar acciones indistinguibles entre sí.

    Dos acciones con el mismo canal canónico, el mismo alcance de producto y los mismos
    tramos de descuento no se pueden separar mirando una línea de venta. `canon_segmento`
    es la función que lleva el texto del Excel al canon del portal (TRADICIONAL,
    AUTOSERVICIO, ...); se recibe por parámetro para no duplicar acá el clasificador."""
    segs = tuple(sorted(canon_segmento(segmentos_de(sub))))
    prods = tuple(sorted(norm(m) for m in marcas_de(sub)))
    return (segs, prods, tuple(tramos_de(sub)))


def resolver_atribucion(sub, todas_las_subs, canon_segmento, tags_encontrados=0) -> dict:
    """{metodo, advertencia, colisiones}.

    `tags_encontrados` > 0 sólo si el ERP trajo el identificador de la acción en alguna
    línea; hoy es siempre 0 (ver docstring del módulo)."""
    if tags_encontrados > 0:
        return {"metodo": METODO_TAG, "advertencia": None, "colisiones": []}

    mia = firma_regla(sub, canon_segmento)
    colisiones = []
    for otra in todas_las_subs:
        if otra.get("action_id") == sub.get("action_id"):
            continue
        if firma_regla(otra, canon_segmento) == mia:
            colisiones.append(otra.get("action_id"))

    if colisiones:
        return {
            "metodo": METODO_AMBIGUO,
            "advertencia": ("No se puede separar de " + ", ".join(sorted(colisiones)) +
                            ": mismo canal, mismos productos y mismo descuento. Las líneas "
                            "se cuentan una sola vez y se informan como compartidas."),
            "colisiones": sorted(colisiones),
        }
    if not tramos_de(sub):
        return {
            "metodo": METODO_REGLA,
            "advertencia": ("La acción no declara un porcentaje de descuento, así que se "
                            "atribuye por producto y canal: puede incluir compras hechas "
                            "sin la acción."),
            "colisiones": [],
        }
    return {"metodo": METODO_REGLA, "advertencia": None, "colisiones": []}


def buscar_tag_accion(df, action_id) -> int:
    """Cuántas líneas traen el identificador de la acción en las columnas de etiqueta del ERP.

    Hoy devuelve 0 en todos los casos: ninguna columna del ERP identifica la acción (ver
    docstring del módulo). Queda para que la atribución exacta entre sola si eso cambia; es
    la razón por la que `metodo` es un dato del payload y no una constante."""
    if df is None or not len(df) or not action_id:
        return 0
    objetivo = norm(action_id)
    if not objetivo:
        return 0
    total = pd.Series(False, index=df.index)
    for col in ("_tags", "_promos"):
        if col in df.columns:
            total |= df[col].map(norm).str.contains(re.escape(objetivo), regex=True, na=False)
    return int(total.sum())


# ─────────────────────────────────────────────
# ALCANCE DE PRODUCTO
# ─────────────────────────────────────────────
#
# El Excel nombra el alcance como lo dice comercial ("VDA Superior", "VDG Super y Ultra
# Premium", "Espumante / Sidra", "Smirnoff botella"), no con códigos. El maestro 04D tiene
# exactamente esa apertura —Categoría x Segmento— así que el alcance se resuelve contra el
# maestro y no con una lista cableada que habría que mantener cada mes.
#
# Por qué importa que esto sea explícito: si el alcance no resuelve, la tarjeta mostraría 0
# litros, y un 0 acá se lee como "no hubo ventas" cuando en realidad significa "no supe qué
# productos mirar". Por eso `resolver_alcance` devuelve `resuelto` y el payload corta con una
# nota en vez de publicar ceros.

#: Palabras que sólo modifican el envase, no la marca.
_MOD_BOTELLA = "BOTELLA"
_MOD_LATA = "LATA"


def _palabras(t):
    return set(t.split())


def resolver_alcance(nombres, maestro, canon_cat, segmentos_hermanos=None):
    """Resuelve los nombres del catálogo a un alcance de producto.

    `maestro` es una lista de dicts {cod, cat, seg} del 04D (cat/seg tal como vienen).
    `canon_cat` canoniza la categoría del maestro (VDA, VDG, ESPUMANTES, ...).
    `segmentos_hermanos` son los segmentos que ya reclama otra acción de la misma categoría:
    es lo que le da sentido a "Resto segmentos" sin inventar nada.

    Devuelve {resuelto, codigos, marcas, envase, detalle}."""
    segmentos_hermanos = {norm(s) for s in (segmentos_hermanos or set())}

    # Índices del maestro: canon de categoría -> {segmento_norm -> set(codigos)}
    por_cat = {}
    for m in maestro:
        c = canon_cat(m.get("cat"))
        if not c:
            continue
        por_cat.setdefault(norm(c), {}).setdefault(norm(m.get("seg")), set()).add(str(m.get("cod")).strip())

    codigos, items, detalle = set(), [], []
    resuelto = False

    # "Espumante / Sidra" son DOS alcances en una celda: se parten antes de resolver, si no
    # el texto junto no matchea ninguna categoría y la acción queda sin alcance.
    partes = []
    for nombre in nombres:
        partes.extend(p for p in re.split(r"[/]", str(nombre or "")) if p.strip())

    for nombre in partes:
        t = norm(nombre)
        if not t:
            continue
        # El envase es del PRODUCTO, no de la acción: "NC lata" no puede dejar fuera al resto
        # de las innovaciones de la misma lista.
        envase = None
        if _MOD_BOTELLA in _palabras(t):
            envase = "botella"
            t = " ".join(w for w in t.split() if w != _MOD_BOTELLA)
        elif _MOD_LATA in _palabras(t):
            envase = "lata"
            t = " ".join(w for w in t.split() if w != _MOD_LATA)

        # ¿nombra una categoría del maestro? Se tolera singular/plural ("Espumante" vs
        # "Espumantes"), que es como alterna la fuente.
        cat_match = None
        for c in por_cat:
            if (t == c or t.startswith(c + " ") or f" {c} " in f" {t} "
                    or t == c.rstrip("S") or t + "S" == c):
                if cat_match is None or len(c) > len(cat_match):
                    cat_match = c
        if cat_match:
            resto_txt = " ".join(w for w in t.split() if w not in _palabras(cat_match))
            segs = por_cat[cat_match]
            elegidos = set()
            if "RESTO" in _palabras(resto_txt):
                elegidos = {s for s in segs if s and s not in segmentos_hermanos}
                detalle.append(f"{nombre}: {cat_match} sin {sorted(segmentos_hermanos) or 'nada'}")
            elif resto_txt.strip():
                palabras = _palabras(resto_txt)
                cand = [s for s in segs if s and _palabras(s) <= palabras]
                # "Super y Ultra Premium" contiene también la palabra "Premium" suelta: si un
                # segmento más largo ya matcheó, el corto que es subconjunto suyo se descarta.
                elegidos = {s for s in cand
                            if not any(o != s and _palabras(s) < _palabras(o) for o in cand)}
                detalle.append(f"{nombre}: {cat_match} / {sorted(elegidos)}")
            else:
                elegidos = set(segs)
                detalle.append(f"{nombre}: {cat_match} completa")
            for s in elegidos:
                codigos |= segs.get(s, set())
            if elegidos:
                resuelto = True
                continue

        # No es una categoría: se trata como marca / producto por texto. Un nombre que
        # arranca con el código de SKU ("74827 — Alma Mora ...") aporta el código: es más
        # preciso que el texto y evita depender de cómo escriba el ERP la descripción.
        if t:
            cod_ini = t.split()[0]
            if cod_ini.isdigit():
                codigos.add(cod_ini)
                resuelto = True
                detalle.append(f"{nombre}: SKU {cod_ini}")
                continue
            items.append({"texto": t, "envase": envase})
            resuelto = True
            detalle.append(f"{nombre}: marca «{t}»" + (f" ({envase})" if envase else ""))

    return {"resuelto": resuelto, "codigos": codigos, "marcas": items, "detalle": detalle}


def pred_alcance(alcance, es_botella=None):
    """Predicado (cat, linea, articulo, marca, cod) -> bool para un alcance ya resuelto.

    El envase se evalúa por producto: cada entrada de marca trae el suyo, así "Antares lata"
    y "Antares botella" pueden convivir en el catálogo sin anularse."""
    codigos = alcance.get("codigos") or set()
    items = alcance.get("marcas") or []

    def _envase_ok(envase, cat, articulo):
        if not envase or es_botella is None:
            return True
        es_bot = bool(es_botella(cat, articulo))
        return es_bot if envase == "botella" else (not es_bot)

    def pred(cat, linea, articulo, marca, cod=None):
        if cod is not None and str(cod).strip() in codigos:
            return True
        if items:
            txt = norm(f"{marca or ''} {articulo or ''} {linea or ''}")
            for it in items:
                if it["texto"] in txt and _envase_ok(it["envase"], cat, articulo):
                    return True
        return False

    return pred


# ─────────────────────────────────────────────
# MÁSCARAS: QUÉ LÍNEA PERTENECE A LA ACCIÓN
# ─────────────────────────────────────────────

def mask_descuento(df, tramos) -> pd.Series:
    """La línea aplicó alguno de los tramos de la acción.

    Sin tramos (bonificación / sin cargo) no hay % que comparar: se pide al menos que la
    línea tenga descuento, igual criterio que `server_orbit._acc_mask_usa_accion`."""
    if not len(df):
        return pd.Series(dtype=bool, index=df.index)
    if not tramos:
        return df["_desc"] > 0
    m = pd.Series(False, index=df.index)
    for t in tramos:
        m |= (df["_pct"] - t).abs() <= TOL_PCT
    return m


def mask_segmento(df, segs_canon) -> pd.Series:
    """La línea pertenece a un cliente del canal de la acción. Sin canal declarado, no filtra."""
    if not len(df):
        return pd.Series(dtype=bool, index=df.index)
    if not segs_canon:
        return pd.Series(True, index=df.index)
    return df["_seg"].isin(list(segs_canon))


def mask_productos(df, pred) -> pd.Series:
    """La línea es de un producto del alcance de la acción. `pred` es el predicado que
    construye server_orbit desde el maestro; acá sólo se aplica."""
    if not len(df):
        return pd.Series(dtype=bool, index=df.index)
    return pd.Series(
        [bool(pred(c, l, a, m, cod)) for c, l, a, m, cod in
         zip(df["_cat"], df["_linea"], df["_art"], df["_marca"], df["_cod"])],
        index=df.index)


# ─────────────────────────────────────────────
# CAJA MIXTA 3+3 (AGO26-TRAD-NC)
# ─────────────────────────────────────────────
#
# Ser elegible NO es haber usado la acción. Acá se valida el cumplimiento REAL, y se valida
# a nivel NroComprobante porque la mecánica es una caja: las 6 botellas tienen que venir en
# la misma compra. `CantBase` ya viene en BOTELLAS/UNIDADES (regla oficial documentada en
# motor_11t), así que se suma tal cual, sin multiplicar por unidades por caja.

def comprobantes_caja_mixta(df, marca_de_linea, pct_objetivo=15.0, botellas=3,
                            solo_botella=None) -> pd.DataFrame:
    """Comprobantes que cumplen la caja mixta: `botellas` de una marca + `botellas` de otra
    marca distinta, ambas del catálogo, con el descuento de la acción, en el MISMO comprobante.

    `marca_de_linea` mapea cada fila a la marca participante (o None). `solo_botella`, si se
    pasa, descarta latas/RTD.

    Devuelve un DataFrame [_nro, _cli, marcas, botellas_accion] con un renglón por
    comprobante que cumple. Lo que NO cumple queda afuera y no se cuenta:
      * 6 botellas de una sola marca (falta la segunda marca);
      * 3+3 repartidos en comprobantes distintos (se agrupa por _nro);
      * descuento distinto al de la acción;
      * productos fuera del catálogo;
      * devoluciones o neto <= 0 (ya filtradas en la preparación)."""
    vacio = pd.DataFrame(columns=["_nro", "_cli", "marcas", "botellas_accion"])
    if df is None or not len(df):
        return vacio

    d = df.copy()
    d["_marca_accion"] = [marca_de_linea(m, a, c) for m, a, c in
                          zip(d["_marca"], d["_art"], d["_cod"])]
    d = d[d["_marca_accion"].notna()]
    if solo_botella is not None and len(d):
        d = d[[bool(solo_botella(c, a)) for c, a in zip(d["_cat"], d["_art"])]]
    if not len(d):
        return vacio
    # El descuento se exige por línea: una caja donde sólo la mitad llevó el 15% no es la
    # acción, es otra compra que casualmente tiene dos marcas del catálogo.
    d = d[(d["_pct"] - pct_objetivo).abs() <= TOL_PCT]
    if not len(d):
        return vacio

    # Botellas netas por comprobante y marca. Un comprobante con dos SKU de Alma Mora suma
    # las dos líneas: son la misma marca, no dos marcas distintas.
    g = (d.groupby(["_nro", "_cli", "_marca_accion"], dropna=False)["_cant"]
           .sum().reset_index(name="bot"))
    g = g[g["bot"] >= botellas]
    if not len(g):
        return vacio

    filas = []
    for (nro, cli), sub in g.groupby(["_nro", "_cli"], dropna=False):
        marcas = sorted(sub["_marca_accion"].unique())
        if len(marcas) < 2:            # 6 de una sola marca: no califica
            continue
        filas.append({"_nro": nro, "_cli": cli, "marcas": marcas,
                      "botellas_accion": float(sub["bot"].sum())})
    return pd.DataFrame(filas) if filas else vacio


# ─────────────────────────────────────────────
# CLASIFICACIÓN DE CLIENTES
# ─────────────────────────────────────────────

def clasificar_clientes(ids_accion, ids_comparado_todo, ids_comparado_categoria,
                        ids_comparado_marca, ids_ventana_historica) -> dict:
    """{cliente_id: {flags..., clasificacion}} para los que usaron la acción.

    Dos ejes independientes, a propósito:

      * **relación con Peñaflor**: recurrente (compró en el período comparado) / reactivado
        (no compró entonces pero sí en los 12 meses previos) / nuevo para Peñaflor (no compró
        ni entonces ni antes). Son excluyentes entre sí.
      * **novedad de producto**: nuevo para la categoría y nuevo para la marca.

    Nuevo-para-Peñaflor se cruza contra la ventana histórica y no sólo contra el período
    comparado: sin eso, cualquiera que se hubiera salteado un mes figuraba como cliente nuevo
    y el número no significaba nada.

    Importante: acá sólo entra quien USÓ la acción. Estar en el universo elegible no
    convierte a nadie en cliente nuevo."""
    out = {}
    for c in ids_accion:
        recurrente = c in ids_comparado_todo
        reactivado = (not recurrente) and (c in ids_ventana_historica)
        nuevo_pf = (not recurrente) and (not reactivado)
        flags = {
            "recurrente":      recurrente,
            "reactivado":      reactivado,
            "nuevo_penaflor":  nuevo_pf,
            "nuevo_categoria": c not in ids_comparado_categoria,
            "nuevo_marca":     c not in ids_comparado_marca,
        }
        etiqueta = next((k for k in ORDEN_CLASIFICACION if flags.get(k)), "recurrente")
        flags["clasificacion"] = etiqueta
        flags["clasificacion_label"] = ETIQUETA_CLASIFICACION[etiqueta]
        out[c] = flags
    return out


def contar_clasificacion(clasif) -> dict:
    """Totales por flag. Cada cliente puede sumar a más de una columna del eje de producto."""
    keys = ("nuevo_penaflor", "reactivado", "recurrente", "nuevo_categoria", "nuevo_marca")
    return {k: int(sum(1 for v in clasif.values() if v.get(k))) for k in keys}


# ─────────────────────────────────────────────
# EMBUDO
# ─────────────────────────────────────────────

def embudo(universo_potencial, ids_accion, ids_convertidos) -> dict:
    """Universo → usaron → convirtieron. Devuelve cantidades, nunca la lista de clientes:
    el potencial de una acción de canal son miles de filas y no entran en una tarjeta."""
    usaron = len(ids_accion)
    convertidos = len(ids_convertidos)
    universo = int(universo_potencial or 0)
    return {
        "universo_potencial":   universo,
        "utilizaron_accion":    int(usaron),
        "convertidos":          int(convertidos),
        "conversion_pct":       round(usaron / universo * 100, 1) if universo else 0.0,
        "potenciales_restantes": int(max(universo - usaron, 0)),
    }


# ─────────────────────────────────────────────
# 11 TITULARES
# ─────────────────────────────────────────────

def impacto_once_titulares(df_periodo, mask_accion, sku_titular, segmento_por_cliente,
                           umbrales) -> dict:
    """Impactos 11T asociados / habilitados / acompañados por la acción.

    Un "impacto" es un par (cliente, titular) cubierto: el cliente alcanzó el mínimo de
    botellas de SU segmento sumando todas sus líneas válidas del período (regla oficial de
    motor_11t, el mínimo se aplica DESPUÉS de sumar).

      * **asociado**  : el par quedó cubierto y la acción aportó botellas.
      * **habilitado**: además, sacando las botellas de la acción el cliente NO llegaba al
        umbral. La acción hizo la diferencia.
      * **acompañado**: llegaba igual sin la acción. La acción sumó, pero no fue lo que
        cerró el titular. No se lo cuenta como habilitado.

    El titular sale de la matriz oficial SKU→titular (`sku_titular`), nunca del nombre de la
    marca. Un SKU fuera de la matriz no es 11T y no suma."""
    base = {"aplica": False, "impactos_asociados": None, "impactos_habilitados": None,
            "impactos_acompanados": None, "detalle": []}
    if df_periodo is None or not len(df_periodo) or not sku_titular:
        return base

    d = df_periodo.copy()
    d["_titular"] = pd.to_numeric(d["_cod"], errors="coerce").map(sku_titular)
    d = d[d["_titular"].notna()]
    if not len(d):
        return base

    d["_acc"] = mask_accion.reindex(d.index).fillna(False)
    if not bool(d["_acc"].any()):
        # La acción no toca ningún SKU del 11T en este período: la sección no aplica.
        return base

    # Botellas del período por (cliente, titular) y, aparte, las que aportó la acción.
    g = d.groupby(["_cli", "_titular"]).agg(bot_total=("_cant", "sum")).reset_index()
    acc = (d[d["_acc"]].groupby(["_cli", "_titular"])
           .agg(bot_accion=("_cant", "sum")).reset_index())
    g = g.merge(acc, on=["_cli", "_titular"], how="left")
    g["bot_accion"] = g["bot_accion"].fillna(0.0)

    asociados = habilitados = acompanados = 0
    detalle = []
    for _, r in g.iterrows():
        seg = segmento_por_cliente.get(int(r["_cli"]))
        umbral = umbrales.get(seg)
        if not umbral:                       # segmento sin umbral 11T: fuera de superficie
            continue
        if r["bot_total"] < umbral:          # el titular no quedó cubierto
            continue
        if r["bot_accion"] <= 0:             # cubierto, pero sin aporte de la acción
            continue
        asociados += 1
        if (r["bot_total"] - r["bot_accion"]) < umbral:
            habilitados += 1
            tipo = "habilitado"
        else:
            acompanados += 1
            tipo = "acompanado"
        detalle.append({"cliente_id": int(r["_cli"]), "titular": r["_titular"],
                        "botellas_total": r["bot_total"], "botellas_accion": r["bot_accion"],
                        "umbral": int(umbral), "tipo": tipo})
    return {"aplica": True, "impactos_asociados": asociados,
            "impactos_habilitados": habilitados, "impactos_acompanados": acompanados,
            "detalle": detalle}


# ─────────────────────────────────────────────
# TOP 5
# ─────────────────────────────────────────────

def top_clientes(df_accion, clasif, modo="compradores", limite=5) -> list:
    """Top de clientes de la acción. SIEMPRE acotado a `limite` (5): la tarjeta es para
    decidir rápido, no para auditar la cartera.

      * `compradores`  : ordena por litros asociados y desempata por importe neto.
      * `incorporaciones`: primero los que entran por primera vez (nuevo Peñaflor,
        reactivado, nuevo en categoría o en marca) y recién después por litros."""
    if df_accion is None or not len(df_accion):
        return []
    g = (df_accion.groupby("_cli")
         .agg(litros=("_litros", "sum"),
              importe_neto=("_imp_neto", "sum"),
              descuento=("_desc", "sum"),
              comprobantes=("_nro", "nunique"),
              cliente=("_clinom", "first"),
              vendedor=("_vnom", "first"),
              vendedor_cod=("_vend", "first"))
         .reset_index())
    g["_orden_inc"] = [
        0 if (clasif.get(int(c), {}).get("clasificacion") != "recurrente") else 1
        for c in g["_cli"]]
    if modo == "incorporaciones":
        g = g.sort_values(["_orden_inc", "litros", "importe_neto"], ascending=[True, False, False])
    else:
        g = g.sort_values(["litros", "importe_neto"], ascending=[False, False])
    out = []
    for _, r in g.head(limite).iterrows():
        cid = int(r["_cli"])
        cl = clasif.get(cid, {})
        vc = r["vendedor_cod"]
        out.append({
            "cliente_id":     cid,
            "cliente":        str(r["cliente"] or ""),
            "vendedor_id":    f"V{int(vc)}" if pd.notna(vc) else "",
            "vendedor":       str(r["vendedor"] or ""),
            "litros":         round(float(r["litros"]), 1),
            "comprobantes":   int(r["comprobantes"]),
            "importe_neto":   round(float(r["importe_neto"]), 2),
            "descuento":      round(float(r["descuento"]), 2),
            "clasificacion":  cl.get("clasificacion", "recurrente"),
            "clasificacion_label": cl.get("clasificacion_label", "Recurrente"),
        })
    return out


# ─────────────────────────────────────────────
# INSIGHT DETERMINÍSTICO
# ─────────────────────────────────────────────

def _n(x):
    """Entero con separador de miles argentino."""
    return f"{int(round(x)):,}".replace(",", ".")


def _pct(x, dec=1):
    return f"{x:.{dec}f}".replace(".", ",")


def construir_insight(kpis, embudo_d, atribucion, periodo_txt) -> str:
    """Conclusión corta armada con reglas y datos, sin IA y sin adjetivos.

    Deliberadamente dice "asociadas a la acción" y "durante la vigencia": con atribución por
    regla hay asociación entre la venta y el descuento, no prueba de que la acción la haya
    causado. Afirmar causalidad sería inventar un dato que la fuente no tiene."""
    cl = kpis.get("clientes_accion") or 0
    if not cl:
        return (f"Ninguna compra {periodo_txt} cumple las condiciones de la acción. "
                "No hay uso para analizar.")

    partes = [f"{_n(cl)} cliente{'s' if cl != 1 else ''} "
              f"{'utilizaron' if cl != 1 else 'utilizó'} la acción "
              f"en {_n(kpis.get('comprobantes_accion') or 0)} comprobante"
              f"{'s' if (kpis.get('comprobantes_accion') or 0) != 1 else ''}."]

    nuevos_cat = kpis.get("clientes_nuevos_categoria") or 0
    if nuevos_cat:
        partes.append(f"{_n(nuevos_cat)} no compraba{'n' if nuevos_cat != 1 else ''} "
                      f"esta categoría {periodo_txt}.")

    nuevos_pf = kpis.get("clientes_nuevos_penaflor") or 0
    react = kpis.get("clientes_reactivados") or 0
    if nuevos_pf or react:
        det = []
        if nuevos_pf:
            det.append(f"{_n(nuevos_pf)} sin compras previas de Peñaflor")
        if react:
            det.append(f"{_n(react)} reactivado{'s' if react != 1 else ''}")
        partes.append("Entre ellos, " + " y ".join(det) + ".")

    part = kpis.get("participacion_litros_pct")
    if part is not None:
        partes.append(f"Las ventas asociadas a la acción representan el {_pct(part)}% "
                      f"de los litros actuales de la categoría.")

    if atribucion.get("metodo") == METODO_AMBIGUO:
        partes.append("Atribución ambigua: hay otra acción del mes con el mismo canal, "
                      "productos y descuento.")
    return " ".join(partes)
