import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
ADAPTER_PATH = BASE_DIR / "src" / "orbit" / "ingest"

sys.path.append(str(ADAPTER_PATH))

from legacy_penaflor_adapter import LegacyPenaflorAdapter

adapter = LegacyPenaflorAdapter()
resultado = adapter.ejecutar_matinal_legacy()
print(resultado)