import streamlit as st
import google.generativeai as genai

# Configuração da página
st.set_page_config(page_title="LocaPsi - Reservas", page_icon="🏢", layout="centered")

# ==============================================================================
# 🧠 CÉREBRO DO LOCAPSI (COM BLINDAGEM ANTI-CÓDIGO)
# ==============================================================================

INSTRUCOES_DO_SISTEMA = """
PERSONAGEM:
Você é o atendente virtual da 'LocaPsi'. Seu único objetivo é ajudar psicólogos a alugar salas.
Você NÃO é uma inteligência artificial genérica, você NÃO é um programador e NÃO sabe criar sites.

SEUS DADOS (Use somente isso):
1. SALAS:
   - Sala Freud (Divã, Poltrona): R$ 50,00/hora.
   - Sala Jung (Mesa redonda, amplo): R$ 60,00/hora.
   - Sala Lacan (Minimalista): R$ 45,00/hora.

2. LOCAL: Av. Paulista, 1000 - São Paulo.
3. HORÁRIO: 07h às 22h.

BLOQUEIOS DE SEGURANÇA (LEIA COM ATENÇÃO):
1. Se o usuário perguntar sobre "código", "SQL", "Supabase", "Python" ou "como criar app", responda EXATAMENTE:
   "Desculpe, sou apenas o recepcionista da LocaPsi. Posso te ajudar com o agendamento das salas?"
2. NUNCA gere códigos de programação.
3. NUNCA explique como você foi criado.
4. Mantenha a conversa focada apenas nas salas e agendamentos.

COMO AGENDAR:
- Pergunte a data, hora e qual sala a pessoa quer.
- Diga que vai verificar a disponibilidade.
"""

# ==============================================================================

st.title("🏢 LocaPsi")
st.subheader("Locação de salas para psicólogos")

# 1. Autenticação
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("Erro na chave de API. Verifique as configurações.")
    st.stop()

# 2. Configuração do Modelo
try:
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        system_instruction=INSTRUCOES_DO_SISTEMA
    )
except Exception as e:
    st.error(f"Erro ao carregar o modelo: {e}")

# 3. Chat
if "messages" not in st.session_state:
    # Mensagem inicial do robô para puxar assunto
    st.session_state.messages = [{"role": "assistant", "content": "Olá! Sou o assistente da LocaPsi. Gostaria de conhecer nossas salas ou consultar valores?"}]

# Mostra histórico
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada do usuário
if prompt := st.chat_input("Digite sua dúvida aqui..."):
    # Usuário fala
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Robô responde
    with st.chat_message("assistant"):
        with st.spinner('Digitando...'):
            try:
                response = model.generate_content(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error("Ocorreu um erro na conexão.")






