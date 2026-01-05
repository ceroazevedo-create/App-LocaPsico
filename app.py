import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client

# Configuração da página
st.set_page_config(page_title="LocaPsi", page_icon="🏢")
st.title("🏢 LocaPsi - Reservas")

# =======================================================
# 1. CONEXÃO COM O SUPABASE
# =======================================================
texto_salas = "Carregando salas..."

try:
    # Pega as chaves
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    
    # Conecta
    supabase: Client = create_client(url, key)
    
    # Busca as salas na tabela 'rooms' que acabamos de criar
    response = supabase.table('rooms').select("*").execute()
    salas_reais = response.data
    
    # Monta o texto para a IA ler
    texto_salas = ""
    if salas_reais:
        for sala in salas_reais:
            texto_salas += f"- {sala['nome']}: {sala['descricao']} (Valor: R$ {sala['valor_padrao']}/hora)\n"
    else:
        texto_salas = "Não encontrei nenhuma sala cadastrada no banco."

except Exception as e:
    st.error(f"⚠️ Erro de conexão com Banco de Dados: {e}")
    # Se der erro, usamos um texto padrão para não travar o app
    texto_salas = "- Sala Freud: R$ 50,00 (Erro ao carregar dados reais)"

# =======================================================
# 2. CONFIGURAÇÃO DA IA
# =======================================================

INSTRUCOES = f"""
Você é o assistente da LocaPsi.
Seu objetivo é ajudar psicólogos a alugar salas.

INFORMAÇÕES REAIS DO BANCO DE DADOS (Use apenas estas salas):
{texto_salas}

REGRAS:
1. Se perguntarem os preços, use a lista acima.
2. Pergunte qual sala a pessoa quer e qual horário.
3. NÃO invente salas que não estão na lista.
"""

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=INSTRUCOES)
except Exception as e:
    st.error("Erro na Google API Key.")
    st.stop()

# =======================================================
# 3. CHAT
# =======================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Gostaria de saber os valores..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        try:
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Erro: {e}")







