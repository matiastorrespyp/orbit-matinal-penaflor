from pathlib import Path
import pandas as pd
import shutil
from datetime import datetime


class OrbitPavRenderer:

    def __init__(self):
        self.base = Path(__file__).resolve().parents[3]

        self.ccc = self.base / "04_DATASETS_ORBIT" / "mod_ccc_segmento.csv"
        self.t11 = self.base / "04_DATASETS_ORBIT" / "mod_11_titulares.csv"
        self.vol = self.base / "04_DATASETS_ORBIT" / "mod_volumen_vendedor.csv"
        self.alertas = self.base / "05_INTELLIGENCE_ORBIT" / "alertas_reales.csv"
        self.foco = self.base / "05_INTELLIGENCE_ORBIT" / "orbit_foco_vendedor.csv"
        self.inv = self.base / "04_DATASETS_ORBIT" / "mod_inversion_desc.csv"
        self.eff = self.base / "04_DATASETS_ORBIT" / "mod_eficiencia_desc.csv"
        self.rein = self.base / "04_DATASETS_ORBIT" / "mod_reintegros_ctrl.csv"
        self.vendedores_csv = self.base / "09_CONFIG" / "vendedores_activos.csv"

        self.out_vend = self.base / "07_PAV_OUTPUT" / "vendedores"
        self.out_ger = self.base / "07_PAV_OUTPUT" / "gerencia"

    def limpiar(self):
        for d in [self.out_vend, self.out_ger]:
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)

    def nv(self, v):
        s = str(v).upper().replace("V", "")
        n = "".join(filter(str.isdigit, s))
        return f"V{int(n)}" if n else ""

    def load(self):
        def read(p):
            try:
                return pd.read_csv(p)
            except:
                return pd.read_csv(p, encoding="latin1")

        ccc = read(self.ccc)
        t11 = read(self.t11)
        vol = read(self.vol)
        alertas = read(self.alertas)
        foco = read(self.foco)

        vend = read(self.vendedores_csv)
        vend = vend[vend["activo"] == 1]
        vend["codigo_vendedor"] = vend["codigo_vendedor"].apply(self.nv)

        for df, col in [(ccc, "vendedor_codigo"), (t11, "vendedor_codigo"), (vol, "vendedor_codigo")]:
            if col in df.columns:
                df[col] = df[col].apply(self.nv)

        alertas["vendedor"] = alertas["vendedor"].apply(self.nv)
        if "vendedor" in foco.columns:
            foco["vendedor"] = foco["vendedor"].apply(self.nv)

        inv, eff, rein = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        for path, nombre in [(self.inv, "inv"), (self.eff, "eff"), (self.rein, "rein")]:
            if path.exists():
                try:
                    df_temp = read(path)
                    if "vendedor_codigo" in df_temp.columns:
                        df_temp["vendedor_codigo"] = df_temp["vendedor_codigo"].apply(self.nv)
                    if nombre == "inv":
                        inv = df_temp
                    elif nombre == "eff":
                        eff = df_temp
                    else:
                        rein = df_temp
                except:
                    pass

        return ccc, t11, vol, alertas, foco, inv, eff, rein, vend

    def build_prioridad_clientes(self, t11_v, alertas_v):
        base = {}
        if "falta_flag" in t11_v.columns:
            falt = t11_v[t11_v["falta_flag"] == 1]
        else:
            falt = pd.DataFrame()

        for _, r in falt.iterrows():
            cid = str(r["cliente_id"])
            base.setdefault(cid, {"cliente": r.get("cliente_nombre", ""), "motivos": set(), "faltantes": set(), "score": 0})
            base[cid]["faltantes"].add(str(r.get("marca_objetivo", "")))
            base[cid]["motivos"].add("Falta 11T")
            base[cid]["score"] += 1

        for _, r in alertas_v.iterrows():
            cid = str(r.get("cliente_id", ""))
            if not cid:
                continue
            base.setdefault(cid, {"cliente": r.get("cliente_nombre", ""), "motivos": set(), "faltantes": set(), "score": 0})
            tipo = str(r.get("tipo_alerta", ""))
            base[cid]["motivos"].add(tipo)
            if "caida" in tipo.lower():
                base[cid]["score"] += 7
            elif "sin_compra" in tipo.lower():
                base[cid]["score"] += 6
            else:
                base[cid]["score"] += 3

        df = pd.DataFrame([
            {
                "cliente_id": k,
                "cliente": v["cliente"],
                "motivos": " | ".join(sorted(v["motivos"])),
                "faltantes": ", ".join(sorted(v["faltantes"])),
                "score": v["score"]
            }
            for k, v in base.items()
        ])

        return df.sort_values(by="score", ascending=False) if not df.empty else df

    def estilo_base(self):
        return """
        <style>
          :root {
            --bg: #0A0D12; --surface: #11161E; --text: #E7ECF3; --text2: #AAB3C0;
            --magenta: #E2147A; --magenta-glow: rgba(226,20,122,0.45);
            --ok: #2EC27E; --warn: #F2B544; --bad: #FF5D5D; --info: #4DA3FF;
          }
          * { margin:0; padding:0; box-sizing:border-box; }
          body {
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--bg); color: var(--text);
            padding: 24px; min-height: 100vh;
          }
          h2 {
            font-family: 'Sora', sans-serif; font-size: 22px; margin-bottom: 4px;
          }
          h3 { font-family: 'Sora', sans-serif; font-size: 14px; color: var(--text2); margin: 20px 0 10px; }
          .sub { color: var(--text2); font-size: 13px; margin-bottom: 16px; }
          .cards {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px; margin-bottom: 20px;
          }
          .kpi-card {
            background: var(--surface); border-radius: 14px; padding: 16px;
            border: 1px solid rgba(255,255,255,0.05);
            box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset;
          }
          .kpi-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1.2px; color: var(--text2); margin-bottom: 6px; }
          .kpi-value { font-family: 'Sora', sans-serif; font-size: 24px; font-weight: 700; }
          .kpi-unit { font-size: 12px; color: var(--text2); margin-left: 4px; }
          .kpi-delta { font-size: 11.5px; margin-top: 6px; display: flex; align-items: center; gap: 4px; }
          .kpi-delta.up { color: var(--ok); }
          .kpi-delta.down { color: var(--bad); }
          .bar-bg { height: 8px; background: rgba(255,255,255,0.06); border-radius: 99px; margin-top: 8px; overflow: hidden; }
          .bar-fill { height: 100%; border-radius: 99px; background: var(--magenta); box-shadow: 0 0 10px var(--magenta-glow); }
          .bar-fill.ok { background: var(--ok); box-shadow: 0 0 10px rgba(46,194,126,0.5); }
          .bar-fill.warn { background: var(--warn); box-shadow: 0 0 10px rgba(242,181,68,0.5); }
          .bar-fill.bad { background: var(--bad); box-shadow: 0 0 10px rgba(255,93,93,0.5); }
          table { width: 100%; border-collapse: collapse; font-size: 13px; }
          th { text-align: left; padding: 10px 12px; background: var(--surface); color: var(--text2); font-size: 10px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid rgba(255,255,255,0.06); }
          td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }
          tr:hover td { background: rgba(255,255,255,0.02); }
          .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; }
          .badge-critical { background: rgba(255,93,93,0.15); color: var(--bad); }
          .badge-warning { background: rgba(242,181,68,0.15); color: var(--warn); }
          .badge-info { background: rgba(77,163,255,0.15); color: var(--info); }
          .footer { margin-top: 30px; text-align: center; color: var(--text2); font-size: 11px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 14px; }
        </style>
        """

    def render_kpi_card(self, label, value, unit="", kind="", delta=None):
        cls = f'kpi-card {kind}' if kind else 'kpi-card'
        delta_html = ""
        if delta is not None:
            d_val = delta
            arrow = "\u2191" if d_val >= 0 else "\u2193"
            d_class = "up" if d_val >= 0 else "down"
            delta_html = f'<div class="kpi-delta {d_class}">{arrow} {abs(d_val):.1f}%</div>'
        return f'''
        <div class="{cls}">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}<span class="kpi-unit">{unit}</span></div>
          {delta_html}
        </div>'''

    def render_bar(self, pct, kind=""):
        cls = f'bar-fill {kind}' if kind else 'bar-fill'
        return f'<div class="bar-bg"><div class="{cls}" style="width:{min(pct,100)}%"></div></div>'

    def render_vendedor_html(self, cod, nombre, vol_v, ccc_v, t11_v, alertas_v, inv_v, eff_v, rein_v):
        objetivo = int(vol_v["objetivo_mes"].sum())
        acumulado = int(vol_v["acumulado_mes"].sum())
        avance = float(vol_v["avance_pct"].mean())
        real_ayer = int(vol_v["venta_ayer"].sum())
        tendencia = float(vol_v["tendencia_mes"].mean()) if "tendencia_mes" in vol_v.columns else 0.0

        ccc_total = int(ccc_v["ccc_mes"].sum()) if not ccc_v.empty and "ccc_mes" in ccc_v.columns else 0
        t11_cumplidos = int((~t11_v["falta_flag"].astype(bool)).sum()) if not t11_v.empty and "falta_flag" in t11_v.columns else 0
        t11_total = len(t11_v)

        inversion = int(inv_v["inversion_total"].sum()) if not inv_v.empty else 0
        rein_pend = int(len(rein_v[rein_v["estado_reintegro"] != "OK"])) if not rein_v.empty and "estado_reintegro" in rein_v.columns else 0
        eff_mala = int(len(eff_v[eff_v["estado_eficiencia"] == "INEFICIENTE"])) if not eff_v.empty and "estado_eficiencia" in eff_v.columns else 0

        avance_kind = "ok" if avance >= 100 else ("warn" if avance >= 60 else "bad")

        clientes_foco = self.build_prioridad_clientes(t11_v, alertas_v)

        html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
{self.estilo_base()}
</head>
<body>
<h2>{cod} · {nombre}</h2>
<div class="sub">Reporte matinal · {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>

<div class="cards">
  {self.render_kpi_card("OBJETIVO MENSUAL", f"${objetivo:,}", "", "", None)}
  {self.render_kpi_card("ACUMULADO", f"${acumulado:,}", "")}
  {self.render_kpi_card("AVANCE", f"{avance:.1f}", "%", avance_kind, None)}
  {self.render_kpi_card("REAL AYER", f"${real_ayer:,}", "")}
  {self.render_kpi_card("TENDENCIA", f"${tendencia:,.0f}", "")}
  {self.render_kpi_card("CCC MES", str(ccc_total))}
  {self.render_kpi_card("11T CUMPLIDOS", f"{t11_cumplidos}/{t11_total}")}
</div>

{self.render_bar(avance, avance_kind)}

<h3>Inversión y riesgos</h3>
<div class="cards">
  {self.render_kpi_card("INVERSIÓN TOTAL", f"${inversion:,}")}
  {self.render_kpi_card("REINTEGROS PEND.", str(rein_pend))}
  {self.render_kpi_card("DESC. INEFICIENTES", str(eff_mala))}
</div>

<h3>Clientes foco ({len(clientes_foco)})</h3>
<table>
<tr><th>ID</th><th>Cliente</th><th>Motivos</th><th>Faltantes 11T</th><th>Prioridad</th></tr>
"""
        for _, r in clientes_foco.head(20).iterrows():
            score = int(r["score"])
            badge = "badge-critical" if score >= 10 else ("badge-warning" if score >= 5 else "badge-info")
            html += f"""<tr>
<td>{r['cliente_id']}</td>
<td>{r['cliente']}</td>
<td>{r['motivos']}</td>
<td>{r['faltantes']}</td>
<td><span class="badge {badge}">{score}</span></td>
</tr>"""

        html += """</table>
<div class="footer">ORBIT © 2026 · Propiedad de Torres Matías</div>
</body></html>"""
        return html

    def render_gerencia_html(self, vend, vol, ccc, t11):
        rows = []
        for _, v in vend.iterrows():
            cod = v["codigo_vendedor"]
            nombre = v["nombre_vendedor"]
            vv = vol[vol["vendedor_codigo"] == cod]
            obj = int(vv["objetivo_mes"].sum())
            acum = int(vv["acumulado_mes"].sum())
            av = float(vv["avance_pct"].mean())
            kind = "ok" if av >= 100 else ("warn" if av >= 60 else "bad")
            rows.append((cod, nombre, obj, acum, av, kind))

        rows.sort(key=lambda x: x[4], reverse=True)

        tarjetas = ""
        for cod, nombre, obj, acum, av, kind in rows:
            tarjetas += f"""
            <div class="kpi-card {kind}">
              <div class="kpi-label">{cod} · {nombre}</div>
              <div class="kpi-value">{av:.1f}<span class="kpi-unit">%</span></div>
              <div style="font-size:11px; color:var(--text2); margin-top:4px;">${acum:,} / ${obj:,}</div>
              {self.render_bar(av, kind)}
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
{self.estilo_base()}
</head>
<body>
<h2>ORBIT · Resumen Gerencial</h2>
<div class="sub">Peñaflor PAV · {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>

<h3>Ranking de vendedores</h3>
<div class="cards" style="grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));">
{tarjetas}
</div>

<div class="footer">ORBIT © 2026 · Propiedad de Torres Matías</div>
</body></html>"""
        return html

    def run(self):
        self.limpiar()
        ccc, t11, vol, alertas, foco, inv, eff, rein, vend = self.load()

        for _, v in vend.iterrows():
            cod = v["codigo_vendedor"]
            nombre = v["nombre_vendedor"]
            ccc_v = ccc[ccc["vendedor_codigo"] == cod] if not ccc.empty else pd.DataFrame()
            t11_v = t11[t11["vendedor_codigo"] == cod] if not t11.empty else pd.DataFrame()
            vol_v = vol[vol["vendedor_codigo"] == cod] if not vol.empty else pd.DataFrame()
            a_v = alertas[alertas["vendedor"] == cod] if not alertas.empty else pd.DataFrame()
            inv_v = inv[inv["vendedor_codigo"] == cod] if not inv.empty else pd.DataFrame()
            eff_v = eff[eff["vendedor_codigo"] == cod] if not eff.empty else pd.DataFrame()
            rein_v = rein[rein["vendedor_codigo"] == cod] if not rein.empty else pd.DataFrame()

            html_vend = self.render_vendedor_html(cod, nombre, vol_v, ccc_v, t11_v, a_v, inv_v, eff_v, rein_v)
            (self.out_vend / f"{cod}.html").write_text(html_vend, encoding="utf-8")

        html_ger = self.render_gerencia_html(vend, vol, ccc, t11)
        (self.out_ger / "PAV_GERENCIA.html").write_text(html_ger, encoding="utf-8")

        print("PAV PREMIUM FINAL GENERADO · 7 vendedores + gerencia")


if __name__ == "__main__":
    OrbitPavRenderer().run()