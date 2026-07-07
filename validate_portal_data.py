#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_portal_data.py — VALIDADOR de Fase 1 (Orbit Peñaflor).

QUÉ HACE
  Certifica que la capa paralela de precómputo (web_data/, generada por
  build_portal_data.py) reproduce EXACTAMENTE la salida viva de los endpoints
  productivos. Lee web_data/manifest.json, y por cada JSON precomputado:
    1. obtiene endpoint_equivalente + path del archivo + payload guardado,
    2. consulta el endpoint real equivalente (mismo código, vía test_client),
    3. compara payload guardado vs payload vivo,
    4. ignora metadata técnica y timestamps de build (ver VOLÁTILES),
    5. reporta totales + detalle por endpoint, con muestra acotada del diff.

  Exit code 0 si TODO coincide; 1 si hay alguna diferencia o error HTTP.

QUÉ **NO** HACE
  - NO modifica server_orbit.py, portal.html, requirements/render/Procfile.
  - NO toca la orbit.db de producción ni Google Sheets (ver AISLAMIENTO).
  - NO toca 01_INPUTS ni 04_DATASETS_ORBIT. NO usa nada en producción.

AISLAMIENTO (idéntico a build_portal_data.py)
  Antes de importar server_orbit se redirigen sus efectos de módulo
  (backup_orbit_db/init_db/restore_planificacion_if_empty) a un temporal
  descartable y se deshabilita Google Sheets:
    - ORBIT_DB_PATH          -> <tmp>/throwaway.db
    - ORBIT_PLAN_BACKUP_DIR  -> <tmp>/plan
    - GSHEETS_SPREADSHEET_ID / GSHEETS_CREDENTIALS_JSON -> removidas
  Si Sheets quedara habilitado, el script ABORTA.

VOLÁTILES (se ignoran en la comparación)
  - Todo el bloque _meta del archivo (no forma parte del payload productivo).
  - Dentro del payload: la clave técnica 'generado_en' (== _now_ar() del server,
    cambia en cada request). Es un timestamp de build, no un dato comercial.

USO
  cd C:\\Orbit\\MATINAL_PENAFLOR
  python validate_portal_data.py            # exit 0 = OK, 1 = diffs/errores
"""
from __future__ import annotations

import os
import sys
import json
import shutil
import tempfile
import datetime
from pathlib import Path

# La consola de Windows (cp1252) no puede encodear algunos glifos (p.ej. ✔) y el print de
# cierre rompía con UnicodeEncodeError DESPUÉS de haber escrito ya los reportes, devolviendo
# exit code ≠ 0 aunque la validación fuera correcta. Reconfigurar stdout/stderr a UTF-8
# tolerante elimina el crash sin cambiar ningún dato ni la lógica de validación.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "web_data"
MANIFEST = OUT_DIR / "manifest.json"
REPORT_JSON = OUT_DIR / "validation_report.json"
REPORT_MD = OUT_DIR / "validation_report.md"
_AR_TZ = datetime.timezone(datetime.timedelta(hours=-3))

# Claves técnicas a ignorar DENTRO del payload (timestamps de build, no datos).
VOLATILE_KEYS = {"generado_en"}

# Límites para no imprimir datasets gigantes.
MAX_DIFFS_PER_ENDPOINT = 15
MAX_VALUE_REPR = 160


def _now_iso() -> str:
    return datetime.datetime.now(_AR_TZ).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# 1) AISLAMIENTO — configurar entorno ANTES de importar server_orbit
# ---------------------------------------------------------------------------
_TMP = Path(tempfile.mkdtemp(prefix="orbit_fase1_val_"))
os.environ["ORBIT_DB_PATH"] = str(_TMP / "throwaway.db")
os.environ["ORBIT_PLAN_BACKUP_DIR"] = str(_TMP / "plan")
for _k in ("GSHEETS_SPREADSHEET_ID", "GSHEETS_CREDENTIALS_JSON"):
    os.environ.pop(_k, None)

sys.path.insert(0, str(BASE))
try:
    import server_orbit as srv  # noqa: E402
except Exception as e:  # pragma: no cover
    print(f"[VALIDATE][FATAL] No se pudo importar server_orbit: {type(e).__name__}: {e}")
    shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(1)

if getattr(srv, "gsheets_enabled", lambda: False)():
    print("[VALIDATE][FATAL] Google Sheets quedó HABILITADO; abortando por seguridad.")
    shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(1)

client = srv.app.test_client()


# ---------------------------------------------------------------------------
# 2) Normalización + diff
# ---------------------------------------------------------------------------
def strip_volatile(obj):
    """Devuelve copia de obj sin las claves volátiles (a cualquier profundidad)."""
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [strip_volatile(x) for x in obj]
    return obj


def _short(v) -> str:
    s = repr(v)
    return s if len(s) <= MAX_VALUE_REPR else s[:MAX_VALUE_REPR] + "…"


def deep_diff(saved, live, path="", out=None):
    """Diferencias saved(guardado) vs live(vivo). Lista de (path, guardado, vivo)."""
    if out is None:
        out = []
    if len(out) >= MAX_DIFFS_PER_ENDPOINT:
        return out

    # Tipos numéricos int/float se comparan por valor (no por tipo exacto).
    num = (int, float)
    if isinstance(saved, num) and isinstance(live, num) and not isinstance(saved, bool):
        if saved != live:
            out.append((path or "/", _short(saved), _short(live)))
        return out

    if type(saved) is not type(live):
        out.append((path or "/", _short(saved), _short(live)))
        return out

    if isinstance(saved, dict):
        ks, kl = set(saved), set(live)
        for k in sorted(ks - kl):
            out.append((f"{path}/{k}", "<presente>", "<ausente>"))
            if len(out) >= MAX_DIFFS_PER_ENDPOINT:
                return out
        for k in sorted(kl - ks):
            out.append((f"{path}/{k}", "<ausente>", "<presente>"))
            if len(out) >= MAX_DIFFS_PER_ENDPOINT:
                return out
        for k in sorted(ks & kl):
            deep_diff(saved[k], live[k], f"{path}/{k}", out)
            if len(out) >= MAX_DIFFS_PER_ENDPOINT:
                return out
    elif isinstance(saved, list):
        if len(saved) != len(live):
            out.append((f"{path}[len]", len(saved), len(live)))
        for i, (x, y) in enumerate(zip(saved, live)):
            deep_diff(x, y, f"{path}[{i}]", out)
            if len(out) >= MAX_DIFFS_PER_ENDPOINT:
                return out
    else:
        if saved != live:
            out.append((path or "/", _short(saved), _short(live)))
    return out


def fetch_live(url: str):
    """(status, payload|None, error|None) del endpoint real."""
    try:
        resp = client.get(url)
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"
    payload = resp.get_json(silent=True)
    if payload is None:
        return resp.status_code, None, f"respuesta no-JSON (len={len(resp.data)})"
    return resp.status_code, payload, None


# ---------------------------------------------------------------------------
# 3) Ejecución
# ---------------------------------------------------------------------------
def main() -> int:
    if not MANIFEST.exists():
        print(f"[VALIDATE][FATAL] No existe {MANIFEST}. Corré build_portal_data.py primero.")
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = manifest.get("entries", [])
    print(f"\nVALIDACIÓN Fase 1 · Orbit Peñaflor  ({_now_iso()})")
    print(f"Manifest: {MANIFEST}  ·  endpoints precomputados: {len(entries)}")
    print(f"Ignorando volátiles en payload: {sorted(VOLATILE_KEYS)}\n")

    results = []
    n_ok = n_diff = n_http = n_missing = 0

    for e in entries:
        endpoint = e.get("endpoint")
        rel = e.get("file")                       # p.ej. "web_data/xxx.json"
        fpath = BASE / rel if rel else None
        row = {"endpoint": endpoint, "file": rel, "status": None,
               "http_status": None, "num_diffs": 0, "diff_sample": [], "error": None}

        # payload guardado
        if not fpath or not fpath.exists():
            row["status"] = "ERROR"
            row["error"] = "archivo JSON precomputado no encontrado"
            n_missing += 1
            results.append(row)
            print(f"  [ERR ] {endpoint:52s} · archivo faltante: {rel}")
            continue
        saved_doc = json.loads(fpath.read_text(encoding="utf-8"))
        saved_payload = saved_doc.get("payload")

        # payload vivo
        status, live_payload, err = fetch_live(endpoint)
        row["http_status"] = status
        if err or live_payload is None or (status is not None and status >= 400):
            row["status"] = "ERROR"
            row["error"] = err or f"HTTP {status}"
            n_http += 1
            results.append(row)
            print(f"  [ERR ] {endpoint:52s} · {row['error']}")
            continue

        # comparar sin volátiles
        diffs = deep_diff(strip_volatile(saved_payload), strip_volatile(live_payload))
        if not diffs:
            row["status"] = "OK"
            n_ok += 1
            print(f"  [ OK ] {endpoint:52s} · idéntico")
        else:
            row["status"] = "DIFF"
            row["num_diffs"] = len(diffs)
            row["diff_sample"] = [
                {"path": p, "guardado": g, "vivo": v} for (p, g, v) in diffs
            ]
            n_diff += 1
            print(f"  [DIFF] {endpoint:52s} · {len(diffs)} difs (muestra ≤{MAX_DIFFS_PER_ENDPOINT})")
            for (p, g, v) in diffs[:5]:
                print(f"          {p}: guardado={g}  |  vivo={v}")
        results.append(row)

    totals = {
        "validated": len(entries),
        "ok": n_ok,
        "diff": n_diff,
        "http_errors": n_http,
        "missing_files": n_missing,
    }
    ok_all = (n_diff == 0 and n_http == 0 and n_missing == 0)

    report = {
        "phase": "fase-1-validation",
        "generated_at": _now_iso(),
        "certificado": ok_all,
        "isolation": {
            "orbit_db_path": os.environ["ORBIT_DB_PATH"],
            "orbit_plan_backup_dir": os.environ["ORBIT_PLAN_BACKUP_DIR"],
            "gsheets_enabled": bool(srv.gsheets_enabled()),
            "nota": "orbit.db de producción y Google Sheets NO tocados.",
        },
        "volatile_keys_ignored": sorted(VOLATILE_KEYS),
        "nota_meta": "El bloque _meta de cada archivo se excluye por diseño (no es payload productivo).",
        "totals": totals,
        "results": results,
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_md(report)

    print("\n" + "=" * 60)
    print(f"  Validados: {totals['validated']}   OK: {totals['ok']}   "
          f"DIFF: {totals['diff']}   HTTP-err: {totals['http_errors']}   "
          f"Faltantes: {totals['missing_files']}")
    print(f"  Certificado Fase 1: {'SÍ ✔' if ok_all else 'NO �’ (revisar report)'}")
    print(f"  Reporte: {REPORT_JSON.name} · {REPORT_MD.name}")
    print("=" * 60)
    return 0 if ok_all else 1


def _write_md(report: dict):
    t = report["totals"]
    lines = [
        "# Validación Fase 1 — Orbit Peñaflor",
        "",
        f"- **Fecha:** {report['generated_at']}",
        f"- **Certificado:** {'✅ SÍ — la capa precomputada es idéntica a producción' if report['certificado'] else '❌ NO — hay diferencias/errores'}",
        f"- **Volátiles ignorados en payload:** `{', '.join(report['volatile_keys_ignored']) or '—'}`",
        f"- **Aislamiento:** gsheets_enabled={report['isolation']['gsheets_enabled']} (orbit.db real y Sheets NO tocados)",
        "",
        "## Totales",
        "",
        "| Validados | OK | DIFF | HTTP-err | Faltantes |",
        "|-----------|----|------|----------|-----------|",
        f"| {t['validated']} | {t['ok']} | {t['diff']} | {t['http_errors']} | {t['missing_files']} |",
        "",
    ]
    problemas = [r for r in report["results"] if r["status"] != "OK"]
    if problemas:
        lines += ["## Endpoints con diferencias / errores", ""]
        for r in problemas:
            lines.append(f"### `{r['endpoint']}` — {r['status']}")
            if r.get("error"):
                lines.append(f"- error: {r['error']}")
            if r.get("num_diffs"):
                lines.append(f"- diferencias: {r['num_diffs']} (muestra):")
                lines.append("")
                lines.append("| path | guardado | vivo |")
                lines.append("|------|----------|------|")
                for d in r["diff_sample"]:
                    g = str(d["guardado"]).replace("|", "\\|")
                    v = str(d["vivo"]).replace("|", "\\|")
                    lines.append(f"| `{d['path']}` | {g} | {v} |")
            lines.append("")
    else:
        lines += ["## Detalle", "", "Todos los endpoints precomputados coinciden con la salida viva. ✅", ""]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(rc)
