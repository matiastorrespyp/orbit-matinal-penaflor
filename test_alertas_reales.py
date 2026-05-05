import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
INTELLIGENCE_PATH = BASE_DIR / "src" / "orbit" / "intelligence"

sys.path.append(str(INTELLIGENCE_PATH))

from alertas_reales_orbit import OrbitAlertasRealesEngine

engine = OrbitAlertasRealesEngine()
resultado = engine.run()

print("\n=== RESULTADO ALERTAS REALES ===\n")
print(resultado)

input("\nPresioná Enter para cerrar...")