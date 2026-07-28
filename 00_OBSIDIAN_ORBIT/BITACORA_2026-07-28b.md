# Bitácora — Sesión 2026-07-28 (parte 2)

Detalle en `CHANGELOG_AI.md`. Continuación de [[BITACORA_2026-07-28]] (pantalla Semanal). Un solo tema:

1. **Días de Stock** al pie de la pantalla Semanal, en dos tarjetas: **Stock PyP** y **VSB Cuyo**.

---

# 1. Días de Stock

## Pedido

Una tarjeta de stock con los **días de stock** según la venta del **mes anterior**, para tres universos: **11 Titulares**, **Innovaciones** y **MPA** (los productos de plan AASS Inicial y Silver, en `01_INPUTS/MPA/MPA.xlsx`).

En una segunda pasada: la tarjeta se llama **Stock PyP** y se calcula sólo con **V3, V4, V6, V8, V10**; los otros dos vendedores (**V7, V9**) van en una tarjeta aparte, **VSB Cuyo**, con su propio archivo de stock. Más un resumen arriba de lo que está bajo 30 días y un desplegable abajo con el detalle.

## Cómo se lee el número

```
venta diaria = unidades vendidas el mes anterior ÷ días operativos del mes
días de stock = unidades disponibles hoy ÷ venta diaria
```

Ejemplo real (SMF Ice Green Apple, PyP): 4.843 u en junio ÷ 24 días operativos = 201,8 u/día. 289 u en depósito ÷ 201,8 = **1,4 días**. Se lee: *si seguimos al ritmo del mes pasado, lo que hay alcanza para 1,4 días de venta*.

Tres cosas que hay que tener presentes al interpretarlo:

- Es el **ritmo del mes cerrado**, no una proyección del mes en curso. Un producto en acción o de temporada va a durar menos de lo que dice el número.
- El **tránsito NO suma** a los días. Está como columna de referencia: 1,4 días con mercadería en camino no es lo mismo que 1,4 días sin nada viniendo.
- Cada depósito cuenta **sólo la venta de su ruta**.

## Las decisiones de cálculo

### Unidades, no cajas

`CantBase` (ventas) y `UniTotalDisponible` (stock) están en la **misma unidad**, y hay que verificarlo antes de dividir: si una fuera cajas y la otra botellas, los días darían 6x mal. Chequeo que lo confirma: Alma Mora Malbec (74210) vendió 6.172 u en junio contra 5.741 u en depósito — magnitudes coherentes, ~22 días.

### Devoluciones con signo

Junio trajo **116 filas con `CantBase` negativo** (`TipoDeVenta` = "Devolución por Rechazo" / "por Canje"). Se suman **con signo**, no se filtran: la mercadería devuelta vuelve al depósito, así que netear es lo correcto.

### Días operativos, no días corridos

El divisor son los **días lun-sáb sin feriados** (junio 2026 = 24). El depósito no despacha domingos, así que un "día de stock" tiene que ser un día en el que se vende. Con días corridos (30) la cobertura daría ~25% más larga de lo real.

### Dos depósitos, dos tarjetas — y por qué no se mezclan

| Tarjeta | Stock | Ruta |
|---|---|---|
| Stock PyP | `Stock/stock.xlsx` | V3 · V4 · V6 · V8 · V10 |
| VSB Cuyo | `Stock/stock_VSB_Cuyo.xlsx` | V7 · V9 |

Cada uno cruza **su** stock con la venta de **sus** vendedores. Si se midiera el stock de PyP contra la venta de los 7, la cobertura daría más corta que la real; al revés para VSB. **V20 (Depósito) queda fuera de los dos**: no pertenece a ninguna de las dos rutas.

Esto **reemplaza** el criterio con el que había arrancado la primera versión ("no se excluye ningún vendedor, el stock lo consume toda la salida física"), que era razonable mientras había un solo stock y dejó de serlo al aparecer el segundo depósito.

## MPA: el mapeo que NO se automatizó

Éste fue el punto difícil y vale dejarlo escrito, porque la tentación de automatizarlo va a volver.

`MPA.xlsx` lista 62 productos por **nombre comercial internacional** ("Alaris Malbec 0.75L", "Smirnoff No.21 Red Vodka 0.7L bottle"). El ERP los tiene con **abreviaturas propias**: `TRAPICHE ALARIS MALBEC 6X750`, `SMIRNOFF 21 DO 12X700`, `SBLANC`, `CABSAUV`, `RVA`, `ETIQ MARRON DNAT`, `FMORAS`.

Escribí un matcher con normalización, extracción de volumen (0.75L → 750) y diccionario de abreviaturas. Resultado: **33 de 62**, y —lo importante— **varios de los que daba como confiables estaban mal**:

- `Alma Mora Cabernet Sauvignon` → *F.LAS MORAS CABSAU* (otra bodega)
- `Don David Malbec` → *DON DAVID RESERVA MALBEC* (otra línea)
- `Dada 3 Syrah - Cabernet` → *DADA ART CABERNET* (otro producto)

Un mapeo adivinado dentro de un reporte de stock es **peor que no tener el reporte**: nadie audita un número que parece razonable. Así que se descartó y se hizo a mano: **`09_CONFIG/mpa_codigos.csv`**, revisado producto por producto contra el catálogo del ERP, con las descripciones **tomadas del catálogo** (no tipeadas, para no introducir errores nuevos). **59 de 62**.

Las **3 que quedaron sin mapear a propósito** se listan en la tarjeta, no se descartan en silencio:

| MPA | Por qué |
|---|---|
| Alma Mora Blend 0.75L | el ERP tiene BLEND TINTO (74437) y BLEND BLANCO (74438); el nombre MPA no dice el color |
| Dada 7 Dulce 0.75L | no existe un Dada N°7 vino; sólo espumante rosé (74473) y orange bitter (74728) |
| Suter Etiqueta Marron Blanco 0.75L | 20303 "ETI MARRON NEW PIN" está en proceso de baja y no confirma que sea el seco |

Se resuelven agregando la fila en el CSV. **Sin tocar código.**

Las 3 últimas columnas de `MPA.xlsx` (*Antares*, *Smirnoff ICE Flavors*, *Smirnoff Flavors 700 ml*) **no son SKU sino agrupaciones de línea**: se expanden a todos los códigos de esa línea y se deduplica por código. Criterio confirmado por el usuario.

## El export de stock equivocado

`01_INPUTS/Stock/stock.xlsx` traía **114 códigos de Georgalos, Bigar, Dielo y Don Satur** — purés, chocolates, chocolatada — con códigos de 8-9 dígitos. Cero productos Peñaflor. Como PyP distribuye varias marcas, el export había salido **filtrado al revés**: trajo todo lo que NO es Peñaflor.

Se detectó porque el cruce contra el portfolio dio **0 coincidencias**. De ahí salió una decisión de diseño que conviene conservar: el endpoint expone `stock_codigos` / `stock_match` / `stock_ok`, y **si ningún código del portfolio aparece en el archivo, la tarjeta avisa y los KPI van en "–", no en 0**. Un 0 se leería como "no tenemos stock", que es una afirmación distinta de "no sabemos". Es la regla de [[feedback_nunca_cero_por_falta_de_calculo]] aplicada a una fuente entera, no a una celda.

El usuario re-exportó en la misma sesión: **222 códigos, todos GRUPO PEÑAFLOR SA**. Revalidado sin parches.

**Chequeo rápido para la próxima:** si `NombreProvedor` no dice GRUPO PEÑAFLOR, el export salió mal. Vale también para `Stock sin Venta`, que lee el mismo archivo.

## Resultado con datos reales (base junio 2026, 24 días operativos)

| | 11 Titulares | Innovaciones | MPA |
|---|---|---|---|
| **Stock PyP** | 19,9 d · 12 bajo 15 d | 133,7 d · 1 bajo 15 d | 18,5 d · 9 bajo 15 d |
| **VSB Cuyo** | 95,0 d · 6 bajo 15 d | 236,9 d · 2 bajo 15 d | 91,7 d · 5 bajo 15 d |

Lo más ajustado en PyP son las **latas de Smirnoff Ice**: Green Apple 1,4 d y Red Berries 2,1 d. Son las que más rotan (201,8 y 313,5 u/día) y las que menos cobertura tienen — el combo que rompe.

VSB Cuyo tiene mucha más cobertura simplemente porque son 2 vendedores contra 25.765 unidades.

## La tarjeta

Dos tarjetas con acento propio (PyP magenta `#E2147A`, VSB Cuyo azul `#4DA3FF`) aplicado a la barra lateral, el degradado del encabezado, el pill de la ruta y el tab activo. Cada una, en este orden:

1. **KPIs**: días del conjunto · bajo 15 d · bajo 30 d · sin existencia · unidades · unidades/día.
2. **Resumen "Bajo 30 días"**: grilla con lo que está por debajo del umbral, borde rojo (<15 d) o ámbar (15-30 d). Es lo que se ve de entrada, sin desplegar.
3. **Desplegable** con la tabla completa.

Tabs de universo y desplegable son **independientes por tarjeta**.

Umbrales en `_DIAS_STOCK_CRITICO` / `_DIAS_STOCK_ATENCION` (15 / 30), a confirmar con el negocio.

## Validación

- Endpoint 200, dos bloques, `stock_ok=true` en los dos.
- **Chequeo cruzado en el DOM del portal** (los screenshots del navegador se pusieron intermitentes, así que se leyó el render directamente): acentos correctos, 22 y 8 ítems en los resúmenes, el desplegable de VSB abre 82 filas sin afectar al de PyP, la nota de los 3 sin código aparece sólo en el tab MPA.
- `stock_sin_venta` (217/55) y `semanal` (12 meses) siguen OK: `_stock_disponible(archivo="stock.xlsx")` mantiene el default.
- `node --check` + `ast.parse` OK.

## Nota de método

Dos veces en esta sesión el camino más rápido habría sido aceptar un dato que "parecía bien": el matcher automático de MPA y la tabla de ceros del stock roto. Los dos casos terminaban en un número plausible y falso dentro de un reporte que se usa para decidir compras. El costo de verificar (mapear 62 productos a mano, cruzar códigos contra el portfolio) fue de una sola vez; el costo de no hacerlo se habría pagado cada mañana.
