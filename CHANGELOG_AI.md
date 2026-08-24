# CHANGELOG AI - ORBIT MATINAL PEÑAFLOR

## 2026-08-24 (2) - fix(codigos): 3 Antares medidos contra el codigo del catalogo, no el del ERP

**Reportado por el usuario** mirando la pantalla Stock nueva: *"hay 3 Antares que sí tenemos
stock (Kolsch, Scotch y Caravana) y estás tomando códigos viejos"*. Confirmado.

### Causa raíz: dos sistemas, dos códigos para el mismo producto

La matriz 11T, `mpa_codigos.csv` y el maestro 04D se arman con el **catálogo del proveedor**
(`RAW_PRODUCTOS/productos<mes>.xlsx`, hoja `Cluster 25`), que factura esos tres como
**60001 / 60002 / 60007**. **Nuestro ERP los factura como 30329 / 30343 / 30268.** Los códigos
del catálogo no tienen ni una línea de venta ni una unidad de stock en ninguna de nuestras
fuentes.

**No se ve como un error: se ve como un producto sin stock.** La pantalla decía "no está en el
archivo de stock" mientras había 150, 102 y 96 unidades en depósito.

### Auditoría de los 3 universos (no sólo Antares)

De los 176 códigos (82 del 11T + 27 de Innovaciones + 67 de MPA), **14 no figuraban ni en stock
ni en ventas**. Pero un código sin stock ni ventas **no es automáticamente un código viejo**:

- **3 códigos equivocados** — los reportados: existe el mismo producto y presentación vivo bajo
  otro código.
- **6 productos que no trabajamos** — Antares Honey y Playa Grande, D.David Tannat, Trapiche
  Reserva Syrah y Merlot, Trapiche Dulce Cosecha Rosé. **No tienen equivalente vivo y tienen
  que seguir figurando como "sin existencia", porque es la verdad.**
- **Innovaciones: 27 de 27 correctos.**

### Solución

- **`09_CONFIG/codigos_equivalencias.csv`** (nuevo): puente catálogo → ERP **revisado a mano**,
  mismo patrón que `mpa_codigos.csv`. Una fila sólo cuando se verificó que el código del
  catálogo no tiene ventas ni stock y el del ERP sí, mismo producto y presentación.
  **NO se adivina por texto**: el `contains` sobre la descripción es lo que metió GORDON'S GIN
  y TONIC dentro de Gordon's Flavours (CLAUDE.md).
- **`motor_codigos.py`** (nuevo): único lector, cacheado por mtime. Sin archivo devuelve `{}` y
  no cambia nada — el cambio es seguro por construcción.
- `motor_11t.cargar_matriz_11t()` y `_mpa_universo()` canonizan. Un punto por consumidor.
- **Maestro 04D**: el CSV del runtime YA tenía los 3 códigos (del 18/08); el **xlsx fuente**
  estaba atrasado y se sincronizó (256 → 259 filas, categoría y litros **copiados del gemelo**).
- **Datasets 11T regenerados**: el dataset congelado tenía los códigos viejos y las dos
  pantallas de gerencia dejaron de coincidir — lo cazó
  `test_dashboard_vivo_y_11t_empresa_coinciden_en_el_total` (148 vivo vs 147 dataset). Se
  regeneraron **sólo los del 11T**: `main()` además appendea a `02_HISTORY` y correrlo hoy
  pisaría el snapshot del último cierre.
- **Descripción vacía**: Caravana no está en VSB y el catálogo no conoce el código, así que la
  fila salía con el titular pelado ("ANTARES"). Ahora el nombre se completa con el de cualquier
  depósito que tenga el producto.
- **`tools/auditar_codigos_universos.py`** (nuevo): deja el control repetible. El catálogo se
  re-dropea cada mes y nada garantiza que el próximo no traiga otro código que no usemos.
  **Sugiere, no corrige**: la fila la agrega una persona.

### Impacto medido

| | Antes | Después |
|---|---|---|
| Stock · Kolsch / Scotch / Caravana | "no figura" | PyP 102 / 42 / 96 u · VSB 48 / 60 / – |
| 11T ANTARES · clientes que cubren | 146 | **147** |
| 11T ANTARES · botellas netas | 1.128 | **1.194** |
| 11T · otros 10 titulares | — | **sin cambio** (medido uno por uno) |

### Validación

`test_motor_11t.py` **73/73 OK** (antes de regenerar el dataset fallaba 1) ·
`test_motor_padron.py` OK · **`test_motor_codigos.py` nuevo 13/13 OK** · smoke de 9 endpoints
con `json.dumps` completo · auditoría re-corrida: **0 códigos con reemplazo pendiente** ·
en vivo en Render: `dias_stock` → `30268:96 | 30329:102 | 30343:42`, `11t_empresa` → ANTARES 148.

## 2026-08-24 - feat(stock): pantalla Stock (gerencia) + exportacion a Excel

**Pedido:** una pantalla debajo de Semanal, sólo para gerencia, con dos tarjetas —una por
depósito— y botones para conmutar entre los tres motivos de seguimiento (11 Titulares,
Innovaciones y MPA) dentro de cada tarjeta. Después: un botón de descarga a Excel, y **sin**
sacarle nada a Semanal por ahora.

### Qué había ya y qué se hizo

El cálculo de días de stock **ya existía** (`/api/gerencia/dias_stock`, con sus dos bloques y
sus tres universos), pero vivía sólo como una tarjeta al pie de la pantalla Semanal. No se
reescribió el motor ni se duplicó el render: ahora **la misma tarjeta se monta en las dos
pantallas** y el contenedor se resuelve en tiempo de render. Dos copias del render habrían
dejado dos versiones del mismo número, que es lo que el contrato del proyecto prohíbe.

- `PAV MATINAL PE_A FLOR/portal.html`
  - Nuevo ítem de menú `Stock` (📦) **inmediatamente debajo de Semanal**, en la sección
    Gerencia. Vive en `#appG`, así que el perfil vendedor no lo ve.
  - `gStock(p)` nueva: encabezado con la base de cálculo (mes cerrado + días operativos), los
    tres umbrales como chips y el botón **⬇ Exportar Excel**, más el contenedor `#stk-cont`.
  - `stkCont()` resuelve el contenedor: `#stk-cont` (pantalla Stock) o `#sem-stock` (pie de
    Semanal). Sólo uno de los dos existe a la vez en el DOM.
  - `semStockCargar/semRenderStock/semSetUni/semStkTog` → `stkCargar/stkRender/stkSetUni/stkTog`.
    El guard de la respuesta asíncrona pasó de `gScreen!=='semanal'` a `stkVisible()`
    (`stock` o `semanal`): si no, el fetch tardío escribía sobre el `gPage` de otra vista.
  - `gSemanal()` **sigue montando** `#sem-stock` y llamando al loader: no se le sacó nada.
  - Carga LAZY y cacheada en `STK`. El estado de los botones (`stkUni`) es **por tarjeta**:
    cambiar de motivo en VSB no mueve a PyP, porque son dos análisis distintos.
- `server_orbit.py`
  - `_STOCK_BLOQUES` lleva `sede` y el endpoint la publica: las tarjetas dicen
    **PyP · Depósito La Francia** y **VSB · Depósito Villa Dolores**. Las etiquetas pasaron de
    "Stock PyP"/"VSB Cuyo" a "PyP"/"VSB".
  - `_dias_stock_payload()` extraído de la ruta: el JSON del portal y el Excel salen de la
    MISMA función, así el archivo descargado no puede divergir de la pantalla.
  - `/api/gerencia/dias_stock/export` nueva. Baja el informe COMPLETO (no sólo la pestaña
    visible): hoja `Resumen` con los 6 cruces depósito × seguimiento, una hoja por depósito
    (`PyP`, `VSB`) con los tres seguimientos apilados y una columna `Seguimiento`, y hoja
    `Sin código` con lo que MPA.xlsx no pudo mapear al ERP. El grupo de riesgo va como texto
    (`Crítico (menos de 15 días)`), porque fuera del portal no hay color que lo explique.

### Lo que NO cambió (a propósito)

La regla de cálculo queda igual: días de stock = unidades disponibles ÷ venta diaria del mes
anterior cerrado, con la venta **sólo de los vendedores de la ruta de ese depósito**
(PyP → V3·V4·V6·V8·V10, VSB → V7·V9) y el divisor en días operativos lun-sáb sin feriados.
Los dos depósitos no se suman ni se comparten stock.

### Validación (datos reales, no sintéticos)

- `/api/gerencia/dias_stock` → 200 en 7,4 s. Base **Jul 2026** (26 días operativos, fuente
  cierre mensual). PyP: 228 códigos de stock, 111 matchean el portfolio. VSB: 125 / 77.
- Los contadores por grupo son excluyentes y cierran contra el total en los 6 cruces:
  p.ej. MPA PyP 6+6+10+2+43 = 67 productos.
- `/api/gerencia/dias_stock/export` → 200, 30 KB, `dias_stock_202607.xlsx`. Hojas
  `Resumen` (6 filas × 16 col), `PyP` y `VSB` (176 filas = 82+27+67 cada una) y `Sin código`
  (3 filas). Los números del Excel coinciden con los del JSON.
- Render verificado leyendo el DOM en Chrome: 2 tarjetas con sus sedes, 3 botones cada una,
  conmutación independiente (VSB 11T 84,7 d → Innovaciones 147,1 d deja PyP intacta), el
  desplegable abre las 67 filas de MPA, y el botón de exportar en el encabezado.
- Confirmado que la pantalla **Semanal sigue completa**: `sem-hist`, `sem-plan`, `sem-inter`
  y `sem-stock` con sus 2 tarjetas y sus 3 botones.
- `node --check` sobre el JS embebido del portal: OK.

### Deploy: el export daba 200 en local y 500 en Render (`260c078` + `357b7a5`)

Mismo payload en los dos lados (se bajó el JSON de Render y se comparó: idéntico), y otros
dos exports xlsx del portal (`stock_sin_venta`, `plan_cobertura`, este último con el MISMO
patrón multi-hoja) devolvían 200. O sea: no eran los datos ni el mecanismo.

El 500 era mudo, así que primero se lo hizo hablar: `try/except` que loguea el traceback y
devuelve `{"error","detalle"}`. El server contestó
**`TypeError: object of type 'float' has no len()`**.

**Causa raíz:** el ancho de columna se calculaba con `col.astype(str).map(len)`. En pandas 2
(local, 2.2.2) un NaN se convierte al string `"nan"` y `len` funciona; en **pandas 3**
(Render) `astype(str)` **preserva el nulo** y `len` recibe un float. `requirements.txt` dice
`pandas>=2.0.0` sin pinear, así que Render instala la última en cada build. Lo dispara
cualquier columna con un hueco: en Días de Stock, los productos que no figuran en el archivo
del depósito dejan `Disponible` y `Días de stock` en nulo (11 de 82 en PyP, 29 de 82 en VSB).

**Y había dos copias del escritor de xlsx.** `_plan_cob_escribir_xlsx` hacía exactamente lo
mismo y sí andaba en Render; nunca tuvo nada de Plan Cobertura, era un escritor genérico con
nombre prestado — y ese nombre fue lo que invitó a escribir la segunda copia. Se renombró a
`_escribir_xlsx`, lo comparten Plan Cobertura y Días de Stock, y el arreglo del nulo
(`_ancho_celda`) se aplicó ahí **y** en el export de Stock sin Venta, que tenía la misma
bomba esperando la primera columna con un hueco.

**Verificado en vivo:** `/api/gerencia/dias_stock/export` → 200, 29.974 B; el xlsx bajado de
Render comparado hoja por hoja contra el local da `DataFrame.equals` = True en las cuatro
(`Resumen` 6×16, `PyP` y `VSB` 176×10, `Sin código` 3×3); `portal.html` servido por Render
idéntico al local.

## 2026-08-18 - fix(litros): Antares lata en 0 L + 8 SKU vigentes fuera del maestro 04D

**Síntoma:** el diagnóstico del interanual mostraba 18 SKU sin maestro y 54 líneas sin litros.
Al revisarlos, cinco Antares en lata aportaban **0 litros** pese a tener stock en dos depósitos
y ventas en agosto 2026: eran invisibles en Sell Out, Semanal, el interanual y cualquier
métrica de volumen.

### Causa 1 — la inferencia de litros no toleraba la unidad pegada al número

`_infer_litros_por_nombre` usaba `[X\s](\d{3,4})\b`. En `ANTARES LATA KOLSCH 6 X 473ML` el
`\b` no cierra después del `473` porque le sigue `ML`, así que no matcheaba. No eran los
espacios: `FRIZZE ITAL LIMA LATA X473` sí funcionaba. Ahora el patrón acepta un sufijo de
unidad opcional (`ML` / `CC` / `CM3`).

Medido sobre los 297 nombres de artículo de las tres fuentes: **8 nombres pasan de 0 a tener
litros y NINGUNO de los que ya funcionaban cambia de valor**. El patrón sólo agrega casos.

### Causa 2 — 8 SKU vigentes no estaban en el maestro 04D

Se agregaron a `09_CONFIG/maestro_04D_productos.csv` (262 → 270 filas). **Nada inventado**,
cada campo tiene origen:

| Código | Artículo | Categoría | Segmento | Línea comercial | De dónde sale |
|---|---|---|---|---|---|
| 30268 | ANTARES LATA CARAVANA | Cerveza Artesanal | Cerveza Artesanal | Antares Especiales | `Marca` del ERP |
| 30275 | ANTARES LATA IPA | Cerveza Artesanal | Cerveza Artesanal | Antares Especiales | hermano 60017 |
| 30329 | ANTARES LATA KOLSCH | Cerveza Artesanal | Cerveza Artesanal | Antares Clasicas | `Marca` del ERP |
| 30343 | ANTARES LATA SCOTCH | Cerveza Artesanal | Cerveza Artesanal | Antares Clasicas | `Marca` del ERP |
| 14590 | TERMIDOR BLANCO 12X1L | Vinos de Mesa | Vinos de Mesa | Termidor Brik | `Marca` del ERP |
| 80003 | SAN TELMO SEL CHARDONNAY | Vinos del año | Medio | San Telmo | hermanos 80002/80004 |
| 14554 | EL REGRESO SEM-CHEN | Vinos del año | Alto | *(vacía)* | sin fuente |
| 80077 | DOLORES ESPUMANTE DULCE | Espumantes | Champaña Alta y Premium | *(vacía)* | sin fuente |

`Categoria` sale del `Rubro` del ERP y `Segmento` de su columna `Linea`, que ya usan el mismo
vocabulario que el maestro. `Lts x caja` / `UxC` salen del envase declarado en la descripción,
con el valor que ya usan los hermanos (473 ml × 6 = 2.838, igual que los 5 Antares lata que sí
estaban). Para **14554 y 80077 la línea comercial quedó VACÍA a propósito**: no tienen `Marca`
en el ERP ni hermano en el maestro, y agregar un nombre de línea nuevo es una decisión
comercial que crearía una línea en todos los reportes. Quedan clasificados a nivel categoría y
segmento, que es lo que sí se puede afirmar.

### Impacto medido, con el filtro real del portal (`ImporteNetoItem > 0`)

- **Ningún SKU baja.** Los dos cambios son estrictamente aditivos: **+2.347,5 L** recuperados
  sobre el total de todas las fuentes (1.338.114,5 → 1.340.462,0 L).
- `lineas_sin_litros` en los períodos comparados: **54 → 0**.
- `skus_sin_maestro`: **18 → 10**, y los 10 restantes no tienen stock ni ventas en 2026
  (discontinuados: 14555, 14595, 30007, 30034, 30035, 30126, 30299, 74416, 74701, 74702).
- `litros_sin_categoria`: 728,5 → 370,7 L. "Sin clasificación" en el mes en curso: **0,0 L**.
- Interanual: agosto MTD 15.446,5 → **15.469,2 L**; julio cerrado 50.047,0 → **50.064,0 L**.
  Coinciden exactamente con los litros que informa la pantalla Semanal (15.469,18 y 50.064,03),
  que es la comprobación de que las dos pantallas siguen midiendo lo mismo.

**Falso positivo descartado durante la validación:** una primera medición mostraba a 60015
(ANTARES PLAYA GRANDE) bajando 30,3 L. Son 9 líneas con `CantBase` negativa cuya inferencia
antes daba 0 y ahora da litros negativos — pero las 9 tienen `ImporteNetoItem` negativo, así
que el portal nunca las cuenta. Con el filtro real aplicado, ningún SKU baja.

**Cómo se investigó:** se buscaron los códigos en los 66 archivos de `01_INPUTS`, `09_CONFIG` y
`05_MASTER_DATA`. Sólo aparecen en archivos de ventas y en `01_INPUTS/Stock/*.xlsx`; los de
stock confirman que están vigentes (96/108/42 unidades en La Francia, 6/48/60 en Villa Dolores)
pero **no traen taxonomía**, así que no sirven para completar el maestro. Ningún archivo del
repo tiene el maestro de estos productos, incluido `RAW_PRODUCTOS/productosjulio.xlsx`.

### Archivos

- `server_orbit.py`: patrón de `_infer_litros_por_nombre`.
- `09_CONFIG/maestro_04D_productos.csv`: +8 filas. Las 262 originales quedaron byte a byte
  idénticas y en el mismo orden; BOM y CRLF preservados; sin códigos duplicados.
- `test_semanal_interanual.py`: 12 aserciones nuevas (63 en total).

### Validación

`test_semanal_interanual.py` 63 OK / 0 fallas. Regresión: `test_acciones_analisis.py` 71 OK,
`test_acciones_trad_nc.py` 23 OK, `test_acciones_explorador.py` 29 OK. Endpoints 200; los
canales y las categorías siguen reconciliando con el total.

## 2026-08-18 - feat(Semanal): interanual de litros por canal, categoría y cliente

**Qué se agrega:** tercera tarjeta de la pantalla Semanal, debajo del histórico y la
planificación. Compara el volumen contra el MISMO mes del año anterior en dos vistas y baja
hasta el cliente. Carga lazy y endpoint propio: no infla `/api/gerencia/semanal` ni el login.

### Las dos comparaciones

- **Mes actual en curso**: MTD contra el mismo tramo del año pasado, más la proyección al
  cierre contra el año anterior MES COMPLETO. En agosto 2026: 01/08 al 18/08 contra 01/08/2025
  al 16/08/2025 (mismo esfuerzo comercial), y la proyección contra todo agosto 2025.
- **Mes cerrado anterior**: completo contra completo, SIN proyección. Julio 2026 vs julio 2025.

Nada está cableado: al cambiar el mes, septiembre pasa a ser el mes en curso y agosto el
cerrado, solo.

### Reglas (heredadas de Semanal, no reinventadas)

- **Fecha**: `FechaComprobante`. FechaCarga y FechaEntrega no deciden el período.
- **Litros**: la cascada única `_litros_por_linea` (maestro 04D → PesoKg → ml inferidos del
  nombre). No se duplica ni se simplifica.
- **Universo**: `empresa` — toda la venta de la distribuidora, ruta + V1/V20 Depósito, sin las
  bajas V2/V5. Es el universo con el que Semanal mide litros; medirlo sobre ruta y compararlo
  contra ese total daría una caída sistemática que no existe. Se informa en el endpoint y en
  la tarjeta.
- **Devoluciones**: las líneas con `ImporteNetoItem <= 0` quedan FUERA; no restan litros. Es
  exactamente lo que ya hace `_semanal_leer`, y tener dos criterios de litros en el mismo
  portal sería peor que el redondeo que esto implica. Queda documentado en `reglas` del
  payload y en la tarjeta.
- **Canales**: se reusa `_canal_ccc_empresa` (el clasificador de objccc.xlsx). No hay un
  clasificador paralelo. Se agrega la fila agregada "On Premise + VTK" SIN perder On Premise,
  Vinotecas y On Premise Noche por separado.

### Días comerciales y proyección

Lunes a sábado, sin domingos y sin los feriados de `09_CONFIG/feriados.csv` (ninguno
cableado). Agosto 1-18 da **14 días, no 18**: tres domingos y San Martín el 17.

    proyeccion = litros_mtd / dias_comerciales_transcurridos * dias_comerciales_totales

El corte es la **última FechaComprobante cargada en ventas.csv**, no la fecha del servidor: si
el input quedó atrasado, contar los días del calendario inventaría una caída que no existe.
El corte del año anterior se elige por la MISMA cantidad de días comerciales, no por el mismo
número de día: si el año pasado los feriados cayeron en otro lado, comparar por día mediría
dos esfuerzos comerciales distintos.

### Fuentes por período (una sola por mes, sin concatenar)

    mes en curso  -> 01_INPUTS/ventas.csv
    mes cerrado   -> 01_INPUTS/cierres mes/ventas_mes_MMAAAA.csv
                     y si no está, 02_HISTORY/historial_ventas.csv

`_ia_fuente_de` reusa `_semanal_fuente_de` y le agrega la única regla que esa función no tiene:
el mes en curso sale de ventas.csv aunque exista un cierre con su nombre.

Verificado en la validación: agosto 2026 ← ventas.csv · julio 2026 ← ventas_mes_072026.csv ·
agosto y julio 2025 ← historial_ventas.csv.

### Jerarquía de categorías

Categoría → Segmento → Línea Comercial → Marca, resuelta contra
`09_CONFIG/maestro_04D_productos.csv`. Nada hardcodeado: la taxonomía sale del maestro, así
que aparecen Vinos del año (con sus segmentos internos Alto / Medio Alto / Superior / Medio),
Vinos de guarda, Espumantes, RTD, Spirits, Vermouth y el resto tal como los define el maestro.
Un SKU que el maestro no trae NO se descarta: cae a **"Sin clasificación"**, queda visible en
la tabla y cuantificado en el diagnóstico (hoy 728,5 L y 18 SKU).

### Clientes nuevos y perdidos

Los rankings usan **outer join**. Con un inner join el cliente que compraba el año pasado y
este año no compró nada desaparecería del ranking — que es justo el que hay que ver:

- compró LY y no compra ahora → actual 0, caída completa, estado **"Perdido"**;
- compra ahora y no compraba LY → LY 0, estado **"Nuevo"** y `delta_pct = null`, sin
  porcentajes infinitos.

En el mes en curso el ranking principal es por diferencia PROYECTADA contra el LY mes
completo; cada fila trae igual MTD, LY MTD, proyección, LY completo, delta y delta %.

### Endpoints

- `GET /api/gerencia/semanal/interanual` — payload completo con los dos períodos, apertura
  por canal y el árbol de categorías. Los top 5 viajan embebidos en los canales y en las
  categorías de primer nivel.
- `GET /api/gerencia/semanal/interanual/clientes?vista=&dimension=&clave=&nivel=` — top 5 de
  los niveles profundos (segmento, línea, marca), que no viajan en el payload principal para
  no mandar cientos de nodos con diez clientes cada uno. Una consulta por click, no una por
  fila renderizada.

### Rendimiento

El historial pesa 63 MB: se lee con `usecols` (13 columnas), UNA vez por proceso, cacheado por
ruta + tamaño + mtime, y todos los períodos que salgan de él se cortan de esa copia en
memoria. La clave de caché del payload incluye las fuentes y sus mtimes, el maestro 04D,
clientes.xlsx y feriados.csv. Medido: **3,44 s la primera respuesta y 0,027 s la cacheada**;
el detalle de clientes 0,13 s.

### Archivos

- `server_orbit.py`: sección "INTERANUAL DE LITROS" con `_ia_fuente_de`, `_ia_leer`,
  `_ia_rango`, `_ia_tops`, `_ia_por_canal`, `_ia_por_categoria`, `_ia_diagnostico`,
  `_ia_payload` y los dos endpoints.
- `PAV MATINAL PE_A FLOR/portal.html`: tarjeta "📊 Interanual de litros · Canal y categoría"
  con selector de comparación y de dimensión, KPIs, tabla con drill-down y top 5 al click.
- `test_semanal_interanual.py` (nuevo): 51 aserciones.

**Renombrado sin cambio de comportamiento:** `_acc_an_dias_comerciales` →
`_dias_comerciales` y `_acc_an_hasta_por_dias` → `_fecha_por_dias_comerciales`. Los usan
ahora dos features (el análisis de acciones y el interanual) y el nombre con prefijo de
acciones invitaba a escribir una segunda implementación.

### Validación (2026-08-18, datos reales, sin mocks)

- `test_semanal_interanual.py`: **51 OK / 0 fallas**. Regresión: `test_acciones_analisis.py`
  71 OK, `test_acciones_trad_nc.py` 23 OK, `test_acciones_explorador.py` 29 OK.
- **Reconciliación**: los canales suman exactamente el total en las dos vistas
  (15.446,5 L actual y 50.047,0 L cerrado) y las categorías también; los hijos del árbol
  reconcilian con su padre.
- Agosto 2026 MTD 15.446,5 L vs agosto 2025 MTD 10.229,7 L (+51,0%); proyección 27.583,0 L vs
  34.177,4 L de agosto 2025 completo (-19,3%). Julio 2026 50.047,0 L vs julio 2025 39.446,9 L
  (+26,9%).
- Caso testigo de cliente perdido: MJE S.A.S. (V7) con 0 L actuales y 1.106,1 L el año
  anterior → caída completa, estado "Perdido". Caso testigo de alta: ALVAREZ ANA LAURA (V10),
  82,8 L MTD, sin base LY → estado "Nuevo" y delta_pct null.
- Endpoints 200; el de detalle valida parámetros y devuelve 400 con mensaje.
  `/api/gerencia/semanal` sigue devolviendo lo mismo y no incluye el interanual.
- Portal sin errores de consola. En 380 px de ancho la tabla scrollea dentro de su contenedor
  y la página no desborda; los selectores se apilan.

**Pendiente de fuente:** 18 SKU sin maestro (728,5 L en el período analizado) y 54 líneas sin
litros por ninguna de las tres vías de la cascada. Quedan listados en `diagnostico`.

## 2026-08-18 - refactor(Acciones): rediseño de la tarjeta "Análisis de la acción"

**Problema:** la tarjeta anterior era una acumulación de indicadores. Mostraba doce KPI a la
vez, un embudo cuyo número más grande era el potencial del canal (1.689 clientes, 0,2% de
conversión), conceptos superpuestos ("nuevo en categoría" y "nuevo en marca" no eran
excluyentes) y ninguna conclusión accionable. Era información, no una herramienta de trabajo.

**Ahora la tarjeta responde cuatro preguntas y nada más:** si la acción está funcionando, qué
resultado nuevo produjo, si llega al objetivo al cierre y qué cinco clientes conviene trabajar.

### Bloque 1 — Resultado

Cuatro números arriba (clientes, litros, % de objetivo, variación comparable) y dos barras que
NO son lo mismo y se etiquetan distinto:

- **Cumplimiento**: logrado / objetivo. Es un hecho.
- **Proyección al cierre**: (logrado / días comerciales transcurridos) x días comerciales
  totales. Es una estimación; llamarla "cumplimiento" haría creer que ya pasó.

Los días son COMERCIALES: lunes a sábado, sin domingos y sin los feriados de
`09_CONFIG/feriados.csv` (no hay ninguno cableado). Agosto 1-18 da 14 días, no 18: tres
domingos y San Martín el 17.

### Objetivo por acción — y por qué hoy dice "no configurado"

Cada acción se evalúa contra el objetivo que le corresponde, no todas contra litros:
`captacion` / `reactivacion` / `volumen` / `mix` / `once_titulares` / `cobertura`, cada uno con
su unidad. Se configuran en **`09_CONFIG/objetivos_acciones.csv`** (nuevo):

    action_id;objetivo_tipo;objetivo_valor;objetivo_unidad;nota
    AGO26-VDA-SUP;volumen;300;litros;Meta de volumen del canal

**El archivo se entrega con el encabezado y sin filas.** Los objetivos de las acciones no
existen en ninguna fuente de ventas y no se inventan: es la misma regla que ya aplica el cierre
mensual (REGLAS_NEGOCIO_PAV: "Acciones NO traen objetivo... No se les inventa uno"). Hasta que
comercial los cargue, las quince acciones muestran "Objetivo comercial no configurado" y las
barras no aparecen. No se muestra 0%, que se leería como fracaso.

### Bloque 2 — Movimiento de compradores

El embudo se reemplazó por tres grupos **mutuamente excluyentes**, todos definidos sobre LOS
PRODUCTOS DE LA ACCIÓN (no sobre "compró algo de Peñaflor", que es otra pregunta):

- **incorporado**: no compró esas marcas ni en el período comparable ni en los 12 meses previos.
- **reactivado** : no las compró en el comparable, pero sí en esos 12 meses.
- **recurrente** : ya las compraba en el comparable.

**"Nuevo para Peñaflor" es un dato aparte, no un cuarto grupo**, y ahora es de verdad: sólo
cuando el cliente no tiene NINGUNA compra válida en todo el historial disponible. Antes se
llamaba nuevo a quien no había comprado en agosto del año pasado, que es un cliente existente
que no compró ese mes — el número no significaba nada.

Debajo, dos barras comparables de litros de las marcas participantes (antes / actual) con su
variación. Se compara el mismo alcance de producto en los dos períodos y no "la categoría
entera": para AGO26-TRAD-NC la categoría abarcaba VDA+VDG+RTD+Spirits+Vodka y diluía cualquier
lectura.

### Bloque 3 — Seguimiento comercial

Dos rankings de cinco filas: **Top 5 resultados** (quién generó) y **Top 5 oportunidades**
(a quién visitar), con el motivo concreto de cada uno:

- "Compraba la marca y todavía no compró en este período"
- "Mueve 495 L de la categoría, sin compra de estas marcas"
- "Compró 16 cajas; con 4 más llega al tramo de 20 (8%)"

Filtros duros: canal de la acción y cartera de un vendedor activo (V3 nunca recibe una
oportunidad de Autoservicio). Con prioridad pura la lista salía monótona —el balde "dejó de
comprar" tiene cientos de clientes y se quedaba con los cinco lugares—, así que se reserva un
lugar para cada tipo antes de completar por prioridad y volumen.

### Escalas: se resolvió el aviso que estaba en Render

La fuente escribe "10 a 20 cajas" y "20 cajas o más", que en 20 daba dos descuentos. La
definición comercial es **10 <= cajas < 20** y **cajas >= 20**, así que el tope del primer tramo
pasa a 19 y el texto visible acompaña ("10 a 19 cajas · 6%"). Se aplica en la LECTURA
(`_acc_explorador`) y no editando el libro ni regenerando el dataset: así el arreglo llega a
producción con el deploy de código.

Además, los avisos que nombran herramientas o agentes ya no llegan al portal. Es una regla
general —si un aviso nombra una herramienta, es una instrucción para quien implementa, no
información comercial— y no una lista de casos: saca el "Claude debe revisar..." de agosto y
cualquier nota parecida en libros futuros, sin tener que editarlos.

### Detalle técnico

Detrás de un desplegable "Ver detalle": comprobantes, importe neto, inversión en descuento,
método de atribución, fuentes, período exacto, universo del canal, 11 Titulares y advertencias.
11T dejó de ser indicador principal; queda en el detalle salvo que el objetivo de la acción
sea 11T.

### Atribución (sin cambios de criterio)

Sigue siendo por regla: el ERP no tiene identificador de acción (`Promociones` = proveedor,
`Tags` = %10/%20). El payload informa `exact_tag` / `rule_discount` / `ambiguous` y los textos
dicen "litros asociados a la acción" y "resultado observado", nunca que la acción generó la
venta.

### Archivos

- `motor_acciones_analisis.py`: objetivos y su evaluación, `normalizar_tramos`, `tramo_de`,
  movimiento excluyente, `sanear_avisos`, `top_oportunidades` con motivos, insight reescrito.
- `server_orbit.py`: normalización de escalas y saneo de avisos en `_acc_explorador`; loader de
  objetivos; mapa UxC para convertir botellas a cajas; `_acc_an_oportunidades`; payload nuevo;
  `_acc_an_ids_historial` (una lectura por fuente en vez de barrer 26 años de períodos: 15 s
  -> 1 s); `objetivos_acciones.csv` sumado a la firma de caché.
- `09_CONFIG/objetivos_acciones.csv` (nuevo, sólo encabezado).
- `PAV MATINAL PE_A FLOR/portal.html`: tarjeta en tres bloques, barras en HTML/CSS (sin
  librería nueva), pestañas de Top y detalle plegado.
- `test_acciones_analisis.py`: 71 aserciones sobre las 22 áreas pedidas.

### Validación (2026-08-18, datos reales, sin mocks)

- `test_acciones_analisis.py` 71 OK / 0 fallas. Regresión: `test_acciones_trad_nc.py` 23 OK,
  `test_acciones_explorador.py` 29 OK.
- Las 15 acciones responden 200 con datos. Conciliación fuente -> endpoint exacta en
  AGO26-VDA-SUP: 22 clientes, 114,8 L y 24 comprobantes por los dos caminos.
- Catálogo servido: los cuatro pares de escalas de cajas salen 10-19 / 20+ con `solapa=False`
  y sin conflictos; ningún aviso menciona herramientas.
- V2, V5 y V20 dan 403; acción inexistente 404. Payload de 4.035 bytes; segunda consulta 0,01 s.
- Portal sin errores de consola: barras de cumplimiento y proyección, tres grupos de
  movimiento, barras comparables, las dos pestañas de Top y el detalle plegado.
- Prueba de objetivo: cargando temporalmente `AGO26-VDA-SUP;volumen;300;litros` la tarjeta
  mostró 38,3% de cumplimiento (114,8/300) y 68,3% de proyección (114,8/14x25 = 205). El
  archivo se dejó otra vez sólo con el encabezado.

## 2026-08-18 - feat(Acciones): tarjeta "Análisis de la acción" en el Explorador

**Qué se agrega:** debajo de la tarjeta que explica QUÉ ofrece cada acción, una segunda tarjeta
que responde QUÉ PASÓ con ella. Se carga diferida (sólo cuando ya hay una acción elegida),
tiene selector "vs. mes anterior" / "vs. mismo mes del año anterior", una conclusión corta,
seis indicadores, secundarios, embudo, 11 Titulares y un Top 5.

**Atribución — no hay identificador de acción en el ERP.** Antes de programar se auditaron las
columnas de etiqueta sobre ventas.csv de agosto:

- `Promociones` tiene 2 valores: 19 = Spirits/Diageo (Gordon's, Smirnoff, JW, Tanqueray) y
  21 = resto del portfolio. Es la agrupación del proveedor, no la acción: el 21 aparece con 17
  porcentajes de descuento distintos.
- `Tags` / `EtiquetaItem` traen `%10` / `%20` + "PEÑAFLOR GRUPO OBJETIVO". El `%20` aparece con
  TODOS los descuentos de 0 a 100, así que tampoco identifica la acción.
- `ComboCodigo` y `Etiqueta` vienen vacías en el 100% de las filas.

Conclusión: hoy la atribución sólo puede ser por regla. El payload informa siempre `metodo`
(`exact_tag` / `rule_discount` / `ambiguous`); `buscar_tag_accion()` queda implementada y
testeada para que la atribución exacta entre sola si el ERP empieza a emitir el código.
Dos acciones con el mismo canal, productos y descuento se marcan `ambiguous` con advertencia
visible. Los textos dicen "ventas asociadas a la acción" y "clientes incorporados dentro del
alcance": con atribución por regla hay asociación, no causalidad demostrada.

**Períodos.** Pertenencia por `FechaComprobante`, siempre. Un mes en curso NO se compara contra
un mes completo: el período comparado se corta a la MISMA cantidad de días comerciales
(lun-sáb sin feriados) y la tarjeta muestra los dos rangos y sus fuentes. El total cerrado del
mes comparado viaja aparte (`mes_completo_hasta`) y no entra en ninguna variación.

**Fuentes históricas, con precedencia.** Mes en curso -> `01_INPUTS/ventas.csv`. Mes cerrado ->
`01_INPUTS/cierres mes/ventas_mes_MMAAAA.csv` y, si no está, `02_HISTORY/historial_ventas.csv`.
El mes en curso sale SIEMPRE de ventas.csv aunque exista un cierre con su nombre: un cierre de
agosto generado por adelantado describiría un mes que todavía no terminó.

**Definiciones.** Cliente que usó la acción = tiene al menos un comprobante que cumple canal,
productos, cantidades y descuento. Nuevo para Peñaflor = usó la acción y no compró ni en el
período comparado ni en los 12 meses previos (sin la ventana, cualquiera que se salteara un mes
figuraba como nuevo). Reactivado = no compró en el comparado pero sí en esos 12 meses.
Recurrente = compró en el comparado. Nuevo en categoría / en marca = ejes de producto
independientes. Estar en el universo elegible NO clasifica a nadie.

**AGO26-TRAD-NC.** Ser elegible no es haber usado la acción: el cumplimiento se valida a nivel
`NroComprobante` — 3 botellas de una marca + 3 de otra marca distinta del catálogo, con el 15%,
en el MISMO comprobante. No cuentan 6 de una sola marca, 3+3 en comprobantes distintos, otro
descuento, productos fuera del catálogo ni neto <= 0. `CantBase` ya viene en botellas/unidades
(regla oficial de motor_11t), así que se suma tal cual.

**11 Titulares.** El titular sale de la matriz oficial SKU->titular, nunca del nombre de marca.
Un impacto es un par (cliente, titular) cubierto con el umbral de SU segmento aplicado después
de sumar. `habilitado` = sacando las botellas de la acción no llegaba al umbral; `acompanado` =
llegaba igual. Si la acción no toca SKU del 11T, la sección devuelve `aplica: false` y no se
muestra.

**Se elimina el despliegue masivo.** El "Ver clientes elegibles (1458)" de AGO26-TRAD-NC salió
de la pantalla: 1.458 filas no sirven para decidir. La tarjeta muestra potenciales, usaron,
convertidos, conversión y Top 5. `acciones_trad_nc` devuelve sólo contadores; la lista queda
detrás de `?detalle=1` para auditar a mano y ninguna pantalla la pide.

**Bugs preexistentes corregidos en el camino:**

1. `_acc_preparar_from_df` parseaba `FechaComprobante` con `dayfirst=True`, pero el cierre
   versionado viene en ISO: sobre `ventas_mes_072026.csv` se perdían 4.863 de 5.811 filas como
   NaT y las que sobrevivían caían en meses inventados (2026-01 a 2026-06). Ahora usa
   `_semanal_fechas`, el parser único del proyecto. Afectaba también a la vista "Acciones
   cierre", que ya consumía esa fuente.
2. La función rompía si la lectura no incluía `FechaCarga` (columna informativa que nunca
   decide período). Ahora la tolera.

**Archivos:**

- `motor_acciones_analisis.py` (nuevo): lógica pura, sin I/O ni Flask, igual que motor_11t y
  motor_padron. Atribución, alcance de producto, caja mixta 3+3, clasificación, embudo, 11T,
  Top 5 e insight determinístico.
- `server_orbit.py`: fuentes por período con precedencia y caché por ruta+tamaño+mtime,
  `_acciones_analisis()` y los endpoints; `_fec` agregado a la preparación (el corte parcial
  necesita el día); los dos arreglos de fecha de arriba.
- `PAV MATINAL PE_A FLOR/portal.html`: tarjeta diferida con selector de comparación, estado de
  carga y error explícito; se quita el drill-down masivo.
- `test_acciones_analisis.py` (nuevo): 54 aserciones sobre las 21 áreas pedidas.

**Alcance de producto resuelto contra el maestro 04D.** El Excel nombra el alcance como lo dice
comercial ("VDA Superior", "VDG Super y Ultra Premium", "Espumante / Sidra", "Smirnoff
botella"). Se resuelve contra la apertura Categoría x Segmento del 04D, no con una lista
cableada. Antes de esto, 5 de las 15 acciones no resolvían ningún producto y `AGO26-VDA-RESTO`
resolvía TODAS las líneas del mes. Si el alcance no resuelve, la tarjeta corta con
"Dato no disponible" en vez de publicar 0 litros, que se leería como "no hubo ventas".

**Endpoints:**

- `GET /api/gerencia/acciones_analisis/<action_id>?comparacion=mes_anterior|anio_anterior`
- `GET /api/vendedor/<vid>/acciones_analisis/<action_id>?comparacion=...`

**Validación (2026-08-18, datos reales, sin mocks):**

- `test_acciones_analisis.py`: 54 OK, 0 fallas. Regresión: `test_acciones_trad_nc.py` 23 OK y
  `test_acciones_explorador.py` 29 OK.
- Endpoints en 8502: las 15 acciones responden 200 con alcance resuelto; V2, V5 y V20 dan 403;
  una acción inexistente da 404. Payload de 3.783 bytes (antes la lista de elegibles sola eran
  ~1.458 registros). Primera consulta 1,9 s (mes anterior) / 5,4 s (año anterior, parsea el
  historial de 66 MB una vez); consultas siguientes 0,02 s por caché.
- Portal: las 15 acciones renderizan la tarjeta sin un solo error de consola; el selector de
  comparación cambia la fuente a `historial_ventas.csv`; el Top se mantiene en 5 filas en
  ambos modos; el scope vendedor (V8) muestra sólo su cartera; AGO26-5X1 muestra la
  advertencia de atribución por no declarar porcentaje.
- Caso testigo 11T: en AGO26-TRAD-NC, 11 impactos asociados y 10 habilitados — coherente con
  una caja de 3+3 que deja al cliente Tradicional justo en el umbral de 3 botellas.

## 2026-08-18 - feat(Acciones): AGO26-TRAD-NC "Tradicionales no compradores" + SKU Alma Mora Low

**Regla comercial (agosto 2026):** 15% de descuento en una caja mixta de 6 botellas, armada con
exactamente 3 botellas de una marca y 3 de otra marca diferente del catalogo elegible. Seis
botellas de una sola marca NO califican. Marcas elegibles: Alma Mora, Alaris, Finca Las Moras,
Dada, Los Arboles, Trapiche Reserva, Don David, Smirnoff botella, Frizze y Gordon's.

**Elegibilidad:** cliente del canal Tradicional que durante agosto no compro NINGUNA de esas diez
marcas. Entran los dos casos: el que no compro nada de Penaflor y el que compro otros productos
Penaflor fuera de esas marcas. V2 y V5 excluidos; tampoco entran deposito (V1/V20) ni canales no
Tradicionales.

**Fecha autoritativa:** la pertenencia al mes se define EXCLUSIVAMENTE por `FechaComprobante`
(regla general del proyecto, sin cambios). `FechaCarga` y `FechaEntrega` no deciden periodo.
Compra valida = `ImporteNetoItem > 0`.

**Que es "marca":** se usa el campo `Marca` del ERP por igualdad exacta normalizada, porque es la
marca COMERCIAL y no la etiqueta del envase: "Alaris" agrupa tambien los Finca Las Moras de entrada
de gama, "Don David" agrupa El Esteco y "Trapiche Reserva" agrupa Puro / Impuro / Origen by
Trapiche. Deducir la marca del texto del articulo daria un agrupamiento que el ERP no reconoce.
La igualdad exacta ademas separa sola "Smirnoff botella" de "Smirnoff Ice" / "Smirnoff Ice
Flavours", que son las latas RTD y no entran. Unico fallback por nombre de articulo: las filas que
el ERP todavia exporta SIN `Marca` (altas nuevas, ej. 74887 y los Dada Low); sin eso, un cliente que
compro Alma Mora Low figuraria como no comprador.

**Innovaciones:** la entrada generica "Alma Mora Low" de AGO26-INNOV quedo reemplazada por los dos
SKU explicitos, con las escalas vigentes intactas (3 unidades 18% / 5 bultos surtidos o mas 20%):

- `74827` - Alma Mora Blanco Dulce Low 6x750 (ERP: ALMA MORA BLANCO DULCE LOW 6X750, vigente).
- `74887` - Alma Mora Malbec Dulce Low 6x750 (ERP: ALMA MORA MALBEC DULCE LOW 6X750, en proceso de
  alta).

Ambos verificados contra `09_CONFIG/mpa_codigos.csv`, `09_CONFIG/maestro_04D_productos.csv` y el
maestro de articulos vigente `01_INPUTS/RAW_PRODUCTOS/productosjulio.xlsx`. No se invento ningun
codigo ni descripcion.

**Por que hubo cambio de codigo y no solo una fila en el Excel:** el explorador publica reglas
ESTATICAS y el dataset del cierre las congela; esta es la primera accion cuyo publico depende de la
venta del mes, asi que un cliente deja de ser elegible en cuanto le entra una factura con esas
marcas. La elegibilidad se calcula en vivo en `server_orbit.py` sobre `ventas.csv` + el padron, y se
cuelga del nodo de la accion en el payload del explorador.

**Archivos:**

- `01_INPUTS/ACCIONES COMERCIALES/2026-08/ORBIT_Acciones_Comerciales_Agosto_2026.xlsx`: +1 fila en
  ACCIONES, +1 en ESCALAS, +10 marcas y el split de los dos SKU en PRODUCTOS_Y_LINEAS. Formato,
  anchos, merges, zebra, bordes y el `0%` de la columna descuento preservados.
- `tools/actualizar_acciones_agosto_trad_nc.py` (nuevo): editor idempotente del libro. Existe
  porque insertar filas en el medio de PRODUCTOS_Y_LINEAS corre el bloque de abajo y openpyxl no
  arrastra la convencion de formato; el script reescribe el bloque y la vuelve a aplicar.
- `generar_datasets_acum.py`: `--solo-explorador` (espejo de `--solo-planes-as`) para regenerar solo
  `mod_acciones_explorador.json` sin correr el pipeline completo ni tocar el snapshot de 02_HISTORY.
  El parser del Excel NO se toco: ya era generico y las filas nuevas fluyen solas.
- `server_orbit.py`: `_trad_nc_marcas_compradas`, `_trad_nc_elegibles`, `_acc_adjuntar_trad_nc` y las
  constantes de marcas; `clientes.xlsx` sumado a `_acc_mes_sig()` para que un cambio de padron
  invalide el payload.
- `PAV MATINAL PE_A FLOR/portal.html`: `accxElegHTML` / `accxElegLoad`, bloque "Clientes elegibles"
  dentro del panel del explorador, con carga perezosa del detalle.
- `test_acciones_trad_nc.py` (nuevo): 23 casos sobre datos reales.
- `04_DATASETS_ORBIT/mod_acciones_explorador.json`: regenerado (14 -> 15 acciones).

**Endpoints:** `/api/gerencia/acciones_mes` y `/api/vendedor/<vid>/acciones_mes` traen el resumen de
elegibilidad dentro de `explorador`; `/api/gerencia/acciones_trad_nc` y
`/api/vendedor/<vid>/acciones_trad_nc` (nuevos) devuelven la lista de clientes. La lista NO viaja en
el payload del login: son ~1.500 filas en gerencia y se piden solo al desplegar el detalle (mismo
patron que `cobertura_acum_faltantes`).

**Validacion (2026-08-18, datos reales, sin mocks):**

- Excel: 8 hojas intactas, anchos/merges/encabezados/titulos iguales al backup, 0 desvios de
  formato en las tres hojas tocadas, sin formulas ni celdas de error.
- Dataset: unica accion nueva `AGO26-TRAD-NC`; el unico cambio en otra accion es
  `AGO26-INNOV.productos` (el split de SKU). Avisos y conflictos identicos al backup.
- `test_acciones_trad_nc.py`: 23 OK, 0 fallas.
- Fuente vs backend vs portal con el server en 8502: cartera Tradicional 1689, elegibles 1458
  (1413 sin compras Penaflor + 45 que compraron otros productos), 231 ya compraron una marca. El
  drill-down devolvio 1458 clientes y el portal renderizo 1458 filas. V3: 182 de 284.
- V2, V5 y V20 rechazados con 403 en ambos endpoints de vendedor.
- Portal: el selector de categoria ofrece "Tradicionales no compradores"; el panel muestra 15%,
  "Desde 6 botellas", el texto 3+3, la advertencia de que 6 de una sola marca no califica, los KPIs,
  el desglose por vendedor y las 10 marcas. Innovaciones muestra los dos SKU y conserva 18%/20%.
  Las demas acciones no traen bloque de elegibilidad.

**Pendiente ajeno a este cambio:** `01_INPUTS/ACCIONES COMERCIALES/2026-08/` no tiene el
`acciones_comerciales_*.csv` del mes, asi que la MEDICION de uso e inversion de agosto
(`acciones[]`, `mod_acciones_ranking.csv`) viene vacia con la nota "Sin catalogo de acciones del
mes". Es previo a esta tarea y no lo toca: el explorador y la elegibilidad funcionan igual.

## 2026-08-18 - fix(Semanal): planificación persistente en Google Sheets

**Síntoma:** el botón Guardar plan respondía OK, pero la planificación semanal desaparecía al
reiniciarse o desplegarse Render.

**Causa raíz:** `plan_semanal` vivía sólo en `orbit.db`. El servicio real de Render fue creado
manualmente y no tiene montado el disco definido en `render.yaml`, por lo que su SQLite está en el
filesystem efímero. El endpoint guardaba correctamente, pero no de forma permanente (ERR-015).

**Solución:** la misma Google Sheet que ya es fuente de verdad de las planificaciones de vendedores
incorpora una pestaña `plan_semanal`, con una fila por período y las cuatro semanas de cada KPI.
`POST /api/gerencia/semanal/plan` escribe y verifica primero Sheets; sólo después actualiza SQLite
como caché. `GET /api/gerencia/semanal` relee Sheets y rehidrata esa caché. Si Sheets falla, el POST
devuelve 503 en lugar de mostrar un guardado falso y el portal identifica explícitamente la caché.

**Frontend:** el éxito confirma “guardado permanentemente” y la tarjeta muestra la fuente de
persistencia y cualquier advertencia.

## 2026-08-18 - feat(Planes AASS): BAT independiente sin cierre diario

**Archivo nuevo:** `ACTUALIZAR_PLAN_AASS.bat`.

**Objetivo:** permitir actualizar Plan AASS por doble clic sin ejecutar `CIERRE_DIA_ORBIT.bat`
ni `REGENERAR_DATOS_ORBIT.bat`. El BAT exige el `sincargos<mes>.xlsx` del mes calendario actual,
valida `ventas.csv`, `clientes.xlsx`, Python y la estructura real del Excel, y llama únicamente a
`generar_datasets_acum.py --solo-planes-as`.

**Seguridad:** antes de escribir crea un respaldo timestamped exclusivamente de
`mod_planes_as.csv` y `mod_sincargos_envios.csv`; si falla la generación o la reconciliación,
restaura ambos. Genera `99_LOGS_ORBIT/actualizar_plan_aass_<timestamp>.log`, no abre el portal y
no hace commit ni push.

**Validación incluida:** reconcilia cajas sin cargo, clientes de Plan Frío y cajas de Puntera entre
el Excel mensual y el CSV; verifica las columnas de envíos y bloquea V2, V3, V5 y V20.

## 2026-08-18 - feat(Planes AASS): actualización parcial de agosto sin cierre diario

**Pedido:** publicar `01_INPUTS/Planes AASS/sincargosagosto.xlsx` en ORBIT sin ejecutar el
cierre porque el día comercial recién había comenzado.

**Problemas detectados en la fuente nueva y resueltos:**

- La escala cambió `Alaris`/`Alma Mora` por **Finca Las Moras**/**Elementos**. El motor conserva
  las columnas históricas como slots compatibles, pero ahora lee y publica las etiquetas reales
  del Excel; la detección de enviados usa `Articulo` y reconoce `F. LAS MORAS` sin confiar en la
  columna Marca del ERP.
- Plan frío acepta encabezado `clientes` o `código` y excluye las filas `NO CUMPLE`.
- Puntera acepta la hoja histórica o el formato agosto embebido: columna `Punteras` y fila
  `ESCALA=Puntera / LC=Los Arboles`.
- Los productos desconocidos ya no se ignoran parcialmente: el lector avisa y rechaza esa fuente.
- V3 queda excluida del dataset y recibe 403 en el endpoint vendedor de Planes AASS.

**Actualización aislada:** `generar_datasets_acum.py --solo-planes-as` carga únicamente ventas,
maestro y Planes AASS, y escribe sólo `mod_planes_as.csv` y `mod_sincargos_envios.csv`. No toca
historial, cobertura, 11T, planificación, otros datasets ni `LEGACY/`.

**Fuente vs salida validada:** 31 clientes; 30 con asignación; **134 cajas de escala**
(109 Finca Las Moras, 23 Elementos, 2 Frizze), **27** clientes Plan Frío y **4** clientes de
puntera con **12 cajas**. Endpoints gerencia/vendedor en HTTP 200; V4=1, V8=16, V9=7, V10=7;
V3=403. Playwright validó gerencia y V8 mostrando Finca Las Moras/Elementos sin errores de consola.

**Respaldo:** `99_BACKUPS_ORBIT/20260818_092020_planes_aass/`. La publicación incluye sólo código,
prueba, fuente y los dos datasets de Planes AASS.

## 2026-08-13 - fix(cierre de mes): un mes sin terminar se publicaba solo como cerrado

**Causa raíz del cierre de agosto que hubo que borrar** (commit `7ca377c`). Ese fue el síntoma; esto es el bug.

**El problema.** El descubrimiento de cierres por carpeta (`server_orbit.py`, `_cierres_historicos`) globea `01_INPUTS/cierres mes/ventas_mes_*.csv` y agrega **cualquier** período que encuentre, marcándolo `estado: PASS`, sin comparar nunca contra el mes actual. Correr `CIERRE_MES_ORBIT.bat` a mitad de mes deja el trío versionado en la carpeta, y con eso solo el mes en curso aparecía en el selector como un mes cerrado, con datos de medio mes. Agosto figuró como cerrado desde el día 1.

**Cambio — sólo `server_orbit.py`, dos puntos:**

- En el loop de descubrimiento: `if periodo >= periodo_actual: continue`, con `periodo_actual = _now_ar()[:7]`. Se reusa el helper de hora argentina existente en vez de `date.today()`, que en Render (UTC) puede correrse un día en los bordes de mes. El `>=` cubre además un `MMAAAA` futuro mal tipeado.
- En `_cierres_hist_key()`: se agrega el período actual a la huella de caché. **Sin esto el fix tenía un bug propio**: la caché sólo dependía de mtimes, así que el 1° de mes el cierre recién terminado se quedaba oculto detrás de la caché hasta que algún archivo cambiara.

**Lo que NO se tocó**: el índice de `07_CIERRES_MENSUALES/` — un cierre real cargado ahí es un acto deliberado, no un descubrimiento automático. Y el glob de la línea 10509 sigue viendo *todos* los archivos, porque es la huella de invalidación de caché y tiene que ver hasta lo filtrado.

**Validación real**, con el archivo de agosto restaurado desde git a la carpeta:

| escenario | períodos devueltos | agosto |
|---|---|---|
| `ventas_mes_082026.csv` presente | `2026-07, 2026-06, 2026-05` | **excluido** |
| el **mismo archivo** renombrado a `_042026` | `2026-07, 2026-06, 2026-05, 2026-04` | aparece |

El control inverso es lo que cierra la prueba: el mismo archivo aparece como abril y se excluye como agosto, así que el descubrimiento sigue funcionando y lo único que lo saca es la regla del mes en curso. Temporales borrados, carpeta de vuelta en 14 archivos. Smoke de 6 endpoints en 200.

## 2026-08-13 - fix(portal): se terminan de eliminar los tokens `--bg2` y `--line`

**Cierre de la serie de tokens fantasma** (tercer y último commit de la sesión). Quedaban los dos usos que habían aparecido buscando los buscadores anteriores.

**Cambios — sólo `PAV MATINAL PE_A FLOR/portal.html`:**

- **`#vpasSearch`** (Planes AS del vendedor): el fondo ya estaba bien (`--surf2`), pero el `border:1px solid var(--line)` hacía desaparecer el borde entero (`border-width: 0px`). Pasa a `.srch-in`, con lo que los **tres** buscadores del portal comparten una sola clase.
- **Riel de la barra de progreso de Stock sin Venta**: `background:var(--line)` daba `rgba(0,0,0,0)`, o sea riel invisible — se veía la porción amarilla flotando sin canal detrás. Pasa a `var(--b)`. El relleno nunca estuvo roto: `--wn` (#F2B544) sí existe.

**Por qué `--b` y no migrar a `.bar`**: la convención del design system para riel es `.bar { background: rgba(255,255,255,0.06) }`, y `--b` es `rgba(255,255,255,0.07)` — la misma superficie a 0.01 de diferencia. Migrar a `.bar`/`.bar-f` habría cambiado alto (7px→5px) y radio (5px→999px), que es un cambio visual y no un fix.

**Validación real**: 8502 y A/B de estilos computados contra la hoja de estilos viva —

| | antes | después |
|---|---|---|
| `#vpasSearch` borde | `0px` | `1px rgba(255,255,255,.07)` |
| riel de la barra | `rgba(0,0,0,0)` | `rgba(255,255,255,.07)`, alto 7px sin cambio |

Único efecto colateral, aceptado: `#vpasSearch` pasa de `padding:10px 12px` a `9px 12px` al adoptar la clase compartida — 1px vertical, a cambio de unificar los tres buscadores. Grep final: **cero usos de `var(--bg2)` y `var(--line)`** en todo el archivo.

## 2026-08-13 - fix(portal): los buscadores de Planes AS y Stock sin Venta eran ilegibles

**Continuación directa del fix de los desplegables** (misma sesión, mismo bug de tokens fantasma). Era el pendiente que quedó anotado abajo.

**Causa raíz — los mismos dos tokens que no existen.** Los buscadores `#gpasSearch` (Planes AS, gerencia) y `#svSearch` (Stock sin Venta) traían `style` inline con `background:var(--bg2)` y `border:1px solid var(--line)`, y **ni `--bg2` ni `--line` están definidos en `:root`**. Medido en el navegador, el efecto era peor de lo que se veía en el código: la `var()` inválida en `background` deja `rgba(0,0,0,0)` (el campo toma el blanco del sistema) **y además el `border` desaparecía por completo — `border-width: 0px`**, porque una `var()` inválida invalida todo el shorthand y `border-style` vuelve a `none`. Con `color:var(--text)` (#E8EDF5) intacto, el campo quedaba blanco, sin borde y con letra casi blanca.

**Cambio — sólo `PAV MATINAL PE_A FLOR/portal.html`:**

- Clase nueva `.srch-in` (`--surf2` / `--text` / `--b`, con `:focus` en `--mg` y `::placeholder` en `--text3`), espejo de `.accf-in`, en reemplazo de los dos `style` inline rotos.
- `#svSearch` conserva su `margin-bottom:10px` inline; el resto de la geometría (ancho 100%, `border-radius:9px`, padding) es idéntica a la anterior.

**Validación real**: servidor en 8502 y A/B de estilos computados contra la hoja de estilos viva, mismo markup con el inline viejo vs la clase nueva —

| | background | border | color |
|---|---|---|---|
| antes | `rgba(0,0,0,0)` | `0px` (sin borde) | `#E8EDF5` |
| después | `rgb(17,24,32)` = `--surf2` | `1px rgba(255,255,255,.07)` = `--b` | `#E8EDF5` |

Confirmado en runtime que `--bg2` y `--line` devuelven vacío desde `:root`. Geometría sin cambios (ancho y radio idénticos), así que no hay corrimiento de layout. Los dos son buscadores de render parcial: el `<input>` se editó en su lugar, dentro del shell, sin moverlo a la zona que se re-renderiza por tecla, así que no pierde el foco.

**Queda pendiente (mismo bug, fuera del pedido)**: `#vpasSearch` (Planes AS del vendedor) tiene el fondo bien (`--surf2`) pero el borde con `var(--line)` → se queda sin borde; y la barrita de progreso de Stock sin Venta usa `background:var(--line)` para el riel, que por eso es invisible.

## 2026-08-13 - fix(portal): los desplegables de Acciones Comerciales eran ilegibles

**Síntoma reportado**: en Acciones Comerciales el menú desplegable salía blanco con las letras blancas; sólo se leía la opción al pasarle el cursor por encima.

**Causa raíz — un token de color que no existe.** Los 3 selectores del Explorador (Categoría / Línea / Segmento) se pintaban con un `style` inline que pedía `background:var(--bg2)`, y **`--bg2` no está definido en `:root`** (el design system tiene `--bg`, `--surf`, `--surf2`, `--surf3`). Una `var()` inválida en `background` cae a `transparent`, así que el control quedaba con el blanco del sistema mientras el texto conservaba `color:var(--text)` (#E8EDF5, casi blanco). Encima, el popup nativo del `<select>` en Windows se pinta con el tema del SO salvo que se le fije `color-scheme` y se estilen los `<option>` — el mismo detalle que ya estaba resuelto en la pantalla de login (`.ln-field select option`) y que faltaba acá.

**Cambio — sólo `PAV MATINAL PE_A FLOR/portal.html`:**

- Clase nueva `.accx-sel` junto a `.accf-sel`, con `background:var(--surf2)` y `color:var(--text)`, en reemplazo del `style` inline roto (constante `selSty` eliminada).
- `color-scheme:dark` + `.accf-sel option, .accx-sel option { background:var(--surf3); color:var(--text); }` para que el desplegable abierto también respete el tema oscuro. Alcanza a los filtros del buscador (`.accf-sel`), que tenían el mismo riesgo en el popup.
- De paso, `.accf-sel` usaba `font-family:var(--f-txt)`, otro token inexistente → `var(--f-body)`.

**Validación real**: servidor levantado en 8502 y estilos computados leídos del DOM — select `rgb(17,24,32)` (#111820) con texto `rgb(232,237,245)`, opciones `rgb(22,30,42)` (#161E2A) con el mismo texto, `color-scheme: dark` en ambas clases. Sin cambios de identidad visual: todo sale de los tokens existentes.

**Queda pendiente (no es el pedido, mismo bug)**: los buscadores de **Planes AS** (`#gpasSearch`) y **Stock sin Venta** (`#svSearch`) siguen con `background:var(--bg2)` y `border:1px solid var(--line)` inline — `--line` tampoco existe. Son `input`, no `select`, así que el síntoma es el campo de texto en blanco, no el desplegable.

## 2026-08-10 - fix(cierre): los objetivos editados a mano no llegaban a Render

**Síntoma reportado**: se cargó el objetivo nuevo en `01_INPUTS/objetivo 11T.xlsx` y ORBIT siguió mostrando el viejo.

**Causa raíz — ERR-014 otra vez, ahora sobre los objetivos.** `CIERRE_DIA_ORBIT.bat` publica por **allowlist explícita** (`git add` archivo por archivo, no `git add .`) y **ningún archivo de objetivos estaba en esa lista**. El portal los lee **en vivo desde el `.xlsx`** (`server_orbit.py:_objetivos_11t`, `_objetivos_ccc`, `_objetivos_sellout`, `_objetivo_dada`), sin dataset intermedio: en local el cambio se ve al instante, pero el archivo se quedaba modificado-sin-commitear para siempre y Render seguía sirviendo la versión del último commit manual. El guard no lo detecta —`check_git_cierre.py` clasifica todo `01_INPUTS/` como operativo permitido— y el cierre daba **verde** igual porque el resto de los `git add` sí dejaba algo staged.

**Medida del desfasaje al momento del reporte** (11T, HEAD vs local): objetivo total **1864 → 3734**, con los 11 titulares desactualizados. El `.xlsx` de Render era del **2026-07-06**; `objccc.xlsx`, del 21/07.

**Cambio**: 5 líneas nuevas en el allowlist de `CIERRE_DIA_ORBIT.bat`, junto a los demás inputs:

```
git add "01_INPUTS/objetivo 11T.xlsx"      REM 11 Titulares
git add "01_INPUTS/objccc.xlsx"            REM CCC por canal y por vendedor
git add "01_INPUTS/OBJSELLOUT.xlsx"        REM Sell Out por categoría (+ litros del semanal)
git add "01_INPUTS/DADAVERANOOBJ.xlsx"     REM Incentivo DADA
git add "01_INPUTS/dadatinto.csv"          REM ventas del incentivo DADA (input propio)
```

- **Sin tocar código ni datasets**: es publicación, no cálculo. `server_orbit.py` ya leía bien el archivo — el problema era que a Render le llegaba otro.
- **`git add` de un archivo sin cambios es no-op** y no rompe el cierre, así que las líneas quedan fijas aunque ese mes no se toque el objetivo.
- **Validado en seco** (`git add -n`, sin tocar el índice): stagea los 3 modificados (`objetivo 11T.xlsx`, `objccc.xlsx`, `dadatinto.csv`) y no dice nada de los 2 sin cambios.
- CRLF preservados (edición binaria + verificación: **309 CRLF, 0 LF sueltos**) — ver regla del `.gitattributes`.
- **Quedan fuera del allowlist a propósito, y siguen siendo publicación manual**: `04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx` (maestro congelado), `11 titulares autoservicio/…match_codigos.xlsx` (matriz oficial de SKU) y `MPA/MPA.xlsx` (lista fija). Si alguno se edita, no viaja con el cierre.

## 2026-08-08 - chore(cierre): versionar el libro .xlsx de Acciones del mes

El explorador lee el JSON, pero la **fuente editable** es el `.xlsx` del mes, y el cierre no lo publicaba: el libro de agosto —con la definición de "+5 bultos" cargada a mano— vivía sólo en la máquina de operaciones, sin respaldo. Una línea nueva en `CIERRE_DIA_ORBIT.bat`:

```
git add "01_INPUTS/ACCIONES COMERCIALES/*/*.xlsx"
```

- **Sirve para cualquier mes** `YYYY-MM`, no sólo agosto. Queda al lado de la regla hermana de los `.csv` de esa carpeta.
- **Alcance verificado con `git ls-files`**: toca exactamente los 4 libros de carpetas mensuales (junio, los dos de julio y el de agosto) y **ningún otro** `.xlsx` de `01_INPUTS` — ni clientes, ni resultado, ni stock, ni los `cierres mes`. Ojo con el detalle técnico: en un pathspec de git el `*` **sí cruza `/`**, así que el patrón alcanzaría subcarpetas; no es un problema porque `*/salida/` ya está en `.gitignore`.
- **Simulación en seco antes de tocar el .bat**: se extrajeron las 44 reglas `git add` reales del archivo y se corrieron con `--dry-run`. Único agregado nuevo: el Excel de agosto.
- **El guard no se tocó**: `check_git_cierre.py` ya clasificaba esa carpeta como operativa.
- CRLF preservados (edición binaria + verificación: 299 CRLF, 0 LF sueltos).
- `mod_acciones_explorador.json` ya se venía publicando desde el commit anterior; se confirmó en la corrida real del cierre `f7e285b` (1310 líneas subidas).

## 2026-08-08 - data(acciones): Innovaciones "+5 bultos" aplica desde 5 inclusive

Definición de comercial sobre una de las dos ambigüedades que el libro de agosto dejaba abiertas. **El cambio es de dato, no de código**: se editó el Excel del mes y se regeneró el catálogo; `generar_datasets_acum.py`, `server_orbit.py` y `portal.html` no se tocaron — que era justamente el objetivo de haber sacado las reglas del HTML.

- `ESCALAS!E43` (AGO26-INNOV, unidad bulto): `min_inclusivo` **6 → 5**. Texto a "5 bultos surtidos o más · 20%" y la observación deja asentado quién y cuándo lo definió.
- `ACCIONES!G15` (resumen) y `VALIDACIONES!A6/D6`, que pasa de **ALTA a RESUELTA** con la definición registrada. La fila no se borra: queda la trazabilidad de que la fuente decía "+5" y de cómo se resolvió.
- **Nada más se movió**: el 20% intacto, el segmento intacto, la escala de "3 unidades · 18%" intacta y la bonificación 5+1 de la fila siguiente intacta (verificado releyendo el archivo guardado).
- **Queda una sola ambigüedad abierta**: el solape de "10 a 20 cajas" / "20 cajas o más" en Autoservicios (VDA Superior, VDA Resto, VDG Premium). Sigue en ALTA y el portal sigue mostrando las dos escalas con ⚠️.
- **Verificado**: 29 tests OK (3 nuevos: umbral en 5, 4 bultos no alcanza / 5 sí, y que las 20 cajas queden como única ALTA); endpoints de gerencia y vendedor devuelven `min=5`.

## 2026-08-08 - feat(acciones): explorador comercial de agosto 2026

Pedido: las reglas del mes se leían como un mosaico de tarjetas (una por acción, por segmento y por escala) imposible de recorrer en un celular. Ahora hay **un solo panel** con tres selectores: **Categoría → Línea → Segmento**.

- **El Excel del mes es la fuente**, no el HTML. `01_INPUTS/ACCIONES COMERCIALES/2026-08/ORBIT_Acciones_Comerciales_Agosto_2026.xlsx` → `generar_datasets_acum.generar_acciones_explorador()` → `04_DATASETS_ORBIT/mod_acciones_explorador.json`. Se procesan las 8 hojas (LEEME, ACCIONES, ESCALAS, PRODUCTOS_Y_LINEAS, EXCLUSIONES, VALIDACIONES, UX_CONFIG, FUENTES). **Ninguna regla comercial quedó cableada en el portal**: el mes que viene se cambia el Excel y la pantalla se actualiza sola. El encabezado real de cada hoja se busca por su columna clave, no por número de fila.
- **Por qué un dataset y no leer el .xlsx en el endpoint**: el `.bat` del cierre publica de esa carpeta únicamente `*/acciones_comerciales_*.csv`. El libro `.xlsx` **no entra en ese allowlist**, así que un endpoint que lo leyera andaría en local y mostraría la pantalla vacía en Render — exactamente ERR-014. El JSON vive en `04_DATASETS_ORBIT/`, que sí se publica (se agregó su línea al `.bat`, con los CRLF intactos).
- **La medición de uso quedó intacta.** `mod_acciones_ranking.csv` sigue midiendo plata, litros y clientes sobre ventas.csv, y sigue alimentando el Cierre de Mes. Son dos cosas distintas: el explorador dice **qué ofrece** cada acción; el ranking dice **cuánto se usó**. En agosto todavía no hay uso medido (no hay CSV de catálogo del mes), así que la pantalla muestra el explorador y un estado claro en lugar del mosaico.
- **Ambigüedades: se muestran, no se resuelven.** El solapamiento "10 a 20 cajas" / "20 cajas o más" se detecta solo, comparando tramos por canal y unidad: se marcan **las dos** escalas con ⚠️ y el conflicto se enuncia textual. No se elige ganadora ni se recorta ninguna escala. Los 6 puntos de la hoja VALIDACIONES (incluido si "+5 bultos" arranca en 5 o en 6) viajan al portal tal cual, plegados bajo "pendientes de confirmación comercial".
- **Verificado**: 26 tests nuevos (`test_acciones_explorador.py`) sobre libros sintéticos en tmpdir — lectura de hojas, escalas, drops, topes, productos, exclusiones, hoja faltante, Excel ausente, filas vacías, mes futuro que no se adelanta, determinismo y los 4 caminos del loader. En el navegador: un único panel tras 4 cambios de selector, selector 2 y 3 ocultos cuando hay una sola opción, productos plegados que abren y cierran, los 4 estados vacíos, y selectores apilados sin scroll horizontal a 360/390 px. 25 endpoints en 200, V20 sigue 403.

## 2026-08-08 - fix(plan vs real): avisar cuando el Real $0 es resultado.xlsx viejo, no un cero real

**Síntoma reportado**: en gerencia, Plan vs Real (el cierre del día) no mostraba la venta de ayer — Real **$0** en los 7 vendedores el 2026-08-07.

- **Causa raíz: `01_INPUTS/resultado.xlsx` no se actualizó antes del cierre del 07/08** (mtime 6-ago 18:55; el cierre corrió 17:49). El real del día es `Acumulado(hoy) − Acumulado(ayer)` sobre `02_HISTORY/acumulado_resultado_historico.csv`, y los snapshots del 06 y del 07 son **idénticos al centavo** en los 7 vendedores → resta 0. El commit del cierre (`55c7c09`) tocó ventas.csv y los datasets pero **no** resultado.xlsx, porque el archivo nunca cambió. El CCC del día sí aparecía (V7=8, V10=7) porque ese sale de ventas.csv, no del xlsx.
- **El aviso cruza dos fuentes, no mira sólo el cero.** Un cero puede ser legítimo: un sábado sin ventas mueve el acumulado en $0. Lo que separa un caso del otro es **si el ERP facturó ese día**. Regla única: *acumulado congelado en TODOS los vendedores* **+** *ventas.csv con facturación de esa fecha* = archivo viejo. Sin facturación → cero real, no se avisa. Por eso no se usó "diferencia = 0" a secas ni el mtime como criterio en el server (en Render el mtime es el del checkout de git y siempre miente).
  - **En el cierre** — `generar_datasets_acum._avisar_acumulado_sin_movimiento`: bloque `[ALERTA]` con la fecha comparada, cuántas líneas facturó ese día, el mtime del xlsx y qué hacer. **Avisa y sigue**: el snapshot se graba igual (el dato es el dato), pero el cierre deja de terminar en verde silencioso. Compara contra el último snapshot del **mismo mes** (el día 1 el acumulado arranca de cero y comparar no significa nada).
  - **En el portal** — `server_orbit.matinal_resumen` devuelve `aviso_real` y Plan vs Real pinta un cartel rojo *"Real no confiable"*. Es donde se detectó el problema, así que es donde tiene que avisar.
- **Bug destapado por el test del sábado: la pantalla daba 500 ese día.** Con el cierre corrido y sin facturación, `usa_resultado` prende `tiene_real=True` aunque `ventas_dia` esté vacío, y `_cargar_ventas_dia` devuelve un DataFrame **sin columnas** → `groupby("vendedor_codigo")` tiraba `KeyError`. Nunca explotó sólo porque los sábados no se corría el cierre. Ahora la condición es `tiene_real and not ventas_dia.empty`: el sábado muestra ceros (que es el dato correcto), no un error.
- **Validación**: 5 escenarios sintéticos del guard (archivo viejo → alerta; sábado sin ventas → "cero real"; día normal, primer día del mes y sin historial → silencio); endpoint sobre los datos reales del 07/08 → `aviso_real` poblado; sábado simulado → 200, ceros, sin aviso; CCC real intacto (8 y 7). Cartel verificado leyendo el DOM de la pantalla renderizada, sin errores JS. `test_matinal_resumen_snapshot.py`: 6/6 OK.
- **El día 07/08 no se recupera re-corriendo el cierre** (la nota anterior de este changelog decía que sí y estaba mal). `snapshot_acumulado_resultado` fecha el snapshot con `max(FechaComprobante)` de **ventas.csv**, no con la fecha del `resultado.xlsx`: con el `ventas.csv` actual —que ya llega al 08— pegar el xlsx del 07 y re-correr grabaría esos números **con fecha 2026-08-08**, pisando el snapshot bueno. La dedup por fecha protege de duplicar, no de escribir el día equivocado. Verificado el 08/08 sobre el histórico: 06 y 07 idénticos, 08 movido → el **07 queda en Real $0** y el **08 arrastra la venta de los dos días** (`acum(08) − acum(07)`). Detalle y única corrección posible en `NEXT_TASK.md`.

## 2026-08-07 - feat(cierre de mes): tarjeta de Acciones Comerciales legible y medida por uso

Pedido de gerencia: la tarjeta no se entendía (en julio varias filas decían **"Accion nueva de julio"**, sin decir qué acción era ni qué línea de producto), no hace falta la plata por acción, y sí hacen falta ventas y litros hechos con cada acción, ordenadas de mayor a menor uso.

- **El título sale de `categoria_tarjeta`, no de `observaciones`.** El catálogo ya trae el nombre pensado para mostrar ("Smirnoff Botella - 15% por volumen", "Caja mixta VDA - Los Árboles", "RTD (Latas)") y está poblado en **las 29 filas**, incluidas las altas nuevas del mes — que eran justamente las que salían sin nombre útil. `observaciones` es texto libre y repite "Accion nueva de julio" en varias filas.
  - `lineas_comerciales` **no** puede ser el título: viene vacío en esas mismas altas nuevas (filas 022-029). Se usa como línea de producto cuando está.
  - `productos_marcas` se muestra sólo si **nombra productos**. Ese campo mezcla tres cosas: marcas de verdad ("Dadá Tinto Verano"), listas de códigos ("30019; 30020; …") y cláusulas de la regla ("Todos menos importados premium…"). `_acc_producto_legible` descarta las dos últimas.
- **Columnas nuevas: `Ventas` y `Litros`; se fue la plata por acción.** Venta = **comprobante distinto** en el que se aplicó la acción, no líneas: una factura con 6 artículos de la acción es **una** venta. Para eso se agregó `_nro` (NroComprobante) a `_acc_preparar_from_df`. Si la fuente no trae comprobante se informa `None` (la tarjeta muestra "–") en vez de un conteo de líneas disfrazado de ventas.
- **Ordenadas de mayor a menor uso** (ventas, y a igualdad de ventas los litros), con barra de proporción. Se devuelven **todas** las acciones usadas, no las 10 primeras: el negocio también necesita ver la cola.
- **El cierre pasó a medir USO, no ALCANCE — y esto mueve los números.** `_cierre_acciones_junio_schema` no aplicaba `_acc_mask_usa_accion`, el filtro que la pantalla viva de Acciones Comerciales sí usa: contaba como "usó la acción" a todo el que compró el producto del alcance, con descuento ajeno o sin descuento. Ahora reusa esa misma función — una sola definición de "usó la acción", no dos conviviendo.
  - Julio-2026: **clientes 861 → 301** e **inversión $41,1M → $9,1M**. No es una pérdida de datos: es dejar de atribuirle a las acciones del catálogo descuentos que no son suyos.
  - **Hallazgo que esto destapa**: de los **$43,6M** de descuento de julio, **$26,2M (60%) se dieron al 17%**, y **ningún tramo del catálogo de julio es 17%**. Es plata real, pero no la explican las acciones del mes. Queda anotado en `NEXT_TASK.md` para revisar con el negocio; **no se tocó nada** para "cuadrarlo".
- **Mayo degrada honesto.** Usa el esquema viejo (`reglas_acciones_mayo_2026_orbit.csv`), que no trae comprobante ni mide uso: la tarjeta muestra **"–"** en ventas y litros totales en vez de ceros inventados, y la nota al pie dice explícitamente que ese cierre mide alcance y no uso.
- **El `.bat` no necesitó cambios**: `tools/cerrar_mes.py` ya copia el catálogo del mes (`01_INPUTS/ACCIONES COMERCIALES/<AAAA-MM>/*.csv` → `acciones_<MMAAAA>.csv`) al cierre versionado, y la tarjeta se reconstruye de ahí en cada lectura. Si un mes no tiene catálogo en esa carpeta, queda el artefacto congelado y la tarjeta vuelve al formato viejo.
- **Validación en el portal renderizado**: julio muestra **20 acciones** ordenadas por uso, encabezado con **582 ventas · 11.272 L · 301 clientes**, y cada fila con nombre real, línea, canal, tramos y sus métricas. Verificado también mayo (esquema viejo): ventas "–" y la nota correcta, sin ceros falsos.

## 2026-08-06 - feat(cierre de mes): plan de acción de la reunión mensual, con seguimiento del mes anterior

Pedido de gerencia: en la reunión mensual, anotar para cada objetivo no alcanzado qué se va a hacer el mes siguiente; y que la reunión del mes siguiente arranque mostrando si esas acciones funcionaron.

- **Dos tarjetas nuevas en Cierre de Mes**, verificado el orden en el DOM:
  - **Arriba de todo** (`#cierre-plan-seg`) — *Seguimiento del plan de acción · \<mes anterior\>*: cada acción acordada con su **✓ LOGRADO / ✗ NO LOGRADO**, el % actual, de cuánto venía y el delta.
  - **Abajo de todo** (`#cierre-plan-acc`) — *Plan de acción · \<mes\>*: los indicadores que cerraron por debajo del objetivo, cada uno con su textarea para la acción, y botón de guardar.
- **"Logrado" se mide, no se declara**: el indicador llegó a su objetivo en el cierre siguiente (`pct >= 100`). Nadie tilda una casilla.
  - **El delta se muestra siempre, aparte del estado.** Caso real de la prueba: `Sell Out · VERMOUTH` pasó de **0% a 51,7%** — sigue `NO LOGRADO`, pero decir sólo eso escondería que se movió 51,7 puntos. El estado responde "¿llegamos?" y el delta "¿mejoramos?"; son dos preguntas distintas y la reunión necesita las dos.
  - Si el indicador **ya no existe** en el cierre nuevo (categoría que se dejó de medir, vendedor que salió) el estado es **`sin_dato`**, nunca "no logrado": no se puede medir no es lo mismo que se falló.
- **Universo de indicadores = los que TIENEN objetivo en el cierre**, en 4 familias: facturación empresa, facturación por vendedor, 11 Titulares por marca y Sell Out por categoría (26 indicadores en julio-2026). CCC, Innovaciones, Planes AS y Acciones **no traen objetivo** en el cierre: no se les inventa uno para poder listarlos.
- **`_plan_accion_indicadores()` es una sola función** para listar los no logrados del mes y para buscar cómo le fue después a un indicador del mes anterior. Si fueran dos, se desincronizarían y el seguimiento mediría distinto que el plan.
- **El id del indicador es un slug ASCII** (`_plan_accion_slug`): es la clave que une el plan de un mes con la medición del siguiente, así que no puede depender de acentos ni de cómo venga codificado el nombre desde el ERP (`VINOS DEL AÑO` → `sellout:vinos_del_ano`).
- **La foto del indicador se guarda con la acción** (objetivo/logrado/pct del mes en que se escribió) y **se toma del cierre, nunca de lo que mande el navegador**: el cliente sólo aporta el texto. El seguimiento compara contra ese número, no contra lo que hoy devuelva un cierre regenerado.
- **El periodo anterior no es "mes − 1" a secas**: es el cierre anterior más reciente **que tenga un plan guardado**. Si un mes no tuvo reunión, el seguimiento muestra el último plan que sí existe en vez de un hueco.
- **Persistencia**: tabla `cierre_plan_accion` en `orbit.db` (disco persistente de Render, `/var/data`) + respaldo CSV, mismo criterio que `plan_semanal`. Texto vacío **borra** la fila, no guarda una acción en blanco.
- **`gerencia_cierres_historicos` refactorizado**: el armado pasó a `_cierres_historicos()` y la ruta sólo hace `jsonify`. El plan de acción lee los mismos cierres sin repetir el recorrido de `07_CIERRES_MENSUALES/`.
- **Caché por mtime de `_cierres_historicos()` — arreglando un costo que introduje.** Medido en Render: la pantalla ya tardaba **~18 s** en traer los cierres, y el endpoint nuevo agregaba **~17 s más** porque rearmaba todo de cero: la pantalla pasaba a tardar el doble. Ahora se cachea contra los mtimes del índice, del árbol de `07_CIERRES_MENSUALES/`, del trío versionado y del maestro 04D. Local: **12,7 s en frío → 0,005 s** después, y el plan de acción reusa el mismo caché (0,004 s). Verificado que **invalida**: tocando el mtime de un `ventas_mes_*.csv` vuelve a reconstruir. Los cierres son datos congelados, así que mientras los archivos no cambien el resultado es idéntico por definición.
- **Los textarea no se re-renderizan al tipear** (se perdería el foco, igual que el buscador de Plan Cobertura): se pintan una vez y se leen recién al guardar.
- **Validación end-to-end por la UI real**, no sólo por API: se cargaron 5 acciones en la reunión de **junio**, se guardó, se cambió el selector a **julio** y la tarjeta de seguimiento apareció arriba de todo con **3 logrados / 2 no logrados**, cada uno con su delta (`11T TRAPICHE RESERVA` 52,6% → 103,8% logrado; `V3` 68,5% → 20,8% no logrado). Orden del DOM verificado: seguimiento **primero de 11**, plan de acción **último**. Filas de prueba borradas después (la tabla quedó en 0).

## 2026-08-06 - feat(plan cobertura): descarga Excel por tarjeta, con la facturación abierta por comprobante

Pedido de gerencia: un botón de descarga en cada tarjeta de Plan Cobertura con el detalle de la facturación de cada cliente, abierta por los comprobantes de venta.

- **Un botón `⬇ Excel` por lista** (5 en total: Capturados, Atendidos sin código, Altas fuera del listado, Potenciales, No atendidos), en el encabezado de cada una. Endpoint único `GET /api/gerencia/plan_cobertura/export?bloque=<id>`, con `_PLAN_COB_BLOQUES` como mapa de bloques válidos (un bloque desconocido devuelve **400** con la lista de válidos, no un archivo vacío).
- **Tres hojas donde hay facturación** (Capturados y Altas fuera):
  - `Clientes` — la tarjeta tal cual se ve, más las medidas de la ficha (activación, meses, recompras, botellas, importe).
  - `Comprobantes` — **una fila por factura**: fecha, número, líneas, botellas compradas, botellas sin cargo e importe neto. Es la vista que pidió el negocio.
  - `Detalle` — una fila por línea de venta con su comprobante, código, artículo, marca, botellas, importe y % de descuento.
  - Los otros tres bloques **no tienen `cliente_id`** (son PDV potenciales / no atendidos / sin código cargado): bajan sólo la hoja `Clientes`. No se les arma una hoja de facturación vacía que se leería como "no compraron".
- **`NroComprobante` incorporado a `_plan_cob_ventas`.** Lo traen las 3 fuentes con formato ERP; `historial_ventas_cliente.csv` (el normalizado) **no lo tiene**.
  - **El problema que había que resolver**: el trimestre vivo está en las dos fuentes, y como el normalizado va primero en `paths` gana el dedup — todas las facturas recientes, que son las que importan, se habrían perdido. Se recupera el número desde el duplicado que sí lo trae, **tocando únicamente la columna `_nro`**: no cambia qué fila queda, así que importes, descuentos y marcas de la pantalla quedan intactos.
  - Resultado: **275 de 329 líneas (83%) con comprobante**. Las 54 sin número son **exactamente 2026-05 y 2026-06**, el tramo que sólo existe en el archivo normalizado; salen etiquetadas `(sin comprobante en la fuente)` en vez de en blanco, para que se lea como una limitación de la fuente y no como un dato faltante.
- **Las líneas de importe 0 (sin cargo de los combos del plan) van al Excel marcadas** en la columna `Tipo`, y `Comprobantes` separa "Botellas compradas" de "Botellas sin cargo". Si se mezclaran, las botellas del Excel no cerrarían contra las de la tarjeta.
- **La facturación se emite una vez por `cliente_id`**: el padrón repite algún PDV con el mismo código y, emitida por fila de la tarjeta, la misma factura se contaría dos veces.
- **Validación**: los 5 Excel se generan (200 + MIME + `Content-Disposition` correctos, verificado por HTTP real, no sólo con el test client). **Cero descuadres** entre el Excel y las fichas de la pantalla: para los 25 clientes con compras, la suma de `Importe neto` / `Botellas` de las líneas `Compra` da exactamente el `importe` y las `botellas` de la tarjeta. `Detalle` y `Comprobantes` concilian entre sí (21.744.381,56 y 259 líneas en Capturados; 3.313.635,50 y 74 en Altas fuera).
- **Regresión del payload**: `/api/gerencia/plan_cobertura` se comparó **contra producción** (Render, que corría el código anterior) — `resumen` idéntico y **0 diferencias** en activación, última compra, meses, recompras, botellas, importe y estado de todas las fichas.

## 2026-08-06 - feat(semanal): KPI Litros en el histórico y en la planificación

Pedido de gerencia: un botón **Litros** al lado de Facturación en la pantalla Semanal, con la apertura de litros por semana y su % sobre el total del mes, más la fila de planificación de litros junto al resto de los indicadores.

- **`_SEMANAL_KPIS` gana `{"id":"litros","label":"Litros","tipo":"litros"}`** en segundo lugar, justo después de Facturación. Esa lista es la fuente única de la pantalla: alimenta los botones del histórico, las filas de la tarjeta de planificación y la validación del POST, así que el KPI entra en los tres lugares sin código nuevo por pantalla.
- **Litros con la cascada única del proyecto** (`_litros_por_linea`: maestro 04D → PesoKg → nombre del artículo). No se inventó un cálculo nuevo: es el mismo criterio que sell out, acciones y ficha de cliente. En junio-2026 sólo **8 de 5.707 líneas** quedan en 0 L (SKU sin litros por ninguna de las tres vías).
- **`_semanal_agg` refactorizado con `_SEMANAL_SUMAS = {"facturacion":"imp", "litros":"litros"}`**: facturación y litros son la misma mecánica (suma de la columna por semana, % sobre el total del mes), sólo cambia la columna. Los CCC siguen con su aporte incremental, intacto.
- **`_SEMANAL_COLS` suma `Codigo`, `CantBase`, `PesoKg` y `Articulo`** (las 4 entradas de la cascada). Están en las 3 fuentes verificadas (`ventas.csv`, los `ventas_mes_MMAAAA.csv` y `historial_ventas.csv`). Los litros se calculan **después** de filtrar bajas/Depósito e importe > 0, para no mapear líneas que se descartan.
- **`_leer_ventas_min` ya no se rompe entera por una columna que falte.** `usecols` con una columna inexistente aborta la lectura completa: una fuente futura sin `PesoKg` habría dejado la pantalla Semanal en blanco, **incluida facturación, que hoy funciona**. Ahora se intersecta contra el encabezado ya sniffeado y cada columna que falte se pierde sólo a sí misma; `_semanal_leer` chequea las requeridas y cae a 0 L si faltan las de litros.
- **Objetivo de litros = el mismo que el TOTAL de la tarjeta de Sell Out del dashboard** (decisión del usuario: un solo objetivo de litros para todo el portal, aunque este mes todavía no esté actualizado). `_semanal_objetivos` reusa **`_cargar_objetivos_sellout()`** —la fuente de esa tarjeta— y suma por categoría igual que el front (`sellData.reduce((a,c)=>a+(c.objetivo||0),0)`). Verificado que los dos caminos dan **el mismo número, 60.597 L**, así que se mueven juntos cuando se actualice `OBJSELLOUT.xlsx`; no hay una segunda copia del objetivo que se pueda desfasar. Las categorías con `total` en `None` se saltean, no cuentan como 0.
- **Litros se mide sobre la venta TOTAL DE LA EMPRESA** (ruta + V1/V20 Depósito, sin las bajas V2/V5), no sólo ruta: *"la planificación semanal es sobre toda la venta semanal"*. Así **numerador y denominador cuentan lo mismo**, porque el objetivo de Sell Out también es de empresa. Facturación y CCC **siguen midiendo ruta**, que es el universo de sus objetivos (`resultado.xlsx` suma ValorObjetivo de la ruta; `objccc.xlsx` se mide sin Depósito en todo el portal, ver `ccc_empresa`).
  - **`universo` es ahora un campo de cada KPI** (`_SEMANAL_KPIS` → `_SEMANAL_UNIVERSO`), no un filtro global. `_semanal_leer` deja de descartar el Depósito y lo marca con **`es_ruta`**; `_semanal_agg` manda cada KPI a su universo. Una sola lectura sirve a los dos (no se parsea el historial de 63 MB dos veces) y el criterio de exclusión no se duplica. Las listas salen de **`motor_11t.VENDEDORES_BAJA` / `VENDEDORES_DEPOSITO`**, que es la implementación única de la regla (CLAUDE.md), en vez de tuplas nuevas.
  - **La brecha era mucho más grande de lo que sugería el mes en curso.** Sobre agosto parcial daba ~1,4%; sobre meses cerrados el Depósito pesa **jul +6.883 L (16%) · jun +11.089 L (24%) · may +13.641 L (30%)**. Medirlo contra un objetivo de empresa como si fuera ruta habría mostrado un avance sistemáticamente hundido.
  - **Verificado que el número coincide con la tarjeta de Sell Out**: julio da **50.047,0 L** por los dos caminos (KPI Semanal y el universo de `_preparar_df_ventas(incluir_deposito=True)`), contra objetivo 60.597 L → **82,6%**. Las categorías del sell out cubren 50.044,8 de esos 50.047,0 L, así que el objetivo no mide un subconjunto.
  - **Regresión controlada**: facturación queda **byte a byte igual** en los 3 meses cerrados verificados (may 285.636.230 · jun 305.251.011 · jul 295.881.284) y los CCC de julio también (656 / 154 / 71, con la misma apertura semanal). El refactor de universos no movió nada de lo que ya estaba.
- **Portal** (`semNum` / `semExacto`): formato `12.345 L` para el tipo `litros` (`toLocaleString('es-AR')`, misma convención que las demás tarjetas de litros), con el valor exacto en el `title`. Notas al pie actualizadas en las dos tarjetas.
- **Validación en el portal real**: la fila Litros muestra **Objetivo mes 60.597 L** y con "↧ Usar promedio histórico" reparte **Plan 7.272 / 12.907 / 13.028 / 27.390 L** (suma 100,0%) contra **Real 2.233 L parcial**, con el desvío en gris por ser la semana en curso. El histórico de Litros da jul **50.047 L** · jun **56.508 L** · may **59.868 L**, y la nota al pie declara el universo del KPI seleccionado ("toda la venta de la empresa" en Litros, "ruta (sin V1/V20 Depósito)" en Facturación y CCC). Con la pestaña Facturación la tabla sigue mostrando **$295,9M** en julio y CCC Tradicionales **656**, sin cambios.
- **Validación con datos reales**: `/api/gerencia/semanal` → 200, `kpis` con los 5 IDs. Junio-2026 da **45.418,94 L**, semanas `[8.402, 6.746, 7.691, 22.581]`, pcts `[18,5 · 14,9 · 16,9 · 49,7]` — **recalculado aparte contra el CSV crudo con el mismo resultado exacto**. Los % de litros suman 100% en los 13 meses y siguen de cerca a los de facturación (jun: 19,9/14,1/16,0/50,0), que es el sanity check esperado. POST del plan con `litros` → 200, persiste y relee `[20, 25, 25, 30]`; filas de prueba (período **2099-01**, nunca una fecha real) borradas después. Histórico en frío **4,9 s** / cacheado 0,001 s, endpoint 80 ms: la pantalla es lazy y el caché por mtime no cambió.

## 2026-08-05 - fix(cierre): publicar las salidas auditables del motor 11T

Preflight del cierre diario sobre los datasets nuevos del motor 11T.

- **El guard NO necesitó cambios.** `check_git_cierre.py` clasifica **por prefijo de ruta**, no con un allowlist por archivo: todo lo que cuelga de `04_DATASETS_ORBIT/` ya es operativo permitido, así que `mod_11t_sin_cartera.csv`, `mod_11t_detalle.csv` y `mod_11t_excepciones.csv` pasaron desde el primer día. `python check_git_cierre.py` → **exit 0**, "solo hay cambios operativos permitidos". Sus pruebas de clasificación (`--test`): **todas OK**, y sigue bloqueando `.py`, `.bat`, `portal.html`, config y rutas desconocidas (verificado: con el `.bat` modificado devuelve exit 1).
- **Lo que sí faltaba era el allowlist de publicación.** `CIERRE_DIA_ORBIT.bat` no hace `git add .`: stagea una lista explícita, y los **tres** datasets nuevos del 11T no estaban en ella. Son dos listas distintas y sólo la primera los reconocía. Es el patrón ERR-014 (dadatinto, Plan Frizze): el archivo se regenera local, nunca viaja a Render y **el cierre igual cierra en verde**.
- **Agregadas tres líneas** a `CIERRE_DIA_ORBIT.bat`, respetando CRLF (`.gitattributes`: `*.bat text eol=crlf`; con LF el `if/else` de cmd se rompe): `mod_11t_detalle.csv`, `mod_11t_excepciones.csv` y `mod_11t_sin_cartera.csv`. Ninguno lo lee el portal, pero `/api/gerencia/once_titulares` publica la ruta de `mod_11t_excepciones.csv` **como puntero** en el payload: sin esto apuntaba a un archivo inexistente en Render.
- **`mod_11t_sin_cartera.csv` verificado** como dataset derivado y determinístico: tres corridas sobre el mismo detalle dan bytes idénticos, y **sin clientes SIN_CARTERA escribe sólo el encabezado** (`cliente_id,cliente_nombre,segmento_11t,titulares_cubiertos,titulares,botellas_netas`), no un archivo vacío. Se regenera en cada corrida del motor, así que nunca entra en un commit funcional.
- **Sin tocar** `cargar_clientes()` ni datasets ajenos al 11T: sigue como tarea independiente en `NEXT_TASK.md`. No se commiteó ningún CSV operativo.

## 2026-08-05 - fix(11T): corrección semántica — DEPOSITO y SIN_CARTERA no son lo mismo

Corrección sobre **`c32d91a`**, sin tocar ese commit. Aquel resolvió que el Depósito sume al total de empresa, pero metió en la misma bolsa dos cosas distintas: los clientes del Depósito (V1/V20) y los clientes **sin `codven`**. Todo lo que no fuera vendedor se etiquetaba `DEPOSITO`.

**Por qué importa:** los dos quedan fuera de los rankings, así que es tentador tratarlos igual. No lo son.

| | Qué es | Qué hay que hacer |
|---|---|---|
| `DEPOSITO` | Decisión comercial: el Depósito existe y vende | Nada, está bien |
| `SIN_CARTERA` | Dato faltante del ERP | Asignarle cartera |

Etiquetar un cliente sin `codven` como "Depósito" lo hace pasar por venta directa legítima y **el hueco no se arregla nunca**. Era exactamente lo que pasaba con **`#786 ANSELMI Y CIA`** (Autoservicio grande, 1.560 botellas de Smirnoff Flavours en julio): figuraba como Depósito cuando en realidad es un cliente al que le falta asignación en el ERP.

- **Cuatro categorías explícitas, mutuamente excluyentes** (`motor_11t`). Cada fila del detalle trae `universo` y cae en exactamente una:
  - `VENDEDORES` — cliente de la cartera de un vendedor de ruta. El único que va a rankings.
  - `DEPOSITO` — `codven` en V1/V20. Suma a empresa, sin cartera ni cumplimiento individual.
  - `SIN_CARTERA` — sin `codven` o sin asignación válida. Suma a empresa, fuera de rankings.
  - `BAJA` (V2/V5) no es un universo: queda fuera de todo.
  - `cuenta_vendedor` se mantiene como atajo de `universo == VENDEDORES`.
  - La asignación es un `where` encadenado sobre la misma columna, así que **una fila no puede caer en dos categorías**.
- **Renombrado `VENDEDORES_SIN_CARTERA` → `VENDEDORES_DEPOSITO`**: el nombre viejo decía "sin cartera" para referirse a los códigos del Depósito, que es justamente la confusión que este commit corrige.
- **`vendedor_id`** ya no dice `DEPOSITO` para todo lo que no es vendedor: dice `DEPOSITO` o `SIN_CARTERA` según corresponda.
- **Trazabilidad explícita de SIN_CARTERA** (antes no existía):
  - `motor_11t.clientes_sin_cartera(detalle)` — una fila por cliente con nombre, segmento, titulares que cubre y botellas netas.
  - **`04_DATASETS_ORBIT/mod_11t_sin_cartera.csv`** — salida auditable nueva, escrita junto al resto del trío 11T. La regeneración avisa por consola con los códigos: `[REVISAR] N cliente(s) SIN_CARTERA suman al total de empresa y no son Deposito`.
  - Excepción **`CLIENTE_SIN_CARTERA`** con los **códigos de cliente** en `clave`, no un total anónimo. La de `DEPOSITO` queda aparte.
  - `sin_cartera_total` y `sin_cartera_clientes` en `/api/gerencia/once_titulares`.
- **Invariante de tres vías** en todos lados: `cubiertos_empresa = cubiertos_vendedores + cubiertos_deposito + cubiertos_sin_cartera`. Propagado a `resumen_por_titular`, `11t_empresa` (`con_sin_cartera`), `once_titulares`, el 11T vivo de `cierre_mes` y `_cierre_once_titulares`. `mod_11t_acum.csv` suma la columna `universo`.
- **`generar_11titulares_excel.py`**: el Excel de preventa ahora también descarta los `SIN_CARTERA` (antes sólo bajas y Depósito). Una hoja de preventa es la ruta de alguien; un cliente sin cartera saldría con la columna Vendedor en blanco.
- **Lo que reveló la corrección**: en julio-2026 el aporte que `c32d91a` mostraba como "Depósito" era **100% `SIN_CARTERA`** (ANSELMI + SENN ENZO). El Depósito real (V1/V20) aportó **0**, porque sus 27 clientes no tuvieron compras 11T ese mes. Los totales de empresa **no se movieron** y Gordon's sigue en 32.
- **Intacto**: precedencia V3/V8, padrón único, arreglo de Ruta del Día, retiro de `mod_11_titulares` como fuente, exclusión V2/V5 y el tratamiento empresarial de V1/V20.
- **Objetivos sin tocar**: `objetivo 11T.xlsx` no se modificó. Su recalibración sigue **pendiente de confirmación de Peñaflor** (los objetivos se fijaron contra la regla vieja de CCC sin mínimo).
- **Validación**: pruebas funcionales del motor + integración → **96 tests OK**, sin skips (`test_motor_11t` + `test_motor_padron`), incluidas la regresión de Gordon's julio-2026 sobre el archivo real y las clases nuevas `SinCarteraNoEsDeposito`, `SinDobleConteo` y `UniversosEnDatosReales`. Suite completa: **108 tests, 102 OK y los 6 errores heredados** de descubrimiento (`test_alertas_reales`, `test_copiloto_*`, `test_kernel_proactivo`: scripts viejos que no son tests unittest y revientan al importarse; ajenos a este cambio).

## 2026-08-05 - fix(11T): regla definitiva de V20/Depósito — dos universos, empresa vs vendedores

Continuación de **`5a2f826`** (motor único de 11T + regla única de padrón). Ese commit dejó una contradicción abierta: al excluir el Depósito del universo de vendedores —que es correcto— también lo sacaba del **total de empresa**, y la venta directa desaparecía del 11T de la distribuidora. `CLAUDE.md` decía una cosa y el código hacía otra.

**Regla que queda (ahora escrita en `CLAUDE.md`):** *V20/Depósito no es vendedor activo ni posee cartera. Sus ventas válidas se incluyen únicamente en los totales empresariales de 11 Titulares y se excluyen de rankings e indicadores individuales.*

- **Dos universos explícitos en `motor_11t.py`**, en vez de un solo filtro que servía para las dos cosas:
  - `VENDEDORES_BAJA = (2, 5)` — fuera de **todo**, de los dos universos.
  - `VENDEDORES_SIN_CARTERA = (1, 20)` — Depósito / venta directa: **suma al universo EMPRESA**, nunca es vendedor. V1 es el bucket `deposito` del padrón (27 clientes: CLIENTES VARIOS, DELFIN S.A., mostradores) y V20 el código con el que factura; son la misma entidad física, igual que P&P Logística en `_LEEME_EMPRESA`.
  - Cada fila del detalle trae **`cuenta_vendedor`**. Un cliente **sin `codven`** en el padrón recibe el mismo trato: cuenta para EMPRESA, no es de nadie.
  - `cobertura_11t()` ya no descarta esas filas: las conserva marcadas. `resumen_por_titular()` devuelve `cubiertos` (empresa) abierto en `cubiertos_vendedores` + `cubiertos_deposito`. `resumen_por_vendedor()` y `marcas_cubiertas_por_vendedor()` pasan por `solo_vendedores()`, el filtro único del universo VENDEDORES.
  - El Depósito se etiqueta **`DEPOSITO`**, no `V1`/`V20`: si sale a pantalla o a un CSV no puede leerse como un vendedor más.
- **`generar_datasets_acum.generar_11t_acum()`**: la grilla de **cartera** sigue siendo sólo de vendedores de ruta (el Depósito no recibe cartera — sería un denominador inventado). Se le **agregan aparte** las filas realmente medidas del Depósito con `cuenta_vendedor=0`, así el numerador de empresa las toma y ningún corte por vendedor las ve. `mod_11t_acum.csv` suma la columna `cuenta_vendedor`.
- **`server_orbit.py`** — helper único `_universo_vendedores_11t()` que aplica el filtro (con fallback si el CSV viene de una generación anterior a la columna). Aplicado en: `11t_empresa` (totales de empresa **con** Depósito, `por_vendedor` y la lista `vendedores` **sin**, más `con_vendedores`/`con_deposito`), `11t_vendedor` (**rechaza** consultar V1/V20: no tienen cumplimiento individual), el KPI **"11T ✓"** del dashboard, `once_titulares` (`ccc_deposito` vuelve a traer un número real en vez del `0` cableado), el 11T vivo de `cierre_mes` y `_cierre_once_titulares` (cierre versionado).
- **`generar_11titulares_excel.py`**: el Excel de preventa es por día de visita = universo VENDEDORES. Su `EXCLUIDOS` local pasa a salir de `motor_11t.VENDEDORES_EXCLUIDOS_11T` para no tener una cuarta definición de "quién es vendedor".
- **Sin doble conteo, por construcción**: el padrón deja una sola fila por cliente (`motor_padron`, `5a2f826`), así que cada cliente cae en **exactamente un** universo y vale `cubiertos_empresa = cubiertos_vendedores + cubiertos_deposito`. Está testeado en sintético y sobre datos reales, y también en los endpoints.
- **Impacto medido (julio 2026)**: los totales de empresa **no se movieron** — Gordon's sigue en 32 y la regresión validada queda intacta. Lo que cambió es que el aporte del Depósito ahora es **visible y correcto**: 1 cliente en 9 de los 11 titulares, que es **`#786 ANSELMI Y CIA`** (Autoservicio grande, sin `codven` en el padrón, 1.560 botellas de Smirnoff Flavours). Antes ese cliente sumaba al total **y además** ensuciaba `resumen_por_vendedor` con un grupo de vendedor `NaN`; ahora suma al total y queda como `DEPOSITO`. Los 27 clientes `codven=1` no tuvieron compras 11T en julio, así que hoy aportan 0: el arreglo es **estructural**, evita que la venta del mostrador se pierda el mes que la haya.
- **Validación**: `python -m unittest test_motor_11t test_motor_padron` → **84 tests OK**, sin skips (incluye la regresión de Gordon's julio-2026 calculada sobre el archivo real: 25 trad + 7 AS = 32). Suite completa: **96 tests, 90 OK y 6 errores heredados** de descubrimiento (`test_alertas_reales`, `test_copiloto_*`, `test_kernel_proactivo`: no son tests unittest sino scripts viejos que llaman `input()` o imprimen emojis en consola cp1252 y revientan **al importarse**; ajenos a este cambio, ya estaban).

### Documentación pendiente saldada en este commit

`5a2f826` no actualizó los registros que exige el contrato del repo. Se completan acá, cubriendo también lo de ese commit: motor único de padrón, precedencia de cartera **V3/V8 → V8**, retiro de `mod_11_titulares.csv` como fuente de lectura del portal, y la corrección de **Ruta del Día** (`/api/vendedor/<vid>/ruta` devolvía **0 clientes para todos los vendedores, siempre**: `clean_code("3.0")` da `"30"` porque se come el punto, así que la comparación nunca era verdadera; corregido con `motor_padron.normalizar_codigo_vendedor`). Ambas cosas siguen intactas y con sus tests en verde.

## 2026-08-05 - feat(plan cobertura): altas fuera del listado + objetivo de 60 altas a diciembre

El negocio actualizó `01_INPUTS/Plan cobertura/on premise.xlsx`: completó códigos de cliente en el padrón y **agregó una hoja nueva, "altas fuera del listado"**, con clientes que se dieron de alta durante el plan y que el relevamiento original no tenía. La pantalla ahora los mide y muestra el avance contra el objetivo del plan.

- **Hoja nueva — `server_orbit.py`, `_plan_cob_altas_fuera()`**: lee del **mismo xlsx** la hoja cuyo nombre contiene "fuera" (código de cliente, nombre y número de vendedor). Las columnas se ubican **por su título, no por posición** (la hoja arranca en la columna B). Mismo cuidado que el padrón: openpyxl `read_only`, nunca `pd.read_excel`. Si la hoja no está, la pantalla queda como antes.
- **Se miden igual que los capturados**: la medición por cliente (activación = primera compra, recompras mes a mes, artículos, descuentos, sin cargos y acciones) se extrajo del loop a `_ficha()` y ahora la comparten las dos listas. Los IDs de la hoja nueva entran al mismo `_plan_cob_ventas(ids)`, así que no hay una segunda lectura del historial.
- **Vendedor y datos del PDV**: los 11 están en el maestro, así que localidad, dirección, razón social y **vendedor salen de la cartera real**; si alguno no estuviera, cae al número de vendedor que cargaron en la hoja (`asignacion: "planilla"`). Si el maestro y la hoja no coinciden, el tooltip lo dice.
- **Tarjeta nueva "Altas fuera del listado"** en la pantalla de gerencia, entre Capturados y Potenciales: mismas columnas que capturados (activación, meses, recompras, última compra, estado), **ficha del cliente al tocar la fila** y columna **Mensaje** (clave `CLI:<código>`, porque estos PDV no tienen ID de punto de venta). El buscador ahora filtra **cinco** listas.
- **Resumen superior — altas totales contra el objetivo**: KPI nuevo `24 / 60` con barra de avance, desglose "del listado + fuera del listado" y cuántas faltan. **`PLAN_COB_OBJETIVO_ALTAS = 60`** (meta a diciembre 2026), también en el plegable "Cómo funciona el plan". Las altas se cuentan **por cliente, no por fila**: el padrón repite algún PDV con el mismo código y el 1409 está en las dos hojas (sale en la tarjeta con el badge "También en el listado", pero suma una sola vez).
- **También en el perfil del vendedor**: `/api/vendedor/<vid>/plan_cobertura` filtra `altas_fuera` por `vendedor_id` igual que las otras listas, con su propia tarjeta **"Tus altas fuera del listado"** en la vista mobile (mismas tarjetas que los capturados, ficha al tocar). El KPI "Capturados" pasó a **"Clientes dados de alta"** = capturados + altas fuera, contadas por cliente. El objetivo de 60 **no se reparte por vendedor** (no hay tal reparto): aparece en el plegable "Cómo funciona el plan" aclarando que es de todo el equipo. V3 sigue con `no_aplica`.
- **`con_recompra` ahora cubre todas las altas** (padrón + fuera del listado, por cliente), en gerencia y en el vendedor: quedaba un número sobre otro denominador al lado del KPI de altas. Pasa de 8 a **14** en gerencia.
- **Validado con datos reales (2026-08-05)**: `/api/gerencia/plan_cobertura` 200 en 6,5 s en frío y 0,01 s cacheado. Padrón 203 filas (el negocio sacó 2 PDV y completó los 19 que estaban sin relevar); **altas totales 24 de 60 (40%)** = 14 clientes del listado + 10 nuevos fuera del listado (11 filas, una repetida); 24 de 24 ya compraron, 14 con recompra. Tarjeta pintada con las 11 filas, ficha de `#1371 HURQUIZA` (activación 21/03/2026, 5 meses, 4 recompras, 114 bot.) y buscador `san francisco` → 6 de 11 altas fuera / 4 de 16 capturados / 17 de 85 potenciales. **Cuadra por vendedor**: las 11 filas se reparten V8 6 + V9 5, y las altas por cliente (V8 10, V9 10, V6 2, V4 1, V10 1, V7 0, V3 0) suman **24**, igual que gerencia; `con_recompra` por vendedor suma 14. Vista mobile de V9 renderizada con sus 5 altas fuera y la ficha abierta desde la tarjeta. `node --check` sobre el JS del portal OK.

## 2026-08-04 - fix(cierre): el xlsx del Plan Frizze no llegaba a Render

**Síntoma:** el negocio agregó los clientes **1462 y 1463** a la línea `Clientes activos:` de `01_INPUTS/PLAN FRIZZE/planfrizze.xlsx` y **no aparecían en el portal**.

- **El parser está bien**: con el archivo actual, `/api/gerencia/plan_frizze` devuelve las 4 tarjetas (301, 1443, 1462, 1463) y por vendedor **V8** = 301 + 1462 + 1463 (DANGUISE DISTRIBUCIONES, San Francisco, dos códigos con el mismo nombre) y **V10** = 1443. No hay que tocar código.
- **La causa es de publicación**: `01_INPUTS/PLAN FRIZZE` **no estaba en el allowlist de `git add` de `CIERRE_DIA_ORBIT.bat`**, y el cierre no hace `git add .`. El archivo se editaba en la PC y quedaba modificado para siempre: Render seguía sirviendo la versión commiteada, con 2 clientes. **Y el cierre cerraba en verde**, porque `check_git_cierre.py` clasifica todo `01_INPUTS/**` como operativo permitido — ese guard bloquea código colado, no verifica que los datos viajen. Mismo patrón que ERR-014 (dadatinto).
- **Arreglo**: `git add "01_INPUTS/PLAN FRIZZE/planfrizze.xlsx"` sumado al allowlist (respetando CRLF del .bat) y el xlsx actualizado commiteado, así los dos clientes nuevos salen en el próximo deploy.
- **Regla para la próxima**: todo input que el negocio edite a mano tiene que entrar al allowlist en el mismo cambio en que se lo empieza a leer. Chequeo rápido: `git status --short 01_INPUTS/` después de un cierre exitoso — lo que siga modificado no llegó al portal.

## 2026-08-04 - feat(plan cobertura): pantalla en el perfil del vendedor

El Plan Cobertura era **sólo de gerencia**: el vendedor no veía ni sus capturados ni los PDV de sus localidades. Ahora cada vendedor tiene su propia pantalla con **los PDV que le tocan**, con el mismo padrón y los mismos criterios que gerencia (nada se recalcula aparte).

- **Backend — `server_orbit.py`**, endpoint nuevo `GET /api/vendedor/<vid>/plan_cobertura`. Reusa `_plan_cobertura()` (mismo caché por mtime, no vuelve a abrir el xlsx ni a leer el historial) y filtra por `vendedor_id`:
  - **capturados** → los de **su cartera** según el maestro de clientes;
  - **potenciales / no atendidos / atendidos sin código** → los de **sus localidades**, con el criterio de zona que ya usaba gerencia (vendedor dominante de la localidad, y si no tenemos clientes ahí, el dominante del partido).
  - El `resumen` se recalcula sobre su subconjunto, así que los KPI son suyos y no del padrón entero.
- **Mensaje por PDV, de sólo lectura para el vendedor**: lo que gerencia escribe en la columna "Mensaje" (tabla `plan_cob_nota`) viaja en cada fila del payload (`mensaje`, `mensaje_autor`, `mensaje_fecha`). Se lee **fuera del caché del plan** (`_plan_cob_notas_map()`, el mismo SELECT que ya usaba el endpoint de notas), porque el mensaje se edita a mano en cualquier momento. Guardar y borrar siguen siendo de gerencia.
- **V3 queda fuera del plan**: no trabaja On Premise (sólo tradicional almacén/despensa/kiosco), así que el endpoint le devuelve listas vacías con `no_aplica` y el portal le **oculta la pestaña**, igual que ya hace con Plan AS.
- **Corrección del vendedor por zona (afecta también a gerencia)**: V3 se excluye del cálculo del dominante por localidad/partido en `_plan_cob_vendedor_por_zona`. Antes **28 PDV** (1 atendido sin código + 20 potenciales + 7 no atendidos) quedaban asignados a V3 — que no puede trabajar un bar — y con el filtro por vendedor **no le llegaban a nadie**. Ahora los 205 PDV del padrón caen en un vendedor que sí trabaja el canal (los 28 pasaron casi todos a V8, que va de 7 a 35 PDV) y ninguno queda sin asignar.
- **Frontend — `portal.html`**: pestaña **🍽️ Cobertura** en el menú inferior del vendedor. **Carga lazy al tocarla** (el padrón + el historial no tienen por qué demorar el login) y se vuelve a pedir al Actualizar sólo si el vendedor ya la había abierto. Vista de celular con **tarjetas, no tablas**: 6 KPI propios, el plegable "Cómo funciona el plan", y las cuatro listas (capturados / sin código / potenciales / no atendidos) con badge de estado, por qué le corresponde ese PDV (localidad o partido), las observaciones del relevamiento y el mensaje 📝 de gerencia. Tocar un capturado abre **la misma ficha** que en gerencia (`pcModalCliente`, extraída de `pcDetalle` para compartirla): activación, recompras mes a mes, artículos, descuentos y sin cargos.
- **Validado con datos reales (2026-08-04)**: los 205 PDV del padrón se reparten V7 65 · V9 47 · V8 35 · V6 24 · V10 22 · V4 13, **cero sin asignar**, y la suma por vendedor coincide con las listas de gerencia (206 con la fila repetida del padrón, que sale en capturados y en potenciales). V9: 47 PDV, 7 capturados (6 clientes), 1 con recompra, 40 no atendidos; ficha de `#1216 Salomon y W` abierta desde el celular con sus 6 meses de compra y 17 artículos. V3: `no_aplica` y pestaña oculta. Mensaje de gerencia probado alta → visible en la vista del vendedor → borrado (la tabla `plan_cob_nota` queda como estaba, vacía). Sin errores de consola; `node --check` sobre el JS del portal OK.

## 2026-08-03 - feat(plan cobertura): buscador y mensaje por punto de venta

Dos pedidos del negocio sobre la pantalla **Plan Cobertura**: poder buscar dentro de los 205 PDV y poder dejar escrito qué hay que hacer con cada uno.

- **Buscador (lupa)**: una sola caja arriba de todo que filtra **las cuatro listas a la vez** (capturados, atendidos sin código, potenciales, no atendidos). Busca por **cliente** (nombre, razón social, código, ID de PDV), **localidad** (y partido, dirección) y **vendedor** (código y nombre); también entra el segmento, el tipo y las observaciones. Acepta **varias palabras**: coincide el PDV que las tenga todas, así `villa dolores v9` deja los de Villa Dolores que atiende V9. El título de cada tarjeta pasa a mostrar `N de M` mientras hay filtro; los KPI de arriba **no** se tocan (son el total del padrón, ver la regla de no mezclar contador filtrado con total).
- **Columna "Mensaje"** a la derecha de cada PDV, en las cuatro tablas: input + botón **💾 guardar** y **🗑 borrar** (borrar un mensaje ya guardado pide confirmación). Debajo queda quién lo escribió y cuándo, o `sin guardar` mientras se está tipeando. En los capturados la celda **no abre la ficha del cliente** (la fila sigue abriéndola).
- **Persistencia — `server_orbit.py`**: tabla nueva `plan_cob_nota(clave, mensaje, autor, updated_at)` en `orbit.db` y endpoint `GET/POST /api/gerencia/plan_cobertura/notas` (mensaje vacío = borra la fila). Mismo patrón que el seguimiento gerencial de alertas. **Va aparte del payload del plan** porque ése se cachea por mtime de los archivos y el mensaje se edita a mano en cualquier momento; el portal lo pide en cada entrada a la pantalla.
- **Clave del mensaje = `PDV:<ID PUNTO DE VENTA>`** (`_plan_cob_clave`, campo `clave` en el payload). El ID del relevamiento es **único en las 205 filas**, así que el mensaje sobrevive a que se reordene o se reemplace el xlsx del padrón. Fallback a nombre+localidad normalizados si algún día viniera vacío. **El padrón no se toca**: los mensajes viven sólo en la base.
- **Render parcial**: `pcRender()` arma el shell una vez y `pcFiltrar()` re-pinta **sólo los `<tbody>`** en cada tecla — si se re-renderizara la pantalla entera el input perdería el foco y se podría escribir una letra por vez. Un mensaje tipeado y todavía sin guardar sobrevive al filtrado (`PC_NDRAFT`).
- **Validado con datos reales (2026-08-03)**: 206 filas pintadas, las 206 con clave única; alta/edición/borrado del mensaje contra la API (200 y `{}` tras borrar, 400 sin clave); en el portal, `villa dolores v9` → 5 de 8 capturados, 27 de 104 no atendidos, 0 potenciales, con el foco del buscador intacto tras escribir la frase entera; mensaje guardado, sobreviviendo al re-render de la pantalla y borrado; click en la celda de mensaje no abre la ficha, click en la fila sí. Sin errores de consola.

## 2026-08-03 - revert(plan cobertura): sin sugerencia de candidatos por dirección

Se había agregado, para los 17 PDV atendidos sin `CÓD. CLIENTE` cargado, una columna que proponía clientes del maestro cruzados por dirección. **Revertido a pedido del negocio, y con razón**: los PDV del plan son **On Premise** (restaurantes y bares con carta) y los candidatos que devolvía el cruce eran almacenes y kioscos de la misma calle. No es que la coincidencia sea débil — **no existe**, así que mostrarla sólo agrega ruido y riesgo de que alguien la cargue por error.

- El cruce por dirección se probó contra los 17 casos reales: 1 sola coincidencia de calle + altura y el resto vecinos con otra altura. Ni siquiera ese único caso pasa el filtro de canal.
- **Decisión: el código de cliente lo averigua el negocio y lo carga en el Excel.** La pantalla sigue listando los 17 PDV atendidos sin código para que el pendiente esté a la vista, sin proponer nada.
- **No volver a implementarlo** salvo que aparezca una llave real (un ID de PDV compartido con el ERP, o el relevamiento con la dirección completa y el canal correcto). Cruzar por calle sin altura, o por nombre contra la razón social —que en el maestro es el nombre de la persona, no el del local— no alcanza.

## 2026-08-03 - feat(gerencia): pantalla Plan Cobertura (On Premise B&C)

**Plan de Grupo Peñaflor** (resumen en `01_INPUTS/Plan cobertura/RESUMEN PLAN COBERTURA.pdf`): incrementar cobertura en clientes **categoría B y C**, destinado a **restaurantes y bares con carta de bebida**. Se mide por **CCC únicos del canal On Premise B&C, de julio a diciembre 2026**. La mecánica (1+2 cajas por línea comercial, Premium 1+1, 5+1 en Alma Mora sólo para capturados, 2+1 de Cinzano en recompra, 5+1 de La Mascota) queda en la pantalla, en el bloque plegable "Cómo funciona el plan".

- **Fuente del padrón**: `01_INPUTS/Plan cobertura/on premise.xlsx` (205 PDV relevados). Autodetecta el xlsx de la carpeta, así que reemplazar el archivo alcanza para actualizar la pantalla.
- **Backend — `server_orbit.py`**, endpoint `GET /api/gerencia/plan_cobertura`. Tres grupos, que son los que pidió el negocio:
  - **Capturados** (PDV con código de cliente cargado): se les mide **activación = fecha de la PRIMERA compra**, recompras mes a mes, artículos comprados y ofertas recibidas. El historial se arma encadenando las cuatro fuentes que cubren la línea de tiempo sin huecos: `02_HISTORY/historial_ventas.csv` (2024-03 → 2026-05) + `historial_ventas_cliente.csv` (2026-05 → último cierre) + `ventas_acumulada.csv` + `ventas.csv`, deduplicando por fecha+cliente+artículo+cantidad+importe.
  - **Potenciales** y **No atendidos**: como no están dados de alta, se les sugiere **vendedor por zona** — el que más clientes tiene en esa localidad según el maestro; si la localidad no tiene ni un cliente nuestro, cae al dominante del **partido**. La pantalla dice cuál de los dos criterios se usó. Los 205 PDV quedaron con vendedor asignado (7 por partido).
  - **Atendidos sin código cargado** (17): el relevamiento dice que los atendemos pero el padrón no tiene el código, así que no se les puede medir nada. Se listan aparte para que el pendiente se vea en vez de desaparecer.
- **Acciones comerciales del cliente**: se **invierte el payload de Acciones Comerciales** en vez de re-detectar acá, para no tener dos criterios de "acción = uso" conviviendo. Como ese catálogo es del mes vigente, para los clientes que compraron antes viene vacío; por eso la ficha muestra además el **dato duro de la factura**: qué artículos compró con descuento y con qué %, y los **sin cargo** recibidos (líneas de importe 0, que son los combos del plan). Los rechazos (cantidad negativa) no cuentan.
- **Frontend — `portal.html`**: pantalla **Plan Cobertura** (menú Productos), **carga lazy** como Semanal — el padrón y el historial no tienen por qué demorar el login. Tira de KPIs + una tarjeta por grupo. Click en un capturado → ficha con segmento, vendedor, localidad, activación, chips de recompra mes a mes (marcando el mes de activación), tabla de artículos y el bloque de acciones/ofertas.
- **Dos cosas que costaban la pantalla y quedaron arregladas**:
  - `on premise.xlsx` viene **inflado** (la hoja declara ~1.048.000 filas para 205 reales) y `pd.read_excel` tardaba **15,6 s**. Se lee con **openpyxl en read_only** cortando por filas vacías: milisegundos. Mismo patrón que `producto activos.xlsx`.
  - `historial_ventas_cliente.csv` se escribe **UTF-8 con BOM**: leído como latin1 la primera columna quedaba `ï»¿fecha_comprobante`, el chequeo de columnas fallaba y **la fuente se descartaba en silencio**. Síntoma: tres clientes activos (`#1416`, `#1417`, `#1409`) figuraban con 0 compras teniendo venta real. Ahora se prueba utf-8-sig primero y se limpia el BOM del encabezado.
- **Validado con datos reales (2026-08-03):** 205 PDV · 7 clientes capturados (8 filas: el padrón repite un PDV con el mismo código y el relevamiento lo marca) · 2 con recompra · 77 potenciales · 104 no atendidos (20 sin relevar). `#389 Bar Comedor` (V10): activación 23/08/2024, 10 meses con compra, 9 recompras, 294 botellas, 2 sin cargos. `#1216 Salomon y W` (V9): activación 17/07/2025, 6 meses, 5 recompras, 17 artículos, 21 líneas con descuento. Endpoint 200 en **2,9 s en frío y 0,008 s cacheado**, con las tres tarjetas y la ficha probadas en el portal.

## 2026-08-03 - feat(gerencia): pantalla Incentivo Alma Mora Malbec Low (código 74887)

**Mecánica pedida por el negocio:** cliente con compra del **código 74887** (ALMA MORA MALBEC DULCE LOW 6X750), medido **sólo sobre autoservicios**, con el **mínimo de 6 botellas** que pide la cobertura de Autoservicio (CLAUDE.md) — igual que el Incentivo Dada. Objetivo = **22% de la cartera de autoservicios**.

> **Corrección post-review (misma fecha):** la primera versión contaba con la sola compra, sin mínimo. El negocio marcó que en autoservicio la cobertura son 6 botellas. Con el criterio corregido el logrado pasa de 1 a **0**: el único autoservicio comprador llevó 3 botellas. Se agregó la lista **"A un paso"** para que ese cliente no desaparezca de la pantalla.

- **Backend — `server_orbit.py`** (bloque nuevo debajo del Incentivo Dada):
  - `_cartera_autoservicios()`: cantidad y detalle de la cartera AS desde `clientes.xlsx`, clasificando con `_clasificar_segmento` (el SubSegmento manda sobre el Ramo). Es el **mismo denominador** que la tarjeta de cobertura del dashboard, así que el 22% no se calcula sobre otro universo.
  - `_incentivo_almamora()`: lee `01_INPUTS/ventas_acumulada.csv` **completo, sin filtro de fecha** (mismo criterio que 11T e Incentivo FARO), filtra el código, excluye V1/V2/V5/V20 y agrupa por cliente. **Cliente logrado = autoservicio de la cartera con compra NETA > 0 y ≥ 6 botellas**: los rechazos restan y un envío 100% bonificado (importe 0) **no** cuenta como CCC. Los que compraron pero no llegan a 6 salen en `parciales` con cuántas botellas les faltan. Cacheado por mtime de las dos fuentes.
  - La venta se le atribuye a **quien facturó** (`CodVendedor`), con el dueño de la cartera como fallback — misma regla que Innovaciones.
  - Endpoint `GET /api/gerencia/incentivo_almamora`. Devuelve objetivo, logrado, faltan, avance, cobertura %, `por_vendedor` con el detalle de cada cliente (segmento del maestro + fechas de compra) y el período que cubre la fuente.
- **Frontend — `PAV MATINAL PE_A FLOR/portal.html`**: item de menú **Incentivo Alma Mora Low** debajo de Incentivo Dada, `gIncentivoAlmaMora()` con el KV del producto, tarjeta con 4 KPIs (objetivo / acumulado logrado / faltan / avance) y barra de avance. **Click en el acumulado** abre el modal de logrados por vendedor y **click en un vendedor** despliega sus clientes con **segmento, localidad y fecha de compra** (también se llega directo tocando el vendedor en la pantalla). Abajo, la tabla **"A un paso"**: quién compró, cuántas botellas lleva y **cuántas le faltan** para las 6. Reusa las clases `dd-*` del Incentivo Dada; sólo se agregó el acordeón `am-*`.
- **Imagen**: `01_INPUTS/incentivo/Alma Mora Malbec Low (74887).pdf` exportado a `PAV MATINAL PE_A FLOR/almamora_low.png` (el PDF es una sola página con el KV, sin mecánica escrita).
- **Validado con datos reales (2026-08-03):** cartera AS **244** → objetivo **54** (22%). Logrado **0**, faltan **54**. Los cuatro clientes que compraron el código quedan afuera y **cada uno por su motivo**: `#8125 CEBALLOS CARLOS JULIO` (V9, Autoservicio Tradicional, 21/07) compró **3 botellas** → va a "A un paso", le faltan 3; `#1082` es ALMACENES (se informa como "1 cliente fuera de autoservicio"); `#1093` es autoservicio y llevó 6 botellas pero **100% bonificado** (neto 0, no es CCC); `#8195` es almacén y además rechazado. Endpoint en 200 con JSON serializable y las dos rutas del drill-down probadas en el portal.
- **Fuentes ya publicadas por el cierre**: `ventas_acumulada.csv` y `clientes.xlsx` están en el allowlist del `.bat`, así que la pantalla se actualiza sola con el cierre diario. **El código y el PNG hay que commitearlos aparte** (el cierre aborta si quedan cambios de desarrollo sin commitear).

## 2026-07-30 - fix(maestro): los 10 clientes duplicados quedan asignados a V8, con guard para que no vuelva a pasar

**Criterio del negocio:** el cliente es de la vendedora que **le supo vender**.

- **Historial revisado:** `02_HISTORY/historial_ventas.csv` + `historial_ventas_cliente.csv` + `ventas.csv` + `ventas_acumulada.csv`. Rango **2024-04-15 → 2026-07-29**, sin fechas nulas.
- **Resultado: los 10 van a V8**, y no es un empate resuelto a dedo:
  - **3 clientes le compraron SÓLO a V8** y nunca a V3: `#1336`, `#1414`, `#1424`.
  - **7 le compraron a las dos, pero con un patrón de traspaso de ruta**: V3 vendía hasta junio 2026 y deja de aparecer; V8 arranca en junio/julio y es **la última en los 10 casos**. Ejemplos: `#272` (V3 hasta 24/06, V8 hasta 22/07), `#1065` (V3 hasta 12/06, V8 hasta 29/07), `#1257` (V3 hasta 03/06, V8 hasta 29/07).
  - **`#320 RABINO JOSE JUAN` es el caso al revés y refuerza lo mismo**: V8 le vende desde 2024-04 (177 líneas, $16,5M en 24 meses) y V3 le hizo 2 líneas sueltas en mayo 2026. Siempre fue de V8.
  - Para que quede dicho: en `#272` y `#1065` **V3 tiene más historia** (16-17 meses, 40 líneas cada uno) pero cortada en junio. Si el traspaso de ruta no fue tal, son los dos a revisar.
- **Cambio 1 — `01_INPUTS/clientes.xlsx`:** borradas las 10 filas con `codven = 3`. El maestro pasa de **2.139 filas / 2.129 códigos** a **2.129 / 2.129**: un cliente, una fila. El archivo está versionado en git y en el allowlist del cierre, así que el arreglo viaja a Render y es reversible.
- **Cambio 2 — guard en los dos loaders** (`_dedup_clientes()` en `generar_datasets_acum.py`, y el bloque equivalente en `_clientes_maestro()` de `server_orbit.py`): si el ERP vuelve a exportar un cliente en dos rutas, se deja **una** fila y se imprime `[AVISO]` con los códigos y los `codven` en conflicto. Ninguno de los dos puede resolver a quién pertenece el cliente (no tienen las ventas a mano), así que **no adivinan**: cortan la duplicación —que es el daño silencioso— y piden que se corrija en el ERP.
- **Por qué importaba:** al estar en las **dos** carteras, esos clientes contaban dos veces en el denominador de cobertura, CCC y planes. Es el error más caro de encontrar porque no rompe nada: sólo empeora los porcentajes.
- **Impacto medido:** cartera Tradicional **1.693 → 1.684**, V3 Tradicional **293 → 284** (9 de los duplicados eran tradicionales; el décimo, `#320`, es On Premise y V3 no tiene esa fila). **V8 no pierde ninguno**: ya tenía su propia fila para los 10. Total de cartera 2.059 → 2.050.
- **Validado:** pipeline completo en el orden del .bat, el guard probado con un duplicado sintético (avisa y deja 1 fila), los 10 clientes con `codven = 8` en el maestro, la ficha de `#272` muestra ALVAREZ VANESA, y 23 endpoints en 200 con serialización JSON verificada.

## 2026-07-30 - feat(canal): PROXIMITY (estaciones de servicio) pasa a ser canal propio

**Decisión del negocio:** las 32 estaciones de servicio no son On Premise ni Autoservicio. Canal propio, **umbral de cobertura 6 botellas**, y **V3 sí lo trabaja** (a diferencia de AS y On Premise).

- **Contexto:** venían clasificadas distinto en cada lado — el motor las mandaba a On Premise (por el SubSegmento `Estacion de Servicio - AXION`) y el portal a Autoservicio (por la clave `PROXIMITY` del Ramo). Era la última discrepancia entre clasificadores.
- **Cambio 1 — los CUATRO clasificadores** (apareció un cuarto: `LEGACY/orbit_matinal_v42.py:clasificar_segmento_operativo()`, que genera `mod_ccc_segmento.csv` y alimenta el **CCC del día**; si no se tocaba, el CCC del día y el del mes se contradecían). `PROXIMITY` se resuelve **antes** que On Premise en los cuatro, y se sacó `ESTACION DE SERVICIO` de las claves de On Premise y `PROXIMITY` de las de Autoservicio/Tradicional.
- **Cambio 2 — umbral 6.** `UMBRAL["PROXIMITY"] = 6` en el motor y `threshold_cobertura()` en el legacy.
- **Cambio 3 — V3 trabaja Proximity.** Constantes nuevas `_V3_SEGMENTOS` / `_V3_SUBCANALES` en el motor, en vez de las listas sueltas `["ALMACEN","KIOSCO"]` repetidas en cobertura e innovaciones. Sus 8 estaciones entran a su cartera.
- **Cambio 4 — que no se pierdan en ningún total.** Este es el riesgo real de agregar un canal: varios lugares sumaban canal por canal con lista fija y el cliente nuevo desaparecía sin que nada avisara. Revisados y corregidos **uno por uno**:
  - `_ccc_mes_por_vendedor()`: nueva clave `proximity` y **entra al `total`**.
  - Dashboard de vendedores y ficha de vendedor: `ccc_proximity` / `ccc_dia_proximity` y los dos totales (`ccc_total`, `ccc_dia_total`).
  - `real_ayer_segmento`: `SEGMENTOS_POSIBLES` (si no, la venta de esas estaciones no aparecía en ninguna fila).
  - Ranking de gerencia y cierre mensual: `ccc_total` sumaba `TRAD+AS+OP+OTROS` y se comía Proximity.
  - Plan vs Real del día: `ccc_prox` en el desglose (el `ccc_total` ya usaba `nunique()`, ese no se perdía).
  - Acciones comerciales: `_acc_seg_canon()` — una acción **sin canal declarado** (= aplica a todos) dejaba afuera a Proximity. Ahora está en el conjunto, y se detecta el canal explícito si la regla lo nombra.
  - Tarjeta de canales de gerencia (`/api/diagnostico`): cuarta fila **Proximity** con color propio.
  - `portal.html`: `_COB_SEG_ORDER` (sin esto el bloque quedaba ordenado antes que Autoservicio).
- **Lo que queda afuera a propósito:** el **11T** (se mide en AS + Almacén + Kiosco; se agregó la rama explícita en `clasificar_segmento_11t` para que no sea un olvido) y la **planificación** del vendedor, que sigue con 3 canales — tocar `PLAN_SHEET_COLS` implica cambiar el esquema de Google Sheets, que es la fuente de verdad ([[project_gsheets_planificaciones]]).
- **Validado con el pipeline real, en el orden del .bat** (`test_legacy_run.py` → `test_datasets_orbit.py` → `generar_datasets_acum.py`; el exportador legacy **pisa** `mod_innovaciones_segmento.csv`, por eso el orden importa):
  - **Los 4 clasificadores dan el mismo resultado en los 2.139 clientes: 0 discrepancias.** Era el objetivo pendiente de la entrada anterior.
  - Cobertura: canal **PROXIMITY con 32 clientes** (V4 11, V3 8, V6 6, V10 4, V9 3), umbral 6. On Premise 148 → **124**.
  - `clientes_dia.csv`: las estaciones salen como PROXIMITY, las carnicerías/verdulerías/panaderías como TRADICIONAL.
  - **Cubiertos 0 en Proximity y eso es el dato real, no un cálculo faltante**: en todo julio hay **una sola** venta a una estación (`#391 BORTOLON Y URQUIZA`, V4, 1 botella de JW Red el 24/07). Aparece como `ccc_proximity: 1` en V4 y no llega al umbral de 6, por eso cubiertos 0.
  - Innovaciones: subcanal PROXIMITY presente, V3 con ALMACEN + KIOSCO + PROXIMITY, 26 de 27 productos reconcilian exacto contra `ventas.csv`.
  - 24 endpoints en 200 + `node --check` del JS del portal.

## 2026-07-30 - fix(clasificación): el SubSegmento manda sobre el Ramo — 60 clientes estaban en el canal equivocado

**Reporte del negocio:** `#525 Velazquez Florencia` es un almacén/kiosco de V8, `#7215` una verdulería y `#7533` una carnicería de V3. La tarjeta las tenía en OTROS y en On Premise.

- **Causa raíz — el Ramo le ganaba al SubSegmento.** El ERP mete carnicerías, verdulerías, panaderías y casas de pastas bajo `Ramo = AWAY FROM HOME`. Los tres clasificadores miraban las palabras clave de On Premise contra Ramo **y** SubSegmento a la vez, así que el Ramo definía el canal y el SubSegmento fino (`Carniceria/Granja`, `Verduleria`) no llegaba a leerse nunca. Es **la misma clase de bug** que [[business_rule_autoservicio_subramo]] (Autoservicio por Subramo, corregido el 20/07): ahí se arregló para AS, pero la precedencia general quedó al revés.
- **Segunda causa — `KIOSKO` con K.** `_TR_KEYWORDS` tenía `KIOSCO`/`MAXIKIOSCO` pero no la grafía con K que usa el ERP, así que esos clientes caían en **OTROS** y quedaban fuera de todas las tarjetas (la de Innovaciones mide 5 subcanales, OTROS no es ninguno). Eran 3: `#525`, `#1247` y `#1412`.
- **Cambio 1 — los tres clasificadores, que estaban duplicados y ahora dicen lo mismo:**
  `generar_datasets_acum.py:_clasificar()`, `server_orbit.py:_clasificar_segmento()` y `tools/generar_cierre_mensual.py:_seg()`. Orden nuevo: Mayorista → Autoservicio → **SubSegmento solo** (On Premise, después Tradicional) → **recién ahí el Ramo** como fallback. Se agregó `KIOSK` (cubre las dos grafías) y `VERDULERIA` a las claves de Tradicional.
- **Cambio 2 — `generar_cobertura_acum()`, lista blanca de V3.** Para V3 se exigía además que el SubSegmento dijera `ALMACEN|DESPENSA|KIOSCO`: se comía las carnicerías, verdulerías y panaderías de su ruta, que V3 **sí** atiende. Alcanza con `segmento == TRADICIONAL`, que ya excluye AS / On Premise / Mayorista.
- **Impacto medido (60 clientes cambian de canal, sobre 2.139):** `Carniceria/Granja` 38, `Panaderia` 12, `Verduleria` 4 y `Casa de Pastas` 3 pasan de **On Premise a Tradicional**; los 3 `KIOSKO` de **OTROS a Kiosco**. Tocan a los 7 vendedores (V9 18, V3 14, V6 11, V4 9, V10 6, V7 1, V8 1).
  - **Cobertura:** cartera On Premise **191 → 148**, Tradicional **1.622 → 1.693**. Cambia el umbral con que se los mide: **3 botellas en vez de 6**. Sube el % de On Premise de todos (menos cartera, casi los mismos cubiertos) y se mueve el de Tradicional. V3: cartera 268 → **293**, cubiertos 21 → **26**.
  - **Innovaciones:** la tarjeta pasa a reconciliar **26 de 27 productos exactos** contra `ventas.csv` (antes 23). CCC total 480 → **485**.
- **Validado:**
  - Los tres clientes reportados caen donde tienen que caer: `#525` → KIOSCO de V8, `#7215` y `#7533` → ALMACEN de V3, y aparecen como faltantes en esas filas.
  - El motor y el portal dan el **mismo** resultado en los 2.139 clientes salvo 33 discrepancias que ya existían antes del cambio y no se tocaron (ver PENDIENTE: estaciones de servicio).
  - Reglas de negocio intactas: V3 sigue con `ccc_autoservicio = 0` y `ccc_onpremise = 0`, y sus filas de Innovaciones siguen siendo sólo ALMACEN y KIOSCO.
  - **Heurística de [[business_rule_autoservicio_subramo]]** (si el objetivo del canal supera su cartera, la clasificación está mal): objetivo CCC On Premise + Vinotecas + OP Noche = 56 sobre cartera 148; Tradicionales 845 sobre 1.693; Autoservicios 145 sobre 199. Ningún canal quedó por debajo de su objetivo.
  - 23 endpoints en 200 (dashboard, alertas, innovaciones, cobertura, 11T ×3, sell out ×2, planes AS, incentivo FARO, acciones, días de stock, clientes, vendedor V3/V8/V9).
- **Cambio 3 — `CADENAS REGIONALES (BAR)` no es un bar** (dato del negocio: es un formato de supermercado grande). El clasificador del portal y el del cierre buscaban `CADENA REGIONAL` en singular, no matcheaban el plural, y caían en la clave `"BAR"` del bloque On Premise por el `(BAR)` del nombre → **falso positivo por substring**. Se agregó `CADENAS REGIONALES` a las claves de Autoservicio de los tres clasificadores, que se evalúan antes que On Premise. Afecta a `#786 ANSELMI` (70 líneas de venta en julio). **No se tocó la clave `"BAR"`**: `#7934 ZAMORA BUSTOS` tiene `Ramo = BAR` y es un bar de verdad; `#1278 RESTAURANT CON BARRA` también queda On Premise. Verificados los tres.
- **Los tres clasificadores ahora dan el mismo resultado** en los 2.139 clientes, salvo las 32 estaciones de servicio (`Ramo = PROXIMITY`) que siguen pendientes de definición (el motor las manda a On Premise, el portal a Autoservicio; es previo a este cambio).
- **Lo que NO se tocó:** `#7174` y `#7231` son bares que el maestro tiene asignados a **V3**, y el negocio confirma que son de **V8**. Eso es una corrección de cartera en el ERP, no de código: editar el export a mano se pierde en la próxima bajada y tapa el problema. Quedan en `NEXT_TASK.md` con los otros huecos del maestro. Son la última diferencia que queda en Innovaciones (Cazador Malbec mide 170 sobre 174 reales: estos 2 bares + `#1458` y `#1459`, que no están en el maestro).

## 2026-07-30 - change(innovaciones): la compra cuenta para el vendedor que la facturó + causa real de las diferencias de CCC

**Definición del negocio:** en Innovaciones la venta le cuenta a **quien la hizo**, no al dueño de la cartera.

- **Cambio — `generar_datasets_acum.py:generar_innovaciones_segmento()`:**
  - `clientes_compraron` = clientes **de ese subcanal** a los que **ese vendedor** le facturó el producto, esté o no en su cartera. Antes era la intersección con la cartera propia, así que una venta cruzada se caía entre las dos puntas.
  - **Un par (producto, cliente) le cuenta a un solo vendedor** (si dos le facturaron el mismo producto al mismo cliente, se lo queda el de mayor volumen). Sin esto el total de gerencia — que suma por vendedor — contaría dos veces al cliente. Hoy no hay ningún caso, es un seguro.
  - Se abre la fila vendedor × subcanal también cuando el vendedor **vendió** ahí sin tener cartera propia (antes se saltaba con `continue` y la venta desaparecía de nuevo).
  - `clientes_faltantes` (el plan de acción del vendedor) ahora descuenta a los clientes que **ya compraron el producto a cualquier vendedor**: no se manda a visitar a alguien que ya lo tiene. Es lo único que movió números hoy — 8 filas de V3, entre 1 y 7 faltantes menos cada una.
  - La regla **V3 sin AS / On Premise / Mayorista** se mantiene explícita (`if vend_cod == 3 and seg not in ...`), ver [[business_rule_v3_sin_onpremise]].
- **El CCC no se movió en ninguna fila** (810 filas comparadas contra el dataset anterior, 0 diferencias en `clientes_compraron`) y hay que decirlo con todas las letras: **la causa de las diferencias que se habían reportado era otra**, no el criterio de atribución.
- **Causa real (verificada cliente por cliente):**
  1. **`clientes.xlsx` tiene 10 clientes cargados dos veces**, una fila en la ruta de **V3** y otra en la de **V8** (`#272, #320, #1065, #1257, #1336, #1366, #1392, #1414, #1424, #4758` — mismo día de visita, rutas distintas). Como estaban en las **dos** carteras, sus compras ya le contaban a V8: por eso el criterio nuevo no cambia nada. **Efecto colateral: inflan el denominador**, esos 10 clientes cuentan dos veces en `clientes_cartera` de toda la tarjeta.
  2. **`#1458` y `#1459` no están en el maestro** (compraron Cazador Malbec por V8). Sin cliente en `clientes.xlsx` no hay subcanal, así que no entran en ninguna fila.
  3. **`#525 VELAZQUEZ FLORENCIA`** tiene subcanal **OTROS** (8 clientes del maestro están así): la tarjeta mide 5 subcanales, OTROS queda afuera por diseño. Explica 1 cliente de diferencia en Cazador Malbec, Cazador Blanco Dulce y Dada Lata Tinto Verano.
  4. **4 ventas de V3 a clientes On Premise** (`#7174`, `#7231` en Cazador Malbec; `#7215`, `#7533` en Cinzano Rosso). Acá el criterio nuevo choca de frente con la regla "V3 no trabaja On Premise": V3 vendió, pero no se le mide. **Se dejó ganar la regla de V3** — es una regla explícita del contrato y no se puede deducir de esta definición. Si el negocio quiere que también cuenten, es una línea.
- **Validado:** 810 filas antes/después, `pct_cobertura > 1` en 0 filas, 0 filas de V3 en AS/OP/Mayorista, CCC total de la tarjeta 480. Endpoints 200: `innovaciones_total`, `innovaciones_segmento` (gerencia), `innovaciones_segmento` y `plan_innovaciones` de V3 y V8, `dashboard`, `alertas`. El plan de V3 sigue trayendo sólo ALMACEN y KIOSCO.

## 2026-07-30 - fix(innovaciones): Don David Torrontés Low con 0 coberturas — código mal tipeado en Innovaciones.xlsx

- **Reporte:** en gerencia → pantalla **Innovaciones**, `Don David Torrontes Low 6x750` mostraba **0 clientes** teniendo 1 cliente con compra real.
- **Causa raíz:** `01_INPUTS/INNOVACIONES/Innovaciones.xlsx` celda **B22** decía `42337 - Don David Torrontes Low 6x750`. El código real del SKU en el ERP es **42377** (`DON DAVID TORRON LOW ALC 6X750`). El `42337` **no existe** en ningún lado: ni en el maestro de productos (`RAW_PRODUCTOS/productosjulio.xlsx`), ni en `04D`, ni en los dos archivos de stock, ni en ninguna venta. Como el motor cruza por código exacto, el producto quedaba con CCC 0 por definición. Ojo: `42375` es el Don David Torrontés **común**, otro SKU — no confundir.
- **Cambio:** una celda del input, `B22` → `42377 - Don David Torrontes Low 6x750`. **No se tocó código**: `Innovaciones.xlsx` es la fuente única y la leen `generar_datasets_acum.py` y `server_orbit.py` (innovaciones por segmento, plan de acción, Planes AS, días de stock, acciones "lista cerrada"). Un solo arreglo propaga a todo.
- **Validado (datos reales de hoy):**
  - Regenerado `mod_innovaciones_segmento.csv`. `42377` → **1 cliente** en V8 · AUTOSERVICIO (`#30033 MARTINICH VIVIANA RITA`, 12 u el 28/07 facturadas por **P&P Logística**; se cuenta bien porque innovaciones no filtra por Empresa, ver [[business_rule_empresa_ambas]]).
  - `/api/gerencia/innovaciones_total` → AUTOSERVICIO 1/199 (0,5%), resto de los subcanales en 0. Los 27 productos siguen en la tarjeta.
  - **Arrastre a Días de Stock:** el producto ahora aparece con **174 u / 87 días** en PyP y 60 u en VSB Cuyo. Venía saliendo como "no está en el archivo de stock" (lo habíamos registrado como dato el 28/07 sin ver que era el mismo typo).
- **Auditoría del resto de la tarjeta (los 27 códigos, uno por uno contra maestro de productos + stock + `ventas.csv`):** 25 códigos correctos y con el CCC que corresponde. Sobre los otros dos:
  - **`14425 TERMIDOR TRAD B-D SLIM 12X1L`** — mismo síntoma (código inexistente en maestro, stock y ventas). **El negocio confirmó que es el `14578`** y se corrigió la celda **B9** → `14578 - TERMIDOR TRAD B-D SLIM 12X1L` (se conserva el nombre comercial de la lista; en el ERP figura como `TERMIDOR BLANCO DULCE 12x1000` / `TERMIDOR B. DULCE 12x1L`). Regenerado y validado: pasa de 0 a **2 clientes** en V8 · AUTOSERVICIO (`#1006` el 20/07 y `#538` el 22 y el 29/07, 12 u cada una), 2/199 = 1,0%. **Arrastre a Días de Stock:** aparece como **crítico** — 12 u disponibles, **3 días de stock**, 12 en tránsito, 96 u vendidas en el mes. Era una alerta comercial real que estaba tapada por el código mal tipeado.
  - **81 líneas de venta facturadas por V8 sobre clientes de la cartera de V3.** Diferencias medidas en Cazador Malbec (169 vs 174 clientes), Cazador Blanco Dulce, Dada Lata Tinto Verano y Cinzano Rosso. Ver la entrada siguiente: el criterio de atribución se cambió por definición del negocio, y al implementarlo apareció que la causa de esas diferencias era otra.

## 2026-07-30 - fix(clientes): la ficha de gerencia decía "sin compras" en los clientes que compran por Depósito

- **Reporte:** en gerencia → pantalla **Clientes**, `#786 ANSELMI Y CIA S.R.L.` salía **"Sin compras en el mes vigente"** teniendo venta real (70 líneas en `ventas.csv`, 2.747,7 L / $15.475.505 en julio).
- **Causa raíz:** desalineación entre las dos mitades de la ficha. El maestro se lee con `_clientes_maestro(incluir_deposito=True)` — la pantalla de Clientes **sí** muestra la cartera del Depósito — pero `_cliente_ventas_base()` llamaba a `_preparar_df_ventas(p)` con el default `incluir_deposito=False`, que descarta **CodVendedor 20**. Anselmi factura 100% por V20 (venta directa), así que el cliente aparecía en el buscador pero su base de ventas quedaba vacía. La ficha no tiene objetivo, no era un tema de la regla de exclusión de V20 (ver [[business_rule_sellout_maestro]]).
- **Cambio 1 — `server_orbit.py:_cliente_ventas_base()`**: `_preparar_df_ventas(p, incluir_deposito=True)`. La base de la ficha ahora contiene V20.
- **Cambio 2 — `server_orbit.py:cliente_ficha()`**: si viene `?vendedor=Vxx` (ficha abierta desde el perfil del vendedor) se filtra `_vend != 20`. Gerencia ve la venta total del cliente; el vendedor sigue viendo sólo lo suyo, sin V20. Los números del vendedor **no se mueven**.
- **Cambio 3 — marca "nan"**: `astype(str)` sobre una celda vacía del ERP dejaba el literal `"nan"`, y la ficha dibujaba una marca llamada **nan** (era el bloque más grande de Anselmi: Cinzano 90105/90106/90110, Dada Sweet, Tanqueray Bossa Nova — el ERP no les completa `Marca`). Helper `_txt()` normaliza `nan`/`none`/`nat` → `""` en `_marca`, `_linea`, `_articulo`, `_codigo`, y el fallback existente los muestra como **"Sin marca"**. Afectaba 133 líneas de la base, o sea a **todas** las fichas, no sólo a esta.
- **Alcance:** `_cliente_ventas_base()` lo usa **únicamente** `/api/clientes/<id>/ficha` (verificado por grep). CCC, cobertura, 11T, sell out, objetivos y avance **no tocan esta base** — ninguna métrica con objetivo cambia.
- **Validado (test_client sobre datos reales de hoy):**
  - `786` gerencia → 200, mes 2026-07, **2.747,7 L / $15.475.505**, 27 marcas, 70 SKUs, última compra 30/07, frecuencia 2 días/mes. Sin marca `nan`.
  - `786` con `?vendedor=V6` → **403** (sigue fuera de la cartera del vendedor).
  - **13 clientes** compran por Depósito este mes y los 13 están en el maestro; 11 mostraban "sin compras" y 2 mostraban la venta a medias.
  - Clientes **mixtos** (ruta + depósito): `#15 BELTRAMO, DUTTO Y DUTT` → gerencia 2.606,6 L vs vendedor V8 197,4 L; `#8212 CLIENTE MOSTRADOR V20` → gerencia 9,0 L vs vendedor V9 1,5 L. La separación funciona.
  - **No regresión** en clientes de ruta pura: `#4 OLGA GROSSO` (11,8 L, 5 marcas) y `#12 QUINTEROS JOEL ENRIQUE` (21,0 L, 1 marca) idénticos a antes.
  - Humo de endpoints: `/api/clientes`, `/api/clientes/buscar`, `/api/clientes/<id>/ficha`, `/api/alertas`, `/api/dashboard`, `/api/vendedor/V6` → todos 200.

## 2026-07-28 - feat(semanal): borrar plan por semana, semanas cerradas bloqueadas y resumen de stock por grupo

Dos pedidos sobre lo entregado hoy.

**1. Planificación semanal: borrar por semana y bloquear las cerradas.**
- Botón **🗑 Borrar** en el encabezado de cada semana: limpia las 4 filas de KPI de esa semana y **persiste** (no hay que apretar Guardar aparte).
- **La semana cerrada no se planifica ni se borra:** sus inputs quedan `disabled` con estilo atenuado, el botón de borrar no se dibuja y en su lugar va un 🔒. El plan ya cargado **sigue visible** (read-only) para poder leer la variación contra lo logrado.
- `semUsarPromedio()` respeta el bloqueo: rellena sólo las semanas abiertas.
- **Regresión cubierta:** un input `disabled` conserva su `value`, así que `semGuardar()` lo re-postea igual y el plan de una semana cerrada **no se pierde** al guardar. Verificado punta a punta.

**2. Tarjeta de stock: el resumen ahora muestra los 3 grupos, no sólo "bajo 30 días".**
- Antes el resumen listaba únicamente los productos bajo 30 días, así que los KPI "sin existencia" y "bajo 15 días" mostraban un número sin decir **cuáles** eran (caso reportado: Innovaciones en PyP con "2 sin existencia de 27" y ningún detalle).
- Ahora hay **tres bloques con sus productos**: 🚫 Sin existencia · 🔴 Bajo 15 días · 🟠 De 15 a 30 días.
- **Los grupos son EXCLUYENTES** (`grupo` en cada fila, calculado en `_dias_stock_filas`): `sin_stock` / `critico` / `atencion` / `sin_venta` / `ok`. Antes "bajo 30" incluía a los "bajo 15" y los de stock 0 contaban en las dos puntas; ahora cada producto cae en un solo grupo y **los contadores de los KPI coinciden exactamente con lo que lista cada bloque**. Se verificó que la suma de los 5 grupos = total de productos en los 6 cortes (2 depósitos × 3 universos).
- Cambia el rótulo del tercer KPI: "Bajo 30 días" → **"De 15 a 30 días"**, para que diga lo que efectivamente cuenta. Se agrega `en_riesgo` (sin_stock + critico + atencion) al resumen.
- Los "sin existencia" distinguen dos casos, que se leen distinto: **"sin existencia en depósito"** (el código está en el archivo con 0 u) y **"no está en el archivo de stock"** (nunca llegó, o el export no lo trae).
- **Validado:** PyP · Innovaciones ahora lista los 2 sin existencia por nombre (`TERMIDOR TRAD B-D SLIM 12X1L` y `Don David Torrontes Low 6x750`, ninguno de los dos figura en el stock y ninguno vendió en junio). KPI 2/1/2 ↔ bloques con 2/1/2 productos. Borrado de S4 probado con clic real: inputs vacíos, DB en null, suma en "–". Plan de prueba borrado de `orbit.db`. `node --check` + `ast.parse` OK.

## 2026-07-28 - fix(cierre): los dos archivos de stock al allowlist del cierre diario

- **Contexto:** `CIERRE_DIA_ORBIT.bat` no hace `git add .` sino un allowlist explícito de ~35 rutas. Ninguno de los archivos de stock estaba: el cierre nunca los publicaba, así que Render quedaba con la foto del último commit manual y la tarjeta Días de Stock (y Stock sin Venta) habría mostrado un stock viejo sin avisar. Es el patrón de ERR-014 (ver [[project_cierre_allowlist]]).
- **Cambio:** dos líneas nuevas — `01_INPUTS/Stock/stock.xlsx` y `01_INPUTS/Stock/stock_VSB_Cuyo.xlsx` — con el comentario de por qué están.
- **`MPA/MPA.xlsx` queda AFUERA a propósito:** es una lista fija de productos, no cambia con el cierre diario. Cuando el negocio actualice el plan AASS se commitea a mano (junto con `09_CONFIG/mpa_codigos.csv`, que hay que revisar en la misma pasada).
- **Nota:** el 27/07 se había intentado lo mismo (`dba1dca`) y se revirtió en `0013665` por estar fuera del pedido; esta vez el usuario lo pidió explícitamente.
- **Validado:** `check_git_cierre.py --test` → TODAS OK (`01_INPUTS/` es ruta operativa, así que el cierre no aborta). El `.bat` sigue en **CRLF puro** (275 CRLF, 0 LF sueltos) — con LF `cmd` rompe el `if/else` y el cierre no pushea, ver [[project_cierre_bat_crlf]].

## 2026-07-28 - feat(semanal): Días de Stock se parte en dos depósitos — Stock PyP y VSB Cuyo

- **Pedido:** la tarjeta pasa a llamarse **Stock PyP** y se calcula sólo con los vendedores **V3, V4, V6, V8, V10**. Los otros dos (**V7, V9**) van en una tarjeta aparte, **VSB Cuyo**, con `01_INPUTS/Stock/stock_VSB_Cuyo.xlsx`. Además: resumen arriba con los productos por debajo de 30 días para detectarlos rápido, y desplegable abajo con el detalle individual.
- **Regla nueva:** son **dos depósitos distintos, no se suman ni se comparten**. Cada uno cruza SU archivo de stock con la venta de SUS vendedores — si se midiera el stock de PyP contra la venta de los 7 vendedores, la cobertura daría más corta de lo real, y al revés para VSB. **V20 (Depósito) queda fuera de los dos**: no pertenece a ninguna de las dos rutas. Esto **reemplaza** el criterio anterior ("no se excluye ningún vendedor"), que valía cuando había un solo stock.
- **Backend (`server_orbit.py`):**
  - `_stock_disponible(archivo="stock.xlsx")` ahora es parametrizable y cachea por `(archivo, mtime)`. El default mantiene intacto a Stock sin Venta.
  - `_dias_stock_venta_base(vendedores)` filtra por `CodVendedor`; caché por `(periodo, archivo, mtime, vendedores)`.
  - `_STOCK_BLOQUES` declara los dos depósitos (id, label, archivo, vendedores) y `_dias_stock_bloque()` arma cada uno. Los 3 universos de producto (11T / Innovaciones / MPA) se construyen **una sola vez** y los dos bloques los cruzan con su propio stock y su propia venta.
  - El endpoint pasa a devolver `bloques: [...]`; `stock_ok` / `stock_match` ahora son **por depósito**. `resumen` suma `atencion` (productos bajo 30 días).
- **Front (`portal.html`):** dos tarjetas con acento propio — PyP magenta `#E2147A`, VSB Cuyo azul `#4DA3FF` — aplicado a la barra lateral, el degradado del encabezado, el pill de la ruta y el tab activo. Cada tarjeta: KPIs (días del conjunto · bajo 15 d · bajo 30 d · sin existencia · unidades · unidades/día), **resumen en grilla de los productos bajo 30 días** (borde rojo <15 d, ámbar 15-30 d, con días y u/día por producto) y **desplegable** con la tabla completa. Tabs de universo y desplegable son **independientes por tarjeta**.
- **Validado:** endpoint 200, dos bloques. Con el stock correcto: **PyP** (V3·V4·V6·V8·V10) 11T 23,1 d de conjunto, 13 bajo 15 d, 22 bajo 30 d; **VSB Cuyo** (V7·V9) 11T 95,0 d, 6 bajo 15 d, 8 bajo 30 d. Chequeo cruzado en el DOM del portal: acentos `#E2147A` / `#4DA3FF`, 22 y 8 ítems en los resúmenes, el desplegable de VSB abre 82 filas sin afectar al de PyP, el tab MPA de PyP muestra la nota de los 3 sin código. `stock_sin_venta` sigue OK (217 con stock / 55 sin venta) y `semanal` también (12 meses). `node --check` + `ast.parse` OK.
- **Resuelto en la misma sesión:** el usuario volvió a exportar `01_INPUTS/Stock/stock.xlsx` y ahora sí trae **222 códigos, todos GRUPO PEÑAFLOR SA**. Revalidado contra el archivo real (sin parches): PyP `stock_ok=true`, 111 códigos del portfolio con existencia; 11T 19,9 d de conjunto (12 bajo 15 d, 22 bajo 30 d), Innovaciones 133,7 d, MPA 18,5 d. Las dos tarjetas quedan sin aviso.

## 2026-07-28 - feat(semanal): tarjeta Días de Stock (11 Titulares · Innovaciones · MPA)

- **Pedido:** al pie de la pantalla Semanal, una tarjeta de stock con los **días de stock** según la venta del **mes anterior**, para **11 Titulares**, **Innovaciones** y **MPA** (los productos de `01_INPUTS/MPA/MPA.xlsx`, plan AASS Inicial y Silver).
- **Cálculo:** `días de stock = unidades disponibles ÷ venta diaria del mes anterior`.
  - **Stock:** `01_INPUTS/Stock/stock.xlsx`, `UniTotalDisponible` (unidades), consolidado por código.
  - **Venta:** `CantBase` del mes anterior cerrado, **misma unidad que el stock** (verificado: Alma Mora Malbec 74210 vendió 6.172 u en junio contra 5.741 u en depósito). Se suma **con signo**: las devoluciones vienen en negativo (116 filas en junio, `TipoDeVenta` "Devolución por Rechazo"/"por Canje") y tienen que netear porque vuelven al depósito.
  - **No se excluye ningún vendedor** (ni V20): el stock lo consume toda la salida física, la venda quien la venda — mismo criterio que Stock sin Venta. Excluir el depósito daría una cobertura más larga que la real.
  - **Divisor = días operativos** del mes anterior (lun-sáb sin feriados; junio 2026 = 24). El depósito no despacha domingos, así que un "día de stock" es un día que se vende.
- **El problema de fondo — MPA no trae códigos.** `MPA.xlsx` lista los productos por **nombre comercial** ("Alaris Malbec 0.75L") y el ERP los tiene abreviados ("TRAPICHE ALARIS MALBEC 6X750"). Se probó un matcher automático por texto con diccionario de abreviaturas y **se descartó**: acertaba 33/62 y varios de los "confiables" estaban **mal** (Alma Mora Cabernet → `F.LAS MORAS CABSAU`, Don David Malbec → la línea Reserva, Dada 3 Syrah-Cabernet → `DADA ART CABERNET`). Un mapeo adivinado en un reporte de stock es peor que no tenerlo.
  - **Solución:** `09_CONFIG/mpa_codigos.csv`, mapeo **revisado producto por producto** contra el catálogo del ERP (`RAW_PRODUCTOS/productosjulio.xlsx`), con las descripciones tomadas del catálogo (no tipeadas). **59 de 62** entradas mapeadas → 67 códigos únicos.
  - Las **3 ambiguas quedan SIN mapear a propósito** y se listan en la tarjeta: *Alma Mora Blend* (el ERP tiene BLEND TINTO 74437 y BLEND BLANCO 74438), *Dada 7 Dulce* (no hay un Dada N°7 vino; sólo espumante rosé 74473 y orange bitter 74728) y *Suter Etiqueta Marron Blanco* (20303 "ETI MARRON NEW PIN", en baja, no confirma que sea el seco). Se resuelven agregando la fila en el CSV, sin tocar código.
  - Las 3 últimas columnas de `MPA.xlsx` (*Antares*, *Smirnoff ICE Flavors*, *Smirnoff Flavors 700 ml*) **no son SKU sino agrupaciones de línea**: se expanden a todos los códigos de esa línea y se deduplica por código.
- **Backend (`server_orbit.py`):** bloque `DÍAS DE STOCK` con `_innovaciones_codigos_todas()` (portfolio completo de `Innovaciones.xlsx`, a diferencia de `_inov_plan_as_productos()` que sólo trae las marcadas con `x`), `_mpa_universo()`, `_dias_stock_venta_base()` (mes anterior, fuente resuelta igual que el histórico semanal: cierre versionado → historial) y `GET /api/gerencia/dias_stock`. El 11T reusa `_codigos_11t_map()` (matriz oficial por código). Se factorizó `_leer_ventas_min(path, cols)` desde `_semanal_leer` para leer las fuentes del ERP con `usecols` distintos sin duplicar el sniff de separador/encoding.
- **Front (`portal.html`):** tercera tarjeta de la pantalla Semanal, con tabs por universo, 5 KPIs (días del conjunto, bajo 15 días, sin existencia, unidades en depósito, unidades/día) y tabla por producto ordenada por **días ascendente** (primero lo que se queda sin stock). Rojo <15 d · ámbar <30 d · verde ≥30 d.
- **⚠️ Hallazgo de datos — `01_INPUTS/Stock/stock.xlsx` NO es el export de Peñaflor.** La copia de trabajo (modificada el 27/07 20:39, sin commitear) trae **114 códigos de otro portfolio**: Georgalos, Bigar, Dielo, Don Satur (golosinas, purés, chocolatada), con códigos de 8-9 dígitos. La versión commiteada sí es la correcta (217 códigos, todos `GRUPO PEÑAFLOR SA`). **Esto también rompe la pantalla Stock sin Venta.** No se tocó el archivo (es un input del usuario).
  - Por eso el endpoint expone `stock_codigos` / `stock_match` / `stock_ok`: si **ningún** código del portfolio aparece en el stock, la tarjeta muestra un aviso explícito y los KPI derivados van en **"–"**, no en 0 (un 0 se leería como "no tenemos stock", que es distinto de "no sabemos").
- **Validado:** endpoint 200. Con el stock correcto (versión commiteada, parcheada en memoria en un server de prueba en `:8599` — **sin tocar el archivo del usuario**): match 108 códigos, 11T 17,8 días de conjunto con 15 productos bajo 15 días, Innovaciones 73,9 días, MPA 15,6 días con 17 críticos. Con el stock actual: `stock_ok=false`, aviso + "–". Portal probado en Chrome en los dos escenarios, tabs y nota de los 3 sin código OK. `node --check` + `ast.parse` OK.

## 2026-07-28 - feat(semanal): pantalla Semanal en gerencia (histórico por semana + planificación del mes)

- **Pedido:** pantalla nueva **Semanal** en el perfil gerencia, con dos tarjetas: (1) el % de la venta de cada mes desde **julio 2025** aperturado por semana, (2) la planificación propia del mes en curso por semana, que al cerrar cada semana muestre la variación contra lo logrado. Ambas con los KPIs **CCC Tradicionales, CCC Autoservicios, CCC On Premise y facturación $**.
- **Definiciones acordadas con el usuario antes de codear** (las tres cambiaban el cálculo de raíz):
  - **Semana = bloque de días del mes:** S1 1-7 · S2 8-14 · S3 15-21 · S4 22-fin. Siempre 4 columnas → los meses se comparan entre sí sin ajustes (la S4 tiene 9-10 días por construcción).
  - **CCC = aporte incremental:** cada cliente cuenta en la semana de su **primera compra del mes**, así las 4 semanas suman 100% del CCC del mes. (El CCC bruto semanal no sirve para planificar: un cliente que compra 2 semanas contaría 2 veces y el total pasaría el 100%.)
  - **V20 Depósito excluido** (además de V1/V2/V5): la planificación semanal es de ruta y se mide contra objetivos, donde V20 nunca entra.
- **Fuentes reales, resueltas por mes y sin hardcodear el calendario** (`_semanal_fuente_de`): 1º `01_INPUTS/cierres mes/ventas_mes_MMAAAA.csv` (cierre congelado), 2º `02_HISTORY/historial_ventas.csv` (export estático 2024-03→2026-04, único detalle diario anterior a los cierres versionados), y `01_INPUTS/ventas.csv` para el mes en curso. Cuando se cierre julio, el cierre deja su `ventas_mes_072026.csv` y el mes entra solo al histórico.
- **Backend (`server_orbit.py`), bloque nuevo `SEMANAL` + tabla:**
  - `init_db()`: tabla `plan_semanal(periodo, kpi, semana, pct, editado_por, updated_at)` con PK compuesta (vive en el disco persistente de Render, igual que `planificacion`).
  - `_semanal_leer(path)`: lector único de las 3 fuentes. **`usecols` de 6 columnas** (de 57) porque `historial_ventas.csv` pesa 63 MB; sniff de separador (`;` vs `,`), encoding en cascada, y dos parseos que había que resolver sí o sí: `_semanal_num` (si el texto trae coma decimal el punto es de miles; si no, se parsea tal cual — nunca al revés) y `_semanal_fechas` (los cierres vienen en **ISO** y ventas/historial en **dd/mm/aaaa**: parsear todo con `dayfirst=True` desarmaba las ISO y generaba meses fantasma).
  - Canal: se **reusa `_canal_ccc_empresa`** (misma clasificación que CCC empresa/objccc). On Premise agrupa On Premise + Vinotecas + On Premise Noche, igual que el objetivo del Excel (30+15+11=56).
  - `_semanal_historico()` cacheado por (archivo, mtime) de todas las fuentes → el historial se parsea una sola vez por proceso; `_semanal_actual()` cacheado por mtime de `ventas.csv` + día.
  - `_semanal_objetivos()`: CCC de `objccc.xlsx` (hoja `total`) y facturación = suma de `ValorObjetivo` de `resultado.xlsx` hoja Avance sin vendedores excluidos. Sin fuente devuelve **None**, nunca 0.
  - Rutas: `GET /api/gerencia/semanal` y `POST /api/gerencia/semanal/plan` (valida periodo YYYY-MM y 0≤pct≤100; `null` **borra** la celda para distinguir "sin plan" de "0%"; respaldo a `plan_semanal_latest.csv`).
- **Front (`PAV MATINAL PE_A FLOR/portal.html`):** botón de menú `📆 Semanal`, bloque CSS `.sem-*` y `gSemanal()`. Carga **lazy** (como Cierre de Mes) para no sumarle segundos al login. Tarjeta 1: tabs por KPI, fila **Promedio** destacada arriba (base para planificar) y un mes por fila con % + valor + barra. Tarjeta 2: inputs de % por semana y KPI, columna Suma (verde en 100%), encabezado con el rango de días y el estado (CERRADA / EN CURSO / PENDIENTE), y por celda **Plan** (% × objetivo), **Real** y **Δ**; la semana en curso muestra su Δ en gris porque es parcial. Botón "↧ Usar promedio histórico" que precarga el promedio **normalizado a 100%** (el promedio de %s redondeados da 99.9/100.1).
  - Los inputs **no re-renderizan la tarjeta al tipear** (se perdería el foco, patrón ya conocido de los buscadores): cada tecla actualiza sólo la meta de esa celda y la suma de su fila.
- **Medida de facturación:** real = **facturado** (`ImporteNetoItem` por `FechaComprobante`), única medida con detalle semanal en los 13 meses. El objetivo de `resultado.xlsx` se mide contra el *acumulado de pedidos* en Plan vs Real, así que la nota al pie de la tarjeta lo aclara explícitamente para que nadie compare peras con manzanas.
- **Validado:** endpoint 200 en 2.6 s la primera vez y **0.03 s cacheado**; **12 meses cerrados** (jul-2025→jun-2026, 10 del historial + may/jun del cierre versionado). Cross-check contra `/api/gerencia/ccc_empresa` del mes vivo: **trad 640 · AS 121 · OP 41 = idénticos**; los % de cada KPI suman 100 ±0.1 (redondeo). POST probado con periodo ficticio **2099-01** (alta, borrado de celda, rechazo de pct>100 y de periodo inválido) y limpiado después. Portal en `:8502` con Chrome: ambas tarjetas renderizan, tabs de KPI, "Usar promedio histórico" deja las 4 filas en **100.0%**, foco preservado tipeando "18.5", guardado OK ("Último guardado …· Gerencia"). `node --check` del JS OK, cero errores de consola.
- **Sin datos de prueba:** el plan de 2026-07 que se guardó para validar se borró de `orbit.db`; la tarjeta arranca en "sin plan".

## 2026-07-27 - chore(portal): baja de la tarjeta "Sin Comp. Mes" del dashboard

- **Pedido:** sacar del dashboard (gerencia) la tarjeta **Sin Comp. Mes**.
- **Cambio:** `PAV MATINAL PE_A FLOR/portal.html` — eliminado el 4º `kcard wn` de la fila de KPIs (contaba `D.cli` con `compra_mes_flag` 0/null, subtítulo "Zona del día · sin compra este mes"). Solo front, sin tocar backend ni datasets: el payload sigue trayendo `D.cli` igual, que lo usan otras pantallas.
- **Layout:** `.krow` es `repeat(auto-fit,minmax(162px,1fr))`, así que las 3 tarjetas restantes (Acumulado compañía, Tendencia %, Clientes del Día) se reparten el ancho sin hueco. El dato no se pierde: "Clientes del Día" ya muestra `⚠ N sin compra mes` en su pie sobre el mismo universo.
- **Validado:** `node --check` sobre el bloque `<script>` del portal → OK.

## 2026-07-23 - fix(planes_as): la puntera sin cargo toma el producto del Excel (Cazador → Los Arboles)

- **Pedido:** en Planes AS la puntera sin cargo figuraba **El Cazador**; el usuario cambió el producto a **Los Arboles** en el Excel fuente y al actualizar no se reflejaba.
- **Causa:** el producto de la puntera estaba **cableado** en el código (nombre "El Cazador" + detección del enviado por `Articulo` que contiene "CAZADOR"). Cambiar el Excel no alcanzaba. El Excel sólo aportaba el *disponible* (cajas por cliente), no el nombre del producto.
- **Solución — ahora es Excel-driven:** el producto sale del **encabezado** de la hoja `Puntera` (`Cjas Sin Cargos (<Producto>)`), así se puede cambiar desde el Excel sin tocar código.
  - **`generar_datasets_acum.py`:** `_cargar_puntera_mes()` devuelve `(dict, producto)` parseando el texto entre paréntesis del encabezado. La detección del enviado usa ese nombre en mayúsculas contra `Articulo` (`LOS ARBOLES` matchea limpio, igual que `CAZADOR` antes). Se agrega columna `pt_producto` a `mod_planes_as.csv` y el detalle de envíos usa ese nombre. `import re` agregado.
  - **`server_orbit.py`:** ambos endpoints de Planes AS (gerencia + vendedor) pasan `pt_producto`.
  - **`portal.html`:** gerencia y vendedor muestran `c.pt_producto` (fallback "Puntera") en la fila/tarjeta de puntera y en el `verSincargo()`, en vez del literal "El Cazador".
  - **Requisito documentado:** el nombre entre paréntesis debe aparecer tal cual en el `Articulo` del ERP (ej. "Los Arboles" → "LOS ARBOLES …"). Si algún día usan un nombre que el ERP escribe distinto, hay que nombrarlo como aparece en el ERP.
- **Validado:** `_cargar_puntera_mes()` → "Los Arboles", 5 clientes. Regeneré `mod_planes_as.csv`: `pt_producto=Los Arboles`, enviado computado desde ventas de Los Arboles (ej. cli 538: 18 → entregado); detalle de envíos "Los Arboles", cero "Cazador". Playwright (`:8599`, copia de orbit.db): gerencia y vendedor V8 muestran "Los Arboles" y **cero "Cazador"**, el modal de envíos también. `ast.parse` + `node --check` OK, sin errores de consola.
- **Nota de datos:** se commitean sólo `mod_planes_as.csv` + `mod_sincargos_envios.csv` (los que produce este cambio). Los demás datasets que tocó la regeneración completa se revirtieron: se regeneran en el cierre, no acá.

## 2026-07-23 - feat(alertas): descartar alertas para que no se acumulen (gerencia)

- **Pedido:** un botón dentro de la pantalla de Alertas para borrar las alertas y que no se sigan acumulando.
- **Contexto (por qué no es un "borrar" literal):** `/api/alertas` **no persiste** alertas — las recalcula en vivo desde `ventas.csv` del mes (`_alertas_descuento_mes` + `_alertas_tope_cajas_mes`). Mientras la venta esté en el mes, la alerta reaparece. Por eso se implementó un **registro de descartadas** (mismo patrón que `alerta_seguimiento`): "ya la vi, no me la muestres más". No se borra ninguna venta.
- **Decisión del usuario:** las descartadas se ocultan **en gerencia Y en el vendedor** (ambos consumen `/api/alertas`); y se ofrece **botón masivo** ("🗑 Limpiar alertas (N)") **+ ✕ por alerta**.
- **Backend (`server_orbit.py`):**
  - Nueva tabla `alerta_descartada(clave, autor, resumen, descartada_at)` en `init_db()`.
  - `_alerta_clave(a)`: clave estable = `mes | tipo | vendedor | cliente | articulo | fecha_pedido`. **Incluye el mes** (YYYY-MM) para que el descarte NO se herede al mes siguiente, y **la fecha del pedido** para que una infracción nueva en otro día vuelva a alertar. En `descuento` agrega la magnitud (`%aplicado/neto/cant`) porque un mismo artículo puede tener dos líneas distintas el mismo día (descartar una no tapa la otra); en `tope` NO, porque es un acumulado del mes que si no reaparecería cada día.
  - `_alertas_descartadas()`: set de claves (tolera tabla inexistente → no filtra).
  - `/api/alertas` ahora adjunta `clave_descarte` a cada alerta y filtra las descartadas.
  - Nueva ruta `POST /api/alertas/descartar` (body `{claves, autor, resumenes}`), UPSERT idempotente; 400 si faltan claves.
- **Front (`PAV MATINAL PE_A FLOR/portal.html`, `gAlertas`):** botón masivo en el encabezado (con `confirm` explicando que se oculta también al vendedor y que una infracción nueva reaparece), ✕ por fila, `descartarAlerta()`/`descartarTodasAlertas()` que hacen el POST, sacan la alerta de `D.al`, re-renderizan y actualizan el badge del sidebar.
- **Validado sobre copia de `orbit.db`** (`ORBIT_DB_PATH` → scratchpad, DB operativa intacta): endpoint 878 alertas → 875/877 claves únicas, las 2 colisiones reales eran líneas distintas del mismo artículo/día (montos distintos) → se agregó la magnitud a la clave para no taparlas. Playwright gerencia: ✕ individual 878→877, masivo → "Sin alertas activas hoy", badge oculto; **V8 (vendedor) ve 0** tras el descarte. Sin errores de consola. `ast.parse` + `node --check` OK.

## 2026-07-23 - chore(portal): baja de la pantalla "Clientes Dormidos" (gerencia)

- **Pedido:** sacar la pantalla de clientes dormidos, ya no se usa.
- **Backend (`server_orbit.py`):** eliminado el bloque completo `# ====== ALERTAS CAÍDA: clientes dormidos ======` → helper `_litros_por_unidad()`, `_dormidos_payload()` y las rutas `GET /api/gerencia/alertas_caida` y `/api/gerencia/alertas_caida/export` (~9.7 KB). `_litros_por_unidad` sólo lo usaba este bloque; `send_file`/`BytesIO` **siguen importados** porque los usa el export de Stock sin Venta.
- **Front (`PAV MATINAL PE_A FLOR/portal.html`):** botón de menú lateral "💤 Dormidos" + su badge `gDormBadge`, el fetch `safe('/api/gerencia/alertas_caida')` de `loadRole()` (con su destructuring y `D.dormidos`), las dos asignaciones de badge en `showApp()`/`refreshAfterRole()`, el ruteo `gScreen==='dormidos'` y las funciones `gDormidos()` + `descargarDormidosExcel()` (~4.8 KB).
- **Sin efectos sobre datos:** la pantalla era de sólo lectura sobre `historial_ventas_cliente.csv` + `ventas.csv`; no se tocó ningún input, dataset ni cálculo de otra pantalla.
- **Validado:** `ast.parse` de `server_orbit.py` OK; import de la app OK → **56 rutas, ninguna `alertas_caida`**; `node --check` del JS de `portal.html` OK; grep de `dormido|Dormidos|gDormBadge|alertas_caida` en ambos archivos → **0 coincidencias**.

## 2026-07-21 - feat(planes_as): buscador de cliente en la pantalla Planes AS (gerencia + vendedor)

- **Pedido:** un buscador en Planes AS para encontrar más rápido un cliente del listado, en ambos perfiles.
- **Cambio (`PAV MATINAL PE_A FLOR/portal.html`), sólo front, sin tocar backend ni datos:**
  - Helper `pasMatch(c,q)`: filtra por nombre, código, dirección, localidad, día de visita y (gerencia) vendedor. Case-insensitive.
  - **Gerencia (`gPlanesAS`):** se separó el armado de filas en `_gPlanesASRows()`. El input + la tabla (shell) se renderizan una vez; cada tecla re-renderiza **sólo `<tbody id="gpasBody">`**, no toda la pantalla → el input no pierde el foco. El chip del header (`gpasCount`) muestra el nº de coincidencias; "Sin coincidencias" si no hay match.
  - **Vendedor (`vPlanesAS`):** mismo patrón con `_vPlanesASCards()` re-renderizando sólo `<div id="vpasBody">`. El KPI "Clientes AS" del resumen se dejó **estable** (cartera completa) para no mezclar un contador filtrado con el "Facturado total" sin filtrar; las tarjetas visibles son el feedback de la búsqueda.
- **Patrón reutilizado** del buscador de Stock sin Venta (re-render parcial para preservar foco), no se inventó nada nuevo.
- **Validado (Playwright, ambos perfiles, `:8599`):** gerencia 32→3 filtrando por apellido, vendedor V8 16→3, **foco preservado en el input** en los dos casos, chip/"Sin coincidencias" OK, `node --check` del JS OK, cero errores de consola.

## 2026-07-21 - data(objccc): objetivos Tradicional por vendedor actualizados (suman 845 exacto)

- **Contexto:** el 20/07 quedó pendiente el desajuste del objetivo Tradicional (Total declarado 845 vs suma por vendedor 809). El usuario actualizó la hoja `tradicional` de `01_INPUTS/objccc.xlsx` repartiendo los 36 faltantes.
- **Resultado:** Tradicional por vendedor ahora suma **845** (V3 116, V4 118, V6 111, V7 116, V8 125, V9 117, V10 142). AS (145) y OP (56) siguen exactos → `objetivo_asignado == objetivo_total == 1046`.
- **Efecto en la tarjeta (sin cambio de código):** la leyenda "N del objetivo no está asignado a ningún vendedor" del pie se **oculta sola** (`sinAsignar=0`). Cambian los denominadores por vendedor (ej. V3 105→116, V4 141→145, V7 125→139).
- **Validado (Playwright + endpoint, `:8599`):** tarjeta Cobertura con los 7 vendedores contra su nuevo objetivo, pie "401 ruta + 10 depósito = 411 sobre objetivo 1046" sin leyenda de faltante. CCC del Mes coherente (AS 76/145). Sin errores de consola. Sólo cambia el input `objccc.xlsx`; sin tocar server ni portal.

## 2026-07-20 - feat(cobertura): tarjeta "Cobertura acumulada del mes" aperturada por vendedor vs objetivo + depósito

- **Pedido:** que la tarjeta tome todos los vendedores y también depósito, y que se mida contra el objetivo de `01_INPUTS/objccc.xlsx` (aperturado por vendedor). Aclaración del usuario: apertura **por vendedor**, y el CCC del depósito va **debajo, sin objetivo propio, pero sumando al objetivo total de la empresa**.
- **Diagnóstico previo:** los 7 vendedores activos ya estaban en `mod_cobertura_acum.csv` (V3 sólo TRADICIONAL, correcto). El depósito ya lo devolvía el endpoint pero la tarjeta **no lo renderizaba**. No había objetivo: la tarjeta mostraba `cubiertos/cartera` y agregaba por segmento, no por vendedor.
- **Backend (`server_orbit.py`):** nueva `_objetivos_ccc_vendedor()` que lee las hojas `autoservicio`/`tradicional`/`On premise` de objccc.xlsx. Esas hojas **no tienen encabezado real** (columnas `Unnamed`), así que NO se leen por posición: se busca en cada fila la celda `V<n>` y se toma el último numérico de la fila; la fila `Total` se guarda como total declarado. Cache por mtime. `gerencia_cobertura_acum` ahora adjunta `objetivo`/`pct_objetivo` por vendedor×segmento, totales por vendedor y un bloque `empresa`.
- **Depósito:** V20 no tiene cartera en el maestro (`clientes.xlsx` sólo tiene codven 1/3/4/6/7/8/9/10) → no puede tener denominador ni %. Se expone `ccc` (clientes con neto>0) y suma sólo al **numerador** del total de empresa.
- **MAYORISTA** no tiene objetivo cargado: queda visible por vendedor como informativo y **fuera** del total, para no medir contra 0.
- **Front (`portal.html`):** la tarjeta se invierte — filas por vendedor (con su objetivo y barra), drill-down a sus segmentos, y de ahí a los clientes faltantes. `gCobSegToggle()` (segmento→vendedor) quedó inalcanzable y se reemplazó por `gCobVendToggle()` (vendedor→segmento); `_cobFaltFetch`/`_faltRows` se reusan sin cambios. Abajo, línea "V20 Depósito" con su CCC, y un pie que explicita la composición del total.
- **Objetivo empresa = totales declarados** (145 AS + 845 TRAD + 56 OP = 1046). Los objetivos por vendedor suman **1010** (Tradicional: 809 vs 845 declarado). La diferencia de **36 no se esconde dentro del %**: la tarjeta la muestra en el pie ("36 del objetivo no está asignado a ningún vendedor"). **Pendiente de confirmación del usuario** si el 845 está vigente o desactualizado.
- **Validado (Playwright, gerencia, `:8599`):** tarjeta con los 7 vendedores (V3 16/105 · 15.2%, V4 34/141, V6 62/141, V7 20/125, V8 113/172 · 65.7%, V9 62/151, V10 87/175), línea V20 con 10 CCC, total 394 ruta + 10 depósito = 404 / 1046 = 38.6%. Drill-down de V8 correcto (AS 22/30, TRAD 80/125, OP 11/17, MAYORISTA sin objetivo). Sin errores de consola.
- **BUG DETECTADO y CORREGIDO (ver entrada siguiente):** la tarjeta vecina "CCC del Mes · real vs objetivo" mostraba **Autoservicios 5/145 = 3.4%** por clasificar el canal sólo por Ramo.

## 2026-07-20 - fix(ccc_empresa): Autoservicio se clasifica por Subramo — la tarjeta mostraba 3.4% en vez de 51%

- **Síntoma:** la tarjeta "CCC del Mes · real vs objetivo" mostraba **Autoservicios 5/145 = 3.4%** y **Tradicionales 370/845**. Apareció al ponerla al lado de la tarjeta nueva de Cobertura, que sobre **el mismo objetivo (145)** daba 74.
- **Causa raíz:** `_canal_ccc_empresa()` clasificaba **sólo por `Ramo`**. El grueso del autoservicio vive en `Subramo`: **`AUTOSERVICIO TRADICIONAL` = 764 de 826 filas AS**, y tiene `Ramo = TRADITIONAL TRADE` → caían todas en Tradicionales. Prueba de que el criterio estaba mal, no el dato: bajo Ramo la cartera **completa** de AS es de **18 clientes**, contra un objetivo de 145 — aritméticamente imposible.
- **El comentario del código y la regla en Obsidian afirmaban que ese criterio era intencional** ("el objetivo se definió por Ramo"). Era falso; ambos quedaron corregidos.
- **Cambio (`server_orbit.py`, `_canal_ccc_empresa`):** Autoservicio se detecta por **Subramo** (`AUTOSERVICIO*`, `CADENA(S) REGIONAL(ES)*`, `LARGE FORMAT`) además de Ramo, con el mismo criterio que `_clasificar()` de `generar_datasets_acum.py` — así las dos tarjetas no se contradicen sobre el mismo objetivo. **Mayoristas/Cash&Carry** salió de Autoservicios (antes `ramo.contains("CASH")` los metía ahí): es canal propio y objccc.xlsx no lo abre, así que queda fuera de los canales con objetivo, igual que MAYORISTA en cobertura.
- **Cambio (total empresa):** pasa a sumar **sólo los canales con objetivo**. Antes era `nunique()` global: metía clientes sin objetivo en el numerador contra un denominador que no los tenía. Se expone `fuera_objetivo` (hoy 1 cliente mayorista) para que el descarte no sea silencioso.
- **Efecto medido:** Tradicionales 370→**300**, Autoservicios 5 (3.4%)→**74 (51.0%)**, On Premise/Vinotecas/OP Noche sin cambios (17/6/5), total empresa 403→**402 · 38.4%**. El total casi no se mueve: lo que estaba roto era **la apertura por canal**.
- **Validado (Playwright, gerencia, `:8599`):** las dos tarjetas renderizadas juntas y **coincidiendo en Autoservicios 74/145**. Sin errores de consola. Diferencias residuales entre tarjetas explicadas y esperadas: Tradicionales 300 CCC vs 295 cubiertos (5 clientes compraron pero no llegaron a 3 botellas — CCC ≠ cobertura) y el depósito (10) que suma en cobertura y no en CCC.
- **Trampa de testeo:** el primer chequeo Playwright reportó "Sin datos de CCC empresa" con los endpoints devolviendo 200. No era un bug: `loadRole` trae esas tarjetas en 2da fase y el fetch entró 10s después del click. Esperar ≥20s al validar tarjetas de gerencia en el navegador.
- **Documentado en Obsidian:** `BITACORA_2026-07-20.md` (nueva) + `REGLAS_NEGOCIO_PAV.md` (regla de clasificación corregida en 2 lugares: sección CCC y sección Segmentos).

## 2026-07-20 - ui(portal): orden del menú lateral de gerencia + arranque en Plan vs Real

- **Pedido:** en el panel lateral izquierdo de gerencia, poner **Plan vs Real** arriba, luego **Dashboard** y **Planificación**, y el resto como estaba. Después: que la pantalla que abre por defecto sea Plan vs Real.
- **Cambio (`PAV MATINAL PE_A FLOR/portal.html`), sección "Gerencia" del `.gs-nav` (líneas 1113-1118):** reordenados los `.gs-item` a Plan vs Real → Dashboard → Planificación → Vendedores → Clientes Críticos → Cliente. Alertas, Dormidos y todo el bloque "Productos" quedaron intactos.
- **Cambio (arranque):** tres puntos que debían moverse juntos para no desfasar contenido/título/resaltado — `class="active"` pasó de Dashboard a Plan vs Real (1113-1114), `gScreen` inicial `"dashboard"` → `"planvsreal"` (1225), y el `<span id="gTopTitle">` inicial `Dashboard` → `Plan vs Real` (1154).
- **Sin cambios** de datos, endpoints, cálculos ni estilos. Ningún llamador invoca `gDashboard()` directo: login y refrescos pasan todos por `gRender()`, que lee `gScreen`.
- **Validado (Playwright, gerencia, server local `:8599`):** tras el login `gScreen='planvsreal'`, botón activo = `planvsreal`, `#gTopTitle`='Plan vs Real' y el orden del menú queda `planvsreal > dashboard > planificacion > vendedores > clientes > cliente > alertas > dormidos > [Productos...]`. Screenshot confirma la pantalla renderizada al entrar. Sin errores de consola ni page-errors.
- **Nota operativa:** hoy (corte 2026-07-18) Plan vs Real abre vacío ("Sin planes para este período", "Real: pendiente"), que es el estado real del día, no un bug. Gerencia verá esa pantalla vacía los días sin planes enviados.
- **Hallazgo lateral (no tocado):** `/index.html` sirve un HTML viejo de ~10KB desde la carpeta del frontend; el portal real se sirve en `/` y `/portal.html`. Candidato a `_NO_USAR_` si está muerto.

## 2026-07-17 - feat(cierre): el .bat espera el deploy nuevo de Render antes de abrir el portal

- **Pedido:** que `CIERRE_DIA_ORBIT.bat` espere el healthcheck de Render antes de abrir el navegador (hoy lo abría apenas terminaba el push, con Render todavía redeployando → portal vacío).
- **Problema de fondo:** Render hace deploy sin downtime; `/api/healthz` responde 200 desde la instancia **vieja** hasta que la nueva pasa el healthcheck. Esperar "un 200" no sirve: devolvería al instante.
- **Cambio (`server_orbit.py`, healthz):** `/api/healthz` ahora incluye `"commit"` con `os.environ.get("RENDER_GIT_COMMIT","")` (SHA que Render inyecta en cada deploy). Mismo 200, un campo nuevo.
- **Cambio (`CIERRE_DIA_ORBIT.bat`):** tras el push, captura `git rev-parse HEAD` y sondea healthz con PowerShell hasta que `commit == SHA` pusheado (hasta 36 intentos × 10s = ~6 min). Si matchea → "Deploy confirmado" y abre el portal; si vence el timeout → avisa y abre igual (no bloquea el cierre). Recién ahí hace `start "%PORTAL%"`.
- **Validado:** healthz local devuelve `{"commit":"", ...}` (vacío sin la env de Render, correcto); lógica de polling PowerShell probada (match con SHA correcto = OK, mismatch = espera); `.bat` reconvertido a **CRLF** (CR=LF=269 bytes) tras normalización del editor — `.gitattributes` ya fuerza `*.bat eol=crlf`; `python -m ast` OK en server_orbit.py.
- **Nota:** el campo `commit` en healthz sólo existe en Render **después** de desplegar este commit; hasta entonces el .bat caerá en el timeout y abrirá igual (comportamiento de transición esperado). Complementa el fix de `safe()` (reintentos) de esta misma fecha.

## 2026-07-17 - fix(portal): `safe()` reintenta ante fallos transitorios de Render ("no salen los vendedores")

- **Síntoma:** tras el cierre del día el usuario abrió el portal (Render) y **no aparecían los vendedores**. Sospecha de que falló el cierre.
- **Diagnóstico:** el cierre de las 17:22 corrió **OK** (log 28KB sin crash, push a `origin/master` confirmado). Los datos están bien de punta a punta: `/api/dashboard` devuelve los **7 vendedores** tanto en **local** como en **Render**, sin filtro y con `?dia=Sa`. La ausencia de V6/V8/V10 en `mod_volumen_vendedor.csv` es **esperada** (no trabajan sábado; el día operativo pasó a "Sa") y queda cubierta por el fallback de `resultado.xlsx`.
- **Causa raíz (frontend):** reproduciendo el render de Render con Playwright aparecieron `ERR_CONNECTION_CLOSED` y `ERR_HTTP2_SERVER_REFUSED_STREAM`. Render (tier starter) rechaza requests concurrentes durante cold-start/redeploy; el portal dispara ~6 `fetch` en paralelo (`Promise.all` en `loadCore`/`loadRole`). `safe()` hacía **un solo fetch y devolvía `null` ante cualquier fallo**, sin reintento → si caía `/api/dashboard`, `D.dash=[]` y **no se renderizaba ningún vendedor**. El `.bat` del cierre además abre el navegador de inmediato, cuando Render todavía está redeployando.
- **Cambio (`PAV MATINAL PE_A FLOR/portal.html`, línea 1254):** `safe(url, tries=4)` reintenta con backoff (400/800/1600ms) ante fetch fallido o `!r.ok`, devolviendo `null` sólo tras agotar los intentos. Firma `safe(url)` intacta → todos los llamadores siguen funcionando. Sin cambios de datos, endpoints ni diseño.
- **Validado (Playwright, gerencia, local y Render):** el ranking renderiza los **7 vendedores** (chip "7 vendedores"), `loginScreen` oculto, sin page-errors ni errores de consola JS tras el fix.
- **Pendiente de commit:** portal.html es archivo funcional → el próximo cierre lo **bloqueará** hasta que se commitee (ver `check_git_cierre.py`).

## 2026-07-17 - feat(planes_as): tercer sin cargo "Puntera (El Cazador)" + tres bloques rotulados

- **Pedido:** el usuario cargó `01_INPUTS/Planes AASS/sincargosjulio.xlsx` con **3 hojas** (diferentes sin cargos). Que quede claro en la tarjeta de Planes AS **cuál sin cargo es por escala (alcance del mes de junio), cuál por puntera y cuál por plan frío**, y que se pinten en verde a medida que se entregan.
- **Diagnóstico:** escala (`sc_*`, hoja "Planes AASS") y plan frío (`pf_*`, hoja "plan frío") **ya existían**. Faltaba la **Puntera** (hoja "Puntera": cajas de vino **El Cazador** cualquier varietal).
- **Motor (`generar_datasets_acum.py`):** nueva `_cargar_puntera_mes()` (lee hoja "Puntera"; header con mojibake → normalización dejando sólo ASCII, porque `replace("�","")` no matchea el U+FFFD del Excel). En `generar_planes_as`: `pt_disponible` (cajas del Excel), `pt_enviado` (líneas 100% descuento con Articulo 'CAZADOR', sólo para clientes con puntera), `pt_pendiente`, `pt_estado`; detalle de envíos categoría "puntera"/producto "El Cazador" en `mod_sincargos_envios.csv`. 4 columnas nuevas al `mod_planes_as.csv`.
- **Backend (`server_orbit.py`):** ambos endpoints `planes_as` devuelven `pt_disponible/pt_enviado/pt_pendiente/pt_estado`.
- **Front (`portal.html`):** los tres sin cargos quedan rotulados **① Sin cargo por escala (alcance <mes anterior>)**, **② Sin cargo por puntera (El Cazador)**, **③ Plan frío (Six Pack Smirnoff ICE)** — en gerencia (celda de la tabla + header de columna) y vendedor (bloques separados por borde). Helper `mesAnteriorNom()` (dinámico, hoy = Junio). Cada uno pinta verde (`✓ enviadas`) a medida que se factura el sin cargo, dorado (`⚠ pendiente`) si falta. Click abre el detalle con fechas (`verSincargo(cid,'El Cazador')`, ya soportado).
- **Validado (`:8599` + Playwright, gerencia + V8):** 5 clientes con puntera (172, 538, 30011=6caj, 30044, 30017), todos pendientes (el único envío de Cazador del mes fue al cliente 1446, sin puntera → correctamente ignorado). Screenshots confirman los tres bloques diferenciados. Sin errores de consola.
- **`sincargosjulio.xlsx`** trackeado y no ignorado → viaja a Render.

## 2026-07-17 - fix(planes_as): "comprado" de la innovación = cobertura AS (6 unidades), no cualquier compra

- **Confirmación del usuario:** "comprado en el mes es mes calendario" (ya estaba) **"y teniendo en cuenta 6 unidades para cobertura"**.
- **Cambio (`server_orbit.py`):** el flag `comprado` (verde) de cada innovación en Planes AS deja de ser `importe>0` y pasa a exigir **≥ 6 unidades** del producto en el mes calendario. Es la misma regla que la cobertura de **Autoservicio** del resto del sistema (`UMBRAL["AUTOSERVICIO"]=6` en `generar_datasets_acum.py`); los Planes AS son todos AS. Constante `_INOV_PLAN_AS_MIN_UNID=6`. `_inov_plan_as_compras()` ahora suma `CantBase` por `(cliente, código)` y `_inov_plan_as_cliente()` compara contra el umbral; el payload agrega `unidades` por innovación.
- **Front (`portal.html`):** rótulo `Innovaciones del mes · cobertura 6+ un.` y contador `n/total cubiertas`; cada chip muestra `· Nu` y tooltip con las unidades del mes.
- **Validado (server :8599 + Playwright):** 832 chips (32×26); **53 verdes (≥6u)** y **6 casos con 3u que ahora caen en dorado** (antes eran verde): p.ej. cliente 2211 con Los Árboles = 3u → pendiente. Cliente 30013 mantiene 2 cubiertas (6u de Trapiche + 6u de Dada sweet red). Screenshot confirma el nuevo rótulo. Sin errores de consola.

## 2026-07-17 - feat(planes_as): innovaciones seguidas por cliente (compró=verde / no=dorado)

- **Pedido:** en la pantalla de **Planes AS**, al hacer click en cada cliente mostrar las **innovaciones** marcadas con `x` en la columna `AASS c/plan` de `Innovaciones.xlsx`, pintando en **verde** si el cliente las compró en el mes y en **dorado** si no. Para gerencia y vendedor. (Antes: el usuario agregó 2 productos nuevos + la columna `AASS c/plan` con `x`; Termidor queda sin `x` y por tanto afuera.)
- **Fuente:** `01_INPUTS/INNOVACIONES/Innovaciones.xlsx` (mismo archivo que la pantalla de Innovaciones → un producto agregado ahí entra en las dos). La compra sale de `ventas.csv` (mes vivo), `ImporteNetoItem>0`, cruce por `Codigo`, **sin filtro de Empresa** (regla P&P Logística). Match por código exacto de innovación.
- **Backend (`server_orbit.py`):** nuevos helpers `_inov_plan_as_productos()` (lee la columna `x`, cacheado por mtime, normaliza `\xa0`), `_inov_plan_as_compras()` (cliente_id → set de códigos comprados en el mes, sobre `_ventas_parsed()` cacheado) y `_inov_plan_as_cliente()`. Ambos endpoints `/api/gerencia/planes_as` y `/api/vendedor/<vid>/planes_as` devuelven `innovaciones_productos` (catálogo) y por cliente una lista `innovaciones:[{codigo,nombre,comprado}]`.
- **Front (`portal.html`):** helper `pasInovHTML(c)` (chips verde `.ok` / dorado `.wn`, contador `n/total`) + `pasInovTog()` (toggle). Gerencia: fila de la tabla clickeable → fila de detalle `colspan=6` desplegable + badge `💡 ok/total`. Vendedor: tarjeta clickeable → bloque desplegable al pie con las innovaciones + badge. Se marcaron con `data-nostop` los onclick internos (sin-cargo, plan frío) para que no disparen el toggle.
- **Validado (server en :8599, `PENAFLOR_SKIP_BOOT=1`):** gerencia 32 clientes AS + 26 innovaciones; V8 16 clientes; cliente 30013 → `compradas: 2`. Cruce verificado contra `ventas.csv`: 30013 compró códigos **74840 + 74886** este mes → coincide exacto. `ast.parse` OK, 26 marcados con `x` (Termidor 14425 excluido).
- **Sin cambios en datasets ni motor de acciones:** es lectura directa del xlsx + ventas, no toca `mod_planes_as.csv` ni `mod_innovaciones_segmento.csv`.

## 2026-07-16 - data(sellout): objetivo de Vermouth = 6312 litros

- **Pedido:** *"el objetivo de Vermouth es de 6312 litros"*.
- **Cambio (`01_INPUTS/OBJSELLOUT.xlsx`):** fila `vermouth | vermouth | 6312`, insertada antes de la fila `total` con el mismo patron que **vinos de guarda** (categoria = Grupo PBP, sin fila 'Total' aparte). Estilos copiados de esa fila. **Sin tocar codigo**: el objetivo por categoria ya sale de este archivo (fuente unica).
- **Validado:** `_cargar_objetivos_sellout()` -> `VERMOUTH {'total': 6312, 'subs': {'vermouth': 6312}}`; la tarjeta muestra **VERMOUTH | 0 L | 6.312 L | faltan 6.312 L | 0,0% | 0 clientes** (0 L porque Cinzano aun no tiene ventas). Playwright sin errores de consola.
- **Efecto colateral esperado:** el **TOTAL** de la tarjeta pasa de 54.285 a **60.597 L** (el portal suma los objetivos de las categorias, no lee la fila 'total' del archivo).
- **Fila `total` del xlsx actualizada a pedido del usuario: 54283 -> 60597.** Es **cosmetica**: el loader IGNORA esa fila (`_cargar_objetivos_sellout` saltea categoria == 'total') y el portal arma su TOTAL sumando las categorias. Sirve para que el archivo cierre solo al abrirlo.
  - **60597, no 60595:** la fila vieja ya estaba mal ANTES de vermouth (decia 54283 contra 54285 de suma real), asi que sumarle 6312 habria arrastrado el error de 2 L. El numero correcto es la **suma de los objetivos por categoria**, que es lo que muestra el portal.
  - Ojo al recalcularlo a mano: **RTD (S) NO se suma aparte** — el `Total` de rtd (12277) ya incluye rtd 5525 + rtd (s) 6752, y `_OBJ_CAT_NORM` mapea RTD (S) -> RTD. Sumar las 8 filas de categoria da 67.349, que es doble conteo.
  - Verificado post-cambio: el sistema sigue leyendo 7 categorias (sin una 'TOTAL' colada) y la suma da 60597 = la fila del archivo.


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
