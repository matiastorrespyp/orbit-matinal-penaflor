import os
import pandas as pd
import unicodedata

# ==============================
# CONFIG GLOBAL (MULTI-TENANT READY)
# ==============================
BASE_PATH = "C:/Orbit/MATINAL_PENAFLOR"
DATASETS_PATH = os.path.join(BASE_PATH, "04_DATASETS_ORBIT")
MASTER_PATH = os.path.join(BASE_PATH, "05_MASTER_DATA")

EMPRESA = "PENAFOR"  # futuro: PEPSICO

# ==============================
# UTILIDADES
# ==============================
def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto.strip()

# ==============================
# KERNEL CLIENTE
# ==============================
class OrbitClienteKernel:

    def __init__(self):
        self.df_clientes = None
        self.df_hist = None
        self.df_titulares = None

    def cargar_datos(self):
        try:
            self.df_clientes = pd.read_csv(os.path.join(MASTER_PATH, "clientes_master.csv"))
            self.df_hist = pd.read_csv(os.path.join(DATASETS_PATH, "hist_cliente_producto.csv"))
            self.df_titulares = pd.read_csv(os.path.join(DATASETS_PATH, "mod_11_titulares.csv"))
        except Exception as e:
            raise Exception(f"Error cargando datasets: {e}")

        # NORMALIZAR
        self.df_clientes.columns = [c.lower() for c in self.df_clientes.columns]
        self.df_hist.columns = [c.lower() for c in self.df_hist.columns]
        self.df_titulares.columns = [c.lower() for c in self.df_titulares.columns]

        # generar campo normalizado
        self.df_clientes["cliente_norm"] = self.df_clientes["cliente_nombre"].apply(normalizar_texto)

    def buscar_cliente(self, query):
        query_norm = normalizar_texto(query)

        matches = self.df_clientes[
            self.df_clientes["cliente_norm"].str.contains(query_norm, na=False)
        ]

        if matches.empty:
            return None

        return matches.iloc[0]

    def analizar_cliente(self, cliente_row):

        cliente_id = cliente_row["cliente_id"]
        nombre = cliente_row["cliente_nombre"]
        vendedor = cliente_row.get("vendedor", "N/D")
        segmento = cliente_row.get("segmento", "N/D")
        localidad = cliente_row.get("localidad", "N/D")

        # HISTORIAL
        hist = self.df_hist[self.df_hist["cliente_id"] == cliente_id]

        productos_hist = hist["producto"].unique().tolist() if not hist.empty else []

        # TITULARES
        titulares = self.df_titulares["producto"].unique().tolist()

        faltantes = [p for p in titulares if p not in productos_hist]

        cobertura = len(productos_hist)
        total = len(titulares)

        return {
            "cliente": nombre,
            "vendedor": vendedor,
            "segmento": segmento,
            "localidad": localidad,
            "cobertura": cobertura,
            "total": total,
            "faltantes": faltantes[:5]
        }

    def generar_accion(self, data):

        accion = f"""
CLIENTE: {data['cliente']}
VENDEDOR: {data['vendedor']}
SEGMENTO: {data['segmento']}
LOCALIDAD: {data['localidad']}

PORTAFOLIO: {data['cobertura']}/{data['total']}

FOCO INMEDIATO:
- {chr(10).join(data['faltantes'])}

ACCIÓN:
- Activar productos faltantes
- Priorizar venta sin descuento
- Consolidar mix de cartera
"""
        return accion

    def ejecutar(self):

        self.cargar_datos()

        while True:
            query = input("\nBuscar cliente (o 'salir'): ")

            if query.lower() == "salir":
                break

            cliente = self.buscar_cliente(query)

            if cliente is None:
                print("Cliente no encontrado")
                continue

            data = self.analizar_cliente(cliente)
            output = self.generar_accion(data)

            print("\n" + "="*40)
            print(output)
            print("="*40)


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    try:
        kernel = OrbitClienteKernel()
        kernel.ejecutar()
    except Exception as e:
        print(f"ERROR KERNEL: {e}")