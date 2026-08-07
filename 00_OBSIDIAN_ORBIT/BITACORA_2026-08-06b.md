# BITÁCORA 2026-08-06b — Cierre de Mes: plan de acción de la reunión mensual

Continuación de [[BITACORA_2026-08-06]]. Publicado en Render en dos commits:
**`ac60fde`** (la feature) y **`72018df`** (el caché que hizo falta para no duplicar la
espera de la pantalla).

## Qué se pedía

Que en la reunión mensual se anote, para cada objetivo no alcanzado, qué se va a hacer el
mes siguiente para mejorar ese indicador. Y que la reunión del mes siguiente **arranque**
mostrando si esas acciones funcionaron.

## Cómo quedó

| Dónde | Tarjeta | Qué muestra |
|---|---|---|
| **Primera de la pantalla** | `🎯 Seguimiento del plan de acción · <mes anterior>` | Cada acción acordada con **✓ LOGRADO / ✗ NO LOGRADO**, el % actual, de cuánto venía y el delta |
| **Última de la pantalla** | `📝 Plan de acción · <mes>` | Los indicadores que cerraron bajo objetivo, del más lejano al más cercano, con su campo para escribir la acción |

## Las tres decisiones que definen la feature

### 1. "Logrado" se mide, no se declara

El estado sale de volver a medir **el mismo indicador** en el cierre siguiente:
`pct >= 100`. Nadie tilda una casilla. La acción se escribe en la reunión; el resultado lo
pone el dato.

### 2. El delta va SIEMPRE, y aparte del estado

Caso real de la validación: `Sell Out · VERMOUTH` pasó de **0% a 51,7%**. Sigue
`NO LOGRADO` — pero mostrar sólo eso escondería que se movió 51,7 puntos.

> **El estado responde "¿llegamos?" y el delta "¿mejoramos?". Son dos preguntas distintas
> y la reunión necesita las dos.** Un indicador puede mejorar muchísimo y seguir sin
> alcanzar el objetivo; con una sola de las dos cifras, esa conversación no se puede tener.

### 3. `sin_dato` no es `no_logrado`

Si el indicador ya no existe en el cierre nuevo (una categoría que se dejó de medir, un
vendedor que salió) el estado es **`sin_dato`**. **No poder medir no es lo mismo que
fallar**, y marcarlo como fallado ensuciaría el conteo de la reunión.

## Universo de indicadores

Sólo los que **tienen objetivo** en el cierre. Son 4 familias, 26 indicadores en
julio-2026:

| Familia | De dónde sale el objetivo | Id |
|---|---|---|
| Facturación empresa | `objetivos_avance.empresa` | `empresa:facturacion` |
| Facturación por vendedor | `objetivos_avance.vendedores[]` | `vendedor:<código>` |
| 11 Titulares por marca | `once_titulares.marcas[]` | `11t:<slug>` |
| Sell Out por categoría | `sellout.categorias[]` | `sellout:<slug>` |

**CCC, Innovaciones, Planes AS y Acciones no traen objetivo en el cierre**, así que no
entran. No se les inventó uno para poder listarlos: un plan de acción contra un objetivo
inventado no se puede evaluar después.

Julio-2026: **11 no logrados de 26**. Junio: 15. Mayo: 18.

## Detalles de implementación que importan

- **`_plan_accion_indicadores()` es UNA sola función** para listar los no logrados del mes
  y para medir cómo le fue después a un indicador del mes anterior. Con dos funciones se
  desincronizarían y el seguimiento terminaría midiendo distinto que el plan.
- **El id es un slug ASCII** (`_plan_accion_slug`): es la clave que une el plan de un mes
  con la medición del siguiente, así que no puede depender de acentos ni de cómo venga
  codificado el nombre desde el ERP. `VINOS DEL AÑO` → `sellout:vinos_del_ano`.
- **La foto del indicador se guarda junto a la acción** (objetivo/logrado/pct del mes en
  que se escribió) y **se toma del cierre, nunca de lo que mande el navegador**: el cliente
  sólo aporta el texto. El seguimiento compara contra ese número, no contra lo que hoy
  devuelva un cierre regenerado.
- **El periodo anterior no es "mes − 1" a secas**: es el cierre anterior más reciente **que
  tenga un plan guardado**. Si un mes no tuvo reunión, el seguimiento muestra el último
  plan que sí existe en vez de un hueco.
- **Persistencia**: tabla `cierre_plan_accion` en `orbit.db` (disco persistente de Render,
  `/var/data`) + respaldo CSV, mismo criterio que `plan_semanal`. Texto vacío **borra** la
  fila, no guarda una acción en blanco.
- **Los textarea no se re-renderizan al tipear**: se pintan una vez y se leen recién al
  guardar. Es la misma lección del buscador de Plan Cobertura — re-renderizar en cada tecla
  destruye el input y le roba el foco.

## El costo que introduje y hubo que arreglar

El endpoint nuevo rearmaba **todos los cierres de cero**. Medido en Render: la pantalla ya
tardaba **~18 s** en traer `cierres_historicos`, y el plan de acción agregaba **~17 s más**
— la pantalla pasaba a tardar el doble.

`_cierres_historicos()` quedó cacheado por mtime del índice, del árbol de
`07_CIERRES_MENSUALES/`, del trío versionado de `01_INPUTS/cierres mes/` y del maestro 04D
(del que depende el sell out del cierre). Los cierres son datos **congelados**: mientras
los archivos no cambien, el resultado es idéntico por definición.

| | Antes | Después |
|---|---|---|
| Local, en frío | 12,7 s | 12,7 s |
| Local, cacheado | — | **0,005 s** |
| Render, 1ª llamada | 18 s + 17 s | **22,9 s** (una sola vez) |
| Render, siguientes | 18 s cada una | **0,2–0,3 s** |

Verificado que **invalida**: tocando el mtime de un `ventas_mes_*.csv` vuelve a construir.

## Validación

End-to-end **por la UI real**, no sólo por API: se cargaron 5 acciones en la reunión de
**junio**, se guardó, se cambió el selector a **julio** y la tarjeta de seguimiento apareció
arriba de todo con **3 logrados / 2 no logrados**:

```
✗ NO LOGRADO   V3 · Gambino Nadia        20,8%  venía de 68,5%   −47,7 pts
✗ NO LOGRADO   Sell Out · VERMOUTH       51,7%  venía de  0,0%   +51,7 pts
✓ LOGRADO      11T · TRAPICHE RESERVA   103,8%  venía de 52,6%   +51,2 pts
✓ LOGRADO      11T · ANTARES            105,3%  venía de 66,3%   +39,0 pts
✓ LOGRADO      11T · SMIRNOFF FLAVOURS  162,7%  venía de 60,3%  +102,4 pts
```

Orden en el DOM verificado: seguimiento **primero de 11 tarjetas**, plan de acción
**última**. Filas de prueba borradas después (la tabla quedó en 0).

## Archivos tocados

| Archivo | Cambio |
|---|---|
| `server_orbit.py` | Tabla `cierre_plan_accion` en `init_db`; `_PLAN_ACCION_FAMILIAS`, `_plan_accion_slug`, `_plan_accion_indicadores`, `_plan_accion_leer`, `_plan_accion_periodo_anterior`, `_plan_accion_export_csv`; endpoints `GET`/`POST /api/gerencia/cierre_plan_accion`; `gerencia_cierres_historicos` refactorizado a `_cierres_historicos()` + `_CIERRES_HIST_CACHE` / `_cierres_hist_key()` |
| `PAV MATINAL PE_A FLOR/portal.html` | CSS `.pa-*`; contenedores `#cierre-plan-seg` (arriba) y `#cierre-plan-acc` (abajo) en `_render()`; `paCargar`, `paSeguimientoHtml`, `paPlanHtml`, `paGuardar` |
| `CHANGELOG_AI.md`, `NEXT_TASK.md` | Registro |

## Pendiente

- **¿El plan de acción entra al PDF / la minuta de la reunión?** Hoy vive sólo en la
  pantalla. Si la reunión se comparte por PDF, hay que sumarlo al generador.
- **Nadie puede cerrar una acción a mano.** Si la acción se cumplió pero el indicador igual
  no llegó (o al revés), no hay dónde dejar constancia. El modelo ya guarda `autor` y
  `updated_at`; sería un campo más.
- **Para planificar sobre CCC** hay que meter `objccc.xlsx` en el payload del cierre
  versionado: hoy el cierre no trae objetivo de CCC y por eso queda afuera.
- **En Render hay un cierre de `2026-08`** (los 4 archivos del período están publicados,
  aunque localmente figuran borrados). Como agosto está en curso, la pantalla **abre por
  defecto en ese mes con 24 de 26 indicadores en 0%**. Para la reunión real hay que elegir
  julio en el selector. Si las bajas locales son intencionales hay que commitearlas: el
  `.bat` del cierre **no** las publica, porque `cierres mes/` no está en su allowlist
  (mismo patrón **ERR-014**).

> Reglas asentadas en [[REGLAS_NEGOCIO_PAV]] y trazabilidad en [[MAPA_DATOS_PAV]].
> El cierre versionado que alimenta esta pantalla viene de [[BITACORA_2026-08-05b]].
