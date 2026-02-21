#!/usr/bin/env python3
"""
Upload C18 et CAP19 vers Garmin Connect

Usage:
    python scripts/upload_workouts.py
"""

import sys
from pathlib import Path

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_parser_v3 import TriathlonPDFParserV3
from api.services.garmin_service import GarminService
import json

print("🚴 Upload C18 et CAP19 vers Garmin Connect")
print("=" * 70)
print()

PDF_FILE = "/Users/aptsdae/Documents/Triathlon/Séances S06 (02_02 au 08_02)_Delalain C_2026.pdf"

# Parser les workouts
print("📄 Parsing des séances depuis PDF...")
parser = TriathlonPDFParserV3(PDF_FILE)

workouts_to_upload = ['C18', 'CAP19']
parsed_workouts = []

with parser:
    # Parser toutes les séances du PDF
    result = parser.parse()
    all_workouts = result.get('workouts', [])

    # Filtrer C18 et CAP19
    for workout in all_workouts:
        workout_code = workout.get('code', '')
        if workout_code in workouts_to_upload:
            parsed_workouts.append(workout)
            intervals_count = len(workout.get('intervals', []))
            print(f"   ✅ {workout_code} parsé : {intervals_count} intervalles")

print()
print(f"✅ {len(parsed_workouts)} séances parsées")
print()

# Connexion Garmin
print("🔐 Connexion à Garmin Connect...")
service = GarminService()
service.connect()
print("✅ Connexion réussie")
print()

# Upload des workouts
print("📤 Upload des séances...")
for workout in parsed_workouts:
    workout_code = workout['code']
    workout_type = workout['type']

    print(f"   Uploading {workout_code} ({workout_type})...")

    try:
        result = service.upload_workout(workout)
        workout_id = result.get('workoutId', 'unknown')
        print(f"   ✅ {workout_code} uploadé - ID: {workout_id}")
        print(f"      URL: https://connect.garmin.com/modern/workout/{workout_id}")
    except Exception as e:
        print(f"   ❌ Erreur upload {workout_code}: {e}")
        import traceback
        traceback.print_exc()

print()
print("=" * 70)
print("✅ Terminé")
