import streamlit as st
import pandas as pd
from supabase import create_client
import datetime

# --- 1. CONFIGURAÇÃO INICIAL E ESTILO ---
st.set_page_config(page_title="LocaPsi", page_icon="Φ", layout="wide")

# Estilo CSS Profissional (Verde)
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="stExpander"] div[role="button"] p { font-weight: bold; color: #0f766e; }
    .stButton>button {
        background-color: #0d9488; color: white; border: none; border-radius: 8px; height: 3em; width: 100%; font-weight: 600;
    }
    .stButton>button:hover { background-color: #0f766e; }
    h1, h2, h3 { color: #0f172a; }
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

# --- 3. FUNÇÕES DO SISTEMA ---

def tela_login():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #0d9488;'>Φ LocaPsi</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Gestão de Salas e Pacientes</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar")
            
            if entrar:
                # Login simples para funcionar HOJE (Pode ser melhorado depois)
                if user == "admin" and senha == "1234":
                    st.session_state['logado'] = True
                    st.session_state['usuario_atual'] = user
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos (Teste: admin / 1234)")

def aba_agenda():
    st.header("📅 Agenda de Salas")
    
    # Formulário de Nova Reserva
    with st.expander("➕ Nova Reserva de Sala"):
        with st.form("form_reserva", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            sala = col_a.selectbox("Sala", ["Sala Interlagos 01", "Sala Tatuapé A", "Consultório 3"])
            data = col_b.date_input("Data", value=datetime.date.today())
            
            col_c, col_d = st.columns(2)
            inicio = col_c.time_input("Início", value=datetime.time(9, 0))
            fim = col_d.time_input("Fim", value=datetime.time(10, 0))
            
            if st.form_submit_button("Confirmar Reserva"):
                dados = {
                    "sala_nome": sala,
                    "data_reserva": str(data),
                    "hora_inicio": str(inicio),
                    "hora_fim": str(fim),
                    "nome_profissional": st.session_state.get('usuario_atual', 'Profissional'),
                    "status": "Ativo"
                }
                supabase.table("reservas").insert(dados).execute()
                st.success("Reserva realizada!")
                st.rerun()

    st.divider()
    
    # Visualização da Agenda
    response = supabase.table("reservas").select("*").order("data_reserva", desc=True).execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        # Renomear colunas para ficar bonito na tela
        st.dataframe(
            df,
            column_config={
                "sala_nome": "Sala",
                "data_reserva": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "hora_inicio": st.column_config.TimeColumn("Início", format="HH:mm"),
                "hora_fim": st.column_config.TimeColumn("Fim", format="HH:mm"),
                "nome_profissional": "Profissional",
                "status": "Status"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhuma reserva encontrada.")

def aba_pacientes():
    st.header("👥 Meus Pacientes")
    
    # Formulário de Cadastro
    with st.expander("➕ Cadastrar Novo Paciente"):
        with st.form("form_paciente", clear_on_submit=True):
            nome = st.text_input("Nome Completo")
            col1, col2 = st.columns(2)
            telefone = col1.text_input("Telefone")
            email = col2.text_input("Email")
            obs = st.text_area("Observações / Histórico")
            
            if st.form_submit_button("Salvar Paciente"):
                dados = {
                    "nome": nome,
                    "telefone": telefone,
                    "email": email,
                    "observacoes": obs
                }
                supabase.table("pacientes").insert(dados).execute()
                st.success(f"Paciente {nome} cadastrado!")
                st.rerun()
                
    st.divider()
    
    # Lista de Pacientes
    response = supabase.table("pacientes").select("*").order("nome").execute()
    df_pacientes = pd.DataFrame(response.data)
    
    if not df_pacientes.empty:
        st.dataframe(
            df_pacientes,
            column_config={
                "nome": "Nome",
                "telefone": "Telefone",
                "email": "Email",
                "observacoes": "Notas"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhum paciente cadastrado ainda.")

# --- 4. CONTROLE DE NAVEGAÇÃO (MENU) ---

if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    tela_login()
else:
    # Menu lateral
    with st.sidebar:
        st.title(f"Olá, {st.session_state['usuario_atual']}")
        menu = st.radio("Navegação", ["Agenda de Salas", "Cadastros Pacientes"])
        st.divider()
        if st.button("Sair"):
            st.session_state['logado'] = False
            st.rerun()

    # Mostra a tela escolhida
    if menu == "Agenda de Salas":
        aba_agenda()
    elif menu == "Cadastros Pacientes":
        aba_pacientes()






