# 🛍️ Price Tracker - Agregador de Ofertas Local

Sistema de scraping y monitoreo de precios para e-commerce peruano, inspirado en knasta.pe. Versión 1.0 completamente local sin frontend.

## 🎯 Características

- ✅ Scraping automatizado de múltiples tiendas
- ✅ Detección inteligente de ofertas reales vs falsas
- ✅ Historial completo de precios
- ✅ Sistema anti-bot con rotación de headers
- ✅ Scheduler integrado para ejecución 24/7
- ✅ CLI intuitiva con Rich UI
- ✅ Base de datos SQLite local
- ✅ Arquitectura extensible para agregar nuevas tiendas

## 📦 Instalación

### Requisitos

- Python 3.10+
- pip

### Setup

```bash
# Clonar el proyecto
git clone <repo>
cd price-tracker

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar Playwright browsers (solo primera vez)
playwright install chromium

# Copiar configuración
cp .env.example .env

# Inicializar base de datos
python main.py init
```

## 🚀 Uso

### Scraping Manual

```bash
# Scraping simple
python main.py scrape

# Scraping con búsquedas específicas
python main.py scrape -q laptop -q smartphone -q tablet

# Scraping de tienda específica
python main.py scrape --store falabella -q "macbook air"

# Más páginas por búsqueda
python main.py scrape -q laptop --pages 5
```

### Modo Automático (24/7)

```bash
# Iniciar scheduler (ejecuta cada 6 horas por defecto)
python main.py schedule

# Personalizar intervalo
python main.py schedule --interval 4  # Cada 4 horas

# Con búsquedas específicas
python main.py schedule -q laptop -q smartphone -q televisor
```

**Mantener ejecutando 24/7:**

**Linux/Mac:**
```bash
# Con nohup
nohup python main.py schedule > scheduler.log 2>&1 &

# Con screen
screen -S price-tracker
python main.py schedule
# Ctrl+A D para detach
```

**Windows:**
```bash
# Crear un archivo run_scheduler.bat:
python main.py schedule
# Luego ejecutar como tarea programada en Windows Task Scheduler
```

### Ver Ofertas

```bash
# Top 10 ofertas
python main.py deals

# Top 20 con descuento mínimo 25%
python main.py deals --limit 20 --min-discount 25
```

### Listar Productos

```bash
python main.py list-products
```

### Ver Tiendas Disponibles

```bash
python main.py stores
```

## 📊 Estructura de Datos

### Base de Datos SQLite

**Tabla: products**
- Información general del producto
- SKU, marca, categoría
- Estado de stock

**Tabla: price_history**
- Historial completo de precios
- Precio original vs precio con descuento
- Etiquetas de promoción
- Timestamp de cada cambio

**Tabla: scraping_logs**
- Logs de cada ejecución
- Estadísticas de éxito/errores

## 🏗️ Arquitectura

```
Scrapers (Strategy Pattern)
    ↓
Factory (crea scrapers)
    ↓
Orchestrator (coordina scraping)
    ↓
Normalizer (limpia datos)
    ↓
Repository (guarda en DB)
    ↓
Analytics (detecta ofertas)
```

### Agregar Nueva Tienda

1. Crear nuevo scraper heredando de `BaseScraper`:

```python
# src/scrapers/ripley.py
from src.scrapers.base import BaseScraper

class RipleyScraper(BaseScraper):
    @property
    def store_name(self) -> str:
        return "ripley"
    
    def search_products(self, query: str, max_pages: int):
        # Implementar lógica de scraping
        pass
    
    def extract_price(self, product_data: dict):
        # Extraer precios
        pass
```

2. Registrar en factory:

```python
# src/scrapers/factory.py
from src.scrapers.ripley import RipleyScraper

class ScraperFactory:
    _scrapers = {
        "falabella": FalabellaScraper,
        "ripley": RipleyScraper,  # ← Agregar aquí
    }
```

¡Listo! La nueva tienda estará disponible automáticamente.

## 🔍 Detección de Ofertas

### Ofertas Reales

El sistema detecta ofertas reales comparando:

- Precio actual vs historial (30 días)
- Precio "original" vs promedio histórico
- Descuento mínimo configurable

### Ofertas Falsas

Detecta cuando:
- El precio "original" fue inflado recientemente
- El descuento es sobre un precio nunca visto
- El precio "oferta" está cerca del promedio histórico

## ⚙️ Configuración

Editar `src/config/settings.py` o `.env`:

```python
# Rate limiting
requests_per_minute: 30
delay_between_requests: 2.0

# Ofertas
min_discount_percentage: 10.0
min_price_history_days: 7

# Scheduler
scraping_interval_hours: 6
cleanup_old_data_days: 90
```

## 🛡️ Anti-Bot

- ✅ Rotación automática de User-Agents
- ✅ Headers realistas por país
- ✅ Rate limiting inteligente
- ✅ Delays aleatorios (jitter)
- ✅ Retry con backoff exponencial
- ✅ Respeto de robots.txt

## 📝 Logs

Logs ubicados en `data/logs/`:

- `scraper_YYYY-MM-DD.log` - Log general
- `errors_YYYY-MM-DD.log` - Solo errores

Rotación automática diaria con compresión.

## 🔧 Troubleshooting

### Error: "No module named 'playwright'"

```bash
pip install playwright
playwright install chromium
```

### Error: "Database is locked"

```bash
# Cerrar todas las conexiones activas
# O mover el archivo database.db temporalmente
```

### Pocos productos encontrados

- Aumentar `--pages` en el comando scrape
- Verificar que los selectores CSS no hayan cambiado
- Revisar logs en `data/logs/`

### Bloqueos por anti-bot

- Reducir `requests_per_minute` en settings
- Aumentar `delay_between_requests`
- Considerar usar proxies

## 🚀 Mejoras Futuras

### Corto Plazo
- [ ] Agregar Ripley scraper
- [ ] Agregar Plaza Vea scraper
- [ ] Sistema de notificaciones (email/Telegram)
- [ ] Exportar ofertas a CSV/Excel

### Mediano Plazo
- [ ] Dashboard web con Flask/FastAPI
- [ ] Gráficos de tendencia de precios
- [ ] Comparador de precios entre tiendas
- [ ] Alertas personalizadas por producto

### Largo Plazo
- [ ] API REST pública
- [ ] Machine Learning para predicción de precios
- [ ] Integración con Selenium para JS-heavy sites
- [ ] Sistema de proxies rotativo
- [ ] Multi-país (Chile, Colombia, etc.)

## 📄 Licencia

MIT License

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-tienda`)
3. Commit cambios (`git commit -m 'Agregar scraper de Ripley'`)
4. Push (`git push origin feature/nueva-tienda`)
5. Abre un Pull Request

## 📧 Contacto

Para preguntas o sugerencias, abre un Issue en GitHub.

---

**⚠️ Disclaimer:** Este proyecto es solo para fines educativos. Asegúrate de respetar los términos de servicio de cada sitio web.
