@echo off
cd /d "%~dp0"

echo ==========================================
echo ORBIT PAV - PROCESO UNICO
echo ==========================================
echo.

echo [1/3] Ejecutando motor Orbit...
if exist "run_orbit.py" (
    python run_orbit.py
) else (
    if exist "src\orbit\control\run_orbit_diario.py" (
        python src\orbit\control\run_orbit_diario.py
    ) else (
        echo ERROR: No encontre run_orbit.py ni src\orbit\control\run_orbit_diario.py
        pause
        exit /b 1
    )
)

if errorlevel 1 (
    echo.
    echo ERROR: Fallo el motor Orbit.
    pause
    exit /b 1
)

echo.
echo [2/3] Generando JSON para la app...
python app_publish.py

if errorlevel 1 (
    echo.
    echo ERROR: Fallo app_publish.py
    pause
    exit /b 1
)

echo.
echo [3/3] Proceso finalizado.
echo JSON actualizados en 06_APP_DATA
echo.
pause