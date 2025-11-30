"""Scheduler para automatización de scraping."""
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz

from src.scrapers.factory import get_scraper
from src.config.settings import SCHEDULER_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ScraperScheduler:
    """Scheduler para ejecutar scraping automáticamente."""
    
    def __init__(self):
        self.timezone = pytz.timezone(SCHEDULER_CONFIG.timezone)
        self.scheduler = BlockingScheduler(timezone=self.timezone)
        self.logger = logger
    
    def scrape_all_stores(self, queries: list[str]):
        """Ejecutar scraping en todas las tiendas configuradas."""
        from src.scrapers.factory import ScraperFactory
        
        stores = ScraperFactory.get_available_stores()
        self.logger.info(f"Starting scheduled scraping for: {stores}")
        
        for store_name in stores:
            try:
                self.logger.info(f"Scraping {store_name}...")
                scraper = get_scraper(store_name)
                result = scraper.run_scraping(queries, max_pages=3)
                
                self.logger.info(
                    f"{store_name} completed: "
                    f"{result.products_saved} products saved, "
                    f"{result.errors} errors"
                )
                
            except Exception as e:
                self.logger.error(f"Error scraping {store_name}: {e}")
    
    def add_scraping_job(
        self, 
        queries: list[str],
        interval_hours: int = None
    ):
        """Agregar job de scraping periódico."""
        if interval_hours is None:
            interval_hours = SCHEDULER_CONFIG.scraping_interval_hours
        
        self.scheduler.add_job(
            func=self.scrape_all_stores,
            trigger=IntervalTrigger(hours=interval_hours),
            args=[queries],
            id="scraping_job",
            name="Scraping periódico",
            replace_existing=True,
            max_instances=SCHEDULER_CONFIG.max_instances
        )
        
        self.logger.info(
            f"Scraping job scheduled every {interval_hours} hours"
        )
    
    def add_cleanup_job(self):
        """Agregar job de limpieza de datos antiguos."""
        self.scheduler.add_job(
            func=self._cleanup_old_data,
            trigger=CronTrigger(hour=3, minute=0),  # 3 AM diario
            id="cleanup_job",
            name="Limpieza de datos antiguos",
            replace_existing=True
        )
        
        self.logger.info("Cleanup job scheduled at 3:00 AM daily")
    
    def _cleanup_old_data(self):
        """Limpiar datos antiguos de la base de datos."""
        from src.database.connection import db
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(
            days=SCHEDULER_CONFIG.cleanup_old_data_days
        )
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Eliminar historial de precios antiguo
                cursor.execute(
                    "DELETE FROM price_history WHERE timestamp < ?",
                    (cutoff_date,)
                )
                deleted_prices = cursor.rowcount
                
                # Eliminar logs antiguos
                cursor.execute(
                    "DELETE FROM scraping_logs WHERE timestamp < ?",
                    (cutoff_date,)
                )
                deleted_logs = cursor.rowcount
                
                self.logger.info(
                    f"Cleanup completed: {deleted_prices} price entries, "
                    f"{deleted_logs} log entries removed"
                )
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def run_once(self, queries: list[str]):
        """Ejecutar scraping una vez (sin scheduler)."""
        self.logger.info("Running one-time scraping...")
        self.scrape_all_stores(queries)
    
    def start(self, queries: list[str]):
        """Iniciar scheduler."""
        self.add_scraping_job(queries)
        self.add_cleanup_job()
        
        # Ejecutar inmediatamente al inicio
        self.logger.info("Running initial scraping...")
        self.scrape_all_stores(queries)
        
        self.logger.info("Scheduler started. Press Ctrl+C to exit.")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Scheduler stopped by user")
            self.scheduler.shutdown()
    
    def list_jobs(self):
        """Listar jobs programados."""
        jobs = self.scheduler.get_jobs()
        
        if not jobs:
            self.logger.info("No scheduled jobs")
            return
        
        self.logger.info("Scheduled jobs:")
        for job in jobs:
            self.logger.info(f"  - {job.name} (ID: {job.id})")
            self.logger.info(f"    Next run: {job.next_run_time}")
