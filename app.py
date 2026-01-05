import streamlit as st
import google.generativeai as genai

# Configuração da página
st.set_page_config(page_title="LocaPsi", page_icon="🧠", layout="centered")

# --- PERSONALIDADE DO LOCAPSI ---
# Aqui definimos como ele deve se comportar
SYSTEM_INSTRUCTION = """
Você é o LocaPsi, um assistente virtual acolhedor e empático focado em saúde mental e psicologia.
Suas respostas devem ser calmas, objetivas, mas muito humanas.
IMPORTANTE: Você não substitui um psicólogo real. Se o usuário relatar crise grave ou risco de vida, oriente a buscar ajuda profissional ou ligar para o CVV (188).
Nunca dê diagnósticos médicos definitivos, ofereça acolhimento e orientações gerais.
"""

# Título e Subtítulo
st.title("🧠 LocaPsi")
st.subheader("Seu espaço de escuta e acolhimento")

# 1. Autenticação
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("Erro na chave de API.")
    st.stop()

# 2. Configuração do Modelo com a Instrução de Sistema
# Usando o modelo que funcionou para você: gemini-2.5-flash
try:
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        system_instruction=SYSTEM_INSTRUCTION
    )
except Exception as e:
    st.error(f"Erro no modelo: {e}")

# 3. Chat (Histórico Simples)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostra as mensagens antigas
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Campo de entrada do usuário
if prompt := st.chat_input("Como você está se sentindo hoje?"):
    # Mostra a mensagem do usuário
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Gera a resposta do LocaPsi
    with st.chat_message("assistant"):
        with st.spinner('O LocaPsi está analisando...'):
            try:
                response = model.generate_content(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Erro ao gerar resposta: {e}")








