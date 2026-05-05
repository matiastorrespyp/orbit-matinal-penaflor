from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import os


BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
DROPZONE = BASE_DIR / "00_DROPZONE_DIARIA"
INPUTS = BASE_DIR / "01_INPUTS"
OUTPUT = BASE_DIR / "07_PAV_OUTPUT"

# nombres destino fijos del sistema actual
DEST_VENTAS = INPUTS / "ventas_diarias.csv"
DEST_AVANCE = INPUTS / "avance_objetivos.xlsx"


class OrbitDiarioRunner:
    def __init__(self) -> None:
        DROPZONE.mkdir(parents=True, exist_ok=True)
        INPUTS.mkdir(parents=True, exist_ok=True)

    # =========================================================
    # HELPERS
    # =========================================================
    @staticmethod
    def _find_latest_file(folder: Path, patterns: list[str]) -> Path | None:
        matches = []
        for pattern in patterns:
            matches.extend(folder.glob(pattern))
        if not matches:
            return None
        return max(matches, key=lambda p: p.stat().st_mtime)

    @staticmethod
    def _run(cmd: str, name: str) -> None:
        print(f"\n=== {name} ===")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print(f"❌ Error en {name}")
            raise SystemExit(result.returncode)
        print(f"✔ {name} OK")

    @staticmethod
    def _open_file(path: Path) -> None:
        if path.exists():
            os.startfile(str(path))

    # =========================================================
    # VALIDACIÓN INPUTS
    # =========================================================
    def preparar_inputs_diarios(self) -> None:
        ventas = self._find_latest_file(
            DROPZONE,
            [
                "*ventas*.csv",
                "*detalle*comprobante*.csv",
                "*detallado*ventas*.csv",
            ],
        )

        avance = self._find_latest_file(
            DROPZONE,
            [
                "*avance*.xlsx",
                "*resultado*.xlsx",
                "*objetivo*.xlsx",
                "*resultado*.csv",
                "*avance*.csv",
            ],
        )

        if ventas is None:
            print("\n❌ Falta archivo de ventas en 00_DROPZONE_DIARIA")
            print("Pegá ahí el detalle de comprobantes / ventas del día.")
            raise SystemExit(1)

        if avance is None:
            print("\n❌ Falta archivo de avance/resultado en 00_DROPZONE_DIARIA")
            print("Pegá ahí el archivo de avance / objetivos / resultado.")
            raise SystemExit(1)

        shutil.copy2(ventas, DEST_VENTAS)

        # conserva extensión real del segundo archivo
        dest_avance_real = INPUTS / f"avance_objetivos{avance.suffix.lower()}"
        shutil.copy2(avance, dest_avance_real)

        print("\nINPUTS PREPARADOS")
        print(f"- Ventas: {ventas.name} -> {DEST_VENTAS.name}")
        print(f"- Avance: {avance.name} -> {dest_avance_real.name}")

    # =========================================================
    # EJECUCIÓN TOTAL
    # =========================================================
    def run(self) -> None:
        inicio = datetime.now()
        print("===== ORBIT DIARIO =====")
        print(f"Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")

        self.preparar_inputs_diarios()

        self._run(f'cd /d "{BASE_DIR}" && py run_orbit.py', "PIPELINE ORBIT")
        self._run(f'cd /d "{BASE_DIR}" && py test_pav_pdf.py', "PAV PDF FINAL")

        gerencia_pdf = OUTPUT / "PAV_GERENCIA.pdf"
        vendedores_dir = OUTPUT / "vendedores"
        whatsapp_dir = OUTPUT / "whatsapp"

        print("\n===== SALIDA FINAL =====")
        print(f"- Gerencia PDF: {gerencia_pdf}")
        print(f"- Vendedores PDF: {vendedores_dir}")
        print(f"- WhatsApp TXT: {whatsapp_dir}")

        # abrir salida principal automáticamente
        self._open_file(gerencia_pdf)
        self._open_file(vendedores_dir)
        self._open_file(whatsapp_dir)

        fin = datetime.now()
        print(f"\nFin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duración: {fin - inicio}")


if __name__ == "__main__":
    OrbitDiarioRunner().run()