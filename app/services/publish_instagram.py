"""
Servicio para publicación en Instagram
"""
import os
import json
import time
from typing import Optional
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, 
    PleaseWaitFewMinutes, 
    ChallengeRequired,
    RateLimitError
)
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class InstagramPublisher:
    """Servicio para publicar posts en Instagram"""
    
    def __init__(self):
        self.client = None
        self.session_path = Path(settings.DATA_PATH) / "ig_session.json"
        self.enabled = self._check_if_enabled()
        self.max_retries = 3
        self.retry_delay = 60  # segundos
    
    def _check_if_enabled(self) -> bool:
        """Verifica si la publicación en Instagram está habilitada"""
        publish_enabled = os.getenv("PUBLISH_TO_INSTAGRAM", "false").lower() == "true"
        
        if not publish_enabled:
            logger.info("Publicación en Instagram deshabilitada (PUBLISH_TO_INSTAGRAM != true)")
            return False
        
        # Verificar credenciales
        username = settings.INSTAGRAM_USERNAME
        password = settings.INSTAGRAM_PASSWORD
        
        if not username or not password:
            logger.warning("Credenciales de Instagram no configuradas")
            return False
        
        logger.info("Publicación en Instagram habilitada")
        return True
    
    def _load_session(self) -> bool:
        """
        Intenta cargar sesión guardada
        
        Returns:
            bool: True si la sesión se cargó exitosamente
        """
        if not self.session_path.exists():
            logger.info("No hay sesión guardada de Instagram")
            return False
        
        try:
            self.client = Client()
            self.client.load_settings(self.session_path)
            
            # Verificar que la sesión sea válida
            self.client.get_timeline_feed()
            
            logger.info("Sesión de Instagram cargada exitosamente")
            return True
            
        except Exception as e:
            logger.warning(f"No se pudo cargar la sesión guardada: {e}")
            return False
    
    def _save_session(self):
        """Guarda la sesión actual para uso futuro"""
        try:
            # Asegurar que el directorio existe
            self.session_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Guardar sesión
            self.client.dump_settings(self.session_path)
            logger.info(f"Sesión de Instagram guardada en: {self.session_path}")
            
        except Exception as e:
            logger.error(f"Error al guardar sesión: {e}")
    
    def login(self) -> bool:
        """
        Inicia sesión en Instagram
        
        Returns:
            bool: True si el login fue exitoso
        """
        if not self.enabled:
            logger.info("Login omitido: Instagram no habilitado")
            return False
        
        # Intentar cargar sesión existente
        if self._load_session():
            return True
        
        # Login desde cero
        try:
            logger.info(f"Iniciando sesión en Instagram como {settings.INSTAGRAM_USERNAME}...")
            
            self.client = Client()
            self.client.login(
                settings.INSTAGRAM_USERNAME,
                settings.INSTAGRAM_PASSWORD
            )
            
            # Guardar sesión para próxima vez
            self._save_session()
            
            logger.info("Login exitoso en Instagram")
            return True
            
        except LoginRequired:
            logger.error("Instagram requiere login - credenciales inválidas")
            return False
        except ChallengeRequired as e:
            logger.error(f"Instagram requiere verificación adicional: {e}")
            return False
        except Exception as e:
            logger.error(f"Error durante login de Instagram: {e}")
            return False
    
    def publish_post(
        self,
        image_path: str,
        caption: str,
        retry_count: int = 0
    ) -> Optional[str]:
        """
        Publica un post en Instagram con retry básico
        
        Args:
            image_path: Ruta a la imagen a publicar
            caption: Caption del post
            retry_count: Contador interno de reintentos
            
        Returns:
            Optional[str]: Media ID del post publicado o None si falla
        """
        if not self.enabled:
            logger.info("Publicación omitida: Instagram no habilitado")
            return None
        
        # Asegurar login
        if not self.client:
            if not self.login():
                return None
        
        try:
            # Verificar que la imagen existe
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Imagen no encontrada: {image_path}")
            
            logger.info(f"Publicando en Instagram: {os.path.basename(image_path)}")
            logger.info(f"Caption: {caption[:50]}...")
            
            # Publicar foto
            media = self.client.photo_upload(
                path=image_path,
                caption=caption
            )
            
            media_id = str(media.pk)
            logger.info(f"✅ Post publicado exitosamente en Instagram: {media_id}")
            
            return media_id
            
        except PleaseWaitFewMinutes as e:
            logger.warning(f"Instagram rate limit: {e}")
            
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (retry_count + 1)
                logger.info(f"Esperando {wait_time}s antes de reintentar ({retry_count + 1}/{self.max_retries})...")
                time.sleep(wait_time)
                return self.publish_post(image_path, caption, retry_count + 1)
            else:
                logger.error("Máximo de reintentos alcanzado")
                return None
        
        except RateLimitError as e:
            logger.error(f"Rate limit excedido: {e}")
            
            if retry_count < self.max_retries:
                wait_time = 300  # 5 minutos para rate limit
                logger.info(f"Esperando {wait_time}s por rate limit...")
                time.sleep(wait_time)
                return self.publish_post(image_path, caption, retry_count + 1)
            else:
                logger.error("Máximo de reintentos alcanzado por rate limit")
                return None
        
        except LoginRequired:
            logger.warning("Sesión expirada, reintentando login...")
            
            if retry_count < self.max_retries:
                self.client = None
                if self.login():
                    return self.publish_post(image_path, caption, retry_count + 1)
            
            logger.error("No se pudo restablecer la sesión")
            return None
        
        except Exception as e:
            logger.error(f"Error al publicar en Instagram: {str(e)}")
            
            if retry_count < self.max_retries:
                logger.info(f"Reintentando... ({retry_count + 1}/{self.max_retries})")
                time.sleep(self.retry_delay)
                return self.publish_post(image_path, caption, retry_count + 1)
            
            return None
    
    def is_enabled(self) -> bool:
        """Verifica si el servicio está habilitado"""
        return self.enabled


# Instancia singleton
instagram_publisher = InstagramPublisher()
