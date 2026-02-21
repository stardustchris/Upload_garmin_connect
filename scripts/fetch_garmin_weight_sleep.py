#!/usr/bin/env python3
"""
Récupère le poids et le sommeil depuis Garmin Connect pour la semaine S06

Usage:
    python scripts/fetch_garmin_weight_sleep.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.garmin_service import GarminService

print("🔍 Récupération Poids & Sommeil Garmin Connect - Semaine S06")
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

# Récupérer poids et sommeil pour chaque jour
print("📥 Récupération des données...")
print()

daily_data = []

current_date = START_DATE
while current_date <= END_DATE:
    date_str = current_date.strftime('%Y-%m-%d')
    day_name = current_date.strftime('%A')  # Monday, Tuesday, etc.

    print(f"📆 {day_name} {current_date.strftime('%d/%m/%Y')}")

    # Récupérer poids
    weight = service.get_weight(date_str)
    if weight:
        print(f"   ⚖️  Poids: {weight:.1f} kg")
    else:
        print(f"   ⚖️  Poids: Non disponible")

    # Récupérer sommeil
    sleep = service.get_sleep(date_str)
    if sleep:
        hours = sleep['duration_hours']
        quality = sleep['quality_score']
        print(f"   😴 Sommeil: {hours:.1f}h (qualité: {quality}/100)")
    else:
        print(f"   😴 Sommeil: Non disponible")

    daily_data.append({
        'date': date_str,
        'day_name': day_name,
        'weight_kg': weight,
        'sleep': sleep
    })

    print()
    current_date += timedelta(days=1)

# Sauvegarder les données
output_file = Path(__file__).parent.parent / "data" / "garmin_weight_sleep_s06.json"
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(daily_data, f, indent=2, ensure_ascii=False)

print("=" * 70)
print(f"💾 Données sauvegardées: {output_file}")
print()
print("📊 RÉSUMÉ SEMAINE S06")
print("=" * 70)

for data in daily_data:
    day_name = data['day_name']
    date = data['date']
    weight = data['weight_kg']
    sleep = data['sleep']

    weight_str = f"{weight:.1f} kg" if weight else "N/A"

    if sleep:
        sleep_str = f"{sleep['duration_hours']:.1f}h (Q:{sleep['quality_score']})"
    else:
        sleep_str = "N/A"

    print(f"{day_name:10s} {date}: Poids={weight_str:10s} Sommeil={sleep_str}")

print()
print("=" * 70)
print("✅ Terminé")
