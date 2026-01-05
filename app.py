import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAÇÃO VISUAL (Igual ao seu Design) ---
st.set_page_config(page_title="LocaPsi", page_icon="Φ", layout="wide")

# CSS para forçar o visual "React" (Cabeçalho branco, botões verdes)
st.markdown("""
<style>
    /* Fundo geral */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Esconde menu padrão */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* CABEÇALHO PERSONALIZADO */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: white;
        padding: 1rem 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .logo-text {
        font-size: 24px;
        font-weight: 800;
        color: #0f172a;
        font-family: sans-serif;
    }
    .logo-icon {
        color: white;
        background-color: #0d9488;
        padding: 5px 12px;
        border-radius: 8px;
        margin-right: 10px;
    }
    
    /* BOTÕES VERDES (Igual sua imagem) */
    .stButton>button {
        background-color: #0d9488 !important;
        color: white !important;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #0f766e !important;
        box-shadow: 0 4px 10px rgba(13, 148, 136, 0.4);
    }
    
    /* Inputs estilo "Card" */
    .stTextInput>div>div>input {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 10px;
    }
    
    /* Card Branco de Login */
    .login-card {
        background-color: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        max-width: 400px;
        margin: auto;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM O BANCO ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

# --- 3. TELA DE LOGIN (Igual Imagem 2) ---
def tela_login():
    # Centralizando com colunas
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="background-color: #0d9488; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px auto;">
                <span style="color: white; font-size: 30px; font-weight: bold;">Φ</span>
            </div>
            <h1 style="color: #0f172a; font-size: 32px; margin: 0;">LocaPsico</h1>
            <p style="color: #0d9488; font-weight: bold; letter-spacing: 2px; font-size: 12px; margin-top: 5px;">ESPECIALISTAS EM SALAS</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("**E-mail profissional**")
            email = st.text_input("email", placeholder="seu@email.com", label_visibility="collapsed")
            
            st.markdown("**Sua senha**")
            senha = st.text_input("senha", type="password", placeholder="Mínimo 6 caracteres", label_visibility="collapsed")
            
            st.write("")
            submitted = st.form_submit_button("Entrar na Agenda")
            
            if submitted:
                # Simulação de login simples (pode melhorar depois)
                if email:
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = email.split('@')[0].capitalize()
                    st.rerun()
                else:
                    st.error("Por favor, digite um e-mail.")

# --- 4. TELA DA AGENDA (Igual Imagem 3) ---
def tela_agenda():
    # Cabeçalho Superior Personalizado
    st.markdown(f"""
    <div class="header-container">
        <div style="display: flex; align-items: center;">
            <span class="logo-icon">L</span>
            <span class="logo-text">LOCAPSICO</span>
        </div>
        <div>
            <span style="color: #0d9488; font-weight: bold; background-color: #f0fdfa; padding: 8px 16px; border-radius: 20px;">📅 AGENDA</span>
            <span style="color: #64748b; font-weight: bold; margin-left: 15px;">MEU PAINEL</span>
        </div>
        <div style="text-align: right;">
            <div style="font-weight: bold; color: #0f172a;">{st.session_state.get('usuario', 'TERAPEUTA')}</div>
            <div style="font-size: 12px; color: #0d9488; font-weight: bold;">TERAPEUTA</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Filtros de Data (Simulando a barra de dias da imagem)
    col_nav1, col_nav2, col_nav3 = st.columns([1, 4, 1])
    with col_nav2:
        # Mostra a semana atual
        hoje = datetime.date.today()
        st.markdown(f"<h3 style='text-align: center; color: #0f172a;'>{hoje.strftime('%d %b')} - {(hoje + datetime.timedelta(days=5)).strftime('%d %b')}</h3>", unsafe_allow_html=True)
        
    # Área principal das Salas
    tab1, tab2 = st.tabs(["Sala 1", "Sala 2"])

    # Lógica para buscar dados
    df = pd.DataFrame()
    if supabase:
        try:
            # Busca dados da tabela que vimos na sua imagem
            response = supabase.table('reservas').select("*").execute()
            dados = response.data
            if dados:
                df = pd.DataFrame(dados)
                # Garante que as colunas existem antes de usar
                if 'id_da_sala' in df.columns and 'data' in df.columns and 'hora' in df.columns:
                    pass
                else:
                    st.error("As colunas da tabela 'reservas' não correspondem ao esperado. Verifique se são: id_da_sala, data, hora")
        except Exception as e:
            st.error(f"Erro ao conectar: {e}")

    with tab1:
        st.info("Agenda da Sala 1")
        if not df.empty and 'id_da_sala' in df.columns:
            # Filtra só Sala 1 e mostra como uma tabela limpa
            agenda_sala1 = df[df['id_da_sala'] == 'Sala 1'][['data', 'hora', 'id_da_sala']]
            if not agenda_sala1.empty:
                st.dataframe(agenda_sala1, use_container_width=True, hide_index=True)
            else:
                st.write("Nenhum agendamento para esta sala.")
        else:
            st.write("Sem dados.")

    with tab2:
        st.info("Agenda da Sala 2")
        if not df.empty and 'id_da_sala' in df.columns:
            agenda_sala2 = df[df['id_da_sala'] == 'Sala 2'][['data', 'hora', 'id_da_sala']]
            if not agenda_sala2.empty:
                st.dataframe(agenda_sala2, use_container_width=True, hide_index=True)
            else:
                st.write("Nenhum agendamento para esta sala.")

# --- CONTROLE DE FLUXO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    tela_login()
else:
    tela_agenda()









