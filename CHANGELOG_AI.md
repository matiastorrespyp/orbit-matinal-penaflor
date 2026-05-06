# CHANGELOG AI - ORBIT MATINAL PEÑAFLOR

## Baseline

Se creó baseline inicial del proyecto antes de trabajar con Claude Code.

Reglas:
- Registrar cada cambio realizado por IA.
- Indicar archivo modificado.
- Indicar motivo.
- Indicar validación ejecutada.

---

## 2026-05-05 — Restaurar data.js (JavaScript)

**Archivo modificado:** `PAV MATINAL PE_A FLOR/data.js`

**Motivo:** El archivo contenía código Python (`tools/orbit_truth_audit.py`) en lugar de JavaScript. El browser lo ejecutaba y fallaba con error de parseo, dejando `window.ORBIT_DATA = undefined`. El componente React montaba inmediatamente sobre `data.diaActivo` y crasheaba. El portal `index.html` no cargaba en absoluto.

**Cambio:** Reemplazado con el contenido de `data.js.mock.bak`, que es el proveedor de datos JavaScript correcto: llama a `/api/diagnostico`, `/api/dashboard`, `/api/clientes`, `/api/alertas` y `/api/planificacion` vía XHR síncrono y construye `window.ORBIT_DATA` con datos reales.

**Validación:** El archivo ahora es JavaScript válido. El portal `index.html` puede parsear y ejecutar `data.js` sin error, y `window.ORBIT_DATA` queda construido desde las APIs Flask reales.

---

## 2026-05-05 — Corregir diaActivo en data.js

**Archivo modificado:** `PAV MATINAL PE_A FLOR/data.js`

**Motivo:** `diaActivo` estaba hardcodeado como `"MA"` (martes). El portal mostraba siempre el día incorrecto independientemente de la fecha real de la matinal.

**Cambio:** `diaActivo` se calcula dinámicamente como `abrev[fecha_corte + 1 día]`. Con `fecha_corte = 2026-05-05`, el resultado es `"MI"` (miércoles = mañana).

**Validación:** `window.ORBIT_DATA.diaActivo === "MI"` en consola del browser.

---

## 2026-05-05 — Corregir título hardcodeado en app.jsx

**Archivo modificado:** `PAV MATINAL PE_A FLOR/app.jsx`

**Motivo:** El título de la pantalla Dashboard mostraba `"Reunión matinal · Lunes 04/05"` — día y fecha incorrectos, hardcodeados.

**Cambio:** El título se construye dinámicamente desde `data.diaActivo` y `data.fechaCorta + 1 día`. Con los valores actuales produce `"Reunión matinal · Miércoles 06/05"`.

**Validación:** El portal muestra "Reunión matinal · Miércoles 06/05" en el encabezado del Dashboard.

---

## 2026-05-05 — Corregir semántica de CCC en data.js

**Archivo modificado:** `PAV MATINAL PE_A FLOR/data.js` (líneas 77-78)

**Motivo:** `mod_ccc_segmento.csv` es construido por el motor legacy desde `ventas_ayer` (ventas de HOY = fecha_ejecucion). Representa el CCC del día, no el CCC acumulado del mes. El campo `ccc_mes` recibía el valor real del día (engañoso), y `ccc_dia` estaba hardcodeado en 0 (incorrecto).

**Cambio:** `ccc_dia: tCCC` (valor real del día), `ccc_mes: 0` (honesto: sin fuente de CCC acumulado del mes disponible).

**Validación:** En el portal, "CCC DEL DÍA" muestra el valor real sumado desde `mod_ccc_segmento.csv`. "CCC ACUMULADOS" muestra 0, pendiente de fuente real.

---

## 2026-05-05 — Corrige acumulado=0 en build_avance_map (app_publish.py)

**Archivo modificado:** `app_publish.py` (línea 543)

**Motivo:** `build_avance_map()` buscaba la columna `"acumulado"` como primer candidato, pero `mod_volumen_vendedor.csv` tiene la columna `"acumulado_mes"`. Ningún candidato de la lista coincidía → `c_acum = ""` → `acumulado = 0.0` para todos los vendedores en `dashboard_vendedor.json`.

**Cambio:** Agregado `"acumulado_mes"` como primer candidato en la lista de `first_col()`.

**Validación:** `build_avance_map()` devuelve acumulados reales: V3=71.109 | V4=798.688 | V6=7.806.975 | V8=4.388.957 | V10=4.218.410. V7 y V9 ausentes del CSV (bug separado).

---

## 2026-05-05 — Fallback V7/V9 en /api/dashboard (server_orbit.py)

**Archivo modificado:** `server_orbit.py`

**Motivo:** V7 (Jofre) y V9 (Sanchez) no tienen clientes asignados en `clientes.xlsx` (codven 7 y 9 ausentes del maestro). El motor legacy los omite, dejando obj=0 y acum=0 en el dashboard. Los datos reales existen en `resultado.xlsx` (V7: obj=10.868.000 / acum=301.735 / avance=22,2%; V9: obj=46.332.000 / acum=16.712.863 / avance=288,6%).

**Cambio:** Al iniciar `/api/dashboard`, se carga `resultado.xlsx` hoja "Avance" en un dict de fallback. Cuando un vendedor de `vendedores_activos.csv` no tiene filas en `mod_volumen_vendedor.csv`, se usan los valores del fallback. El campo `"sin_maestro": true` en la respuesta identifica el origen. Vendedores con datos en CSV no son afectados.

**Validación:** V7 y V9 aparecen en `/api/dashboard` con datos reales de avance. CCC, clientes y ruta quedan en 0 (correcto: sin maestro de clientes).

**Deuda pendiente:** agregar clientes de V7 y V9 a `clientes.xlsx` con codven, Ramo y DiasVisita correctos para que el motor legacy los procese.

---

## 2026-05-06 — Bloque B: eliminar datos hardcodeados del frontend

**Archivos modificados:**
- `PAV MATINAL PE_A FLOR/screens/dashboard.jsx`
- `PAV MATINAL PE_A FLOR/app.jsx`

**Motivo:** El frontend contenía cinco datos inventados o con nombre de persona real que violaban la regla "no inventar datos":
1. `cccSpark = [3,7,9,12,8,15,18,22,19,24]` — array mock sin fuente, mostraba una sparkline inventada en "CCC ACUMULADOS".
2. Sparkline CCC consumía ese array mock vía `React.createElement(Sparkline,{data:cccSpark,...})`.
3. `hint:"Cierre proyectado al 30/05"` — fecha de cierre fija, incorrecta si el mes cambia.
4. Sidebar footer con `"MR"` / `"Manuel R."` / `"Supervisor PyP"` — nombre de persona real.
5. Topbar con `"Vista mobile · Milagros Ortega"` — nombre de persona real.

**Cambios aplicados:**
- `dashboard.jsx` línea 12: `cccSpark = null`.
- `dashboard.jsx` línea 14: agregado `cierreProyectado` calculado desde `data.fechaCorta` — deriva el último día del mes real con `new Date(año, mes+1, 0)`.
- `dashboard.jsx` línea 46: `hint: cierreProyectado` (dinámico).
- `dashboard.jsx` línea 61: `spark: null` (no muestra Sparkline sin fuente).
- `app.jsx` líneas 41-43: avatar `"SV"`, nombre `"Supervisor"` (sin persona real).
- `app.jsx` línea 59: `"Vista mobile · vendedor"` (sin persona real).

**No se modificó:** backend, `data.js`, CSV, `app_publish.py`.

**Validación:** `git diff` confirma 7 inserciones / 6 borrados exclusivamente en los dos archivos JSX. Sin mock data ni nombres de persona en el frontend.
