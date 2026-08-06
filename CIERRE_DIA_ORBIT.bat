@echo off
setlocal enabledelayedexpansion

title ORBIT - Cierre del Dia

echo ============================================================
echo ORBIT MATINAL PENAFLOR - CIERRE DEL DIA
echo ============================================================
echo.

set "ROOT=C:\Orbit\MATINAL_PENAFLOR"
set "VENTAS=%ROOT%\01_INPUTS\ventas.csv"
set "PORTAL=https://orbit-matinal-penaflor.onrender.com"

cd /d "%ROOT%"

REM ── Guard de rama: el cierre DEBE correr sobre master (Render deploya master).
REM    Si estas parado en otra rama (p.ej. trabajando orbit-home), el commit del
REM    cierre cae en esa rama y "git push origin master" es un no-op silencioso:
REM    Render NO avanza el dia. Este guard lo frena antes de tocar nada.
set "RAMA_ACTUAL="
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set "RAMA_ACTUAL=%%b"
if /I not "%RAMA_ACTUAL%"=="master" (
    echo ============================================================
    echo ERROR: Estas en la rama "%RAMA_ACTUAL%", no en master.
    echo.
    echo El cierre publica a master y Render deploya master. Corriendo
    echo desde otra rama, el dato NO llega a produccion aunque el push
    echo diga OK. Cambia a master antes de cerrar el dia:
    echo.
    echo     git checkout master
    echo ============================================================
    pause
    exit /b 1
)

echo Verificando estado Git antes de iniciar...
echo.

REM ── Bloquear SOLO cambios funcionales (fuera de rutas operativas permitidas).
REM    La clasificacion POR RUTA vive en check_git_cierre.py (arbol 01_INPUTS/,
REM    02_HISTORY/, 04_DATASETS_ORBIT/, 06_APP_DATA/, 07_CIERRES_MENSUALES/ = operativo).
REM    Cualquier .py, .bat, portal.html, config u otro archivo fuera de eso FRENA el cierre.
python "%ROOT%\check_git_cierre.py"
if errorlevel 1 (
    echo ============================================================
    echo Commitea o resolve esos cambios ANTES de cerrar el dia.
    echo ============================================================
    pause
    exit /b 1
)

REM ── Pull SOLO si el repo esta 100%% limpio. Si ya hay inputs operativos
REM    cargados (ventas.csv, etc.), NO se intenta pull con working tree sucio.
set "REPO_DIRTY="
for /f "delims=" %%i in ('git status --porcelain') do set "REPO_DIRTY=1"
if defined REPO_DIRTY goto sin_pull

echo Repositorio limpio. Sincronizando con el remoto (git pull --rebase)...
git pull --rebase origin master
if errorlevel 1 (
    git rebase --abort >nul 2>&1
    echo ============================================================
    echo ERROR: No se pudo sincronizar con el remoto.
    echo No se regenero ningun dato y Render NO fue actualizado.
    echo Resolver el estado Git/red y volver a ejecutar el cierre.
    echo ============================================================
    pause
    exit /b 1
)
echo OK: repositorio sincronizado.
goto pull_ok

:sin_pull
echo Hay inputs operativos ya cargados. No se puede hacer pull con cambios locales.
echo Si necesitas sincronizar con GitHub, hacelo antes de cargar los inputs.

:pull_ok
echo.

echo Validando archivo ventas.csv...
echo.

if not exist "%VENTAS%" (
    echo ERROR: No existe el archivo:
    echo %VENTAS%
    echo.
    echo Pegue primero el ventas.csv nuevo en 01_INPUTS.
    pause
    exit /b 1
)

python -c "import pandas as pd; p=r'%VENTAS%'; df=pd.read_csv(p, sep=';', encoding='latin1'); print('Filas detectadas:', len(df)); assert 'FechaComprobante' in df.columns, 'Falta columna FechaComprobante'; f=pd.to_datetime(df['FechaComprobante'], dayfirst=True, errors='coerce'); print('Fecha mas reciente:', f.max().strftime('%%Y-%%m-%%d') if f.notna().any() else 'SIN_FECHA')"

if errorlevel 1 (
    echo.
    echo ERROR: ventas.csv no pudo validarse.
    echo Revisar separador, encoding o columna FechaComprobante.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo PASO 1/3: Regenerando datasets (motor legacy + CSVs)...
echo Esto actualiza acumulado, sellout, CCC, 11T y todos los KPIs.
echo Puede tardar 1-2 minutos.
echo ============================================================
echo.

call "%ROOT%\REGENERAR_DATOS_ORBIT.bat"

echo.
if errorlevel 1 (
    echo ============================================================
    echo ERROR: La regeneracion de datasets FALLO.
    echo Los datos NO se publicaron. NO se hace commit ni push.
    echo Render se queda con los datos anteriores ^(no avanza el dia^).
    echo Revisar el ultimo log en 99_LOGS_ORBIT y reintentar el cierre.
    echo ============================================================
    echo.
    pause
    exit /b 1
)
echo OK: Datasets regenerados correctamente.
echo.

echo ============================================================
echo PASO 2/3: Sincronizando planes desde Render...
echo (Los vendedores los enviaron por sus telefonos al servidor en la nube)
echo ============================================================
echo.
python "%ROOT%\sync_planes_render.py"
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: No se pudieron sincronizar planes desde Render.
    echo Render NO fue actualizado.
    echo ============================================================
    pause
    exit /b 1
)
echo.

echo ============================================================
echo PASO 3/3: Publicando datos en GitHub para actualizar Render...
echo ============================================================
echo.

for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set FECHA_COMMIT=%%i

echo Preparando archivos para commit...
git add "01_INPUTS/resultado.xlsx"
git add "01_INPUTS/ventas.csv"
git add "01_INPUTS/ventas_acumulada.csv"
git add "01_INPUTS/ventas_mes.csv"
git add "01_INPUTS/clientes.xlsx"
git add "01_INPUTS/ventas-clubfaro.csv"
git add "01_INPUTS/incentivo_club_faro*.xlsx"
git add "01_INPUTS/INNOVACIONES/Innovaciones.xlsx"
git add "01_INPUTS/Planes AASS"
REM Padron del Plan Cobertura: lo actualizan a mano a medida que se dan de alta
REM clientes nuevos, asi que viaja con el cierre diario como el resto de los inputs.
git add "01_INPUTS/Plan cobertura"
REM Plan Frizze: el negocio suma clientes al plan editando el xlsx a mano.
REM Sin esta linea el cierre no lo publica y Render sigue mostrando la lista
REM vieja aunque el archivo local este actualizado (mismo patron que ERR-014).
git add "01_INPUTS/PLAN FRIZZE/planfrizze.xlsx"
REM Stock de los dos depositos: los lee la tarjeta Dias de Stock (pantalla Semanal)
REM y Stock sin Venta. Sin estas dos lineas el cierre no los publica y Render
REM sigue mostrando la foto del ultimo commit manual (mismo patron que ERR-014).
REM MPA.xlsx NO va: es una lista fija, no cambia con el cierre diario.
git add "01_INPUTS/Stock/stock.xlsx"
git add "01_INPUTS/Stock/stock_VSB_Cuyo.xlsx"
git add "02_HISTORY/historial_ventas_cliente.csv"
git add "02_HISTORY/acumulado_resultado_historico.csv"
git add "04_DATASETS_ORBIT/clientes_dia.csv"
git add "04_DATASETS_ORBIT/hist_cliente_mes.csv"
git add "04_DATASETS_ORBIT/hist_cliente_producto.csv"
git add "04_DATASETS_ORBIT/hist_cliente_resumen.csv"
git add "04_DATASETS_ORBIT/mod_11_titulares.csv"
git add "04_DATASETS_ORBIT/mod_11t_acum.csv"
REM Salidas auditables del motor 11T (motor_11t): detalle cliente x titular,
REM excepciones de medicion y clientes SIN_CARTERA. El portal no las lee, pero
REM /api/gerencia/once_titulares publica la ruta de mod_11t_excepciones.csv como
REM puntero: sin estas lineas apunta a un archivo que no existe en Render.
git add "04_DATASETS_ORBIT/mod_11t_detalle.csv"
git add "04_DATASETS_ORBIT/mod_11t_excepciones.csv"
git add "04_DATASETS_ORBIT/mod_11t_sin_cartera.csv"
git add "04_DATASETS_ORBIT/mod_acciones_analisis.csv"
git add "04_DATASETS_ORBIT/mod_acciones_ranking.csv"
git add "04_DATASETS_ORBIT/mod_alertas_descuentos.csv"
git add "04_DATASETS_ORBIT/mod_ccc_segmento.csv"
git add "04_DATASETS_ORBIT/mod_cobertura_acum.csv"
git add "04_DATASETS_ORBIT/mod_cobertura_acum_detalle.csv"
git add "04_DATASETS_ORBIT/mod_gastos_accion.csv"
git add "04_DATASETS_ORBIT/mod_innovaciones_segmento.csv"
git add "04_DATASETS_ORBIT/mod_planes_as.csv"
git add "04_DATASETS_ORBIT/mod_sellout_categoria.csv"
git add "04_DATASETS_ORBIT/mod_sincargos_envios.csv"
git add "04_DATASETS_ORBIT/mod_vda_clientes_detalle.csv"
git add "04_DATASETS_ORBIT/mod_vda_productos.csv"
git add "04_DATASETS_ORBIT/mod_vda_productos_revision_necesaria.csv"
git add "04_DATASETS_ORBIT/mod_vda_ranking_vendedor.csv"
git add "04_DATASETS_ORBIT/mod_vda_resumen_mensual.csv"
git add "04_DATASETS_ORBIT/mod_volumen_vendedor.csv"
git add "01_INPUTS/ACCIONES COMERCIALES/*/acciones_comerciales_*.csv"

REM ── Abortar si quedan cambios FUERA del allowlist operativo (desarrollo colado).
REM    Los archivos operativos ya quedaron staged por los git add de arriba.
python "%ROOT%\check_git_cierre.py"
if errorlevel 1 (
    echo.
    echo No se hace commit ni push para no mezclar desarrollo con cierre.
    goto fin_error
)

git diff --cached --quiet
if not errorlevel 1 (
    echo No hay cambios nuevos para publicar.
    echo No se ejecuto push; Render NO fue actualizado por este cierre.
    goto fin_error
)

git commit -m "data: cierre dia %FECHA_COMMIT% — datasets + inputs actualizados"
if errorlevel 1 (
    echo.
    echo ERROR: Fallo el commit. Verificar estado de git. NO se publico.
    echo Render NO fue actualizado.
    goto fin_error
)

git push origin master
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Fallo el PUSH a GitHub. Los datos NO llegaron a Render.
    echo Revisar conexion a internet y volver a ejecutar el cierre.
    echo ============================================================
    goto fin_error
)

echo.
echo OK: Datos publicados en GitHub.
echo.

REM ── Esperar a que Render sirva el DEPLOY NUEVO antes de abrir el portal.
REM    Render hace deploy sin downtime: /api/healthz responde 200 desde la instancia
REM    vieja hasta que la nueva pasa el healthcheck. Por eso no alcanza con "responde
REM    200": sondeamos hasta que healthz reporte el commit que acabamos de pushear
REM    (campo "commit" = RENDER_GIT_COMMIT). Timeout ~6 min; si vence, se abre igual.
for /f "delims=" %%i in ('git rev-parse HEAD') do set "COMMIT_SHA=%%i"
echo Esperando a que Render despliegue el commit %COMMIT_SHA:~0,7% (hasta 6 min)...
powershell -NoProfile -Command "$sha='%COMMIT_SHA%'; $url='%PORTAL%/api/healthz'; $ok=$false; for($i=1;$i -le 36;$i++){ try{ $r=Invoke-RestMethod -Uri $url -TimeoutSec 10; if($r.commit -eq $sha){ $ok=$true; break } }catch{}; Write-Host ('  esperando deploy... '+$i+'/36'); Start-Sleep -Seconds 10 }; if($ok){ Write-Host 'OK: Render esta sirviendo el deploy nuevo.'; exit 0 } else { Write-Host 'AVISO: se agoto la espera del deploy.'; exit 1 }"
if errorlevel 1 (
    echo.
    echo Render tardo mas de lo esperado ^(o corre una version sin el commit en healthz^).
    echo Se abre el portal igual; si no ves datos, recarga en unos minutos.
) else (
    echo Deploy confirmado en Render.
)
start "" "%PORTAL%"
goto fin_ok

:fin_error

echo.
echo ============================================================
echo CIERRE NO PUBLICADO
echo Render NO fue actualizado por este cierre.
echo Portal Render: https://orbit-matinal-penaflor.onrender.com
echo ============================================================
echo.

pause
exit /b 1

:fin_ok

echo.
echo ============================================================
echo LISTO
echo Portal Render: https://orbit-matinal-penaflor.onrender.com
echo (actualiza en 2-3 min luego del push)
echo ============================================================
echo.

pause
exit /b 0
