#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_portal_data.py — FASE 1 de migración Orbit Peñaflor (capa paralela de precómputo).

QUÉ HACE
  Genera JSON estáticos en web_data/ a partir de los MISMOS endpoints derivables de
  bajo riesgo (Grupo A de AUDITORIA_MIGRACION_PENAFLOR.md). Están pensados para
  COMPARARSE contra la salida viva de /api/... — todavía NO se usan en producción.

QUÉ **NO** HACE (Fase 1)
  - NO modifica server_orbit.py, portal.html, requirements.txt, render.yaml ni Procfile.
  - NO reemplaza endpoints. NO cambia el comportamiento productivo del portal.
  - NO toca la orbit.db de producción ni Google Sheets (ver AISLAMIENTO).
  - NO toca 01_INPUTS. NO hace git add.

CÓMO LOGRA FIDELIDAD TOTAL (cero divergencia de lógica)
  Reutiliza el código real del server: importa server_orbit y llama sus endpoints por
  medio del test_client de Flask (no levanta ningún servidor). La salida es idéntica a
  la de producción porque es LA MISMA función; no se reimplementa ninguna regla comercial
  (vendedores activos, exclusiones, cobertura 3/6 botellas, CCC neto>0, 11T, innovaciones).

AISLAMIENTO (por qué es seguro importar server_orbit)
  server_orbit.py, a nivel de módulo, ejecuta backup_orbit_db() + init_db() +
  restore_planificacion_if_empty(). Para NO tocar la base ni las hojas de producción,
  ANTES de importar redirigimos esos efectos a un directorio temporal descartable y
  dejamos Google Sheets deshabilitado (sin credenciales -> gsheets_enabled()=False):
    - ORBIT_DB_PATH          -> <tmp>/throwaway.db   (SQLite descartable, NO la real)
    - ORBIT_PLAN_BACKUP_DIR  -> <tmp>/plan           (backups descartables)
    - GSHEETS_SPREADSHEET_ID / GSHEETS_CREDENTIALS_JSON -> removidas del entorno
  Además, los endpoints del Grupo A sólo leen CSV de 04_DATASETS_ORBIT/: no consultan
  SQLite ni Sheets en ningún caso.

USO
  cd C:\\Orbit\\MATINAL_PENAFLOR
  python build_portal_data.py
  -> escribe web_data/<nombre>.json y web_data/manifest.json
"""
from __future__ import annotations

import os
import sys
import json
import time
import hashlib
import tempfile
import shutil
import datetime
import urllib.parse
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "web_data"
_AR_TZ = datetime.timezone(datetime.timedelta(hours=-3))


def _now_iso() -> str:
    return datetime.datetime.now(_AR_TZ).isoformat(timespec="seconds")


def _slug(val: str) -> str:
    """Nombre de archivo seguro y estable a partir de un valor de query (p.ej. un segmento).
    'ON PREMISE' -> 'on_premise'. No se usa para la URL (esa va url-encodeada)."""
    s = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(val))
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_") or "sin_valor"


# ---------------------------------------------------------------------------
# 1) AISLAMIENTO — configurar el entorno ANTES de importar server_orbit
# ---------------------------------------------------------------------------
_TMP = Path(tempfile.mkdtemp(prefix="orbit_fase1_"))
os.environ["ORBIT_DB_PATH"] = str(_TMP / "throwaway.db")
os.environ["ORBIT_PLAN_BACKUP_DIR"] = str(_TMP / "plan")
# Garantizar Sheets deshabilitado (no heredar credenciales de una sesión previa).
for _k in ("GSHEETS_SPREADSHEET_ID", "GSHEETS_CREDENTIALS_JSON"):
    os.environ.pop(_k, None)

# Importar el server como módulo (NO arranca gunicorn/app.run: está bajo __main__).
sys.path.insert(0, str(BASE))
try:
    import server_orbit as srv  # noqa: E402
except Exception as e:  # pragma: no cover
    print(f"[FASE1][FATAL] No se pudo importar server_orbit: {type(e).__name__}: {e}")
    shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(1)

# Sanidad del aislamiento: si por lo que sea Sheets quedó habilitado, abortar para no
# arriesgar contacto con producción.
if getattr(srv, "gsheets_enabled", lambda: False)():
    print("[FASE1][FATAL] Google Sheets quedó HABILITADO; abortando por seguridad.")
    shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(1)

# Vendedores activos = ÚNICA fuente de verdad, tomada del propio server.
#   {"V3","V4","V6","V7","V8","V9","V10"}  (excluye V2, V5, V20)
_ACTIVOS = getattr(srv, "_VENDEDORES_ACTIVOS_PLAN", {"V3", "V4", "V6", "V7", "V8", "V9", "V10"})
VENDEDORES = [v for v in ("V3", "V4", "V6", "V7", "V8", "V9", "V10") if v in _ACTIVOS]

client = srv.app.test_client()


# ---------------------------------------------------------------------------
# 2) CATÁLOGO — sólo Grupo A (derivables puros de CSV, bajo riesgo)
#    source_files: tomado de AUDITORIA_MIGRACION_PENAFLOR.md §4.4
# ---------------------------------------------------------------------------
def _p(*names):
    return [f"04_DATASETS_ORBIT/{n}" for n in names]

# Endpoints globales (sin path param ni query obligatoria)
GLOBAL = [
    dict(name="gastos_accion",              url="/api/gastos_accion",
         source_files=_p("mod_gastos_accion.csv")),
    dict(name="gerencia_planes_autoservicio", url="/api/gerencia/planes_autoservicio",
         source_files=_p("mod_gastos_accion.csv")),
    dict(name="gerencia_planes_as",         url="/api/gerencia/planes_as",
         source_files=_p("mod_planes_as.csv", "mod_sincargos_envios.csv")),
    dict(name="gerencia_innovaciones_segmento", url="/api/gerencia/innovaciones_segmento",
         source_files=_p("mod_innovaciones_segmento.csv")),
    dict(name="gerencia_11t_empresa",       url="/api/gerencia/11t_empresa",
         source_files=_p("mod_11_titulares.csv")),
    dict(name="gerencia_11t_acum",          url="/api/gerencia/11t_acum",
         source_files=_p("mod_11t_acum.csv")),
    dict(name="gerencia_cobertura_segmento", url="/api/gerencia/cobertura_segmento",
         source_files=_p("clientes_dia.csv")),
    dict(name="gerencia_cobertura_acum",    url="/api/gerencia/cobertura_acum",
         source_files=_p("mod_cobertura_acum.csv")),
    dict(name="gerencia_real_ayer_segmento", url="/api/gerencia/real_ayer_segmento",
         source_files=_p("mod_ccc_segmento.csv") + ["09_CONFIG/vendedores_activos.csv"]),
]

# Endpoints por vendedor (se genera un JSON por vendedor activo)
PER_VENDOR = [
    dict(name="vendedor_cobertura_acum",      url_t="/api/vendedor/{vid}/cobertura_acum",
         source_files=_p("mod_cobertura_acum.csv", "mod_cobertura_acum_detalle.csv")),
    dict(name="vendedor_planes_as",           url_t="/api/vendedor/{vid}/planes_as",
         source_files=_p("mod_planes_as.csv")),
    dict(name="vendedor_innovaciones_segmento", url_t="/api/vendedor/{vid}/innovaciones_segmento",
         source_files=_p("mod_innovaciones_segmento.csv")),
    dict(name="vendedor_plan_innovaciones",   url_t="/api/vendedor/{vid}/plan_innovaciones",
         source_files=_p("mod_innovaciones_segmento.csv", "clientes_dia.csv")
                      + ["05_MASTER_DATA/clientes_master.csv"]),
]

# Endpoints con query obligatoria ?vendedor= (se genera un JSON por vendedor activo)
PER_VENDOR_QUERY = [
    dict(name="gerencia_11t_vendedor", url_t="/api/gerencia/11t_vendedor?vendedor={vid}",
         source_files=_p("mod_11_titulares.csv")),
]

# --- Fase 1.2: endpoints con query arg ENUMERABLE desde los datos ---
# Se genera UN JSON por VALOR. El set de valores NO se hardcodea: se deriva de la MISMA
# fuente y de la MISMA lógica del server (se reutiliza srv.read_csv + el helper real del
# endpoint), de modo que respeta exclusiones V2/V5/V20 y no reimplementa ninguna regla
# comercial. Cada valor se consulta url-encodeado y se valida contra el endpoint vivo.
def _enum_segmentos_cobertura_faltantes():
    """Segmentos que realmente producen faltantes tras exclusiones, tomados del propio server.
    Reusa srv._cobertura_faltantes_rows (misma normalización, mismo filtro V2/V5/V20)."""
    try:
        det = srv.read_csv(srv.DATASETS / "mod_cobertura_acum_detalle.csv")
        rows = srv._cobertura_faltantes_rows(det)   # {(vid, seg): [...]}, ya excluye V2/V5/V20
        return sorted({seg for (_vid, seg) in rows.keys() if seg})
    except Exception as e:
        print(f"  [!] no se pudieron enumerar segmentos de cobertura_acum_faltantes: "
              f"{type(e).__name__}: {e}")
        return []

PER_QUERY_ENUM = [
    dict(name="gerencia_cobertura_acum_faltantes",
         url_t="/api/gerencia/cobertura_acum_faltantes?segmento={val}",
         param="segmento",
         enumerator=_enum_segmentos_cobertura_faltantes,
         source_files=_p("mod_cobertura_acum_detalle.csv")),
]

# Pendientes conocidos que TODAVÍA no se pueden certificar (se registran en el manifest).
# El drill-down por segmento de cobertura_acum_faltantes pasó a PER_QUERY_ENUM (Fase 1.2).
PENDING = []


# ---------------------------------------------------------------------------
# 3) EJECUCIÓN — llamar cada endpoint por test_client y volcar JSON + metadata
# ---------------------------------------------------------------------------
def _count(payload):
    if isinstance(payload, list):
        return len(payload), "list"
    if isinstance(payload, dict):
        return len(payload), "dict_keys"
    return None, type(payload).__name__


def _checksum(payload) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _fetch(url: str):
    """Devuelve (status, payload|None, error|None) llamando al endpoint real."""
    try:
        resp = client.get(url)
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"
    status = resp.status_code
    try:
        payload = resp.get_json(silent=True)
    except Exception:
        payload = None
    if payload is None:
        # No es JSON (o body vacío): guardamos el texto para diagnóstico, sin romper.
        return status, None, f"respuesta no-JSON (len={len(resp.data)})"
    return status, payload, None


def _emit(name: str, endpoint_url: str, source_files, payload, status):
    count, ctype = _count(payload)
    checksum = _checksum(payload)
    doc = {
        "_meta": {
            "endpoint_equivalente": endpoint_url,
            "generated_at": _now_iso(),
            "source_files": source_files,
            "http_status": status,
            "count": count,
            "count_type": ctype,
            "checksum_sha256": checksum,
            "fase": "1-precompute-paralelo",
            "uso": "COMPARAR contra /api vivo; NO usar en producción",
        },
        "payload": payload,
    }
    (OUT_DIR / f"{name}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return dict(file=f"web_data/{name}.json", endpoint=endpoint_url, http_status=status,
                count=count, count_type=ctype, checksum_sha256=checksum,
                source_files=source_files)


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    entries, errors = [], []
    t0 = time.time()

    def run(name, url, source_files):
        status, payload, err = _fetch(url)
        if err or payload is None or (status is not None and status >= 400):
            errors.append(dict(name=name, endpoint=url, http_status=status,
                               error=err or f"HTTP {status}"))
            print(f"  [!] {name:38s} {url:52s} -> {status} {err or ''}")
            return
        entry = _emit(name, url, source_files, payload, status)
        print(f"  [OK] {name:37s} {url:52s} -> {status}  "
              f"count={entry['count']} ({entry['count_type']})")
        entries.append(entry)

    print(f"\nFASE 1 · precómputo paralelo Orbit Peñaflor  ({_now_iso()})")
    print(f"Vendedores activos: {', '.join(VENDEDORES)}")
    print(f"Salida: {OUT_DIR}\n")

    print("-- Endpoints globales --")
    for ep in GLOBAL:
        run(ep["name"], ep["url"], ep["source_files"])

    print("\n-- Endpoints por vendedor --")
    for ep in PER_VENDOR + PER_VENDOR_QUERY:
        for vid in VENDEDORES:
            run(f"{ep['name']}__{vid}", ep["url_t"].format(vid=vid), ep["source_files"])

    print("\n-- Endpoints con query args (valores enumerados desde datos) --")
    pendientes_runtime = []
    for ep in PER_QUERY_ENUM:
        valores = ep["enumerator"]()
        if not valores:
            pendientes_runtime.append(dict(endpoint=ep["url_t"],
                                           motivo="enumeración vacía: sin valores en los datos"))
            print(f"  [!] {ep['name']:37s} sin valores para enumerar -> pendiente")
            continue
        print(f"  ({ep['param']}: {', '.join(valores)})")
        for val in valores:
            enc = urllib.parse.quote(str(val), safe="")     # URL segura; el server la decodifica
            url = ep["url_t"].format(val=enc)
            run(f"{ep['name']}__{_slug(val)}", url, ep["source_files"])

    manifest = {
        "phase": "fase-1-precompute",
        "generated_at": _now_iso(),
        "descripcion": ("Capa PARALELA de precómputo (Grupo A / bajo riesgo). "
                        "JSON para comparar contra la salida viva de /api/...; "
                        "NO usados en producción. server_orbit.py NO modificado."),
        "isolation": {
            "orbit_db_path": os.environ["ORBIT_DB_PATH"],
            "orbit_plan_backup_dir": os.environ["ORBIT_PLAN_BACKUP_DIR"],
            "gsheets_enabled": bool(srv.gsheets_enabled()),
            "nota": "orbit.db de producción y Google Sheets NO tocados.",
        },
        "vendedores_activos": VENDEDORES,
        "total_generados": len(entries),
        "total_errores": len(errors),
        "duracion_seg": round(time.time() - t0, 2),
        "entries": entries,
        "errores": errors,
        "pendientes": PENDING + pendientes_runtime,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nResumen: {len(entries)} JSON generados, {len(errors)} con error/omitidos.")
    print(f"Manifest: {OUT_DIR / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)   # limpiar SQLite/backup descartables
    sys.exit(rc)
