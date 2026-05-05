# perf_engine.py - PERFORMANCE FULL ROBUSTO (FIX RESULTADO)

from __future__ import annotations
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta


class OrbitPerformanceEngine:

    def __init__(self):
        self.base = Path(__file__).resolve().parents[3]

        self.input_ventas = self.base / "01_INPUTS" / "ventas.csv"
        self.input_clientes = self.base / "01_INPUTS" / "clientes.xlsx"
        self.input_productos = self.base / "01_INPUTS" / "productos_activos.xlsx"
        self.input_resultado = self.base / "01_INPUTS" / "resultado.xlsx"

        self.out = self.base / "05_INTELLIGENCE_ORBIT"

    # =========================
    # CSV ROBUSTO
    # =========================

    def read_csv(self, path):
        for enc in ["utf-8", "latin1", "cp1252"]:
            for sep in [";", ",", "|", "\t"]:
                try:
                    df = pd.read_csv(path, encoding=enc, sep=sep, engine="python", on_bad_lines="skip")
                    if len(df.columns) > 5:
                        print(f"OK ventas -> {enc} | {sep}")
                        return df
                except:
                    pass
        raise Exception("No se pudo leer ventas.csv")

    # =========================
    # HELPERS
    # =========================

    def nv(self, v):
        s = str(v).upper().replace("VENDEDOR", "").replace("V", "")
        n = "".join(filter(str.isdigit, s))
        return f"V{int(n)}" if n else ""

    def find_col(self, cols, keys):
        for c in cols:
            for k in keys:
                if k in c:
                    return c
        return None

    def seg(self, s):
        s = str(s).lower()
        if "auto" in s: return "autoservicio"
        if "alma" in s or "kios" in s: return "tradicional"
        if "premise" in s or "bar" in s: return "on_premise"
        return "otros"

    # =========================
    # CARGA
    # =========================

    def load(self):

        v = self.read_csv(self.input_ventas)
        c = pd.read_excel(self.input_clientes)
        p = pd.read_excel(self.input_productos) if self.input_productos.exists() else pd.DataFrame()

        v.columns = [x.lower().strip() for x in v.columns]
        c.columns = [x.lower().strip() for x in c.columns]

        # ===== VENTAS =====
        v["cliente_id"] = v[self.find_col(v.columns, ["cliente"])].astype(str)
        v["vendedor"] = v[self.find_col(v.columns, ["vendedor"])].apply(self.nv)
        v["botellas"] = pd.to_numeric(v[self.find_col(v.columns, ["cant"])], errors="coerce").fillna(0)
        v["importe"] = pd.to_numeric(v[self.find_col(v.columns, ["importe", "neto"])], errors="coerce").fillna(0)
        v["fecha"] = pd.to_datetime(v[self.find_col(v.columns, ["fecha"])], errors="coerce")

        # ===== CLIENTES =====
        c["cliente_id"] = c["codigo"].astype(str)
        c["vendedor"] = c["vendedor"].apply(self.nv)
        c["segmento_norm"] = c["ramo"].apply(self.seg)

        # excluir vendedores
        v = v[~v["vendedor"].isin(["V2", "V5"])]
        c = c[~c["vendedor"].isin(["V2", "V5"])]

        # ===== RESULTADO =====
        if self.input_resultado.exists():
            r = pd.read_excel(self.input_resultado)
            r.columns = [x.lower().strip() for x in r.columns]

            col_vend = self.find_col(r.columns, ["vendedor", "codven", "vend"])

            if col_vend:
                r["vendedor"] = r[col_vend].apply(self.nv)
            else:
                print("⚠ resultado.xlsx sin columna vendedor, se ignora")
                r = pd.DataFrame()
        else:
            r = pd.DataFrame()

        return v, c, p, r

    # =========================
    # SEGMENTOS
    # =========================

    def perf_segmentos(self, v, c, fecha_obj):

        df = v.merge(c[["cliente_id", "segmento_norm", "vendedor"]], on="cliente_id", how="left", suffixes=("", "_c"))

        df["vendedor"] = df["vendedor"].fillna(df["vendedor_c"])
        df.drop(columns=["vendedor_c"], inplace=True)

        def cob(row):
            if row["segmento_norm"] == "tradicional":
                return row["botellas"] >= 3
            return row["botellas"] >= 6

        df["cob"] = df.apply(cob, axis=1)

        dia = df[df["fecha"].dt.date == fecha_obj]

        g = df.groupby(["vendedor", "segmento_norm"]).agg(
            clientes=("cliente_id", "nunique"),
            venta=("importe", "sum"),
            botellas=("botellas", "sum"),
            cobertura=("cob", "sum")
        ).reset_index()

        g_dia = dia.groupby(["vendedor", "segmento_norm"]).agg(
            clientes_dia=("cliente_id", "nunique"),
            venta_dia=("importe", "sum"),
            botellas_dia=("botellas", "sum"),
            cobertura_dia=("cob", "sum")
        ).reset_index()

        return g.merge(g_dia, how="left").fillna(0)

    # =========================
    # RESUMEN
    # =========================

    def perf_resumen(self, seg, r):

        res = seg.groupby("vendedor").agg(
            clientes=("clientes", "sum"),
            clientes_dia=("clientes_dia", "sum"),
            cobertura=("cobertura", "sum"),
            cobertura_dia=("cobertura_dia", "sum"),
            venta=("venta", "sum"),
            venta_dia=("venta_dia", "sum")
        ).reset_index()

        if not r.empty and "vendedor" in r.columns:
            res = res.merge(r, on="vendedor", how="left")

        return res

    # =========================
    # MAIN
    # =========================

    def run(self):

        print("=== PERFORMANCE FULL ===")

        v, c, p, r = self.load()

        fecha_obj = datetime.now().date() + timedelta(days=1)

        seg = self.perf_segmentos(v, c, fecha_obj)
        res = self.perf_resumen(seg, r)

        self.out.mkdir(exist_ok=True)

        seg.to_csv(self.out / "perf_segmentos.csv", index=False)
        res.to_csv(self.out / "perf_resumen_vendedor.csv", index=False)

        print("OK PERFORMANCE ESTABLE")

        return True


if __name__ == "__main__":
    OrbitPerformanceEngine().run()