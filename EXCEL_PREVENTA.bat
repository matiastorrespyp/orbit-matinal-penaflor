@echo off
setlocal

title ORBIT - Excel Preventa 11 Titulares

echo ============================================================
echo ORBIT MATINAL PENAFLOR - EXCEL DE PREVENTA (11 TITULARES)
echo ============================================================
echo.
echo Genera un Excel con una hoja por dia de visita y, por cliente,
echo la cobertura de los 11 Titulares y las botellas a vender.
echo.

set "ROOT=C:\Orbit\MATINAL_PENAFLOR"
cd /d "%ROOT%"

python "%ROOT%\tools\excel_preventa.py"

if errorlevel 1 (
    echo.
    echo ERROR: no se pudo generar el Excel. Revisar que existan
    echo 01_INPUTS\clientes.xlsx y 01_INPUTS\ventas_acumulada.csv.
    pause
    exit /b 1
)

echo.
echo Abriendo el Excel generado...
for /f "delims=" %%f in ('dir /b /o-d "%ROOT%\03_OUTPUTS\PREVENTA_11T_*.xlsx" 2^>nul') do (
    start "" "%ROOT%\03_OUTPUTS\%%f"
    goto abierto
)
:abierto

echo.
echo ============================================================
echo LISTO. El archivo quedo en 03_OUTPUTS\PREVENTA_11T_*.xlsx
echo ============================================================
echo.
pause
