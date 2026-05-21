# NEXT TASK - ORBIT MATINAL PEÑAFLOR

## Sesión 2026-05-19 — Cierre confirmado (commit b16a54c)

### Estado final
- Regla V20 formalizada: `VENDEDORES_EXCLUIDOS = [2, 5, 20]` en motor legacy.
- Documentación actualizada: `CLAUDE.md` y `REGLAS_NEGOCIO_PAV.md`.
- Auditoría completa del estado del proyecto realizada. Portal, inputs, datasets y orbit.db intactos.

### ~~Próximo paso — Prioridad 1~~ ✅ COMPLETADO 2026-05-19

**Validar Etapa B1 del portal — PASS backend + visual.**

Backend y portal validados. Ver CHANGELOG_AI.md entrada 2026-05-19.

### ~~Próximo paso — Prioridad 1~~ ✅ COMPLETADO 2026-05-19

**Diagnosticar y corregir error JS 404.**
Diagnosticado: `/favicon.ico` ausente. Fix: ruta Flask `@app.route("/favicon.ico") → 204`. Commit `7ef8edb`.

### Pendientes adicionales actualizados — 2026-05-19

- ~~**Recalcular `clientes_sin_compra_mes`**~~ ✅ Fix motor legacy commit `9e89030`. Dif = 0 en todos los vendedores.
- ~~**Favicon 404**~~ ✅ Resuelto con ruta Flask 204, commit `7ef8edb`.
- **Decidir limpieza** de `portal.html.bak.2026-05-14` y `screenshots/` — pendiente, no urgente.

### ~~Próximo paso — Prioridad 1~~ ✅ COMPLETADO 2026-05-19

**Validación integral portal gerencia + vendedor post-fix — PASS.**
APIs 200, excluidos 404, portal gerencia correcto, Sin Comp. Mes = 262 coincide con motor. Sin errores JS ni 404s. Ver CHANGELOG_AI.md entrada 2026-05-19.

### Próximo paso — Prioridad 1

**Definir y unificar semántica: CCC Mes vs Sin Comp. Mes.**

**Problema:** el portal mezcla dos universos en la misma vista gerencial:
- "CCC Mes" en ranking → cartera completa mes actual (`server_orbit._ccc_mes_por_vendedor()`, ventas.csv).
- "Sin Comp. Mes" → zona Vi del día (`clientes_dia`, motor).

Comparar estos dos números en el mismo contexto es semánticamente incorrecto.

**Decisión pendiente (sin tocar código hasta resolver):**
1. Opción A: mostrar ambos con etiquetas explícitas de universo.
2. Opción B: unificar ambos al universo de zona Vi (cartera planificada del día).
3. Opción C: unificar ambos al universo de cartera completa del mes.

**Restricciones:** proponer diseño primero, alineado con sistema visual existente. No implementar sin aprobación.

### ~~Prioridad 2: Módulo Innovaciones Plan AS~~ ✅ COMPLETADO 2026-05-19 — INOV-1

**Motor:** `generar_mod_innovaciones_plan_as()` en `LEGACY/orbit_matinal_v42.py`.
**Dataset:** `04_DATASETS_ORBIT/mod_innovaciones_plan_as.csv` — 28 filas / 9 columnas.
**Denominador:** 13 (columnas Si/No del xlsx). NaN = no aplica para PYP.
**Antares P770/P330:** solo en `productos_pendiente_stock`. Fuera del denominador.
**Frizze M y Antares XPA:** NaN en xlsx PYP → van en módulo separado INOV-2.

### ~~Prioridad 2: INOV-2 Frizze Manxana + Antares XPA por segmento~~ ✅ COMPLETADO 2026-05-19

**Dataset:** `04_DATASETS_ORBIT/mod_innovaciones_segmento.csv` — 26 filas / 10 columnas.
**Motor:** `generar_mod_innovaciones_segmento()` en `LEGACY/orbit_matinal_v42.py` — commit `a651d01`.
**Fuente:** `ventas.csv`. Segmentos: Tradicional / Autoservicio. V2/V5/V20 y V3/AUTOSERVICIO ausentes. ✅

### ~~Prioridad 2: INOV-3 Endpoints Innovaciones~~ ✅ COMPLETADO 2026-05-19

**Endpoints:** `server_orbit.py` — commit `b11ab9d`.
- `/api/gerencia/innovaciones_segmento` y `/api/vendedor/<id>/innovaciones_segmento`.
- Validación 10/10 PASS. Sin V2/V5/V20. Sin V3/AUTOSERVICIO. `clientes_faltantes` como list. ✅

### ~~Prioridad 2: INOV-4 UI Innovaciones por segmento~~ ✅ COMPLETADO 2026-05-20

**Commit:** `5c8434a` — `PAV MATINAL PE_A FLOR/portal.html`.
- Gerencia: bloque full-width Innovaciones (cards + tabla cobertura por vendedor). V2/V5/V20 excluidos.
- Vendedor: card Innovaciones en KPIs (barras + clientes_faltantes). V3 sin AUTOSERVICIO.
- Playwright 15/15 PASS. Endpoints INOV-3 200 OK.

### ~~Prioridad 2: INOV-5 Mejora visual Innovaciones~~ ✅ COMPLETADO 2026-05-20

**Commit:** `b247410` — `PAV MATINAL PE_A FLOR/portal.html`. Pusheado.
- Fase 1: auditoría visual + endpoints crudos. V3 0% = dato real. V4/Gerencia coinciden. V2/V5/V20 ausentes.
- Fase 2: wording "Sin compradores aún", cards 260px, tabla compacta X/Y + mini-barra. Sin tocar lógica ni backend.

### ~~Prioridad 2: INOV-6a endpoint plan_innovaciones~~ ✅ COMPLETADO 2026-05-20

**Commit:** `ebb0d17` — `server_orbit.py`. Pusheado.
- `GET /api/vendedor/<vid>/plan_innovaciones` — read-only.
- Faltantes enriquecidos: `en_zona_hoy`, `enriquecimiento` (completo/parcial/sin_datos).
- Fuentes: `mod_innovaciones_segmento.csv` + `clientes_dia.csv` + `clientes_master.csv`.
- V3 sin AUTOSERVICIO. V2/V5/V20 → 403. Endpoints INOV-3 intactos.

### Próximo paso — Prioridad 2: INOV-6b UI Plan de Acción en portal.html

- Mostrar lista accionable de clientes faltantes en la card Innovaciones del vendedor.
- Fuente: `/api/vendedor/<vid>/plan_innovaciones`.
- Priorizar `en_zona_hoy=true` primero, luego parciales.
- No tocar backend. Solo `portal.html`.
- Proponer diseño antes de implementar.

---

## Sesión 2026-05-14 — Cierre confirmado (commit c67e70e)

### Estado final
- `portal.html` rediseñado y commiteado. Dos portales activos: gerencial desktop + vendedor mobile.
- `server_orbit.py`: endpoint `/api/vendedor/{id}` implementado y funcionando con datos reales.
- `test_portal.py` y `test_kpis.py` creados y commiteados.
- V3 Nadia Gambino: regla autoservicio aplicada en servidor y en portal (columna AUTOSERV. oculta).
- 11 Titulares: usa datos por vendedor del nuevo endpoint.

### Pendientes próxima sesión (no bloquean operación diaria)

1. **Revisar portal visualmente en navegador** — validación visual humana del diseño (gerencia en desktop, vendedor en mobile/devtools 390px). Los screenshots de Playwright confirman carga técnica pero no aprobación visual final.

2. **Validar con datos reales del próximo cierre operativo** — la próxima vez que se actualicen `ventas.csv` y `resultado.xlsx`, regenerar datasets y verificar que todos los KPIs del portal reflejan los nuevos valores correctamente.

3. **Favicon** — agregar `favicon.ico` en `PAV MATINAL PE_A FLOR/` para eliminar el 404 cosmético de browser.

4. **Decidir limpieza de archivos no commiteados:**
   - `PAV MATINAL PE_A FLOR/portal.html.bak.2026-05-14` — backup del rediseño (se puede borrar cuando el diseño esté aprobado).
   - `screenshots/` — capturas de validación (se puede limpiar o gitignorear).
   - `CHANGELOG_AI.md` y `NEXT_TASK.md` — pendientes de commit cuando el usuario lo indique.

5. **Resolver conflicto portal.html vs index.html** — Flask sirve `index.html` en `/` pero el portal activo es `portal.html`. Evaluar si redirigir `/` → `portal.html` o unificar en un solo archivo.

---

## Sesión 2026-05-12 — Módulo VDA completado (PROMPT_004)

### Estado final
- Todos los datasets VDA generados con datos reales (57,280 filas VDA, 764 clientes)
- Mes actual (mayo) incompleto — datos hasta 2026-05-11; balance negativo es esperado
- V20 en ranking VDA — no figura en la lista de vendedores activos Peñaflor; validar con usuario

### Próximas acciones VDA (Fase 2)

1. **Validar V20** — ¿Es un vendedor activo no registrado? ¿Error de datos?
2. **Integrar módulo VDA en pipeline diario** — agregar llamada a `_tmp_auditoria_vda.py` (o extraer función) desde `orbit_matinal_v42.py`.
3. **Exponer `/api/vda`** en `server_orbit.py` sirviendo `vda_clientes_ganados.json`.
4. **Agregar hoja VDA** a `MATINAL_PENA_V42.xlsx` para exportación automática.
5. **Resolver encoding `producto activos.xlsx`** — exportar desde Gescom con UTF-8.

---

## Sesión 2026-05-12 — Auditoría total (PROMPT_003)

Auditoría completa ejecutada. Ver `AUDITORIA_ORBIT_MATINAL_2026-05-12.md` para diagnóstico completo.

### Próximas acciones por fase (resultado de la auditoría)

#### FASE 1 — Inmediato (sin código)
1. **Exportar `producto activos.xlsx`** desde Gescom → colocar en `01_INPUTS/`. Sin esto, 11 Titulares usa mapa hardcodeado.
2. **Resolver `portal.html` vs `index.html`**: portal.html fue actualizado 2026-05-11 22:41 pero Flask sirve index.html. ¿Cuál es el activo?
3. **Eliminar archivos basura** raíz: `3`, `float`, `None`, `str`, `pd.DataFrame`, `Dict[str]` (creados 2026-04-10).

#### FASE 2 — Motor (requiere código)
4. Implementar `ccc_mes` acumulado desde `historial_ventas_cliente.csv` en `orbit_matinal_v42.py`.
5. Exportar como CSV `mod_ccc_mes.csv` en `04_DATASETS_ORBIT/`.
6. Exponer `ccc_mes` en `/api/diagnostico` y `/api/dashboard`.
7. Actualizar `data.js` para consumir `ccc_mes` real.

#### FASE 3 — Limpieza
8. Deprecar `app_publish.py` (genera JSONs obsoletos, no forma parte del pipeline).
9. Desactivar o actualizar `/api/orbit-data` en `server_orbit.py`.
10. Archivar `06_APP_DATA/*.json` obsoletos (generados 2026-05-05).
11. Mover `src/orbit/` a `LEGACY/` si no tiene consumidor activo.

---

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

1. ~~**`vendedor_codigo` en gastos_accion**~~ → ✓ Resuelto commit `4cbbbee`. Función `normalizar_vendedor_codigo()` — 9/9 casos validados. HTTP 200, V10/V9/V8/V3 correctos, importes sin cambio.
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
