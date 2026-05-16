# Reglas de Negocio — PAV Matinal Peñaflor

Fuente de verdad para cálculos comerciales. Toda lógica en scripts, endpoints y portal debe respetar estas reglas sin excepción.

---

## Vendedores

### Activos Peñaflor
V3, V4, V6, V7, V8, V9, V10

### Excluidos — siempre
V2 y V5 se excluyen de **todos** los reportes, filtros, sumas y denominadores.
- En `ventas.csv`: filtrar `CodVendedor not in {2, 5}`.
- En `clientes.xlsx`: filtrar `CodVendedor not in {2, 5}`.
- En datasets intermedios: verificar que no incluyan filas de V2/V5.

### V3 — Nadia Gambino
- No trabaja el canal Autoservicio.
- `ccc_autoservicio = 0` en todos los endpoints y datasets.
- `trabaja_autoservicio = false` en todos los endpoints.
- Excluir Autoservicio de objetivos, cobertura y 11 Titulares para V3.
- Si un segmento de V3 figura como Autoservicio en ventas.csv, igualmente contar como 0 en sus métricas.

---

## CCC — Compradores con compra neta

**Definición:** Cliente único con al menos una línea de venta con `ImporteNetoItem > 0`.

### Tipos — no mezclar nunca

| Tipo | Fuente | Período | Filtro |
|------|--------|---------|--------|
| CCC Compradores Mes | `ventas.csv` | Mes calendario actual (día 1 al último día con datos) | ImporteNetoItem > 0, sin V2/V5 |
| CCC Día | `mod_ccc_segmento` (columna `clientes_con_compra`) | Último día operativo | Sin V2/V5 |
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

---

## Segmentos — clasificación

Función: `_clasificar_segmento(ramo, subsegmento)` en `server_orbit.py`.

| Segmento | Palabras clave en Ramo/Subramo |
|----------|-------------------------------|
| AUTOSERVICIO | AUTOSERVICIO, CADENA REGIONAL, SAR, LARGE FORMAT, PROXIMITY, CASH&CARRY, MAYORISTA |
| ON_PREMISE_VTK | ON PREMISE, AWAY FROM HOME, VINOTECA, BAR, RESTAURANT, ESTACION DE SERVICIO, CATERING |
| TRADICIONAL | TRADITIONAL TRADE, ALMACEN, DESPENSA, KIOSCO, MAXIKIOSCO, FIAMBRERIA, PANADERIA |
| OTROS | Todo lo que no clasifica arriba |

---

## Períodos — separación obligatoria

Nunca presentar un KPI sin especificar a qué período corresponde.

| Etiqueta a usar | Período real | Fuente |
|-----------------|-------------|--------|
| Mes | Mes calendario actual | `ventas.csv` filtrado |
| Día / Ayer | Último día operativo | `mod_ccc_segmento` |
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
