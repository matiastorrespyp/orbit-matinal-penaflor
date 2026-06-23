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
REM    Rutas operativas que SI pueden estar modificadas antes del cierre de mes:
REM      01_INPUTS/{cierres mes/, resultado.xlsx, ventas.csv, ventas_mes.csv,
REM                 ventas_acumulada.csv, clientes.xlsx, ventas-clubfaro.csv,
REM                 objetivo 11T.xlsx, INNOVACIONES/, Planes AASS/, PLANES_AS/,
REM                 ACCIONES COMERCIALES/}
REM      02_HISTORY/  04_DATASETS_ORBIT/
REM    Cualquier .py, .bat, portal.html, config u otro archivo fuera de eso FRENA el cierre.
set "FUNC_PEND="
for /f "delims=" %%i in ('git status --porcelain -- . ":(exclude)01_INPUTS/cierres mes" ":(exclude)01_INPUTS/resultado.xlsx" ":(exclude)01_INPUTS/ventas.csv" ":(exclude)01_INPUTS/ventas_mes.csv" ":(exclude)01_INPUTS/ventas_acumulada.csv" ":(exclude)01_INPUTS/clientes.xlsx" ":(exclude)01_INPUTS/ventas-clubfaro.csv" ":(exclude)01_INPUTS/objetivo 11T.xlsx" ":(exclude)01_INPUTS/INNOVACIONES" ":(exclude)01_INPUTS/Planes AASS" ":(exclude)01_INPUTS/PLANES_AS" ":(exclude)01_INPUTS/ACCIONES COMERCIALES" ":(exclude)02_HISTORY" ":(exclude)04_DATASETS_ORBIT"') do set "FUNC_PEND=1"

if defined FUNC_PEND (
    echo ============================================================
    echo ERROR: Hay cambios FUNCIONALES pendientes fuera de las rutas operativas.
    echo Codigo .py, .bat, portal.html o configuracion sin commitear.
    echo Commitea o resolve esos cambios ANTES de cerrar el mes.
    echo.
    git status --short
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
set "FUERA_ALLOW="
for /f "delims=" %%i in ('git status --porcelain -- . ":(exclude)01_INPUTS/cierres mes" ":(exclude)01_INPUTS/resultado.xlsx" ":(exclude)01_INPUTS/ventas.csv" ":(exclude)01_INPUTS/ventas_mes.csv" ":(exclude)01_INPUTS/ventas_acumulada.csv" ":(exclude)01_INPUTS/clientes.xlsx" ":(exclude)01_INPUTS/ventas-clubfaro.csv" ":(exclude)01_INPUTS/objetivo 11T.xlsx" ":(exclude)01_INPUTS/INNOVACIONES" ":(exclude)01_INPUTS/Planes AASS" ":(exclude)01_INPUTS/PLANES_AS" ":(exclude)01_INPUTS/ACCIONES COMERCIALES" ":(exclude)02_HISTORY" ":(exclude)04_DATASETS_ORBIT"') do set "FUERA_ALLOW=1"
if defined FUERA_ALLOW (
    echo.
    echo ============================================================
    echo ERROR: Quedaron cambios fuera de las rutas operativas permitidas.
    echo No se hace commit ni push para no mezclar desarrollo con cierre.
    echo.
    git status --short
    echo ============================================================
    goto fin_error
)

git diff --cached --quiet
if not errorlevel 1 (
    echo No hay archivos nuevos del cierre para publicar.
    echo Render ya tiene la version mas reciente; este cierre no publico nada nuevo.
    goto fin_ok
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
