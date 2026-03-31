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
from app.services.instagram_token_manager import InstagramTokenManager

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
        self.token_manager = InstagramTokenManager()

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
        
        if not (settings.INSTAGRAM_GRAPH_ACCESS_TOKEN or (Path(settings.DATA_PATH) / "instagram_graph_token.json").exists()):
            logger.warning("INSTAGRAM_GRAPH_ACCESS_TOKEN no configurado y no hay token persistido en DATA_PATH")
            return False

        if not settings.INSTAGRAM_GRAPH_PUBLIC_BASE_URL:
            logger.warning("INSTAGRAM_GRAPH_PUBLIC_BASE_URL no configurado")
            return False
        
        logger.info("Publicación en Instagram Graph API habilitada")
        return True

    def _build_graph_params(self, extra: Optional[dict] = None) -> dict:
        token_info = self.token_manager.load()
        access_token = token_info.access_token if token_info else ""
        params = {
            "access_token": access_token,
        }
        if settings.INSTAGRAM_GRAPH_APP_SECRET and access_token:
            proof = hmac.new(
                settings.INSTAGRAM_GRAPH_APP_SECRET.encode("utf-8"),
                msg=access_token.encode("utf-8"),
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

    def _try_fetch_feed_media_image_url(self, feed_media_id: str) -> Optional[str]:
        """
        Obtiene una URL de imagen asociada al IG Media ya publicado (feed).

        La app nativa "compartir post en historias" no está expuesta en Graph API;
        lo más cercano es reutilizar el activo en CDN de Instagram (`media_url`)
        del mismo media_id que acaba de publicarse, en lugar de volver a pasar
        la URL del generador o self-hosted.
        """
        try:
            data = self._graph_get(
                f"/{feed_media_id}",
                params={
                    "fields": "media_type,media_url,children{media_type,media_url}",
                },
            )
        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response is not None else ""
            logger.warning("GET IG Media %s falló: %s %s", feed_media_id, e.response.status_code if e.response else "", body[:300])
            return None

        mt = (data.get("media_type") or "").upper()
        if mt == "IMAGE":
            return data.get("media_url")
        if mt in ("CAROUSEL_ALBUM", "CAROUSEL"):
            for child in (data.get("children") or {}).get("data") or []:
                cmt = (child.get("media_type") or "").upper()
                if cmt == "IMAGE" and child.get("media_url"):
                    return child["media_url"]
            ch = (data.get("children") or {}).get("data") or []
            if ch and ch[0].get("media_url"):
                return ch[0]["media_url"]
        return data.get("media_url")

    def _fetch_feed_media_image_url_with_retry(self, feed_media_id: str) -> Optional[str]:
        """Reintentos: el media_url puede no estar listo al instante tras publish."""
        delays = (0.0, 1.5, 3.0, 5.0)
        for i, delay in enumerate(delays):
            if delay:
                time.sleep(delay)
            url = self._try_fetch_feed_media_image_url(feed_media_id)
            if url:
                return url
            logger.debug("media_url aún vacío para %s (intento %s/%s)", feed_media_id, i + 1, len(delays))
        return None

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
        retry_count: int = 0,
        source_image_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Publica un post en Instagram con retry básico
        
        Args:
            image_path: Ruta a la imagen a publicar
            caption: Caption del post
            retry_count: Contador interno de reintentos
            source_image_url: URL original de la imagen (CDN del generador),
                              preferida sobre la URL self-hosted si está disponible.
            
        Returns:
            Optional[str]: Media ID del post publicado o None si falla
        """
        if not self.enabled:
            logger.info("Publicación omitida: Instagram no habilitado")
            self._set_error("instagram_disabled", "Servicio deshabilitado por configuración")
            return None
        self._clear_error()
        
        if not self.login():
            return None
        
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

            if source_image_url:
                image_url = source_image_url
                logger.info("Usando URL fuente (CDN del generador) para Graph API")
            else:
                image_url = self._image_url_for_graph(image_path)
                if not image_url:
                    logger.error("No se pudo construir image_url pública para Graph API.")
                    return None

            logger.info(f"Publicando en Instagram Graph API: {os.path.basename(image_path)}")
            logger.info(f"Image URL para Graph API: {image_url}")
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
                    return self.publish_post(image_path, caption, retry_count + 1, source_image_url=source_image_url)
            else:
                self._set_error("instagram_graph_http_error", body)
            return None

        except Exception as e:
            logger.error(f"Error al publicar en Instagram Graph API: {str(e)}")
            self._set_error("instagram_graph_publish_error", str(e))
            if retry_count < self.max_retries:
                logger.info(f"Reintentando... ({retry_count + 1}/{self.max_retries})")
                time.sleep(self._compute_backoff(retry_count))
                return self.publish_post(image_path, caption, retry_count + 1, source_image_url=source_image_url)
            
            return None
    
    def _publish_story_image_url(
        self,
        image_url: str,
        retry_count: int = 0,
    ) -> Optional[str]:
        """Crea y publica un contenedor STORIES con la URL de imagen indicada."""
        try:
            logger.info(f"Publicando Story (contenedor): {image_url[:80]}...")

            media_resp = self._graph_post(
                f"/{self.ig_user_id}/media",
                data={
                    "image_url": image_url,
                    "media_type": "STORIES",
                },
            )
            creation_id = media_resp.get("id")
            if not creation_id:
                raise RuntimeError(f"Respuesta sin creation_id: {media_resp}")

            publish_resp = self._graph_post(
                f"/{self.ig_user_id}/media_publish",
                data={"creation_id": creation_id},
            )
            story_media_id = str(publish_resp.get("id", ""))
            if not story_media_id:
                raise RuntimeError(f"Respuesta de publicación inválida: {publish_resp}")

            logger.info(f"✅ Story publicada en Instagram: {story_media_id}")
            return story_media_id

        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response is not None else str(e)
            logger.error(f"Graph API Story error ({e.response.status_code}): {body}")
            if e.response is not None and e.response.status_code in (429, 500, 502, 503, 504):
                self._set_error("instagram_graph_story_transient", body)
                if retry_count < self.max_retries:
                    wait_time = self._compute_backoff(retry_count)
                    logger.info(f"Reintentando Story en {wait_time}s ({retry_count + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    return self._publish_story_image_url(image_url, retry_count + 1)
            else:
                self._set_error("instagram_graph_story_http_error", body)
            return None

        except Exception as e:
            logger.error(f"Error al publicar Story: {str(e)}")
            self._set_error("instagram_graph_story_error", str(e))
            if retry_count < self.max_retries:
                time.sleep(self._compute_backoff(retry_count))
                return self._publish_story_image_url(image_url, retry_count + 1)
            return None

    def share_feed_post_to_story(
        self,
        feed_media_id: str,
        image_path: str,
        source_image_url: Optional[str] = None,
        retry_count: int = 0,
    ) -> Optional[str]:
        """
        Publica una historia usando el mismo activo que el post del feed recién publicado.

        1) Tras publicar el feed, se consulta GET /{feed_media_id} para obtener `media_url`
           (CDN de Instagram del media publicado).
        2) Esa URL alimenta el contenedor STORIES. Así no se reutiliza la URL del generador
           como si fuera un segundo upload independiente.

        Nota: La app muestra "compartir post" con sticker; Graph API no lo expone. Este flujo
        es el más cercano permitido por Meta.

        Args:
            feed_media_id: ID devuelto por publish_post (IG Media del feed).
            image_path: Ruta local (fallback si no hay media_url).
            source_image_url: URL del generador (segundo fallback).
            retry_count: Reintentos internos de publicación del contenedor.

        Returns:
            Media ID de la story publicada, o None.
        """
        if not self.enabled:
            return None
        self._clear_error()

        if not self.login():
            return None

        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

            ig_asset_url = self._fetch_feed_media_image_url_with_retry(feed_media_id)
            if ig_asset_url:
                logger.info(
                    "Story: usando media_url del post publicado (mismo activo en Instagram que el feed)"
                )
                story_image_url = ig_asset_url
            else:
                logger.warning(
                    "No se obtuvo media_url del post publicado; usando URL de respaldo para la historia"
                )
                story_image_url = source_image_url or self._image_url_for_graph(image_path)
                if not story_image_url:
                    logger.error("No hay URL disponible para publicar la historia.")
                    return None

            return self._publish_story_image_url(story_image_url, retry_count=retry_count)

        except Exception as e:
            logger.error(f"Error en share_feed_post_to_story: {str(e)}")
            self._set_error("instagram_graph_share_story_error", str(e))
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
