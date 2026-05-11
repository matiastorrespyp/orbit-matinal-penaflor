# Aceptar ventas Gescom como fuente real y limpiar estado técnico

Aplicá la skill orbit-pav-guardian.

## Corrección de criterio funcional

Todo lo que el usuario pega en:

01_INPUTS/ventas.csv

sale de Gescom y debe considerarse fuente real.

Por lo tanto, el patrón detectado el 09/05/2026 NO debe tratarse como “contaminación” ni como motivo para bloquear el pipeline.

Nuevo criterio:

- ventas.csv = fuente real de Gescom.
- Si hay comprobantes correlativos con mismo mix, mismas cantidades e importes, eso se registra como venta real atípica.
- No excluir automáticamente.
- No pedir export limpio.
- No frenar el BAT por ese motivo.
- Puede marcarse como alerta gerencial de patrón atípico, pero entra al seguimiento comercial.

## Diagnóstico anterior reinterpretado

Antes se interpretó:

“ventas.csv contaminado”

Ahora debe reinterpretarse como:

“ventas.csv real con patrón comercial atípico detectado en Gescom”

Ese patrón debe poder ser alertado, pero no eliminado ni censurado.

## Decisión funcional

1. Aceptar 01_INPUTS/ventas.csv como fuente real.
2. No modificar ventas.csv.
3. No excluir las líneas del 09/05/2026.
4. No pedir export limpio.
5. No bloquear el pipeline por esa venta.
6. Registrar el patrón como alerta potencial, no como error.

## Estado técnico actual a resolver

Hay dos temas técnicos separados:

### A. LEGACY/__pycache__/orbit_matinal_v42.cpython-314.pyc

Este archivo está trackeado por Git aunque .gitignore ya ignora __pycache__/ y *.pyc.

Acción propuesta:
- desindexarlo con git rm --cached,
- no borrar el archivo local,
- hacer commit separado de limpieza técnica.

No ejecutar todavía sin aprobación.

### B. 02_HISTORY/historial_ventas_cliente.csv

Este archivo fue modificado por una ejecución manual anterior del motor legacy, sin backup/log del BAT.

Como ahora sabemos que ventas.csv es fuente real, el historial debe regenerarse de forma controlada desde esa fuente real.

Acción propuesta:
- revertir historial a HEAD antes de ejecutar el BAT controlado,
- luego ejecutar REGENERAR_DATOS_ORBIT.bat,
- así el historial queda regenerado desde ventas.csv real, pero con backup, log y validación.

Importante:
Revertir historial NO significa descartar ventas reales.
Significa quitar una regeneración previa sin trazabilidad para que el BAT lo regenere correctamente.

## Restricciones

No ejecutar REGENERAR_DATOS_ORBIT.bat todavía.
No ejecutar scripts.
No tocar 01_INPUTS.
No modificar ventas.csv.
No modificar resultado.xlsx.
No commitear sin aprobación.
No hacer git rm sin aprobación.
No hacer git checkout/restore sin aprobación.
No borrar archivos.

## Tarea ahora

Primero mostrar un plan claro antes de tocar nada:

1. Confirmar que ventas.csv queda aceptado como fuente real de Gescom.
2. Reinterpretar el diagnóstico anterior como “patrón real atípico”, no contaminación.
3. Confirmar que esas ventas entrarán al seguimiento comercial.
4. Confirmar que el patrón podrá ser alerta gerencial futura.
5. Proponer secuencia exacta para limpiar:
   - .pyc trackeado,
   - historial modificado sin trazabilidad.
6. Mostrar comandos que ejecutarías, pero NO ejecutarlos todavía.
7. Mostrar git status --short.
8. Confirmar que 01_INPUTS no se toca.

## Entregable

Mostrar:

- decisión funcional actualizada,
- plan técnico,
- comandos propuestos,
- riesgos,
- qué NO se toca,
- qué requiere aprobación.

Esperar aprobación antes de cualquier acción.