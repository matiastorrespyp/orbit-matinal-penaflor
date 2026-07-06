# Auditoría de migración — Orbit Peñaflor → patrón operativo Orbit PepsiCo

**Fecha:** 2026-07-06
**Alcance:** SOLO documental. Este archivo NO cambia código, NO mueve archivos, NO toca endpoints, NO toca SQLite, NO toca Google Sheets y NO elimina inputs.
**Objetivo:** dejar cerrado el **Mapa de Fase 0** (inventario endpoint → fuente de datos → clasificación → riesgo → fase) como red de seguridad previa a cualquier migración. **Fase 1 NO se ejecuta todavía.**

> Regla transversal: **ningún cambio de esta migración debe mezclar PepsiCo con Peñaflor.** Sheets aislado por proveedor, sin helper común, sin unificar spreadsheets, sin unificar bases locales.

---

## 1. Patrón objetivo vs. estado actual

**Patrón PepsiCo (destino):**
```
inputs Excel → ETL (build) → web/app_data.js + data/*.json  (TODO precomputado)
            → server FINO: sólo sirve estáticos, cero pandas en request
            → Google Sheets SÓLO para datos vivos (planificación, mensajes, push)
```

**Peñaflor (hoy, verificado):**
```
inputs Excel (01_INPUTS/*.xlsx, 38 tracked)  ─┬─→ generar_datasets_acum.py (ETL local) → 04_DATASETS_ORBIT/*.csv (24 tracked)
                                              │
                    ⚠ los .xlsx crudos se DEPLOYAN a Render
                                              │
server_orbit.py (7932 líneas, ~55 endpoints) ── lee CSV Y Excel crudo EN CADA REQUEST y corre pandas por endpoint
                                              → /api/... → PAV MATINAL PE_A FLOR/portal.html (frontend único)
   SQLite /var/data/orbit.db (Persistent Disk) ← hidratado desde Google Sheets (sólo planificación)
```

**Diferencia central:** PepsiCo pre-cocina; Peñaflor **recomputa en tiempo de request** leyendo CSVs y `.xlsx` crudos. Ese es el gap a cerrar, gradualmente y con fallback.

**Deploy actual (no romper):** Flask + gunicorn (`server_orbit:app`, `--workers 1 --threads 8`), Render `starter` + Persistent Disk 1 GB en `/var/data`, `ORBIT_DB_PATH=/var/data/orbit.db`, healthcheck `/api/healthz`, autoDeploy en `master`.

---

## 2. Hallazgos de riesgo (explícitos)

| # | Hallazgo | Estado | Implicancia |
|---|----------|--------|-------------|
| R1 | **Excel comercial crudo versionado y deployado a Render.** 38 archivos `01_INPUTS/*.xlsx / *.csv` están tracked en git y viajan al servicio. `server_orbit.py` los lee en runtime (`resultado.xlsx`, `objetivo 11T.xlsx`, `clientes.xlsx`, `OBJSELLOUT.xlsx`, `planfrizze.xlsx`, `ventas.csv`, `ventas_acumulada.csv`, etc.). | ⚠ Abierto | Datos comerciales sensibles en el deploy + costo/lentitud de pandas por request. Objetivo: que el Excel lo consuma SÓLO el ETL offline. |
| R2 | **`mensajes` y `alerta_seguimiento` viven SÓLO en SQLite.** No tienen espejo en Google Sheets. | ⚠ Abierto | Si se pierde/recrea el Persistent Disk, se pierden. Son datos vivos sin fuente de verdad externa. (No se cambia ahora; queda como deuda documentada.) |
| R3 | **`planificacion` SÍ tiene Google Sheets como fuente de verdad.** SQLite se hidrata desde Sheets (`hydrate_planificacion_from_sheets`, `restore_planificacion_if_empty`) y cada escritura hace `gsheets_upsert_plan` + `gsheets_verify_plan`. | ✅ OK | Es el modelo correcto a replicar para R2 en el futuro. |
| R4 | **SQLite debe quedar como CACHE, no como verdad.** Hoy lo es para `planificacion`; NO lo es para `mensajes` / `alerta_seguimiento` (ahí es la única copia). | ⚠ Parcial | Regla de arquitectura: la verdad de datos vivos = Google Sheets; SQLite = cache descartable/rehidratable. |
| R5 | **Aislamiento por proveedor.** | ✅ Regla | Ningún paso puede unificar Sheets, bases ni helpers con PepsiCo. |

---

## 3. Convenciones del mapa

- **Tipo de lectura:** `CSV` = dataset en `04_DATASETS_ORBIT/` (o `09_CONFIG`, `05_MASTER_DATA`); `XLS` = Excel crudo en `01_INPUTS/`; `VENTAS` = `01_INPUTS/ventas*.csv` crudo (mes vivo); `SQLITE` = `orbit.db`; `SHEETS` = Google Sheets; `JSON` = `06_APP_DATA/*.json` ya generado; `STATIC` = archivo servido tal cual.
- **Clasificación del dato:**
  - **Derivable** = se reconstruye 100% desde inputs/ETL (candidato a precomputar).
  - **Vivo** = lo genera el usuario en runtime (planificación, mensajes, seguimiento). NO se precomputa.
  - **Mixto** = combina dato vivo (SQLite/Sheets) con dataset. No puede quedar 100% estático.
- **Riesgo de migración:** `Bajo` / `Medio` / `Alto` (por volumen de fuentes y mezcla con Excel crudo o dato vivo).

---

## 4. Inventario de endpoints (mapa Fase 0)

### 4.1 Infra / estáticos — no aplican a precómputo

| Endpoint | Método | Fuente | Lectura | Dato | Riesgo | Fase |
|----------|--------|--------|---------|------|--------|------|
| `/favicon.ico` | GET | — | — | — | — | — |
| `/` , `/portal.html` | GET | `PAV MATINAL PE_A FLOR/portal.html` | STATIC | — | — | — |
| `/<path:filename>` | GET | carpeta frontend | STATIC | — | — | — |
| `/api/healthz` | GET | — (liviano) | — | — | — | — |
| `/api/login` | POST | `USERS` (en código) | in-code | vivo (auth) | — | No tocar |

### 4.2 Datos VIVOS — **NO TOCAR** (Grupo C)

| Endpoint | Método | Fuente | Lectura | Dato | Riesgo | Fase |
|----------|--------|--------|---------|------|--------|------|
| `/api/planificacion` | GET/POST | SQLite `planificacion` + Google Sheets | SQLITE+SHEETS | **vivo** | Alto | **No tocar** (verdad = Sheets, R3) |
| `/api/planificacion/<plan_id>` | PATCH | SQLite `planificacion` + Google Sheets | SQLITE+SHEETS | **vivo** | Alto | **No tocar** |
| `/api/mensajes` | GET/POST | SQLite `mensajes` (SÓLO) | SQLITE | **vivo** | Alto | **No tocar** — ver R2 |
| `/api/alertas/seguimiento` | GET/POST | SQLite `alerta_seguimiento` (SÓLO) | SQLITE | **vivo** | Alto | **No tocar** — ver R2 |

### 4.3 MIXTO (vivo + dataset) — no 100% estático (Grupo D)

| Endpoint | Método | Fuente | Lectura | Dato | Riesgo | Fase |
|----------|--------|--------|---------|------|--------|------|
| `/api/matinal/resumen` | GET | SQLite `planificacion` + CSV datasets + `vendedores_activos` | SQLITE+CSV | **mixto** | Alto | Tarde. La parte de dataset se puede precomputar; el cruce con `planificacion` queda dinámico. |
| `/api/orbit-data` | GET | `06_APP_DATA/orbit_portal_data.json` | JSON | derivable | Bajo | Ya es JSON pre-generado (referencia del patrón destino). |

### 4.4 Derivables PUROS de CSV — **candidatos #1 a precomputar** (Grupo A, riesgo bajo)

| Endpoint | Método | Fuente | Lectura | Dato | Riesgo | Fase |
|----------|--------|--------|---------|------|--------|------|
| `/api/gerencia/11t_empresa` | GET | `mod_11_titulares.csv` | CSV | derivable | Bajo | **Fase 1/2 primero** |
| `/api/gerencia/11t_vendedor` | GET | `mod_11_titulares.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/gerencia/11t_acum` | GET | `mod_11t_acum.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/gerencia/cobertura_segmento` | GET | `clientes_dia.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/gerencia/cobertura_acum` | GET | `mod_cobertura_acum.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/gerencia/cobertura_acum_faltantes` | GET | `mod_cobertura_acum_detalle.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/vendedor/<vid>/cobertura_acum` | GET | `mod_cobertura_acum.csv` + `_detalle.csv` | CSV | derivable | Bajo | Primero (por vendedor) |
| `/api/gerencia/real_ayer_segmento` | GET | `mod_ccc_segmento.csv` + `vendedores_activos.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/gerencia/planes_autoservicio` | GET | `mod_gastos_accion.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/gerencia/planes_as` | GET | `mod_planes_as.csv` + `mod_sincargos_envios.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/vendedor/<vid>/planes_as` | GET | `mod_planes_as.csv` | CSV | derivable | Bajo | Primero (por vendedor) |
| `/api/gastos_accion` | GET | `mod_gastos_accion.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/gerencia/innovaciones_segmento` | GET | `mod_innovaciones_segmento.csv` | CSV | derivable | Bajo | **Primero** |
| `/api/vendedor/<vid>/innovaciones_segmento` | GET | `mod_innovaciones_segmento.csv` | CSV | derivable | Bajo | Primero (por vendedor) |
| `/api/vendedor/<vid>/plan_innovaciones` | GET | `mod_innovaciones_segmento.csv` + `clientes_dia.csv` + `05_MASTER_DATA/clientes_master.csv` | CSV | derivable | Bajo-Medio | Primero (por vendedor, multi-CSV) |

> **Nota parametrizados `<vid>`:** los endpoints por vendedor se precomputan como **un JSON por vendedor** (igual que PepsiCo hace per-vendedor). El set de vendedores es fijo: V3, V4, V6, V7, V8, V9, V10 (excluidos V2, V5, V20).

### 4.5 Derivables con Excel crudo / ventas — Fase 2 media (Grupo B, riesgo medio)

| Endpoint | Método | Fuente | Lectura | Dato | Riesgo | Fase |
|----------|--------|--------|---------|------|--------|------|
| `/api/dashboard` | GET | CSV datasets + `resultado.xlsx` + `ventas.csv` | CSV+XLS+VENTAS | derivable | Medio | Fase 2 media |
| `/api/diagnostico` | GET | CSV datasets + `ventas.csv` + `clientes.xlsx` | CSV+XLS+VENTAS | derivable | Medio | Fase 2 media |
| `/api/clientes` | GET | `clientes_dia.csv` + `02_HISTORY/…` | CSV | derivable | Medio | Fase 2 media |
| `/api/clientes/buscar` | GET | `clientes.xlsx` + ventas | XLS+VENTAS | derivable | Medio | Fase 2 media |
| `/api/clientes/<cliente_id>/ficha` | GET | `clientes.xlsx` + ventas | XLS+VENTAS | derivable | Medio | Fase 2 media |
| `/api/vendedor/<vid>` (detalle) | GET | CSV datasets + `resultado.xlsx` | CSV+XLS | derivable | Medio | Fase 2 media |
| `/api/gerencia/ccc_empresa` | GET | `ventas.csv` (mes, ImporteNeto>0) + `vendedores_activos.csv` | VENTAS+CSV | derivable | Medio | Fase 2 media |
| `/api/gerencia/once_titulares` | GET | `11_titulares_…match_codigos.xlsx` + `ventas_acumulada.csv` + `objetivo 11T.xlsx` + `mod_11_titulares.csv` | XLS+VENTAS+CSV | derivable | Medio-Alto | Fase 2 |
| `/api/gerencia/once_titulares_zona` | GET | `ventas_acumulada.csv` + `clientes.xlsx` + `objetivo 11T.xlsx` | VENTAS+XLS | derivable | Medio-Alto | Fase 2 |
| `/api/gerencia/ranking_rechazos` | GET | `resultado.xlsx` (hoja Rechazos) | XLS | derivable | Medio | Fase 2 media |
| `/api/gerencia/innovaciones_total` | GET | `mod_innovaciones_segmento.csv` + `ventas.csv` | CSV+VENTAS | derivable | Medio | Fase 2 media |
| `/api/gerencia/sellout_categoria` | GET | `mod_sellout_categoria.csv` + maestro 04D (csv/xlsx) + `OBJSELLOUT.xlsx` + ventas | CSV+XLS+VENTAS | derivable | Alto | Fase 2 |
| `/api/gerencia/sellout_litros` | GET | `ventas.csv` | VENTAS | derivable | Medio | Fase 2 media |
| `/api/gerencia/acciones_ranking` | GET | `mod_acciones_ranking.csv` + `mod_acciones_analisis.csv` + ventas | CSV+VENTAS | derivable | Medio | Fase 2 media |
| `/api/gerencia/alertas_caida` | GET | `ventas.csv` (mes vivo) | VENTAS | derivable | Medio | Fase 2 media |
| `/api/gerencia/alertas_caida/export` | GET | `ventas.csv` → export `.xlsx` | VENTAS | derivable | Medio | Fase 2 media (genera descarga) |
| `/api/alertas` | GET | `01_INPUTS/ACCIONES COMERCIALES/<mes>/acciones_comerciales_<mes>_penaflor.csv` | CSV(input) | derivable | Medio | Fase 2 media |
| `/api/vendedor/<vid>/ruta` | GET | `clientes.xlsx` + `mod_innovaciones_segmento.csv` + `ventas.csv` | XLS+CSV+VENTAS | derivable | Medio-Alto | Fase 2 (por vendedor) |
| `/api/vendedor/<vid>/oportunidades_innovacion` | GET | `mod_innovaciones_segmento.csv` + `ventas_acumulada.csv` | CSV+VENTAS | derivable | Medio | Fase 2 (por vendedor) |
| `/api/gerencia/incentivo_faro` | GET | `incentivo_club_faro*.xlsx` + `ventas_acumulada.csv` + `vendedores_activos.csv` | XLS+VENTAS+CSV | derivable | Medio | Fase 2 |
| `/api/vendedor/<vid>/incentivo_faro` | GET | idem por vendedor | XLS+VENTAS | derivable | Medio | Fase 2 (por vendedor) |
| `/api/gerencia/plan_frizze` | GET | `PLAN FRIZZE/planfrizze.xlsx` | XLS | derivable | Bajo-Medio | Fase 2 media |
| `/api/vendedor/<vid>/plan_frizze` | GET | `planfrizze.xlsx` | XLS | derivable | Bajo-Medio | Fase 2 (por vendedor) |
| `/api/gerencia/incentivo_dada` | GET | `DADAVERANOOBJ.xlsx` + `dadatinto.csv` | XLS+CSV | derivable | Bajo-Medio | Fase 2 media |
| `/api/gerencia/acciones_mes` | GET | catálogo acciones (CSV/xlsx del mes) | CSV+XLS | derivable | Medio | Fase 2 |
| `/api/vendedor/<vid>/acciones_mes` | GET | idem por vendedor | CSV+XLS | derivable | Medio | Fase 2 (por vendedor) |

### 4.6 Muy pesados / especiales — Fase 2 tardía (Grupo E)

| Endpoint | Método | Fuente | Lectura | Dato | Riesgo | Fase |
|----------|--------|--------|---------|------|--------|------|
| `/api/acciones_vigentes` | GET | reglas `09_CONFIG/*.csv` + `ACCIONES COMERCIALES/*` (csv/json/xlsx) + `RAW_PRODUCTOS/*.xlsx` + `objetivo 11T.xlsx` + `INNOVACIONES/Innovaciones.xlsx` + `mod_planes_as.csv` + ventas + acciones ON `.xlsx` + maestro 04D | CSV+XLS+VENTAS (múltiple) | derivable | **Alto** | Tarde — es el endpoint más entrelazado; migrar último dentro de derivables. |
| `/api/gerencia/cierre_mes` | GET | `resultado_mes.xlsx` / `resultado.xlsx` (Avance) + `ventas_acumulada.csv` + `objetivo 11T.xlsx` + `01_INPUTS/cierres mes/*` | XLS+VENTAS | derivable (mensual, congelado) | Alto | Tarde — cadencia mensual, no diaria. |
| `/api/gerencia/cierres_historicos` | GET | `07_CIERRES_MENSUALES/*.json` + manifests `01_INPUTS/cierres mes/` | JSON | derivable | Bajo | Ya lee JSON pre-generado; casi alineado al patrón destino. |

---

## 5. Recomendación por fase

**Fase 0 — Mapa (este documento).** Cerrada. Red de seguridad: toda migración se valida contra esta clasificación.

**Fase 1 — Capa de precómputo, sin tocar endpoints.**
Crear un `build_portal_data.py` (espejo del ETL→JSON de PepsiCo) que corra **las mismas funciones** del server offline y vuelque **un JSON por endpoint** (y uno por vendedor para los `<vid>`) a una carpeta nueva (p. ej. `web_data/`). No modifica `server_orbit.py`. Se valida con diff contra la salida viva del endpoint. Riesgo runtime = 0. **NO ejecutar todavía.**

**Fase 2 — Conmutar lecturas endpoint por endpoint, con flag + fallback.**
Por cada endpoint validado: `if JSON precomputado fresco → servirlo; else → camino pandas actual`. Orden sugerido:
1. Grupo A (§4.4) — derivables puros de CSV, riesgo bajo.
2. Grupo B (§4.5) — derivables con Excel/ventas, riesgo medio.
3. Grupo E (§4.6) — pesados/mensuales, al final.
Los Grupos C (vivos) y la parte viva del Grupo D **no se tocan**.

**Fase 3 — Dejar de deployar Excel crudo a Render (cierra R1).**
Cuando los endpoints leen JSON precomputado, el ETL corre offline (local/CI) y se commitea **sólo** el JSON. Se saca el Excel comercial del deploy y `openpyxl` del runtime.

**Fase 4 — Adelgazar el server (alinear a PepsiCo) + tratar R2.**
Sacar pandas del camino de request; SQLite como cache pura. Recién acá evaluar dar a `mensajes`/`alerta_seguimiento` una fuente de verdad en Sheets (replicando R3). Sólo después de migrar todos los derivables.

---

## 6. Qué precomputar primero vs. qué no tocar

**Candidatos #1 (empezar por acá):** todos los de §4.4 (Grupo A) — derivables puros de un CSV de `04_DATASETS_ORBIT/`. Bajo riesgo, alto alivio de cómputo. Empezar por los de gerencia sin `<vid>`:
`11t_empresa`, `11t_vendedor`, `11t_acum`, `cobertura_segmento`, `cobertura_acum`, `cobertura_acum_faltantes`, `real_ayer_segmento`, `planes_autoservicio`, `planes_as`, `gastos_accion`, `innovaciones_segmento`.

**NO tocar todavía (dato vivo o mezcla):**
- `/api/planificacion` (GET/POST) y `/api/planificacion/<id>` (PATCH) — verdad en Sheets.
- `/api/mensajes` (GET/POST) — SQLite único (R2).
- `/api/alertas/seguimiento` (GET/POST) — SQLite único (R2).
- `/api/matinal/resumen` — mixto (planificación + datasets).
- `/api/login` — auth en código.

---

## 7. Garantías (no se rompe nada)

- **Lógica comercial intacta:** vendedores activos V3/V4/V6/V7/V8/V9/V10; excluidos V2/V5/V20; V3 no trabaja Autoservicios; sábado sólo V3 y V4; cobertura Tradicional = 3 botellas misma marca; AS/OP/Vinotecas = 6 botellas; CCC = importe neto > 0; no computar retornables ni exhibidores como cobertura. En la migración estas reglas **se mueven verbatim** de request-time a build-time, no se reescriben.
- **Acciones comerciales, 11 titulares, innovaciones, cierres mensuales y planificación:** sin cambios de lógica.
- **Sheets:** fuente de verdad de datos vivos; aislado de PepsiCo; sin helper común; sin unificar spreadsheets ni bases locales.
- **SQLite:** cache descartable/rehidratable; no fuente principal.
- **Deploy:** sin cambios hasta Fase 2, y siempre con fallback al camino actual. Se mantiene Flask, gunicorn y `server_orbit:app`.

---

## Apéndice — Referencias de código (server_orbit.py)

- Persistencia viva: `init_db` (L53), `backup_orbit_db` (L91), tablas `planificacion`/`mensajes`/`alerta_seguimiento` (L64/L82/L86).
- Google Sheets (planificación): `_gsheets_*` (L145–261), `gsheets_upsert_plan` (L208), `gsheets_verify_plan` (L236), `hydrate_planificacion_from_sheets` (L279), `restore_planificacion_if_empty` (L322).
- Lector genérico de datasets: `read_csv` (L398); rutas base `DATASETS` / `INPUTS` / `CONFIG` / `APP_DATA` / `FRONTEND`.
- Escrituras SQLite vivas: `alerta_seguimiento` (L1468–1480), `planificacion` (L1689–1741, L1806), `mensajes` (L1819–1826).
