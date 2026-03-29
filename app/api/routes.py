"""
Rutas de la API FastAPI
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
from pathlib import Path
from app.db.session import get_db
from app.models.post import Post
from app.services.state_engine import get_current_state, next_state, load_identity_metadata
from app.services.text_gen import generate_caption
from app.services.image_gen import generate_image, load_identity_config
from app.services.publish_instagram import instagram_publisher
from app.core.config import settings
from app.core.logging_config import get_logger
import os

logger = get_logger(__name__)
router = APIRouter()

_MAGIC_SIGNATURES = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP
]


def _detect_image_media_type(path: Path) -> str:
    """Detect actual image MIME type from file magic bytes."""
    try:
        with open(path, "rb") as f:
            header = f.read(12)
        for magic, mime in _MAGIC_SIGNATURES:
            if header.startswith(magic):
                return mime
        if header[4:8] == b"WEBP":
            return "image/webp"
    except OSError:
        pass
    return "application/octet-stream"


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


@router.get("/files/images/{year}/{month}/{filename}")
@router.head("/files/images/{year}/{month}/{filename}")
def serve_generated_image(year: str, month: str, filename: str):
    """
    Sirve imágenes generadas para uso por Instagram Graph API.
    Debe ser accesible públicamente desde INSTAGRAM_GRAPH_PUBLIC_BASE_URL.
    """
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    image_path = Path(settings.DATA_PATH) / "images" / year / month / filename
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    media_type = _detect_image_media_type(image_path)
    return FileResponse(path=str(image_path), media_type=media_type)


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
        
        # 5. Generar imagen (build_visual_prompt se ejecuta internamente)
        logger.info("Paso 5/6: Generando imagen con Replicate...")
        image_path, source_image_url = await generate_image(
            prompt="",
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
            image_prompt="(built internally by build_visual_prompt)",
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
            media_id = instagram_publisher.publish_post(
                image_path, caption, source_image_url=source_image_url
            )
            
            if media_id:
                platforms = {"instagram": media_id}
                logger.info(f"📱 Publicado en Instagram: {media_id}")

                story_id = instagram_publisher.publish_story(
                    image_path, source_image_url=source_image_url
                )
                if story_id:
                    platforms["instagram_story"] = story_id
                    logger.info(f"📱 Story publicada: {story_id}")
                else:
                    logger.warning("Fallo al publicar Story")

                new_post.published_platforms = platforms
                db.commit()
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
