#!/usr/bin/env python3
"""
Script para inicializar la base de datos
"""
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import init_db

if __name__ == "__main__":
    print("Inicializando base de datos...")
    init_db()
    print("✅ Base de datos inicializada correctamente")
