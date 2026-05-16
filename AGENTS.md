# AGENTS — Contrato de trabajo para agentes IA

Proyecto: **ORBIT Matinal Peñaflor**
Ruta base: `C:\Orbit\MATINAL_PENAFLOR`

---

## Roles de agentes

| Agente | Rol | Permisos |
|--------|-----|----------|
| **Claude Code** | Ejecuta, modifica y valida código, datasets y endpoints | Lectura/escritura sobre el repo. Puede correr scripts Python y PowerShell. |
| **Codex** | Audita externamente, revisa lógica y propone correcciones | Solo lectura. No modifica archivos directamente. |
| **Obsidian** | Fuente de reglas de negocio, errores conocidos y arquitectura | Referencia documental. Ver `00_OBSIDIAN_ORBIT/`. |

---

## Reglas absolutas

- **No inventar datos.** No usar mock. No usar fallback silencioso.
- **No hacer commit sin aprobación explícita del usuario.**
- **No hacer push bajo ninguna circunstancia sin aprobación.**
- **Precisión del dato primero. Diseño visual después.**
- **No modificar LEGACY/** sin autorización explícita.
- **No crear archivos tipo** `final`, `final2`, `nuevo`, `corregido`, `fix`, `v2`, `v3`.
- **No ejecutar kill general de procesos Python.** Detener solo procesos `server_orbit.py` en puerto 8502.
- **No usar Bash para levantar el servidor.** Usar PowerShell con `Start-Process`.
- Antes de modificar cualquier archivo, explicar qué se va a tocar y por qué.
- Después de modificar, ejecutar validación real y mostrar diff.
- Todo cambio registrarlo en `CHANGELOG_AI.md`.
- Toda próxima tarea documentarla en `NEXT_TASK.md`.

---

## Reglas comerciales Peñaflor

### Vendedores activos
- Activos: **V3, V4, V6, V7, V8, V9, V10**
- **Excluir siempre V2 y V5** de todos los reportes, endpoints y cálculos.

### V3 — Nadia Gambino
- **No trabaja Autoservicio.**
- No calcular objetivos, CCC, cobertura ni 11 Titulares de Autoservicio para V3.
- `ccc_autoservicio = 0` siempre para V3.
- `trabaja_autoservicio = false` en todos los endpoints.

### CCC — Compradores con compra neta
- **CCC = cliente único con `ImporteNetoItem > 0`.**
- Separar siempre:
  - `CCC Compradores Mes` → clientes únicos en `ventas.csv` del mes calendario actual.
  - `CCC Día` → clientes únicos con compra ayer, desde `mod_ccc_segmento`.
  - `CCC Ruta` → clientes del maestro (`clientes.xlsx`) con compra.
- Nunca mezclar CCC Mes con CCC Día ni con CCC de historial.

### Cobertura
- **Tradicional / Almacén / Kiosco**: mínimo 3 botellas para considerar cubierto.
- **Autoservicio**: mínimo 6 botellas.
- **On Premise / Vinoteca**: mínimo 6 botellas.
- No mostrar % de cobertura si el denominador no es la cartera real (`clientes.xlsx`).
- No mostrar cobertura si el numerador mezcla períodos distintos.

### Separación de períodos — obligatoria
Cada KPI debe indicar claramente a qué período y cartera corresponde:

| Etiqueta | Fuente | Período | Cartera |
|----------|--------|---------|---------|
| Mes | `ventas.csv` filtrado mes actual | Mes calendario | Total empresa |
| Día / Ayer | `mod_ccc_segmento` | Último día operativo | Zona del día |
| Zona Vi | `clientes_dia.csv` | Día de visita (Vi) | Solo clientes de esa zona |
| Cartera total | `clientes.xlsx` | Estático maestro | 2045 clientes (sin V2/V5) |

### Avance vs. Tendencia
- **Avance %** = `acumulado / objetivo * 100` — lo que se ejecutó.
- **Tendencia %** = `(acumulado / días_corridos) * días_totales / objetivo * 100` — proyección al cierre.
- El portal muestra **Tendencia**, no Avance bruto. Etiquetar correctamente.

### 11 Titulares
- 11T puede ser mayor que CCC: cuenta impactos o marcas, no solo clientes.
- Etiquetar siempre como "Marcas 11T" o "Impactos 11T", nunca como "Clientes".
- No usar `once_titulares_total` como denominador de clientes.

---

## Fuentes de verdad por KPI

| KPI | Fuente correcta | Fuente PROHIBIDA |
|-----|----------------|------------------|
| CCC Mes | `ventas.csv` mes actual | `clientes_dia.ccc_mes_flag` |
| CCC Día | `mod_ccc_segmento` | `ventas.csv` completo |
| Cartera total | `clientes.xlsx` | `clientes_dia.csv` |
| Objetivos | `resultado.xlsx` / `mod_volumen_vendedor.csv` | Hardcode |
| Botellas mes | `ventas.csv` (pendiente implementar) | `clientes_dia.botellas_mes` (solo Vi) |
| Cobertura | ventas.csv + clientes.xlsx (pendiente) | `cobertura_mes_flag` con historial |

---

## Archivos peligrosos — no usar sin verificar

- `01_INPUTS/_NO_USAR_ventas_diarias.csv`
- `01_INPUTS/_NO_USAR_avance_objetivos.xlsx`
- `PAV MATINAL PE_A FLOR/data.js.mock.bak`
- `PAV MATINAL PE_A FLOR/data_provider.js.bak`
- Cualquier columna `ccc_mes_flag`, `cobertura_mes_flag` de `clientes_dia.csv` como fuente principal.

---

## Contexto adicional

Ver `00_OBSIDIAN_ORBIT/` para:
- Reglas de negocio detalladas → `REGLAS_NEGOCIO_PAV.md`
- Mapa de flujo de datos → `MAPA_DATOS_PAV.md`
- Errores conocidos y soluciones → `05_ERRORES_Y_SOLUCIONES/`
- Arquitectura del sistema → `08_ARQUITECTURA/`
- Prompts maestros para auditoría → `04_PROMPTS_MAESTROS/`
