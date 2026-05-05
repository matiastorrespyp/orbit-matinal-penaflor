from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[3]
OUTPUT_DIR = BASE_DIR / "06_KERNEL_OUTPUT"


class Kernel:
    """
    KERNEL V3 - PEÑAFLOR
    Objetivo:
    - priorizar clientes con criterio comercial real
    - generar top 20 por vendedor
    - producir decisiones accionables y no genéricas

    Archivos de salida:
    - 06_KERNEL_OUTPUT/kernel_output.csv              -> universo completo priorizado
    - 06_KERNEL_OUTPUT/kernel_top20_vendedor.csv      -> foco real por vendedor
    - 06_KERNEL_OUTPUT/kernel_resumen_vendedor.csv    -> resumen ejecutivo
    """

    def __init__(self):
        self.clientes_path = BASE_DIR / "04_DATASETS_ORBIT" / "clientes_dia.csv"
        self.t11_path = BASE_DIR / "04_DATASETS_ORBIT" / "mod_11_titulares.csv"
        self.alertas_path = BASE_DIR / "05_INTELLIGENCE_ORBIT" / "alertas_reales.csv"
        self.hist_mes_path = BASE_DIR / "04_DATASETS_ORBIT" / "hist_cliente_mes.csv"

    # =========================================================
    # IO
    # =========================================================

    def read_csv_safe(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()

        for enc in ["utf-8", "utf-8-sig", "latin1", "cp1252"]:
            try:
                return pd.read_csv(path, encoding=enc)
            except Exception:
                pass

        return pd.read_csv(path)

    # =========================================================
    # HELPERS
    # =========================================================

    def clean_id(self, x):
        if pd.isna(x):
            return ""
        s = "".join(filter(str.isdigit, str(x)))
        return str(int(s)) if s else ""

    def nv(self, v):
        s = "".join(filter(str.isdigit, str(v)))
        return f"V{int(s)}" if s else "SIN_VENDEDOR"

    def to_num(self, s, default=0):
        return pd.to_numeric(s, errors="coerce").fillna(default)

    def find_col(self, df: pd.DataFrame, patterns):
        cols = {str(c).lower().strip(): c for c in df.columns}
        for pat in patterns:
            for c_lower, c_real in cols.items():
                if pat in c_lower:
                    return c_real
        return None

    def yes_no_flag(self, series):
        if series is None:
            return pd.Series(dtype="int64")
        s = series.astype(str).str.strip().str.upper()
        true_vals = {"1", "TRUE", "SI", "S", "YES", "Y"}
        return s.isin(true_vals).astype(int)

    def scale_0_20(self, series):
        s = self.to_num(series)
        max_val = float(s.max()) if len(s) and float(s.max()) > 0 else 0.0
        if max_val <= 0:
            return pd.Series([0.0] * len(s), index=s.index)
        return (s / max_val * 20).clip(lower=0, upper=20)

    # =========================================================
    # LOAD
    # =========================================================

    def load(self):
        c = self.read_csv_safe(self.clientes_path)
        t = self.read_csv_safe(self.t11_path)
        a = self.read_csv_safe(self.alertas_path)
        h = self.read_csv_safe(self.hist_mes_path)
        return c, t, a, h

    # =========================================================
    # BASE
    # =========================================================

    def build_base(self, c: pd.DataFrame) -> pd.DataFrame:
        required = ["cliente_id", "cliente_nombre", "vendedor_codigo"]
        missing = [x for x in required if x not in c.columns]
        if missing:
            raise Exception(f"clientes_dia.csv sin columnas requeridas: {missing}")

        base = pd.DataFrame()
        base["cliente_id"] = c["cliente_id"].apply(self.clean_id)
        base["cliente_nombre"] = c["cliente_nombre"].astype(str).fillna("")
        base["vendedor"] = c["vendedor_codigo"].apply(self.nv)

        base["localidad"] = c["localidad"] if "localidad" in c.columns else ""
        base["segmento_operativo"] = c["segmento_operativo"] if "segmento_operativo" in c.columns else ""
        base["segmento_11t"] = c["segmento_11t"] if "segmento_11t" in c.columns else ""
        base["dias_visita"] = c["dias_visita"] if "dias_visita" in c.columns else ""
        base["estado_cliente"] = c["estado_cliente"] if "estado_cliente" in c.columns else ""
        base["prioridad_comercial_base"] = c["prioridad_comercial"] if "prioridad_comercial" in c.columns else ""

        base["botellas_ayer"] = self.to_num(c["botellas_ayer"]) if "botellas_ayer" in c.columns else 0
        base["importe_ayer"] = self.to_num(c["importe_ayer"]) if "importe_ayer" in c.columns else 0
        base["botellas_mes"] = self.to_num(c["botellas_mes"]) if "botellas_mes" in c.columns else 0
        base["importe_mes"] = self.to_num(c["importe_mes"]) if "importe_mes" in c.columns else 0

        base["compra_ayer_flag"] = self.yes_no_flag(c["compra_ayer_flag"]) if "compra_ayer_flag" in c.columns else 0
        base["ccc_ayer_flag"] = self.yes_no_flag(c["ccc_ayer_flag"]) if "ccc_ayer_flag" in c.columns else 0
        base["cobertura_ayer_flag"] = self.yes_no_flag(c["cobertura_ayer_flag"]) if "cobertura_ayer_flag" in c.columns else 0
        base["compra_mes_flag"] = self.yes_no_flag(c["compra_mes_flag"]) if "compra_mes_flag" in c.columns else 0
        base["ccc_mes_flag"] = self.yes_no_flag(c["ccc_mes_flag"]) if "ccc_mes_flag" in c.columns else 0
        base["cobertura_mes_flag"] = self.yes_no_flag(c["cobertura_mes_flag"]) if "cobertura_mes_flag" in c.columns else 0

        base = base.drop_duplicates(subset=["cliente_id"]).copy()
        base = base[base["cliente_id"] != ""].copy()
        base = base[~base["vendedor"].isin(["V2", "V5"])].copy()

        return base

    # =========================================================
    # 11T
    # =========================================================

    def add_11t(self, base: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
        out = base.copy()

        out["faltantes_11t"] = 0
        out["marcas_faltantes_11t"] = ""
        out["prioridad_marca_max"] = 0

        if t.empty or "cliente_id" not in t.columns:
            return out

        tt = t.copy()
        tt["cliente_id"] = tt["cliente_id"].apply(self.clean_id)

        if "falta_flag" in tt.columns:
            falt = tt[tt["falta_flag"].fillna(0).astype(int) == 1].copy()
        else:
            return out

        if falt.empty:
            return out

        agg = falt.groupby("cliente_id").agg(
            faltantes_11t=("cliente_id", "size")
        ).reset_index()

        if "prioridad_marca" in falt.columns:
            pm = falt.groupby("cliente_id")["prioridad_marca"].max().reset_index(name="prioridad_marca_max")
            agg = agg.merge(pm, on="cliente_id", how="left")
        else:
            agg["prioridad_marca_max"] = 0

        if "marca_objetivo" in falt.columns:
            marcas = (
                falt.groupby("cliente_id")["marca_objetivo"]
                .apply(lambda s: ", ".join(sorted(set([str(x).strip() for x in s if str(x).strip()]))))
                .reset_index(name="marcas_faltantes_11t")
            )
            agg = agg.merge(marcas, on="cliente_id", how="left")
        else:
            agg["marcas_faltantes_11t"] = ""

        out = out.merge(agg, on="cliente_id", how="left", suffixes=("", "_new"))

        for col in ["faltantes_11t", "prioridad_marca_max"]:
            if f"{col}_new" in out.columns:
                out[col] = self.to_num(out[f"{col}_new"])
                out.drop(columns=[f"{col}_new"], inplace=True)

        if "marcas_faltantes_11t_new" in out.columns:
            out["marcas_faltantes_11t"] = out["marcas_faltantes_11t_new"].fillna("")
            out.drop(columns=["marcas_faltantes_11t_new"], inplace=True)

        return out

    # =========================================================
    # ALERTAS
    # =========================================================

    def add_alertas(self, base: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
        out = base.copy()

        out["alertas_total"] = 0
        out["impacto_alertas_ars"] = 0
        out["tipos_alerta"] = ""
        out["alerta_sin_compra"] = 0
        out["alerta_caida_compra"] = 0

        if a.empty or "cliente_id" not in a.columns:
            return out

        aa = a.copy()
        aa["cliente_id"] = aa["cliente_id"].apply(self.clean_id)
        aa["impacto_ars"] = self.to_num(aa["impacto_ars"]) if "impacto_ars" in aa.columns else 0

        agg = aa.groupby("cliente_id").agg(
            alertas_total=("cliente_id", "size"),
            impacto_alertas_ars=("impacto_ars", "sum"),
        ).reset_index()

        if "tipo_alerta" in aa.columns:
            tipos = (
                aa.groupby("cliente_id")["tipo_alerta"]
                .apply(lambda s: " | ".join(sorted(set([str(x).strip() for x in s if str(x).strip()]))))
                .reset_index(name="tipos_alerta")
            )
            agg = agg.merge(tipos, on="cliente_id", how="left")

            flags = aa.groupby("cliente_id").agg(
                alerta_sin_compra=("tipo_alerta", lambda s: int("sin_compra_dia" in set([str(x).strip() for x in s]))),
                alerta_caida_compra=("tipo_alerta", lambda s: int("caida_compra" in set([str(x).strip() for x in s]))),
            ).reset_index()
            agg = agg.merge(flags, on="cliente_id", how="left")
        else:
            agg["tipos_alerta"] = ""
            agg["alerta_sin_compra"] = 0
            agg["alerta_caida_compra"] = 0

        out = out.merge(agg, on="cliente_id", how="left", suffixes=("", "_new"))

        for col in ["alertas_total", "impacto_alertas_ars", "alerta_sin_compra", "alerta_caida_compra"]:
            if f"{col}_new" in out.columns:
                out[col] = self.to_num(out[f"{col}_new"])
                out.drop(columns=[f"{col}_new"], inplace=True)

        if "tipos_alerta_new" in out.columns:
            out["tipos_alerta"] = out["tipos_alerta_new"].fillna("")
            out.drop(columns=["tipos_alerta_new"], inplace=True)

        return out

    # =========================================================
    # HISTORIAL
    # =========================================================

    def add_historial(self, base: pd.DataFrame, h: pd.DataFrame) -> pd.DataFrame:
        out = base.copy()
        out["importe_hist_prom"] = 0
        out["caida_vs_hist_flag"] = 0

        if h.empty:
            return out

        hh = h.copy()

        col_id = self.find_col(hh, ["cliente_id", "cliente", "codigo"])
        col_imp = self.find_col(hh, ["importe", "venta", "neto", "facturacion"])

        if not col_id or not col_imp:
            return out

        hh["cliente_id"] = hh[col_id].apply(self.clean_id)
        hh["importe_hist"] = self.to_num(hh[col_imp])

        hist = hh.groupby("cliente_id").agg(
            importe_hist_prom=("importe_hist", "mean")
        ).reset_index()

        out = out.merge(hist, on="cliente_id", how="left", suffixes=("", "_new"))

        if "importe_hist_prom_new" in out.columns:
            out["importe_hist_prom"] = self.to_num(out["importe_hist_prom_new"])
            out.drop(columns=["importe_hist_prom_new"], inplace=True)
        else:
            out["importe_hist_prom"] = self.to_num(out["importe_hist_prom"])

        out["caida_vs_hist_flag"] = (
            (out["importe_hist_prom"] > 0) &
            (out["importe_mes"] < out["importe_hist_prom"] * 0.60)
        ).astype(int)

        return out

    # =========================================================
    # SCORING
    # =========================================================

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        impacto_scaled = self.scale_0_20(out["impacto_alertas_ars"])
        hist_scaled = self.scale_0_20(out["importe_hist_prom"])
        mes_scaled = self.scale_0_20(out["importe_mes"])

        out["score"] = 0.0

        # 11T
        out["score"] += out["faltantes_11t"] * 4
        out["score"] += out["prioridad_marca_max"] * 1.5

        # sin compra / sin CCC / sin cobertura del mes
        out["score"] += (1 - out["compra_mes_flag"]) * 14
        out["score"] += (1 - out["ccc_mes_flag"]) * 10
        out["score"] += (1 - out["cobertura_mes_flag"]) * 10

        # comportamiento reciente
        out["score"] += (1 - out["compra_ayer_flag"]) * 4
        out["score"] += (1 - out["cobertura_ayer_flag"]) * 4

        # alertas reales
        out["score"] += out["alertas_total"] * 3
        out["score"] += out["alerta_sin_compra"] * 8
        out["score"] += out["alerta_caida_compra"] * 12
        out["score"] += impacto_scaled

        # historial y negocio
        out["score"] += out["caida_vs_hist_flag"] * 12
        out["score"] += hist_scaled * 0.5

        # penalización leve si ya tiene buen mes
        out["score"] -= mes_scaled * 0.2

        out["score"] = out["score"].clip(lower=0)

        def nivel(x):
            if x >= 45:
                return "ALTA"
            if x >= 25:
                return "MEDIA"
            return "BAJA"

        out["prioridad"] = out["score"].apply(nivel)

        return out

    # =========================================================
    # DECISIONES
    # =========================================================

    def build_reason(self, row):
        razones = []

        if row["alerta_caida_compra"] == 1:
            razones.append("caída de compra")
        if row["alerta_sin_compra"] == 1:
            razones.append("sin compra reciente")
        if row["caida_vs_hist_flag"] == 1:
            razones.append("debajo del histórico")
        if row["compra_mes_flag"] == 0:
            razones.append("sin compra del mes")
        if row["ccc_mes_flag"] == 0:
            razones.append("sin CCC del mes")
        if row["cobertura_mes_flag"] == 0:
            razones.append("sin cobertura del mes")
        if row["faltantes_11t"] > 0:
            razones.append("faltantes 11T")

        if not razones:
            razones.append("seguimiento comercial")

        return " | ".join(razones[:3])

    def build_decision(self, row):
        if row["alerta_caida_compra"] == 1 or row["caida_vs_hist_flag"] == 1:
            if row["marcas_faltantes_11t"]:
                return f"Recuperar ticket y completar portafolio → foco en {row['marcas_faltantes_11t']}"
            return "Recuperar ticket vs histórico"

        if row["compra_mes_flag"] == 0 and row["ccc_mes_flag"] == 0:
            if row["marcas_faltantes_11t"]:
                return f"Reactivar cliente y lograr primer pedido del mes → foco en {row['marcas_faltantes_11t']}"
            return "Reactivar cliente y lograr primer pedido del mes"

        if row["cobertura_mes_flag"] == 0:
            if row["marcas_faltantes_11t"]:
                return f"Lograr cobertura del mes → foco en {row['marcas_faltantes_11t']}"
            return "Lograr cobertura del mes"

        if row["faltantes_11t"] > 0:
            return f"Completar 11T → foco en {row['marcas_faltantes_11t']}"

        return "Seguimiento comercial"

    # =========================================================
    # TOP POR VENDEDOR
    # =========================================================

    def add_rankings(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        out = out.sort_values(
            by=["vendedor", "score", "impacto_alertas_ars", "faltantes_11t", "importe_mes"],
            ascending=[True, False, False, False, False]
        ).reset_index(drop=True)

        out["rank_vendedor"] = out.groupby("vendedor").cumcount() + 1
        out["foco_top20_flag"] = (out["rank_vendedor"] <= 20).astype(int)
        out["foco_top10_flag"] = (out["rank_vendedor"] <= 10).astype(int)

        return out

    def build_resumen_vendedor(self, df: pd.DataFrame) -> pd.DataFrame:
        resumen = (
            df.groupby("vendedor")
            .agg(
                clientes_total=("cliente_id", "size"),
                clientes_foco_top20=("foco_top20_flag", "sum"),
                score_promedio=("score", "mean"),
                impacto_total_alertas=("impacto_alertas_ars", "sum"),
                clientes_prioridad_alta=("prioridad", lambda s: int((s == "ALTA").sum())),
            )
            .reset_index()
        )
        return resumen.sort_values(by="score_promedio", ascending=False)

    # =========================================================
    # MAIN
    # =========================================================

    def run(self):
        print("KERNEL EJECUTANDO")

        c, t, a, h = self.load()

        base = self.build_base(c)
        print("Clientes base:", len(base))

        base = self.add_11t(base, t)
        base = self.add_alertas(base, a)
        base = self.add_historial(base, h)
        base = self.score(base)

        base["motivo_principal"] = base.apply(self.build_reason, axis=1)
        base["decision"] = base.apply(self.build_decision, axis=1)

        base = self.add_rankings(base)

        final_cols = [
            "cliente_id",
            "cliente_nombre",
            "vendedor",
            "rank_vendedor",
            "foco_top20_flag",
            "foco_top10_flag",
            "prioridad",
            "score",
            "motivo_principal",
            "decision",
            "localidad",
            "segmento_operativo",
            "segmento_11t",
            "dias_visita",
            "estado_cliente",
            "prioridad_comercial_base",
            "importe_ayer",
            "importe_mes",
            "importe_hist_prom",
            "faltantes_11t",
            "marcas_faltantes_11t",
            "alertas_total",
            "impacto_alertas_ars",
            "tipos_alerta",
            "caida_vs_hist_flag",
        ]

        final_cols = [c for c in final_cols if c in base.columns]
        out_df = base[final_cols].copy()

        top20_df = out_df[out_df["foco_top20_flag"] == 1].copy()
        resumen_df = self.build_resumen_vendedor(base)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        out_full = OUTPUT_DIR / "kernel_output.csv"
        out_top20 = OUTPUT_DIR / "kernel_top20_vendedor.csv"
        out_resumen = OUTPUT_DIR / "kernel_resumen_vendedor.csv"

        out_df.to_csv(out_full, index=False, encoding="utf-8-sig")
        top20_df.to_csv(out_top20, index=False, encoding="utf-8-sig")
        resumen_df.to_csv(out_resumen, index=False, encoding="utf-8-sig")

        print(f"✔ Kernel generado: {out_full}")
        print(f"✔ Top20 vendedor: {out_top20}")
        print(f"✔ Resumen vendedor: {out_resumen}")
        print(f"Filas total: {len(out_df)}")
        print(f"Filas top20: {len(top20_df)}")
        print(out_df.head(20))

        return out_df


if __name__ == "__main__":
    Kernel().run()