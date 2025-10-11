"""
Motor de estado - Gestiona la evolución narrativa del influencer
"""
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.post import Post
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def load_identity_metadata(path: str) -> Dict[str, Any]:
    """
    Carga el metadata del identity pack
    
    Args:
        path: Ruta al archivo identity_metadata.json
        
    Returns:
        dict: Metadata del identity pack o dict vacío si no existe
    """
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                logger.info(f"Metadata cargado desde {path}")
                return metadata
        else:
            logger.warning(f"Archivo de metadata no encontrado: {path}")
            return {}
    except Exception as e:
        logger.error(f"Error al cargar metadata: {e}")
        return {}


def get_current_state(db: Session) -> Dict[str, Any]:
    """
    Lee el último post y devuelve el estado actual base
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        dict: Estado base con chapter, emotion_focus, learning_goal, location
    """
    try:
        # Obtener el último post
        last_post = db.query(Post).order_by(Post.created_at.desc()).first()
        
        if last_post:
            state = {
                "chapter": last_post.chapter or "inicio",
                "emotion_focus": last_post.emotion_focus or "curiosidad",
                "learning_goal": last_post.learning_goal or "explorar el mundo",
                "location": last_post.location or "ciudad",
                "meta": last_post.meta or {}
            }
            logger.info(f"Estado actual: capítulo='{state['chapter']}', emoción='{state['emotion_focus']}'")
        else:
            # Estado inicial si no hay posts previos
            state = {
                "chapter": "inicio",
                "emotion_focus": "curiosidad",
                "learning_goal": "explorar el mundo",
                "location": "ciudad",
                "meta": {"post_count": 0}
            }
            logger.info("No hay posts previos, usando estado inicial")
        
        return state
        
    except Exception as e:
        logger.error(f"Error al obtener estado actual: {e}")
        # Estado por defecto en caso de error
        return {
            "chapter": "inicio",
            "emotion_focus": "curiosidad",
            "learning_goal": "explorar el mundo",
            "location": "ciudad",
            "meta": {}
        }


def next_state(prev_state: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calcula el siguiente estado aplicando reglas simples de evolución
    
    Args:
        prev_state: Estado previo (chapter, emotion_focus, learning_goal, location)
        feedback: Feedback opcional para ajustar la evolución (ej: {"emotion": "alegría", "force_chapter": "desarrollo"})
        
    Returns:
        dict: Nuevo estado con ligeros cambios
    """
    logger.info(f"Calculando siguiente estado desde: {prev_state.get('chapter')} / {prev_state.get('emotion_focus')}")
    
    # Estado base copiado del anterior
    new_state = prev_state.copy()
    meta = prev_state.get("meta", {})
    post_count = meta.get("post_count", 0) + 1
    
    # Override via environment variables (para pruebas)
    force_chapter = os.getenv("FORCE_CHAPTER")
    force_emotion = os.getenv("FORCE_EMOTION")
    force_location = os.getenv("FORCE_LOCATION")
    
    if force_chapter:
        new_state["chapter"] = force_chapter
        logger.info(f"Capítulo forzado por env: {force_chapter}")
    elif feedback and "force_chapter" in feedback:
        new_state["chapter"] = feedback["force_chapter"]
        logger.info(f"Capítulo forzado por feedback: {feedback['force_chapter']}")
    else:
        # Evolución automática de capítulo según contador
        new_state["chapter"] = _evolve_chapter(prev_state.get("chapter", "inicio"), post_count)
    
    if force_emotion:
        new_state["emotion_focus"] = force_emotion
        logger.info(f"Emoción forzada por env: {force_emotion}")
    elif feedback and "emotion" in feedback:
        new_state["emotion_focus"] = feedback["emotion"]
        logger.info(f"Emoción forzada por feedback: {feedback['emotion']}")
    else:
        # Ligero cambio de emoción (rotación natural)
        new_state["emotion_focus"] = _evolve_emotion(prev_state.get("emotion_focus", "curiosidad"))
    
    if force_location:
        new_state["location"] = force_location
        logger.info(f"Ubicación forzada por env: {force_location}")
    elif feedback and "location" in feedback:
        new_state["location"] = feedback["location"]
        logger.info(f"Ubicación forzada por feedback: {feedback['location']}")
    else:
        # Evolución de ubicación
        new_state["location"] = _evolve_location(prev_state.get("location", "ciudad"))
    
    # Evolución de learning_goal según capítulo
    new_state["learning_goal"] = _evolve_learning_goal(new_state["chapter"])
    
    # Actualizar meta
    new_state["meta"] = {
        **meta,
        "post_count": post_count,
        "last_evolution": datetime.now().isoformat(),
        "feedback_applied": bool(feedback)
    }
    
    logger.info(f"Nuevo estado: capítulo='{new_state['chapter']}', emoción='{new_state['emotion_focus']}'")
    
    return new_state


def _evolve_chapter(current_chapter: str, post_count: int) -> str:
    """
    Evoluciona el capítulo según el número de posts
    
    Reglas simples:
    - Posts 1-5: inicio
    - Posts 6-15: desarrollo
    - Posts 16-25: conflicto
    - Posts 26+: resolución
    """
    chapter_progression = [
        (5, "inicio"),
        (15, "desarrollo"),
        (25, "conflicto"),
        (float('inf'), "resolución")
    ]
    
    for threshold, chapter in chapter_progression:
        if post_count <= threshold:
            return chapter
    
    return current_chapter


def _evolve_emotion(current_emotion: str) -> str:
    """
    Rotación natural de emociones para variedad
    
    Args:
        current_emotion: Emoción actual
        
    Returns:
        str: Nueva emoción
    """
    emotion_cycle = [
        "curiosidad",
        "alegría",
        "sorpresa",
        "reflexión",
        "determinación",
        "nostalgia",
        "esperanza",
        "gratitud"
    ]
    
    try:
        current_index = emotion_cycle.index(current_emotion)
        # Avanzar a la siguiente emoción (con ciclo)
        next_index = (current_index + 1) % len(emotion_cycle)
        return emotion_cycle[next_index]
    except ValueError:
        # Si la emoción actual no está en el ciclo, empezar desde el inicio
        return emotion_cycle[0]


def _evolve_location(current_location: str) -> str:
    """
    Variación de ubicaciones para diversidad visual
    
    Args:
        current_location: Ubicación actual
        
    Returns:
        str: Nueva ubicación
    """
    location_cycle = [
        "ciudad",
        "parque",
        "café",
        "playa",
        "montaña",
        "hogar",
        "biblioteca",
        "mercado"
    ]
    
    try:
        current_index = location_cycle.index(current_location)
        # Rotar ubicación
        next_index = (current_index + 1) % len(location_cycle)
        return location_cycle[next_index]
    except ValueError:
        # Default
        return location_cycle[0]


def _evolve_learning_goal(chapter: str) -> str:
    """
    Define el learning goal según el capítulo actual
    
    Args:
        chapter: Capítulo actual
        
    Returns:
        str: Learning goal apropiado
    """
    chapter_goals = {
        "inicio": "descubrir nuevas experiencias y conectar con el entorno",
        "desarrollo": "profundizar en relaciones y crecer personalmente",
        "conflicto": "enfrentar desafíos y encontrar soluciones creativas",
        "resolución": "integrar aprendizajes y compartir sabiduría"
    }
    
    return chapter_goals.get(chapter, "explorar y aprender del mundo")


# Clase opcional para uso orientado a objetos
class StateEngine:
    """Motor de estado orientado a objetos (opcional)"""
    
    def __init__(self, identity_metadata_path: Optional[str] = None):
        if identity_metadata_path is None:
            identity_metadata_path = os.path.join(
                settings.IDENTITY_PACK_PATH, 
                "identity_metadata.json"
            )
        self.metadata = load_identity_metadata(identity_metadata_path)
    
    def get_current_state(self, db: Session) -> Dict[str, Any]:
        """Obtiene el estado actual"""
        return get_current_state(db)
    
    def next_state(self, prev_state: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calcula el siguiente estado"""
        return next_state(prev_state, feedback)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Devuelve el metadata cargado"""
        return self.metadata


# Instancia singleton (opcional)
state_engine = StateEngine()
