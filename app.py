import streamlit as st
import os
import google.generativeai as genai

st.title("🕵️ Tela de Diagnóstico")

# 1. Qual versão está instalada?
st.subheader("1. Versão da Biblioteca")
try:
    st.code(f"google-generativeai: {genai.__version__}")
except:
    st.error("A biblioteca nem sequer foi encontrada!")

# 2. Quais arquivos existem na pasta?
st.subheader("2. Arquivos no servidor")
files = os.listdir('.')
st.write(files)

# 3. O arquivo requirements existe mesmo?
st.subheader("3. Verificação do arquivo de instalação")
if "requirements.txt" in files:
    st.success("O arquivo 'requirements.txt' EXISTE e o nome está CORRETO.")
elif "requirements.txt.txt" in files:
    st.error("ERRO ENCONTRADO: O arquivo se chama 'requirements.txt.txt' (nome duplicado).")
else:
    st.error(f"ERRO: Não achei 'requirements.txt'. Achei estes nomes parecidos: {[f for f in files if 'req' in f]}")






