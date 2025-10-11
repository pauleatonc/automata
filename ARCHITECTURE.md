# 🏗️ Arquitectura del Sistema

## Visión General

```
┌─────────────────────────────────────────────────────────────┐
│                   AI Influencer Backend                      │
│                      (FastAPI + Docker)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │         API REST Endpoints              │
        │  ┌────────────────────────────────────┐ │
        │  │ POST /api/v1/generate/now          │ │
        │  │ GET  /api/v1/posts/latest          │ │
        │  │ GET  /api/v1/health                │ │
        │  └────────────────────────────────────┘ │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │         APScheduler (Cron)              │
        │   Ejecución diaria configurable         │
        │   Trigger: manual o scheduled           │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │       Post Generator (Orchestrator)     │
        └─────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   OpenAI     │    │  Replicate   │    │  Instagram   │
│   Service    │    │   Service    │    │   Service    │
│              │    │              │    │  (Opcional)  │
│ • GPT-4o     │    │ • SDXL       │    │              │
│ • Texto      │    │ • InstantID  │    │ • instagrapi │
│ • Temas      │    │ • Imágenes   │    │ • Publicar   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        │                     ▼                     │
        │           ┌──────────────┐                │
        │           │ Identity Pack│                │
        │           │  (Volumen)   │                │
        │           │              │                │
        │           │ • reference1 │                │
        │           │ • reference2 │                │
        │           │ • metadata   │                │
        │           └──────────────┘                │
        │                                           │
        └───────────────────┬───────────────────────┘
                            ▼
                ┌──────────────────────┐
                │   SQLAlchemy ORM     │
                └──────────────────────┘
                            ▼
                ┌──────────────────────┐
                │   SQLite Database    │
                │     (Volumen /data)  │
                │                      │
                │ • posts              │
                │ • generation_logs    │
                │ • generated_images/  │
                └──────────────────────┘
```

## 🔄 Flujo de Generación de Post

```
1. Trigger (Scheduler o Manual)
         │
         ▼
2. PostGenerator.generate_post()
         │
         ├─► [OpenAI] Generar texto del post
         │            └─► Texto + Tema
         │
         ├─► [OpenAI] Generar prompt de imagen
         │            └─► Image prompt
         │
         ├─► [Replicate] Generar imagen
         │     │
         │     ├─► Seleccionar imagen de referencia
         │     ├─► InstantID (con referencia)
         │     │   └─► URL de imagen generada
         │     │
         │     └─► Descargar y guardar localmente
         │          └─► /data/generated_images/post_*.png
         │
         ├─► [Database] Guardar Post
         │            └─► ID, texto, imagen, tema, etc.
         │
         ├─► [Instagram] Publicar (si habilitado)
         │            └─► Media ID
         │
         └─► [Database] Registrar GenerationLog
                      └─► status, trigger_type, post_id
```

## 📦 Componentes Principales

### 1. **FastAPI Application** (`app/main.py`)
- Servidor HTTP asíncrono
- Gestión del ciclo de vida
- CORS middleware
- Rutas API

### 2. **Scheduler** (`app/scheduler.py`)
- APScheduler con AsyncIOScheduler
- Trigger cron configurable
- Generación automática diaria
- Timezone aware

### 3. **Services**

#### OpenAI Service (`app/services/openai_service.py`)
- Generación de texto para posts
- Temas rotativos
- Prompts personalizables
- Estilos fotográficos

#### Replicate Service (`app/services/replicate_service.py`)
- Generación de imágenes con SDXL
- InstantID para consistencia facial
- Gestión de imágenes de referencia
- Descarga y almacenamiento local

#### Instagram Service (`app/services/instagram_service.py`)
- Publicación automática (opcional)
- Login y autenticación
- Upload de fotos con caption

#### Post Generator (`app/services/post_generator.py`)
- Orquestador principal
- Coordina todos los servicios
- Manejo de errores
- Logging de generaciones

### 4. **Database** (`app/database.py`, `app/models.py`)
- SQLAlchemy ORM
- SQLite por defecto (PostgreSQL en prod)
- Dos tablas:
  - `posts`: Posts generados
  - `generation_logs`: Historial de generaciones

### 5. **Configuration** (`app/config.py`)
- Pydantic Settings
- Variables de entorno
- Configuración centralizada

## 🗄️ Modelos de Datos

### Post
```python
{
  id: int,
  text_content: str,
  image_path: str,
  image_url: str,
  prompt_used: str,
  image_prompt_used: str,
  theme: str,
  published: bool,
  published_at: datetime,
  instagram_media_id: str,
  created_at: datetime,
  updated_at: datetime
}
```

### GenerationLog
```python
{
  id: int,
  status: str,  # success, error
  error_message: str,
  post_id: int,
  trigger_type: str,  # scheduled, manual
  created_at: datetime
}
```

## 🐳 Arquitectura Docker

```
┌─────────────────────────────────────────┐
│         Docker Container                │
│    (ai-influencer-backend)              │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │   Python 3.11 + FastAPI           │ │
│  │   + APScheduler                   │ │
│  │   + SQLAlchemy                    │ │
│  │   + OpenAI + Replicate            │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Volumes:                               │
│  • ./data → /data                      │
│  • ./identity_pack → /identity_pack    │
│                                         │
│  Ports:                                 │
│  • 8000:8000                            │
└─────────────────────────────────────────┘
```

## 🔐 Seguridad

- Variables de entorno para secretos
- No se commitean archivos .env
- Identity pack en .gitignore
- Data folder persistente pero privada
- CORS configurable

## ⚡ Performance

- FastAPI asíncrono
- Conexiones a APIs externas async
- SQLAlchemy con pool de conexiones
- Imágenes guardadas localmente
- Scheduler no bloqueante

## 🔧 Escalabilidad

### Actual (Monolito)
- Single container
- SQLite
- Local file storage

### Futuro (Microservicios)
- Separar servicios en containers
- PostgreSQL/MySQL
- S3/Cloud Storage para imágenes
- Redis para caché
- Queue (Celery) para generaciones

## 📊 Monitoreo

### Health Check
```bash
GET /api/v1/health
{
  status: "ok",
  database: "ok",
  identity_pack: "ok",
  scheduler: "configured"
}
```

### Logs
- Structured logging
- Console output
- Docker logs accesibles
- Error tracking en GenerationLog

## 🚀 Deploy Flow

```
1. Development
   └─► Local: uvicorn --reload

2. Build
   └─► docker build -t ai-influencer .

3. Deploy
   └─► docker-compose up -d

4. Monitoring
   └─► docker-compose logs -f
   └─► GET /api/v1/health
```

## 📝 Consideraciones de Producción

### Database
- Migrar a PostgreSQL
- Backups automáticos
- Replicación si necesario

### Storage
- Mover imágenes a S3/Cloud Storage
- CDN para servir imágenes
- Cleanup de imágenes antiguas

### Scheduler
- Considerar Celery Beat para mayor robustez
- Queue para tareas pesadas
- Retry logic

### Monitoring
- Sentry para error tracking
- Prometheus + Grafana para métricas
- Uptime monitoring

### Security
- Rate limiting
- API authentication
- HTTPS obligatorio
- Secrets management (Vault)

## 🎯 Extensiones Futuras

- [ ] Múltiples influencers
- [ ] Publicación en múltiples plataformas (Twitter, TikTok)
- [ ] Análisis de engagement
- [ ] A/B testing de contenido
- [ ] Dashboard web para gestión
- [ ] Webhook para notificaciones
- [ ] API pública con autenticación
- [ ] Machine learning para optimizar horarios

---

**Documentación actualizada**: Octubre 2025

