import streamlit as st
import google.generativeai as genai

# Configuração da página
st.set_page_config(page_title="LocaPsi", page_icon="🧠")

st.title("LocaPsi - Assistente IA")

# 1. Autenticação Segura
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("⚠️ Erro de Configuração: Não encontrei a chave 'GOOGLE_API_KEY' nos Secrets do Streamlit.")
    st.stop()

# 2. Configuração do Modelo (Usando o mais moderno para versão 0.8.6)
# Estamos usando o Flash, que é rápido e compatível com a biblioteca nova
MODEL_NAME = 'gemini-1.5-flash'

try:
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    st.error(f"Erro ao configurar o modelo: {e}")

# 3. Interface de Chat
user_input = st.text_input("Como posso ajudar você hoje?", placeholder="Digite aqui...")

if st.button("Enviar"):
    if not user_input:
        st.warning("Por favor, digite algo.")
    else:
        with st.spinner('Analisando...'):
            try:
                # Tentativa de gerar resposta
                response = model.generate_content(user_input)
                st.markdown(response.text)
                
            except Exception as e:
                # SE DER ERRO, VAMOS DESCOBRIR O PORQUÊ
                st.error(f"Ocorreu um erro ao conectar com o Google: {e}")
                
                # Diagnóstico de emergência: Lista os modelos disponíveis para sua chave
                st.warning("Tentando listar modelos disponíveis para sua conta...")
                try:
                    st.write("Sua chave tem acesso a estes modelos:")
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            st.code(m.name)
                except:
                    st.error("Não consegui nem listar os modelos. Verifique se sua API Key é válida.")







