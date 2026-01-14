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

# --- 1. CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="centered", initial_sidebar_state="collapsed")

# Inicializa Estado
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()

NOME_DO_ARQUIVO_LOGO = "logo.png"

# --- 2. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. CSS LIMPO (APENAS ESTÉTICA) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; font-family: 'Inter', sans-serif; color: #1e293b; }
    header, footer, [data-testid="stToolbar"] { display: none !important; }
    
    /* Botões */
    div[data-testid="stForm"] button, button[kind="primary"] { 
        background: #0f766e !important; color: white !important; border: none; border-radius: 8px; 
    }
    
    /* Card de Agendamento */
    .slot-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .slot-time { font-weight: 700; color: #64748b; font-size: 16px; min-width: 60px; }
    .slot-status { flex-grow: 1; padding-left: 10px; font-size: 14px; font-weight: 600; }
    .status-free { color: #10b981; }
    .status-busy { color: #0369a1; }
    .status-blocked { color: #94a3b8; }
    
    /* Ajustes Mobile */
    @media only screen and (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
        button { min-height: 45px !important; }
    }
</style>
""", unsafe_allow_html=True)

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

def navegar(delta_dias):
    st.session_state.data_ref += timedelta(days=delta_dias)

@st.dialog("Confirmar Agendamento")
def modal_agendamento(sala_padrao, data_sugerida, hora_sugerida_int):
    st.markdown(f"### {data_sugerida.strftime('%d/%m/%Y')} às {hora_sugerida_int}:00")
    config_precos = get_config_precos()
    
    st.info(f"Sala: {sala_padrao}")
    
    opcoes = ["Hora Avulsa", "Manhã", "Tarde", "Noite"]
    modo = st.selectbox("Tipo de Reserva", opcoes)
    
    horarios_selecionados = []
    valor_final = 0.0
    
    if modo == "Hora Avulsa":
        horarios_selecionados = [(f"{hora_sugerida_int:02d}:00", f"{hora_sugerida_int+1:02d}:00")]
        valor_final = config_precos['preco_hora']
        st.write(f"Valor: **R$ {valor_final:.2f}**")
        
    elif modo == "Manhã":
        horarios_selecionados = [(f"{h:02d}:00", f"{h+1:02d}:00") for h in range(7, 12)]
        valor_final = config_precos['preco_manha']
        st.write("Horário: 07:00 às 12:00")
        
    elif modo == "Tarde":
        horarios_selecionados = [(f"{h:02d}:00", f"{h+1:02d}:00") for h in range(13, 18)]
        valor_final = config_precos['preco_tarde']
        st.write("Horário: 13:00 às 18:00")
        
    elif modo == "Noite":
        horarios_selecionados = [(f"{h:02d}:00", f"{h+1:02d}:00") for h in range(18, 22)]
        valor_final = config_precos['preco_noite']
        st.write("Horário: 18:00 às 22:00")

    st.divider()
    
    if st.button("✅ Confirmar Reserva", type="primary", use_container_width=True):
        user = st.session_state.user
        nm = resolver_nome(user.email, user.user_metadata.get('nome'))
        agora = datetime.datetime.now()
        
        try:
            inserts = []
            for h_start, h_end in horarios_selecionados:
                # Validação Básica
                dt_check = datetime.datetime.combine(data_sugerida, datetime.datetime.strptime(h_start, "%H:%M").time())
                if dt_check < agora: st.error("Horário já passou!"); return
                
                # Verifica Conflito
                chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(data_sugerida)).eq("hora_inicio", f"{h_start}:00").neq("status", "cancelada").execute()
                if chk.data: st.error(f"Horário {h_start} já ocupado!"); return
                
                # Salva apenas o valor no primeiro slot para não duplicar no financeiro
                val_to_save = valor_final if (h_start, h_end) == horarios_selecionados[0] else 0.0
                
                inserts.append({
                    "sala_nome": sala_padrao,
                    "data_reserva": str(data_sugerida),
                    "hora_inicio": f"{h_start}:00",
                    "hora_fim": f"{h_end}:00",
                    "user_id": user.id,
                    "email_profissional": user.email,
                    "nome_profissional": nm,
                    "valor_cobrado": val_to_save,
                    "status": "confirmada"
                })
            
            if inserts:
                supabase.table("reservas").insert(inserts).execute()
                st.toast("Reservado com sucesso!", icon="🎉")
                time.sleep(1)
                st.rerun()
                
        except Exception as e:
            st.error(f"Erro: {e}")

# --- 6. RENDERIZADOR DIÁRIO (VERTICAL - MOBILE FRIENDLY) ---
def render_daily_view(sala, is_admin_mode=False):
    # --- NAVEGAÇÃO DE DATAS ---
    col_nav1, col_nav2, col_nav3 = st.columns([1, 4, 1])
    col_nav1.button("◀", on_click=lambda: navegar(-1), use_container_width=True)
    col_nav3.button("▶", on_click=lambda: navegar(1), use_container_width=True)
    
    hoje = st.session_state.data_ref
    dias_sem = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    dia_str = dias_sem[hoje.weekday()]
    
    col_nav2.markdown(f"<h4 style='text-align:center; margin:0'>{hoje.day}/{hoje.month} - {dia_str}</h4>", unsafe_allow_html=True)
    st.divider()

    # --- BUSCA DADOS ---
    reservas = []
    try:
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).neq("status", "cancelada").eq("data_reserva", str(hoje)).execute()
        reservas = r.data
    except: pass
    
    mapa_dia = {}
    for x in reservas:
        mapa_dia[x['hora_inicio']] = x

    # --- RENDERIZA LISTA VERTICAL (7h as 22h) ---
    agora = datetime.datetime.now()
    
    if hoje.weekday() == 6: # Domingo
        st.warning("😴 Domingo não há atendimento.")
        return

    for h in range(7, 23):
        h_str = f"{h:02d}:00"
        h_db = f"{h:02d}:00:00"
        res = mapa_dia.get(h_db)
        
        # Estado do Slot
        dt_slot = datetime.datetime.combine(hoje, datetime.time(h, 0))
        is_past = dt_slot < agora
        is_sat_closed = (hoje.weekday() == 5 and h >= 14)
        
        # LAYOUT DA LINHA: [HORA] [STATUS] [BOTÃO]
        c1, c2, c3 = st.columns([1.2, 3, 1.5])
        
        with c1:
            st.markdown(f"<div style='margin-top:10px; font-weight:bold; color:#64748b'>{h_str}</div>", unsafe_allow_html=True)
            
        with c2:
            if res:
                nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                if res['status'] == 'bloqueado':
                    st.markdown(f"<div style='margin-top:10px; color:#94a3b8'>🔒 BLOQUEADO</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='margin-top:10px; color:#0369a1; font-weight:bold'>👤 {nm}</div>", unsafe_allow_html=True)
            elif is_past:
                st.markdown(f"<div style='margin-top:10px; color:#cbd5e1'>-- Passou --</div>", unsafe_allow_html=True)
            elif is_sat_closed:
                st.markdown(f"<div style='margin-top:10px; color:#cbd5e1'>Fechado</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='margin-top:10px; color:#10b981'>✨ Livre</div>", unsafe_allow_html=True)
                
        with c3:
            if not res and not is_past and not is_sat_closed:
                # Botão verde de ação
                if st.button("Reservar", key=f"btn_{h}", use_container_width=True):
                    modal_agendamento(sala, hoje, h)
            elif res and is_admin_mode:
                if st.button("🗑️", key=f"del_{h}"):
                    supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute()
                    st.rerun()

def tela_admin_master():
    # Simplificado para caber no código
    sala_adm = st.radio("Sala Admin", ["Sala 1", "Sala 2"], horizontal=True)
    render_daily_view(sala_adm, is_admin_mode=True)

# --- 7. MAIN ---
def main():
    if not st.session_state.user:
        # TELA DE LOGIN
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.write("") 
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='text-align:center; color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            
            with st.form("login"):
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        if u.user: 
                            st.session_state.user = u.user
                            st.session_state.is_admin = (email == "admin@admin.com.br")
                            st.rerun()
                    except: st.error("Erro login.")
            
            if st.button("Criar Conta"): st.session_state.auth_mode = 'register'; st.rerun()
        return

    # TELA PRINCIPAL
    u = st.session_state['user']
    if u is None: st.session_state.auth_mode = 'login'; st.rerun(); return

    if st.session_state.get('is_admin'):
        if st.button("Sair (Admin)"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        tela_admin_master()
    else:
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"### Olá, {nm}")
        if c2.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        
        tabs = st.tabs(["📅 Agenda", "📊 Meus Dados"])
        
        with tabs[0]:
            sala = st.radio("Local de Atendimento", ["Sala 1", "Sala 2"], horizontal=True)
            # AQUI ESTÁ A MUDANÇA CRUCIAL: VISÃO DIÁRIA VERTICAL
            render_daily_view(sala)
            
        with tabs[1]:
            st.info("Em construção: Histórico e Financeiro.")

if __name__ == "__main__":
    main()
