"""
Servicio para generación de texto con OpenAI
"""
from openai import OpenAI
from typing import Dict, Any
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def generate_caption(state: Dict[str, Any], identity_meta: Dict[str, Any]) -> str:
    """
    Genera un caption breve y poético para el post
    
    Args:
        state: Estado actual con chapter, emotion_focus, learning_goal, location
        identity_meta: Metadata del identity pack (nombre, estilo, paleta, etc.)
        
    Returns:
        str: Caption en español, 50-90 palabras, coherente con emoción y paleta
    """
    logger.info(f"Generando caption para: {state.get('chapter')} / {state.get('emotion_focus')}")
    
    # Extraer información del estado
    chapter = state.get("chapter", "inicio")
    emotion = state.get("emotion_focus", "curiosidad")
    goal = state.get("learning_goal", "explorar el mundo")
    location = state.get("location", "ciudad")
    
    # Extraer información del identity metadata
    influencer_name = identity_meta.get("influencer_name", "Nuestro personaje")
    style_notes = identity_meta.get("style_notes", "fotografía natural y auténtica")
    themes = identity_meta.get("themes", ["lifestyle", "crecimiento personal"])
    description = identity_meta.get("description", "Influencer en un viaje de autodescubrimiento")
    
    # Construir el prompt
    prompt = f"""Escribe un caption poético y breve para una publicación de Instagram.

Contexto del personaje:
- Nombre/Identidad: {influencer_name}
- Descripción: {description}
- Estilo visual: {style_notes}
- Temas: {", ".join(themes) if isinstance(themes, list) else themes}

Momento narrativo actual:
- Capítulo: {chapter}
- Emoción predominante: {emotion}
- Objetivo de aprendizaje: {goal}
- Ubicación/Escenario: {location}

Requisitos del caption:
- Extensión: 50-90 palabras exactamente
- Idioma: español
- Tono: poético, introspectivo, auténtico
- Debe reflejar la emoción "{emotion}" de manera sutil
- Debe conectar con el objetivo: "{goal}"
- Coherente con el momento "{chapter}" de la historia
- Incluir 2-3 hashtags relevantes al final

El caption debe sentirse natural, como si el personaje estuviera compartiendo un momento genuino de su día.
No uses emojis excesivos. Sé auténtico y conmovedor."""

    try:
        # Inicializar cliente OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Llamar a la API
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un escritor creativo especializado en narrativa visual y storytelling para redes sociales. Escribes captions poéticos, auténticos y emotivos que conectan profundamente con la audiencia."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,
            max_tokens=250,
            presence_penalty=0.6,
            frequency_penalty=0.3
        )
        
        caption = response.choices[0].message.content.strip()
        
        # Validar longitud aproximada
        word_count = len(caption.split())
        logger.info(f"Caption generado: {word_count} palabras")
        
        if word_count < 40:
            logger.warning(f"Caption muy corto ({word_count} palabras), considerado válido pero bajo el rango ideal")
        elif word_count > 120:
            logger.warning(f"Caption largo ({word_count} palabras), considerado válido pero sobre el rango ideal")
        
        return caption
        
    except Exception as e:
        logger.error(f"Error al generar caption con OpenAI: {str(e)}")
        raise Exception(f"Error al generar caption: {str(e)}")


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
    chapter = state.get("chapter", "inicio")
    
    style_notes = identity_meta.get("style_notes", "fotografía natural")
    
    # Mapeo de emociones a descripciones visuales
    emotion_visuals = {
        "curiosidad": "mirada atenta y abierta, postura exploradora",
        "alegría": "sonrisa genuina, energía positiva",
        "sorpresa": "ojos abiertos, expresión de descubrimiento",
        "reflexión": "mirada pensativa, momento contemplativo",
        "determinación": "expresión enfocada, postura firme",
        "nostalgia": "mirada suave, atmósfera melancólica",
        "esperanza": "mirada hacia el horizonte, luz cálida",
        "gratitud": "expresión serena, conexión con el entorno"
    }
    
    # Mapeo de ubicaciones a settings visuales
    location_settings = {
        "ciudad": "entorno urbano moderno, arquitectura contemporánea",
        "parque": "naturaleza verde, espacio abierto, luz natural",
        "café": "interior acogedor, luz suave, ambiente íntimo",
        "playa": "costa, arena, luz dorada, horizonte marino",
        "montaña": "paisaje montañoso, altura, perspectiva amplia",
        "hogar": "interior cálido, espacio personal, comodidad",
        "biblioteca": "estanterías de libros, ambiente tranquilo, luz cálida",
        "mercado": "colores vibrantes, actividad, ambiente cultural"
    }
    
    emotion_visual = emotion_visuals.get(emotion, "expresión auténtica")
    location_setting = location_settings.get(location, "entorno natural")
    
    # Construir prompt para imagen
    prompt = f"""professional portrait photograph, {style_notes}, 
{location_setting}, {emotion_visual},
natural lighting, high quality, detailed, instagram aesthetic,
cinematic composition, depth of field, 8k, photorealistic"""
    
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
