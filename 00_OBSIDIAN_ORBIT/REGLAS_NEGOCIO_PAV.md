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

### EMPRESA — solo Peñaflor (regla agregada 2026-06-18)
`ventas.csv` y `ventas_acumulada.csv` MEZCLAN dos distribuidores en la columna `Empresa`: `'Empresa'` (Peñaflor, ~60%) y `'P&P LOGISTICA S.R.L'` (~40%). **Todos los KPIs de Peñaflor deben filtrar `Empresa == 'Empresa'`** y excluir P&P. No filtrarlo infla los conteos ~15-35% (fue la causa raíz del sobreconteo del 11T). Ya lo aplican: FARO, cierre, 11T (card/zona/ruta/generador) e **Innovaciones** (segmento + plan AS + oportunidades, ambos perfiles; impacto −25% en clientes_compraron).

### V3 — Nadia Gambino — SOLO Tradicional almacén/despensa/kiosco
V3 trabaja **únicamente** el canal Tradicional, subsegmentos **Almacén / Despensa / Kiosco** (NO Autoservicio, NO On Premise/Vinoteca, NO Mayorista, NI tradicionales que no sean almacén/despensa/kiosco como fiambrería/panadería). Aplica a **TODO su perfil** (ampliado 2026-06-18):
- CCC (mes/día), cobertura, 11T, objetivos, Plan vs Real, planificación: AS=0 y On Premise=0; cobertura acumulada solo TRADICIONAL almacén/despensa/kiosco.
- **Ruta** (`/api/vendedor/V3/ruta`): whitelist por SubSegmento ALMACEN/DESPENSA/KIOSCO.
- **Clientes** (`/api/clientes` + `_clientes_por_dia`): sin clientes no-tradicionales.
- **Acciones comerciales**: solo acciones que aplican a tradicional almacén/kiosco; las de AS/OP/Mayorista/Vinoteca no se le muestran.
- **Incentivo FARO**: solo categoría tradicional (Alaris+FLM); ocultas Antares y Familia Smirnoff (AS).
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

---

## Cobertura

### Mínimos por segmento para considerar "cubierto"
| Segmento | Botellas mínimas |
|----------|-----------------|
| Tradicional / Almacén / Kiosco | 3 |
| Autoservicio | 6 |
| On Premise / Vinoteca | 6 |

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

---

## Sell Out — fuentes y cálculo

### Regla de fuente — OBLIGATORIA

**Fuente de ventas — Dashboard:** `01_INPUTS/ventas.csv` (operación diaria / seguimiento mensual vivo). Excluir V2, V5, V20.

**Fuente de ventas — Cierre de mes:** `01_INPUTS/ventas_mes.csv` (cierre mensual congelado). Excluir V2, V5, V20.

**Fuente de categoría/segmento/litros por unidad (ambos contextos):** `01_INPUTS/04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx` (header fila 4, hoja Hoja1). Cruce por `Codigo` del artículo.

Función en código: `_cargar_maestro_04D()` + `_sellout_desde_ventas(df)` + `_preparar_df_ventas(path)` en `server_orbit.py`.

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

### Mapa Segmento 04D → Sub-bucket VDA

| Segmento maestro | Sub-bucket |
|---|---|
| Alto | Alto |
| Medio Alto | Medio Alto |
| Superior | Superior |
| Medio / Vinos de Mesa | Medio |
| Nacional | Spirits Nacionales |
| Importados | Spirits Importados |

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

---

## Segmentos — clasificación

Función: `_clasificar_segmento(ramo, subsegmento)` en `server_orbit.py`.

| Segmento | Palabras clave en Ramo/Subramo |
|----------|-------------------------------|
| AUTOSERVICIO | AUTOSERVICIO, CADENA REGIONAL, SAR, LARGE FORMAT, PROXIMITY, CASH&CARRY, MAYORISTA |
| ON_PREMISE_VTK | ON PREMISE, AWAY FROM HOME, VINOTECA, BAR, RESTAURANT, ESTACION DE SERVICIO, CATERING |
| TRADICIONAL | TRADITIONAL TRADE, ALMACEN, DESPENSA, KIOSCO, MAXIKIOSCO, FIAMBRERIA, PANADERIA |
| OTROS | Todo lo que no clasifica arriba |

**Despensa = Almacén (regla agregada 2026-06-13):** dentro de TRADICIONAL, el subcanal *Despensa* se trata igual que *Almacén* en **todas** las estadísticas. En el motor de acciones se canoniza `despensa → almacén` (`_ACC_SUBSEG_TRAD` y el `_subseg` de la venta en `_acc_preparar_ventas`). Una acción acotada a "almacén/kiosco" también cubre despensa. El resto del sistema ya colapsaba almacén/despensa/kiosco en TRADICIONAL por igual.

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
