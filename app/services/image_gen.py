"""
Servicio para generación de imágenes con Replicate
"""
import replicate
import json
import os
import random
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def load_identity_config() -> Dict[str, Any]:
    """
    Carga configuración de identity desde metadata.json
    
    Returns:
        dict: Configuración con identity_strength, style_strength, etc.
    """
    metadata_path = os.path.join(settings.IDENTITY_PACK_PATH, "identity_metadata.json")
    
    try:
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                logger.info("Identity metadata cargado correctamente")
                return metadata
        else:
            logger.warning(f"Metadata no encontrado en {metadata_path}, usando valores por defecto")
            return {}
    except Exception as e:
        logger.error(f"Error al cargar identity metadata: {e}")
        return {}


def get_reference_images(identity_meta: Dict[str, Any]) -> list[str]:
    """
    Obtiene las rutas a las imágenes de referencia del identity pack
    
    Args:
        identity_meta: Metadata del identity pack
        
    Returns:
        list: Rutas a imágenes de referencia
    """
    reference_images = identity_meta.get("reference_images", [
        "identity_pack_01.png",
        "identity_pack_02.png"
    ])
    
    image_paths = []
    for img in reference_images:
        path = os.path.join(settings.IDENTITY_PACK_PATH, img)
        if os.path.exists(path):
            image_paths.append(path)
        else:
            logger.warning(f"Imagen de referencia no encontrada: {path}")
    
    if not image_paths:
        logger.error("No se encontraron imágenes de referencia")
    
    return image_paths


async def generate_image(
    prompt: str,
    state: Dict[str, Any],
    identity_meta: Dict[str, Any],
    model: str = "instantid"
) -> str:
    """
    Genera imagen usando Replicate con InstantID o IP-Adapter FaceID
    
    Args:
        prompt: Descripción de la imagen a generar
        state: Estado actual (emotion, location, etc.)
        identity_meta: Metadata del identity pack
        model: Modelo a usar ("instantid" o "ip-adapter")
        
    Returns:
        str: Ruta local de la imagen guardada
    """
    logger.info(f"Generando imagen con modelo: {model}")
    logger.info(f"Prompt: {prompt[:100]}...")
    
    # Configuración de identity
    identity_strength = identity_meta.get("identity_strength", 0.8)
    style_strength = identity_meta.get("style_strength", 0.7)
    
    # Obtener imágenes de referencia
    reference_images = get_reference_images(identity_meta)
    
    if not reference_images:
        raise Exception("No hay imágenes de referencia disponibles")
    
    # Seleccionar imagen de referencia (usar la primera o mezclar)
    reference_image_path = reference_images[0]
    logger.info(f"Usando imagen de referencia: {os.path.basename(reference_image_path)}")
    
    try:
        # Inicializar cliente Replicate
        client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
        
        # Leer imagen de referencia
        with open(reference_image_path, 'rb') as f:
            reference_image = f.read()
        
        # Componer prompt con mood/escena
        emotion = state.get("emotion_focus", "curiosidad")
        location = state.get("location", "ciudad")
        
        composed_prompt = f"{prompt}, {emotion} mood, {location} setting, natural and authentic"
        
        # Seleccionar modelo y configurar inputs
        if model == "instantid":
            model_version = "instantx/instantid"
            inputs = {
                "image": reference_image,
                "prompt": composed_prompt,
                "negative_prompt": "blurry, low quality, distorted, bad anatomy, bad proportions, duplicate",
                "ip_adapter_scale": identity_strength,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "seed": random.randint(1, 1000000)
            }
        else:  # ip-adapter
            model_version = "h94/ip-adapter-faceid-sdxl"
            inputs = {
                "image": reference_image,
                "prompt": composed_prompt,
                "negative_prompt": "blurry, low quality, distorted, bad anatomy",
                "ip_adapter_scale": identity_strength,
                "controlnet_conditioning_scale": style_strength,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "seed": random.randint(1, 1000000)
            }
        
        logger.info(f"Llamando a Replicate: {model_version}")
        
        # Ejecutar generación
        output = client.run(model_version, input=inputs)
        
        # Obtener URL de imagen generada
        if isinstance(output, list):
            image_url = output[0]
        else:
            image_url = str(output)
        
        logger.info(f"Imagen generada: {image_url[:80]}...")
        
        # Descargar y guardar imagen
        local_path = await download_and_save_image(image_url)
        
        logger.info(f"Imagen guardada en: {local_path}")
        
        return local_path
        
    except Exception as e:
        logger.error(f"Error al generar imagen: {str(e)}")
        raise Exception(f"Error en generación de imagen: {str(e)}")


async def download_and_save_image(image_url: str) -> str:
    """
    Descarga imagen desde URL y la guarda en estructura de carpetas por fecha
    
    Args:
        image_url: URL de la imagen generada
        
    Returns:
        str: Ruta local donde se guardó la imagen
    """
    try:
        # Crear estructura de carpetas: images/YYYY/MM/
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        
        images_dir = Path(settings.DATA_PATH) / "images" / year / month
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Nombre de archivo: DD_post.png
        day = now.strftime("%d")
        filename = f"{day}_post.png"
        filepath = images_dir / filename
        
        # Si ya existe, agregar timestamp
        if filepath.exists():
            timestamp = now.strftime("%H%M%S")
            filename = f"{day}_post_{timestamp}.png"
            filepath = images_dir / filename
        
        logger.info(f"Descargando imagen a: {filepath}")
        
        # Descargar imagen
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            
            # Guardar imagen
            with open(filepath, 'wb') as f:
                f.write(response.content)
        
        logger.info(f"Imagen descargada correctamente: {filepath}")
        
        return str(filepath)
        
    except Exception as e:
        logger.error(f"Error al descargar/guardar imagen: {str(e)}")
        raise Exception(f"Error al guardar imagen: {str(e)}")


# Clase de servicio (opcional)
class ImageGenerationService:
    """Servicio de generación de imágenes"""
    
    def __init__(self):
        self.client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
        self.identity_meta = load_identity_config()
    
    async def generate(
        self,
        prompt: str,
        state: Dict[str, Any],
        model: str = "instantid"
    ) -> str:
        """Genera imagen usando el servicio"""
        return await generate_image(prompt, state, self.identity_meta, model)
    
    def reload_identity_config(self):
        """Recarga la configuración de identity"""
        self.identity_meta = load_identity_config()


# Instancia singleton
image_gen_service = ImageGenerationService()
