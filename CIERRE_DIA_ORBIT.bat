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
echo Sincronizando planes desde Render...
echo (Los vendedores los enviaron por sus telefonos al servidor en la nube)
echo.
python "%ROOT%\sync_planes_render.py"
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
echo Abriendo portal...
start "" "%PORTAL%"

echo.
echo ============================================================
echo LISTO
echo 1. Ingresar al portal.
echo 2. Ir a Gerencia.
echo 3. Abrir panel Plan vs Real.
echo ============================================================
echo.

pause