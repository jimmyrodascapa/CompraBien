"""Analizar HTML de Falabella para encontrar selectores correctos."""
from bs4 import BeautifulSoup

# Leer el HTML del test
with open('test_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("✅ HTML leído correctamente")

# Parsear con BeautifulSoup
soup = BeautifulSoup(content, 'html.parser')

print("\n📊 ANÁLISIS DEL HTML:")
print("=" * 60)

# 1. Contar elementos básicos
print("\n1️⃣ Elementos básicos:")
images = soup.select('img')
links = soup.select('a')
divs = soup.select('div')
print(f"   Total imágenes: {len(images)}")
print(f"   Total links: {len(links)}")
print(f"   Total divs: {len(divs)}")

# 2. Buscar imágenes de productos
print("\n2️⃣ Imágenes de productos:")
laptop_images = soup.select('img[alt*="laptop"], img[alt*="LAPTOP"], img[alt*="Laptop"]')
print(f"   Imágenes con 'laptop' en alt: {len(laptop_images)}")

if laptop_images:
    for i, img in enumerate(laptop_images[:3]):
        print(f"\n   Imagen {i+1}:")
        print(f"      alt: {img.get('alt')[:80]}...")
        print(f"      src: {img.get('src')[:80]}...")
        
        # Buscar el link padre
        parent = img
        for _ in range(10):
            parent = parent.find_parent()
            if not parent:
                break
            link = parent.select_one('a[href*="/product/"]')
            if link:
                print(f"      Link encontrado: {link.get('href')[:80]}...")
                break

# 3. Links de productos
print("\n3️⃣ Links de productos:")
product_links = soup.select('a[href*="/product/"]')
print(f"   Total links con '/product/': {len(product_links)}")

if product_links:
    print(f"   Ejemplos:")
    for link in product_links[:5]:
        href = link.get('href', '')
        print(f"      {href}")

# 4. Buscar estructura de productos
print("\n4️⃣ Estructura de contenedores:")

# Probar selectores comunes
selectors = [
    'div[data-testid="pod"]',
    'div[class*="pod"]',
    'div[class*="ProductCard"]',
    'div[class*="search-results"]',
    'article',
]

for selector in selectors:
    items = soup.select(selector)
    if items:
        print(f"   ✅ {selector}: {len(items)} elementos")
    else:
        print(f"   ❌ {selector}: 0 elementos")

# 5. Analizar clases comunes
print("\n5️⃣ Clases CSS comunes en divs:")
all_classes = []
for div in soup.select('div[class]'):
    classes = div.get('class', [])
    all_classes.extend(classes)

from collections import Counter
common_classes = Counter(all_classes).most_common(20)

print("   Top 20 clases más usadas:")
for cls, count in common_classes:
    if 'pod' in cls.lower() or 'product' in cls.lower() or 'card' in cls.lower():
        print(f"      ✨ {cls}: {count} veces")
    else:
        print(f"         {cls}: {count} veces")

print("\n" + "=" * 60)
print("✅ Análisis completado!")