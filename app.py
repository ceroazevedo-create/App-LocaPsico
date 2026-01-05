import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
import plotly.express as px
from fpdf import FPDF
import base64
from streamlit_calendar import calendar # Biblioteca nova para o visual

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f0fdfa; } 
    .stButton>button {
        background-color: #0d9488 !important; color: white !important;
        border: none; border-radius: 8px; height: 3em; width: 100%; font-weight: 600;
    }
    .stButton>button:hover { background-color: #0f766e !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

# --- 3. FUNÇÕES AUXILIARES ---

def pegar_config_preco():
    resp = supabase.table("configuracoes").select("preco_hora").limit(1).execute()
    if resp.data: return float(resp.data[0]['preco_hora'])
    return 32.00

def gerar_pdf_relatorio(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Relatorio Financeiro - LocaPsico", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    
    pdf.set_fill_color(13, 148, 136)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 10, "Data", 1, 0, 'C', True)
    pdf.cell(40, 10, "Sala", 1, 0, 'C', True)
    pdf.cell(60, 10, "Profissional", 1, 0, 'C', True)
    pdf.cell(40, 10, "Valor", 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    total = 0
    for index, row in df.iterrows():
        pdf.cell(40, 10, str(row['data_reserva']), 1)
        pdf.cell(40, 10, str(row['sala_nome']), 1)
        pdf.cell(60, 10, str(row['email_profissional'])[:20], 1)
        pdf.cell(40, 10, f"R$ {row['valor_cobrado']:.2f}", 1, 1)
        total += float(row['valor_cobrado'])
        
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"TOTAL: R$ {total:.2f}", ln=True, align="R")
    return pdf.output(dest='S').encode('latin-1')

# --- 4. COMPONENTE DE CALENDÁRIO ---
# --- SUBTITUA A FUNÇÃO ANTIGA POR ESTA ---
def mostrar_calendario_visual(is_admin=False):
    st.markdown("### 📅 Visualização da Agenda")
    
    # 1. Busca dados
    resp = supabase.table("reservas").select("*").eq("status", "confirmada").execute()
    df = pd.DataFrame(resp.data)
    
    if df.empty:
        st.info("A agenda está livre esta semana.")
        return

    # 2. Prepara dados para o gráfico
    # Cria colunas de data/hora completas para o gráfico entender
    df['Inicio'] = pd.to_datetime(df['data_reserva'].astype(str) + ' ' + df['hora_inicio'].astype(str))
    df['Fim'] = pd.to_datetime(df['data_reserva'].astype(str) + ' ' + df['hora_fim'].astype(str))
    
    # Define o que aparece escrito na barra
    if is_admin:
        df['Legenda'] = df['email_profissional'] # Admin vê quem é
    else:
        df['Legenda'] = "Ocupado" # Usuário vê só "Ocupado"

    # 3. Cria o Gráfico de Cronograma (Gantt)
    # Eixo Y = Salas, Eixo X = Horário
    fig = px.timeline(
        df, 
        x_start="Inicio", 
        x_end="Fim", 
        y="sala_nome", 
        color="sala_nome", # Cada sala uma cor
        text="Legenda",
        title="Ocupação das Salas (Arraste para ver mais dias)",
        color_discrete_map={"Sala 1": "#0d9488", "Sala 2": "#0ea5e9"} # Verde e Azul
    )
    
    # 4. Ajustes Visuais (Para parecer um calendário)
    fig.update_yaxes(title="", autorange="reversed") # Sala 1 em cima
    fig.update_layout(
        xaxis_title="Horário",
        showlegend=False,
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="#f8f9fa"
    )
    
    # Mostra linhas de grade para facilitar leitura das horas
    fig.update_xaxes(
        tickformat="%H:%M\n%d/%m", # Formato Hora e Dia
        dtick=3600000 * 4, # Mostra marcação a cada 4 horas
        gridcolor="#e2e8f0"
    )

    st.plotly_chart(fig, use_container_width=True)

# --- 5. TELAS ---

def tela_login():
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #0d9488;'>Ψ LocaPsico</h1>", unsafe_allow_html=True)
        tab_login, tab_cadastro = st.tabs(["Entrar", "Criar Conta"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("E-mail")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar"):
                    try:
                        auth = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state['user'] = auth.user
                        st.session_state['is_admin'] = (email == "admin@admin.com.br")
                        st.rerun()
                    except:
                        st.error("Dados incorretos.")

        with tab_cadastro:
            with st.form("signup_form"):
                novo_nome = st.text_input("Nome")
                novo_email = st.text_input("E-mail")
                nova_senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    try:
                        supabase.auth.sign_up({
                            "email": novo_email, "password": nova_senha,
                            "options": {"data": {"nome": novo_nome}}
                        })
                        st.success("Conta criada! Faça login.")
                    except Exception as e:
                        st.error(f"Erro: {e}")

def dashboard_usuario():
    user = st.session_state['user']
    st.sidebar.title(f"Olá, {user.user_metadata.get('nome', 'Psi')}")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    # ABAS DO USUÁRIO
    aba_reserva, aba_calendario, aba_meus_agendamentos = st.tabs(["➕ Nova Reserva", "📅 Calendário Geral", "👤 Meus Agendamentos"])

    with aba_calendario:
        st.info("Veja aqui os horários ocupados (Azul = Sala 1 | Verde = Sala 2)")
        mostrar_calendario_visual(is_admin=False)

    with aba_reserva:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Reservar Horário")
            preco = pegar_config_preco()
            st.write(f"Valor Hora: **R$ {preco:.2f}**")
            
            with st.form("nova_reserva"):
                sala = st.selectbox("Sala", ["Sala 1", "Sala 2"])
                data = st.date_input("Data", min_value=datetime.date.today())
                hora = st.selectbox("Início", [f"{h:02d}:00" for h in range(7, 23)])
                
                if st.form_submit_button("Confirmar Agendamento"):
                    h_fim = f"{int(hora[:2])+1:02d}:00"
                    # Verifica conflito
                    check = supabase.table("reservas").select("*").eq("sala_nome", sala).eq("data_reserva", str(data)).eq("hora_inicio", hora).eq("status", "confirmada").execute()
                    if check.data:
                        st.error("Horário já reservado por outro profissional!")
                    else:
                        dados = {
                            "user_id": user.id, "email_profissional": user.email,
                            "sala_nome": sala, "data_reserva": str(data),
                            "hora_inicio": hora, "hora_fim": h_fim,
                            "valor_cobrado": preco, "status": "confirmada"
                        }
                        supabase.table("reservas").insert(dados).execute()
                        st.success("Agendado!")
                        st.rerun()

    with aba_meus_agendamentos:
        st.subheader("Minhas Reservas Ativas")
        resp = supabase.table("reservas").select("*").eq("user_id", user.id).eq("status", "confirmada").order("data_reserva", desc=True).execute()
        df = pd.DataFrame(resp.data)
        
        if not df.empty:
            for i, row in df.iterrows():
                with st.expander(f"{row['data_reserva']} às {row['hora_inicio']} - {row['sala_nome']}"):
                    # Regra de 24h
                    dt_reserva = datetime.datetime.strptime(f"{row['data_reserva']} {row['hora_inicio']}", "%Y-%m-%d %H:%M:%S")
                    if dt_reserva - datetime.datetime.now() > timedelta(hours=24):
                        if st.button("Cancelar", key=row['id']):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                            st.rerun()
                    else:
                        st.warning("Cancelamento bloqueado (menos de 24h). Contate o Admin.")
        else:
            st.info("Você não tem agendamentos futuros.")

def dashboard_admin():
    st.sidebar.markdown("🛡️ **ADMIN MASTER**")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    aba_dash, aba_gestao, aba_calendario = st.tabs(["📊 Faturamento", "🛠️ Gerenciar Reservas", "📅 Calendário Completo"])
    
    with aba_calendario:
        mostrar_calendario_visual(is_admin=True)

    with aba_dash:
        resp = supabase.table("reservas").select("*").eq("status", "confirmada").execute()
        df = pd.DataFrame(resp.data)
        if not df.empty:
            total = df['valor_cobrado'].sum()
            st.metric("Receita Total", f"R$ {total:.2f}")
            
            # Gráfico
            df['mes'] = pd.to_datetime(df['data_reserva']).dt.strftime('%Y-%m')
            graf = df.groupby('mes')['valor_cobrado'].sum().reset_index()
            st.plotly_chart(px.bar(graf, x='mes', y='valor_cobrado'), use_container_width=True)
            
            # PDF Button
            b64 = base64.b64encode(gerar_pdf_relatorio(df)).decode()
            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="relatorio.pdf">📄 Baixar Relatório PDF</a>', unsafe_allow_html=True)

    with aba_gestao:
        st.subheader("Controle Total de Reservas")
        st.info("⚠️ Admin pode cancelar qualquer reserva a qualquer momento.")
        
        # Admin vê tudo, inclusive reservas futuras e passadas
        resp_all = supabase.table("reservas").select("*").eq("status", "confirmada").order("data_reserva", desc=True).execute()
        df_all = pd.DataFrame(resp_all.data)
        
        if not df_all.empty:
            # Mostra uma tabela interativa customizada
            for index, row in df_all.iterrows():
                col1, col2, col3, col4 = st.columns([2, 2, 3, 2])
                with col1: st.write(f"📅 **{row['data_reserva']}**")
                with col2: st.write(f"⏰ {row['hora_inicio']} ({row['sala_nome']})")
                with col3: st.write(f"👤 {row['email_profissional']}")
                with col4: 
                    # BOTÃO DE CANCELAMENTO DO ADMIN (SEM REGRAS DE TEMPO)
                    if st.button("❌ CANCELAR", key=f"admin_del_{row['id']}"):
                        supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                        st.success("Cancelado pelo Admin!")
                        st.rerun()
                st.divider()
        else:
            st.info("Nenhuma reserva ativa no sistema.")

# --- 6. ROTEAMENTO ---
if 'user' not in st.session_state:
    tela_login()
else:
    if st.session_state.get('is_admin', False):
        dashboard_admin()
    else:
        dashboard_usuario()





