"""
Configuración de la aplicación
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación desde variables de entorno"""
    
    # Base de datos
    DATABASE_URL: str = "sqlite:///./data/influencer.db"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Replicate
    REPLICATE_API_TOKEN: str
    
    # Instagram (opcional)
    INSTAGRAM_USERNAME: Optional[str] = None
    INSTAGRAM_PASSWORD: Optional[str] = None
    INSTAGRAM_ENABLED: bool = False
    
    # Scheduler
    DAILY_CRON: str = "0 9 * * *"  # 9 AM todos los días
    TIMEZONE: str = "America/Santiago"
    
    # Rutas
    IDENTITY_PACK_PATH: str = "/identity_pack"
    DATA_PATH: str = "/data"
    
    # Prompts
    POST_PROMPT_TEMPLATE: str = """Genera un post para Instagram de un influencer de {theme}.
El post debe ser:
- Inspirador y motivacional
- Auténtico y personal
- Entre 100-150 palabras
- Incluir 3-5 hashtags relevantes
- En español

Tema del día: {daily_theme}"""
    
    IMAGE_PROMPT_TEMPLATE: str = """professional portrait photo, {style}, 
high quality, detailed face, natural lighting, instagram worthy,
{theme}"""
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

