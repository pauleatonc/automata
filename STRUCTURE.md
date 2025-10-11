# 📁 Estructura del Proyecto

## Árbol de Directorios

```
ai-influencer/
├── app/
│  ├── main.py                    # Aplicación FastAPI principal
│  ├── schemas.py                 # Schemas Pydantic
│  ├── api/
│  │  └── routes.py               # Rutas y endpoints de la API
│  ├── core/
│  │  ├── config.py               # Configuración (settings)
│  │  ├── scheduler.py            # APScheduler setup
│  │  └── logging_config.py       # Configuración de logging
│  ├── models/
│  │  ├── base.py                 # Clase base SQLAlchemy
│  │  └── post.py                 # Modelos Post y GenerationLog
│  ├── services/
│  │  ├── text_gen.py             # Generación de texto (OpenAI)
│  │  ├── image_gen.py            # Generación de imágenes (Replicate)
│  │  ├── publish_instagram.py    # Publicación en Instagram
│  │  └── state_engine.py         # Orquestador principal
│  ├── db/
│  │  └── session.py              # Sesiones de base de datos
│  ├── jobs/
│  │  └── daily_job.py            # Job de generación diaria
│  ├── utils/
│  │  ├── identity.py             # Manejo del identity pack
│  │  └── files.py                # Utilidades de archivos
│  └── __init__.py
├── identity_pack/
│  ├── identity_pack_01.png       # Imagen de referencia 1
│  ├── identity_pack_02.png       # Imagen de referencia 2
│  ├── identity_pack_03.png       # Imagen de referencia 3
│  ├── identity_pack_04.png       # Imagen de referencia 4
│  └── identity_metadata.json     # Metadata del influencer
├── scripts/
│  ├── init_db.py                 # Inicializar base de datos
│  ├── test_generation.py         # Probar generación manual
│  └── check_config.py            # Verificar configuración
├── data/                         # Datos persistentes (volumen Docker)
│  ├── influencer.db              # Base de datos SQLite
│  └── generated_images/          # Imágenes generadas
├── .env.example                  # Template de configuración
├── requirements.txt              # Dependencias Python
├── Dockerfile                    # Docker image
├── docker-compose.yml            # Orquestación Docker
├── README.md                     # Documentación principal
├── QUICKSTART.md                 # Guía rápida
├── ARCHITECTURE.md               # Arquitectura técnica
└── Makefile                      # Comandos útiles
```

## 📦 Módulos Principales

### `app/main.py`
- Punto de entrada de la aplicación
- Configuración de FastAPI
- Lifecycle management (startup/shutdown)
- Inicialización del scheduler

### `app/api/routes.py`
- Definición de endpoints REST
- `/api/v1/generate/now` - Generación manual
- `/api/v1/posts/latest` - Último post
- `/api/v1/health` - Health check

### `app/core/`
**Configuración y componentes centrales**

- `config.py`: Variables de entorno con Pydantic Settings
- `scheduler.py`: APScheduler para jobs programados
- `logging_config.py`: Setup de logging estructurado

### `app/models/`
**Modelos de base de datos**

- `base.py`: Clase base declarativa de SQLAlchemy
- `post.py`: Modelos `Post` y `GenerationLog`

### `app/services/`
**Lógica de negocio**

- `text_gen.py`: Generación de texto con OpenAI
- `image_gen.py`: Generación de imágenes con Replicate
- `publish_instagram.py`: Publicación en Instagram
- `state_engine.py`: Orquestador que coordina todo el flujo

### `app/db/`
**Gestión de base de datos**

- `session.py`: Configuración de sesiones y engine de SQLAlchemy

### `app/jobs/`
**Tareas programadas**

- `daily_job.py`: Job que se ejecuta diariamente según cron

### `app/utils/`
**Utilidades**

- `identity.py`: Manejo de imágenes de referencia del identity pack
- `files.py`: Descarga y gestión de archivos

## 🔄 Flujo de Ejecución

### Generación Manual (API)
```
1. Usuario → POST /api/v1/generate/now
2. routes.py → state_engine.generate_post()
3. state_engine coordina:
   ├─ text_gen.generate_post_text()
   ├─ image_gen.generate_post_image()
   ├─ db.session guarda Post
   └─ publish_instagram (opcional)
4. Respuesta → JSON con post generado
```

### Generación Automática (Scheduler)
```
1. Scheduler (cron) → jobs/daily_job.py
2. daily_job.generate_daily_post()
3. state_engine.generate_post()
4. ... mismo flujo que generación manual
```

## 🎨 Patrones de Diseño

### Singleton Services
Todos los servicios son instancias singleton:
```python
text_gen_service = TextGenerationService()
image_gen_service = ImageGenerationService()
instagram_service = InstagramPublishService()
state_engine = StateEngine()
```

### Dependency Injection
FastAPI usa inyección de dependencias para DB:
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### State Engine Pattern
`StateEngine` orquesta todos los servicios manteniendo el estado de la generación.

## 📝 Convenciones de Código

- **Nombres de archivos**: snake_case (`text_gen.py`)
- **Nombres de clases**: PascalCase (`TextGenerationService`)
- **Nombres de funciones**: snake_case (`generate_post_text()`)
- **Constantes**: UPPER_CASE (`DAILY_CRON`)
- **Docstrings**: Google style
- **Type hints**: Siempre que sea posible

## 🔍 Imports

### Absolutos (preferido)
```python
from app.core.config import settings
from app.services.text_gen import text_gen_service
from app.models.post import Post
```

### Relativos (evitar)
```python
# ❌ Evitar
from ..core.config import settings
```

## 🚀 Extensibilidad

### Agregar un Nuevo Servicio
1. Crear archivo en `app/services/`
2. Implementar clase del servicio
3. Crear instancia singleton
4. Exportar en `app/services/__init__.py`
5. Usar en `state_engine.py` si es necesario

### Agregar un Nuevo Endpoint
1. Agregar función en `app/api/routes.py`
2. Decorar con `@router.get/post/put/delete`
3. Usar dependency injection para DB si es necesario

### Agregar un Nuevo Modelo
1. Crear clase en `app/models/`
2. Heredar de `Base`
3. Definir `__tablename__` y columnas
4. Importar en `app/db/session.py::init_db()`

## 📚 Más Información

- **Documentación completa**: [README.md](README.md)
- **Arquitectura técnica**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Guía rápida**: [QUICKSTART.md](QUICKSTART.md)

---

**Última actualización**: Octubre 2025  
**Versión**: 2.0.0 (Estructura reorganizada)

