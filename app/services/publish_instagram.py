"""
Servicio para publicación en Instagram
"""
import os
import time
import hmac
import hashlib
from typing import Optional
from pathlib import Path
import httpx
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class InstagramPublisher:
    """Servicio para publicar posts vía Instagram Graph API."""
    
    def __init__(self):
        self.client = httpx.Client(timeout=60.0)
        self.enabled = self._check_if_enabled()
        self.max_retries = 3
        self.retry_delay = 20
        self.max_retry_delay = 180
        self.last_error_code = None
        self.last_error_detail = None
        self.ig_user_id = settings.INSTAGRAM_GRAPH_IG_USER_ID
        self.api_base = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_API_VERSION}"

    def _set_error(self, code: str, detail: str):
        """Guarda estado del último error para diagnóstico."""
        self.last_error_code = code
        self.last_error_detail = detail

    def _clear_error(self):
        self.last_error_code = None
        self.last_error_detail = None

    def _compute_backoff(self, retry_count: int) -> int:
        """Backoff exponencial con tope."""
        wait = self.retry_delay * (2 ** retry_count)
        return min(wait, self.max_retry_delay)
    
    def _check_if_enabled(self) -> bool:
        """Verifica si la publicación en Instagram está habilitada"""
        if not settings.PUBLISH_TO_INSTAGRAM:
            logger.info("Publicación en Instagram deshabilitada (PUBLISH_TO_INSTAGRAM=false)")
            return False
        
        if not settings.INSTAGRAM_GRAPH_ACCESS_TOKEN:
            logger.warning("INSTAGRAM_GRAPH_ACCESS_TOKEN no configurado")
            return False

        if not settings.INSTAGRAM_GRAPH_PUBLIC_BASE_URL:
            logger.warning("INSTAGRAM_GRAPH_PUBLIC_BASE_URL no configurado")
            return False
        
        logger.info("Publicación en Instagram Graph API habilitada")
        return True

    def _build_graph_params(self, extra: Optional[dict] = None) -> dict:
        params = {
            "access_token": settings.INSTAGRAM_GRAPH_ACCESS_TOKEN or "",
        }
        if settings.INSTAGRAM_GRAPH_APP_SECRET and settings.INSTAGRAM_GRAPH_ACCESS_TOKEN:
            proof = hmac.new(
                settings.INSTAGRAM_GRAPH_APP_SECRET.encode("utf-8"),
                msg=settings.INSTAGRAM_GRAPH_ACCESS_TOKEN.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()
            params["appsecret_proof"] = proof
        if extra:
            params.update(extra)
        return params

    def _graph_get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        response = self.client.get(
            f"{self.api_base}{endpoint}",
            params=self._build_graph_params(params),
        )
        response.raise_for_status()
        return response.json()

    def _graph_post(self, endpoint: str, data: Optional[dict] = None) -> dict:
        payload = self._build_graph_params(data or {})
        response = self.client.post(f"{self.api_base}{endpoint}", data=payload)
        response.raise_for_status()
        return response.json()

    def _ensure_ig_user_id(self) -> bool:
        if self.ig_user_id:
            return True
        try:
            result = self._graph_get("/me/accounts", params={
                "fields": "name,instagram_business_account{id,username}",
            })
            pages = result.get("data", []) or []
            for page in pages:
                iba = (page or {}).get("instagram_business_account") or {}
                if iba.get("id"):
                    self.ig_user_id = str(iba["id"])
                    logger.info(
                        "Instagram Graph account detectada: page='%s' ig_user_id='%s'",
                        page.get("name", "unknown"),
                        self.ig_user_id,
                    )
                    return True
            self._set_error("instagram_graph_no_account", "No se encontró instagram_business_account en /me/accounts")
            logger.error("No se encontró cuenta de Instagram Business vinculada al token.")
            return False
        except Exception as e:
            self._set_error("instagram_graph_discovery_error", str(e))
            logger.error(f"Error descubriendo IG User ID: {e}")
            return False

    def _image_url_for_graph(self, image_path: str) -> Optional[str]:
        if image_path.startswith("http://") or image_path.startswith("https://"):
            return image_path

        base = (settings.INSTAGRAM_GRAPH_PUBLIC_BASE_URL or "").rstrip("/")
        if not base:
            self._set_error(
                "instagram_graph_public_base_url_missing",
                "INSTAGRAM_GRAPH_PUBLIC_BASE_URL no configurado",
            )
            return None

        data_images = (Path(settings.DATA_PATH) / "images").resolve()
        image_abs = Path(image_path).resolve()
        try:
            relative = image_abs.relative_to(data_images)
        except Exception:
            self._set_error(
                "instagram_graph_image_path_invalid",
                f"Imagen fuera de DATA_PATH/images: {image_path}",
            )
            return None

        rel_url = str(relative).replace(os.sep, "/")
        return f"{base}/api/v1/files/images/{rel_url}"
    
    def login(self) -> bool:
        """
        Compatibilidad de interfaz: en Graph API solo valida credenciales/token.
        
        Returns:
            bool: True si hay token válido y cuenta IG detectada
        """
        if not self.enabled:
            logger.info("Login omitido: Instagram no habilitado")
            self._set_error("instagram_disabled", "Servicio deshabilitado por configuración")
            return False
        self._clear_error()
        return self._ensure_ig_user_id()
    
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
            self._set_error("instagram_disabled", "Servicio deshabilitado por configuración")
            return None
        self._clear_error()
        
        # Asegurar contexto Graph API válido
        if not self.login():
            return None
        
        try:
            # Verificar que la imagen existe
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

            image_url = self._image_url_for_graph(image_path)
            if not image_url:
                logger.error("No se pudo construir image_url pública para Graph API.")
                return None

            logger.info(f"Publicando en Instagram Graph API: {os.path.basename(image_path)}")
            logger.info(f"Caption: {caption[:50]}...")

            # 1) Crear contenedor de media
            media_resp = self._graph_post(
                f"/{self.ig_user_id}/media",
                data={
                    "image_url": image_url,
                    "caption": caption,
                },
            )
            creation_id = media_resp.get("id")
            if not creation_id:
                raise RuntimeError(f"Respuesta sin creation_id: {media_resp}")

            # 2) Publicar contenedor
            publish_resp = self._graph_post(
                f"/{self.ig_user_id}/media_publish",
                data={"creation_id": creation_id},
            )
            media_id = str(publish_resp.get("id", ""))
            if not media_id:
                raise RuntimeError(f"Respuesta de publicación inválida: {publish_resp}")

            logger.info(f"✅ Post publicado exitosamente en Instagram Graph API: {media_id}")
            
            return media_id

        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response is not None else str(e)
            logger.error(f"Graph API HTTP error ({e.response.status_code}): {body}")
            if e.response is not None and e.response.status_code in (429, 500, 502, 503, 504):
                self._set_error("instagram_graph_transient_http", body)
                if retry_count < self.max_retries:
                    wait_time = self._compute_backoff(retry_count)
                    logger.info(f"Reintentando Graph API en {wait_time}s ({retry_count + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    return self.publish_post(image_path, caption, retry_count + 1)
            else:
                self._set_error("instagram_graph_http_error", body)
            return None

        except Exception as e:
            logger.error(f"Error al publicar en Instagram Graph API: {str(e)}")
            self._set_error("instagram_graph_publish_error", str(e))
            if retry_count < self.max_retries:
                logger.info(f"Reintentando... ({retry_count + 1}/{self.max_retries})")
                time.sleep(self._compute_backoff(retry_count))
                return self.publish_post(image_path, caption, retry_count + 1)
            
            return None
    
    def is_enabled(self) -> bool:
        """Verifica si el servicio está habilitado"""
        return self.enabled

    def get_last_error(self) -> Optional[dict]:
        """Devuelve el último error del publicador para observabilidad."""
        if not self.last_error_code:
            return None
        return {
            "code": self.last_error_code,
            "detail": self.last_error_detail,
        }


# Instancia singleton
instagram_publisher = InstagramPublisher()
