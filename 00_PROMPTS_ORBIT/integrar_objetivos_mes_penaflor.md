# Integrar objetivos mensuales Peñaflor — ORBIT PAV

Aplicá la skill orbit-pav-guardian.

## Contexto

El usuario recibió objetivos reales del mes para Peñaflor.

Hay 3 tipos de objetivos:

1. CCC por marca.
2. CCC por canal.
3. Litros por categoría.

Importante:
- En las imágenes de CCC por marca y CCC por canal, ignorar acumulados actuales.
- Usar solamente la columna Objetivo.
- En la imagen de litros por categoría, ignorar Real.
- Usar solamente la columna Objetivo.
- El seguimiento debe realizarse día a día contra ventas reales.

## Objetivos CCC por marca

| Marca | Objetivo CCC |
|---|---:|
| Alaris | 440 |
| Alma Mora | 640 |
| Altares | 190 |
| Dada | 468 |
| Don David | 126 |
| Finca Las Moras | 384 |
| Gordon's Flavors | 124 |
| Los Arboles | 396 |
| Smirnoff Flavors | 318 |
| Smirnoff Ice | 400 |
| Trapiche Reserva | 138 |

## Objetivos CCC por canal

| Canal | Objetivo CCC |
|---|---:|
| Tradicionales | 803 |
| Autoservicios | 145 |
| On Premise | 35 |
| Vinotecas | 20 |
| On Premise Noche | 5 |

## Objetivos litros por categoría

| Categoría | Objetivo litros |
|---|---:|
| Vinos del Año | 19015 |
| Vinos de Guarda | 678 |
| Spirits | 17752 |
| RTD | 9999 |
| Champaña | 686 |
| Cerveza Artesanal | 405 |
| Total | 48535 |

## Nueva fuente propuesta

Crear o proponer archivo:

01_INPUTS/objetivos_mes_penaflor.csv

Columnas:

- mes
- tipo_objetivo
- grupo
- objetivo

Ejemplo:

2026-05,CCC_MARCA,Alaris,440
2026-05,CCC_CANAL,Tradicionales,803
2026-05,LITROS_CATEGORIA,Vinos del Año,19015

No crear todavía sin aprobación.

## Reglas de cálculo

### CCC por marca

CCC real marca = clientes únicos con compra válida de esa marca.

Compra válida = importe_neto > 0.

### CCC por canal

CCC real canal = clientes únicos con compra válida dentro de ese canal.

Compra válida = importe_neto > 0.

### Litros por categoría

Litros reales = suma de litros vendidos por productos pertenecientes a esa categoría.

Validar qué archivo maestro permite mapear:

producto → categoría → litros

## Calendario de objetivos

Para lectura de objetivos y media necesaria:

- NO contar sábados.
- Contar lunes a viernes.
- Excluir feriados.
- Este mes el usuario define:
  - total días venta objetivo = 19
  - días trabajados = 5
  - días restantes = 14

No mezclar con calendario operativo de matinal.

## Media necesaria

media_necesaria = (objetivo - real_acumulado) / días_restantes

Si real_acumulado >= objetivo:

media_necesaria = 0

No puede quedar negativa.

## Lo que debe mostrar el portal

Por cada objetivo:

- objetivo mensual
- real acumulado
- real del día
- avance %
- gap
- media necesaria diaria

Aplicar a:

1. CCC por marca.
2. CCC por canal.
3. Litros por categoría.

## Auditoría requerida antes de implementar

Antes de tocar código, revisar:

1. dónde se calculan hoy CCC por marca
2. dónde se calculan hoy CCC por canal
3. dónde se calculan hoy litros por categoría
4. qué datasets de 04_DATASETS_ORBIT ya tienen esos datos
5. si server_orbit.py ya expone algo parecido
6. si dashboard.jsx o data.js ya muestran algo parecido
7. si ccc_mes puede dejar de ser 0 usando ventas reales
8. qué maestro de productos permite calcular categoría/litros
9. qué archivos habría que tocar
10. qué NO habría que tocar

## Restricciones

No ejecutar REGENERAR_DATOS_ORBIT.bat.
No ejecutar scripts.
No modificar 01_INPUTS todavía.
No crear objetivos_mes_penaflor.csv todavía.
No commitear.
No tocar ventas.csv.
No tocar resultado.xlsx.
No usar mock.
No inventar datos.

## Entregable

Primero mostrar:

1. diagnóstico de fuentes actuales
2. si los reales pueden calcularse con ventas.csv/datasets actuales
3. propuesta de archivo de objetivos
4. fórmula exacta de seguimiento diario
5. cómo mostrarlo en panel gerencial
6. cómo mostrarlo en vendedor
7. archivos que tocarías si apruebo
8. riesgos
9. qué NO tocarías

Esperar aprobación antes de implementar.