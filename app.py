import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Diagnóstico Final", page_icon="🕵️")

st.title("🕵️ Onde estou conectado?")

# 1. PEGAR AS CHAVES
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except:
    st.error("❌ As chaves não foram encontradas nos Secrets!")
    st.stop()

# 2. ANÁLISE DO PROJETO (SEM MOSTRAR A SENHA)
# A URL do Supabase é sempre: https://[ID-DO-PROJETO].supabase.co
# Vamos extrair esse ID para ver se bate com o seu.
projeto_id = url.replace("https://", "").split(".")[0]

st.info(f"🔑 O App está tentando conectar no Projeto de ID: **{projeto_id}**")

st.markdown("""
**TESTE VISUAL:**
1. Olhe para a URL do seu navegador quando você está no site do Supabase.
2. Ela deve começar com `https://supabase.com/dashboard/project/...`
3. O código que vem depois é **IGUAL** ao que mostrei acima em azul?
""")

# 3. TENTATIVA DE CONEXÃO DIRETA
client = create_client(url, key)

st.write("---")
st.write("### 🧪 Tentando ler a tabela 'reservas'...")

try:
    # Tenta ler apenas 1 linha para testar
    response = client.table('reservas').select("*").limit(1).execute()
    st.success("✅ SUCESSO! Conexão funcionando.")
    st.dataframe(response.data)
except Exception as e:
    st.error(f"❌ Erro: {e}")
    
    st.warning("""
    **SE O ID DO PROJETO ESTIVER CERTO E AINDA DER ERRO:**
    Significa que a tabela está bloqueada.
    1. Vá no Supabase > SQL Editor.
    2. Cole e rode: `ALTER TABLE public.reservas DISABLE ROW LEVEL SECURITY;`
    """)







