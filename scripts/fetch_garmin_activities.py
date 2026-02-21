#!/usr/bin/env python3
"""
Récupère les activités Garmin Connect pour une période donnée

Utilise l'API Garmin Connect pour fetcher toutes les activités de la semaine S06
(02/02/2026 au 08/02/2026) et affiche les données (distance, durée, calories, etc.)

Usage:
    python scripts/fetch_garmin_activities.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.garmin_service import GarminService

print("🔍 Récupération Activités Garmin Connect - Semaine S06")
print("=" * 70)
print()

# Dates S06: du 02/02/2026 au 08/02/2026
START_DATE = datetime(2026, 2, 2)
END_DATE = datetime(2026, 2, 8)

print(f"📅 Période: {START_DATE.strftime('%d/%m/%Y')} → {END_DATE.strftime('%d/%m/%Y')}")
print()

# Connexion Garmin
print("🔐 Connexion à Garmin Connect...")
service = GarminService()
service.connect()
print("✅ Connexion réussie")
print()

# Récupérer les activités
print("📥 Récupération des activités...")

# La méthode get_activities() retourne les activités récentes
# On va fetcher activité par activité en utilisant start/limit
all_activities = []

try:
    # Fetcher les dernières 100 activités (devrait couvrir la période)
    activities = service.client.get_activities(0, 100)

    # Filtrer par date (dans la plage S06)
    for activity in activities:
        # La date est au format ISO string "2026-02-03 10:30:00"
        activity_date_str = activity.get('startTimeLocal', '')

        if activity_date_str:
            # Parser la date
            activity_date = datetime.fromisoformat(activity_date_str.split(' ')[0])

            # Vérifier si dans la plage
            if START_DATE <= activity_date <= END_DATE:
                all_activities.append(activity)

    print(f"✅ {len(all_activities)} activités trouvées dans la période")
    print()

    # Afficher les activités
    if all_activities:
        print("📋 ACTIVITÉS S06")
        print("=" * 70)
        print()

        for idx, activity in enumerate(all_activities, 1):
            activity_id = activity.get('activityId')
            activity_name = activity.get('activityName', 'N/A')
            activity_type = activity.get('activityType', {}).get('typeKey', 'N/A')
            start_time = activity.get('startTimeLocal', 'N/A')
            duration_sec = activity.get('duration', 0)
            distance_m = activity.get('distance', 0)
            calories = activity.get('calories', 0)

            # Convertir durée en HH:MM:SS
            duration_h = int(duration_sec // 3600)
            duration_m = int((duration_sec % 3600) // 60)
            duration_s = int(duration_sec % 60)
            duration_str = f"{duration_h:02d}:{duration_m:02d}:{duration_s:02d}"

            # Convertir distance en km (ou m pour natation)
            if activity_type == 'lap_swimming':
                distance_str = f"{int(distance_m)} m"
            else:
                distance_km = distance_m / 1000.0
                distance_str = f"{distance_km:.2f} km"

            print(f"Activité #{idx}")
            print(f"   ID: {activity_id}")
            print(f"   URL: https://connect.garmin.com/app/activity/{activity_id}")
            print(f"   Nom: {activity_name}")
            print(f"   Type: {activity_type}")
            print(f"   Date: {start_time}")
            print(f"   Durée: {duration_str}")
            print(f"   Distance: {distance_str}")
            print(f"   Calories: {calories} kcal")
            print()

        # Sauvegarder les données brutes
        output_file = Path(__file__).parent.parent / "data" / "garmin_activities_s06.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(all_activities, f, indent=2, ensure_ascii=False)

        print("=" * 70)
        print(f"💾 Données sauvegardées: {output_file}")
        print()
        print("🔗 URLs des activités:")
        for activity in all_activities:
            activity_id = activity.get('activityId')
            activity_name = activity.get('activityName', 'N/A')
            print(f"   - {activity_name}: https://connect.garmin.com/app/activity/{activity_id}")

    else:
        print("⚠️  Aucune activité trouvée pour la période S06")

except Exception as e:
    print(f"❌ Erreur lors de la récupération des activités: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("✅ Terminé")
