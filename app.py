import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta

# --- 1. CONFIGURAÇÃO VISUAL E CSS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

# CSS para o visual Clean/Teal (Igual ao seu print)
st.markdown("""
<style>
    /* Fundo e Fontes */
    .stApp { background-color: #ffffff; }
    h1, h2, h3, p, div { font-family: 'Segoe UI', sans-serif; }
    
    /* Botões Principais (Teal) */
    .stButton>button {
        background-color: #0d9488 !important; 
        color: white !important;
        border-radius: 6px; 
        border: none;
        font-weight: 600;
    }
    
    /* Header Personalizado */
    .header-container {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 20px; background-color: white; border-bottom: 1px solid #e5e7eb;
        margin-bottom: 20px;
    }
    .logo { font-size: 24px; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 10px; }
    .logo-icon { background-color: #0d9488; color: white; padding: 5px 10px; border-radius: 8px; }
    
    /* Card de Agendamento na Grade */
    .event-card {
        background-color: #d1fae5; /* Verde claro */
        border-left: 4px solid #0d9488;
        color: #064e3b;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 2px;
        overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
    }
    
    /* Estilo da Grade */
    .time-col { color: #94a3b8; font-size: 12px; text-align: right; padding-right: 10px; margin-top: -10px;}
    .day-header { text-align: center; font-weight: bold; color: #334155; padding-bottom: 10px; border-bottom: 2px solid #e2e8f0; }
    
    /* Remove padding padrão do Streamlit para caber mais coisa */
    .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM O BANCO ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

# --- 3. CONTROLE DE DATA (NAVEGAÇÃO) ---
if 'data_referencia' not in st.session_state:
    st.session_state['data_referencia'] = datetime.date.today()

def mudar_semana(dias):
    st.session_state['data_referencia'] += timedelta(days=dias)

# --- 4. FUNÇÃO QUE DESENHA A GRADE (VISUAL) ---
def renderizar_grade(sala_selecionada, is_admin=False):
    # 1. Calcular início e fim da semana atual
    hoje = st.session_state['data_referencia']
    inicio_semana = hoje - timedelta(days=hoje.weekday()) # Segunda-feira
    fim_semana = inicio_semana + timedelta(days=6) # Domingo
    
    # 2. Buscar reservas do banco
    try:
        resp = supabase.table("reservas").select("*")\
            .eq("sala_nome", sala_selecionada)\
            .eq("status", "confirmada")\
            .gte("data_reserva", str(inicio_semana))\
            .lte("data_reserva", str(fim_semana))\
            .execute()
        reservas = resp.data
    except:
        reservas = []
        st.error("Erro ao conectar com a agenda.")
    
    # Mapear reservas: mapa[data][hora] = dados
    mapa_reservas = {}
    for r in reservas:
        d = r['data_reserva']
        h = r['hora_inicio'] 
        if d not in mapa_reservas: mapa_reservas[d] = {}
        mapa_reservas[d][h] = r

    # 3. Cabeçalho da Grade (Dias da Semana)
    cols_header = st.columns([0.5] + [1]*7) # 1 coluna fina p/ hora, 7 p/ dias
    dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    datas_semana = []
    
    cols_header[0].write("") # Espaço vazio em cima da hora
    for i in range(7):
        data_atual = inicio_semana + timedelta(days=i)
        datas_semana.append(data_atual)
        dia_str = f"{dias_semana[i]} **{data_atual.day:02d}**"
        
        # Destacar o dia de Hoje
        if data_atual == datetime.date.today():
             cols_header[i+1].markdown(f"<div class='day-header' style='color: #0d9488; border-bottom-color: #0d9488;'>{dia_str}</div>", unsafe_allow_html=True)
        else:
             cols_header[i+1].markdown(f"<div class='day-header'>{dia_str}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # 4. Linhas de Horário (07:00 as 22:00)
    horarios = [f"{h:02d}:00:00" for h in range(7, 23)] 
    
    for hora in horarios:
        hora_display = hora[:5] # Mostra apenas HH:MM
        cols = st.columns([0.5] + [1]*7)
        
        # Coluna da Hora
        cols[0].markdown(f"<div class='time-col'>{hora_display}</div>", unsafe_allow_html=True)
        
        # Colunas dos Dias (Células)
        for i in range(7):
            data_atual_str = str(datas_semana[i])
            cell_placeholder = cols[i+1].empty()
            
            # Verifica se tem reserva neste dia+hora
            reserva_aqui = mapa_reservas.get(data_atual_str, {}).get(hora)
            
            if reserva_aqui:
                # CARD DE RESERVADO
                nome_display = "Reservado"
                if is_admin:
                    nome_display = reserva_aqui.get('email_profissional', 'Psi')
                
                cell_placeholder.markdown(f"""
                <div class='event-card' title='{nome_display}'>
                    {nome_display}
                </div>
                """, unsafe_allow_html=True)
            else:
                # ESPAÇO VAZIO (Grade)
                cell_placeholder.markdown("<div style='height: 30px; border-left: 1px solid #f1f5f9;'></div>", unsafe_allow_html=True)

# --- 5. TELA DE LOGIN ---
def login_screen():
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #0d9488;'>Ψ LocaPsico</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Acesse sua conta</p>", unsafe_allow_html=True)
        
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            if not supabase:
                st.error("Erro de conexão com o banco.")
                return
            try:
                user = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state['user'] = user.user
                st.session_state['is_admin'] = (email == "admin@admin.com.br")
                st.rerun()
            except:
                st.error("Login falhou. Verifique e-mail e senha.")

# --- 6. FUNÇÃO PRINCIPAL (APP) ---
def main():
    # HEADER
    c1, c2, c3 = st.columns([2, 4, 2])
    with c1:
        st.markdown("<div class='logo'><span class='logo-icon'>L</span> LOCAPSICO</div>", unsafe_allow_html=True)
    with c2:
        # Navegação
        nav = st.radio("Navegação", ["📅 AGENDA", "⚙️ MEU PAINEL"], horizontal=True, label_visibility="collapsed")
    with c3:
        if 'user' in st.session_state:
            try:
                email_short = st.session_state['user'].email.split('@')[0].upper()
                st.markdown(f"<div style='text-align:right'><b>{email_short}</b><br><span style='color:#0d9488; font-size:12px'>TERAPEUTA</span></div>", unsafe_allow_html=True)
            except:
                st.markdown("Logado")
        else:
            st.markdown("<div style='text-align:right; color:#999'>Visitante</div>", unsafe_allow_html=True)

    # VERIFICA LOGIN
    if 'user' not in st.session_state:
        login_screen()
        return

    # TELA DA AGENDA
    if "AGENDA" in nav:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Seletor de Sala
        sala_selecionada = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True, label_visibility="collapsed")
        
        st.markdown("---")
        
        # Controles de Semana (< >)
        col_nav1, col_nav2, col_nav3 = st.columns([1, 6, 2])
        with col_nav1:
            if st.button("◀", key="prev_week"): mudar_semana(-7)
        with col_nav2:
            inicio = st.session_state['data_referencia'] - timedelta(days=st.session_state['data_referencia'].weekday())
            fim = inicio + timedelta(days=6)
            mes_str = inicio.strftime("%B") # Mês
            st.markdown(f"<h3 style='text-align:center; margin:0'>{inicio.day} - {fim.day} {mes_str}</h3>", unsafe_allow_html=True)
        with col_nav3:
            if st.button("▶", key="next_week"): mudar_semana(7)
            
        if st.button("Voltar para Hoje"): 
            st.session_state['data_referencia'] = datetime.date.today()
            st.rerun()

        # RENDERIZA A GRADE VISUAL
        renderizar_grade(sala_selecionada, is_admin=st.session_state.get('is_admin', False))
        
        # ÁREA DE AGENDAMENTO (EXPANDÍVEL)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("➕ CLIQUE AQUI PARA AGENDAR UM NOVO HORÁRIO", expanded=False):
            with st.form("quick_add"):
                st.write(f"Criar reserva na **{sala_selecionada}**")
                c_data, c_hora = st.columns(2)
                dt_input = c_data.date_input("Dia")
                hr_input = c_hora.selectbox("Horário", [f"{h:02d}:00" for h in range(7, 23)])
                
                if st.form_submit_button("Confirmar Reserva"):
                    h_fim = f"{int(hr_input[:2])+1:02d}:00"
                    
                    # Verifica conflito
                    conflito = False
                    try:
                        check = supabase.table("reservas").select("*").eq("sala_nome", sala_selecionada).eq("data_reserva", str(dt_input)).eq("hora_inicio", hr_input).eq("status", "confirmada").execute()
                        if check.data: conflito = True
                    except: pass
                    
                    if conflito:
                        st.error("❌ Este horário já está ocupado!")
                    else:
                        dados = {
                            "sala_nome": sala_selecionada,
                            "data_reserva": str(dt_input),
                            "hora_inicio": hr_input,
                            "hora_fim": h_fim,
                            "user_id": st.session_state['user'].id,
                            "email_profissional": st.session_state['user'].email,
                            "valor_cobrado": 32.00
                        }
                        try:
                            supabase.table("reservas").insert(dados).execute()
                            st.success("✅ Agendado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

    # TELA DO PAINEL
    else:
        st.title("Meu Painel")
        st.info("Funcionalidades financeiras e de perfil aparecerão aqui.")
        if st.button("Sair do Sistema"):
            st.session_state.clear()
            st.rerun()

# --- 7. PONTO DE PARTIDA ---
if __name__ == "__main__":
    main()



