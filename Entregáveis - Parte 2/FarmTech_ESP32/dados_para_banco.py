import datetime
import random

# Gera 50 registros distribuídos em 25 dias (2 registros por dia), começando em 01/04/2025
dados_coletados_fase3 = []
start_date = datetime.date(2025, 4, 1)

for day_offset in range(25):
    current_date = start_date + datetime.timedelta(days=day_offset)
    for _ in range(2):
        # Gera horário aleatório
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        ts = datetime.datetime.combine(current_date, datetime.time(hour, minute))
        timestamp = ts.strftime("%Y-%m-%d %H:%M:%S")
        
        # Gera umidade com cenários variados/extremos
        humidity_generator = random.choice([
            lambda: round(random.uniform(0, 5), 1),     # extremo baixo
            lambda: round(random.uniform(5, 14.9), 1),  # crítico baixo
            lambda: round(random.uniform(15, 19.9), 1), # baixo normal
            lambda: round(random.uniform(20, 30), 1),    # ok
            lambda: round(random.uniform(30.1, 60), 1), # alto
            lambda: round(random.uniform(60.1, 100), 1) # extremo alto
        ])
        umidade = humidity_generator()
        
        # Gera pH com cenários variados/extremos
        ph_generator = random.choice([
            lambda: round(random.uniform(0, 4.4), 1),   # crítico ácido
            lambda: round(random.uniform(4.5, 5.4), 1), # ligeiro fora inferior
            lambda: round(random.uniform(5.5, 6.5), 1), # ideal
            lambda: round(random.uniform(6.6, 7.5), 1), # ligeiro fora superior
            lambda: round(random.uniform(7.6, 14), 1)   # crítico alcalino
        ])
        ph = ph_generator()
        
        # Nutrientes e temperatura
        fosforo = random.choice([True, False])
        potassio = random.choice([True, False])
        temperatura = round(random.uniform(15, 35), 1)
        
        # Lógica de decisão
        if umidade < 15.0:
            bomba = True
            decisao = "EMERGENCIA: Umidade critica baixa."
        elif ph < 4.5 or ph > 7.5:
            bomba = False
            decisao = "Bomba DESLIGADA: pH critico."
        elif 15.0 <= umidade < 20.0:
            if 5.5 <= ph <= 6.5:
                bomba = True
                if fosforo and potassio:
                    decisao = "Bomba LIGADA: Umidade baixa, pH ideal, P e K presentes."
                elif fosforo or potassio:
                    decisao = "Bomba LIGADA: Umidade baixa, pH ideal, P ou K presente."
                else:
                    decisao = "Bomba LIGADA: Umidade baixa, pH ideal, P e K ausentes."
            else:
                bomba = False
                decisao = "Bomba DESLIGADA: Umidade baixa, mas pH fora da faixa ideal."
        elif 20.0 <= umidade <= 30.0:
            bomba = False
            decisao = "Condicoes de umidade OK, bomba permanece desligada."
        else:
            bomba = False
            decisao = "Bomba DESLIGADA: Umidade alta."
        
        dados_coletados_fase3.append({
            "timestamp": timestamp,
            "umidade": umidade,
            "ph_estimado": ph,
            "fosforo_presente": fosforo,
            "potassio_presente": potassio,
            "temperatura": temperatura,
            "bomba_ligada": bomba,
            "decisao_logica_esp32": decisao
        })

# Validações (double checks)
total = len(dados_coletados_fase3)
ligada_count = sum(1 for r in dados_coletados_fase3 if r["bomba_ligada"])
desligada_count = total - ligada_count

emergencia_count = sum(
    1 for r in dados_coletados_fase3
    if (r["umidade"] < 15.0) or (r["ph_estimado"] < 4.5 or r["ph_estimado"] > 7.5)
)
nao_emergencia_count = total - emergencia_count

print(f"Total de registros gerados: {total}")
print(f"Registros com bomba LIGADA: {ligada_count}")
print(f"Registros com bomba DESLIGADA: {desligada_count}")
print(f"Registros com emergencia_real=True: {emergencia_count}")
print(f"Registros com emergencia_real=False: {nao_emergencia_count}")
