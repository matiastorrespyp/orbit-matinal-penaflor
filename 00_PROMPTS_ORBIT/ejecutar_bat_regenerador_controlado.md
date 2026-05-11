# Ejecutar BAT regenerador ORBIT PAV de forma controlada

Aplicá la skill orbit-pav-guardian.

## Contexto

El repo ya quedó preparado para ejecutar el BAT regenerador:

- El BAT REGENERAR_DATOS_ORBIT.bat ya está commiteado.
- El pyc trackeado fue desindexado y commiteado.
- Los prompts de trabajo fueron commiteados.
- 02_HISTORY/historial_ventas_cliente.csv quedó limpio en HEAD.
- 01_INPUTS/ventas.csv se acepta como fuente real de Gescom.
- 01_INPUTS/resultado.xlsx se acepta como input real.
- Las ventas atípicas del 09/05 se consideran reales de Gescom, no contaminación.
- El BAT todavía no fue ejecutado.

## Objetivo

Ejecutar únicamente:

REGENERAR_DATOS_ORBIT.bat

de forma controlada, dejando backup, log y outputs validados.

## Antes de ejecutar

Mostrar y confirmar:

1. Ruta actual:
   C:\Orbit\MATINAL_PENAFLOR

2. git status --short

3. Confirmar:
   - no hay archivos staged
   - 01_INPUTS/ventas.csv está modificado pero no staged
   - 01_INPUTS/resultado.xlsx está modificado pero no staged
   - 02_HISTORY/historial_ventas_cliente.csv está limpio
   - REGENERAR_DATOS_ORBIT.bat existe
   - 99_LOGS_ORBIT no existe o indicar si existe
   - 99_BACKUPS_ORBIT no existe o indicar si existe

## Ejecución autorizada

Ejecutar únicamente:

cmd /c REGENERAR_DATOS_ORBIT.bat

No ejecutar manualmente:

- test_legacy_run.py
- test_datasets_orbit.py
- run_orbit_diario.py
- app_publish.py
- server_orbit.py
- ningún otro BAT

## Después de ejecutar

Mostrar:

1. Resultado de ejecución:
   - OK
   - ERROR

2. git status --short

3. Carpeta backup creada en:
   99_BACKUPS_ORBIT

4. Log creado en:
   99_LOGS_ORBIT

5. Últimas 80 líneas del log.

6. Confirmación de outputs críticos:

- 03_OUTPUTS/MATINAL_PENA_V42.xlsx
- 04_DATASETS_ORBIT/clientes_dia.csv
- 04_DATASETS_ORBIT/mod_volumen_vendedor.csv
- 04_DATASETS_ORBIT/mod_ccc_segmento.csv
- 04_DATASETS_ORBIT/mod_11_titulares.csv
- 04_DATASETS_ORBIT/mod_alertas_descuentos.csv
- 04_DATASETS_ORBIT/mod_gastos_accion.csv

7. Confirmar si 02_HISTORY/historial_ventas_cliente.csv fue regenerado.

8. Confirmar que 01_INPUTS no fue modificado por el BAT.

9. Confirmar que no se hizo git add ni commit.

## Restricciones

No hacer git add.
No commitear.
No abrir otro bloque.
No tocar 01_INPUTS.
No modificar código.
No ejecutar scripts por fuera del BAT.
No levantar el portal todavía.

## Entregable final

Mostrar una tabla:

Archivo / carpeta | Estado antes | Estado después | Observación

Incluir:

- 01_INPUTS/ventas.csv
- 01_INPUTS/resultado.xlsx
- 02_HISTORY/historial_ventas_cliente.csv
- 03_OUTPUTS/MATINAL_PENA_V42.xlsx
- 04_DATASETS_ORBIT/clientes_dia.csv
- 04_DATASETS_ORBIT/mod_volumen_vendedor.csv
- 04_DATASETS_ORBIT/mod_ccc_segmento.csv
- 04_DATASETS_ORBIT/mod_11_titulares.csv
- 04_DATASETS_ORBIT/mod_alertas_descuentos.csv
- 04_DATASETS_ORBIT/mod_gastos_accion.csv
- 99_LOGS_ORBIT
- 99_BACKUPS_ORBIT

Esperar instrucciones después de mostrar el resultado.