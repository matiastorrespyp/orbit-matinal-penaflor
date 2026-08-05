# -*- coding: utf-8 -*-
"""
Tests del motor autoritativo de 11 Titulares (motor_11t.py).

Cubre la regla de cobertura (mínimo 3 trad / 6 AS aplicado DESPUÉS de consolidar), el
match por SKU contra la matriz oficial, el recorte de período, las exclusiones y la
regresión histórica de Gordon's Flavours julio-2026 (25 trad + 7 AS = 32).

La regresión CALCULA el resultado desde `01_INPUTS/cierres mes/ventas_acumulada_072026.csv`;
no hay ninguna lista de códigos hardcodeada haciendo de sustituto del cálculo.

Ejecutar:  python -m unittest test_motor_11t
"""
from __future__ import annotations

import unittest

import pandas as pd

import motor_11t as m

# ── SKU sintéticos para los tests unitarios ──────────────────────────────────
MATRIZ_FAKE = pd.DataFrame([
    {"codigo_articulo": 30134, "titular": "GORDON'S FLAVOURS", "descripcion": "PINK GIN"},
    {"codigo_articulo": 30139, "titular": "GORDON'S FLAVOURS", "descripcion": "TROPICAL FRUITS"},
    {"codigo_articulo": 74400, "titular": "ALMA MORA", "descripcion": "ALMA MORA MALBEC"},
])
# 30075 (Gordon's Gin) y 35107 (Gordon's Tonic) NO están en la matriz: comparten la
# palabra "GORDON" pero no pertenecen al titular Gordon's Flavours.

PADRON_FAKE = pd.DataFrame([
    {"cliente_id": 1, "cliente_nombre": "ALMACEN UNO", "vendedor_codigo": 8,
     "vendedor_nombre": "V8", "ramo": "TRADITIONAL TRADE", "subsegmento": "Almacen/Despensa",
     "segmento_11t": "TRADICIONAL", "duplicado_padron": False},
    {"cliente_id": 2, "cliente_nombre": "AUTOSERVICIO DOS", "vendedor_codigo": 8,
     "vendedor_nombre": "V8", "ramo": "TRADITIONAL TRADE", "subsegmento": "Autoservicio Tradicional",
     "segmento_11t": "AUTOSERVICIO", "duplicado_padron": False},
    {"cliente_id": 3, "cliente_nombre": "KIOSCO TRES", "vendedor_codigo": 9,
     "vendedor_nombre": "V9", "ramo": "TRADITIONAL TRADE", "subsegmento": "Kiosco/Maxikiosco",
     "segmento_11t": "TRADICIONAL", "duplicado_padron": False},
    {"cliente_id": 9, "cliente_nombre": "CLIENTE DE V20", "vendedor_codigo": 20,
     "vendedor_nombre": "DEPOSITO", "ramo": "TRADITIONAL TRADE", "subsegmento": "Almacen/Despensa",
     "segmento_11t": "TRADICIONAL", "duplicado_padron": False},
    {"cliente_id": 10, "cliente_nombre": "VINOTECA DIEZ", "vendedor_codigo": 8,
     "vendedor_nombre": "V8", "ramo": "AWAY FROM HOME", "subsegmento": "Vinoteca",
     "segmento_11t": m.FUERA_DE_SUPERFICIE, "duplicado_padron": False},
])


def _ventas(filas):
    """filas: (cliente, codigo, cantbase, neto, fecha, nro_comprobante, marca, articulo)."""
    return pd.DataFrame([{
        "Cliente": c, "Codigo": cod, "CantBase": cant, "ImporteNetoItem": neto,
        "FechaComprobante": fecha, "NroComprobante": nro, "Marca": marca, "Articulo": art,
    } for c, cod, cant, neto, fecha, nro, marca, art in filas])


def _run(filas, **kw):
    kw.setdefault("clientes", PADRON_FAKE)
    kw.setdefault("matriz", MATRIZ_FAKE)
    return m.cobertura_11t(_ventas(filas), **kw)


def _cumple(det, cliente, titular="GORDON'S FLAVOURS"):
    f = det[(det["cliente_id"] == cliente) & (det["titular"] == titular)]
    return bool(f["cumple"].iloc[0]) if len(f) else False


G = "Gordon's Flavors"


class MinimosPorSegmento(unittest.TestCase):
    """El mínimo se aplica por segmento y DESPUÉS de consolidar."""

    def test_tradicional_3_botellas_cumple(self):
        det, _ = _run([(1, 30134, 3, 1000, "05/07/2026", "FAC-1", G, "PINK GIN")])
        self.assertTrue(_cumple(det, 1))

    def test_tradicional_2_botellas_no_cumple(self):
        det, _ = _run([(1, 30134, 2, 900, "05/07/2026", "FAC-1", G, "PINK GIN")])
        self.assertFalse(_cumple(det, 1))
        self.assertIn("no cubre", det["motivo"].iloc[0])

    def test_autoservicio_6_botellas_cumple(self):
        det, _ = _run([(2, 30134, 6, 2000, "05/07/2026", "FAC-1", G, "PINK GIN")])
        self.assertTrue(_cumple(det, 2))

    def test_autoservicio_5_botellas_no_cumple(self):
        det, _ = _run([(2, 30134, 5, 1800, "05/07/2026", "FAC-1", G, "PINK GIN")])
        self.assertFalse(_cumple(det, 2))

    def test_autoservicio_con_3_botellas_no_usa_umbral_tradicional(self):
        """Un AS con 3 botellas cumpliría si se le aplicara el mínimo de Tradicional."""
        det, _ = _run([(2, 30134, 3, 1000, "05/07/2026", "FAC-1", G, "PINK GIN")])
        self.assertFalse(_cumple(det, 2))
        self.assertEqual(int(det["umbral"].iloc[0]), 6)


class ConsolidacionAntesDelMinimo(unittest.TestCase):

    def test_tres_lineas_de_una_botella_consolidan_a_3(self):
        det, _ = _run([
            (1, 30134, 1, 400, "05/07/2026", "FAC-1", G, "PINK GIN"),
            (1, 30134, 1, 400, "12/07/2026", "FAC-2", G, "PINK GIN"),
            (1, 30139, 1, 400, "20/07/2026", "FAC-3", G, "TROPICAL"),
        ])
        self.assertEqual(len(det), 1, "el cliente tiene que aparecer una sola vez por titular")
        self.assertTrue(_cumple(det, 1))
        self.assertEqual(float(det["botellas_netas"].iloc[0]), 3.0)

    def test_autoservicio_2_mas_4_cumple(self):
        det, _ = _run([
            (2, 30134, 2, 800, "05/07/2026", "FAC-1", G, "PINK GIN"),
            (2, 30134, 4, 1600, "18/07/2026", "FAC-2", G, "PINK GIN"),
        ])
        self.assertTrue(_cumple(det, 2))
        self.assertEqual(float(det["botellas_netas"].iloc[0]), 6.0)

    def test_varios_comprobantes_cuentan_una_sola_vez(self):
        det, _ = _run([(1, 30134, 5, 2000, "05/07/2026", f"FAC-{i}", G, "PINK GIN")
                       for i in range(4)])
        g = det[det["titular"] == "GORDON'S FLAVOURS"]
        self.assertEqual(len(g), 1)
        self.assertEqual(int(g["cliente_id"].nunique()), 1)

    def test_devolucion_resta_botellas_netas(self):
        """6 compradas - 4 devueltas = 2 netas: un Tradicional con 3 de mínimo NO cumple."""
        det, _ = _run([
            (1, 30134, 6, 2400, "05/07/2026", "FAC-1", G, "PINK GIN"),
            (1, 30134, -4, -1600, "22/07/2026", "NCR-1", G, "PINK GIN"),
        ])
        fila = det.iloc[0]
        self.assertEqual(float(fila["botellas_positivas"]), 6.0)
        self.assertEqual(float(fila["botellas_devueltas"]), -4.0)
        self.assertEqual(float(fila["botellas_netas"]), 2.0)
        self.assertFalse(bool(fila["cumple"]))

    def test_devolucion_parcial_deja_el_cliente_cubierto(self):
        det, _ = _run([
            (1, 30134, 6, 2400, "05/07/2026", "FAC-1", G, "PINK GIN"),
            (1, 30134, -1, -400, "22/07/2026", "NCR-1", G, "PINK GIN"),
        ])
        self.assertTrue(_cumple(det, 1))
        self.assertEqual(float(det["botellas_netas"].iloc[0]), 5.0)


class MatchDeSKU(unittest.TestCase):
    """El titular sale del código de artículo, nunca de `contains` sobre la descripción."""

    def test_gordons_gin_no_entra_en_gordons_flavours(self):
        det, exc = _run([(1, 30075, 12, 5000, "05/07/2026", "FAC-1", "Gordon's", "GORDON'S GIN 6x700")])
        self.assertTrue(det.empty, "Gordon's Gin no pertenece al titular Gordon's Flavours")
        self.assertIn("SKU_SIN_MATCH_EN_MATRIZ", set(exc["tipo"]))
        self.assertIn(30075, set(exc["clave"]))

    def test_gordons_tonic_no_entra_en_gordons_flavours(self):
        det, exc = _run([(1, 35107, 12, 5000, "05/07/2026", "FAC-1", "Gordon's", "GORDON'S TONIC 4X6X473")])
        self.assertTrue(det.empty)
        self.assertIn(35107, set(exc["clave"]))

    def test_sku_oficiales_de_gordons_flavours_si_entran(self):
        det, _ = _run([
            (1, 30134, 2, 800, "05/07/2026", "FAC-1", G, "PINK GIN"),
            (1, 30139, 1, 400, "06/07/2026", "FAC-2", G, "TROPICAL FRUITS"),
        ])
        self.assertTrue(_cumple(det, 1))
        self.assertEqual(det["skus"].iloc[0], "30134,30139")

    def test_sku_desconocido_se_reporta_no_se_descarta_en_silencio(self):
        _, exc = _run([(1, 99999, 10, 5000, "05/07/2026", "FAC-1", "OTRA", "PRODUCTO RARO")])
        fila = exc[exc["clave"] == 99999]
        self.assertEqual(len(fila), 1)
        self.assertEqual(int(fila["filas"].iloc[0]), 1)


class Periodo(unittest.TestCase):

    def test_cierre_de_julio_no_incorpora_agosto(self):
        filas = [
            (1, 30134, 2, 800, "20/07/2026", "FAC-1", G, "PINK GIN"),
            (1, 30134, 5, 2000, "03/08/2026", "FAC-2", G, "PINK GIN"),   # agosto
        ]
        det, _ = _run(filas, desde="2026-07-01", hasta="2026-07-31")
        self.assertEqual(float(det["botellas_netas"].iloc[0]), 2.0)
        self.assertFalse(_cumple(det, 1))
        self.assertEqual(det["periodo_desde"].iloc[0], "2026-07-01")
        self.assertEqual(det["periodo_hasta"].iloc[0], "2026-07-31")

    def test_ultimo_dia_del_periodo_entra(self):
        det, _ = _run([(1, 30134, 3, 1200, "31/07/2026", "FAC-1", G, "PINK GIN")],
                      desde="2026-07-01", hasta="2026-07-31")
        self.assertTrue(_cumple(det, 1))


class ExclusionesYNormalizacion(unittest.TestCase):

    def test_vendedor_excluido_no_se_contabiliza(self):
        det, exc = _run([(9, 30134, 12, 5000, "05/07/2026", "FAC-1", G, "PINK GIN")])
        self.assertTrue(det.empty)
        self.assertIn("VENDEDOR_EXCLUIDO", set(exc["tipo"]))

    def test_segmento_fuera_de_superficie_se_informa(self):
        det, exc = _run([(10, 30134, 12, 5000, "05/07/2026", "FAC-1", G, "PINK GIN")])
        self.assertTrue(det.empty)
        self.assertIn("SEGMENTO_FUERA_DE_SUPERFICIE", set(exc["tipo"]))

    def test_codigos_equivalentes_de_cliente_no_duplican(self):
        """'1', ' 1 ', '1.0' y 1 son el mismo cliente."""
        det, _ = _run([
            (1,     30134, 1, 400, "05/07/2026", "FAC-1", G, "PINK GIN"),
            (" 1 ",  30134, 1, 400, "06/07/2026", "FAC-2", G, "PINK GIN"),
            ("1.0", 30134, 1, 400, "07/07/2026", "FAC-3", G, "PINK GIN"),
        ])
        self.assertEqual(len(det), 1)
        self.assertEqual(float(det["botellas_netas"].iloc[0]), 3.0)
        self.assertTrue(_cumple(det, 1))

    def test_normalizacion_de_vendedor(self):
        for valor in (8, "8", "V8", "08", "8.0", " v8 "):
            self.assertEqual(m.normalizar_codigo_vendedor(valor), 8, f"fallo con {valor!r}")

    def test_normalizacion_de_segmento(self):
        casos = [
            ("TRADITIONAL TRADE", "Almacen/Despensa", "TRADICIONAL"),
            ("TRADITIONAL TRADE", "ALMACÉN", "TRADICIONAL"),
            ("TRADITIONAL TRADE", "  kiosco/maxikiosco ", "TRADICIONAL"),
            ("KIOSKO", "KIOSKO", "TRADICIONAL"),
            ("TRADITIONAL TRADE", "Autoservicio Tradicional", "AUTOSERVICIO"),
            ("Large Format", "Cadena Regional", "AUTOSERVICIO"),
            ("CADENAS REGIONALES (BAR)", "CADENAS REGIONALES (BAR)", "AUTOSERVICIO"),
            ("CASH&CARRY", "Mayoristas", m.FUERA_DE_SUPERFICIE),
            ("AWAY FROM HOME", "Vinoteca", m.FUERA_DE_SUPERFICIE),
            ("PROXIMITY", "Estacion de Servicio - AXION", m.FUERA_DE_SUPERFICIE),
        ]
        for ramo, sub, esperado in casos:
            self.assertEqual(m.normalizar_segmento_11t(ramo, sub), esperado,
                             f"fallo con {ramo!r} / {sub!r}")

    def test_sin_cargo_neto_cero_no_computa(self):
        det, exc = _run([(1, 30134, 12, 0, "05/07/2026", "FAC-1", G, "PINK GIN")])
        self.assertTrue(det.empty)
        self.assertIn("LINEA_SIN_CARGO_NETO_CERO", set(exc["tipo"]))


class RegresionGordonsJulio2026(unittest.TestCase):
    """Regresión histórica obligatoria: 25 tradicionales + 7 autoservicios = 32.

    Se CALCULA sobre el archivo real del cierre. Si falta el archivo el test se saltea
    (entorno sin inputs), nunca da falso verde."""

    FUENTE = m.INPUTS / "cierres mes" / "ventas_acumulada_072026.csv"

    @classmethod
    def setUpClass(cls):
        if not cls.FUENTE.exists() or not m.CLIENTES_PATH.exists() or not m.MATRIZ_11T_PATH.exists():
            raise unittest.SkipTest("faltan los inputs reales de julio 2026")
        ventas = pd.read_csv(cls.FUENTE, sep=";", encoding="latin1", low_memory=False)
        cls.det, cls.exc = m.cobertura_11t(ventas, desde="2026-07-01", hasta="2026-07-31")
        cls.g = cls.det[cls.det["titular"] == "GORDON'S FLAVOURS"]

    def test_gordons_tradicional_25(self):
        ok = self.g[self.g["cumple"] & (self.g["segmento_11t"] == "TRADICIONAL")]
        self.assertEqual(ok["cliente_id"].nunique(), 25)

    def test_gordons_autoservicio_7(self):
        ok = self.g[self.g["cumple"] & (self.g["segmento_11t"] == "AUTOSERVICIO")]
        self.assertEqual(ok["cliente_id"].nunique(), 7)

    def test_gordons_total_32(self):
        self.assertEqual(self.g[self.g["cumple"]]["cliente_id"].nunique(), 32)

    def test_gordons_no_incluye_gin_ni_tonic(self):
        """Los SKU 30075/35107 no pueden aparecer entre los de Gordon's Flavours."""
        skus = {s for fila in self.g["skus"] for s in str(fila).split(",") if s}
        self.assertNotIn("30075", skus)
        self.assertNotIn("35107", skus)
        self.assertTrue(skus <= {"30134", "30139"}, f"SKU inesperados: {skus}")

    def test_gordons_un_cliente_una_vez(self):
        self.assertEqual(len(self.g), self.g["cliente_id"].nunique())

    def test_la_regla_vieja_daba_mas(self):
        """Contar 'neto>0 sin mínimo' sobre los mismos SKU da más que la cobertura real:
        confirma que el test no está midiendo la regla vieja por accidente."""
        self.assertGreater(self.g["cliente_id"].nunique(),
                           self.g[self.g["cumple"]]["cliente_id"].nunique())

    def test_resumen_por_titular_coincide_con_el_detalle(self):
        r = m.resumen_por_titular(self.det)
        fila = r[r["titular"] == "GORDON'S FLAVOURS"].iloc[0]
        self.assertEqual(int(fila["cubiertos"]), 32)
        self.assertEqual(int(fila["cubiertos_tradicional"]), 25)
        self.assertEqual(int(fila["cubiertos_autoservicio"]), 7)

    def test_periodo_no_pasa_de_julio(self):
        self.assertEqual(set(self.det["periodo_desde"]), {"2026-07-01"})
        self.assertEqual(set(self.det["periodo_hasta"]), {"2026-07-31"})

    def test_todos_los_titulares_de_la_matriz_se_miden(self):
        self.assertEqual(set(self.det["titular"]) <= set(m.titulares_oficiales()), True)


class TodosLosModulosDanLoMismo(unittest.TestCase):
    """Integración: dashboard vivo, 11t_empresa, 11t_acum, cierre versionado y el motor
    tienen que devolver la MISMA cobertura para Gordon's julio-2026. Es el test que impide
    que vuelva a haber cuatro implementaciones con cuatro resultados."""

    TITULAR = "GORDON'S FLAVOURS"

    @classmethod
    def setUpClass(cls):
        import os
        fuente = m.INPUTS / "cierres mes" / "ventas_acumulada_072026.csv"
        if not fuente.exists() or not (m.BASE / "04_DATASETS_ORBIT" / "mod_11t_acum.csv").exists():
            raise unittest.SkipTest("faltan inputs reales o mod_11t_acum.csv")
        os.environ["PENAFLOR_SKIP_BOOT"] = "1"
        import server_orbit as srv
        cls.srv = srv
        cls.client = srv.app.test_client()

    def _gordons_del_motor(self):
        v = pd.read_csv(m.INPUTS / "cierres mes" / "ventas_acumulada_072026.csv",
                        sep=";", encoding="latin1", low_memory=False)
        det, _ = m.cobertura_11t(v, desde="2026-07-01", hasta="2026-07-31")
        g = det[(det["titular"] == self.TITULAR) & det["cumple"]]
        return (int((g["segmento_11t"] == "TRADICIONAL").sum()),
                int((g["segmento_11t"] == "AUTOSERVICIO").sum()))

    def test_cierre_versionado_igual_al_motor(self):
        files = self.srv._cierre_archivos_mes("2026-07")
        self.assertIsNotNone(files, "faltan los archivos del cierre de julio")
        r = self.srv._cierre_once_titulares(files)
        fila = next(x for x in r["marcas"] if x["marca"] == self.TITULAR)
        tr, aut = self._gordons_del_motor()
        self.assertEqual((fila["cubiertos_tradicional"], fila["cubiertos_autoservicio"]), (tr, aut))
        self.assertEqual(fila["cubiertos"], tr + aut)
        self.assertEqual(r["metrica"], "cobertura")

    def test_cierre_no_arrastra_agosto(self):
        files = self.srv._cierre_archivos_mes("2026-07")
        r = self.srv._cierre_once_titulares(files)
        self.assertEqual(r["periodo_desde"], "2026-07-01")
        self.assertEqual(r["periodo_hasta"], "2026-07-31")

    def test_cierre_da_igual_con_acumulada_que_con_ventas_mes(self):
        files = self.srv._cierre_archivos_mes("2026-07")
        con = self.srv._cierre_once_titulares(files)
        sin = self.srv._cierre_once_titulares({**files, "ventas_acumulada": None})
        f1 = next(x for x in con["marcas"] if x["marca"] == self.TITULAR)
        f2 = next(x for x in sin["marcas"] if x["marca"] == self.TITULAR)
        self.assertEqual(f1["cubiertos"], f2["cubiertos"])

    def test_dashboard_vivo_declara_periodo_y_metrica(self):
        j = self.client.get("/api/gerencia/once_titulares").get_json()
        self.assertEqual(j["metrica"], "cobertura")
        self.assertEqual(j["umbrales"], {"AUTOSERVICIO": 6, "TRADICIONAL": 3})
        self.assertTrue(j["periodo_desde"] and j["periodo_hasta"])
        fila = next(x for x in j["marcas"] if x["marca"] == self.TITULAR)
        # el campo histórico `ccc` tiene que traer la cobertura, no clientes con compra
        self.assertEqual(fila["ccc"], fila["cubiertos"])
        self.assertEqual(fila["cubiertos"],
                         fila["cubiertos_tradicional"] + fila["cubiertos_autoservicio"])

    def test_dashboard_11t_empresa_y_11t_acum_coinciden(self):
        emp = self.client.get("/api/gerencia/11t_empresa").get_json()
        acu = self.client.get("/api/gerencia/11t_acum").get_json()
        f_emp = next(x for x in emp["marcas"] if x["marca"] == self.TITULAR)
        f_acu = next(x for x in acu["por_marca"] if x["marca_objetivo"] == self.TITULAR)
        self.assertEqual(f_emp["con"], int(f_acu["cubiertos"]))
        self.assertEqual(f_emp["total"], int(f_acu["cartera"]))

    def test_kpi_marcas_11t_no_supera_el_total_de_titulares(self):
        """El KPI cuenta TITULARES cubiertos, no pares cliente×marca."""
        t11 = pd.read_csv(m.BASE / "04_DATASETS_ORBIT" / "mod_11t_acum.csv", encoding="utf-8-sig")
        n_tit = t11["marca_objetivo"].nunique()
        for _cn, g in t11.groupby(t11["vendedor_codigo"].astype(str)):
            cubiertas = g.loc[g["tiene_flag"] == 1, "marca_objetivo"].nunique()
            self.assertLessEqual(cubiertas, n_tit)

    def test_11t_empresa_no_usa_el_dataset_legacy(self):
        j = self.client.get("/api/gerencia/11t_empresa").get_json()
        self.assertNotIn("mod_11_titulares", j["fuente"])
        self.assertIn("mod_11t_acum", j["fuente"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
