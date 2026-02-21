#!/usr/bin/env python3
"""
Remplit le fichier Excel S06 avec les données RÉELLES depuis Garmin Connect

Lit les activités Garmin Connect et remplit les volumes (distance, durée)
dans les feuilles quotidiennes (Lundi-Dimanche)

Usage:
    python scripts/fill_excel_from_garmin.py
"""

import sys
from pathlib import Path
import json
from datetime import datetime
import subprocess
import time

# Importer xlrd pour lire et xlwt pour écrire .xls
try:
    import xlrd
    import xlwt
    from xlutils.copy import copy as xl_copy
except ImportError:
    print("❌ xlrd/xlwt/xlutils non installés. Installation...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xlrd", "xlwt", "xlutils"])
    import xlrd
    import xlwt
    from xlutils.copy import copy as xl_copy


EXCEL_FILE = Path("/Users/aptsdae/Documents/Triathlon/S06_Delalain C_2026.xls")
ACTIVITIES_FILE = Path(__file__).parent.parent / "data" / "garmin_activities_s06.json"


def seconds_to_excel_time(seconds: float) -> float:
    """Convertit secondes en format Excel time (fraction de jour)"""
    hours = seconds / 3600.0
    return hours / 24.0


def meters_to_km(meters: float) -> float:
    """Convertit mètres en kilomètres"""
    return meters / 1000.0


def extract_workout_code(activity_name: str) -> str:
    """Extrait le code de workout (ex: 'Sciez - CAP17' → 'CAP17')"""
    import re
    # Pattern: CAP suivi de chiffres, ou C suivi de chiffres, ou N suivi de chiffres
    match = re.search(r'\b(CAP\d+|C\d+|N\d+)\b', activity_name)
    if match:
        return match.group(1)
    # Si pas de pattern trouvé, retourner le nom complet
    return activity_name


def force_excel_recalculation(file_path: Path):
    """Force Excel à ouvrir le fichier et recalculer les formules via AppleScript"""
    print()
    print("🔄 Ouverture dans Excel pour recalcul des formules...")

    applescript = f'''
    tell application "Microsoft Excel"
        activate
        open POSIX file "{file_path}"
    end tell
    '''

    try:
        result = subprocess.run(['osascript', '-e', applescript], check=True, capture_output=True, text=True)
        print("✅ Fichier ouvert dans Excel")
        print("💡 Excel va recalculer automatiquement les formules")
        print("💡 Vérifiez l'onglet Synthèse pour voir les totaux")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Impossible d'ouvrir Excel automatiquement")
        print(f"   Erreur: {e.stderr.strip()}")
        print()
        print("💡 Ouvrez manuellement le fichier:")
        print(f"   open '{file_path}'")
        return False


# Mapping jour de la semaine → index de feuille Excel (0-based)
DAY_SHEET_MAP = {
    'Monday': 2,     # Lundi
    'Tuesday': 3,    # Mardi
    'Wednesday': 4,  # Mercredi
    'Thursday': 5,   # Jeudi
    'Friday': 6,     # Vendredi
    'Saturday': 7,   # Samedi
    'Sunday': 8      # Dimanche
}

DAY_NAME_FR = {
    'Monday': 'Lundi',
    'Tuesday': 'Mardi',
    'Wednesday': 'Mercredi',
    'Thursday': 'Jeudi',
    'Friday': 'Vendredi',
    'Saturday': 'Samedi',
    'Sunday': 'Dimanche'
}

# Mapping type d'activité → colonnes Excel
# Pour chaque discipline :
# Ligne 4 (index 3) : "Séance n°" - CELLULES FUSIONNÉES
# Ligne 5 (index 4) : Volume (m/km) et Durée (hh:min)
#
# Natation: seance_col=5 (F, fusionnée F-G), volume_col=5 (m), time_col=6 (hh:min)
# Cyclisme: seance_col=8 (I, fusionnée I-J), volume_col=8 (km), time_col=9 (hh:min)
# Course à pied: seance_col=11 (L, fusionnée L-M), volume_col=11 (km), time_col=12 (hh:min)
ACTIVITY_TYPE_COLUMNS = {
    'lap_swimming': (5, 5, 6),      # Natation: (seance_col, volume_col, time_col)
    'indoor_cycling': (8, 8, 9),    # Cyclisme indoor
    'cycling': (8, 8, 9),           # Cyclisme
    'running': (11, 11, 12),        # Course à pied
}


def main():
    print("📊 Remplissage Excel depuis Activités Garmin Connect")
    print("=" * 70)
    print()

    # Charger les activités Garmin
    if not ACTIVITIES_FILE.exists():
        print(f"❌ Fichier activités introuvable: {ACTIVITIES_FILE}")
        print("   Exécutez d'abord: python scripts/fetch_garmin_activities.py")
        return

    with open(ACTIVITIES_FILE) as f:
        activities = json.load(f)

    print(f"📂 Activités chargées: {len(activities)}")
    for activity in activities:
        name = activity.get('activityName', 'N/A')
        activity_type = activity.get('activityType', {}).get('typeKey', 'N/A')
        date_str = activity.get('startTimeLocal', 'N/A')
        print(f"   - {name} ({activity_type}) - {date_str}")
    print()

    # Ouvrir le fichier Excel
    print(f"📁 Ouverture: {EXCEL_FILE.name}")
    workbook_read = xlrd.open_workbook(str(EXCEL_FILE), formatting_info=True)
    workbook_write = xl_copy(workbook_read)

    modifications = []

    # Pour chaque activité
    for activity in activities:
        activity_id = activity.get('activityId')
        activity_name_raw = activity.get('activityName', 'N/A')
        activity_name = extract_workout_code(activity_name_raw)  # Nettoyer le nom
        activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')
        start_time_local = activity.get('startTimeLocal', '')
        duration_sec = activity.get('duration', 0)
        distance_m = activity.get('distance', 0)

        # Parser la date pour trouver le jour de la semaine
        if not start_time_local:
            print(f"⚠️  Pas de date pour {activity_name} - ignoré")
            continue

        # Format: "2026-02-06 21:38:37"
        activity_datetime = datetime.fromisoformat(start_time_local)
        day_of_week = activity_datetime.strftime('%A')  # Monday, Tuesday, etc.

        # Trouver les colonnes pour ce type d'activité
        if activity_type not in ACTIVITY_TYPE_COLUMNS:
            print(f"⚠️  Type inconnu '{activity_type}' pour {activity_name} - ignoré")
            continue

        seance_col, volume_col, time_col = ACTIVITY_TYPE_COLUMNS[activity_type]

        # Récupérer la feuille du jour
        if day_of_week not in DAY_SHEET_MAP:
            print(f"⚠️  Jour invalide '{day_of_week}' - ignoré")
            continue

        sheet_idx = DAY_SHEET_MAP[day_of_week]
        sheet_write = workbook_write.get_sheet(sheet_idx)

        # Ligne 4 (index 3) : "Séance n°"
        # Ligne 5 (index 4) : En-têtes (Volume total, km, hh:min)
        # Ligne 6 (index 5) : VALEURS - Volume et Durée
        seance_row_idx = 3
        volume_row_idx = 5

        # Écrire le nom de la séance (ligne 4) - SANS STYLE
        sheet_write.write(seance_row_idx, seance_col, activity_name)

        # Écrire volume (distance) - ligne 6 - SANS STYLE
        if activity_type == 'lap_swimming':
            # Natation en mètres
            volume_value = float(distance_m)
            volume_unit = 'm'
        else:
            # Cyclisme et CAP en km
            volume_value = meters_to_km(distance_m)
            volume_unit = 'km'

        # Écrire VALEUR BRUTE sans formatage
        sheet_write.write(volume_row_idx, volume_col, volume_value)

        # Écrire durée (hh:mm) - ligne 6 - VALEUR BRUTE (fraction de jour)
        excel_time = seconds_to_excel_time(duration_sec)
        sheet_write.write(volume_row_idx, time_col, excel_time)

        # Convertir durée en format lisible
        duration_h = int(duration_sec // 3600)
        duration_m = int((duration_sec % 3600) // 60)
        duration_str = f"{duration_h:02d}:{duration_m:02d}"

        jour_fr = DAY_NAME_FR[day_of_week]

        modifications.append({
            'name': activity_name,
            'type': activity_type,
            'jour': jour_fr,
            'volume': f"{volume_value:.2f} {volume_unit}",
            'duration': duration_str,
            'cells': f"{chr(65 + seance_col)}{seance_row_idx + 1}, {chr(65 + volume_col)}{volume_row_idx + 1}, {chr(65 + time_col)}{volume_row_idx + 1}"
        })

        print(f"✅ {activity_name:15s} ({activity_type:15s}) → {jour_fr:9s}")
        print(f"   └─ Séance: {activity_name} (cellule {chr(65 + seance_col)}{seance_row_idx + 1})")
        print(f"   └─ Volume: {volume_value:.2f} {volume_unit} (cellule {chr(65 + volume_col)}{volume_row_idx + 1})")
        print(f"   └─ Durée: {duration_str} (cellule {chr(65 + time_col)}{volume_row_idx + 1})")

    print()
    print("=" * 70)

    # Sauvegarder
    output_file = EXCEL_FILE.parent / f"{EXCEL_FILE.stem}_garmin{EXCEL_FILE.suffix}"
    workbook_write.save(str(output_file))

    print(f"✅ Fichier sauvegardé: {output_file}")
    print()
    print(f"📊 {len(modifications)} activités remplies:")
    for mod in modifications:
        print(f"   - {mod['name']:15s} ({mod['jour']:9s}): {mod['volume']:12s} / {mod['duration']}")
    print()

    # Forcer Excel à recalculer les formules
    force_excel_recalculation(output_file)

    print()
    print("💡 Vérifier le fichier Excel:")
    print(f"   open '{output_file}'")


if __name__ == '__main__':
    main()
