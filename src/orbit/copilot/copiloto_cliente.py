import pandas as pd
import os
import unicodedata

BASE_DIR = r"C:\Orbit\MATINAL_PENAFLOR"
MASTER_DIR = os.path.join(BASE_DIR, "05_MASTER_DATA")
DATASETS_DIR = os.path.join(BASE_DIR, "04_DATASETS_ORBIT")


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    txt = str(valor).strip().lower()
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("utf-8")
    txt = " ".join(txt.split())
    return txt


class OrbitClientCopilot:
    def __init__(self):
        self.master = pd.read_csv(os.path.join(MASTER_DIR, "clientes_master.csv"))
        self.titulares = pd.read_csv(os.path.join(DATASETS_DIR, "mod_11_titulares.csv"))
        self.descuentos = pd.read_csv(os.path.join(DATASETS_DIR, "mod_alertas_descuentos.csv"))

    # -------------------------------------------------
    def find_col(self, df, keywords):
        cols = list(df.columns)
        cols_lower = [c.lower() for c in cols]
        for kw in keywords:
            for i, c in enumerate(cols_lower):
                if kw in c:
                    return cols[i]
        return None

    def find_client(self, query):
        q = normalizar_texto(query)

        col_id = self.find_col(self.master, ["cliente_id", "cliente", "id"])
        col_nombre = self.find_col(self.master, ["nombre"])

        if not col_id or not col_nombre:
            raise Exception("No se encontraron columnas base en clientes_master.csv")

        df = self.master.copy()
        df["_nombre_norm"] = df[col_nombre].apply(normalizar_texto)
        df["_id_norm"] = df[col_id].astype(str).str.strip()

        # por ID exacto
        by_id = df[df["_id_norm"] == str(query).strip()]
        if len(by_id) == 1:
            return by_id.iloc[0]

        # por nombre flexible
        palabras = [p for p in q.split() if p]
        for p in palabras:
            df = df[df["_nombre_norm"].str.contains(p, na=False)]

        if df.empty:
            return "Cliente no encontrado"

        if len(df) > 1:
            vista = df[[col_id, col_nombre]].head(10).to_dict(orient="records")
            return f"Múltiples clientes encontrados: {vista}"

        return df.iloc[0]

    def get_client_titulares(self, cliente_id):
        col_id_tit = self.find_col(self.titulares, ["cliente_id", "cliente", "id"])
        if not col_id_tit:
            return pd.DataFrame(), pd.DataFrame(), 0

        cli = self.titulares[self.titulares[col_id_tit].astype(str).str.strip() == str(cliente_id).strip()].copy()
        if cli.empty:
            return pd.DataFrame(), pd.DataFrame(), 0

        col_marca = self.find_col(cli, ["marca", "titular", "producto"])
        col_compra = self.find_col(cli, ["compra", "cantidad", "volumen"])

        total = len(cli)

        if not col_compra:
            faltantes = cli.copy()
            comprados = pd.DataFrame(columns=cli.columns)
        else:
            cli[col_compra] = pd.to_numeric(cli[col_compra], errors="coerce").fillna(0)
            comprados = cli[cli[col_compra] > 0].copy()
            faltantes = cli[cli[col_compra] <= 0].copy()

        return comprados, faltantes, total

    def get_client_discount_alert(self, cliente_id):
        if self.descuentos.empty:
            return ""

        col_id_desc = self.find_col(self.descuentos, ["cliente_id", "cliente", "id"])
        if not col_id_desc:
            return ""

        cli = self.descuentos[self.descuentos[col_id_desc].astype(str).str.strip() == str(cliente_id).strip()].copy()
        if cli.empty:
            return ""

        col_desc_aplicado = self.find_col(cli, ["descuento_aplicado_pct", "descuento", "desc"])
        col_desc_max = self.find_col(cli, ["descuento_maximo_pct", "maximo"])
        col_exceso = self.find_col(cli, ["exceso_pct", "exceso"])
        col_valor = self.find_col(cli, ["valor_descuento", "impacto", "monto"])

        desc_aplicado = 0
        desc_max = 0
        exceso = 0
        impacto = 0

        if col_desc_aplicado:
            desc_aplicado = pd.to_numeric(cli[col_desc_aplicado], errors="coerce").fillna(0).max()
        if col_desc_max:
            desc_max = pd.to_numeric(cli[col_desc_max], errors="coerce").fillna(0).max()
        if col_exceso:
            exceso = pd.to_numeric(cli[col_exceso], errors="coerce").fillna(0).max()
        if col_valor:
            impacto = pd.to_numeric(cli[col_valor], errors="coerce").fillna(0).sum()

        if max(desc_aplicado, desc_max, exceso, impacto) == 0:
            return ""

        return (
            f"⚠ Descuento detectado | Aplicado: {round(desc_aplicado,2)}% | "
            f"Máximo: {round(desc_max,2)}% | Exceso: {round(exceso,2)}% | "
            f"Impacto: ${round(impacto,2)}"
        )

    def build_message(self, cliente_row):
        col_id = self.find_col(self.master, ["cliente_id", "cliente", "id"])
        col_nombre = self.find_col(self.master, ["nombre"])
        col_vendedor = self.find_col(self.master, ["vendedor", "codven"])
        col_segmento = self.find_col(self.master, ["segmento"])
        col_localidad = self.find_col(self.master, ["localidad"])

        cliente_id = cliente_row[col_id]
        nombre = cliente_row[col_nombre] if col_nombre else "N/D"
        vendedor = cliente_row[col_vendedor] if col_vendedor else "N/D"
        segmento = cliente_row[col_segmento] if col_segmento else "N/D"
        localidad = cliente_row[col_localidad] if col_localidad else "N/D"

        comprados, faltantes, total = self.get_client_titulares(cliente_id)
        alerta_desc = self.get_client_discount_alert(cliente_id)

        col_marca_f = self.find_col(faltantes, ["marca", "titular", "producto"])

        lineas = []
        lineas.append("=" * 30)
        lineas.append(f"CLIENTE: {nombre}")
        lineas.append(f"CÓDIGO: {cliente_id}")
        lineas.append(f"VENDEDOR: {vendedor}")
        lineas.append(f"SEGMENTO: {segmento}")
        lineas.append(f"LOCALIDAD: {localidad}")
        lineas.append("=" * 30)
        lineas.append("")
        lineas.append("PORTAFOLIO:")
        lineas.append(f"- Compra: {len(comprados)}/{total}")
        lineas.append(f"- Falta desarrollar: {len(faltantes)}")
        lineas.append("")
        lineas.append("OPORTUNIDAD:")

        if not faltantes.empty and col_marca_f:
            top = faltantes[col_marca_f].dropna().astype(str).head(5).tolist()
            for m in top:
                lineas.append(f"- {m}")
        else:
            lineas.append("- Sin faltantes detectados o sin información de portafolio")

        lineas.append("")
        lineas.append("ACCIÓN RECOMENDADA:")

        if len(faltantes) > 0:
            lineas.append("- Activar marcas faltantes")
            lineas.append("- Priorizar volumen sin depender de descuento")
        else:
            lineas.append("- Defender volumen actual")
            lineas.append("- Evitar descuentos innecesarios")

        if alerta_desc:
            lineas.append("")
            lineas.append(alerta_desc)
            lineas.append("- No repetir descuento por encima del máximo")
            lineas.append("- Intentar cierre a precio objetivo")

        return "\n".join(lineas)

    def ejecutar(self, query):
        result = self.find_client(query)

        if isinstance(result, str):
            return result

        return self.build_message(result)


if __name__ == "__main__":
    cop = OrbitClientCopilot()

    while True:
        q = input("\nBuscar cliente (o 'salir'): ").strip()
        if q.lower() == "salir":
            break

        print("\n" + cop.ejecutar(q))

    input("\nPresioná Enter para cerrar...")