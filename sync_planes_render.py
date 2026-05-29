"""
sync_planes_render.py
Descarga los planes del servidor Render y los importa en el orbit.db local.
Usar antes de iniciar el servidor local para Plan vs Real en la matinal.
"""
import urllib.request, json, sqlite3, sys
from pathlib import Path

RENDER_BASE = "https://orbit-penaflor-pav.onrender.com"
RENDER_URL  = RENDER_BASE + "/api/planificacion"
DB_PATH     = Path(__file__).parent / "orbit.db"

def sync():
    # Paso 1: Wake-up — Render puede estar dormido (plan gratuito/starter)
    print(f"  Despertando servidor Render (puede tardar hasta 30 seg)...")
    for intento in range(3):
        try:
            req_wake = urllib.request.Request(
                RENDER_BASE + "/api/healthz",
                headers={"User-Agent": "ORBIT-sync/1.0"}
            )
            with urllib.request.urlopen(req_wake, timeout=35) as resp:
                status = json.loads(resp.read()).get("status","?")
                print(f"  Render activo: {status}")
                break
        except Exception as e:
            if intento < 2:
                print(f"  Intento {intento+1} fallido ({e}), reintentando...")
            else:
                print(f"  AVISO: Render no respondió al wake-up: {e}")
                print(f"  Continuando sin sincronizar. Plan vs Real mostrará solo planes locales.")
                return False

    # Paso 2: Descargar planes
    print(f"  Descargando planes desde Render...")
    try:
        req = urllib.request.Request(RENDER_URL, headers={"User-Agent": "ORBIT-sync/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            planes = json.loads(resp.read())
    except Exception as e:
        print(f"  AVISO: No se pudo conectar a Render: {e}")
        print(f"  Continuando sin sincronizar. Plan vs Real mostrara solo planes locales.")
        return False

    if not isinstance(planes, list) or not planes:
        print(f"  Sin planes en Render o respuesta inesperada.")
        return True

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    cols = [
        "fecha","vendedor_id","zona","dia_visita","venta_esperada",
        "ccc_tradicional","ccc_autoservicio","ccc_onpremise","once_t",
        "marcas","clientes_clave","acciones","estado",
        "editado_por","comentario_gerencia","created_at","updated_at"
    ]

    importados = 0
    for p in planes:
        vals = [p.get(c) for c in cols]
        conn.execute(
            f"INSERT OR REPLACE INTO planificacion ({','.join(cols)}) "
            f"VALUES ({','.join(['?']*len(cols))})",
            vals
        )
        importados += 1

    conn.commit()

    # Mostrar resumen
    rows = conn.execute(
        "SELECT fecha, vendedor_id, estado, ccc_tradicional, updated_at "
        "FROM planificacion ORDER BY fecha DESC, vendedor_id"
    ).fetchall()
    conn.close()

    print(f"  Planes importados desde Render: {importados}")
    for r in rows:
        print(f"    {r['vendedor_id']} | {r['fecha']} | {r['estado']} | CCC T={r['ccc_tradicional']} | {(r['updated_at'] or '')[:16]}")

    return True

if __name__ == "__main__":
    ok = sync()
    sys.exit(0 if ok else 1)
