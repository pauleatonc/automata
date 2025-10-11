# AI Influencer Backend 🤖✨

Backend automatizado para generar posts diarios de un influencer IA con texto generado por OpenAI e imágenes generadas por Replicate (SDXL + InstantID).

## 🚀 Características

- ✅ **Generación automática de texto** con OpenAI API (GPT-4o-mini)
- ✅ **Generación de imágenes** con Replicate (SDXL + InstantID/IP-Adapter FaceID)
- ✅ **Publicación automática** en Instagram con instagrapi (opcional)
- ✅ **Scheduler configurable** con APScheduler (ejecución diaria)
- ✅ **API REST** con FastAPI
- ✅ **Persistencia** con SQLAlchemy + SQLite (PostgreSQL en producción)
- ✅ **Dockerizado** con Dockerfile y docker-compose

## 📋 Stack Tecnológico

- **Framework**: FastAPI
- **Scheduler**: APScheduler
- **ORM**: SQLAlchemy
- **Database**: SQLite (configurable a PostgreSQL)
- **IA Texto**: OpenAI API
- **IA Imagen**: Replicate (SDXL + InstantID)
- **Instagram**: instagrapi
- **Despliegue**: Docker + Docker Compose

## 📁 Estructura del Proyecto

```
influencer/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicación FastAPI principal
│   ├── schemas.py           # Schemas Pydantic
│   ├── api/
│   │   └── routes.py        # Rutas de la API
│   ├── core/
│   │   ├── config.py        # Configuración desde env vars
│   │   ├── scheduler.py     # Configuración del scheduler
│   │   └── logging_config.py # Configuración de logging
│   ├── models/
│   │   ├── base.py          # Clase base SQLAlchemy
│   │   └── post.py          # Modelos de posts
│   ├── services/
│   │   ├── text_gen.py      # Generación de texto (OpenAI)
│   │   ├── image_gen.py     # Generación de imágenes (Replicate)
│   │   ├── publish_instagram.py # Publicación Instagram
│   │   └── state_engine.py  # Orquestador principal
│   ├── db/
│   │   └── session.py       # Sesiones de base de datos
│   ├── jobs/
│   │   └── daily_job.py     # Job de generación diaria
│   └── utils/
│       ├── identity.py      # Utilidades identity pack
│       └── files.py         # Utilidades de archivos
├── data/                    # Volumen para DB y datos (creado automáticamente)
├── identity_pack/           # Imágenes de referencia del influencer
│   ├── identity_metadata.json
│   └── *.jpg/png            # Tus imágenes de referencia
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔧 Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone <tu-repo>
cd influencer
```

### 2. Crear archivo .env

Copia el archivo de ejemplo y configura tus credenciales:

```bash
cp env.example .env
```

Edita `.env` con tus valores:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-tu-clave-de-openai
OPENAI_MODEL=gpt-4o-mini

# Replicate Configuration
REPLICATE_API_TOKEN=tu-token-de-replicate

# Instagram (Optional)
INSTAGRAM_USERNAME=tu_usuario_instagram
INSTAGRAM_PASSWORD=tu_password_instagram
INSTAGRAM_ENABLED=true

# Scheduler Configuration
DAILY_CRON=0 9 * * *  # 9 AM todos los días
TIMEZONE=America/Santiago

# Paths
IDENTITY_PACK_PATH=/identity_pack
DATA_PATH=/data

# Database
DATABASE_URL=sqlite:///./data/influencer.db
```

### 3. Preparar Identity Pack

Crea la carpeta `identity_pack` y agrega tus imágenes de referencia:

```bash
mkdir -p identity_pack
```

Copia tus imágenes de referencia del influencer a esta carpeta y crea el archivo `identity_metadata.json`:

```json
{
  "reference_images": [
    "image1.jpg",
    "image2.jpg",
    "image3.jpg"
  ],
  "influencer_name": "Tu Influencer IA",
  "description": "Descripción de tu influencer"
}
```

### 4. Desplegar con Docker

```bash
# Construir y ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

### 5. Instalación Local (sin Docker)

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python -m uvicorn app.main:app --reload
```

## 🌐 API Endpoints

### POST /api/v1/generate/now

Genera un post inmediatamente.

**Query Parameters:**
- `publish` (bool, opcional): Si se debe publicar automáticamente en Instagram

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/generate/now?publish=true"
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Post generado exitosamente",
  "post": {
    "id": 1,
    "text_content": "Contenido del post...",
    "image_url": "https://replicate.delivery/...",
    "image_path": "/data/generated_images/post_20250101_090000.png",
    "theme": "lifestyle y bienestar",
    "published": true,
    "created_at": "2025-01-01T09:00:00"
  }
}
```

### GET /api/v1/posts/latest

Obtiene el último post generado.

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/posts/latest"
```

### GET /api/v1/health

Health check del sistema.

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/health"
```

**Respuesta:**
```json
{
  "status": "ok",
  "database": "ok",
  "identity_pack": "ok",
  "scheduler": "configured",
  "timestamp": "2025-01-01T09:00:00"
}
```

## ⏰ Scheduler

El scheduler ejecuta automáticamente la generación de posts según la configuración de `DAILY_CRON`.

**Formato CRON:**
```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Día de la semana (0-7, 0 y 7 = Domingo)
│ │ │ └───── Mes (1-12)
│ │ └─────── Día del mes (1-31)
│ └───────── Hora (0-23)
└─────────── Minuto (0-59)
```

**Ejemplos:**
- `0 9 * * *` - Todos los días a las 9 AM
- `0 12,18 * * *` - Todos los días a las 12 PM y 6 PM
- `0 9 * * 1-5` - Lunes a Viernes a las 9 AM

## 🎨 Personalización

### Temas de Posts

Los temas se definen en `app/services/openai_service.py`. Puedes agregar o modificar temas:

```python
self.themes = [
    "lifestyle y bienestar",
    "fitness y salud",
    "moda y tendencias",
    # Agrega tus temas aquí
]
```

### Estilos de Fotografía

Los estilos fotográficos también se pueden personalizar:

```python
self.photo_styles = [
    "casual lifestyle portrait",
    "professional photoshoot",
    # Agrega tus estilos aquí
]
```

### Templates de Prompts

Modifica los templates en `app/config.py`:

```python
POST_PROMPT_TEMPLATE: str = """Tu template personalizado..."""
IMAGE_PROMPT_TEMPLATE: str = """Tu template de imagen..."""
```

## 🗄️ Base de Datos

### SQLite (Default)

Por defecto se usa SQLite para desarrollo:
```
DATABASE_URL=sqlite:///./data/influencer.db
```

### PostgreSQL (Producción)

Para producción, cambia a PostgreSQL:
```
DATABASE_URL=postgresql://usuario:password@host:5432/influencer_db
```

### Modelos

**Post**: Almacena posts generados
- `text_content`: Texto del post
- `image_path`: Ruta local de la imagen
- `image_url`: URL de Replicate
- `published`: Estado de publicación
- `instagram_media_id`: ID del post en Instagram

**GenerationLog**: Registra intentos de generación
- `status`: success/error
- `trigger_type`: manual/scheduled
- `post_id`: ID del post generado

## 📝 Logs

Los logs se muestran en la consola y incluyen:
- Inicio/detención de la aplicación
- Ejecuciones del scheduler
- Generación de posts
- Publicaciones en Instagram
- Errores y excepciones

Ver logs en Docker:
```bash
docker-compose logs -f
```

## 🔒 Seguridad

- ✅ Nunca commitees el archivo `.env` con tus credenciales
- ✅ Usa variables de entorno para secretos
- ✅ En producción, usa HTTPS
- ✅ Limita el acceso a la API con autenticación (a implementar)

## 🚀 Despliegue en Producción

### Opciones de Hosting

1. **VPS (DigitalOcean, Linode, AWS EC2)**
   - Instalar Docker y Docker Compose
   - Clonar repositorio
   - Configurar `.env`
   - Ejecutar `docker-compose up -d`

2. **Railway/Render**
   - Conectar repositorio
   - Configurar variables de entorno
   - Deploy automático

3. **AWS/GCP/Azure**
   - Usar servicios de contenedores (ECS, Cloud Run, etc.)
   - Configurar volúmenes persistentes
   - Configurar variables de entorno

### Migrar a PostgreSQL

1. Instalar PostgreSQL
2. Crear base de datos
3. Actualizar `DATABASE_URL` en `.env`
4. Reiniciar aplicación

```env
DATABASE_URL=postgresql://user:password@localhost:5432/influencer_db
```

## 🐛 Troubleshooting

### Error: "Instagram login failed"
- Verifica usuario y contraseña
- Instagram puede requerir verificación 2FA
- Considera usar tokens de aplicación

### Error: "No reference images found"
- Verifica que la carpeta `identity_pack` tenga imágenes
- Revisa permisos del volumen en Docker

### Error: "OpenAI API key invalid"
- Verifica que tu API key sea correcta
- Revisa que tengas créditos disponibles

### Error: "Replicate timeout"
- Las generaciones pueden tardar 30-60 segundos
- Verifica tu conexión a internet
- Revisa límites de tu cuenta Replicate

## 📄 Licencia

MIT License

## 🤝 Contribuciones

Las contribuciones son bienvenidas! Por favor abre un issue o pull request.

## 📧 Contacto

Para preguntas o soporte, abre un issue en GitHub.

---

**¡Disfruta de tu influencer IA!** 🎉

