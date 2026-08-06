# ORBIT MATINAL PEÑAFLOR - CONTRATO DE TRABAJO PARA CLAUDE CODE

## Objetivo del proyecto

ORBIT Matinal Peñaflor debe procesar datos reales de ventas, clientes, objetivos y productos para generar información confiable para la reunión matinal, el seguimiento de vendedores y el portal gerencial.

El sistema debe poder generar:
- Datos reales para portal/app.
- PDFs o HTML para vendedores.
- Vista gerencial.
- Alertas comerciales.
- Seguimiento de CCC, cobertura, 11 Titulares, objetivos, tendencia, avance y planificación.

## Regla principal

No inventar datos.
No usar datos mock.
No maquillar visualmente información incorrecta.
Primero precisión de datos, después diseño.

## Reglas comerciales Peñaflor

- Vendedores activos Peñaflor: V3, V4, V6, V7, V8, V9, V10.
- Excluir siempre V2 y V5 de todos los reportes Peñaflor.
- V20 = DEPOSITO / venta directa / no es vendedor de ruta Peñaflor.

  **REGLA DEFINITIVA (2026-08-05):** V20/Depósito no es vendedor activo ni posee cartera.
  Sus ventas válidas se incluyen únicamente en los totales empresariales de 11 Titulares
  y se excluyen de rankings e indicadores individuales.

  - Hay DOS UNIVERSOS y no son el mismo filtro:
    - **EMPRESA**: todo el total comercial de la distribuidora, INCLUIDO el Depósito.
      Es el número que se compara contra el objetivo de empresa y contra el proveedor.
    - **VENDEDORES**: sólo vendedores de ruta. Alimenta rankings, cartera, selectores,
      cumplimiento individual y cualquier promedio entre vendedores.
  - V20 sigue EXCLUIDO de todas las métricas con objetivo: avance vs objetivo,
    Incentivo Club FARO, Planes AS, dashboard de vendedores. No tiene cartera asignada
    en el maestro de clientes ni login propio.
  - V20 NO debe: aparecer en rankings o selectores, recibir cartera, generar cumplimiento
    individual, figurar como vendedor activo, alterar promedios entre vendedores, ni
    generar filas individuales en reportes comerciales.
  - En 11 Titulares el Depósito **suma al total de empresa** y se informa aparte
    (`cubiertos_deposito` / `con_deposito`), nunca como línea de vendedor. En Sell Out,
    Innovaciones y Cobertura se mantiene la línea informativa "V20 Depósito"
    (solo logrado, sin objetivo).
  - Códigos del padrón que son Depósito / venta directa: **V1** (bucket `deposito`) y
    **V20** (código con el que factura). Un cliente sin `codven` en el padrón recibe el
    mismo trato: cuenta para EMPRESA, no es de nadie.
  - Implementación única: `motor_11t.VENDEDORES_BAJA` (V2/V5, fuera de todo) y
    `motor_11t.VENDEDORES_SIN_CARTERA` (V1/V20). Cada fila del detalle trae
    `cuenta_vendedor`. No duplicar estas listas en otros módulos.
  - No hay doble conteo posible: el padrón deja una sola fila por cliente, así que vale
    `cubiertos_empresa = cubiertos_vendedores + cubiertos_deposito` (testeado).
  - Para los bloques depósito NO se filtra por Empresa: el depósito factura parte de su
    venta directa vía P&P Logística pero es la misma entidad física V20.
- V3 es Nadia Gambino.
- V3 no trabaja Autoservicios.
- No calcular objetivos, penalizaciones ni métricas de Autoservicio para V3.
- CCC = cliente con compra con Importe Neto > 0.
- Cobertura Tradicional / Almacén / Kiosco = mínimo 3 botellas.
- Cobertura Autoservicio = mínimo 6 botellas.
- Cobertura On Premise / Vinoteca = mínimo 6 botellas.
- Avance % correcto = Tendencia / Objetivo * 100.
- Real del día debe salir de diferencia entre snapshot anterior y snapshot actual.

## Fuentes esperadas

- 01_INPUTS/ventas.csv = ventas reales.
- 01_INPUTS/clientes.xlsx = maestro de clientes.
- 01_INPUTS/resultado.xlsx = objetivos, acumulado, tendencia y avance.
- 09_CONFIG/vendedores_activos.csv = vendedores activos.
- 09_CONFIG/feriados.csv = calendario comercial si aplica.
- 06_APP_DATA/orbit_portal_data.json = salida principal para portal si está vigente.

## Archivos peligrosos o a revisar

- 01_INPUTS/_NO_USAR_ventas_diarias.csv
- 01_INPUTS/_NO_USAR_avance_objetivos.xlsx
- PAV MATINAL PE_A FLOR/data.js
- PAV MATINAL PE_A FLOR/data.js.mock.bak
- PAV MATINAL PE_A FLOR/data_provider.js.bak
- app_matinal_penaflor.py
- server_orbit.py
- run_orbit.py
- app_publish.py

## Reglas técnicas

- Mantener compatibilidad con Windows.
- No depender de posiciones fijas de columnas.
- Detectar encoding y separador en CSV.
- Usar rutas con pathlib.
- Registrar logs claros.
- No crear archivos tipo final, final2, nuevo, corregido, fix, v2, v3.
- No duplicar fuentes de datos.
- Antes de tocar código, explicar qué archivo se va a modificar y por qué.
- Después de tocar código, ejecutar validación real.
- Todo cambio debe registrarse en CHANGELOG_AI.md.
- Toda próxima tarea debe quedar en NEXT_TASK.md.

## Flujo obligatorio

1. Inspeccionar estructura.
2. Identificar fuente real.
3. Identificar consumidor.
4. Detectar causa raíz.
5. Proponer cambio mínimo.
6. Modificar solo lo necesario.
7. Ejecutar prueba o comando de validación.
8. Mostrar resumen de diff.
9. Actualizar CHANGELOG_AI.md.
10. Actualizar NEXT_TASK.md.

## Problemas actuales a resolver

- El portal muestra días corridos/hábiles incorrectos.
- Las métricas del portal no coinciden con los CSV reales.
- Puede estar tomando datos mock.
- Puede haber conflicto entre data.js, window.ORBIT_DATA, Flask, React o App Script.
- Puede haber duplicidad entre ventas.csv y ventas_diarias.
- Puede haber duplicidad entre resultado.xlsx y avance_objetivos.xlsx.
- Puede haber vendedores, zonas o localidades incompletas.
- El diseño no debe corregirse hasta que los datos sean correctos.

## Orden de prioridad

1. Datos reales.
2. Fuente de verdad única.
3. Cálculos correctos.
4. Validación.
5. Portal.
6. PDFs.
7. Automatización diaria.
8. Diseño visual.
