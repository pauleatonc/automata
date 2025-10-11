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


def build_visual_prompt(state: Dict[str, Any]) -> str:
    """
    Construye el prompt visual con características específicas del personaje
    
    Args:
        state: Estado actual con emotion_focus y location
        
    Returns:
        str: Prompt detallado para generación de imagen
    """
    emotion = state.get("emotion_focus", "curiosidad")
    location = state.get("location", "ciudad")
    
    # Mapeo de emociones a mood visual
    emotion_moods = {
        "curiosidad": "contemplative curiosity, open wonder",
        "asombro": "quiet amazement, discovery",
        "confusión": "thoughtful uncertainty, introspection",
        "empatía": "warm connection, understanding",
        "ternura": "soft tenderness, gentle intimacy",
        "soledad": "solitary reflection, peaceful isolation",
        "memoria": "nostalgic remembrance, distant gaze",
        "aceptación": "serene acceptance, inner peace",
        "libertad": "expansive freedom, lightness"
    }
    
    mood = emotion_moods.get(emotion, "contemplative presence")
    
    # Extraer cue de ubicación (simplificar ubicación para el prompt)
    location_cue = _extract_location_cue(location)
    
    # Construir prompt visual específico
    prompt = f"""same woman as reference, feminine-androgynous aesthetic, 
light olive skin tone, light gray-green eyes, pastel lilac hair, 
minimalist contemporary clothing, understated style,
cinematic composition, soft natural lighting, shallow depth of field,
inspired by Her, Ex Machina, Ghost in the Shell,
mood: {mood},
scene: {location_cue},
photorealistic portrait, intimate framing, 8k quality"""
    
    logger.info(f"Visual prompt construido: {emotion} / {location_cue}")
    
    return prompt


def _extract_location_cue(location: str) -> str:
    """
    Extrae cue visual de la ubicación para el prompt
    
    Args:
        location: Ubicación completa (ej: "Santiago, Barrio Lastarria")
        
    Returns:
        str: Cue visual simplificado
    """
    # Mapeo de ubicaciones a cues visuales
    location_cues = {
        # Chile
        "Santiago": "urban contemporary space, modern architecture",
        "Lastarria": "bohemian urban corner, cultural district",
        "Valparaíso": "colorful hillside, coastal bohemian atmosphere",
        "Puerto Varas": "lakeside serenity, mountain backdrop",
        "Patagonia": "vast wild landscape, raw nature",
        
        # Ciudades grandes
        "Buenos Aires": "cosmopolitan cafe culture, European-inspired streets",
        "Ciudad de México": "vibrant cultural corner, historic modernism",
        "Tokio": "minimalist urban space, neon reflections",
        "Londres": "rainy urban atmosphere, contemporary gallery",
        "Berlín": "industrial-chic space, artistic underground",
        "Seúl": "futuristic urban corner, sleek modernity",
        
        # Barrios específicos
        "Palermo": "trendy neighborhood, green urban space",
        "Roma Norte": "artistic district, mid-century architecture",
        "Shibuya": "bustling crossing, urban energy",
        "Shoreditch": "creative district, brick walls and art",
        "Kreuzberg": "alternative urban corner, street culture",
        "Hongdae": "youthful artistic quarter, creative energy"
    }
    
    # Buscar coincidencias en la ubicación
    for key, cue in location_cues.items():
        if key in location:
            return cue
    
    # Fallback genérico
    return "intimate urban space, contemporary setting"


async def generate_image(
    prompt: str,
    state: Dict[str, Any],
    identity_meta: Dict[str, Any],
    model: str = "instantid"
) -> str:
    """
    Genera imagen usando Replicate con InstantID o IP-Adapter FaceID
    
    Args:
        prompt: Descripción de la imagen a generar (se sobrescribirá con prompt visual específico)
        state: Estado actual (emotion, location, etc.)
        identity_meta: Metadata del identity pack
        model: Modelo a usar ("instantid" o "ip-adapter")
        
    Returns:
        str: Ruta local de la imagen guardada
    """
    logger.info(f"Generando imagen con modelo: {model}")
    
    # Construir prompt visual específico
    visual_prompt = build_visual_prompt(state)
    logger.info(f"Prompt visual: {visual_prompt[:100]}...")
    
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
        
        # Obtener modelo desde settings o usar por defecto
        replicate_model = os.getenv("REPLICATE_MODEL", "instantx/instantid")
        
        # Configurar inputs según modelo
        negative_prompt = "blurry, low quality, distorted, bad anatomy, bad proportions, masculine features, heavy makeup"
        
        if "instantid" in replicate_model or model == "instantid":
            inputs = {
                "image": reference_image,
                "prompt": visual_prompt,
                "negative_prompt": negative_prompt,
                "ip_adapter_scale": identity_strength,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "seed": random.randint(1, 1000000)
            }
        else:  # ip-adapter o modelo custom
            inputs = {
                "image": reference_image,
                "prompt": visual_prompt,
                "negative_prompt": negative_prompt,
                "ip_adapter_scale": identity_strength,
                "controlnet_conditioning_scale": style_strength,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "seed": random.randint(1, 1000000)
            }
        
        logger.info(f"Llamando a Replicate: {replicate_model}")
        
        # Ejecutar generación
        output = client.run(replicate_model, input=inputs)
        
        # Obtener URL de imagen generada
        if isinstance(output, list):
            image_url = output[0]
        else:
            image_url = str(output)
        
        logger.info(f"Imagen generada: {image_url[:80]}...")
        
        # Descargar y guardar imagen con estructura de fecha
        local_path = await save_generated_image(image_url)
        
        logger.info(f"Imagen guardada en: {local_path}")
        
        return local_path
        
    except Exception as e:
        logger.error(f"Error al generar imagen: {str(e)}")
        raise Exception(f"Error en generación de imagen: {str(e)}")


async def save_generated_image(image_url: str) -> str:
    """
    Descarga imagen desde URL y la guarda con estructura images/YYYY/MM/DD.png
    
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
        day = now.strftime("%d")
        
        images_dir = Path(settings.DATA_PATH) / "images" / year / month
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Nombre de archivo: DD.png
        filename = f"{day}.png"
        filepath = images_dir / filename
        
        # Si ya existe ese día, agregar timestamp
        if filepath.exists():
            timestamp = now.strftime("%H%M%S")
            filename = f"{day}_{timestamp}.png"
            filepath = images_dir / filename
            logger.info(f"Archivo del día ya existe, usando timestamp: {filename}")
        
        logger.info(f"Descargando imagen a: {filepath}")
        
        # Descargar imagen
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            
            # Guardar imagen como PNG
            with open(filepath, 'wb') as f:
                f.write(response.content)
        
        logger.info(f"✅ Imagen guardada: {filepath}")
        
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
