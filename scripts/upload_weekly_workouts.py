#!/usr/bin/env python3
"""
Script pour uploader automatiquement toutes les séances d'une semaine vers Garmin Connect

Usage:
    python scripts/upload_weekly_workouts.py <pdf_path>

Exemple:
    python scripts/upload_weekly_workouts.py "/Users/aptsdae/Documents/Triathlon/Séances S07 (09_02 au 15_02)_Delalain C_2026.pdf"
"""

import sys
import json
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_parser_v3 import TriathlonPDFParserV3
from api.services.garmin_service import GarminService
from src.garmin_workout_converter import convert_to_garmin_cycling_workout, convert_to_garmin_running_workout


def upload_weekly_workouts(pdf_path: str):
    """
    Parse et upload toutes les séances d'une semaine

    Args:
        pdf_path: Chemin vers le PDF de la semaine
    """

    print(f"📄 Parsing du PDF: {pdf_path}\n")

    # Parser le PDF
    with TriathlonPDFParserV3(pdf_path) as parser:
        result = parser.parse()

    week = result.get('week', 'Unknown')
    period = result.get('period', 'Unknown')

    print("="*80)
    print(f"SEMAINE: {week}")
    print(f"PÉRIODE: {period}")
    print(f"TOTAL: {len(result['workouts'])} séances")
    print("="*80)

    # Grouper par type
    cycling = [w for w in result['workouts'] if w['type'] == 'Cyclisme']
    running = [w for w in result['workouts'] if w['type'] == 'Course à pied']
    swimming = [w for w in result['workouts'] if w['type'] == 'Natation']

    print(f"\n🚴 Cyclisme: {len(cycling)} séances")
    print(f"🏃 Course à pied: {len(running)} séances")
    print(f"🏊 Natation: {len(swimming)} séances")

    # Connexion à Garmin
    print(f"\n🔐 Connexion à Garmin Connect...")
    garmin = GarminService()
    garmin.connect()
    print("✅ Connecté\n")

    print("="*80)
    print("📤 UPLOAD DES SÉANCES")
    print("="*80)

    uploaded = []
    skipped = []
    errors = []

    # Upload cyclisme
    for workout in cycling:
        code = workout['code']

        # Vérifier si la séance a des intervalles
        if not workout.get('intervals'):
            skipped.append({
                'code': code,
                'date': workout.get('date'),
                'reason': 'Pas d\'intervalles'
            })
            print(f"\n⚠️  {code} - Séance sans intervalles (skip)")
            continue

        print(f"\n📤 {code} (Cyclisme)")
        print(f"   - Date: {workout.get('date')}")
        print(f"   - Durée: {workout.get('duration_total')}")
        print(f"   - {len(workout['intervals'])} intervalles")

        try:
            garmin_workout = convert_to_garmin_cycling_workout(workout)
            result_upload = garmin.client.upload_workout(garmin_workout)
            workout_id = result_upload.get('workoutId', 'unknown')

            print(f"   ✅ Uploadé - ID: {workout_id}")

            uploaded.append({
                'code': code,
                'type': 'Cyclisme',
                'date': workout.get('date'),
                'workout_id': workout_id
            })

        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            errors.append({
                'code': code,
                'date': workout.get('date'),
                'error': str(e)
            })

    # Upload course à pied
    for workout in running:
        code = workout['code']

        # Vérifier si c'est une séance libre
        if not workout.get('intervals'):
            skipped.append({
                'code': code,
                'date': workout.get('date'),
                'reason': 'Séance libre'
            })
            print(f"\n⚠️  {code} - Séance libre (skip)")
            continue

        print(f"\n📤 {code} (Course à pied)")
        print(f"   - Date: {workout.get('date')}")
        print(f"   - Durée: {workout.get('duration_total')}")
        print(f"   - {len(workout['intervals'])} intervalles")

        try:
            garmin_workout = convert_to_garmin_running_workout(workout)
            result_upload = garmin.client.upload_workout(garmin_workout)
            workout_id = result_upload.get('workoutId', 'unknown')

            print(f"   ✅ Uploadé - ID: {workout_id}")

            uploaded.append({
                'code': code,
                'type': 'Course à pied',
                'date': workout.get('date'),
                'workout_id': workout_id
            })

        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            errors.append({
                'code': code,
                'date': workout.get('date'),
                'error': str(e)
            })

    # TODO: Natation (quand converter sera implémenté)
    if swimming:
        print(f"\n⚠️  {len(swimming)} séances de natation non uploadées (converter non implémenté)")
        for w in swimming:
            skipped.append({
                'code': w['code'],
                'date': w.get('date'),
                'reason': 'Natation non supportée'
            })

    # Résumé final
    print(f"\n{'='*80}")
    print(f"📊 RÉSUMÉ")
    print(f"{'='*80}\n")

    if uploaded:
        print(f"✅ {len(uploaded)} séances uploadées:\n")
        for w in uploaded:
            print(f"  • {w['code']} - {w['type']} ({w['date']}) - ID: {w['workout_id']}")

    if skipped:
        print(f"\n⚠️  {len(skipped)} séances ignorées:\n")
        for w in skipped:
            print(f"  • {w['code']} ({w['date']}) - {w['reason']}")

    if errors:
        print(f"\n❌ {len(errors)} erreurs:\n")
        for w in errors:
            print(f"  • {w['code']} ({w['date']}) - {w['error']}")

    print()

    # Sauvegarder le résultat
    output_file = f"data/workouts_cache/{week}_upload_result.json"
    with open(output_file, 'w') as f:
        json.dump({
            'week': week,
            'period': period,
            'uploaded': uploaded,
            'skipped': skipped,
            'errors': errors
        }, f, indent=2, ensure_ascii=False)

    print(f"💾 Résultat sauvegardé: {output_file}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/upload_weekly_workouts.py <pdf_path>")
        print("\nExemple:")
        print('  python scripts/upload_weekly_workouts.py "/Users/aptsdae/Documents/Triathlon/Séances S07 (09_02 au 15_02)_Delalain C_2026.pdf"')
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"❌ Erreur: Le fichier n'existe pas: {pdf_path}")
        sys.exit(1)

    upload_weekly_workouts(pdf_path)
