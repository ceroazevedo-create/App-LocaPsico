# --- 5. TELA PRINCIPAL (CORRIGIDA) ---

def main():
    # HEADER SUPERIOR (Igual ao print)
    c1, c2, c3 = st.columns([2, 4, 2])
    with c1:
        st.markdown("<div class='logo'><span class='logo-icon'>L</span> LOCAPSICO</div>", unsafe_allow_html=True)
    with c2:
        # Navegação Central (Agenda / Painel) -> O ERRO ESTAVA AQUI
        nav = st.radio("Navegação", ["📅 AGENDA", "⚙️ MEU PAINEL"], horizontal=True, label_visibility="collapsed")
    with c3:
        if 'user' in st.session_state:
            email_short = st.session_state['user'].email.split('@')[0].upper()
            st.markdown(f"<div style='text-align:right'><b>{email_short}</b><br><span style='color:#0d9488; font-size:12px'>TERAPEUTA</span></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:right; color:#999'>Visitante</div>", unsafe_allow_html=True)

    # LOGIN CHECK
    if 'user' not in st.session_state:
        login_screen()
        return

    if "AGENDA" in nav:
        # --- BARRA DE COMANDOS DA AGENDA ---
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Linha 1: Seleção de Sala (Abas Largas)
        sala_selecionada = st.radio("Sala", ["Sala 1", "Sala 2"], horizontal=True, label_visibility="collapsed")
        
        st.markdown("---")
        
        # Linha 2: Controles de Data (< Janeiro >)
        col_nav1, col_nav2, col_nav3 = st.columns([1, 6, 2])
        with col_nav1:
            if st.button("◀", key="prev_week"): mudar_semana(-7)
        with col_nav2:
            inicio = st.session_state['data_referencia'] - timedelta(days=st.session_state['data_referencia'].weekday())
            fim = inicio + timedelta(days=6)
            # Tenta pegar o nome do mês em inglês mesmo para evitar erro de locale no servidor
            mes_str = inicio.strftime("%B") 
            st.markdown(f"<h3 style='text-align:center; margin:0'>{inicio.day} - {fim.day} {mes_str}</h3>", unsafe_allow_html=True)
        with col_nav3:
            if st.button("▶", key="next_week"): mudar_semana(7)
            
        # Botão Hoje
        if st.button("Ir para Hoje"): st.session_state['data_referencia'] = datetime.date.today()

        # --- A GRADE (GRID) ---
        renderizar_grade(sala_selecionada, is_admin=st.session_state.get('is_admin', False))
        
        # --- FORMULÁRIO FLUTUANTE (Para Agendar) ---
        with st.expander("➕ CLIQUE AQUI PARA AGENDAR UM HORÁRIO", expanded=False):
            with st.form("quick_add"):
                st.write(f"Agendar na **{sala_selecionada}**")
                c_data, c_hora = st.columns(2)
                dt_input = c_data.date_input("Dia")
                hr_input = c_hora.selectbox("Horário", [f"{h:02d}:00" for h in range(7, 23)])
                
                if st.form_submit_button("Confirmar Reserva"):
                    # Salva no banco
                    h_fim = f"{int(hr_input[:2])+1:02d}:00"
                    dados = {
                        "sala_nome": sala_selecionada,
                        "data_reserva": str(dt_input),
                        "hora_inicio": hr_input,
                        "hora_fim": h_fim,
                        "user_id": st.session_state['user'].id,
                        "email_profissional": st.session_state['user'].email,
                        "valor_cobrado": 32.00
                    }
                    try:
                        supabase.table("reservas").insert(dados).execute()
                        st.success("Agendado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

    else:
        # TELA MEU PAINEL (Simplificada)
        st.title("Meu Painel")
        st.info("Aqui você verá seu histórico financeiro e de atendimentos.")
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

def login_screen():
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("LocaPsico")
        st.markdown("Acesse sua conta")
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                user = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state['user'] = user.user
                st.session_state['is_admin'] = (email == "admin@admin.com.br")
                st.rerun()
            except:
                st.error("Erro de login: Verifique e-mail e senha.")

if __name__ == "__main__":
    main()



