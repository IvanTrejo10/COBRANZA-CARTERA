# -*- coding: utf-8 -*-
"""
Motor de procesos de COBRANZA (LATAM + PRESICO MX) y CARTERA (LATAM + MÉXICO).
Lógica pura, sin Streamlit y sin rutas locales: los archivos se generan en memoria
(bytes) para descargarse desde la web. Los queries viven en los módulos datos_* y
están pegados TAL CUAL vienen de Power Query.
"""
import io
import re
import numpy as np
import pandas as pd
from xlsxwriter.utility import xl_range

import datos_cobranza_latam as DL
import datos_cobranza_presico as DP
import datos_cartera as DC

# Credenciales por defecto (en Streamlit Cloud se pueden sobreescribir con Secrets)
DB_USER = "jtrejol"
DB_PASSWORD = "49vakqO4ox15"


def _noop(*args, **kwargs):
    pass


def decodificar_query_m(query_m):
    """Convierte los códigos de Power Query a caracteres reales: #(lf) -> salto de línea, #(tab) -> tab."""
    return query_m.replace("#(lf)", "\n").replace("#(tab)", "\t")


def _engine(host, db, usuario, contrasena):
    from sqlalchemy import create_engine
    return create_engine(f"mysql+pymysql://{usuario}:{contrasena}@{host}/{db}")


# ==========================================================
# FUENTES COMUNES: Estructura (Google Sheets) y Tipo de Cambio
# ==========================================================
def cargar_estructura():
    """Estructura publicada como CSV (todo como texto)."""
    return pd.read_csv(DL.URL_ESTRUCTURA, dtype=str, encoding="utf-8")


def cargar_tipo_cambio(fuente):
    """TIPO DE CAMBIO.xlsx -> Hoja1 (PAIS, ID Pais, TIPO CAMBIO). `fuente` puede ser ruta o archivo subido."""
    df = pd.read_excel(fuente, sheet_name="Hoja1")
    df = df.dropna(subset=["PAIS"])
    df["PAIS"] = df["PAIS"].astype(str)
    df["TIPO CAMBIO"] = pd.to_numeric(df["TIPO CAMBIO"], errors="coerce")
    return df


def leer_venta_cartera(fuente, hoja):
    """Lee Venta Cartera tomando solo Llave y Concepto. Acepta .xlsx o .xlsb
    (el binario pesa menos para GitHub y se lee con el motor pyxlsb), y puede ser
    ruta del repositorio o archivo subido (se re-lee desde el inicio cada vez)."""
    nombre = str(getattr(fuente, "name", fuente))
    engine = "pyxlsb" if nombre.lower().endswith(".xlsb") else None
    if hasattr(fuente, "getvalue"):
        fuente = io.BytesIO(fuente.getvalue())
    return pd.read_excel(fuente, sheet_name=hoja, usecols=["Llave", "Concepto"], engine=engine)


# ==========================================================
# COBRANZA LATAM (mismos pasos del Power Query / script local)
# ==========================================================
def _extraer_cobranza_latam(servidor, fecha, usuario, contrasena):
    from sqlalchemy import text
    engine = _engine(servidor["host"], servidor["db"], usuario, contrasena)
    sql = decodificar_query_m(DL.RAW_QUERIES[servidor["nombre"]])
    with engine.connect() as conn:
        conn.execute(text("SET @Date = :fecha"), {"fecha": fecha})
        df = pd.read_sql(text(sql), conn)
    engine.dispose()
    return df


def _transformar_cobranza_latam(df, unidad, pais):
    df = df.copy()
    df["numero_clientes_dia"] = pd.to_numeric(df["numero_clientes_dia"], errors="coerce")
    df["numero_clientes_dia_pagado"] = pd.to_numeric(df["numero_clientes_dia_pagado"], errors="coerce")
    df["Unidad de Negocio"] = unidad
    df["Pais"] = pais
    df["Faltas"] = df["numero_clientes_dia"] - df["numero_clientes_dia_pagado"]
    df = df[DL.COLUMNAS_POR_UNIDAD].copy()
    df["dbc_cliente limpio"] = df["dbc_cliente_id"].where(df["dbc_cliente_id"].notna(), df["coordinadora_id"])
    return df


def construir_agrupado_latam(df, df_estructura, df_tipo_cambio):
    df = df.copy()

    # Ruta: MAYÚSCULAS, recortado y limpieza (Text.Upper, Text.Trim, Text.Clean)
    df["Ruta"] = df["Ruta"].str.upper().str.strip()
    df["Ruta"] = df["Ruta"].str.replace(r"[\x00-\x1F\x7F-\x9F]", "", regex=True)

    # Combinar con Estructura (LeftOuter por Ruta)
    df = df.merge(df_estructura[["Ruta", "Subdireccion", "Sucursal", "Zona "]], on="Ruta", how="left")
    df = df.rename(columns={"Zona ": "Zona-Reg"})

    # Combinar con Tipo Cambio (LeftOuter, Pais -> PAIS)
    df = df.merge(
        df_tipo_cambio[["PAIS", "TIPO CAMBIO"]].rename(columns={"TIPO CAMBIO": "TIPO CAMBIO.1"}),
        left_on="Pais", right_on="PAIS", how="left"
    )

    # Columnas convertidas a moneda común
    for col_original, col_nueva in DL.COLUMNAS_TIPO_CAMBIO:
        df[col_original] = pd.to_numeric(df[col_original], errors="coerce")
        df[col_nueva] = df[col_original] * df["TIPO CAMBIO.1"]

    df = df[DL.COLUMNAS_SELECCION_AGRUPADO].rename(columns=DL.RENOMBRES_FINALES)

    # Columnas condicionales NW
    df["Cobranza_con_atrasoNW"] = np.where(
        df["PAGO COBRANZA EN ATRASO"] > df["COBRANZA EN ATRASO"],
        df["PAGO COBRANZA EN ATRASO"], df["COBRANZA EN ATRASO"]
    )
    df["COBRANZA_DEL_DIA_NW"] = np.where(
        df["pago_cobranza_dia"] > df["cobranza_del_dia"],
        df["pago_cobranza_dia"], df["cobranza_del_dia"]
    )
    df["Dif_Cob_dia vs Pago"] = np.where(
        df["Dif. BOBRANZA DEL DIA vs PAGADO"] < 0, 0, df["Dif. BOBRANZA DEL DIA vs PAGADO"]
    )
    df["TIPO_DESEMBOLSO_NUEVO_NW"] = df["TIPO_DESEMBOLSO_NUEVO"].where(
        ~((df["ENTREGADO_CLIENTE"] == 0) & (df["ENTREGADO_COORDINADORA"] > 0)),
        "Prestamo Personal"
    )
    return df[DL.ORDEN_FINAL]


def proceso_cobranza_latam(fecha, df_estructura, df_tipo_cambio,
                           usuario=None, contrasena=None, log=_noop, avance=_noop):
    """Corre la cobranza LATAM completa para una fecha. Regresa (df_final, conteos)."""
    usuario = usuario or DB_USER
    contrasena = contrasena or DB_PASSWORD
    dfs, conteos = [], []
    total = len(DL.SERVIDORES_COBRANZA)
    for i, s in enumerate(DL.SERVIDORES_COBRANZA):
        log(f"🔌 Conectando a **{s['nombre']}** ({s['pais']})...")
        try:
            df_raw = _extraer_cobranza_latam(s, fecha, usuario, contrasena)
            df_t = _transformar_cobranza_latam(df_raw, s["unidad"], s["pais"])
            dfs.append(df_t)
            conteos.append({"Base": s["nombre"], "País": s["pais"], "Registros": len(df_t), "Estado": "✅ OK"})
            log(f"　　✅ {len(df_t):,} registros descargados")
        except Exception as e:
            conteos.append({"Base": s["nombre"], "País": s["pais"], "Registros": 0, "Estado": f"❌ {e}"})
            log(f"　　❌ ERROR: {e}")
        avance((i + 1) / total)
    if not dfs:
        return None, conteos
    log("🧮 Combinando unidades y construyendo el agrupado (estructura + tipo de cambio)...")
    df = pd.concat(dfs, ignore_index=True)
    df_final = construir_agrupado_latam(df, df_estructura, df_tipo_cambio)
    log(f"📋 Agrupado final: {len(df_final):,} registros, {len(df_final.columns)} columnas.")
    return df_final, conteos


def rutas_faltantes_cobranza_latam(df_final):
    """Rutas del reporte que NO cruzaron con la Estructura (hay que agregarlas al catálogo)."""
    sin_cruce = df_final[df_final["Subdireccion"].isna()]["Ruta"].dropna().astype(str)
    return sorted(sin_cruce.unique().tolist())


def resumen_cobranza_latam(df_final):
    """Tabla de montos por País y Marca (como la vista de Power BI)."""
    cols = ["COBRANZA_DEL_DIA_NW", "Cobranza_con_atrasoNW", "pago_cobranza_dia",
            "PAGO COBRANZA EN ATRASO", "pago_adelantado", "pago_renovacion",
            "PAGO ADELANTADO EN EXTRACOBRANZA", "pago_servicio"]
    base = df_final.copy()
    base["Pais"] = base["Pais"].fillna("(sin país)")
    base["Marca"] = base["Unidad de Negocio"].fillna("(sin marca)")
    res = base.groupby(["Pais", "Marca"], dropna=False)[cols].sum().reset_index()
    res = res.sort_values(["Pais", "Marca"]).reset_index(drop=True)
    total = res[cols].sum()
    fila_total = {"Pais": "Total", "Marca": ""}
    fila_total.update(total.to_dict())
    return pd.concat([res, pd.DataFrame([fila_total])], ignore_index=True)


# ==========================================================
# COBRANZA PRESICO MX (mismos pasos del flujo NV)
# ==========================================================
RUTAS_EXCLUIDAS_COBRANZA_PRESICO = frozenset({
    "TEPATITLAN-LL-R1",
    "TALA-C-R1",
    "ZONA DE PRUEBAS-P-R1",
})


def filtrar_rutas_excluidas_presico(df):
    """Quita rutas que no deben formar parte de la cobranza PRESICO."""
    if "Ruta" not in df.columns:
        return df.copy()
    rutas_normalizadas = df["Ruta"].astype("string").str.strip().str.upper()
    return df.loc[~rutas_normalizadas.isin(RUTAS_EXCLUIDAS_COBRANZA_PRESICO)].copy()


def _extraer_cobranza_presico(servidor, fecha, usuario, contrasena):
    from sqlalchemy import text
    engine = _engine(servidor["host"], servidor["db"], usuario, contrasena)
    raw = DP.RAW_QUERIES_PRESICO[servidor["nombre"]]
    with engine.connect() as conn:
        if servidor["tipo"] == "call":
            df = pd.read_sql(text(raw.replace("__FECHA__", fecha)), conn)
        else:
            conn.execute(text("SET @Date = :fecha"), {"fecha": fecha})
            df = pd.read_sql(text(decodificar_query_m(raw)), conn)
    engine.dispose()
    return df


def transformar_cobranza_presico(df, df_estructura, limpiar_ruta=False):
    """Réplica de los pasos del flujo NV. limpiar_ruta=True solo para PRESICO MX NV."""
    df = df.copy()
    for col in DP.COLUMNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Faltas"] = df["numero_clientes_dia"] - df["numero_clientes_dia_pagado"]
    df = df[DP.COLUMNAS_SELECCION_UNIDAD].copy()
    df["dbc_cliente limpio"] = df["dbc_cliente_id"].where(df["dbc_cliente_id"].notna(), df["coordinadora_id"])
    df["dbc_cliente limpio"] = pd.to_numeric(df["dbc_cliente limpio"], errors="coerce")
    df = df.drop(columns=["Zona", "dbc_cliente_id"])
    if limpiar_ruta:
        df["Ruta"] = df["Ruta"].replace("MANZANILLO", "MANZANILLO-P-R2")
        df["Ruta"] = df["Ruta"].str.strip()
        df["Ruta"] = df["Ruta"].str.replace(r"[\x00-\x1F\x7F-\x9F]", "", regex=True)
    df = filtrar_rutas_excluidas_presico(df)
    df = df.merge(
        df_estructura[["Ruta", "Territorio", "Subdireccion", "Zona ", "Sucursal", "Base"]],
        on="Ruta", how="left"
    )
    df["Cobranza_con_atrasoNW"] = np.where(
        df["pago_saldo_devengado"] > df["saldo_devengado"],
        df["pago_saldo_devengado"], df["saldo_devengado"]
    )
    df["Cobranza_del_diaNW"] = np.where(
        df["pago_cobranza_dia"] > df["cobranza_del_dia"],
        df["pago_cobranza_dia"], df["cobranza_del_dia"]
    )
    df["Dif_Cob_dia vs Pago"] = df["Cobranza_del_diaNW"] - df["pago_cobranza_dia"]
    cond_prestamo = (df["ENTREGADO_CLIENTE"] == 0) & (df["ENTREGADO_COORDINADORA"] > 0)
    cond_nulo = (df["ENTREGADO_CLIENTE"] == 0)
    df["TIPO_DESEMBOLSO_NUEVO_NW"] = np.select(
        [cond_prestamo, cond_nulo], ["Prestamo Personal", None],
        default=df["TIPO_DESEMBOLSO_NUEVO"]
    )
    df = df.rename(columns={"Base": "Unidad de Negocio"})
    return df[DP.ORDEN_FINAL_PRESICO]


def proceso_cobranza_presico(fecha, df_estructura, usuario=None, contrasena=None, log=_noop, avance=_noop):
    """Corre la cobranza PRESICO MX completa para una fecha. Regresa (df_final, conteos)."""
    usuario = usuario or DB_USER
    contrasena = contrasena or DB_PASSWORD
    dfs, conteos = [], []
    total = len(DP.SERVIDORES_PRESICO)
    for i, s in enumerate(DP.SERVIDORES_PRESICO):
        log(f"🔌 Conectando a **{s['nombre']}**...")
        try:
            df_raw = _extraer_cobranza_presico(s, fecha, usuario, contrasena)
            df_t = transformar_cobranza_presico(df_raw, df_estructura,
                                                limpiar_ruta=(s["nombre"] == "PRESICO MX NV"))
            dfs.append(df_t)
            conteos.append({"Base": s["nombre"], "Registros": len(df_t), "Estado": "✅ OK"})
            log(f"　　✅ {len(df_t):,} registros descargados")
        except Exception as e:
            conteos.append({"Base": s["nombre"], "Registros": 0, "Estado": f"❌ {e}"})
            log(f"　　❌ ERROR: {e}")
        avance((i + 1) / total)
    if not dfs:
        return None, conteos
    df_final = pd.concat(dfs, ignore_index=True)
    log(f"📋 Combinado final: {len(df_final):,} registros, {len(df_final.columns)} columnas.")
    return df_final, conteos


def rutas_faltantes_cobranza_presico(df_final):
    """Rutas del reporte que NO cruzaron con la Estructura Presico MX."""
    sin_cruce = df_final[df_final["Territorio"].isna()]["Ruta"].dropna().astype(str)
    return sorted(sin_cruce.unique().tolist())


def resumen_cobranza_presico(df_final):
    """Tabla de montos por Unidad de Negocio (como la vista de Power BI de MX)."""
    mapa = {
        "Cobranza_del_diaNW": "Cobranza del dia",
        "Cobranza_con_atrasoNW": "Cobranza con atraso",
        "pago_cobranza_dia": "Pago Cobranza del dia",
        "pago_saldo_devengado": "Pago Cobranza con atraso",
        "pago_adelantado": "Pago Adelanto",
        "pago_renovacion": "Pago Renovacion",
        "pago_adelantado_extracobranza": "Pago Adelantado Extracobranza",
        "pago_servicio": "Pago Servicio",
    }
    base = df_final.copy()
    base["Unidad de Negocio"] = base["Unidad de Negocio"].fillna("(sin unidad)")
    res = base.groupby("Unidad de Negocio", dropna=False)[list(mapa)].sum().reset_index()
    res = res.rename(columns=mapa).sort_values("Unidad de Negocio").reset_index(drop=True)
    total = res[list(mapa.values())].sum()
    fila_total = {"Unidad de Negocio": "Total"}
    fila_total.update(total.to_dict())
    return pd.concat([res, pd.DataFrame([fila_total])], ignore_index=True)


# ==========================================================
# CARTERA (mismos pasos de extraccion_cartera.py, sin rutas locales)
# ==========================================================
COLS_FECHA_CARTERA = ["Corte", "fecha_desembolso", "fecha_finalizacion", "fecha_cambio_coordinadora"]
COL_FECHA_HORA_CARTERA = "fecha_ultimo_pago"


def _aplicar_tipos_y_orden(df, columnas_finales):
    for c in COLS_FECHA_CARTERA:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    if COL_FECHA_HORA_CARTERA in df.columns:
        df[COL_FECHA_HORA_CARTERA] = pd.to_datetime(df[COL_FECHA_HORA_CARTERA], errors="coerce")
    return df[[col for col in columnas_finales if col in df.columns]]


def proceso_cartera_latam(fecha, venta_cartera=None, usuario=None, contrasena=None, log=_noop, avance=_noop):
    """Bloque LATAM de cartera. `venta_cartera` es el archivo Venta Cartera.xlsx (opcional).
    Regresa (df, conteos, avisos, rutas_faltantes)."""
    from sqlalchemy import text
    usuario = usuario or DB_USER
    contrasena = contrasena or DB_PASSWORD
    query = f"SELECT * FROM operacion_cierre_cartera WHERE fecha_cierre = '{fecha}' AND estatus_id = 1"

    dfs, conteos, avisos = [], [], []
    total = len(DC.SERVIDORES_LATAM)
    for i, s in enumerate(DC.SERVIDORES_LATAM):
        log(f"🔌 Conectando a **{s['marca']}** ({s['pais']})...")
        try:
            engine = _engine(s["host"], s["db"], usuario, contrasena)
            df_temp = pd.read_sql(text(query), con=engine)
            engine.dispose()
            if not df_temp.empty:
                df_temp["MARCA"] = s["marca"]
                df_temp["PAIS"] = s["pais"]
                dfs.append(df_temp)
                conteos.append({"Base": s["marca"], "País": s["pais"], "Registros": len(df_temp), "Estado": "✅ OK"})
                log(f"　　✅ {len(df_temp):,} registros descargados")
            else:
                conteos.append({"Base": s["marca"], "País": s["pais"], "Registros": 0, "Estado": "⚠️ Sin registros"})
                log("　　⚠️ Sin registros.")
        except Exception as e:
            conteos.append({"Base": s["marca"], "País": s["pais"], "Registros": 0, "Estado": f"❌ {e}"})
            log(f"　　❌ ERROR: {e}")
        avance((i + 1) / total)

    if not dfs:
        return None, conteos, avisos, []

    df = pd.concat(dfs, ignore_index=True)
    log("🧹 Limpiando LATAM...")
    cols_quitar = ["fecha_registro", "id", "estatus_id", "colocado_ci_sin_parciales"]
    df = df.drop(columns=[c for c in cols_quitar if c in df.columns], errors="ignore")
    df = df.rename(columns={"fecha_cierre": "Corte"})
    df["colocado_con_interes_fp"] = df["colocado_con_interes_fp"].fillna(0)
    df["vencido_con_interes_fp"] = df["vencido_con_interes_fp"].fillna(0)

    # Exclusiones de Venta de Cartera (pestaña LATAM)
    if venta_cartera is not None:
        try:
            df["id_desembolso_str"] = df["id_desembolso"].fillna(0).astype(int).astype(str)
            df["Llaveventa"] = df["PAIS"].astype(str) + df["MARCA"].astype(str) + df["id_desembolso_str"]
            df = df.drop(columns=["id_desembolso_str"])
            df_venta = leer_venta_cartera(venta_cartera, "LATAM")
            df_venta["Llave"] = df_venta["Llave"].astype(str)
            df = df.merge(df_venta, left_on="Llaveventa", right_on="Llave", how="left")
            antes = len(df)
            df = df[df["Concepto"].isna()]
            excluidos = antes - len(df)
            df = df.drop(columns=["Llaveventa", "Concepto", "Llave"], errors="ignore")
            log(f"🚫 Venta de Cartera LATAM: se excluyeron {excluidos:,} registros.")
            avisos.append(f"Venta de Cartera LATAM: {excluidos:,} registros excluidos.")
        except Exception as e:
            df = df.drop(columns=["Llaveventa"], errors="ignore")
            avisos.append(f"No se pudo procesar Venta de Cartera LATAM: {e}")
            log(f"⚠️ No se pudo procesar Venta de Cartera LATAM: {e}")
    else:
        avisos.append("No se subió Venta Cartera.xlsx: NO se aplicaron exclusiones de venta/inseguridad en LATAM.")
        log("⚠️ Sin archivo de Venta de Cartera: no se aplican exclusiones LATAM.")

    # Validación de rutas LATAM: rutas del catálogo que faltan en la extracción
    rutas_faltantes = []
    try:
        log("🔎 Validando rutas LATAM contra la Estructura...")
        df_rutas = pd.read_csv(DC.URL_RUTAS_VALIDACION)
        df_rutas = df_rutas[df_rutas["País"] != "México"]
        rutas_ext = set(df["ruta"].dropna().astype(str).unique())
        rutas_cat = set(df_rutas["Ruta"].dropna().astype(str).unique())
        rutas_faltantes = sorted(rutas_cat - rutas_ext)
    except Exception as e:
        avisos.append(f"Validación de rutas LATAM falló: {e}")

    return _aplicar_tipos_y_orden(df, DC.ORDEN_COLUMNAS_LATAM), conteos, avisos, rutas_faltantes


def proceso_cartera_mexico(fecha, venta_cartera=None, usuario=None, contrasena=None, log=_noop, avance=_noop):
    """Bloque MÉXICO de cartera. Regresa (df, conteos, avisos, rutas_faltantes_en_estructura)."""
    from sqlalchemy import text
    usuario = usuario or DB_USER
    contrasena = contrasena or DB_PASSWORD
    query = f"CALL reporte_operacion_cierre_cartera('{fecha}')"

    dfs, conteos, avisos = [], [], []
    total = len(DC.SERVIDORES_MEXICO)
    for i, s in enumerate(DC.SERVIDORES_MEXICO):
        log(f"🔌 Conectando a **{s['marca']}**...")
        try:
            engine = _engine(s["host"], s["db"], usuario, contrasena)
            df_temp = pd.read_sql(text(query), con=engine)
            engine.dispose()
            if not df_temp.empty:
                df_temp["Marca"] = s["marca"]
                dfs.append(df_temp)
                conteos.append({"Base": s["marca"], "Registros": len(df_temp), "Estado": "✅ OK"})
                log(f"　　✅ {len(df_temp):,} registros descargados")
            else:
                conteos.append({"Base": s["marca"], "Registros": 0, "Estado": "⚠️ Sin registros"})
                log("　　⚠️ Sin registros.")
        except Exception as e:
            conteos.append({"Base": s["marca"], "Registros": 0, "Estado": f"❌ {e}"})
            log(f"　　❌ ERROR: {e}")
        avance((i + 1) / total)

    if not dfs:
        return None, conteos, avisos, []

    df = pd.concat(dfs, ignore_index=True)
    log("🧹 Limpiando MÉXICO...")
    if "ruta" in df.columns:
        df["ruta"] = df["ruta"].replace("MANZANILLO", "MANZANILLO-P-R2")
        df = df[df["ruta"] != "ZONA DE PRUEBAS-P-R1"]
    df = df.rename(columns={"fecha_cierre": "Corte"})

    # Exclusiones de Venta de Cartera (pestaña "Venta de Cartera")
    if venta_cartera is not None:
        try:
            df["id_desembolso_str"] = df["id_desembolso"].fillna(0).astype(int).astype(str)
            df["LlaveVenta"] = df["Marca"].astype(str) + df["id_desembolso_str"]
            df = df.drop(columns=["id_desembolso_str"])
            df_venta = leer_venta_cartera(venta_cartera, "Venta de Cartera")
            df_venta["Llave"] = df_venta["Llave"].astype(str)
            df = df.merge(df_venta, left_on="LlaveVenta", right_on="Llave", how="left")
            antes = len(df)
            df = df[df["Concepto"].isna()]
            excluidos = antes - len(df)
            df = df.drop(columns=["LlaveVenta", "Concepto", "Llave"], errors="ignore")
            log(f"🚫 Venta de Cartera MÉXICO: se excluyeron {excluidos:,} registros.")
            avisos.append(f"Venta de Cartera MÉXICO: {excluidos:,} registros excluidos.")
        except Exception as e:
            df = df.drop(columns=["LlaveVenta"], errors="ignore")
            avisos.append(f"No se pudo procesar Venta de Cartera MÉXICO: {e}")
            log(f"⚠️ No se pudo procesar Venta de Cartera MÉXICO: {e}")
    else:
        avisos.append("No se subió Venta Cartera.xlsx: NO se aplicaron exclusiones de venta/inseguridad en MÉXICO.")
        log("⚠️ Sin archivo de Venta de Cartera: no se aplican exclusiones MÉXICO.")

    # Validación de rutas MÉXICO: rutas extraídas que FALTAN en la Estructura (hay que agregarlas)
    rutas_faltantes = []
    try:
        log("🔎 Validando rutas MÉXICO contra la Estructura...")
        df_rutas = pd.read_csv(DC.URL_RUTAS_VALIDACION)
        df_rutas = df_rutas[df_rutas["País"] == "México"]
        rutas_ext = set(df["ruta"].dropna().astype(str).unique())
        rutas_cat = set(df_rutas["Ruta"].dropna().astype(str).unique())
        rutas_faltantes = sorted(rutas_ext - rutas_cat)
    except Exception as e:
        avisos.append(f"Validación de rutas MÉXICO falló: {e}")

    return _aplicar_tipos_y_orden(df, DC.ORDEN_COLUMNAS_MEXICO), conteos, avisos, rutas_faltantes


# ==========================================================
# GENERACIÓN DE ARCHIVOS EN MEMORIA (para descargar desde la web)
# ==========================================================
def excel_bytes(df, hoja="Hoja1", columnas_fecha=None, columna_fecha_hora=None):
    """Genera el .xlsx en memoria con el mismo estilo (Century Gothic 8, encabezado naranja).

    ``Grupo`` es un identificador y se exporta siempre como texto real de Excel,
    aunque la base de datos entregue algunos valores como números.
    """
    columnas_fecha = columnas_fecha or []
    df_excel = df.copy()
    columnas_texto = [col for col in ("Grupo",) if col in df_excel.columns]
    for col in columnas_texto:
        # El formateador LATAM conserva nulos y ceros a la izquierda de las
        # cadenas, y elimina el sufijo ".0" cuando el origen entregó un float.
        df_excel[col] = df_excel[col].map(DL._texto_bi)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df_excel.to_excel(writer, sheet_name=hoja, index=False)
        wb = writer.book
        ws = writer.sheets[hoja]
        wb.formats[0].set_font_name("Century Gothic")
        wb.formats[0].set_font_size(8)
        fmt_encabezado = wb.add_format({
            "font_name": "Century Gothic", "font_size": 8, "bold": True,
            "font_color": "#FFFFFF", "bg_color": "#ED7D31",
            "align": "center", "valign": "vcenter",
        })
        fmt_fecha = wb.add_format({"num_format": "dd/mm/yyyy", "font_name": "Century Gothic", "font_size": 8})
        fmt_fecha_hora = wb.add_format({"num_format": "dd/mm/yyyy hh:mm", "font_name": "Century Gothic", "font_size": 8})
        fmt_texto = wb.add_format({"num_format": "@", "font_name": "Century Gothic", "font_size": 8})
        muestra = df_excel.head(200)
        for i, col in enumerate(df_excel.columns):
            ws.write(0, i, str(col), fmt_encabezado)
            largos = [len(str(col))] + [len(str(v)) for v in muestra[col].tolist()]
            ancho = min(max(largos) + 2, 35)
            if col in columnas_fecha:
                ws.set_column(i, i, ancho, fmt_fecha)
            elif columna_fecha_hora and col == columna_fecha_hora:
                ws.set_column(i, i, ancho, fmt_fecha_hora)
            elif col in columnas_texto:
                ws.set_column(i, i, ancho, fmt_texto)
                # Se reescriben las celdas para que el tipo interno sea string
                # y el formato de cada celda sea Texto, no solo el de la columna.
                for fila, valor in enumerate(df_excel[col], start=1):
                    if valor is None or pd.isna(valor):
                        ws.write_blank(fila, i, None, fmt_texto)
                    else:
                        ws.write_string(fila, i, valor, fmt_texto)
                if len(df_excel):
                    # Excel interpreta cadenas como "148" correctamente como
                    # texto, pero por defecto muestra el aviso visual "número
                    # almacenado como texto". Se conserva el tipo texto y solo
                    # se desactiva esa advertencia para la columna Grupo.
                    ws.ignore_errors({
                        "number_stored_as_text": xl_range(1, i, len(df_excel), i)
                    })
            else:
                ws.set_column(i, i, ancho)
    return buf.getvalue()


def parquet_bytes(df):
    """Parquet en memoria (mismas conversiones que el script de cartera)."""
    df_pq = df.copy()
    for col in df_pq.select_dtypes(include="object").columns:
        df_pq[col] = df_pq[col].astype(str)
    buf = io.BytesIO()
    df_pq.to_parquet(buf, engine="pyarrow")
    return buf.getvalue()
