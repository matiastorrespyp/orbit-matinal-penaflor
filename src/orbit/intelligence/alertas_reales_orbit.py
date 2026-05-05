from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json
import unicodedata
import pandas as pd
import sys

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
INPUTS_DIR = BASE_DIR / "01_INPUTS"
DATASETS_DIR = BASE_DIR / "04_DATASETS_ORBIT"
INTELLIGENCE_DIR = BASE_DIR / "05_INTELLIGENCE_ORBIT"
PROACTIVE_DIR = BASE_DIR / "06_COPILOTO_VENDEDOR_PROACTIVO"
CONFIG_PATH = BASE_DIR / "src" / "orbit" / "config"

if str(CONFIG_PATH) not in sys.path:
    sys.path.append(str(CONFIG_PATH))

from config_comercial import OrbitConfigComercial


class OrbitAlertasRealesEngine:
    def __init__(self, tenant: str = "PENAFLOR") -> None:
        self.tenant = tenant.upper().strip()
        INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cfg = OrbitConfigComercial()

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
    def _norm_text(value) -> str:
        if pd.isna(value):
            return ""
        txt = str(value).strip().lower()
        txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("utf-8")
        txt = " ".join(txt.split())
        return txt

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
    def _priority_rank(value: str) -> int:
        value = str(value).strip().lower()
        mapping = {"critica": 1, "alta": 2, "media": 3, "baja": 4}
        return mapping.get(value, 9)

    def load_sources(self) -> Dict[str, pd.DataFrame]:
        return {
            "clientes_dia": self._read_csv_any(DATASETS_DIR / "clientes_dia.csv"),
            "mod_11_titulares": self._read_csv_any(DATASETS_DIR / "mod_11_titulares.csv"),
            "orbit_alertas_priorizadas": self._read_csv_any(INTELLIGENCE_DIR / "orbit_alertas_priorizadas.csv"),
            "top_50_caida": self._read_csv_any(PROACTIVE_DIR / "top_50_caida_vinos_alta_gama.csv"),
            "ventas_diarias": self._read_csv_any(INPUTS_DIR / "ventas_diarias.csv"),
        }

    def build_client_lookup(self, clientes_dia: pd.DataFrame) -> pd.DataFrame:
        if clientes_dia.empty:
            return pd.DataFrame(columns=["cliente_id", "cliente_nombre", "vendedor", "localidad", "segmento"])

        df = clientes_dia.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]

        col_id = self._find_first(df.columns, ["cliente_id", "cliente", "codigo", "id"])
        col_nombre = self._find_first(df.columns, ["cliente_nombre", "razon_social", "razon social", "nombre", "razon"])
        col_v = self._find_first(df.columns, ["vendedor"])
        col_loc = self._find_first(df.columns, ["localidad"])
        col_seg = self._find_first(df.columns, ["segmento", "subsegmento"])

        out = pd.DataFrame()
        out["cliente_id"] = df[col_id].astype(str).str.strip() if col_id else ""
        out["cliente_nombre"] = df[col_nombre].astype(str).str.strip() if col_nombre else ""
        out["vendedor"] = df[col_v].astype(str).str.strip() if col_v else ""
        out["localidad"] = df[col_loc].astype(str).str.strip() if col_loc else ""
        out["segmento"] = df[col_seg].astype(str).str.strip() if col_seg else ""

        out = out.drop_duplicates(subset=["cliente_id", "cliente_nombre"])
        return out

    def build_alertas_descuento(self, df: pd.DataFrame, cli: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()

        work = df.copy()
        work.columns = [str(c).strip().lower() for c in work.columns]

        col_v = self._find_first(work.columns, ["vendedor"])
        col_cli = self._find_first(work.columns, ["cliente"])
        col_prod = self._find_first(work.columns, ["producto", "articulo"])
        col_pri = self._find_first(work.columns, ["prioridad"])
        col_det = self._find_first(work.columns, ["detalle"])
        col_acc = self._find_first(work.columns, ["accion_sugerida", "accion"])
        col_id = self._find_first(work.columns, ["cliente_id", "id"])

        rows = []
        for _, row in work.iterrows():
            prioridad = self._safe_text(row[col_pri]) if col_pri else self.cfg.prioridad_default("descuento", "alta")
            prioridad = prioridad.lower()
            if prioridad not in ("alta", "media", "baja", "critica"):
                prioridad = self.cfg.prioridad_default("descuento", "alta")

            cliente_id = self._safe_text(row[col_id]) if col_id else ""
            cliente = self._safe_text(row[col_cli]) if col_cli else ""
            vendedor = self._safe_text(row[col_v]) if col_v else ""

            if cliente_id and not cli.empty:
                sub = cli[cli["cliente_id"].astype(str).str.strip() == cliente_id]
                if not sub.empty:
                    if not cliente:
                        cliente = self._safe_text(sub.iloc[0]["cliente_nombre"])
                    if not vendedor:
                        vendedor = self._safe_text(sub.iloc[0]["vendedor"])

            accion = self._safe_text(row[col_acc]) if col_acc else ""
            if not accion:
                accion = self.cfg.accion_default("descuento", "critica" if prioridad == "alta" else prioridad, "Revisar descuento y corregir margen.")

            rows.append({
                "tipo_alerta": "descuento",
                "prioridad": "critica" if prioridad == "alta" else prioridad,
                "vendedor": vendedor,
                "cliente_id": cliente_id,
                "cliente_nombre": cliente,
                "localidad": "",
                "segmento": "",
                "producto_codigo": "",
                "producto_nombre": self._safe_text(row[col_prod]) if col_prod else "",
                "motivo": self._safe_text(row[col_det]) if col_det else "Descuento fuera de parámetro",
                "accion_sugerida": accion,
                "impacto_ars": 0.0,
                "fuente": "orbit_alertas_priorizadas.csv",
            })

        return pd.DataFrame(rows)

    def build_alertas_11t(self, df: pd.DataFrame, cli: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()

        work = df.copy()
        work.columns = [str(c).strip().lower() for c in work.columns]

        col_codigo = self._find_first(work.columns, ["codigo", "cliente_id", "cliente"])
        col_cliente = self._find_first(work.columns, ["cliente"])
        col_seg = self._find_first(work.columns, ["seg", "segmento"])
        col_faltan = self._find_first(work.columns, ["faltan"])
        col_det = self._find_first(work.columns, ["detalle faltantes", "faltantes", "detalle"])

        rows = []
        for _, row in work.iterrows():
            faltan = int(self._safe_num(row[col_faltan])) if col_faltan else 0
            if faltan <= 0:
                continue

            cliente_id = self._safe_text(row[col_codigo]) if col_codigo else ""
            cliente = self._safe_text(row[col_cliente]) if col_cliente else ""
            segmento = self._safe_text(row[col_seg]) if col_seg else ""

            vendedor = ""
            localidad = ""
            if cliente_id and not cli.empty:
                sub = cli[cli["cliente_id"].astype(str).str.strip() == cliente_id]
                if not sub.empty:
                    if not cliente:
                        cliente = self._safe_text(sub.iloc[0]["cliente_nombre"])
                    vendedor = self._safe_text(sub.iloc[0]["vendedor"])
                    localidad = self._safe_text(sub.iloc[0]["localidad"])
                    if not segmento:
                        segmento = self._safe_text(sub.iloc[0]["segmento"])

            prioridad = "alta" if faltan >= 8 else "media" if faltan >= 4 else "baja"
            detalle_faltantes = self._safe_text(row[col_det]) if col_det else ""

            max_marcas = self.cfg.max_marcas_sugeridas("faltante_11_titulares", prioridad, 4)
            accion = self.cfg.accion_default("faltante_11_titulares", prioridad, "Trabajar portfolio en próxima visita.")
            if detalle_faltantes:
                marcas = [x.strip() for x in detalle_faltantes.split("|") if x.strip()]
                marcas = marcas[:max_marcas]
                if marcas:
                    accion = "Intentar vender: " + " + ".join(marcas)

            rows.append({
                "tipo_alerta": "faltante_11_titulares",
                "prioridad": prioridad,
                "vendedor": vendedor,
                "cliente_id": cliente_id,
                "cliente_nombre": cliente,
                "localidad": localidad,
                "segmento": segmento,
                "producto_codigo": "",
                "producto_nombre": detalle_faltantes[:250],
                "motivo": f"Cliente con {faltan} faltantes de 11 titulares.",
                "accion_sugerida": accion,
                "impacto_ars": 0.0,
                "fuente": "mod_11_titulares.csv",
            })

        return pd.DataFrame(rows)

    def build_alertas_proactivas(self, df: pd.DataFrame, cli: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()

        work = df.copy()
        work.columns = [str(c).strip().lower() for c in work.columns]

        col_v = self._find_first(work.columns, ["vendedor"])
        col_id = self._find_first(work.columns, ["cliente_id"])
        col_cli = self._find_first(work.columns, ["cliente_nombre", "cliente"])
        col_caida = self._find_first(work.columns, ["caida_ars", "caida", "riesgo"])
        col_tope = self._find_first(work.columns, ["descuento_maximo_ars", "tope", "descuento_ars"])
        col_prod = self._find_first(work.columns, ["productos_semana_anterior", "producto"])
        col_prev = self._find_first(work.columns, ["venta_premium_semana_anterior_ars"])
        col_act = self._find_first(work.columns, ["venta_premium_semana_actual_ars"])

        rows = []
        for _, row in work.iterrows():
            cliente_id = self._safe_text(row[col_id]) if col_id else ""
            cliente = self._safe_text(row[col_cli]) if col_cli else ""
            vendedor = self._safe_text(row[col_v]) if col_v else ""
            impacto = self._safe_num(row[col_caida]) if col_caida else 0.0

            localidad = ""
            segmento = ""
            if cliente_id and not cli.empty:
                sub = cli[cli["cliente_id"].astype(str).str.strip() == cliente_id]
                if not sub.empty:
                    if not cliente:
                        cliente = self._safe_text(sub.iloc[0]["cliente_nombre"])
                    if not vendedor:
                        vendedor = self._safe_text(sub.iloc[0]["vendedor"])
                    localidad = self._safe_text(sub.iloc[0]["localidad"])
                    segmento = self._safe_text(sub.iloc[0]["segmento"])

            prioridad = "critica" if impacto >= 50000 else "alta" if impacto >= 10000 else "media"
            anterior = self._safe_num(row[col_prev]) if col_prev else 0.0
            actual = self._safe_num(row[col_act]) if col_act else 0.0
            tope = self._safe_num(row[col_tope]) if col_tope else 0.0
            prod = self._safe_text(row[col_prod]) if col_prod else ""
            accion = self.cfg.accion_default("caida_compra", prioridad, f"Recuperar compra sin superar tope sugerido ARS {tope:,.2f}.")

            rows.append({
                "tipo_alerta": "caida_compra",
                "prioridad": prioridad,
                "vendedor": vendedor,
                "cliente_id": cliente_id,
                "cliente_nombre": cliente,
                "localidad": localidad,
                "segmento": segmento,
                "producto_codigo": "",
                "producto_nombre": prod[:250],
                "motivo": f"Caída detectada. Semana anterior ARS {anterior:,.2f} vs actual ARS {actual:,.2f}.",
                "accion_sugerida": accion,
                "impacto_ars": round(impacto, 2),
                "fuente": "top_50_caida_vinos_alta_gama.csv",
            })

        return pd.DataFrame(rows)

    def build_alertas_sin_compra(self, ventas_diarias: pd.DataFrame, cli: pd.DataFrame) -> pd.DataFrame:
        if ventas_diarias.empty or cli.empty:
            return pd.DataFrame()

        v = ventas_diarias.copy()
        v.columns = [str(c).strip().lower() for c in v.columns]

        col_cliente = self._find_first(v.columns, ["cliente", "codigo"])
        if not col_cliente:
            return pd.DataFrame()

        compraron = set(v[col_cliente].astype(str).str.strip().tolist())

        rows = []
        for _, row in cli.iterrows():
            cliente_id = self._safe_text(row["cliente_id"])
            cliente = self._safe_text(row["cliente_nombre"])
            vendedor = self._safe_text(row["vendedor"])
            localidad = self._safe_text(row["localidad"])
            segmento = self._safe_text(row["segmento"])

            if not cliente_id:
                continue

            if cliente_id not in compraron:
                prioridad = "media"
                seg_norm = self._norm_text(segmento)
                if "autoserv" in seg_norm or "vinotec" in seg_norm:
                    prioridad = "alta"

                accion = self.cfg.accion_default("sin_compra_dia", prioridad, "Revisar no compra y proponer compra mínima de cobertura.")
                rows.append({
                    "tipo_alerta": "sin_compra_dia",
                    "prioridad": prioridad,
                    "vendedor": vendedor,
                    "cliente_id": cliente_id,
                    "cliente_nombre": cliente,
                    "localidad": localidad,
                    "segmento": segmento,
                    "producto_codigo": "",
                    "producto_nombre": "",
                    "motivo": "Cliente del padrón del día sin compra detectada en ventas cargadas.",
                    "accion_sugerida": accion,
                    "impacto_ars": 0.0,
                    "fuente": "ventas_diarias.csv + clientes_dia.csv",
                })

        return pd.DataFrame(rows)

    def build_alertas_reales(self, sources: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        cli = self.build_client_lookup(sources["clientes_dia"])

        frames = [
            self.build_alertas_descuento(sources["orbit_alertas_priorizadas"], cli),
            self.build_alertas_11t(sources["mod_11_titulares"], cli),
            self.build_alertas_proactivas(sources["top_50_caida"], cli),
            self.build_alertas_sin_compra(sources["ventas_diarias"], cli),
        ]

        frames = [f for f in frames if not f.empty]
        if not frames:
            return pd.DataFrame(columns=[
                "tipo_alerta", "prioridad", "vendedor", "cliente_id", "cliente_nombre",
                "localidad", "segmento", "producto_codigo", "producto_nombre",
                "motivo", "accion_sugerida", "impacto_ars", "fuente"
            ])

        out = pd.concat(frames, ignore_index=True)

        out["vendedor"] = out["vendedor"].fillna("").astype(str).str.strip()
        out["cliente_id"] = out["cliente_id"].fillna("").astype(str).str.strip()
        out["cliente_nombre"] = out["cliente_nombre"].fillna("").astype(str).str.strip()
        out["producto_nombre"] = out["producto_nombre"].fillna("").astype(str).str.strip()

        permitidos = self.cfg.vendedores_permitidos()
        if permitidos:
            out = out[out["vendedor"].astype(str).str.strip().str.upper().isin(permitidos)].copy()

        out["prioridad_sort"] = out["prioridad"].apply(self._priority_rank)

        out["dedupe_key"] = (
            out["tipo_alerta"].astype(str) + "|" +
            out["vendedor"].astype(str) + "|" +
            out["cliente_id"].astype(str) + "|" +
            out["cliente_nombre"].astype(str) + "|" +
            out["producto_nombre"].astype(str).str[:80]
        )
        out = out.sort_values(["prioridad_sort", "impacto_ars"], ascending=[True, False])
        out = out.drop_duplicates(subset=["dedupe_key"], keep="first").reset_index(drop=True)
        out = out.drop(columns=["dedupe_key", "prioridad_sort"])

        return out

    def build_resumen_vendedor(self, alertas: pd.DataFrame) -> pd.DataFrame:
        if alertas.empty:
            return pd.DataFrame(columns=[
                "vendedor", "total_alertas", "criticas", "altas", "medias", "bajas", "impacto_total_ars"
            ])

        rows = []
        for vendedor, sub in alertas.groupby(alertas["vendedor"].fillna("").astype(str).str.strip()):
            if vendedor == "":
                vendedor = "SIN VENDEDOR"

            rows.append({
                "vendedor": vendedor,
                "total_alertas": int(len(sub)),
                "criticas": int((sub["prioridad"].astype(str).str.lower() == "critica").sum()),
                "altas": int((sub["prioridad"].astype(str).str.lower() == "alta").sum()),
                "medias": int((sub["prioridad"].astype(str).str.lower() == "media").sum()),
                "bajas": int((sub["prioridad"].astype(str).str.lower() == "baja").sum()),
                "impacto_total_ars": float(pd.to_numeric(sub["impacto_ars"], errors="coerce").fillna(0).sum()),
            })

        out = pd.DataFrame(rows)
        out = out.sort_values(
            ["criticas", "altas", "impacto_total_ars", "total_alertas"],
            ascending=[False, False, False, False]
        ).reset_index(drop=True)
        return out

    def build_gerencia_payload(self, alertas: pd.DataFrame, resumen: pd.DataFrame) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "tenant": self.tenant,
            "generated_at": self.generated_at,
            "total_alertas": 0,
            "alertas_criticas": 0,
            "impacto_total_ars": 0.0,
            "top_vendedores": [],
            "top_alertas": [],
        }

        if alertas.empty:
            return payload

        payload["total_alertas"] = int(len(alertas))
        payload["alertas_criticas"] = int((alertas["prioridad"].astype(str).str.lower() == "critica").sum())
        payload["impacto_total_ars"] = float(pd.to_numeric(alertas["impacto_ars"], errors="coerce").fillna(0).sum())

        for _, row in resumen.head(7).iterrows():
            payload["top_vendedores"].append({
                "vendedor": self._safe_text(row["vendedor"]),
                "total_alertas": int(self._safe_num(row["total_alertas"])),
                "criticas": int(self._safe_num(row["criticas"])),
                "altas": int(self._safe_num(row["altas"])),
                "impacto_total_ars": float(self._safe_num(row["impacto_total_ars"])),
            })

        top_alertas = alertas.copy()
        top_alertas["priority_sort"] = top_alertas["prioridad"].apply(self._priority_rank)
        top_alertas = top_alertas.sort_values(["priority_sort", "impacto_ars"], ascending=[True, False])

        for _, row in top_alertas.head(25).iterrows():
            payload["top_alertas"].append({
                "tipo_alerta": self._safe_text(row["tipo_alerta"]),
                "prioridad": self._safe_text(row["prioridad"]),
                "vendedor": self._safe_text(row["vendedor"]),
                "cliente_id": self._safe_text(row["cliente_id"]),
                "cliente_nombre": self._safe_text(row["cliente_nombre"]),
                "localidad": self._safe_text(row["localidad"]),
                "segmento": self._safe_text(row["segmento"]),
                "producto_nombre": self._safe_text(row["producto_nombre"]),
                "motivo": self._safe_text(row["motivo"]),
                "accion_sugerida": self._safe_text(row["accion_sugerida"]),
                "impacto_ars": float(self._safe_num(row["impacto_ars"])),
            })

        return payload

    def save_outputs(self, alertas: pd.DataFrame, resumen: pd.DataFrame, payload: Dict[str, object]) -> Dict[str, str]:
        alertas_path = INTELLIGENCE_DIR / "alertas_reales.csv"
        resumen_path = INTELLIGENCE_DIR / "alertas_reales_resumen_vendedor.csv"
        gerencia_json = INTELLIGENCE_DIR / "alertas_reales_gerencia.json"

        alertas.to_csv(alertas_path, index=False, encoding="utf-8-sig")
        resumen.to_csv(resumen_path, index=False, encoding="utf-8-sig")
        gerencia_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "alertas_csv": str(alertas_path),
            "resumen_vendedor_csv": str(resumen_path),
            "gerencia_json": str(gerencia_json),
        }

    def run(self) -> Dict[str, object]:
        print("=== ORBIT ALERTAS REALES ENGINE ===")

        sources = self.load_sources()
        alertas = self.build_alertas_reales(sources)
        resumen = self.build_resumen_vendedor(alertas)
        payload = self.build_gerencia_payload(alertas, resumen)
        files = self.save_outputs(alertas, resumen, payload)

        print(f"Alertas reales generadas: {len(alertas)}")
        print(f"Vendedores con alertas: {len(resumen)}")
        print(f"Impacto total ARS: {payload['impacto_total_ars']:,.2f}")
        print(f"CSV alertas: {files['alertas_csv']}")
        print(f"CSV resumen: {files['resumen_vendedor_csv']}")
        print(f"JSON gerencia: {files['gerencia_json']}")

        return {
            "status": "ok",
            "tenant": self.tenant,
            "alertas_rows": int(len(alertas)),
            "vendedores_rows": int(len(resumen)),
            "impacto_total_ars": float(payload["impacto_total_ars"]),
            "files": files,
        }


if __name__ == "__main__":
    result = OrbitAlertasRealesEngine().run()
    print(result)