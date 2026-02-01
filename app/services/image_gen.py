"""
Servicio para generación de imágenes con Replicate
"""
import replicate
from replicate import files as replicate_files
import json
import os
import random
import httpx
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def _pick_from(lst):
    """Helper para muestrear elementos de una lista"""
    import random
    return random.choice(lst) if isinstance(lst, list) and lst else None


def _sample_look(identity_meta: Dict[str, Any]) -> Dict[str, str]:
    """
    Muestrea un look completo desde appearance_variation y look_rotation
    
    Args:
        identity_meta: Metadata del identity pack
        
    Returns:
        dict: Look muestreado con hair, palette, archetype, etc.
    """
    av = identity_meta.get("appearance_variation", {}) or {}
    lr = identity_meta.get("look_rotation", {}) or {}

    hair = _pick_from(av.get("hair_presets"))
    palettes = av.get("palettes", {})
    palette_key = _pick_from(list(palettes.keys()))
    palette_vals = palettes.get(palette_key, [])
    palette_desc = f"{palette_key}: " + ", ".join(palette_vals) if palette_vals else palette_key

    archetype = _pick_from(av.get("outfit_archetypes"))
    texture = _pick_from(av.get("textures"))
    accessory = _pick_from(av.get("accessories"))

    angles = (av.get("camera_lighting", {}) or {}).get("angles", [])
    lighting = (av.get("camera_lighting", {}) or {}).get("lighting", [])
    angle = _pick_from(angles)
    light = _pick_from(lighting)

    avoid = ", ".join(av.get("avoid", [])) if av.get("avoid") else ""

    return {
        "hair": hair or "",
        "palette": palette_desc or "",
        "archetype": archetype or "",
        "texture": texture or "",
        "accessory": accessory or "",
        "angle": angle or "",
        "lighting": light or "",
        "avoid": avoid
    }


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
    # 1) intento: nivel raíz
    ref = identity_meta.get("reference_images")
    # 2) intento: ruta usada en tu metadata real
    if not ref:
        ref = (identity_meta.get("identity_pack", {})
                          .get("integration_instructions", {})
                          .get("reference_images"))
    # 3) fallback por defecto
    if not ref:
        ref = ["identity_pack_01.png", "identity_pack_02.png"]

    image_paths = []
    for img in ref:
        path = os.path.join(settings.IDENTITY_PACK_PATH, img)
        if os.path.exists(path):
            image_paths.append(path)
        else:
            logger.warning(f"Imagen de referencia no encontrada: {path}")

    if not image_paths:
        logger.error("No se encontraron imágenes de referencia")
    return image_paths


def build_visual_prompt(state: Dict[str, Any], identity_meta: Dict[str, Any]) -> str:
    """
    Construye el prompt visual con características específicas del personaje
    
    Args:
        state: Estado actual con emotion_focus y location
        identity_meta: Metadata del identity pack
        
    Returns:
        str: Prompt detallado para generación de imagen
    """
    emotion = state.get("emotion_focus", "curiosidad")
    location = state.get("location", "ciudad")

    # Obtener configuraciones desde metadata
    pr = (identity_meta.get("photorealism", {}) or {})
    ig = (identity_meta.get("image_prompt_guidelines", {}) or {})
    gd = (identity_meta.get("generation_defaults", {}) or {})

    # Construir boosts de fotorealismo y ánimo
    boosts = []
    
    # Photorealism keywords
    if pr.get("keywords"):
        boosts.append(pr["keywords"])
    
    # Expression bias (siempre incluir para expresiones amables)
    expression_bias = ig.get("expression_bias", [])
    if expression_bias:
        boosts.extend(expression_bias)
    
    # Wardrobe defaults
    wardrobe_defaults = ig.get("wardrobe_defaults", [])
    if wardrobe_defaults:
        boosts.extend(wardrobe_defaults)
    
    # Lighting y framing desde generation_defaults
    if gd.get("lighting_tags"):
        boosts.append(gd["lighting_tags"])
    if gd.get("framing_tags"):
        boosts.append(gd["framing_tags"])

    # Mood controls dinámicos
    mood_controls = (identity_meta.get("mood_controls", {}) or {})
    cheerful = mood_controls.get("cheerful_boost", ["gentle smile", "warm expression", "soft joy"])
    neutral = mood_controls.get("neutral_dial", ["calm presence", "contemplative", "serene"])

    # palabras para "alegría suave" en emociones luminosas
    positive_emotions = {"asombro", "ternura", "aceptación", "libertad", "empatía"}
    mood_tags = cheerful if emotion in positive_emotions else neutral

    location_cue = _extract_location_cue(location)

    # Muestrear look dinámico
    look = _sample_look(identity_meta)
    
    # Construir prompt base con look dinámico
    base_prompt = f"""same woman as reference, feminine aesthetic,
                    light olive skin tone, grey-green eyes,
                    hairstyle: {look['hair']},
                    outfit: {look['archetype']} in {look['texture']}, accessory: {look['accessory']},
                    color palette: {look['palette']},
                    camera angle: {look['angle']}, lighting: {look['lighting']},
                    mood: {", ".join(mood_tags) if mood_tags else "calm presence"},
                    scene: {location_cue},
                    portrait, candid feeling, high detail, photorealistic"""

    # Agregar todos los boosts
    if boosts:
        visual_prompt = f"{base_prompt}, {', '.join(boosts)}"
    else:
        visual_prompt = base_prompt

    # Anti-gris y sanitizer
    ps = (identity_meta.get("prompt_sanitizer", {}) or {})
    ban = set(ps.get("ban_phrases", []))
    replace_map = ps.get("replace_map", {}) or {}

    # Aplica replacements simples
    for k, v in replace_map.items():
        visual_prompt = visual_prompt.replace(k, v)

    # Evita gris monocromo si aparece
    visual_prompt += ", avoid monochrome grey outfits, avoid cold grey palette"

    # Remoción básica de ban_phrases
    for phrase in ban:
        visual_prompt = visual_prompt.replace(phrase, "")

    safe_suffix = ps.get("append_safe_suffix", "")
    if safe_suffix:
        visual_prompt += safe_suffix
    
    logger.info(f"Visual prompt construido: {emotion} / {location_cue} / look: {look['hair']} + {look['archetype']}")
    
    return visual_prompt


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


def _resolve_replicate_model_with_version(client: "replicate.Client", slug: str) -> str:
    """
    Devuelve 'owner/model:<version_id>' si el modelo expone versiones.
    Si el modelo NO expone versiones (p.ej. google/nano-banana), retorna el slug tal cual.
    Acepta 'owner/model', 'owner/model:latest' o 'owner/model:<hash>'.
    """
    # Si ya viene con versión concreta, respetamos
    if ":" in slug:
        owner_model, ver = slug.split(":", 1)
        if ver and ver.lower() != "latest":
            return slug
        slug = owner_model  # forzamos resolución de 'latest'

    # Algunos modelos (p.ej. google/nano-banana) NO exponen versiones
    try:
        model = client.models.get(slug)
        # Puede lanzar 404 "does not expose a list of versions"
        versions = getattr(model, "versions", None)
        if not versions:
            # No hay interfaz de versions → usar slug sin versión
            return slug
        vlist = versions.list()
        if not vlist:
            return slug
        version_id = vlist[0].id
        resolved = f"{slug}:{version_id}"
        logger.info(f"Modelo resuelto a versión: {resolved}")
        return resolved
    except Exception as e:
        logger.warning(f"No se pudo resolver versión para '{slug}' ({e}); usando slug tal cual.")
        return slug


def _first_image_url_from_output(output: Any) -> Optional[str]:
    """
    Extrae la primera URL de imagen de la salida del modelo de Replicate.
    Maneja diferentes formatos: list[str], str, dict con keys como 'image', 'url', 'output', 'images'.
    """
    # Casos comunes: list[str] o str
    if isinstance(output, list) and output and isinstance(output[0], str):
        return output[0]
    if isinstance(output, str):
        return output
    # A veces devuelven dict con 'image' o 'images'
    if isinstance(output, dict):
        for key in ("image", "url", "output"):
            if key in output and isinstance(output[key], str):
                return output[key]
        if "images" in output and isinstance(output["images"], list) and output["images"]:
            if isinstance(output["images"][0], str):
                return output["images"][0]
    # Último recurso: primer str dentro
    if isinstance(output, (list, tuple)):
        for v in output:
            if isinstance(v, str):
                return v
    return None


def _replicate_file_input(path: str, client: "replicate.Client") -> str:
    """
    Devuelve un string utilizable por Replicate como input de archivo:
    - Si la versión del SDK soporta upload: URL temporal (files.upload / files.upload_bytes)
    - Si no: data URL (base64) con el mimetype correcto
    """
    # Intento 1: usar upload del SDK si existe
    try:
        # algunas versiones exponen replicate.files.upload(...)
        from replicate import files as _files
        if hasattr(_files, "upload"):
            with open(path, "rb") as fh:
                return _files.upload(fh)
        if hasattr(_files, "upload_bytes"):
            with open(path, "rb") as fh:
                return _files.upload_bytes(fh.read(), filename=os.path.basename(path))
    except Exception as e:
        # seguimos con data URL
        logger.warning(f"No se pudo usar upload del SDK ({e}); usando data URL.")

    # Intento 2: data URL (siempre funciona)
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"
    return data_url


async def generate_image(
    prompt: str,
    state: Dict[str, Any],
    identity_meta: Dict[str, Any],
    model: str = "Nano-banana"
) -> str:
    """
    Genera imagen usando Replicate con Nano-banana o IP-Adapter FaceID
    
    Args:
        prompt: Descripción de la imagen a generar (se sobrescribirá con prompt visual específico)
        state: Estado actual (emotion, location, etc.)
        identity_meta: Metadata del identity pack
        model: Modelo a usar ("Nano-banana" o "ip-adapter")
        
    Returns:
        str: Ruta local de la imagen guardada
    """
    logger.info(f"Generando imagen con modelo: {model}")
    
    # Construir prompt visual específico
    visual_prompt = build_visual_prompt(state, identity_meta)
    logger.info(f"Prompt visual: {visual_prompt[:100]}...")
    
    # Configuración de identity
    identity_strength = identity_meta.get("identity_strength", 0.8)
    style_strength = identity_meta.get("style_strength", 0.7)
    
    # Obtener imágenes de referencia
    reference_images = get_reference_images(identity_meta)
    if not reference_images:
        raise Exception("No hay imágenes de referencia disponibles")

    # Prepara todas las refs; nano-banana soporta múltiples
    try:
        # Inicializar cliente Replicate
        client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
        
        ref_inputs = []
        for p in reference_images:
            ref_inputs.append(_replicate_file_input(p, client))

        # Para logging, mantén la primera como "principal"
        reference_image_path = reference_images[0]
        logger.info(f"Usando imagen de referencia: {os.path.basename(reference_image_path)}")

        # Resolver modelo (con fallback si no lista versiones)
        raw_slug = os.getenv("REPLICATE_MODEL")
        replicate_model = _resolve_replicate_model_with_version(client, raw_slug)

        # Configurar negative prompt (seguirá aplicando para otros modelos)
        nsfw_cfg = (identity_meta.get("nsfw_filters", {}) or {})
        negative_prompt = nsfw_cfg.get(
            "negative_prompt",
            "nsfw, explicit, sexual, nude, inappropriate, blurry, low quality, distorted, bad anatomy, bad proportions, deformed, extra fingers, heavy makeup, doll-like, waxy skin, plastic skin, overprocessed"
        )
        over = (identity_meta.get("replicate_overrides", {}) or {})

        logger.info(f"Llamando a Replicate: {replicate_model}")
        
        # ---- NUEVA RAMA: Nano-Banana ----
        if "nano-banana" in replicate_model:
            # Nano-Banana solo necesita prompt + image_input (lista)
            inputs = {
                "prompt": visual_prompt,
                "image_input": ref_inputs  # lista de URLs/data-urls
            }
            output = client.run(replicate_model, input=inputs)

        # ---- Stable Diffusion "clásico" ----
        elif "stable-diffusion" in replicate_model:
            inputs = {
                "prompt": visual_prompt,
                "negative_prompt": negative_prompt,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "seed": random.randint(1, 1_000_000),
            }
            output = client.run(replicate_model, input=inputs)

        # ---- Nano-banana / IP-Adapter (rama existente) ----
        else:
            # Mantén la rama existente para instant-id/ip-adapter
            inputs = {
                "image": ref_inputs[0],  # compat: los otros modelos aceptan 1 imagen
                "prompt": visual_prompt,
                "negative_prompt": negative_prompt,
                "num_inference_steps": over.get("num_inference_steps", 30),
                "guidance_scale": over.get("guidance_scale", 7.5),
                "ip_adapter_scale": over.get("ip_adapter_scale", identity_meta.get("identity_strength", 0.8)),
                "controlnet_conditioning_scale": over.get("controlnet_conditioning_scale", identity_meta.get("style_strength", 0.7)),
                "seed": random.randint(1, 1_000_000),
                "output_format": over.get("output_format", "png"),
                "output_quality": over.get("output_quality", 95),
                "enable_pose_controlnet": over.get("enable_pose_controlnet", False),
                "pose_strength": over.get("pose_strength", 0.35),
                "enable_canny_controlnet": over.get("enable_canny_controlnet", False),
                "canny_strength": over.get("canny_strength", 0.3),
                "enable_depth_controlnet": over.get("enable_depth_controlnet", False),
                "depth_strength": over.get("depth_strength", 0.5),
                "enable_lcm": over.get("enable_lcm", False),
                "sdxl_weights": over.get("sdxl_weights", "stable-diffusion-xl-base-1.0"),
                "scheduler": over.get("scheduler", "EulerDiscreteScheduler"),
                "face_detection_input_width": over.get("face_detection_input_width", 640),
                "face_detection_input_height": over.get("face_detection_input_height", 640),
                "num_outputs": over.get("num_outputs", 1),
            }
            try:
                output = client.run(replicate_model, input=inputs)
            except Exception as e:
                logger.error(f"Replicate error: {e}")
                try:
                    m = client.models.get(replicate_model.split(":")[0])
                    v = m.versions.list()[0]
                    schema = getattr(v, "openapi_schema", None) or getattr(v, "input_schema", None)
                    logger.error(f"Schema del modelo: {schema}")
                except Exception as e2:
                    logger.error(f"No se pudo obtener schema: {e2}")
                raise
        
        # Obtener URL de imagen generada con helper robusto
        image_url = _first_image_url_from_output(output)
        if not image_url:
            raise Exception(f"Salida no reconocida del modelo: {type(output)}")
        logger.info(f"Imagen generada: {str(image_url)[:80]}...")
        
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
        async with httpx.AsyncClient(timeout=300.0) as client:
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
        model: str = "Nano-banana"
    ) -> str:
        """Genera imagen usando el servicio"""
        return await generate_image(prompt, state, self.identity_meta, model)
    
    def reload_identity_config(self):
        """Recarga la configuración de identity"""
        self.identity_meta = load_identity_config()


# Instancia singleton
image_gen_service = ImageGenerationService()
