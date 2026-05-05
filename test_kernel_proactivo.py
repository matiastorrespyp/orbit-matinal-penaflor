import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
PROACTIVE_PATH = BASE_DIR / "src" / "orbit" / "proactive"

sys.path.append(str(PROACTIVE_PATH))

from orbit_kernel_proactivo import Kernel

kernel = Kernel()
resultado = kernel.run()
print(resultado)