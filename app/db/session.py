"""
Configuración de sesiones de base de datos
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.base import Base
import os

# Asegurar que el directorio de datos existe con permisos correctos
os.makedirs(settings.DATA_PATH, exist_ok=True)
os.chmod(settings.DATA_PATH, 0o777)

# Motor de base de datos
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False
)

# Sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependencia para obtener una sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializa la base de datos creando todas las tablas"""
    # Importar todos los modelos para que SQLAlchemy los registre
    from app.models import post  # noqa
    
    Base.metadata.create_all(bind=engine)
