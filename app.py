import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import base64
import time
import os

# --- 1. CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide", initial_sidebar_state="collapsed")

# --- 2. GESTÃO DE ESTADO (MEMÓRIA) ---
# Autenticação
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'reset_email' not in st.session_state: st.session_state.reset_email = ""

# Agenda
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
if 'modal_ativo' not in st.session_state: st.session_state.modal_ativo = False
if 'dados_agendamento' not in st.session_state: st.session_state.dados_agendamento = {}

NOME_DO_ARQUIVO_LOGO = "logo.png"

# --- 3. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 4. CSS (LAYOUT RÍGIDO - O SEGREDO PARA NÃO EMPILHAR) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; font-family: 'Inter', sans-serif; color: #1e293b; }
    
    header, footer, [data-testid="stToolbar"] { display: none !important; }
    
    /* Botões Padrão */
    div[data-testid="stForm"] button, button[kind="primary"] { 
        background: #0f766e !important; color: white !important; border: none; border-radius: 6px; 
    }

    /* === TABELA RÍGIDA (MOBILE) === */
    @media only screen and (max-width: 768px) {
        
        /* Força o container da agenda a ter largura fixa maior que a tela */
        /* Isso OBRIGA o navegador a criar scroll horizontal em vez de empilhar */
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(8)) {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            width: 100% !important;
            min-width: 800px !important; /* <--- O SEGRED0 */
            gap: 2px !important;
        }

        /* Define largura fixa das colunas */
        div[data-testid="column"] {
            flex: 0 0 90px !important;
            width: 90px !important;
            min-width: 90px !important;
        }
        
        /* Coluna da Hora (Primeira) um pouco menor */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {
            flex: 0 0 50px !important;
            width: 50px !important;
            min-width: 50px !important;
            position: sticky !important;
            left: 0 !important;
            background: white !important;
            z-index: 100 !important;
            border-right: 1px solid #ddd !important;
        }

        /* Botões da Agenda (Quadrados) */
        div[data-testid="stVerticalBlock"] button[kind="secondary"] {
            height: 45px !important;
            border-radius: 0px !important;
            border: 1px solid #e2e8f0 !important;
            margin-bottom: 0px !important;
        }
        
        /* Remove espaçamento vertical */
        div[data-testid="stVerticalBlock"] { gap: 0px !important; }
    }
    
    /* Desktop */
    @media (min-width: 769px) {
        div[data-testid="stVerticalBlock"] { gap: 0px !important; }
        button[kind="secondary"] { border-radius: 0px !important; height: 45px !important; border: 1px solid #eee !important; }
    }

    /* Cartões de Status */
    .evt-card {
        background-color: #ef4444; border: 1px solid #b91c1c; color: white;
        width: 100%; height: 45px; font-size: 10px; font-weight: bold;
        display: flex; align-items: center; justify-content: center;
        overflow: hidden; white-space: nowrap;
    }
    .slot-past { background-color: #cbd5e1; height: 45px; border:1px solid #94a3b8; }
</style>
""", unsafe_allow_html=True)

# --- 5. FUNÇÕES AUXILIARES ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if not email: return "Visitante"
    nome_completo = nome_banco or nome_meta or email.split('@')[0]
    return str(nome_completo).strip().split(' ')[0].title()

def get_agora_br():
    return datetime.datetime.utcnow() - timedelta(hours=3)

def get_config_precos():
    defaults = {'preco_hora': 32.0, 'preco_manha': 100.0, 'preco_tarde': 100.0, 'preco_noite': 80.0, 'preco_diaria': 250.0}
    try:
        r = supabase.table("configuracoes").select("*").limit(1).execute()
        if r.data: return r.data[0]
        return defaults
    except: return defaults

def navegar(direcao):
    delta = 7 
    if direcao == 'prev': st.session_state.data_ref -= timedelta(days=delta)
    else: st.session_state.data_ref += timedelta(days=delta)

# CALLBACK DE CLIQUE (INFALÍVEL)
def abrir_modal(sala, dia, hora):
    st.session_state.dados_agendamento = {
        'sala': sala,
        'dia': dia,
        'hora': hora
    }
    st.session_state.modal_ativo = True

# --- 6. MODAL ---
@st.dialog("Novo Agendamento")
def modal_agendamento():
    dados = st.session_state.dados_agendamento
    if not dados: return

    sala_padrao = dados['sala']
    data_sugerida = dados['dia']
    hora_int = dados['hora']

    st.markdown(f"### {data_sugerida.strftime('%d/%m/%Y')} às {hora_int:02d}:00")
    config_precos = get_config_precos()
    
    modo = st.radio("Tipo", ["Por Hora", "Por Período"], horizontal=True)
    horarios = []
    valor = 0.0
    
    if modo == "Por Hora":
        horarios = [(f"{hora_int:02d}:00", f"{hora_int+1:02d}:00")]
        valor = config_precos['preco_hora']
        st.info(f"Valor: R$ {valor:.2f}")
    else:
        if 7 <= hora_int < 12: p, ini, fim, v = "Manhã", 7, 12, config_precos['preco_manha']
        elif 13 <= hora_int < 18: p, ini, fim, v = "Tarde", 13, 18, config_precos['preco_tarde']
        elif 18 <= hora_int < 22: p, ini, fim, v = "Noite", 18, 22, config_precos['preco_noite']
        else: p, ini, fim, v = "Diária", 7, 22, config_precos['preco_diaria']
        
        st.write(f"Período: **{p}**")
        st.info(f"Valor: R$ {v:.2f}")
        valor = v
        for h in range(ini, fim): horarios.append((f"{h:02d}:00", f"{h+1:02d}:00"))
    
    repetir = st.checkbox("Repetir por 4 semanas")
    
    if st.button("Confirmar Reserva", type="primary", use_container_width=True):
        user = st.session_state.user
        nm = resolver_nome(user.email, user.user_metadata.get('nome'))
        agora = get_agora_br()
        
        try:
            dias = [data_sugerida]
            if repetir:
                for k in range(1, 4): dias.append(data_sugerida + timedelta(days=7*k))
            
            inserts = []
            for d in dias:
                if d.weekday() == 6: continue
                for h_ini, h_fim in horarios:
                    dt_chk = datetime.datetime.combine(d, datetime.datetime.strptime(h_ini, "%H:%M").time())
                    if dt_chk < agora: st.error("Horário passado."); return
                    
                    chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(d)).eq("hora_inicio", f"{h_ini}:00").neq("status", "cancelada").execute()
                    if chk.data: st.error(f"Ocupado em {d.day}/{d.month} as {h_ini}"); return
                    
                    cobrar = valor if (h_ini, h_fim) == horarios[0] or modo == "Por Hora" else 0.0
                    inserts.append({
                        "sala_nome": sala_padrao, "data_reserva": str(d), "hora_inicio": f"{h_ini}:00", "hora_fim": f"{h_fim}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": cobrar, "status": "confirmada"
                    })
            
            if inserts:
                supabase.table("reservas").insert(inserts).execute()
                st.session_state.modal_ativo = False
                st.toast("Agendado!", icon="✅")
                time.sleep(1)
                st.rerun()
        except Exception as e: st.error(f"Erro: {e}")

# --- 7. RENDERIZADOR (GRADE CLÁSSICA COM CORREÇÃO MOBILE) ---
def render_calendar_interface(sala, is_admin_mode=False):
    c1, c2, c3 = st.columns([1, 4, 1])
    c1.button("❮", on_click=lambda: navegar('prev'), use_container_width=True)
    c3.button("❯", on_click=lambda: navegar('next'), use_container_width=True)
    
    ref = st.session_state.data_ref
    d_start = ref - timedelta(days=ref.weekday())
    mes_nome = d_start.strftime("%b").upper()
    c2.markdown(f"<div style='text-align:center; font-weight:bold; margin-top:5px'>{mes_nome} {d_start.day}</div>", unsafe_allow_html=True)

    # Dados
    reservas = []
    try:
        d_end = d_start + timedelta(days=7)
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).neq("status", "cancelada").gte("data_reserva", str(d_start)).lte("data_reserva", str(d_end)).execute()
        reservas = r.data
    except: pass
    
    mapa = {}
    for x in reservas:
        if x['data_reserva'] not in mapa: mapa[x['data_reserva']] = {}
        mapa[x['data_reserva']][x['hora_inicio']] = x

    dias = [d_start + timedelta(days=i) for i in range(7)]
    dias_sem = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]

    # 1. Cabeçalho
    cols = st.columns(8)
    cols[0].write("")
    for i, d in enumerate(dias):
        with cols[i+1]:
            bg = "#bfdbfe" if d == datetime.date.today() else "#e2e8f0"
            st.markdown(f"<div style='background:{bg}; text-align:center; border:1px solid #ccc; font-size:11px; font-weight:bold; padding:5px 0;'>{dias_sem[d.weekday()]}<br>{d.day}</div>", unsafe_allow_html=True)

    # 2. Grade
    agora = get_agora_br()
    
    for h in range(7, 22):
        row = st.columns(8)
        row[0].markdown(f"<div style='text-align:center; font-size:11px; font-weight:bold; margin-top:12px'>{h:02d}:00</div>", unsafe_allow_html=True)
        
        for i, d in enumerate(dias):
            with row[i+1]:
                d_s = str(d)
                h_s = f"{h:02d}:00:00"
                res = mapa.get(d_s, {}).get(h_s)
                
                dt_chk = datetime.datetime.combine(d, datetime.time(h, 0))
                is_past = dt_chk < (agora - timedelta(minutes=15))
                is_closed = (d.weekday() == 6) or (d.weekday() == 5 and h >= 14)
                
                cont = st.container()
                
                if res:
                    nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                    cls = "blocked" if res['status'] == 'bloqueado' else "evt-card"
                    
                    if is_admin_mode:
                        if cont.button("X", key=f"del_{res['id']}", type="primary", use_container_width=True):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute()
                            st.rerun()
                    else:
                        st.markdown(f"<div class='{cls}'>{nm}</div>", unsafe_allow_html=True)
                
                elif is_past or is_closed:
                    st.markdown("<div class='slot-past'></div>", unsafe_allow_html=True)
                else:
                    # BOTÃO CLÁSSICO - FUNCIONA SEMPRE
                    cont.button(" ", key=f"b_{d}_{h}", on_click=abrir_modal, args=(sala, d, h), use_container_width=True)

def tela_admin_master():
    # Mantendo a lógica admin simples para não quebrar o foco
    tabs = st.tabs(["Preços", "Agenda", "Bloqueios"])
    with tabs[0]:
        st.write("Configuração de Preços (Simulado)")
    with tabs[1]:
        s = st.radio("Sala Admin", ["Sala 1", "Sala 2"], horizontal=True)
        render_calendar_interface(s, True)
    with tabs[2]:
        st.write("Bloqueios")

# --- 8. MAIN (LOGIN V86 RESTAURADO) ---
def main():
    if not st.session_state.user:
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.write("") 
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='text-align:center; color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            
            # Lógica de Login/Cadastro/Recuperar
            if st.session_state.auth_mode == 'login':
                with st.form("login_form"):
                    email = st.text_input("Email")
                    senha = st.text_input("Senha", type="password")
                    if st.form_submit_button("Entrar", use_container_width=True):
                        try:
                            u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                            if u.user: 
                                st.session_state.user = u.user
                                st.session_state.is_admin = (email == "admin@admin.com.br")
                                st.rerun()
                        except: st.error("Login falhou.")
                
                c_reg, c_rec = st.columns(2)
                if c_reg.button("Criar Conta"): st.session_state.auth_mode = 'register'; st.rerun()
                if c_rec.button("Recuperar"): st.session_state.auth_mode = 'forgot'; st.rerun()

            elif st.session_state.auth_mode == 'register':
                st.markdown("### Nova Conta")
                nome = st.text_input("Nome")
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                if st.button("Cadastrar", type="primary", use_container_width=True):
                    try:
                        r = supabase.auth.sign_up({"email": email, "password": senha, "options": {"data": {"nome": nome}}})
                        if r.user: st.success("Sucesso! Faça login."); st.session_state.auth_mode = 'login'; time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
                if st.button("Voltar"): st.session_state.auth_mode = 'login'; st.rerun()
            
            elif st.session_state.auth_mode == 'forgot':
                st.markdown("### Recuperar Senha")
                email = st.text_input("Email")
                if st.button("Enviar Email", type="primary"):
                    try: supabase.auth.reset_password_email(email); st.success("Verifique seu email.")
                    except: st.error("Erro.")
                if st.button("Voltar"): st.session_state.auth_mode = 'login'; st.rerun()
        return

    # LOGADO
    if st.session_state.modal_ativo:
        modal_agendamento()

    if st.session_state.is_admin:
        if st.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        tela_admin_master()
    else:
        u = st.session_state.user
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        
        c_head, c_btn = st.columns([4, 1])
        c_head.markdown(f"### Olá, {nm}")
        if c_btn.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        
        tab1, tab2 = st.tabs(["Agenda", "Meus Agendamentos"])
        with tab1:
            sala = st.radio("Local", ["Sala 1", "Sala 2"], horizontal=True)
            render_calendar_interface(sala)
        with tab2:
            st.write("Histórico de agendamentos...")

if __name__ == "__main__":
    main()

