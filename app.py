import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client

# Configuração da página
st.set_page_config(page_title="LocaPsi Real", page_icon="🏢")

st.title("🏢 LocaPsi - Integrado ao Supabase")

# =======================================================
# 1. CONEXÃO COM O SUPABASE (O BANCO DE DADOS)
# =======================================================
try:
    # Pega as chaves dos Secrets do Streamlit
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    
    # Cria a conexão
    supabase: Client = create_client(url, key)
    
    # TESTE DE CONEXÃO: Tenta buscar as salas do banco
    response = supabase.table('rooms').select("*").execute()
    salas_reais = response.data
    
    # Se der certo, monta um texto com as salas para ensinar a IA
    texto_salas = ""
    if salas_reais:
        for sala in salas_reais:
            # Aqui ele pega o nome e valor direto do seu banco
            texto_salas += f"- {sala['nome']}: {sala.get('descricao', 'Sem descrição')}. Preço: R$ {sala['valor_padrao']}\n"
    else:
        texto_salas = "Nenhuma sala encontrada no banco de dados."

except Exception as e:
    st.error(f"⚠️ Erro ao conectar no Supabase: {e}")
    st.stop()

# =======================================================
# 2. CONFIGURAÇÃO DA IA (GEMINI)
# =======================================================

# Instrução dinâmica: A IA agora sabe o que tem no banco de verdade!
INSTRUCOES = f"""
Você é o assistente da LocaPsi.
Use APENAS os dados abaixo (vindos do banco de dados) para responder:

LISTA DE SALAS DISPONÍVEIS AGORA:
{texto_salas}

Regra: Se o cliente quiser reservar, peça o nome da sala e o horário.
(Por enquanto, apenas colete os dados, não grave no banco ainda).
"""

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=INSTRUCOES)
except Exception as e:
    st.error("Erro no Google API Key.")
    st.stop()

# =======================================================
# 3. CHAT
# =======================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Pergunte sobre as salas..."):
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






