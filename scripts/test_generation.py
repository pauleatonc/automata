#!/usr/bin/env python3
"""
Script de prueba para generar un post manualmente
"""
import sys
import os
import asyncio

# Agregar el directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal, init_db
from app.services.state_engine import state_engine


async def main():
    """Genera un post de prueba"""
    print("🚀 Iniciando generación de post de prueba...\n")
    
    # Inicializar DB
    init_db()
    
    # Crear sesión
    db = SessionLocal()
    
    try:
        # Generar post
        success, post, error = await state_engine.generate_post(
            db=db,
            trigger_type="manual",
            publish_to_instagram=False
        )
        
        if success and post:
            print("\n✅ Post generado exitosamente!")
            print(f"\n📝 Texto del post:\n{post.text_content}\n")
            print(f"🎨 Tema: {post.theme}")
            print(f"🖼️  Imagen guardada en: {post.image_path}")
            print(f"🔗 URL de imagen: {post.image_url}")
        else:
            print(f"\n❌ Error al generar post: {error}")
            
    except Exception as e:
        print(f"\n❌ Excepción: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
