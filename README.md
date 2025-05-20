# FarmTech Solutions: Sistema de Irrigação Inteligente - Simulação, Gerenciamento e Análise Avançada

Este projeto abrangente desenvolve e simula um sistema de irrigação inteligente, desde o controle embarcado no ESP32, passando por um backend Python robusto para gerenciamento e análise de dados, até um dashboard interativo em Streamlit com inteligência climática e suporte à decisão.

## 1. Simulação de Sistema de Irrigação Inteligente (ESP32 - Wokwi)

* **Visão Geral:** Simula um sistema de irrigação inteligente na plataforma Wokwi.com utilizando um microcontrolador ESP32. Monitora em tempo real umidade do solo, pH (simulado por LDR) e níveis de nutrientes Fósforo (P) e Potássio (K) (simulados por botões) para acionar uma bomba de irrigação (LED/Relé).
* **Diferencial:** A lógica de controle da irrigação possui parâmetros definidos a partir de uma **pesquisa simulada de mercado e consulta a referências agronômicas**, buscando replicar critérios realistas para a otimização do uso da água e saúde das culturas.
* **Componentes Chave:**
    * **ESP32 Dev Module:** Cérebro do sistema.
    * **Sensor de Umidade:** DHT22 (fornece leituras contínuas).
    * **Sensor de pH (Simulado):** LDR (`ldrPH`) em circuito divisor de tensão com resistor (`rLDR` de 10kΩ), convertendo luminosidade para escala de pH (0-14).
    * **Sensores de Nutrientes (P/K):** Botões (`btnP`, `btnK`) indicando presença/ausência.
    * **Bomba de Irrigação (Simulada):** LED (`ledRele`) com resistor (`rLedRele` de 220Ω) visualizando o estado do relé.
* **Lógica de Irrigação Inteligente (Parâmetros de Referência):**
    * Umidade Crítica Baixa (Emergência): < 15.0%
    * Umidade Mínima (Gatilho Principal): < 20.0%
    * Umidade Alta (Parar Irrigação): > 30.0%
    * Faixa de pH Ideal: 5.5 – 6.5
    * Faixa de pH Crítica (Não Irrigar, exceto emergência): < 4.5 ou > 7.5
* **Hierarquia e Regras de Decisão Implementadas:**
    1.  **Prioridade Máxima - Irrigação de Emergência:** Umidade < 15% -> ATIVA bomba, independentemente de outros fatores.
    2.  **Condição Restritiva - pH Crítico:** Sem emergência de umidade, mas pH < 4.5 ou > 7.5 -> DESATIVA bomba.
    3.  **Condição Principal - Irrigação Otimizada:**
        * Umidade < 20% (e não crítica, pH não crítico):
            * **E** pH na faixa ideal (5.5-6.5): ATIVA bomba. "Intensidade" modulada pela presença de P e K (P e K presentes: normal; P ou K presente: reduzida; P e K ausentes: mínima).
            * **E** pH fora da ideal, mas não crítico: DESATIVA bomba.
    4.  **Condição de Interrupção - Umidade Alta:** Umidade > 30% -> DESATIVA bomba.
    5.  **Padrão:** Bomba DESATIVADA.
* **Teste:** Compilação com PlatformIO no VS Code (`Build ✓`) e simulação via `Wokwi: Start Simulation`. Saídas e lógica validadas pelo "Serial Monitor".

## 2. Sistema Python de Gerenciamento e Análise Avançada de Dados (`gerenciador_dados.py`)

* **Objetivo:** Fornecer uma solução de backend robusta para armazenar, gerenciar, e analisar os dados de irrigação, transformando-os em insights acionáveis.
* **Arquitetura e Tecnologias (Python):**
    * **Linguagem:** Python 3.x.
    * **Banco de Dados:** SQLite (`farmtech_phd_data_final_v2.db`, nome configurável), com ORM SQLAlchemy para modelagem de dados orientada a objetos e interação segura.
    * **Manipulação/Análise:** Pandas e NumPy para estruturação, limpeza, transformação e cálculos.
    * **Interface:** CLI interativa com Rich para apresentação formatada e prompts guiados.
    * **Configuração Externa:** Todos os parâmetros operacionais (limiares de irrigação, configs de ML, custos) gerenciados via arquivo YAML (`farmtech_config_phd.yaml`), conferindo flexibilidade sem alterar código-fonte.
    * **Geração de Dados Iniciais:** Script `dados_para_banco.py` para gerar automaticamente 50 cenários de teste variados e extremos para popular o BD.
    * **Modelagem Preditiva:**
        * **Machine Learning:** Scikit-learn para treinar um `RandomForestClassifier` para classificação de risco de emergência (umidade criticamente baixa ou pH fora da faixa crítica).
        * **Séries Temporais:** Statsmodels para modelo ARIMA para forecast (previsão) de umidade do solo.
    * **Geração de Relatórios:** ReportLab para criar relatórios analíticos detalhados em PDF.
    * **Gerenciamento de Dependências:** Script principal (`gerenciador_dados.py`) verifica e tenta auto-instalar bibliotecas Python ausentes via `pip`.
* **Estrutura da Tabela SQL (`leituras_sensores_phd_v2`):**
    * Campos: `id` (INTEGER, PK, Autoincrement), `timestamp` (DATETIME, UNIQUE, NOT NULL, UTC), `umidade` (REAL, NOT NULL), `ph_estimado` (REAL, NOT NULL), `fosforo_presente` (BOOLEAN, NOT NULL), `potassio_presente` (BOOLEAN, NOT NULL), `temperatura` (REAL), `bomba_ligada` (BOOLEAN, NOT NULL).
    * **Diferencial da Tabela:** Campo `decisao_logica_esp32` (STRING) armazena a descrição textual do motivo da decisão tomada pela lógica do ESP32, vital para auditoria, correlação com condições ambientais/nutrientes, e refinamento da lógica.
* **Funcionalidades Detalhadas (CLI):**
    * **Gerenciamento de Dados (CRUD):** Inserção manual (com simulação da lógica ESP32 para sugerir estado da bomba e motivo), consulta (todos ou por ID), atualização (ex: pH de uma leitura), e remoção (com confirmação).
    * **Suite de Análises Avançadas:**
        * Análise Estatística Descritiva (média, mediana, desvio padrão, quartis, min/max) para umidade, pH, temperatura.
        * Detecção Inteligente de Anomalias (método Z-score) para sinalizar possíveis falhas ou eventos extremos.
        * Análise de Correlação (matriz de Pearson) entre leituras e estado da bomba.
        * Modelo Preditivo de Risco de Emergência (treinamento, previsão, análise de importância das features - `feature_importance`).
        * Forecast de Umidade do Solo (ARIMA com alerta proativo para níveis críticos futuros).
        * Geração de Relatório Analítico em PDF consolidando todas as análises.
* **Execução:** `python gerenciador_dados.py`. Na primeira execução, verifica/instala dependências, cria BD (se não existir), popula com dados de exemplo e cria `farmtech_config_phd.yaml`.

## 3. Projeto "Ir Além": Dashboard Interativo com Inteligência Climática usando API (`dashboard_avancado.py`)

* **Objetivo:** Complementar o backend com uma interface web (Streamlit) para visualização dinâmica, simulação interativa e integração de inteligência climática em tempo real, focando na usabilidade e suporte à decisão.
* **Destaques e Funcionalidades:**
    * **Visualização Dinâmica de Dados Históricos:** Gráficos de linha interativos (Plotly Express) de umidade, pH, temperatura. Gráfico de barras para acionamento da bomba. Filtros de período (data inicial/final) e tabela de dados detalhada.
    * **Integração com API Meteorológica (Meteoblue):**
        * Busca e exibe dados climáticos atuais e previsão para próximos dias (pacote `basic-day`) e previsão horária detalhada (pacote `basic-1h`) para geolocalização configurável.
        * Usa chave API da Meteoblue: `5239OsFXJijKVSDq` (embutida no código para demonstração).
        * Apresenta temp. max/min, precipitação, probabilidade de chuva, pictocode (diário); temp. horária, precipitação horária, prob. chuva horária.
    * **Simulador "What-If" Avançado com Inteligência Climática:**
        * Usuário insere valores hipotéticos de sensores (umidade, pH, P, K) via sliders e botões.
        * Sistema simula decisão da lógica de irrigação (replicada do ESP32 em Python).
        * **Crucialmente, incorpora a previsão de chuva atual da API Meteoblue** para ajustar a recomendação final (ex: recomendar não irrigar/adiar se chuva significativa prevista).
        * Realiza **"Análise de Risco Adicional"** alertando se os inputs já configuram condição preocupante.
        * Calcula e exibe **"Economia Estimada"** (R$) se a não irrigação for devido à previsão de chuva.
    * **Módulos de Suporte à Decisão (Integrados ao Histórico):**
        * **Painel de Alertas Inteligentes e Proativos:** Na aba de histórico, analisa dados recentes e exibe alertas visuais (`st.warning`/markdown) para umidade criticamente baixa ou pH fora da faixa de segurança.
        * **Estimativa de Custos Operacionais da Irrigação:** Calcula custos de água e energia para o período selecionado, baseados no tempo total de acionamento da bomba (inferido pela frequência dos registros e tempo de ciclo padrão) e parâmetros de custo do `farmtech_config_phd.yaml`.
        * **Mini-Diagnóstico do Sistema e Sugestões de Otimização (Beta):** Analisa umidade média no acionamento da bomba, pH médio vs. ideal, frequência de condições críticas, e oferece sugestões contextuais para otimizar parâmetros ou investigar problemas.
* **Execução:** `python dashboard_avancado.py` (após `gerenciador_dados.py` ter criado o BD). Verifica/instala dependências e lança o servidor Streamlit (geralmente `http://localhost:8501`).

Este projeto integrado representa uma solução completa e analiticamente rica para o desafio da irrigação inteligente, desde a simulação do hardware e lógica embarcada até uma plataforma robusta para análise de dados, suporte à decisão e demonstração do valor da agricultura de precisão com inteligência climática.
