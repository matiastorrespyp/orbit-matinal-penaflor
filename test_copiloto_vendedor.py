import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")

# El copiloto vendedor vigente del proyecto es el proactivo.
PROACTIVE_PATH = BASE_DIR / "src" / "orbit" / "proactive"
sys.path.append(str(PROACTIVE_PATH))

from copiloto_vendedor_proactivo import OrbitSellerProactiveCopilot

copilot = OrbitSellerProactiveCopilot()
resultado = copilot.run()

print("\n=== RESULTADO COPILOTO VENDEDOR ===\n")
print(resultado)
