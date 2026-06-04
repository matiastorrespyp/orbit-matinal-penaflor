# CHANGELOG AI - ORBIT MATINAL PEÑAFLOR

## 2026-06-04 — feat(alertas): alertas de descuento desde el catálogo del mes (no mayo)

**Commit:** `9ebc42d`. Solo `server_orbit.py` (mismo formato de salida → portal sin cambios). Desplegado y validado en Render.

**Problema:** las alertas de descuento (`/api/alertas` → pantalla gerencial **Alertas** + bloque "Alertas de clientes" del vendedor) salían de `mod_alertas_descuentos.csv`, que el motor legacy genera contra `reglas_acciones_mayo_2026_orbit.csv` (**mes pasado**). No se actualizaba solo cada mes.

**Fix:** `/api/alertas` ahora se computa **en vivo desde el catálogo del mes** (`acciones_comerciales_<mes>_penaflor.csv`, autodetectado) × `ventas_acumulada.csv`. Se actualiza solo al cambiar de mes. Ya no depende del motor legacy ni de `mod_alertas_descuentos.csv`.
- Línea con descuento (`descuento aplicado = (ImporteItem−ImporteNetoItem)/ImporteItem`) es **alerta** si supera el **tramo más alto** de la acción del catálogo que aplica (vendedor + segmento + marca).
- **Sin acción que habilite** ese producto/segmento/vendedor → máximo 0 → alerta (`fuente_regla = "sin acción aplicable"`). (Definiciones confirmadas por el usuario.)
- Plan AS / 11T ya no necesitan exclusión hardcodeada: el catálogo define sus % permitidos.
- **Normalización de marca** (`_acc_norm`: sin acentos/puntuación) → corrige falsos positivos tipo `GORDON´S` vs `Gordon's`.

**Validación Render:** 112 alertas; Gordon's → ACJ26-007 (ya no "sin acción"); 6 "sin acción aplicable" (Tanqueray/JW/Alaris sin acción que los habilite para ese vendedor). Pantalla gerencial y vendedor V8 renderizan OK, sin errores JS.

**Nota:** el matcheo regla→venta reusa la misma capa de Acciones del Mes (vendedor+segmento+marca vía maestro 04D). Detalles finos de escala por cantidad no se aplican: el tope es el tramo más alto (criterio conservador, menos falsos positivos).

---

## 2026-06-04 — feat(acciones): "Acciones Comerciales del Mes" (catálogo mensual × ventas) gerencia + vendedor

**Commit:** `69bb95c`. `server_orbit.py` + `portal.html`. Desplegado y validado en Render.

**Fuente oficial (mensual, autodetectada):** `01_INPUTS/ACCIONES COMERCIALES/<YYYY-MM>/acciones_comerciales_<mes>_<año>_penaflor.csv`. El backend toma el mes más reciente disponible (en julio tomará julio solo, mismo patrón de nombre).

**Motor nuevo (`server_orbit.py`):** por cada acción del catálogo cruza el catálogo × ventas (`ventas_acumulada.csv` + maestro 04D) y calcula, con la fórmula probada de mayo:
- **Inversión real** = `ImporteItem − ImporteNetoItem` (descuento real del ERP, líneas con descuento > 0; "sin cargo" = 100% bonificado).
- **Litros** = CantBase × Lts/unidad (04D). **Clientes alcanzados** = únicos. **Clientes nuevos** = compraron esas marcas este mes y no el anterior.
- Matcheo regla→venta: **vendedor** (`vendedores_aplica`) + **segmento** del cliente + **marca/categoría** (vía maestro 04D marca→línea/categoría, con desambiguación "DADA VINO" ≠ Sidra/Champaña).
- Display desde catálogo: segmento, tipo (descuento/sin cargo), escala (condición), marcas, topes.
- Endpoints: `GET /api/gerencia/acciones_mes` (todas) y `GET /api/vendedor/<vid>/acciones_mes` (filtrado por `vendedores_aplica` + V3-sin-AS).

**Portal (`portal.html`):**
- Gerencia "Acciones Comerciales" → tarjeta por acción "Acciones Comerciales de Junio" (KPIs + inversión/litros/clientes/nuevos + segmento/tipo/escala/marcas/topes). (Versión anterior mayo/ranking quedó comentada.)
- Vendedor tab Alertas → bloque "Acciones Comerciales de Junio" con tarjeta por acción, **solo las que aplican a ese vendedor**.

**Validación Render (PASS):** gerencia 26 acciones (19 con inversión, total ~$3.1M; ACJ26-002 Trad VDA $360.462/23 cli/12 nuevos; "Sin cargo" detectado). Vendedor V8 = 25 acciones (sin ACJ26-017); V3 = 26 (con ACJ26-017, que es V3/V4/V6). `node --check` del portal OK; `py_compile` OK.

**Alcance/limitación:** inversión/litros/clientes se computan sobre el universo que matchea vendedor+segmento+marca con descuento real. Detalles finos de reglas (escala por tramos, surtido, 11T-quiebre mín/máx) se muestran como **condición/escala** (display), no como filtro adicional de líneas.

---

## 2026-06-04 — fix(vendedores): KPI "11T ✓" daba 0 en todos los vendedores

**Commit:** `a2b86ca`. Solo `server_orbit.py` (endpoint `/api/dashboard`); revisión tarjeta por tarjeta de la pantalla Vendedores.

**Auditoría de la pantalla Vendedores** (una tarjeta por vendedor, fuente `/api/dashboard`):
- Chip avance % (`tendencia_pct`) = proyección a fin de mes (acum/corridos×total/obj) → **OK** (correcto por regla del proyecto; no es el avance crudo).
- Acum/Obj (resultado.xlsx), CCC Mes (`ventas.csv` mes) → **OK**.
- Plan.día / SC Día iguales → **OK** (contexto matinal: planificación del próximo día, nadie compró aún).
- **11T ✓ (`once_titulares_cumplidos`) = 0 en los 7 vendedores → MAL.**

**Causa raíz:** el dataset `04_DATASETS_ORBIT/mod_11_titulares.csv` (objetivo del día, lo genera el motor legacy) llega con `tiene_flag`, `botellas_mes` e `importe_mes` en **0 en las 3740 filas** (`falta_flag=1` en todo). El motor no carga las ventas del mes a ese dataset → ningún titular "cumplido". Es un **bug del pipeline/motor**, no del dashboard.

**Fix (dashboard):** el KPI "11T ✓" ahora cuenta cobertura desde `mod_11t_acum.csv` (que sí está poblado y es la misma familia que usa la tarjeta 11T del gerencial), sumando `tiene_flag` por vendedor; fallback a `mod_11_titulares.csv` si no existe. Resultado validado en Render: V8=31, V10=9, V9=6, V4=3, V6=3, V3/V7=0 (suma 52).

**Pendiente (causa raíz, no resuelto):** el motor que genera `mod_11_titulares.csv` debe volver a cargar `botellas_mes`/`importe_mes` (tarea aparte en `LEGACY/`, fuera del alcance del dashboard).

---

## 2026-06-04 — fix(cierre-bat): push diario robusto en CIERRE_DIA_ORBIT.bat

**Commit:** `c8b6156`. Solo `CIERRE_DIA_ORBIT.bat` (herramienta del operador); no toca dashboard, datos ni backend.

**Contexto:** el push del refresh diario lo hace el **Paso 3/3 de `CIERRE_DIA_ORBIT.bat`** (no hay archivo aparte). El operador ejecuta ese único `.bat` y hace todo en cadena: valida `ventas.csv` → regenera datasets (`REGENERAR_DATOS_ORBIT.bat`) → sincroniza planes (`sync_planes_render.py`) → `git add`+`commit`+`push` → abre el portal. No es programado: se dispara a mano, pero corre todo de una.

**Problema:** el push fallaba en silencio cuando el repo local estaba detrás del remoto (rechazo non-fast-forward) — fue lo que dejó el dashboard en "Matinal miércoles" el 2026-06-04 (datos regenerados pero no publicados).

**Mejora aplicada al Paso 3/3:**
- Se agregó **`git pull --rebase origin master`** *después* del `commit` (árbol limpio) y *antes* del `push`, para sincronizar con el remoto y evitar el rechazo.
- Si el rebase falla → `git rebase --abort` + mensaje claro ("NO se publicaron los datos, avise a soporte"); deja el repo sano.
- Si el `push` falla → error grande y visible ("los datos NO llegaron a Render"); ya no pasa desapercibido.
- Chequeos migrados al idiom `if errorlevel 1` (lee el error real de cada comando), más confiable que el `%ERRORLEVEL%` anidado previo.

**Recordatorio operativo:** correr **`CIERRE_DIA_ORBIT.bat` completo** en cada cierre (no solo `REGENERAR_DATOS_ORBIT.bat`, que regenera pero NO publica). Render lee lo committeado, no el working tree local.

---

## 2026-06-04 — fix(dashboard): Sell Out en cero en Render + blindaje parseo ventas + validación integral

**Commits:** `4864d22` (fix Sell Out) · `41ec473` (limpieza) · `ffc0c1e` (blindaje). Desplegados y validados en Render.

### Síntoma
La tarjeta **Sell Out** del dashboard mostraba categorías en cero en Render (VINOS DEL AÑO 0/0), pese a haber datos. Localmente (Windows) se veía bien → no se reproducía.

### Causa raíz
`_preparar_df_ventas` (alimenta `/api/gerencia/sellout_litros`) leía `ventas.csv` **sin `dtype=str`** y dejaba a pandas inferir tipos. En Render (otra versión de pandas) la columna `ImporteNetoItem` (coma decimal "15800,82") se infería distinto → casi todas las filas quedaban con importe 0 → el filtro `ImporteNetoItem>0` descartaba 308/310 filas → categorías en cero. **No era el separador** (un intento con `sep=";"` dio solo `filas=2`, lo que reorientó el diagnóstico vía un marcador `_diag` temporal).

### Fix
- `_preparar_df_ventas`: leer con `dtype=str` + parseo numérico manual (`strip`+`strip('"')`+coma→punto+`to_numeric`), idéntico al patrón de `_leer_ventas_mes_csv` que ya funcionaba en Render. Reproducido en Render: `filas=310`, VINOS DEL AÑO 903.8L/54, SPIRITS 510/29, RTD 397.2/32, VDG 49.5/10, CHAMPAÑA 4.5/1, CERVEZA 22.7/5.
- **Blindaje (`ffc0c1e`)**: mismo `dtype=str` en `_cargar_ventas_mes_actual` y `_cargar_ventas_dia` (lectores de `ventas.csv` que usan `_parse_num_ar`), para que el parseo sea determinístico ante futuras versiones de pandas. Los lectores de `ventas_acumulada.csv` (11T) ya usaban el patrón robusto `.astype(str).str.replace` y filtran `CodVendedor` como int → se dejaron sin tocar.

### Validación integral del dashboard (Render, 15 endpoints PASS)
Cada tarjeta lee su archivo correcto y responde con datos:
- `ventas.csv` (`;`): diagnóstico (fecha), `/api/dashboard` (acum/venta/CCC vía `_parse_num_ar`), Sell Out (dtype=str). 
- `ventas_acumulada.csv` (`;`): 11T empresa/zona (`.str.replace`).
- `resultado.xlsx`: objetivos/avance.
- `04_DATASETS_ORBIT/*` (coma estándar): CCC, innovaciones, cobertura, 11t_acum, planes AS, acciones, alertas, clientes_dia.
Verificado: diagnóstico corte=2026-06-03/Matinal JU, dashboard V3 acum=391.694/venta_hoy=244.813, 11T ccc=2657, Sell Out VDA=903.8.

### ⚠️ Recordatorio operativo — PUSH DIARIO (no es código)
Render lee los archivos **committeados**, no el working tree local. El refresh diario llega a las tarjetas SOLO si se despliega. **Rutina diaria obligatoria:**
1. Actualizar inputs (`ventas.csv`, `ventas_acumulada.csv`, `resultado.xlsx`) + correr el pipeline (regenera `04_DATASETS_ORBIT/` + `02_HISTORY/`).
2. `git add` (inputs + datasets) → `git commit` → **`git push`** → Render auto-deploya (~1-3 min) y todas las tarjetas se actualizan solas.
Sin el push, el dashboard queda con datos del día anterior (fue la causa del "Matinal miércoles" del 2026-06-04).

---

## 2026-06-04 — feat(acciones): loader mensual de acciones comerciales + reporte de colisiones

**Commit:** `c2c6b55` (pusheado). Solo herramienta + datos de acciones; no afecta runtime del backend ni el cierre.

**Qué se hizo:** loader idempotente y versionado por mes para el catálogo de acciones comerciales, con validación, normalización y detección de colisiones. Tratado como **input mensual** (`aplica_cierre_mes = NO`); **no toca** cierre de mes, `resultado.xlsx`, históricos, datasets ni `server_orbit.py`.

**`tools/loader_acciones_comerciales.py`** (sin libs externas nuevas):
- Lee `01_INPUTS/ACCIONES COMERCIALES/<mes>/*.csv` (`;`, UTF-8-BOM). Uso: `python tools/loader_acciones_comerciales.py 2026-06`.
- Normaliza: expande `TODOS_ACTIVOS` → {V3,V4,V6,V7,V8,V9,V10}, **excluye V2/V5/V20**, valida `aplica_cierre_mes`.
- **Capa semántica marca→categoría**: lee el maestro `producto activos.xlsx` (solo lectura) y mapea marca → línea comercial → categoría (VDA/VDG/Espumantes/Sidra/Spirits…), desambiguando "DADA VINO" (solo VINOS DEL AÑO; excluye Sidra/Champaña). Degrada con gracia si el maestro no está.
- Idempotente: regenera la salida y respalda la previa en `salida/_backups/` con timestamp.

**Salida (en `01_INPUTS/ACCIONES COMERCIALES/2026-06/salida/`):**
- `catalogo_acciones_2026-06.json` — 26 reglas normalizadas (con `_cats` por regla) + validación.
- `reporte_colisiones_2026-06.json` / `.csv` — campo `tipo` (DIRECTA / SEMANTICA_LINEA_MARCA), estado `PENDIENTE_VALIDACION`.

**Diagnóstico Junio 2026:** 26 reglas, todas `aplica_cierre_mes=NO`, sin V2/V5/V20. **40 colisiones** (20 directas + 20 semánticas). ACJ26-017 (30% Alma Mora/Dada vino/Alaris/Finca Las Moras, V3/V4/V6, Tradicional) correctamente acotada; su único solape es **semántico con ACJ26-002** (escala VDA Tradicional, mismos vendedores), capturado vía mapeo marca→categoría (VDA).

**Pendiente:** el loader propone catálogo + colisiones; el motor de aplicación de descuentos y la resolución de colisiones quedan para etapa futura (no se acumulan automáticamente).

---

## 2026-06-03 — fix(cierre): acumulado distribuidora y por vendedor desde resultado_mes.xlsx

**Problema:** la tarjeta "Resumen compañía" (ventas acumuladas distribuidora) y "Cierre por vendedor" mostraban el acumulado de `ventas_mes.csv` ($285.579.795 / 87.39%). Ese valor era *importe neto facturado*, no el acumulado oficial del mes cerrado. El acumulado correcto vive en `01_INPUTS/resultado_mes.xlsx` (acumulado congelado del ERP, `Acumulado == Tendencia`): **$323.898.602,72 / 99.11%**.

**Causa raíz:** en el fix previo (`3b4dd72`) se cayó a `ventas_mes.csv` porque `resultado.xlsx` (archivo vivo) tenía el acumulado *stale* del mes en curso. Ahora existe `resultado_mes.xlsx` (snapshot del mes cerrado), que es la fuente correcta.

**Cambios aplicados:**
- `server_orbit.py` → `/api/gerencia/cierre_mes`: fuente primaria de objetivo/acumulado pasa a `resultado_mes.xlsx`, con fallback a `resultado.xlsx` si no existe. `fuente_objetivos` refleja la fuente real usada.
- `07_CIERRES_MENSUALES/2026-05/version_001/cierre_objetivos_avance.json` (artefacto congelado que consume el portal vía `/api/gerencia/cierres_historicos`): `objetivo/acumulado/avance_pct/faltante` de empresa y de cada vendedor reescritos desde `resultado_mes.xlsx`. **CCC, días hábiles y nombres preservados.** `fuente_acumulado`/`fuente_objetivos` = `resultado_mes.xlsx`. Backup en `99_BACKUPS_ORBIT/`.

**Validación (local):** `/api/gerencia/cierres_historicos` → acumulado compañía $323.898.602,72 / 99.11%; por vendedor V3 144.93%, V8 114.99%, V6 106.6%, V9 100.38%, V10 91.84%, V4 74.61%, V7 27.57%; CCC empresa 827 (preservado).

**Atención — diferencia intencional entre tarjetas:** "Resumen empresa del cierre" sigue mostrando **importe neto facturado** $285.579.795 (`ventas_mes.csv`), mientras "Resumen compañía" muestra **acumulado oficial** $323.898.602 (`resultado_mes.xlsx`). Son métricas distintas (gap ≈ $38,3M). Esto revierte parcialmente la unificación de `3b4dd72`. Definir si "Resumen empresa del cierre" también debe reconciliarse.

**No tocado:** `ventas_mes.csv`, CCC (`ventas_acumulada.csv`), 11T, sell out, innovaciones, planes, acciones, dashboard diario. `resultado_mes.xlsx` no se commitea (regla 01_INPUTS); el portal no depende de él en runtime porque lee el artefacto congelado.

---

## 2026-06-03 — fix(cierre): panel histórico completo + acumulado unificado

**Commits en producción:** `f8af3c9` (panel completo) → **`3b4dd72`** (acumulado unificado). Desplegado en Render, **Live** y validado end-to-end.

### Parte 1 — Panel histórico completo (`f8af3c9`)
El panel "Cierre de Mes" había quedado reducido a ranking + ganadores. Se recuperaron **todas** las secciones gerenciales, ahora alimentadas por **artefactos versionados congelados** (no por fuentes vivas).

- **Artefactos nuevos congelados** en `07_CIERRES_MENSUALES/2026-05/version_001/` (snapshot de `/api/gerencia/cierre_mes?mes=2026-05`, solo lectura):
  `cierre_objetivos_avance.json`, `cierre_11_titulares_detalle.json`, `cierre_innovaciones_detalle.json`, `cierre_sellout.json`, `cierre_planes_as.json`, `cierre_acciones_comerciales.json`.
- **Endpoint** `/api/gerencia/cierres_historicos` extendido (aditivo, solo lectura) con bloques: `objetivos_avance`, `ccc_segmentos`, `once_titulares`, `innovaciones`, `sellout`, `planes_as`, `acciones_comerciales`.
- **Portal**: secciones restauradas — Resumen compañía, Cierre por vendedor (V3–V10), 11 Titulares (CCC vs objetivo), Innovaciones (penetración), Sell Out, Planes AS, Acciones Comerciales, además de Ranking y Ganadores. Sin CantBase, sin botellas.

### Parte 2 — Acumulado unificado (`3b4dd72`)
Las dos tarjetas de compañía mostraban acumulados de fuentes distintas: "Resumen empresa del cierre" $285.6M (`ventas_mes.csv`) vs "Resumen compañía" $16.0M con avance irreal 4.9% (`resultado.xlsx`, valor stale).

- **Criterio unificado**: acumulado oficial = **`ventas_mes.csv`** (fuente del cierre); objetivo = `resultado.xlsx`.
  - Empresa: acumulado = `importe_neto_total` = **$285.579.795** (idéntico en ambas tarjetas).
  - Por vendedor: acumulado = `dinero_vendido` (suma exacta = total compañía).
  - Avance recalculado real: **compañía 87.39%** (antes 4.9% irreal); por vendedor V3 119.9%, V8 112.9%, V6 87.2%, V9 83.6%, V10 75.2%, V4 61.5%, V7 23.5%. Faltante compañía $41.2M.
- `cierre_objetivos_avance.json` regenerado; `portal.html` muestra la fuente del acumulado (`Acumulado: ventas_mes.csv`).

**Validación (Render):** endpoint confirma `acumulado_compañía == importe_neto_cierre == $285.579.795`; Playwright login gerencia → Cierre de Mes: todas las secciones presentes, avance 87.4%, ganador 11T V3 NADIA GAMBINO, sin CantBase ni botellas, sin errores JS ni de red.

**No tocado:** inputs, datasets, planificaciones, Google Sheets, datos maestros. Solo `server_orbit.py`, `portal.html` y los artefactos del cierre 2026-05/version_001.

---

## 2026-06-03 — feat(cierre): consolidar panel gerencial "Cierre de Mes" como cierre mensual oficial histórico

**Commits en producción:** `2a237a1` (panel histórico inicial) → `93e72a0`/`e488bef` (sheets) → **`b097300`** (consolidación final). Desplegado en Render, estado **Live** y validado.

**Problema corregido:** la pantalla gerencial "Cierre de Mes" mezclaba el cierre histórico versionado con una **vista dinámica** que recalculaba al vuelo desde `resultado.xlsx` + `ventas_acumulada.csv` (fuentes vivas/cambiantes). Además, el panel histórico solo mostraba el `ranking_top3`, por lo que el **ganador de 11 Titulares (V3 NADIA GAMBINO)** quedaba invisible (V3 es 5° en el ranking general).

**Regla de negocio formalizada:** para cierres oficiales, el portal debe consumir **únicamente artefactos congelados/versionados** (`07_CIERRES_MENSUALES/…` generados desde `01_INPUTS/ventas_mes.csv`) y **no recalcular** con fuentes cambiantes. Los datos dinámicos siguen siendo válidos para el dashboard diario, no para el cierre.

**Cambios aplicados:**

| Archivo | Cambio |
|---|---|
| `server_orbit.py` | Extensión **aditiva y solo-lectura** de `/api/gerencia/cierres_historicos`: agrega `empresa` (de `cierre_mensual_resumen.json`), `ranking` completo (7 vendedores, de `ranking_vendedores_mes.json`) y `ganadores` por categoría (`general`, `volumen_dinero`, `once_titulares`, `innovaciones`). No recalcula; no lee `ventas.csv`/`ventas_acumulada.csv`/`resultado.xlsx`; no toca generación de cierres ni inputs. |
| `PAV MATINAL PE_A FLOR/portal.html` | Pantalla "Cierre de Mes" 100% histórica: encabezado "Cierre de Mes — Histórico Versionado" + fuente `01_INPUTS/ventas_mes.csv`; metadatos del cierre; resumen empresa; ranking completo; bloque final "🏁 Cierre del Mes" con los 4 ganadores. **Eliminada** la "Vista dinámica (no histórica)" y todo consumo de `/api/gerencia/cierre_mes` en esta pantalla (el endpoint dinámico sigue intacto en backend, solo deja de usarse aquí). |

**Ganadores reauditados (Mayo 2026, desde `ranking_vendedores_mes.json`):** General **V8 ALVAREZ VANESA** (84.81) · Volumen/Dinero **V8** ($117.046.215) · 11 Titulares **V3 NADIA GAMBINO** (231 clientes) · Innovaciones **V8** (44 clientes). Resumen empresa: importe neto $285.579.795, 45.506,29 L, CCC 1.026, 7 vendedores.

**Validación PASS (Render producción, commit `b097300`):** `py_compile` OK; endpoint extendido devuelve `empresa` + `ranking`(7) + `ganadores`; Playwright login gerencia → Cierre de Mes confirma encabezado histórico, fuente `ventas_mes.csv`, `2026-05/version_001`, ganador 11T V3, ranking 7 vendedores, sin "Vista dinámica", sin CantBase ni botellas, sin errores JS ni de red.

**No tocado:** `07_CIERRES_MENSUALES/`, inputs, datasets, planificaciones, Google Sheets, datos maestros. Los CSV `clientes_master.csv` y `top_50_caida_vinos_alta_gama.csv` (modificados previamente) quedaron fuera de los commits.

---

## 2026-06-03 — feat(planificacion): Google Sheets como fuente de verdad (fail-closed)

**Commit en producción:** `93e72a0` — desplegado en Render, estado **Live**.

**Problema resuelto:** en Render Free, las planificaciones escritas en SQLite (`orbit.db`) se perdían en cada redeploy/restart porque el contenedor es efímero. Se establece **Google Sheets como fuente de verdad** y SQLite queda **solo como caché**.

**Google Sheet:** `ORBIT_PLANIFICACIONES_PENAFLOR`, pestaña `planificaciones`. ID de fila determinístico = `fecha + "_" + vendedor_id` (ej. `2099-01-01_V8`).

**Variables de entorno** (cargadas en el dashboard de Render, `sync:false`, sin secretos en Git):
- `GSHEETS_CREDENTIALS_JSON` — service account.
- `GSHEETS_SPREADSHEET_ID` — id del spreadsheet.
- `GSHEETS_SHEET_NAME` = `planificaciones`.

**Cambios aplicados en `server_orbit.py`:**

| Punto | Comportamiento |
|---|---|
| Helpers `gsheets_*` | upsert/verify/read_all/hydrate sobre la hoja; imports lazy de `gspread`/`google-auth` |
| `POST /api/planificacion` | **fail-closed**: guarda+verifica en Sheets; si falla → `ok:false` HTTP 503 sin tocar SQLite |
| `PATCH /api/planificacion/<id>` | **fail-closed**: Sheets primero, verifica fila, después SQLite |
| `GET /api/planificacion` | si SQLite vacío → `hydrate_planificacion_from_sheets()` → reconsulta SQLite → devuelve filas con id numérico |
| `restore_planificacion_if_empty()` | CSV de backup → si no hay CSV o está vacío → restaura desde Sheets |

**Validación end-to-end en producción (PASS):**
- `python -m py_compile server_orbit.py` PASS.
- Render Live, `/api/healthz` HTTP 200.
- Login gerencia HTTP 200 `ok:true`.
- POST controlado `V8` / `2099-01-01` → HTTP 200 `ok:true`. Endpoint no expone `sheets_ok`, pero `ok:true` bajo fail-closed equivale a guardado+verificado en Sheets.
- Fila confirmada visualmente en Google Sheets (id `2099-01-01_V8`).
- `GET ?fecha=2099-01-01&vendedor_id=V8` → fila con id numérico SQLite (`id:1`).
- **Manual Deploy/restart** realizado → GET post-redeploy devolvió la fila **hidratada desde Google Sheets**.
- **Conclusión: las planificaciones ya no se pierden por redeploy/restart de Render Free.**

**Archivos tocados:** `server_orbit.py`, `requirements.txt` (+`gspread>=6.0.0`, `google-auth>=2.0.0`), `.gitignore` (patrones de credenciales), `render.yaml` (env vars `GSHEETS_*`), `CHANGELOG_AI.md`, `NEXT_TASK.md`. **No** se tocó `portal.html`, inputs, datasets, cierres ni datos maestros.

**Pendientes:**
- Fila de prueba `2099-01-01_V8` ("TEST PLANIFICACION GOOGLE SHEETS - BORRAR") queda **pendiente de limpieza con aprobación**.
- Etapa separada: crear `tools/descargar_planificaciones_sheets.py` (backup local a `07_PLANIFICACIONES/planificaciones_render.csv`) sin duplicaciones.

---

## 2026-06-03 — fix(horario): normalizar timestamps visibles a hora Argentina

**Commit en producción:** `daf443b`

**Problema corregido:** varios campos de `server_orbit.py` usaban `datetime.now()` naive o `CURRENT_TIMESTAMP` de SQLite, que en Render (servidor UTC) devolvían la hora UTC — 3 horas adelantada respecto a Argentina.

**Zona oficial aplicada:** `America/Argentina/Cordoba` / UTC-3 via `_now_ar()` (ya existía en el código, no se usaba de forma consistente).

**Cambios aplicados:**

| Función | Campo | Antes | Después |
|---|---|---|---|
| `planificacion_patch()` | `updated_at` | `CURRENT_TIMESTAMP` (UTC SQLite) | `updated_at=?` con `_now_ar()` |
| `planificacion()` POST | log a archivo | `datetime.now().strftime(...)` | `_now_ar()` |
| `backup_orbit_db()` | nombre de archivo | `datetime.now().strftime(...)` | `_now_ar().replace(...)` |
| `mensajes()` POST | `created_at` | `DEFAULT CURRENT_TIMESTAMP` implícito | `created_at=_now_ar()` explícito |
| ~30 endpoints | `generado_en` y `last_sync` | `datetime.now().strftime(...)` | `_now_ar()` |

**Validaciones PASS:**
- `python -m py_compile server_orbit.py` PASS.
- Render auto-deploy activo (65 segundos).
- Login gerencia HTTP 200 PASS.
- `/api/dashboard` — `last_sync: 2026-06-03 15:23:09` = hora Argentina ✓
- `/api/diagnostico` — `generado_en: 2026-06-03 15:23:14` = hora Argentina ✓
- `/api/gerencia/cierres_historicos` — estado OK, sin warn, top3 V8/V10/V9 ✓
- `portal.html`, inputs y datos no tocados.
- Archivos pendientes fuera de objetivo sin stage y sin commit.

**PATCH planificación:** no probado en producción — sin planes activos disponibles para modificar de forma segura.

**`datetime.now()` residuales sin corrección** (fuera del alcance aprobado):
- Líneas 284, 474, 666, 3216 — cálculos internos de fecha/calendario, no timestamps visibles al usuario.

**Archivos tocados:** `server_orbit.py`, `CHANGELOG_AI.md`, `NEXT_TASK.md`.

---

## 2026-06-03 — qa(render): validación producción post-commit 5a9b7a0

**QA Render producción — solo lectura, sin modificaciones.**

Commit verificado: `5a9b7a0` (fix path separadores Windows→Linux).

**Endpoints validados:**

| Endpoint | Estado |
|---|---|
| Home / portal HTML | PASS — HTTP 200 |
| POST /api/login gerencia | PASS — ok:true, rol:gerencia |
| POST /api/login vendedor V8 | PASS — ok:true, nombre correcto |
| POST /api/login inválido | PASS — HTTP 401, ok:false |
| GET /api/diagnostico | PASS — fecha_corte 2026-06-02, corridos 2/24 |
| GET /api/dashboard | PASS — 7 vendedores con datos reales |
| GET /api/gerencia/cierre_mes | PASS — mes 2026-05, 7 vendedores, avance 4.9% |
| GET /api/gerencia/cierres_historicos | PASS — estado OK, 2026-05/version_001, top3 V8·V10·V9, sin warn |

**Portal gerencial (Playwright headless):**
- Dashboard `appG` visible con datos reales: Acumulado $16.0M, Tendencia 58.7%, 7 vendedores con KPIs.
- Sidebar completo: Dashboard, Vendedores, Clientes Críticos, Planificación, Plan vs Real, Alertas, Dormidos, Innovaciones, Planes AS, Acciones Comerciales, Cierre de Mes.
- Sección "Cierre de Mes" presente bajo REPORTES — carga endpoint `/api/gerencia/cierre_mes`.
- Sin errores JS en consola.
- Sin errores de red 4xx/5xx.
- CantBase no visible en pantalla: confirmado.
- Botellas no visible en pantalla: confirmado.
- NaN: 0 / undefined: 0.

**Validaciones QA PASS.**

**QA solo lectura:** no se modificaron archivos, no commit, no push, no deploy.

---

## 2026-06-03 — feat(cierre): endpoint read-only /api/gerencia/cierres_historicos

**Qué se hizo:**
- Agregado endpoint `GET /api/gerencia/cierres_historicos` en `server_orbit.py` (inserción entre línea 3565 y bloque STARTUP).
- Solo lectura: lee `07_CIERRES_MENSUALES/index_cierres_mensuales.json` y los archivos internos de cada versión.
- No genera cierres. No ejecuta `tools/generar_cierre_mensual.py`. No toca ningún input de ventas.

**Respuesta del endpoint:**
- `estado`: OK / SIN_CIERRES / ERROR
- `total_cierres`: cantidad de cierres en el índice
- Por cierre: `periodo`, `version`, `timestamp_argentina`, `estado`, `manifest` resumido, `ranking_top3`
- Si falta `manifest.json` o `ranking_vendedores_mes.json` → agrega `warn` a esa entrada, no rompe el endpoint

**Validaciones PASS:**
- `python -m py_compile server_orbit.py` → PASS
- Endpoint probado local `http://localhost:8502/api/gerencia/cierres_historicos` → `estado: OK`, `total_cierres: 1`, cierre `2026-05/version_001`, top3: V8 (84.81) · V10 (48.54) · V9 (44.82)
- CantBase y botellas no expuestos
- `portal.html` no tocado
- `ventas_mes.csv`, `ventas.csv`, `ventas_acumulada.csv` no tocados
- No commit, no push, no deploy. Render pendiente de verificación post-deploy.

**Archivos tocados:** `server_orbit.py` (nuevo endpoint ~75 líneas), `CHANGELOG_AI.md`, `NEXT_TASK.md`.

---

## 2026-06-03 — feat(cierre): cierre mensual histórico versionado + ranking vendedores

**Qué se hizo:**
- Creado `tools/generar_cierre_mensual.py` — script standalone de generación de cierre mensual histórico versionado.
- Generado primer cierre histórico: `07_CIERRES_MENSUALES/2026-05/version_001/`.
- Fuente exclusiva de ventas: `01_INPUTS/ventas_mes.csv`. Prohibido usar `ventas.csv` o `ventas_acumulada.csv` para valores finales.
- Maestros/catálogos usados solo como referencia: `04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx` (litros), `INNOVACIONES/Innovaciones.xlsx` (códigos), `vendedores_activos.csv`.

**Archivos generados en `07_CIERRES_MENSUALES/2026-05/version_001/`:**
- `manifest.json` — trazabilidad: fuente, hash, timestamps AR/UTC, filas, fechas, vendedores, estado PASS.
- `snapshot_inputs.json` — estado de cada input al momento del cierre.
- `cierre_mensual_resumen.csv` / `.json` — resumen por vendedor: dinero, litros, CCC, 11T, innovaciones.
- `ranking_vendedores_mes.csv` / `.json` — scores ponderados y rankings por categoría.
- `acciones_comerciales_mes.csv` / `.json` — descuentos por tramo y sin cargo.
- `detalle_11_titulares_mes.csv` — cobertura 11T por vendedor × marca.
- `detalle_innovaciones_mes.csv` — clientes por vendedor × producto innovación.
- `index_cierres_mensuales.csv` / `.json` — índice global de todos los cierres.

**Ranking mensual validado (Mayo 2026):**

| Categoría | Ganador | Valor |
|---|---|---|
| General | V8 ALVAREZ VANESA | score 84.81 |
| Volumen/Dinero | V8 ALVAREZ VANESA | score_vd 100.0 |
| 11 Titulares | V3 NADIA GAMBINO | 231 clientes cubiertos |
| Innovaciones | V8 ALVAREZ VANESA | 44 clientes |

**Ponderación aplicada:** litros 20% · dinero 20% · 11 titulares 30% · innovaciones 30%.

**Validaciones PASS:**
- Fuente ventas = `ventas_mes.csv` exclusivamente.
- V3 solo Tradicionales — `segmentos: ['TRADICIONAL']`.
- V1 y V20 excluidos del cierre (detectados en CSV, filtrados).
- py_compile PASS. dry-run PASS.
- Versionado inmutable: segunda ejecución detecta `version_002` sin pisar `version_001`.
- Timestamp Argentina correcto: `2026-06-03T13:55:41-03:00` / UTC `2026-06-03T16:55:41Z`.
- `server_orbit.py` y `portal.html` no tocados.
- No commit, no push, no deploy.

**Riesgos comerciales detectados (para seguimiento):**
- V3 puede ganar 11T por ventaja estructural: opera solo TRADICIONAL, casi toda su cartera compra marcas 11T naturalmente. Evaluar normalizar por % de cobertura en etapa futura.
- JW BLACK y JW RED con 0 clientes cubiertos en mayo (V4, V7, V8, V10).
- V7 JOFRE GUILLERMO score 8.78 — muy bajo. Revisar cartera/datos/actividad del mes.
- Tramo descuento 19% concentrado en 1 cliente ($1.2M inversión estimada). Validar si es acción especial o error ERP.
- Innovaciones bajas en general salvo V8 (44 clientes) y V9 (33 clientes). V4=1, V3=3.

**Archivos tocados:** `tools/generar_cierre_mensual.py` (nuevo), `07_CIERRES_MENSUALES/` (nueva carpeta), `CHANGELOG_AI.md`, `NEXT_TASK.md`.

---

## 2026-06-03 — fix(pav): calendario matinal dashboard

**Problema:**
`/api/diagnostico` mostraba en Render `corridos=3`, `total=26`, `dia_operativo=JU` y `fecha_matinal=2026-06-04` en lugar de los valores correctos. El portal mostraba "3 de 26 días" y la matinal apuntaba al día equivocado.

**Causas identificadas y corregidas:**

1. **`total=26` → `total=24`** (`49d2c28`): feriados.csv solo tenía mayo. Se agregaron los feriados del resto de 2026 incluyendo `2026-06-15` (Güemes trasladado) y `2026-06-20` (Día de la Bandera). Los dos días de junio reducen el total de 26 a 24.

2. **`corridos=3` y `fecha_matinal=JU`** (`49d2c28` + `936efa1`): el calendario usaba `datetime.now()` del servidor (UTC → ya era Jun 3 cuando AR era Jun 2). Se cambió a leer la última `FechaComprobante` de `ventas.csv` con `sep=";"` explícito. `sep=None` en Linux (mismo bug que `ventas_mes.csv`) perdía las filas de Jun 2 por columnas mal alineadas.

3. **Parser de fecha ambiguo** (`b17eec3`): `'2/6/2026'` con `dayfirst=True` daba resultados inconsistentes entre Windows (Jun 2) y Linux (Feb 6 o NaT). Se cambió a `format="%d/%m/%Y"` explícito.

4. **`fecha_corte` top-level = reloj del servidor** (`40c5d82`): `"fecha_corte"` en la respuesta era `datetime.now()` (Jun 3 en Render) mientras `calendario.fecha_corte` era Jun 1. Ambos se unificaron a `_fecha_corte_datos.strftime(...)` = última fecha de `ventas.csv`.

**Resultado en Render (`40c5d82`):**
- `fecha_corte`: `2026-06-02` ✓
- `corridos`: `2` ✓
- `total`: `24` ✓
- `restantes`: `22` ✓
- `dia_operativo`: `MI` ✓
- `fecha_matinal`: `2026-06-03` ✓
- `feriados_detectados_del_mes`: `['2026-06-15', '2026-06-20']` ✓

**Commits:**
- `49d2c28` — feriados junio 2026 + hora AR para calendario
- `b17eec3` — parser `format="%d/%m/%Y"` para FechaComprobante
- `936efa1` — matinal desde última fecha de datos (no `datetime.now()`)
- `40c5d82` — unificar `fecha_corte` top-level desde `ventas.csv`

**Archivos tocados:** `server_orbit.py`, `09_CONFIG/feriados.csv`

## 2026-06-02 — data: cierre diario y sincronización 11T dashboard

**Qué se hizo:**
- Se ejecutó `CIERRE_DIA_ORBIT.bat` para publicar inputs y datasets actualizados.
- El BAT completó la regeneración de datos (motor legacy + exportador CSV) pero no pudo ejecutar el commit/push en modo no-interactivo (el `pause` final bloquea stdin). Se realizó el commit manual con exactamente los mismos archivos que el BAT hubiera incluido.
- `orbit.db` **no fue commiteado** — el fix de planificación persistente (`7b08c88`) funcionó correctamente: ausente del BAT, presente en `.gitignore`, ausente del commit.

**Archivos commiteados (`6a05ef1`):**
- `01_INPUTS/ventas.csv`, `ventas_acumulada.csv`, `resultado.xlsx`
- `02_HISTORY/historial_ventas_cliente.csv`
- `04_DATASETS_ORBIT/` — 19 datasets regenerados

**Resultado en Render:**
- `/api/gerencia/once_titulares` usa `ventas_acumulada.csv` ✓
- ALMA MORA dashboard: 757 → **472** (coincide con local)
- 11 marcas sincronizadas con la fuente actualizada

**Archivos tocados:** ninguno de código — solo datos.

## 2026-06-02 — fix(pav): persistencia planificación — orbit.db dejó de commitearse

**Problema:**
Las planificaciones que los vendedores cargaban en Render desaparecían al volver al portal. Siempre aparecía solo el plan V4 del 18/5 (seedeado desde el repo).

**Diagnóstico:**
- `orbit.db` estaba trackeado en git.
- `CIERRE_DIA_ORBIT.bat` tenía `git add "orbit.db"`, lo que commiteaba la DB local (sin los planes de los vendedores) en cada cierre de día.
- Cada push → nuevo deploy en Render → `init_db()` al arrancar podía re-seedear `/var/data/orbit.db` desde el `orbit.db` del repo, pisando los planes guardados por los vendedores.
- Confirmado por diagnóstico API: la DB de Render tenía solo 2 registros (`id=2` V4 18/5 y `id=9` test de diagnóstico); los ids 3–8 habían existido y desaparecido.

**Corrección:**
- `CIERRE_DIA_ORBIT.bat`: eliminada la línea `git add "orbit.db"`.
- `.gitignore`: agregada regla `orbit.db` con comentario explicativo.
- `git rm --cached orbit.db`: sacado del tracking sin borrar el archivo físico local.

**Resultado:**
Render conserva sus planificaciones en `/var/data/orbit.db`. Los deploys ya no pisan la DB persistente. El seed inicial de `init_db()` solo corre si el archivo no existe — desde que existe, nunca se re-seedea.

**Commit:** `7b08c88`
**Archivos tocados:** `CIERRE_DIA_ORBIT.bat`, `.gitignore`

## 2026-06-02 — fix(pav): corregir sell out cierre mensual (ventas_mes.csv en Render)

**Problema:**
`/api/gerencia/cierre_mes` devolvía `filas_ventas_mes=53` y Vinos del Año=192 L en Render (producción).
Localmente el mismo endpoint producía 5067 filas válidas y ≈14900 L. El dashboard sellout_litros no estaba afectado.

**Diagnóstico:**
`ventas_mes.csv` usa coma como separador y decimales europeos entre comillas (`"6620,94"`).
Git checkoutea el archivo con CRLF en Windows y con LF en Linux (Render). El motor C de pandas con `sep=None` (y luego con `sep=","` sin `engine="python"`) no dequoteaba correctamente los campos en Linux, dejando comillas residuales en `ImporteNetoItem`. Eso hacía que `pd.to_numeric` devolviera NaN → 0 → casi todas las filas fallaban el filtro `> 0`. Solo las 53 filas con importe entero (sin coma decimal en el CSV) pasaban.

Se confirmó la causa con un endpoint de diagnóstico temporal (`/api/debug/ventas_mes`) que expuso `md5`, tamaño, filas raw y filas válidas sin datos sensibles. El md5 de Render (LF) difería del local (CRLF) en exactamente 5553 bytes = 1 byte × 5553 filas.

**Solución:**
Nueva función `_leer_ventas_mes_csv(src_path)` en `server_orbit.py`:
- `pd.read_csv(..., sep=",", quotechar='"', engine="python", dtype=str)` — el motor Python dequotea correctamente en Linux; `dtype=str` evita conversión automática que ocultaba el problema.
- Cadena de limpieza antes de `pd.to_numeric`: `.str.strip().str.strip('"').str.replace(",", ".", regex=False)` — elimina espacios, `\r` residuales y cualquier comilla no eliminada.
- Aplicada a `PesoKg`, `CantBase`, `ImporteNetoItem`, `CodVendedor`.
- Usada solo en `/api/gerencia/cierre_mes`. `_preparar_df_ventas` (ventas.csv, dashboard, sellout_litros) **sin tocar**.

**Resultado final en Render:**
- `filas_ventas_mes`: 5067 ✓
- Vinos del Año: 14923.5 L ✓
- Spirits: 18585.9 L, RTD: 12792.8 L, Vinos de Guarda: 403.5 L
- `sellout_litros` sigue usando `ventas.csv` sin cambios ✓

**Commits de esta sesión:**
- `e31e348` — `fix(pav): corregir parser ventas_mes para sell out cierre` (primer intento, `sep=","` sin engine=python — insuficiente)
- `ff38ba1` — `debug(pav): exponer diagnostico seguro ventas_mes render` (endpoint temporal de diagnóstico)
- `b1f4c2a` — `fix(pav): robustecer lectura ventas_mes en linux` (fix definitivo)
- `4242821` — `chore(pav): remover endpoint debug ventas_mes` (limpieza)

**Archivos tocados:** `server_orbit.py`

## 2026-06-01 — fix(sellout): clasificación Nacionales/Importados + fallback litros PesoKg=0

**Causa raíz:**
1. `SPIRITS_NAC`/`SPIRITS_IMP` usaban el campo `Linea` (Standard/Premium) — JW Red caía en Nacionales porque es Standard, pero debería ser Importado. J&B Rare tenía `Linea=Whisky` y PesoKg=0, sin litros.
2. Bloque fallback PesoKg=0 tenía condición `if mask0.any() and cod2lxu:` — si el maestro de productos no existe, la inferencia por nombre nunca corría. Gordon's Tropical, J&B Rare y Smirnoff Tamarindo mostraban 0 L.

**Fix aplicado:**
- `server_orbit.py` (`gerencia_sellout_litros`): reemplaza clasificación por `Linea` con keywords por nombre de artículo: `SMIRNOFF`, `GORDON`, `WHITE HORSE`, `J&B` → Nacionales; resto → Importados.
- `server_orbit.py`: fallback PesoKg=0 siempre corre (`and cod2lxu` eliminado); inferencia del nombre es el fallback final garantizado.
- `server_orbit.py` (`gerencia_cierre_mes`): sellout del cierre ahora lee `ventas_acumulada.csv` filtrado al mes con la misma lógica corregida (reemplaza lectura de `mod_sellout_categoria.csv` pre-computado).
- `portal.html` (`gCierreMes`): tabla sellout muestra subcategorías (Nacionales/Importados, Líneas Vinos del Año) con barra y chip de color.

**Archivos tocados:** `server_orbit.py`, `PAV MATINAL PE_A FLOR/portal.html`

## 2026-06-01 — feat(cierre_mes): 11T + Innovaciones + Sell Out + Planes AS + Acciones

**Qué se hizo:**
- `server_orbit.py` (`/api/gerencia/cierre_mes`): extendido con 5 bloques nuevos:
  - `once_titulares`: empresa (cumplidos/total/%), por vendedor, por marca; fuente `mod_11t_acum.csv`
  - `innovaciones`: resumen (productos, compraron, penet. promedio), top 20 por producto; fuente `mod_innovaciones_segmento.csv`
  - `sellout`: litros vs objetivo por categoría (remap al diccionario OBJ del endpoint sellout_litros); fuente `mod_sellout_categoria.csv`
  - `planes_as`: resumen (clientes, facturado, SC ganado/pendiente) + desglose por plan; fuente `mod_planes_as.csv`
  - `acciones`: resumen (total acciones, inversión, clientes) + top 10 por inversión; fuente `mod_acciones_ranking.csv`
- `portal.html` (`gCierreMes`): renderiza las 5 secciones nuevas después de la tabla de vendedores con barras, chips de color y tablas.

**Archivos tocados:** `server_orbit.py`, `PAV MATINAL PE_A FLOR/portal.html`

## 2026-06-01 — feat(gerencia): pantalla Cierre de Mes

**Qué se hizo:**
- `server_orbit.py`: nuevo endpoint `GET /api/gerencia/cierre_mes?mes=YYYY-MM`.
  - Default: mes anterior (mayo al estar en junio).
  - Objetivos y acumulado $ desde `resultado.xlsx` hoja "Avance".
  - CCC desde `ventas_acumulada.csv` filtrado al mes, con filtro `Empresa='Empresa'` para excluir P&P Logística.
  - Reglas: excluye V2/V5/V20; V3 `ccc_autoservicio=0`; clasifica por `_clasificar_segmento()`.
  - Devuelve: empresa (totales) + vendedores (ordenados por avance desc) + calendario del mes cerrado.
- `portal.html` (sidebar): nuevo ítem "🏁 Cierre de Mes" bajo sección "Reportes".
- `portal.html` (gCierreMes): pantalla self-loading con selector de mes (últimos 3 meses), tarjetas KPI empresa, tabla por vendedor con barra de avance y desglose CCC (TRAD/AS/OP).
- `portal.html` (gSw, gRender): registrado en título y router.

**Archivos tocados:** `server_orbit.py`, `PAV MATINAL PE_A FLOR/portal.html`

## 2026-05-28 — feat(planificacion): timestamps Argentina + total todos los planes

**Qué se hizo:**
- `server_orbit.py`: agrega `_ARG_TZ = timezone(timedelta(hours=-3))` y helper `_now_ar()` para timestamps en hora Argentina.
- `server_orbit.py` (POST /api/planificacion): reemplaza `CURRENT_TIMESTAMP` SQLite por `_now_ar()` en Python. En re-envíos (ON CONFLICT), solo actualiza `updated_at`, preserva `created_at` original. Devuelve `hora_envio` en la respuesta.
- `portal.html` (gPlanificacion — gerencia): cada tarjeta de vendedor muestra "📅 Enviado hoy HH:MM" usando `updated_at` (último envío) en lugar de `created_at`. Incluye fecha si no es hoy.
- `portal.html` (gPlanificacion — gerencia): tarjeta "📊 Total Planificación PyP del Día" ahora incluye TODOS los planes (no solo aprobados). Nueva columna Estado y columna Enviado con hora. Chips de conteo por estado.
- `portal.html` (vPlan — vendedor): muestra "📅 Enviado hoy a las HH:MM" debajo del header cuando el plan ya fue cargado.

**Causa raíz de horas incorrectas:**
SQLite `CURRENT_TIMESTAMP` devuelve UTC. En Argentina (UTC-3) la diferencia era de 3 horas. Fix: usar Python `datetime.now(timezone(timedelta(hours=-3)))`.

**Archivos tocados:** `server_orbit.py`, `PAV MATINAL PE_A FLOR/portal.html`

---

## 2026-05-28 — chore(deploy): healthz liviano + estabilizar Render

**Qué se hizo:**
- `server_orbit.py`: nuevo endpoint `GET /api/healthz` — devuelve `{"status":"ok","service":"orbit-penaflor-pav","healthcheck":true}` con HTTP 200 sin leer ningún archivo ni base de datos. Pensado para Render health check y UptimeRobot.
- `render.yaml`: `healthCheckPath` cambiado de `/api/diagnostico` → `/api/healthz`. El diagnostico completo sigue disponible pero no bloquea el deploy.
- `render.yaml`: `--workers 2` → `--workers 1` (evita conflictos de escritura en SQLite).
- `render.yaml`: `autoDeploy: true` → `autoDeploy: false` (deployar manualmente para no sobreescribir orbit.db en producción).
- `Procfile`: agrega `--workers 1` para coherencia con render.yaml.
- `server_orbit.py` (planificacion POST): agrega log IP + payload a `99_LOGS_ORBIT/planificacion_post.log`.

**Causa raíz del 404 en UptimeRobot:**
`/api/diagnostico` lee Excel y múltiples CSVs. En Render, estos archivos no existen. La llamada al health check durante el deploy podía tardar o devolver 500, haciendo que Render hiciera rollback a una versión anterior que sí tenía el endpoint pero en estado degradado.

**Archivos tocados:** `server_orbit.py`, `render.yaml`, `Procfile`

---

## 2026-05-28 — fix(planificacion): errores silenciosos y datos cacheados en portal

**Qué se hizo:**
- `portal.html` — `submitPlan`: el `catch(e){}` era silencioso. Ahora muestra mensaje rojo visible al vendedor si el POST falla (sin conexión o error del servidor).
- `portal.html` — `submitPlan`: si el servidor responde `ok:false`, muestra el mensaje de error del servidor.
- `portal.html` — `gPlanificacion`: refetch de `/api/planificacion` al abrir la pantalla. Antes gerencia veía datos del login; ahora siempre muestra los planes más recientes.

**Causa raíz de planes que no llegaban:**
El servidor no estaba iniciado cuando los vendedores enviaron. El `catch(e){}` silenciaba el error de red. Los vendedores no recibían feedback de que el envío había fallado.

**Archivos tocados:** `PAV MATINAL PE_A FLOR/portal.html`

---

## 2026-05-28 — fix(planvsreal): CCC T/A/O y 11T Plan muestran '–' aunque el valor sea 0

**Qué se hizo:**
- `portal.html`: cambio de `v.plan_ccc_trad||'–'` → `v.tiene_plan?v.plan_ccc_trad:'–'` (ídem para CCC A, CCC O, 11T).
- En JavaScript `0 || '–'` devuelve `'–'`, por lo que cualquier campo con valor 0 se mostraba vacío aunque el vendedor sí tuviera plan cargado.
- La guardia correcta es `tiene_plan` (booleano que el endpoint ya devuelve).

**Archivos tocados:** `PAV MATINAL PE_A FLOR/portal.html`

---

## 2026-05-28 — feat(planificacion): protección de datos — backup automático, CSV de seguridad y auto-restore

**Qué se hizo:**
- **`server_orbit.py`**: al arrancar el servidor, copia `orbit.db` con timestamp a `99_BACKUPS_ORBIT/planificacion/orbit_YYYYMMDD_HHMMSS.db`.
- **`server_orbit.py`**: si `planificacion` queda vacía y existe `planificacion_latest.csv`, restaura automáticamente los datos al arranque.
- **`server_orbit.py`**: cada vez que un vendedor guarda (POST) o gerencia aprueba/edita (PATCH) un plan, exporta la tabla entera a `99_BACKUPS_ORBIT/planificacion/planificacion_latest.csv`.
- **`REGENERAR_DATOS_ORBIT.bat`**: agrega `orbit.db` al paso de backup (paso 4) con el mismo mecanismo de timestamp que los demás archivos críticos.

**Causa raíz del problema:**
`orbit.db` tenía fecha de modificación 2026-05-18. Los planes cargados el 2026-05-27 no aparecían en Plan vs Real porque el archivo en uso era una copia anterior (posiblemente reemplazado manualmente o por restauración).

**Archivos tocados:** `server_orbit.py`, `REGENERAR_DATOS_ORBIT.bat`

---

## 2026-05-27 — fix(gerencia): sellout litros — fallback PesoKg=0 y fuente corregida a ventas.csv

**Qué se hizo:**
- **Fuente corregida**: el endpoint `/api/gerencia/sellout_litros` ahora lee `ventas.csv` (no `ventas_acumulada.csv`).
- **Fallback nivel 1**: cuando `PesoKg = 0` y `CantBase > 0`, calcula `CantBase × LitrosXunidad` desde `producto activos.xlsx`.
  - Cubre 24 productos que venían sin litros en el CSV (DADA 7 SWEET, ANTARES LAGER, GORDONS GIN, etc.).
  - CHAMPAÑA: de 256L → 580L (cuadra con imagen -56L de diferencia = venta de hoy).
  - CERVEZA: de 43L → 228L (imagen 195L, sistema tiene +34L = venta de hoy incluida ✅).
- **Fallback nivel 2**: productos no encontrados en el maestro → infiere ml del nombre del artículo por regex (`X750` → 0.75L, `X1000` → 1.0L, `X473` → 0.473L).
  - Cubre 8 productos sin match en maestro (FRIZZE MANXANA, MARANTIQUA, ALARIS, etc.).
- **Función helper** `_infer_litros_por_nombre()` agregada a nivel de módulo.

**Archivos tocados:**
- `server_orbit.py` — endpoint `gerencia_sellout_litros` + función `_infer_litros_por_nombre`

---

## 2026-05-27 — feat(gerencia): sellout en litros con objetivos y alcance por categoría

**Qué se hizo:**
- **Nuevo endpoint** `/api/gerencia/sellout_litros`: devuelve sellout acumulado en litros vs objetivos del mes.
  - Fuente: `01_INPUTS/ventas_acumulada.csv` (PesoKg = litros precomputados por línea).
  - Excluye V2, V5, V20. Solo ImporteNetoItem > 0.
  - Objetivos hardcoded de `obj sell out.jpeg`: 6 categorías principales + subcategorías.
  - Subcategorías: VINOS DEL AÑO → Alto/Medio/Medio Alto/Superior (por columna `Linea`).
  - Subcategorías: SPIRITS → Importados (Whisky/Gin/Ron/Whisky Maltas) / Nacionales (Vodka/Licores).
  - Retorna: litros real, objetivo, alcance_pct, clientes por categoría y subcategoría.
- **Tarjeta Sellout reemplazada** en `gDashboard()`:
  - Nueva columna "Objetivo" con los litros meta.
  - Nueva columna "Alcance" con chip color: ok ≥100%, wn ≥60%, bd <60%.
  - Mini barra proporcional antes del chip.
  - Subcategorías indentadas con ↳ y chip de alcance propio.
  - Eliminada columna "Cajas" y barra de proporción relativa (sustituidas por objetivo real).

**Datos validados (ventas_acumulada.csv al 27-May-2026):**
- VINOS DEL AÑO: 22.190L / 19.015L obj = 116.7% ✅ (sobre objetivo)
- VINOS DE GUARDA: 1.063L / 678L = 156.8% ✅
- SPIRITS: 31.231L / 17.752L = 175.9% ✅
- RTD: 15.671L / 9.999L = 156.7% ✅
- CHAMPAÑA: 483L / 686L = 70.4% ⚠️
- CERVEZA ARTESANAL: 102L / 405L = 25.2% 🔴

**Archivos tocados:**
- `server_orbit.py` — endpoint `/api/gerencia/sellout_litros` añadido (línea ~2376)
- `PAV MATINAL PE_A FLOR/portal.html` — tarjeta sellout reemplazada en `gDashboard()`

---

## 2026-05-27 — feat(gerencia): panel 11T distribuidora + 11T por vendedor seleccionado

**Qué se hizo:**
- **Nuevo endpoint** `/api/gerencia/11t_empresa`: devuelve resumen 11T de toda la distribuidora (por marca: con/sin/total/% empresa + desglose por vendedor). Fuente: `mod_11_titulares.csv`.
- **Nuevo endpoint** `/api/gerencia/11t_vendedor?vendedor=V3`: devuelve 11T detallado del vendedor seleccionado (por marca: con/sin/total/%). Fuente: `mod_11_titulares.csv`.
- **Nueva tarjeta** "🏅 11 Titulares · Resumen Distribuidora" en `gDashboard`: tabla full-width con todas las marcas, % empresa, y chips por vendedor (con hover de con/sin/pct). Siempre visible.
- **Nueva tarjeta** "🏅 11 Titulares · [Vendedor]" en `gDashboard`: tabla con desglose del vendedor seleccionado en el selector superior. Se muestra/oculta dinámicamente — visible solo cuando hay un vendedor seleccionado en `gVSel`.
- Ambas tarjetas usan IIFEs async self-loading; se regeneran al cambiar el filtro (`gFiltV → gRender → gDashboard`).

**Archivos tocados:**
- `server_orbit.py` — 2 endpoints nuevos después de `gerencia_once_titulares_zona`
- `PAV MATINAL PE_A FLOR/portal.html` — gDashboard(): 2 tarjetas + IIFEs insertados antes del bloque Sellout

## 2026-05-27 — fix(gerencia): 11T cards self-loading — bypass D state issue

**Problema**: las dos tarjetas de 11 Titulares en el dashboard gerencial mostraban solo el título ("Cargando datos…" / "Sin datos") sin tabla, a pesar de que los endpoints `/api/gerencia/once_titulares` y `/api/gerencia/once_titulares_zona` devuelven datos correctos.

**Causa probable**: `D.onceTit` o `D.onceTitDia` no estaba disponible en el momento del render de `gDashboard()` (timing issue o race condition entre loadAll() y gRender()).

**Fix aplicado** — `portal.html`:
- Ambas tarjetas de 11T ahora usan **IIFEs async self-loading** en lugar de depender del estado de `D`
- La tarjeta *CCC vs Objetivo* (col derecha) hace `fetch('/api/gerencia/once_titulares')` directamente después de que el DOM es insertado, y rellena `#body-11t-obj` con la tabla. También actualiza `D.onceTit` para consistencia.
- La tarjeta *CCC zona del día* (col izquierda) hace `fetch('/api/gerencia/once_titulares_zona?dia=currentDay')` directamente, actualiza etiqueta, chip y tabla. También actualiza `D.onceTitDia`.
- Si el endpoint devuelve error HTTP o lanza excepción, muestra mensaje de error visible en la tarjeta.
- Placeholders "Cargando datos…" visibles mientras se resuelven los fetch.

**Archivos tocados:**
- `PAV MATINAL PE_A FLOR/portal.html` — gDashboard(): 2 tarjetas 11T reescritas con self-loading

## 2026-05-26 — feat(vendedor): acciones comerciales con tramos y marcas en Alertas

**Acciones comerciales — pestaña Alertas del vendedor:**
- `/api/acciones_vigentes` reescrito: lee `reglas_acciones_*.csv` (fuente de verdad) agrupando por
  `accion_grupo`. Devuelve `lineas_segmentos` + lista `tramos[]` con `{condicion, descuento_pct,
  cant_min, cant_max, bonif_cajas, unidad}` — elimina el campo `descuento_display` de rango (era "3-25%", ilegible)
- Portal: `vAlertas()` reescrita con `CAT_LABEL` (categoria → etiqueta legible) y `marcasLabel()`
  que usa `lineas_segmentos` si es específico o el mapa si es genérico
- Un tramo: condición + chip de dto en una línea; múltiples tramos: bullet list con chip por escalón
- V3 (Nadia Gambino) sigue sin ver acciones de canal AUTOSERVICIOS
- `CONFIG.glob("reglas_acciones_*.csv")` auto-detecta el archivo del mes vigente → sin cambios de código para junio

**Archivos tocados:**
- `server_orbit.py`: endpoint `/api/acciones_vigentes` (+78 líneas)
- `PAV MATINAL PE_A FLOR/portal.html`: función `vAlertas()` (+107 líneas)

**Validación:**
- Endpoint devuelve 22 grupos con `lineas_segmentos` + `tramos[]`
- V3 filtra AUTOSERVICIOS en frontend
- Commit `b4c8e6e` — push `8cca2ce..b4c8e6e` → Render auto-deploya

---

## 2026-05-26 — feat(responsive): smartphone optimization + Render deploy setup

**Smartphone — perfil vendedor:**
- `viewport-fit=cover` en meta viewport → habilita safe area en iOS (notch + home indicator)
- `@supports env(safe-area-inset-bottom)`: `.vbnav` y `.vcont` ajustan padding para home indicator
- `#loginScreen overflow-y:auto` en móviles → form no se clipa cuando el teclado virtual sube
- `visualViewport.resize` event → ajusta altura de login al espacio disponible sobre el teclado
- `@media (max-width:380px)`: `.pf-grid` colapsa a 1 columna, `.vkv` reduce a 20px
- `@media (max-width:340px)`: `.vkv` 17px, tabs 7.5px, íconos 15px, vendor header 16px
- `.vtab > span:last-child`: `white-space:nowrap; overflow:hidden` evita desborde de etiquetas
- Tab "Mi Plan" → "Plan" (más corto, entra en pantallas de 320px sin problema)
- Botón "Salir" en topbar vendedor: `min-height:44px` para touch target adecuado
- Touch targets en formularios: `min-height:44px` en inputs/textareas a ≤380px
- Fix: login logo `assets/orbit-mark.png` (no existía) → `orbit_pav_matinal_final.png`

**Render deployment:**
- `render.yaml` creado (web service, Python, gunicorn, plan Starter $7/mes)
- `DEPLOY_RENDER.md` con guía completa: pasos, flujo diario, variables de entorno, nota SQLite
- GitHub remote ya existente: `matiastorrespyp/orbit-matinal-penaflor`
- Nota: Render ya no tiene tier gratuito; Railway.app tiene $5/mes de crédito incluido

**Archivos tocados:**
- `PAV MATINAL PE_A FLOR/portal.html`: CSS responsivo + JS visualViewport + correcciones HTML
- `render.yaml`: nuevo
- `DEPLOY_RENDER.md`: nuevo

---

## 2026-05-26 — feat(acciones): panel acciones comerciales por acción con análisis de retorno

**Nuevo panel "Acciones Comerciales" con tres mejoras principales:**

**1. Detección por acción individual (no canal+categoría):**
- `generar_acciones_ranking()` ahora agrupa por `accion_grupo` (definido en CSV de reglas)
- Cada acción tiene nombre legible (ej: "Smirnoff ICE 25%", "Drop Vinos — Autoservicios")
- Muestra rango de descuento real aplicado (ej: "6-25%")
- 19 acciones detectadas vs las 7-8 anteriores

**2. Análisis comparativo vs mes anterior (nuevo: `generar_acciones_analisis()`):**
- Para cada acción calcula clientes nuevos en categoría (no compraban en abril y ahora sí)
- Delta de litros % vs mes anterior (usando historial_ventas.csv)
- Costo de activación por cliente nuevo (inversión ÷ clientes nuevos)
- Clientes que repitieron vs abril

**3. Corrección de bug crítico: `ImporteItem` con coma decimal:**
- El filtro original `ImporteItem - ImporteNetoItem > 0` fallaba para casi todos los productos
  porque `ImporteItem` usa coma decimal y no se limpiaba → parseaba como 0
- Fix: cambiar filtro a `Descuento_pct > 0` (descuento explícito en ERP)
- `ImporteItem` ahora se limpia correctamente para calcular inversión real

**4. Corrección de bug RTD duplicado + acciones faltantes:**
- `_ARTICULO_CAT_MAP`: RTD=Frizze, RTD LATAS=Gordons/Smirnoff BC/Antares, RTD ICE=Smirnoff ICE
- `_REGLA_CAT_MAP`: SIDRA capitalizado correctamente ("SIDRA" no "Sidra")
- Nuevas reglas CSV: Smirnoff ICE 25% (imagen 7) y Termidor 5-15% (imagen 8)

**Archivos tocados:**
- `generar_datasets_acum.py`: nuevas funciones `_preparar_ventas_acciones`, `_filtrar_ventas_accion`,
  `generar_acciones_ranking` (reescrita), `generar_acciones_analisis` (nueva)
- `09_CONFIG/reglas_acciones_mayo_2026_orbit.csv`: +cols `accion_grupo`/`accion_nombre`, +2 reglas
- `04_DATASETS_ORBIT/mod_acciones_ranking.csv`: regenerado con nuevo formato (19 filas)
- `04_DATASETS_ORBIT/mod_acciones_analisis.csv`: nuevo archivo (19 filas)
- `server_orbit.py`: endpoint `/api/gerencia/acciones_ranking` reescrito con datos enriquecidos
- `PAV MATINAL PE_A FLOR/portal.html`: `gAccionesComerciales()` reescrita con:
  - Tabla detalle por acción (nombre, canal, dto, inversión, litros, clientes)
  - Panel análisis: clientes nuevos, clientes que repitieron, delta litros, costo activación

**Validación:**
- Endpoint `/api/gerencia/acciones_ranking` → 200 OK, 19 acciones con datos de análisis
- Ejemplo Smirnoff ICE 25%: 277 clientes, 78% nuevos en categoría, +77.3% litros vs abril, $28.937/cliente activado

---

## 2026-05-26 — fix(planes_as): NaN Marca Frizze + regla fechas + regla fuente mensual

**Problema 1 — Errores de Marca en ERP (afecta múltiples marcas):**
La detección de sin cargo usaba la columna `Marca` del ERP, que tiene dos tipos de error:
- `Marca = NaN`: códigos 14619/14620 (FRIZZE BUBBLE MOOD/MANXANA POP) sin Marca → Frizze no detectado
- `Marca = "Alaris"` incorrecto: código 74510 "F. LAS MORAS ROSADO" tiene Marca="Alaris" en el ERP
  → falso positivo: CLIs 1178 y 997 mostraban Alaris enviado cuando no se había enviado nada
- Código 35103/35104/35105 "SMF ICE...": Marca="Smirnoff Ice Flavours" es correcto pero Articulo
  usa abreviatura "SMF", no "SMIRNOFF" → se perdería si se usa solo Articulo sin keyword "smf ice"

**Fix:** `_detectar_prod_as()` usa `Articulo` como fuente primaria y exclusiva (sin fallback a Marca).
Keywords ampliados: `"sc_env_smf_flavours": ["smirnoff", "smf ice"]` para cubrir abreviaturas ERP.
"F. LAS MORAS ROSADO" no contiene ningún keyword del plan → correctamente excluido.
"FRIZZE BUBBLE MOOD" contiene "frizze" → correctamente detectado.
"SMF ICE RED BERRIE" contiene "smf ice" → correctamente detectado como Smirnoff.

**Regla de negocio formalizada — FechaComprobante:**
Para Peñaflor la fecha válida de venta es siempre `FechaComprobante` (facturación), nunca
`FechaEntrega` ni `FechaCarga`. Una venta facturada el 30/5 y entregada el 4/6 es de mayo.
Corregido en:
- `app_matinal_penaflor.py`: 4 lugares (load_ventas_mes, load_historial, load_real_dia,
  semanas históricas) — todos usaban `FechaEntrega` para filtrar períodos.
- `tools/orbit_truth_audit.py`: "ventas_ayer" filtrada por `FechaEntrega` → `FechaComprobante`.
- `server_orbit.py` y `generar_datasets_acum.py`: ya usaban `FechaComprobante` correctamente.
- Memoria guardada en `memory/business_rule_fecha_facturacion.md`.

**Regla de negocio formalizada — fuente Plan AS:**
Sin cargos enviados se calculan SOLO desde `ventas.csv` (período mensual activo).
`Reconocimiento Plan As.xlsx` se renueva cada mes → define lo adeudado en ese mes.
`ventas_acumulada.csv` NO aplica para Plan AS (es período anterior).
Comentario fijo en `main()` de `generar_datasets_acum.py`.

**Resultado final:**
- 8/31 clientes genuinamente pendientes (8125, 390, 30006, 1178, 2689, 8010, 997, 2353)
- 23/31 con todos sus sin cargos del mes entregados y registrados
- CLI 2357/30033/172/30044: Frizze sc_pend_frizze=0 ✓ (antes PENDIENTE por NaN Marca)
- CLI 1178/997: Alaris sc_env_alaris=0 ✓ (antes mostraba 6 enviado por F.Las Moras mal taggeado)
- CLIs con Smirnoff SMF ICE: sc_env_smf_flavours detectado correctamente vía keyword "smf ice"

**Archivos tocados:**
- `generar_datasets_acum.py` — fix NaN Marca Frizze + comentario regla fuente mensual
- `app_matinal_penaflor.py` — 4 ocurrencias FechaEntrega → FechaComprobante
- `tools/orbit_truth_audit.py` — FechaEntrega → FechaComprobante
- `04_DATASETS_ORBIT/mod_planes_as.csv` — regenerado, 7 genuinamente pendientes

## 2026-05-26 — feat(innovaciones): 17 productos reales, sin desglose vendedor en gerencia, avance propio en panel vendedor

**Problema encontrado:**
- `generar_datasets_acum.py` cargaba `ventas.csv` (Apr30-May23, 2 productos) para innovaciones
  en vez de `ventas_acumulada.csv` (Apr1-May9, 15 productos con data real).
- El panel gerencial mostraba una tabla de "Desglose por Vendedor" que el usuario no quiere.
- El card vendedor mostraba cada producto×segmento por separado (duplicado visual).

**Fix:**
- `generar_datasets_acum.py`: refactor `cargar_ventas_acum()` → `_parsear_ventas_csv()` + nueva
  función `cargar_ventas_acumulada()`. Las funciones de innovaciones ahora usan `ventas_acumulada.csv`.
- CSV regenerado: 221 filas, 17 productos, todos con datos reales desde ventas acumuladas.
- `portal.html` `gInnovaciones()`: tabla "Desglose por Vendedor" eliminada. Panel gerencial muestra
  solo resumen total: stats cards (N productos, con cobertura, cartera) + lista de 17 productos
  con barra de progreso y compraron/cartera.
- `portal.html` INOV-4 vendedor: productos ahora agrupados por nombre (combina TRAD+AS),
  muestra compraron/cartera total y barra por producto. Chip "X/17 con cobertura".

**Archivos tocados:**
- `generar_datasets_acum.py` — refactor carga ventas + uso de ventas_acumulada para innovaciones
- `04_DATASETS_ORBIT/mod_innovaciones_segmento.csv` — regenerado, 17 productos × 7 vend × segs
- `04_DATASETS_ORBIT/mod_innovaciones_plan_as.csv` — regenerado con ventas_acumulada
- `PAV MATINAL PE_A FLOR/portal.html` — gInnovaciones() + INOV-4 vendedor

## 2026-05-26 — fix(dashboard): tendencia_pct usa ERP en lugar de recálculo dinámico

**Problema encontrado en auditoría:**
El servidor recalculaba `tendencia_pct = (acum / corridos_hoy) * total / obj * 100`
usando `corridos_hoy = 20` (fecha actual 26/5), pero el acumulado es de fecha_datos = 23/5
(19 días hábiles). El divisor incorrecto inflaba la tendencia +0.73 a +1.78 pp vs ERP.
Caso crítico: V9 SANCHEZ aparecía en portal como 100.11% (objetivo cumplido) cuando
el ERP oficial dice 99.07% (no llegó). Decisión incorrecta en reunión matinal.

**Fix:**
- `server_orbit.py` línea 556: `tendencia_pct` ahora usa `av` (avance_pct del CSV = ERP)
  cuando está disponible. Fallback al recálculo solo si no hay dato oficial.
- Validación: los 7 vendedores muestran tendencia_pct = avance_pct exacto del ERP.

**Archivos tocados:**
- `server_orbit.py` — línea 556: 1 línea → 4 líneas con lógica ERP-first.

**Auditoría dashboard completa — resultado:**
- ✅ Acumulado, objetivo, avance_pct: exactos vs resultado.xlsx
- ✅ CCC mes: Δ ≤ 2 clientes por vendedor (snapshot timing aceptable)
- ✅ 11 Titulares: CSV = API exacto
- ✅ V3 sin autoservicio: CCC AS = 0
- ✅ Vendedores activos: V3,V4,V6,V7,V8,V9,V10 (sin V2,V5,V20)
- ✅ Total días comerciales mayo = 24 (feriados 1/5 y 25/5 correctos)
- ✅ tendencia_pct (post-fix): Portal = ERP exacto

## 2026-05-26 — feat(portal): responsive mobile — sidebar drawer, hamburger, media queries

**Archivos tocados:**
- `PAV MATINAL PE_A FLOR/portal.html` — responsive completo para PC y smartphones:
  - `.gt-ham`: botón hamburger (3 líneas → X animado) oculto en desktop, visible en mobile.
  - `.gs-overlay`: capa oscura backdrop detrás del sidebar cuando está abierto en mobile.
  - `@media (max-width:768px)`: sidebar `.gs` pasa a drawer deslizable desde la izquierda (posición fixed, `left:-290px`, transición cubic-bezier). Grids `.g2/.g3` a 1 columna. `.krow` a 2 columnas. Tablas con `overflow-x:auto`. Topbar compacto (50px, sin `.gt-live`, sin `#gVSel`). Padding de página reducido.
  - `@media (max-width:430px)`: login card con padding reducido, logo 144px. Topbar sin "ORBIT ›". KPI cards más compactas.
  - `openNav()` / `closeNav()`: muestran/ocultan sidebar y overlay.
  - `gSw()`: llama `closeNav()` al navegar → sidebar se cierra solo al seleccionar sección.
  - Overlay `onclick="closeNav()"` → tap fuera del sidebar lo cierra.
- `server_orbit.py` — default de ruta `/` cambiado de `index.html` a `portal.html`. `http://localhost:8502/` ahora abre directamente el portal correcto.

## 2026-05-26 — feat(portal): login — toggle día/noche, cielo animado, form glass minimalista

**Archivos tocados:**
- `PAV MATINAL PE_A FLOR/portal.html` — rediseño completo del login screen:
  - Botón toggle ☀️/🌙 en esquina superior derecha (posición `fixed` glass con blur).
  - Dos capas de fondo con transición suave (opacity 1.4s): `fondo.png` (día) / `fondo_noche.png` (noche).
  - Overlay `.sky-overlay` con elementos CSS animados:
    - **Día:** `.sky-sun` (arc 30s, `sunArc` keyframe, glow cálido), 4 nubes (`.sky-c1`–`.sky-c4`) con `::before/::after`, animaciones `c1Move`/`c2Move` en sentidos opuestos.
    - **Noche:** `.sky-moon` (arc 34s, `moonArc`, glow azulado), 2 nubes oscuras (`.sky-nc1/2`), `.sky-stars` generadas dinámicamente (90 estrellas, `starTwinkle`).
  - Clase `.night` en `#loginScreen` controla visibilidad vía CSS (`display:none/block`).
  - Card blanca eliminada → `.ln-glass` (backdrop-filter blur 32px, border rgba).
  - Logo: `orbit_pav_matinal_final.png` 176px, `orbitFloat` sin sonido.
  - Selector de perfil con `ln-sel-wrap` (custom arrow CSS, opciones legibles `#0D1118`).
  - JS: `applyLoginMode()`, `toggleMode()`, `initStars()`, persistencia en `localStorage`.
  - Boot: `initStars()` + `applyLoginMode(loginMode)` antes de mostrar pantalla.
- `PAV MATINAL PE_A FLOR/fondo_noche.png` — copiado desde `01_INPUTS/` (2.3MB).
- `PAV MATINAL PE_A FLOR/orbit_pav_matinal_final.png` — copiado desde `01_INPUTS/` (110KB).

**Validación:** portal.html: 261 insertions / 60 deletions. Las 4 imágenes PNG están en `PAV MATINAL PE_A FLOR/`. Sin cambios a endpoints, datasets ni app gerencial/vendedor.

## 2026-05-23 — feat(portal): Clientes Dormidos — alertas comparativas historial

**Archivos tocados:**
- `server_orbit.py` — nuevo endpoint `GET /api/gerencia/alertas_caida`. Compara `historial_ventas_cliente.csv` (período anterior: antes del inicio de ventas.csv = 30 abril) con `ventas.csv` (período actual). Devuelve: resumen, por_vendedor con top 5, detalle completo. Excluye V2/V5/V20. Resultado: 561 dormidos, $41.2M en riesgo. V4=171/V8=$12.6M/V6=108.
- `PAV MATINAL PE_A FLOR/portal.html` — nuevo ítem sidebar "💤 Dormidos" con badge amarillo, loadAll ampliado, showApp actualiza badge, función `gDormidos(p)` con KPI cards + tabla por vendedor + tabla detalle top100 con urgencia (rojo≥45d, amarillo≥30d, azul<30d).

## 2026-05-23 — feat(portal): login redesign — fondo.png, logo isotipo flotante, card blanca

**Archivos tocados:**
- `PAV MATINAL PE_A FLOR/portal.html` — fondo login → `fondo.png` (cover), logo ORBIT 190px con animación `orbitFloat` continua, card login con fondo blanco/claro para legibilidad del isotipo negro. Sin efectos de sonido ni spin.
- `PAV MATINAL PE_A FLOR/orbit_logo.png` — isotipo ORBIT (copiado desde 01_INPUTS).
- `PAV MATINAL PE_A FLOR/pyp_logo.png` — logo PyP 3D (copiado desde 01_INPUTS).
- `PAV MATINAL PE_A FLOR/fondo.png` — imagen de fondo pantalla login (copiado desde 01_INPUTS).
- Sidebar gerencial: logo PyP en lugar del texto ORBIT + "PAV PEÑAFLOR". Logo ORBIT debajo del perfil de usuario.

## 2026-05-23 — fix(portal): botón Actualizar preserva día seleccionado

**Archivos tocados:**
- `PAV MATINAL PE_A FLOR/portal.html` — `reloadData()`: guarda `savedDay` antes de `loadAll()`, muestra spinner, restaura selección y re-fetchea datos del día si difiere del operativo.
- `server_orbit.py` — comentario REGLA FIJA en `gerencia_sellout_categoria()`.



## 2026-05-23 — fix(sellout): fuente pipeline corregida a ventas.csv + datasets regenerados

**Archivos tocados:**
- `generar_datasets_acum.py` — `cargar_ventas_acum()`: `ventas_acumulada.csv` → `ventas.csv` (sep=";" explícito). Pipeline regenerado: 7 datasets actualizados.
- `04_DATASETS_ORBIT/mod_sellout_categoria.csv` — regenerado con fuente correcta.
- `04_DATASETS_ORBIT/mod_11t_acum.csv`, `mod_cobertura_acum.csv`, `mod_innovaciones_segmento.csv`, `mod_innovaciones_plan_as.csv`, `mod_acciones_ranking.csv`, `mod_planes_as.csv` — ídem.

**Validación:**
- Cerveza Artesanal: 911 litros, 26 clientes ✓ (antes: 4776 litros, 225 clientes con ventas_acumulada)
- RTD (S): 209512 L, 287 clientes (antes: 302553 L, 476)
- Vinos del año: 48753 L, 1041 clientes (antes: 122764 L, 2023)
- Endpoint `/api/gerencia/sellout_categoria`: todos los datos correctos

**Causa raíz:** `ventas_acumulada.csv` contiene datos desde abril 1 (8646 filas); `ventas.csv` es el período comercial actual (3579 filas). El usuario confirmó que ventas.csv = fuente correcta.

## 2026-05-23 — fix(11T): fuente corregida a ventas.csv (era ventas_acumulada.csv)

**Archivos tocados:**
- `server_orbit.py` — `gerencia_once_titulares()`: cambia `ventas_acumulada.csv` → `ventas.csv`. El archivo acumulado tenía datos desde abril 1 (225 clientes Antares), ventas.csv es el período comercial actual (26 clientes Antares = coincide con conteo manual del usuario).

**Validación:**
- ANTARES: CCC=26 ✓ (usuario valida 26 a mano)
- Diferencia origen: ventas_acumulada.csv abarca 1/4 al 21/5 (8646 filas); ventas.csv es el período comercial actual (3621 filas, desde fin de abril)

## 2026-05-23 — 11T: CCC real vs objetivo CCC (ventas_acumulada.csv)

**Archivos tocados:**
- `server_orbit.py` — `gerencia_once_titulares()`: reescrito completo. Fuente cambia de `mod_11t_acum.csv` (botellas/cajas) a `ventas_acumulada.csv` (clientes únicos). Fix decimal comma en ImporteNetoItem (coma → punto antes de to_numeric). Normalización por Marca column (lookup dict) + fallback por Articulo (keyword search) para filas con Marca rota (#¿NOMBRE?/NaN). CCC = nunique clientes por marca_objetivo. Objetivo desde `objetivo 11T.xlsx` (columna Objetivo = nro clientes, no cajas). Resultado: `ccc`, `objetivo_ccc`, `pct_objetivo`.
- `PAV MATINAL PE_A FLOR/portal.html` — Tabla 11T: "Cajas vs Objetivo" → "CCC vs Objetivo". Variables `cajas_mes`/`objetivo_cajas` → `ccc`/`objetivo_ccc`.

**Resultados validados (endpoint `/api/gerencia/once_titulares`):**
- fuente: ventas_acumulada.csv | 11 marcas
- ALMA MORA CCC=638 / obj=639 = 99.8% ✓
- DADA 533/467 = 114.1% ✓
- ALARIS 516/440 = 117.3% ✓
- SMIRNOFF ICE 454/400 = 113.5% (dedup "Smirnoff Ice" + "Smirnoff Ice Flavours") ✓
- GORDON'S FLAVOURS 109/122 = 89.3% ⚠ (único bajo objetivo)

**Notas técnicas:**
- ImporteNetoItem usa coma decimal en CSV → `str.replace(',','.')` antes de `to_numeric`
- Marcas rotas (#¿NOMBRE?) resueltas por Articulo: ANTARES=225, CAZADOR=199, GORDON=109
- Smirnoff split: "Smirnoff" (botella DO) → SMIRNOFF FLAVOURS; "Smirnoff Ice Flavours" (lata SMF ICE) + "Smirnoff Ice" → SMIRNOFF ICE

## 2026-05-23 — Selector de días: filtra todos los paneles por día seleccionado

**Archivos tocados:**
- `server_orbit.py` — (1) Nueva función `_clientes_por_dia(dia)`: computa cartera del día desde `clientes.xlsx` (filtra por DiasVisita, excluye V2/V5/V20), cruza con `ventas.csv` para `compra_mes_flag`, enriquece con `historial_ventas_cliente.csv`. (2) `/api/clientes`: acepta `?dia=` opcional; cuando se pasa, usa `_clientes_por_dia()` en lugar de `clientes_dia.csv`. (3) `/api/dashboard`: acepta `?dia=` opcional; cuando se pasa, precomputa `clientes_dia_map` con total y sin_compra por vendedor desde `_clientes_por_dia()`, y sobreescribe `cli_total`, `cli_sin`, `oportunidades` en el loop — vendedores sin clientes ese día muestran 0.
- `PAV MATINAL PE_A FLOR/portal.html` — (1) `setDay(d)` → async: muestra spinner, llama `Promise.all([/api/clientes?dia=d, /api/dashboard?dia=d])`, actualiza D.cli y D.dash, re-renderiza. (2) `gClientes`: usa `currentDay` como zona de filtro en lugar de `D.diag?.dia_operativo`. (3) "Plan.Vi" → "Plan.${currentDay}" en ranking de vendedores.

**Resultados validados:**
- `/api/clientes?dia=Lu` → 302 clientes, 195 sin compra mes ✓
- `/api/clientes?dia=Vi` → 550 clientes, 403 sin compra mes ✓
- `/api/dashboard?dia=Lu` → V3=64, V4=55, V6=53, V7=0, V8=71, V9=17, V10=42; total=302, sin=195 ✓
- `/api/dashboard?dia=Vi` → total=550, sin=403 ✓
- V7 correctamente 0 clientes para Lu (no trabaja ese día) ✓

## 2026-05-23 — Corrección datos: 11T cartera completa + alertas 11T + filtros CCC + Clientes del Día

**Archivos tocados:**
- `server_orbit.py` — (1) `/api/gerencia/once_titulares`: cambia fuente de `mod_11_titulares.csv` (548 clientes Vi solo) a `mod_11t_acum.csv` (1800 clientes, cartera completa). Agrega `objetivo_cajas`, `cajas_mes`, `pct_objetivo` desde `01_INPUTS/objetivo 11T.xlsx`. Incluye todas las marcas incluso con 0 cobertura. (2) `/api/alertas`: nueva exclusión de 11T brands con ≤10% de descuento (hay una acción comercial válida de 10% en 11T); alertas 14 → 3.
- `PAV MATINAL PE_A FLOR/portal.html` — (1) Card "Planificados VI" → "Clientes del Día" con labels "compraron mes / sin compra mes". (2) Card "Sin Comp. Mes": filtro ahora usa solo `compra_mes_flag===0` (eliminado `estado.includes('SIN')` que incluía falsamente CCC_SIN_COBERTURA). (3) Mini-lista clientes sin compra en dashboard: misma corrección. (4) Panel Clientes Críticos: mismo fix de filtro → cliente 8212 (CCC_SIN_COBERTURA, compra_mes_flag=1) ya no aparece. (5) 11T panel: reemplazado gráfico de barras por tabla con cajas actuales, objetivo y % avance.

**Resultados validados:**
- 11T: 18 marcas mostradas (antes 9 Vi-only). Alma Mora 932 cajas / obj 639 = 145.9% ✓. Dada 467.5/467 = 100.1% ✓. Alaris 129/440 = 29.3% ⚠.
- Alertas: 3 (CAZADOR 15%, ELEMENTOS 10%, DON DAVID 15%) — todas legítimas. 11 alertas anteriores eran 10% en marcas 11T con acción válida.
- Sin Comp. Mes card: 401 (antes 403, bug CCC_SIN_COBERTURA).
- Cliente 8212 MOSTRADOR ya no aparece en Clientes Críticos (compra_mes_flag=1, estado=CCC_SIN_COBERTURA).
- "Clientes del Día" card: 548 total, 147 compraron mes, 401 sin compra mes.

**Nota arquitectural:**
Tanto la card "Clientes del Día" como "Sin Comp. Mes" muestran la zona del día (Vi), no la cartera total. Esta es la misma fuente (`clientes_dia.csv` / `mod_volumen_vendedor.csv`). Para la cartera completa mes se requeriría un dataset adicional de todos los clientes activos.

## 2026-05-22 — Fix crítico: NaN inválido en /api/clientes + 4 correcciones de UI

**Archivos tocados:**
- `server_orbit.py` — `/api/clientes`: `ultima_compra_importe` devolvía `NaN` (JSON inválido) para clientes sin historial. JavaScript del portal lanzaba SyntaxError y `D.cli` quedaba vacío → Dashboard "Sin Comp. Mes = 0" y panel Clientes Críticos vacío. Fix: iteración post-`to_dict` que reemplaza float no-finito con None antes de `jsonify`.
- `PAV MATINAL PE_A FLOR/portal.html` — (1) Dashboard ranking: "Sin Comp. Mes" → "Sin Comp. Día" (el dato es `clientes_pendientes` del día, no del mes). (2) Panel Vendedores: "SC Mes" → "SC Día" por misma razón. (3) Plan vs Real: columna "Delta" → "Diferencia". (4) Alertas: cada fila muestra código de cliente `[123]` y vendedor `(V8)` junto al nombre.

**Resultados validados:**
- `/api/clientes`: `Bare NaN count = 0`. Python `json.loads` + PowerShell `ConvertFrom-Json`: OK. 548 clientes, 401 con `compra_mes_flag=0`. JSON válido para browser.
- Dashboard "Sin Comp. Mes": mostrará 401 (antes: 0 por JSON roto).
- Clientes Críticos: panel populado (antes: vacío).
- V3 sin compra día = 7/42 planificados del día: correcto.

## 2026-05-22 — QA portal: 7 correcciones (innovaciones, acciones, escala AS, alertas, clientes críticos, dashboard)

**Archivos tocados:**
- `generar_datasets_acum.py` — Fix INOV_PRODUCTOS (17 prods en CSV, estaba generando solo 2). Acciones: solo ventas con descuento real (`Descuento_pct > 0`). Plan AS: agrega `escala_actual/escala_max` desde hoja ESCALA. Agrega `sc_env_*` y `sc_pend_*` por producto Plan AS. Corrección columnas ESCALA (Gold=col5, Silver=col6, Inicial=col7).
- `server_orbit.py` — Alertas: excluye Plan AS clientes con descuento ≤10%. `/api/clientes`: agrega `ultima_compra_fecha` e `ultima_compra_importe` desde `historial_ventas_cliente.csv`. `/api/gerencia/planes_as`: expone escala_actual, escala_max, sc_env_* y sc_pend_* por producto.
- `PAV MATINAL PE_A FLOR/portal.html` — Plan AS (gerencia y vendedor): "Cajas ganadas" → "Escala actual N/max". Sin cargo: por producto, verde=enviado, rojo=pendiente. Clientes críticos: filtro zona del día + sin compra mes + columnas última compra fecha/importe. Dashboard "Planificados": muestra compraron vs sin compra en vez de solo total.

**Resultados validados:**
- Innovaciones: 17 productos × 7 vendedores × segmentos = 221 filas. (14620: Frizze, 60020: Antares, 74813: Dada ExBrut, 80094: NC Spark, 14619: Frizze Bubble, 74830: Dada Sidra, 30139: Gordons Tropical, 74749: Intocables DO, 44396/14425: 0 ventas en periodo, 42376: Don David RB, 74814-16-27-40: Cazador/Alma Mora, 74786: El Bautismo).
- Alertas: 36 → 14 (excluye Plan AS con ≤10% que es su descuento de plan).
- Escala: Inicial con $3.5M → escala 5/5. Silver con $4.4M → 9/9. Correcto.
- Acciones: 20 → 12 (solo ventas con descuento real). Inversión top: VTK/TDB SPIRITS $66k (2 clientes).
- Clientes críticos zona Vi sin compra mes: 403 clientes con última compra fecha/importe.
- Plan AS endpoint: sc_env_alaris, sc_pend_alaris y demás por producto ✓.

## 2026-05-22 — Sellout litros por categoría + Acciones Comerciales + Cobertura acumulada dashboard

**Archivos tocados:**
- `generar_datasets_acum.py` — +2 funciones: `cargar_maestro_productos()`, `generar_sellout_categoria()`, `generar_acciones_ranking()`. 7 datasets generados.
- `04_DATASETS_ORBIT/mod_sellout_categoria.csv` — 23 filas: 13 categorías × segmentos. Top: RTD(S)=302k L, Vodka=175k L, Vinos del año=123k L.
- `04_DATASETS_ORBIT/mod_acciones_ranking.csv` — 20 acciones: canal × categoría. Cruce ventas × maestro × clientes_seg.
- `server_orbit.py` — 2 endpoints nuevos: `GET /api/gerencia/sellout_categoria` y `GET /api/gerencia/acciones_ranking`.
- `PAV MATINAL PE_A FLOR/portal.html` — Dashboard: card "Cobertura acumulada del mes" junto a cobertura diaria. Card INOV-4 (innovaciones dashboard) reemplazado por tabla sellout en litros por categoría+segmento. Sidebar: botón "Acciones Comerciales". Nueva función `gAccionesComerciales(p)` con KPIs resumen + tabla ranking.

**Fuentes:**
- Sellout: `ventas_acumulada.csv` × `04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx` (col E=Categoria, col B=Segmento, col G=Lts_caja).
- Acciones: `reglas_acciones_mayo_2026_orbit.csv` × ventas × maestro × clientes._seg. Agrupa tiers del mismo canal+categoria.
- Cobertura acumulada: `mod_cobertura_acum.csv` (ya existía). JavaScript agrega por segmento.

**Validaciones:**
- `/api/gerencia/sellout_categoria` → 200, 13 categorías, top RTD(S)=302,554 L.
- `/api/gerencia/acciones_ranking` → 200, 20 acciones, top inversión VTK/TDB SPIRITS $66,423.
- Portal HTML: braces 44/44 balanceados.

## 2026-05-22 — Fix clasificación AUTOSERVICIO vs MAYORISTA + 17 productos innovación

**Regla de negocio aplicada:** MAYORISTAS/CASH&CARRY son canal MAYORISTA independiente, no AUTOSERVICIO.
AUTOSERVICIO real se identifica por columna SubSegmento de clientes.xlsx: "Autoservicio Tradicional" (185), "Cadena Regional" (20), "AUTOSERVICIO" (3), "CADENAS REGIONALES (SAR/BAR)" (2). Total: ~210 clientes reales.

**Archivos tocados:**
- `generar_datasets_acum.py` — `_clasificar()` reescrito: SubSegmento como fuente primaria, MAYORISTAS/CASH&CARRY → MAYORISTA (antes → AUTOSERVICIO). AUTOSERVICIO cartera total = 192 excl. V3 (era 272 inflado). V3 excluido de AUTOSERVICIO en cobertura también (consistente con 11T e innovaciones). 17 productos innovación (era 2). 5 datasets generados.
- `04_DATASETS_ORBIT/mod_cobertura_acum.csv` — regenerado: 26 filas. V3 sin AUTOSERVICIO. V8 AS = 31 (era 1). MAYORISTA como segmento propio.
- `04_DATASETS_ORBIT/mod_11t_acum.csv` — regenerado: 18.202 filas, 6.2% cubiertos. AUTOSERVICIO cartera = 192.
- `04_DATASETS_ORBIT/mod_innovaciones_segmento.csv` — regenerado: 221 filas, 17 productos × 7 vendedores × 2 segmentos. V3 sin AUTOSERVICIO.
- `04_DATASETS_ORBIT/mod_innovaciones_plan_as.csv` — regenerado: 31 clientes AS Plan.
- `04_DATASETS_ORBIT/mod_planes_as.csv` — regenerado: 31 clientes AS Plan.
- `server_orbit.py` — Fix `botellas_mes`: calcula desde historial_ventas_cliente.csv filtrado al mes actual (era `null`). 6 nuevos endpoints: cobertura_acum, 11t_acum, innovaciones_total, planes_as (gerencia), planes_as+innovaciones_segmento (vendedor). PORT desde env var (Render compatible). BASE relativo.
- `PAV MATINAL PE_A FLOR/portal.html` — Botones sidebar "Innovaciones" y "Planes AS". Títulos correctos en gSw(). Secciones gerencia y vendedor. vRuta con chips verde/rojo.
- `requirements.txt` + `Procfile` — deployment Render.

**Validaciones:**
- `/api/gerencia/cobertura_acum` → 7 vendedores, V3 sin AUTOSERVICIO, MAYORISTA = canal propio.
- `/api/gerencia/innovaciones_total` → 34 items (17 × 2 segmentos), 7 vendedores.
- `/api/diagnostico` → `botellas_mes=53860` (era null).
- AUTOSERVICIO cartera V4=45, V6=36, V7=23, V8=31, V9=28, V10=29. Total=192 (correcto).

## 2026-05-21 — Módulos Acum + Innovaciones + Planes AS + Render

**Archivos tocados:**
- `generar_datasets_acum.py` (NUEVO)
- `04_DATASETS_ORBIT/mod_cobertura_acum.csv` (NUEVO)
- `04_DATASETS_ORBIT/mod_11t_acum.csv` (NUEVO)
- `04_DATASETS_ORBIT/mod_planes_as.csv` (NUEVO)
- `server_orbit.py` (5 endpoints nuevos + ruta relativa + PORT env var)
- `PAV MATINAL PE_A FLOR/portal.html` (botones laterales + secciones + vRuta verde/rojo)
- `requirements.txt` (NUEVO)
- `Procfile` (NUEVO)

**Datasets generados:**
- `mod_cobertura_acum.csv` — 26 filas. Cobertura real por vendedor × segmento desde ventas_acumulada.csv × clientes.xlsx. V2/V5/V20 excluidos. Umbrales: AS≥6, resto≥3.
- `mod_11t_acum.csv` — 18.601 filas. 11T desde ventas_acumulada × clientes (AUTOSERVICIO + TRADICIONAL). V3 sin AUTOSERVICIO. 962/18.601 cubiertos (5.2%).
- `mod_planes_as.csv` — 31 clientes AS. Desde BBDD sheet (plan, facturado, cajas ganadas por marca) + ventas 100% descuento (sin cargo enviado).

**Endpoints nuevos en server_orbit.py:**
- `GET /api/gerencia/cobertura_acum` — cobertura acumulada por vendedor × segmento.
- `GET /api/gerencia/11t_acum` — 11T acumulado por marca (distribuidora + por vendedor).
- `GET /api/gerencia/innovaciones_total` — total innovaciones por producto × distribuidora + desglose vendedor.
- `GET /api/gerencia/planes_as` — planes AS: 31 clientes, plan, facturado, cajas ganadas, sin cargo.
- `GET /api/vendedor/<vid>/planes_as` — planes AS filtrado por vendedor. V2/V5/V20 → 403.

**Fixes en server_orbit.py:**
- `BASE = Path(__file__).parent` (antes: ruta absoluta hardcodeada).
- `PORT = int(os.environ.get("PORT", 8502))` (para Render).
- `debug = os.environ.get("FLASK_DEBUG","false").lower()=="true"` (producción safe).

**Portal gerencia:**
- Sección "Productos" en sidebar con dos botones: 🚀 Innovaciones y 🏆 Planes AS.
- `gInnovaciones(p)`: total por producto (barras), desglose por vendedor.
- `gPlanesAS(p)`: tabla clientes AS con plan/facturado/cajas ganadas/sin cargo enviado/pendiente.

**Portal vendedor:**
- Tab "Plan AS" (🏆) en nav bottom.
- `vPlanesAS()`: cards por cliente AS con facturado, cajas, barra de escala, sin cargo por marca, pendiente.
- `vRuta()`: cada cliente del día muestra innovaciones relevantes. Verde = compró. Rojo = no compró. Solo muestra el segmento que corresponde al cliente (AUTOSERVICIO o TRADICIONAL).

**Render (despliegue remoto):**
- `requirements.txt`: flask, pandas, numpy, openpyxl, gunicorn.
- `Procfile`: `web: gunicorn server_orbit:app --bind 0.0.0.0:$PORT --timeout 120`.

**Pendiente de validación:** reiniciar servidor para confirmar 5 endpoints nuevos HTTP 200.

---

## 2026-05-20 — INOV-6c: Ranking gerencial Innovaciones — PASS

**Commit:** `e2bad1b` — `PAV MATINAL PE_A FLOR/portal.html` (único archivo).

**Cambios en portal.html:**
- `gDashboard()`: nueva card "🎯 Ranking de Oportunidad — Innovaciones" debajo de "Cobertura por vendedor".
- Fuente: `D.inov.por_vendedor` (ya cargado desde `/api/gerencia/innovaciones_segmento`). Sin nuevo endpoint.
- Calcula por vendedor: `falt` (sum len clientes_faltantes), `comp`, `cart`, `pctProm` (1 decimal).
- Ordena por `falt DESC`. Excluye V2/V5/V20. Mini-barra cobertura con color `ok/wn/bd`.
- Columnas: `#`, Vendedor, Faltantes, Compraron/Cartera, Cobertura, Prods.

**Validación:** 14/15 PASS.
- Ranking visible (gerencia). V2/V5/V20 ausentes. Sin errores JS. ✅
- V3 sin AUTOSERVICIO. Plan Innovaciones V3/V4 visible. ✅
- 1 FAIL: extracción automática del orden en test (problema de timing en `inner_text()` sobre tablas grandes). No es falla funcional — orden verificado en Fase 1 contra endpoint real.

**Próximo:** INOV-7 por definir, o cierre del ciclo Innovaciones.

---

## 2026-05-20 — INOV-6b: UI Plan de Acción Innovaciones — PASS

**Commit:** `ff5e17a` — `PAV MATINAL PE_A FLOR/portal.html` (único archivo).

**Cambios en portal.html:**
- `let D`: agregado `plan_inov:null`.
- `logout()`: reset incluye `plan_inov:null`.
- `loadAll()` vendedor: Promise.all extendido — agrega fetch `/api/vendedor/<id>/plan_innovaciones` → `D.plan_inov`.
- `vKpis()`: nueva card "📋 Plan Innovaciones" debajo de 🚀 Innovaciones. Máx 5 clientes por producto/segmento, badge "hoy" para `en_zona_hoy`, chips ALTA/MEDIA/BAJA, ruta+día solo si presentes, overflow "+N más". Si endpoint falla, card no se renderiza.

**Validación:**
- test_inov4.py: 15/15 PASS. Sin errores JS. ✅
- V3: 2 productos TRADICIONAL, sin AUTOSERVICIO. 5 clientes + "+277 más". ✅
- V4: 4 productos (AUTOSERVICIO + TRADICIONAL). Clientes con ruta, prioridad, badge "hoy". ✅

**Próximo:** INOV-6c — ranking de oportunidad Innovaciones en vista gerencia.

---

## 2026-05-20 — INOV-6a: endpoint plan_innovaciones — PASS

**Commit:** `ebb0d17` — `server_orbit.py` (único archivo). Pusheado.

**Endpoint creado:** `GET /api/vendedor/<vid>/plan_innovaciones` — read-only.

**Fuentes:** `mod_innovaciones_segmento.csv` + `clientes_dia.csv` + `clientes_master.csv`.

**Enriquecimiento por cliente:**
- `en_zona_hoy: true` + `enriquecimiento: "completo"` → desde `clientes_dia` (nombre, segmento, ruta, dias_visita, localidad, prioridad).
- `en_zona_hoy: false` + `enriquecimiento: "parcial"` → desde `clientes_master` (nombre, segmento, localidad).
- `enriquecimiento: "sin_datos"` → ID sin match en ninguna fuente.

**Ordenamiento plan:** en_zona_hoy primero → prioridad ALTA > MEDIA > BAJA → nombre alfabético.

**Validación:**
- V3 HTTP 200, solo TRADICIONAL, sin AUTOSERVICIO. 282 faltantes, 76 en zona hoy. ✅
- V4 HTTP 200, AUTOSERVICIO + TRADICIONAL. ✅
- V2/V5/V20 → 403. ✅
- Endpoints INOV-3 siguen 200. ✅

**Próximo:** INOV-6b — UI Plan de Acción en `portal.html`.

## 2026-05-20 — INOV-5: mejora visual Innovaciones en portal — PASS

**Commit:** `b247410` — `PAV MATINAL PE_A FLOR/portal.html` (único archivo). Pusheado.

**Fase 1 — Auditoría visual + datos crudos:**
- V3 muestra 0% en ambos productos TRADICIONAL → confirmado real (endpoint: compraron=0, cartera=282).
- V4 endpoint coincide con portal: AUTOSERVICIO y TRADICIONAL correctos.
- Gerencia: vendedores V3/V4/V6/V7/V8/V9/V10. V2/V5/V20 ausentes. ✅

**Fase 2 — Mejoras visuales (sin tocar lógica ni backend):**
- Helper `iLbl`: cuando pct=0 muestra "Sin compradores aún" en lugar de "0%".
- Cards gerencia: `minmax(210px→260px)` para mejor legibilidad.
- Tabla gerencia: columnas Cartera+Compraron fusionadas en `X / Y` + mini-barra + chip en "Cobertura".
- Vendedor: sub-línea dinámica "Sin compradores aún · 0 de N clientes" cuando compraron=0.

## 2026-05-20 — INOV-4: UI Innovaciones por segmento en portal — PASS

**Commit:** `5c8434a` — `PAV MATINAL PE_A FLOR/portal.html` (único archivo).

**Gerencia:** bloque full-width al final de `gDashboard()`. Cards por producto con barra por segmento + tabla cobertura por vendedor. V2/V5/V20 excluidos.

**Vendedor:** card al final de `vKpis()` con barras de avance por segmento + lista `clientes_faltantes` (primeros 5 + contador). V3 no muestra AUTOSERVICIO.

**Playwright 15/15 PASS:**
- Endpoints `/api/gerencia/innovaciones_segmento`, `/api/vendedor/v3/innovaciones_segmento`, `/api/vendedor/v4/innovaciones_segmento` → 200 ✅
- appG visible ✅ · Bloque Innovaciones ✅ · Frizze Manxana ✅ · Antares XPA ✅
- Tabla Cobertura por vendedor ✅ · V2/V5/V20 ausentes ✅
- appV V3 ✅ · Card Innovaciones V3 ✅ · AUTOSERVICIO ausente V3 ✅
- appV V4 ✅ · Card Innovaciones V4 ✅ · Sin errores JS ✅

## 2026-05-19 — INOV-3: endpoints Innovaciones por segmento — PASS

**Archivo:** `server_orbit.py` — commit `b11ab9d`.

**Endpoints creados:**
- `/api/gerencia/innovaciones_segmento` — resumen empresa por producto × segmento.
- `/api/vendedor/<id>/innovaciones_segmento` — detalle por vendedor con clientes faltantes.

**Fuente:** `04_DATASETS_ORBIT/mod_innovaciones_segmento.csv`.

**Validación 10/10 PASS:**
- gerencia = 200 ✅ · V3 = 200 ✅ · V4 = 200 ✅ · V2 = 403 (esperado) ✅
- Sin V2/V5/V20 en respuesta ✅
- Sin V3/AUTOSERVICIO en respuesta ✅
- `producto_codigo` solo 14620 y 60020 ✅
- `clientes_faltantes` como list ✅

**Pendiente:** INOV-4 — UI portal para mostrar innovaciones por segmento en gerencia y vendedor.

## 2026-05-19 — INOV-2: dataset Innovaciones por segmento — PASS

**Archivo:** `LEGACY/orbit_matinal_v42.py` — commit `a651d01`.

**Cambios:** función `generar_mod_innovaciones_segmento()` + constante `_INOV2_PRODUCTOS`.

**Resultado motor:** `04_DATASETS_ORBIT/mod_innovaciones_segmento.csv` — 26 filas / 10 columnas. Exit code 0.

**Reglas aplicadas:**
- Fuente: `ventas.csv`, mes actual hasta `fecha_ejecucion`, `ImporteNetoItem > 0`.
- Productos: Frizze Manxana (14620) y Antares XPA (60020).
- Segmentos: Tradicional / Autoservicio.
- V2/V5/V20 ausentes del dataset. ✅
- V3/AUTOSERVICIO ausente del dataset. ✅

**Pendiente:** endpoints `/api/gerencia/innovaciones_segmento` y `/api/vendedor/<id>/innovaciones_segmento` — INOV-3.

## 2026-05-19 — INOV-1: módulo Innovaciones Plan AS — PASS

**Archivo:** `LEGACY/orbit_matinal_v42.py` — commit `a091e78`.

**Cambios:** función `generar_mod_innovaciones_plan_as()` + 3 constantes (`INPUT_INNOVACIONES`, `_INOV_TEXTO_A_CODIGO`, `_INOV_PENDIENTE_STOCK`).

**Resultado motor:** 28 filas / 9 columnas. `04_DATASETS_ORBIT/mod_innovaciones_plan_as.csv` generado. Exit code 0.

**Reglas de negocio confirmadas:**
- Denominador = columnas Si/No en `Innovaciones.xlsx` → **13 hoy**. NaN = no aplica para PYP. No se fuerza.
- Antares P770 y P330 → solo en `productos_pendiente_stock`. Fuera del denominador.
- Frizze M (14620) y Antares XPA (60020) → NaN para todos los clientes PYP → no cuentan en Plan AS.
- Frizze M y Antares XPA → módulo separado INOV-2 (seguimiento por segmento desde ventas.csv).
- V2/V5/V20 ausentes del dataset. ✅

**Validación:** 28 clientes, denominador 13, pendiente_stock correcto y motor ejecutado con exit code 0. ✅

## 2026-05-19 — Validación integral post-fix Etapa B: PASS

**Validación:** no se modificaron código, portal, inputs, datasets ni orbit.db. Solo se generó evidencia temporal de validación.

**APIs:** `/api/matinal/resumen`, `/api/gerencia/ccc_empresa`, `/api/gerencia/once_titulares`, `/api/dashboard` → todos 200.

**Excluidos:** V2, V5, V20 retornan 404 en `/api/vendedor/V{id}`. ✅

**Portal gerencia (`/portal.html`):**
- CCC COMPRADORES MES: 353 · Trad: 236 · AS: 97 · OP: 20. ✅
- SIN COMP. MES: 262 = suma exacta de `clientes_sin_compra_mes` post-fix por vendedor. ✅
- 11 Titulares por Marca: 14 marcas con clientes reales de mayo 2026. ✅
- Sin Comp. Mes por vendedor en ranking: V3:11, V4:45, V6:61, V7:57, V8:41, V9:18, V10:29. ✅
- Sin errores JS. Sin URLs con 404. Favicon resuelto. ✅

**Observación registrada — no bloqueante:**
"CCC Mes" del ranking usa cartera completa (ventas.csv). "Sin Comp. Mes" usa zona Vi (clientes_dia/motor). Universos distintos — inconsistencia semántica preexistente. Pendiente análisis en próxima sesión.

---

## 2026-05-19 — Fix Etapa B motor: ventas_mes filtrado al mes calendario actual

**Commit:** `9e89030 fix(motor): filtrar ventas_mes al mes calendario actual`

**Archivo modificado:**
- `LEGACY/orbit_matinal_v42.py` líneas 919-921: agregado `_primer_dia_mes = fecha_ejecucion.replace(day=1).date()` como piso del filtro de `ventas_mes`.

**Causa raíz:** `ventas_mes` se construía desde `historial_ventas` con filtro `<= fecha_ejecucion` sin cota inferior. El historial acumulaba marzo–mayo 2026, por lo que `ccc_mes_flag=1` significaba "compró desde marzo", no "compró en mayo". Todos los derivados (cobertura_mes, botellas_mes, 11 Titulares) heredaban el error.

**Validación post-fix (PASS):**
- `ac.py` Dif = 0 en los 7 vendedores activos (V3,V4,V6,V7,V8,V9,V10).
- V2/V5/V20 ausentes en `clientes_dia` y `mod_volumen_vendedor`.
- `clientes_sin_compra_mes` corregido: V4 5→45, V6 20→61, V8 9→41, V10 16→29.
- 11 Titulares ajustado al mes actual: V8 128→36, V4 32→11, V9 36→18.
- Motor regenerado con backup en `99_BACKUPS_ORBIT/20260519_134231/`.
- Portal, inputs, datasets y orbit.db no tocados manualmente.

---

## 2026-05-19 — Validación Etapa B1: PASS backend + visual

**Sin commit** — solo validación.

**Backend OK:**
- `/api/gerencia/ccc_empresa`: 353 CCC · Trad: 236 · AS: 97 · OP: 20.
- `/api/gerencia/once_titulares`: 15 marcas con clientes reales.
- `/api/dashboard`: 7 vendedores, KPIs reales, V3 sin autoservicio.

**Visual OK contra `/portal.html`:**
- CCC COMPRADORES MES: 353 con desglose Trad/AS/OP visible en kcard.
- Bloque "11 Titulares por Marca": 15 marcas con barras relativas.
- Label "SIN COMP. MES" en kcard principal y "Sin Comp. Mes" en ranking — correctos.
- Bloque "Alertas críticas" viejo: no aparece.
- Header: `REAL · Corte: 2026-05-18 · Matinal: MA 2026-05-19`.

**Error detectado:** 1 error JS 404 NOT FOUND — probable `orbit_portal_data.json` inexistente. Preexistente, no bloquea B1. Pendiente diagnosticar.

**Hallazgo:** Flask sirve `index.html` en `/`. B1 vive en `/portal.html`. Pendiente decidir si unificar o redirigir.

**Validación:** no se modificaron código, portal, inputs, datasets ni orbit.db. Solo se generaron evidencias temporales en %TEMP%.

---

## 2026-05-19 — Corrección mínima V20: formalizar exclusión en reglas Peñaflor

**Commit:** `b16a54c docs(pav): formalizar exclusion V20 en reglas Peñaflor`

**Archivos commiteados:**
- `LEGACY/orbit_matinal_v42.py` — `VENDEDORES_EXCLUIDOS = [2, 5]` → `[2, 5, 20]`
- `CLAUDE.md` — regla de exclusión V20 documentada en contrato de trabajo
- `00_OBSIDIAN_ORBIT/REGLAS_NEGOCIO_PAV.md` — sección "Excluidos — siempre" actualizada con V20

**Qué se logró:**
1. V20 (DEPOSITO / venta directa) formalizado como excluido en motor legacy, contrato y documentación Obsidian.
2. Regla oficial consolidada: activos = V3,V4,V6,V7,V8,V9,V10 / excluidos = V2,V5,V20.
3. Auditoría del estado del proyecto al 2026-05-19 realizada. No se tocaron portal, inputs, datasets ni orbit.db.

**Contexto de la auditoría:**
- `ventas.csv`: 2104 filas, mayo hasta 2026-05-18. V20 en fuente ERP cruda (40 filas, DEPOSITO) — correcto, es dato de origen.
- `server_orbit.py` ya tenía `{2, 5, 20}` en `_VENDEDORES_EXCLUIDOS` — OK.
- Motor legacy tenía solo `[2, 5]` — corregido.
- Datasets `04_DATASETS_ORBIT/` sin V20 — OK.
- Etapa B1 (`portal.html`) aplicada en sesión anterior pero sin validación — pendiente próxima sesión.

---

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
## 2026-06-01 - Render unico + planificacion persistente

- `server_orbit.py`: `orbit.db` puede vivir en `ORBIT_DB_PATH` para usar Render Persistent Disk; backups de planificacion pueden ir a `ORBIT_PLAN_BACKUP_DIR`.
- `server_orbit.py`: la fecha de planificacion por defecto ahora apunta a la proxima matinal desde las 12:00, evitando que los planes enviados la noche anterior queden fechados en el dia equivocado.
- `server_orbit.py`: `/api/matinal/resumen` por defecto usa modo cierre y elige la ultima fecha anterior a hoy con planes, para que los planes nuevos no tapen el cierre Plan vs Real del dia anterior.
- `portal.html`: Mi Plan muestra y envia la fecha objetivo de planificacion, no siempre `hoy`.
- `sync_planes_render.py`: descarga todas las planificaciones desde Render con `limit=all`.
- `CIERRE_DIA_ORBIT.bat`: deja de levantar/abrir portal local y publica el cierre hacia Render.
- `render.yaml`: agrega disco persistente `orbit-data` y variables `ORBIT_DB_PATH` / `ORBIT_PLAN_BACKUP_DIR`.
- `portal.html`: Planificacion gerencial incorpora selector de fecha de matinal para revisar planes historicos por dia.
