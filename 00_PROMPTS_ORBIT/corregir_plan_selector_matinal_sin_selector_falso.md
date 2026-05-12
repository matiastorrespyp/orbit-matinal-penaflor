# Corregir plan selector matinal sin selector falso — ORBIT PAV

Aplicá orbit-pav-guardian.

El diagnóstico del selector de día encontró dos causas:

1. En LEGACY/orbit_matinal_v42.py:
   fecha_objetivo = fecha_max_ventas + 1 día

2. En PAV MATINAL PE_A FLOR/portal.html:
   currentDay = "MA" hardcodeado

El diagnóstico sirve, pero NO apruebo implementar tal cual.

## Correcciones obligatorias antes de tocar archivos

### 1. No selector visual falso

No quiero un selector que parezca cambiar la matinal si en realidad no cambia los datos reales.

Si hoy el backend no puede devolver datos reales por día con ?dia=, entonces:

- NO implementar re-fetch falso.
- NO implementar setDay como si fuera selector real.
- NO hacer que el usuario crea que cambió la matinal si los datos siguen siendo los mismos.
- Permitido: inicializar el día desde /api/diagnostico.
- Permitido: mostrar banner de contexto.
- Pendiente: selector manual real cuando exista fuente tipo clientes_todos_dias.csv o equivalente.

### 2. siguiente_dia_operativo robusto

La lógica nueva debe resolver:

- sábado → lunes
- domingo → lunes
- feriado → siguiente operativo
- viernes → sábado solo si existen rutas/vendedores sábado
- si no hay rutas sábado, viernes → lunes

La detección de ruta sábado debe ser robusta.

No alcanza con buscar solo "Sa" exacto.

Debe detectar variantes como:

- SA
- Sa
- sa
- LU,MA,SA
- Lu, Ma, Sa
- LU, MA, SA
- VI,SA

### 3. Feriados

Usar feriados.csv si existe.

No hardcodear feriados.

Si no existe feriados.csv, informar y usar comportamiento sin feriados como fallback explícito.

### 4. No tocar todavía

No tocar:

- media necesaria
- panel gerencial
- objetivos mensuales
- 01_INPUTS
- ventas.csv
- resultado.xlsx
- REGENERAR_DATOS_ORBIT.bat
- datasets generados
- lógica de objetivos

## Implementación mínima autorizable

Solo se puede implementar esta fase mínima:

### Archivo 1 — LEGACY/orbit_matinal_v42.py

Corregir fecha_objetivo automática.

Debe dejar de ser simplemente:

fecha_objetivo = fecha_ejecucion + timedelta(days=1)

Debe usar una función tipo:

siguiente_dia_operativo(fecha_ejecucion, clientes, feriados)

Reglas:

- saltear domingos
- saltear feriados
- saltear sábado si no hay ruta sábado
- permitir sábado si hay ruta sábado
- sábado cargado como fecha de datos debe sugerir lunes

### Archivo 2 — server_orbit.py

Exponer en /api/diagnostico:

- fecha_datos
- fecha_corte
- fecha_objetivo
- fecha_matinal
- dia_operativo
- modo_fecha

Todo aditivo y retrocompatible.

No implementar todavía ?dia= si no hay fuente real.

### Archivo 3 — PAV MATINAL PE_A FLOR/portal.html

Corregir:

currentDay = "MA"

Debe inicializarse desde /api/diagnostico.

Agregar banner de contexto con:

- Fecha datos
- Fecha corte
- Matinal seleccionada/sugerida
- Día operativo
- Modo fecha

No implementar selector manual falso.

## Entregable requerido ahora

Antes de modificar archivos, mostrame:

1. plan corregido
2. archivos exactos que tocarías
3. cambios exactos por archivo
4. cómo detectarías ruta sábado
5. cómo leerías feriados.csv
6. cómo queda Matinal lunes con ventas del sábado
7. cómo queda Matinal sábado
8. qué queda pendiente para selector manual real
9. si requiere ejecutar BAT después
10. riesgos
11. qué NO vas a tocar

No modifiques archivos todavía.
No commitees.
No ejecutes BAT.
Esperá aprobación.