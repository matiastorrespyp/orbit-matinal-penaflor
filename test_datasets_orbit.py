import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
DATASETS_PATH = BASE_DIR / "src" / "orbit" / "datasets"

sys.path.append(str(DATASETS_PATH))

from datasets_orbit import OrbitDatasetBuilder

builder = OrbitDatasetBuilder()
resultado = builder.run()
print(resultado)