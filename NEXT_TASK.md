# NEXT TASK - ORBIT MATINAL PEÑAFLOR

## Próxima tarea — sesión 2026-05-05

### Bloque A — Requiere datos externos (ERP)
**Actualizar `clientes.xlsx` con clientes de V7 y V9.**
Causa raíz: `codven=7` y `codven=9` ausentes del maestro. Sin esto, el motor legacy no genera rutas ni métricas de cobertura para estos vendedores.
- Clientes de V7: `7898`, `7931`, `1210`
- Clientes de V9: `1094`, `1285`, `8125`, `1362`, `1387`, `8010`, `769`, `388`, `8139`, `1089`, `1093`
- Datos necesarios por cliente: `Razon_Social`, `Ramo`, `DiasVisita`, `Localidad`, `SubSegmento`

### ~~Bloque B~~ — ✓ Completado 2026-05-06
Eliminados todos los datos hardcodeados del frontend (`dashboard.jsx` y `app.jsx`):
- `cccSpark` → `null`; Sparkline CCC → `null`
- `"Cierre proyectado al 30/05"` → `cierreProyectado` calculado desde `data.fechaCorta`
- `"MR"` / `"Manuel R."` → `"SV"` / `"Supervisor"`
- `"Vista mobile · Milagros Ortega"` → `"Vista mobile · vendedor"` (hallazgo adicional)

### ~~Incorporación V7/V9 al maestro~~ — ✓ Completado 2026-05-06
clientes.xlsx actualizado manualmente (+302 V7, +355 V9). Pipeline motor→adaptador re-ejecutado.
- Fallback `sin_maestro` de server_orbit.py ya no se activa para V7/V9 (tienen filas reales en mod_volumen_vendedor).
- Deuda menor: 2 clientes V7 y 8 clientes V9 sin `DiasVisita` en clientes.xlsx.
- `acciones_comerciales.csv` pendiente de integración (bloque separado).

### ~~Bloque C~~ — ✓ Completado 2026-05-06
`ventas_mes` ahora se construye desde `historial_ventas` (acumulado) en lugar de `ventas_validas` (solo 2 días).
- `importe_mes > 0`: 175/255 clientes MI (antes: 0/255)
- Suma importe_mes: $26.608.333
- `ventas_ayer` sin cambios (correcto)

### ~~Bloque D~~ — ✓ Completado 2026-05-06
`server_orbit.py` expone `segmentos` y `titulares11` desde CSVs reales; `data.js` los consume vía `diag.*`.
- `segmentos`: TRADICIONAL 330 clientes / 12 cubiertos; AUTOSERVICIO 40 / 12; ON_PREMISE_VTK 30 / 1
- `titulares11`: 28 marcas, top Alma Mora 66/398, Cazador 19/353
- `ccc_mes: 0` permanece honesto — sin fuente de CCC acumulado disponible en ningún CSV actual

### ~~Bloque E~~ — ✓ Completado 2026-05-06 (registrado, sin integrar consumidor)
- `acciones_comerciales.csv` restaurado a texto CSV real (8 filas, configuración de alertas para `config_comercial.py`).
- `reglas_acciones_mayo_2026_orbit.csv` creado: 31 reglas comerciales Mayo 2026 (descuentos por canal/categoría/cantidad).
- `reglas_acciones_mayo_2026_orbit.json` y `acciones_mayo_2026_formato_gastos_orbit.xlsx` trackeados.

### ~~Bloque F~~ — ✓ Completado 2026-05-06
`calcular_descuento_maximo()` ahora lee `reglas_acciones_mayo_2026_orbit.csv` como fuente primaria.
- AS + VDA + 1–9 cajas → 6.0% (`MAY26-GRAL-AS-VIN-001`) en lugar de 10.0% hardcodeado.
- `mod_alertas_descuentos`: 103 filas (antes: 14). 91/103 con `fuente_regla = MAY26-...`.
- Fallback hardcodeado activo para productos/segmentos sin cobertura en CSV (12 filas).

### ~~Bloque G~~ — ✓ Completado 2026-05-06
`mod_gastos_accion` generado en `MATINAL_PENA_V42.xlsx` y exportado a `04_DATASETS_ORBIT/` por `datasets_orbit.py`.
- 26 filas (fuente_regla × vendedor), 0 NaN/Inf, `gasto_real > gasto_teorico` garantizado.
- Mayor exceso: `MAY26-GRAL-TRAD-SPI-LOC-001` V10 → $83.166 | `MAY26-GRAL-AS-VIN-001` V9 → $58.982.
- Diagnóstico clave: `valor_descuento` ERP = por unidad (no por línea); correcto es `× cant_base`.
- Sin consumidor en portal todavía — deuda separada.
- ~~**Días hábiles**~~: ✓ Resuelto en commit `ef59d83`.

### Bloque H — Pendiente

#### ~~DiasVisita gaps~~ — ✓ Resuelto 2026-05-07
10 clientes sin `DiasVisita` en `clientes.xlsx` (V7: 2, V9: 8). Todos cerrados formalmente.

**10 casos cerrados — excluidos de todo análisis comercial:**
- `402` – CONSUMIDOR FINAL, V7, Ruta=DEPOSITO VILLA DOLORES: placeholder de venta directa, no es cliente de ruta. En `clientes_excluidos.csv` + regla dinámica.
- `20001`–`20038` (8 empleados V9, Ramo=Empleados, Ruta=BEBIDAS VD, Frecuencia=Eventual): compras vía DEPOSITO (codven=20), no visitas programadas. En `clientes_excluidos.csv`.
- `8614` – BUSTAMANTE JUAN, V7, Ruta=DEPOSITO VILLA DOLORES, sin ventas activas ni historial: excluido por CSV + regla dinámica. Commit `fe913dd`.

**Regla dinámica activa:** todo cliente con Ruta que contiene "DEPOSITO" y sin `DiasVisita` queda excluido automáticamente en `cargar_clientes()`, sin necesidad de estar en el CSV.

#### ~~Consumidor `mod_gastos_accion`~~ — ✓ Completado 2026-05-06
`/api/gastos_accion` expuesto en `server_orbit.py` (commit `4867990`).
- `resumen`: exceso total $231.133, 4 vendedores alertados, 26 filas, 18 acciones CSV + 8 fallback.
- `top_acciones`: top 5 por exceso_pesos agrupado por accion_id.
- `top_vendedores`: top 5 — V10 Ortega $93.169, V9 Sánchez $81.043.
- `detalle`: 26 filas completas. Sin NaN. Sin cambios a endpoints existentes.
- Pendiente: consumo desde `data.js` para vista gerencial del portal.

#### ~~`data.js` → portal gerencial~~ — ✓ Completado 2026-05-06
`window.ORBIT_DATA.gastosAccion` disponible. Dashboard muestra 3 cards al final:
resumen (exceso total, gasto real, vendedores, clientes), top 5 acciones y top 5 vendedores.
Se oculta automáticamente si no hay datos. Commit `c3f7813`.

#### ~~Clientes no comerciales excluidos formalmente~~ — ✓ Completado 2026-05-07
`09_CONFIG/clientes_excluidos.csv` (10 filas) + regla dinámica por Ruta DEPOSITO sin DiasVisita. Commits `97993d2`, `fe913dd`.
- Excluidos por CSV: `402`, `20001`, `20008`, `20011`, `20021`, `20027`, `20029`, `20031`, `20038`, `8614`
- Regla dinámica en `cargar_clientes()`: Ruta contains DEPOSITO & DiasVisita vacío → excluido automáticamente
- Validación: ninguno de los 10 en `mod_alertas_descuentos`, `clientes_dia` ni outputs post-regeneración.

#### Pendientes adicionales Bloque H
- **`02_PLANTILLA_GASTOS` del Excel**: pendiente de integración si se necesitan gastos proyectados vs. reales desde la plantilla original.

---

## Problemas pendientes detectados en auditoría (2026-05-05)

1. **V7 y V9 ausentes** en datasets (ver arriba).
2. **Días hábiles en `server_orbit.py`** no excluye feriados → `/api/diagnostico` devuelve total=26/corridos=4 en vez de 24/3.
3. **Acumulado=0** en `dashboard_vendedor.json` → `app_publish.py` busca columna `acumulado` pero `mod_volumen_vendedor.csv` tiene `acumulado_mes` → retorna 0 para todos.
4. **Datos hardcodeados** en frontend: sparkline CCC en `dashboard.jsx` (mock inventado), usuario "Manuel R." en sidebar de `app.jsx`.
5. **`orbit_portal_data.json`** tiene estructura distinta a la que genera `tools/orbit_truth_audit.py` — fue generado por otra herramienta anterior.
6. ~~**Importes = 0 en clientes_dia.csv**~~ → ✓ Resuelto (Bloque C + botellas expuestas en commit `c1124b5`). `importe_mes > 0` en 199/400 clientes. `botellas_dia=1406`, `botellas_mes=9050` en `kpisGerencia`.
7. **`ccc_mes: 0`** en `data.js` — correcto y honesto pero pendiente: necesita fuente real de CCC acumulado del mes (no existe en ningún CSV actual).
8. **Segmentos `cubiertos: 0`** hardcodeados en `data.js` — los datos existen en `mod_ccc_segmento.csv` pero no se cruzan con el total de clientes del universo.
9. **`titulares11` incompleto** en `data.js` — solo 2 de 11 hardcodeados; los reales están en `mod_11_titulares.csv` pero no se mapean al array.

## Resueltos en esta sesión (2026-05-05)
- ✓ `data.js` restaurado como JavaScript válido (era código Python).
- ✓ `diaActivo` ahora se calcula desde `fecha_corte + 1 día` → "MI".
- ✓ Título de la matinal en `app.jsx` ahora es dinámico → "Miércoles 06/05".
- ✓ `ccc_dia` ahora toma el valor real de `mod_ccc_segmento`; `ccc_mes` queda en 0 (honesto).
- ✓ `acumulado=0` corregido en `app_publish.py`: `"acumulado_mes"` agregado como primer candidato en `build_avance_map()`.
- ✓ V7 y V9 visibles en `/api/dashboard` con fallback desde `resultado.xlsx` (`sin_maestro: true`). Deuda: actualizar `clientes.xlsx`.
