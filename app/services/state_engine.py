"""
Motor de estado - Gestiona la evolución narrativa del influencer
"""
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
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
                "chapter": last_post.chapter or "despertar",
                "emotion_focus": last_post.emotion_focus or "curiosidad",
                "learning_goal": last_post.learning_goal or "explorar el mundo",
                "location": last_post.location or "Santiago",
                "meta": last_post.meta or {}
            }
            logger.info(f"Estado actual: capítulo='{state['chapter']}', emoción='{state['emotion_focus']}'")
        else:
            # Estado inicial si no hay posts previos
            state = {
                "chapter": "despertar",
                "emotion_focus": "curiosidad",
                "learning_goal": "descubrir el mundo y mi propósito",
                "location": "Santiago",
                "meta": {
                    "post_count": 0,
                    "days_elapsed": 0
                }
            }
            logger.info("No hay posts previos, usando estado inicial")
        
        return state
        
    except Exception as e:
        logger.error(f"Error al obtener estado actual: {e}")
        # Estado por defecto en caso de error
        return {
            "chapter": "despertar",
            "emotion_focus": "curiosidad",
            "learning_goal": "descubrir el mundo",
            "location": "Santiago",
            "meta": {"post_count": 0, "days_elapsed": 0}
        }


def next_state(prev_state: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calcula el siguiente estado aplicando reglas de evolución narrativa
    
    Reglas:
    - Capítulos por ventana de días: 0-59, 60-119, 120-179, 180+
    - Rotación de emociones: 9 emociones en ciclo
    - Ubicaciones por arco narrativo progresivo
    
    Args:
        prev_state: Estado previo (chapter, emotion_focus, learning_goal, location)
        feedback: Feedback opcional para ajustar la evolución
        
    Returns:
        dict: Nuevo estado evolucionado
    """
    logger.info(f"Calculando siguiente estado desde: {prev_state.get('chapter')} / {prev_state.get('emotion_focus')}")
    
    # Estado base copiado del anterior
    new_state = prev_state.copy()
    meta = prev_state.get("meta", {})
    post_count = meta.get("post_count", 0) + 1
    days_elapsed = meta.get("days_elapsed", 0) + 1
    
    # Override via environment variables (para pruebas)
    force_chapter = os.getenv("FORCE_CHAPTER")
    force_emotion = os.getenv("FORCE_EMOTION")
    force_location = os.getenv("FORCE_LOCATION")
    
    # 1. EVOLUCIÓN DE CAPÍTULO (por ventana de días)
    if force_chapter:
        new_state["chapter"] = force_chapter
        logger.info(f"Capítulo forzado por env: {force_chapter}")
    elif feedback and "force_chapter" in feedback:
        new_state["chapter"] = feedback["force_chapter"]
        logger.info(f"Capítulo forzado por feedback: {feedback['force_chapter']}")
    else:
        new_state["chapter"] = _evolve_chapter_by_days(days_elapsed)
    
    # 2. EVOLUCIÓN DE EMOCIÓN (ciclo de 9 emociones)
    if force_emotion:
        new_state["emotion_focus"] = force_emotion
        logger.info(f"Emoción forzada por env: {force_emotion}")
    elif feedback and "emotion" in feedback:
        new_state["emotion_focus"] = feedback["emotion"]
        logger.info(f"Emoción forzada por feedback: {feedback['emotion']}")
    else:
        new_state["emotion_focus"] = _evolve_emotion(prev_state.get("emotion_focus", "curiosidad"))
    
    # 3. EVOLUCIÓN DE UBICACIÓN (arco narrativo geográfico)
    if force_location:
        new_state["location"] = force_location
        logger.info(f"Ubicación forzada por env: {force_location}")
    elif feedback and "location" in feedback:
        new_state["location"] = feedback["location"]
        logger.info(f"Ubicación forzada por feedback: {feedback['location']}")
    else:
        new_state["location"] = _evolve_location_by_arc(
            days_elapsed, 
            prev_state.get("location", "Santiago")
        )
    
    # 4. EVOLUCIÓN DE LEARNING GOAL (según capítulo)
    new_state["learning_goal"] = _evolve_learning_goal(new_state["chapter"])
    
    # 5. ACTUALIZAR META
    new_state["meta"] = {
        **meta,
        "post_count": post_count,
        "days_elapsed": days_elapsed,
        "last_evolution": datetime.now().isoformat(),
        "feedback_applied": bool(feedback)
    }
    
    logger.info(f"Nuevo estado: {new_state['chapter']} / {new_state['emotion_focus']} / {new_state['location']}")
    
    return new_state


def _evolve_chapter_by_days(days_elapsed: int) -> str:
    """
    Evoluciona el capítulo según ventanas de días
    
    Ventanas:
    - Días 0-59: despertar
    - Días 60-119: búsqueda
    - Días 120-179: encuentro
    - Días 180+: integración
    
    Args:
        days_elapsed: Días transcurridos desde el inicio
        
    Returns:
        str: Capítulo correspondiente
    """
    if days_elapsed < 60:
        return "despertar"
    elif days_elapsed < 120:
        return "búsqueda"
    elif days_elapsed < 180:
        return "encuentro"
    else:
        return "integración"


def _evolve_emotion(current_emotion: str) -> str:
    """
    Rotación de emociones en ciclo de 9
    
    Ciclo emocional:
    curiosidad → asombro → confusión → empatía → ternura → 
    soledad → memoria → aceptación → libertad → (ciclo)
    
    Args:
        current_emotion: Emoción actual
        
    Returns:
        str: Siguiente emoción en el ciclo
    """
    emotion_cycle = [
        "curiosidad",
        "asombro",
        "confusión",
        "empatía",
        "ternura",
        "soledad",
        "memoria",
        "aceptación",
        "libertad"
    ]
    
    try:
        current_index = emotion_cycle.index(current_emotion)
        # Avanzar a la siguiente emoción (con ciclo)
        next_index = (current_index + 1) % len(emotion_cycle)
        next_emotion = emotion_cycle[next_index]
        logger.debug(f"Emoción: {current_emotion} → {next_emotion}")
        return next_emotion
    except ValueError:
        # Si la emoción actual no está en el ciclo, empezar desde el inicio
        logger.warning(f"Emoción '{current_emotion}' no en ciclo, reiniciando desde curiosidad")
        return emotion_cycle[0]


def _evolve_location_by_arc(days_elapsed: int, current_location: str) -> str:
    """
    Evoluciona la ubicación siguiendo un arco narrativo geográfico
    
    Arco de viaje:
    Santiago → costa chilena → sur de Chile → 
    Buenos Aires/CDMX/Tokio → Londres/Berlín/Seúl
    
    Progresión flexible basada en días, sin fechas exactas
    
    Args:
        days_elapsed: Días transcurridos
        current_location: Ubicación actual
        
    Returns:
        str: Nueva ubicación según el arco
    """
    # Definir arcos de ubicaciones con progresión aproximada
    location_arcs = [
        # Fase 1: Chile (días 0-45)
        {
            "range": (0, 15),
            "locations": ["Santiago, Barrio Lastarria", "Santiago, Cerro San Cristóbal", "Santiago, Barrio Italia"]
        },
        {
            "range": (15, 30),
            "locations": ["Valparaíso", "Viña del Mar", "Concón"]
        },
        {
            "range": (30, 45),
            "locations": ["Puerto Varas", "Chiloé", "Pucón"]
        },
        # Fase 2: Sur austral (días 45-75)
        {
            "range": (45, 60),
            "locations": ["Patagonia chilena", "Torres del Paine", "Coyhaique"]
        },
        {
            "range": (60, 75),
            "locations": ["El Calafate", "Ushuaia", "Puerto Natales"]
        },
        # Fase 3: Latinoamérica y Asia (días 75-120)
        {
            "range": (75, 90),
            "locations": ["Buenos Aires, Palermo", "Buenos Aires, San Telmo", "Montevideo"]
        },
        {
            "range": (90, 105),
            "locations": ["Ciudad de México, Roma Norte", "Ciudad de México, Coyoacán", "Oaxaca"]
        },
        {
            "range": (105, 120),
            "locations": ["Tokio, Shibuya", "Tokio, Shinjuku", "Kioto"]
        },
        # Fase 4: Europa y Asia avanzada (días 120-180+)
        {
            "range": (120, 140),
            "locations": ["Londres, Shoreditch", "Londres, Camden", "Edimburgo"]
        },
        {
            "range": (140, 160),
            "locations": ["Berlín, Kreuzberg", "Berlín, Mitte", "Ámsterdam"]
        },
        {
            "range": (160, 999),
            "locations": ["Seúl, Gangnam", "Seúl, Hongdae", "Busan"]
        }
    ]
    
    # Encontrar el arco correspondiente a los días actuales
    for arc in location_arcs:
        min_days, max_days = arc["range"]
        if min_days <= days_elapsed < max_days:
            locations = arc["locations"]
            # Rotar dentro de las ubicaciones del arco
            try:
                current_index = locations.index(current_location)
                next_index = (current_index + 1) % len(locations)
                next_location = locations[next_index]
            except ValueError:
                # Si la ubicación actual no está en este arco, tomar la primera
                next_location = locations[0]
            
            logger.debug(f"Ubicación: {current_location} → {next_location} (día {days_elapsed})")
            return next_location
    
    # Si estamos más allá de todos los arcos, quedarse en la última fase
    return "Seúl, Hongdae"


def _evolve_learning_goal(chapter: str) -> str:
    """
    Define el learning goal según el capítulo actual
    
    Args:
        chapter: Capítulo actual
        
    Returns:
        str: Learning goal apropiado para el capítulo
    """
    chapter_goals = {
        "despertar": "descubrir quién soy y qué busco en este mundo",
        "búsqueda": "encontrar conexiones auténticas y mi voz interior",
        "encuentro": "integrar experiencias y comprender mi propósito",
        "integración": "compartir aprendizajes y crear significado desde la experiencia"
    }
    
    goal = chapter_goals.get(chapter, "explorar y aprender del mundo")
    return goal


def calculate_days_elapsed(db: Session) -> int:
    """
    Calcula días transcurridos desde el primer post
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        int: Número de días desde el primer post
    """
    try:
        first_post = db.query(Post).order_by(Post.created_at.asc()).first()
        
        if not first_post:
            return 0
        
        days = (datetime.now() - first_post.created_at).days
        return max(0, days)
        
    except Exception as e:
        logger.error(f"Error al calcular días transcurridos: {e}")
        return 0


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
        state = get_current_state(db)
        
        # Recalcular days_elapsed basado en la DB real
        days_elapsed = calculate_days_elapsed(db)
        state["meta"]["days_elapsed"] = days_elapsed
        
        return state
    
    def next_state(self, prev_state: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calcula el siguiente estado"""
        return next_state(prev_state, feedback)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Devuelve el metadata cargado"""
        return self.metadata


# Instancia singleton (opcional)
state_engine = StateEngine()
