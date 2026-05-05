from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd


class LegacyPenaflorAdapter:
    """
    Adaptador puente entre Orbit y el script legacy de la matinal Peñaflor.

    Objetivo de esta primera versión:
    - Conectarse a orbit_matinal_v42.py sin modificar su lógica.
    - Poder reutilizar sus funciones de carga.
    - Dejar lista una base segura para el pipeline nuevo.

    IMPORTANTE:
    - Este adapter NO reemplaza el script legacy.
    - Este adapter NO ejecuta aún toda la matinal desde Orbit.
    - Este adapter solo encapsula la carga y acceso al módulo legacy.
    """

    def __init__(self, legacy_file: str | Path | None = None) -> None:
        self.project_root = Path(__file__).resolve().parents[3]
        self.legacy_file = Path(legacy_file) if legacy_file else self.project_root / "legacy" / "orbit_matinal_v42.py"
        self._legacy_module = None

    # =========================================================
    # CARGA DEL MÓDULO LEGACY
    # =========================================================
    def _load_legacy_module(self):
        """
        Carga dinámicamente el archivo legacy/orbit_matinal_v42.py
        sin necesidad de moverlo ni convertirlo en paquete Python.
        """
        if self._legacy_module is not None:
            return self._legacy_module

        if not self.legacy_file.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo legacy esperado en: {self.legacy_file}"
            )

        spec = importlib.util.spec_from_file_location("orbit_matinal_v42_legacy", str(self.legacy_file))
        if spec is None or spec.loader is None:
            raise ImportError(f"No se pudo crear spec para el módulo legacy: {self.legacy_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._legacy_module = module
        return module

    # =========================================================
    # VALIDACIÓN BÁSICA
    # =========================================================
    def validar_legacy(self) -> Dict[str, Any]:
        """
        Verifica que el archivo legacy exista y exponga las funciones clave.
        """
        module = self._load_legacy_module()

        funciones_requeridas = [
            "cargar_clientes",
            "cargar_ventas",
            "cargar_resultado",
            "cargar_productos",
            "main",
        ]

        estado = {
            "legacy_file": str(self.legacy_file),
            "legacy_exists": self.legacy_file.exists(),
            "functions": {},
        }

        for fn in funciones_requeridas:
            estado["functions"][fn] = hasattr(module, fn)

        return estado

    # =========================================================
    # CARGA DE DATOS LEGACY
    # =========================================================
    def cargar_clientes(self) -> pd.DataFrame:
        module = self._load_legacy_module()
        return module.cargar_clientes(str(module.INPUT_CLIENTES))

    def cargar_ventas(self) -> pd.DataFrame:
        module = self._load_legacy_module()
        return module.cargar_ventas(str(module.INPUT_VENTAS))

    def cargar_resultado(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        module = self._load_legacy_module()
        return module.cargar_resultado(str(module.INPUT_RESULTADO))

    def cargar_productos(self) -> pd.DataFrame:
        module = self._load_legacy_module()
        return module.cargar_productos(str(module.INPUT_PRODUCTOS))

    def cargar_todo(self) -> Dict[str, pd.DataFrame]:
        """
        Devuelve todas las tablas base que hoy consume la matinal legacy.
        """
        clientes = self.cargar_clientes()
        ventas = self.cargar_ventas()
        avance, rechazos = self.cargar_resultado()
        productos = self.cargar_productos()

        return {
            "clientes": clientes,
            "ventas": ventas,
            "avance": avance,
            "rechazos": rechazos,
            "productos": productos,
        }

    # =========================================================
    # EJECUCIÓN LEGACY COMPLETA
    # =========================================================
    def ejecutar_matinal_legacy(self) -> Dict[str, Any]:
        """
        Ejecuta el script legacy completo usando su main() actual.

        Esto sirve para validar que Orbit puede disparar el legacy sin romperlo.
        """
        module = self._load_legacy_module()

        if not hasattr(module, "main"):
            raise AttributeError("El módulo legacy no tiene función main().")

        module.main()

        output_file = getattr(module, "OUTPUT_FILE", None)
        history_file = getattr(module, "HISTORY_FILE", None)

        return {
            "status": "ok",
            "output_file": str(output_file) if output_file else "",
            "history_file": str(history_file) if history_file else "",
        }


if __name__ == "__main__":
    adapter = LegacyPenaflorAdapter()

    print("=== VALIDACIÓN LEGACY ===")
    validacion = adapter.validar_legacy()
    for k, v in validacion.items():
        print(f"{k}: {v}")

    print("\n=== CARGA BÁSICA ===")
    data = adapter.cargar_todo()
    for nombre, df in data.items():
        print(f"{nombre}: {len(df)} filas")