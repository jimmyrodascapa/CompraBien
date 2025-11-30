"""Database connection with improved locking handling."""
import sqlite3
from contextlib import contextmanager
from typing import Optional
import threading

from src.config.settings import DATABASE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Thread lock global para prevenir escrituras concurrentes
_db_write_lock = threading.RLock()


class DatabaseConnection:
    """Singleton para manejar la conexión a SQLite."""
    
    _instance: Optional['DatabaseConnection'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = DATABASE_CONFIG.db_path
            self.initialized = True
            self._initialize_schema()
    
    @contextmanager
    def get_connection(self, write_mode: bool = False):
        """
        Context manager para obtener conexión con timeout mejorado.
        
        Args:
            write_mode: Si True, usa lock para operaciones de escritura
        """
        conn = None
        lock_acquired = False
        
        try:
            # Adquirir lock solo para operaciones de escritura
            if write_mode:
                _db_write_lock.acquire()
                lock_acquired = True
            
            # Aumentar timeout a 30 segundos
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,  # 30 segundos de timeout
                check_same_thread=False,  # Permitir uso multi-thread
                isolation_level='DEFERRED'  # Mejor para concurrencia
            )
            
            # Configurar pragmas para mejor rendimiento y concurrencia
            conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
            conn.execute('PRAGMA busy_timeout=30000')  # 30 segundos
            conn.execute('PRAGMA synchronous=NORMAL')  # Balance performance/seguridad
            
            conn.row_factory = sqlite3.Row
            
            yield conn
            
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
            
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            
            # Liberar lock si fue adquirido
            if lock_acquired:
                _db_write_lock.release()
    
    def _initialize_schema(self):
        """Inicializar esquema de base de datos."""
        with self.get_connection(write_mode=True) as conn:
            cursor = conn.cursor()
            
            # Tabla de productos con categorías
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_name TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    brand TEXT,
                    category TEXT,
                    subcategory TEXT,
                    sub_subcategory TEXT,
                    url TEXT,
                    image_url TEXT,
                    in_stock BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(store_name, product_id)
                )
            ''')
            
            # Tabla de historial de precios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    currency TEXT DEFAULT 'PEN',
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            ''')
            
            # Índices para mejorar rendimiento
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_products_store_id 
                ON products(store_name, product_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_price_history_product 
                ON price_history(product_id, scraped_at DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_products_category 
                ON products(category, subcategory)
            ''')
            
            conn.commit()
            logger.info("Database schema initialized successfully")


# Singleton instance
db_connection = DatabaseConnection()


@contextmanager
def get_db_connection(write_mode: bool = False):
    """
    Helper function para obtener conexión de base de datos.
    
    Args:
        write_mode: True para operaciones de escritura (usa lock)
    
    Example:
        # Para lecturas
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products")
        
        # Para escrituras
        with get_db_connection(write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO products ...")
            conn.commit()
    """
    with db_connection.get_connection(write_mode=write_mode) as conn:
        yield conn