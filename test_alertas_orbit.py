import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
INTELLIGENCE_PATH = BASE_DIR / "src" / "orbit" / "intelligence"

sys.path.append(str(INTELLIGENCE_PATH))

from alertas_orbit import OrbitAlertEngine

engine = OrbitAlertEngine()
resultado = engine.run()
print(resultado)