from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
OUTPUT_XLSX = BASE_DIR / "03_OUTPUTS" / "MATINAL_PENA_V42.xlsx"
LOGS_DIR = BASE_DIR / "08_LOGS"


def run(cmd: str, name: str) -> None:
    print(f"\n=== {name} ===")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Error en {name}")
        raise SystemExit(result.returncode)
    print(f"✔ {name} OK")


def check_output_not_locked() -> None:
    if not OUTPUT_XLSX.exists():
        return
    try:
        os.rename(OUTPUT_XLSX, OUTPUT_XLSX)
    except PermissionError:
        print("\n❌ El archivo está bloqueado:")
        print(OUTPUT_XLSX)
        print("Cerrá el Excel y volvé a ejecutar.")
        raise SystemExit(1)


def ensure_paths() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def print_final_paths() -> None:
    print("\n===== SALIDAS PRINCIPALES =====")
    print(f"- Excel matinal: {BASE_DIR / '03_OUTPUTS' / 'MATINAL_PENA_V42.xlsx'}")
    print(f"- PAV gerencia PDF: {BASE_DIR / '07_PAV_OUTPUT' / 'PAV_GERENCIA.pdf'}")
    print(f"- PAV gerencia HTML: {BASE_DIR / '07_PAV_OUTPUT' / 'PAV_GERENCIA.html'}")
    print(f"- QA resumen TXT: {BASE_DIR / '08_LOGS' / 'orbit_qa_resumen_latest.txt'}")
    print(f"- QA resumen JSON: {BASE_DIR / '08_LOGS' / 'orbit_qa_resumen_latest.json'}")
    print(f"- Alertas reales CSV: {BASE_DIR / '05_INTELLIGENCE_ORBIT' / 'alertas_reales.csv'}")
    print(f"- Resumen alertas vendedor CSV: {BASE_DIR / '05_INTELLIGENCE_ORBIT' / 'alertas_reales_resumen_vendedor.csv'}")


def main() -> None:
    start = datetime.now()

    print("\n===== ORBIT RUNNER + QA =====")
    print(f"Inicio: {start.strftime('%Y-%m-%d %H:%M:%S')}")

    ensure_paths()
    os.chdir(BASE_DIR)
    check_output_not_locked()

    run("py test_legacy_run.py", "MATINAL ENGINE")
    run("py test_datasets_orbit.py", "DATASETS BUILDER")
    run("py test_alertas_orbit.py", "ALERT ENGINE")
    run(r"py src\orbit\intelligence\alertas_reales_orbit.py", "ALERTAS REALES ENGINE")
    run("py test_copiloto_vendedor.py", "COPILOTO VENDEDOR")
    run(r"py src\orbit\history\historial_orbit.py", "HISTORIAL CLIENTES")
    run(r"py src\orbit\master\clientes_master.py", "MASTER CLIENTES")
    run("py test_kernel_proactivo.py", "KERNEL PROACTIVO")
    run("py test_pav_render.py", "PAV HTML PREMIUM")
    run("py test_pav_pdf.py", "PAV PDF PREMIUM")
    run(r"py src\orbit\qa\orbit_qa_auditor.py", "ORBIT QA AUDITOR")

    end = datetime.now()

    print("\n===== ORBIT COMPLETO =====")
    print(f"Fin: {end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duración: {end - start}")

    print_final_paths()


if __name__ == "__main__":
    main()
