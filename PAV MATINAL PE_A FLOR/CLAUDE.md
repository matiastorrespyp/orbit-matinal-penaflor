# Instrucciones para Claude Code

Este proyecto es un **prototipo de alta fidelidad** del producto **ORBIT · Peñaflor PAV Matinal**. Implementarlo en producción.

## Reglas estrictas

1. **No modificar la identidad visual.** Magenta `#E2147A` es la marca. Sora + Inter son las fuentes. Dark theme es el default. Si dudás, mirá `screenshots/`.

2. **`data.js` es el contrato de datos.** Cuando construyas el backend/API, el endpoint debe devolver exactamente esa shape. No la inventes — copiala.

3. **Sin librerías de UI.** Los gráficos son SVG custom en `charts.jsx`. NO migrar a Recharts/Chart.js sin permiso — pierde el estilo Orbit.

4. **Iconos: SVG inline en `icons.jsx`.** No agregar Lucide/Heroicons.

5. **Números tabulares.** Todo display de cifras usa `font-variant-numeric: tabular-nums`. Si rompés esto, el ranking se desalinea.

6. **Tokens de color.** Los componentes leen `var(--ok)` / `var(--warn)` / `var(--bad)` / `var(--orbit-magenta)`. NO hex inline excepto en las series de datos numéricas (avance >=100 → `--ok`, etc).

## Stack sugerido para producción

- **Frontend:** Next.js 14 App Router + Tailwind (con tokens del prototipo) + React Query
- **Backend:** Node.js + Postgres + Prisma
- **Realtime:** Pusher o Server-Sent Events para `ventaDia` y `alertas`
- **Auth:** Clerk o NextAuth con SSO Peñaflor
- **Mobile (vendedor):** Expo (React Native) reusando los componentes de `screens/vendedor-mobile.jsx`
- **IA / copiloto:** Claude Haiku para generar narrativa de alertas a partir de las reglas de negocio

## Orden de implementación recomendado

1. Backend mínimo: `GET /api/matinal/today` que sirva `data.js` literal.
2. Migrar el HTML a Next.js, una ruta por pantalla.
3. Auth + roles (gerente, supervisor, vendedor).
4. Endpoint `POST /api/planificacion` para que la edición del modal persista.
5. Job nocturno que computa alertas desde ventas reales.
6. App mobile del vendedor.

## Lo que **no** está en el prototipo y vas a tener que diseñar

- Pantalla de login.
- Selector de fecha (hoy solo hay LU/MA/MI… de la semana actual).
- Vista detallada de un cliente individual (drill-down desde "Clientes Críticos").
- Vista detallada de un vendedor (drill-down desde "Vendedores").
- Vista vespertina (cierre del día).
- Configuración: alta de vendedor, edición de objetivos.

Antes de implementar cualquiera de éstas: **proponer el diseño primero**, alineado con el sistema visual existente.
