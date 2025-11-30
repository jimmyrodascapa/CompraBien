"""Repository para operaciones CRUD."""
from datetime import datetime, timedelta
from typing import Optional, List
from src.database.connection import db
from src.models.product import Product, PriceHistory
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProductRepository:
    """Repositorio para productos."""
    
    @staticmethod
    def upsert_product(product: Product) -> int:
        """Insertar o actualizar producto."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si existe
            cursor.execute(
                "SELECT id FROM products WHERE store_name = ? AND product_id = ?",
                (product.store_name, product.product_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Actualizar
                cursor.execute("""
                    UPDATE products 
                    SET name = ?, brand = ?, category = ?, url = ?, 
                        image_url = ?, in_stock = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    product.name, product.brand, product.category, 
                    str(product.url), str(product.image_url) if product.image_url else None,
                    product.in_stock, datetime.now(), existing['id']
                ))
                logger.debug(f"Updated product: {product.name}")
                return existing['id']
            else:
                # Insertar
                cursor.execute("""
                    INSERT INTO products 
                    (store_name, product_id, sku, name, brand, category, 
                     url, image_url, in_stock)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product.store_name, product.product_id, product.sku,
                    product.name, product.brand, product.category,
                    str(product.url), str(product.image_url) if product.image_url else None,
                    product.in_stock
                ))
                logger.debug(f"Inserted new product: {product.name}")
                return cursor.lastrowid
    
    @staticmethod
    def get_product_by_id(product_id: int) -> Optional[dict]:
        """Obtener producto por ID."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_all_products(store_name: Optional[str] = None) -> List[dict]:
        """Obtener todos los productos."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            if store_name:
                cursor.execute(
                    "SELECT * FROM products WHERE store_name = ? ORDER BY updated_at DESC",
                    (store_name,)
                )
            else:
                cursor.execute("SELECT * FROM products ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]


class PriceHistoryRepository:
    """Repositorio para historial de precios."""
    
    @staticmethod
    def add_price_entry(price_history: PriceHistory) -> int:
        """Agregar entrada de precio."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_history 
                (product_id, price, original_price, discount_percentage, 
                 currency, is_promotion, promotion_label)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                price_history.product_id, float(price_history.price),
                float(price_history.original_price) if price_history.original_price else None,
                price_history.discount_percentage, price_history.currency,
                price_history.is_promotion, price_history.promotion_label
            ))
            logger.debug(f"Added price entry for product {price_history.product_id}")
            return cursor.lastrowid
    
    @staticmethod
    def get_latest_price(product_id: int) -> Optional[dict]:
        """Obtener último precio registrado."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM price_history 
                WHERE product_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_price_history(product_id: int, days: int = 30) -> List[dict]:
        """Obtener historial de precios."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            since_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT * FROM price_history 
                WHERE product_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (product_id, since_date))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_avg_price(product_id: int, days: int = 30) -> Optional[float]:
        """Obtener precio promedio."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            since_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT AVG(price) as avg_price 
                FROM price_history 
                WHERE product_id = ? AND timestamp >= ?
            """, (product_id, since_date))
            result = cursor.fetchone()
            return result['avg_price'] if result and result['avg_price'] else None
