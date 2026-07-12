@echo off
setlocal enabledelayedexpansion

title ORBIT - Cierre de Mes

echo ============================================================
echo ORBIT MATINAL PENAFLOR - CIERRE DE MES
echo ============================================================
echo.

set "ROOT=C:\Orbit\MATINAL_PENAFLOR"
set "PORTAL=https://orbit-matinal-penaflor.onrender.com"
cd /d "%ROOT%"

echo Verificando estado Git antes de iniciar...
echo.

REM -- Bloquear SOLO cambios funcionales (fuera de rutas operativas permitidas).
REM    La clasificacion POR RUTA vive en check_git_cierre.py (arbol 01_INPUTS/,
REM    02_HISTORY/, 04_DATASETS_ORBIT/, 06_APP_DATA/, 07_CIERRES_MENSUALES/ = operativo).
REM    Cualquier .py, .bat, portal.html, config u otro archivo fuera de eso FRENA el cierre.
python "%ROOT%\check_git_cierre.py"
if errorlevel 1 (
    echo ============================================================
    echo Commitea o resolve esos cambios ANTES de cerrar el mes.
    echo ============================================================
    pause
    exit /b 1
)

REM -- Pull SOLO si el repo esta 100%% limpio. Si ya hay inputs operativos
REM    cargados, NO se intenta pull con working tree sucio.
set "REPO_DIRTY="
for /f "delims=" %%i in ('git status --porcelain') do set "REPO_DIRTY=1"
if defined REPO_DIRTY goto sin_pull

echo Repositorio limpio. Sincronizando con el remoto (git pull --rebase)...
git pull --rebase origin master
if errorlevel 1 (
    git rebase --abort >nul 2>&1
    echo ============================================================
    echo ERROR: No se pudo sincronizar con el remoto.
    echo No se versiono ningun cierre y Render NO fue actualizado.
    echo Resolver el estado Git/red y volver a ejecutar el cierre.
    echo ============================================================
    pause
    exit /b 1
)
echo OK: repositorio sincronizado.
goto pull_ok

:sin_pull
echo Hay inputs operativos ya cargados. No se puede hacer pull con cambios locales.
echo Si necesitas sincronizar con GitHub, hacelo antes de cargar los inputs.

:pull_ok
echo.

REM -- Refrescar ventas_mes.csv (cierre congelado) desde ventas.csv vivo. Sin esto, el cierre
REM    autodetecta el mes anterior (si ventas_mes quedo viejo) y "no hace nada". Solo en modo
REM    automatico (sin argumentos); si se fuerza un mes manual NO se toca ventas_mes.csv.
if "%~1"=="" (
    echo Preparando ventas_mes.csv del mes desde ventas.csv vivo...
    python "%ROOT%\tools\preparar_ventas_mes.py"
    if errorlevel 1 (
        echo ============================================================
        echo ERROR: no se pudo preparar ventas_mes.csv desde ventas.csv.
        echo No se cerro el mes. Revisar 01_INPUTS\ventas.csv.
        echo ============================================================
        pause
        exit /b 1
    )
) else (
    echo Modo manual ^(argumento "%~1"^): NO se regenera ventas_mes.csv.
    echo Se usara el 01_INPUTS\ventas_mes.csv que ya esta cargado.
)
echo.

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

echo Preparando archivos para commit...
git add "01_INPUTS/cierres mes/"

REM -- Abortar si quedan cambios FUERA del allowlist operativo (desarrollo colado).
REM    El cierre de mes solo versiona 01_INPUTS/cierres mes/; los inputs fuente
REM    del mes pueden quedar modificados sin frenar (no se commitean aca).
python "%ROOT%\check_git_cierre.py"
if errorlevel 1 (
    echo.
    echo No se hace commit ni push para no mezclar desarrollo con cierre.
    goto fin_error
)

git diff --cached --quiet
if not errorlevel 1 (
    goto fin_nada
)

git commit -m "cierre mes: archivos versionados (%FECHA_COMMIT%)"
if errorlevel 1 (
    echo.
    echo ERROR: Fallo el commit. Verificar estado de git. NO se publico.
    echo Render NO fue actualizado.
    goto fin_error
)

git push origin master
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Fallo el PUSH a GitHub. El cierre NO llego a Render.
    echo Revisar conexion a internet y volver a ejecutar.
    echo ============================================================
    goto fin_error
)

echo.
echo OK: Cierre publicado en GitHub. Render actualiza en 2-3 minutos.
start "" "https://orbit-matinal-penaflor.onrender.com"
goto fin_ok

:fin_error

echo.
echo ============================================================
echo CIERRE NO PUBLICADO
echo Render NO fue actualizado por este cierre.
echo Portal Render: https://orbit-matinal-penaflor.onrender.com
echo ============================================================
echo.

pause
exit /b 1

:fin_nada

echo.
echo ============================================================
echo NADA NUEVO QUE CERRAR
echo Este mes ya estaba cerrado (los archivos del cierre ya existen).
echo No se genero ni publico nada nuevo. Render queda igual.
echo Si querias re-generar este mes pisando con las fuentes actuales,
echo ejecuta:  CIERRE_MES_ORBIT.bat MMAAAA --force   (ej: 062026 --force)
echo ============================================================
echo.

pause
exit /b 0

:fin_ok

echo.
echo ============================================================
echo LISTO
echo Pantalla: Portal gerencial - Cierre de Mes
echo Log del cierre en: 99_LOGS_ORBIT\
echo ============================================================
echo.

pause
exit /b 0
