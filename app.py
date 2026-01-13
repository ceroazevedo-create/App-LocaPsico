import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import base64
import calendar
import time
import os
import streamlit.components.v1 as components

# --- 1. CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide", initial_sidebar_state="collapsed")

# Inicializa Estado
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'reset_email' not in st.session_state: st.session_state.reset_email = ""
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
if 'view_days' not in st.session_state: st.session_state.view_days = 7 # Padrão 7 dias

NOME_DO_ARQUIVO_LOGO = "logo.png"

# --- 2. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. CSS VISUAL (ESTILO GOOGLE CLEAN) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    
    .stApp { background-color: #ffffff; font-family: 'Roboto', sans-serif; color: #3c4043; }
    
    /* Centralizar e Limitar Largura (Evita ficar muito largo) */
    .block-container { 
        padding-top: 1rem !important; 
        max-width: 1200px !important; 
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* Títulos */
    h1 { font-size: 22px; color: #202124; text-align: center; font-weight: 400; margin-bottom: 20px; }
    
    /* --- BOTOES DO SISTEMA --- */
    div[data-testid="stForm"] button, button[kind="primary"] {
        background-color: #1a73e8 !important; /* Azul Google */
        border: none; color: white !important; font-weight: 500; border-radius: 4px; height: 40px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    div[data-testid="stForm"] button:hover, button[kind="primary"]:hover {
        background-color: #1557b0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    
    /* --- GRADE DA AGENDA (Google Style) --- */
    
    /* Coluna de Horas */
    .time-label {
        font-size: 10px;
        color: #70757a;
        text-align: right;
        padding-right: 8px;
        transform: translateY(-50%); /* Alinha com a linha */
        position: relative;
        top: -10px;
    }

    /* Cabeçalho dos Dias */
    .day-header-box {
        text-align: center;
        padding-bottom: 5px;
    }
    .day-name { font-size: 11px; font-weight: 500; color: #70757a; text-transform: uppercase; }
    .day-number { 
        font-size: 20px; 
        font-weight: 400; 
        color: #3c4043; 
        display: inline-block; 
        width: 35px; 
        height: 35px; 
        line-height: 35px; 
        border-radius: 50%; 
        margin-top: 2px;
    }
    /* Dia Atual (Bolinha Azul) */
    .today-circle { background-color: #1a73e8; color: white !important; }

    /* Slots (Células) */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        background-color: transparent !important;
        border: 1px solid #dadce0 !important; /* Linhas da grade */
        border-top: none !important;
        border-left: none !important; /* Visual mais limpo */
        color: transparent !important; /* Texto invisível até hover */
        height: 50px !important;
        min-height: 50px !important;
        border-radius: 0px !important;
        width: 100% !important;
    }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        background-color: #f1f3f4 !important;
        color: #1a73e8 !important; /* Mostra + ao passar mouse */
        font-weight: bold;
    }
    /* Remove texto do botão vazio para ficar clean */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] p { display: none; }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover p { display: block; }

    /* Eventos (Agendados) */
    .evt-card {
        background-color: #e8f0fe; /* Azulzinho claro Google */
        color: #1967d2;
        border-left: 3px solid #1967d2;
        font-size: 10px;
        font-weight: 500;
        padding: 4px;
        border-radius: 4px;
        height: 48px;
        overflow: hidden;
        margin-top: 1px;
        cursor: pointer;
    }
    .evt-blocked {
        background-color: #5f6368;
        color: white;
        font-size: 10px;
        display: flex; align-items: center; justify-content: center;
        height: 48px; border-radius: 4px; margin-top: 1px;
    }
    
    /* Navegação */
    button[kind="secondary"] { border: 1px solid #dadce0; color: #3c4043; border-radius: 4px; }

    /* Inputs */
    .stTextInput input { border: 1px solid #dadce0; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# Javascript Cleaner
components.html("""<script>try{const doc=window.parent.document;const style=doc.createElement('style');style.innerHTML=`header, footer, .stApp > header { display: none !important; } [data-testid="stToolbar"] { display: none !important; } .viewerBadge_container__1QSob { display: none !important; }`;doc.head.appendChild(style);}catch(e){}</script>""", height=0)

# --- 4. FUNÇÕES DE SUPORTE ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if not email: return "Visitante"
    if "cesar_unib" in email: return "Cesar"
    if "thascaranalle" in email: return "Thays"
    nome_completo = nome_banco or nome_meta or email.split('@')[0]
    return str(nome_completo).strip().split(' ')[0].title()

def get_config_precos():
    defaults = {'preco_hora': 32.0, 'preco_manha': 100.0, 'preco_tarde': 100.0, 'preco_noite': 80.0, 'preco_diaria': 250.0}
    try:
        r = supabase.table("configuracoes").select("*").limit(1).execute()
        if r.data:
            data = r.data[0]
            return {
                '
