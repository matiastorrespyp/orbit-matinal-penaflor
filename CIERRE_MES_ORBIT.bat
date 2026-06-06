@echo off
setlocal enabledelayedexpansion

title ORBIT - Cierre de Mes

echo ============================================================
echo ORBIT MATINAL PENAFLOR - CIERRE DE MES
echo ============================================================
echo.

set "ROOT=C:\Orbit\MATINAL_PENAFLOR"
cd /d "%ROOT%"

echo Generando/versionando los archivos del mes en 01_INPUTS\cierres mes\ ...
echo (toma las fuentes que dejaste en 01_INPUTS y las copia con sufijo _MMAAAA)
echo.

python "%ROOT%\tools\cerrar_mes.py" %*

if errorlevel 1 (
    echo.
    echo ============================================================
    echo CIERRE INCOMPLETO: faltan archivos fuente obligatorios.
    echo Deja en 01_INPUTS: resultado.xlsx, ventas_mes.csv, objetivo 11T.xlsx
    echo y volve a ejecutar este .bat. NO se publico nada.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Publicando el cierre en GitHub para actualizar Render...
echo ============================================================
echo.

for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set FECHA_COMMIT=%%i

git add "01_INPUTS/cierres mes/"

git diff --cached --quiet
if not errorlevel 1 (
    echo No hay archivos nuevos del cierre para publicar.
    echo Render ya tiene la version mas reciente.
    goto fin_publicar
)

git commit -m "cierre mes: archivos versionados (%FECHA_COMMIT%)"
if errorlevel 1 (
    echo.
    echo ERROR: Fallo el commit. Verificar estado de git. NO se publico.
    goto fin_publicar
)

echo.
echo Sincronizando con el remoto antes de publicar (git pull --rebase)...
git pull --rebase origin master
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo sincronizar con el remoto. Cancelando el rebase...
    git rebase --abort
    echo Los datos NO se publicaron. Avise a soporte tecnico.
    goto fin_publicar
)

git push origin master
if errorlevel 1 (
    echo.
    echo ERROR: Fallo el PUSH a GitHub. El cierre NO llego a Render.
    echo Revisar conexion a internet y volver a ejecutar.
    goto fin_publicar
)

echo.
echo OK: Cierre publicado en GitHub. Render actualiza en 2-3 minutos.
start "" "https://orbit-matinal-penaflor.onrender.com"

:fin_publicar

echo.
echo ============================================================
echo LISTO
echo Pantalla: Portal gerencial - Cierre de Mes
echo Log del cierre en: 99_LOGS_ORBIT\
echo ============================================================
echo.

pause
