#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_11titulares_excel.py
============================
Genera 03_OUTPUTS/11 titulares.xlsx

Una hoja por día de visita (Lu, Ma, Mi, Ju, Vi, Sa).
Cada hoja: Vendedor | Cliente | [marca1 ... marca11] | TOTAL

Fuentes
-------
  Ventas    : 01_INPUTS/ventas_acumulada.csv   (principal)
  Clientes  : 01_INPUTS/clientes.xlsx
  Objetivos : 01_INPUTS/objetivo 11T.xlsx

Excluye V2, V5, V20.
"""
import sys
from pathlib import Path
import pandas as pd

ROOT    = Path(__file__).parent
INPUTS  = ROOT / "01_INPUTS"
OUTPUTS = ROOT / "03_OUTPUTS"
OUTPUTS.mkdir(exist_ok=True)

EXCLUIDOS = {2, 5, 20}

DAY_ORDER  = ["Lu","Ma","Mi","Ju","Vi","Sa"]
DAY_LABELS = {
    "Lu":"LUNES","Ma":"MARTES","Mi":"MIÉRCOLES",
    "Ju":"JUEVES","Vi":"VIERNES","Sa":"SÁBADO",
}

# ── Alias de marcas (igual que el servidor) ──────────────────────────────────
MARCA_LOOKUP = {
    "ALMA MORA":"ALMA MORA","ALARIS":"ALARIS","TRAPICHE ALARIS":"ALARIS",
    "DON DAVID":"DON DAVID","DADA":"DADA","LOS ARBOLES":"LOS ARBOLES",
    "FINCA LAS MORAS":"FINCA LAS MORAS","F LAS MORAS":"FINCA LAS MORAS",
    "TRAPICHE RESERVA":"TRAPICHE RESERVA",
    "FOND DE CAVE":"FOND DE CAVE","FOND CAVE":"FOND DE CAVE",
    "CAZADOR":"CAZADOR","ANTARES":"ANTARES",
    "GORDON'S FLAVOURS":"GORDON'S FLAVOURS","GORDONS FLAVOURS":"GORDON'S FLAVOURS",
    "GORDON'S":"GORDON'S FLAVOURS","GORDONS":"GORDON'S FLAVOURS","GORDON S":"GORDON'S FLAVOURS",
    "SMIRNOFF":"SMIRNOFF FLAVOURS","SMIRNOFF FLAVOURS":"SMIRNOFF FLAVOURS",
    "SMIRNOFF ICE FLAVOURS":"SMIRNOFF ICE","SMIRNOFF ICE":"SMIRNOFF ICE",
    "JW":"JW BLACK","JW BLACK":"JW BLACK","JW RED":"JW RED",
    "MASCOTA":"MASCOTA","LA MASCOTA":"MASCOTA",
    "NC ESPUMANTES":"NC ESPUMANTES","NAVARRO CORREAS":"NC ESPUMANTES",
    "TRAPICHE MEDALLA":"TRAPICHE MEDALLA","GRAN MEDALLA":"TRAPICHE MEDALLA",
}
ART_KW = [
    ("SMIRNOFF ICE","SMIRNOFF ICE"),("SMF ICE","SMIRNOFF ICE"),
    ("SMIRNOFF","SMIRNOFF FLAVOURS"),("GORDON","GORDON'S FLAVOURS"),
    ("ANTARES","ANTARES"),("CAZADOR","CAZADOR"),("FOND DE CAVE","FOND DE CAVE"),
    ("ALMA MORA","ALMA MORA"),("LOS ARBOLES","LOS ARBOLES"),("DADA","DADA"),
    ("FINCA LAS MORAS","FINCA LAS MORAS"),("F.LAS MORAS","FINCA LAS MORAS"),
    ("DON DAVID","DON DAVID"),("ALARIS","ALARIS"),("TRAPICHE RESERVA","TRAPICHE RESERVA"),
    ("JW BLACK","JW BLACK"),("JW RED","JW RED"),
]
OBJ_ALIAS = {
    "ALMA MORA":"ALMA MORA","TRAPICHE RESERVA":"TRAPICHE RESERVA",
    "FINCA LAS MORAS":"FINCA LAS MORAS","ALARIS":"ALARIS",
    "DON DAVID":"DON DAVID","DADA":"DADA",
    "SIMRNOFF FLAVORS":"SMIRNOFF FLAVOURS","SMIRNOFF FLAVORS":"SMIRNOFF FLAVOURS",
    "SMIRNOFF FLAVOURS":"SMIRNOFF FLAVOURS","LOS ARBOLES":"LOS ARBOLES",
    "ANTARES":"ANTARES","SMIRNOFF ICE":"SMIRNOFF ICE","SMF ICE":"SMIRNOFF ICE",
    "GORDONS FLAVOURS":"GORDON'S FLAVOURS","GORDONS FLAVORS":"GORDON'S FLAVOURS",
    "GORDON'S FLAVOURS":"GORDON'S FLAVOURS",
}


def normalize_marca(marca_raw, art_raw=""):
    m = str(marca_raw).upper().strip()
    if m in MARCA_LOOKUP:
        return MARCA_LOOKUP[m]
    art = str(art_raw).upper()
    for kw, mo in ART_KW:
        if kw in art:
            return mo
    return None


def load_marcas_objetivo():
    """Lista de marcas oficiales 11T desde objetivo 11T.xlsx."""
    try:
        df = pd.read_excel(INPUTS / "objetivo 11T.xlsx", header=1)
        df = df.dropna(subset=df.columns[1:2])
        marcas = []
        for _, row in df.iterrows():
            raw = str(row.iloc[1]).upper().strip()
            mk  = OBJ_ALIAS.get(raw, raw)
            if mk and mk not in marcas:
                marcas.append(mk)
        if marcas:
            return marcas
    except Exception as e:
        print(f"  AVISO: no se pudo leer objetivo 11T.xlsx ({e}). Usando lista por defecto.")
    # Fallback a lista por defecto
    return [
        "ALMA MORA","ALARIS","DON DAVID","DADA","LOS ARBOLES",
        "FINCA LAS MORAS","TRAPICHE RESERVA","FOND DE CAVE",
        "ANTARES","GORDON'S FLAVOURS","SMIRNOFF FLAVOURS","SMIRNOFF ICE",
    ]


def main():
    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("ERROR: instale openpyxl -> pip install openpyxl")
        sys.exit(1)

    print("=" * 54)
    print("  ORBIT · 11 TITULARES POR CLIENTE / VENDEDOR / DIA")
    print("=" * 54)

    # ── 1. Ventas acumuladas ─────────────────────────────────
    vac_path = INPUTS / "ventas_acumulada.csv"
    if not vac_path.exists():
        print(f"ERROR: {vac_path} no encontrado.")
        sys.exit(1)

    print("\n[1/4] Leyendo ventas_acumulada.csv ...")
    vac = pd.read_csv(vac_path, sep=";", encoding="latin1", low_memory=False)
    vac["ImporteNetoItem"] = pd.to_numeric(
        vac["ImporteNetoItem"].astype(str).str.replace(",",".",regex=False), errors="coerce")
    vac = vac[~vac["CodVendedor"].astype(float).astype(int).isin(EXCLUIDOS)]
    vac = vac[vac["ImporteNetoItem"] > 0]

    vac["marca_norm"] = vac.apply(
        lambda r: normalize_marca(r.get("Marca",""), r.get("Articulo","")), axis=1)

    # Conjunto CCC: pares (cliente_id int, marca_norm str)
    vac_ok = vac[vac["marca_norm"].notna()][["Cliente","marca_norm"]].drop_duplicates()
    ccc_set = set(zip(vac_ok["Cliente"].astype(int), vac_ok["marca_norm"]))
    print(f"  {len(ccc_set):,} pares cliente-marca con compra (CCC)")

    # ── 2. Clientes ─────────────────────────────────────────
    print("[2/4] Leyendo clientes.xlsx ...")
    cli = pd.read_excel(INPUTS / "clientes.xlsx")

    # Detectar columnas
    cod_col  = next((c for c in cli.columns if c.lower() in ("codigo","cod","id")), cli.columns[0])
    nom_col  = next((c for c in cli.columns if "razon" in c.lower() or "nombre" in c.lower()), cli.columns[1])
    vend_col = next((c for c in cli.columns if c.lower() == "codven"), None)
    vnom_col = next((c for c in cli.columns if c.lower() == "vendedor"), None)
    dias_col = next((c for c in cli.columns if "diasvisita" in c.lower().replace(" ","")), None)

    if not dias_col:
        print("ERROR: columna DiasVisita no encontrada en clientes.xlsx")
        sys.exit(1)

    print(f"  {len(cli):,} clientes | cols: {cod_col}, {nom_col}, {vend_col}, {vnom_col}, {dias_col}")

    # Excluir vendedores no activos
    if vend_col:
        cli = cli[~pd.to_numeric(cli[vend_col], errors="coerce").isin(EXCLUIDOS)]

    # ── 3. Marcas 11T ───────────────────────────────────────
    print("[3/4] Cargando marcas objetivo ...")
    marcas_11t = load_marcas_objetivo()
    print(f"  {len(marcas_11t)} marcas: {', '.join(marcas_11t)}")

    # ── 4. Generar Excel ─────────────────────────────────────
    print("[4/4] Construyendo Excel ...")

    wb = Workbook()
    wb.remove(wb.active)  # eliminar hoja por defecto

    # Estilos
    C_BG_HDR   = "1A1A2E"   # azul muy oscuro — encabezado
    C_BG_VEND  = "0F0F2D"   # fondo vendedor
    C_BG_CLI   = "16213E"   # fondo cliente
    C_BG_OK    = "155724"   # verde oscuro — tiene
    C_BG_NO    = "6B1A1A"   # rojo oscuro  — falta
    C_BG_TOT_OK= "0D4A1E"   # verde total >=11
    C_BG_TOT_HF= "0D3030"   # verde-azul >50%
    C_BG_TOT_NO= "4A0D0D"   # rojo total <50%

    FILL_HDR  = PatternFill("solid", fgColor=C_BG_HDR)
    FILL_VEND = PatternFill("solid", fgColor=C_BG_VEND)
    FILL_CLI  = PatternFill("solid", fgColor=C_BG_CLI)
    FILL_OK   = PatternFill("solid", fgColor=C_BG_OK)
    FILL_NO   = PatternFill("solid", fgColor=C_BG_NO)

    FNT_HDR   = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
    FNT_VEND  = Font(bold=True, color="E2147A", name="Calibri", size=9)
    FNT_CLI   = Font(color="CCCCCC",            name="Calibri", size=9)
    FNT_CHK   = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
    FNT_TOT   = Font(bold=True, color="FFFFFF", name="Calibri", size=10)

    thin   = Side(border_style="thin", color="2A2A4A")
    BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

    AL_CTR = Alignment(horizontal="center", vertical="center")
    AL_LFT = Alignment(horizontal="left",   vertical="center")
    AL_HDR = Alignment(horizontal="center", vertical="center", wrap_text=True)

    dias_presentes = cli[dias_col].dropna().unique()
    dias_a_procesar = [d for d in DAY_ORDER if d in dias_presentes] + \
                      [d for d in dias_presentes if d not in DAY_ORDER]

    for dia in dias_a_procesar:
        label = DAY_LABELS.get(dia, dia.upper())
        ws = wb.create_sheet(title=label)

        # Clientes del día, ordenados por vendedor y nombre
        mask = cli[dias_col].astype(str).str.strip().str.lower() == dia.lower()
        cli_dia = cli[mask].copy()
        sort_cols = [c for c in [vend_col, nom_col] if c]
        if sort_cols:
            cli_dia = cli_dia.sort_values(sort_cols)

        # ── Encabezado ──────────────────────────────────────
        headers = ["Vendedor", "Cliente"] + [m[:22] for m in marcas_11t] + ["TOTAL ✓"]
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.fill      = FILL_HDR
            cell.font      = FNT_HDR
            cell.alignment = AL_HDR
            cell.border    = BORDER
        ws.row_dimensions[1].height = 44
        ws.freeze_panes = "C2"

        # ── Filas de datos ───────────────────────────────────
        for ri, (_, row) in enumerate(cli_dia.iterrows(), 2):
            cid  = int(row[cod_col]) if pd.notna(row[cod_col]) else -1
            cnom = str(row[nom_col]) if pd.notna(row[nom_col]) else "–"
            vend = int(row[vend_col]) if (vend_col and pd.notna(row[vend_col])) else 0
            vnom = str(row[vnom_col]) if (vnom_col and pd.notna(row[vnom_col])) else str(vend)

            label_v = f"V{vend} · {vnom}" if vnom != str(vend) else f"V{vend}"

            # Vendedor
            c = ws.cell(row=ri, column=1, value=label_v)
            c.fill=FILL_VEND; c.font=FNT_VEND; c.alignment=AL_LFT; c.border=BORDER

            # Cliente
            c = ws.cell(row=ri, column=2, value=cnom)
            c.fill=FILL_CLI; c.font=FNT_CLI; c.alignment=AL_LFT; c.border=BORDER

            # Marcas
            total_ok = 0
            for mi, marca in enumerate(marcas_11t, 3):
                tiene = (cid, marca) in ccc_set
                if tiene:
                    total_ok += 1
                val = "✓" if tiene else "✗"
                c = ws.cell(row=ri, column=mi, value=val)
                c.fill      = FILL_OK if tiene else FILL_NO
                c.font      = FNT_CHK
                c.alignment = AL_CTR
                c.border    = BORDER

            # Total
            pct_tot = total_ok / len(marcas_11t)
            if pct_tot >= 1:
                fgt = PatternFill("solid", fgColor=C_BG_TOT_OK)
            elif pct_tot >= 0.5:
                fgt = PatternFill("solid", fgColor=C_BG_TOT_HF)
            else:
                fgt = PatternFill("solid", fgColor=C_BG_TOT_NO)
            c = ws.cell(row=ri, column=len(headers), value=total_ok)
            c.fill=fgt; c.font=FNT_TOT; c.alignment=AL_CTR; c.border=BORDER

        # ── Anchos de columna ────────────────────────────────
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 34
        for i in range(len(marcas_11t)):
            ws.column_dimensions[get_column_letter(i+3)].width = 12
        ws.column_dimensions[get_column_letter(len(headers))].width = 9

        print(f"  Hoja {label:12s}: {len(cli_dia):3d} clientes")

    out = OUTPUTS / "11 titulares.xlsx"
    wb.save(out)
    print(f"\n{'='*54}")
    print(f"  GUARDADO: {out}")
    print(f"  Hojas   : {', '.join(ws.title for ws in wb.worksheets)}")
    print(f"{'='*54}\n")


if __name__ == "__main__":
    main()
