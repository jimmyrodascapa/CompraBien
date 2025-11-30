"""Models para productos y precios - CON CATEGORÍAS."""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from decimal import Decimal


class Product(BaseModel):
    """Modelo de producto con categorías."""
    
    id: Optional[int] = None
    store_name: str
    product_id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    sub_subcategory: Optional[str] = None
    url: HttpUrl
    image_url: Optional[str] = None
    in_stock: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PriceHistory(BaseModel):
    """Modelo de historial de precios."""
    
    id: Optional[int] = None
    product_id: int
    price: Decimal = Field(gt=0)  # Precio debe ser mayor que 0
    currency: str = "PEN"
    scraped_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ScrapingResult(BaseModel):
    """Resultado de una sesión de scraping."""
    
    store_name: str
    products_found: int
    products_saved: int
    errors: int
    duration_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)
    error_messages: list[str] = []
    
    class Config:
        from_attributes = True