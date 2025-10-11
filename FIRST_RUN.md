# 🎬 Primera Ejecución - Checklist

Sigue estos pasos para poner en marcha tu influencer IA por primera vez.

## ✅ Pre-requisitos

- [ ] Docker y Docker Compose instalados
- [ ] API Key de OpenAI
- [ ] Token de Replicate
- [ ] 3-5 fotos de referencia de tu influencer

## 📝 Paso 1: Configurar Variables de Entorno

```bash
# Copiar el template
cp env.example .env

# Editar con tus credenciales
nano .env
```

**Campos OBLIGATORIOS:**
```env
OPENAI_API_KEY=sk-xxxxxxxxxx      # Obtener de: https://platform.openai.com/api-keys
REPLICATE_API_TOKEN=xxxxxxxxxxxxx  # Obtener de: https://replicate.com/account/api-tokens
```

**Campos OPCIONALES (Instagram):**
```env
INSTAGRAM_USERNAME=tu_usuario
INSTAGRAM_PASSWORD=tu_password
INSTAGRAM_ENABLED=true
```

**Configuración del Scheduler:**
```env
DAILY_CRON=0 9 * * *              # 9 AM todos los días (cambiar si quieres)
TIMEZONE=America/Santiago          # Tu timezone
```

## 📸 Paso 2: Preparar Identity Pack

```bash
# Verificar que la carpeta existe
ls identity_pack/

# Copiar tus fotos de referencia
cp /ruta/a/tus/fotos/*.jpg identity_pack/

# Editar metadata
nano identity_pack/identity_metadata.json
```

**Actualizar identity_metadata.json:**
```json
{
  "reference_images": [
    "foto1.jpg",
    "foto2.jpg",
    "foto3.jpg"
  ],
  "influencer_name": "Nombre de tu Influencer",
  "description": "Descripción corta"
}
```

### Tips para mejores resultados:
- ✅ Fotos de alta calidad (mínimo 512x512)
- ✅ Rostro bien iluminado y visible
- ✅ Diferentes ángulos (frontal, 3/4, perfil)
- ✅ Diferentes expresiones
- ❌ Evitar fotos borrosas
- ❌ Evitar rostros ocultos

## 🐳 Paso 3: Verificar Configuración

```bash
# Verificar que todo está OK
python3 scripts/check_config.py
```

Deberías ver:
```
✅ OpenAI API Key: True
✅ Replicate Token: True
✅ Database URL: True
✅ Daily Cron: True
📸 Imágenes encontradas: 3
```

## 🚀 Paso 4: Iniciar Aplicación

```bash
# Construir e iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f
```

Espera ver algo como:
```
✅ Aplicación iniciada correctamente
✅ Scheduler iniciado con cron: 0 9 * * *
```

## 🧪 Paso 5: Probar Generación Manual

### Opción A: Con curl
```bash
curl -X POST "http://localhost:8000/api/v1/generate/now"
```

### Opción B: Con el navegador
1. Ir a: http://localhost:8000/docs
2. Expandir `POST /api/v1/generate/now`
3. Click en "Try it out"
4. Click en "Execute"

**Nota**: La primera generación puede tardar 1-2 minutos:
- OpenAI: ~5 segundos
- Replicate: ~30-60 segundos
- Total: ~45-90 segundos

## ✅ Paso 6: Verificar Resultado

```bash
# Ver el último post generado
curl http://localhost:8000/api/v1/posts/latest

# O en el navegador:
# http://localhost:8000/api/v1/posts/latest
```

Deberías ver:
```json
{
  "id": 1,
  "text_content": "Tu post generado...",
  "image_path": "/data/generated_images/post_20251011_100000.png",
  "image_url": "https://replicate.delivery/...",
  "theme": "lifestyle y bienestar",
  "published": false,
  "created_at": "2025-10-11T10:00:00"
}
```

## 🔍 Paso 7: Verificar Archivos Generados

```bash
# Ver base de datos creada
ls -lh data/

# Ver imágenes generadas
ls -lh data/generated_images/
```

## 📱 Paso 8 (Opcional): Probar con Instagram

Si configuraste Instagram:

```bash
# Generar y publicar automáticamente
curl -X POST "http://localhost:8000/api/v1/generate/now?publish=true"
```

## 🎯 Siguiente: Configurar Scheduler

El scheduler ya está corriendo según tu `DAILY_CRON`. Para cambiar:

1. Editar `.env`:
```env
DAILY_CRON=0 12,18 * * *  # Mediodía y 6 PM
```

2. Reiniciar:
```bash
docker-compose restart
```

## 📊 Monitoreo

### Ver logs en tiempo real
```bash
docker-compose logs -f
```

### Health check
```bash
curl http://localhost:8000/api/v1/health
```

### Ver documentación interactiva
Navegar a: http://localhost:8000/docs

## 🐛 Troubleshooting

### "No reference images found"
```bash
# Verificar imágenes
ls identity_pack/*.jpg identity_pack/*.png

# Verificar metadata
cat identity_pack/identity_metadata.json
```

### "OpenAI API error"
- Verificar que tu API key es correcta
- Verificar que tienes créditos en tu cuenta OpenAI
- Revisar logs: `docker-compose logs -f`

### "Replicate timeout"
- Es normal que tarde 30-60 segundos
- Verificar tu token de Replicate
- Verificar límites de tu cuenta

### "Container won't start"
```bash
# Ver logs detallados
docker-compose logs

# Reconstruir desde cero
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 📚 Recursos

- **Documentación completa**: `README.md`
- **Inicio rápido**: `QUICKSTART.md`
- **Arquitectura**: `ARCHITECTURE.md`
- **Resumen**: `PROJECT_SUMMARY.md`

## 🎉 ¡Listo!

Si llegaste aquí sin errores, tu influencer IA está funcionando.

### Próximos pasos:
- ✅ Esperar la primera ejecución automática según tu cron
- ✅ Personalizar temas en `app/services/openai_service.py`
- ✅ Ajustar prompts en `app/config.py`
- ✅ Monitorear posts generados

### Comandos útiles para el día a día:

```bash
# Ver logs
docker-compose logs -f

# Reiniciar
docker-compose restart

# Detener
docker-compose down

# Ver último post
curl localhost:8000/api/v1/posts/latest

# Generar post manual
curl -X POST localhost:8000/api/v1/generate/now
```

---

**¿Problemas?** Revisa los logs o abre un issue en GitHub.

**¡Disfruta tu influencer IA!** 🤖✨

