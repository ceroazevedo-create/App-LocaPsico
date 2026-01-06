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

# --- 1. CONFIGURAÇÕES GERAIS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

# NOME DA LOGO
NOME_DO_ARQUIVO_LOGO = "logo.png" 

# --- HACK JAVASCRIPT + CSS (A SOLUÇÃO DEFINITIVA) ---
# O CSS esconde, o Javascript remove do HTML para garantir
html_code = """
    <script>
    // Função para remover elementos persistentes
    function removeElements() {
        // Remove o botão de "Manage App" e o "Viewer Badge"
        const badges = window.parent.document.querySelectorAll('[data-testid="stDecoration"], [data-testid="stToolbar"], .viewerBadge_container__1QSob, .stApp > header');
        badges.forEach(el => el.style.display = 'none');
        
        // Tenta remover pelo texto do rodapé
        const footerLinks = window.parent.document.querySelectorAll('a');
        footerLinks.forEach(el => {
            if(el.innerText.includes("Streamlit")) {
                el.style.display = 'none';
            }
        });
    }
    // Roda repetidamente para garantir que suma mesmo se a net for lenta
    window.setInterval(removeElements, 500);
    </script>
    
    <style>
    /* CSS de Segurança caso o JS falhe */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    
    /* Remove a marca d'água no canto inferior direito */
    .viewerBadge_container__1QSob {display: none !important;}
    
    /* Ajuste de topo */
    .block-container {
        padding-top: 1rem !important;
        max-width: 1000px;
    }
    </style>
"""
components.html(html_code, height=0)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* RESET GERAL */
    .stApp { 
        background-color: #f2f4f7;
        font-family: 'Inter', sans-serif; 
        color: #1a1f36;
    }

    /* CARD DE LOGIN */
    div[data-testid="column"]:nth-of-type(2) > div {
        background-color: #ffffff;
        padding: 48px 40px;
        border-radius: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
        border: 1px solid #eef2f6;
        margin-top: 5vh;
    }

    /* LOGO PROPORCIONAL */
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center !important;
        width: 100%;
        margin-bottom: 24px;
    }
    div[data-testid="stImage"] > img {
        object-fit: contain;
        width: 85% !important;
        max-width: 400px;
    }

    /* TIPOGRAFIA */
    h1 { 
        font-size: 28px;
        font-weight: 700; 
        color: #1a1f36; 
        margin-bottom: 8px; 
        text-align: center; 
        letter-spacing: -0.5px;
    }
    p { 
        color: #697386; 
        font-size: 15px; 
        text-align: center; 
        margin-bottom: 32px; 
        line-height: 1.5;
    }
    
    /* INPUTS */
    .stTextInput label { font-size: 13px; font-weight: 600; color: #3c4257; margin-bottom: 4px;}
    .stTextInput input {
        background-color: #ffffff;
        border: 1px solid #e3e8ee;
        color: #1a1f36;
        border-radius: 10px;
        padding: 12px 16px;
        height: 48px;
        font-size: 16px;
        transition: all 0.2s;
    }
    .stTextInput input:focus {
        border-color: #0d9488;
        box-shadow: 0 0 0 4px rgba(13, 148, 136, 0.15);
        outline: none;
    }

    /* BOTÃO PRINCIPAL */
    div[data-testid="stVerticalBlock"] button[kind="primary"] {
        background-color: #0d9488 !important;
        color: #ffffff !important;
        border: none;
        height: 48px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 10px;
        width: 100%;
        margin-top: 16px;
        transition: transform 0.1s;
        box-shadow: 0 4px 6px rgba(13, 148, 136, 0.2);
    }
    div[data-testid="stVerticalBlock"] button[kind="primary"] * {
        color: #ffffff !important;
    }
    div[data-testid="stVerticalBlock"] button[kind="primary"]:hover {
        background-color: #0f766e !important;
        transform: translateY(-1px);
    }

    /* LINK ESQUECI SENHA */
    .forgot-container { text-align: center; margin-top: 24px; }
    .forgot-btn button {
        background: none !important; border: none !important; padding: 0 !important;
        color: #697386 !important; font-size: 13px !important; font-weight: 500 !important;
        text-decoration: none !important; box-shadow: none !important; width: auto !important;
    }
    .forgot-btn button:hover {
        color: #0d9488 !important; text-decoration: underline !important;
    }

    /* RESPONSIVIDADE */
    @media (max-width: 768px) {
        div[data-testid="column"]:nth-of-type(2) > div {
            box-shadow: none; border: none; background-color: transparent; padding: 0;
        }
        .block-container { padding-top: 2rem !important; }
    }
    
    /* INTERNO */
    .app-header { display: flex; justify-content: space-between; align-items: center; background: white; padding: 15px 30px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .evt-chip { background: #ccfbf1; border-left: 3px solid #0d9488; color: #115e59; font-size: 10px; padding: 4px; border-radius: 4px; overflow: hidden; white-space: nowrap; }
    .blocked-slot { background: repeating-linear-gradient(45deg, #fef2f2, #fef2f2 10px, #fee2e2 10px, #fee2e2 20px); height: 40px; border-radius: 4px; opacity: 0.5; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. LÓGICA DE DADOS ---
def resolver_nome(email, nome_meta=None):
    return nome_meta or email.split('@')[0].title()

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

# --- 4. FUNÇÕES SISTEMA ---
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
    if dia_sem == 6: lista_horas = []; st.error("Fechado Domingo")
    elif dia_sem == 5: lista_horas = [f"{h:02d}:00" for h in range(7, 14)]; st.info("Sábado até 14h")
    else: lista_horas = [f"{h:02d}:00" for h in range(7, 22)]
    hr = st.selectbox("Horário", lista_horas, disabled=(len(lista_horas)==0))
    if st.button("Confirmar", type="primary", use_container_width=True, disabled=(len(lista_horas)==0)):
        try:
            chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(dt)).eq("hora_inicio", hr).eq("status", "confirmada").execute()
            if chk.data: st.error("Ocupado!")
            else:
                user = st.session_state['user']
                nm = resolver_nome(user.email, user.user_metadata.get('nome'))
                supabase.table("reservas").insert({
                    "sala_nome": sala_padrao, "data_reserva": str(dt), "hora_inicio": hr, "hora_fim": f"{int(hr[:2])+1:02d}:00",
                    "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": get_preco(), "status": "confirmada"
                }).execute()
                st.toast("Agendado!", icon="✅"); st.rerun()
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
        if d not in mapa: mapa[d] = {}
        mapa[d][x['hora_inicio']] = x

    if mode == 'MÊS':
        st.info("Visão mensal simplificada. Use a semanal para detalhes.")
    else:
        visiveis = [d_start + timedelta(days=i) for i in range(7 if mode == 'SEMANA' else 1)]
        ratio = [0.6] + [1]*len(visiveis)
        c_h = st.columns(ratio)
        c_h[0].write("")
        d_n = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
        for i, d in enumerate(visiveis):
            wd = d.weekday()
            c_h[i+1].markdown(f"<div style='text-align:center; padding-bottom:5px; border-bottom:2px solid #e2e8f0; margin-bottom:5px'><div style='font-size:10px; font-weight:bold; color:#64748b'>{d_n[wd]}</div><div style='font-size:16px; font-weight:bold; color:#1e293b'>{d.day}</div></div>", unsafe_allow_html=True)
        for h in range(7, 22):
            hora = f"{h:02d}:00:00"
            row = st.columns(ratio)
            row[0].markdown(f"<div style='font-size:11px; color:#94a3b8; text-align:right; margin-top:10px'>{h:02d}:00</div>", unsafe_allow_html=True)
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
                        cont.markdown("<div style='height:40px; border-left:1px solid #f1f5f9'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Agendar", type="primary", use_container_width=True):
        modal_agendamento(sala, st.session_state.data_ref)

# --- 5. TELA DE LOGIN ---
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

def main():
    if 'user' not in st.session_state:
        # Layout 3 colunas para centralizar
        c1, c2, c3 = st.columns([1, 1.2, 1])
        
        with c2:
            st.write("") # Spacer
            
            # --- LOGO (CONTROLADA PELO CSS) ---
            if os.path.exists(NOME_DO_ARQUIVO_LOGO):
                st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else:
                st.markdown("<h1 style='text-align:center; color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            
            # --- LOGIN ---
            if st.session_state.auth_mode == 'login':
                st.markdown("<h1>Bem-vindo de volta</h1>", unsafe_allow_html=True)
                st.markdown("<p>Acesse sua agenda profissional</p>", unsafe_allow_html=True)
                
                email = st.text_input("E-mail profissional", placeholder="seu@email.com")
                senha = st.text_input("Sua senha", type="password", placeholder="••••••••")
                
                if st.button("Entrar na Agenda", type="primary"):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state['user'] = u.user
                        st.session_state['is_admin'] = (email == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Credenciais inválidas.")

                st.markdown('<div class="forgot-container"><div class="forgot-btn">', unsafe_allow_html=True)
                if st.button("Esqueci minha senha"):
                    st.session_state.auth_mode = 'forgot'; st.rerun()
                st.markdown('</div></div>', unsafe_allow_html=True)

            # --- RECUPERAÇÃO ---
            elif st.session_state.auth_mode == 'forgot':
                st.markdown("<h1>Recuperar Senha</h1>", unsafe_allow_html=True)
                st.markdown("<p>Informe seu e-mail cadastrado</p>", unsafe_allow_html=True)
                
                rec_e = st.text_input("E-mail")
                
                if st.button("Enviar Link", type="primary"):
                    try:
                        supabase.auth.reset_password_for_email(rec_e, options={"redirect_to": "https://locapsico.streamlit.app"})
                        st.success("Verifique seu e-mail.")
                    except: st.error("Erro ao enviar.")
                
                st.markdown('<div class="forgot-container"><div class="forgot-btn">', unsafe_allow_html=True)
                if st.button("Voltar ao Login"):
                    st.session_state.auth_mode = 'login'; st.rerun()
                st.markdown('</div></div>', unsafe_allow_html=True)
        return

    # --- APP LOGADO ---
    u = st.session_state['user']
    
    if st.session_state.get('is_admin'):
        with st.sidebar:
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, width=100)
            st.write("ADMIN")
            if st.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        tela_admin_master()
    else:
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        st.markdown(f"<div class='app-header'><div style='color:#0d9488;font-weight:bold'>LocaPsico</div><div>Olá, <b>{nm}</b></div></div>", unsafe_allow_html=True)
        tabs = st.tabs(["📅 Agenda", "📊 Painel"])
        with tabs[0]:
            sala = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
            render_calendar(sala)
        with tabs[1]:
            try:
                df = pd.DataFrame(supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").execute().data)
                k1, k2 = st.columns(2)
                k1.metric("Investido", f"R$ {df['valor_cobrado'].sum() if not df.empty else 0:.0f}")
                k2.metric("Sessões", len(df) if not df.empty else 0)
                with st.expander("Segurança"):
                    p1 = st.text_input("Nova Senha", type="password")
                    if st.button("Alterar Senha"):
                        supabase.auth.update_user({"password": p1})
                        st.success("OK!")
            except: pass
        with st.sidebar:
            if st.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()

# --- ADMIN ---
def tela_admin_master():
    st.markdown("<div style='background:#0f172a; padding:20px; border-radius:12px; color:white; margin-bottom:20px'><h2 style='margin:0'>⚙️ Painel Admin</h2></div>", unsafe_allow_html=True)
    tabs = st.tabs(["💰 Config", "❌ Gerenciar", "📄 Relatórios"])
    with tabs[0]:
        c1, c2 = st.columns([1, 2])
        preco_atual = get_preco()
        with c1:
            novo_preco = st.number_input("Valor da Hora (R$)", value=preco_atual, step=1.0)
        with c2:
            st.write("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar Preço", type="primary"):
                supabase.table("configuracoes").update({"preco_hora": novo_preco}).gt("id", 0).execute()
                st.success("Atualizado!")
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
        col_m, col_u = st.columns(2)
        mes_sel = col_m.selectbox("Mês", ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])
        try:
            users_db = supabase.table("reservas").select("email_profissional, nome_profissional").execute()
            df_u = pd.DataFrame(users_db.data)
            if not df_u.empty:
                df_u['display'] = df_u.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                user_sel = col_u.selectbox("Profissional", df_u['display'].unique())
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

if __name__ == "__main__":
    main()





