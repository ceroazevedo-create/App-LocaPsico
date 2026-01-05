import streamlit as st
import google.generativeai as genai

st.title("Teste de Diagnóstico")

# Vamos ver qual versão o servidor instalou
st.write(f"Versão da biblioteca instalada: {genai.__version__}")

# Se a versão for menor que 0.7.0, o arquivo requirements.txt está sendo ignorado
if genai.__version__ < "0.7.0":
    st.error("ERRO CRÍTICO: O servidor está usando uma versão antiga. Verifique o nome do arquivo requirements.txt")
else:
    st.success("SUCESSO: A versão está correta! Agora podemos colocar o código da IA.")




