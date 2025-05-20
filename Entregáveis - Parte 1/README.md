# FarmTech Solutions - Fase 3: Simulação de Sistema de Irrigação Inteligente

## Visão Geral do Projeto

Este projeto simula um sistema de irrigação inteligente, desenvolvido como parte da Fase 3 para a FarmTech Solutions. Utilizando a plataforma Wokwi.com e um microcontrolador ESP32, o sistema monitora em tempo real as condições do solo – umidade, pH (simulado por LDR), e níveis de nutrientes Fósforo (P) e Potássio (K) (simulados por botões) – para acionar de forma autônoma e eficiente uma bomba de irrigação (representada por um LED/Relé).

O diferencial deste projeto reside na **lógica de controle da irrigação, cujos parâmetros foram definidos a partir de uma pesquisa simulada de mercado e consulta a referências agronômicas**, buscando replicar critérios realistas para a otimização do uso da água e saúde das culturas.

## Arquitetura da Simulação

### Componentes Principais:
*   **ESP32 Dev Module:** O cérebro do sistema, processando os dados dos sensores e controlando o atuador.
*   **Sensor de Umidade (DHT22):** Fornece leituras contínuas da umidade do solo.
*   **Sensor de pH (LDR - `ldrPH` & Resistor `rLDR`):** Um LDR, em um circuito divisor de tensão com um resistor de 10kΩ, simula um sensor de pH. A variação da luminosidade (controlada na simulação) é convertida para uma escala de pH (0-14), refletindo a natureza contínua deste parâmetro.
*   **Sensores de Nutrientes (Botões `btnP` e `btnK`):** Botões representam a detecção de Fósforo (P) e Potássio (K), indicando presença (pressionado) ou ausência (solto).
*   **Bomba de Irrigação (LED `ledRele` & Resistor `rLedRele`):** Um LED (com resistor de 220Ω) visualiza o estado do relé que acionaria a bomba. LED aceso indica irrigação ativa.

### Imagem do Circuito Implementado no Wokwi:
![Circuito FarmTech Wokwi](circuito_farmtech.png)

## Lógica de Irrigação Inteligente: Decisões Baseadas em Dados

A estratégia de irrigação foi fundamentada em parâmetros agronômicos para maximizar a eficiência hídrica e o aproveitamento de nutrientes.

**Parâmetros de Referência (Derivados da Pesquisa):**
*   **Umidade Crítica Baixa (Emergência):** < 15.0%
*   **Umidade Mínima (Gatilho para Irrigação Principal):** < 20.0%
*   **Umidade Alta (Parar Irrigação):** > 30.0%
*   **Faixa de pH Ideal:** 5.5 – 6.5
*   **Faixa de pH Crítica (Não Irrigar, exceto emergência):** < 4.5 ou > 7.5

**Hierarquia e Regras de Decisão Implementadas:**

1.  **Prioridade Máxima - Irrigação de Emergência:** Se a umidade cair abaixo de 15%, a bomba é **ATIVADA** independentemente de outros fatores, para prevenir perdas críticas.
2.  **Condição Restritiva - pH Crítico:** Se não houver emergência de umidade, mas o pH estiver fora da faixa crítica (ex: <4.5 ou >7.5), a bomba permanece **DESATIVADA**, pois a absorção de água e nutrientes seria ineficiente ou prejudicial.
3.  **Condição Principal - Irrigação Otimizada:**
    *   Se a umidade estiver abaixo de 20% (e não crítica, e pH não crítico):
        *   **E** o pH estiver na faixa ideal (5.5-6.5): A bomba é **ATIVADA**. A "intensidade" da irrigação (simulada pela decisão de ligar) é modulada pela presença de nutrientes:
            *   **P e K presentes:** Irrigação com maior benefício (considerada "normal").
            *   **P ou K presente:** Irrigação ainda benéfica ("reduzida").
            *   **P e K ausentes:** Irrigação para suprir umidade, mas com menor otimização de nutrientes ("mínima").
        *   **E** o pH estiver fora da faixa ideal, mas não crítico: A bomba permanece **DESATIVADA**, aguardando condições de pH mais favoráveis.
4.  **Condição de Interrupção - Umidade Alta:** Se a umidade exceder 30%, a bomba é **DESATIVADA**.
5.  **Padrão:** Em todas as outras situações, a bomba permanece **DESATIVADA**.

Esta abordagem multifatorial visa um manejo hídrico preciso e adaptativo, refletindo a complexidade das necessidades reais das culturas. O sistema demonstra a capacidade de integrar múltiplos inputs de sensores para uma tomada de decisão automatizada e inteligente.

*(Nota sobre a simulação: A renderização visual de todos os componentes na simulação Wokwi iniciada via VS Code pode apresentar variações. No entanto, o código implementa a leitura e a lógica para todos os sensores descritos, incluindo o LDR para pH, conforme validado pelo monitor serial.)*

## Instruções para Teste
1.  Compile o projeto utilizando PlatformIO no VS Code (Build ✓).
2.  Inicie a simulação através do comando `Wokwi: Start Simulation` na paleta de comandos do VS Code (Ctrl+Shift+P).
3.  Na interface de simulação Wokwi (geralmente em uma aba dentro do VS Code):
    *   Ajuste os valores dos sensores: sliders para Umidade (DHT22) e pH (LDR); botões para Fósforo (P) e Potássio (K).
    *   Monitore as saídas no "Serial Monitor" para observar as leituras dos sensores, a lógica de decisão aplicada e o estado da bomba.
    *   Verifique o acionamento do LED vermelho (Bomba) no diagrama.