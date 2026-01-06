import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import base64
import calendar
import plotly.express as px

# --- 1. CONFIGURAÇÃO E CSS RESPONSIVO ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    /* RESET E FONTE */
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* AJUSTE DE PADDING PARA MOBILE E DESKTOP */
    .block-container { padding-top: 1rem; padding-bottom: 3rem; padding-left: 1rem; padding-right: 1rem; }

    /* BOTÕES COM TOQUE MODERNO E RESPONSIVO */
    .stButton>button {
        border-radius: 8px; font-weight: 600; border: none; transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); width: 100%;
    }
    div[data-testid="stHorizontalBlock"] button:hover { transform: translateY(-2px); }

    /* HEADER RESPONSIVO */
    .app-header {
        display: flex; justify-content: space-between; align-items: center;
        background: white; padding: 15px 20px; border-radius: 12px;
        margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        flex-wrap: wrap; gap: 10px;
    }
    .logo-area { font-size: 20px; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 10px; }
    .psi-icon { background: #0d9488; color: white; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }

    /* CALENDÁRIO: ADAPTAÇÃO */
    .day-col-header { text-align: center; padding: 5px 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 5px; }
    .day-name { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .day-num { font-size: 18px; font-weight: 800; color: #1e293b; }
    .day-num.today { color: #0d9488; }
    
    .time-slot-row { border-bottom: 1px solid #f1f5f9; min-height: 50px; display: flex; align-items: center; }
    .time-label { font-size: 11px; color: #94a3b8; font-weight: 600; padding-right: 5px; text-align: right; width: 100%; }
    
    /* CHIPS DE EVENTO */
    .evt-chip {
        background: #ccfbf1; border-left: 3px solid #0d9488; color: #115e59;
        font-size: 10px; font-weight: 600; padding: 3px 5px; border-radius: 4px;
        margin: 1px 0; cursor: default; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }

    /* MÊS VIEW */
    .month-day {
        background: white; border: 1px solid #e2e8f0; min-height: 80px; padding: 2px; border-radius: 4px;
        display: flex; flex-direction: column; gap: 2px;
    }
    .month-day-header { font-weight: 700; font-size: 11px; color: #475569; margin-bottom: 2px; text-align:center; }
    .month-evt-dot {
        font-size: 9px; background: #0f766e; color: white; padding: 1px 3px; border-radius: 3px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    
    .blocked-slot { 
        background: repeating-linear-gradient(45deg, #fef2f2, #fef2f2 10px, #fee2e2 10px, #fee2e2 20px); 
        height: 40px; width: 100%; border-radius: 4px; opacity: 0.5;
    }

    /* MEDIA QUERIES PARA CELULAR */
    @media (max-width: 768px) {
        .app-header { padding: 10px; flex-direction: column; align-items: flex-start; }
        .logo-area { font-size: 18px; }
        .day-name { font-size: 9px; }
        .day-num { font-size: 14px; }
        .evt-chip { font-size: 9px; padding: 2px; border-left-width: 2px; }
        .month-day { min-height: 50px; }
        .month-evt-dot { font-size: 8px; display:none; } /* Oculta detalhes no mês mobile para não poluir */
        .month-day.has-event { background-color: #d1fae5 !important; } /* Pinta o fundo se tiver evento no mobile */
        
        /* Ajuste de colunas */
        [data-testid="column"] { min-width: 0 !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. LÓGICA ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if email == "cesar_unib@msn.com": return "Cesar"
    if email == "thascaranalle@gmail.com": return "Thays"
    return nome_banco or nome_meta or email.split('@')[0].title()

def get_preco():
    try:
        r = supabase.table("configuracoes").select("preco_hora").limit(1).execute()
        return float(r.data[0]['preco_hora']) if r.data else 32.00
    except: return 32.00

# --- 4. NAVEGAÇÃO ---
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'SEMANA'

def navegar(direcao):
    mode = st.session_state.view_mode
    delta = 1 if mode == 'DIA' else (7 if mode == 'SEMANA' else 30)
    if direcao == 'prev': st.session_state.data_ref -= timedelta(days=delta)
    else: st.session_state.data_ref += timedelta(days=delta)

# --- 5. MODAL AGENDAMENTO (Mobile Friendly) ---
@st.dialog("Novo Agendamento")
def modal_agendamento(sala_padrao, data_sugerida):
    st.write("Confirmar Reserva")
    
    # Layout empilhado no mobile automaticamente
    dt = st.date_input("Data", value=data_sugerida, min_value=datetime.date.today())
    
    # Regras Horário
    dia_sem = dt.weekday()
    if dia_sem == 6:
        lista_horas = []
        st.error("Domingo: Fechado")
    elif dia_sem == 5:
        lista_horas = [f"{h:02d}:00" for h in range(7, 14)]
        st.info("Sábado: Até 14h")
    else:
        lista_horas = [f"{h:02d}:00" for h in range(7, 22)]
    
    hr = st.selectbox("Horário", lista_horas, disabled=(len(lista_horas)==0))
    
    ignore = st.checkbox("Admin: Ignorar Regras") if st.session_state.get('is_admin') else False

    if st.button("Confirmar Agendamento", use_container_width=True, disabled=(len(lista_horas)==0 and not ignore)):
        hr_final = hr if hr else "07:00"
        agora = datetime.datetime.now()
        dt_check = datetime.datetime.combine(dt, datetime.time(int(hr_final[:2]), 0))
        
        erro = None
        if not ignore:
            if dia_sem == 6: erro = "Domingo fechado."
            elif dt_check < agora: erro = "Data passada."
        
        if erro: st.error(erro)
        else:
            try:
                chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao)\
                    .eq("data_reserva", str(dt)).eq("hora_inicio", hr_final).eq("status", "confirmada").execute()
                if chk.data:
                    st.error("Indisponível!")
                else:
                    user = st.session_state['user']
                    nm = resolver_nome(user.email, user.user_metadata.get('nome'))
                    supabase.table("reservas").insert({
                        "sala_nome": sala_padrao, "data_reserva": str(dt),
                        "hora_inicio": hr_final, "hora_fim": f"{int(hr_final[:2])+1:02d}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm,
                        "valor_cobrado": get_preco(), "status": "confirmada"
                    }).execute()
                    st.toast("Sucesso!", icon="✅")
                    st.rerun()
            except Exception as e: st.error(f"Erro: {e}")

# --- 6. RENDER CALENDÁRIO RESPONSIVO ---
def render_calendar(sala):
    # NAV
    c_L, c_R = st.columns([1, 1])
    with c_L: 
        if st.button("◀ Anterior", use_container_width=True): navegar('prev'); st.rerun()
    with c_R: 
        if st.button("Próximo ▶", use_container_width=True): navegar('next'); st.rerun()
        
    # MENU VIEW
    mode = st.session_state.view_mode
    def set_mode(m): st.session_state.view_mode = m
    bt_sty = lambda m: "primary" if mode == m else "secondary"
    
    b1, b2, b3 = st.columns(3)
    with b1: 
        if st.button("Dia", type=bt_sty('DIA'), use_container_width=True): set_mode('DIA'); st.rerun()
    with b2: 
        if st.button("Semana", type=bt_sty('SEMANA'), use_container_width=True): set_mode('SEMANA'); st.rerun()
    with b3: 
        if st.button("Mês", type=bt_sty('MÊS'), use_container_width=True): set_mode('MÊS'); st.rerun()

    # LABEL
    ref = st.session_state.data_ref
    mes_str = ref.strftime("%B").capitalize()
    if mode == 'SEMANA':
        i = ref - timedelta(days=ref.weekday())
        f = i + timedelta(days=6)
        lbl = f"{i.day} - {f.day} {mes_str}"
    elif mode == 'DIA': lbl = f"{ref.day} de {mes_str}"
    else: lbl = f"{mes_str} {ref.year}"
    
    st.markdown(f"<div style='text-align:center; font-weight:800; color:#334155; margin:10px 0'>{lbl}</div>", unsafe_allow_html=True)

    # DADOS
    if mode == 'MÊS':
        ano, mes = ref.year, ref.month
        last = calendar.monthrange(ano, mes)[1]
        d_start, d_end = datetime.date(ano, mes, 1), datetime.date(ano, mes, last)
    elif mode == 'SEMANA':
        d_start = ref - timedelta(days=ref.weekday())
        d_end = d_start + timedelta(days=6)
    else: d_start = d_end = ref

    reservas = []
    try:
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).eq("status", "confirmada")\
            .gte("data_reserva", str(d_start)).lte("data_reserva", str(d_end)).execute()
        reservas = r.data
    except: pass

    mapa = {}
    for x in reservas:
        d = x['data_reserva']
        if mode == 'MÊS':
            if d not in mapa: mapa[d] = []
            mapa[d].append(x)
        else:
            if d not in mapa: mapa[d] = {}
            mapa[d][x['hora_inicio']] = x

    # --- GRID RENDER ---
    if mode == 'MÊS':
        cols = st.columns(7)
        for i,d in enumerate(['D','S','T','Q','Q','S','S']):
            cols[i].markdown(f"<div style='text-align:center; font-size:10px; font-weight:bold; color:#94a3b8'>{d}</div>", unsafe_allow_html=True)
        
        cal_mat = calendar.monthcalendar(ref.year, ref.month)
        for sem in cal_mat:
            cols = st.columns(7)
            for i, dia in enumerate(sem):
                if dia == 0:
                    cols[i].markdown("<div style='height:50px; background:#f8fafc'></div>", unsafe_allow_html=True)
                else:
                    dt_at = datetime.date(ref.year, ref.month, dia)
                    dt_s = str(dt_at)
                    has_evt = dt_s in mapa
                    
                    html = ""
                    css_class = "month-day"
                    if has_evt: css_class += " has-event" # CSS hook for mobile background
                    
                    if has_evt:
                        for e in mapa[dt_s]:
                            nm = resolver_nome(e['email_profissional'], nome_banco=e.get('nome_profissional'))
                            html += f"<div class='month-evt-dot'>{e['hora_inicio'][:5]} {nm}</div>"
                    
                    bg = "#f0fdfa" if dt_at == datetime.date.today() else "white"
                    cols[i].markdown(f"<div class='{css_class}' style='background:{bg}'><div class='month-day-header'>{dia}</div>{html}</div>", unsafe_allow_html=True)

    else: # DIA/SEMANA
        visiveis = [d_start + timedelta(days=i) for i in range(7 if mode == 'SEMANA' else 1)]
        ratio = [0.6] + [1]*len(visiveis) # Coluna hora menor no mobile
        
        # Header Dias
        c_h = st.columns(ratio)
        c_h[0].write("")
        d_n = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
        for i, d in enumerate(visiveis):
            wd = d.weekday()
            c_h[i+1].markdown(f"<div class='day-col-header'><div class='day-name'>{d_n[wd]}</div><div class='day-num'>{d.day}</div></div>", unsafe_allow_html=True)

        # Slots
        # Regra: Seg-Sex até 21h (fim 22h), Sáb até 13h (fim 14h)
        # Mostramos até 21h no grid para consistência
        for h in range(7, 22):
            hora = f"{h:02d}:00:00"
            row = st.columns(ratio)
            row[0].markdown(f"<div class='time-label'>{h:02d}:00</div>", unsafe_allow_html=True)
            
            for i, d in enumerate(visiveis):
                d_s = str(d)
                res = mapa.get(d_s, {}).get(hora)
                cont = row[i+1].container()
                
                if res:
                    nm = resolver_nome(res['email_profissional'], nome_banco=res.get('nome_profissional'))
                    cont.markdown(f"<div class='evt-chip'>{nm}</div>", unsafe_allow_html=True)
                else:
                    # Bloqueios
                    dt_slot = datetime.datetime.combine(d, datetime.time(h, 0))
                    bloq_sab = (d.weekday() == 5 and h > 13)
                    if d.weekday() == 6 or dt_slot < datetime.datetime.now() or bloq_sab:
                        cont.markdown("<div class='blocked-slot'></div>", unsafe_allow_html=True)
                    else:
                        cont.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Agendar", type="primary", use_container_width=True):
        modal_agendamento(sala, st.session_state.data_ref)

# --- 7. TELA ADMIN ---
def tela_admin():
    st.markdown("### ⚙️ Admin")
    t1, t2 = st.tabs(["KPIs", "Reservas"])
    
    with t1:
        try:
            df = pd.DataFrame(supabase.table("reservas").select("*").eq("status", "confirmada").execute().data)
            rec = df['valor_cobrado'].sum() if not df.empty else 0
            
            k1, k2 = st.columns(2)
            k1.metric("Receita", f"R$ {rec:.0f}")
            k2.metric("Preço/h", f"R$ {get_preco():.2f}")
            
            nv = st.number_input("Novo Valor", value=get_preco())
            if st.button("Salvar Preço", use_container_width=True):
                supabase.table("configuracoes").update({"preco_hora": nv}).gt("id", 0).execute()
                st.toast("Atualizado!")
        except: pass

    with t2:
        q = st.text_input("Buscar User")
        try:
            res = supabase.table("reservas").select("*").eq("status", "confirmada").order("data_reserva", desc=True).limit(30).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                if q: df = df[df['email_profissional'].str.contains(q, case=False)]
                for _, r in df.iterrows():
                    c1, c2 = st.columns([3, 1])
                    c1.caption(f"{r['data_reserva']} | {r['sala_nome']} | {r['email_profissional']}")
                    if c2.button("X", key=f"ad_{r['id']}"):
                        supabase.table("reservas").update({"status": "cancelada"}).eq("id", r['id']).execute()
                        st.rerun()
                    st.divider()
        except: pass

# --- 8. APP PRINCIPAL ---
def main():
    if 'user' not in st.session_state:
        st.markdown("<br><h1 style='text-align:center; color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Entrar", "Criar"])
        with t1:
            e = st.text_input("Email")
            p = st.text_input("Senha", type="password")
            if st.button("Entrar", use_container_width=True):
                try:
                    u = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state['user'] = u.user
                    st.session_state['is_admin'] = (e == "admin@admin.com.br")
                    st.rerun()
                except: st.error("Erro")
        with t2:
            n = st.text_input("Nome")
            ne = st.text_input("Email Reg")
            np = st.text_input("Senha Reg", type="password")
            if st.button("Cadastrar", use_container_width=True):
                supabase.auth.sign_up({"email": ne, "password": np, "options": {"data": {"nome": n}}})
                st.success("OK! Login.")
        return

    # LOGADO
    u = st.session_state['user']
    nm = resolver_nome(u.email, u.user_metadata.get('nome'))
    
    st.markdown(f"""
    <div class='app-header'>
        <div class='logo-area'><div class='psi-icon'>Ψ</div> LocaPsico</div>
        <div style='font-size:14px; color:#64748b'>Olá, <b>{nm}</b></div>
    </div>
    """, unsafe_allow_html=True)

    opts = ["📅 Agenda", "📊 Painel"]
    if st.session_state.get('is_admin'): opts.append("⚙️ Admin")
    
    tabs = st.tabs(opts)
    
    with tabs[0]:
        sala = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
        render_calendar(sala)

    with tabs[1]:
        try:
            df = pd.DataFrame(supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").execute().data)
            c1, c2 = st.columns(2)
            c1.metric("Investido", f"R$ {df['valor_cobrado'].sum() if not df.empty else 0:.0f}")
            c2.metric("Reservas", len(df) if not df.empty else 0)
            
            st.write("Agendamentos Futuros")
            hj = str(datetime.date.today())
            futs = supabase.table("reservas").select("*").eq("user_id", u.id).eq("status", "confirmada").gte("data_reserva", hj).order("data_reserva").execute().data
            if futs:
                for r in futs:
                    dt = datetime.datetime.strptime(f"{r['data_reserva']} {r['hora_inicio']}", "%Y-%m-%d %H:%M:%S")
                    dif = (dt - datetime.datetime.now()).total_seconds()/3600
                    c_a, c_b = st.columns([3, 1])
                    c_a.write(f"📅 {r['data_reserva'][8:]}/{r['data_reserva'][5:7]} | {r['hora_inicio'][:5]}")
                    if dif > 24:
                        if c_b.button("X", key=f"cl_{r['id']}"):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", r['id']).execute()
                            st.rerun()
                    else: c_b.caption("🔒")
                    st.divider()
        except: pass

    if len(tabs) > 2:
        with tabs[2]: tela_admin()

    with st.sidebar:
        if st.button("Sair"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()

