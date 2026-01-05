import streamlit as st
import google.generativeai as genai

# Título do App
st.title("LocaPsi - Assistente IA")

# 1. Configuração da Chave de Segurança
# Ele busca a senha que você salvou nos "Secrets" do Streamlit
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("Erro na chave de API. Verifique os 'Secrets' nas configurações do Streamlit.")

# 2. Configuração do Modelo
# Se der erro no Flash, troque 'gemini-1.5-flash' por 'gemini-pro'
model = genai.GenerativeModel('gemini-pro')

# 3. Interface do Usuário
user_input = st.text_input("Digite sua pergunta ou caso:", placeholder="Ex: Como lidar com ansiedade?")

# 4. Ação do Botão
if st.button("Enviar"):
    if not user_input:
        st.warning("Por favor, digite algo antes de enviar.")
    else:
        try:
            with st.spinner('O LocaPsi está pensando...'):
                # Envia para o Google
                response = model.generate_content(user_input)
                # Mostra a resposta
                st.write(response.text)
        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")





