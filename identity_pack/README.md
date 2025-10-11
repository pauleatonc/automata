# Identity Pack

Esta carpeta contiene las imágenes de referencia de tu influencer IA que serán usadas para generar nuevas imágenes con InstantID.

## 📸 Instrucciones

1. **Agrega tus imágenes de referencia** en esta carpeta:
   - Formatos soportados: JPG, JPEG, PNG, WEBP
   - Recomendación: 3-5 imágenes de alta calidad
   - Incluye diferentes ángulos y expresiones

2. **Actualiza el archivo `identity_metadata.json`** con:
   - Nombres de los archivos de imagen
   - Información del influencer
   - Notas de estilo

## 🎯 Mejores Prácticas

### Calidad de las Imágenes
- ✅ Alta resolución (mínimo 512x512, recomendado 1024x1024)
- ✅ Buena iluminación
- ✅ Rostro claramente visible
- ✅ Diferentes ángulos (frontal, 3/4, perfil)
- ✅ Diferentes expresiones (sonrisa, serio, pensativo)
- ❌ Evitar fotos borrosas
- ❌ Evitar iluminación muy oscura o sobreexpuesta
- ❌ Evitar rostros parcialmente ocultos

### Variedad
- Incluye fotos en diferentes contextos (interior/exterior)
- Diferentes fondos
- Diferentes vestimentas
- Diferentes poses

## 📝 Ejemplo de metadata

```json
{
  "reference_images": [
    "frontal.jpg",
    "profile.jpg", 
    "smile.jpg"
  ],
  "influencer_name": "Alex Style",
  "description": "Influencer de moda urbana y lifestyle",
  "style_notes": "Estética moderna, colores vibrantes, urbano"
}
```

## 🔒 Privacidad

- Asegúrate de tener los derechos de las imágenes que uses
- No compartas este directorio si contiene imágenes personales
- Esta carpeta está en `.gitignore` para proteger tu privacidad

