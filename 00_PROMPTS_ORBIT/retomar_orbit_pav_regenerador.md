# Retomar ORBIT PAV — Regenerador de datos

Aplicá la skill orbit-pav-guardian.

Estamos retomando el bloque de creación del BAT:

REGENERAR_DATOS_ORBIT.bat

## Estado esperado

En la sesión anterior se había creado el BAT, pero no debía ejecutarse todavía.

Archivos esperados:

- REGENERAR_DATOS_ORBIT.bat
- 00_PROMPTS_ORBIT/crear_bat_regenerar_datos.md
- 00_PROMPTS_ORBIT/ajustar_bat_regenerar_datos_final.md

Archivos que NO deben tocarse ni commitearse:

- 01_INPUTS/resultado.xlsx
- 01_INPUTS/ventas.csv

## Objetivo de esta retoma

No modificar nada todavía.

Primero verificar el estado real del proyecto y confirmar si hay un commit pendiente relacionado con el BAT.

## Tareas de solo lectura

Mostrar:

1. git status --short
2. git diff --cached --name-only
3. git diff --cached --stat
4. git log --oneline -8
5. si REGENERAR_DATOS_ORBIT.bat existe
6. si REGENERAR_DATOS_ORBIT.bat está staged o untracked
7. si 00_PROMPTS_ORBIT/crear_bat_regenerar_datos.md existe
8. si 00_PROMPTS_ORBIT/ajustar_bat_regenerar_datos_final.md existe
9. si hay carpetas 99_LOGS_ORBIT o 99_BACKUPS_ORBIT
10. si el BAT fue ejecutado o no

## Validación del BAT

Leer el contenido real de:

REGENERAR_DATOS_ORBIT.bat

y confirmar que contiene:

- chequeo de Excel bloqueado con PowerShell File.Open
- if errorlevel 1 (
- backup en 99_BACKUPS_ORBIT
- log en 99_LOGS_ORBIT
- py test_legacy_run.py
- py test_datasets_orbit.py
- exit /b 1 si faltan outputs críticos
- no abre portal
- no levanta server_orbit.py
- no toca 01_INPUTS
- no ejecuta run_orbit_diario.py
- no ejecuta app_publish.py

## Si hay archivos staged

Confirmar si los staged son únicamente:

- REGENERAR_DATOS_ORBIT.bat
- 00_PROMPTS_ORBIT/crear_bat_regenerar_datos.md
- 00_PROMPTS_ORBIT/ajustar_bat_regenerar_datos_final.md

Si aparece cualquier otro archivo staged, NO commitear.

## Si no hay archivos staged

Mostrar qué archivos están untracked o modificados y recomendar el próximo paso.

## Restricciones

No ejecutes REGENERAR_DATOS_ORBIT.bat.
No ejecutes scripts.
No crees logs.
No crees backups.
No modifiques archivos.
No commitees.
No toques 01_INPUTS.

## Entregable

Mostrar:

1. estado real actual,
2. archivos staged,
3. archivos untracked,
4. confirmación de si el BAT existe,
5. confirmación de si el BAT fue ejecutado,
6. recomendación exacta:
   - commitear,
   - ajustar BAT,
   - stagear archivos,
   - o frenar.

Esperar mi aprobación antes de cualquier acción.