"""
Utilidades para manejo de archivos e imágenes
"""
import os
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional, Union
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def get_dated_path(base_dir: str, filename: str, date: Optional[datetime] = None) -> str:
    """
    Genera una ruta organizada por fecha: base_dir/YYYY/MM/filename
    
    Args:
        base_dir: Directorio base
        filename: Nombre del archivo
        date: Fecha para organizar (si es None, usa fecha actual)
        
    Returns:
        str: Ruta completa con estructura de fecha
    """
    if date is None:
        date = datetime.now()
    
    year = date.strftime("%Y")
    month = date.strftime("%m")
    
    path = Path(base_dir) / year / month / filename
    return str(path)


def get_timestamped_filename(base_name: str, extension: str = ".png") -> str:
    """
    Genera un nombre de archivo con timestamp
    
    Args:
        base_name: Nombre base del archivo
        extension: Extensión del archivo (incluir el punto)
        
    Returns:
        str: Nombre de archivo con timestamp: base_name_YYYYMMDD_HHMMSS.extension
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}{extension}"


def get_daily_filename(prefix: str = "post", extension: str = ".png") -> str:
    """
    Genera nombre de archivo basado en el día: prefix_DD.extension
    
    Args:
        prefix: Prefijo del archivo
        extension: Extensión del archivo
        
    Returns:
        str: Nombre de archivo: prefix_DD.extension
    """
    day = datetime.now().strftime("%d")
    return f"{prefix}_{day}{extension}"


def ensure_dir(directory: Union[str, Path]) -> Path:
    """
    Asegura que un directorio existe, creándolo si es necesario
    
    Args:
        directory: Ruta del directorio a crear
        
    Returns:
        Path: Objeto Path del directorio
    """
    dir_path = Path(directory)
    
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directorio asegurado: {dir_path}")
    except Exception as e:
        logger.error(f"Error al crear directorio {dir_path}: {e}")
        raise
    
    return dir_path


def get_images_dir(with_date_structure: bool = True) -> Path:
    """
    Obtiene el directorio para guardar imágenes generadas
    
    Args:
        with_date_structure: Si es True, incluye estructura YYYY/MM
        
    Returns:
        Path: Directorio de imágenes
    """
    base_dir = Path(settings.DATA_PATH) / "images"
    
    if with_date_structure:
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        images_dir = base_dir / year / month
    else:
        images_dir = base_dir
    
    return ensure_dir(images_dir)


async def download_image_from_url(
    url: str,
    save_path: Optional[str] = None,
    filename: Optional[str] = None,
    timeout: int = 60
) -> str:
    """
    Descarga una imagen desde una URL y la guarda localmente
    
    Args:
        url: URL de la imagen a descargar
        save_path: Ruta completa donde guardar (si se proporciona, ignora filename)
        filename: Nombre del archivo (se guardará en images/YYYY/MM/)
        timeout: Timeout en segundos para la descarga
        
    Returns:
        str: Ruta local donde se guardó la imagen
    """
    try:
        logger.info(f"Descargando imagen desde: {url[:80]}...")
        
        # Determinar ruta de guardado
        if save_path:
            file_path = Path(save_path)
            ensure_dir(file_path.parent)
        else:
            if not filename:
                filename = get_daily_filename("post", ".png")
            
            images_dir = get_images_dir(with_date_structure=True)
            file_path = images_dir / filename
            
            # Si el archivo ya existe, agregar timestamp
            if file_path.exists():
                base_name = file_path.stem
                extension = file_path.suffix
                timestamped_name = get_timestamped_filename(base_name, extension)
                file_path = images_dir / timestamped_name
        
        # Descargar imagen
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Guardar imagen
            with open(file_path, 'wb') as f:
                f.write(response.content)
        
        logger.info(f"✅ Imagen descargada: {file_path}")
        return str(file_path)
        
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP al descargar imagen: {e}")
        raise Exception(f"Error al descargar imagen: {str(e)}")
    except Exception as e:
        logger.error(f"Error al descargar/guardar imagen: {e}")
        raise Exception(f"Error al guardar imagen: {str(e)}")


def save_image_from_bytes(
    image_bytes: bytes,
    filename: Optional[str] = None,
    save_path: Optional[str] = None
) -> str:
    """
    Guarda una imagen desde bytes
    
    Args:
        image_bytes: Bytes de la imagen
        filename: Nombre del archivo (opcional)
        save_path: Ruta completa donde guardar (opcional)
        
    Returns:
        str: Ruta donde se guardó la imagen
    """
    try:
        # Determinar ruta de guardado
        if save_path:
            file_path = Path(save_path)
            ensure_dir(file_path.parent)
        else:
            if not filename:
                filename = get_daily_filename("post", ".png")
            
            images_dir = get_images_dir(with_date_structure=True)
            file_path = images_dir / filename
            
            # Si existe, agregar timestamp
            if file_path.exists():
                base_name = file_path.stem
                extension = file_path.suffix
                timestamped_name = get_timestamped_filename(base_name, extension)
                file_path = images_dir / timestamped_name
        
        # Guardar imagen
        with open(file_path, 'wb') as f:
            f.write(image_bytes)
        
        logger.info(f"✅ Imagen guardada: {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"Error al guardar imagen desde bytes: {e}")
        raise Exception(f"Error al guardar imagen: {str(e)}")


def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """
    Obtiene el tamaño de un archivo en MB
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        float: Tamaño en megabytes
    """
    try:
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return round(size_mb, 2)
    except Exception as e:
        logger.error(f"Error al obtener tamaño de archivo: {e}")
        return 0.0


def clean_old_images(days_to_keep: int = 30) -> int:
    """
    Limpia imágenes antiguas del directorio
    
    Args:
        days_to_keep: Número de días a mantener
        
    Returns:
        int: Número de archivos eliminados
    """
    from datetime import timedelta
    
    deleted_count = 0
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    try:
        images_base = Path(settings.DATA_PATH) / "images"
        
        if not images_base.exists():
            return 0
        
        for file_path in images_base.rglob("*.png"):
            try:
                # Obtener fecha de modificación
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if mod_time < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Eliminada imagen antigua: {file_path.name}")
                    
            except Exception as e:
                logger.warning(f"Error al eliminar {file_path}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Limpieza completada: {deleted_count} imágenes eliminadas")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error en limpieza de imágenes: {e}")
        return deleted_count


def list_recent_images(limit: int = 10) -> list[dict]:
    """
    Lista las imágenes más recientes
    
    Args:
        limit: Número máximo de imágenes a listar
        
    Returns:
        list: Lista de diccionarios con info de las imágenes
    """
    images_info = []
    
    try:
        images_base = Path(settings.DATA_PATH) / "images"
        
        if not images_base.exists():
            return []
        
        # Obtener todos los archivos de imagen
        image_files = list(images_base.rglob("*.png"))
        image_files.extend(list(images_base.rglob("*.jpg")))
        image_files.extend(list(images_base.rglob("*.jpeg")))
        
        # Ordenar por fecha de modificación (más recientes primero)
        image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Tomar solo los últimos N
        for file_path in image_files[:limit]:
            stat = file_path.stat()
            images_info.append({
                "path": str(file_path),
                "name": file_path.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
    except Exception as e:
        logger.error(f"Error al listar imágenes: {e}")
    
    return images_info
