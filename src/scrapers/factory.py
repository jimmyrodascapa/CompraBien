"""Factory para crear scrapers - Factory Pattern."""
from typing import Dict, Type
from src.scrapers.base import BaseScraper
from src.scrapers.falabella import FalabellaScraper
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ScraperFactory:
    """Factory para instanciar scrapers."""
    
    _scrapers: Dict[str, Type[BaseScraper]] = {
        "falabella": FalabellaScraper,
        # Futuros scrapers:
        # "ripley": RipleyScraper,
        # "plazavea": PlazaVeaScraper,
    }
    
    @classmethod
    def create_scraper(cls, store_name: str) -> BaseScraper:
        """Crear scraper para una tienda específica."""
        scraper_class = cls._scrapers.get(store_name.lower())
        
        if not scraper_class:
            available = ", ".join(cls._scrapers.keys())
            raise ValueError(
                f"Scraper '{store_name}' not found. "
                f"Available scrapers: {available}"
            )
        
        logger.info(f"Creating scraper for: {store_name}")
        return scraper_class()
    
    @classmethod
    def get_available_stores(cls) -> list[str]:
        """Obtener lista de tiendas disponibles."""
        return list(cls._scrapers.keys())
    
    @classmethod
    def register_scraper(cls, store_name: str, scraper_class: Type[BaseScraper]):
        """Registrar un nuevo scraper dinámicamente."""
        cls._scrapers[store_name.lower()] = scraper_class
        logger.info(f"Registered new scraper: {store_name}")


# Convenience function
def get_scraper(store_name: str) -> BaseScraper:
    """Shortcut para obtener un scraper."""
    return ScraperFactory.create_scraper(store_name)
