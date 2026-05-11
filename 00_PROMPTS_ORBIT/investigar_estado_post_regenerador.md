# Investigar estado post-regenerador ORBIT PAV

Aplicá la skill orbit-pav-guardian.

No ejecutes REGENERAR_DATOS_ORBIT.bat.
No ejecutes scripts.
No modifiques archivos.
No commitees.
No toques 01_INPUTS.

## Contexto

El BAT REGENERAR_DATOS_ORBIT.bat ya fue commiteado en:

fd5206a chore: agregar regenerador de datos ORBIT PAV

Pero al retomar aparecieron archivos modificados que hay que investigar antes de ejecutar cualquier cosa:

- 02_HISTORY/historial_ventas_cliente.csv
- LEGACY/__pycache__/orbit_matinal_v42.cpython-314.pyc

También sigue modificado:

- 01_INPUTS/resultado.xlsx
- 01_INPUTS/ventas.csv

Y existe como untracked:

- 00_PROMPTS_ORBIT/retomar_orbit_pav_regenerador.md

## Objetivo

Diagnosticar el estado actual sin modificar nada.

No quiero ejecutar el BAT todavía hasta saber por qué aparece modificado el historial y el pyc.

## Tareas

### 1. Estado Git

Mostrar:

- git status --short
- git log --oneline -8

### 2. Investigar historial

Para:

02_HISTORY/historial_ventas_cliente.csv

Mostrar:

- si está trackeado por Git
- git diff --stat del archivo
- cantidad de líneas actual
- cantidad de líneas en HEAD
- primeras diferencias relevantes, sin volcar todo el archivo
- si parece cambio real de datos
- si parece cambio de encoding, formato, orden o fin de línea
- si puede haber sido modificado por una ejecución anterior del motor legacy
- recomendación: conservar, revertir o analizar más

No modificarlo.

### 3. Investigar pyc

Para:

LEGACY/__pycache__/orbit_matinal_v42.cpython-314.pyc

Mostrar:

- si está trackeado por Git
- por qué aparece modificado aunque .gitignore tenga __pycache__/ y *.pyc
- si conviene sacarlo del índice con git rm --cached
- no ejecutar git rm todavía
- no modificarlo

### 4. Confirmar BAT

Confirmar:

- REGENERAR_DATOS_ORBIT.bat existe
- REGENERAR_DATOS_ORBIT.bat está commiteado en fd5206a
- REGENERAR_DATOS_ORBIT.bat no fue ejecutado
- 99_LOGS_ORBIT no existe o existe
- 99_BACKUPS_ORBIT no existe o existe

### 5. Prompt de retoma

Para:

00_PROMPTS_ORBIT/retomar_orbit_pav_regenerador.md

Confirmar:

- si existe
- si es solo prompt de trabajo
- si conviene commitearlo después
- no hacer git add todavía

## Entregable

Mostrar una tabla final:

Archivo | Estado | Causa probable | Riesgo | Recomendación

Incluir:

- 01_INPUTS/resultado.xlsx
- 01_INPUTS/ventas.csv
- 02_HISTORY/historial_ventas_cliente.csv
- LEGACY/__pycache__/orbit_matinal_v42.cpython-314.pyc
- 00_PROMPTS_ORBIT/retomar_orbit_pav_regenerador.md
- REGENERAR_DATOS_ORBIT.bat

## Restricciones

No ejecutar BAT.
No ejecutar scripts.
No modificar archivos.
No hacer git add.
No hacer git commit.
No revertir archivos.
No borrar archivos.
No tocar 01_INPUTS.

Esperar mi aprobación antes de cualquier acción.