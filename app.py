# -*- coding: utf-8 -*-
"""
COBRANZA Y CARTERA — App web para publicar en https://share.streamlit.io/
Apartados: COBRANZA (LATAM + PRESICO MX) y CARTERA (LATAM + MÉXICO), con seguimiento
en vivo por base, validación de rutas contra la Estructura, KPIs, gráficas y descargas.
"""
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import procesos as pr

# ==========================================================
# CONFIGURACIÓN GENERAL
# ==========================================================
st.set_page_config(page_title="Cobranza y Cartera — LATAM / MX", page_icon="💼",
                   layout="wide", initial_sidebar_state="expanded")

TZ = ZoneInfo("America/Mexico_City")
HOY = datetime.now(TZ).date()
AYER = HOY - timedelta(days=1)
BASE = Path(__file__).parent
RUTA_TIPO_CAMBIO_REPO = BASE / "TIPO DE CAMBIO.xlsx"
# Acepta .xlsb (binario: pesa menos y sí pasa el límite de GitHub) o .xlsx
RUTA_VENTA_CARTERA_REPO = next(
    (p for p in (BASE / "Venta Cartera.xlsb", BASE / "Venta Cartera.xlsx") if p.exists()), None
)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# ==========================================================
# ESTILO (tema claro + acento naranja corporativo, sidebar oscuro)
# ==========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

[data-testid="stAppViewContainer"] * { font-family: 'Inter', 'Segoe UI', sans-serif; }
/* Restaurar la fuente de los ICONOS de Streamlit (si no, se ven como texto) */
span[data-testid="stIconMaterial"], [data-testid="stExpanderToggleIcon"], [class*="material-symbols"] {
    font-family: 'Material Symbols Rounded' !important;
    font-weight: 400 !important;
}
#MainMenu, footer { visibility: hidden; height: 0; }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1350px; }

/* ---------- Encabezado principal ---------- */
.hero {
    border-radius: 18px; padding: 1.7rem 2.1rem 1.45rem;
    background: linear-gradient(115deg, #171923 0%, #1f2b46 52%, #b34700 130%);
    color: #fff; box-shadow: 0 10px 30px rgba(23, 25, 35, .18); margin-bottom: 1.1rem;
}
.hero h1 { margin: 0; font-size: 1.85rem; font-weight: 800; letter-spacing: -.02em; color: #fff; }
.hero .sub { color: #aeb7cc; margin-top: .3rem; font-size: .95rem; }
.chips { margin-top: .95rem; }
.chip {
    display: inline-flex; align-items: center; gap: .4rem; padding: .3rem .85rem;
    border-radius: 999px; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.22);
    color: #fff; font-size: .8rem; font-weight: 600; margin-right: .5rem;
}
.chip b { color: #ffd7b3; }

/* ---------- Métricas tipo tarjeta ---------- */
div[data-testid="stMetric"] {
    background: #ffffff; border: 1px solid #e9eaf0; border-radius: 14px;
    padding: .85rem 1rem; box-shadow: 0 1px 3px rgba(16,24,40,.05);
}
div[data-testid="stMetric"] label { color: #6b7280; font-weight: 600; }

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid #e9eaf0; }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: .45rem 1.05rem; font-weight: 600; }
.stTabs [aria-selected="true"] { background: #fff3ea; }

/* ---------- Tarjetas de resultado ---------- */
.card-title { font-size: 1.12rem; font-weight: 800; letter-spacing: -.01em; margin: 0; }
.card-sub { color: #6b7280; font-size: .85rem; margin-top: .15rem; }
.badge-ok   { display: inline-block; padding: .2rem .65rem; border-radius: 999px; background: #e7f7ee; color: #127a44; font-size: .75rem; font-weight: 700; }
.badge-warn { display: inline-block; padding: .2rem .65rem; border-radius: 999px; background: #fdeeee; color: #b42318; font-size: .75rem; font-weight: 700; }

div[data-testid="stStatus"] { border-radius: 12px; }

/* ==========================================================
   SIDEBAR — panel oscuro tipo dashboard
   ========================================================== */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #12141d 0%, #1a2338 70%, #1f2b46 100%);
    border-right: 1px solid rgba(255,255,255,.06);
}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] li,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] summary span { color: #dfe3ee; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12); }

.sb-brand { display: flex; align-items: center; gap: .7rem; margin-bottom: 1.05rem; }
.sb-logo {
    width: 44px; height: 44px; border-radius: 13px; display: flex; align-items: center; justify-content: center;
    font-size: 1.35rem; background: linear-gradient(135deg, #E8590C, #b34700);
    box-shadow: 0 6px 18px rgba(232,89,12,.4); flex: none;
}
.sb-title { font-weight: 800; font-size: 1.04rem; color: #fff; letter-spacing: -.01em; line-height: 1.15; }
.sb-sub { font-size: .72rem; color: #9aa3ba; }
.sb-pill {
    margin-left: auto; font-size: .63rem; font-weight: 700; padding: .16rem .5rem; border-radius: 999px;
    background: rgba(232,89,12,.18); color: #ffb98a; border: 1px solid rgba(232,89,12,.4); flex: none;
}

.sb-card {
    background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.09);
    border-radius: 14px; padding: .8rem .95rem; margin-bottom: .9rem;
}

.sb-fechas { display: flex; align-items: center; }
.sb-fecha { flex: 1; text-align: center; }
.sb-fecha span { display: block; font-size: .6rem; letter-spacing: .13em; color: #9aa3ba; font-weight: 700; }
.sb-fecha b { display: block; font-size: 1.08rem; color: #fff; font-weight: 800; margin-top: .18rem; }
.sb-fecha i { display: block; font-style: normal; font-size: .68rem; color: #9aa3ba; }
.sb-fecha-sep { width: 1px; height: 2.3rem; background: rgba(255,255,255,.14); }

.sb-section {
    font-size: .64rem; font-weight: 800; letter-spacing: .15em; text-transform: uppercase;
    color: #8b94ab; margin: .2rem 0 .45rem .15rem;
}

.sb-row { display: flex; gap: .6rem; align-items: flex-start; padding: .34rem 0; }
.sb-row + .sb-row { border-top: 1px dashed rgba(255,255,255,.09); }
.dot-ok, .dot-warn { width: 9px; height: 9px; border-radius: 50%; margin-top: .32rem; flex: none; }
.dot-ok { background: #3ddc84; box-shadow: 0 0 9px rgba(61,220,132,.65); }
.dot-warn { background: #ffb020; box-shadow: 0 0 9px rgba(255,176,32,.65); }
.sb-row-t { font-size: .8rem; font-weight: 600; color: #eef0f6; line-height: 1.2; }
.sb-row-d { font-size: .69rem; color: #9aa3ba; }

.tc-row { display: flex; align-items: center; gap: .55rem; padding: .27rem 0; }
.tc-row + .tc-row { border-top: 1px dashed rgba(255,255,255,.09); }
.tc-pill {
    font-family: 'JetBrains Mono', monospace; font-size: .62rem; font-weight: 700; color: #ffd7b3;
    background: rgba(232,89,12,.16); border: 1px solid rgba(232,89,12,.35); border-radius: 6px;
    padding: .1rem .35rem; min-width: 2.5rem; text-align: center; flex: none;
}
.tc-pais { font-size: .78rem; color: #e6e9f2; flex: 1; }
.tc-valor { font-family: 'JetBrains Mono', monospace; font-size: .78rem; font-weight: 700; color: #fff; }

.act-row { display: flex; gap: .55rem; align-items: flex-start; padding: .32rem 0; }
.act-row + .act-row { border-top: 1px dashed rgba(255,255,255,.09); }
.act-emoji { font-size: .95rem; flex: none; }
.act-t { font-size: .78rem; font-weight: 700; color: #eef0f6; line-height: 1.2; }
.act-d { font-size: .68rem; color: #9aa3ba; }
.act-hora { margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: .66rem; color: #ffd7b3; flex: none; }
.sb-vacio { font-size: .74rem; color: #8b94ab; text-align: center; padding: .35rem 0; }

[data-testid="stSidebar"] button {
    background: rgba(255,255,255,.06) !important; color: #e6e9f2 !important;
    border: 1px solid rgba(255,255,255,.16) !important; border-radius: 10px !important; font-weight: 600;
}
[data-testid="stSidebar"] button:hover { border-color: #E8590C !important; color: #fff !important; }
[data-testid="stSidebar"] details {
    background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.10); border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# ==========================================================
# UTILIDADES DE UI
# ==========================================================
def credenciales():
    """Usuario/contraseña desde Secrets de Streamlit Cloud; si no hay, usa los del código."""
    try:
        return st.secrets["DB_USER"], st.secrets["DB_PASSWORD"]
    except Exception:
        return pr.DB_USER, pr.DB_PASSWORD


@st.cache_data(ttl=600, show_spinner=False)
def estructura_cacheada():
    return pr.cargar_estructura()


@st.cache_data(ttl=3600, show_spinner=False)
def tipo_cambio_repo():
    return pr.cargar_tipo_cambio(str(RUTA_TIPO_CAMBIO_REPO))


def dinero(v):
    try:
        return f"${v:,.0f}"
    except Exception:
        return "-"


def tabla_montos(df, columnas_texto):
    """Tabla con formato de miles y la fila Total en negritas."""
    columnas_num = [c for c in df.columns if c not in columnas_texto]
    styler = df.style.format({c: "{:,.2f}" for c in columnas_num}, na_rep="")
    styler = styler.apply(
        lambda fila: ["font-weight: 700; background-color: #fff3ea" if str(fila.iloc[0]) == "Total" else "" for _ in fila],
        axis=1,
    )
    return styler


def mostrar_conteos(conteos):
    st.dataframe(pd.DataFrame(conteos), use_container_width=True, hide_index=True)


def bloque_rutas(rutas, mensaje_ok, mensaje_alerta):
    if rutas:
        st.warning(f"**{mensaje_alerta}** — {len(rutas)} ruta(s):")
        st.dataframe(pd.DataFrame({"Ruta": rutas}), use_container_width=True, hide_index=True, height=220)
    else:
        st.success(mensaje_ok)


def encabezado_tarjeta(titulo, subtitulo, rutas_faltantes, registros, boton_args=None):
    c1, c2, c3, c4 = st.columns([2.6, 1.1, 1.0, 1.5])
    with c1:
        st.markdown(f'<p class="card-title">{titulo}</p><p class="card-sub">{subtitulo}</p>', unsafe_allow_html=True)
    with c2:
        if rutas_faltantes:
            st.markdown(f'<span class="badge-warn">⚠ {len(rutas_faltantes)} rutas fuera de estructura</span>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-ok">✔ Estructura completa</span>', unsafe_allow_html=True)
    with c3:
        st.metric("Registros", f"{registros:,}")
    with c4:
        if boton_args:
            st.download_button(**boton_args, type="primary", use_container_width=True)


# ==========================================================
# SIDEBAR — panel de control
# ==========================================================
MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]


def _fila_fuente(nombre, ok, detalle):
    punto = "dot-ok" if ok else "dot-warn"
    return (f'<div class="sb-row"><span class="{punto}"></span>'
            f'<div><div class="sb-row-t">{nombre}</div><div class="sb-row-d">{detalle}</div></div></div>')


with st.sidebar:
    # --- Marca ---
    st.markdown(
        '<div class="sb-brand">'
        '<div class="sb-logo">📊</div>'
        '<div><div class="sb-title">Centro de Reportes</div>'
        '<div class="sb-sub">Cobranza · Cartera · LATAM &amp; MX</div></div>'
        '<span class="sb-pill">v2.1</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- Fechas de operación ---
    st.markdown(
        f'''<div class="sb-card sb-fechas">
            <div class="sb-fecha"><span>HOY</span><b>{HOY.day:02d} {MESES[HOY.month-1]}</b><i>{HOY.year}</i></div>
            <div class="sb-fecha-sep"></div>
            <div class="sb-fecha"><span>DÍA VENCIDO</span><b>{AYER.day:02d} {MESES[AYER.month-1]}</b><i>{AYER.year}</i></div>
        </div>''',
        unsafe_allow_html=True,
    )

    # --- Fuentes de datos (estado en vivo) ---
    st.markdown('<div class="sb-section">Fuentes de datos</div>', unsafe_allow_html=True)
    filas = []
    try:
        n_rutas = len(estructura_cacheada())
        filas.append(_fila_fuente("Estructura · Google Sheets", True, f"conectada · {n_rutas:,} rutas en catálogo"))
    except Exception:
        filas.append(_fila_fuente("Estructura · Google Sheets", False, "sin conexión al catálogo"))
    try:
        n_tc = len(tipo_cambio_repo())
        filas.append(_fila_fuente("Tipo de cambio", True, f"{n_tc} países · repositorio"))
    except Exception:
        filas.append(_fila_fuente("Tipo de cambio", False, "falta TIPO DE CAMBIO.xlsx"))
    if RUTA_VENTA_CARTERA_REPO is not None:
        mb = RUTA_VENTA_CARTERA_REPO.stat().st_size / 1_048_576
        formato = RUTA_VENTA_CARTERA_REPO.suffix.upper().lstrip(".")
        filas.append(_fila_fuente("Venta de Cartera", True, f"{formato} en repositorio · {mb:.1f} MB"))
    else:
        filas.append(_fila_fuente("Venta de Cartera", False, "no está en el repositorio (súbelo en Cartera)"))
    filas.append(_fila_fuente("Bases de datos", True, "10 LATAM · 7 MX vía MySQL"))
    st.markdown(f'<div class="sb-card">{"".join(filas)}</div>', unsafe_allow_html=True)

    if st.button("🔄 Refrescar catálogos", use_container_width=True,
                 help="Vuelve a leer la Estructura y el Tipo de Cambio"):
        st.cache_data.clear()
        st.rerun()

    # --- Tipo de cambio vigente ---
    st.markdown('<div class="sb-section">Tipo de cambio vigente</div>', unsafe_allow_html=True)
    try:
        tc = tipo_cambio_repo()
        filas_tc = "".join(
            f'<div class="tc-row"><span class="tc-pill">{fila["ID Pais"]}</span>'
            f'<span class="tc-pais">{fila["PAIS"]}</span>'
            f'<span class="tc-valor">{fila["TIPO CAMBIO"]:g}</span></div>'
            for _, fila in tc.iterrows()
        )
        st.markdown(f'<div class="sb-card">{filas_tc}</div>', unsafe_allow_html=True)
    except Exception:
        st.markdown('<div class="sb-card sb-vacio">Sin tipo de cambio disponible</div>', unsafe_allow_html=True)

    # --- Actividad de la sesión ---
    st.markdown('<div class="sb-section">Actividad de la sesión</div>', unsafe_allow_html=True)
    actividad = []
    res_cob = st.session_state.get("resultado_cobranza")
    if res_cob:
        for it in res_cob["items"]:
            if not it.get("error"):
                actividad.append(("💰", f"Cobranza {it['region']}",
                                  f"corte {it['fecha']} · {it['registros']:,} registros",
                                  res_cob.get("hora", "")))
    res_car = st.session_state.get("resultado_cartera")
    if res_car:
        for b in res_car["bloques"]:
            if not b.get("error"):
                actividad.append(("📦", f"Cartera {b['region']}",
                                  f"corte {res_car['fecha']} · {b['registros']:,} registros",
                                  res_car.get("hora", "")))
    if actividad:
        filas_act = "".join(
            f'<div class="act-row"><span class="act-emoji">{e}</span>'
            f'<div><div class="act-t">{t}</div><div class="act-d">{d}</div></div>'
            f'<span class="act-hora">{h}</span></div>'
            for e, t, d, h in actividad
        )
        st.markdown(f'<div class="sb-card">{filas_act}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="sb-card sb-vacio">Aún no generas reportes en esta sesión</div>',
                    unsafe_allow_html=True)

    # --- Guía ---
    with st.expander("🧭 ¿Cómo funciona?"):
        st.markdown(
            "1. Elige el apartado (**Cobranza** o **Cartera**).\n"
            "2. Selecciona el proceso o la fecha.\n"
            "3. Presiona **Generar** y sigue el avance base por base.\n"
            "4. Revisa los montos y las rutas faltantes.\n"
            "5. Descarga los archivos a tu computadora."
        )
    st.caption("Queries de Power Query pegados tal cual · Los archivos se generan en memoria, nada se guarda en el servidor")

# ==========================================================
# ENCABEZADO
# ==========================================================
st.markdown(
    f"""
    <div class="hero">
        <h1>📊 Cobranza y Cartera</h1>
        <div class="sub">Extracción operativa LATAM · PRESICO MX — reportes diarios con validación de estructura</div>
        <div class="chips">
            <span class="chip">📆 Hoy <b>{HOY.strftime('%d-%m-%Y')}</b></span>
            <span class="chip">⏪ Día vencido <b>{AYER.strftime('%d-%m-%Y')}</b></span>
            <span class="chip">🌎 10 bases LATAM</span>
            <span class="chip">🦅 7 bases MX</span>
        </div>
    </div>
    """, unsafe_allow_html=True,
)

tab_cobranza, tab_cartera = st.tabs(["💰  COBRANZA", "📦  CARTERA"])

# ==========================================================
# APARTADO 1: COBRANZA
# ==========================================================
with tab_cobranza:
    with st.container(border=True):
        st.markdown("#### ⚙️ Configuración del proceso")
        col1, col2 = st.columns([2.2, 1])
        with col1:
            proceso = st.radio(
                "Proceso",
                ["🌅 Mañana (día vencido + hoy)", "🌇 Tarde (hoy)", "📅 Fecha específica"],
                horizontal=True, key="cob_proceso",
            )
        with col2:
            fecha_especifica_cob = None
            if proceso.startswith("📅"):
                fecha_especifica_cob = st.date_input("Fecha de corte", value=AYER, key="cob_fecha")

        col3, col4, col5 = st.columns([1, 1, 1.4])
        with col3:
            correr_latam = st.checkbox("🌎 Cobranza LATAM (10 bases)", value=True, key="cob_latam")
        with col4:
            correr_presico = st.checkbox("🦅 Cobranza PRESICO MX (7 bases)", value=True, key="cob_presico")
        with col5:
            tc_subido = st.file_uploader("TIPO DE CAMBIO.xlsx (opcional: si no, se usa el del repositorio)",
                                         type=["xlsx"], key="cob_tc")

        if proceso.startswith("🌅"):
            fechas_cobranza = [AYER.strftime("%Y-%m-%d"), HOY.strftime("%Y-%m-%d")]
        elif proceso.startswith("🌇"):
            fechas_cobranza = [HOY.strftime("%Y-%m-%d")]
        else:
            fechas_cobranza = [fecha_especifica_cob.strftime("%Y-%m-%d")] if fecha_especifica_cob else []

        regiones_txt = ", ".join([r for r, ok in [("LATAM", correr_latam), ("PRESICO MX", correr_presico)] if ok]) or "ninguna región"
        st.info(f"Se generará el corte **{' y '.join(fechas_cobranza)}** para **{regiones_txt}**.")

        generar_cob = st.button("🚀 Generar cobranza", type="primary",
                                disabled=not (fechas_cobranza and (correr_latam or correr_presico)))

    if generar_cob:
        usuario, contrasena = credenciales()
        items = []

        with st.status("📥 Cargando Estructura (Google Sheets)...", expanded=False) as s:
            df_estructura = estructura_cacheada()
            s.update(label=f"📥 Estructura cargada: {len(df_estructura):,} rutas en catálogo", state="complete")

        df_tc = None
        if correr_latam:
            with st.status("💱 Cargando Tipo de Cambio...", expanded=False) as s:
                df_tc = pr.cargar_tipo_cambio(tc_subido) if tc_subido is not None else tipo_cambio_repo()
                origen = "archivo subido" if tc_subido is not None else "repositorio"
                s.update(label=f"💱 Tipo de Cambio cargado ({origen}): {len(df_tc)} países", state="complete")

        for fecha in fechas_cobranza:
            if correr_latam:
                with st.status(f"🌎 COBRANZA LATAM — corte {fecha}", expanded=True) as s:
                    barra = st.progress(0.0)
                    df_final, conteos = pr.proceso_cobranza_latam(
                        fecha, df_estructura, df_tc, usuario, contrasena,
                        log=st.write, avance=barra.progress,
                    )
                    if df_final is not None:
                        resumen = pr.resumen_cobranza_latam(df_final)
                        total = resumen.iloc[-1]
                        items.append({
                            "fecha": fecha, "region": "LATAM", "resumen": resumen,
                            "faltantes": pr.rutas_faltantes_cobranza_latam(df_final),
                            "conteos": conteos, "registros": len(df_final),
                            "kpis": {
                                "💵 Cobranza del día": dinero(total["COBRANZA_DEL_DIA_NW"]),
                                "✅ Pago del día": dinero(total["pago_cobranza_dia"]),
                                "🕓 Cobranza c/ atraso": dinero(total["Cobranza_con_atrasoNW"]),
                                "🧾 Pago c/ atraso": dinero(total["PAGO COBRANZA EN ATRASO"]),
                            },
                            "archivo": f"COBRANZA LATAM {fecha}.xlsx",
                            "excel": pr.excel_bytes(df_final),
                        })
                        s.update(label=f"🌎 COBRANZA LATAM {fecha} — ✅ {len(df_final):,} registros", state="complete", expanded=False)
                    else:
                        items.append({"fecha": fecha, "region": "LATAM", "error": "Sin datos de ninguna base", "conteos": conteos})
                        s.update(label=f"🌎 COBRANZA LATAM {fecha} — ❌ sin datos", state="error")

            if correr_presico:
                with st.status(f"🦅 COBRANZA PRESICO MX — corte {fecha}", expanded=True) as s:
                    barra = st.progress(0.0)
                    df_final, conteos = pr.proceso_cobranza_presico(
                        fecha, df_estructura, usuario, contrasena,
                        log=st.write, avance=barra.progress,
                    )
                    if df_final is not None:
                        resumen = pr.resumen_cobranza_presico(df_final)
                        total = resumen.iloc[-1]
                        items.append({
                            "fecha": fecha, "region": "PRESICO MX", "resumen": resumen,
                            "faltantes": pr.rutas_faltantes_cobranza_presico(df_final),
                            "conteos": conteos, "registros": len(df_final),
                            "kpis": {
                                "💵 Cobranza del día": dinero(total["Cobranza del dia"]),
                                "✅ Pago del día": dinero(total["Pago Cobranza del dia"]),
                                "🕓 Cobranza c/ atraso": dinero(total["Cobranza con atraso"]),
                                "🧾 Pago c/ atraso": dinero(total["Pago Cobranza con atraso"]),
                            },
                            "archivo": f"COBRANZA PRESICO {fecha}.xlsx",
                            "excel": pr.excel_bytes(df_final),
                        })
                        s.update(label=f"🦅 COBRANZA PRESICO MX {fecha} — ✅ {len(df_final):,} registros", state="complete", expanded=False)
                    else:
                        items.append({"fecha": fecha, "region": "PRESICO MX", "error": "Sin datos de ninguna base", "conteos": conteos})
                        s.update(label=f"🦅 COBRANZA PRESICO MX {fecha} — ❌ sin datos", state="error")

        st.session_state["resultado_cobranza"] = {"proceso": proceso, "fechas": fechas_cobranza, "items": items,
                                                  "hora": datetime.now(TZ).strftime("%H:%M")}

    # ---------- Resultados de cobranza (persisten aunque descargues) ----------
    if "resultado_cobranza" in st.session_state:
        res = st.session_state["resultado_cobranza"]
        st.markdown(f"### 📈 Resultados — {res['proceso']}")

        for fecha in res["fechas"]:
            for item in [it for it in res["items"] if it["fecha"] == fecha]:
                with st.container(border=True):
                    if item.get("error"):
                        st.markdown(f'<p class="card-title">{"🌎" if item["region"] == "LATAM" else "🦅"} '
                                    f'Cobranza {item["region"]} — corte {fecha}</p>', unsafe_allow_html=True)
                        st.error(item["error"])
                        mostrar_conteos(item["conteos"])
                        continue

                    encabezado_tarjeta(
                        titulo=f'{"🌎" if item["region"] == "LATAM" else "🦅"} Cobranza {item["region"]}',
                        subtitulo=f"Fecha de corte: {fecha}",
                        rutas_faltantes=item["faltantes"],
                        registros=item["registros"],
                        boton_args=dict(
                            label=f"⬇️ {item['archivo']}", data=item["excel"], file_name=item["archivo"],
                            mime=XLSX_MIME, key=f"dl_cob_{item['region']}_{fecha}",
                        ),
                    )

                    k1, k2, k3, k4 = st.columns(4)
                    for col, (nombre, valor) in zip([k1, k2, k3, k4], item["kpis"].items()):
                        col.metric(nombre, valor)

                    t_montos, t_grafica, t_rutas, t_carga = st.tabs(
                        ["💵 Montos", "📈 Gráfica", "🗺️ Rutas vs Estructura", "📡 Carga por base"])

                    with t_montos:
                        columnas_texto = ["Pais", "Marca"] if item["region"] == "LATAM" else ["Unidad de Negocio"]
                        st.caption(f"Montos por {'País y Marca' if item['region'] == 'LATAM' else 'Unidad de Negocio'} — corte {fecha}")
                        st.dataframe(tabla_montos(item["resumen"], columnas_texto),
                                     use_container_width=True, hide_index=True)

                    with t_grafica:
                        base_g = item["resumen"][item["resumen"].iloc[:, 0] != "Total"]
                        if item["region"] == "LATAM":
                            graf = base_g.groupby("Pais")[["COBRANZA_DEL_DIA_NW", "pago_cobranza_dia"]].sum()
                            graf.columns = ["Cobranza del día", "Pago del día"]
                        else:
                            graf = base_g.set_index("Unidad de Negocio")[["Cobranza del dia", "Pago Cobranza del dia"]]
                            graf.columns = ["Cobranza del día", "Pago del día"]
                        st.bar_chart(graf, color=["#E8590C", "#1f2b46"])

                    with t_rutas:
                        bloque_rutas(
                            item["faltantes"],
                            "✅ Todas las rutas del reporte cruzaron con la Estructura.",
                            "Rutas del reporte que NO están en la Estructura (hay que agregarlas al catálogo)",
                        )

                    with t_carga:
                        mostrar_conteos(item["conteos"])

# ==========================================================
# APARTADO 2: CARTERA
# ==========================================================
with tab_cartera:
    with st.container(border=True):
        st.markdown("#### ⚙️ Configuración del proceso")
        col1, col2 = st.columns([2.2, 1])
        with col1:
            modo_cartera = st.radio(
                "Fecha de corte",
                [f"📆 Día vencido ({AYER.strftime('%d-%m-%Y')})", "📅 Fecha específica"],
                horizontal=True, key="car_modo",
            )
        with col2:
            fecha_especifica_car = None
            if modo_cartera.startswith("📅"):
                fecha_especifica_car = st.date_input("Fecha de corte", value=AYER, key="car_fecha")

        venta_subida = st.file_uploader(
            "Venta Cartera (.xlsx o .xlsb) — opcional: si no subes nada, se usa el del repositorio",
            type=["xlsx", "xlsb"], key="car_venta",
        )
        if venta_subida is not None:
            fuente_venta, origen_venta = venta_subida, f"archivo subido ({venta_subida.name})"
        elif RUTA_VENTA_CARTERA_REPO is not None:
            fuente_venta, origen_venta = str(RUTA_VENTA_CARTERA_REPO), f"repositorio ({RUTA_VENTA_CARTERA_REPO.name})"
        else:
            fuente_venta, origen_venta = None, "no disponible"

        fecha_cartera = (fecha_especifica_car if modo_cartera.startswith("📅") and fecha_especifica_car else AYER).strftime("%Y-%m-%d")
        if fuente_venta is not None:
            st.info(f"Se generará la cartera con corte **{fecha_cartera}** · Exclusiones de Venta de Cartera: **{origen_venta}** ✅")
        else:
            st.warning(f"Se generará la cartera con corte **{fecha_cartera}** · **SIN** exclusiones de Venta de Cartera (no hay archivo).")

        generar_car = st.button("🚀 Generar cartera", type="primary", key="btn_cartera")

    if generar_car:
        usuario, contrasena = credenciales()
        bloques = []

        # -------- BLOQUE LATAM --------
        with st.status(f"🌎 CARTERA LATAM — corte {fecha_cartera}", expanded=True) as s:
            barra = st.progress(0.0)
            df_latam, conteos, avisos, rutas = pr.proceso_cartera_latam(
                fecha_cartera, fuente_venta, usuario, contrasena,
                log=st.write, avance=barra.progress,
            )
            if df_latam is not None:
                st.write("🗂️ Generando Excel LATAM...")
                bloques.append({
                    "region": "LATAM", "conteos": conteos, "avisos": avisos, "rutas": rutas,
                    "registros": len(df_latam),
                    "etiqueta_rutas": ("✅ Todas las rutas del catálogo LATAM tienen registros.",
                                       "Rutas del catálogo LATAM SIN registros en la extracción"),
                    "archivos": [(f"LATAM {fecha_cartera}.xlsx",
                                  pr.excel_bytes(df_latam, columnas_fecha=pr.COLS_FECHA_CARTERA,
                                                 columna_fecha_hora=pr.COL_FECHA_HORA_CARTERA), XLSX_MIME)],
                })
                s.update(label=f"🌎 CARTERA LATAM {fecha_cartera} — ✅ {len(df_latam):,} registros", state="complete", expanded=False)
            else:
                bloques.append({"region": "LATAM", "error": "Sin datos", "conteos": conteos, "avisos": avisos})
                s.update(label=f"🌎 CARTERA LATAM {fecha_cartera} — ❌ sin datos", state="error")

        # -------- BLOQUE MÉXICO --------
        with st.status(f"🦅 CARTERA MÉXICO — corte {fecha_cartera}", expanded=True) as s:
            barra = st.progress(0.0)
            df_mx, conteos, avisos, rutas = pr.proceso_cartera_mexico(
                fecha_cartera, fuente_venta, usuario, contrasena,
                log=st.write, avance=barra.progress,
            )
            if df_mx is not None:
                st.write("🗂️ Generando Excel y Parquet de MÉXICO...")
                bloques.append({
                    "region": "MÉXICO", "conteos": conteos, "avisos": avisos, "rutas": rutas,
                    "registros": len(df_mx),
                    "etiqueta_rutas": ("✅ Todas las rutas de México ya existen en la Estructura.",
                                       "Rutas de las bases de México que FALTAN en la Estructura (hay que agregarlas)"),
                    "archivos": [
                        (f"PRESICO {fecha_cartera}.xlsx",
                         pr.excel_bytes(df_mx, columnas_fecha=pr.COLS_FECHA_CARTERA,
                                        columna_fecha_hora=pr.COL_FECHA_HORA_CARTERA), XLSX_MIME),
                        (f"PRESICO_{fecha_cartera}.parquet", pr.parquet_bytes(df_mx), "application/octet-stream"),
                    ],
                })
                s.update(label=f"🦅 CARTERA MÉXICO {fecha_cartera} — ✅ {len(df_mx):,} registros", state="complete", expanded=False)
            else:
                bloques.append({"region": "MÉXICO", "error": "Sin datos", "conteos": conteos, "avisos": avisos})
                s.update(label=f"🦅 CARTERA MÉXICO {fecha_cartera} — ❌ sin datos", state="error")

        st.session_state["resultado_cartera"] = {"fecha": fecha_cartera, "origen_venta": origen_venta, "bloques": bloques,
                                                 "hora": datetime.now(TZ).strftime("%H:%M")}

    # ---------- Resultados de cartera ----------
    if "resultado_cartera" in st.session_state:
        res = st.session_state["resultado_cartera"]
        st.markdown(f"### 📈 Resultados — corte {res['fecha']}")

        for bloque in res["bloques"]:
            with st.container(border=True):
                if bloque.get("error"):
                    st.markdown(f'<p class="card-title">{"🌎" if bloque["region"] == "LATAM" else "🦅"} '
                                f'Cartera {bloque["region"]}</p>', unsafe_allow_html=True)
                    st.error(bloque["error"])
                    mostrar_conteos(bloque["conteos"])
                    continue

                c1, c2, c3 = st.columns([2.6, 1.0, 1.8])
                with c1:
                    st.markdown(
                        f'<p class="card-title">{"🌎" if bloque["region"] == "LATAM" else "🦅"} Cartera {bloque["region"]}</p>'
                        f'<p class="card-sub">Fecha de corte: {res["fecha"]} · Venta de Cartera: {res["origen_venta"]}</p>',
                        unsafe_allow_html=True,
                    )
                    if bloque.get("rutas"):
                        st.markdown(f'<span class="badge-warn">⚠ {len(bloque["rutas"])} rutas con pendiente</span>',
                                    unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-ok">✔ Rutas completas</span>', unsafe_allow_html=True)
                with c2:
                    st.metric("Registros", f"{bloque['registros']:,}")
                with c3:
                    for nombre, datos, mime in bloque["archivos"]:
                        st.download_button(f"⬇️ {nombre}", data=datos, file_name=nombre, mime=mime,
                                           key=f"dl_car_{bloque['region']}_{nombre}", type="primary",
                                           use_container_width=True)

                t_carga, t_rutas, t_avisos = st.tabs(["📡 Carga por base", "🗺️ Rutas vs Estructura", "ℹ️ Avisos"])
                with t_carga:
                    mostrar_conteos(bloque["conteos"])
                with t_rutas:
                    ok, alerta = bloque["etiqueta_rutas"]
                    bloque_rutas(bloque.get("rutas", []), ok, alerta)
                with t_avisos:
                    if bloque.get("avisos"):
                        for aviso in bloque["avisos"]:
                            st.info(aviso)
                    else:
                        st.caption("Sin avisos.")

# ==========================================================
# PIE DE PÁGINA
# ==========================================================
st.caption("Los queries SQL son los mismos de Power Query, pegados tal cual. "
           "Los archivos se generan en memoria y se descargan en la computadora de quien usa la página.")
