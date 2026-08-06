# Retiro de `mod_11_titulares.csv` — 2026-08-05

## Qué era

Dataset legacy generado por `LEGACY/orbit_matinal_v42.py:1436`. Grilla cliente × marca del
día, con columnas `tiene_flag` / `falta_flag`.

## Por qué se retira

1. **Venía con `tiene_flag = 0` en las 4.489 filas.** Todo endpoint que lo leyera devolvía
   ceros. `/api/gerencia/11t_empresa` mostraba 0 en las 11 marcas.
2. **No contenía los 11 Titulares.** Tenía 28 "marcas" (TANQUERAY, BAILEYS, JW GOLD,
   COSTA&PAMPA, LOS INTOCABLES…), o sea un universo distinto al oficial.
3. **Era una tercera fuente en desacuerdo** con `mod_11t_acum.csv` y con el cálculo vivo
   de `server_orbit.py`. Para Gordon's Flavours julio-2026 las tres daban 0 / 0 / 51 contra
   los 32 reales informados por el proveedor.

## Fuente que lo reemplaza

`04_DATASETS_ORBIT/mod_11t_acum.csv`, generado por `generar_datasets_acum.generar_11t_acum()`
sobre el motor autoritativo **`motor_11t.py`**. Mismo esquema de columnas
(`vendedor_codigo`, `vendedor_nombre`, `cliente_id`, `segmento_11t`, `marca_objetivo`,
`cant_base_acum`, `tiene_flag`, `falta_flag`), así que la migración no rompió contratos.

`tiene_flag = 1` ahora significa **el cliente llegó al mínimo de botellas de su segmento**
(3 tradicional / 6 autoservicio) tras consolidar el período — no "compró algo".

### Columna agregada 2026-08-05: `cuenta_vendedor`

`mod_11t_acum.csv` distingue los **dos universos** del 11T (ver `CLAUDE.md`, regla V20):

| `cuenta_vendedor` | Qué es | Cuenta en |
|---|---|---|
| `1` | Cliente de la cartera de un vendedor de ruta | EMPRESA y VENDEDORES |
| `0` | Depósito / venta directa (V1, V20) o cliente sin `codven` | **sólo EMPRESA** |

Las filas con `0` traen `vendedor_codigo` vacío y `vendedor_nombre = DEPOSITO`, y **no**
forman parte de la grilla de cartera (el Depósito no tiene cartera: sería un denominador
inventado). Sólo se agregan las combinaciones cliente × titular realmente medidas.

Todo corte por vendedor tiene que filtrar con `server_orbit._universo_vendedores_11t()`.
Los totales de empresa **no** filtran: ahí el Depósito suma. Vale
`con_empresa = con_vendedores + con_deposito` (testeado en `test_motor_11t.SinDobleConteo`).

## Consumidores migrados

| Consumidor | Archivo | Estado |
|---|---|---|
| `/api/gerencia/11t_empresa` | `server_orbit.py` | migrado a `mod_11t_acum.csv` |
| `/api/gerencia/11t_vendedor` | `server_orbit.py` | migrado a `mod_11t_acum.csv` |
| `/api/diagnostico` (bloque `titulares11` e inventario de fuentes) | `server_orbit.py` | migrado |
| Dashboard vendedor (`t11_df`) | `server_orbit.py` | migrado |
| Fallback de `/api/gerencia/once_titulares` | `server_orbit.py` | **eliminado** — el endpoint ahora calcula con `motor_11t`; ya no hay un fallback que devuelva ceros en silencio |

## Consumidores NO migrados (legacy, fuera del portal vigente)

Siguen leyendo el archivo. No alimentan el portal ni el cierre; se dejan como estaban para
no tocar pipelines apagados:

- `app_matinal_penaflor.py:349`
- `app_publish.py:21`
- `audit_pav_matinal_data.py:157`
- `diagnostico_app_orbit.py:20`

## Por qué el archivo NO se borró ni se renombró

Convención del proyecto: los archivos descartados se renombran con `_NO_USAR_`, nunca se
borran. Acá no se hizo ninguna de las dos cosas porque **`LEGACY/orbit_matinal_v42.py` lo
sigue escribiendo** en cada corrida: renombrarlo lo regeneraría igual y quedarían dos
archivos. Queda como salida legacy sin consumidores vigentes en el portal.

**Próximo paso pendiente:** cuando se apague `LEGACY/orbit_matinal_v42.py`, renombrar el
archivo a `_NO_USAR_mod_11_titulares.csv` y migrar los 4 consumidores legacy de la lista.
