#!/usr/bin/env python3
"""
Upload tous les workouts cyclisme de S06 vers Garmin Connect

Usage:
    python scripts/upload_all_cycling.py
"""

import sys
from pathlib import Path
import json

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.garmin_service import GarminService
from src.garmin_workout_converter import convert_to_garmin_cycling_workout

print("🚀 Upload Workouts Cyclisme S06 vers Garmin Connect")
print("=" * 70)
print()

# Charger les workouts
WORKOUT_FILE = Path(__file__).parent.parent / "data" / "workouts_cache" / "S06_workouts_v6_near_final.json"

with open(WORKOUT_FILE) as f:
    data = json.load(f)

# Filtrer les workouts cyclisme
cycling_workouts = [w for w in data['workouts'] if w.get('type') == 'Cyclisme']

print(f"📂 Workouts cyclisme trouvés : {len(cycling_workouts)}")
for w in cycling_workouts:
    print(f"   - {w['code']}: {w.get('description', 'N/A')}")
print()

# Connexion Garmin
print("🔐 Connexion à Garmin Connect...")
service = GarminService()
service.connect()
print("✅ Connexion réussie")
print()

# Upload chaque workout
uploaded = []
errors = []

for workout_json in cycling_workouts:
    code = workout_json['code']

    print(f"📤 Upload {code}...")

    try:
        # Afficher info (convert pour preview seulement)
        garmin_workout_preview = convert_to_garmin_cycling_workout(workout_json)
        duration_min = garmin_workout_preview['estimatedDurationInSecs'] // 60
        num_steps = len(garmin_workout_preview['workoutSegments'][0]['workoutSteps'])
        print(f"   Durée: {duration_min} min, Steps: {num_steps}")

        # Upload (passer le JSON original, le service fera la conversion)
        result = service.upload_workout(workout_json)

        workout_id = result.get('workoutId', 'UNKNOWN')
        workout_name = result.get('workoutName', code)

        uploaded.append({
            'code': code,
            'id': workout_id,
            'name': workout_name
        })

        print(f"   ✅ Workout ID: {workout_id}")
        print()

    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        errors.append({'code': code, 'error': str(e)})
        print()

# Résumé
print("=" * 70)
print("📊 RÉSUMÉ")
print("=" * 70)
print()

if uploaded:
    print(f"✅ {len(uploaded)} workouts uploadés avec succès:")
    for w in uploaded:
        print(f"   - {w['code']:6s} → ID: {w['id']}")
    print()

if errors:
    print(f"❌ {len(errors)} erreurs:")
    for e in errors:
        print(f"   - {e['code']:6s} → {e['error']}")
    print()

print("💡 Vérifier sur Garmin Connect:")
print("   https://connect.garmin.com/modern/workouts")
