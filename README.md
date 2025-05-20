# FarmTech Solutions: Sistema de Irrigação Inteligente - Simulação, Gerenciamento e Análise Avançada

Este README compila as informações detalhadas de todas as três entregas do projeto "FarmTech Solutions", que aborda um sistema de irrigação inteligente de ponta a ponta: desde a simulação do controle embarcado em um ESP32, passando por um *backend* Python robusto para gerenciamento e análise de dados, até um *dashboard* interativo em Streamlit que incorpora inteligência climática e suporte à decisão.

Para os detalhes técnicos aprofundados e arquivos de cada parte, você pode consultar as suas respectivas pastas no projeto.

---

## 1. Simulação de Sistema de Irrigação Inteligente (ESP32 - Wokwi)

A primeira parte do projeto foca na simulação do hardware e da lógica de controle embarcada.

* **Visão Geral:** Este componente simula um sistema de irrigação inteligente na plataforma Wokwi.com, utilizando um microcontrolador ESP32. Ele monitora em tempo real a umidade do solo, pH (simulado por LDR) e os níveis de nutrientes Fósforo (P) e Potássio (K) (simulados por botões) para acionar uma bomba de irrigação (representada por um LED/Relé).

* **Diferencial:** A lógica de controle da irrigação possui parâmetros definidos a partir de uma **pesquisa simulada de mercado e consulta a referências agronômicas**. Isso busca replicar critérios realistas para a otimização do uso da água e a promoção da saúde das culturas.

* **Componentes Chave:**
    * **ESP32 Dev Module:** O cérebro do sistema, responsável por processar as leituras e tomar decisões.
    * **Sensor de Umidade:** DHT22, fornecendo leituras contínuas de umidade do solo.
    * **Sensor de pH (Simulado):** Um LDR (`ldrPH`) configurado em um circuito divisor de tensão com um resistor (`rLDR` de 10kΩ), convertendo a luminosidade em uma escala de pH de 0 a 14.
    * **Sensores de Nutrientes (P/K):** Botões (`btnP`, `btnK`) que simulam a presença ou ausência desses nutrientes no solo.
    * **Bomba de Irrigação (Simulada):** Um LED (`ledRele`) com um resistor (`rLedRele` de 220Ω), visualizando o estado de acionamento do relé da bomba.

* **Lógica de Irrigação Inteligente (Parâmetros de Referência):**
    * **Umidade Crítica Baixa (Emergência):** Menor que 15.0%
    * **Umidade Mínima (Gatilho Principal):** Menor que 20.0%
    * **Umidade Alta (Parar Irrigação):** Maior que 30.0%
    * **Faixa de pH Ideal:** Entre 5.5 e 6.5
    * **Faixa de pH Crítica (Não Irrigar, exceto emergência):** Menor que 4.5 ou maior que 7.5

* **Hierarquia e Regras de Decisão Implementadas:**
    1.  **Prioridade Máxima - Irrigação de Emergência:** Se a umidade for menor que 15%, a bomba é **ativada** independentemente de outros fatores.
    2.  **Condição Restritiva - pH Crítico:** Se não houver emergência de umidade, mas o pH estiver menor que 4.5 ou maior que 7.5, a bomba é **desativada**.
    3.  **Condição Principal - Irrigação Otimizada:**
        * Se a umidade for menor que 20% (e não crítica, e pH não crítico):
            * **E** o pH estiver na faixa ideal (5.5-6.5): A bomba é **ativada**. A "intensidade" da irrigação é modulada pela presença de P e K (P e K presentes: normal; P ou K presente: reduzida; P e K ausentes: mínima).
            * **E** o pH estiver fora da faixa ideal, mas não crítico: A bomba é **desativada**.
    4.  **Condição de Interrupção - Umidade Alta:** Se a umidade for maior que 30%, a bomba é **desativada**.
    5.  **Padrão:** Em todas as outras condições, a bomba permanece **desativada**.

* **Teste:** O código foi compilado usando PlatformIO no VS Code (`Build ✓`) e simulado via `Wokwi: Start Simulation`. As saídas e a lógica foram validadas através do "Serial Monitor" da plataforma.

---

## 2. Sistema Python de Gerenciamento e Análise Avançada de Dados (`gerenciador_dados.py`)

Esta segunda entrega do projeto focou no desenvolvimento de uma solução de *backend* robusta utilizando Python. O objetivo primordial foi criar um sistema capaz de armazenar, gerenciar e, crucialmente, analisar os dados de irrigação coletados, transformando-os em *insights* valiosos e acionáveis.

* **Objetivo:** Fornecer uma solução de *backend* robusta para armazenar, gerenciar e analisar os dados de irrigação, transformando-os em *insights* acionáveis.

* **Arquitetura e Tecnologias (Python):**
    * **Linguagem:** Python 3.x.
    * **Banco de Dados:** **SQLite** (`farmtech_phd_data_final_v2.db`, nome configurável), com **SQLAlchemy** como ORM para modelagem de dados orientada a objetos e interação segura.
    * **Manipulação/Análise:** **Pandas** e **NumPy** para estruturação, limpeza, transformação e cálculos complexos.
    * **Interface:** CLI interativa construída com a biblioteca **Rich** para apresentação formatada em tabelas e *prompts* guiados.
    * **Configuração Externa:** Todos os parâmetros operacionais (limiares da lógica de irrigação, configurações de modelos de Machine Learning, parâmetros de custo) são gerenciados via um arquivo **YAML** externo (`farmtech_config_phd.yaml`), o que confere grande flexibilidade e facilita ajustes sem a necessidade de alterar o código-fonte.
    * **Geração de Dados Iniciais:** O script `dados_para_banco.py` foi criado para gerar automaticamente 50 cenários de teste variados e extremos, populando o banco de dados.
    * **Modelagem Preditiva:**
        * **Machine Learning:** **Scikit-learn** foi utilizado para treinar um `RandomForestClassifier` para classificação de risco de emergência (definida por umidade criticamente baixa ou pH fora da faixa crítica).
        * **Séries Temporais:** **Statsmodels** foi empregado para a implementação de um modelo ARIMA para o *forecast* (previsão) de umidade do solo.
    * **Geração de Relatórios:** A biblioteca **ReportLab** foi utilizada para a criação de relatórios analíticos detalhados em formato PDF.
    * **Gerenciamento de Dependências:** O script principal (`gerenciador_dados.py`) inclui um mecanismo para verificar a presença das bibliotecas Python necessárias e tenta realizar a auto-instalação via `pip install --user...` caso alguma esteja ausente.

* **Estrutura da Tabela SQL (`leituras_sensores_phd_v2`):**
    * **Campos:** `id` (INTEGER, PK, Autoincrement), `timestamp` (DATETIME, UNIQUE, NOT NULL, armazenado em UTC), `umidade` (REAL, NOT NULL), `ph_estimado` (REAL, NOT NULL), `fosforo_presente` (BOOLEAN, NOT NULL), `potassio_presente` (BOOLEAN, NOT NULL), `temperatura` (REAL), `bomba_ligada` (BOOLEAN, NOT NULL).
    * **Diferencial da Tabela:** A inclusão do campo `decisao_logica_esp32` (STRING) é um diferencial importante. Ele armazena a descrição textual do motivo da decisão tomada pela lógica de controle embarcada no ESP32. Isso é vital para auditoria, correlação entre as condições ambientais/nutrientes e as ações de controle, e para o refinamento contínuo da lógica.

* **Funcionalidades Detalhadas (CLI):**
    * **Gerenciamento de Dados (CRUD):**
        * **Inserção (Create):** Permite a adição manual de novas leituras. Durante a inserção, a lógica de irrigação do ESP32 é simulada para sugerir o estado da bomba e o motivo da decisão, enriquecendo o registro. O banco é também inicialmente populado automaticamente com 50 cenários de teste diversificados.
        * **Consulta (Read):** Oferece visualização flexível de todos os registros armazenados (ordenados cronologicamente) ou a consulta detalhada de um registro específico através do seu ID. Os dados são apresentados em tabelas formatadas para fácil leitura e interpretação no console.
        * **Atualização (Update):** Permite a modificação de campos específicos de registros existentes (demonstrado com a funcionalidade de atualizar o pH de uma leitura), com as devidas validações para manter a integridade dos dados.
        * **Remoção (Delete):** Possibilita a remoção segura de registros específicos por ID, incluindo uma etapa de confirmação do usuário para prevenir perdas acidentais de dados.
    * **Suite de Análises Avançadas:**
        * **Análise Estatística Descritiva:** Geração e exibição de métricas estatísticas fundamentais (média, mediana, desvio padrão, quartis, valores mínimos e máximos) para as principais variáveis dos sensores (umidade, pH, temperatura).
        * **Detecção Inteligente de Anomalias:** Utilização do método Z-score para identificar automaticamente leituras que se desviam significativamente do padrão normal, crucial para sinalizar falhas de sensores ou eventos extremos.
        * **Análise de Correlação:** Cálculo e apresentação da matriz de correlação de Pearson, permitindo investigar as interdependências entre as leituras dos sensores e o estado de acionamento da bomba.
        * **Modelo Preditivo de Risco de Emergência:** Treinamento de um `RandomForestClassifier` para classificar e prever a probabilidade de o sistema entrar em "emergência", com análise da importância das *features* (`feature_importance`).
        * **Forecast de Umidade do Solo:** Utilização de um modelo ARIMA para realizar previsões das próximas N leituras de umidade do solo, incorporando um **alerta proativo** se o *forecast* indicar níveis críticos.
        * **Geração de Relatório Analítico em PDF:** Capacidade de criar automaticamente um relatório profissional e abrangente em formato PDF, consolidando todas as análises geradas.

* **Execução:**
    1.  Abra seu terminal ou *prompt* de comando e navegue até a pasta raiz do projeto `FarmTech_ESP32`.
    2.  Execute o script com o comando: `python gerenciador_dados.py`.
    3.  Na primeira execução, o script verificará e tentará instalar automaticamente as dependências Python necessárias. O banco de dados `farmtech_phd_data_final_v2.db` será criado e populado com os 50 registros de exemplo (se o banco estiver vazio).
    4.  Siga as opções apresentadas no menu interativo da CLI para explorar todas as funcionalidades de CRUD e análise.
    5.  O arquivo de configuração `farmtech_config_phd.yaml` é criado na primeira execução (se não existir) e permite a customização de diversos parâmetros operacionais.

---

## 3. Projeto "Ir Além do Além": Dashboard Interativo com Inteligência Climática vinda da API (`dashboard_avancado.py`)

Esta iniciativa "Ir Além" buscou explorar ainda mais o potencial da solução, desenvolvendo um *dashboard* interativo utilizando a biblioteca Streamlit. O *dashboard* (`dashboard_avancado.py`) complementa as funcionalidades do `gerenciador_dados.py`, focando na visualização dinâmica, na simulação interativa e na integração com dados climáticos.

* **Objetivo:** Complementar o *backend* com uma interface web (Streamlit) para visualização dinâmica, simulação interativa e integração de inteligência climática em tempo real, focando na usabilidade e suporte à decisão.

* **Destaques e Funcionalidades:**
    * **Visualização Dinâmica e Interativa de Dados Históricos:** Apresentação dos dados históricos de umidade do solo, pH e temperatura em **gráficos de linha interativos** (utilizando Plotly Express). Inclui um gráfico de barras para visualizar o histórico de acionamento da bomba de irrigação. Oferece filtros de período (data inicial e final) e uma tabela de dados detalhada e formatada para o período selecionado.
    * **Integração em Tempo Real com API Meteorológica (Meteoblue):**
        * Busca e exibe dados climáticos atuais e previsão para os próximos dias (pacote `basic-day`) e previsão horária detalhada (pacote `basic-1h`) para uma geolocalização configurável (Latitude/Longitude) diretamente na interface do *dashboard*.
        * Utiliza a chave de API Meteoblue: `5239OsFXJijKVSDq` (embutida no código para facilidade de demonstração).
        * Apresenta informações como temperatura máxima/mínima, precipitação total, probabilidade de chuva e *pictocode* para a previsão diária; e temperatura horária, precipitação horária e probabilidade de chuva para as próximas horas.
    * **Simulador "What-If" Avançado com Inteligência Climática:**
        * Uma ferramenta interativa que permite ao usuário inserir valores hipotéticos para os sensores da fazenda (umidade, pH, presença de P e K) através de *sliders* e botões de rádio.
        * O sistema então simula a decisão da lógica de irrigação (replicada do ESP32 em Python), mas crucialmente, **incorpora a previsão de chuva atual obtida da API Meteoblue** para ajustar a recomendação final. Por exemplo, mesmo que os sensores da fazenda indiquem necessidade de irrigação, se houver previsão de chuva significativa nas próximas horas, o sistema recomendará não irrigar ou adiar a irrigação.
        * Apresenta uma **"Análise de Risco Adicional"** que alerta o usuário se os próprios *inputs* para a simulação já configurarem uma condição preocupante (ex: umidade criticamente baixa ou pH fora da faixa crítica).
        * Calcula e exibe a **"Economia Estimada"** (em R$) se a decisão de não irrigar for tomada devido à previsão de chuva, quantificando o benefício da inteligência climática.
    * **Módulos de Suporte à Decisão Integrados ao Histórico:**
        * **Painel de Alertas Inteligentes e Proativos:** Na aba de visualização do histórico, o sistema analisa os dados mais recentes do período selecionado e exibe alertas visuais destacados (`st.warning` ou `st.error` simulado com markdown) para condições como umidade criticamente baixa ou pH fora da faixa de segurança, permitindo uma rápida identificação de problemas.
        * **Estimativa de Custos Operacionais da Irrigação:** Também na aba de histórico, são calculados e exibidos os custos estimados de água e energia para o período de dados selecionado. Este cálculo é baseado no tempo total de acionamento da bomba (inferido pela frequência dos registros e um tempo de ciclo padrão) e nos parâmetros de custo definidos no `farmtech_config_phd.yaml`.
        * **Mini-Diagnóstico do Sistema e Sugestões de Otimização (Beta):** Uma seção expansível na aba de histórico analisa o comportamento do sistema no período selecionado, incluindo: umidade média no momento do acionamento da bomba, pH médio do período em relação à faixa ideal configurada, e frequência de ocorrência de condições críticas (umidade baixa ou pH crítico). Com base nessas análises, o sistema oferece sugestões informativas e contextuais para otimizar os parâmetros de irrigação ou investigar possíveis problemas.

* **Execução:**
    1.  Certifique-se de que o `gerenciador_dados.py` já foi executado pelo menos uma vez para criar e popular o banco de dados.
    2.  No seu terminal ou *prompt* de comando, navegue até a pasta raiz do projeto.
    3.  Execute o *dashboard* com o comando: `streamlit run dashboard_avancado.py`.
    4.  O script verificará e instalará as dependências ausentes e, em seguida, abrirá o *dashboard* automaticamente em seu navegador web (geralmente em `http://localhost:8501`).

Este projeto integrado representa uma solução abrangente e analiticamente rica para o desafio da irrigação inteligente. O esforço em ir além dos requisitos básicos, especialmente na construção do *dashboard* interativo com inteligência climática e nas funcionalidades analíticas do sistema Python, reflete um profundo engajamento com o tema e um desejo de explorar o potencial máximo das ferramentas e conceitos envolvidos. O resultado é uma suíte de ferramentas que não apenas simula um sistema de irrigação, mas oferece uma plataforma robusta para análise de dados, suporte à decisão e demonstração do valor da agricultura de precisão.
