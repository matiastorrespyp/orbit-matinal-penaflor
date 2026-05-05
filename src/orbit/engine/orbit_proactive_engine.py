import os
import pandas as pd
import unicodedata
from datetime import datetime

# ==============================
# CONFIGURACIÓN DE NÚCLEO
# ==============================
PATHS = {
    "PENAFLOR": "C:/Orbit/MATINAL_PENAFLOR",
    "PEPSICO": "C:/Orbit/MATINAL_PEPSICO" # Puerta abierta para PepsiCo
}

EMPRESA_ACTIVA = "PENAFLOR"
BASE_PATH = PATHS[EMPRESA_ACTIVA]
DATASETS_PATH = os.path.join(BASE_PATH, "04_DATASETS_ORBIT")
MASTER_PATH = os.path.join(BASE_PATH, "05_MASTER_DATA")
OUTPUT_PATH = os.path.join(BASE_PATH, "06_OUTPUT_VENDEDORES")

if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)

# ==============================
# PROCESADOR DE INTELIGENCIA
# ==============================
class OrbitProactiveEngine:
    def __init__(self):
        self.df_clientes = None
        self.df_hist = None
        self.df_titulares = None

    def normalizar_columnas(self, df):
        df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]
        return df

    def cargar_protocolo(self):
        """Carga y normaliza el universo de datos."""
        try:
            self.df_clientes = self.normalizar_columnas(pd.read_csv(os.path.join(MASTER_PATH, "clientes_master.csv")))
            self.df_hist = self.normalizar_columnas(pd.read_csv(os.path.join(DATASETS_PATH, "hist_cliente_producto.csv")))
            self.df_titulares = self.normalizar_columnas(pd.read_csv(os.path.join(DATASETS_PATH, "mod_11_titulares.csv")))
        except Exception as e:
            raise Exception(f"FALLO CRÍTICO EN CARGA: {e}")

    def procesar_universo(self):
        """Analiza los 1,200 clientes y genera el plan de ataque."""
        hoja_ruta_vendedores = []
        
        titulares_set = set(self.df_titulares["producto"].unique())

        for _, cliente in self.df_clientes.iterrows():
            c_id = cliente["cliente_id"]
            
            # Obtener historial específico
            hist_c = self.df_hist[self.df_hist["cliente_id"] == c_id]
            productos_comprados = set(hist_c["producto"].unique())
            
            # Identificar brechas (Faltantes)
            faltantes = list(titulares_set - productos_comprados)
            cobertura = len(productos_comprados.intersection(titulares_set))
            
            # Solo agregar si falta algo del portafolio core
            if faltantes:
                hoja_ruta_vendedores.append({
                    "VENDEDOR": cliente.get("vendedor", "SIN ASIGNAR"),
                    "CLIENTE": cliente["cliente_nombre"],
                    "LOCALIDAD": cliente.get("localidad", "N/D"),
                    "COBERTURA": f"{cobertura}/{len(titulares_set)}",
                    "PRODUCTOS_A_COLOCAR": ", ".join(faltantes[:3]), # Top 3 urgentes
                    "ACCION_ARS": "Priorizar precio de lista (Sin Descuento)"
                })
        
        return pd.DataFrame(hoja_ruta_vendedores)

    def exportar_planes_de_accion(self, df_resultado):
        """Genera archivos individuales por vendedor para envío automático."""
        vendedores = df_resultado["VENDEDOR"].unique()
        fecha_str = datetime.now().strftime("%Y-%m-%d")

        for v in vendedores:
            df_vendedor = df_resultado[df_resultado["VENDEDOR"] == v]
            filename = f"PLAN_ACCION_V{v}_{fecha_str}.csv"
            df_vendedor.to_csv(os.path.join(OUTPUT_PATH, filename), index=False, sep=";")
        
        print(f"KERNEL: {len(vendedores)} planes de acción generados en {OUTPUT_PATH}")

# ==============================
# EJECUCIÓN ABSOLUTA
# ==============================
if __name__ == "__main__":
    print(f"--- INICIANDO ORBIT PROACTIVE ENGINE ({EMPRESA_ACTIVA}) ---")
    engine = OrbitProactiveEngine()
    engine.cargar_protocolo()
    resultados = engine.procesar_universo()
    engine.exportar_planes_de_accion(resultados)
    print("--- PROCESO FINALIZADO CON CERO ERRORES ---")