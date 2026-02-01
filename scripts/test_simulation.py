#!/usr/bin/env python3
"""
Script de prueba simulada para demostrar el funcionamiento del sistema
sin usar APIs reales (OpenAI/Replicate)
"""
import sys
import os
import asyncio
from datetime import datetime

# Agregar el directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal, init_db
from app.services.state_engine import state_engine, get_recent_posts_context
from app.models.post import Post


async def simulate_generation():
    """Simula la generación de un post completo"""
    print("🎭 SIMULACIÓN DEL SISTEMA DE GENERACIÓN")
    print("=" * 50)
    
    # Inicializar DB
    init_db()
    db = SessionLocal()
    
    try:
        # 1. Cargar identity metadata
        print("\n📋 Paso 1: Cargando identity metadata...")
        metadata = state_engine.get_metadata()
        print(f"   ✅ Nombre: {metadata.get('influencer_name', 'No encontrado')}")
        print(f"   ✅ Imágenes base: {len(metadata.get('base_images', []))}")
        print(f"   ✅ Imágenes generadas: {len(metadata.get('generated_images', []))}")
        
        # 2. Obtener estado actual
        print("\n🧠 Paso 2: Obteniendo estado actual...")
        current_state = state_engine.get_current_state(db)
        print(f"   ✅ Capítulo: {current_state.get('chapter')}")
        print(f"   ✅ Emoción: {current_state.get('emotion_focus')}")
        print(f"   ✅ Ubicación: {current_state.get('location')}")
        
        # 3. Calcular siguiente estado
        print("\n🔄 Paso 3: Calculando siguiente estado...")
        new_state = state_engine.next_state(current_state)
        print(f"   ✅ Nuevo capítulo: {new_state.get('chapter')}")
        print(f"   ✅ Nueva emoción: {new_state.get('emotion_focus')}")
        print(f"   ✅ Nueva ubicación: {new_state.get('location')}")
        
        # 4. Obtener contexto de posts recientes
        print("\n📚 Paso 4: Obteniendo contexto de posts recientes...")
        recent_context = get_recent_posts_context(db, limit=3)
        print(f"   ✅ Posts recientes encontrados: {len(recent_context)}")
        for i, post in enumerate(recent_context[:2], 1):
            print(f"      {i}. Post {post.get('id')}: {post.get('chapter')} / {post.get('emotion_focus')}")
        
        # 5. Simular generación de caption
        print("\n✍️  Paso 5: Simulando generación de caption...")
        simulated_caption = f"""En {new_state.get('location')}, donde la {new_state.get('emotion_focus')} 
        se entrelaza con la luz del atardecer, encuentro en este momento de {new_state.get('chapter')} 
        una pausa necesaria. La ciudad respira a mi alrededor mientras yo busco {new_state.get('learning_goal')}. 
        Hay algo en la manera en que la luz toca las superficies que me recuerda que cada instante 
        es una oportunidad de conexión con lo esencial."""
        print(f"   ✅ Caption simulado: {len(simulated_caption)} caracteres")
        print(f"   📝 Preview: {simulated_caption[:100]}...")
        
        # 6. Simular generación de imagen
        print("\n🎨 Paso 6: Simulando generación de imagen...")
        simulated_image_path = f"./data/images/{datetime.now().strftime('%Y/%m')}/simulated_{datetime.now().strftime('%d_%H%M%S')}.png"
        print(f"   ✅ Ruta simulada: {simulated_image_path}")
        
        # 7. Crear post simulado
        print("\n💾 Paso 7: Creando post simulado en BD...")
        simulated_post = Post(
            chapter=new_state.get("chapter"),
            emotion_focus=new_state.get("emotion_focus"),
            learning_goal=new_state.get("learning_goal"),
            location=new_state.get("location"),
            caption=simulated_caption,
            image_prompt=f"portrait in {new_state.get('location')} with {new_state.get('emotion_focus')} mood",
            image_path=simulated_image_path,
            published_platforms={},
            meta=new_state.get("meta", {})
        )
        
        db.add(simulated_post)
        db.commit()
        db.refresh(simulated_post)
        print(f"   ✅ Post guardado con ID: {simulated_post.id}")
        
        # 8. Simular actualización de identity pack
        print("\n🔄 Paso 8: Simulando actualización de identity pack...")
        post_count = simulated_post.meta.get("post_count", 0) if simulated_post.meta else 0
        print(f"   📊 Post número: {post_count}")
        
        if post_count % 5 == 0:
            print("   ✅ Es momento de actualizar identity pack!")
            print("   📸 Se agregaría una nueva imagen generada")
            print("   🔄 Identity pack evolucionaría automáticamente")
        else:
            print(f"   ⏳ Próxima actualización en {5 - (post_count % 5)} posts")
        
        # 9. Mostrar resumen
        print("\n🎉 RESUMEN DE LA SIMULACIÓN:")
        print("=" * 50)
        print(f"✅ Post ID: {simulated_post.id}")
        print(f"✅ Capítulo: {simulated_post.chapter}")
        print(f"✅ Emoción: {simulated_post.emotion_focus}")
        print(f"✅ Ubicación: {simulated_post.location}")
        print(f"✅ Caption: {len(simulated_post.caption)} caracteres")
        print(f"✅ Contexto usado: {len(recent_context)} posts anteriores")
        print(f"✅ Identity pack: {len(metadata.get('base_images', []))} base + {len(metadata.get('generated_images', []))} generadas")
        
        print("\n🚀 El sistema está funcionando correctamente!")
        print("📝 Para probar con APIs reales, configura las credenciales y ejecuta:")
        print("   python scripts/test_generation.py")
        
    except Exception as e:
        print(f"\n❌ Error en simulación: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(simulate_generation())
