import sys
from pathlib import Path
import importlib.util

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
RENDER_PATH = BASE_DIR / "src" / "orbit" / "render"

sys.path.append(str(RENDER_PATH))


def reportlab_instalado() -> bool:
    return importlib.util.find_spec("reportlab") is not None


def main():
    if not reportlab_instalado():
        print("⚠️ ReportLab no está instalado. Se omite PAV PDF PREMIUM.")
        print({
            "status": "skipped",
            "reason": "reportlab_not_installed",
            "suggestion": r"Ejecutar: py -m pip install reportlab"
        })
        return

    from pav_pdf_orbit import OrbitPavPdf

    renderer = OrbitPavPdf()
    resultado = renderer.run()
    print(resultado)


if __name__ == "__main__":
    main()