from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


BASE_DIR = Path(r"C:\Orbit\MATINAL_PENAFLOR")
DATASETS_DIR = BASE_DIR / "04_DATASETS_ORBIT"
INTELLIGENCE_DIR = BASE_DIR / "05_INTELLIGENCE_ORBIT"
KERNEL_DIR = BASE_DIR / "06_KERNEL_OUTPUT"
OUTPUT_DIR = BASE_DIR / "07_PAV_OUTPUT"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class OrbitPavPdf:
    def __init__(self) -> None:
        self.fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.styles = self._build_styles()

    # =========================================================
    # ESTILOS
    # =========================================================
    def _build_styles(self):
        base = getSampleStyleSheet()

        base.add(ParagraphStyle(
            name="OrbitTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_LEFT,
            spaceAfter=8,
        ))

        base.add(ParagraphStyle(
            name="OrbitSubTitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748B"),
            alignment=TA_LEFT,
            spaceAfter=16,
        ))

        base.add(ParagraphStyle(
            name="OrbitSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=10,
        ))

        base.add(ParagraphStyle(
            name="OrbitCardLabel",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER,
        ))

        base.add(ParagraphStyle(
            name="OrbitCardValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_CENTER,
        ))

        base.add(ParagraphStyle(
            name="OrbitBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#111827"),
            alignment=TA_LEFT,
        ))

        base.add(ParagraphStyle(
            name="OrbitSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#334155"),
            alignment=TA_LEFT,
        ))

        base.add(ParagraphStyle(
            name="OrbitAction",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.white,
            alignment=TA_LEFT,
        ))

        return base

    # =========================================================
    # HELPERS
    # =========================================================
    @staticmethod
    def _safe_text(v) -> str:
        if pd.isna(v):
            return ""
        return str(v).strip()

    @staticmethod
    def _safe_num(v) -> float:
        try:
            if pd.isna(v):
                return 0.0
            if isinstance(v, str):
                v = v.strip().replace("$", "").replace("%", "")
                if "," in v and "." in v:
                    v = v.replace(".", "").replace(",", ".")
                elif "," in v:
                    v = v.replace(",", ".")
            return float(v)
        except Exception:
            return 0.0

    @staticmethod
    def _find_first(columns, keywords: List[str]) -> Optional[str]:
        cols = list(columns)
        cols_lower = [str(c).lower() for c in cols]
        for kw in keywords:
            for i, c in enumerate(cols_lower):
                if kw in c:
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

    def _pick_existing(self, folder: Path, names: List[str]) -> pd.DataFrame:
        for n in names:
            p = folder / n
            if p.exists():
                df = self._read_csv_any(p)
                if not df.empty:
                    return df
        return pd.DataFrame()

    def _money(self, value: float) -> str:
        return f"ARS {value:,.2f}"

    def _p(self, text: str, style: str):
        return Paragraph(text, self.styles[style])

    # =========================================================
    # CARGA
    # =========================================================
    def load_sources(self) -> Dict[str, pd.DataFrame]:
        foco = self._pick_existing(INTELLIGENCE_DIR, ["orbit_foco_vendedor.csv"])
        kernel_top = self._pick_existing(KERNEL_DIR, ["kernel_proactivo_top50.csv", "kernel_output.csv", "top_50_caida_vinos_alta_gama.csv"])
        volumen = self._pick_existing(DATASETS_DIR, ["mod_volumen_vendedor.csv"])
        clientes_dia = self._pick_existing(DATASETS_DIR, ["clientes_dia.csv"])

        return {
            "foco": foco,
            "kernel_top": kernel_top,
            "volumen": volumen,
            "clientes_dia": clientes_dia,
        }

    # =========================================================
    # DATA GERENCIA
    # =========================================================
    def build_gerencia_data(self, data: Dict[str, pd.DataFrame]) -> Dict[str, object]:
        foco = data["foco"].copy()
        kernel_top = data["kernel_top"].copy()
        volumen = data["volumen"].copy()
        clientes_dia = data["clientes_dia"].copy()

        total_vendedores = len(foco) if not foco.empty else 0
        clientes_hoy = len(clientes_dia) if not clientes_dia.empty else 0

        total_alertas = 0
        criticas = 0
        if not foco.empty:
            c_total = self._find_first(foco.columns, ["total_alertas"])
            c_crit = self._find_first(foco.columns, ["alertas_alta", "criticas"])
            if c_total:
                total_alertas = int(pd.to_numeric(foco[c_total], errors="coerce").fillna(0).sum())
            if c_crit:
                criticas = int(pd.to_numeric(foco[c_crit], errors="coerce").fillna(0).sum())

        riesgo_ars = 0.0
        top_clientes = []
        if not kernel_top.empty:
            c_cliente = self._find_first(kernel_top.columns, ["cliente_nombre", "cliente"])
            c_vendedor = self._find_first(kernel_top.columns, ["vendedor"])
            c_localidad = self._find_first(kernel_top.columns, ["localidad"])
            c_producto = self._find_first(kernel_top.columns, ["producto_ref", "producto"])
            c_caida = self._find_first(kernel_top.columns, ["caida", "riesgo"])
            c_tope = self._find_first(kernel_top.columns, ["descuento_max_ars", "descuento_ars", "tope"])

            if c_caida:
                riesgo_ars = float(pd.to_numeric(kernel_top[c_caida], errors="coerce").fillna(0).sum())

            for _, row in kernel_top.head(12).iterrows():
                top_clientes.append({
                    "cliente": self._safe_text(row[c_cliente]) if c_cliente else "",
                    "vendedor": self._safe_text(row[c_vendedor]) if c_vendedor else "",
                    "localidad": self._safe_text(row[c_localidad]) if c_localidad else "",
                    "producto": self._safe_text(row[c_producto]) if c_producto else "",
                    "caida_ars": self._safe_num(row[c_caida]) if c_caida else 0.0,
                    "tope_ars": self._safe_num(row[c_tope]) if c_tope else 0.0,
                })

        venta_total = 0.0
        if not volumen.empty:
            c_venta = self._find_first(volumen.columns, ["venta", "importe", "neto", "total", "volumen"])
            if c_venta:
                venta_total = float(pd.to_numeric(volumen[c_venta], errors="coerce").fillna(0).sum())

        top_vendedores = []
        if not foco.empty:
            c_vendedor = self._find_first(foco.columns, ["vendedor"])
            c_total = self._find_first(foco.columns, ["total_alertas"])
            c_crit = self._find_first(foco.columns, ["alertas_alta", "criticas"])
            c_foco = self._find_first(foco.columns, ["foco_principal"])

            for _, row in foco.head(10).iterrows():
                top_vendedores.append({
                    "vendedor": self._safe_text(row[c_vendedor]) if c_vendedor else "",
                    "alertas": int(self._safe_num(row[c_total])) if c_total else 0,
                    "criticas": int(self._safe_num(row[c_crit])) if c_crit else 0,
                    "foco": self._safe_text(row[c_foco]) if c_foco else "",
                })

        return {
            "fecha": self.fecha,
            "total_vendedores": total_vendedores,
            "clientes_hoy": clientes_hoy,
            "total_alertas": total_alertas,
            "criticas": criticas,
            "riesgo_ars": riesgo_ars,
            "venta_total": venta_total,
            "top_clientes": top_clientes,
            "top_vendedores": top_vendedores,
        }

    # =========================================================
    # DATA VENDEDORES
    # =========================================================
    def build_vendedores_data(self, data: Dict[str, pd.DataFrame]) -> List[Dict[str, object]]:
        foco = data["foco"].copy()
        kernel_top = data["kernel_top"].copy()

        if foco.empty:
            return []

        c_v_f = self._find_first(foco.columns, ["vendedor"])
        c_total = self._find_first(foco.columns, ["total_alertas"])
        c_crit = self._find_first(foco.columns, ["alertas_alta", "criticas"])
        c_foco = self._find_first(foco.columns, ["foco_principal"])
        c_accion = self._find_first(foco.columns, ["accion_sugerida"])

        c_v_k = self._find_first(kernel_top.columns, ["vendedor"]) if not kernel_top.empty else None
        c_cliente = self._find_first(kernel_top.columns, ["cliente_nombre", "cliente"]) if not kernel_top.empty else None
        c_localidad = self._find_first(kernel_top.columns, ["localidad"]) if not kernel_top.empty else None
        c_producto = self._find_first(kernel_top.columns, ["producto_ref", "producto"]) if not kernel_top.empty else None
        c_caida = self._find_first(kernel_top.columns, ["caida", "riesgo"]) if not kernel_top.empty else None
        c_tope = self._find_first(kernel_top.columns, ["descuento_max_ars", "descuento_ars", "tope"]) if not kernel_top.empty else None

        out = []

        for _, row in foco.iterrows():
            vendedor = self._safe_text(row[c_v_f]) if c_v_f else "SIN VENDEDOR"

            clientes = []
            if not kernel_top.empty and c_v_k:
                sub = kernel_top[kernel_top[c_v_k].astype(str).str.strip() == vendedor].copy()
                for _, r in sub.head(10).iterrows():
                    clientes.append({
                        "cliente": self._safe_text(r[c_cliente]) if c_cliente else "",
                        "localidad": self._safe_text(r[c_localidad]) if c_localidad else "",
                        "producto": self._safe_text(r[c_producto]) if c_producto else "",
                        "caida_ars": self._safe_num(r[c_caida]) if c_caida else 0.0,
                        "tope_ars": self._safe_num(r[c_tope]) if c_tope else 0.0,
                    })

            out.append({
                "vendedor": vendedor,
                "total_alertas": int(self._safe_num(row[c_total])) if c_total else 0,
                "alertas_criticas": int(self._safe_num(row[c_crit])) if c_crit else 0,
                "foco_principal": self._safe_text(row[c_foco]) if c_foco else "",
                "accion_general": self._safe_text(row[c_accion]) if c_accion else "",
                "clientes": clientes,
            })

        return out

    # =========================================================
    # BLOQUES VISUALES
    # =========================================================
    def build_kpi_cards(self, ctx: Dict[str, object]):
        cards = [
            ["Ventas detectadas", self._money(ctx["venta_total"])],
            ["Riesgo total", self._money(ctx["riesgo_ars"])],
            ["Clientes del día", str(ctx["clientes_hoy"])],
            ["Vendedores", str(ctx["total_vendedores"])],
            ["Alertas", str(ctx["total_alertas"])],
            ["Críticas", str(ctx["criticas"])],
        ]

        rows = []
        temp = []
        for label, value in cards:
            cell = Table(
                [[self._p(label, "OrbitCardLabel")], [self._p(value, "OrbitCardValue")]],
                colWidths=[55 * mm],
                rowHeights=[10 * mm, 12 * mm],
            )
            cell.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            temp.append(cell)
            if len(temp) == 3:
                rows.append(temp)
                temp = []
        if temp:
            while len(temp) < 3:
                temp.append("")
            rows.append(temp)

        table = Table(rows, colWidths=[60 * mm, 60 * mm, 60 * mm], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return table

    def build_table(self, headers: List[str], rows: List[List[object]], widths: List[float]):
        data = [[self._p(f"<b>{h}</b>", "OrbitSmall") for h in headers]]
        for r in rows:
            data.append([self._p(str(x), "OrbitSmall") for x in r])

        table = Table(data, colWidths=widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return table

    # =========================================================
    # PDF GERENCIA
    # =========================================================
    def render_gerencia_pdf(self, ctx: Dict[str, object]) -> Path:
        path = OUTPUT_DIR / "PAV_GERENCIA.pdf"

        doc = SimpleDocTemplate(
            str(path),
            pagesize=landscape(A4),
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=14 * mm,
            bottomMargin=12 * mm,
        )

        story = []
        story.append(self._p("PAV GERENCIA · ORBIT", "OrbitTitle"))
        story.append(self._p(f"Generado: {ctx['fecha']}", "OrbitSubTitle"))
        story.append(self.build_kpi_cards(ctx))
        story.append(Spacer(1, 10))

        story.append(self._p("Top clientes críticos", "OrbitSection"))
        rows = [
            [
                c["cliente"],
                c["vendedor"],
                c["localidad"],
                c["producto"],
                self._money(c["caida_ars"]),
                self._money(c["tope_ars"]),
            ]
            for c in ctx["top_clientes"]
        ]
        story.append(self.build_table(
            ["Cliente", "Vendedor", "Localidad", "Producto foco", "Caída", "Tope desc."],
            rows,
            [65 * mm, 28 * mm, 30 * mm, 60 * mm, 28 * mm, 28 * mm]
        ))
        story.append(Spacer(1, 12))

        story.append(self._p("Foco por vendedor", "OrbitSection"))
        rows2 = [
            [
                v["vendedor"],
                str(v["alertas"]),
                str(v["criticas"]),
                v["foco"],
            ]
            for v in ctx["top_vendedores"]
        ]
        story.append(self.build_table(
            ["Vendedor", "Alertas", "Críticas", "Foco"],
            rows2,
            [35 * mm, 22 * mm, 22 * mm, 160 * mm]
        ))

        doc.build(story)
        return path

    # =========================================================
    # PDF VENDEDORES
    # =========================================================
    def render_vendedor_pdf(self, vd: Dict[str, object]) -> Path:
        file_name = self._norm(vd["vendedor"])
        path = OUTPUT_DIR / "vendedores" / f"PAV_VENDEDOR_{file_name}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=14 * mm,
            bottomMargin=12 * mm,
        )

        story = []
        story.append(self._p(f"PAV VENDEDOR · {vd['vendedor']}", "OrbitTitle"))
        story.append(self._p(f"Generado: {self.fecha}", "OrbitSubTitle"))

        # Cards
        cards = [
            ["Alertas", str(vd["total_alertas"])],
            ["Críticas", str(vd["alertas_criticas"])],
            ["Clientes foco", str(len(vd["clientes"]))],
            ["Foco principal", vd["foco_principal"] or "Sin foco"],
        ]

        card_rows = []
        temp = []
        for label, value in cards:
            cell = Table(
                [[self._p(label, "OrbitCardLabel")], [self._p(value, "OrbitSmall" if label == "Foco principal" else "OrbitCardValue")]],
                colWidths=[42 * mm],
                rowHeights=[10 * mm, 14 * mm],
            )
            cell.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            temp.append(cell)
        card_table = Table([temp], colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm])
        story.append(card_table)
        story.append(Spacer(1, 10))

        action_box = Table(
            [[self._p(f"ACCIÓN GENERAL: {vd['accion_general']}", "OrbitAction")]],
            colWidths=[180 * mm],
        )
        action_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1D4ED8")),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#1E3A8A")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(action_box)
        story.append(Spacer(1, 12))

        story.append(self._p("Clientes a atacar hoy", "OrbitSection"))

        rows = [
            [
                c["cliente"],
                c["localidad"],
                c["producto"],
                self._money(c["caida_ars"]),
                self._money(c["tope_ars"]),
            ]
            for c in vd["clientes"]
        ]
        if not rows:
            rows = [["Sin clientes críticos", "-", "-", "-", "-"]]

        story.append(self.build_table(
            ["Cliente", "Localidad", "Producto foco", "Caída", "Tope desc."],
            rows,
            [55 * mm, 28 * mm, 55 * mm, 22 * mm, 25 * mm]
        ))

        doc.build(story)
        return path

    # =========================================================
    # WHATSAPP TXT
    # =========================================================
    def render_whatsapp_txt(self, vd: Dict[str, object]) -> Path:
        file_name = self._norm(vd["vendedor"])
        path = OUTPUT_DIR / "whatsapp" / f"WHATSAPP_VENDEDOR_{file_name}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append(f"VENDEDOR: {vd['vendedor']}")
        lines.append(f"FOCO: {vd['foco_principal']}")
        lines.append(f"ALERTAS CRÍTICAS: {vd['alertas_criticas']}")
        lines.append("")
        lines.append("CLIENTES PRIORITARIOS:")

        if not vd["clientes"]:
            lines.append("- Sin clientes críticos detectados hoy")
        else:
            for i, c in enumerate(vd["clientes"], start=1):
                lines.append(
                    f"{i}. {c['cliente']} | {c['localidad']} | "
                    f"Caída {self._money(c['caida_ars'])} | Tope {self._money(c['tope_ars'])}"
                )

        lines.append("")
        lines.append(f"ACCIÓN: {vd['accion_general']}")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    # =========================================================
    # RUN
    # =========================================================
    def run(self) -> Dict[str, object]:
        data = self.load_sources()
        ger = self.build_gerencia_data(data)
        vendedores = self.build_vendedores_data(data)

        ger_pdf = self.render_gerencia_pdf(ger)

        count_pdf = 0
        count_txt = 0
        for vd in vendedores:
            self.render_vendedor_pdf(vd)
            self.render_whatsapp_txt(vd)
            count_pdf += 1
            count_txt += 1

        return {
            "status": "ok",
            "fecha": self.fecha,
            "gerencia_pdf": str(ger_pdf),
            "vendedores_pdf": count_pdf,
            "whatsapp_txt": count_txt,
        }


if __name__ == "__main__":
    result = OrbitPavPdf().run()
    print(result)