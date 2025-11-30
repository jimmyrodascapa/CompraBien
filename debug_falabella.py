"""Script de debug para analizar HTML de Falabella."""
import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def analyze_falabella_html():
    """Analizar estructura HTML de Falabella."""
    
    url = "https://www.falabella.com.pe/falabella-pe/search?Ntt=laptop&page=1"
    
    ua = UserAgent()
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-PE,es;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    
    print("🔍 Descargando página de Falabella...")
    
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Guardar HTML completo
    with open('falabella_debug.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("✅ HTML guardado en: falabella_debug.html")
    
    print("\n📊 Analizando selectores...")
    
    # Probar diferentes selectores
    selectors_to_try = [
        'div[data-testid="pod"]',
        'div.grid-pod',
        'div.search-results-item',
        'div[class*="pod"]',
        'article',
        'div[class*="product"]',
        'div[id*="product"]',
    ]
    
    for selector in selectors_to_try:
        items = soup.select(selector)
        print(f"  {selector}: {len(items)} elementos")
        
        if items and len(items) > 0:
            print(f"    ✅ ENCONTRADO! Primer elemento:")
            first_item = items[0]
            print(f"       Clases: {first_item.get('class')}")
            print(f"       ID: {first_item.get('id')}")
            print(f"       Data attrs: {[attr for attr in first_item.attrs if attr.startswith('data-')]}")
    
    # Buscar links de productos
    print("\n🔗 Buscando links de productos...")
    links = soup.select('a[href*="/product/"]')
    print(f"  Links con '/product/': {len(links)}")
    if links:
        print(f"  Ejemplo: {links[0].get('href')}")
    
    # Buscar precios
    print("\n💰 Buscando elementos de precio...")
    price_selectors = [
        'span[data-testid*="price"]',
        '[class*="price"]',
        'span.copy14',
        'li.prices',
    ]
    
    for selector in price_selectors:
        prices = soup.select(selector)
        print(f"  {selector}: {len(prices)} elementos")
        if prices:
            print(f"    Ejemplo: {prices[0].get_text(strip=True)}")
    
    # Buscar imágenes de productos
    print("\n🖼️ Buscando imágenes...")
    images = soup.select('img[alt*="laptop"]') or soup.select('img[alt*="LAPTOP"]')
    print(f"  Imágenes con 'laptop' en alt: {len(images)}")
    
    print("\n✨ Análisis completado!")
    print("📄 Revisa el archivo 'falabella_debug.html' para ver la estructura completa")


if __name__ == "__main__":
    try:
        analyze_falabella_html()
    except Exception as e:
        print(f"❌ Error: {e}")