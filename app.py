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

# --- 1. CONFIGURAÇÃO E CSS (DESIGN SYSTEM PREMIUM) ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* --- RESET GERAL --- */
    .stApp { 
        background-color: #f2f4f7; /* Cinza muito suave e moderno */
        font-family: 'Inter', sans-serif; 
    }
    
    /* Remove cabeçalho colorido padrão do Streamlit */
    header {visibility: hidden;} 
    footer {visibility: hidden;}
    
    /* Centraliza o conteúdo na tela verticalmente */
    .block-container {
        padding-top: 5vh; 
        max-width: 1000px;
    }

    /* --- O SEGREDO DO CARD (ESTILIZANDO A COLUNA DO MEIO) --- */
    /* Isso pega a segunda coluna (onde está o login) e transforma num card */
    div[data-testid="column"]:nth-of-type(2) > div {
        background-color: #ffffff;
        padding: 48px;
        border-radius: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 
                    0 10px 15px -3px rgba(0, 0, 0, 0.05); /* Sombra elegante estilo Stripe */
        border: 1px solid #eef2f6;
    }

    /* --- TIPOGRAFIA --- */
    h1 { font-size: 24px; font-weight: 700; color: #1e293b; margin-bottom: 0.5rem; letter-spacing: -0.5px; }
    p { color: #64748b; font-size: 14px; line-height: 1.5; }
    
    /* --- INPUTS MODERNOS --- */
    /* Remove labels padrão para usar placeholders ou custom labels */
    .stTextInput label { font-size: 13px; font-weight: 600; color: #334155; }
    
    .stTextInput input {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        color: #1e293b;
        border-radius: 10px;
        padding: 12px 16px;
        height: 48px;
        font-size: 15px;
        transition: all 0.2s ease-in-out;
    }
    
    /* Efeito de Foco (Borda Verde Suave) */
    .stTextInput input:focus {
        border-color: #0d9488;
        box-shadow: 0 0 0 4px rgba(13, 148, 136, 0.1);
        outline: none;
    }

    /* --- BOTÃO PRINCIPAL (ENTRAR) --- */
    div[data-testid="stVerticalBlock"] button[kind="primary"] {
        background-color: #0d9488;
        color: white;
        border: none;
        height: 48px;
        font-size: 15px;
        font-weight: 600;
        border-radius: 10px;
        width: 100%;
        margin-top: 10px;
        transition: transform 0.1s, box-shadow 0.2s;
    }
    div[data-testid="stVerticalBlock"] button[kind="primary"]:hover {
        background-color: #0f766e;
        box-shadow: 0 4px 12px rgba(13, 148, 136, 0.25);
        transform: translateY(-1px);
    }

    /* --- BOTÕES SOCIAIS E SECUNDÁRIOS --- */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        background-color: white;
        color: #1e293b;
        border: 1px solid #e2e8f0;
        height: 44px;
        font-size: 14px;
        font-weight: 500;
        border-radius: 10px;
        width: 100%;
        transition: all 0.2s;
    }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        background-color: #f8fafc;
        border-color: #cbd5e1;
    }

    /* --- LINK ESQUECI SENHA --- */
    .forgot-container { text-align: center; margin-top: 16px; }
    .forgot-btn {
        background: none; border: none; padding: 0;
        color: #64748b; font-size: 13px; font-weight: 500;
        cursor: pointer; text-decoration: none;
    }
    .forgot-btn:hover { color: #0d9488; text-decoration: underline; }

    /* --- DIVISOR "OU" --- */
    .divider {
        display: flex; align-items: center; text-align: center;
        color: #94a3b8; font-size: 12px; font-weight: 600; margin: 24px 0;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .divider::before, .divider::after {
        content: ''; flex: 1; border-bottom: 1px solid #e2e8f0;
    }
    .divider::before { margin-right: 15px; }
    .divider::after { margin-left: 15px; }

    /* --- RESPONSIVIDADE --- */
    @media (max-width: 768px) {
        /* No celular, remove o efeito de card para ocupar a tela toda */
        div[data-testid="column"]:nth-of-type(2) > div {
            box-shadow: none;
            border: none;
            background-color: transparent;
            padding: 0;
        }
        .block-container { padding-top: 2rem; }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. FUNÇÕES AUXILIARES ---
def resolver_nome(email, nome_meta=None):
    return nome_meta or email.split('@')[0].title()

# --- 4. TELA DE LOGIN MODERNA ---
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

def main():
    if 'user' not in st.session_state:
        # Layout de 3 colunas para centralizar o Login na coluna do meio (c2)
        # O CSS acima transforma especificamente a c2 em um Card Branco
        c1, c2, c3 = st.columns([1, 1.2, 1])
        
        with c2:
            # --- LOGO ---
            # Centraliza a imagem
            col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
            with col_l2:
                if os.path.exists("logo.png"):
                    st.image("logo.png", use_container_width=True)
                else:
                    st.markdown("<h2 style='text-align:center; color:#0d9488'>LocaPsico</h2>", unsafe_allow_html=True)
            
            # Espaço
            st.write("") 

            # --- ESTADO: LOGIN ---
            if st.session_state.auth_mode == 'login':
                st.markdown("<h1 style='text-align:center'>Bem-vindo de volta</h1>", unsafe_allow_html=True)
                st.markdown("<p style='text-align:center; margin-bottom:30px'>Acesse sua agenda para gerenciar sessões</p>", unsafe_allow_html=True)
                
                email = st.text_input("E-mail profissional", placeholder="ex: nome@clinica.com")
                senha = st.text_input("Senha", type="password", placeholder="••••••••")
                
                # Botão Entrar
                if st.button("Entrar na Agenda", type="primary"):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state['user'] = u.user
                        st.session_state['is_admin'] = (email == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Email ou senha incorretos.")

                # Divisor
                st.markdown('<div class="divider">ou continue com</div>', unsafe_allow_html=True)
                
                # Login Social (Visual)
                cs1, cs2 = st.columns(2)
                with cs1: 
                    if st.button("Google", type="secondary", icon="🌐"): st.toast("Em breve")
                with cs2: 
                    if st.button("Apple", type="secondary", icon="🍎"): st.toast("Em breve")

                # Rodapé (Criar conta e Esqueci senha)
                st.markdown("<br>", unsafe_allow_html=True)
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Criar conta grátis", type="secondary"):
                        st.session_state.auth_mode = 'register'; st.rerun()
                with col_btn2:
                    # Usando botão secundário com label diferente para simular link
                    if st.button("Esqueci minha senha", type="secondary"):
                        st.session_state.auth_mode = 'forgot'; st.rerun()

            # --- ESTADO: CADASTRO ---
            elif st.session_state.auth_mode == 'register':
                st.markdown("<h1 style='text-align:center'>Criar Conta</h1>", unsafe_allow_html=True)
                st.markdown("<p style='text-align:center; margin-bottom:20px'>Junte-se à LocaPsico</p>", unsafe_allow_html=True)
                
                n = st.text_input("Nome Completo")
                e = st.text_input("E-mail")
                p = st.text_input("Criar Senha (min 6 digitos)", type="password")
                
                if st.button("Cadastrar", type="primary"):
                    try:
                        supabase.auth.sign_up({"email": e, "password": p, "options": {"data": {"nome": n}}})
                        st.success("Conta criada! Redirecionando...")
                        st.session_state.auth_mode = 'login'
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as err: st.error(f"Erro: {err}")
                
                if st.button("Voltar ao Login", type="secondary"):
                    st.session_state.auth_mode = 'login'; st.rerun()

            # --- ESTADO: RECUPERAÇÃO ---
            elif st.session_state.auth_mode == 'forgot':
                st.markdown("<h1 style='text-align:center'>Recuperar Senha</h1>", unsafe_allow_html=True)
                st.markdown("<p style='text-align:center; margin-bottom:20px'>Digite seu email para receber o link</p>", unsafe_allow_html=True)
                
                rec_e = st.text_input("E-mail cadastrado")
                
                if st.button("Enviar Link de Recuperação", type="primary"):
                    try:
                        supabase.auth.reset_password_for_email(rec_e, options={"redirect_to": "https://locapsico.streamlit.app"})
                        st.success("Verifique sua caixa de entrada (e spam).")
                    except: st.error("Erro ao enviar.")
                
                if st.button("Cancelar", type="secondary"):
                    st.session_state.auth_mode = 'login'; st.rerun()
        return

    # --- APP LOGADO (MANTIDO) ---
    # Se o usuário estiver logado, mostra o resto do app
    u = st.session_state['user']
    
    # Barra Lateral
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        st.write("Menu Principal")
        if st.button("Sair da Conta"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

    # Roteamento
    if st.session_state.get('is_admin'):
        st.title("Painel Administrativo")
        # (Aqui entra o código do painel admin que já fizemos antes)
        st.info("Funções administrativas ativas.")
    else:
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        st.title(f"Olá, {nm}")
        st.write("Bem-vindo à sua agenda.")
        # (Aqui entra o código do calendário user que já fizemos antes)

if __name__ == "__main__":
    main()






