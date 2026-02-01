"""
Rutas de la API FastAPI
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.db.session import get_db
from app.models.post import Post
from app.services.state_engine import get_current_state, next_state, load_identity_metadata
from app.services.text_gen import generate_caption, generate_image_prompt
from app.services.image_gen import generate_image, load_identity_config
from app.services.publish_instagram import instagram_publisher
from app.core.config import settings
from app.core.logging_config import get_logger
import os

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
def health_check() -> Dict[str, str]:
    """
    Health check endpoint
    
    Returns:
        dict: Status del sistema
    """
    return {
        "status": "ok",
        "version": "2.0.0",
        "database": "connected",
        "identity_pack": "ok" if os.path.exists(settings.IDENTITY_PACK_PATH) else "missing"
    }


@router.get("/posts/latest")
def get_latest_post(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Obtiene el último post generado (sin imagen binaria, solo metadata)
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        dict: Último post con todos sus campos excepto la imagen binaria
    """
    try:
        # Obtener último post
        latest_post = db.query(Post).order_by(Post.created_at.desc()).first()
        
        if not latest_post:
            raise HTTPException(
                status_code=404,
                detail="No hay posts generados aún"
            )
        
        # Convertir a dict
        post_data = latest_post.to_dict()
        
        logger.info(f"Devolviendo último post: ID {latest_post.id}")
        
        return post_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener último post: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener post: {str(e)}"
        )


@router.post("/generate/now")
async def generate_now(
    publish: bool = False,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Ejecuta la pipeline completa de generación inmediatamente
    
    Args:
        publish: Si se debe publicar automáticamente en Instagram
        db: Sesión de base de datos
        
    Returns:
        dict: Caption, image_path y metadata del post generado
    """
    try:
        logger.info("🚀 Iniciando generación manual de post...")
        
        # 1. Cargar identity metadata
        logger.info("Paso 1/6: Cargando identity metadata...")
        identity_metadata_path = os.path.join(
            settings.IDENTITY_PACK_PATH,
            "identity_metadata.json"
        )
        identity_meta = load_identity_metadata(identity_metadata_path)
        
        if not identity_meta:
            logger.warning("Identity metadata vacío, usando valores por defecto")
            identity_meta = {
                "influencer_name": "Influencer IA",
                "description": "Un viaje de autodescubrimiento",
                "style_notes": "fotografía natural y auténtica"
            }
        
        # 2. Obtener estado actual
        logger.info("Paso 2/6: Obteniendo estado actual...")
        current_state = get_current_state(db)
        logger.info(f"Estado actual: {current_state.get('chapter')} / {current_state.get('emotion_focus')}")
        
        # 3. Calcular siguiente estado
        logger.info("Paso 3/6: Calculando siguiente estado...")
        new_state = next_state(current_state)
        logger.info(f"Nuevo estado: {new_state.get('chapter')} / {new_state.get('emotion_focus')}")
        
        # 4. Generar caption
        logger.info("Paso 4/6: Generando caption con OpenAI...")
        caption = generate_caption(new_state, identity_meta)
        logger.info(f"Caption generado: {len(caption.split())} palabras")
        
        # 5. Generar imagen
        logger.info("Paso 5/6: Generando imagen con Replicate...")
        image_prompt = generate_image_prompt(new_state, identity_meta)
        logger.info(f"Image prompt: {image_prompt[:100]}...")
        
        image_path = await generate_image(
            prompt=image_prompt,
            state=new_state,
            identity_meta=identity_meta,
            model="Nano-banana"
        )
        logger.info(f"Imagen generada: {image_path}")
        
        # 6. Guardar en base de datos
        logger.info("Paso 6/6: Guardando en base de datos...")
        new_post = Post(
            chapter=new_state.get("chapter"),
            emotion_focus=new_state.get("emotion_focus"),
            learning_goal=new_state.get("learning_goal"),
            location=new_state.get("location"),
            caption=caption,
            image_prompt=image_prompt,
            image_path=image_path,
            published_platforms={},
            meta=new_state.get("meta", {})
        )
        
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        logger.info(f"✅ Post guardado con ID: {new_post.id}")
        
        # 7. Publicar en Instagram (opcional)
        if publish and instagram_publisher.is_enabled():
            logger.info("Publicando en Instagram...")
            media_id = instagram_publisher.publish_post(image_path, caption)
            
            if media_id:
                new_post.published_platforms = {"instagram": media_id}
                db.commit()
                logger.info(f"📱 Publicado en Instagram: {media_id}")
            else:
                logger.warning("Fallo al publicar en Instagram")
        
        # Preparar respuesta
        response = {
            "success": True,
            "post_id": new_post.id,
            "caption": caption,
            "image_path": image_path,
            "state": {
                "chapter": new_state.get("chapter"),
                "emotion_focus": new_state.get("emotion_focus"),
                "location": new_state.get("location")
            },
            "published": bool(new_post.published_platforms),
            "published_platforms": new_post.published_platforms,
            "created_at": new_post.created_at.isoformat()
        }
        
        logger.info("✅ Generación completada exitosamente")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error en generación: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar post: {str(e)}"
        )
