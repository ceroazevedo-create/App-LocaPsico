import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import base64
import calendar
import plotly.express as px

# --- 1. CONFIGURAÇÃO E CSS (VISUAL MODERNO) ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; padding-left: 1rem; padding-right: 1rem; }

    /* BOTÕES GERAIS */
    .stButton>button {
        border-radius: 8px; font-weight: 600; border: none; transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); width: 100%;
    }
    
    /* BOTÃO PRIMÁRIO (TEAL - ENTRAR) */
    .btn-primary button {
        background-color: #0d9488 !important; color: white !important;
        padding: 0.7rem 1rem; font-size: 16px;
    }
    .btn-primary button:hover { background-color: #0f766e !important; transform: translateY(-2px); }

    /* BOTÃO SECUNDÁRIO (OUTLINE - CRIAR CONTA) */
    .btn-outline button {
        background-color: transparent !important; 
        border: 2px solid #0d9488 !important; 
        color: #0d9488 !important;
        padding: 0.6rem 1rem;
    }
    .btn-outline button:hover { background-color: #f0fdfa !important; }

    /* LINK ESQUECI SENHA */
    .btn-link button {
        background: none !important; border: none !important; 
        color: #94a3b8 !important; font-size: 12px !important; 
        box-shadow: none !important; text-decoration: underline;
    }
    .btn-link button:hover { color: #0d9488 !important; }

    /* CONTAINER LOGIN (CARD BRANCO) */
    .login-card {
        background: white; padding: 40px; border-radius: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
        text-align: center; margin-top: 20px;
    }
    
    /* SEPARADOR "OU" */
    .separator {
        display: flex; align-items: center; text-align: center; color: #94a3b8; font-size: 12px; font-weight: bold; margin: 20px 0;
    }
    .separator::before, .separator::after {
        content: ''; flex: 1; border-bottom: 1px solid #e2e8f0;
    }
    .separator:not(:empty)::before { margin-right: .5em; }
    .separator:not(:empty)::after { margin-left: .5em; }

    /* OUTROS ESTILOS (MANTIDOS) */
    .app-header { display: flex; justify-content: space-between; align-items: center; background: white; padding: 15px 30px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); flex-wrap: wrap; gap: 10px; }
    .logo-area { font-size: 20px; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 10px; }
    .psi-icon { background: #0d9488; color: white; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
    .admin-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 15px; }
    .evt-chip { background: #ccfbf1; border-left: 3px solid #0d9488; color: #115e59; font-size: 10px; font-weight: 600; padding: 3px 5px; border-radius: 4px; margin: 1px 0; cursor: default; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .month-day { background: white; border: 1px solid #e2e8f0; min-height: 80px; padding: 2px; border-radius: 4px; display: flex; flex-direction: column; gap: 2px; }
    .month-evt-dot { font-size: 9px; background: #0f766e; color: white; padding: 1px 3px; border-radius: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .blocked-slot { background: repeating-linear-gradient(45deg, #fef2f2, #fef2f2 10px, #fee2e2 10px, #fee2e2 20px); height: 40px; width: 100%; border-radius: 4px; opacity: 0.5; }
    .day-col-header { text-align: center; padding: 5px 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 5px; }
    .day-name { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .day-num { font-size: 18px; font-weight: 800; color: #1e293b; }
    .day-num.today { color: #0d9488; }
    .time-label { font-size: 11px; color: #94a3b8; font-weight: 600; padding-right: 5px; text-align: right; width: 100%; }

    @media (max-width: 768px) {
        .app-header { flex-direction: column; align-items: flex-start; }
        .month-evt-dot { display:none; }
        .month-day.has-event { background-color: #d1fae5 !important; }
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

# --- 4. FUNÇÕES USER (CALENDÁRIO) ---
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
    
    if st.button("Confirmar Agendamento", use_container_width=True, disabled=(len(lista_horas)==0)):
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
                "sala_nome": sala_padrao, "data_reserva": str(dt),
                "hora_inicio": hr, "hora_fim": f"{int(hr[:2])+1:02d}:00",
                "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm,
                "valor_cobrado": get_preco(), "status": "confirmada"
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
    elif mode == 'DIA':
        lbl = f"{ref.day} de {mes_str}"
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
    st.markdown("""
    <div style='background:#0f172a; padding:20px; border-radius:12px; color:white; margin-bottom:20px'>
        <h2 style='margin:0'>⚙️ Painel do Administrador</h2>
        <p style='margin:0; opacity:0.8'>Controle total do sistema</p>
    </div>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs(["💰 Config & Preço", "❌ Gerenciar Reservas", "📄 Financeiro & Relatórios"])
    
    with tabs[0]:
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.subheader("Configuração de Valor")
        c1, c2 = st.columns([1, 2])
        preco_atual = get_preco()
        with c1:
            novo_preco = st.number_input("Valor da Hora (R$)", value=preco_atual, step=1.0)
        with c2:
            st.write("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar Novo Preço"):
                supabase.table("configuracoes").update({"preco_hora": novo_preco}).gt("id", 0).execute()
                st.success(f"Preço atualizado para R$ {novo_preco}!")
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
        search = st.text_input("Buscar por Nome ou Email")
        st.markdown("</div>", unsafe_allow_html=True)
        try:
            query = supabase.table("reservas").select("*").eq("status", "confirmada").order("data_reserva", desc=True).limit(100)
            res = query.execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                if search:
                    df = df[df['email_profissional'].str.contains(search, case=False) | df['nome_profissional'].str.contains(search, case=False, na=False)]
                for idx, row in df.iterrows():
                    with st.container():
                        nm = resolver_nome(row['email_profissional'], nome_banco=row.get('nome_profissional'))
                        c_dt, c_sl, c_nm, c_bt = st.columns([1.5, 1.5, 3, 1.5])
                        c_dt.write(f"📅 **{row['data_reserva']}**")
                        c_sl.write(f"{row['sala_nome']} ({row['hora_inicio'][:5]})")
                        c_nm.write(f"👤 {nm}")
                        if c_bt.button("❌ Cancelar", key=f"del_adm_{row['id']}"):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                            st.toast(f"Reserva de {nm} cancelada!", icon="🗑️")
                            st.rerun()
                        st.divider()
            else: st.info("Nenhuma reserva ativa encontrada.")
        except Exception as e: st.error(str(e))

    with tabs[2]:
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.subheader("Faturamento Mensal Individual")
        col_m, col_u = st.columns(2)
        mes_sel = col_m.selectbox("Selecione Mês", ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])
        try:
            users_db = supabase.table("reservas").select("email_profissional, nome_profissional").execute()
            df_u = pd.DataFrame(users_db.data)
            if not df_u.empty:
                df_u['display'] = df_u.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                lista = df_u['display'].unique()
                user_sel = col_u.selectbox("Selecione Profissional", lista)
                st.markdown("---")
                if st.button("🔍 Gerar Extrato Financeiro", use_container_width=True):
                    ano, mes = map(int, mes_sel.split('-'))
                    ult_dia = calendar.monthrange(ano, mes)[1]
                    d_ini, d_fim = f"{ano}-{mes:02d}-01", f"{ano}-{mes:02d}-{ult_dia}"
                    r_fin = supabase.table("reservas").select("*").eq("status", "confirmada")\
                        .gte("data_reserva", d_ini).lte("data_reserva", d_fim).execute()
                    df_fin = pd.DataFrame(r_fin.data)
                    if not df_fin.empty:
                        df_fin['nm'] = df_fin.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                        df_final = df_fin[df_fin['nm'] == user_sel]
                        if not df_final.empty:
                            total = df_final['valor_cobrado'].sum()
                            kc1, kc2 = st.columns(2)
                            kc1.metric("Total a Receber", f"R$ {total:.2f}")
                            kc2.metric("Qtd. Agendamentos", len(df_final))
                            st.dataframe(df_final[["data_reserva", "sala_nome", "hora_inicio", "valor_cobrado"]], use_container_width=True)
                            pdf_data = gerar_pdf_fatura(df_final, user_sel, mes_sel)
                            b64 = base64.b64encode(pdf_data).decode()
                            href = f'<a href="data:application/octet-stream;base64,{b64}" download="Fatura_{user_sel}_{mes_sel}.pdf" style="text-decoration:none; background:#0d9488; color:white; padding:10px 20px; border-radius:8px; display:block; text-align:center; font-weight:bold;">📥 BAIXAR FATURA PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        else: st.warning(f"Sem agendamentos para {user_sel} neste mês.")
                    else: st.warning("Sem dados financeiros neste período.")
            else: st.write("Carregando usuários...")
        except: pass
        st.markdown("</div>", unsafe_allow_html=True)

# --- 6. APP PRINCIPAL ---
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

def main():
    # --- TELA DE LOGIN / CADASTRO / RECUPERAÇÃO ---
    if 'user' not in st.session_state:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.markdown("<br><br><div style='text-align:center'><div class='psi-icon' style='width:50px;height:50px;margin:auto;font-size:24px'>Ψ</div><h1 style='color:#0f172a; margin-top:10px'>LocaPsico</h1></div>", unsafe_allow_html=True)
            
            st.markdown("<div class='login-card'>", unsafe_allow_html=True)
            
            # --- MODO: LOGIN ---
            if st.session_state.auth_mode == 'login':
                st.markdown("<h3 style='color:#334155; margin-bottom:20px'>Acesse sua conta</h3>", unsafe_allow_html=True)
                email = st.text_input("E-mail profissional", placeholder="seu@email.com")
                senha = st.text_input("Sua senha", type="password")
                
                st.markdown("<div class='btn-primary'>", unsafe_allow_html=True)
                if st.button("Entrar na Agenda"):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state['user'] = u.user
                        st.session_state['is_admin'] = (email == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Email ou senha incorretos.")
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div class='separator'>OU</div>", unsafe_allow_html=True)
                
                st.markdown("<div class='btn-outline'>", unsafe_allow_html=True)
                if st.button("Criar nova conta profissional"):
                    st.session_state.auth_mode = 'register'
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<br><div class='btn-link'>", unsafe_allow_html=True)
                if st.button("ESQUECI MINHA SENHA"):
                    st.session_state.auth_mode = 'forgot'
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # --- MODO: REGISTRO ---
            elif st.session_state.auth_mode == 'register':
                st.markdown("<h3 style='color:#334155'>Criar Conta</h3>", unsafe_allow_html=True)
                nome = st.text_input("Nome Completo")
                email = st.text_input("E-mail")
                senha = st.text_input("Crie uma Senha", type="password")
                
                st.markdown("<div class='btn-primary'>", unsafe_allow_html=True)
                if st.button("Cadastrar"):
                    try:
                        supabase.auth.sign_up({"email": email, "password": senha, "options": {"data": {"nome": nome}}})
                        st.success("Conta criada! Verifique seu e-mail ou faça login.")
                        st.session_state.auth_mode = 'login'
                    except Exception as e: st.error(f"Erro: {e}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                if st.button("Voltar ao Login"):
                    st.session_state.auth_mode = 'login'
                    st.rerun()

            # --- MODO: ESQUECI SENHA ---
            elif st.session_state.auth_mode == 'forgot':
                st.markdown("<h3 style='color:#334155'>Recuperar Senha</h3>", unsafe_allow_html=True)
                st.info("Digite seu e-mail para receber o link de redefinição.")
                email_rec = st.text_input("E-mail cadastrado")
                
                st.markdown("<div class='btn-primary'>", unsafe_allow_html=True)
                if st.button("Enviar Link de Recuperação"):
                    try:
                        # Requer configuração de SMTP no Supabase
                        supabase.auth.reset_password_for_email(email_rec, options={"redirect_to": "https://locapsico.streamlit.app/"}) 
                        st.success("Se o e-mail existir, você receberá um link em instantes.")
                    except Exception as e: st.error(f"Erro ao enviar: {e}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                if st.button("Cancelar"):
                    st.session_state.auth_mode = 'login'
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True) # Fim do card
        return

    # --- ROTEAMENTO DE VISÃO ---
    if st.session_state.get('is_admin'):
        with st.sidebar:
            st.write("🔑 **ADMINISTRADOR**")
            if st.button("Sair"):
                supabase.auth.sign_out()
                st.session_state.clear()
                st.rerun()
        tela_admin_master()
    else:
        u = st.session_state['user']
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        
        st.markdown(f"""
        <div class='app-header'>
            <div class='logo-area'><div class='psi-icon'>Ψ</div> LocaPsico</div>
            <div style='font-size:14px; color:#64748b'>Olá, <b>{nm}</b></div>
        </div>
        """, unsafe_allow_html=True)

        tabs = st.tabs(["📅 Agenda", "📊 Painel"])
        
        with tabs[0]:
            sala = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
            render_calendar(sala)

        with tabs[1]:
            try:
                df = pd.DataFrame(supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").execute().data)
                c1, c2 = st.columns(2)
                c1.metric("Investido", f"R$ {df['valor_cobrado'].sum() if not df.empty else 0:.0f}")
                c2.metric("Reservas", len(df) if not df.empty else 0)
                
                st.write("Agendamentos Futuros")
                hj = str(datetime.date.today())
                futs = supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").gte("data_reserva", hj).order("data_reserva").execute().data
                if futs:
                    for r in futs:
                        dt = datetime.datetime.strptime(f"{r['data_reserva']} {r['hora_inicio']}", "%Y-%m-%d %H:%M:%S")
                        dif = (dt - datetime.datetime.now()).total_seconds()/3600
                        c_a, c_b = st.columns([3, 1])
                        c_a.write(f"📅 {r['data_reserva'][8:]}/{r['data_reserva'][5:7]} | {r['hora_inicio'][:5]}")
                        if dif > 24:
                            if c_b.button("X", key=f"cl_{r['id']}"):
                                supabase.table("reservas").update({"status": "cancelada"}).eq("id", r['id']).execute()
                                st.rerun()
                        else: c_b.caption("🔒")
                        st.divider()
            except: pass

        with st.sidebar:
            if st.button("Sair"):
                supabase.auth.sign_out()
                st.session_state.clear()
                st.rerun()

if __name__ == "__main__":
    main()


