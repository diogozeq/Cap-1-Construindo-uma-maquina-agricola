#include <Arduino.h>
#include "DHT.h" 

// --- Mapeamento de Pinos ---
const int PINO_BOTAO_FOSFORO = 23; 
const int PINO_BOTAO_POTASSIO = 21; 
const int PINO_LDR_PH = 35;         // Confirmado que está conectado ao AO do seu módulo ldrPH
const int PINO_DHT_UMIDADE = 19;    
const int PINO_RELE_BOMBA = 22;     

#define DHTTYPE DHT22               
DHT dht(PINO_DHT_UMIDADE, DHTTYPE); 

// --- Constantes da Lógica de Irrigação ---
const float UMIDADE_MINIMA_PARA_IRRIGAR = 20.0;
const float UMIDADE_ALTA_PARAR_IRRIGACAO = 30.0; // Ajustado para ser um pouco acima da mínima para ter uma banda
const float UMIDADE_CRITICA_BAIXA = 15.0;
const float PH_IDEAL_MINIMO = 5.5;
const float PH_IDEAL_MAXIMO = 6.5;
const float PH_CRITICO_MINIMO = 4.5;
const float PH_CRITICO_MAXIMO = 7.5;

void setup() {
  Serial.begin(115200);
  Serial.println("--- Sistema de Irrigacao Inteligente - Aula 3: LOGICA ATIVA ---");

  pinMode(PINO_BOTAO_FOSFORO, INPUT_PULLUP);
  pinMode(PINO_BOTAO_POTASSIO, INPUT_PULLUP);
  pinMode(PINO_LDR_PH, INPUT); 
  pinMode(PINO_RELE_BOMBA, OUTPUT);
  digitalWrite(PINO_RELE_BOMBA, LOW); // Bomba começa desligada

  dht.begin();
  Serial.println("Sensores configurados. Iniciando logica de irrigacao...");
  delay(2000); 
}

void loop() {
  // --- Leitura dos Sensores ---
  bool fosforoPresente = (digitalRead(PINO_BOTAO_FOSFORO) == LOW);
  bool potassioPresente = (digitalRead(PINO_BOTAO_POTASSIO) == LOW);
  int valorLDR = analogRead(PINO_LDR_PH); 
  float phEstimado = map(valorLDR, 0, 4095, 0.0, 14.0); // Ajuste a calibração do LDR se necessário
  float umidade = dht.readHumidity();
  float temperatura = dht.readTemperature(); // Informativo

  // Variável para decisão da bomba
  bool ligarBomba = false;
  String motivoDecisao = "Condicoes normais, bomba desligada.";

  // Verifica se leituras do DHT são válidas
  if (isnan(umidade) || isnan(temperatura)) {
    Serial.println("!! ATENCAO: Falha ao ler sensor DHT. Logica de irrigacao pausada. !!");
    digitalWrite(PINO_RELE_BOMBA, LOW); // Desliga a bomba por segurança
    delay(2000);
    return; // Pula o resto do loop se o DHT falhar
  }

  // --- Lógica de Decisão para Irrigação ---

  // 1. IRRIGAÇÃO DE EMERGÊNCIA
  if (umidade < UMIDADE_CRITICA_BAIXA) {
    ligarBomba = true;
    motivoDecisao = "EMERGENCIA: Umidade critica baixa (<" + String(UMIDADE_CRITICA_BAIXA) + "%).";
  } 
  // 2. DESLIGAR POR PH CRÍTICO (se não for emergência)
  else if (phEstimado < PH_CRITICO_MINIMO || phEstimado > PH_CRITICO_MAXIMO) {
    ligarBomba = false;
    motivoDecisao = "Bomba DESLIGADA: pH critico (fora de " + String(PH_CRITICO_MINIMO) + "-" + String(PH_CRITICO_MAXIMO) + ").";
  }
  // 3. IRRIGAÇÃO PRINCIPAL / DESLIGAR POR UMIDADE ALTA
  else if (umidade < UMIDADE_MINIMA_PARA_IRRIGAR) { // Umidade baixa, mas não crítica, e pH não crítico
    if (phEstimado >= PH_IDEAL_MINIMO && phEstimado <= PH_IDEAL_MAXIMO) { // pH Ideal
      if (fosforoPresente && potassioPresente) {
        ligarBomba = true;
        motivoDecisao = "Bomba LIGADA: Umidade baixa, pH ideal, P e K presentes (irrig. normal).";
      } else if (fosforoPresente || potassioPresente) {
        ligarBomba = true;
        motivoDecisao = "Bomba LIGADA: Umidade baixa, pH ideal, P ou K presente (irrig. reduzida).";
      } else { // Sem P nem K
        ligarBomba = true; // Ainda liga pela umidade e pH, mas com intensidade mínima
        motivoDecisao = "Bomba LIGADA: Umidade baixa, pH ideal, P e K ausentes (irrig. minima).";
      }
    } else { // pH não ideal, mas também não crítico (está entre crítico e ideal)
      ligarBomba = false; // Ou poderia ser uma irrigação muito leve, mas vamos manter desligado
      motivoDecisao = "Bomba DESLIGADA: Umidade baixa, mas pH fora da faixa ideal (entre " + String(PH_IDEAL_MINIMO) + "-" + String(PH_IDEAL_MAXIMO) + ").";
    }
  } else if (umidade > UMIDADE_ALTA_PARAR_IRRIGACAO) {
    ligarBomba = false;
    motivoDecisao = "Bomba DESLIGADA: Umidade alta (>" + String(UMIDADE_ALTA_PARAR_IRRIGACAO) + "%).";
  } else { 
    // Umidade está na faixa "ok" (entre MINIMA_PARA_IRRIGAR e ALTA_PARAR_IRRIGACAO)
    // e pH não é crítico. Mantém desligada se não foi ligada por outra razão.
    ligarBomba = false; 
    motivoDecisao = "Condicoes de umidade OK, bomba permanece desligada.";
  }

  // --- Controle do Relé/Bomba ---
  digitalWrite(PINO_RELE_BOMBA, ligarBomba ? HIGH : LOW);

  // --- Exibição dos Dados e Decisão no Monitor Serial ---
  Serial.println("-------------------------------------------");
  Serial.print("Umidade: "); Serial.print(umidade, 1); Serial.print("%");
  Serial.print(" | pH Estimado: "); Serial.print(phEstimado, 1);
  Serial.print(" | P: "); Serial.print(fosforoPresente ? "SIM" : "NAO");
  Serial.print(" | K: "); Serial.print(potassioPresente ? "SIM" : "NAO");
  Serial.print(" | Temp: "); Serial.print(temperatura, 1); Serial.println(" *C");
  Serial.print("DECISAO: "); Serial.println(motivoDecisao);
  Serial.print("ESTADO DA BOMBA: "); Serial.println(ligarBomba ? "LIGADA" : "DESLIGADA");
  Serial.println("-------------------------------------------\n");

  delay(3000); // Intervalo entre leituras e decisões (aumentado para melhor visualização)
}