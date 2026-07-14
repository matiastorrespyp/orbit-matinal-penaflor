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

---

## ERR-011 — "Hice la pantalla pero no la veo en Render" = caché del navegador

**Detectado:** 2026-07-06  
**Síntoma:** El usuario había hecho la pantalla **Stock sin Venta** (commit `994efea`) y no la veía en gerencia (trabaja solo en Render, no en local).  
**Diagnóstico (sin tocar código):** el ítem de menú es HTML estático en `portal.html:1059`, sin filtro de rol → debe aparecer siempre. Los commits ya estaban en `origin/master` y `stock.xlsx` (102 KB) trackeado; el endpoint carga el xlsx *lazy*, no al arranque → no tumba el boot. **Prueba discriminante:** los datos del cierre de hoy **sí** se veían en Render pero el botón **no** → el servidor servía código nuevo y el navegador servía el `portal.html` viejo cacheado.  
**Causa raíz:** **caché del navegador** (no era código ni deploy).  
**Solución:** **hard refresh** (`Ctrl+Shift+R`) o ventana de incógnito. Confirmado por el usuario.  
**Estado:** ✅ Resuelto.  
**Lección / diagnóstico rápido:** ante "no aparece en Render", primero discriminar: si los **datos** frescos (cierre del día) **sí** se ven pero el **elemento nuevo de UI no** → es caché del navegador (`portal.html` es estático), se resuelve con `Ctrl+Shift+R`. Solo si **tampoco** se ven los datos frescos → mirar el deploy en Render (Events/Deploys, commit efectivo, deploy fallido). No asumir "deploy roto" cuando el síntoma es solo de la capa de UI.

## ERR-012 — `/api/gerencia/cierre_mes` da HTTP 500 por `ventas_mes.csv` en `;` leído con `sep=','`

**Detectado:** 2026-07-06 (mientras se validaba el cambio de 11T por superficie; **preexistente**, no lo introdujo ese cambio).  
**Síntoma:** `GET /api/gerencia/cierre_mes` → 500. Traceback: `pandas.errors.ParserError: Expected 11 fields in line 7, saw 13` en `_leer_ventas_mes_csv` (línea del sell-out del cierre), **antes** de llegar al bloque 11T.  
**Causa raíz:** `01_INPUTS/ventas_mes.csv` está delimitado por **`;`** (58 columnas, 0 comas en el header), pero `_leer_ventas_mes_csv` lo lee con **`sep=','`**. Los decimales tipo `6620,94` generan filas con distinta cantidad de campos → ParserError. El lector fue pensado para un `ventas_mes.csv` con coma; el archivo vivo hoy es semicolon.  
**Prueba de que es preexistente:** se copió `server_orbit.py` de **HEAD (git)** al directorio real del proyecto y `cierre_mes` **también dio 500**. La falsa impresión inicial de "HEAD daba 200" fue porque al cargar HEAD desde el scratchpad, su `INPUTS` resolvía a una carpeta sin `ventas_mes.csv` (saltaba el sell-out).  
**Estado:** ⏳ Pendiente (anotado en `NEXT_TASK.md`, fuera del alcance de la tarea de 11T).  
**Solución propuesta:** que `_leer_ventas_mes_csv` **autodetecte** el separador (`;` vs `,`) —o `sep=None`+`engine='python'`— o regenerar `ventas_mes.csv` con coma. La pantalla **Cierre de Mes** queda caída hasta entonces.  
**Lección:** al comparar "mi versión vs HEAD" cargando módulos desde rutas distintas, verificar que `BASE`/`INPUTS` (derivados de `__file__`) apunten al **mismo** directorio de datos; si no, la comparación es inválida.

---

## ERR-013 — El maestro 04D estaba congelado: ventas sin categoría, 0 litros y alertas de descuento FALSAS

**Detectado:** 2026-07-14 (al construir el buscador de producto→acción, que consulta el maestro de frente)
**Síntoma:** el buscador marcaba **83 SKU "sin categoría en el maestro"**. Los vendedores recibían alertas de sobre-descuento del tipo *"descuento aplicado 8% / máximo 0,0% — sin acción aplicable"* sobre productos con descuento **normal**.
**Causa raíz:** `09_CONFIG/maestro_04D_productos.csv` quedó congelado en **258 códigos** y le faltan **82 SKU vigentes que sí se venden** (Alaris D.Cosecha, Dada Sweet Red, Los Arboles Rosado, Smirnoff BC…). Una venta cuyo código no está en el maestro sale con `_cat = NaN`, `_linea = ""` y sin litros/caja → no matchea las reglas por categoría de las acciones, se descarta del sell out (`Categoria.notna()`), aporta **0 L**, y como "no hay acción aplicable" su descuento máximo permitido queda en **0%** → **alerta falsa**. Impacto: **60 líneas / $1.386.829 (2,1% del importe del mes)**.
**Cómo detectarlo:** si una alerta de descuento dice `máximo 0.0% (sin acción aplicable)` sobre un producto que claramente entra en una acción del mes, el sospechoso es el maestro, no la acción. Verificar con `_cargar_maestro_04D()` si el `Codigo` está.
**Solución aplicada:** el 04D se **completa** con `01_INPUTS/RAW_PRODUCTOS/productos<mes>.xlsx` (`_maestro_mes_productos()` en `server_orbit.py` y su gemelo en `generar_datasets_acum.py`). El 04D manda donde tiene dato; el mes agrega los faltantes. **258 → 340 códigos.** Alertas 162 → **151** (las 11 eliminadas eran falsas; los sobre-descuentos reales siguen alertando). Sell out 9.038 → 9.139 L y aparece la categoría **Vodka**, que faltaba entera.
**Trampa:** `producto activos.xlsx` **no** arregla esto — es la misma lista vieja (257 códigos) y cubre menos ventas.
**Commit:** 9e15b40
**Estado:** ✅ Resuelto. Pendiente: subir el export de productos **todos los meses** a `RAW_PRODUCTOS/`, y dar de alta el código `20305` (no está en ningún maestro).
