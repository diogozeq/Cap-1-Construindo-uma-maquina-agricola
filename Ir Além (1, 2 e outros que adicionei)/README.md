---
## 4. Projeto "Ir Além": Dashboard Interativo com Inteligência Climática e Analítica Avançada

Para transcender os requisitos básicos e demonstrar o verdadeiro potencial de um sistema de irrigação inteligente orientado a dados, desenvolvi um dashboard interativo (`dashboard_avancado.py`) utilizando a biblioteca Streamlit. Esta aplicação web não apenas visualiza os dados coletados, mas também integra inteligência climática em tempo real e oferece ferramentas de simulação e diagnóstico, representando um salto qualitativo em termos de usabilidade e suporte à decisão.

### 4.1. Funcionalidades Chave do Dashboard Avançado:

* **Visualização Dinâmica e Interativa de Dados Históricos:**
    * Apresentação dos dados históricos de umidade do solo, pH estimado e temperatura em gráficos de linha interativos (gerados com Plotly Express), permitindo a fácil identificação de tendências, padrões e correlações visuais.
    * Gráfico de barras dedicado para visualizar o histórico de acionamento da bomba de irrigação, facilitando a análise da frequência e duração dos ciclos.
    * Filtros de período (data inicial e final) para que o usuário possa focar a análise em intervalos específicos do histórico de dados, adaptando a visualização às suas necessidades investigativas.
    * Tabela de dados detalhada e formatada para o período selecionado, permitindo uma inspeção granular dos registros.

* **Integração com API Meteorológica em Tempo Real (Meteoblue):**
    * O dashboard busca e exibe dados climáticos atuais e previsões para os próximos dias (através do pacote `basic-day` da Meteoblue) e uma previsão horária detalhada (pacote `basic-1h`) para uma geolocalização configurável (Latitude/Longitude) diretamente na interface.
    * A chave de API da Meteoblue (`5239OsFXJijKVSDq`) foi embutida no código para facilitar a demonstração e o acesso imediato a esta funcionalidade. [cite: 1]
    * São apresentadas informações cruciais como temperatura máxima/mínima, precipitação total acumulada, probabilidade de chuva e um pictograma representativo do tempo para a previsão diária.
    * A previsão horária detalha temperatura, precipitação e probabilidade de chuva para as próximas horas, fornecendo um panorama de curto prazo essencial para decisões de irrigação.

* **Simulador "What-If" Inteligente com Influência Climática:**
    * Uma ferramenta interativa poderosa que permite ao usuário (como um gestor agrícola) inserir valores hipotéticos para os sensores da fazenda (umidade, pH, presença de Fósforo e Potássio) através de sliders e botões de rádio intuitivos.
    * O sistema então simula a decisão da lógica de irrigação (a mesma lógica implementada no ESP32, agora replicada em Python), mas com um diferencial crucial: **ele considera a previsão de chuva atual obtida da API Meteoblue** para ajustar a recomendação final. Por exemplo, mesmo que os sensores da fazenda indiquem uma necessidade iminente de irrigação, se houver uma previsão de chuva significativa nas próximas horas, o sistema inteligentemente recomendará não irrigar ou adiar a irrigação.
    * Antes de apresentar a recomendação, o simulador realiza uma **"Análise de Risco Adicional"**, alertando o usuário se os próprios valores de entrada para a simulação já configurarem uma condição agronomicamente preocupante (ex: umidade do solo em nível crítico ou pH fora da faixa agronomicamente aceitável).
    * **Quantificação de Benefício:** O simulador calcula e exibe a **"Economia Estimada"** (em R$) se a decisão de não irrigar for tomada devido à previsão de chuva, mas a irrigação teria ocorrido sem essa informação climática. Isso tangibiliza o valor da integração de dados externos.

* **Módulos de Suporte à Decisão Integrados ao Histórico de Dados:**
    * **Painel de Alertas Inteligentes e Proativos:** Na aba de visualização do histórico de dados, o sistema analisa automaticamente os registros mais recentes do período selecionado e exibe alertas visuais destacados (`st.warning` ou markdown formatado) para condições como umidade criticamente baixa ou pH fora da faixa de segurança recomendada, permitindo uma rápida identificação de possíveis problemas ou necessidade de intervenção.
    * **Estimativa de Custos Operacionais da Irrigação:** Também na aba de histórico, são calculados e exibidos os custos operacionais estimados com água e energia para o período de dados selecionado. Este cálculo é baseado no tempo total de acionamento da bomba (inferido pela frequência dos registros e por um tempo de ciclo padrão configurável) e nos parâmetros de custo (R$/m³ de água, R$/kWh de energia, vazão e potência da bomba) definidos no arquivo `farmtech_config_phd.yaml`.
    * **Mini-Diagnóstico do Sistema e Sugestões de Otimização (Versão Beta):** Uma seção expansível na aba de histórico oferece uma análise preliminar do comportamento do sistema de irrigação com base nos dados do período selecionado. Inclui:
        * Análise da umidade média do solo no momento em que a bomba foi acionada, comparando-a com os limiares ideais.
        * Avaliação do pH médio do período em relação à faixa ideal configurada para a cultura.
        * Contagem da frequência de ocorrência de condições críticas (umidade excessivamente baixa ou pH fora dos limites críticos).
        * Com base nessas análises, o sistema oferece sugestões informativas e contextuais para potenciais otimizações nos parâmetros de irrigação ou para investigar possíveis problemas com sensores ou manejo do solo.

### 4.2. Como Executar o Dashboard Interativo:

1.  Garanta que o banco de dados (`farmtech_phd_data_final_v2.db`) já foi criado e preferencialmente populado através da execução prévia do script `gerenciador_dados.py`.
2.  No seu terminal, navegue até a pasta raiz do projeto `FarmTech_ESP32`.
3.  Execute o seguinte comando:
    ```bash
    python dashboard_avancado.py
    ```
4.  Este comando verificará as dependências Python necessárias (como Streamlit, Pandas, Plotly, etc.) e tentará instalá-las automaticamente se estiverem ausentes. Em seguida, ele lançará o servidor Streamlit.
5.  O dashboard será aberto automaticamente no seu navegador web padrão. Caso isso não ocorra, acesse o endereço fornecido no terminal (geralmente `http://localhost:8501`).
6.  Interaja com as diferentes abas ("Histórico e Diagnóstico", "Clima (Meteoblue)", "Simulador What-If") e com os widgets (sliders, botões, filtros de data) para explorar todas as funcionalidades.

Este dashboard "Ir Além" visa demonstrar como os dados coletados podem ser transformados em uma ferramenta visual, interativa e inteligente de apoio à decisão, agregando valor significativo ao sistema de irrigação.