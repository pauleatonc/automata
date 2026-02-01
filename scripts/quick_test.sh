#!/bin/bash
# Script de testing rápido

echo "🧪 AI Influencer Backend - Quick Test"
echo "===================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: Ejecuta este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Test 1: Verificar .env
echo "1️⃣  Verificando archivo .env..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado${NC}"
    echo "   Creando desde env.example..."
    cp env.example .env
    echo -e "${YELLOW}   ⚠️  EDITA .env con tus API keys antes de continuar${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Archivo .env encontrado${NC}"
fi

# Test 2: Verificar OpenAI API Key
echo ""
echo "2️⃣  Verificando OpenAI API Key..."
if grep -q "OPENAI_API_KEY=sk-" .env; then
    echo -e "${GREEN}✅ OpenAI API Key configurada${NC}"
else
    echo -e "${RED}❌ OpenAI API Key no configurada en .env${NC}"
    exit 1
fi

# Test 3: Verificar Replicate Token
echo ""
echo "3️⃣  Verificando Replicate Token..."
if grep -q "REPLICATE_API_TOKEN=" .env && ! grep -q "REPLICATE_API_TOKEN=your-replicate" .env; then
    echo -e "${GREEN}✅ Replicate Token configurado${NC}"
else
    echo -e "${RED}❌ Replicate Token no configurado en .env${NC}"
    exit 1
fi

# Test 4: Verificar identity pack
echo ""
echo "4️⃣  Verificando identity pack..."
if [ -d "identity_pack" ]; then
    IMAGE_COUNT=$(ls -1 identity_pack/*.png identity_pack/*.jpg 2>/dev/null | wc -l)
    if [ "$IMAGE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Identity pack encontrado ($IMAGE_COUNT imágenes)${NC}"
    else
        echo -e "${YELLOW}⚠️  No hay imágenes en identity_pack/${NC}"
        echo "   Agrega al menos 2 imágenes de referencia"
        exit 1
    fi
else
    echo -e "${RED}❌ Directorio identity_pack no encontrado${NC}"
    exit 1
fi

# Test 5: Verificar Python
echo ""
echo "5️⃣  Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ Python encontrado: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 3 no encontrado${NC}"
    exit 1
fi

# Test 6: Verificar Docker (opcional)
echo ""
echo "6️⃣  Verificando Docker..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}✅ Docker encontrado: $DOCKER_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  Docker no encontrado (opcional)${NC}"
fi

# Test 7: Verificar estructura de archivos
echo ""
echo "7️⃣  Verificando estructura del proyecto..."
REQUIRED_FILES=(
    "app/main.py"
    "app/api/routes.py"
    "app/core/config.py"
    "app/services/state_engine.py"
    "app/services/text_gen.py"
    "app/services/image_gen.py"
)

ALL_FOUND=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}✓${NC} $file"
    else
        echo -e "   ${RED}✗${NC} $file"
        ALL_FOUND=false
    fi
done

if [ "$ALL_FOUND" = false ]; then
    echo -e "${RED}❌ Algunos archivos faltan${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Estructura correcta${NC}"

# Resumen
echo ""
echo "===================================="
echo -e "${GREEN}✅ Todas las verificaciones pasaron${NC}"
echo ""
echo "🚀 Próximos pasos:"
echo ""
echo "   Opción 1 - Testing sin Docker:"
echo "   $ python3 -m venv venv"
echo "   $ source venv/bin/activate"
echo "   $ pip install -r requirements.txt"
echo "   $ python scripts/test_generation.py"
echo ""
echo "   Opción 2 - Testing con Docker:"
echo "   $ docker-compose up -d"
echo "   $ docker-compose logs -f"
echo ""
echo "   Opción 3 - Testing API manual:"
echo "   $ python -m uvicorn app.main:app --reload"
echo "   $ curl -X POST http://localhost:8000/api/v1/generate/now"
echo ""
echo "📖 Documentación completa: TEST_GUIDE.md"
echo ""


