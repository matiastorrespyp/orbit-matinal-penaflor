# Mapa de Datos — PAV Matinal Peñaflor

Trazabilidad completa: fuente real → script generador → dataset intermedio → endpoint Flask → variable JS → KPI visible.

---

## Flujo general

```
01_INPUTS/                              →  LEGACY/orbit_matinal_v42.py  →  04_DATASETS_ORBIT/
  ventas.csv            ← OPERACIÓN DIARIA / SEGUIMIENTO MENSUAL VIVO        mod_volumen_vendedor.csv
  ventas_mes.csv        ← CIERRE MENSUAL CONGELADO                           mod_ccc_segmento.csv
  ventas_acumuladas.csv ← 11T (período comercial completo)                   mod_11_titulares.csv
  clientes.xlsx                                                               clientes_dia.csv
  resultado.xlsx        ← OBJETIVOS / RECHAZOS
  04D_MAESTRO_PRODUCTOS_PENAFLOR.xlsx  ← clasificación sell out (ambos) — CONGELADO, 258 cods
  RAW_PRODUCTOS/productos<mes>.xlsx     ← COMPLETA el 04D (339 cods) — obligatorio subirlo cada mes

04_DATASETS_ORBIT/   →  server_orbit.py (Flask)             →  PAV MATINAL PE_A FLOR/
  + 01_INPUTS/                                                  portal.html / index.html
    ventas.csv             → Sell Out dashboard / CCC Día / CCC Mes / Alertas día
    ventas_mes.csv         → Sell Out cierre / Dormidos / Planes AS
    ventas_acumuladas.csv  → 11T
    clientes.xlsx          → cartera real
```

### Regla de fuentes por indicador (resumen)

| Indicador | Fuente ventas | Fuente clasificación | Filtro fecha |
|---|---|---|---|
| Sell Out litros (dashboard) | ventas.csv | **04D + RAW_PRODUCTOS/productos<mes>.xlsx** | Período vigente |
| Sell Out litros (cierre mes) | ventas_mes.csv | **04D + RAW_PRODUCTOS/productos<mes>.xlsx** | Mes cerrado |
| Acciones del mes + buscador producto→acción | ventas.csv | **04D + RAW_PRODUCTOS/productos<mes>.xlsx** | Mes vivo |
| CCC Día | ventas.csv | _clasificar_segmento() | Último día operativo |
| CCC Mes | ventas.csv | _clasificar_segmento() | Mes calendario |
| 11T CCC vs objetivo | ventas_acumuladas.csv | objetivo 11T.xlsx | **Sin filtro — acumulado completo** |
| Acumulado $ vendedor | resultado.xlsx | — | Período ERP |
| Alertas día | ventas.csv + acciones comerciales mes.xlsx | — | Último día operativo |
| Acciones cierre | ventas_mes.csv + acciones comerciales mes.xlsx | — | Mes cerrado |
| Dormidos | ventas_mes.csv + clientes.xlsx + historial_ventas_cliente.csv | — | Mes cerrado |
| Planes AS | ventas_mes.csv + reconocimiento de planes as.xlsx + escala_junio.xlsx | — | Mes cerrado |

---

## KPIs principales — trazabilidad por KPI

### Acumulado compañía / por vendedor
| Campo | Fuente | Script | Dataset | Endpoint | Variable JS |
|-------|--------|--------|---------|----------|-------------|
| acumulado_mes | resultado.xlsx / mod_volumen_vendedor | orbit_matinal_v42.py | mod_volumen_vendedor.csv | /api/dashboard → kpis.acumulado | vendedores[i].acumulado |
| objetivo_mes | resultado.xlsx / mod_volumen_vendedor | orbit_matinal_v42.py | mod_volumen_vendedor.csv | /api/dashboard → kpis.objetivo | vendedores[i].objetivo |
| avance_pct | calculado en motor | orbit_matinal_v42.py | mod_volumen_vendedor.csv | /api/dashboard → kpis.avance_pct | vendedores[i].avance |

**Advertencia:** `avance_pct` en el motor puede ser Avance bruto. En el portal se muestra como "Tendencia %". Verificar fórmula.

---

### CCC Compradores Mes
| Campo | Fuente correcta | Flujo |
|-------|----------------|-------|
| ccc_total | `ventas.csv` (mes actual, ImporteNetoItem > 0) | `_cargar_ventas_mes_actual()` → `_ccc_mes_por_vendedor()` → `/api/dashboard` → `kpis.ccc_total` |
| ccc_tradicional | ventas.csv, segmento TRADICIONAL | mismo flujo |
| ccc_autoservicio | ventas.csv, segmento AUTOSERVICIO (0 para V3) | mismo flujo |
| ccc_onpremise | ventas.csv, segmento ON_PREMISE_VTK | mismo flujo |

**Total compañía (2026-05-15):** 311 compradores  
**V3:** 79 total, 0 autoservicio ✓

**Fuente PROHIBIDA para CCC Mes:** `clientes_dia.ccc_mes_flag` — incluye historial con posible mezcla de meses.

---

### CCC Día
| Campo | Fuente | Dataset | Endpoint |
|-------|--------|---------|----------|
| ccc_dia_total | mod_ccc_segmento.clientes_con_compra | 04_DATASETS_ORBIT/mod_ccc_segmento.csv | /api/dashboard → kpis.ccc_dia_total |

**Total compañía (2026-05-15):** 37 compradores ayer  

---

### Clientes planificados Vi / Sin compra Vi
| Campo | Fuente | Dataset | Endpoint | Estado |
|-------|--------|---------|----------|--------|
| clientes_total (tC) | mod_volumen_vendedor.clientes_planificados | mod_volumen_vendedor.csv | /api/dashboard → kpis.clientes_total | OK — son los 548 clientes de zona Vi |
| clientes_pendientes (tP) | mod_volumen_vendedor.clientes_sin_compra_mes | mod_volumen_vendedor.csv | /api/dashboard → kpis.clientes_pendientes | DESFASADO — motor usa historial sin filtro estricto de mes |

**Nota:** `clientes_sin_compra_mes` puede incluir clientes que compraron en abril como "ya compraron". Valor actual: 290 de 548. Se muestra como número crudo sin porcentaje hasta recalcular desde ventas.csv + clientes.xlsx.

---

### Cartera real
| Campo | Fuente | Uso |
|-------|--------|-----|
| cartera_real_total | clientes.xlsx (sin V2/V5) | /api/diagnostico → cartera_real_total = 2045 |
| cartera por segmento | clientes.xlsx clasificado por Ramo/Subramo | /api/diagnostico → segmentos[i].clientes |

**Segmentos (2026-05-15):** TRAD=1609, AS=272, OP=155, OTROS=9

---

### Cobertura por segmento (ayer)
| Campo | Fuente | Endpoint | Estado |
|-------|--------|----------|--------|
| cubiertos | mod_ccc_segmento.coberturas_logradas | /api/diagnostico → segmentos[i].cubiertos | OK — es ayer |
| clientes (denominador) | clientes.xlsx (cartera real) | /api/diagnostico → segmentos[i].clientes | OK — cartera real desde Etapa A |

**No hay % de cobertura en el dashboard principal.** Pendiente: calcular cobertura real desde ventas.csv mes actual.

---

### Cobertura acumulada del mes — drill-down por vendedor + faltantes
*(2026-06-18 — desplegado en Render)*

Tarjeta **"📊 Cobertura acumulada del mes"**. Mide cobertura sobre el período **acumulado** (no el día). Un cliente está *cubierto* si `cant_base_acum >= umbral` del segmento (3 botellas Tradicional, 6 en AS/On Premise/Mayorista). V3 sin AUTOSERVICIO.

| Campo | Fuente | Script | Dataset | Endpoint |
|-------|--------|--------|---------|----------|
| cubiertos / cartera / pct_cobertura (agregado por vendedor×segmento) | clientes.xlsx (cartera) + ventas acum (CantBase, ImporteNetoItem>0) | `generar_cobertura_acum()` | `mod_cobertura_acum.csv` | `/api/gerencia/cobertura_acum` (por_vendedor[].segmentos) |
| **clientes faltantes** (cubierto=0) por vendedor×segmento, con nombre+localidad | mismo `merged` que calcula `cubierto` | `generar_cobertura_acum()` | **`mod_cobertura_acum_detalle.csv`** | `/api/gerencia/cobertura_acum_faltantes?segmento=X` |
| cobertura propia del vendedor por segmento + faltantes (solo sus datos) | los 2 datasets anteriores | — | — | `/api/vendedor/<vid>/cobertura_acum` |

**Consistencia garantizada:** `sin_cobertura` (agregado) == nº filas del detalle por vendedor×segmento.

**Portal (`portal.html`):**
- Dashboard gerencia (`gCobSegToggle`/`gCobFaltToggle`): clic en segmento → vendedores (cubiertos/cartera/%) → faltantes. Faltantes con **lazy fetch + caché** (`_cobFaltFetch`, `window.__cobFalt[seg]`); cubiertos/cartera salen de `D.cob_acum.por_vendedor` (ya en cliente).
- Pantalla Vendedores 360 (`gVendCobToggle`): "Cobertura acumulada por segmento" expandible a faltantes (reusa el mismo fetch/caché).
- Perfil del vendedor (`vKpis` + `vCobToggle`): tarjeta propia; faltantes vienen embebidos en `D.cob_acum_v` (cargado en `loadRole`, sin fetch extra al expandir).

**Regla de oro:** los faltantes deben salir de la fuente **acumulada** (`mod_cobertura_acum_detalle.csv`), NO de `clientes_dia.cobertura_mes_flag` (ese es mes vivo y daría otro número).

---

### Ruta del vendedor (perfil vendedor → pestaña Ruta)
*(2026-06-18)*

`/api/vendedor/<id>/ruta` (fuente: clientes.xlsx + ventas.csv mes vivo + mod_innovaciones_segmento.csv):
- **Orden de visita**: clientes ordenados por la columna `Orden` de clientes.xlsx (asc); `Orden<=0`/vacío van al final. `Orden` está poblado ~60% (V3/V6/V10 casi completos, V7/V9 casi vacíos).
- **11 Titulares por cliente**: `titulares_comprados` + `titulares_faltantes` (de ventas.csv mes vivo, Peñaflor, sin V1/V2/V5/V20). En el portal: chip colapsable "11 Titulares x/11" → pills verde (comprado) / amarillo (faltante).
- **Innovaciones por cliente**: catálogo desde `mod_innovaciones_segmento.csv` (por segmento), compras desde ventas.csv por `Codigo`. Chip colapsable "Innovaciones y/N" verde/amarillo. Solo TRAD/AS; V3 sin AS.
- V3: ruta filtrada a Tradicional almacén/despensa/kiosco (ver [[REGLAS_NEGOCIO_PAV]]).

---

### 11 Titulares
*(Auditoría y corrección 2026-06-18/19 — desplegado en Render)*

**REGLA DE MEDICIÓN (corregida contra el reporte oficial de la empresa):**
1. **Solo Peñaflor** → `Empresa == 'Empresa'`. Se EXCLUYE `P&P LOGISTICA S.R.L`. `ventas_acumulada.csv` y `ventas.csv` MEZCLAN ambos distribuidores (~60% Peñaflor / ~40% P&P). **Contar P&P era el error**: inflaba el CCC ~15-35%.
2. **Solo vendedores de ruta** → excluir `V1, V2, V5, V20` (`_VENDEDORES_EXCLUIDOS = {1,2,5,20}`). V20 = depósito; V1 no es de ruta.
3. **Período = TRIMESTRE calendario en curso** (ene-mar / abr-jun / jul-sep / oct-dic), arranca de cero al cambiar de trimestre. En el vivo se filtra por `FechaComprobante >= inicio del trimestre`.
4. **CCC = clientes únicos** con compra válida (neto>0) por marca titular (nunique de Cliente).

**Todos los puntos de lectura del 11T (deben usar el mismo criterio):**

| Tarjeta / vista | Endpoint / fuente | Estado |
|---|---|---|
| Dashboard "11T · CCC vs Objetivo" | `/api/gerencia/once_titulares` ← ventas_acumulada.csv | ✓ Peñaflor + trimestre + V1 |
| Dashboard "11T · CCC zona del día" | `/api/gerencia/once_titulares_zona` ← ventas_acumulada.csv | ✓ Peñaflor + trimestre + V1 |
| Dashboard per-vendedor "11T ✓" | kpis.once_titulares_cumplidos ← `mod_11t_acum.csv` | ✓ Peñaflor (generador) + V1 |
| Gerencia 11T acum | `/api/gerencia/11t_acum` ← `mod_11t_acum.csv` | ✓ |
| Perfil vendedor "11 Titulares · clientes vendidos" | `/api/vendedor/<id>` → titulares11 ← `mod_11t_acum.csv` | ✓ |
| Ruta del vendedor "11 Titulares x/11" | `/api/vendedor/<id>/ruta` ← ventas.csv (mes vivo) | ✓ Peñaflor + V1 |
| Cierre de mes 11T | `_cierre_once_titulares` ← ventas_acumulada_<MMAAAA>.csv | ✓ Peñaflor |

`mod_11t_acum.csv` lo genera `generar_11t_acum` (cobertura con mínimo de botellas por cartera, métrica distinta del nunique de la tarjeta) y filtra Peñaflor.

**Validación vs reporte empresa (trimestre abr-jun):** total 4435 vs 4574 (−3%); 8/11 marcas en ±5% (Antares −1.3%, Smirnoff Ice −2.6%, Alma Mora −3%, Alaris −4.4%, Dada +4.7%).

**Residual NO reconciliado (decisión: dejar así):** Finca Las Moras −12%, Trapiche Reserva +16%, Gordon's −17%. Se descartó con datos que sea P&P, depósito (V20, +1 cli) o segmentos. `01_INPUTS/producto activos.xlsx` (mapeo oficial artículo→Línea Comercial) confirma que el mapeo de ORBIT es correcto y además **está incompleto** (faltan ~140 artículos vendidos reales: ALARIS D.Cosecha, DADA Lata, LOS ARBOLES Bco Dulce, ANTARES latas…), por eso NO se reemplazó el mapeo por código. Cerrar esas 3 marcas requeriría el detalle cliente-nivel de la empresa.

---

### Botellas
| Campo | Estado |
|-------|--------|
| botellas_dia | mod_ccc_segmento.botellas_vendidas — OK (ayer) |
| botellas_mes | NULL — eliminado. Antes venía de clientes_dia Vi solamente (absurdo: 15628 < 16674 botellas_dia) |

---

## Archivos de entrada — estado

| Archivo | Ruta | Fuente | Actualización | Estado |
|---------|------|--------|---------------|--------|
| ventas.csv | 01_INPUTS/ | ERP Peñaflor | Diaria / Mes vivo | CCC Día, CCC Mes, Sell Out dashboard, Alertas día |
| ventas_mes.csv | 01_INPUTS/ | ERP Peñaflor | Cierre mensual congelado | Sell Out cierre, Dormidos, Planes AS, Acciones cierre |
| ventas_acumuladas.csv | 01_INPUTS/ | ERP Peñaflor | Acumulado período completo | Fuente exclusiva 11T |
| clientes.xlsx | 01_INPUTS/ | Maestro clientes | Periódica | OK — 2045 clientes |
| resultado.xlsx | 01_INPUTS/ | ERP objetivos | Mensual | OK — objetivos, acumulado de ventas y rechazos |
| producto activos.xlsx | 01_INPUTS/ | Catálogo | Periódica | ❌ NO usar — misma lista vieja que el 04D (257 cods) y cubre menos ventas |
| productos<mes>.xlsx | 01_INPUTS/RAW_PRODUCTOS/ | Maestro de productos del mes | **Mensual — obligatorio** | OK — 339 cods, completa el 04D (2026-07-14) |

---

## Datasets intermedios — estado

| Dataset | Generado por | Fuente | Estado |
|---------|-------------|--------|--------|
| mod_volumen_vendedor.csv | orbit_matinal_v42.py | resultado.xlsx + ventas | PARCIAL — `clientes_sin_compra_mes` desfasado (Etapa B) |
| mod_ccc_segmento.csv | orbit_matinal_v42.py | ventas ayer | OK para CCC Día |
| mod_11_titulares.csv | orbit_matinal_v42.py | ventas + maestro productos | OK para 11T — denominar correctamente |
| clientes_dia.csv | orbit_matinal_v42.py | clientes.xlsx filtrado zona | OK para lista Vi — NO usar ccc_mes_flag ni cobertura_mes_flag como fuente principal |

---

## Endpoints Flask — estado

| Endpoint | Estado | Fuente CCC Mes | Notas |
|----------|--------|----------------|-------|
| /api/diagnostico | OK (Etapa A) | ventas.csv | cartera_real_total=2045, botellas_mes=null |
| /api/dashboard | OK (Etapa 1) | ventas.csv | CCC Mes=311, CCC Día=37 |
| /api/vendedor/v3 | OK (Etapa 1) | ventas.csv | ccc_total=79, ccc_auto=0 |
| /api/clientes | DESFASADO PARCIAL | clientes_dia.ccc_mes_flag | Usado para lista Clientes Críticos, no para KPI cards |
| /api/alertas | Pendiente auditar | mod_alertas_descuentos | — |
| /api/planificacion | OK — SQLite | orbit.db | — |
| /api/gerencia/plan_cobertura | OK | padrón `Plan cobertura/*.xlsx` (2 hojas) + maestro + historial encadenado | Caché por mtime; cada PDV trae `clave` estable. `altas_fuera` = hoja "altas fuera del listado"; altas contadas por cliente vs objetivo 60 a dic-2026. Ver [[BITACORA_2026-08-05]] |
| /api/gerencia/plan_cobertura/notas | OK — SQLite | orbit.db (`plan_cob_nota`) | Mensaje por PDV, clave = `PDV:<ID PUNTO DE VENTA>`, o `CLI:<código>` en las altas fuera del listado; vacío = borra. Ver [[BITACORA_2026-08-03]] |
| /api/vendedor/&lt;vid&gt;/plan_cobertura | OK | mismo payload cacheado de gerencia | Filtra las 5 listas por `vendedor_id` (capturados y altas fuera = su cartera; el resto, sus localidades). V3 → `no_aplica` |

---

## Portal — variables JS principales

| Variable | Alimentada por | Etiqueta actual | Estado |
|----------|---------------|-----------------|--------|
| tO | sum(kpis.objetivo) | Objetivo compañía | OK |
| tA | sum(kpis.acumulado) | Acumulado compañía | OK |
| avG | tA/tO*100 | Tendencia % | OK (etiqueta corregida Etapa A) |
| tCCC | sum(kpis.ccc_total) | CCC Compradores Mes | OK (311, ventas.csv) |
| tCCC_DIA | sum(kpis.ccc_dia_total) | CCC Día | OK (37) |
| tC | sum(kpis.clientes_total) | Planificados Vi | OK — son 548 Vi clientes |
| tP | sum(kpis.clientes_pendientes) | Sin compra Vi | DESFASADO fuente — mostrar sin % |
| cobG | 1 - tP/tC | (eliminada de display) | Calculada pero no renderizada (Etapa A) |
