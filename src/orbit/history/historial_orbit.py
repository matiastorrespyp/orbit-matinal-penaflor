import pandas as pd
import os

BASE_DIR = r"C:\Orbit\MATINAL_PENAFLOR"
INPUT_FILE = os.path.join(BASE_DIR, "02_HISTORY", "historial_ventas.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "04_DATASETS_ORBIT")

class HistorialOrbit:

    def __init__(self):
        self.df = None

    def cargar_datos(self):
        print("Cargando historial...")
        self.df = pd.read_csv(INPUT_FILE, sep=";", encoding="latin1", low_memory=False)
        print(f"Filas cargadas: {len(self.df)}")

        # Normalización básica
        self.df.columns = self.df.columns.str.lower().str.strip()

    def preparar_datos(self):
        df = self.df.copy()

        # Detectar columnas clave (ajustable)
        col_cliente = [c for c in df.columns if "cliente" in c][0]
        col_producto = [c for c in df.columns if "producto" in c or "articulo" in c][0]
        col_fecha = [c for c in df.columns if "fecha" in c][0]
        col_cantidad = [c for c in df.columns if "cant" in c or "unidad" in c][0]

        df["cliente"] = df[col_cliente]
        df["producto"] = df[col_producto]
        df["fecha"] = pd.to_datetime(df[col_fecha], errors="coerce")
        df["cantidad"] = pd.to_numeric(df[col_cantidad], errors="coerce")

        df = df.dropna(subset=["cliente", "producto", "fecha"])

        df["mes"] = df["fecha"].dt.to_period("M").astype(str)

        self.df = df

    def generar_resumen_cliente(self):
        print("Generando resumen cliente...")

        resumen = self.df.groupby("cliente").agg({
            "cantidad": "sum",
            "fecha": "max"
        }).reset_index()

        resumen.columns = ["cliente", "volumen_total", "ultima_compra"]

        path = os.path.join(OUTPUT_DIR, "hist_cliente_resumen.csv")
        resumen.to_csv(path, index=False)

        return path

    def generar_producto_cliente(self):
        print("Generando productos por cliente...")

        prod = self.df.groupby(["cliente", "producto"]).agg({
            "cantidad": "sum"
        }).reset_index()

        path = os.path.join(OUTPUT_DIR, "hist_cliente_producto.csv")
        prod.to_csv(path, index=False)

        return path

    def generar_compra_mensual(self):
        print("Generando compra mensual...")

        mes = self.df.groupby(["cliente", "mes"]).agg({
            "cantidad": "sum"
        }).reset_index()

        path = os.path.join(OUTPUT_DIR, "hist_cliente_mes.csv")
        mes.to_csv(path, index=False)

        return path

    def ejecutar(self):
        self.cargar_datos()
        self.preparar_datos()

        outputs = {
            "resumen": self.generar_resumen_cliente(),
            "producto": self.generar_producto_cliente(),
            "mensual": self.generar_compra_mensual()
        }

        print("=== HISTORIAL GENERADO ===")
        for k, v in outputs.items():
            print(f"{k}: {v}")

        return outputs


if __name__ == "__main__":
    engine = HistorialOrbit()
    engine.ejecutar()