# MÓDULO VDA — CLIENTES GANADOS
## Orbit Matinal Peñaflor · 2026-05-12

---

## Diagnóstico del maestro de productos

| Atributo | Valor |
|---|---|
| Archivo | `01_INPUTS/producto activos.xlsx` |
| Header real | Fila 3 (filas 0-2 son metadatos) |
| Total productos | **253** |
| Columnas | bodega, segmento, linea_comercial, codigo_producto, categoria, descripcion_art, lts_x_caja, uxc |
| Productos VDA | **93** (`categoria == "Vinos del año"`) |
| Productos VDG | 75 |
| Espumantes | 21 |
| Whisky | 22 |
| Cerveza Artesanal | 9 |
| Encoding | Problema detectado (ñ/á aparecen como ?) — procesado con normalización unicode |

## Criterio VDA

**Fuente primaria:** `categoria == "Vinos del año"` en `producto activos.xlsx` (cruce por `Codigo` = `código_producto`).
**Fallback:** `Tags == "Vinos del Año"` en Gescom para filas cuyo código no figura en el maestro.
**CCC VDA:** cliente con `ImporteNetoItem > 0` en al menos una línea VDA en el período.
**Litros VDA:** `CantBase × (lts_x_caja / uxc)`.

## Fuentes usadas

| Fuente | Ruta | Filas / Tamaño | Período |
|---|---|---|---|
| Maestro productos | `01_INPUTS/producto activos.xlsx` | 253 productos | — |
| Historial ventas | `02_HISTORY/historial_ventas.csv` | ~129.080 filas / 63 MB | 2024-03-01 a 2026-05-04 |
| Ventas actuales | `01_INPUTS/ventas.csv` | ~962 filas | hasta 2026-05-11 |
| Maestro clientes | `01_INPUTS/clientes.xlsx` | 2.001 clientes | — |

**Deduplicación:** por `NroComprobante||Codigo` al combinar historial + ventas. El historial tiene prioridad.
**Excluidos:** V2 y V5 en todas las métricas.

## Rango de fechas analizado

- Rango VDA total: `2024-03-01` a `2026-05-11`
- **Mes actual:** 2026-05
- **Mes anterior:** 2026-04
- Total filas VDA procesadas: **57,280** (maestro: 57,280 | tags fallback: 0)

## Productos VDA detectados

- **93 productos** con `categoria = "Vinos del año"`
- Bodegas: Finca Las Moras (32), Trapiche (22), Navarro Correas (9), Elementos (9), El Esteco (8), Suter (4), La Liga de los Enologos (4), Mascota (3)
- Top líneas: Alma Mora, Alaris, Dada, ELEMENTOS, Don David

---

## Resumen ejecutivo

| Métrica | Mes actual (2026-05) | Mes anterior (2026-04) | Variación |
|---|---|---|---|
| Clientes VDA | **152** | 727 | -575 |
| Litros VDA | **4,957.5** | 15,288.8 | -10,331.2 |
| Venta Neta VDA | **$20,649,331** | $62,056,558 | $-41,407,227 |
| **Ganados/recuperados** | **37** | — | — |
| **Perdidos** | **612** | — | — |
| **Retenidos** | **115** | — | — |
| **Balance neto** | **-575** | — | — |

> ⚠ El mes actual (2026-05) está **incompleto** (datos hasta 2026-05-11).
> Las métricas de clientes actuales crecerán hasta el cierre del mes.

---

## Clientes ganados o recuperados VDA (top 15 por venta neta)

| Cliente | Razón Social | Vendedor | Localidad | Litros | Venta Neta |
|---|---|---|---|---|---|
| 403 | LOPEZ HNOS S R L | 20 | VILLA DOLORES | 1,462.5 | $5,723,318 |
| 234 | COLLO MAXIMILIANO | 9 | Villa Dolores | 60.8 | $256,872 |
| 181 | WANG XUEQUING | 4 | MORTEROS | 45.0 | $196,316 |
| 30068 | VASCHETTI IGNACIO  | 8 | LAS VARILLAS | 27.0 | $153,611 |
| 8234 | VIGNOLO JOAQUIN IGNACIO | 9 | VILLA LAS ROSAS | 40.5 | $151,678 |
| 1194 | FERRERO FABIO EZEQUIEL | 9 | Los Pozos | 31.5 | $141,319 |
| 776 | GONZALEZ MARIA JUDITH | 9 | Villa Dolores | 27.0 | $126,109 |
| 2714 | BROCHERO MARIANA | 6 | LA PARA | 22.5 | $95,017 |
| 777 | ROMERO EMILCE | 9 | Cruz de Caña | 18.0 | $79,500 |
| 2953 | YAKO DRUGSTORE S.A.S. | 10 | ARROYITO | 13.5 | $70,590 |
| 7857 | JUAN BRINGAS | 9 | LA PAZ | 15.8 | $57,443 |
| 1130 | ALMEIDA JORGE ANTONIO | 9 | La Paz | 9.0 | $49,337 |
| 2162 | MONDINO VANESA PAOLA | 6 | LA PARA | 11.2 | $46,295 |
| 1365 | FENOGLIO MELISA | 6 | Miramar | 13.5 | $44,682 |
| 161 | YANDEN S.A.S | 4 | MORTEROS | 9.0 | $44,166 |


---

## Clientes perdidos VDA (top 15 por venta neta anterior)

| Cliente | Razón Social | Vendedor | Localidad | Litros ant. | Venta Neta ant. |
|---|---|---|---|---|---|
| 938 | CAREGLIO HERMANOS SRL | 20 | San Francisco | 1,588.5 | $5,564,179 |
| 1009 | LOS 3P DISTRIBUCIONES SAS | 6 | Santa Rosa de Río Primero | 1,260.0 | $5,389,151 |
| 15 | BELTRAMO, DUTTO Y DUTTO S.R.L. | 20 | SAN FRANCISCO | 1,138.5 | $4,462,791 |
| 30026 | PEDROTTI DISTRIBUCIONES SOCIEDAD DE | 8 | SAN FRANCISCO | 261.0 | $954,081 |
| 678 | DANGUISE DISTRIBUCIONES S.R.L. | 8 | SAN FRANCISCO | 135.0 | $558,704 |
| 390 | MIRANDA SEBASTIAN LEONARDO | 8 | San Francisco | 112.5 | $457,512 |
| 172 | GIORDANA ENELE GERMAN | 8 | San Francisco | 90.0 | $390,131 |
| 4467 | COOP. AGRIC. CONSUMO | 4 | PORTEA | 99.0 | $377,683 |
| 538 | ZHAO JIAHUI | 8 | San Francisco | 78.8 | $343,942 |
| 340 | ZHUANG BIN  | 9 | YACANTO | 72.0 | $336,220 |
| 8161 | BELLON FABRICIO | 9 | VILLA DOLORES | 72.0 | $294,684 |
| 439 | SUPERVEINTINUEVE S.R.L. | 4 | FREYRE | 63.0 | $279,687 |
| 4457 | FERRARIS HUGO RUBY | 4 | PORTEA | 67.5 | $271,875 |
| 8197 | HUANG JIANPING | 9 | Villa Dolores | 63.0 | $271,220 |
| 21 | BORGIATINO DAVID HERNAN+ | 6 | Río Primero | 54.0 | $222,724 |


---

## Ranking por vendedor

| Vendedor | Nombre | Act. | Ant. | Ganados | Perdidos | Balance | Litros | Venta Neta |
|---|---|---|---|---|---|---|---|---|
| V20 | DEPOSITO | 2 | 5 | +1 | +4 | -3 | 1,467.0 | $5,743,017 |
| V8 | ALVAREZ VANESA  KAFF | 46 | 181 | +4 | +139 | -135 | 1,336.5 | $5,620,124 |
| V9 | SANCHEZ FERNANDO JAVIER | 34 | 67 | +15 | +48 | -33 | 1,026.0 | $4,421,868 |
| V6 | PEYRONEL ANDREA | 26 | 106 | +7 | +87 | -80 | 513.0 | $2,199,530 |
| V4 | GRIBAUDO ANGEL | 10 | 155 | +2 | +147 | -145 | 270.0 | $1,189,474 |
| V10 | ORTEGA MILAGROS DESIREE | 27 | 147 | +2 | +122 | -120 | 275.2 | $1,188,991 |
| V7 | JOFRE GUILLERMO AGUSTIN | 4 | 23 | +3 | +22 | -19 | 51.8 | $214,393 |
| V3 | GAMBINO NADIA | 3 | 43 | +3 | +43 | -40 | 18.0 | $71,933 |


---

## Problemas detectados

1. **Encoding roto en `producto activos.xlsx`** — `ñ`, `á`, `é` aparecen como `?` al leer con Python. El procesamiento usa normalización unicode para comparar categorías correctamente. Recomendación: exportar desde Gescom con UTF-8.

2. **Mes actual incompleto** — Datos VDA del mes actual hasta 2026-05-11. Las métricas de clientes actuales, litros y venta neta son parciales. El balance neto puede cambiar.

3. **Litros = 0 para VDA por Tags** — Los 0 registros identificados por fallback (Tags) no tienen `lts_x_caja` disponible en el maestro -> `litros = 0`. Se puede resolver enriqueciendo el maestro o cruzando por descripción de artículo.

4. **Sin segmento del cliente en la base VDA** — El campo `Ramo` en ventas.csv representa el ramo del cliente tal como aparece en la transacción, no el segmento normalizado del maestro de clientes. Para segmentar correctamente hay que cruzar con `clientes.xlsx`.

---

## Validaciones pendientes

1. Confirmar que `Codigo` en ventas.csv = `codigo_producto` en maestro (cruce 1:1).
2. Revisar los 0 registros VDA por Tags — ¿están todos en el maestro bajo otro código?
3. Validar litros calculados para un vendedor muestra contra registro físico.
4. Cruzar marcas VDA del maestro contra `MAP_11T_FINE` en `orbit_matinal_v42.py` — verificar coherencia.
5. Confirmar el criterio de "cliente recuperado" vs "cliente ganado" (¿tiene historia VDA anterior al mes anterior?).

---

## Próximos pasos

1. Integrar `mod_vda_ventas_base.csv` en `orbit_matinal_v42.py` como módulo oficial del pipeline diario.
2. Agregar hoja `mod_vda` en `MATINAL_PENA_V42.xlsx` para que `datasets_orbit.py` la exporte automáticamente.
3. Exponer `/api/vda` en `server_orbit.py` sirviendo `vda_clientes_ganados.json`.
4. Integrar panel VDA en el portal gerencial (pantalla de evolución de clientes).
5. Resolver encoding de `producto activos.xlsx` — exportar desde Gescom con UTF-8.

---

## Archivos generados por este módulo

| Archivo | Filas/Contenido | Descripción |
|---|---|---|
| `04_DATASETS_ORBIT/diagnostico_productos_activos.md` | — | Diagnóstico completo del maestro de productos |
| `04_DATASETS_ORBIT/mod_vda_productos.csv` | 93 | Productos VDA confirmados con litros/unidad |
| `04_DATASETS_ORBIT/mod_vda_productos_revision_necesaria.csv` | 160 | Productos no-VDA (referencia) |
| `04_DATASETS_ORBIT/mod_vda_ventas_base.csv` | 57,280 | Todas las ventas VDA históricas + actuales |
| `04_DATASETS_ORBIT/mod_vda_resumen_mensual.csv` | 1 | Resumen mensual VDA |
| `04_DATASETS_ORBIT/mod_vda_clientes_detalle.csv` | 764 | Detalle por cliente con estado VDA |
| `04_DATASETS_ORBIT/mod_vda_ranking_vendedor.csv` | 8 | Ranking por vendedor |
| `06_APP_DATA/vda_clientes_ganados.json` | — | JSON para portal gerencial futuro |
| `MODULO_VDA_CLIENTES_GANADOS_2026-05-12.md` | — | Este reporte |

*Generado por `_tmp_auditoria_vda.py` · Sin modificación de portal, Flask, AppScript ni código principal.*
