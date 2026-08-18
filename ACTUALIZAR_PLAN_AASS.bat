@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

title ORBIT - Actualizar Plan AASS sin cierre

:: ============================================================
:: ACTUALIZAR_PLAN_AASS.bat
:: Regenera exclusivamente:
::   - 04_DATASETS_ORBIT\mod_planes_as.csv
::   - 04_DATASETS_ORBIT\mod_sincargos_envios.csv
:: No ejecuta cierre diario, no abre el portal y no hace Git.
:: ============================================================

set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"
set "INPUT_DIR=%BASE%\01_INPUTS\Planes AASS"
set "VENTAS=%BASE%\01_INPUTS\ventas.csv"
set "CLIENTES=%BASE%\01_INPUTS\clientes.xlsx"
set "GENERADOR=%BASE%\generar_datasets_acum.py"
set "OUT_PLANES=%BASE%\04_DATASETS_ORBIT\mod_planes_as.csv"
set "OUT_ENVIOS=%BASE%\04_DATASETS_ORBIT\mod_sincargos_envios.csv"
set "NO_PAUSE=0"
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"

for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%T"
for /f "delims=" %%M in ('powershell -NoProfile -Command "(Get-Date).Month"') do set "MES_NUM=%%M"

if "!MES_NUM!"=="1"  set "MES=enero"
if "!MES_NUM!"=="2"  set "MES=febrero"
if "!MES_NUM!"=="3"  set "MES=marzo"
if "!MES_NUM!"=="4"  set "MES=abril"
if "!MES_NUM!"=="5"  set "MES=mayo"
if "!MES_NUM!"=="6"  set "MES=junio"
if "!MES_NUM!"=="7"  set "MES=julio"
if "!MES_NUM!"=="8"  set "MES=agosto"
if "!MES_NUM!"=="9"  set "MES=septiembre"
if "!MES_NUM!"=="10" set "MES=octubre"
if "!MES_NUM!"=="11" set "MES=noviembre"
if "!MES_NUM!"=="12" set "MES=diciembre"

set "LOG_DIR=%BASE%\99_LOGS_ORBIT"
set "LOG=%LOG_DIR%\actualizar_plan_aass_!TS!.log"
set "BACKUP_DIR=%BASE%\99_BACKUPS_ORBIT\!TS!_planes_aass"
if not exist "!LOG_DIR!" mkdir "!LOG_DIR!"

> "!LOG!" echo ============================================================
>>"!LOG!" echo ORBIT - ACTUALIZACION PARCIAL PLAN AASS
>>"!LOG!" echo Inicio: !TS!
>>"!LOG!" echo Mes: !MES!
>>"!LOG!" echo ============================================================

echo ============================================================
echo ORBIT - ACTUALIZAR PLAN AASS SIN CIERRE
echo ============================================================
echo.
echo Mes esperado: !MES!
echo Log: !LOG!
echo.

:: 1. Resolver Python real y validar dependencias.
set "PYTHON_EXE="
for /f "delims=" %%P in ('powershell -NoProfile -Command "$c=Get-Command python -ErrorAction SilentlyContinue; if($c){$c.Source}"') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE (
    echo ERROR: No se encontro Python.>>"!LOG!"
    echo ERROR: No se encontro Python instalado.
    goto :error_sin_backup
)

"!PYTHON_EXE!" -c "import pandas, openpyxl" >>"!LOG!" 2>&1
if errorlevel 1 (
    echo ERROR: Python no tiene pandas/openpyxl.>>"!LOG!"
    echo ERROR: Faltan pandas u openpyxl en Python.
    goto :error_sin_backup
)

:: 2. Validar que existan solamente las fuentes requeridas por Plan AASS.
if not exist "!VENTAS!" (
    echo ERROR: Falta 01_INPUTS\ventas.csv.>>"!LOG!"
    echo ERROR: Falta 01_INPUTS\ventas.csv.
    goto :error_sin_backup
)
if not exist "!CLIENTES!" (
    echo ERROR: Falta 01_INPUTS\clientes.xlsx.>>"!LOG!"
    echo ERROR: Falta 01_INPUTS\clientes.xlsx.
    goto :error_sin_backup
)
if not exist "!GENERADOR!" (
    echo ERROR: Falta generar_datasets_acum.py.>>"!LOG!"
    echo ERROR: Falta generar_datasets_acum.py.
    goto :error_sin_backup
)

set "PLAN_FILE="
for /f "delims=" %%F in ('dir /b /a-d /o-d "!INPUT_DIR!\sincargos*!MES!*.xlsx" 2^>nul') do if not defined PLAN_FILE set "PLAN_FILE=!INPUT_DIR!\%%F"
if not defined PLAN_FILE (
    echo ERROR: No existe sincargos*!MES!*.xlsx en 01_INPUTS\Planes AASS.>>"!LOG!"
    echo ERROR: No existe el Excel de Plan AASS del mes actual ^(!MES!^).
    echo Debe llamarse, por ejemplo: sincargos!MES!.xlsx
    goto :error_sin_backup
)

echo Fuente elegida: !PLAN_FILE!
echo Fuente elegida: !PLAN_FILE!>>"!LOG!"

"!PYTHON_EXE!" -c "import sys; from pathlib import Path; import generar_datasets_acum as g; p=Path(sys.argv[1]); a=g._cargar_sincargos_mes(p); assert a, 'El Excel no contiene asignaciones Plan AASS validas'; print('INPUT_OK clientes_con_asignacion=', len(a), 'cajas=', sum(x['sc_total_ganado'] for x in a.values()))" "!PLAN_FILE!" >>"!LOG!" 2>&1
if errorlevel 1 (
    echo ERROR: El Excel no paso la validacion estructural.
    echo Revisar el log: !LOG!
    goto :error_sin_backup
)

:: 3. Backup exclusivo de los dos outputs que este BAT puede sobrescribir.
mkdir "!BACKUP_DIR!" >nul 2>&1
set "HAD_PLANES=0"
set "HAD_ENVIOS=0"
if exist "!OUT_PLANES!" (
    copy /y "!OUT_PLANES!" "!BACKUP_DIR!\mod_planes_as.csv" >>"!LOG!" 2>&1
    if errorlevel 1 goto :error_backup
    set "HAD_PLANES=1"
)
if exist "!OUT_ENVIOS!" (
    copy /y "!OUT_ENVIOS!" "!BACKUP_DIR!\mod_sincargos_envios.csv" >>"!LOG!" 2>&1
    if errorlevel 1 goto :error_backup
    set "HAD_ENVIOS=1"
)
echo Backup: !BACKUP_DIR!
echo Backup completo.>>"!LOG!"

:: 4. Regeneracion parcial. No llama a REGENERAR_DATOS_ORBIT ni a CIERRE_DIA_ORBIT.
echo.
echo Generando exclusivamente los datasets de Plan AASS...
"!PYTHON_EXE!" "!GENERADOR!" --solo-planes-as >>"!LOG!" 2>&1
if errorlevel 1 (
    echo ERROR: Fallo generar_datasets_acum.py --solo-planes-as.>>"!LOG!"
    goto :error_restaurar
)

:: 5. Reconciliar fuente contra los dos CSV y controlar vendedores prohibidos.
"!PYTHON_EXE!" -c "import sys; from pathlib import Path; import pandas as pd; import generar_datasets_acum as g; src=Path(sys.argv[1]); p=Path(sys.argv[2]); e=Path(sys.argv[3]); assert p.exists() and p.stat().st_size, 'Falta mod_planes_as.csv'; assert e.exists() and e.stat().st_size, 'Falta mod_sincargos_envios.csv'; d=pd.read_csv(p, encoding='utf-8-sig'); assert len(d), 'mod_planes_as.csv vacio'; req={'cliente_id','vendedor_codigo','sc_total_ganado','pf_disponible','pt_disponible'}; assert req.issubset(d.columns), 'Columnas incompletas en mod_planes_as.csv'; ids=set(pd.to_numeric(d['cliente_id'], errors='coerce').dropna().astype(int)); vend=set(pd.to_numeric(d['vendedor_codigo'], errors='coerce').dropna().astype(int)); bad=vend.intersection({2,3,5,20}); assert not bad, 'Vendedores prohibidos: '+str(sorted(bad)); a=g._cargar_sincargos_mes(src); esperado=sum(int(a.get(cid,{}).get('sc_total_ganado',0)) for cid in ids); actual=int(pd.to_numeric(d['sc_total_ganado'], errors='coerce').fillna(0).sum()); assert actual==esperado, f'Sin cargo fuente={esperado} salida={actual}'; pf=g._cargar_planfrio_mes(src); assert int((pd.to_numeric(d['pf_disponible'], errors='coerce').fillna(0)>0).sum())==len(ids.intersection(pf)), 'Plan Frio no coincide'; pt,prod=g._cargar_puntera_mes(src); assert int(pd.to_numeric(d['pt_disponible'], errors='coerce').fillna(0).sum())==sum(int(pt.get(cid,0)) for cid in ids), 'Puntera no coincide'; env=pd.read_csv(e, encoding='utf-8-sig'); assert {'cliente_id','categoria','producto','fecha','cajas'}.issubset(env.columns), 'Columnas incompletas en mod_sincargos_envios.csv'; print(f'VALIDACION_OK clientes={len(d)} sin_cargo={actual} plan_frio={len(ids.intersection(pf))} puntera_cajas={sum(int(pt.get(cid,0)) for cid in ids)} producto_puntera={prod}')" "!PLAN_FILE!" "!OUT_PLANES!" "!OUT_ENVIOS!" >>"!LOG!" 2>&1
if errorlevel 1 (
    echo ERROR: La salida no coincide con la fuente.>>"!LOG!"
    goto :error_restaurar
)

echo.
echo ============================================================
echo ACTUALIZACION PLAN AASS COMPLETADA
echo ============================================================
powershell -NoProfile -Command "Get-Content -LiteralPath '!LOG!' | Select-String 'VALIDACION_OK' | Select-Object -Last 1"
echo.
echo No se ejecuto cierre de dia.
echo No se modificaron otros datasets.
echo No se hizo commit ni push.
echo Para actualizar Render, estos cambios deben publicarse en Git.
echo Log: !LOG!
echo.
if "!NO_PAUSE!"=="0" pause
exit /b 0

:error_backup
echo ERROR: No se pudo crear el backup. No se regenero nada.>>"!LOG!"
echo ERROR: No se pudo crear el backup. No se regenero nada.
goto :fin_error

:error_restaurar
echo Restaurando los dos datasets de Plan AASS...>>"!LOG!"
if "!HAD_PLANES!"=="1" copy /y "!BACKUP_DIR!\mod_planes_as.csv" "!OUT_PLANES!" >>"!LOG!" 2>&1
if "!HAD_PLANES!"=="0" if exist "!OUT_PLANES!" del /q "!OUT_PLANES!"
if "!HAD_ENVIOS!"=="1" copy /y "!BACKUP_DIR!\mod_sincargos_envios.csv" "!OUT_ENVIOS!" >>"!LOG!" 2>&1
if "!HAD_ENVIOS!"=="0" if exist "!OUT_ENVIOS!" del /q "!OUT_ENVIOS!"
echo ERROR: Se restauraron los datasets anteriores.
echo Revisar el log: !LOG!
goto :fin_error

:error_sin_backup
echo ABORTADO antes del backup.>>"!LOG!"

:fin_error
echo.
if "!NO_PAUSE!"=="0" pause
exit /b 1
