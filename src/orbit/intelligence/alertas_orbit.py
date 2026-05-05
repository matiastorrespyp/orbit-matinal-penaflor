from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd


class OrbitAlertEngine:
    """
    Primer motor de inteligencia Orbit.

    Lee datasets ya exportados por datasets_orbit.py y genera:
    - alertas priorizadas
    - foco resumido por vendedor

    Objetivo:
    - no tocar la matinal legacy
    - trabajar arriba de datasets ya consolidados
    - preparar base para agente vendedor
    """

    def __init__(
        self,
        base_dir: str | Path = r"C:\Orbit\MATINAL_PENAFLOR",
        datasets_dir: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.datasets_dir = Path(datasets_dir) if datasets_dir else self.base_dir / "04_DATASETS_ORBIT"
        self.output_dir = Path(output_dir) if output_dir else self.base_dir / "05_INTELLIGENCE_ORBIT"

    # =========================================================
    # HELPERS
    # =========================================================
    def _ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _read_csv(self, filename: str) -> pd.DataFrame:
        path = self.datasets_dir / filename
        if not path.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(path)

    @staticmethod
    def _safe_text(value) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    @staticmethod
    def _safe_num(value) -> float:
        try:
            if pd.isna(value):
                return 0.0
            if isinstance(value, str):
                value = value.strip().replace("%", "").replace("$", "")
                value = value.replace(".", "").replace(",", ".") if "," in value else value
            return float(value)
        except Exception:
            return 0.0

    # =========================================================
    # CARGA DE DATASETS
    # =========================================================
    def load_sources(self) -> Dict[str, pd.DataFrame]:
        return {
            "clientes_dia": self._read_csv("clientes_dia.csv"),
            "mod_volumen_vendedor": self._read_csv("mod_volumen_vendedor.csv"),
            "mod_alertas_descuentos": self._read_csv("mod_alertas_descuentos.csv"),
            "resumen_alertas_vend": self._read_csv("resumen_alertas_vend.csv"),
            "mod_eficiencia_desc": self._read_csv("mod_eficiencia_desc.csv"),
            "mod_inversion_desc": self._read_csv("mod_inversion_desc.csv"),
            "mod_11_titulares": self._read_csv("mod_11_titulares.csv"),
            "mod_ccc_segmento": self._read_csv("mod_ccc_segmento.csv"),
            "log_motor": self._read_csv("log_motor.csv"),
        }

    # =========================================================
    # ALERTAS PRIORIZADAS
    # =========================================================
    def build_alertas_priorizadas(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        rows = []

        # 1. Alertas de descuentos
        df_alertas_desc = data["mod_alertas_descuentos"].copy()
        if not df_alertas_desc.empty:
            for _, row in df_alertas_desc.iterrows():
                rows.append({
                    "origen": "mod_alertas_descuentos",
                    "tipo_alerta": "descuento",
                    "prioridad": "alta",
                    "vendedor": self._pick(row, ["vendedor", "vendedor_nombre", "nombre_vendedor"]),
                    "cliente": self._pick(row, ["cliente", "cliente_nombre", "razon_social"]),
                    "producto": self._pick(row, ["articulo", "producto", "producto_nombre"]),
                    "detalle": self._build_detalle_descuento(row),
                    "accion_sugerida": "Revisar si el descuento está justificado, medir excedente y validar retorno comercial.",
                })

        # 2. Resumen alertas por vendedor
        df_resumen = data["resumen_alertas_vend"].copy()
        if not df_resumen.empty:
            for _, row in df_resumen.iterrows():
                vendedor = self._pick(row, ["vendedor", "vendedor_nombre", "nombre_vendedor"])
                cantidad = self._pick_num(row, ["cantidad_alertas", "alertas", "total_alertas"])
                if cantidad > 0:
                    prioridad = "alta" if cantidad >= 3 else "media"
                    rows.append({
                        "origen": "resumen_alertas_vend",
                        "tipo_alerta": "vendedor",
                        "prioridad": prioridad,
                        "vendedor": vendedor,
                        "cliente": "",
                        "producto": "",
                        "detalle": f"{vendedor} tiene {int(cantidad)} alertas activas.",
                        "accion_sugerida": "Priorizar revisión de alertas de su cartera al inicio de la jornada.",
                    })

        # 3. Eficiencia de descuentos
        df_ef = data["mod_eficiencia_desc"].copy()
        if not df_ef.empty:
            low_cols = [c for c in df_ef.columns if "eficien" in c or "roi" in c or "retorno" in c]
            for _, row in df_ef.iterrows():
                bandera_baja = False
                valor_metrico = None

                for col in low_cols:
                    val = self._safe_num(row.get(col))
                    valor_metrico = val
                    if val < 0:
                        bandera_baja = True
                        break

                if bandera_baja:
                    rows.append({
                        "origen": "mod_eficiencia_desc",
                        "tipo_alerta": "eficiencia_descuento",
                        "prioridad": "alta",
                        "vendedor": self._pick(row, ["vendedor", "vendedor_nombre"]),
                        "cliente": self._pick(row, ["cliente", "cliente_nombre"]),
                        "producto": self._pick(row, ["articulo", "producto"]),
                        "detalle": self._build_detalle_eficiencia(row, valor_metrico),
                        "accion_sugerida": "Revisar inversión aplicada, excedente de descuento y validar si generó volumen rentable.",
                    })

        out = pd.DataFrame(rows)

        if out.empty:
            out = pd.DataFrame(columns=[
                "origen", "tipo_alerta", "prioridad", "vendedor",
                "cliente", "producto", "detalle", "accion_sugerida"
            ])
            return out

        prioridad_order = {"alta": 1, "media": 2, "baja": 3}
        out["prioridad_sort"] = out["prioridad"].map(prioridad_order).fillna(9)
        out = out.sort_values(["prioridad_sort", "vendedor", "cliente"], ascending=[True, True, True]).reset_index(drop=True)
        out = out.drop(columns=["prioridad_sort"])

        return out

    # =========================================================
    # FOCO POR VENDEDOR
    # =========================================================
    def build_foco_vendedor(self, data: Dict[str, pd.DataFrame], alertas_df: pd.DataFrame) -> pd.DataFrame:
        rows = []

        df_vol = data["mod_volumen_vendedor"].copy()
        df_resumen = data["resumen_alertas_vend"].copy()
        df_11t = data["mod_11_titulares"].copy()

        vendedores = set()

        for df in [df_vol, df_resumen, df_11t]:
            if not df.empty:
                for col in ["vendedor", "vendedor_nombre", "nombre_vendedor"]:
                    if col in df.columns:
                        vendedores.update(df[col].dropna().astype(str).str.strip().tolist())

        vendedores = sorted(v for v in vendedores if v)

        for vendedor in vendedores:
            alertas_v = alertas_df.loc[alertas_df["vendedor"].astype(str).str.strip() == vendedor].copy() if not alertas_df.empty else pd.DataFrame()

            total_alertas = len(alertas_v)
            alertas_altas = len(alertas_v.loc[alertas_v["prioridad"] == "alta"]) if not alertas_v.empty else 0

            foco_principal = "Seguimiento general"
            if total_alertas > 0:
                if alertas_altas > 0:
                    foco_principal = "Resolver alertas críticas"
                else:
                    foco_principal = "Revisar alertas comerciales"

            oportunidades_11t = 0
            if not df_11t.empty:
                col_v = self._find_first(df_11t.columns, ["vendedor", "vendedor_nombre", "nombre_vendedor"])
                col_pri = self._find_first(df_11t.columns, ["prioridad", "prioridad_11t"])
                if col_v and col_pri:
                    mask = df_11t[col_v].astype(str).str.strip() == vendedor
                    oportunidades_11t = len(df_11t.loc[mask & (df_11t[col_pri].astype(str).str.upper() == "ALTA")])

            volumen = 0.0
            if not df_vol.empty:
                col_v = self._find_first(df_vol.columns, ["vendedor", "vendedor_nombre", "nombre_vendedor"])
                col_vol = self._find_first(df_vol.columns, ["venta", "volumen", "importe", "neto", "total"])
                if col_v and col_vol:
                    tmp = df_vol.loc[df_vol[col_v].astype(str).str.strip() == vendedor, col_vol]
                    if not tmp.empty:
                        volumen = pd.to_numeric(tmp, errors="coerce").fillna(0).sum()

            accion_sugerida = self._build_accion_vendedor(
                total_alertas=total_alertas,
                alertas_altas=alertas_altas,
                oportunidades_11t=oportunidades_11t,
            )

            rows.append({
                "vendedor": vendedor,
                "foco_principal": foco_principal,
                "total_alertas": total_alertas,
                "alertas_alta": alertas_altas,
                "oportunidades_11t_alta": oportunidades_11t,
                "volumen_detectado": volumen,
                "accion_sugerida": accion_sugerida,
            })

        out = pd.DataFrame(rows)

        if out.empty:
            out = pd.DataFrame(columns=[
                "vendedor", "foco_principal", "total_alertas", "alertas_alta",
                "oportunidades_11t_alta", "volumen_detectado", "accion_sugerida"
            ])
            return out

        out = out.sort_values(
            ["alertas_alta", "total_alertas", "oportunidades_11t_alta", "volumen_detectado"],
            ascending=[False, False, False, False]
        ).reset_index(drop=True)

        return out

    # =========================================================
    # HELPERS DE NEGOCIO
    # =========================================================
    def _pick(self, row, candidates):
        for c in candidates:
            if c in row.index:
                val = self._safe_text(row[c])
                if val:
                    return val
        return ""

    def _pick_num(self, row, candidates):
        for c in candidates:
            if c in row.index:
                val = self._safe_num(row[c])
                if val != 0:
                    return val
        return 0.0

    @staticmethod
    def _find_first(columns, candidates):
        cols_lower = {str(c).lower(): c for c in columns}
        for cand in candidates:
            for key, real in cols_lower.items():
                if cand in key:
                    return real
        return None

    def _build_detalle_descuento(self, row) -> str:
        cliente = self._pick(row, ["cliente_nombre", "cliente", "razon_social"])
        producto = self._pick(row, ["articulo", "producto", "producto_nombre"])

        desc_aplicado = self._safe_num(row.get("descuento_aplicado_pct"))
        desc_objetivo = self._safe_num(row.get("descuento_maximo_pct"))
        excedente = self._safe_num(row.get("exceso_pct"))

        impacto = self._safe_num(row.get("valor_descuento"))

        partes = []

        if cliente:
            partes.append(f"Cliente: {cliente}")

        if producto:
            partes.append(f"Producto: {producto}")

        if desc_aplicado != 0:
            partes.append(f"Desc aplicado: {round(desc_aplicado, 2)}%")

        if desc_objetivo != 0:
            partes.append(f"Desc objetivo: {round(desc_objetivo, 2)}%")

        if excedente != 0:
            partes.append(f"Excedente: {round(excedente, 2)}%")

        if impacto != 0:
            partes.append(f"Impacto real: ${round(impacto, 0)}")

        if not partes:
            return "Alerta de descuento detectada."

        return " | ".join(partes)

    def _build_detalle_eficiencia(self, row, valor_metrico) -> str:
        cliente = self._pick(row, ["cliente", "cliente_nombre", "razon_social"])
        producto = self._pick(row, ["articulo", "producto", "producto_nombre"])

        desc_aplicado = self._pick_num(row, [
            "descuento",
            "descuento_aplicado",
            "desc_aplicado",
            "pct_descuento",
            "porc_descuento",
            "descuento_aplicado_pct",
        ])

        desc_objetivo = self._pick_num(row, [
            "descuento_objetivo",
            "desc_objetivo",
            "pct_objetivo",
            "tope_descuento",
            "descuento_pactado",
            "descuento_maximo_pct",
        ])

        excedente = 0.0
        if "exceso_pct" in row.index:
            excedente = self._safe_num(row.get("exceso_pct"))
        elif desc_aplicado != 0 and desc_objetivo != 0:
            excedente = desc_aplicado - desc_objetivo

        partes = []

        if cliente:
            partes.append(f"Cliente: {cliente}")

        if producto:
            partes.append(f"Producto: {producto}")

        if desc_aplicado != 0:
            partes.append(f"Desc aplicado: {round(desc_aplicado, 2)}%")

        if desc_objetivo != 0:
            partes.append(f"Desc objetivo: {round(desc_objetivo, 2)}%")

        if excedente != 0:
            partes.append(f"Excedente: {round(excedente, 2)}%")

        if valor_metrico is not None:
            partes.append(f"Eficiencia/ROI: {round(float(valor_metrico), 2)}")

        if not partes:
            return "Eficiencia negativa detectada."

        return " | ".join(partes)

    @staticmethod
    def _build_accion_vendedor(total_alertas: int, alertas_altas: int, oportunidades_11t: int) -> str:
        if alertas_altas >= 2:
            return "Entrar al día resolviendo descuentos/alertas críticas antes de ampliar cartera."
        if total_alertas >= 1 and oportunidades_11t >= 3:
            return "Combinar resolución de alertas con foco en clientes 11 titulares de prioridad alta."
        if oportunidades_11t >= 3:
            return "Priorizar recuperación y cierre de oportunidades 11 titulares."
        if total_alertas >= 1:
            return "Revisar alertas activas y ordenar clientes antes de salir a la calle."
        return "Sin alertas críticas. Mantener foco comercial normal y capturar oportunidades."

    # =========================================================
    # EXPORTACIÓN
    # =========================================================
    def save_outputs(self, alertas_df: pd.DataFrame, foco_df: pd.DataFrame) -> Dict[str, Path]:
        self._ensure_output_dir()

        alertas_path = self.output_dir / "orbit_alertas_priorizadas.csv"
        foco_path = self.output_dir / "orbit_foco_vendedor.csv"

        alertas_df.to_csv(alertas_path, index=False, encoding="utf-8-sig")
        foco_df.to_csv(foco_path, index=False, encoding="utf-8-sig")

        return {
            "alertas": alertas_path,
            "foco_vendedor": foco_path,
        }

    # =========================================================
    # RUN
    # =========================================================
    def run(self) -> Dict[str, object]:
        print("=== ORBIT ALERT ENGINE ===")
        print(f"Origen datasets: {self.datasets_dir}")
        print(f"Salida inteligencia: {self.output_dir}")

        data = self.load_sources()

        print("\n=== DATASETS CARGADOS ===")
        for name, df in data.items():
            print(f" - {name}: {len(df)} filas")

        alertas_df = self.build_alertas_priorizadas(data)
        foco_df = self.build_foco_vendedor(data, alertas_df)

        saved = self.save_outputs(alertas_df, foco_df)

        print("\n=== RESULTADOS ===")
        print(f" - alertas priorizadas: {saved['alertas']}")
        print(f" - foco vendedor: {saved['foco_vendedor']}")
        print(f" - total alertas: {len(alertas_df)}")
        print(f" - total vendedores: {len(foco_df)}")

        return {
            "status": "ok",
            "datasets_dir": str(self.datasets_dir),
            "output_dir": str(self.output_dir),
            "alertas_rows": len(alertas_df),
            "foco_rows": len(foco_df),
            "files": {k: str(v) for k, v in saved.items()},
        }


if __name__ == "__main__":
    engine = OrbitAlertEngine()
    result = engine.run()
    print("\n=== RESULTADO FINAL ===")
    print(result)