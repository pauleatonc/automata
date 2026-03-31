"""
Instagram/Meta Graph token management.

Meta Graph API does not provide a classic OAuth refresh_token for Facebook Login tokens.
The closest equivalent is exchanging a short-lived user token for a long-lived user token,
then using that token in Graph calls.

This module persists the current token + expiry in /data so containers can be recreated
without losing runtime token state.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # ISO 8601
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


@dataclass(frozen=True)
class TokenInfo:
    access_token: str
    expires_at: Optional[datetime] = None

    def is_expired(self, skew_seconds: int = 60) -> bool:
        if not self.expires_at:
            return False
        return _utcnow() >= (self.expires_at - timedelta(seconds=skew_seconds))


class InstagramTokenManager:
    """
    Manages a single Graph API access token with best-effort inspection/refresh.

    Persistence:
      - /data/instagram_graph_token.json
    """

    def __init__(self):
        self._path = Path(settings.DATA_PATH) / "instagram_graph_token.json"
        self._http = httpx.Client(timeout=30.0)

    def load(self) -> Optional[TokenInfo]:
        # Priority: persisted token -> env token
        persisted = self._load_persisted()
        if persisted and persisted.access_token:
            return persisted
        if settings.INSTAGRAM_GRAPH_ACCESS_TOKEN:
            return TokenInfo(access_token=settings.INSTAGRAM_GRAPH_ACCESS_TOKEN, expires_at=None)
        return None

    def _load_persisted(self) -> Optional[TokenInfo]:
        try:
            if not self._path.exists():
                return None
            data = json.loads(self._path.read_text(encoding="utf-8"))
            token = str(data.get("access_token") or "")
            expires_at = _parse_ts(data.get("expires_at"))
            if not token:
                return None
            return TokenInfo(access_token=token, expires_at=expires_at)
        except Exception as e:
            logger.warning("No se pudo leer token persistido: %s", e)
            return None

    def persist(self, token: str, expires_at: Optional[datetime]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "access_token": token,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "updated_at": _utcnow().isoformat(),
            }
            self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("No se pudo persistir token en %s: %s", self._path, e)

    def inspect_token(self, token: Optional[str] = None) -> dict:
        """
        Uses Graph debug_token to validate and read expires_at.
        Requires app_id + app_secret for app access token.
        """
        token = token or (self.load().access_token if self.load() else "")
        if not token:
            raise RuntimeError("No hay access_token para inspeccionar")
        if not settings.INSTAGRAM_GRAPH_APP_ID or not settings.INSTAGRAM_GRAPH_APP_SECRET:
            raise RuntimeError("Faltan INSTAGRAM_GRAPH_APP_ID / INSTAGRAM_GRAPH_APP_SECRET para debug_token")

        app_access_token = f"{settings.INSTAGRAM_GRAPH_APP_ID}|{settings.INSTAGRAM_GRAPH_APP_SECRET}"
        url = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_API_VERSION}/debug_token"
        resp = self._http.get(url, params={"input_token": token, "access_token": app_access_token})
        resp.raise_for_status()
        return resp.json()

    def _exchange_short_to_long_lived(self, token: str) -> Tuple[str, Optional[datetime]]:
        """
        Exchange short-lived user token for long-lived user token (best-effort).
        """
        if not settings.INSTAGRAM_GRAPH_APP_ID or not settings.INSTAGRAM_GRAPH_APP_SECRET:
            raise RuntimeError("Faltan INSTAGRAM_GRAPH_APP_ID / INSTAGRAM_GRAPH_APP_SECRET para exchange")

        url = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_API_VERSION}/oauth/access_token"
        resp = self._http.get(
            url,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.INSTAGRAM_GRAPH_APP_ID,
                "client_secret": settings.INSTAGRAM_GRAPH_APP_SECRET,
                "fb_exchange_token": token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        new_token = str(data.get("access_token") or "")
        expires_in = data.get("expires_in")
        expires_at = None
        try:
            if expires_in is not None:
                expires_at = _utcnow() + timedelta(seconds=int(expires_in))
        except Exception:
            expires_at = None
        if not new_token:
            raise RuntimeError(f"Exchange sin access_token: {data}")
        return new_token, expires_at

    def refresh_if_needed(self, threshold_hours: int = 72) -> Optional[TokenInfo]:
        """
        Refresh (exchange) if token is expiring soon or invalid.
        Returns new TokenInfo if refreshed, None if not needed.
        """
        current = self.load()
        if not current:
            logger.warning("No hay token cargado para refresh")
            return None

        # If we have expiry and it's far enough, keep
        if current.expires_at:
            if current.expires_at - _utcnow() > timedelta(hours=threshold_hours):
                return None

        # Try inspect first (may update expiry if persisted lacked it)
        try:
            debug = self.inspect_token(current.access_token)
            data = (debug.get("data") or {}) if isinstance(debug, dict) else {}
            is_valid = bool(data.get("is_valid"))
            expires_at_unix = data.get("expires_at")
            expires_at = None
            if expires_at_unix:
                try:
                    expires_at = datetime.fromtimestamp(int(expires_at_unix), tz=timezone.utc)
                except Exception:
                    expires_at = None

            if not is_valid:
                logger.warning("Token inválido según debug_token; intentando exchange")
            else:
                # If expires_at known and is not near expiry, persist and stop
                if expires_at and expires_at - _utcnow() > timedelta(hours=threshold_hours):
                    self.persist(current.access_token, expires_at)
                    return None
        except Exception as e:
            logger.warning("No se pudo inspeccionar token (continuando a refresh): %s", e)

        # Exchange short-lived -> long-lived (best effort)
        new_token, new_expires_at = self._exchange_short_to_long_lived(current.access_token)
        self.persist(new_token, new_expires_at)
        logger.info("Token Graph refrescado (exchange) y persistido en %s", self._path)

        # Small pause to avoid immediate race with subsequent Graph calls
        time.sleep(0.2)
        return TokenInfo(access_token=new_token, expires_at=new_expires_at)

