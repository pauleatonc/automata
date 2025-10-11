# 👋 Bienvenido a AI Influencer Backend

## 🎯 ¿Qué es esto?

Un backend completo que **genera automáticamente posts** para tu influencer IA:
- 📝 **Texto**: Generado con OpenAI (GPT)
- 🎨 **Imágenes**: Generadas con Replicate (SDXL + InstantID)
- 📱 **Instagram**: Publicación automática (opcional)
- ⏰ **Scheduler**: Ejecución diaria configurable
- 🚀 **Docker**: Deploy fácil con un comando

## ⚡ Inicio Rápido (3 pasos)

### 1️⃣ Configurar Credenciales

```bash
cp env.example .env
nano .env  # Agregar tu OPENAI_API_KEY y REPLICATE_API_TOKEN
```

### 2️⃣ Agregar Fotos de Referencia

```bash
# Copiar 3-5 fotos de tu influencer
cp tus_fotos/*.jpg identity_pack/
```

### 3️⃣ Iniciar

```bash
docker-compose up -d
```

**¡Listo!** Tu influencer IA está funcionando en http://localhost:8000

## 📚 Documentación

Elige según tu necesidad:

| Archivo | Para qué sirve |
|---------|---------------|
| **[FIRST_RUN.md](FIRST_RUN.md)** | 🎬 **Empieza aquí** - Checklist paso a paso para primera ejecución |
| **[QUICKSTART.md](QUICKSTART.md)** | ⚡ Guía rápida de 5 minutos |
| **[README.md](README.md)** | 📖 Documentación completa y detallada |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | 🏗️ Arquitectura técnica del sistema |
| **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** | 📋 Resumen ejecutivo del proyecto |

## 🎬 Primera Vez

**Lee primero: [FIRST_RUN.md](FIRST_RUN.md)**

Este archivo te guiará paso a paso en tu primera ejecución.

## 🔑 Requisitos

- ✅ Docker y Docker Compose
- ✅ API Key de OpenAI ([obtener aquí](https://platform.openai.com/api-keys))
- ✅ Token de Replicate ([obtener aquí](https://replicate.com/account/api-tokens))
- ✅ 3-5 fotos de referencia de tu influencer

## 🚀 Comandos Principales

```bash
# Iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Generar post ahora
curl -X POST http://localhost:8000/api/v1/generate/now

# Ver último post
curl http://localhost:8000/api/v1/posts/latest

# Documentación interactiva
# Abrir en navegador: http://localhost:8000/docs

# Detener
docker-compose down
```

## 📊 API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/generate/now` | POST | Generar post inmediatamente |
| `/api/v1/posts/latest` | GET | Ver último post generado |
| `/api/v1/health` | GET | Health check del sistema |
| `/docs` | GET | Documentación interactiva |

## 🎨 Características

- ✅ Generación automática diaria (configurable)
- ✅ Texto con IA (OpenAI GPT)
- ✅ Imágenes con IA (Replicate SDXL + InstantID)
- ✅ 10 temas diferentes rotativos
- ✅ Mantiene consistencia facial con tus fotos
- ✅ Publicación en Instagram (opcional)
- ✅ Base de datos SQLite (migrable a PostgreSQL)
- ✅ Logs y monitoring
- ✅ Docker y docker-compose
- ✅ Documentación completa

## 📁 Estructura del Proyecto

```
influencer/
├── app/                    # Código de la aplicación
│   ├── main.py            # FastAPI app
│   ├── services/          # Servicios (OpenAI, Replicate, Instagram)
│   └── ...
├── scripts/               # Scripts útiles
├── identity_pack/         # 📸 Tus fotos de referencia (agregar aquí)
├── data/                  # Base de datos e imágenes generadas
├── docker-compose.yml     # Configuración Docker
└── .env                   # 🔑 Tus credenciales (crear de env.example)
```

## ⏰ Scheduler

Por defecto, genera un post todos los días a las 9 AM.

Para cambiar:
```bash
# Editar .env
DAILY_CRON=0 12,18 * * *  # Mediodía y 6 PM
```

## 🌐 Producción

Para deploy en producción:
1. Clonar en tu servidor
2. Configurar `.env` con credenciales de producción
3. Agregar tus fotos al `identity_pack/`
4. `docker-compose up -d`

Opcional:
- Configurar nginx como reverse proxy
- Configurar SSL/HTTPS
- Migrar a PostgreSQL

## 🆘 Ayuda

- **Primera ejecución**: Lee [FIRST_RUN.md](FIRST_RUN.md)
- **Problemas comunes**: Sección Troubleshooting en [README.md](README.md)
- **Ver logs**: `docker-compose logs -f`
- **Verificar config**: `python scripts/check_config.py`

## 📊 Estadísticas del Proyecto

- 📦 27 archivos
- 💻 1,057 líneas de código Python
- 📚 5 documentos de ayuda
- 🔧 4 scripts útiles
- 🐳 100% dockerizado

## 🎯 Próximos Pasos

1. ✅ **Leer [FIRST_RUN.md](FIRST_RUN.md)** - Configuración inicial
2. ✅ Configurar tus credenciales
3. ✅ Agregar tus fotos
4. ✅ Iniciar con Docker
5. ✅ Generar tu primer post
6. ✅ Personalizar temas y prompts
7. ✅ Configurar Instagram (opcional)
8. ✅ Deploy en producción

## 💡 Tips

- Las primeras generaciones tardan ~1-2 minutos
- InstantID mantiene la consistencia facial usando tus fotos
- Puedes personalizar temas en `app/services/openai_service.py`
- Puedes cambiar prompts en `app/config.py`
- Usa `http://localhost:8000/docs` para probar la API interactivamente

## 🎉 ¡Disfruta!

Tu influencer IA está listo para generar contenido automáticamente.

---

**¿Dudas?** Lee la documentación o abre un issue en GitHub.

**Stack**: FastAPI • APScheduler • SQLAlchemy • OpenAI • Replicate • Docker

