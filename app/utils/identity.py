"""
Utilidades para manejo del identity pack
"""
import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.identity_metadata_adapter import normalize_identity_metadata

logger = get_logger(__name__)


def load_identity_metadata(metadata_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Carga y valida el archivo identity_metadata.json
    
    Args:
        metadata_path: Ruta opcional al archivo metadata. Si no se proporciona,
                      usa la ruta por defecto del settings
    
    Returns:
        dict: Metadata validado del identity pack
    """
    if metadata_path is None:
        metadata_path = os.path.join(settings.IDENTITY_PACK_PATH, "identity_metadata.json")
    
    try:
        if not os.path.exists(metadata_path):
            logger.warning(f"Archivo metadata no encontrado: {metadata_path}")
            return get_default_metadata()
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = normalize_identity_metadata(json.load(f))
        
        # Validar metadata
        validated_metadata = validate_metadata(metadata)
        
        logger.info(f"Identity metadata cargado: {validated_metadata.get('influencer_name', 'Sin nombre')}")
        return validated_metadata
        
    except json.JSONDecodeError as e:
        logger.error(f"Error al parsear JSON: {e}")
        return get_default_metadata()
    except Exception as e:
        logger.error(f"Error al cargar identity metadata: {e}")
        return get_default_metadata()


def validate_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida y completa el metadata con valores por defecto si faltan campos
    
    Args:
        metadata: Metadata a validar
        
    Returns:
        dict: Metadata validado y completo
    """
    default = get_default_metadata()
    
    # Campos requeridos con valores por defecto
    validated = {
        "influencer_name": metadata.get("influencer_name", default["influencer_name"]),
        "description": metadata.get("description", default["description"]),
        "reference_images": metadata.get("reference_images", default["reference_images"]),
        "identity_strength": float(metadata.get("identity_strength", default["identity_strength"])),
        "style_strength": float(metadata.get("style_strength", default["style_strength"])),
        "style_notes": metadata.get("style_notes", default["style_notes"]),
        "themes": metadata.get("themes", default["themes"])
    }
    
    # Validar rangos numéricos
    if not 0 <= validated["identity_strength"] <= 1:
        logger.warning(f"identity_strength fuera de rango [0,1]: {validated['identity_strength']}, usando 0.8")
        validated["identity_strength"] = 0.8
    
    if not 0 <= validated["style_strength"] <= 1:
        logger.warning(f"style_strength fuera de rango [0,1]: {validated['style_strength']}, usando 0.7")
        validated["style_strength"] = 0.7
    
    # Validar que reference_images sea una lista
    if not isinstance(validated["reference_images"], list):
        logger.warning("reference_images no es una lista, convirtiendo")
        validated["reference_images"] = [validated["reference_images"]]
    
    # Campos opcionales
    validated["palette"] = metadata.get("palette", {})
    validated["personality_traits"] = metadata.get("personality_traits", [])
    validated["voice_tone"] = metadata.get("voice_tone", "auténtico y reflexivo")
    
    return validated


def get_default_metadata() -> Dict[str, Any]:
    """
    Devuelve metadata por defecto si no existe archivo
    
    Returns:
        dict: Metadata por defecto
    """
    return {
        "influencer_name": "Influencer IA",
        "description": "Un viaje de autodescubrimiento y crecimiento personal",
        "reference_images": [
            "identity_pack_01.png",
            "identity_pack_02.png"
        ],
        "identity_strength": 0.8,
        "style_strength": 0.7,
        "style_notes": "fotografía natural, luz suave, estética minimalista",
        "themes": ["lifestyle", "introspección", "crecimiento personal"],
        "palette": {
            "primary": ["cálidos", "tierra"],
            "mood": "sereno y contemplativo"
        },
        "personality_traits": ["reflexivo", "curioso", "auténtico"],
        "voice_tone": "poético y genuino"
    }


def get_reference_images() -> List[str]:
    """
    Obtiene las rutas completas a todas las imágenes de referencia disponibles
    
    Returns:
        list: Lista de rutas absolutas a imágenes de referencia
    """
    metadata = load_identity_metadata()
    reference_images = metadata.get("reference_images", [])
    
    image_paths = []
    
    for img_name in reference_images:
        img_path = os.path.join(settings.IDENTITY_PACK_PATH, img_name)
        
        if os.path.exists(img_path):
            image_paths.append(img_path)
            logger.debug(f"Imagen de referencia encontrada: {img_name}")
        else:
            logger.warning(f"Imagen de referencia no encontrada: {img_path}")
    
    # Si no se encuentra ninguna, buscar cualquier imagen en el directorio
    if not image_paths:
        logger.warning("No se encontraron imágenes de referencia listadas, buscando en directorio...")
        image_paths = scan_identity_pack_images()
    
    logger.info(f"Total de imágenes de referencia disponibles: {len(image_paths)}")
    return image_paths


def scan_identity_pack_images() -> List[str]:
    """
    Escanea el directorio identity_pack en busca de imágenes
    
    Returns:
        list: Lista de rutas a imágenes encontradas
    """
    valid_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
    image_paths = []
    
    try:
        identity_dir = Path(settings.IDENTITY_PACK_PATH)
        
        if not identity_dir.exists():
            logger.error(f"Directorio identity_pack no existe: {identity_dir}")
            return []
        
        for file_path in identity_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                image_paths.append(str(file_path))
                logger.debug(f"Imagen encontrada: {file_path.name}")
        
    except Exception as e:
        logger.error(f"Error al escanear identity_pack: {e}")
    
    return image_paths


def select_reference_image(index: Optional[int] = None) -> Optional[str]:
    """
    Selecciona una imagen de referencia específica o aleatoria
    
    Args:
        index: Índice específico de la imagen (0-based). Si es None, selecciona aleatoriamente
        
    Returns:
        Optional[str]: Ruta a la imagen seleccionada o None si no hay imágenes
    """
    images = get_reference_images()
    
    if not images:
        logger.error("No hay imágenes de referencia disponibles")
        return None
    
    if index is not None:
        if 0 <= index < len(images):
            selected = images[index]
        else:
            logger.warning(f"Índice {index} fuera de rango, usando primera imagen")
            selected = images[0]
    else:
        import random
        selected = random.choice(images)
    
    logger.info(f"Imagen de referencia seleccionada: {os.path.basename(selected)}")
    return selected


def verify_identity_pack() -> Dict[str, Any]:
    """
    Verifica la integridad del identity pack
    
    Returns:
        dict: Reporte de verificación
    """
    report = {
        "valid": True,
        "metadata_exists": False,
        "metadata_valid": False,
        "images_found": 0,
        "images_expected": 0,
        "missing_images": [],
        "warnings": []
    }
    
    # Verificar metadata
    metadata_path = os.path.join(settings.IDENTITY_PACK_PATH, "identity_metadata.json")
    report["metadata_exists"] = os.path.exists(metadata_path)
    
    if report["metadata_exists"]:
        try:
            metadata = load_identity_metadata()
            report["metadata_valid"] = True
            
            # Verificar imágenes listadas
            reference_images = metadata.get("reference_images", [])
            report["images_expected"] = len(reference_images)
            
            for img in reference_images:
                img_path = os.path.join(settings.IDENTITY_PACK_PATH, img)
                if os.path.exists(img_path):
                    report["images_found"] += 1
                else:
                    report["missing_images"].append(img)
                    report["warnings"].append(f"Imagen faltante: {img}")
            
        except Exception as e:
            report["metadata_valid"] = False
            report["warnings"].append(f"Error al validar metadata: {str(e)}")
            report["valid"] = False
    else:
        report["warnings"].append("Archivo identity_metadata.json no encontrado")
        report["valid"] = False
    
    # Verificar directorio
    if not os.path.exists(settings.IDENTITY_PACK_PATH):
        report["warnings"].append(f"Directorio identity_pack no existe: {settings.IDENTITY_PACK_PATH}")
        report["valid"] = False
    
    if report["images_found"] == 0:
        report["warnings"].append("No se encontraron imágenes de referencia")
        report["valid"] = False
    
    return report
