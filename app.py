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

# --- 3. CSS "HACK" PARA SCROLL HORIZONTAL (MOBILE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; color: #1e293b; }
    .block-container { padding-top: 1rem !important; max-width: 1100px; }

    /* ============================================================ */
    /* 🚀 HACK DE SCROLL HORIZONTAL PARA MOBILE (Mobile Grid Fix)   */
    /* ============================================================ */
    
    @media only screen and (max-width: 768px) {
        
        /* 1. Alvo: Container que segura as colunas (stHorizontalBlock) */
        /* Usamos :has() para aplicar SÓ quando houver 7 colunas (Calendário) */
        /* Fallback: Aplica a todos se o navegador não suportar :has, o que é seguro */
        
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-wrap: nowrap !important;       /* OBRIGATÓRIO: Proíbe quebra de linha */
            overflow-x: auto !important;        /* OBRIGATÓRIO: Habilita scroll lateral */
            white-space: nowrap !important;     /* Mantém integridade */
            padding-bottom: 5px;                /* Espaço para o dedo não cobrir conteúdo */
            align-items: stretch !important;    /* Altura igual para todas */
            -webkit-overflow-scrolling: touch;  /* Scroll suave no iPhone */
        }

        /* 2. Alvo: As Colunas Individuais (column) */
        div[data-testid="column"] {
            flex: 0 0 auto !important;          /* Não encolher, não crescer, tamanho fixo */
            width: auto !important;
            min-width: 140px !important;        /* LARGURA MÍNIMA: Garante que o dia não esmague */
        }
        
        /* 3. Ajuste Fino: Coluna da Hora (A primeira da esquerda) */
        /* Deixamos ela um pouco menor e fixamos ela na esquerda (Sticky) se quiser efeito Excel */
        div[data-testid="column"]:first-child {
            min-width: 50px !important;
            position: sticky;
            left: 0;
            background-color: #f8fafc; /* Cor de fundo para cobrir ao rolar */
            z-index: 10;
            border-right: 1px solid #e2e8f0;
        }
    }
    /* ============================================================ */

    /* Resto do Design (Mantido da V86 Estável) */
    div[data-testid="column"]:nth-of-type(2) > div { background-color: #ffffff; padding: 30px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #f1f5f9; }
    div[data-testid="stImage"] { display: flex; justify-content: center; margin-bottom: 20px; }
    div[data-testid="stImage"] > img { max-height: 100px; object-fit: contain; }
    h1 { font-size: 24px; font-weight: 700; color: #0f172a; text-align: center; margin-bottom: 10px; }
    
    /* Botões e Inputs */
    .stTextInput input { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; height: 45px; }
    div[data-testid="stForm"] button, button[kind="primary"] { background: linear-gradient(180deg, #0f766e 0%, #0d9488 100%) !important; border: none !important; height: 45px !important; font-weight: 600 !important; border-radius: 8px !important; color: white !important; }
    button[kind="secondary"] { background-color: white !important; border: 1px solid #cbd5e1 !important; color: #475569 !important; border-radius: 8px !important; height: 45px !important; }
    
    /* Grade Calendário */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        background-color: #f0fdf4 !important; border: 1px solid #bbf7d0 !important; color: #15803d !important;
        font-size: 11px !important; font-weight: 600; height: 40px; min-height: 40px; border-radius: 6px; width: 100%;
    }
    
    .evt-chip { background: white; border-left: 4px solid #0d9488; color: #0f766e; font-size: 10px; font-weight: 600; padding: 4px; border-radius: 4px; display: flex; align-items: center; justify-content: center; height: 40px; }
    .admin-blocked { background: #334155; color: #cbd5e1; font-size: 10px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 4px; }
    .blocked-slot { background-color: #fef2f2; height: 40px; border-radius: 6px; opacity: 0.6; }
    
    /* Header Escondido */
    header[data-testid="stHeader"] { display: none !important; }
    
    /* Hora lateral */
    .time-label { font-size: 10px; color: #64748b; font-weight: bold; text-align: center; margin-top: 12px; }
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
    st.markdown(f"### {data_sugerida.strftime('%d/%m/%Y')}")
    config_precos = get_config_precos()
    modo = st.radio("Tipo", ["Por Hora", "Por Período"], horizontal=True)
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
            if str_h in lista_horas: idx_padrao = lista_horas.index(str_h)
        hr = st.selectbox("Início", lista_horas, index=idx_padrao, disabled=(len(lista_horas)==0))
        if hr:
            horarios_selecionados = [(hr, f"{int(hr[:2])+1:02d}:00")]
            valor_final = config_precos['preco_hora']
    else:
        opcoes_periodo = {
            "Manhã (07h-12h)": {"start": 7, "end": 12, "price": config_precos['preco_manha']},
            "Tarde (13h-18h)": {"start": 13, "end": 18, "price": config_precos['preco_tarde']},
            "Noite (18h-22h)": {"start": 18, "end": 22, "price": config_precos['preco_noite']},
            "Diária (07h-22h)": {"start": 7, "end": 22, "price": config_precos['preco_diaria']}
        }
        sel_periodo = st.selectbox("Período", list(opcoes_periodo.keys()))
        dados_p = opcoes_periodo[sel_periodo]
        st.info(f"R$ {dados_p['price']:.2f}")
        for h in range(dados_p['start'], dados_p['end']):
            horarios_selecionados.append((f"{h:02d}:00", f"{h+1:02d}:00"))
        valor_final = dados_p['price']
    st.markdown("---")
    is_recurring = st.checkbox("🔄 Repetir 4 semanas")
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
                    val_to_save = 0.0
                    if (h_start, h_end) == horarios_selecionados[0]: val_to_save = valor_final
                    elif modo == "Por Hora": val_to_save = valor_final 
                    inserts.append({
                        "sala_nome": sala_padrao, "data_reserva": str(d_res), "hora_inicio": f"{h_start}:00", "hora_fim": f"{h_end}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": val_to_save, "status": "confirmada"
                    })
            if inserts:
                supabase.table("reservas").insert(inserts).execute()
                st.toast("Confirmado!", icon="✅"); time.sleep(1); st.rerun()
        except: st.error("Erro técnico.")

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
        # (Lógica do mês simplificada para focar na semana, mas aplicando o mesmo grid se necessário)
        ano, mes = ref.year, ref.month
        st.markdown(f"<div style='text-align:center; font-weight:800; color:#334155; margin:10px 0'>{mes_str} {ano}</div>", unsafe_allow_html=True)
        # ... (implementação padrão do mês)
        
    else:
        # LOGICA DA SEMANA COM SCROLL HORIZONTAL
        if mode == 'SEMANA':
            d_start = ref - timedelta(days=ref.weekday())
            d_end = d_start + timedelta(days=6)
            lbl = f"{d_start.day} - {d_end.day} {mes_str}"
            num_dias = 7
        else:
            d_start = ref
            d_end = ref
            lbl = f"{ref.day} de {mes_str}"
            num_dias = 1
            
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

        # 1. CABEÇALHO DOS DIAS
        # Usa st.columns normal, mas o CSS vai forçar a não quebrar no mobile
        visiveis = [d_start + timedelta(days=i) for i in range(num_dias)]
        
        # Coluna da Hora (Fake no header para alinhar) + Colunas de Dias
        ratios = [0.3] + [1]*num_days 
        cols = st.columns(ratios)
        cols[0].write("") # Espaço vazio acima da hora
        
        d_n = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
        for i, d in enumerate(visiveis):
            wd = d.weekday()
            # Mostra cabeçalho centralizado
            cols[i+1].markdown(f"<div style='text-align:center; border-bottom:2px solid #e2e8f0; padding-bottom:5px'><div style='font-size:10px; font-weight:bold; color:#64748b'>{d_n[wd]}</div><div style='font-size:16px; font-weight:bold; color:#1e293b'>{d.day}</div></div>", unsafe_allow_html=True)

        # 2. LINHAS DE HORÁRIO
        for h in range(7, 22):
            row_cols = st.columns(ratios)
            
            # Coluna 0: A Hora Fixa
            with row_cols[0]:
                st.markdown(f"<div class='time-label'>{h}h</div>", unsafe_allow_html=True)
                
            # Colunas 1 a 7: Os Slots
            for i, d in enumerate(visiveis):
                with row_cols[i+1]:
                    d_s = str(d)
                    h_s = f"{h:02d}:00:00"
                    res = mapa.get(d_s, {}).get(h_s)
                    
                    cont = st.container()
                    dt_slot = datetime.datetime.combine(d, datetime.time(h, 0))
                    agora = datetime.datetime.now()
                    is_sunday = d.weekday() == 6
                    is_sat_closed = (d.weekday() == 5 and h >= 14)
                    is_past = dt_slot < agora
                    
                    if res:
                        if res['status'] == 'bloqueado':
                            cont.markdown(f"<div class='admin-blocked'>⛔</div>", unsafe_allow_html=True)
                            if is_admin_mode:
                                 if cont.button("🗑️", key=f"rm_{res['id']}"): supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                        else:
                            nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                            if is_admin_mode:
                                c1, c2 = cont.columns([3,1])
                                c1.markdown(f"<div class='evt-chip'>{nm}</div>", unsafe_allow_html=True)
                                if c2.button("x", key=f"del_{res['id']}"): supabase.table("reservas").update({"status": "cancelada"}).eq("id", res['id']).execute(); st.rerun()
                            else:
                                cont.markdown(f"<div class='evt-chip'>{nm}</div>", unsafe_allow_html=True)
                    
                    elif is_sunday or is_sat_closed or is_past:
                        cont.markdown("<div class='blocked-slot'></div>", unsafe_allow_html=True)
                    
                    else:
                        # Botão Livre
                        if not is_admin_mode:
                            if cont.button("Livre", key=f"add_{d}_{h}", type="secondary", use_container_width=True):
                                modal_agendamento(sala, d, h)
                        else:
                            cont.markdown("<div style='height:40px; border-left:1px dashed #e2e8f0'></div>", unsafe_allow_html=True)

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
        if st.button("Bloquear", type="primary"):
            salas = ["Sala 1", "Sala 2"] if sala_block == "Ambas" else [sala_block]
            for s in salas:
                supabase.table("reservas").update({"status": "cancelada"}).eq("sala_nome", s).eq("data_reserva", str(dt_block)).neq("status", "cancelada").execute()
                inserts = [{"sala_nome": s, "data_reserva": str(dt_block), "hora_inicio": f"{h:02d}:00", "hora_fim": f"{h+1:02d}:00", "user_id": st.session_state.user.id, "email_profissional": "ADM", "nome_profissional": "BLOQUEIO", "valor_cobrado": 0, "status": "bloqueado"} for h in range(7, 22)]
                supabase.table("reservas").insert(inserts).execute()
            st.success("Bloqueado!")
        if st.button("Desbloquear", type="secondary"):
            salas = ["Sala 1", "Sala 2"] if sala_block == "Ambas" else [sala_block]
            for s in salas: supabase.table("reservas").delete().eq("sala_nome", s).eq("data_reserva", str(dt_block)).eq("status", "bloqueado").execute()
            st.success("Desbloqueado!")
    with tabs[3]:
        # ...
        pass
    with tabs[4]:
        # ...
        pass

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
