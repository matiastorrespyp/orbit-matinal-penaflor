import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ["PENAFLOR_SKIP_BOOT"] = "1"

import server_orbit as orbit


class PlanSemanalPersistenciaTest(unittest.TestCase):
    """Prueba real sobre SQLite temporal; no toca orbit.db ni datos del portal."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_original = orbit.DB_PATH
        orbit.DB_PATH = Path(self.tmp.name) / "orbit_test.db"
        orbit.DB_PATH.touch()  # evita sembrar la temporal con orbit.db del proyecto
        orbit.init_db()
        self.client = orbit.app.test_client()

    def tearDown(self):
        orbit.DB_PATH = self.db_original
        self.tmp.cleanup()

    def test_guardar_releer_y_borrar_plan_completo(self):
        plan = {kpi: [10, 20, 30, 40] for kpi in orbit._SEMANAL_KPI_IDS}
        response = self.client.post("/api/gerencia/semanal/plan", json={
            "periodo": "2026-08", "autor": "Prueba ORBIT", "plan": plan,
        })
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["persistencia"], "sqlite_local")

        # Nueva conexión al mismo archivo: comprueba persistencia, no memoria del proceso.
        conn = sqlite3.connect(str(orbit.DB_PATH))
        rows = conn.execute(
            "SELECT kpi, semana, pct FROM plan_semanal WHERE periodo='2026-08'"
        ).fetchall()
        conn.close()
        self.assertEqual(len(rows), len(orbit._SEMANAL_KPI_IDS) * 4)
        releido, meta = orbit._semanal_plan_local_leer("2026-08")
        self.assertEqual(releido, {kpi: [10.0, 20.0, 30.0, 40.0]
                                   for kpi in orbit._SEMANAL_KPI_IDS})
        self.assertEqual(meta["editado_por"], "Prueba ORBIT")

        vacio = {kpi: [None, None, None, None] for kpi in orbit._SEMANAL_KPI_IDS}
        borrado = self.client.post("/api/gerencia/semanal/plan", json={
            "periodo": "2026-08", "autor": "Prueba ORBIT", "plan": vacio,
        })
        self.assertEqual(borrado.status_code, 200, borrado.get_data(as_text=True))
        conn = sqlite3.connect(str(orbit.DB_PATH))
        cantidad = conn.execute(
            "SELECT COUNT(*) FROM plan_semanal WHERE periodo='2026-08'"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(cantidad, 0)


if __name__ == "__main__":
    unittest.main()
