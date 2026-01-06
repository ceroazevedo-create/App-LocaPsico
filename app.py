import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import base64
import calendar
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="LocaPsico Admin", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 2rem; }

    /* CORES DA MARCA: Teal (#0d9488) & Slate (#0f172a) */
    
    /* Botões */
    .stButton>button {
        background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%);
        color: white !important; border: none; border-radius: 10px;
        font-weight: 600; padding: 0.5rem 1rem;
        box-shadow: 0 4px 6px -1px rgba(13, 148, 136, 0.2);
    }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 6px 8px -2px rgba(13, 148, 136, 0.3); }

    /* Cards */
    .kpi-card {
        background: white; padding: 20px; border-radius: 12px;
        border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        text-align: center;
    }
    .kpi-val { font-size: 24px; font-weight: 800; color: #0f172a; }
    .kpi-lbl { font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; }

    /* Header */
    .app-header {
        display: flex; justify-content: space-between; align-items: center;
        background: white; padding: 15px 30px; border-radius: 16px;
        margin-bottom: 25px; border: 1px solid #e2e8f0;
    }
    
    /* Calendário */
    .cal-day-box { background: white; min-height: 100px; padding: 5px; border: 1px solid #f1f5f9; font-size: 12px; }
    .cal-evt { background: #ccfbf1; color: #115e59; padding: 2px 5px; border-radius: 4px; margin-bottom: 2px; font-size: 10px; font-weight: bold; overflow: hidden; white-space: nowrap; }
    .day-header { text-align: center; font-weight: 700; color: #475569; padding-bottom: 5px; border-bottom: 2px solid #e2e8f0; margin-bottom: 5px; }
    
    /* Tabelas */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. LÓGICA DE NEGÓCIO ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if email == "cesar_unib@msn.com": return "Cesar"
    if email == "thascaranalle@gmail.com": return "Thays"
    return nome_banco or nome_meta or email.split('@')[0].title()

def get_preco():
    try:
        r = supabase.table("configuracoes").select("preco_hora").limit(1).execute()
        return float(r.data[0]['preco_hora']) if r.data else 32.00
    except: return 32.00

def gerar_pdf(df, nome, mes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 10, "LOCAPSICO - Extrato Mensal", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(50,50,50)
    pdf.ln(5)
    pdf.cell(0, 10, f"Profissional: {nome}", ln=True)
    pdf.cell(0, 10, f"Referencia: {mes}", ln=True)
    pdf.ln(5)
    
    # Header Tabela
    pdf.set_fill_color(240, 253, 250)
    pdf.set_font("Arial", "B", 10)
    cols = [("Data", 30), ("Sala", 30), ("Inicio", 30), ("Fim", 30), ("Valor", 40)]
    for c in cols: pdf.cell(c[1], 10, c[0], 1, 0, 'C', True)
    pdf.ln()
    
    # Rows
    pdf.set_font("Arial", "", 10)
    total = 0
    for _, row in df.iterrows():
        total += float(row['valor_cobrado'])
        dt = pd.to_datetime(row['data_reserva']).strftime('%d/%m')
        pdf.cell(30, 10, dt, 1, 0, 'C')
        pdf.cell(30, 10, str(row['sala_nome']), 1, 0, 'C')
        pdf.cell(30, 10, str(row['hora_inicio'])[:5], 1, 0, 'C')
        pdf.cell(30, 10, str(row['hora_fim'])[:5], 1, 0, 'C')
        pdf.cell(40, 10, f"R$ {row['valor_cobrado']:.2f}", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"TOTAL: R$ {total:.2f}", ln=True, align="R")
    return pdf.output(dest='S').encode('latin-1')

# --- 4. COMPONENTE DE CALENDÁRIO ---
def render_calendar(sala):
    # Controles Navegação
    c1, c2, c3 = st.columns([1, 6, 1])
    with c1: 
        if st.button("◀"): st.session_state.data_ref -= timedelta(days=30)
    with c3: 
        if st.button("▶"): st.session_state.data_ref += timedelta(days=30)
    with c2:
        dt = st.session_state.data_ref
        mes_nome = dt.strftime("%B").capitalize()
        st.markdown(f"<h3 style='text-align:center; margin:0; color:#334155'>{mes_nome} {dt.year}</h3>", unsafe_allow_html=True)

    st.markdown("---")
    
    # Lógica Mês
    ano, mes = dt.year, dt.month
    cal = calendar.monthcalendar(ano, mes)
    
    # Busca Dados
    ult_dia = calendar.monthrange(ano, mes)[1]
    d_ini, d_fim = f"{ano}-{mes:02d}-01", f"{ano}-{mes:02d}-{ult_dia}"
    
    try:
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).eq("status", "confirmada").gte("data_reserva", d_ini).lte("data_reserva", d_fim).execute()
        df = pd.DataFrame(r.data)
    except: df = pd.DataFrame()

    # Renderiza Grid
    cols_head = st.columns(7)
    for i, d in enumerate(['DOM','SEG','TER','QUA','QUI','SEX','SÁB']):
        cols_head[i].markdown(f"<div style='text-align:center; font-weight:bold; font-size:12px; color:#94a3b8'>{d}</div>", unsafe_allow_html=True)

    for semana in cal:
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            if dia == 0:
                cols[i].markdown("<div style='min-height:80px; background:#f8fafc'></div>", unsafe_allow_html=True)
            else:
                conteudo = ""
                if not df.empty:
                    # Filtra eventos do dia
                    dia_str = f"{ano}-{mes:02d}-{dia:02d}"
                    evts = df[df['data_reserva'] == dia_str]
                    for _, row in evts.iterrows():
                        nm = resolver_nome(row['email_profissional'], nome_banco=row.get('nome_profissional'))
                        conteudo += f"<div class='cal-evt' title='{nm}'>{row['hora_inicio'][:5]} {nm}</div>"
                
                bg = "#f0fdfa" if datetime.date(ano, mes, dia) == datetime.date.today() else "white"
                cols[i].markdown(f"""
                <div class='cal-day-box' style='background:{bg}'>
                    <div style='font-weight:bold; color:#cbd5e1'>{dia}</div>
                    {conteudo}
                </div>
                """, unsafe_allow_html=True)

# --- 5. TELA ADMIN (NOVA) ---
def tela_admin():
    st.markdown("## ⚙️ Painel de Controle Master")
    
    tabs = st.tabs(["📊 Dashboard & Config", "❌ Gerenciar Reservas", "💰 Faturamento & Relatórios"])

    # TAB 1: VISÃO GERAL E PREÇO
    with tabs[0]:
        c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
        
        # Dados Globais
        try:
            r_all = supabase.table("reservas").select("*").eq("status", "confirmada").execute()
            df_all = pd.DataFrame(r_all.data)
            
            receita_total = df_all['valor_cobrado'].sum() if not df_all.empty else 0
            horas_total = len(df_all) if not df_all.empty else 0
            
            c_kpi1.markdown(f"<div class='kpi-card'><div class='kpi-val'>R$ {receita_total:,.0f}</div><div class='kpi-lbl'>Receita Histórica</div></div>", unsafe_allow_html=True)
            c_kpi2.markdown(f"<div class='kpi-card'><div class='kpi-val'>{horas_total}</div><div class='kpi-lbl'>Horas Locadas</div></div>", unsafe_allow_html=True)
            
            # KPI Preço Atual
            preco = get_preco()
            c_kpi3.markdown(f"<div class='kpi-card'><div class='kpi-val'>R$ {preco:.2f}</div><div class='kpi-lbl'>Preço Atual / Hora</div></div>", unsafe_allow_html=True)
            
            st.divider()
            
            # Coluna 1: Configurar Preço
            col_cfg, col_chart = st.columns([1, 2])
            with col_cfg:
                st.subheader("Alterar Valor Hora")
                novo_preco = st.number_input("Novo valor (R$)", value=preco, step=1.0)
                if st.button("💾 Salvar Novo Preço", use_container_width=True):
                    supabase.table("configuracoes").update({"preco_hora": novo_preco}).gt("id", 0).execute()
                    st.toast("Preço atualizado!", icon="✅")
                    st.rerun()

            # Coluna 2: Gráficos
            with col_chart:
                st.subheader("Ocupação por Sala")
                if not df_all.empty:
                    fig = px.pie(df_all, names='sala_nome', values='valor_cobrado', hole=0.4, color_discrete_sequence=['#0d9488', '#3b82f6'])
                    fig.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as e: st.error(str(e))

    # TAB 2: GERENCIAR RESERVAS (Cancelar Tudo)
    with tabs[1]:
        st.write("Lista completa de reservas ativas. **O Admin pode cancelar qualquer uma (ignora regra de 24h).**")
        
        # Filtros
        c_flt1, c_flt2 = st.columns(2)
        mes_filtro = c_flt1.selectbox("Filtrar Mês", ["Todos", "2026-01", "2026-02", "2026-03", "2026-04"])
        user_filtro = c_flt2.text_input("Buscar Profissional (Nome/Email)")

        try:
            query = supabase.table("reservas").select("*").eq("status", "confirmada").order("data_reserva", desc=True)
            if mes_filtro != "Todos":
                query = query.ilike("data_reserva", f"{mes_filtro}%")
            
            r_list = query.execute()
            df_list = pd.DataFrame(r_list.data)

            if not df_list.empty:
                # Resolve nomes para busca
                df_list['display_name'] = df_list.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x.get('nome_profissional')), axis=1)
                
                # Filtro de texto
                if user_filtro:
                    df_list = df_list[df_list['display_name'].str.contains(user_filtro, case=False) | df_list['email_profissional'].str.contains(user_filtro, case=False)]

                # Exibir Tabela com Botões
                for idx, row in df_list.iterrows():
                    with st.container():
                        c_dat, c_sal, c_usr, c_act = st.columns([1.5, 1.5, 3, 1.5])
                        c_dat.write(f"📅 {row['data_reserva']}")
                        c_sal.write(f"🏠 {row['sala_nome']} ({row['hora_inicio'][:5]})")
                        c_usr.write(f"👤 {row['display_name']}")
                        if c_act.button("❌ Cancelar", key=f"adm_cancel_{row['id']}"):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                            st.toast("Reserva cancelada pelo Admin!", icon="🗑️")
                            st.rerun()
                        st.markdown("<hr style='margin:5px 0'>", unsafe_allow_html=True)
            else:
                st.info("Nenhuma reserva encontrada com esses filtros.")

        except Exception as e: st.error(f"Erro: {e}")

    # TAB 3: FATURAMENTO & RELATÓRIOS
    with tabs[2]:
        st.subheader("Fechamento Mensal")
        
        c_sel_mes, c_sel_user = st.columns(2)
        mes_ref = c_sel_mes.selectbox("Selecione o Mês", ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"])
        
        # Busca lista única de usuários que têm reserva
        try:
            users_raw = supabase.table("reservas").select("email_profissional, nome_profissional").execute()
            df_users = pd.DataFrame(users_raw.data)
            if not df_users.empty:
                df_users['display'] = df_users.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                lista_users = df_users['display'].unique()
                user_target = c_sel_user.selectbox("Selecione o Profissional", lista_users)
                
                # Botão Gerar
                if st.button("📄 Gerar Relatório PDF", use_container_width=True):
                    # Datas limite
                    ano, mes = map(int, mes_ref.split('-'))
                    ult_dia = calendar.monthrange(ano, mes)[1]
                    d_ini, d_fim = f"{ano}-{mes:02d}-01", f"{ano}-{mes:02d}-{ult_dia}"

                    # Query Específica
                    r_rep = supabase.table("reservas").select("*").eq("status", "confirmada")\
                        .gte("data_reserva", d_ini).lte("data_reserva", d_fim).execute()
                    
                    df_rep = pd.DataFrame(r_rep.data)
                    
                    if not df_rep.empty:
                        # Filtra pelo nome resolvido
                        df_rep['nm'] = df_rep.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                        df_final = df_rep[df_rep['nm'] == user_target]
                        
                        if not df_final.empty:
                            total = df_final['valor_cobrado'].sum()
                            st.success(f"Fatura gerada: R$ {total:.2f} ({len(df_final)} sessões)")
                            
                            # Download
                            pdf_bytes = gerar_pdf(df_final, user_target, mes_ref)
                            b64 = base64.b64encode(pdf_bytes).decode()
                            href = f'<a href="data:application/octet-stream;base64,{b64}" download="Fatura_{user_target}_{mes_ref}.pdf" style="text-decoration:none; background:#0d9488; color:white; padding:10px 20px; border-radius:8px; display:block; text-align:center;">📥 BAIXAR PDF AGORA</a>'
                            st.markdown(href, unsafe_allow_html=True)
                            
                            st.dataframe(df_final[["data_reserva", "sala_nome", "hora_inicio", "valor_cobrado"]])
                        else: st.warning("Este usuário não teve agendamentos neste mês.")
                    else: st.warning("Sem dados no mês selecionado.")
            else: st.info("Sem usuários na base.")
        except Exception as e: st.error(f"Erro relatório: {e}")

# --- 6. TELAS DO USUÁRIO ---
def tela_usuario():
    user = st.session_state['user']
    nome = resolver_nome(user.email, nome_meta=user.user_metadata.get('nome'))
    
    # Header User
    st.markdown(f"""
    <div class='app-header'>
        <div style='font-weight:800; font-size:20px; color:#0f172a'>Olá, {nome}!</div>
        <div style='color:#64748b; font-size:14px'>Painel do Terapeuta</div>
    </div>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs(["📅 Agenda", "💰 Meu Painel"])
    
    # TAB AGENDA USER
    with tabs[0]:
        c_sala, c_cal = st.columns([1, 4])
        with c_sala:
            sala = st.radio("Sala", ["Sala 1", "Sala 2"], label_visibility="collapsed")
            st.info("💡 Selecione o dia no calendário para ver horários livres.")
            
            # Modal Trigger
            if st.button("➕ Agendar Horário", use_container_width=True):
                modal_agendamento()

        with c_cal:
            render_calendar(sala)

    # TAB PAINEL USER
    with tabs[1]:
        try:
            # Métricas
            r = supabase.table("reservas").select("*").eq("user_id", user.id).eq("status", "confirmada").execute()
            df = pd.DataFrame(r.data)
            
            inv = df['valor_cobrado'].sum() if not df.empty else 0
            qtd = len(df) if not df.empty else 0
            
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='kpi-card'><div class='kpi-val'>R$ {inv:.0f}</div><div class='kpi-lbl'>Total Investido</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='kpi-card'><div class='kpi-val'>{qtd}</div><div class='kpi-lbl'>Sessões Realizadas</div></div>", unsafe_allow_html=True)
            
            st.markdown("### 🗓️ Próximos Agendamentos")
            hoje = str(datetime.date.today())
            futs = supabase.table("reservas").select("*").eq("user_id", user.id).eq("status", "confirmada").gte("data_reserva", hoje).order("data_reserva").execute().data
            
            if futs:
                for row in futs:
                    # Lógica Cancelamento 24h
                    dt_obj = datetime.datetime.strptime(f"{row['data_reserva']} {row['hora_inicio']}", "%Y-%m-%d %H:%M:%S")
                    diff = (dt_obj - datetime.datetime.now()).total_seconds()/3600
                    
                    with st.container():
                        c_d, c_i, c_b = st.columns([1, 4, 1])
                        c_d.markdown(f"**{row['data_reserva'][8:]}/{row['data_reserva'][5:7]}**")
                        c_i.markdown(f"{row['sala_nome']} • {row['hora_inicio'][:5]}")
                        
                        if diff > 24:
                            if c_b.button("Cancelar", key=f"usr_c_{row['id']}"):
                                supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                                st.rerun()
                        else:
                            c_b.caption("🔒 < 24h")
                        st.markdown("<hr style='margin:5px 0'>", unsafe_allow_html=True)
            else: st.info("Sua agenda futura está vazia.")
            
        except Exception as e: st.error(str(e))

# --- 7. MODAL AGENDAMENTO USER ---
@st.dialog("Novo Agendamento")
def modal_agendamento():
    c1, c2 = st.columns(2)
    dt = c1.date_input("Data", min_value=datetime.date.today())
    hr = c2.selectbox("Horário", [f"{h:02d}:00" for h in range(7, 23)])
    sala_t = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
    
    if st.button("Confirmar Reserva", use_container_width=True):
        agora = datetime.datetime.now()
        dt_check = datetime.datetime.combine(dt, datetime.time(int(hr[:2]), 0))
        
        # Validacoes User
        if dt.weekday() == 6: st.error("Domingo fechado."); return
        if dt_check < agora: st.error("Data passada."); return
        
        # Check conflito
        c = supabase.table("reservas").select("id").eq("sala_nome", sala_t).eq("data_reserva", str(dt)).eq("hora_inicio", hr).eq("status", "confirmada").execute()
        if c.data: st.error("Horário Ocupado!"); return
        
        # Insert
        user = st.session_state['user']
        nm = resolver_nome(user.email, nome_meta=user.user_metadata.get('nome'))
        
        supabase.table("reservas").insert({
            "sala_nome": sala_t, "data_reserva": str(dt), "hora_inicio": hr, "hora_fim": f"{int(hr[:2])+1:02d}:00",
            "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm,
            "valor_cobrado": get_preco(), "status": "confirmada"
        }).execute()
        st.toast("Sucesso!"); st.rerun()

# --- 8. LOGIN E MAIN ---
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()

def main():
    if 'user' not in st.session_state:
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.markdown("<br><h1 style='text-align:center; color:#0d9488'>Ψ LocaPsico</h1>", unsafe_allow_html=True)
            t1, t2 = st.tabs(["Entrar", "Cadastrar"])
            with t1:
                e = st.text_input("Email")
                s = st.text_input("Senha", type="password")
                if st.button("Entrar", use_container_width=True):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": e, "password": s})
                        st.session_state['user'] = u.user
                        st.session_state['is_admin'] = (e == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Erro login")
            with t2:
                n = st.text_input("Nome")
                ne = st.text_input("Email Reg")
                ns = st.text_input("Senha Reg", type="password")
                if st.button("Criar", use_container_width=True):
                    supabase.auth.sign_up({"email": ne, "password": ns, "options": {"data": {"nome": n}}})
                    st.success("Criado!")
        return

    # Routing
    with st.sidebar:
        st.write(f"Logado: **{resolver_nome(st.session_state['user'].email)}**")
        if st.button("Sair"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

    if st.session_state.get('is_admin'):
        tela_admin()
    else:
        tela_usuario()

if __name__ == "__main__":
    main()
