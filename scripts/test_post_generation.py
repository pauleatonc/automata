#!/usr/bin/env python3
"""
Script para probar la generación de posts con datos simulados
"""
import asyncio
import os
import sys
import json
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.state_engine import state_engine, get_recent_posts_context
from app.db.session import SessionLocal, init_db
from app.models.post import Post
from app.core.logging_config import get_logger
from unittest.mock import patch, AsyncMock

logger = get_logger(__name__)

async def test_post_generation():
    """Prueba la generación de posts con datos simulados"""
    logger.info("🎭 PRUEBA DE GENERACIÓN DE POSTS")
    logger.info("==================================================")

    # Inicializar BD
    init_db()
    db = SessionLocal()

    try:
        # Mock de las APIs externas
        with patch('app.services.text_gen.generate_caption', new_callable=AsyncMock) as mock_caption, \
             patch('app.services.image_gen.generate_image', new_callable=AsyncMock) as mock_image:

            # Configurar mocks
            mock_caption.return_value = """En Santiago, Barrio Lastarria, donde la asombro 
se entrelaza con la luz del atardecer, encuentro en este momento de despertar 
una pausa necesaria. La ciudad respira a mi alrededor mientras yo busco descubrir quién soy y qué busco en este mundo. 
Hay algo en la manera en que la luz toca las superficies que me recuerda que cada instante 
es una oportunidad de conexión con lo esencial."""

            mock_image.return_value = "./data/images/2025/10/18_141500.png"

            # 1. Cargar identity metadata
            logger.info("\n📋 Paso 1: Cargando identity metadata...")
            metadata = state_engine.get_metadata()
            logger.info(f"   ✅ Nombre: {metadata.get('influencer_name')}")
            logger.info(f"   ✅ Imágenes base: {len(metadata.get('base_images', []))}")
            logger.info(f"   ✅ Imágenes generadas: {len(metadata.get('generated_images', []))}")

            # 2. Obtener estado actual
            logger.info("\n🧠 Paso 2: Obteniendo estado actual...")
            current_state = state_engine.get_current_state(db)
            logger.info(f"   ✅ Capítulo: {current_state.get('chapter')}")
            logger.info(f"   ✅ Emoción: {current_state.get('emotion_focus')}")
            logger.info(f"   ✅ Ubicación: {current_state.get('location')}")

            # 3. Calcular siguiente estado
            logger.info("\n🔄 Paso 3: Calculando siguiente estado...")
            new_state = state_engine.next_state(current_state)
            logger.info(f"   ✅ Nuevo capítulo: {new_state.get('chapter')}")
            logger.info(f"   ✅ Nueva emoción: {new_state.get('emotion_focus')}")
            logger.info(f"   ✅ Nueva ubicación: {new_state.get('location')}")

            # 4. Obtener contexto de posts recientes
            logger.info("\n📚 Paso 4: Obteniendo contexto de posts recientes...")
            recent_context = get_recent_posts_context(db, limit=3)
            logger.info(f"   ✅ Posts recientes encontrados: {len(recent_context)}")

            # 5. Simular generación de caption
            logger.info("\n✍️  Paso 5: Simulando generación de caption...")
            caption = await mock_caption(new_state, metadata, recent_context)
            logger.info(f"   ✅ Caption simulado: {len(caption)} caracteres")
            logger.info(f"   📝 Preview: {caption[:100]}...")

            # 6. Simular generación de imagen
            logger.info("\n🎨 Paso 6: Simulando generación de imagen...")
            image_path = await mock_image(
                prompt="simulated prompt",
                state=new_state,
                identity_meta=metadata,
                model="Nano-banana"
            )
            logger.info(f"   ✅ Ruta simulada: {image_path}")

            # 7. Guardar post simulado en BD
            logger.info("\n💾 Paso 7: Creando post simulado en BD...")
            new_post = Post(
                chapter=new_state.get("chapter"),
                emotion_focus=new_state.get("emotion_focus"),
                learning_goal=new_state.get("learning_goal"),
                location=new_state.get("location"),
                caption=caption,
                image_prompt="simulated prompt",
                image_path=image_path,
                published_platforms={},
                meta=new_state.get("meta", {})
            )
            db.add(new_post)
            db.commit()
            db.refresh(new_post)
            logger.info(f"   ✅ Post guardado con ID: {new_post.id}")

            # 8. Simular actualización de identity pack
            logger.info("\n🔄 Paso 8: Simulando actualización de identity pack...")
            await state_engine._update_identity_pack_if_needed(new_post, metadata)
            logger.info(f"   📊 Post número: {new_post.meta.get('post_count', 0)}")
            logger.info(f"   ⏳ Próxima actualización en {5 - (new_post.meta.get('post_count', 0) % 5)} posts")

            logger.info("\n🎉 RESUMEN DE LA PRUEBA:")
            logger.info("==================================================")
            logger.info(f"✅ Post ID: {new_post.id}")
            logger.info(f"✅ Capítulo: {new_post.chapter}")
            logger.info(f"✅ Emoción: {new_post.emotion_focus}")
            logger.info(f"✅ Ubicación: {new_post.location}")
            logger.info(f"✅ Caption: {len(new_post.caption)} caracteres")
            logger.info(f"✅ Contexto usado: {len(recent_context)} posts anteriores")
            
            # Verificar metadata actualizado
            updated_metadata = state_engine.get_metadata()
            logger.info(f"✅ Identity pack: {len(updated_metadata.get('base_images', []))} base + {len(updated_metadata.get('generated_images', []))} generadas")

            # Verificar en BD
            total_posts = db.query(Post).count()
            logger.info(f"✅ Total posts en BD: {total_posts}")

    except Exception as e:
        logger.error(f"❌ Error durante la prueba: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_post_generation())
