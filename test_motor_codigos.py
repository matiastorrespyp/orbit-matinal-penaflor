# -*- coding: utf-8 -*-
"""Tests de motor_codigos: equivalencias codigo del catalogo del proveedor -> codigo del ERP.

Correr:  python test_motor_codigos.py
"""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

import motor_11t
import motor_codigos

BASE = Path(__file__).resolve().parent


def _csv(tmp, texto):
    p = Path(tmp) / "equiv.csv"
    p.write_text(texto, encoding="utf-8-sig")
    return p


class TestEquivalencias(unittest.TestCase):

    def test_lee_el_archivo_real(self):
        """El archivo de produccion carga y todas sus filas son int->int."""
        eq = motor_codigos.equivalencias()
        self.assertIsInstance(eq, dict)
        for a, b in eq.items():
            self.assertIsInstance(a, int)
            self.assertIsInstance(b, int)
            self.assertNotEqual(a, b, "una equivalencia a si mismo no sirve para nada")

    def test_los_tres_antares_estan_mapeados(self):
        """Caso testigo 2026-08-24: el catalogo dice 600xx, nuestro ERP factura 30xxx."""
        eq = motor_codigos.equivalencias()
        self.assertEqual(eq.get(60001), 30329, "Antares Kolsch")
        self.assertEqual(eq.get(60002), 30343, "Antares Scotch")
        self.assertEqual(eq.get(60007), 30268, "Antares Caravana")

    def test_canonizar_deja_pasar_lo_que_no_tiene_equivalencia(self):
        """Sin fila en la tabla, el codigo NO se toca. Es lo que hace el cambio seguro."""
        self.assertEqual(motor_codigos.canonizar(60018), 60018)
        self.assertEqual(motor_codigos.canonizar(74208), 74208)

    def test_canonizar_tolera_basura(self):
        # Devuelve el MISMO objeto: se compara con assertIs porque NaN != NaN.
        for v in (None, "", "abc", float("nan")):
            self.assertIs(motor_codigos.canonizar(v), v)

    def test_sin_archivo_no_cambia_nada(self):
        """Si el CSV no esta, equivalencias() = {} y todo queda como estaba.
        Nunca se inventa un mapeo."""
        with TemporaryDirectory() as tmp:
            self.assertEqual(motor_codigos.equivalencias(Path(tmp) / "no_existe.csv"), {})

    def test_ignora_filas_incompletas_o_identidad(self):
        with TemporaryDirectory() as tmp:
            p = _csv(tmp, "codigo_catalogo,codigo_erp,producto\n"
                          "111,222,ok\n"
                          "333,,sin destino\n"
                          ",444,sin origen\n"
                          "555,555,identidad\n"
                          "xxx,666,no numerico\n")
            eq = motor_codigos.equivalencias(p)
            self.assertEqual(eq, {111: 222})

    def test_canonizar_serie_vectorizado(self):
        with TemporaryDirectory() as tmp:
            p = _csv(tmp, "codigo_catalogo,codigo_erp\n10,99\n")
            s = pd.Series([10, 11, 10])
            self.assertEqual(list(motor_codigos.canonizar_serie(s, p)), [99, 11, 99])

    def test_serie_intacta_sin_equivalencias(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "vacio.csv"
            s = pd.Series([1, 2, 3])
            self.assertEqual(list(motor_codigos.canonizar_serie(s, p)), [1, 2, 3])


class TestMatriz11T(unittest.TestCase):
    """La matriz oficial tiene que salir del loader ya canonizada."""

    def setUp(self):
        motor_11t._MATRIZ_CACHE.update({"mtime": None, "data": None})
        self.m = motor_11t.cargar_matriz_11t()
        self.codigos = set(self.m["codigo_articulo"].astype(int))

    def test_los_codigos_vivos_estan_en_la_matriz(self):
        for c, nombre in [(30329, "Kolsch"), (30343, "Scotch"), (30268, "Caravana")]:
            self.assertIn(c, self.codigos, f"Antares {nombre} tiene que medirse por {c}")

    def test_los_codigos_del_catalogo_ya_no_estan(self):
        for c in (60001, 60002, 60007):
            self.assertNotIn(c, self.codigos,
                             f"{c} es el codigo del catalogo: no lo factura nuestro ERP")

    def test_siguen_siendo_los_mismos_titulares_y_la_misma_cantidad(self):
        """Canonizar REMAPEA, no agrega ni saca SKUs: 82 filas y 11 titulares."""
        self.assertEqual(len(self.m), 82)
        self.assertEqual(len(set(self.m["titular"])), 11)

    def test_los_tres_siguen_siendo_antares(self):
        t = dict(zip(self.m["codigo_articulo"].astype(int), self.m["titular"]))
        for c in (30329, 30343, 30268):
            self.assertEqual(t[c], "ANTARES")

    def test_no_hay_codigos_duplicados(self):
        """Si una equivalencia apuntara a un codigo que ya esta en la matriz, el
        drop_duplicates lo colapsa y el SKU cambiaria de titular sin avisar."""
        self.assertEqual(len(self.m), len(self.codigos))


if __name__ == "__main__":
    unittest.main(verbosity=2)
