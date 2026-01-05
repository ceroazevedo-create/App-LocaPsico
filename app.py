import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide")

# CSS para ficar IGUAL ao seu design (Teal/Branco/Limpo)
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
    .grid-cell { border-left: 1px solid #f1f5f9; min-height: 50px; padding: 2px; }
    .grid-row { border-bottom: 1px solid #f1f5f9; }
    
    /* Remove padding padrão do Streamlit para caber mais coisa */
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

# --- 3. ESTADO DA DATA (Navegação < >) ---
if 'data_referencia' not in st.session_state:
    st.session_state['data_referencia'] = datetime.date.today()

def mudar_semana(dias):
    st.session_state['data_referencia'] += timedelta(days=dias)

# --- 4. FUNÇÃO DE GRADE VISUAL (O SEGREDO) ---
def renderizar_grade(sala_selecionada, is_admin=False):
    # 1. Calcular início e fim da semana atual
    hoje = st.session_state['data_referencia']
    inicio_semana = hoje - timedelta(days=hoje.weekday()) # Segunda-feira
    fim_semana = inicio_semana + timedelta(days=6) # Domingo
    
    # 2. Buscar reservas do banco APENAS para esta semana e sala
    resp = supabase.table("reservas").select("*")\
        .eq("sala_nome", sala_selecionada)\
        .eq("status", "confirmada")\
        .gte("data_reserva", str(inicio_semana))\
        .lte("data_reserva", str(fim_semana))\
        .execute()
    
    reservas = resp.data # Lista de dicionários
    
    # Transformar em um dicionário fácil de buscar: agendamentos["2025-01-05"]["09:00:00"] = Dados
    mapa_reservas = {}
    for r in reservas:
        d = r['data_reserva']
        h = r['hora_inicio'] # Vem como '09:00:00'
        if d not in mapa_reservas: mapa_reservas[d] = {}
        mapa_reservas[d][h] = r

    # 3. Cabeçalho da Grade (Dias da Semana)
    cols_header = st.columns([0.5] + [1]*7) # 1 coluna fina p/ hora, 7 p/ dias
    
    dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    datas_semana = []
    
    # Renderiza TOPO (Seg 05, Ter 06...)
    cols_header[0].write("") # Espaço da hora
    for i in range(7):
        data_atual = inicio_semana + timedelta(days=i)
        datas_semana.append(data_atual)
        dia_str = f"{dias_semana[i]} **{data_atual.day:02d}**"
        
        # Destacar o dia de "Hoje" visualmente
        if data_atual == datetime.date.today():
             cols_header[i+1].markdown(f"<div class='day-header' style='color: #0d9488; border-bottom-color: #0d9488;'>{dia_str}</div>", unsafe_allow_html=True)
        else:
             cols_header[i+1].markdown(f"<div class='day-header'>{dia_str}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # 4. Corpo da Grade (Horários 07:00 as 22:00)
    horarios = [f"{h:02d}:00:00" for h in range(7, 23)] # Formato do banco HH:MM:SS
    
    for hora in horarios:
        hora_display = hora[:5] # Apenas HH:MM para mostrar na tela
        cols = st.columns([0.5] + [1]*7)
        
        # Coluna da Hora
        cols[0].markdown(f"<div class='time-col'>{hora_display}</div>", unsafe_allow_html=True)
        
        # Colunas dos Dias
        for i in range(7):
            data_atual_str = str(datas_semana[i])
            cell_placeholder = cols[i+1].empty()
            
            # Verifica se tem reserva
            reserva_aqui = mapa_reservas.get(data_atual_str, {}).get(hora)
            
            if reserva_aqui:
                # MOSTRAR CARD DE RESERVADO
                nome_display = "Reservado"
                if is_admin:
                    nome_display = reserva_aqui.get('email_profissional', 'Psi')
                
                # HTML do Card
                cell_placeholder.markdown(f"""
                <div class='event-card' title='{nome_display}'>
                    {nome_display}
                </div>
                """, unsafe_allow_html=True)
            else:
                # ESPAÇO VAZIO (Botão transparente ou lógica de clique futura)
                # Para manter o visual limpo, deixamos vazio, mas com a borda css
                cell_placeholder.markdown("<div style='height: 30px; border-left: 1px solid #f1f5f9;'></div>", unsafe_allow_html=True)

# --- 5. TELA PRINCIPAL ---

def main():
    # HEADER SUPERIOR (Igual ao print)
    c1, c2, c3 = st.columns([2, 4, 2])
    with c1:
        st.markdown("<div class='logo'><span class='logo-icon'>L</span> LOCAPSICO</div>", unsafe_allow_html=True)
    with c2:
        # Navegação Central (Agenda / Painel)
        nav = st.radio("Navegação", ["📅 AGENDA", "⚙️ MEU PA





