# README — Contexto ORBIT para agentes IA

Esta carpeta contiene la documentación operativa del proyecto **ORBIT Matinal Peñaflor**, preparada para ser consumida por Claude Code y Codex como contexto real de trabajo.

**No es una copia de la bóveda completa.** Es una selección controlada de los documentos necesarios para operar con precisión sobre el repo.

---

## Contenido

| Archivo / Carpeta | Qué contiene | Cuándo leerlo |
|-------------------|--------------|---------------|
| `REGLAS_NEGOCIO_PAV.md` | Reglas comerciales Peñaflor: vendedores, CCC, cobertura, 11T, períodos | Siempre, antes de calcular cualquier KPI |
| `MAPA_DATOS_PAV.md` | Flujo completo: fuente → script → dataset → endpoint → portal | Antes de modificar cualquier dataset o endpoint |
| `04_PROMPTS_MAESTROS/` | Prompts de auditoría y corrección ya validados | Antes de ejecutar una auditoría nueva |
| `08_ARQUITECTURA/` | Arquitectura del sistema, stack, dependencias | Antes de cambiar estructura de archivos o endpoints |
| `05_ERRORES_Y_SOLUCIONES/` | Errores conocidos, causa raíz y solución aplicada | Antes de intentar corregir un bug ya visto |
| `BITACORA_2026-06-13.md` | Registro de cambios de la sesión 12-13/06: reglas (V3 On Premise, Despensa=Almacén, 11T), productos nuevos, ACJ26-028, features de portal | Para ver qué se tocó recientemente |

---

## Reglas de uso para agentes

1. Leer `REGLAS_NEGOCIO_PAV.md` antes de calcular CCC, cobertura, 11T o segmentos.
2. Leer `MAPA_DATOS_PAV.md` antes de modificar cualquier script o endpoint.
3. Consultar `05_ERRORES_Y_SOLUCIONES/` antes de proponer una corrección.
4. No asumir que un dataset intermedio es correcto sin verificarlo contra su fuente real.
5. No mostrar porcentajes de cobertura si el denominador no es `clientes.xlsx`.
6. No usar `ccc_mes_flag` ni `cobertura_mes_flag` como fuente principal de KPIs.

---

## Estado del proyecto (2026-05-15)

| Etapa | Estado |
|-------|--------|
| Etapa 1 — CCC Mes desde ventas.csv | ✅ Completada (commit c3de7aa) |
| Etapa A — Labels y denominadores | En revisión — sin commit |
| Etapa B — Motor legacy (filtro mes) | Pendiente aprobación |
| Etapa C — Portal labels finales | Pendiente Etapa B |

---

## Cómo agregar documentación

Solo agregar a esta carpeta documentos que:
- Sean reglas de negocio confirmadas por el usuario.
- Sean errores ya diagnosticados con causa raíz conocida.
- Sean arquitectura real del sistema (no especulativa).

No copiar toda la bóveda Obsidian sin filtrar.
