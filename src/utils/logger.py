"""Configuración centralizada de logging."""
import sys
from loguru import logger
from src.config.settings import LOG_DIR, LOG_LEVEL

# Remover handler por defecto
logger.remove()

# Console handler con colores
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True
)

# File handler con rotación
logger.add(
    LOG_DIR / "scraper_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="00:00",  # Nueva archivo cada día
    retention="30 days",  # Mantener 30 días
    compression="zip",  # Comprimir logs antiguos
    enqueue=True  # Thread-safe
)

# Error handler separado
logger.add(
    LOG_DIR / "errors_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="00:00",
    retention="90 days",
    compression="zip",
    backtrace=True,
    diagnose=True
)


def get_logger(name: str):
    """Obtener logger con contexto específico."""
    return logger.bind(name=name)
