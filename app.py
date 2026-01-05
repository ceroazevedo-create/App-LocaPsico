import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import base64
import calendar

# --- 1. CONFIGURAÇÃO VISUAL E CSS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3, p, div, span { font-family: 'Segoe UI', sans-serif; }
    
    .stButton>button {
        background-color: #0d9488 !important; color: white !important;
        border-radius: 6px; border: none; font-weight: 600;
    }
    .stButton>button:hover { background-color: #0f766e !important; }
    
    /* Botões de Navegação de Visualização (Dia/Sem/Mes) */
    .view-selector { display: flex; gap: 5px; justify-content: center; margin-bottom: 10px; }
    
    /* Header */
    .logo { font-size: 24px; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 10px; }
    .logo-icon { background-color: #0d9488; color: white; padding: 5px 10px; border-radius: 8px; }
    
    /* Cards */
    .stat-card {
        background-color: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02); border: 1px solid #e2e8f0;
        display: flex; align-items: center; gap: 15px;
    }
    .icon-box { width: 50px; height: 50px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; color: white; }
    .icon-green { background-color: #10b981; } 
    .icon-blue { background-color: #3b82f6; }  
    .stat-value { font-size: 24px; color: #0f172a; font-weight: 800; }

    /* AGENDA GERAL */
    .event-card { background-color: #d1fae5; border-left: 4px solid #0d9488; color: #064e3b; padding: 4px; font-size: 11px; font-weight: bold; border-radius: 4px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
    .blocked-cell { background-color: #fee2e2; border: 1px dashed #ef4444; height: 100%; opacity: 0.6; border-radius: 4px; }
    .day-header { text-align: center; font-weight: bold; color: #334155; padding-bottom: 10px; border-bottom: 2px solid #e2e8f0; }
    .time-col { color: #94a3b8; font-size: 12px; text-align: right; padding-right: 10px; margin-top: -10px;}
    
    /* MÊS VIEW */
    .month-day-box {
        border: 1px solid #e2e8f0;
        min-height: 80px;
        padding: 5px;
        background: white;
        font-size: 12px;
    }
    .month-day-header { font-weight: bold; color: #64748b; margin-bottom: 5px; }
    .month-event-dot {
        background-color: #d1fae5; color: #064e3b; 
        font-size: 10px; padding: 2px 4px; border-radius: 3px; 
        margin-bottom: 2px; white-space: nowrap; overflow: hidden;
    }
    
    .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except: return None

supabase = init_connection()

# --- 3. FUNÇÕES AUXILIARES ---
def resolver_nome_display(email, nome_meta=None, nome_banco=None):
    if email == "cesar_unib@msn.com": return "Cesar"
    if email == "thascaranalle@gmail.com": return "Thays"
    if nome_banco: return nome_banco
    if nome_meta: return nome_meta
    return email.split('@')[0].title()

def pegar_preco_atual():
    try:
        resp = supabase.table("configuracoes").select("preco_hora").limit(1).execute()
        if resp.data: return float(resp.data[0]['preco_hora'])
    except: pass
    return 32.00

def gerar_pdf_fatura(df, nome_usuario, mes_referencia):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 10, "LOCAPSICO - Fatura Mensal", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(50, 50, 50)
    pdf.ln(10)
    pdf.cell(0, 10, f"Profissional: {nome_usuario}", ln=True)
    pdf.cell(0, 10, f"Referencia: {mes_referencia}", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(240, 253, 250)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 10, "Data", 1, 0, 'C', True)
    pdf.cell(30, 10, "Sala", 1, 0, 'C', True)
    pdf.cell(30, 10, "Inicio", 1, 0, 'C', True)
    pdf.cell(30, 10, "Fim", 1, 0, 'C', True)
    pdf.cell(40, 10, "Valor", 1, 1, 'C', True)
    pdf.set_font("Arial", "", 10)
    total = 0
    for index, row in df.iterrows():
        data_fmt = pd.to_datetime(row['data_reserva']).strftime('%d/%m/%Y')
        val = float(row['valor_cobrado'])
        total += val
        pdf.cell(30, 10, data_fmt, 1, 0, 'C')
        pdf.cell(30, 10, str(row['sala_nome']), 1, 0, 'C')
        pdf.cell(30, 10, str(row['hora_inicio'])[:5], 1, 0, 'C')
        pdf.cell(30, 10, str(row['hora_fim'])[:5], 1, 0, 'C')
        pdf.cell(40, 10, f"R$ {val:.2f}", 1, 1, 'R')
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"TOTAL A PAGAR: R$ {total:.2f}", ln=True, align="R")
    return pdf.output(dest='S').encode('latin-1')

# --- 4. CONTROLE DE ESTADO E DATA ---
if 'data_referencia' not in st.session_state:
    st.session_state['data_referencia'] = datetime.date.today()
if 'view_mode' not in st.session_state:
    st.session_state['view_mode'] = 'SEMANA'

def navegar_data(direcao):
    modo = st.session_state['view_mode']
    delta = 0
    if modo == 'DIA': delta = 1
    elif modo == 'SEMANA': delta = 7
    elif modo == 'MÊS': delta = 30 
    
    if direcao == 'anterior':
        st.session_state['data_referencia'] -= timedelta(days=delta)
    else:
        st.session_state['data_referencia'] += timedelta(days=delta)

# --- 5. RENDERIZAÇÃO DA GRADE ---
def buscar_reservas(sala, data_inicio, data_fim):
    try:
        resp = supabase.table("reservas").select("*")\
            .eq("sala_nome", sala)\
            .eq("status", "confirmada")\
            .gte("data_reserva", str(data_inicio))\
            .lte("data_reserva", str(data_fim))\
            .execute()
        return resp.data
    except: return []

def renderizar_calendario_view(sala_selecionada, is_admin=False):
    view_mode = st.session_state['view_mode']
    data_ref = st.session_state['data_referencia']
    agora = datetime.datetime.now()

    if view_mode == 'DIA':
        inicio_periodo = data_ref
        fim_periodo = data_ref
        dias_para_mostrar = [data_ref]
        col_ratios = [0.5, 4]
        
    elif view_mode == 'SEMANA':
        inicio_periodo = data_ref - timedelta(days=data_ref.weekday())
        fim_periodo = inicio_periodo + timedelta(days=6)
        dias_para_mostrar = [inicio_periodo + timedelta(days=i) for i in range(7)]
        col_ratios = [0.5] + [1]*7

    elif view_mode == 'MÊS':
        ano, mes = data_ref.year, data_ref.month
        num_dias = calendar.monthrange(ano, mes)[1]
        inicio_periodo = datetime.date(ano, mes, 1)
        fim_periodo = datetime.date(ano, mes, num_dias)
    
    reservas = buscar_reservas(sala_selecionada, inicio_periodo, fim_periodo)
    
    mapa = {}
    for r in reservas:
        d = r['data_reserva']
        h = r['hora_inicio']
        if d not in mapa: mapa[d] = {}
        if view_mode == 'MÊS':
            if 'lista' not in mapa[d]: mapa[d]['lista'] = []
            mapa[d]['lista'].append(r)
        else:
            mapa[d][h] = r

    # RENDERIZAÇÃO
    if view_mode == 'MÊS':
        dias_semana_nome = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"]
        cols = st.columns(7)
        for i, d_nome in enumerate(dias_semana_nome):
            cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#64748b;'>{d_nome}</div>", unsafe_allow_html=True)
        
        cal_matrix = calendar.monthcalendar(data_ref.year, data_ref.month)
        
        for semana in cal_matrix:
            cols = st.columns(7)
            for i, dia_num in enumerate(semana):
                if dia_num == 0:
                    cols[i].markdown("<div class='month-day-box' style='background:#f8f9fa;'></div>", unsafe_allow_html=True)
                else:
                    data_atual = datetime.date(data_ref.year, data_ref.month, dia_num)
                    data_str = str(data_atual)
                    html_content = f"<div class='month-day-header'>{dia_num}</div>"
                    
                    if data_str in mapa and 'lista' in mapa[data_str]:
                        for evt in mapa[data_str]['lista']:
                            nm = resolver_nome_display(evt['email_profissional'], nome_banco=evt.get('nome_profissional'))
                            hora_curta = evt['hora_inicio'][:5]
                            html_content += f"<div class='month-event-dot' title='{hora_curta} - {nm}'>{hora_curta} {nm}</div>"
                    
                    cols[i].markdown(f"<div class='month-day-box'>{html_content}</div>", unsafe_allow_html=True)

    else:
        cols_header = st.columns(col_ratios)
        cols_header[0].write("")
        for i, data_atual in enumerate(dias_para_mostrar):
            dia_str = f"{data_atual.strftime('%a').upper()} <br> <span style='font-size:18px'>{data_atual.day:02d}</span>"
            style = "color: #ef4444;" if data_atual.weekday() == 6 else ("color: #0d9488; border-bottom-color: #0d9488;" if data_atual == datetime.date.today() else "")
            cols_header[i+1].markdown(f"<div class='day-header' style='{style}'>{dia_str}</div>", unsafe_allow_html=True)
        st.markdown("---")
        horarios = [f"{h:02d}:00:00" for h in range(7, 23)] 
        for hora in horarios:
            cols = st.columns(col_ratios)
            cols[0].markdown(f"<div class='time-col'>{hora[:5]}</div>", unsafe_allow_html=True)
            for i, data_atual in enumerate(dias_para_mostrar):
                data_str = str(data_atual)
                hora_int = int(hora[:2])
                dt_slot = datetime.datetime.combine(data_atual, datetime.time(hora_int, 0))
                reserva = mapa.get(data_str, {}).get(hora)
                cell = cols[i+1].empty()
                if reserva:
                    nm = resolver_nome_display(reserva.get('email_profissional',''), nome_banco=reserva.get('nome_profissional'))
                    cell.markdown(f"<div class='event-card' title='{nm}'>👤 {nm}</div>", unsafe_allow_html=True)
                elif data_atual.weekday() == 6 or dt_slot < agora:
                    cell.markdown("<div class='blocked-cell'></div>", unsafe_allow_html=True)
                else:
                    cell.markdown("<div style='height: 30px; border-left: 1px solid #f1f5f9;'></div>", unsafe_allow_html=True)

# --- 6. TELA LOGIN ---
def login_screen():
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<br><br><h1 style='text-align: center; color: #0d9488;'>Ψ LocaPsico</h1><p style='text-align: center;'>Gestão de Espaços Terapêuticos</p>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["JÁ TENHO CONTA", "CRIAR NOVA CONTA"])
        with tab1:
            with st.form("form_login"):
                email = st.text_input("Email", key="login_email")
                senha = st.text_input("Senha", type="password", key="login_pass")
                if st.form_submit_button("Entrar no Sistema"):
                    try:
                        user = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        st.session_state['user'] = user.user
                        st.session_state['is_admin'] = (email == "admin@admin.com.br")
                        st.rerun()
                    except: st.error("Email ou senha incorretos.")
        with tab2:
            with st.form("form_cadastro"):
                new_nome = st.text_input("Seu Nome Completo")
                new_email = st.text_input("Seu Email")
                new_senha = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    if len(new_senha) < 6: st.warning("Senha curta.")
                    else:
                        try:
                            response = supabase.auth.sign_up({
                                "email": new_email, "password": new_senha,
                                "options": { "data": { "nome": new_nome } }
                            })
                            if response.user: st.success("Conta criada! Faça login.")
                        except Exception as e: st.error(f"Erro: {e}")

# --- 7. APP PRINCIPAL ---
def main():
    c1, c2, c3 = st.columns([2, 4, 2])
    with c1: st.markdown("<div class='logo'><span class='logo-icon'>L</span> LOCAPSICO</div>", unsafe_allow_html=True)
    with c2:
        opcoes = ["AGENDA", "MEU PAINEL", "⚙️ GESTÃO"] if st.session_state.get('is_admin') else ["AGENDA", "MEU PAINEL"]
        nav = st.radio("menu", opcoes, horizontal=True, label_visibility="collapsed")
    with c3:
        if 'user' in st.session_state:
            email_atual = st.session_state['user'].email
            meta_nome = st.session_state['user'].user_metadata.get('nome')
            nome_topo = resolver_nome_display(email_atual, nome_meta=meta_nome)
            role = "ADMINISTRADOR" if st.session_state.get('is_admin') else "TERAPEUTA"
            st.markdown(f"<div style='text-align:right; line-height:1.2;'><span style='font-weight:800; color:#0f172a;'>{nome_topo.upper()}</span><br><span style='color:#0d9488; font-size:11px; font-weight:bold;'>{role}</span></div>", unsafe_allow_html=True)
            if st.button("Sair", key="out"):
                supabase.auth.sign_out()
                st.session_state.clear()
                st.rerun()

    if 'user' not in st.session_state:
        login_screen()
        return

    # --- TELA 1: AGENDA ---
    if nav == "AGENDA":
        st.markdown("<br>", unsafe_allow_html=True)
        sala = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True, label_visibility="collapsed")
        st.markdown("---")
        
        c_nav1, c_nav2, c_nav3 = st.columns([1, 6, 2])
        with c_nav1: 
            if st.button("◀", key="p"): navegar_data('anterior')
        with c_nav2:
            dt_ref = st.session_state['data_referencia']
            col_b1, col_b2, col_b3, col_lbl = st.columns([1,1,1,3])
            def set_view(v): st.session_state['view_mode'] = v
            
            style_dia = "primary" if st.session_state['view_mode'] == 'DIA' else "secondary"
            style_sem = "primary" if st.session_state['view_mode'] == 'SEMANA' else "secondary"
            style_mes = "primary" if st.session_state['view_mode'] == 'MÊS' else "secondary"
            
            with col_b1: 
                if st.button("DIA", type=style_dia, use_container_width=True): set_view('DIA')
            with col_b2: 
                if st.button("SEM", type=style_sem, use_container_width=True): set_view('SEMANA')
            with col_b3: 
                if st.button("MÊS", type=style_mes, use_container_width=True): set_view('MÊS')
            
            with col_lbl:
                mes_str = dt_ref.strftime('%B').capitalize()
                if st.session_state['view_mode'] == 'SEMANA':
                    ini = dt_ref - timedelta(days=dt_ref.weekday())
                    fim = ini + timedelta(days=6)
                    st.markdown(f"<h4 style='margin:0; text-align:right'>{ini.day} - {fim.day} {mes_str}</h4>", unsafe_allow_html=True)
                elif st.session_state['view_mode'] == 'DIA':
                    st.markdown(f"<h4 style='margin:0; text-align:right'>{dt_ref.day} de {mes_str}</h4>", unsafe_allow_html=True)
                else: 
                    st.markdown(f"<h4 style='margin:0; text-align:right'>{mes_str} {dt_ref.year}</h4>", unsafe_allow_html=True)

        with c_nav3: 
            if st.button("▶", key="n"): navegar_data('proximo')
            
        renderizar_calendario_view(sala, is_admin=st.session_state.get('is_admin'))
        
        with st.expander("➕ NOVO AGENDAMENTO", expanded=False):
            with st.form("new"):
                ca, cb = st.columns(2)
                dt = ca.date_input("Data", value=st.session_state['data_referencia'], min_value=datetime.date.today())
                hr = cb.selectbox("Horário", [f"{h:02d}:00" for h in range(7, 23)])
                if st.form_submit_button("Confirmar"):
                    try:
                        agora = datetime.datetime.now()
                        hr_int = int(hr[:2])
                        dt_check = datetime.datetime.combine(dt, datetime.time(hr_int, 0))
                        
                        if not st.session_state.get('is_admin'):
                            if dt.weekday() == 6: st.error("Domingo fechado."); st.stop()
                            if dt_check < agora: st.error("Passado bloqueado."); st.stop()

                        h_fim = f"{hr_int+1:02d}:00"
                        email = st.session_state['user'].email
                        nome = resolver_nome_display(email, nome_meta=st.session_state['user'].user_metadata.get('nome'))
                        
                        dados = {
                            "sala_nome": sala, "data_reserva": str(dt), "hora_inicio": hr, "hora_fim": h_fim,
                            "user_id": st.session_state['user'].id, "email_profissional": email,
                            "nome_profissional": nome, "valor_cobrado": pegar_preco_atual(), "status": "confirmada"
                        }
                        supabase.table("reservas").insert(dados).execute()
                        st.success("Reservado!"); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

    # --- TELA 2: MEU PAINEL (CORRIGIDO PARA SUBTRAIR) ---
    elif nav == "MEU PAINEL":
        user_id = st.session_state['user'].id
        email = st.session_state['user'].email
        nome = resolver_nome_display(email, nome_meta=st.session_state['user'].user_metadata.get('nome'))
        
        inv, total = 0.0, 0
        try:
            # SÓ PEGA STATUS 'confirmada'. Ao cancelar, o status vira 'cancelada' e some daqui.
            resp = supabase.table("reservas").select("valor_cobrado").eq("user_id", user_id).eq("status", "confirmada").execute()
            df = pd.DataFrame(resp.data)
            
            if not df.empty:
                inv = df['valor_cobrado'].sum()
                total = len(df) # Conta apenas as confirmadas
            else:
                inv = 0.0
                total = 0
        except: pass

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1.5, 1, 1])
        c1.markdown(f"<h1 style='color:#0f172a;'>Olá, {nome}!</h1>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-card'><div class='icon-box icon-green'>$</div><div><div class='stat-label'>Investido</div><div class='stat-value'>R$ {inv:.0f}</div></div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat-card'><div class='icon-box icon-blue'>#</div><div><div class='stat-label'>Reservas</div><div class='stat-value'>{total}</div></div></div>", unsafe_allow_html=True)
        
        st.markdown("<br><h4>Minhas Reservas Ativas</h4>", unsafe_allow_html=True)
        
        agora = datetime.datetime.now()
        try:
            resp_futuro = supabase.table("reservas").select("*").eq("user_id", user_id).eq("status", "confirmada").gte("data_reserva", str(datetime.date.today())).order("data_reserva").execute()
            df_f = pd.DataFrame(resp_futuro.data)
            if not df_f.empty:
                for idx, row in df_f.iterrows():
                    dt_evento = datetime.datetime.strptime(f"{row['data_reserva']} {row['hora_inicio']}", "%Y-%m-%d %H:%M:%S")
                    diff = dt_evento - agora
                    horas_restantes = diff.total_seconds() / 3600
                    c_info, c_canc = st.columns([4, 1])
                    with c_info: st.write(f"📅 **{row['data_reserva']}** | ⏰ {row['hora_inicio']} | {row['sala_nome']}")
                    with c_canc:
                        if horas_restantes > 24:
                            if st.button("Cancelar", key=f"canc_{row['id']}"):
                                supabase.table("reservas").update({"status": "cancelada"}).eq("id", row['id']).execute()
                                st.rerun()
                        elif horas_restantes > 0: st.caption("🔒 < 24h")
                        else: st.caption("Concluído")
                    st.divider()
            else: st.info("Sem agendamentos futuros.")
        except: pass

    # --- TELA 3: GESTÃO (ADMIN) ---
    elif nav == "⚙️ GESTÃO":
        st.markdown("<br><h2>Gestão Administrativa</h2>", unsafe_allow_html=True)
        tab_config, tab_relat, tab_canc = st.tabs(["💰 Preço", "📄 Relatórios (Faturamento)", "❌ Cancelamentos"])
        
        with tab_config:
            novo = st.number_input("Preço Hora", value=pegar_preco_atual())
            if st.button("Salvar Preço"):
                try: 
                    supabase.table("configuracoes").update({"preco_hora": novo}).gt("id", 0).execute()
                    st.success("Atualizado!")
                except: pass
                
        with tab_relat:
            st.write("Selecione o Mês para ver o faturamento.")
            mes_sel = st.selectbox("Mês de Referência", ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])
            try:
                ano, mes = map(int, mes_sel.split('-'))
                ultimo_dia = calendar.monthrange(ano, mes)[1]
                dt_ini = f"{ano}-{mes:02d}-01"
                dt_fim = f"{ano}-{mes:02d}-{ultimo_dia}"

                r_total_mes = supabase.table("reservas").select("valor_cobrado").eq("status", "confirmada").gte("data_reserva", dt_ini).lte("data_reserva", dt_fim).execute()
                df_tm = pd.DataFrame(r_total_mes.data)
                total_mes_geral = df_tm['valor_cobrado'].sum() if not df_tm.empty else 0.0
                st.metric(f"Faturamento Total ({mes_sel})", f"R$ {total_mes_geral:.2f}")
                st.divider()
            except Exception as e: st.error(f"Erro ao calcular total: {e}")

            st.write("Baixar PDF Individual:")
            users_resp = supabase.table("reservas").select("email_profissional, nome_profissional").execute()
            df_u = pd.DataFrame(users_resp.data)
            if not df_u.empty:
                df_u['display'] = df_u.apply(lambda x: resolver_nome_display(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                lista_users = df_u['display'].unique()
                user_sel = st.selectbox("Profissional", lista_users)
                if st.button("Gerar Relatório Individual"):
                    try:
                        r_fatura = supabase.table("reservas").select("*").eq("status", "confirmada").gte("data_reserva", dt_ini).lte("data_reserva", dt_fim).execute()
                        df_fat = pd.DataFrame(r_fatura.data)
                        if not df_fat.empty:
                            df_fat['nome_calc'] = df_fat.apply(lambda x: resolver_nome_display(x['email_profissional'], nome_banco=x['nome_profissional']), axis=1)
                            df_final = df_fat[df_fat['nome_calc'] == user_sel]
                            if not df_final.empty:
                                st.dataframe(df_final[["data_reserva", "sala_nome", "hora_inicio", "valor_cobrado"]])
                                pdf_bytes = gerar_pdf_fatura(df_final, user_sel, mes_sel)
                                b64 = base64.b64encode(pdf_bytes).decode()
                                href = f'<a href="data:application/octet-stream;base64,{b64}" download="Fatura_{user_sel}_{mes_sel}.pdf"><b>📥 BAIXAR PDF</b></a>'
                                st.markdown(href, unsafe_allow_html=True)
                            else: st.warning("Sem dados.")
                        else: st.warning("Sem dados.")
                    except Exception as e: st.error(f"Erro ao gerar: {e}")
            
        with tab_canc:
            st.write("Lista Global (Admin)")
            try:
                res_all = supabase.table("reservas").select("*").eq("status", "confirmada").order("data_reserva", desc=True).limit(50).execute()
                df_all = pd.DataFrame(res_all.data)
                if not df_all.empty:
                    for i, r in df_all.iterrows():
                        nm = resolver_nome_display(r['email_profissional'], nome_banco=r.get('nome_profissional'))
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"{r['data_reserva']} | {r['sala_nome']} | {nm}")
                        if c2.button("Cancelar", key=f"adm_del_{r['id']}"):
                            supabase.table("reservas").update({"status": "cancelada"}).eq("id", r['id']).execute()
                            st.rerun()
                        st.divider()
            except: pass

if __name__ == "__main__":
    main()

