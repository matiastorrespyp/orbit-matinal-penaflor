"""
generar_datasets_acum.py
Genera tres datasets desde ventas_acumulada.csv + fuentes secundarias.
Salidas en 04_DATASETS_ORBIT/:
  mod_cobertura_acum.csv  — cobertura por segmento (periodo acumulado)
  mod_11t_acum.csv        — 11 Titulares acumulado (autoservicio + tradicional)
  mod_planes_as.csv       — Planes AS: facturacion, cajas ganadas, sin cargo enviado
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

BASE = Path(__file__).parent
OUT  = BASE / "04_DATASETS_ORBIT"
OUT.mkdir(exist_ok=True)

VENDEDORES_EXCLUIDOS = {2, 5, 20}

# SubSegmentos que identifican AUTOSERVICIO (fuente autoritativa: clientes.xlsx columna SubSegmento)
_AS_SUBSEG = {
    "AUTOSERVICIO TRADICIONAL", "AUTOSERVICIO",
    "CADENA REGIONAL", "CADENAS REGIONALES (SAR)", "CADENAS REGIONALES (BAR)",
    "LARGE FORMAT",
}
# SubSegmentos/Ramos que identifican MAYORISTA (canal separado — NO es AUTOSERVICIO)
_MAY_SUBSEG = {
    "MAYORISTAS", "MAYORISTA", "MAYORISTA REGIONALES",
    "CASH&CARRY", "CASH & CARRY",
}
# Claves ON_PREMISE
_OP_KEYWORDS = {
    "ON PREMISE", "AWAY FROM HOME", "VINOTECA", "VINOTECAS", "BAR",
    "RESTAURANT", "RESTAURANTE", "ESTACION DE SERVICIO", "EVENTOS",
    "TEMPORADA", "CATERING", "ON DIA", "ON NOCHE",
}
# Claves TRADICIONAL
_TR_KEYWORDS = {
    "TRADITIONAL TRADE", "ALMACEN", "DESPENSA", "KIOSCO", "MAXIKIOSCO",
    "FIAMBRERIA", "CARNICERIA", "GRANJA", "PANADERIA", "CASA DE PASTAS",
    "TRADICIONAL", "PROXIMITY",
}

def _clasificar(ramo: str, subseg: str) -> str:
    s = str(subseg).upper().strip()
    r = str(ramo).upper().strip()
    # MAYORISTA: va primero para que nunca caiga en AUTOSERVICIO
    if s in _MAY_SUBSEG or r in {"CASH&CARRY", "MAYORISTAS", "MAYORISTA"}:
        return "MAYORISTA"
    # AUTOSERVICIO: SubSegmento como fuente primaria (regla de negocio)
    if s in _AS_SUBSEG or r in {"AUTOSERVICIO", "LARGE FORMAT"}:
        return "AUTOSERVICIO"
    # ON_PREMISE
    if any(k in s for k in _OP_KEYWORDS) or any(k in r for k in _OP_KEYWORDS):
        return "ON_PREMISE"
    # TRADICIONAL
    if any(k in s for k in _TR_KEYWORDS) or any(k in r for k in _TR_KEYWORDS):
        return "TRADICIONAL"
    return "OTROS"

UMBRAL = {
    "AUTOSERVICIO": 6,
    "TRADICIONAL":  3,
    "ON_PREMISE":   6,
    "VINOTECAS":    6,
    "MAYORISTA":    6,
}

MAP_11T = {
    "AUTOSERVICIO": [
        "ALMA MORA", "DADA", "LOS ARBOLES", "TRAPICHE RESERVA", "ALARIS",
        "FINCA LAS MORAS", "DON DAVID", "GORDON'S FLAVOURS", "SMIRNOFF FLAVOURS",
        "ANTARES", "SMIRNOFF ICE",
    ],
    "TRADICIONAL": [
        "ALMA MORA", "DON DAVID", "FOND DE CAVE", "CAZADOR",
        "JW BLACK", "JW RED", "MASCOTA", "NC ESPUMANTES",
        "TRAPICHE MEDALLA", "TRAPICHE RESERVA",
    ],
}

MARCA_ALIASES = {
    "ALMA MORA":         ["ALMA MORA", "AM"],
    "DON DAVID":         ["DON DAVID"],
    "CAZADOR":           ["CAZADOR"],
    "JW BLACK":          ["JW BLACK", "JOHNNIE WALKER BLACK"],
    "JW RED":            ["JW RED", "JOHNNIE WALKER RED"],
    "MASCOTA":           ["MASCOTA", "LA MASCOTA"],
    "NC ESPUMANTES":     ["NC ESPUMANTES", "NAVARRO CORREAS", "NC SPARK", "NC BRUT", "NC NATURE", "NC ROSE"],
    "TRAPICHE MEDALLA":  ["TRAPICHE MEDALLA", "GRAN MEDALLA", "MEDALLA"],
    "TRAPICHE RESERVA":  ["TRAPICHE RESERVA"],
    "ALARIS":            ["ALARIS", "TRAPICHE ALARIS"],
    "FOND DE CAVE":      ["FOND DE CAVE", "FOND CAVE"],
    "DADA":              ["DADA"],
    "LOS ARBOLES":       ["LOS ARBOLES"],
    "FINCA LAS MORAS":   ["FINCA LAS MORAS", "F LAS MORAS", "FLM"],
    "GORDON'S FLAVOURS": ["GORDON'S FLAVOURS", "GORDONS FLAVOURS", "GORDON'S PINK",
                          "GORDONS PINK", "GORDONS TROPICAL", "GORDON'S TROPICAL"],
    "SMIRNOFF FLAVOURS": ["SMIRNOFF FLAVOURS", "SMIRNOFF SANDIA", "SMIRNOFF MANZANA",
                          "SMIRNOFF RASPBERRY", "SMIRNOFF GREENAPPLE", "SMIRNOFF TROPICAL",
                          "SMIRNOFF RASPBERRY DO"],
    "SMIRNOFF ICE":      ["SMIRNOFF ICE", "SMF ICE", "SMIR ICE"],
    "ANTARES":           ["ANTARES"],
}

# alias_lookup: texto_marca_upper -> marca_objetivo
ALIAS_LOOKUP = {}
for _mo, _aliases in MARCA_ALIASES.items():
    for _a in _aliases:
        ALIAS_LOOKUP[_a.upper().strip()] = _mo

# Innovaciones: codigo_articulo → nombre_comercial
INOV_PRODUCTOS = {
    14620: "FRIZZE MANXANA POP 6X1000",
    60020: "ANTARES XPA LATA 6X473",
    74813: "DADA EXTRA BRUT 6X750",
    80094: "NC SPARK EXTRA BRUT LATA 4X6X355",
    14619: "FRIZZE BUBBLE MOOD 6X1000",
    74830: "DADA SIDRA 6X750",
    30139: "GORDONS TROPICAL FRUITS 6X700",
    74749: "INTOCABLES DOUBLE OAK 6X750",
    44396: "BLEND DE EXTREMOS PN 6X750",
    14425: "TERMIDOR BLANCO DULCE 12X1LT",
    42376: "DON DAVID RED BLEND 6X750",
    74814: "CAZADOR MALBEC 6X750",
    74815: "CAZADOR CAB SAU 6X750",
    74816: "CAZADOR BLANCO DULCE 6X750",
    74827: "ALMA MORA BLANCO DULCE LOW 6X750",
    74840: "TRAPICHE DULCE COSECHA TINTO 6X750",
    74786: "EL BAUTISMO CABERNET 6X750",
}
VENDEDORES_ACTIVOS_INOV = [3, 4, 6, 7, 8, 9, 10]


# ─────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────

def cargar_ventas_acum():
    p = BASE / "01_INPUTS" / "ventas_acumulada.csv"
    df = pd.read_csv(p, encoding="latin1", sep=None, engine="python")
    df["CantBase"] = pd.to_numeric(df["CantBase"], errors="coerce").fillna(0)
    df["ImporteNetoItem"] = (
        df["ImporteNetoItem"].astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["ImporteNetoItem"] = pd.to_numeric(df["ImporteNetoItem"], errors="coerce").fillna(0)
    df["Descuento_pct"] = (
        df["Descuento"].astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["Descuento_pct"] = pd.to_numeric(df["Descuento_pct"], errors="coerce").fillna(0)
    df["CodVendedor"] = pd.to_numeric(df["CodVendedor"], errors="coerce")
    df["Cliente"] = pd.to_numeric(df["Cliente"], errors="coerce")
    df = df[~df["CodVendedor"].isin(VENDEDORES_EXCLUIDOS)]
    return df


def cargar_clientes():
    p = BASE / "01_INPUTS" / "clientes.xlsx"
    df = pd.read_excel(p)
    df["codven"] = pd.to_numeric(df["codven"], errors="coerce")
    df["Codigo"] = pd.to_numeric(df["Codigo"], errors="coerce")
    df = df[~df["codven"].isin(VENDEDORES_EXCLUIDOS)]
    sub_col = next((c for c in df.columns if "subseg" in c.lower() or "subramo" in c.lower()), None)
    df["_seg"] = df.apply(
        lambda r: _clasificar(str(r.get("Ramo", "")), str(r.get(sub_col, "") if sub_col else "")), axis=1
    )
    return df


def cargar_planes_as_bbdd():
    p = BASE / "01_INPUTS" / "PLANES_AS" / "Reconocimiento Plan As.xlsx"
    raw = pd.read_excel(p, sheet_name="BBDD", header=None)
    # Header real en fila indice 2; datos desde indice 3
    data = raw.iloc[3:].copy()
    data.columns = range(data.shape[1])
    col_map = {
        1:  "cliente_id",
        3:  "cliente_nombre",
        8:  "plan_as",
        14: "total_facturado",
        15: "dcto_plan",
        16: "cant_cajas",
        17: "tope",
        18: "cant_cajas_tope",
        19: "sc_alaris",
        20: "sc_alma_mora",
        21: "sc_frizze",
        22: "sc_antares_ipa",
        23: "sc_smf_flavours",
        24: "sc_total_ganado",
    }
    df = data[list(col_map.keys())].rename(columns=col_map)
    df["cliente_id"] = pd.to_numeric(df["cliente_id"], errors="coerce")
    for c in ["total_facturado", "dcto_plan", "cant_cajas", "tope",
              "cant_cajas_tope", "sc_alaris", "sc_alma_mora", "sc_frizze",
              "sc_antares_ipa", "sc_smf_flavours", "sc_total_ganado"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df = df.dropna(subset=["cliente_id"])
    df["cliente_id"] = df["cliente_id"].astype(int)
    df["cliente_nombre"] = df["cliente_nombre"].astype(str).str.strip()
    df["plan_as"] = df["plan_as"].astype(str).str.strip()

    # Calcular escala_actual desde hoja ESCALA
    try:
        esc = pd.read_excel(p, sheet_name="ESCALA", header=None)
        # Fila 0: encabezado "ESCALA / LC / SEGMENTO / PRECIO / 0.1(Gold) / 0.08(Silver) / 0.06(Inicial) / Reconocimiento"
        esc_data = esc.iloc[1:].copy()
        esc_data.columns = range(esc_data.shape[1])
        esc_col_map = {1: "escala_num", 5: "thresh_gold", 6: "thresh_silver", 7: "thresh_inicial"}
        esc_df = esc_data[list(esc_col_map.keys())].rename(columns=esc_col_map)
        for c in ["escala_num", "thresh_gold", "thresh_silver", "thresh_inicial"]:
            esc_df[c] = pd.to_numeric(esc_df[c], errors="coerce")
        esc_df = esc_df.dropna(subset=["escala_num"])

        def _calc_escala(row):
            plan = str(row["plan_as"]).strip().lower()
            fact = float(row["total_facturado"])
            if "gold" in plan:
                col = "thresh_gold"
            elif "silver" in plan:
                col = "thresh_silver"
            else:
                col = "thresh_inicial"
            validas = esc_df[esc_df[col].notna() & (esc_df[col] <= fact)]
            if validas.empty:
                return 0
            return int(validas["escala_num"].max())

        df["escala_actual"] = df.apply(_calc_escala, axis=1)
        df["escala_max"] = df["plan_as"].str.lower().apply(
            lambda p: int(esc_df[esc_df["thresh_gold"].notna()]["escala_num"].max()) if "gold" in p
            else int(esc_df[esc_df["thresh_silver"].notna()]["escala_num"].max()) if "silver" in p
            else int(esc_df[esc_df["thresh_inicial"].notna()]["escala_num"].max())
        )
    except Exception as e:
        print(f"  Advertencia escala: {e}")
        df["escala_actual"] = 0
        df["escala_max"] = 0

    return df


def cargar_maestro_productos():
    p = BASE / "01_INPUTS" / "04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx"
    df = pd.read_excel(p, header=2)
    df = df.iloc[1:].copy()
    df.columns = ["Bodega", "Segmento", "Linea_Comercial", "Codigo", "Categoria", "Descripcion", "Lts_caja", "UxC"]
    df["Codigo"] = pd.to_numeric(df["Codigo"], errors="coerce")
    df["Lts_caja"] = pd.to_numeric(df["Lts_caja"], errors="coerce").fillna(0)
    return df.dropna(subset=["Codigo"])


# ─────────────────────────────────────────────
# MOD COBERTURA ACUM
# ─────────────────────────────────────────────

def generar_cobertura_acum(ventas, clientes):
    cart = clientes[["Codigo", "codven", "Vendedor", "_seg"]].rename(
        columns={"Codigo": "cliente_id", "codven": "vendedor_codigo",
                 "Vendedor": "vendedor_nombre", "_seg": "segmento"}
    ).copy()
    cart = cart[cart["segmento"] != "OTROS"]
    # V3 no trabaja AUTOSERVICIO
    cart = cart[~((cart["vendedor_codigo"] == 3) & (cart["segmento"] == "AUTOSERVICIO"))]

    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v_agg = (v.groupby(["Cliente", "CodVendedor"])["CantBase"]
               .sum().reset_index()
               .rename(columns={"Cliente": "cliente_id", "CodVendedor": "vendedor_codigo",
                                "CantBase": "cant_base_acum"}))

    merged = cart.merge(v_agg, on=["cliente_id", "vendedor_codigo"], how="left")
    merged["cant_base_acum"] = merged["cant_base_acum"].fillna(0)
    merged["umbral"] = merged["segmento"].map(UMBRAL).fillna(3)
    merged["cubierto"] = (merged["cant_base_acum"] >= merged["umbral"]).astype(int)

    agg = merged.groupby(["vendedor_codigo", "vendedor_nombre", "segmento"]).agg(
        cartera=("cliente_id", "count"),
        cubiertos=("cubierto", "sum"),
    ).reset_index()
    agg["sin_cobertura"] = agg["cartera"] - agg["cubiertos"]
    agg["pct_cobertura"] = (agg["cubiertos"] / agg["cartera"].replace(0, np.nan)).round(4).fillna(0)
    agg["fecha_calculo"] = datetime.now().strftime("%Y-%m-%d")
    agg = agg.sort_values(["vendedor_codigo", "segmento"])
    return agg


# ─────────────────────────────────────────────
# MOD 11T ACUM
# ─────────────────────────────────────────────

def generar_11t_acum(ventas, clientes):
    cart = clientes[["Codigo", "codven", "Vendedor", "_seg"]].rename(
        columns={"Codigo": "cliente_id", "codven": "vendedor_codigo",
                 "Vendedor": "vendedor_nombre", "_seg": "segmento_11t"}
    ).copy()
    cart = cart[cart["segmento_11t"].isin(["AUTOSERVICIO", "TRADICIONAL"])]
    # V3 no tiene autoservicio en 11T
    cart = cart[~((cart["vendedor_codigo"] == 3) & (cart["segmento_11t"] == "AUTOSERVICIO"))]

    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v["marca_upper"] = v["Marca"].astype(str).str.upper().str.strip()
    v["marca_objetivo"] = v["marca_upper"].map(ALIAS_LOOKUP)
    v_valid = v[v["marca_objetivo"].notna()].copy()

    v_agg = (v_valid.groupby(["Cliente", "CodVendedor", "marca_objetivo"])["CantBase"]
             .sum().reset_index()
             .rename(columns={"Cliente": "cliente_id", "CodVendedor": "vendedor_codigo",
                              "CantBase": "cant_base_acum"}))

    fecha = datetime.now().strftime("%Y-%m-%d")
    bloques = []

    for seg, marcas in MAP_11T.items():
        cart_seg = cart[cart["segmento_11t"] == seg].copy()
        umbral = UMBRAL.get(seg, 3)

        for marca in marcas:
            comp = (v_agg[v_agg["marca_objetivo"] == marca]
                    [["cliente_id", "vendedor_codigo", "cant_base_acum"]].copy())
            merged = cart_seg.merge(comp, on=["cliente_id", "vendedor_codigo"], how="left")
            merged["cant_base_acum"] = merged["cant_base_acum"].fillna(0)
            merged["tiene_flag"] = (merged["cant_base_acum"] >= umbral).astype(int)
            merged["falta_flag"] = 1 - merged["tiene_flag"]
            merged["marca_objetivo"] = marca
            merged["segmento_11t"] = seg
            merged["fecha_calculo"] = fecha
            bloques.append(merged[["fecha_calculo", "vendedor_codigo", "vendedor_nombre",
                                   "cliente_id", "segmento_11t", "marca_objetivo",
                                   "cant_base_acum", "tiene_flag", "falta_flag"]])

    return pd.concat(bloques, ignore_index=True)


# ─────────────────────────────────────────────
# MOD PLANES AS
# ─────────────────────────────────────────────

def generar_planes_as(ventas, bbdd):
    # Vendedor principal por cliente AS (por frecuencia de ventas validas)
    v_norm = ventas[ventas["ImporteNetoItem"] > 0].copy()
    vend_cli = (v_norm.groupby(["Cliente", "CodVendedor", "Vendedor"])
                .size().reset_index(name="n")
                .sort_values("n", ascending=False)
                .drop_duplicates(subset=["Cliente"])
                .rename(columns={"Cliente": "cliente_id", "CodVendedor": "vendedor_codigo",
                                 "Vendedor": "vendedor_nombre"})[["cliente_id", "vendedor_codigo", "vendedor_nombre"]])

    # Sin cargo: filas con 100% descuento
    sc = ventas[ventas["Descuento_pct"] >= 99.9].copy()

    # Resumen sin cargo enviado por cliente × marca
    sc_det = (sc.groupby(["Cliente", "Marca"])["CantBase"]
              .sum().reset_index()
              .rename(columns={"Cliente": "cliente_id", "Marca": "marca", "CantBase": "cajas"}))

    sc_pivot = sc_det.pivot_table(
        index="cliente_id", columns="marca", values="cajas", aggfunc="sum", fill_value=0
    ).reset_index()
    sc_pivot.columns.name = None
    sc_pivot = sc_pivot.rename(columns=lambda c: f"sc_env_{c.lower().replace(' ','_').replace('(','').replace(')','')}"
                               if c != "cliente_id" else c)

    sc_total_env = sc.groupby("Cliente")["CantBase"].sum().reset_index().rename(
        columns={"Cliente": "cliente_id", "CantBase": "sc_cajas_enviadas_total"}
    )

    # SC enviados por producto Plan AS (solo productos del plan)
    _AS_MARCAS = {
        "alaris": "sc_env_alaris",
        "alma mora": "sc_env_alma_mora",
        "frizze": "sc_env_frizze",
        "antares": "sc_env_antares_ipa",
        "smirnoff": "sc_env_smf_flavours",
    }
    sc_copy = sc.copy()
    sc_copy["_marca_lower"] = sc_copy["Marca"].fillna("").str.lower()
    sc_copy["_prod_as"] = sc_copy["_marca_lower"].apply(
        lambda m: next((v for k, v in _AS_MARCAS.items() if k in m), None)
    )
    sc_plan = sc_copy[sc_copy["_prod_as"].notna()]
    sc_env_prod = {}
    for prod_col in _AS_MARCAS.values():
        sub = sc_plan[sc_plan["_prod_as"] == prod_col]
        grp = sub.groupby("Cliente")["CantBase"].sum().reset_index().rename(
            columns={"Cliente": "cliente_id", "CantBase": prod_col}
        )
        sc_env_prod[prod_col] = grp

    # Join
    df = bbdd.merge(vend_cli, on="cliente_id", how="left")
    df = df.merge(sc_total_env, on="cliente_id", how="left")
    df["sc_cajas_enviadas_total"] = df["sc_cajas_enviadas_total"].fillna(0)

    for prod_col, grp in sc_env_prod.items():
        df = df.merge(grp, on="cliente_id", how="left")
        df[prod_col] = df[prod_col].fillna(0)

    # sc_pendiente por producto Plan AS
    df["sc_pend_alaris"] = (df["sc_alaris"] - df.get("sc_env_alaris", 0)).clip(lower=0)
    df["sc_pend_alma_mora"] = (df["sc_alma_mora"] - df.get("sc_env_alma_mora", 0)).clip(lower=0)
    df["sc_pend_frizze"] = (df["sc_frizze"] - df.get("sc_env_frizze", 0)).clip(lower=0)
    df["sc_pend_antares_ipa"] = (df["sc_antares_ipa"] - df.get("sc_env_antares_ipa", 0)).clip(lower=0)
    df["sc_pend_smf_flavours"] = (df["sc_smf_flavours"] - df.get("sc_env_smf_flavours", 0)).clip(lower=0)
    df["sc_pendiente"] = (df["sc_pend_alaris"] + df["sc_pend_alma_mora"] + df["sc_pend_frizze"]
                          + df["sc_pend_antares_ipa"] + df["sc_pend_smf_flavours"])
    df["fecha_calculo"] = datetime.now().strftime("%Y-%m-%d")

    cols_out = [
        "fecha_calculo", "cliente_id", "cliente_nombre", "vendedor_codigo", "vendedor_nombre",
        "plan_as", "escala_actual", "escala_max", "total_facturado", "dcto_plan",
        "cant_cajas", "tope", "cant_cajas_tope",
        "sc_alaris", "sc_alma_mora", "sc_frizze", "sc_antares_ipa", "sc_smf_flavours",
        "sc_total_ganado",
        "sc_env_alaris", "sc_env_alma_mora", "sc_env_frizze", "sc_env_antares_ipa", "sc_env_smf_flavours",
        "sc_pend_alaris", "sc_pend_alma_mora", "sc_pend_frizze", "sc_pend_antares_ipa", "sc_pend_smf_flavours",
        "sc_cajas_enviadas_total", "sc_pendiente",
    ]
    return df[[c for c in cols_out if c in df.columns]]


# ─────────────────────────────────────────────
# MOD INNOVACIONES SEGMENTO
# ─────────────────────────────────────────────

def generar_innovaciones_segmento(ventas, clientes):
    """
    CCC de 17 productos innovación por vendedor × segmento (TRADICIONAL + AUTOSERVICIO).
    Fuente: ventas_acumulada.csv (periodo completo). V3 no AUTOSERVICIO.
    """
    SEGMENTOS = ["TRADICIONAL", "AUTOSERVICIO"]

    # Cartera por vendedor × segmento
    cart = clientes[["Codigo", "codven", "Vendedor", "_seg"]].rename(
        columns={"Codigo": "cliente_id", "codven": "vendedor_codigo",
                 "Vendedor": "vendedor_nombre", "_seg": "segmento"}
    ).copy()
    cart = cart[cart["segmento"].isin(SEGMENTOS)]
    cart = cart[cart["vendedor_codigo"].isin(VENDEDORES_ACTIVOS_INOV)]
    # V3 sin AUTOSERVICIO
    cart = cart[~((cart["vendedor_codigo"] == 3) & (cart["segmento"] == "AUTOSERVICIO"))]

    # Ventas de productos innovación
    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v["_cod"] = pd.to_numeric(v["Codigo"], errors="coerce")
    v_inov = v[v["_cod"].isin(INOV_PRODUCTOS.keys()) &
               v["CodVendedor"].isin(VENDEDORES_ACTIVOS_INOV)].copy()

    fecha = datetime.now().strftime("%Y-%m-%d")
    filas = []
    for vend_cod, grp_vend in cart.groupby("vendedor_codigo"):
        vend_nombre = grp_vend["vendedor_nombre"].iloc[0]
        for seg in SEGMENTOS:
            grp_seg = grp_vend[grp_vend["segmento"] == seg]
            if grp_seg.empty:
                continue
            cartera_ids = set(grp_seg["cliente_id"].dropna().astype(int))
            for cod, nombre in INOV_PRODUCTOS.items():
                compraron_ids = set(
                    v_inov[(v_inov["CodVendedor"] == vend_cod) & (v_inov["_cod"] == cod)]
                    ["Cliente"].dropna().astype(int)
                ) & cartera_ids
                faltantes = sorted(cartera_ids - compraron_ids)
                filas.append({
                    "fecha_ejecucion": fecha,
                    "vendedor_codigo": int(vend_cod),
                    "vendedor_nombre": vend_nombre,
                    "segmento": seg,
                    "producto_codigo": cod,
                    "producto_nombre": nombre,
                    "clientes_cartera": len(cartera_ids),
                    "clientes_compraron": len(compraron_ids),
                    "pct_cobertura": round(len(compraron_ids) / len(cartera_ids), 4) if cartera_ids else 0.0,
                    "clientes_faltantes": "|".join(str(x) for x in faltantes),
                })
    df = pd.DataFrame(filas)
    if not df.empty:
        df = df.sort_values(["vendedor_codigo", "segmento", "producto_codigo"]).reset_index(drop=True)
    return df


def generar_innovaciones_plan_as(ventas, bbdd):
    """
    Por cliente AS: cuántas y cuáles innovaciones compró en el periodo acumulado.
    """
    PENDIENTE_STOCK = "Antares P770|Antares P330"

    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v["_cod"] = pd.to_numeric(v["Codigo"], errors="coerce")
    v_inov = v[v["_cod"].isin(INOV_PRODUCTOS.keys())].copy()

    total_activas = len(INOV_PRODUCTOS)
    fecha = datetime.now().strftime("%Y-%m-%d")
    filas = []
    for _, row in bbdd.iterrows():
        cid = int(row["cliente_id"])
        compras = set(v_inov[v_inov["Cliente"] == cid]["_cod"].dropna().astype(int))
        compradas = compras & set(INOV_PRODUCTOS.keys())
        faltantes = [INOV_PRODUCTOS[c] for c in INOV_PRODUCTOS if c not in compradas]
        filas.append({
            "fecha_ejecucion": fecha,
            "cliente_id": cid,
            "cliente_nombre": str(row.get("cliente_nombre", "")),
            "vendedor_codigo": row.get("vendedor_codigo", ""),
            "plan_as": str(row.get("plan_as", "")),
            "innovaciones_activas": total_activas,
            "innovaciones_compradas": len(compradas),
            "pct_avance": round(len(compradas) / total_activas, 4),
            "productos_faltantes": "|".join(faltantes),
            "productos_pendiente_stock": PENDIENTE_STOCK,
        })
    return pd.DataFrame(filas)


# ─────────────────────────────────────────────
# MOD SELLOUT CATEGORIA
# ─────────────────────────────────────────────

def generar_sellout_categoria(ventas, maestro):
    """Ventas acumuladas en litros × categoría de bebida (col E maestro) × segmento (col B maestro)."""
    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v["_cod"] = pd.to_numeric(v["Codigo"], errors="coerce")
    merged = v.merge(
        maestro[["Codigo", "Segmento", "Categoria", "Lts_caja"]],
        left_on="_cod", right_on="Codigo", how="left"
    )
    merged["_litros"] = merged["CantBase"] * merged["Lts_caja"].fillna(0)
    merged = merged[merged["Categoria"].notna()]
    agg = merged.groupby(["Categoria", "Segmento"]).agg(
        litros=("_litros", "sum"),
        cajas=("CantBase", "sum"),
        importe=("ImporteNetoItem", "sum"),
        clientes=("Cliente", "nunique"),
    ).reset_index()
    agg["litros"] = agg["litros"].round(1)
    agg["importe"] = agg["importe"].round(0).astype("int64")
    agg["fecha_calculo"] = datetime.now().strftime("%Y-%m-%d")
    return agg.sort_values(["Categoria", "litros"], ascending=[True, False]).reset_index(drop=True)


# ─────────────────────────────────────────────
# MOD ACCIONES RANKING
# ─────────────────────────────────────────────

# Mapeo: categoria de regla → Categoria del maestro de productos
_REGLA_CAT_MAP = {
    "VDA/VDG/ESPUMANTES/SIDRA": ["Vinos del año", "Vinos de guarda", "Espumantes", "Sidra"],
    "VDA":                       ["Vinos del año", "Vinos de guarda"],
    "RTD":                       ["RTD", "RTD (S)", "Primary (S)", "Standard (S)", "Premium (S)", "Super Premium (S)"],
    "RTD LATAS":                 ["RTD", "RTD (S)", "Primary (S)", "Standard (S)", "Premium (S)", "Super Premium (S)"],
    "SPIRITS LOCALES":           ["Gin", "Vodka", "Ron", "Licores"],
    "SPIRITS IMPORTADOS":        ["Whisky", "Whisky (Maltas)", "Bourbon"],
    "SPIRITS":                   ["Gin", "Vodka", "Ron", "Licores", "Whisky", "Whisky (Maltas)", "Bourbon"],
    "ESPUMANTES":                ["Espumantes"],
}

# Mapeo: canal de regla → segmentos de clientes (_seg)  None = sin filtro
_REGLA_CANAL_SEG_MAP = {
    "AUTOSERVICIOS":           ["AUTOSERVICIO"],
    "TRAD+KIOSCO+ON PREMISE":  ["TRADICIONAL", "ON_PREMISE"],
    "VTK/TDB":                 ["ON_PREMISE"],
    "TODOS":                   None,
    "ON PREMISE NOCHE; BARES": ["ON_PREMISE"],
    "PETIT MAYORISTAS":        ["MAYORISTA"],
}

def generar_acciones_ranking(ventas, clientes, maestro):
    """Ranking de acciones comerciales del mes: litros vendidos, $ inversión, clientes."""
    p = BASE / "09_CONFIG" / "reglas_acciones_mayo_2026_orbit.csv"
    if not p.exists():
        return pd.DataFrame()
    reglas = pd.read_csv(p, encoding="latin1")
    reglas.columns = [c.lstrip("﻿").strip() for c in reglas.columns]

    v = ventas[ventas["ImporteNetoItem"] > 0].copy()
    v["_cod"] = pd.to_numeric(v["Codigo"], errors="coerce")
    v["_cli"] = pd.to_numeric(v["Cliente"], errors="coerce")
    v["_imp_item"] = pd.to_numeric(v.get("ImporteItem", 0), errors="coerce").fillna(0)
    v["_descuento_p"] = (v["_imp_item"] - v["ImporteNetoItem"]).clip(lower=0)

    # Solo contar ventas con descuento real (bajo una acción promocional)
    v = v[v["_descuento_p"] > 0].copy()

    v = v.merge(maestro[["Codigo", "Categoria", "Lts_caja"]], left_on="_cod", right_on="Codigo", how="left")
    v["_litros"] = v["CantBase"] * v["Lts_caja"].fillna(0)

    cli_seg = clientes[["Codigo", "_seg"]].copy()
    cli_seg["Codigo"] = pd.to_numeric(cli_seg["Codigo"], errors="coerce")
    v = v.merge(cli_seg.rename(columns={"Codigo": "cli_id"}), left_on="_cli", right_on="cli_id", how="left")

    # Deduplica canal+categoria (agrupa tiers de descuento distintos en una sola accion)
    seen: set = set()
    filas = []
    for _, r in reglas.iterrows():
        canal = str(r.get("canal", "")).strip()
        cat_key = str(r.get("categoria", "")).strip().upper()
        key = (canal, cat_key)
        if key in seen:
            continue
        seen.add(key)
        # Excluir PLANES AASS (cubierto por mod_planes_as) y RESTO SKU sin mapeo
        if canal == "PLANES AASS" or cat_key == "RESTO SKU":
            continue
        if canal not in _REGLA_CANAL_SEG_MAP:
            continue

        segs = _REGLA_CANAL_SEG_MAP[canal]
        mask = pd.Series(True, index=v.index)
        if segs is not None:
            mask &= v["_seg"].isin(segs)

        if cat_key == "INNOVACIONES":
            mask &= v["_cod"].isin(set(INOV_PRODUCTOS.keys()))
        else:
            maestro_cats = None
            for k, cats in _REGLA_CAT_MAP.items():
                if cat_key == k:
                    maestro_cats = cats
                    break
            if maestro_cats is None:
                continue
            mask &= v["Categoria"].isin(maestro_cats)

        v_m = v[mask]
        if v_m.empty:
            continue

        filas.append({
            "canal": canal,
            "categoria": cat_key,
            "litros_vendidos": round(float(v_m["_litros"].sum()), 1),
            "cajas_vendidas": int(v_m["CantBase"].sum()),
            "inversion_pesos": round(float(v_m["_descuento_p"].sum()), 0),
            "importe_neto": round(float(v_m["ImporteNetoItem"].sum()), 0),
            "clientes_afectados": int(v_m["_cli"].nunique()),
            "fecha_calculo": datetime.now().strftime("%Y-%m-%d"),
        })

    df = pd.DataFrame(filas)
    if not df.empty:
        df = df.sort_values("inversion_pesos", ascending=False).reset_index(drop=True)
    return df


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 50)
    print("generar_datasets_acum.py")
    print("=" * 50)

    print("\nCargando fuentes...")
    ventas   = cargar_ventas_acum()
    clientes = cargar_clientes()
    bbdd     = cargar_planes_as_bbdd()
    maestro  = cargar_maestro_productos()
    print(f"  ventas_acumulada : {len(ventas):>6} filas")
    print(f"  clientes         : {len(clientes):>6} filas")
    print(f"  planes_as BBDD   : {len(bbdd):>6} clientes AS")
    print(f"  maestro productos: {len(maestro):>6} productos")

    # ── Cobertura ──
    print("\n[1/3] Generando mod_cobertura_acum.csv ...")
    cob = generar_cobertura_acum(ventas, clientes)
    cob.to_csv(OUT / "mod_cobertura_acum.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(cob)} filas")
    print(cob[["vendedor_codigo", "segmento", "cartera", "cubiertos", "pct_cobertura"]].to_string(index=False))

    # ── 11 Titulares ──
    print("\n[2/3] Generando mod_11t_acum.csv ...")
    t11 = generar_11t_acum(ventas, clientes)
    t11.to_csv(OUT / "mod_11t_acum.csv", index=False, encoding="utf-8-sig")
    tiene = int(t11["tiene_flag"].sum())
    total = len(t11)
    print(f"  OK: {total} filas / {tiene} tienen ({round(100*tiene/total,1)}%) / {total - tiene} faltan")
    resumen_11t = (t11.groupby("marca_objetivo")
                   .agg(cartera=("cliente_id","count"), tienen=("tiene_flag","sum"))
                   .reset_index())
    resumen_11t["pct"] = (resumen_11t["tienen"] / resumen_11t["cartera"] * 100).round(1)
    print(resumen_11t.to_string(index=False))

    # ── Planes AS ──
    print("\n[3/5] Generando mod_planes_as.csv ...")
    pas = generar_planes_as(ventas, bbdd)
    pas.to_csv(OUT / "mod_planes_as.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(pas)} clientes AS")
    cols_show = ["cliente_id", "cliente_nombre", "plan_as", "total_facturado",
                 "sc_total_ganado", "sc_cajas_enviadas_total", "sc_pendiente"]
    print(pas[[c for c in cols_show if c in pas.columns]].to_string(index=False))

    # ── Innovaciones Segmento ──
    print("\n[4/5] Generando mod_innovaciones_segmento.csv ...")
    inov_seg = generar_innovaciones_segmento(ventas, clientes)
    inov_seg.to_csv(OUT / "mod_innovaciones_segmento.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(inov_seg)} filas ({inov_seg['producto_nombre'].nunique()} productos x {inov_seg['vendedor_codigo'].nunique()} vendedores x segmentos)")
    resumen_inov = (inov_seg.groupby("producto_nombre")
                    .agg(total_cartera=("clientes_cartera","max"),
                         total_compraron=("clientes_compraron","sum"))
                    .reset_index())
    resumen_inov["pct"] = (resumen_inov["total_compraron"] / resumen_inov["total_cartera"].replace(0, np.nan) * 100).round(1).fillna(0)
    print(resumen_inov.to_string(index=False))

    # ── Innovaciones Plan AS ──
    print("\n[5/7] Generando mod_innovaciones_plan_as.csv ...")
    inov_pas = generar_innovaciones_plan_as(ventas, bbdd)
    inov_pas.to_csv(OUT / "mod_innovaciones_plan_as.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(inov_pas)} clientes AS")

    # ── Sellout por Categoría ──
    print("\n[6/7] Generando mod_sellout_categoria.csv ...")
    sellout = generar_sellout_categoria(ventas, maestro)
    sellout.to_csv(OUT / "mod_sellout_categoria.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(sellout)} filas ({sellout['Categoria'].nunique()} categorias x {sellout['Segmento'].nunique()} segmentos)")
    resumen_sell = (sellout.groupby("Categoria")
                    .agg(litros_total=("litros","sum"), cajas_total=("cajas","sum"), clientes=("clientes","sum"))
                    .reset_index()
                    .sort_values("litros_total", ascending=False))
    resumen_sell["litros_total"] = resumen_sell["litros_total"].round(1)
    print(resumen_sell.to_string(index=False))

    # ── Acciones Ranking ──
    print("\n[7/7] Generando mod_acciones_ranking.csv ...")
    acc = generar_acciones_ranking(ventas, clientes, maestro)
    acc.to_csv(OUT / "mod_acciones_ranking.csv", index=False, encoding="utf-8-sig")
    print(f"  OK: {len(acc)} acciones")
    if not acc.empty:
        print(acc[["canal","categoria","litros_vendidos","inversion_pesos","clientes_afectados"]].to_string(index=False))

    print("\n[OK] Siete datasets generados en 04_DATASETS_ORBIT/")
    print("     mod_cobertura_acum.csv")
    print("     mod_11t_acum.csv")
    print("     mod_planes_as.csv")
    print("     mod_innovaciones_segmento.csv")
    print("     mod_innovaciones_plan_as.csv")
    print("     mod_sellout_categoria.csv")
    print("     mod_acciones_ranking.csv")


if __name__ == "__main__":
    main()
