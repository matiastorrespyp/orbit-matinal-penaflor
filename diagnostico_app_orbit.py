# -*- coding: utf-8 -*-
"""
diagnostico_app_orbit.py
Audita los archivos fuente reales de Orbit para detectar
qué columnas existen y cuáles contienen datos útiles
para la app.

UBICACIÓN:
C:\Orbit\MATINAL_PENAFLOR\diagnostico_app_orbit.py
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

FILES = {
    "clientes_dia": BASE_DIR / "04_DATASETS_ORBIT" / "clientes_dia.csv",
    "hist_cliente_resumen": BASE_DIR / "04_DATASETS_ORBIT" / "hist_cliente_resumen.csv",
    "mod_11_titulares": BASE_DIR / "04_DATASETS_ORBIT" / "mod_11_titulares.csv",
    "mod_clientes_11t_10": BASE_DIR / "04_DATASETS_ORBIT" / "mod_clientes_11t_10.csv",
    "mod_ccc_segmento": BASE_DIR / "04_DATASETS_ORBIT" / "mod_ccc_segmento.csv",
    "mod_alertas_descuentos": BASE_DIR / "04_DATASETS_ORBIT" / "mod_alertas_descuentos.csv",
    "orbit_alertas_priorizadas": BASE_DIR / "05_INTELLIGENCE_ORBIT" / "orbit_alertas_priorizadas.csv",
    "kernel_output": BASE_DIR / "06_KERNEL_OUTPUT" / "kernel_output.csv",
    "kernel_resumen_vendedor": BASE_DIR / "06_KERNEL_OUTPUT" / "kernel_resumen_vendedor.csv",
    "kernel_top20_vendedor": BASE_DIR / "06_KERNEL_OUTPUT" / "kernel_top20_vendedor.csv",
}

OUTPUT_TXT = BASE_DIR / "08_LOGS" / "diagnostico_app_orbit.txt"
OUTPUT_TXT.parent.mkdir(parents=True, exist_ok=True)


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc)
            df.columns = [str(c).strip().lower() for c in df.columns]
            return df
        except Exception:
            continue

    return pd.DataFrame()


def to_num_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce"
    ).fillna(0)


def analyze_dataframe(name: str, df: pd.DataFrame) -> str:
    lines = []
    lines.append("=" * 90)
    lines.append(f"ARCHIVO: {name}")
    lines.append("=" * 90)

    if df.empty:
        lines.append("SIN DATOS O NO ENCONTRADO")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"FILAS: {len(df)}")
    lines.append(f"COLUMNAS: {len(df.columns)}")
    lines.append("")
    lines.append("LISTA DE COLUMNAS:")
    for col in df.columns:
        lines.append(f" - {col}")

    lines.append("")
    lines.append("COLUMNAS NUMÉRICAS CON DATOS NO CERO (TOP 30):")

    found_numeric = False
    for col in df.columns[:]:
        try:
            nums = to_num_series(df[col])
            non_zero = int((nums != 0).sum())
            total = float(nums.sum())
            maxv = float(nums.max()) if len(nums) else 0.0

            if non_zero > 0:
                found_numeric = True
                lines.append(
                    f" - {col}: non_zero={non_zero} | suma={round(total,2)} | max={round(maxv,2)}"
                )
        except Exception:
            pass

    if not found_numeric:
        lines.append(" - ninguna detectada con valores no cero")

    lines.append("")
    lines.append("MUESTRA DE 5 FILAS:")
    preview = df.head(5).fillna("")
    lines.append(preview.to_string(index=False))
    lines.append("")

    return "\n".join(lines)


def main():
    report_parts = []
    print("===== DIAGNOSTICO APP ORBIT =====")
    print("")

    for name, path in FILES.items():
        print(f"[LEYENDO] {name} -> {path}")
        df = read_csv_safe(path)
        report = analyze_dataframe(name, df)
        report_parts.append(report)

    final_report = "\n".join(report_parts)

    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write(final_report)

    print("")
    print("OK -> Diagnóstico generado en:")
    print(OUTPUT_TXT)
    print("")
    print("IMPORTANTE: abrí ese TXT y pegamelo acá completo.")
    print("Con eso te devuelvo el app_publish.py final alineado a tus columnas reales.")


if __name__ == "__main__":
    main()