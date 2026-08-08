"""
Test del catálogo del Explorador de Acciones Comerciales.

Cubre el motor `generar_datasets_acum.generar_acciones_explorador()` (Excel mensual ->
04_DATASETS_ORBIT/mod_acciones_explorador.json) y el loader `server_orbit._acc_explorador()`.

Trabaja SIEMPRE sobre libros sintéticos en carpetas temporales: redirige
generar_datasets_acum.BASE a un tmpdir, así que no toca 01_INPUTS ni los datasets reales.
Un solo caso lee el Excel productivo, y sólo para leerlo (nunca lo escribe).

Ejecutar:  python test_acciones_explorador.py
"""
from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import generar_datasets_acum as g

REAL_BASE = Path(__file__).parent


def _hoja(rows, titulo):
    """Replica el formato del libro real: fila 1 de portada, fila 2 encabezado, luego datos."""
    ancho = max(len(r) for r in rows)
    filas = [[titulo] + [None] * (ancho - 1)] + [list(r) + [None] * (ancho - len(r)) for r in rows]
    return pd.DataFrame(filas)


def _libro(path, acciones=None, escalas=None, productos=None, exclusiones=None,
           validaciones=None, leeme=None, omitir=()):
    """Escribe un libro sintético con la estructura del Excel de acciones."""
    hojas = {
        "LEEME": _hoja(leeme or [
            ["Orden", "Tema", "Definición para Claude / Orbit"],
            [1, "Vigencia", "2026-08-01 a 2026-08-31. No mezclar con acciones de julio."],
        ], "ACCIONES COMERCIALES"),
        "ACCIONES": _hoja(acciones or [
            ["action_id", "categoria_ui", "subcategoria_ui", "mecanica", "grupo_ui", "estado", "resumen"],
            ["X-VDA-SUP", "VDA", "Superior", "Drop por volumen", "Vinos", "Activa", "Escalas por canal."],
            ["X-VDA-RES", "VDA", "Resto", "Drop por volumen", "Vinos", "Activa", "Otra línea."],
            ["X-ESP", "Espumantes", "Espumante / Sidra", "Drop fijo", "Espumantes", "Activa", "Canal único."],
        ], "CATÁLOGO"),
        "ESCALAS": _hoja(escalas or [
            ["action_id", "canal_regla", "segmentos_cliente", "unidad", "min_inclusivo",
             "max_inclusivo", "descuento", "tipo_beneficio", "texto_vendedor", "observacion"],
            ["X-VDA-SUP", "Autoservicios", "Autoservicios", "caja", 1, 9, 0.04, "descuento", "1 a 9 cajas · 4%", None],
            ["X-VDA-SUP", "Autoservicios", "Autoservicios", "caja", 10, 20, 0.06, "descuento", "10 a 20 cajas · 6%", "Ver VALIDACIONES."],
            ["X-VDA-SUP", "Autoservicios", "Autoservicios", "caja", 20, None, 0.08, "descuento", "20 cajas o más · 8%", None],
            ["X-VDA-SUP", "Tradicional", "Tradicional | Kiosco", "caja", 0, 3, 0.04, "descuento", "0 a 3 cajas · 4%", None],
            ["X-VDA-RES", "Autoservicios", "Autoservicios", "caja", 1, None, 0.06, "descuento", "1 caja o más · 6%", None],
            ["X-ESP", "General", "Autoservicios | Kioscos", "caja", 1, None, 0.04, "descuento",
             "1 caja o más · 4%", "Tope: 200 cajas."],
        ], "ESCALAS"),
        "PRODUCTOS_Y_LINEAS": _hoja(productos or [
            ["action_id", "tipo", "nombre_visible", "regla_asociada", "observacion"],
            ["X-VDA-SUP", "línea", "VDA Superior", "Resolver SKU desde maestro", "Fuente no enumera marcas."],
            ["X-ESP", "línea", "Espumante / Sidra", "Resolver SKU desde maestro", None],
        ], "PRODUCTOS"),
        "EXCLUSIONES": _hoja(exclusiones or [
            ["action_id", "categoria_excluida", "tratamiento"],
            ["X-VDA-SUP", "Vinos de Mesa", "Sin descuento"],
        ], "EXCLUSIONES"),
        "VALIDACIONES": _hoja(validaciones or [
            ["severidad", "tema", "hallazgo", "acción requerida"],
            ["ALTA", "Escalas AS de 20 cajas", "La fuente escribe “10 a 20” y “20 o más”.", "Pedir definición."],
        ], "VALIDACIONES"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path) as w:
        for nombre, df in hojas.items():
            if nombre in omitir:
                continue
            df.to_excel(w, sheet_name=nombre, index=False, header=False)


class _BaseTmp(unittest.TestCase):
    """Redirige generar_datasets_acum.BASE a un tmpdir: los inputs reales quedan intactos."""

    MES = "2026-08"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit_accx_"))
        self._base_orig = g.BASE
        g.BASE = self.tmp
        self.mdir = self.tmp / "01_INPUTS" / "ACCIONES COMERCIALES" / self.MES
        self.xlsx = self.mdir / "ORBIT_Acciones_Comerciales_Agosto_2026.xlsx"

    def tearDown(self):
        g.BASE = self._base_orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cat(self, nombre, catalogo):
        return next((c for c in catalogo["categorias"] if c["categoria"] == nombre), None)

    def sub(self, catalogo, cat, sub):
        c = self.cat(cat, catalogo)
        return next((s for s in c["subcategorias"] if s["subcategoria"] == sub), None)


class LecturaDelExcel(_BaseTmp):

    def test_categorias_y_subcategorias(self):
        _libro(self.xlsx)
        c = g.generar_acciones_explorador()
        self.assertIsNone(c["nota"])
        self.assertEqual(c["mes"], self.MES)
        self.assertEqual([x["categoria"] for x in c["categorias"]], ["Espumantes", "VDA"])
        vda = self.cat("VDA", c)
        self.assertEqual(sorted(s["subcategoria"] for s in vda["subcategorias"]),
                         ["Resto", "Superior"])

    def test_vigencia_sale_del_leeme_no_cableada(self):
        _libro(self.xlsx, leeme=[["Orden", "Tema", "Definición para Claude / Orbit"],
                                 [1, "Vigencia", "2026-09-01 a 2026-09-30."]])
        self.assertEqual(g.generar_acciones_explorador()["vigencia"], "2026-09-01 a 2026-09-30.")

    def test_escalas_drops_y_unidades(self):
        _libro(self.xlsx)
        sup = self.sub(g.generar_acciones_explorador(), "VDA", "Superior")
        aut = next(s for s in sup["segmentos"] if s["canal"] == "Autoservicios")
        self.assertEqual([(e["min"], e["max"], e["descuento"]) for e in aut["escalas"]],
                         [(1, 9, 0.04), (10, 20, 0.06), (20, None, 0.08)])
        # enteros, no 10.0 — el portal los muestra tal cual
        self.assertIsInstance(aut["escalas"][0]["min"], int)
        self.assertEqual(aut["escalas"][0]["unidad"], "caja")

    def test_segmentos_por_accion(self):
        _libro(self.xlsx)
        c = g.generar_acciones_explorador()
        sup = self.sub(c, "VDA", "Superior")
        self.assertEqual(sorted(s["canal"] for s in sup["segmentos"]), ["Autoservicios", "Tradicional"])
        trad = next(s for s in sup["segmentos"] if s["canal"] == "Tradicional")
        self.assertEqual(trad["segmentos_cliente"], ["Tradicional", "Kiosco"])
        # el selector 3 sólo puede ofrecer canales de ESTA acción
        res = self.sub(c, "VDA", "Resto")
        self.assertEqual([s["canal"] for s in res["segmentos"]], ["Autoservicios"])

    def test_productos_y_exclusiones(self):
        _libro(self.xlsx)
        sup = self.sub(g.generar_acciones_explorador(), "VDA", "Superior")
        self.assertEqual([p["nombre"] for p in sup["productos"]], ["VDA Superior"])
        self.assertEqual(sup["exclusiones"], [{"categoria": "Vinos de Mesa",
                                               "tratamiento": "Sin descuento"}])

    def test_accion_sin_productos_declarados(self):
        _libro(self.xlsx)
        res = self.sub(g.generar_acciones_explorador(), "VDA", "Resto")
        self.assertEqual(res["productos"], [])     # la UI muestra "No se encontraron productos"
        self.assertEqual(res["exclusiones"], [])

    def test_tope_se_separa_de_la_observacion(self):
        _libro(self.xlsx)
        esp = self.sub(g.generar_acciones_explorador(), "Espumantes", "Espumante / Sidra")
        e = esp["segmentos"][0]["escalas"][0]
        self.assertEqual(e["tope"], "Tope: 200 cajas.")
        self.assertIsNone(e["observacion"])

    def test_categoria_con_una_sola_subcategoria(self):
        _libro(self.xlsx)
        esp = self.cat("Espumantes", g.generar_acciones_explorador())
        self.assertEqual(len(esp["subcategorias"]), 1)   # el portal oculta el selector 2

    def test_avisos_de_validaciones_viajan_sin_interpretar(self):
        _libro(self.xlsx)
        av = g.generar_acciones_explorador()["avisos"]
        self.assertEqual(len(av), 1)
        self.assertEqual(av[0]["severidad"], "ALTA")
        self.assertIn("10 a 20", av[0]["hallazgo"])


class Solapamientos(_BaseTmp):
    """El punto que NO se debe resolver por interpretación."""

    def test_detecta_solape_sin_elegir_ganadora(self):
        _libro(self.xlsx)
        c = g.generar_acciones_explorador()
        sup = self.sub(c, "VDA", "Superior")
        self.assertEqual(len(sup["conflictos"]), 1)
        self.assertIn("se pisan en 20", sup["conflictos"][0])
        aut = next(s for s in sup["segmentos"] if s["canal"] == "Autoservicios")
        marcadas = [e for e in aut["escalas"] if e["solapa"]]
        # las DOS escalas en conflicto quedan marcadas: ninguna se descarta
        self.assertEqual(sorted(e["descuento"] for e in marcadas), [0.06, 0.08])
        self.assertTrue(all(e["descuento"] in (0.06, 0.08) for e in marcadas))
        self.assertEqual(len(aut["escalas"]), 3)    # no se eliminó ninguna

    def test_escalas_contiguas_no_son_solape(self):
        _libro(self.xlsx, escalas=[
            ["action_id", "canal_regla", "segmentos_cliente", "unidad", "min_inclusivo",
             "max_inclusivo", "descuento", "tipo_beneficio", "texto_vendedor", "observacion"],
            ["X-VDA-SUP", "Autoservicios", "Autoservicios", "caja", 1, 9, 0.04, "descuento", "1 a 9", None],
            ["X-VDA-SUP", "Autoservicios", "Autoservicios", "caja", 10, 19, 0.06, "descuento", "10 a 19", None],
            ["X-VDA-SUP", "Autoservicios", "Autoservicios", "caja", 20, None, 0.08, "descuento", "20+", None],
        ])
        c = g.generar_acciones_explorador()
        self.assertEqual(self.sub(c, "VDA", "Superior")["conflictos"], [])
        self.assertEqual(c["conflictos"], [])

    def test_tramo_abierto_no_dispara_falso_positivo(self):
        _libro(self.xlsx, escalas=[
            ["action_id", "canal_regla", "segmentos_cliente", "unidad", "min_inclusivo",
             "max_inclusivo", "descuento", "tipo_beneficio", "texto_vendedor", "observacion"],
            ["X-VDA-SUP", "Autoservicios", "Autoservicios", "caja", 1, None, 0.04, "descuento", "1+", None],
        ])
        self.assertEqual(g.generar_acciones_explorador()["conflictos"], [])


class DatosIncompletosYAusencias(_BaseTmp):
    """Nada de esto puede voltear el cierre ni la pantalla."""

    def test_sin_carpeta_del_mes(self):
        c = g.generar_acciones_explorador()
        self.assertEqual(c["categorias"], [])
        self.assertIn("ACCIONES COMERCIALES", c["nota"])

    def test_carpeta_sin_excel(self):
        self.mdir.mkdir(parents=True, exist_ok=True)
        c = g.generar_acciones_explorador()
        self.assertEqual(c["categorias"], [])
        self.assertIn("xlsx", c["nota"])
        self.assertEqual(c["mes"], self.MES)

    def test_excel_sin_hoja_escalas(self):
        _libro(self.xlsx, omitir=("ESCALAS",))
        c = g.generar_acciones_explorador()
        self.assertEqual(c["categorias"], [])
        self.assertIn("ACCIONES y ESCALAS", c["nota"])

    def test_hojas_opcionales_ausentes_no_rompen(self):
        _libro(self.xlsx, omitir=("EXCLUSIONES", "VALIDACIONES", "PRODUCTOS_Y_LINEAS", "LEEME"))
        c = g.generar_acciones_explorador()
        self.assertIsNone(c["nota"])
        self.assertTrue(c["categorias"])
        self.assertEqual(c["avisos"], [])
        self.assertIsNone(c["vigencia"])
        self.assertEqual(self.sub(c, "VDA", "Superior")["productos"], [])

    def test_filas_vacias_y_action_id_en_blanco_se_ignoran(self):
        _libro(self.xlsx, acciones=[
            ["action_id", "categoria_ui", "subcategoria_ui", "mecanica", "grupo_ui", "estado", "resumen"],
            ["X-VDA-SUP", "VDA", "Superior", None, None, None, None],
            [None, "VDA", "Fantasma", None, None, None, None],
        ])
        c = g.generar_acciones_explorador()
        vda = self.cat("VDA", c)
        self.assertEqual([s["subcategoria"] for s in vda["subcategorias"]], ["Superior"])
        self.assertIsNone(vda["subcategorias"][0]["mecanica"])   # None, no el string "nan"

    def test_accion_declarada_sin_escalas_se_conserva(self):
        """Acción que el libro declara pero para la que no cargaron ninguna escala.

        NO se filtra del catálogo: es un hueco del Excel y esconderlo haría que la acción
        desapareciera en silencio de la pantalla sin que nadie se entere de que falta cargarla
        (mismo criterio que SIN_CARTERA en el 11T). Queda con `segmentos` vacío y el portal
        muestra "No hay una acción disponible para esta combinación"."""
        _libro(self.xlsx, escalas=[
            ["action_id", "canal_regla", "segmentos_cliente", "unidad", "min_inclusivo",
             "max_inclusivo", "descuento", "tipo_beneficio", "texto_vendedor", "observacion"],
            ["X-VDA-SUP", "Autoservicios", "Autoservicios", "caja", 1, None, 0.04, "descuento", "1+", None],
        ])
        c = g.generar_acciones_explorador()
        self.assertEqual(self.sub(c, "VDA", "Resto")["segmentos"], [])
        esp = self.cat("Espumantes", c)
        self.assertIsNotNone(esp)
        self.assertEqual(esp["subcategorias"][0]["segmentos"], [])

    def test_mes_futuro_no_se_adelanta(self):
        _libro(self.xlsx)
        futuro = self.tmp / "01_INPUTS" / "ACCIONES COMERCIALES" / "2099-01"
        _libro(futuro / "ORBIT_Acciones_Comerciales_Futuro.xlsx")
        self.assertEqual(g.generar_acciones_explorador()["mes"], self.MES)


class Determinismo(_BaseTmp):

    def test_dos_corridas_producen_el_mismo_json(self):
        _libro(self.xlsx)
        a = json.dumps(g.generar_acciones_explorador(), ensure_ascii=False, sort_keys=True)
        b = json.dumps(g.generar_acciones_explorador(), ensure_ascii=False, sort_keys=True)
        self.assertEqual(a, b)
        self.assertNotIn("generado_en", a)   # sin timestamp: el cierre diario no ensucia el repo


class ExcelRealDeAgosto(unittest.TestCase):
    """Contrato contra el libro productivo. Sólo lectura."""

    @classmethod
    def setUpClass(cls):
        cls.cat = g.generar_acciones_explorador()

    def test_carga_el_libro_real(self):
        if self.cat.get("nota"):
            self.skipTest(f"sin libro del mes en el repo: {self.cat['nota']}")
        self.assertTrue(self.cat["categorias"])
        self.assertIn("VDA", [c["categoria"] for c in self.cat["categorias"]])

    def test_reporta_los_solapamientos_de_agosto(self):
        if self.cat.get("nota") or self.cat.get("mes") != "2026-08":
            self.skipTest("el mes vigente ya no es agosto 2026")
        # Los tres tramos "10 a 20 / 20 o más" de Autoservicios (VDA Superior, VDA Resto, VDG
        # Premium y VDG Super) que la hoja VALIDACIONES marca como ALTA.
        self.assertTrue(self.cat["conflictos"], "deberían detectarse los solapes de 20 cajas")
        self.assertTrue(all("se pisan en 20" in c for c in self.cat["conflictos"]))
        altas = [a for a in self.cat["avisos"] if a["severidad"] == "ALTA"]
        temas = " ".join(a["tema"] for a in altas)
        self.assertIn("20 cajas", temas)
        self.assertIn("+5 bultos", temas)   # la otra ambigüedad que no se resuelve sola


class LoaderDelServidor(unittest.TestCase):
    """server_orbit._acc_explorador() nunca puede lanzar: la pantalla degrada con nota."""

    def setUp(self):
        import server_orbit
        self.srv = server_orbit
        self._orig = server_orbit.DATASETS
        self.tmp = Path(tempfile.mkdtemp(prefix="orbit_accx_srv_"))
        server_orbit.DATASETS = self.tmp

    def tearDown(self):
        self.srv.DATASETS = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sin_catalogo(self):
        r = self.srv._acc_explorador()
        self.assertEqual(r["categorias"], [])
        self.assertIn("No se cargaron", r["nota"])

    def test_json_corrupto(self):
        (self.tmp / "mod_acciones_explorador.json").write_text("{roto", encoding="utf-8")
        r = self.srv._acc_explorador()
        self.assertEqual(r["categorias"], [])
        self.assertIn("no se pudo leer", r["nota"])

    def test_catalogo_vacio_conserva_la_nota_del_generador(self):
        (self.tmp / "mod_acciones_explorador.json").write_text(
            json.dumps({"mes": "2026-08", "fuente": None, "categorias": [],
                        "nota": "No hay libro .xlsx de acciones en 2026-08."}), encoding="utf-8")
        r = self.srv._acc_explorador()
        self.assertEqual(r["mes"], "2026-08")
        self.assertIn("No hay libro", r["nota"])

    def test_catalogo_bueno_pasa_completo(self):
        payload = {"mes": "2026-08", "fuente": "x.xlsx", "vigencia": "ago",
                   "categorias": [{"categoria": "VDA", "subcategorias": []}],
                   "avisos": [], "conflictos": [], "nota": None}
        (self.tmp / "mod_acciones_explorador.json").write_text(
            json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.srv._acc_explorador(), payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
