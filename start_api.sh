#!/bin/bash
# Script de démarrage de l'API Garmin Automation

cd "$(dirname "$0")"

# Activer le venv
source venv/bin/activate

# Lancer l'API
echo "🚀 Démarrage de l'API Garmin Automation..."
echo "📍 URL: http://localhost:8000"
echo "📖 Docs: http://localhost:8000/docs"
echo ""

uvicorn api.main:app --reload --port 8000
