from pathlib import Path
import pandas as pd


class OrbitKernelProactivo:

    def __init__(self):
        self.base = Path(__file__).resolve().parents[3]

        self.clientes = self.base / "04_DATASETS_ORBIT" / "clientes_dia.csv"
        self.t11 = self.base / "04_DATASETS_ORBIT" / "mod_11_titulares.csv"

        self.out = self.base / "06_KERNEL_OUTPUT" / "kernel_output.csv"

    def read(self, path):
        try:
            return pd.read_csv(path)
        except:
            return pd.read_csv(path, encoding="latin1")

    def clean_id(self, x):
        if pd.isna(x):
            return ""
        s = str(x)
        s = "".join(filter(str.isdigit, s))
        return str(int(s)) if s else ""

    def nv(self, v):
        s = str(v)
        n = "".join(filter(str.isdigit, s))
        return f"V{int(n)}" if n else "SIN_VENDEDOR"

    def run(self):

        print("KERNEL EJECUTANDO")

        c = self.read(self.clientes)
        t = self.read(self.t11)

        # =========================
        # NORMALIZAR IDS
        # =========================

        c["cliente_id"] = c["codigo"].apply(self.clean_id)
        t["cliente_id"] = t["cliente_id"].apply(self.clean_id)

        # =========================
        # BASE REAL
        # =========================

        base = pd.DataFrame()
        base["cliente_id"] = c["cliente_id"]
        base["cliente"] = c["razon_social"] if "razon_social" in c.columns else ""
        base["vendedor"] = c["codven"].apply(self.nv)

        base = base.drop_duplicates()

        print("Clientes base:", len(base))

        # =========================
        # 11T (REAL DRIVER)
        # =========================

        falt = t[t["falta_flag"] == 1]

        falt_agg = falt.groupby("cliente_id").size().reset_index(name="faltantes_11t")

        base = base.merge(falt_agg, on="cliente_id", how="left")

        base["faltantes_11t"] = base["faltantes_11t"].fillna(0)

        # =========================
        # SCORE
        # =========================

        base["score"] = base["faltantes_11t"] * 10

        def nivel(x):
            if x >= 30:
                return "ALTA"
            if x >= 10:
                return "MEDIA"
            return "BAJA"

        base["prioridad"] = base["score"].apply(nivel)

        # =========================
        # DECISION
        # =========================

        def decision(r):
            if r["faltantes_11t"] > 0:
                return "visitar y completar 11T"
            return "mantenimiento"

        base["decision"] = base.apply(decision, axis=1)

        # =========================
        # LIMPIEZA
        # =========================

        base = base[~base["vendedor"].isin(["V2", "V5"])]

        base = base.sort_values(by=["vendedor", "score"], ascending=[True, False])

        base.to_csv(self.out, index=False)

        print(f"✔ Kernel generado: {self.out}")
        print(f"Filas: {len(base)}")

        return base


if __name__ == "__main__":
    OrbitKernelProactivo().run()