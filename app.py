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

NOME_DO_ARQUIVO_LOGO = "logo.png"

# --- 2. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. CSS "MATADOR" (GRID RÍGIDO + DUAL VIEW) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; font-family: 'Inter', sans-serif; color: #1e293b; }
    .block-container { padding-top: 1rem !important; max-width: 100% !important; padding-left: 5px !important; padding-right: 5px !important;}

    /* ================================================================= */
    /* 🏗️ LAYOUT GRID RÍGIDO (FORCE 7 COLUMNS)                           */
    /* ================================================================= */
    
    /* Força o container das colunas a usar GRID em vez de FLEX */
    div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: 0.6fr repeat(7, 1fr) !important; /* 1 col hora + 7 dias */
        gap: 2px !important;
        overflow-x: hidden !important; /* Sem scroll, força caber */
        align-items: start !important;
    }
    
    /* Garante que as colunas obedeçam o Grid */
    div[data-testid="column"] {
        width: 100% !important;
        min-width: 0 !important; /* Permite encolher muito */
        flex: unset !important;
        padding: 0 !important;
    }

    /* ================================================================= */
    /* 📱 DUAL RENDERING SYSTEM (DESKTOP VS MOBILE VIEW)                 */
    /* ================================================================= */

    /* Classes Visuais */
    .desktop-view { display: block; }
    .mobile-view { display: none; }
    
    /* Estilo do Card Desktop */
    .evt-card-desktop {
        background: #e0f2fe; border-left: 3px solid #0284c7; color: #0369a1;
        padding: 4px; font-size: 11px; font-weight: 600; border-radius: 4px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        height: 42px; line-height: 1.2;
    }

    /* Estilo do Indicador Mobile (Pílula) */
    .evt-indicator-mobile {
        height: 42px; width: 100%;
        background-color: #0ea5e9; /* Azul forte */
        border-radius: 3px;
        display: flex; align-items: center; justify-content: center;
        color: white; font-weight: bold; font-size: 10px;
    }
    .evt-blocked-mobile {
        height: 42px; width: 100%;
        background-color: #64748b; /* Cinza */
        border-radius: 3px;
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 8px;
    }

    /* --- MEDIA QUERY CRÍTICA (< 768px) --- */
    @media (max-width: 768px) {
        /* Inverte a visibilidade */
        .desktop-view { display: none !important; }
        .mobile-view { display: block !important; }
        
        /* Ajusta tipografia do cabeçalho */
        .day-name { font-size: 8px !important; text-transform: uppercase; color: #94a3b8; }
        .day-num { font-size: 14px !important; font-weight: 700; }
        
        /* Coluna da hora bem pequena */
        .time-label { font-size: 9px !important; margin-top: 15px; }
        
        /* Botões do Streamlit ficam invisíveis mas clicáveis ou pequenos */
        div[data-testid="stVerticalBlock"] button[kind="secondary"] {
            border: 1px dashed #e2e8f0 !important;
            height: 42px !important;
        }
    }

    /* Estilos Gerais */
    .time-label { text-align: center; font-weight: 600; color: #64748b; font-size: 11px; padding-top: 12px; }
    .header-box { text-align: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; margin-bottom: 5px; }
    .day-num { font-size: 18px; font-weight: 700; color: #1e293b; }
    .today-hl .day-num { color: #0284c7; }
    
    /* Remove tralha do Streamlit */
    header {display: none;} footer {display: none;}
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

def navegar(direcao):
    if direcao == 'prev': st.session_state.data_ref -= timedelta(days=7)
    else: st.session_state.data_ref += timedelta(days=7)

@st.dialog("Agendar")
def modal_agendamento(sala_padrao, data_sugerida, hora_sugerida_int):
    st.markdown(f"##### {data_sugerida.strftime('%d/%m')} às {hora_sugerida_int}h")
    config_precos = get_config_precos()
    modo = st.radio("Tipo", ["Hora", "Período"], horizontal=True)
    
    horarios_selecionados = []
    valor_final = 0.0
    
    if modo == "Hora":
        lista_horas = [f"{h:02d}:00" for h in range(7, 22)]
        default_idx = max(0, hora_sugerida_int - 7)
        if default_idx >= len(lista_horas): default_idx = 0
        
        hr = st.selectbox("Início", lista_horas, index=default_idx)
        if hr:
            horarios_selecionados = [(hr, f"{int(hr[:2])+1:02d}:00")]
            valor_final = config_precos['preco_hora']
    else:
        # Período simplificado
        p_opt = {"Manhã (07-12)": (7,12, config_precos['preco_manha']), "Tarde (13-18)": (13,18, config_precos['preco_tarde'])}
        sel = st.selectbox("Período", list(p_opt.keys()))
        start, end, price = p_opt[sel]
        valor_final = price
        for h in range(start, end): horarios_selecionados.append((f"{h:02d}:00", f"{h+1:02d}:00"))

    if st.button("Confirmar", type="primary", use_container_width=True):
        user = st.session_state.user
        nm = resolver_nome(user.email, user.user_metadata.get('nome'))
        try:
            inserts = []
            for h_start, h_end in horarios_selecionados:
                # Validação básica
                chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(data_sugerida)).eq("hora_inicio", f"{h_start}:00").neq("status", "cancelada").execute()
                if chk.data: st.error("Ocupado"); return
                
                inserts.append({
                    "sala_nome": sala_padrao, "data_reserva": str(data_sugerida), "hora_inicio": f"{h_start}:00", "hora_fim": f"{h_end}:00",
                    "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": valor_final if h_start == horarios_selecionados[0][0] else 0, "status": "confirmada"
                })
            supabase.table("reservas").insert(inserts).execute()
            st.rerun()
        except: st.error("Erro")

def render_calendar_rigid(sala, is_admin_mode=False):
    # --- CONTROLES SIMPLES ---
    c1, c2, c3 = st.columns([1, 4, 1])
    c1.button("❮", on_click=lambda: navegar('prev'), use_container_width=True)
    c3.button("❯", on_click=lambda: navegar('next'), use_container_width=True)
    
    ref = st.session_state.data_ref
    d_start = ref - timedelta(days=ref.weekday())
    mes_nome = d_start.strftime("%b").upper()
    c2.markdown(f"<div style='text-align:center; font-weight:bold; margin-top:5px'>{mes_nome} {d_start.year}</div>", unsafe_allow_html=True)

    # --- DADOS ---
    d_end = d_start + timedelta(days=6)
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

    # --- RENDERIZAÇÃO DO GRID (A MÁGICA) ---
    dias_visiveis = [d_start + timedelta(days=i) for i in range(7)]
    dias_sem = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    
    # 1. Cabeçalho (8 colunas: 1 hora + 7 dias)
    # O CSS vai forçar isso a ser um GRID
    cols = st.columns(8) 
    cols[0].write("") # Espaço hora
    
    for i, d in enumerate(dias_visiveis):
        with cols[i+1]:
            is_hj = (d == datetime.date.today())
            cls_hj = "today-hl" if is_hj else ""
            st.markdown(f"""
            <div class='header-box {cls_hj}'>
                <div class='day-name'>{dias_sem[d.weekday()]}</div>
                <div class='day-num'>{d.day}</div>
            </div>""", unsafe_allow_html=True)

    # 2. Linhas (Horas)
    for h in range(7, 22):
        row = st.columns(8) # Isso vira GRID no CSS
        
        # Hora
        row[0].markdown(f"<div class='time-label'>{h}h</div>", unsafe_allow_html=True)
        
        # Dias
        for i, d in enumerate(dias_visiveis):
            with row[i+1]:
                d_s = str(d)
                h_s = f"{h:02d}:00:00"
                res = mapa.get(d_s, {}).get(h_s)
                
                # HTML DUAL VIEW
                html_content = ""
                
                if res:
                    nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                    initial = nm[0].upper() if nm else "?"
                    
                    if res['status'] == 'bloqueado':
                        html_content = f"""
                        <div class='desktop-view admin-blocked'>BLOQUEADO</div>
                        <div class='mobile-view evt-blocked-mobile'>X</div>
                        """
                    else:
                        html_content = f"""
                        <div class='desktop-view evt-card-desktop' title='{nm}'>{nm}</div>
                        <div class='mobile-view evt-indicator-mobile'>{initial}</div>
                        """
                        
                    # Renderiza o visual
                    st.markdown(html_content, unsafe_allow_html=True)
                    
                    # Botão invisível para ação (admin deletar)
                    if is_admin_mode:
                        if st.button("x", key=f"del_{res['id']}", help="Remover"):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute()
                            st.rerun()
                
                else:
                    # Slot Livre
                    # No Desktop: Mostra botão transparente. No Mobile: Mostra botão transparente.
                    # O CSS cuida das bordas.
                    if not is_admin_mode:
                        if st.button(" ", key=f"add_{d}_{h}", type="secondary", use_container_width=True):
                            modal_agendamento(sala, d, h)
                    else:
                        st.markdown("<div style='height:40px; border-right:1px solid #f1f5f9'></div>", unsafe_allow_html=True)

def main():
    if not st.session_state.user:
        # TELA DE LOGIN MANTIDA E COMPACTA
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.write("")
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            
            with st.form("login"):
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        if u.user: st.session_state.user = u.user; st.session_state.is_admin = (email == "admin@admin.com.br"); st.rerun()
                    except: st.error("Erro")
        return

    # TELA PRINCIPAL
    if st.session_state.is_admin:
        st.info("Painel Admin")
        sala = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
        render_calendar_rigid(sala, is_admin_mode=True)
        if st.button("Sair"): st.session_state.user = None; st.rerun()
    else:
        nm = resolver_nome(st.session_state.user.email, st.session_state.user.user_metadata.get('nome'))
        c_h, c_b = st.columns([4,1])
        c_h.markdown(f"**Olá, {nm}**")
        if c_b.button("Sair"): st.session_state.user = None; st.rerun()
        
        sala = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True, label_visibility="collapsed")
        render_calendar_rigid(sala, is_admin_mode=False)

if __name__ == "__main__":
    main()
