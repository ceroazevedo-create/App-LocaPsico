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

# --- 1. CONFIGURAÇÕES E ESTADO ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide", initial_sidebar_state="collapsed")

if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'SEMANA'

NOME_DO_ARQUIVO_LOGO = "logo.png"

@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 2. CSS PREMIUM (VERSÃO DOUG 7.0) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; color: #1e293b; }
    .block-container { padding-top: 2rem !important; max-width: 1100px; }
    
    /* Botões Primários */
    div[data-testid="stForm"] button, button[kind="primary"] {
        background: linear-gradient(180deg, #0f766e 0%, #0d9488 100%) !important;
        border: none !important; color: white !important; border-radius: 8px !important;
        font-weight: 600 !important; height: 45px !important;
    }
    
    /* Slots do Calendário */
    .evt-chip { background: white; border-left: 4px solid #0d9488; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                color: #0f766e; font-size: 11px; font-weight: 600; padding: 6px 8px; border-radius: 4px; margin-bottom: 4px; }
    .blocked-slot { background-color: #fef2f2; height: 35px; border-radius: 6px; border: 1px solid #fecaca; opacity: 0.7; }
    .admin-blocked { background: #334155; color: white; border-radius: 4px; font-size: 10px; padding: 8px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# Cleaner
components.html("""<script>try{const doc=window.parent.document;const style=doc.createElement('style');style.innerHTML=`header, footer, [data-testid="stToolbar"] { display: none !important; }`;doc.head.appendChild(style);}catch(e){}</script>""", height=0)

# --- 3. UTILITÁRIOS ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if not email: return "Visitante"
    nome = nome_banco or nome_meta or email.split('@')[0]
    return str(nome).strip().split(' ')[0].title()

def get_config_precos():
    try:
        r = supabase.table("configuracoes").select("*").limit(1).execute()
        return r.data[0] if r.data else {'preco_hora': 32.0, 'preco_manha': 100.0, 'preco_tarde': 100.0, 'preco_noite': 80.0, 'preco_diaria': 250.0}
    except: return {'preco_hora': 32.0, 'preco_manha': 100.0, 'preco_tarde': 100.0, 'preco_noite': 80.0, 'preco_diaria': 250.0}

def navegar(direcao):
    delta = 1 if st.session_state.view_mode == 'DIA' else (7 if st.session_state.view_mode == 'SEMANA' else 30)
    st.session_state.data_ref += timedelta(days=delta if direcao == 'next' else -delta)

# --- 4. O MOTOR DE AGENDAMENTO (ATÔMICO) ---
@st.dialog("Novo Agendamento")
def modal_agendamento(sala_padrao, data_sugerida, hora_sugerida_int=None):
    st.markdown(f"### Reservar: {data_sugerida.strftime('%d/%m/%Y')}")
    cf = get_config_precos()
    modo = st.radio("Cobrança", ["Por Hora", "Por Período"], horizontal=True)
    horarios_selecionados = []
    valor_final = 0.0

    if modo == "Por Hora":
        if data_sugerida.weekday() == 6: st.error("Domingo Fechado"); return
        lista_h = [f"{h:02d}:00" for h in (range(7, 14) if data_sugerida.weekday() == 5 else range(7, 22))]
        idx = lista_h.index(f"{hora_sugerida_int:02d}:00") if hora_sugerida_int and f"{hora_sugerida_int:02d}:00" in lista_h else 0
        hr = st.selectbox("Início", lista_h, index=idx)
        horarios_selecionados = [(hr, f"{int(hr[:2])+1:02d}:00")]
        valor_final = cf['preco_hora']
    else:
        opc = {"Manhã (07-12h)": (7,12,cf['preco_manha']), "Tarde (13-18h)": (13,18,cf['preco_tarde']), 
               "Noite (18-22h)": (18,22,cf['preco_noite']), "Diária (07-22h)": (7,22,cf['preco_diaria'])}
        sel = st.selectbox("Período", list(opc.keys()))
        h1, h2, p = opc[sel]
        horarios_selecionados = [(f"{h:02d}:00", f"{h+1:02d}:00") for h in range(h1, h2)]
        valor_final = p

    repetir = st.checkbox("🔄 Repetir por 4 semanas")
    
    if st.button("Confirmar", type="primary", use_container_width=True):
        agora = datetime.datetime.now()
        datas = [data_sugerida + timedelta(days=7*i) for i in range(4 if repetir else 1)]
        inserts = []
        
        # Validação All-or-Nothing
        for d in datas:
            if d.weekday() == 6: continue
            for h_s, h_e in horarios_selecionados:
                dt_c = datetime.datetime.combine(d, datetime.datetime.strptime(h_s, "%H:%M").time())
                if dt_c < agora: st.error(f"Data {d} {h_s} já passou."); return
                
                chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(d)).eq("hora_inicio", f"{h_s}:00").neq("status", "cancelada").execute()
                if chk.data: st.error(f"Conflito em {d} às {h_s}"); return
                
                v = valor_final if (modo == "Por Hora" or (h_s, h_e) == horarios_selecionados[0]) else 0
                inserts.append({"sala_nome": sala_padrao, "data_reserva": str(d), "hora_inicio": f"{h_s}:00", "hora_fim": f"{h_e}:00",
                               "user_id": st.session_state.user.id, "email_profissional": st.session_state.user.email,
                               "nome_profissional": resolver_nome(st.session_state.user.email), "valor_cobrado": v, "status": "confirmada"})
        
        if inserts:
            supabase.table("reservas").insert(inserts).execute()
            st.toast("Reservado!", icon="✅"); time.sleep(1); st.rerun()

# --- 5. RENDERIZAÇÃO DO CALENDÁRIO ---
def render_calendar(sala, is_admin=False):
    c1, c2 = st.columns(2)
    if c1.button("◀ Ant", use_container_width=True, key=f"p{is_admin}"): navegar('prev'); st.rerun()
    if c2.button("Próx ▶", use_container_width=True, key=f"n{is_admin}"): navegar('next'); st.rerun()
    
    ref = st.session_state.data_ref
    d_ini = ref - timedelta(days=ref.weekday())
    d_fim = d_ini + timedelta(days=6)
    
    st.markdown(f"<center><b>{d_ini.day} - {d_fim.day} {ref.strftime('%B')}</b></center>", unsafe_allow_html=True)
    
    res = supabase.table("reservas").select("*").eq("sala_nome", sala).neq("status", "cancelada").gte("data_reserva", str(d_ini)).lte("data_reserva", str(d_fim)).execute().data
    mapa = {f"{r['data_reserva']}_{r['hora_inicio']}": r for r in res}
    
    visiveis = [d_ini + timedelta(days=i) for i in range(7)]
    cols = st.columns([0.6] + [1]*7)
    d_nomes = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
    
    for i, d in enumerate(visiveis):
        with cols[i+1]:
            if st.button(f"{d_nomes[d.weekday()]} {d.day}", key=f"d{d}{is_admin}", use_container_width=True):
                if d >= datetime.date.today() and d.weekday() != 6: modal_agendamento(sala, d)

    for h in range(7, 22):
        row = st.columns([0.6] + [1]*7)
        row[0].markdown(f"<div style='font-size:11px; color:#94a3b8; margin-top:10px'>{h:02d}:00</div>", unsafe_allow_html=True)
        for i, d in enumerate(visiveis):
            h_str = f"{h:02d}:00:00"
            key = f"{d}_{h_str}"
            slot = mapa.get(key)
            
            with row[i+1]:
                if slot:
                    if slot['status'] == 'bloqueado': st.markdown("<div class='admin-blocked'>⛔</div>", unsafe_allow_html=True)
                    else: st.markdown(f"<div class='evt-chip'>{resolver_nome(slot['email_profissional'])}</div>", unsafe_allow_html=True)
                elif d.weekday() == 6 or (d.weekday() == 5 and h >= 14) or datetime.datetime.combine(d, datetime.time(h,0)) < datetime.datetime.now():
                    st.markdown("<div class='blocked-slot'></div>", unsafe_allow_html=True)
                elif not is_admin:
                    if st.button("Livre", key=f"f{key}", type="secondary", use_container_width=True): modal_agendamento(sala, d, h)

# --- 6. TELAS ---
def tela_admin():
    t1, t2, t3 = st.tabs(["💰 Preços", "📅 Agenda", "👥 Usuários"])
    with t1:
        cf = get_config_precos()
        ph = st.number_input("Hora", value=cf['preco_hora'])
        if st.button("Salvar"): supabase.table("configuracoes").update({"preco_hora": ph}).gt("id", 0).execute(); st.success("Ok")
    with t2:
        s = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True, key="adm_s")
        render_calendar(s, True)
    with t3:
        st.write("Gerenciar usuários...")

def main():
    if not st.session_state.user:
        _, c2, _ = st.columns([1, 1.2, 1])
        with c2:
            st.markdown("<h1>LocaPsico</h1>", unsafe_allow_html=True)
            with st.form("l"):
                e = st.text_input("Email")
                p = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": e, "password": p})
                        st.session_state.user = u.user
                        st.session_state.is_admin = (e == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Falha")
        return

    # Header
    c1, c2 = st.columns([5,1])
    c1.subheader(f"Olá, {resolver_nome(st.session_state.user.email)}")
    if c2.button("Sair"): st.session_state.clear(); st.rerun()
    
    if st.session_state.is_admin: tela_admin()
    else:
        s = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
        render_calendar(s)

if __name__ == "__main__":
    main()

