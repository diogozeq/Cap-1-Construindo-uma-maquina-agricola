#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FarmTech Solutions - Sistema Avançado de Gerenciamento e Análise de Irrigação
Descrição: Este script Python implementa um sistema completo para gerenciar, analisar e extrair
insights de dados coletados por um sistema de irrigação inteligente simulado (ESP32/Wokwi).
"""

import sys
import subprocess
import importlib
import logging
import os
import datetime
import time
import warnings
import io # Para suprimir output no PDF

# --- Configuração Inicial do Logging Otimizada ---
LOGGING_LEVEL = logging.INFO # ou logging.DEBUG
logging.basicConfig(
    level=LOGGING_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("FarmTechSuite")

# --- Mapeamento e Auto-Instalação de Dependências ---
PIP_MODULE_MAP = {
    'yaml': 'PyYAML',
    'sqlalchemy': 'SQLAlchemy',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'sklearn': 'scikit-learn',
    'statsmodels': 'statsmodels',
    'rich': 'rich',
    'plotext': 'plotext',
    'reportlab': 'reportlab'
}

INSTALLED_PACKAGES_CACHE = {}

def ensure_package(module_name, critical=True):
    """Verifica e instala um pacote se não estiver presente, com cache."""
    if module_name in INSTALLED_PACKAGES_CACHE:
        return INSTALLED_PACKAGES_CACHE[module_name]

    try:
        pkg = importlib.import_module(module_name)
        version = getattr(pkg, '__version__', None)
        if version is None: # Tentar outros atributos comuns
            version = getattr(pkg, 'VERSION', None)
            if version is None and module_name == 'reportlab': # Caso especial para reportlab
                version = getattr(pkg, 'Version', 'não especificada') # reportlab.Version é a string da versão
        if version is None: version = 'não especificada' # Fallback final
        logger.debug(f"Pacote '{module_name}' já está instalado (versão: {version}).")
        INSTALLED_PACKAGES_CACHE[module_name] = pkg
        return pkg
    except ImportError:
        pip_name = PIP_MODULE_MAP.get(module_name, module_name)
        logger.warning(f"Pacote '{module_name}' (pip: '{pip_name}') não encontrado. Tentando instalar...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--user", "--quiet", "--disable-pip-version-check"])
            logger.info(f"Pacote '{pip_name}' instalado com sucesso.")
            importlib.invalidate_caches()
            pkg = importlib.import_module(module_name)
            version_after_install = getattr(pkg, '__version__', None)
            if version_after_install is None:
                version_after_install = getattr(pkg, 'VERSION', None)
                if version_after_install is None and module_name == 'reportlab':
                    version_after_install = getattr(pkg, 'Version', 'não especificada')
            if version_after_install is None: version_after_install = 'não especificada'
            logger.info(f"Pacote '{module_name}' importado com sucesso após instalação (versão: {version_after_install}).")
            INSTALLED_PACKAGES_CACHE[module_name] = pkg
            return pkg
        except Exception as e:
            logger.error(f"Falha ao instalar ou importar '{pip_name}'. Erro: {e}")
            if critical:
                logger.critical(f"Dependência crítica '{pip_name}' não pôde ser instalada. O script não pode continuar.")
                sys.exit(f"ERRO: Instale '{pip_name}' manualmente (ex: pip install {pip_name}) e tente novamente.")
            else:
                logger.warning(f"Dependência opcional '{pip_name}' não instalada. Algumas funcionalidades podem não estar disponíveis.")
                INSTALLED_PACKAGES_CACHE[module_name] = None
                return None

logger.info("Iniciando FarmTech PhD Suite - Verificação e Carregamento de Dependências...")
yaml        = ensure_package('yaml', critical=True)
sqlalchemy  = ensure_package('sqlalchemy', critical=True)
pd          = ensure_package('pandas', critical=True)
np          = ensure_package('numpy', critical=True)
sklearn     = ensure_package('sklearn', critical=True)
statsmodels = ensure_package('statsmodels', critical=True)
rich        = ensure_package('rich', critical=True)
plotext_module = ensure_package('plotext', critical=False)
reportlab_module = ensure_package('reportlab', critical=False)
logger.info("Verificação de dependências principais concluída.")

# --- Imports específicos ---
from sqlalchemy import create_engine, Column, Integer, Float, Boolean, DateTime, String, inspect, func as sqlfunc, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError as SAIntegrityError

from pandas import DataFrame, Series, Timedelta, to_datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tools.sm_exceptions import ValueWarning as StatsmodelsValueWarning, \
                                         HessianInversionWarning as StatsmodelsHessianWarning, \
                                         ConvergenceWarning as StatsmodelsConvergenceWarning

from rich.console import Console as RichConsole
from rich.table import Table as RichTable
from rich.prompt import Prompt, Confirm, FloatPrompt, IntPrompt
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.padding import Padding
from rich.syntax import Syntax

if plotext_module:
    import plotext as plt
if reportlab_module:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as PDFTable, PageBreak, Image as ReportLabImage, KeepInFrame
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4 # Importado para uso no relatório
    from reportlab.platypus.tables import TableStyle as PDFTableStyle  # Corrigido: importa TableStyle corretamente

warnings.filterwarnings("ignore", category=StatsmodelsValueWarning)
warnings.filterwarnings("ignore", category=StatsmodelsHessianWarning)
warnings.filterwarnings("ignore", category=StatsmodelsConvergenceWarning)
warnings.filterwarnings("ignore", category=UserWarning, module='statsmodels')
warnings.filterwarnings("ignore", category=UserWarning, module='sklearn')

try:
    from dados_para_banco import dados_coletados_fase3
except ImportError:
    logger.warning("Arquivo 'dados_para_banco.py' não encontrado. Dados iniciais não serão populados automaticamente.")
    dados_coletados_fase3 = []

# --- Configurações ---
CONFIG_FILE = 'farmtech_config_phd.yaml'
DB_NAME_DEFAULT = 'farmtech_phd_data_final_v2.db'
TABLE_NAME_DEFAULT = 'leituras_sensores_phd_v2'

def carregar_configuracoes():
    default_config = {
        'db_name': DB_NAME_DEFAULT, 'table_name': TABLE_NAME_DEFAULT,
        'logica_esp32': {
            'UMIDADE_CRITICA_BAIXA': 15.0, 'UMIDADE_MINIMA_PARA_IRRIGAR': 20.0,
            'UMIDADE_ALTA_PARAR_IRRIGACAO': 60.0, 'PH_IDEAL_MINIMO': 5.5,
            'PH_IDEAL_MAXIMO': 6.5, 'PH_CRITICO_MINIMO': 4.5, 'PH_CRITICO_MAXIMO': 7.5,
        },
        'forecast_settings':{
            'num_leituras_futuras': 6, 'intervalo_leitura_minutos': 5,
            'alerta_forecast_ativo': True, 'arima_p': 1, 'arima_d': 1, 'arima_q': 1  # Componentes separados em vez de tupla
        },
        'custo_settings':{
            'custo_agua_reais_por_m3': 5.00, 'vazao_bomba_litros_por_hora': 1000.0,
            'tempo_irrigacao_padrao_minutos': 15.0, 'custo_energia_kwh': 0.75,
            'potencia_bomba_kw': 0.75
        },
        'ml_classifier':{
            'test_size': 0.3, 'random_state': 42, 'n_estimators': 100,
            'min_samples_leaf': 3
        },
        'report_settings':{
            'max_anomalias_no_relatorio': 5, 'max_leituras_recentes_tabela_pdf': 15,
            'autor_relatorio': "Diogo Zequini & FarmTech AI Team"
        },
        'cli_settings':{ 'max_leituras_tabela_console': 10 }
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: config_loaded = yaml.safe_load(f)
            logger.info(f"Configurações carregadas de '{CONFIG_FILE}'.")
            merged_config = default_config.copy()
            for key, value in config_loaded.items():
                if isinstance(value, dict) and isinstance(merged_config.get(key), dict):
                    merged_config[key].update(value)
                else: merged_config[key] = value
            if merged_config != config_loaded:
                 with open(CONFIG_FILE, 'w', encoding='utf-8') as f_save:
                    yaml.dump(merged_config, f_save, sort_keys=False, allow_unicode=True, indent=4)
                 logger.info(f"'{CONFIG_FILE}' atualizado com novas chaves padrão.")
            return merged_config
        except yaml.YAMLError as e:
            logger.error(f"Erro ao carregar '{CONFIG_FILE}': {e}. Usando padrões.")
            return default_config
    else:
        logger.warning(f"'{CONFIG_FILE}' não encontrado. Usando padrões e criando.")
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, sort_keys=False, allow_unicode=True, indent=4)
            logger.info(f"Arquivo de configuração padrão '{CONFIG_FILE}' criado.")
        except IOError as e:
            logger.error(f"Não foi possível criar '{CONFIG_FILE}': {e}")
        return default_config

config = carregar_configuracoes()
# Converter os parâmetros ARIMA individuais para a ordem requerida pela função
if 'forecast_settings' in config:
    config['forecast_settings']['arima_order'] = (
        config['forecast_settings'].get('arima_p', 1),
        config['forecast_settings'].get('arima_d', 1),
        config['forecast_settings'].get('arima_q', 1)
    )
TABLE_NAME = config['table_name']

# --- ORM e Banco de Dados ---
Base = declarative_base()
engine = create_engine(f"sqlite:///{config['db_name']}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
    finally:
        cursor.close()

class LeituraSensor(Base):
    __tablename__ = TABLE_NAME
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, unique=True, nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)
    umidade = Column(Float, nullable=False)
    ph_estimado = Column(Float, nullable=False)
    fosforo_presente = Column(Boolean, nullable=False)
    potassio_presente = Column(Boolean, nullable=False)
    temperatura = Column(Float)
    bomba_ligada = Column(Boolean, nullable=False)
    decisao_logica_esp32 = Column(String, nullable=True)

    def __repr__(self):
        return (f"<Leitura(id={self.id}, ts='{self.timestamp.strftime('%Y-%m-%d %H:%M')}', "
                f"U:{self.umidade:.1f}, pH:{self.ph_estimado:.1f}, P:{int(self.fosforo_presente)}, K:{int(self.potassio_presente)}, "
                f"T:{self.temperatura:.1f}°C, Bomba:{int(self.bomba_ligada)})>")

def criar_tabelas_se_nao_existirem():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Tabela '{TABLE_NAME}' verificada/criada.")
    except Exception as e:
        logger.critical(f"Erro crítico ao criar tabelas: {e}", exc_info=True); sys.exit(1)

def carregar_dados_para_pandas():
    """Carrega todos os dados do banco para um DataFrame Pandas com timestamp como índice."""
    with SessionLocal() as db:
        query = db.query(LeituraSensor).order_by(LeituraSensor.timestamp)
        # Usar db.bind em vez de engine diretamente para consistência com a sessão
        df = pd.read_sql(query.statement, db.bind, index_col='timestamp')
    if not df.empty:
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
    return df

# --- CRUD ---
def popular_dados_iniciais_phd(dados_originais_lista_de_dicts):
    """Popula o banco com dados iniciais, verificando primeiro se já existem registros."""
    if not dados_originais_lista_de_dicts:
        logger.info("Nenhum dado original para popular."); return
    
    # Verifica se já existem dados no banco em vez de usar arquivo de flag
    with SessionLocal() as db:
        count = db.query(LeituraSensor).count()
        if count > 0:
            logger.info(f"BD já populado ({count} registros encontrados)."); return
        
        logger.info(f"Populando banco com {len(dados_originais_lista_de_dicts)} registros iniciais...")
        try:
            for item_dict in dados_originais_lista_de_dicts:
                try:
                    ts_obj = datetime.datetime.strptime(item_dict['timestamp'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    logger.warning(f"Timestamp inválido '{item_dict['timestamp']}'. Usando now(utc).")
                    ts_obj = datetime.datetime.now(datetime.timezone.utc)
                decisao_simulada = f"U:{item_dict['umidade']:.1f},pH:{item_dict['ph_estimado']:.1f},P:{item_dict['fosforo_presente']},K:{item_dict['potassio_presente']}"
                leitura_obj = LeituraSensor(
                    timestamp=ts_obj, umidade=item_dict['umidade'], ph_estimado=item_dict['ph_estimado'],
                    fosforo_presente=bool(item_dict['fosforo_presente']), potassio_presente=bool(item_dict['potassio_presente']),
                    temperatura=item_dict['temperatura'], bomba_ligada=bool(item_dict['bomba_ligada']),
                    decisao_logica_esp32=item_dict.get('decisao_logica_esp32', decisao_simulada)
                )
                db.add(leitura_obj)
            db.commit()
            logger.info(f"{len(dados_originais_lista_de_dicts)} registros iniciais inseridos.")
        except SAIntegrityError as sie:
            db.rollback()
            logger.error(f"Erro de integridade ao inserir dados iniciais (timestamp duplicado?): {sie}.")
        except Exception as e:
            db.rollback(); logger.error(f"Erro ao inserir dados iniciais: {e}", exc_info=True)

def adicionar_leitura_interativo_phd(console_rich: RichConsole):
    console_rich.print(Panel("[bold gold1]--- Adicionar Nova Leitura Manualmente ---[/]", expand=False, border_style="yellow"))
    try:
        ts_str = Prompt.ask("Timestamp (AAAA-MM-DD HH:MM:SS) [Enter para agora UTC]", default=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
        timestamp = datetime.datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
        umidade = FloatPrompt.ask("Umidade (%)", default=round(np.random.uniform(10, 90),1))
        ph = FloatPrompt.ask("pH Estimado (0-14)", default=round(np.random.uniform(5, 8),1))
        fosforo = Confirm.ask("Fósforo Presente?", default=np.random.choice([True, False]))
        potassio = Confirm.ask("Potássio Presente?", default=np.random.choice([True, False]))
        temperatura = FloatPrompt.ask("Temperatura (°C)", default=round(np.random.uniform(15, 30),1))
        
        console_rich.print("\n[bold]Simulando lógica de irrigação:[/]")
        bomba_sug, dec_sug = simular_logica_irrigacao_esp32_py(umidade, ph, fosforo, potassio, console_rich, config['logica_esp32'])
        bomba_final = Confirm.ask(f"Bomba Ligada? (Lógica sugere: {'LIGADA' if bomba_sug else 'DESLIGADA'})", default=bomba_sug)
        
        if not (0 <= umidade <= 100 and 0 <= ph <= 14):
            console_rich.print("[bold red]Umidade ou pH fora das faixas. Leitura não adicionada.[/]"); return
        with SessionLocal() as db:
            nova = LeituraSensor(timestamp=timestamp, umidade=umidade, ph_estimado=ph, fosforo_presente=fosforo,
                                 potassio_presente=potassio, temperatura=temperatura, bomba_ligada=bomba_final,
                                 decisao_logica_esp32=dec_sug)
            db.add(nova); db.commit(); db.refresh(nova)
            logger.info(f"Nova leitura ID: {nova.id} adicionada.")
            console_rich.print(f"[bold chartreuse1]Leitura ID {nova.id} adicionada![/]")
    except ValueError: console_rich.print(f"[bold red]Erro na entrada de dados.[/]")
    except SAIntegrityError: console_rich.print(f"[bold red]Erro: Timestamp '{ts_str}' já existe.[/]")
    except Exception as e: logger.error(f"Erro ao add leitura: {e}", exc_info=True); console_rich.print(f"[bold red]Erro inesperado.[/]")

def visualizar_leituras_phd(console_rich: RichConsole, filtro_id: int = None, limit: int = None):
    console_rich.print(Panel(f"[bold sky_blue1]--- Visualizar Leituras ---[/]", expand=False, border_style="sky_blue1"))
    with SessionLocal() as db:
        try:
            query = db.query(LeituraSensor)
            if filtro_id: query = query.filter(LeituraSensor.id == filtro_id); limit = 1
            leituras = query.order_by(LeituraSensor.timestamp.desc()).limit(limit or config['cli_settings']['max_leituras_tabela_console']).all()
            if not leituras:
                msg = f"ID {filtro_id} não encontrado." if filtro_id else "Nenhuma leitura no banco."
                console_rich.print(f"[yellow]{msg}[/]"); return
            if filtro_id and leituras: console_rich.print(f"[bold]Detalhes da Leitura ID {leituras[0].id}:[/]")
            exibir_leituras_rich_table_phd(console_rich, leituras, titulo="Visualização de Leituras")
        except Exception as e: logger.error(f"Erro ao viz leituras: {e}", exc_info=True); console_rich.print("[bold red]Erro ao buscar leituras.[/]")

def exibir_leituras_rich_table_phd(console_rich: RichConsole, leituras: list, titulo: str = "Leituras Recentes"):
    if not leituras: console_rich.print("[yellow]Nenhuma leitura para exibir.[/]"); return
    table = RichTable(title=titulo, show_lines=True, border_style="blue")
    cols = ["ID", "Timestamp (UTC)", "Umidade (%)", "pH", "P", "K", "Temp (°C)", "Bomba", "Decisão ESP32"]
    styles = ["dim", "cyan", "green", "yellow", None, None, "magenta", None, None]
    justifies = ["right", None, "right", "right", "center", "center", "right", "center", None]
    min_widths = [5, 20, None, None, None, None, None, None, None]
    max_widths = [None, None, None, None, None, None, None, None, 30]

    for i, col_name in enumerate(cols):
        table.add_column(col_name, style=styles[i], justify=justifies[i] or "left", 
                         min_width=min_widths[i], max_width=max_widths[i], overflow="fold" if max_widths[i] else None)
    for leitura in leituras:
        table.add_row(
            str(leitura.id), leitura.timestamp.strftime('%Y-%m-%d %H:%M:%S'), f"{leitura.umidade:.1f}",
            f"{leitura.ph_estimado:.1f}", "Sim" if leitura.fosforo_presente else "Não",
            "Sim" if leitura.potassio_presente else "Não",
            f"{leitura.temperatura:.1f}" if leitura.temperatura is not None else "N/A",
            "[bold red]ON[/]" if leitura.bomba_ligada else "[bold blue]OFF[/]",
            leitura.decisao_logica_esp32 or "N/A"
        )
    console_rich.print(table)

def atualizar_leitura_interativo_phd(console_rich: RichConsole):
    console_rich.print(Panel("[bold orange1]--- Atualizar Leitura ---[/]", expand=False, border_style="orange1"))
    try:
        id_leitura = IntPrompt.ask("ID da leitura para atualizar")
        with SessionLocal() as db:
            leitura = db.get(LeituraSensor, id_leitura)
            if not leitura: console_rich.print(f"[bold red]ID {id_leitura} não encontrado.[/]"); return
            console_rich.print(f"Atual ID {id_leitura}: Umid={leitura.umidade:.1f}%, pH={leitura.ph_estimado:.1f}, Bomba={'ON' if leitura.bomba_ligada else 'OFF'}")
            
            opts = {"1": "Umidade", "2": "pH Estimado", "3": "Bomba Ligada", "0": "Cancelar"}
            tbl = RichTable(show_header=False); tbl.add_column("Opt"); tbl.add_column("Campo")
            for k,v in opts.items(): tbl.add_row(f"[{k}]",v)
            console_rich.print(tbl)
            esc_campo = Prompt.ask("Qual campo atualizar?", choices=opts.keys(), default="0")

            if esc_campo == '1':
                val = FloatPrompt.ask(f"Nova Umidade (%)", default=round(leitura.umidade,1))
                if not (0 <= val <= 100): raise ValueError("Umidade inválida.")
                leitura.umidade = val
            elif esc_campo == '2':
                val = FloatPrompt.ask(f"Novo pH", default=round(leitura.ph_estimado,1))
                if not (0 <= val <= 14): raise ValueError("pH inválido.")
                leitura.ph_estimado = val
            elif esc_campo == '3': leitura.bomba_ligada = Confirm.ask(f"Bomba Ligada?", default=leitura.bomba_ligada)
            elif esc_campo == '0': console_rich.print("Cancelado."); return
            else: console_rich.print("[red]Opção inválida."); return # Não deve ocorrer
            
            db.commit(); logger.info(f"Leitura ID {id_leitura} atualizada.")
            console_rich.print(f"[bold green]Leitura ID {id_leitura} atualizada![/]")
    except ValueError as ve: console_rich.print(f"[bold red]Entrada inválida: {ve}.[/]")
    except Exception as e: logger.error(f"Erro ao att leitura: {e}", exc_info=True); console_rich.print("[bold red]Erro inesperado.[/]")

def deletar_leitura_interativo_phd(console_rich: RichConsole):
    console_rich.print(Panel("[bold red]--- Deletar Leitura ---[/]", expand=False, border_style="red"))
    try:
        id_leitura = IntPrompt.ask("ID da leitura para deletar")
        with SessionLocal() as db:
            leitura = db.get(LeituraSensor, id_leitura)
            if not leitura: console_rich.print(f"[bold red]ID {id_leitura} não encontrado.[/]"); return
            console_rich.print(f"Deletando ID {id_leitura}: TS={leitura.timestamp.strftime('%Y-%m-%d %H:%M')}, Umid={leitura.umidade:.1f}%")
            if Confirm.ask(f"Deletar registro ID {id_leitura}?", default=False):
                db.delete(leitura); db.commit()
                logger.info(f"Leitura ID {id_leitura} deletada.")
                console_rich.print(f"[bold green]Leitura ID {id_leitura} deletada.[/]")
            else: console_rich.print("Deleção cancelada.")
    except ValueError: console_rich.print("[bold red]ID inválido.[/]")
    except Exception as e: logger.error(f"Erro ao del leitura: {e}", exc_info=True); console_rich.print("[bold red]Erro inesperado.[/]")

# --- Análises ---
clf_modelo_global = None # Modelo ML treinado

def simular_logica_irrigacao_esp32_py(umidade, ph, p_presente, k_presente, console_rich: RichConsole, cfg_logica: dict):
    ligar_bomba, motivo = False, "Condições padrão, bomba desligada."
    if umidade < cfg_logica['UMIDADE_CRITICA_BAIXA']:
        ligar_bomba, motivo = True, f"EMERGÊNCIA: Umidade crítica ({umidade:.1f}%) < {cfg_logica['UMIDADE_CRITICA_BAIXA']:.1f}%."
    elif ph < cfg_logica['PH_CRITICO_MINIMO'] or ph > cfg_logica['PH_CRITICO_MAXIMO']:
        motivo = f"pH crítico ({ph:.1f}) fora de {cfg_logica['PH_CRITICO_MINIMO']:.1f}-{cfg_logica['PH_CRITICO_MAXIMO']:.1f}."
    elif umidade < cfg_logica['UMIDADE_MINIMA_PARA_IRRIGAR']:
        if cfg_logica['PH_IDEAL_MINIMO'] <= ph <= cfg_logica['PH_IDEAL_MAXIMO']:
            ligar_bomba = True
            if p_presente and k_presente: motivo = f"Umid. baixa ({umidade:.1f}%), pH ideal ({ph:.1f}), P e K presentes."
            elif p_presente or k_presente: motivo = f"Umid. baixa ({umidade:.1f}%), pH ideal ({ph:.1f}), P ou K presente."
            else: motivo = f"Umid. baixa ({umidade:.1f}%), pH ideal ({ph:.1f}), P e K ausentes."
        else: motivo = f"Umid. baixa ({umidade:.1f}%), mas pH ({ph:.1f}) fora do ideal."
    elif umidade > cfg_logica['UMIDADE_ALTA_PARAR_IRRIGACAO']:
        motivo = f"Umidade alta ({umidade:.1f}%) > {cfg_logica['UMIDADE_ALTA_PARAR_IRRIGACAO']:.1f}%."
    return ligar_bomba, motivo

def executar_estatisticas_descritivas_phd(df, console_rich: RichConsole):
    if df.empty or len(df) < 2: console_rich.print("[yellow]Dados insuficientes para estatísticas.[/]"); return None
    cols = ['umidade', 'ph_estimado', 'temperatura']
    valid_cols = [c for c in cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if not valid_cols: console_rich.print("[yellow]Nenhuma coluna numérica para estatísticas.[/]"); return None
    stats = df[valid_cols].describe().round(2)
    console_rich.print("\n[bold cyan]== Estatísticas Descritivas ==[/]"); console_rich.print(stats)
    return stats

def executar_deteccao_anomalias_phd(df, console_rich: RichConsole):
    console_rich.print(f"\n[bold red]== Detecção de Anomalias (Z-score) ==[/]")
    if df.empty or len(df) < 3:
        console_rich.print("[yellow]Dados insuficientes para anomalias.[/]"); return pd.DataFrame()
    anomalias = []
    cols = ['umidade', 'ph_estimado', 'temperatura']; limite_z = 2.5
    for col in cols:
        if col not in df.columns or df[col].isnull().all(): continue
        s = df[col].dropna(); 
        if len(s) < 3 or s.std() == 0: continue
        z_scores = (s - s.mean()) / s.std()
        outliers = s[np.abs(z_scores) > limite_z]
        for idx, val in outliers.items():
            anomalias.append({'timestamp': idx, 'parametro': col, 'valor': val, 
                              'z_score': z_scores.loc[idx], 'media_ref': s.mean(), 'std_ref': s.std()})
    anom_df = pd.DataFrame(anomalias)
    if not anom_df.empty:
        console_rich.print(f"[yellow]Encontradas {len(anom_df)} anomalias potenciais (Z > {limite_z}):[/]")
        anom_df = anom_df.sort_values(by='timestamp')
        tbl = RichTable(title="Anomalias Detectadas")
        tbl.add_column("Timestamp"); tbl.add_column("Parâmetro"); tbl.add_column("Valor"); tbl.add_column("Z-Score")
        for _, r in anom_df.head(config['report_settings'].get('max_anomalias_no_relatorio', 5)).iterrows():
             tbl.add_row(r['timestamp'].strftime('%y-%m-%d %H:%M'), r['parametro'], f"{r['valor']:.2f}", f"{r['z_score']:.2f}")
        console_rich.print(tbl)
    else: console_rich.print("[green]Nenhuma anomalia significativa detectada.[/]")
    return anom_df

def executar_correlacoes_phd(df, console_rich: RichConsole):
    console_rich.print("\n[bold cyan]== Matriz de Correlação (Pearson) ==[/]")
    if df.empty or len(df) < 2: console_rich.print("[yellow]Dados insuficientes para correlações.[/]"); return None
    cols = ['umidade', 'ph_estimado', 'temperatura']
    valid = [c for c in cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() > 1]
    if len(valid) < 2: console_rich.print("[yellow]Colunas insuficientes para correlações.[/]"); return None
    corr_matrix = df[valid].corr(method='pearson').round(3)
    console_rich.print("Correlação entre variáveis:"); console_rich.print(corr_matrix)
    return corr_matrix

def treinar_ou_carregar_classificador_phd(df_historico, console_rich: RichConsole, cfg_ml: dict):
    global clf_modelo_global
    console_rich.print(f"\n[bold cyan]== Classificador de Emergência (Random Forest) ==[/]")
    if df_historico.empty or len(df_historico) < 10:
        console_rich.print("[yellow]Dados insuficientes para treinar classificador.[/]")
        clf_modelo_global = None; return None, 0.0, None, None

    df = df_historico.copy()
    cfg_logica = config['logica_esp32']
    df['emergencia_real'] = ((df['umidade'] < cfg_logica['UMIDADE_CRITICA_BAIXA']) | \
                            (df['ph_estimado'] < cfg_logica['PH_CRITICO_MINIMO']) | \
                            (df['ph_estimado'] > cfg_logica['PH_CRITICO_MAXIMO'])).astype(int)

    if len(df['emergencia_real'].unique()) < 2:
        console_rich.print("[yellow]Apenas uma classe 'emergencia_real'. Não é possível treinar.[/]")
        clf_modelo_global = None; return None, 0.0, None, None

    features = ['umidade', 'ph_estimado', 'temperatura']
    X = df[features].fillna(df[features].mean()) # Tratar NaNs
    y = df['emergencia_real']
    
    try: X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=cfg_ml['test_size'], random_state=cfg_ml['random_state'], stratify=y)
    except ValueError: X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=cfg_ml['test_size'], random_state=cfg_ml['random_state'])

    clf = RandomForestClassifier(n_estimators=cfg_ml['n_estimators'], random_state=cfg_ml['random_state'],
                                 min_samples_leaf=cfg_ml['min_samples_leaf'], class_weight='balanced')
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    console_rich.print(f"[green]Acurácia do Modelo (teste):[/] {acc*100:.1f}%")
    fi_df = pd.DataFrame({'Feature': X.columns, 'Importance': clf.feature_importances_}).sort_values(by='Importance', ascending=False)
    console_rich.print("[bold]Importância das Features:[/]"); console_rich.print(fi_df.round(3))

    clf_modelo_global = clf
    clf_modelo_global.last_accuracy_ = acc
    return clf, acc, X_test, y_test

def executar_forecast_umidade_phd(df, console_rich: RichConsole, cfg_fc: dict, umid_critica: float):
    console_rich.print(f"\n[bold cyan]== Forecast de Umidade (ARIMA) ==[/]")
    alerts, forecast = [], None
    
    # Verificar dados disponíveis
    if df.empty:
        console_rich.print("[yellow]Sem dados para forecast.[/]"); return forecast, alerts
    if 'umidade' not in df.columns:
        console_rich.print("[yellow]Coluna 'umidade' não encontrada.[/]"); return forecast, alerts
    if len(df['umidade'].dropna()) < 10:
        console_rich.print("[yellow]Menos de 10 valores válidos de umidade. Forecast requer mais dados.[/]"); return forecast, alerts
    
    console_rich.print("Preparando dados para forecast...")
    
    # Criar uma cópia para não modificar o original
    try:
        # Garantir que o índice seja temporal e ordenado
        work_df = df.copy()
        if not isinstance(work_df.index, pd.DatetimeIndex):
            console_rich.print("[yellow]Índice não é temporal, preparando dados...[/]")
            if 'timestamp' in work_df.columns:
                work_df = work_df.set_index('timestamp')
            else:
                # Criar um índice temporal sintético - útil quando o índice é um problema
                console_rich.print("[yellow]Criando índice temporal sintético...[/]")
                datas = pd.date_range(
                    start=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=len(work_df)-1),
                    periods=len(work_df),
                    freq='5min'
                )
                work_df.index = datas
        
        # Ordenar pelo índice de tempo
        work_df = work_df.sort_index()
        
        # Extrair dados de umidade e converter para float
        umid_series = work_df['umidade'].astype(float)
        
        # Lidar com valores faltantes
        umid_series = umid_series.interpolate(method='linear')
        if umid_series.isnull().any():
            umid_series = umid_series.ffill().bfill()
        
        if umid_series.isnull().any():
            console_rich.print("[red]Ainda existem valores nulos após tratamento.[/]")
            return forecast, alerts
            
        console_rich.print(f"Série preparada: {len(umid_series)} pontos")
        
        # Abordagem alternativa se o índice estiver sendo um problema
        # Criar série com índice numérico
        numeric_series = pd.Series(umid_series.values)
        
        # Configuração ARIMA e exibição
        arima_order = cfg_fc.get('arima_order', (1, 1, 1))
        console_rich.print(f"Ordem ARIMA: {arima_order}")
        
        # Tentar abordagens diferentes, uma de cada vez
        console_rich.print("Tentando forecast com série temporal...")
        try:
            # Primeira tentativa com o índice original
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model1 = ARIMA(umid_series, order=arima_order).fit()
                forecast1 = model1.forecast(steps=cfg_fc['num_leituras_futuras'])
                
                if isinstance(forecast1, (pd.Series, np.ndarray)) and len(forecast1) > 0:
                    forecast = forecast1
                    console_rich.print("[green]Forecast bem-sucedido com série temporal![/]")
                else:
                    console_rich.print("[yellow]Forecast com série temporal retornou vazio, tentando alternativa...[/]")
                    raise ValueError("Forecast vazio")
        except Exception as e1:
            console_rich.print(f"[yellow]Tentativa 1 falhou: {str(e1)}[/]")
            
            # Segunda tentativa com índice numérico (nem sempre funciona, mas é uma alternativa)
            try:
                console_rich.print("Tentando forecast com série numérica simples...")
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model2 = ARIMA(numeric_series, order=arima_order, enforce_stationarity=False).fit()
                    forecast2 = model2.forecast(steps=cfg_fc['num_leituras_futuras'])
                    
                    if isinstance(forecast2, (pd.Series, np.ndarray)) and len(forecast2) > 0:
                        forecast = forecast2
                        console_rich.print("[green]Forecast bem-sucedido com série numérica![/]")
                    else:
                        console_rich.print("[yellow]Ambas tentativas de forecast retornaram vazio.[/]")
            except Exception as e2:
                console_rich.print(f"[yellow]Tentativa 2 falhou: {str(e2)}[/]")
                
                # Terceira tentativa - método mais simples possível
                console_rich.print("Tentando método mais simples (média móvel)...")
                try:
                    # Método de fallback - média móvel simples
                    valores = umid_series.values
                    media_ultimos = np.mean(valores[-3:]) if len(valores) >= 3 else np.mean(valores)
                    forecast_simples = np.array([media_ultimos] * cfg_fc['num_leituras_futuras'])
                    forecast = pd.Series(forecast_simples)
                    console_rich.print("[green]Forecast simplificado gerado com sucesso.[/]")
                except Exception as e3:
                    console_rich.print(f"[red]Todas tentativas de forecast falharam: {str(e3)}[/]")
                    return None, alerts
        
        # Exibir e verificar resultados
        if forecast is not None:
            # Converter para DataFrame para exibição
            if isinstance(forecast, pd.Series):
                fc_df = forecast.to_frame(name='Umidade Prevista (%)')
            else:
                fc_df = pd.DataFrame(forecast, columns=['Umidade Prevista (%)'])
            
            # Arredondar para melhor visualização
            fc_df = fc_df.round(1)
            console_rich.print(fc_df)
            
            # Verificar alertas
            if cfg_fc.get('alerta_forecast_ativo', False):
                for i, val_fc in enumerate(forecast):
                    if val_fc < umid_critica:
                        t_alert = (i + 1) * cfg_fc['intervalo_leitura_minutos']
                        alerta = f"Umid. crítica ({val_fc:.1f}%) prevista em ~{t_alert} min ({i+1}ª leitura)."
                        console_rich.print(f"[bold red]ALERTA FORECAST:[/] {alerta}"); alerts.append(alerta)
        else:
            console_rich.print("[yellow]Forecast não produziu resultados.[/]")
            
    except Exception as e: 
        logger.error(f"Erro na execução do forecast: {e}", exc_info=True)
        console_rich.print(f"[yellow]Problema ao gerar forecast: {e}[/]")
        forecast = None
        
    return forecast, alerts

def executar_analise_custo_detalhada(df, cfg_custos: dict, console_rich: RichConsole):
    console_rich.print(Panel("[bold dodger_blue1]--- Análise de Custo da Irrigação ---[/]", expand=False, border_style="dodger_blue1"))
    if df.empty or 'bomba_ligada' not in df.columns:
        console_rich.print("[yellow]Dados insuficientes ('bomba_ligada') para custo.[/]"); return 0, 0.0, 0.0, 0.0
    
    intervalo_min = config['forecast_settings'].get('intervalo_leitura_minutos', 5)
    if pd.api.types.is_bool_dtype(df['bomba_ligada']):
        tempo_on_min = df['bomba_ligada'].sum() * intervalo_min
        ciclos = df['bomba_ligada'].astype(int).diff().fillna(0).eq(1).sum()
    elif pd.api.types.is_numeric_dtype(df['bomba_ligada']):
        tempo_on_min = df['bomba_ligada'].astype(bool).sum() * intervalo_min
        ciclos = df['bomba_ligada'].astype(bool).astype(int).diff().fillna(0).eq(1).sum()
    else: console_rich.print("[red]'bomba_ligada' não é bool/num.[/]"); return 0, 0.0, 0.0, 0.0

    if tempo_on_min == 0: console_rich.print("[green]Bomba não acionada. Custo zero.[/]"); return 0, 0.0, 0.0, 0.0
    
    tempo_on_h = tempo_on_min / 60.0
    vol_agua_m3 = (cfg_custos['vazao_bomba_litros_por_hora'] / 1000.0) * tempo_on_h
    custo_agua = vol_agua_m3 * cfg_custos['custo_agua_reais_por_m3']
    cons_kwh = cfg_custos['potencia_bomba_kw'] * tempo_on_h
    custo_energia = cons_kwh * cfg_custos['custo_energia_kwh']
    custo_total = custo_agua + custo_energia

    console_rich.print(f"Ciclos de irrigação: {ciclos}"); console_rich.print(f"Tempo bomba ligada: {tempo_on_min:.1f} min")
    console_rich.print(f"Volume água: {vol_agua_m3:.3f} m³; Custo água: R$ {custo_agua:.2f}")
    console_rich.print(f"Consumo energia: {cons_kwh:.2f} kWh; Custo energia: R$ {custo_energia:.2f}")
    console_rich.print(Panel(f"Custo Total Estimado: [bold green]R$ {custo_total:.2f}[/]", expand=False))
    return ciclos, custo_total, custo_agua, custo_energia

def exibir_grafico_umidade_plotext_phd(df, console_rich: RichConsole):
    """Exibe um gráfico ASCII da umidade utilizando a biblioteca plotext."""
    if not plotext_module: 
        console_rich.print("[yellow]'plotext' não disponível. Gráfico ASCII não gerado.[/]"); return
    if df.empty or 'umidade' not in df.columns or len(df['umidade'].dropna()) < 2:
        console_rich.print("[yellow]Dados insuficientes para gráfico ASCII.[/]"); return
    
    console_rich.print("\n[bold cyan]== Gráfico ASCII Histórico de Umidade ==[/]")
    df_plot = df.copy(); num_pts = len(df_plot)
    if num_pts > 50: df_plot = df_plot.iloc[::(num_pts // 30), :] # Amostra
    
    try:
        plt.clf()
        # Usar o índice apenas como números, não como datas
        indices = list(range(len(df_plot)))
        plt.plot(indices, df_plot['umidade'].tolist(), marker="braille")
        plt.title("Histórico Umidade Solo (%)")
        plt.xlabel("Leituras")
        plt.ylabel("Umidade (%)")
        plt.theme("matrix")
        plt.show()
        console_rich.print("[bold](Gráfico exibido acima)[/bold]")
    except Exception as e:
        console_rich.print(f"[yellow]Erro ao gerar gráfico ASCII: {e}[/]")

def executar_simulador_what_if(console_rich: RichConsole, modelo_ml, cfg_logica: dict):
    console_rich.print(Panel("[bold orchid]--- Simulador 'What-If' ---[/]", expand=False, border_style="orchid"))
    u = FloatPrompt.ask("Umidade (%)", default=round(np.random.uniform(10,70),1))
    ph = FloatPrompt.ask("pH", default=round(np.random.uniform(5,7.5),1))
    temp = FloatPrompt.ask("Temperatura (°C)", default=round(np.random.uniform(18,28),1))
    p = Confirm.ask("Fósforo?", default=np.random.choice([True,False]))
    k = Confirm.ask("Potássio?", default=np.random.choice([True,False]))

    console_rich.print("\n[bold]--- Simulação (Lógica ESP32) ---[/]")
    bomba_esp, motivo_esp = simular_logica_irrigacao_esp32_py(u, ph, p, k, console_rich, cfg_logica)
    dec_txt = "[bold red]LIGAR BOMBA[/]" if bomba_esp else "[bold blue]MANTER DESLIGADA[/]"
    console_rich.print(f"Decisão ESP32: {dec_txt}\nMotivo: {motivo_esp}")

    console_rich.print("\n[bold]--- Simulação (Modelo ML Risco Emergência) ---[/]")
    if modelo_ml is None: console_rich.print("[yellow]Modelo ML não treinado.[/]"); return
    try:
        dados_pred = pd.DataFrame([[u, ph, temp]], columns=['umidade', 'ph_estimado', 'temperatura'])
        if hasattr(modelo_ml, "predict_proba"):
            prob = modelo_ml.predict_proba(dados_pred)[0]
            risco = prob[1] 
            cor_risco = "red" if risco > 0.7 else ("yellow" if risco > 0.4 else "green")
            console_rich.print(f"Risco Emergência (ML): [{cor_risco}]{risco*100:.1f}%[/]")
        pred_ml = modelo_ml.predict(dados_pred)[0]
        res_ml = "[bold red]EMERGÊNCIA[/]" if pred_ml == 1 else "[bold green]NORMAL[/]"
        console_rich.print(f"Classificação ML: {res_ml}")
        if hasattr(modelo_ml, 'last_accuracy_'): console_rich.print(f"(Acurácia modelo: {modelo_ml.last_accuracy_*100:.1f}%)")
    except Exception as e: logger.error(f"Erro ML sim: {e}"); console_rich.print(f"[red]Erro ML: {e}[/]")

# --- Relatório PDF ---
def _add_empty_lines(story, num_lines=1):
    for _ in range(num_lines): story.append(Spacer(1, 0.2*cm))

def _df_to_pdf_table(df, col_widths=None, styles=None):
    if df is None or df.empty: return Paragraph("Dados não disponíveis.", styles['Normal'] if styles else getSampleStyleSheet()['Normal'])
    data = [list(df.columns)] + df.values.tolist()
    # Converter todos os dados para string para evitar problemas com tipos no PDFTable
    data_str = [[str(item) for item in row] for row in data]

    pdf_table = PDFTable(data_str, colWidths=col_widths)
    # Corrigido: uso adequado do PDFTableStyle
    pdf_table.setStyle(PDFTableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4A6B4D")), # Verde escuro para cabeçalho
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#E8F5E9")), # Verde claro para dados
        ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    return pdf_table

def gerar_relatorio_farmtech_pdf_phd(
    df_historico, stats_df, corr_df, forecast_series, alertas_fc,
    ciclos_irr, custo_total, modelo_ml, anomalias_df, console_rich: RichConsole
):
    if not reportlab_module:
        console_rich.print("[red]Reportlab não disponível. PDF não gerado.[/]"); return

    cfg_rep = config['report_settings']
    fname = f"FarmTech_PhD_Relatorio_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(fname, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='H1_Custom', parent=styles['h1'], alignment=TA_CENTER, fontSize=18, spaceAfter=0.5*cm, textColor=colors.HexColor("#2E7D32")))
    styles.add(ParagraphStyle(name='H2_Custom', parent=styles['h2'], fontSize=14, spaceBefore=0.5*cm, spaceAfter=0.3*cm, textColor=colors.HexColor("#4A6B4D")))
    styles.add(ParagraphStyle(name='Body_Center', parent=styles['Normal'], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Alert_Red', parent=styles['Normal'], textColor=colors.red))
    
    story = []
    story.append(Paragraph("Relatório Analítico Avançado - FarmTech PhD Suite", styles['H1_Custom']))
    story.append(Paragraph(f"Gerado em: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Body_Center']))
    story.append(Paragraph(f"Autor: {cfg_rep.get('autor_relatorio', 'FarmTech System')}", styles['Body_Center']))
    _add_empty_lines(story, 2)

    story.append(Paragraph("Resumo Executivo", styles['H2_Custom']))
    resumo = f"Relatório de {len(df_historico)} leituras. Custo total: R$ {custo_total:.2f} ({ciclos_irr} ciclos). "
    if modelo_ml and hasattr(modelo_ml, 'last_accuracy_'): resumo += f"ML Acc: {modelo_ml.last_accuracy_*100:.1f}%. "
    if alertas_fc: resumo += f"{len(alertas_fc)} alertas de forecast. "
    story.append(Paragraph(resumo, styles['Normal']))
    _add_empty_lines(story)

    story.append(Paragraph("Leituras Recentes", styles['H2_Custom']))
    if not df_historico.empty:
        df_rec = df_historico.tail(cfg_rep.get('max_leituras_recentes_tabela_pdf',10)).reset_index()
        df_rec['timestamp'] = df_rec['timestamp'].dt.strftime('%y-%m-%d %H:%M')
        for c_bool in ['fosforo_presente','potassio_presente','bomba_ligada']:
            if c_bool in df_rec.columns: df_rec[c_bool] = df_rec[c_bool].apply(lambda x: "Sim" if x else "Não")
        cols_pdf = {'timestamp':'TS', 'umidade':'U(%)', 'ph_estimado':'pH', 'temperatura':'T(C)', 'bomba_ligada':'Bomba'}
        df_rec_disp = df_rec[[c for c in cols_pdf.keys() if c in df_rec.columns]].rename(columns=cols_pdf)
        story.append(_df_to_pdf_table(df_rec_disp, styles=styles))
    else: story.append(Paragraph("Nenhuma leitura.", styles['Normal']))
    _add_empty_lines(story)

    story.append(Paragraph("Estatísticas Descritivas", styles['H2_Custom']))
    if stats_df is not None: story.append(_df_to_pdf_table(stats_df.reset_index().rename(columns={'index':'Métrica'}), styles=styles))
    else: story.append(Paragraph("N/A.", styles['Normal']))
    _add_empty_lines(story); story.append(PageBreak())

    story.append(Paragraph("Detecção de Anomalias", styles['H2_Custom']))
    if anomalias_df is not None and not anomalias_df.empty:
        anom_pdf = anomalias_df.copy()
        anom_pdf['timestamp'] = pd.to_datetime(anom_pdf['timestamp']).dt.strftime('%y-%m-%d %H:%M')
        anom_disp = anom_pdf[['timestamp','parametro','valor','z_score']].head(cfg_rep.get('max_anomalias_no_relatorio',5))
        anom_disp.columns = ['TS','Parâmetro','Valor','Z-Score']
        story.append(_df_to_pdf_table(anom_disp, styles=styles))
    else: story.append(Paragraph("Nenhuma anomalia detectada.", styles['Normal']))
    _add_empty_lines(story)

    story.append(Paragraph("Matriz de Correlação", styles['H2_Custom']))
    if corr_df is not None: story.append(_df_to_pdf_table(corr_df.reset_index().rename(columns={'index':'Var'}), styles=styles))
    else: story.append(Paragraph("N/A.", styles['Normal']))
    _add_empty_lines(story)

    story.append(Paragraph("Forecast de Umidade", styles['H2_Custom']))
    if forecast_series is not None:
        fc_df = forecast_series.to_frame(name='Umid. Prev. (%)').round(1)
        fc_df.index.name = "Passo Futuro"
        story.append(_df_to_pdf_table(fc_df.reset_index(), styles=styles))
        if alertas_fc:
            story.append(Paragraph("Alertas Forecast:", styles['Normal']))
            for al in alertas_fc: story.append(Paragraph(f"- {al}", styles['Alert_Red']))
    else: story.append(Paragraph("N/A.", styles['Normal']))
    _add_empty_lines(story); story.append(PageBreak())
    
    story.append(Paragraph("Análise de Custo", styles['H2_Custom']))
    story.append(Paragraph(f"Ciclos Irrigação: {ciclos_irr}", styles['Normal']))
    story.append(Paragraph(f"Custo Total Estimado: R$ {custo_total:.2f}", styles['Normal']))
    _add_empty_lines(story)

    story.append(Paragraph("Modelo ML (Risco Emergência)", styles['H2_Custom']))
    if modelo_ml and hasattr(modelo_ml, 'last_accuracy_'):
        story.append(Paragraph(f"Acurácia Teste: {modelo_ml.last_accuracy_*100:.1f}%", styles['Normal']))
        if hasattr(modelo_ml, 'feature_importances_') and hasattr(modelo_ml, 'feature_names_in_'):
            fi = pd.DataFrame({'Feature':modelo_ml.feature_names_in_, 'Importance':modelo_ml.feature_importances_})
            fi = fi.sort_values(by='Importance',ascending=False).round(3)
            story.append(Paragraph("Importância Features:", styles['Normal'])); story.append(_df_to_pdf_table(fi, styles=styles))
    else: story.append(Paragraph("Modelo não treinado/info N/A.", styles['Normal']))
    _add_empty_lines(story)

    story.append(Paragraph("Conclusões", styles['H2_Custom']))
    story.append(Paragraph("Análise preliminar. Monitoramento contínuo recomendado.", styles['Normal']))
    
    try: doc.build(story); console_rich.print(f"[green]Relatório PDF '{fname}' gerado![/]")
    except Exception as e: console_rich.print(f"[red]Erro ao gerar PDF: {e}[/]"); logger.error(f"Erro PDF: {e}", exc_info=True)

# --- Main CLI ---
def run_farmtech_phd_suite():
    """Função principal que executa o sistema completo FarmTech PhD."""
    console = RichConsole()
    console.print(Panel(Text("Bem-vindo ao FarmTech PhD Suite!", justify="center"),
                        title="[bold dark_spring_green]FarmTech Solutions[/]",
                        border_style="bold green", expand=False, padding=(1,2)))
    logger.info("Inicializando sistema...")
    criar_tabelas_se_nao_existirem()
    if dados_coletados_fase3: popular_dados_iniciais_phd(dados_coletados_fase3)
    else: console.print("[yellow]Aviso: 'dados_para_banco.py' não encontrado ou vazio.[/]")

    global clf_modelo_global; clf_modelo_global = None
    cache_analises = {"stats": None, "anomalias": None, "correl": None, "forecast": None, 
                      "alertas_fc": [], "ciclos_irr": 0, "custo_total": 0.0}

    while True:
        df_atual = carregar_dados_para_pandas()
        console.print(Padding(Text("\nEscolha uma Ação:", style="bold white on navy_blue"), (1,0,0,0)))
        menu = {"1": "Visualizar Leituras", "2": "Adicionar Leitura", "3": "Atualizar Leitura",
                "4": "Deletar Leitura", "5": "Executar Suite de Análises",
                "6": "[ML] Treinar Classificador", "7": "[Stats] Forecast Umidade",
                "8": "[Sim] Simulador 'What-If'", "9": "[Eco] Análise de Custo",
                "10": "[Doc] Gerar Relatório PDF", "0": "Sair"}
        tbl_menu = RichTable(show_header=False, box=None); tbl_menu.add_column("Opt", style="bold yellow", width=5); tbl_menu.add_column("Desc")
        for k,v in menu.items(): tbl_menu.add_row(f"[{k}]",v)
        console.print(tbl_menu)
        
        try:
            esc = Prompt.ask("Opção", choices=menu.keys(), default="0")
            if esc == '1': visualizar_leituras_phd(console)
            elif esc == '2': adicionar_leitura_interativo_phd(console)
            elif esc == '3': atualizar_leitura_interativo_phd(console)
            elif esc == '4': deletar_leitura_interativo_phd(console)
            elif esc == '5':
                if df_atual.empty: console.print("[yellow]Sem dados para análises.[/]"); continue
                console.print(Panel("[bold]Executando Suite Analítica...[/]", expand=False))
                cache_analises["stats"] = executar_estatisticas_descritivas_phd(df_atual, console)
                cache_analises["anomalias"] = executar_deteccao_anomalias_phd(df_atual, console)
                cache_analises["correl"] = executar_correlacoes_phd(df_atual, console)
                if len(df_atual) >= 10: _,_,_,_ = treinar_ou_carregar_classificador_phd(df_atual, console, config['ml_classifier'])
                else: console.print("[yellow]Dados insuficientes para treinar ML na suite.[/]")
                cache_analises["forecast"], cache_analises["alertas_fc"] = executar_forecast_umidade_phd(
                    df_atual, console, config['forecast_settings'], config['logica_esp32']['UMIDADE_CRITICA_BAIXA'])
                cache_analises["ciclos_irr"], cache_analises["custo_total"], _, _ = executar_analise_custo_detalhada(
                    df_atual, config['custo_settings'], console)
                if plotext_module: exibir_grafico_umidade_plotext_phd(df_atual, console)
                console.print("\n[green]Suite de análises concluída! Resultados cacheados.[/]")
            elif esc == '6':
                if df_atual.empty or len(df_atual) < 10: console.print("[yellow]Sem dados suficientes para treinar ML.[/]")
                else: _,_,_,_ = treinar_ou_carregar_classificador_phd(df_atual, console, config['ml_classifier'])
            elif esc == '7':
                if df_atual.empty: console.print("[yellow]Sem dados para forecast.[/]")
                else: cache_analises["forecast"], cache_analises["alertas_fc"] = executar_forecast_umidade_phd(
                    df_atual, console, config['forecast_settings'], config['logica_esp32']['UMIDADE_CRITICA_BAIXA'])
            elif esc == '8': executar_simulador_what_if(console, clf_modelo_global, config['logica_esp32'])
            elif esc == '9':
                if df_atual.empty: console.print("[yellow]Sem dados para análise de custo.[/]")
                else: cache_analises["ciclos_irr"], cache_analises["custo_total"], _, _ = executar_analise_custo_detalhada(
                    df_atual, config['custo_settings'], console)
            elif esc == '10':
                if df_atual.empty: console.print("[yellow]Sem dados para relatório.[/]"); continue
                console.print(Panel("[bold]Gerando Relatório PDF...[/]", expand=False))
                # Garante análises para o PDF se não executadas antes
                temp_console = RichConsole(file=io.StringIO()) # Suprime output para console
                if cache_analises["stats"] is None: cache_analises["stats"] = executar_estatisticas_descritivas_phd(df_atual, temp_console)
                if cache_analises["anomalias"] is None: cache_analises["anomalias"] = executar_deteccao_anomalias_phd(df_atual, temp_console)
                if cache_analises["correl"] is None: cache_analises["correl"] = executar_correlacoes_phd(df_atual, temp_console)
                if cache_analises["forecast"] is None: cache_analises["forecast"], cache_analises["alertas_fc"] = executar_forecast_umidade_phd(
                    df_atual, temp_console, config['forecast_settings'], config['logica_esp32']['UMIDADE_CRITICA_BAIXA'])
                if cache_analises["custo_total"] == 0.0 and cache_analises["ciclos_irr"] == 0: # Recalcular se não foi feito
                     cache_analises["ciclos_irr"], cache_analises["custo_total"], _, _ = executar_analise_custo_detalhada(
                        df_atual, config['custo_settings'], temp_console)
                if clf_modelo_global is None and len(df_atual) >=10 :
                     _,_,_,_ = treinar_ou_carregar_classificador_phd(df_atual, temp_console, config['ml_classifier'])
                
                gerar_relatorio_farmtech_pdf_phd(df_atual, cache_analises["stats"], cache_analises["correl"],
                    cache_analises["forecast"], cache_analises["alertas_fc"], cache_analises["ciclos_irr"],
                    cache_analises["custo_total"], clf_modelo_global, cache_analises["anomalias"], console)
            elif esc == '0':
                console.print(Panel("[bold bright_magenta]Encerrando FarmTech. Obrigado![/]", expand=False, border_style="magenta")); break
            
            # Limpar a entrada ao retornar ao menu
            if esc != '0':
                _ = input("\nPressione Enter para menu...")
                
        except Exception as e_menu:
            logger.critical(f"Erro no menu: {e_menu}", exc_info=True)
            console.print(f"[bold red]\nERRO NO MENU: {e_menu}. Ver logs. Enter para continuar ou Ctrl+C.[/]")
            input()

if __name__ == '__main__':
    try:
        if sys.stdout.encoding is None or sys.stdout.encoding.lower() != 'utf-8':
            logger.warning(
                f"O encoding da saída padrão (stdout) é {sys.stdout.encoding}, que não é 'utf-8'. "
                "A biblioteca Rich pode ter problemas na exibição de alguns caracteres ou elementos gráficos."
            )
    except Exception as e_enc:
        logger.warning(f"Não foi possível verificar o encoding do stdout: {e_enc}")
        pass

    run_farmtech_phd_suite()