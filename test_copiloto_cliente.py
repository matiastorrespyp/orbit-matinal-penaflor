import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")

# Agregamos TODO el src al path
sys.path.append(str(BASE_DIR / "src"))

from orbit.copilot.copiloto_cliente import OrbitClientCopilot

copilot = OrbitClientCopilot()

# Cambiar cliente de prueba si querés
query = "LOPEZ"

resultado = copilot.run_for_client(query)

print("\n=== RESULTADO CLIENTE ===\n")
print(resultado)

input("\nPresioná Enter para cerrar...")