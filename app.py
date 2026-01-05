import streamlit as st
import google.generativeai as genai

# Título do App
st.title("Meu App com Google AI Studio")

# Configuração da Chave de Segurança (Pega do cofre do Streamlit)
# NÃO cole sua chave diretamente aqui!
api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

# Configuração do Modelo
model = genai.GenerativeModel('gemini-pro')

# Campo para o usuário digitar
user_input = st.text_input("Digite sua pergunta:", placeholder="Ex: Crie um poema sobre café")

# Botão para enviar
if st.button("Enviar"):
    if not user_input:
        st.warning("Por favor, digite algo.")
    else:
        try:
            with st.spinner('Pensando...'):
                response = model.generate_content(user_input)
                st.write(response.text)
        except Exception as e:
            st.error(f"Erro: {e}")




