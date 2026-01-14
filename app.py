"Atue como um Especialista Sênior em CSS e Design de Interface Mobile para Streamlit.

O OBJETIVO: Transformar meu calendário de grade gigante (estilo Desktop) em uma visualização ultra-compacta e densa no mobile, inspirada diretamente na densidade do Google Agenda.

A SITUAÇÃO ATUAL: Tenho um grid de 7 colunas (st.columns). Dentro de cada coluna, tenho blocos (containers ou elementos visuais) que representam os horários. Eles são muito grandes, com muito padding e texto grande, tornando a visualização mobile impossível ou feia.

A MISSÃO TÁTICA (CSS INJECTION): Gere um bloco de código Python com st.markdown(..., unsafe_allow_html=True) contendo CSS que, APENAS em telas menores que 768px, realize uma compactação agressiva:

Colunas Anoréxicas: Mire em [data-testid="column"]. Reduza o padding lateral para quase zero (padding: 0 2px !important;).

Células Compactas: Mire nos elementos internos que formam os blocos de horário (assuma que são divs dentro das colunas, talvez com uma classe específica ou genericamente div[data-testid^="st"] > div).

Altura Mínima: Force uma altura muito pequena (ex: min-height: 30px !important; ou menos).

Padding/Margin Zero: Remova qualquer espaçamento interno e externo (padding: 1px !important; margin: 1px 0 !important;).

Tipografia Microscópica: Reduza drasticamente o tamanho da fonte para caber (ex: font-size: 0.65rem !important;). O texto deve ser legível apenas com esforço, priorizando a visão geral do grid.

Conteúdo Cortado: Adicione overflow: hidden; text-overflow: ellipsis; white-space: nowrap; para que nomes longos não quebrem o layout.

Coluna de Horários (Eixo Y): Aplique a mesma compactação extrema na primeira coluna que mostra as horas, para alinhar com as células.
