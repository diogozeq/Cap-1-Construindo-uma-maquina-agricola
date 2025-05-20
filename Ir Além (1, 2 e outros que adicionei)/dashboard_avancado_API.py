#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FarmTech Solutions - Dashboard Avançado com Integração API para Irrigação Inteligente
Autor: Diogo Zequini
Data: 2025-05-20

Descrição:
Dashboard interativo com Streamlit para visualização de dados históricos de irrigação,
integração com dados meteorológicos em tempo real, simulação de lógica de decisão,
alertas proativos, análise de custos e diagnóstico do sistema.
"""

# Bloco 1: Imports Padrão e Configuração Inicial de Logging
import sys
import subprocess
import importlib
import logging
import os
import datetime
import warnings

LOGGING_LEVEL = logging.INFO
logging.basicConfig(
    level=LOGGING_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FarmTechDashboardApp")

# Bloco 2: Gerenciamento de Dependências
PIP_MODULE_MAP_DASH = {
    'streamlit': 'streamlit', 'pandas': 'pandas', 'numpy': 'numpy',
    'requests': 'requests', 'sqlalchemy': 'SQLAlchemy',
    'plotly': 'plotly', 'yaml': 'PyYAML'
}
INSTALLED_PACKAGES_CACHE_DASH = {}

def ensure_package_dash(module_name, critical=True):
    if module_name in INSTALLED_PACKAGES_CACHE_DASH:
        return INSTALLED_PACKAGES_CACHE_DASH[module_name]
    try:
        pkg = importlib.import_module(module_name)
        version = getattr(pkg, '__version__', getattr(pkg, 'VERSION', 'não especificada'))
        if module_name == 'reportlab' and hasattr(pkg, 'Version'): version = pkg.Version
        logger.debug(f"Pacote '{module_name}' já instalado (versão: {version}).")
        INSTALLED_PACKAGES_CACHE_DASH[module_name] = pkg
        return pkg
    except ImportError:
        pip_name = PIP_MODULE_MAP_DASH.get(module_name, module_name)
        logger.warning(f"Pacote '{module_name}' (pip: '{pip_name}') não encontrado. Tentando instalar...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--user", "--quiet", "--disable-pip-version-check"])
            logger.info(f"Pacote '{pip_name}' instalado com sucesso.")
            importlib.invalidate_caches()
            pkg = importlib.import_module(module_name)
            version_after_install = getattr(pkg, '__version__', getattr(pkg, 'VERSION', 'não especificada'))
            if module_name == 'reportlab' and hasattr(pkg, 'Version'): version_after_install = pkg.Version
            logger.info(f"Pacote '{module_name}' importado (versão: {version_after_install}).")
            INSTALLED_PACKAGES_CACHE_DASH[module_name] = pkg
            return pkg
        except Exception as e:
            logger.error(f"Falha ao instalar/importar '{pip_name}'. Erro: {e}", exc_info=True)
            if critical:
                print(f"ERRO CRÍTICO: Dependência '{pip_name}' não instalada. Instale manualmente.", file=sys.stderr)
                sys.exit(1)
            INSTALLED_PACKAGES_CACHE_DASH[module_name] = None
            return None

logger.info("Dashboard: Verificando dependências...")
yaml_module = ensure_package_dash('yaml', critical=True)
st_module = ensure_package_dash('streamlit', critical=True)
pd_module = ensure_package_dash('pandas', critical=True)
np_module = ensure_package_dash('numpy', critical=True)
requests_module = ensure_package_dash('requests', critical=True)
sqlalchemy_module = ensure_package_dash('sqlalchemy', critical=True)
plotly_module = ensure_package_dash('plotly', critical=True)
logger.info("Dashboard: Dependências verificadas.")

if not st_module:
    logger.critical("Streamlit não pôde ser carregado.")
    sys.exit("ERRO CRÍTICO: Streamlit não está disponível.")

import streamlit as st

# CONFIGURAÇÃO DA PÁGINA (PRIMEIRO COMANDO STREAMLIT)
st.set_page_config(page_title="FarmTech PhD Dashboard", layout="wide", initial_sidebar_state="expanded", page_icon="💧")

import pandas as pd
import numpy as np
import requests
import yaml
from sqlalchemy import create_engine, Column, Integer, Float, Boolean, DateTime, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import plotly.express as px

# # (O Bloco 4: st.set_page_config(...) deve estar ANTES desta seção)

# --- Constantes Padrão Globais para Configuração (DEFINIDAS ANTES DE USAR) ---
DB_NAME_DEFAULT_GLOBAL_DASH = 'farmtech_phd_data_final_v2.db'
TABLE_NAME_DEFAULT_GLOBAL_DASH = 'leituras_sensores_phd_v2'

LOGICA_ESP32_PARAMS_DEFAULT_GLOBAL_DASH = {
    'UMIDADE_CRITICA_BAIXA': 15.0, 
    'UMIDADE_MINIMA_PARA_IRRIGAR': 20.0,
    'UMIDADE_ALTA_PARAR_IRRIGACAO': 60.0, 
    'PH_IDEAL_MINIMO': 5.5,
    'PH_IDEAL_MAXIMO': 6.5, 
    'PH_CRITICO_MINIMO': 4.5, 
    'PH_CRITICO_MAXIMO': 7.5,
}

FORECAST_SETTINGS_DEFAULT_GLOBAL_DASH = {
    'num_leituras_futuras': 6, 
    'intervalo_leitura_minutos': 5,
    'alerta_forecast_ativo': True, 
    'arima_p': 1, 
    'arima_d': 1, 
    'arima_q': 1
}

CUSTO_SETTINGS_DEFAULT_GLOBAL_DASH = {
    'custo_agua_reais_por_m3': 5.00, 
    'vazao_bomba_litros_por_hora': 1000.0,
    'tempo_irrigacao_padrao_minutos': 15.0, 
    'custo_energia_kwh': 0.75,
    'potencia_bomba_kw': 0.75
}

ML_CLASSIFIER_DEFAULT_GLOBAL_DASH = {
    'test_size': 0.3, 
    'random_state': 42, 
    'n_estimators': 100,
    'min_samples_leaf': 3
}

REPORT_SETTINGS_DEFAULT_GLOBAL_DASH = {
    'max_anomalias_no_relatorio': 5, 
    'max_leituras_recentes_tabela_pdf': 15,
    'autor_relatorio': "Diogo Zequini" # Seu nome aqui
}

CLI_SETTINGS_DEFAULT_GLOBAL_DASH = { 
    'max_leituras_tabela_console': 10 
}

CONFIG_FILE_PATH_GLOBAL_DASH = 'farmtech_config_phd.yaml'
METEOBLUE_API_KEY_FIXA = "5239OsFXJijKVSDq" # Sua chave da API Meteoblue

# (A função @st.cache_resource def carregar_configuracoes_dashboard_corrigido(): continua DEPOIS deste bloco)


@st.cache_resource
def carregar_configuracoes_dashboard_final():
    default_cfg_interno = {
        'db_name': DB_NAME_DEFAULT_GLOBAL_DASH,
        'table_name': TABLE_NAME_DEFAULT_GLOBAL_DASH,
        'logica_esp32': LOGICA_ESP32_PARAMS_DEFAULT_GLOBAL_DASH.copy(),
        'custo_settings': CUSTO_SETTINGS_DEFAULT_GLOBAL_DASH.copy(), # Adicionada ao default
        # Adicione outras seções de config default que seu YAML cobre
        'forecast_settings': {'num_leituras_futuras': 6, 'intervalo_leitura_minutos': 5, 'alerta_forecast_ativo': True, 'arima_p': 1, 'arima_d': 1, 'arima_q': 1},
        'ml_classifier': {'test_size': 0.3, 'random_state': 42, 'n_estimators': 100, 'min_samples_leaf': 3},
        'report_settings': {'max_anomalias_no_relatorio': 5, 'max_leituras_recentes_tabela_pdf': 15, 'autor_relatorio': "Diogo Zequini"},
        'cli_settings': {'max_leituras_tabela_console': 10}
    }
    config_final_para_uso = default_cfg_interno.copy()
    if yaml_module and os.path.exists(CONFIG_FILE_PATH_GLOBAL_DASH):
        try:
            with open(CONFIG_FILE_PATH_GLOBAL_DASH, 'r', encoding='utf-8') as f:
                config_do_arquivo = yaml_module.safe_load(f)
            if config_do_arquivo:
                logger.info(f"Configurações carregadas de '{CONFIG_FILE_PATH_GLOBAL_DASH}'.")
                for chave_principal, valor_default_secao in default_cfg_interno.items():
                    if chave_principal in config_do_arquivo:
                        if isinstance(valor_default_secao, dict) and isinstance(config_do_arquivo.get(chave_principal), dict):
                            secao_mesclada = valor_default_secao.copy()
                            secao_mesclada.update(config_do_arquivo[chave_principal])
                            config_final_para_uso[chave_principal] = secao_mesclada
                        else:
                            config_final_para_uso[chave_principal] = config_do_arquivo[chave_principal]
                
                # Tratar arima_order se p,d,q separados existem
                if 'forecast_settings' in config_final_para_uso and \
                   all(k in config_final_para_uso['forecast_settings'] for k in ['arima_p', 'arima_d', 'arima_q']):
                     cfg_fc = config_final_para_uso['forecast_settings']
                     config_final_para_uso['forecast_settings']['arima_order'] = (cfg_fc['arima_p'], cfg_fc['arima_d'], cfg_fc['arima_q'])
                
                # Reescrever o YAML se a estrutura carregada for diferente da final esperada
                config_para_salvar_yaml = config_final_para_uso.copy()
                if 'forecast_settings' in config_para_salvar_yaml and \
                   isinstance(config_para_salvar_yaml['forecast_settings'].get('arima_order'), tuple):
                    p,d,q = config_para_salvar_yaml['forecast_settings']['arima_order']
                    config_para_salvar_yaml['forecast_settings']['arima_p'] = p
                    config_para_salvar_yaml['forecast_settings']['arima_d'] = d
                    config_para_salvar_yaml['forecast_settings']['arima_q'] = q
                    if 'arima_order' in config_para_salvar_yaml['forecast_settings']:
                        del config_para_salvar_yaml['forecast_settings']['arima_order'] 
                
                # Verifica se precisa reescrever
                precisa_reescrever_yaml = False
                if not all(k in config_do_arquivo for k in default_cfg_interno): # Se faltam chaves default no arquivo
                    precisa_reescrever_yaml = True
                else: # Checa se os sub-dicionários também estão completos
                    for k_default, v_default_section in default_cfg_interno.items():
                        if isinstance(v_default_section, dict):
                            if not all(sub_k in config_do_arquivo.get(k_default,{}) for sub_k in v_default_section):
                                precisa_reescrever_yaml = True; break
                if config_para_salvar_yaml != config_do_arquivo and any(k not in config_do_arquivo.get('forecast_settings', {}) for k in ['arima_p','arima_d','arima_q']): # Se arima p,d,q não estavam no arquivo
                    precisa_reescrever_yaml = True

                if precisa_reescrever_yaml:
                    try:
                        with open(CONFIG_FILE_PATH_GLOBAL_DASH, 'w', encoding='utf-8') as f_save:
                            yaml_module.dump(config_para_salvar_yaml, f_save, sort_keys=False, allow_unicode=True, indent=4)
                        logger.info(f"'{CONFIG_FILE_PATH_GLOBAL_DASH}' (re)escrito com estrutura completa/padronizada.")
                    except IOError as e_write:
                        logger.error(f"Não reescreveu '{CONFIG_FILE_PATH_GLOBAL_DASH}': {e_write}")
            else:
                 logger.warning(f"'{CONFIG_FILE_PATH_GLOBAL_DASH}' vazio/malformado. Usando defaults e recriando.")
                 # Recria com p,d,q separados
                 with open(CONFIG_FILE_PATH_GLOBAL_DASH, 'w', encoding='utf-8') as f_create_empty:
                    yaml_module.dump(default_cfg_interno, f_create_empty, sort_keys=False, allow_unicode=True, indent=4)
            return config_final_para_uso
        except yaml.YAMLError as e:
            logger.error(f"Sintaxe YAML em '{CONFIG_FILE_PATH_GLOBAL_DASH}': {e}. Usando padrões.")
            return default_cfg_interno
        except Exception as e_gen:
            logger.error(f"Erro geral ao carregar '{CONFIG_FILE_PATH_GLOBAL_DASH}': {e_gen}. Usando padrões.")
            return default_cfg_interno
    else:
        logger.warning(f"'{CONFIG_FILE_PATH_GLOBAL_DASH}' não encontrado. Usando padrões e criando.")
        try:
            with open(CONFIG_FILE_PATH_GLOBAL_DASH, 'w', encoding='utf-8') as f:
                yaml_module.dump(default_cfg_interno, f, sort_keys=False, allow_unicode=True, indent=4)
            logger.info(f"'{CONFIG_FILE_PATH_GLOBAL_DASH}' criado com defaults.")
        except IOError as e_io_create:
            logger.error(f"Não criou '{CONFIG_FILE_PATH_GLOBAL_DASH}': {e_io_create}")
        return default_cfg_interno

config_app = carregar_configuracoes_dashboard_final()

# Usa as configurações carregadas ou os defaults globais
DB_NAME_APP = config_app.get('db_name', DB_NAME_DEFAULT_GLOBAL_DASH)
TABLE_NAME_APP = config_app.get('table_name', TABLE_NAME_DEFAULT_GLOBAL_DASH)
LOGICA_ESP32_PARAMS_APP_CONFIG = config_app.get('logica_esp32', LOGICA_ESP32_PARAMS_DEFAULT_GLOBAL_DASH.copy())
CUSTO_CFG_APP_CONFIG = config_app.get('custo_settings', CUSTO_SETTINGS_DEFAULT_GLOBAL_DASH.copy())


# --- Sidebar ---
st.sidebar.header("Configurações da Simulação")
st.sidebar.subheader("Localização para Dados Climáticos")
default_lat_app, default_lon_app = -22.9083, -43.1964
sim_lat_app = st.sidebar.number_input("Latitude", value=default_lat_app, format="%.4f", key="app_lat_v3")
sim_lon_app = st.sidebar.number_input("Longitude", value=default_lon_app, format="%.4f", key="app_lon_v3")
st.sidebar.info(f"Usando chave API Meteoblue embutida para {sim_lat_app}, {sim_lon_app}.")


# --- Conexão com Banco de Dados e Definição da Tabela ---
BaseDB_App = declarative_base()
engine_app_conn = None
SessionLocal_App = None
try:
    engine_app_conn = create_engine(f"sqlite:///{DB_NAME_APP}?check_same_thread=False")
    SessionLocal_App = sessionmaker(autocommit=False, autoflush=False, bind=engine_app_conn)
    class LeituraSensorApp(BaseDB_App):
        __tablename__ = TABLE_NAME_APP
        __table_args__ = {'extend_existing': True}
        id = Column(Integer, primary_key=True)
        timestamp = Column(DateTime, unique=True, nullable=False)
        umidade = Column(Float, nullable=False)
        ph_estimado = Column(Float, nullable=False)
        fosforo_presente = Column(Boolean, nullable=False)
        potassio_presente = Column(Boolean, nullable=False)
        temperatura = Column(Float)
        bomba_ligada = Column(Boolean, nullable=False)
        decisao_logica_esp32 = Column(String, nullable=True)
    BaseDB_App.metadata.create_all(bind=engine_app_conn)
except Exception as e_db_app_setup:
    logger.error(f"Erro DB dashboard: {e_db_app_setup}", exc_info=True)
    st.error(f"Erro crítico DB: {e_db_app_setup}. Verifique '{DB_NAME_APP}'.")

# --- Funções de Apoio (carregar dados, buscar clima, simular lógica) ---
@st.cache_data(ttl=300)
def carregar_dados_historicos_app():
    if not engine_app_conn or not SessionLocal_App: return pd.DataFrame()
    try:
        with SessionLocal_App() as db:
            query = db.query(LeituraSensorApp).order_by(LeituraSensorApp.timestamp.desc())
            df = pd.read_sql(query.statement, db.bind, index_col='timestamp', parse_dates=['timestamp'])
        if not df.empty:
            if df.index.tz is None: df.index = df.index.tz_localize('UTC')
            else: df.index = df.index.tz_convert('UTC')
        return df
    except Exception as e:
        logger.error(f"Erro ao carregar dados histórico para App: {e}", exc_info=True)
        st.warning(f"Não foi possível carregar dados históricos (Tabela '{TABLE_NAME_APP}' existe?).")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def buscar_dados_meteoblue_app(lat, lon, tipo_pacote="basic-1h"):
    api_key_interna_mb = METEOBLUE_API_KEY_FIXA
    if not api_key_interna_mb: return None, "Chave API Meteoblue não configurada no código."
    # ... (resto da função buscar_dados_meteoblue_cached_app, usando api_key_interna_mb)
    base_url = f"https://my.meteoblue.com/packages/{tipo_pacote}"
    params = {
        "apikey": api_key_interna_mb, "lat": lat, "lon": lon, "format": "json",
        "temperature": "C", "windspeed": "kmh", "precipitationamount": "mm",
        "timeformat": "iso8601", "forecast_days": 3
    }
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "metadata" not in data or (tipo_pacote == "basic-day" and "data_day" not in data) or \
           (tipo_pacote == "basic-1h" and "data_1h" not in data) :
            logger.error(f"Estrutura API Meteoblue inesperada ({tipo_pacote}): {data}")
            return None, "Resposta API Meteoblue com estrutura inesperada."
        return data, None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout Meteoblue ({tipo_pacote}).")
        return None, f"Timeout API Meteoblue ({tipo_pacote})."
    except requests.exceptions.HTTPError as http_err:
        err_msg_http = f"Erro HTTP {response.status_code} API Meteoblue ({tipo_pacote}): {http_err}."
        if response and hasattr(response, 'text') and response.text: err_msg_http += f" Detalhe: {response.text[:200]}"
        logger.error(err_msg_http)
        return None, err_msg_http
    except Exception as e_meteo:
        logger.error(f"Erro API Meteoblue ({tipo_pacote}): {e_meteo}", exc_info=True)
        return None, f"Erro ao buscar dados Meteoblue ({tipo_pacote})."


def simular_logica_irrigacao_app(umidade, ph, p, k, cfg_logica: dict, chuva_mm=0.0):
    # (Lógica do ESP32 - replicada e usando cfg_logica)
    ligar_bomba, motivo = False, "Condições padrão, bomba desligada."
    if umidade < cfg_logica['UMIDADE_CRITICA_BAIXA']:
        ligar_bomba, motivo = True, f"EMERGÊNCIA: Umidade crítica ({umidade:.1f}%)"
    elif ph < cfg_logica['PH_CRITICO_MINIMO'] or ph > cfg_logica['PH_CRITICO_MAXIMO']:
        ligar_bomba, motivo = False, f"pH crítico ({ph:.1f}%)"
    elif umidade < cfg_logica['UMIDADE_MINIMA_PARA_IRRIGAR']:
        if cfg_logica['PH_IDEAL_MINIMO'] <= ph <= cfg_logica['PH_IDEAL_MAXIMO']:
            ligar_bomba = True
            if p and k: motivo = f"Umid. baixa ({umidade:.1f}%), pH ideal ({ph:.1f}), P&K OK"
            elif p or k: motivo = f"Umid. baixa ({umidade:.1f}%), pH ideal ({ph:.1f}), P ou K OK"
            else: motivo = f"Umid. baixa ({umidade:.1f}%), pH ideal ({ph:.1f}), Nutrientes Ausentes"
        else: motivo = f"Umid. baixa ({umidade:.1f}%), mas pH ({ph:.1f}) não ideal"
    elif umidade > cfg_logica['UMIDADE_ALTA_PARAR_IRRIGACAO']:
        ligar_bomba, motivo = False, f"Umidade alta ({umidade:.1f}%)"
    
    if ligar_bomba and chuva_mm > 1.0: # Limiar de chuva significativa
        return False, f"DECISÃO BASE: Ligar ({motivo}). AJUSTE CLIMA: DESLIGAR (Chuva: {chuva_mm:.1f}mm)."
    
    final_motivo = motivo
    if chuva_mm > 0: final_motivo += f" (Chuva: {chuva_mm:.1f}mm)"
    else: final_motivo += " (Sem chuva prevista)"
    return ligar_bomba, final_motivo

# --- Funções para Novas Melhorias ---
def analisar_alertas_recentes_app(df_periodo, cfg_logica, console=st):
    """Analisa os dados mais recentes do período e exibe alertas."""
    if df_periodo.empty: return
    alertas = []
    # Analisar os últimos 5 registros do período selecionado, por exemplo
    df_recente = df_periodo.tail(5) 
    for idx, row in df_recente.iterrows():
        if row['umidade'] < cfg_logica['UMIDADE_CRITICA_BAIXA']:
            alertas.append(f"🔴 Umidade Crítica ({row['umidade']:.1f}%) em {idx.strftime('%d/%m %H:%M')}")
        if not (cfg_logica['PH_CRITICO_MINIMO'] <= row['ph_estimado'] <= cfg_logica['PH_CRITICO_MAXIMO']):
            alertas.append(f"🟡 pH Fora da Faixa Segura ({row['ph_estimado']:.1f}) em {idx.strftime('%d/%m %H:%M')}")
    
    if alertas:
        console.warning("🚨 Painel de Alertas Rápidos (Dados Recentes):")
        for alerta in alertas:
            console.markdown(f"- {alerta}")
    else:
        console.info("✅ Sem alertas críticos nos dados recentes do período selecionado.")

def calcular_custos_operacionais_app(df_periodo, cfg_custos, cfg_geral, console=st):
    if df_periodo.empty or 'bomba_ligada' not in df_periodo.columns:
        console.info("Custos: Dados insuficientes para cálculo.")
        return 0.0, 0.0, 0
    
    intervalo_registros_min = cfg_geral.get('forecast_settings', {}).get('intervalo_leitura_minutos', 5)
    tempo_bomba_ligada_min = df_periodo['bomba_ligada'].sum() * intervalo_registros_min
    
    if tempo_bomba_ligada_min == 0:
        console.info("Custos: Bomba não foi acionada no período. Custo zero.")
        return 0.0, 0.0, 0
    
    tempo_bomba_ligada_h = tempo_bomba_ligada_min / 60.0
    volume_agua_usado_m3 = (cfg_custos['vazao_bomba_litros_por_hora'] / 1000.0) * tempo_bomba_ligada_h
    custo_total_agua = volume_agua_usado_m3 * cfg_custos['custo_agua_reais_por_m3']
    
    consumo_energia_kwh = cfg_custos['potencia_bomba_kw'] * tempo_bomba_ligada_h
    custo_total_energia = consumo_energia_kwh * cfg_custos['custo_energia_kwh']
    
    custo_operacional_total = custo_total_agua + custo_total_energia
    num_ciclos_estimados = df_periodo['bomba_ligada'].astype(int).diff().fillna(0).eq(1).sum()


    console.metric("Ciclos de Irrigação Estimados", num_ciclos_estimados)
    col1, col2, col3 = console.columns(3)
    col1.metric("Custo Água Estimado", f"R$ {custo_total_agua:.2f}")
    col2.metric("Custo Energia Estimado", f"R$ {custo_total_energia:.2f}")
    col3.metric("CUSTO OPERACIONAL TOTAL", f"R$ {custo_operacional_total:.2f}")
    return custo_total_agua, custo_total_energia, num_ciclos_estimados


def gerar_diagnostico_sugestoes_app(df_periodo, cfg_logica, console=st):
    if df_periodo.empty or len(df_periodo) < 5: # Precisa de alguns dados para diagnóstico
        console.info("Diagnóstico: Dados insuficientes para um diagnóstico detalhado.")
        return

    with console.expander("🔬 Diagnóstico do Sistema e Sugestões (Beta)"):
        st.markdown("**Análise de Comportamento:**")
        # Umidade média no acionamento
        df_bomba_on = df_periodo[df_periodo['bomba_ligada'] == True]
        if not df_bomba_on.empty:
            umid_media_acionamento = df_bomba_on['umidade'].mean()
            st.write(f"- Umidade média no momento do acionamento da bomba: **{umid_media_acionamento:.1f}%**.")
            if umid_media_acionamento < cfg_logica['UMIDADE_MINIMA_PARA_IRRIGAR'] - 5: # Se aciona muito abaixo
                st.caption("  Sugestão: A bomba está sendo acionada com umidade já consideravelmente baixa. Verifique se o limiar de irrigação está adequado ou se há atrasos na resposta do sistema.")
            elif umid_media_acionamento > cfg_logica['UMIDADE_MINIMA_PARA_IRRIGAR'] + 5:
                 st.caption("  Sugestão: A bomba parece ser acionada com umidade ainda relativamente alta. Considere revisar o limiar MÍNIMO para irrigar para otimizar o uso da água.")
        else:
            st.write("- Bomba não foi acionada no período para análise de umidade de acionamento.")

        # pH médio
        ph_medio_periodo = df_periodo['ph_estimado'].mean()
        st.write(f"- pH médio no período: **{ph_medio_periodo:.1f}**.")
        if not (cfg_logica['PH_IDEAL_MINIMO'] <= ph_medio_periodo <= cfg_logica['PH_IDEAL_MAXIMO']):
            st.caption(f"  Atenção: O pH médio está fora da faixa ideal ({cfg_logica['PH_IDEAL_MINIMO']}-{cfg_logica['PH_IDEAL_MAXIMO']}). Isso pode afetar a absorção de nutrientes. Considere análise e correção do solo.")

        # Frequência de condições críticas
        umidade_critica_ocorrencias = df_periodo[df_periodo['umidade'] < cfg_logica['UMIDADE_CRITICA_BAIXA']].shape[0]
        ph_critico_ocorrencias = df_periodo[(df_periodo['ph_estimado'] < cfg_logica['PH_CRITICO_MINIMO']) | (df_periodo['ph_estimado'] > cfg_logica['PH_CRITICO_MAXIMO'])].shape[0]
        
        st.write(f"- Ocorrências de umidade crítica (<{cfg_logica['UMIDADE_CRITICA_BAIXA']}%): **{umidade_critica_ocorrencias}**.")
        if umidade_critica_ocorrencias > len(df_periodo) * 0.1: # Se mais de 10% das leituras foram críticas
            st.caption("  Sugestão: Alta frequência de umidade crítica. Revise a frequência de irrigação ou os limiares de emergência.")
        
        st.write(f"- Ocorrências de pH crítico (<{cfg_logica['PH_CRITICO_MINIMO']} ou >{cfg_logica['PH_CRITICO_MAXIMO']}): **{ph_critico_ocorrencias}**.")
        if ph_critico_ocorrencias > len(df_periodo) * 0.1:
            st.caption("  Sugestão: Alta frequência de pH crítico. Priorize a correção do pH do solo.")

# --- Layout Principal do Dashboard ---
# (Adaptações para usar as novas funções)
# ... (Logo e Título como antes) ...
if os.path.exists("logo_farmtech.png"): # Assumindo que você tem um logo.png
    st.image("logo_farmtech.png", width=80)

st.title("💧 FarmTech Solutions - Dashboard de Irrigação Inteligente Avançado 🛰️")

tab_historico, tab_clima, tab_whatif, tab_sobre = st.tabs([
    "📈 Histórico e Diagnóstico", "🌦️ Clima (Meteoblue)", "💡 Simulador What-If", "ℹ️ Sobre"
])

with tab_historico:
    st.header("Dados Históricos, Alertas e Custos")
    df_hist_app_main = carregar_dados_historicos_app() # Renomeado para evitar conflito
    
    if not df_hist_app_main.empty:
        # Filtros de data
        datas_disponiveis_main = sorted(list(set(df_hist_app_main.index.date)))
        if datas_disponiveis_main:
            val_min_main, val_max_main = datas_disponiveis_main[0], datas_disponiveis_main[-1]
            intervalo_data_main = st.select_slider(
                "Filtrar por Intervalo de Data:",
                options=datas_disponiveis_main,
                value=(val_min_main, val_max_main) if len(datas_disponiveis_main) > 1 else val_min_main,
                key="date_range_hist_main_v4"
            )
            if isinstance(intervalo_data_main, tuple) and len(intervalo_data_main) == 2:
                df_para_visualizar = df_hist_app_main[
                    (df_hist_app_main.index.date >= intervalo_data_main[0]) & 
                    (df_hist_app_main.index.date <= intervalo_data_main[1])
                ]
            else:
                df_para_visualizar = df_hist_app_main[df_hist_app_main.index.date == intervalo_data_main]
        else:
            df_para_visualizar = df_hist_app_main.copy()

        # Seção de Alertas Rápidos
        st.subheader("⚡ Painel de Alertas Rápidos")
        analisar_alertas_recentes_app(df_para_visualizar, LOGICA_ESP32_PARAMS_APP_CONFIG)
        st.markdown("---")

        # Diagnóstico e Sugestões
        st.subheader("🩺 Diagnóstico do Sistema e Sugestões")
        gerar_diagnostico_sugestoes_app(df_para_visualizar, LOGICA_ESP32_PARAMS_APP_CONFIG, st)
        st.markdown("---")

        # Tabela de Dados
        st.subheader("Registros do Período Selecionado")
        st.dataframe(df_para_visualizar.style.format({
            "umidade": "{:.1f}%", "ph_estimado": "{:.1f}", "temperatura": "{:.1f}°C",
            "fosforo_presente": lambda x: "Sim" if x else "Não",
            "potassio_presente": lambda x: "Sim" if x else "Não",
            "bomba_ligada": lambda x: "LIGADA" if x else "DESLIGADA"
        }), height=300, use_container_width=True)
        st.markdown("---")
        
        # Custos Operacionais
        st.subheader("💰 Custos Operacionais Estimados (Período Selecionado)")
        if 'custo_settings' in config_app: # Verifica se a seção de custo existe na config
            calcular_custos_operacionais_app(df_para_visualizar, config_app['custo_settings'], config_app, st)
        else:
            st.warning("Configurações de custo não encontradas no arquivo YAML. Não é possível calcular custos.")
        st.markdown("---")

        # Gráficos (como antes, usando df_para_visualizar)
        if not df_para_visualizar.empty and plotly_module:
            st.subheader("Gráficos Interativos do Período")
            # ... (seu código de gráficos plotly usando df_para_visualizar) ...
            try:
                col_g_main1, col_g_main2 = st.columns(2)
                if "umidade" in df_para_visualizar and len(df_para_visualizar["umidade"].dropna()) > 1:
                    fig_u_main = px.line(df_para_visualizar, y="umidade", title="Umidade (%)", color_discrete_sequence=['#27AE60'])
                    col_g_main1.plotly_chart(fig_u_main, use_container_width=True)
                
                if "ph_estimado" in df_para_visualizar and len(df_para_visualizar["ph_estimado"].dropna()) > 1:
                    fig_p_main = px.line(df_para_visualizar, y="ph_estimado", title="pH Estimado", color_discrete_sequence=['#F39C12'])
                    col_g_main2.plotly_chart(fig_p_main, use_container_width=True)
                
                if "temperatura" in df_para_visualizar and len(df_para_visualizar["temperatura"].dropna()) > 1:
                    fig_t_main = px.line(df_para_visualizar, y="temperatura", title="Temperatura (°C)", color_discrete_sequence=['#E74C3C'])
                    st.plotly_chart(fig_t_main, use_container_width=True)

                if 'bomba_ligada' in df_para_visualizar.columns:
                    df_bomba_plot_main = df_para_visualizar.copy()
                    df_bomba_plot_main['bomba_status_num'] = df_bomba_plot_main['bomba_ligada'].astype(int)
                    if len(df_bomba_plot_main["bomba_status_num"].dropna()) > 1:
                        fig_b_main = px.bar(df_bomba_plot_main, y='bomba_status_num', title="Acionamento da Bomba",
                                            labels={'timestamp': 'Data/Hora', 'bomba_status_num': 'Bomba'},
                                            color_discrete_sequence=['#3498DB'])
                        fig_b_main.update_layout(yaxis=dict(tickvals=[0, 1], ticktext=['Desligada', 'Ligada']))
                        st.plotly_chart(fig_b_main, use_container_width=True)
            except Exception as e_plot_plotly_main: st.error(f"Erro Plotly: {e_plot_plotly_main}")

    else:
        st.info("Nenhum dado histórico no banco. Execute `gerenciador_dados.py` para popular.")

# --- Aba: Clima (Meteoblue) ---
with tab_clima:
    # (Como antes, usando METEOBLUE_API_KEY_FIXA e sim_lat_app, sim_lon_app)
    st.header("Condições Meteorológicas (API Meteoblue)")
    if not METEOBLUE_API_KEY_FIXA:
        st.error("Chave da API Meteoblue não configurada no código do dashboard.")
    else:
        if st.button("Buscar Dados Climáticos Agora (Meteoblue)", key="btn_fetch_mb_main_v3"):
            with st.spinner(f"Buscando dados Meteoblue para Lat:{sim_lat_app:.2f}, Lon:{sim_lon_app:.2f}..."):
                dados_diarios_mb_main, erro_d_mb_main = buscar_dados_meteoblue_app(sim_lat_app, sim_lon_app, "basic-day")
                dados_horarios_mb_main, erro_h_mb_main = buscar_dados_meteoblue_app(sim_lat_app, sim_lon_app, "basic-1h")
            
            if erro_d_mb_main: st.error(f"Erro (diário Meteoblue): {erro_d_mb_main}")
            if erro_h_mb_main: st.error(f"Erro (horário Meteoblue): {erro_h_mb_main}")

            if dados_diarios_mb_main and "metadata" in dados_diarios_mb_main:
                st.subheader(f"Previsão Diária - {dados_diarios_mb_main['metadata'].get('name', 'Local')}")
                # ... (código para exibir dados diários da Meteoblue)
                try:
                    df_d_mb_main = pd.DataFrame({
                        'Data': pd.to_datetime(dados_diarios_mb_main['data_day']['time'][:3]),
                        'TMax(°C)': dados_diarios_mb_main['data_day']['temperature_max'][:3],
                        # ... (outras colunas diárias)
                        'Chuva(mm)': dados_diarios_mb_main['data_day']['precipitation'][:3]
                    }).set_index('Data')
                    st.dataframe(df_d_mb_main.style.format("{:.1f}", subset=['TMax(°C)', 'Chuva(mm)'])) # Ajuste subset
                except Exception as e_d_proc_mb_main: st.error(f"Processar dados diários Meteoblue: {e_d_proc_mb_main}")


            if dados_horarios_mb_main and "metadata" in dados_horarios_mb_main:
                st.subheader(f"Previsão Horária - {dados_horarios_mb_main['metadata'].get('name', 'Local')} (Próximas 12h)")
                # ... (código para exibir dados horários da Meteoblue)
                try:
                    df_h_mb_main = pd.DataFrame({
                        'Hora': pd.to_datetime(dados_horarios_mb_main['data_1h']['time'][:12]),
                        'Temp(°C)': dados_horarios_mb_main['data_1h']['temperature'][:12],
                        'Chuva(mm)': dados_horarios_mb_main['data_1h']['precipitation'][:12]
                        # ... (outras colunas horárias)
                    }).set_index('Hora')
                    st.dataframe(df_h_mb_main.style.format("{:.1f}", subset=['Temp(°C)', 'Chuva(mm)']))
                    
                    chuva_prox_val_mb_main = df_h_mb_main["Chuva (mm)"][:3].sum() if not df_h_mb_main.empty else 0.0
                    st.session_state.chuva_mm_meteoblue_proximas_horas_val_main = chuva_prox_val_mb_main
                    st.info(f"Chuva prevista (Meteoblue) para as próximas ~3h: {chuva_prox_val_mb_main:.1f} mm")
                    if plotly_module and not df_h_mb_main.empty:
                        fig_ch_mb_main = px.bar(df_h_mb_main, y="Chuva (mm)", title="Precipitação Horária Prevista (Meteoblue)")
                        st.plotly_chart(fig_ch_mb_main, use_container_width=True)
                except Exception as e_h_proc_mb_main: st.error(f"Processar dados horários Meteoblue: {e_h_proc_mb_main}")


# --- Aba: Simulador What-If ---
with tab_whatif:
    st.header("💡 Simulador 'What-If' e Recomendação de Irrigação")
    # ... (Layout e lógica do What-If como antes, usando LOGICA_ESP32_PARAMS_APP e
    #      st.session_state.chuva_mm_meteoblue_proximas_horas_val_main para a chuva)
    col_sim_wi_main1, col_sim_wi_main2 = st.columns(2)
    with col_sim_wi_main1:
        st.subheader("Condições da Fazenda (Hipotéticas)")
        sim_umid_val_wi_main = st.slider("Umidade Solo (%)", 0.0, 100.0, 25.0, 0.5, key="wi_umid_val_v3")
        sim_ph_val_wi_main = st.slider("pH Estimado Solo", 0.0, 14.0, 6.0, 0.1, key="wi_ph_val_v3")
    with col_sim_wi_main2:
        st.subheader("Nutrientes (Hipotéticos)")
        sim_p_val_wi_main = st.radio("Fósforo (P) Presente?", (False, True), index=0, key="wi_p_val_v3", format_func=lambda x: "Presente" if x else "Ausente")
        sim_k_val_wi_main = st.radio("Potássio (K) Presente?", (False, True), index=0, key="wi_k_val_v3", format_func=lambda x: "Presente" if x else "Ausente")

    chuva_final_wi_val_main = st.session_state.get('chuva_mm_meteoblue_proximas_horas_val_main', 0.0)
    st.caption(f"Considerando {chuva_final_wi_val_main:.1f}mm de chuva prevista (Meteoblue).")

    if st.button("Executar Simulação 'What-If' e Obter Recomendação", key="btn_run_whatif_val_v3"):
        # Análise de Risco Adicional (Nova Melhoria)
        st.subheader("Análise de Risco Adicional (Entrada)")
        if sim_umid_val_wi_main < LOGICA_ESP32_PARAMS_APP_CONFIG['UMIDADE_CRITICA_BAIXA']:
            st.error(f"⚠️ ALERTA WHAT-IF: Umidade de entrada ({sim_umid_val_wi_main}%) já está em nível crítico!")
        if not (LOGICA_ESP32_PARAMS_APP_CONFIG['PH_CRITICO_MINIMO'] <= sim_ph_val_wi_main <= LOGICA_ESP32_PARAMS_APP_CONFIG['PH_CRITICO_MAXIMO']):
            st.error(f"⚠️ ALERTA WHAT-IF: pH de entrada ({sim_ph_val_wi_main}) já está em nível crítico!")
        
        bomba_res_wi_val_c, motivo_res_wi_val_c = simular_logica_irrigacao_app(
            sim_umid_val_wi_main, sim_ph_val_wi_main, sim_p_val_wi_main, sim_k_val_wi_main, 
            LOGICA_ESP32_PARAMS_APP_CONFIG, 
            chuva_final_wi_val_main
        )
        st.subheader("Resultado da Simulação 'What-If':")
        if bomba_res_wi_val_c: 
            st.success(f"RECOMENDAÇÃO: LIGAR BOMBA ✅")
        else: 
            st.error(f"RECOMENDAÇÃO: MANTER BOMBA DESLIGADA ❌")
        st.info(f"Justificativa: {motivo_res_wi_val_c}")

        # Economia com Chuva (Nova Melhoria)
        if not bomba_res_wi_val_c and chuva_final_wi_val_main > 1.0: # Se não ligou E choveu significativamente
            # Simula qual seria a decisão SEM chuva
            bomba_sem_chuva, _ = simular_logica_irrigacao_app(
                sim_umid_val_wi_main, sim_ph_val_wi_main, sim_p_val_wi_main, sim_k_val_wi_main, 
                LOGICA_ESP32_PARAMS_APP_CONFIG, 0.0 # Simula sem chuva
            )
            if bomba_sem_chuva: # Se a bomba LIGARIA sem a chuva
                cfg_custo_local = config_app.get('custo_settings', CUSTO_SETTINGS_DEFAULT_GLOBAL_DASH.copy())
                tempo_ciclo_h = cfg_custo_local['tempo_irrigacao_padrao_minutos'] / 60.0
                vol_agua_ciclo_m3 = (cfg_custo_local['vazao_bomba_litros_por_hora'] / 1000.0) * tempo_ciclo_h
                custo_agua_ciclo_calc = vol_agua_ciclo_m3 * cfg_custo_local['custo_agua_reais_por_m3']
                energia_ciclo_kwh = cfg_custo_local['potencia_bomba_kw'] * tempo_ciclo_h
                custo_energia_ciclo_calc = energia_ciclo_kwh * cfg_custo_local['custo_energia_kwh']
                economia_ciclo = custo_agua_ciclo_calc + custo_energia_ciclo_calc
                st.success(f"💰 ECONOMIA ESTIMADA: Ao evitar irrigação devido à previsão de chuva, você economizou aproximadamente R$ {economia_ciclo:.2f} neste ciclo!")


# --- Aba: Sobre ---
with tab_sobre:
    # (Como antes)
    st.header("ℹ️ Sobre o FarmTech PhD Dashboard")
    st.markdown(f"""
    Este dashboard é parte do projeto FarmTech Solutions - Fase 3.
    **Desenvolvido por:** {config_app.get('report_settings', {}).get('autor_relatorio', 'Equipe FarmTech')}
    **Data:** {datetime.date.today().strftime('%d/%m/%Y')}
    """)

st.sidebar.markdown("---")
st.sidebar.caption(f"FarmTech Dashboard v1.1 - {datetime.datetime.now().year}")

# # --- Ponto de Entrada para rodar como script ---
if __name__ == '__main__':
    if os.environ.get('STREAMLIT_AUTOLAUNCHED') is None:
        os.environ['STREAMLIT_AUTOLAUNCHED'] = '1'
        # Configure para que o Streamlit não abra automaticamente nenhuma aba:
        os.environ["BROWSER"] = ""
        os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
        script_path = os.path.abspath(__file__)
        streamlit_cmd = [sys.executable, "-m", "streamlit", "run", script_path]
        process = subprocess.Popen(streamlit_cmd)
        import time, webbrowser, requests
        def wait_for_server(url, timeout=15):
            start = time.time()
            while time.time() - start < timeout:
                try:
                    resp = requests.get(url)
                    if resp.status_code == 200:
                        return True
                except:
                    pass
                time.sleep(0.5)
            return False
        if wait_for_server('http://localhost:8501', timeout=15):
            webbrowser.open('http://localhost:8501')
        else:
            logger.error("Server not available on http://localhost:8501")
        # NÃO chamar process.wait() para evitar bloqueios
    else:
        logger.info("Dashboard iniciado por processo filho. Execute manualmente se necessário.")