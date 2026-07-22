"""
Test del fallback de Plan vs Real (/api/matinal/resumen) al ÚLTIMO SNAPSHOT COMPLETO.

Reproduce el modo EMBEBIDO (Orbit Home): sin SQLite poblado, sin 02_HISTORY, sin
01_INPUTS/ventas.csv. Verifica que el endpoint NO usa la fecha del reloj sino el último
cierre completo (fecha_ejecucion del dataset), con datos reales del snapshot, sin mezclar
fechas y sin pedir CIERRE_DIA_ORBIT.bat.

Aísla el módulo redirigiendo BASE/DATASETS/CONFIG/INPUTS/DB_PATH a temporales sintéticos.
No toca datos productivos, Google Sheets, SQLite productiva ni Render.

Ejecutar:  python -m unittest test_matinal_resumen_snapshot
"""
from __future__ import annotations
import csv
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ["PENAFLOR_SKIP_BOOT"] = "1"          # import seguro: sin ETL/hilos/escritura

import server_orbit as srv                       # noqa: E402

VOL_COLS = ["fecha_ejecucion", "fecha_objetivo", "vendedor_codigo", "vendedor_nombre",
            "clientes_planificados", "venta_ayer", "real_resultado", "clientes_compra_ayer",
            "objetivo_mes", "acumulado_mes"]


def _write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)


class MatinalResumenSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="matinal_snap_")
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        base = Path(self.tmp)
        self.ds = base / "04_DATASETS_ORBIT"; self.ds.mkdir()
        self.cfg = base / "09_CONFIG"; self.cfg.mkdir()
        self.inp = base / "01_INPUTS"    # existe pero SIN ventas.csv
        self.db = base / "orbit.db"

        # Guardar y redirigir los globals del módulo (aislamiento total).
        self._orig = {k: getattr(srv, k) for k in ("BASE", "DATASETS", "CONFIG", "INPUTS", "DB_PATH")}
        srv.BASE, srv.DATASETS, srv.CONFIG, srv.INPUTS, srv.DB_PATH = \
            base, self.ds, self.cfg, self.inp, self.db
        try:
            srv._READ_CSV_CACHE.clear(); srv._VENTAS_PARSED_CACHE.clear()
        except Exception:
            pass
        self.addCleanup(self._restore)

        # vendedores activos (V6, V8, V9 — dentro del roster; no V2/V5/V20).
        _write_csv(self.cfg / "vendedores_activos.csv",
                   ["codigo_vendedor", "nombre_vendedor", "activo"],
                   [{"codigo_vendedor": "V6", "nombre_vendedor": "Andrea Peyronel", "activo": "1"},
                    {"codigo_vendedor": "V8", "nombre_vendedor": "Vanesa Alvarez", "activo": "1"},
                    {"codigo_vendedor": "V9", "nombre_vendedor": "Fernando Sanchez", "activo": "1"}])

        srv.init_db()          # esquema SQLite vacío (como el mount de Orbit Home en runtime)
        srv.app.config.update(TESTING=True)
        self.client = srv.app.test_client()

    def _restore(self):
        for k, v in self._orig.items():
            setattr(srv, k, v)
        try:
            srv._READ_CSV_CACHE.clear(); srv._VENTAS_PARSED_CACHE.clear()
        except Exception:
            pass

    def _snapshot(self, fechas_por_vendedor):
        """fechas_por_vendedor: lista de dicts con fecha_ejecucion/vendedor/real/venta/ccc."""
        rows = []
        for d in fechas_por_vendedor:
            rows.append({
                "fecha_ejecucion": d["fecha"], "fecha_objetivo": d.get("obj", ""),
                "vendedor_codigo": d["vc"], "vendedor_nombre": d.get("nombre", f"V{d['vc']}"),
                "clientes_planificados": d.get("cli", "0"),
                "venta_ayer": d.get("venta", "0"), "real_resultado": d.get("real", "0"),
                "clientes_compra_ayer": d.get("ccc", "0"),
                "objetivo_mes": "0", "acumulado_mes": "0"})
        _write_csv(self.ds / "mod_volumen_vendedor.csv", VOL_COLS, rows)
        try:
            srv._READ_CSV_CACHE.clear()
        except Exception:
            pass

    def _seed_plan(self, fecha, vid, venta_esperada):
        srv.init_db()
        conn = sqlite3.connect(str(self.db))
        conn.execute(
            "INSERT INTO planificacion (fecha,vendedor_id,venta_esperada,ccc_tradicional,estado,"
            "created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (fecha, vid, venta_esperada, 5, "aprobada", "t", "t"))
        conn.commit(); conn.close()
        try:
            srv._READ_CSV_CACHE.clear()
        except Exception:
            pass

    # A. Reloj != snapshot: usa la fecha del snapshot (último cierre), con datos reales.
    def test_A_usa_ultimo_cierre_con_datos(self):
        self._snapshot([{"fecha": "2026-07-21", "vc": "6", "venta": "100000", "real": "95000", "ccc": "12"},
                        {"fecha": "2026-07-21", "vc": "8", "venta": "80000", "real": "82000", "ccc": "9"}])
        r = self.client.get("/api/matinal/resumen")
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertEqual(j["fecha_plan"], "2026-07-21")
        self.assertEqual(j["fecha_real"], "2026-07-21")
        self.assertTrue(j["tiene_real"])
        self.assertEqual(j.get("origen"), "snapshot")
        by = {v["vendedor_id"]: v for v in j["resumen"]}
        self.assertEqual(by["V6"]["real_ayer"], 95000.0)     # real_resultado del snapshot
        self.assertEqual(by["V8"]["real_ayer"], 82000.0)
        self.assertTrue(by["V6"]["tiene_real"])

    # C. Plan de una fecha, real de otra: NUNCA se mezclan (todo en la fecha efectiva).
    def test_C_no_mezcla_fechas(self):
        self._snapshot([{"fecha": "2026-07-21", "vc": "6", "venta": "100000", "real": "95000", "ccc": "12"}])
        self._seed_plan("2026-07-22", "V6", 120000)         # plan de OTRA fecha (22)
        j = self.client.get("/api/matinal/resumen").get_json()
        self.assertEqual(j["fecha_plan"], "2026-07-21")     # efectiva = snapshot 21
        v6 = next(v for v in j["resumen"] if v["vendedor_id"] == "V6")
        self.assertEqual(v6["fecha_plan"], v6["fecha_real"])          # misma fecha
        self.assertFalse(v6["tiene_plan"])                  # el plan del 22 NO se usa para el 21

    # Plan de la MISMA fecha efectiva sí se usa (fuente de verdad hidratada en cache).
    def test_plan_misma_fecha_se_usa(self):
        self._snapshot([{"fecha": "2026-07-21", "vc": "6", "venta": "100000", "real": "95000", "ccc": "12"}])
        self._seed_plan("2026-07-21", "V6", 120000)
        v6 = next(v for v in self.client.get("/api/matinal/resumen").get_json()["resumen"]
                  if v["vendedor_id"] == "V6")
        self.assertTrue(v6["tiene_plan"])
        self.assertEqual(v6["plan_venta"], 120000.0)
        self.assertEqual(v6["delta"], 95000.0 - 120000.0)

    # F. Cambio de mes/año: elige el último cierre disponible por fecha (orden lexicográfico ISO).
    def test_F_cambio_mes_anio(self):
        self._snapshot([{"fecha": "2025-12-31", "vc": "6", "venta": "1", "real": "1", "ccc": "1"},
                        {"fecha": "2026-01-02", "vc": "6", "venta": "500", "real": "480", "ccc": "3"}])
        j = self.client.get("/api/matinal/resumen").get_json()
        self.assertEqual(j["fecha_plan"], "2026-01-02")     # el más reciente
        v6 = next(v for v in j["resumen"] if v["vendedor_id"] == "V6")
        self.assertEqual(v6["real_ayer"], 480.0)

    # Contrato JSON: claves que consume portal.html presentes.
    def test_contrato_json(self):
        self._snapshot([{"fecha": "2026-07-21", "vc": "6", "venta": "100000", "real": "95000", "ccc": "12"}])
        j = self.client.get("/api/matinal/resumen").get_json()
        for k in ("fecha_plan", "fecha_real", "tiene_real", "modo", "fuente_real", "resumen"):
            self.assertIn(k, j)
        v = j["resumen"][0]
        for k in ("vendedor_id", "vendedor_nombre", "plan_venta", "real_ayer", "delta",
                  "pct_cumplimiento", "plan_ccc_trad", "real_ccc_trad", "real_ccc_total",
                  "tiene_plan", "tiene_real", "fecha_plan", "fecha_real"):
            self.assertIn(k, v)

    # Sin snapshot NI fuentes vivas: no rompe (200, sin fecha de reloj forzada con datos).
    def test_sin_snapshot_no_500(self):
        # no se crea mod_volumen_vendedor.csv
        r = self.client.get("/api/matinal/resumen")
        self.assertEqual(r.status_code, 200)     # cae al return normal (sin datos), sin 500


if __name__ == "__main__":
    unittest.main(verbosity=2)
