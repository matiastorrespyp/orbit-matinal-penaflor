# AUDITORÍA ORBIT MATINAL PEÑAFLOR
## Fecha: 2026-05-12 · Ejecutada por Claude Code · Basado en estado real del repositorio

---

## DIAGNÓSTICO EJECUTIVO

El sistema ORBIT Matinal Peñaflor está **operativo y procesando datos reales** para 7 vendedores (V3, V4, V6, V7, V8, V9, V10). El motor legacy (`orbit_matinal_v42.py`) ejecutó correctamente esta mañana (07:25) y generó outputs válidos para la matinal del martes 12/05/2026.

**Sin embargo, se detectan 4 problemas críticos y 8 problemas medios** que afectan la confiabilidad de los datos a mediano plazo.

El portal activo (`index.html` + `data.js`) consume datos reales desde Flask sin mock activo. Los JSONs estáticos generados por `app_publish.py` están obsoletos (fecha 2026-05-05) y no son consumidos por el portal activo, pero existen en disco y representan un riesgo si alguien los referencia.

---

## 1. MAPA DE CARPETAS

```
C:\Orbit\MATINAL_PENAFLOR\
│
├── 00_DROPZONE_DIARIA\          ← datos del 2026-04-16, desactualizados (NO usar)
├── 00_PROMPTS_ORBIT\            ← prompts operativos para Claude Code (OK)
│
├── 01_INPUTS\                   ← FUENTES PRIMARIAS
│   ├── ventas.csv               ← REAL, 2026-05-11 17:34, 515 KB, sep ';'
│   ├── resultado.xlsx           ← REAL, 2026-05-11 17:33, 14 KB
│   ├── clientes.xlsx            ← REAL, 2026-05-06 16:40, 2001 clientes
│   ├── _NO_USAR_ventas_diarias.csv    ← DEPRECATED (mismo formato, datos abril)
│   └── _NO_USAR_avance_objetivos.xlsx ← DEPRECATED (mismo propósito que resultado.xlsx)
│
├── 02_HISTORY\
│   ├── historial_ventas.csv          ← histórico viejo (2026-04-11, 08:42)
│   └── historial_ventas_cliente.csv  ← ACTIVO, 5652 filas, 2026-05-12 07:21
│
├── 03_OUTPUTS\
│   └── MATINAL_PENA_V42.xlsx    ← output principal del motor, 2026-05-12 07:25
│
├── 04_DATASETS_ORBIT\           ← CSVs exportados del Excel, regenerados hoy 07:25
│   ├── clientes_dia.csv         ← 346 filas, 32 columnas
│   ├── mod_volumen_vendedor.csv ← 7 filas (V3-V10), 25 columnas
│   ├── mod_ccc_segmento.csv     ← 6 filas (solo V3/V8/V10), 12 columnas
│   ├── mod_11_titulares.csv     ← 3798 filas, 17 columnas
│   ├── mod_alertas_descuentos.csv ← 31 filas, 20 columnas
│   ├── mod_gastos_accion.csv    ← 9 filas, 17 columnas
│   ├── resumen_alertas_vend.csv ← 3 filas
│   ├── mod_inversion_desc.csv   ← 32 filas
│   ├── mod_clientes_11t_10.csv  ← 4 filas
│   ├── mod_eficiencia_desc.csv  ← 65 filas
│   ├── mod_reintegros_ctrl.csv  ← 48 filas
│   ├── hist_cliente_mes.csv     ← 2026-05-05 (NO regenerado hoy)
│   ├── hist_cliente_producto.csv← 2026-05-05 (NO regenerado hoy)
│   ├── hist_cliente_resumen.csv ← 2026-05-05 (NO regenerado hoy)
│   ├── datasets_inventory.csv   ← inventario de columnas, regenerado hoy
│   └── log_motor.csv            ← log del último run, 26 filas
│
├── 05_INTELLIGENCE_ORBIT\       ← outputs del motor src/orbit/ (VIEJO, 2026-05-05)
│   ├── alertas_reales.csv
│   ├── alertas_reales_gerencia.json
│   ├── alertas_reales_resumen_vendedor.csv
│   ├── orbit_alertas_priorizadas.csv
│   ├── orbit_foco_vendedor.csv
│   ├── perf_resumen_vendedor.csv  ← 2026-04-19 (muy viejo)
│   └── perf_segmentos.csv         ← 2026-04-19
│
├── 06_APP_DATA\                 ← JSONs estáticos generados por app_publish.py
│   ├── orbit_portal_data.json   ← OBSOLETO (2026-05-05, cubiertos=0, corridos=3)
│   ├── dashboard_vendedor.json  ← OBSOLETO (2026-05-05)
│   ├── clientes_hoy.json        ← OBSOLETO (2026-05-05, 255 filas vs 346 reales)
│   ├── alertas_app.json         ← OBSOLETO (2026-05-05)
│   ├── charts_app.json          ← OBSOLETO (2026-05-05)
│   ├── cliente_detalle.json     ← OBSOLETO (2026-05-05)
│   ├── planificacion.json       ← OBSOLETO (2026-05-02)
│   ├── reglas_acciones_mayo_2026_orbit.json ← VIGENTE (config)
│   └── truth_audit.json         ← OBSOLETO (2026-05-05)
│
├── 07_PAV_OUTPUT\               ← HTMLs estáticos por vendedor (2026-05-05)
│   ├── vendedores\              ← V3 a V10.html
│   └── gerencia\PAV_GERENCIA.html
│
├── 08_LOGS\
│   ├── diagnostico_app_orbit.txt
│   ├── orbit_qa_resumen_latest.json  ← 2026-05-05
│   └── orbit_qa_resumen_latest.txt   ← 2026-05-05
│
├── 09_CONFIG\                   ← CONFIGURACIÓN ACTIVA
│   ├── vendedores_activos.csv   ← 7 vendedores, activo=1
│   ├── feriados.csv             ← 2 feriados mayo 2026
│   ├── clientes_excluidos.csv   ← 10 clientes excluidos
│   ├── acciones_comerciales.csv ← 8 filas, config alertas
│   ├── reglas_acciones_mayo_2026_orbit.csv ← 31 reglas Mayo 2026
│   ├── reglas_alertas.csv       ← 2026-04-19
│   └── acciones_mayo_2026_formato_gastos_orbit.xlsx
│
├── LEGACY\
│   └── orbit_matinal_v42.py     ← MOTOR ACTIVO, actualizado 2026-05-11 22:40
│
├── PAV MATINAL PE_A FLOR\       ← FRONTEND ACTIVO
│   ├── index.html               ← portal activo (2026-05-05 19:09)
│   ├── portal.html              ← ⚠ portal alternativo (2026-05-11 22:41) — ¿cuál se usa?
│   ├── data.js                  ← proveedor de datos real (sin mock)
│   ├── data.js.mock.bak         ← backup (confusamente nombrado)
│   ├── data_provider.js.bak     ← backup viejo
│   ├── app.jsx, charts.jsx, icons.jsx, fmtMoney.js
│   └── screens\                 ← dashboard.jsx, avance.jsx, etc.
│
├── src\orbit\                   ← módulo Python legacy (2026-04-09 a 2026-04-21)
│   ├── config\, control\, copilot\, datasets\, engine\
│   ├── history\, ingest\, intelligence\, kernel\
│   ├── master\, performance\, presentation\, proactive\, qa\, render\
│   └── [NO integrado al pipeline actual REGENERAR_DATOS_ORBIT.bat]
│
├── server_orbit.py              ← FLASK API ACTIVA (2026-05-12 07:57)
├── REGENERAR_DATOS_ORBIT.bat    ← pipeline de regeneración (2026-05-11)
├── ABRIR_CLAUDE_ORBIT.bat       ← launcher del portal
├── LEGACY\orbit_matinal_v42.py  ← motor real
├── app_publish.py               ← generador de JSONs estáticos (OBSOLETO en uso)
├── app_matinal_penaflor.py      ← aplicación anterior (status desconocido)
├── run_orbit.py                 ← runner anterior (2026-04-19)
│
├── 3, float, None, str, pd.DataFrame, Dict[str] ← ⚠ archivos basura raíz (2026-04-10)
│
├── 99_BACKUPS_ORBIT\            ← backups automáticos por fecha
└── 99_LOGS_ORBIT\               ← logs de REGENERAR_DATOS_ORBIT.bat
```

---

## 2. FUENTES DE DATOS

| Archivo | Función | Real/Mock | Última modificación | Columnas relevantes | ¿Consumido activamente? |
|---|---|---|---|---|---|
| `01_INPUTS/ventas.csv` | Ventas Gescom del día | **REAL** | 2026-05-11 17:34 | 57 cols, sep ';', utf-8-sig. Cliente;FechaComprobante;CantBase;ImporteNetoItem;CodVendedor;Articulo;Marca;valorDescuento;Descuento | Sí — motor legacy |
| `01_INPUTS/resultado.xlsx` | Objetivos + acumulado + avance por vendedor | **REAL** | 2026-05-11 17:33 | Hoja "Avance": VendedorCodigo, ValorObjetivo, Acumulado, Avance | Sí — motor + fallback server_orbit.py |
| `01_INPUTS/clientes.xlsx` | Maestro de clientes | **REAL** | 2026-05-06 16:40 | Cliente, Razon_Social, Ramo, DiasVisita, Localidad, codven | Sí — motor legacy |
| `01_INPUTS/producto activos.xlsx` | Maestro de productos activos | **NO EXISTE** | — | — | ⚠ Motor carga 0 productos |
| `01_INPUTS/_NO_USAR_ventas_diarias.csv` | Copia de ventas (misma estructura) | DEPRECATED | 2026-04-16 | igual que ventas.csv | No — marcado NO_USAR |
| `01_INPUTS/_NO_USAR_avance_objetivos.xlsx` | Copia de resultado | DEPRECATED | 2026-04-27 | similar a resultado.xlsx | No — marcado NO_USAR |
| `09_CONFIG/vendedores_activos.csv` | Lista activos V3-V10 | **REAL** | 2026-05-01 | codigo_vendedor, nombre_vendedor, activo, orden | Sí — server_orbit.py + motor |
| `09_CONFIG/feriados.csv` | Feriados mayo 2026 | **REAL** | 2026-05-05 | fecha, nombre (2 feriados: 01/05, 25/05) | Sí — server_orbit.py, motor |
| `09_CONFIG/clientes_excluidos.csv` | 10 clientes excluidos (empleados, depósito) | **REAL** | 2026-05-07 | cliente_id, razon_social, motivo_exclusion | Sí — motor legacy |
| `09_CONFIG/reglas_acciones_mayo_2026_orbit.csv` | 31 reglas comerciales mayo 2026 | **REAL** | 2026-05-06 | accion_id, canal, descuento_pct, cantidad_min/max | Sí — motor legacy |
| `04_DATASETS_ORBIT/mod_volumen_vendedor.csv` | KPIs por vendedor (objetivo, acumulado, tendencia) | **REAL** | 2026-05-12 07:25 | 25 cols, 7 filas | Sí — server_orbit.py /api/dashboard |
| `04_DATASETS_ORBIT/clientes_dia.csv` | Clientes del día con métricas | **REAL** | 2026-05-12 07:25 | 32 cols, 346 filas | Sí — server_orbit.py /api/clientes |
| `04_DATASETS_ORBIT/mod_ccc_segmento.csv` | CCC por segmento y vendedor | **REAL** | 2026-05-12 07:25 | 12 cols, 6 filas | Sí — server_orbit.py /api/diagnostico, /api/dashboard |
| `04_DATASETS_ORBIT/mod_11_titulares.csv` | 11 Titulares por cliente/marca | **REAL** | 2026-05-12 07:25 | 17 cols, 3798 filas | Sí — server_orbit.py /api/diagnostico, /api/dashboard |
| `04_DATASETS_ORBIT/mod_alertas_descuentos.csv` | Alertas de descuentos excesivos | **REAL** | 2026-05-12 07:25 | 20 cols, 31 filas | Sí — server_orbit.py /api/alertas |
| `04_DATASETS_ORBIT/mod_gastos_accion.csv` | Gastos reales vs teóricos por acción | **REAL** | 2026-05-12 07:25 | 17 cols, 9 filas | Sí — server_orbit.py /api/gastos_accion |
| `06_APP_DATA/orbit_portal_data.json` | Datos portal completos | **OBSOLETO** | 2026-05-05 19:13 | cubiertos=0, corridos=3, clientesCriticos=[] | server_orbit.py /api/orbit-data (endpoint inactivo) |
| `06_APP_DATA/clientes_hoy.json` | Clientes del día (estático) | **OBSOLETO** | 2026-05-05 | 255 filas (vs 346 reales) | No — reemplazado por CSV real |
| `06_APP_DATA/alertas_app.json` | Alertas estáticas | **OBSOLETO** | 2026-05-05 | — | No — reemplazado por CSV real |
| `06_APP_DATA/dashboard_vendedor.json` | Dashboard estático | **OBSOLETO** | 2026-05-05 | acumulado=0 para todos (bug conocido) | No — reemplazado por CSVs |
| `02_HISTORY/historial_ventas_cliente.csv` | Acumulado mensual de ventas | **REAL** | 2026-05-12 07:21 | 13 cols, 5652 filas, desde 2026-03-27 | Sí — motor (ventas_mes) |
| `PAV MATINAL PE_A FLOR/data.js` | Proveedor de datos del frontend | **REAL** | 2026-05-07 12:08 | Llama a 6 endpoints Flask, sin hardcode | Sí — index.html del portal |
| `PAV MATINAL PE_A FLOR/data.js.mock.bak` | Backup (mismo contenido que data.js activo) | Backup | 2026-05-05 | Igual al data.js actual | No |

---

## 3. ARCHIVOS DUPLICADOS

| Par | Fuente oficial | Archivo a ignorar/archivar | Riesgo |
|---|---|---|---|
| `ventas.csv` vs `_NO_USAR_ventas_diarias.csv` | `ventas.csv` | `_NO_USAR_ventas_diarias.csv` | Bajo — marcado NO_USAR, no es consumido |
| `resultado.xlsx` vs `_NO_USAR_avance_objetivos.xlsx` | `resultado.xlsx` | `_NO_USAR_avance_objetivos.xlsx` | Bajo — marcado NO_USAR |
| `index.html` vs `portal.html` | `index.html` (servido por Flask) | `portal.html` (sin consumidor conocido) | **MEDIO** — portal.html fue actualizado 2026-05-11 y puede contener cambios no reflejados |
| `04_DATASETS_ORBIT/*.csv` vs `06_APP_DATA/*.json` | `04_DATASETS_ORBIT/*.csv` | JSONs en `06_APP_DATA/` (obsoletos) | **MEDIO** — si alguien ejecuta `app_publish.py`, regenera JSONs obsoletos |
| `data.js` vs `data.js.mock.bak` | `data.js` | `data.js.mock.bak` | Bajo — el .bak contiene el mismo código real |
| `05_INTELLIGENCE_ORBIT/*.csv` vs `04_DATASETS_ORBIT/*.csv` | `04_DATASETS_ORBIT/*.csv` | `05_INTELLIGENCE_ORBIT/` (módulo src/orbit viejo) | **MEDIO** — datos de mayo 2026-05-05, no actualizados |
| `ABRIR_CLAUDE_ORBIT.bat` vs `backup_bat/EJECUTAR_APP_MATINAL_PAV.bat` | `ABRIR_CLAUDE_ORBIT.bat` | `backup_bat/*.bat` | Bajo — en carpeta backup |
| `LEGACY/orbit_matinal_v42.py` vs `src/orbit/**` | Motor: `LEGACY/orbit_matinal_v42.py` | `src/orbit/` (módulos viejos desintegrados) | **MEDIO** — posible confusión sobre cuál es el motor real |

---

## 4. FLUJO DE DATOS

```
GESCOM (ERP)
    │
    ▼
01_INPUTS/ventas.csv       (exportación manual diaria)
01_INPUTS/resultado.xlsx   (exportación manual diaria)
01_INPUTS/clientes.xlsx    (actualización cuando hay cambios)
    │
    ▼ [REGENERAR_DATOS_ORBIT.bat]
LEGACY/orbit_matinal_v42.py
    │   Lee: ventas.csv, clientes.xlsx, resultado.xlsx, feriados.csv
    │   Lee: reglas_acciones_mayo_2026_orbit.csv, clientes_excluidos.csv
    │   Lee: historial_ventas_cliente.csv (acumulado)
    │   ⚠ Lee: producto activos.xlsx → NO EXISTE → PRODUCTOS_CARGADOS = 0
    │
    ▼
03_OUTPUTS/MATINAL_PENA_V42.xlsx  (12 hojas)
02_HISTORY/historial_ventas_cliente.csv (acumulado actualizado)
    │
    ▼ [test_datasets_orbit.py → src/orbit/datasets/datasets_orbit.py]
04_DATASETS_ORBIT/*.csv   (11 CSVs + log + inventory)
    │
    ▼ [server_orbit.py — Flask puerto 8502]
/api/diagnostico        ← mod_volumen_vendedor + mod_ccc_segmento + mod_11_titulares + clientes_dia
/api/dashboard          ← mod_volumen_vendedor + mod_ccc_segmento + mod_11_titulares + vendedores_activos + resultado.xlsx (fallback)
/api/clientes           ← clientes_dia.csv
/api/alertas            ← mod_alertas_descuentos.csv
/api/gastos_accion      ← mod_gastos_accion.csv
/api/planificacion      ← orbit.db (SQLite)
/api/mensajes           ← orbit.db (SQLite)
/api/orbit-data         ← ⚠ orbit_portal_data.json (OBSOLETO 2026-05-05, no se consume actualmente)
    │
    ▼ [data.js — XHR síncronos al cargar]
PAV MATINAL PE_A FLOR/index.html
    └── window.ORBIT_DATA construido desde APIs Flask
        │
        ▼
app.jsx, screens/dashboard.jsx, screens/avance.jsx, etc.

RUPTURA DE TRAZABILIDAD DETECTADA:
──────────────────────────────────
1. producto activos.xlsx → NO EXISTE → 11T usa mapa hardcodeado (MAP_11T_FINE)
2. 06_APP_DATA/*.json → obsoletos, app_publish.py puede regenerarlos incorrectamente
3. 05_INTELLIGENCE_ORBIT/ → módulo src/orbit viejo, datos del 2026-05-05, no en pipeline
4. portal.html → sin consumidor identificado, puede tener cambios no sincronizados con index.html
5. historial_ventas.csv (raíz 02_HISTORY) → viejo, vs historial_ventas_cliente.csv (activo)
```

---

## 5. RIESGO DE MOCK DATA

| Archivo | Línea/Sección | Dato | Tipo de riesgo | Estado |
|---|---|---|---|---|
| `data.js` | línea 24 | `calendario = diag.calendario || { total: 24, corridos: 2, restantes: 22 }` | Fallback hardcoded si Flask no responde. total=24 puede ser incorrecto si cambia el mes | ⚠ BAJO |
| `data.js` | líneas 88-95 | `dailyEvolution`: interpolación lineal `(tAcum / corridos) * (i+1)` | NO es evolución real diaria, es proyección. No hay datos diarios individuales en ningún CSV | ⚠ MEDIO — el gráfico de evolución no es real |
| `data.js` | línea 79 | `ccc_mes: 0` | Honesto pero incompleto — no existe fuente de CCC acumulado del mes | INFO |
| `06_APP_DATA/orbit_portal_data.json` | segmentos | `cubiertos: 0` en todos los segmentos | Datos del 2026-05-05 antes de los fixes. Si se consume vía /api/orbit-data → datos incorrectos | ⚠ MEDIO |
| `06_APP_DATA/clientes_hoy.json` | todo | 255 filas vs 346 reales | Obsoleto 2026-05-05 | ⚠ MEDIO si se ejecuta app_publish.py |
| `data.js.mock.bak` | — | Nombre "mock" engañoso — contiene código real | Confusión de nomenclatura | INFO |
| `PAV MATINAL PE_A FLOR/portal.html` | todo | Portal alternativo sin consumidor | Puede tener hardcode no auditado | ⚠ MEDIO — requiere revisión |
| `LEGACY/orbit_matinal_v42.py` | MAP_11T_FINE | Listas hardcodeadas de marcas por segmento | Si producto activos.xlsx no existe, 11T usa este mapa sin validar contra ERP | ⚠ ALTO — las marcas pueden estar desactualizadas |

**Resultado**: No hay mock data activo en el flujo principal (Flask → data.js → portal). El riesgo principal es la interpolación lineal en `dailyEvolution` y el mapa hardcodeado de 11 Titulares por ausencia de `producto activos.xlsx`.

---

## 6. VALIDACIÓN DE VENDEDORES

| Regla | Estado | Dónde está implementada | Evidencia |
|---|---|---|---|
| V2 excluido | ✅ CORRECTO | Motor: `VENDEDORES_EXCLUIDOS = [2, 5]`; server_orbit.py: `USERS` sin V2; vendedores_activos.csv sin V2 | log_motor: 7 vendedores (V3,V4,V6,V7,V8,V9,V10) |
| V5 excluido | ✅ CORRECTO | Mismo mecanismo | Igual |
| V3 = Nadia Gambino | ✅ CORRECTO | vendedores_activos.csv: `V3, NADIA GAMBINO`; server_orbit.py USERS: `v3→Nadia Gambino`; mod_volumen_vendedor: `3,GAMBINO NADIA` | Tres fuentes coinciden |
| V3 sin autoservicios | ✅ CORRECTO | Motor: no hay filtro explícito en ventas (V3 no tiene Autoservicio en clientes.xlsx); server_orbit.py: `if cod == "V3": ccc_as = 0`; data.js: `segmento_excluye: ["AUTOSERVICIO"]` | mod_ccc_segmento: V3 solo con TRADICIONAL |
| V3 sin objetivo autoservicio | ✅ CORRECTO | mod_volumen_vendedor V3: `clientes_auto=0`; server_orbit.py dashboard: `ccc_as = 0 if V3` | OK |
| V7 con datos | ✅ CORRECTO desde 2026-05-06 | clientes.xlsx actualizado (+302 filas V7) | mod_volumen_vendedor V7 presente con datos |
| V9 con datos | ✅ CORRECTO desde 2026-05-06 | clientes.xlsx actualizado (+355 filas V9) | mod_volumen_vendedor V9 presente con datos |

**Sin problemas de vendedores detectados en la auditoría.**

---

## 7. VALIDACIÓN DE DÍAS COMERCIALES

### Implementación actual

`contar_dias_habiles()` en `server_orbit.py`:
- Excluye domingos (`weekday() == 6`)
- Excluye feriados desde `09_CONFIG/feriados.csv`
- Feriados mayo 2026: `2026-05-01` (Día del Trabajador) y `2026-05-25` (Revolución de Mayo)
- Total mayo 2026: **24 días comerciales** (correcto)

### Estado al 2026-05-12

```
Datos en mod_volumen_vendedor.csv:
  fecha_ejecucion : 2026-05-11 (domingo — el motor se ejecuta el día anterior)
  fecha_objetivo  : 2026-05-12 (martes — día de la matinal)
  dia_objetivo    : Ma

Días corridos hasta 2026-05-11:
  02/05 (Sáb) + 04/05 (Lun) + 05/05 (Mar) + 06/05 (Mié) + 07/05 (Jue)
  + 08/05 (Vie) + 09/05 (Sáb) + 11/05 (Lun) = 8 días comerciales corridos
```

| Parámetro | Estado | Detalle |
|---|---|---|
| Total días comerciales mayo | ✅ 24 | Correcto con 2 feriados excluidos |
| Días corridos al 2026-05-11 | ✅ 8 | Motor calcula con fecha_ejecucion |
| Feriados detectados | ✅ 2 | 01/05 y 25/05 |
| Sábados como comerciales | ✅ OK | Decisión confirmada en auditoría anterior |
| Día operativo siguiente | ✅ Ma 12/05 | Calculado por el motor y expuesto como `dia_objetivo` |
| `diaActivo` en data.js | ✅ CORRECTO | Calculado dinámicamente: `fecha_corte + 1 día` |

**No se detectan problemas en el cálculo de días comerciales.**

---

## 8. VALIDACIÓN DE ZONAS Y LOCALIDADES

### Cobertura actual

`clientes_dia.csv` (346 filas) tiene campos: `localidad`, `codigo_ruta`, `ruta`, `orden`, `dias_visita`, `segmento_operativo`.

### Distribución por vendedor (día martes 12/05)

| Vendedor | Clientes día | Ventas ayer | Estado |
|---|---|---|---|
| V3 Gambino | 47 | 2 clientes, 18 bot, $54K | Solo TRADICIONAL (correcto) |
| V4 Gribaudo | 52 | 0 clientes, 0 bot, $0 | Vendedor LU/MI/VI, no trabaja Ma |
| V6 Peyronel | 71 | 0 clientes, 0 bot, $0 | No trabaja Ma |
| V7 Jofre | 60 | 0 clientes, 0 bot, $0 | No trabaja Ma |
| V8 Alvarez | 55 | 15 clientes, 662 bot, $3.5M | Trabaja Ma |
| V9 Sanchez | 21 | 0 clientes, 0 bot, $0 | No trabaja Ma |
| V10 Ortega | 40 | 7 clientes, 92 bot, $445K | Trabaja Ma |

### Problemas detectados en zonas/localidades

| Problema | Severidad | Detalle |
|---|---|---|
| No existe dataset independiente de zonas | ⚠ MEDIO | No hay forma de comparar zonas esperadas vs procesadas sin el maestro ERP |
| `hist_cliente_mes.csv` no se regenera diariamente | ⚠ BAJO | Último update: 2026-05-05. Puede tener datos desactualizados |
| `hist_cliente_resumen.csv` y `hist_cliente_producto.csv` | ⚠ BAJO | Misma fecha, módulo src/orbit viejo |

---

## 9. VALIDACIÓN DE KPIs

| KPI | Archivo fuente | Dónde se calcula | Riesgo | Validado |
|---|---|---|---|---|
| Ventas del día (`venta_ayer`) | `ventas.csv` → `historial_ventas_cliente.csv` | `orbit_matinal_v42.py`: `ventas_validas_dia` → `venta_ayer` en `mod_volumen_vendedor` | ✅ Bajo — 80 ventas validadas del día | ✅ |
| Ventas del mes (`acumulado_mes`) | `02_HISTORY/historial_ventas_cliente.csv` | `orbit_matinal_v42.py`: `ventas_mes = historial_ventas[hasta fecha_ejecucion]` | ✅ Bajo — 5651 filas historial | ✅ |
| CCC del día | `ventas.csv` → `clientes_dia` | Motor: `ccc_ayer_flag` (importe_ayer > 0) | ✅ Correcto por regla CCC = Importe Neto > 0 | ✅ |
| CCC del mes | Ninguno | No existe fuente — `ccc_mes: 0` en data.js | ⚠ ALTO — métrica faltante importante | ❌ Sin fuente |
| Botellas del día | `mod_ccc_segmento.csv` → `botellas_vendidas` | Motor: suma por vendedor/segmento | ✅ OK — 662+92+18 = 772 botellas Ma | ✅ |
| Botellas del mes | `clientes_dia.csv` → `botellas_mes` | Motor: desde `historial_ventas_cliente.csv` | ✅ OK — dato presente en CSV | ✅ |
| Cobertura tradicional (≥3 bot) | `mod_ccc_segmento.csv` → `coberturas_logradas` | Motor: `cobertura_ayer_flag` según umbral por segmento | ✅ OK | ✅ |
| Cobertura autoservicio (≥6 bot) | Igual | Igual | ✅ OK — umbral 6 en `clientes.xlsx` | ✅ |
| Cobertura on premise/vinoteca (≥6 bot) | Igual | Igual | ✅ OK | ✅ |
| 11 Titulares | `mod_11_titulares.csv` | Motor: MAP_11T_FINE (hardcoded) | ⚠ ALTO — mapa hardcodeado, no validado contra ERP. `producto activos.xlsx` no existe → `PRODUCTOS_CARGADOS = 0` | ⚠ Parcial |
| Descuentos | `mod_alertas_descuentos.csv` | Motor: reglas desde `reglas_acciones_mayo_2026_orbit.csv` + fallback hardcodeado | ✅ OK — 91/103 con fuente CSV en auditoría 07/05 | ✅ |
| Sin cargo | No detectado | No existe campo explícito en outputs | ⚠ MEDIO — no se reporta sin cargo | ❌ Sin fuente |
| Avance % | `mod_volumen_vendedor.csv` → `avance_pct` | Motor: `acumulado_mes / objetivo_mes * 100` | ✅ Correcto según regla CLAUDE.md | ✅ |
| Tendencia | `mod_volumen_vendedor.csv` → `tendencia_mes` | Motor: `(acumulado_mes / dias_corridos) * total_mes` | ✅ Correcto | ✅ |
| Clientes sin compra | `clientes_dia.csv` → `estado_cliente == SIN_COMPRA_MES` | Motor + server_orbit.py `/api/clientes` | ✅ OK — 346 clientes con estado real | ✅ |
| Gastos por acción | `mod_gastos_accion.csv` | Motor: `valor_descuento × cant_base` | ✅ OK — validado 2026-05-07 | ✅ |
| Objetivo del día | `data.js` | `tObj / calendario.total` (promedio lineal) | ⚠ BAJO — no considera zonificación real por día | INFO |
| Evolución diaria (gráfico) | Ninguno | `data.js`: interpolación lineal `tAcum / corridos * día` | ⚠ MEDIO — no son datos reales por día sino proyección | ❌ No real |

### Problemas críticos en KPIs

**CCC ACUMULADO DEL MES** — No existe ninguna fuente real. El historial de ventas tiene los datos para calcularlo pero nadie lo computa. En `data.js` aparece como `ccc_mes: 0` (honesto). Este es el KPI faltante más importante de la matinal.

**11 TITULARES SIN MAESTRO DE PRODUCTOS** — `producto activos.xlsx` no existe. Log del motor: `PRODUCTOS_CARGADOS: 0`. Las 3798 filas de `mod_11_titulares.csv` se generan desde `MAP_11T_FINE` (dict hardcodeado en Python con ~11 marcas por segmento). Si el ERP cambia nombres de marcas, el mapa queda desactualizado sin aviso.

**EVOLUCIÓN DIARIA NO REAL** — El gráfico de `dailyEvolution` en el portal es una proyección lineal, no datos reales por día. No existe ningún CSV con ventas acumuladas por fecha.

---

## 10. REPORTE FINAL

---

### PROBLEMAS CRÍTICOS (bloquean confiabilidad de datos)

#### CRÍTICO 1 — `producto activos.xlsx` no existe
- **Archivo**: `01_INPUTS/producto activos.xlsx`
- **Impacto**: Motor registra `PRODUCTOS_CARGADOS: 0`. Los 11 Titulares se calculan 100% desde el dict hardcodeado `MAP_11T_FINE` en `orbit_matinal_v42.py`. Si el ERP usa nombres de marca distintos a los del dict, el cálculo es incorrecto sin alerta.
- **Evidencia**: `log_motor.csv` → `PRODUCTOS_CARGADOS,0`
- **Acción**: Exportar el maestro de productos desde Gescom y colocarlo como `01_INPUTS/producto activos.xlsx`. Revisar que las marcas del ERP coincidan con `MAP_11T_FINE`.

#### CRÍTICO 2 — CCC acumulado del mes no tiene fuente real
- **Archivo**: Ninguno — métrica inexistente en todos los CSVs
- **Impacto**: `kpisGerencia.ccc_mes: 0` en data.js. El portal gerencial muestra CCC del mes = 0. Dato clave de la matinal.
- **Evidencia**: `data.js` línea 79 `ccc_mes: 0`, CHANGELOG 2026-05-05 "CCC ACUMULADOS muestra 0, pendiente de fuente real"
- **Acción**: Calcular `ccc_mes_flag` acumulado desde `historial_ventas_cliente.csv` en el motor. Ya existe el campo `ccc_mes_flag` en `clientes_dia.csv` (binario) pero el total por vendedor/segmento no se expone.

#### CRÍTICO 3 — `orbit_portal_data.json` obsoleto + endpoint /api/orbit-data activo
- **Archivo**: `06_APP_DATA/orbit_portal_data.json`
- **Impacto**: El endpoint `GET /api/orbit-data` está activo en `server_orbit.py` y sirve este JSON del 2026-05-05 con datos incorrectos (`cubiertos: 0`, `clientesCriticos: []`, `corridos: 3`). Aunque `data.js` no lo llama, cualquier consumidor externo (AppScript, mobile, script de prueba) recibiría datos viejos como si fueran reales.
- **Evidencia**: `06_APP_DATA/orbit_portal_data.json` → `meta.fecha_corte: "2026-05-05"`, `segmentos[*].cubiertos: 0`
- **Acción**: Desactivar `/api/orbit-data` o actualizar `tools/orbit_truth_audit.py` para que regenere el JSON con datos del pipeline actual.

#### CRÍTICO 4 — Evolución diaria es interpolación, no datos reales
- **Archivo**: `PAV MATINAL PE_A FLOR/data.js` líneas 88-95
- **Impacto**: El gráfico "Plan vs Real" usa `(tAcum / calendario.corridos) * (i+1)`. No existe ningún CSV con ventas acumuladas por fecha de día. El gráfico muestra una línea recta perfecta que no refleja cómo se distribuyeron realmente las ventas.
- **Evidencia**: `data.js` línea 91: `real: i < calendario.corridos ? (tAcum / calendario.corridos) * (i + 1) : null`
- **Acción**: El historial `historial_ventas_cliente.csv` tiene `fecha_comprobante` por registro. El motor podría agregar un módulo de evolución diaria real. Es trabajo de desarrollo, no una corrección de datos.

---

### PROBLEMAS MEDIOS

#### MEDIO 1 — portal.html vs index.html (dos portales)
- `PAV MATINAL PE_A FLOR/portal.html` (2026-05-11 22:41) vs `index.html` (2026-05-05 19:09)
- Flask sirve `index.html`. `portal.html` es más reciente pero sin consumidor activo conocido.
- **Acción**: Revisar si `portal.html` reemplaza o complementa a `index.html`. Si es la versión actualizada, renombrarlo o ajustar Flask para servirlo.

#### MEDIO 2 — app_publish.py puede regenerar JSONs obsoletos
- Si alguien ejecuta `app_publish.py`, regenerará `06_APP_DATA/*.json` con datos incorrectos (tiene bug de `acumulado=0` en `build_avance_map()`).
- El pipeline oficial `REGENERAR_DATOS_ORBIT.bat` NO incluye `app_publish.py`. 
- **Acción**: Desactivar o archivar `app_publish.py`. Agregar comentario de "DEPRECADO" en el encabezado.

#### MEDIO 3 — src/orbit/ desintegrado del pipeline
- El directorio `src/orbit/` contiene ~15 módulos Python (perf_engine, alertas_orbit, copiloto_vendedor, etc.) con fechas 2026-04-09 a 2026-04-21.
- Sus outputs están en `05_INTELLIGENCE_ORBIT/` con datos del 2026-05-05.
- El pipeline `REGENERAR_DATOS_ORBIT.bat` no los ejecuta.
- **Acción**: Definir si estos módulos son activos o legacy. Si son legacy, moverlos a `LEGACY/` o agregar `_NO_USAR_` como prefijo.

#### MEDIO 4 — hist_cliente_mes/producto/resumen no se regeneran diariamente
- `04_DATASETS_ORBIT/hist_cliente_mes.csv`, `hist_cliente_producto.csv`, `hist_cliente_resumen.csv` tienen fecha 2026-05-05.
- El motor `orbit_matinal_v42.py` genera estas hojas pero `datasets_orbit.py` no las exporta diariamente (no aparecen en el log de hoy).
- **Acción**: Verificar si `datasets_orbit.py` exporta todas las hojas del Excel o solo algunas.

#### MEDIO 5 — `clientes_excluidos.csv` es parcialmente defensivo
- Los 10 clientes excluidos están correctamente formalizados.
- Pero hay una regla dinámica (Ruta DEPOSITO + sin DiasVisita) que podría excluir clientes legítimos si en el futuro se agrega un cliente en zona DEPOSITO con visitas programadas.
- **Acción**: Documentar la regla en el CSV y revisar si aplica a todos los casos futuros.

#### MEDIO 6 — Sin cargo no está en ningún output
- No se detectó ningún CSV o endpoint que reporte ventas "sin cargo" (bonificaciones sin costo).
- Los campos `valorDescuento`, `Descuento` en `ventas.csv` capturan descuentos. Sin cargo requeriría filtrar `TipoDeVenta` o campos específicos del ERP.
- **Acción**: Verificar con el usuario si sin cargo existe como campo en Gescom y definir si debe incluirse en los módulos del motor.

#### MEDIO 7 — Archivos basura en la raíz del proyecto
- Archivos con nombres de tipos Python: `3`, `float`, `None`, `str`, `pd.DataFrame`, `Dict[str]` (fecha 2026-04-10).
- Probablemente creados por un script que usó `open(str(tipo), 'w')` con variables de tipo en lugar de rutas de archivo.
- **Acción**: Eliminar estos 6 archivos (confirmar con `type` o `Get-Content` que están vacíos o son irrelevantes).

#### MEDIO 8 — historial_ventas.csv antiguo vs historial_ventas_cliente.csv activo
- `02_HISTORY/historial_ventas.csv` (2026-04-11, 08:42) — formato original
- `02_HISTORY/historial_ventas_cliente.csv` (2026-05-12, activo) — formato normalizado por el motor
- El historial viejo no es consumido pero podría confundir.
- **Acción**: Archivar `historial_ventas.csv` o agregar prefijo `_NO_USAR_`.

---

### PROBLEMAS MENORES

- `00_DROPZONE_DIARIA/ventas.csv` y `resultado.xlsx` con fecha 2026-04-16 — no consumidos, pero inducen confusión.
- `08_LOGS/orbit_qa_resumen_latest.json` con datos del 2026-05-05 — nombre "latest" desactualizado.
- `PAV MATINAL PE_A FLOR/Orbit Peñaflor PAV Matinal.html` — archivo HTML sin relación con el portal activo, fecha 2026-04-04.
- `tools/orbit_truth_audit.py` genera `orbit_portal_data.json` que está obsoleto — si se ejecuta manualmente, sobreescribe con datos potencialmente incorrectos.

---

## ARCHIVOS QUE DEBEN CORREGIRSE

| Archivo | Corrección requerida |
|---|---|
| `LEGACY/orbit_matinal_v42.py` | Agregar cálculo de `ccc_mes` por vendedor y segmento desde `historial_ventas_cliente.csv`. Exportar como nueva hoja en el Excel. |
| `LEGACY/orbit_matinal_v42.py` | Validar que `producto activos.xlsx` existe al inicio y emitir WARNING explícito si falta. |
| `server_orbit.py` | Desactivar o deprecar `/api/orbit-data` (o actualizar para que lea CSVs reales). |
| `PAV MATINAL PE_A FLOR/data.js` | `dailyEvolution` debería calcularse desde datos reales cuando estén disponibles, o documentar explícitamente que es proyección. |
| `src/orbit/datasets/datasets_orbit.py` | Verificar que exporta `hist_cliente_mes`, `hist_cliente_producto`, `hist_cliente_resumen` diariamente. |

---

## ARCHIVOS QUE DEBERÍAN DEJAR DE USARSE

| Archivo | Razón |
|---|---|
| `app_publish.py` | Genera JSONs obsoletos. Reemplazado por Flask + CSVs directos. Deprecar formalmente. |
| `run_orbit.py` | Runner antiguo. Reemplazado por `REGENERAR_DATOS_ORBIT.bat`. |
| `06_APP_DATA/orbit_portal_data.json` | Datos 2026-05-05, obsoletos. Eliminar o actualizar automáticamente. |
| `06_APP_DATA/clientes_hoy.json`, `alertas_app.json`, `dashboard_vendedor.json`, `charts_app.json`, `cliente_detalle.json` | Todos obsoletos 2026-05-05, reemplazados por CSVs. |
| `00_DROPZONE_DIARIA/ventas.csv` y `resultado.xlsx` | Datos de abril, sin uso activo. |
| `PAV MATINAL PE_A FLOR/data_provider.js.bak` | Backup obsoleto. |
| `src/orbit/` (completo si no tiene consumidor activo) | Módulos del 15/04 a 21/04, sin integración al pipeline actual. Mover a `LEGACY/` o eliminar. |
| `3`, `float`, `None`, `str`, `pd.DataFrame`, `Dict[str]` | Archivos basura en raíz. Eliminar. |

---

## FUENTES OFICIALES RECOMENDADAS

| Dato | Fuente oficial | Frecuencia de actualización |
|---|---|---|
| Ventas | `01_INPUTS/ventas.csv` | Diaria (exportación manual Gescom) |
| Objetivos + avance | `01_INPUTS/resultado.xlsx` | Diaria |
| Maestro clientes | `01_INPUTS/clientes.xlsx` | Cuando haya altas/bajas |
| Maestro productos | `01_INPUTS/producto activos.xlsx` | **⚠ FALTA** — exportar desde Gescom |
| KPIs por vendedor | `04_DATASETS_ORBIT/mod_volumen_vendedor.csv` | Cada ejecución del motor |
| CCC del día | `04_DATASETS_ORBIT/mod_ccc_segmento.csv` | Cada ejecución |
| CCC del mes | **No existe — pendiente de implementar** | — |
| 11 Titulares | `04_DATASETS_ORBIT/mod_11_titulares.csv` | Cada ejecución (mapa hardcoded) |
| Alertas descuentos | `04_DATASETS_ORBIT/mod_alertas_descuentos.csv` | Cada ejecución |
| Calendario comercial | `09_CONFIG/feriados.csv` + `server_orbit.py` | Por mes o cuando haya cambios |
| Vendedores activos | `09_CONFIG/vendedores_activos.csv` | Cuando haya cambios en equipo |
| Clientes excluidos | `09_CONFIG/clientes_excluidos.csv` | Defensivo, cuando se detecte nuevo caso |

---

## PLAN DE CORRECCIÓN POR FASES

### Fase 1 — Inmediato (sin tocar código)
1. Exportar `01_INPUTS/producto activos.xlsx` desde Gescom.
2. Revisar `portal.html` vs `index.html` — definir cuál es el portal activo.
3. Eliminar archivos basura raíz (`3`, `float`, `None`, `str`, `pd.DataFrame`, `Dict[str]`).

### Fase 2 — Corrección de datos (motor)
4. Implementar cálculo de `ccc_mes` en `orbit_matinal_v42.py` desde `historial_ventas_cliente.csv`.
5. Exportar como hoja nueva `mod_ccc_mes` en el Excel y CSV en `04_DATASETS_ORBIT/`.
6. Conectar `ccc_mes` en `/api/diagnostico` y `/api/dashboard`.
7. Actualizar `data.js`: `ccc_mes: diag.ccc_mes || 0`.

### Fase 3 — Limpieza de archivos obsoletos
8. Marcar `app_publish.py` como DEPRECADO o mover a `backup_bat/`.
9. Desactivar endpoint `/api/orbit-data` o actualizarlo para leer CSVs reales.
10. Archivar `06_APP_DATA/*.json` obsoletos en `99_BACKUPS_ORBIT/` o eliminar.
11. Mover `src/orbit/` a carpeta `LEGACY/` o eliminar si no tiene consumidor activo.
12. Renombrar `02_HISTORY/historial_ventas.csv` → `_NO_USAR_historial_ventas_legacy.csv`.

### Fase 4 — Mejoras de calidad
13. Implementar evolución diaria real desde `historial_ventas_cliente.csv` (agrupar por fecha).
14. Investigar campo "sin cargo" en Gescom y agregar al motor si existe.
15. Verificar que `datasets_orbit.py` regenera `hist_cliente_mes.csv` diariamente.

---

## VALIDACIONES OBLIGATORIAS ANTES DE CERRAR

| Área | Estado | Evidencia | Acción recomendada |
|---|---|---|---|
| Fuentes de datos | ✅ Mayormente OK | ventas.csv, resultado.xlsx, clientes.xlsx presentes y actualizados 2026-05-11 | Exportar `producto activos.xlsx` |
| Duplicados | ⚠ Requiere acción | portal.html vs index.html; JSONs obsoletos en 06_APP_DATA; src/orbit viejo | Limpiar fase 3 |
| Mock data | ✅ Sin mock activo | data.js llama APIs reales; dailyEvolution es proyección documentada | Documentar proyección; CCC mes = 0 honesto |
| Vendedores | ✅ CORRECTO | V2/V5 excluidos en 3 capas; V3=Nadia Gambino confirmado; 7 vendedores en todos los outputs | Sin acción |
| V3 sin autoservicios | ✅ CORRECTO | mod_ccc_segmento: V3 solo TRADICIONAL; server_orbit.py: ccc_as=0 para V3; data.js: segmento_excluye | Sin acción |
| Días comerciales | ✅ CORRECTO | total=24, feriados 01/05 y 25/05, fecha_objetivo=2026-05-12, dia_objetivo=Ma | Sin acción |
| Zonas/localidades | ⚠ Sin validación cruzada | clientes_dia tiene localidad/ruta pero no hay maestro de zonas independiente | Exportar maestro de zonas si existe en Gescom |
| KPIs | ⚠ 2 KPIs faltantes | CCC mes = 0 (sin fuente); evolución diaria = proyección lineal | Implementar ccc_mes (fase 2); evolución diaria (fase 4) |
| Portal vendedor | ✅ Operativo | index.html + data.js + Flask 8502 sirven datos reales | Resolver portal.html vs index.html |
| Portal gerencial | ⚠ KPI faltante | Dashboard gerencial sin CCC acumulado del mes | Implementar en fase 2 |
| 11 Titulares | ⚠ Mapa hardcodeado | producto activos.xlsx no existe; MAP_11T_FINE sin validar contra ERP | Exportar producto activos.xlsx (fase 1) |
| Sin cargo | ❌ No implementado | No existe campo ni output de sin cargo en ningún CSV | Investigar en Gescom |

---

*Fin de auditoría. Próxima acción recomendada: Fase 1 (exportar producto activos.xlsx y resolver portal.html).*
*No se modificó ningún archivo del proyecto durante esta auditoría.*
