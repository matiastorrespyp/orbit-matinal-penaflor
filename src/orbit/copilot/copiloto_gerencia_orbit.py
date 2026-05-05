from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import unicodedata
import re
import json

import pandas as pd


BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
DATASETS_DIR = BASE_DIR / "04_DATASETS_ORBIT"
INTELLIGENCE_DIR = BASE_DIR / "05_INTELLIGENCE_ORBIT"
PROACTIVE_DIR = BASE_DIR / "06_COPILOTO_VENDEDOR_PROACTIVO"
OUTPUT_DIR = BASE_DIR / "06_COPILOTO_GERENCIA"


class OrbitGerenciaCopilot:
    """
    Copiloto Gerencia Orbit - Peñaflor

    Objetivo:
    - resumir el estado operativo/comercial del día
    - priorizar vendedores a intervenir
    - identificar clientes críticos
    - cuantificar riesgo comercial
    - dejar un mensaje ejecutivo listo para lectura rápida
    """

    def __init__(self, tenant: str = "PENAFLOR") -> None:
        self.tenant = tenant.upper().strip()
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fecha_generacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
                value = value.strip().replace("$", "").replace("%", "")
                if "," in value and "." in value:
                    value = value.replace(".", "").replace(",", ".")
                elif "," in value:
                    value = value.replace(",", ".")
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
    def _read_csv_any(path: Path) -> pd.DataFrame:
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
                if len(df.columns) > 0:
                    return df
            except Exception:
                pass

        return pd.DataFrame()

    @staticmethod
    def _clean_filename(name: str) -> str:
        text = str(name).strip().lower()
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "sin_nombre"

    def _pick_existing(self, folder: Path, names: List[str]) -> pd.DataFrame:
        for name in names:
            p = folder / name
            if p.exists():
                df = self._read_csv_any(p)
                if not df.empty:
                    return df
        return pd.DataFrame()

    def load_sources(self) -> Dict[str, pd.DataFrame]:
        return {
            "foco": self._read_csv_any(INTELLIGENCE_DIR / "orbit_foco_vendedor.csv"),
            "alertas": self._read_csv_any(INTELLIGENCE_DIR / "orbit_alertas_priorizadas.csv"),
            "volumen": self._read_csv_any(DATASETS_DIR / "mod_volumen_vendedor.csv"),
            "clientes_dia": self._read_csv_any(DATASETS_DIR / "clientes_dia.csv"),
            "kernel_top": self._pick_existing(
                PROACTIVE_DIR,
                ["top_50_caida_vinos_alta_gama.csv"]
            ),
            "kernel_resumen": self._pick_existing(
                PROACTIVE_DIR,
                ["mensajes_vendedores_resumen.csv"]
            ),
        }

    def build_context(self, data: Dict[str, pd.DataFrame]) -> Dict[str, object]:
        foco = data["foco"].copy()
        alertas = data["alertas"].copy()
        volumen = data["volumen"].copy()
        clientes_dia = data["clientes_dia"].copy()
        kernel_top = data["kernel_top"].copy()

        ctx: Dict[str, object] = {
            "tenant": self.tenant,
            "fecha_generacion": self.fecha_generacion,
            "clientes_dia_total": 0,
            "vendedores_total": 0,
            "venta_total": 0.0,
            "alertas_total": 0,
            "alertas_criticas": 0,
            "riesgo_total_caida": 0.0,
            "tope_descuento_total": 0.0,
            "vendedores_a_intervenir": [],
            "clientes_criticos": [],
            "decision_gerencial": [],
        }

        if not clientes_dia.empty:
            ctx["clientes_dia_total"] = int(len(clientes_dia))

        if not volumen.empty:
            col_v = self._find_first(volumen.columns, ["vendedor_nombre", "vendedor"])
            col_venta = self._find_first(volumen.columns, ["venta_ayer", "venta", "importe", "neto"])
            if col_v:
                vend_count = volumen[col_v].astype(str).str.strip().replace("", pd.NA).dropna().nunique()
                ctx["vendedores_total"] = int(vend_count)
            if col_venta:
                ctx["venta_total"] = float(pd.to_numeric(volumen[col_venta], errors="coerce").fillna(0).sum())

        if not alertas.empty:
            ctx["alertas_total"] = int(len(alertas))
            col_pri = self._find_first(alertas.columns, ["prioridad"])
            if col_pri:
                ctx["alertas_criticas"] = int(
                    alertas[col_pri].astype(str).str.lower().isin(["alta", "critico", "crítica", "critica"]).sum()
                )

        if not kernel_top.empty:
            col_cli = self._find_first(kernel_top.columns, ["cliente_nombre", "cliente"])
            col_v = self._find_first(kernel_top.columns, ["vendedor"])
            col_caida = self._find_first(kernel_top.columns, ["caida_ars", "caida", "riesgo"])
            col_tope = self._find_first(kernel_top.columns, ["descuento_maximo_ars", "tope", "descuento_ars"])
            col_prev = self._find_first(kernel_top.columns, ["venta_premium_semana_anterior_ars"])
            col_act = self._find_first(kernel_top.columns, ["venta_premium_semana_actual_ars"])

            if col_caida:
                ctx["riesgo_total_caida"] = float(pd.to_numeric(kernel_top[col_caida], errors="coerce").fillna(0).sum())
            if col_tope:
                ctx["tope_descuento_total"] = float(pd.to_numeric(kernel_top[col_tope], errors="coerce").fillna(0).sum())

            clientes_criticos = []
            for _, row in kernel_top.head(10).iterrows():
                clientes_criticos.append({
                    "cliente": self._safe_text(row[col_cli]) if col_cli else "",
                    "vendedor": self._safe_text(row[col_v]) if col_v else "",
                    "caida_ars": self._safe_num(row[col_caida]) if col_caida else 0.0,
                    "tope_ars": self._safe_num(row[col_tope]) if col_tope else 0.0,
                    "venta_anterior": self._safe_num(row[col_prev]) if col_prev else 0.0,
                    "venta_actual": self._safe_num(row[col_act]) if col_act else 0.0,
                })
            ctx["clientes_criticos"] = clientes_criticos

        vendedores_a_intervenir = self._build_vendedores_a_intervenir(foco, kernel_top)
        ctx["vendedores_a_intervenir"] = vendedores_a_intervenir
        ctx["decision_gerencial"] = self._build_decision_gerencial(ctx)

        return ctx

    def _build_vendedores_a_intervenir(
        self,
        foco: pd.DataFrame,
        kernel_top: pd.DataFrame,
    ) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        vendedores: Dict[str, Dict[str, object]] = {}

        if not foco.empty:
            col_v = self._find_first(foco.columns, ["vendedor"])
            col_total = self._find_first(foco.columns, ["total_alertas"])
            col_crit = self._find_first(foco.columns, ["alertas_alta", "criticas"])
            col_foco = self._find_first(foco.columns, ["foco_principal"])
            col_accion = self._find_first(foco.columns, ["accion_sugerida"])

            for _, row in foco.iterrows():
                nombre = self._safe_text(row[col_v]) if col_v else ""
                if not nombre:
                    continue
                vendedores[nombre] = {
                    "vendedor": nombre,
                    "alertas_total": int(self._safe_num(row[col_total])) if col_total else 0,
                    "alertas_criticas": int(self._safe_num(row[col_crit])) if col_crit else 0,
                    "foco": self._safe_text(row[col_foco]) if col_foco else "",
                    "accion": self._safe_text(row[col_accion]) if col_accion else "",
                    "clientes_proactivos": 0,
                    "caida_total": 0.0,
                    "tope_total": 0.0,
                    "score_intervencion": 0.0,
                }

        if not kernel_top.empty:
            col_v = self._find_first(kernel_top.columns, ["vendedor"])
            col_caida = self._find_first(kernel_top.columns, ["caida_ars", "caida", "riesgo"])
            col_tope = self._find_first(kernel_top.columns, ["descuento_maximo_ars", "tope", "descuento_ars"])

            if col_v:
                grouped = kernel_top.groupby(kernel_top[col_v].astype(str).str.strip())
                for vendedor, sub in grouped:
                    if vendedor == "":
                        continue
                    if vendedor not in vendedores:
                        vendedores[vendedor] = {
                            "vendedor": vendedor,
                            "alertas_total": 0,
                            "alertas_criticas": 0,
                            "foco": "",
                            "accion": "",
                            "clientes_proactivos": 0,
                            "caida_total": 0.0,
                            "tope_total": 0.0,
                            "score_intervencion": 0.0,
                        }

                    vendedores[vendedor]["clientes_proactivos"] = int(len(sub))
                    if col_caida:
                        vendedores[vendedor]["caida_total"] = float(pd.to_numeric(sub[col_caida], errors="coerce").fillna(0).sum())
                    if col_tope:
                        vendedores[vendedor]["tope_total"] = float(pd.to_numeric(sub[col_tope], errors="coerce").fillna(0).sum())

        for vendedor, item in vendedores.items():
            item["score_intervencion"] = (
                item["alertas_criticas"] * 5 +
                item["alertas_total"] * 2 +
                item["clientes_proactivos"] * 3 +
                (item["caida_total"] / 1000.0)
            )
            rows.append(item)

        rows.sort(key=lambda x: x["score_intervencion"], reverse=True)
        return rows[:7]

    def _build_decision_gerencial(self, ctx: Dict[str, object]) -> List[str]:
        decisiones: List[str] = []

        if ctx["alertas_criticas"] >= 5:
            decisiones.append("Prioridad inmediata en control de margen: hay volumen relevante de alertas críticas.")
        elif ctx["alertas_total"] > 0:
            decisiones.append("La jornada requiere seguimiento comercial fino, pero sin crisis de margen general.")
        else:
            decisiones.append("No se detecta presión fuerte por alertas. El foco puede ir a crecimiento y ejecución.")

        if ctx["riesgo_total_caida"] >= 20000:
            decisiones.append("Hay riesgo comercial alto en cartera premium. Conviene intervención directa sobre vendedores top.")
        elif ctx["riesgo_total_caida"] > 0:
            decisiones.append("Hay señales de caída comercial detectables. Conviene gestión selectiva, no masiva.")
        else:
            decisiones.append("No se detecta caída relevante en cartera premium para esta corrida.")

        vendedores = ctx["vendedores_a_intervenir"]
        if vendedores:
            top = vendedores[0]
            decisiones.append(
                f"El primer vendedor a intervenir hoy es {top['vendedor']}: "
                f"{top['alertas_criticas']} alertas críticas, "
                f"{top['clientes_proactivos']} clientes proactivos y "
                f"ARS {top['caida_total']:,.2f} de caída potencial."
            )

        clientes = ctx["clientes_criticos"]
        if clientes:
            top_cli = clientes[0]
            decisiones.append(
                f"Cliente crítico principal del día: {top_cli['cliente']} "
                f"({top_cli['vendedor']}) con caída estimada de ARS {top_cli['caida_ars']:,.2f}."
            )

        return decisiones

    def build_message(self, ctx: Dict[str, object]) -> str:
        lines: List[str] = []
        lines.append(f"COPILOTO GERENCIA ORBIT - {ctx['tenant']}")
        lines.append(f"Generado: {ctx['fecha_generacion']}")
        lines.append("")

        lines.append("RESUMEN EJECUTIVO:")
        lines.append(f"- Clientes del día: {ctx['clientes_dia_total']}")
        lines.append(f"- Vendedores con actividad: {ctx['vendedores_total']}")
        lines.append(f"- Venta total detectada: ARS {ctx['venta_total']:,.2f}")
        lines.append(f"- Alertas totales: {ctx['alertas_total']}")
        lines.append(f"- Alertas críticas: {ctx['alertas_criticas']}")
        lines.append(f"- Riesgo comercial detectado: ARS {ctx['riesgo_total_caida']:,.2f}")
        lines.append(f"- Tope total teórico de descuento: ARS {ctx['tope_descuento_total']:,.2f}")
        lines.append("")

        lines.append("DECISIÓN GERENCIAL SUGERIDA:")
        for i, dec in enumerate(ctx["decision_gerencial"], start=1):
            lines.append(f"{i}. {dec}")
        lines.append("")

        lines.append("VENDEDORES A INTERVENIR:")
        if not ctx["vendedores_a_intervenir"]:
            lines.append("- Sin vendedores priorizados en esta corrida.")
        else:
            for i, v in enumerate(ctx["vendedores_a_intervenir"], start=1):
                lines.append(
                    f"{i}. {v['vendedor']} | "
                    f"Alertas: {v['alertas_total']} | "
                    f"Críticas: {v['alertas_criticas']} | "
                    f"Clientes proactivos: {v['clientes_proactivos']} | "
                    f"Caída: ARS {v['caida_total']:,.2f}"
                )
                if v["foco"]:
                    lines.append(f"   Foco: {v['foco']}")
                if v["accion"]:
                    lines.append(f"   Acción base: {v['accion']}")
        lines.append("")

        lines.append("CLIENTES CRÍTICOS DEL DÍA:")
        if not ctx["clientes_criticos"]:
            lines.append("- No se detectaron clientes críticos para esta corrida.")
        else:
            for i, c in enumerate(ctx["clientes_criticos"][:10], start=1):
                lines.append(
                    f"{i}. {c['cliente']} | {c['vendedor']} | "
                    f"Caída: ARS {c['caida_ars']:,.2f} | "
                    f"Tope: ARS {c['tope_ars']:,.2f} | "
                    f"Antes: ARS {c['venta_anterior']:,.2f} | "
                    f"Ahora: ARS {c['venta_actual']:,.2f}"
                )
        lines.append("")

        lines.append("CIERRE:")
        if ctx["riesgo_total_caida"] > 0 or ctx["alertas_total"] > 0:
            lines.append("- La gerencia debería abrir el día con foco en vendedores priorizados y clientes críticos.")
        else:
            lines.append("- La gerencia puede operar con foco de crecimiento y seguimiento normal.")

        return "\n".join(lines)

    def save_outputs(self, message: str, ctx: Dict[str, object]) -> Dict[str, str]:
        txt_path = self.output_dir / "copiloto_gerencia_resumen.txt"
        json_path = self.output_dir / "copiloto_gerencia_resumen.json"

        txt_path.write_text(message, encoding="utf-8")

        payload = {
            "tenant": ctx["tenant"],
            "fecha_generacion": ctx["fecha_generacion"],
            "clientes_dia_total": ctx["clientes_dia_total"],
            "vendedores_total": ctx["vendedores_total"],
            "venta_total": ctx["venta_total"],
            "alertas_total": ctx["alertas_total"],
            "alertas_criticas": ctx["alertas_criticas"],
            "riesgo_total_caida": ctx["riesgo_total_caida"],
            "tope_descuento_total": ctx["tope_descuento_total"],
            "decision_gerencial": ctx["decision_gerencial"],
            "vendedores_a_intervenir": ctx["vendedores_a_intervenir"],
            "clientes_criticos": ctx["clientes_criticos"],
        }

        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "txt": str(txt_path),
            "json": str(json_path),
        }

    def run(self) -> Dict[str, object]:
        print("=== COPILOTO GERENCIA ORBIT ===")

        data = self.load_sources()
        ctx = self.build_context(data)
        message = self.build_message(ctx)
        files = self.save_outputs(message, ctx)

        print(f"Vendedores priorizados: {len(ctx['vendedores_a_intervenir'])}")
        print(f"Clientes críticos: {len(ctx['clientes_criticos'])}")
        print(f"TXT: {files['txt']}")
        print(f"JSON: {files['json']}")

        return {
            "status": "ok",
            "tenant": self.tenant,
            "vendedores_priorizados": len(ctx["vendedores_a_intervenir"]),
            "clientes_criticos": len(ctx["clientes_criticos"]),
            "files": files,
        }


if __name__ == "__main__":
    result = OrbitGerenciaCopilot().run()
    print(result)
