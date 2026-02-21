#!/usr/bin/env python3
"""
Remplit automatiquement les volumes (durée) dans le fichier Excel S06

Lit les workouts parsés et remplit les colonnes hh:min pour chaque discipline
dans les feuilles quotidiennes (Lundi-Dimanche)

Usage:
    python scripts/fill_excel_volumes.py
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Importer xlrd pour lire et xlwt pour écrire .xls
try:
    import xlrd
    import xlwt
    from xlutils.copy import copy as xl_copy
except ImportError:
    print("❌ xlrd/xlwt/xlutils non installés. Installation...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xlrd", "xlwt", "xlutils"])
    import xlrd
    import xlwt
    from xlutils.copy import copy as xl_copy


# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))


EXCEL_FILE = Path("/Users/aptsdae/Documents/Triathlon/S06_Delalain C_2026.xls")
WORKOUT_FILE = Path(__file__).parent.parent / "data" / "workouts_cache" / "S06_workouts_v6_near_final.json"


def parse_duration_to_minutes(duration_str: str) -> int:
    """Convertit durée MM:SS en minutes totales"""
    if ':' in duration_str:
        parts = duration_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    else:
        return int(duration_str) * 60


def minutes_to_excel_time(minutes: int) -> float:
    """Convertit minutes en format Excel time (fraction de jour)"""
    # Excel stocke les heures comme fraction de 24h
    # 1:00 = 1/24 = 0.041666...
    hours = minutes / 60.0
    return hours / 24.0


def get_workout_duration_minutes(workout_json: dict) -> int:
    """Calcule la durée totale d'un workout en minutes"""
    # Si workout structuré avec intervalles
    if workout_json.get('intervals') and len(workout_json['intervals']) > 0:
        total_seconds = sum(
            parse_duration_to_minutes(interval['duration'])
            for interval in workout_json['intervals']
        )
        return total_seconds // 60

    # Sinon utiliser duration_total (format "0h45" ou "1h00")
    duration_total = workout_json.get('duration_total')
    if duration_total and 'h' in duration_total:
        parts = duration_total.replace('h', ':').split(':')
        hours = int(parts[0]) if parts[0] else 0
        minutes = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        return hours * 60 + minutes

    return 0


def get_swim_volume_meters(workout_json: dict) -> int:
    """Extrait le volume de natation en mètres"""
    # Chercher dans les series pour "2500 m" ou similaire
    for serie in workout_json.get('series', []):
        desc = serie.get('description', '')
        # Pattern: "2500 m" ou "2500m"
        import re
        match = re.search(r'(\d+)\s*m\b', desc, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def estimate_swim_duration_minutes(meters: int) -> int:
    """Estime la durée de natation basée sur volume (3km/h = 50m/min)"""
    if meters == 0:
        return 0
    # Vitesse moyenne: 3 km/h = 3000m/60min = 50m/min
    return int(meters / 50)


# Mapping jour → index de feuille (0-based)
DAY_SHEET_MAP = {
    'Lundi': 2,
    'Mardi': 3,
    'Mercredi': 4,
    'Jeudi': 5,
    'Vendredi': 6,
    'Samedi': 7,
    'Dimanche': 8
}

# Mapping code workout → (jour, discipline_col_volume, discipline_col_time)
# Colonnes pour chaque discipline (basé sur ligne 5 des feuilles journalières):
# Natation: col 5 (m), col 6 (hh:min)
# Cyclisme: col 8 (km), col 9 (hh:min)
# Course à pied: col 11 (km), col 12 (hh:min)
WORKOUT_MAPPING = {
    'C16': ('Lundi', None, 9),       # Cyclisme - pas de distance, juste durée
    'CAP16': ('Mardi', None, 12),    # Course à pied
    'N5': ('Mercredi', 5, 6),        # Natation - mètres + durée
    'CAP17': ('Mercredi', None, 12), # Course à pied (S1)
    'C17': ('Jeudi', None, 9),       # Cyclisme
    'CAP18': ('Vendredi', None, 12), # Course à pied (S1)
    'C18': ('Samedi', None, 9),      # Cyclisme (S1)
    'CAP19': ('Samedi', None, 12),   # Course à pied (S2)
    'C19': ('Dimanche', None, 9),    # Cyclisme
}


def main():
    print("📊 Remplissage automatique du fichier Excel S06")
    print("=" * 70)
    print()

    # Charger les workouts
    with open(WORKOUT_FILE) as f:
        data = json.load(f)

    workouts = {w['code']: w for w in data['workouts']}

    print(f"📂 Workouts chargés: {len(workouts)}")
    for code in sorted(workouts.keys()):
        w = workouts[code]
        duration_min = get_workout_duration_minutes(w)
        print(f"   - {code:6s} ({w['type']:12s}): {duration_min} min")
    print()

    # Ouvrir le fichier Excel
    print(f"📁 Ouverture: {EXCEL_FILE.name}")
    workbook_read = xlrd.open_workbook(str(EXCEL_FILE), formatting_info=True)
    workbook_write = xl_copy(workbook_read)

    modifications = []

    # Pour chaque workout à mapper
    for code, (jour, col_volume, col_time) in WORKOUT_MAPPING.items():
        if code not in workouts:
            print(f"⚠️  {code} non trouvé dans les workouts parsés")
            continue

        workout = workouts[code]

        # Récupérer la feuille du jour
        sheet_idx = DAY_SHEET_MAP[jour]
        sheet_write = workbook_write.get_sheet(sheet_idx)

        # La ligne pour "Volume total" est ligne 5 (index 4)
        row_idx = 4

        # Traitement spécial pour natation
        if workout['type'] == 'Natation':
            meters = get_swim_volume_meters(workout)
            duration_min = estimate_swim_duration_minutes(meters)

            # Écrire volume (mètres)
            if col_volume is not None and meters > 0:
                sheet_write.write(row_idx, col_volume, float(meters))
                print(f"✅ {code:6s} → {jour:9s} : {meters} m (cellule {chr(65 + col_volume)}{row_idx + 1})")

            # Écrire durée (hh:mm)
            if col_time is not None and duration_min > 0:
                excel_time = minutes_to_excel_time(duration_min)
                style_time = xlwt.XFStyle()
                style_time.num_format_str = 'hh:mm'
                sheet_write.write(row_idx, col_time, excel_time, style_time)
                print(f"   └─ Durée estimée : {duration_min} min (cellule {chr(65 + col_time)}{row_idx + 1})")

            modifications.append({
                'code': code,
                'jour': jour,
                'volume_m': meters,
                'duration_min': duration_min,
                'cells': f"{chr(65 + col_volume) if col_volume else ''}{row_idx + 1}, {chr(65 + col_time)}{row_idx + 1}"
            })

        else:
            # Cyclisme et Course à pied : juste durée
            duration_min = get_workout_duration_minutes(workout)

            if col_time is not None and duration_min > 0:
                excel_time = minutes_to_excel_time(duration_min)
                style_time = xlwt.XFStyle()
                style_time.num_format_str = 'hh:mm'
                sheet_write.write(row_idx, col_time, excel_time, style_time)

                modifications.append({
                    'code': code,
                    'jour': jour,
                    'duration_min': duration_min,
                    'cell': f"{chr(65 + col_time)}{row_idx + 1}"
                })

                print(f"✅ {code:6s} → {jour:9s} : {duration_min} min (cellule {chr(65 + col_time)}{row_idx + 1})")

    print()
    print("=" * 70)

    # Sauvegarder
    output_file = EXCEL_FILE.parent / f"{EXCEL_FILE.stem}_filled{EXCEL_FILE.suffix}"
    workbook_write.save(str(output_file))

    print(f"✅ Fichier sauvegardé: {output_file}")
    print()
    print(f"📊 {len(modifications)} volumes remplis:")
    for mod in modifications:
        print(f"   - {mod['code']:6s} ({mod['jour']:9s}): {mod['duration_min']} min → {mod['cell']}")
    print()

    print("💡 Vérifier le fichier Excel:")
    print(f"   open '{output_file}'")


if __name__ == '__main__':
    main()
