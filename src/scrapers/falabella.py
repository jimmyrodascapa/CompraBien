"""Scraper para Falabella Perú - VERSIÓN OPTIMIZADA Y CORREGIDA."""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Tuple
from decimal import Decimal
import re
import time

from src.scrapers.base import BaseScraper
from src.models.product import Product, PriceHistory
from src.config.settings import SCRAPER_CONFIG


class FalabellaScraper(BaseScraper):
    """Scraper para Falabella usando Playwright."""
    
    BASE_URL = "https://www.falabella.com.pe"
    SEARCH_URL = f"{BASE_URL}/falabella-pe/search"
    
    @property
    def store_name(self) -> str:
        return "falabella"
    
    def safe_request(self, url: str, **kwargs) -> str:
        """Request usando Playwright."""
        self.rate_limiter.wait_if_needed()
        
        url_str = str(url)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            
            try:
                self.logger.info(f"Loading: {url_str[:100]}...")
                page.goto(url_str, wait_until='domcontentloaded', timeout=30000)
                
                time.sleep(2)
                
                # Scroll progresivo para cargar TODAS las lazy images
                for i in range(0, 10000, 1000):
                    page.evaluate(f'window.scrollTo(0, {i})')
                    time.sleep(0.5)
                
                # Scroll final al fondo
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(1)
                
                html_content = page.content()
                self.logger.info(f"HTML loaded: {len(html_content)} bytes")
                
            except Exception as e:
                self.logger.error(f"Error loading page: {e}")
                html_content = "<html></html>"
            finally:
                context.close()
                browser.close()
            
            return html_content
    
    def search_products(self, query: str, max_pages: int = 3) -> List[Tuple[Product, Optional[PriceHistory]]]:
        """Buscar productos en Falabella con sus precios."""
        products = []
        seen_ids_global = set()  # Control de duplicados entre páginas
        
        for page_num in range(1, max_pages + 1):
            try:
                self.logger.info(f"Scraping page {page_num} for '{query}'")
                
                url = f"{self.SEARCH_URL}?Ntt={query}"
                if page_num > 1:
                    url += f"&page={page_num}"
                
                html_content = self.safe_request(url)
                
                if page_num == 1:
                    with open('debug_scraper.html', 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    self.logger.info("Saved HTML to debug_scraper.html")
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extraer categorías de la página
                categories = self._extract_categories(soup)
                self.logger.info(f"Categories: {categories}")
                
                # Extraer productos CON PRECIOS desde la página de búsqueda
                page_products = self._extract_products_with_prices(soup, categories)
                
                if not page_products:
                    self.logger.warning(f"No products found on page {page_num}")
                    break
                
                # Filtrar duplicados entre páginas
                unique_products = []
                for product, price_history in page_products:
                    if product.product_id not in seen_ids_global:
                        unique_products.append((product, price_history))
                        seen_ids_global.add(product.product_id)
                    else:
                        self.logger.info(f"⚠️ Duplicate skipped (page {page_num}): {product.name[:50]}")
                
                products.extend(unique_products)
                self.logger.info(f"Found {len(unique_products)} unique products on page {page_num} ({len(page_products) - len(unique_products)} duplicates)")
                
                if page_num < max_pages:
                    time.sleep(2)  # Solo 2 segundos entre páginas
                
            except Exception as e:
                self.logger.error(f"Error scraping page {page_num}: {e}")
                break
        
        return products
    
    def _extract_categories(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extraer categorías del breadcrumb.
        Separa correctamente "Tecnología - Computadoras" en category y subcategory.
        """
        categories = {
            'category': None,
            'subcategory': None,
            'sub_subcategory': None
        }
        
        try:
            # Estrategia 1: Buscar breadcrumb con aria-label
            breadcrumb = soup.select_one('nav[aria-label*="breadcrumb"]')
            
            if not breadcrumb:
                # Estrategia 2: Buscar por clase
                breadcrumb = soup.select_one('.breadcrumb, [class*="breadcrumb"]')
            
            if breadcrumb:
                # Obtener todos los links del breadcrumb
                links = breadcrumb.select('a')
                texts = [link.get_text(strip=True) for link in links]
                
                # Filtrar "Inicio" y vacíos
                texts = [t for t in texts if t and t.lower() not in ['inicio', 'home', 'falabella']]
                
                self.logger.debug(f"Breadcrumb texts: {texts}")
                
                # Si hay textos, procesarlos
                if texts:
                    # Tomar el último (más específico)
                    main_text = texts[-1] if texts else None
                    
                    if main_text:
                        # Separar por " - " (común en Falabella)
                        parts = [p.strip() for p in main_text.split('-')]
                        
                        if len(parts) >= 1:
                            categories['category'] = parts[0]
                        if len(parts) >= 2:
                            categories['subcategory'] = parts[1]
                        if len(parts) >= 3:
                            categories['sub_subcategory'] = parts[2]
            
            # Estrategia 3: Si no hay breadcrumb, intentar inferir del título
            if not categories['category']:
                title = soup.select_one('h1, h2')
                if title:
                    title_text = title.get_text(strip=True).lower()
                    # Inferir categoría común
                    if 'laptop' in title_text or 'computadora' in title_text:
                        categories['category'] = 'Tecnología'
                        categories['subcategory'] = 'Computadoras'
                    elif 'smartphone' in title_text or 'celular' in title_text:
                        categories['category'] = 'Tecnología'
                        categories['subcategory'] = 'Smartphones'
        
        except Exception as e:
            self.logger.error(f"Error extracting categories: {e}")
        
        return categories
    
    def _extract_products_with_prices(
        self, 
        soup: BeautifulSoup, 
        categories: Dict[str, str]
    ) -> List[Tuple[Product, Optional[PriceHistory]]]:
        """
        Extraer productos CON PRECIOS desde la página de búsqueda.
        NO hace requests individuales - extrae todo de una vez.
        Retorna lista de tuplas (Product, PriceHistory).
        """
        products_with_prices = []
        seen_ids = set()
        
        # Selectores para productos
        selectors = [
            'div.grid-pod',
            'div[class*="pod"]',
            'article[data-test-id*="pod"]',
            'div[data-test-id*="pod"]',
        ]
        
        for selector in selectors:
            containers = soup.select(selector)
            self.logger.debug(f"Selector '{selector}': found {len(containers)} containers")
            
            for container in containers:
                try:
                    # FILTRO EFICIENTE: Buscar "Patrocinado" en el contenedor (ADs)
                    container_text = container.get_text()
                    if 'Patrocinado' in container_text or 'patrocinado' in container_text:
                        continue
                    
                    result = self._parse_product_with_price(container, categories)
                    if result:
                        product, price_history = result
                        
                        # Filtro 1: Sin precio (banners)
                        if not price_history or not price_history.price:
                            continue
                        
                        # Filtro 2: Precio fuera de rango
                        try:
                            price_val = float(price_history.price)
                            if price_val < 50 or price_val > 100000:
                                continue
                        except (ValueError, TypeError):
                            continue
                        
                        # Filtro 3: Sin nombre o nombre muy corto
                        if not product.name or len(product.name) < 5:
                            continue
                        
                        # Filtro 4: Sin imagen (banners/ADs)
                        if not product.image_url:
                            continue
                        
                        if product.product_id not in seen_ids:
                            products_with_prices.append((product, price_history))
                            seen_ids.add(product.product_id)
                except Exception as e:
                    self.logger.debug(f"Error parsing product: {e}")
                    continue
        
        self.logger.info(f"Total unique products found: {len(products_with_prices)}")
        return products_with_prices
    
    def _parse_product_with_price(
        self, 
        container: BeautifulSoup, 
        categories: Dict[str, str]
    ) -> Optional[Tuple[Product, Optional[PriceHistory]]]:
        """
        Parsear producto Y precio desde el contenedor.
        Retorna (Product, PriceHistory) o None.
        """
        try:
            # 1. Extraer URL
            link = container.select_one('a[href*="/product/"]')
            if not link and container.name == 'a' and '/product/' in str(container.get('href', '')):
                link = container
            
            if not link:
                return None
            
            product_url = link.get('href')
            if not product_url:
                return None
            
            if not product_url.startswith('http'):
                product_url = self.BASE_URL + product_url
            
            # Limpiar URL
            if '?' in product_url:
                product_url = product_url.split('?')[0]
            
            # 2. Extraer ID
            product_id_match = re.search(r'/product/(\d+)/', product_url)
            if not product_id_match:
                return None
            product_id = product_id_match.group(1)
            
            # 3. Extraer NOMBRE LIMPIO
            name = self._extract_clean_name(container)
            if not name or len(name) < 5:
                return None
            
            # 4. Extraer IMAGEN
            image_url = self._extract_image_url(container)
            
            # 5. Extraer MARCA
            brand = self._extract_brand(name)
            
            # 6. Extraer PRECIO desde el contenedor
            price_history = self._extract_price_from_container(container, product_id)
            
            # Crear producto
            product = Product(
                store_name=self.store_name,
                product_id=product_id,
                name=name,
                brand=brand,
                category=categories.get('category'),
                subcategory=categories.get('subcategory'),
                sub_subcategory=categories.get('sub_subcategory'),
                url=product_url,
                image_url=image_url,
                in_stock=True
            )
            
            return (product, price_history)
            
        except Exception as e:
            self.logger.debug(f"Error parsing product with price: {e}")
            return None
    
    def _extract_clean_name(self, container: BeautifulSoup) -> Optional[str]:
        """Extraer nombre limpio del producto SIN basura."""
        name = None
        
        # Estrategia 1: Desde imagen alt (suele ser el más completo)
        img = container.select_one('img[alt]')
        if img and img.get('alt'):
            alt_text = img.get('alt').strip()
            if len(alt_text) > 5:
                name = alt_text
        
        # Estrategia 2: Desde atributo title o aria-label del link
        if not name or len(name) < 10:
            link = container.select_one('a[href*="/product/"]')
            if link:
                title = link.get('title') or link.get('aria-label')
                if title and len(title.strip()) > 5:
                    name = title.strip()
        
        # Estrategia 3: Desde elementos de texto específicos
        if not name or len(name) < 10:
            for selector in ['b.pod-title', 'h2', 'h3', '.product-name', '[class*="title"]']:
                elem = container.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if len(text) > 5:
                        name = text
                        break
        
        # Estrategia 4: Buscar en cualquier texto del contenedor que parezca un nombre
        if not name or len(name) < 10:
            text_elements = container.find_all(['span', 'div', 'p'])
            for elem in text_elements:
                text = elem.get_text(strip=True)
                if (len(text) > 15 and 
                    not text.startswith('S/') and 
                    'Agregar' not in text and
                    'Llega' not in text and
                    any(c.isalpha() for c in text)):
                    name = text
                    break
        
        if not name:
            return None
        
        # LIMPIAR: Remover basura común
        name = str(name).strip()
        
        # Remover patrones de precio
        name = re.sub(r'S/\s*[\d,]+\.?\d*', '', name)
        name = re.sub(r'\$\s*[\d,]+\.?\d*', '', name)
        
        # Remover patrones comunes de basura
        patterns_to_remove = [
            r'Por\s+[\w\s]+',
            r'Agregar al Carro',
            r'Llega\s+(hoy|mañana)',
            r'Retira\s+hoy',
            r'BLACK\s+FRIDAY',
            r'\(\d+\)',
            r'-\d+%',
            r'Por\s+',
        ]
        
        for pattern in patterns_to_remove:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # CRÍTICO: Separar marca pegada al inicio del nombre
        # Buscar patrones como "LENOVOLaptop", "ASUSLaptop", "ASUSLAPTOP" etc.
        brands_to_separate = [
            'LENOVO', 'HP', 'DELL', 'ASUS', 'ACER', 'MSI', 'APPLE', 
            'SAMSUNG', 'LG', 'XIAOMI', 'MOTOROLA', 'HONOR', 'HUAWEI'
        ]
        
        for brand in brands_to_separate:
            # Patrón 1: MARCA + Palabra (Laptop, MacBook, etc.)
            # Acepta tanto "LENOVOLaptop" como "ASUSLAPTOP"
            pattern = f'^({brand})([A-Z][a-zA-Z]+)'
            match = re.match(pattern, name)
            if match:
                # Separar con " - "
                name = f"{match.group(1)} - {match.group(2)}{name[len(match.group(0)):]}"
                break
        
        # Limpiar espacios múltiples
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
        # Si después de limpiar quedó muy corto, retornar None
        if len(name) < 5:
            return None
        
        return name
    
    def _extract_image_url(self, container: BeautifulSoup) -> Optional[str]:
        """Extraer URL de imagen con múltiples estrategias y filtros anti-banner."""
        # Buscar todas las imágenes en el contenedor
        images = container.select('img')
        
        if not images:
            self.logger.debug("No img tags found in container")
            return None
        
        found_urls = []
        
        for img in images:
            # Intentar diferentes atributos en orden de prioridad
            for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'data-lazy', 'srcset']:
                url = img.get(attr)
                if url:
                    # Si es srcset, tomar la primera URL
                    if attr == 'srcset':
                        url = url.split(',')[0].split()[0]
                    
                    url = url.strip()
                    
                    # FILTROS ANTI-BANNER:
                    # 1. Rechazar GIFs (banners son casi siempre GIF)
                    # 2. Rechazar dimensiones típicas de banner (1280x180, 728x90, etc.)
                    # 3. Rechazar URLs con "banner" en el nombre
                    if (url and 
                        len(url) > 10 and
                        ('http' in url or url.startswith('/')) and
                        not url.lower().endswith('.gif') and  # NO GIFs
                        'placeholder' not in url.lower() and
                        'loading' not in url.lower() and
                        'blank' not in url.lower() and
                        'banner' not in url.lower() and  # NO banners
                        '1280x180' not in url and  # Dimensiones de banner
                        '728x90' not in url):
                        
                        # Si es relativa, convertirla a absoluta
                        if url.startswith('/'):
                            url = f"{self.BASE_URL}{url}"
                        
                        found_urls.append(url)
                        break
        
        if found_urls:
            return found_urls[0]
        
        self.logger.debug(f"No valid image URL found. Images found: {len(images)}")
        return None
    
    def _extract_price_from_container(
        self, 
        container: BeautifulSoup, 
        product_id: str
    ) -> Optional[PriceHistory]:
        """
        Extraer precio DESDE EL CONTENEDOR de la página de búsqueda.
        NO hace request individual.
        """
        try:
            # Estrategia 1: Buscar en elementos específicos de precio
            price_selectors = [
                'span.copy14',  # Clase específica de Falabella para precios
                'span[class*="copy"]',  # Variantes de copy
                'div[class*="prices"] span',
                '[class*="price"]',
                '.price',
                '[data-price]',
            ]
            
            found_prices = []
            
            for selector in price_selectors:
                elements = container.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    
                    # Solo procesar si contiene S/
                    if 'S/' in text:
                        price = self._clean_price(text)
                        if price:
                            found_prices.append(price)
            
            # Estrategia 2: Buscar patrón S/ en todo el contenedor
            if not found_prices:
                text = container.get_text()
                matches = re.findall(r'S/\s*[\d,]+\.?\d*', text)
                for match in matches:
                    price = self._clean_price(match)
                    if price:
                        found_prices.append(price)
            
            # Si encontramos precios, tomar el más bajo (suele ser el precio actual)
            if found_prices:
                # Ordenar y tomar el precio más bajo (ignorando outliers)
                found_prices.sort()
                
                # Si hay varios precios, tomar el más común o el segundo más bajo
                # (para evitar precios erróneos muy bajos)
                if len(found_prices) == 1:
                    final_price = found_prices[0]
                elif len(found_prices) >= 2:
                    # Tomar el segundo precio si el primero es sospechosamente bajo
                    if found_prices[0] < 50 and found_prices[1] >= 50:
                        final_price = found_prices[1]
                    else:
                        final_price = found_prices[0]
                else:
                    final_price = found_prices[0]
                
                return PriceHistory(
                    product_id=0,  # Se asignará luego
                    price=Decimal(str(final_price)),
                    currency="PEN"
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error extracting price from container: {e}")
            return None
    
    def _extract_brand(self, name: str) -> Optional[str]:
        """Extraer marca del nombre."""
        brands = [
            'LENOVO', 'HP', 'DELL', 'ASUS', 'ACER', 'MSI', 'APPLE', 'SAMSUNG', 
            'LG', 'TOSHIBA', 'RAZER', 'ALIENWARE', 'HUAWEI', 'XIAOMI',
            'DYSON', 'TAURUS', 'GAMA', 'SHARK', 'REVLON', 'SIEGEN', 'MINT', 
            'ULA', 'BLACK+DECKER', 'OSTER', 'PHILIPS', 'ELECTROLUX', 'WHIRLPOOL'
        ]
        
        name_upper = name.upper()
        for brand in brands:
            if brand in name_upper:
                return brand
        
        # Primera palabra como marca
        first_word = name.split()[0].strip().upper()
        if len(first_word) >= 3 and first_word.isalpha():
            return first_word
        
        return None
    
    def get_product_details(self, product_url: str) -> Optional[Product]:
        """No implementado."""
        return None
    
    def extract_price(self, product_data: dict) -> Optional[PriceHistory]:
        """
        DEPRECADO: Ya no se usa porque extraemos precios en _extract_products_with_prices.
        Esta función ya no hace requests individuales.
        """
        # Si por alguna razón se llama, retornar None
        return None
    
    def _clean_price(self, price_text: str) -> Optional[float]:
        """Limpiar y validar precio."""
        try:
            cleaned = re.sub(r'[^\d,.]', '', price_text)
            if not cleaned:
                return None
            
            cleaned = cleaned.replace(',', '')
            price = float(cleaned)
            
            if 50 <= price <= 100000:
                return price
            
            if price > 100000:
                price = price / 100
                if 50 <= price <= 100000:
                    return price
            
            return None
            
        except (ValueError, TypeError):
            return None