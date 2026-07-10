# -*- coding: utf-8 -*-
"""
Guard Git del Cierre del Dia / Cierre de Mes de ORBIT Matinal Penaflor.

Clasifica los cambios pendientes del repo POR RUTA (no solo por extension) en:

  - OPERATIVOS PERMITIDOS: datos de entrada, snapshots y datasets generados por
    el propio proceso de cierre. Pueden estar modificados antes de cerrar el dia.
  - FUNCIONALES BLOQUEANTES: codigo, scripts, configuracion o interfaz del portal.
    Si hay al menos uno, el cierre se aborta.

Sale con codigo 0 si NO hay cambios funcionales (cierre permitido) y 1 si los hay
(cierre bloqueado). Pensado para invocarse desde los .bat de cierre en Windows.

Uso:
    python check_git_cierre.py           # evalua el estado real del repo
    python check_git_cierre.py --test    # corre las pruebas de clasificacion

No hace git add/commit/push/stash ni modifica ningun archivo. Solo lee el estado.
"""
import subprocess
import sys

# --- Rutas operativas permitidas (clasificacion POR PREFIJO DE RUTA) -----------
# Todo lo que cuelga de estos arboles es dato operativo o dataset generado por el
# cierre. Cualquier otra ruta se considera cambio funcional y bloquea el cierre.
RUTAS_OPERATIVAS = (
    "01_INPUTS/",        # fuentes operativas (ventas, clientes, stock, acciones, etc.)
    "02_HISTORY/",       # snapshots historicos generados por el cierre
    "04_DATASETS_ORBIT/",  # datasets/CSVs que consume el portal, regenerados por el cierre
    "06_APP_DATA/",      # JSON de datos del portal generado por el proceso
    "07_CIERRES_MENSUALES/",  # salidas del cierre de mes
)


def normalizar_ruta(ruta):
    """Normaliza una ruta suelta: quita comillas, espacios y usa '/' siempre."""
    ruta = ruta.strip()
    # git puede envolver rutas con caracteres especiales entre comillas dobles.
    if len(ruta) >= 2 and ruta[0] == '"' and ruta[-1] == '"':
        ruta = ruta[1:-1]
    return ruta.replace("\\", "/").strip()


def rutas_de_linea(linea):
    """
    Extrae las rutas de una linea de `git status --porcelain`.

    - Descarta los 2 caracteres de estado XY y el espacio separador.
    - Soporta renombrados con formato 'ruta_anterior -> ruta_nueva' (2 rutas).
    - Devuelve la(s) ruta(s) ya normalizada(s).
    """
    if not linea:
        return []
    # Porcelain v1: [0:2]=estado, [2]=espacio, [3:]=ruta. Para '??' es identico.
    parte = linea[3:] if len(linea) > 3 else linea.strip()
    if " -> " in parte:
        anterior, nueva = parte.split(" -> ", 1)
        return [normalizar_ruta(anterior), normalizar_ruta(nueva)]
    ruta = normalizar_ruta(parte)
    return [ruta] if ruta else []


def es_operativa(ruta):
    """True si la ruta cae dentro de un arbol operativo permitido."""
    ruta = normalizar_ruta(ruta)
    return any(ruta.startswith(prefijo) for prefijo in RUTAS_OPERATIVAS)


def clasificar(lineas):
    """
    Clasifica lineas de porcelain en (operativas, funcionales).

    Una linea (incluido un renombrado) es funcional si CUALQUIERA de sus rutas
    cae fuera de las rutas operativas permitidas: mover un .py a 01_INPUTS/ o
    viceversa sigue siendo un cambio funcional.
    """
    operativas, funcionales = [], []
    for linea in lineas:
        rutas = rutas_de_linea(linea)
        if not rutas:
            continue
        etiqueta = " -> ".join(rutas) if len(rutas) > 1 else rutas[0]
        if all(es_operativa(r) for r in rutas):
            operativas.append(etiqueta)
        else:
            funcionales.append(etiqueta)
    return operativas, funcionales


def leer_estado_git():
    """Lee `git status --porcelain` con rutas sin escapar (quotePath=false)."""
    salida = subprocess.run(
        ["git", "-c", "core.quotePath=false", "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if salida.returncode != 0:
        sys.stderr.write("ERROR: no se pudo ejecutar 'git status'.\n")
        sys.stderr.write(salida.stderr or "")
        sys.exit(2)
    return [ln for ln in salida.stdout.splitlines() if ln.strip()]


def main():
    lineas = leer_estado_git()
    operativas, funcionales = clasificar(lineas)

    if operativas:
        print("Cambios OPERATIVOS permitidos (%d):" % len(operativas))
        for r in operativas:
            print("   [OK]  %s" % r)
    if funcionales:
        print("Cambios FUNCIONALES bloqueantes (%d):" % len(funcionales))
        for r in funcionales:
            print("   [!!]  %s" % r)

    if funcionales:
        print("")
        print("ERROR: Hay cambios FUNCIONALES pendientes fuera de las rutas operativas.")
        print("Codigo .py, .bat, portal.html o configuracion sin commitear.")
        print("Commitea o resolve esos cambios ANTES de cerrar.")
        return 1

    if not operativas:
        print("Repositorio sin cambios pendientes.")
    else:
        print("")
        print("OK: solo hay cambios operativos permitidos. Cierre habilitado.")
    return 0


# --- Pruebas de clasificacion (no tocan git) -----------------------------------
def _test():
    casos = [
        # (linea porcelain, es_funcional_esperado, descripcion)
        (" M 01_INPUTS/ventas.csv", False, "input operativo (unstaged)"),
        (" M 01_INPUTS/Stock/stock.xlsx", False, "input operativo en subcarpeta nueva"),
        ("M  01_INPUTS/resultado.xlsx", False, "input operativo (staged)"),
        ("?? 01_INPUTS/nuevo_input.csv", False, "input operativo nuevo (untracked)"),
        (" M 02_HISTORY/acumulado.csv", False, "snapshot generado"),
        (" M 04_DATASETS_ORBIT/mod_ccc_segmento.csv", False, "dataset generado"),
        (" M 06_APP_DATA/orbit_portal_data.json", False, "JSON de datos del portal"),
        (" M portal/data/dashboard.json", True, "JSON fuera de ruta generada -> bloquea"),
        (" M server_orbit.py", True, "codigo .py -> bloquea"),
        (" M portal.html", True, "interfaz -> bloquea"),
        ("M  CIERRE_DIA_ORBIT.bat", True, "script .bat -> bloquea"),
        (" M render.yaml", True, "config de deploy -> bloquea"),
        (" M requirements.txt", True, "dependencias -> bloquea"),
        (" M 01_INPUTS\\ventas.csv", False, "separador Windows normalizado"),
        ('R  "01_INPUTS/a.csv" -> "01_INPUTS/b.csv"', False, "renombrado operativo->operativo"),
        ("R  server_orbit.py -> nuevo.py", True, "renombrado de codigo -> bloquea"),
        ("R  01_INPUTS/x.csv -> tools/x.csv", True, "renombrado operativo->funcional -> bloquea"),
    ]
    ok = True
    for linea, esperado_funcional, desc in casos:
        _, funcionales = clasificar([linea])
        obtenido_funcional = len(funcionales) == 1
        estado = "OK " if obtenido_funcional == esperado_funcional else "FALLA"
        if obtenido_funcional != esperado_funcional:
            ok = False
        print("[%s] %-45s | %s" % (estado, desc, linea.strip()))

    # Escenario combinado: input operativo + un .py juntos -> bloquea solo por el .py
    ops, funcs = clasificar([" M 01_INPUTS/ventas.csv", " M server_orbit.py"])
    combo_ok = ops == ["01_INPUTS/ventas.csv"] and funcs == ["server_orbit.py"]
    print("[%s] %s" % ("OK " if combo_ok else "FALLA",
                        "combinado: ventas.csv permitido, server_orbit.py bloquea"))
    ok = ok and combo_ok

    print("")
    print("RESULTADO PRUEBAS:", "TODAS OK" if ok else "HAY FALLAS")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(_test())
    sys.exit(main())
