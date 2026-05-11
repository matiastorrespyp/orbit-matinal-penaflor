# Validar ventas 2026-05-09 antes de ejecutar BAT

Aplicá la skill orbit-pav-guardian.

No ejecutes REGENERAR_DATOS_ORBIT.bat.
No ejecutes scripts de pipeline.
No modifiques archivos.
No hagas git add.
No commitees.
No toques 01_INPUTS.

## Contexto

El diagnóstico detectó que:

- 02_HISTORY/historial_ventas_cliente.csv tiene +485 líneas nuevas.
- Las fechas agregadas detectadas incluyen 2026-05-04 y 2026-05-09.
- En 2026-05-09 aparecen patrones sospechosos:
  - mismos productos,
  - mismas cantidades,
  - mismos importes exactos,
  - repetidos para muchos clientes distintos.
- El BAT REGENERAR_DATOS_ORBIT.bat NO fue ejecutado.
- No existen 99_LOGS_ORBIT ni 99_BACKUPS_ORBIT.
- Por lo tanto, el historial pudo contaminarse por una ejecución manual previa del motor legacy.
- Pero antes de revertir historial, hay que validar si la fuente 01_INPUTS/ventas.csv ya contiene esa contaminación.

## Objetivo

Determinar si 01_INPUTS/ventas.csv tiene datos contaminados para 2026-05-09.

No quiero revertir historial todavía si ventas.csv está mal, porque el BAT volvería a generar el mismo problema.

## Tareas de solo lectura

### 1. Confirmar columnas relevantes de ventas.csv

Detectar columnas reales para:

- fecha
- cliente_codigo o cliente_id
- cliente_nombre
- vendedor_codigo
- vendedor_nombre
- producto/articulo
- marca
- cantidad
- importe_neto
- descuento

Mostrar nombres exactos de columnas encontrados.

### 2. Filtrar ventas del 2026-05-09

Mostrar:

- cantidad total de líneas de venta del 2026-05-09
- vendedores presentes
- cantidad de clientes distintos
- cantidad de productos distintos
- total importe_neto
- total cantidad/botellas si aplica

### 3. Buscar patrón sospechoso

Validar si en ventas.csv existen múltiples clientes distintos con estas combinaciones exactas o similares:

- SMIRNOFF RASPBERRY DO 6X700 | 90 unidades | $535.539,78
- SMIRNOFF GREEN APPLE DO 6X700 | 30 unidades | $178.513,26
- ALMA MORA MALBEC 6X750 | 60 unidades | $196.315,83
- JW RED 12X750 UK | 3 unidades | $56.393,10

Mostrar:

- clientes afectados
- vendedores afectados
- cantidad de repeticiones
- si los importes coinciden exactamente
- si las cantidades coinciden exactamente

### 4. Vendedor 20 / DEPOSITO

Validar si en ventas.csv del 2026-05-09 aparece:

- vendedor_codigo 20
- vendedor_nombre DEPOSITO
- clientes asociados
- importe total
- cantidad de líneas

Aclarar:
- si vendedor 20 pertenece a datos no comerciales,
- si debe excluirse del portal comercial,
- si puede estar en historial bruto pero no en KPIs.

### 5. Conclusión

Responder con una tabla:

Archivo | Hallazgo | Riesgo | Recomendación

Incluir:

- 01_INPUTS/ventas.csv
- 02_HISTORY/historial_ventas_cliente.csv
- LEGACY/__pycache__/orbit_matinal_v42.cpython-314.pyc

### 6. Decisión recomendada

Proponer una de estas opciones:

A. ventas.csv está contaminado  
- No ejecutar BAT.
- No revertir todavía sin definir corrección de fuente.
- Pedir al usuario recargar ventas.csv limpio.

B. ventas.csv está bien y el problema está solo en historial  
- Revertir 02_HISTORY/historial_ventas_cliente.csv a HEAD.
- Luego ejecutar BAT controlado.

C. No hay evidencia suficiente  
- Mostrar qué falta revisar.

## Restricciones

No modificar archivos.
No ejecutar BAT.
No ejecutar scripts de pipeline.
No revertir historial.
No hacer git rm.
No hacer git add.
No hacer commit.
No tocar 01_INPUTS.

Esperar aprobación.