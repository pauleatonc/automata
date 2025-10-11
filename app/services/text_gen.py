"""
Servicio para generación de texto con OpenAI
"""
from openai import OpenAI
from typing import Dict, Any
from datetime import datetime
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def generate_caption(state: Dict[str, Any], identity_meta: Dict[str, Any]) -> str:
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
    logger.info(f"Generando caption para: {state.get('chapter')} / {state.get('emotion_focus')}")
    
    # Extraer información del estado
    chapter = state.get("chapter", "despertar")
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
    
    # Obtener tema del día (basado en día del año)
    daily_theme = _get_daily_theme()
    
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
- Propósito interior: {goal}

TEMA DEL DÍA: {daily_theme}

REFERENCIAS ESTÉTICAS:
- Estilo visual: {style_notes}
- Paleta emocional: {palette_desc}

INSTRUCCIONES ESPECÍFICAS:
- Longitud: exactamente entre 50 y 90 palabras
- Idioma: español
- Tono: poético, íntimo, reflexivo
- Perspectiva: primera persona
- NO incluir hashtags
- NO usar emojis
- Evocar la emoción "{emotion}" de manera sutil y lírica
- Conectar orgánicamente con el tema "{daily_theme}"
- Sentir como un fragmento de diario personal
- Dejar espacio para la interpretación del lector

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
                    "content": "Eres una escritora lírica que crea micro-narrativas íntimas. Tu estilo es poético pero accesible, profundo pero no pretencioso. Escribes como si compartieras un secreto con un amigo cercano."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.85,
            max_tokens=200,
            presence_penalty=0.5,
            frequency_penalty=0.4
        )
        
        caption = response.choices[0].message.content.strip()
        
        # Validar longitud
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
    logger.info(f"Generando image prompt para: {state.get('location')} / {state.get('emotion_focus')}")
    
    emotion = state.get("emotion_focus", "curiosidad")
    location = state.get("location", "ciudad")
    chapter = state.get("chapter", "despertar")
    
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
soft natural lighting, {color_desc}, depth of field,
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
