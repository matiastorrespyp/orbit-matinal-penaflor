# -*- coding: utf-8 -*-
"""
MOTOR AUTORITATIVO DEL PADRÓN DE CLIENTES — ORBIT Matinal Peñaflor
==================================================================

Una sola definición de "qué cliente pertenece a qué cartera". Todo módulo que cargue
`01_INPUTS/clientes.xlsx` (motor de datasets, server, motor 11T, preventa) resuelve los
duplicados por acá. No repetir la regla en ningún otro archivo.

EL PROBLEMA QUE RESUELVE
------------------------
El ERP exporta algunos clientes DOS VECES, uno por cada ruta a la que quedaron cargados.
Hasta 2026-08-05 los tres cargadores hacían `drop_duplicates(keep="first")`: se quedaban
con la fila que el Excel trajera primero, o sea con un vendedor elegido por el orden de
exportación. En la práctica los 10 clientes duplicados V3/V8 caían todos en V3 — la
cartera equivocada — y con eso se movían cobertura, 11T, KPI y reportes por vendedor.

LA REGLA
--------
1. La clave es el CÓDIGO estable del cliente, normalizado (texto/numérico, espacios,
   sufijo `.0`). Los ceros a la izquierda NO son significativos: en `clientes.xlsx` la
   columna `Codigo` es entera.
2. Si el mismo cliente aparece en V3 y V8 → **prevalece V8** (decisión comercial
   2026-08-05: la cartera autoritativa de esos clientes es la de Vanesa Alvarez).
   Se conserva la FILA ENTERA de V8 — incluidos `DiasVisita` y `Orden`, que difieren
   entre las dos filas en los clientes 1392 y 1424.
3. Si el mismo cliente aparece dos veces con el MISMO vendedor → se deja un registro y
   se informa. No hay nada que decidir.
4. Cualquier otra colisión entre vendedores → **no se resuelve automáticamente**: se
   conserva la primera fila (statu quo, para no romper la carga) y se reporta como
   excepción para revisión manual. No inventamos a quién pertenece el cliente.

Lo que esta regla NO hace: no toca ventas, ni facturas, ni el `CodVendedor` de ningún
comprobante. Solo define la PERTENENCIA COMERCIAL del cliente. Una venta facturada por
V20 Depósito o por V3 sigue registrada como está; lo que cambia es a qué cartera se le
imputa el cliente cuando la métrica usa vendedor de cartera.

POR QUÉ LA REGLA VIVE ACÁ Y NO EN EL EXCEL
------------------------------------------
`01_INPUTS/clientes.xlsx` se re-exporta del ERP y el cierre diario lo publica
(`git add "01_INPUTS/clientes.xlsx"` en CIERRE_DIA_ORBIT.bat). Editar el archivo a mano
duraría hasta el próximo drop. La corrección de fondo es en el ERP; mientras tanto esta
regla es la defensa que sobrevive a cada exportación. No hay ninguna lista de códigos
hardcodeada: la regla es por PAR DE VENDEDORES, así que si mañana el ERP duplica otro
cliente entre V3 y V8 queda resuelto igual, y si lo duplica entre otros dos vendedores
salta como excepción.
"""
from __future__ import annotations

import pandas as pd

#: Precedencia de cartera para colisiones conocidas: {frozenset(vendedores): ganador}.
#: Cada entrada es una decisión comercial explícita, no una heurística.
#: 2026-08-05 — V3/V8: la cartera autoritativa corresponde a V8.
PRECEDENCIA_CARTERA = {
    frozenset({3, 8}): 8,
}

#: Tipos de incidencia que devuelve `resolver_padron`.
DUP_MISMO_VENDEDOR = "DUPLICADO_MISMO_VENDEDOR"
DUP_RESUELTO = "DUPLICADO_RESUELTO_POR_PRECEDENCIA"
DUP_SIN_REGLA = "DUPLICADO_SIN_REGLA_REVISAR"

_COLS_INCIDENCIA = ["tipo", "cliente_id", "cliente_nombre", "vendedores",
                    "vendedor_resuelto", "apariciones", "origen", "detalle"]


def normalizar_codigo_cliente(valor):
    """'1294', ' 1294 ', '1294.0', 1294.0 → 1294. None si no es numérico.

    Los ceros a la izquierda no son significativos: `Codigo` es entero en el padrón y en
    la columna `Cliente` de ventas, así que normalizar a int no pierde información."""
    n = pd.to_numeric(str(valor).strip(), errors="coerce")
    return None if pd.isna(n) else int(n)


def normalizar_codigo_vendedor(valor):
    """'V8', '8', '08', '8.0', 8.0, ' v8 ' → 8. None si no hay número."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    s = str(valor).strip().upper().replace("V", "").split(".")[0]
    digitos = "".join(ch for ch in s if ch.isdigit())
    return int(digitos) if digitos else None


def resolver_padron(df, col_codigo="Codigo", col_vendedor="codven",
                    col_nombre=None, origen=""):
    """Deja UNA fila por cliente aplicando la precedencia de cartera.

    Determinístico: el resultado no depende del orden de las filas del Excel.

    Parámetros
    ----------
    df : padrón crudo.
    col_codigo / col_vendedor : nombres de las columnas de código de cliente y de vendedor.
    col_nombre : columna de razón social, sólo para enriquecer el reporte de incidencias.
    origen : etiqueta del módulo que llama, para que el aviso diga de dónde salió.

    Devuelve
    --------
    (df_resuelto, incidencias) — `incidencias` es un DataFrame con `_COLS_INCIDENCIA`,
    vacío si no hubo duplicados.
    """
    vacio = pd.DataFrame(columns=_COLS_INCIDENCIA)
    if df is None or len(df) == 0 or col_codigo not in df.columns:
        return df, vacio

    d = df.copy()
    # dtype="object" a propósito: con `.map()` pelado, un solo NaN en la columna hace que
    # pandas re-castee la serie a float64 y los códigos vuelven a ser 3.0 / 8.0. Eso
    # ensuciaba el reporte ("V3.0/V8.0") y dejaba la clave de PRECEDENCIA_CARTERA
    # dependiendo de que float e int hasheen igual.
    _cod = pd.Series([normalizar_codigo_cliente(v) for v in d[col_codigo]],
                     index=d.index, dtype="object")
    _ven = pd.Series([normalizar_codigo_vendedor(v) for v in d[col_vendedor]]
                     if col_vendedor in d.columns else [None] * len(d),
                     index=d.index, dtype="object")

    dup_mask = _cod.notna() & _cod.duplicated(keep=False)
    dup_mask = dup_mask.astype(bool)
    if not dup_mask.any():
        return d, vacio

    if col_nombre is None:
        col_nombre = next((c for c in d.columns
                           if str(c).lower().replace("_", "") in
                           ("razonsocial", "nombre", "cliente", "clientenombre")), None)

    filas_a_tirar, incidencias = [], []
    for cod, idx in _cod[dup_mask].groupby(_cod[dup_mask]).groups.items():
        idx = list(idx)
        vendedores = [_ven.get(i) for i in idx]
        unicos = {v for v in vendedores if v is not None}
        nombre = str(d.loc[idx[0], col_nombre]) if col_nombre else ""

        if len(unicos) <= 1:
            ganador = next(iter(unicos), None)
            elegido = idx[0]
            tipo = DUP_MISMO_VENDEDOR
            detalle = "misma cartera cargada dos veces: se conserva un registro"
        elif frozenset(unicos) in PRECEDENCIA_CARTERA:
            ganador = PRECEDENCIA_CARTERA[frozenset(unicos)]
            # Se conserva la fila ENTERA del ganador (DiasVisita, Orden, Ruta…).
            elegido = next(i for i in idx if _ven.get(i) == ganador)
            tipo = DUP_RESUELTO
            detalle = (f"precedencia de cartera {'/'.join('V%d' % v for v in sorted(unicos))}"
                       f" -> V{ganador}")
        else:
            ganador = _ven.get(idx[0])
            elegido = idx[0]
            tipo = DUP_SIN_REGLA
            detalle = ("colision entre vendedores sin regla de precedencia: se conserva la "
                       "primera fila y queda para revision manual (no se resuelve solo)")

        filas_a_tirar += [i for i in idx if i != elegido]
        incidencias.append({
            "tipo": tipo,
            "cliente_id": int(cod),
            "cliente_nombre": nombre,
            "vendedores": "/".join(f"V{v}" for v in sorted(unicos)) if unicos else "",
            "vendedor_resuelto": f"V{ganador}" if ganador is not None else "",
            "apariciones": len(idx),
            "origen": origen,
            "detalle": detalle,
        })

    inc = pd.DataFrame(incidencias, columns=_COLS_INCIDENCIA)
    return d.drop(index=filas_a_tirar), inc


def avisar_incidencias(inc, origen=""):
    """Imprime el resumen de duplicados. Las colisiones SIN regla se marcan aparte: son
    las que hay que mirar a mano, no se pueden perder entre las resueltas."""
    if inc is None or inc.empty:
        return
    pref = f"[{origen}] " if origen else ""
    res = inc[inc["tipo"] == DUP_RESUELTO]
    if not res.empty:
        det = ", ".join(f"#{r.cliente_id} {r.vendedores}->{r.vendedor_resuelto}"
                        for r in res.itertuples())
        print(f"  {pref}padron: {len(res)} cliente(s) duplicado(s) resuelto(s) por "
              f"precedencia de cartera: {det}")
    mismo = inc[inc["tipo"] == DUP_MISMO_VENDEDOR]
    if not mismo.empty:
        print(f"  {pref}padron: {len(mismo)} cliente(s) cargado(s) dos veces con el mismo "
              f"vendedor: {sorted(mismo['cliente_id'].tolist())} — se dejo un registro.")
    sin = inc[inc["tipo"] == DUP_SIN_REGLA]
    if not sin.empty:
        det = ", ".join(f"#{r.cliente_id} ({r.vendedores})" for r in sin.itertuples())
        print(f"  {pref}[REVISAR] padron: {len(sin)} colision(es) entre vendedores SIN regla "
              f"de precedencia: {det}. No se resolvieron automaticamente — corregir la "
              f"cartera en el ERP o agregar la regla en motor_padron.PRECEDENCIA_CARTERA.")
