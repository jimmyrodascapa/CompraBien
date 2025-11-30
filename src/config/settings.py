"""Configuración global del sistema."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "database.db"

# Crear directorios si no existen
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


@dataclass
class ScraperConfig:
    """Configuración para scrapers."""
    
    # Rate limiting
    requests_per_minute: int = 30
    delay_between_requests: float = 2.0
    max_retries: int = 3
    retry_delay: int = 5
    
    # Timeouts
    request_timeout: int = 30
    page_load_timeout: int = 60
    
    # Headers rotation
    rotate_user_agent: bool = True
    rotate_headers: bool = True
    
    # Anti-bot
    use_proxies: bool = False
    proxy_list: list = None
    
    # Scraping behavior
    respect_robots_txt: bool = True
    max_concurrent_requests: int = 5


@dataclass
class DatabaseConfig:
    """Configuración de base de datos."""
    
    db_path: str = str(DB_PATH)
    echo_sql: bool = False
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class SchedulerConfig:
    """Configuración del scheduler."""
    
    scraping_interval_hours: int = 6
    cleanup_old_data_days: int = 90
    timezone: str = "America/Lima"
    max_instances: int = 1  # Evitar ejecuciones simultáneas


@dataclass
class AnalyticsConfig:
    """Configuración para análisis de precios."""
    
    # Detección de ofertas
    min_discount_percentage: float = 10.0
    min_price_history_days: int = 7
    
    # Detección de ofertas falsas
    fake_offer_threshold_hours: int = 48
    price_inflation_threshold: float = 20.0
    
    # Alertas
    alert_on_price_drop: bool = True
    min_alert_discount: float = 25.0


# Instancias globales
SCRAPER_CONFIG = ScraperConfig()
DATABASE_CONFIG = DatabaseConfig()
SCHEDULER_CONFIG = SchedulerConfig()
ANALYTICS_CONFIG = AnalyticsConfig()


# Environment variables
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
