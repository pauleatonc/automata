"""
Configuración del scheduler para generación automática de posts
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PostScheduler:
    """Scheduler para la generación automática de posts"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
        self._job_func = None
        
    def set_job_function(self, job_func):
        """
        Establece la función que se ejecutará en cada job
        
        Args:
            job_func: Función async a ejecutar
        """
        self._job_func = job_func
    
    def start(self):
        """Inicia el scheduler"""
        if not self._job_func:
            logger.error("No se ha configurado la función del job")
            return
            
        try:
            # Parsear expresión cron
            cron_parts = settings.DAILY_CRON.split()
            
            if len(cron_parts) != 5:
                logger.error(f"Expresión CRON inválida: {settings.DAILY_CRON}")
                return
            
            minute, hour, day, month, day_of_week = cron_parts
            
            # Crear trigger cron
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=settings.TIMEZONE
            )
            
            # Agregar job
            self.scheduler.add_job(
                self._job_func,
                trigger=trigger,
                id="daily_post_generation",
                name="Generación diaria de post",
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info(f"Scheduler iniciado con cron: {settings.DAILY_CRON} ({settings.TIMEZONE})")
            
        except Exception as e:
            logger.error(f"Error al iniciar scheduler: {str(e)}")
    
    def shutdown(self):
        """Detiene el scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler detenido")


# Instancia global del scheduler
scheduler = PostScheduler()

