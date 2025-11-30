"""Script para limpiar la base de datos y volver a scrapear con datos mejorados."""
import sqlite3
from pathlib import Path
import sys

DB_PATH = Path("data") / "database.db"

def limpiar_bd():
    """Eliminar todos los productos y precios."""
    print("\n" + "="*60)
    print("LIMPIAR BASE DE DATOS")
    print("="*60)
    
    respuesta = input("\n¿Estás seguro de eliminar TODOS los datos? (si/no): ")
    
    if respuesta.lower() not in ['si', 's', 'yes', 'y']:
        print("Operación cancelada.")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Contar antes de borrar
    cursor.execute("SELECT COUNT(*) FROM products")
    productos_antes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM price_history")
    precios_antes = cursor.fetchone()[0]
    
    print(f"\nEliminando {productos_antes} productos y {precios_antes} registros de precios...")
    
    # Borrar todo
    cursor.execute("DELETE FROM price_history")
    cursor.execute("DELETE FROM products")
    
    # Reiniciar secuencias
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='products'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='price_history'")
    
    conn.commit()
    conn.close()
    
    print("✓ Base de datos limpiada correctamente")
    print("="*60 + "\n")
    return True

def ver_problemas():
    """Mostrar productos con problemas en la BD actual."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("PRODUCTOS CON PROBLEMAS")
    print("="*60)
    
    # Productos sin nombre completo (solo marca)
    cursor.execute("""
        SELECT id, brand, name
        FROM products
        WHERE LENGTH(name) < 15
        LIMIT 20
    """)
    sin_nombre = cursor.fetchall()
    
    if sin_nombre:
        print(f"\n{len(sin_nombre)} productos sin nombre completo:")
        for id_, brand, name in sin_nombre:
            print(f"  ID {id_}: {brand} - {name}")
    
    # Productos sin categoría
    cursor.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE category IS NULL OR category = ''
    """)
    sin_categoria = cursor.fetchone()[0]
    print(f"\n{sin_categoria} productos sin categoría")
    
    # Productos con categorías mal formateadas
    cursor.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE category LIKE '%-%'
        LIMIT 10
    """)
    cats_malas = cursor.fetchall()
    
    if cats_malas:
        print(f"\nCategorías mal formateadas (con '-'):")
        for (cat,) in cats_malas:
            print(f"  {cat}")
    
    # Precios sospechosos
    cursor.execute("""
        SELECT p.id, p.name, ph.price
        FROM products p
        JOIN price_history ph ON p.id = ph.product_id
        WHERE ph.price > 50000 OR ph.price < 10
        LIMIT 20
    """)
    precios_raros = cursor.fetchall()
    
    if precios_raros:
        print(f"\n{len(precios_raros)} productos con precios sospechosos:")
        for id_, name, price in precios_raros:
            print(f"  ID {id_}: S/ {price:.2f} - {name[:50]}")
    
    # Productos sin imagen
    cursor.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE image_url IS NULL OR image_url = ''
    """)
    sin_imagen = cursor.fetchone()[0]
    print(f"\n{sin_imagen} productos sin imagen")
    
    print("="*60 + "\n")
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ver":
        ver_problemas()
    elif len(sys.argv) > 1 and sys.argv[1] == "limpiar":
        if limpiar_bd():
            print("Ahora ejecuta:")
            print("  python main.py scrape -q laptop --pages 3 --store falabella")
    else:
        print("\nUso:")
        print("  python limpiar_bd.py ver      - Ver productos con problemas")
        print("  python limpiar_bd.py limpiar  - Borrar TODA la base de datos")
        print()