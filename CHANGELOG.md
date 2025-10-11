# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [2.0.0] - 2025-10-11

### 🎉 Refactorización Mayor - Nueva Estructura Modular

#### ✨ Agregado
- Nueva estructura de directorios modular
- `app/core/` - Componentes centrales (config, scheduler, logging)
- `app/api/` - Endpoints de la API
- `app/models/` - Modelos de base de datos separados
- `app/db/` - Gestión de sesiones de base de datos
- `app/jobs/` - Jobs programados
- `app/utils/` - Utilidades (identity, files)
- `app/core/logging_config.py` - Configuración de logging estructurado
- `STRUCTURE.md` - Documentación detallada de la estructura
- `REFACTORING_SUMMARY.md` - Resumen de cambios de refactorización
- `CHANGELOG.md` - Este archivo

#### 🔄 Cambiado
- **Servicios renombrados** para ser más descriptivos:
  - `openai_service.py` → `text_gen.py`
  - `replicate_service.py` → `image_gen.py`
  - `instagram_service.py` → `publish_instagram.py`
  - `post_generator.py` → `state_engine.py`
- **Archivos reorganizados**:
  - `config.py` → `core/config.py`
  - `routes.py` → `api/routes.py`
  - `scheduler.py` → `core/scheduler.py`
  - `database.py` → `db/session.py` + `models/base.py`
  - `models.py` → `models/post.py`
- **Scripts actualizados** con nuevos imports
- **Documentación actualizada** con nueva estructura

#### 🗑️ Eliminado
- Archivos antiguos en estructura plana
- Código duplicado

#### 🔧 Mejorado
- Separación de responsabilidades
- Modularidad y escalabilidad
- Mantenibilidad del código
- Testabilidad
- Organización de imports

### 📝 Notas de Migración
- ✅ Sin breaking changes en funcionalidad
- ✅ Todos los imports actualizados
- ✅ Scripts funcionando correctamente
- ✅ Sin errores de linting

## [1.0.0] - 2025-10-11

### 🎉 Release Inicial

#### ✨ Características
- Backend FastAPI completo
- Generación automática de posts con IA
- Generación de texto con OpenAI
- Generación de imágenes con Replicate (SDXL + InstantID)
- Publicación automática en Instagram (opcional)
- Scheduler configurable (APScheduler)
- Base de datos SQLite con SQLAlchemy
- Dockerizado con docker-compose
- Documentación completa

#### 📋 Endpoints
- `POST /api/v1/generate/now` - Generación manual
- `GET /api/v1/posts/latest` - Último post
- `GET /api/v1/health` - Health check

#### 🐳 Docker
- Dockerfile optimizado
- docker-compose con volúmenes
- Identity pack system

#### 📚 Documentación
- README.md completo
- QUICKSTART.md
- ARCHITECTURE.md
- FIRST_RUN.md
- START_HERE.md
- PROJECT_SUMMARY.md

---

## Formato

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Tipos de Cambios
- `✨ Agregado` - Para nuevas características
- `🔄 Cambiado` - Para cambios en funcionalidad existente
- `🗑️ Eliminado` - Para características eliminadas
- `🐛 Corregido` - Para corrección de bugs
- `🔒 Seguridad` - Para vulnerabilidades
- `🔧 Mejorado` - Para mejoras de performance o código

