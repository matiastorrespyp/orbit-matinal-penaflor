import pandas as pd
import os
import unicodedata

BASE_DIR = r"C:\Orbit\MATINAL_PENAFLOR"
DATASETS = os.path.join(BASE_DIR, "04_DATASETS_ORBIT")
HISTORY = os.path.join(BASE_DIR, "02_HISTORY")
OUTPUT = os.path.join(BASE_DIR, "05_MASTER_DATA")

os.makedirs(OUTPUT, exist_ok=True)


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    txt = str(valor).strip()
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("utf-8")
    txt = " ".join(txt.split())
    return txt


class ClientesMasterBuilder:

    def __init__(self):
        self.clientes_dia = pd.read_csv(os.path.join(DATASETS, "clientes_dia.csv"))
        self.historial = pd.read_csv(os.path.join(HISTORY, "historial_ventas_cliente.csv"))

    def find_col(self, df, keywords):
        cols = list(df.columns)
        cols_lower = [c.lower() for c in cols]
        for kw in keywords:
            for i, c in enumerate(cols_lower):
                if kw in c:
                    return cols[i]
        return None

    def build(self):
        print("Construyendo MASTER de clientes...")

        # === columnas clientes_dia ===
        col_id_dia = self.find_col(self.clientes_dia, ["cliente_id", "cliente", "id"])
        col_nombre_dia = self.find_col(self.clientes_dia, ["nombre"])
        col_vendedor_dia = self.find_col(self.clientes_dia, ["vendedor", "codven"])
        col_segmento_dia = self.find_col(self.clientes_dia, ["segmento"])
        col_localidad_dia = self.find_col(self.clientes_dia, ["localidad"])

        if not col_id_dia:
            raise Exception("❌ No se encontró columna ID en clientes_dia.csv")

        base_hoy = pd.DataFrame()
        base_hoy["cliente_id"] = self.clientes_dia[col_id_dia].astype(str).str.strip()

        if col_nombre_dia:
            base_hoy["cliente_nombre"] = self.clientes_dia[col_nombre_dia].apply(normalizar_texto)
        else:
            base_hoy["cliente_nombre"] = ""

        if col_vendedor_dia:
            base_hoy["vendedor"] = self.clientes_dia[col_vendedor_dia]
        else:
            base_hoy["vendedor"] = ""

        if col_segmento_dia:
            base_hoy["segmento"] = self.clientes_dia[col_segmento_dia]
        else:
            base_hoy["segmento"] = ""

        if col_localidad_dia:
            base_hoy["localidad"] = self.clientes_dia[col_localidad_dia]
        else:
            base_hoy["localidad"] = ""

        base_hoy = base_hoy.drop_duplicates(subset=["cliente_id"])

        # === columnas historial ===
        col_id_hist = self.find_col(self.historial, ["cliente_id", "cliente", "id", "negocio"])
        col_nombre_hist = self.find_col(self.historial, ["nombre", "razon", "cliente"])

        if not col_id_hist:
            raise Exception("❌ No se encontró columna ID en historial_ventas_cliente.csv")

        hist = pd.DataFrame()
        hist["cliente_id"] = self.historial[col_id_hist].astype(str).str.strip()

        if col_nombre_hist:
            hist["cliente_nombre"] = self.historial[col_nombre_hist].apply(normalizar_texto)
        else:
            hist["cliente_nombre"] = ""

        hist = hist.drop_duplicates(subset=["cliente_id"])

        # === merge principal ===
        master = hist.merge(base_hoy, on="cliente_id", how="outer", suffixes=("_hist", "_dia"))

        # nombre: priorizar día, luego histórico
        master["cliente_nombre"] = (
            master["cliente_nombre_dia"]
            .replace("", pd.NA)
            .fillna(master["cliente_nombre_hist"])
            .fillna("SIN NOMBRE")
        )

        # resto de campos
        master["vendedor"] = master["vendedor"].fillna("SIN VENDEDOR").replace("", "SIN VENDEDOR")
        master["segmento"] = master["segmento"].fillna("SIN SEGMENTO").replace("", "SIN SEGMENTO")
        master["localidad"] = master["localidad"].fillna("SIN LOCALIDAD").replace("", "SIN LOCALIDAD")

        master = master[["cliente_id", "cliente_nombre", "vendedor", "segmento", "localidad"]].copy()
        master = master.drop_duplicates(subset=["cliente_id"])

        out_file = os.path.join(OUTPUT, "clientes_master.csv")
        master.to_csv(out_file, index=False, encoding="utf-8-sig")

        print(f"✅ MASTER generado: {out_file}")
        print(f"Clientes totales: {len(master)}")

        return {
            "status": "ok",
            "output_file": out_file,
            "clientes_totales": len(master),
        }


if __name__ == "__main__":
    engine = ClientesMasterBuilder()
    result = engine.build()
    print(result)