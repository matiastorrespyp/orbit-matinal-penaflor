# Ajustar propuesta final de REGENERAR_DATOS_ORBIT.bat

Usá la skill orbit-pav-guardian.

No apruebo todavía la creación del BAT.

La propuesta está casi lista, pero faltan 3 correcciones obligatorias antes de crear REGENERAR_DATOS_ORBIT.bat.

## Corrección 1 — Excel bloqueado

Antes del backup y antes de ejecutar cualquier script, el BAT debe verificar si está bloqueado:

03_OUTPUTS\MATINAL_PENA_V42.xlsx

Si está abierto o bloqueado, debe:

- mostrar ERROR,
- escribir ERROR en log,
- terminar con exit /b 1.

Objetivo:
Si el Excel está abierto, cortar antes de correr el motor.

## Corrección 2 — Outputs críticos

Actualmente, si falta un output crítico, el BAT cierra como ADVERTENCIA.

Eso no sirve.

Si falta cualquiera de estos outputs:

- 03_OUTPUTS\MATINAL_PENA_V42.xlsx
- 04_DATASETS_ORBIT\clientes_dia.csv
- 04_DATASETS_ORBIT\mod_volumen_vendedor.csv
- 04_DATASETS_ORBIT\mod_ccc_segmento.csv
- 04_DATASETS_ORBIT\mod_11_titulares.csv
- 04_DATASETS_ORBIT\mod_alertas_descuentos.csv
- 04_DATASETS_ORBIT\mod_gastos_accion.csv

Entonces debe:

- mostrar ERROR,
- escribir ERROR en log,
- terminar con exit /b 1.

No debe cerrar como “regeneración completa con advertencias”.

## Corrección 3 — Backup de CSVs previos

Si no existen CSVs previos en:

04_DATASETS_ORBIT\*.csv

el backup no debe fallar.

Debe registrar:

“no existían CSVs previos”

y seguir.

## Restricciones

No crear el archivo todavía.

No modificar archivos.
No crear REGENERAR_DATOS_ORBIT.bat.
No ejecutar scripts.
No commitear.
No tocar 01_INPUTS.

## Entregable

Mostrame nuevamente el contenido completo final propuesto de:

REGENERAR_DATOS_ORBIT.bat

con estas 3 correcciones incorporadas.

Solo propuesta en pantalla.
No crear archivo.
No ejecutar nada.