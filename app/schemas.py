"""
Schemas de Pydantic para validación de datos
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PostResponse(BaseModel):
    """Schema de respuesta para un post"""
    id: int
    text_content: str
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    theme: Optional[str] = None
    published: bool
    published_at: Optional[datetime] = None
    instagram_media_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GenerateResponse(BaseModel):
    """Schema de respuesta para la generación de posts"""
    success: bool
    message: str
    post: Optional[PostResponse] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Schema de respuesta para el endpoint de health"""
    status: str
    database: str
    identity_pack: str
    scheduler: str
    timestamp: datetime

