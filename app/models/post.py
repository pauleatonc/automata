"""
Modelos de base de datos para posts
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.models.base import Base
from datetime import datetime


class Post(Base):
    """Modelo para almacenar posts generados"""
    
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    # Contenido del post
    chapter = Column(String(200), nullable=True, index=True)
    emotion_focus = Column(String(200), nullable=True)
    learning_goal = Column(Text, nullable=True)
    location = Column(String(300), nullable=True)
    caption = Column(Text, nullable=False)
    
    # Imagen
    image_prompt = Column(Text, nullable=True)
    image_path = Column(String(500), nullable=True)
    
    # Metadatos
    published_platforms = Column(JSON, nullable=True, default=dict)  # {"instagram": "media_id", "twitter": "tweet_id"}
    meta = Column(JSON, nullable=True, default=dict)  # Metadata adicional flexible
    
    def __repr__(self):
        return f"<Post(id={self.id}, chapter='{self.chapter}', emotion_focus='{self.emotion_focus}')>"
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "chapter": self.chapter,
            "emotion_focus": self.emotion_focus,
            "learning_goal": self.learning_goal,
            "location": self.location,
            "caption": self.caption,
            "image_prompt": self.image_prompt,
            "image_path": self.image_path,
            "published_platforms": self.published_platforms or {},
            "meta": self.meta or {},
        }
