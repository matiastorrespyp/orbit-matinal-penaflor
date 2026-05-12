# Ajustar selector de día de matinal — ORBIT PAV

Aplicá orbit-pav-guardian.

El diagnóstico encontró dos causas del problema:

1. En LEGACY/orbit_matinal_v42.py:
   fecha_objetivo = fecha_max_ventas + 1 día

2. En portal.html:
   currentDay = "MA" hardcodeado

Necesito corregir esto, pero con estas reglas obligatorias.

## Reglas funcionales

### Calendario de objetivos / media necesaria

No contar sábados.

Usar solo:
- lunes a viernes
- sin feriados
- sin sábados

Este calendario aplica a:
- media necesaria
- avance
- ritmo
- tendencia
- lectura de objetivo mensual

### Calendario operativo / matinal

Sí puede incluir sábado.

Aplica a:
- matinal diaria
- rutas
- clientes del día
- CCC no compradores
- planificación
- vendedores que trabajan sábado

No mezclar ambos calendarios.

## Selector de día

No quiero selector visual falso.

Antes de implementar re-fetch con ?dia=, confirmá si el backend puede devolver datos reales para ese día usando fuente real.

Si no hay fuente suficiente para filtrar por día, frená y explicá qué falta.

## Cambio mínimo autorizado

Implementar solo si se puede hacer con datos reales:

1. Eliminar hardcode:
   currentDay = "MA"

2. Inicializar el día desde /api/diagnostico.

3. Exponer en /api/diagnostico:
   - fecha_datos
   - fecha_corte
   - fecha_objetivo
   - fecha_matinal
   - dia_operativo
   - modo_fecha

4. Corregir lógica fecha_max_ventas + 1 para:
   - sábado → lunes
   - domingo → lunes
   - feriado → siguiente operativo
   - viernes → sábado solo si hay ruta/vendedores sábado; si no, lunes

## No tocar todavía

- media necesaria
- panel gerencial
- objetivos mensuales
- 01_INPUTS
- REGENERAR_DATOS_ORBIT.bat
- ventas.csv
- resultado.xlsx

## Entregable antes de modificar

Mostrame:

1. archivos exactos que vas a tocar
2. git diff propuesto o explicación concreta
3. endpoints afectados
4. si requiere regenerar BAT después
5. cómo queda Matinal lunes con ventas del sábado
6. cómo queda Matinal sábado
7. riesgo de cada cambio
8. qué NO vas a tocar

No commitees.
No ejecutes BAT.
Esperá aprobación antes de implementar.