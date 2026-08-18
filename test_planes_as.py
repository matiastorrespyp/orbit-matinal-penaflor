import unittest
from pathlib import Path

import generar_datasets_acum as motor


FUENTE_AGOSTO = Path(__file__).parent / "01_INPUTS" / "Planes AASS" / "sincargosagosto.xlsx"


class PlanesAASSAgostoTest(unittest.TestCase):
    """Valida el Excel real de agosto; no usa mocks ni datos inventados."""

    def test_escala_y_etiquetas(self):
        asignaciones = motor._cargar_sincargos_mes(FUENTE_AGOSTO)
        self.assertEqual(len(asignaciones), 30)
        self.assertEqual(sum(a["sc_total_ganado"] for a in asignaciones.values()), 134)
        self.assertEqual(sum(a["sc_alaris"] for a in asignaciones.values()), 109)
        self.assertEqual(sum(a["sc_alma_mora"] for a in asignaciones.values()), 23)
        self.assertEqual(sum(a["sc_frizze"] for a in asignaciones.values()), 2)
        muestra = next(iter(asignaciones.values()))
        self.assertEqual(muestra["sc_label_alaris"], "Finca Las Moras")
        self.assertEqual(muestra["sc_label_alma_mora"], "Elementos")
        self.assertEqual(muestra["sc_label_antares_ipa"], "Antares Lager")

    def test_plan_frio_excluye_no_cumple(self):
        clientes = motor._cargar_planfrio_mes(FUENTE_AGOSTO)
        self.assertEqual(len(clientes), 27)
        self.assertNotIn(2357, clientes)
        self.assertNotIn(30006, clientes)
        self.assertIn(390, clientes)

    def test_puntera_embebida(self):
        clientes, producto = motor._cargar_puntera_mes(FUENTE_AGOSTO)
        self.assertEqual(producto, "Los Arboles")
        self.assertEqual(clientes, {172: 3, 538: 3, 30011: 3, 30044: 3})


if __name__ == "__main__":
    unittest.main()
