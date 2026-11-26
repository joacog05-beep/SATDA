"""SATDA — prototipo B2B para presentación académica (Streamlit).

Ejecutar: python -m streamlit run app.py
Acceso SOLO demostrativo: usuario / usuario. No es autenticación segura.
"""
from __future__ import annotations

import base64
import hashlib
import html
import os
from pathlib import Path
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from satda_core import (
    ALERT_COLORS, ALERT_ORDER, CYAN, FEATURES, GREEN, NAVY,
    PROJECT_EVALUATION_N, PROJECT_METRICS, PROJECT_RL_CONFUSION,
    PURPLE, RED, YELLOW, ModelResult, classify_risk,
    create_demo_dataset, fit_model, read_uploaded_dataset,
    score_scenario, suggested_interventions,
)

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "satda_logo.svg"


def find_builtin_dataset() -> Path:
    """Ubica el Excel del TP tanto en la raíz de GitHub como en data/.

    Acepta asimismo nombres como '(V03) students_performance_dataset (2).xlsx'.
    No usa automáticamente el CSV de alumnos ficticios como sustituto del TP.
    """
    folders = (ROOT, ROOT / "data")
    exact_names = ("students_performance_dataset.xlsx", "students_performance_dataset.csv")

    # Preferimos el dataset colocado junto a app.py, como en el GitHub del usuario.
    for folder in folders:
        for name in exact_names:
            candidate = folder / name
            if candidate.is_file():
                return candidate

    # Los archivos descargados de Excel a veces tienen prefijos/sufijos de versión.
    for folder in folders:
        if not folder.is_dir():
            continue
        matches = sorted(
            (p for p in folder.iterdir()
             if p.is_file() and not p.name.startswith("~$")
             and p.suffix.lower() in {".xlsx", ".csv"}
             and "student" in p.stem.lower()),
            key=lambda p: (p.suffix.lower() != ".xlsx", p.name.lower()),
        )
        if matches:
            return matches[0]

    # También aceptamos cualquier nombre si hay un único Excel en la raíz/data.
    all_excels = [
        p for folder in folders if folder.is_dir()
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() == ".xlsx" and not p.name.startswith("~$")
    ]
    if len(all_excels) == 1:
        return all_excels[0]

    raise FileNotFoundError(
        "No encontré el Excel del TP en GitHub. Subí el archivo .xlsx en la "
        "misma carpeta que app.py (o dentro de data/). El nombre "
        "students_performance_dataset.xlsx es válido, pero no obligatorio."
    )


# Permite importar el dataset académico. Los archivos no se escriben en disco;
# en una instalación pública utilizar solamente datos autorizados y sin nombres reales.
ENABLE_DATA_UPLOAD = os.getenv("SATDA_ENABLE_DATA_UPLOAD", "1").strip().lower() in {"1", "true", "yes"}


st.set_page_config(
    page_title="SATDA | Inteligencia predictiva educativa",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "SATDA · Sistema de Alerta Temprana de Deserción Académica"},
)


# Logo de respaldo incluido directamente en la aplicación, para evitar errores
# cuando GitHub no conserva la carpeta assets/ al cargar archivos manualmente.
EMBEDDED_LOGO_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img" aria-labelledby="title desc">\n<title id="title">SATDA — identidad definitiva</title>\n<desc id="desc">Birrete azul institucional, cuatro nodos violetas de análisis predictivo y arco celeste centrado. Fondo transparente, sin brillos, sombras ni elementos blancos.</desc>\n<!-- Birrete académico: formas planas, sin franjas blancas -->\n<path fill="#102E57" d="M 90 167 Q 88 164 97 159 L 249 88 Q 256 84 263 88 L 415 159 Q 424 164 422 168 L 345 207 Q 256 172 167 207 Z"/>\n<path fill="#102E57" d="M 169 217 Q 256 182 343 217 L 343 260 Q 256 218 169 260 Z"/>\n<!-- Gráfico de cuatro nodos: los extremos están centrados respecto del arco -->\n<path d="M 165.23 341.32 L 198.77 322.68 M 239.12 318.16 L 268.88 326.84 M 309.04 321.98 L 346.96 300.02" stroke="#7454D6" stroke-width="14" fill="none" stroke-linecap="round"/>\n<path d="M 124 352 a 22 22 0 1 0 44 0 a 22 22 0 1 0 -44 0 Z M 137 352 a 9 9 0 1 1 18 0 a 9 9 0 1 1 -18 0 Z M 196 312 a 22 22 0 1 0 44 0 a 22 22 0 1 0 -44 0 Z M 209 312 a 9 9 0 1 1 18 0 a 9 9 0 1 1 -18 0 Z M 268 333 a 22 22 0 1 0 44 0 a 22 22 0 1 0 -44 0 Z M 281 333 a 9 9 0 1 1 18 0 a 9 9 0 1 1 -18 0 Z M 344 289 a 22 22 0 1 0 44 0 a 22 22 0 1 0 -44 0 Z M 357 289 a 9 9 0 1 1 18 0 a 9 9 0 1 1 -18 0 Z" fill="#7454D6" fill-rule="evenodd"/>\n<!-- Arco simétrico de apoyo, extremos x=108/404 (a igual distancia del centro) -->\n<path d="M 108 369 C 154 432 207 449 256 449 C 305 449 358 432 404 369 C 379 429 326 470 256 470 C 186 470 133 429 108 369 Z" fill="#35B9D8"/>\n</svg>'


@st.cache_data(show_spinner=False)
def logo_base64() -> str:
    svg_data = LOGO.read_bytes() if LOGO.is_file() else EMBEDDED_LOGO_SVG.encode("utf-8")
    return base64.b64encode(svg_data).decode("ascii")


def logo_html(width: int = 100) -> str:
    return f'<img src="data:image/svg+xml;base64,{logo_base64()}" width="{width}" height="{width}" alt="Logo SATDA" style="object-fit:contain;display:block;" />'


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'DM Sans',system-ui,Arial,sans-serif; }
[data-testid="stAppViewContainer"] {
  background: radial-gradient(ellipse at 92% 0%, #EAE5FE 0%, transparent 31%),
              linear-gradient(180deg, #F4F7FD 0%, #F8FAFE 100%);
}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stMainBlockContainer"] {max-width:1370px;padding-top:2.1rem;padding-bottom:4rem;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#102E57 0%,#152D58 55%,#25264F 100%);}
[data-testid="stSidebar"] * {color:#EAF0FF;}
[data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.16);}
[data-testid="stSidebar"] [data-testid="stExpander"] {border:1px solid rgba(255,255,255,.22);border-radius:13px;}
[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stFileUploader"] * {color:#263B5E;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {font-weight:700;}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {gap:.27rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label {padding:.38rem .3rem;border-radius:9px;}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover {background:rgba(255,255,255,.08);}
[data-testid="stMetric"] {padding: .25rem 0;}
[data-testid="stMetricValue"] {color:#102E57;font-weight:800;}
.stButton>button[kind="primary"], .stFormSubmitButton>button[kind="primary"] {
  background:linear-gradient(100deg,#102E57,#23559C) !important;
  color:white !important;border:0;border-radius:12px;font-weight:800;box-shadow:0 8px 20px rgba(116,84,214,.19);
}
.stButton>button, .stFormSubmitButton>button {border-radius:12px;font-weight:700;min-height:42px;}
.stDownloadButton>button {border-radius:12px;border:1px solid #D6DEF0;font-weight:700;}
[data-testid="stTabs"] [role="tab"] {font-weight:700;}
[data-testid="stPlotlyChart"] {border:1px solid #E7ECF6;border-radius:17px;background:white;padding:7px 10px;box-shadow:0 7px 22px rgba(29,47,89,.04);}
h1,h2,h3,h4 {color:#122D55 !important;letter-spacing:-.03em;}
hr {border-color:#E6EAF5;}
.brand-head {display:flex;align-items:center;gap:12px; padding:2px 0 22px;}
.brand-name {font-size:24px;font-weight:800;color:white;line-height:1.1;letter-spacing:.07em;}
.brand-sub {font-size:11px;line-height:1.35;color:#B6C6E8;margin-top:4px;}
.small-caps {font-size:11px;letter-spacing:.11em;text-transform:uppercase;font-weight:800;color:#71819C;}
.page-head {margin:.2rem 0 1.25rem;}
.page-head h1 {font-size:2.05rem !important;line-height:1.2;margin:.3rem 0 .25rem;}
.page-head p {margin:0;color:#64728D;max-width:850px;font-size:1rem;}
.hero {background:linear-gradient(112deg,#102E57 0%,#183B75 54%,#5A4DB8 100%);
 border-radius:22px;display:flex;align-items:center;gap:29px;padding:24px 30px;color:#FFF;
 min-height:194px;margin:0 0 1.3rem;box-shadow:0 18px 37px rgba(16,46,87,.14);}
.hero img {background:rgba(255,255,255,.98);border-radius:18px;padding:9px;}
.hero .supra {color:#A8EEFA;font-size:11px;letter-spacing:.17em;font-weight:800;}
.hero h2 {color:#FFF !important;font-size:2rem;margin:.3rem 0 .4rem;line-height:1.13;}
.hero p {margin:0;color:#DCE7FD;max-width:610px;line-height:1.5;}
.hero-tag {display:inline-block;margin-top:14px;padding:5px 11px;background:#FFFFFF21;border:1px solid #FFFFFF46;border-radius:999px;font-size:12px;font-weight:700;color:#EAF7FF;}
.metric-card {background:white;border:1px solid #E5EAF4;border-radius:17px;padding:18px 20px;min-height:123px;
 box-shadow:0 7px 23px rgba(16,46,87,.045);margin-bottom:7px;position:relative;overflow:hidden;}
.metric-card:before {position:absolute;content:'';top:0;left:0;width:100%;height:4px;background:var(--stripe);}
.metric-card .num {font-size:30px;line-height:1.3;color:#102E57;font-weight:800;letter-spacing:-.035em;}
.metric-card .label {font-size:13px;font-weight:700;color:#52657F;margin-bottom:7px;}
.metric-card .mini {font-size:11px;color:#8997AB;line-height:1.2;}
.section-head {display:flex;justify-content:space-between;align-items:center;margin:19px 0 10px;gap:15px;}
.section-title {color:#102E57;font-size:19px;font-weight:800;letter-spacing:-.02em;}
.section-sub {font-size:12px;color:#75839C;}
.status {display:inline-flex;gap:7px;align-items:center;padding:5px 10px;border-radius:999px;font-weight:800;font-size:12px;}
.status-red {background:#FFE9EF;color:#AE2E50;}
.status-yellow {background:#FFF2D8;color:#936100;}
.status-green {background:#DDF6F1;color:#167D70;}
.detail-banner {display:flex;gap:15px;align-items:center;padding:21px 24px;border-radius:18px;
 background:white;border:1px solid #E5EAF4;box-shadow:0 8px 24px rgba(16,46,87,.05);margin:12px 0 19px;}
.student-avatar {flex-shrink:0;display:flex;align-items:center;justify-content:center;width:56px;height:56px;
 border-radius:17px;color:#fff;font-weight:800;font-size:24px;background:linear-gradient(130deg,#7454D6,#35B9D8);}
.student-name {font-size:23px;font-weight:800;color:#102E57;line-height:1.15;}
.student-id {font-size:12px;color:#76869C;margin-top:5px;}
.action-card {background:white;border:1px solid #E5EAF4;border-left:4px solid #35B9D8;
 border-radius:14px;padding:16px 18px;margin:0 0 12px;box-shadow:0 5px 19px rgba(16,46,87,.035);}
.action-card .a-title {font-weight:800;color:#17345F;font-size:14px;margin-bottom:4px;}
.action-card .a-text {font-size:13px;color:#64728D;line-height:1.5;}
.info-strip {background:#EAF4FC;padding:11px 15px;border-radius:12px;color:#315B7D;font-size:12px;line-height:1.5;border:1px solid #D9EAF6;margin:10px 0 20px;}
.login-header {text-align:center;margin:1rem 0 0;}
.login-header h1 {font-size:2.4rem !important;margin:0 0 .25rem;}
.login-header p {color:#66758E;margin:0 auto 24px;max-width:550px;}
.login-logo {display:flex;justify-content:center;margin:25px auto 12px;background:white;max-width:170px;padding:13px;
 border:1px solid #E6ECF8;border-radius:28px;box-shadow:0 12px 32px rgba(16,46,87,.08);}
.login-card {text-align:center;background:white;padding:13px 24px;border:1px solid #E5EBF6;border-radius:16px;margin-bottom:12px;}
.footer {font-size:11px;color:#7A8AA4;text-align:center;padding:26px 0 6px;}
/* Legibilidad: Streamlit puede usar estilos oscuros heredados de navegador. */
[data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] p,
[data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] p,
[data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] p,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] > p,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] > ul,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] > ol,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] li,
[data-testid="stMainBlockContainer"] .stMarkdown p {color:#465771 !important;opacity:1!important;}
[data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] p,
[data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] p {color:#53627A!important;font-weight:650!important;}
[data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] p {color:#53627A!important;}
[data-testid="stMainBlockContainer"] .hero p {color:#E2EDFF!important;}
[data-testid="stMainBlockContainer"] .hero .supra {color:#A8EEFA!important;}
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] strong {color:#1C3761;}
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] .hero strong {color:#FFF;}
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] .info-strip {color:#2F536F;}
[data-testid="stMainBlockContainer"] [data-testid="stSelectbox"] label p,
[data-testid="stMainBlockContainer"] [data-testid="stSlider"] label p,
[data-testid="stMainBlockContainer"] [data-testid="stToggle"] label p,
[data-testid="stMainBlockContainer"] [data-testid="stTextInput"] label p {color:#4A5E79!important;}
[data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] {color:#102E57!important;}
[data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"] {font-weight:700;}
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] .footer {color:#60728C;}
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] .metric-card .mini {color:#5F7089;}
[data-testid="stMainBlockContainer"] [data-testid="stTextInput"] input {color:#243750!important;}
/* Contraste accesible para TODOS los textos dentro de botones azules.
   Streamlit a veces dibuja la etiqueta dentro de <p> o <span> y hereda otro color. */
[data-testid="stAppViewContainer"] .stButton button[kind="primary"],
[data-testid="stAppViewContainer"] .stFormSubmitButton button[kind="primary"],
[data-testid="stAppViewContainer"] button[data-testid="stBaseButton-primary"] {
  background:linear-gradient(105deg,#102E57,#1F5293)!important;
  border:1px solid #102E57!important;
  color:#FFFFFF!important;
}
[data-testid="stAppViewContainer"] .stButton button[kind="primary"] *,
[data-testid="stAppViewContainer"] .stFormSubmitButton button[kind="primary"] *,
[data-testid="stAppViewContainer"] button[data-testid="stBaseButton-primary"] *,
[data-testid="stAppViewContainer"] .stButton button[kind="primary"] p,
[data-testid="stAppViewContainer"] .stFormSubmitButton button[kind="primary"] p {
  color:#FFFFFF!important;fill:#FFFFFF!important;opacity:1!important;
  -webkit-text-fill-color:#FFFFFF!important;
}
/* Estilos legados secundarios: reemplazados por el bloque v1.3 de contraste al final. */
[data-testid="stAppViewContainer"] .stButton button[kind="secondary"],
[data-testid="stAppViewContainer"] button[data-testid="stBaseButton-secondary"] {
  background:#FFFFFF!important;border:1.5px solid #23558E!important;
  color:#102E57!important;
}
[data-testid="stAppViewContainer"] .stButton button[kind="secondary"] *,
[data-testid="stAppViewContainer"] button[data-testid="stBaseButton-secondary"] * {
  color:#102E57!important;opacity:1!important;
  -webkit-text-fill-color:#102E57!important;
}
[data-testid="stAppViewContainer"] .stButton button:focus-visible {
  outline:3px solid #35B9D8!important;outline-offset:2px;
}

/* Panel del modelo: botones azules en lugar de pestañas con texto poco contrastado */
.st-key-satda_model_tab_0 button, .st-key-satda_model_tab_1 button, .st-key-satda_model_tab_2 button {min-height:52px;border-radius:13px!important;}
@media(max-width:750px){.hero {padding:18px;gap:15px}.hero img{width:80px;height:80px}.hero h2{font-size:1.3rem !important}.page-head h1{font-size:1.55rem !important}.metric-card{padding:13px}.metric-card .num{font-size:24px}}

/* SATDA v1.3 — contraste consistente en controles interactivos.
   Corrección de textos oscuros sobre botones azules/negros y sobre el buscador.
   Este bloque está al final para prevalecer sobre los estilos anteriores. */
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stButton button,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stFormSubmitButton button,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] button[data-testid^="stBaseButton-"] {
  background:#163A70 !important;
  background-image:linear-gradient(105deg,#102E57,#245497) !important;
  border:1px solid #153C75 !important;
  color:#FFFFFF !important;
  -webkit-text-fill-color:#FFFFFF !important;
  opacity:1 !important;
  font-weight:750 !important;
}
/* La etiqueta del botón está en un <p> interno en algunas versiones de Streamlit.
   Forzar el color en el propio texto, no solo en el elemento button. */
html body [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stButton button :is(p,span,div,strong,small),
html body [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stFormSubmitButton button :is(p,span,div,strong,small),
html body [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] button[data-testid^="stBaseButton-"] :is(p,span,div,strong,small),
html body [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stButton button svg,
html body [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stFormSubmitButton button svg {
  color:#FFFFFF !important;
  -webkit-text-fill-color:#FFFFFF !important;
  fill:currentColor !important;
  opacity:1 !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stButton button:hover,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stFormSubmitButton button:hover,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] button[data-testid^="stBaseButton-"]:hover {
  background:#2B63AE !important;
  background-image:none !important;
  color:#FFFFFF !important;
  border-color:#3273C4 !important;
}
/* Botón sin habilitar: continúa siendo perceptiblemente inactivo pero legible. */
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stButton button:disabled,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] .stFormSubmitButton button:disabled {
  background:#506787 !important;
  background-image:none !important;
  border-color:#506787 !important;
  color:#FFFFFF !important;
  -webkit-text-fill-color:#FFFFFF !important;
  opacity:.82 !important;
  cursor:not-allowed !important;
}
/* Navegación de Modelo y métricas: tres botones de la marca, texto blanco.
   La opción activa mantiene un azul más claro para distinguirla. */
[data-testid="stAppViewContainer"] [class*="st-key-satda_model_tab_"] button {
  background:#163763 !important;
  background-image:none !important;
  border:1px solid #274C82 !important;
  color:#FFFFFF !important;
  -webkit-text-fill-color:#FFFFFF !important;
  min-height:52px !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-satda_model_tab_"] button[kind="primary"],
[data-testid="stAppViewContainer"] [class*="st-key-satda_model_tab_"] button[data-testid="stBaseButton-primary"] {
  background:#2355A0 !important;
  background-image:none !important;
  border:1px solid #2355A0 !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-satda_model_tab_"] button :is(p,span,div,strong) {
  color:#FFFFFF !important;
  -webkit-text-fill-color:#FFFFFF !important;
  opacity:1 !important;
}
/* Buscador de StudentID: mantener fondo oscuro pero texto y marcador claros. */
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] div[data-baseweb="input"],
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] div[data-baseweb="base-input"] {
  background:#252932 !important;
  border-color:#52658A !important;
  color:#FFFFFF !important;
}
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] input,
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] div[data-baseweb="input"] input {
  background:#252932 !important;
  color:#FFFFFF !important;
  -webkit-text-fill-color:#FFFFFF !important;
  caret-color:#FFFFFF !important;
  opacity:1 !important;
}
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] input::placeholder {
  color:#C9D6E9 !important;
  -webkit-text-fill-color:#C9D6E9 !important;
  opacity:1 !important;
}
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] [data-testid="InputInstructions"],
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] [data-testid="InputInstructions"] *,
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] [data-testid="stInputInstructions"],
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] [data-testid="stInputInstructions"] * {
  color:#EFF4FF !important;
  -webkit-text-fill-color:#EFF4FF !important;
}
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stAppViewContainer"] [data-testid="stTextInput"] div[data-baseweb="base-input"]:focus-within {
  border-color:#35B9D8 !important;
  box-shadow:0 0 0 1px #35B9D8 !important;
}

</style>
""", unsafe_allow_html=True)


def h(value: str) -> str:
    return html.escape(str(value), quote=True)


def fmt_num(number: float, decimals: int = 0) -> str:
    return f"{number:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def metric_tile(label: str, value: str, note: str, accent: str) -> None:
    st.markdown(f'<div class="metric-card" style="--stripe:{accent}"><div class="label">{h(label)}</div>'
                f'<div class="num">{h(value)}</div><div class="mini">{h(note)}</div></div>', unsafe_allow_html=True)


def section(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="section-head"><span class="section-title">{h(title)}</span>'
                f'<span class="section-sub">{h(subtitle)}</span></div>', unsafe_allow_html=True)


def page_heading(tag: str, title: str, description: str) -> None:
    st.markdown(f'<div class="page-head"><span class="small-caps">{h(tag)}</span><h1>{h(title)}</h1>'
                f'<p>{h(description)}</p></div>', unsafe_allow_html=True)


def risk_badge(alert: str) -> str:
    css = {"Alerta roja": "red", "Alerta amarilla": "yellow", "Sin alerta": "green"}[alert]
    return f'<span class="status status-{css}">● {h(alert)}</span>'


def fig_style(fig: go.Figure, height: int = 320, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=18, r=18, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color="#253D62", size=12),
        showlegend=legend, hoverlabel=dict(bgcolor="#102E57", font_color="white"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color="#64748B"))
    fig.update_yaxes(gridcolor="#EDF1F7", zeroline=False, tickfont=dict(color="#64748B"))
    return fig


def render_chart(fig: go.Figure, key: str) -> None:
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    st.plotly_chart(fig, use_container_width=True, theme=None,
                    config={"displayModeBar": False, "responsive": True,
                            "scrollZoom": False, "doubleClick": False}, key=key)


@st.cache_resource(show_spinner=False)
def bundled_result() -> ModelResult:
    dataset_path = find_builtin_dataset()
    data = read_uploaded_dataset(dataset_path.read_bytes(), dataset_path.name)
    return fit_model(data, is_demo=False)


def get_current_result() -> tuple[ModelResult, str]:
    """Nunca sustituir silenciosamente un Excel rechazado por 360 alumnos demo."""
    if ENABLE_DATA_UPLOAD and st.session_state.get("data_mode", "Base del trabajo práctico") == "Cargar archivo":
        uploaded = st.session_state.get("user_dataset")
        if uploaded is None:
            st.info("Seleccioná un archivo .xlsx o .csv en «Fuente de información» para abrir su panel.")
            st.stop()
        raw = uploaded.getvalue()
        # Versión de parser en la clave: revalida archivos que fallaron en versiones anteriores.
        sig = hashlib.sha256(raw).hexdigest() + ":parser-v1.2"
        if st.session_state.get("uploaded_sha") != sig:
            try:
                df = read_uploaded_dataset(raw, uploaded.name)
                sample_only = ("ficticio" in uploaded.name.lower() or "demo" in uploaded.name.lower())
                with st.spinner("Validando columnas y entrenando los cinco modelos..."):
                    result = fit_model(df, is_demo=sample_only)
                st.session_state["uploaded_result"] = result
                st.session_state["uploaded_sha"] = sig
                st.session_state["upload_error"] = None
                st.session_state["selected_student"] = None
            except Exception as exc:
                st.session_state["upload_error"] = str(exc)
                st.session_state["uploaded_result"] = None
                st.session_state["uploaded_sha"] = sig
        if st.session_state.get("uploaded_result") is None:
            st.error("El archivo no se pudo cargar: " + str(st.session_state.get("upload_error") or "Error desconocido."))
            st.info("El tablero no muestra datos de otra fuente. Verificá el formato del Excel y volvé a cargarlo.")
            st.stop()
        saved = st.session_state["uploaded_result"]
        return saved, "Archivo de ejemplo" if saved.is_demo else "Archivo importado"
    try:
        return bundled_result(), "Base del trabajo práctico"
    except Exception as exc:
        st.error("No se pudo abrir la base incluida con SATDA: " + str(exc))
        st.info("El archivo puede estar junto a `app.py` o en `data/`. Si está presente pero falla su lectura, comprobá que `requirements.txt` incluya `openpyxl`.")
        st.stop()


def login_page() -> None:
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    left, center, right = st.columns([1, 1.12, 1], gap="large")
    with center:
        st.markdown(f'<div class="login-logo">{logo_html(132)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-header"><div class="small-caps">INTELIGENCIA PREDICTIVA EDUCATIVA</div>'
                    '<h1>Bienvenido a SATDA</h1><p>Transformamos datos académicos en decisiones de acompañamiento temprano.</p></div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="login-card"><b>Acceso institucional · Demostración</b><br>'
                    '<span style="font-size:12px;color:#6B7A96">Ingresá con las credenciales de prueba para explorar la plataforma.</span></div>',
                    unsafe_allow_html=True)
        with st.form("demo_login", border=False):
            user = st.text_input("Usuario", placeholder="Ingresá tu usuario", autocomplete="username")
            password = st.text_input("Contraseña", type="password", placeholder="Ingresá tu contraseña", autocomplete="current-password")
            submit = st.form_submit_button("Ingresar a SATDA  →", use_container_width=True, type="primary")
        if submit:
            if user == "usuario" and password == "usuario":
                st.session_state["logged_in"] = True
                st.session_state["view"] = "Resumen institucional"
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos. Para esta demo ambos son «usuario».")
        st.info("**Acceso de demostración:** usuario `usuario` · contraseña `usuario`.", icon="🔐")
        st.markdown('<div class="footer">SATDA · Plataforma de análisis educativo</div>', unsafe_allow_html=True)


def logout_callback() -> None:
    for key in ("uploaded_result", "uploaded_sha", "upload_error", "user_dataset", "selected_student"):
        st.session_state.pop(key, None)
    st.session_state["logged_in"] = False


def sidebar_controls() -> None:
    with st.sidebar:
        st.markdown(f'<div class="brand-head">{logo_html(58)}<div><div class="brand-name">SATDA</div>'
                    '<div class="brand-sub">Plataforma de alerta temprana<br>para instituciones educativas</div></div></div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#A2B9DE;font-size:10px;font-weight:800;letter-spacing:.15em;margin-bottom:9px">ESPACIO INSTITUCIONAL</div>', unsafe_allow_html=True)
        st.radio("Secciones", ["Resumen institucional", "Ficha de estudiante", "Modelo y métricas", "Acerca del sistema"],
                 label_visibility="collapsed", key="view", captions=["Indicadores y prioridades", "Búsqueda e intervención", "Resultados y comparación", "Aplicaciones institucionales"])
        st.divider()
        with st.expander("⚙️  Fuente de información", expanded=False):
            if ENABLE_DATA_UPLOAD:
                st.radio("Origen de datos", ["Base del trabajo práctico", "Cargar archivo"], key="data_mode")
                if st.session_state["data_mode"] == "Cargar archivo":
                    st.file_uploader("Dataset (.xlsx o .csv)", type=["xlsx", "csv"], key="user_dataset")
                    st.caption("Columnas: Absences, Tutoring, ParentalSupport y GradeClass. StudentID y nombres son opcionales.")
                    st.caption("Utilizá exclusivamente bases académicas autorizadas o anonimizadas.")
                else:
                    st.caption("students_performance_dataset.xlsx · 2.343 registros")
            else:
                st.session_state["data_mode"] = "Base del trabajo práctico"
                st.caption("Base del trabajo práctico")
        st.markdown('<div style="color:#B8C7E5;font-size:12px;line-height:1.6;margin-top:12px">'
                    '🧑‍🏫 Vista docente y directiva<br>🎯 Objetivo: riesgo de nota D/F<br>🛡️ Requiere supervisión humana</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
        st.button("Cerrar sesión", use_container_width=True, on_click=logout_callback)


def source_notice(result: ModelResult, label: str) -> None:
    # La carga se valida antes de renderizar: sin sustituciones ni datos heredados.
    return


def donut(records: pd.DataFrame) -> go.Figure:
    counts = records["Alert"].value_counts().reindex(ALERT_ORDER, fill_value=0)
    fig = go.Figure(go.Pie(labels=list(counts.index), values=counts.values, hole=.72,
                           marker=dict(colors=[ALERT_COLORS[n] for n in counts.index], line=dict(color="#FFFFFF", width=3)),
                           textinfo="percent", textposition="outside", sort=False,
                           hovertemplate="<b>%{label}</b><br>%{value} estudiantes · %{percent}<extra></extra>"))
    fig.update_layout(annotations=[dict(text=f'<b>{fmt_num(len(records))}</b><br><span style="font-size:12px">estudiantes</span>',
                                       font=dict(size=24, color=NAVY), showarrow=False)],
                      legend=dict(orientation="h", x=.5, xanchor="center", y=-.05, font=dict(size=11)))
    return fig_style(fig, 330, legend=True)


def absences_chart(records: pd.DataFrame) -> go.Figure:
    labels = ["0–5", "6–10", "11–15", "16–20", "21–25", "26–30", "Sin dato"]
    groups = pd.cut(records["Absences"], bins=[-1, 5, 10, 15, 20, 25, 30], labels=labels[:6])
    data = records.assign(Group=groups.astype("object").fillna("Sin dato"))
    fig = go.Figure()
    for priority in ["Sin alerta", "Alerta amarilla", "Alerta roja"]:
        g = data.loc[data["Alert"] == priority].groupby("Group").size().reindex(labels, fill_value=0)
        fig.add_trace(go.Bar(x=labels, y=g.values, name=priority,
            marker_color=ALERT_COLORS[priority],
            hovertemplate="Inasistencias: %{x}<br>%{y} estudiantes<extra>"+priority+"</extra>"))
    fig_style(fig, 335, legend=True)
    fig.update_layout(barmode="stack", bargap=.25,
        margin=dict(l=48,r=10,t=68,b=48),
        legend=dict(orientation="h", x=.5, xanchor="center", y=1.24,
                    yanchor="top", font=dict(size=11), traceorder="normal"),
        xaxis=dict(title=None, tickangle=0, tickfont=dict(size=10.5)),
        yaxis=dict(title=None, rangemode="tozero", tickformat=",d"))
    return fig


def risk_distribution(records: pd.DataFrame) -> go.Figure:
    """Barras discretas por deciles, sin zoom ni desplazamiento accidental."""
    edges = list(range(0, 101, 10))
    cats = [f"{a}–{b} %" for a, b in zip(edges[:-1],edges[1:])]
    r = records.copy()
    r["Decil"] = pd.cut(r["RiskProbability"]*100, bins=edges, labels=cats,
                        include_lowest=True).astype(str)
    fig = go.Figure()
    for priority in ["Sin alerta", "Alerta amarilla", "Alerta roja"]:
        counts = r.loc[r["Alert"]==priority, "Decil"].value_counts().reindex(cats,fill_value=0)
        fig.add_trace(go.Bar(x=cats, y=counts.values, name=priority,
                 marker_color=ALERT_COLORS[priority],
                 customdata=[priority]*len(cats),
                 hovertemplate="Rango de riesgo: %{x}<br>Estudiantes: %{y}<extra>"+priority+"</extra>"))
    fig_style(fig, 290, legend=True)
    fig.update_layout(barmode="stack", bargap=.20,
                      margin=dict(l=50, r=16, t=58, b=55),
                      legend=dict(orientation="h", x=.5, xanchor="center", y=1.27, yanchor="top",font=dict(size=12)),
                      xaxis=dict(title=None,tickfont=dict(size=11),tickangle=0),
                      yaxis=dict(title=None,tickformat=",d",rangemode="tozero"))
    return fig


def risk_gauge(p: float) -> go.Figure:
    val = p * 100
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val, number={"suffix": "%", "valueformat": ".1f", "font": {"size": 42, "color": NAVY}},
        title={"text": "Probabilidad estimada de nota D/F", "font": {"size": 15, "color": "#516786"}},
        gauge={"axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "#ffffff", "ticksuffix": "%"},
               "bar": {"color": PURPLE, "thickness": .28}, "bgcolor": "#F3F6FA", "borderwidth": 0,
               "steps": [{"range": [0, 50], "color": "#D8F3EE"},
                         {"range": [50, 80], "color": "#FCEED7"},
                         {"range": [80, 100], "color": "#FCE0E7"}]},
    ))
    return fig_style(fig, 290)


def benchmark_fig(metrics: pd.DataFrame) -> go.Figure:
    m = metrics.set_index("Modelo").reindex(["Regresión Logística", "Gradient Boosting", "AdaBoost", "KNN", "Random Forest"])
    fig = go.Figure()
    names = list(m.index)
    fig.add_trace(go.Bar(x=names, y=m["Recall"]*100, name="Recall", marker_color=CYAN, text=[f"{v:.1f}" for v in m["Recall"]*100], textposition="outside"))
    fig.add_trace(go.Bar(x=names, y=m["Precisión"]*100, name="Precisión", marker_color=PURPLE, text=[f"{v:.1f}" for v in m["Precisión"]*100], textposition="outside"))
    fig.add_trace(go.Bar(x=names, y=m["F1-Score"]*100, name="F1-Score", marker_color=NAVY, text=[f"{v:.1f}" for v in m["F1-Score"]*100], textposition="outside"))
    fig.update_layout(barmode="group", yaxis=dict(range=[0, 110], title="Puntuación (%)"),
                      legend=dict(orientation="h", x=.5, xanchor="center", y=1.16), xaxis_tickangle=-10)
    return fig_style(fig, 390, legend=True)


def errors_fig(metrics: pd.DataFrame) -> go.Figure:
    m = metrics.sort_values("FN", ascending=True)
    fig = go.Figure(go.Bar(y=m["Modelo"], x=m["FN"], orientation="h",
                           marker_color=[PURPLE if name=="Regresión Logística" else CYAN for name in m["Modelo"]],
                           text=m["FN"], textposition="outside",
                           hovertemplate="%{y}<br>%{x} casos D/F no detectados<extra></extra>"))
    fig.update_layout(xaxis_title="Falsos negativos (conjunto de prueba)", yaxis=dict(autorange="reversed"))
    return fig_style(fig, 310)


def confusion_fig(cm: np.ndarray) -> go.Figure:
    fig = go.Figure(go.Heatmap(z=cm, x=["Pred. A/B/C", "Pred. D/F"], y=["Real A/B/C", "Real D/F"],
                               colorscale=[[0, "#EDF6FC"], [.5, "#68C8E2"], [1, "#173D76"]], showscale=False,
                               text=cm, texttemplate="<b>%{text}</b>", textfont={"size": 26},
                               hovertemplate="%{y} · %{x}<br>%{z} estudiantes<extra></extra>"))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig_style(fig, 280)


def open_student_from_dashboard(student_id: str) -> None:
    """Callback: se ejecuta antes de instanciar el radio de navegación en el rerun."""
    st.session_state["selected_student"] = student_id
    st.session_state["view"] = "Ficha de estudiante"


def lookup_widget(records: pd.DataFrame, key: str, jump: bool) -> str | None:
    col_a, col_b = st.columns([2.2, 1.0], gap="small")
    with col_a:
        search = st.text_input("Buscar por StudentID o nombre registrado", placeholder="Ej.: 1817, 2896 o apellido (si está registrado)", key=f"{key}_query")
    s = search.strip()
    if s:
        matches = records.loc[records["StudentID"].str.contains(re.escape(s), case=False, na=False) |
                              records["FullName"].str.contains(re.escape(s), case=False, na=False)]
    else:
        matches = records.head(30)
        remembered = st.session_state.get("selected_student")
        if remembered and remembered in set(records["StudentID"]):
            extra = records.loc[records["StudentID"] == remembered]
            matches = pd.concat([extra, matches], ignore_index=True).drop_duplicates("StudentID")
    matches = matches.head(30)
    if matches.empty:
        st.warning("No encontramos estudiantes que coincidan. Revisá el nombre o el identificador.")
        return None
    id_to_rec = matches.drop_duplicates("StudentID").set_index("StudentID")
    labels = {sid: f"{rec['FullName']}  ·  {sid}  ·  {rec['RiskProbability']:.0%} D/F"
              for sid, rec in id_to_rec.iterrows()}
    with col_b:
        remembered = st.session_state.get("selected_student")
        defaults = list(labels)
        idx = defaults.index(remembered) if key == "student_search" and remembered in defaults else 0
        selected = st.selectbox("Coincidencias", options=defaults, index=idx, format_func=lambda sid: labels[sid], key=f"{key}_choice")
    st.caption(f"{len(matches)} coincidencia(s) visibles. La búsqueda es parcial y no requiere nombre completo.")
    if jump:
        st.button("Abrir ficha del estudiante  →", type="primary", key=f"{key}_open",
                  on_click=open_student_from_dashboard, args=(selected,))
    return selected


def dashboard(result: ModelResult, mode: str) -> None:
    rows = result.records
    st.markdown(f'<div class="hero">{logo_html(125)}<div><div class="supra">SATDA · CENTRO DE ALERTAS</div>'
                '<h2>Decisiones a tiempo.<br>Trayectorias con más apoyo.</h2>'
                '<p>Una vista institucional de estudiantes, riesgos académicos y oportunidades de acompañamiento preventivo.</p>'
                f'<span class="hero-tag">{h(mode)}</span></div></div>', unsafe_allow_html=True)
    source_notice(result, mode)
    c = rows["Alert"].value_counts()
    high = int(c.get("Alerta roja", 0)); medium = int(c.get("Alerta amarilla", 0)); low = int(c.get("Sin alerta", 0))
    tiles = st.columns(4, gap="medium")
    with tiles[0]: metric_tile("Estudiantes en el panel", fmt_num(len(rows)), "Base disponible", NAVY)
    with tiles[1]: metric_tile("Atención prioritaria", fmt_num(high), "Probabilidad D/F > 80 %", RED)
    with tiles[2]: metric_tile("Seguimiento sugerido", fmt_num(medium), "Probabilidad D/F 50–80 %", YELLOW)
    with tiles[3]: metric_tile("Sin alerta activa", fmt_num(low), "Probabilidad D/F < 50 %", GREEN)
    section("Panorama institucional", "Distribución de alertas y relación con la asistencia")
    a, b = st.columns([.86, 1.14], gap="medium")
    with a:
        st.markdown("**Distribución global de alertas**")
        render_chart(donut(rows), "dashboard_donut")
    with b:
        st.markdown("**Inasistencias por nivel de alerta**")
        render_chart(absences_chart(rows), "dashboard_absences")
    section("Explorar estudiantes", "Búsqueda rápida por nombre o identificación")
    lookup_widget(rows, "dash_search", jump=True)
    section("Bandeja de seguimiento", "Ordenada por mayor probabilidad estimada de D/F")
    x, y = st.columns([2.1, 1], gap="medium")
    with y:
        filter_alert = st.selectbox("Filtrar por prioridad", ["Todas las alertas", *ALERT_ORDER], key="queue_filter")
    filtered = rows if filter_alert == "Todas las alertas" else rows.loc[rows["Alert"] == filter_alert]
    visible = filtered.copy()
    visible["Probabilidad D/F"] = (visible["RiskProbability"]*100).round(1)
    visible["Tutorías"] = visible["Tutoring"].map({0.0: "No", 1.0: "Sí"}).fillna("Sin dato")
    visible["Inasistencias"] = visible["Absences"].round(0)
    visible = visible.rename(columns={"StudentID": "StudentID", "FullName": "Estudiante", "Alert": "Prioridad"})
    st.dataframe(visible[["StudentID", "Estudiante", "Prioridad", "Inasistencias", "Tutorías", "Probabilidad D/F"]].head(100),
                 hide_index=True, use_container_width=True, height=300,
                 column_config={"Probabilidad D/F": st.column_config.ProgressColumn("Riesgo D/F (%)", format="%.1f%%", min_value=0, max_value=100),
                                "Inasistencias": st.column_config.NumberColumn("Inasistencias", format="%.0f")})
    st.caption("El panel muestra hasta 100 registros ordenados; el archivo descargable respeta el filtro completo.")
    export = visible[["StudentID", "Estudiante", "Prioridad", "Inasistencias", "Tutorías", "Probabilidad D/F"]]
    st.download_button("⬇️  Exportar listado filtrado (CSV)", data=export.to_csv(index=False).encode("utf-8-sig"),
                       file_name="SATDA_seguimiento.csv", mime="text/csv", key="dashboard_csv")
    section("Distribución de probabilidades", "Cortes de alerta: 50 % y 80 %")
    render_chart(risk_distribution(rows), "dashboard_distribution")
    st.caption("Las alertas sirven para ordenar la revisión humana, no para diagnosticar deserción ni sancionar estudiantes.")


def student_profile(result: ModelResult, mode: str) -> None:
    rows = result.records
    page_heading("FICHA ACADÉMICA", "Consulta individual del estudiante", "Buscá por nombre o StudentID, revisá señales académicas y explorá acciones de apoyo.")
    source_notice(result, mode)
    chosen = lookup_widget(rows, "student_search", jump=False)
    if chosen is None:
        return
    selected = st.session_state.get("selected_student")
    # Usar la ficha elegida por el usuario; el selector de coincidencias tiene prioridad al buscar.
    if st.session_state.get("student_search_query", "").strip():
        selected = chosen
    elif not selected or selected not in rows["StudentID"].values:
        selected = chosen
    # El selector manual siempre gobierna si ya fue modificado.
    if st.session_state.get("student_search_choice") != selected:
        selected = st.session_state["student_search_choice"]
    record = rows.loc[rows["StudentID"] == selected].iloc[0]
    st.session_state["selected_student"] = selected
    initials = "".join(n[0] for n in str(record["FullName"]).split()[:2]).upper() or "ST"
    st.markdown(f'<div class="detail-banner"><div class="student-avatar">{h(initials)}</div>'
                f'<div style="flex:1"><div class="student-name">{h(record["FullName"])}</div>'
                f'<div class="student-id">StudentID: {h(record["StudentID"])} · Nota registrada: {h(record["GradeLabel"])}'
                f'{" (ficticia)" if result.is_demo else " (histórica)"}</div></div>{risk_badge(record["Alert"])}</div>', unsafe_allow_html=True)

    lc, rc = st.columns([1, 1.1], gap="large")
    with lc:
        render_chart(risk_gauge(float(record["RiskProbability"])), "student_gauge")
        st.caption("Estimación de nota crítica D/F — **no** es una probabilidad de deserción académica.")
    with rc:
        st.markdown("### Indicadores registrados")
        k1, k2 = st.columns(2)
        with k1:
            st.metric("Inasistencias", f"{fmt_num(record['Absences']) if pd.notna(record['Absences']) else 'S/D'} / 30")
            st.metric("Tutorías", "Participa" if float(record["Tutoring"]) == 1 else "No participa" if pd.notna(record["Tutoring"]) else "Sin dato")
        with k2:
            plabel = ["Sin apoyo", "Bajo", "Moderado", "Alto", "Muy alto"]
            pv = record["ParentalSupport"]
            support = plabel[int(pv)] if pd.notna(pv) and int(pv) in range(5) else "Sin dato"
            st.metric("Apoyo familiar (registrado)", support)
            if "StudyTimeWeekly" in record.index and pd.notna(record["StudyTimeWeekly"]):
                st.metric("Estudio semanal (contexto)", f"{fmt_num(record['StudyTimeWeekly'], 1)} h")
        st.caption("El modelo solo usa inasistencias, tutorías y apoyo familiar. Otras variables son informativas, si están disponibles.")
    section("Acciones recomendadas", "Orientación preventiva para tutoría o coordinación")
    st.markdown('<div class="info-strip">🧑‍🏫 Estas sugerencias responden a señales observadas en el registro, '
                'no a causas demostradas por el algoritmo. Requieren contexto y decisión profesional.</div>', unsafe_allow_html=True)
    actions = suggested_interventions(record)
    columns = st.columns(len(actions), gap="small")
    for col, (icon, title, description) in zip(columns, actions):
        with col:
            st.markdown(f'<div class="action-card"><div class="a-title">{h(title)}</div>'
                        f'<div class="a-text">{h(description)}</div></div>', unsafe_allow_html=True)
    section("Simulador de escenarios", "Exploración, no efecto causal validado")
    st.markdown("Modificá variables **hipotéticas** y observá cómo responde el modelo. Esto no edita los datos originales del estudiante.")
    default_abs = int(record["Absences"]) if pd.notna(record["Absences"]) else 10
    default_tut = bool(record["Tutoring"]) if pd.notna(record["Tutoring"]) else False
    default_par = int(record["ParentalSupport"]) if pd.notna(record["ParentalSupport"]) else 2
    s1, s2, s3 = st.columns(3, gap="medium")
    with s1: a = st.slider("Inasistencias (0 a 30)", 0, 30, default_abs, 1, key=f"sc_abs_{selected}")
    with s2: t = st.toggle("Participación en tutorías", value=default_tut, key=f"sc_tut_{selected}")
    with s3: pa = st.select_slider("Apoyo familiar registrado (0 a 4)", options=[0, 1, 2, 3, 4], value=default_par, key=f"sc_par_{selected}")
    scenario = score_scenario(result.model, a, int(t), pa)
    old = float(record["RiskProbability"])
    cols = st.columns([.84, 1.16], gap="large")
    with cols[0]:
        st.metric("Riesgo en el escenario", f"{scenario*100:.1f} %".replace(".", ","),
                  delta=f"{(scenario-old)*100:+.1f} pp".replace(".", ","), delta_color="inverse")
        st.markdown(risk_badge(classify_risk(scenario)), unsafe_allow_html=True)
    with cols[1]:
        fig = go.Figure(go.Bar(x=[old*100, scenario*100], y=["Registro", "Escenario"], orientation="h",
                               marker_color=["#B2C6E2", PURPLE], text=[f"{old*100:.1f} %", f"{scenario*100:.1f} %"],
                               textposition="inside", insidetextanchor="end"))
        fig.update_layout(xaxis=dict(range=[0, 100], title="Probabilidad estimada de D/F (%)"), yaxis=dict(autorange="reversed"))
        render_chart(fig_style(fig, 190), "scenario_compare")
    st.caption("Importante: un cambio en la estimación no implica que modificar una variable produzca necesariamente ese efecto. El modelo describe asociaciones de datos históricos.")


def model_page(result: ModelResult, mode: str) -> None:
    page_heading("ANÁLISIS PREDICTIVO", "Modelo y métricas", "Resultados comparativos para evaluar el desempeño y respaldar decisiones académicas.")
    source_notice(result, mode)
    choices = ["📊 Resultados del proyecto", "📈 Dataset actual", "🎯 Metodología"]
    if "satda_metrics_view" not in st.session_state:
        st.session_state["satda_metrics_view"] = choices[0]
    buttons = st.columns(3, gap="small")
    for idx, (column, name) in enumerate(zip(buttons, choices)):
        with column:
            if st.button(name, key=f"satda_model_tab_{idx}", use_container_width=True,
                         type="primary" if st.session_state["satda_metrics_view"] == name else "secondary"):
                st.session_state["satda_metrics_view"] = name
                st.rerun()
    if st.session_state["satda_metrics_view"] == choices[0]:
        st.caption("Resultados históricos del trabajo práctico: 2.343 registros · partición 80 % entrenamiento / 20 % prueba.")
        rl = PROJECT_METRICS.set_index("Modelo").loc["Regresión Logística"]
        cols = st.columns(4)
        for col, (lab, val, expl, color) in zip(cols,[
            ("Recall", f"{rl['Recall']*100:.2f} %", "Casos D/F identificados", CYAN),
            ("Precisión", f"{rl['Precisión']*100:.2f} %", "Alertas positivas acertadas", PURPLE),
            ("F1-Score", f"{rl['F1-Score']:.4f}", "Balance de precisión y Recall", NAVY),
            ("AUC-ROC", f"{rl['AUC-ROC']:.4f}", "Separación global de clases", GREEN),
        ]):
            with col: metric_tile(lab, val.replace(".", ","), expl, color)
        section("Cinco modelos, mismos datos de prueba", "Comparación Recall / Precisión / F1")
        render_chart(benchmark_fig(PROJECT_METRICS), "bench_bars")
        two = st.columns([1,1],gap="medium")
        with two[0]:
            st.markdown("**Errores que más importan: falsos negativos**")
            render_chart(errors_fig(PROJECT_METRICS), "bench_errors")
        with two[1]:
            st.markdown("**Matriz de confusión · Regresión Logística**")
            render_chart(confusion_fig(PROJECT_RL_CONFUSION), "bench_confusion")
        st.markdown("**¿Por qué Regresión Logística?**")
        st.write("Gradient Boosting detectó más casos D/F (Recall de 96,24 % frente a 94,36 %), pero Regresión Logística logró la mayor precisión (81,79 %) y el mayor F1-Score (0,8763) de los modelos evaluados. Se seleccionó como motor inicial por su balance de desempeño, interpretabilidad y menor complejidad de despliegue.")
        with st.expander("Tabla completa de métricas experimentales"):
            st.dataframe(PROJECT_METRICS.drop(columns=["FN", "FP"]).style.format({m:"{:.4f}" for m in ["AUC-ROC","Recall","Precisión","F1-Score","Accuracy"]}), hide_index=True, use_container_width=True)
        st.caption(f"Conjunto de evaluación: {PROJECT_EVALUATION_N} estudiantes · Matriz: VP=301, FN=18, FP=67, VN=83.")
    elif st.session_state["satda_metrics_view"] == choices[1]:
        if result.is_demo:
            st.caption("Los resultados de esta vista corresponden al conjunto de ejemplo.")
        else:
            st.caption("Métricas recalculadas sobre el 20 % reservado del dataset seleccionado (random_state = 42).")
        st.caption(f"Muestra: {len(result.records)} registros · Entrenamiento: {result.train_n} · Prueba: {result.test_n}.")
        st.dataframe(result.metrics.style.format({m:"{:.4f}" for m in ["AUC-ROC","Recall","Precisión","F1-Score","Accuracy"]}), hide_index=True, use_container_width=True)
        render_chart(benchmark_fig(result.metrics), "actual_benchmark")
        with st.expander("Matriz de confusión y evaluación independiente"):
            render_chart(confusion_fig(result.confusion), "actual_cm")
        st.caption("El modelo mostrado en las fichas se reajusta sobre todos los registros después de evaluar con el conjunto de prueba, para ilustrar el uso operativo. Las puntuaciones de los estudiantes históricos no son una validación fuera de muestra.")
    else:
        st.markdown("""
**Diseño experimental recuperado del notebook del grupo:**

- **Objetivo binario:** `GradeClass` = D/F (clase 1) frente a A/B/C (clase 0).
- **Variables de entrada:** `Absences` (0–30), `Tutoring` (0/1) y `ParentalSupport` (0–4).
- **Preparación:** imputación por mediana, estandarización y partición estratificada 80/20.
- **Modelos comparados:** Regresión Logística, Gradient Boosting, Random Forest, AdaBoost y KNN.
- **Alerta roja:** riesgo estimado mayor al 80 %; **amarilla:** desde 50 % hasta 80 %; **sin alerta:** menor al 50 %.

**Límites y buenas prácticas:** el modelo predice calificaciones, no deserción. Los valores de probabilidad no deben tratarse como probabilidades calibradas sin validación adicional. Las señales no demuestran causalidad. El apoyo familiar debe usarse con especial cautela y controles de acceso, privacidad, equidad y revisión humana. No tomar decisiones punitivas ni automatizar sanciones.
        """)


def about_page(result: ModelResult, mode: str) -> None:
    page_heading("SISTEMA SATDA", "Anticipar para acompañar",
                 "Sistema de Alerta Temprana de Deserción Académica · Inteligencia predictiva educativa.")
    st.markdown(f'<div class="hero">{logo_html(122)}<div><div class="supra">SOLUCIÓN PARA INSTITUCIONES EDUCATIVAS</div>'
                '<h2>Información que impulsa<br>decisiones oportunas.</h2>'
                '<p>Una plataforma de análisis académico para universidades y escuelas que necesitan detectar señales de riesgo, coordinar recursos y acompañar trayectorias educativas.</p></div></div>', unsafe_allow_html=True)
    a,b,c = st.columns(3, gap="medium")
    with a: metric_tile("Visión integrada", "Monitoreo", "Indicadores de la población estudiantil", CYAN)
    with b: metric_tile("Intervenciones", "Prioridad", "Alertas y seguimiento individual", PURPLE)
    with c: metric_tile("Gestión institucional", "Eficiencia", "Asignación informada de recursos", NAVY)
    section("Una plataforma para la gestión académica", "Aplicaciones concretas")
    st.markdown("""
- **Panel institucional:** indicadores y visualizaciones para reconocer tendencias académicas, asistencia y niveles de alerta.
- **Fichas de estudiantes:** consulta por StudentID o por nombre, cuando la base lo incluya; acceso a métricas y antecedentes de seguimiento.
- **Detección anticipada:** un modelo de Regresión Logística permite estimar el riesgo de calificación crítica (D/F) utilizando inasistencias, tutorías y apoyo familiar.
- **Acompañamiento personalizado:** recomendaciones orientativas para planificar tutorías, mentorías, orientación y contacto con el estudiante.
- **Análisis de escenarios:** simulación interactiva para explorar cómo responde la estimación ante distintos perfiles académicos.
- **Administración de datos:** importación de archivos académicos compatibles y comparación de métricas para apoyar la evaluación del sistema.
    """)
    section("Propuesta de valor para universidades y escuelas", "Modelo institucional B2B")
    st.markdown("""
SATDA permite pasar de un seguimiento principalmente reactivo a una **gestión académica preventiva y basada en datos**.
Al priorizar los casos que requieren atención, las instituciones pueden organizar mejor sus recursos de tutoría,
mejorar la coordinación entre áreas y fortalecer sus estrategias de acompañamiento y permanencia estudiantil.

La plataforma también ofrece una base tecnológica escalable para incorporar nuevas fuentes de información,
tablero de seguimiento de cohortes, trazabilidad de intervenciones y evaluación continua del desempeño predictivo.
    """)
    st.markdown('<div class="info-strip"><strong>Próxima etapa:</strong> implementación piloto con una institución educativa, '
                'personalización de indicadores y validación del impacto de las acciones de acompañamiento.</div>', unsafe_allow_html=True)


def main() -> None:
    if not st.session_state.get("logged_in", False):
        login_page()
        return
    if "view" not in st.session_state:
        st.session_state["view"] = "Resumen institucional"
    if "data_mode" not in st.session_state:
        st.session_state["data_mode"] = "Base del trabajo práctico"
    sidebar_controls()
    result, source = get_current_result()
    try:
        view = st.session_state["view"]
        if view == "Resumen institucional": dashboard(result, source)
        elif view == "Ficha de estudiante": student_profile(result, source)
        elif view == "Modelo y métricas": model_page(result, source)
        else: about_page(result, source)
    except Exception as exc:
        st.error("No se pudo mostrar esta vista. Revisá los datos cargados o volvé al resumen.")
        st.exception(exc)
    st.markdown('<div class="footer">SATDA · Análisis académico y acompañamiento temprano</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
