@echo off
title ORBIT · Matinal Peñaflor
cd /d "C:\Orbit\MATINAL_PENAFLOR"
echo.
echo  ██████╗ ██████╗ ██████╗ ██╗████████╗
echo  ██╔══██╗██╔══██╗██╔══██╗██║╚══██╔══╝
echo  ██║  ██║██████╔╝██████╔╝██║   ██║
echo  ██║  ██║██╔══██╗██╔══██╗██║   ██║
echo  ██████╔╝██║  ██║██████╔╝██║   ██║
echo  ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═╝   ╚═╝
echo.

:: Cerrar instancias anteriores del servidor en el puerto 8502
echo  Cerrando instancias anteriores en puerto 8502...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8502 " ^| findstr "LISTENING"') do (
    if not "%%p"=="" (
        taskkill /PID %%p /F >nul 2>&1
    )
)
timeout /t 1 /nobreak >nul

echo  Matinal Peñaflor · Iniciando servidor...
echo  Portal: http://localhost:8502
echo.
start "" http://localhost:8502
py -3.12 server_orbit.py
pause
