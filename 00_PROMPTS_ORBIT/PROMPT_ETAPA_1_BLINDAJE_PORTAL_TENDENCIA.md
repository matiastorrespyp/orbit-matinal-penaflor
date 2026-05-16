# PROMPT_ETAPA_1_BLINDAJE_PORTAL_TENDENCIA

## Contexto

Continuación de auditoría PAV Matinal Peñaflor.

Etapa 1 (commit c3de7aa) y Etapa A (sin commit, pendiente aprobación) ya corrigieron:
- CCC Mes → desde `ventas.csv` mes actual (no `ccc_mes_flag`)
- Cobertura % eliminada del dashboard principal
- Labels: Avance → Tendencia, CCC acumulado → CCC Compradores Mes, etc.
- `botellas_mes` eliminado (era Vi solamente)
- `cartera_real_total = 2045` expuesto en `/api/diagnostico`
- Denominadores de segmentos → desde `clientes.xlsx` (cartera real)

Lo que **NO** está resuelto todavía:
- `clientes_sin_compra_mes` en `mod_volumen_vendedor.csv` usa historial sin filtro de mes (Etapa B, pendiente)
- Cobertura real desde `ventas.csv` + `clientes.xlsx` no está calculada (Etapa C, pendiente)
- Motor legacy `LEGACY/orbit_matinal_v42.py` no tocado

---

## Objetivo de este prompt

Blindar el portal para que:
1. **Tendencia %** se calcule y muestre correctamente (no confundir con Avance).
2. **Ningún KPI con porcentaje** use denominadores desfasados o de Vi solamente.
3. **CCC Mes** siempre venga de `ventas.csv` del mes actual, nunca de `ccc_mes_flag`.
4. **El portal no regrese a un estado inválido** si se regeneran los datasets (el motor legacy puede sobreescribir `clientes_dia.csv` con datos desactualizados).

---

## Tarea 1 — Verificar Tendencia % en portal

### Leer y confirmar:
- `PAV MATINAL PE_A FLOR/portal.html` — buscar todas las ocurrencias de `% avance` y `% tendencia`
- Confirmar que no queda ninguna etiqueta `avance` donde debería decir `tendencia`

### Validar en el endpoint:
- `/api/dashboard` → `kpis.avance_pct` ¿viene del motor o se recalcula?
- Si viene del motor (`mod_volumen_vendedor.avance_pct`), verificar la fórmula usada:
  - ¿Es `acumulado / objetivo`? → Es avance bruto
  - ¿Es `(acumulado / días_corridos) * días_totales / objetivo`? → Es tendencia

### Regla comercial aplicable:
- El portal debe mostrar **Tendencia %** en el chip de cabecera y en la tarjeta KPI.
- La fórmula correcta: `tendencia = (acumulado / max(días_corridos, 1)) * días_totales / objetivo * 100`
- Si `avance_pct` del endpoint es avance bruto, corregir el cálculo en `server_orbit.py` o recalcular en `data.js`.

---

## Tarea 2 — Blindar CCC Mes contra regeneración de datasets

### Problema:
Si el motor legacy se ejecuta y regenera `clientes_dia.csv`, el campo `ccc_mes_flag` se actualiza.
Los endpoints `/api/dashboard` y `/api/vendedor/<vid>` ya NO usan `ccc_mes_flag` (Etapa 1 ✓).
Pero `_cargar_ventas_mes_actual()` depende de que `01_INPUTS/ventas.csv` esté actualizado.

### Verificar:
- ¿`ventas.csv` tiene datos de mayo 2026? Confirmar fecha máxima de `FechaComprobante`.
- ¿El total CCC Mes = 311 es consistente con la fecha de los datos?

### Comando de verificación:
```bash
python -c "
import pandas as pd
df = pd.read_csv('01_INPUTS/ventas.csv', sep=';', encoding='latin1')
df['fecha'] = pd.to_datetime(df['FechaComprobante'], dayfirst=True, errors='coerce')
print('Fecha min:', df['fecha'].min())
print('Fecha max:', df['fecha'].max())
print('Filas mayo 2026:', (df['fecha'].dt.month == 5).sum())
"
```

---

## Tarea 3 — Verificar que cobG no se renderiza en ningún lado

### Buscar en portal.html:
- `cobG` → ¿aparece en algún `innerHTML` o `textContent` visible?
- Si aparece: eliminar o reemplazar por texto estático.

### Buscar en index.html (si existe):
- Verificar que `index.html` no tiene una copia del cálculo de cobertura con el bug original.

### Diferencia entre portal.html e index.html:
- Confirmar cuál de los dos está siendo servido por Flask en la ruta `/`.
- Si `index.html` tiene KPIs duplicados y desfasados, documentarlo para Etapa C.

---

## Tarea 4 — Agregar campo `tendencia_pct` limpio al endpoint

### Propuesta:
En `/api/dashboard`, exponer `tendencia_pct` calculado desde `ventas.csv`:

```python
# En _ccc_mes_por_vendedor o en el loop de dashboard:
dias = contar_dias_habiles()
corridos = max(dias["corridos"], 1)
totales = dias["total"]
tendencia_pct = (acum / corridos) * totales / obj * 100 if obj else 0
```

Agregar al response: `"tendencia_pct": tendencia_pct`

En `data.js`: usar `k.tendencia_pct || k.avance_pct` para el display.

### Antes de implementar:
- Confirmar que `contar_dias_habiles()` devuelve valores correctos para mayo 2026.
- Validar: `corridos` debe ser ≤ `total`.

---

## Tarea 5 — Documentar en CHANGELOG_AI.md

Al finalizar, agregar entrada:
```
## [Etapa A] YYYY-MM-DD — Blindaje portal tendencia
- Eliminada cobertura % del dashboard
- CCC Mes desde ventas.csv
- Labels corregidos: Avance → Tendencia, etc.
- cartera_real_total = 2045 expuesto
- botellas_mes = null
- Pendiente: tendencia_pct limpio, cobertura real, motor legacy
```

---

## Fuentes de verdad a consultar antes de ejecutar

- `00_OBSIDIAN_ORBIT/REGLAS_NEGOCIO_PAV.md` — reglas de CCC, cobertura, tendencia
- `00_OBSIDIAN_ORBIT/MAPA_DATOS_PAV.md` — trazabilidad de KPIs
- `00_OBSIDIAN_ORBIT/05_ERRORES_Y_SOLUCIONES/README.md` — errores documentados
- `CLAUDE.md` — contrato de trabajo y reglas técnicas

---

## Validaciones obligatorias antes de cualquier commit

```
1. python audit_pav_matinal_data.py
2. GET /api/diagnostico → cartera_real_total = 2045, botellas_mes = null
3. GET /api/dashboard → CCC Mes = 311, CCC Día = 37
4. GET /api/vendedor/v3 → ccc_total = 79, ccc_autoservicio = 0
5. Revisar visualmente /portal.html — no debe aparecer "% avance" ni "Cobertura %"
6. git diff — mostrar antes de cualquier commit
7. git status --short
```

## Prohibiciones

- No modificar `LEGACY/orbit_matinal_v42.py`.
- No hacer commit sin aprobación explícita.
- No usar mock ni fallback silencioso.
- No agregar % de cobertura sin denominador desde `clientes.xlsx`.
- No usar `ccc_mes_flag` ni `cobertura_mes_flag` como fuente principal.
