# Commit post ejecución BAT regenerador ORBIT PAV

Aplicá orbit-pav-guardian.

El BAT REGENERAR_DATOS_ORBIT.bat ya fue ejecutado y terminó OK.

Antes de commitear hay que limpiar y stagear solo lo autorizado.

## Acciones autorizadas

1. Revertir el BAT a HEAD porque el cambio actual es corrupción de encoding en comentarios:

git checkout HEAD -- REGENERAR_DATOS_ORBIT.bat

2. Stagear solo:

- .gitignore
- 02_HISTORY/historial_ventas_cliente.csv
- 03_OUTPUTS/MATINAL_PENA_V42.xlsx
- 04_DATASETS_ORBIT/*.csv
- 00_PROMPTS_ORBIT/ejecutar_bat_regenerador_controlado.md

## NO stagear

- 01_INPUTS/resultado.xlsx
- 01_INPUTS/ventas.csv
- 99_LOGS_ORBIT/
- 99_BACKUPS_ORBIT/
- REGENERAR_DATOS_ORBIT.bat.bak_antes_crlf
- REGENERAR_DATOS_ORBIT.bat si después del checkout queda sin cambios

## Verificación antes de commit

Mostrar:

1. git status --short
2. git diff --cached --stat
3. git diff --cached --name-only
4. confirmar que REGENERAR_DATOS_ORBIT.bat ya no aparece modificado
5. confirmar que 01_INPUTS no está staged
6. confirmar que logs/backups no están staged

Si todo está correcto, commitear con:

feat: regenerar datasets ORBIT desde ventas.csv real 2026-05-11

## Después del commit

Mostrar:

1. git status --short
2. git log --oneline -5
3. git show --stat HEAD
4. confirmar que el commit no incluyó 01_INPUTS
5. confirmar que el BAT no quedó con encoding corrupto

No ejecutar el BAT otra vez.
No tocar 01_INPUTS.
No abrir otro bloque.