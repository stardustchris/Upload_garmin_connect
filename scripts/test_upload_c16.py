#!/usr/bin/env python3
"""
Script de test pour uploader C16 vers Garmin Connect

Usage:
    python scripts/test_upload_c16.py
"""

import sys
import json
from pathlib import Path

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.garmin_service import GarminService

def main():
    print("🚀 Test Upload C16 vers Garmin Connect")
    print("=" * 50)

    # Charger C16 depuis JSON
    json_path = Path(__file__).parent.parent / 'data/workouts_cache/S06_workouts_v6_near_final.json'

    print(f"\n📂 Chargement workout depuis {json_path.name}...")
    with open(json_path) as f:
        data = json.load(f)

    c16 = [w for w in data['workouts'] if w['code'] == 'C16'][0]
    print(f"✅ C16 chargé: {c16['code']} - {c16.get('description', '')}")
    print(f"   Date: {c16['date']}")
    print(f"   Durée: {c16['duration_total']}")
    print(f"   Intervalles: {len(c16['intervals'])}")

    # Initialiser GarminService
    print("\n🔐 Connexion à Garmin Connect...")
    service = GarminService()

    try:
        service.connect()
        print("✅ Connexion réussie")

        # Upload workout
        print(f"\n📤 Upload de C16...")
        result = service.upload_workout(c16)

        print("\n✅ Upload réussi!")
        print(f"   Workout ID: {result.get('workoutId', 'N/A')}")
        print(f"   Workout Name: {result.get('workoutName', 'N/A')}")

        print("\n💡 Vérifier sur Garmin Connect:")
        print("   https://connect.garmin.com/modern/workouts")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
