# Crear Skill ORBIT PAV Guardian

Necesito reemplazar el contenido actual de:

.claude/skills/orbit-pav-guardian/SKILL.md

Ese archivo existe, pero su contenido actual es inválido porque quedó guardado texto de chat.

No crear archivos nuevos.
No tocar código.
No tocar 01_INPUTS.
No commitear.

## Objetivo

Crear una skill real para el proyecto ORBIT Matinal Peñaflor.

La skill debe funcionar como guardián técnico y funcional del proyecto.

## Contenido requerido para SKILL.md

Usar este frontmatter:

---
name: orbit-pav-guardian
description: Guardián técnico y funcional para ORBIT Matinal Peñaflor. Usar en tareas de portal PAV, server_orbit.py, datasets, BATs, endpoints, dashboard, vendedores, CCC, 11 Titulares, gastos acción, planificación y regeneración de datos.
---

# ORBIT PAV Guardian

## Criterio de éxito

El trabajo solo cuenta como avance real si:

- el portal lo muestra,
- el endpoint lo devuelve,
- la fuente lo respalda,
- el git diff es controlado,
- el usuario puede comprobarlo.

## Reglas comerciales

- Excluir siempre V2 y V5.
- Vendedores activos esperados: V3, V4, V6, V7, V8, V9, V10.
- V3 es Nadia Gambino.
- V3 no trabaja Autoservicio.
- CCC = cliente con compra válida.
- Compra válida = importe neto > 0.
- Días comerciales = lunes a sábado.
- Domingos no cuentan.
- Feriados salen de feriados.csv.
- Sábados cuentan.
- No hardcodear feriados.

## Reglas técnicas

- No usar mock data.
- No inventar datos.
- Si falta fuente real, mostrar "Dato no disponible".
- No dejar 0 cuando significa falta de fuente.
- No commitear 01_INPUTS salvo orden explícita.
- No commitear temporales, __pycache__ ni .pyc.
- No tocar diseño antes de validar datos.
- No cerrar OK sin endpoint o validación visible.
- No crear archivos "final" como falsa solución.

## Antes de modificar

Antes de cambiar cualquier archivo, indicar:

1. archivo a tocar,
2. motivo,
3. fuente real del dato,
4. endpoint afectado,
5. riesgo,
6. qué NO se toca.

## Después de modificar

Después de cambiar cualquier archivo, mostrar:

1. endpoint validado,
2. comparación fuente vs backend,
3. comparación backend vs portal si aplica,
4. git diff,
5. git status --short,
6. archivos tocados.

No commitear sin aprobación explícita.

## BATs

Antes de crear o modificar BATs:

- auditar scripts reales,
- validar inputs,
- validar outputs,
- crear backup antes de sobrescribir,
- crear log timestamped,
- no mezclar launcher con regenerador salvo decisión explícita.

Para regeneración de datos:

- backupear 03_OUTPUTS/MATINAL_PENA_V42.xlsx,
- backupear 02_HISTORY/historial_ventas_cliente.csv,
- backupear 04_DATASETS_ORBIT/*.csv,
- usar 99_BACKUPS_ORBIT/YYYYMMDD_HHMMSS/,
- usar 99_LOGS_ORBIT/regenerar_datos_YYYYMMDD_HHMMSS.log,
- confirmar si el historial es idempotente antes de ejecutar,
- no abrir portal si el BAT solo regenera.

## Commits

Antes de commit:

1. mostrar git diff,
2. mostrar git status --short,
3. listar archivos a commitear,
4. confirmar exclusión de 01_INPUTS,
5. hacer commit atómico,
6. mostrar git show --stat HEAD.

## Pendientes actuales

- ccc_mes: resolver fuente real o mostrar "Dato no disponible".
- Bloque A: clientes.xlsx requiere datos ERP externos.
- Automatización pipeline: BAT separado con backup y log.
- Validación visible: portal debe mostrar fecha, fuente, versión y estado.

## Tarea

Reemplazar el contenido de:

.claude/skills/orbit-pav-guardian/SKILL.md

con la skill real anterior.

Después mostrar:

1. contenido completo final del SKILL.md,
2. git diff -- .claude/skills/orbit-pav-guardian/SKILL.md,
3. git status --short,
4. confirmación de que solo cambió ese archivo,
5. cómo confirmar que Claude Code detecta la skill.

No commitear todavía.