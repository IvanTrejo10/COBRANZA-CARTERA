# -*- coding: utf-8 -*-
"""
Motor de BASE DÍAS (extracción a nivel base de datos) + COMPARATIVO de archivos.

- Extracción: corre los queries de datos_basedias.py directo en las bases,
  con la fecha de corte que se elija (igual que cobranza). Los archivos se
  generan en memoria para descargarse desde la página.
- Comparativo: valida que dos archivos (por ejemplo, el descargado de la
  página vs el generado por base de datos) tengan los MISMOS registros y que
  cada registro tenga la MISMA información, y reporta cualquier diferencia.
"""
import io
import re
import unicodedata

import pandas as pd

import datos_basedias as DBD
import procesos as pr


def _noop(*args, **kwargs):
    pass


# ==========================================================
# EXTRACCIÓN A NIVEL BASE DE DATOS
# ==========================================================
def servidor_configurado(servidor):
    """False si el servidor todavía tiene datos PENDIENTE_ por llenar."""
    return not any('PENDIENTE' in str(servidor.get(campo, '')) for campo in ('host', 'db'))


def extraer_base_dias(servidor, fecha, usuario, contrasena):
    """Corre el query de una marca para la fecha elegida y regresa el DataFrame."""
    from urllib.parse import quote_plus
    from sqlalchemy import create_engine, text

    if not servidor_configurado(servidor):
        raise ValueError(
            f"Falta configurar el servidor de {servidor['nombre']} en datos_basedias.py "
            "(campos marcados con PENDIENTE)."
        )

    sql = DBD.QUERIES_BASE_DIAS[servidor['query']]
    # Se codifican usuario/contraseña por si traen caracteres especiales (/, #, =, @)
    usuario = quote_plus(servidor.get('usuario') or usuario)
    contrasena = quote_plus(servidor.get('contrasena') or contrasena)

    if servidor['motor'] == 'mysql':
        engine = create_engine(f"mysql+pymysql://{usuario}:{contrasena}@{servidor['host']}/{servidor['db']}")
        with engine.connect() as conn:
            conn.execute(text("SET @FechaCorte = :fecha"), {"fecha": fecha})
            df = pd.read_sql(text(sql), conn)
        engine.dispose()
    elif servidor['motor'] == 'sqlserver':
        engine = create_engine(f"mssql+pymssql://{usuario}:{contrasena}@{servidor['host']}/{servidor['db']}")
        with engine.connect() as conn:
            df = pd.read_sql(text(sql.replace('__FECHA__', fecha)), conn)
        engine.dispose()
    else:
        raise ValueError(f"Motor no soportado: {servidor['motor']}")
    return df


def proceso_base_dias(fecha, marcas=None, usuario=None, contrasena=None, log=_noop, avance=_noop):
    """Corre Base Días para las marcas elegidas. Regresa (resultados, conteos).

    resultados: dict {marca: DataFrame}
    conteos:    lista de dicts para la tabla de seguimiento por base.
    """
    usuario = usuario or pr.DB_USER
    contrasena = contrasena or pr.DB_PASSWORD
    servidores = [s for s in DBD.SERVIDORES_BASE_DIAS if (marcas is None or s['nombre'] in marcas)]
    resultados, conteos = {}, []
    total = max(len(servidores), 1)
    for i, s in enumerate(servidores):
        if not servidor_configurado(s):
            conteos.append({"Base": s['nombre'], "Registros": 0,
                            "Estado": "⚠️ Falta configurar el servidor en datos_basedias.py"})
            log(f"⚠️ **{s['nombre']}**: falta configurar el servidor (datos_basedias.py).")
            avance((i + 1) / total)
            continue
        log(f"🔌 Conectando a **{s['nombre']}** ({s['host']})...")
        try:
            df = extraer_base_dias(s, fecha, usuario, contrasena)
            resultados[s['nombre']] = df
            conteos.append({"Base": s['nombre'], "Registros": len(df), "Estado": "✅ OK"})
            log(f"　　✅ {len(df):,} registros descargados")
            if df.empty:
                log("　　⚠️ Ojo: 0 registros — puede que aún no exista el cierre de esa fecha.")
        except Exception as e:
            conteos.append({"Base": s['nombre'], "Registros": 0, "Estado": f"❌ {e}"})
            log(f"　　❌ ERROR: {e}")
        avance((i + 1) / total)
    return resultados, conteos


def nombre_archivo(servidor_o_marca, fecha):
    """Nombre de archivo por marca (sin extensión), como los de la página."""
    if isinstance(servidor_o_marca, dict):
        plantilla = servidor_o_marca['archivo']
    else:
        plantilla = next((s['archivo'] for s in DBD.SERVIDORES_BASE_DIAS
                          if s['nombre'] == servidor_o_marca), 'Base_Dias_{fecha}')
    return plantilla.format(fecha=fecha)


def csv_bytes(df):
    """CSV en memoria con BOM (utf-8-sig) para que Excel respete los acentos."""
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding='utf-8-sig')
    return buf.getvalue()


def kpis_base_dias(df):
    """Sumas rápidas para las tarjetas (solo columnas que existan)."""
    kpis = {}
    for etiqueta, columna in [("💰 Total", "Total"), ("🔴 Vencido", "Vencido"),
                              ("🟠 Exigible", "Exigible"), ("🟢 Vigente", "Vigente")]:
        if columna in df.columns:
            kpis[etiqueta] = pd.to_numeric(df[columna], errors="coerce").sum()
    return kpis


# ==========================================================
# COMPARATIVO DE ARCHIVOS
# ==========================================================
_VACIOS_TXT = {"", "nan", "none", "null", "na", "n/a"}


def _sin_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto))
                   if unicodedata.category(c) != 'Mn')


def _canon_columna(nombre):
    """Nombre canónico de columna: sin acentos, minúsculas, espacios colapsados."""
    limpio = _sin_acentos(nombre).strip().lower()
    return re.sub(r'\s+', ' ', limpio)


def _numero(valor):
    """Intenta convertir a número tolerando comas de miles, $, (), vacíos."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and valor != valor:
            return None
        return float(valor)
    txt = str(valor).strip()
    if txt.lower() in _VACIOS_TXT:
        return None
    negativo = txt.startswith('(') and txt.endswith(')')
    if negativo:
        txt = txt[1:-1]
    txt = re.sub(r'[^0-9,.\-+]', '', txt)
    if txt.strip('+-.,') == '':
        return None
    if ',' in txt and '.' in txt:
        if txt.rfind(',') > txt.rfind('.'):
            txt = txt.replace('.', '').replace(',', '.')
        else:
            txt = txt.replace(',', '')
    elif ',' in txt:
        if re.match(r'^[-+]?\d{1,3}(,\d{3})+(\.\d+)?$', txt):
            txt = txt.replace(',', '')
        else:
            txt = txt.replace(',', '.')
    try:
        n = float(txt)
    except ValueError:
        return None
    return -abs(n) if negativo else n


def _texto_norm(valor):
    """Texto normalizado para comparar: sin espacios extremos ni dobles."""
    if valor is None or (isinstance(valor, float) and valor != valor):
        return ''
    txt = str(valor).strip()
    if txt.lower() in _VACIOS_TXT:
        return ''
    if re.fullmatch(r'-?\d+\.0', txt):  # 123.0 -> 123 (Excel/pandas)
        txt = txt[:-2]
    return re.sub(r'\s+', ' ', txt)


def _valores_iguales(va, vb, tolerancia):
    na, nb = _numero(va), _numero(vb)
    if na is not None and nb is not None:
        return abs(na - nb) <= tolerancia
    return _texto_norm(va) == _texto_norm(vb)


def leer_archivo_tabla(fuente, nombre=None):
    """Lee un archivo .csv / .xlsx / .xls subido o en disco y regresa el DataFrame."""
    nombre = str(nombre or getattr(fuente, 'name', fuente))
    if hasattr(fuente, 'getvalue'):
        fuente = io.BytesIO(fuente.getvalue())
    if nombre.lower().endswith(('.xlsx', '.xls', '.xlsb')):
        engine = 'pyxlsb' if nombre.lower().endswith('.xlsb') else None
        df = pd.read_excel(fuente, engine=engine)
    else:
        try:
            df = pd.read_csv(fuente, sep=None, engine='python', encoding='utf-8-sig', dtype=str)
        except UnicodeDecodeError:
            if hasattr(fuente, 'seek'):
                fuente.seek(0)
            df = pd.read_csv(fuente, sep=None, engine='python', encoding='latin-1', dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df


_LLAVES_PREFERIDAS = ['numero', 'id socio', 'id_socio', 'no. socio', 'numero socio']


def _detectar_llave(cols_canon_a, cols_canon_b):
    comunes = [c for c in cols_canon_a if c in cols_canon_b]
    for cand in _LLAVES_PREFERIDAS:
        if cand in comunes:
            return cand
    return None


def comparar_tablas(df_a, df_b, etiqueta_a="Archivo 1", etiqueta_b="Archivo 2",
                    llave=None, tolerancia=0.01):
    """Compara dos tablas registro por registro y campo por campo.

    Regresa un dict con:
      resumen        : conteos generales (registros, comunes, faltantes, diferencias)
      solo_a, solo_b : DataFrames con los registros que solo están en un lado
      diferencias    : DataFrame Llave | Columna | <etiqueta_a> | <etiqueta_b>
      columnas_solo_a / columnas_solo_b : columnas sin pareja en el otro archivo
      llave_usada    : columna(s) usadas como llave
      avisos         : lista de avisos (llaves duplicadas, etc.)
      identicos      : True si mismos registros y misma información
    """
    avisos = []
    a, b = df_a.copy(), df_b.copy()

    # Emparejar columnas por nombre canónico (sin acentos/mayúsculas/espacios)
    canon_a = {_canon_columna(c): c for c in a.columns}
    canon_b = {_canon_columna(c): c for c in b.columns}
    comunes = [c for c in canon_a if c in canon_b]
    columnas_solo_a = [canon_a[c] for c in canon_a if c not in canon_b]
    columnas_solo_b = [canon_b[c] for c in canon_b if c not in canon_a]

    # Llave
    llave_canon = _canon_columna(llave) if llave else _detectar_llave(canon_a, canon_b)
    if llave_canon and llave_canon in comunes:
        nombre_llave_a, nombre_llave_b = canon_a[llave_canon], canon_b[llave_canon]
        serie_a = a[nombre_llave_a].map(_texto_norm)
        serie_b = b[nombre_llave_b].map(_texto_norm)
        llave_usada = nombre_llave_a
    else:
        serie_a = pd.Series(range(len(a)), index=a.index).astype(str)
        serie_b = pd.Series(range(len(b)), index=b.index).astype(str)
        llave_usada = "(número de fila)"
        avisos.append("No se encontró una columna llave en común (Numero / ID Socio); "
                      "se comparó por posición de fila.")

    # Si la llave se repite, se numeran las repeticiones en orden (1, 2, ...)
    if serie_a.duplicated().any() or serie_b.duplicated().any():
        dup = int(serie_a.duplicated().sum() + serie_b.duplicated().sum())
        avisos.append(f"La llave se repite en {dup} fila(s); las repetidas se comparan en el orden en que aparecen.")
        serie_a = serie_a + serie_a.groupby(serie_a).cumcount().map(lambda n: '' if n == 0 else f' ({n+1})')
        serie_b = serie_b + serie_b.groupby(serie_b).cumcount().map(lambda n: '' if n == 0 else f' ({n+1})')

    a.index, b.index = serie_a, serie_b
    llaves_a, llaves_b = set(serie_a), set(serie_b)
    solo_a = a.loc[sorted(llaves_a - llaves_b)]
    solo_b = b.loc[sorted(llaves_b - llaves_a)]
    llaves_comunes = sorted(llaves_a & llaves_b)

    # Comparación campo por campo en las columnas comunes
    difs = []
    a_com, b_com = a.loc[llaves_comunes], b.loc[llaves_comunes]
    for canon in comunes:
        col_a, col_b = canon_a[canon], canon_b[canon]
        va, vb = a_com[col_a], b_com[col_b]
        for k, x, y in zip(llaves_comunes, va.tolist(), vb.tolist()):
            if not _valores_iguales(x, y, tolerancia):
                difs.append({"Llave": k, "Columna": col_a, etiqueta_a: x, etiqueta_b: y})
    diferencias = pd.DataFrame(difs, columns=["Llave", "Columna", etiqueta_a, etiqueta_b])
    if not diferencias.empty:
        diferencias = diferencias.sort_values(["Llave", "Columna"]).reset_index(drop=True)

    identicos = solo_a.empty and solo_b.empty and diferencias.empty and not columnas_solo_a and not columnas_solo_b
    resumen = {
        f"Registros {etiqueta_a}": len(a),
        f"Registros {etiqueta_b}": len(b),
        "Registros en común": len(llaves_comunes),
        f"Solo en {etiqueta_a}": len(solo_a),
        f"Solo en {etiqueta_b}": len(solo_b),
        "Columnas comparadas": len(comunes),
        "Celdas con diferencia": len(diferencias),
        "Registros con alguna diferencia": int(diferencias["Llave"].nunique()) if not diferencias.empty else 0,
    }
    return {
        "resumen": resumen, "solo_a": solo_a.reset_index(names="Llave"),
        "solo_b": solo_b.reset_index(names="Llave"), "diferencias": diferencias,
        "columnas_solo_a": columnas_solo_a, "columnas_solo_b": columnas_solo_b,
        "llave_usada": llave_usada, "avisos": avisos, "identicos": identicos,
        "etiquetas": (etiqueta_a, etiqueta_b),
    }


def reporte_comparativo_bytes(resultado):
    """Excel del comparativo: Resumen + Diferencias + Solo en A + Solo en B."""
    et_a, et_b = resultado["etiquetas"]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        filas = [{"Concepto": k, "Valor": v} for k, v in resultado["resumen"].items()]
        filas.append({"Concepto": "Llave usada", "Valor": resultado["llave_usada"]})
        if resultado["columnas_solo_a"]:
            filas.append({"Concepto": f"Columnas solo en {et_a}", "Valor": ", ".join(resultado["columnas_solo_a"])})
        if resultado["columnas_solo_b"]:
            filas.append({"Concepto": f"Columnas solo en {et_b}", "Valor": ", ".join(resultado["columnas_solo_b"])})
        for aviso in resultado["avisos"]:
            filas.append({"Concepto": "Aviso", "Valor": aviso})
        filas.append({"Concepto": "Resultado",
                      "Valor": "✅ IDÉNTICOS: mismos registros y misma información"
                               if resultado["identicos"] else "❌ HAY DIFERENCIAS (ver pestañas)"})
        pd.DataFrame(filas).to_excel(writer, sheet_name="Resumen", index=False)
        resultado["diferencias"].to_excel(writer, sheet_name="Diferencias", index=False)
        resultado["solo_a"].to_excel(writer, sheet_name=f"Solo en {et_a}"[:31], index=False)
        resultado["solo_b"].to_excel(writer, sheet_name=f"Solo en {et_b}"[:31], index=False)
        for hoja in writer.sheets.values():
            hoja.set_column(0, 40, 22)
    return buf.getvalue()
