import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import base64
import calendar
import plotly.express as px

# --- 1. CONFIGURAÇÃO E CSS MODERNO ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    /* BOTÕES */
    .stButton>button {
        background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%);
        color: white !important; border: none; border-radius: 12px;
        padding: 0.6rem 1.2rem; font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(13, 148, 136, 0.3);
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(13, 148, 136, 0.4); }
    
    /* HEADER E CARDS */
    .app-header {
        display: flex; justify-content: space-between; align-items: center;
        background: white; padding: 16px 32px; border-radius: 16px;
        margin-bottom: 32px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    .modern-card {
        background: white; padding: 24px; border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0; margin-bottom: 20px;
    }

    /* AGENDA SEMANAL/DIÁRIA */
    .cal-cell-wrapper { border-left: 1px solid #e2e8f0; min-height: 50px; position: relative; transition: background 0.2s; }
    .event-chip {
        background: #ccfbf1; border-left: 3px solid #0d9488; color: #115e59;
        padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;
        margin: 2px; cursor: pointer; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
    }
    .blocked-chip {
        background: repeating-linear-gradient(45deg, #fef2f2, #fef2f2 10px, #fee2e2 10px, #fee2e2 20px);
        border: 1px dashed #ef4444; opacity: 0.6; width: 100%; height: 100%; position: absolute; top:0; left:0;
    }
    .day-header { text-align: center; font-weight: 700; color: #64748b; font-size: 0.85rem; padding-bottom: 10px; border-bottom: 2px solid #e2e8f0; }

    /* AGENDA MENSAL (NOVO) */
    .month-day-box {
        background: white; border: 1px solid #e2e8f0; min-height: 100px; padding: 5px;
        font-size: 12px; display: flex; flex-direction: column; gap: 2px;
    }
    .month-day-num { font-weight: 800; color: #334155; margin-bottom: 4px; }
    .month-event {
        background-color: #0d9488; color: white; border-radius: 4px; padding: 2px 4px;
        font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. LOGICA AUXILIAR ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if email == "cesar_unib@msn.com": return "Cesar"
    if email == "thascaranalle@gmail.com": return "Thays"
    return nome_banco or nome_meta or email.split('@')[0].title()

def get_preco():
    try:
        r = supabase.table("configuracoes").select("preco_hora").limit(1).execute()
        return float(r.data[0]['preco_hora']) if r.data else 32.00
    except: return 32.00

# --- 4. MODAL AGENDAMENTO ---
@st.dialog("Novo Agendamento")
def modal_agendamento(sala_padrao, data_padrao):
    st.write("Detalhes da Sessão")
    c1, c2 = st.columns(2)
    dt = c1.date_input("Data", value=data_padrao, min_value=datetime.date.today())
    hr = c2.selectbox("Horário", [f"{h:02d}:00" for h in range(7, 23)])
    
    # Checkbox admin
    ignore = st.checkbox("Admin: Forçar Reserva") if st.session_state.get('is_admin') else False

    if st.button("Confirmar", use_container_width=True):
        agora = datetime.datetime.now()
        dt_check = datetime.datetime.combine(dt, datetime.time(int(hr[:2]), 0))
        
        erro = None
        if not ignore:
            if dt.weekday() == 6: erro = "Domingo fechado."
            elif dt_check < agora: erro = "Data passada."
        
        if erro:
            st.error(erro)
        else:
            try:
                # Checa conflito
                check = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao)\
                    .eq("data_reserva", str(dt)).eq("hora_inicio", hr).eq("status", "confirmada").execute()
                
                if check.data:
                    st.error("Horário Ocupado!")
                else:
                    h_fim = f"{int(hr[:2])+1:02d}:00"
                    user = st.session_state['user']
                    nome = resolver_nome(user.email, nome_meta=user.user_metadata.get('nome'))
                    
                    supabase.table("reservas").insert({
                        "sala_nome": sala_padrao, "data_reserva": str(dt), "hora_inicio": hr, "hora_fim": h_fim,
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nome,
                        "valor_cobrado": get_preco(), "status": "confirmada"
                    }).execute()
                    st.toast("Agendado!", icon="✅")
                    st.rerun()
            except Exception as e: st.error(f"Erro: {e}")

# --- 5. RENDER CALENDÁRIO ---
def render_calendar_ui(sala):
    # --- CONTROLES ---
    col_nav_a, col_nav_b, col_nav_c = st.columns([1, 4, 1])
    
    with col_nav_a:
        if st.button("◀", use_container_width=True):
            delta = 7 if st.session_state.view_mode == 'SEMANA' else (1 if st.session_state.view_mode == 'DIA' else 30)
            st.session_state.data_ref -= timedelta(days=delta)
            st.rerun()

    with col_nav_b:
        # Seletor de Modo
        v1, v2, v3 = st.columns(3)
        def set_m(m): st.session_state.view_mode = m
        sty = lambda m: "primary" if st.session_state.view_mode == m else "secondary"
        
        with v1: 
            if st.button("DIA", type=sty('DIA'), use_container_width=True): set_m('DIA')
        with v2: 
            if st.button("SEMANA", type=sty('SEMANA'), use_container_width=True): set_m('SEMANA')
        with v3: 
            if st.button("MÊS", type=sty('MÊS'), use_container_width=True): set_m('MÊS')
        
        # Label da Data
        dt = st.session_state.data_ref
        mes_nome = dt.strftime("%B").capitalize()
        if st.session_state.view_mode == 'SEMANA':
            ini = dt - timedelta(days=dt.weekday())
            fim = ini + timedelta(days=6)
            st.markdown(f"<div style='text-align:center; font-weight:800; font-size:18px; color:#334155; margin-top:5px'>{ini.day} - {fim.day} {mes_nome}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center; font-weight:800; font-size:18px; color:#334155; margin-top:5px'>{mes_nome} {dt.year}</div>", unsafe_allow_html=True)

    with col_nav_c:
        if st.button("▶", use_container_width=True):
            delta = 7 if st.session_state.view_mode == 'SEMANA' else (1 if st.session_state.view_mode == 'DIA' else 30)
            st.session_state.data_ref += timedelta(days=delta)
            st.rerun()

    st.markdown("---")

    # --- LÓGICA DE DADOS ---
    ref = st.session_state.data_ref
    
    # Define intervalo de busca no banco
    if st.session_state.view_mode == 'MÊS':
        ano, mes = ref.year, ref.month
        ult_dia = calendar.monthrange(ano, mes)[1]
        data_min = datetime.date(ano, mes, 1)
        data_max = datetime.date(ano, mes, ult_dia)
    elif st.session_state.view_mode == 'SEMANA':
        data_min = ref - timedelta(days=ref.weekday())
        data_max = data_min + timedelta(days=6)
    else: # DIA
        data_min = ref
        data_max = ref

    # Busca Reservas
    reservas = []
    try:
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).eq("status", "confirmada")\
            .gte("data_reserva", str(data_min)).lte("data_reserva", str(data_max)).execute()
        reservas = r.data
    except: pass

    # Mapa de Dados
    mapa = {}
    for item in reservas:
        d_str = item['data_reserva']
        if st.session_state.view_mode == 'MÊS':
            # No mês, agrupamos por dia numa lista
            if d_str not in mapa: mapa[d_str] = []
            mapa[d_str].append(item)
        else:
            # Na semana/dia, mapeamos por Hora
            if d_str not in mapa: mapa[d_str] = {}
            mapa[d_str][item['hora_inicio']] = item

    # --- RENDERIZAÇÃO ---
    
    # >>>> VISÃO MENSAL <<<<
    if st.session_state.view_mode == 'MÊS':
        # Cabeçalho Semanal
        cols = st.columns(7)
        dias_sem = ['SEG','TER','QUA','QUI','SEX','SÁB','DOM']
        for i, d in enumerate(dias_sem):
            cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#64748b; font-size:12px'>{d}</div>", unsafe_allow_html=True)
            
        # Matriz
        matriz = calendar.monthcalendar(ref.year, ref.month)
        for semana in matriz:
            cols = st.columns(7)
            for i, dia in enumerate(semana):
                if dia == 0:
                    cols[i].markdown("<div style='min-height:100px; background:#f8fafc; border:1px solid #e2e8f0'></div>", unsafe_allow_html=True)
                else:
                    dt_atual = datetime.date(ref.year, ref.month, dia)
                    dt_str = str(dt_atual)
                    
                    # Conteúdo HTML do dia
                    html_evts = ""
                    if dt_str in mapa:
                        for evt in mapa[dt_str]:
                            nm = resolver_nome(evt['email_profissional'], nome_banco=evt.get('nome_profissional'))
                            hr = evt['hora_inicio'][:5]
                            html_evts += f"<div class='month-event'>{hr} {nm}</div>"
                    
                    # Renderiza Célula
                    cols[i].markdown(f"""
                    <div class='month-day-box'>
                        <div class='month-day-num'>{dia}</div>
                        {html_evts}
                    </div>
                    """, unsafe_allow_html=True)

    # >>>> VISÃO SEMANAL / DIÁRIA <<<<
    else:
        # Prepara colunas
        if st.session_state.view_mode == 'SEMANA':
            dias_show = [data_min + timedelta(days=i) for i in range(7)]
            col_widths = [0.5] + [1]*7
        else:
            dias_show = [ref]
            col_widths = [0.5, 6]

        # Cabeçalho
        cols = st.columns(col_widths)
        cols[0].write("")
        nomes_sem = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
        
        for i, d in enumerate(dias_show):
            wd = d.weekday()
            is_today = d == datetime.date.today()
            cor = "#0d9488" if is_today else ("#ef4444" if wd==6 else "#64748b")
            bg = "#f0fdfa" if is_today else "transparent"
            
            cols[i+1].markdown(f"""
            <div style='text-align:center; border-bottom:3px solid {cor}; background:{bg}; border-radius:8px 8px 0 0; padding:5px'>
                <div style='font-size:11px; font-weight:bold; color:{cor}'>{nomes_sem[wd]}</div>
                <div style='font-size:20px; font-weight:900; color:#1e293b'>{d.day}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Linhas de Hora
        horarios = [f"{h:02d}:00:00" for h in range(7, 23)]
        for hora in horarios:
            c_row = st.columns(col_widths)
            c_row[0].markdown(f"<div style='font-size:11px; color:#94a3b8; text-align:right; margin-top:15px'>{hora[:5]}</div>", unsafe_allow_html=True)
            
            for i, d in enumerate(dias_show):
                d_str = str(d)
                reserva = mapa.get(d_str, {}).get(hora)
                container = c_row[i+1].container()
                
                if reserva:
                    nm = resolver_nome(reserva['email_profissional'], nome_banco=reserva.get('nome_profissional'))
                    container.markdown(f"<div class='event-chip' title='{nm}'>👤 {nm}</div>", unsafe_allow_html=True)
                else:
                    # Bloqueios visuais
                    dt_slot = datetime.datetime.combine(d, datetime.time(int(hora[:2]), 0))
                    if d.weekday() == 6 or dt_slot < datetime.datetime.now():
                        container.markdown("<div class='blocked-chip'></div>", unsafe_allow_html=True)
                    else:
                        container.markdown("<div class='cal-cell-wrapper'></div>", unsafe_allow_html=True)

    # Botão Flutuante
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✨ Agendar Sessão", use_container_width=True):
        modal_agendamento(sala, st.session_state.data_ref)

# --- 6. TELAS DO SISTEMA ---
def tela_dashboard():
    user = st.session_state['user']
    nome = resolver_nome(user.email, nome_meta=user.user_metadata.get('nome'))
    
    # Header
    st.markdown(f"""
    <div class='modern-card' style='border-left:5px solid #0d9488; display:flex; justify-content:space-between; align-items:center;'>
        <div><h2 style='margin:0'>Olá, {nome}!</h2><p style='margin:0; color:#64748b'>Resumo financeiro e agenda.</p></div>
    </div>
    """, unsafe_allow_html=True)

    try:
        # Métricas (Só confirmadas)
        df = pd.DataFrame(supabase.table("reservas").select("*").eq("user_id", user.id).eq("status", "confirmada").execute().data)
        
        c1, c2 = st.columns([1, 2])
        with c1:
            val = df['valor_cobrado'].sum() if not df.empty else 0
            qtd = len(df) if not df.empty else 0
            st.metric("Total Investido", f"R$ {val:.0f}")
            st.metric("Sessões Realizadas", qtd)
            
            with st.expander("Alterar Senha"):
                p1 = st.text_input("Nova Senha", type="password")
                if st.button("Salvar"):
                    if len(p1)>=6: 
                        supabase.auth.update_user({"password": p1})
                        st.toast("Sucesso!")
        
        with c2:
            if not df.empty:
                df['mes'] = pd.to_datetime(df['data_reserva']).dt.strftime('%Y-%m')
                gf = df.groupby('mes')['valor_cobrado'].sum().reset_index()
                fig = px.bar(gf, x='mes', y='valor_cobrado', title="Investimento Mensal", color_discrete_sequence=['#0d9488'])
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Sem dados.")
            
        # Lista Futura
        st.subheader("Próximos Agendamentos")
        hoje = str(datetime.date.today())
        futs = supabase.table("reservas").select("*").eq("user_id", user.id).eq("status", "confirmada").gte("data_reserva", hoje).order("data_reserva").execute().data
        
        if futs:
            for r in futs:
                dt_obj = datetime.datetime.strptime(f"{r['data_reserva']} {r['hora_inicio']}", "%Y-%m-%d %H:%M:%S")
                diff = (dt_obj - datetime.datetime.now()).total_seconds()/3600
                
                cc1, cc2 = st.columns([4,1])
                cc1.write(f"📅 **{r['data_reserva']}** | ⏰ {r['hora_inicio']} | {r['sala_nome']}")
                
                if diff > 24:
                    if cc2.button("Cancelar", key=f"c_{r['id']}"):
                        supabase.table("reservas").update({"status":"cancelada"}).eq("id", r['id']).execute()
                        st.rerun()
                else: cc2.caption("🔒 < 24h")
                st.divider()
        else: st.info("Agenda vazia.")
            
    except Exception as e: st.error(str(e))

# --- 7. LOGIN E MAIN ---
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'SEMANA'

def main():
    if 'user' not in st.session_state:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.markdown("<h1 style='text-align:center; color:#0d9488'>Ψ LocaPsico</h1>", unsafe_allow_html=True)
            tab_l, tab_c = st.tabs(["Entrar", "Criar Conta"])
            with tab_l:
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                if st.button("Entrar", use_container_width=True):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state['user'] = u.user
                        st.session_state['is_admin'] = (email == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Erro no login")
            with tab_c:
                nome = st.text_input("Nome")
                em = st.text_input("Email Reg")
                pw = st.text_input("Senha Reg", type="password")
                if st.button("Cadastrar", use_container_width=True):
                    try:
                        supabase.auth.sign_up({"email": em, "password": pw, "options": {"data": {"nome": nome}}})
                        st.success("Sucesso! Faça login.")
                    except: st.error("Erro")
        return

    # App Logado
    st.markdown(f"""
    <div class='app-header'>
        <div class='brand-logo'><span class='brand-icon'>L</span> LOCAPSICO</div>
        <div>{st.session_state['user'].email}</div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["📅 AGENDA", "📊 PAINEL"] + (["⚙️ ADMIN"] if st.session_state.get('is_admin') else []))
    
    with tabs[0]:
        c_s, c_cal = st.columns([1, 4])
        with c_s: 
            st.write("### Sala")
            sala = st.radio("S", ["Sala 1", "Sala 2"], label_visibility="collapsed")
        with c_cal: render_calendar_ui(sala)
        
    with tabs[1]: tela_dashboard()
    
    if len(tabs) > 2:
        with tabs[2]: st.write("Painel Admin (Configurações e Relatórios aqui...)") # (Simplificado para caber)

    with st.sidebar:
        if st.button("Sair"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()
