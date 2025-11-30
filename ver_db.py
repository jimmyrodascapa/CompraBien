"""Script simple para ver los datos de la base de datos CORRECTA."""
import sqlite3
from pathlib import Path

# La BD real esta en data/database.db
DB_PATH = Path("data") / "database.db"

def ver_productos():
    """Ver todos los productos con sus precios."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
    SELECT 
        p.id,
        p.store_name,
        p.brand,
        p.category,
        p.subcategory,
        p.name,
        ph.price
    FROM products p
    LEFT JOIN (
        SELECT product_id, price
        FROM price_history
        WHERE (product_id, scraped_at) IN (
            SELECT product_id, MAX(scraped_at)
            FROM price_history
            GROUP BY product_id
        )
    ) ph ON p.id = ph.product_id
    ORDER BY p.id
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print("\n" + "="*130)
    print(f"{'ID':<5} {'MARCA':<8} {'CATEGORIA':<25} {'SUBCATEGORIA':<15} {'PRECIO':<10} {'NOMBRE':<50}")
    print("="*130)
    
    for row in results:
        id_, store, brand, category, subcategory, name, price = row
        brand = (brand or "N/A")[:7]
        category = (category or "N/A")[:24]
        subcategory = (subcategory or "N/A")[:14]
        price_str = f"S/ {price:.0f}" if price else "-"
        name_short = name[:47] + "..." if len(name) > 50 else name
        
        print(f"{id_:<5} {brand:<8} {category:<25} {subcategory:<15} {price_str:<10} {name_short:<50}")
    
    print("="*130)
    print(f"Total: {len(results)} productos\n")
    
    conn.close()

def ver_stats():
    """Ver estadisticas."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total productos
    cursor.execute("SELECT COUNT(*) FROM products")
    total = cursor.fetchone()[0]
    
    # Productos con precio
    cursor.execute("""
        SELECT COUNT(DISTINCT product_id)
        FROM price_history
    """)
    con_precio = cursor.fetchone()[0]
    
    # Por categoria
    cursor.execute("""
        SELECT category, subcategory, COUNT(*) as count
        FROM products
        WHERE category IS NOT NULL
        GROUP BY category, subcategory
        ORDER BY count DESC
        LIMIT 10
    """)
    categorias = cursor.fetchall()
    
    # Por marca
    cursor.execute("""
        SELECT brand, COUNT(*) as count
        FROM products
        WHERE brand IS NOT NULL
        GROUP BY brand
        ORDER BY count DESC
        LIMIT 10
    """)
    marcas = cursor.fetchall()
    
    print("\n" + "="*60)
    print("ESTADISTICAS")
    print("="*60)
    print(f"\nTotal de productos: {total}")
    print(f"Productos con precio: {con_precio}")
    print(f"Productos sin precio: {total - con_precio}")
    
    print("\nTop Categorias:")
    for cat, subcat, count in categorias:
        sub = f" > {subcat}" if subcat else ""
        print(f"  * {cat}{sub}: {count}")
    
    print("\nTop Marcas:")
    for marca, count in marcas:
        print(f"  * {marca}: {count}")
    
    print("="*60 + "\n")
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        ver_stats()
    else:
        ver_productos()