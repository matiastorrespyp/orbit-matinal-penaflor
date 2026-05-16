# Mapa de Datos — PAV Matinal Peñaflor

Trazabilidad completa: fuente real → script generador → dataset intermedio → endpoint Flask → variable JS → KPI visible.

---

## Flujo general

```
01_INPUTS/           →  LEGACY/orbit_matinal_v42.py  →  04_DATASETS_ORBIT/
  ventas.csv                                              mod_volumen_vendedor.csv
  clientes.xlsx                                           mod_ccc_segmento.csv
  resultado.xlsx                                          mod_11_titulares.csv
  producto activos.xlsx                                   clientes_dia.csv

04_DATASETS_ORBIT/   →  server_orbit.py (Flask)       →  PAV MATINAL PE_A FLOR/
  + 01_INPUTS/                                            data.js (fetch sync)
    ventas.csv (CCC Mes directo)                          portal.html / index.html
    clientes.xlsx (cartera real)
```

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

### 11 Titulares
| Campo | Fuente | Dataset | Endpoint |
|-------|--------|---------|----------|
| once_titulares_cumplidos | mod_11_titulares.tiene_flag (sum) | mod_11_titulares.csv | /api/dashboard → kpis.once_titulares_cumplidos |
| once_titulares_total | mod_11_titulares (count filas por vendedor) | mod_11_titulares.csv | /api/dashboard → kpis.once_titulares_total |

**Advertencia:** `once_titulares_total` para V3 = 11 marcas × 42 clientes Vi = 462 combinaciones. No es un conteo de clientes.

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
| ventas.csv | 01_INPUTS/ | ERP Peñaflor | Diaria | OK — fuente primaria CCC Mes |
| clientes.xlsx | 01_INPUTS/ | Maestro clientes | Periódica | OK — 2045 clientes |
| resultado.xlsx | 01_INPUTS/ | ERP objetivos | Mensual | OK — objetivos y acumulado |
| producto activos.xlsx | 01_INPUTS/ | Catálogo | Periódica | Pendiente auditar |

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
