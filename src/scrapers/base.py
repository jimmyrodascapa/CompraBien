"""Scraper base abstracto - Strategy Pattern."""
from abc import ABC, abstractmethod
from typing import List, Optional
import time
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.product import Product, PriceHistory, ScrapingResult
from src.database.repository import ProductRepository, PriceHistoryRepository
from src.scrapers.anti_bot.headers import HeaderRotator, RateLimiter
from src.config.settings import SCRAPER_CONFIG
from src.utils.logger import get_logger


class BaseScraper(ABC):
    """Clase base para todos los scrapers."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.header_rotator = HeaderRotator()
        self.rate_limiter = RateLimiter(SCRAPER_CONFIG.requests_per_minute)
        self.product_repo = ProductRepository()
        self.price_repo = PriceHistoryRepository()
        
        self.stats = {
            "products_found": 0,
            "products_saved": 0,
            "errors": 0,
            "error_messages": []
        }
    
    @property
    @abstractmethod
    def store_name(self) -> str:
        """Nombre de la tienda."""
        pass
    
    @abstractmethod
    def search_products(self, query: str, max_pages: int = 3):
        """
        Buscar productos por query.
        
        Puede retornar:
        - List[Product]: Lista de productos (formato antiguo)
        - List[Tuple[Product, Optional[PriceHistory]]]: Productos con precios (nuevo formato)
        """
        pass
    
    @abstractmethod
    def get_product_details(self, product_url: str) -> Optional[Product]:
        """Obtener detalles de un producto específico."""
        pass
    
    @abstractmethod
    def extract_price(self, product_data: dict) -> Optional[PriceHistory]:
        """Extraer información de precio. Retorna None si no se encuentra precio."""
        pass
    
    @retry(
        stop=stop_after_attempt(SCRAPER_CONFIG.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def safe_request(self, url: str, **kwargs) -> any:
        """Request con retry y rate limiting."""
        self.rate_limiter.wait_if_needed()
        # Implementar en subclases
        raise NotImplementedError
    
    def save_product_with_price(self, product: Product, price_history: Optional[PriceHistory]) -> bool:
        """Guardar producto y su precio."""
        try:
            # Si no hay precio, no guardamos nada
            if price_history is None:
                self.logger.warning(f"No price found for {product.name}, skipping")
                return False
            
            # Guardar/actualizar producto
            product_id = self.product_repo.upsert_product(product)
            
            # Verificar si el precio cambió antes de guardar
            latest_price = self.price_repo.get_latest_price(product_id)
            
            should_save_price = True
            if latest_price:
                # Solo guardar si el precio cambió significativamente (>0.1%)
                price_diff = abs(float(price_history.price) - latest_price['price'])
                if price_diff / latest_price['price'] < 0.001:
                    should_save_price = False
                    self.logger.debug(f"Price unchanged for {product.name}")
            
            if should_save_price:
                # Crear nuevo PriceHistory con el product_id correcto
                new_price_history = PriceHistory(
                    product_id=product_id,
                    price=price_history.price,
                    currency=price_history.currency
                )
                self.price_repo.add_price_entry(new_price_history)
                self.logger.info(f"Saved: {product.name} - {price_history.currency} {price_history.price}")
            
            self.stats["products_saved"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving product {product.name}: {e}")
            self.stats["errors"] += 1
            self.stats["error_messages"].append(str(e))
            return False
    
    def run_scraping(self, queries: List[str], max_pages: int = 3) -> ScrapingResult:
        """Ejecutar scraping completo."""
        start_time = time.time()
        self.logger.info(f"Starting scraping for {self.store_name}")
        
        for query in queries:
            try:
                self.logger.info(f"Searching: {query}")
                results = self.search_products(query, max_pages)
                
                if not results:
                    self.logger.warning(f"No results for query: {query}")
                    continue
                
                # Detectar el formato de retorno
                first_item = results[0]
                
                if isinstance(first_item, tuple) and len(first_item) == 2:
                    # Nuevo formato: lista de tuplas (Product, Optional[PriceHistory])
                    self.logger.debug("Processing results in tuple format (Product, PriceHistory)")
                    self.stats["products_found"] += len(results)
                    
                    for product, price_history in results:
                        try:
                            self.save_product_with_price(product, price_history)
                        except Exception as e:
                            self.logger.error(f"Error processing product: {e}")
                            self.stats["errors"] += 1
                            self.stats["error_messages"].append(str(e))
                else:
                    # Formato antiguo: lista de Product
                    self.logger.debug("Processing results in Product format")
                    self.stats["products_found"] += len(results)
                    
                    for product in results:
                        try:
                            # Extraer precio (retorna Optional[PriceHistory])
                            price_history = self.extract_price(product.model_dump())
                            
                            # Guardar
                            self.save_product_with_price(product, price_history)
                            
                        except Exception as e:
                            self.logger.error(f"Error processing product: {e}")
                            self.stats["errors"] += 1
                            self.stats["error_messages"].append(str(e))
                        
            except Exception as e:
                self.logger.error(f"Error searching '{query}': {e}")
                self.stats["errors"] += 1
                self.stats["error_messages"].append(f"Query '{query}': {str(e)}")
        
        duration = time.time() - start_time
        
        result = ScrapingResult(
            store_name=self.store_name,
            products_found=self.stats["products_found"],
            products_saved=self.stats["products_saved"],
            errors=self.stats["errors"],
            duration_seconds=round(duration, 2),
            error_messages=self.stats["error_messages"]
        )
        
        self.logger.info(f"Scraping completed: {result.model_dump()}")
        return result