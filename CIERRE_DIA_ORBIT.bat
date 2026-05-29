@echo off
setlocal enabledelayedexpansion

title ORBIT - Cierre del Dia

echo ============================================================
echo ORBIT MATINAL PENAFLOR - CIERRE DEL DIA
echo ============================================================
echo.

set "ROOT=C:\Orbit\MATINAL_PENAFLOR"
set "VENTAS=%ROOT%\01_INPUTS\ventas.csv"
set "PORTAL=http://127.0.0.1:8502"

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
echo PASO 3/3: Iniciando servidor local...
echo ============================================================
echo.

echo Cerrando servidor ORBIT anterior si existe...
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8502" ^| findstr "LISTENING"') do (
    echo Cerrando proceso en puerto 8502: %%a
    taskkill /PID %%a /F >nul 2>nul
)

timeout /t 2 >nul

echo.
echo Iniciando servidor ORBIT local...
echo.

start "ORBIT - Server Local" cmd /k cd /d "%ROOT%" ^&^& python server_orbit.py

echo Esperando inicio del servidor...
timeout /t 6 >nul

echo.
echo Abriendo portal local...
start "" "%PORTAL%"

echo.
echo ============================================================
echo PASO 4/4: Publicando datos en GitHub para actualizar Render...
echo ============================================================
echo.

for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set FECHA_COMMIT=%%i

echo Preparando archivos para commit...
git add 01_INPUTS\resultado.xlsx
git add 01_INPUTS\ventas.csv
git add 01_INPUTS\ventas_acumulada.csv
git add 04_DATASETS_ORBIT\*.csv
git add orbit.db

git diff --cached --quiet
if %ERRORLEVEL% equ 0 (
    echo No hay cambios nuevos para publicar.
) else (
    git commit -m "data: cierre dia %FECHA_COMMIT% — datasets + inputs actualizados"
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Fallo el commit. Verificar estado de git.
    ) else (
        git push origin master
        if %ERRORLEVEL% neq 0 (
            echo ERROR: Fallo el push. Verificar conexion a internet.
        ) else (
            echo OK: Datos publicados en GitHub.
            echo.
            echo ============================================================
            echo SIGUIENTE PASO: Hacer deploy manual en Render
            echo Abriendo Render dashboard...
            echo ============================================================
            start "" "https://dashboard.render.com"
            echo.
            echo En Render: seleccionar el servicio orbit-penaflor-pav
            echo           hacer clic en "Manual Deploy" ^> "Deploy latest commit"
            echo.
            echo El portal https://orbit-matinal-penaflor.onrender.com
            echo estara actualizado en 2-3 minutos.
        )
    )
)

echo.
echo ============================================================
echo LISTO
echo Portal local : %PORTAL%
echo Portal Render: https://orbit-matinal-penaflor.onrender.com
echo ============================================================
echo.

pause