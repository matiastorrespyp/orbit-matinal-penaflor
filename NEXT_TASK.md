# NEXT TASK - ORBIT MATINAL PEÑAFLOR

## Estado sesión 2026-05-07 — Auditoría portal

### Commits realizados en esta sesión
| Hash | Descripción | Archivo(s) |
|---|---|---|
| `7a4f7e8` | `/api/clientes` y `/api/alertas` → CSVs reales | `server_orbit.py` |
| `076db05` | Días comerciales con feriados reales | `server_orbit.py` |
| `8e6bd78` | Documentación: estado real de auditoría | `CHANGELOG_AI.md`, `NEXT_TASK.md` |
| `a24d34f` | Etiqueta "visitados" → "planificados" | `dashboard.jsx` |
| `67a62b7` | Launcher portal ORBIT | `ABRIR_CLAUDE_ORBIT.bat` |
| `b242b7c` | `.gitignore` para `__pycache__/` | `.gitignore` |

### Datos de entrada sin commitear (no son errores)
- `01_INPUTS/resultado.xlsx` — modificado (datos ERP del día, actualización diaria normal)
- `01_INPUTS/ventas.csv` — modificado (ventas del día, actualización diaria normal)
- Estos archivos **no deben commitearse** sin confirmación explícita del usuario.

### Qué NO tocar sin confirmación
- `server_orbit.py` — endpoint Flask estable, 7 vendedores, todos los KPIs funcionando
- `PAV MATINAL PE_A FLOR/screens/dashboard.jsx` — JSX limpio, sin mock, sin hardcode
- `PAV MATINAL PE_A FLOR/data.js` — contrato de datos real, sin mock
- `ABRIR_CLAUDE_ORBIT.bat` — launcher correcto recién creado
- `.gitignore` — recién creado
- `01_INPUTS/` — datos de entrada, solo el usuario los actualiza
- `LEGACY/orbit_matinal_v42.py` — motor estable, no tocar sin nueva tarea específica
- `09_CONFIG/clientes_excluidos.csv` — 10 exclusiones formalizadas, estable

### Validación funcional — 2026-05-07 (servidor activo, sin cambios de código)

**Portal operativo. Sin mock activo en ningún bloque auditado.**

| Endpoint | Estado | Detalle |
|---|---|---|
| `/api/diagnostico` | ✓ REAL | total=24, corridos=5, botellas 1406/9050, 3 segmentos, 28 titulares |
| `/api/dashboard` | ✓ REAL | 7 vendedores, sin_maestro=False todos |
| `/api/clientes` | ✓ REAL | 340 items, estados y prioridades reales |
| `/api/alertas` | ✓ REAL | 103 items, descuentos reales por artículo |
| `/api/gastos_accion` | ✓ REAL | 26 filas, exceso $231k |
| `/` + `/data.js` | ✓ HTTP 200 | portal y contrato de datos cargan |
| `/api/planificacion` | ⚠ VACÍO | esperado — sin fuente real aún |

**Decisiones confirmadas — no cambiar sin nueva instrucción:**
- Sábados cuentan como días comerciales. `corridos=5` al 2026-05-07 es correcto.
- `/api/alertas` no mezcla SIN_COMPRA_MES. Los clientes sin compra están en `/api/clientes`.
- `/api/planificacion` vacío es esperado si no hay fuente real.

### Pendientes funcionales (no bloquean portal)

1. **`vendedor_codigo` en gastos_accion** — llega como `"10"` en lugar de `"V10"`. Cards de gastos pierden color de vendedor (cae a magenta). Fix menor en `server_orbit.py`.
2. **`ccc_mes: 0`** — honesto; ningún CSV actual tiene CCC acumulado del mes.
3. **Bloque A (ERP externo)** — completar `clientes.xlsx` con datos faltantes de algunos clientes V7/V9. Requiere datos externos, no tiene código pendiente.
4. **Automatización de regeneración** — `ABRIR_CLAUDE_ORBIT.bat` solo abre el portal. El pipeline (`run_orbit.py` + `datasets_orbit.py`) sigue siendo manual. Decidir si automatizar con un segundo BAT o integrar en el mismo.

### Qué NO tocar sin confirmación
- `server_orbit.py` — estable, 7 vendedores, todos los endpoints funcionando
- `PAV MATINAL PE_A FLOR/screens/dashboard.jsx` — sin mock, sin hardcode
- `PAV MATINAL PE_A FLOR/data.js` — contrato de datos real
- `ABRIR_CLAUDE_ORBIT.bat` — launcher correcto
- `01_INPUTS/` — solo el usuario actualiza estos archivos
- `LEGACY/orbit_matinal_v42.py` — motor estable
- `09_CONFIG/clientes_excluidos.csv` — 10 exclusiones formalizadas

---

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
2. ~~**Días hábiles en `server_orbit.py`**~~ → ✓ Resuelto commit `076db05`. `total=24`, `corridos=3`, feriados leídos desde `09_CONFIG/feriados.csv`.
3. **Acumulado=0** en `dashboard_vendedor.json` → `app_publish.py` busca columna `acumulado` pero `mod_volumen_vendedor.csv` tiene `acumulado_mes` → retorna 0 para todos.
4. ~~**Datos hardcodeados en frontend**~~ → ✓ Resuelto (Bloque B + commit `a24d34f`). Sin mock, sin nombres de persona, etiqueta "planificados" correcta.
5. ~~**`orbit_portal_data.json`** tiene estructura distinta~~ → No bloqueante: ningún endpoint activo lo consume. JSONs estáticos de `app_publish.py` (`clientes_hoy.json`, `alertas_app.json`) reemplazados por CSVs reales en commit `7a4f7e8`.
6. ~~**Importes = 0 en clientes_dia.csv**~~ → ✓ Resuelto (Bloque C + botellas expuestas en commit `c1124b5`). `importe_mes > 0` en 199/400 clientes. `botellas_dia=1406`, `botellas_mes=9050` en `kpisGerencia`.
7. **`ccc_mes: 0`** en `data.js` — correcto y honesto pero pendiente: necesita fuente real de CCC acumulado del mes (no existe en ningún CSV actual).
8. ~~**Segmentos `cubiertos: 0`**~~ → ✓ Resuelto (Bloque D). `server_orbit.py` expone segmentos reales desde `mod_ccc_segmento.csv`; `data.js` consume `diag.segmentos`.
9. ~~**`titulares11` incompleto**~~ → ✓ Resuelto (Bloque D). 28 marcas reales desde `mod_11_titulares.csv`; `data.js` consume `diag.titulares11`.

## Resueltos en esta sesión (2026-05-05)
- ✓ `data.js` restaurado como JavaScript válido (era código Python).
- ✓ `diaActivo` ahora se calcula desde `fecha_corte + 1 día` → "MI".
- ✓ Título de la matinal en `app.jsx` ahora es dinámico → "Miércoles 06/05".
- ✓ `ccc_dia` ahora toma el valor real de `mod_ccc_segmento`; `ccc_mes` queda en 0 (honesto).
- ✓ `acumulado=0` corregido en `app_publish.py`: `"acumulado_mes"` agregado como primer candidato en `build_avance_map()`.
- ✓ V7 y V9 visibles en `/api/dashboard` con fallback desde `resultado.xlsx` (`sin_maestro: true`). Deuda: actualizar `clientes.xlsx`.
