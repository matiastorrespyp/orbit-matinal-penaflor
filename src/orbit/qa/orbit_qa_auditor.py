from pathlib import Path
import json
from datetime import datetime

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
OUTPUT_DIR = BASE_DIR / "08_LOGS"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class OrbitQaAuditor:

    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def run(self):

        print("=== ORBIT QA AUDITOR ===")

        checks = []

        # chequeos básicos
        checks.append(("MATINAL", (BASE_DIR / "03_OUTPUTS" / "MATINAL_PENA_V42.xlsx").exists()))
        checks.append(("DATASETS", (BASE_DIR / "04_DATASETS_ORBIT").exists()))
        checks.append(("INTELLIGENCE", (BASE_DIR / "05_INTELLIGENCE_ORBIT").exists()))
        checks.append(("COPILOTO_VENDEDOR", (BASE_DIR / "06_COPILOTO_VENDEDOR_PROACTIVO").exists()))
        checks.append(("KERNEL", (BASE_DIR / "06_KERNEL_OUTPUT").exists()))
        checks.append(("PAV_HTML", (BASE_DIR / "07_PAV_OUTPUT").exists()))

        resultado = {
            "timestamp": self.timestamp,
            "checks": [],
            "status": "ok"
        }

        status_final = True

        for nombre, estado in checks:
            resultado["checks"].append({
                "modulo": nombre,
                "ok": estado
            })
            if not estado:
                status_final = False

        if status_final:
            resultado["status"] = "CONFIABLE"
        else:
            resultado["status"] = "NO_CONFIABLE"

        # guardar TXT
        txt_path = OUTPUT_DIR / "orbit_qa_resumen_latest.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("ORBIT QA AUDITOR\n")
            f.write(f"Fecha: {self.timestamp}\n\n")

            for c in resultado["checks"]:
                estado = "OK" if c["ok"] else "ERROR"
                f.write(f"{c['modulo']}: {estado}\n")

            f.write(f"\nESTADO FINAL: {resultado['status']}\n")

        # guardar JSON
        json_path = OUTPUT_DIR / "orbit_qa_resumen_latest.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)

        print(f"✔ QA generado: {txt_path}")
        print(f"Estado final: {resultado['status']}")

        return resultado


if __name__ == "__main__":
    auditor = OrbitQaAuditor()
    print(auditor.run())
