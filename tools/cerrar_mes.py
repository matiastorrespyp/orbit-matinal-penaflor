#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cerrar_mes.py — Genera/versiona los archivos del cierre mensual en 01_INPUTS/cierres mes/.

Toma las fuentes "vivas" del mes que se cierra y las copia con sufijo _MMAAAA, dejando
cada cierre autocontenido y sin pisar meses anteriores. NO inventa datos: solo copia los
archivos fuente reales que el usuario dejó en 01_INPUTS.

Uso:
    python tools/cerrar_mes.py            # autodetecta el mes por la fecha máx de ventas_mes.csv
    python tools/cerrar_mes.py 062026     # fuerza el mes (MMAAAA)
    python tools/cerrar_mes.py --dry-run  # muestra qué haría, sin copiar

Salida: 01_INPUTS/cierres mes/<base>_<MMAAAA>.<ext>
Backup: 99_BACKUPS_ORBIT/cierre_mes_<ts>/   (si ya existían archivos de ese mes)
Log:    99_LOGS_ORBIT/cierre_mes_<ts>.log
"""
import sys
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

# La consola de Windows suele ser cp1252 y rompe con caracteres no-ASCII.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT       = Path(__file__).resolve().parent.parent
INPUTS     = ROOT / "01_INPUTS"
CIERRES_MES = INPUTS / "cierres mes"
ACCIONES   = INPUTS / "ACCIONES COMERCIALES"
PLANES_AS  = INPUTS / "PLANES_AS"
BACKUPS    = ROOT / "99_BACKUPS_ORBIT"
LOGS       = ROOT / "99_LOGS_ORBIT"

_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
_LOG_LINES = []


def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    _LOG_LINES.append(line)


def _detectar_mmaaaa():
    """Mes a cerrar = mes de la fecha máxima de ventas_mes.csv (ISO o dd/mm/aaaa)."""
    src = INPUTS / "ventas_mes.csv"
    if not src.exists():
        return None
    try:
        df = pd.read_csv(src, sep=",", quotechar='"', engine="python", dtype=str,
                         encoding="utf-8-sig", usecols=lambda c: c.strip() == "FechaComprobante")
        df.columns = [c.strip() for c in df.columns]
        f = pd.to_datetime(df["FechaComprobante"], format="%Y-%m-%d", errors="coerce")
        if f.isna().all():
            f = pd.to_datetime(df["FechaComprobante"], dayfirst=True, errors="coerce")
        fmax = f.max()
        if pd.notna(fmax):
            return f"{fmax.month:02d}{fmax.year}"
    except Exception as e:
        log(f"  [AVISO] no se pudo autodetectar el mes: {e}")
    return None


def _buscar_acciones_csv(mmaaaa):
    """Catálogo de acciones del mes: 01_INPUTS/ACCIONES COMERCIALES/<AAAA-MM>/*.csv."""
    if not ACCIONES.exists():
        return None
    aaaa, mm = mmaaaa[2:], mmaaaa[:2]
    carpeta = ACCIONES / f"{aaaa}-{mm}"
    if not carpeta.is_dir():
        return None
    for c in sorted(carpeta.glob("*.csv")):
        n = c.name.lower()
        if "salida" in n or "_backup" in n:
            continue
        return c
    return None


def _buscar_escala():
    """Escala del Plan AS: el escala_*.xlsx más reciente en 01_INPUTS/PLANES_AS/."""
    if not PLANES_AS.exists():
        return None
    cands = sorted(PLANES_AS.glob("escala_*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    return cands[0] if cands else None


def main():
    args = [a for a in sys.argv[1:]]
    dry = "--dry-run" in args
    force = "--force" in args
    args = [a for a in args if not a.startswith("--")]

    mmaaaa = args[0].strip() if args else _detectar_mmaaaa()
    if not mmaaaa or len(mmaaaa) != 6 or not mmaaaa.isdigit():
        log("ERROR: no se pudo determinar el mes (MMAAAA). Pasalo como argumento, ej: 062026.")
        return 1
    aaaa, mm = mmaaaa[2:], mmaaaa[:2]

    log("=" * 60)
    log(f"CIERRE DE MES — {mm}/{aaaa}  (MMAAAA={mmaaaa}){'  [DRY-RUN]' if dry else ''}")
    log("=" * 60)

    # Mapeo fuente → destino versionado
    acc = _buscar_acciones_csv(mmaaaa)
    esc = _buscar_escala()
    plan = [
        (INPUTS / "resultado.xlsx",                 f"resultado_mes_{mmaaaa}.xlsx",      True),
        (INPUTS / "ventas_mes.csv",                 f"ventas_mes_{mmaaaa}.csv",          True),
        (INPUTS / "objetivo 11T.xlsx",              f"objetivo 11T_{mmaaaa}.xlsx",       True),
        # 11T es trimestral: su fuente es la acumulada (sin filtro de fecha). Opcional: si falta,
        # el portal cae a ventas_mes (1 mes) para el 11T.
        (INPUTS / "ventas_acumulada.csv",           f"ventas_acumulada_{mmaaaa}.csv",    False),
        (acc,                                       f"acciones_{mmaaaa}.csv",            False),
        (PLANES_AS / "Reconocimiento Plan As.xlsx", f"reconocimiento_{mmaaaa}.xlsx",     False),
        (esc,                                       f"escala_{mmaaaa}.xlsx",             False),
    ]

    CIERRES_MES.mkdir(parents=True, exist_ok=True)
    backup_dir = BACKUPS / f"cierre_mes_{_TS}"
    copiados, faltantes, backuped, omitidos = [], [], [], []

    # Mes ya cerrado (ya tiene archivos) y sin --force: NO se toca nada (ni se crean catálogos
    # nuevos), para no mezclar datos de otro mes en un cierre ya hecho.
    ya_existe = any((CIERRES_MES / dn).exists() for _, dn, _ in plan)
    bloqueado = ya_existe and not force
    if bloqueado:
        log(f"  [AVISO] el cierre {mm}/{aaaa} YA existe en 'cierres mes/'. No se toca nada.")
        log("          Para re-generarlo (pisando con las fuentes actuales), ejecutá con --force.")

    for src, dest_name, obligatorio in plan:
        dest = CIERRES_MES / dest_name
        if bloqueado:
            if dest.exists():
                omitidos.append(dest_name)
            continue
        if src is None or not Path(src).exists():
            nivel = "ERROR" if obligatorio else "AVISO"
            faltantes.append((dest_name, obligatorio))
            log(f"  [{nivel}] fuente no encontrada para -> {dest_name}"
                + ("" if obligatorio else " (opcional; el cierre usará fallback)"))
            continue
        if dest.exists() and not dry:
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, backup_dir / dest_name)
            backuped.append(dest_name)
        if not dry:
            shutil.copy2(src, dest)
        log(f"  OK  {Path(src).name}  ->  cierres mes/{dest_name}")
        copiados.append(dest_name)

    # Validación: que los 3 obligatorios estén
    obligatorios_faltan = [n for n, ob in faltantes if ob]
    if obligatorios_faltan:
        log("")
        log("RESULTADO: INCOMPLETO — faltan archivos obligatorios: " + ", ".join(obligatorios_faltan))
        log("El cierre del mes NO está completo. Dejá las fuentes en 01_INPUTS y volvé a ejecutar.")
        estado = "INCOMPLETO"
    else:
        log("")
        log(f"RESULTADO: OK — {len(copiados)} archivos versionados"
            + (f", {len(omitidos)} ya existían (no se pisaron)" if omitidos else "")
            + (f". Backup en {backup_dir.name}" if backuped else "") + ".")
        if [n for n, ob in faltantes if not ob]:
            log("Nota: Acciones/Planes sin catálogo del mes usarán el fallback del cierre.")
        estado = "OK"

    log("")
    log("Para ver el cierre en el portal: pantalla Cierre de Mes (se descubre solo por carpeta).")
    log("Recordá hacer commit + push de 'cierres mes/' para que Render lo tome.")

    # Escribir log
    if not dry:
        LOGS.mkdir(parents=True, exist_ok=True)
        (LOGS / f"cierre_mes_{_TS}.log").write_text("\n".join(_LOG_LINES), encoding="utf-8")

    return 0 if estado == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
