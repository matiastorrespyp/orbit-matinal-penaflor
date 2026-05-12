# Diagnóstico: producto activos.xlsx
Fecha: 2026-05-12

## Archivo
- Ruta: `01_INPUTS/producto activos.xlsx`
- Header real: fila 3 (filas 0-2 son metadatos del archivo de referencia)
- Total productos con código numérico: **253**

## Columnas (8 columnas)
| # | Columna original | Nombre normalizado | Descripción |
|---|---|---|---|
| 1 | Bodega | bodega | Bodega/empresa proveedora |
| 2 | Segmento | segmento | Segmento de precio (Premium, Alto, Superior...) |
| 3 | Linea Comercial | linea_comercial | Línea comercial específica |
| 4 | Código Art. | codigo_producto | Código numérico — clave de cruce con ventas.csv:Codigo |
| 5 | Categoria | categoria | **Categoría comercial — fuente de clasificación VDA/VDG/etc.** |
| 6 | Descripción Art. | descripcion_art | Nombre del artículo |
| 7 | Lts x caja | lts_x_caja | Litros totales por caja/envase |
| 8 | UxC | uxc | Unidades por caja (para calcular lts/unidad = lts_x_caja / uxc) |

## Distribución por Categoría
- `Vinos del año`: 93 productos
- `Vinos de guarda`: 75 productos
- `Espumantes`: 21 productos
- `Whisky`: 13 productos
- `Whisky (Maltas)`: 9 productos
- `Cerveza Artesanal`: 9 productos
- `Vodka`: 7 productos
- `Gin`: 6 productos
- `RTD (S)`: 5 productos
- `Vinos de Mesa`: 4 productos
- `RTD`: 3 productos
- `Licores`: 3 productos
- `Ron`: 2 productos
- `Bourbon`: 2 productos
- `Sidra`: 1 productos

## Distribución por Segmento
- `Premium`: 42
- `Alto`: 35
- `Superior`: 27
- `Medio Alto`: 25
- `Super Premium`: 21
- `Champaña Alta y Premium`: 17
- `Premium (S)`: 15
- `Super Premium (S)`: 14
- `Ultra Premium`: 13
- `Standard (S)`: 13
- `Cerveza Artesanal`: 9
- `Medio`: 6
- `Vinos de Mesa`: 4
- `RTD (S)`: 4
- `Champaña Medio`: 4
- `RTD`: 3
- `Primary (S)`: 1

## Distribución por Bodega
- `Finca Las Moras`: 53
- `Trapiche`: 49
- `Diageo`: 47
- `El Esteco`: 32
- `Navarro Correas`: 20
- `Mascota Vineyards`: 10
- `Elementos`: 9
- `Antares`: 9
- `Suter`: 6
- `Vinos de Mesa`: 4
- `La Liga de los Enologos`: 4
- `San Telmo`: 4
- `Frizze`: 3
- `Mascota`: 3

## Productos VDA (Vinos del año): 93
**Criterio:** `categoria == 'Vinos del año'` (normalizado: sin tildes/ñ)

### Bodegas VDA
- `Finca Las Moras`: 32
- `Trapiche`: 22
- `Navarro Correas`: 9
- `Elementos`: 9
- `El Esteco`: 8
- `Suter`: 4
- `La Liga de los Enologos`: 4
- `Mascota`: 3
- `San Telmo`: 2

### Segmentos VDA
- `Alto`: 35
- `Superior`: 27
- `Medio Alto`: 25
- `Medio`: 6

### Líneas Comerciales VDA (top 10)
- `Alma Mora`: 10
- `Alaris`: 10
- `Dada`: 9
- `ELEMENTOS`: 9
- `Don David`: 8
- `Finca Las Moras`: 7
- `Trapiche Reserva`: 6
- `Coleccion Privada`: 5
- `Los Arboles`: 4
- `Fond de Cave`: 4

## Clasificaciones disponibles desde el maestro
| Clasificación | Criterio | Productos |
|---|---|---|
| VDA | `categoria == 'Vinos del año'` | 93 |
| VDG | `categoria == 'Vinos de guarda'` | 75 |
| Espumantes | `categoria == 'Espumantes'` | 21 |
| Whisky | `categoria in ['Whisky', 'Whisky (Maltas)']` | 22 |
| Cerveza Artesanal | `categoria == 'Cerveza Artesanal'` | 9 |
| Vodka | `categoria == 'Vodka'` | 7 |
| Gin | `categoria == 'Gin'` | 6 |
| Vinos de Mesa | `categoria == 'Vinos de Mesa'` | 4 |

## Nota: Tags en ventas.csv / historial_ventas.csv
El campo `Tags` de Gescom contiene valores como `Vinos del Año`, `PEÑAFLOR GRUPO OBJETIVO`, etc.
Se usa como **fallback** de clasificación VDA para filas cuyo `Codigo` no figura en el maestro.
La fuente oficial es siempre el maestro de productos.

## Nota: Encoding
El archivo tiene un problema de codificación interna (caracteres `ñ`, `á` aparecen como `?` al leer con Python).
El procesamiento usa `unicodedata.normalize` para comparar sin diacríticos.
Se recomienda exportar una versión limpia desde Gescom o guardar el Excel con encoding UTF-8.

## Archivos generados
- `04_DATASETS_ORBIT/mod_vda_productos.csv` — 93 productos VDA
- `04_DATASETS_ORBIT/mod_vda_productos_revision_necesaria.csv` — 160 no-VDA (referencia)