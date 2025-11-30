"""Manejo de conexiones y esquema de base de datos."""
import sqlite3
from contextlib import contextmanager
from typing import Generator
from src.config.settings import DATABASE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Gestor de base de datos SQLite."""
    
    def __init__(self):
        self.db_path = DATABASE_CONFIG.db_path
        self._initialize_schema()
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager para conexiones."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Acceder por nombre de columna
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _initialize_schema(self):
        """Crear tablas si no existen."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de productos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_name TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    sku TEXT,
                    name TEXT NOT NULL,
                    brand TEXT,
                    category TEXT,
                    url TEXT NOT NULL,
                    image_url TEXT,
                    in_stock BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(store_name, product_id)
                )
            """)
            
            # Tabla de historial de precios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    original_price REAL,
                    discount_percentage REAL,
                    currency TEXT DEFAULT 'PEN',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_promotion BOOLEAN DEFAULT 0,
                    promotion_label TEXT,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
            
            # Tabla de logs de scraping
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraping_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_name TEXT NOT NULL,
                    products_found INTEGER,
                    products_saved INTEGER,
                    errors INTEGER,
                    duration_seconds REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_messages TEXT
                )
            """)
            
            # Índices para mejorar performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_store 
                ON products(store_name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_product 
                ON price_history(product_id, timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_timestamp 
                ON price_history(timestamp DESC)
            """)
            
            logger.info("Database schema initialized successfully")


# Singleton instance
db = Database()
