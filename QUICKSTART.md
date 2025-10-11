# 🚀 Quick Start Guide

Guía rápida para poner en marcha tu influencer IA en minutos.

## ⚡ Setup Rápido (5 minutos)

### 1. Configurar Variables de Entorno

```bash
cp env.example .env
nano .env  # o usa tu editor favorito
```

Completa estas variables OBLIGATORIAS:
```env
OPENAI_API_KEY=sk-tu-clave-aqui
REPLICATE_API_TOKEN=tu-token-aqui
```

### 2. Agregar Imágenes de Referencia

```bash
# Copia tus imágenes al identity_pack
cp tus_fotos/*.jpg identity_pack/

# Edita el metadata
nano identity_pack/identity_metadata.json
```

### 3. Iniciar con Docker

```bash
docker-compose up -d
```

¡Listo! La aplicación está corriendo en http://localhost:8000

## 📋 Verificar Instalación

```bash
# Ver logs
docker-compose logs -f

# Health check
curl http://localhost:8000/api/v1/health
```

## 🎯 Primeros Pasos

### Generar tu Primer Post

```bash
# Desde la terminal
curl -X POST "http://localhost:8000/api/v1/generate/now"

# O desde el navegador
# Ir a: http://localhost:8000/docs
# Usar la interfaz interactiva de Swagger
```

### Ver el Último Post

```bash
curl http://localhost:8000/api/v1/posts/latest
```

## 🔧 Configuración Básica

### Cambiar Horario de Publicación

Edita `.env`:
```env
# 9 AM todos los días
DAILY_CRON=0 9 * * *

# Mediodía y 6 PM
DAILY_CRON=0 12,18 * * *

# Solo lunes a viernes a las 8 AM
DAILY_CRON=0 8 * * 1-5
```

Reinicia:
```bash
docker-compose restart
```

### Habilitar Publicación Automática en Instagram

Edita `.env`:
```env
INSTAGRAM_USERNAME=tu_usuario
INSTAGRAM_PASSWORD=tu_password
INSTAGRAM_ENABLED=true
```

## 🛠️ Comandos Útiles

```bash
# Iniciar
docker-compose up -d

# Detener
docker-compose down

# Ver logs
docker-compose logs -f

# Reiniciar
docker-compose restart

# Reconstruir después de cambios
docker-compose up -d --build
```

## 📱 Endpoints Principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/generate/now` | POST | Generar post ahora |
| `/api/v1/posts/latest` | GET | Ver último post |
| `/api/v1/health` | GET | Estado del sistema |
| `/docs` | GET | Documentación interactiva |

## 🎨 Personalización Rápida

### Cambiar Temas

Edita `app/services/openai_service.py`:
```python
self.themes = [
    "tu tema 1",
    "tu tema 2",
    # ...
]
```

### Cambiar Modelo de IA

Edita `.env`:
```env
OPENAI_MODEL=gpt-4o-mini  # más económico
# o
OPENAI_MODEL=gpt-4o  # más potente
```

## ❓ Problemas Comunes

### "No reference images found"
```bash
# Verifica que tengas imágenes en identity_pack
ls identity_pack/
```

### "Database error"
```bash
# Elimina y recrea la DB
rm -rf data/
docker-compose restart
```

### "Instagram login failed"
- Verifica usuario/password
- Instagram puede requerir 2FA
- Prueba sin Instagram primero (INSTAGRAM_ENABLED=false)

## 📚 Siguiente Paso

Lee el [README.md](README.md) completo para configuración avanzada.

## 🆘 Ayuda

- Abre un issue en GitHub
- Revisa los logs: `docker-compose logs -f`
- Ejecuta el script de verificación: `python scripts/check_config.py`

---

**¡Feliz generación de contenido!** 🎉

