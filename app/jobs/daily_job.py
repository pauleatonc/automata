"""
Job diario para generación automática de posts
"""
from app.db.session import SessionLocal
from app.services.state_engine import state_engine
from app.services.publish_instagram import instagram_publisher
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def generate_daily_post():
    """
    Tarea programada para generar post diario
    Ejecutada por el scheduler según configuración DAILY_CRON
    """
    logger.info("🔄 Iniciando generación programada de post...")
    
    db = SessionLocal()
    try:
        # Generar post con publicación automática en Instagram si está habilitado
        success, post, error = await state_engine.generate_post(
            db=db,
            trigger_type="scheduled",
            publish_to_instagram=instagram_publisher.is_enabled()
        )
        
        if success:
            logger.info(f"✅ Post generado exitosamente: ID {post.id}")
            if post.published_platforms and "instagram" in post.published_platforms:
                logger.info(f"📱 Publicado en Instagram: {post.published_platforms['instagram']}")
            if post.published_platforms and "instagram_story" in post.published_platforms:
                logger.info(f"📱 Story publicada en Instagram: {post.published_platforms['instagram_story']}")
        else:
            logger.error(f"❌ Error al generar post: {error}")
            
    except Exception as e:
        logger.error(f"❌ Excepción en generación programada: {str(e)}")
    finally:
        db.close()

