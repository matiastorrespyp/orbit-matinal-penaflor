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

### ~~Bloque C~~ — ✓ Completado 2026-05-06
`ventas_mes` ahora se construye desde `historial_ventas` (acumulado) en lugar de `ventas_validas` (solo 2 días).
- `importe_mes > 0`: 175/255 clientes MI (antes: 0/255)
- Suma importe_mes: $26.608.333
- `ventas_ayer` sin cambios (correcto)

### Bloque D — data.js sin fuente
- `segmentos.cubiertos = 0` → cruzar con `mod_ccc_segmento.csv` desde el servidor
- `titulares11` tiene solo 2 de 11 hardcodeados → mapear desde `mod_11_titulares.csv`
- `ccc_mes = 0` → sin fuente de CCC acumulado del mes disponible en ningún CSV

---

## Problemas pendientes detectados en auditoría (2026-05-05)

1. **V7 y V9 ausentes** en datasets (ver arriba).
2. **Días hábiles en `server_orbit.py`** no excluye feriados → `/api/diagnostico` devuelve total=26/corridos=4 en vez de 24/3.
3. **Acumulado=0** en `dashboard_vendedor.json` → `app_publish.py` busca columna `acumulado` pero `mod_volumen_vendedor.csv` tiene `acumulado_mes` → retorna 0 para todos.
4. **Datos hardcodeados** en frontend: sparkline CCC en `dashboard.jsx` (mock inventado), usuario "Manuel R." en sidebar de `app.jsx`.
5. **`orbit_portal_data.json`** tiene estructura distinta a la que genera `tools/orbit_truth_audit.py` — fue generado por otra herramienta anterior.
6. **Importes = 0 en clientes_dia.csv** → `importe_mes`, `botellas_mes`, `importe_ayer` = 0 para las 255 filas. El join con `ventas.csv` en el motor legacy no está transfiriendo datos.
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
