#!/usr/bin/env python3
"""
Script para verificar la configuración del sistema
"""
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.utils.identity import get_reference_images


def check_env_vars():
    """Verifica variables de entorno"""
    print("🔍 Verificando variables de entorno...\n")
    
    checks = {
        "OpenAI API Key": bool(settings.OPENAI_API_KEY),
        "Replicate Token": bool(settings.REPLICATE_API_TOKEN),
        "Instagram Enabled": settings.INSTAGRAM_ENABLED,
        "Database URL": bool(settings.DATABASE_URL),
        "Daily Cron": bool(settings.DAILY_CRON),
    }
    
    for check, status in checks.items():
        symbol = "✅" if status else "❌"
        print(f"{symbol} {check}: {status}")
    
    print()


def check_identity_pack():
    """Verifica el identity pack"""
    print("📸 Verificando identity pack...\n")
    
    path = settings.IDENTITY_PACK_PATH
    exists = os.path.exists(path)
    
    print(f"{'✅' if exists else '❌'} Ruta: {path}")
    
    if exists:
        images = get_reference_images()
        print(f"{'✅' if images else '⚠️ '} Imágenes encontradas: {len(images)}")
        
        for img in images:
            print(f"   - {os.path.basename(img)}")
    else:
        print("⚠️  La carpeta identity_pack no existe")
    
    print()


def check_data_path():
    """Verifica el path de datos"""
    print("💾 Verificando path de datos...\n")
    
    path = settings.DATA_PATH
    exists = os.path.exists(path)
    
    print(f"{'✅' if exists else '❌'} Ruta: {path}")
    
    if not exists:
        print("ℹ️  La carpeta será creada automáticamente al iniciar")
    
    print()


def main():
    """Ejecuta todas las verificaciones"""
    print("=" * 50)
    print("  AI Influencer Backend - Verificación de Sistema")
    print("=" * 50)
    print()
    
    check_env_vars()
    check_identity_pack()
    check_data_path()
    
    print("=" * 50)
    print("✨ Verificación completada")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
