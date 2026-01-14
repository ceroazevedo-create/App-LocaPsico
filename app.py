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

# --- 3. CSS "GOOGLE CALENDAR DENSITY" (O SEGREDO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; font-family: 'Inter', sans-serif; color: #1e293b; }
    .block-container { padding-top: 1rem !important; max-width: 100% !important; padding-left: 5px; padding-right: 5px; }

    /* ============================================================ */
    /* 📱 MOBILE OVERRIDE - FORÇAR GRADE LADO A LADO (< 768px)      */
    /* ============================================================ */
    
    @media only screen and (max-width: 768px) {
        
        /* 1. CONTAINER PAI DAS COLUNAS: PROIBIDO EMPILHAR */
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-wrap: nowrap !important; /* A Mágica: Obriga ficar na linha */
            overflow-x: hidden !important; /* Sem scroll, espreme para caber */
            gap: 1px !important;
        }

        /* 2. AS COLUNAS (DIAS): LARGURA MÍNIMA ZERO */
        div[data-testid="column"] {
            flex: 1 1 0 !important; /* Cresce e encolhe igualmente */
            min-width: 0 !important; /* Permite ficar muito pequeno */
            width: auto !important;
            padding: 0 1px !important;
        }

        /* 3. COLUNA DA HORA (EIXO Y): ESCONDIDA OU MINÚSCULA */
        /* Opção: Esconder a hora no mobile para dar espaço aos dias */
        div[data-testid="column"]:first-child {
            display: none !important; 
        }

        /* 4. VISIBILIDADE DOS EVENTOS (DUAL RENDERING) */
        .evt-desktop { display: none !important; }
        .evt-mobile { display: block !important; }

        /* 5. TIPOGRAFIA MICROSCÓPICA */
        .day-header-name { font-size: 8px !important; text-transform: uppercase; }
        .day-header-num { font-size: 12px !important; font-weight: 700; }
        
        /* Botões de Agendar (Slot Livre) */
        div[data-testid="stVerticalBlock"] button[kind="secondary"] {
            padding: 0 !important;
            height: 35px !important;
            min-height: 35px !important;
            border: 1px solid #f1f5f9 !important;
        }
    }

    /* ============================================================ */
    /* 💻 DESKTOP RULES (> 768px)                                   */
    /* ============================================================ */
    @media only screen and (min-width: 769px) {
        .evt-desktop { display: block !important; }
        .evt-mobile { display: none !important; }
        
        div[data-testid="column"]:first-child {
            display: block !important; /* Mostra hora no PC */
            min-width: 50px !important;
        }
    }

    /* --- ESTILOS GERAIS --- */
    
    /* Login Clean */
    div[data-testid="column"]:nth-of-type(2) > div { background-color: #ffffff; padding: 30px; border-radius: 12px; border: 1px solid #e2e8f0; }
    
    /* Eventos */
    .evt-desktop {
        background-color: #e0f2fe; border-left: 3px solid #0284c7; color: #0369a1;
        font-size: 10px; font-weight: 600; padding: 4px; border-radius: 4px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        height: 40px; line-height: 1.2; margin-bottom: 2px;
    }
    
    .evt-mobile {
        background-color: #0ea5e9; /* Azul sólido */
        height: 35px; width: 100%;
        border-radius: 2px;
        margin-bottom: 2px;
    }
    
    .evt-blocked-mobile { background-color: #64748b; height: 35px; border-radius: 2px; }
    .evt-blocked-desktop { background: #334155; color: white; font-size: 10px; padding: 4px; border-radius: 4px; height: 40px; text-align: center; }

    /* Headers */
    .day-header-box { text-align: center; border-bottom: 1px solid #e2e8f0; margin-bottom: 5px; padding-bottom: 5px; }
    .day-header-name { font-size: 11px; font-weight: 600; color: #64748b; }
    .day-header-num { font-size: 20px; font-weight: 700; color: #1e293b; }
    .today-hl { color: #0284c7; }

    /* Botões Padrão */
    div[data-testid="stForm"] button, button[kind="primary"] { background: #0f766e !important; color: white !important; border: none; height: 45px; }
    .stTextInput input { background: #f8fafc; border: 1px solid #e2e8f0; height: 45px; }
    
    /* Remover tralha nativa */
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
    delta = 7 
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
        st.info(f"Valor: R$ {dados_p['price']:.2f}")
        for h in range(dados_p['start'], dados_p['end']):
            horarios_selecionados.append((f"{h:02d}:00", f"{h+1:02d}:00"))
        valor_final = dados_p['price']
    
    st.write("")
    is_recurring = st.checkbox("Repetir por 4 semanas")
    if st.button("Confirmar", type="primary", use_container_width=True):
        if not horarios_selecionados: st.error("Erro."); return
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
                    if d_res.weekday() == 5 and int(h_start[:2]) >= 14: st.error("Sábado fecha 14h."); return
                    chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(d_res)).eq("hora_inicio", f"{h_start}:00").neq("status", "cancelada").execute()
                    if chk.data: st.error("Ocupado."); return 
                    val_to_save = valor_final if (h_start, h_end) == horarios_selecionados[0] or modo == "Por Hora" else 0.0
                    inserts.append({
                        "sala_nome": sala_padrao, "data_reserva": str(d_res), "hora_inicio": f"{h_start}:00", "hora_fim": f"{h_end}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": val_to_save, "status": "confirmada"
                    })
            if inserts:
                supabase.table("reservas").insert(inserts).execute()
                st.toast("Sucesso!", icon="✅"); time.sleep(1); st.rerun()
        except: st.error("Erro.")

def render_calendar(sala, is_admin_mode=False):
    # NAVEGAÇÃO
    c1, c2, c3 = st.columns([1, 4, 1])
    c1.button("❮", on_click=lambda: navegar('prev'), use_container_width=True)
    c3.button("❯", on_click=lambda: navegar('next'), use_container_width=True)
    
    ref = st.session_state.data_ref
    d_start = ref - timedelta(days=ref.weekday())
    d_end = d_start + timedelta(days=6)
    mes_nome = d_start.strftime("%b").upper()
    c2.markdown(f"<div style='text-align:center; font-weight:bold; margin-top:5px'>{mes_nome} {d_start.day}-{d_end.day}</div>", unsafe_allow_html=True)

    # DADOS
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

    # GRADE (8 Colunas: 1 Hora + 7 Dias)
    # CSS vai forçar: No mobile, col 0 some, cols 1-7 ficam lado a lado espremidas
    dias_visiveis = [d_start + timedelta(days=i) for i in range(7)]
    dias_sem = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    
    cols = st.columns([0.3, 1, 1, 1, 1, 1, 1, 1])
    cols[0].write("") # Espaço hora (some no mobile)
    
    for i, d in enumerate(dias_visiveis):
        with cols[i+1]:
            is_hj = (d == datetime.date.today())
            cls_hj = "today-hl" if is_hj else ""
            st.markdown(f"""
            <div class='day-header-box'>
                <div class='day-header-name'>{dias_sem[d.weekday()]}</div>
                <div class='day-header-num {cls_hj}'>{d.day}</div>
            </div>""", unsafe_allow_html=True)

    # LINHAS DE HORÁRIO
    for h in range(7, 22):
        row = st.columns([0.3, 1, 1, 1, 1, 1, 1, 1])
        
        # Hora (some no mobile via CSS)
        row[0].markdown(f"<div style='font-size:10px; text-align:right; margin-top:10px; color:#94a3b8'>{h:02d}:00</div>", unsafe_allow_html=True)
        
        for i, d in enumerate(dias_visiveis):
            with row[i+1]:
                d_s = str(d)
                h_s = f"{h:02d}:00:00"
                res = mapa.get(d_s, {}).get(h_s)
                
                # RECURSO HTML DUPLO (O Segredo)
                if res:
                    nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                    if res['status'] == 'bloqueado':
                        st.markdown(f"""
                        <div class='evt-desktop evt-blocked-desktop'>BLOQUEADO</div>
                        <div class='evt-mobile evt-blocked-mobile'></div>
                        """, unsafe_allow_html=True)
                        if is_admin_mode:
                             if st.button("x", key=f"del_{res['id']}"): supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                    else:
                        st.markdown(f"""
                        <div class='evt-desktop' title='{nm}'>{nm}</div>
                        <div class='evt-mobile' title='{nm}'></div>
                        """, unsafe_allow_html=True)
                        if is_admin_mode:
                             if st.button("x", key=f"del_{res['id']}"): supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                else:
                    # Slot Livre
                    # No Mobile, o botão fica quase invisível mas clicável, ocupando o espaço
                    if not is_admin_mode:
                        if st.button(" ", key=f"add_{d}_{h}", type="secondary", use_container_width=True):
                            modal_agendamento(sala, d, h)
                    else:
                        st.markdown("<div style='height:40px; border-right:1px solid #f1f5f9'></div>", unsafe_allow_html=True)

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
    with tabs[3]: pass
    with tabs[4]: pass

# --- 7. MAIN ---
def main():
    if not st.session_state.user:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.write("") 
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='color:#0d9488; text-align:center'>LocaPsico</h1>", unsafe_allow_html=True)
            
            if st.session_state.auth_mode == 'login':
                with st.form("login"):
                    email = st.text_input("Email")
                    senha = st.text_input("Senha", type="password")
                    if st.form_submit_button("Entrar", use_container_width=True):
                        try:
                            u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                            if u.user: st.session_state.user = u.user; st.session_state.is_admin = (email == "admin@admin.com.br"); st.rerun()
                        except: st.error("Erro")
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
                                c1.markdown(f"**{row['data_reserva']}** às **{row['hora_inicio'][:5]}** - {row['sala_nome']}")
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
