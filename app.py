import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="LocaPsi", page_icon="Φ", layout="wide")

# --- CSS (VISUAL VERDE ESTILO REACT) ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Card de Login */
    .login-container {
        background-color: white; padding: 40px; border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); max-width: 400px; margin: auto;
    }
    
    /* Cabeçalho Interno */
    .header-bar {
        display: flex; justify-content: space-between; align-items: center;
        background-color: white; padding: 1rem 2rem; border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px;
    }
    
    /* Botões Verdes */
    .stButton>button {
        background-color: #0d9488 !important; color: white !important;
        border: none; border-radius: 8px; font-weight: 600; height: 3em; width: 100%;
    }
    .stButton>button:hover { background-color: #0f766e !important; }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

# --- TELA 1: LOGIN ---
def tela_login():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("""
        <div class="login-container" style="text-align: center;">
            <div style="background-color: #0d9488; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px auto;">
                <span style="color: white; font-size: 24px; font-weight: bold;">Φ</span>
            </div>
            <h2 style="color: #0f172a; margin: 0;">LocaPsico</h2>
            <p style="color: #94a3b8; font-size: 14px; margin-bottom: 30px;">Acesse sua agenda de salas</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("E-mail profissional", placeholder="seu@email.com")
            senha = st.text_input("Senha", type="password")
            st.write("")
            if st.form_submit_button("Entrar na Agenda"):
                # Login simulado para teste
                st.session_state['logado'] = True
                st.session_state['user_email'] = email
                st.rerun()

# --- TELA 2: AGENDA ---
def tela_agenda():
    # Barra Superior
    st.markdown(f"""
    <div class="header-bar">
        <div>
            <span style="font-weight: 800; font-size: 20px; color: #0f172a;">LOCAPSICO</span>
        </div>
        <div>
            <span style="background-color: #f0fdfa; color: #0d9488; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px;">● Online</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.title("📅 Minha Agenda")

    # Busca dados no Supabase
    if supabase:
        try:
            # Tenta ler a tabela
            response = supabase.table('reservas').select("*").execute()
            df = pd.DataFrame(response.data)
            
            if not df.empty:
                # Mostra a tabela bonita
                st.dataframe(
                    df, 
                    column_config={
                        "id_da_sala": "Sala",
                        "data": "Data",
                        "hora": "Horário",
                        "id_do_usuário": "ID Terapeuta"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Sua agenda está vazia neste momento. (Tabela 'reservas' encontrada, mas sem linhas)")
                
        except Exception as e:
            st.error("Erro ao carregar agenda. Tente recarregar a página.")
            st.code(str(e)) # Mostra erro técnico pequeno se houver

# --- CONTROLE DE FLUXO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    tela_login()
else:
    tela_agenda()





