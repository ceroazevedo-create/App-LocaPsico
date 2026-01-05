import streamlit as st
import time
from supabase import create_client, Client

# --- CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha) ---
st.set_page_config(page_title="LocaPsi App", page_icon="Φ", layout="centered")

# --- ESTILO VISUAL (CSS) PARA FICAR PARECIDO COM SUA IMAGEM ---
st.markdown("""
<style>
    /* Esconde o menu padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Estiliza o botão para ficar Verde igual sua imagem */
    .stButton>button {
        background-color: #0d9488; /* Cor Verde Petróleo */
        color: white;
        border-radius: 8px;
        height: 3em;
        width: 100%;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #0f766e;
    }
    
    /* Centraliza títulos */
    h1, h2, h3 {
        text-align: center;
        color: #0f172a;
    }
    
    /* Caixa de login */
    .login-box {
        padding: 2rem;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

# --- FUNÇÃO: TELA DE LOGIN ---
def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Tenta mostrar uma logo (simulada com texto grande por enquanto)
        st.markdown("<h1 style='font-size: 60px;'>Φ</h1>", unsafe_allow_html=True)
        st.markdown("<h1>LocaPsico</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; letter-spacing: 2px; font-size: 12px; font-weight: bold;'>ESPECIALISTAS EM SALAS</p>", unsafe_allow_html=True)
        st.write("") # Espaço
        st.write("") # Espaço

        with st.form("login_form"):
            st.markdown("##### E-mail profissional")
            email = st.text_input("E-mail", placeholder="seu@email.com", label_visibility="collapsed")
            
            st.markdown("##### Sua senha")
            senha = st.text_input("Senha", type="password", placeholder="Mínimo 6 caracteres", label_visibility="collapsed")
            
            st.write("") 
            submitted = st.form_submit_button("Entrar na Agenda")
            
            if submitted:
                if not email or not senha:
                    st.error("Preencha e-mail e senha.")
                else:
                    # AQUI VALIDARÍAMOS NO SUPABASE
                    # Por enquanto, vamos "fingir" que logou para você ver o app
                    with st.spinner("Autenticando..."):
                        time.sleep(1) # Charme
                        st.session_state['logado'] = True
                        st.session_state['usuario_email'] = email
                        st.rerun()

# --- FUNÇÃO: TELA DO SISTEMA (DENTRO DO APP) ---
def tela_sistema():
    # Barra lateral
    with st.sidebar:
        st.title(f"Olá, Doutor(a)!")
        st.caption(f"Logado como: {st.session_state['usuario_email']}")
        if st.button("Sair"):
            st.session_state['logado'] = False
            st.rerun()
    
    # Abas do Aplicativo
    aba1, aba2, aba3 = st.tabs(["📅 Minha Agenda", "🏢 Salas", "⚙️ Configurações"])
    
    with aba1:
        st.subheader("Seus Agendamentos")
        # Tenta buscar do Supabase (Tabela RESERVAS da sua imagem 1)
        if supabase:
            try:
                # Busca na tabela que vimos na sua imagem: 'reservas'
                response = supabase.table('reservas').select("*").execute()
                dados = response.data
                
                if dados:
                    st.dataframe(dados)
                else:
                    st.info("Nenhuma reserva encontrada no banco de dados.")
            except Exception as e:
                st.error(f"Erro ao ler tabela 'reservas': {e}")
        else:
            st.warning("Banco de dados desconectado.")

        st.divider()
        st.markdown("### Nova Reserva Rápida")
        col_a, col_b = st.columns(2)
        with col_a:
            st.date_input("Dia")
        with col_b:
            st.selectbox("Sala", ["Sala 1", "Sala 2"])
        st.button("Agendar Horário")

    with aba2:
        st.header("Nossas Salas")
        c1, c2 = st.columns(2)
        with c1:
            st.image("https://images.unsplash.com/photo-1497366216548-37526070297c", caption="Sala 1 - Aconchego")
            st.write("**R$ 32,00/hora**")
        with c2:
            st.image("https://images.unsplash.com/photo-1497215728101-856f4ea42174", caption="Sala 2 - Grupo")
            st.write("**R$ 32,00/hora**")

# --- CONTROLE DE FLUXO PRINCIPAL ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    tela_login()
else:
    tela_sistema()








