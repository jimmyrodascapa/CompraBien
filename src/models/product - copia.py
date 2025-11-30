"""Modelos de datos para productos y precios."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Product(BaseModel):
    """Modelo de producto."""
    
    id: Optional[int] = None
    store_name: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    sku: Optional[str] = None
    name: str = Field(..., min_length=1)
    brand: Optional[str] = None
    category: Optional[str] = None
    url: HttpUrl
    image_url: Optional[HttpUrl] = None
    in_stock: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('name')
    @classmethod
    def clean_name(cls, v: str) -> str:
        """Limpiar nombre del producto."""
        return ' '.join(v.split())
    
    class Config:
        json_schema_extra = {
            "example": {
                "store_name": "falabella",
                "product_id": "881974817",
                "name": "Notebook HP Pavilion 15",
                "brand": "HP",
                "category": "Tecnología",
                "url": "https://falabella.com.pe/...",
                "in_stock": True
            }
        }


class PriceHistory(BaseModel):
    """Modelo de historial de precios."""
    
    id: Optional[int] = None
    product_id: int
    price: Decimal = Field(..., gt=0)
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    currency: str = Field(default="PEN")
    timestamp: datetime = Field(default_factory=datetime.now)
    is_promotion: bool = False
    promotion_label: Optional[str] = None
    
    @field_validator('discount_percentage', mode='before')
    @classmethod
    def calculate_discount(cls, v, info):
        """Calcular descuento si no se proporciona."""
        if v is None and info.data.get('original_price'):
            original = float(info.data['original_price'])
            current = float(info.data['price'])
            if original > current:
                return round(((original - current) / original) * 100, 2)
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": 1,
                "price": 2499.00,
                "original_price": 3499.00,
                "discount_percentage": 28.58,
                "currency": "PEN",
                "is_promotion": True
            }
        }


class ScrapingResult(BaseModel):
    """Resultado de un scraping."""
    
    store_name: str
    products_found: int
    products_saved: int
    errors: int
    duration_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)
    error_messages: list[str] = Field(default_factory=list)
