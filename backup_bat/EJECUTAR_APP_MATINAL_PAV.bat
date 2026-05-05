@echo off
cd /d "C:\Orbit\MATINAL_PENAFLOR"
title ORBIT Matinal PAV - Penaflor

echo.
echo ============================================================
echo   ORBIT MATINAL PAV - PENAFLOR
echo   Orbit (c) 2026 - Propiedad de Torres Matias
echo ============================================================
echo.

REM Detectar IP local para compartir con vendedores
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :gotip
)
:gotip
set IP=%IP: =%

echo  [INFO] Tu IP local: %IP%
echo.
echo  ACCESO PARA VENDEDORES (misma red WiFi):
echo  ------------------------------------------
echo  URL: http://%IP%:8502
echo.
echo  ACCESO LOCAL (esta PC):
echo  ------------------------------------------
echo  URL: http://localhost:8502
echo.
echo  CONTRASENAS:
echo    Vendedores : pav2026
echo    Gerencia   : gerencia2026
echo.
echo  [INFO] Compartí la URL con los vendedores por WhatsApp.
echo  [INFO] Ellos la abren desde el navegador del telefono.
echo  [INFO] Presiona Ctrl+C para cerrar la app.
echo.
echo ============================================================
echo.

streamlit run app_matinal_penaflor.py ^
  --server.port 8502 ^
  --server.address 0.0.0.0 ^
  --server.headless true ^
  --theme.base dark ^
  --theme.primaryColor "#6EC531" ^
  --theme.backgroundColor "#0A0A0A" ^
  --theme.secondaryBackgroundColor "#111111" ^
  --theme.textColor "#E8E8E8" ^
  --browser.gatherUsageStats false

pause
