"""Test script para verificar Playwright con Falabella."""
from playwright.sync_api import sync_playwright
import time

def test_falabella():
    print("🚀 Iniciando test de Playwright...")
    
    with sync_playwright() as p:
        print("📦 Lanzando navegador...")
        browser = p.chromium.launch(
            headless=False,  # Visible para debug
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        
        # Ocultar webdriver
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        url = "https://www.falabella.com.pe/falabella-pe/search?Ntt=laptop"
        
        print(f"🌐 Navegando a: {url}")
        
        try:
            # Navegar con estrategia flexible
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            print("✅ Página cargada (domcontentloaded)")
        except Exception as e:
            print(f"⚠️  Error en goto: {e}")
            print("Intentando continuar...")
        
        # Esperar un poco
        print("⏳ Esperando JavaScript...")
        time.sleep(5)
        
        # Tomar screenshot
        print("📸 Tomando screenshot...")
        page.screenshot(path='test_screenshot.png', full_page=True)
        
        # Guardar HTML
        print("💾 Guardando HTML...")
        html = page.content()
        with open('test_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"📄 HTML size: {len(html)} bytes")
        
        # Buscar elementos
        print("\n🔍 Buscando elementos...")
        
        # Imágenes
        images = page.locator('img').count()
        print(f"   Imágenes: {images}")
        
        # Links
        links = page.locator('a').count()
        print(f"   Links: {links}")
        
        # Imágenes con alt que contengan laptop
        laptop_images = page.locator('img[alt*="laptop"], img[alt*="LAPTOP"], img[alt*="Laptop"]').count()
        print(f"   Imágenes con 'laptop' en alt: {laptop_images}")
        
        # Links de productos
        product_links = page.locator('a[href*="/product/"]').count()
        print(f"   Links de productos: {product_links}")
        
        # Esperar para ver la página
        print("\n⏸️  Página abierta por 10 segundos para inspección...")
        time.sleep(10)
        
        print("\n✅ Test completado!")
        print("📁 Archivos generados:")
        print("   - test_screenshot.png")
        print("   - test_page.html")
        
        context.close()
        browser.close()

if __name__ == "__main__":
    try:
        test_falabella()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()