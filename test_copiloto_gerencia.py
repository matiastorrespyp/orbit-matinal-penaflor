import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
COPILOT_PATH = BASE_DIR / "src" / "orbit" / "copilot"

sys.path.append(str(COPILOT_PATH))

from copiloto_gerencia_orbit import OrbitGerenciaCopilot

copilot = OrbitGerenciaCopilot()
resultado = copilot.run()

print("\n=== RESULTADO COPILOTO GERENCIA ===\n")
print(resultado)

input("\nPresioná Enter para cerrar...")
