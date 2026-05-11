# Piloto de planificación diaria por vendedor — ORBIT PAV

Aplicá la skill orbit-pav-guardian.

Antes de implementar cambios grandes en media necesaria, panel gerencial o automatización, quiero hacer una prueba piloto real de planificación diaria con un vendedor.

## Objetivo del piloto

Validar el flujo completo:

Vendedor envía planificación → ORBIT la recibe → ORBIT la guarda → al día siguiente se compara contra el real logrado → el portal muestra Plan vs Real.

No quiero todavía una implementación masiva.
Quiero una prueba controlada, con 1 vendedor, para validar el circuito.

## Contexto

Todos los días voy pegando información nueva del día en los inputs del proyecto, como si el sistema ya estuviera funcionando.

Necesito comprobar que si un vendedor planifica hoy para mañana, al día siguiente el portal pueda decir:

- qué planificó,
- qué vendió realmente,
- cuántos CCC planificó,
- cuántos CCC reales hizo,
- qué clientes planificados compraron,
- qué clientes planificados no compraron,
- diferencia entre plan y real,
- cumplimiento de planificación.

## Alcance del piloto

Trabajar con 1 vendedor.

No definir todavía todos los vendedores.
No hacer integración final con Google Form/AppSheet todavía si no hace falta.
Primero puede ser una fuente simple y controlada, por ejemplo:

- CSV manual,
- Excel manual,
- o archivo dentro de 01_INPUTS o carpeta equivalente.

Pero antes de decidir la ubicación, auditar si ya existe:

- /api/planificacion
- función de planificación en server_orbit.py
- dataset de planificación
- archivo planificacion existente
- endpoint o estructura previa.

## Preguntas que debe responder la auditoría

1. ¿Existe actualmente /api/planificacion?
2. ¿Qué devuelve?
3. ¿De dónde intenta leer datos?
4. ¿Existe algún archivo de planificación?
5. ¿Hay estructura previa para planificación diaria?
6. ¿Hay columnas esperadas?
7. ¿Qué falta para que funcione?
8. ¿Cómo conviene hacer el piloto sin romper el portal?

## Diseño mínimo esperado

Proponer un contrato de datos mínimo para el piloto.

Ejemplo de columnas posibles:

- fecha_carga
- fecha_planificada
- vendedor_codigo
- vendedor_nombre
- dia_operativo
- zona
- venta_planificada
- ccc_planificados
- clientes_planificados
- observaciones
- usuario_carga
- timestamp_carga

Si hace falta trabajar a nivel cliente, proponer otro archivo separado:

- fecha_planificada
- vendedor_codigo
- cliente_codigo
- cliente_nombre
- objetivo_cliente
- observacion_cliente
- prioridad

No implementar todavía sin aprobación.

## Comparación contra real

Definir cómo se va a calcular el real al día siguiente:

- real_venta = venta real del vendedor en la fecha planificada
- real_ccc = clientes únicos con compra válida
- compra válida = importe neto > 0
- clientes_planificados_con_compra
- clientes_planificados_sin_compra
- cumplimiento_venta = real_venta / venta_planificada
- cumplimiento_ccc = real_ccc / ccc_planificados

Respetar reglas ORBIT:

- excluir V2 y V5
- V3 es Nadia Gambino
- V3 no trabaja Autoservicio
- CCC = cliente con compra válida
- compra válida = importe neto > 0
- no usar mock data
- si falta fuente, mostrar "Dato no disponible"

## Visualización deseada

Proponer cómo debería verse en el portal.

Para vendedor:

- Planificado para el día
- Real logrado
- Diferencia
- Cumplimiento %
- CCC planificados vs CCC reales
- Clientes planificados que compraron
- Clientes planificados sin compra

Para gerencia:

- tabla por vendedor
- plan vs real
- cumplimiento
- alertas de desvío
- observaciones

## Restricciones

No ejecutar REGENERAR_DATOS_ORBIT.bat.
No modificar 01_INPUTS sin aprobación.
No tocar ventas.csv ni resultado.xlsx.
No commitear.
No crear integración definitiva todavía.
No hacer diseño visual antes de cerrar contrato de datos.
No inventar datos.
No usar mock.

## Entregable de esta fase

Solo auditoría y propuesta.

Mostrar:

1. si existe /api/planificacion y cómo funciona hoy
2. archivos actuales relacionados con planificación
3. propuesta de contrato de datos para piloto
4. ubicación recomendada del archivo piloto
5. fórmula de comparación Plan vs Real
6. cómo se mostraría en portal vendedor
7. cómo se mostraría en portal gerencial
8. riesgos
9. archivos que tocarías si apruebo implementación
10. qué NO tocarías

No implementar todavía.
Esperar aprobación.