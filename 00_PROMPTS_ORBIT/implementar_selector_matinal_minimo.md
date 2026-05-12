# Implementar selector matinal mínimo — ORBIT PAV

Aplicá orbit-pav-guardian.

Aprobado implementar solo la fase mínima del selector de día de matinal.

## Alcance autorizado

Implementar únicamente:

1. Corregir fecha_objetivo automática en el motor.
2. Exponer contexto de fecha en /api/diagnostico.
3. Quitar currentDay="MA" hardcodeado.
4. Inicializar currentDay desde /api/diagnostico.
5. Mostrar banner de contexto.
6. Dejar el selector como informativo, no falso.

## Archivos autorizados

Tocar solo:

- LEGACY/orbit_matinal_v42.py
- server_orbit.py
- PAV MATINAL PE_A FLOR/portal.html

## Archivo 1 — LEGACY/orbit_matinal_v42.py

Implementar:

- lectura de 09_CONFIG/feriados.csv si existe
- función cargar_feriados()
- función siguiente_dia_operativo(fecha_ejecucion, clientes, feriados)

Reglas:

- sábado como fecha de datos → lunes
- domingo → lunes
- feriado → siguiente operativo
- viernes → sábado solo si hay rutas sábado
- viernes → lunes si no hay rutas sábado
- no hardcodear feriados
- detectar sábado aunque dias_visita venga como:
  - SA
  - Sa
  - sa
  - LU,MA,SA
  - Lu, Ma, Sa
  - VI,SA

Reemplazar la lógica:

fecha_objetivo = fecha_ejecucion + timedelta(days=1)

por la nueva función.

## Archivo 2 — server_orbit.py

Agregar en /api/diagnostico, sin romper campos existentes:

- fecha_datos
- fecha_corte
- fecha_objetivo
- fecha_matinal
- dia_operativo
- modo_fecha

Debe leer esos datos desde los CSVs regenerados, especialmente mod_volumen_vendedor.csv si ahí existen fecha_ejecucion, fecha_objetivo y dia_objetivo.

## Archivo 3 — PAV MATINAL PE_A FLOR/portal.html

Corregir:

currentDay = "MA"

Debe pasar a:

currentDay = null

Y luego inicializar currentDay desde:

/api/diagnostico

Agregar banner de contexto visible con:

- Fecha datos
- Fecha corte
- Matinal
- Día operativo
- Modo fecha

El selector LU/MA/MI/JU/VI/SA debe quedar informativo, sin onclick falso si no hay refetch real por día.

## No implementar todavía

No implementar selector manual real con ?dia=.

Motivo:
Hoy no existe una fuente completa tipo clientes_todos_dias.csv. clientes_dia.csv ya viene prefiltrado por el motor.

## No tocar

- 01_INPUTS/
- ventas.csv
- resultado.xlsx
- REGENERAR_DATOS_ORBIT.bat
- media necesaria
- panel gerencial
- objetivos mensuales
- 04_DATASETS_ORBIT/*.csv
- 03_OUTPUTS/
- logs
- backups

## Después de implementar

Mostrar:

1. git status --short
2. git diff de:
   - LEGACY/orbit_matinal_v42.py
   - server_orbit.py
   - PAV MATINAL PE_A FLOR/portal.html
3. Confirmar que no tocaste 01_INPUTS.
4. Confirmar que no ejecutaste BAT.
5. Confirmar que no commiteaste.
6. Decir si después hará falta ejecutar BAT para regenerar fecha_objetivo.

No commitear.
No ejecutar BAT.
Esperar aprobación después del diff.