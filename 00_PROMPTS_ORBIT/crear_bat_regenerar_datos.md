# Crear BAT de regeneración de datos ORBIT PAV

Usá la skill orbit-pav-guardian.

Necesito avanzar con el bloque de automatización del pipeline, pero sin romper el portal operativo.

## Objetivo

Crear una propuesta controlada para:

REGENERAR_DATOS_ORBIT.bat

Este BAT debe regenerar los datos derivados del portal ORBIT Matinal Peñaflor.

No debe abrir el portal.
No debe levantar server_orbit.py.
No debe tocar frontend.
No debe tocar 01_INPUTS.
No debe commitear nada.

## Estado actual

El portal ya quedó operativo en bloques auditados:

- /api/diagnostico OK
- /api/dashboard OK
- /api/clientes OK
- /api/alertas OK
- /api/gastos_accion OK
- data.js sin mock activo
- V2 y V5 excluidos
- V3 Nadia Gambino
- días comerciales lunes a sábado
- feriados desde feriados.csv

## Tarea

Antes de crear el BAT, auditar:

1. Qué scripts regeneran realmente los datos.
2. Qué inputs necesita cada script.
3. Qué outputs genera cada script.
4. Qué consume server_orbit.py.
5. Qué consume el portal.
6. Si hay scripts obsoletos.
7. Si hay outputs duplicados.
8. Si el historial es idempotente.

## Scripts probables a auditar

Revisar, pero no asumir:

- LEGACY/orbit_matinal_v42.py
- run_orbit.py
- test_datasets_orbit.py
- datasets_orbit.py
- cualquier script que escriba en 03_OUTPUTS, 04_DATASETS_ORBIT o 02_HISTORY

## Punto crítico: historial

Auditar específicamente:

02_HISTORY/historial_ventas_cliente.csv

Responder con precisión:

- qué script lo escribe,
- si hace append,
- si hace overwrite,
- si deduplica,
- si correr dos veces con los mismos inputs duplica registros,
- qué riesgo real hay,
- qué mitigación debe tener el BAT.

Mostrar fragmento relevante del código.

## Requisitos obligatorios del BAT

Antes de correr scripts, debe validar que existan:

- 01_INPUTS/ventas.csv
- 01_INPUTS/resultado.xlsx
- LEGACY/orbit_matinal_v42.py
- test_datasets_orbit.py

Si falta algo, cortar con error claro.

## Backup obligatorio

Antes de sobreescribir nada, crear backup timestamped en:

99_BACKUPS_ORBIT/YYYYMMDD_HHMMSS/

Backupear:

- 03_OUTPUTS/MATINAL_PENA_V42.xlsx
- 02_HISTORY/historial_ventas_cliente.csv
- 04_DATASETS_ORBIT/*.csv

Crear subcarpetas dentro del backup:

- 03_OUTPUTS
- 02_HISTORY
- 04_DATASETS_ORBIT

## Log obligatorio

Crear log en:

99_LOGS_ORBIT/regenerar_datos_YYYYMMDD_HHMMSS.log

El log debe registrar:

- fecha/hora inicio,
- inputs detectados con tamaño y fecha,
- backups creados,
- scripts ejecutados,
- resultado de cada script,
- outputs detectados con tamaño y fecha,
- errores,
- fecha/hora fin.

Crear 99_LOGS_ORBIT si no existe.

## Validación de outputs

Después de correr, validar mínimo:

- 03_OUTPUTS/MATINAL_PENA_V42.xlsx
- 04_DATASETS_ORBIT/clientes_dia.csv
- 04_DATASETS_ORBIT/mod_volumen_vendedor.csv
- 04_DATASETS_ORBIT/mod_ccc_segmento.csv
- 04_DATASETS_ORBIT/mod_11_titulares.csv
- 04_DATASETS_ORBIT/mod_alertas_descuentos.csv
- 04_DATASETS_ORBIT/mod_gastos_accion.csv

Si falta alguno, marcar ERROR.

## Restricciones

No modificar:

- server_orbit.py
- dashboard.jsx
- data.js
- ABRIR_CLAUDE_ORBIT.bat
- 01_INPUTS/resultado.xlsx
- 01_INPUTS/ventas.csv
- CHANGELOG_AI.md
- NEXT_TASK.md

No crear el BAT todavía.

## Entregable solicitado ahora

Primero mostrame:

1. scripts reales detectados,
2. orden correcto de ejecución,
3. auditoría de idempotencia del historial,
4. inputs requeridos,
5. outputs generados,
6. riesgos reales,
7. propuesta completa del BAT,
8. archivos que el BAT crearía o modificaría,
9. qué NO tocarías,
10. si necesitás aprobación antes de crear el archivo.

No crees REGENERAR_DATOS_ORBIT.bat todavía.
No ejecutes scripts.
No commitees.