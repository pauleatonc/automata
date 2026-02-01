"""
Aplicación principal FastAPI
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.scheduler import scheduler
from app.db.session import init_db
from app.jobs.daily_job import generate_daily_post

# Configurar logging
setup_logging("INFO")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación
    Startup y Shutdown hooks
    """
    # ========== STARTUP ==========
    logger.info("=" * 60)
    logger.info("🚀 Iniciando AI Influencer Backend v2.0")
    logger.info("=" * 60)
    
    # 1. Inicializar base de datos
    logger.info("📦 Inicializando base de datos...")
    try:
        init_db()
        logger.info("✅ Base de datos inicializada")
    except Exception as e:
        logger.error(f"❌ Error al inicializar DB: {e}")
        raise
    
    # 2. Verificar identity pack
    if os.path.exists(settings.IDENTITY_PACK_PATH):
        logger.info(f"✅ Identity pack encontrado: {settings.IDENTITY_PACK_PATH}")
    else:
        logger.warning(f"⚠️  Identity pack no encontrado: {settings.IDENTITY_PACK_PATH}")
    
    # 3. Iniciar scheduler (controlado por ENV)
    enable_scheduler = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    
    if enable_scheduler:
        logger.info("⏰ Iniciando scheduler...")
        try:
            scheduler.set_job_function(generate_daily_post)
            scheduler.start()
            logger.info(f"✅ Scheduler iniciado: {settings.DAILY_CRON} ({settings.TIMEZONE})")
        except Exception as e:
            logger.error(f"❌ Error al iniciar scheduler: {e}")
            logger.warning("Continuando sin scheduler...")
    else:
        logger.info("⏸️  Scheduler deshabilitado (ENABLE_SCHEDULER=false)")
    
    logger.info("=" * 60)
    logger.info("✨ Aplicación lista")
    logger.info(f"📖 Documentación: http://localhost:8000/docs")
    logger.info(f"🔗 API: http://localhost:8000/api/v1")
    logger.info("=" * 60)
    
    yield
    
    # ========== SHUTDOWN ==========
    logger.info("=" * 60)
    logger.info("🛑 Deteniendo aplicación...")
    logger.info("=" * 60)
    
    if enable_scheduler:
        logger.info("⏰ Deteniendo scheduler...")
        scheduler.shutdown()
        logger.info("✅ Scheduler detenido")
    
    logger.info("✅ Aplicación detenida correctamente")
    logger.info("=" * 60)


# Crear aplicación FastAPI
app = FastAPI(
    title="AI Influencer Backend",
    description="Backend para generación automática de posts de influencer IA con narrativa evolutiva",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(router, prefix="/api/v1", tags=["posts"])


@app.get("/")
def root():
    """Ruta raíz - Información de la API"""
    return {
        "name": "AI Influencer Backend",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": "/api/v1/health",
            "latest_post": "/api/v1/posts/latest",
            "generate": "/api/v1/generate/now"
        },
        "features": [
            "Generación automática de posts con IA",
            "Narrativa evolutiva con state engine",
            "Generación de imágenes con Nano Banana (refs múltiples) + soporte opcional InstantID/IP-Adapter",
            "Publicación automática en Instagram",
            "Scheduler configurable"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    # Configuración para desarrollo
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
