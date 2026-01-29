import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
from fpdf import FPDF
import time
import os

# --- 1. CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="LocaPsico", page_icon="Ψ", layout="wide", initial_sidebar_state="collapsed")

# --- 2. ESTADO E MEMÓRIA ---
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'data_ref' not in st.session_state: st.session_state.data_ref = datetime.date.today()

# Variáveis críticas para o agendamento
if 'form_ativo' not in st.session_state: st.session_state.form_ativo = False
if 'dados_escolhidos' not in st.session_state: st.session_state.dados_escolhidos = {}

NOME_DO_ARQUIVO_LOGO = "logo.png"

# --- 3. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 4. CSS (Limpeza Visual) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #f0f2f6; font-family: 'Inter', sans-serif; color: #1e293b; }
    header, footer, [data-testid="stToolbar"] { display: none !important; }
    
    /* Remove padding excessivo */
    .block-container { padding: 1rem 0.5rem !important; }
    
    /* Botões */
    button[kind="primary"] { background: #0f766e !important; color: white !important; border: none; }
</style>
""", unsafe_allow_html=True)

# --- 5. FUNÇÕES DE SUPORTE ---
def resolver_nome(email, nome_meta=None, nome_banco=None):
    if not email: return "Visitante"
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
    pdf.cell(0, 10, "LOCAPSICO - Extrato", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(5)
    pdf.cell(0, 10, f"Profissional: {nome_usuario} | Ref: {mes_referencia}", ln=True)
    pdf.ln(10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(30, 10, "Data", 1, 0, 'C', True)
    pdf.cell(30, 10, "Hora", 1, 0, 'C', True)
    pdf.cell(40, 10, "Sala", 1, 0, 'C', True)
    pdf.cell(30, 10, "Valor", 1, 1, 'C', True)
    total = 0
    for _, row in df.iterrows():
        total += float(row['valor_cobrado'])
        dt_str = pd.to_datetime(row['data_reserva']).strftime('%d/%m')
        pdf.cell(30, 10, dt_str, 1, 0, 'C')
        pdf.cell(30, 10, str(row['hora_inicio'])[:5], 1, 0, 'C')
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

# --- 6. MODAL DE AGENDAMENTO ---
@st.dialog("📅 Novo Agendamento")
def show_booking_modal():
    # Pega os dados seguros da sessão
    dados = st.session_state.dados_escolhidos
    if not dados:
        st.error("Erro de seleção.")
        if st.button("Fechar"): 
            st.session_state.form_ativo = False
            st.rerun()
        return

    sala = dados['sala']
    data = dados['data']
    hora = dados['hora']
    hora_int = int(hora.split(':')[0])

    st.markdown(f"**{sala}** | **{data.strftime('%d/%m/%Y')}** às **{hora}**")
    st.divider()

    config = get_config_precos()
    tipo = st.radio("Tipo", ["Hora Avulsa", "Período/Turno"], horizontal=True)
    
    slots = []
    preco = 0.0

    if tipo == "Hora Avulsa":
        slots = [(f"{hora_int:02d}:00", f"{hora_int+1:02d}:00")]
        preco = config['preco_hora']
        st.metric("Valor", f"R$ {preco:.2f}")
    else:
        # Auto-detecta turno
        if 7 <= hora_int < 12: nm, ini, fim, val = "Manhã", 7, 12, config['preco_manha']
        elif 13 <= hora_int < 18: nm, ini, fim, val = "Tarde", 13, 18, config['preco_tarde']
        elif 18 <= hora_int < 22: nm, ini, fim, val = "Noite", 18, 22, config['preco_noite']
        else: nm, ini, fim, val = "Diária", 7, 22, config['preco_diaria']
        
        st.info(f"Turno detectado: {nm}")
        st.metric("Valor Pacote", f"R$ {val:.2f}")
        preco = val
        for h in range(ini, fim):
            slots.append((f"{h:02d}:00", f"{h+1:02d}:00"))

    repetir = st.checkbox("Repetir por 4 semanas")
    
    if st.button("Confirmar Reserva", type="primary", use_container_width=True):
        user = st.session_state.user
        nm_prof = resolver_nome(user.email, user.user_metadata.get('nome'))
        
        dias = [data]
        if repetir:
            for k in range(1, 4): dias.append(data + timedelta(days=7*k))
            
        try:
            inserts = []
            for d in dias:
                if d.weekday() == 6: continue
                for h_ini, h_fim in slots:
                    # Verifica conflito
                    chk = supabase.table("reservas").select("id").eq("sala_nome", sala).eq("data_reserva", str(d)).eq("hora_inicio", f"{h_ini}:00").neq("status", "cancelada").execute()
                    if chk.data: st.error(f"Conflito em {d} às {h_ini}"); return

                    # Valor só no primeiro slot do primeiro dia ou se for avulso
                    cobrar = preco if (h_ini, h_fim) == slots[0] or tipo == "Hora Avulsa" else 0.0
                    
                    inserts.append({
                        "sala_nome": sala, "data_reserva": str(d), "hora_inicio": f"{h_ini}:00", "hora_fim": f"{h_fim}:00",
                        "user_id": user.id, "email_profissional": user.email, "nome_profissional": nm_prof, "valor_cobrado": cobrar, "status": "confirmada"
                    })
            
            if inserts:
                supabase.table("reservas").insert(inserts).execute()
                st.session_state.form_ativo = False
                st.session_state.dados_escolhidos = {}
                st.toast("Sucesso!", icon="✅")
                time.sleep(1)
                st.rerun()
                
        except Exception as e: st.error(f"Erro: {e}")

# --- 7. RENDERIZADOR DA TABELA (ESTILO LOGICPLACE) ---
def render_agenda(sala, is_admin):
    # Cabeçalho de Navegação
    c1, c2, c3 = st.columns([1, 4, 1])
    c1.button("◀", on_click=lambda: navegar('prev'), use_container_width=True)
    c3.button("▶", on_click=lambda: navegar('next'), use_container_width=True)
    
    ref = st.session_state.data_ref
    start = ref - timedelta(days=ref.weekday())
    end = start + timedelta(days=6)
    c2.markdown(f"<div style='text-align:center; font-weight:bold; padding-top:10px'>{start.strftime('%d/%m')} a {end.strftime('%d/%m')}</div>", unsafe_allow_html=True)

    # 1. Estrutura de Dados
    dias = [start + timedelta(days=i) for i in range(7)]
    col_names = [f"{d.strftime('%d/%m')}\n{['SEG','TER','QUA','QUI','SEX','SAB','DOM'][d.weekday()]}" for d in dias]
    rows = [f"{h:02d}:00" for h in range(7, 22)]
    
    # 2. Busca Dados
    data_content = []
    agora = get_agora_br()
    
    try:
        res = supabase.table("reservas").select("*").eq("sala_nome", sala).neq("status", "cancelada").gte("data_reserva", str(start)).lte("data_reserva", str(end + timedelta(days=1))).execute().data
        
        mapa = {}
        for r in res:
            k = f"{r['data_reserva']}|{r['hora_inicio'][:5]}"
            nm = resolver_nome(r['email_profissional'], nome_banco=r['nome_profissional'])
            mapa[k] = "BLOQ" if r['status'] == 'bloqueado' else nm

        for h in range(7, 22):
            row_vals = []
            h_str = f"{h:02d}:00"
            for d in dias:
                k = f"{d}|{h_str}"
                dt_chk = datetime.datetime.combine(d, datetime.time(h, 0))
                
                # Regras de Negócio
                is_past = dt_chk < (agora - timedelta(minutes=15))
                is_closed = (d.weekday() == 6) or (d.weekday() == 5 and h >= 14)
                
                if k in mapa: row_vals.append(mapa[k])
                elif is_past or is_closed: row_vals.append("---")
                else: row_vals.append("LIVRE")
            data_content.append(row_vals)
    except: pass

    df = pd.DataFrame(data_content, index=rows, columns=col_names)

    # 3. Estilização (O SEGREDO DO VISUAL)
    def style_cells(val):
        # Base: borda fina, centralizado
        base = 'border: 1px solid #d1d5db; text-align: center; vertical-align: middle; font-size: 12px;'
        
        if val == "LIVRE":
            return base + 'background-color: #ffffff; color: #10b981; font-weight: bold; cursor: pointer;'
        elif val == "---":
            return base + 'background-color: #e2e8f0; color: #94a3b8;'
        elif "BLOQ" in str(val):
            return base + 'background-color: #475569; color: white;'
        else: # Ocupado
            return base + 'background-color: #ef4444; color: white; font-weight: bold;'

    # 4. Renderização
    st.caption("Clique na célula **LIVRE** para agendar.")
    
    # DATAFRAME INTERATIVO (NATIVO DO STREAMLIT)
    # Isso garante scroll horizontal no mobile sem hacks
    event = st.dataframe(
        df.style.map(style_cells),
        use_container_width=True,
        height=600,
        on_select="rerun", # Gatilho de recarregamento
        selection_mode="single-cell",
        key=f"grid_{sala}_{ref}"
    )

    # 5. Captura do Clique (Pós-Rerun)
    if event and event.selection and event.selection.rows:
        r_idx = event.selection.rows[0]
        c_idx = event.selection.columns[0]
        
        # Recupera valores originais
        hora_sel = rows[r_idx]
        data_sel = dias[c_idx]
        val_sel = df.iat[r_idx, c_idx]
        
        if val_sel == "LIVRE":
            # SALVA ESTADO E FORÇA ABERTURA
            st.session_state.dados_escolhidos = {
                'sala': sala, 'data': data_sel, 'hora': hora_sel
            }
            st.session_state.form_ativo = True
            st.rerun() # Garante que o modal abra no próximo frame
        elif val_sel != "---":
            st.toast(f"Ocupado por {val_sel}", icon="⚠️")

def tela_admin():
    tabs = st.tabs(["💰", "📅", "🚫", "📄", "👥"])
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
            if st.button("Salvar"):
                supabase.table("configuracoes").update({"preco_hora": ph, "preco_manha": pm, "preco_tarde": pt, "preco_noite": pn, "preco_diaria": pdia}).gt("id", 0).execute()
                st.success("Salvo!")
    with tabs[1]:
        s = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True)
        render_agenda(s, True)
    with tabs[2]:
        dt = st.date_input("Data Bloqueio")
        sl = st.selectbox("Sala", ["Sala 1", "Sala 2"])
        if st.button("Bloquear Dia"):
            inserts = [{"sala_nome": sl, "data_reserva": str(dt), "hora_inicio": f"{h:02d}:00", "hora_fim": f"{h+1:02d}:00", "user_id": st.session_state.user.id, "email_profissional": "ADM", "nome_profissional": "BLOQUEIO", "valor_cobrado": 0, "status": "bloqueado"} for h in range(7, 22)]
            supabase.table("reservas").insert(inserts).execute()
            st.success("Bloqueado!")
    with tabs[3]:
        mes = st.selectbox("Mês", ["2026-01", "2026-02"])
        if st.button("Gerar Extrato"):
            # Lógica simplificada de relatório
            st.info("Funcionalidade de relatório ativa.")
    with tabs[4]:
        st.write("Gestão de Usuários")

# --- 8. MAIN ---
def main():
    # TELA DE LOGIN
    if not st.session_state.user:
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            if os.path.exists(NOME_DO_ARQUIVO_LOGO): st.image(NOME_DO_ARQUIVO_LOGO)
            else: st.markdown("## LocaPsico")
            
            with st.form("login_form"):
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
                    try:
                        u = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        if u.user: 
                            st.session_state.user = u.user
                            st.session_state.is_admin = (email == "admin@admin.com.br")
                            st.rerun()
                    except: st.error("Login falhou")
            return

    # MODAL DE AGENDAMENTO (PRIORIDADE ALTA)
    if st.session_state.form_ativo:
        show_booking_modal()

    # APP PRINCIPAL
    if st.session_state.is_admin:
        if st.button("Sair"): st.session_state.user = None; st.rerun()
        tela_admin()
    else:
        c_tit, c_sair = st.columns([4, 1])
        nm = resolver_nome(st.session_state.user.email, st.session_state.user.user_metadata.get('nome'))
        c_tit.markdown(f"#### Olá, {nm}")
        if c_sair.button("Sair"): st.session_state.user = None; st.rerun()
        
        tab1, tab2 = st.tabs(["📅 Agenda", "📊 Meus Dados"])
        with tab1:
            sala = st.radio("Local", ["Sala 1", "Sala 2"], horizontal=True)
            render_agenda(sala, False)
        with tab2:
            st.write("Histórico...")

if __name__ == "__main__":
    main()


