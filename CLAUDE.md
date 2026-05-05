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
