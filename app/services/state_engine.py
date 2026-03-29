"""
Motor de estado - Gestiona la evolución narrativa del influencer
"""
import json
import os
import random
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.post import Post
from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.text_gen import generate_caption
from app.services.image_gen import generate_image, select_visual_decision
from app.services.identity_metadata_adapter import normalize_identity_metadata
from app.services.publish_instagram import instagram_publisher

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
                metadata = normalize_identity_metadata(json.load(f))
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


def get_recent_posts_context(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Obtiene los posts recientes para contexto en generación
    
    Args:
        db: Sesión de base de datos
        limit: Número de posts recientes a obtener
        
    Returns:
        List[Dict]: Lista de posts recientes con información relevante
    """
    try:
        recent_posts = db.query(Post).order_by(Post.created_at.desc()).limit(limit).all()
        
        context = []
        for post in recent_posts:
            context.append({
                "id": post.id,
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "chapter": post.chapter,
                "emotion_focus": post.emotion_focus,
                "location": post.location,
                "caption": post.caption,
                "image_path": post.image_path,
                "meta": post.meta or {}
            })
        
        logger.info(f"Contexto de {len(context)} posts recientes cargado")
        return context
        
    except Exception as e:
        logger.error(f"Error al obtener contexto de posts: {e}")
        return []


def next_state(
    prev_state: Dict[str, Any],
    feedback: Optional[Dict[str, Any]] = None,
    identity_meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
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
        new_state["chapter"] = _evolve_chapter_by_days(days_elapsed, identity_meta)
    
    # 2. EVOLUCIÓN DE EMOCIÓN (aleatoria ponderada, evita repeticiones)
    if force_emotion:
        new_state["emotion_focus"] = force_emotion
        logger.info(f"Emoción forzada por env: {force_emotion}")
    elif feedback and "emotion" in feedback:
        new_state["emotion_focus"] = feedback["emotion"]
        logger.info(f"Emoción forzada por feedback: {feedback['emotion']}")
    else:
        recent_emotions = meta.get("recent_emotions", []) or []
        new_state["emotion_focus"] = _evolve_emotion(
            prev_state.get("emotion_focus", "curiosidad"),
            identity_meta,
            recent_emotions,
        )
    
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
            prev_state.get("location", "Santiago"),
            identity_meta
        )
    
    # 4. EVOLUCIÓN DE LEARNING GOAL (según capítulo)
    new_state["learning_goal"] = _evolve_learning_goal(new_state["chapter"], identity_meta)
    
    # 5. ACTUALIZAR META
    recent_emotions = (meta.get("recent_emotions", []) or [])[:4]
    recent_emotions.insert(0, new_state["emotion_focus"])
    recent_emotions = recent_emotions[:5]

    new_state["meta"] = {
        **meta,
        "post_count": post_count,
        "days_elapsed": days_elapsed,
        "last_evolution": datetime.now().isoformat(),
        "feedback_applied": bool(feedback),
        "recent_emotions": recent_emotions,
    }
    
    logger.info(f"Nuevo estado: {new_state['chapter']} / {new_state['emotion_focus']} / {new_state['location']}")
    
    return new_state


def _evolve_chapter_by_days(days_elapsed: int, identity_meta: Optional[Dict[str, Any]] = None) -> str:
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
    narrative = ((identity_meta or {}).get("narrative", {}) or {})
    chapter_windows = narrative.get("chapter_windows", []) or []
    if isinstance(chapter_windows, list) and chapter_windows:
        for item in chapter_windows:
            if not isinstance(item, dict):
                continue
            chapter_name = item.get("name")
            min_days = int(item.get("min_days", 0))
            max_days = item.get("max_days")
            if max_days is None:
                if days_elapsed >= min_days and chapter_name:
                    return chapter_name
            else:
                if min_days <= days_elapsed < int(max_days) and chapter_name:
                    return chapter_name

    if days_elapsed < 60:
        return "despertar"
    if days_elapsed < 120:
        return "búsqueda"
    if days_elapsed < 180:
        return "encuentro"
    return "integración"


def _evolve_emotion(
    current_emotion: str,
    identity_meta: Optional[Dict[str, Any]] = None,
    recent_emotions: Optional[List[str]] = None,
) -> str:
    """
    Selecciona la siguiente emoción con aleatoriedad ponderada.
    
    Emociones recientes reciben peso reducido para evitar repeticiones.
    La emoción actual siempre se penaliza para forzar cambio.
    
    Args:
        current_emotion: Emoción actual
        recent_emotions: Emociones de los últimos N posts
        
    Returns:
        str: Siguiente emoción seleccionada
    """
    narrative = ((identity_meta or {}).get("narrative", {}) or {})
    emotion_cycle = narrative.get("emotion_cycle", []) or [
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
    
    if len(emotion_cycle) <= 1:
        return emotion_cycle[0] if emotion_cycle else "curiosidad"

    recent = set(recent_emotions or [])
    recent.add(current_emotion)

    weights = []
    for e in emotion_cycle:
        if e == current_emotion:
            weights.append(0.05)
        elif e in recent:
            weights.append(0.3)
        else:
            weights.append(1.0)

    next_emotion = random.choices(emotion_cycle, weights=weights, k=1)[0]
    logger.debug(f"Emoción: {current_emotion} → {next_emotion} (ponderada)")
    return next_emotion


def _evolve_location_by_arc(
    days_elapsed: int,
    current_location: str,
    identity_meta: Optional[Dict[str, Any]] = None
) -> str:
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
    # Definir arcos de ubicaciones con progresión aproximada (fallback)
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

    narrative = ((identity_meta or {}).get("narrative", {}) or {})
    configured_arcs = narrative.get("location_arcs", []) or []
    if isinstance(configured_arcs, list) and configured_arcs:
        parsed_arcs = []
        for arc in configured_arcs:
            if not isinstance(arc, dict):
                continue
            min_days = int(arc.get("min_days", 0))
            max_days = arc.get("max_days", 999)
            if max_days is None:
                max_days = 999
            locations = arc.get("locations", []) or []
            if not locations:
                continue
            parsed_arcs.append({"range": (min_days, int(max_days)), "locations": locations})
        if parsed_arcs:
            location_arcs = parsed_arcs
    
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


def _evolve_learning_goal(chapter: str, identity_meta: Optional[Dict[str, Any]] = None) -> str:
    """
    Define el learning goal según el capítulo actual
    
    Args:
        chapter: Capítulo actual
        
    Returns:
        str: Learning goal apropiado para el capítulo
    """
    narrative = ((identity_meta or {}).get("narrative", {}) or {})
    chapter_goals = narrative.get("learning_goals", {}) or {
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
        return next_state(prev_state, feedback, self.get_metadata())
    
    def get_metadata(self) -> Dict[str, Any]:
        """Devuelve el metadata cargado"""
        return normalize_identity_metadata(self.metadata)
    
    async def generate_post(
        self, 
        db: Session, 
        trigger_type: str = "manual",
        publish_to_instagram: bool = False
    ) -> Tuple[bool, Optional[Post], Optional[str]]:
        """
        Pipeline completa de generación de post
        
        Args:
            db: Sesión de base de datos
            trigger_type: Tipo de trigger ("manual", "scheduled", "api")
            publish_to_instagram: Si se debe publicar automáticamente en Instagram
            
        Returns:
            Tuple[bool, Optional[Post], Optional[str]]: (success, post, error_message)
        """
        logger.info(f"🚀 Iniciando pipeline de generación (trigger: {trigger_type})")
        
        try:
            # 1. Cargar identity metadata
            logger.info("Paso 1/7: Cargando identity metadata...")
            identity_meta = self.get_metadata()
            
            if not identity_meta:
                logger.warning("Identity metadata vacío, usando valores por defecto")
                identity_meta = {
                    "influencer_name": "Influencer IA",
                    "description": "Un viaje de autodescubrimiento",
                    "style_notes": "fotografía natural y auténtica"
                }
            
            # 2. Obtener estado actual
            logger.info("Paso 2/7: Obteniendo estado actual...")
            current_state = self.get_current_state(db)
            logger.info(f"Estado actual: {current_state.get('chapter')} / {current_state.get('emotion_focus')}")
            
            # 3. Calcular siguiente estado
            logger.info("Paso 3/7: Calculando siguiente estado...")
            new_state = self.next_state(current_state)
            logger.info(f"Nuevo estado: {new_state.get('chapter')} / {new_state.get('emotion_focus')}")
            
            # 4. Obtener contexto de posts recientes
            logger.info("Paso 4/8: Obteniendo contexto de posts recientes...")
            recent_context = get_recent_posts_context(db, limit=3)

            # 4.1 Seleccionar dirección visual con memoria reciente
            recent_visual_decisions = []
            for prev in recent_context:
                prev_meta = (prev.get("meta", {}) or {})
                prev_decision = prev_meta.get("visual_decision")
                if isinstance(prev_decision, dict):
                    recent_visual_decisions.append(prev_decision)

            recent_looks = []
            for prev in recent_context:
                prev_meta = (prev.get("meta", {}) or {})
                prev_look = prev_meta.get("look")
                if isinstance(prev_look, dict):
                    recent_looks.append(prev_look)

            runtime_state = dict(new_state)
            runtime_meta = dict(new_state.get("meta", {}) or {})
            runtime_meta["recent_visual_decisions"] = recent_visual_decisions
            runtime_meta["recent_looks"] = recent_looks
            runtime_state["meta"] = runtime_meta

            selected_visual = select_visual_decision(runtime_state, identity_meta)
            runtime_meta["visual_decision"] = selected_visual
            runtime_state["meta"] = runtime_meta

            # Persistir decisión visual y look reciente para anti-repetición
            new_state["meta"] = {
                **(new_state.get("meta", {}) or {}),
                "visual_decision": selected_visual,
            }
            logger.info(
                "Dirección visual: shot=%s pose=%s scene=%s",
                selected_visual.get("shot_type"),
                selected_visual.get("pose"),
                selected_visual.get("scene_type"),
            )
            
            # 5. Generar caption con contexto
            logger.info("Paso 5/8: Generando caption con OpenAI...")
            caption = generate_caption(runtime_state, identity_meta, recent_context)
            logger.info(f"Caption generado: {len(caption)} caracteres")
            
            # 6. Generar imagen (build_visual_prompt se ejecuta internamente)
            logger.info("Paso 6/7: Generando imagen con Replicate...")
            image_path, source_image_url = await generate_image(
                prompt="",
                state=runtime_state,
                identity_meta=identity_meta,
                model="Nano-banana"
            )
            logger.info(f"Imagen generada: {image_path}")

            # Persist look from runtime meta into new_state for DB storage
            generated_look = runtime_meta.get("look")
            if generated_look:
                new_state["meta"] = {**(new_state.get("meta", {}) or {}), "look": generated_look}
            
            # 7. Guardar en base de datos
            logger.info("Paso 7/7: Guardando en base de datos...")
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
            
            # 9. Actualizar identity pack con imagen generada (opcional)
            logger.info("Paso 9/9: Evaluando actualización del identity pack...")
            await self._update_identity_pack_if_needed(new_post, identity_meta)
            
            # 10. Publicar en Instagram (opcional)
            if publish_to_instagram and instagram_publisher.is_enabled():
                logger.info("📱 Publicando en Instagram...")
                try:
                    media_id = instagram_publisher.publish_post(
                        image_path, caption, source_image_url=source_image_url
                    )
                    
                    if media_id:
                        platforms = {"instagram": media_id}
                        logger.info(f"✅ Publicado en Instagram: {media_id}")

                        # Compartir a Stories después de publicar el post
                        story_id = instagram_publisher.publish_story(
                            image_path, source_image_url=source_image_url
                        )
                        if story_id:
                            platforms["instagram_story"] = story_id
                            logger.info(f"✅ Story publicada: {story_id}")
                        else:
                            logger.warning("⚠️ Fallo al publicar Story")

                        new_post.published_platforms = platforms
                        db.commit()
                    else:
                        logger.warning("⚠️ Fallo al publicar en Instagram")
                except Exception as e:
                    logger.error(f"❌ Error al publicar en Instagram: {str(e)}")
                    # No fallar todo el proceso por error de Instagram
            elif publish_to_instagram and not instagram_publisher.is_enabled():
                logger.info("⏸️ Publicación en Instagram solicitada pero no habilitada")
            
            logger.info(f"🎉 Pipeline completada exitosamente: Post ID {new_post.id}")
            return True, new_post, None
            
        except Exception as e:
            logger.error(f"❌ Error en pipeline de generación: {str(e)}")
            db.rollback()
            return False, None, str(e)
    
    async def _update_identity_pack_if_needed(self, post: Post, identity_meta: Dict[str, Any]) -> None:
        """
        Evalúa si la imagen generada debe agregarse al identity pack
        
        Criterios:
        - Solo cada N posts (configurable)
        - Solo si la imagen es de alta calidad
        - Solo si no hay demasiadas imágenes en el pack
        
        Args:
            post: Post recién generado
            identity_meta: Metadata actual del identity pack
        """
        try:
            # Configuración
            max_identity_images = 8  # Máximo de imágenes en el identity pack
            update_frequency = 5     # Actualizar cada 5 posts
            
            # Verificar si debemos actualizar
            post_count = post.meta.get("post_count", 0) if post.meta else 0
            if post_count % update_frequency != 0:
                logger.info(f"No es momento de actualizar identity pack (post #{post_count})")
                return
            
            # Separar imágenes base de las generadas
            current_images = identity_meta.get("reference_images", [])
            base_images = identity_meta.get("base_images", current_images[:4])  # Primeras 4 son base
            generated_images = [img for img in current_images if img.startswith("generated_")]
            
            # Verificar límite de imágenes generadas (preservando siempre las base)
            max_generated_images = max_identity_images - len(base_images)
            if len(generated_images) >= max_generated_images:
                logger.info(f"Identity pack ya tiene {len(generated_images)} imágenes generadas (máximo: {max_generated_images})")
                return
            
            # Copiar imagen al identity pack
            if post.image_path and os.path.exists(post.image_path):
                identity_pack_dir = Path(settings.IDENTITY_PACK_PATH)
                identity_pack_dir.mkdir(exist_ok=True)
                
                # Nombre para la nueva imagen
                new_image_name = f"generated_{post.id}_{post.created_at.strftime('%Y%m%d')}.png"
                new_image_path = identity_pack_dir / new_image_name
                
                # Copiar imagen
                import shutil
                shutil.copy2(post.image_path, new_image_path)
                
                # Actualizar metadata manteniendo separación base/generadas
                updated_generated_images = generated_images + [new_image_name]
                updated_reference_images = base_images + updated_generated_images
                
                # Cargar y actualizar el archivo JSON
                metadata_path = identity_pack_dir / "identity_metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Actualizar listas separadas (legacy + estructura por proceso)
                    metadata["reference_images"] = updated_reference_images
                    metadata["base_images"] = base_images
                    metadata["generated_images"] = updated_generated_images
                    assets = metadata.get("assets", {}) or {}
                    assets["reference_images"] = updated_reference_images
                    assets["base_images"] = base_images
                    assets["generated_images"] = updated_generated_images
                    metadata["assets"] = assets
                    
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"✅ Identity pack actualizado con nueva imagen: {new_image_name}")
                    logger.info(f"📸 Imágenes base: {len(base_images)}, Generadas: {len(updated_generated_images)}, Total: {len(updated_reference_images)}")
                else:
                    logger.warning("No se encontró archivo identity_metadata.json para actualizar")
            
        except Exception as e:
            logger.error(f"Error al actualizar identity pack: {str(e)}")
            # No fallar el proceso principal por este error


# Instancia singleton (opcional)
state_engine = StateEngine()
