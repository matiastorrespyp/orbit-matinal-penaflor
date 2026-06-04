# Arquitectura del Sistema

Carpeta para documentación de arquitectura real del sistema ORBIT Matinal Peñaflor.

## Contenido pendiente de agregar

- Diagrama de componentes (Flask + datasets + portal).
- Stack actual vs. stack sugerido para producción.
- Dependencias entre scripts y datasets.
- Descripción de flujos de datos por caso de uso.

## Stack actual (2026-05-15)

| Componente | Tecnología | Archivo principal |
|------------|-----------|------------------|
| Backend API | Flask (Python) | server_orbit.py |
| Motor de datos | Python + pandas | LEGACY/orbit_matinal_v42.py |
| Frontend gerencia | HTML + JS vanilla | PAV MATINAL PE_A FLOR/portal.html |
| Frontend vendedor | HTML + JS vanilla | PAV MATINAL PE_A FLOR/portal.html (sección vInicio/vRuta/vKpis) |
| Base de datos | SQLite (planificación) | orbit.db |
| Config | CSV | 09_CONFIG/ |

## Stack sugerido producción (de CLAUDE.md)

- Frontend: Next.js 14 App Router + Tailwind + React Query
- Backend: Node.js + Postgres + Prisma
- Realtime: Pusher o SSE
- Auth: Clerk o NextAuth
- Mobile: Expo (React Native)

## Cierres oficiales vs. datos dinámicos (2026-06-03)

**Regla:** los datos vivos (`ventas.csv`, `ventas_acumulada.csv`, `resultado.xlsx`) son dinámicos y cambian. Para **cierres mensuales oficiales**, el portal debe consumir **únicamente artefactos congelados/versionados** y **no recalcular** con fuentes cambiantes.

| Vista | Endpoint | Fuente | Naturaleza |
|---|---|---|---|
| Cierre de Mes (gerencial) | `/api/gerencia/cierres_historicos` | `07_CIERRES_MENSUALES/<periodo>/<version>/` (generado desde `01_INPUTS/ventas_mes.csv`) | **Histórico, congelado, versionado** |
| Dashboard diario / mes en curso | `/api/dashboard`, `/api/gerencia/cierre_mes`, etc. | `ventas.csv` · `ventas_acumulada.csv` · `resultado.xlsx` | Dinámico, recalcula al vuelo |

- El cierre se genera con `tools/generar_cierre_mensual.py` (versionado inmutable: `version_001`, `version_002`, … nunca pisa el anterior).
- Artefactos del cierre leídos por el endpoint histórico (solo lectura): `manifest.json`, `cierre_mensual_resumen.json`, `ranking_vendedores_mes.json`.
- El endpoint expone `empresa`, `ranking` completo y `ganadores` por categoría (`general`, `volumen_dinero`, `once_titulares`, `innovaciones`). No expone CantBase ni botellas.
- El panel gerencial "Cierre de Mes" (`portal.html`) **no** debe consumir `/api/gerencia/cierre_mes` ni mostrar vista dinámica. Consolidado en commit `b097300`.
