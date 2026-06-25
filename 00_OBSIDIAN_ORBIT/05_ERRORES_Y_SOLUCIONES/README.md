# Errores Conocidos y Soluciones

Registro de errores ya diagnosticados, con causa raíz y solución aplicada o pendiente.

---

## ERR-001 — CCC Mes usaba historial completo (no mes actual)

**Detectado:** 2026-05-14  
**Síntoma:** Portal mostraba CCC Mes = 258 cuando el valor real de mayo era 311.  
**Causa raíz:** `clientes_dia.ccc_mes_flag` se genera desde `historial_ventas` sin filtro de mes calendario. Incluía compradores de abril.  
**Solución aplicada:** `/api/dashboard` y `/api/vendedor/<vid>` ahora leen `ventas.csv` del mes actual directamente via `_cargar_ventas_mes_actual()`. No se modificó el motor legacy.  
**Commit:** c3de7aa  
**Estado:** ✅ Resuelto en endpoints. Motor legacy (Bug 1) pendiente Etapa B.

---

## ERR-002 — Cobertura % usando denominador Vi y numerador desfasado

**Detectado:** 2026-05-14  
**Síntoma:** Portal mostraba "Cobertura 47%" = 257/548, usando clientes_dia (solo Vi) como denominador y cobertura_mes_flag (historial) como numerador.  
**Causa raíz:** `cobG = 1 - (tP/tC)` en portal.html donde tP = `clientes_sin_compra_mes` (historial con posible mezcla de meses) y tC = suma de `clientes_planificados` (solo Vi).  
**Solución aplicada (Etapa A):** Se eliminó el % de cobertura del dashboard. Se reemplazó la tarjeta por "Planificados Vi: 548 / Sin compra Vi: 290" (números crudos, sin porcentaje).  
**Estado:** ⏳ Parcial. Pendiente calcular cobertura real desde ventas.csv mes actual + clientes.xlsx (Etapa C).

---

## ERR-003 — botellas_dia > botellas_mes (absurdo)

**Detectado:** 2026-05-14  
**Síntoma:** botellas_dia = 16674, botellas_mes = 15628. Día mayor que mes es imposible.  
**Causa raíz:** `botellas_dia` venía de `mod_ccc_segmento` (empresa completa, ayer). `botellas_mes` venía de `clientes_dia.botellas_mes` (solo clientes Vi, acumulado parcial).  
**Solución aplicada (Etapa A):** `botellas_mes = null` en `/api/diagnostico`. No se muestra en el portal.  
**Estado:** ✅ Eliminado de display. Pendiente calcular botellas_mes real desde ventas.csv.

---

## ERR-004 — Motor legacy no filtra mes calendario en ventas_mes

**Detectado:** 2026-05-14  
**Síntoma:** `clientes_sin_compra_mes` y `ccc_mes_flag` en datasets incluyen ventas de meses anteriores.  
**Causa raíz:** `LEGACY/orbit_matinal_v42.py` línea ~919: `ventas_mes = historial_ventas.loc[fecha_comprobante <= fecha_ejecucion]` — no filtra por mes actual, acumula todo el historial hasta hoy.  
**Solución pendiente (Etapa B):** Agregar filtro `fecha_comprobante >= primer_dia_mes_actual` en la línea ~919 del motor.  
**Riesgo:** Puede afectar AppSheet, PDFs y otros consumidores del dataset. Validar antes de modificar.  
**Estado:** ⏳ Pendiente aprobación para Etapa B.

---

## ERR-005 — $pid reservado en PowerShell

**Detectado:** Durante sesión de trabajo  
**Síntoma:** Script PowerShell falla con error en `$pid`.  
**Causa raíz:** `$pid` es una variable automática de PowerShell (Process ID del proceso actual). No se puede usar como variable de usuario.  
**Solución:** Usar `$procId` u otro nombre.  
**Estado:** ✅ Documentado. Usar siempre `$procId`.

---

## ERR-006 — Ruta con ñ en nombre de carpeta

**Detectado:** Durante sesión de trabajo  
**Síntoma:** Script Python falla al acceder a `PAV MATINAL PEÑA FLOR`.  
**Causa raíz:** El nombre real de la carpeta en el repo es `PAV MATINAL PE_A FLOR` (con guión bajo, no ñ). Git convirtió la ñ al hacer checkout en Windows.  
**Solución:** Siempre verificar el nombre exacto con `Get-ChildItem` antes de referenciar la carpeta. Usar `PAV MATINAL PE_A FLOR` en todo el código.  
**Estado:** ✅ Documentado. Verificar con PowerShell antes de usar rutas.

---

## ERR-007 — Múltiples instancias de server_orbit.py

**Detectado:** Durante sesiones de trabajo  
**Síntoma:** Puerto 8502 responde pero con datos desactualizados; hay 3-4 procesos `server_orbit.py` corriendo.  
**Causa raíz:** Start-Process en Windows puede generar múltiples procesos Python. Las instancias anteriores no mueren correctamente.  
**Solución:** Antes de iniciar el servidor, usar `Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%server_orbit%'"` para detectar todas las instancias y matarlas por PID antes de arrancar una nueva.  
**Estado:** ✅ Documentado. Procedimiento estándar de arranque.

---

## ERR-008 — Panel "Cierre de Mes" mezclaba cierre histórico con vista dinámica

**Detectado:** 2026-06-03  
**Síntoma:** La pantalla gerencial "Cierre de Mes" mostraba datos del cierre histórico mezclados con una "Vista dinámica" que recalculaba al vuelo; además el ganador de 11 Titulares (V3 NADIA GAMBINO) no era visible.  
**Causa raíz:** El panel consumía `/api/gerencia/cierre_mes` (recalcula desde `resultado.xlsx` + `ventas_acumulada.csv`, fuentes vivas/cambiantes) en lugar del cierre congelado. El endpoint histórico solo exponía `ranking_top3` (general), y V3 es 5° general → su victoria en 11T quedaba oculta.  
**Solución aplicada:** (1) `/api/gerencia/cierres_historicos` extendido de forma aditiva/solo-lectura con `empresa`, `ranking` completo y `ganadores` por categoría (lee `cierre_mensual_resumen.json` y `ranking_vendedores_mes.json`). (2) `portal.html`: pantalla "Cierre de Mes" 100% histórica, eliminada la vista dinámica y todo consumo de `/api/gerencia/cierre_mes`.  
**Commit:** b097300  
**Estado:** ✅ Resuelto y validado en Render. Regla: cierres oficiales = solo artefactos versionados, sin recalcular (ver `08_ARQUITECTURA/README.md`).

---

## ERR-009 — Acciones Comerciales (gerencia) daba HTTP 500 en Render por timeout del worker

**Detectado:** 2026-06-23  
**Síntoma:** La pantalla de Acciones Comerciales no cargaba en gerencia. `/api/gerencia/acciones_mes` → **HTTP 500 a los ~30,9s** en Render; `/api/vendedor/<id>/acciones_mes` → 200 (10s). En local: 200 en 5,2s, tipos nativos OK (no era bug de lógica ni de serialización).  
**Causa raíz:** La vista gerencia (sin filtro) corre las **28 acciones sobre toda la venta** y tardaba **>30s** en el Render de 0.5 vCPU. El **timeout default de gunicorn (30s)** mataba el worker; como nunca completaba, el payload **nunca se cacheaba** (`_ACC_MES_CACHE`) → 500 permanente. La vendedor (datos filtrados, ~10s) sí entraba. Descartado OOM: el dataset son 2.787 filas / 2,5 MB. El cuello: `_match` evaluaba el predicado de producto con `sub.apply(..., axis=1)` **fila por fila** (62.510 llamadas, ~5s local).  
**Solución aplicada:** (1) `_match` evalúa `pred()` **una vez por combinación única** de `(_cat,_linea,_art,_marca,_cod)` y mapea a las filas (resultado idéntico, 5,2s→3,86s local). (2) Hilo daemon `_warm_caches()` que precalienta el payload gerencia al arranque (el boot no tiene timeout HTTP) → la 1ª request del gerente cae en caché.  
**Pendiente operativo:** El **Start Command en el dashboard de Render está vacío** y el servicio **no es Blueprint** → ignora `render.yaml`/`Procfile` y usa el default de gunicorn (timeout 30s). Setear a mano:  
`gunicorn server_orbit:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --threads 8 --worker-class gthread`  
**Commits:** `c8bd8d8` (código). **Estado:** ✅ Resuelto y validado en vivo (200, 0.6-1.7s). ⏳ Falta blindar el `--timeout 120` en el dashboard.  
**Lección:** un endpoint pesado que **no cachea porque time-outea** falla siempre; en Render verificar el Start Command efectivo (si está vacío y no hay Blueprint, NO se aplican `render.yaml`/`Procfile`). Diagnóstico rápido: si el 500 llega a ~30s exactos → es el timeout del worker, no un exception.

---

## ERR-010 — El Cierre del Día "se colgaba" en el PASO 1 (motor legacy)

**Detectado:** 2026-06-25  
**Síntoma:** `CIERRE_DIA_ORBIT.bat` quedaba trabado en `[5/8] Ejecutando motor legacy`, sin avanzar. Los logs `99_LOGS_ORBIT/regenerar_datos_*.log` del día pesaban ~976 bytes y se cortaban justo en esa línea (los días que sí completaban pesaban ~23 KB). **No era el `.bat`** (estructura, CRLF y `FUNC_PEND` estaban bien).  
**Diagnóstico:** correr el motor con `py -u test_legacy_run.py` + `faulthandler.dump_traceback_later(30, repeat=True)`. El volcado mostró el cuelgue exacto en `LEGACY/orbit_matinal_v42.py` → `cargar_productos()` (línea ~898) → `pd.read_excel` → openpyxl parseando XML. (Cero output con `-u` = se cuelga **antes** del primer print, no es buffering.)  
**Causa raíz (2 cuellos):**  
  1. **`01_INPUTS/producto activos.xlsx` inflado a 19,2 MB.** Tenía solo **260 filas reales** pero el "rango usado" de Excel llegaba hasta la fila **1.048.527** (~1 millón de filas vacías fantasma, típico de un export sucio de Gescom). `pd.read_excel` recorría TODAS → minutos por lectura (solo iterarlas en read_only tardaba 87s).  
  2. Pasado eso, la sección **"11 TITULARES"** (`~1367-1381`) evaluaba el match con `marcas_mes.apply(..., axis=1)` **fila por fila** por cada (cliente × marca objetivo) → O(N×M×K). Crecía con los datos del mes/trimestre y dominaba el tiempo.  
**Solución aplicada:**  
  1. Reparado el archivo dejando solo el rango real: **19,2 MB → 17,8 KB**, lectura 0,08s. Backup del original en `99_BACKUPS_ORBIT/producto_activos_bloated/` (gitignored → no frena el cierre). Equivalencia validada celda a celda (idéntico salvo ruido de float inocuo en litros).  
  2. Vectorizado el 11T: pre-filtra `marcas_mes` por `(cliente_id, vendedor_codigo)` una vez por cliente (mismo `==`, mismo NaN→False) y `match_marca_objetivo` corre solo sobre el subconjunto del cliente. `mod_11_titulares` validado **idéntico** (5910×17, sumas iguales). **Motor 338s → 32s.**  
**Commits:** `095c9df` (perf 11T) + reparación del xlsx (archivo gitignored, no commiteable).  
**Estado:** ✅ Resuelto. El cierre corre completo y rápido.  
**Prevención / lección:** si `producto activos.xlsx` vuelve a pesar **>1 MB para ~260 productos**, está inflado y volverá a ralentizar el cierre → reexportarlo limpio de Gescom (o re-reparar el rango usado). Regla general: cualquier `.xlsx` de input que de golpe pese de más probablemente arrastra filas/columnas fantasma; openpyxl lee TODO el rango usado. Diagnóstico de cuelgues del motor: `faulthandler` + `py -u`.
