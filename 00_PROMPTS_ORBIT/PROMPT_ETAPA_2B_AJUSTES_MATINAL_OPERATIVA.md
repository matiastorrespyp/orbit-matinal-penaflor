# PROMPT_ETAPA_2B_AJUSTES_MATINAL_OPERATIVA

## Contexto del Sistema

Estamos trabajando sobre ORBIT Matinal Peñaflor.

Ya funciona:
- carga de planificación del vendedor
- aprobación gerencial
- pestaña Mi Plan
- Planificación
- Plan vs Real
- exclusión V2/V5/V20
- V3 sin Autoservicio

Ahora hay que corregir métricas y pantallas para que la matinal sea realmente útil.

Archivos principales:
- server_orbit.py
- PAV MATINAL PE_A FLOR/portal.html

No tocar:
- LEGACY
- 01_INPUTS
- 02_HISTORY
- 05_MASTER_DATA
- 06_APP_DATA
- CSV/XLSX manualmente

---

## Objetivo

Ajustar el dashboard de gerencia y la vista vendedor para mostrar correctamente:

1. Acumulado mensual real.
2. Tendencia.
3. CCC total mensual y por segmento.
4. 11 titulares por marca acumulados.
5. Cobertura por segmento.
6. Real del día anterior por segmento.
7. Planes de autoservicio.
8. Alertas útiles en su solapa correspondiente.
9. Vista vendedor con acumulado mensual y zona del día separados.

---

## Reglas de negocio obligatorias

- Excluir siempre V2, V5 y V20.
- V3 / Nadia no trabaja Autoservicio.
- No mostrar Autoservicio a V3.
- No calcular objetivos/cobertura/CCC de Autoservicio para V3.
- No inventar datos.
- Si una métrica no tiene fuente confiable, informarlo antes de implementarla.
- No romper endpoints actuales.
- Mantener funcionando Mi Plan y aprobación gerencial.

---

## Cambios requeridos

### Dashboard principal gerencia

Mantener:
- Acumulado compañía en pesos.
- Tendencia %.

Corregir/agregar:
- CCC compradores mes total.
- CCC compradores mes por segmento:
  - Tradicional
  - Autoservicio
  - On Premise / Vinoteca

Reemplazar el bloque de Alertas Críticas del dashboard principal por:
- 11 Titulares por marca acumulados en el mes.
- Mostrar marca y cantidad acumulada.
- Si existe denominador confiable, mostrar cobertura/cumplimiento.

Ranking de vendedores:
- Revisar qué significa “S/C”.
- Si significa sin cargo, quitarlo del ranking porque no se necesita ahí.

---

### Nueva solapa lateral: Planes Autoservicios

Crear una solapa nueva llamada:

Planes Autoservicios

Debe mostrar:
- Clientes autoservicios con planes.
- Venta acumulada del mes por cliente.
- Cantidad de sin cargos enviados.
- Detalle de producto enviado en sin cargo.
- Si no hay fuente confiable, indicar qué archivo/fuente falta.

V3 no debe aparecer con autoservicios.

---

### Solapa Alertas

Mover alertas fuera del dashboard principal.

En la solapa Alertas mostrar:
- Código de cliente + nombre.
- Top 10 clientes más relevantes de cualquier día de visita.
- Resumen del día de preventa.
- Listado completo abajo para revisión.

El código de cliente debe aparecer antes del nombre.

---

### Vista gerencia por vendedores / segunda vista

Quitar alertas que no aportan.

Reemplazar por:
- Cobertura acumulada del mes por segmento para cada vendedor.

En el primer recuadro mostrar:
- Real del día anterior por vendedor.
- Apertura por segmento:
  - Tradicional
  - Autoservicio
  - On Premise / Vinoteca

V3 sin Autoservicio.

---

### Vista vendedor

En la primera pantalla del vendedor mostrar primero bloque mensual:

- Venta acumulada total en pesos.
- CCC total acumulado.
- CCC acumulado por segmento.
- 11 Titulares abiertos por marca.
- Cantidad acumulada por marca.

Debajo mostrar bloque zona/día de matinal:

- Zona de visita del día.
- Venta real/relevante de esa zona.
- CCC de esa zona.
- CCC por segmento de esa zona.
- 11 titulares de esa zona por marca.

Mantener:
- Mi Plan
- Ruta
- KPIs
- Alertas

---

## Fuentes a auditar

Leer y auditar antes de editar:

- server_orbit.py
- PAV MATINAL PE_A FLOR/portal.html
- AGENTS.md
- 00_OBSIDIAN_ORBIT/REGLAS_NEGOCIO_PAV.md
- 00_OBSIDIAN_ORBIT/MAPA_DATOS_PAV.md
- 04_DATASETS_ORBIT/mod_volumen_vendedor.csv
- 04_DATASETS_ORBIT/mod_ccc_segmento.csv
- 04_DATASETS_ORBIT/mod_11_titulares.csv
- 04_DATASETS_ORBIT/clientes_dia.csv
- 04_DATASETS_ORBIT/mod_clientes_11t_10.csv
- 04_DATASETS_ORBIT/mod_alertas_descuentos.csv
- 04_DATASETS_ORBIT/mod_gastos_accion.csv
- 04_DATASETS_ORBIT/mod_inversion_desc.csv
- 04_DATASETS_ORBIT/mod_reintegros_ctrl.csv
- 04_DATASETS_ORBIT/mod_eficiencia_desc.csv
- 01_INPUTS/ventas.csv
- 01_INPUTS/resultado.xlsx
- orbit.db

---

## Entregable Etapa 1

No editar todavía.

Primero entregar:

1. Qué datos ya existen.
2. Qué datos faltan.
3. Qué archivos tocarías.
4. Qué endpoints crearías o corregirías.
5. Qué pantallas modificarías.
6. Qué métricas tienen fuente confiable.
7. Qué métricas no tienen fuente confiable.
8. Riesgos.
9. Plan de implementación por etapas.
10. Validaciones concretas.

Esperar aprobación antes de modificar archivos.

---

## Restricciones

- No tocar LEGACY.
- No tocar CSV/XLSX como solución manual.
- No modificar 01_INPUTS ni 02_HISTORY.
- No modificar 06_APP_DATA salvo lectura.
- No hacer commit.
- No usar datos mock.
- No usar nombres final/final2/corregido.
- Validar backend con endpoints reales.
- Validar frontend visualmente.
- Después de implementar, mostrar diff solo de archivos tocados.

---

## Validación esperada después de implementar

Gerencia:
- Dashboard muestra acumulado, tendencia, CCC total y por segmento.
- Dashboard muestra 11 titulares por marca, no alertas.
- Existe solapa Planes Autoservicios.
- Alertas muestra código + nombre de cliente.
- Ranking no muestra S/C si no aporta.

Vendedor:
- Inicio muestra acumulado mensual.
- Inicio muestra zona/día separado.
- V3 no muestra Autoservicio.
- Mi Plan sigue funcionando.

