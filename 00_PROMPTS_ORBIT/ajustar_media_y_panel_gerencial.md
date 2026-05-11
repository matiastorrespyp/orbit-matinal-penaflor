# Ajustar media necesaria y panel gerencial ORBIT PAV

Aplicá la skill orbit-pav-guardian.

Vamos a trabajar un cambio funcional importante del proyecto Matinal Peñaflor.

## Contexto real de operación

Yo todos los días voy pegando la información nueva del día, como si ya estuviera trabajando con el proyecto funcionando. Por eso los reales del día se van generando y actualizando.

## Cambio funcional 1 — media necesaria / lectura de objetivo

A partir de ahora, para la lectura comercial de objetivo, media necesaria, ritmo y avance, voy a sacar de la medición la venta de los sábados.

Motivo:
- solo 2 vendedores venden el sábado,
- venden muy poco,
- el objetivo se estaba dividiendo para todos de la misma forma contando sábados,
- eso distorsiona la media necesaria.

### Nueva regla

Separar 2 calendarios distintos:

#### A. Calendario de objetivos / lectura comercial
Se usa para:
- media necesaria
- ritmo
- tendencia
- lectura de avance contra objetivo

Regla:
- contar solo días de venta de lunes a viernes
- excluir feriados
- NO contar sábados

Para este mes:
- total de días de venta = 19
- días ya trabajados = 5
- días restantes = 14

Quiero que este criterio quede bien implementado para la lectura comercial.

#### B. Calendario operativo / matinal
Se usa para:
- planificación del día siguiente
- matinal del sábado
- clientes sin compra
- CCC no compradores
- titulares / cobertura del día
- planificación de los vendedores que sí trabajan sábado

Regla:
- el sábado sigue existiendo operativamente
- necesito poder tener la matinal del sábado viendo los resultados del viernes
- esa matinal del sábado debe aplicar solo a los vendedores que efectivamente venden el sábado
- debe incluir sus ccc, no compradores, planificación y todo lo necesario para ese día

### Importante

No mezclar ambos conceptos:
- una cosa es la media necesaria del objetivo mensual
- otra cosa es la operación real del sábado para los pocos vendedores que sí trabajan

## Cambio funcional 2 — panel gerencial de avance de objetivos

No me queda claro si hoy el panel está mostrando bien el avance / alcance. En la vista gerencial actual veo porcentajes, pero quiero que quede mucho más preciso y explícito.

Adjunto referencia visual del heatmap actual de vendedores x indicadores.

### Lo que quiero

En la parte gerencial de avance de objetivos, por vendedor, quiero ver claramente:

- Objetivo
- Real acumulado
- Media necesaria
- Avance %

Y que quede claro qué representa cada cosa.

### Definiciones deseadas

Para cada vendedor:

- Objetivo = objetivo mensual del vendedor
- Real acumulado = venta acumulada real del vendedor
- Avance % = real acumulado / objetivo mensual * 100
- Media necesaria = (objetivo mensual - real acumulado) / días de venta restantes según el calendario comercial SIN sábados

Si el gap es negativo o ya superó objetivo:
- media necesaria no debe quedar negativa
- resolver con criterio comercial claro (0 o equivalente razonable)
- explicarlo

Si días restantes = 0:
- no romper el cálculo
- resolver de forma robusta

## Qué quiero ver en el panel

### Opción mínima obligatoria
En el heatmap o en la sección gerencial, que cada vendedor tenga claramente visibles:

- Avance %
- Obj
- Real
- Media necesaria

No quiero un porcentaje ambiguo sin contexto.

### Mejora deseada
Si hace falta:
- cambiar el título "AVANCE" por algo más explícito como "AVANCE %"
- debajo del porcentaje mostrar:
  - Obj: $...
  - Real: $...
  - Media: $.../día

Si existe otra sección mejor dentro del panel para mostrarlo, también sirve, pero debe quedar claro visualmente y ser útil para gerencia.

## Reglas comerciales que siguen vigentes

- excluir siempre V2 y V5
- vendedores activos esperados: V3, V4, V6, V7, V8, V9, V10
- V3 es Nadia Gambino
- V3 no trabaja Autoservicio
- CCC = cliente con compra válida
- compra válida = importe neto > 0
- sábados NO cuentan para media necesaria
- sábados SÍ pueden existir para la operación matinal de los vendedores que sí trabajan ese día

## Tarea

Necesito que hagas esto en 2 fases.

### Fase 1 — auditoría y diseño mínimo
Identificar:
1. dónde se calcula hoy la media necesaria / avance / ritmo / tendencia
2. qué archivos afectan esa lógica
3. qué archivos afectan el panel gerencial
4. cómo se está calculando hoy el porcentaje que aparece en el panel
5. qué cambios mínimos hay que hacer para:
   - separar calendario comercial y calendario operativo
   - excluir sábados de media necesaria
   - mantener matinal del sábado para quienes correspondan
   - mostrar obj / real / media / avance de forma clara

### Fase 2 — implementación
Después de explicar el plan, implementar el cambio con el menor impacto posible y sin romper lo que ya funciona.

## Restricciones

No tocar:
- 01_INPUTS/
- REGENERAR_DATOS_ORBIT.bat
- CHANGELOG_AI.md
- NEXT_TASK.md
- historial ni outputs generados, salvo que sea estrictamente necesario y me lo expliques antes

No usar mock.
No inventar datos.
No commitear todavía.

## Entregable ahora

Primero mostrame, sin commitear:

1. diagnóstico de cómo se calcula hoy
2. archivos que tocarías
3. propuesta de cambio
4. fórmula exacta para media necesaria nueva
5. cómo resolverías la matinal del sábado
6. cómo quedaría visualmente la parte gerencial
7. riesgos
8. qué NO tocarías

Después esperá mi aprobación antes de implementar.