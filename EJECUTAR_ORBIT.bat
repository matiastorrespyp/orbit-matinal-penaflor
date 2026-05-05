@echo off
title ORBIT - Peñaflor PAV
cd /d C:\Orbit\MATINAL_PENAFLOR

echo ============================================================
echo   ORBIT MATINAL PAV - PENAFLOR
echo   Orbit (c) 2026 - Propiedad de Torres Matias
echo ============================================================
echo.

echo [1/4] Ejecutando pipeline de datos...
python run_orbit.py
if errorlevel 1 (
    echo ERROR en el pipeline. Revisa los logs.
    pause
    exit /b 1
)

echo.
echo [2/4] Generando JSONs para el portal...
python app_publish.py
if errorlevel 1 (
    echo ERROR en app_publish.py
    pause
    exit /b 1
)

echo.
echo [3/4] Iniciando servidor ORBIT...
echo.
echo   URL Local : http://localhost:8502/portal.html
echo   URL Red   : http://%IP%:8502/portal.html
echo.
echo   Vendedores: pav2026
echo   Gerencia  : gerencia2026
echo.
echo   Presiona Ctrl+C para detener el servidor
echo ============================================================
echo.

python server_orbit.py

pause