import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
RENDER_PATH = BASE_DIR / "src" / "orbit" / "render"

sys.path.append(str(RENDER_PATH))

from pav_render_orbit import OrbitPavRenderer

renderer = OrbitPavRenderer()
resultado = renderer.run()
print(resultado)