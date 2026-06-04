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
