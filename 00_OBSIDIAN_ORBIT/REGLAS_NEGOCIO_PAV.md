# Reglas de Negocio — PAV Matinal Peñaflor

Fuente de verdad para cálculos comerciales. Toda lógica en scripts, endpoints y portal debe respetar estas reglas sin excepción.

---

## Vendedores

### Activos Peñaflor
V3, V4, V6, V7, V8, V9, V10

### Excluidos — siempre
V1, V2, V5 y V20 se excluyen de **todos** los reportes, filtros, sumas y denominadores. `_VENDEDORES_EXCLUIDOS = {1, 2, 5, 20}` (server) y `VENDEDORES_EXCLUIDOS = {1,2,5,20}` (generador).
- En `ventas.csv` / `ventas_acumulada.csv`: filtrar `CodVendedor not in {1, 2, 5, 20}`.
- En `clientes.xlsx`: filtrar `CodVendedor not in {1, 2, 5, 20}`.
- **V20 = DEPOSITO**: venta directa de depósito, no es vendedor de ruta. **V1**: no es vendedor de ruta (agregado 2026-06-18; se colaba en el 11T en vivo).

### EMPRESA — se mide SIEMPRE con las dos razones sociales (regla corregida 2026-07-13)
**NUNCA filtrar por la columna `Empresa`.** `P&P LOGISTICA S.R.L` **NO es otro distribuidor: es nuestra segunda razón social.** La columna `Proveedor` es `GRUPO PEÑAFLOR SA` en el **100%** de las filas de ventas, facture quien facture. **Todo lo que medimos es con ambas empresas** (confirmado por el usuario 2026-07-13).

**Esta regla reemplaza a la del 2026-06-18** ("solo Peñaflor, excluir P&P"), que era incorrecta:
- Filtrar `Empresa == 'Empresa'` **borraba a los clientes facturados vía P&P**: en julio 2026, **135 de los 229 clientes con compra**. Rutas enteras se caían — **V6 perdía 30 de sus 34 clientes (88%)** y **V10, 35 de 40**.
- Parecía validar en junio porque **la razón social "Empresa" era la que facturaba a casi todos** (8.558 filas vs 5.762 de P&P) y ningún cliente se caía del CCC. En julio **el mix se dio vuelta** (P&P 630 vs Empresa 421) y el CCC se partió al medio.
- **La razón social que emite la factura no puede decidir si el cliente cuenta.**

**Qué rompía (medido, antes → después de sacar el filtro):**
| Métrica | Antes | Real |
|---|---|---|
| 11T — Alma Mora | 29 | **75** (Peñaflor reporta 55) |
| 11T — Smirnoff Ice | 9 | **48** |
| CCC empresa — Tradicionales | 79 | **194** |
| Acciones — inversión real | $4.267.780 | **$5.205.236** |
| Innovaciones — CCC | 45 | **90** (V10: 2 → 15) |

**Dónde está escrita la regla:** bloque **`_LEEME_EMPRESA`** en `server_orbit.py`, junto a `_VENDEDORES_EXCLUIDOS`. Se eliminó el filtro de los **13 puntos** que lo tenían: 11T (`once_titulares`, `once_titulares_zona`, `_leer_ventas_acum_cierre`, `_cierre_once_titulares`, `generar_11t_acum`), `gerencia_ccc_empresa`, `_acc_preparar_from_df` (acciones + alertas de descuentos), `vendedor_ruta`, `vendedor_oportunidades_innovacion`, `gerencia_cierre_mes`, `_cierre_ccc_por_vend_segmento`, `generar_innovaciones_segmento`, `generar_innovaciones_plan_as`. **Sell out y cobertura nunca filtraron — ya estaban bien.**

**Si aparece un `Empresa == 'Empresa'` nuevo en el código, es un bug.** Única excepción legítima: un corte donde la razón social **es** el dato pedido (ej. conciliar facturación por entidad).

### V3 — Nadia Gambino — Tradicional completo + Proximity
V3 trabaja el canal **Tradicional completo** y **Proximity** (NO Autoservicio, NO On Premise/Vinoteca, NO Mayorista). Aplica a **TODO su perfil** (ampliado 2026-06-18):

> **Corregido 2026-07-30:** antes esto decía "sólo almacén/despensa/kiosco" y había una lista blanca por SubSegmento en `generar_cobertura_acum()`. Esa lista se comía las **carnicerías, verdulerías y panaderías** de su ruta, que son tradicionales y que V3 **sí** atiende: su cartera pasó de 268 a 293 clientes. Alcanza con el segmento (`TRADICIONAL`), que ya excluye AS / On Premise / Mayorista. Las estaciones de servicio (canal Proximity) también son suyas: 8 clientes. En el motor son las constantes `_V3_SEGMENTOS` y `_V3_SUBCANALES`, no listas sueltas repetidas.
- CCC (mes/día), cobertura, 11T, objetivos, Plan vs Real, planificación: AS=0 y On Premise=0; cobertura acumulada solo TRADICIONAL almacén/despensa/kiosco.
- **Ruta** (`/api/vendedor/V3/ruta`): whitelist por SubSegmento ALMACEN/DESPENSA/KIOSCO.
- **Clientes** (`/api/clientes` + `_clientes_por_dia`): sin clientes no-tradicionales.
- **Acciones comerciales**: solo acciones que aplican a tradicional almacén/kiosco; las de AS/OP/Mayorista/Vinoteca no se le muestran.
- **Incentivo FARO**: solo la(s) categoría(s) de canal **Tradicional** (hoy Smirnoff Ice); ocultas las de Autoservicio.
- **Alertas**: solo de clientes Tradicional almacén/despensa/kiosco.
- **Portal**: pestaña "Plan AS" oculta para V3; casillas AS/On Premise ocultas en "CCC por Segmento".

---

## CCC — Compradores con compra neta

**Definición:** Cliente único con al menos una línea de venta con `ImporteNetoItem > 0`.

### Tipos — no mezclar nunca

| Tipo | Fuente | Período | Filtro |
|------|--------|---------|--------|
| CCC Compradores Mes | `ventas.csv` | Mes calendario actual (datos acumulados del mes vivo) | ImporteNetoItem > 0, sin V2/V5 |
| CCC Día | `ventas.csv` | Último día operativo | ImporteNetoItem > 0, sin V2/V5 |
| CCC Ruta | Cruce de ventas.csv con clientes.xlsx | Mes actual | Solo clientes en maestro |

### Reglas de cálculo
- Deduplicar por `Cliente` dentro del período (un cliente = un CCC aunque tenga muchas líneas).
- Para CCC por segmento: clasificar por `Ramo` + `Subramo` de ventas.csv usando `_clasificar_segmento()`.
- V3: `ccc_autoservicio = 0` independientemente de los datos.

### CCC total empresa vs objetivo — tile gerencia (2026-07-06)
- Endpoint `GET /api/gerencia/ccc_empresa` (reescrito). **Real:** `ventas.csv` (mes vivo), neto>0, solo Peñaflor, excluye V1/V2/V5/V20; clientes únicos por canal.
- **5 canales** clasificados por **Ramo + Subramo** (helper `_canal_ccc_empresa`): `Tradicionales` (default) · `Autoservicios` · `On Premise` · `Vinotecas` · `On Premise Noche`. `Mayoristas` es canal aparte y **queda fuera** de los canales con objetivo.
- ⚠️ **CORREGIDO 2026-07-20:** hasta esa fecha esta regla decía que el Subramo "Autoservicio Tradicional" contaba como **Tradicional** porque el objetivo se habría definido por Ramo. **Era falso.** Bajo ese criterio la cartera entera de AS eran 18 clientes contra un objetivo de 145 (imposible), y la tarjeta mostró **Autoservicios 5/145 = 3.4%**. El objetivo 145 corresponde a la clasificación por **Subramo** (cartera 199) — la misma del 11T y de `mod_cobertura_acum.csv`. Ya **no** hay dos definiciones: AS se identifica por Subramo en todo el sistema. Ver [[BITACORA_2026-07-20]].
- **Objetivo:** `01_INPUTS/objccc.xlsx`. Hoja `total` (canal → objetivo, helper `_objetivos_ccc_empresa`): On Premise 30 / Vinotecas 15 / On Premise Noche 11 / Autoservicios 145 / Tradicionales 845 = **1046**. Hojas `autoservicio` / `tradicional` / `On premise`: **apertura por vendedor** (helper `_objetivos_ccc_vendedor`), sin encabezado real → se parsea buscando la celda `V<n>` en cada fila, nunca por posición de columna.
- ⚠️ **Objetivo Tradicional 845 vs 809:** el Total declarado en la hoja es 845 pero los 7 vendedores suman 809. AS y OP cierran exacto. **Sin resolver** — la tarjeta usa 845 y muestra los 36 sin asignar de forma explícita.
- **El total de empresa suma sólo los canales con objetivo** (numerador y denominador miden lo mismo). Antes era `nunique()` global e incluía clientes sin objetivo en el numerador.
- Portal: kcard "CCC Compradores Mes" muestra `real / objetivo · %` + card "📊 CCC del Mes · real vs objetivo" por canal.

---

## Cobertura

### Mínimos por segmento para considerar "cubierto"
| Segmento | Botellas mínimas |
|----------|-----------------|
| Tradicional / Almacén / Kiosco | 3 |
| Autoservicio | 6 |
| On Premise / Vinoteca | 6 |
| Proximity (estaciones de servicio) | 6 |
| Mayorista | 6 |

### Reglas de denominador
- El denominador **siempre** debe ser explícito: ¿cuántos clientes del universo definido?
- **Cartera total**: 2045 clientes de `clientes.xlsx` (sin V2/V5).
- **Cartera Vi**: 548 clientes planificados para la zona Vi del día operativo.
- Nunca mezclar numerador de ayer con denominador de otra zona o período.

### Prohibiciones
- No mostrar `%` de cobertura si el denominador es `clientes_dia.csv` (solo Vi) y el numerador es del mes.
- No llamar "Cobertura General" a un cálculo sobre la zona Vi.
- No usar `cobertura_mes_flag` de `clientes_dia.csv` como numerador principal — incluye historial con posible mezcla de meses.

---

## 11 Titulares

- 11T cuenta **marcas/impactos**, no clientes únicos.
- `once_titulares_cumplidos` puede ser mayor que CCC porque un cliente puede tener múltiples marcas cubiertas.
- Etiquetar siempre como "Marcas 11T cubiertas" o "Impactos 11T", nunca como "Clientes".
- `once_titulares_total` = cantidad de combinaciones cliente-marca objetivo (no = cantidad de clientes).

### Regla de fuente y período — OBLIGATORIA (corregida 2026-06-18 vs reporte empresa)

**Fuente:** `01_INPUTS/ventas_acumulada.csv`.

**Filtros obligatorios:**
1. `Empresa == 'Empresa'` → solo Peñaflor, EXCLUIR P&P Logística (era el sobreconteo ~15-35%).
2. Excluir `CodVendedor in {1,2,5,20}`.
3. **Período = TRIMESTRE calendario en curso** (ene-mar / abr-jun / jul-sep / oct-dic). Arranca de cero al cambiar de trimestre (en julio → solo jul en adelante). En el vivo se filtra `FechaComprobante >= inicio del trimestre`.
4. CCC = clientes únicos (neto>0) por marca titular (nunique de Cliente).
5. **SUPERFICIE (2026-07-06): el 11T se mide SOLO en Autoservicio + Almacén + Kiosco.** Helper `_mask_superficie_11t(df)` (fail-open si falta Ramo/Subramo). INCLUYE: Ramo `AUTOSERVICIO` **o** Subramo con "AUTOSERVICIO" (cuenta **"Autoservicio Tradicional"** — autoservicios chicos bajo Ramo `TRADITIONAL TRADE`, confirmado con el usuario) + Subramo Almacén/Despensa (o Ramo `ALMACENES`) + Subramo Kiosco/Maxikiosco. EXCLUYE On Premise, Vinotecas, Away From Home, Mayoristas, Cash&Carry, Fiambrería/Carnicería/Panadería y resto tradicional sin formato self-service. Aplicado en las 4 mediciones vivas. (Antes no filtraba superficie → inflaba con On Premise/Vinotecas/etc.)

**Por qué trimestre:** confirmado por el usuario el 2026-06-18. (Antes esta regla decía "archivo completo sin filtro de fecha" / "bimestral" — ambos incorrectos.)

**Nunca usar:**
- `ventas_mes.csv` como única fuente de 11T del vivo (es 1 mes).
- Sumar P&P Logística ni V1/V20.
- `producto activos.xlsx` como única fuente de mapeo marca→artículo (está incompleto, faltan ~140 artículos vendidos reales).

**Fuente de objetivos:** `01_INPUTS/objetivo 11T.xlsx` (hoja con columnas: Linea comercial, Objetivo).

**Residual sin reconciliar (dejado así 2026-06-18):** tras los filtros, el total queda −3% vs la empresa (8/11 marcas ±5%). Finca Las Moras (−12%), Trapiche Reserva (+16%) y Gordon's (−17%) difieren por cómo la empresa agrupa artículos puntuales; no es error sistemático nuestro. Cerrarlo requiere su detalle cliente-nivel.

**Las 11 marcas con objetivo** (únicas que se reportan):
Alma Mora · Trapiche Reserva · Finca Las Moras · Alaris · Don David · Dada · Smirnoff Flavours · Los Arboles · Antares · Smirnoff Ice · Gordon's Flavours

**Métrica correcta del cierre:** CCC por marca (clientes únicos que compraron esa marca en el período) vs objetivo CCC. No es % de combinaciones.

**Match SKU→marca por CÓDIGO (2026-07-06):** la asignación de cada venta a su marca titular es por **Código Art. exacto** (matriz `01_INPUTS/11 titulares autoservicio/11_titulares_autoservicios_match_codigos.xlsx`, hoja `DETALLE_SKU_11T_AS`, 82 SKUs) como fuente **primaria**; el match por texto de `Marca` queda como **fallback** (todas las variedades de una marca suman a la misma marca — Opción A). Aplicado en las 4 rutas vivas de `server_orbit.py` (`gerencia_once_titulares`, `once_titulares_zona`, snapshot de `gerencia_cierre_mes`, `_cierre_once_titulares`) y en `tools/generar_cierre_mensual.py` (`_marca_11t`). Helper `_codigos_11t_map()`/`_marca_11t_por_codigo()`. Los drill-down `11t_empresa`/`11t_vendedor` (legacy `mod_11_titulares.csv`) NO migraron. Sin el xlsx en Render → cae al match por texto (no rompe).

---

## Sell Out — fuentes y cálculo

### Regla de fuente — OBLIGATORIA

**Fuente de ventas — Dashboard:** `01_INPUTS/ventas.csv` (operación diaria / seguimiento mensual vivo). Excluir V2, V5, V20.

**Fuente de ventas — Cierre de mes:** `01_INPUTS/ventas_mes.csv` (cierre mensual congelado). Excluir V2, V5, V20.

**Fuente de categoría/segmento/litros por unidad (ambos contextos):** `01_INPUTS/04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx` (header fila 4, hoja Hoja1) — en producción se lee su versión liviana `09_CONFIG/maestro_04D_productos.csv`. Cruce por `Codigo` del artículo. **Se COMPLETA con el maestro del mes** (ver regla siguiente).

Función en código: `_cargar_maestro_04D()` + `_sellout_desde_ventas(df)` + `_preparar_df_ventas(path)` en `server_orbit.py`.

### El maestro 04D se COMPLETA con el maestro del mes — OBLIGATORIA (2026-07-14)

El 04D quedó **congelado en 258 códigos** y le faltan **82 SKU vigentes que sí se venden** (Alaris D.Cosecha, Dada Sweet Red, Los Arboles Rosado, Smirnoff BC, Trapiche, Finca Las Moras…). La fuente actualizada es el export mensual **`01_INPUTS/RAW_PRODUCTOS/productos<mes>.xlsx`** (339 códigos, cubre 127/128 de lo vendido, mismo vocabulario de Categoría/Segmento, y además trae `Estado`).

**Regla:** el **04D manda donde tiene dato**; el archivo del mes **solo agrega los códigos faltantes y rellena campos vacíos**. Implementado en `_maestro_mes_productos()` → usado por `_cargar_maestro_04D_uncached()` (`server_orbit.py`) y por `cargar_maestro_productos()` (`generar_datasets_acum.py`). Resultado: **340 códigos**, todos con litros/caja.

**Por qué es obligatoria** — un código ausente del maestro sale con `_cat = NaN`, `_linea = ""` y sin litros/caja, y entonces:
- no matchea las **reglas por categoría** de las acciones (no suma clientes ni inversión),
- se **descarta** del sell out (`Categoria.notna()`),
- aporta **0 litros**,
- y dispara **falsas alertas de descuento** ("máximo 0% — sin acción aplicable").

En julio 2026 eran **60 líneas / $1.386.829 (2,1% del importe)**, una categoría entera fuera del sell out (Vodka) y **11 alertas falsas**.

**Consecuencia operativa:** hay que **subir el export de productos todos los meses** a `01_INPUTS/RAW_PRODUCTOS/`. Si falta el del mes, se usa el más reciente por mtime (fail-safe), pero los SKU nuevos quedan sin clasificar.

**`producto activos.xlsx` NO sirve para esto:** es la misma lista vieja (257 códigos) y cubre **menos** ventas que el 04D (115/128 vs 118/128).

**Spirits en el maestro 04D:**
Los spirits (códigos 30xxx de Diageo/P&P) **sí están** en el maestro 04D con `Categoria = 'Spirits'` (42 productos). El campo `Segmento` del maestro clasifica directamente en `'Nacional'` o `'Importados'`. El cruce por `Código Art.` funciona igual que para vinos — no se necesita fallback por `Rubro` ni por keywords de nombre.

**Nunca usar:**
- `ventas_acumuladas.csv` para sell out (dashboard → `ventas.csv`, cierre → `ventas_mes.csv`)
- El campo `Rubro` de ventas.csv como fuente primaria de categoría — usar siempre el maestro 04D (aplica también a spirits)
- El campo `Linea` de ventas.csv para determinar el tier/sub-bucket
- El maestro `producto activos.xlsx` para esta clasificación (usar solo `04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx`)

### Flujo de clasificación por artículo

1. Leer `Codigo` de ventas.csv → cruzar con `Código Art.` del maestro 04D
2. Si match (vinos, spirits, RTD, etc.): tomar `Categoria` del maestro → bucket · `Segmento` del maestro → sub-bucket · `Lts x caja / UxC` → lxu
3. Si sin match (código desconocido / no está en 04D): `Rubro` de ventas.csv → bucket como fallback. Registrar en log para auditar.
4. Litros = `CantBase × lxu` (primario) → fallback `PesoKg` → fallback inferencia del nombre (regex `6X750` → 0.75L)

### Mapa Categoria 04D → Bucket sell out

| Categoria maestro | Bucket |
|---|---|
| Vinos del año / Vinos de Mesa | VINOS DEL AÑO |
| Vinos de guarda | VINOS DE GUARDA |
| Espumantes / Sidra | CHAMPAÑA |
| Cerveza Artesanal | CERVEZA ARTESANAL |
| RTD (S) / RTD | RTD |
| Spirits (Bodega: Whisky / Whisky Maltas / Gin / Ron / Vodka / Licores / Bourbon) | SPIRITS |

> **RTD vs RTD (S) (2026-06-19):** son categorías distintas (RTD = base vino, Frizze / Dada Tinto de Verano; RTD (S) = base spirits, Smirnoff Ice / Gordon's / SMF Bitter Citric). En la tarjeta se anidan bajo la madre "RTD" porque `OBJSELLOUT.xlsx` les da un Total combinado (9.056 L = rtd 4.028 + rtd (s) 5.028). El **sub-split** RTD vs RTD (S) usa la `Categoria` cruda del maestro 04D. **Ojo:** un SKU que NO esté en el maestro entra a RTD sólo por `Rubro` y, sin subtipo, cae por defecto en RTD regular. Por eso se cargaron al maestro `35108` (SMF BC → RTD (S)) y `14620` (Frizze Manxana → RTD). Mantener el maestro completo evita este leak.

### Mapa Segmento 04D → Sub-bucket VDA

| Segmento maestro | Sub-bucket |
|---|---|
| Alto | Alto |
| Medio Alto | Medio Alto |
| Superior | Superior |
| Medio / Vinos de Mesa | Medio |
| Nacional | Spirits Nacionales |
| Importados | Spirits Importados |

> **Finca Las Moras "FFL" (Fair For Life), cod `74721`/`74722` = `Alto` a propósito (2026-06-19).** Es la línea premium; el resto de Finca Las Moras es `Medio Alto`. Confirmado por el usuario: NO reclasificar.
>
> **Tarjeta Sell Out (UI):** cada categoría/subcategoría muestra columna **Faltan (L)** = `max(objetivo − real, 0)` y hay **fila TOTAL** al pie (suma Real / Objetivo / Faltan + avance). Las marcas abren con 1 click más el desglose por **varietal** (SKU) en litros (`_marcas_de_grupo` → `varietales`).

### Objetivos sell out (hardcoded de imagen obj sell out.jpeg)

| Categoría | Objetivo L | Sub-buckets |
|---|---|---|
| VINOS DEL AÑO | 19.015 | Alto: 11.792 · Medio Alto: 4.651 · Superior: 2.171 · Medio: 401 |
| VINOS DE GUARDA | 678 | — |
| SPIRITS | 17.752 | Nacionales: 17.045 · Importados: 707 |
| RTD | 9.999 | — |
| CHAMPAÑA | 686 | — |
| CERVEZA ARTESANAL | 405 | — |

---

## Incentivo Club FARO

**Definición 100% desde la hoja** (refactor 2026-07-06): TODO se lee de `01_INPUTS/incentivo_club_faro*.xlsx` vía **`_faro_config()`** en `server_orbit.py` (cacheado por mtime) — categorías, canal, umbral, **códigos de SKU**, tope por cliente, período (meses), objetivos por vendedor, premios y supervisores. **Ya no hay nada hardcodeado.** El usuario cambia el incentivo editando SOLO el Excel (y recommiteándolo para Render). **Logrado y no-compradores:** `ventas_acumulada.csv` filtrado a los meses del período (de la hoja), solo Peñaflor (`Empresa=='Empresa'`), excl V2/V5/V20. Match de producto **por CÓDIGO de SKU**. Funciones `_faro_config` / `_faro_ventas(cfg)` / `_faro_detalle_vendedor(df,cod,cfg)`; endpoints `/api/gerencia/incentivo_faro` y `/api/vendedor/<id>/incentivo_faro` (exponen `categorias_orden`+`categorias_meta`; front data-driven).

**Conteo:** cobertura **por SKU** — cada SKU participante con **≥ umbral botellas** del PDV suma 1 cobertura; se suman por cliente; el tope por cliente sale de la hoja ("N máximo").

**Bimestre vigente julio-agosto 2026** (histórico: mayo-junio era Alaris+FLM / Antares por-SKU-con-doble / Familia Smirnoff, matcheado por texto):

| Categoría | Canal | Umbral | SKUs | Premio |
|---|---|---|---|---|
| **Smirnoff Ice** | Tradicional (kiosco+almacén) | 3 bot/SKU | 35103/35104/35105 | 2000 millas |
| **Vinos Red Blends** | Autoservicio | 6 bot/SKU | 80089/74684/44395/71716/74735/42376/74737 | 1000 |
| **Familia Gordons** (x700) | Autoservicio | 6 bot/SKU (tope 3/cli) | 30139/30075/30134 | 1000 |

> Smirnoff Ice se vende en pack de 6 → siempre supera el mínimo 3 (confirmado usuario 2026-07-06). Supervisores: **Esteban** = V3,V4,V6,V8,V10; **Raúl** = V7,V9 (leídos de la hoja). Requisitos de layout de la hoja para el parser: ver `NEXT_TASK.md`.

---

## Plan Cobertura (On Premise B&C)

Plan de Grupo Peñaflor para subir cobertura en **restaurantes y bares con carta** de categoría **B y C**. Medición oficial: **CCC únicos On Premise B&C, julio a diciembre 2026**. Fuente: `01_INPUTS/Plan cobertura/*.xlsx`, que el negocio edita a mano y viaja con el cierre (el PDF de la carpeta es la mecánica). Pantalla de gerencia + pestaña 🍽️ Cobertura del vendedor.

**El padrón tiene DOS hojas** (2026-08-05):

| Hoja | Qué trae | Cómo se usa |
|---|---|---|
| Padrón relevado | 203 PDV, columna `¿LO ATIENDE?` + `CÓD. CLIENTE` | Capturados (Sí + código), atendidos sin código, potenciales, no atendidos |
| `altas fuera del listado` | Clientes dados de alta durante el plan que no estaban relevados | Tarjeta propia; se miden igual que los capturados |

**Objetivo: 60 altas a diciembre 2026** (`PLAN_COB_OBJETIVO_ALTAS`). Es meta **del equipo**, no está repartida por vendedor.

**Las altas se cuentan por CLIENTE, no por fila** — y no es un detalle: el padrón repite PDV con el mismo código (1195, 1417) y hay clientes cargados en las dos hojas (1409). Contar filas daría 27 en vez de **24**. Misma regla para `con_recompra`, que cubre **todas** las altas (padrón + fuera del listado), no sólo los capturados.

**Activación = fecha de la PRIMERA compra** del cliente, sin corte de fecha; recompra = mes con compra posterior al de activación. Sólo líneas con importe > 0 (un sin cargo o una devolución no activan).

**Vendedor de un PDV**: si el cliente está en el maestro, manda **la cartera real**; el número de la planilla es fallback. Para los PDV que no son clientes, el vendedor se sugiere por zona: el que más clientes tiene en esa localidad, y si no tenemos ninguno, el dominante del partido. **V3 queda fuera de ese cálculo** (no trabaja On Premise) y el plan entero le devuelve `no_aplica`.

**Descarga Excel por tarjeta** (2026-08-06): cada una de las 5 listas tiene su `⬇ Excel`. Los dos bloques de clientes dados de alta traen además la facturación **abierta por comprobante** (hoja `Comprobantes`, una fila por factura) y el **detalle línea por línea** (hoja `Detalle`). Los otros tres bloques no tienen `cliente_id` → bajan sólo el listado; una hoja de facturación vacía se leería como "no compraron", que es distinto de "no se puede medir".

> **El número de comprobante no está en todas las fuentes.** Lo traen las 3 con formato ERP; `historial_ventas_cliente.csv` no. Por eso **2026-05 y 2026-06 salen como `(sin comprobante en la fuente)`** (54 de 329 líneas): es el tramo que sólo existe en ese archivo. El resto se recupera del duplicado que sí lo trae. Etiquetado explícito, nunca en blanco.

**Los sin cargo de los combos del plan (importe 0) van al Excel marcados** en la columna `Tipo`, y `Comprobantes` separa botellas compradas de botellas sin cargo: mezclados, las botellas del Excel no cierran contra las de la tarjeta. Y **la facturación se emite una vez por `cliente_id`** — misma trampa que obligó a contar las altas por cliente y no por fila.

> Detalle de implementación y validación en [[BITACORA_2026-08-06]] (export Excel), [[BITACORA_2026-08-05]] (altas fuera del listado y objetivo), [[BITACORA_2026-08-03]] (buscador y mensajes por PDV) y [[MAPA_DATOS_PAV]].

---

## Alertas, Acciones Comerciales y Planes AS — fuentes

| Indicador | Fuente ventas | Fuente complementaria | Período |
|-----------|--------------|----------------------|---------|
| Alertas día | `ventas.csv` | `acciones comerciales mes.xlsx` | Último día operativo |
| Acciones cierre | `ventas_mes.csv` | `acciones comerciales mes.xlsx` | Mes cerrado |
| Dormidos | `ventas_mes.csv` | `clientes.xlsx` + `historial_ventas_cliente.csv` | Mes cerrado |
| Planes AS | `ventas_mes.csv` | `reconocimiento de planes as.xlsx` + `escala_junio.xlsx` | Mes cerrado |

**Regla:**
- Indicadores del **día** → `ventas.csv`.
- Indicadores de **cierre/mes congelado** → `ventas_mes.csv`.
- Nunca usar `ventas.csv` para cierres ni planes (no es cierre congelado).

### Plan Frío (Planes AS)

Plan frío = **1 Six Pack de Smirnoff ICE en lata SIN CARGO** por cliente listado en la hoja `plan frío` de `sincargos<mes>.xlsx`. El "entregado" se detecta en `ventas.csv` por una línea 100% descuento del producto, **mirando el `Articulo`, NO la `Marca`**.

> **Las latas Smirnoff BC (Bitter Citric, COD 35108/35109) NO son plan frío** — pertenecen a una acción comercial del mes. En el ERP tienen `Marca='Smirnoff Ice Flavours'` (engañoso), pero su `Articulo` dice **"BC"**, no **"ICE"**. La detección filtra `Articulo` con `ICE` + (`SMIRNOFF`|`SMF`), así que las BC y la botella Smirnoff 700 (escala) quedan afuera. Antes se detectaba por Marca e inflaba el "entregado" (regla corregida 2026-06-22). Código: `generar_planes_as` en `generar_datasets_acum.py` → `mod_planes_as.csv` (`pf_enviado`/`pf_estado`) + `mod_sincargos_envios.csv`.

---

## Segmentos — clasificación

**Son CUATRO clasificadores espejo y tienen que dar el mismo resultado.** Chequeo: clasificar los 2.139 clientes de `clientes.xlsx` con los cuatro y exigir **0 discrepancias**.

| Archivo | Función | Alimenta |
|---------|---------|----------|
| `server_orbit.py` | `_clasificar_segmento()` | el portal (CCC del mes, tarjetas, acciones) |
| `generar_datasets_acum.py` | `_clasificar()` + `_clasificar_subcanal()` | cobertura, innovaciones, 11T, acciones |
| `LEGACY/orbit_matinal_v42.py` | `clasificar_segmento_operativo()` | `mod_ccc_segmento.csv` = **el CCC del DÍA** |
| `tools/generar_cierre_mensual.py` | `_seg()` | el cierre de mes |

| Segmento | Palabras clave |
|----------|----------------|
| MAYORISTA | MAYORISTA(S), CASH&CARRY |
| AUTOSERVICIO | AUTOSERVICIO, CADENA REGIONAL, **CADENAS REGIONALES**, SAR, LARGE FORMAT, TIENDA DE BEBIDAS |
| PROXIMITY | PROXIMITY, ESTACION DE SERVICIO |
| ON_PREMISE_VTK | ON PREMISE, AWAY FROM HOME, VINOTECA, BAR, RESTAURANT, CATERING, EVENTOS, TEMPORADA |
| TRADICIONAL | TRADITIONAL TRADE, ALMACEN, DESPENSA, KIOSCO, **KIOSK**, MAXIKIOSCO, FIAMBRERIA, CARNICERIA, GRANJA, PANADERIA, CASA DE PASTAS, **VERDULERIA** |
| OTROS | Todo lo que no clasifica arriba (empleados, consumidor final) |

### El SubSegmento MANDA sobre el Ramo (regla general, 2026-07-30)

Orden obligatorio: **Mayorista → Autoservicio → Proximity → SubSegmento solo (OP, después Trad) → recién ahí el Ramo como fallback**.

El ERP mete carnicerías, verdulerías, panaderías y casas de pastas bajo `Ramo = AWAY FROM HOME`. Mirando Ramo y SubSegmento a la vez, el Ramo ganaba y **57 clientes tradicionales se medían como On Premise**: se les exigía 6 botellas de cobertura en vez de 3. Es la generalización de la regla de Autoservicio de más abajo, que arreglaba el mismo problema sólo para AS.

**Grafías del ERP:** `KIOSKO` con K no estaba en las claves y esos clientes caían en **OTROS**, que no es ningún subcanal de las tarjetas → quedaban fuera de todo.

**Falsos positivos por substring:** `CADENAS REGIONALES (BAR)` es un **formato de supermercado grande**, no un bar (el `(BAR)` matcheaba la clave `BAR`). Se resuelve en el bloque de Autoservicio, que corre antes — **no** sacando la clave `BAR`, porque `Ramo = BAR` existe y es un bar real, igual que `RESTAURANT CON BARRA`.

### PROXIMITY — canal propio (decisión del negocio 2026-07-30)

Las **32 estaciones de servicio** no son On Premise ni Autoservicio: canal propio, **umbral 6 botellas**, **V3 sí lo trabaja**, **fuera del 11T** (que se mide en AS + Almacén + Kiosco) y **sin objetivo** en `objccc.xlsx`.

**Al agregar un canal, el riesgo no es clasificar: es que se pierda en los totales.** Varios lugares sumaban `TRAD + AS + OP (+ OTROS)` con lista fija y el canal nuevo desaparecía sin aviso. Hay que revisar: `_ccc_mes_por_vendedor`, `ccc_total`/`ccc_dia_total` (dashboard y ficha de vendedor), `SEGMENTOS_POSIBLES` de `real_ayer_segmento`, el ranking de gerencia, el cierre mensual, `_acc_seg_canon` (una acción **sin canal declarado** dejaba afuera al canal nuevo) y `_COB_SEG_ORDER` en `portal.html`.

**Despensa = Almacén (regla agregada 2026-06-13):** dentro de TRADICIONAL, el subcanal *Despensa* se trata igual que *Almacén* en **todas** las estadísticas. En el motor de acciones se canoniza `despensa → almacén` (`_ACC_SUBSEG_TRAD` y el `_subseg` de la venta en `_acc_preparar_ventas`). Una acción acotada a "almacén/kiosco" también cubre despensa. El resto del sistema ya colapsaba almacén/despensa/kiosco en TRADICIONAL por igual.

### Autoservicio se identifica por SUBRAMO, no por Ramo (corregido 2026-07-20)

`AUTOSERVICIO TRADICIONAL` es **el grueso del canal** (764 de 826 filas de venta AS) y tiene `Ramo = TRADITIONAL TRADE`. Clasificar autoservicio mirando sólo `Ramo` lo manda entero a Tradicionales.

Cómo se detectó y cómo verificarlo: bajo el criterio Ramo la cartera **completa** de Autoservicios era de **18 clientes**, contra un objetivo de **145**. Un objetivo mayor que la cartera del canal es **aritméticamente imposible** → no es un problema comercial, es un error de clasificación. La tarjeta "CCC del Mes" mostró **Autoservicios 5/145 = 3.4%** durante ese período.

**Regla:** todo clasificador de canal debe mirar `Subramo`/`SubSegmento` como fuente primaria para AUTOSERVICIO. Vale para `_clasificar()` de `generar_datasets_acum.py` (siempre lo hizo bien) y para `_canal_ccc_empresa()` de `server_orbit.py` (corregido).

**Mayorista / Cash&Carry nunca es Autoservicio** — es canal propio y `objccc.xlsx` no lo abre, así que queda **fuera** de los canales con objetivo, nunca sumado a AS ni a Tradicional.

**Chequeo antes de dar por buena una métrica nueva:** comparar el objetivo del canal contra la **cartera** de ese canal. Si el objetivo es mayor, la clasificación está mal.

---

## Semanal — apertura del mes en 4 semanas

Semana = bloque de días del mes: **S1 1-7 · S2 8-14 · S3 15-21 · S4 22-fin**. Siempre 4, así los meses se comparan entre sí sin ajustes.

| KPI | Qué mide | % de la semana |
|-----|----------|----------------|
| Facturación | Suma de `ImporteNetoItem` por `FechaComprobante` | sobre el total facturado del mes |
| Litros | Suma de `_litros_por_linea` (04D → PesoKg → nombre) | sobre el total de litros del mes |
| CCC (Trad / AS / OP) | **Aporte incremental**: el cliente cuenta en la semana de su **primera** compra del mes | sobre el CCC del mes |

El CCC es incremental a propósito: contando el CCC bruto semanal, un cliente que compra dos semanas contaría dos veces y las 4 semanas pasarían el 100%, que no es lo que se planifica.

### Cada KPI se mide en el universo de SU objetivo (regla 2026-08-06)

**`universo` es un campo de cada KPI (`_SEMANAL_KPIS` → `_SEMANAL_UNIVERSO`), no un filtro global de la pantalla.** Si el real y el objetivo no cuentan el mismo universo, el avance es falso.

| KPI | Universo | Por qué |
|-----|----------|---------|
| **Litros** | **`empresa`** — ruta + V1/V20 Depósito, sin las bajas V2/V5 | *"La planificación semanal es sobre toda la venta semanal"*. Además es el universo de su objetivo (el TOTAL del Sell Out, que agrupa ruta + Depósito) |
| Facturación | `ruta` — sin V1/V20 | Su objetivo es la suma de `ValorObjetivo` **de la ruta** en `resultado.xlsx` |
| CCC | `ruta` — sin V1/V20 | `objccc.xlsx` se mide sin Depósito en todo el portal (ver `ccc_empresa`) |

**No es un detalle chico:** el Depósito pesa **16% en julio, 24% en junio y 30% en mayo** de los litros. Medir litros de ruta contra un objetivo de empresa hundía el avance de forma sistemática. Sobre un mes parcial la brecha parece ~1,4% y engaña — verificar siempre contra meses cerrados.

Implementación: `_semanal_leer` conserva las filas del Depósito marcadas con **`es_ruta=False`** en vez de descartarlas, y `_semanal_agg` manda cada KPI a su universo. Una sola lectura sirve a los dos (el historial de 63 MB no se parsea dos veces). Exclusiones desde `motor_11t.VENDEDORES_BAJA` / `VENDEDORES_DEPOSITO`, sin duplicar la regla.

### Objetivo de litros = el TOTAL de la tarjeta de Sell Out (2026-08-06)

**Un solo objetivo de litros en todo el portal.** `_semanal_objetivos` reusa `_cargar_objetivos_sellout()` —la fuente de esa tarjeta— y suma por categoría igual que el front. Verificado que los dos caminos dan el mismo número (**60.597 L**): no hay una segunda copia que se pueda desfasar, y al actualizar `OBJSELLOUT.xlsx` las dos pantallas se mueven solas.

> **Ojo:** `OBJSELLOUT.xlsx` se carga a mano cada mes. Si no lo actualizaron, la pantalla Semanal **y** la tarjeta de Sell Out muestran el objetivo del mes anterior — las dos, no una sola.

Control julio-2026: **50.047 L logrados vs 60.597 L = 82,6%**, y esos 50.047,0 L son exactamente el mismo número que da el universo de la tarjeta de Sell Out.

> Detalle e implementación en [[BITACORA_2026-08-06]].

---

## Períodos — separación obligatoria

Nunca presentar un KPI sin especificar a qué período corresponde.

| Etiqueta a usar | Período real | Fuente |
|-----------------|-------------|--------|
| Día / Ayer | Último día operativo | `ventas.csv` |
| Mes (seguimiento vivo) | Mes calendario en curso | `ventas.csv` |
| Cierre mes (congelado) | Mes cerrado definitivo | `ventas_mes.csv` |
| Período 11T (trimestre) | Trimestre calendario en curso (abr-jun…) | `ventas_acumulada.csv` filtrado a Peñaflor + trimestre |
| Objetivos / Acumulado / Rechazos | Período ERP | `resultado.xlsx` |
| Zona Vi | Día de visita viernes | `clientes_dia.csv` |
| Cartera total | Maestro estático | `clientes.xlsx` |

---

## Avance vs. Tendencia

| Campo | Fórmula | Etiqueta correcta |
|-------|---------|------------------|
| Avance % | `acumulado_mes / objetivo_mes * 100` | "Avance %" |
| Tendencia % | `(acumulado / días_corridos) * días_totales / objetivo * 100` | "Tendencia %" |

El portal muestra **Tendencia** (proyección al cierre del mes), no el avance bruto.
Si `avance_pct` viene de `mod_volumen_vendedor.csv`, verificar qué fórmula usó el motor antes de mostrarlo.

---

## Calendario comercial

- Días hábiles del mes: calculados por `contar_dias_habiles()` en `server_orbit.py`.
- Días corridos: días hábiles desde el día 1 del mes hasta la fecha de ejecución.
- Días restantes: días hábiles totales − días corridos.
- Fuente: `09_CONFIG/feriados.csv` si existe; sino, lunes a viernes sin feriados.
