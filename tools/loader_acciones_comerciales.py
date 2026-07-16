"""
loader_acciones_comerciales.py — Loader idempotente de acciones comerciales mensuales.

Lee el catálogo mensual de acciones (CSV ';' UTF-8-BOM) de un mes dado, lo valida
y normaliza, detecta colisiones/solapes y escribe la salida SEPARADA POR MES.

Colisiones detectadas:
  - DIRECTA: solape de tokens de producto/línea/marca entre dos reglas.
  - SEMANTICA_LINEA_MARCA: solape vía mapeo marca→categoría desde el maestro de
    productos (ej. regla de línea "VDA" vs regla de marca "ALMA MORA" que es VDA).

NO toca cierre de mes, resultado.xlsx, históricos (07_CIERRES_MENSUALES) ni datasets
productivos (04_DATASETS_ORBIT) ni server_orbit.py. Solo lee el input del mes (y el
maestro de productos en modo lectura) y escribe en <mes>/salida/.

Idempotente: re-ejecutar regenera la misma salida; antes de sobrescribir hace backup
timestamp de la salida previa.

Uso:
    python tools/loader_acciones_comerciales.py 2026-06
"""
import sys
import csv
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

_ARG = timezone(timedelta(hours=-3))
BASE = Path(__file__).resolve().parent.parent
VEND_ACTIVOS = {"V3", "V4", "V6", "V7", "V8", "V9", "V10"}
VEND_EXCLUIDOS = {"V2", "V5", "V20"}

_CANALES = {
    "TRADICIONAL":  ["TRADICIONAL", "TRAD"],
    "KIOSCO":       ["KIOSCO"],
    "AUTOSERVICIO": ["AUTOSERVICIO", "AS"],
    "ON_PREMISE":   ["ON PREMISE", "ON_PREMISE", "ONPREMISE"],
    "VTK_TDB":      ["VTK", "TDB", "VINOTECA"],
    "MAYORISTA":    ["MAYORISTA"],
}
# Tokens de producto genéricos que NO se usan para cruzar colisiones (no son marcas concretas).
_PROD_GENERICOS = {
    "", "SEGUN MAESTRO PRODUCTOS ACTIVOS", "LISTA CERRADA DE INNOVACIONES JUNIO 2026",
    "RESTO SKU", "RESTO", "TODOS", "TODOS_ACTIVOS",
}
# Maestros de producto candidatos (solo lectura) para mapear marca/línea → categoría.
# El maestro vigente es el CSV de 09_CONFIG (completado con RAW_PRODUCTOS/productos<mes>.xlsx);
# 'producto activos.xlsx' quedó como _NO_USAR_ el 16/07/2026 (lista vieja, no es fuente).
_MAESTRO_CANDIDATOS = [
    "01_INPUTS/04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx",
]
# Categoría del maestro → token canónico que usan las reglas.
_CAT_CANON = [
    (("VINOS DEL AÑO", "VINOS DEL ANO", "VDA"), "VDA"),
    (("VINOS DE GUARDA", "VDG"), "VDG"),
    (("VINOS DE MESA", "VDM"), "VDM"),
    (("ESPUMANTE",), "ESPUMANTES"),
    (("SIDRA",), "SIDRA"),
    (("SPIRIT",), "SPIRITS"),
    (("RTD",), "RTD"),
    (("CERVEZA",), "CERVEZA"),
]
# Tokens de línea/categoría que pueden aparecer directos en las reglas.
_LINEA_TOKENS = {
    "VDA": "VDA", "VDG": "VDG", "VDM": "VDM",
    "ESPUMANTE": "ESPUMANTES", "ESPUMANTES": "ESPUMANTES",
    "SIDRA": "SIDRA", "SPIRIT": "SPIRITS", "SPIRITS": "SPIRITS",
}


def _ts():
    return datetime.now(_ARG).strftime("%Y%m%d_%H%M%S")


def _norm(s):
    return (s or "").strip().upper()


def _canon_cat(c):
    u = _norm(c)
    for kws, canon in _CAT_CANON:
        if any(k in u for k in kws):
            return canon
    return u or None


def cargar_mapa_categorias():
    """Lee el maestro de productos y devuelve (linea_to_cats: dict, disponible: bool).
    linea_to_cats mapea 'LINEA COMERCIAL' (uppercase) -> set de categorías canónicas."""
    try:
        import pandas as pd
    except Exception:
        return {}, False
    for cand in _MAESTRO_CANDIDATOS:
        p = BASE / cand
        if not p.exists():
            continue
        try:
            raw = pd.read_excel(p, header=None)
            hdr, cols = None, None
            for i, row in raw.iterrows():
                vals = [str(x).strip() for x in row.tolist()]
                if "Linea Comercial" in vals and any(v.startswith("Categor") for v in vals):
                    hdr, cols = i, vals
                    break
            if hdr is None:
                continue
            df = raw.iloc[hdr + 1:].copy()
            df.columns = cols
            lc = "Linea Comercial"
            cat = [c for c in cols if str(c).startswith("Categor")][0]
            mapa = {}
            for _, r in df.iterrows():
                ln = _norm(r.get(lc))
                ca = _canon_cat(r.get(cat))
                if not ln or ln == "LINEA COMERCIAL" or not ca:
                    continue
                mapa.setdefault(ln, set()).add(ca)
            if mapa:
                return mapa, True
        except Exception:
            continue
    return {}, False


def _expand_vendedores(raw):
    """Devuelve set de vendedores activos; expande TODOS_ACTIVOS y excluye V2/V5/V20."""
    txt = _norm(raw)
    if "TODOS" in txt:
        return set(VEND_ACTIVOS)
    out = set()
    for tok in raw.replace(",", ";").split(";"):
        t = _norm(tok)
        if t.startswith("V") and t[1:].isdigit():
            out.add(t)
    return (out & VEND_ACTIVOS)  # nunca V2/V5/V20


def _canales(raw_canal, raw_seg):
    txt = _norm(raw_canal) + " | " + _norm(raw_seg)
    out = set()
    for canon, kws in _CANALES.items():
        if any(k in txt for k in kws):
            out.add(canon)
    return out


def _tokens_producto(raw_marcas, raw_lineas):
    out = set()
    for raw in (raw_marcas, raw_lineas):
        for tok in (raw or "").replace(",", ";").split(";"):
            t = _norm(tok)
            if t and t not in _PROD_GENERICOS:
                out.add(t)
    return out


def _categorias_de_regla(prod_tokens, linea_to_cats):
    """Categorías canónicas que cubre una regla: por tokens de línea directos y por
    mapeo marca→categoría desde el maestro. Respeta el caso 'DADA VINO' (solo vino)."""
    cats = set()
    for tok in prod_tokens:
        t = _norm(tok)
        for k, canon in _LINEA_TOKENS.items():
            if k in t:
                cats.add(canon)
        wine_only = t.endswith(" VINO") or t == "VINO"
        base = t.replace(" VINO", "").strip()
        if not base:
            continue
        for linea, lcats in linea_to_cats.items():
            if linea == t or linea == base or linea.startswith(base + " ") or base.startswith(linea + " "):
                for c in lcats:
                    if wine_only and c in ("SIDRA", "ESPUMANTES", "RTD"):
                        continue
                    cats.add(c)
    return cats


def _solapan_productos(a, b):
    """Overlap de tokens de producto: igualdad o contención (substring) entre tokens."""
    comunes = set()
    for x in a:
        for y in b:
            if x == y or x in y or y in x:
                comunes.add(x if len(x) <= len(y) else y)
    return comunes


def _localizar_csv(indir):
    csvs = sorted(indir.glob("*.csv"))
    return csvs[0] if csvs else None


def cargar_mes(mes):
    indir = BASE / "01_INPUTS" / "ACCIONES COMERCIALES" / mes
    if not indir.exists():
        raise SystemExit(f"[ERROR] No existe la carpeta del mes: {indir}")
    src = _localizar_csv(indir)
    if not src:
        raise SystemExit(f"[ERROR] No se encontró CSV de acciones en {indir}")
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return indir, src, rows


def normalizar(rows, linea_to_cats):
    reglas = []
    for r in rows:
        vend = _expand_vendedores(r.get("vendedores_aplica", ""))
        can = _canales(r.get("canal_aplica", ""), r.get("segmento_cliente_aplica", ""))
        prod = _tokens_producto(r.get("productos_marcas", ""), r.get("lineas_comerciales", ""))
        cats = _categorias_de_regla(prod, linea_to_cats)
        menciona_excluidos = sorted(
            v for v in VEND_EXCLUIDOS
            if v in _norm(r.get("vendedores_aplica", "")).replace(",", " ").split()
        )
        reglas.append({
            "id_accion":          r.get("id_accion", "").strip(),
            "tipo_regla":         r.get("tipo_regla", "").strip(),
            "segmento":           r.get("segmento_cliente_aplica", "").strip(),
            "canal":              r.get("canal_aplica", "").strip(),
            "vendedores_raw":     r.get("vendedores_aplica", "").strip(),
            "productos_marcas":   r.get("productos_marcas", "").strip(),
            "lineas_comerciales": r.get("lineas_comerciales", "").strip(),
            "descuento_pct":      r.get("descuento_pct", "").strip(),
            "combinable":         r.get("combinable", "").strip(),
            "aplica_cierre_mes":  r.get("aplica_cierre_mes", "").strip(),
            "observaciones":      r.get("observaciones", "").strip(),
            "_vend":  sorted(vend),
            "_canal": sorted(can),
            "_prod":  sorted(prod),
            "_cats":  sorted(cats),
            "_aplica_cierre_mes_ok": _norm(r.get("aplica_cierre_mes", "")) == "NO",
            "_menciona_vendedores_excluidos": menciona_excluidos,
        })
    return reglas


def detectar_colisiones(reglas):
    cols = []
    for i in range(len(reglas)):
        for j in range(i + 1, len(reglas)):
            a, b = reglas[i], reglas[j]
            v = set(a["_vend"]) & set(b["_vend"])
            c = set(a["_canal"]) & set(b["_canal"])
            if not (v and c):
                continue
            p = _solapan_productos(set(a["_prod"]), set(b["_prod"]))
            cats = set(a["_cats"]) & set(b["_cats"])
            if p:
                tipo, comunes = "DIRECTA", sorted(p)
            elif cats:
                tipo, comunes = "SEMANTICA_LINEA_MARCA", []
            else:
                continue
            cols.append({
                "tipo": tipo,
                "accion_a": a["id_accion"],
                "accion_b": b["id_accion"],
                "vendedores_comunes": sorted(v),
                "canales_comunes": sorted(c),
                "productos_comunes": comunes,
                "categorias_comunes": sorted(cats),
                "descuentos": f'{a["descuento_pct"]} vs {b["descuento_pct"]}',
                "ambas_no_acumulables": ("NO_ACUMULAR" in a["combinable"].upper())
                                        and ("NO_ACUMULAR" in b["combinable"].upper()),
                "estado": "PENDIENTE_VALIDACION",
            })
    return cols


def _backup_si_existe(path):
    if path.exists():
        bdir = path.parent / "_backups"
        bdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(path), str(bdir / f"{path.stem}_{_ts()}{path.suffix}"))


def escribir_salida(indir, mes, reglas, colisiones, src, mapa_ok):
    outdir = indir / "salida"
    outdir.mkdir(parents=True, exist_ok=True)

    cat_path = outdir / f"catalogo_acciones_{mes}.json"
    col_json = outdir / f"reporte_colisiones_{mes}.json"
    col_csv  = outdir / f"reporte_colisiones_{mes}.csv"
    for p in (cat_path, col_json, col_csv):
        _backup_si_existe(p)

    errores_cierre = [r["id_accion"] for r in reglas if not r["_aplica_cierre_mes_ok"]]
    con_excluidos  = [r["id_accion"] for r in reglas if r["_menciona_vendedores_excluidos"]]

    catalogo = {
        "mes": mes,
        "fuente": src.name,
        "generado_en": datetime.now(_ARG).isoformat(timespec="seconds"),
        "total_reglas": len(reglas),
        "mapeo_marca_categoria_disponible": mapa_ok,
        "aplica_cierre_mes": "NO (todas)" if not errores_cierre else "REVISAR",
        "validacion": {
            "reglas_con_aplica_cierre_mes_distinto_de_NO": errores_cierre,
            "reglas_que_mencionan_V2_V5_V20": con_excluidos,
            "vendedores_activos": sorted(VEND_ACTIVOS),
            "vendedores_excluidos": sorted(VEND_EXCLUIDOS),
        },
        "reglas": reglas,
    }
    cat_path.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")

    n_dir = sum(1 for c in colisiones if c["tipo"] == "DIRECTA")
    n_sem = sum(1 for c in colisiones if c["tipo"] == "SEMANTICA_LINEA_MARCA")
    reporte = {
        "mes": mes,
        "generado_en": datetime.now(_ARG).isoformat(timespec="seconds"),
        "total_colisiones": len(colisiones),
        "colisiones_directas": n_dir,
        "colisiones_semanticas": n_sem,
        "mapeo_marca_categoria_disponible": mapa_ok,
        "criterio": "vendedor & canal & (producto directo | categoria via maestro). No se acumulan descuentos; PENDIENTE_VALIDACION.",
        "colisiones": colisiones,
    }
    col_json.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(col_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tipo", "accion_a", "accion_b", "vendedores_comunes", "canales_comunes",
                    "productos_comunes", "categorias_comunes", "descuentos",
                    "ambas_no_acumulables", "estado"])
        for c in colisiones:
            w.writerow([c["tipo"], c["accion_a"], c["accion_b"], "|".join(c["vendedores_comunes"]),
                        "|".join(c["canales_comunes"]), "|".join(c["productos_comunes"]),
                        "|".join(c["categorias_comunes"]), c["descuentos"],
                        c["ambas_no_acumulables"], c["estado"]])

    return outdir, cat_path, col_json, col_csv, errores_cierre, con_excluidos, n_dir, n_sem


def main():
    mes = sys.argv[1] if len(sys.argv) > 1 else "2026-06"
    indir, src, rows = cargar_mes(mes)
    linea_to_cats, mapa_ok = cargar_mapa_categorias()
    reglas = normalizar(rows, linea_to_cats)
    colisiones = detectar_colisiones(reglas)
    outdir, cat_path, col_json, col_csv, err_cierre, con_excl, n_dir, n_sem = escribir_salida(
        indir, mes, reglas, colisiones, src, mapa_ok)

    print(f"[OK] Mes {mes} · fuente {src.name}")
    print(f"  Reglas cargadas: {len(reglas)}")
    print(f"  Mapeo marca->categoría disponible: {mapa_ok} ({len(linea_to_cats)} líneas)")
    print(f"  aplica_cierre_mes != NO: {err_cierre or 'ninguna'}")
    print(f"  reglas con V2/V5/V20: {con_excl or 'ninguna'}")
    print(f"  Colisiones: {len(colisiones)}  (directas={n_dir}, semánticas={n_sem})  PENDIENTE_VALIDACION")
    print(f"  Catálogo:  {cat_path}")
    print(f"  Colisiones JSON: {col_json}")
    print(f"  Colisiones CSV:  {col_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
