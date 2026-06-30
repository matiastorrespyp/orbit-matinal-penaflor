#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
preparar_ventas_mes.py — Refresca 01_INPUTS/ventas_mes.csv (cierre congelado del mes)
re-codificando la fuente viva 01_INPUTS/ventas.csv.

Por qué existe: el cierre de mes autodetecta y versiona el mes a partir de ventas_mes.csv.
Si ese archivo queda con el mes anterior, el cierre "no hace nada" (detecta un mes ya
cerrado). Este paso deja ventas_mes.csv == ventas.csv del mes en curso, en el formato que
consume el motor del cierre:

  - separador  ;  ->  ,
  - encoding   latin1  ->  utf-8-sig
  - FechaComprobante  d/m/aaaa  ->  ISO aaaa-mm-dd   (las demás fechas se preservan)
  - el resto de columnas/valores se preservan tal cual (dtype=str, sin floats fantasma)

NO inventa datos: copia las mismas 58 columnas, fila por fila.

Uso:
    python tools/preparar_ventas_mes.py            # ventas.csv -> ventas_mes.csv
    python tools/preparar_ventas_mes.py --dry-run  # informa sin escribir
"""
import sys
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT    = Path(__file__).resolve().parent.parent
INPUTS  = ROOT / "01_INPUTS"
BACKUPS = ROOT / "99_BACKUPS_ORBIT"

SRC  = INPUTS / "ventas.csv"
DEST = INPUTS / "ventas_mes.csv"


def _leer_ventas_vivo(path):
    """Lee ventas.csv detectando encoding. Todo como str para no perder formato ni
    introducir floats (ej. RutaPreventa 8050 -> 8050.0). keep_default_na=False deja
    los vacíos como '' en vez de NaN."""
    for enc in ("latin-1", "utf-8-sig", "windows-1252"):
        try:
            df = pd.read_csv(path, sep=";", quotechar='"', engine="python",
                             dtype=str, keep_default_na=False, na_filter=False,
                             encoding=enc)
            return df, enc
        except UnicodeDecodeError:
            continue
    raise RuntimeError("No se pudo leer ventas.csv con ningún encoding conocido.")


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args

    if not SRC.exists():
        print(f"ERROR: no existe la fuente viva {SRC}.")
        return 1

    df, enc = _leer_ventas_vivo(SRC)
    df.columns = [c.strip() for c in df.columns]
    if df.empty:
        print("ERROR: ventas.csv sin filas. No se toca ventas_mes.csv.")
        return 1
    if "FechaComprobante" not in df.columns:
        print("ERROR: ventas.csv no tiene columna FechaComprobante.")
        return 1

    # FechaComprobante -> ISO aaaa-mm-dd (mismo formato que los cierres anteriores).
    f = pd.to_datetime(df["FechaComprobante"], format="%Y-%m-%d", errors="coerce")
    if f.isna().all():
        f = pd.to_datetime(df["FechaComprobante"], dayfirst=True, errors="coerce")
    df["FechaComprobante"] = f.dt.strftime("%Y-%m-%d").where(f.notna(), "")

    fmin, fmax = f.min(), f.max()
    meses = sorted(f.dropna().dt.to_period("M").astype(str).unique())
    print(f"Fuente : {SRC.name} ({enc}) — {len(df)} filas")
    print(f"Rango  : {fmin.date() if pd.notna(fmin) else '?'} -> {fmax.date() if pd.notna(fmax) else '?'}")
    print(f"Mes(es): {', '.join(meses) if meses else '?'}")
    if len(meses) > 1:
        print(f"  [AVISO] ventas.csv abarca {len(meses)} meses. El cierre tomará el mes de la "
              f"fecha máxima ({fmax.strftime('%m/%Y') if pd.notna(fmax) else '?'}). "
              f"Verificá que sea el mes que querés cerrar.")

    if dry:
        print(f"[DRY-RUN] escribiría {DEST.name} (sep=',', utf-8-sig). No se escribió nada.")
        return 0

    # Backup del ventas_mes.csv anterior (no se pierde el mes previo si hiciera falta).
    if DEST.exists():
        BACKUPS.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bkp = BACKUPS / f"ventas_mes_previo_{ts}.csv"
        shutil.copy2(DEST, bkp)
        print(f"Backup : {DEST.name} previo -> 99_BACKUPS_ORBIT/{bkp.name}")

    df.to_csv(DEST, sep=",", index=False, encoding="utf-8-sig")
    print(f"OK     : {DEST.name} actualizado desde {SRC.name} ({len(df)} filas, utf-8-sig).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
