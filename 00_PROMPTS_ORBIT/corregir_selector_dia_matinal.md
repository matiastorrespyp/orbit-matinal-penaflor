# Corregir selector de día / fecha de matinal — ORBIT PAV

Aplicá la skill orbit-pav-guardian.

## Problema detectado

Todavía no está lograda la posibilidad real de seleccionar el día de matinal.

Caso real:
Por una cuestión de tiempo, el usuario descargó hoy la venta del sábado y la pegó hoy antes de la matinal.

El portal mostró:
- “Matinal martes”

Pero en realidad debía mostrar:
- “Matinal lunes”

Esto demuestra que el portal probablemente está calculando la matinal desde la fecha actual del sistema o desde “próximo día automático”, en lugar de respetar la fecha operativa real de la matinal que el usuario necesita ver.

## Objetivo

Implementar o diseñar correctamente la lógica de selección de día operativo / fecha de matinal.

El usuario debe poder seleccionar explícitamente qué matinal quiere ver.

Ejemplos:
- Matinal lunes viendo resultados del sábado.
- Matinal sábado viendo resultados del viernes.
- Matinal martes si efectivamente corresponde.
- Matinal de una fecha específica si el usuario carga datos atrasados.

## Conceptos obligatorios

Separar claramente:

### 1. fecha_datos
Fecha máxima de ventas disponibles en los datos cargados.
Ejemplo:
- si se cargó venta del sábado, fecha_datos = sábado.

### 2. fecha_corte
Fecha hasta la cual se consideran ventas reales.
Normalmente coincide con fecha_datos.

### 3. fecha_matinal
Fecha de la reunión matinal que se quiere preparar.
Ejemplo:
- si el lunes a la mañana se cargó venta del sábado, fecha_matinal = lunes.

### 4. dia_operativo
Día/zona que se quiere trabajar en la matinal.
Ejemplo:
- LU, MA, MI, JU, VI, SA.

### 5. modo_selector
Puede ser:
- automático sugerido
- manual seleccionado por usuario

## Regla funcional

El portal NO debe forzar “mañana” desde la fecha del sistema.

Debe permitir:

1. sugerir una fecha_matinal automáticamente,
2. pero permitir que el usuario la cambie manualmente.

## Regla de sugerencia automática

La sugerencia automática debe ser razonable, pero nunca obligatoria.

Propuesta:
- detectar fecha_datos máxima en ventas reales
- sugerir como fecha_matinal el próximo día operativo posterior a fecha_datos
- si fecha_datos es sábado, sugerir lunes
- si fecha_datos es viernes, sugerir sábado solo si existen vendedores con ruta sábado o si el usuario elige sábado
- si no corresponde sábado general, sugerir lunes

Pero el usuario siempre debe poder seleccionar manualmente:
- fecha matinal
- día operativo
- vendedor si aplica

## Sábado

Importante:

Hay dos reglas distintas:

### A. Objetivos / media necesaria
Los sábados NO cuentan para media necesaria ni lectura de objetivo mensual.

### B. Operación matinal
El sábado SÍ existe operativamente para los vendedores que trabajan sábado.

Por lo tanto:
- debe poder existir Matinal sábado,
- pero solo con vendedores/rutas que trabajan sábado,
- y no debe distorsionar media necesaria general.

## Qué debe mostrar el portal

En el encabezado del portal o panel debe mostrarse claramente:

- Fecha datos: YYYY-MM-DD
- Fecha corte: YYYY-MM-DD
- Matinal seleccionada: YYYY-MM-DD
- Día operativo: LU/MA/MI/JU/VI/SA
- Modo: automático o manual

Si el usuario selecciona manualmente, mostrar:
- “Modo manual”

Si se usa sugerencia automática, mostrar:
- “Modo automático sugerido”

## Selector requerido

Agregar o revisar selector para:

1. fecha_matinal
2. día operativo
3. vendedor
4. vista general / vendedor

El selector no debe romper endpoints existentes.

## Auditoría requerida antes de tocar código

Antes de implementar, auditar:

1. Dónde se calcula hoy “Matinal martes” o el título de matinal.
2. Si sale de server_orbit.py, data.js, dashboard.jsx o index.html.
3. Qué endpoint devuelve fecha/día actual.
4. Si /api/diagnostico tiene calendario suficiente.
5. Si /api/dashboard recibe o ignora parámetros de fecha/día.
6. Si /api/clientes filtra por día operativo o devuelve todo.
7. Si hay soporte actual para query params:
   - ?fecha_matinal=
   - ?dia=
   - ?vendedor=
8. Si el frontend tiene estado de selección de día.
9. Qué archivos hay que tocar mínimo.

## Diseño técnico deseado

Proponer un contrato simple para endpoints.

Ejemplo:

GET /api/diagnostico?fecha_matinal=2026-05-11&dia=LU

Debe devolver:

{
  "fecha_datos": "...",
  "fecha_corte": "...",
  "fecha_matinal": "2026-05-11",
  "dia_operativo": "LU",
  "modo_fecha": "manual",
  "calendario_objetivos": {...},
  "calendario_operativo": {...}
}

GET /api/dashboard?fecha_matinal=2026-05-11&dia=LU

Debe devolver datos consistentes para esa matinal.

GET /api/clientes?fecha_matinal=2026-05-11&dia=LU&vendedor=V10

Debe devolver clientes correspondientes a esa matinal/día/vendedor.

No implementar este contrato sin auditar primero qué existe.

## Restricciones

No ejecutar REGENERAR_DATOS_ORBIT.bat.
No tocar 01_INPUTS.
No modificar ventas.csv.
No modificar resultado.xlsx.
No commitear.
No usar mock.
No inventar fechas.
No romper el portal actual.

## Entregable fase 1

Primero mostrar:

1. diagnóstico de dónde nace “Matinal martes”
2. archivos involucrados
3. endpoints involucrados
4. si hoy existe selector real de día o solo lógica automática
5. propuesta técnica para selector manual
6. cómo manejar Matinal lunes con ventas del sábado
7. cómo manejar Matinal sábado
8. cómo separar calendario operativo de calendario de objetivos
9. riesgos
10. archivos que tocarías si apruebo implementación

No implementar todavía.
Esperar aprobación.