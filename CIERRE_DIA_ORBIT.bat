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
echo PASO 1/3: Regenerando datasets (motor legacy + CSVs)...
echo Esto actualiza acumulado, sellout, CCC, 11T y todos los KPIs.
echo Puede tardar 1-2 minutos.
echo ============================================================
echo.

call "%ROOT%\REGENERAR_DATOS_ORBIT.bat"

echo.
if exist "%ROOT%\04_DATASETS_ORBIT\mod_volumen_vendedor.csv" (
    echo OK: Datasets regenerados correctamente.
) else (
    echo AVISO: mod_volumen_vendedor.csv no encontrado.
    echo La regeneracion pudo haber fallado. Revisar 99_LOGS_ORBIT.
    echo Presione cualquier tecla para continuar de todas formas...
    pause >nul
)

echo.
echo ============================================================
echo PASO 2/3: Sincronizando planes desde Render...
echo (Los vendedores los enviaron por sus telefonos al servidor en la nube)
echo ============================================================
echo.
python "%ROOT%\sync_planes_render.py"
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
git add "02_HISTORY/historial_ventas_cliente.csv"
git add "02_HISTORY/acumulado_resultado_historico.csv"
git add "04_DATASETS_ORBIT/"
git add "01_INPUTS/ACCIONES COMERCIALES/*/acciones_comerciales_*.csv"

git diff --cached --quiet
if not errorlevel 1 (
    echo No hay cambios nuevos para publicar.
    echo Render ya tiene los datos mas recientes.
    goto fin_publicar
)

git commit -m "data: cierre dia %FECHA_COMMIT% — datasets + inputs actualizados"
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
    echo ============================================================
    echo ERROR: No se pudo sincronizar con el remoto.
    echo Cancelando el rebase para no dejar el repositorio a medias...
    git rebase --abort
    echo Los datos NO se publicaron. Avise a soporte tecnico.
    echo ============================================================
    goto fin_publicar
)

git push origin master
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Fallo el PUSH a GitHub. Los datos NO llegaron a Render.
    echo Revisar conexion a internet y volver a ejecutar el cierre.
    echo ============================================================
    goto fin_publicar
)

echo.
echo OK: Datos publicados en GitHub.
echo Render va a actualizar automaticamente en 2-3 minutos.
start "" "https://orbit-matinal-penaflor.onrender.com"

:fin_publicar

echo.
echo ============================================================
echo LISTO
echo Portal Render: https://orbit-matinal-penaflor.onrender.com
echo (actualiza en 2-3 min luego del push)
echo ============================================================
echo.

pause
