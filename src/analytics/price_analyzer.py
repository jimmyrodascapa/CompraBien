"""Análisis de precios y detección de ofertas."""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass

from src.database.repository import PriceHistoryRepository, ProductRepository
from src.config.settings import ANALYTICS_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PriceAlert:
    """Alerta de cambio de precio."""
    product_id: int
    product_name: str
    old_price: float
    new_price: float
    discount_percentage: float
    is_real_offer: bool
    alert_type: str  # "price_drop", "fake_offer", "back_to_normal"
    message: str


class PriceAnalyzer:
    """Analizador de precios e historial."""
    
    def __init__(self):
        self.price_repo = PriceHistoryRepository()
        self.product_repo = ProductRepository()
        self.logger = get_logger(__name__)
    
    def detect_price_drops(self, min_discount: float = None) -> List[PriceAlert]:
        """Detectar productos con bajada de precio significativa."""
        if min_discount is None:
            min_discount = ANALYTICS_CONFIG.min_discount_percentage
        
        alerts = []
        products = self.product_repo.get_all_products()
        
        for product in products:
            alert = self._analyze_product_price(product['id'], min_discount)
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def _analyze_product_price(
        self, 
        product_id: int, 
        min_discount: float
    ) -> Optional[PriceAlert]:
        """Analizar precio de un producto específico."""
        # Obtener historial reciente
        history = self.price_repo.get_price_history(
            product_id, 
            days=ANALYTICS_CONFIG.min_price_history_days
        )
        
        if len(history) < 2:
            return None
        
        current_price = history[0]
        previous_price = history[1]
        
        # Calcular descuento
        price_diff = previous_price['price'] - current_price['price']
        discount_pct = (price_diff / previous_price['price']) * 100
        
        if discount_pct < min_discount:
            return None
        
        # Verificar si es oferta real o falsa
        is_real = self._is_real_offer(history, current_price)
        
        product = self.product_repo.get_product_by_id(product_id)
        
        alert_type = "price_drop" if is_real else "fake_offer"
        message = self._generate_alert_message(
            product['name'], 
            previous_price['price'],
            current_price['price'],
            discount_pct,
            is_real
        )
        
        return PriceAlert(
            product_id=product_id,
            product_name=product['name'],
            old_price=previous_price['price'],
            new_price=current_price['price'],
            discount_percentage=round(discount_pct, 2),
            is_real_offer=is_real,
            alert_type=alert_type,
            message=message
        )
    
    def _is_real_offer(self, history: List[dict], current_price: dict) -> bool:
        """Determinar si una oferta es real o falsa."""
        if len(history) < 3:
            return True  # No hay suficiente historial
        
        # Obtener precio promedio de los últimos 30 días (excluyendo actual)
        avg_price = sum(h['price'] for h in history[1:]) / len(history[1:])
        
        # Si el precio "anterior" es mucho mayor al promedio histórico,
        # probablemente es una oferta falsa
        if current_price.get('original_price'):
            original = current_price['original_price']
            inflation_threshold = ANALYTICS_CONFIG.price_inflation_threshold
            
            if original > avg_price * (1 + inflation_threshold / 100):
                self.logger.warning(
                    f"Possible fake offer detected. "
                    f"Original: {original}, Avg: {avg_price}"
                )
                return False
        
        # Verificar si el precio actual está cerca del precio histórico promedio
        # Una bajada real debería estar significativamente por debajo del promedio
        if current_price['price'] > avg_price * 0.95:
            return False
        
        return True
    
    def _generate_alert_message(
        self, 
        product_name: str,
        old_price: float,
        new_price: float,
        discount: float,
        is_real: bool
    ) -> str:
        """Generar mensaje de alerta."""
        status = "✅ OFERTA REAL" if is_real else "⚠️ POSIBLE OFERTA FALSA"
        
        return (
            f"{status}\n"
            f"Producto: {product_name}\n"
            f"Precio anterior: S/ {old_price:.2f}\n"
            f"Precio actual: S/ {new_price:.2f}\n"
            f"Descuento: {discount:.1f}%"
        )
    
    def get_best_deals(self, limit: int = 10) -> List[Dict]:
        """Obtener las mejores ofertas actuales."""
        alerts = self.detect_price_drops(min_discount=15.0)
        
        # Filtrar solo ofertas reales
        real_deals = [a for a in alerts if a.is_real_offer]
        
        # Ordenar por descuento
        real_deals.sort(key=lambda x: x.discount_percentage, reverse=True)
        
        return [
            {
                "product_name": deal.product_name,
                "old_price": deal.old_price,
                "new_price": deal.new_price,
                "discount": deal.discount_percentage,
                "savings": deal.old_price - deal.new_price
            }
            for deal in real_deals[:limit]
        ]
    
    def get_price_trend(self, product_id: int, days: int = 30) -> Dict:
        """Obtener tendencia de precio."""
        history = self.price_repo.get_price_history(product_id, days)
        
        if not history:
            return {"trend": "unknown", "data": []}
        
        prices = [h['price'] for h in history]
        
        # Calcular tendencia simple
        if len(prices) >= 2:
            first_half_avg = sum(prices[len(prices)//2:]) / len(prices[len(prices)//2:])
            second_half_avg = sum(prices[:len(prices)//2]) / len(prices[:len(prices)//2])
            
            if second_half_avg < first_half_avg * 0.95:
                trend = "decreasing"
            elif second_half_avg > first_half_avg * 1.05:
                trend = "increasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "current_price": prices[0],
            "avg_price": sum(prices) / len(prices),
            "min_price": min(prices),
            "max_price": max(prices),
            "data": history
        }
