# NEXT TASK - ORBIT MATINAL PEÑAFLOR

## Próxima tarea

Corregir vendedores faltantes: V7 (Jofre) y V9 (Sanchez) no aparecen en `clientes_dia.csv` ni en `mod_volumen_vendedor.csv`.

Están presentes en `resultado.xlsx` y en `ventas.csv`, pero el motor legacy no los procesa.

Rastrear en `LEGACY/orbit_matinal_v42.py` por qué V7 y V9 no generan filas en los datasets. Puede ser un filtro por código de vendedor, un ramo no contemplado o un error de mapeo.

No modificar código hasta identificar la causa raíz.

---

## Problemas pendientes detectados en auditoría (2026-05-05)

1. **V7 y V9 ausentes** en datasets (ver arriba).
2. **Días hábiles en `server_orbit.py`** no excluye feriados → `/api/diagnostico` devuelve total=26/corridos=4 en vez de 24/3.
3. **Acumulado=0** en `dashboard_vendedor.json` → `app_publish.py` suma `venta_mes_actual` desde `clientes_dia.csv` pero esa columna vale 0; el importe real está en `importe_mes`.
4. **Datos hardcodeados** en frontend: sparkline CCC en `dashboard.jsx`, título de fecha en `app.jsx`, usuario "Manuel R." en sidebar.
5. **`orbit_portal_data.json`** tiene estructura distinta a la que genera `tools/orbit_truth_audit.py` — fue generado por otra herramienta anterior.
