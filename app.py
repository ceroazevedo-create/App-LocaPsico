import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Diagnóstico LocaPsi")
st.title("🕵️ Tela de Diagnóstico")

# 1. Mostra onde o app está tentando conectar
url_secreta = st.secrets["SUPABASE_URL"]
# Mostra só o começo da URL para você conferir (ex: https://abcde...)
st.write(f"🔌 **Conectando no Projeto:** `{url_secreta[:20]}...`")

# 2. Tenta conectar
try:
    supabase = create_client(url_secreta, st.secrets["SUPABASE_KEY"])
    st.success("Conexão estabelecida!")
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# 3. Tenta achar a tabela com nomes diferentes (para testar Maiúsculas/Minúsculas)
nomes_teste = ['reservas', 'Reservas', 'RESERVAS', 'public.reservas']

st.write("---")
st.write("### 🧪 Testando Tabela 'reservas'")

for nome in nomes_teste:
    st.write(f"Tentando ler tabela: **'{nome}'**...")
    try:
        response = supabase.table(nome).select("*").limit(1).execute()
        st.success(f"✅ SUCESSO! A tabela correta é: '{nome}'")
        st.write("Dados encontrados:", response.data)
        break # Para se achar
    except Exception as e:
        # Se o erro for o 205, mostra aviso
        if "PGRST205" in str(e):
            st.warning(f"❌ Não encontrei '{nome}' (Erro 205)")
        else:
            st.error(f"❌ Erro diferente em '{nome}': {e}")

st.info("👆 Se todos derem erro, suas chaves do Supabase no Streamlit estão erradas.")







