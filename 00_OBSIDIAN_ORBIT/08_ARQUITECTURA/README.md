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
