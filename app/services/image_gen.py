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
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.identity_metadata_adapter import normalize_identity_metadata

logger = get_logger(__name__)

SAFE_IMAGE_DEFAULTS: Dict[str, Any] = {
    "identity_strength": 0.8,
    "style_strength": 0.7,
    "composition_policy": {
        "shot_weights": {"portrait_close": 0.45, "half_body": 0.35, "full_body": 0.20},
        "pose_weights": {"standing": 0.35, "walking": 0.20, "sitting": 0.20, "candid": 0.15, "dynamic": 0.10},
        "scene_weights": {"urban": 0.45, "rural": 0.20, "interior": 0.20, "coastal": 0.10, "mountain": 0.05},
    },
    "mood_controls": {
        "cheerful_boost": ["gentle smile", "warm expression", "soft joy"],
        "neutral_dial": ["calm presence", "contemplative", "serene"],
        "positive_emotions": ["asombro", "ternura", "aceptación", "libertad", "empatía"],
    },
    "generation_defaults": {
        "stable_diffusion": {
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
        },
        "model_input_defaults": {
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "output_format": "png",
            "output_quality": 95,
            "enable_pose_controlnet": False,
            "pose_strength": 0.35,
            "enable_canny_controlnet": False,
            "canny_strength": 0.3,
            "enable_depth_controlnet": False,
            "depth_strength": 0.5,
            "enable_lcm": False,
            "sdxl_weights": "stable-diffusion-xl-base-1.0",
            "scheduler": "EulerDiscreteScheduler",
            "face_detection_input_width": 640,
            "face_detection_input_height": 640,
            "num_outputs": 1,
        },
    },
}


def _pick_from(lst):
    """Helper para muestrear elementos de una lista"""
    import random
    return random.choice(lst) if isinstance(lst, list) and lst else None


def _weighted_choice(weight_map: Dict[str, float]) -> str:
    """Elige una clave basada en pesos positivos."""
    if not weight_map:
        return ""
    items = []
    for key, value in weight_map.items():
        try:
            w = float(value)
        except (TypeError, ValueError):
            w = 0.0
        if w > 0:
            items.append((key, w))
    if not items:
        return next(iter(weight_map.keys()), "")
    keys, weights = zip(*items)
    return random.choices(list(keys), weights=list(weights), k=1)[0]


def _scene_cue(scene_type: str, location: str, identity_meta: Dict[str, Any]) -> str:
    """Construye cue de escena mezclando tipo y ubicación."""
    ig = (identity_meta.get("image_prompt_guidelines", {}) or {})
    base_by_scene = ig.get("scene_type_cues", {}) or {}
    base = base_by_scene.get(scene_type, "contemporary environment with natural details")
    location_hint = _extract_location_cue(location, identity_meta)
    policy = ig.get("location_render_policy", {}) or {}
    include_name = bool(policy.get("use_explicit_place_name_in_image_prompt", False))
    if include_name:
        return f"{base}, {location_hint}, inspired by {location}"
    return f"{base}, {location_hint}"


def _normalize_text(value: str) -> str:
    if not isinstance(value, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def _pick_n(values: Any, n: int) -> list[str]:
    if not isinstance(values, list) or not values:
        return []
    n = max(0, min(n, len(values)))
    if n == 0:
        return []
    return random.sample([str(v) for v in values], k=n)


def _match_location_profile(location: str, identity_meta: Dict[str, Any]) -> Dict[str, Any]:
    ig = (identity_meta.get("image_prompt_guidelines", {}) or {})
    profiles = ig.get("location_profiles", {}) or {}
    if not isinstance(profiles, dict):
        return {}

    location_norm = _normalize_text(location)
    for key, profile in profiles.items():
        key_norm = _normalize_text(str(key))
        aliases = profile.get("aliases", []) if isinstance(profile, dict) else []
        aliases_norm = [_normalize_text(str(a)) for a in aliases if a]
        if key_norm and key_norm in location_norm:
            return profile if isinstance(profile, dict) else {}
        for alias_norm in aliases_norm:
            if alias_norm and alias_norm in location_norm:
                return profile if isinstance(profile, dict) else {}
    return {}


def select_visual_decision(state: Dict[str, Any], identity_meta: Dict[str, Any]) -> Dict[str, str]:
    """
    Selecciona encuadre/pose/escena con aleatoriedad controlada y coherente.
    """
    identity_meta = normalize_identity_metadata(identity_meta)
    state_meta = (state.get("meta", {}) or {})
    composition = (identity_meta.get("composition_policy", {}) or {})

    emotion = state.get("emotion_focus", "curiosidad")
    chapter = state.get("chapter", "despertar")
    location = state.get("location", "ciudad")

    composition_fallback = SAFE_IMAGE_DEFAULTS["composition_policy"]
    shot_weights = composition.get("shot_weights", composition_fallback["shot_weights"])
    pose_weights = composition.get("pose_weights", composition_fallback["pose_weights"])
    scene_weights = composition.get("scene_weights", composition_fallback["scene_weights"])

    # Ajustes narrativos por emoción/capítulo si existen
    emotion_overrides = (composition.get("emotion_overrides", {}) or {}).get(emotion, {}) or {}
    chapter_overrides = (composition.get("chapter_overrides", {}) or {}).get(chapter, {}) or {}

    def _apply_overrides(base: Dict[str, float], override: Dict[str, Any]) -> Dict[str, float]:
        merged = dict(base)
        for key, value in (override or {}).items():
            try:
                merged[key] = float(value)
            except (TypeError, ValueError):
                continue
        return merged

    shot_weights = _apply_overrides(shot_weights, emotion_overrides.get("shot_weights"))
    shot_weights = _apply_overrides(shot_weights, chapter_overrides.get("shot_weights"))
    pose_weights = _apply_overrides(pose_weights, emotion_overrides.get("pose_weights"))
    pose_weights = _apply_overrides(pose_weights, chapter_overrides.get("pose_weights"))
    scene_weights = _apply_overrides(scene_weights, emotion_overrides.get("scene_weights"))
    scene_weights = _apply_overrides(scene_weights, chapter_overrides.get("scene_weights"))

    # Evita repeticiones recientes de encuadre/pose
    no_repeat_window = int(composition.get("no_repeat_window", 4))
    recent = state_meta.get("recent_visual_decisions", []) or []
    if isinstance(recent, list):
        recent = recent[:no_repeat_window]
    else:
        recent = []

    repeated_shots = {d.get("shot_type") for d in recent if isinstance(d, dict)}
    repeated_poses = {d.get("pose") for d in recent if isinstance(d, dict)}

    for key in repeated_shots:
        if key in shot_weights:
            shot_weights[key] = max(float(shot_weights[key]) * 0.3, 0.01)
    for key in repeated_poses:
        if key in pose_weights:
            pose_weights[key] = max(float(pose_weights[key]) * 0.4, 0.01)

    shot_type = _weighted_choice(shot_weights)
    pose = _weighted_choice(pose_weights)
    scene_type = _weighted_choice(scene_weights)

    shot_prompt_map = composition.get("shot_prompt_map", {}) or {}
    pose_prompt_map = composition.get("pose_prompt_map", {}) or {}

    return {
        "shot_type": shot_type or "half_body",
        "pose": pose or "standing",
        "scene_type": scene_type or "urban",
        "shot_prompt": shot_prompt_map.get(shot_type or "half_body", "half-body framing"),
        "pose_prompt": pose_prompt_map.get(pose or "standing", "standing pose"),
        "scene_prompt": _scene_cue(scene_type or "urban", location, identity_meta)
    }


def _pick_avoiding_recent(options: list, recent_values: list) -> str:
    """Pick from options avoiding recently used values when possible."""
    if not options:
        return ""
    available = [o for o in options if o not in recent_values]
    pool = available if available else options
    return random.choice(pool)


def _sample_look(identity_meta: Dict[str, Any], recent_looks: Optional[list] = None) -> Dict[str, str]:
    """
    Muestrea un look completo evitando repeticiones recientes.
    
    Args:
        identity_meta: Metadata del identity pack
        recent_looks: Lista de looks recientes (dicts) para evitar repeticiones
        
    Returns:
        dict: Look muestreado con hair, palette, archetype, etc.
    """
    av = identity_meta.get("appearance_variation", {}) or {}
    lr = identity_meta.get("look_rotation", {}) or {}
    window = int(lr.get("no_repeat_window", 7))

    recent = (recent_looks or [])[:window]
    recent_hair = [lk.get("hair", "") for lk in recent if isinstance(lk, dict)]
    recent_archetype = [lk.get("archetype", "") for lk in recent if isinstance(lk, dict)]
    recent_palette = [lk.get("palette", "") for lk in recent if isinstance(lk, dict)]

    hair = _pick_avoiding_recent(av.get("hair_presets", []), recent_hair)

    palettes = av.get("palettes", {})
    recent_palette_keys = [lk.get("palette_key", "") for lk in recent if isinstance(lk, dict)]
    palette_key = _pick_avoiding_recent(list(palettes.keys()), recent_palette_keys)
    palette_vals = palettes.get(palette_key, [])
    palette_desc = f"{palette_key}: " + ", ".join(palette_vals) if palette_vals else palette_key

    archetype = _pick_avoiding_recent(av.get("outfit_archetypes", []), recent_archetype)
    texture = _pick_from(av.get("textures"))
    accessory = _pick_from(av.get("accessories"))

    angles = (av.get("camera_lighting", {}) or {}).get("angles", [])
    lighting = (av.get("camera_lighting", {}) or {}).get("lighting", [])
    recent_lighting = [lk.get("lighting", "") for lk in recent if isinstance(lk, dict)]
    angle = _pick_from(angles)
    light = _pick_avoiding_recent(lighting, recent_lighting)

    avoid = ", ".join(av.get("avoid", [])) if av.get("avoid") else ""

    return {
        "hair": hair or "",
        "palette": palette_desc or "",
        "palette_key": palette_key or "",
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
                metadata = normalize_identity_metadata(json.load(f))
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
    identity_meta = normalize_identity_metadata(identity_meta)

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
    identity_meta = normalize_identity_metadata(identity_meta)

    emotion = state.get("emotion_focus", "curiosidad")
    location = state.get("location", "ciudad")
    state_meta = (state.get("meta", {}) or {})

    # Obtener configuraciones desde metadata
    pr = (identity_meta.get("photorealism", {}) or {})
    ig = (identity_meta.get("image_prompt_guidelines", {}) or {})
    gd = (identity_meta.get("generation_defaults", {}) or {})

    # Construir boosts de fotorealismo y ánimo
    boosts = []
    
    # Photorealism keywords
    if pr.get("keywords"):
        boosts.append(pr["keywords"])
    
    # Expression pool: pick 2 random expressions per image for variety
    expression_pool = ig.get("expression_pool", ig.get("expression_bias", []))
    if isinstance(expression_pool, list) and expression_pool:
        k = min(2, len(expression_pool))
        boosts.extend(random.sample(expression_pool, k))
    
    # Wardrobe defaults (safety constraints, always included)
    wardrobe_defaults = ig.get("wardrobe_defaults", [])
    if wardrobe_defaults:
        boosts.extend(wardrobe_defaults)

    # Mood controls dinámicos
    mood_controls = (identity_meta.get("mood_controls", {}) or {})
    mood_fallback = SAFE_IMAGE_DEFAULTS["mood_controls"]
    cheerful = mood_controls.get("cheerful_boost", mood_fallback["cheerful_boost"])
    neutral = mood_controls.get("neutral_dial", mood_fallback["neutral_dial"])

    # palabras para "alegría suave" en emociones luminosas
    positive_emotions = set(mood_controls.get("positive_emotions", mood_fallback["positive_emotions"]))
    mood_tags = cheerful if emotion in positive_emotions else neutral

    location_cue = _extract_location_cue(location, identity_meta)
    selected_visual = state_meta.get("visual_decision") if isinstance(state_meta.get("visual_decision"), dict) else {}
    if not selected_visual:
        selected_visual = select_visual_decision(state, identity_meta)

    # Muestrear look dinámico con anti-repetición
    recent_looks = state_meta.get("recent_looks", []) or []
    look = _sample_look(identity_meta, recent_looks)
    
    # Construir prompt base con look dinámico
    base_quality_tags = ig.get(
        "base_quality_tags",
        "portrait or lifestyle photograph, candid feeling, high detail, photorealistic"
    )
    base_prompt = f"""same woman as reference, feminine aesthetic,
                    light olive skin tone, grey-green eyes,
                    hairstyle: {look['hair']},
                    outfit: {look['archetype']} in {look['texture']}, accessory: {look['accessory']},
                    color palette: {look['palette']},
                    camera angle: {look['angle']}, lighting: {look['lighting']},
                    framing: {selected_visual.get('shot_prompt', 'half-body framing')},
                    pose: {selected_visual.get('pose_prompt', 'standing pose')},
                    mood: {", ".join(mood_tags) if mood_tags else "calm presence"},
                    scene: {selected_visual.get('scene_prompt', location_cue)},
                    {base_quality_tags}"""

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
    anti_grey_tags = ig.get("anti_grey_tags", ["avoid monochrome grey outfits", "avoid cold grey palette"])
    if isinstance(anti_grey_tags, str):
        anti_grey_text = anti_grey_tags
    else:
        anti_grey_text = ", ".join([str(x) for x in anti_grey_tags if x])
    if anti_grey_text:
        visual_prompt += f", {anti_grey_text}"

    # Remoción básica de ban_phrases
    for phrase in ban:
        visual_prompt = visual_prompt.replace(phrase, "")

    safe_suffix = ps.get("append_safe_suffix", "")
    if safe_suffix:
        visual_prompt += safe_suffix
    
    # Persist selected look into state meta for anti-repetition tracking
    if isinstance(state_meta, dict):
        state_meta["look"] = look

    logger.info(f"Visual prompt construido: {emotion} / {location_cue} / look: {look['hair']} + {look['archetype']}")
    
    return visual_prompt


def _extract_location_cue(location: str, identity_meta: Dict[str, Any]) -> str:
    """
    Extrae cue visual de la ubicación para el prompt
    
    Args:
        location: Ubicación completa (ej: "Santiago, Barrio Lastarria")
        
    Returns:
        str: Cue visual simplificado
    """
    ig = (identity_meta.get("image_prompt_guidelines", {}) or {})
    policy = ig.get("location_render_policy", {}) or {}
    profile = _match_location_profile(location, identity_meta)
    if profile:
        max_signatures = int(policy.get("max_visual_signatures", 3))
        max_landmarks = int(policy.get("max_landmarks", 1))
        max_street = int(policy.get("max_street_details", 1))

        chunks: list[str] = []
        chunks.extend(_pick_n(profile.get("visual_signatures", []), max_signatures))
        chunks.extend(_pick_n(profile.get("landmarks", []), max_landmarks))
        chunks.extend(_pick_n(profile.get("street_furniture", []), max_street))

        climate = profile.get("climate_light")
        if climate:
            chunks.append(str(climate))

        if chunks:
            return ", ".join(chunks)

    location_cues = ig.get("location_cues", {}) or {}
    
    # Buscar coincidencias en la ubicación
    location_lower = location.lower()
    for key, cue in location_cues.items():
        if str(key).lower() in location_lower:
            return cue
    
    # Fallback genérico
    return ig.get("location_fallback", "intimate urban space, contemporary setting")


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
    identity_meta = normalize_identity_metadata(identity_meta)
    logger.info(f"Generando imagen con modelo: {model}")
    
    # Construir prompt visual específico
    visual_prompt = build_visual_prompt(state, identity_meta)
    logger.info(f"Prompt visual: {visual_prompt[:100]}...")
    
    # Configuración de identity
    identity_strength = identity_meta.get("identity_strength", SAFE_IMAGE_DEFAULTS["identity_strength"])
    style_strength = identity_meta.get("style_strength", SAFE_IMAGE_DEFAULTS["style_strength"])
    
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
        generation_defaults = (identity_meta.get("generation_defaults", {}) or {})
        sd_defaults = (generation_defaults.get("stable_diffusion", {}) or {})
        model_input_defaults = (generation_defaults.get("model_input_defaults", {}) or {})
        safe_sd_defaults = SAFE_IMAGE_DEFAULTS["generation_defaults"]["stable_diffusion"]
        safe_model_defaults = SAFE_IMAGE_DEFAULTS["generation_defaults"]["model_input_defaults"]

        logger.info(f"Llamando a Replicate: {replicate_model}")
        
        # ---- NUEVA RAMA: Nano-Banana ----
        if "nano-banana" in replicate_model:
            inputs = {
                "prompt": visual_prompt,
                "image_input": ref_inputs,
                "negative_prompt": negative_prompt,
            }
            output = client.run(replicate_model, input=inputs)

        # ---- Stable Diffusion "clásico" ----
        elif "stable-diffusion" in replicate_model:
            inputs = {
                "prompt": visual_prompt,
                "negative_prompt": negative_prompt,
                "num_inference_steps": sd_defaults.get("num_inference_steps", safe_sd_defaults["num_inference_steps"]),
                "guidance_scale": sd_defaults.get("guidance_scale", safe_sd_defaults["guidance_scale"]),
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
                "num_inference_steps": over.get("num_inference_steps", model_input_defaults.get("num_inference_steps", safe_model_defaults["num_inference_steps"])),
                "guidance_scale": over.get("guidance_scale", model_input_defaults.get("guidance_scale", safe_model_defaults["guidance_scale"])),
                "ip_adapter_scale": over.get("ip_adapter_scale", identity_strength),
                "controlnet_conditioning_scale": over.get("controlnet_conditioning_scale", style_strength),
                "seed": random.randint(1, 1_000_000),
                "output_format": over.get("output_format", model_input_defaults.get("output_format", safe_model_defaults["output_format"])),
                "output_quality": over.get("output_quality", model_input_defaults.get("output_quality", safe_model_defaults["output_quality"])),
                "enable_pose_controlnet": over.get("enable_pose_controlnet", model_input_defaults.get("enable_pose_controlnet", safe_model_defaults["enable_pose_controlnet"])),
                "pose_strength": over.get("pose_strength", model_input_defaults.get("pose_strength", safe_model_defaults["pose_strength"])),
                "enable_canny_controlnet": over.get("enable_canny_controlnet", model_input_defaults.get("enable_canny_controlnet", safe_model_defaults["enable_canny_controlnet"])),
                "canny_strength": over.get("canny_strength", model_input_defaults.get("canny_strength", safe_model_defaults["canny_strength"])),
                "enable_depth_controlnet": over.get("enable_depth_controlnet", model_input_defaults.get("enable_depth_controlnet", safe_model_defaults["enable_depth_controlnet"])),
                "depth_strength": over.get("depth_strength", model_input_defaults.get("depth_strength", safe_model_defaults["depth_strength"])),
                "enable_lcm": over.get("enable_lcm", model_input_defaults.get("enable_lcm", safe_model_defaults["enable_lcm"])),
                "sdxl_weights": over.get("sdxl_weights", model_input_defaults.get("sdxl_weights", safe_model_defaults["sdxl_weights"])),
                "scheduler": over.get("scheduler", model_input_defaults.get("scheduler", safe_model_defaults["scheduler"])),
                "face_detection_input_width": over.get("face_detection_input_width", model_input_defaults.get("face_detection_input_width", safe_model_defaults["face_detection_input_width"])),
                "face_detection_input_height": over.get("face_detection_input_height", model_input_defaults.get("face_detection_input_height", safe_model_defaults["face_detection_input_height"])),
                "num_outputs": over.get("num_outputs", model_input_defaults.get("num_outputs", safe_model_defaults["num_outputs"])),
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
        
        image_url = _first_image_url_from_output(output)
        if not image_url:
            raise Exception(f"Salida no reconocida del modelo: {type(output)}")
        logger.info(f"Imagen generada: {str(image_url)[:80]}...")
        
        local_path = await save_generated_image(image_url)
        
        logger.info(f"Imagen guardada en: {local_path}")
        
        return local_path, image_url
        
    except Exception as e:
        logger.error(f"Error al generar imagen: {str(e)}")
        raise Exception(f"Error en generación de imagen: {str(e)}")


def _detect_extension(content: bytes, content_type: str = "") -> str:
    """Detect image file extension from magic bytes, falling back to Content-Type."""
    if content[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    ct = content_type.lower().split(";")[0].strip()
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(ct, ".jpg")


async def save_generated_image(image_url: str) -> str:
    """
    Descarga imagen desde URL y la guarda con estructura images/YYYY/MM/DD.png
    
    Args:
        image_url: URL de la imagen generada
        
    Returns:
        str: Ruta local donde se guardó la imagen
    """
    try:
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        
        images_dir = Path(settings.DATA_PATH) / "images" / year / month
        images_dir.mkdir(parents=True, exist_ok=True)
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            content = response.content

        ext = _detect_extension(content, response.headers.get("content-type", ""))

        filename = f"{day}{ext}"
        filepath = images_dir / filename
        
        if filepath.exists():
            timestamp = now.strftime("%H%M%S")
            filename = f"{day}_{timestamp}{ext}"
            filepath = images_dir / filename
            logger.info(f"Archivo del día ya existe, usando timestamp: {filename}")
        
        logger.info(f"Descargando imagen a: {filepath}")
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
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
    ) -> tuple[str, str]:
        """Genera imagen usando el servicio"""
        return await generate_image(prompt, state, self.identity_meta, model)
    
    def reload_identity_config(self):
        """Recarga la configuración de identity"""
        self.identity_meta = load_identity_config()


# Instancia singleton
image_gen_service = ImageGenerationService()
