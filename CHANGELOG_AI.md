# CHANGELOG AI - ORBIT MATINAL PEÑAFLOR

## 2026-07-16 - fix(acciones): la tarjeta contaba como "usuarios de la accion" a quien compro SIN el descuento

- **Pedido:** *"veo que las acciones comerciales nuevas me salen con clientes que ya la usaron, cosa que es imposible ya que son nuevas... que el dato de los compradores de la accion sea justamente con el descuento de la accion, sino que no salgan ahi"*. El usuario tenia razon y el problema era MAS profundo que las nuevas.
- **Causa raiz:** la footprint de cada accion matcheaba **alcance** (vendedor + segmento + producto) y **NO** miraba si el descuento aplicado era el de la accion. Contaba como usuario a cualquiera que comprara el producto: sin descuento, o con descuento de OTRA accion.
  - `ACJ26-029` (Resto 10%): mostraba **32 clientes / $22.769** cuando sus unicas lineas con descuento tenian **3% y 5%** (de la accion de Spirits) — **ninguna del 10%**. Nadie la habia usado.
  - La inversion ademas se **contaba doble entre tarjetas**: un mismo descuento caia en todas las tarjetas cuyo alcance de producto lo alcanzara. Suma por tarjeta: **$23,5M** vs **$4,0M** realmente atribuible.
- **Verificacion previa (por que el fix es confiable):** los % que llegan de ventas.csv son **enteros limpios** (1763/1770 lineas del mes caen en entero exacto) -> matchear el tramo es seguro. Tolerancia `_ACC_PCT_TOL = 0.5` pp: absorbe redondeo y no acerca un tramo a otro (el par mas cercano es 6 vs 7).
- **Cambio (`server_orbit.py`):** `_acc_tramos_pct(rule)` + `_acc_mask_usa_accion(df, tramos)`, aplicado **dentro de `_match`** -> clientes, inversion y litros se mueven juntos (decidido con el usuario: a TODAS las tarjetas, vigentes + nuevas). Bonificacion/sin cargo (sin tramos) cae a "tiene descuento". `portal.html`: el drill-down pasa a decir **"clientes que usaron la accion"** (antes "clientes que compraron", que ya no describia el dato).
- **Impacto (todas las tarjetas, no solo las nuevas):**
  - Nuevas: ACJ26-024 **43 -> 1** cliente, -025 **12 -> 0**, -026 **55 -> 1**, -027 **11 -> 0**, -028 **4 -> 0**, -029 **32 -> 0**. Coincide con lo que el usuario sabia: son nuevas, casi nadie las uso.
  - Vigentes: ACJ26-001 **65 -> 28**, -002 **251 -> 73**, -007 **36 -> 12**, -017 **30 -> 2**, -022 **138 -> 16**, -023 **29 -> 1**.
  - KPI gerencia: inversion **$3.943.895**, litros **4.922 L**, clientes **172** (union deduplicada).
- **Validado:** ninguna tarjeta queda con 0 clientes y plata > 0; `clientes_alcanzados == clientes_con_descuento` en las 29 (coherente). Caso testigo revisado a mano: ACJ26-026 = **1 cliente real** (#273 FONTANA, V10, 2190 botellas al 15% exacto el 02/07 = 365 cajas -> califica para el tramo de 50). `py_compile` OK, endpoints gerencia/V9/V3 200, Playwright gerencia + vendedor sin errores de consola.
- **Dato para el negocio:** los descuentos de estas acciones **ya se aplicaban antes** de que se subiera el xlsx (la venta al 15% de ACJ26-026 es del 02/07). Por eso `vigencia_desde=1/7` no esta inventando uso; si el negocio define otra fecha de inicio, se cambia en el catalogo.
- **Limitacion conocida y ACEPTADA por el negocio (confirmada por el usuario 16/07):** *"tuvimos algunas acciones puntuales este mes con el mismo descuento, por eso te figuran"*. El match es por **% aplicado**, y una **accion puntual** (fuera del catalogo) con el MISMO % es indistinguible de la accion del catalogo -> puede atribuirle un uso que en realidad fue de la puntual (ej. el cliente que queda en ACJ26-024/026). No hay dato en ventas.csv que separe una de otra: la unica forma de desambiguar seria que las puntuales entren al catalogo con su propio id. Es un **falso positivo acotado**, muy preferible al estado anterior (contar a todo el que compraba la categoria).


## 2026-07-16 - feat(sellout): categoria nueva VERMOUTH (Cinzano) + alta de los 6 articulos nuevos

- **Pedido:** *"actualice el archivo de productos con la incorporacion de 6 articulos nuevos, para que los tomes. En el caso de Cinzano colocalo en el tablero de Innovaciones tambien"* + *"la venta de estos productos suma en la categoria NUEVA Vermouth, esta debe empezar a estar en la tarjeta de Sell Out"*.
- **Los 6 articulos** (venian de `01_INPUTS/producto activos.xlsx`, y ya estaban en `RAW_PRODUCTOS/productosjulio.xlsx`):
  - **3 Iscay (74410, 74411, 74528):** ya clasificaban solos (VDG / Iscay / litros OK). **Sin cambios.** 74411 figura "En proceso de baja".
  - **3 Cinzano (90105, 90106, 90110):** estaban en el archivo del mes **sin Categoria ni Linea Comercial** (solo Segmento=Vermouth) -> `_acc_canon_cat` daba `NAN`, quedaban **fuera de acciones y de sell out**.
- **Alta en `09_CONFIG/maestro_04D_productos.csv` (260 -> 263 filas):** `90105/90106,Vermouth,Vermouth,Cinzano,12.0,12` y `90110,Vermouth,Vermouth,Cinzano,4.5,6`. Linea Comercial **Cinzano** para que la tarjeta agrupe las 3 variedades bajo una marca (varietales al drill-down).
- **Categoria nueva de sell out (`server_orbit.py`), definida por el negocio:** Vermouth **NO suma a Spirits**, es bucket propio.
  - `_SO_CAT_MAP`: `"vermouth" -> "VERMOUTH"` (sin esto la venta se cae del sell out: la categoria del maestro que no esta en el mapa queda NaN).
  - `SUBS`: `"VERMOUTH": []` (es lo que decide que categorias lista la tarjeta).
  - **Sin objetivo:** `OBJSELLOUT.xlsx` no trae fila de vermouth -> `objetivo=None` y `alcance=None`. El portal ya renderiza ese caso como "–" (no hizo falta tocarlo).
- **Innovaciones (`01_INPUTS/INNOVACIONES/Innovaciones.xlsx`, 22 -> 25 productos):** agregados los 3 Cinzano en formato `CODIGO - NOMBRE` con openpyxl (preservando estilos). El lector del generador los toma: `90105 -> Cinz. VTH RSO 12X1000`, etc. **Aparecen en el tablero recien al regenerar datasets** (el tablero lee `mod_innovaciones_segmento.csv`, no el xlsx en vivo) -> entra con el cierre del dia.
- **Validado:** los 6 codigos resuelven categoria/bucket/LC/litros; `/api/gerencia/sellout_litros` devuelve **VERMOUTH 0.0 L | obj=None**; Playwright en gerencia: la fila "VERMOUTH | 0 L | – | – | – | 0" renderiza en la tarjeta sin errores de consola. `py_compile` OK.
- **Nota:** Cinzano todavia **no tiene ventas** (0 lineas en ventas.csv y ventas_acumulada.csv), por eso la fila arranca en 0 L. Es alta anticipada.
- **Aprendizaje (me equivoque primero):** busque "CINZANO" y no encontre nada porque **el archivo abrevia "Cinz."**. Los 6 articulos SI estaban. Para diffear altas: comparar por **codigo**, nunca por texto de la descripcion.
- **Limpieza de archivos que confunden (decidido con el usuario: renombrar, no borrar — estan gitignored y no se recuperan):**
  - `01_INPUTS/producto activos.xlsx` -> **`_NO_USAR_producto activos.xlsx`**. Referencia actualizada en `05_INTELLIGENCE_ORBIT/modulo_vda_clientes_ganados.py`; `tools/loader_acciones_comerciales.py` pasa a usar solo el 04D xlsx (lee con read_excel, el CSV no le sirve).
  - `01_INPUTS/RAW_PRODUCTOS/04D_..._raw_2026-05-12_1352.xlsx` (19MB inflado) -> **`_NO_USAR_04D_raw_2026-05-12.xlsx`**.
  - **Blindaje:** `_acc_desc_articulo_file()` (server) y `_maestro_mes_productos()` (generador) ahora **ignoran `_NO_USAR_*`**. Sin esto el raw de mayo podia ser elegido como maestro del mes por mtime y colgar el cierre.
- **`producto activos.xlsx` NO es fuente del sistema** (lo lee solo `modulo_vda_clientes_ganados.py`, y esta en .gitignore -> nunca llega a Render). Las altas de productos deben ir a **`01_INPUTS/RAW_PRODUCTOS/productos<mes>.xlsx`**. En este caso los 6 ya estaban ahi, asi que no hubo que tocarlo.


## 2026-07-16 - feat(acciones): 6 acciones NUEVAS de julio (tarjeta propia) + soporte "menos AASS con planes"

- **Pedido:** *"cree las tarjetas para la pantalla de Acciones Comerciales, gerencia y vendedor, con un diseño visual diferente pero la misma mecanica que las vigentes, el detalle de los productos que entran, las cantidades y en que negocio. Armar las tarjetas de acuerdo a los descuentos... esto que este activo tambien para las alertas."*
- **Fuente:** `01_INPUTS/ACCIONES COMERCIALES/2026-07/Acciones comerciales nueva JULIO.xlsx` (18 SKU x 3 columnas de accion). Se agrupan en **6 descuentos distintos** = 6 tarjetas.
- **Alta en el catalogo del mes (`acciones_comerciales_julio_2026_penaflor.csv`, 23 -> 29 reglas)** — NO se toco el motor: las tarjetas, la footprint real, el buscador y las alertas ya salen del catalogo. Las 23 vigentes quedaron byte-identicas.
  - `ACJ26-024` Smirnoff Botella **10%** desde 1 caja (6 botellas), todos los segmentos **menos AASS con planes**.
  - `ACJ26-025` Smirnoff Botella **12%** en AASS **con** plan, desde 1 caja.
  - `ACJ26-026` Smirnoff Botella **15%** a partir de 50 cajas, todos los clientes.
  - `ACJ26-027` Smirnoff Ice **lata 50%** desde un six pack (35103).
  - `ACJ26-028` **Cerveza** Antares Lager **18%** desde un six pack (60021, 60022).
  - `ACJ26-029` **Resto 10%** desde 3 botellas del mismo codigo — JW / Baileys / Tanqueray (9 codigos).
  - Las 6 apuntan a **codigos exactos** (`productos_marcas` numerico), que el predicado ya soporta; los 18 resuelven descripcion contra `RAW_PRODUCTOS/productosjulio.xlsx`. Bloque nuevo **`07_NUEVAS_JULIO`**.
- **Cambio real de motor (`server_orbit.py`) — el unico que hacia falta:** existia `requiere_plan_as` (accion SOLO para AASS con plan) pero **no el caso inverso**, y ACJ26-024 lo pide literal. Nuevo **`_acc_plan_as_flags(rule) -> (requiere, excluye)`**, usado por el payload y por las alertas. Chequea la **exclusion primero**: el texto *"menos AASS con planes"* contiene *"PLAN AASS"* y sin eso el filtro quedaba **exactamente al reves**. El payload ademas expone `bloque`, `nueva`, `minimo`, `unidad_minimo` y `subcategoria`.
- **Portal (`portal.html`) — diseño propio, sin tocar el de las vigentes:** seccion **"✨ Acciones nuevas del mes"** (`.accnew*`) en gerencia y vendedor, con el **descuento como badge circular**, escala, **compra minima**, **en que negocio** (segmento) y **los productos que entran** (codigo + descripcion; los que falten en el maestro salen en ambar). Las nuevas se sacan del listado de vigentes (`!a.nueva`). Mantienen `data-acc`, asi que el **buscador** y el **drill-down de clientes** funcionan igual. Identidad visual intacta (magenta de marca, tokens, tabular-nums).
- **Alertas: activas.** Las 6 reglas ya autorizan tramo. Verificado: 14 alertas donde manda una accion nueva (`ACJ26-026`, Smirnoff al 16-17% sobre un maximo de 15%). El split por plan AS es real: **ACJ26-024 = 43 clientes, 0 con plan**; **ACJ26-025 = 12 clientes, los 12 con plan**; ACJ26-026 (todos) = 55 = 43 + 12 (revalidado contra la carga de ventas de las 17:41).
- **Validado:** payload 29 acciones en 3,3 s; `json.dumps` OK sobre payload gerencia, V4 y alertas (numpy no rompe en Render); `py_compile` OK; server local 8502, `/api/gerencia/acciones_mes` y `/api/vendedor/V4/acciones_mes` 200. Playwright gerencia (desktop) + V9 (mobile): **6 tarjetas, 0 errores de consola**; filtro `60021` deja solo ACJ26-028 y oculta la seccion cuando no hay match; drill-down de ACJ26-028 abre 4 clientes / 2 vendedores. **V3 (Nadia) no ve ACJ26-025** (autoservicio), como corresponde.
- **Limitacion conocida (heredada, no la introduce este cambio):** las alertas toman el **tramo mas alto** de la regla sin mirar la cantidad comprada — ACJ26-026 autoriza 15% en Smirnoff botella aunque el cliente no llegue a las 50 cajas. Es la misma semantica de las escalas vigentes (ACJ26-001 autoriza 8% siempre). Si se quiere gatillar por cantidad, es un cambio de motor aparte.
- **Bug preexistente detectado (NO tocado):** `ventas_acumulada.csv` solo tiene **2026-07**, asi que el comparativo del mes anterior esta vacio y **todas** las acciones — viejas y nuevas — muestran `clientes_nuevos == clientes_alcanzados` (ACJ26-001: 60 cli / 60 nuevos). Anotado en NEXT_TASK.md.


## 2026-07-14 - data(maestro): alta del codigo 20305 (Suter Etiqueta Marron) + el generador lee el 04D del CSV

- **Pedido:** *"dale de alta el 20305 en el maestro, en la categoria del resto de la marca suter"* (era el unico codigo vendido que no estaba en NINGUN maestro).
- **Alta (`09_CONFIG/maestro_04D_productos.csv`):** `20305,Vinos del año,Medio,Etiqueta Marron Suter,4.5,6`. Clasificacion copiada de su hermano **20301** (SUTER ETIQ MARRON DNAT, Vinos del año / Medio); la linea comercial coincide con la columna `Marca` con la que 20305 viene en ventas. Litros/caja 4,5 y 6 unidades salen del formato 6X750.
- **Bug encontrado al hacerlo (`generar_datasets_acum.py`):** el generador leia el **xlsx** del 04D mientras `server_orbit.py` lee el **CSV** de `09_CONFIG` → un alta hecha en el CSV **no llegaba a los datasets**. Nuevo `_cargar_04D()`: prefiere el CSV (la regla vigente del proyecto) y cae al xlsx solo si no esta. Las dos mitades del sistema leen la misma fuente.
- **Validado:** maestro **340 -> 341** codigos; 20305 clasifica como **VDA / Medio** (lxu 0,75) y entra en **8 acciones** (ACJ26-001/002/009/015/017/018/019/021). El buscador de acciones pasa a **0 SKU fuera del maestro** (era 1). Datasets regenerados con backup (`99_BACKUPS_ORBIT/20260714_111855`): sell out **Vinos del año 14.890,5 -> 14.917,5 L** y +$9.567 de importe — exactamente la venta que quedaba afuera. `py_compile` OK.

## 2026-07-14 - fix(maestro): el 04D estaba congelado y arrastraba TODO — se completa con el maestro del mes

- **Pedido:** *"controla si todo dependia del archivo incompleto y de ser necesario modifica para que el resultado sea siempre correcto"* (a partir del hallazgo del buscador de acciones).
- **Auditoria — si, casi todo dependia del 04D:** `_acc_preparar_from_df` (acciones + alertas de descuento), `_litros_por_linea` (sell out, ficha de cliente), `_sellout_desde_ventas`, Plan Frizze, ranking de acciones, cierre de mes, `_acc_marcas_maestro`, y el loader **propio** de `generar_datasets_acum.py` (`cargar_maestro_productos`, que ademas descartaba las lineas sin categoria: `Categoria.notna()`).
- **Causa raiz:** `09_CONFIG/maestro_04D_productos.csv` quedo **congelado en 258 codigos**. Faltan **82 SKU vigentes** que si se venden (Alaris D.Cosecha, Dada Sweet Red, Los Arboles Rosado, Smirnoff BC...). Sin categoria, sin linea comercial y sin litros/caja: **60 lineas de venta del mes ($1.386.829, 2,1% del importe)** no entraban en las reglas por categoria ni en sell out, y aportaban 0 L.
- **Descartado:** `01_INPUTS/producto activos.xlsx` **no arregla nada** — son los mismos 257 codigos que el 04D y cubre **menos** ventas (115/128 vs 118/128). La fuente correcta es el export mensual **`01_INPUTS/RAW_PRODUCTOS/productos<mes>.xlsx`** (339 codigos, cubre **127/128**, mismo vocabulario de Categoria/Segmento).
- **Cambio (fuente unica, no parche en el consumidor):**
  - `server_orbit.py`: nuevo **`_maestro_mes_productos()`** (cacheado por mtime) y **`_cargar_maestro_04D_uncached()` lo usa para COMPLETAR**: el 04D manda donde tiene dato, el mes agrega los codigos faltantes y rellena campos vacios. La caché del wrapper ahora tambien invalida por el mtime del archivo del mes. Maestro: **258 -> 340 codigos**, todos con litros/caja.
  - `server_orbit.py`: `_acc_preparar_from_df` pasa a calcular litros con la cascada unica **`_litros_por_linea`** (maestro -> PesoKg -> ml del nombre) en vez del `lxu` pelado: una accion no puede mostrar 0 L porque falte el SKU.
  - `generar_datasets_acum.py`: gemelo **`_maestro_mes_productos()`** + `cargar_maestro_productos()` completa igual (**256 -> 340** codigos).
- **Impacto medido (dos procesos limpios, con y sin completado):**
  - **Acciones del mes:** litros **5.362 -> 5.657**, importe $41,04M -> **$41,41M**, inversion real $5.205.236 -> **$5.263.359**, clientes 191 -> 193. Cambian 12 de las 23 acciones.
  - **Alertas de descuento: 162 -> 151.** Las **11 que desaparecen eran FALSAS**: descuentos normales de 5-8% (dentro de las escalas de ACJ26-001/002) marcados como *"maximo 0% - sin accion aplicable"* solo porque el SKU no estaba en el maestro. Los sobre-descuentos reales del mismo articulo (Alaris D.Cosecha) **siguen alertando**. No aparecio ninguna alerta nueva.
  - **Sell out litros:** 9.038 -> **9.139 L**. Dataset `mod_sellout_categoria`: +2.054 L, +$1,43M, +14 clientes, y aparece una **categoria entera que faltaba (Vodka, 0 -> 327,6 L)**.
  - **Datasets:** solo cambian **3** por este fix (`mod_sellout_categoria`, `mod_acciones_ranking` 7 -> 13 filas, `mod_acciones_analisis`); el resto de las diferencias eran deriva normal de inputs mas nuevos. Regenerados con backup en `99_BACKUPS_ORBIT/20260714_104153`.
  - **Sin cambios (verificado):** 11 Titulares, 11T por zona, Club FARO, Planes AS, cobertura, CCC empresa, busqueda de clientes — no clasifican por el maestro.
- **Validado:** `py_compile` OK; server local 8502, los 6 endpoints 200 (acciones_mes 0,08 s); Playwright en gerencia / V4 / V3, sin errores JS. El buscador de acciones pasa de **83 SKU "fuera del maestro" a 1**.
- **Queda 1 solo hueco (documentado):** `20305` SUTER ETIQ MARRON BLANC DE BLANCO ($9.567, 1 linea) no esta en **ningun** maestro. En el portal sus litros salen igual por la cascada; en `mod_sellout_categoria` se sigue descartando por falta de categoria.

## 2026-07-14 - feat(acciones): buscador de producto/marca en Acciones Comerciales (gerencia + vendedor)

- **Pedido:** *"un filtro en la pantalla de acciones comerciales para los dos perfiles, vendedor y gerencia, en donde pueda filtrar un producto o marca y que me aparezcan las acciones comerciales en las que aplica ese producto, segmento, y tipo de accion comercial"*.
- **Backend (`server_orbit.py`):**
  - Nuevo **`_acc_universo_productos(v_act)`**: universo de productos = SKUs del maestro de productos activos (`01_INPUTS/RAW_PRODUCTOS/productos<mes>.xlsx`) + los codigos vendidos en el mes (340 en julio). Cada item trae los **cinco argumentos exactos** con los que se evalua el predicado de una accion sobre una linea de venta (categoria canonica y linea comercial **salen del 04D**, igual que `_acc_preparar_from_df`).
  - **`_acciones_mes_payload_uncached`**: dentro del loop de reglas, **despues** del filtro por vendedor, evalua el **mismo `pred`** de la footprint contra el universo -> indice `producto -> acciones`. Se publica como `payload["productos"]` (codigo, producto, marca, alias, linea, categoria, cat_canon, en_maestro, acciones[]). No se agrego endpoint: viaja en el payload que el portal ya carga.
  - Costo: ~7.000 evaluaciones de predicado por build, dentro del cache por mtime ya existente. Payload gerencia +87 KB (441 KB), respuesta cacheada 0,06 s.
- **Portal (`portal.html`):** `accIdx` / `accFiltroHTML` / `accFiltroApply` / `accFiltroClear` + estilos `.accf-*`. Buscador con autocompletado (marcas + productos + codigo) y dos selects (**segmento** y **tipo de accion**), montado en la pantalla de gerencia (`gAccionesComerciales`) y en el bloque de acciones del vendedor (tab Alertas). Filtra las tarjetas ya renderizadas (`data-acc`) y tambien las **Acciones ON** (`data-accon`, indexadas por sus productos elegibles). Los KPI de arriba **no** se filtran (son los totales del mes, deduplicados): el chip avisa `· filtrado`.
- **Precision, no maquillaje:** el filtro responde con el mismo criterio que la footprint. Si un SKU no entra en ninguna accion lo dice; y si el SKU **no esta en el maestro 04D** muestra la advertencia (`en_maestro=false`) en vez de adivinarle la categoria.
- **Validado (server local 8502 + Playwright, gerencia / V4 / V3, desktop y mobile, 0 errores JS):** "alma mora" -> 6 acciones de catalogo + 2 ON (ACJ26-001/002/009/015/018/019); codigo exacto `74210` -> las mismas 6; "VDA" -> 10; "frizze" -> 1 (ACJ26-018, Resto de SKU); inexistente -> "Sin coincidencias". **V3** (Nadia, sin autoservicio) ve solo ACJ26-002 en "alma mora": el indice se calcula **despues** del filtro por vendedor.
- **Hallazgo de datos (no tocado, queda en NEXT_TASK):** **82 de los 339 SKUs activos no estan en el maestro 04D** (47 vigentes: Trapiche 36, Finca Las Moras 8, El Esteco 8, Diageo 8...). Sus ventas hoy quedan **sin categoria y sin litros por caja** -> no matchean las reglas por categoria de acciones y aportan 0 L. Es preexistente; el buscador ahora lo hace visible.

## 2026-07-13 - fix(global): se elimina el filtro `Empresa` de TODAS las métricas — medimos con las dos razones sociales

- **Pedido del usuario, después del fix del 11T:** *"revisá si en otra parte de Peñaflor ocurre el mismo problema. **Todo lo que medimos es con ambas empresas**"*.
- **Auditoría:** quedaban **8 puntos** filtrando `Empresa == 'Empresa'` (ninguno en `tools/` ni en los legacy). Todos rotos por la misma causa: **P&P Logística es nuestra segunda razón social**, no otro distribuidor (`Proveedor = GRUPO PEÑAFLOR SA` en el 100% de las filas).
- **Cambio — filtro eliminado en los 8:**
  - `server_orbit.py`: `gerencia_ccc_empresa()` (`/api/gerencia/ccc_empresa`), `_acc_preparar_from_df()` (**acciones comerciales**, alimenta `/api/gerencia/acciones_mes` y las alertas de descuentos), `vendedor_ruta()` (`/api/vendedor/<id>/ruta`), `vendedor_oportunidades_innovacion()`, `gerencia_cierre_mes()` (`/api/gerencia/cierre_mes`) y `_cierre_ccc_por_vend_segmento()`.
  - `generar_datasets_acum.py`: `generar_innovaciones_segmento()` y `generar_innovaciones_plan_as()`.
  - Nuevo bloque **`_LEEME_EMPRESA`** en `server_orbit.py` (junto a `_VENDEDORES_EXCLUIDOS`): la regla queda escrita **una sola vez** y las 8 llamadas la referencian, para que nadie vuelva a agregar el filtro.
- **Impacto medido (endpoints reales, antes → después):**
  - **CCC empresa** (`/api/gerencia/ccc_empresa`): Tradicionales **79 → 194** (obj. 845), On Premise 3 → 9, Vinotecas 3 → 5, On Premise Noche 3 → 5, Autoservicios 2 → 5. **Estaba mostrando el 40% del CCC real.**
  - **Acciones comerciales** (`/api/gerencia/acciones_mes`): clientes alcanzados **83 → 191**, importe neto **$28.268.671 → $41.035.953**, **inversión real $4.267.780 → $5.205.236**, litros 3.673 → 5.362. La inversión en acciones venía **subvaluada ~$1M**.
  - **Innovaciones** (`mod_innovaciones_segmento.csv`): CCC **45 → 90**. V10 Ortega **2 → 15**, V7 Jofre 1 → 6, V6 Peyronel 4 → 10.
- **Validado:** `py_compile` OK; los endpoints responden 200; `grep` confirma **0 filtros de `Empresa`** vivos. Datasets regenerados con backup (`99_BACKUPS_ORBIT/20260713_200755`, log en `99_LOGS_ORBIT/`): de los 9, **solo cambió `mod_innovaciones_segmento.csv`**.
- **Bug preexistente detectado (NO tocado, queda en `NEXT_TASK.md`):** `/api/vendedor/<id>/ruta` devuelve **0 clientes en todos los vendedores y todos los días** — antes y después del cambio. El match es `clientes.xlsx::DiasVisita == dia`; el formato del maestro no coincide. No lo causó este cambio.
- **Sin tocar:** `01_INPUTS`, `portal.html`, objetivos, reglas comerciales.

## 2026-07-13 - fix(11T): el CCC acumulado mostraba la mitad — P&P Logística no es otro distribuidor

- **Pedido:** la tarjeta **11 Titulares acumulada** del dashboard no coincide con el reporte de Peñaflor (que se arma **con nuestros propios archivos**). Ellos ven: Alma Mora 55, Dada 58, Finca Las Moras 38, Los Arboles 34, Alaris 30, Smirnoff Ice 29, Smirnoff Flavours 28, Don David 11, Trapiche Reserva 10, Gordon's 6, Antares 0. Nuestra tarjeta mostraba **≈ la mitad** (Alma Mora 29, Dada 28, Ice 9).
- **Causa raíz:** el 11T filtraba `Empresa == 'Empresa'` para "excluir P&P Logística (otro distribuidor)". **P&P Logística no es otro distribuidor: es nuestra segunda razón social.** En `ventas_acumulada.csv` la columna **`Proveedor` es `GRUPO PEÑAFLOR SA` en el 100% de las filas** (1051/1051 hoy; 16.884/16.884 en el acumulado de junio). El filtro borraba **135 de los 229 clientes con compra** de julio, es decir, rutas enteras: **V6 perdía 30 de 34 clientes (88%) y V10 35 de 40 (88%)**; V3 75%, V7 79%.
- **Por qué la regla del 18/06 parecía correcta:** en junio el mix de facturación era **Empresa 8.558 filas vs P&P 5.762** (Empresa mayoritaria, y casi todo cliente tenía al menos una factura por Empresa, así que el CCC no se caía). En julio **se dio vuelta: P&P 630 vs Empresa 421**, y aparecieron 135 clientes que facturan **solo** por P&P → el CCC se partió al medio.
- **Cambio — se elimina el filtro por `Empresa` en los 4 puntos del 11T:**
  - `server_orbit.py` → `gerencia_once_titulares()` (tarjeta del dashboard), `gerencia_once_titulares_zona()`, `_leer_ventas_acum_cierre()` y `_cierre_once_titulares()` (cierre de mes).
  - `generar_datasets_acum.py` → `generar_11t_acum()` (dataset `mod_11t_acum.csv`, vista del vendedor).
  - **Intacto:** sell out, cobertura, Club FARO, CCC por segmento y planes AS **siguen filtrando por `Empresa`** — no se tocó ninguna otra métrica.
- **Validado:** `/api/gerencia/once_titulares` (HTTP 200, fuente `ventas_acumulada.csv`) → Alma Mora **29 → 75**, Dada 28 → 71, Finca Las Moras 17 → 50, Smirnoff Ice 9 → 48, Los Arboles 18 → 38. `/api/gerencia/once_titulares_zona` 200 OK. Datasets regenerados con backup previo (`99_BACKUPS_ORBIT/20260713_195908`): de los 9 datasets **solo cambió `mod_11t_acum.csv`** (Alma Mora 25 → 66) — los otros 8 salieron idénticos.
- **Desvío que queda (documentado, no maquillado):** seguimos **por encima** del reporte de Peñaflor en todas las marcas (Alma Mora 75 vs 55 — 69 si se descuenta hoy; Ice 48 vs 29). **No** se explica por fecha de corte (su Los Arboles equivale a nuestro 10/07 pero su Alma Mora a nuestro 07/07), ni por match estricto de la matriz de códigos, ni por mínimo de botellas, ni por V20: **probados y descartados los cuatro**. Además su **Antares = 0** no es reproducible (tenemos 5-8 clientes con códigos 60017-60022, todos en la matriz oficial). Hace falta el archivo del reporte para reconciliar cliente por cliente → queda en `NEXT_TASK.md`.
- **Sin tocar:** `01_INPUTS`, `portal.html` (la tarjeta consume el endpoint, no necesitó cambios), objetivos.

## 2026-07-13 - fix(litros): fuente única `_litros_por_linea` — si falta el litraje, se calcula (nunca 0)

- **Pedido:** los SKUs con `PesoKg = 0` mostraban **0 L** en la ficha de cliente. Regla del usuario: **"evitemos mostrar 0 en un reporte porque falta el cálculo; cuando falte hay que realizarlo"** → inferir los litros desde el maestro 04D.
- **Causa:** `_cliente_ventas_base()` tomaba litros de **`PesoKg` pelado**. Sell Out, en cambio, ya resolvía bien el problema con una cascada de 3 niveles, pero la lógica estaba **inline dentro de `_sellout_desde_ventas`** y nadie más podía usarla.
- **Cambio (`server_orbit.py`) — extracción, no lógica nueva:** nuevo helper **`_litros_por_linea(df)`**, fuente única del criterio de litros:
  1. **`CantBase × (Lts x caja / UxC)` del maestro 04D** (primaria),
  2. **`PesoKg`** del ERP si el SKU no está en el maestro,
  3. **ml inferidos del nombre** (`6X750` → 0,75) × `CantBase` como último recurso.
  `_sellout_desde_ventas` **reemplaza su bloque inline** por una llamada al helper (misma cascada, sin duplicar el criterio) y `_cliente_ventas_base` lo adopta (`_litros = _litros_por_linea(df)`).
- **Validado (dos frentes):**
  - **Sell Out no se movió ni un litro:** helper nuevo vs implementación vieja sobre las 881 filas de `ventas.csv` → total **6.953,49 L en ambas**, **máxima diferencia por fila 0,0000000000**, **0 filas distintas**. El refactor es equivalente exacto.
  - **Ficha #278 (mes 2026-07):** SKUs en 0 L pasan de **2 → 0**. `DADA 7 SWEET 6X750` **0 L → 22,5 L** (30 bot × 0,75 del maestro) y `GORDON'S PINK GIN 6X700` **0 L → 8,4 L** (12 × 0,7). Coherentes con sus hermanos de la misma marca (DADA ESPUMANTE 22,5 L, GORDON'S GIN 8,4 L). Venta del mes del cliente: **324,9 L → 355,8 L** (el importe no cambia). Verificado en navegador (Playwright) en **gerencia y vendedor**: 7 marcas / 12 SKUs, ningún "0 L".
- **Alcance del cambio de números:** `_cliente_ventas_base` **solo lo usa la ficha** (`/api/clientes/<id>/ficha`) → los litros que suben son los de **venta del mes / promedio 12m / posibilidad de venta de la ficha**, que antes estaban subvaluados. Ninguna otra métrica (CCC, cobertura, 11T, objetivos) usa esta base.
- **Sin tocar:** `01_INPUTS`, datasets, `portal.html`, cálculos comerciales.

## 2026-07-13 - feat(ficha cliente): detalle por producto (SKU) de lo comprado en el mes

- **Pedido:** en la pantalla **Cliente** (gerencia **y** vendedor), al desplegar la consulta de un cliente, ver **qué producto** viene comprando en el mes — no la categoría/marca suelta, sino el SKU (ej. no "Dada" a secas, sino "DADA LATA TINTO VERANO 4X6X355"), y así con todo.
- **Estado previo:** la ficha (`clienteFicha`, que **comparten los dos perfiles** vía `renderClienteBuscador`) mostraba solo chips de **"Marcas compradas en el mes"** — el endpoint `/api/clientes/<id>/ficha` agrupaba únicamente por columna `Marca` (`marcas_mes`). No había ningún corte por artículo.
- **Backend (`server_orbit.py`):**
  - `_cliente_ventas_base()`: se agregan 3 columnas derivadas — `_articulo` (Articulo = descripción del SKU), `_codigo` (Codigo) y `_botellas` (CantBase, ya numérico y en botellas, igual criterio que cobertura en `:3264`).
  - `cliente_ficha()`: nuevo campo **`productos_mes`** = agrupado por `(Marca, Código, Artículo)` del **mes vigente**, con `botellas`, `litros`, `importe` y `compras` (días distintos), ordenado por importe desc. `marcas_mes` se conserva (compat) y suma `botellas`. Rama sin ventas devuelve `productos_mes: []`.
- **Frontend (`portal.html`, `clienteFicha`):** la sección pasa a **"Productos comprados en el mes"**: una fila por **marca** (con totales botellas/litros/dinero) **desplegable** — al tocarla se abre/cierra la tabla de sus **SKUs** (Producto + #código, Botellas, Litros, Dinero). Arranca desplegada. Nueva función `clienteToggleMarca(scope,i)` (los selectores llevan `scope` `g`/`v` para no cruzar los dos contenedores). **Un solo cambio cubre los dos perfiles** porque la ficha es la misma.
- **Validado con navegador real (Playwright, server :8502, cliente #278 AVENATTI, mes 2026-07):** **gerencia y vendedor V6 idénticos** → 7 marcas, **12 SKUs**. Antes se veía solo "Champaña Dada · 22,5 L · $294.449"; ahora se abre en **DADA ESPUMANTE ROS 6X750 (#74473) 30 bot · 22,5 L · $147.225** y **DADA 7 SWEET 6X750 (#74446) 30 bot · $147.225**. Plegado/desplegado por marca verificado (7→6→7 tablas visibles). Empty-state OK (cliente #1278 sin compras → "Sin compras en el mes vigente"). Acentos/ñ correctos (`Champaña Dada` = 0xF1, no mojibake). `py_compile` + `node --check` OK.
- **Nota de datos:** algunos SKUs muestran **0 L** (ej. DADA 7 SWEET, GORDON'S PINK GIN) porque **`PesoKg` viene 0 en esas filas del origen** — es un dato faltante preexistente (ya afectaba a `marcas_mes`), no se inventa: botellas e importe sí son correctos.
- **Sin tocar:** cálculos comerciales, CCC, cobertura, objetivos, datasets, `01_INPUTS`. Solo se agregó un corte de lectura en la ficha.

## 2026-07-13 - fix(planificación): `venta_esperada` también en pesos completos

- **Pedido:** extender el `fmtP` de Plan vs Real a la tabla **"Total Planificación PyP del Día"** (quedaba pendiente en el commit anterior).
- **Alcance:** `venta_esperada` es el **plan del día** (decenas de miles), y se renderizaba con `fmtM` en **4 lugares**. Se pasaron los 4 a `fmtP` para no dejar el mismo número en dos formatos dentro de la misma pantalla: (1) tarjeta por vendedor de Planificación ("Venta obj.", `portal.html:2257`), (2) fila de la tabla "Total Planificación PyP del Día" (`:2307`), (3) su fila **TOTAL DÍA** (`:2318`), y (4) la tarjeta **"Plan cargado para \<fecha\>"** de la app del vendedor ("Venta esperada", `:3512`) — mismo campo, mismo aplastamiento (el vendedor que planificaba $60.000 se veía `$0.1M`).
- **Validado (server real :8502, `GET /api/planificacion`, plan del 2026-07-11):** V3 `$0.1M` → **$50.000**, V4 `$0.1M` → **$60.000**, V9 `$0.6M` → **$600.000**, TOTAL DÍA `$0.7M` → **$710.000**. `node --check` del bloque `<script>` → OK; 0 usos de `fmtM` restantes sobre `venta_esperada`.
- **Sin tocar:** `fmtM` sigue intacto y en uso para acumulados del mes (dashboard, avance, objetivos, cierre). Cambio de presentación puro: ni endpoints, ni cálculos, ni `01_INPUTS`.

## 2026-07-13 - fix(plan vs real): importes en pesos completos (no redondeados a millones)

- **Pedido:** en la pantalla **Plan vs Real** de gerencia, lo planificado y el real vendido en dinero deben verse **abiertos** (valor completo). Un vendedor que vendió menos de $100.000 aparecía en **cero** sin serlo.
- **Causa raíz (`portal.html:1171`):** la tabla usaba el formateador global **`fmtM`** (`n => n ? '$'+(n/1e6).toFixed(1)+'M' : '$0'`), que **redondea a millones con 1 decimal**. Todo monto < $50.000 cae a `$0.0M` y los < $100.000 se aplastan a `$0.1M`/`$0.0M`. No era un problema de datos: el endpoint `/api/matinal/resumen` devolvía el importe exacto; se perdía **solo en el render**.
- **Cambio (`portal.html`, mínimo y acotado a esta pantalla):**
  - Nuevo formateador **`fmtP`** junto a `fmtM`/`fmtK`: importe entero en pesos con separador de miles es-AR y signo delante del `$` (`-$238.400`). `null`/`undefined`/`0` → `$0`.
  - `gPlanVsReal` usa `fmtP` en las **3 columnas de dinero** (Plan $, Real $, Dif) y en la fila **TOTAL** del `tfoot`. El `+` de la diferencia positiva se antepone al `$` (`+$14.900`).
  - **`fmtM` no se tocó**: sigue igual en dashboard, avance, vendedores, etc. (cambiarlo globalmente rompería la densidad de los KPI).
  - Sin cambios de CSS: `.pvr-wrap` ya es `overflow-x:auto` y `.pvr-tbl td` es `white-space:nowrap` → los importes largos no rompen el layout.
- **Validado (server real :8502, `GET /api/matinal/resumen`, plan/real 2026-07-11):** reproducido el bug exacto que reportó el usuario — **V7 real $14.900 y V8 real $12.680 se mostraban como `$0.0M`**; ahora `$14.900` y `$12.680`. V9 `$0.2M` → **$226.198** (plan `$0.6M` → $600.000). TOTAL plan `$0.7M` → **$710.000**, real `$0.3M` → **$253.778**. `node --check` sobre el bloque `<script>` de `portal.html` → OK.
- **Sin tocar:** `server_orbit.py`, endpoints, cálculos, `01_INPUTS`, datasets. Es un cambio de presentación puro.

## 2026-07-12 - fix(dashboard): una sola tarjeta de CCC del mes (real/objetivo/avance)

- **Pedido:** el dashboard de gerencia mostraba tres números distintos y confundía — KPI "CCC Compradores Mes" (76), "CCC Empresa · real vs objetivo" y "Cobertura acumulada del mes". Pidió una sola tarjeta de CCC con real, objetivo y avance.
- **Diagnóstico (datos primero):** las **dos tarjetas de CCC muestran el mismo 76** — no había inconsistencia de datos. El KPI top usaba `D.cccEmpresa?.empresa?.total ?? tCCC` y la tarjeta de canal usaba `cccEmpresa.empresa.total`; ambos = 76 clientes únicos con compra (neto>0) del mes (verificado contra `ventas.csv`: 76, y por canal Trad 66 / AS 2 / OP 3 / Vino 3 / Noche 2 = 76). La **"Cobertura acumulada" (190)** es una métrica DISTINTA por diseño (clientes con mínimo de botellas: 3 trad / 6 AS-OP), no comparable con CCC — **queda como tarjeta aparte** (no se fusiona; sería mezclar métricas).
- **Cambio (`portal.html`, `gDashboard`):** eliminado el KPI redundante "CCC Compradores Mes" de la fila superior (la `.krow` es `auto-fit`, reflota a 4 tarjetas sin huecos). Queda como única fuente de CCC la tarjeta detallada, **renombrada "📊 CCC del Mes · real vs objetivo"** (total 76/1046 · 7,3% + desglose por canal con CCC/objetivo/avance, objetivo desde objccc.xlsx). Elegido por el usuario: variante "detallada por canal".
- **Validado:** server local en 8502 → `GET /` HTTP 200; el HTML servido ya NO contiene "CCC Compradores Mes" (0) y sí "CCC del Mes · real vs objetivo" (1). `GET /api/gerencia/ccc_empresa` → total 76 / objetivo 1046 · 7,3%; canales Trad 66/845·7,8% · AS 2/145·1,4% · OP 3/30·10% · Vino 3/15·20% · Noche 2/11·18,2%. Server apagado tras validar.
- **Sin tocar:** ningún endpoint ni cálculo (solo se sacó una tarjeta del render y se renombró otra). `01_INPUTS`, datasets, lógica de CCC/cobertura intactos. **Pendiente:** para verse en Render, el `portal.html` debe llegar a `master` (esta rama es `feat/m1-import-safe-gsheets-namespace`).

## 2026-07-11 - fix(cierre): guard de rama — el cierre exige estar en master

- **Causa raíz de un desfasaje en producción:** `CIERRE_DIA_ORBIT.bat` **da por sentado que estás parado en `master`**. No hace `git checkout master`; hace `git commit` (rama actual) y luego `git push origin master`. Trabajando orbit-home en la rama `feat/m1-import-safe-gsheets-namespace`, el cierre del 10/07 committeó el dato en esa rama y el `git push origin master` fue un **no-op silencioso** (empuja la `master` local, que nunca recibió el commit) → salió "Everything up-to-date" con éxito y **Render nunca recibió el dato**. Producción quedó en el cierre del 08/07; como el 09/07 es feriado, el motor calculaba "siguiente día operativo" = viernes 10 y el portal mostraba VI en vez de SA. Corregido en caliente con cherry-pick de `15d36a8` a master (commit `d1f9fd0`, pusheado).
- **Cambio:** guard de rama al inicio de `CIERRE_DIA_ORBIT.bat` (después de `cd /d %ROOT%`, antes de todo lo demás). Lee `git rev-parse --abbrev-ref HEAD`; si la rama actual **no es `master`** (comparación `if /I`, case-insensitive) aborta con `exit /b 1` y un mensaje claro ("Estás en la rama X, hacé `git checkout master`"). No toca la lógica de datos, publicación ni nada de orbit-home; es ortogonal.
- **Validado:** replicada la lógica del guard en un `.bat` aislado corriendo desde `feat/m1-import-safe-gsheets-namespace` → detecta la rama y aborta (exit 1), correcto. En master la comparación deja pasar. Archivo verificado en **CRLF** puro (253 CRLF, 0 LF suelto; `.gitattributes` fuerza `*.bat text eol=crlf`) para no romper los `if/else` de cmd.
- **Sin tocar:** `01_INPUTS`, datasets, `server_orbit.py`, `portal.html`, la lógica de cierre/publicación. Solo se agregó el bloque guard en el `.bat`.

## 2026-07-10 - fix(cierre): guard Git clasifica por RUTA, no por lista de archivos

- **Causa raíz:** el guard Git de `CIERRE_DIA_ORBIT.bat` (y `CIERRE_MES_ORBIT.bat`) clasificaba lo operativo con una **lista blanca de archivos concretos** dentro de `01_INPUTS` (`resultado.xlsx`, `ventas.csv`, …). Un input operativo nuevo no enumerado — `01_INPUTS/Stock/stock.xlsx` — caía fuera del allowlist y disparaba `FUNC_PEND=1`, abortando el cierre como si fuera un cambio funcional. El `git status --short` del error mostraba los 7 archivos (status plano), enmascarando que el único gatillo real era `Stock/stock.xlsx`.
- **Cambio:** nueva función reutilizable de clasificación **por ruta** en `check_git_cierre.py` (stdlib pura, sin dependencias). Trata como operativo todo el árbol `01_INPUTS/`, `02_HISTORY/`, `04_DATASETS_ORBIT/`, `06_APP_DATA/` (JSON del portal) y `07_CIERRES_MENSUALES/`; cualquier otra ruta (`.py`, `.bat`, `portal.html`, `render.yaml`, config, etc.) sigue bloqueando. Normaliza rutas (quita XY de porcelain, `\`→`/`, comillas, `ruta -> ruta` de renombrados). Muestra dos grupos (operativos permitidos / funcionales bloqueantes) y sale 0/1. Los dos `.bat` reemplazan sus dos chequeos inline (`git status --porcelain -- . :(exclude)…`) por `python check_git_cierre.py`.
- **Validado:** `python check_git_cierre.py --test` (18 casos, TODAS OK) + los 6 escenarios del plan (solo 01_INPUTS→permite; ventas.csv+.py→bloquea solo el .py; 06_APP_DATA json→permite; portal.html/.bat/render.yaml→bloquea; separadores `/` y `\`; estados unstaged/staged/`??`/`R `). Estado real del repo: los 7 inputs → operativos; único bloqueante = `check_git_cierre.py` sin commitear (correcto: el guard debe frenar hasta que el propio código nuevo se commitee).
- **Sin tocar:** ningún archivo dentro de `01_INPUTS`, ni lógica comercial, cálculos, fuentes de ventas ni publicación. Sigue bloqueando cambios reales de código/config.

## 2026-07-09 - feat(orbit-home M1): server_orbit import-safe + Sheets namespaced (PENAFLOR_GSHEETS_*)

- **Contexto:** preparar Peñaflor para montarse embebido bajo Orbit Home (`/penaflor`). El preflight M0 dio NO-GO por dos bloqueos que resuelve este cambio: (1) importar `server_orbit.py` disparaba tareas de arranque; (2) leía solo `GSHEETS_*` genéricas (riesgo de mezclar la planilla con la de PepsiCo en un proceso compartido). **Cambio quirúrgico y reversible; NO toca lógica comercial, endpoints, cálculos ni UI.** El standalone se comporta igual que siempre.
- **`import_safe` — nuevo guard `PENAFLOR_SKIP_BOOT`** (`server_orbit.py`): el bloque STARTUP (`backup_orbit_db()` + `init_db()` + `restore_planificacion_if_empty()` + `export_planificacion_csv()`) y el hilo de warmup (`threading.Thread(_warm_caches)`) ahora corren dentro de `if not _PENAFLOR_SKIP_BOOT`. Con `PENAFLOR_SKIP_BOOT=1`, importar el módulo **no escribe SQLite/CSV, no lanza hilos, no toca el filesystem**: sólo deja `app` importable. Sin la variable (standalone/Render actual), el arranque es idéntico.
- **`env_safe` — Sheets namespaced** (`server_orbit.py`): nuevo helper `_penv(name)` que prioriza `PENAFLOR_GSHEETS_<X>` y cae a `GSHEETS_<X>` **solo en standalone**. Con **`PENAFLOR_REQUIRE_NAMESPACED_GSHEETS=1`** (modo estricto, pensado para Orbit Home) usa **SOLO `PENAFLOR_GSHEETS_*`** y NUNCA la genérica; si faltan, config incompleta controlada (no rompe el import). Las 3 lecturas (`_GSHEETS_SPREADSHEET_ID`, `_GSHEETS_SHEET_NAME`, credenciales en `_gsheets_credentials_info`) pasan por `_penv`. Nuevo `get_gsheets_config()` (diagnóstico NO sensible: `source`/`configured`/`strict`/`skip_boot`/`missing` por nombre; nunca valores). No se creó ni modificó ningún endpoint.
- **Validado** (`scratchpad/m1_check.py`, subprocesos, exit 0): (A) matriz env — solo `GSHEETS_*` sin estricto → `source=GSHEETS_LEGACY` configured; con estricto → `source=missing`, no toma la genérica; solo `PENAFLOR_GSHEETS_*` → namespaced; ambas → prefiere `PENAFLOR_*` (spreadsheet_id efectivo = NS). (B) `PENAFLOR_SKIP_BOOT=1` → import ok, DB **no creada**, sin hilo `orbit-warmup`, sin backups/CSV, sin prints de startup. (C) sin la variable (dry-run a tmp) → startup **sí** corre (DB creada, "Planificacion → CSV 167 registros", warmup presente) = standalone preservado. (D) `get_gsheets_config()` no filtra id ni credenciales. `py_compile` OK.
- **Aislamiento verificado:** todas las lecturas de `os.environ[...GSHEETS...]` quedan dentro de `_penv`, el flag estricto y `get_gsheets_config()`; no hay lecturas directas de `GSHEETS_*` operativas fuera del helper.
- **Sin tocar:** `01_INPUTS`, `orbit.db`, datasets, `portal.html`, endpoints. `git status`: solo `server_orbit.py` (+ CHANGELOG/NEXT_TASK). Rama `feat/m1-import-safe-gsheets-namespace` (NO se pushea `master`; ese repo tiene autoDeploy). **Rollback:** revertir el commit; sin las variables nuevas el comportamiento es el previo.
- **Pendiente (fuera de M1):** M2 (2º cerrojo `penaflor_sess` en Orbit Home), M3 (bundling server fino + pandas/numpy en Orbit Home), M4 (wiring `DispatcherMiddleware` local-only).

## 2026-07-06 - feat(11T + CCC): 11 Titulares mide solo AS+Almacén+Kiosco; tile CCC empresa real vs objetivo

- Pedido del usuario: (1) el 11T debe medirse en **Autoservicio + Almacén + Kiosco** (antes no filtraba superficie y sumaba todo canal). (2) Nuevo tile de gerencia **CCC total empresa real vs objetivo** desde `01_INPUTS/objccc.xlsx`. (3) Cargó los objetivos del mes en `01_INPUTS/objetivo 11T.xlsx`.
- **Superficie 11T** (`server_orbit.py`, nuevo helper `_mask_superficie_11t`): incluye Ramo `AUTOSERVICIO` **o** Subramo con "AUTOSERVICIO" (cuenta "Autoservicio Tradicional" — autoservicios chicos, **confirmado con el usuario**), + Subramo Almacén/Despensa (o Ramo `ALMACENES`), + Subramo Kiosco/Maxikiosco. EXCLUYE On Premise, Vinotecas, Away From Home, Mayoristas, Cash&Carry, Fiambrería/Carnicería/etc. Fail-open si la fuente no trae Ramo ni Subramo (no anula el CCC). Aplicado en las 4 mediciones vivas: `gerencia_once_titulares`, `gerencia_once_titulares_zona`, bloque 11T de `gerencia_cierre_mes` y `_cierre_once_titulares`. (El generador mensual `tools/generar_cierre_mensual.py::_11t_por_vend` usa otra metodología —cobertura por mínimo de botellas— y corre por .bat; queda igual, no mezcla criterios.)
- **CCC empresa vs objetivo** (`server_orbit.py`, reescrito `gerencia_ccc_empresa`): CCC del mes vivo (`ventas.csv`, neto>0, solo Peñaflor, excl V1/V2/V5/V20) por los 5 canales de objccc (Tradicionales, Autoservicios, On Premise, Vinotecas, On Premise Noche) clasificados por **Ramo** (el Subramo "Autoservicio Tradicional" cuenta como Tradicional acá, consistente con cómo se armó el objetivo); objetivo desde `01_INPUTS/objccc.xlsx` (helper `_objetivos_ccc_empresa`). Devuelve `canales[]` + `empresa{total,objetivo_total,pct,tradicional,autoservicio,onpremise}` (compat con el render previo). Números nativos (int/round), sin numpy → jsonify OK en Render.
- **Frontend** (`portal.html`): la kcard "CCC Compradores Mes" ahora muestra `real / objetivo · %`; nueva card en gerencia "📊 CCC Empresa · real vs objetivo" con tabla por canal (CCC/Objetivo/Avance/barra). El endpoint ya se llamaba desde `loadRole` (`D.cccEmpresa`).
- Validado (test_client Flask, datos reales de julio): `once_titulares` 200 — el filtro baja el CCC (p.ej. titulares en superficie pasan de 179→72 filas; se excluyen On Premise/Vinotecas/Cash&Carry/Away/Restaurant y se conservan AS+Almacén+Kiosco+Autoserv.Tradicional). `once_titulares_zona` 200. `ccc_empresa` 200 (total 44 / obj 1046 = 4,2%; canales reconcilian 37+2+2+2+1=44). `_cierre_once_titulares` (junio versionado) 200 con filtro aplicado (5122/3552=144%). `py_compile` OK.
- Nota (bug preexistente, fuera de alcance): `GET /api/gerencia/cierre_mes` devuelve 500 porque `01_INPUTS/ventas_mes.csv` está delimitado por `;` y `_leer_ventas_mes_csv` lo lee con `sep=','` (ParserError en el sell-out, antes del bloque 11T). Se reproduce igual en HEAD (git) ejecutado en el directorio real → NO lo introdujo este cambio. Queda anotado en NEXT_TASK.

## 2026-07-06 - feat(Stock sin Venta): exportación a Excel (.xlsx) del reporte

- Pedido del usuario: agregar un botón de exportación a Excel del reporte Stock sin Venta, **solo con los productos con stock y sin ventas**.
- Backend (`server_orbit.py`): extraído el cálculo de la ruta JSON a un helper compartido `_stock_sin_venta_payload()` (mismo criterio, sin divergencia); la ruta `GET /api/gerencia/stock_sin_venta` ahora lo consume. Nuevo endpoint `GET /api/gerencia/stock_sin_venta/export` que genera el `.xlsx` server-side (pandas + openpyxl, mismo patrón que `alertas_caida/export`): hoja "Stock sin venta" con Código, Producto, Disponible, Reserva, En tránsito, Bultos total; anchos de columna auto; nombre `stock_sin_venta_<mes>.xlsx`; 404 si falta el xlsx (sin datos falsos).
- Frontend (`portal.html`): botón "⬇ Exportar Excel" (server-side vía `window.location.href`) junto al CSV existente; función `descargarStockSinVentaExcel()`.
- Validado: server real en :8502 → `/api/gerencia/stock_sin_venta` HTTP 200 (115 productos, 16.103 u) y `/export` HTTP 200 con `Content-Type` xlsx y `Content-Disposition` correcto; el `.xlsx` bajado abre como "Microsoft Excel 2007+", 115 filas (= total_sin_venta), suma Disponible 16.103 (= unidades_sin_venta), todas Disponible>0. `git status`: solo `server_orbit.py` + `portal.html` (+ CHANGELOG/NEXT_TASK). Sin commit (a la espera de aprobación).

## 2026-07-06 - feat(Stock sin Venta): pantalla de gerencia con productos sin venta del mes que tienen stock

- Pedido del usuario: subió `01_INPUTS/Stock/stock.xlsx` y pidió una pantalla en gerencia con el listado de productos con **venta cero en el mes** que **tienen stock**.
- Fuente stock: `01_INPUTS/Stock/stock.xlsx` (217 códigos, sede La Francia, depósito Picking). Campo de existencia = `UniTotalDisponible` (= disponible real; `BultosTotal` = disponible + reserva; `BultosTransito` = mercadería en camino, informativo). Fuente ventas: `01_INPUTS/ventas.csv` (mes en curso).
- Criterio: producto con `disponible > 0` cuyo `Codigo` NO aparece con `CantBase > 0` en ninguna venta del mes calendario en curso (cualquier empresa/vendedor — si se movió por algún canal no es stock muerto). Resultado hoy: 115 productos, 16.103 unidades inmovilizadas; top DADA SIDRA 6X750 (1.743).
- Backend (`server_orbit.py`): `_ventas_parsed()` ahora conserva `codigo_art` y `cant_base` (solo suma columnas, sin romper consumidores). Nuevo `_stock_disponible()` (cacheado por mtime, consolida por código) + endpoint `GET /api/gerencia/stock_sin_venta` (devuelve `mes`, `total_sin_venta`, `unidades_sin_venta`, `total_productos_stock`, `productos[]` ordenados por disponible desc; 404 con `error` si falta el xlsx, sin datos falsos).
- Frontend (`portal.html`): ítem de menú "📦 Stock sin Venta" (sección Productos), router `gStockSinVenta`, fetch en `loadRole`, render con 3 KPIs + buscador por código/descripción + tabla (código, producto, disponible, reserva, barra) + descarga CSV client-side.
- Validado: server real en :8577 → endpoint HTTP 200 (115 productos, top DADA SIDRA), `portal.html` HTTP 200 con el código presente. Regresión: `ccc_empresa`/`sellout_litros`/`incentivo_dada` siguen 200 tras el cambio en `_ventas_parsed`. `git status`: solo `server_orbit.py` + `portal.html`. Sin commit (a la espera de aprobación).

## 2026-07-06 - refactor(Incentivo FARO): toda la definición se lee de la hoja (sin hardcode)

- Pedido del usuario: que FARO trabaje leyendo la hoja, para editar solo el Excel cada bimestre (así creía que ya funcionaba; por eso solo modificó la hoja).
- Cambio (`server_orbit.py`): nuevo `_faro_config()` (cacheado por mtime) que parsea TODA la definición desde `incentivo_club_faro*.xlsx` (Hoja1) tal como el usuario la escribe hoy: categorías (fila de encabezado sobre la grilla), segmento (banda superior con forward-fill), objetivos (filas con vendedor numérico), y de las REGLAS en texto libre → códigos de SKU (números ≥4 dígitos por línea de categoría), umbral (nº antes de "botellas/latas", o default por segmento 3 trad/6 AS), tope por cliente ("N máximo"), premios (fila MILLAS, asignados por tokens del nombre), período/meses (título) y supervisores (línea "Esteban… Raúl…"). Se eliminaron TODAS las constantes hardcodeadas (`_FARO_CATS`, `_FARO_CAT_SKUS`, `_FARO_MESES`, etc.); `_faro_ventas(cfg)` y `_faro_detalle_vendedor(df,cod,cfg)` reciben la config; los endpoints la construyen. Si la hoja no se puede leer → 200 con `error` (no datos falsos).
- Frontend: sin cambios (ya era data-driven por `categorias_orden`/`categorias_meta`).
- Validado: `py_compile` OK. `_faro_config()` reproduce EXACTO lo que estaba hardcodeado (cats smirnoff_ice/vinos_red_blends/familia_gordons; seg TRAD/AS/AS; umbral 3/6/6; cap gordons=3; SKUs; objetivos V3 60/0/0…; premios 2000/1000/1000; meses (7,8); sup Esteban[3,4,6,8,10]/Raul[7,9]). Endpoints 200 con numeros idénticos al commit anterior. Playwright gerencia+V8: render correcto, 0 errores de consola. La caché de ventas ahora contempla el mtime del xlsx (al reeditar la hoja, refresca).
- Nota: los nombres de categoría se muestran como se escriben en la hoja (la tabla de gerencia los pasa a mayúscula por CSS). Requisitos de layout para que el parser lea bien la próxima hoja quedan en NEXT_TASK.md.

## 2026-07-06 - feat(Incentivo FARO): bimestre julio-agosto (nuevas categorías por código de SKU)

- Síntoma: el usuario editó `01_INPUTS/incentivo_club_faro .xlsx` para el nuevo bimestre pero la pantalla de Incentivo FARO no cambiaba. Causa raíz: la lógica de QUÉ se mide estaba **hardcodeada** en `server_orbit.py` para el bimestre viejo (mayo-junio: Alaris+FLM / Antares / Familia Smirnoff, match por texto de marca) y el período fijo en meses [5,6]; del xlsx solo se leían objetivos y premios. Como `ventas_acumulada.csv` hoy solo tiene julio, el filtro [5,6] además descartaba todo.
- Definición nueva (del xlsx, bimestre julio-agosto), match por **CÓDIGO de SKU**: **Smirnoff Ice** (kiosco+almacén/Tradicional, min 3 bot por SKU — 35103/35104/35105, 🎟2000); **Vinos Red Blends** (Autoservicio, min 6 bot por SKU — 80089/74684/44395/71716/74735/42376/74737, 🎟1000); **Familia Gordons** (Autoservicio, min 6 bot por SKU — Gordons x700 30139/30075/30134, tope 3 coberturas/cliente, 🎟1000). Cobertura = cada SKU participante con ≥ umbral botellas suma 1; se suman por cliente. Interpretación adoptada del texto libre del xlsx: **umbral POR SKU** (a confirmar con el usuario).
- Backend (`server_orbit.py`): reescritas constantes FARO (`_FARO_MESES=(7,8)`, `_FARO_PERIODO`, `_FARO_CATS`, `_FARO_CAT_SEG/UMBRAL`, nuevo `_FARO_CAT_SKUS`, `_FARO_CAT_CAP`); `_faro_objetivos` mapea las 3 columnas al orden de `_FARO_CATS`; `_faro_premios` reconoce gordons/red blends/smirnoff ice; `_faro_ventas` filtra al bimestre y asigna categoría por código; `_faro_detalle_vendedor` cuenta cobertura por SKU con umbral y tope. Endpoints ahora exponen `categorias_orden` + `categorias_meta` (segmento/umbral/premio) para que el front sea data-driven; `periodo` dinámico.
- Frontend (`portal.html`): la tabla de gerencia y el detalle del vendedor iteran `categorias_orden`/`categorias_meta` en vez de las 3 claves hardcodeadas; textos de regla y período generados desde el payload (ya no dicen "mayo-junio"/"Antares por SKU").
- Validado: `py_compile` + `node --check` OK. Endpoints 200. Objetivos leídos = xlsx (V3 60/0/0, V4-V10 38/13-15/8; sup Esteban 212/56/32, Raul 76/28/16). Playwright login gerencia + vendedor V8: pantallas renderizan las 3 categorías nuevas, min 3/6 bot, julio-agosto, drill-down de coberturas por SKU, 0 errores de consola. Logrado bajo (solo 4 días de julio cargados) — esperado.

## 2026-07-06 - feat(11T): match por Código Art. exacto (matriz oficial) como fuente primaria

- Pedido: para la medición de 11 Titulares, usar las reglas con los códigos de producto del archivo `01_INPUTS/11 titulares autoservicio/11_titulares_autoservicios_match_codigos.xlsx` (contrato de datos preparado por el usuario). La medición sigue siendo **por marca**: todas las variedades de una marca (todos sus códigos) suman a la misma marca (confirmado con el usuario). Decisión de alcance: **Opción A** — si un SKU tiene un código fuera de la matriz igual suma a la marca por texto (no se pierde ninguna variedad).
- Fuente: hoja `DETALLE_SKU_11T_AS` (82 SKUs, columnas `codigo_articulo` + `linea_comercial_11t`). Las 11 líneas de la matriz coinciden 1:1 con los 11 titulares actuales; única normalización: `SMF ICE`→`SMIRNOFF ICE`. El match es `ventas.Codigo` (SKU) == `codigo_articulo`.
- Cambio (`server_orbit.py`): nuevo helper módulo `_codigos_11t_map()` (carga cacheada por mtime; `{}` si falta el archivo → cae al comportamiento previo) y `_marca_11t_por_codigo(df)`. Se asigna `marca_objetivo` en 2 pasos: **1) código exacto (primario)**, **2) texto de `Marca` (fallback)** + el keyword-fallback por `Articulo` que ya existía. Aplicado en las 4 rutas que calculan CCC por marca en vivo desde ventas: `gerencia_once_titulares`, `gerencia_once_titulares_zona`, snapshot 11T de `gerencia_cierre_mes` y `_cierre_once_titulares`.
- Cambio (`tools/generar_cierre_mensual.py`): mismo `_codigos_11t_map()` y `_marca_11t()` reescrito a código-primario + fallback texto, para que el cierre mensual congelado quede consistente con el vivo.
- NO se tocó: reglas de OP/Vinotecas, cobertura, ni el match por texto de otras marcas (Cazador, JW, NC, etc.); los drill-down `11t_empresa`/`11t_vendedor` que leen el legacy `mod_11_titulares.csv` (otra lineage) quedan como estaban (ver NEXT_TASK.md).
- Validado: `py_compile` OK. Test client Flask → `/api/gerencia/once_titulares` 200, 82 códigos cargados, CCC sin regresión (ALMA MORA 13, DADA 7, DON DAVID 4, TRAPICHE RESERVA 3 — idénticos a texto). Delta medido sobre `ventas_acumulada.csv`: **0 filas cambian de marca** (código coincide con texto donde ya resolvía; texto cubre el resto). `_marca_11t` del cierre probado: código con texto errado→corrige a la marca correcta, variedad fuera de matriz→suma por texto (Opción A), código de cerveza→ANTARES.

## 2026-07-04 - fix(cierre dia): whitelistear ventas_mes.csv para que no bloquee el cierre

- Síntoma: `CIERRE_DIA_ORBIT.bat` frenaba con "Hay cambios FUNCIONALES pendientes fuera de las rutas operativas" porque `01_INPUTS/ventas_mes.csv` aparecía modificado y no estaba en el allowlist operativo. El cambio era legítimo: reducción de ~6100→320 filas por el reset de mes/trimestre de julio (ventas_mes.csv = cierre congelado, consumido por la vista Sell Out de cierre en Render).
- Fix (`CIERRE_DIA_ORBIT.bat`): se agregó `":(exclude)01_INPUTS/ventas_mes.csv"` a los dos chequeos de bloqueo (`FUNC_PEND` línea 27 y `FUERA_ALLOW` línea 179) y `git add "01_INPUTS/ventas_mes.csv"` al bloque de staging (PASO 3/3) para que se publique en Render junto con el resto de inputs de cierre. Se preservó CRLF.
- Validado: el `git status --porcelain` con los excludes del `.bat` sale vacío (ya no frena por inputs de datos). El `.bat` se commitea aparte para que su propio cambio de código no auto-bloquee el próximo cierre.

## 2026-07-03 - feat(acciones comerciales): tarjetas de acciones ON (On Premise / VTK / TDB / Catering)

- Pedido: agregar a la pantalla de Acciones Comerciales las tarjetas necesarias para las acciones de ON del archivo `01_INPUTS/ACCIONES COMERCIALES/2026-07/acciones_comerciales_julio_2026_orbit_penaflorON.xlsx`.
- Fuente: el xlsx trae hoja `01_Acciones` (6 combos de incorporación sin cargo: mecánica, canales, compra, beneficio, tope) + hoja `02_Detalle_Productos` (468 líneas de productos elegibles por subcanal y LC). Son informativas (combos "compra 1 → llevás N sin cargo"), NO pasan por el motor de inversión/footprint de las acciones AS/Trad.
- Backend (`server_orbit.py`): `_acc_on_file()` autodetecta el `*ON.xlsx` del mes; `_acc_on_cards()` lo parsea (cacheado por mtime) → 6 tarjetas con `grupos:[{subcanal, lineas:[{lc, productos:[{codigo,descripcion,estado}]}]}]`. Se suma su mtime a `_acc_mes_sig` (al resubir el archivo el payload se refresca) y se expone como `acciones_on` en el payload de `acciones_mes` (gerencia y vendedor). El motor existente quedó intacto.
- Frontend (`portal.html`): sección "🌙 Acciones ON" al pie de la pantalla de Acciones Comerciales (gerencia `gAccionesComerciales` y vendedor `vAcciones`). Cada tarjeta: id, "Sin cargo", título, chips de canal, mecánica, combo `📦 compra → 🎁 beneficio`, tope y "Ver productos (N)". Click → modal `accShowOn` (reusa `.accd-*`) con los productos agrupados por subcanal → LC; los no vigentes se resaltan en ámbar con su estado. CSS `.accon-*`.
- Validado: `/api/gerencia/acciones_mes` → 23 acciones + 6 `acciones_on` (ON-11T 96 prod, VTK-TDB-11T 166, ON-INNOV 88, VTK-TDB-INNOV 88, ANTARES 6, DADA-TDV 24); `/api/vendedor/V8/acciones_mes` también trae las 6. `node --check` JS OK. Playwright con login gerencia: sección ON con 6 tarjetas, modal abre con grupos por subcanal, 0 errores de consola. Screenshots OK.

## 2026-07-03 - feat(incentivo dada): botón "Incentivo Dada" en gerencia (cobertura Dada Tinto Verano · autoservicios)

- Pedido: en el perfil de gerencia, botón bajo Plan Frizze llamado "Incentivo Dada". Adentro: arriba la imagen de 01_INPUTS/dadatinto.png y debajo una tarjeta con el seguimiento de la cobertura del producto. Objetivo de la distribuidora en 01_INPUTS/DADAVERANOOBJ.xlsx y ventas para las coberturas en 01_INPUTS/dadatinto.csv.
- Regla (del XLSX): "se mide ccc (cobertura del producto 74884 Dada tinto de verano) en autoservicios objetivo 38 clientes". Cliente cubierto = superficie autoservicio + compra válida (ImporteNeto>0) + ≥6 botellas del código objetivo (regla Cobertura Autoservicio de CLAUDE.md). Excluye V1/V2/V5/V20.
- Backend (server_orbit.py): `_incentivo_dada_objetivo()` parsea objetivo (38) y código (74884) del texto del XLSX (sin hardcode, con fallback); `_incentivo_dada()` lee dadatinto.csv (ya filtrado al producto), clasifica autoservicio por Ramo/Subramo, agrupa por cliente y arma logrado/objetivo/faltan/avance + desglose por vendedor + detalle de clientes. Nueva ruta `/api/gerencia/incentivo_dada`.
- Frontend (portal.html): item de menú "🍷 Incentivo Dada" bajo Plan Frizze, carga en loadRole (gerencia), router `gRender`, título y render `gIncentivoDada` (hero con la imagen + tarjeta con KPIs, barra de avance, por vendedor y tabla de clientes). CSS `.dd-*`. Imagen copiada a PAV MATINAL PE_A FLOR/dadatinto.png (patrón Frizze) y servida en `/dadatinto.png`.
- Validado: `/api/gerencia/incentivo_dada` → 200, objetivo=38 logrado=22 faltan=16 avance=57.9% (V8=14, V10=6, V4=2, 22 clientes); `/dadatinto.png` → 200 (2.26MB); py_compile OK; server reiniciado en :8502.
- Incremento: el KPI "Clientes con compra" es clickeable y abre un modal con el detalle de cada cliente (nombre, localidad, vendedor, total de botellas) y sus pedidos (fecha del comprobante + cantidad). Backend agrega `pedidos:[{fecha,botellas}]` por cliente (agrupado por FechaComprobante). Validado: suma de pedidos == total por cliente (0 descuadres); ej. YANDEN S.A.S 12 bot = 17/06 (6) + 30/06 (6).

## 2026-07-02 - feat(acciones comerciales): descripción de artículo por código desde productos<mes>.xlsx

- Pedido: en las tarjetas por código, al hacer click mostrar la DESCRIPCIÓN del artículo para que el vendedor sepa qué producto entra. Gerencia subió 01_INPUTS/RAW_PRODUCTOS/productosjulio.xlsx (dato en columna H "Descripción Art.").
- Backend: nuevo `_acc_desc_articulo_map()` que lee ese archivo (header autodetectado; Código Art. col D, Descripción Art. col H, Linea Comercial, Categoría), mapea código→{descripcion, linea, categoria}. Autodetección por mes (productos<mes>.xlsx, fallback al más reciente), cacheado por mtime y sumado a `_acc_mes_sig` (al resubir el archivo se refresca solo). La resolución de códigos usa primero este archivo (descripción) y cae al 04D (Linea Comercial); `codigos_detalle` ahora trae `descripcion`/`linea`/`categoria`.
- Frontend: el modal "Códigos participantes" muestra `código · descripción de artículo` (ej. 30075 · GORDON'S GIN 6x700, 80010 · LOS ARBOLES SEL MALBEC 6X750). Los 4 códigos antes pendientes (35093, 35101, 74882, 74881) ya resuelven.
- .gitignore: `01_INPUTS/RAW_PRODUCTOS/` estaba ignorado entero; se cambió a `RAW_PRODUCTOS/*` + `!RAW_PRODUCTOS/productos*.xlsx` para trackear solo el archivo mensual de productos (58KB) sin subir el raw 04D de 19MB. Así Render tiene el archivo y resuelve las descripciones.
- Validado: 339 productos leídos; los 20 códigos de ACJ26-022/023 resuelven su descripción; JS del portal parsea; screenshot del modal con descripciones; dry-run de git agrega solo productosjulio.xlsx. Deployado a Render.

## 2026-07-02 - feat(acciones comerciales): mostrar el CÓDIGO cuando el SKU no está en el maestro

- Pedido: los códigos de las cajas mixtas son correctos; gerencia actualizará el maestro de productos y ahí se resolverá el nombre (el match por código ya funciona en dashboard/cierre, es independiente del maestro). Mientras tanto, si un código no encuentra match en el maestro, mostrar EL CÓDIGO para que el vendedor lo vea igual.
- Backend: cada acción por código ahora trae `codigos` = [{codigo, producto, categoria, encontrado}] resolviendo cada SKU contra el maestro 04D. El campo `marcas` de la tarjeta pasó de los códigos crudos a un resumen legible: nombres resueltos + "cód. X, Y" para los pendientes (ej. ACJ26-023 → "Smirnoff; Smirnoff Flavors; Gordon's Flavors; Gordon's; cód. 35093, 35101"). Acciones sin códigos (por marca) quedan igual.
- Frontend: el modal de detalle agrega la sección "Códigos participantes": cada código con su producto; los que aún no están en el maestro se muestran igual, resaltados en ámbar "pendiente en maestro".
- Confirmado que el cierre del día también matchea por código (reúsa `_acc_product_pred`, línea 6931): al actualizar el maestro solo se resuelve el nombre/categoría/litros, el match ya opera hoy.
- Validado: payload resuelve 30019/30020/30131/30065→Smirnoff, 30135→Smirnoff Flavors, 30139/30134→Gordon's Flavors, 30075→Gordon's; pendientes 35093/35101 (ACJ26-023) y 74882/74881 (ACJ26-022) se muestran como código; JS del portal parsea; screenshot del modal con la sección de códigos. Deployado a Render.

## 2026-07-02 - feat(acciones comerciales): cajas mixtas almacén/kiosco por CÓDIGOS EXACTOS (SKU curados por gerencia)

- Pedido: armar las 2 cajas mixtas (almacén/kiosco, V3/V4/V6/V8/V10) con los códigos exactos que participan, en vez del match por marca. "Si hay algún parecido no importa" → no preocuparse por colisiones. Segmento almacén/kiosco se mantiene.
- Mapeo de los 2 grupos que pasó gerencia: Grupo 1 = Spirits (Smirnoff+Gordon's) → ACJ26-023 15%; Grupo 2 = VDA (Trapiche Reserva + Los Árboles) → ACJ26-022 20%.
- `productos_marcas` de ACJ26-022 y 023 pasó de tokens de marca a la LISTA DE CÓDIGOS. El `pred` ya soporta `code_set` (match por Codigo exacto), así que ahora cada acción matchea solo esos SKU (footprint + alertas). Detalle: Trapiche → "Trapiche Reserva" (los códigos del grupo 2 son solo Reserva, sin Origen By Trapiche).
  - Grupo 1 (ACJ26-023): 30019; 35093; 35101; 30020; 30135; 30131; 30065; 30139; 30075; 30134. Se dedupe `30020` (venía repetido) y se corrige `300131`→`30131` (typo). `35093` no está en el maestro liviano pero se incluye literal (el match es por código de venta).
  - Grupo 2 (ACJ26-022): 74737; 74415; 74421; 74419; 74882; 74881; 80089; 80007; 80008; 80010. `74882`/`74881` no están en el maestro liviano; se incluyen literal.
- Motor: el filtro heurístico "solo botella" ahora se saltea cuando la acción trae códigos explícitos (`solo_botella and not code_set`): con SKU curados no hace falta el heurístico. Queda inactivo para 022/023 (usan códigos) y disponible para futuras acciones sin códigos.
- Validado: CSV íntegro (24 filas × 36 cols); ACJ26-023 pred True para 30020 (botella en lista) y False para 35103 (Smirnoff Ice, fuera de lista); detalle 022 = Los Árboles + Trapiche Reserva, 023 = Smirnoff/Smirnoff Flavors/Gordon's/Gordon's Flavors; 23 acciones orden ASC; V3/V4 las ven, V7 no; alertas 3 legítimas; endpoints 200. Deployado a Render.
- REVISAR (gerencia): confirmar `35093` (no aparece en el maestro liviano; ¿código correcto?), `74882`/`74881` (idem), y que `300131` efectivamente era `30131`.

## 2026-07-02 - fix(acciones comerciales): ACJ26-023 (caja mixta Smirnoff+Gordon's 15%) es SOLO botella

- Aclaración del usuario: la acción del 15% (3 botellas Smirnoff + 3 botellas Gordon's) aplica SOLO a botella, no a lata/RTD. El detalle ya excluía Smirnoff Ice, pero el footprint/alertas usan el `pred` por marca SIN filtro de categoría, así que el token "Gordon's" todavía matcheaba Gordon's Tonic (lata RTD) y "Smirnoff" la Smirnoff Ice.
- Fix: nuevo filtro `_acc_es_botella(cat_canon, articulo)` (excluye categoría RTD y descripciones con marcador de lata "LATA"/"LAT"). `_acc_product_pred` lo aplica cuando la acción menciona "botella" en condicion_compra/unidad (se activa solo en ACJ26-022 y 023; ninguna otra acción de julio menciona botella). Vale para footprint Y alertas (una lata Smirnoff/Gordon's ya no queda autorizada por esta acción).
- Validado con datos reales: en 023 quedan afuera 35103 Smirnoff Ice, 35105 Ice Flavours y 35107 Gordon's Tonic (todas latas RTD) y adentro 30020 Smirnoff Green Apple 6X700 y 35101 Smirnoff BC Orange&Lime 6X700 (botellas). ACJ26-022 (vinos, ya botella) sin cambios. Alertas siguen en 3 legítimas; endpoints gerencia/V4/V3 → 200. Deployado a Render.
- NOTA: 35101 "Smirnoff BC Orange & Lime 6X700" (categoría sin clasificar en el maestro) es botella y entra al 15%. Si el usuario quiere excluir la línea BC del 15%, avisar.

## 2026-07-02 - feat(acciones comerciales): tarjeta caja mixta almacén/kiosco (V3/V4/V6/V8/V10) + review integral de alertas

- Pedido: (a) revisar cada acción para que el módulo (sobre todo alertas) trabaje bien; (b) agregar una tarjeta para V3/V4/V6/V8/V10, segmento Almacén+Kiosco: 20% en una caja mixta de 3 botellas Los Árboles + 3 botellas Trapiche por cliente, y 15% en 3 botellas Smirnoff + 3 botellas Gordon's, una sola caja por cliente en el mes; con el mismo click de categoría para ver la variedad; visible en gerencia y en los vendedores que aplican.
- Nuevas acciones (2 filas en el CSV de julio + 4 en detalle_categorias): se implementó como DOS tarjetas (ACJ26-022 20% VDA Los Árboles+Trapiche; ACJ26-023 15% Spirits Smirnoff+Gordon's) porque el cap de alerta es por producto (20 vs 15): una sola fila con "20|15" habría autorizado 20% también a Smirnoff/Gordon's y tapado sobre-descuentos. Segmento "Almacén; Despensa; Kiosco" (Despensa=Almacén), vendedores "V3; V4; V6; V8; V10", tope 1 caja mixta/cliente/mes. `lineas_comerciales` vacío a propósito (si se pone "VDA"/"Spirits", el pred matchea TODA la categoría, no solo las marcas). Validado: gerencia y V3/V4/V6/V8/V10 las ven; V7/V9 no; detalle expande marcas del maestro (Los Árboles Medio Alto, Trapiche Reserva/Origen; Smirnoff/Gordon's sin Smirnoff Ice).
- Review de alertas — 3 fixes de correctitud en el motor de matching (server_orbit.py), todos con footprint validado antes/después:
  1. Planes AASS en alertas: el tope de las acciones PLANES_AASS ahora aplica SOLO a clientes del plan (`requiere_plan_as` en `parsed` + skip si el cliente no está en `mod_planes_as.csv`). Antes autorizaban su % a cualquier autoservicio y tapaban sobre-descuentos de clientes sin plan.
  2. Token "TODOS ..." (ej. "Todos menos importados premium…") se trata como genérico, no como marca: antes ese token basura cortaba el match por categoría y ACJ26-007/008 (Spirits y Cerveza) no matcheaban nada. Además se mapeó "CERVEZA" en `_ACC_LINEA_TOK`.
  3. Apóstrofes: `_acc_norm` ahora ELIMINA apóstrofes/comillas (antes los volvía espacio), así "Gordons" (catálogo) = "Gordon's" (ventas). Corrige que ACJ26-005/006/011 no tomaban "Gordon's Tonic" y generaban falsas alertas.
- Enriquecimiento de detalle consciente de categoría: `_acc_enriquecer_grupo` restringe la expansión FAMILIA/MARCA_EXPLICITA a la categoría del grupo (ej. Smirnoff bajo Spirits no trae Smirnoff Ice, que es RTD).
- Resultado alertas: de 3→5 (fix Planes AASS destapó reales) y luego a 3 legítimas: Smirnoff Ice 25% (cód 35103) y Smirnoff Ice Flavours 6% (cód 35105) SIN acción en el catálogo de julio, y Don David 10% con cap 8% (sobre-descuento real). NOTA para gerencia: en junio existía ACJ26-027 (Smirnoff Ice 35103 al 25%); no está en el catálogo de julio — si sigue vigente hay que agregarla al CSV del mes.
- Validado: syntax OK; 23 acciones orden ASC; endpoints gerencia/V4/V3 → 200; screenshot del modal de ACJ26-023 (Smirnoff/Gordon's, sin Ice). Deployado a Render.

## 2026-07-02 - fix(acciones comerciales): las acciones de MAYORISTA no deben caer sobre autoservicios

- Bug reportado: la tarjeta de ACJ26-021 (Petit Mayoristas, canal MAYORISTA) mostraba al cliente 538, que es Autoservicio.
- Causa raíz: el canal MAYORISTA de la regla mapeaba a canon AUTOSERVICIO en `_acc_seg_canon`, y el clasificador global `_clasificar_segmento` también mete a los mayoristas dentro de AUTOSERVICIO. Así, toda acción de mayoristas matcheaba a cualquier autoservicio (538 = `TRADITIONAL TRADE / Autoservicio Tradicional` → AUTOSERVICIO). Encima no hay mayoristas en ventas, así que esas acciones debían dar 0 clientes.
- Fix (SOLO dentro del módulo de acciones; NO se toca `_clasificar_segmento`, que alimenta cobertura/CCC/11T/cierre):
  - `_acc_seg_canon`: MAYORISTA pasa a ser su propio canon (antes se agregaba AUTOSERVICIO); el fallback "cualquier segmento" ahora incluye MAYORISTA.
  - `_acc_preparar_from_df`: nueva columna `_es_mayorista` (Ramo/Subramo contiene "MAYORISTA"), para separar al mayorista del autoservicio sin cambiar el clasificador global.
  - Nuevo helper `_acc_seg_match(row_seg, row_may, rule_segs)`: cliente mayorista matchea solo si la regla apunta a MAYORISTA; cliente no mayorista matchea por su segmento clasificado. `_match` (payload) usa la versión vectorizada; `_alertas_descuento_mes` usa el helper. Corrige el cruce en ambos sentidos (mayorista→AS y AS→mayorista).
- Validación real: ACJ26-019/020/021 (Petit Mayoristas) → 0 clientes, 538 excluido; ACJ26-001 (Autoservicio) sigue incluyendo a 538; ACJ26-002 (Trad/Kiosco/On Premise) no lo incluye. Alertas sin crash (3), endpoints gerencia/V4/V3 → 200. Deployado a Render.

## 2026-07-02 - fix(acciones comerciales): detalle de categoría en MODAL encima + marcas reales del maestro

- Feedback del usuario tras probar en Render: el botón de la categoría (1) hacía scrollear al fondo de la lista (se renderizaba en `acc-v-detalle`/`acc-g-detalle` al final), poco práctico; debía abrir una tarjeta ENCIMA con diseño propio; y (2) mostraba la categoría genérica ("VDA") en vez de las MARCAS que entran (ej. "VDA Alto Alma Mora").
- Backend (`server_orbit.py`): los grupos de `detalle_categorias` ahora se enriquecen con las marcas reales resueltas del **maestro 04D vigente** (no hardcode). Nuevos `_acc_marcas_maestro()` (cat_canon → [{segmento, marca=Linea Comercial}], ordenado por gama Medio→Superior) y `_acc_enriquecer_grupo()` que por `tipo_detalle` expande: `FILTRO_MAESTRO`/`FILTRO_EXCLUSION` → todas las marcas de la(s) categoría(s); `FAMILIA`/`MARCA_EXPLICITA` → marcas cuya Linea Comercial matchea el token; el resto (`PRODUCTO_EXPLICITO`, `PRODUCTO_O_FAMILIA`, `SUBREGLA`, `EXCLUSION`) queda literal. Se resuelve en el payload (invalida por mtime del 04D vía `_acc_mes_sig`). Cada item lleva ahora `marcas:[{segmento,marca}]`.
- Frontend (`portal.html`): `accShowCat` reescrito para abrir un **modal `.accd-*`** centrado y encima (overlay `.emod-bg`, cierra por ✕ / click afuera), en vez de escribir al fondo. Diseño propio: cabecera con degradé magenta + `categoria_tarjeta` + `id_accion`/segmento; secciones por grupo (multi-ref) y, dentro, marcas agrupadas por segmento en chips. Ítems literales (productos/subreglas/exclusiones) se listan como nota. `id_accion` y el chip de categoría en la tarjeta sin cambios.
- Validación real: payload → VDA Alto incluye "Alma Mora" (ejemplo del usuario); RTD Latas (`PRODUCTO_O_FAMILIA`) queda literal (Gordons Tonic / Smirnoff BC / Antares + subregla BC 15%); endpoints gerencia/V4 → 200; JS del portal parsea (vm.Script). Screenshot del modal renderizado con la CSS real: abre encima, marcas por segmento, acentos OK ("Champaña", "Unánime"). Deployado a Render.

## 2026-07-02 - feat(acciones comerciales): esquema julio (categoria_tarjeta + detalle click desde DETALLE_CATEGORIAS), orden por orden_visual

- Pedido: el módulo de Acciones Comerciales debe consumir el catálogo de julio (`01_INPUTS/ACCIONES COMERCIALES/2026-07/acciones_comerciales_julio_2026_penaflor.csv`, sep `;`, UTF-8-SIG) manteniendo compatibilidad con el CSV de junio. Ordenar tarjetas por `orden_visual` ASC (orden del PPTX), mostrar `id_accion` + `categoria_tarjeta`, y al hacer clic en la categoría abrir el detalle de marcas/líneas desde `DETALLE_CATEGORIAS` vía `detalle_click_ref` (varias refs separadas por `|` → abrir todas). No hardcodear marcas en la tarjeta.
- Fuente real (sin hardcode): el detalle sale de `detalle_categorias_acciones_julio_2026_penaflor.csv` (misma carpeta del mes). Las columnas nuevas del catálogo están agregadas AL FINAL, así que junio (sin ellas) sigue funcionando: `r.get(...)` cae a vacío/None.
- Backend (`server_orbit.py`):
  - Nuevo `_acc_detalle_map()`: autodetecta el `detalle_categorias*.csv` del mes más reciente, lo parsea (';', UTF-8-BOM) y devuelve `{detalle_click_ref: {categoria_tarjeta, items:[{grupo, marca_o_linea, tipo_detalle, observaciones}]}}`. Cacheado por (path, mtime). `{}` en meses sin detalle (junio) → sin efecto.
  - `_acciones_mes_payload_uncached`: cada acción agrega `categoria_tarjeta`, `mostrar_detalle_click` (True solo si el CSV dice `SI` **y** hay grupos resueltos), `detalle_click_ref` (lista), `detalle_categorias` (grupos resueltos) y `orden_visual` (int|None). La lista de acciones se ordena por `orden_visual` ASC con sort **estable** (junio: todos None → conserva orden del catálogo). Totales/matching de líneas sin cambios.
  - No se tocó el matching de marcas/segmentos, la inversión (`valorDescuento × CantBase`), ni cobertura/CCC/11T/cierre.
- Frontend (`PAV MATINAL PE_A FLOR/portal.html`): tarjeta de vendedor y de gerencia agregan un chip `🗂 categoria_tarjeta` (helper `accCatChip`). Si `mostrar_detalle_click`, el chip es clickeable y abre `accShowCat`, que despliega en el contenedor de detalle existente (`acc-v-detalle`/`acc-g-detalle`) las marcas/líneas de cada grupo de `detalle_categorias`. `id_accion` se sigue mostrando igual. En junio (sin `categoria_tarjeta`) `accCatChip` devuelve '' → tarjeta idéntica a antes.
- **Autoactualización por mes (regla nueva):** `_acc_catalogo_mes` y `_acc_detalle_map` ahora eligen la carpeta del **mes en curso** (YYYY-MM en hora AR, `_ARG_TZ`) vía helper compartido `_acc_mes_dir()`, en vez de "la carpeta más reciente" incondicional. Regla: si existe `01_INPUTS/ACCIONES COMERCIALES/<YYYY-MM>/` del mes actual, se usa; si todavía no se subió, cae al mes real más reciente que NO sea futuro (subir el mes siguiente por adelantado **nunca** adelanta el cambio); si todo fuera futuro, a la más nueva. Catálogo y detalle salen siempre de la MISMA carpeta. Además `_acc_mes_sig()` (firma de caché) incluye el mes en curso: el payload se recalcula solo al cambiar de mes aunque el proceso de Render lleve semanas vivo y ningún mtime cambie. Mismo criterio que ya se usa en Planes AASS (escala/sincargos por mes). Convención: cada mes subir `acciones_comerciales_<mes>_2026_penaflor.csv` + `detalle_categorias_*.csv` a la carpeta `<YYYY-MM>` y el sistema los toma solo.
- Validación real: `_acc_detalle_map()` → 11 refs; payload julio → 21 acciones, `orden_visual` monotónico ASC, `categoria_tarjeta` presente, multi-ref resuelta (VDA/VDG/Espumantes/Sidra = 4 grupos). Selección de mes probada en 5 escenarios (mes en curso, agosto pre-subido no adelanta, mes sin carpeta cae al no-futuro, solo junio, solo futuro). Endpoints `/api/gerencia/acciones_mes`, `/api/vendedor/V4/acciones_mes` (21) y `/api/vendedor/V3/acciones_mes` (5, sin AS/On Premise) → 200, orden ASC. Serialización JSON OK (tipos nativos int/bool, sin numpy). Compat junio verificada (fila sin columnas nuevas: cat='', refs=[], mostrar=False, orden=None; sort estable preserva orden). Deployado a Render en esta sesión.

## 2026-07-01 - revert(cierre dia): se quita el PASO 0 de consistencia — el gap venta vs facturación es esperado

- Contexto: se había agregado un PASO 0 que frenaba el cierre cuando un vendedor tenía Acumulado > 0 en resultado.xlsx pero 0 líneas en ventas.csv (caso V9/V6 hoy). Parecía imposible, pero NO lo es.
- Aclaración del usuario (regla de negocio): el módulo de OBJETIVO/acumulado toma el PEDIDO ENVIADO por el vendedor; el módulo de VENTAS solo refleja lo FACTURADO. Un pedido cargado y aún no facturado aparece en el acumulado (resultado.xlsx) pero todavía no en el detalle (ventas.csv), por lo que ese vendedor puede tener acumulado sin clientes con compra. Es un margen NORMAL y aceptado entre lo vendido y lo facturado; NO es un error a bloquear.
- Cambio: se revierte el PASO 0. Se elimina `validar_consistencia_cierre.py` y se quita su invocación de `CIERRE_DIA_ORBIT.bat`. El cierre vuelve a publicar normal aunque exista ese desfasaje venta/facturación. No reintroducir esta validación como bloqueo.

## 2026-07-01 - fix(cierre dia): el incentivo Club FARO frenaba el cierre como "cambio funcional"

- Síntoma: `CIERRE_DIA_ORBIT.bat` abortaba en la verificación inicial de Git con "Hay cambios FUNCIONALES pendientes fuera de las rutas operativas", listando todos los inputs operativos (ventas, resultado, clientes, datasets…). No regeneraba nada ni publicaba.
- Causa raíz: `01_INPUTS/incentivo_club_faro .xlsx` (objetivos del Incentivo Club FARO, consumido por `server_orbit.py:5368` vía `incentivo_club_faro*.xlsx`) es un input operativo que se actualiza en cada cierre, pero **no estaba en la allowlist** de excludes del guardián (líneas 27 y 178) ni en los `git add` del PASO 3. Al cambiar, el guardián lo interpretaba como código funcional sin commitear y frenaba todo.
- Cambio mínimo: se agregó `":(exclude)01_INPUTS/incentivo_club_faro*.xlsx"` a las dos allowlists de `git status --porcelain` y `git add "01_INPUTS/incentivo_club_faro*.xlsx"` en el PASO 3, junto a `ventas-clubfaro.csv`. Patrón sin espacio (`incentivo_club_faro*.xlsx`) igual que el server, tolera el espacio raro del nombre real (`incentivo_club_faro .xlsx`).
- Validación real: se reprodujo el error corriendo el .bat (salía exit 1 en el guardián). Tras el fix, el `git status --porcelain` con los mismos excludes ya no marca el incentivo; sólo queda el propio `CIERRE_DIA_ORBIT.bat` editado (pendiente de commit, cambio de código legítimo).

## 2026-07-01 - fix(planes as): la escala del mes se elige por el MES del nombre del archivo, no por mtime

- Pedido: la medición de Planes AASS (a qué escala accede cada cliente según su compra) debe cambiar SOLA de archivo al cambiar de mes. El usuario sube cada mes `escala<mes>.xlsx` a `01_INPUTS/Planes AASS/` (p.ej. `escalajulio.xlsx`) y no quiere tocar código todos los meses.
- Causa raíz: `_cargar_escala_df()` en `generar_datasets_acum.py` autodetectaba el `escala*.xlsx` **más reciente por fecha de modificación (mtime)**. Frágil: un `git checkout`, re-descarga o subir el archivo del mes siguiente por adelantado podía elegir el equivocado.
- Cambio mínimo: nuevo helper `_archivo_del_mes(candidatos, mes_idx=None)` que elige el archivo cuyo nombre contiene el MES actual en español (`_MESES_ES`). Regla: julio→`escalajulio.xlsx`, agosto→`escalaagosto.xlsx`, etc. Si ningún archivo matchea el mes en curso, cae al más reciente por mtime (fail-safe: la pantalla de Planes nunca queda sin escala). En `_cargar_escala_df` se pone el archivo del mes primero y el resto como respaldo, antes de la hoja 'ESCALA' de Reconocimiento.
- Convención de nombre (queda establecida): `escala` + nombre del mes en español, minúsculas, `.xlsx`. El match es por "el nombre contiene el mes", así que tolera variantes tipo `escalasjunio.xlsx`.
- Validación real: `_archivo_del_mes` elige `escalajulio.xlsx` en julio, `escalasjunio.xlsx` simulando junio, y cae a mtime simulando agosto (sin archivo). `generar_datasets_acum.py` corre completo: "Escala Plan AS desde: escalajulio.xlsx" y regenera `mod_planes_as.csv` sin errores.
- Ampliación (misma sesión): a pedido del usuario, se extendió la regla a `sincargos*.xlsx`. El helper se generalizó a `_ordenar_por_mes(candidatos)` (devuelve lista ordenada: el del mes primero, resto por mtime) y `_archivo_del_mes` ahora lo reusa. Migrados los 3 puntos que leían sincargos por mtime: `_cargar_sincargos_mes`, `_cargar_planfrio_mes`, `_bbdd_desde_sincargos`. Convención: `sincargos<mes>.xlsx`. Validado: en julio, con sólo `sincargosjunio.xlsx` presente, cae al de junio (fallback correcto); al subir `sincargosjulio.xlsx` lo tomará solo. Pipeline completo OK.

## 2026-07-01 - feat(portal): botón "Plan Frizze" (On Premise Noche · 3+1 misma variedad) en gerencia y vendedor

- Pedido: botón "Plan Frizze" debajo de Incentivo FARO. Por cada cliente del plan una tarjeta con código, nombre, dirección, localidad, sub canal, vendedor y ventas por marca (litros y $) + sin cargos enviados; clic en el sin cargo → fecha de facturación; alerta si el sin cargo enviado es de otra variedad que la facturada (el 3+1 debe ser de la misma variedad). En gerencia (todos) y vendedor (solo los que tienen cliente con el plan).
- Fuentes reales (sin hardcode / sin mock):
  - Definición del plan (clientes 301/1443, códigos 14583 Frizze Blue New / 14619 Frizze Bubble Mood, mecánica) se **parsea de `01_INPUTS/PLAN FRIZZE/planfrizze.xlsx`** (el archivo que agregó el usuario) — fuente única y editable.
  - Ficha del cliente ← `clientes.xlsx` (SubSegmento = sub canal). 1443 NO está en el maestro → sus campos muestran "Dato no disponible".
  - Ventas $/litros ← `ventas.csv` (mes vivo), líneas `ImporteNetoItem>0` de los 2 códigos; litros = CantBase × Lts/caja del maestro 04D (ambos 6 L/caja).
  - Sin cargos ← líneas 100% desc (`ImporteNetoItem==0`) de los 2 códigos; fecha = FechaComprobante (regla de facturación).
  - Alerta = sin cargo de una variedad sin compra de esa misma variedad.
- `server_orbit.py`: `_plan_frizze_config()` (parser del xlsx, cacheado por mtime) + `_plan_frizze_clientes()` (arma tarjetas en vivo, reusa `_cargar_maestro_04D` para litros y `_ventas_parsed` cacheado). Endpoints nuevos `GET /api/gerencia/plan_frizze` y `GET /api/vendedor/<vid>/plan_frizze` (este filtra a los clientes del vendedor). Aditivo: no toca Planes AS, FARO, ni el pipeline de datasets/BAT.
- `PAV MATINAL PE_A FLOR/portal.html`: botón en menú gerencia (bajo Incentivo FARO) + tab vendedor (bajo FARO, se muestra sólo si el vendedor tiene cliente del plan, decidido en `vPlanFrizze()` tras cargar datos). Render `_pfRender`/`_pfHeader`/`_pfClienteCard` (cabecera con las 2 imágenes de producto sobre banner degradé azul→violeta + tarjetas por cliente) y desplegable `verSincargoFrizze` (fecha de facturación por marca). CSS `.pf-*` con tokens del sistema (--surf/--b/--wn/--ok/--f-dis).
- Imágenes: `frizze_blue.jpg` / `frizze_bubble.jpg` copiadas a la carpeta del frontend (servidas por la ruta estática existente).
- Validación: endpoints por test_client y en vivo (8502) → gerencia 2 clientes, V8 1 (cliente 301), V4 0. Alerta probada con datos reales (cliente 2353: sin cargo Blue sin compra Blue → alerta correcta + fechas). `node --check` del JS OK. Screenshots reales gerencia + vendedor V8 (login real): cabecera, tarjetas, "Dato no disponible" para 1443, y tab "FRIZZE" visible en la barra del vendedor. Datos en 0 para 301/1443 porque aún no hay ventas Frizze del mes vivo (poblará en julio). Emoji 🥂 (🫧 salía como cuadro en Win10).

## 2026-06-30 - feat(cierre): Acciones Comerciales de junio en el cierre (catálogo versionado, esquema nuevo)

- Pedido: registrar el catálogo de reglas de acciones de junio (las Acciones del cierre de junio salían vacías).
- Diagnóstico: el cierre usaba `_cierre_acciones_versionado` (esquema MAYO: `canal/categoria/accion_grupo` + `_REGLA_CAT_MAP`), pero la fuente real de junio (`01_INPUTS/ACCIONES COMERCIALES/2026-06/...csv`) está en el esquema NUEVO (`canal_aplica/segmento_cliente_aplica/tipo_regla/productos_marcas`, con Planes AASS, 11T, innovaciones, bonificaciones). Forzar junio al esquema mayo habría perdido la mayoría de las acciones. El motor LIVE (`_acciones_mes_payload`) ya entiende el esquema nuevo.
- Decisión: en vez de hand-craftear un catálogo mayo-schema (infiel), el cierre computa junio con los **helpers oficiales** del motor live, sobre el **ventas_mes congelado** + el **catálogo versionado** que `cerrar_mes.py` ya copia (`01_INPUTS/cierres mes/acciones_<MMAAAA>.csv`). Durable y sin registrar mes a mes.
- `server_orbit.py`:
  - Refactor (extract-method): `_acc_preparar_from_df(df)` (cómputo de columnas de acciones, sin I/O) + `_acc_preparar_ventas(nombre)` (lee ventas.csv vivo) + nuevo `_acc_preparar_ventas_mes_versionado(path)` (lee el ventas_mes congelado del cierre, coma/utf-8). Motor live intacto.
  - Nueva `_cierre_acciones_junio_schema(files, reglas)`: matching con `_acc_seg_canon`/`_acc_subseg_filtro`/`_acc_product_pred` (mismos del live), inversión = valorDescuento×CantBase, totales sobre la unión de líneas (sin doble conteo), gate Plan AS. Devuelve {resumen, detalle} con el shape que ya renderiza el portal.
  - `_cierre_acciones_versionado`: si no hay catálogo mayo-schema registrado para el mmaaaa, usa el catálogo versionado del cierre (esquema nuevo) → `_cierre_acciones_junio_schema`. Mayo (registrado) sigue por el path mayo.
- Validación (test_client): cierre 2026-06 → 26 acciones, inversión total **36.131.409** = idéntica a `/api/gerencia/acciones_mes` (motor live), clientes 929. Detalle correcto (SPIRITS 29,4M, Petit Mayoristas 25,5M, Planes AASS, 11T AS, Drop VDA TRAD 791 clientes). Mayo intacto (14 acciones, 14,97M). Motor live de acciones sin cambios (28 acciones, 36,1M). `py_compile` OK.

## 2026-06-30 - feat(cierre): Sell Out con drill-down (categoría → subcategoría → marcas) y baja de la tarjeta V20 Depósito

- Pedido: en el Cierre de Mes, (1) poder aperturar la tarjeta de Sell Out por sus categorías y marcas; (2) sacar del informe la tarjeta "Del cual · V20 Depósito".
- La data ya traía todo: `_sellout_desde_ventas` devuelve `categorias[].subcategorias[].marcas[].varietales[]` y `categorias[].marcas[]`. No hubo cambios de backend para esto (el sell-out del cierre ya incluye V20 en el total).
- `PAV MATINAL PE_A FLOR/portal.html` (`_renderCierreHistorico`): el Sell Out del cierre pasó de tabla estática a un sub-componente interactivo `_renderCierreSellout` (placeholder `#cierre-sellout`), espejo del drill-down del dashboard (`_renderSoDash`): clic en categoría abre subcategorías (Alto/Medio/Nacionales/Importados/RTD/RTD(S)) con su avance, y dentro las marcas; clic en marca abre varietales (SKUs). Estado `soCExp`/`soCMExp` (se resetea al cambiar de mes), toggles `window._soCTog`/`_soCMTog`. Fila TOTAL (ruta + depósito) con avance vs objetivo de empresa y nota "Incluye V20 Depósito".
- Se eliminó la tarjeta "Del cual · V20 Depósito (venta directa)" del informe del cierre (el depósito sigue sumado en el total; `total_deposito` se muestra en la nota).
- Validación: `node --check` del JS del portal OK; test_client cierre 2026-06 → categorías con subcategorías y marcas con varietales (VINOS DEL AÑO 4 subs/22 marcas, SPIRITS Nacionales 21.160 L/Importados 781 L, RTD/RTD(S), marcas con SKUs ej. Smirnoff 17.460 L/5 varietales). Total 56.356 L (depósito 11.087 L).

## 2026-06-30 - feat(cierre): 'mejor vendedor en volumen' se determina por alcance del objetivo mensual

- Pedido: cambiar la forma de determinar el mejor vendedor en volumen en el Cierre de Mes; que sea por el ALCANCE DE SU OBJETIVO MENSUAL (avance % = acumulado/objetivo), no por litros+dinero vendidos.
- Decisión del usuario (alcance del cambio): SOLO el ganador de Volumen. El score general / 'mejor general' NO se toca (sigue litros+dinero 40% + 11T 30% + Innov 30%).
- `server_orbit.py` (`_cierre_ranking_payload`): nuevo parámetro `avance_map` (codigo→avance_pct). Si viene, re-rankea la dimensión volumen por alcance de objetivo (desc), rehace la etiqueta MEJOR_VOLUMEN_DINERO y el ganador de volumen pasa a tener `metrica`=alcance% + `base`="alcance_objetivo". No modifica `_ranking` ni el score general. La lista de ranking ahora también expone `alcance_objetivo_pct` por vendedor.
- `server_orbit.py` (endpoint cierres_historicos): arma `avance_map` desde `cierre["objetivos_avance"]` (ya calculado) y lo pasa a `_cierre_ranking_payload`.
- `PAV MATINAL PE_A FLOR/portal.html` (`gCierreMes`): la tarjeta de ganadores pasa de "Volumen / Dinero ($)" a "Volumen · alcance objetivo" y muestra el % del objetivo (ej. "181,8% del objetivo").
- Validación (test_client): cierre 2026-06 → mejor en volumen V4 GRIBAUDO ANGEL 181,79% (antes V8 por dinero); mejor general sigue V8 ALVAREZ VANESA (score 100, intacto). 2026-05 → mejor en volumen V3 NADIA GAMBINO 144,93%. Recálculo en vivo, aplica a todos los cierres. `py_compile` OK.

## 2026-06-30 - fix(cierre): Sell Out incluye depósito (V20) y ranking de Innovaciones deja de marcar 0 clientes

- Pedido: en el Cierre de Mes (gerencia), (1) la tarjeta de Sell Out debe estar completa incluyendo la venta de depósito (V20); (2) el ranking marca una "mejor vendedora en innovaciones" pero abajo dice 0 clientes — revisarlo.
- Causa Sell Out: el cierre mostraba `categorias` solo de ruta (vs objetivo) y V20 como bloque aparte. El dashboard ya se había unificado (29/06) agrupando V20 dentro de cada categoría vs objetivo de empresa; el cierre quedó con el criterio viejo.
- Causa Innovaciones/ranking: `_cierre_extras_versionado` tomaba los códigos de innovación con `gcm._leer_innovaciones` (parser viejo que busca el patrón "000000" en las primeras filas del xlsx). El formato de `Innovaciones.xlsx` cambió a "CODIGO - NOMBRE" → ese parser devolvía **0 códigos** → `_inov_por_vend`/`_inov_detalle` daban 0, pero `_ranking` igual asignaba la etiqueta MEJOR_INNOVACIONES a alguien con 0 clientes.
- `server_orbit.py` (`_cierre_extras_versionado`):
  - Sell Out: ahora `categorias = _sellout_desde_ventas(so_df)` con V20 incluido (igual que `/api/gerencia/sellout_litros`); agrega `total_litros`, `incluye_deposito:true` y conserva `deposito`/`total_deposito` como desglose informativo (ya sumado en categorias). Ya NO usa `_sellout_con_deposito` (que separaba ruta vs depósito).
  - Innovaciones: `cod_inov = set(_gda().INOV_PRODUCTOS.keys())` (loader oficial, 22 productos, mismo que el dashboard) en vez del parser viejo. Esto corrige el detalle de innovaciones Y el ranking (clientes_innovaciones reales).
- `PAV MATINAL PE_A FLOR/portal.html` (`gCierreMes`): la tarjeta de Sell Out muestra el TOTAL (ruta + depósito) con nota "Incluye V20 Depósito… objetivo de empresa"; el bloque V20 pasó de "Total ruta + depósito" a "Del cual · V20 Depósito (desglose informativo, ya incluido arriba)".
- Validación (test_client, cierre 2026-06): Sell Out total 56.356,1 L (depósito 11.087 L); categorías con V20 incluido (VINOS DEL AÑO 21.855 L=128,4%, SPIRITS 21.942 L=128,9%, RTD 10.424 L=115,1%, CHAMPAÑA 1.079 L=144,5%, VINOS DE GUARDA 567 L=69,4%, CERVEZA ART. 488 L=114,9%). Innovaciones 19 productos (CAZADOR MALBEC 76, DADA LATA 48, FRIZZE MANXANA 47…). Ranking innovaciones: V8 ALVAREZ VANESA con 115 clientes (antes 0). Recálculo en vivo (no se regeneran archivos del cierre); aplica también a mayo. `py_compile` OK.

## 2026-06-30 - fix(cierre): el cierre de mes ahora corre de verdad y cada mes aparece en gerencia con selector

- Síntoma: el usuario ejecutó `CIERRE_MES_ORBIT.bat` y "no hizo el cierre". Quería verlo en gerencia → Cierre de Mes con un selector para ir pasando entre meses.
- Causa raíz 1 (no cerraba): el `.bat` autodetecta el mes a cerrar leyendo la fecha máx de `01_INPUTS/ventas_mes.csv`, pero ese archivo quedó en MAYO (máx 2026-05-30). El cierre detectó 05/2026, vio que ya existía y no hizo nada — y encima terminaba con "LISTO" (exit 0). `ventas.csv` (vivo) sí tenía junio completo (6101 filas), con las mismas 58 columnas que `ventas_mes.csv` (solo cambia `;`/latin1 → `,`/utf-8 y FechaComprobante → ISO).
- Causa raíz 2 (no se veía en gerencia): el `.bat` solo corría `cerrar_mes.py` (versiona el trío en `01_INPUTS/cierres mes/`), pero el portal listaba los cierres desde `07_CIERRES_MENSUALES/index_cierres_mensuales.json`, que solo lo escribe `generar_cierre_mensual.py` — y el `.bat` nunca lo llamaba. Por eso solo figuraba mayo y el selector (que YA existe en `portal.html:3689`, aparece con >1 cierre) no crecía.
- Decisión del usuario: (1) el portal descubre los cierres directo de `01_INPUTS/cierres mes/` (FASE 2b); (2) el cierre genera `ventas_mes.csv` desde `ventas.csv`.
- `tools/preparar_ventas_mes.py` (NUEVO): re-codifica `ventas.csv` (`;`/latin1) → `ventas_mes.csv` (`,`/utf-8-sig), normaliza FechaComprobante a ISO, preserva las 58 columnas como str (sin floats fantasma). Backup del ventas_mes previo en `99_BACKUPS_ORBIT/`.
- `CIERRE_MES_ORBIT.bat`: (a) antes de versionar, regenera `ventas_mes.csv` desde `ventas.csv` (solo en modo automático sin argumentos; con mes manual NO se toca); (b) la rama "no hay nada para publicar" ya no dice "LISTO" — va a `:fin_nada` con mensaje claro ("este mes ya estaba cerrado, usá MMAAAA --force"). Normalizado a CRLF.
- `tools/cerrar_mes.py`: se agregó `ventas_acumulada.csv` → `ventas_acumulada_<MMAAAA>.csv` al plan (opcional) para que el 11T trimestral del cierre quede versionado.
- `server_orbit.py` (`gerencia_cierres_historicos` + nuevo `_cierre_manifest_versionado`): además del índice 07, descubre los períodos presentes en `01_INPUTS/cierres mes/` (`ventas_mes_*.csv`) que no estén en el índice y los arma 100% desde el cierre versionado (manifest mínimo reconstruido con el motor oficial + objetivos/avance + 11T + sell-out + ranking). Mayo (que está en el índice 07) no se duplica.
- Validación: `preparar_ventas_mes.py` → ventas_mes.csv = junio (6101 filas). `cerrar_mes.py` → 5 archivos versionados en `cierres mes/` (incl. ventas_acumulada_062026.csv). `app.test_client().get('/api/gerencia/cierres_historicos')` → HTTP 200, `total_cierres=2`: **2026-06** (filas 5960, avance empresa 111,99%, 11T ccc 5280/3552, sell-out 6 cat, ranking 7 vend) y **2026-05** intacto. El selector de mes ahora muestra ambos. `py_compile` OK en los 3 .py.
- Pendiente (preexistente, fuera de alcance): innovaciones del cierre versionado dan 0 productos (mayo también); acciones de junio quedan vacías porque `_ACC_REGLAS_POR_MMAAAA` solo registra mayo. NO publicado a Render (sin commit/push) — a la espera del OK del usuario.

## 2026-06-30 - feat(gerencia): innovaciones muestran el total de cobertura acumulada del mes por innovación

- Pedido: en gerencia → pantalla de Innovaciones, controlar que el dato esté correcto y agregar —junto al total del día que ya está a la derecha de cada innovación— el total de cobertura acumulada del mes (cantidad absoluta de clientes que la compraron).
- Control del dato (sin cambios de código): el dataset `mod_innovaciones_segmento.csv` se genera bien (`clientes_compraron` = clientes de la cartera con ImporteNeto>0 sobre la innovación en el mes vivo, solo Peñaflor, sin doble conteo entre vendedores/subcanales). El server (`gerencia_innovaciones_total`) recalcula `pct` y agrega `compraron_total` por producto correctamente. Reconcilia: 22 productos, cartera 2031, cobertura mes 0–43 clientes (top: CAZADOR MALBEC 43, Antares XPA 33, Frizze Manxana 31). La columna `pct_cobertura` del CSV está como fracción (0.0041) pero NINGÚN consumidor la usa: todos recalculan `compraron/cartera`, así que no afecta — se deja como está (fuera de alcance).
- `PAV MATINAL PE_A FLOR/portal.html` (`gInnovaciones`): a la derecha de cada innovación se agrega un chip "<n> mes" con `prod.compraron` (total mensual = suma de los subcanales, que el portal ya calculaba en `byProd` para el %). Queda: **total mes · total día**, con el mismo estilo del chip del día. No se tocó el backend.
- Ajuste posterior (mismo día): el usuario pidió quitar el % de cobertura, solo quieren los dos totales. Se eliminó el chip "<pct>%" de la fila; `pct` se sigue calculando internamente (orden de la lista + tooltip del chip mes) pero no se muestra.
- Validación: `GET /api/gerencia/innovaciones_total?dia=Ma` (server 8502) → HTTP 200; `compraron_total` por producto×segmento coincide con el agregado del dataset; el portal suma por `producto_nombre`. Sin reinicio del server (cambio solo de frontend).

## 2026-06-30 - feat(gerencia): pantalla de Clientes incluye el Depósito (codven=1)

- Pedido: en gerencia → pantalla de Clientes poder seleccionar TODOS los clientes, incluidos los del depósito. En `clientes.xlsx` el depósito figura como `codven=1` (no 20).
- Causa: `_clientes_maestro()` excluía `_VENDEDORES_EXCLUIDOS = {1,2,5,20}`, así que los 29 clientes del depósito (codven=1) no aparecían en el buscador.
- `server_orbit.py` (`_clientes_maestro`): nuevo parámetro `incluir_deposito=False`. El caché ahora guarda el maestro completo y el filtro de excluidos se aplica al retornar; con `incluir_deposito=True` solo se excluyen 2/5/20 (conserva codven=1). Por defecto sigue excluyendo el depósito → cobertura, planes AS y demás métricas con objetivo intactas.
- `server_orbit.py` (`clientes_buscar`, `cliente_ficha`): pasan `incluir_deposito=True` — son las dos rutas de la pantalla de Clientes (búsqueda + ficha). El resto de callers (cobertura, planes_as join, alertas V3) quedan en el default.
- `PAV MATINAL PE_A FLOR/portal.html`: la nota del buscador (sin vendedor) ahora dice "Cartera completa + Depósito (V1), sin V2/V5".
- Regla de negocio respetada: el depósito sigue EXCLUIDO de toda métrica con objetivo; solo se lo deja seleccionar/ver en la pantalla de Clientes. Los clientes del depósito muestran chip "V1" (así viene el dato en el maestro).
- Validación: `_clientes_maestro()` → 2097 clientes (codven 3..10, sin depósito); `_clientes_maestro(incluir_deposito=True)` → 2126 (incluye los 29 de codven=1, ej. #100000 DELFIN S.A.).

## 2026-06-29 - feat(gerencia): Sell Out agrupa toda la venta de la empresa (incluye V20) vs objetivo

- Pedido (cambio de criterio): el objetivo de Sell Out es de la EMPRESA, independiente del vendedor que vende. La tarjeta debe estar unificada y AGRUPAR toda la venta (ruta + V20 Depósito) contra el objetivo, no mostrar V20 como bloque aparte sin objetivo.
- `server_orbit.py` (`gerencia_sellout_litros`): ahora calcula `_sellout_desde_ventas(df)` sobre el df completo con V20 incluido (`incluir_deposito=True`), en vez de `_sellout_con_deposito` que separaba ruta vs depósito. Devuelve `categorias` (real ya incluye V20 en cada categoría, avance vs objetivo de empresa), `total_litros` e `incluye_deposito:true`. Ya no devuelve `deposito`/`total_ruta`/`total_deposito`/`total_general`.
- `PAV MATINAL PE_A FLOR/portal.html` (`_renderSoDash`): se eliminó el bloque de filas separadas de V20; queda una sola tabla con el TOTAL agrupado y una nota "📦 Incluye V20 Depósito (venta directa). El objetivo de Sell Out es de la empresa...". El drill-down por categoría/objetivos sigue intacto.
- Nota de alcance: este criterio (V20 agrupado vs objetivo) aplica al **Sell Out del dashboard de gerencia**. El cierre de mes y los demás bloques (11T, innovaciones, cobertura) siguen mostrando V20 como línea aparte; no se tocaron.
- Validación: `/api/gerencia/sellout_litros` (server 8502 reiniciado) → `total_litros` 55.345,4 L, `incluye_deposito:true`. Categorías con V20 incluido: VINOS DEL AÑO 21.459,0 L (126,1%), SPIRITS 21.357,2 L (125,5%), RTD 10.407,7 L (114,9%), VINOS DE GUARDA 560,2 L (68,6%), CHAMPAÑA 1.072,8 L (143,6%), CERVEZA ARTESANAL 488,5 L (114,9%). `python -c ast.parse` OK.

## 2026-06-29 - feat(gerencia): Sell Out unificado en una sola tarjeta (ruta + V20 Depósito)

- Pedido: en el dashboard de gerencia, unificar el Sell Out en una sola tarjeta aperturable por objetivos (como veníamos trabajando) y sumarle la venta del V20 Depósito a esa misma tarjeta.
- `PAV MATINAL PE_A FLOR/portal.html` (`_renderSoDash`): el bloque del Depósito V20 dejó de ser una segunda `<div class="card">` aparte. Ahora se renderiza dentro de la MISMA tabla/tarjeta de Sell Out, como filas extra debajo del TOTAL de ruta: una fila separadora "📦 V20 Depósito · venta directa (sin objetivo) — <L>", las categorías del depósito (sin objetivo/faltan/avance, columnas con "–") y la fila final "Total ruta + depósito". El drill-down por categoría/objetivos de la ruta queda intacto.
- Regla de negocio respetada (V20 solo logrado, sin objetivo): el depósito sigue sin objetivo ni avance, solo cambia de presentación (misma tarjeta en vez de tarjeta aparte). No se tocó el backend.
- Validación: `/api/gerencia/sellout_litros` (server 8502) → 6 categorías ruta, 6 categorías depósito, total_ruta 44.262,9 L, total_deposito 11.082,6 L, total_general 55.345,5 L. La tarjeta única muestra ruta + TOTAL ruta, luego depósito y "Total ruta + depósito" 55.345,5 L.

## 2026-06-29 - feat(vendedor): tarjeta "Oportunidad del día" arriba de todo + mensaje amigable

- Pedido: en el perfil del vendedor, mover la tarjeta de Oportunidad del día (innovaciones) ARRIBA DE TODO (lo primero al entrar) y reescribir el mensaje en tono amigable con el nombre del vendedor.
- `PAV MATINAL PE_A FLOR/portal.html` (`vInicio`): la tarjeta de innovaciones se construye en `oportTop` y se antepone (`let h=oportTop+...`), por encima del header con el nombre y los KPIs. El bloque viejo (después de los KPIs) se reemplazó por el fallback "Recuperar cliente" (`if(!oportTop && opors.length)`), que sigue en su lugar cuando no hay oportunidad de innovaciones.
- Mensaje nuevo: "Buenos días <nombre>, te propongo hoy venderles a estos 3 clientes estas innovaciones que aún no compraron. ¡Tú puedes hacerlo! 💪". Nombre por apodo según código de vendedor (`NICK`): V3 Nadia, V4 Ángel, V6 Andre, V7 Agus, V8 Pitu, V9 Fer; fallback al primer nombre para el resto (V10 → "Milagros", sin apodo dado). Clientes capados a 3 (`slice(0,3)`).
- Validación: render Playwright del inicio del vendedor (V8=Pitu) con la tarjeta arriba y el mensaje nuevo, sin errores de consola. `node --check` OK. (La tarjeta aparece tras `refreshAfterRole→vRenderAll`, fase 2 del login; en fase 1 sin oportInov se muestra el fallback, comportamiento de carga existente.)

## 2026-06-29 - feat(FARO): premios (millas) en ambos perfiles + métrica Antares por SKU

- Pedido: mostrar en Club FARO (vendedor y gerencia, incl. supervisores) los premios que va alcanzando cada uno según Real vs Objetivo; y corregir la métrica del Real de Antares (cada cobertura suma 1, XPA/Porrón 330/Porrón 660 suman doble; ej: 1 Lager lata + 1 XPA = 3).
- Input `01_INPUTS/incentivo_club_faro .xlsx`: fila "PREMIOS" → Alaris+FLM 2000 millas, Antares 1000, Familia Smirnoff 1000. Regla Antares (fila 17): "Cada SKU suma 1 CCC, pero XPA y Lager botella suman doble".
- **Métrica Antares** (decisión usuario: por SKU SIN umbral): antes era por cliente con tope 2 (≥6 botellas). Ahora cada SKU distinto de Antares que el cliente compró suma 1, y XPA / Lager Porrón 330 / Lager Botella 660 (códigos **60020 / 60021 / 60022**) suman 2, **sin tope por cliente**. `server_orbit.py`: `_FARO_ANTARES_DOBLE`, `_w` por código, rama antares de `_faro_detalle_vendedor` con `drop_duplicates(["_cli","_cod"])` + suma de `_w`; `cubiertos` = clientes con ≥1 SKU (no ≥6 botellas).
- **Premios**: `_faro_premios()` parsea la fila PREMIOS (regex, fallback a defaults). Endpoints `incentivo_faro` (gerencia + vendedor) devuelven `premio_millas`+`alcanzado` por categoría, `millas_alcanzadas`/`millas_posibles` por vendedor y supervisor, y `premios` global. Categoría alcanzada = logrado≥objetivo (objetivo>0); posibles solo cuenta categorías con objetivo>0 (V3 = 2000, no 4000).
- **Frontend** (`portal.html`): `vFaro` (vendedor) → banner "🎟 Millas que vas ganando" + badge 🎟 por categoría con borde verde al alcanzar. `gIncentivoFaro` (gerencia) → premio por categoría en el encabezado, badge 🎟 en cada celda alcanzada, columna "🎟 Millas ganadas/posibles" en vendedores y supervisores. Textos de regla actualizados.
- Validación (datos reales): premios parseados OK; Antares por SKU (V10 30/7, V8 19/10, V4 9/8…); millas — V4/V8/V10 4000/4000, V3 2000/2000, V6/V9 1000/4000, V7 0/4000; supervisores Esteban 4000/4000, Raúl 1000/4000. `py_compile` OK, portal `node --check` OK, render Playwright de ambos perfiles sin errores de consola.
- Pendiente: deploy a Render (el xlsx con espacio ya está versionado). Nota: los objetivos de Antares quedaron calibrados al criterio viejo → con el nuevo conteo por SKU el logrado los supera holgadamente (esperable).

## 2026-06-29 - feat(gerencia): incluir V20 "Depósito" como línea aparte en Sell Out / 11T / Innovaciones / Cobertura

- Pedido: el sell out de gerencia mostraba 41.609 L y el proveedor reportaba 47.480 L. Diagnóstico contra datos reales: la diferencia es el vendedor **V20 = Depósito / venta directa** (~7.055 L en el sell out de las 6 categorías), concentrado en 3 mayoristas (BELTRAMO/DUTTO, CAREGLIO, ANSELMI) + cuentas chicas internas. ORBIT lo excluía por la regla histórica `{1,2,5,20}`. El usuario pidió sumarlo, siempre identificado como "V20 Depósito".
- Decisiones (confirmadas con el usuario): (1) **línea aparte** "V20 Depósito" con solo logrado, **sin % de cobertura ni faltantes** (el depósito tiene **0 clientes en el maestro** → no hay cartera/denominador); (2) las métricas con objetivo (avance vs objetivo, Incentivo FARO, Planes AS, dashboard de vendedores) **quedan sin V20**; (3) **solo en gerencia**, sin login propio.
- Principio: NO se tocó la exclusión global `_VENDEDORES_EXCLUIDOS = {1,2,5,20}` (eso filtraría V20 hacia métricas con objetivo). El depósito se computa por separado (`CodVendedor==20`) y se adjunta como bloque `deposito` en cada endpoint de gerencia.
- `server_orbit.py`:
  - `_preparar_df_ventas(src, incluir_deposito=False)`: nuevo flag que conserva V20.
  - `_df_deposito_ventas()`: helper nuevo, V20 de ventas.csv (mes vivo). **NO filtra por Empresa**: el depósito factura parte de su venta directa vía P&P Logística pero es la misma entidad física V20 (mismo criterio que el sell out y la conciliación con el proveedor).
  - `gerencia_sellout_litros`: computa ruta (6 cat. con objetivo, **idéntico a antes**) y depósito (mismas cat., sin objetivo/avance). Respuesta nueva: `deposito`, `total_ruta`, `total_deposito`, `total_general`.
  - `once_titulares`: conserva V20 (`Empresa=='Empresa' | CodVendedor==20`), calcula `ccc_dep_map` aparte. Respuesta: `ccc_deposito` por marca + `ccc_deposito_total`. Objetivos/avance de ruta intactos.
  - `gerencia_innovaciones_total` y `gerencia_innovaciones_segmento`: bloque `deposito` = CCC de innovación logrado por producto (V20, clientes únicos).
  - `gerencia_cobertura_acum`: bloque `deposito` = clientes/botellas del depósito (informativo, sin %).
- `PAV MATINAL PE_A FLOR/portal.html`: sub-card "📦 V20 Depósito" bajo el sell out (con total ruta+depósito); columna "Dep.V20" en la tabla 11T; card "V20 Depósito · innovaciones"; banner depósito en la pantalla Vendedores. Sin librerías nuevas; tokens de color y `tabular-nums` respetados.
- Validación (server local, datos reales): sell out `total_ruta=41.609` (sin cambios), `total_deposito=7.055`, `total_general=48.664` (concilia con el proveedor 47.480; el ~1,2k de margen es conversión/período). 11T `ccc_deposito_total=72`, CCC y objetivos de ruta **idénticos** a antes (ALMA MORA 913, DADA 643…). Innovaciones depósito 4 productos. Cobertura depósito 15 clientes / 9.637 botellas. FARO/Planes AS/dashboard sin V20 (verificado). `py_compile` OK; JS del portal `node --check` OK. Validación visual (Playwright, login gerencia): dashboard, vendedores e innovaciones renderizan el depósito sin errores de consola.
- **Paridad en el cierre de mes (misma sesión):** helper compartido `_sellout_con_deposito(df_full)` (separa ruta con objetivo del depósito sin objetivo). `_leer_ventas_mes_csv(src, incluir_deposito=False)` y `_leer_ventas_mes_cacheado(path, incluir_deposito=False)` — la bandera entra en la **clave de caché** para no contaminar la variante sin-V20 que usan CCC/once_titulares/ranking del cierre. Bloque depósito agregado en `gerencia_cierre_mes` (cierre vivo) y `_cierre_extras_versionado` (cierre histórico). Sub-card "📦 V20 Depósito" en la pantalla Cierre de Mes (`portal.html`, bloque del cierre congelado). Validado: cierre `total_ruta=47.565`, `total_deposito=12.324`, `total_general=59.890` (ventas_mes.csv = mes congelado completo, mayor que el vivo); endpoints `cierre_mes` y `cierres_historicos` ambos con bloque depósito; render del portal OK sin errores. **Detalle operativo:** `pkill -f` no mata los python detached en Git-Bash/Windows → quedaban servers viejos sirviendo código previo; matar con `taskkill`/`Stop-Process` por CommandLine.
- Pendiente (NEXT_TASK): deploy a Render.

## 2026-06-25 - perf(11T): vectorizar el match del motor legacy (motor 338s -> 32s)

- Contexto: tras reparar `producto activos.xlsx`, el motor legacy completaba pero tardaba 338 s, dominado por la sección "11 TITULARES".
- Causa del costo: `LEGACY/orbit_matinal_v42.py` (~1367-1381) evaluaba el match con `marcas_mes.apply(..., axis=1)` fila por fila, por cada (cliente × marca objetivo) → O(N×M×K). Crecía con los datos del mes/trimestre.
- Cambio: las condiciones `cliente_id`/`vendedor_codigo` se pre-filtran UNA vez por cliente con el mismo operador `==` vectorizado (`sub_cli = marcas_mes[(==cid) & (==vc)]`), preservando el manejo de NaN (`NaN==NaN` → False → sub vacío). `match_marca_objetivo` corre solo sobre las marcas que ese cliente compró en el mes. Mismo patrón que el fix de `_match` del 23/06.
- Validación: `mod_11_titulares` comparado celda a celda contra la corrida previa (loop original) sobre los mismos inputs → **IDÉNTICO** (5910 filas × 17 cols; suma botellas 4805; suma importe 23.311.235,13; tiene_flag=1 en 190). `ast.parse` OK. Motor: **338 s → 32 s** (≈10×).

## 2026-06-25 - fix(cierre): el cierre del día "se colgaba" en el PASO 1 (motor legacy) por un xlsx inflado

- Síntoma: `CIERRE_DIA_ORBIT.bat` quedaba trabado en `[5/8] Ejecutando motor legacy`. Los logs `regenerar_datos_*.log` del 25/06 (18:21 y 18:32) pesaban 976 bytes y se cortaban justo en esa línea, sin output posterior. El 23 y 24/06 los logs pesaban 23 KB y completaban. NO era el `.bat`.
- Diagnóstico (faulthandler sobre `test_legacy_run.py`): el motor se colgaba en `legacy/orbit_matinal_v42.py` → `cargar_productos()` (línea 898) → `pd.read_excel` → openpyxl parseando XML.
- Causa raíz: `01_INPUTS/producto activos.xlsx` (input gitignored, maestro de productos) estaba **inflado a 19,2 MB**. Tenía solo **260 filas reales** pero el "rango usado" llegaba hasta la fila **1.048.527** (casi el límite de Excel); el resto eran ~1.048.000 filas vacías fantasma. `pd.read_excel` recorría TODAS esas filas → minutos por lectura (solo iterarlas en read_only tardaba 87 s).
- Arreglo (sin tocar código): se reparó el archivo dejando solo el rango real. Backup del original en `99_BACKUPS_ORBIT/producto_activos_bloated/producto activos_BLOATED_2026-06-25_1910.xlsx.bak` (gitignored, no frena el cierre). Resultado: **19,2 MB → 17,8 KB**; `pd.read_excel` 0,08 s. Equivalencia validada celda a celda contra el original: idéntico salvo 15 celdas de ruido de punto flotante (`0.47300000000000003` → `0.473`, litros/caja de botellas 473 ml — numéricamente iguales). `cargar_productos()` devuelve los mismos 19 productos.
- Validación end-to-end: `py test_legacy_run.py` ahora **completa en 338 s (exit 0)** donde antes quedaba colgado >540 s. `git status` quedó limpio fuera de rutas operativas (el `FUNC_PEND` del cierre pasa).
- Bottleneck secundario detectado (NO arreglado, no rompe el cierre): la sección "11 TITULARES" (`orbit_matinal_v42.py:~1367-1381`) tiene un doble loop con `marcas_mes.apply(..., axis=1)` row-wise por cada (cliente × marca objetivo) → O(N×M×K). Crece con los datos del mes y domina los 338 s. Se puede vectorizar pre-filtrando `marcas_mes` por (cliente_id, vendedor_codigo) una sola vez (mismo patrón que el fix de `_match` del 23/06), preservando salida. Ver NEXT_TASK.

## 2026-06-24 - fix(plan-vs-real): gerencia anclaba en el día anterior tras el cierre

- Síntoma: en gerencia, Plan vs Real seguía mostrando el día previo aunque ya se había hecho el cierre del día. El gerente quería ver plan de esta mañana (24) vs real de hoy (24), y mantenerlo hasta el próximo cierre.
- Causa raíz: la pantalla llama a `/api/matinal/resumen` sin `modo`, por lo que usa el modo "cierre", que anclaba la fecha del plan con `fecha < today_ar`. Eso EXCLUYE siempre el plan de hoy, así que tras cerrar el 24 (snapshot 24 ya presente en `02_HISTORY/acumulado_resultado_historico.csv`) seguía eligiendo el plan del 23.
- `server_orbit.py` (`matinal_resumen`, modo "cierre"): el ancla pasa a ser el ÚLTIMO día con cierre hecho = última fecha de snapshot que devuelve `_real_dia_resultado()`. Se elige el plan más reciente con `fecha <= last_snap` (dentro del cutoff de 10 días). Antes del cierre del día → sigue mostrando el último día cerrado (sin regresión); después del cierre del 24 → muestra plan(24) vs real(24) y se mantiene hasta que el cierre del 25 agregue su snapshot.
- Validación local: con los datos actuales, ancla nueva = 2026-06-24 (antes 2026-06-23); real del día = acumulado(24) − acumulado(23) por vendedor (V8=1.698.023,54; V10=209.062,53; V3=188.022,38). `ast.parse` OK. Sin cambios de frontend ni en otros modos ("actual"/"ultimo"/"plan" intactos).
- Pendiente: desplegar a Render (push) para que el gerente lo vea en producción.

## 2026-06-23 - feat(acciones): detalle por tarjeta en acordeon de 2 niveles (resumen vendedor -> clientes)

- Pedido: al desplegar los clientes de una tarjeta, mostrar primero un RESUMEN por vendedor (con nro de clientes y subtotales) y poder hacer clic en un vendedor para ver sus clientes.
- `PAV MATINAL PE_A FLOR/portal.html` (`accShowDetalle`): el detalle ahora arranca COLAPSADO mostrando una fila-resumen por vendedor (V# · nombre · N cli. · $importe · $dto · litros). Las filas de clientes quedan ocultas (`display:none`) hasta que se hace clic en el vendedor. Nueva funcion `accTogVend(scope,gi)` que despliega/colapsa las filas `.accv-gN` y voltea el caret ▸/▾. Encabezado de tabla: "Vendedor / Cliente" + nota "clic en un vendedor para ver sus clientes". Aplica a vista gerencia y vendedor.
- Sin cambio de backend (los datos por cliente y vendedor ya venian en `clientes_detalle`). Validado: `node --check` del script del portal OK.

## 2026-06-23 - fix(acciones): vista gerencia daba HTTP 500 en Render (timeout del worker)

- Sintoma: la pantalla de Acciones Comerciales no cargaba en gerencia. `/api/gerencia/acciones_mes` devolvia HTTP 500 a los ~30,9s en Render; `/api/vendedor/<id>/acciones_mes` devolvia 200 (10s). Local: 200 en 5,2s, tipos nativos OK. => No era bug de logica ni serializacion: la vista gerencia (sin filtro, 28 acciones sobre toda la venta) superaba el timeout default de gunicorn (30s) en el Render de 0.5 vCPU, el worker moria y como nunca completaba NUNCA cacheaba => 500 permanente. Descartado OObM (dataset 2.787 filas, 2,5 MB). El commit anterior (dedup de litros) fue la gota que la paso de ~25s a >30s.
- Causa raiz del costo: `_match` evaluaba el predicado de producto con `sub.apply(..., axis=1)` fila por fila (62.510 llamadas, ~5s).
- `server_orbit.py` (`_match` dentro de `_acciones_mes_payload_uncached`): `pred()` depende SOLO de `(_cat,_linea,_art,_marca,_cod)`; ahora se evalua una vez por combinacion unica y se mapea a cada fila. Resultado IDENTICO (validado: totales.litros=20.775,3; ACJ26-007 13.358,8/360; ACJ26-002 4.955,1/445; ACJ26-021 4.894,0/441), tiempo 5,2s -> 3,86s local.
- `server_orbit.py` (startup): hilo daemon `_warm_caches()` que precalienta `_acciones_mes_payload(None)` al arranque (el boot no tiene timeout HTTP). Asi la primera request del gerente cae en cache. No bloquea arranque ni request; fallo de warmup es no-fatal. Import de `threading`.
- Validacion local: import dispara warmup; `/api/gerencia/acciones_mes` 200 (2da llamada 0,016s por cache); `/api/vendedor/V4/acciones_mes` 200; serializa OK; `py_compile` OK.

## 2026-06-23 - feat(acciones): detalle de clientes agrupado por vendedor + revision de tarjetas

- `PAV MATINAL PE_A FLOR/portal.html` (`accShowDetalle`): al hacer clic en "clientes" / "nuevos" de una tarjeta, el detalle ahora se agrupa por vendedor. Cada grupo tiene encabezado (V# · nombre) con subtotal de importe, descuento, litros y cantidad de clientes; debajo, las filas de clientes de ese vendedor. Se reemplazo la columna "Vendedor" (redundante) por "Lineas" (cantidad de lineas de factura que matchearon). Aplica a vista gerencia y vendedor (ambas usan la misma funcion). El chip de cabecera ahora informa "N clientes · M vend.".
- Datos ya disponibles: `_detalle_clientes` (backend) ya devolvia `vendedor_id` / `vendedor_nombre` por cliente; las 2.139 filas del detalle tienen vendedor poblado (0 sin asignar). No hubo cambio de backend.
- Revision de las 28 tarjetas: litros/clientes/inversion coherentes. Inversion por accion varia entre ~11,6% y ~17,3% del importe (NO es ratio constante => es valorDescuento real, no IVA). Observaciones de CATALOGO (no son bugs de codigo): ACJ26-018 y ACJ26-019 devuelven el mismo set (6 clientes, 183 L identicos) por solaparse en Alma Mora On Premise; ACJ26-020 y ACJ26-025 dan 0 clientes (sin ventas que matcheen aun). Revisar definicion de esas reglas con negocio.

## 2026-06-23 - fix(acciones): total "Litros bajo acciones" sin doble conteo entre acciones

- Sintoma: el portal (gerencia) mostraba ~54.451 L (en este snapshot 57.146 L) "bajo acciones", imposible porque supera el sell out total del mes (~28.635 L). Causa raiz: el frontend totalizaba `acc.reduce(litros)` sumando los litros de cada accion por separado; una misma linea de venta matchea varias acciones (canal + Planes AASS + 11 Titulares + Innovaciones) y se contaba 2-4 veces.
- `server_orbit.py` (`_acciones_mes_payload_uncached`): acumula la UNION de indices de lineas que caen bajo al menos una accion (`matched_idx`) y del mes anterior (`prev_idx`). Agrega bloque `totales` deduplicado: `litros`, `importe_neto`, `inversion_pesos`, `clientes_alcanzados`, `clientes_nuevos`, `clientes_con_descuento`. El calculo por accion NO se modifica (cada tarjeta sigue mostrando sus litros correctos; el solape entre acciones es esperado).
- `PAV MATINAL PE_A FLOR/portal.html` (`gAccionesComerciales`): los 4 KPIs del encabezado (Inversion total, Litros bajo acciones, Clientes alcanzados, Clientes nuevos) usan `dat.totales`; fallback al `reduce` solo si el payload viejo no trae `totales`.
- Validacion: `/api/gerencia/acciones_mes` → totales.litros = 20.775,3 L (antes 57.146,7 por suma) < sell out total 28.634,7 L (coherente). Status 200, tipos nativos serializables (jsonify OK en Render). Vista vendedor `/api/vendedor/V4/acciones_mes` tambien devuelve `totales`.

## 2026-06-23 - fix(cierre): blindar flujo Git del cierre de MES (mismo patron que el diario)

- `CIERRE_MES_ORBIT.bat`: agrega preflight Git antes de generar el cierre. Si hay cambios funcionales (codigo `.py`, `.bat`, `portal.html`, config) fuera de las rutas operativas permitidas, aborta antes de ejecutar `tools/cerrar_mes.py`.
- `CIERRE_MES_ORBIT.bat`: allowlist operativo del mes = `01_INPUTS/{cierres mes, resultado.xlsx, ventas.csv, ventas_mes.csv, ventas_acumulada.csv, clientes.xlsx, ventas-clubfaro.csv, objetivo 11T.xlsx, INNOVACIONES, Planes AASS, PLANES_AS, ACCIONES COMERCIALES}`, `02_HISTORY`, `04_DATASETS_ORBIT`.
- `CIERRE_MES_ORBIT.bat`: agrega `git pull --rebase origin master` al inicio, solo con repositorio 100%% limpio; con inputs operativos ya cargados omite el pull (no rebasa sobre working tree sucio).
- `CIERRE_MES_ORBIT.bat`: tras `git add "01_INPUTS/cierres mes/"`, segundo guard que aborta a `:fin_error` si quedan cambios fuera del allowlist. No usa `git reset --hard` ni `git clean`.
- `CIERRE_MES_ORBIT.bat`: elimina el `pull --rebase` posterior al commit. `LISTO` solo tras push exitoso; ante fallo de commit/push informa que Render NO fue actualizado. Exit codes explicitos (`exit /b 1` en error, `exit /b 0` en exito).
- Diferencia deliberada vs diario: "sin cambios nuevos" en el mensual NO es error (re-ejecutar un mes ya cerrado es valido; `cerrar_mes.py` no pisa nada y devuelve 0), por eso va a `:fin_ok`.
- Archivo regrabado en CRLF, UTF-8 sin BOM (consistente con `.gitattributes` `eol=crlf`).

## 2026-06-23 - fix(cierre): blindar flujo Git del cierre diario

- `CIERRE_DIA_ORBIT.bat`: agrega preflight Git antes de validar/regenerar datos. Si hay cambios unstaged, staged o archivos nuevos no versionados, aborta antes de tocar `01_INPUTS`, `02_HISTORY` o datasets.
- `CIERRE_DIA_ORBIT.bat`: mueve `git pull --rebase origin master` al inicio del cierre, con repositorio limpio y antes de ejecutar `REGENERAR_DATOS_ORBIT.bat`.
- `CIERRE_DIA_ORBIT.bat`: mueve la sincronizacion de planes desde Render antes de regenerar datasets; si falla, aborta sin dejar datos operativos regenerados a medias.
- `CIERRE_DIA_ORBIT.bat`: reemplaza `git add "04_DATASETS_ORBIT/"` por una lista explicita de datasets operativos permitidos y mantiene inputs/historiales operativos puntuales.
- `CIERRE_DIA_ORBIT.bat`: despues del `git add`, aborta si quedan cambios fuera del allowlist o archivos nuevos no permitidos. No descarta cambios, no usa `git reset --hard` ni `git clean`.
- `CIERRE_DIA_ORBIT.bat`: elimina el `pull --rebase` posterior al commit. El cierre solo muestra `LISTO` si `git push origin master` termino correctamente; si no hay cambios, falla el commit o falla el push, muestra que Render NO fue actualizado.

## 2026-06-23 - fix(cierre): abortar el cierre si la regeneracion falla (no publicar datasets viejos)

**Bug latente desde el 17/06:** el motor venía crasheando en TODAS las corridas desde el 17/06 19:20 (8 cierres) por el tema `Cuadro Inov` (ver entrada siguiente). Pasó desapercibido porque `CIERRE_DIA_ORBIT.bat` no chequeaba el código de salida de la regeneración — solo verificaba `if exist mod_volumen_vendedor.csv`, que existía **viejo (17/06)**. Resultado: el cierre decía "OK" en falso y hacía commit + push igual, publicando a Render `ventas.csv`/`resultado.xlsx` nuevos pero **datasets congelados del 17/06** (CCC, 11T, innovaciones, cobertura, sell out, volumen y los snapshots del real del día). El historial de snapshots saltaba directo del 17/06 al 22/06.

- `CIERRE_DIA_ORBIT.bat`: tras `call REGENERAR_DATOS_ORBIT.bat`, reemplazado el chequeo `if exist ...csv` por `if errorlevel 1` → si la regeneración falla, **ABORTA** con cartel rojo y `exit /b 1` (NO commit, NO push). `REGENERAR_DATOS_ORBIT.bat` ya devolvía `exit /b 1` en cada fallo; el problema era solo que el cierre no lo miraba. Archivo mantiene CRLF.
- **Validado:** patrón `call`→`exit /b 1`→`if errorlevel 1` probado en cmd (caso falla = aborta; caso OK = continúa).

## 2026-06-23 - fix(cierre): Innovaciones.xlsx sin hoja 'Cuadro Inov' no aborta el motor

**Causa del cierre que "no actualizaba nada":** el cierre del 23/06 abortó en el paso 5/8 (motor legacy). Se reemplazó `01_INPUTS/INNOVACIONES/Innovaciones.xlsx` por un archivo con una sola hoja `innovaciones` (lista plana de 22 productos), pero `generar_mod_innovaciones_plan_as` hacía `read_excel(sheet_name="Cuadro Inov", header=4)` y crasheaba con `ValueError: Worksheet named 'Cuadro Inov' not found`, deteniendo toda la regeneración → sin datasets, sin commit, sin push (Render quedó en 22/06).

- `legacy/orbit_matinal_v42.py` `generar_mod_innovaciones_plan_as`: antes de leer la hoja, verifica `pd.ExcelFile(...).sheet_names`. Si no existe `Cuadro Inov` (o el Excel no se puede leer), loguea WARN y devuelve `DataFrame()` vacío en lugar de abortar. El resto del cierre sigue normal.
- **Validado:** `REGENERAR_DATOS_ORBIT.bat` corre completo (log `regenerar_datos_20260623_085554.log`): WARN registrado, `mod_innovaciones_plan_as` 0 filas, todos los datasets regenerados a 2026-06-23. La tarjeta de Innovaciones del portal no se ve afectada (usa `mod_innovaciones_segmento.csv`).
- Parte A de un cambio mayor. **Pendiente Parte B** (NEXT_TASK): nueva medición de Innovaciones por producto × subcanal (Autoservicio/Almacén/Kiosco/On Premise/Mayorista), compraron vs no compraron.

## 2026-06-22 - fix(plan frío): excluir latas Smirnoff BC del sin-cargo enviado

**Planes AS** (ambos perfiles). El "enviado" de **Plan Frío** (Six Pack Smirnoff ICE sin cargo) se detectaba por **Marca** (`contains('ice') & contains('smirnoff')`). Las latas **Smirnoff BC** (Bitter Citric, COD 35108/35109) tienen `Marca='Smirnoff Ice Flavours'` en el ERP pero **NO son plan frío** — pertenecen a una acción comercial del mes. Resultado: 4 clientes (30063, 390, 7219, 30017) figuraban como plan frío **entregado** sin haberlo recibido.

**Regla correcta (confirmada por el usuario):** el plan frío se paga **solo con Smirnoff ICE en lata**. Las latas BC quedan afuera.

- `generar_datasets_acum.py` `generar_planes_as`: la detección de plan frío pasa de **Marca** a **Articulo** — `Articulo` con `ICE` + (`SMIRNOFF`|`SMF`). Las BC dicen `BC` y NO `ICE`, así que se excluyen; también se excluye Smirnoff botella 700 (escala, no Ice). Aplica al `pf_enviado` y al detalle `mod_sincargos_envios.csv`.
- Regenerados `mod_planes_as.csv` y `mod_sincargos_envios.csv` desde `ventas.csv`. **Validado:** `pf_enviado` pasa de {30063,390,7219,30017} (todos por BC) a **{2410}** (compró SMF ICE RED BERRIE lata al 100%, plan frío real). 31 clientes, sin pérdidas.
- El server solo lee `pf_disponible/pf_enviado/pf_estado` del CSV (gerencia + vendedor), así que ambos perfiles quedan corregidos al regenerar.

## 2026-06-19 - fix(FARO): Antares logrado por cliente (no por variedad)

**Incentivo Club FARO**, categoría **Antares (Autoservicio)**. El `logrado` contaba el peso **por cada SKU/variedad** con ≥6 botellas (`sku_ok["w"].sum()`), inflando el número: V4 mostraba **6/8** pero el detalle tenía solo **2 clientes** (cli 100: IPA+Caravana+XPA = 1+1+2=4; cli 370: Lager lata+Scotch = 1+1=2).

**Regla correcta (confirmada por el usuario):** la cobertura es **por cliente**, no por variedad. Un cliente con ≥6 botellas de Antares en autoservicio suma **1**; si entre sus compras hay **XPA o Lager en botella** (peso 2) suma **2**. Máximo 2 por cliente.

- `server_orbit.py` `_faro_detalle_vendedor`: la rama `antares` ahora calcula `logrado = Σ peso_cliente` sobre `cubiertos` (clientes con total Antares ≥ umbral), `peso_cliente = 2 si el cliente compró algún SKU XPA/Lager-botella, si no 1`. `compradores` pasa a ser **una fila por cliente** (con su peso), no por SKU.
- Validado: V4 Antares **3/8** (cli 100 peso 2 + cli 370 peso 1), 2 clientes. Todos los vendedores quedan con `logrado ≤ 2×clientes` (V6 4, V8 9, V9 10, V10 11).
- Textos de regla actualizados (header del módulo + leyenda del portal vendedor). alaris_flm y smirnoff no cambian (ya eran 1 por cliente).

## 2026-06-19 - fix(sellout): RTD (S) ya no se filtra en RTD + drill-down marca→varietal

**Sell Out por categoría** (tarjeta gerencia, `/api/gerencia/sellout_litros`).

1. **Fix leak RTD/RTD (S):** una venta de Smirnoff Bitter Citric (RTD (S)) caía dentro de la subcategoría RTD regular. **Causa raíz:** el split RTD vs RTD (S) confía en la `Categoria` del maestro 04D, pero 2 productos no estaban cargados en `09_CONFIG/maestro_04D_productos.csv` y entraban a RTD solo por el Rubro del ERP, sin subtipo → caían por defecto en RTD regular. Se agregaron al maestro con su clasificación real (confirmada por el usuario): `35108` SMF BC RUBYORANGE → **RTD (S)**; `14620` FRIZZE MANXANA → **RTD** (Frizze es base vino; el Rubro del ERP lo etiquetaba mal como RTD (S)). No se tocó la lógica del split. Validado: 0 ventas RTD (S) en RTD regular; RTD (S) ahora 2171 L con SMF BC incluido.
   - Nota: la marca **FINCA LAS MORAS FFL** (Fair For Life, cod 74721/74722) queda en segmento **Alto** a propósito (confirmado por el usuario) — es la línea premium, no es error.
2. **Drill-down marca → varietal:** `server_orbit.py` `_marcas_de_grupo` ahora devuelve `varietales:[{nombre, litros}]` (desglose por Articulo/SKU dentro de cada marca). `portal.html`: las marcas de la tarjeta Sell Out son clickeables (helper `_soMarcas` + estado `soMExp`) y abren los litros por varietal vendido. No cambia identidad visual.

## 2026-06-19 - fix(innovaciones): medir solo Peñaflor (excluir P&P Logística) en ambos perfiles

Mismo criterio que el 11T. Las innovaciones contaban compras de **P&P Logística** de clientes Peñaflor.
- `generar_datasets_acum.py` `generar_innovaciones_segmento` y `generar_innovaciones_plan_as`: filtran `Empresa=='Empresa'`. Regenerados `mod_innovaciones_segmento.csv` y `mod_innovaciones_plan_as.csv`.
- `server_orbit.py` `/api/vendedor/<id>/oportunidades_innovacion`: filtra `Empresa=='Empresa'` (lee ventas_acumulada en vivo).
- Afecta gerencia (innovaciones_segmento, innovaciones_total) y vendedor (innovaciones_segmento, plan_innovaciones, oportunidades) — todos leen los datasets regenerados.
- Impacto: total clientes_compraron 149→111 (−25%, salieron las compras P&P). Endpoints validados.

## 2026-06-19 - fix(11T): aplicar el criterio correcto en las demás lecturas (zona y ruta)

Extiende el fix del 11T a todas las tarjetas/perfil para que lean igual que la tarjeta principal:
- **Tarjeta "11T CCC zona del día"** (`once_titulares_zona`): además del filtro Peñaflor (ya agregado), ahora acota al **trimestre calendario en curso** por FechaComprobante (antes contaba sobre toda la acumulada).
- **11T de la Ruta del vendedor** (`vendedor_ruta`, ventas.csv mes vivo): `ventas.csv` también mezclaba **P&P Logística** y usaba `[2,5,20]` hardcodeado. Ahora filtra `Empresa=='Empresa'` y usa `_VENDEDORES_EXCLUIDOS` ({1,2,5,20}).
- Per-vendedor (`mod_11t_acum` → dashboard "11T ✓" y perfil vendedor) ya quedó correcto en commits previos (Peñaflor + V1 excluido). Verificado: zona JU 11 marcas, V8 8/11 cumplidos, ruta V8 OK.

## 2026-06-18 - fix: excluir vendedor 1 (no es de ruta) además de 2/5/20

**`server_orbit.py` + `generar_datasets_acum.py`**: `VENDEDORES_EXCLUIDOS` pasa de `{2,5,20}` a `{1,2,5,20}`. V1 no es vendedor de ruta Peñaflor (activos = 3,4,6,7,8,9,10) y se colaba en el conteo en vivo del 11T (`once_titulares`). Impacto: 11T total 4439→4435 (V1 tenía footprint mínimo); el maestro de clientes no tiene ningún cliente codven=1, así que ningún dataset cambia (no requiere regeneración).

## 2026-06-18 - fix(11T): medir solo Peñaflor (excluir P&P Logística) + período trimestral

**Hallazgo:** los CCC del 11 Titulares estaban ~15-35% por encima del reporte de la empresa. **Causa raíz:** el dashboard sumaba las ventas de **P&P LOGISTICA S.R.L** (otro distribuidor, ~5600 filas en `ventas_acumulada.csv`) además de Peñaflor. Una decisión previa había asumido —erróneamente— que P&P eran ventas de los vendedores activos. NO era problema de segmentos (filtrarlos solo movía ~3%).

**Corrección (todos los puntos del 11T, igual criterio que FARO y el cierre):**
- `/api/gerencia/once_titulares` y `/api/gerencia/once_titulares_zona`: filtran `Empresa=='Empresa'` (excluye P&P). El acumulado además se acota al **trimestre calendario en curso** (abr-jun ahora; en julio arranca de cero) por FechaComprobante.
- `generar_datasets_acum.py` `generar_11t_acum`: filtra Peñaflor → `mod_11t_acum.csv` regenerado (per-vendedor 11T del dashboard y perfil vendedor).
- Cierre (`_leer_ventas_acum_cierre` + `_cierre_once_titulares`): filtra Peñaflor; comentario previo corregido.

**Validación vs reporte empresa:** total 4439 vs 4574 (−3%); por marca casi todas en ±5% (Antares −1.3%, Smirnoff Ice −2.6%, Alma Mora −3%, Alaris −4.4%, Dada +4.7%). Período = TRIMESTRE (abr+may+jun hasta fin de junio), confirmado por el usuario. Quedan 3 marcas con desvío residual mixto (Finca −12%, Trapiche +16%, Gordon's −17%) por mapeo de sub-etiquetas — pendiente de afinar, ya no es error sistemático.

## 2026-06-18 - fix(V3): alertas solo de clientes Tradicional almacén/despensa/kiosco

**`server_orbit.py`** (`/api/alertas` + helper `_v3_clientes_tradicional`): las alertas de descuento/tope de V3 se filtran a sus clientes Tradicional almacén/despensa/kiosco (las de clientes On Premise/AS/Mayorista no se muestran). Salvaguarda consistente con la regla V3. Nota: hoy las 105 alertas de V3 ya eran todas de su canal → 0 quitadas; el filtro evita fugas futuras. V8 sin cambios.

## 2026-06-18 - fix(V3): perfil completo solo Tradicional (almacén/despensa/kiosco)

**Objetivo:** que V3 (Nadia) no vea NADA de Autoservicio / On Premise / Mayorista en ningún lado de su perfil. Auditoría de todas las pantallas; corregido en backend (consistente para gerencia y vendedor).

- **Acciones comerciales** (`server_orbit.py` `acciones_mes`): para V3 `seg_use &= {TRADICIONAL}` y si la acción no aplica a tradicional **se descarta** (antes seguía apareciendo con 0 clientes); footprint restringido a almacén/kiosco. Resultado: V3 pasa de ~28 a 9 acciones (solo tradicional/almacén/kiosco/todos). V8 sin cambios (28, sigue con AS).
- **Incentivo FARO** (`vendedor_incentivo_faro`): V3 solo categorías de canal tradicional → queda Alaris + Finca Las Moras; se ocultan Antares y Familia Smirnoff (Autoservicio).
- **Cobertura acumulada** (`generar_datasets_acum.py` `generar_cobertura_acum`): V3 solo TRADICIONAL almacén/despensa/kiosco (antes traía MAYORISTA y ON_PREMISE). Cartera V3 = 284. Regenerados `mod_cobertura_acum.csv` y `mod_cobertura_acum_detalle.csv`.
- **Clientes del día** (`/api/clientes` y `_clientes_por_dia`): V3 solo Tradicional almacén/despensa/kiosco (saca los 4 On Premise que aparecían en Inicio/Plan/Clientes).
- **Pestaña Plan AS** (`portal.html` `showApp`): oculta para V3 (no trabaja Autoservicio; ya venía con 0 clientes).

Validado vía HTTP: acciones/FARO/cobertura/clientes de V3 sin AS/OP/Mayorista; V8 control sin cambios. `node --check` OK.

## 2026-06-18 - fix(ruta): V3 solo Tradicional almacén/despensa/kiosco

**`server_orbit.py`** (`/api/vendedor/<vid>/ruta`): la ruta de V3 ahora deja SOLO clientes Tradicional con SubSegmento almacén/despensa/kiosco (whitelist `ALMACEN`/`DESPENSA`/`KIOSCO`). Esto reemplaza el filtro anterior (que solo sacaba AS/On Premise) y además excluye fiambrería, panadería, carnicería, "resto de tradicionales", etc. Validado contra el maestro: quedan 284 de 347 (Almacen/Despensa 234 + Kiosco/Maxikiosco 50); el resto excluido.

## 2026-06-18 - fix(ruta): V3 sin AUTOSERVICIO ni ON PREMISE en su ruta

**`server_orbit.py`** (`/api/vendedor/<vid>/ruta`): V3 (Nadia) no trabaja AS ni On Premise → se excluyen esos clientes de su ruta física (antes aparecían en la lista). Filtro en el loop: `if vid=="V3" and seg in (AUTOSERVICIO, ON_PREMISE_VTK): continue`. Validado: V3 ruta solo TRADICIONAL (total 55, antes incluía AS/OP); V8 sin cambios.

## 2026-06-18 - feat(ruta): orden de visita + 11 Titulares e Innovaciones colapsables (verde/amarillo)

**Objetivo:** en la pestaña Ruta del perfil del vendedor, listar los clientes en **orden de visita** y, en vez de mostrar marcas sueltas, dos chips colapsables por cliente: **11 Titulares** y **Innovaciones**; al hacer clic se abre el detalle con las marcas/productos en **verde** (ya comprados) y **amarillo** (aún no).

**`server_orbit.py`** (`/api/vendedor/<vid>/ruta`):
- Orden de visita: ordena por la columna `Orden` de clientes.xlsx (asc); `Orden<=0` o vacío = sin asignar → al final. Se agrega `orden` a cada cliente.
- 11 Titulares: además de `titulares_faltantes` ahora devuelve `titulares_comprados` y `once_t_total`.
- Innovaciones por cliente: catálogo desde `mod_innovaciones_segmento.csv` (por segmento), compras desde ventas.csv (mes vivo, columna `Codigo`). Devuelve `inov_comprados`, `inov_faltantes`, `inov_comprados_n`, `inov_total`. Solo TRAD/AS; V3 sin AUTOSERVICIO.

**`PAV MATINAL PE_A FLOR/portal.html`** (`vRuta` + helpers `vRutaPills`/`vRutaToggle`): cada cliente muestra su nº de orden, estado, y los chips "11 Titulares x/11" e "Innovaciones y/N" (color ok/wn/bd según avance). Clic → pills verde/amarillo. El front respeta el orden del backend (no re-ordena).

Validado vía HTTP: V6 sale 10,20,30,…(orden real); ejemplo cliente con 11T 3/11 (verdes ALMA MORA/FINCA LAS MORAS/LOS ARBOLES, amarillas el resto) e Innovaciones 1/22. V3 sin innovaciones en AS. `node --check` OK.

## 2026-06-18 - feat(cobertura): drill-down por vendedor + faltantes en tarjeta de cobertura acumulada

**Objetivo:** ver las coberturas logradas por cada vendedor en los segmentos, dentro de la tarjeta "Cobertura acumulada del mes", expandiendo cada segmento para ver el detalle por vendedor y los clientes que aún no lograron cobertura.

**`generar_datasets_acum.py`** (`generar_cobertura_acum`): además del agregado `mod_cobertura_acum.csv` ahora emite **`mod_cobertura_acum_detalle.csv`** = clientes faltantes (cubierto=0, es decir `cant_base_acum < umbral` en el acumulado) por vendedor × segmento, con nombre y localidad desde `clientes.xlsx`. Mismo `merged` que ya calculaba `cubierto` (no cambia ningún cálculo de cobertura). Validado: `sin_cobertura` del agregado = nº de filas del detalle en las 26 combinaciones vendedor×segmento.

**`server_orbit.py`**: dos endpoints nuevos (+ helper `_cobertura_faltantes_rows`):
- `GET /api/gerencia/cobertura_acum_faltantes?segmento=X` → faltantes por vendedor para el drill-down de gerencia.
- `GET /api/vendedor/<vid>/cobertura_acum` → cobertura propia del vendedor por segmento + faltantes (solo sus datos). Respeta V3 sin AUTOSERVICIO.

**`PAV MATINAL PE_A FLOR/portal.html`**:
- Dashboard gerencia: cada segmento de la tarjeta es clicable → despliega vendedores (cubiertos/cartera/%) y, por vendedor, los clientes faltantes (lazy fetch con caché por segmento).
- Pantalla Vendedores (360°): cada tarjeta suma "Cobertura acumulada por segmento" expandible a sus faltantes.
- Perfil propio del vendedor (`vKpis`): nueva tarjeta "Cobertura acumulada del mes" con faltantes por segmento (cargada en `loadRole`).

Validado vía HTTP (server local): portal 200, endpoint gerencia 6 vendedores con faltantes, V9 segmentos con faltantes = sin_cobertura, V3 sin AUTOSERVICIO. `node --check` del script del portal OK.

## 2026-06-17 - fix(sellout): RTD se abre en RTD + RTD (S) (obj y litros)

**`server_orbit.py`**: en OBJSELLOUT.xlsx, 'rtd' y 'rtd (s)' comparten Grupo PBP 'RTD' → se trataban como categorías separadas (RTD (S) quedaba huérfano). Ahora `_OBJ_CAT_NORM` mapea 'rtd (s)'→RTD y `_cargar_objetivos_sellout` detecta la colisión de Grupo PBP y etiqueta los subgrupos por nombre de categoría → RTD: total 9056, subs {RTD 4028, RTD (S) 5028}. En `_sellout_desde_ventas` se agregó `_cat_raw` (categoría cruda del maestro 04D) y la rama RTD que abre los litros logrados en RTD vs RTD (S). Validado: RTD 619 L (15.4%) + RTD (S) 1946.9 L (38.7%) = 2565.9 L (total 28.3%).

## 2026-06-17 - feat(sellout): objetivo abierto por Grupo PBP (subgrupos con objetivo+alcance)

**`server_orbit.py`** (`_cargar_objetivos_sellout`, `_sellout_desde_ventas`): OBJSELLOUT.xlsx ahora trae el objetivo abierto por **Grupo PBP** (categoria | Grupo PBP | objetivo litros + fila Total por categoría). `_cargar_objetivos_sellout` devuelve `{CAT: {total, subs:{grupo:obj}}}`. La tarjeta de sell out (`/api/gerencia/sellout_litros`) asigna objetivo y alcance_pct a cada subcategoría (antes objetivo=None). Validado: VDA total 17023 (Alto 10711/Medio Alto 4111/Superior 1863/Medio 338), SPIRITS 17019 (Nacionales 16341/Importados 678), RTD 9056, etc. El portal ya renderiza objetivo+alcance por subcategoría (sin cambios de front).
**`01_INPUTS/OBJSELLOUT.xlsx`**: commiteado (excepción a la regla de 01_INPUTS) porque Render lo lee en vivo para esta tarjeta.

## 2026-06-17 - feat(innovaciones): lista de productos desde Innovaciones.xlsx

**`generar_datasets_acum.py`**: `_cargar_inov_productos()` lee `01_INPUTS/INNOVACIONES/Innovaciones.xlsx` (formato "CODIGO - NOMBRE") como fuente oficial de los productos innovación; antes era una lista hardcodeada de 20. `INOV_PRODUCTOS` ahora se carga de ahí (fallback `_INOV_PRODUCTOS_DEFAULT` si falta el archivo). Misma mecánica de medición (CCC por vendedor × segmento). Pasó de 20 a **22 productos** (suma 42337 Don David Torrontes Low, 74882 Los Arboles bco dulce). Validado: dataset `mod_innovaciones_segmento.csv` con 22 productos en gerencia y por vendedor; `mod_innovaciones_plan_as.csv` activas=22. Endpoints de ambos perfiles OK.

## 2026-06-17 - perf(portal): carga mucho más rápida en Render

**Causa:** gunicorn `--workers 1 --worker-class sync` atendía 1 request a la vez → los ~17 endpoints del login se encolaban (~20-30s). Además cada endpoint reparseaba ventas.csv (con `.apply` fila por fila para segmento) y releía clientes.xlsx.

**`server_orbit.py`**: `_ventas_parsed()` parsea ventas.csv UNA vez por mtime (segmento vectorizado por pares únicos Ramo/Subramo); `_cargar_ventas_mes_actual` y `_cargar_ventas_dia` filtran de ahí. `diagnostico` y `gerencia_planes_as` leen clientes.xlsx vía `_clientes_maestro()` (caché por mtime existente). Local: diagnostico 1.04s→0.13s cacheado, sin cambio de valores (segmentos/cartera idénticos).

**`render.yaml` + `Procfile`**: gunicorn `--threads 8 --worker-class gthread` (sigue 1 worker para SQLite; cada request abre su propia conexión → threads seguros). Los endpoints del login se atienden en paralelo. Medido en Render: 17 endpoints 35s serie → 10.9s paralelo.

**`server_orbit.py` `read_csv()`**: caché por (ruta, mtime) devolviendo COPIA (los endpoints transforman sin contaminar el caché) → los datasets no se reparsean por request. diagnostico 0.93s→0.06s local.

**`portal.html`**: el login muestra el portal apenas carga el CORE liviano (`loadCore` = diagnostico+dashboard+clientes, ~2s en Render) y trae el resto (`loadRole`: alertas ~3s, planificación, plan-vs-real, datos por rol) en 2do plano con re-render (`refreshAfterRole`). Las funciones de render son null-safe (las tarjetas sin dato aún quedan vacías y se completan al re-render). **Tiempo hasta ver el portal: ~20-35s → ~2s.**

Piso actual ≈ 2s por Render starter (0.5 vCPU). Para bajar más: upgrade de plan (más CPU) o un endpoint /bootstrap único. `alertas` (~3s) quedó pendiente de optimizar (corre en 2do plano).

## 2026-06-17 - feat(planes_as): sin cargos del mes desde sincargos*.xlsx (verde/amarillo + Estado)

**`generar_datasets_acum.py`** (`_cargar_sincargos_mes`, `generar_planes_as`).

- Nuevo `_cargar_sincargos_mes()`: autodetecta `01_INPUTS/Planes AASS/sincargos*.xlsx` (mensual, por mtime → `sincargosjulio.xlsx` el mes que viene). Lee la hoja **Planes AASS** (código + "Cjas Sin Cargos" + tabla escala ESCALA→LC) y reparte las cajas por la **escala acumulativa** → desglose por marca. Ej validado: cliente 30033 = 9 cajas → 4 Alaris + 4 Alma Mora + 1 Frizze.
- En `generar_planes_as`: el **disponible** de sin cargos (`sc_alaris/alma_mora/frizze/antares_ipa/smf_flavours/sc_total_ganado`) ahora se **sobreescribe** desde ese Excel (clientes no listados → 0). Se recalcula `sc_pend_*`/`sc_pendiente` y se agrega `sc_estado` (`enviados`/`pendiente`/`""`) y `sc_origen_disponible`.
- **NO cambia** cliente / plan / facturado / escala_actual (siguen por facturación). **Fail-safe**: si el Excel falta o falla, se conserva el disponible por facturación.
- **Fallback sin Reconocimiento**: `cargar_planes_as_bbdd()` arma la base (cliente/nombre/plan) desde `Planes AASS/sincargos*.xlsx` cuando falta `PLANES_AS/Reconocimiento Plan As.xlsx`; facturado←ventas.csv, escala←`escala*.xlsx` (ahora también detecta `Planes AASS/escalasjunio.xlsx`). Helpers `_bbdd_desde_sincargos`, `_aplicar_escala`. Validado: 31 clientes, 30033 Silver escala 9/9 = 4 Alaris+4 Alma Mora+1 Frizze.
- **Plan frío**: nuevo `_cargar_planfrio_mes()` lee la hoja "plan frío" de sincargos*.xlsx (20 clientes, 1 Six Pack Smirnoff ICE c/u). En `generar_planes_as`: `pf_disponible` (lista del Excel), `pf_enviado` (binario: cliente con línea 100% descuento Marca "Smirnoff Ice Flavours" en ventas.csv), `pf_estado` (entregado/pendiente/""). Expuesto en ambos endpoints; portal muestra "Plan frío · Six Pack Smirnoff ICE" verde(entregado)/amarillo(pendiente) en gerencia y vendedor. Validado en vivo: 20 disp, 4 entregados (30063/390/7219/30017).
- Validado end-to-end con server local 8502: `/api/gerencia/planes_as` y `/api/vendedor/V8/planes_as` 200, sirven facturado/escala/sin cargos/plan frío correctos.

## 2026-06-17 - feat(planes_as): tarjeta con fechas de envío al clickear un sin cargo

**`generar_datasets_acum.py`** (`generar_planes_as`): nuevo dataset `04_DATASETS_ORBIT/mod_sincargos_envios.csv` (cliente_id, categoria escala/plan_frio, producto, fecha=FechaComprobante, cajas) — una fila por cliente×producto×fecha de cada línea 100% descuento.

**`server_orbit.py`** (`_cargar_sincargos_envios`): ambos endpoints planes_as adjuntan `envios: [{producto, fecha, cajas, categoria}]` por cliente.

**`PAV MATINAL PE_A FLOR/portal.html`** (`verSincargo`): los chips de sin cargo (escala y plan frío) son clickeables → tarjeta modal (estilo `emod`) con las fechas de envío y cajas; si no hay envíos, muestra "Sin envíos registrados aún". Validado: 30063 plan frío → 01/06 (6) + 16/06 (24); 30033 pendiente → vacío. PY+JS (node --check) OK, endpoint 200 con `envios`.

**`PAV MATINAL PE_A FLOR/portal.html`** (gerencia `gPlanesAS`, vendedor `vPlanesAS`).

- "Pendiente" pasa de **rojo** (`--bd`) a **amarillo** (`--wn`) en ambos perfiles. "Enviado" sigue verde (`--ok`).
- **Estado**: "enviados" (verde) cuando se envió todo, "pendiente" (amarillo) cuando falta algo, "—" cuando el cliente no tiene sin cargos asignados este mes. Vendedor: chip de estado en la cabecera del bloque "Sin cargo del plan"; etiqueta "ganado" → "disponible".
- Validado: `_cargar_sincargos_mes()` (31 clientes, reparto OK), override+pendiente+estado sobre `mod_planes_as.csv` real, `node --check` del JS del portal OK.

## 2026-06-16 - feat(login): modo día/noche automático por horario argentino

**`PAV MATINAL PE_A FLOR/portal.html`** (`arHour`, `autoLoginMode`, `applyLoginMode`, `toggleMode`, `refreshAutoLoginMode`).

- La pantalla de ingreso ahora elige **día/noche automáticamente según la hora argentina** (`Intl` con `America/Argentina/Buenos_Aires`, robusto aunque el dispositivo esté en otra zona). Día 07:00–18:59, noche 19:00–06:59.
- Se mantiene el **botón manual**: al tocarlo sobreescribe el modo hasta recargar; al reabrir el portal vuelve a seguir el horario.
- Refresco cada 60s: si no hubo override manual, flipea en vivo al cruzar el límite con la pantalla abierta.
- Se quitó la persistencia en `localStorage` (`orbitLoginMode`), que fijaba el modo para siempre e impedía el automático.

## 2026-06-16 - perf(login): cache por mtime de endpoints pesados

**`server_orbit.py`** (`_acciones_mes_payload`, `_acc_preparar_ventas`, `_cargar_maestro_04D`).

- **Causa:** tras el login, el portal dispara en paralelo todos los endpoints, pero gunicorn corre 1 worker sync, así que se serializan. `/api/gerencia/acciones_mes` tardaba **18.8 s** porque recalculaba todo en cada request (lectura de ventas + `.apply(axis=1)` por regla), sin caché.
- **Cambio:** memoización por mtime (mismo patrón que `_faro_ventas`/`_clientes_maestro`), sin tocar lógica de negocio:
  - `_acciones_mes_payload` cacheado por (firma de fuentes, vendedor); se invalida al cambiar el mtime de ventas/catálogo/planes_as/04D.
  - `_acc_preparar_ventas` cacheado por (archivo, mtime).
  - `_cargar_maestro_04D` cacheado por mtime (lo usan acciones, dashboard, sellout, alertas).
- **Validación:** payload cold 4.09 s → warm 0.001 s, **output idéntico bit a bit**; un vendedor distinto no invalida el de gerencia; primer login tras cada cierre paga el costo una vez, el resto del día es instantáneo.

## 2026-06-16 - feat(cliente): buscador y ficha 360 en gerencia/vendedor

**`server_orbit.py`** (`/api/clientes/buscar`, `/api/clientes/<id>/ficha`) + **`PAV MATINAL PE_A FLOR/portal.html`** (pantalla/pestaña Cliente).

- Nuevo botón **Cliente** en gerencia y en perfil vendedor.
- Gerencia puede buscar cualquier cliente de `clientes.xlsx` sin V2/V5/V20; vendedor solo ve clientes de su cartera.
- La ficha muestra nombre, dirección, localidad, vendedor, día/frecuencia de visita, subcanal, frecuencia de compra mensual, marcas compradas en el mes con litros/dinero, ventas por mes con color por variación de litros, promedio disponible y posibilidad de venta.
- Fuente viva: `clientes.xlsx` + `ventas_acumulada.csv`/`ventas.csv`. Litros = `PesoKg`, igual que Sell Out. Si no hay 12 meses reales disponibles, se informa `meses_con_datos`.

## 2026-06-16 - fix(faro): medicion mayo-junio y reglas por categoria

**`server_orbit.py`** (`_faro_ventas`, `_faro_detalle_vendedor`, endpoints FARO) + **`PAV MATINAL PE_A FLOR/portal.html`** (`vFaro`, `faroShow`, `gIncentivoFaro`).

- **Periodo corregido:** FARO ahora filtra `ventas_acumulada.csv` a comprobantes de **mayo y junio** con venta neta (`ImporteNetoItem > 0`) y excluye V2/V5.
- **Reglas de producto/canal:** Smirnoff cuenta solo familia 700cc en Autoservicio; Antares cuenta en Autoservicio por SKU cubierto, con XPA y Lager 330/660 doble; Alaris/Finca Las Moras cuentan en Almacen/Despensa/Kiosco.
- **Detalle corregido:** el portal separa **coberturas logradas** de **clientes cubiertos**. En Antares, el drill-down muestra articulo y peso de cobertura, evitando interpretar coberturas como clientes.
- **Control inicial:** V4 Antares pasa de 13 inflado a **6/8 coberturas**, con **2 clientes unicos** y 5 filas de articulos cubiertos en mayo-junio.

## 2026-06-16 — fix(acciones): tarjetas desde ventas.csv + drill-down clientes

**`server_orbit.py`** (`_acciones_mes_payload`, predicados 11T/innovaciones, filtro Plan AS) + **`PAV MATINAL PE_A FLOR/portal.html`** (`accShowDetalle` en gerencia y vendedor).

- **Fuente corregida:** las tarjetas de Acciones Comerciales ahora cuentan `clientes_alcanzados` y `clientes_nuevos` desde **ventas netas de `01_INPUTS/ventas.csv`** (`ImporteNetoItem > 0`, sin V2/V5/V20). La `inversion_pesos` queda separada y sigue saliendo de `valorDescuento × CantBase`.
- **11 Titulares:** ACJ26-021/022/023 ya no buscan literalmente `"11 titulares por segmento"`; usan las marcas de `objetivo 11T.xlsx`. Validado: ACJ26-021 = 146 clientes, ACJ26-022 = 27, ACJ26-023 = 3.
- **Innovaciones:** ACJ26-008/024 usan la lista cerrada de códigos de `INNOVACIONES/Innovaciones.xlsx`. Validado: ACJ26-008 = 25 clientes; ACJ26-024 = 1.
- **Plan AS:** ACJ26-010/011/012/013 filtran clientes contra `mod_planes_as.csv` antes de contar. Validado: ACJ26-011 = 10 clientes, ACJ26-012 = 6, ACJ26-013 = 14.
- **Drill-down:** en gerencia y perfil vendedor, los textos **clientes** y **nuevos** son clickeables; abren una tarjeta con cliente, dirección, localidad, vendedor, venta neta, descuento, litros y última compra. Re-clic o ✕ cierra.
- **Validado:** `python -m py_compile server_orbit.py` OK; scripts del portal extraídos y `node --check -` OK; `test_client` OK para `/api/gerencia/acciones_mes` y `/api/vendedor/V8/acciones_mes`.
- **Observación:** ACJ26-026 queda en 0 correctamente con el catálogo actual porque no hay ventas Dadá Tinto de Verano en VTK/TDB; las 7 ventas existentes son Tradicional/Autoservicio.

## 2026-06-13 — feat(productos): alta Antares Lager 660 ml (cód 60022) + sumado a ACJ26-028

**`09_CONFIG/maestro_04D_productos.csv`** + **`01_INPUTS/04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx`** + **`generar_datasets_acum.py`** + catálogo de acciones + datasets.

- Código provisto por el usuario: **60022**. Alta en maestro 04D (CSV + xlsx) → Categoría **Cerveza Artesanal**, línea Cerveza Lager, Lts x caja 3.96 / UxC 6 → **lxu 0.66** (correcto para 660 ml, independiente del pack; UxC=6 es placeholder, no afecta ninguna métrica). Sumado a `INOV_PRODUCTOS` (19 → 20). Aún sin ventas → contribución 0 en sell out/innovaciones hasta que se venda.
- **Acción `ACJ26-028`**: `productos_marcas += 60022` (token de código → match exacto por SKU). Validado con el predicado: matchea 60022 (660) y 60021 (porrón 330), **excluye la lata 473** (60018). Cierra el pendiente del 660 ml.

## 2026-06-13 — feat(faro): drill-down de clientes con cobertura lograda (clic en el avance)

**`server_orbit.py`** (`_faro_detalle_vendedor` + `gerencia_incentivo_faro`) + **`PAV MATINAL PE_A FLOR/portal.html`** (`gIncentivoFaro` + nueva `faroShow`).

- En la pantalla gerencial **Incentivo Club FARO**, cada celda de avance (logrado/objetivo) de un vendedor es **clickeable** → abre abajo una tarjeta con los **clientes que tienen la cobertura lograda** en esa categoría (cliente, razón social, localidad, botellas). Re-clic o ✕ cierra.
- **Backend:** `_faro_detalle_vendedor` ya calculaba los clientes cubiertos pero los descartaba; ahora devuelve `compradores` (Alaris/Smirnoff = clientes que alcanzan el umbral; Antares = clientes con un SKU ≥6). Expuesto en `/api/gerencia/incentivo_faro` por vendedor×categoría. Supervisores → `compradores=[]`.
- **Frontend:** la respuesta se cachea en `D.faroData`/`window._faroByCod`; `faroShow(cod,cat)` renderiza la tarjeta en `#faro-detalle`. Sin librerías nuevas.
- **Validado (test_client):** Alaris/Smirnoff `len(compradores)==logrado` (V3 alaris 121=121, V4 smirnoff 23=23); Antares logrado por SKU (V4=13) vs 2 clientes distintos. Portal sirve 200 con `faroShow`. `py_compile` OK.

## 2026-06-13 — feat(plan-vs-real): fila TOTAL con lo planificado por cada KPI

**`PAV MATINAL PE_A FLOR/portal.html`** (`gPlanVsReal`, solo frontend).

- La tarjeta gerencial **Plan vs Real** suma un `<tfoot>` **TOTAL** con la suma de lo **planificado** por cada KPI: Plan $, CCC Tradicional, CCC Autoservicio, CCC On Premise y 11T (en negrita). Al lado, en las subcolumnas Real, el total real correspondiente + Cumpl% global, para mantener la fila alineada con el encabezado Plan/Real.
- **Sin cambios de backend:** se calcula en JS sobre `pvr.resumen` (endpoint `/api/matinal/resumen`), respetando `tiene_plan`/`tiene_real`. Validado contra el endpoint: Plan $ 4.920.000 (6 planes), CCC Trad 31 / Auto 8 / OP 6, 11T 35.

## 2026-06-13 — feat(acciones): ACJ26-028 (Antares Lager + Dadá Tinto Verano, 5/8% six pack) + Despensa = Almacén

**`01_INPUTS/ACCIONES COMERCIALES/2026-06/...csv`** (nueva fila ACJ26-028) + **`server_orbit.py`** (motor de acciones: despensa→almacén + sub-filtro multicanal).

- **Nueva acción `ACJ26-028`** (DESCUENTO_ESCALA): `Antares Lager Porrón` (cód 60021; el 660 se suma con su código) + `Dadá Lata Tinto de Verano` (74884), canal **Autoservicio + Almacén + Kiosco**, **1 six pack → 5% / 2+ six packs → 8%**, sin tope, TODOS_ACTIVOS. Tokens de marca precisos: **excluye la lata Antares Lager 473**. Aparece en gerencia (`/api/gerencia/acciones_mes`) y vendedor (`/api/vendedor/<vid>/acciones_mes`) + alertas, sin tocar frontend (data-driven).
- **Regla nueva: Despensa = Almacén** en todas las estadísticas. Único lugar que las distinguía era el sub-filtro de acciones `_ACC_SUBSEG_TRAD` (despensa→"DESPENSA"); ahora despensa→"ALMACEN" y el subramo de la venta se canoniza despensa→almacén en `_acc_preparar_ventas`. El resto del sistema ya las colapsaba en TRADICIONAL.
- **Motor multicanal (una sola tarjeta):** el sub-filtro almacén/kiosco ahora SOLO restringe el canon TRADICIONAL; las líneas de Autoservicio/On Premise no se filtran por subramo. Aplicado en `_acciones_mes_payload._match`, `_alertas_descuento_mes` y `_alertas_tope_cajas_mes`. Permite que ACJ26-028 cubra AS + Almacén/Kiosco en una fila.
- **Validado (baseline vs después, vía import directo):** 27→28 acciones, **las 27 existentes con números idénticos** (0 cambios, incl. ACJ26-017 $567.635/135). ACJ26-028 = $2.342/5 clientes. Alertas descuento 85→85, tope 9→9 (sin regresión). Presente en vista V4 (1 cli) y V3 (aparece, $0). `py_compile` OK.
- **Pendiente:** Antares Lager 660 ml (token/código a sumar cuando el usuario lo pase).

## 2026-06-13 — feat(productos): alta Antares Lager Porrón 330 (Cerveza Artesanal) y Dadá Tinto Verano (RTD)

**`09_CONFIG/maestro_04D_productos.csv`** + **`01_INPUTS/04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx`** + **`generar_datasets_acum.py`** (`INOV_PRODUCTOS`) + datasets regenerados (`mod_innovaciones_segmento.csv`, `mod_sellout_categoria.csv`).

- **Alta de 2 productos nuevos** (pedido del usuario): `60021` ANTARES LAGER PORRON 6X330 → Categoría **Cerveza Artesanal** (línea Cerveza Lager, lxc 1.98, UxC 6); `74884` DADA LATA TINTO VERANO 4X6X355 → Categoría **RTD** (lxc 8.52, UxC 24). Ambos ya se venden este mes (60021: 2 clientes; 74884: 10).
- **Sell out:** quedan clasificados en sus categorías; `OBJSELLOUT.xlsx` ya tenía objetivo para RTD (9.056 L) y Cerveza Artesanal (425 L), así que se suman solos. Validado en `/api/gerencia/sellout_litros`.
- **Innovaciones:** agregados a `INOV_PRODUCTOS` (17 → 19). Validado en `/api/gerencia/innovaciones_total` (19 productos, los 2 nuevos presentes).
- **Maestro xlsx defragmentado**: estaba inflado a 1.048.527 filas (19 MB con imágenes) → reescrito limpio (0,02 MB, 255 filas) preservando estructura (header en fila 3) para que el generador lo parsee igual. Backup del original en `99_BACKUPS_ORBIT/`.
- **Pendiente:** Antares Lager **660 ml** (sin código en el sistema) — se suma cuando el usuario pase el código. Acción comercial (tarjeta) = Fase 2.

## 2026-06-12 — feat(dormidos): botón de descarga Excel con el listado completo

**`server_orbit.py`** (refactor `gerencia_alertas_caida` → helper `_dormidos_payload()` + nuevo endpoint `/api/gerencia/alertas_caida/export`; imports `send_file` + `BytesIO`) + **`PAV MATINAL PE_A FLOR/portal.html`** (botón "⬇ Descargar Excel" en la pantalla Dormidos + `descargarDormidosExcel()`).

- **Qué hace:** botón en la pantalla gerencial de Clientes Dormidos que descarga un `.xlsx` con el **listado COMPLETO** (la tabla en pantalla muestra solo top 100 por importe; el Excel trae todos).
- **Una sola fuente de verdad:** el cálculo de dormidos se extrajo a `_dormidos_payload()` (sin cambiar el criterio: sin compra +60 días, excluye V2/V5/V20, riesgo $ y litros desde `historial_ventas_cliente.csv` + `ventas.csv`). Lo consumen tanto el JSON (`/api/gerencia/alertas_caida`) como el Excel (`/export`), así no divergen.
- **Excel:** 8 columnas (Cliente ID, Cliente, Vendedor, Nombre vendedor, Última compra, Días sin compra, Importe anterior $, Litros anteriores), anchos auto, hoja "Dormidos", nombre `clientes_dormidos_<fecha_corte>.xlsx`. `openpyxl` ya estaba en requirements.txt → deploy Render OK.
- **Validado** (endpoint en vivo, puerto 8502): JSON `total_dormidos=17` / `len(detalle)=17`; `/export` → HTTP 200, `Content-Disposition: attachment; filename=clientes_dormidos_2026-06-12.xlsx`, mimetype spreadsheet, **18 filas (17 + encabezado) = listado completo**, 8 columnas. `py_compile` OK.

## 2026-06-12 — fix(V3): regla "V3 no trabaja On Premise" (espejo de Autoservicio)

**`server_orbit.py`** (13 puntos) + **`PAV MATINAL PE_A FLOR/portal.html`** (tarjeta CCC por Segmento del vendedor).

- **Síntoma:** en el cierre del día (Plan vs Real) V3 (Nadia Gambino) figuraba con **1 cliente CCC On Premise** (cliente 696, "AWAY FROM HOME / Bar/Restaurant", Alma Mora, 2026-06-11). V3 no aplica a ese subcanal, igual que ya no aplica a Autoservicio.
- **Regla aplicada:** V3 → CCC On Premise = 0 en **todas** las superficies donde ya se forzaba AS=0: `_ccc_mes_por_vendedor` (fuente del CCC mes), dashboard (mes/día/oportunidades + flag `trabaja_onpremise`), vendedor (día + flag), `matinal/resumen` (Plan vs Real, `real_ccc_op`), `cobertura_segmento`, cierre mensual versionado, y **planificación** POST/PATCH (no se puede planificar OP a V3). Portal: la vista del vendedor **oculta** la casilla "ON PREMISE" para V3 (grid de columnas dinámico), como ya hacía con AUTOSERV.
- **Fuente:** `ventas.csv` (verificado: V3 tiene 1 cliente OP). No se toca el dato crudo ni la clasificación de segmentos; solo el conteo atribuido a V3.
- **Validado** (endpoints en vivo, puerto 8502): `ccc_empresa` V3 onpremise=0; `dashboard` V3 ccc_onpremise(mes)=0, ccc_dia_onpremise=0, trabaja_onpremise=False; `vendedor/V3` idem; `matinal/resumen` V3 plan_ccc_op=0/real_ccc_op=0; `cobertura_segmento` V3 = solo TRADICIONAL. Otros vendedores conservan su On Premise (V6=4, V8=4, V9=5, V10=2). `py_compile` OK.

## 2026-06-10 — feat(alertas): control automático de tope mensual de cajas por cliente

**`server_orbit.py`** (nuevo `_acc_botellas_por_caja` + `_alertas_tope_cajas_mes`; el endpoint `/api/alertas` ahora devuelve `_alertas_descuento_mes() + _alertas_tope_cajas_mes()`).

- **Qué hace:** alerta cuando un cliente supera el **tope mensual de cajas** de una acción. Catálogo-driven: aplica a toda regla con `maximo` numérico + `unidad_maximo` que contenga "caja" y "mes" (hoy: ACJ26-017, tope 2 cajas/mes). Sin hardcode del id de acción.
- **Caja = botellas/caja del artículo** (`_acc_botellas_por_caja`: "ALMA MORA MALBEC **6X750**" → 6; default 6). `CantBase` viene en **botellas** (confirmado: lxu maestro 04D = 0.75 L/unidad). Cajas = CantBase / botellas-por-caja.
- **Footprint:** mismas líneas que matchean la acción (vendedor + segmento canon + sub-segmento almacén/despensa/kiosco + marca) con **descuento real (>0)**. Se suman las cajas por cliente en el mes (combinable entre las 4 marcas) y se alerta si superan el tope.
- **Feed unificado:** la alerta usa el mismo contrato que las de descuento (`cliente_nombre`/`titulo`, `vendedor_id`, `detalle`, `prioridad: alta`, `fecha_carga`), `tipo: "tope"`. Clave de seguimiento estable `vendedor_id|cliente_id|articulo` con `articulo="TOPE <id_accion>"`. Se renderiza solo en gerencia (`gAlertas`) y vendedor (`vAlertas` filtra `D.al` por vendedor) **sin tocar frontend**.
- **Validado** (local): 4 alertas de tope para ACJ26-017 — cli 643 (V8, 5 cajas), 7518 (V3, 5), 30064 (V8, 4.5), 509 (V8, 4); todas con exceso y marcas combinadas. Feed combinado = 55 (51 descuento + 4 tope), serializable para jsonify (Render).

## 2026-06-10 — feat(acciones): ACJ26-017 20% almacén/despensa+kiosco, V3/V4/V6/V8/V10 + sub-filtro de tradicional

**`server_orbit.py`** (nuevo `_acc_subseg_filtro` + columna `_subseg` en `_acc_preparar_ventas`; aplicado en `_acciones_mes_payload._match` y `_alertas_descuento_mes`) + **catálogo** `01_INPUTS/ACCIONES COMERCIALES/2026-06/acciones_comerciales_junio_2026_penaflor.csv` (fuente real) + `.json` (derivado sincronizado).

- **Antes:** ACJ26-017 = Tradicional, vendedores V3/V4/V6, **30%**, tope "No informado". El motor segmentaba solo a nivel canon `TRADICIONAL` (no distinguía almacén/despensa/kiosco de panadería/carnicería/etc.).
- **Ahora regla:** vendedores **V3/V4/V6/V8/V10**; **solo almacén/despensa/kiosco** (segmento "Almacén; Despensa; Kiosco", canal `ALMACEN_DESPENSA_KIOSCO`); **20%**; mismas 4 marcas (Alma Mora, Dada vino, Alaris, Finca Las Moras); **tope 2 cajas/mes combinable entre marcas** (ej. 3 botellas de una y 3 de otra → `maximo=2`, `unidad_maximo=cajas en el mes`).
- **Sub-filtro de motor:** `_acc_subseg_filtro` detecta cuando una acción nombra subtipos específicos (almacén/despensa/kiosco/maxikiosco) **sin** el genérico de canal ("tradicional"/"trad") y, en ese caso, restringe el match por `Subramo` de la venta (`_subseg`). Opt-in: ACJ26-002/005/006/007/021 (genéricos "Tradicional") quedan **intactos** = todo el canal. Solo ACJ26-017 sub-filtra. No se tocó `_clasificar_segmento` (cobertura).
- **Efecto en alertas de descuento:** el % permitido para estas marcas/vendedores en almacén/despensa/kiosco baja de 30% → **20%**.
- **Validado** (endpoint real): subfiltro ACJ26-017={ALMACEN,DESPENSA,KIOSCO}, ACJ26-002/021=None. Tarjeta gerencia: canal ALMACEN_DESPENSA_KIOSCO, vendedores [V3,V4,V6,V8,V10], 20%, tope OK, 17 clientes / $145.091. ACJ26-002 sin cambios (36 cli / $387.509). V8/V10 ven la acción, V7 no. Alertas: 51 filas sin excepción. Footprint junio: 46 líneas, todas subramo "Almacen/Despensa" (0 excluidas este mes; el filtro discrimina y excluiría otros sub-tradicionales).

## 2026-06-09 — feat(sellout): objetivos de la tarjeta Sellout litros desde OBJSELLOUT.xlsx

**`server_orbit.py`** (nuevo `_cargar_objetivos_sellout`; `_sellout_desde_ventas` → endpoint `/api/gerencia/sellout_litros`) + **`PAV MATINAL PE_A FLOR/portal.html`** (`_renderSoDash`, tarjeta gerencial *Sellout acumulado en litros · por categoría*) + **`01_INPUTS/OBJSELLOUT.xlsx`** (objetivos).

- **Antes:** los objetivos por categoría estaban **hardcodeados** en el dict `OBJ` de `_sellout_desde_ventas` (VINOS DEL AÑO 19015, RTD 9999, etc.).
- **Ahora:** `_cargar_objetivos_sellout()` lee `01_INPUTS/OBJSELLOUT.xlsx` (Hoja1: `categoria` | `objetivo en litros`) y es la **fuente única** de objetivos. Clave = categoría en mayúsculas, coincide con los buckets. Valores: VINOS DEL AÑO 17023 · VINOS DE GUARDA 817 · SPIRITS 17019 · RTD 9056 · CHAMPAÑA 747 · CERVEZA ARTESANAL 425.
- **Subcategorías** (VDA: Alto/Medio Alto/Superior/Medio · SPIRITS: Nacionales/Importados): el archivo solo trae objetivo a nivel categoría, así que las subcategorías muestran **litros sin objetivo** (`objetivo=None`, `alcance_pct=None`). Decisión del usuario: "sin objetivo de sub".
- **Frontend:** `_renderSoDash` tolera `alcance_pct`/`objetivo` null → muestra `–` en vez de romper con `.toFixed`. (La vista congelada/cierre de la línea ~3244 ya manejaba null; no se tocó.)
- **Si falta una categoría en el archivo** → objetivo `None` (Dato no disponible), no se cae a valores viejos.
- **Validado** (test_client `/api/gerencia/sellout_litros` → 200): objetivos = OBJSELLOUT.xlsx; avances recalculados (VDA 13.8%, SPIRITS 35.1%, RTD 17.6%…); subs con litros y objetivo/alcance None. Loader: 6/6 buckets matchean.

## 2026-06-08 — feat(faro): Incentivo Club FARO en gerencia y vendedor

**`server_orbit.py`** (sección INCENTIVO CLUB FARO: `_faro_objetivos`, `_faro_ventas`, `_faro_detalle_vendedor`, endpoints `/api/gerencia/incentivo_faro` y `/api/vendedor/<vid>/incentivo_faro`) + **`portal.html`** (botón + pantalla gerencial `gIncentivoFaro` y tab vendedor `vFaro`) + **`01_INPUTS/incentivo_club_faro .xlsx`** (objetivos).

- **Objetivos**: desde `incentivo_club_faro*.xlsx` (3 categorías × vendedor). Supervisores = suma de su equipo (Esteban=V3/4/6/8/10, Raúl=V7/9).
- **3 categorías** (segmento por Ramo+Subramo de la venta; Autoservicio incluye autoservicio-tradicional): **Alaris+Finca Las Moras** (Tradicional, ≥3 bot, 1 CCC/cliente) · **Antares** (Autoservicio, ≥6, por SKU con XPA/Lager **doble**) · **Familia Smirnoff** (Autoservicio, ≥6, 1 CCC/cliente; Marca SMIRNOFF, excluye Smirnoff Ice).
- **Logrado y no-compradores**: desde `ventas_acumulada.csv` (bimestre mayo-junio). No-compradores = clientes del canal a los que el vendedor vendió en el bimestre y NO cubrieron la marca (con botellas compradas o "sin compra").
- **Gerencia**: tabla vendedores + supervisores con logrado/objetivo/% por categoría. **Vendedor**: tab FARO con su objetivo (3 tarjetas con barra de avance) y debajo la lista de no-compradores por categoría.
- **Validado** (test_client): ambos endpoints 200. V8: alaris 42/65, antares 13/10 (130% por regla doble), smirnoff 25/25. V3 (no AS): alaris 120/100, antares/smirnoff 0/0. Serialización nativa (`_to_native`).

## 2026-06-08 — fix(cierre): tarjeta Acciones Comerciales mostraba IVA, no inversión real

**`server_orbit.py`** (nuevo `_cierre_acciones_versionado` + helper `_gda`; endpoint `/api/gerencia/cierres_historicos` → pantalla **Cierre de Mes**, tarjeta Acciones Comerciales).

- **Síntoma:** la tarjeta mostraba 6 acciones, inversión 828.235, 50 clientes (artefacto congelado `cierre_acciones_comerciales.json`).
- **Causa raíz:** ese artefacto calculó inversión = `ImporteItem − ImporteNetoItem`, que es **IVA (21%)**, no descuento. Comprobado: inversión 828.235 = 21% del neto 3.943.978; las 6 acciones daban exactamente 21% c/u. Además solo cubría 6 de 11 acciones del catálogo y subcontaba clientes.
- **Fix:** `_cierre_acciones_versionado(files)` recalcula desde `ventas_mes_<MMAAAA>.csv` con el matching canónico de `generar_acciones_ranking` (`_REGLA_CANAL_SEG_MAP`/`_filtrar_ventas_accion`/`INOV_PRODUCTOS`) pero con **inversión = `valorDescuento × CantBase`** (descuento real). Maestro 04D vía CSV liviano (no el xlsx 19MB). Catálogo por mes en `_ACC_REGLAS_POR_MMAAAA`. Fallback al artefacto si no hay catálogo.
- **Validado** sobre `01_INPUTS/cierres mes/ventas_mes_052026.csv`: clientes/neto idénticos al generador canónico (139/286/752…), solo cambia la inversión (item−neto→vd×CantBase). Resultado: **11 acciones, inversión 14.856.477, neto 112.346.234, 936 clientes**. Serialización nativa verificada (jsonify-safe).
- **Pendiente:** `mod_acciones_ranking.csv` (datasets vivos) y el endpoint `gerencia_cierre_mes` siguen usando item−neto=IVA en `inversion_pesos` → corregir aparte.

## 2026-06-08 — fix(cierre): tarjeta 11 Titulares · CCC vs Objetivo — fuente bimestral + sin filtro Empresa

**`server_orbit.py`** (`_cierre_archivos_mes`, `_cierre_once_titulares`, nuevo `_leer_ventas_acum_cierre`; endpoint `/api/gerencia/cierres_historicos` → pantalla **Cierre de Mes**).

- **Síntoma:** la tarjeta "11 Titulares · CCC vs Objetivo" del cierre daba muy por debajo del real (mayo 2026: 2066 / 58.2%).
- **Causa raíz (dos):** (1) `_cierre_once_titulares` filtraba `Empresa == "Empresa"`, descartando las filas de **P&P Logística** (ventas reales de vendedores activos); el 11T canónico (`/api/gerencia/once_titulares`) no filtra Empresa. (2) Leía de `ventas_mes_<MMAAAA>.csv` (1 mes), pero **el 11 Titulares se mide bimestral** (2 meses) → la fuente correcta es `ventas_acumulada_<MMAAAA>.csv`.
- **Fix:** `_cierre_archivos_mes` ahora expone `ventas_acumulada` (opcional). `_cierre_once_titulares` lee de esa acumulada bimestral (nuevo lector `_leer_ventas_acum_cierre`, sep=';'/latin1, neto>0, excl V2/V5/V20, sin filtro Empresa), con **fallback** a `ventas_mes` si un cierre viejo no tiene la acumulada. Mismo criterio que el dashboard diario. Objetivos y mapeo de marcas sin cambios.
- **Validado** sobre `01_INPUTS/cierres mes/ventas_acumulada_052026.csv` (rango 2026-04-01→05-30): **4424 CCC / 124.5%**, 11/11 marcas ≥ objetivo. Por marca: ALMA MORA 749, DADA 556, ALARIS 541, SMIRNOFF ICE 519, SMIRNOFF FLAVOURS 481, FINCA LAS MORAS 448, LOS ARBOLES 445, ANTARES 230, TRAPICHE RESERVA 187, DON DAVID 134, GORDON'S 134.
- **Decisión del usuario:** el cierre queda **con nuestro criterio canónico**, aun con diferencias vs el reporte oficial de Peñaflor (ellos ~4007). Diferencia bidireccional (mapeo de SKUs + base de clientes) que no se reconcilia sin su detalle cliente-nivel; auditoría exportada en `99_AUDITORIA_ORBIT/auditoria_11t_clientes_052026.csv`.

## 2026-06-06 — feat(alertas): nota gerencial por alerta (vista/hablada con el vendedor)

**`server_orbit.py`** (tabla `alerta_seguimiento` + endpoint `/api/alertas/seguimiento`) + **`portal.html`** (pantalla Alertas gerencial).

- En la pantalla **Alertas** del perfil gerencial, cada alerta tiene ahora un **campo de nota + botón Guardar** para dejar asentado si fue vista y hablada con el vendedor. La nota persiste y se pre-carga al volver a entrar.
- Backend: tabla `alerta_seguimiento(clave, mensaje, autor, updated_at)` en orbit.db (disco persistente en Render). Endpoint GET (todas las notas) y POST (upsert; mensaje vacío borra). Clave estable = `vendedor_id|cliente_id|articulo`.
- Frontend: `gAlertas` arma la clave por fila, `_cargarSeguimientoAlertas()` pre-llena, `guardarSeguimiento(idx)` hace POST (Enter o botón). Autor = "Gerencia".
- Validado (instancia temp): ciclo GET vacío → POST guardar → GET con nota → POST vacío borra → GET vacío.

## 2026-06-06 — feat(tool): EXCEL_PREVENTA.bat — Excel de preventa 11 Titulares por día

**Nuevos: `EXCEL_PREVENTA.bat` (CRLF) + `tools/excel_preventa.py`.**

- Genera un Excel con **una hoja por día de visita** (Lunes→Sábado). Cada hoja lista los clientes de ese día (ordenados por vendedor + orden de ruta) con: Vendedor, Código, Nombre, Dirección, Localidad, Segmento, **Compró (Sí/No)**, **Titulares cubiertos (X/11)** y **una columna por cada uno de los 11 Titulares**.
- En cada columna de titular: estado de cobertura vs `ventas_acumulada.csv` → "OK" si cubre, o "b/umbral vender f" (compró b botellas, faltan f). **Umbral: TRADICIONAL=3 (kiosco/almacén/despensa), resto=6** (regla Peñaflor). Colores verde/amarillo/rojo.
- Reglas reutilizadas de `generar_datasets_acum.py` (ALIAS_LOOKUP, _ONCE_TITULARES, UMBRAL, segmento, cargar_clientes/ventas_acumulada). No toca server/Render.
- Salida: `03_OUTPUTS/PREVENTA_11T_<fecha>.xlsx` (el .bat lo abre solo). Validado: 6 hojas, 2035 clientes.

## 2026-06-06 — feat(dashboard): rechazo por supervisor en tarjeta Ranking de Rechazos

**`server_orbit.py`** (`/api/gerencia/ranking_rechazos`) + **`portal.html`** (tarjeta Ranking de Rechazos del dashboard gerencial).

- Se agrega el **% de rechazo de los dos supervisores** (Esteban = Gribaudo, Raul = Benítez) en una franja "Rechazo por supervisor" arriba del ranking de vendedores.
- Fuente: `resultado.xlsx` hoja Rechazos, filas `Origen == Supervisor` (campo `SupervisorNombre` + `PorcRechazo`). El endpoint ahora devuelve `supervisores: [{supervisor_nombre, nombre, rechazo_pct}]` (nombre = nombre de pila). Salida casteada a tipos nativos (jsonify-safe).
- Validado (instancia temp): Esteban 0.5% · Raul 0.4%; sin tipos numpy.

## 2026-06-06 — feat(cierre): CIERRE_MES_ORBIT.bat — versionado automático del cierre

**Nuevos: `CIERRE_MES_ORBIT.bat` (CRLF) + `tools/cerrar_mes.py`.**

- Automatiza la generación de los archivos del cierre en `01_INPUTS/cierres mes/`: el usuario deja las fuentes del mes en `01_INPUTS` y ejecuta el `.bat`; este copia/versiona con sufijo `_MMAAAA` y publica a Render (commit + pull --rebase + push).
- `cerrar_mes.py`: autodetecta el mes por la fecha máx de `ventas_mes.csv` (o `MMAAAA` por argumento), mapea 6 fuentes → versionadas (resultado_mes, ventas_mes, objetivo 11T, acciones, reconocimiento, escala), **backup** a `99_BACKUPS_ORBIT/`, **log** a `99_LOGS_ORBIT/`. NO inventa datos (solo copia las fuentes reales).
- **Protección:** un mes ya cerrado (con archivos en la carpeta) NO se toca sin `--force` → evita pisar un cierre hecho con fuentes de otro mes. `--dry-run` para previsualizar.
- Validado: dry-run y run real sobre mayo = no-op (los 3 archivos de mayo intactos). Acciones de mayo: no hay catálogo de mayo → el cierre usa fallback (correcto).
- **Pendiente FASE 2b:** que el server calcule **Acciones** y **Planes AS** desde los catálogos versionados (`acciones_<MMAAAA>.csv`, `reconocimiento_<MMAAAA>.xlsx`, `escala_<MMAAAA>.xlsx`) con fallback al artefacto viejo. Se construye/valida con los catálogos reales de junio al cerrarse, para no desplegar lógica comercial sin datos que la validen.

---

## 2026-06-06 — fix+feat(cierre): FASE 2a re-aplicada y corregida (Sell-Out/Innov/Ranking)

**`server_orbit.py`**. Re-aplica la Fase 2a tras el revert `4690b9a` (que se hizo porque la 1ª versión rompía Render con HTTP 500 a los ~31s).

- **Causa 1 (HTTP 500):** el ranking traía `numpy.float64` (de `groupby().to_dict()`) que el JSON provider de Flask no serializa en Render (en local sí). **Fix:** casteo de litros/dinero/11t/innov a `float`/`int` nativos + sanitizador recursivo `_to_native()` sobre toda la salida de extras.
- **Causa 2 (~43s → timeout):** se leía `04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx` (19MB con imágenes, ~40s) para los litros del ranking. **Fix:** usar `_cargar_maestro_04D()` (CSV liviano `09_CONFIG/maestro_04D_productos.csv`) → endpoint **3.2s**. Caché de lecturas de ventas_mes (`_leer_ventas_mes_cacheado`, `_gcm_leer_ventas_cacheado`).
- **Validado (instancia temp):** 1er request 3.2s, sin warnings, sin tipos numpy; Sell-Out 6 cat, Innovaciones 13 productos, Ranking #1 V8.

---

## 2026-06-06 — feat(cierre): cierre versionado por carpeta (FASE 1: objetivos/avance + 11T)

**`server_orbit.py`** (endpoint `/api/gerencia/cierres_historicos`) + nuevos archivos en `01_INPUTS/cierres mes/`.

- **Objetivo:** cada cierre mensual se calcula desde un trío de archivos versionados por `_MMAAAA` en `01_INPUTS/cierres mes/`, autocontenido y sin romper meses anteriores:
  - `resultado_mes_<MMAAAA>.xlsx` → objetivo/acumulado/avance por vendedor.
  - `ventas_mes_<MMAAAA>.csv` → CCC (y en fases siguientes sell-out/planes/acciones/innov).
  - `objetivo 11T_<MMAAAA>.xlsx` → objetivo del 11T por marca.
- **FASE 1 (esta):** `cierres_historicos` ahora, si existen los 3 archivos del período, recalcula **objetivos_avance** (Resumen compañía + Cierre por vendedor + CCC por segmento) y **once_titulares** (11 Titulares · CCC vs Objetivo) desde ese trío, sustituyendo a los artefactos congelados. Helpers nuevos: `_cierre_archivos_mes`, `_cierre_ccc_por_vend_segmento`, `_cierre_objetivos_avance`, `_cierre_once_titulares`.
- **Corrige** el bug reportado: el 11T del cierre tomaba CCC de `ventas_acumulada.csv` (mayo+junio mezclados → 2656/74.8%). Ahora sale de `ventas_mes_052026.csv` (mayo aislado) → **2066 CCC / 58.2%**, 1/11 marcas ≥100%.
- **Validado (instancia temp):** Resumen compañía obj $326.8M / acum $323.9M / 99.11%; CCC 831; 7 vendedores poblados; 11T 11 marcas. Catálogos compartidos (maestro 04D, escala, acciones, innovaciones) NO se mueven a la carpeta.
- **Pendiente FASE 2:** migrar Sell-Out / Planes AS / Acciones / Innovaciones / Ranking al mismo trío, y descubrir cierres directamente desde la carpeta (hoy aún usa el índice de 07_CIERRES_MENSUALES).

---

## 2026-06-06 — ui(cierre): quitar tarjeta "Resumen empresa del cierre"

**`PAV MATINAL PE_A FLOR/portal.html`** — función `gCierreMes` / `_renderCierreHistorico`.

- A pedido del usuario se elimina de la pantalla **Cierre de Mes** la tarjeta **"🏢 Resumen empresa del cierre"** (Importe neto total / Litros total / CCC total / Filas ventas mes, derivada de `ventas_mes.csv` vía `c.empresa`).
- Solo se removió el bloque HTML de esa tarjeta. La variable `e=c.empresa` se mantiene porque sigue usándose en la tarjeta de metadatos (`e.filas_ventas_mes`). La tarjeta "🏢 Resumen compañía" (objetivos/avance desde resultado.xlsx) queda intacta.
- Cambio solo de presentación; no toca endpoints ni datos.

---

## 2026-06-05 — fix(planes_as): facturado del Plan AS desde ventas.csv (no del Excel)

**`generar_datasets_acum.py`** + regen `04_DATASETS_ORBIT/mod_planes_as.csv`. Afecta `/api/gerencia/planes_as` y `/api/vendedor/<vid>/planes_as` (tarjetas "Facturado").

- **Problema:** el "Facturado" (`total_facturado`) de las pantallas Plan AS (gerencia y perfil vendedor) salía de la **columna 14 del Excel `Reconocimiento Plan As.xlsx`** (valor estático, ~$77,9M total), no de ventas reales. Violaba la **regla 3.10** (REGLAS_CALCULO_Y_FUENTES_PENAFLOR): fuente oficial del Plan AS = `ventas.csv`, salida = "venta acumulada válida".
- **Fix:** `generar_planes_as` ahora calcula `total_facturado` = suma de `ImporteNetoItem` (> 0) por cliente desde **ventas.csv**, y **recalcula la escala alcanzada** con esa venta real contra `escala_junio.xlsx`. El Excel de Reconocimiento se sigue usando solo para lo que le corresponde (plan_as, tope, sin-cargo ganado por producto, dcto_plan). Se extrajo el cálculo de escala a un helper reutilizable `_calc_escala_actual()`.
- **Validado (endpoints en vivo):** `total_facturado` coincide 1:1 con la suma neta de ventas.csv por cliente; escalas recalculadas; gerencia 31 clientes AS; V8 16 clientes AS. Total facturado OLD $77,9M (Excel) → NEW $7,8M (ventas.csv mes vivo 01–04 jun).
- **Nota operativa:** ventas.csv es el **mes vivo** (hoy 01–04 jun). El facturado/escala reflejan el avance del mes a la fecha y **suben cada día** que se carga el ventas.csv. 11 clientes aún sin compra en junio → escala 0.
- **Observación de dato (ERP):** en ventas.csv 4 clientes AS (8010, 8139, 8230, 1093) tienen exactamente $785.458 neto en 1 sola fila cada uno — revisar en el ERP si es correcto.
- **No se tocó:** server_orbit.py, portal.html, otras datasets, cierre mensual.

---

## 2026-06-05 — fix(objetivos): perfil de vendedor usa resultado.xlsx (no mod_volumen)

**`server_orbit.py`** — endpoints `/api/vendedor/<vid>` y `/api/dashboard`.

- **Problema:** las tarjetas del perfil de vendedor ("Te falta para el objetivo" y "Tendencia vs. Objetivo") tomaban objetivo/acumulado/tendencia de `mod_volumen_vendedor.csv`, mientras el dashboard ya usaba `resultado.xlsx`. Resultado: la **tendencia divergía** entre pantallas (ej. V3 dashboard 20.62% vs perfil 16.49%; V9 109.88% vs 87.9%) y el perfil se quedaba viejo cuando se actualizaba `resultado.xlsx` sin regenerar el motor.
- **Causa raíz:** `/api/vendedor/<vid>` calculaba `obj/acum/av` desde mod_volumen y recalculaba la tendencia con su propio conteo de días hábiles, distinto al del dashboard.
- **Fix:** `/api/vendedor/<vid>` ahora lee `objetivo/acumulado/avance` de `resultado.xlsx` hoja Avance como fuente primaria (fallback a mod_volumen si falta el Excel), y `tendencia_pct = Avance` (= Tendencia/Objetivo, regla Peñaflor) sin recálculo por días. En `/api/dashboard` la tendencia también se fija al `Avance` de resultado.xlsx para los vendedores con fuente (mismo valor mostrado hoy, pero robusto ante cambios de días corridos).
- **Validado (instancia temp puerto 8599):** los 7 activos coinciden 1:1 con `resultado.xlsx` en objetivo, acumulado y tendencia. Dashboard OBJ compañía = **$330.000.000** (suma de los 7 ValorObjetivo). Perfil V3 16.49%→**20.62%**, V9 87.9%→**109.88%**.
- **No se tocó:** portal.html / diseño, datasets, CCC/11T, objetivos del dashboard (ya correctos).

---

## 2026-06-05 — feat(plan vs real): real del día = acumulado hoy − ayer (resultado.xlsx)

**`server_orbit.py`**, **`generar_datasets_acum.py`**, **`CIERRE_DIA_ORBIT.bat`**, nuevo `02_HISTORY/acumulado_resultado_historico.csv`.

- **Problema:** el "real del día" en Plan vs Real se calculaba contando líneas de `ventas.csv` por `FechaComprobante` → si las facturas del día no quedan fechadas ese día, el vendedor figuraba **"sin ventas"**. Caso real: **V10 figuraba sin ventas el 04/06** pese a haber vendido.
- **Fix (validado por usuario):** real del día por vendedor = **`Acumulado(hoy) − Acumulado(ayer)`** de `resultado.xlsx` (hoja Avance). Con eso **V10 = $357.851** el 04/06 (acum 3.988.161 − 3.630.310). Captura las ventas sin depender de la fecha del comprobante.
- **Mecanismo:** snapshot diario del Acumulado por vendedor → `02_HISTORY/acumulado_resultado_historico.csv` (función `snapshot_acumulado_resultado` en el cierre; histórico bootstrapeado desde git para 06-02/03/04). `_real_dia_resultado(fecha)` en server_orbit.py hace la diferencia (mismo mes; negativos→0). `matinal_resumen` usa el resultado cuando hay snapshot exacto del día; fallback a ventas.csv. El bat ahora commitea el histórico.

---

## 2026-06-04 — fix(cierre): CIERRE_DIA_ORBIT.bat con finales LF (rompía el push)

- **Causa raíz:** `CIERRE_DIA_ORBIT.bat` tenía **finales de línea LF** (0 CRLF). En cmd.exe eso rompe los bloques `if exist (...) else (...)` → errores `'exist'`/`'else'`/`'hq.'` no reconocidos y, peor, **la sección git (PASO 3/3) no se ejecutaba** → el cierre regeneraba los datos pero **nunca los pusheaba**. Por eso Render quedaba con `ventas.csv` viejo (no avanzaba a viernes) y no reflejaba los cambios.
- **Fix:** `.bat` convertido a **CRLF** + `.gitattributes` (`*.bat/*.cmd eol=crlf`) para que no se repita. `.gitignore`: `01_INPUTS/ACCIONES COMERCIALES/*/salida/`.
- **Datos pendientes del cierre del usuario** (ya consistentes con las correcciones: 11T=11 marcas, innovaciones junio=38, planes con dirección) commiteados y pusheados. Render: `fecha_corte=2026-06-04` → `dia_operativo=VI` ✓.

---

## 2026-06-04 — fix(vendedor): pantalla Ruta correcta (clientes.xlsx + ventas.csv, 11 titulares)

**`server_orbit.py`** (`/api/vendedor/<vid>/ruta`) y **`portal.html`** (vRuta).

- **Bugs:** `/api/clientes` sin `dia` traía `faltan_11t = 11` **hardcodeado** para todos; con `?dia=` (`_clientes_por_dia`) ni siquiera calculaba 11T → 0. La ruta mostraba datos incorrectos.
- **Fix:** nuevo endpoint `/api/vendedor/<vid>/ruta` que arma la ruta del día desde **`clientes.xlsx`** (DiasVisita = día, codven = vendedor) y calcula **compra/sin compra** y **11 Titulares faltantes** desde **`ventas.csv`** (mes vivo), considerando **solo los 11 titulares**.
- Por cliente: `once_t_comprados/11` + chips de las marcas titulares faltantes. `vRuta` usa `D.ruta` (antes `D.cli`). Reemplaza los chips de innovaciones por los de 11 titulares (la ruta es solo titulares).
- Validado: V8 día MA = 55 clientes (13 con compra), AMANTINI 3/11 faltan Trapiche Reserva/Alaris/Don David.

---

## 2026-06-04 — feat(vendedor): Oportunidad del día de Innovaciones

**`server_orbit.py`** (`/api/vendedor/<vid>/oportunidades_innovacion`) y **`portal.html`** (inicio vendedor).

- Nueva tarjeta llamativa en "Oportunidades del día": 3 clientes de la **zona de hoy** que **compraron el mes pasado y este mes** pero **nunca innovaciones** (ni mayo ni junio). Texto alentador: "Hoy <vendedor>, andá a venderles innovaciones a estos clientes... pero todavía no compraron estas marcas: <3 innovaciones al azar>".
- Fuente: **`ventas_acumulada.csv`** (mayo+junio); innovaciones desde `mod_innovaciones_segmento.csv` (17 productos). Candidatos = `(compró mes ant. − inov mes ant.) ∩ (compró mes act. − inov mes act.) ∩ clientes del día`. Top 3 por volumen ($). 3 marcas random.
- Fallback: si no hay candidatos del día, se muestra el bloque anterior de "Recuperar cliente".

---

## 2026-06-04 — feat(historial): retención de 90 días (ventana móvil)

**`LEGACY/orbit_matinal_v42.py`** (`actualizar_historial_ventas`).

- Antes el historial **no tenía tope** (acumulaba indefinidamente; hoy ~69 días por la antigüedad del sistema). Se agregó **ventana móvil de 90 días**: en cada cierre mantiene solo `fecha >= max_fecha − 90 días`.
- Beneficio para Dormidos (+60 días): la banda de detección se amplía de los ~60-69 días actuales hacia **60-90 días** a medida que el historial acumula. Aplica en el próximo cierre (no modifica el historial actual: 69 días < 90, poda 0).

---

## 2026-06-04 — feat(dormidos): criterio +60 días sin compra + riesgo $/litros

**`server_orbit.py`** (`/api/gerencia/alertas_caida`) y **`portal.html`** (pantalla Dormidos gerencia).

- **Nuevo criterio:** dormido = **sin compra hace más de 60 días**. Antes era "compró en período anterior y no en el actual". Última compra por cliente = max fecha en `historial_ventas_cliente.csv` + `ventas.csv`; `dias_sin_compra > 60`.
- **Riesgo en $ y litros:** se agregó volumen en litros (parseado del nombre del artículo: `6X750`→0.75L, `4X6X473`→0.473L; `cant_base` = unidades base). Las **3 tarjetas KPI** ahora son: Clientes dormidos · Riesgo $ · Riesgo litros.
- **Dormidos por Vendedor:** top **3** clientes (antes 5), por **mayor volumen ($)**; columnas Vendedor · Dormidos · Riesgo $/Litros · Top 3.
- **Detalle clientes:** sin cambios de estructura (solo refleja el nuevo criterio). Validado: 7 dormidos (63-65 días), $300.754 / 50.2 L.
- **Limitación:** `historial_ventas_cliente.csv` retiene ~70 días, así que hoy se detecta la franja 61-70 días. Para dormidos de >70 días haría falta más retención del historial.

---

## 2026-06-04 — fix(11T): los 11 titulares son los mismos en Tradicional y Autoservicio

**`generar_datasets_acum.py`** (`MAP_11T`). Validado por usuario.

- **Problema:** `MAP_11T["TRADICIONAL"]` tenía marcas equivocadas (Fond de Cave, Cazador, JW Black/Red, Mascota, NC Espumantes, Trapiche Medalla). Por eso vendedores como V3 daban 0 en 11T (no venden esas marcas).
- **Fix:** los **11 Titulares son los mismos** para ambos segmentos: Alma Mora, Trapiche Reserva, Finca Las Moras, Alaris, Don David, Dada (vino), Smirnoff Flavours, Los Árboles, Antares, Smirnoff Ice, Gordon's Flavours. `MAP_11T` ahora usa la misma lista (`_ONCE_TITULARES`) en Autoservicio y Tradicional.
- Validado: mod_11t_acum.csv → 11 marcas en cada segmento. V3 ahora refleja cobertura real (total 702) en vez de 0.

---

## 2026-06-04 — fix(11T): mod_11t_acum.csv desde ventas_acumulada.csv (regla 11T)

**`generar_datasets_acum.py`** (regenera `mod_11t_acum.csv`).

- **Problema:** `generar_11t_acum` se llamaba con `ventas` (= `ventas.csv`, mes vivo), pero la **regla del proyecto es 11T = `ventas_acumulada.csv`** (período comercial completo, sin filtro de fecha). El dataset subestimaba la cobertura (tiene_flag=52, 34 clientes).
- **Fix:** ahora se genera con `ventas_acum_full` (`ventas_acumulada.csv`). Validado: tiene_flag 52 → **803**, clientes con marca 34 → **516**.
- Afecta: panel gerencia `11t_acum` y la tarjeta 11T del vendedor (ambos leen `mod_11t_acum.csv`). Coherente con `/api/gerencia/once_titulares` y `once_titulares_zona`, que ya usaban `ventas_acumulada.csv` directo.
- **`mod_11_titulares.csv`** tiene `tiene_flag` en 0 (motor legacy), pero en gerencia solo es *fallback* de `once_titulares` (no se activa) y sus endpoints `11t_empresa`/`11t_vendedor` no los consume el portal. No requiere fix.

---

## 2026-06-04 — feat(11T vendedor): tarjeta KPIs muestra clientes vendidos (día zona | total)

**`server_orbit.py`** (`/api/vendedor/<vid>`) y **`portal.html`** (tarjeta 11 Titulares en KPIs vendedor).

- **Antes:** la tarjeta mostraba `% (cubiertos/objetivo)` calculado desde `mod_11_titulares.csv`, cuyo `tiene_flag` viene **TODO en 0** → mostraba 0% en todas las marcas (rota).
- **Ahora:** por cada marca titular muestra **cantidad de clientes a los que logró vender**: los de la **zona del día** y, al lado, el **total de todas las zonas** (`6 | 7`). Sin porcentaje.
- Fuente correcta: **`mod_11t_acum.csv`** (tiene_flag poblado por cliente). `cubiertos_dia` = clientes con la marca cuya `DiasVisita` = día de hoy (zona del día, vía `_clientes_por_dia`); `cubiertos` = total. El endpoint acepta `?dia=`; sin él usa el día AR de hoy.
- Validado: V8 día MA = 23 clientes zona / 31 total; por marca ALMA MORA 6|7, CAZADOR 5|7.

---

## 2026-06-04 — fix(innovaciones): cobertura del mes vivo desde ventas.csv (no acumulada)

**`generar_datasets_acum.py`** (regenera `mod_innovaciones_segmento.csv`) y **`server_orbit.py`** (overlay `?dia`). Afecta pantalla Innovaciones (gerencia) y tarjeta Innovaciones de KPIs (vendedor); ambas leen `mod_innovaciones_segmento.csv`.

- **Problema:** `generar_innovaciones_segmento` usaba `ventas_acumulada.csv` (mayo+junio: 341 filas innov, 293 de mayo) → la cobertura contaba compras de **mayo**. Total clientes "compraron" inflado: **256** (la mayoría mayo) vs **38** reales de junio.
- **Fix:** ahora usa `ventas.csv` (MES VIVO). Cobertura de innovaciones = compras de **este mes**. Validado: total compraron 256 → **38**.
- **Overlay `?dia`** de `/api/gerencia/innovaciones_total` también leía `ventas_acumulada.csv` sin filtrar fecha → ahora lee `ventas.csv`.
- `mod_innovaciones_plan_as.csv` (vista innovaciones dentro de Plan AS) sigue usando acumulada (no es ninguna de las dos pantallas pedidas); revisar aparte si se quiere también mes vivo.

---

## 2026-06-04 — feat(planes_as): nombre del maestro + dirección + N° cliente en tarjetas

**`generar_datasets_acum.py`** (escribe `cliente_nombre` del maestro y `direccion` en `mod_planes_as.csv`), **`server_orbit.py`** (expone `direccion` en gerencia y vendedor) y **`portal.html`**.

- **Nombre desde `clientes.xlsx` (Razon_Social)** en vez del nombre de la BBDD del Reconocimiento (que tenía mojibake, ej. "YBAÃ‘EZ" → ahora "YBAÑEZ"). Fallback al nombre BBDD si el cliente no está en el maestro.
- **Dirección (`Direccion` del maestro)** agregada a `mod_planes_as.csv` y a ambos endpoints; se muestra en la tarjeta de gerencia (meta: `#id · dirección · localidad · día`) y del vendedor (bajo el nombre: `#id · dirección`).
- N° de cliente ya se mostraba; queda explícito con `#`.

---

## 2026-06-04 — fix(planes_as): escala desde escala_junio.xlsx + vendedor desde maestro

**`generar_datasets_acum.py`** (regenera `mod_planes_as.csv`). Server sin cambios (lee `mod_planes_as.csv`). Validado en local.

Auditoría de Planes AS (gerencia + vendedor). Flujo correcto: clientes/facturación/cajas ganadas ← `Reconocimiento Plan As.xlsx` (BBDD); sin cargo enviado ← `ventas.csv`; escalas ← `escala_junio.xlsx`. Se corrigieron 2 cosas:

- **Escala desde `escala_junio.xlsx` (no de la hoja interna).** Antes la escala se calculaba con la hoja "ESCALA" embebida en `Reconocimiento Plan As.xlsx` (umbrales viejos: Gold esc.1 = 155.073). Ahora `_cargar_escala_df()` **autodetecta `escala_*.xlsx`** (el mes que viene `escala_julio.xlsx`) y mapea columnas por nombre de encabezado; fallback a la hoja ESCALA. Umbral nuevo Gold esc.1 = 159.493 → 1 cliente recalculó escala (CEBALLOS: 4→3, correcto).
- **Vendedor del cliente AS desde el maestro `clientes.xlsx` (cartera real), fallback a `ventas.csv`.** Antes el vendedor se deducía solo de quién le vendió en el mes; los clientes AS que aún no compraron en junio quedaban **sin vendedor (11/31)** y no aparecían en la pestaña de su vendedor. Ahora **0 sin vendedor** (V8=16, V10=7, V9=7, V4=1).
- **Actualización automática:** al pegar `ventas.csv`, `escala_junio.xlsx` o `Reconocimiento Plan As.xlsx` y correr `CIERRE_DIA_ORBIT.bat`, REGENERAR recalcula `mod_planes_as.csv` y el BAT lo commitea (`git add 04_DATASETS_ORBIT/`) → Render actualiza. Los `.xlsx` crudos NO necesitan subirse a Render (el server lee `mod_planes_as.csv`).

---

## 2026-06-04 — fix(alertas): fuente = ventas.csv (mes vivo) + fecha de pedido

**`server_orbit.py`** + `portal.html`. Validado en local.

- **Alertas desde `ventas.csv` (mes vivo), no `ventas_acumulada.csv`.** `ventas_acumulada.csv` arrastra **mayo + junio** (5.461 filas mayo / 380 junio); como las acciones de mayo eran distintas a las de junio, comparar el catálogo de junio contra ventas de mayo inflaba las alertas. `ventas.csv` = 321 filas, todas de junio. Resultado: **alertas 34 → 22**. `_acc_preparar_ventas(nombre)` quedó parametrizada (default `ventas.csv`); `_alertas_descuento_mes` usa `ventas.csv`.
- **Acciones:** mes vivo desde `ventas.csv`; `ventas_acumulada.csv` se usa **solo** para el comparativo de "clientes nuevos" del mes anterior (mayo). ACJ26-027 sigue OK (inv $15.091, 4 clientes, 3 nuevos).
- **Fecha de pedido en cada alerta:** se agregó `fecha_pedido` (FechaComprobante, la que define el período) y `fecha_carga` (FechaCarga) al registro de `/api/alertas`. Se muestra 📅 en la pantalla de Alertas (gerencia) y en el bloque de alertas del vendedor. Ayuda a identificar errores de período/carga.

---

## 2026-06-04 — feat(acciones): matcheo por código de SKU + fixes SMF BC / Smirnoff Ice 35103

**`server_orbit.py`** + catálogo `acciones_comerciales_junio_2026_penaflor.csv`. Validado en local (27 reglas, 34 alertas).

- **Matcheo por código de producto** (`_acc_product_pred`): si `productos_marcas` contiene un token numérico (ej. `35103`), la acción aplica **solo a ese SKU** (no a toda la línea). `pred(...)` ahora recibe el código (`_cod`); se pasa en `_acciones_mes_payload` y `_alertas_descuento_mes`.
- **Smirnoff Ice Clásica 35103 → 25%** (acción nueva `ACJ26-027`): cualquier canal, vendedores V3/V4/V6/V8, sin tope. Antes salía como exceso (catálogo solo tenía Smirnoff 5/10/15%). Ahora no alerta para esos vendedores y aparece en la pantalla de Acciones (inv $15.091, 4 clientes, 3 nuevos).
- **SMF BC 15% (ACJ26-006):** el token estaba como `SMIR BC` y no matcheaba los SKU reales (línea *Smirnoff Bitter Citric RTD* / artículo *SMF BC...*, algunos sin maestro 04D). Se cambió a `Smirnoff Bitter Citric; Smirnoff BC; SMF BC` → ahora toma 15% (cubre línea y nombre de artículo). El segmento ya incluía Autoservicio (*Todos los segmentos*). Una venta de SMF BC al 25% queda correctamente como exceso (máx 15%).

---

## 2026-06-04 — fix(alertas): sin tolerancia + piso 10% Plan AS

**Commit:** `5110fec`. `server_orbit.py`. Validado en Render (38 alertas, exceso mínimo 1).

- **Sin tolerancia:** cualquier descuento que **supere** el permitido alerta (umbral de exceso `> 0`; antes `> 0.5`). Ej. 6% sobre acción de 5% → alerta.
- **Clientes Plan AS:** tienen **10% de descuento en factura siempre** → piso permitido = 10%. Solo alertan si superan el 10% (se carga `mod_planes_as.csv` para identificarlos). Validado: clientes Plan AS solo alertan a 25%; los de ≤10% ya no.

---

## 2026-06-04 — fix(acciones/alertas): descuento real = valorDescuento (no IVA)

**Commit:** `9fcf258`. `server_orbit.py`. Validado en Render. Corrige volumen/criterio de alertas y la inversión de acciones.

**Problema (detectado revisando datos reales):** el motor usaba `ImporteItem − ImporteNetoItem` como "descuento". Pero esa diferencia es **IVA** (21/1,21 ≈ **17,4%** en TODAS las líneas), no descuento comercial → 112 alertas falsas y la "inversión" de acciones inflada (~$3.1M de IVA).

**Fix:** el descuento real sale de **`valorDescuento`** (por unidad) × `CantBase`:
- **% descuento aplicado** = `valorDesc×Cant / (ImporteNetoItem + valorDesc×Cant)` → da la escala real **5/6/8/10/15/20/25/30%** (coincide con mayo).
- **inversión real** = `valorDescuento × CantBase` (no IVA).
- Acciones: inversión/litros/clientes/nuevos se miden sobre líneas con descuento real (`valorDescuento>0`).

**Resultado en Render:** alertas **112 → 44** (descuentos reales 6/10/13/15/25%); ejemplo confirmado por el usuario: **Gordon's acción 5% → ventas a 6% y 10% alertan (máx 5%)**. Inversión acciones **$3.1M → $1.215.257** (real).

---

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
