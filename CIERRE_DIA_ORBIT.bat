@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
title ORBIT - Cierre del Dia

:: ============================================================
:: CIERRE_DIA_ORBIT.bat
:: Ejecutar DESPUES de pegar el nuevo ventas.csv.
:: Reinicia el servidor ORBIT y abre Plan vs Real.
:: NO toca 01_INPUTS. NO regenera datasets completos.
:: ============================================================

set BASE=C:\Orbit\MATINAL_PENAFLOR

echo.
echo  ===================================================
echo   ORBIT ^| Cierre del Dia ^| PAV Penaflor
echo  ===================================================
echo.

:: 1. Validar que ventas.csv existe
if not exist "%BASE%\01_INPUTS\ventas.csv" (
    echo  ERROR: No existe 01_INPUTS\ventas.csv
    echo  Pegar el archivo antes de ejecutar este BAT.
    echo.
    pause
    exit /b 1
)

:: 2. Verificar fecha mas reciente en ventas.csv
echo  Verificando datos en ventas.csv...
py -3.12 -c "
import pandas as pd, sys
try:
    df = pd.read_csv(r'%BASE%\01_INPUTS\ventas.csv', sep=';', encoding='latin1', usecols=['FechaComprobante','CodVendedor','ImporteNetoItem'])
    df['f'] = pd.to_datetime(df['FechaComprobante'], dayfirst=True, errors='coerce')
    df['imp'] = pd.to_numeric(df['ImporteNetoItem'].astype(str).str.replace(',','.'), errors='coerce')
    max_f = df['f'].dropna().max()
    filas = len(df)
    vend_unicos = df['CodVendedor'].dropna().nunique()
    print(f'  Fecha mas reciente : {max_f.strftime(\"%d/%m/%Y\")}')
    print(f'  Filas en archivo   : {filas:,}')
    print(f'  Vendedores         : {vend_unicos}')
except Exception as e:
    print(f'  ERROR al leer ventas.csv: {e}')
    sys.exit(1)
" 2>&1
if %ERRORLEVEL% neq 0 (
    echo  Error al leer ventas.csv. Ver mensaje arriba.
    echo.
    pause
    exit /b 1
)

echo.

:: 3. Cerrar instancias anteriores del servidor en puerto 8502
echo  Cerrando instancias anteriores en puerto 8502...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8502 " ^| findstr "LISTENING"') do (
    if not "%%p"=="" (
        taskkill /PID %%p /F >nul 2>&1
    )
)
timeout /t 1 /nobreak >nul

:: 4. Iniciar servidor ORBIT en ventana separada
echo  Iniciando servidor ORBIT...
start "ORBIT Server" cmd /k "cd /d %BASE% && title ORBIT Server - Puerto 8502 && py -3.12 server_orbit.py"
echo  Esperando que el servidor inicie (4 seg)...
timeout /t 4 /nobreak >nul

:: 5. Abrir el portal en el navegador
echo  Abriendo portal...
start "" "http://localhost:8502"

echo.
echo  ===================================================
echo   ORBIT iniciado correctamente.
echo.
echo   URL: http://localhost:8502
echo   Ir a: Plan vs Real (icono 📊 en el menu)
echo.
echo   Los datos de venta se leen directo de ventas.csv.
echo   No necesitas regenerar datasets para ver Plan vs Real.
echo  ===================================================
echo.
pause
endlocal
