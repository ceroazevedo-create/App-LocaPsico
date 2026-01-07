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

# Inicializa Estado (Garante que as variáveis existem)
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'SEMANA'

NOME_DO_ARQUIVO_LOGO = "logo.png" 

# --- 2. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. JAVASCRIPT: CAPTURA DE HASH (CRUCIAL) ---
# Esse script converte o #access_token... do email em ?access_token... que o Python lê
js_hash_fix = """
<script>
    if (window.location.hash) {
        const params = new URLSearchParams(window.location.hash.substring(1));
        if (params.has('access_token') && params.has('refresh_token')) {
            const newUrl = window.location.origin + window.location.pathname + 
                           '?access_token=' + params.get('access_token') + 
                           '&refresh_token=' + params.get('refresh_token') + 
                           '&type=' + (params.get('type') || 'recovery');
            window.location.href = newUrl;
        }
    }
</script>
"""
components.html(js_hash_fix, height=0)

# --- 4. CSS VISUAL ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; margin-top: 0rem !important; max-width: 1000px; }
    .stApp { background-color: #f2f4f7; font-family: 'Inter', sans-serif; color: #1a1f36; }
    
    div[data-testid="column"]:nth-of-type(2) > div {
        background-color: #ffffff; padding: 48px 40px; border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #eef2f6; margin-top: 2vh;
    }
    div[data-testid="stImage"] { display: flex; justify-content: center !important; width: 100%; margin-bottom: 20px; }
    div[data-testid="stImage"] > img { object-fit: contain; width: 90% !important; max-width: 380px; }
    
    h1 { font-size: 28px; font-weight: 800; color: #1a1f36; margin-bottom: 8px; text-align: center; }
    p { color: #697386; font-size: 15px; text-align: center; margin-bottom: 24px; }
    .stTextInput input { background-color: #ffffff; border: 1px solid #e3e8ee; border-radius: 10px; padding: 12px; height: 48px; }
    
    div[data-testid="stVerticalBlock"] button[kind="primary"] {
        background-color: #0d9488 !important; color: #ffffff !important; border: none; height: 48px; font-weight: 700; border-radius: 10px; margin-top: 10px;
    }
    div[data-testid="stVerticalBlock"] button[kind="primary"] * { color: #ffffff !important; }
    button[kind="secondary"] { border: 1px solid #e2e8f0; color: #64748b; }
    
    button[key="logout_btn"], button[key="admin_logout"] { 
        border-color: #fecaca !important; color: #ef4444 !important; background: #fef2f2 !important; font-weight: 600; 
    }
    
    .blocked-slot { background-color: #fef2f2; height: 40px; border-radius: 4px; border: 1px solid #fecaca; opacity: 0.7; }
    .admin-blocked { background-color: #1e293b; color: white; font-size: 10px; padding: 4px; border-radius: 4px; text-align: center; font-weight: bold; margin-bottom: 2px; }
    .evt-chip { background: #ccfbf1; border-left: 3px solid #0d9488; color: #115e59; font-size: 10px; padding: 4px; border-radius: 4px; overflow: hidden; white-space: nowrap; margin-bottom: 2px; }
</style>
""", unsafe_allow_html=True)

# --- 5. FUNÇÕES LÓGICAS ---

def process_url_token():
    """Verifica e processa tokens na URL antes de qualquer coisa"""
    qp = st.query_params
    if "access_token" in qp and "refresh_token" in qp:
        try:
            # Tenta autenticar com o token do email
            session = supabase.auth.set_session(qp["access_token"], qp["refresh_token"])
            if session and session.user:
                st.session_state.user = session.user
                st.session_state.is_admin = (session.user.email == "admin@admin.com.br") # Ajuste seu email admin
                
                # Se for recuperação de senha, força o modo
                if qp.get("type") == "recovery":
                    st.session_state.auth_mode = 'reset_password'
                
                # Limpa URL para não processar de novo
                st.query_params.clear()
                st.rerun()
        except:
            st.error("O link de recuperação é inválido ou expirou.")
            time.sleep(3)
            st.query_params.clear()
            st.rerun()

# CHAMADA IMEDIATA DA VERIFICAÇÃO DE URL
process_url_token()

def resolver_nome(email, nome_meta=None, nome_banco=None):
    if not email: return "Visitante"
    if "cesar_unib" in email: return "Cesar"
    if "thascaranalle" in email: return "Thays"
    return nome_banco or nome_meta or email.split('@')[0].title()

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
def modal_agendamento(sala_padrao, data_sugerida):
    st.markdown("### Detalhes da Reserva")
    config_precos = get_config_precos()
    
    modo = st.radio("Tipo de Cobrança", ["Por Hora", "Por Período"], horizontal=True)
    dt = st.date_input("Data", value=data_sugerida, min_value=datetime.date.today())
    
    horarios_selecionados = []
    valor_final = 0.0
    
    if modo == "Por Hora":
        dia_sem = dt.weekday()
        if dia_sem == 6: lista_horas = []; st.error("Domingo: Fechado")
        elif dia_sem == 5: lista_horas = [f"{h:02d}:00" for h in range(7, 14)]; st.info("Sábado: Até 14h")
        else: lista_horas = [f"{h:02d}:00" for h in range(7, 22)]
        hr = st.selectbox("Horário de Início", lista_horas, disabled=(len(lista_horas)==0))
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
                        "sala_nome": sala_padrao, "data_reserva": str(d_res),
                        "hora_inicio": f"{h_start}:00", "hora_fim": f"{h_end}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm,
                        "valor_cobrado": val_to_save, "status": "confirmada"
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
                    bg_color = "white"
                    if d_obj < datetime.date.today() or d_obj.weekday() == 6: bg_color = "#fef2f2"
                    elif d_obj == datetime.date.today(): bg_color = "#f0fdf4"
                    eventos_html = ""
                    if d_str in mapa:
                        for h in sorted(mapa[d_str].keys()):
                            res = mapa[d_str][h]
                            if res['status'] == 'bloqueado': eventos_html += f"<div style='background:#1e293b; color:white; font-size:9px; padding:2px; border-radius:3px; margin-bottom:2px;'>⛔ BLOQ</div>"
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
        for i, d in enumerate(visiveis): c_h[i+1].markdown(f"<div style='text-align:center; padding-bottom:5px; border-bottom:2px solid #e2e8f0; margin-bottom:5px'><div style='font-size:10px; font-weight:bold; color:#64748b'>{d_n[wd]}</div><div style='font-size:16px; font-weight:bold; color:#1e293b'>{visiveis[i].day}</div></div>", unsafe_allow_html=True)
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
                else: cont.markdown("<div style='height:40px; border-left:1px solid #f1f5f9'></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if not is_admin_mode:
        if st.button("➕ Agendar", type="primary", use_container_width=True): modal_agendamento(sala, st.session_state.data_ref)

def tela_admin_master():
    tabs = st.tabs(["💰 Config", "📅 Visualizar/Excluir", "🚫 Bloqueios", "📄 Relatórios"])
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

# --- 6. EXECUÇÃO ---
def main():
    # 1. VERIFICA MODO DE RECUPERAÇÃO DE SENHA (PRIORIDADE ALTA)
    if st.session_state.auth_mode == 'reset_password':
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.write("")
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True)
            st.markdown("<h2 style='text-align:center'>🔒 Nova Senha</h2>", unsafe_allow_html=True)
            
            new_pass = st.text_input("Digite sua nova senha", type="password")
            if st.button("Atualizar Senha", type="primary"):
                if len(new_pass) >= 6:
                    try:
                        # Tenta atualizar
                        supabase.auth.update_user({"password": new_pass})
                        st.success("Senha atualizada! Redirecionando...")
                        st.session_state.auth_mode = 'login' 
                        time.sleep(2)
                        st.rerun()
                    except: st.error("Erro ao atualizar. Tente novamente.")
                else: st.warning("Senha muito curta.")
        return 

    # 2. SE NÃO LOGADO:
    if not st.session_state.user:
        # Tenta pegar sessão ativa antes de mostrar login
        try:
            sess = supabase.auth.get_session()
            if sess:
                st.session_state.user = sess.user
                st.session_state.is_admin = (sess.user.email == "admin@admin.com.br")
                st.rerun()
        except: pass

        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.write("") 
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='text-align:center; color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            if st.session_state.auth_mode == 'login':
                st.markdown("<h1>Bem-vindo de volta</h1>", unsafe_allow_html=True)
                email = st.text_input("E-mail profissional", placeholder="seu@email.com")
                senha = st.text_input("Sua senha", type="password", placeholder="••••••••")
                if st.button("Entrar na Agenda", type="primary"):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state['user'] = u.user
                        st.session_state['is_admin'] = (email == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Credenciais inválidas.")
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
                        supabase.auth.reset_password_for_email(rec_e, options={"redirect_to": "https://app-locapsico.streamlit.app"})
                        st.success("Verifique seu e-mail.")
                    except: st.error("Erro.")
                if st.button("Voltar", type="secondary"): st.session_state.auth_mode = 'login'; st.rerun()
        return

    # 3. SE LOGADO E NÃO ESTÁ EM MODO DE RECUPERAÇÃO
    u = st.session_state['user']
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
                                        supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute(); st.toast("Cancelado!", icon="✅"); time.sleep(1); st.rerun()
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
                if st.button("Alterar Senha"): supabase.auth.update_user({"password": p1}); st.success("Senha atualizada!")

if __name__ == "__main__":
    main()
