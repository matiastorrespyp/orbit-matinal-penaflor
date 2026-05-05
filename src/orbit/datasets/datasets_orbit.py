from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd


class OrbitDatasetBuilder:
    """
    Construye datasets Orbit a partir del Excel ya generado por la matinal legacy.

    Objetivo de esta versión:
    - NO tocar el script legacy
    - leer el Excel final de salida
    - capturar todas las hojas disponibles
    - exportarlas a CSV para que Orbit empiece a trabajar con datos intermedios

    Esto permite dar el siguiente paso:
    - análisis
    - alertas
    - ROI
    - agentes por vendedor
    """

    def __init__(
        self,
        base_dir: str | Path = r"C:\Orbit\MATINAL_PENAFLOR",
        input_excel: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.input_excel = (
            Path(input_excel)
            if input_excel
            else self.base_dir / "03_OUTPUTS" / "MATINAL_PENA_V42.xlsx"
        )
        self.output_dir = (
            Path(output_dir)
            if output_dir
            else self.base_dir / "04_DATASETS_ORBIT"
        )

    # =========================================================
    # HELPERS
    # =========================================================
    @staticmethod
    def _normalize_colname(col: str) -> str:
        col = str(col).strip()
        col = col.replace("\n", " ")
        col = col.replace("\r", " ")
        col = col.replace("%", "pct")
        col = col.replace("$", "ars")
        col = col.replace("/", "_")
        col = col.replace("-", "_")
        col = col.replace(".", "_")
        col = col.replace("(", "")
        col = col.replace(")", "")
        col = col.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        col = col.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
        col = col.replace("ñ", "n").replace("Ñ", "N")
        col = "_".join(col.split())
        return col.lower()

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out.columns = [self._normalize_colname(c) for c in out.columns]
        return out

    def _ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================
    # LECTURA DEL EXCEL
    # =========================================================
    def get_sheet_names(self) -> List[str]:
        if not self.input_excel.exists():
            raise FileNotFoundError(f"No se encontró el Excel de salida: {self.input_excel}")

        xls = pd.ExcelFile(self.input_excel)
        return xls.sheet_names

    def load_all_sheets(self) -> Dict[str, pd.DataFrame]:
        """
        Lee todas las hojas del Excel final y devuelve un dict:
        {nombre_hoja_original: dataframe}
        """
        if not self.input_excel.exists():
            raise FileNotFoundError(f"No se encontró el Excel de salida: {self.input_excel}")

        xls = pd.ExcelFile(self.input_excel)
        data = {}

        for sheet in xls.sheet_names:
            try:
                df = pd.read_excel(self.input_excel, sheet_name=sheet)
                df = self._normalize_columns(df)
                data[sheet] = df
            except Exception as e:
                print(f"[WARN] No se pudo leer la hoja '{sheet}': {e}")

        return data

    # =========================================================
    # EXPORTACIÓN
    # =========================================================
    def export_sheets_to_csv(self, sheets: Dict[str, pd.DataFrame]) -> Dict[str, Path]:
        """
        Exporta cada hoja a CSV dentro de 04_DATASETS_ORBIT
        """
        self._ensure_output_dir()
        saved = {}

        for sheet_name, df in sheets.items():
            safe_name = self._normalize_colname(sheet_name)
            output_file = self.output_dir / f"{safe_name}.csv"
            df.to_csv(output_file, index=False, encoding="utf-8-sig")
            saved[sheet_name] = output_file

        return saved

    def build_inventory(self, sheets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Genera un inventario resumen de hojas/datasets
        """
        rows = []

        for sheet_name, df in sheets.items():
            rows.append(
                {
                    "sheet_name_original": sheet_name,
                    "sheet_name_normalized": self._normalize_colname(sheet_name),
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": " | ".join(df.columns.astype(str).tolist()),
                }
            )

        return pd.DataFrame(rows)

    def save_inventory(self, inventory_df: pd.DataFrame) -> Path:
        self._ensure_output_dir()
        path = self.output_dir / "datasets_inventory.csv"
        inventory_df.to_csv(path, index=False, encoding="utf-8-sig")
        return path

    # =========================================================
    # RUN COMPLETO
    # =========================================================
    def run(self) -> Dict[str, object]:
        print("=== ORBIT DATASETS BUILDER ===")
        print(f"Excel origen: {self.input_excel}")
        print(f"Salida datasets: {self.output_dir}")

        sheets = self.load_all_sheets()
        print(f"Hojas detectadas: {len(sheets)}")

        for name, df in sheets.items():
            print(f" - {name}: {len(df)} filas / {len(df.columns)} columnas")

        saved_csv = self.export_sheets_to_csv(sheets)
        inventory_df = self.build_inventory(sheets)
        inventory_path = self.save_inventory(inventory_df)

        print("\n=== EXPORTACIÓN OK ===")
        for sheet_name, path in saved_csv.items():
            print(f" - {sheet_name} -> {path}")

        print(f"\nInventario: {inventory_path}")

        return {
            "status": "ok",
            "input_excel": str(self.input_excel),
            "output_dir": str(self.output_dir),
            "sheet_count": len(sheets),
            "csv_files": {k: str(v) for k, v in saved_csv.items()},
            "inventory_file": str(inventory_path),
        }


if __name__ == "__main__":
    builder = OrbitDatasetBuilder()
    result = builder.run()
    print("\n=== RESULTADO FINAL ===")
    print(result)