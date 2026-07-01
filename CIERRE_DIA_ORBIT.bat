@echo off
setlocal enabledelayedexpansion

title ORBIT - Cierre del Dia

echo ============================================================
echo ORBIT MATINAL PENAFLOR - CIERRE DEL DIA
echo ============================================================
echo.

set "ROOT=C:\Orbit\MATINAL_PENAFLOR"
set "VENTAS=%ROOT%\01_INPUTS\ventas.csv"
set "PORTAL=https://orbit-matinal-penaflor.onrender.com"

cd /d "%ROOT%"

echo Verificando estado Git antes de iniciar...
echo.

REM ── Bloquear SOLO cambios funcionales (fuera de rutas operativas permitidas).
REM    Rutas operativas que SI pueden estar modificadas antes del cierre:
REM      01_INPUTS/{resultado.xlsx, ventas.csv, ventas_acumulada.csv, clientes.xlsx,
REM                 ventas-clubfaro.csv, INNOVACIONES/, Planes AASS/, ACCIONES COMERCIALES/}
REM      02_HISTORY/  04_DATASETS_ORBIT/
REM    Cualquier .py, .bat, portal.html, config u otro archivo fuera de eso FRENA el cierre.
set "FUNC_PEND="
for /f "delims=" %%i in ('git status --porcelain -- . ":(exclude)01_INPUTS/resultado.xlsx" ":(exclude)01_INPUTS/ventas.csv" ":(exclude)01_INPUTS/ventas_acumulada.csv" ":(exclude)01_INPUTS/clientes.xlsx" ":(exclude)01_INPUTS/ventas-clubfaro.csv" ":(exclude)01_INPUTS/incentivo_club_faro*.xlsx" ":(exclude)01_INPUTS/INNOVACIONES" ":(exclude)01_INPUTS/Planes AASS" ":(exclude)01_INPUTS/ACCIONES COMERCIALES" ":(exclude)02_HISTORY" ":(exclude)04_DATASETS_ORBIT"') do set "FUNC_PEND=1"

if defined FUNC_PEND (
    echo ============================================================
    echo ERROR: Hay cambios FUNCIONALES pendientes fuera de las rutas operativas.
    echo Codigo .py, .bat, portal.html o configuracion sin commitear.
    echo Commitea o resolve esos cambios ANTES de cerrar el dia.
    echo.
    git status --short
    echo ============================================================
    pause
    exit /b 1
)

REM ── Pull SOLO si el repo esta 100%% limpio. Si ya hay inputs operativos
REM    cargados (ventas.csv, etc.), NO se intenta pull con working tree sucio.
set "REPO_DIRTY="
for /f "delims=" %%i in ('git status --porcelain') do set "REPO_DIRTY=1"
if defined REPO_DIRTY goto sin_pull

echo Repositorio limpio. Sincronizando con el remoto (git pull --rebase)...
git pull --rebase origin master
if errorlevel 1 (
    git rebase --abort >nul 2>&1
    echo ============================================================
    echo ERROR: No se pudo sincronizar con el remoto.
    echo No se regenero ningun dato y Render NO fue actualizado.
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

echo Validando archivo ventas.csv...
echo.

if not exist "%VENTAS%" (
    echo ERROR: No existe el archivo:
    echo %VENTAS%
    echo.
    echo Pegue primero el ventas.csv nuevo en 01_INPUTS.
    pause
    exit /b 1
)

python -c "import pandas as pd; p=r'%VENTAS%'; df=pd.read_csv(p, sep=';', encoding='latin1'); print('Filas detectadas:', len(df)); assert 'FechaComprobante' in df.columns, 'Falta columna FechaComprobante'; f=pd.to_datetime(df['FechaComprobante'], dayfirst=True, errors='coerce'); print('Fecha mas reciente:', f.max().strftime('%%Y-%%m-%%d') if f.notna().any() else 'SIN_FECHA')"

if errorlevel 1 (
    echo.
    echo ERROR: ventas.csv no pudo validarse.
    echo Revisar separador, encoding o columna FechaComprobante.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo PASO 0/3: Validando consistencia resultado.xlsx ^<-^> ventas.csv...
echo (Un vendedor no puede tener acumulado sin lineas de venta)
echo ============================================================
echo.

python "%ROOT%\validar_consistencia_cierre.py"
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: resultado.xlsx y ventas.csv estan desincronizados.
    echo No se regenero ningun dato. NO se publico. Render NO fue actualizado.
    echo Re-exporta ambos del MISMO corte del ERP y reintenta el cierre.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo PASO 1/3: Regenerando datasets (motor legacy + CSVs)...
echo Esto actualiza acumulado, sellout, CCC, 11T y todos los KPIs.
echo Puede tardar 1-2 minutos.
echo ============================================================
echo.

call "%ROOT%\REGENERAR_DATOS_ORBIT.bat"

echo.
if errorlevel 1 (
    echo ============================================================
    echo ERROR: La regeneracion de datasets FALLO.
    echo Los datos NO se publicaron. NO se hace commit ni push.
    echo Render se queda con los datos anteriores ^(no avanza el dia^).
    echo Revisar el ultimo log en 99_LOGS_ORBIT y reintentar el cierre.
    echo ============================================================
    echo.
    pause
    exit /b 1
)
echo OK: Datasets regenerados correctamente.
echo.

echo ============================================================
echo PASO 2/3: Sincronizando planes desde Render...
echo (Los vendedores los enviaron por sus telefonos al servidor en la nube)
echo ============================================================
echo.
python "%ROOT%\sync_planes_render.py"
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: No se pudieron sincronizar planes desde Render.
    echo Render NO fue actualizado.
    echo ============================================================
    pause
    exit /b 1
)
echo.

echo ============================================================
echo PASO 3/3: Publicando datos en GitHub para actualizar Render...
echo ============================================================
echo.

for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set FECHA_COMMIT=%%i

echo Preparando archivos para commit...
git add "01_INPUTS/resultado.xlsx"
git add "01_INPUTS/ventas.csv"
git add "01_INPUTS/ventas_acumulada.csv"
git add "01_INPUTS/clientes.xlsx"
git add "01_INPUTS/ventas-clubfaro.csv"
git add "01_INPUTS/incentivo_club_faro*.xlsx"
git add "01_INPUTS/INNOVACIONES/Innovaciones.xlsx"
git add "01_INPUTS/Planes AASS"
git add "02_HISTORY/historial_ventas_cliente.csv"
git add "02_HISTORY/acumulado_resultado_historico.csv"
git add "04_DATASETS_ORBIT/clientes_dia.csv"
git add "04_DATASETS_ORBIT/hist_cliente_mes.csv"
git add "04_DATASETS_ORBIT/hist_cliente_producto.csv"
git add "04_DATASETS_ORBIT/hist_cliente_resumen.csv"
git add "04_DATASETS_ORBIT/mod_11_titulares.csv"
git add "04_DATASETS_ORBIT/mod_11t_acum.csv"
git add "04_DATASETS_ORBIT/mod_acciones_analisis.csv"
git add "04_DATASETS_ORBIT/mod_acciones_ranking.csv"
git add "04_DATASETS_ORBIT/mod_alertas_descuentos.csv"
git add "04_DATASETS_ORBIT/mod_ccc_segmento.csv"
git add "04_DATASETS_ORBIT/mod_cobertura_acum.csv"
git add "04_DATASETS_ORBIT/mod_cobertura_acum_detalle.csv"
git add "04_DATASETS_ORBIT/mod_gastos_accion.csv"
git add "04_DATASETS_ORBIT/mod_innovaciones_segmento.csv"
git add "04_DATASETS_ORBIT/mod_planes_as.csv"
git add "04_DATASETS_ORBIT/mod_sellout_categoria.csv"
git add "04_DATASETS_ORBIT/mod_sincargos_envios.csv"
git add "04_DATASETS_ORBIT/mod_vda_clientes_detalle.csv"
git add "04_DATASETS_ORBIT/mod_vda_productos.csv"
git add "04_DATASETS_ORBIT/mod_vda_productos_revision_necesaria.csv"
git add "04_DATASETS_ORBIT/mod_vda_ranking_vendedor.csv"
git add "04_DATASETS_ORBIT/mod_vda_resumen_mensual.csv"
git add "04_DATASETS_ORBIT/mod_volumen_vendedor.csv"
git add "01_INPUTS/ACCIONES COMERCIALES/*/acciones_comerciales_*.csv"

REM ── Abortar si quedan cambios FUERA del allowlist operativo (desarrollo colado).
REM    Los archivos operativos ya quedaron staged por los git add de arriba.
set "FUERA_ALLOW="
for /f "delims=" %%i in ('git status --porcelain -- . ":(exclude)01_INPUTS/resultado.xlsx" ":(exclude)01_INPUTS/ventas.csv" ":(exclude)01_INPUTS/ventas_acumulada.csv" ":(exclude)01_INPUTS/clientes.xlsx" ":(exclude)01_INPUTS/ventas-clubfaro.csv" ":(exclude)01_INPUTS/incentivo_club_faro*.xlsx" ":(exclude)01_INPUTS/INNOVACIONES" ":(exclude)01_INPUTS/Planes AASS" ":(exclude)01_INPUTS/ACCIONES COMERCIALES" ":(exclude)02_HISTORY" ":(exclude)04_DATASETS_ORBIT"') do set "FUERA_ALLOW=1"
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
    echo No hay cambios nuevos para publicar.
    echo No se ejecuto push; Render NO fue actualizado por este cierre.
    goto fin_error
)

git commit -m "data: cierre dia %FECHA_COMMIT% — datasets + inputs actualizados"
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
    echo ERROR: Fallo el PUSH a GitHub. Los datos NO llegaron a Render.
    echo Revisar conexion a internet y volver a ejecutar el cierre.
    echo ============================================================
    goto fin_error
)

echo.
echo OK: Datos publicados en GitHub.
echo Render va a actualizar automaticamente en 2-3 minutos.
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
echo Portal Render: https://orbit-matinal-penaflor.onrender.com
echo (actualiza en 2-3 min luego del push)
echo ============================================================
echo.

pause
exit /b 0
