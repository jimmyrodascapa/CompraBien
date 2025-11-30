"""Repository pattern para acceso a base de datos CON LOCKS."""
from typing import List, Optional, Dict
from datetime import datetime

from src.models.product import Product, PriceHistory
from src.database.connection import get_db_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProductRepository:
    """Repository para operaciones de productos."""
    
    def upsert_product(self, product: Product) -> int:
        """
        Insertar o actualizar producto.
        Retorna el ID del producto en la DB.
        """
        with get_db_connection(write_mode=True) as conn:
            cursor = conn.cursor()
            
            # Verificar si existe
            cursor.execute('''
                SELECT id FROM products 
                WHERE store_name = ? AND product_id = ?
            ''', (product.store_name, product.product_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Actualizar
                product_id = existing['id']
                cursor.execute('''
                    UPDATE products SET
                        name = ?,
                        brand = ?,
                        category = ?,
                        subcategory = ?,
                        sub_subcategory = ?,
                        url = ?,
                        image_url = ?,
                        in_stock = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    product.name,
                    product.brand,
                    product.category,
                    product.subcategory,
                    product.sub_subcategory,
                    str(product.url),
                    product.image_url,
                    product.in_stock,
                    product_id
                ))
            else:
                # Insertar
                cursor.execute('''
                    INSERT INTO products (
                        store_name, product_id, name, brand,
                        category, subcategory, sub_subcategory,
                        url, image_url, in_stock
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product.store_name,
                    product.product_id,
                    product.name,
                    product.brand,
                    product.category,
                    product.subcategory,
                    product.sub_subcategory,
                    str(product.url),
                    product.image_url,
                    product.in_stock
                ))
                product_id = cursor.lastrowid
            
            conn.commit()
            return product_id
    
    def get_product(self, store_name: str, product_id: str) -> Optional[Product]:
        """Obtener producto por tienda y ID."""
        with get_db_connection() as conn:  # Solo lectura, sin lock
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products 
                WHERE store_name = ? AND product_id = ?
            ''', (store_name, product_id))
            
            row = cursor.fetchone()
            if row:
                return Product(**dict(row))
            return None
    
    def get_all_products(self, limit: int = 100) -> List[Product]:
        """Obtener todos los productos."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products 
                ORDER BY updated_at DESC 
                LIMIT ?
            ''', (limit,))
            
            return [Product(**dict(row)) for row in cursor.fetchall()]
    
    def search_products(self, query: str) -> List[Product]:
        """Buscar productos por nombre o marca."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products 
                WHERE name LIKE ? OR brand LIKE ?
                ORDER BY updated_at DESC
            ''', (f'%{query}%', f'%{query}%'))
            
            return [Product(**dict(row)) for row in cursor.fetchall()]
    
    def get_products_by_category(
        self, 
        category: Optional[str] = None,
        subcategory: Optional[str] = None
    ) -> List[Product]:
        """Obtener productos por categoría."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if category and subcategory:
                cursor.execute('''
                    SELECT * FROM products 
                    WHERE category = ? AND subcategory = ?
                    ORDER BY name
                ''', (category, subcategory))
            elif category:
                cursor.execute('''
                    SELECT * FROM products 
                    WHERE category = ?
                    ORDER BY name
                ''', (category,))
            else:
                cursor.execute('SELECT * FROM products ORDER BY name')
            
            return [Product(**dict(row)) for row in cursor.fetchall()]


class PriceHistoryRepository:
    """Repository para historial de precios."""
    
    def add_price_entry(self, price_history: PriceHistory) -> int:
        """Agregar entrada de precio."""
        with get_db_connection(write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO price_history (product_id, price, currency)
                VALUES (?, ?, ?)
            ''', (
                price_history.product_id,
                float(price_history.price),
                price_history.currency
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_latest_price(self, product_id: int) -> Optional[Dict]:
        """Obtener el precio más reciente de un producto."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT price, currency, scraped_at
                FROM price_history
                WHERE product_id = ?
                ORDER BY scraped_at DESC
                LIMIT 1
            ''', (product_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_price_history(
        self, 
        product_id: int, 
        limit: int = 30
    ) -> List[PriceHistory]:
        """Obtener historial de precios de un producto."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM price_history
                WHERE product_id = ?
                ORDER BY scraped_at DESC
                LIMIT ?
            ''', (product_id, limit))
            
            return [PriceHistory(**dict(row)) for row in cursor.fetchall()]
    
    def get_products_with_price_changes(
        self, 
        hours: int = 24
    ) -> List[Dict]:
        """Obtener productos con cambios de precio en las últimas N horas."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    p.id,
                    p.name,
                    p.brand,
                    p.url,
                    ph1.price as current_price,
                    ph2.price as previous_price,
                    (ph1.price - ph2.price) as price_change,
                    ph1.scraped_at as last_update
                FROM products p
                INNER JOIN price_history ph1 ON p.id = ph1.product_id
                INNER JOIN price_history ph2 ON p.id = ph2.product_id
                WHERE ph1.scraped_at >= datetime('now', '-' || ? || ' hours')
                AND ph2.scraped_at < ph1.scraped_at
                AND ph1.price != ph2.price
                ORDER BY abs(ph1.price - ph2.price) DESC
            ''', (hours,))
            
            return [dict(row) for row in cursor.fetchall()]


class StatsRepository:
    """Repository para estadísticas."""
    
    def get_general_stats(self) -> Dict:
        """Obtener estadísticas generales."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total de productos
            cursor.execute('SELECT COUNT(*) as count FROM products')
            stats['total_products'] = cursor.fetchone()['count']
            
            # Productos por tienda
            cursor.execute('''
                SELECT store_name, COUNT(*) as count 
                FROM products 
                GROUP BY store_name
            ''')
            stats['products_by_store'] = [dict(row) for row in cursor.fetchall()]
            
            # Productos por marca
            cursor.execute('''
                SELECT brand, COUNT(*) as count 
                FROM products 
                WHERE brand IS NOT NULL
                GROUP BY brand 
                ORDER BY count DESC
                LIMIT 10
            ''')
            stats['top_brands'] = [dict(row) for row in cursor.fetchall()]
            
            # Productos por categoría
            cursor.execute('''
                SELECT category, subcategory, COUNT(*) as count 
                FROM products 
                WHERE category IS NOT NULL
                GROUP BY category, subcategory
                ORDER BY count DESC
                LIMIT 10
            ''')
            stats['products_by_category'] = [dict(row) for row in cursor.fetchall()]
            
            # Total de registros de precio
            cursor.execute('SELECT COUNT(*) as count FROM price_history')
            stats['total_price_records'] = cursor.fetchone()['count']
            
            return stats