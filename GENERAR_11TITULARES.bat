@echo off
chcp 65001 >nul
title ORBIT - 11 Titulares por Vendedor y Dia
echo.
echo  ====================================================
echo   ORBIT PAV MATINAL  -  11 TITULARES EXCEL
echo  ====================================================
echo.
echo  Fuente : 01_INPUTS\ventas_acumulada.csv
echo  Clientes: 01_INPUTS\clientes.xlsx
echo  Output : 03_OUTPUTS\11 titulares.xlsx
echo.
cd /d "%~dp0"
python generar_11titulares_excel.py
if errorlevel 1 (
    echo.
    echo  [ERROR] Revisa los mensajes arriba.
    pause
    exit /b 1
)
echo.
echo  Abriendo el archivo...
start "" "03_OUTPUTS\11 titulares.xlsx"
pause
