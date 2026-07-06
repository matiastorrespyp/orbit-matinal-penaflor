# NEXT TASK - ORBIT MATINAL PEÑAFLOR

## Sesion 2026-07-06 - feat(11T): match por Código Art. exacto (matriz oficial)

### HECHO
- [x] 11 Titulares ahora asigna la marca por **Código Art. exacto** (matriz `01_INPUTS/11 titulares autoservicio/11_titulares_autoservicios_match_codigos.xlsx`, hoja `DETALLE_SKU_11T_AS`, 82 SKUs) como fuente primaria; texto de `Marca` = fallback (Opción A: variedades fuera de matriz igual suman a la marca). Medición sigue por marca.
- [x] `server_orbit.py`: helpers `_codigos_11t_map()` + `_marca_11t_por_codigo()`; aplicado en `gerencia_once_titulares`, `once_titulares_zona`, snapshot de `gerencia_cierre_mes` y `_cierre_once_titulares`. `tools/generar_cierre_mensual.py`: `_marca_11t()` reescrito igual.
- [x] Validado: 82 códigos, endpoints 200, CCC sin regresión, 0 filas cambian de marca sobre `ventas_acumulada.csv`.

### PENDIENTE / A TENER EN CUENTA
- [ ] **Commit + deploy a Render NO hechos** (esperando aprobación). Al commitear: `server_orbit.py`, `tools/generar_cierre_mensual.py`, CHANGELOG/NEXT_TASK **y el input** `01_INPUTS/11 titulares autoservicio/11_titulares_autoservicios_match_codigos.xlsx` — sin ese archivo en Render el 11T cae al match por texto (comportamiento previo, no rompe pero no aplica el código). El loader versiona por mtime.
- [ ] Los drill-down `/api/gerencia/11t_empresa` y `11t_vendedor` leen el legacy `mod_11_titulares.csv` (lo genera `LEGACY/orbit_matinal_v42.py`, otra lineage) → NO fueron migrados al match por código. Ya hoy pueden diferir de la tarjeta principal (vivo vs dataset legacy). Si se quiere que también usen código, hay que decidir si se regenera ese dataset o se migran esos endpoints a cálculo en vivo desde ventas.
- [ ] La matriz cubre solo SKUs de Autoservicios. Si aparece una variedad NUEVA de una marca titular, conviene agregar su `codigo_articulo` a `DETALLE_SKU_11T_AS` (igual suma por texto mientras tanto).

## Sesion 2026-07-03 - feat(acciones comerciales): tarjetas de acciones ON

### HECHO
- [x] Sección "🌙 Acciones ON" en la pantalla de Acciones Comerciales (gerencia + vendedor) con las 6 acciones del `...penaflorON.xlsx` de julio. Tarjetas informativas (combo sin cargo) + modal con productos elegibles por subcanal/LC (no vigentes resaltados).
- [x] Backend `_acc_on_cards()` + `acciones_on` en el payload; motor de inversión intacto. Validado por endpoint + Playwright (login gerencia).

### PENDIENTE / A TENER EN CUENTA
- [ ] **Commit + deploy a Render NO hechos** (esperando aprobación). Incluir `server_orbit.py`, `portal.html`, CHANGELOG/NEXT_TASK **y el input** `01_INPUTS/ACCIONES COMERCIALES/2026-07/acciones_comerciales_julio_2026_orbit_penaflorON.xlsx` — sin ese archivo en Render la sección ON sale vacía (mismo criterio que los otros inputs de acciones). El `_acc_mes_sig` ya versiona por mtime, así que al resubir el xlsx el payload se refresca solo.
- [ ] Convención para meses siguientes: subir `acciones_comerciales_<mes>_..._penaflorON.xlsx` en `01_INPUTS/ACCIONES COMERCIALES/<YYYY-MM>/`. El sistema autodetecta el `*ON.xlsx` del mes; sin tocar código.
- [ ] Las ON no tienen mapeo de vendedor (aplican por canal ON/VTK/TDB/Catering) → hoy se muestran a todos los vendedores. Si gerencia quiere filtrar por vendedor de On Premise, definir la regla.

## Sesion 2026-07-03 - feat(incentivo dada): botón + cobertura Dada Tinto Verano

### HECHO
- [x] Gerencia: botón "🍷 Incentivo Dada" bajo Plan Frizze. Hero con 01_INPUTS/dadatinto.png (copiada a la carpeta del portal → `/dadatinto.png`) + tarjeta de cobertura (KPIs, barra de avance, por vendedor, tabla de clientes).
- [x] Backend `/api/gerencia/incentivo_dada`: objetivo y código parseados de DADAVERANOOBJ.xlsx; ventas de dadatinto.csv; cliente cubierto = autoservicio + compra válida + ≥6 bot.; excluye V2/V5/V20.
- [x] Validado: 200; objetivo=38 logrado=22 faltan=16 avance=57.9% (V8=14, V10=6, V4=2); imagen 200. Server local :8502 reiniciado.

### PENDIENTE / A TENER EN CUENTA
- [ ] **Commit + deploy a Render NO hechos** (esperando aprobación). Al commitear: incluir server_orbit.py, portal.html, CHANGELOG/NEXT_TASK y el asset `PAV MATINAL PE_A FLOR/dadatinto.png`; los inputs (dadatinto.csv, dadatinto.png, DADAVERANOOBJ.xlsx) NO se commitean salvo orden — pero OJO: si Render necesita dadatinto.csv/DADAVERANOOBJ.xlsx para computar, hay que definir cómo llegan (¿cierre/subida?). Sin esos inputs el endpoint devuelve 404 en Render.
- [ ] Confirmar con gerencia la definición de "cubierto": hoy = autoservicio + ≥6 botellas (regla Cobertura AS). Si quieren CCC puro (compra >0 sin umbral) o incluir otras superficies, ajustar `_incentivo_dada`.
- [ ] ¿Falta vista de vendedor (cada vendedor ve solo sus clientes Dada)? El pedido fue solo gerencia; si lo quieren, replicar patrón Frizze.

## Sesion 2026-07-02 - feat(acciones): tarjeta caja mixta almacén/kiosco + review de alertas

### HECHO
- [x] 2 tarjetas nuevas (ACJ26-022 20% Los Árboles+Trapiche; ACJ26-023 15% Smirnoff+Gordon's) para V3/V4/V6/V8/V10 en Almacén/Kiosco, 1 caja mixta/cliente/mes. En CSV julio + detalle. Visibles en gerencia y esos vendedores; V7/V9 no.
- [x] Alertas: tope Planes AASS solo a clientes del plan; "TODOS ..." como genérico + CERVEZA mapeada; `_acc_norm` elimina apóstrofes (Gordons=Gordon's). Footprint validado por acción, sin regresiones.
- [x] Detalle consciente de categoría (Smirnoff bajo Spirits no trae Smirnoff Ice/RTD).

### PENDIENTE / A TENER EN CUENTA
- [ ] **Gerencia**: en julio hay un 25% en Smirnoff Ice (cód 35103) y 6% en Smirnoff Ice Flavours (35105) SIN acción en el catálogo → alertan. En junio existía ACJ26-027 (35103 al 25%). Si sigue vigente, agregar la acción al CSV de julio; si no, la alerta es correcta.
- [ ] Verificar en Render el modal de ACJ26-022/023 (gerencia + un vendedor que aplique) y que la tarjeta aparezca en el orden correcto.

## Sesion 2026-07-02 - fix(acciones comerciales): modal encima + marcas reales del maestro

### HECHO
- [x] Detalle de categoría ahora abre en **modal encima** (`.accd-*` sobre `.emod-bg`), no al fondo. Cierra por ✕ / click afuera. Diseño propio (cabecera magenta, chips por segmento).
- [x] Marcas reales resueltas del **maestro 04D** (no hardcode): `_acc_marcas_maestro()` + `_acc_enriquecer_grupo()`. VDA Alto → Alma Mora, etc. Familias por Linea Comercial; productos/subreglas literales.
- [x] Validado: VDA Alto incluye Alma Mora; RTD Latas literal; endpoints 200; JS parsea; screenshot del modal OK. Commiteado + pusheado + deployado a Render.

### PENDIENTE / A TENER EN CUENTA
- [ ] Verificar en vivo en Render el modal (gerencia + vendedor) tras el deploy y que las marcas por segmento se vean bien en mobile.

## Sesion 2026-07-02 - feat(acciones comerciales): esquema julio + detalle click

### HECHO
- [x] Backend `server_orbit.py`: `_acc_detalle_map()` lee `detalle_categorias_*.csv` del mes (';' UTF-8-BOM) y arma `{detalle_click_ref: {categoria_tarjeta, items[]}}`, cacheado por mtime.
- [x] `_acciones_mes_payload_uncached`: agrega por acción `categoria_tarjeta`, `mostrar_detalle_click`, `detalle_click_ref` (lista), `detalle_categorias` (grupos resueltos, multi-ref por `|`), `orden_visual`. Acciones ordenadas por `orden_visual` ASC (sort estable → junio conserva orden).
- [x] Frontend `portal.html`: chip `🗂 categoria_tarjeta` (helper `accCatChip`) en tarjeta vendedor y gerencia; clic abre `accShowCat` con marcas/líneas del detalle. `id_accion` intacto. Junio sin cambios (chip vacío).
- [x] Validado: `_acc_detalle_map` 11 refs; payload julio 21 acciones orden ASC, multi-ref OK; endpoints gerencia/V4/V3 → 200; JSON serializa (int/bool nativo); compat junio OK.
- [x] **Autoactualización por mes**: `_acc_mes_dir()` elige la carpeta del mes en curso (AR) con fallback al no-futuro; `_acc_mes_sig` incluye el mes → flip automático al cambiar de mes sin restart. Probado en 5 escenarios.
- [x] **Commiteado y pusheado a master → deploy Render** (esta sesión).

### PENDIENTE / A TENER EN CUENTA
- [ ] Verificar en vivo en Render tras el deploy: `/api/gerencia/acciones_mes` (21 acciones, orden ASC) y el clic de categoría en gerencia/vendedor (screenshots). El portal en 8502 no se levantó en esta sesión.
- [ ] Al cambiar de mes: subir `acciones_comerciales_<mes>_2026_penaflor.csv` + `detalle_categorias_*.csv` a `01_INPUTS/ACCIONES COMERCIALES/<YYYY-MM>/`. El sistema toma el mes EN CURSO solo (no hace falta tocar código). Subir el mes siguiente por adelantado no adelanta el cambio.
- [ ] El `.xlsx` de julio no existe (solo los 2 CSV); Orbit lee el CSV. Si más adelante se agrega el xlsx, el loader sigue tomando el CSV principal (se salta explícitamente `detalle_categorias*`).

## Sesion 2026-07-01 - fix(planes as): escala del mes por nombre de archivo

### HECHO
- [x] `_cargar_escala_df()` (`generar_datasets_acum.py`) ahora elige el `escala<mes>.xlsx` por el MES actual (helper `_archivo_del_mes` + `_MESES_ES`), no por mtime. Fallback a mtime si no hay archivo del mes.
- [x] Convención establecida: subir cada mes `escala<mes>.xlsx` a `01_INPUTS/Planes AASS/` (ya está `escalajulio.xlsx`). No hay que tocar código.
- [x] Validado: elige `escalajulio.xlsx` en julio; `generar_datasets_acum.py` regenera `mod_planes_as.csv` OK.

### HECHO (ampliación)
- [x] Misma regla por mes aplicada a `sincargos*.xlsx` (helper `_ordenar_por_mes`): `_cargar_sincargos_mes`, `_cargar_planfrio_mes`, `_bbdd_desde_sincargos`. Convención `sincargos<mes>.xlsx`.

### PENDIENTE / A TENER EN CUENTA
- [ ] Al cambiar a agosto: subir `escalaagosto.xlsx` **y** `sincargosagosto.xlsx` a `01_INPUTS/Planes AASS/`. El sistema los toma solos.
- [ ] Falta `sincargosjulio.xlsx`: hoy (julio) el motor cae al de junio (fallback correcto). Subirlo cuando esté para medir sin cargos de julio.
- [ ] Este cambio es en el motor de datasets (`generar_datasets_acum.py`). Se aplica al **regenerar datasets** (cierre / BAT). Si el portal en Render debe reflejarlo, requiere el pipeline de datasets del deploy.

## Sesion 2026-07-01 - feat(portal): botón Plan Frizze (HECHO + DEPLOYADO a Render)

### HECHO
- [x] Endpoints `GET /api/gerencia/plan_frizze` y `/api/vendedor/<vid>/plan_frizze` en `server_orbit.py` (`_plan_frizze_config` parsea `01_INPUTS/PLAN FRIZZE/planfrizze.xlsx`; `_plan_frizze_clientes` arma tarjetas en vivo desde ventas.csv + clientes.xlsx + 04D).
- [x] Portal: botón en gerencia (bajo Incentivo FARO) + tab vendedor (bajo FARO, visible solo si tiene cliente del plan). Cabecera con las 2 imágenes de producto + tarjetas por cliente; clic en sin cargo → fecha de facturación; alerta por mezcla de variedad (3+1 debe ser misma variedad).
- [x] Imágenes `frizze_blue.jpg`/`frizze_bubble.jpg` en la carpeta del frontend.
- [x] Validado por test_client, en vivo (8502) y screenshots reales (gerencia + V8). node --check OK.
- [x] **Commiteado y pusheado** (`38119e4`) — incluye el `planfrizze.xlsx` (el parser lo lee en Render).
- [x] **Deployado y verificado en Render** (`orbit-matinal-penaflor.onrender.com`): `/api/gerencia/plan_frizze` → 2 clientes (301 CAMAR SRL / V8), imágenes 200. Bitácora en `00_OBSIDIAN_ORBIT/BITACORA_2026-07-01.md` (`d25351a`).

### PENDIENTE / A TENER EN CUENTA
- [ ] Datos en 0 para 301/1443: es real (aún sin ventas Frizze del mes vivo). Verificar en julio cuando haya facturación que litros/$/sin cargos/alerta pueblen.
- [ ] Cliente **1443 no está en el maestro `clientes.xlsx`** ni tiene vendedor asignado → aparece como "Dato no disponible" en gerencia y no lo ve ningún vendedor. Si debe verlo un vendedor, hay que darlo de alta en el maestro.

## Sesion 2026-06-30 - fix(cierre): cierre de mes corre de verdad + portal lo descubre por carpeta (HECHO local, sin commitear)

### HECHO
- [x] Diagnóstico: el cierre detectaba mayo (ventas_mes.csv viejo) y no hacía nada; además el .bat nunca alimentaba el listado del portal (07_CIERRES_MENSUALES). El selector de mes ya existía (portal.html:3689), faltaban cierres para que apareciera.
- [x] `tools/preparar_ventas_mes.py` (NUEVO): regenera ventas_mes.csv desde ventas.csv (`;`/latin1 → `,`/utf-8, FechaComprobante ISO, 58 cols). Backup del previo.
- [x] `CIERRE_MES_ORBIT.bat`: corre el prep antes de versionar (solo modo automático sin args); rama "nada nuevo" ahora es `:fin_nada` (no más "LISTO" engañoso). CRLF normalizado.
- [x] `tools/cerrar_mes.py`: versiona también ventas_acumulada_<MMAAAA>.csv (11T trimestral).
- [x] `server_orbit.py`: `gerencia_cierres_historicos` descubre cierres desde `01_INPUTS/cierres mes/` (no solo el índice 07) + `_cierre_manifest_versionado`. Validado por test_client: total_cierres=2 (junio + mayo), junio reconstruido OK.
- [x] Cierre de JUNIO generado en local: `01_INPUTS/cierres mes/*_062026.*` (5 archivos).

### HECHO (continuación)
- [x] Sell Out del cierre ahora incluye V20 Depósito en cada categoría vs objetivo de empresa (total + desglose informativo) — espejo del dashboard. `_cierre_extras_versionado`.
- [x] Innovaciones del cierre ya NO dan 0: se usa `_gda().INOV_PRODUCTOS` (22 productos) en vez del parser viejo `_leer_innovaciones`. Corrige detalle + ranking (V8 ALVAREZ VANESA 115 clientes, antes 0).
- [x] Mejor en VOLUMEN del cierre ahora por alcance del objetivo mensual (no litros+dinero), solo ese ganador; score general intacto. `_cierre_ranking_payload(avance_map)`. Junio→V4 181,8%, mayo→V3 144,9%.
- [x] Sell Out del cierre con drill-down por categoría → subcategoría → marcas → varietales (`_renderCierreSellout`, espejo del dashboard). Se quitó la tarjeta "Del cual · V20 Depósito" (sigue sumado en el total).

- [x] Acciones Comerciales de junio en el cierre: RESUELTO. El catálogo viaja versionado (`01_INPUTS/cierres mes/acciones_<MMAAAA>.csv`, que cerrar_mes.py ya copia) y el server lo procesa con `_cierre_acciones_junio_schema` (esquema nuevo, helpers del motor live, sobre ventas_mes congelado). Junio: 26 acciones, inversión 36,1M (= motor live). Mayo intacto. Ya NO hace falta registrar mes a mes en `_ACC_REGLAS_POR_MMAAAA`.

### PENDIENTE
- [ ] Verificar en Render (gerencia → Cierre de Mes, mes 2026-06): tarjeta Sell Out con total incluido depósito, ranking con innovaciones reales, drill-down de Sell Out y tarjeta de Acciones Comerciales con datos.

## Sesion 2026-06-30 - feat(gerencia): Innovaciones con total de cobertura del mes (HECHO, sin commitear)

### HECHO
- [x] Control del dato de Innovaciones gerencia: dataset y endpoint correctos (22 productos, cartera 2031, cobertura mes 0–43). `pct_cobertura` del CSV es fracción pero nadie la usa (todos recalculan) → se deja.
- [x] `gInnovaciones` (portal.html): chip "<n> mes" (total cobertura acumulada del mes = `prod.compraron`) a la derecha de cada innovación, junto al % y al total del día. Solo frontend, sin reinicio de server.

### PENDIENTE
- [ ] Verlo en el portal vivo (server 8502 / Render cuando el usuario lo pida): recargar pantalla Innovaciones y confirmar los 3 chips (% · mes · día).

## Sesion 2026-06-30 - feat(gerencia): Clientes incluye Depósito (codven=1) (HECHO, sin commitear)

### HECHO
- [x] `_clientes_maestro(incluir_deposito=False)` + `clientes_buscar`/`cliente_ficha` con `incluir_deposito=True`. Depósito (codven=1, 29 clientes) ahora seleccionable en la pantalla de Clientes de gerencia. Métricas con objetivo sin cambios.
- [x] Validado en local (2097 sin depósito / 2126 con depósito). Ver CHANGELOG_AI 2026-06-30.

### PENDIENTE
- [ ] Probar en el portal vivo (server 8502): buscar un cliente del depósito y abrir su ficha. (¿Reiniciar server / deploy a Render cuando el usuario lo pida.)
- [ ] Opcional UX: ¿mostrar el chip como "Depósito" en vez de "V1"? No pedido; dejar como está salvo que se solicite.

## Sesion 2026-06-29 - feat(FARO): premios (millas) + métrica Antares por SKU (HECHO, sin commitear)

### HECHO
- [x] Premios (millas) del xlsx en ambos perfiles: badge 🎟 por categoría al alcanzar (logrado≥objetivo) + total millas ganadas/posibles por vendedor y supervisor. Alaris+FLM 2000, Antares 1000, Smirnoff 1000.
- [x] Métrica Antares corregida a **por SKU sin umbral** (cada SKU =1; XPA/Porrón330/660 [60020/61/62] =2, sin tope por cliente). Antes era por cliente con tope 2.
- [x] Validado (datos reales + Playwright ambos perfiles, sin errores de consola). Ver CHANGELOG_AI 2026-06-29.

### HECHO (cont.)
- [x] Deploy a Render (commit 2d5dc98 pusheado a master).
- [x] Objetivos de Antares: se usan TAL CUAL están en el xlsx (decisión usuario 2026-06-29: "el objetivo es el del archivo, no hay que recalibrar"). El conteo por SKU puede superar holgadamente el objetivo y está bien así.

## Sesion 2026-06-29 - feat(gerencia): V20 "Depósito" como línea aparte (HECHO, sin commitear)

### HECHO
- [x] Sell Out gerencia incluye V20 Depósito: `total_ruta` (41.609, sin cambios) + `total_deposito` (7.055) = `total_general` (48.664, concilia con proveedor 47.480). Sub-card "📦 V20 Depósito" en el portal.
- [x] 11T: `ccc_deposito` por marca + `ccc_deposito_total` (72); columna "Dep.V20". Innovaciones y Cobertura: bloque `deposito` informativo. Todo solo-logrado, sin objetivo/faltantes (V20 no tiene cartera en el maestro).
- [x] V20 sigue EXCLUIDO de avance/objetivo, FARO, Planes AS, dashboard (decisión usuario). No se tocó `_VENDEDORES_EXCLUIDOS` global. Bloques depósito NO filtran por Empresa (depósito factura parte vía P&P Logística pero es la misma entidad V20).
- [x] Validado contra datos reales (server local). `py_compile` OK, portal `node --check` OK. Ver CHANGELOG_AI 2026-06-29.
- [x] **Paridad en el cierre de mes** (HECHO): helper `_sellout_con_deposito()` compartido; `_leer_ventas_mes_csv(incluir_deposito=)` + `_leer_ventas_mes_cacheado(incluir_deposito=)` (bandera en la clave de caché, no contamina CCC/once_titulares/ranking del cierre). Bloque depósito en `gerencia_cierre_mes` (vivo) y `_cierre_extras_versionado` (histórico). Sub-card "📦 V20 Depósito" en la pantalla Cierre de Mes. Validado: cierre `total_ruta=47.565`, `total_deposito=12.324`, `total_general=59.890` (ventas_mes.csv = mes congelado completo).

### PENDIENTE
- [ ] Push a Render (validar serialización nativa y tiempo según [[feedback_render_deploy_validacion]]).

## Sesion 2026-06-25 - fix(cierre): xlsx inflado colgaba el PASO 1 del cierre (HECHO)

### HECHO
- [x] Causa raíz: `01_INPUTS/producto activos.xlsx` inflado a 19,2 MB (260 filas reales, rango usado hasta fila 1.048.527). `cargar_productos()` del motor legacy tardaba minutos leyéndolo → el cierre parecía colgado en `[5/8]`.
- [x] Reparado el archivo (solo rango real): 19,2 MB → 17,8 KB. Backup del original en `99_BACKUPS_ORBIT/producto_activos_bloated/`. Equivalencia validada (idéntico salvo ruido de float en col litros). Motor legacy completa en 338 s (antes colgado).

### HECHO (perf 11T)
- [x] Optimizada la sección "11 TITULARES" en `LEGACY/orbit_matinal_v42.py` (~1367-1381): se pre-filtra `marcas_mes` por (cliente_id, vendedor_codigo) una vez por cliente (vectorizado, mismo `==` y manejo de NaN) y `match_marca_objetivo` corre solo sobre el subconjunto del cliente. Salida `mod_11_titulares` IDÉNTICA validada celda a celda (5910×17). Motor 338 s → 32 s.

### PENDIENTE
- [ ] Recordatorio operativo: si en el futuro `producto activos.xlsx` vuelve a exportarse de Gescom inflado (>1 MB para ~260 productos), el cierre se volverá a ralentizar. Reexportar limpio o re-aplicar la reparación.

## Sesion 2026-06-24 - fix(plan-vs-real): ancla en último día cerrado (HECHO, sin commitear)

### HECHO
- [x] Causa raiz: gerencia Plan vs Real usaba modo "cierre" con `fecha < today_ar`, excluyendo el plan de hoy aun despues del cierre -> mostraba el dia anterior.
- [x] `server_orbit.py` (`matinal_resumen`, modo "cierre"): ancla = ultimo snapshot de `_real_dia_resultado()` (ultimo dia cerrado); plan mas reciente con `fecha <= last_snap`. Mantiene plan(hoy) vs real(hoy) hasta el proximo cierre.
- [x] Validado local: ancla 2026-06-24 (antes 23); real = acum(24)-acum(23). `ast.parse` OK.

### PENDIENTE
- [ ] Push a Render para que el gerente lo vea en produccion (validar tiempo/200 segun [[feedback_render_deploy_validacion]]).

## Sesion 2026-06-23 - fix(acciones): doble conteo de litros bajo acciones (HECHO, sin commitear)

### HECHO
- [x] Causa raiz: el portal sumaba `litros` de cada accion por separado; una misma linea matchea varias acciones (canal + Planes AASS + 11T + Innovaciones) -> doble/triple conteo. Daba 57.146 L > sell out total 28.635 L (imposible).
- [x] `server_orbit.py` (`_acciones_mes_payload_uncached`): bloque `totales` deduplicado por union de lineas (`matched_idx`/`prev_idx`). Calculo por accion intacto.
- [x] `portal.html` (`gAccionesComerciales`): KPIs de encabezado usan `dat.totales`, fallback a `reduce`.
- [x] Validado endpoint: totales.litros = 20.775,3 L < 28.634,7 sell out. Status 200, serializa OK.

### HECHO (continuacion)
- [x] Detalle de clientes por tarjeta agrupado por vendedor, con subtotal por vendedor (importe/dto/litros/cli) + columna "Lineas". `portal.html` `accShowDetalle`. Vista gerencia y vendedor.
- [x] Revision de las 28 tarjetas: numeros coherentes (ver CHANGELOG). Inversion = valorDescuento real (no IVA).

### HECHO (fix 500 Render)
- [x] `/api/gerencia/acciones_mes` daba 500 en Render por timeout de gunicorn (30s); la vista gerencia tardaba >30s y nunca cacheaba. Optimizado `_match` (pred por combinacion unica, no fila-por-fila) + warmup en hilo al arranque. Validado local 200 + cache.

### HECHO (acordeon detalle)
- [x] Detalle por tarjeta en acordeon: resumen por vendedor (colapsado) + clic para ver clientes de ese vendedor. `portal.html` `accShowDetalle` + `accTogVend`.

### PENDIENTE
- [ ] Verificar visualmente: clic en clientes de una tarjeta => lista de vendedores con nro de clientes; clic en un vendedor => se abren sus clientes.
- [ ] Verificar EN VIVO tras deploy: `curl https://orbit-matinal-penaflor.onrender.com/api/gerencia/acciones_mes` => 200 (no 500). Y que la pantalla cargue.
- [ ] REVISAR config Render: el timeout efectivo parece ser 30s (gunicorn default) aunque Procfile/render.yaml dicen `--timeout 120`. Probable override en el start command del dashboard de Render. Subir a 120 ahi da margen extra.
- [ ] Verificar visualmente: KPI "Litros bajo acciones" ~20.775 L; clic en clientes de una tarjeta => agrupado por vendedor.
- [ ] CATALOGO (con negocio): ACJ26-018 ≡ ACJ26-019 (mismo set Alma Mora On Premise); ACJ26-020 y ACJ26-025 con 0 clientes. Revisar definicion de reglas.
- [ ] (Opcional) Mostrar % cobertura: litros bajo acciones / sell out total.

## Sesion 2026-06-23 - Blindaje Git de los cierres (AMBOS .bat HECHO)

### HECHO - AMBOS .bat blindados, commiteados y pusheados
- [x] `CIERRE_DIA_ORBIT.bat` blindado (commit `7a8e060`, en `origin/master`).
- [x] `CIERRE_MES_ORBIT.bat` blindado con el mismo patron (commit `4732259`, en `origin/master`).

Patron comun aplicado a los dos:
- Preflight Git: aborta si hay cambios funcionales (`.py`/`.bat`/`portal.html`/config) fuera de las rutas operativas permitidas.
- `git pull --rebase origin master` al inicio, solo con repo 100% limpio; con inputs operativos cargados omite el pull.
- Segundo guard tras el `git add` operativo: aborta a `:fin_error` si queda algo fuera del allowlist. No usa `git reset --hard` ni `git clean`.
- Se elimino el `pull --rebase` posterior al commit. `LISTO` solo tras push exitoso; exit codes explicitos (`exit /b 1` error / `exit /b 0` ok).
- Ambos en CRLF garantizado por `.gitattributes` (`*.bat text eol=crlf`): `git ls-files --eol` -> `w/crlf` en working tree.

Diferencia del mensual: "sin cambios nuevos" NO es error (re-cerrar un mes ya cerrado es valido, `cerrar_mes.py` devuelve 0) -> sale por `:fin_ok`.

### PENDIENTE
- Validar en el proximo cierre REAL (diario): repo limpio -> pull inicial OK -> regeneracion OK -> commit operativo -> push OK -> Render actualizado.
- Validar en el proximo cierre de MES real: repo limpio -> pull inicial -> `cerrar_mes.py` OK -> commit de `cierres mes/` -> push -> Render.

## Sesion 2026-06-23 - Innovaciones: destrabar cierre (A) + nueva medición por subcanal (B)

### HECHO — Parte A (validado, NO pusheado aún)
- `legacy/orbit_matinal_v42.py` `generar_mod_innovaciones_plan_as`: tolera Excel sin hoja `Cuadro Inov` (WARN + DataFrame vacío) en vez de abortar el cierre. Causa del "no actualizó nada" del 23/06.
- Datasets regenerados a 2026-06-23 vía `REGENERAR_DATOS_ORBIT.bat` (OK).
- `CIERRE_DIA_ORBIT.bat`: ahora ABORTA si la regeneración falla (`if errorlevel 1` en vez de `if exist ...csv`). Antes publicaba datasets viejos en silencio — el motor crasheaba desde el 17/06 (8 cierres) y nadie se enteraba. Validado en cmd.

### OJO — datos de Render quedaron desfasados 17/06→22/06
- Entre el 17/06 y el 22/06 Render recibió ventas/resultado nuevos pero datasets del 17/06. Recién la corrida del 23/06 08:58 los puso al día (data del 22/06). Las tarjetas históricas de esos días mostraban números del 17.

### PENDIENTE — cerrar el día
- Falta correr `CIERRE_DIA_ORBIT.bat` (commit + push a Render). Antes, el usuario decide si pega un `ventas.csv` nuevo del día (hoy sigue el del 22/06 17:23).

### PENDIENTE — Parte B (nueva medición de Innovaciones, aprobada por el usuario)
Medir por **producto × subcanal**: cuántos clientes compraron (verde) y cuántos NO (rojo), por cada subcanal.
- **Productos:** leer los 22 desde `Innovaciones.xlsx` (no hardcodear `_INOV2_PRODUCTOS`; los 7 nuevos: 14620, 42337, 60020, 60021, 60022, 74882, 74884). `_acc_innovaciones_codigos` en server ya lee el archivo nuevo bien (sheet 0, header=None).
- **Subcanales (5)** desde `SubSegmento`:
  - Autoservicio = Autoservicio Tradicional + AUTOSERVICIO + Cadena Regional + CADENAS REGIONALES (SAR) + Large Format + Proximity
  - **Almacén** = Almacen/Despensa + ALMACENES + **tradicionales no-kiosco** (Carniceria/Granja, Fiambreria, Panaderia, Casa de Pastas, Verduleria, Heladeria, Resto de Tradicionales) ← decisión del usuario
  - Kiosco = Kiosco/Maxikiosco + Kiosco - 365 + KIOSKO
  - On Premise = Resto de On Premise + Vinoteca(s) + ON PREMISE(/NOCHE/DIA) + Bar/Restaurant + RESTAURANT(/CON BARRA) + BAR + Estacion de Servicio* + Eventos + Canchas/Instituciones/Colegios/Centros
  - Mayorista = Mayoristas + MAYORISTAS + Mayorista Regionales + CASH&CARRY
  - Empleados → excluir
- **Reglas:** vendedores activos V3,V4,V6,V7,V8,V9,V10; excluir V2/V5/V20; **V3 solo Tradicional** (Almacén+Kiosco; sin AS/Mayorista/On Premise).
- Reconstruir `generar_mod_innovaciones_segmento` (5 subcanales + productos del archivo) y actualizar endpoints `innovaciones_segmento`/`innovaciones_total` + tarjeta en `portal.html` (verde compraron / rojo no compraron por subcanal).

## Sesion 2026-06-22 - Plan Frío: excluir latas Smirnoff BC

### HECHO (validado + pusheado a Render)
- `generar_datasets_acum.py` `generar_planes_as`: detección de plan frío por **Articulo** (ICE + SMIRNOFF/SMF), no por Marca. Las latas BC (Bitter Citric, COD 35108/35109, Marca='Smirnoff Ice Flavours' en ERP) ya NO cuentan como enviado — son de una acción comercial.
- Regenerados `mod_planes_as.csv` + `mod_sincargos_envios.csv`. pf_enviado {30063,390,7219,30017}→{2410}.
- Docs: CHANGELOG, bitácora 2026-06-22, REGLAS_NEGOCIO_PAV (Plan Frío).

### OJO
- Al regenerar `mod_planes_as.csv` se refresca todo el dataset desde la `ventas.csv` actual (facturado/escala/fecha_calculo cambian, no solo plan frío). Es el flujo normal de regeneración.

## Sesion 2026-06-19 - Incentivo FARO: Antares por cliente

### HECHO (validado + pusheado a Render)
- `server_orbit.py` `_faro_detalle_vendedor` rama `antares`: logrado = Σ peso por **cliente** (1, o 2 si compró XPA/Lager-botella), no por variedad. Antes inflaba sumando peso por cada SKU ≥6 bot. V4 6/8 → **3/8** (2 clientes). `compradores` = 1 fila por cliente.
- `portal.html`: leyenda de regla FARO actualizada (Antares 1 cob/cliente, 2 si XPA/Lager botella).
- Docs: CHANGELOG, bitácora 2026-06-19, REGLAS_NEGOCIO_PAV (nueva sección Incentivo Club FARO).

## Sesion 2026-06-19 - Sell Out: fix RTD (S) + drill-down varietal + Faltan/TOTAL

### HECHO (validado + pusheado a Render — commit 83b84df)
- `09_CONFIG/maestro_04D_productos.csv`: +2 productos faltantes — `35108` SMF BC RUBYORANGE → RTD (S); `14620` FRIZZE MANXANA → RTD. Resuelve el leak de una venta RTD (S) que caía en RTD regular.
- `server_orbit.py` `_marcas_de_grupo`: agrega `varietales:[{nombre,litros}]` por Articulo.
- `portal.html`: tarjeta Sell Out — marcas clickeables que abren litros por varietal (`_soMarcas`/`soMExp`).

### PENDIENTE
- Commit + push a master (Render autodeploy) cuando el usuario apruebe.
- Validación visual en el portal (abrir RTD → RTD (S) debe mostrar SMF BC; click en marca → varietales).
- OPCIONAL: el xlsx maestro (`01_INPUTS/04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx`, fuente de `mod_sellout_categoria.csv` que genera `generar_datasets_acum.py`) tampoco tiene 35108/14620 → quedan fuera de ESA tarjeta (la otra, `sellout_categoria`). El portal en vivo usa el CSV (ya corregido); evaluar si vale cargarlos también al xlsx.


## Sesion 2026-06-18 - Ruta del vendedor: orden de visita + 11T/Innovaciones colapsables

### HECHO (validado en local, pendiente de deploy)
- `/api/vendedor/<vid>/ruta`: orden por columna `Orden` (Orden<=0 al final); agrega titulares_comprados/once_t_total e innovaciones por cliente (inov_comprados/faltantes/n/total) desde ventas.csv + mod_innovaciones_segmento.csv. V3 sin AS.
- `portal.html` `vRuta`: clientes en orden de visita; chips colapsables "11 Titulares" e "Innovaciones" con pills verde (comprado) / amarillo (faltante).

### OJO / DATO
- La columna `Orden` esta poblada al ~60% (V3/V6/V10 casi completos; V7/V9 casi vacios → esos caen al final y se muestran con nº correlativo del render). Si se quiere orden real para todos, hay que cargar `Orden` en clientes.xlsx (fuente ERP).
- V3 tiene clientes AUTOSERVICIO en su cartera fisica (aparecen en la ruta) pero sin innovaciones AS. Si se quiere excluirlos de la ruta tambien, definirlo.

### PENDIENTE
- Commit + push a master (Render autodeploy) cuando el usuario apruebe.
- Validacion visual en el portal (un vendedor con Orden completo, ej V6/V10).

## Sesion 2026-06-18 - Cobertura por vendedor + faltantes (drill-down)

### HECHO (validado en local, NO commiteado aun)
- `generar_datasets_acum.py`: nuevo `mod_cobertura_acum_detalle.csv` (faltantes por vendedor x segmento) desde el mismo merge de cobertura. Consistencia sin_cobertura == filas detalle OK.
- `server_orbit.py`: `/api/gerencia/cobertura_acum_faltantes?segmento=` y `/api/vendedor/<vid>/cobertura_acum`. V3 sin AUTOSERVICIO respetado.
- `portal.html`: drill-down por segmento en dashboard gerencia, cobertura por segmento en pantalla Vendedores 360, y tarjeta nueva en el perfil propio del vendedor.

### PENDIENTE
- Commit (pedir aprobacion). Incluir `mod_cobertura_acum_detalle.csv` en el commit para que Render lo tenga (el endpoint lo lee). Confirmar que el flujo de cierre/regeneracion lo deja siempre fresco (main() ya lo emite).
- Validacion visual del usuario en el portal (gerencia y un vendedor real).

## Sesion 2026-06-17 - Performance carga del portal (Render)

### HECHO (desplegado en Render)
- gunicorn con threads (gthread x8, 1 worker) -> concurrencia real (35s serie -> 10.9s paralelo).
- Cache por mtime: _ventas_parsed() (segmento vectorizado), read_csv() (copia al devolver), clientes.xlsx via _clientes_maestro en diagnostico/planes_as.
- Login muestra el portal con CORE liviano (diagnostico+dashboard+clientes) y carga el resto en 2do plano (loadRole + refreshAfterRole).
- Tiempo hasta ver el portal: ~20-35s -> ~2s. Validado en Render.

### PENDIENTE / SI QUIEREN MAS VELOCIDAD
- Piso ~2s por Render starter = 0.5 vCPU. Para bajar: upgrade de plan (mas CPU) o endpoint /bootstrap unico que devuelva el core en 1 request.
- Optimizar /api/alertas (~3s aun cacheado; corre en 2do plano). Revisar si hace apply fila-por-fila o relee historial.
- Si Render no toma el startCommand de render.yaml/Procfile (servicio no-blueprint), aplicar los flags --threads 8 --worker-class gthread en el dashboard de Render.

## Sesion 2026-06-17 - Sin cargos del mes (Planes AS) desde sincargos*.xlsx

### HECHO
- Motor (`generar_datasets_acum.py`): `_cargar_sincargos_mes()` + override del disponible de sin cargos desde `01_INPUTS/Planes AASS/sincargos*.xlsx`. Recalcula pendiente, agrega `sc_estado`/`sc_origen_disponible`.
- Portal (`portal.html`): pendiente rojo->amarillo en gerencia y vendedor; Estado "enviados"/"pendiente"/"—"; vendedor con chip de estado y etiqueta "disponible".
- Validado: reparto helper (30033=4/4/1), override+estado sobre CSV real, node --check JS OK.

### RESUELTO (esta sesion)
- Sin Reconocimiento: la base Plan AS se reconstruye desde `Planes AASS/sincargos<mes>.xlsx` + `escalas<mes>.xlsx` + ventas.csv. `mod_planes_as.csv` regenerado y validado.
- Sin cargos escala: disponible del Excel, enviado de ventas.csv, verde/amarillo + Estado.
- Plan frio AGREGADO: hoja "plan frio" -> 1 Six Pack Smirnoff ICE por cliente; entregado/pendiente por linea 100% desc Marca "Smirnoff Ice Flavours". Visible en gerencia y vendedor.
- Click en un sin cargo (escala o plan frio) -> tarjeta modal con las FECHAS de envio (mod_sincargos_envios.csv + endpoints adjuntan 'envios'; funcion verSincargo en portal). Validado en vivo.
- Validado end-to-end con server local 8502 (endpoints 200, datos correctos) y node --check del portal.

### A REVISAR / PENDIENTE (al retomar)
- **Validacion VISUAL en pantalla** pendiente de confirmacion del usuario (Ctrl+F5 en la pestaña Planes AS, gerencia y cada vendedor).
- Falta commit + push + deploy a Render.
- Cada mes el usuario carga `sincargos<mes>.xlsx` y `escalas<mes>.xlsx` en `01_INPUTS/Planes AASS/` (autodetecta por mtime). El motor ya NO depende de `PLANES_AS/Reconocimiento`.
- Si vuelve a aparecer el Reconocimiento, el motor lo prioriza (el fallback solo entra si falta).

## Sesion 2026-06-16 - Login dia/noche automatico

### HECHO
- Pantalla de ingreso cambia dia/noche automaticamente por hora argentina (Intl America/Argentina/Buenos_Aires).
- Boton manual sigue funcionando (override hasta recargar); refresco cada 60s.
- Validado con Node: 07h->dia, 18h->dia, 19h->noche, 00/06h->noche.

### A REVISAR / PENDIENTE
- Falta commit + push + deploy a Render.
- Si negocio quiere otros umbrales (ej. dia 06:00 o noche 20:00), ajustar autoLoginMode en portal.html.

## Sesion 2026-06-16 - Perf login (cache por mtime)

### HECHO
- Cacheados por mtime `_acciones_mes_payload`, `_acc_preparar_ventas` y `_cargar_maestro_04D` en `server_orbit.py`.
- Validado en local: `acciones_mes` cold 4.09s -> warm 0.001s, output identico; cache por vendedor no pisa la de gerencia.

### A REVISAR / PENDIENTE
- Falta commit + push + deploy a Render para que el usuario lo note (pendiente de aprobacion).
- Medir en Render el login warm completo; si sigue lento, evaluar cachear tambien `/api/diagnostico` (4.4s), `/api/gerencia/planes_as` (3.7s) y `/api/alertas` (3s) con el mismo patron.
- Opcional mayor riesgo: gunicorn `--threads` para paralelizar fetch del login (cuidar escritura SQLite de planificaciones).
- Nota: el primer login tras cada cierre diario paga el costo completo una vez (cache se invalida por mtime).

## Sesion 2026-06-16 - Buscador Cliente 360

### HECHO
- Boton Cliente agregado en gerencia y vendedor.
- Endpoints nuevos: `/api/clientes/buscar` y `/api/clientes/<id>/ficha`.
- Gerencia busca toda la cartera activa; vendedor queda restringido a sus clientes.
- Ficha cliente con datos maestro, marcas del mes, litros/dinero, historico mensual, color por tendencia de litros y posibilidad de venta contra promedio disponible.

### A REVISAR / PENDIENTE
- Validar visualmente en navegador que la tabla mensual y chips de marcas no desborden en mobile.
- Si negocio requiere promedio exacto de 12 meses, cargar una fuente historica con litros (`PesoKg`) para los 12 meses completos; hoy la ficha informa cuantos meses reales hay disponibles.

## Sesion 2026-06-16 - Fix Incentivo Club FARO mayo-junio

### HECHO
- FARO filtra ventas netas de `ventas_acumulada.csv` solo a mayo y junio, excluyendo V2/V5.
- Smirnoff mide familia 700cc en Autoservicio; Antares mide Autoservicio por SKU cubierto con XPA y Lager 330/660 doble; Alaris/Finca Las Moras mide Almacen/Despensa/Kiosco.
- Gerencia y vendedor separan coberturas logradas de clientes cubiertos. Antares muestra articulo/peso para explicar diferencias entre avance y cantidad de clientes.
- Control puntual: V4 Antares queda en 6/8 coberturas y 2 clientes unicos, no 13 clientes.

### A REVISAR / PENDIENTE
- Validar visualmente en navegador la tarjeta desplegable FARO en escritorio y movil.
- Cuando ingresen ventas Antares Lager 330/660, confirmar que los codigos nuevos esten en `ventas_acumulada.csv` y sigan matcheando la regla doble.

## Sesión 2026-06-16 — Acciones comerciales desde ventas.csv + drill-down

### HECHO ✅
- ✅ Tarjetas de Acciones Comerciales corregidas para contar clientes desde **`ventas.csv` con `ImporteNetoItem > 0`**, sin V2/V5/V20. `inversion_pesos` queda separada como descuento real (`valorDescuento × CantBase`).
- ✅ ACJ26-021/022/023 usan las marcas de **`objetivo 11T.xlsx`**; ACJ26-008/024 usan códigos de **`INNOVACIONES/Innovaciones.xlsx`**; ACJ26-010/011/012/013 filtran contra **`mod_planes_as.csv`**.
- ✅ En gerencia y perfil vendedor, clic en **clientes** o **nuevos** abre el detalle de clientes que compraron la acción: dirección, vendedor, venta neta, descuento, litros y última compra.
- ✅ Validado local: `py_compile`, `node --check` de scripts extraídos y endpoints `/api/gerencia/acciones_mes` + `/api/vendedor/V8/acciones_mes`.

### A REVISAR / PENDIENTE
- Validar visualmente en navegador/Render que la tarjeta desplegable no desborde en móvil.
- Las acciones Petit Mayoristas (ACJ26-014/015/016) y Plan Cobertura OP (ACJ26-018/019/020) siguen dependiendo de datos operativos externos para validar condición completa; el portal muestra ventas que matchean catálogo, no liquidación final.
- ACJ26-026 queda en cero con canal VTK/TDB porque no hay ventas Dadá Tinto de Verano en ese canal; si negocio quiere contar Tradicional/Autoservicio, hay que cambiar el catálogo.

## Sesión 2026-06-10 — Nueva regla ACJ26-017

### HECHO ✅
- ✅ ACJ26-017 reescrita: vendedores **V3/V4/V6/V8/V10**, **solo almacén/despensa/kiosco** (canal `ALMACEN_DESPENSA_KIOSCO`), **20%**, mismas 4 marcas, **tope 2 cajas/mes combinable entre marcas**. Catálogo (CSV+JSON) + **motor**: nuevo `_acc_subseg_filtro` sub-filtra por `Subramo` cuando la acción nombra subtipos sin el genérico "tradicional" (opt-in; otras acciones intactas). Aplicado en `_acciones_mes_payload` y `_alertas_descuento_mes`. Validado con endpoint real. Ver [[business_rule_acciones_mensuales]].

- ✅ **Control de tope de cajas:** nuevo `_alertas_tope_cajas_mes` (server_orbit.py) — alerta cuando un cliente supera el tope mensual de cajas de una acción (catálogo-driven: `maximo`+`unidad_maximo` con caja/mes). `/api/alertas` = descuento + tope. Caja = botellas/6 (CantBase en botellas). 4 alertas para ACJ26-017 en junio. Aparece en alertas de gerencia y de vendedor sin tocar frontend.

### A REVISAR / PENDIENTE
- **Validar en Render** el feed combinado de `/api/alertas` (tipo "tope" presente, serialización OK).

## Sesión 2026-06-09 — Objetivos Sellout litros desde OBJSELLOUT.xlsx

### HECHO ✅
- ✅ Tarjeta gerencial *Sellout acumulado en litros · por categoría* (`/api/gerencia/sellout_litros`): objetivos por categoría ahora salen de `01_INPUTS/OBJSELLOUT.xlsx` (nuevo `_cargar_objetivos_sellout`), ya no hardcode. Subcategorías sin objetivo (None). `_renderSoDash` tolera nulls. Validado en local (test_client 200). Ver [[business_rule_sellout_maestro]].

### A REVISAR / PENDIENTE
- **Pushear a Render** este cambio (validar que `OBJSELLOUT.xlsx` esté disponible en el deploy o que el endpoint tolere su ausencia → hoy devuelve objetivo None, no rompe).
- Si en el futuro se quieren objetivos por subcategoría, agregar columnas a `OBJSELLOUT.xlsx` y extender el loader.

## Sesión 2026-06-08 — Fix tarjeta 11T del cierre

### HECHO ✅
- ✅ 11T del cierre: fuente cambiada a `ventas_acumulada_<MMAAAA>.csv` (bimestral abril+mayo) con criterio canónico (neto>0, excl V2/V5/V20, sin filtro Empresa) + fallback a `ventas_mes`. Mayo: **4424 CCC / 124.5%**, 11/11 marcas ≥ objetivo. Validado en local; **pendiente pushear a Render**.
- ✅ Decisión: el cierre queda con NUESTRO criterio, aunque difiera del reporte oficial Peñaflor (~4007). No se reconcilia sin detalle cliente-nivel de ellos. Auditoría en `99_AUDITORIA_ORBIT/auditoria_11t_clientes_052026.csv`. Ver [[business_rule_11t_bimestral]].

- ✅ Acciones Comerciales del cierre: nuevo `_cierre_acciones_versionado` recalcula desde `ventas_mes_<MMAAAA>.csv` con inversión real (`valorDescuento×CantBase`, no IVA). Mayo: 11 acciones, inversión 14.856.477, 936 clientes. (FASE 2b parcial.) Ver [[business_rule_acciones_mensuales]].

- ✅ Incentivo Club FARO: botón en gerencia (`gIncentivoFaro`) + tab vendedor (`vFaro`); endpoints `/api/gerencia/incentivo_faro` y `/api/vendedor/<vid>/incentivo_faro`. Objetivos de `incentivo_club_faro .xlsx`, logrado+no-compradores de `ventas_acumulada.csv` (mayo-junio). Ver [[business_rule_incentivo_faro]].

### A REVISAR (FARO)
- Período: hoy usa `ventas_acumulada.csv` (cubre 04-may→06-jun). Cuando cierre junio, confirmar que la fuente siga siendo el bimestre completo mayo+junio.
- V7 da logrado muy bajo (pocas ventas suyas en `ventas_acumulada.csv`) — revisar si faltan datos de V7 en esa fuente.
- Antares "Lager botella": el doble se aplica a artículos con XPA o LAGER (en datos solo hay lata). Confirmar si aparece un SKU botella.

### A REVISAR (consistencia P&P Logística en el cierre)
- `_cierre_ccc_por_vend_segmento` (CCC por segmento del cierre, tarjetas "Resumen compañía" / "Cierre por vendedor") **sí** filtra `Empresa=='Empresa'`. Definir con el usuario si CCC-por-segmento del cierre debe incluir P&P Logística o no (hoy 11T sí, segmento no). El `gerencia_cierre_mes` live también filtra Empresa en CCC segmento.

### A CORREGIR (mismo bug de IVA en inversión, fuera del cierre histórico)
- `generar_datasets_acum.py::_preparar_ventas_acciones` usa `inversion = ImporteItem−ImporteNetoItem` (IVA) → `mod_acciones_ranking.csv` y el endpoint `gerencia_cierre_mes` muestran IVA, no descuento real. Corregir a `valorDescuento×CantBase` y regenerar datasets.
- FASE 2b acciones: versionar el catálogo de reglas por cierre (hoy `_ACC_REGLAS_POR_MMAAAA` mapea 052026→reglas_acciones_mayo en 09_CONFIG; generalizar para junio+).

## Sesión 2026-06-06 — Cierre versionado por carpeta (cierres mes/)

### HECHO ✅
- ✅ FASE 1: `cierres_historicos` recalcula objetivos/avance + CCC + 11T desde el trío del mes. Mayo validado en Render.
- ✅ FASE 2a: Sell-Out + Innovaciones + Ranking desde `ventas_mes_<MMAAAA>.csv` (+ maestro 04D CSV, Innovaciones.xlsx). Validado en Render. (Hubo incidente 500 por numpy + Excel 19MB; corregido con casteo nativo + maestro CSV.)
- ✅ Automatización: `CIERRE_MES_ORBIT.bat` + `tools/cerrar_mes.py` versionan los archivos del mes (backup+log+protección, publican a Render). Validado en mayo (no-op).

### PENDIENTE (FASE 2b) — construir/validar con catálogos reales de JUNIO al cerrarse
1. Server: **Acciones** desde `acciones_<MMAAAA>.csv` + `ventas_mes_<MMAAAA>.csv` (catalog-match), con fallback al artefacto viejo si no hay catálogo del mes.
2. Server: **Planes AS** desde `reconocimiento_<MMAAAA>.xlsx` + `escala_<MMAAAA>.xlsx` + `ventas_mes_<MMAAAA>.csv`, con fallback.
3. **Descubrir cierres desde la carpeta** `cierres mes/` (hoy se listan desde `07_CIERRES_MENSUALES/index`). Meta: agregar el trío `_062026` y que aparezca junio solo.
4. Innovaciones: listar las 17 (no solo las 13 con venta) marcando 0 las sin venta (regla 3.9).
5. Una vez migrado todo, deprecar los artefactos `cierre_*.json`.

### LECCIÓN
- Validar **serialización estricta (sin numpy)** y **performance tipo-Render** antes de pushear, no solo que el endpoint responda en local. El Excel 04D (19MB) tarda ~40s; usar siempre el CSV liviano.

---

## Sesión 2026-06-05 (c) — Facturado Plan AS desde ventas.csv

### HECHO EN ESTA SESIÓN ✅
- ✅ `total_facturado` del Plan AS (gerencia + perfil vendedor) ahora sale de **ventas.csv** (suma neta válida por cliente), no del Excel de Reconocimiento. Regla 3.10 cumplida.
- ✅ Escala alcanzada se recalcula con la venta real (`escala_junio.xlsx`); helper `_calc_escala_actual()`.
- ✅ `mod_planes_as.csv` regenerado (con backup en `99_BACKUPS_ORBIT/`). Validado en endpoints en vivo.

### A OBSERVAR / PENDIENTE
1. **Escalas reflejan mes vivo:** con ventas.csv de 01–04 jun las escalas son bajas y suben al cargar más días. Confirmar que es el comportamiento deseado (avance del mes) y no "facturado del período de reconocimiento" (que sería otra fuente/período).
2. **Dato ERP a revisar:** clientes AS 8010/8139/8230/1093 tienen exactamente $785.458 neto en 1 fila en ventas.csv (idéntico) — verificar en el ERP.
3. **Pendiente confirmar en Render tras push.**

---

## Sesión 2026-06-05 (b) — Objetivos del perfil de vendedor desde resultado.xlsx

### HECHO EN ESTA SESIÓN ✅
- ✅ Auditados los OBJ de dashboard (Acumulado Compañía + Ranking): **ya salían de `resultado.xlsx`**. OBJ compañía = **$330.000.000** (suma de los 7 activos). Correcto.
- ✅ Bug detectado y corregido: `/api/vendedor/<vid>` tomaba obj/acum/tendencia de `mod_volumen_vendedor.csv` y recalculaba la tendencia distinto → divergía del dashboard (V3 16.49% vs 20.62%; V9 87.9% vs 109.88%). Ahora usa `resultado.xlsx` (Avance) como fuente primaria; `tendencia_pct = Avance`.
- ✅ `/api/dashboard`: tendencia fijada al `Avance` de resultado.xlsx (robusto ante días corridos).
- ✅ Validado en instancia temp (8599): perfil coincide 1:1 con resultado.xlsx en los 7 vendedores.

### A OBSERVAR / PENDIENTE
1. **Reiniciar el server de producción (8502)** para que tome el cambio — había **dos** instancias `python server_orbit.py` corriendo a la vez sobre el 8502 (PIDs 15004 y 9508). Conviene dejar **una sola**.
2. La pantalla de Plan vs Real y el "% del objetivo" usan `tendencia_pct` (= Avance = Tendencia/Objetivo). No se expone un avance "real" Acumulado/Objetivo aparte; si se quisiera, es otra tarea.
3. **Pendiente confirmar en Render tras push.**

---

## Sesión 2026-06-05 — Real del día = acumulado hoy − ayer (resultado.xlsx)

### HECHO EN ESTA SESIÓN ✅
- ✅ Plan vs Real: el "real del día" por vendedor ahora sale de **`Acumulado(hoy) − Acumulado(ayer)`** de `resultado.xlsx`, no del conteo de ventas.csv por FechaComprobante. V10 pasó de "sin ventas" a **$357.851** (04/06).
- ✅ Snapshot diario `02_HISTORY/acumulado_resultado_historico.csv` (bootstrap 06-02/03/04 desde git; se actualiza en cada cierre vía `snapshot_acumulado_resultado`). Bat lo commitea.
- ✅ `_real_dia_resultado()` en server_orbit.py (mismo mes, negativos→0). Portal ya lee `real_ayer`/`tiene_real` (sin cambios de frontend).
- ✅ Validado local. **Pendiente confirmar en Render tras push.**

### A OBSERVAR
1. El histórico arranca el **06-02** (el 06-01 era cierre de mayo, se excluyó). El primer día de cada mes no tiene "ayer" del mismo mes → ese día el real puede no calcularse por diferencia (cae a ventas.csv o queda pendiente).
2. Las columnas CCC de Plan vs Real siguen viniendo de ventas.csv (el usuario pidió cambiar la VENTA $). Si se quieren los CCC también por otra fuente, es aparte.

---

## Sesión 2026-06-04 — Ruta del vendedor (clientes.xlsx + ventas.csv, 11 titulares)

### HECHO EN ESTA SESIÓN ✅
- ✅ Nuevo endpoint `/api/vendedor/<vid>/ruta`: cartera del día desde `clientes.xlsx` + compra/sin compra y **11 Titulares faltantes** desde `ventas.csv` (mes vivo). Solo los 11 titulares.
- ✅ `vRuta` usa `D.ruta`; muestra `once_t_comprados/11` + chips de marcas titulares faltantes (reemplaza chips de innovaciones).
- ✅ Corrige `faltan_11t = 11` hardcodeado en `/api/clientes` (ese endpoint no se tocó; la ruta ahora usa el endpoint nuevo, aislado de gerencia).
- ✅ Validado local + preview visual. **Pendiente confirmar en Render.**

### A OBSERVAR
1. "Comprado un titular" = cualquier compra de esa marca este mes (sin umbral de botellas). Si se quiere aplicar el umbral de cobertura (Trad 3 / AS 6), es un ajuste.
2. `/api/clientes` (gerencia Clientes Críticos) sigue con `faltan_11t=11` hardcodeado, pero esa pantalla no usa ese campo. Revisar si en el futuro lo necesita.

---

## Sesión 2026-06-04 — Oportunidad del día de Innovaciones (vendedor)

### HECHO EN ESTA SESIÓN ✅
- ✅ Nueva tarjeta "Oportunidad del día · Innovaciones" en el inicio del vendedor: 3 clientes de la zona de hoy que compraron mayo y junio pero nunca innovaciones, con texto alentador + 3 innovaciones al azar.
- ✅ Endpoint `/api/vendedor/<vid>/oportunidades_innovacion` (fuente `ventas_acumulada.csv`). Top 3 por volumen $. Filtra por día (`?dia=`, default hoy AR).
- ✅ Tarjeta con gradiente magenta, validada visualmente. **Pendiente confirmar en Render.**

### A OBSERVAR
1. Las 3 innovaciones son random por carga (cambian al refrescar). Si se quiere fijarlas por día, sembrar el random con fecha+vendedor.
2. Si la zona del día no tiene candidatos, cae al bloque viejo "Recuperar cliente".

---

## Sesión 2026-06-04 — Dormidos: criterio +60 días + riesgo $/litros

### HECHO EN ESTA SESIÓN ✅
- ✅ Criterio dormido = **sin compra hace +60 días** (antes "no compró este período"). Última compra = max(historial + ventas.csv).
- ✅ Riesgo en **$ y litros** (litros parseados del nombre del artículo). 3 tarjetas KPI: dormidos · riesgo $ · riesgo litros.
- ✅ Dormidos por vendedor: top **3** por mayor volumen ($), con $ y litros. Detalle clientes sin cambios de estructura.
- ✅ Validado local: 7 dormidos (63-65 días), $300.754 / 50.2 L. **Pendiente confirmar en Render.**

### A OBSERVAR
1. **Retención del historial ampliada a 90 días** (ventana móvil en `actualizar_historial_ventas`, LEGACY/orbit_matinal_v42.py). Hoy el historial tiene 69 días (no poda nada); a medida que acumule, la detección de dormidos llega a la banda 60-90 días. Aplica desde el próximo cierre.
2. Litros se derivan del nombre del artículo (`cant_base` × ml/unidad). Default 0.75 L si no parsea. `cant_base` confirmado = unidades/botellas (validado con White Horse 12X750 = 720 botellas).
3. Top 3 se ordena por **$**; si se prefiere por litros, cambiar el sort.

---

## Sesión 2026-06-04 — 11T: mod_11t_acum desde ventas_acumulada

### HECHO EN ESTA SESIÓN ✅
- ✅ `mod_11t_acum.csv` ahora se genera desde **`ventas_acumulada.csv`** (regla 11T), no de ventas.csv. tiene_flag 52 → **803**, clientes con marca 34 → **516**.
- ✅ Revisado flag de `mod_11_titulares.csv` (en 0): en gerencia es solo fallback de `once_titulares` (no se activa, la primaria usa ventas_acumulada) y `11t_empresa`/`11t_vendedor` no los consume el portal. No requiere fix.
- ✅ Tarjeta 11T vendedor (clientes día|total) ahora con datos acumulados correctos (V8: 56/157). Muestra 18 marcas = titulares por segmento (correcto; V3 muestra 10, sin Autoservicio).
- ✅ Validado local. **Pendiente confirmar en Render.**

---

## Sesión 2026-06-04 — Tarjeta 11T vendedor: clientes vendidos (día | total)

### HECHO EN ESTA SESIÓN ✅
- ✅ Tarjeta 11 Titulares en KPIs del vendedor: **reemplazado % por cantidad de clientes vendidos por marca** → `clientes zona del día | total de zonas`. Sin porcentaje.
- ✅ Fuente cambiada a `mod_11t_acum.csv` (la buena; `mod_11_titulares.csv` tiene `tiene_flag` en 0 → el % anterior daba 0 siempre).
- ✅ Día de la zona vía `_clientes_por_dia` (DiasVisita). Endpoint `/api/vendedor/<vid>` acepta `?dia=`; sin él, día AR de hoy.
- ✅ Validado local (V8 MA: 23/31). **Pendiente confirmar en Render.**

### A OBSERVAR
1. `mod_11_titulares.csv` tiene `tiene_flag`/botellas en 0 (lo genera el motor legacy). Otras vistas que dependan de ese flag pueden estar en 0; revisar si se usa en gerencia.
2. "Día de la zona" = día AR de hoy. Si se prefiere el próximo día operativo (matinal), se ajusta.

---

## Sesión 2026-06-04 — Innovaciones del mes vivo (ventas.csv)

### HECHO EN ESTA SESIÓN ✅
- ✅ **Cobertura de innovaciones ahora sale de `ventas.csv` (mes vivo)**, no de `ventas_acumulada.csv` (que arrastraba mayo). Total clientes "compraron": 256 → **38** (junio real). Afecta pantalla Innovaciones gerencia + tarjeta Innovaciones KPIs vendedor.
- ✅ Overlay `?dia` de `innovaciones_total` también pasó a `ventas.csv`.
- ✅ Validado local (gerencia total=38; V8=19). **Pendiente confirmar en Render.**

### A OBSERVAR
1. `mod_innovaciones_plan_as.csv` (innovaciones dentro de la vista Plan AS) sigue con acumulada. Si se quiere mes vivo, cambiar `generar_innovaciones_plan_as(ventas_acum_full,...)` → `ventas`.
2. La cartera de innovaciones es grande (1609 trad / 192 AS) y la cobertura de junio es baja (esperable a principio de mes; sube con el avance del mes).

---

## Sesión 2026-06-04 — Auditoría Planes AS (escala + vendedor)

### HECHO EN ESTA SESIÓN ✅
- ✅ **Escala del Plan AS ahora sale de `escala_junio.xlsx`** (autodetecta `escala_*.xlsx` del mes; fallback hoja ESCALA). Antes usaba umbrales viejos embebidos en Reconocimiento.
- ✅ **Vendedor del cliente AS desde maestro `clientes.xlsx`** (fallback ventas.csv). Antes 11/31 clientes quedaban sin vendedor → ahora 0.
- ✅ Confirmado: sin cargo enviado ← `ventas.csv`; clientes/facturación/ganado ← `Reconocimiento Plan As.xlsx`.
- ✅ Flujo de actualización OK: pegar archivos + `CIERRE_DIA_ORBIT.bat` → REGENERAR recalcula `mod_planes_as.csv` → BAT lo commitea → Render.
- ✅ Validado local. **Pendiente confirmar en Render tras push.**

### A OBSERVAR
1. **Escala por LC simplificada:** `_calc_escala` toma el máximo `escala_num` global cuyo umbral (Gold/Silver/Inicial según plan) ≤ `total_facturado`, sin separar por Línea Comercial. Si se necesita escala exacta por LC, es un paso extra (la hoja tiene LC/SEGMENTO).
2. **`total_facturado`** sale del Reconocimiento (BBDD), no se recalcula de ventas.csv. Es la facturación oficial del plan; confirmar si debe seguir así.
3. Nombres con mojibake (ej. "YBAÑEZ"→"YBAÃ‘EZ") vienen del Reconocimiento; si molesta, usar el nombre del maestro clientes.xlsx.
4. Los `.xlsx` crudos de PLANES_AS están sin trackear en git (no hace falta para Render; opcional commitearlos como backup).

---

## Sesión 2026-06-04 — Alertas desde ventas.csv + fecha de pedido

### HECHO EN ESTA SESIÓN ✅
- ✅ **Alertas ahora salen de `ventas.csv` (mes vivo)**, no de `ventas_acumulada.csv` (que trae mayo+junio y generaba alertas falsas por acciones de mayo). Alertas 34 → **22**.
- ✅ `_acc_preparar_ventas(nombre)` parametrizada. Acciones: mes vivo de `ventas.csv`; `ventas_acumulada.csv` solo para "clientes nuevos" del mes anterior.
- ✅ Cada alerta muestra 📅 **fecha de pedido** (FechaComprobante) + `fecha_carga` en el dato. Visible en pantalla gerencial y bloque del vendedor.
- ✅ Validado local. **Pendiente confirmar en Render tras push.**

### A OBSERVAR
1. `ventas.csv` (321 filas jun) vs porción junio de `ventas_acumulada.csv` (380 filas): hay diferencia de snapshot. Se priorizó `ventas.csv` por ser el mes vivo/fresco (regla del proyecto).
2. La fecha mostrada es **FechaComprobante**. Si se prefiere FechaCarga (literal "creación de pedido"), ya está en el dato (`fecha_carga`); cambiar el display es 1 línea.

---

## Sesión 2026-06-04 — Matcheo por código + SMF BC / Smirnoff Ice 35103

### HECHO EN ESTA SESIÓN ✅
- ✅ `_acc_product_pred` matchea por **código de SKU** cuando `productos_marcas` trae un número (acción dirigida a un código, no a toda la línea).
- ✅ Catálogo junio: **ACJ26-027** = Smirnoff Ice Clásica **35103 al 25%**, cualquier canal, V3/V4/V6/V8, sin tope → deja de alertar para esos vendedores y aparece en Acciones.
- ✅ **ACJ26-006 SMF BC**: token `SMIR BC` → `Smirnoff Bitter Citric; Smirnoff BC; SMF BC` → ahora aplica el 15% real (segmento ya incluía Autoservicio). Venta al 25% queda como exceso (máx 15%).
- ✅ Validado en local: 27 reglas, 34 alertas. **Pendiente confirmar en Render tras push.**

### A OBSERVAR
1. Para apuntar una acción a un SKU puntual, cargar el **código numérico** en `productos_marcas` y dejar `lineas_comerciales` vacío (si no, arrastra toda la línea).
2. Algunos SKU de SMF BC (ej. 35108) **no están en el maestro 04D** → no tienen línea; por eso el match usa también el nombre de artículo. Si se quiere prolijidad, sumar esos códigos al maestro 04D.

---

## Sesión 2026-06-04 — Fix descuento real = valorDescuento (commit 9fcf258)

### HECHO EN ESTA SESIÓN ✅
- ✅ Revisado volumen/criterio de alertas con datos reales. Detectado que `ImporteItem−ImporteNetoItem` = IVA (17.4%), no descuento.
- ✅ Descuento real ahora = `valorDescuento × CantBase`; % = `desc/(neto+desc)`. Afecta alertas y la inversión de acciones.
- ✅ Validado en Render: alertas 112→**44**; Gordon's (acción 5%) alerta a 6% y 10%; inversión acciones $3.1M→**$1.215.257**.

### A OBSERVAR
1. Alertas con exceso de 1pp (ej. 6% vs 5%) se cuentan como alerta. Si querés tolerancia mayor (ej. solo exceso ≥2pp), se ajusta el umbral (hoy >0.5).
2. Escala por cantidad sigue sin aplicarse (tope = tramo más alto).

---

## Sesión 2026-06-04 — Alertas de descuento desde catálogo del mes (commit 9ebc42d)

### HECHO EN ESTA SESIÓN ✅
- ✅ `/api/alertas` (pantalla Alertas gerencia + bloque alertas vendedor) ahora se calcula en vivo desde el catálogo del mes (autodetectado), no desde `reglas_acciones_mayo` ni `mod_alertas_descuentos.csv`. Se actualiza solo cada mes.
- ✅ Criterio: alerta si descuento aplicado > tramo más alto de la acción aplicable (vendedor+segmento+marca); sin acción → máximo 0 → alerta.
- ✅ Normalización de marca (`_acc_norm`) corrige falsos positivos por acentos/apóstrofes (Gordon's). Validado en Render (112 alertas; Gordon's→ACJ26-007).

### PENDIENTES / A OBSERVAR
1. **Volumen de alertas**: 112 total (V8=81) por criterio estricto ("sin acción → alerta"). Si en uso real resulta ruidoso, evaluar umbral o excluir marcas sin acción.
2. **Escala por cantidad**: el tope de alerta usa el tramo más alto (no el tramo exacto por cajas). Si se quiere precisión por cantidad, es un paso extra.
3. `mod_alertas_descuentos.csv` (motor legacy, mayo) quedó sin consumidor en el portal; se puede deprecar.

---

## Sesión 2026-06-04 — Acciones Comerciales del Mes (catálogo × ventas) (commit 69bb95c)

### HECHO EN ESTA SESIÓN ✅
- ✅ Motor "acciones del mes": lee el catálogo mensual oficial `01_INPUTS/ACCIONES COMERCIALES/<YYYY-MM>/acciones_comerciales_<mes>_<año>_penaflor.csv` (autodetecta el mes) y cruza con ventas.
- ✅ Calcula por acción: inversión real (ERP), litros, clientes alcanzados, clientes nuevos (vs mes anterior). Display: segmento, tipo (descuento/sin cargo), escala, marcas, topes.
- ✅ Endpoints `/api/gerencia/acciones_mes` y `/api/vendedor/<vid>/acciones_mes` (filtrado por vendedores_aplica + V3-sin-AS).
- ✅ Portal: gerencia + vendedor (tab Alertas) muestran tarjeta por acción "Acciones Comerciales de Junio". Validado en Render (V8 sin ACJ26-017, V3 con).

### PRÓXIMOS PASOS / PENDIENTES
1. **Reglas finas no computadas como filtro** (sí mostradas como condición): escala por tramos, surtido, 11T-quiebre mín/máx. Evaluar si se necesita aplicarlas al cálculo de inversión/clientes.
2. **Julio**: cuando llegue, dejar el CSV en `01_INPUTS/ACCIONES COMERCIALES/2026-07/` (mismo patrón) — el motor lo toma solo. Recordar commit+push (CIERRE_DIA no incluye esa carpeta; ver punto 3).
3. **Deploy de la carpeta de acciones**: `01_INPUTS/ACCIONES COMERCIALES/<mes>/` no está en el `git add` de `CIERRE_DIA_ORBIT.bat`; al cargar un mes nuevo hay que commitearlo manualmente o agregarlo al bat.

---

## Sesión 2026-06-04 — Auditoría pantalla Vendedores + fix KPI 11T (commit a2b86ca)

### HECHO EN ESTA SESIÓN ✅
- ✅ Revisada la pantalla Vendedores tarjeta por tarjeta. OK: chip avance (tendencia/proyección), Acum/Obj, CCC Mes, Plan.día/SC Día (contexto matinal).
- ✅ Fix "11T ✓" (daba 0 en todos): repuntado a `mod_11t_acum.csv` (cobertura real por vendedor). Validado en Render: V8=31, V10=9, V9=6, V4=3, V6=3, V3/V7=0.

### PENDIENTE — CAUSA RAÍZ (pipeline/motor, NO dashboard) 🔲
1. **`mod_11_titulares.csv` viene con `tiene_flag`/`botellas_mes`/`importe_mes` en 0** (3740 filas). El motor legacy que genera ese dataset (vía `REGENERAR_DATOS_ORBIT.bat`) no está cargando las ventas del mes. El dashboard ya no depende de él para el 11T, pero conviene arreglar el motor para que `mod_11_titulares.csv` (objetivo del día) quede consistente. Toca `LEGACY/` → tarea separada, con aprobación.

### PRÓXIMOS PASOS
1. Seguir revisando otras pantallas tarjeta por tarjeta cuando el usuario indique.
2. (Pendiente previo) motor de aplicación de acciones comerciales (loader junio ya deja catálogo + colisiones).

---

## Sesión 2026-06-04 — Push diario robusto en CIERRE_DIA_ORBIT.bat (commit c8b6156)

### HECHO EN ESTA SESIÓN ✅
- ✅ `CIERRE_DIA_ORBIT.bat` Paso 3/3: agregado `git pull --rebase origin master` (tras commit, antes del push) → evita el rechazo non-fast-forward que dejaba el push sin subir.
- ✅ Errores visibles: si falla rebase (`git rebase --abort` + aviso) o push (mensaje claro), el operador se entera; ya no falla en silencio.
- ✅ Chequeos con `if errorlevel 1` (más confiable que `%ERRORLEVEL%` anidado).

### PROCEDIMIENTO DIARIO (confirmado)
- **No hay archivo aparte de push.** El push ya es el Paso 3/3 de `CIERRE_DIA_ORBIT.bat`.
- Rutina: pegar `ventas.csv` nuevo en `01_INPUTS/` → ejecutar **`CIERRE_DIA_ORBIT.bat` completo** (un doble-clic). Hace: validar → regenerar datasets → sincronizar planes → commit+pull --rebase+push → abrir portal.
- ⚠️ NO usar solo `REGENERAR_DATOS_ORBIT.bat` (regenera pero NO publica → Render queda con datos viejos).

### PRÓXIMOS PASOS (opcionales)
1. Programar `CIERRE_DIA_ORBIT.bat` con el Programador de tareas de Windows si se quiere 100% automático a una hora fija (hoy es manual de un clic).
2. Motor de aplicación de acciones comerciales (loader junio ya deja catálogo + colisiones).

---

## Sesión 2026-06-04 — Fix Sell Out + dashboard validado integral (commits 4864d22, ffc0c1e)

### HECHO EN ESTA SESIÓN ✅
- ✅ Fix Sell Out en cero (Render): `_preparar_df_ventas` ahora lee `ventas.csv` con `dtype=str` (la inferencia de coma decimal fallaba en Render). VINOS DEL AÑO 903.8L/54, etc.
- ✅ Blindaje: `dtype=str` también en `_cargar_ventas_mes_actual` y `_cargar_ventas_dia`. Lectores de `ventas_acumulada.csv` (11T) sin tocar (ya robustos).
- ✅ **Dashboard validado integral en Render** (15 endpoints PASS): cada tarjeta lee su archivo correcto y devuelve datos no-cero coherentes.
- ✅ Fix previo de fecha: refresh de datos al 2026-06-03 desplegado → Matinal JU 2026-06-04.

### ⚠️ PROCEDIMIENTO DIARIO (fijo — no es bug, es operación)
Render lee archivos **committeados**, no el working tree. Para que el refresh diario llegue a las tarjetas:
1. Actualizar `01_INPUTS/` (ventas.csv, ventas_acumulada.csv, resultado.xlsx) + correr pipeline (regenera `04_DATASETS_ORBIT/` + `02_HISTORY/`).
2. **`git add` inputs+datasets → `git commit` → `git push`** → Render auto-deploya y las tarjetas se actualizan solas (~1-3 min).
- Si el dashboard muestra el día anterior, casi siempre es **falta de push**, no un bug de código.

### ESTADO DEL DASHBOARD
- **Validado y fijo.** No requiere más cambios de código para el flujo diario. Cada tarjeta ↔ fuente:
  - `ventas.csv` → diagnóstico (fecha), KPIs por vendedor, Sell Out.
  - `ventas_acumulada.csv` → 11 Titulares (empresa/zona).
  - `resultado.xlsx` → objetivos/avance.
  - `04_DATASETS_ORBIT/*` → CCC, innovaciones, cobertura, 11t_acum, planes AS, acciones, alertas, clientes del día.

### PRÓXIMOS PASOS (opcionales, requieren aprobación)
1. **Automatizar el push diario** — un `.bat`/script que tras el pipeline haga add+commit+push de inputs+datasets, para evitar el olvido del deploy.
2. Motor de aplicación de acciones comerciales (loader junio ya deja catálogo + colisiones).

---

## Sesión 2026-06-04 — Loader de acciones comerciales mensual (commit c2c6b55)

### HECHO EN ESTA SESIÓN ✅
- ✅ `tools/loader_acciones_comerciales.py` — loader idempotente, versionado por mes, sin libs externas. No toca cierre, `resultado.xlsx`, históricos, datasets ni `server_orbit.py`.
- ✅ Capa semántica marca→categoría desde `producto activos.xlsx` (mapea Alma Mora/Dada vino/Alaris/Finca Las Moras → VDA; desambigua Dada vino de Sidra/Champaña).
- ✅ Diagnóstico Junio 2026: 26 reglas, todas `aplica_cierre_mes=NO`, sin V2/V5/V20. ACJ26-017 correctamente acotada (V3/V4/V6 + Tradicional + 30% + marcas permitidas).
- ✅ Reporte de colisiones: 40 (20 directas + 20 semánticas), `PENDIENTE_VALIDACION`. ACJ26-017 solapa solo con ACJ26-002 (VDA Tradicional) vía capa semántica.
- ✅ Commiteado y pusheado (`c2c6b55`): loader + input junio + salidas (sin `_backups`).
- ✅ Validado en Render que el panel "Cierre de Mes" sigue OK tras deploy `0b2152c` (acumulado $323.9M / 99.11%, todas las secciones, sin CantBase/botellas, sin errores JS/red).

### PRÓXIMOS PASOS (requieren aprobación)
1. **Motor de aplicación de acciones** — el loader hoy solo produce catálogo + colisiones; falta el motor que aplique descuentos/escala y resuelva las 40 colisiones (no acumular). Definir alcance.
2. **Mapeo línea↔marca para Spirits/RTD** — validar manualmente las 20 colisiones semánticas (varias por VDA/SIDRA/RTD en Autoservicio) antes de liquidar.
3. **Integrar loader al pipeline mensual** — para que cada mes nuevo de `01_INPUTS/ACCIONES COMERCIALES/<mes>/` se procese sin paso manual.

---

## Sesión 2026-06-03 — Acumulado distribuidora/vendedor desde resultado_mes.xlsx

### HECHO EN ESTA SESIÓN ✅
- ✅ Tarjeta "Resumen compañía" y "Cierre por vendedor" ahora usan el acumulado oficial del mes cerrado desde `resultado_mes.xlsx`: compañía $323.898.602,72 / 99.11% (antes $285.579.795 / 87.39% de `ventas_mes.csv`).
- ✅ `server_orbit.py` `/api/gerencia/cierre_mes`: fuente primaria `resultado_mes.xlsx`, fallback `resultado.xlsx`.
- ✅ Artefacto congelado `cierre_objetivos_avance.json` reescrito (CCC preservado); backup en `99_BACKUPS_ORBIT/`.

### PRÓXIMOS PASOS (requieren aprobación)
1. **Diferencia entre tarjetas de compañía** — "Resumen empresa del cierre" = importe neto facturado $285,6M (`ventas_mes.csv`) vs "Resumen compañía" = acumulado oficial $323,9M (`resultado_mes.xlsx`). Gap ≈ $38,3M. Decidir si la primera también se reconcilia o se aclara la etiqueta para que no confunda.
2. **Generador mensual** — `tools/generar_cierre_mensual.py` no incorpora `resultado_mes.xlsx`; para junio en adelante, definir cómo se congela el acumulado oficial por mes (hoy fue parche manual del artefacto).
3. **Deploy Render** — `resultado_mes.xlsx` vive en `01_INPUTS` (no commiteado). El portal lee el artefacto congelado, así que no depende de él en runtime; verificar igualmente tras deploy.

---

## Sesión 2026-06-03 — Panel histórico completo + acumulado unificado (commits f8af3c9, 3b4dd72)

### HECHO EN ESTA SESIÓN ✅
- ✅ Panel "Cierre de Mes" completo: recuperadas todas las secciones (Resumen compañía, Cierre por vendedor, 11 Titulares, Innovaciones, Sell Out, Planes AS, Acciones Comerciales) desde artefactos versionados congelados.
- ✅ 6 artefactos nuevos congelados en `07_CIERRES_MENSUALES/2026-05/version_001/` (snapshot de `cierre_mes`, solo lectura).
- ✅ Endpoint `cierres_historicos` extendido con bloques `objetivos_avance`, `ccc_segmentos`, `once_titulares`, `innovaciones`, `sellout`, `planes_as`, `acciones_comerciales`.
- ✅ Acumulado unificado: ambas tarjetas usan `ventas_mes.csv` ($285.579.795); avance compañía real 87.39% (antes 4.9% irreal). Objetivo sigue de `resultado.xlsx`.
- ✅ Validado en Render: sin CantBase/botellas, sin errores JS/red, ganador 11T V3 NADIA GAMBINO.

### PRÓXIMOS PASOS (requieren aprobación)
1. **Generador mensual** — `tools/generar_cierre_mensual.py` NO produce hoy los 6 artefactos de detalle (objetivos_avance, 11T, innovaciones, sellout, planes_as, acciones); para junio en adelante se generan recién por el snapshot manual. Evaluar incorporar su generación al cierre mensual para que cada `version_xxx` quede completa sin paso manual.
2. **CCC: criterio entre tarjetas** — "Resumen empresa del cierre" muestra CCC 1.026 (`ventas_mes.csv`) y "Resumen compañía" 827 (`ventas_acumulada.csv`). Se unificó el acumulado (dinero), no el conteo CCC. Evaluar unificar también el CCC a una sola fuente.
3. **Higiene Git CSV regenerados** — pendiente decisión sobre `top_50_caida…` (seguro de destrackear) y `clientes_master.csv` (lo lee `server_orbit.py` en runtime → no destrackear sin regeneración en deploy). Ver auditoría previa.
4. **Inputs modificados sin commitear** — `resultado.xlsx`, `ventas.csv`, `ventas_acumulada.csv` figuran como `M` en el working tree; revisar si son actualizaciones reales a conservar o descartar (no commiteados en esta sesión).

---

## Sesión 2026-06-03 — Consolidación panel "Cierre de Mes" histórico (commit b097300)

### HECHO EN ESTA SESIÓN ✅
- ✅ `/api/gerencia/cierres_historicos` extendido (aditivo, solo-lectura): `empresa` + `ranking` completo (7) + `ganadores` por categoría.
- ✅ Pantalla gerencial "Cierre de Mes" 100% histórica: metadatos + resumen empresa + ranking completo + bloque final ganadores. Eliminada la "Vista dinámica" y el consumo de `/api/gerencia/cierre_mes`.
- ✅ Ganadores Mayo 2026 reauditados desde el cierre versionado: General V8 · Volumen/Dinero V8 · 11T V3 NADIA GAMBINO · Innovaciones V8.
- ✅ Validado en Render (commit `b097300`): sin Vista dinámica, sin CantBase/botellas, sin errores JS/red.
- ✅ No se tocó `07_CIERRES_MENSUALES/`, inputs, datasets, planificaciones, Google Sheets ni datos maestros.

### PRÓXIMOS PASOS (requieren aprobación antes de implementar)
1. **Workflow mensual junio** — cuando cierre junio, correr `python tools/generar_cierre_mensual.py` (detecta `version_001` de junio sin pisar mayo); el panel histórico lo mostrará automáticamente vía el selector de período (`cs.length>1`).
2. **Selector de período visible** — hoy hay un solo cierre (`2026-05`); cuando exista más de uno, validar que el `<select>` de períodos del panel histórico funcione end-to-end.
3. **Endpoint dinámico `/api/gerencia/cierre_mes`** — quedó en el backend sin consumidor en la pantalla Cierre de Mes. Decidir si se conserva para otra vista (mes en curso) o se deprecia formalmente.
4. **Reglas acciones junio** — cambiar `reglas_acciones_mayo_2026_orbit.csv` → `reglas_acciones_junio_2026_orbit.csv` antes del próximo pipeline.
5. **Ranking 11T por porcentaje** — evaluar normalizar 11T por cobertura % (no conteo absoluto) para comparación equitativa entre carteras. Requiere decisión comercial.

---

## Sesión 2026-06-03 — Google Sheets fuente de verdad de planificaciones (commit 93e72a0)

### HECHO EN ESTA SESIÓN ✅
- ✅ Commit `93e72a0` desplegado en Render — estado **Live**.
- ✅ **Google Sheets configurado como fuente de verdad** de planificaciones; SQLite queda solo como caché.
- ✅ Variables en Render (`sync:false`, sin secretos en Git): `GSHEETS_CREDENTIALS_JSON`, `GSHEETS_SPREADSHEET_ID`, `GSHEETS_SHEET_NAME=planificaciones`.
- ✅ `POST /api/planificacion` **fail-closed** validado: guarda+verifica en Sheets o `ok:false` HTTP 503 sin tocar SQLite.
- ✅ `PATCH /api/planificacion/<id>` **fail-closed** implementado: Sheets primero, verifica fila, después SQLite.
- ✅ `GET /api/planificacion`: si SQLite vacío → hidrata desde Sheets → reconsulta SQLite → devuelve id numérico.
- ✅ `restore_planificacion_if_empty()`: CSV → si no hay CSV o está vacío → restaura desde Sheets.
- ✅ Google Sheet `ORBIT_PLANIFICACIONES_PENAFLOR` recibió fila de prueba `id = 2099-01-01_V8` (confirmada visualmente).
- ✅ GET devolvió la fila con id numérico SQLite (`id:1`).
- ✅ Manual Deploy/restart realizado → GET post-redeploy devolvió la fila **hidratada desde Google Sheets**.
- ✅ **Conclusión: las planificaciones ya no se pierden por redeploy/restart de Render Free.**
- ✅ `py_compile server_orbit.py` PASS. `portal.html`, inputs, datasets, cierres y datos maestros no tocados.

### PENDIENTES 🔲
1. **Limpieza fila de prueba** — borrar `2099-01-01_V8` ("TEST PLANIFICACION GOOGLE SHEETS - BORRAR") del Google Sheet. **No borrar sin aprobación del usuario.**
2. **Script backup local** — crear `tools/descargar_planificaciones_sheets.py` (destino `07_PLANIFICACIONES/planificaciones_render.csv`, sin duplicaciones). Etapa separada.
3. **PATCH en producción** — validar un PATCH fail-closed real desde gerencia (aprobar/modificar) confirmando que actualiza la fila en Sheets.

---

## Sesión 2026-06-03 — fix horario Argentina (commit daf443b)

### HECHO EN ESTA SESIÓN ✅
- ✅ Auditado uso de `datetime.now()` y `CURRENT_TIMESTAMP` en `server_orbit.py`.
- ✅ `planificacion_patch()`: `updated_at=CURRENT_TIMESTAMP` (UTC) → `updated_at=?` con `_now_ar()`.
- ✅ `planificacion()` POST log: `datetime.now()` → `_now_ar()`.
- ✅ `backup_orbit_db()`: nombre de archivo → `_now_ar()`.
- ✅ `mensajes()` POST: `created_at` explícito con `_now_ar()`.
- ✅ ~30 endpoints con `generado_en` / `last_sync`: `datetime.now()` → `_now_ar()`.
- ✅ `py_compile` PASS. Render auto-deploy PASS.
- ✅ `last_sync` y `generado_en` en producción coinciden con hora Argentina (15:23 AR vs 18:23 UTC).
- ✅ Login gerencia, `/api/dashboard`, `/api/diagnostico`, `/api/gerencia/cierres_historicos` PASS.
- ✅ `portal.html`, inputs y datos no tocados. Archivos de datos sin stage/commit.

### PENDIENTES 🔲
1. **PATCH planificación en producción** — probar con un plan controlado o de prueba para confirmar que `updated_at` queda en hora Argentina. No ejecutar sobre planes reales sin coordinación.
2. **Migración de históricos** — los registros antiguos en `orbit.db` con `created_at`/`updated_at` en UTC no se migraron. Evaluar si se deben corregir. **No migrar sin aprobación explícita.**
3. **Mensajes históricos** — misma situación: mensajes anteriores al commit `daf443b` tienen `created_at` UTC.
4. **Regla permanente**: toda hora visible en portal debe usar `_now_ar()`. No usar `datetime.now()` naive ni `CURRENT_TIMESTAMP` SQLite en campos que llegan al usuario.

### `datetime.now()` residuales sin corregir (cálculos internos, no visibles)
- Líneas 284, 474, 666, 3216 — cálculos de fecha/calendario internos. No afectan timestamps visibles.

---

## Sesión 2026-06-03 — QA Render producción (post-commit 5a9b7a0)

### HECHO EN ESTA SESIÓN ✅
- ✅ QA Render producción ejecutado — solo lectura, sin modificaciones.
- ✅ Portal HTTP 200 en producción.
- ✅ Login gerencia PASS, login V8 PASS, login inválido → 401 PASS.
- ✅ Dashboard gerencial visible con datos reales (Acumulado $16.0M, Tendencia 58.7%, 7 vendedores).
- ✅ `/api/diagnostico`, `/api/dashboard`, `/api/gerencia/cierre_mes` → PASS.
- ✅ `/api/gerencia/cierres_historicos` → estado OK, 2026-05/version_001, top3 V8·V10·V9, sin warn.
- ✅ Sin errores JS ni errores de red 4xx/5xx.
- ✅ CantBase y botellas no visibles en pantalla.
- ✅ NaN/undefined = 0.
- ✅ Sidebar "Cierre de Mes" presente bajo REPORTES.
- ✅ Validaciones QA PASS.
- ✅ No se modificaron archivos, no commit, no push, no deploy.

### ESTADO ACTUAL EN PRODUCCIÓN
- Commits en producción: `606d1e0` (feat cierre) + `5a9b7a0` (fix path separadores).
- Portal operativo sin regresiones.
- Endpoint `/api/gerencia/cierres_historicos` funcional en Render con rutas Linux.

### PRÓXIMOS PASOS (requieren aprobación antes de implementar)
1. **Tarjeta visual portal gerencial** — consumir `/api/gerencia/cierres_historicos` desde `portal.html` para mostrar selector de período, versión y ranking del cierre. Requiere aprobación.
2. **Ranking 11T por porcentaje** — evaluar cambiar conteo absoluto por `pct_cobertura_11t` para comparación equitativa entre carteras de distinto tamaño. Requiere decisión comercial.
3. **Workflow mensual junio** — cuando cierre junio, correr `python tools/generar_cierre_mensual.py` → detectará `version_001` de junio y creará nueva carpeta sin tocar mayo.
4. **Reglas acciones junio** — cambiar `reglas_acciones_mayo_2026_orbit.csv` → `reglas_acciones_junio_2026_orbit.csv` antes del próximo pipeline.

---

## Sesión 2026-06-03 — Endpoint /api/gerencia/cierres_historicos

### HECHO EN ESTA SESIÓN ✅
- ✅ `GET /api/gerencia/cierres_historicos` agregado en `server_orbit.py` — solo lectura.
- ✅ Lee `07_CIERRES_MENSUALES/index_cierres_mensuales.json` + manifest + ranking_top3 por versión.
- ✅ Sin index → responde `{"cierres":[], "estado":"SIN_CIERRES"}`.
- ✅ Archivo interno faltante → `warn` por entrada, endpoint no rompe.
- ✅ No expone CantBase ni botellas. No recalcula. No llama al script de cierre.
- ✅ `py_compile server_orbit.py` PASS.
- ✅ Probado local: `estado:OK`, `total_cierres:1`, cierre `2026-05/version_001`, top3 V8·V10·V9.
- ✅ `portal.html`, `ventas_mes.csv`, `ventas.csv`, `ventas_acumulada.csv` no tocados.
- ✅ No commit, no push, no deploy.

### PENDIENTE INMEDIATO 🔲
1. **Commit + push + deploy en Render** — incluir `server_orbit.py` (endpoint nuevo) + `tools/generar_cierre_mensual.py` + `07_CIERRES_MENSUALES/` + documentación. Requiere aprobación explícita.
2. **Verificar en Render** — `GET /api/gerencia/cierres_historicos` debe responder `estado:OK` con el cierre de mayo.

### PRÓXIMOS PASOS (requieren aprobación antes de implementar)
1. **Tarjeta visual portal gerencial** — mostrar cierres históricos en portal.html consumiendo `/api/gerencia/cierres_historicos`. Selector de período, version, fecha, estado, top-3 ranking. No implementar hasta aprobación.
2. **Ranking 11T por porcentaje** — evaluar cambiar `clientes_11_titulares` (conteo absoluto) por `pct_cobertura_11t` para comparación equitativa entre carteras de distinto tamaño. Requiere decisión comercial.
3. **Reglas acciones junio** — cambiar `reglas_acciones_mayo_2026_orbit.csv` por `reglas_acciones_junio_2026_orbit.csv` antes del próximo pipeline diario.

---

## Sesión 2026-06-03 — Cierre Mensual Histórico + Ranking

### HECHO EN ESTA SESIÓN ✅
- ✅ `tools/generar_cierre_mensual.py` creado — cierre mensual histórico versionado.
- ✅ Primer cierre generado: `07_CIERRES_MENSUALES/2026-05/version_001/` — 12 archivos, PASS.
- ✅ Ranking Mayo 2026: ganador general V8 ALVAREZ VANESA (84.81), mejor 11T V3 NADIA GAMBINO (231 clientes), mejor innovaciones V8 (44 clientes).
- ✅ Versionado inmutable validado: dry-run detecta `version_002` sin pisar `version_001`.
- ✅ V3 solo Tradicionales validada. V1 y V20 excluidos. CantBase no expuesto en salidas.
- ✅ Timestamps AR correctos (`America/Argentina/Cordoba`, UTC-3).
- ✅ Auditoría read-only PASS en todos los archivos generados.

### RIESGOS DETECTADOS — Seguimiento pendiente
1. **V3 ventaja estructural en 11T**: opera solo TRADICIONAL, cartera naturalmente compra marcas 11T. Evaluar normalizar ranking 11T por % de cobertura (no solo conteo absoluto) antes del próximo cierre.
2. **JW BLACK / JW RED = 0 clientes en mayo**: V4, V7, V8, V10 sin cobertura. Acción comercial pendiente.
3. **V7 score 8.78**: desempeño muy bajo. Revisar cartera, actividad y datos del mes antes del próximo cierre.
4. **Tramo 19% concentrado en 1 cliente**: $1.2M inversión estimada, 9 líneas. Validar con el equipo comercial si es acción especial o error ERP.
5. **Innovaciones bajas**: solo V8 y V9 tienen adopción real. Producto con mejor adopción: CAZADOR MALBEC 6X750 (74814).

### PRÓXIMOS PASOS RECOMENDADOS
- **Workflow mensual**: cuando cierre junio, correr `python tools/generar_cierre_mensual.py` — detectará `version_001` de junio y creará nueva carpeta sin tocar mayo.
- **Portal — tarjeta cierres históricos**: exponer `07_CIERRES_MENSUALES/index_cierres_mensuales.json` como endpoint `/api/gerencia/cierres_historicos` en `server_orbit.py` (etapa futura, requiere aprobación).
- **Ranking — normalización 11T**: evaluar cambiar `clientes_11_titulares` por `pct_cobertura_11t` para hacer comparación más equitativa entre vendedores con carteras de distinto tamaño.
- **Ranking — acciones comerciales por vendedor**: agregar al ranking el uso de descuentos (inversión estimada por vendedor) como métricas informativas adicionales.
- **Actualizar `reglas_acciones` para junio**: cambiar `reglas_acciones_mayo_2026_orbit.csv` por `reglas_acciones_junio_2026_orbit.csv` antes del próximo pipeline.

---

## Sesión 2026-05-28 — Deploy Render + Planificación

### HECHO EN ESTA SESIÓN ✅
- ✅ `/api/healthz` agregado — endpoint liviano para Render health check y UptimeRobot
- ✅ `render.yaml`: healthCheckPath → `/api/healthz`, workers 1, autoDeploy false
- ✅ `Procfile`: workers 1 consistente con render.yaml
- ✅ Timestamps en hora Argentina (UTC-3) en planificación — antes mostraba UTC
- ✅ POST planificación devuelve `hora_envio` en respuesta
- ✅ Re-envíos preservan `created_at`, solo actualizan `updated_at`
- ✅ Vista gerencia: cada card muestra "📅 Enviado hoy HH:MM" con `updated_at`
- ✅ Tarjeta Total PyP: muestra TODOS los planes (no solo aprobados), con columnas Estado + Hora
- ✅ Vista vendedor: muestra "📅 Enviado hoy a las HH:MM" cuando el plan ya existe

### PRÓXIMO PASO 🔲
- **Push**: `git push origin master`
- **Deploy manual en Render**: Dashboard → Manual Deploy (autoDeploy está apagado)
- **Verificar en Render**: logs de arranque → debe aparecer `[ORBIT] Backup orbit.db` y `[ORBIT calendario]`
- **Verificar `/api/healthz`**: debe devolver `{"status":"ok","service":"orbit-penaflor-pav","healthcheck":true}` HTTP 200
- **Actualizar UptimeRobot**: cambiar URL monitoreada de `/api/diagnostico` → `/api/healthz` (más rápido, no depende de datos)
- **Validar en portal gerencia**: CHAMPAÑA ~70% (chip wn), CERVEZA ~25% (chip rojo)

### Pendiente técnico
- Investigar gap SPIRITS Nacionales: sistema 15.139L vs imagen 17.800L (-2.661L)
- Workflow mensual: en junio cambiar `reglas_acciones_mayo_2026_orbit.csv` → junio

---

## Sesión 2026-05-27 — Estado anterior

### HECHO EN ESA SESIÓN ✅
- ✅ Panel 11T en gerencia (endpoints + tarjetas)
- ✅ Tarjeta Sellout reemplazada:
  - Endpoint `/api/gerencia/sellout_litros` — lee ventas.csv, calcula litros vs objetivos
  - Tarjeta en portal: Real / Objetivo / Alcance% (chip coloreado + barra) / Clientes
  - Subcategorías: VINOS DEL AÑO por Linea; SPIRITS por tipo (Importados/Nacionales)
  - Datos validados: 6 categorías con datos reales
- Investigar gap SPIRITS Nacionales: sistema 15.139L vs imagen 17.800L (-2.661L) — posible diferencia de fecha de corte o productos faltantes en ventas.csv

---

## Sesión 2026-05-26 (noche) — Estado actual

### HECHO EN ESTA SESIÓN ✅
- ✅ Acciones comerciales en Alertas del vendedor:
  - `/api/acciones_vigentes` reescrito con tramos y `lineas_segmentos` (reemplaza "3-25%")
  - Portal: marcas y escalones por acción, chip de descuento por tramo
  - V3 sigue sin ver AUTOSERVICIOS
  - Commit `b4c8e6e` pusheado → Render auto-deploy en curso
- ✅ Smartphone responsiveness — perfil vendedor:
  - `viewport-fit=cover` → safe area habilitada en iPhones con notch/home indicator
  - CSS `@supports env(safe-area-inset-bottom)` para bottom nav y content padding
  - Login scrollable cuando el teclado virtual sube (overflow-y:auto + visualViewport API)
  - `@media (max-width:380px)`: pf-grid 1 columna, vkv 20px, touch targets 44px
  - `@media (max-width:340px)`: vkv 17px, tabs compactos para 320px legacy
  - Tab "Mi Plan" → "Plan" (evita desborde en 320px)
  - Botón "Salir" min-height:44px
  - Login logo corregido (assets/orbit-mark.png → orbit_pav_matinal_final.png)
- ✅ Render deployment preparado:
  - `render.yaml` creado
  - `DEPLOY_RENDER.md` guía completa
  - GitHub remote ya existe: matiastorrespyp/orbit-matinal-penaflor

### PRÓXIMO PASO — Render deploy (para hacer)
1. Asegurarse que el repo GitHub esté actualizado: `git push`
2. Ir a render.com → New Web Service → conectar `matiastorrespyp/orbit-matinal-penaflor`
3. Render detecta `render.yaml` automáticamente
4. Plan Starter = $7/mes (no hay tier gratis para apps dinámicas en Render 2024+)
5. **Alternativa gratuita**: Railway.app → $5/mes crédito incluido → efectivamente gratis para tráfico bajo

### PENDIENTES TÉCNICOS
- **Workflow mensual acciones**: en junio cambiar `reglas_acciones_mayo_2026_orbit.csv` por `reglas_acciones_junio_2026_orbit.csv`
  y actualizar la referencia en `generar_acciones_ranking()`. El usuario puede subir las imágenes y Claude genera el CSV.
- **Drop Spirits Vinotecas / Especial Smirnoff 5+1**: ambas muestran los mismos clientes porque comparten
  el segmento ON_PREMISE + categoría SPIRITS. Revisar si son realmente distintas en el ERP.
- **Termidor delta**: muestra `None` en delta_litros porque en abril no había ventas de Termidor para esos clientes.
  El cap de 9999% lo excluye correctamente.
- **Persistencia de datos en Render**: orbit.db se lee del repo (commit necesario). Planificación/mensajes
  escritos en el portal se pierden al re-deployar. Para persistencia: usar Render Persistent Disk ($7/mes extra).

### PRÓXIMAS ETAPAS (portal, por orden de prioridad)
1. **Deploy en Railway / Render** (listo para ejecutar — ver DEPLOY_RENDER.md)
2. **Etapa A — Vista Gerencial dashboard**: verificar gráficas de barras (valores reales vs visualización).
3. **Etapa B — Vista Vendedor individual**: drill-down desde ranking, KPIs de clientes del día.
4. **Etapa C — Clientes Críticos**: validar que la lista y estados vienen de datos reales.
5. **Etapa D — 11 Titulares detalle**: tabla por marca y cliente.

### PENDIENTES TÉCNICOS
- `ccc_mes`: pequeña diferencia ≤2 clientes aceptable por timing de snapshot. No crítico.
- `corridos` en `/api/diagnostico` usa datetime.now() → siempre incluye hoy aunque no haya datos. No bloquea.

## Sesión 2026-05-22 — Estado actual

### HECHO EN ESTA SESIÓN ✅
- ✅ `_clasificar()` corregido: AUTOSERVICIO = SubSegmento real (210 clientes). MAYORISTAS/CASH&CARRY = MAYORISTA.
- ✅ AUTOSERVICIO cartera total=192 (excl. V3). Era 272 inflado.
- ✅ 17 productos innovación cargados y CSV regenerado (era solo 2).
- ✅ 7 datasets en 04_DATASETS_ORBIT/: cobertura_acum, 11t_acum, planes_as, innovaciones_segmento, innovaciones_plan_as, sellout_categoria, acciones_ranking.
- ✅ Dashboard: "Cobertura acumulada del mes" por segmento. Tabla sellout en litros. Card planificados muestra compraron + sin compra del día.
- ✅ Sidebar: botón "Acciones Comerciales". Innovaciones: 17 productos en portal.
- ✅ Acciones comerciales: solo ventas con descuento real. Inversión más precisa.
- ✅ Plan AS: "Escala actual N/max" desde hoja ESCALA (Inicial max=5, Silver max=9, Gold max=12). Sin cargo: verde=enviado / rojo=pendiente por producto.
- ✅ Alertas: 36 → 14. Plan AS con ≤10% descuento no es alerta (es su beneficio de plan).
- ✅ Clientes críticos: solo zona del día sin compra mes. Muestra última compra fecha+importe.
- ✅ `ultima_compra_fecha` y `ultima_compra_importe` en `/api/clientes` desde historial.

### HECHO 2026-05-23 ✅
- ✅ 11T: usa `mod_11t_acum.csv` (cartera completa 1800 clientes) en lugar de Vi-only (548).
- ✅ 11T: agrega objetivo por marca (objetivo 11T.xlsx) y % avance. 18 marcas visibles.
- ✅ Alertas: exluye 11T brands con ≤10% dto (acción comercial válida). 14 → 3 alertas.
- ✅ Filtro `estado.includes('SIN')` eliminado → cliente 8212 (CCC_SIN_COBERTURA) ya no aparece en Clientes Críticos.
- ✅ "Planificados VI" → "Clientes del Día" con labels "mes" explícitos.
- ✅ Card "Sin Comp. Mes": usa solo `compra_mes_flag===0`.

### HECHO EN ESTA SESIÓN (fix UI post-commit df23c5a) ✅
- ✅ Fix NaN inválido en `/api/clientes` → `D.cli` quedaba vacío → "Sin Comp. Mes = 0" y "Clientes Críticos vacío" resueltos.
- ✅ Labels "Sin Comp. Mes/SC Mes" → "Sin Comp. Día/SC Día" (el dato es del día, no del mes).
- ✅ Plan vs Real: "Delta" → "Diferencia".
- ✅ Alertas: código cliente `[ID]` + vendedor `(VX)` por fila.

### HECHO 2026-05-23 (selector de días) ✅
- ✅ `_clientes_por_dia(dia)`: cartera real del día desde clientes.xlsx + compra_mes_flag desde ventas.csv.
- ✅ `/api/clientes?dia=X`: usa cartera del día seleccionado (Lu=302, Ma=353, Vi=550).
- ✅ `/api/dashboard?dia=X`: clientes_total y clientes_pendientes por vendedor para el día seleccionado.
- ✅ `setDay(d)` → async: llama ambos endpoints, actualiza D.cli + D.dash, re-renderiza.
- ✅ `gClientes`: usa `currentDay` como zona (Clientes Críticos filtra por día seleccionado).
- ✅ "Plan.Vi" → "Plan.${currentDay}" en ranking vendedores.

### HECHO 2026-05-23 ✅ (continuación)
- ✅ Panel "Clientes Dormidos": 561 clientes sin compra en período actual, $41.2M en riesgo. Endpoint `/api/gerencia/alertas_caida`. Badge sidebar. Tabla por vendedor + detalle top100.
- ✅ Login: fondo.png, logo ORBIT isotipo 190px flotante, card blanca.
- ✅ Sidebar: logo PyP + "PAV PEÑAFLOR" arriba, logo ORBIT abajo del perfil.

### HECHO 2026-05-26 ✅ — Responsive mobile + default route
- ✅ `server_orbit.py`: `/` ahora sirve `portal.html` (antes: `index.html`). `http://localhost:8502` abre el portal correcto.
- ✅ Responsive: `@media (max-width:768px)` — sidebar drawer deslizable, hamburger, grids 1 col, tablas scroll, topbar compacto.
- ✅ Responsive: `@media (max-width:430px)` — login card compacta, topbar mínimo, KPI cards ajustadas.
- ✅ `openNav()` / `closeNav()` + overlay + hook en `gSw()` → UX de navegación mobile completa.

### HECHO 2026-05-26 ✅ — Login rediseño
- ✅ Login: toggle ☀️/🌙 (top-right, glass pill) — persiste en localStorage.
- ✅ Login: fondos de día (`fondo.png`) y noche (`fondo_noche.png`) con transición suave (opacity 1.4s).
- ✅ Login: cielo animado — sol (arc 30s + glow), 4 nubes de día (sentidos opuestos), luna (arc 34s + glow azul), 2 nubes nocturnas, 90 estrellas generadas en JS con `starTwinkle`.
- ✅ Login: card blanca eliminada → glass dark (`backdrop-filter:blur(32px)`, border rgba semitransparente).
- ✅ Login: logo `orbit_pav_matinal_final.png` 176px flotante (sin sonido), selector de perfil con nombres legibles, campo contraseña. Sin el tag "Peñaflor · PAV Matinal" duplicado.
- ✅ `fondo_noche.png` y `orbit_pav_matinal_final.png` copiados a `PAV MATINAL PE_A FLOR/`.

### HECHO 2026-05-26 ✅ — Fix Planes AS + reglas de negocio formalizadas
- ✅ Fix detección sin cargo: reemplaza Marca por Articulo como fuente primaria. Corrige 3 bugs ERP:
  NaN Marca (Frizze 14619/14620), Marca incorrecta (74510 "F.Las Moras" con Marca="Alaris"),
  abreviatura SMF (35103/35104/35105 "SMF ICE" = Smirnoff). 8/31 genuinamente pendientes.
- ✅ Regla FechaComprobante: fecha válida siempre = facturación, nunca entrega. Corregido en
  app_matinal_penaflor.py (4 lugares) y tools/orbit_truth_audit.py. Guardado en memoria.
- ✅ Regla fuente Plan AS: sin cargos enviados = solo ventas.csv (período mensual). BBDD se
  renueva mensualmente. ventas_acumulada no aplica. Comentario fijo en pipeline.
- ✅ Resultado: 7/31 genuinamente pendientes. Portal CLI 2357 sc_pend_frizze=0 ✓.

### PENDIENTE INMEDIATO

1. **Regeneración diaria:**
   - Actualizar `EJECUTAR_ORBIT.bat` para correr `python generar_datasets_acum.py` antes del pipeline.

2. **Dormidos — refinamiento opcional:**
   - Filtro por vendedor dentro del panel (ya hay `gFiltro` global, se puede conectar).
   - Alertas comparativas a nivel producto: cliente que compraba X marca y dejó de hacerlo.

### Pendientes opcionales
- 11T acumulado visible en dashboard gerencia.
- Objetivo de cobertura 11T por segmento/marca (archivo `09_CONFIG/objetivos_11t.csv`).
- Semántica CCC Mes vs Sin Comp. Mes.



## Sesión 2026-05-19 — Cierre confirmado (commit b16a54c)

### Estado final
- Regla V20 formalizada: `VENDEDORES_EXCLUIDOS = [2, 5, 20]` en motor legacy.
- Documentación actualizada: `CLAUDE.md` y `REGLAS_NEGOCIO_PAV.md`.
- Auditoría completa del estado del proyecto realizada. Portal, inputs, datasets y orbit.db intactos.

### ~~Próximo paso — Prioridad 1~~ ✅ COMPLETADO 2026-05-19

**Validar Etapa B1 del portal — PASS backend + visual.**

Backend y portal validados. Ver CHANGELOG_AI.md entrada 2026-05-19.

### ~~Próximo paso — Prioridad 1~~ ✅ COMPLETADO 2026-05-19

**Diagnosticar y corregir error JS 404.**
Diagnosticado: `/favicon.ico` ausente. Fix: ruta Flask `@app.route("/favicon.ico") → 204`. Commit `7ef8edb`.

### Pendientes adicionales actualizados — 2026-05-19

- ~~**Recalcular `clientes_sin_compra_mes`**~~ ✅ Fix motor legacy commit `9e89030`. Dif = 0 en todos los vendedores.
- ~~**Favicon 404**~~ ✅ Resuelto con ruta Flask 204, commit `7ef8edb`.
- **Decidir limpieza** de `portal.html.bak.2026-05-14` y `screenshots/` — pendiente, no urgente.

### ~~Próximo paso — Prioridad 1~~ ✅ COMPLETADO 2026-05-19

**Validación integral portal gerencia + vendedor post-fix — PASS.**
APIs 200, excluidos 404, portal gerencia correcto, Sin Comp. Mes = 262 coincide con motor. Sin errores JS ni 404s. Ver CHANGELOG_AI.md entrada 2026-05-19.

### Próximo paso — Prioridad 1

**Definir y unificar semántica: CCC Mes vs Sin Comp. Mes.**

**Problema:** el portal mezcla dos universos en la misma vista gerencial:
- "CCC Mes" en ranking → cartera completa mes actual (`server_orbit._ccc_mes_por_vendedor()`, ventas.csv).
- "Sin Comp. Mes" → zona Vi del día (`clientes_dia`, motor).

Comparar estos dos números en el mismo contexto es semánticamente incorrecto.

**Decisión pendiente (sin tocar código hasta resolver):**
1. Opción A: mostrar ambos con etiquetas explícitas de universo.
2. Opción B: unificar ambos al universo de zona Vi (cartera planificada del día).
3. Opción C: unificar ambos al universo de cartera completa del mes.

**Restricciones:** proponer diseño primero, alineado con sistema visual existente. No implementar sin aprobación.

### ~~Prioridad 2: Módulo Innovaciones Plan AS~~ ✅ COMPLETADO 2026-05-19 — INOV-1

**Motor:** `generar_mod_innovaciones_plan_as()` en `LEGACY/orbit_matinal_v42.py`.
**Dataset:** `04_DATASETS_ORBIT/mod_innovaciones_plan_as.csv` — 28 filas / 9 columnas.
**Denominador:** 13 (columnas Si/No del xlsx). NaN = no aplica para PYP.
**Antares P770/P330:** solo en `productos_pendiente_stock`. Fuera del denominador.
**Frizze M y Antares XPA:** NaN en xlsx PYP → van en módulo separado INOV-2.

### ~~Prioridad 2: INOV-2 Frizze Manxana + Antares XPA por segmento~~ ✅ COMPLETADO 2026-05-19

**Dataset:** `04_DATASETS_ORBIT/mod_innovaciones_segmento.csv` — 26 filas / 10 columnas.
**Motor:** `generar_mod_innovaciones_segmento()` en `LEGACY/orbit_matinal_v42.py` — commit `a651d01`.
**Fuente:** `ventas.csv`. Segmentos: Tradicional / Autoservicio. V2/V5/V20 y V3/AUTOSERVICIO ausentes. ✅

### ~~Prioridad 2: INOV-3 Endpoints Innovaciones~~ ✅ COMPLETADO 2026-05-19

**Endpoints:** `server_orbit.py` — commit `b11ab9d`.
- `/api/gerencia/innovaciones_segmento` y `/api/vendedor/<id>/innovaciones_segmento`.
- Validación 10/10 PASS. Sin V2/V5/V20. Sin V3/AUTOSERVICIO. `clientes_faltantes` como list. ✅

### ~~Prioridad 2: INOV-4 UI Innovaciones por segmento~~ ✅ COMPLETADO 2026-05-20

**Commit:** `5c8434a` — `PAV MATINAL PE_A FLOR/portal.html`.
- Gerencia: bloque full-width Innovaciones (cards + tabla cobertura por vendedor). V2/V5/V20 excluidos.
- Vendedor: card Innovaciones en KPIs (barras + clientes_faltantes). V3 sin AUTOSERVICIO.
- Playwright 15/15 PASS. Endpoints INOV-3 200 OK.

### ~~Prioridad 2: INOV-5 Mejora visual Innovaciones~~ ✅ COMPLETADO 2026-05-20

**Commit:** `b247410` — `PAV MATINAL PE_A FLOR/portal.html`. Pusheado.
- Fase 1: auditoría visual + endpoints crudos. V3 0% = dato real. V4/Gerencia coinciden. V2/V5/V20 ausentes.
- Fase 2: wording "Sin compradores aún", cards 260px, tabla compacta X/Y + mini-barra. Sin tocar lógica ni backend.

### ~~Prioridad 2: INOV-6a endpoint plan_innovaciones~~ ✅ COMPLETADO 2026-05-20

**Commit:** `ebb0d17` — `server_orbit.py`. Pusheado.
- `GET /api/vendedor/<vid>/plan_innovaciones` — read-only.
- Faltantes enriquecidos: `en_zona_hoy`, `enriquecimiento` (completo/parcial/sin_datos).
- Fuentes: `mod_innovaciones_segmento.csv` + `clientes_dia.csv` + `clientes_master.csv`.
- V3 sin AUTOSERVICIO. V2/V5/V20 → 403. Endpoints INOV-3 intactos.

### ~~Prioridad 2: INOV-6b UI Plan de Acción en portal.html~~ ✅ COMPLETADO 2026-05-20

**Commit:** `ff5e17a` — `PAV MATINAL PE_A FLOR/portal.html` (único archivo).
- Card "📋 Plan Innovaciones" en KPIs vendedor, debajo de 🚀 Innovaciones.
- Fuente: `/api/vendedor/<id>/plan_innovaciones`.
- Máx 5 clientes por producto/segmento. Badge "hoy", chips ALTA/MEDIA/BAJA, ruta+día opcionales. "+N más" si hay overflow.
- V3 sin AUTOSERVICIO. Si endpoint falla, card no se renderiza.
- test_inov4.py 15/15 PASS. Sin errores JS.

### ~~Prioridad 2: INOV-6c ranking de oportunidad Innovaciones (gerencia)~~ ✅ COMPLETADO 2026-05-20

**Commit:** `e2bad1b` — `PAV MATINAL PE_A FLOR/portal.html` (único archivo).
- Card "🎯 Ranking de Oportunidad — Innovaciones" en `gDashboard()`, debajo de Cobertura por vendedor.
- Sin nuevo endpoint. Usa `D.inov.por_vendedor` ya disponible.
- Ordena por faltantes DESC. V2/V5/V20 excluidos. pctProm con 1 decimal + mini-barra.
- 14/15 PASS. Único FAIL: extracción automática de orden en test (timing), no falla funcional.

### Próximo paso — Prioridad 2: INOV-7 (por definir)

- Ciclo Innovaciones completado: motor (INOV-1/2), endpoints (INOV-3), UI vendedor (INOV-4/5/6b), UI gerencia (INOV-6c).
- Posibles próximos pasos: cierre formal del ciclo, nueva funcionalidad, o mejora de cobertura de tests.
- No implementar sin definición aprobada.

---

## Sesión 2026-05-14 — Cierre confirmado (commit c67e70e)

### Estado final
- `portal.html` rediseñado y commiteado. Dos portales activos: gerencial desktop + vendedor mobile.
- `server_orbit.py`: endpoint `/api/vendedor/{id}` implementado y funcionando con datos reales.
- `test_portal.py` y `test_kpis.py` creados y commiteados.
- V3 Nadia Gambino: regla autoservicio aplicada en servidor y en portal (columna AUTOSERV. oculta).
- 11 Titulares: usa datos por vendedor del nuevo endpoint.

### Pendientes próxima sesión (no bloquean operación diaria)

1. **Revisar portal visualmente en navegador** — validación visual humana del diseño (gerencia en desktop, vendedor en mobile/devtools 390px). Los screenshots de Playwright confirman carga técnica pero no aprobación visual final.

2. **Validar con datos reales del próximo cierre operativo** — la próxima vez que se actualicen `ventas.csv` y `resultado.xlsx`, regenerar datasets y verificar que todos los KPIs del portal reflejan los nuevos valores correctamente.

3. **Favicon** — agregar `favicon.ico` en `PAV MATINAL PE_A FLOR/` para eliminar el 404 cosmético de browser.

4. **Decidir limpieza de archivos no commiteados:**
   - `PAV MATINAL PE_A FLOR/portal.html.bak.2026-05-14` — backup del rediseño (se puede borrar cuando el diseño esté aprobado).
   - `screenshots/` — capturas de validación (se puede limpiar o gitignorear).
   - `CHANGELOG_AI.md` y `NEXT_TASK.md` — pendientes de commit cuando el usuario lo indique.

5. **Resolver conflicto portal.html vs index.html** — Flask sirve `index.html` en `/` pero el portal activo es `portal.html`. Evaluar si redirigir `/` → `portal.html` o unificar en un solo archivo.

---

## Sesión 2026-05-12 — Módulo VDA completado (PROMPT_004)

### Estado final
- Todos los datasets VDA generados con datos reales (57,280 filas VDA, 764 clientes)
- Mes actual (mayo) incompleto — datos hasta 2026-05-11; balance negativo es esperado
- V20 en ranking VDA — no figura en la lista de vendedores activos Peñaflor; validar con usuario

### Próximas acciones VDA (Fase 2)

1. **Validar V20** — ¿Es un vendedor activo no registrado? ¿Error de datos?
2. **Integrar módulo VDA en pipeline diario** — agregar llamada a `_tmp_auditoria_vda.py` (o extraer función) desde `orbit_matinal_v42.py`.
3. **Exponer `/api/vda`** en `server_orbit.py` sirviendo `vda_clientes_ganados.json`.
4. **Agregar hoja VDA** a `MATINAL_PENA_V42.xlsx` para exportación automática.
5. **Resolver encoding `producto activos.xlsx`** — exportar desde Gescom con UTF-8.

---

## Sesión 2026-05-12 — Auditoría total (PROMPT_003)

Auditoría completa ejecutada. Ver `AUDITORIA_ORBIT_MATINAL_2026-05-12.md` para diagnóstico completo.

### Próximas acciones por fase (resultado de la auditoría)

#### FASE 1 — Inmediato (sin código)
1. **Exportar `producto activos.xlsx`** desde Gescom → colocar en `01_INPUTS/`. Sin esto, 11 Titulares usa mapa hardcodeado.
2. **Resolver `portal.html` vs `index.html`**: portal.html fue actualizado 2026-05-11 22:41 pero Flask sirve index.html. ¿Cuál es el activo?
3. **Eliminar archivos basura** raíz: `3`, `float`, `None`, `str`, `pd.DataFrame`, `Dict[str]` (creados 2026-04-10).

#### FASE 2 — Motor (requiere código)
4. Implementar `ccc_mes` acumulado desde `historial_ventas_cliente.csv` en `orbit_matinal_v42.py`.
5. Exportar como CSV `mod_ccc_mes.csv` en `04_DATASETS_ORBIT/`.
6. Exponer `ccc_mes` en `/api/diagnostico` y `/api/dashboard`.
7. Actualizar `data.js` para consumir `ccc_mes` real.

#### FASE 3 — Limpieza
8. Deprecar `app_publish.py` (genera JSONs obsoletos, no forma parte del pipeline).
9. Desactivar o actualizar `/api/orbit-data` en `server_orbit.py`.
10. Archivar `06_APP_DATA/*.json` obsoletos (generados 2026-05-05).
11. Mover `src/orbit/` a `LEGACY/` si no tiene consumidor activo.

---

## Estado sesión 2026-05-07 — Auditoría portal

### Commits realizados en esta sesión
| Hash | Descripción | Archivo(s) |
|---|---|---|
| `7a4f7e8` | `/api/clientes` y `/api/alertas` → CSVs reales | `server_orbit.py` |
| `076db05` | Días comerciales con feriados reales | `server_orbit.py` |
| `8e6bd78` | Documentación: estado real de auditoría | `CHANGELOG_AI.md`, `NEXT_TASK.md` |
| `a24d34f` | Etiqueta "visitados" → "planificados" | `dashboard.jsx` |
| `67a62b7` | Launcher portal ORBIT | `ABRIR_CLAUDE_ORBIT.bat` |
| `b242b7c` | `.gitignore` para `__pycache__/` | `.gitignore` |

### Datos de entrada sin commitear (no son errores)
- `01_INPUTS/resultado.xlsx` — modificado (datos ERP del día, actualización diaria normal)
- `01_INPUTS/ventas.csv` — modificado (ventas del día, actualización diaria normal)
- Estos archivos **no deben commitearse** sin confirmación explícita del usuario.

### Qué NO tocar sin confirmación
- `server_orbit.py` — endpoint Flask estable, 7 vendedores, todos los KPIs funcionando
- `PAV MATINAL PE_A FLOR/screens/dashboard.jsx` — JSX limpio, sin mock, sin hardcode
- `PAV MATINAL PE_A FLOR/data.js` — contrato de datos real, sin mock
- `ABRIR_CLAUDE_ORBIT.bat` — launcher correcto recién creado
- `.gitignore` — recién creado
- `01_INPUTS/` — datos de entrada, solo el usuario los actualiza
- `LEGACY/orbit_matinal_v42.py` — motor estable, no tocar sin nueva tarea específica
- `09_CONFIG/clientes_excluidos.csv` — 10 exclusiones formalizadas, estable

### Validación funcional — 2026-05-07 (servidor activo, sin cambios de código)

**Portal operativo. Sin mock activo en ningún bloque auditado.**

| Endpoint | Estado | Detalle |
|---|---|---|
| `/api/diagnostico` | ✓ REAL | total=24, corridos=5, botellas 1406/9050, 3 segmentos, 28 titulares |
| `/api/dashboard` | ✓ REAL | 7 vendedores, sin_maestro=False todos |
| `/api/clientes` | ✓ REAL | 340 items, estados y prioridades reales |
| `/api/alertas` | ✓ REAL | 103 items, descuentos reales por artículo |
| `/api/gastos_accion` | ✓ REAL | 26 filas, exceso $231k |
| `/` + `/data.js` | ✓ HTTP 200 | portal y contrato de datos cargan |
| `/api/planificacion` | ⚠ VACÍO | esperado — sin fuente real aún |

**Decisiones confirmadas — no cambiar sin nueva instrucción:**
- Sábados cuentan como días comerciales. `corridos=5` al 2026-05-07 es correcto.
- `/api/alertas` no mezcla SIN_COMPRA_MES. Los clientes sin compra están en `/api/clientes`.
- `/api/planificacion` vacío es esperado si no hay fuente real.

### Pendientes funcionales (no bloquean portal)

1. ~~**`vendedor_codigo` en gastos_accion**~~ → ✓ Resuelto commit `4cbbbee`. Función `normalizar_vendedor_codigo()` — 9/9 casos validados. HTTP 200, V10/V9/V8/V3 correctos, importes sin cambio.
2. **`ccc_mes: 0`** — honesto; ningún CSV actual tiene CCC acumulado del mes.
3. **Bloque A (ERP externo)** — completar `clientes.xlsx` con datos faltantes de algunos clientes V7/V9. Requiere datos externos, no tiene código pendiente.
4. **Automatización de regeneración** — `ABRIR_CLAUDE_ORBIT.bat` solo abre el portal. El pipeline (`run_orbit.py` + `datasets_orbit.py`) sigue siendo manual. Decidir si automatizar con un segundo BAT o integrar en el mismo.

### Qué NO tocar sin confirmación
- `server_orbit.py` — estable, 7 vendedores, todos los endpoints funcionando
- `PAV MATINAL PE_A FLOR/screens/dashboard.jsx` — sin mock, sin hardcode
- `PAV MATINAL PE_A FLOR/data.js` — contrato de datos real
- `ABRIR_CLAUDE_ORBIT.bat` — launcher correcto
- `01_INPUTS/` — solo el usuario actualiza estos archivos
- `LEGACY/orbit_matinal_v42.py` — motor estable
- `09_CONFIG/clientes_excluidos.csv` — 10 exclusiones formalizadas

---

## Próxima tarea — sesión 2026-05-05

### Bloque A — Requiere datos externos (ERP)
**Actualizar `clientes.xlsx` con clientes de V7 y V9.**
Causa raíz: `codven=7` y `codven=9` ausentes del maestro. Sin esto, el motor legacy no genera rutas ni métricas de cobertura para estos vendedores.
- Clientes de V7: `7898`, `7931`, `1210`
- Clientes de V9: `1094`, `1285`, `8125`, `1362`, `1387`, `8010`, `769`, `388`, `8139`, `1089`, `1093`
- Datos necesarios por cliente: `Razon_Social`, `Ramo`, `DiasVisita`, `Localidad`, `SubSegmento`

### ~~Bloque B~~ — ✓ Completado 2026-05-06
Eliminados todos los datos hardcodeados del frontend (`dashboard.jsx` y `app.jsx`):
- `cccSpark` → `null`; Sparkline CCC → `null`
- `"Cierre proyectado al 30/05"` → `cierreProyectado` calculado desde `data.fechaCorta`
- `"MR"` / `"Manuel R."` → `"SV"` / `"Supervisor"`
- `"Vista mobile · Milagros Ortega"` → `"Vista mobile · vendedor"` (hallazgo adicional)

### ~~Incorporación V7/V9 al maestro~~ — ✓ Completado 2026-05-06
clientes.xlsx actualizado manualmente (+302 V7, +355 V9). Pipeline motor→adaptador re-ejecutado.
- Fallback `sin_maestro` de server_orbit.py ya no se activa para V7/V9 (tienen filas reales en mod_volumen_vendedor).
- Deuda menor: 2 clientes V7 y 8 clientes V9 sin `DiasVisita` en clientes.xlsx.
- `acciones_comerciales.csv` pendiente de integración (bloque separado).

### ~~Bloque C~~ — ✓ Completado 2026-05-06
`ventas_mes` ahora se construye desde `historial_ventas` (acumulado) en lugar de `ventas_validas` (solo 2 días).
- `importe_mes > 0`: 175/255 clientes MI (antes: 0/255)
- Suma importe_mes: $26.608.333
- `ventas_ayer` sin cambios (correcto)

### ~~Bloque D~~ — ✓ Completado 2026-05-06
`server_orbit.py` expone `segmentos` y `titulares11` desde CSVs reales; `data.js` los consume vía `diag.*`.
- `segmentos`: TRADICIONAL 330 clientes / 12 cubiertos; AUTOSERVICIO 40 / 12; ON_PREMISE_VTK 30 / 1
- `titulares11`: 28 marcas, top Alma Mora 66/398, Cazador 19/353
- `ccc_mes: 0` permanece honesto — sin fuente de CCC acumulado disponible en ningún CSV actual

### ~~Bloque E~~ — ✓ Completado 2026-05-06 (registrado, sin integrar consumidor)
- `acciones_comerciales.csv` restaurado a texto CSV real (8 filas, configuración de alertas para `config_comercial.py`).
- `reglas_acciones_mayo_2026_orbit.csv` creado: 31 reglas comerciales Mayo 2026 (descuentos por canal/categoría/cantidad).
- `reglas_acciones_mayo_2026_orbit.json` y `acciones_mayo_2026_formato_gastos_orbit.xlsx` trackeados.

### ~~Bloque F~~ — ✓ Completado 2026-05-06
`calcular_descuento_maximo()` ahora lee `reglas_acciones_mayo_2026_orbit.csv` como fuente primaria.
- AS + VDA + 1–9 cajas → 6.0% (`MAY26-GRAL-AS-VIN-001`) en lugar de 10.0% hardcodeado.
- `mod_alertas_descuentos`: 103 filas (antes: 14). 91/103 con `fuente_regla = MAY26-...`.
- Fallback hardcodeado activo para productos/segmentos sin cobertura en CSV (12 filas).

### ~~Bloque G~~ — ✓ Completado 2026-05-06
`mod_gastos_accion` generado en `MATINAL_PENA_V42.xlsx` y exportado a `04_DATASETS_ORBIT/` por `datasets_orbit.py`.
- 26 filas (fuente_regla × vendedor), 0 NaN/Inf, `gasto_real > gasto_teorico` garantizado.
- Mayor exceso: `MAY26-GRAL-TRAD-SPI-LOC-001` V10 → $83.166 | `MAY26-GRAL-AS-VIN-001` V9 → $58.982.
- Diagnóstico clave: `valor_descuento` ERP = por unidad (no por línea); correcto es `× cant_base`.
- Sin consumidor en portal todavía — deuda separada.
- ~~**Días hábiles**~~: ✓ Resuelto en commit `ef59d83`.

### Bloque H — Pendiente

#### ~~DiasVisita gaps~~ — ✓ Resuelto 2026-05-07
10 clientes sin `DiasVisita` en `clientes.xlsx` (V7: 2, V9: 8). Todos cerrados formalmente.

**10 casos cerrados — excluidos de todo análisis comercial:**
- `402` – CONSUMIDOR FINAL, V7, Ruta=DEPOSITO VILLA DOLORES: placeholder de venta directa, no es cliente de ruta. En `clientes_excluidos.csv` + regla dinámica.
- `20001`–`20038` (8 empleados V9, Ramo=Empleados, Ruta=BEBIDAS VD, Frecuencia=Eventual): compras vía DEPOSITO (codven=20), no visitas programadas. En `clientes_excluidos.csv`.
- `8614` – BUSTAMANTE JUAN, V7, Ruta=DEPOSITO VILLA DOLORES, sin ventas activas ni historial: excluido por CSV + regla dinámica. Commit `fe913dd`.

**Regla dinámica activa:** todo cliente con Ruta que contiene "DEPOSITO" y sin `DiasVisita` queda excluido automáticamente en `cargar_clientes()`, sin necesidad de estar en el CSV.

#### ~~Consumidor `mod_gastos_accion`~~ — ✓ Completado 2026-05-06
`/api/gastos_accion` expuesto en `server_orbit.py` (commit `4867990`).
- `resumen`: exceso total $231.133, 4 vendedores alertados, 26 filas, 18 acciones CSV + 8 fallback.
- `top_acciones`: top 5 por exceso_pesos agrupado por accion_id.
- `top_vendedores`: top 5 — V10 Ortega $93.169, V9 Sánchez $81.043.
- `detalle`: 26 filas completas. Sin NaN. Sin cambios a endpoints existentes.
- Pendiente: consumo desde `data.js` para vista gerencial del portal.

#### ~~`data.js` → portal gerencial~~ — ✓ Completado 2026-05-06
`window.ORBIT_DATA.gastosAccion` disponible. Dashboard muestra 3 cards al final:
resumen (exceso total, gasto real, vendedores, clientes), top 5 acciones y top 5 vendedores.
Se oculta automáticamente si no hay datos. Commit `c3f7813`.

#### ~~Clientes no comerciales excluidos formalmente~~ — ✓ Completado 2026-05-07
`09_CONFIG/clientes_excluidos.csv` (10 filas) + regla dinámica por Ruta DEPOSITO sin DiasVisita. Commits `97993d2`, `fe913dd`.
- Excluidos por CSV: `402`, `20001`, `20008`, `20011`, `20021`, `20027`, `20029`, `20031`, `20038`, `8614`
- Regla dinámica en `cargar_clientes()`: Ruta contains DEPOSITO & DiasVisita vacío → excluido automáticamente
- Validación: ninguno de los 10 en `mod_alertas_descuentos`, `clientes_dia` ni outputs post-regeneración.

#### Pendientes adicionales Bloque H
- **`02_PLANTILLA_GASTOS` del Excel**: pendiente de integración si se necesitan gastos proyectados vs. reales desde la plantilla original.

---

## Problemas pendientes detectados en auditoría (2026-05-05)

1. **V7 y V9 ausentes** en datasets (ver arriba).
2. ~~**Días hábiles en `server_orbit.py`**~~ → ✓ Resuelto commit `076db05`. `total=24`, `corridos=3`, feriados leídos desde `09_CONFIG/feriados.csv`.
3. **Acumulado=0** en `dashboard_vendedor.json` → `app_publish.py` busca columna `acumulado` pero `mod_volumen_vendedor.csv` tiene `acumulado_mes` → retorna 0 para todos.
4. ~~**Datos hardcodeados en frontend**~~ → ✓ Resuelto (Bloque B + commit `a24d34f`). Sin mock, sin nombres de persona, etiqueta "planificados" correcta.
5. ~~**`orbit_portal_data.json`** tiene estructura distinta~~ → No bloqueante: ningún endpoint activo lo consume. JSONs estáticos de `app_publish.py` (`clientes_hoy.json`, `alertas_app.json`) reemplazados por CSVs reales en commit `7a4f7e8`.
6. ~~**Importes = 0 en clientes_dia.csv**~~ → ✓ Resuelto (Bloque C + botellas expuestas en commit `c1124b5`). `importe_mes > 0` en 199/400 clientes. `botellas_dia=1406`, `botellas_mes=9050` en `kpisGerencia`.
7. **`ccc_mes: 0`** en `data.js` — correcto y honesto pero pendiente: necesita fuente real de CCC acumulado del mes (no existe en ningún CSV actual).
8. ~~**Segmentos `cubiertos: 0`**~~ → ✓ Resuelto (Bloque D). `server_orbit.py` expone segmentos reales desde `mod_ccc_segmento.csv`; `data.js` consume `diag.segmentos`.
9. ~~**`titulares11` incompleto**~~ → ✓ Resuelto (Bloque D). 28 marcas reales desde `mod_11_titulares.csv`; `data.js` consume `diag.titulares11`.

## Resueltos en esta sesión (2026-05-05)
- ✓ `data.js` restaurado como JavaScript válido (era código Python).
- ✓ `diaActivo` ahora se calcula desde `fecha_corte + 1 día` → "MI".
- ✓ Título de la matinal en `app.jsx` ahora es dinámico → "Miércoles 06/05".
- ✓ `ccc_dia` ahora toma el valor real de `mod_ccc_segmento`; `ccc_mes` queda en 0 (honesto).
- ✓ `acumulado=0` corregido en `app_publish.py`: `"acumulado_mes"` agregado como primer candidato en `build_avance_map()`.
- ✓ V7 y V9 visibles en `/api/dashboard` con fallback desde `resultado.xlsx` (`sin_maestro: true`). Deuda: actualizar `clientes.xlsx`.
## Siguiente tarea - validar flujo Render Plan vs Real

1. Confirmar que Render acepto el disco persistente `orbit-data` y que `ORBIT_DB_PATH=/var/data/orbit.db` aparece en el entorno.
2. Enviar un plan desde un usuario vendedor despues del mediodia y verificar que queda fechado para la proxima matinal.
3. Aprobar el plan desde gerencia en Render.
4. Al dia siguiente, actualizar `ventas.csv`, ejecutar `CIERRE_DIA_ORBIT.bat` y verificar en Render que Plan vs Real muestra el cierre de la fecha anterior aunque ya existan planes nuevos.
5. Validar en la solapa Planificacion que el selector "Matinal YYYY-MM-DD" trae todos los vendedores de la fecha elegida.
6. Si Render rechaza `plan: starter` o `disk` por configuracion de cuenta, corregir el servicio desde el dashboard de Render antes de reintentar deploy.
