# CHANGELOG AI - ORBIT MATINAL PEÑAFLOR

## 2026-05-14 — Cierre de sesión: rediseño portal + endpoint vendedor real

**Commit:** `c67e70e feat(matinal): rediseñar portal y agregar endpoint vendedor real`

**Archivos commiteados:**
- `PAV MATINAL PE_A FLOR/portal.html` — rediseño completo del portal
- `server_orbit.py` — nuevo endpoint `/api/vendedor/{id}`
- `test_portal.py` — script Playwright: 8 screenshots de flujo completo
- `test_kpis.py` — script Playwright: validación KPIs vendedor V3

**Archivos excluidos del commit (no productivos):**
- `PAV MATINAL PE_A FLOR/portal.html.bak.2026-05-14` — backup previo al rediseño
- `01_INPUTS/` — datos ERP del día (actualización diaria, no se commitean)
- `02_HISTORY/` — historial de ventas (actualización diaria, no se commitea)
- `screenshots/` — capturas de validación Playwright
- `.claude/settings.local.json` — configuración local de sesión

**Qué se logró:**
1. Rediseño completo de `portal.html`: dos portales distintos (gerencial desktop-first + vendedor mobile-first 390px), login unificado con routing por rol, design system dark con magenta #E2147A, Sora + Inter, semáforos ok/wn/bd.
2. Nuevo endpoint `GET /api/vendedor/{id}` en `server_orbit.py`: devuelve KPIs reales por vendedor (objetivo, acumulado, avance_pct, CCC por segmento, 11 Titulares por vendedor, clientes). Fuentes: `mod_volumen_vendedor.csv`, `mod_ccc_segmento.csv`, `mod_11_titulares.csv`, `vendedores_activos.csv`.
3. Regla V3 aplicada en servidor: `ccc_autoservicio = 0`, `trabaja_autoservicio = false`. El portal oculta la columna AUTOSERV. en el grid CCC cuando `trabaja_autoservicio === false`.
4. 11 Titulares ahora usa `D.det.titulares11` (por vendedor, del nuevo endpoint) con fallback a `D.diag.titulares11` (empresa).
5. Corrección de field names API: `ccc_total`, `once_titulares_cumplidos`, `titulares11.marca`, `titulares11.cubiertos`, `titulares11.objetivo`.

**Validación ejecutada:**
- `test_portal.py`: 8 screenshots OK — login, gerencia (dashboard/vendedores/alertas), vendedor (inicio/ruta/KPIs/alertas).
- `test_kpis.py` V3: TRADICIONAL OK | AUTOSERV FALTA (correcto, V3 no trabaja AS) | Avance vs OK | 11 Titulares OK.
- `/api/vendedor/V3`: vendedor_nombre=NADIA GAMBINO, ccc_tradicional=2, ccc_autoservicio=0, trabaja_autoservicio=false, titulares11=11 marcas, modo_datos=REAL.
- Único error JS: `404 /favicon.ico` — cosmético, aprobado.

---

## 2026-05-14 — Rediseño completo portal.html (frontend-design)

**Archivo modificado:**
- `PAV MATINAL PE_A FLOR/portal.html` — rediseño total del portal web

**Backup creado:**
- `PAV MATINAL PE_A FLOR/portal.html.bak.2026-05-14`

**Motivo:**
- El portal anterior tenía diseño funcional pero básico (emojis como iconos de nav, KPI cards sin semáforo, vista vendedor como phone-stage estático).
- Se rediseñó para soporte de dos portales distintos: Gerencial (desktop-first) y Vendedor (mobile-first).

**Cambios realizados:**
- Login: nuevo diseño premium con gradiente radial, fuentes Sora/Inter, botón magenta con glow.
- Portal Gerencial: sidebar oscura con nav activo (barra magenta), topbar con breadcrumb + selector de día + selector de vendedor, 6 KPIs reales en header, ranking de vendedores con progress bars y semáforo ok/wn/bd, cobertura por segmento, alertas críticas, clientes sin compra.
- Portal Vendedor: mobile 390px con header personal, bottom nav (Inicio/Ruta/KPIs/Alertas), KPI "Te falta para el objetivo", grid 2×2 con CCC/11T/Pendientes/Total, lista de clientes de ruta ordenada sin-compra primero, oportunidades sugeridas, 11 Titulares con semáforo por marca.
- Corrección de nombres de campo reales de la API: `ccc_total`, `once_titulares_cumplidos`, `titulares11.marca`, `titulares11.cubiertos`, `titulares11.objetivo`.
- Fallback para `/api/vendedor/{id}` (404): usa datos del dashboard para CCC por segmento.

**Validación ejecutada:**
- Playwright con Chrome del sistema: 8 screenshots capturados.
- HTTP 200 en login, dashboard, vendedores, alertas, inicio vendedor, ruta, KPIs, alertas vendedor.
- Errores JS: 2 errores 404 no funcionales (favicon.ico + /api/vendedor/id — endpoint pendiente de implementar en servidor).
- Datos reales verificados: $106.1M acumulado compañía, 7 vendedores, ranking con avances reales, 31 alertas, segmentos TRAD/AS/OP.

---

## Baseline

Se creó baseline inicial del proyecto antes de trabajar con Claude Code.

Reglas:
- Registrar cada cambio realizado por IA.
- Indicar archivo modificado.
- Indicar motivo.
- Indicar validación ejecutada.

---

## 2026-05-12 — Módulo VDA completo (PROMPT_004)

**Archivos creados:**
- `_tmp_auditoria_vda.py` — script temporal de análisis VDA (lectura pura, no modifica portal ni Flask)
- `04_DATASETS_ORBIT/diagnostico_productos_activos.md`
- `04_DATASETS_ORBIT/mod_vda_productos.csv` — 93 productos VDA
- `04_DATASETS_ORBIT/mod_vda_productos_revision_necesaria.csv` — 160 no-VDA
- `04_DATASETS_ORBIT/mod_vda_ventas_base.csv` — 57,280 filas VDA (historial + ventas actuales)
- `04_DATASETS_ORBIT/mod_vda_resumen_mensual.csv`
- `04_DATASETS_ORBIT/mod_vda_clientes_detalle.csv` — 764 clientes
- `04_DATASETS_ORBIT/mod_vda_ranking_vendedor.csv` — 8 vendedores
- `06_APP_DATA/vda_clientes_ganados.json`
- `MODULO_VDA_CLIENTES_GANADOS_2026-05-12.md`

**Motivo:** PROMPT_004. Validar `producto activos.xlsx` y generar módulo VDA (clientes ganados/perdidos/retenidos).

**Bugs encontrados y resueltos:**
1. `decimal=","` faltaba en `read_csv_safe()` — sin él, `ImporteNetoItem` leía `"15491,87"` como string → NaN → solo 838/129k filas pasaban el filtro `> 0`. Con el fix: 103,508 filas válidas y 57,280 VDA.
2. Type mismatch en `isin()` — `cli_act/cli_ant` eran `set(str)` pero `detalle["cliente"]` era float → todos los estados resultaban `"sin_compra_vda"`. Fix: normalizar a `set(int)` con `.dropna().astype(int)`.

**Resultados finales:**
- Mes actual (2026-05, parcial): **152 clientes VDA**, $20,649,331, 4,957.5 L
- Mes anterior (2026-04): **727 clientes VDA**, $62,056,558, 15,288.75 L
- Ganados/recuperados: **37** · Perdidos: **612** · Retenidos: **115** · Balance: **-575**
- Alerta: balance negativo esperado (mayo incompleto al 12/05)
- Anomalía: V20 aparece con 2 clientes VDA — no está en la lista de vendedores activos, requiere validación

**Validación:** Script ejecutado sin errores. Todos los archivos generados con datos reales.

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

## 2026-05-06 — Bloque C: corrige importe_mes/botellas_mes = 0 en clientes_dia

**Archivo modificado:** `LEGACY/orbit_matinal_v42.py` (línea 784)

**Causa raíz:** `ventas_mes` se construía desde `ventas_validas` (fuente: `ventas.csv`, solo 2 días: 2026-05-04/05). Los 255 clientes de `clientes_dia` visitan el miércoles; ninguno compró el lunes/martes. El join `clientes_dia.merge(agg_mes, on=["cliente_id","vendedor_codigo"])` devolvía NaN en el 100% de las filas → `fillna(0)` → 0 para todos.

**Dato clave:** el motor ya acumulaba el historial en `02_HISTORY/historial_ventas_cliente.csv` (4.913 filas, desde 2026-03-27 hasta 2026-05-05) pero no lo usaba para `ventas_mes`.

**Cambio:**
```python
# ANTES
ventas_mes = ventas_validas.loc[ventas_validas["fecha_comprobante"] <= fecha_ejecucion].copy()

# DESPUÉS
ventas_mes = historial_ventas.loc[
    historial_ventas["fecha_comprobante"] <= fecha_ejecucion.date()
].copy().rename(columns={"marca": "marca_final", "articulo": "articulo_final"})
```
El rename es necesario porque el historial normaliza `marca_final`→`marca` y `articulo_final`→`articulo` al persistir.

**No se modificó:** `ventas_ayer` (sigue usando `ventas_validas` — correcto: representa el día fresco).

**Validación:** `03_OUTPUTS/MATINAL_PENA_V42.xlsx` hoja `clientes_dia`:
- `importe_mes > 0`: 175/255 (antes: 0/255)
- `botellas_mes > 0`: 175/255 (antes: 0/255)
- `importe_ayer > 0`: 0/255 (correcto — clientes MI no compraron el martes)
- Suma `importe_mes`: $26.608.333

---

## 2026-05-06 — Incorporación de V7 y V9 al maestro de clientes

**Archivos modificados:**
- `01_INPUTS/clientes.xlsx` (actualización manual del usuario)
- `03_OUTPUTS/MATINAL_PENA_V42.xlsx` (regenerado por motor)
- `04_DATASETS_ORBIT/*.csv` (regenerados por adaptador)

**Motivo:** V7 (Jofre) y V9 (Sanchez) estaban ausentes del maestro `clientes.xlsx`. El motor los omitía completamente; el fallback en `server_orbit.py` los mostraba con datos de `resultado.xlsx` pero sin rutas, clientes ni cobertura.

**Cambio:** El usuario actualizó manualmente `clientes.xlsx` (+280 filas: 302 clientes para V7, 355 para V9). Se ejecutó el pipeline completo:
1. `python LEGACY/orbit_matinal_v42.py` → clientes del día: 255→400, vendedores resumidos: 5→7
2. `python src/orbit/datasets/datasets_orbit.py` → 11 CSVs regenerados en `04_DATASETS_ORBIT/`

**Validación:**
- `mod_volumen_vendedor.csv`: V7 y V9 con filas propias, sin `[fallback]`
- `clientes_dia.csv`: V7=132 clientes MI / V9=13 clientes MI
- `importe_mes > 0`: 196/400 clientes (antes: 175/255)
- 2 clientes de V7 y 8 de V9 sin `DiasVisita` — deuda menor, no crítica

**Nota:** `acciones_comerciales.csv` detectado como modificado — se integrará en bloque separado.

---

## 2026-05-06 — Bloque D: segmentos y titulares11 desde fuente real

**Archivos modificados:**
- `server_orbit.py` (función `diagnostico()`)
- `PAV MATINAL PE_A FLOR/data.js`

**Motivo:** `data.js` tenía hardcodeados `segmentos` (clientes=279/43/21, cubiertos=0 para los tres) y `titulares11` (solo 2 marcas con cubiertos=0). Los datos reales existían en `mod_ccc_segmento.csv` y `mod_11_titulares.csv` pero `/api/diagnostico` no los exponía.

**Cambios en `server_orbit.py`:**
- Se agregan `segmentos` al response de `/api/diagnostico`: lee `mod_ccc_segmento.csv` para `coberturas_logradas` y `clientes_dia.csv` para el total de clientes por segmento.
- Se agrega `titulares11` al response: agrupa `mod_11_titulares.csv` por `marca_objetivo`, suma `tiene_flag` para cubiertos, ordena por cubiertos descendente.

**Cambios en `data.js`:**
- `segmentos` → `diag.segmentos || [fallback vacío]`
- `titulares11` → `diag.titulares11 || []`
- `ccc_mes: 0` sin cambio (honesto, sin fuente).

**Validación `/api/diagnostico`:**
- TRADICIONAL: 330 clientes, 12 cubiertos
- AUTOSERVICIO: 40 clientes, 12 cubiertos
- ON_PREMISE_VTK: 30 clientes, 1 cubierto
- titulares11: 28 marcas, top: Alma Mora 66/398, Cazador 19/353

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

---

## 2026-05-06 — Bloque E: registra reglas comerciales Mayo 2026 y restaura acciones_comerciales.csv

**Archivos incluidos:**
- `09_CONFIG/acciones_comerciales.csv` — restaurado a texto CSV (había sido reemplazado por un Excel .xlsx disfrazado)
- `09_CONFIG/reglas_acciones_mayo_2026_orbit.csv` — nuevo: 31 reglas comerciales de Mayo 2026 extraídas de la hoja `01_REGLAS_ACCIONES`
- `06_APP_DATA/reglas_acciones_mayo_2026_orbit.json` — nuevo: mismas 31 reglas en formato JSON
- `09_CONFIG/acciones_mayo_2026_formato_gastos_orbit.xlsx` — nuevo: plantilla de control de gastos por acción

**Motivo:** `09_CONFIG/acciones_comerciales.csv` fue reemplazado por un Excel de 4 hojas con datos de Mayo 2026. Esto rompía silenciosamente `config_comercial.py._read_csv()` → `OrbitConfigComercial.acciones_comerciales` quedaba vacío → `alertas_reales_orbit.py` perdía la configuración de acciones sugeridas por tipo de alerta.

**Cambio:**
- Restaurado `acciones_comerciales.csv` al CSV original (8 filas, 6 columnas: `tipo_alerta`, `prioridad`, `accion_sugerida_default`, `max_marcas_sugeridas`, `activa`, `comentario`). Encoding: latin-1. Legible por `config_comercial.py`.
- Extraída hoja `01_REGLAS_ACCIONES` del Excel como CSV real UTF-8 (`reglas_acciones_mayo_2026_orbit.csv`): 31 filas, 27 columnas con `accion_id`, `tipo_accion`, `canal`, `descuento_pct`, `cantidad_min/max`, etc.

**No integrado todavía:** consumidor de `reglas_acciones_mayo_2026_orbit.csv` en el motor. `02_PLANTILLA_GASTOS` del Excel queda fuera del scope de este bloque.

**Validación:** `pd.read_csv('09_CONFIG/acciones_comerciales.csv', encoding='latin-1')` devuelve 8 filas con schema correcto. `09_CONFIG/acciones_comerciales.csv` no aparece en `git diff`.

---

## 2026-05-06 — Bloque H (portal): gastosAccion en data.js y dashboard.jsx

**Archivos modificados:** `PAV MATINAL PE_A FLOR/data.js`, `PAV MATINAL PE_A FLOR/screens/dashboard.jsx`

**Motivo:** Conectar `/api/gastos_accion` al portal gerencial para mostrar exceso de descuentos por acción y por vendedor en la vista Dashboard.

**Cambio en `data.js`:** Agrega `fetchSync("/api/gastos_accion")` y expone `window.ORBIT_DATA.gastosAccion` con `resumen`, `top_acciones` y `top_vendedores`.

**Cambio en `dashboard.jsx`:** Nuevo bloque IIFE al final de `ScreenDashboard` con 3 cards en `grid cols-12`:
- Card resumen: exceso total ($231.133), gasto real ($444.782), vendedores alertados (4), clientes afectados (38), acciones CSV/fallback.
- Card top 5 acciones: `accion_id` abreviado, canal, categoría, exceso en pesos.
- Card top 5 vendedores: código, nombre, exceso en pesos, cantidad de acciones con exceso.
- Se oculta automáticamente si `resumen.filas_con_exceso` es falsy (cero o ausente).

**Validación:** `/api/dashboard` y `/api/diagnostico` sin cambios. `window.ORBIT_DATA.gastosAccion.top_acciones.length === 5`, `top_vendedores.length === 4`.

**Commit:** `c3f7813`

---

## 2026-05-06 — Bloque H: /api/gastos_accion en server_orbit.py

**Archivo modificado:** `server_orbit.py`

**Motivo:** Exponer `mod_gastos_accion.csv` vía API para que el portal gerencial pueda mostrar gastos por acción comercial. El CSV ya existía (generado por `datasets_orbit.py` desde el Excel del motor), sin consumidor hasta esta sesión.

**Cambio:** Nuevo endpoint `GET /api/gastos_accion` agregado antes de `/api/orbit-data`:
- Lee `04_DATASETS_ORBIT/mod_gastos_accion.csv` con el helper `read_csv()` existente.
- Convierte columnas numéricas con `pd.to_numeric(..., errors='coerce')`.
- `resumen`: totales globales (gasto_real, gasto_teorico, exceso_pesos, vendedores_alertados, acciones_csv vs fallback).
- `top_acciones`: top 5 agrupados por `accion_id` ordenados por `exceso_pesos_total`.
- `top_vendedores`: top 5 agrupados por `vendedor_codigo` ordenados por `exceso_pesos_total`.
- `detalle`: 26 filas completas con NaN → `null`.
- Sin modificaciones a ningún endpoint existente.

**Validación:** Servidor arranca sin error en puerto 8502.
- `/api/gastos_accion`: `modo_datos=REAL`, 26 filas, top1=`MAY26-GRAL-TRAD-SPI-LOC-001` $83.166, V10 Ortega $93.169 exceso.
- `/api/diagnostico`: sin cambios — 7 vendedores, 3 segmentos, 28 titulares.

**Commit:** `4867990`

---

## 2026-05-06 — Bloque G: mod_gastos_accion — gasto real vs teórico por acción

**Archivo modificado:** `LEGACY/orbit_matinal_v42.py`

**Motivo:** Analizar cuánto gasto en descuentos genera cada acción comercial por vendedor, comparando el gasto real (descuento efectivamente aplicado) contra el gasto teórico (máximo permitido por la regla). Prerequisito: Bloque F ya generaba `fuente_regla` = `accion_id` en `mod_alertas_descuentos`.

**Diagnóstico previo:** `valor_descuento` del ERP (`valorDescuento`) es un valor **por unidad** (por botella), no por línea. Validado cruzando con `ImporteItem` (que incluye IVA 21%) e `ImporteNetoItem` (neto sin IVA). La fórmula correcta es `valor_descuento × cant_base` para el total de la línea.

**Cambio:** Nuevo bloque `MOD GASTOS POR ACCION` después de `MOD_ALERTAS_DESCUENTOS_GENERADO`:
- `gasto_real = valor_descuento × cant_base` (total descuento de la línea, neto IVA, desde ERP)
- `gasto_teorico = gasto_real × descuento_maximo_pct / descuento_aplicado_pct` (escala proporcional)
- `exceso_pesos = gasto_real - gasto_teorico` (siempre positivo: solo filas donde se excede el máximo)
- Agrupa por `(fuente_regla, vendedor_codigo, vendedor_nombre)` → columnas: `clientes_afectados`, `lineas_alertadas`, `gasto_real_total`, `gasto_teorico_total`, `exceso_pesos_total`, `exceso_pct_promedio`
- Join a `reglas_acciones_mayo_2026_orbit.csv` para enriquecer `canal` y `categoria`; fallbacks con `es_regla_csv=False`, `canal="FALLBACK"`
- Filtro: solo filas con `exceso_pesos_total > 0`
- Nueva hoja `mod_gastos_accion` en `MATINAL_PENA_V42.xlsx`; `datasets_orbit.py` exporta automáticamente a `04_DATASETS_ORBIT/mod_gastos_accion.csv`

**Validación:** `python LEGACY/orbit_matinal_v42.py` sin error.
- Hoja `mod_gastos_accion`: 26 filas, 0 NaN, 0 Inf
- `MAY26-GRAL-AS-VIN-001` presente ✓
- `gasto_real > gasto_teorico` en todas las filas ✓
- Mayor exceso: `MAY26-GRAL-TRAD-SPI-LOC-001` V10 → $83.166 | `MAY26-GRAL-AS-VIN-001` V9 → $58.982

**Commit:** `895de3f`

---

## 2026-05-06 — Bloque F: calcular_descuento_maximo lee reglas desde CSV

**Archivo modificado:** `LEGACY/orbit_matinal_v42.py`

**Motivo:** `calcular_descuento_maximo()` usaba dicts hardcodeados (`REGLAS_PRODUCTO_EXACTAS`, `REGLAS_PRODUCTO_FLEX`) y lógica if/elif con máximos incorrectos para Mayo 2026. Ejemplo: Autoservicio + VDA + 1–9 cajas devolvía 10% (incorrecto) en lugar de 6% (regla real del mes).

**Cambio:** Agregados antes de `calcular_descuento_maximo`:
- `_cargar_reglas_csv()`: carga lazy de `09_CONFIG/reglas_acciones_mayo_2026_orbit.csv`, filtra solo `beneficio_tipo == "DESCUENTO"`, normaliza tipos numéricos.
- `_SEG_A_CANALES_CSV`: mapeo de `segmento_11t` → valores de canal en el CSV.
- `_cats_comerciales()`: clasifica artículo/marca en categoría comercial CSV usando helpers existentes.
- `_buscar_regla_csv()`: lookup por canal + categoría + cajas_eq en rango `[cantidad_min, cantidad_max]`, ordena por `prioridad_regla`. Guarda defensiva: `pct * 100 if pct <= 1` (CSV usa decimales 0.06).
- `calcular_descuento_maximo()`: llama CSV primero; si no hay match, cae al fallback hardcodeado.

**Validación:** `python LEGACY/orbit_matinal_v42.py` sin error.
- `mod_alertas_descuentos`: 103 filas (antes: 14). 91/103 con `fuente_regla` = `MAY26-...`.
- `MAY26-GRAL-AS-VIN-001`: 48 filas, `descuento_maximo_pct = 6.0` ✓ (antes: 10.0).
- Fallback activo en 12 filas (segmentos sin cobertura en CSV o productos específicos).

---

## 2026-05-07 — Bloque H: exclusión formal de clientes no comerciales

**Archivos modificados:**
- `LEGACY/orbit_matinal_v42.py` (+18 líneas)
- `09_CONFIG/clientes_excluidos.csv` (nuevo, 9 filas)

**Motivo:** 9 códigos de cliente estaban presentes en `clientes.xlsx` pero no deben aparecer en ningún análisis comercial: un placeholder de venta directa (`402 CONSUMIDOR FINAL`) y 8 empleados de Peñaflor (`20001`–`20038`, Ramo=Empleados, codven=9, Ruta=BEBIDAS VD, Frecuencia=Eventual). Sin exclusión explícita, si algún día se les agrega `DiasVisita` o aparecen en ventas activas, entrarían en clientes_dia, CCC, cobertura, alertas, 11T y gastos.

**Cambio en `orbit_matinal_v42.py`:**
- Función `_cargar_clientes_excluidos()`: carga lazy de `09_CONFIG/clientes_excluidos.csv`, devuelve set de enteros. Fallback silencioso a `set()` si el archivo no existe o falla.
- Global `_EXCLUIDOS_CLI_IDS = None` para cachear entre llamadas (mismo patrón que `_EXCLUIDOS_REGLAS_CSV`).
- Filtro agregado en `cargar_clientes()` justo después del filtro `VENDEDORES_EXCLUIDOS`.
- Filtro agregado en `cargar_ventas()` justo después del filtro `VENDEDORES_EXCLUIDOS`.

**`09_CONFIG/clientes_excluidos.csv`:** columnas `cliente_id, razon_social, motivo_exclusion, aplica_a`. Los 9 registros llevan `aplica_a = TODO_ANALISIS_COMERCIAL`.

Códigos excluidos: `402`, `20001`, `20008`, `20011`, `20021`, `20027`, `20029`, `20031`, `20038`.

**Impacto actual:** cero — ninguno de los 9 tiene ventas en `ventas.csv` activo ni `DiasVisita`, por lo que no aparecían en ningún output de todos modos. La exclusión es defensiva.

**Validación post-motor + adaptador:**
- `mod_alertas_descuentos`: ninguno de los 9 códigos presente ✓
- `clientes_dia`: ninguno de los 9 códigos presente ✓
- `mod_gastos_accion`: 26 filas sin cambio ✓
- Motor y adaptador: exit code 0, sin errores ✓

**Commit:** `97993d2`

---

## 2026-05-07 — Bloque H: 8614 excluido + regla dinámica Ruta DEPOSITO

**Archivos modificados:**
- `LEGACY/orbit_matinal_v42.py` (+6 líneas)
- `09_CONFIG/clientes_excluidos.csv` (+1 fila, total 10)

**Motivo:** `8614 BUSTAMANTE JUAN` (V7, Ruta=DEPOSITO VILLA DOLORES, sin `DiasVisita`, sin ventas activas) quedaba fuera del CSV de exclusión del commit anterior. Adicionalmente, se detectó que la exclusión por CSV es reactiva: requiere agregar manualmente cada caso nuevo. Se incorporó una regla defensiva dinámica para cubrir futuros clientes en la misma condición.

**Cambio en `09_CONFIG/clientes_excluidos.csv`:**
- Nueva fila: `8614, BUSTAMANTE JUAN, sin_diasvisita_ruta_deposito, TODO_ANALISIS_COMERCIAL`

**Cambio en `orbit_matinal_v42.py` — `cargar_clientes()`:**
```python
mask_deposito_sin_dia = (
    df["ruta"].str.contains("DEPOSITO", case=False, na=False) &
    df["dias_visita"].isin(["", "nan", "NaN", "None", "<NA>"])
)
df = df.loc[~mask_deposito_sin_dia].copy()
```
Aplicado después del filtro `_cargar_clientes_excluidos()`. No aplica a `cargar_ventas()` porque `ventas.csv` no contiene columna `Ruta` del maestro.

**Regla:** todo cliente con Ruta que contiene "DEPOSITO" y sin `DiasVisita` queda excluido de todo análisis comercial, sin necesidad de estar en el CSV.

**Validación post-motor + adaptador:**
- `clientes_dia`: ninguno de los 10 IDs presente ✓
- `mod_alertas_descuentos`: ninguno de los 10 IDs presente ✓
- `mod_gastos_accion`: 26 filas sin cambio ✓
- Regla dinámica: 0 clientes legítimos afectados (ningún cliente con Ruta DEPOSITO tiene `DiasVisita` válido) ✓
- Motor y adaptador: exit code 0 ✓

**Commit:** `fe913dd`

---

## 2026-05-07 — botellas_dia y botellas_mes expuestos en /api/diagnostico y data.js

**Archivos modificados:**
- `server_orbit.py` (+5 líneas en `diagnostico()`)
- `PAV MATINAL PE_A FLOR/data.js` (+2/-1 líneas en `kpisGerencia`)

**Motivo:** `kpisGerencia.botellas_dia` estaba hardcodeado en 0 en `data.js`. El dato real existe en `mod_ccc_segmento.botellas_vendidas` (1.406 botellas del día) y `clientes_dia.botellas_mes` (9.050 botellas del mes), pero ningún endpoint los exponía.

**Cambio en `server_orbit.py` — `diagnostico()`:**
```python
botellas_dia = int(pd.to_numeric(ccc_df["botellas_vendidas"], errors="coerce").sum()) if not ccc_df.empty and "botellas_vendidas" in ccc_df.columns else 0
botellas_mes = int(pd.to_numeric(cdia_df["botellas_mes"], errors="coerce").sum()) if not cdia_df.empty and "botellas_mes" in cdia_df.columns else 0
```
Agregados al `return jsonify({...})` de `/api/diagnostico`.

**Cambio en `data.js` — `kpisGerencia`:**
```js
botellas_dia: diag.botellas_dia || 0,   // antes: 0 hardcodeado
botellas_mes: diag.botellas_mes || 0,   // nuevo campo
```

**Validación:**
- `/api/diagnostico`: `botellas_dia: 1406`, `botellas_mes: 9050` ✓
- `/api/dashboard`: 7 vendedores sin cambios ✓
- `/api/gastos_accion`: `modo_datos=REAL`, 26 filas sin cambios ✓
- Ningún otro endpoint ni KPI afectado ✓

**Commit:** `c1124b5`

---

## 2026-05-07 — /api/clientes y /api/alertas desde CSVs reales (elimina JSONs estáticos)

**Archivo modificado:** `server_orbit.py` (+34/-8 líneas)

**Motivo:** `/api/clientes` leía `06_APP_DATA/clientes_hoy.json` (255 filas, generado el 2026-05-05 por `app_publish.py`). `/api/alertas` leía `06_APP_DATA/alertas_app.json` (255 filas, mismo origen). Ambos JSONs estáticos no se actualizan con el pipeline nuevo. El pipeline genera `clientes_dia.csv` (340 filas) y `mod_alertas_descuentos.csv` (103 filas) en `04_DATASETS_ORBIT/` en cada ejecución.

**Cambio en `/api/clientes`:**
- Lee `04_DATASETS_ORBIT/clientes_dia.csv` vía `read_csv()`.
- Construye `vendedor_id`, `segmento`, `estado`, `prioridad_label`, `impacto_alertas_ars`, `faltan_11t`, `kernel_accion` desde columnas reales del CSV.

**Cambio en `/api/alertas`:**
- Lee `04_DATASETS_ORBIT/mod_alertas_descuentos.csv` vía `read_csv()`.
- Construye `vendedor_id`, `prioridad`, `tipo`, `titulo`, `detalle` (artículo + descuento aplicado vs máximo), `accion`, `impacto_alertas_ars` desde columnas reales del CSV.

**Validación:**
- `/api/clientes`: **340 items** (antes: 255), `estado` real, `prioridad_label` real ✓
- `/api/alertas`: **103 items** (antes: 255), `detalle` con descuento real ✓
- `/api/dashboard`: 7 vendedores sin cambios ✓
- `/api/gastos_accion`: `REAL`, 26 filas sin cambios ✓

**Commit:** `7a4f7e8`

---

## 2026-05-07 — fix: calcular dias comerciales con feriados reales

**Archivo modificado:** `server_orbit.py` (+12 líneas en `contar_dias_habiles()`)

**Motivo:** `/api/diagnostico` devolvía `total=26` y `corridos=4` porque `contar_dias_habiles()` no leía `09_CONFIG/feriados.csv`. Mayo 2026 tiene 2 feriados: `2026-05-01` (Día del Trabajador) y `2026-05-25` (Revolución de Mayo). El total correcto es 24 días comerciales. Sin este fix el frontend mostraba días incorrectos en todas las métricas de avance y tendencia.

**Cambio:** `contar_dias_habiles()` enriquecida:
- Lee y aplica feriados desde `09_CONFIG/feriados.csv`
- Expone `feriados_detectados_del_mes` en el response
- Expone `total_dias_comerciales_mes` y `dias_comerciales_corridos` como aliases
- Log en consola: `[ORBIT calendario] fecha_corte=... | total_comerciales=... | corridos=... | feriados_mes=[...]`

**Validación:** `/api/diagnostico` devuelve `total=24`, `corridos=3`, `feriados_detectados_del_mes=["2026-05-01"]`. Log visible en consola del servidor.

**Commit:** `076db05`

---

## 2026-05-07 — fix: corregir etiqueta de clientes planificados

**Archivo modificado:** `PAV MATINAL PE_A FLOR/screens/dashboard.jsx` (1 línea)

**Motivo:** El hint de la card "CLIENTES C/COMPRA" decía `"N de X visitados"`. La expresión `clientes_compra + alertas` suma clientes con compra más pendientes = universo **planificado** del día. No son "visitados" porque al momento de la matinal aún no ocurrió la visita.

**Cambio:** `"visitados"` → `"planificados"` (línea ~78). Sin cambio en lógica ni en otros archivos.

**Commit:** `a24d34f`

---

## 2026-05-07 — feat: agregar launcher portal ORBIT

**Archivo creado:** `ABRIR_CLAUDE_ORBIT.bat`

**Motivo:** El BAT anterior solo abría la CLI de Claude Code. No existía un launcher que arrancara `server_orbit.py`, mostrara URLs de diagnóstico en consola y abriera el navegador en el portal correcto (`http://localhost:8502/`).

**Cambio:**
- Muestra URLs: Portal / Diagnóstico / Dashboard antes de arrancar
- `start /b cmd /c "timeout /t 3 ... && start http://localhost:8502/"` — abre navegador 3s después (background)
- `python server_orbit.py` — Flask en primer plano, logs visibles

**No hace:** no corre `run_orbit.py`, no corre `app_publish.py`, no genera archivos estáticos, no depende de `06_APP_DATA/`.

**Commit:** `67a62b7`

---

## 2026-05-07 — chore: ignorar cache de python

**Archivo creado:** `.gitignore`

**Motivo:** `__pycache__/` aparecía permanentemente como untracked. No existía `.gitignore` en el repositorio.

**Contenido:**
```
__pycache__/
*.pyc
```

**Commit:** `b242b7c`

---

## 2026-05-07 — Validación funcional completa del portal

**Archivos modificados:** ninguno (auditoría con servidor activo, sin cambios de código)

**Método:** todos los endpoints probados con `Invoke-WebRequest` contra servidor en puerto 8502. Sin mock activo en ningún bloque auditado.

**Estado por endpoint:**

| Endpoint | Estado | Items | Detalle |
|---|---|---|---|
| `/api/diagnostico` | ✓ REAL | — | calendario, botellas, segmentos, titulares OK |
| `/api/dashboard` | ✓ REAL | 7 vendedores | sin_maestro=False en todos |
| `/api/clientes` | ✓ REAL | 340 | 141 SIN_COMPRA_MES + 199 COBERTURA_OK |
| `/api/alertas` | ✓ REAL | 103 | descuentos excesivos, detalle real por artículo |
| `/api/gastos_accion` | ✓ REAL | 26 filas | exceso total $231.133 |
| `/` (index.html) | ✓ HTTP 200 | 10.061 bytes | portal carga correctamente |
| `/data.js` | ✓ HTTP 200 | 5.869 bytes | sin mock, sin hardcode |
| `/api/planificacion` | ⚠ VACÍO | 0 | esperado — sin fuente real aún |

**`/api/diagnostico` valores clave al 2026-05-07:**
- `total=24`, `corridos=5`, `restantes=19`, `fecha_corte=2026-05-07`
- `feriados_detectados_del_mes=["2026-05-01","2026-05-25"]`
- `botellas_dia=1406`, `botellas_mes=9050`
- TRADICIONAL: 265 clientes / 18 cubiertos; AUTOSERVICIO: 47/11; ON_PREMISE: 28/1
- titulares11: 28 marcas; top ALMA MORA 126/337, CAZADOR 32/288

**Decisiones confirmadas (no requieren cambio de código):**
- **Sábados = días comerciales** en Peñaflor. `contar_dias_habiles()` excluye solo domingos y feriados. `corridos=5` al 2026-05-07 es correcto: Sáb 02/05 + Lun-Jue 04-07/05.
- **`/api/alertas` no mezcla SIN_COMPRA_MES** — los 141 clientes sin compra están en `/api/clientes` (prioridad=ALTA). Son canales distintos en el frontend. No mezclar hasta decisión explícita.
- **`/api/planificacion` vacío es esperado** si los vendedores no enviaron planes. No es un bug.

**Pendientes funcionales detectados en auditoría (no bloquean portal):**
1. ~~`vendedor_codigo` numérico en `top_vendedores`~~ → ✓ Resuelto commit `4cbbbee`.
2. `ccc_mes: 0` — honesto; ningún CSV actual tiene CCC acumulado del mes.
3. **Bloque A** — algunos clientes V7/V9 con datos faltantes en `clientes.xlsx` (requiere datos ERP externos).
4. **Automatización regeneración** — `ABRIR_CLAUDE_ORBIT.bat` solo abre el portal. El pipeline de regeneración (`run_orbit.py` + `datasets_orbit.py`) sigue siendo manual. Decisión futura: automatizar o mantener separado.

---

## 2026-05-07 — fix: normalizar vendedor_codigo en gastos accion

**Archivo modificado:** `server_orbit.py` (+16 líneas)

**Motivo:** `/api/gastos_accion` devolvía `vendedor_codigo` como entero (`10`, `9`) en lugar de formato `"V10"`, `"V9"`. Las cards de gastos del portal perdían el color del vendedor (caían al magenta default) porque el colorMap de `data.js` espera claves `"V10"`, `"V9"`, etc.

**Cambio:** nueva función helper `normalizar_vendedor_codigo(valor)` junto a `clean_code()` (línea 48). Reemplaza el `int(r["vendedor_codigo"])` inline en `top_vendedores`.

**Lógica de la función:**
- `None` → `""`
- `""` / `"NONE"` / `"NAN"` → `""`
- Prefijo `"V"` o `"v"` → extrae la parte numérica, aplica `int(float(n))`
- Sin prefijo → aplica `int(float(n))` directamente
- Fallback: si no parsea, devuelve el string tal cual

**Casos validados (9/9):**

| Input | Resultado |
|---|---|
| `10` | `V10` |
| `10.0` | `V10` |
| `"10.0"` | `V10` |
| `"V10"` | `V10` |
| `"v10"` | `V10` |
| `"V10.0"` | `V10` |
| `"v10.0"` | `V10` |
| `None` | `""` |
| `""` | `""` |

**Validación `/api/gastos_accion` — HTTP 200:**
- V10 Ortega `$93.169`, V9 Sanchez `$81.042`, V8 Alvarez `$54.012`, V3 Gambino `$2.908` ✓
- V4, V6, V7 ausentes (sin excesos en `mod_gastos_accion.csv`) ✓
- V2 y V5 ausentes (excluidos por motor) ✓
- Importes sin cambio ✓

**Commit:** `4cbbbee`

---

## 2026-05-12 — Auditoría total ORBIT Matinal Peñaflor

**Archivo creado:** `AUDITORIA_ORBIT_MATINAL_2026-05-12.md`

**Motivo:** Ejecución del PROMPT_003_AUDITORIA_TOTAL_MATINAL_PENAFLOR. Diagnóstico completo del estado del proyecto antes de cualquier modificación de diseño o funcionalidad.

**Metodología:** Solo lectura de archivos. Sin modificación de código. Sin datos mock. Inspección de todos los archivos del proyecto, logs del motor, CSVs de salida, endpoints Flask, frontend y configuración.

**Hallazgos críticos:**
1. `01_INPUTS/producto activos.xlsx` **no existe** → motor registra `PRODUCTOS_CARGADOS=0` → 11 Titulares usa mapa hardcodeado `MAP_11T_FINE` sin validar contra ERP.
2. **CCC acumulado del mes** no tiene fuente → `ccc_mes: 0` honesto pero KPI faltante importante.
3. `06_APP_DATA/orbit_portal_data.json` obsoleto (2026-05-05) → `/api/orbit-data` activo en Flask, datos incorrectos.
4. `dailyEvolution` en `data.js` es interpolación lineal, no datos reales por día.

**Sin mock activo en el flujo principal** (Flask → data.js → portal). 7 vendedores correctos. V2/V5 excluidos. V3 sin autoservicios. Días comerciales correctos.

**No se modificó ningún archivo del proyecto durante esta auditoría.**
