"""CLI principal para el price tracker - VERSION SIN EMOJIS PARA WINDOWS."""
import click
from rich.console import Console
from rich.table import Table

from src.scrapers.factory import get_scraper, ScraperFactory
from src.scheduler.job_scheduler import ScraperScheduler
from src.analytics.price_analyzer import PriceAnalyzer
from src.database.repository import ProductRepository, PriceHistoryRepository, StatsRepository
from src.utils.logger import get_logger

console = Console()
logger = get_logger(__name__)


@click.group()
def cli():
    """Price Tracker - Monitor de precios de e-commerce"""
    pass


@cli.command()
@click.option(
    '--store',
    type=click.Choice(['falabella', 'all'], case_sensitive=False),
    default='all',
    help='Tienda a scrapear'
)
@click.option(
    '--queries',
    '-q',
    multiple=True,
    default=['laptop', 'smartphone', 'televisor'],
    help='Terminos de busqueda (puede usar multiples -q)'
)
@click.option(
    '--pages',
    default=3,
    help='Numero maximo de paginas por busqueda'
)
def scrape(store, queries, pages):
    """Ejecutar scraping manual."""
    console.print(f"\n[bold cyan]Iniciando scraping...[/bold cyan]")
    console.print(f"Tienda: [yellow]{store}[/yellow]")
    console.print(f"Busquedas: [yellow]{', '.join(queries)}[/yellow]")
    console.print(f"Paginas: [yellow]{pages}[/yellow]\n")
    
    stores = [store] if store != 'all' else ScraperFactory.get_available_stores()
    
    for store_name in stores:
        try:
            console.print(f"\n[bold]Scraping {store_name}...[/bold]")
            
            scraper = get_scraper(store_name)
            result = scraper.run_scraping(list(queries), max_pages=pages)
            
            # Mostrar resultados
            console.print(f"[green]Completado[/green]")
            console.print(f"  Productos encontrados: {result.products_found}")
            console.print(f"  Productos guardados: {result.products_saved}")
            console.print(f"  Errores: {result.errors}")
            console.print(f"  Duracion: {result.duration_seconds:.2f}s")
            
            if result.error_messages:
                console.print("\n[yellow]Errores:[/yellow]")
                for error in result.error_messages[:5]:
                    console.print(f"  * {error}")
                    
        except Exception as e:
            console.print(f"[red]Error en {store_name}: {e}[/red]")


@cli.command()
@click.option(
    '--queries',
    '-q',
    multiple=True,
    default=['laptop', 'smartphone', 'televisor'],
    help='Terminos de busqueda'
)
@click.option(
    '--interval',
    default=6,
    help='Intervalo en horas entre ejecuciones'
)
def schedule(queries, interval):
    """Iniciar scraping automatico (scheduler)."""
    console.print("\n[bold cyan]Iniciando scheduler...[/bold cyan]")
    console.print(f"Intervalo: [yellow]{interval} horas[/yellow]")
    console.print(f"Busquedas: [yellow]{', '.join(queries)}[/yellow]")
    console.print("\n[dim]Presiona Ctrl+C para detener[/dim]\n")
    
    scheduler = ScraperScheduler()
    scheduler.start(list(queries))


@cli.command(name='list')
@click.option('--limit', default=50, help='Numero de productos a mostrar')
def list_products(limit):
    """Listar todos los productos en la base de datos."""
    repo = ProductRepository()
    price_repo = PriceHistoryRepository()
    products = repo.get_all_products(limit=limit)
    
    if not products:
        console.print("[yellow]No hay productos en la base de datos[/yellow]")
        return
    
    table = Table(title=f"Productos ({len(products)})")
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Tienda", style="magenta", width=10)
    table.add_column("Marca", style="yellow", width=8)
    table.add_column("Categoria", style="blue", width=18)
    table.add_column("Subcategoria", style="blue", width=15)
    table.add_column("Nombre", style="green", width=40)
    table.add_column("Precio", style="red", justify="right", width=12)
    
    for product in products:
        # Obtener precio mas reciente
        latest_price = price_repo.get_latest_price(product.id)
        price_str = f"S/ {latest_price['price']:.2f}" if latest_price else "-"
        
        table.add_row(
            str(product.id),
            product.store_name,
            (product.brand or '-')[:7],
            (product.category or '-')[:17],
            (product.subcategory or '-')[:14],
            product.name[:37] + "..." if len(product.name) > 40 else product.name,
            price_str
        )
    
    console.print(table)
    
    if len(products) >= limit:
        console.print(f"\n[dim]Mostrando primeros {limit} productos. Use --limit para ver mas.[/dim]")


@cli.command(name='search')
@click.argument('query')
@click.option('--limit', default=20, help='Numero de resultados')
def search_products(query, limit):
    """Buscar productos por nombre o marca."""
    repo = ProductRepository()
    price_repo = PriceHistoryRepository()
    products = repo.search_products(query)
    
    if not products:
        console.print(f"[yellow]No se encontraron productos con: {query}[/yellow]")
        return
    
    table = Table(title=f"Resultados: {query} ({len(products)})")
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Marca", style="yellow", width=8)
    table.add_column("Nombre", style="green", width=50)
    table.add_column("Precio", style="red", justify="right", width=12)
    table.add_column("Categoria", style="blue", width=20)
    
    for product in products[:limit]:
        latest_price = price_repo.get_latest_price(product.id)
        price_str = f"S/ {latest_price['price']:.2f}" if latest_price else "-"
        category = product.category or '-'
        
        table.add_row(
            str(product.id),
            (product.brand or '-')[:7],
            product.name[:47] + "..." if len(product.name) > 50 else product.name,
            price_str,
            category[:19]
        )
    
    console.print(table)
    
    if len(products) > limit:
        console.print(f"\n[dim]... y {len(products) - limit} mas. Use --limit para ver mas.[/dim]")


@cli.command(name='stats')
def show_stats():
    """Mostrar estadisticas generales."""
    stats_repo = StatsRepository()
    stats = stats_repo.get_general_stats()
    
    console.print("\n[bold cyan]ESTADISTICAS GENERALES[/bold cyan]\n")
    
    # Stats basicas
    console.print(f"Total de productos: [green]{stats['total_products']}[/green]")
    console.print(f"Total de registros de precios: [green]{stats['total_price_records']}[/green]")
    
    if stats.get('products_by_store'):
        console.print("\n[bold]Productos por tienda:[/bold]")
        for item in stats['products_by_store']:
            console.print(f"   * {item['store_name']}: {item['count']}")
    
    if stats.get('top_brands'):
        console.print("\n[bold]Top 10 marcas:[/bold]")
        for item in stats['top_brands']:
            console.print(f"   * {item['brand']}: {item['count']}")
    
    if stats.get('products_by_category'):
        console.print("\n[bold]Top 10 categorias:[/bold]")
        for item in stats['products_by_category']:
            sub = f" > {item['subcategory']}" if item['subcategory'] else ""
            console.print(f"   * {item['category']}{sub}: {item['count']}")
    
    console.print()


@cli.command(name='history')
@click.argument('product_id', type=int)
def price_history(product_id):
    """Ver historial de precios de un producto."""
    repo = ProductRepository()
    price_repo = PriceHistoryRepository()
    
    # Buscar producto por ID de la BD
    products = repo.get_all_products(limit=1000)
    product = next((p for p in products if p.id == product_id), None)
    
    if not product:
        console.print(f"[red]Producto con ID {product_id} no encontrado[/red]")
        return
    
    history = price_repo.get_price_history(product_id, limit=30)
    
    if not history:
        console.print(f"[yellow]No hay historial de precios para este producto[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Historial de Precios[/bold cyan]")
    console.print(f"[green]{product.name}[/green]\n")
    
    table = Table()
    table.add_column("Fecha", style="cyan")
    table.add_column("Precio", style="green", justify="right")
    table.add_column("Cambio", style="yellow", justify="right")
    
    prev_price = None
    for entry in history:
        date_str = entry.scraped_at.strftime("%Y-%m-%d %H:%M") if entry.scraped_at else "-"
        price_str = f"{entry.currency} {entry.price:.2f}"
        
        if prev_price:
            change = float(entry.price) - prev_price
            if change > 0:
                change_str = f"[+] +S/ {abs(change):.2f}"
            elif change < 0:
                change_str = f"[-] -S/ {abs(change):.2f}"
            else:
                change_str = "[ ] Sin cambio"
        else:
            change_str = "-"
        
        table.add_row(date_str, price_str, change_str)
        prev_price = float(entry.price)
    
    console.print(table)
    console.print()


@cli.command()
@click.option(
    '--min-discount',
    default=15.0,
    help='Descuento minimo para considerar oferta (%)'
)
@click.option(
    '--limit',
    default=10,
    help='Numero de ofertas a mostrar'
)
def deals(min_discount, limit):
    """Mostrar mejores ofertas actuales."""
    console.print("\n[bold cyan]Analizando ofertas...[/bold cyan]\n")
    
    analyzer = PriceAnalyzer()
    best_deals = analyzer.get_best_deals(limit)
    
    if not best_deals:
        console.print("[yellow]No se encontraron ofertas significativas[/yellow]")
        return
    
    table = Table(title=f"Top {len(best_deals)} Ofertas")
    table.add_column("Producto", style="green")
    table.add_column("Antes", style="red", justify="right")
    table.add_column("Ahora", style="green", justify="right")
    table.add_column("Descuento", style="cyan", justify="right")
    table.add_column("Ahorras", style="yellow", justify="right")
    
    for deal in best_deals:
        table.add_row(
            deal['product_name'][:50],
            f"S/ {deal['old_price']:.2f}",
            f"S/ {deal['new_price']:.2f}",
            f"{deal['discount']:.1f}%",
            f"S/ {deal['savings']:.2f}"
        )
    
    console.print(table)


@cli.command()
def stores():
    """Listar tiendas disponibles."""
    available = ScraperFactory.get_available_stores()
    
    console.print("\n[bold cyan]Tiendas disponibles:[/bold cyan]\n")
    
    for store in available:
        console.print(f"  [green]{store}[/green]")
    
    console.print("\n[dim]Para agregar mas tiendas, implementa un nuevo scraper[/dim]\n")


@cli.command()
def init():
    """Inicializar base de datos y estructura."""
    from src.database.connection import db_connection
    
    console.print("\n[bold cyan]Inicializando sistema...[/bold cyan]\n")
    
    # La base de datos se inicializa automaticamente
    console.print("Base de datos inicializada")
    console.print(f"  Ubicacion: {db_connection.db_path}")
    
    console.print("\n[green]Sistema listo para usar![/green]")
    console.print("\nEjemplos:")
    console.print("  python main.py scrape -q laptop")
    console.print("  python main.py list")
    console.print("  python main.py search laptop")
    console.print("  python main.py stats")
    console.print("  python main.py history 1\n")


if __name__ == '__main__':
    cli()