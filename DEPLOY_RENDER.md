# ORBIT PAV Matinal · Guía de Deploy en Render

## TL;DR — Pasos mínimos

1. Subir el repo a GitHub (si no está)
2. Ir a [render.com](https://render.com) → New Web Service → conectar el repo
3. Render detecta `render.yaml` y configura solo
4. Cada día de matinal: commit + push de los datos actualizados → Render re-deploy automático

---

## Pre-requisitos

| Qué | Estado |
|-----|--------|
| `server_orbit.py` usa `PORT` env var | ✅ ya implementado |
| `gunicorn` en `requirements.txt` | ✅ ya incluido |
| `Procfile` con comando gunicorn | ✅ ya existe |
| `render.yaml` | ✅ creado |
| Datos en git (`04_DATASETS_ORBIT/`, `orbit.db`) | ✅ tracked |

---

## Paso 1: Subir a GitHub

Si el repo no está en GitHub todavía:

```bash
# Crear repo privado en github.com (no compartir credenciales)
# luego desde la carpeta del proyecto:
git remote add origin https://github.com/TU_USUARIO/orbit-penaflor-pav.git
git push -u origin master
```

Si ya está, solo hacer push de los cambios actuales:
```bash
git push
```

---

## Paso 2: Crear servicio en Render

1. Ir a **render.com** → **New +** → **Web Service**
2. Conectar repositorio de GitHub (autorizar acceso)
3. Seleccionar el repo `orbit-penaflor-pav` (o el nombre que tengas)
4. Render detecta `render.yaml` automáticamente
5. Click **Create Web Service**

### Costo
- Plan **Starter**: US$7/mes (~$6.200 ARS/mes a cotización actual)
- **No hay tier gratuito para apps dinámicas** en Render desde 2024

### Alternativa gratis: Railway
Si el costo es un problema, Railway tiene $5/mes de crédito incluido:
1. [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Detecta el Procfile automáticamente
3. Variable de entorno `FLASK_DEBUG=false` ya está
4. Costo: US$0-2/mes para tráfico bajo

---

## Paso 3: URL del portal

Una vez desplegado, Render asigna una URL tipo:
```
https://orbit-penaflor-pav.onrender.com
```

Ahí vas a poder acceder desde cualquier smartphone con el mismo login de siempre.

---

## Flujo diario de actualización de datos

Los datos **no persisten entre re-deploys** en el tier básico (filesystem efímero).
El workflow recomendado para la matinal:

```
Cada mañana antes de la reunión:
1. Bajar ventas del ERP → guardar como 01_INPUTS/ventas.csv
2. Bajar objetivos → guardar como 01_INPUTS/resultado.xlsx
3. Ejecutar: python generar_datasets_acum.py
4. git add -A && git commit -m "datos matinal YYYY-MM-DD" && git push
5. Render re-deploya automáticamente (2-3 min)
6. Abrir portal desde smartphone ✅
```

---

## Variables de entorno opcionales

En el panel de Render podés agregar:

| Variable | Valor | Para qué |
|----------|-------|----------|
| `FLASK_DEBUG` | `false` | Desactivar debug en prod |
| `ORBIT_SECRET_KEY` | (string random) | Futura sesión firmada |

---

## Notas sobre SQLite y persistencia

- `orbit.db` se incluye en el repo → está disponible en el deploy
- Los planes de vendedores y mensajes que se graben **desde el portal** se pierden al re-deployar
- Para persistencia real: usar Render's **Persistent Disk** ($7/mes extra) o migrar a Postgres

---

## Checklist pre-deploy

- [ ] `01_INPUTS/ventas.csv` actualizado y commiteado
- [ ] `01_INPUTS/resultado.xlsx` actualizado y commiteado
- [ ] `04_DATASETS_ORBIT/*.csv` regenerados y commiteados
- [ ] `orbit.db` commiteado
- [ ] Contraseñas de usuarios no están hardcodeadas en archivos públicos
- [ ] Repo es **privado** en GitHub (los datos de clientes son sensibles)

---

*Generado automáticamente por ORBIT Pipeline · $(date)*
