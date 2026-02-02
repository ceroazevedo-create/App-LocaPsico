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

# --- 2. GESTÃO DE ESTADO ---
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()

# Controle do Modal
if 'modal_ativo' not in st.session_state: st.session_state.modal_ativo = False
if 'dados_modal' not in st.session_state: st.session_state.dados_modal = {}

NOME_DO_ARQUIVO_LOGO = "logo.png"

# --- 3. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 4. CSS (CORREÇÃO DE ENCAVALAMENTO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; color: #1e293b; }
    header, footer, [data-testid="stToolbar"] { display: none !important; }
    
    div[data-testid="stForm"] button, button[kind="primary"] { 
        background: #0f766e !important; color: white !important; border: none; border-radius: 6px; 
    }

    /* === CORREÇÃO DA GRADE NO MOBILE === */
    @media only screen and (max-width: 768px) {
        
        /* 1. O Scroll Horizontal Geral */
        div[data-testid="stHorizontalBlock"]:has(.grade-container) {
            width: 100% !important;
            overflow-x: auto !important;
            white-space: nowrap !important;
            padding-bottom: 5px !important;
            display: block !important; /* Importante para o scroll funcionar */
        }
        
        /* 2. Força a largura MÍNIMA dos containers internos */
        /* Isso garante que Header e Botões tenham a mesma largura e não "encavalem" */
        .grade-row {
            min-width: 650px !important; /* Largura forçada maior que a tela */
            display: flex !important;
            flex-wrap: nowrap !important;
            gap: 0px !important;
        }

        /* 3. Colunas Individuais (Dias) */
        /* Usa flex-basis para garantir tamanho igual */
        .grade-col {
            flex: 1 0 80px !important; /* Cresce, não encolhe, base 80px */
            min-width: 80px !important;
            max-width: 80px !important;
        }

        /* 4. Coluna da Hora (Fixa e menor) */
        .time-col-wrapper {
            flex: 0 0 45px !important;
            min-width: 45px !important;
            position: sticky !important;
            left: 0 !important;
            z-index: 50 !important;
            background: #f8fafc !important;
            border-right: 1px solid #cbd5e1 !important;
        }

        /* 5. Ajuste de Fonte do Cabeçalho para não quebrar */
        .day-header {
            font-size: 10px !important; /* Fonte menor no mobile */
            line-height: 1.1 !important;
            padding: 4px 0 !important;
            height: 35px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            white-space: normal !important; /* Permite quebra de linha controlada */
        }

        /* Botões */
        .grade-row button {
            height: 40px !important;
            min-height: 40px !important;
            padding: 0 !important;
            font-size: 10px !important;
        }
    }

    /* DESKTOP (Padrão Normal) */
    @media (min-width: 769px) {
        .grade-row { display: flex; width: 100%; }
        .grade-col { flex: 1; }
        .time-col-wrapper { width: 60px; }
        .grade-row button { height: 45px !important; }
        .day-header { font-size: 12px; padding: 10px 0; }
    }

    /* ESTILOS VISUAIS COMUNS */
    .day-header {
        background: #e2e8f0; border: 1px solid #94a3b8; color: #334155; font-weight: bold;
    }
    .time-val {
        font-size: 11px; font-weight: bold; color: #64748b; 
        display: flex; align-items: center; justify-content: center; height: 100%;
    }
    .grade-row button {
        width: 100%; border-radius: 0px !important; border: 1px solid #cbd5e1 !important; margin: 0 !important;
    }
    .grade-row button:hover { border: 1px solid #000 !important; z-index: 10; }

</style>
""", unsafe_allow_html=True)

# --- 5. FUNÇÕES ---
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

def click_agendar(sala, data_obj, hora_str):
    st.session_state.dados_modal = {'sala': sala, 'data': data_obj, 'hora': hora_str}
    st.session_state.modal_ativo = True

# --- 6. MODAL ---
@st.dialog("📅 Novo Agendamento")
def modal_agendamento():
    dados = st.session_state.dados_modal
    if not dados: return

    sala_padrao = dados['sala']
    data_obj = dados['data']
    hora_str = dados['hora']
    hora_int = int(hora_str.split(':')[0])

    st.markdown(f"**Sala:** {sala_padrao}")
    st.markdown(f"**Quando:** {data_obj.strftime('%d/%m/%Y')} às {hora_str}")
    st.divider()

    config = get_config_precos()
    modo = st.radio("Tipo", ["Por Hora", "Por Período"], horizontal=True)
    slots = []
    valor = 0.0

    if modo == "Por Hora":
        slots = [(f"{hora_int:02d}:00", f"{hora_int+1:02d}:00")]
        valor = float(config['preco_hora'])
        st.metric("Valor", f"R$ {valor:.2f}")
    else:
        if 7 <= hora_int < 12: p, ini, fim, val = "Manhã", 7, 12, config['preco_manha']
        elif 13 <= hora_int < 18: p, ini, fim, val = "Tarde", 13, 18, config['preco_tarde']
        elif 18 <= hora_int < 22: p, ini, fim, val = "Noite", 18, 22, config['preco_noite']
        else: p, ini, fim, val = "Diária", 7, 22, config['preco_diaria']
        
        st.info(f"Pacote: {p}")
        st.metric("Valor", f"R$ {val:.2f}")
        valor = float(val)
        for h in range(ini, fim):
            slots.append((f"{h:02d}:00", f"{h+1:02d}:00"))

    repetir = st.checkbox("Repetir (Mensal - 4 semanas)")
    
    if st.button("Confirmar Reserva", type="primary", use_container_width=True):
        user = st.session_state.user
        nm = resolver_nome(user.email, user.user_metadata.get('nome'))
        dias = [data_obj]
        if repetir:
            for k in range(1, 4): dias.append(data_obj + timedelta(days=7*k))
            
        try:
            inserts = []
            for d in dias:
                if d.weekday() == 6: continue
                for h_ini, h_fim in slots:
                    chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(d)).eq("hora_inicio", f"{h_ini}:00").neq("status", "cancelada").execute()
                    if chk.data: st.error(f"Ocupado em {d} às {h_ini}"); return

                    cobrar = valor if (h_ini, h_fim) == slots[0] or modo == "Por Hora" else 0.0
                    inserts.append({
                        "sala_nome": sala_padrao, "data_reserva": str(d), "hora_inicio": f"{h_ini}:00", "hora_fim": f"{h_fim}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": cobrar, "status": "confirmada"
                    })
            if inserts:
                supabase.table("reservas").insert(inserts).execute()
                st.session_state.modal_ativo = False
                st.toast("Sucesso!", icon="✅"); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Erro: {e}")

# --- 7. RENDERIZADOR DA GRADE (ESTRUTURA HÍBRIDA HTML/BOTOES) ---
def render_calendar_interface(sala, is_admin_mode=False):
    # Navegação
    c1, c2, c3 = st.columns([1, 4, 1])
    c1.button("❮", on_click=lambda: navegar('prev'), use_container_width=True)
    c3.button("❯", on_click=lambda: navegar('next'), use_container_width=True)
    
    ref = st.session_state.data_ref
    start = ref - timedelta(days=ref.weekday())
    mes_nome = start.strftime("%b").upper()
    c2.markdown(f"<div style='text-align:center; font-weight:bold; margin-top:5px'>{mes_nome} {start.day}</div>", unsafe_allow_html=True)

    # Dados
    agora = get_agora_br()
    dias = [start + timedelta(days=i) for i in range(7)]
    # Cabeçalhos com quebra de linha HTML para ficar compacto
    col_headers = [f"{['SEG','TER','QUA','QUI','SEX','SAB','DOM'][d.weekday()]}\n{d.day:02d}" for d in dias]
    
    try:
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).neq("status", "cancelada").gte("data_reserva", str(start)).lte("data_reserva", str(start + timedelta(days=7))).execute()
        mapa = {f"{x['data_reserva']}|{x['hora_inicio'][:5]}": x for x in r.data}
    except: mapa = {}

    # --- INÍCIO DA GRADE ---
    # Container invisível para ativar o CSS
    st.markdown('<div class="grade-container"></div>', unsafe_allow_html=True)

    # 1. CABEÇALHO DA TABELA
    # Usamos st.columns com as classes CSS aplicadas via markdown wrapper ou estrutura nativa
    # O truque aqui é que o st.columns nativo vai ser manipulado pelo CSS .grade-row
    
    # Header Row
    with st.container():
        # HTML PURO PARA O HEADER PARA GARANTIR ALINHAMENTO
        # Isso evita que o st.columns adicione gaps estranhos no header
        html_header = """
        <div class="grade-row">
            <div class="time-col-wrapper" style="background:#f1f5f9; border-bottom:1px solid #94a3b8;"></div>
        """
        for h_text in col_headers:
            html_header += f'<div class="grade-col"><div class="day-header">{h_text.replace(chr(10), "<br>")}</div></div>'
        html_header += "</div>"
        st.markdown(html_header, unsafe_allow_html=True)

    # 2. LINHAS DE HORA (BOTOES REAIS)
    for h in range(7, 22):
        row_cols = st.columns([0.6] + [1]*7) # A proporção não importa tanto pois o CSS força width
        
        # Coluna da Hora (HTML Puro para alinhar com o header)
        with row_cols[0]:
            st.markdown(f"""<div class="time-col-wrapper"><div class="time-val">{h:02d}:00</div></div>""", unsafe_allow_html=True)
        
        h_str = f"{h:02d}:00"
        
        # Colunas dos Dias (Botões)
        for i, d in enumerate(dias):
            k = f"{d}|{h_str}"
            res = mapa.get(k)
            
            dt_chk = datetime.datetime.combine(d, datetime.time(h, 0))
            is_past = dt_chk < (agora - timedelta(minutes=15))
            is_closed = (d.weekday() == 6) or (d.weekday() == 5 and h >= 14)
            
            label = " "
            tipo = "secondary"
            disabled = False
            
            if res:
                nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                label = "🔒" if res['status'] == 'bloqueado' else nm
                tipo = "primary" # Vermelho
                if not is_admin_mode: disabled = True
            elif is_past or is_closed:
                label = "•"
                disabled = True
            
            # Aqui aplicamos o wrapper para o CSS pegar
            with row_cols[i+1]:
                # Injetamos uma div wrapper para o CSS "grade-col" pegar
                st.markdown('<div class="grade-col" style="height:40px; margin:0; padding:0;">', unsafe_allow_html=True)
                if res and is_admin_mode:
                    if st.button("X", key=f"del_{d}_{h}", type="primary", use_container_width=True):
                        supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute()
                        st.rerun()
                elif res:
                    st.button(label, key=f"occ_{d}_{h}", type="primary", disabled=True, use_container_width=True)
                else:
                    st.button(" ", key=f"btn_{d}_{h}", type="secondary", disabled=disabled, use_container_width=True, on_click=click_agendar, args=(sala, d, h_str))
                st.markdown('</div>', unsafe_allow_html=True)

# --- 8. MAIN (LOGIN RESTAURADO) ---
def main():
    if not st.session_state.user:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.write("") 
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='text-align:center; color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            
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
                if c_rec.button("Esqueci Senha"): st.session_state.auth_mode = 'forgot'; st.rerun()

            elif st.session_state.auth_mode == 'register':
                st.markdown("### Nova Conta")
                nome = st.text_input("Nome Completo")
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

    # MODAL
    if st.session_state.modal_ativo:
        modal_agendamento()

    # APP
    if st.session_state.get('is_admin'):
        c_head, c_btn = st.columns([5, 1])
        c_head.markdown("### Painel Admin")
        if c_btn.button("Sair"): supabase.auth.sign_out(); st.session_state.user = None; st.rerun()
        st.divider()
        # (Conteúdo Admin Simplificado para caber, use o do código anterior se precisar de tudo)
        st.info("Painel administrativo carregado.") 
    else:
        u = st.session_state.user
        nm = resolver_nome(u.email, u.user_metadata.get('nome'))
        
        c_head, c_btn = st.columns([4, 1])
        c_head.markdown(f"### Olá, {nm}")
        if c_btn.button("Sair"): supabase.auth.sign_out(); st.session_state.user = None; st.rerun()
        
        tab1, tab2 = st.tabs(["📅 Agenda", "📊 Meus Agendamentos"])
        
        with tab1:
            sala = st.radio("Local", ["Sala 1", "Sala 2"], horizontal=True)
            render_calendar_interface(sala)
            
        with tab2:
            st.markdown("### Histórico")
            try:
                ini = get_agora_br().date().replace(day=1)
                r = supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").gte("data_reserva", str(ini)).order("data_reserva").execute()
                for row in r.data:
                    with st.container():
                        c1, c2 = st.columns([3,1])
                        c1.info(f"{row['data_reserva']} - {row['hora_inicio'][:5]} ({row['sala_nome']})")
                        if c2.button("Cancelar", key=f"c_{row['id']}"):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                            st.rerun()
            except: pass

if __name__ == "__main__":
    main()



