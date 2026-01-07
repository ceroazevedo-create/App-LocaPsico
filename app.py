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

NOME_DO_ARQUIVO_LOGO = "logo.png"

# --- 2. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. CSS VISUAL (DESIGN PREMIUM) ---
st.markdown("""
<style>
    /* --- FUNDO E TIPOGRAFIA GERAL --- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
        color: #1e293b;
    }
    
    .block-container {
        padding-top: 2rem !important;
        max-width: 1100px;
    }

    /* Container Principal */
    div[data-testid="column"]:nth-of-type(2) > div {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #f1f5f9;
        margin-bottom: 20px;
    }

    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
        margin-bottom: 24px;
    }
    div[data-testid="stImage"] > img {
        max-height: 120px;
        object-fit: contain;
    }

    h1 {
        font-size: 26px;
        font-weight: 700;
        color: #0f172a;
        text-align: center;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    }
    h2, h3 { color: #334155; font-weight: 600; }
    p { color: #64748b; }

    /* --- INPUTS --- */
    .stTextInput input {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 12px;
        height: 45px;
        font-size: 15px;
        transition: all 0.2s;
    }
    .stTextInput input:focus {
        border-color: #0d9488;
        box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.2);
    }

    /* --- BOTÕES PRIMÁRIOS (VERDE TEAL) --- */
    div[data-testid="stForm"] button, 
    button[kind="primary"] {
        background: linear-gradient(180deg, #0f766e 0%, #0d9488 100%) !important;
        border: none !important;
        height: 45px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(13, 148, 136, 0.2) !important;
        color: white !important;
        transition: transform 0.1s ease !important;
    }
    div[data-testid="stForm"] button:hover, 
    button[kind="primary"]:hover {
        background: #0f766e !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(13, 148, 136, 0.3) !important;
    }
    div[data-testid="stForm"] button *, button[kind="primary"] * {
        color: white !important;
    }

    /* --- BOTÕES SECUNDÁRIOS --- */
    button[kind="secondary"] {
        background-color: white !important;
        border: 1px solid #cbd5e1 !important;
        color: #475569 !important;
        border-radius: 8px !important;
        height: 45px !important;
        font-weight: 500 !important;
    }
    button[kind="secondary"]:hover {
        background-color: #f1f5f9 !important;
        border-color: #94a3b8 !important;
        color: #1e293b !important;
    }

    /* --- BOTÕES DO CALENDÁRIO (DIAS) --- */
    div[data-testid="stButton"] button {
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
    }

    /* --- SLOT "LIVRE" --- */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        background-color: #f0fdf4 !important;
        border: 1px solid #bbf7d0 !important;
        color: #15803d !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        height: 38px !important;
        min-height: 38px !important;
        border-radius: 6px !important;
        box-shadow: none !important;
        transition: all 0.2s;
    }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        background-color: #16a34a !important;
        border-color: #16a34a !important;
        color: white !important;
    }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover p {
        color: white !important;
    }

    /* --- MÉTRICAS --- */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] { font-size: 14px !important; color: #64748b !important; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; color: #0d9488 !important; font-weight: 700 !important; }

    /* --- BOTÕES DE PERIGO --- */
    button[help="Excluir Usuário"], button[key="logout_btn"], button[key="admin_logout"] { 
        border-color: #fecaca !important; 
        color: #dc2626 !important; 
        background-color: #fef2f2 !important; 
    }
    button[help="Excluir Usuário"]:hover, button[key="logout_btn"]:hover {
        background-color: #dc2626 !important;
        color: white !important;
        border-color: #dc2626 !important;
    }
    button[help="Excluir Usuário"]:hover *, button[key="logout_btn"]:hover * { color: white !important; }

    /* Olhinho da senha */
    div[data-testid="stTextInput"] button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    .evt-chip {
        background: white;
        border-left: 4px solid #0d9488;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        color: #0f766e;
        font-size: 11px;
        font-weight: 600;
        padding: 6px 8px;
        border-radius: 4px;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
    }
    .admin-blocked { background: #334155; color: #f8fafc; border-radius: 4px; font-size: 10px; font-weight: bold; text-align: center; padding: 8px; letter-spacing: 1px; }
    .blocked-slot { background-color: #fef2f2; height: 35px; border-radius: 6px; border: 1px solid #fecaca; opacity: 0.7; margin-bottom: 5px; }
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
    if nome_completo is None: return "Usuário"
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
    mode = st.session_state.view_mode
    delta = 1 if mode == 'DIA' else (7 if mode == 'SEMANA' else 30)
    if direcao == 'prev': st.session_state.data_ref -= timedelta(days=delta)
    else: st.session_state.data_ref += timedelta(days=delta)

@st.dialog("Novo Agendamento")
def modal_agendamento(sala_padrao, data_sugerida, hora_sugerida_int=None):
    st.markdown(f"### Reservar para {data_sugerida.strftime('%d/%m/%Y')}")
    config_precos = get_config_precos()
    modo = st.radio("Tipo de Cobrança", ["Por Hora", "Por Período"], horizontal=True)
    dt = data_sugerida
    horarios_selecionados = []
    valor_final = 0.0
    if modo == "Por Hora":
        dia_sem = dt.weekday()
        if dia_sem == 6: lista_horas = []; st.error("Domingo: Fechado")
        elif dia_sem == 5: lista_horas = [f"{h:02d}:00" for h in range(7, 14)]; st.info("Sábado: Até 14h")
        else: lista_horas = [f"{h:02d}:00" for h in range(7, 22)]
        idx_padrao = 0
        if hora_sugerida_int:
            str_h = f"{hora_sugerida_int:02d}:00"
            if str_h in lista_horas:
                idx_padrao = lista_horas.index(str_h)
        hr = st.selectbox("Horário de Início", lista_horas, index=idx_padrao, disabled=(len(lista_horas)==0))
        if hr:
            horarios_selecionados = [(hr, f"{int(hr[:2])+1:02d}:00")]
            valor_final = config_precos['preco_hora']
    else:
        opcoes_periodo = {
            "Manhã (07h - 12h)": {"start": 7, "end": 12, "price": config_precos['preco_manha']},
            "Tarde (13h - 18h)": {"start": 13, "end": 18, "price": config_precos['preco_tarde']},
            "Noite (18h - 22h)": {"start": 18, "end": 22, "price": config_precos['preco_noite']},
            "Diária (07h - 22h)": {"start": 7, "end": 22, "price": config_precos['preco_diaria']}
        }
        sel_periodo = st.selectbox("Escolha o Período", list(opcoes_periodo.keys()))
        dados_p = opcoes_periodo[sel_periodo]
        st.info(f"Reservando das {dados_p['start']}:00 às {dados_p['end']}:00 - Valor: R$ {dados_p['price']:.2f}")
        for h in range(dados_p['start'], dados_p['end']):
            horarios_selecionados.append((f"{h:02d}:00", f"{h+1:02d}:00"))
        valor_final = dados_p['price']
    st.markdown("---")
    is_recurring = st.checkbox("🔄 Repetir nas próximas 4 semanas (Mensal)")
    if st.button("Confirmar Agendamento", type="primary", use_container_width=True):
        if not horarios_selecionados: st.error("Nenhum horário selecionado."); return
        user = st.session_state.user
        nm = resolver_nome(user.email, user.user_metadata.get('nome'))
        agora = datetime.datetime.now()
        datas_to_book = [dt]
        if is_recurring:
            for i in range(1, 4): datas_to_book.append(dt + timedelta(days=7*i))
        try:
            inserts = []
            for d_res in datas_to_book:
                if d_res.weekday() == 6: st.warning(f"Ignorado {d_res} (Domingo)."); continue
                for h_start, h_end in horarios_selecionados:
                    dt_check = datetime.datetime.combine(d_res, datetime.datetime.strptime(h_start, "%H:%M").time())
                    if dt_check < agora: st.error(f"Horário {h_start} em {d_res} já passou."); return
                    if d_res.weekday() == 5 and int(h_start[:2]) >= 14: st.error(f"Sábado {d_res} fecha às 14h."); return
                    chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(d_res)).eq("hora_inicio", f"{h_start}:00").neq("status", "cancelada").execute()
                    if chk.data: st.error(f"Conflito: {d_res} às {h_start} já está ocupado."); return 
                    val_to_save = 0.0
                    if (h_start, h_end) == horarios_selecionados[0]: val_to_save = valor_final
                    elif modo == "Por Hora": val_to_save = valor_final 
                    inserts.append({
                        "sala_nome": sala_padrao, "data_reserva": str(d_res), "hora_inicio": f"{h_start}:00", "hora_fim": f"{h_end}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": val_to_save, "status": "confirmada"
                    })
            if inserts:
                supabase.table("reservas").insert(inserts).execute()
                st.toast("Agendamento(s) realizado(s)!", icon="✅"); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Erro técnico: {e}")

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
        for i, d in enumerate(dias): cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#64748b; font-size:12px; margin-bottom:5px'>{d}</div>", unsafe_allow_html=True)
        cal_matrix = calendar.monthcalendar(ref.year, ref.month)
        for week in cal_matrix:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0: cols[i].write("")
                else:
                    d_obj = datetime.date(ref.year, ref.month, day)
                    d_str = str(d_obj)
                    with cols[i]:
                        if not is_admin_mode:
                            if st.button(f"{day}", key=f"btn_day_{day}_{mes}_{is_admin_mode}", use_container_width=True):
                                if d_obj < datetime.date.today(): st.toast("Data passada.", icon="🚫")
                                elif d_obj.weekday() == 6: st.toast("Domingo fechado.", icon="🚫")
                                else: modal_agendamento(sala, d_obj)
                        else:
                            st.markdown(f"<div style='text-align:center; font-weight:bold; padding:5px'>{day}</div>", unsafe_allow_html=True)
                    eventos_html = ""
                    if d_str in mapa:
                        for h in sorted(mapa[d_str].keys()):
                            res = mapa[d_str][h]
                            if res['status'] == 'bloqueado': eventos_html += f"<div style='background:#1e293b; color:white; font-size:9px; padding:2px; border-radius:3px; margin-bottom:2px;'>⛔ BLOQ</div>"
                            else:
                                nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                                eventos_html += f"<div style='background:#ccfbf1; color:#115e59; font-size:9px; padding:2px; border-radius:3px; margin-bottom:2px; white-space:nowrap; overflow:hidden;'>{h[:5]} {nm}</div>"
                    cols[i].markdown(f"{eventos_html}", unsafe_allow_html=True)
    else:
        visiveis = [d_start + timedelta(days=i) for i in range(7 if mode == 'SEMANA' else 1)]
        ratio = [0.6] + [1]*len(visiveis)
        c_h = st.columns(ratio)
        c_h[0].write("")
        d_n = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
        for i, d in enumerate(visiveis):
            wd = d.weekday()
            with c_h[i+1]:
                lbl_sem = f"{d_n[wd]} {d.day}"
                if not is_admin_mode:
                    if st.button(lbl_sem, key=f"btn_week_{d}_{is_admin_mode}", use_container_width=True):
                         if d < datetime.date.today(): st.toast("Data passada.", icon="🚫")
                         elif d.weekday() == 6: st.toast("Domingo fechado.", icon="🚫")
                         else: modal_agendamento(sala, d)
                else:
                    st.markdown(f"<div style='text-align:center; font-weight:bold; color:#1e293b'>{lbl_sem}</div>", unsafe_allow_html=True)
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
                             if cont.button("🗑️", key=f"del_blk_{res['id']}"): supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                    else:
                        nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                        if is_admin_mode:
                            c_chip, c_del = cont.columns([3,1])
                            c_chip.markdown(f"<div class='evt-chip'>{nm}</div>", unsafe_allow_html=True)
                            if c_del.button("🗑️", key=f"del_res_{res['id']}", help="Excluir"): supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                        else: cont.markdown(f"<div class='evt-chip'>{nm}</div>", unsafe_allow_html=True)
                elif is_sunday or is_sat_closed or is_past: cont.markdown("<div class='blocked-slot'></div>", unsafe_allow_html=True)
                else: 
                    if not is_admin_mode:
                        if cont.button("Livre", key=f"free_{d_s}_{h}", type="secondary", use_container_width=True):
                            modal_agendamento(sala, d, h)
                    else:
                        cont.markdown("<div style='height:35px; border-left:1px dashed #cbd5e1'></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

def tela_admin_master():
    tabs = st.tabs(["💰 Config", "📅 Visualizar/Excluir", "🚫 Bloqueios", "📄 Relatórios", "👥 Usuários"])
    with tabs[0]: 
        cf = get_config_precos()
        st.markdown("### Configuração de Preços")
        c1, c2 = st.columns(2)
        with c1: 
            ph = st.number_input("Valor Hora (R$)", value=cf['preco_hora'], step=1.0)
            pm = st.number_input("Valor Manhã (07-12h)", value=cf['preco_manha'], step=1.0)
            pt = st.number_input("Valor Tarde (13-18h)", value=cf['preco_tarde'], step=1.0)
        with c2:
            pn = st.number_input("Valor Noite (18-22h)", value=cf['preco_noite'], step=1.0)
            pdia = st.number_input("Valor Diária (07-22h)", value=cf['preco_diaria'], step=1.0)
            st.write("")
            if st.button("💾 Salvar Tabela de Preços", type="primary"):
                supabase.table("configuracoes").update({
                    "preco_hora": ph, "preco_manha": pm, "preco_tarde": pt, 
                    "preco_noite": pn, "preco_diaria": pdia
                }).gt("id", 0).execute()
                st.success("Preços atualizados!")
    with tabs[1]:
        st.info("Selecione a sala para visualizar.")
        sala_adm = st.radio("Selecione Sala:", ["Sala 1", "Sala 2"], horizontal=True, key="sala_adm_view")
        render_calendar(sala_adm, is_admin_mode=True)
    with tabs[2]:
        st.write("Bloquear dias inteiros")
        c_dt_b, c_sl_b, c_bt_b = st.columns([2, 2, 2])
        dt_block = c_dt_b.date_input("Data para Bloquear")
        sala_block = c_sl_b.selectbox("Sala", ["Sala 1", "Sala 2", "Ambas"])
        if c_bt_b.button("🔒 Bloquear Data", type="primary"):
            salas_to_block = ["Sala 1", "Sala 2"] if sala_block == "Ambas" else [sala_block]
            try:
                for s in salas_to_block:
                    supabase.table("reservas").update({"status": "cancelada"}).eq("sala_nome", s).eq("data_reserva", str(dt_block)).neq("status", "cancelada").execute()
                inserts = []
                for s in salas_to_block:
                    for h in range(7, 22):
                        inserts.append({
                            "sala_nome": s, "data_reserva": str(dt_block), "hora_inicio": f"{h:02d}:00", "hora_fim": f"{h+1:02d}:00",
                            "user_id": "admin_block", "email_profissional": "admin@locapsico.com", "nome_profissional": "BLOQUEIO ADM",
                            "valor_cobrado": 0, "status": "bloqueado"
                        })
                supabase.table("reservas").insert(inserts).execute()
                st.success(f"Dia {dt_block} bloqueado!")
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
                        df_fin = df_fin.sort_values(by=['data_reserva', 'hora_inicio'])
                        df_fin['nm'] = df_fin.apply(lambda x: resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                        df_final = df_fin[df_fin['nm'] == user_sel]
                        if not df_final.empty:
                            total = df_final['valor_cobrado'].sum()
                            st.success(f"Total a Receber: R$ {total:.2f}")
                            st.markdown("### Detalhamento")
                            df_table = df_final[['data_reserva', 'hora_inicio', 'sala_nome', 'valor_cobrado']].copy()
                            df_table.columns = ['Data', 'Horário', 'Sala', 'Valor (R$)']
                            st.dataframe(df_table, use_container_width=True, hide_index=True)
                            pdf_data = gerar_pdf_fatura(df_final, user_sel, mes_sel)
                            b64 = base64.b64encode(pdf_data).decode()
                            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Extrato_{user_sel}_{mes_sel}.pdf" style="text-decoration:none; background:#0d9488; color:white; padding:10px; border-radius:8px; display:block; text-align:center;">📥 BAIXAR PDF DETALHADO</a>', unsafe_allow_html=True)
                        else: st.warning("Sem dados.")
                    else: st.warning("Sem dados.")
        except: pass
    with tabs[4]:
        st.markdown("### Gerenciar Usuários")
        service_key = st.secrets.get("SUPABASE_SERVICE_KEY")
        if service_key:
            st.success("🟢 Modo Super Admin: Exclusão total ativada.")
        else:
            st.warning("🟡 Modo Limitado: Histórico apagado, login mantido. Configure SUPABASE_SERVICE_KEY para apagar tudo.")
        df_users = pd.DataFrame()
        if service_key:
            try:
                adm_client = create_client(st.secrets["SUPABASE_URL"], service_key)
                auth_users = adm_client.auth.admin.list_users()
                users_list = []
                for u in auth_users:
                    users_list.append({"user_id": u.id, "email_profissional": u.email, "nome_profissional": u.user_metadata.get('nome', 'Sem Nome')})
                df_users = pd.DataFrame(users_list)
            except Exception as e: pass
        if df_users.empty:
            try:
                users_data = supabase.table("reservas").select("user_id, email_profissional, nome_profissional").execute().data
                if users_data:
                    df_users = pd.DataFrame(users_data).drop_duplicates(subset=['user_id'])
            except: pass
        if not df_users.empty:
            for _, row in df_users.iterrows():
                if st.session_state.user.id == row['user_id']: continue
                with st.container():
                    c1, c2, c3 = st.columns([3, 3, 2])
                    raw_name = row.get('nome_profissional')
                    raw_email = row.get('email_profissional')
                    nm_show = resolver_nome(raw_email, nome_banco=raw_name)
                    c1.write(f"**{nm_show}**")
                    c2.write(f"_{raw_email}_")
                    if c3.button("🗑️ Remover", key=f"rm_user_{row['user_id']}", help="Excluir Usuário"):
                        if service_key:
                            try:
                                adm_client = create_client(st.secrets["SUPABASE_URL"], service_key)
                                try: adm_client.table("reservas").delete().eq("user_id", row['user_id']).execute()
                                except: pass
                                try: adm_client.table("profiles").delete().eq("id", row['user_id']).execute()
                                except: pass
                                adm_client.auth.admin.delete_user(row['user_id'])
                                st.toast("Usuário excluído completamente!", icon="✅")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir: {e}")
                                st.warning("Verifique se rodou o comando SQL no Supabase para 'on delete cascade'.")
                        else:
                            try:
                                supabase.table("reservas").delete().eq("user_id", row['user_id']).execute()
                                st.toast("Histórico limpo (Login mantido).", icon="⚠️")
                            except: pass
                            time.sleep(1.5)
                            st.rerun()
                    st.divider()
        else:
            st.info("Nenhum usuário encontrado.")

# --- 7. MAIN ---
def main():
    if not st.session_state.user:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.write("") 
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='text-align:center; color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            
            if st.session_state.auth_mode == 'login':
                st.markdown("<h1>Bem-vindo de volta</h1>", unsafe_allow_html=True)
                with st.form("login_form"):
                    email = st.text_input("E-mail profissional", placeholder="seu@email.com")
                    senha = st.text_input("Sua senha", type="password", placeholder="••••••••")
                    submitted = st.form_submit_button("Entrar na Agenda")
                    if submitted:
                        try:
                            u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                            if u.user:
                                st.session_state['user'] = u.user
                                st.session_state['is_admin'] = (email == "admin@admin.com.br")
                                st.rerun()
                        except Exception as e:
                            if "Invalid login credentials" in str(e): st.error("E-mail ou senha incorretos.")
                            else: st.error(f"Erro ao entrar: {e}")
                st.markdown("<br>", unsafe_allow_html=True)
                col_reg, col_rec = st.columns(2)
                with col_reg:
                    if st.button("Criar conta", type="secondary", use_container_width=True): st.session_state.auth_mode = 'register'; st.rerun()
                with col_rec:
                    if st.button("Esqueci senha", type="secondary", use_container_width=True): st.session_state.auth_mode = 'forgot'; st.rerun()

            elif st.session_state.auth_mode == 'forgot':
                st.markdown("<h1>Recuperar Senha</h1>", unsafe_allow_html=True)
                st.info("Vamos enviar um CÓDIGO para seu e-mail.")
                reset_email = st.text_input("E-mail", value=st.session_state.reset_email)
                if st.button("Enviar Código", type="primary"):
                    try:
                        st.session_state.reset_email = reset_email
                        supabase.auth.sign_in_with_otp({"email": reset_email})
                        st.session_state.auth_mode = 'verify_otp'
                        st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
                if st.button("Voltar", type="secondary"): st.session_state.auth_mode = 'login'; st.rerun()

            elif st.session_state.auth_mode == 'verify_otp':
                st.markdown("<h1>Verificar Código</h1>", unsafe_allow_html=True)
                st.info(f"Enviado para: {st.session_state.reset_email}")
                otp_code = st.text_input("Digite o CÓDIGO do e-mail")
                if st.button("Verificar e Redefinir", type="primary"):
                    success = False
                    try:
                        res = supabase.auth.verify_otp({"email": st.session_state.reset_email, "token": otp_code, "type": "magiclink"})
                        if res.user: success = True
                    except: pass
                    if not success:
                        try:
                            res = supabase.auth.verify_otp({"email": st.session_state.reset_email, "token": otp_code, "type": "recovery"})
                            if res.user: success = True
                        except: pass
                    if not success:
                        try:
                            res = supabase.auth.verify_otp({"email": st.session_state.reset_email, "token": otp_code, "type": "email"})
                            if res.user: success = True
                        except: pass
                    if success:
                        curr_session = supabase.auth.get_session()
                        if curr_session:
                            st.session_state.user = curr_session.user
                            st.session_state.is_admin = (curr_session.user.email == "admin@admin.com.br")
                            st.session_state.auth_mode = 'reset_screen'
                            st.rerun()
                    else: st.error("Código inválido.")
                if st.button("Voltar", type="secondary"): st.session_state.auth_mode = 'forgot'; st.rerun()

            elif st.session_state.auth_mode == 'reset_screen':
                st.markdown("<h1>Nova Senha</h1>", unsafe_allow_html=True)
                new_pass = st.text_input("Digite sua nova senha", type="password")
                if st.button("Salvar Senha", type="primary"):
                    if len(new_pass) >= 6:
                        supabase.auth.update_user({"password": new_pass})
                        st.success("Senha alterada! Faça login.")
                        st.session_state.auth_mode = 'login'
                        st.session_state.user = None
                        time.sleep(2)
                        st.rerun()
                    else: st.warning("Senha curta.")

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
                            st.success("Sucesso! Faça login.")
                            time.sleep(1.5)
                            st.session_state.auth_mode = 'login'
                            st.rerun()
                        except Exception as e: st.error(f"Erro ao cadastrar: {e}")
                if st.button("Voltar", type="secondary"): st.session_state.auth_mode = 'login'; st.rerun()
        return

    u = st.session_state['user']
    if u is None: st.session_state.auth_mode = 'login'; st.rerun(); return

    if st.session_state.get('is_admin'):
        c_adm_title, c_adm_out = st.columns([5,1])
        with c_adm_title: st.markdown(f"<h3 style='color:#0d9488; margin:0'>Painel Administrativo</h3>", unsafe_allow_html=True)
        with c_adm_out:
            if st.button("Sair", key="admin_logout", use_container_width=True): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        st.divider()
        tela_admin_master()
    else:
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        c_head_text, c_head_btn = st.columns([5, 1])
        with c_head_text: st.markdown(f"<h3 style='color:#0d9488; margin:0'>LocaPsico | <span style='color:#334155'>Olá, {nm}</span></h3>", unsafe_allow_html=True)
        with c_head_btn:
            if st.button("Sair", key="logout_btn", use_container_width=True): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        st.divider()
        
        # --- ABAS (SEGURANÇA AGORA É UMA ABA) ---
        tabs = st.tabs(["📅 Agenda", "📊 Painel", "🔒 Segurança"])
        
        with tabs[0]:
            sala = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
            render_calendar(sala)
            
        with tabs[1]:
            # Fetch isolado para não conflitar com Rerun
            st.markdown("### Meus Agendamentos")
            agora = datetime.datetime.now()
            hoje = datetime.date.today()
            df_fut = pd.DataFrame()
            try:
                res_futuras = supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").gte("data_reserva", str(hoje)).order("data_reserva").order("hora_inicio").execute()
                df_fut = pd.DataFrame(res_futuras.data)
            except: st.error("Erro ao carregar dados.")

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
                                    try:
                                        supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                                        st.toast("Cancelado!", icon="✅")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e: st.error(f"Erro ao cancelar: {e}")
                            else: c_btn.caption("🚫 < 24h")
                            st.divider()
            else: st.info("Sem agendamentos futuros.")
                
            st.markdown("### Financeiro")
            try:
                df_all = pd.DataFrame(supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").execute().data)
                k1, k2 = st.columns(2)
                k1.metric("Investido Total", f"R$ {df_all['valor_cobrado'].sum() if not df_all.empty else 0:.0f}")
                k2.metric("Sessões Totais", len(df_all) if not df_all.empty else 0)
            except: st.error("Erro ao carregar financeiro.")
            
        with tabs[2]:
            st.markdown("### Segurança da Conta")
            st.markdown("Redefina sua senha de acesso abaixo.")
            
            p1 = st.text_input("Nova Senha", type="password")
            if st.button("Alterar Senha"):
                if len(p1) < 6: st.warning("A senha deve ter pelo menos 6 caracteres.")
                else:
                    try:
                        supabase.auth.update_user({"password": p1})
                        st.success("Senha atualizada com sucesso!")
                    except Exception as e: st.error(f"Erro ao atualizar senha: {e}")

if __name__ == "__main__":
    main()
