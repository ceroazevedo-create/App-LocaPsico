import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import base64
import calendar
import plotly.express as px
import os

# --- 1. CONFIGURAÇÃO E CSS (VISUAL IDENTICO AO EXEMPLO) ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }

    /* --- ESTILOS ESPECÍFICOS DA TELA DE LOGIN --- */
    
    /* Container Branco Centralizado */
    .login-container {
        background: white;
        padding: 40px;
        border-radius: 24px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.1);
        max-width: 400px;
        margin: auto;
        text-align: center;
    }

    /* Botão Primário (Entrar na Agenda) - VERDE SÓLIDO */
    button[kind="primary"] {
        background-color: #0d9488 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 1rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: all 0.2s !important;
    }
    button[kind="primary"]:hover {
        background-color: #0f766e !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3) !important;
    }

    /* Botão Secundário (Criar Conta) - BORDA VERDE */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #0d9488 !important;
        border: 2px solid #0d9488 !important;
        border-radius: 8px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 600 !important;
        width: 100% !important;
    }
    button[kind="secondary"]:hover {
        background-color: #f0fdfa !important;
    }

    /* Link Esqueci Minha Senha (Estilo Texto) */
    /* Usamos um hack CSS para transformar o terceiro botão em link */
    div[data-testid="stVerticalBlock"] > div > div > div > div > button {
       /* Este seletor é genérico, aplicamos classe especifica no container abaixo */
    }
    
    .forgot-btn button {
        background: transparent !important;
        border: none !important;
        color: #94a3b8 !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        box-shadow: none !important;
        padding-top: 10px !important;
    }
    .forgot-btn button:hover {
        color: #0d9488 !important;
        text-decoration: underline;
    }

    /* Separador OU */
    .separator {
        display: flex; align-items: center; text-align: center;
        color: #cbd5e1; font-size: 12px; font-weight: 800; margin: 20px 0; text-transform: uppercase;
    }
    .separator::before, .separator::after {
        content: ''; flex: 1; border-bottom: 2px solid #f1f5f9;
    }
    .separator:not(:empty)::before { margin-right: 1em; }
    .separator:not(:empty)::after { margin-left: 1em; }

    /* Inputs */
    .stTextInput label { font-size: 14px; font-weight: 600; color: #334155; }
    .stTextInput input { border-radius: 8px; border: 1px solid #e2e8f0; padding: 10px; }

    /* --- ESTILOS DO SISTEMA INTERNO --- */
    .app-header { display: flex; justify-content: space-between; align-items: center; background: white; padding: 15px 30px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .admin-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px; }
    .evt-chip { background: #ccfbf1; border-left: 3px solid #0d9488; color: #115e59; font-size: 10px; font-weight: 600; padding: 3px 5px; border-radius: 4px; margin: 1px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .blocked-slot { background: repeating-linear-gradient(45deg, #fef2f2, #fef2f2 10px, #fee2e2 10px, #fee2e2 20px); height: 40px; width: 100%; border-radius: 4px; opacity: 0.5; }
    
    @media (max-width: 768px) {
        .login-container { padding: 20px; box-shadow: none; background: transparent; }
        .app-header { flex-direction: column; align-items: flex-start; }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. LÓGICA DE DADOS ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if email == "cesar_unib@msn.com": return "Cesar"
    if email == "thascaranalle@gmail.com": return "Thays"
    return nome_banco or nome_meta or email.split('@')[0].title()

def get_preco():
    try:
        r = supabase.table("configuracoes").select("preco_hora").limit(1).execute()
        return float(r.data[0]['preco_hora']) if r.data else 32.00
    except: return 32.00

def gerar_pdf_fatura(df, nome_usuario, mes_referencia):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 10, "LOCAPSICO - Extrato Mensal", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(50, 50, 50)
    pdf.ln(5)
    pdf.cell(0, 10, f"Profissional: {nome_usuario}", ln=True)
    pdf.cell(0, 10, f"Periodo: {mes_referencia}", ln=True)
    pdf.ln(10)
    pdf.set_fill_color(240, 253, 250)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 10, "Data", 1, 0, 'C', True)
    pdf.cell(30, 10, "Sala", 1, 0, 'C', True)
    pdf.cell(30, 10, "Inicio", 1, 0, 'C', True)
    pdf.cell(30, 10, "Fim", 1, 0, 'C', True)
    pdf.cell(40, 10, "Valor", 1, 1, 'C', True)
    pdf.set_font("Arial", "", 10)
    total = 0
    for _, row in df.iterrows():
        total += float(row['valor_cobrado'])
        dt = pd.to_datetime(row['data_reserva']).strftime('%d/%m/%Y')
        pdf.cell(30, 10, dt, 1, 0, 'C')
        pdf.cell(30, 10, str(row['sala_nome']), 1, 0, 'C')
        pdf.cell(30, 10, str(row['hora_inicio'])[:5], 1, 0, 'C')
        pdf.cell(30, 10, str(row['hora_fim'])[:5], 1, 0, 'C')
        pdf.cell(40, 10, f"R$ {row['valor_cobrado']:.2f}", 1, 1, 'R')
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"TOTAL: R$ {total:.2f}", ln=True, align="R")
    return pdf.output(dest='S').encode('latin-1')

# --- 4. FUNÇÕES USER ---
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'SEMANA'

def navegar(direcao):
    mode = st.session_state.view_mode
    delta = 1 if mode == 'DIA' else (7 if mode == 'SEMANA' else 30)
    if direcao == 'prev': st.session_state.data_ref -= timedelta(days=delta)
    else: st.session_state.data_ref += timedelta(days=delta)

@st.dialog("Novo Agendamento")
def modal_agendamento(sala_padrao, data_sugerida):
    st.write("Confirmar Reserva")
    dt = st.date_input("Data", value=data_sugerida, min_value=datetime.date.today())
    dia_sem = dt.weekday()
    if dia_sem == 6:
        lista_horas = []; st.error("Domingo: Fechado")
    elif dia_sem == 5:
        lista_horas = [f"{h:02d}:00" for h in range(7, 14)]
        st.info("Sábado: Até 14h")
    else:
        lista_horas = [f"{h:02d}:00" for h in range(7, 22)]
    hr = st.selectbox("Horário", lista_horas, disabled=(len(lista_horas)==0))
    if st.button("Confirmar Agendamento", type="primary", use_container_width=True, disabled=(len(lista_horas)==0)):
        agora = datetime.datetime.now()
        dt_check = datetime.datetime.combine(dt, datetime.time(int(hr[:2]), 0))
        if dt.weekday() == 6: st.error("Fechado."); return
        if dt_check < agora: st.error("Passado."); return
        try:
            chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(dt)).eq("hora_inicio", hr).eq("status", "confirmada").execute()
            if chk.data: st.error("Indisponível!"); return
            user = st.session_state['user']
            nm = resolver_nome(user.email, user.user_metadata.get('nome'))
            supabase.table("reservas").insert({
                "sala_nome": sala_padrao, "data_reserva": str(dt), "hora_inicio": hr, "hora_fim": f"{int(hr[:2])+1:02d}:00",
                "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": get_preco(), "status": "confirmada"
            }).execute()
            st.toast("Sucesso!", icon="✅"); st.rerun()
        except: st.error("Erro")

def render_calendar(sala):
    c_L, c_R = st.columns([1, 1])
    with c_L: 
        if st.button("◀ Anterior", use_container_width=True): navegar('prev'); st.rerun()
    with c_R: 
        if st.button("Próximo ▶", use_container_width=True): navegar('next'); st.rerun()
    
    mode = st.session_state.view_mode
    def set_mode(m): st.session_state.view_mode = m
    bt_sty = lambda m: "primary" if mode == m else "secondary"
    b1, b2, b3 = st.columns(3)
    with b1: 
        if st.button("Dia", type=bt_sty('DIA'), use_container_width=True): set_mode('DIA'); st.rerun()
    with b2: 
        if st.button("Semana", type=bt_sty('SEMANA'), use_container_width=True): set_mode('SEMANA'); st.rerun()
    with b3: 
        if st.button("Mês", type=bt_sty('MÊS'), use_container_width=True): set_mode('MÊS'); st.rerun()

    ref = st.session_state.data_ref
    mes_str = ref.strftime("%B").capitalize()
    lbl = f"{mes_str} {ref.year}"
    if mode == 'SEMANA':
        i = ref - timedelta(days=ref.weekday())
        f = i + timedelta(days=6)
        lbl = f"{i.day} - {f.day} {mes_str}"
    elif mode == 'DIA': lbl = f"{ref.day} de {mes_str}"
    st.markdown(f"<div style='text-align:center; font-weight:800; color:#334155; margin:10px 0'>{lbl}</div>", unsafe_allow_html=True)

    if mode == 'MÊS':
        ano, mes = ref.year, ref.month
        last = calendar.monthrange(ano, mes)[1]
        d_start, d_end = datetime.date(ano, mes, 1), datetime.date(ano, mes, last)
    elif mode == 'SEMANA':
        d_start = ref - timedelta(days=ref.weekday())
        d_end = d_start + timedelta(days=6)
    else: d_start = d_end = ref

    reservas = []
    try:
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).eq("status", "confirmada").gte("data_reserva", str(d_start)).lte("data_reserva", str(d_end)).execute()
        reservas = r.data
    except: pass

    mapa = {}
    for x in reservas:
        d = x['data_reserva']
        if mode == 'MÊS':
            if d not in mapa: mapa[d] = []
            mapa[d].append(x)
        else:
            if d not in mapa: mapa[d] = {}
            mapa[d][x['hora_inicio']] = x

    if mode == 'MÊS':
        cols = st.columns(7)
        for i,d in enumerate(['D','S','T','Q','Q','S','S']):
            cols[i].markdown(f"<div style='text-align:center; font-size:10px; font-weight:bold; color:#94a3b8'>{d}</div>", unsafe_allow_html=True)
        cal_mat = calendar.monthcalendar(ref.year, ref.month)
        for sem in cal_mat:
            cols = st.columns(7)
            for i, dia in enumerate(sem):
                if dia == 0:
                    cols[i].markdown("<div style='height:50px; background:#f8fafc'></div>", unsafe_allow_html=True)
                else:
                    dt_at = datetime.date(ref.year, ref.month, dia)
                    dt_s = str(dt_at)
                    has_evt = dt_s in mapa
                    css_class = "month-day"
                    html = ""
                    if has_evt:
                        css_class += " has-event"
                        for e in mapa[dt_s]:
                            nm = resolver_nome(e['email_profissional'], nome_banco=e.get('nome_profissional'))
                            html += f"<div class='month-evt-dot'>{e['hora_inicio'][:5]} {nm}</div>"
                    bg = "#f0fdfa" if dt_at == datetime.date.today() else "white"
                    cols[i].markdown(f"<div class='{css_class}' style='background:{bg}'><div style='text-align:center; font-weight:bold; font-size:12px; color:#475569'>{dia}</div>{html}</div>", unsafe_allow_html=True)
    else:
        visiveis = [d_start + timedelta(days=i) for i in range(7 if mode == 'SEMANA' else 1)]
        ratio = [0.6] + [1]*len(visiveis)
        c_h = st.columns(ratio)
        c_h[0].write("")
        d_n = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
        for i, d in enumerate(visiveis):
            wd = d.weekday()
            c_h[i+1].markdown(f"<div class='day-col-header'><div class='day-name'>{d_n[wd]}</div><div class='day-num'>{d.day}</div></div>", unsafe_allow_html=True)
        for h in range(7, 22):
            hora = f"{h:02d}:00:00"
            row = st.columns(ratio)
            row[0].markdown(f"<div class='time-label'>{h:02d}:00</div>", unsafe_allow_html=True)
            for i, d in enumerate(visiveis):
                d_s = str(d)
                res = mapa.get(d_s, {}).get(hora)
                cont = row[i+1].container()
                if res:
                    nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                    cont.markdown(f"<div class='evt-chip'>{nm}</div>", unsafe_allow_html=True)
                else:
                    dt_slot = datetime.datetime.combine(d, datetime.time(h, 0))
                    bloq_sab = (d.weekday() == 5 and h > 13)
                    if d.weekday() == 6 or dt_slot < datetime.datetime.now() or bloq_sab:
                        cont.markdown("<div class='blocked-slot'></div>", unsafe_allow_html=True)
                    else:
                        cont.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Agendar", type="primary", use_container_width=True):
        modal_agendamento(sala, st.session_state.data_ref)

# --- 5. TELA ADMIN EXCLUSIVA ---
def tela_admin_master():
    st.markdown("<div style='background:#0f172a; padding:20px; border-radius:12px; color:white; margin-bottom:20px'><h2 style='margin:0'>⚙️ Painel Admin</h2></div>", unsafe_allow_html=True)
    tabs = st.tabs(["💰 Config", "❌ Gerenciar", "📄 Relatórios"])
    
    with tabs[0]:
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        preco_atual = get_preco()
        with c1:
            novo_preco = st.number_input("Valor da Hora (R$)", value=preco_atual, step=1.0)
        with c2:
            st.write("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar Preço", type="primary"):
                supabase.table("configuracoes").update({"preco_hora": novo_preco}).gt("id", 0).execute()
                st.success("Atualizado!")
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        search = st.text_input("Buscar Nome/Email")
        try:
            query = supabase.table("reservas").select("*").eq("status", "confirmada").order("data_reserva", desc=True).limit(50)
            res = query.execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                if search: df = df[df['email_profissional'].str.contains(search, case=False) | df['nome_profissional'].str.contains(search, case=False, na=False)]
                for idx, row in df.iterrows():
                    with st.container():
                        nm = resolver_nome(row['email_profissional'], nome_banco=row.get('nome_profissional'))
                        c_dt, c_sl, c_nm, c_bt = st.columns([1.5, 1.5, 3, 1.5])
                        c_dt.write(f"📅 **{row['data_reserva']}**")
                        c_sl.write(f"{row['sala_nome']} ({row['hora_inicio'][:5]})")
                        c_nm.write(f"👤 {nm}")
                        if c_bt.button("❌ Cancelar", key=f"da_{row['id']}"):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                            st.rerun()
                        st.divider()
            else: st.info("Vazio.")
        except: pass

    with tabs[2]:
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        col_m, col_u = st.columns(2)
        mes_sel = col_m.selectbox("Mês", ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])
        try:
            users_db = supabase.table("reservas").select("email_profissional, nome_profissional").execute()
            df_u = pd.DataFrame(users_db.data)
            if not df_u.empty:
                df_u['display'] = df_u.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                user_sel = col_u.selectbox("Profissional", df_u['display'].unique())
                st.markdown("---")
                if st.button("🔍 Gerar Extrato", type="primary", use_container_width=True):
                    ano, mes = map(int, mes_sel.split('-'))
                    ult_dia = calendar.monthrange(ano, mes)[1]
                    d_ini, d_fim = f"{ano}-{mes:02d}-01", f"{ano}-{mes:02d}-{ult_dia}"
                    r_fin = supabase.table("reservas").select("*").eq("status", "confirmada").gte("data_reserva", d_ini).lte("data_reserva", d_fim).execute()
                    df_fin = pd.DataFrame(r_fin.data)
                    if not df_fin.empty:
                        df_fin['nm'] = df_fin.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                        df_final = df_fin[df_fin['nm'] == user_sel]
                        if not df_final.empty:
                            total = df_final['valor_cobrado'].sum()
                            st.success(f"Total: R$ {total:.2f}")
                            pdf_data = gerar_pdf_fatura(df_final, user_sel, mes_sel)
                            b64 = base64.b64encode(pdf_data).decode()
                            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Fatura.pdf" style="text-decoration:none; background:#0d9488; color:white; padding:10px; border-radius:8px; display:block; text-align:center;">📥 BAIXAR PDF</a>', unsafe_allow_html=True)
                        else: st.warning("Sem agendamentos.")
                    else: st.warning("Sem dados.")
        except: pass
        st.markdown("</div>", unsafe_allow_html=True)

# --- 6. APP PRINCIPAL ---
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

def main():
    if 'user' not in st.session_state:
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # CARD DE LOGIN ESTILO CLEAN
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            # LOGO (SE EXISTIR, SENÃO TEXTO)
            if os.path.exists("logo.png"):
                st.image("logo.png", width=150)
            else:
                st.markdown("<h1 style='color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)

            # --- TELA 1: LOGIN ---
            if st.session_state.auth_mode == 'login':
                email = st.text_input("E-mail profissional", placeholder="seu@email.com")
                senha = st.text_input("Sua senha", type="password")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Entrar na Agenda", type="primary"):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state['user'] = u.user
                        st.session_state['is_admin'] = (email == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Dados incorretos.")
                
                st.markdown("<div class='separator'>OU</div>", unsafe_allow_html=True)
                
                if st.button("Criar nova conta profissional", type="secondary"):
                    st.session_state.auth_mode = 'register'
                    st.rerun()
                
                st.markdown("<div class='forgot-btn'>", unsafe_allow_html=True)
                if st.button("ESQUECI MINHA SENHA"):
                    st.session_state.auth_mode = 'forgot'
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # --- TELA 2: CADASTRO ---
            elif st.session_state.auth_mode == 'register':
                st.markdown("<h4>Criar Conta</h4>", unsafe_allow_html=True)
                n = st.text_input("Nome Completo")
                e = st.text_input("E-mail")
                p = st.text_input("Senha (min 6 digitos)", type="password")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Cadastrar", type="primary"):
                    try:
                        supabase.auth.sign_up({"email": e, "password": p, "options": {"data": {"nome": n}}})
                        st.success("Sucesso! Faça login.")
                        st.session_state.auth_mode = 'login'
                    except Exception as err: st.error(f"Erro: {err}")
                
                if st.button("Voltar", type="secondary"):
                    st.session_state.auth_mode = 'login'
                    st.rerun()

            # --- TELA 3: RECUPERAÇÃO ---
            elif st.session_state.auth_mode == 'forgot':
                st.markdown("<h4>Recuperar Senha</h4>", unsafe_allow_html=True)
                st.info("Digite seu e-mail para receber o link.")
                rec_email = st.text_input("E-mail cadastrado")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Enviar Link", type="primary"):
                    try:
                        # URL CORRETA DO SITE (IMPORTANTE)
                        my_url = "https://locapsico.streamlit.app"
                        supabase.auth.reset_password_for_email(rec_email, options={"redirect_to": my_url})
                        st.success("Verifique seu e-mail (Cheque spam).")
                    except: st.error("Erro ao enviar.")
                
                if st.button("Cancelar", type="secondary"):
                    st.session_state.auth_mode = 'login'
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True) # Fim Container
        return

    # --- ROTEAMENTO ---
    if st.session_state.get('is_admin'):
        with st.sidebar:
            st.image("logo.png", width=100) if os.path.exists("logo.png") else None
            st.write("ADMIN")
            if st.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        tela_admin_master()
    else:
        u = st.session_state['user']
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        st.markdown(f"<div class='app-header'><div class='logo-area'>LocaPsico</div><div>Olá, <b>{nm}</b></div></div>", unsafe_allow_html=True)
        tabs = st.tabs(["📅 Agenda", "📊 Painel"])
        with tabs[0]:
            sala = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
            render_calendar(sala)
        with tabs[1]:
            # Painel simplificado user
            try:
                df = pd.DataFrame(supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").execute().data)
                c1, c2 = st.columns(2)
                c1.metric("Investido", f"R$ {df['valor_cobrado'].sum() if not df.empty else 0:.0f}")
                c2.metric("Reservas", len(df) if not df.empty else 0)
                # Alterar Senha (Usuário)
                with st.expander("Alterar Minha Senha"):
                    p1 = st.text_input("Nova Senha", type="password", key="p1")
                    if st.button("Salvar Senha"):
                        supabase.auth.update_user({"password": p1})
                        st.success("Senha alterada!")
            except: pass
        with st.sidebar:
            if st.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()

if __name__ == "__main__":
    main()





