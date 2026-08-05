# BITÁCORA 2026-08-05b — 11 Titulares: de CCC a cobertura, motor único

## Qué se pedía

Unificar la medición de 11 Titulares. Varios módulos contaban "cualquier cliente con neto
positivo" y para Gordon's Flavours mostraban 51 clientes. La medición correcta, validada
contra el resultado informado por el proveedor, es **cobertura**: 3 botellas acumuladas en
Tradicional, 6 en Autoservicio. Control julio-2026: **25 Trad + 7 AS = 32**.

## Causa de la diferencia 51 → 32

Dos errores acumulados, ninguno de datos:

1. **No se aplicaba el mínimo de botellas.** Se contaba CCC (cliente con compra) y se lo
   mostraba como cobertura. De los 51, **19 no llegaban al mínimo de su segmento**.
2. **El titular se resolvía por `str.contains("GORDON")` sobre la descripción del artículo.**
   Eso metía **GORDON'S GIN (30075)** y **GORDON'S TONIC (35107)** dentro de Gordon's
   Flavours, cuyo universo oficial en `DETALLE_SKU_11T_AS` son solo **30134** (Pink Gin) y
   **30139** (Tropical Fruits). Aportaban 16 clientes ajenos.

Descomposición exacta: 51 CCC − 16 clientes de SKU ajeno = 35 clientes con SKU oficial;
de esos, 3 no llegan al mínimo por sí solos y 1 más cae al recortar el período → **32**.
(Medido: 36 clientes tocaron SKU oficiales en julio, 4 no alcanzaron el mínimo.)

## Hallazgo lateral: el filtro de vendedor borraba un cliente real

Con V20 excluido por el `CodVendedor` de la **factura**, Gordon's Autoservicio daba **6**, no 7.

El cliente **15 — BELTRAMO, DUTTO Y DUTTO S.R.L.** es un Autoservicio de la **cartera de
V8** en `clientes.xlsx`. En julio compró 60 botellas de Gordon's Pink Gin, pero la factura
la emitió **V20 Depósito**. Filtrando por el vendedor de la factura, el cliente desaparecía
de la cobertura de la empresa.

**Regla que quedó:** el cliente pertenece a la cartera del **padrón**; la venta se consolida
sin importar qué razón social o vendedor la facturó. La exclusión de V1/V2/V5/V20 se aplica
sobre el `codven` del padrón. Es el mismo criterio que `_LEEME_EMPRESA` para P&P Logística:
V20 no es otro distribuidor, es un canal de facturación de la misma entidad física. **V20
sigue sin cartera propia y sin objetivo**: no se le atribuye cobertura a nadie.

Otro cliente de V20, **20026 VILLAFAÑE MARIANO** (`codven = 1` "deposito", subsegmento
"Resto de Tradicionales"), queda **fuera** — vendedor excluido y segmento fuera de superficie.
Sale en el reporte de excepciones, no se descarta en silencio.

## Motor único

**`motor_11t.py`** (nuevo). Es la única definición de la regla. Recibe ventas, período,
matriz de SKU, padrón, exclusiones y umbrales; devuelve una fila por cliente × titular con
botellas positivas, devueltas, netas, umbral, cumple y motivo, más un DataFrame de excepciones.

- Titular por **código de artículo** contra `DETALLE_SKU_11T_AS`. El texto de `Marca` solo
  como respaldo **exacto** y solo si la línea no trae código. Sin `contains`.
- Segmento normalizado desde el padrón (tildes, mayúsculas, espacios, KIOSCO/KIOSKO, AS,
  Cadenas Regionales). Superficie = Autoservicio + Almacén + Kiosco; el resto es excepción.
- `CantBase` ya viene en **botellas**: `_litros_por_linea` calcula litros como
  `CantBase × (Lts_caja / UxC)`. No se vuelve a multiplicar por unidades por caja.
- Las notas de crédito traen `CantBase` negativa → la suma da **botellas netas**.
- Líneas con neto = 0 (sin cargo, `Descuento = 100,00%`) no computan; se informan.
- El mínimo se aplica **después** de consolidar. Un cliente se cuenta una sola vez por titular.

## Archivos tocados

| Archivo | Cambio |
|---|---|
| `motor_11t.py` | **nuevo** — motor autoritativo |
| `test_motor_11t.py` | **nuevo** — 44 tests, incluida la regresión de julio |
| `server_orbit.py` | `once_titulares`, `once_titulares_zona`, `11t_empresa`, `11t_vendedor`, `_cierre_once_titulares`, el 11T vivo de `cierre_mes`, el KPI `11T ✓` y `/api/diagnostico` pasan por el motor. Eliminados `_marca_11t_por_codigo`, `_mask_superficie_11t`, `_MARCA_LKP_CIERRE`, `_ART_KW_11T_CIERRE`, `_OBJ_ALIAS_11T_CIERRE` y las tablas de alias embebidas en los endpoints |
| `generar_datasets_acum.py` | `generar_11t_acum` delega en el motor; nueva `cargar_ventas_acumulada_11t()` sin filtro de vendedor; eliminados `_ONCE_TITULARES`, `MAP_11T`, `MARCA_ALIASES`, `ALIAS_LOOKUP` |
| `tools/excel_preventa.py` | usa el motor para titulares, botellas y umbrales |
| `04_DATASETS_ORBIT/mod_11t_detalle.csv` | **nuevo** — salida auditable cliente × titular |
| `04_DATASETS_ORBIT/mod_11t_excepciones.csv` | **nuevo** — SKU sin match, sin cargo, fuera de superficie, duplicados de padrón |
| `00_OBSIDIAN_ORBIT/08_ARQUITECTURA/RETIRO_mod_11_titulares.md` | **nuevo** — retiro documentado |

## Lo que cambia en pantalla

`mod_11t_acum.csv` cambia de contenido, no de esquema. Antes el titular se resolvía por
texto de `Marca` contra una tabla de alias local que no contemplaba los valores reales del
ERP (`SMIRNOFF`, `SMIRNOFF ICE FLAVOURS`, `CHAMPAÑA DADA`, `ANTARES ESPECIALES`,
`GORDON'S FLAVORS` en grafía US). Por eso tres titulares estaban en cero.

| Titular | antes | ahora |
|---|---:|---:|
| GORDON'S FLAVOURS | 0 | 32 |
| ANTARES | 0 | 103 |
| SMIRNOFF FLAVOURS | 0 | 317 |
| SMIRNOFF ICE | 39 | 301 |
| ALMA MORA | 389 | 382 |
| ALARIS | 259 | 249 |
| DADA | 289 | 282 |

El KPI **`11T ✓`** de gerencia pasa a contar **titulares cubiertos sobre 11**. Antes sumaba
`tiene_flag`, o sea pares cliente × marca: daba números de tres cifras contra un total de 11
y no coincidía con el "Marcas 11T" de la pantalla del vendedor, que sí contaba marcas.

Los endpoints ahora devuelven `metrica: "cobertura"`, `umbrales` y `periodo_desde` /
`periodo_hasta`. El campo `ccc` se conserva por compatibilidad con el portal, pero **trae
cobertura**. Convendría renombrarlo en el frontend cuando se toque esa pantalla.

## Período

Explícito en todos lados. Dashboard vivo y `mod_11t_acum`: trimestre en curso (el 11T
resetea en ene/abr/jul/oct). Cierre: el mes del cierre, con corte duro — un cierre de julio
no incorpora agosto aunque el CSV traiga cola.

## Verificación

Las cinco superficies coinciden para Gordon's julio-2026 en **25 Trad / 7 AS / 32 total**:
dashboard vivo, `/api/gerencia/11t_empresa`, `/api/gerencia/11t_acum`, cierre versionado y
el fallback por `ventas_mes`. Las tres fuentes de datos de julio (cierre acumulada, cierre
ventas_mes, acumulada viva recortada) dan lo mismo.

`python -m unittest test_motor_11t` → **44 tests OK**.
`python -m unittest test_matinal_resumen_snapshot` → **6 tests OK** (sin regresión).

## Duplicados V3/V8 del padrón — RESUELTO 2026-08-05

> **Decisión comercial: ante duplicación del mismo cliente entre V3 y V8, la cartera
> autoritativa corresponde a V8.**

Son 10 clientes que el ERP exporta dos veces, una por cada ruta: 272, 320, 1065, 1257,
1336, 1366, 1392, 1414, 1424 y 4758.

Los tres cargadores del padrón hacían `drop_duplicates(keep="first")`. Con el orden real
del Excel eso mandaba **los 10 a V3**, la cartera equivocada. Ahora la resolución vive en
**`motor_padron.resolver_padron()`**, regla única de todo el sistema:

- **V3 + V8 → V8**, conservando la FILA ENTERA de V8. Importa: en 1392 (V3=Sá, V8=Vi) y
  1424 (V3=Sá, V8=Ju) el `DiasVisita` difiere entre las dos filas, así que la ruta del día
  también cambia.
- Mismo cliente duplicado con el mismo vendedor → se deja un registro y se informa.
- **Cualquier otra colisión entre vendedores NO se resuelve sola**: se reporta como
  `DUPLICADO_SIN_REGLA_REVISAR`. Hoy no hay ninguna en el padrón real.

No hay lista de códigos hardcodeada: la regla es por **par de vendedores**
(`PRECEDENCIA_CARTERA`), así que sobrevive a cada re-exportación del ERP y cubre
duplicados futuros entre V3 y V8 sin tocar código.

**Esto NO toca ventas.** No se modificó ningún archivo de ventas, ni el `CodVendedor` de
ningún comprobante. Sólo cambia la pertenencia comercial del cliente: una venta facturada
por V3 o por V20 sigue registrada igual, pero cuando la métrica usa vendedor de cartera se
imputa a V8.

### Antes / después

| Indicador | V3 antes | V3 después | V8 antes | V8 después |
|---|---:|---:|---:|---:|
| Cartera de cobertura | 301 | **292** | 271 | **281** |
| Cartera medida en 11T | 268 | **259** | 207 | **216** |
| Titulares cubiertos (de 11) | 10 | **8** | 11 | **11** |
| Pares cliente×titular cubiertos | 58 | **35** | 688 | **711** |

De los 10, **9 entran al 11T**; el 320 (RABINO JOSE JUAN) es Vinoteca y queda fuera de la
superficie del 11T por regla, en V3 y en V8 igual. En cobertura V8 suma 10 y V3 baja 9,
porque el 320 no estaba en la cartera de V3 (V3 no trabaja On Premise) y sí entra en la de V8.

Ninguno de los 10 aparece ya en cartera ni en indicadores de V3. V3 sigue sin Autoservicio.

### Bug pre-existente encontrado al verificar

`/api/vendedor/<vid>/ruta` devolvía **0 clientes para todos los vendedores, siempre**.
El filtro comparaba `clean_code(codven)` contra el código del vendedor, y `codven` viene
float del Excel: `clean_code("3.0")` devuelve `"30"` (se come el punto y pega los dígitos),
así que la comparación nunca daba verdadera. No tiene relación con los duplicados; se
detectó porque la pantalla de ruta era donde había que ver la reasignación. Corregido con
`motor_padron.normalizar_codigo_vendedor`. Ahora V8 Viernes trae 53 clientes (incluido el
1392) y V8 Jueves 55 (incluidos 1336 y 1424).

## Pendiente
- Renombrar `mod_11_titulares.csv` a `_NO_USAR_` cuando se apague `LEGACY/orbit_matinal_v42.py`.
- Los objetivos de `objetivo 11T.xlsx` fueron fijados contra la regla vieja (CCC sin mínimo).
  Con cobertura real, Gordon's queda en 61,5% del objetivo 52. **Confirmar con Peñaflor si
  los objetivos se recalibran** ahora que numerador y denominador miden lo mismo.
