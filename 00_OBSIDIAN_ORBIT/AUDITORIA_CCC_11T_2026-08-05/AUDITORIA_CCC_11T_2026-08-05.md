# AUDITORÍA CCC / 11 TITULARES — ORBIT Matinal Peñaflor

**Fecha:** 2026-08-05 · **Alcance:** solo lectura, sin modificación de código ni de `01_INPUTS`
**Período auditado:** cierre julio 2026 (`_072026`) + mes vivo agosto 2026
**Valor de control:** CCC = 51

---

## 0. Resultado en una línea

El **51 se reproduce exactamente** desde las filas reales: es el **CCC de GORDON'S FLAVOURS del 11T en el cierre de julio 2026**, medido sobre `01_INPUTS/cierres mes/ventas_acumulada_072026.csv`, con neto > 0, sin mínimo de botellas, superficie AS + Almacén + Kiosco, sin V1/V2/V5/V20.

El módulo de **cierre mensual da 51 (correcto)**. Los que no coinciden son **otros tres módulos que calculan lo mismo de tres maneras distintas**:

| Módulo | Gordon's Flavours | Por qué difiere |
|---|---|---|
| Cierre mensual (`_cierre_once_titulares`) | **51** ✅ | Coincide con el control |
| Dashboard 11T vivo (`/api/gerencia/once_titulares`) | 52 | Período trimestral jul–sep: suma 4 días de agosto |
| `mod_11t_acum.csv` → KPI "11T ✓" y "Marcas 11T" del vendedor | **0** ❌ | Match solo por texto de `Marca` + aplica mínimo 3/6 |
| `mod_11_titulares.csv` → `/api/gerencia/11t_empresa` | **0** ❌ | Dataset legacy con `tiene_flag` todo en 0 |

Además hay **dos defectos independientes en CCC** (ver §5): el CCC empresa del mes vivo cuenta 5 días (31/07 + agosto) en vez del mes calendario, y el CCC nunca consolida notas de crédito.

> **No se corrigió nada.** Ningún valor fue forzado a 51.

---

## 1. Mapa de implementaciones

### 1.A — CCC (Clientes Con Compra)

| # | Pantalla / reporte | Función | Archivo:línea | Fuente | Columnas | Filtros | Agrupación |
|---|---|---|---|---|---|---|---|
| C1 | Gerencia → tarjeta **CCC Empresa vs objetivo** | `gerencia_ccc_empresa` | `server_orbit.py:2583` | `01_INPUTS/ventas.csv` | `Cliente`, `CodVendedor`, `ImporteNetoItem`, `Ramo`, `Subramo` | `CodVendedor ∉ {1,2,5,20}`, `neto>0`. **SIN filtro de fecha** | `nunique(Cliente)` por canal (`_canal_ccc_empresa`, `server_orbit.py:2476`) |
| C2 | Dashboard vendedor → **CCC Mes** por segmento | `_ccc_mes_por_vendedor` | `server_orbit.py:669` | `ventas.csv` vía `_cargar_ventas_mes_actual` (`:638`) → `_ventas_parsed` (`:595`) | `Cliente`, `CodVendedor`, `ImporteNetoItem`, `FechaComprobante`, `Ramo`, `Subramo` | `fecha ≥ 1° del mes`, `neto>0`, excluye `{1,2,5,20}`; V3 → AS=0 y OP=0 | `drop_duplicates(cliente_id, vendedor_codigo)` y luego conteo por `segmento_operativo` |
| C3 | Dashboard → **CCC del Día** | `_ccc_dia_seg` | `server_orbit.py:1196` y `:1802` | `04_DATASETS_ORBIT/mod_ccc_segmento.csv` | `clientes_con_compra`, `segmento_operativo` | pattern-match del segmento | **Suma** de un conteo ya agregado por el motor legacy |
| C4 | Cierre de Mes → **CCC por vendedor × segmento** | `_cierre_ccc_por_vend_segmento` | `server_orbit.py:9569`, consumido en `_cierre_objetivos_avance` (`:9592`) | `01_INPUTS/cierres mes/ventas_mes_<MMAAAA>.csv` vía `_leer_ventas_mes_csv` (`:7032`) | `Cliente`, `CodVendedor`, `ImporteNetoItem`, `Ramo`, `Subramo` | `neto>0` (a nivel línea), excluye `{2,5,20}`; V3 → AS=0 y OP=0 | `nunique(Cliente)` por `(vendedor, segmento)`; el total suma los 5 segmentos |
| C5 | Motor de datasets → `mod_ccc_segmento.csv` | (bloque CCC día) | `LEGACY/orbit_matinal_v42.py:1355` | `ventas.csv` | `Cliente`, `CodVendedor`, `ImporteNetoItem`, `Ramo`, `Subramo` | día objetivo, neto>0 | conteo por `(vendedor, segmento_operativo)` |

### 1.B — 11 Titulares

| # | Pantalla / reporte | Función | Archivo:línea | Fuente | Match de marca | Mínimo botellas | Superficie | Agrupación |
|---|---|---|---|---|---|---|---|---|
| T1 | Gerencia → **11 Titulares (CCC vs objetivo)** | `gerencia_once_titulares` | `server_orbit.py:3424` | `01_INPUTS/ventas_acumulada.csv` | **código** (matriz) → texto `Marca` → **keyword de `Articulo`** | **NO** | AS + Almacén + Kiosco (`_mask_superficie_11t`, `:3404`) | `nunique(Cliente)` por `marca_objetivo`; trimestre en curso |
| T2 | Gerencia → **11T zona del día** | `gerencia_once_titulares_zona` | `server_orbit.py:3584` | `ventas_acumulada.csv` | idem T1 | **NO** | idem T1 | idem T1, filtrado a clientes de la zona |
| T3 | Gerencia → **11T acumulado (cartera vs cubiertos)** | `gerencia_11t_acum` | `server_orbit.py:4504` | `04_DATASETS_ORBIT/mod_11t_acum.csv` | **solo texto** `Marca` (`ALIAS_LOOKUP`) | **SÍ (3/6)** | cartera del padrón, segmentos AS + TRAD | `sum(tiene_flag)` / `count(cliente_id)` |
| T4 | KPI **"11T ✓"** (gerencia) y **"Marcas 11T"** (vendedor) | dashboard | `server_orbit.py:1077-1090`, `:1207`, `:1832` | `mod_11t_acum.csv` | idem T3 | **SÍ (3/6)** | idem T3 | `sum(tiene_flag)` — cuenta **pares cliente×marca**, no marcas |
| T5 | `/api/gerencia/11t_empresa` | `gerencia_11t_empresa` | `server_orbit.py:3781` | `04_DATASETS_ORBIT/mod_11_titulares.csv` | legacy | n/d | n/d | **endpoint muerto: `portal.html` no lo llama** |
| T6 | **Cierre de Mes → 11T** | `_cierre_once_titulares` | `server_orbit.py:9683` | `cierres mes/ventas_acumulada_<MMAAAA>.csv` vía `_leer_ventas_acum_cierre` (`:9663`) | idem T1 | **NO** | idem T1 | `nunique(Cliente)` por marca |
| T7 | Motor → `mod_11t_acum.csv` | `generar_11t_acum` | `generar_datasets_acum.py:852` | `ventas_acumulada.csv` (`cargar_ventas_acumulada`, `:235`) | **solo texto** `Marca` | **SÍ**, `UMBRAL` (`:97`) | cartera de `clientes.xlsx` | `merge(cliente_id, vendedor_codigo)` × 11 marcas × 2 segmentos |
| T8 | Motor → `mod_cobertura_acum.csv` (**cobertura, NO 11T**) | `generar_cobertura_acum` | `generar_datasets_acum.py:792` | `ventas.csv` | — (todas las marcas) | **SÍ (3/6)** | cartera del padrón | `CantBase` total por cliente vs `UMBRAL` |

**Definición de los 11 Titulares:** dos fuentes en paralelo.
- Matriz oficial de SKU: `01_INPUTS/11 titulares autoservicio/11_titulares_autoservicios_match_codigos.xlsx`, hoja `DETALLE_SKU_11T_AS` → **82 códigos, 11 marcas** (incluye Gordon's Flavours: solo `30134` Pink Gin y `30139` Tropical Fruits).
- Lista hardcodeada `_ONCE_TITULARES` en `generar_datasets_acum.py:107` (las 11 marcas, sin códigos).
- Objetivos: `01_INPUTS/objetivo 11T.xlsx` (vivo) y `cierres mes/objetivo 11T_<MMAAAA>.xlsx` (cierre). Ambos con las 11 marcas vigentes, Gordon's incluida (objetivo 52).

---

## 2. Diccionario real de columnas

Los cuatro archivos de ventas comparten el mismo layout de 58-59 columnas del ERP. **Diferencias de formato relevantes:**

| Archivo | Separador | Encoding | Decimal | Fecha |
|---|---|---|---|---|
| `ventas.csv` | `;` | latin1 | coma | `d/m/yyyy` |
| `ventas_acumulada.csv` | `;` | latin1 | coma | `d/m/yyyy` |
| `ventas_mes.csv` / `ventas_mes_<MMAAAA>.csv` | `,` | UTF-8 BOM | coma + comillas | ISO `yyyy-mm-dd` |

| Concepto | Encabezado real | Notas |
|---|---|---|
| Fecha de venta | **`FechaComprobante`** | también existen `FechaEntrega`, `FechaCarga`, `FechaLiquidacion`, `FechaPreparacion`. Regla vigente: siempre `FechaComprobante`. |
| Código de cliente | **`Cliente`** | entero, sin ceros a la izquierda ni sufijos. **No se detectó ninguna variante de formato** en los 4 archivos. |
| Nombre de cliente | **`RazonSocial`** | |
| Código de vendedor | **`CodVendedor`** | entero (`4`, `20`…), nunca `V4` ni `4.0`. `Vendedor` = nombre. |
| Segmento / subramo | **`Ramo`** + **`Subramo`** | en el padrón `clientes.xlsx` el par es `Ramo` + **`SubSegmento`**. También `Taxonomia` y `SegmentoRentabilidad` (no usados). |
| Código de artículo / SKU | **`Codigo`** | entero. Cruza contra `codigo_articulo` de la matriz 11T y `Codigo` del maestro 04D. |
| Descripción del producto | **`Articulo`** | + `Marca`, `Linea`, `Familia`, `Rubro`, `Sabor`, `Calibre`. |
| Cantidad | **`CantBase`** | **= botellas/unidades**, confirmado: `_litros_por_linea` (`server_orbit.py:6791`) hace `CantBase × (Lts_caja / UxC)`, o sea CantBase × litros-por-botella. 0 valores decimales en julio → no hay cajas mezcladas. Comparar contra 3/6 es correcto y **no hay doble conversión**. |
| Importe neto del ítem | **`ImporteNetoItem`** | sin IVA. `ImporteItem` = con IVA. `NetoItem` = neto unitario. |
| Tipo y número de comprobante | **`TipoDeVenta`** (`Venta` / `Devolución por Rechazo` / `Devolución por Canje`) + **`NroComprobante`** (`FAC-…` / `NCR-…`) + `ComprobanteReferencia` | |
| Estado / anulación | **NO EXISTE** una columna de estado ni de anulado | Proxies disponibles: `TipoDeVenta` ≠ `Venta`, prefijo `NCR-`, `MotivoDevolucion` no vacío, `ImporteNetoItem < 0`. En julio: 96 filas negativas, **todas** `NCR-` y `TipoDeVenta` de devolución → los cuatro proxies son consistentes. |
| Descuento | **`Descuento`** (texto, `"0,00%"`) + **`valorDescuento`** (numérico) | |
| Bonificación / sin cargo | **NO EXISTE** una columna explícita | Se identifican sin ambigüedad por **`Descuento == "100,00%"` ⟺ `ImporteNetoItem == 0`** (168 filas en julio, correspondencia 1:1). Llevan `CantBase > 0` y `EtiquetaItem = "PENAFLOR GRUPO OBJETIVO…"`. |

---

## 3. Conciliación de CCC

**Archivo generado:** `conciliacion_CCC_072026.csv` (886 filas, una por código de cliente).
Columnas: `cliente_codigo, cliente_nombre, vendedor, segmento, segmentos_distintos, lineas_originales, lineas_positivas, lineas_cero, lineas_negativas, comprobantes, comprobantes_NCR, importe_positivo, importe_nc_devoluciones, importe_neto_consolidado, ccc_orbit, ccc_regla_correcta, motivo`.

### Resultado

| Medida | Valor |
|---|---|
| Clientes en `ventas_mes_072026.csv` (excl. V1/V2/V5/V20) | 886 |
| **CCC como lo cuenta Orbit hoy** (≥1 línea con neto>0) | **885** |
| **CCC recalculado** (neto **consolidado** del período > 0) | **880** |
| Diferencia | **5 clientes** |
| Clientes sin código válido | **0** (ninguna excepción) |
| Clientes con líneas en más de un segmento | **0** |
| Clientes facturados por más de un vendedor | **0** |
| Códigos duplicados por formato (texto/decimal/espacios) | **0** |

### Los 5 clientes que explican la diferencia

Venta íntegramente anulada por nota de crédito dentro del mismo mes; Orbit los cuenta igual porque filtra `ImporteNetoItem > 0` **línea por línea** antes de consolidar (`_leer_ventas_mes_csv`, `server_orbit.py:7059`), de modo que la línea negativa nunca llega a restar.

| Cliente | Nombre | Vendedor | Importe positivo | NC / devoluciones | Neto consolidado |
|---|---|---|---|---|---|
| 735 | OLMOS JULIO CESAR | V8 | 130.948,56 | −130.948,56 | **0,00** |
| 1084 | PEREYRA ANGELA ESTHER | V9 | 45.556,78 | −45.556,78 | **0,00** |
| 1106 | PALMA MARIA EVA | V9 | 106.374,78 | −106.374,78 | **0,00** |
| 2796 | DALMASSO MARTIN ALEJANDRO | V10 | 866.490,71 | −866.490,71 | **0,00** |
| 7480 | AIMAR SERGIO MARCELO | V3 | 20.225,36 | −20.225,36 | **0,00** |

### Sobre el valor de control 51

**El 51 no es un total de CCC comercial.** El CCC total de julio es de 880-885 clientes y los objetivos de `objccc.xlsx` están en ese orden de magnitud (Tradicionales 845, Autoservicios 145, On Premise 30, Vinotecas 15, On Premise Noche 11). **51 corresponde al CCC de un titular** — ver §4.

Se verificó además que **el CCC comercial no aplica ningún mínimo de botellas** en ninguna de las 5 implementaciones (C1-C5): no hay contaminación de la regla 3/6 sobre el CCC. Ejemplo de control: cliente **751 OVIEDO CLAUDIA ALEJANDRA** (V9, Autoservicio) compró **1 sola botella** de Gordon's y **cuenta como CCC** correctamente.

---

## 4. Conciliación de 11 Titulares

**Archivos generados:**
- `conciliacion_11T_detalle_072026.csv` — cliente × titular × SKU (cantidad, capa de match, estado del match contra el maestro).
- `conciliacion_11T_cliente_titular_072026.csv` — consolidado cliente × titular con umbral y cumplimiento.
- `resumen_11T_por_titular_072026.csv`, `resumen_11T_por_vendedor_072026.csv`.

### Resumen por titular — cierre julio 2026

| Titular | Objetivo | **CCC Orbit (cierre)** | CCC solo matriz oficial | Cobertura si se aplicara 3/6 | `mod_11t_acum` (portal) | Gap keyword |
|---|---:|---:|---:|---:|---:|---:|
| ALMA MORA | 318 | 381 | 377 | 376 | 389 | +4 |
| TRAPICHE RESERVA | 106 | 125 | 122 | 117 | 119 | +3 |
| FINCA LAS MORAS | 189 | 224 | 224 | 219 | 222 | 0 |
| ALARIS | 216 | 243 | 243 | 241 | 259 | 0 |
| DON DAVID | 46 | 67 | 64 | 60 | 64 | +3 |
| DADA | 254 | 369 | 280 | 367 | 289 | **+89** |
| SMIRNOFF FLAVOURS | 193 | 314 | 314 | 312 | **0** | 0 |
| LOS ARBOLES | 199 | 223 | 223 | 219 | 230 | 0 |
| ANTARES | 95 | 100 | 100 | 100 | **0** | 0 |
| SMIRNOFF ICE | 196 | 288 | 288 | 288 | **39** | 0 |
| **GORDON'S FLAVOURS** | **52** | **51** ✅ | **35** | 47 | **0** | **+16** |

Totales por segmento (11T, cierre julio): Tradicional 630 pares cliente-titular (622 llegan a 3 botellas), Autoservicio 182 (143 llegan a 6). Totales por vendedor en `resumen_11T_por_vendedor_072026.csv`.

### Verificación manual pedida — GORDON'S FLAVOURS

| Caso | Cliente | Segmento | SKU | Botellas | Mínimo | ¿Cumple mínimo? | ¿Cuenta CCC 11T? |
|---|---|---|---|---:|---:|---|---|
| Tradicional | 33 ROMINA ARDILES (V10) | TRADICIONAL | 30134 Pink Gin | 3 | 3 | Sí | **Sí** |
| Autoservicio | 751 OVIEDO CLAUDIA ALEJANDRA (V9) | AUTOSERVICIO | 30134 Pink Gin | 1 | 6 | **No** | **Sí** |

**Conclusión de la verificación:** el 51 informado **solo se alcanza sin aplicar el mínimo**. Con mínimo 3/6 el valor sería 47. Los 4 clientes que no llegan al mínimo (234 COLLO MAXIMILIANO, 519 WENZHI LI, 751 OVIEDO CLAUDIA ALEJANDRA, 8021 DONG MEIZHU — todos Autoservicio, 3/3/1/3 botellas) están **incluidos** en los 51.

> Esto **confirma la regla vigente del proyecto** (`business_rule_11t_fuente`): el 11T se mide como **CCC puro, sin mínimo de botellas**. El mínimo 3/6 pertenece a **Cobertura**, que es otra métrica. El requerimiento de la auditoría que pedía aplicar 3/6 al 11T **no coincide con la regla que valida el número informado de Peñaflor**; se deja constancia y no se cambió nada.

### Composición de los 51 — capas de match

| SKU | Descripción | `Marca` en el ERP | ¿En la matriz oficial? | Capa | Clientes |
|---|---|---|---|---|---:|
| 30134 | GORDON'S PINK GIN 6X700 | `Gordon's Flavors` | **Sí** | 1 — código | 34 |
| 30139 | GORDONS TROPICAL FRUITS 6X700 | `Gordon's Flavors` | **Sí** | 1 — código | 6 |
| 30075 | GORDON'S GIN 6x700 | `Gordon's` | **No** | 3 — keyword `"GORDON"` sobre `Articulo` | 14 |
| 35107 | GORDON'S TONIC 4X6X473 | `Gordon's` | **No** | 3 — keyword `"GORDON"` sobre `Articulo` | 13 |

**35 clientes vienen de la matriz oficial; 16 entran solo por el fallback de keyword** (clientes 208, 234, 375, 519, 815, 1249, 1255, 1360, 2237, 7219, 8021, 30006, 30011, 30022, 30023, 30033). Es decir: **el 51 informado incluye Gin y Tónica comunes de Gordon's, que la matriz `DETALLE_SKU_11T_AS` no reconoce como Gordon's Flavours.**

Estos SKU quedan marcados como `REVISAR_ESTADO` en la columna `match_maestro` del detalle, no se eliminaron. Mismo efecto en otras marcas: **DADA +89 clientes** (SKU de `Champaña Dada`: DADA 7 SWEET, ESPUMANTE MARACUYÁ, etc.), ALMA MORA +4 (`Alma Mora Reserva`), TRAPICHE RESERVA +3 (`ORIGEN BY TRAPICHE`), DON DAVID +3 (`Don David Rva`, `EL ESTECO MALBEC`).

### Por qué `mod_11t_acum.csv` da 0 en Gordon's, Antares y Smirnoff Flavours

`generar_11t_acum` (`generar_datasets_acum.py:852`) resuelve la marca **únicamente** con `ALIAS_LOOKUP` sobre el texto de la columna `Marca` — no usa el código de artículo. Los valores reales de `Marca` en el ERP no están en esa tabla de alias:

| `Marca` en `ventas_acumulada.csv` | Filas | Alias esperado por el motor | ¿Matchea? |
|---|---:|---|---|
| `SMIRNOFF` | 925 | `SMIRNOFF FLAVOURS`, `SMIRNOFF SANDIA`, … | **No** |
| `SMIRNOFF ICE FLAVOURS` | 678 | `SMIRNOFF ICE`, `SMF ICE`, `SMIR ICE` | **No** |
| `CHAMPAÑA DADA` | 325 | `DADA` | **No** |
| `ANTARES ESPECIALES` | 91 | `ANTARES` | **No** |
| `ANTARES CLASICAS` | 50 | `ANTARES` | **No** |
| `GORDON'S FLAVORS` (grafía US) | 56 | `GORDON'S FLAVOURS` (grafía UK) | **No** |
| `GORDON'S` (apóstrofo tipográfico) | 37 | `GORDON'S` (apóstrofo recto) | **No** |
| `JW` | 103 | `JW BLACK` | **No** |
| `ALMA MORA RESERVA` | 33 | `ALMA MORA` | **No** |

`server_orbit.py` sobrevive a esto porque **matchea primero por código** contra la matriz oficial; el motor no tiene esa capa. Resultado: en `mod_11t_acum.csv` **GORDON'S FLAVOURS = 0, ANTARES = 0, SMIRNOFF FLAVOURS = 0, SMIRNOFF ICE = 39** (contra 288 reales).

### `mod_11_titulares.csv`

Dataset legacy producido por `LEGACY/orbit_matinal_v42.py:1436`. Tiene **28 "marcas"** (no 11: incluye TANQUERAY, BAILEYS, JW GOLD, COSTA&PAMPA…) y **`tiene_flag = 0` en las 4.489 filas**. Es el *fallback* de `gerencia_once_titulares` y la fuente única de `gerencia_11t_empresa` (`server_orbit.py:3781`), endpoint que **`portal.html` no invoca** — no llega a pantalla, pero está vivo en la API.

---

## 5. Diagnóstico

Contra la lista de causas posibles del pedido:

| Causa evaluada | Veredicto | Evidencia |
|---|---|---|
| **Aplicación incorrecta de mínimos 3/6 al CCC** | **NO** en el CCC comercial · **SÍ** en el 11T del portal | C1-C5 no aplican mínimo. Pero T3/T4 (`mod_11t_acum`) sí lo aplican y alimentan el KPI "11T ✓" y "Marcas 11T" del vendedor, que por eso no reconcilian con los 51. |
| **Conteo de líneas en lugar de clientes únicos** | **NO** | Todas las implementaciones usan `nunique()` o `drop_duplicates`. |
| **Duplicación de códigos de cliente** | **NO en ventas** · **SÍ en el padrón** | 0 duplicados en los 4 CSV de ventas. En `clientes.xlsx`: **2.144 filas / 2.134 códigos → 10 clientes duplicados con `codven` 3 y 8** (272, 320, 1065, 1257, 1336, 1366, 1392, 1414, 1424, 4758). Infla la **cartera** (denominador) de `mod_cobertura_acum` y `mod_11t_acum`, no el CCC. |
| **Fuente de ventas incorrecta** | **SÍ — causa raíz principal** | Cuatro implementaciones de 11T sobre tres fuentes distintas (`ventas_acumulada.csv`, `mod_11t_acum.csv`, `mod_11_titulares.csv`) con tres criterios distintos. |
| **Período incorrecto** | **SÍ — dos casos** | (a) `gerencia_ccc_empresa` (`:2583`) **no filtra por fecha**: `ventas.csv` contiene 31/07 + 01-04/08, así que publica **67 clientes** cuando el CCC de agosto es **49**; los 18 de más son clientes que solo compraron el 31/07. La docstring dice "mes actual" pero el código no lo hace. (b) el dashboard 11T mide el **trimestre** jul-sep, el cierre mide el mes → 52 vs 51 en Gordon's. Diferencia legítima de definición, pero **invisible en pantalla**. |
| **Segmentación incorrecta** | **NO** | Los tres clasificadores espejo (`server_orbit.py:562`, `generar_datasets_acum.py:51`, `_canal_ccc_empresa:2476`) coinciden en julio. 0 clientes clasificados en más de un segmento. |
| **Vendedores excluidos incluidos** | **NO** | `CodVendedor` es siempre entero puro; `_VENDEDORES_EXCLUIDOS = {1,2,5,20}` funciona. V20 correctamente separado. |
| **Devoluciones o notas de crédito** | **SÍ** | 5 clientes con venta 100% anulada por NC cuentan como CCC (§3). El filtro `neto>0` se aplica **por línea, antes de consolidar**, en `_leer_ventas_mes_csv:7059`, `_leer_ventas_acum_cierre:9677`, `gerencia_ccc_empresa:2600` y `_cargar_ventas_mes_actual:646`. |
| **Importe cero o bonificados** | **NO** — correctamente excluidos | 168 líneas sin cargo (`Descuento = 100,00%`, neto = 0) quedan fuera por el filtro `neto>0`. |
| **Conversión incorrecta de cajas a botellas** | **NO** | `CantBase` está en botellas/unidades (§2). No hay doble multiplicación. |
| **Match por descripción en lugar de SKU** | **SÍ — es el que explica los 51 vs 35** | La cascada de `gerencia_once_titulares` / `_cierre_once_titulares` termina en `_ART_KW`, un `str.contains` sobre `Articulo`. `"GORDON"` captura Gin y Tónica (16 clientes); `"DADA"` captura Champaña Dada (89 clientes). |
| **Duplicación entre marcas o titulares** | **NO entre titulares** | Un cliente puede contar en varias marcas (correcto: son 11 CCC independientes). Ningún SKU se asigna a dos titulares. |
| **Diferencias entre dashboard y cierre mensual** | **SÍ — el hallazgo más grave** | Para el mismo concepto y el mismo período, cuatro módulos dan 51 / 52 / 0 / 0. |

### Causa raíz, ordenada

1. **Cuatro implementaciones del 11T, tres criterios de match, dos definiciones de la métrica.** El cierre (T6) y el dashboard vivo (T1/T2) miden **CCC sin mínimo** con match por código; el portal (T3/T4) mide **cobertura con mínimo 3/6** con match solo por texto y lo rotula "11T". No son la misma métrica y se muestran como si lo fueran.
2. **`ALIAS_LOOKUP` del motor está desactualizado contra los valores reales de `Marca`** → Gordon's, Antares y Smirnoff Flavours en 0, Smirnoff Ice al 13%.
3. **El fallback por keyword de descripción contamina el universo del titular** → +16 en Gordon's, +89 en DADA sobre lo que define la matriz oficial de SKU.
4. **`gerencia_ccc_empresa` no filtra por mes** → CCC empresa inflado en 18 clientes hoy.
5. **El filtro `neto>0` se aplica por línea, no por cliente consolidado** → 5 CCC falsos en julio.
6. **10 clientes duplicados V3/V8 en `clientes.xlsx`** → cartera inflada en cobertura y 11T acumulado.

---

## 6. Propuesta de corrección (NO implementada — requiere autorización)

Ordenada por relación impacto/riesgo. **Nada de esto se tocó.**

### P1 — Unificar el match de marca del 11T (alto impacto, riesgo bajo)
- **Archivo:** `generar_datasets_acum.py`, `generar_11t_acum` (`:852`).
- **Cambio:** agregar la capa de match por `Codigo` contra `DETALLE_SKU_11T_AS` **antes** del `ALIAS_LOOKUP`, reutilizando el mismo criterio de `server_orbit.py:3361`. Alternativa mínima: sumar los alias faltantes (`SMIRNOFF`, `SMIRNOFF ICE FLAVOURS`, `CHAMPAÑA DADA`, `ANTARES ESPECIALES`, `ANTARES CLASICAS`, `GORDON'S FLAVORS`, `GORDON'S`) — más barato pero frágil ante la próxima grafía del ERP.
- **Riesgo:** `mod_11t_acum.csv` cambia de valores en el portal (Gordon's/Antares/Smirnoff pasan de 0 a valores reales). Es el efecto buscado.
- **Prueba de regresión requerida:** `mod_11t_acum` debe cubrir las 11 marcas con `tiene_flag>0` y su CCC (sin umbral) debe igualar el de `_cierre_once_titulares` sobre la misma fuente.

### P2 — Separar en pantalla "CCC 11T" de "Cobertura 11T" (alto impacto, riesgo nulo en datos)
- **Archivos:** `server_orbit.py:1077-1090`, `:1207`, `:1832`; `portal.html:2306`, `:2910`.
- **Cambio:** rotular explícitamente el KPI que sale de `mod_11t_acum` como cobertura con mínimo 3/6, y exponer aparte el CCC 11T sin mínimo. Hoy "11T ✓" suma **pares cliente×marca** bajo una etiqueta que se lee como "marcas cubiertas".
- **Riesgo:** cambia texto de UI, no contratos JSON.

### P3 — Decidir el alcance del fallback por keyword (impacto medio, **requiere decisión del negocio**)
- **Archivos:** `server_orbit.py:3466` (`_ART_KW` en `gerencia_once_titulares`) y `_ART_KW_11T_CIERRE`.
- **Pregunta abierta a Peñaflor:** ¿Gordon's Gin y Gordon's Tonic cuentan para el titular "Gordon's Flavours"? El 51 informado dice que **sí**; la matriz `DETALLE_SKU_11T_AS` dice que **no** (daría 35). Igual pregunta para Champaña Dada (369 vs 280).
- **Recomendación:** no tocar el código hasta la respuesta. Si la respuesta es "sí", **dar de alta esos códigos en la matriz** y eliminar el fallback por keyword — así el resultado deja de depender de un `str.contains`.
- **Prueba de regresión requerida:** congelar el caso Gordon's julio 2026 = 51 y DADA = 369 como test.

### P4 — Filtrar por mes calendario en `gerencia_ccc_empresa` (impacto alto, riesgo bajo)
- **Archivo:** `server_orbit.py:2583-2607`.
- **Cambio:** aplicar `FechaComprobante >= inicio de mes`, igual que `_cargar_ventas_mes_actual` (`:645`).
- **Efecto medido hoy:** CCC empresa pasa de **67 a 49**.
- **Riesgo:** el número baja en pantalla; hay que avisarlo antes de publicar.
- **Prueba de regresión requerida:** con `ventas.csv` del 2026-08-04, el endpoint debe devolver 49 y no 67.

### P5 — Consolidar el neto por cliente antes de decidir el CCC (impacto bajo, riesgo medio)
- **Archivos:** `_leer_ventas_mes_csv:7059`, `_leer_ventas_acum_cierre:9677`, `gerencia_ccc_empresa:2600`, `_cargar_ventas_mes_actual:646`.
- **Cambio:** conservar las líneas negativas hasta después del `groupby(Cliente)` y filtrar por suma > 0.
- **Efecto medido en julio:** CCC 885 → 880.
- **Riesgo:** **estos lectores alimentan también sell out, acciones, innovaciones y planes AS.** Cambiar el filtro base los afecta a todos. Recomendación: **no** tocar el lector compartido; agregar la consolidación solo en las funciones de CCC.
- **Prueba de regresión requerida:** los 5 clientes de §3 deben salir del CCC de julio y los litros de sell out no deben moverse.

### P6 — Deduplicar el padrón (impacto medio, riesgo bajo)
- **Archivo:** dato, no código — `01_INPUTS/clientes.xlsx` (10 clientes con `codven` 3 y 8). Corregir en origen; si no es posible, deduplicar al cargar en `cargar_clientes` (`generar_datasets_acum.py:312`).

### P7 — Retirar lo muerto (riesgo nulo)
- `gerencia_11t_empresa` (`server_orbit.py:3781`) y el fallback a `mod_11_titulares.csv` en `gerencia_once_titulares` (`:3519`) apuntan a un dataset legacy con `tiene_flag` todo en 0. Si un día la fuente primaria falla, el fallback devuelve ceros silenciosamente. Renombrar el dataset con la convención `_NO_USAR_` o hacer que el fallback falle ruidosamente.

---

## Anexo — archivos generados por esta auditoría

Todos en `00_OBSIDIAN_ORBIT/AUDITORIA_CCC_11T_2026-08-05/`:

| Archivo | Contenido |
|---|---|
| `AUDITORIA_CCC_11T_2026-08-05.md` | este informe |
| `conciliacion_CCC_072026.csv` | 886 filas — una por cliente, con líneas/comprobantes/NC/neto consolidado y motivo |
| `conciliacion_11T_detalle_072026.csv` | cliente × titular × SKU, con capa de match y estado contra el maestro |
| `conciliacion_11T_cliente_titular_072026.csv` | consolidado cliente × titular con umbral y cumplimiento |
| `resumen_11T_por_titular_072026.csv` | los 11 titulares: objetivo, CCC Orbit, CCC solo matriz, cobertura 3/6, `mod_11t_acum` |
| `resumen_11T_por_vendedor_072026.csv` | matriz vendedor × titular |

Ningún archivo de `01_INPUTS` fue modificado. Ningún archivo de código fue modificado.
