import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta

# --- 1. CONFIGURAÇÃO VISUAL E CSS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

st.markdown("""
<style>
    /* Fundo Geral */
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3, p, div, span { font-family: 'Segoe UI', sans-serif; }
    
    /* Botões Principais (Teal) */
    .stButton>button {
        background-color: #0d9488 !important; 
        color: white !important;
        border-radius: 6px; border: none; font-weight: 600;
    }
    .stButton>button:hover { background-color: #0f766e !important; }
    
    /* Header Personalizado */
    .header-container {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 20px; background-color: white; border-bottom: 1px solid #e5e7eb; margin-bottom: 20px;
    }
    .logo { font-size: 24px; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 10px; }
    .logo-icon { background-color: #0d9488; color: white; padding: 5px 10px; border-radius: 8px; }
    
    /* CARDS DO PAINEL (MÉTRICAS) */
    .stat-card {
        background-color: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02); border: 1px solid #e2e8f0;
        display: flex; align-items: center; gap: 15px;
    }
    .icon-box {
        width: 50px; height: 50px; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px; color: white;
    }
    .icon-green { background-color: #10b981; } /* Verde Dinheiro */
    .icon-blue { background-color: #3b82f6; }  /* Azul Relógio */
    
    .stat-label { font-size: 12px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-value { font-size: 24px; color: #0f172a; font-weight: 800; }

    /* BARRA DE SEGURANÇA */
    .security-bar {
        background-color: white; border-radius: 12px; padding: 20px; margin-top: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02); border: 1px solid #e2e8f0;
        display: flex; justify-content: space-between; align-items: center;
    }

    /* Células da Agenda */
    .event-card { background-color: #d1fae5; border-left: 4px solid #0d9488; color: #064e3b; padding: 4px; font-size: 11px; font-weight: bold; border-radius: 4px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
    .blocked-cell { background-color: #fee2e2; border: 1px dashed #ef4444; height: 100%; opacity: 0.6; border-radius: 4px; }
    .day-header { text-align: center; font-weight: bold; color: #334155; padding-bottom: 10px; border-bottom: 2px solid #e2e8f0; }
    .time-col { color: #94a3b8; font-size: 12px; text-align: right; padding-right: 10px; margin-top: -10px;}
    
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
    except:
        return None

supabase = init_connection()

# --- 3. ESTADOS E FUNÇÕES AUXILIARES ---
if 'data_referencia' not in st.session_state:
    st.session_state['data_referencia'] = datetime.date.today()

def mudar_semana(dias):
    st.session_state['data_referencia'] += timedelta(days=dias)

def renderizar_grade(sala_selecionada, is_admin=False):
    hoje = st.session_state['data_referencia']
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    agora = datetime.datetime.now()

    try:
        resp = supabase.table("reservas").select("*")\
            .eq("sala_nome", sala_selecionada)\
            .eq("status", "confirmada")\
            .gte("data_reserva", str(inicio_semana))\
            .lte("data_reserva", str(fim_semana))\
            .execute()
        reservas = resp.data
    except: reservas = []

    mapa_reservas = {}
    for r in reservas:
        d = r['data_reserva']
        h = r['hora_inicio'] 
        if d not in mapa_reservas: mapa_reservas[d] = {}
        mapa_reservas[d][h] = r

    cols_header = st.columns([0.5] + [1]*7)
    dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    datas_semana = []
    
    cols_header[0].write("") 
    for i in range(7):
        data_atual = inicio_semana + timedelta(days=i)
        datas_semana.append(data_atual)
        style = "color: #ef4444;" if data_atual.weekday() == 6 else ("color: #0d9488; border-bottom-color: #0d9488;" if data_atual == datetime.date.today() else "")
        cols_header[i+1].markdown(f"<div class='day-header' style='{style}'>{dias_semana[i]}<br><span style='font-size:18px'>{data_atual.day:02d}</span></div>", unsafe_allow_html=True)

    st.markdown("---")

    horarios = [f"{h:02d}:00:00" for h in range(7, 23)] 
    for hora in horarios:
        hora_display = hora[:5]
        cols = st.columns([0.5] + [1]*7)
        cols[0].markdown(f"<div class='time-col'>{hora_display}</div>", unsafe_allow_html=True)
        
        for i in range(7):
            data_atual = datas_semana[i]
            hora_int = int(hora[:2])
            dt_slot = datetime.datetime.combine(data_atual, datetime.time(hora_int, 0))
            
            reserva = mapa_reservas.get(str(data_atual), {}).get(hora)
            cell = cols[i+1].empty()
            
            if reserva:
                nome = reserva.get('email_profissional', 'Psi').split('@')[0].title()
                cell.markdown(f"<div class='event-card' title='{nome}'>👤 {nome}</div>", unsafe_allow_html=True)
            elif data_atual.weekday() == 6 or dt_slot < agora:
                cell.markdown("<div class='blocked-cell'></div>", unsafe_allow_html=True)
            else:
                cell.markdown("<div style='height: 30px; border-left: 1px solid #f1f5f9;'></div>", unsafe_allow_html=True)

# --- 4. TELA LOGIN ---
def login_screen():
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<br><br><h1 style='text-align: center; color: #0d9488;'>Ψ LocaPsico</h1><p style='text-align: center;'>Gestão de Espaços Terapêuticos</p>", unsafe_allow_html=True)
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                user = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state['user'] = user.user
                st.session_state['is_admin'] = (email == "admin@admin.com.br")
                st.rerun()
            except: st.error("Login falhou.")

# --- 5. APP PRINCIPAL ---
def main():
    # HEADER IGUAL AO PRINT (Branco, Logo Esquerda, User Direita)
    c1, c2, c3 = st.columns([2, 4, 2])
    with c1:
        st.markdown("<div class='logo'><span class='logo-icon'>L</span> LOCAPSICO</div>", unsafe_allow_html=True)
    with c2:
        # Navegação Centralizada com estilo de botão
        nav = st.radio("menu", ["AGENDA", "MEU PAINEL"], horizontal=True, label_visibility="collapsed")
    with c3:
        if 'user' in st.session_state:
            nome_user = st.session_state['user'].user_metadata.get('nome', st.session_state['user'].email.split('@')[0]).upper()
            st.markdown(f"""
            <div style='text-align:right; line-height:1.2;'>
                <span style='font-weight:800; color:#0f172a;'>{nome_user}</span><br>
                <span style='color:#0d9488; font-size:11px; font-weight:bold;'>TERAPEUTA</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de Sair discreto
            if st.button("Sair", key="logout_btn"):
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
        
        col_nav1, col_nav2, col_nav3 = st.columns([1, 6, 2])
        with col_nav1:
            if st.button("◀", key="prev"): mudar_semana(-7)
        with col_nav2:
            ini = st.session_state['data_referencia'] - timedelta(days=st.session_state['data_referencia'].weekday())
            fim = ini + timedelta(days=6)
            st.markdown(f"<h3 style='text-align:center; margin:0'>{ini.day} - {fim.day} {ini.strftime('%B')}</h3>", unsafe_allow_html=True)
        with col_nav3:
            if st.button("▶", key="next"): mudar_semana(7)
            
        renderizar_grade(sala, is_admin=st.session_state.get('is_admin', False))
        
        with st.expander("➕ NOVO AGENDAMENTO", expanded=False):
            with st.form("new_reserva"):
                col_a, col_b = st.columns(2)
                dt = col_a.date_input("Data", min_value=datetime.date.today())
                hr = col_b.selectbox("Horário", [f"{h:02d}:00" for h in range(7, 23)])
                if st.form_submit_button("Confirmar"):
                    # AQUI ESTAVA O ERRO, AGORA ESTÁ CORRIGIDO:
                    try:
                        h_fim = f"{int(hr[:2])+1:02d}:00"
                        dados = {
                            "sala_nome": sala, "data_reserva": str(dt), "hora_inicio": hr, "hora_fim": h_fim,
                            "user_id": st.session_state['user'].id, "email_profissional": st.session_state['user'].email,
                            "valor_cobrado": 32.00, "status": "confirmada"
                        }
                        supabase.table("reservas").insert(dados).execute()
                        st.success("Reservado!")
                        st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

    # --- TELA 2: MEU PAINEL (IGUAL AO PRINT) ---
    else:
        # Dados do Usuário
        user_id = st.session_state['user'].id
        nome_display = st.session_state['user'].email.split('@')[0].title()
        
        # 1. CÁLCULO DAS MÉTRICAS REAIS
        total_investido = 0.0
        total_reservas = 0
        try:
            resp = supabase.table("reservas").select("valor_cobrado").eq("user_id", user_id).eq("status", "confirmada").execute()
            df_metricas = pd.DataFrame(resp.data)
            if not df_metricas.empty:
                total_investido = df_metricas['valor_cobrado'].sum()
                total_reservas = len(df_metricas)
        except: pass

        # 2. LAYOUT SUPERIOR (Boas vindas + Cards)
        st.markdown("<br>", unsafe_allow_html=True)
        col_text, col_card1, col_card2 = st.columns([1.5, 1, 1])
        
        with col_text:
            st.markdown(f"""
            <h1 style='color:#0f172a; margin-bottom:0;'>Olá, {nome_display}! 👋</h1>
            <p style='color:#64748b;'>Gerencie sua conta e histórico profissional.</p>
            """, unsafe_allow_html=True)
            
        with col_card1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="icon-box icon-green">↗</div>
                <div>
                    <div class="stat-label">Total Investido</div>
                    <div class="stat-value">R$ {total_investido:.0f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_card2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="icon-box icon-blue">🕒</div>
                <div>
                    <div class="stat-label">Reservas</div>
                    <div class="stat-value">{total_reservas}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 3. SEGURANÇA (Igual ao Print)
        st.markdown("""
        <div class="security-bar">
            <div style="display:flex; gap:15px; align-items:center;">
                <div style="background:#f1f5f9; padding:10px; border-radius:50%; color:#64748b;">🔑</div>
                <div>
                    <div style="font-weight:800; color:#0f172a;">SEGURANÇA</div>
                    <div style="font-size:12px; color:#64748b; font-weight:600;">TROCA DE SENHA DE ACESSO</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botão funcional de troca de senha (Expander para não poluir o visual clean)
        with st.expander("Alterar Senha (Clique aqui)", expanded=False):
            with st.form("change_pass"):
                nova_senha = st.text_input("Nova Senha", type="password")
                confirma_senha = st.text_input("Confirmar Nova Senha", type="password")
                if st.form_submit_button("Atualizar Senha Agora"):
                    if nova_senha == confirma_senha and len(nova_senha) >= 6:
                        try:
                            supabase.auth.update_user({"password": nova_senha})
                            st.success("Senha alterada com sucesso!")
                        except Exception as e: st.error(f"Erro: {e}")
                    else:
                        st.error("Senhas não conferem ou muito curtas.")

        # 4. HISTÓRICO DE RESERVAS
        st.markdown("<br><h4 style='color:#94a3b8; font-weight:700; text-transform:uppercase; font-size:14px;'>Histórico de Reservas</h4>", unsafe_allow_html=True)
        
        try:
            # Busca histórico completo
            resp_hist = supabase.table("reservas").select("*").eq("user_id", user_id).order("data_reserva", desc=True).limit(20).execute()
            df_hist = pd.DataFrame(resp_hist.data)
            
            if not df_hist.empty:
                # Tabela estilizada nativa do Streamlit
                st.dataframe(
                    df_hist,
                    column_config={
                        "sala_nome": "Sala",
                        "data_reserva": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "hora_inicio": "Início",
                        "hora_fim": "Fim",
                        "valor_cobrado": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                        "status": "Status"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma reserva encontrada no histórico.")
        except:
            st.error("Erro ao carregar histórico.")

if __name__ == "__main__":
    main()




