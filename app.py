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

# --- 1. CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide", initial_sidebar_state="collapsed")

# Inicializa Estado
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'reset_email' not in st.session_state: st.session_state.reset_email = ""
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'SEMANA'
# Padrão começa com 7 dias, mas o usuário pode mudar
if 'days_to_show' not in st.session_state: st.session_state.days_to_show = 7 

NOME_DO_ARQUIVO_LOGO = "logo.png"

# --- 2. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. CSS VISUAL (GRADE "INQUEBRÁVEL") ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; color: #1e293b; }
    
    /* --- CSS CRÍTICO: FORÇAR GRADE HORIZONTAL (NÃO EMPILHAR) --- */
    /* Isso garante que st.columns NUNCA empilhe, independente do tamanho da tela */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important; /* Proíbe quebra de linha */
        overflow-x: auto !important;  /* Permite rolagem lateral */
        display: flex !important;
        align-items: stretch !important;
        padding-bottom: 5px; /* Espaço para scrollbar se houver */
    }
    
    /* Define largura mínima para colunas não esmagarem */
    div[data-testid="column"] {
        flex: 1 0 auto !important; /* Cresce, não encolhe, base auto */
        min-width: 0px !important;
    }
    
    /* Regra especial para grade de horário: Colunas de dia devem ter largura mínima confortável */
    /* Aplica-se apenas quando temos muitas colunas (calendário) */
    div[data-testid="column"]:nth-of-type(n+2) { 
        min-width: 90px !important; /* Largura mínima do dia no celular */
    }
    
    /* A primeira coluna (Hora) pode ser mais fina */
    div[data-testid="column"]:first-of-type {
        min-width: 45px !important;
        position: sticky;
        left: 0;
        background-color: #f8fafc; /* Fundo para cobrir ao rolar */
        z-index: 10;
        border-right: 1px solid #e2e8f0;
    }
    /* ----------------------------------------------------------- */

    .block-container { padding-top: 1rem !important; max-width: 1200px; }

    /* Login e Cards */
    div[data-testid="column"]:nth-of-type(2) > div { 
        background-color: #ffffff; padding: 30px; border-radius: 16px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #f1f5f9; 
    }

    h1 { font-size: 22px; font-weight: 700; color: #0f172a; text-align: center; margin-bottom: 10px; }
    
    /* Botões e Inputs */
    div[data-testid="stForm"] button, button[kind="primary"] { background: linear-gradient(180deg, #0f766e 0%, #0d9488 100%) !important; border: none !important; height: 45px !important; font-weight: 600 !important; border-radius: 8px !important; color: white !important; }
    button[kind="secondary"] { background-color: white !important; border: 1px solid #cbd5e1 !important; color: #475569 !important; border-radius: 8px !important; height: 45px !important; font-weight: 500 !important; }
    .stTextInput input { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; height: 45px; }

    /* Estilo Calendário */
    .cal-header { text-align: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; margin-bottom: 5px; }
    .cal-day { font-size: 10px; font-weight: bold; color: #64748b; text-transform: uppercase; }
    .cal-num { font-size: 18px; font-weight: 700; color: #1e293b; }
    .cal-today .cal-num { color: #0d9488; }
    
    /* Botões da Grade */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        background-color: #ffffff !important; border: 1px solid #f1f5f9 !important; color: transparent !important;
        height: 50px !important; width: 100% !important; border-radius: 0px !important; margin: 0 !important;
    }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        background-color: #f0fdf4 !important; border-color: #0d9488 !important; color: #0d9488 !important;
    }
    
    .evt-card { background: #ccfbf1; border-left: 3px solid #0d9488; color: #0f766e; font-size: 10px; font-weight: 700; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 4px; overflow: hidden; margin-top: 1px; }
    .admin-blocked { background: #334155; color: #cbd5e1; font-size: 10px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 4px; }
    .blocked-slot { background: #f8fafc; height: 50px; border-right: 1px solid #f1f5f9; opacity: 0.5; }
    
    /* Coluna Hora */
    .time-label { font-size: 11px; font-weight: 600; color: #94a3b8; text-align: center; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

# Javascript Cleaner
components.html("""<script>try{const doc=window.parent.document;const style=doc.createElement('style');style.innerHTML=`header, footer, .stApp > header { display: none !important; } [data-testid="stToolbar"] { display: none !important; } .viewerBadge_container__1QSob { display: none !important; }`;doc.head.appendChild(style);}catch(e){}</script>""", height=0)

# --- 4. FUNÇÕES DE SUPORTE ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if not email: return "Visitante"
    if "cesar_unib" in email: return "Cesar"
    if "thascaranalle" in email: return "Thays"
    nome_completo = nome_banco or nome_meta or email.split('@')[0]
    return str(nome_completo).strip().split(' ')[0].title()

def get_config_precos():
    defaults = {'preco_hora': 32.0, 'preco_manha': 100.0, 'preco_tarde': 100.0, 'preco_noite': 80.0, 'preco_diaria': 250.0}
    try:
        r = supabase.table("configuracoes").select("*").limit(1).execute()
        if r.data:
            data = r.data[0]
            return {
                'preco_hora': float(data.get('preco_hora', 32.0)),
                'preco_manha': float(data.get('preco_manha', 100.0)),
                'preco_tarde': float(data.get('preco_tarde', 100.0)),
                'preco_noite': float(data.get('preco_noite', 80.0)),
                'preco_diaria': float(data.get('preco_diaria', 250.0)),
            }
        return defaults
    except: return defaults

def gerar_pdf_fatura(df, nome_usuario, mes_referencia):
    df = df.sort_values(by=['data_reserva', 'hora_inicio'])
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 10, "LOCAPSICO - Extrato", ln=True, align="C")
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
    pdf.cell(25, 10, "Horario", 1, 0, 'C', True)
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
        pdf.cell(25, 10, str(row['hora_inicio'])[:5], 1, 0, 'C')
        pdf.cell(40, 10, str(row['sala_nome']), 1, 0, 'C')
        pdf.cell(30, 10, f"R$ {row['valor_cobrado']:.2f}", 1, 1, 'R')
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"TOTAL: R$ {total:.2f}", ln=True, align="R")
    return pdf.output(dest='S').encode('latin-1')

def navegar(direcao):
    delta = st.session_state.days_to_show # Navega conforme a visão (3 ou 7 dias)
    if direcao == 'prev': st.session_state.data_ref -= timedelta(days=delta)
    else: st.session_state.data_ref += timedelta(days=delta)

@st.dialog("Novo Agendamento")
def modal_agendamento(sala_padrao, data_sugerida, hora_sugerida_int=None):
    st.markdown(f"#### {data_sugerida.strftime('%d/%m/%Y')}")
    config_precos = get_config_precos()
    modo = st.radio("Cobrança", ["Por Hora", "Por Período"], horizontal=True)
    dt = data_sugerida
    horarios_selecionados = []
    valor_final = 0.0
    if modo == "Por Hora":
        dia_sem = dt.weekday()
        if dia_sem == 6: lista_horas = []; st.error("Domingo Fechado")
        elif dia_sem == 5: lista_horas = [f"{h:02d}:00" for h in range(7, 14)]; st.info("Sábado até 14h")
        else: lista_horas = [f"{h:02d}:00" for h in range(7, 22)]
        idx_padrao = 0
        if hora_sugerida_int:
            str_h = f"{hora_sugerida_int:02d}:00"
            if str_h in lista_horas: idx_padrao = lista_horas.index(str_h)
        hr = st.selectbox("Horário", lista_horas, index=idx_padrao, disabled=(len(lista_horas)==0))
        if hr:
            horarios_selecionados = [(hr, f"{int(hr[:2])+1:02d}:00")]
            valor_final = config_precos['preco_hora']
    else:
        opcoes_periodo = {
            "Manhã (07-12h)": {"start": 7, "end": 12, "price": config_precos['preco_manha']},
            "Tarde (13-18h)": {"start": 13, "end": 18, "price": config_precos['preco_tarde']},
            "Noite (18-22h)": {"start": 18, "end": 22, "price": config_precos['preco_noite']},
            "Diária (07-22h)": {"start": 7, "end": 22, "price": config_precos['preco_diaria']}
        }
        sel_periodo = st.selectbox("Período", list(opcoes_periodo.keys()))
        dados_p = opcoes_periodo[sel_periodo]
        st.info(f"R$ {dados_p['price']:.2f}")
        for h in range(dados_p['start'], dados_p['end']):
            horarios_selecionados.append((f"{h:02d}:00", f"{h+1:02d}:00"))
        valor_final = dados_p['price']
    st.markdown("---")
    is_recurring = st.checkbox("Repetir por 4 semanas")
    if st.button("Confirmar", type="primary", use_container_width=True):
        if not horarios_selecionados: st.error("Selecione horário."); return
        user = st.session_state.user
        nm = resolver_nome(user.email, user.user_metadata.get('nome'))
        agora = datetime.datetime.now()
        datas_to_book = [dt]
        if is_recurring:
            for i in range(1, 4): datas_to_book.append(dt + timedelta(days=7*i))
        try:
            inserts = []
            for d_res in datas_to_book:
                if d_res.weekday() == 6: continue
                for h_start, h_end in horarios_selecionados:
                    dt_check = datetime.datetime.combine(d_res, datetime.datetime.strptime(h_start, "%H:%M").time())
                    if dt_check < agora: st.error("Passou."); return
                    chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(d_res)).eq("hora_inicio", f"{h_start}:00").neq("status", "cancelada").execute()
                    if chk.data: st.error("Ocupado."); return 
                    val_to_save = valor_final if (h_start, h_end) == horarios_selecionados[0] or modo == "Por Hora" else 0.0
                    inserts.append({
                        "sala_nome": sala_padrao, "data_reserva": str(d_res), "hora_inicio": f"{h_start}:00", "hora_fim": f"{h_end}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": val_to_save, "status": "confirmada"
                    })
            if inserts:
                supabase.table("reservas").insert(inserts).execute()
                st.toast("Confirmado!", icon="✅"); time.sleep(1); st.rerun()
        except: st.error("Erro.")

def render_calendar(sala, is_admin_mode=False):
    # SELETOR DE DISPOSITIVO (O que você pediu)
    c1, c2, c3 = st.columns([1.5, 2, 1.5])
    with c1:
        # ESCOLHA: CELULAR ou PC
        dev_mode = st.radio("Modo:", ["📱 Celular (3 Dias)", "💻 PC (7 Dias)"], horizontal=True, label_visibility="collapsed")
        st.session_state.days_to_show = 3 if "Celular" in dev_mode else 7
        
    with c2:
        # Navegação Mês
        cn1, cn2, cn3 = st.columns([1, 2, 1])
        cn1.button("◀", use_container_width=True, on_click=lambda: navegar('prev'))
        mes_str = st.session_state.data_ref.strftime("%B").capitalize()
        cn2.markdown(f"<div style='text-align:center; font-weight:700; font-size:18px; padding-top:5px'>{mes_str}</div>", unsafe_allow_html=True)
        cn3.button("▶", use_container_width=True, on_click=lambda: navegar('next'))
    
    with c3:
        pass

    # Lógica de Datas
    num_days = st.session_state.days_to_show
    ref = st.session_state.data_ref
    
    # Se for PC (7 dias), alinha na segunda-feira. Se for Celular (3 dias), começa do dia atual.
    if num_days == 7:
        d_start = ref - timedelta(days=ref.weekday())
    else:
        d_start = ref
        
    d_end = d_start + timedelta(days=num_days - 1)
    
    # Busca Reservas
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

    # Renderiza Grade
    visiveis = [d_start + timedelta(days=i) for i in range(num_days)]
    dias_sem = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    
    # Ratios: 0.5 (Hora) + 1 (Cada Dia)
    ratios = [0.5] + [1]*num_days
    
    # 1. Cabeçalho
    cols = st.columns(ratios)
    cols[0].write("")
    for i, d in enumerate(visiveis):
        with cols[i+1]:
            wd = d.weekday()
            is_today = (d == datetime.date.today())
            cls_today = "cal-today" if is_today else ""
            st.markdown(f"""
            <div class='cal-header {cls_today}'>
                <div class='cal-day'>{dias_sem[wd]}</div>
                <div class='cal-num'>{d.day}</div>
            </div>
            """, unsafe_allow_html=True)
            
    # 2. Corpo
    for h in range(7, 22):
        row = st.columns(ratios)
        # Coluna Hora Fixa
        row[0].markdown(f"<div class='time-label'>{h:02d}:00</div>", unsafe_allow_html=True)
        
        # Colunas Dias
        for i, d in enumerate(visiveis):
            with row[i+1]:
                d_s = str(d)
                h_s = f"{h:02d}:00:00"
                res = mapa.get(d_s, {}).get(h_s)
                cont = st.container()
                
                # Regras
                agora = datetime.datetime.now()
                dt_slot = datetime.datetime.combine(d, datetime.time(h, 0))
                past = dt_slot < agora
                sun = d.weekday() == 6
                sat_close = (d.weekday() == 5 and h >= 14)
                
                if res:
                    if res['status'] == 'bloqueado':
                        cont.markdown(f"<div class='admin-blocked'>X</div>", unsafe_allow_html=True)
                        if is_admin_mode:
                             if cont.button("🗑️", key=f"d_blk_{res['id']}"): supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                    else:
                        nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                        if is_admin_mode:
                            c_chip, c_del = cont.columns([3,1])
                            c_chip.markdown(f"<div class='evt-card'>{nm}</div>", unsafe_allow_html=True)
                            if c_del.button("x", key=f"d_res_{res['id']}"): supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                        else:
                            cont.markdown(f"<div class='evt-card'>{nm}</div>", unsafe_allow_html=True)
                elif sun or sat_close or past:
                    cont.markdown("<div class='blocked-slot'></div>", unsafe_allow_html=True)
                else:
                    if not is_admin_mode:
                        if cont.button(" ", key=f"add_{d}_{h}", type="secondary", use_container_width=True):
                            modal_agendamento(sala, d, h)
                    else:
                        cont.markdown("<div style='height:50px; border-right:1px solid #f1f5f9'></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

def tela_admin_master():
    tabs = st.tabs(["💰 Config", "📅 Visualizar", "🚫 Bloqueios", "📄 Relatórios", "👥 Usuários"])
    with tabs[0]: 
        cf = get_config_precos()
        c1, c2 = st.columns(2)
        with c1: 
            ph = st.number_input("Valor Hora", value=cf['preco_hora'])
            pm = st.number_input("Manhã", value=cf['preco_manha'])
            pt = st.number_input("Tarde", value=cf['preco_tarde'])
        with c2:
            pn = st.number_input("Noite", value=cf['preco_noite'])
            pdia = st.number_input("Diária", value=cf['preco_diaria'])
            if st.button("Salvar Preços", type="primary"):
                supabase.table("configuracoes").update({"preco_hora": ph, "preco_manha": pm, "preco_tarde": pt, "preco_noite": pn, "preco_diaria": pdia}).gt("id", 0).execute()
                st.success("Salvo!")
    with tabs[1]:
        sala_adm = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
        render_calendar(sala_adm, is_admin_mode=True)
    with tabs[2]:
        c_dt, c_sl = st.columns(2)
        dt_block = c_dt.date_input("Data")
        sala_block = c_sl.selectbox("Sala", ["Sala 1", "Sala 2", "Ambas"])
        if st.button("Bloquear Dia", type="primary"):
            salas = ["Sala 1", "Sala 2"] if sala_block == "Ambas" else [sala_block]
            for s in salas:
                supabase.table("reservas").update({"status": "cancelada"}).eq("sala_nome", s).eq("data_reserva", str(dt_block)).neq("status", "cancelada").execute()
                inserts = [{"sala_nome": s, "data_reserva": str(dt_block), "hora_inicio": f"{h:02d}:00", "hora_fim": f"{h+1:02d}:00", "user_id": st.session_state.user.id, "email_profissional": "ADM", "nome_profissional": "BLOQUEIO", "valor_cobrado": 0, "status": "bloqueado"} for h in range(7, 22)]
                supabase.table("reservas").insert(inserts).execute()
            st.success("Bloqueado!")
        if st.button("Desbloquear Dia", type="secondary"):
            salas = ["Sala 1", "Sala 2"] if sala_block == "Ambas" else [sala_block]
            for s in salas: supabase.table("reservas").delete().eq("sala_nome", s).eq("data_reserva", str(dt_block)).eq("status", "bloqueado").execute()
            st.success("Desbloqueado!")
    with tabs[3]:
        st.info("Relatórios")
    with tabs[4]:
        st.info("Usuários")

# --- 7. MAIN ---
def main():
    if not st.session_state.user:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.write("") 
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            
            if st.session_state.auth_mode == 'login':
                with st.form("login"):
                    email = st.text_input("Email")
                    senha = st.text_input("Senha", type="password")
                    if st.form_submit_button("Entrar", use_container_width=True):
                        try:
                            u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                            if u.user: st.session_state.user = u.user; st.session_state.is_admin = (email == "admin@admin.com.br"); st.rerun()
                        except: st.error("Erro login")
                c_a, c_b = st.columns(2)
                if c_a.button("Criar Conta"): st.session_state.auth_mode = 'register'; st.rerun()
                if c_b.button("Recuperar"): st.session_state.auth_mode = 'forgot'; st.rerun()
            
            elif st.session_state.auth_mode == 'register':
                st.markdown("### Criar Conta")
                nm = st.text_input("Nome")
                em = st.text_input("Email")
                pw = st.text_input("Senha", type="password")
                if st.button("Cadastrar", type="primary"):
                    try: supabase.auth.sign_up({"email": em, "password": pw, "options": {"data": {"nome": nm}}}); st.success("OK!"); time.sleep(1); st.session_state.auth_mode='login'; st.rerun()
                    except: st.error("Erro")
                if st.button("Voltar"): st.session_state.auth_mode='login'; st.rerun()
            
            elif st.session_state.auth_mode == 'forgot':
                em = st.text_input("Email")
                if st.button("Enviar"): 
                    try: supabase.auth.sign_in_with_otp({"email": em}); st.session_state.reset_email=em; st.session_state.auth_mode='verify_otp'; st.rerun()
                    except: st.error("Erro")
                if st.button("Voltar"): st.session_state.auth_mode='login'; st.rerun()
            
            elif st.session_state.auth_mode == 'verify_otp':
                otp = st.text_input("Código")
                if st.button("Verificar"):
                    try: 
                        r = supabase.auth.verify_otp({"email": st.session_state.reset_email, "token": otp, "type": "recovery"})
                        if r.user: st.session_state.user=r.user; st.session_state.auth_mode='reset_screen'; st.rerun()
                    except: st.error("Inválido")
            
            elif st.session_state.auth_mode == 'reset_screen':
                np = st.text_input("Nova Senha", type="password")
                if st.button("Salvar"): supabase.auth.update_user({"password": np}); st.session_state.auth_mode='login'; st.rerun()
        return

    u = st.session_state['user']
    if u is None: st.session_state.auth_mode = 'login'; st.rerun(); return

    if st.session_state.get('is_admin'):
        c_head_text, c_head_btn = st.columns([5, 1])
        with c_head_text: st.markdown("<h3 style='color:#0d9488; margin:0'>Painel Admin</h3>", unsafe_allow_html=True)
        with c_head_btn: 
            if st.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        st.divider()
        tela_admin_master()
    else:
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        c_head_text, c_head_btn = st.columns([5, 1])
        with c_head_text: st.markdown(f"<h3 style='color:#0d9488; margin:0'>LocaPsico | {nm}</h3>", unsafe_allow_html=True)
        with c_head_btn: 
            if st.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        st.divider()
        
        tabs = st.tabs(["📅 Agenda", "📊 Painel", "🔒 Conta"])
        
        with tabs[0]:
            sala = st.radio("Local", ["Sala 1", "Sala 2"], horizontal=True)
            render_calendar(sala)
            
        with tabs[1]:
            st.markdown("### Meus Agendamentos")
            agora = datetime.datetime.now()
            inicio_mes = datetime.date.today().replace(day=1)
            try:
                r = supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").gte("data_reserva", str(inicio_mes)).order("data_reserva").execute()
                df = pd.DataFrame(r.data)
                if not df.empty:
                    for _, row in df.iterrows():
                        dt_res = datetime.datetime.combine(datetime.date.fromisoformat(row['data_reserva']), datetime.datetime.strptime(row['hora_inicio'], "%H:%M:%S").time())
                        if dt_res < agora:
                            st.markdown(f"<div style='background:#f8fafc; padding:10px; border-radius:8px; color:#94a3b8; margin-bottom:8px'>✅ {row['data_reserva']} às {row['hora_inicio'][:5]} <small>({row['sala_nome']})</small></div>", unsafe_allow_html=True)
                        else:
                            with st.container():
                                c1, c2 = st.columns([3,1])
                                c1.markdown(f"**{row['data_reserva']}** às {row['hora_inicio'][:5]} - {row['sala_nome']}")
                                if dt_res > agora + timedelta(hours=24):
                                    if c2.button("Cancelar", key=f"c_{row['id']}"): supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute(); st.rerun()
                                else: c2.caption("🚫 <24h")
                                st.divider()
                else: st.info("Nada este mês.")
            except: pass
            
            st.markdown("### Financeiro")
            try:
                df_all = pd.DataFrame(supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").execute().data)
                k1, k2 = st.columns(2)
                k1.metric("Total Investido", f"R$ {df_all['valor_cobrado'].sum():.0f}")
                k2.metric("Sessões", len(df_all))
            except: pass

        with tabs[2]:
            p = st.text_input("Nova Senha", type="password")
            if st.button("Trocar Senha"):
                if len(p)<6: st.warning("Min 6 chars")
                else: supabase.auth.update_user({"password": p}); st.success("Atualizado!")

if __name__ == "__main__":
    main()
