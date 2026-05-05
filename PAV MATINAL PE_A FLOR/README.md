# ORBIT · Peñaflor — PAV Matinal

Plataforma operativa para la **reunión matinal de Peñaflor**: panel gerencial + app del vendedor. Diseñada como prototipo navegable de alta fidelidad, lista para implementación productiva con Claude Code.

> **Stack del prototipo:** HTML estático + React 18 (UMD) + Babel Standalone, sin build. Todos los datos viven en `data.js`. Sin dependencias de red.

---

## 🚀 Cómo correrlo

### Opción A — abrir directo
Doble click en `Orbit Peñaflor PAV Matinal.html`.

### Opción B — servidor local (recomendado)
```bash
# Python 3
python3 -m http.server 8080
# luego abrir http://localhost:8080/Orbit%20Peñaflor%20PAV%20Matinal.html

# o con npx
npx serve .
```

---

## 🗂 Estructura del proyecto

```
.
├── Orbit Peñaflor PAV Matinal.html   # entrypoint — carga todo
├── styles.css                         # design tokens + componentes UI
├── data.js                            # ⚠️ TODA la data de negocio (mock)
├── icons.jsx                          # íconos SVG inline (sin librería)
├── charts.jsx                         # gráficos custom (donut, barras, área, heatmap)
├── app.jsx                            # shell: sidebar, topbar, router de pantallas
├── screens/
│   ├── dashboard.jsx                  # pantalla 1 — Dashboard ejecutivo
│   ├── avance.jsx                     # pantalla 2 — Avance de objetivos
│   ├── planificacion.jsx              # pantalla 3 — Planificación matinal
│   ├── other.jsx                      # pantallas 4–8 — Vendedores, Clientes, Titulares, Segmentos, Alertas
│   └── vendedor-mobile.jsx            # pantalla 9 — App vendedor (mockup mobile)
├── assets/
│   ├── orbit-logo-pink.png            # logo completo (886×293)
│   └── orbit-mark.png                 # solo marca (293×293)
└── screenshots/                       # capturas de referencia
```

---

## 🎨 Sistema de diseño

### Paleta
| Token | Valor | Uso |
|---|---|---|
| `--orbit-magenta` | `#E2147A` | Brand primario |
| `--orbit-magenta-2` | `#B30E5F` | Brand sombra/gradiente |
| `--orbit-lime` | `#FF5BB0` | Brand acento |
| `--ok` | `#2EC27E` | Estado: logrado / cubierto |
| `--warn` | `#F2B544` | Estado: en riesgo |
| `--bad` | `#FF5D5D` | Estado: crítico |
| `--info` | `#4DA3FF` | Estado: en progreso |
| `--bg` | `#0A0D12` | Fondo principal (dark) |
| `--surface` | `#11161E` | Cards |
| `--surface-2` | `#161C26` | Cards elevadas |

> ⚠️ **Nota:** En el código viejo `--orbit-green` ahora apunta a magenta (alias compatibilidad). Cuando refactoricen a producción, renombrar a `--orbit-primary`.

### Tipografía
- **Display / títulos:** Sora (Google Fonts) 600/700
- **UI / cuerpo:** Inter 400/500/600
- **Datos / numérico:** Inter tabular-nums

### Iconografía
SVG inline en `icons.jsx`. No se usa ninguna librería de iconos. Trazos `1.6` stroke-width, redondeados.

---

## 📊 Modelo de datos (`data.js`)

```js
window.ORBIT_DATA = {
  diaActivo: "MA",           // día seleccionado por defecto
  meta: {                    // KPIs de cabecera
    ventaAcumulada, ventaDia, objetivoMensual, avance,
    tendenciaProyectada, diferencia, ...
  },
  vendedores: [              // 7 vendedores Peñaflor
    { id, nombre, zona, color, avance, objetivo, acumulado,
      ccc, t11, clientes, alertas, segmento_excluido? }
  ],
  evolucion: [               // serie diaria del mes
    { d, real, plan }
  ],
  ranking: [...],            // ordenado por avance %
  planificacion: {           // pendiente de aprobación
    [vendedorId]: {
      vendedor: { clientes, ventaProyectada, t11, ... },
      gerencia: { clientes, ventaProyectada, t11, ... },
      diff: [...],           // array de campos modificados
      estado: "pendiente"|"enviada"|"modificada"|"aprobada"
    }
  },
  clientesCriticos: [...],   // brecha + acción recomendada
  titulares11: [...],        // 11 marcas titulares con cobertura
  segmentos: [               // Tradicional / Autoservicio / On Premise
    { id, nombre, req, clientes, cubiertos, color }
  ],
  alertas: [...]             // copiloto comercial — prioridad + impacto $
};
```

### Campos críticos
- `vendedores[].avance` — % vs objetivo. Driver de los semáforos.
- `vendedores[].segmento_excluido` — `"AS"` para V3 Nadia Gambino (no opera autoservicio).
- `planificacion[].diff` — lista de campos donde gerencia modificó la propuesta del vendedor; activa el badge "modificada".
- `alertas[].impacto` — número en pesos, no string.

---

## 🧩 Pantallas

| # | Slug | Archivo | Descripción |
|---|---|---|---|
| 1 | `dashboard` | `screens/dashboard.jsx` | 12 KPIs + evolución mes + ranking + cobertura |
| 2 | `avance` | `screens/avance.jsx` | Barras objetivo vs logrado, proyección, heatmap vendedor×indicador |
| 3 | `planificacion` | `screens/planificacion.jsx` | Tarjetas con diff vendedor↔gerencia, modal de edición |
| 4 | `vendedores` | `screens/other.jsx` | Fichas 360° del equipo |
| 5 | `clientes` | `screens/other.jsx` | Tabla accionable de clientes críticos |
| 6 | `titulares` | `screens/other.jsx` | Cobertura por marca (11T) |
| 7 | `segmentos` | `screens/other.jsx` | Tradicional / AS / On Premise |
| 8 | `alertas` | `screens/other.jsx` | Alertas comerciales priorizadas |
| 9 | `vendedor` | `screens/vendedor-mobile.jsx` | Mockup mobile · 3 vistas |

---

## 🛠 Roadmap de implementación productiva

### Fase 1 — Backend & datos reales
- [ ] Modelar entidades en DB (Postgres recomendado): `vendedor`, `cliente`, `venta_diaria`, `objetivo_mensual`, `planificacion`, `alerta`, `marca_titular`, `cobertura`.
- [ ] ETL desde el sistema fuente (¿SAP? ¿planillas?) — frecuencia mínima: 1× por día antes de la matinal.
- [ ] Endpoint `GET /api/matinal/:fecha` que devuelva el shape exacto de `data.js`.

### Fase 2 — App web (gerencial)
- [ ] Migrar a Next.js o Vite + React. Cada pantalla → ruta.
- [ ] Reemplazar `window.ORBIT_DATA` por React Query / SWR contra el endpoint.
- [ ] Auth (gerente, supervisor, vendedor) con SSO corporativo.
- [ ] Persistencia de **planificación**: el modal de edición de gerencia debe `POST /api/planificacion/:vendedor/:fecha`.
- [ ] Tiempo real: WebSocket o polling de 60s para `ventaDia` + `alertas`.

### Fase 3 — App vendedor (mobile)
- [ ] La pantalla 9 se mueve a React Native o PWA.
- [ ] Push notifications cuando gerencia aprueba/modifica la planificación.
- [ ] Modo offline para clientes críticos (LocalStorage + sync).

### Fase 4 — Copiloto / IA
- [ ] Las **alertas inteligentes** hoy son mock. En prod: regla de negocio + LLM resumen.
- [ ] Patrón sugerido: cron diario que compara `acumulado vs objetivo`, detecta anomalías por vendedor/cliente, y emite una alerta con `impacto $` calculado.
- [ ] Usar `claude-haiku-4-5` (ya disponible vía `window.claude.complete` en este prototipo) para generar el copy de cada alerta.

---

## 🎯 Decisiones de diseño documentadas

1. **Dark theme por defecto.** La matinal arranca a las 7 AM en pantalla grande de sala — dark reduce fatiga y resalta los semáforos.
2. **No emoji.** Todo iconografía custom, alineada con identidad Orbit.
3. **Tabular-nums en todos los números.** Las cifras tienen que alinearse verticalmente cuando se comparan vendedores.
4. **Día pill (LU/MA/MI…).** Permite revisar matinales pasadas sin salir de la pantalla.
5. **Diff vendedor↔gerencia visible.** El supervisor planifica el día anterior; el vendedor lo ve la mañana siguiente. La transparencia del cambio es clave para la dinámica del equipo.
6. **V3 Nadia Gambino sin AS.** Hardcodeado como `segmento_excluido: "AS"` — no afecta su % avance pero sí su heatmap.

---

## 📐 Cómo extender

### Agregar una pantalla
1. Crear `screens/nueva.jsx` exportando `function NuevaScreen({ data, ... })` a `window.NuevaScreen`.
2. Registrarla en `app.jsx` → `nav` array y `titles` map.
3. Sumar `<script type="text/babel" src="screens/nueva.jsx"></script>` al HTML antes de `app.jsx`.

### Agregar un vendedor
Solo editar `data.vendedores[]` en `data.js` — el resto se recalcula.

### Cambiar paleta
Solo `styles.css` `:root`. Los componentes leen tokens, no hex.

---

## 📦 Entregables

- ✅ HTML/CSS/JSX completos, sin build, sin dependencias externas más allá de React+Babel UMD.
- ✅ Logo pink en alta resolución (`assets/orbit-logo-pink.png`).
- ✅ Datos reales del equipo Peñaflor (7 vendedores, alertas, planificación).
- ✅ Mockup mobile del vendedor.
- ✅ Documentación de implementación.

## 🔮 Pendientes conocidos

- Clientes en mapa por zona (zona ya existe en data, falta visual).
- Vista **vespertina** (cierre del día) — espejo del matinal con foco en cumplimiento.
- Plantilla **PepsiCo** — el sistema está pensado para multi-cliente, pero solo Peñaflor está cargado.
- Export PDF del briefing matinal para distribución por WhatsApp.

---

**Autor:** Diseñado en Claude · 2026-05  
**Cliente:** Peñaflor — Equipo PAV
