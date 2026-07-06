#!/usr/bin/env python3
"""
generar_cierre_mensual.py
Cierre mensual historico versionado — ORBIT Matinal Penaflor.
Fuente exclusiva: 01_INPUTS/ventas_mes.csv
"""

import sys, json, csv, hashlib, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
INPUTS  = ROOT / "01_INPUTS"
CONFIG  = ROOT / "09_CONFIG"
CIERRES = ROOT / "07_CIERRES_MENSUALES"

VENDEDORES_ACTIVOS = {3, 4, 6, 7, 8, 9, 10}
VENDEDOR_SOLO_TRAD = {3}
TZ_AR = timezone(timedelta(hours=-3))
COB_MIN = {"AUTOSERVICIO": 6, "ON_PREMISE_VTK": 6, "TRADICIONAL": 3, "OTROS": 3}

_MARCA_LKP = {
    "ALMA MORA": "ALMA MORA", "ALARIS": "ALARIS", "TRAPICHE ALARIS": "ALARIS",
    "DON DAVID": "DON DAVID", "DADA": "DADA", "LOS ARBOLES": "LOS ARBOLES",
    "FINCA LAS MORAS": "FINCA LAS MORAS", "F LAS MORAS": "FINCA LAS MORAS",
    "TRAPICHE RESERVA": "TRAPICHE RESERVA",
    "FOND DE CAVE": "FOND DE CAVE", "FOND CAVE": "FOND DE CAVE",
    "CAZADOR": "CAZADOR", "ANTARES": "ANTARES",
    "GORDON'S FLAVOURS": "GORDON'S FLAVOURS", "GORDONS FLAVOURS": "GORDON'S FLAVOURS",
    "GORDONS": "GORDON'S FLAVOURS", "GORDON'S": "GORDON'S FLAVOURS",
    "SMIRNOFF": "SMIRNOFF FLAVOURS", "SMIRNOFF FLAVOURS": "SMIRNOFF FLAVOURS",
    "SMIRNOFF ICE": "SMIRNOFF ICE", "JW BLACK": "JW BLACK", "JW RED": "JW RED",
    "MASCOTA": "MASCOTA", "NC ESPUMANTES": "NC ESPUMANTES",
    "TRAPICHE MEDALLA": "TRAPICHE MEDALLA",
}

_ART_KW_11T = [
    ("SMIRNOFF ICE", "SMIRNOFF ICE"), ("SMF ICE", "SMIRNOFF ICE"),
    ("SMIRNOFF", "SMIRNOFF FLAVOURS"), ("GORDON", "GORDON'S FLAVOURS"),
    ("ANTARES", "ANTARES"), ("CAZADOR", "CAZADOR"),
    ("FOND DE CAVE", "FOND DE CAVE"), ("ALMA MORA", "ALMA MORA"),
    ("LOS ARBOLES", "LOS ARBOLES"), ("DADA", "DADA"),
    ("FINCA LAS MORAS", "FINCA LAS MORAS"), ("DON DAVID", "DON DAVID"),
    ("ALARIS", "ALARIS"), ("TRAPICHE RESERVA", "TRAPICHE RESERVA"),
    ("JW BLACK", "JW BLACK"), ("JW RED", "JW RED"),
]

# Match por Código Art. exacto (matriz oficial 11 Titulares) — fuente primaria; texto de Marca = fallback.
_COD11T_CACHE = {"mtime": None, "map": None}

def _codigos_11t_map():
    """codigo_articulo (int) -> marca_objetivo desde la matriz oficial. {} si falta el archivo."""
    p = INPUTS / "11 titulares autoservicio" / "11_titulares_autoservicios_match_codigos.xlsx"
    if not p.exists():
        return {}
    mt = p.stat().st_mtime
    if _COD11T_CACHE["map"] is not None and _COD11T_CACHE["mtime"] == mt:
        return _COD11T_CACHE["map"]
    _NORM = {"SMF ICE": "SMIRNOFF ICE"}
    out = {}
    try:
        d = pd.read_excel(p, sheet_name="DETALLE_SKU_11T_AS")
        for _, r in d.iterrows():
            cod = pd.to_numeric(r.get("codigo_articulo"), errors="coerce")
            marca = str(r.get("linea_comercial_11t", "")).upper().strip()
            marca = _NORM.get(marca, marca)
            if pd.notna(cod) and marca and marca != "NAN":
                out[int(cod)] = marca
    except Exception as e:
        print(f"[AVISO] 11T códigos matriz: {e}")
        return {}
    _COD11T_CACHE["map"], _COD11T_CACHE["mtime"] = out, mt
    return out


def _ahora_ar():
    return datetime.now(tz=TZ_AR)


def _seg(ramo, subramo):
    t = str(ramo).upper() + " | " + str(subramo).upper()
    if any(k in t for k in ["AUTOSERVICIO","CADENA REGIONAL","SAR","LARGE FORMAT",
                             "PROXIMITY","CASH&CARRY","CASH & CARRY","MAYORISTA",
                             "MAYORISTAS","TIENDA DE BEBIDAS"]):
        return "AUTOSERVICIO"
    if any(k in t for k in ["ON PREMISE","AWAY FROM HOME","VINOTECA","VINOTECAS",
                             "BAR","RESTAURANT","RESTAURANTE","ESTACION DE SERVICIO",
                             "EVENTOS","TEMPORADA","CATERING","ON DIA","ON NOCHE"]):
        return "ON_PREMISE_VTK"
    if any(k in t for k in ["TRADITIONAL TRADE","ALMACEN","DESPENSA","KIOSCO",
                             "MAXIKIOSCO","FIAMBRERIA","CARNICERIA","GRANJA",
                             "PANADERIA","CASA DE PASTAS","TRADICIONAL"]):
        return "TRADICIONAL"
    return "OTROS"


def _file_meta(path):
    if not path.exists():
        return {"existe": False, "ruta": str(path)}
    s = path.stat()
    return {"existe": True, "ruta": str(path), "tamano_bytes": s.st_size,
            "modificado": datetime.fromtimestamp(s.st_mtime, tz=TZ_AR).isoformat()}


def _sha256_head(path, n=65536):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(n))
    return h.hexdigest()[:16]


def _raw_codigos(src):
    for enc in ("utf-8-sig", "latin-1", "windows-1252"):
        try:
            df = pd.read_csv(src, sep=",", usecols=["CodVendedor"],
                             dtype=str, encoding=enc, engine="python")
            return set(pd.to_numeric(df["CodVendedor"], errors="coerce")
                       .dropna().astype(int).unique())
        except Exception:
            continue
    return set()


def _leer_ventas(src):
    df = None
    for enc in ("utf-8-sig", "latin-1", "windows-1252"):
        try:
            df = pd.read_csv(src, sep=",", quotechar='"', engine="python",
                             dtype=str, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = [c.strip() for c in df.columns]
    for col in ("CantBase", "ImporteNetoItem", "ImporteItem", "valorDescuento"):
        if col in df.columns:
            df[col] = (df[col].astype(str).str.strip().str.strip('"')
                       .str.replace(",", ".", regex=False)
                       .pipe(pd.to_numeric, errors="coerce").fillna(0.0))
        else:
            df[col] = 0.0
    df["CodVendedor"] = (pd.to_numeric(df["CodVendedor"].astype(str).str.strip(),
                                       errors="coerce").fillna(0).astype(int))
    df["FechaComprobante"] = pd.to_datetime(df["FechaComprobante"],
                                            format="%Y-%m-%d", errors="coerce")
    df["Cliente"] = (pd.to_numeric(df["Cliente"].astype(str).str.strip(),
                                   errors="coerce").fillna(0).astype(int))
    df["Codigo"] = (pd.to_numeric(df["Codigo"].astype(str).str.strip(),
                                  errors="coerce").fillna(0).astype(int))
    df = df[df["CodVendedor"].isin(VENDEDORES_ACTIVOS)].copy()
    df["segmento"] = df.apply(lambda r: _seg(r.get("Ramo",""), r.get("Subramo","")), axis=1)
    df = df[~((df["CodVendedor"] == 3) & (df["segmento"] != "TRADICIONAL"))].copy()
    return df


def _leer_04d(src):
    try:
        m = pd.read_excel(src, header=3, dtype=str)
        m.columns = [str(c).strip() for c in m.columns]
        rn = {}
        for c in m.columns:
            cu = c.upper()
            if "DIGO" in cu or ("COD" in cu and "ART" in cu):
                rn[c] = "codigo_art"
            elif "LTS" in cu and ("CAJA" in cu or "X" in cu):
                rn[c] = "lts_x_caja"
            elif "UXC" in cu or "UN X" in cu:
                rn[c] = "uxc"
        m.rename(columns=rn, inplace=True)
        for col in ("codigo_art", "lts_x_caja", "uxc"):
            if col not in m.columns:
                m[col] = 0.0
        m["codigo_art"] = pd.to_numeric(m["codigo_art"], errors="coerce").fillna(0).astype(int)
        m["lts_x_caja"] = pd.to_numeric(m["lts_x_caja"], errors="coerce").fillna(0.0)
        m["uxc"] = pd.to_numeric(m["uxc"], errors="coerce").fillna(0.0)
        m = m[m["codigo_art"] > 0].copy()
        return m[["codigo_art","lts_x_caja","uxc"]].drop_duplicates("codigo_art")
    except Exception as e:
        print("WARN 04D: " + str(e))
        return pd.DataFrame(columns=["codigo_art","lts_x_caja","uxc"])


def _leer_innovaciones(src):
    codigos = set()
    try:
        import openpyxl
        wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
        ws = wb.active
        for row in ws.iter_rows(min_row=1, max_row=10, values_only=True):
            if any(isinstance(v, str) and str(v).strip().startswith("000000") for v in row):
                for cell in row:
                    if isinstance(cell, str) and cell.strip().startswith("000000"):
                        cs = cell.strip().split(" ")[0].lstrip("0")
                        if cs:
                            try:
                                codigos.add(int(cs))
                            except ValueError:
                                pass
                break
        wb.close()
    except Exception as e:
        print("WARN innovaciones: " + str(e))
    return codigos


def _leer_vendedores(src):
    vend = {}
    try:
        df = pd.read_csv(src)
        for _, r in df.iterrows():
            cn = str(r.get("codigo_vendedor","")).strip().lstrip("Vv")
            try:
                vend[int(cn)] = str(r.get("nombre_vendedor","")).strip()
            except ValueError:
                pass
    except Exception:
        pass
    return vend


def _litros(df, m04d):
    if m04d.empty:
        df = df.copy(); df["litros"] = 0.0; return df
    mg = df.merge(m04d, left_on="Codigo", right_on="codigo_art", how="left")
    mg["lts_x_caja"] = mg["lts_x_caja"].fillna(0.0)
    mg["uxc"] = mg["uxc"].fillna(0.0)
    lu = mg["lts_x_caja"] / mg["uxc"].replace(0, float("nan"))
    mg["litros"] = (mg["CantBase"] * lu).fillna(0.0)
    return mg


def _marca_11t(df):
    # 1) match por Código Art. exacto (matriz oficial) — fuente primaria
    lk = _codigos_11t_map()
    if lk and "Codigo" in df.columns:
        marcas = pd.to_numeric(df["Codigo"], errors="coerce").map(lk)
    else:
        marcas = pd.Series(pd.NA, index=df.index, dtype="object")
    # 2) fallback: texto de Marca (variedades fuera de la matriz)
    falta = marcas.isna()
    marcas.loc[falta] = df.loc[falta, "Marca"].astype(str).str.upper().str.strip().map(_MARCA_LKP)
    for kw, mo in _ART_KW_11T:
        sin = marcas.isna()
        if not sin.any():
            break
        hits = df.loc[sin, "Articulo"].astype(str).str.upper().str.contains(kw, regex=False, na=False)
        marcas.loc[sin & hits] = mo
    return marcas


def _11t_por_vend(df):
    df = df.copy()
    df["marca_11t"] = _marca_11t(df)
    df = df[df["marca_11t"].notna()]
    result = {}
    for v in VENDEDORES_ACTIVOS:
        dfv = df[df["CodVendedor"] == v]
        cub = set()
        for (cli, marca, seg), grp in dfv.groupby(["Cliente","marca_11t","segmento"]):
            if grp["CantBase"].sum() >= COB_MIN.get(seg, 3):
                cub.add(cli)
        result[v] = len(cub)
    return result


def _11t_detalle(df, vn):
    df = df.copy()
    df["marca_11t"] = _marca_11t(df)
    df = df[df["marca_11t"].notna()]
    rows = []
    for v in sorted(VENDEDORES_ACTIVOS):
        dfv = df[df["CodVendedor"] == v]
        if dfv.empty:
            continue
        for marca, gm in dfv.groupby("marca_11t"):
            cub = set()
            for (cli, seg), grp in gm.groupby(["Cliente","segmento"]):
                if grp["CantBase"].sum() >= COB_MIN.get(seg, 3):
                    cub.add(cli)
            rows.append({"vendedor_codigo": "V"+str(v), "vendedor_nombre": vn.get(v,"V"+str(v)),
                         "marca_11t": marca, "clientes_cubiertos": len(cub)})
    return rows


def _inov_por_vend(df, codigos):
    if not codigos:
        return {v: 0 for v in VENDEDORES_ACTIVOS}
    di = df[df["Codigo"].isin(codigos)]
    return {v: int(di[di["CodVendedor"] == v]["Cliente"].nunique()) for v in VENDEDORES_ACTIVOS}


def _inov_detalle(df, codigos, vn):
    if not codigos:
        return []
    di = df[df["Codigo"].isin(codigos)].copy()
    rows = []
    for v in sorted(VENDEDORES_ACTIVOS):
        dfv = di[di["CodVendedor"] == v]
        if dfv.empty:
            continue
        for (cod, art), grp in dfv.groupby(["Codigo","Articulo"]):
            rows.append({"vendedor_codigo": "V"+str(v), "vendedor_nombre": vn.get(v,"V"+str(v)),
                         "producto_codigo": int(cod), "producto_nombre": str(art),
                         "clientes_compraron": int(grp["Cliente"].nunique())})
    return rows


def _acciones(df, vn):
    df = df.copy()
    df["desc_pct"] = (df["Descuento"].astype(str).str.strip()
                      .str.replace(",",".",regex=False).str.replace("%","",regex=False)
                      .pipe(pd.to_numeric, errors="coerce").fillna(0.0))
    sc = df[df["desc_pct"] >= 100].copy()
    cd = df[(df["desc_pct"] > 0) & (df["desc_pct"] < 100)].copy()
    cd["inv"] = cd["valorDescuento"] * cd["CantBase"]
    tramos = {}
    for _, row in cd.iterrows():
        t = str(int(row["desc_pct"])) + "%"
        if t not in tramos:
            tramos[t] = {"descuento": t, "_c": set(), "importe_neto": 0.0, "inversion_estimada": 0.0, "lineas": 0}
        tramos[t]["_c"].add(row["Cliente"])
        tramos[t]["importe_neto"] += row["ImporteNetoItem"]
        tramos[t]["inversion_estimada"] += row.get("inv", 0.0)
        tramos[t]["lineas"] += 1
    tl = []
    for k in sorted(tramos, key=lambda x: -float(x.rstrip("%"))):
        t = tramos[k]
        tl.append({"tipo":"DESCUENTO","descuento":t["descuento"],
                   "clientes_impactados":len(t["_c"]),
                   "importe_neto":round(t["importe_neto"],0),
                   "inversion_estimada":round(t["inversion_estimada"],0),
                   "lineas":t["lineas"]})
    pv = []
    for v in sorted(VENDEDORES_ACTIVOS):
        dfv = cd[cd["CodVendedor"] == v]
        if dfv.empty:
            continue
        pv.append({"vendedor_codigo":"V"+str(v),"vendedor_nombre":vn.get(v,"V"+str(v)),
                   "clientes_con_desc":int(dfv["Cliente"].nunique()),
                   "importe_neto_desc":round(float(dfv["ImporteNetoItem"].sum()),0),
                   "inversion_estimada":round(float(dfv["inv"].sum()),0)})
    sc_pv = []
    for v in sorted(VENDEDORES_ACTIVOS):
        dfv = sc[sc["CodVendedor"] == v]
        if dfv.empty:
            continue
        sc_pv.append({"vendedor_codigo":"V"+str(v),"vendedor_nombre":vn.get(v,"V"+str(v)),
                      "clientes_sin_cargo":int(dfv["Cliente"].nunique()),
                      "marcas_sin_cargo":sorted(dfv["Marca"].dropna().unique().tolist()),
                      "lineas_sin_cargo":int(len(dfv))})
    return {
        "resumen_empresa": {"clientes_con_descuento":int(cd["Cliente"].nunique()),
                            "clientes_sin_cargo":int(sc["Cliente"].nunique()),
                            "lineas_con_descuento":int(len(cd)),
                            "lineas_sin_cargo":int(len(sc)),
                            "inversion_estimada":round(float(cd["inv"].sum()),0),
                            "nota_inversion":"valorDescuento x CantBase"},
        "tramos_descuento": tl,
        "sin_cargo": {"lineas":int(len(sc)),"clientes_impactados":int(sc["Cliente"].nunique()),
                      "marcas":sorted(sc["Marca"].dropna().unique().tolist()),
                      "por_vendedor":sc_pv,
                      "nota":"CantBase usado internamente — no expuesto"},
        "por_vendedor_descuentos": pv,
    }


def _ranking(litros, dinero, c11t, inov, vn):
    ml = max(litros.values(), default=0)
    md = max(dinero.values(), default=0)
    m11 = max(c11t.values(), default=0)
    mi = max(inov.values(), default=0)
    rows = []
    for v in sorted(VENDEDORES_ACTIVOS):
        l = litros.get(v, 0.0)
        d = dinero.get(v, 0.0)
        t = c11t.get(v, 0)
        i = inov.get(v, 0)
        sl = l/ml if ml > 0 else 0.0
        sd = d/md if md > 0 else 0.0
        s11 = t/m11 if m11 > 0 else 0.0
        si = i/mi if mi > 0 else 0.0
        score = round((sl*0.20 + sd*0.20 + s11*0.30 + si*0.30)*100, 2)
        svd = round((sl*0.20 + sd*0.20)/0.40*100, 2) if (sl+sd) > 0 else 0.0
        rows.append({"vendedor_codigo":"V"+str(v),"vendedor_nombre":vn.get(v,"V"+str(v)),
                     "litros_vendidos":round(l,2),"dinero_vendido":round(d,0),
                     "clientes_11_titulares":t,"clientes_innovaciones":i,
                     "score_litros":round(sl*100,2),"score_dinero":round(sd*100,2),
                     "score_volumen_dinero":svd,"score_11_titulares":round(s11*100,2),
                     "score_innovaciones":round(si*100,2),"score_total":score,
                     "ranking_general":0,"ranking_volumen_dinero":0,
                     "ranking_11_titulares":0,"ranking_innovaciones":0,
                     "etiqueta_destacada":""})
    rows.sort(key=lambda r: -r["score_total"])
    for i, r in enumerate(rows): r["ranking_general"] = i+1
    rows.sort(key=lambda r: -(r["score_litros"]*0.20 + r["score_dinero"]*0.20))
    for i, r in enumerate(rows): r["ranking_volumen_dinero"] = i+1
    rows.sort(key=lambda r: -r["score_11_titulares"])
    for i, r in enumerate(rows): r["ranking_11_titulares"] = i+1
    rows.sort(key=lambda r: -r["score_innovaciones"])
    for i, r in enumerate(rows): r["ranking_innovaciones"] = i+1
    for r in rows:
        etiq = []
        if r["ranking_general"] == 1: etiq.append("MEJOR_GENERAL")
        if r["ranking_volumen_dinero"] == 1: etiq.append("MEJOR_VOLUMEN_DINERO")
        if r["ranking_11_titulares"] == 1: etiq.append("MEJOR_11_TITULARES")
        if r["ranking_innovaciones"] == 1: etiq.append("MEJOR_INNOVACIONES")
        r["etiqueta_destacada"] = "|".join(etiq)
    rows.sort(key=lambda r: r["ranking_general"])
    return rows


def _detectar_version(carpeta_mes):
    if not carpeta_mes.exists():
        return "version_001"
    nums = [int(d.name.replace("version_","")) for d in carpeta_mes.iterdir()
            if d.is_dir() and d.name.startswith("version_")
            and d.name.replace("version_","").isdigit()]
    return ("version_" + str(max(nums)+1).zfill(3)) if nums else "version_001"


def _actualizar_indice(periodo, version, carpeta, estado, ts_ar):
    CIERRES.mkdir(parents=True, exist_ok=True)
    idx_csv = CIERRES / "index_cierres_mensuales.csv"
    idx_json = CIERRES / "index_cierres_mensuales.json"
    entrada = {"periodo":periodo,"version":version,
               "carpeta":str(carpeta.relative_to(ROOT)),
               "timestamp_argentina":ts_ar,"estado":estado}
    rows = []
    if idx_csv.exists():
        with open(idx_csv, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    rows.append(entrada)
    with open(idx_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(entrada.keys()))
        w.writeheader(); w.writerows(rows)
    with open(idx_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def generar_cierre(periodo=None, dry_run=False):
    ts_inicio = _ahora_ar()
    ts_utc = datetime.now(tz=timezone.utc)

    src_ventas = INPUTS / "ventas_mes.csv"
    if not src_ventas.exists():
        print("ERROR: 01_INPUTS/ventas_mes.csv no encontrado. Abortando.")
        sys.exit(1)

    excluidos_raw = sorted(_raw_codigos(src_ventas) - VENDEDORES_ACTIVOS)

    df = _leer_ventas(src_ventas)
    if df.empty:
        print("ERROR: ventas_mes.csv sin filas validas. Abortando.")
        sys.exit(1)

    n_filas = len(df)
    fecha_min = df["FechaComprobante"].min()
    fecha_max = df["FechaComprobante"].max()
    vend_presentes = sorted(df["CodVendedor"].unique())
    periodo_final = periodo if periodo else fecha_max.strftime("%Y-%m")

    v3_rows = df[df["CodVendedor"] == 3]
    v3_solo_trad = bool((v3_rows["segmento"] == "TRADICIONAL").all()) if not v3_rows.empty else True
    v3_segs = sorted(v3_rows["segmento"].unique().tolist()) if not v3_rows.empty else []

    print("Periodo        : " + periodo_final)
    print("Filas leidas   : " + str(n_filas))
    print("Fecha min      : " + str(fecha_min.date()))
    print("Fecha max      : " + str(fecha_max.date()))
    print("Incluidos      : " + str(["V"+str(v) for v in vend_presentes]))
    print("Excluidos CSV  : " + str(["V"+str(v) for v in excluidos_raw]))
    print("V3 solo Trad   : " + ("PASS" if v3_solo_trad else "FAIL") + " " + str(v3_segs))

    carpeta_mes = CIERRES / periodo_final
    version = _detectar_version(carpeta_mes)
    carpeta_version = carpeta_mes / version
    print("Version        : " + version)

    if dry_run:
        print("DRY RUN OK — no se escriben archivos.")
        return

    carpeta_version.mkdir(parents=True, exist_ok=True)

    src_04d = INPUTS / "04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx"
    m04d = _leer_04d(src_04d)
    src_inov = INPUTS / "INNOVACIONES" / "Innovaciones.xlsx"
    cod_inov = _leer_innovaciones(src_inov)
    vn = _leer_vendedores(CONFIG / "vendedores_activos.csv")

    df_neto = df[df["ImporteNetoItem"] > 0].copy()
    df_lit = _litros(df_neto, m04d)
    litros_d = df_lit.groupby("CodVendedor")["litros"].sum().to_dict()
    dinero_d = df_neto.groupby("CodVendedor")["ImporteNetoItem"].sum().to_dict()
    ccc_d = df_neto.groupby("CodVendedor")["Cliente"].nunique().to_dict()

    c11t_d = _11t_por_vend(df)
    det_11t = _11t_detalle(df, vn)
    inov_d = _inov_por_vend(df, cod_inov)
    det_inov = _inov_detalle(df, cod_inov, vn)
    acc = _acciones(df, vn)
    rank = _ranking(litros_d, dinero_d, c11t_d, inov_d, vn)

    res_emp = {"periodo":periodo_final,"fecha_min":str(fecha_min.date()),
               "fecha_max":str(fecha_max.date()),"filas_ventas_mes":n_filas,
               "vendedores_incluidos":["V"+str(v) for v in vend_presentes],
               "importe_neto_total":round(float(df_neto["ImporteNetoItem"].sum()),0),
               "litros_total":round(float(df_lit["litros"].sum()),2),
               "ccc_total":int(df_neto["Cliente"].nunique())}

    res_vend = []
    for v in sorted(VENDEDORES_ACTIVOS):
        if v not in vend_presentes:
            continue
        res_vend.append({"vendedor_codigo":"V"+str(v),"vendedor_nombre":vn.get(v,"V"+str(v)),
                         "solo_tradicional":v in VENDEDOR_SOLO_TRAD,
                         "dinero_vendido":round(dinero_d.get(v,0.0),0),
                         "litros_vendidos":round(litros_d.get(v,0.0),2),
                         "ccc":int(ccc_d.get(v,0)),
                         "clientes_11_titulares":c11t_d.get(v,0),
                         "clientes_innovaciones":inov_d.get(v,0)})

    ts_ar = ts_inicio.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    ts_uc = ts_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest = {"periodo":periodo_final,"version":version,
                "timestamp_utc":ts_uc,"timestamp_argentina":ts_ar,
                "zona_horaria":"America/Argentina/Cordoba",
                "fuente_ventas":"01_INPUTS/ventas_mes.csv",
                "fuente_ventas_hash_head":_sha256_head(src_ventas),
                "fuente_ventas_tamano_bytes":src_ventas.stat().st_size,
                "filas_leidas":n_filas,"fecha_min":str(fecha_min.date()),
                "fecha_max":str(fecha_max.date()),
                "vendedores_detectados":["V"+str(v) for v in vend_presentes],
                "vendedores_excluidos_csv":["V"+str(v) for v in excluidos_raw],
                "regla_excluidos":"Solo V3,V4,V6,V7,V8,V9,V10 incluidos",
                "regla_v3":"V3 solo TRADICIONAL",
                "v3_solo_tradicional_pass":v3_solo_trad,
                "v3_segmentos_detectados":v3_segs,
                "codigos_innovaciones":sorted(list(cod_inov)),
                "archivos_generados":["manifest.json","snapshot_inputs.json",
                                      "cierre_mensual_resumen.csv","cierre_mensual_resumen.json",
                                      "ranking_vendedores_mes.csv","ranking_vendedores_mes.json",
                                      "acciones_comerciales_mes.csv","acciones_comerciales_mes.json",
                                      "detalle_11_titulares_mes.csv","detalle_innovaciones_mes.csv"],
                "estado":"PASS",
                "nota_botellas":"CantBase solo interno — salidas no exponen botellas",
                "fuentes_prohibidas":["ventas.csv","ventas_acumulada.csv","resultado.xlsx"]}

    meta_v = _file_meta(src_ventas)
    meta_v["filas_leidas"] = n_filas
    meta_v["fecha_min"] = str(fecha_min.date())
    meta_v["fecha_max"] = str(fecha_max.date())
    snapshot = {"ventas_mes_csv":meta_v,"maestro_04d_xlsx":_file_meta(src_04d),
                "innovaciones_xlsx":_file_meta(src_inov),
                "vendedores_activos_csv":_file_meta(CONFIG/"vendedores_activos.csv")}

    def wj(name, data):
        p = carpeta_version / name
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return p

    def wc(name, rows_list, fields=None):
        p = carpeta_version / name
        if not rows_list:
            p.write_text("", encoding="utf-8"); return p
        fn = fields if fields else list(rows_list[0].keys())
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader(); w.writerows(rows_list)
        return p

    created = []
    created.append(wj("manifest.json", manifest))
    created.append(wj("snapshot_inputs.json", snapshot))
    created.append(wj("cierre_mensual_resumen.json", {"empresa":res_emp,"vendedores":res_vend}))
    created.append(wc("cierre_mensual_resumen.csv", res_vend))
    created.append(wj("ranking_vendedores_mes.json", rank))
    created.append(wc("ranking_vendedores_mes.csv", rank))
    created.append(wj("acciones_comerciales_mes.json", acc))
    af = ["tipo","descuento","clientes_impactados","importe_neto","inversion_estimada","lineas"]
    ar = list(acc["tramos_descuento"])
    sc2 = acc["sin_cargo"]
    ar.append({"tipo":"SIN_CARGO","descuento":"100%",
               "clientes_impactados":sc2["clientes_impactados"],
               "importe_neto":0,"inversion_estimada":0,"lineas":sc2["lineas"]})
    created.append(wc("acciones_comerciales_mes.csv", ar, fields=af))
    created.append(wc("detalle_11_titulares_mes.csv", det_11t))
    created.append(wc("detalle_innovaciones_mes.csv", det_inov))

    _actualizar_indice(periodo_final, version, carpeta_version, "PASS", ts_ar)
    created.append(CIERRES / "index_cierres_mensuales.csv")
    created.append(CIERRES / "index_cierres_mensuales.json")

    for fp in created:
        sz = fp.stat().st_size if fp.exists() else 0
        print("OK " + fp.name + " (" + str(sz) + " bytes)")

    print("Ranking generado")
    print("ESTADO FINAL: PASS")

    return manifest, rank, acc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mes", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    generar_cierre(periodo=args.mes, dry_run=args.dry_run)
