# NEXT TASK - ORBIT MATINAL PEÑAFLOR

## Próxima tarea

**Actualizar `clientes.xlsx` para incluir clientes de V7 y V9.**

Causa raíz identificada: `clientes.xlsx` no tiene ningún cliente con `codven=7` ni `codven=9`. El motor legacy usa este maestro como base — sin clientes, V7 y V9 son invisibles para el pipeline completo.

Clientes de V7 en `ventas.csv`: `7898`, `7931`, `1210`.
Clientes de V9 en `ventas.csv`: `1094`, `1285`, `8125`, `1362`, `1387`, `8010`, `769`, `388`, `8139`, `1089`, `1093`.

Para cada cliente se necesita: `Razon_Social`, `Ramo`, `DiasVisita`, `Localidad`, `SubSegmento`. Obtener del sistema de gestión comercial o de otra exportación del ERP.

Mientras tanto, V7 y V9 aparecen en el portal con visibilidad gerencial (objetivo/acumulado/avance) gracias al fallback en `server_orbit.py`.

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
