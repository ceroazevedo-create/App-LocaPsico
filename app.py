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
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide", initial_sidebar_state="collapsed")

# NOME DA LOGO
NOME_DO_ARQUIVO_LOGO = "logo.png" 

# --- HACK DE LIMPEZA VISUAL ---
st.markdown("""
    <style>
        header, footer, #MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
            visibility: hidden !important; display: none !important; height: 0px !important;
        }
        a[href*="streamlit.app"] { display: none !important; }
        .viewerBadge_container__1QSob { display: none !important; }
        .block-container { padding-top: 1rem !important; margin-top: 0rem !important; max-width: 1000px; }
        .stApp { background-color: #f2f4f7; font-family: 'Inter', sans-serif; color: #1a1f36; }
    </style>
""", unsafe_allow_html=True)

js_cleaner = """
<script>
    try {
        const doc = window.parent.document;
        const style = doc.createElement('style');
        style.innerHTML = `header, footer, .stApp > header { display: none !important; } [data-testid="stToolbar"] { display: none !important; } .viewerBadge_container__1QSob { display: none !important; }`;
        doc.head.appendChild(style);
    } catch (e) {}
</script>
"""
components.html(js_cleaner, height=0)

# --- CSS VISUAL ---
st.markdown("""
<style>
    /* Card Login */
    div[data-testid="column"]:nth-of-type(2) > div {
        background-color: #ffffff; padding: 48px 40px; border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #eef2f6; margin-top: 2vh;
    }
    /* Logo */
    div[data-testid="stImage"] { display: flex; justify-content: center !important; width: 100%; margin-bottom: 20px; }
    div[data-testid="stImage"] > img { object-fit: contain; width: 90% !important; max-width: 380px; }
    /* Tipografia */
    h1 { font-size: 28px; font-weight: 800; color: #1a1f36; margin-bottom: 8px; text-align: center; }
    p { color: #697386; font-size: 15px; text-align: center; margin-bottom: 24px; }
    /* Inputs */
    .stTextInput input { background-color: #ffffff; border: 1px solid #e3e8ee; border-radius: 10px; padding: 12px; height: 48px; }
    /* Botões */
    div[data-testid="stVerticalBlock"] button[kind="primary"] {
        background-color: #0d9488 !important; color: #ffffff !important; border: none; height: 48px; font-weight: 700; border-radius: 10px; margin-top: 10px;
    }
    div[data-testid="stVerticalBlock"] button[kind="primary"] * { color: #ffffff !important; }
    button[kind="secondary"] { border: 1px solid #e2e8f0; color: #64748b; }
    
    /* Botões de Ação (Logout e Excluir) */
    button[key="logout_btn"], button[key="admin_logout"], button[kind="secondary"][help="Excluir"] { 
        border-color: #fecaca !important; color: #ef4444 !important; background: #fef2f2 !important; font-weight: 600; 
    }
    
    /* ESTILOS DE AGENDA */
    .blocked-slot { 
        background-color: #fef2f2; 
        background-image: repeating-linear-gradient(45deg, #fee2e2 25%, transparent 25%, transparent 50%, #fee2e2 50%, #fee2e2 75%, transparent 75%, transparent);
        background-size: 10px 10px; height: 40px; border-radius: 4px; border: 1px solid #fecaca; opacity: 0.7; 
    }
    .admin-blocked {
        background-color: #1e293b; color: white; font-size: 10px; padding: 4px; border-radius: 4px; text-align: center; font-weight: bold; margin-bottom: 2px;
    }
    .evt-chip { background: #ccfbf1; border-left: 3px solid #0d9488; color: #115e59; font-size: 10px; padding: 4px; border-radius: 4px; overflow: hidden; white-space: nowrap; margin-bottom: 2px; }
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
    if email and "cesar_unib" in email: return "Cesar"
    if email and "thascaranalle" in email: return "Thays"
    return nome_banco or nome_meta or email.split('@')[0].title()

def get_preco_hora():
    try:
        r = supabase.table("configuracoes").select("preco_hora").limit(1).execute()
        return float(r.data[0]['preco_hora']) if r.data else 32.00
    except: return 32.00

def gerar_pdf_fatura(df, nome_usuario, mes_referencia):
    df = df.sort_values(by=['data_reserva', 'hora_inicio'])
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 10, "LOCAPSICO - Extrato Detalhado", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(50, 50, 50)
    pdf.ln(5)
    pdf.cell(0, 10, f"Profissional: {nome_usuario}", ln=True)
    pdf.cell(0, 10, f"Referencia: {mes_referencia}", ln=True)
    pdf.ln(10)
    pdf.set_fill_color(240, 253, 250)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 10, "Data", 1, 0, 'C', True)
    pdf.cell(30, 10, "Dia Sem.", 1, 0, 'C', True)
    pdf.cell(30, 10, "Horario", 1, 0, 'C', True)
    pdf.cell(40, 10, "Sala", 1, 0, 'C', True)
    pdf.cell(30, 10, "Valor", 1, 1, 'C', True)
    pdf.set_font("Arial", "", 10)
    total = 0
    dias_sem = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    for _, row in df.iterrows():
        total += float(row['valor_cobrado'])
        dt_obj = pd.to_datetime(row['data_reserva'])
        dt_str = dt_obj.strftime('%d/%m/%Y')
        dia_sem_str = dias_sem[dt_obj.weekday()]
        pdf.cell(30, 10, dt_str, 1, 0, 'C')
        pdf.cell(30, 10, dia_sem_str, 1, 0, 'C')
        pdf.cell(30, 10, str(row['hora_inicio'])[:5], 1, 0, 'C')
        pdf.cell(40, 10, str(row['sala_nome']), 1, 0, 'C')
        pdf.cell(30, 10, f"R$ {row['valor_cobrado']:.2f}", 1, 1, 'R')
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
    if dia_sem == 6: 
        lista_horas = []; st.error("Domingo: Fechado")
    elif dia_sem == 5: 
        lista_horas = [f"{h:02d}:00" for h in range(7, 14)]; st.info("Sábado: Até 14h")
    else:
        lista_horas = [f"{h:02d}:00" for h in range(7, 22)]
    hr = st.selectbox("Horário", lista_horas, disabled=(len(lista_horas)==0))
    if st.button("Confirmar", type="primary", use_container_width=True, disabled=(len(lista_horas)==0)):
        agora = datetime.datetime.now()
        dt_check = datetime.datetime.combine(dt, datetime.time(int(hr[:2]), 0))
        if dt_check < agora: st.error("Passado."); return
        if dt.weekday() == 6: st.error("Fechado."); return
        if dt.weekday() == 5 and int(hr[:2]) >= 14: st.error("Sábado fecha às 14h."); return
        try:
            chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(dt)).eq("hora_inicio", hr).neq("status", "cancelada").execute()
            if chk.data: st.error("Horário indisponível!")
            else:
                user = st.session_state['user']
                nm = resolver_nome(user.email, user.user_metadata.get('nome'))
                # Usa o valor da hora atual para o agendamento
                val_hora = get_preco_hora()
                supabase.table("reservas").insert({
                    "sala_nome": sala_padrao, "data_reserva": str(dt), "hora_inicio": hr, "hora_fim": f"{int(hr[:2])+1:02d}:00",
                    "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": val_hora, "status": "confirmada"
                }).execute()
                st.toast("Agendado!", icon="✅"); st.rerun()
        except Exception as e: st.error(f"Erro: {e}")

def render_calendar(sala, is_admin_mode=False):
    c_L, c_R = st.columns([1, 1])
    with c_L: 
        if st.button("◀ Anterior", use_container_width=True, key=f"nav_prev_{is_admin_mode}"): navegar('prev'); st.rerun()
    with c_R: 
        if st.button("Próximo ▶", use_container_width=True, key=f"nav_next_{is_admin_mode}"): navegar('next'); st.rerun()
    
    mode = st.session_state.view_mode
    def set_mode(m): st.session_state.view_mode = m
    bt_sty = lambda m: "primary" if mode == m else "secondary"
    b1, b2, b3 = st.columns(3)
    with b1: 
        if st.button("Dia", type=bt_sty('DIA'), use_container_width=True, key=f"v_dia_{is_admin_mode}"): set_mode('DIA'); st.rerun()
    with b2: 
        if st.button("Semana", type=bt_sty('SEMANA'), use_container_width=True, key=f"v_sem_{is_admin_mode}"): set_mode('SEMANA'); st.rerun()
    with b3: 
        if st.button("Mês", type=bt_sty('MÊS'), use_container_width=True, key=f"v_mes_{is_admin_mode}"): set_mode('MÊS'); st.rerun()

    ref = st.session_state.data_ref
    mes_str = ref.strftime("%B").capitalize()
    if mode == 'MÊS':
        ano, mes = ref.year, ref.month
        last_day = calendar.monthrange(ano, mes)[1]
        d_start, d_end = datetime.date(ano, mes, 1), datetime.date(ano, mes, last_day)
        lbl = f"{mes_str} {ano}"
    elif mode == 'SEMANA':
        d_start = ref - timedelta(days=ref.weekday())
        d_end = d_start + timedelta(days=6)
        lbl = f"{d_start.day} - {d_end.day} {mes_str}"
    else: 
        d_start = d_end = ref
        lbl = f"{ref.day} de {mes_str}"

    st.markdown(f"<div style='text-align:center; font-weight:800; color:#334155; margin:10px 0'>{lbl}</div>", unsafe_allow_html=True)

    reservas = []
    try:
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).neq("status", "cancelada").gte("data_reserva", str(d_start)).lte("data_reserva", str(d_end)).execute()
        reservas = r.data
    except: pass

    mapa = {}
    for x in reservas:
        d = x['data_reserva']
        if d not in mapa: mapa[d] = {}
        mapa[d][x['hora_inicio']] = x

    if mode == 'MÊS':
        cols = st.columns(7)
        dias = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
        for i, d in enumerate(dias):
            cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#64748b; font-size:12px; margin-bottom:5px'>{d}</div>", unsafe_allow_html=True)
        
        cal_matrix = calendar.monthcalendar(ref.year, ref.month)
        for week in cal_matrix:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0: cols[i].write("")
                else:
                    d_obj = datetime.date(ref.year, ref.month, day)
                    d_str = str(d_obj)
                    bg_color = "white"
                    if d_obj < datetime.date.today() or d_obj.weekday() == 6: bg_color = "#fef2f2"
                    elif d_obj == datetime.date.today(): bg_color = "#f0fdf4"
                    eventos_html = ""
                    if d_str in mapa:
                        for h in sorted(mapa[d_str].keys()):
                            res = mapa[d_str][h]
                            if res['status'] == 'bloqueado':
                                eventos_html += f"<div style='background:#1e293b; color:white; font-size:9px; padding:2px; border-radius:3px; margin-bottom:2px;'>⛔ BLOQ</div>"
                            else:
                                nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                                eventos_html += f"<div style='background:#ccfbf1; color:#115e59; font-size:9px; padding:2px; border-radius:3px; margin-bottom:2px; white-space:nowrap; overflow:hidden;'>{h[:5]} {nm}</div>"
                    cols[i].markdown(f"<div style='background:{bg_color}; border:1px solid #e2e8f0; border-radius:8px; min-height:80px; padding:5px; font-size:12px;'><div style='font-weight:bold; color:#1e293b; text-align:right'>{day}</div>{eventos_html}</div>", unsafe_allow_html=True)

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
                dt_slot = datetime.datetime.combine(d, datetime.time(h, 0))
                agora = datetime.datetime.now()
                is_sunday = d.weekday() == 6
                is_sat_closed = (d.weekday() == 5 and h >= 14)
                is_past = dt_slot < agora
                
                if res:
                    if res['status'] == 'bloqueado':
                        cont.markdown(f"<div class='admin-blocked'>⛔ FECHADO</div>", unsafe_allow_html=True)
                        if is_admin_mode:
                             if cont.button("🗑️", key=f"del_blk_{res['id']}"):
                                supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                    else:
                        nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                        if is_admin_mode:
                            c_chip, c_del = cont.columns([3,1])
                            c_chip.markdown(f"<div class='evt-chip'>{nm}</div>", unsafe_allow_html=True)
                            if c_del.button("🗑️", key=f"del_res_{res['id']}", help="Excluir"):
                                supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                        else:
                            cont.markdown(f"<div class='evt-chip'>{nm}</div>", unsafe_allow_html=True)
                elif is_sunday or is_sat_closed or is_past:
                    cont.markdown("<div class='blocked-slot'></div>", unsafe_allow_html=True)
                else:
                    cont.markdown("<div style='height:40px; border-left:1px solid #f1f5f9'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not is_admin_mode:
        if st.button("➕ Agendar", type="primary", use_container_width=True):
            modal_agendamento(sala, st.session_state.data_ref)

# --- 5. APP ---
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

def main():
    if 'user' not in st.session_state:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.write("") 
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='text-align:center; color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            
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
                    except: st.error("Email ou senha inválidos.")
                st.markdown("<br>", unsafe_allow_html=True)
                col_reg, col_rec = st.columns(2)
                with col_reg:
                    if st.button("Criar conta", type="secondary", use_container_width=True): st.session_state.auth_mode = 'register'; st.rerun()
                with col_rec:
                    if st.button("Esqueci senha", type="secondary", use_container_width=True): st.session_state.auth_mode = 'forgot'; st.rerun()

            elif st.session_state.auth_mode == 'register':
                st.markdown("<h1>Criar Nova Conta</h1>", unsafe_allow_html=True)
                new_nome = st.text_input("Nome Completo")
                new_email = st.text_input("Seu E-mail")
                new_pass = st.text_input("Crie uma Senha", type="password")
                if st.button("Cadastrar", type="primary"):
                    if len(new_pass) < 6: st.warning("Senha curta.")
                    else:
                        try:
                            supabase.auth.sign_up({"email": new_email, "password": new_pass, "options": {"data": {"nome": new_nome}}})
                            st.success("Sucesso! Faça login."); st.session_state.auth_mode = 'login'; time.sleep(1.5); st.rerun()
                        except: st.error("Erro ao cadastrar.")
                if st.button("Voltar", type="secondary"): st.session_state.auth_mode = 'login'; st.rerun()

            elif st.session_state.auth_mode == 'forgot':
                st.markdown("<h1>Recuperar Senha</h1>", unsafe_allow_html=True)
                rec_e = st.text_input("E-mail")
                if st.button("Enviar Link", type="primary"):
                    try:
                        supabase.auth.reset_password_for_email(rec_e, options={"redirect_to": "https://locapsico.streamlit.app"})
                        st.success("Verifique seu e-mail.")
                    except: st.error("Erro.")
                if st.button("Voltar", type="secondary"): st.session_state.auth_mode = 'login'; st.rerun()
        return

    # LOGADO
    u = st.session_state['user']
    if st.session_state.get('is_admin'):
        c_adm_title, c_adm_out = st.columns([5,1])
        with c_adm_title: st.markdown(f"<h3 style='color:#0d9488; margin:0'>Painel Administrativo</h3>", unsafe_allow_html=True)
        with c_adm_out:
            if st.button("Sair", key="admin_logout", use_container_width=True):
                supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        st.divider()
        tela_admin_master()
    else:
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        c_head_text, c_head_btn = st.columns([5, 1])
        with c_head_text: st.markdown(f"<h3 style='color:#0d9488; margin:0'>LocaPsico | <span style='color:#334155'>Olá, {nm}</span></h3>", unsafe_allow_html=True)
        with c_head_btn:
            if st.button("Sair", key="logout_btn", use_container_width=True): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        st.divider()

        tabs = st.tabs(["📅 Agenda", "📊 Painel"])
        with tabs[0]:
            sala = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
            render_calendar(sala)
        with tabs[1]:
            st.markdown("### Meus Agendamentos")
            agora = datetime.datetime.now()
            hoje = datetime.date.today()
            try:
                res_futuras = supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").gte("data_reserva", str(hoje)).order("data_reserva").order("hora_inicio").execute()
                df_fut = pd.DataFrame(res_futuras.data)
                if not df_fut.empty:
                    for _, row in df_fut.iterrows():
                        dt_reserva = datetime.datetime.combine(datetime.date.fromisoformat(row['data_reserva']), datetime.datetime.strptime(row['hora_inicio'], "%H:%M:%S").time())
                        if dt_reserva > agora:
                            with st.container():
                                c_info, c_btn = st.columns([3, 1])
                                c_info.markdown(f"**{row['data_reserva']}** às **{row['hora_inicio'][:5]}** - {row['sala_nome']}")
                                diff = dt_reserva - agora
                                if diff > timedelta(hours=24):
                                    if c_btn.button("Cancelar", key=f"usr_cancel_{row['id']}"):
                                        supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                                        st.toast("Cancelado!", icon="✅"); time.sleep(1); st.rerun()
                                else: c_btn.caption("🚫 < 24h")
                                st.divider()
                else: st.info("Sem agendamentos futuros.")
                
                st.markdown("### Financeiro")
                df_all = pd.DataFrame(supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").execute().data)
                k1, k2 = st.columns(2)
                k1.metric("Investido Total", f"R$ {df_all['valor_cobrado'].sum() if not df_all.empty else 0:.0f}")
                k2.metric("Sessões Totais", len(df_all) if not df_all.empty else 0)
            except: st.error("Erro ao carregar dados.")

            with st.expander("Segurança"):
                p1 = st.text_input("Nova Senha", type="password")
                if st.button("Alterar Senha"):
                    supabase.auth.update_user({"password": p1})
                    st.success("Senha atualizada!")

# --- ADMIN ---
def tela_admin_master():
    tabs = st.tabs(["💰 Config", "📅 Visualizar/Excluir", "🚫 Bloqueios", "📄 Relatórios"])
    
    with tabs[0]: 
        # Busca todas as configurações
        r_conf = supabase.table("configuracoes").select("*").limit(1).execute()
        current_conf = r_conf.data[0] if r_conf.data else {'preco_hora': 32.0, 'preco_periodo': 0.0}
        
        # Pega valores com fallback caso a coluna nova ainda não exista
        val_h = current_conf.get('preco_hora', 32.0)
        val_p = current_conf.get('preco_periodo', 0.0)

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1: novo_preco_h = st.number_input("Valor da Hora (R$)", value=float(val_h), step=1.0)
        with c2: novo_preco_p = st.number_input("Valor do Período (R$)", value=float(val_p), step=10.0)
        with c3: 
            st.write("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar Configurações", type="primary"):
                supabase.table("configuracoes").update({
                    "preco_hora": novo_preco_h,
                    "preco_periodo": novo_preco_p
                }).gt("id", 0).execute()
                st.success("Configurações atualizadas!")
    
    with tabs[1]:
        st.info("Selecione a sala para visualizar e use o botão 🗑️ para excluir agendamentos.")
        sala_adm = st.radio("Selecione Sala:", ["Sala 1", "Sala 2"], horizontal=True, key="sala_adm_view")
        render_calendar(sala_adm, is_admin_mode=True)

    with tabs[2]:
        st.write("Bloquear dias inteiros (Feriados/Manutenção)")
        c_dt_b, c_sl_b, c_bt_b = st.columns([2, 2, 2])
        dt_block = c_dt_b.date_input("Data para Bloquear")
        sala_block = c_sl_b.selectbox("Sala", ["Sala 1", "Sala 2", "Ambas"])
        
        if c_bt_b.button("🔒 Bloquear Data", type="primary"):
            salas_to_block = ["Sala 1", "Sala 2"] if sala_block == "Ambas" else [sala_block]
            try:
                inserts = []
                for s in salas_to_block:
                    for h in range(7, 22):
                        inserts.append({
                            "sala_nome": s, "data_reserva": str(dt_block), "hora_inicio": f"{h:02d}:00", "hora_fim": f"{h+1:02d}:00",
                            "user_id": "admin_block", "email_profissional": "admin@locapsico.com", "nome_profissional": "BLOQUEIO ADM",
                            "valor_cobrado": 0, "status": "bloqueado"
                        })
                supabase.table("reservas").insert(inserts).execute()
                st.success(f"Dia {dt_block} bloqueado com sucesso!")
            except Exception as e: st.error(f"Erro: {e}")

    with tabs[3]:
        col_m, col_u = st.columns(2)
        mes_sel = col_m.selectbox("Mês", ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])
        try:
            all_res = supabase.table("reservas").select("email_profissional, nome_profissional").execute()
            df_u = pd.DataFrame(all_res.data)
            if not df_u.empty:
                df_u['display'] = df_u.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                lista_users = df_u['display'].unique()
                user_sel = col_u.selectbox("Profissional", lista_users)
                if st.button("🔍 Gerar Extrato Completo", type="primary", use_container_width=True):
                    ano, mes = map(int, mes_sel.split('-'))
                    ult_dia = calendar.monthrange(ano, mes)[1]
                    d_ini, d_fim = f"{ano}-{mes:02d}-01", f"{ano}-{mes:02d}-{ult_dia}"
                    r_fin = supabase.table("reservas").select("*").eq("status", "confirmada").gte("data_reserva", d_ini).lte("data_reserva", d_fim).execute()
                    df_fin = pd.DataFrame(r_fin.data)
                    if not df_fin.empty:
                        # Ordena
                        df_fin = df_fin.sort_values(by=['data_reserva', 'hora_inicio'])
                        
                        df_fin['nm'] = df_fin.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                        df_final = df_fin[df_fin['nm'] == user_sel]
                        
                        if not df_final.empty:
                            total = df_final['valor_cobrado'].sum()
                            st.success(f"Total a Receber: R$ {total:.2f}")
                            
                            # --- EXIBIR TABELA NA TELA ---
                            st.markdown("### Detalhamento")
                            df_table = df_final[['data_reserva', 'hora_inicio', 'sala_nome', 'valor_cobrado']].copy()
                            df_table.columns = ['Data', 'Horário', 'Sala', 'Valor (R$)']
                            st.dataframe(df_table, use_container_width=True, hide_index=True)
                            
                            # --- PDF ---
                            pdf_data = gerar_pdf_fatura(df_final, user_sel, mes_sel)
                            b64 = base64.b64encode(pdf_data).decode()
                            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Extrato_{user_sel}_{mes_sel}.pdf" style="text-decoration:none; background:#0d9488; color:white; padding:10px; border-radius:8px; display:block; text-align:center;">📥 BAIXAR PDF DETALHADO</a>', unsafe_allow_html=True)
                        else: st.warning("Sem dados.")
                    else: st.warning("Sem dados.")
        except: pass

if __name__ == "__main__":
    main()

