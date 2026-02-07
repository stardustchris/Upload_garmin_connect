#!/usr/bin/env python3
"""
Module d'upload de workouts vers Garmin Connect via fichiers FIT
Génère des fichiers FIT natifs et les upload via l'API Garmin Connect
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import struct
import time

# Garmin Connect authentication
try:
    from garth.exc import GarthHTTPError
    from garminconnect import Garmin
except ImportError:
    print("⚠️  Installer garminconnect: pip install garminconnect garth")
    exit(1)


class FITWorkoutGenerator:
    """Génère des fichiers FIT pour workouts structurés Garmin"""

    # FIT File constants
    FIT_HEADER_SIZE = 14
    FIT_PROTOCOL_VERSION = 0x20
    FIT_PROFILE_VERSION = 2108

    # Message types
    MSG_FILE_ID = 0
    MSG_WORKOUT = 26
    MSG_WORKOUT_STEP = 27

    # Field types for cycling
    SPORT_CYCLING = 2
    SUB_SPORT_INDOOR_CYCLING = 6

    # Field types for running
    SPORT_RUNNING = 1
    SUB_SPORT_GENERIC = 0

    # Workout step types
    STEP_WARMUP = 1
    STEP_ACTIVE = 2
    STEP_COOLDOWN = 3
    STEP_REST = 4
    STEP_REPEAT = 6

    # Duration types
    DURATION_TIME = 0  # Secondes
    DURATION_OPEN = 28  # Durée libre

    # Target types
    TARGET_POWER = 1
    TARGET_POWER_ZONE = 2
    TARGET_PACE = 9
    TARGET_OPEN = 0

    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "data" / "fit_files"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def duration_to_seconds(self, duration_str: str) -> int:
        """Convertit 'mm:ss' en secondes"""
        parts = duration_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0

    def power_to_milliwatts(self, power_str: str) -> tuple:
        """Convertit '235à245' en (min_mw, max_mw)"""
        if 'à' in power_str:
            parts = power_str.replace('W', '').split('à')
            min_w = int(parts[0].strip())
            max_w = int(parts[1].strip())
            return (min_w * 1000, max_w * 1000)
        return (0, 0)

    def pace_to_mmpkm(self, pace_str: str) -> tuple:
        """Convertit '4:45à4:50' en (min_pace, max_pace) en mm:ss/km"""
        if 'à' in pace_str:
            parts = pace_str.split('à')
            min_pace = self.duration_to_seconds(parts[0].strip())
            max_pace = self.duration_to_seconds(parts[1].strip())
            return (min_pace, max_pace)
        return (0, 0)

    def generate_cycling_fit(self, workout: Dict, output_path: str) -> bool:
        """
        Génère un fichier FIT pour workout cyclisme

        Note: Génération simplifiée - utilise l'API Garmin pour créer le workout
        plutôt que de générer le binaire FIT complet (très complexe)
        """

        print(f"⚠️  Génération FIT binaire complexe - utilisation API Garmin à la place")
        return False

    def create_workout_via_api(self, workout: Dict, garmin_client: Garmin) -> Optional[str]:
        """
        Crée un workout structuré via l'API Garmin Connect

        Returns:
            workout_id si succès, None sinon
        """

        workout_name = f"{workout['code']} - {workout.get('description', 'Cyclisme HT')}"

        # Construire structure de workout pour API Garmin
        workout_data = {
            "workoutName": workout_name,
            "description": workout.get('notes', ''),
            "sport": {
                "sportTypeId": 2,  # Cycling
                "sportTypeKey": "cycling"
            },
            "workoutSegments": []
        }

        # Convertir intervalles en segments Garmin
        for i, interval in enumerate(workout.get('intervals', [])):
            segment = self._interval_to_garmin_segment(interval, i)
            if segment:
                workout_data["workoutSegments"].append(segment)

        try:
            # API endpoint pour créer workout
            response = garmin_client.connectapi(
                f"/workout-service/workout",
                method="POST",
                data=workout_data
            )

            if response and 'workoutId' in response:
                workout_id = response['workoutId']
                print(f"✅ Workout créé : {workout_name} (ID: {workout_id})")

                # Programmer à la date spécifiée
                if 'date' in workout:
                    self._schedule_workout(garmin_client, workout_id, workout['date'])

                return workout_id
            else:
                print(f"❌ Erreur création workout: {response}")
                return None

        except Exception as e:
            print(f"❌ Exception lors de la création: {e}")
            return None

    def _interval_to_garmin_segment(self, interval: Dict, index: int) -> Optional[Dict]:
        """Convertit un intervalle JSON en segment Garmin API"""

        duration_seconds = self.duration_to_seconds(interval.get('duration', '0:00'))

        # Type de step
        phase = interval.get('phase', '').lower()
        if 'échauffement' in phase or 'echauffement' in phase:
            step_type = 1  # WARMUP
        elif 'récupération' in phase:
            step_type = 3  # COOLDOWN
        elif 'repos' in phase or interval.get('power_watts', '').startswith('160à170'):
            step_type = 4  # REST
        else:
            step_type = 2  # ACTIVE

        segment = {
            "segmentOrder": index + 1,
            "sportType": {
                "sportTypeId": 2,
                "sportTypeKey": "cycling"
            },
            "workoutSteps": [
                {
                    "type": "ExecutableStepDTO",
                    "stepId": None,
                    "stepOrder": 1,
                    "stepType": {
                        "stepTypeId": step_type,
                        "stepTypeKey": self._get_step_type_key(step_type)
                    },
                    "endCondition": {
                        "conditionTypeKey": "time",
                        "conditionTypeId": 2
                    },
                    "endConditionValue": duration_seconds,
                    "targetType": {
                        "workoutTargetTypeId": 1,  # POWER
                        "workoutTargetTypeKey": "power.zone"
                    }
                }
            ]
        }

        # Ajouter target de puissance si disponible
        power_watts = interval.get('power_watts', '')
        if power_watts and 'à' in power_watts:
            min_mw, max_mw = self.power_to_milliwatts(power_watts)
            segment["workoutSteps"][0]["targetValueOne"] = min_mw
            segment["workoutSteps"][0]["targetValueTwo"] = max_mw

        return segment

    def _get_step_type_key(self, step_type_id: int) -> str:
        """Retourne la clé textuelle du type de step"""
        mapping = {
            1: "warmup",
            2: "active",
            3: "cooldown",
            4: "rest",
            6: "repeat"
        }
        return mapping.get(step_type_id, "active")

    def _schedule_workout(self, garmin_client: Garmin, workout_id: str, date_str: str):
        """Programme un workout à une date spécifique"""

        try:
            # Convertir date "2026-02-02" en timestamp
            workout_date = datetime.strptime(date_str, "%Y-%m-%d")

            schedule_data = {
                "workoutId": workout_id,
                "date": date_str
            }

            response = garmin_client.connectapi(
                f"/workout-service/schedule/{workout_id}",
                method="PUT",
                data=schedule_data
            )

            print(f"📅 Workout programmé pour le {date_str}")

        except Exception as e:
            print(f"⚠️  Impossible de programmer le workout: {e}")


class GarminWorkoutUploader:
    """Upload automatisé de workouts vers Garmin Connect"""

    def __init__(self, email: str = None, password: str = None):
        self.email = email or os.getenv('GARMIN_EMAIL')
        self.password = password or os.getenv('GARMIN_PASSWORD')
        self.garmin_client = None
        self.fit_generator = FITWorkoutGenerator()

    def login(self) -> bool:
        """Connexion à Garmin Connect"""

        if not self.email or not self.password:
            print("❌ GARMIN_EMAIL et GARMIN_PASSWORD requis dans .env")
            return False

        try:
            print(f"🔐 Connexion à Garmin Connect ({self.email})...")
            self.garmin_client = Garmin(self.email, self.password)
            self.garmin_client.login()
            print("✅ Connexion réussie")
            return True

        except GarthHTTPError as e:
            print(f"❌ Erreur d'authentification: {e}")
            return False
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            return False

    def upload_workout(self, workout: Dict) -> bool:
        """Upload un workout vers Garmin Connect"""

        if not self.garmin_client:
            if not self.login():
                return False

        workout_type = workout.get('type', '')
        code = workout.get('code', 'Unknown')

        print(f"\n📤 Upload {code} ({workout_type})...")

        if workout_type == "Cyclisme":
            return self._upload_cycling(workout)
        elif workout_type == "Course à pied":
            return self._upload_running(workout)
        elif workout_type == "Natation":
            print(f"⚠️  Natation non supportée pour l'instant")
            return False
        else:
            print(f"❌ Type inconnu: {workout_type}")
            return False

    def _upload_cycling(self, workout: Dict) -> bool:
        """Upload workout cyclisme"""

        try:
            workout_id = self.fit_generator.create_workout_via_api(
                workout,
                self.garmin_client
            )

            return workout_id is not None

        except Exception as e:
            print(f"❌ Erreur upload cyclisme: {e}")
            return False

    def _upload_running(self, workout: Dict) -> bool:
        """Upload workout course à pied"""

        # TODO: Implémenter upload CAP
        print(f"⚠️  Upload CAP pas encore implémenté")
        return False

    def upload_from_json(self, json_path: str) -> Dict[str, bool]:
        """
        Upload tous les workouts depuis un fichier JSON

        Returns:
            Dict {workout_code: success_bool}
        """

        with open(json_path, 'r') as f:
            data = json.load(f)

        results = {}

        for workout in data.get('workouts', []):
            code = workout['code']

            try:
                success = self.upload_workout(workout)
                results[code] = success

                # Pause entre uploads pour éviter rate limiting
                time.sleep(2)

            except Exception as e:
                print(f"❌ Exception {code}: {e}")
                results[code] = False

        return results


def main():
    """Test standalone"""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python garmin_fit_uploader.py <workout_code> [json_path]")
        print("Exemple: python garmin_fit_uploader.py C18")
        sys.exit(1)

    workout_code = sys.argv[1]
    json_path = sys.argv[2] if len(sys.argv) > 2 else "data/workouts_cache/S06_workouts_v6_near_final.json"

    # Charger JSON
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Trouver le workout
    workout = None
    for w in data.get('workouts', []):
        if w['code'] == workout_code:
            workout = w
            break

    if not workout:
        print(f"❌ Workout {workout_code} non trouvé dans {json_path}")
        sys.exit(1)

    # Upload
    uploader = GarminWorkoutUploader()

    success = uploader.upload_workout(workout)

    if success:
        print(f"\n✅ {workout_code} uploadé avec succès")
        sys.exit(0)
    else:
        print(f"\n❌ Échec upload {workout_code}")
        sys.exit(1)


if __name__ == "__main__":
    main()
