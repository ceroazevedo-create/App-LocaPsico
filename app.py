import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import base64
import calendar
import plotly.express as px

# --- 1. CONFIGURAÇÃO E CSS (VISUAL MODERNO) ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }

    /* BOTÕES */
    .stButton>button {
        border-radius: 8px; font-weight: 600; border: none; transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stHorizontalBlock"] button:hover { transform: translateY(-2px); }

    /* HEADER */
    .app-header {
        display: flex; justify-content: space-between; align-items: center;
        background: white; padding: 15px 30px; border-radius: 12px;
        margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .logo-area { font-size: 22px; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 10px; }
    .psi-icon { background: #0d9488; color: white; width: 35px; height: 35px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }

    /* CALENDÁRIO: GERAL */
    .cal-container { background: white; border-radius: 12px; padding: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    
    /* CALENDÁRIO: SEMANA/DIA */
    .day-col-header { text-align: center; padding: 10px 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 10px; }
    .day-name { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .day-num { font-size: 20px; font-weight: 800; color: #1e293b; }
    .day-num.today { color: #0d9488; }
    
    .time-slot-row { border-bottom: 1px solid #f1f5f9; min-height: 50px; display: flex; align-items: center; }
    .time-label { font-size: 11px; color: #94a3b8; font-weight: 600; padding-right: 10px; text-align: right; width: 100%; }
    
    /* EVENT CHIPS */
    .evt-chip {
        background: #ccfbf1; border-left: 3px solid #0d9488; color: #115e59;
        font-size: 11px; font-weight: 600; padding: 4px 8px; border-radius: 6px;
        margin: 2px 0; cursor: default; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .evt-chip:hover { background: #99f6e4; }

    /* CALENDÁRIO: MÊS */
    .month-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; }
    .month-day {
        background: white; border: 1px solid #e2e8f0; min-height: 100px; padding: 5px; border-radius: 6px;
        display: flex; flex-direction: column; gap: 3px;
    }
    .month-day:hover { border-color: #cbd5e1; }
    .month-day-header { font-weight: 700; font-size: 12px; color: #475569; margin-bottom: 4px; }
    .month-evt-dot {
        font-size: 10px; background: #0f766e; color: white; padding: 2px 4px; border-radius: 4px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    
    /* BLOQUEIOS */
    .blocked-slot { 
        background: repeating-linear-gradient(45deg, #fef2f2, #fef2f2 10px, #fee2e2 10px, #fee2e2 20px); 
        height: 45px; width: 100%; border-radius: 4px; opacity: 0.5;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. LÓGICA DE DADOS ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if email == "cesar_unib@msn.com": return "Cesar"
    if email == "thascaranalle@gmail.com": return "Thays"
    return nome_banco or nome_meta or email.split('@')[0].title()

def get_preco():
    try:
        r = supabase.table("configuracoes").select("preco_hora").limit(1).execute()
        return float(r.data[0]['preco_hora']) if r.data else 32.00
    except: return 32.00

# --- 4. CONTROLE DE ESTADO ---
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'SEMANA'

def navegar(direcao):
    mode = st.session_state.view_mode
    delta = 0
    if mode == 'DIA': delta = 1
    elif mode == 'SEMANA': delta = 7
    elif mode == 'MÊS': delta = 30
    
    if direcao == 'prev': st.session_state.data_ref -= timedelta(days=delta)
    else: st.session_state.data_ref += timedelta(days=delta)

# --- 5. MODAL AGENDAMENTO (REGRAS DE HORÁRIO AQUI) ---
@st.dialog("Novo Agendamento")
def modal_agendamento(sala_padrao, data_sugerida):
    st.write("Preencha os detalhes da reserva.")
    c1, c2 = st.columns(2)
    
    # 1. Seleção de Data
    dt = c1.date_input("Data", value=data_sugerida, min_value=datetime.date.today())
    
    # 2. Definição Dinâmica de Horários baseada no Dia da Semana
    # 0=Seg, 5=Sáb, 6=Dom
    dia_sem = dt.weekday()
    
    if dia_sem == 6: # Domingo
        lista_horas = []
        st.warning("A clínica encerra aos Domingos.")
    elif dia_sem == 5: # Sábado (Até as 13:00, terminando as 14:00)
        lista_horas = [f"{h:02d}:00" for h in range(7, 14)] # 07, 08... 13
        st.info("Sábados: Atendimento até às 14:00.")
    else: # Seg-Sex (Até as 21:00, terminando as 22:00)
        lista_horas = [f"{h:02d}:00" for h in range(7, 22)] # 07, 08... 21
    
    # Selectbox com a lista filtrada
    hr = c2.selectbox("Horário", lista_horas, disabled=(len(lista_horas)==0))
    
    ignore = st.checkbox("Admin: Ignorar bloqueios") if st.session_state.get('is_admin') else False

    if st.button("Confirmar Reserva", use_container_width=True, disabled=(len(lista_horas)==0 and not ignore)):
        # Se for admin ignorando, permite qualquer hora
        if ignore: 
            hr_final = hr if hr else "07:00" # fallback
        else: 
            hr_final = hr

        agora = datetime.datetime.now()
        dt_check = datetime.datetime.combine(dt, datetime.time(int(hr_final[:2]), 0))
        
        erro = None
        if not ignore:
            if dia_sem == 6: erro = "Fechado aos domingos."
            elif dt_check < agora: erro = "Data no passado."
        
        if erro: st.error(erro)
        else:
            try:
                chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao)\
                    .eq("data_reserva", str(dt)).eq("hora_inicio", hr_final).eq("status", "confirmada").execute()
                if chk.data:
                    st.error("Horário já reservado!")
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

# --- 6. RENDER CALENDÁRIO (VISUALIZAÇÃO) ---
def render_calendar(sala):
    # Header Navegação
    col_nav_L, col_nav_C, col_nav_R = st.columns([1, 4, 1])
    
    with col_nav_L:
        if st.button("◀", use_container_width=True): navegar('prev'); st.rerun()
    with col_nav_R:
        if st.button("▶", use_container_width=True): navegar('next'); st.rerun()
        
    with col_nav_C:
        c_v1, c_v2, c_v3 = st.columns(3)
        mode = st.session_state.view_mode
        def set_mode(m): st.session_state.view_mode = m
        
        bt_d = "primary" if mode == 'DIA' else "secondary"
        bt_s = "primary" if mode == 'SEMANA' else "secondary"
        bt_m = "primary" if mode == 'MÊS' else "secondary"
        
        with c_v1: 
            if st.button("Dia", type=bt_d, use_container_width=True): set_mode('DIA'); st.rerun()
        with c_v2: 
            if st.button("Semana", type=bt_s, use_container_width=True): set_mode('SEMANA'); st.rerun()
        with c_v3: 
            if st.button("Mês", type=bt_m, use_container_width=True): set_mode('MÊS'); st.rerun()
            
        ref = st.session_state.data_ref
        mes_str = ref.strftime("%B").capitalize()
        label = f"{mes_str} {ref.year}"
        if mode == 'SEMANA':
            ini = ref - timedelta(days=ref.weekday())
            fim = ini + timedelta(days=6)
            label = f"{ini.day} - {fim.day} {mes_str}"
        elif mode == 'DIA':
            label = f"{ref.day} de {mes_str}"
            
        st.markdown(f"<div style='text-align:center; font-weight:800; color:#334155; margin-top:5px'>{label}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Preparação Dados
    if mode == 'MÊS':
        ano, mes = ref.year, ref.month
        last_day = calendar.monthrange(ano, mes)[1]
        d_start, d_end = datetime.date(ano, mes, 1), datetime.date(ano, mes, last_day)
    elif mode == 'SEMANA':
        d_start = ref - timedelta(days=ref.weekday())
        d_end = d_start + timedelta(days=6)
    else: # DIA
        d_start = d_end = ref

    reservas = []
    try:
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).eq("status", "confirmada")\
            .gte("data_reserva", str(d_start)).lte("data_reserva", str(d_end)).execute()
        reservas = r.data
    except: pass

    mapa = {}
    for item in reservas:
        d = item['data_reserva']
        if mode == 'MÊS':
            if d not in mapa: mapa[d] = []
            mapa[d].append(item)
        else:
            if d not in mapa: mapa[d] = {}
            mapa[d][item['hora_inicio']] = item

    # --- RENDER VISUAL ---
    
    # MODO MÊS
    if mode == 'MÊS':
        cols = st.columns(7)
        for i, d in enumerate(['DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB']):
            cols[i].markdown(f"<div style='text-align:center; font-size:11px; font-weight:bold; color:#94a3b8'>{d}</div>", unsafe_allow_html=True)
        
        cal_mat = calendar.monthcalendar(ref.year, ref.month)
        for semana in cal_mat:
            cols = st.columns(7)
            for i, dia in enumerate(semana):
                if dia == 0:
                    cols[i].markdown("<div style='height:80px; background:#f8fafc; border:1px solid #f1f5f9; border-radius:6px'></div>", unsafe_allow_html=True)
                else:
                    dt_atual = datetime.date(ref.year, ref.month, dia)
                    dt_str = str(dt_atual)
                    
                    html_evts = ""
                    if dt_str in mapa:
                        for evt in mapa[dt_str]:
                            nm = resolver_nome(evt['email_profissional'], nome_banco=evt.get('nome_profissional'))
                            html_evts += f"<div class='month-evt-dot' title='{evt['hora_inicio'][:5]} - {nm}'>{evt['hora_inicio'][:5]} {nm}</div>"
                    
                    bg_color = "#f0fdfa" if dt_atual == datetime.date.today() else "white"
                    border_color = "#0d9488" if dt_atual == datetime.date.today() else "#e2e8f0"
                    
                    cols[i].markdown(f"""
                    <div class='month-day' style='background:{bg_color}; border-color:{border_color}'>
                        <div class='month-day-header'>{dia}</div>
                        {html_evts}
                    </div>
                    """, unsafe_allow_html=True)

    # MODO DIA / SEMANA
    else:
        if mode == 'SEMANA':
            dias_visiveis = [d_start + timedelta(days=i) for i in range(7)]
            razao_cols = [0.5] + [1]*7
        else: # DIA
            dias_visiveis = [d_start]
            razao_cols = [0.5, 6]

        c_head = st.columns(razao_cols)
        c_head[0].write("")
        d_names = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
        
        for i, d in enumerate(dias_visiveis):
            wd = d.weekday()
            is_today = d == datetime.date.today()
            cor_num = "today" if is_today else ""
            txt_cor = "#ef4444" if wd == 6 else "#64748b"
            
            c_head[i+1].markdown(f"""
            <div class='day-col-header'>
                <div class='day-name' style='color:{txt_cor}'>{d_names[wd]}</div>
                <div class='day-num {cor_num}'>{d.day}</div>
            </div>
            """, unsafe_allow_html=True)

        # RANGE VISUAL DO CALENDÁRIO: 07:00 AS 21:00 (Para mostrar até 22h, o ultimo slot começa as 21)
        # O pedido foi: Semanal até 21h (termina 22h) e Sábado até 13h (termina 14h)
        # O grid deve mostrar o máximo (até 21h). Bloqueamos visualmente o que não pode.
        horarios = [f"{h:02d}:00:00" for h in range(7, 22)] 
        
        for hora in horarios:
            c_slots = st.columns(razao_cols)
            c_slots[0].markdown(f"<div class='time-label'>{hora[:5]}</div>", unsafe_allow_html=True)
            
            for i, d in enumerate(dias_visiveis):
                d_str = str(d)
                reserva = mapa.get(d_str, {}).get(hora)
                container = c_slots[i+1].container()
                
                if reserva:
                    nm = resolver_nome(reserva['email_profissional'], nome_banco=reserva.get('nome_profissional'))
                    container.markdown(f"<div class='evt-chip' title='{nm}'>👤 {nm}</div>", unsafe_allow_html=True)
                else:
                    # LÓGICA DE BLOQUEIO VISUAL
                    dt_slot = datetime.datetime.combine(d, datetime.time(int(hora[:2]), 0))
                    
                    # 1. Domingo (wd=6) -> Bloqueado
                    # 2. Passado -> Bloqueado
                    # 3. Sábado (wd=5) e hora > 13 -> Bloqueado
                    hora_int = int(hora[:2])
                    bloqueado_sabado = (d.weekday() == 5 and hora_int > 13)
                    
                    if d.weekday() == 6 or dt_slot < datetime.datetime.now() or bloqueado_sabado:
                        container.markdown("<div class='blocked-slot'></div>", unsafe_allow_html=True)
                    else:
                        container.markdown("<div style='height:45px'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Novo Agendamento", type="primary", use_container_width=True):
        modal_agendamento(sala, st.session_state.data_ref)

# --- 7. TELA ADMIN ---
def tela_admin():
    st.markdown("### ⚙️ Painel Administrativo")
    t1, t2 = st.tabs(["Dashboard & Preço", "Gerenciar Tudo"])
    
    with t1:
        try:
            df = pd.DataFrame(supabase.table("reservas").select("*").eq("status", "confirmada").execute().data)
            receita = df['valor_cobrado'].sum() if not df.empty else 0
            horas = len(df) if not df.empty else 0
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Receita Total", f"R$ {receita:.0f}")
            k2.metric("Horas Locadas", horas)
            k3.metric("Preço Atual", f"R$ {get_preco():.2f}")
            
            st.divider()
            
            c_p, c_g = st.columns([1, 2])
            with c_p:
                nv = st.number_input("Novo Valor Hora", value=get_preco())
                if st.button("Salvar Valor"):
                    supabase.table("configuracoes").update({"preco_hora": nv}).gt("id", 0).execute()
                    st.toast("Preço atualizado!")
                    st.rerun()
            with c_g:
                if not df.empty:
                    fig = px.pie(df, names='sala_nome', title="Ocupação por Sala", color_discrete_sequence=['#0d9488', '#3b82f6'])
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, use_container_width=True)
        except: pass

    with t2:
        st.write("Lista Global")
        try:
            q = st.text_input("Buscar (Nome/Email)")
            res = supabase.table("reservas").select("*").eq("status", "confirmada").order("data_reserva", desc=True).limit(50).execute()
            df_r = pd.DataFrame(res.data)
            
            if not df_r.empty:
                if q: 
                    df_r = df_r[df_r['email_profissional'].str.contains(q, case=False)]
                
                for _, r in df_r.iterrows():
                    nm = resolver_nome(r['email_profissional'], nome_banco=r.get('nome_profissional'))
                    c1, c2, c3 = st.columns([2, 4, 2])
                    c1.write(f"📅 {r['data_reserva']}")
                    c2.write(f"👤 {nm} ({r['sala_nome']})")
                    if c3.button("Cancelar", key=f"adm_{r['id']}"):
                        supabase.table("reservas").update({"status": "cancelada"}).eq("id", r['id']).execute()
                        st.rerun()
                    st.divider()
        except: pass

# --- 8. APP PRINCIPAL ---
def main():
    if 'user' not in st.session_state:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.markdown("<br><br><div style='text-align:center'><div class='psi-icon' style='width:60px;height:60px;margin:auto;font-size:30px'>Ψ</div><h1 style='color:#0f172a'>LocaPsico</h1></div>", unsafe_allow_html=True)
            t_log, t_cad = st.tabs(["Entrar", "Cadastrar"])
            with t_log:
                e = st.text_input("Email")
                s = st.text_input("Senha", type="password")
                if st.button("Acessar", use_container_width=True):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": e, "password": s})
                        st.session_state['user'] = u.user
                        st.session_state['is_admin'] = (e == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Erro login")
            with t_cad:
                n = st.text_input("Nome")
                em = st.text_input("Email Reg")
                ps = st.text_input("Senha Reg", type="password")
                if st.button("Criar Conta", use_container_width=True):
                    try:
                        supabase.auth.sign_up({"email": em, "password": ps, "options": {"data": {"nome": n}}})
                        st.success("Criado! Faça login.")
                    except: st.error("Erro cadastro")
        return

    # LOGADO
    user = st.session_state['user']
    nome_topo = resolver_nome(user.email, user.user_metadata.get('nome'))
    
    st.markdown(f"""
    <div class='app-header'>
        <div class='logo-area'><div class='psi-icon'>Ψ</div> LOCAPSICO</div>
        <div style='color:#64748b'>Olá, <b>{nome_topo}</b></div>
    </div>
    """, unsafe_allow_html=True)

    tabs_labels = ["📅 AGENDA", "📊 MEU PAINEL"]
    if st.session_state.get('is_admin'): tabs_labels.append("⚙️ ADMIN")
    
    tabs = st.tabs(tabs_labels)
    
    with tabs[0]:
        c_sala, c_cal = st.columns([1, 4])
        with c_sala:
            st.markdown("#### Selecione a Sala")
            sala = st.radio("S", ["Sala 1", "Sala 2"], label_visibility="collapsed")
            st.info("Sábados até às 14h.\nSemana até às 22h.")
        with c_cal:
            render_calendar(sala)

    with tabs[1]:
        try:
            df = pd.DataFrame(supabase.table("reservas").select("*").eq("user_id", user.id).eq("status", "confirmada").execute().data)
            
            c1, c2 = st.columns(2)
            val = df['valor_cobrado'].sum() if not df.empty else 0
            qtd = len(df) if not df.empty else 0
            
            c1.metric("Total Investido", f"R$ {val:.0f}")
            c2.metric("Reservas Ativas", qtd)
            
            st.markdown("### 🗓️ Próximos Agendamentos")
            hoje = str(datetime.date.today())
            futs = supabase.table("reservas").select("*").eq("user_id", user.id).eq("status", "confirmada").gte("data_reserva", hoje).order("data_reserva").execute().data
            
            if futs:
                for r in futs:
                    dt_obj = datetime.datetime.strptime(f"{r['data_reserva']} {r['hora_inicio']}", "%Y-%m-%d %H:%M:%S")
                    diff = (dt_obj - datetime.datetime.now()).total_seconds()/3600
                    
                    cc1, cc2, cc3 = st.columns([1, 3, 1])
                    cc1.write(f"📅 **{r['data_reserva'][8:]}/{r['data_reserva'][5:7]}**")
                    cc2.write(f"{r['sala_nome']} às {r['hora_inicio'][:5]}")
                    
                    if diff > 24:
                        if cc3.button("Cancelar", key=f"uc_{r['id']}"):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", r['id']).execute()
                            st.toast("Cancelado!")
                            st.rerun()
                    else: cc3.caption("🔒 < 24h")
                    st.divider()
            else: st.info("Sem agendamentos futuros.")
        except: pass

    if len(tabs) > 2:
        with tabs[2]: tela_admin()

    with st.sidebar:
        if st.button("Sair da Conta"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()

