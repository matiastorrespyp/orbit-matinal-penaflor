from __future__ import annotations

from pathlib import Path
import pandas as pd

BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
CONFIG_DIR = BASE_DIR / "09_CONFIG"


class OrbitConfigComercial:
    def __init__(self, config_dir: str | Path = CONFIG_DIR) -> None:
        self.config_dir = Path(config_dir)
        self.vendedores_activos = self._read_csv("vendedores_activos.csv")
        self.reglas_alertas = self._read_csv("reglas_alertas.csv")
        self.acciones_comerciales = self._read_csv("acciones_comerciales.csv")

    def _read_csv(self, name: str) -> pd.DataFrame:
        path = self.config_dir / name
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
    def _norm(value) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip().upper()

    def vendedores_permitidos(self) -> set[str]:
        if self.vendedores_activos.empty:
            return set()

        df = self.vendedores_activos.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]

        if "vendedor" not in df.columns:
            return set()

        if "activo" in df.columns:
            df = df[df["activo"].astype(str).str.strip().isin(["1", "true", "TRUE", "si", "SI"])]

        return {self._norm(v) for v in df["vendedor"].tolist() if self._norm(v)}

    def prioridad_default(self, tipo_alerta: str, fallback: str = "media") -> str:
        if self.reglas_alertas.empty:
            return fallback

        df = self.reglas_alertas.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]

        if "tipo_alerta" not in df.columns or "prioridad_default" not in df.columns:
            return fallback

        sub = df[df["tipo_alerta"].astype(str).str.strip().str.lower() == str(tipo_alerta).strip().lower()]
        if sub.empty:
            return fallback

        return str(sub.iloc[0]["prioridad_default"]).strip().lower() or fallback

    def accion_default(self, tipo_alerta: str, prioridad: str, fallback: str = "") -> str:
        if self.acciones_comerciales.empty:
            return fallback

        df = self.acciones_comerciales.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]

        needed = {"tipo_alerta", "prioridad", "accion_sugerida_default"}
        if not needed.issubset(set(df.columns)):
            return fallback

        sub = df[
            (df["tipo_alerta"].astype(str).str.strip().str.lower() == str(tipo_alerta).strip().lower()) &
            (df["prioridad"].astype(str).str.strip().str.lower() == str(prioridad).strip().lower())
        ]
        if sub.empty:
            return fallback

        return str(sub.iloc[0]["accion_sugerida_default"]).strip() or fallback

    def max_marcas_sugeridas(self, tipo_alerta: str, prioridad: str, fallback: int = 4) -> int:
        if self.acciones_comerciales.empty:
            return fallback

        df = self.acciones_comerciales.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]

        needed = {"tipo_alerta", "prioridad", "max_marcas_sugeridas"}
        if not needed.issubset(set(df.columns)):
            return fallback

        sub = df[
            (df["tipo_alerta"].astype(str).str.strip().str.lower() == str(tipo_alerta).strip().lower()) &
            (df["prioridad"].astype(str).str.strip().str.lower() == str(prioridad).strip().lower())
        ]
        if sub.empty:
            return fallback

        try:
            return int(float(sub.iloc[0]["max_marcas_sugeridas"]))
        except Exception:
            return fallback