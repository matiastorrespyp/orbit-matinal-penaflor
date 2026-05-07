@echo off
title ORBIT - Portal Penaflor PAV
cd /d C:\Orbit\MATINAL_PENAFLOR

echo ============================================================
echo   ORBIT MATINAL PENAFLOR
echo ============================================================
echo.
echo   Portal:      http://localhost:8502/
echo   Diagnostico: http://localhost:8502/api/diagnostico
echo   Dashboard:   http://localhost:8502/api/dashboard
echo.
echo   Ctrl+C para detener el servidor.
echo ============================================================
echo.

:: Abrir navegador 3 segundos despues de que el servidor levante
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8502/"

python server_orbit.py

pause
