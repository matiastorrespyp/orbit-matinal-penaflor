# PROMPT_AUDITORIA_TOTAL_DATOS_PAV_MATINAL

## Contexto del Sistema

Estamos trabajando en Orbit Matinal Peñaflor, proyecto PAV Matinal para reunión comercial diaria.

El problema actual es crítico: el portal muestra KPIs que no generan confianza. Ya se detectaron inconsistencias en CCC, cobertura, base de clientes, zona/día, mes acumulado, clientes pendientes, 11 Titulares y diferencia entre `/index.html` y `/portal.html`.

La prioridad absoluta es precisión del dato antes que diseño.

No quiero más cambios visuales, logos ni mejoras estéticas hasta cerrar la trazabilidad completa de datos.

El sistema debe trabajar solamente sobre datos reales disponibles en el proyecto y en la documentación de Obsidian.

## Fuentes de conocimiento obligatorias

Analizar primero la documentación existente en Obsidian y repo:

- `04_PROMPTS_MAESTROS/`
- `08_ARQUITECTURA/`
- `05_ERRORES_Y_SOLUCIONES/`
- `CLAUDE.md`
- `CHANGELOG_AI.md`
- `NEXT_TASK.md`
- `AUDITORIA_ORBIT_MATINAL_*.md`
- cualquier documento `.md` relacionado con Matinal, PAV, Peñaflor, KPIs, CCC, cobertura, 11 Titulares, portal, AppSheet, datasets o errores previos.

Objetivo de esta lectura:
- detectar reglas ya definidas;
- evitar repetir errores;
- recuperar nombres correctos de archivos, columnas, rutas, endpoints y lógica comercial;
- usar Obsidian como fuente operativa de verdad.

## Archivos fuente reales obligatorios

Auditar y cruzar datos desde estos archivos reales:

### Inputs principales

- `01_INPUTS/ventas.csv`
- `01_INPUTS/resultado.xlsx`
- `01_INPUTS/clientes.xlsx`
- `01_INPUTS/producto activos.xlsx`
- `01_INPUTS/RAW_PRODUCTOS/`
- cualquier otro archivo activo dentro de `01_INPUTS/`

### Históricos

- `02_HISTORY/historial_ventas.csv`
- `02_HISTORY/historial_ventas_cliente.csv`

### Outputs legacy

- `03_OUTPUTS/MATINAL_PENA_V42.xlsx`
- cualquier otro output relacionado con Matinal Peñaflor.

### Datasets Orbit

- `04_DATASETS_ORBIT/clientes_dia.csv`
- `04_DATASETS_ORBIT/mod_volumen_vendedor.csv`
- `04_DATASETS_ORBIT/mod_ccc_segmento.csv`
- `04_DATASETS_ORBIT/mod_11_titulares.csv`
- `04_DATASETS_ORBIT/vendedores_activos.csv`
- todos los demás `.csv` dentro de `04_DATASETS_ORBIT/`

### Inteligencia / App data

- `05_INTELLIGENCE_ORBIT/`
- `06_APP_DATA/`

### Código

- `run_orbit.py`
- `server_orbit.py`
- `app_matinal_penaflor.py`
- `LEGACY/orbit_matinal_v42.py`
- scripts generadores de datasets
- `PAV MATINAL PE_A FLOR/index.html`
- `PAV MATINAL PE_A FLOR/portal.html`
- `PAV MATINAL PE_A FLOR/data.js`
- `PAV MATINAL PE_A FLOR/app.jsx`
- `PAV MATINAL PE_A FLOR/screens/`
- `test_portal.py`
- `test_kpis.py`
- `audit_pav_matinal_data.py`

## Objetivo principal

Construir una auditoría total del flujo de datos PAV Matinal Peñaflor para que cada número visible en el portal tenga trazabilidad exacta:

archivo fuente real → script que calcula → dataset intermedio → endpoint Flask → variable JS → KPI visible.

No se puede permitir ningún KPI sin fuente, sin fórmula, sin período definido o con denominador incorrecto.

## Reglas de negocio obligatorias

### Vendedores

- Peñaflor debe excluir vendedores 2 y 5 de todos los reportes.
- V3 es Nadia Gambino.
- V3 Nadia Gambino no trabaja Autoservicio.
- Para V3, Autoservicio debe quedar fuera de objetivos, CCC, cobertura y 11 Titulares si corresponde.

### CCC

Definir y separar claramente:

1. `CCC Compradores Mes`
   - cliente único con `ImporteNetoItem > 0`;
   - fuente primaria: `ventas.csv` del mes actual;
   - excluye V2 y V5;
   - por vendedor y total compañía;
   - este es el KPI real de compradores del mes.

2. `CCC Día`
   - cliente único con `ImporteNetoItem > 0`;
   - última fecha operativa o día seleccionado;
   - no confundir con CCC mensual.

3. `CCC Ruta / Cobertura Cartera`
   - cliente de cartera/ruta que compró;
   - debe cruzar ventas reales contra `clientes.xlsx`;
   - no usar si la base de clientes está desfasada;
   - debe mostrar claramente el denominador.

Nunca llamar simplemente “CCC” si no se especifica si es:
- mes;
- día;
- ruta;
- ERP;
- cartera.

### Cobertura

Auditar cobertura desde cero.

Validar:
- numerador;
- denominador;
- fuente;
- período;
- si corresponde a mes, día, zona o cartera total.

Reglas:
- Tradicional cubierto si compra >= 3 botellas.
- Autoservicio / On Premise / Vinoteca cubierto si compra >= 6 botellas.
- No calcular cobertura sobre una base parcial sin etiquetarlo.
- Si el portal muestra “258 de 548”, debe explicar exactamente qué son 258 y qué son 548.
- Si la cartera real Peñaflor tiene más de 548 clientes, no puede llamarse “Cobertura General” sin aclaración.

### 11 Titulares

Auditar 11 Titulares desde cero.

Separar:
- clientes;
- marcas;
- impactos;
- objetivos;
- cobertura por segmento;
- acumulado mes;
- día/zona.

Reglas:
- 11T puede ser mayor que CCC si cuenta impactos/marcas y no clientes.
- El portal debe etiquetarlo claramente.
- No mostrar 11T como si fueran clientes.
- No usar fallback silencioso.
- No usar datos hardcodeados.

### Zona / Día / Matinal

El portal no puede mezclar visualmente:

- zona VI;
- día seleccionado;
- mes acumulado;
- cartera total;
- clientes planificados;
- clientes pendientes;
- datos de compañía.

Si el usuario selecciona VI, cada KPI debe indicar si:
- filtra por VI;
- no filtra por VI;
- corresponde al mes total;
- corresponde a zona/día;
- corresponde a cartera.

## Variables/KPIs mínimos a auditar

Auditar obligatoriamente estas variables:

### Comerciales

- venta acumulada mes;
- venta del día;
- objetivo mensual;
- avance %;
- tendencia proyectada;
- diferencia vs objetivo;
- venta por vendedor;
- ranking de vendedores.

### Clientes

- total cartera real desde `clientes.xlsx`;
- total cartera por vendedor;
- total clientes por zona/día;
- clientes planificados;
- clientes pendientes;
- clientes sin compra mes;
- clientes sin compra día/zona;
- CCC Compradores Mes;
- CCC Día;
- CCC Ruta;
- CCC ERP;
- clientes fuera de ruta;
- clientes del maestro con venta;
- clientes con venta que no están en maestro.

### Cobertura

- cobertura general;
- cobertura por vendedor;
- cobertura por segmento;
- cobertura por zona/día;
- cobertura mensual;
- numerador y denominador exacto de cada cobertura.

### Segmentos

- Tradicional;
- Autoservicio;
- On Premise;
- Vinoteca;
- otros segmentos detectados;
- mapeo desde `Ramo`, `Subramo`, `subsegmento`, `segmento_operativo`, `segmento_11t`.

### 11 Titulares

- 11T acumulado;
- 11T día;
- 11T por vendedor;
- 11T por segmento;
- marcas titulares;
- clientes/impactos cubiertos;
- objetivo/base.

### Alertas

- alertas críticas;
- alertas por descuento;
- fuente de alertas;
- si son acumuladas, diarias o actuales.

### Portal

Comparar:

- `/index.html`
- `/portal.html`
- `/api/diagnostico`
- `/api/dashboard`
- `/api/vendedor/{id}`
- `/api/clientes`
- `/api/alertas`
- `/api/planificacion`

## Prohibiciones

- No inventar datos.
- No usar mock.
- No usar fallback silencioso.
- No corregir visualmente sin corregir fuente.
- No cambiar logos.
- No tocar diseño.
- No hacer commit.
- No hacer push.
- No modificar LEGACY sin autorización explícita.
- No usar datasets intermedios como verdad si no se verificó contra fuente real.
- No aceptar un denominador sin explicar de dónde sale.
- No mostrar “Cobertura General” si no usa cartera real total.
- No mostrar “CCC Mes” si mezcla CCC día, ruta o histórico desfasado.

## Tarea principal

Crear o actualizar un script independiente:

`audit_pav_matinal_data.py`

El script debe:

1. Leer todas las fuentes reales.
2. Detectar columnas y tipos.
3. Normalizar fechas, vendedores, clientes, importes y segmentos.
4. Recalcular KPIs desde fuente real.
5. Comparar contra datasets intermedios.
6. Comparar contra endpoints Flask.
7. Comparar contra variables visibles de `/index.html` y `/portal.html` cuando sea posible.
8. Marcar cada KPI como:
   - OK;
   - ERROR;
   - DESFASADO;
   - PARCIAL;
   - SIN FUENTE;
   - DENOMINADOR INVÁLIDO;
   - NOMBRE CONFUSO.

## Salida obligatoria

Generar diagnóstico con estas tablas.

### Tabla 1 — Inventario de fuentes

| Archivo | Existe | Fecha modificación | Filas | Columnas clave | Rango fechas | Estado |

### Tabla 2 — Base de clientes

| Fuente | Total clientes | Vendedores incluidos | Vendedores excluidos | Por vendedor | Estado |

Debe responder:
- cuántos clientes reales hay en `clientes.xlsx`;
- cuántos quedan excluyendo V2 y V5;
- cuántos hay por vendedor;
- cuántos hay por día/zona;
- por qué el portal muestra 548 si la cartera real es mayor.

### Tabla 3 — CCC

| KPI | Fuente real | Cálculo | Valor fuente | Valor dataset | Valor endpoint | Valor portal | Estado |

Incluir:
- CCC Compradores Mes;
- CCC Día;
- CCC Ruta;
- CCC ERP;
- CCC por vendedor;
- CCC V3;
- CCC V3 Autoservicio.

### Tabla 4 — Cobertura

| KPI visible | Numerador | Denominador | Fuente numerador | Fuente denominador | Período | Zona | Estado |

Debe explicar:
- de dónde sale 258;
- de dónde sale 548;
- si cobertura 47% es mes, cartera, zona o dato parcial;
- cuál debería ser el nombre correcto.

### Tabla 5 — 11 Titulares

| KPI visible | Qué cuenta | Fuente | Vendedor | Segmento | Período | Estado | Etiqueta recomendada |

Debe explicar:
- por qué 11T puede ser mayor que CCC;
- si está contando marcas, impactos o clientes;
- si corresponde a mes o zona.

### Tabla 6 — Portal

| Pantalla | KPI | Variable JS | Endpoint | Fuente final | Filtra por día/zona | Estado |

Comparar:
- Dashboard principal;
- Vendedores;
- Clientes críticos;
- Planificación;
- Alertas;
- Portal vendedor.

### Tabla 7 — Errores críticos

| Error | Causa raíz | Archivo responsable | Riesgo operativo | Corrección propuesta |

## Preguntas que debe responder obligatoriamente

1. ¿La pantalla principal muestra mes acumulado, zona/día o una mezcla?
2. ¿El selector VI filtra realmente los KPIs o solo cambia el título?
3. ¿Cuántos clientes reales tiene Peñaflor en `clientes.xlsx`?
4. ¿Por qué el portal usa 548 como denominador?
5. ¿Qué significa 258?
6. ¿La cobertura 47% es válida?
7. ¿Qué significa cada valor en el panel Vendedores?
8. ¿CCC, Total, Pend. y 11T son comparables?
9. ¿Qué KPI debe mostrarse como principal en la reunión matinal?
10. ¿Qué KPIs deben separarse como “Mes”, “Día/Zona” y “Cartera”?
11. ¿Qué archivos están desfasados?
12. ¿Qué datasets se pueden seguir usando y cuáles no?
13. ¿Qué endpoints devuelven datos confiables?
14. ¿Qué pantalla debe quedar operativa: `/index.html` o `/portal.html`?

## Propuesta de corrección

Después del diagnóstico, proponer corrección en etapas:

### Etapa A — Datos críticos

Corregir únicamente KPIs que hoy invalidan la operación:

- CCC;
- cobertura;
- base de clientes;
- zona/día;
- denominadores;
- etiquetas engañosas.

### Etapa B — Motor

Corregir motor legacy solo después de confirmar:

- qué script genera cada dataset;
- qué archivos dependen de ese dataset;
- qué riesgo hay de romper AppSheet, portal o PDFs.

### Etapa C — Portal

Solo después de validar datos:

- renombrar etiquetas;
- separar secciones Mes / Zona / Cartera;
- evitar que el selector de día parezca filtrar lo que no filtra;
- usar logos reales únicamente si existen assets reales.

## Validaciones obligatorias antes de cualquier commit

Ejecutar:

1. `python audit_pav_matinal_data.py`
2. Verificar `/api/diagnostico`
3. Verificar `/api/dashboard`
4. Verificar `/api/vendedor/V3`
5. Verificar visualmente `/portal.html`
6. Verificar visualmente `/index.html`
7. Mostrar `git diff`
8. Mostrar `git status --short`

No hacer commit hasta aprobación explícita.

## Resultado esperado

Al finalizar esta auditoría, debo poder decir:

- de dónde sale cada número;
- qué período representa;
- qué vendedor/zona afecta;
- qué archivo lo genera;
- qué endpoint lo entrega;
- qué variable JS lo muestra;
- si el dato es confiable o no;
- qué hay que corregir;
- qué no debe tocarse.

La prioridad es que Orbit Matinal Peñaflor sea más confiable que Excel, no solo más visual.