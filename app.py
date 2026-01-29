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

# --- 1. CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide", initial_sidebar_state="collapsed")

# Inicializa Estado
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'reset_email' not in st.session_state: st.session_state.reset_email = ""
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()
# Controle de seleção da tabela
if 'last_selected' not in st.session_state: st.session_state.last_selected = None

NOME_DO_ARQUIVO_LOGO = "logo.png"

# --- 2. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 3. CSS (Ajustes finos apenas) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; font-family: 'Inter', sans-serif; color: #1e293b; }
    header, footer, [data-testid="stToolbar"] { display: none !important; }
    
    div[data-testid="stForm"] button, button[kind="primary"] { 
        background: #0f766e !important; color: white !important; border: none; border-radius: 6px; 
    }
    
    /* Remove padding excessivo do mobile */
    @media only screen and (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNÇÕES DE SUPORTE ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if not email: return "Visitante"
    if "cesar_unib" in email: return "Cesar"
    if "thascaranalle" in email: return "Thays"
    nome_completo = nome_banco or nome_meta or email.split('@')[0]
    return str(nome_completo).strip().split(' ')[0].title()

def get_agora_br():
    return datetime.datetime.utcnow() - timedelta(hours=3)

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
    delta = 7 
    if direcao == 'prev': st.session_state.data_ref -= timedelta(days=delta)
    else: st.session_state.data_ref += timedelta(days=delta)

# --- 5. MODAL DE AGENDAMENTO ---
@st.dialog("Agendar Horário")
def modal_agendamento(sala_padrao, data_obj, hora_str):
    hora_int = int(hora_str.split(':')[0])
    st.markdown(f"### {data_obj.strftime('%d/%m/%Y')} às {hora_str}")
    config_precos = get_config_precos()
    
    modo = st.radio("Tipo de Cobrança", ["Por Hora", "Por Período"], horizontal=True)
    horarios_selecionados = []
    valor_final = 0.0
    
    if modo == "Por Hora":
        horarios_selecionados = [(f"{hora_int:02d}:00", f"{hora_int+1:02d}:00")]
        valor_final = config_precos['preco_hora']
        st.info(f"Valor: R$ {valor_final:.2f}")
    else:
        if 7 <= hora_int < 12: p = "Manhã (07-12h)"; start, end, price = 7, 12, config_precos['preco_manha']
        elif 13 <= hora_int < 18: p = "Tarde (13-18h)"; start, end, price = 13, 18, config_precos['preco_tarde']
        elif 18 <= hora_int < 22: p = "Noite (18-22h)"; start, end, price = 18, 22, config_precos['preco_noite']
        else: p = "Diária"; start, end, price = 7, 22, config_precos['preco_diaria']
        
        st.write(f"Período: **{p}**")
        st.info(f"Valor: R$ {price:.2f}")
        for h in range(start, end):
            horarios_selecionados.append((f"{h:02d}:00", f"{h+1:02d}:00"))
        valor_final = price
    
    st.write("")
    is_recurring = st.checkbox("Repetir por 4 semanas")
    
    if st.button("Confirmar Reserva", type="primary", use_container_width=True):
        user = st.session_state.user
        nm = resolver_nome(user.email, user.user_metadata.get('nome'))
        agora = get_agora_br()
        
        try:
            dias_reserva = [data_obj]
            if is_recurring:
                for k in range(1, 4): dias_reserva.append(data_obj + timedelta(days=7*k))
            
            inserts = []
            for d_res in dias_reserva:
                if d_res.weekday() == 6: continue 
                
                for h_start, h_end in horarios_selecionados:
                    dt_check = datetime.datetime.combine(d_res, datetime.datetime.strptime(h_start, "%H:%M").time())
                    if dt_check < agora: st.error(f"Horário {h_start} já passou."); return
                    if d_res.weekday() == 5 and int(h_start[:2]) >= 14: st.error("Sábado fecha 14h."); return
                    
                    chk = supabase.table("reservas").select("id").eq("sala_nome", sala_padrao).eq("data_reserva", str(d_res)).eq("hora_inicio", f"{h_start}:00").neq("status", "cancelada").execute()
                    if chk.data: st.error(f"Horário {h_start} dia {d_res.day} ocupado."); return 
                    
                    val_to_save = valor_final if (h_start, h_end) == horarios_selecionados[0] or modo == "Por Hora" else 0.0
                    
                    inserts.append({
                        "sala_nome": sala_padrao, "data_reserva": str(d_res), "hora_inicio": f"{h_start}:00", "hora_fim": f"{h_end}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm, "valor_cobrado": val_to_save, "status": "confirmada"
                    })
            
            if inserts:
                supabase.table("reservas").insert(inserts).execute()
                # Limpa a seleção para fechar o ciclo
                st.session_state.last_selected = None
                st.toast("Agendado!", icon="✅")
                time.sleep(1)
                st.rerun()
                
        except Exception as e: st.error(f"Erro: {e}")

# --- 6. RENDERIZADOR DA AGENDA (DATAFRAME STYLED) ---
def render_calendar_interface(sala, is_admin_mode=False):
    # NAVEGAÇÃO
    c1, c2, c3 = st.columns([1, 4, 1])
    c1.button("❮", on_click=lambda: navegar('prev'), use_container_width=True)
    c3.button("❯", on_click=lambda: navegar('next'), use_container_width=True)
    
    ref = st.session_state.data_ref
    d_start = ref - timedelta(days=ref.weekday())
    mes_nome = d_start.strftime("%b").upper()
    c2.markdown(f"<div style='text-align:center; font-weight:bold; margin-top:5px'>{mes_nome} {d_start.day}</div>", unsafe_allow_html=True)

    # 1. PREPARAÇÃO DOS DADOS
    dias_visiveis = [d_start + timedelta(days=i) for i in range(7)]
    # Títulos das colunas
    col_headers = [f"{d.strftime('%d/%m')} {['SEG','TER','QUA','QUI','SEX','SAB','DOM'][d.weekday()]}" for d in dias_visiveis]
    # Títulos das linhas (Horas 07:00 as 21:00)
    row_headers = [f"{h:02d}:00" for h in range(7, 22)]
    
    # Matriz de Dados (O que aparece escrito) e Matriz de Estilo (Cores)
    data_matrix = []
    
    # 2. BUSCA DO BANCO
    agora = get_agora_br()
    d_end_q = d_start + timedelta(days=7)
    
    try:
        r = supabase.table("reservas").select("*").eq("sala_nome", sala).neq("status", "cancelada").gte("data_reserva", str(d_start)).lte("data_reserva", str(d_end_q)).execute()
        reservas = r.data
        
        mapa_reservas = {}
        for x in reservas:
            k = f"{x['data_reserva']} {x['hora_inicio']}"
            nm = resolver_nome(x['email_profissional'], nome_banco=x['nome_profissional'])
            val = "BLOQUEADO" if x['status'] == 'bloqueado' else f"{nm}"
            mapa_reservas[k] = val

        # Constrói a Matriz
        for h in range(7, 22):
            row_data = []
            h_full = f"{h:02d}:00:00"
            for d in dias_visiveis:
                key = f"{d} {h_full}"
                
                # Regras de Negócio
                dt_check = datetime.datetime.combine(d, datetime.time(h, 0))
                is_past = dt_check < (agora - timedelta(minutes=15))
                is_closed = (d.weekday() == 6) or (d.weekday() == 5 and h >= 14)
                
                if key in mapa_reservas:
                    row_data.append(mapa_reservas[key]) # Ocupado
                elif is_past or is_closed:
                    row_data.append("---") # Fechado
                else:
                    row_data.append("LIVRE") # Disponível
            data_matrix.append(row_data)

    except Exception as e: st.error(f"Erro dados: {e}")

    # Cria o DataFrame
    df = pd.DataFrame(data_matrix, index=row_headers, columns=col_headers)

    # 3. FUNÇÃO DE ESTILO (PINTAR AS CÉLULAS)
    def color_coding(val):
        color = '#f0f2f6' # Cinza claro (Padrão/Livre)
        text_color = '#31333F'
        weight = 'normal'
        
        if val == "LIVRE":
            color = '#ffffff' # Branco para livre
            text_color = '#0f766e' # Verde escuro texto
            weight = 'bold'
        elif val == "---":
            color = '#e0e0e0' # Cinza escuro (fechado)
            text_color = '#999999'
        elif val == "BLOQUEADO":
            color = '#64748b' # Cinza Azulado
            text_color = 'white'
        elif val: # Qualquer outro texto (Nome da pessoa)
            color = '#ef4444' # Vermelho (Ocupado)
            text_color = 'white'
            weight = 'bold'
            
        return f'background-color: {color}; color: {text_color}; font-weight: {weight}; text-align: center; border: 1px solid #ddd;'

    # Aplica o estilo
    styled_df = df.style.map(color_coding)

    # 4. RENDERIZA E CAPTURA CLIQUE
    st.markdown("Clique em **LIVRE** para agendar:", unsafe_allow_html=True)
    
    # O PULO DO GATO: st.dataframe com seleção
    selection = st.dataframe(
        styled_df, # Passa o DF estilizado
        use_container_width=True,
        height=600,
        on_select="rerun", # Reexecuta ao clicar
        selection_mode="single-cell",
        key=f"grid_{sala}_{ref}" # Key única para forçar refresh ao mudar semana
    )

    # 5. PROCESSA A SELEÇÃO
    if selection and selection.selection.rows and selection.selection.columns:
        r_idx = selection.selection.rows[0]
        c_idx = selection.selection.columns[0]
        
        # Recupera dados
        hora_clicada = row_headers[r_idx]
        data_clicada = dias_visiveis[c_idx]
        
        # Valor Real (sem formatação)
        valor_celula = df.iat[r_idx, c_idx]
        
        if valor_celula == "LIVRE":
            # Abre Modal
            modal_agendamento(sala, data_clicada, hora_clicada)
        elif valor_celula == "---":
            st.toast("Horário fechado ou passado.", icon="🚫")
        else:
            st.toast(f"Ocupado por: {valor_celula}", icon="⚠️")
            if is_admin_mode:
                st.info("Admin: Use o painel para cancelar.")

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
        render_calendar_interface(sala_adm, is_admin_mode=True)
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
        
    with tabs[4]:
        st.markdown("### Gerenciar Usuários")
        service_key = st.secrets.get("SUPABASE_SERVICE_KEY")
        if service_key:
            st.success("🟢 Modo Super Admin: Exclusão total ativada.")
        else:
            st.warning("🟡 Modo Limitado: Histórico apagado, login mantido. Configure SUPABASE_SERVICE_KEY para apagar tudo.")
        df_users = pd.DataFrame()
        if service_key:
            try:
                adm_client = create_client(st.secrets["SUPABASE_URL"], service_key)
                auth_users = adm_client.auth.admin.list_users()
                users_list = []
                for u in auth_users:
                    users_list.append({"user_id": u.id, "email_profissional": u.email, "nome_profissional": u.user_metadata.get('nome', 'Sem Nome')})
                df_users = pd.DataFrame(users_list)
            except Exception as e: pass
        if df_users.empty:
            try:
                users_data = supabase.table("reservas").select("user_id, email_profissional, nome_profissional").execute().data
                if users_data:
                    df_users = pd.DataFrame(users_data).drop_duplicates(subset=['user_id'])
            except: pass
        if not df_users.empty:
            for _, row in df_users.iterrows():
                if st.session_state.user.id == row['user_id']: continue
                with st.container():
                    c1, c2, c3 = st.columns([3, 3, 2])
                    raw_name = row.get('nome_profissional')
                    raw_email = row.get('email_profissional')
                    nm_show = resolver_nome(raw_email, nome_banco=raw_name)
                    c1.write(f"**{nm_show}**")
                    c2.write(f"_{raw_email}_")
                    if c3.button("🗑️ Remover", key=f"rm_user_{row['user_id']}", help="Excluir Usuário"):
                        if service_key:
                            try:
                                adm_client = create_client(st.secrets["SUPABASE_URL"], service_key)
                                try: adm_client.table("reservas").delete().eq("user_id", row['user_id']).execute()
                                except: pass
                                try: adm_client.table("profiles").delete().eq("id", row['user_id']).execute()
                                except: pass
                                adm_client.auth.admin.delete_user(row['user_id'])
                                st.toast("Usuário excluído completamente!", icon="✅")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir: {e}")
                                st.warning("Verifique se rodou o comando SQL no Supabase para 'on delete cascade'.")
                        else:
                            try:
                                supabase.table("reservas").delete().eq("user_id", row['user_id']).execute()
                                st.toast("Histórico limpo (Login mantido).", icon="⚠️")
                            except: pass
                            time.sleep(1.5)
                            st.rerun()
                    st.divider()
        else:
            st.info("Nenhum usuário encontrado.")

# --- 7. MAIN ---
def main():
    if not st.session_state.user:
        c_v1, c_main, c_v2 = st.columns([1, 1.2, 1])
        with c_main:
            st.write("") 
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO, use_container_width=True) 
            else: st.markdown("<h1 style='text-align:center; color:#0d9488'>LocaPsico</h1>", unsafe_allow_html=True)
            
            with st.form("login"):
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        if u.user: 
                            st.session_state.user = u.user
                            st.session_state.is_admin = (email == "admin@admin.com.br")
                            st.rerun()
                    except Exception as e:
                        if "StopException" not in str(type(e)):
                            st.error("Erro login.")
            
            c_a, c_b = st.columns(2)
            if c_a.button("Criar Conta"): st.session_state.auth_mode = 'register'; st.rerun()
            if c_b.button("Recuperar"): st.session_state.auth_mode = 'forgot'; st.rerun()
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
        
        c_head_text, c_head_btn = st.columns([4, 1]) 
        with c_head_text: st.markdown(f"<h3 style='color:#0d9488; margin:0'>LocaPsico | {nm}</h3>", unsafe_allow_html=True)
        with c_head_btn: 
            if st.button("Sair"): supabase.auth.sign_out(); st.session_state.clear(); st.rerun()
        st.divider()
        
        tabs = st.tabs(["📅 Agenda", "📊 Painel", "🔒 Conta"])
        
        with tabs[0]:
            sala = st.radio("Local", ["Sala 1", "Sala 2"], horizontal=True)
            render_calendar_interface(sala)
            
        with tabs[1]:
            st.markdown("### Meus Agendamentos")
            agora = get_agora_br()
            inicio_mes = agora.date().replace(day=1)
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
                                else: c2.caption("🚫 < 24h")
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

