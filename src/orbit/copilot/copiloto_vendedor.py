from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


class OrbitClientCopilot:
    """
    Copiloto cliente Orbit v2 con histórico.

    Usa:
    - clientes_dia.csv
    - mod_11_titulares.csv
    - orbit_alertas_priorizadas.csv
    - hist_cliente_resumen.csv
    - hist_cliente_producto.csv
    - hist_cliente_mes.csv
    """

    def __init__(
        self,
        base_dir: str | Path = r"C:\Orbit\MATINAL_PENAFLOR",
        datasets_dir: str | Path | None = None,
        intelligence_dir: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.datasets_dir = Path(datasets_dir) if datasets_dir else self.base_dir / "04_DATASETS_ORBIT"
        self.intelligence_dir = Path(intelligence_dir) if intelligence_dir else self.base_dir / "05_INTELLIGENCE_ORBIT"
        self.output_dir = Path(output_dir) if output_dir else self.base_dir / "07_COPILOTO_CLIENTE"

    # =========================================================
    # HELPERS
    # =========================================================
    def _ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _read_csv(self, folder: Path, filename: str) -> pd.DataFrame:
        path = folder / filename
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

    @staticmethod
    def _normalize_spaces(text: str) -> str:
        return " ".join(str(text).strip().split())

    @staticmethod
    def _clean_filename(name: str) -> str:
        text = str(name).strip().lower()
        replacements = {
            "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        text = " ".join(text.split())

        out = []
        for ch in text:
            if ch.isalnum():
                out.append(ch)
            elif ch in {" ", "-", "_"}:
                out.append("_")

        clean = "".join(out)
        while "__" in clean:
            clean = clean.replace("__", "_")
        return clean.strip("_")

    @staticmethod
    def _find_first(columns, candidates) -> Optional[str]:
        cols_lower = {str(c).lower(): c for c in columns}
        for cand in candidates:
            for key, real in cols_lower.items():
                if cand in key:
                    return real
        return None

    @staticmethod
    def _contains_text(series: pd.Series, text: str) -> pd.Series:
        return series.astype(str).str.upper().str.contains(str(text).upper(), na=False)

    @staticmethod
    def _extract_metric(text: str, label: str) -> float:
        if not text or label not in text:
            return 0.0
        try:
            fragment = text.split(label, 1)[1]
            fragment = fragment.split("|", 1)[0].strip()
            fragment = fragment.replace("%", "").replace("$", "").strip()

            if "," in fragment and "." in fragment:
                fragment = fragment.replace(".", "").replace(",", ".")
            elif "," in fragment:
                fragment = fragment.replace(",", ".")
            return float(fragment)
        except Exception:
            return 0.0

    # =========================================================
    # CARGA
    # =========================================================
    def load_sources(self) -> Dict[str, pd.DataFrame]:
        return {
            "clientes_dia": self._read_csv(self.datasets_dir, "clientes_dia.csv"),
            "mod_11_titulares": self._read_csv(self.datasets_dir, "mod_11_titulares.csv"),
            "alertas": self._read_csv(self.intelligence_dir, "orbit_alertas_priorizadas.csv"),
            "hist_cliente_resumen": self._read_csv(self.datasets_dir, "hist_cliente_resumen.csv"),
            "hist_cliente_producto": self._read_csv(self.datasets_dir, "hist_cliente_producto.csv"),
            "hist_cliente_mes": self._read_csv(self.datasets_dir, "hist_cliente_mes.csv"),
        }

    # =========================================================
    # BÚSQUEDA CLIENTE
    # =========================================================
    def find_client(self, clientes_df: pd.DataFrame, query: str) -> pd.DataFrame:
        if clientes_df.empty:
            return pd.DataFrame()

        q = self._normalize_spaces(query)

        col_cliente_id = self._find_first(clientes_df.columns, ["cliente_id", "codigo", "cliente"])
        col_nombre = self._find_first(clientes_df.columns, ["cliente_nombre", "razon_social", "cliente"])
        col_vendedor = self._find_first(clientes_df.columns, ["vendedor", "vendedor_nombre", "nombre_vendedor"])
        col_segmento = self._find_first(clientes_df.columns, ["segmento", "segmento_operativo"])
        col_localidad = self._find_first(clientes_df.columns, ["localidad"])
        col_ruta = self._find_first(clientes_df.columns, ["ruta"])
        col_direccion = self._find_first(clientes_df.columns, ["direccion"])

        mask = pd.Series([False] * len(clientes_df), index=clientes_df.index)

        if col_cliente_id:
            try:
                q_num = str(int(float(q)))
                mask = mask | (clientes_df[col_cliente_id].astype(str).str.strip() == q_num)
            except Exception:
                pass

        if col_nombre:
            mask = mask | self._contains_text(clientes_df[col_nombre], q)

        result = clientes_df.loc[mask].copy()
        if result.empty:
            return pd.DataFrame()

        output = pd.DataFrame()
        output["cliente_id"] = result[col_cliente_id] if col_cliente_id else ""
        output["cliente_nombre"] = result[col_nombre] if col_nombre else ""
        output["vendedor"] = result[col_vendedor] if col_vendedor else ""
        output["segmento"] = result[col_segmento] if col_segmento else ""
        output["localidad"] = result[col_localidad] if col_localidad else ""
        output["ruta"] = result[col_ruta] if col_ruta else ""
        output["direccion"] = result[col_direccion] if col_direccion else ""

        return output.reset_index(drop=True)

    # =========================================================
    # ALERTAS / 11T
    # =========================================================
    def get_client_alerts(self, alertas_df: pd.DataFrame, cliente_nombre: str) -> pd.DataFrame:
        if alertas_df.empty or "cliente" not in alertas_df.columns:
            return pd.DataFrame()

        mask = alertas_df["cliente"].astype(str).map(self._normalize_spaces).str.upper() == self._normalize_spaces(cliente_nombre).upper()
        result = alertas_df.loc[mask].copy()

        if result.empty:
            return pd.DataFrame()

        prioridad_order = {"alta": 1, "media": 2, "baja": 3}
        if "prioridad" in result.columns:
            result["prioridad_sort"] = result["prioridad"].astype(str).str.lower().map(prioridad_order).fillna(9)
            result = result.sort_values(["prioridad_sort"]).drop(columns=["prioridad_sort"])

        return result.reset_index(drop=True)

    def get_client_11t(self, df_11t: pd.DataFrame, cliente_nombre: str) -> pd.DataFrame:
        if df_11t.empty:
            return pd.DataFrame()

        col_cliente = self._find_first(df_11t.columns, ["cliente_nombre", "cliente", "razon_social"])
        if not col_cliente:
            return pd.DataFrame()

        mask = df_11t[col_cliente].astype(str).map(self._normalize_spaces).str.upper() == self._normalize_spaces(cliente_nombre).upper()
        result = df_11t.loc[mask].copy()

        if result.empty:
            return pd.DataFrame()

        col_prioridad = self._find_first(result.columns, ["prioridad", "prioridad_11t"])
        if col_prioridad:
            prioridad_order = {"ALTA": 1, "MEDIA": 2, "BAJA": 3}
            result["prioridad_sort"] = result[col_prioridad].astype(str).str.upper().map(prioridad_order).fillna(9)
            result = result.sort_values(["prioridad_sort"]).drop(columns=["prioridad_sort"])

        return result.reset_index(drop=True)

    # =========================================================
    # HISTÓRICO
    # =========================================================
    def get_hist_resumen(self, hist_resumen_df: pd.DataFrame, cliente_nombre: str) -> pd.DataFrame:
        if hist_resumen_df.empty or "cliente" not in hist_resumen_df.columns:
            return pd.DataFrame()

        mask = hist_resumen_df["cliente"].astype(str).map(self._normalize_spaces).str.upper() == self._normalize_spaces(cliente_nombre).upper()
        return hist_resumen_df.loc[mask].copy().reset_index(drop=True)

    def get_hist_productos(self, hist_producto_df: pd.DataFrame, cliente_nombre: str) -> pd.DataFrame:
        if hist_producto_df.empty or "cliente" not in hist_producto_df.columns:
            return pd.DataFrame()

        mask = hist_producto_df["cliente"].astype(str).map(self._normalize_spaces).str.upper() == self._normalize_spaces(cliente_nombre).upper()
        result = hist_producto_df.loc[mask].copy()

        if result.empty:
            return pd.DataFrame()

        if "cantidad" in result.columns:
            result["cantidad"] = pd.to_numeric(result["cantidad"], errors="coerce").fillna(0)
            result = result.sort_values("cantidad", ascending=False)

        return result.reset_index(drop=True)

    def get_hist_mensual(self, hist_mes_df: pd.DataFrame, cliente_nombre: str) -> pd.DataFrame:
        if hist_mes_df.empty or "cliente" not in hist_mes_df.columns:
            return pd.DataFrame()

        mask = hist_mes_df["cliente"].astype(str).map(self._normalize_spaces).str.upper() == self._normalize_spaces(cliente_nombre).upper()
        result = hist_mes_df.loc[mask].copy()

        if result.empty:
            return pd.DataFrame()

        if "mes" in result.columns:
            result = result.sort_values("mes", ascending=False)

        return result.reset_index(drop=True)

    # =========================================================
    # MENSAJE
    # =========================================================
    def build_client_message(
        self,
        client_row: pd.Series,
        alertas_cliente: pd.DataFrame,
        oportunidades_11t: pd.DataFrame,
        hist_resumen: pd.DataFrame,
        hist_productos: pd.DataFrame,
        hist_mensual: pd.DataFrame,
    ) -> str:
        cliente_id = self._safe_text(client_row.get("cliente_id", ""))
        cliente_nombre = self._safe_text(client_row.get("cliente_nombre", ""))
        vendedor = self._safe_text(client_row.get("vendedor", ""))
        segmento = self._safe_text(client_row.get("segmento", ""))
        localidad = self._safe_text(client_row.get("localidad", ""))
        ruta = self._safe_text(client_row.get("ruta", ""))
        direccion = self._safe_text(client_row.get("direccion", ""))

        lines: List[str] = []

        lines.append(f"CLIENTE: {cliente_nombre}")
        if cliente_id:
            lines.append(f"CÓDIGO: {cliente_id}")
        if vendedor:
            lines.append(f"VENDEDOR: {vendedor}")
        if segmento:
            lines.append(f"SEGMENTO: {segmento}")
        if localidad:
            lines.append(f"LOCALIDAD: {localidad}")
        if ruta:
            lines.append(f"RUTA: {ruta}")
        if direccion:
            lines.append(f"DIRECCIÓN: {direccion}")

        lines.append("")

        # HISTÓRICO RESUMEN
        lines.append("HISTÓRICO DEL CLIENTE:")
        if hist_resumen.empty:
            lines.append("- No hay resumen histórico disponible para este cliente.")
        else:
            row = hist_resumen.iloc[0]
            volumen_total = self._safe_num(row.get("volumen_total", 0))
            ultima_compra = self._safe_text(row.get("ultima_compra", ""))
            lines.append(f"- Volumen histórico total: {round(volumen_total, 2)}")
            if ultima_compra:
                lines.append(f"- Última compra histórica registrada: {ultima_compra}")

        if hist_productos.empty:
            lines.append("- Productos históricos destacados: sin datos.")
        else:
            lines.append("- Top productos históricos:")
            top_prod = hist_productos.head(5)
            for i, (_, row) in enumerate(top_prod.iterrows(), start=1):
                prod = self._safe_text(row.get("producto", ""))
                cant = self._safe_num(row.get("cantidad", 0))
                lines.append(f"  {i}. {prod} | Cantidad acumulada: {round(cant, 2)}")

        if hist_mensual.empty:
            lines.append("- Evolución mensual: sin datos.")
        else:
            lines.append("- Últimos meses detectados:")
            top_mes = hist_mensual.head(4)
            for _, row in top_mes.iterrows():
                mes = self._safe_text(row.get("mes", ""))
                cant = self._safe_num(row.get("cantidad", 0))
                lines.append(f"  {mes}: {round(cant, 2)}")

        lines.append("")

        # ALERTAS
        lines.append("ALERTAS DEL CLIENTE:")
        impacto_total = 0.0
        if alertas_cliente.empty:
            lines.append("- Sin alertas activas detectadas.")
        else:
            for i, (_, row) in enumerate(alertas_cliente.iterrows(), start=1):
                prioridad = self._safe_text(row.get("prioridad", "")).upper() or "SIN PRIORIDAD"
                tipo_alerta = self._safe_text(row.get("tipo_alerta", "")).replace("_", " ").upper()
                producto = self._safe_text(row.get("producto", ""))
                detalle = self._safe_text(row.get("detalle", ""))
                accion = self._safe_text(row.get("accion_sugerida", ""))

                impacto = self._extract_metric(detalle, "Impacto real:")
                impacto_total += impacto

                lines.append(f"{i}. [{prioridad}] {tipo_alerta}")
                if producto:
                    lines.append(f"   Producto: {producto}")
                if detalle:
                    lines.append(f"   Qué pasa: {detalle}")
                if accion:
                    lines.append(f"   Acción base: {accion}")

            lines.append(f"- Impacto acumulado detectado: ${round(impacto_total, 0)}")

        lines.append("")

        # OPORTUNIDADES 11T
        lines.append("OPORTUNIDADES 11 TITULARES:")
        if oportunidades_11t.empty:
            lines.append("- No aparecen oportunidades específicas para este cliente en esta corrida.")
        else:
            col_producto = self._find_first(oportunidades_11t.columns, ["marca", "producto", "articulo"])
            col_prioridad = self._find_first(oportunidades_11t.columns, ["prioridad", "prioridad_11t"])
            col_segmento = self._find_first(oportunidades_11t.columns, ["segmento_11t", "segmento"])

            for i, (_, row) in enumerate(oportunidades_11t.head(10).iterrows(), start=1):
                producto = self._safe_text(row[col_producto]) if col_producto else ""
                prioridad = self._safe_text(row[col_prioridad]) if col_prioridad else ""
                segmento_11t = self._safe_text(row[col_segmento]) if col_segmento else ""

                texto = f"{i}. {producto}" if producto else f"{i}. Oportunidad detectada"
                if prioridad:
                    texto += f" | Prioridad: {prioridad}"
                if segmento_11t:
                    texto += f" | Segmento 11T: {segmento_11t}"

                lines.append(texto)

        lines.append("")

        # ACCIÓN FINAL
        accion_final = self._build_final_action(alertas_cliente, oportunidades_11t, hist_productos)
        lines.append("ACCIÓN RECOMENDADA EN EL PDV:")
        lines.append(accion_final)

        lines.append("")
        lines.append("CIERRE DE VISITA:")
        lines.append("- Antes de retirarte, registrar novedad comercial relevante.")
        lines.append("- Si hubo corrección de descuento, dejarlo asentado.")
        lines.append("- Si viste oportunidad no capturada por el sistema, anotarla para próxima matinal.")

        return "\n".join(lines)

    def _build_final_action(
        self,
        alertas_cliente: pd.DataFrame,
        oportunidades_11t: pd.DataFrame,
        hist_productos: pd.DataFrame,
    ) -> str:
        impacto_total = 0.0
        exceso_max = 0.0

        if not alertas_cliente.empty and "detalle" in alertas_cliente.columns:
            for detalle in alertas_cliente["detalle"].astype(str):
                impacto_total += self._extract_metric(detalle, "Impacto real:")
                exceso = self._extract_metric(detalle, "Excedente:")
                if exceso > exceso_max:
                    exceso_max = exceso

        oportunidades_altas = 0
        if not oportunidades_11t.empty:
            col_prioridad = self._find_first(oportunidades_11t.columns, ["prioridad", "prioridad_11t"])
            if col_prioridad:
                oportunidades_altas = len(
                    oportunidades_11t.loc[
                        oportunidades_11t[col_prioridad].astype(str).str.upper() == "ALTA"
                    ]
                )
            else:
                oportunidades_altas = len(oportunidades_11t)

        top_hist = ""
        if not hist_productos.empty:
            row = hist_productos.iloc[0]
            top_hist = self._safe_text(row.get("producto", ""))

        if impacto_total >= 1000:
            return "Entrar con foco en corrección de margen. NO repetir descuentos altos. Buscar cierre a precio objetivo y validar volumen mínimo antes de conceder descuento."

        if exceso_max >= 5:
            return "Reducir descuento en esta visita. No sostener el nivel actual. Defender margen y condicionar cualquier concesión a volumen real."

        if oportunidades_altas >= 3 and top_hist:
            return f"Priorizar recuperación y crecimiento. Entrar con foco en oportunidades 11 titulares y usar {top_hist} como referencia histórica de compra."

        if oportunidades_altas >= 1 and impacto_total > 0:
            return "Combinar corrección de descuento con venta de oportunidad. No ir solo a resolver problema: buscar también crecimiento."

        if oportunidades_altas >= 1:
            return "Entrar con foco comercial. Cerrar al menos una oportunidad 11 titulares en esta visita."

        if top_hist:
            return f"Visita con foco en recuperación. Revisar si corresponde reactivar compra sobre {top_hist} u otro producto histórico del cliente."

        if impacto_total > 0:
            return "Visita orientada a control. Corregir precio/descuento antes de volver a ampliar venta."

        return "Visita normal. Mantener ejecución comercial y capturar oportunidades que el sistema todavía no haya detectado."

    # =========================================================
    # SAVE
    # =========================================================
    def save_message(self, client_query: str, message: str) -> Path:
        self._ensure_output_dir()

        file_name = f"{self._clean_filename(client_query)}.txt"
        path = self.output_dir / file_name
        path.write_text(message, encoding="utf-8")
        return path

    # =========================================================
    # RUN
    # =========================================================
    def run_for_client(self, query: str) -> Dict[str, object]:
        data = self.load_sources()

        clientes = data["clientes_dia"]
        df_11t = data["mod_11_titulares"]
        alertas = data["alertas"]
        hist_resumen = data["hist_cliente_resumen"]
        hist_productos = data["hist_cliente_producto"]
        hist_mensual = data["hist_cliente_mes"]

        found = self.find_client(clientes, query)

        if found.empty:
            return {
                "status": "not_found",
                "query": query,
                "message": f"No se encontró cliente para la búsqueda: {query}",
            }

        if len(found) > 1:
            return {
                "status": "multiple",
                "query": query,
                "matches": found.to_dict(orient="records"),
                "message": f"La búsqueda '{query}' devolvió múltiples clientes. Refinar consulta.",
            }

        client_row = found.iloc[0]
        cliente_nombre = self._safe_text(client_row.get("cliente_nombre", ""))

        alertas_cliente = self.get_client_alerts(alertas, cliente_nombre)
        oportunidades_11t = self.get_client_11t(df_11t, cliente_nombre)
        hist_res_cliente = self.get_hist_resumen(hist_resumen, cliente_nombre)
        hist_prod_cliente = self.get_hist_productos(hist_productos, cliente_nombre)
        hist_mes_cliente = self.get_hist_mensual(hist_mensual, cliente_nombre)

        message = self.build_client_message(
            client_row,
            alertas_cliente,
            oportunidades_11t,
            hist_res_cliente,
            hist_prod_cliente,
            hist_mes_cliente,
        )

        path = self.save_message(cliente_nombre or query, message)

        return {
            "status": "ok",
            "query": query,
            "cliente": cliente_nombre,
            "output_file": str(path),
            "alertas": len(alertas_cliente),
            "oportunidades_11t": len(oportunidades_11t),
            "hist_productos": len(hist_prod_cliente),
            "message": message,
        }


if __name__ == "__main__":
    copilot = OrbitClientCopilot()
    query = "LOPEZ"
    result = copilot.run_for_client(query)
    print(result)