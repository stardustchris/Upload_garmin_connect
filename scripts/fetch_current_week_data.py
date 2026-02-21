#!/usr/bin/env python3
"""
Récupère le poids et le sommeil depuis Garmin Connect pour la semaine actuelle

Usage:
    python scripts/fetch_current_week_data.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.garmin_service import GarminService

print("🔍 Récupération Poids & Sommeil Garmin Connect - Semaine Actuelle")
print("=" * 70)
print()

# Calculer la semaine actuelle (Lundi → Dimanche)
today = datetime.now()
# Trouver le lundi de cette semaine (weekday: 0=Lundi, 6=Dimanche)
days_since_monday = today.weekday()
monday = today - timedelta(days=days_since_monday)
sunday = monday + timedelta(days=6)

print(f"📅 Semaine actuelle: {monday.strftime('%d/%m/%Y')} → {sunday.strftime('%d/%m/%Y')}")
print(f"📅 Aujourd'hui: {today.strftime('%A %d/%m/%Y')}")
print()

# Connexion Garmin
print("🔐 Connexion à Garmin Connect...")
service = GarminService()
service.connect()
print("✅ Connexion réussie")
print()

# Récupérer poids et sommeil pour chaque jour jusqu'à aujourd'hui
print("📥 Récupération des données...")
print()

daily_data = []

current_date = monday
while current_date <= min(today, sunday):
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
output_file = Path(__file__).parent.parent / "data" / "garmin_current_week.json"
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(daily_data, f, indent=2, ensure_ascii=False)

print("=" * 70)
print(f"💾 Données sauvegardées: {output_file}")
print()
print("📊 RÉSUMÉ SEMAINE ACTUELLE")
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
