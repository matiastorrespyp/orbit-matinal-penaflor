# -*- coding: utf-8 -*-
"""
Tests de la resolución de duplicados del padrón (motor_padron.py).

Regla auditada: si un mismo cliente aparece en V3 y V8, prevalece **V8**. Cualquier otra
colisión entre vendedores se informa y NO se resuelve automáticamente.

Incluye la verificación sobre el padrón real (`01_INPUTS/clientes.xlsx`) y sobre los
indicadores de V3/V8 que dependen de la cartera.

Ejecutar:  python -m unittest test_motor_padron
"""
from __future__ import annotations

import unittest

import pandas as pd

import motor_padron as mp

#: Los 10 duplicados V3/V8 del padrón real. NO es la fuente de la regla — la regla es por
#: par de vendedores. Esta lista sólo documenta el caso conocido y se verifica contra el
#: archivo: si el ERP corrige la cartera, el test lo detecta en vez de dar falso verde.
CODIGOS_V3_V8 = [272, 320, 1065, 1257, 1336, 1366, 1392, 1414, 1424, 4758]


def _padron(filas):
    """filas: (Codigo, Razon_Social, codven, DiasVisita)."""
    return pd.DataFrame([{"Codigo": c, "Razon_Social": n, "codven": v, "DiasVisita": d}
                         for c, n, v, d in filas])


class ReglaV3V8(unittest.TestCase):

    def test_duplicado_v3_v8_queda_en_v8(self):
        df, inc = mp.resolver_padron(_padron([
            (123, "CLIENTE UNO", 3, "Lu"),
            (123, "CLIENTE UNO", 8, "Mi"),
        ]))
        self.assertEqual(len(df), 1)
        self.assertEqual(int(df["codven"].iloc[0]), 8)
        self.assertEqual(inc["tipo"].iloc[0], mp.DUP_RESUELTO)
        self.assertEqual(inc["vendedor_resuelto"].iloc[0], "V8")

    def test_el_orden_de_las_filas_no_cambia_el_resultado(self):
        a, _ = mp.resolver_padron(_padron([(123, "X", 3, "Lu"), (123, "X", 8, "Mi")]))
        b, _ = mp.resolver_padron(_padron([(123, "X", 8, "Mi"), (123, "X", 3, "Lu")]))
        self.assertEqual(int(a["codven"].iloc[0]), 8)
        self.assertEqual(int(b["codven"].iloc[0]), 8)

    def test_conserva_la_fila_entera_de_v8(self):
        """DiasVisita y Orden difieren entre las dos filas (clientes 1392 y 1424 reales)."""
        df, _ = mp.resolver_padron(_padron([
            (1392, "PASERO", 3, "Sa"),
            (1392, "PASERO", 8, "Vi"),
        ]))
        self.assertEqual(df["DiasVisita"].iloc[0], "Vi")

    def test_cliente_exclusivo_de_v3_permanece_en_v3(self):
        df, inc = mp.resolver_padron(_padron([(500, "SOLO V3", 3, "Lu")]))
        self.assertEqual(int(df["codven"].iloc[0]), 3)
        self.assertTrue(inc.empty)

    def test_cliente_exclusivo_de_v8_permanece_en_v8(self):
        df, inc = mp.resolver_padron(_padron([(501, "SOLO V8", 8, "Lu")]))
        self.assertEqual(int(df["codven"].iloc[0]), 8)
        self.assertTrue(inc.empty)

    def test_no_afecta_al_resto_del_padron(self):
        df, _ = mp.resolver_padron(_padron([
            (500, "SOLO V3", 3, "Lu"), (501, "SOLO V8", 8, "Lu"),
            (123, "DUP", 3, "Lu"), (123, "DUP", 8, "Mi"),
            (700, "OTRO", 9, "Ju"),
        ]))
        self.assertEqual(sorted(df["Codigo"].tolist()), [123, 500, 501, 700])
        self.assertEqual(int(df[df["Codigo"] == 700]["codven"].iloc[0]), 9)


class ColisionesQueNoSeResuelvenSolas(unittest.TestCase):

    def test_colision_entre_otros_vendedores_se_informa_y_no_se_decide(self):
        df, inc = mp.resolver_padron(_padron([
            (900, "AMBIGUO", 4, "Lu"),
            (900, "AMBIGUO", 9, "Mi"),
        ]))
        self.assertEqual(len(df), 1, "igual queda una sola fila para no romper la carga")
        self.assertEqual(inc["tipo"].iloc[0], mp.DUP_SIN_REGLA)
        self.assertIn("revision manual", inc["detalle"].iloc[0])

    def test_duplicado_con_el_mismo_vendedor_deja_un_registro_y_avisa(self):
        df, inc = mp.resolver_padron(_padron([
            (800, "DOBLE V8", 8, "Lu"),
            (800, "DOBLE V8", 8, "Lu"),
        ]))
        self.assertEqual(len(df), 1)
        self.assertEqual(int(df["codven"].iloc[0]), 8)
        self.assertEqual(inc["tipo"].iloc[0], mp.DUP_MISMO_VENDEDOR)


class NormalizacionDeCodigos(unittest.TestCase):

    def test_codigos_equivalentes_se_detectan_como_el_mismo_cliente(self):
        df, inc = mp.resolver_padron(_padron([
            ("123", "X", 3, "Lu"), (" 123 ", "X", 8, "Mi"), ("123.0", "X", 3, "Ju"),
        ]))
        self.assertEqual(len(df), 1)
        self.assertEqual(int(df["codven"].iloc[0]), 8)
        self.assertEqual(int(inc["apariciones"].iloc[0]), 3)

    def test_normalizacion_de_vendedor(self):
        for v in (8, "8", "V8", "08", "8.0", " v8 "):
            self.assertEqual(mp.normalizar_codigo_vendedor(v), 8, f"fallo con {v!r}")

    def test_normalizacion_de_cliente(self):
        for v in (1294, "1294", " 1294 ", "1294.0"):
            self.assertEqual(mp.normalizar_codigo_cliente(v), 1294, f"fallo con {v!r}")
        self.assertIsNone(mp.normalizar_codigo_cliente("SIN CODIGO"))

    def test_padron_sin_duplicados_devuelve_incidencias_vacias(self):
        df, inc = mp.resolver_padron(_padron([(1, "A", 3, "Lu"), (2, "B", 8, "Mi")]))
        self.assertEqual(len(df), 2)
        self.assertTrue(inc.empty)


class PadronReal(unittest.TestCase):
    """Verificación sobre `01_INPUTS/clientes.xlsx`."""

    @classmethod
    def setUpClass(cls):
        import motor_11t as m11
        if not m11.CLIENTES_PATH.exists():
            raise unittest.SkipTest("falta 01_INPUTS/clientes.xlsx")
        cls.crudo = pd.read_excel(m11.CLIENTES_PATH)
        cls.resuelto, cls.inc = mp.resolver_padron(cls.crudo, origen="test")
        cls.padron = m11.cargar_padron_clientes()

    def test_no_quedan_codigos_duplicados_despues_de_cargar(self):
        self.assertEqual(len(self.resuelto), self.resuelto["Codigo"].nunique())
        self.assertEqual(len(self.padron), self.padron["cliente_id"].nunique())

    def test_los_duplicados_conocidos_son_todos_v3_v8(self):
        res = self.inc[self.inc["tipo"] == mp.DUP_RESUELTO]
        self.assertEqual(sorted(res["cliente_id"].tolist()), CODIGOS_V3_V8)
        self.assertEqual(set(res["vendedores"]), {"V3/V8"})

    def test_todos_quedaron_exclusivamente_en_v8(self):
        for cod in CODIGOS_V3_V8:
            fila = self.padron[self.padron["cliente_id"] == cod]
            self.assertEqual(len(fila), 1, f"cliente {cod} aparece {len(fila)} veces")
            self.assertEqual(int(fila["vendedor_codigo"].iloc[0]), 8,
                             f"cliente {cod} no quedó en V8")

    def test_ninguno_sigue_en_la_cartera_de_v3(self):
        cartera_v3 = set(self.padron[self.padron["vendedor_codigo"] == 3]["cliente_id"])
        self.assertEqual(cartera_v3 & set(CODIGOS_V3_V8), set())

    def test_todos_estan_en_la_cartera_de_v8(self):
        cartera_v8 = set(self.padron[self.padron["vendedor_codigo"] == 8]["cliente_id"])
        self.assertEqual(set(CODIGOS_V3_V8) - cartera_v8, set())

    def test_no_hay_colisiones_sin_regla_en_el_padron_real(self):
        sin = self.inc[self.inc["tipo"] == mp.DUP_SIN_REGLA]
        self.assertTrue(sin.empty,
                        f"colisiones sin regla que hay que revisar: {sin.to_dict('records')}")

    def test_el_padron_no_perdio_clientes_no_duplicados(self):
        self.assertEqual(len(self.resuelto), len(self.crudo) - len(CODIGOS_V3_V8))


class IndicadoresPorVendedor(unittest.TestCase):
    """La reasignación tiene que verse en la cobertura 11T por vendedor de cartera."""

    @classmethod
    def setUpClass(cls):
        import motor_11t as m11
        cls.m11 = m11
        fuente = m11.INPUTS / "cierres mes" / "ventas_acumulada_072026.csv"
        if not fuente.exists() or not m11.CLIENTES_PATH.exists():
            raise unittest.SkipTest("faltan los inputs reales")
        v = pd.read_csv(fuente, sep=";", encoding="latin1", low_memory=False)
        cls.det, _ = m11.cobertura_11t(v, desde="2026-07-01", hasta="2026-07-31")

    def test_los_clientes_corregidos_no_aparecen_en_indicadores_de_v3(self):
        v3 = self.det[self.det["vendedor_codigo"] == 3]
        self.assertEqual(set(v3["cliente_id"]) & set(CODIGOS_V3_V8), set())

    def test_los_clientes_corregidos_con_venta_aparecen_en_v8(self):
        medidos = set(self.det["cliente_id"]) & set(CODIGOS_V3_V8)
        self.assertTrue(medidos, "ninguno de los 10 tuvo venta 11T en julio: test sin señal")
        v8 = set(self.det[self.det["vendedor_codigo"] == 8]["cliente_id"])
        self.assertEqual(medidos - v8, set())

    def test_venta_facturada_por_v20_se_atribuye_al_vendedor_de_cartera(self):
        """Cliente 15: Autoservicio de la cartera de V8, facturado por V20 Depósito."""
        fila = self.det[(self.det["cliente_id"] == 15) &
                        (self.det["titular"] == "GORDON'S FLAVOURS")]
        self.assertEqual(len(fila), 1)
        self.assertEqual(int(fila["vendedor_codigo"].iloc[0]), 8)
        self.assertTrue(bool(fila["cumple"].iloc[0]))

    def test_v3_no_tiene_autoservicio(self):
        v3 = self.det[self.det["vendedor_codigo"] == 3]
        self.assertEqual(set(v3["segmento_11t"]) & {"AUTOSERVICIO"}, set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
