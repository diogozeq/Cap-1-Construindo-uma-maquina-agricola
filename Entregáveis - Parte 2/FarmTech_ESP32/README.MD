## Entrega 2: Sistema Python de Gerenciamento e Análise Avançada de Dados

Esta fase do projeto concentrou-se na criação de uma solução de *backend* robusta em Python, projetada para armazenar, gerenciar e, de forma crucial, analisar dados de irrigação. O objetivo principal foi transformar esses dados em *insights* valiosos e acionáveis, otimizando os processos agrícolas.

### Arquitetura e Tecnologias Empregadas (Python)

Para construir este sistema, foram utilizadas tecnologias Python consolidadas, reconhecidas por sua eficiência e capacidade:

* **Linguagem de Programação:** Python 3.x, escolhido por sua versatilidade, vasta gama de bibliotecas e facilidade de desenvolvimento.
* **Banco de Dados:** **SQLite**, implementado através do arquivo `farmtech_phd_data_final_v2.db` (nome configurável). A escolha pelo SQLite deve-se à sua simplicidade, portabilidade (baseado em arquivo, sem necessidade de servidor dedicado) e adequação ao escopo de uma simulação detalhada e para prototipagem rápida.
* **ORM (Mapeamento Objeto-Relacional):** **SQLAlchemy** foi utilizado para uma interação elegante e segura com o banco de dados, permitindo uma modelagem de dados orientada a objetos e abstraindo a complexidade do SQL.
* **Manipulação e Análise de Dados:** As bibliotecas **Pandas** e **NumPy** foram fundamentais para a estruturação, limpeza, transformação e para a realização de cálculos complexos sobre os conjuntos de dados.
* **Interface de Linha de Comando (CLI) Interativa:** Para facilitar a interação e demonstração das funcionalidades, a biblioteca **Rich** foi empregada, resultando em uma CLI com apresentação de dados em tabelas formatadas, uso de cores e *prompts* guiados.
* **Configuração Externa:** Todos os parâmetros operacionais, incluindo limiares da lógica de irrigação, configurações de modelos de Machine Learning e parâmetros de custo, são gerenciados através de um arquivo **YAML** externo (`farmtech_config_phd.yaml`), o que confere grande flexibilidade e facilita ajustes sem a necessidade de alterar o código-fonte.
* **Geração de Dados Iniciais:** Para permitir testes e demonstrações robustas, o script `dados_para_banco.py` foi criado para gerar automaticamente 50 cenários de teste variados e extremos, cobrindo diversas condições de umidade, pH e combinações de nutrientes, distribuídos ao longo de 25 dias simulados. Estes dados são utilizados para popular o banco de dados na primeira execução do sistema.
* **Modelagem Preditiva:**
    * **Machine Learning:** **Scikit-learn** foi utilizado para treinar um modelo `RandomForestClassifier` para classificação de risco de emergência.
    * **Séries Temporais:** **Statsmodels** foi empregado para a implementação de um modelo ARIMA para o *forecast* (previsão) de umidade do solo.
* **Geração de Relatórios:** A biblioteca **ReportLab** foi utilizada para a criação de relatórios analíticos detalhados em formato PDF.
* **Gerenciamento de Dependências:** O script principal (`gerenciador_dados.py`) inclui um mecanismo para verificar a presença das bibliotecas necessárias e tenta realizar a auto-instalação caso alguma esteja ausente.

### Estrutura da Tabela SQL e Relação com MER

Os dados operacionais do sistema de irrigação são persistidos na tabela `leituras_sensores_phd_v2` (nome configurável via `farmtech_config_phd.yaml`), cuja estrutura detalhada é:

| Coluna | Tipo | Restrições | Descrição |
| :----------------------- | :------- | :----------------- | :------------------------------------------------------------ |
| `id` | INTEGER | PK, Autoincrement | Identificador único para cada registro de leitura. |
| `timestamp` | DATETIME | UNIQUE, NOT NULL | Data e hora exatas da coleta dos dados (armazenado em UTC). |
| `umidade` | REAL | NOT NULL | Percentual de umidade do solo (ex: 0.0 a 100.0). |
| `ph_estimado` | REAL | NOT NULL | Valor do pH estimado do solo (ex: 0.0 a 14.0). |
| `fosforo_presente` | BOOLEAN | NOT NULL | Indica a presença (True) ou ausência (False) de Fósforo. |
| `potassio_presente` | BOOLEAN | NOT NULL | Indica a presença (True) ou ausência (False) de Potássio. |
| `temperatura` | REAL | | Temperatura ambiente em graus Celsius. |
| `bomba_ligada` | BOOLEAN | NOT NULL | Estado da bomba de irrigação (True = Ligada, False = Desligada). |
| `decisao_logica_esp32` | STRING | | Descrição textual do motivo da decisão tomada pela lógica do ESP32. |

**Justificativa da Estrutura de Dados (Alinhamento com o MER da Fase 2):**
Esta estrutura de tabela foi concebida para ser a representação direta da entidade "RegistroDeLeitura" ou "EventoDeSensoriamento" que seria definida em um Modelo Entidade-Relacionamento (MER) na Fase 2 do projeto. O design visa:

* **Atomicidade e Abrangência:** Cada linha na tabela captura um conjunto completo de leituras de todos os sensores e o estado do sistema (bomba) em um instante específico, garantindo que cada registro seja autocontido e significativo.
* **Integridade Temporal:** O campo `timestamp` (com *constraint* `UNIQUE` e armazenado em UTC) é fundamental. Ele não apenas ordena cronologicamente os eventos, mas também previne a duplicidade de registros e facilita análises de séries temporais e rastreabilidade de eventos.
* **Tipagem Otimizada:** A escolha dos tipos de dados (`REAL` para valores contínuos como umidade e pH, `BOOLEAN` para estados binários como presença de nutrientes e estado da bomba) foi feita para otimizar o armazenamento, garantir a integridade dos dados e melhorar a performance de consultas e análises.
* **Rastreabilidade e Análise de Decisão:** Um diferencial importante é a inclusão do campo `decisao_logica_esp32`. Este campo armazena o motivo textual que levou a lógica de controle embarcada no ESP32 a tomar uma determinada ação (ligar/desligar a bomba). Isso é vital para:
    * Auditar o comportamento do sistema.
    * Correlacionar as condições ambientais e de nutrientes com as ações de controle efetivamente tomadas.
    * Facilitar a depuração da lógica de irrigação e permitir o seu refinamento contínuo com base no desempenho histórico observado.

Esta estrutura de dados garante que todas as informações relevantes, provenientes dos sensores simulados e refletindo o estado do atuador, estejam disponíveis de forma organizada e eficiente, servindo como uma base sólida para as operações CRUD e para as diversas análises avançadas implementadas.

### Funcionalidades Detalhadas do `gerenciador_dados.py` (Interface CLI)

O script `gerenciador_dados.py` constitui o núcleo da Entrega 2, fornecendo uma interface de linha de comando (CLI) interativa e amigável (utilizando a biblioteca Rich) para um gerenciamento completo do ciclo de vida dos dados e para a execução de análises sofisticadas:

* **Gerenciamento de Dados (Operações CRUD):**
    * **Create (Inserção):** Além do povoamento inicial e automático do banco com 50 cenários de teste diversificados (provenientes de `dados_para_banco.py`), o sistema permite a adição manual de novas leituras. Durante a inserção manual, a lógica de irrigação do ESP32 é simulada para sugerir o estado da bomba e o motivo da decisão, enriquecendo o registro.
    * **Read (Consulta):** Oferece visualização flexível de todos os registros armazenados (ordenados cronologicamente) ou a consulta detalhada de um registro específico através do seu ID. Os dados são apresentados em tabelas formatadas para fácil leitura e interpretação no console.
    * **Update (Atualização):** Permite a modificação de campos específicos de registros existentes (demonstrado com a funcionalidade de atualizar o pH de uma leitura), com as devidas validações para manter a integridade dos dados.
    * **Delete (Remoção):** Possibilita a remoção segura de registros específicos por ID, incluindo uma etapa de confirmação do usuário para prevenir perdas acidentais de dados.
* **Suite de Análises Avançadas e Preditivas:**
    Com o intuito de ir além do básico e demonstrar o potencial analítico da solução, foram implementadas as seguintes funcionalidades, acessíveis via menu:
    * **Análise Estatística Descritiva:** Geração e exibição de métricas estatísticas fundamentais (média, mediana, desvio padrão, quartis, valores mínimos e máximos) para as principais variáveis dos sensores (umidade, pH, temperatura), oferecendo um panorama quantitativo do comportamento dos dados.
    * **Detecção Inteligente de Anomalias:** Utilização do método Z-score para identificar automaticamente leituras que se desviam significativamente do padrão normal. Esta funcionalidade é crucial para sinalizar possíveis falhas de sensores, eventos ambientais extremos ou necessidade de calibração.
    * **Análise de Correlação:** Cálculo e apresentação da matriz de correlação de Pearson, permitindo investigar as interdependências e a força da relação linear entre as diferentes leituras dos sensores e o estado de acionamento da bomba.
    * **Modelo Preditivo de Risco de Emergência (Machine Learning):**
        * Implementação do treinamento de um modelo `RandomForestClassifier` (utilizando Scikit-learn) para classificar e prever a probabilidade de o sistema entrar em uma condição de "emergência" (definida por umidade criticamente baixa ou pH fora da faixa crítica).
        * Análise da importância das *features* (*feature importance*), que revela quais sensores (umidade, pH, temperatura) têm maior impacto na definição de um estado de emergência pelo modelo, fornecendo *insights* valiosos para o entendimento do sistema.
    * **Forecast de Umidade do Solo (Séries Temporais - ARIMA):**
        * Utilização de um modelo ARIMA (via Statsmodels) para realizar previsões das próximas N leituras de umidade do solo, com base no histórico de dados.
        * Incorporação de um sistema de **alerta proativo** que notifica o usuário se o *forecast* indicar que a umidade atingirá níveis críticos em um futuro próximo, permitindo ações preventivas e um manejo mais eficiente.
    * **Geração de Relatório Analítico em PDF:** Capacidade de criar automaticamente um relatório profissional e abrangente em formato PDF (utilizando ReportLab). Este relatório consolida todas as estatísticas descritivas, anomalias detectadas, a matriz de correlação, os resultados do *forecast* de umidade (incluindo os alertas gerados) e a análise de importância das *features* do modelo de Machine Learning, facilitando a comunicação e o compartilhamento dos *insights* gerados.

### Instruções de Execução (Sistema Python - `gerenciador_dados.py`)

1.  Assegure-se de que o **Python 3.8 (ou superior)** está instalado e configurado no PATH do sistema.
2.  Navegue até a pasta raiz do projeto `FarmTech_ESP32` através do seu terminal ou *prompt* de comando.
3.  Execute o script utilizando o comando: `python gerenciador_dados.py`
4.  Na primeira execução, o script verificará as dependências Python necessárias e tentará instalá-las automaticamente (usando `pip install --user ...`). O banco de dados `farmtech_phd_data_final_v2.db` será criado e populado com os 50 registros de exemplo do arquivo `dados_para_banco.py` (caso o banco esteja vazio).
5.  Siga as opções apresentadas no menu interativo da CLI para explorar todas as funcionalidades de CRUD e análise.
6.  O arquivo de configuração `farmtech_config_phd.yaml` é criado na primeira execução (se não existir) e permite a customização de diversos parâmetros operacionais, como os limiares da lógica de irrigação, parâmetros de modelos e custos.

---

Este projeto integrado representa uma solução abrangente e analiticamente rica para o desafio da irrigação inteligente. O esforço em ir além dos requisitos básicos, especialmente na construção do *dashboard* interativo com inteligência climática (entrega 3) e nas funcionalidades analíticas do sistema Python, reflete um profundo engajamento com o tema e um desejo de explorar o potencial máximo das ferramentas e conceitos envolvidos. O resultado é uma suíte de ferramentas que não apenas simula um sistema de irrigação, mas oferece uma plataforma robusta para análise de dados, suporte à decisão e demonstração do valor da agricultura de precisão.
