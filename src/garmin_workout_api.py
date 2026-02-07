#!/usr/bin/env python3
"""
Upload de workouts vers Garmin Connect via API directe (sans fichiers FIT)
Utilise l'API interne de Garmin Connect pour créer des workouts structurés
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import time

import garth
from garminconnect import Garmin


class GarminWorkoutAPIUploader:
    """Upload workouts via API Garmin Connect (workout service)"""

    def __init__(self):
        self.garmin_client = None
        self.garth_dir = Path.home() / ".garth"

    def login(self) -> bool:
        """Connexion à Garmin Connect avec tokens sauvegardés"""

        # Vérifier si tokens existent
        if not self.garth_dir.exists():
            print("❌ Tokens Garmin non trouvés")
            print("Exécutez d'abord: python src/garmin_auth.py")
            return False

        try:
            print("🔐 Chargement tokens Garmin...")
            garth.resume(str(self.garth_dir))
            garth.client.username  # Test si tokens valides

            # Créer client garminconnect
            self.garmin_client = Garmin()
            self.garmin_client.login()

            print("✅ Connexion réussie (tokens réutilisés)")
            return True

        except Exception as e:
            print(f"❌ Tokens expirés ou invalides: {e}")
            print("Ré-authentifiez avec: python src/garmin_auth.py")
            return False

    def duration_to_seconds(self, duration_str: str) -> int:
        """Convertit 'mm:ss' ou 'h:mm' en secondes"""
        parts = duration_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0

    def power_to_watts(self, power_str: str) -> tuple:
        """Convertit '235à245' en (235, 245)"""
        if 'à' in power_str:
            parts = power_str.replace('W', '').split('à')
            return (int(parts[0].strip()), int(parts[1].strip()))
        return (0, 0)

    def create_cycling_workout(self, workout: Dict) -> Optional[str]:
        """
        Crée un workout cyclisme structuré via API Garmin

        Returns:
            workout_id si succès, None sinon
        """

        workout_name = f"{workout['code']} - {workout.get('description', 'HT')}"
        workout_date = workout.get('date', '')

        print(f"\n📤 Création workout: {workout_name}")
        print(f"📅 Date: {workout_date}")
        print(f"🚴 Intervalles: {len(workout.get('intervals', []))}")

        # Construire payload API Garmin
        workout_data = {
            "workoutName": workout_name,
            "description": workout.get('notes', '')[:500] if workout.get('notes') else "",
            "sportType": {
                "sportTypeId": 2,  # Cycling
                "sportTypeKey": "cycling"
            },
            "workoutSegments": []
        }

        # Ajouter segments (un segment = groupe d'intervalles)
        segment_order = 1
        step_order = 1

        for interval in workout.get('intervals', []):
            step = self._interval_to_api_step(interval, step_order)
            if step:
                # Créer segment contenant ce step
                segment = {
                    "segmentOrder": segment_order,
                    "sportType": {
                        "sportTypeId": 2,
                        "sportTypeKey": "cycling"
                    },
                    "workoutSteps": [step]
                }

                workout_data["workoutSegments"].append(segment)
                segment_order += 1
                step_order += 1

        try:
            # Appel API Garmin Connect
            endpoint = "/workout-service/workout"

            response = self.garmin_client.connectapi(
                endpoint,
                method="POST",
                data=json.dumps(workout_data),
                headers={"Content-Type": "application/json"}
            )

            if response and isinstance(response, dict):
                workout_id = response.get('workoutId')

                if workout_id:
                    print(f"✅ Workout créé (ID: {workout_id})")

                    # Programmer à la date
                    if workout_date:
                        self._schedule_workout(workout_id, workout_date)

                    return workout_id
                else:
                    print(f"⚠️  Réponse inattendue: {response}")
                    return None
            else:
                print(f"❌ Erreur création: {response}")
                return None

        except Exception as e:
            print(f"❌ Exception API: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _interval_to_api_step(self, interval: Dict, step_order: int) -> Optional[Dict]:
        """Convertit un intervalle JSON en step API Garmin"""

        duration_seconds = self.duration_to_seconds(interval.get('duration', '0:00'))
        phase = interval.get('phase', '').lower()

        # Type de step selon phase
        if 'échauffement' in phase or 'echauffement' in phase:
            step_type_id = 1  # WARMUP
            step_type_key = "warmup"
        elif 'récupération' in phase or 'recuperation' in phase:
            step_type_id = 3  # COOLDOWN
            step_type_key = "cooldown"
        else:
            step_type_id = 2  # ACTIVE (corps de séance)
            step_type_key = "active"

        # Parser puissance
        power_watts = interval.get('power_watts', '')
        if 'à' in power_watts:
            min_power, max_power = self.power_to_watts(power_watts)
        else:
            min_power, max_power = 0, 0

        step = {
            "type": "ExecutableStepDTO",
            "stepId": None,
            "stepOrder": step_order,
            "stepType": {
                "stepTypeId": step_type_id,
                "stepTypeKey": step_type_key
            },
            "endCondition": {
                "conditionTypeKey": "time",
                "conditionTypeId": 2
            },
            "endConditionValue": duration_seconds,
            "targetType": {
                "workoutTargetTypeId": 1,  # POWER
                "workoutTargetTypeKey": "power.zone"
            },
            "targetValueOne": min_power,  # Watts (min)
            "targetValueTwo": max_power    # Watts (max)
        }

        return step

    def _schedule_workout(self, workout_id: str, date_str: str):
        """Programme un workout à une date spécifique"""

        try:
            # API scheduling
            endpoint = f"/workout-service/schedule/{workout_id}"

            schedule_data = {
                "workoutId": int(workout_id),
                "date": date_str  # Format: "2026-02-07"
            }

            response = self.garmin_client.connectapi(
                endpoint,
                method="PUT",
                data=json.dumps(schedule_data),
                headers={"Content-Type": "application/json"}
            )

            print(f"📅 Workout programmé pour le {date_str}")

        except Exception as e:
            print(f"⚠️  Impossible de programmer: {e}")

    def upload_workout(self, workout: Dict) -> bool:
        """Upload un workout (point d'entrée principal)"""

        workout_type = workout.get('type', '')

        if workout_type == "Cyclisme":
            workout_id = self.create_cycling_workout(workout)
            return workout_id is not None

        elif workout_type == "Course à pied":
            print("⚠️  Upload CAP pas encore implémenté")
            return False

        elif workout_type == "Natation":
            print("⚠️  Upload Natation pas encore implémenté")
            return False

        else:
            print(f"❌ Type inconnu: {workout_type}")
            return False


def main():
    """Test standalone - upload d'un workout depuis JSON"""

    if len(sys.argv) < 2:
        print("Usage: python garmin_workout_api.py <workout_code> [json_path]")
        print("\nExemple:")
        print("  python garmin_workout_api.py C18")
        sys.exit(1)

    workout_code = sys.argv[1]
    json_path = sys.argv[2] if len(sys.argv) > 2 else "data/workouts_cache/S06_workouts_v6_near_final.json"

    # Charger JSON
    json_path_full = Path(__file__).parent.parent / json_path
    with open(json_path_full, 'r') as f:
        data = json.load(f)

    # Trouver workout
    workout = None
    for w in data.get('workouts', []):
        if w['code'] == workout_code:
            workout = w
            break

    if not workout:
        print(f"❌ Workout {workout_code} non trouvé")
        sys.exit(1)

    print(f"📋 Workout trouvé: {workout['code']} ({workout['type']})")
    print(f"📊 {len(workout.get('intervals', []))} intervalles")

    # Upload
    uploader = GarminWorkoutAPIUploader()

    if not uploader.login():
        print("\n💡 Authentifiez-vous d'abord:")
        print("   python src/garmin_auth.py cdelalain@hotmail.com LdpCoaching1 <CODE_MFA>")
        sys.exit(1)

    success = uploader.upload_workout(workout)

    if success:
        print(f"\n✅ {workout_code} uploadé avec succès sur Garmin Connect")
        print("🌐 Vérifiez sur: https://connect.garmin.com/modern/workouts")
        sys.exit(0)
    else:
        print(f"\n❌ Échec upload {workout_code}")
        sys.exit(1)


if __name__ == "__main__":
    main()
