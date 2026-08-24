# BITÁCORA 2026-08-24 (parte 2) — Códigos del catálogo vs códigos del ERP

Publicada en **`b57aec7`**. Continuación de [[BITACORA_2026-08-24]] (pantalla Stock).

El usuario, mirando la pantalla nueva: *"hay 3 Antares que sí tenemos stock (Kolsch, Scotch
y Caravana) y vos estás tomando códigos viejos"*. Tenía razón, y el problema es más general
que Antares.

---

## La causa: dos sistemas, dos códigos para el mismo producto

La matriz 11T, `mpa_codigos.csv` y el maestro 04D se arman con el **catálogo del proveedor**
(`RAW_PRODUCTOS/productos<mes>.xlsx`, hoja `Cluster 25`). Ese catálogo factura esos tres
Antares como **60001 / 60002 / 60007**. **Nuestro ERP los factura como 30329 / 30343 / 30268.**

Los códigos del catálogo no tienen **ni una línea de venta ni una unidad de stock** en ninguna
de nuestras fuentes. Y ese es el punto peligroso:

> **No se ve como un error. Se ve como un producto sin stock.**
> La pantalla decía *"no está en el archivo de stock"* mientras había **150, 102 y 96
> unidades** en depósito. Un número plausible y equivocado es peor que un error visible.

Detalle que lo delata: en el catálogo la descripción es `ANTARES KOLSCH LATA 6X473 (60001)`
— alguien le pegó el código del proveedor al nombre. En nuestro ERP es
`ANTARES LATA KOLSCH 6 X 473ML`.

## No me quedé en Antares: audité los 3 universos

De los **176 códigos** (82 del 11T + 27 de Innovaciones + 67 de MPA), **14 no figuraban ni en
stock ni en ventas**. Pero un código sin stock ni ventas **no es automáticamente un código
viejo**. Hay que separar dos cosas distintas:

| | Qué es | Qué corresponde |
|---|---|---|
| **Código equivocado** | Existe un producto vivo, con el mismo nombre y presentación, bajo otro código | Corregir |
| **Producto que no trabajamos** | No hay ningún equivalente vivo en stock ni en ventas | Dejarlo como *"sin existencia"*: es la verdad |

Buscando para cada huérfano un gemelo vivo (mismo producto y presentación), quedaron **sólo 3
códigos equivocados** — exactamente los tres reportados. Los otros 6 no tienen equivalente:

- **Antares Honey (60008)** y **Antares Playa Grande (60015)** — no los compramos.
- **D.David Tannat (41681)** — el único Tannat vivo es `ELEMENTOS TANNAT`, otra línea.
- **Trapiche Reserva Syrah (74420)**, **Merlot (74422)**, **Dulce Cosecha Rosé (74478)** — no
  trabajamos esas variedades de Trapiche Reserva.

**Innovaciones no tenía ningún código mal** (27 de 27 vivos).

## La solución: una tabla revisada a mano, un solo lector

`09_CONFIG/codigos_equivalencias.csv` — mismo patrón que `mpa_codigos.csv`. Una fila se agrega
**sólo** cuando se verificó que el código del catálogo no tiene ventas ni stock y el del ERP sí,
para el mismo producto y presentación.

**Deliberadamente NO se adivina por texto.** Un `contains` sobre la descripción es lo que en su
momento metió `GORDON'S GIN` y `GORDON'S TONIC` dentro de Gordon's Flavours (51 clientes contra
32 reales, ver CLAUDE.md). La tabla es corta, explícita y auditable a propósito.

`motor_codigos.py` es el **único** lector. Sin archivo devuelve `{}` y no cambia nada: el
cambio es seguro por construcción. Lo consumen `motor_11t.cargar_matriz_11t()` y
`_mpa_universo()` — un solo punto por consumidor, sin listas paralelas.

## Tres cosas más que hubo que arreglar, y una que NO

**El maestro 04D.** El CSV que usa el runtime (`09_CONFIG/maestro_04D_productos.csv`) **ya
tenía** los 3 códigos, de la sesión del 18/08. El que estaba atrasado era el **xlsx fuente**
(256 → 259 filas). Categoría, segmento y litros se **copiaron del gemelo**, no se inventaron.

**Los datasets del 11T estaban congelados con los códigos viejos.** Las dos pantallas de
gerencia dejaron de coincidir, y lo cazó un test que existe justamente para eso
(`test_dashboard_vivo_y_11t_empresa_coinciden_en_el_total`: 148 vivo contra 147 del dataset).
Se regeneraron **sólo los del 11T**: `main()` además appendea a `02_HISTORY`, y correrlo hoy
**pisaría el snapshot del último cierre** ([[BITACORA_2026-07-23|snapshot fechado por ventas]]).

**La descripción vacía.** Caravana no está en VSB y el catálogo no conoce el código, así que
esa fila salía con el titular pelado (*"ANTARES"*). Ahora el nombre se completa con el de
cualquier depósito que sí tenga el producto: es el mismo producto.

**Lo que NO se tocó:** los 6 productos sin equivalente. Siguen apareciendo como "sin
existencia", porque no los trabajamos. Inventarles un código para que la pantalla quede
"prolija" sería exactamente el error que este trabajo corrige.

---

## Impacto medido

| | Antes | Después |
|---|---|---|
| Pantalla Stock · Kolsch / Scotch / Caravana | "no figura" | PyP 102 / 42 / 96 u · VSB 48 / 60 / – |
| 11T ANTARES · clientes que cubren | 146 | **147** |
| 11T ANTARES · botellas netas | 1.128 | **1.194** |
| 11T · los otros 10 titulares | — | **sin cambio** (medido titular por titular) |

## Validación

- `test_motor_11t.py` **73/73 OK** (antes de regenerar el dataset fallaba 1).
- `test_motor_padron.py` OK. **`test_motor_codigos.py` nuevo: 13/13 OK.**
- Smoke de 9 endpoints con `json.dumps` completo.
- Auditoría re-corrida: **0 códigos con reemplazo pendiente**.
- En vivo en Render: `dias_stock` devuelve `30268:96 | 30329:102 | 30343:42`, y
  `11t_empresa` da ANTARES **148** de empresa (147 vendedores + depósito).

---

## Archivos tocados

| Archivo | Cambio |
|---|---|
| `09_CONFIG/codigos_equivalencias.csv` | **Nuevo.** Puente catálogo → ERP, revisado a mano. 3 filas |
| `motor_codigos.py` | **Nuevo.** Único lector de la tabla; `canonizar` / `canonizar_serie` |
| `test_motor_codigos.py` | **Nuevo.** 13 tests |
| `motor_11t.py` | `cargar_matriz_11t()` canoniza al cargar |
| `server_orbit.py` | `_mpa_universo()` canoniza; la descripción se completa con la de cualquier depósito |
| `01_INPUTS/04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx` | +3 filas (256 → 259), copiadas del gemelo |
| `04_DATASETS_ORBIT/mod_11t_*.csv` | Regenerados con los códigos corregidos |

---

## Pendiente

- [ ] **`30275 ANTARES LATA IPA` tiene 6 unidades en VSB y no está en ningún universo.**
      No se agregó porque **no es un reemplazo**: `60017 ANTARES IPA LATA (New)` está vivo,
      con 288 unidades y 630 vendidas. Son dos códigos de IPA conviviendo en el ERP.
      **Preguntar a depósito cuál es el bueno**; si 30275 es residuo, que lo den de baja.
- [ ] **Confirmar con el negocio los 6 productos sin equivalente.** Hoy figuran como "sin
      existencia" porque no los trabajamos. Si alguno se compra bajo otro código que no supe
      relacionar, va como fila nueva en `codigos_equivalencias.csv`.
- [ ] **El allowlist del cierre no publica `09_CONFIG/`** — ninguno de sus archivos, ni
      `mpa_codigos.csv` ni `maestro_04D_productos.csv`. La convención es que la config a mano
      viaja en un commit. **Al agregar una equivalencia hay que commitearla**: el cierre
      diario no la va a subir y va a dar verde igual (mismo patrón que
      [[BITACORA_2026-07-28b|ERR-014]]).
- [ ] **Este chequeo conviene que sea periódico.** El catálogo del proveedor se re-dropea cada
      mes; nada garantiza que el próximo no traiga otro código que nuestro ERP no use. El
      script de auditoría cruza universo × stock × ventas y tarda segundos.

> Reglas en [[REGLAS_NEGOCIO_PAV]] · trazabilidad en [[MAPA_DATOS_PAV]] · la pantalla en
> [[BITACORA_2026-08-24]].
