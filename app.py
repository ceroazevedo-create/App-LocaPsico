import streamlit as st
import google.generativeai as genai

# Configuração da página
st.set_page_config(page_title="LocaPsi", page_icon="🏢")

# ==============================================================================
# 👇👇👇 ÁREA DE COLAGEM (AQUI ENTRA O SEU TEXTO DO AI STUDIO) 👇👇👇
# ==============================================================================

# Dica: Mantenha as três aspas (""") no começo e no fim.
# Cole seu texto no meio delas.

INSTRUCOES_DO_SISTEMA = """

1. Propósito e Identidade
Objetivo: Aplicativo de locação de salas para psicólogos e terapeutas.
Identidade Visual: Minimalista e profissional (Teal/Emerald). Logo: Marcador de mapa com o símbolo Psi (Ψ).
Nomenclatura: Aplicativo "LocaPsico". Admin master identificado como "Administrador".
2. Regras de Acesso e Perfis
Autenticação: Baseado em Supabase Auth (E-mail/Senha).
Funções:ADMIN(acesso total) eUSUÁRIO(psicólogos/terapeutas).
Administrador:admin@admin.com.br(senha inicial:123mudar).
3. Regras de Reserva (Agenda)
Salas: "Sala 1" e "Sala 2".
Horários: Das 07:00 às 22:00 (intervalos de 1h).
Valor da Locação: Dinâmico, definido pelo Administrador (inicial: R$ 32,00). O valor é fixado no momento da reserva (preçoNaReserva).
Cancelamento:
Usuário: Permitido apenas com antecedência mínima de 24 horas.
Administrador: Permissão total de cancelamento a qualquer momento.
4. Gestão de Feriados e Bloqueios
Feriados Nacionais: Lista fixa de dados (ex: 01-01, 25-12, etc).
Bloqueio Global: Chave mestre que impede agendamentos em qualquer feriado.
Exceções (Lista branca): Admin pode liberar dados específicos de feriados individualmente.
5. Funcionalidades de Gestão (Painel Admin)
Faturamento Mensal:
Visualização de receita bruta e total de reservas por mês/ano.
Baixe o relatório PDF Geral.
Faturamento Individual:
Filtro por profissional e mês.
Resumo de gastos e lista de atendimentos.
Identificação de perfis administrativos como "Administrador".
Baixe o relatório PDF Individual.
Gestão de Usuários: Pesquisa de profissionais, visualização de dados e exclusão de contas (com remoção em cascata de agendamentos).
6. Experiência do Usuário (Dashboard)
Resumo Individual: Total investido e próximas reservas.
Reserva Inteligente: Sugestão baseada nos hábitos de agendamento (dia da semana, hora e sala preferida).
Segurança: Alteração de senha direta pelo painel do profissional.
7. Técnica de Pilha
Front-endReact 19, Tailwind CSS, Lucide React (Ícones).
Back-end/Banco: Supabase (PostgreSQL paraperfis,reservaseapp_configs).
Relatórios: jsPDF e jsPDF-AutoTable.


"""

# ==============================================================================
# 👆👆👆 FIM DA ÁREA DE COLAGEM 👆👆👆
# ==============================================================================


st.title("🏢 LocaPsi - Reservas")

# 1. Autenticação
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("Erro na chave de API. Verifique os Secrets do Streamlit.")
    st.stop()

# 2. Configuração do Modelo
# Aqui nós pegamos o texto que você colou lá em cima e enviamos para o Google
try:
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        system_instruction=INSTRUCOES_DO_SISTEMA
    )
except Exception as e:
    st.error(f"Erro ao configurar o modelo: {e}")

# 3. Chat (Interface visual)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostra o histórico de mensagens na tela
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Campo para digitar a pergunta
if prompt := st.chat_input("Olá! Gostaria de saber mais sobre as salas..."):
    # Mostra a mensagem do usuário
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Gera a resposta usando suas instruções
    with st.chat_message("assistant"):
        with st.spinner('O LocaPsi está consultando...'):
            try:
                response = model.generate_content(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Erro na conexão: {e}")






