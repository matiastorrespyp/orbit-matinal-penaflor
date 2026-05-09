@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

:: ============================================================
:: REGENERAR_DATOS_ORBIT.bat
:: Regenera datos derivados del portal ORBIT Matinal Peñaflor.
:: No abre el portal. No levanta server_orbit.py.
:: No toca 01_INPUTS. No commitea nada.
:: ============================================================

set BASE=C:\Orbit\MATINAL_PENAFLOR

:: Timestamp via PowerShell — evita problemas de locale en Windows español
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i

set BACKUP_DIR=%BASE%\99_BACKUPS_ORBIT\%TS%
set LOG_DIR=%BASE%\99_LOGS_ORBIT
set LOG=%LOG_DIR%\regenerar_datos_%TS%.log

:: ============================================================
:: 1. CREAR DIRECTORIO DE LOG
:: ============================================================
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo ============================================================ >> "%LOG%"
echo ORBIT REGENERAR DATOS                                        >> "%LOG%"
echo Inicio: %TS%                                                 >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo.
echo ===== ORBIT REGENERAR DATOS =====
echo Inicio: %TS%
echo Log:    %LOG%
echo.

:: ============================================================
:: 2. VALIDAR INPUTS — abortar si falta alguno
:: ============================================================
echo [1/8] Validando inputs... >> "%LOG%"
echo [1/8] Validando inputs...

set ERROR_VALIDACION=0

if not exist "%BASE%\01_INPUTS\ventas.csv" (
    echo ERROR: No existe 01_INPUTS\ventas.csv >> "%LOG%"
    echo ERROR: No existe 01_INPUTS\ventas.csv
    set ERROR_VALIDACION=1
)
if not exist "%BASE%\01_INPUTS\resultado.xlsx" (
    echo ERROR: No existe 01_INPUTS\resultado.xlsx >> "%LOG%"
    echo ERROR: No existe 01_INPUTS\resultado.xlsx
    set ERROR_VALIDACION=1
)
if not exist "%BASE%\LEGACY\orbit_matinal_v42.py" (
    echo ERROR: No existe LEGACY\orbit_matinal_v42.py >> "%LOG%"
    echo ERROR: No existe LEGACY\orbit_matinal_v42.py
    set ERROR_VALIDACION=1
)
if not exist "%BASE%\test_datasets_orbit.py" (
    echo ERROR: No existe test_datasets_orbit.py >> "%LOG%"
    echo ERROR: No existe test_datasets_orbit.py
    set ERROR_VALIDACION=1
)

if %ERROR_VALIDACION% neq 0 (
    echo ABORTADO: faltan inputs obligatorios. >> "%LOG%"
    echo ABORTADO. Ver log: %LOG%
    exit /b 1
)
echo OK: todos los inputs presentes >> "%LOG%"
echo OK: todos los inputs presentes

:: ============================================================
:: 3. LOGEAR ESTADO DE INPUTS
:: ============================================================
echo [2/8] Estado de inputs: >> "%LOG%"
for %%f in ("%BASE%\01_INPUTS\ventas.csv" "%BASE%\01_INPUTS\resultado.xlsx") do (
    powershell -NoProfile -Command "$f=Get-Item '%%~f'; '  '+$f.Name+' | '+$f.Length+' bytes | '+$f.LastWriteTime" >> "%LOG%"
)

:: ============================================================
:: 3. VERIFICAR EXCEL NO BLOQUEADO
:: Chequeo seguro via PowerShell — no toca el archivo.
:: Debe hacerse ANTES del backup y ANTES de ejecutar cualquier script.
:: ============================================================
echo [3/8] Verificando que el Excel no este bloqueado... >> "%LOG%"
echo [3/8] Verificando Excel no bloqueado...

if exist "%BASE%\03_OUTPUTS\MATINAL_PENA_V42.xlsx" (
    powershell -NoProfile -Command "try { $fs=[System.IO.File]::Open('%BASE%\03_OUTPUTS\MATINAL_PENA_V42.xlsx','Open','ReadWrite','None'); $fs.Close(); exit 0 } catch { exit 1 }"
    if errorlevel 1 (
        echo ERROR: MATINAL_PENA_V42.xlsx esta abierto o bloqueado. >> "%LOG%"
        echo ERROR: Cerrar el Excel e intentar de nuevo.            >> "%LOG%"
        echo ABORTADO por Excel bloqueado.                          >> "%LOG%"
        echo.
        echo ERROR: MATINAL_PENA_V42.xlsx esta abierto o bloqueado.
        echo        Cerrar el Excel e intentar de nuevo.
        exit /b 1
    )
    echo OK: Excel no esta bloqueado >> "%LOG%"
    echo OK: Excel no esta bloqueado
) else (
    echo OK: Excel no existe aun, no hay riesgo de bloqueo >> "%LOG%"
)

:: ============================================================
:: 4. BACKUP OBLIGATORIO — antes de cualquier ejecución
:: ============================================================
echo [4/8] Creando backup en: %BACKUP_DIR% >> "%LOG%"
echo [4/8] Creando backup...

mkdir "%BACKUP_DIR%\03_OUTPUTS"
mkdir "%BACKUP_DIR%\02_HISTORY"
mkdir "%BACKUP_DIR%\04_DATASETS_ORBIT"

if exist "%BASE%\03_OUTPUTS\MATINAL_PENA_V42.xlsx" (
    xcopy /y /q "%BASE%\03_OUTPUTS\MATINAL_PENA_V42.xlsx" "%BACKUP_DIR%\03_OUTPUTS\" >> "%LOG%" 2>&1
    echo OK: backup MATINAL_PENA_V42.xlsx >> "%LOG%"
) else (
    echo AVISO: MATINAL_PENA_V42.xlsx no existe aun, omitiendo backup >> "%LOG%"
)

if exist "%BASE%\02_HISTORY\historial_ventas_cliente.csv" (
    xcopy /y /q "%BASE%\02_HISTORY\historial_ventas_cliente.csv" "%BACKUP_DIR%\02_HISTORY\" >> "%LOG%" 2>&1
    echo OK: backup historial_ventas_cliente.csv >> "%LOG%"
) else (
    echo AVISO: historial_ventas_cliente.csv no existe aun, omitiendo backup >> "%LOG%"
)

:: Si no existen CSVs previos: registrar y seguir sin fallar
dir /b "%BASE%\04_DATASETS_ORBIT\*.csv" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    xcopy /y /q "%BASE%\04_DATASETS_ORBIT\*.csv" "%BACKUP_DIR%\04_DATASETS_ORBIT\" >> "%LOG%" 2>&1
    echo OK: backup 04_DATASETS_ORBIT\*.csv >> "%LOG%"
) else (
    echo AVISO: no existian CSVs previos en 04_DATASETS_ORBIT, omitiendo backup >> "%LOG%"
    echo AVISO: no existian CSVs previos en 04_DATASETS_ORBIT
)

echo Backup completo: %BACKUP_DIR% >> "%LOG%"
echo OK: backup completo

:: ============================================================
:: 5. PASO 1 — MOTOR LEGACY
::    Genera MATINAL_PENA_V42.xlsx + historial_ventas_cliente.csv
:: ============================================================
echo [5/8] Ejecutando motor legacy... >> "%LOG%"
echo [5/8] Ejecutando motor legacy (puede tardar 1-2 min)...

cd /d "%BASE%"
py test_legacy_run.py >> "%LOG%" 2>&1

if %ERRORLEVEL% neq 0 (
    echo ERROR: test_legacy_run.py fallo con codigo %ERRORLEVEL% >> "%LOG%"
    echo ABORTADO: no se ejecuta el paso siguiente.              >> "%LOG%"
    echo ERROR: Motor legacy fallo. Ver log: %LOG%
    exit /b 1
)
echo OK: motor legacy completado >> "%LOG%"
echo OK: motor legacy completado

:: ============================================================
:: 6. PASO 2 — EXPORTADOR CSV
::    Lee MATINAL_PENA_V42.xlsx, exporta 04_DATASETS_ORBIT\*.csv
:: ============================================================
echo [6/8] Exportando datasets CSV... >> "%LOG%"
echo [6/8] Exportando datasets CSV...

cd /d "%BASE%"
py test_datasets_orbit.py >> "%LOG%" 2>&1

if %ERRORLEVEL% neq 0 (
    echo ERROR: test_datasets_orbit.py fallo con codigo %ERRORLEVEL% >> "%LOG%"
    echo ERROR: Exportador CSV fallo. Ver log: %LOG%
    exit /b 1
)
echo OK: exportador CSV completado >> "%LOG%"
echo OK: exportador CSV completado

:: ============================================================
:: 7. VALIDAR OUTPUTS
::    Si falta cualquier output critico: ERROR + exit /b 1
:: ============================================================
echo [7/8] Validando outputs criticos... >> "%LOG%"
echo [7/8] Validando outputs criticos...

set OUTPUTS_OK=1

for %%f in (
    "03_OUTPUTS\MATINAL_PENA_V42.xlsx"
    "04_DATASETS_ORBIT\clientes_dia.csv"
    "04_DATASETS_ORBIT\mod_volumen_vendedor.csv"
    "04_DATASETS_ORBIT\mod_ccc_segmento.csv"
    "04_DATASETS_ORBIT\mod_11_titulares.csv"
    "04_DATASETS_ORBIT\mod_alertas_descuentos.csv"
    "04_DATASETS_ORBIT\mod_gastos_accion.csv"
) do (
    if exist "%BASE%\%%~f" (
        echo   OK: %%~f >> "%LOG%"
    ) else (
        echo   ERROR: FALTA %%~f >> "%LOG%"
        echo   ERROR: FALTA %%~f
        set OUTPUTS_OK=0
    )
)

if %OUTPUTS_OK% neq 1 (
    echo ERROR: faltan outputs criticos. Regeneracion FALLIDA. >> "%LOG%"
    echo ERROR: faltan outputs criticos. Ver log: %LOG%
    exit /b 1
)
echo OK: todos los outputs criticos presentes >> "%LOG%"
echo OK: todos los outputs criticos presentes

:: ============================================================
:: 8. LOGEAR ESTADO DE OUTPUTS
:: ============================================================
echo [8/8] Estado de outputs: >> "%LOG%"
for %%f in (
    "%BASE%\03_OUTPUTS\MATINAL_PENA_V42.xlsx"
    "%BASE%\04_DATASETS_ORBIT\clientes_dia.csv"
    "%BASE%\04_DATASETS_ORBIT\mod_volumen_vendedor.csv"
    "%BASE%\04_DATASETS_ORBIT\mod_ccc_segmento.csv"
    "%BASE%\04_DATASETS_ORBIT\mod_11_titulares.csv"
    "%BASE%\04_DATASETS_ORBIT\mod_alertas_descuentos.csv"
    "%BASE%\04_DATASETS_ORBIT\mod_gastos_accion.csv"
) do (
    if exist "%%~f" (
        powershell -NoProfile -Command "$f=Get-Item '%%~f'; '  OK: '+$f.Name+' | '+$f.Length+' bytes | '+$f.LastWriteTime" >> "%LOG%"
    )
)

:: ============================================================
:: CIERRE — solo llega aqui si todo OK
:: ============================================================
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS_FIN=%%i

echo ============================================================ >> "%LOG%"
echo Fin: %TS_FIN%                                                >> "%LOG%"
echo RESULTADO: OK — todos los outputs presentes                  >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo.
echo ===== REGENERACION COMPLETA — OK =====
echo Fin: %TS_FIN%
echo Log: %LOG%

endlocal
