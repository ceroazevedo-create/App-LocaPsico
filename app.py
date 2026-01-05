import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
import plotly.express as px
from fpdf import FPDF
import base64

# --- 1. CONFIGURAÇÃO E IDENTIDADE VISUAL (Teal/Emerald) ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    /* Cores Teal/Emerald */
    .stApp { background-color: #f0fdfa; } 
    .stButton>button {
        background-color: #0d9488 !important; color: white !important;
        border: none; border-radius: 8px; height: 3em; width: 100%; font-weight: 600;
    }
    .stButton>button:hover { background-color: #0f766e !important; }
    
    /* Cards */
    .metric-card {
        background-color: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #0d9488;
        text-align: center;
    }
    .metric-value { font-size: 24px; font-weight: bold; color: #0f172a; }
    .metric-label { font-size: 14px; color: #64748b; }
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
    # Busca o preço atual definido pelo admin
    resp = supabase.table("configuracoes").select("preco_hora").limit(1).execute()
    if resp.data:
        return float(resp.data[0]['preco_hora'])
    return 32.00

def gerar_pdf_relatorio(df, titulo="Relatório LocaPsico"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    
    # Cabeçalho da tabela
    pdf.set_fill_color(13, 148, 136) # Teal
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 10, "Data", 1, 0, 'C', True)
    pdf.cell(40, 10, "Sala", 1, 0, 'C', True)
    pdf.cell(60, 10, "Profissional", 1, 0, 'C', True)
    pdf.cell(40, 10, "Valor", 1, 1, 'C', True)
    
    # Dados
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

# --- 4. TELAS DO SISTEMA ---

def tela_login():
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #0d9488;'>Ψ LocaPsico</h1>", unsafe_allow_html=True)
        
        tab_login, tab_cadastro = st.tabs(["Entrar", "Criar Conta"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("E-mail")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Sistema"):
                    try:
                        auth_resp = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state['user'] = auth_resp.user
                        # Verifica se é admin
                        st.session_state['is_admin'] = (email == "admin@admin.com.br")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao entrar: {e}")

        with tab_cadastro:
            with st.form("signup_form"):
                novo_nome = st.text_input("Seu Nome Completo")
                novo_email = st.text_input("Seu E-mail")
                nova_senha = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Cadastrar-se"):
                    try:
                        supabase.auth.sign_up({
                            "email": novo_email, 
                            "password": nova_senha,
                            "options": {"data": {"nome": novo_nome}}
                        })
                        st.success("Conta criada! Faça login na aba ao lado.")
                    except Exception as e:
                        st.error(f"Erro ao cadastrar: {e}")

def dashboard_usuario():
    user = st.session_state['user']
    user_email = user.email
    st.sidebar.markdown(f"👤 **{user.user_metadata.get('nome', 'Profissional')}**")
    
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

    st.title("Minha Área")
    
    # --- MÉTRICAS DE RESUMO ---
    try:
        resp = supabase.table("reservas").select("*").eq("user_id", user.id).eq("status", "confirmada").execute()
        df = pd.DataFrame(resp.data)
        
        # Sugestão Inteligente (Baseado na moda estatística)
        sugestao = "Nenhuma ainda"
        if not df.empty:
            df['dia_semana'] = pd.to_datetime(df['data_reserva']).dt.day_name()
            dia_frequente = df['dia_semana'].mode()[0]
            sala_frequente = df['sala_nome'].mode()[0]
            sugestao = f"{sala_frequente} às {dia_frequente}s"
            
            total_investido = df['valor_cobrado'].sum()
        else:
            total_investido = 0.0

        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='metric-card'><div class='metric-value'>R$ {total_investido:.2f}</div><div class='metric-label'>Total Investido</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-value'>{sugestao}</div><div class='metric-label'>Sugestão Inteligente</div></div>", unsafe_allow_html=True)
        
    except:
        st.error("Erro ao carregar resumo.")

    st.divider()

    # --- NOVA RESERVA ---
    col_reserva, col_lista = st.columns([1, 2])
    
    with col_reserva:
        st.subheader("Nova Locação")
        preco_atual = pegar_config_preco()
        st.info(f"Valor atual: **R$ {preco_atual:.2f}/hora**")
        
        with st.form("form_reserva"):
            sala = st.selectbox("Sala", ["Sala 1", "Sala 2"])
            data = st.date_input("Data", min_value=datetime.date.today())
            
            # Horários (07:00 as 22:00)
            horarios = [f"{h:02d}:00" for h in range(7, 23)]
            hora_inicio = st.selectbox("Início", horarios)
            
            # Calcula hora fim (1h depois)
            h_int = int(hora_inicio.split(":")[0])
            hora_fim_str = f"{h_int+1:02d}:00"
            st.write(f"Término automático: {hora_fim_str}")

            if st.form_submit_button("Confirmar e Pagar"):
                # Verificar disponibilidade
                check = supabase.table("reservas").select("*").eq("sala_nome", sala).eq("data_reserva", str(data)).eq("hora_inicio", hora_inicio).eq("status", "confirmada").execute()
                
                if check.data:
                    st.error("❌ Horário indisponível!")
                else:
                    dados = {
                        "user_id": user.id,
                        "email_profissional": user_email,
                        "sala_nome": sala,
                        "data_reserva": str(data),
                        "hora_inicio": hora_inicio,
                        "hora_fim": hora_fim_str,
                        "valor_cobrado": preco_atual,
                        "status": "confirmada"
                    }
                    supabase.table("reservas").insert(dados).execute()
                    st.success("✅ Reserva Confirmada!")
                    st.rerun()

    with col_lista:
        st.subheader("Meus Agendamentos")
        if not df.empty:
            for index, row in df.sort_values(by="data_reserva", ascending=False).iterrows():
                with st.expander(f"{row['data_reserva']} | {row['hora_inicio']} - {row['sala_nome']}"):
                    st.write(f"Valor: R$ {row['valor_cobrado']}")
                    
                    # Regra de Cancelamento (24h)
                    data_reserva_dt = datetime.datetime.strptime(f"{row['data_reserva']} {row['hora_inicio']}", "%Y-%m-%d %H:%M:%S")
                    agora = datetime.datetime.now()
                    diff = data_reserva_dt - agora
                    
                    if diff > datetime.timedelta(hours=24):
                        if st.button("Cancelar Reserva", key=f"btn_{row['id']}"):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                            st.success("Cancelado com sucesso.")
                            st.rerun()
                    else:
                        st.warning("Cancelamento indisponível (menos de 24h).")
        else:
            st.write("Nenhuma reserva ativa.")

def dashboard_admin():
    st.sidebar.markdown("🛡️ **ADMINISTRADOR**")
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

    st.title("Painel de Gestão")
    
    abas = st.tabs(["Faturamento", "Todas Reservas", "Configurações"])
    
    with abas[0]: # FATURAMENTO
        resp = supabase.table("reservas").select("*").eq("status", "confirmada").execute()
        df_all = pd.DataFrame(resp.data)
        
        if not df_all.empty:
            fat_total = df_all['valor_cobrado'].sum()
            st.metric("Faturamento Bruto Total", f"R$ {fat_total:.2f}")
            
            # Gráfico Mensal
            df_all['mes'] = pd.to_datetime(df_all['data_reserva']).dt.strftime('%Y-%m')
            grafico = df_all.groupby('mes')['valor_cobrado'].sum().reset_index()
            fig = px.bar(grafico, x='mes', y='valor_cobrado', title="Receita por Mês", color_discrete_sequence=['#0d9488'])
            st.plotly_chart(fig, use_container_width=True)
            
            # Download PDF
            if st.button("Baixar Relatório Geral (PDF)"):
                pdf_bytes = gerar_pdf_relatorio(df_all)
                b64 = base64.b64encode(pdf_bytes).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="relatorio_locapsico.pdf">Clique para baixar PDF</a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("Sem dados financeiros ainda.")

    with abas[1]: # TODAS RESERVAS
        st.write("Gestão de Agendamentos (Admin pode cancelar qualquer um)")
        if not df_all.empty:
             st.dataframe(df_all[["data_reserva", "hora_inicio", "sala_nome", "email_profissional", "status"]])
             
             id_cancel = st.number_input("ID para cancelar", min_value=0)
             if st.button("Forçar Cancelamento"):
                 supabase.table("reservas").update({"status": "cancelada"}).eq("id", id_cancel).execute()
                 st.success("Cancelado pelo Admin.")
                 st.rerun()

    with abas[2]: # CONFIGURAÇÕES
        preco_atual = pegar_config_preco()
        novo_preco = st.number_input("Valor da Hora (R$)", value=float(preco_atual))
        if st.button("Atualizar Preço"):
            supabase.table("configuracoes").update({"preco_hora": novo_preco}).gt("id", 0).execute()
            st.success("Preço atualizado para todas as novas reservas!")

# --- 5. ROTEAMENTO ---

if 'user' not in st.session_state:
    tela_login()
else:
    if st.session_state.get('is_admin', False):
        dashboard_admin()
    else:
        dashboard_usuario()




