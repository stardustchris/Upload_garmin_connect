#!/usr/bin/env python3
"""
Remplit le fichier Google Sheets avec les données RÉELLES depuis Garmin Connect

Utilise l'API Google Sheets pour modifier directement le fichier en ligne.

Usage:
    python scripts/fill_gsheets_from_garmin.py
"""

import sys
from pathlib import Path
import json
from datetime import datetime
import re

# Google Sheets API
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ google-api-python-client non installé. Installation...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib"
    ])
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError


# ID du fichier Google Sheets (extrait de l'URL)
SPREADSHEET_ID = "1m3GJChwbN-UEvi4pmBZ6qBsMGZvjAsx7"

# Scopes nécessaires pour modifier le fichier
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

ACTIVITIES_FILE = Path(__file__).parent.parent / "data" / "garmin_activities_s06.json"
TOKEN_FILE = Path(__file__).parent.parent / "credentials" / "token.json"
CREDENTIALS_FILE = Path(__file__).parent.parent / "credentials" / "credentials.json"


def seconds_to_duration_string(seconds: float) -> str:
    """Convertit secondes en format hh:mm pour Google Sheets"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours:02d}:{minutes:02d}"


def meters_to_km(meters: float) -> float:
    """Convertit mètres en kilomètres"""
    return meters / 1000.0


def extract_workout_code(activity_name: str) -> str:
    """Extrait le code de workout (ex: 'Sciez - CAP17' → 'CAP17')"""
    match = re.search(r'\b(CAP\d+|C\d+|N\d+)\b', activity_name)
    if match:
        return match.group(1)
    return activity_name


# Mapping jour de la semaine → nom de feuille Google Sheets
DAY_SHEET_MAP = {
    'Monday': 'Lundi',
    'Tuesday': 'Mardi',
    'Wednesday': 'Mercredi',
    'Thursday': 'Jeudi',
    'Friday': 'Vendredi',
    'Saturday': 'Samedi',
    'Sunday': 'Dimanche'
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

# Mapping type d'activité → colonnes Google Sheets (lettres)
# Natation: seance_col=F, volume_col=F (m), time_col=G (hh:min)
# Cyclisme: seance_col=I, volume_col=I (km), time_col=J (hh:min)
# Course à pied: seance_col=L, volume_col=L (km), time_col=M (hh:min)
ACTIVITY_TYPE_COLUMNS = {
    'lap_swimming': ('F', 'F', 'G'),
    'indoor_cycling': ('I', 'I', 'J'),
    'cycling': ('I', 'I', 'J'),
    'running': ('L', 'L', 'M'),
}


def get_google_sheets_service():
    """Authentifie et retourne le service Google Sheets API"""
    creds = None

    # Créer le répertoire credentials s'il n'existe pas
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Charger les credentials existants
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Si pas de credentials valides, demander l'authentification
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print("❌ Fichier credentials.json introuvable!")
                print(f"   Téléchargez-le depuis Google Cloud Console et placez-le ici:")
                print(f"   {CREDENTIALS_FILE}")
                print()
                print("   Instructions:")
                print("   1. Allez sur https://console.cloud.google.com/")
                print("   2. Créez un projet ou sélectionnez-en un")
                print("   3. Activez l'API Google Sheets")
                print("   4. Créez des identifiants OAuth 2.0 (Application de bureau)")
                print("   5. Téléchargez le fichier JSON et renommez-le credentials.json")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Sauvegarder les credentials pour la prochaine fois
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('sheets', 'v4', credentials=creds)


def main():
    print("📊 Remplissage Google Sheets depuis Activités Garmin Connect")
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

    # Authentifier avec Google Sheets API
    print("🔐 Authentification Google Sheets...")
    service = get_google_sheets_service()
    print("✅ Authentifié")
    print()

    modifications = []
    batch_update_data = []

    # Pour chaque activité
    for activity in activities:
        activity_name_raw = activity.get('activityName', 'N/A')
        activity_name = extract_workout_code(activity_name_raw)
        activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')
        start_time_local = activity.get('startTimeLocal', '')
        duration_sec = activity.get('duration', 0)
        distance_m = activity.get('distance', 0)

        # Parser la date pour trouver le jour de la semaine
        if not start_time_local:
            print(f"⚠️  Pas de date pour {activity_name} - ignoré")
            continue

        activity_datetime = datetime.fromisoformat(start_time_local)
        day_of_week = activity_datetime.strftime('%A')

        # Trouver les colonnes pour ce type d'activité
        if activity_type not in ACTIVITY_TYPE_COLUMNS:
            print(f"⚠️  Type inconnu '{activity_type}' pour {activity_name} - ignoré")
            continue

        seance_col, volume_col, time_col = ACTIVITY_TYPE_COLUMNS[activity_type]

        # Récupérer le nom de la feuille
        if day_of_week not in DAY_SHEET_MAP:
            print(f"⚠️  Jour invalide '{day_of_week}' - ignoré")
            continue

        sheet_name = DAY_SHEET_MAP[day_of_week]

        # Lignes: 4 pour séance, 6 pour données
        seance_row = 4
        volume_row = 6

        # Préparer les valeurs
        if activity_type == 'lap_swimming':
            volume_value = float(distance_m)
            volume_unit = 'm'
        else:
            volume_value = meters_to_km(distance_m)
            volume_unit = 'km'

        duration_str = seconds_to_duration_string(duration_sec)

        # Ajouter les mises à jour au batch
        # 1. Nom de la séance
        batch_update_data.append({
            'range': f'{sheet_name}!{seance_col}{seance_row}',
            'values': [[activity_name]]
        })

        # 2. Volume
        batch_update_data.append({
            'range': f'{sheet_name}!{volume_col}{volume_row}',
            'values': [[volume_value]]
        })

        # 3. Durée
        batch_update_data.append({
            'range': f'{sheet_name}!{time_col}{volume_row}',
            'values': [[duration_str]]
        })

        jour_fr = DAY_NAME_FR[day_of_week]

        modifications.append({
            'name': activity_name,
            'type': activity_type,
            'jour': jour_fr,
            'volume': f"{volume_value:.2f} {volume_unit}",
            'duration': duration_str,
            'cells': f"{seance_col}{seance_row}, {volume_col}{volume_row}, {time_col}{volume_row}"
        })

        print(f"✅ {activity_name:15s} ({activity_type:15s}) → {jour_fr:9s}")
        print(f"   └─ Séance: {activity_name} (cellule {seance_col}{seance_row})")
        print(f"   └─ Volume: {volume_value:.2f} {volume_unit} (cellule {volume_col}{volume_row})")
        print(f"   └─ Durée: {duration_str} (cellule {time_col}{volume_row})")

    print()
    print("=" * 70)

    # Exécuter toutes les mises à jour en une seule requête batch
    if batch_update_data:
        print(f"📝 Écriture de {len(batch_update_data)} cellules dans Google Sheets...")

        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': batch_update_data
        }

        try:
            result = service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()

            print(f"✅ {result.get('totalUpdatedCells')} cellules mises à jour")
        except HttpError as error:
            print(f"❌ Erreur lors de la mise à jour: {error}")
            return

    print()
    print(f"📊 {len(modifications)} activités remplies:")
    for mod in modifications:
        print(f"   - {mod['name']:15s} ({mod['jour']:9s}): {mod['volume']:12s} / {mod['duration']}")
    print()

    print("💡 Les formules de l'onglet Synthèse se recalculent automatiquement")
    print(f"💡 Vérifiez le fichier: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


if __name__ == '__main__':
    main()
