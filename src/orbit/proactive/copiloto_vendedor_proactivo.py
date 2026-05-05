from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional, Dict, List

import pandas as pd


BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
DATASETS_DIR = BASE_DIR / "04_DATASETS_ORBIT"
INTELLIGENCE_DIR = BASE_DIR / "05_INTELLIGENCE_ORBIT"
HISTORY_DIR = BASE_DIR / "02_HISTORY"
OUTPUT_DIR = BASE_DIR / "06_COPILOTO_VENDEDOR_PROACTIVO"


class OrbitSellerProactiveCopilot:
    """
    Copiloto Vendedor Proactivo - Peñaflor
    ------------------------------------------------
    Objetivo:
    - detectar los 50 clientes con mayor caída semanal en vinos de alta gama
    - asignarlos por vendedor
    - generar mensaje accionable por vendedor
    - calcular descuento máximo permitido en ARS para recuperar la venta
    """

    def __init__(self, tenant: str = "PENAFLOR") -> None:
        self.tenant = tenant.upper().strip()
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================
    # HELPERS
    # =========================================================
    @staticmethod
    def _normalize(text) -> str:
        if pd.isna(text):
            return ""
        txt = str(text).strip().lower()
        txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("utf-8")
        txt = " ".join(txt.split())
        return txt

    @staticmethod
    def _safe_num(value) -> float:
        try:
            if pd.isna(value):
                return 0.0
            if isinstance(value, str):
                value = value.strip().replace("$", "").replace("%", "")
                value = value.replace(".", "").replace(",", ".") if "," in value else value
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _find_first(columns, keywords: List[str]) -> Optional[str]:
        cols = list(columns)
        cols_lower = [str(c).lower() for c in cols]
        for kw in keywords:
            for i, col in enumerate(cols_lower):
                if kw in col:
                    return cols[i]
        return None

    @staticmethod
    def _clean_filename(name: str) -> str:
        txt = str(name).strip().lower()
        txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("utf-8")
        txt = re.sub(r"[^a-z0-9]+", "_", txt)
        txt = re.sub(r"_+", "_", txt).strip("_")
        return txt or "sin_nombre"

    # =========================================================
    # CARGA
    # =========================================================
    def _read_csv_any(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()

        tries = [
            {"sep": ",", "encoding": "utf-8-sig"},
            {"sep": ";", "encoding": "utf-8-sig"},
            {"sep": ";", "encoding": "latin1"},
            {"sep": ",", "encoding": "latin1"},
        ]

        for cfg in tries:
            try:
                df = pd.read_csv(path, low_memory=False, **cfg)
                if len(df.columns) > 1:
                    return df
            except Exception:
                pass

        raise Exception(f"No se pudo leer archivo: {path}")

    def load_sources(self) -> Dict[str, pd.DataFrame]:
        hist_candidates = [
            HISTORY_DIR / "historial_ventas_cliente.csv",
            HISTORY_DIR / "historial_ventas.csv",
            HISTORY_DIR / "ventas-Detallado de ventas extendido-20260411-084213.csv",
        ]

        hist_df = pd.DataFrame()
        hist_path = None
        for p in hist_candidates:
            if p.exists():
                hist_df = self._read_csv_any(p)
                hist_path = p
                break

        if hist_df.empty:
            raise Exception("No se encontró archivo de historial de ventas en 02_HISTORY")

        alertas_path = DATASETS_DIR / "mod_alertas_descuentos.csv"
        clientes_path = DATASETS_DIR / "clientes_dia.csv"

        alertas_df = self._read_csv_any(alertas_path) if alertas_path.exists() else pd.DataFrame()
        clientes_df = self._read_csv_any(clientes_path) if clientes_path.exists() else pd.DataFrame()

        return {
            "historial": hist_df,
            "alertas_desc": alertas_df,
            "clientes_dia": clientes_df,
            "historial_path": pd.DataFrame({"path": [str(hist_path)]}),
        }

    # =========================================================
    # PREPARACIÓN HISTÓRICO
    # =========================================================
    def _prepare_historial(self, df: pd.DataFrame) -> pd.DataFrame:
        work = df.copy()
        work.columns = [str(c).strip().lower() for c in work.columns]

        col_fecha = self._find_first(work.columns, ["fecha"])
        col_cliente_id = self._find_first(work.columns, ["cliente_id", "cliente", "negocio", "id"])
        col_cliente_nombre = self._find_first(work.columns, ["cliente_nombre", "razon", "nombre"])
        col_vendedor = self._find_first(work.columns, ["vendedor", "codven", "preventa"])
        col_producto = self._find_first(work.columns, ["producto", "articulo", "descripcion"])
        col_importe = self._find_first(work.columns, ["importe_neto", "neto", "importe", "monto", "valor"])
        col_cantidad = self._find_first(work.columns, ["cantidad", "cant", "unidades", "botellas", "bultos"])

        if not col_fecha:
            raise Exception("Historial sin columna fecha")
        if not col_cliente_id:
            raise Exception("Historial sin columna de cliente")
        if not col_producto:
            raise Exception("Historial sin columna de producto")
        if not col_importe:
            raise Exception("Historial sin columna de importe")

        work["fecha"] = pd.to_datetime(work[col_fecha], errors="coerce", dayfirst=True)
        work["cliente_id"] = work[col_cliente_id].astype(str).str.strip()
        work["cliente_nombre"] = work[col_cliente_nombre].astype(str).str.strip() if col_cliente_nombre else "SIN NOMBRE"
        work["vendedor"] = work[col_vendedor].astype(str).str.strip() if col_vendedor else "SIN VENDEDOR"
        work["producto"] = work[col_producto].astype(str).str.strip()
        work["importe_ars"] = pd.to_numeric(work[col_importe], errors="coerce").fillna(0.0)
        work["cantidad"] = pd.to_numeric(work[col_cantidad], errors="coerce").fillna(0.0) if col_cantidad else 0.0

        work = work.dropna(subset=["fecha"])
        work = work[work["cliente_id"] != ""]
        work = work[work["producto"] != ""]
        work = work[work["importe_ars"] != 0]

        producto_norm = work["producto"].apply(self._normalize)
        work = work[~producto_norm.str.contains("sin cargo", na=False)]

        work["producto_norm"] = producto_norm

        return work

    # =========================================================
    # ALTA GAMA
    # =========================================================
    def _is_alta_gama(self, producto_norm: str) -> bool:
        if self.tenant != "PENAFLOR":
            return False

        premium_keywords = [
            "fond de cave",
            "gran enemigo",
            "trumpeter",
            "rutini",
            "rutini wines",
            "marco real",
            "don david reserve",
            "don david reserva",
            "el enemigo",
            "escorihuela gascon gran reserva",
            "gran reserva",
            "reserva",
            "intocables double oak",
            "mosquita muerta",
            "alta vista",
            "cadus",
            "luigi bosca",
            "chandon",
            "terrazas",
            "saint felicien",
            "las perdices reserva",
            "finca ferrer",
        ]

        return any(k in producto_norm for k in premium_keywords)

    def _filter_alta_gama(self, df: pd.DataFrame) -> pd.DataFrame:
        mask = df["producto_norm"].apply(self._is_alta_gama)
        df_filtrado = df.loc[mask].copy()

        # fallback 1: si no detecta alta gama por keywords, usar cuartil superior por importe
        if df_filtrado.empty:
            print("⚠️ No se detectó alta gama por keywords, usando fallback por importe")

            if "importe_ars" not in df.columns or df.empty:
                return df.copy()

            umbral = df["importe_ars"].quantile(0.75)
            df_fallback = df[df["importe_ars"] >= umbral].copy()

            if df_fallback.empty:
                print("⚠️ Fallback por importe también vacío, usando historial completo")
                return df.copy()

            return df_fallback

        return df_filtrado

    # =========================================================
    # SEMANAS
    # =========================================================
    def _get_week_bounds(self, df: pd.DataFrame):
        max_date = df["fecha"].max().normalize()
        week_start = max_date - pd.to_timedelta(max_date.weekday(), unit="D")
        prev_week_start = week_start - pd.Timedelta(days=7)
        prev_week_end = week_start - pd.Timedelta(days=1)

        return {
            "current_start": week_start,
            "current_end": max_date,
            "prev_start": prev_week_start,
            "prev_end": prev_week_end,
        }

    # =========================================================
    # DESCUENTO MÁXIMO
    # =========================================================
    def _prepare_alertas_desc(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["cliente_id", "descuento_maximo_pct"])

        work = df.copy()
        work.columns = [str(c).strip().lower() for c in work.columns]

        col_cliente_id = self._find_first(work.columns, ["cliente_id", "cliente", "id"])
        col_max = self._find_first(work.columns, ["descuento_maximo_pct", "maximo", "tope", "descuento_max"])

        if not col_cliente_id:
            return pd.DataFrame(columns=["cliente_id", "descuento_maximo_pct"])

        out = pd.DataFrame()
        out["cliente_id"] = work[col_cliente_id].astype(str).str.strip()

        if col_max:
            out["descuento_maximo_pct"] = pd.to_numeric(work[col_max], errors="coerce").fillna(0.0)
        else:
            out["descuento_maximo_pct"] = 0.0

        out = out.groupby("cliente_id", as_index=False)["descuento_maximo_pct"].max()

        return out

    # =========================================================
    # CAÍDA SEMANAL / FALLBACK HISTÓRICO
    # =========================================================
    def build_top_50_caidas(self, hist_df: pd.DataFrame, alertas_df: pd.DataFrame, clientes_df: pd.DataFrame) -> pd.DataFrame:
        hist = self._prepare_historial(hist_df)
        hist = self._filter_alta_gama(hist)

        if hist.empty:
            return pd.DataFrame()

        bounds = self._get_week_bounds(hist)

        cur = hist[
            (hist["fecha"] >= bounds["current_start"]) &
            (hist["fecha"] <= bounds["current_end"])
        ].copy()

        prev = hist[
            (hist["fecha"] >= bounds["prev_start"]) &
            (hist["fecha"] <= bounds["prev_end"])
        ].copy()

        cur_agg = (
            cur.groupby(["cliente_id", "cliente_nombre", "vendedor"], as_index=False)
            .agg(
                venta_premium_semana_actual_ars=("importe_ars", "sum"),
                productos_semana_actual=("producto", lambda s: " | ".join(sorted(set(s.astype(str))))[:1000]),
            )
        )

        prev_agg = (
            prev.groupby(["cliente_id", "cliente_nombre", "vendedor"], as_index=False)
            .agg(
                venta_premium_semana_anterior_ars=("importe_ars", "sum"),
                productos_semana_anterior=("producto", lambda s: " | ".join(sorted(set(s.astype(str))))[:1000]),
            )
        )

        merged = prev_agg.merge(
            cur_agg,
            on=["cliente_id", "cliente_nombre", "vendedor"],
            how="outer",
        ).fillna({
            "venta_premium_semana_anterior_ars": 0.0,
            "venta_premium_semana_actual_ars": 0.0,
            "productos_semana_actual": "",
            "productos_semana_anterior": "",
        })

        merged["caida_ars"] = (
            merged["venta_premium_semana_anterior_ars"] -
            merged["venta_premium_semana_actual_ars"]
        )

        caidas = merged[merged["caida_ars"] > 0].copy()

        # fallback 2: si no hay caídas semanales, usar promedio histórico vs semana actual
        if caidas.empty:
            print("⚠️ No hay caídas semanales, usando fallback por promedio histórico")

            hist_avg = (
                hist.groupby("cliente_id", as_index=False)
                .agg(promedio_historico_ars=("importe_ars", "mean"))
            )

            actual = (
                cur.groupby("cliente_id", as_index=False)
                .agg(venta_premium_semana_actual_ars=("importe_ars", "sum"))
            )

            fallback = hist_avg.merge(actual, on="cliente_id", how="left").fillna({
                "venta_premium_semana_actual_ars": 0.0
            })

            fallback["caida_ars"] = (
                fallback["promedio_historico_ars"] -
                fallback["venta_premium_semana_actual_ars"]
            )

            fallback = fallback[fallback["caida_ars"] > 0].copy()

            info_cliente = hist[["cliente_id", "cliente_nombre", "vendedor"]].drop_duplicates()
            fallback = fallback.merge(info_cliente, on="cliente_id", how="left")

            fallback["venta_premium_semana_anterior_ars"] = fallback["promedio_historico_ars"]
            fallback["productos_semana_anterior"] = "PROMEDIO HISTÓRICO"
            fallback["productos_semana_actual"] = "SEMANA ACTUAL"

            merged = fallback.copy()
        else:
            merged = caidas.copy()

        if merged.empty:
            return pd.DataFrame()

        topes = self._prepare_alertas_desc(alertas_df)
        merged = merged.merge(topes, on="cliente_id", how="left")
        merged["descuento_maximo_pct"] = merged["descuento_maximo_pct"].fillna(0.0)
        merged["descuento_maximo_pct"] = merged["descuento_maximo_pct"].replace(0.0, 8.0)

        merged["descuento_maximo_ars"] = (
            merged["caida_ars"] * (merged["descuento_maximo_pct"] / 100.0)
        ).round(2)

        if not clientes_df.empty:
            cli = clientes_df.copy()
            cli.columns = [str(c).strip().lower() for c in cli.columns]
            col_id = self._find_first(cli.columns, ["cliente_id", "cliente", "id"])
            col_vendedor = self._find_first(cli.columns, ["vendedor", "codven", "preventa"])

            if col_id and col_vendedor:
                aux = cli[[col_id, col_vendedor]].drop_duplicates()
                aux.columns = ["cliente_id", "vendedor_dia"]
                aux["cliente_id"] = aux["cliente_id"].astype(str).str.strip()

                merged["cliente_id"] = merged["cliente_id"].astype(str).str.strip()
                merged = merged.merge(aux, on="cliente_id", how="left")
                merged["vendedor"] = (
                    merged["vendedor"]
                    .replace("", pd.NA)
                    .fillna(merged["vendedor_dia"])
                    .fillna("SIN VENDEDOR")
                )
                merged = merged.drop(columns=["vendedor_dia"])

        merged = merged.sort_values("caida_ars", ascending=False).head(50).reset_index(drop=True)

        merged["semana_actual_desde"] = bounds["current_start"].date().isoformat()
        merged["semana_actual_hasta"] = bounds["current_end"].date().isoformat()
        merged["semana_anterior_desde"] = bounds["prev_start"].date().isoformat()
        merged["semana_anterior_hasta"] = bounds["prev_end"].date().isoformat()

        columnas_base = [
            "cliente_id",
            "cliente_nombre",
            "vendedor",
            "venta_premium_semana_anterior_ars",
            "venta_premium_semana_actual_ars",
            "caida_ars",
            "descuento_maximo_pct",
            "descuento_maximo_ars",
            "productos_semana_anterior",
            "productos_semana_actual",
            "semana_actual_desde",
            "semana_actual_hasta",
            "semana_anterior_desde",
            "semana_anterior_hasta",
        ]

        cols_presentes = [c for c in columnas_base if c in merged.columns]
        return merged[cols_presentes].copy()

    # =========================================================
    # MENSAJES POR VENDEDOR
    # =========================================================
    def build_messages_by_vendor(self, top50_df: pd.DataFrame) -> pd.DataFrame:
        if top50_df.empty:
            return pd.DataFrame(columns=["vendedor", "mensaje", "cantidad_clientes"])

        rows = []

        for vendedor, group in top50_df.groupby("vendedor"):
            group = group.sort_values("caida_ars", ascending=False).copy()

            lines = []
            lines.append(f"VENDEDOR: {vendedor}")
            lines.append("FOCO PROACTIVO PEÑAFLOR - RECUPERACIÓN ALTA GAMA")
            lines.append("")

            total_caida = round(group["caida_ars"].sum(), 2)
            total_descuento = round(group["descuento_maximo_ars"].sum(), 2)

            lines.append(f"CLIENTES CRÍTICOS: {len(group)}")
            lines.append(f"CAÍDA TOTAL DETECTADA: ARS {total_caida:,.2f}")
            lines.append(f"TOPE DE RECUPERACIÓN CON DESCUENTO: ARS {total_descuento:,.2f}")
            lines.append("")

            lines.append("ORDEN DE EJECUCIÓN:")
            for idx, (_, row) in enumerate(group.iterrows(), start=1):
                cliente = row.get("cliente_nombre", "SIN NOMBRE")
                caida = round(self._safe_num(row.get("caida_ars", 0)), 2)
                actual = round(self._safe_num(row.get("venta_premium_semana_actual_ars", 0)), 2)
                anterior = round(self._safe_num(row.get("venta_premium_semana_anterior_ars", 0)), 2)
                desc_pct = round(self._safe_num(row.get("descuento_maximo_pct", 0)), 2)
                desc_ars = round(self._safe_num(row.get("descuento_maximo_ars", 0)), 2)

                productos_ref = row.get("productos_semana_anterior", "")
                if str(productos_ref).strip() == "":
                    productos_ref = "SIN DETALLE"

                lines.append(f"{idx}. {cliente}")
                lines.append(f"   - Caída semanal premium: ARS {caida:,.2f}")
                lines.append(f"   - Semana anterior: ARS {anterior:,.2f} | Semana actual: ARS {actual:,.2f}")
                lines.append(f"   - Línea afectada: {str(productos_ref)[:220]}")
                lines.append(f"   - Descuento máximo permitido: {desc_pct}% | Tope ARS {desc_ars:,.2f}")
                lines.append("   - ACCIÓN: recuperar venta premium sin superar el tope autorizado.")
                lines.append("")

            mensaje = "\n".join(lines)

            rows.append({
                "vendedor": vendedor,
                "mensaje": mensaje,
                "cantidad_clientes": len(group),
                "caida_total_ars": total_caida,
                "tope_total_descuento_ars": total_descuento,
                "archivo_sugerido": f"{self._clean_filename(vendedor)}.txt",
            })

        return pd.DataFrame(rows)

    # =========================================================
    # SAVE
    # =========================================================
    def save_outputs(self, top50_df: pd.DataFrame, mensajes_df: pd.DataFrame) -> Dict[str, str]:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        top50_path = self.output_dir / "top_50_caida_vinos_alta_gama.csv"
        mensajes_path = self.output_dir / "mensajes_vendedores_resumen.csv"
        txt_dir = self.output_dir / "mensajes"
        txt_dir.mkdir(parents=True, exist_ok=True)

        top50_df.to_csv(top50_path, index=False, encoding="utf-8-sig")
        mensajes_df.to_csv(mensajes_path, index=False, encoding="utf-8-sig")

        count = 0
        for _, row in mensajes_df.iterrows():
            file_name = row["archivo_sugerido"]
            txt_file = txt_dir / file_name
            txt_file.write_text(str(row["mensaje"]), encoding="utf-8")
            count += 1

        return {
            "top50_csv": str(top50_path),
            "mensajes_csv": str(mensajes_path),
            "mensajes_dir": str(txt_dir),
            "mensajes_generados": str(count),
        }

    # =========================================================
    # RUN
    # =========================================================
    def run(self) -> Dict[str, object]:
        print("=== COPILOTO VENDEDOR PROACTIVO - PEÑAFLOR ===")

        sources = self.load_sources()

        top50 = self.build_top_50_caidas(
            hist_df=sources["historial"],
            alertas_df=sources["alertas_desc"],
            clientes_df=sources["clientes_dia"],
        )

        mensajes = self.build_messages_by_vendor(top50)
        saved = self.save_outputs(top50, mensajes)

        print(f"Top 50 generados: {len(top50)}")
        print(f"Mensajes por vendedor: {len(mensajes)}")

        return {
            "status": "ok",
            "tenant": self.tenant,
            "top50_rows": len(top50),
            "vendor_messages": len(mensajes),
            "files": saved,
        }


if __name__ == "__main__":
    result = OrbitSellerProactiveCopilot().run()
    print(result)