"""
Servicio para generación de texto con OpenAI
"""
from openai import OpenAI
from typing import Dict, Any, List, Optional
from datetime import datetime
import random
import unicodedata
from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.identity_metadata_adapter import normalize_identity_metadata

logger = get_logger(__name__)


def _normalize_text(value: str) -> str:
    if not isinstance(value, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


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


def _pick_one(values: Any) -> str:
    if isinstance(values, list) and values:
        return str(random.choice(values))
    return ""


def _build_location_anchor(location: str, identity_meta: Dict[str, Any]) -> str:
    profile = _match_location_profile(location, identity_meta)
    if not profile:
        return "ancla el lugar con 2-3 detalles sensoriales concretos (textura, luz, sonido, objeto urbano/rural)"

    pieces = []
    for key in ("visual_signatures", "landmarks", "street_furniture", "sensory_tokens"):
        picked = _pick_one(profile.get(key, []))
        if picked:
            pieces.append(picked)
    climate = profile.get("climate_light")
    if climate:
        pieces.append(str(climate))
    if not pieces:
        return "ancla el lugar con 2-3 detalles sensoriales concretos (textura, luz, sonido, objeto urbano/rural)"
    return "; ".join(pieces[:4])


def generate_caption(state: Dict[str, Any], identity_meta: Dict[str, Any], recent_context: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Genera un caption poético e íntimo para el post
    
    Construye prompt con: identidad, capítulo, emoción, tema del día, referencias estéticas
    Produce 50-90 palabras máx, en español, sin hashtags, tono poético íntimo
    
    Args:
        state: Estado actual con chapter, emotion_focus, learning_goal, location
        identity_meta: Metadata del identity pack (nombre, estilo, paleta, etc.)
        
    Returns:
        str: Caption en español, 50-90 palabras, sin hashtags, poético e íntimo
    """
    identity_meta = normalize_identity_metadata(identity_meta)
    logger.info(f"Generando caption para: {state.get('chapter')} / {state.get('emotion_focus')}")
    
    # Extraer información del estado
    chapter = state.get("chapter", "despertar")
    visual_decision = ((state.get("meta", {}) or {}).get("visual_decision", {}) or {})
    emotion = state.get("emotion_focus", "curiosidad")
    goal = state.get("learning_goal", "explorar el mundo")
    location = state.get("location", "ciudad")
    
    # Extraer información del identity metadata
    influencer_name = identity_meta.get("influencer_name", "Narradora")
    description = identity_meta.get("description", "Un viaje de autodescubrimiento")
    style_notes = identity_meta.get("style_notes", "fotografía natural y contemplativa")
    palette = identity_meta.get("palette", {})
    palette_desc = palette.get("mood", "sereno") if isinstance(palette, dict) else "sereno"
    voice_tone = identity_meta.get("voice_tone", "poético e íntimo")
    location_anchor = _build_location_anchor(location, identity_meta)
    ig = (identity_meta.get("image_prompt_guidelines", {}) or {})
    location_policy = ig.get("location_render_policy", {}) or {}
    mention_place_name = bool(location_policy.get("use_explicit_place_name_in_caption", False))
    
    # Reglas de caption desde JSON
    cap_rules = (identity_meta.get("narrative_rules", {}) or {}).get("caption_guidelines", {}) or {}
    must_include = cap_rules.get("must_include", [])
    forbidden = cap_rules.get("forbidden", [])
    emoji_policy = cap_rules.get("emoji_policy", "0–1 emoji opcional; nunca como remate principal")
    humor_profile = ((identity_meta.get("persona", {}) or {}).get("personality", {}) or {}).get("humor_profile", {}) or {}
    
    # Obtener tema del día (basado en día del año)
    daily_theme = _get_daily_theme()
    
    # Construir contexto de posts recientes
    context_text = ""
    if recent_context and len(recent_context) > 0:
        context_text = "\n\nCONTEXTO DE POSTS RECIENTES:\n"
        for i, post in enumerate(recent_context[:3], 1):
            context_text += f"Post {i} ({post.get('created_at', 'fecha desconocida')[:10]}):\n"
            context_text += f"- Capítulo: {post.get('chapter', 'N/A')}\n"
            context_text += f"- Emoción: {post.get('emotion_focus', 'N/A')}\n"
            context_text += f"- Ubicación: {post.get('location', 'N/A')}\n"
            context_text += f"- Caption: {post.get('caption', 'N/A')[:100]}...\n\n"
    
    # Construir el prompt
    prompt = f"""Escribe un caption poético e íntimo para una publicación de Instagram.

IDENTIDAD:
- Voz narrativa: {influencer_name}
- Esencia: {description}
- Tono de voz: {voice_tone}

MOMENTO NARRATIVO:
- Capítulo actual: {chapter}
- Emoción predominante: {emotion}
- Ubicación: {location}
- Ancla sensorial del lugar: {location_anchor}
- Propósito interior: {goal}

TEMA DEL DÍA: {daily_theme}{context_text}

REFERENCIAS ESTÉTICAS:
- Estilo visual: {style_notes}
- Paleta emocional: {palette_desc}

INSTRUCCIONES ESPECÍFICAS:
- Longitud: 50–80 palabras
- Idioma: español
- Tono: poético, íntimo, reflexivo, con humor seco sutil (no solemne)
- Perspectiva: primera persona
- NO incluir hashtags
- Debe incluir: 1 micro-escena concreta (objeto/gesto/lugar) + 1 línea de observación irónica o autoirónica (máx. 1 línea) + 1 pregunta abierta sin moraleja
- Evitar: autoayuda explícita, clichés motivacionales, metáforas grandilocuentes sin ancla cotidiana
- Emojis: 0–1 como condimento, nunca como remate
- Mostrar el lugar con señales observables (texturas, sonidos, luz, objetos), no solo nombrarlo
- Mencionar el nombre del lugar explícitamente: {"sí, pero solo si fluye natural" if mention_place_name else "no, salvo que sea indispensable"}
- Evocar la emoción "{emotion}" de manera sutil y lírica
- Conectar orgánicamente con el tema "{daily_theme}"
- Sentir como un fragmento de diario personal
- Dejar espacio para la interpretación del lector
- Si hay contexto de posts recientes, crear continuidad narrativa sin repetir exactamente
- Evolucionar naturalmente desde los posts anteriores

El caption debe ser como un susurro compartido, una reflexión privada hecha pública.
Usa imágenes sensoriales y metáforas sutiles."""

    try:
        # Inicializar cliente OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Llamar a la API
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Eres una escritora íntima con humor seco (deadpan) y una ironía amable. Poética pero nada solemne. Evitas grandilocuencias y clichés. SIEMPRE: (a) un detalle cotidiano concreto, (b) UNA línea irónica/autoirónica breve, (c) cierras con una pregunta abierta sin moraleja. 0–1 emoji máximo y nunca como remate."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=1.0,
            max_completion_tokens=200
        )
        
        # Manejar respuesta de OpenAI con mejor logging
        try:
            caption = (response.choices[0].message.content or "").strip()
            logger.info(f"Respuesta inicial de OpenAI: '{caption[:100]}...' (longitud: {len(caption)})")
        except Exception as e:
            logger.error(f"Error al extraer caption de respuesta: {e}")
            caption = ""

        # Forzar formato y longitud mínima
        if not caption or len(caption.split()) < 30:
            logger.warning(f"Caption corto ({len(caption.split())} palabras); reintento con más guía")
            prompt_retry = prompt + (
                "\n\nIMPORTANTE: Escribe exactamente 60–90 palabras, tono íntimo y poético, en español, "
                "sin hashtags, sin emojis, sin listas, en un solo párrafo. "
                "Debe ser una reflexión personal sobre la emoción y ubicación mencionadas."
            )
            
            try:
                resp2 = client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres una escritora íntima con humor seco (deadpan) y una ironía amable. Poética pero nada solemne. Evitas grandilocuencias y clichés. SIEMPRE: (a) un detalle cotidiano concreto, (b) UNA línea irónica/autoirónica breve, (c) cierras con una pregunta abierta sin moraleja. 0–1 emoji máximo y nunca como remate. SIEMPRE responde con texto, nunca con listas o formato especial."
                        },
                        {
                            "role": "user",
                            "content": prompt_retry
                        }
                    ],
                    temperature=1.0,
                    max_completion_tokens=200
                )
                caption = (resp2.choices[0].message.content or "").strip()
                logger.info(f"Respuesta de reintento: '{caption[:100]}...' (longitud: {len(caption)})")
            except Exception as e:
                logger.error(f"Error en reintento de caption: {e}")
                caption = ""

        if not caption:
            # Fallback: generar caption básico
            logger.warning("Generando caption de fallback")
            location_phrase = state.get('location', 'este lugar') if mention_place_name else "este rincón"
            caption = (
                f"En {location_phrase}, con {location_anchor}, la {state.get('emotion_focus', 'emoción')} "
                f"se enreda con la luz del momento y me regala una pausa. "
                f"Mientras busco {state.get('learning_goal', 'conexión')}, todo parece cotidiano y raro a la vez. "
                "¿No te pasa que un detalle mínimo te cambia el día sin pedir permiso?"
            )
        
        # Sanitizer de texto post-generación
        ps = (identity_meta.get("prompt_sanitizer", {}) or {})
        ban = set(ps.get("ban_phrases", []))
        rep = ps.get("replace_map", {}) or {}

        for k, v in rep.items():
            caption = caption.replace(k, v)
        for phrase in ban:
            caption = caption.replace(phrase, "")

        # Asegura requisitos mínimos (detalle + ironía + pregunta)
        def _has_question(txt): 
            return "?" in txt
        def _has_deadpan(txt):
            import re
            return bool(re.search(r"\b(irónico|ironía|al menos|claro que no|qué podría salir mal|en teoría)\b", txt.lower()))
        
        if not _has_question(caption):
            caption += " ¿Y tú, cómo lo ves?"
        
        # Validar longitud final
        word_count = len(caption.split())
        logger.info(f"Caption generado: {word_count} palabras")
        
        if word_count < 45:
            logger.warning(f"Caption corto ({word_count} palabras), bajo rango ideal")
        elif word_count > 95:
            logger.warning(f"Caption largo ({word_count} palabras), sobre rango ideal")
        
        return caption
        
    except Exception as e:
        logger.error(f"Error al generar caption con OpenAI: {str(e)}")
        raise Exception(f"Error al generar caption: {str(e)}")


def _get_daily_theme() -> str:
    """
    Obtiene el tema del día basado en ciclo mensual
    
    Returns:
        str: Tema sugerido para el día
    """
    themes = [
        "luz y sombra",
        "memorias que regresan",
        "gestos cotidianos",
        "espacios intermedios",
        "conversaciones silenciosas",
        "rituales personales",
        "fragmentos de belleza",
        "tiempo suspendido",
        "presencias ausentes",
        "caminos que se bifurcan",
        "ecos interiores",
        "ventanas y umbrales",
        "lo que permanece",
        "transformaciones sutiles",
        "encuentros fortuitos",
        "soledad habitada",
        "pequeñas revelaciones",
        "ciclos y regresos",
        "huellas invisibles",
        "instantes robados",
        "la textura del silencio",
        "geografías internas",
        "lo no dicho",
        "destellos de conexión",
        "respirar el presente",
        "mapas imaginarios",
        "reflejos y superficies",
        "el peso de las cosas",
        "lugares de paso",
        "la música del mundo"
    ]
    
    # Usar día del mes para consistencia
    day_of_month = datetime.now().day
    theme_index = (day_of_month - 1) % len(themes)
    
    return themes[theme_index]


def generate_image_prompt(state: Dict[str, Any], identity_meta: Dict[str, Any]) -> str:
    """
    Genera un prompt para la generación de imagen basado en el estado actual
    
    Args:
        state: Estado actual con chapter, emotion_focus, learning_goal, location
        identity_meta: Metadata del identity pack
        
    Returns:
        str: Prompt detallado para generación de imagen
    """
    identity_meta = normalize_identity_metadata(identity_meta)
    logger.info(f"Generando image prompt para: {state.get('location')} / {state.get('emotion_focus')}")
    
    emotion = state.get("emotion_focus", "curiosidad")
    location = state.get("location", "ciudad")
    chapter = state.get("chapter", "despertar")
    visual_decision = ((state.get("meta", {}) or {}).get("visual_decision", {}) or {})
    
    style_notes = identity_meta.get("style_notes", "fotografía natural")
    palette = identity_meta.get("palette", {})
    
    # Extraer colores de paleta si existen
    if isinstance(palette, dict):
        palette_colors = palette.get("primary", ["tonos cálidos"])
        if isinstance(palette_colors, list):
            color_desc = ", ".join(palette_colors)
        else:
            color_desc = str(palette_colors)
    else:
        color_desc = "tonos naturales"
    
    # Pistas del look para alinear texto/imagen
    av = identity_meta.get("appearance_variation", {}) or {}
    lighting_opt = ", ".join((av.get("camera_lighting", {}) or {}).get("lighting", [])[:1]) or "soft natural lighting"
    
    # Mapeo de emociones a descripciones visuales
    emotion_visuals = {
        "curiosidad": "mirada atenta y abierta, postura exploradora, descubrimiento",
        "asombro": "ojos ampliamente abiertos, momento de revelación, maravilla",
        "confusión": "expresión pensativa, búsqueda interna, incertidumbre",
        "empatía": "mirada cálida y comprensiva, conexión humana",
        "ternura": "suavidad en la expresión, intimidad, delicadeza",
        "soledad": "figura contemplativa, espacio vacío, introspección",
        "memoria": "mirada distante, nostalgia, remembranza",
        "aceptación": "serenidad en el rostro, paz interior, calma",
        "libertad": "apertura, expansión, movimiento fluido"
    }
    
    emotion_visual = emotion_visuals.get(emotion, "expresión auténtica y natural")
    
    # Componer prompt para imagen
    prompt = f"""portrait photograph, {style_notes}, 
cinematic composition, {location}, {emotion_visual},
{lighting_opt}, {color_desc}, depth of field,
{visual_decision.get('shot_prompt', 'natural framing')},
{visual_decision.get('pose_prompt', 'natural pose')},
{visual_decision.get('scene_prompt', 'contextual environment')},
intimate and contemplative mood, authentic moment,
high quality, detailed, photorealistic, 8k"""
    
    logger.info(f"Image prompt generado: {prompt[:100]}...")
    
    return prompt


# Instancia singleton del servicio (opcional)
class TextGenerationService:
    """Servicio de generación de texto (clase opcional)"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    def generate_caption(self, state: Dict[str, Any], identity_meta: Dict[str, Any]) -> str:
        """Genera caption usando la función principal"""
        return generate_caption(state, identity_meta)
    
    def generate_image_prompt(self, state: Dict[str, Any], identity_meta: Dict[str, Any]) -> str:
        """Genera image prompt usando la función principal"""
        return generate_image_prompt(state, identity_meta)


# Instancia singleton
text_gen_service = TextGenerationService()
