#!/usr/bin/env python3
"""
Module d'upload de workouts vers Garmin Connect
Convertit les JSON parsés en fichiers YAML compatibles avec garmin-workouts
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List
import subprocess
import tempfile


class GarminWorkoutUploader:
    """Upload workouts vers Garmin Connect via garmin-workouts"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.include_dir = Path(__file__).parent.parent / "data" / "yaml_includes"
        self.include_dir.mkdir(parents=True, exist_ok=True)

        # Créer les fichiers include pour HT warmup/cooldown
        self._create_ht_includes()

    def _create_ht_includes(self):
        """Crée les fichiers YAML include pour échauffement et récupération HT standard"""

        # Échauffement HT standard (4 blocs)
        ht_warmup = {
            "steps": [
                {"warmup": {"duration": "2:30", "target": {"power": "96-106W"}}},
                {"warmup": {"duration": "2:30", "target": {"power": "130-136W"}}},
                {"warmup": {"duration": "5:00", "target": {"power": "156-166W"}}},
                {"warmup": {"duration": "5:00", "target": {"power": "180-190W"}}}
            ]
        }

        warmup_path = self.include_dir / "warmup_ht.yaml"
        with open(warmup_path, 'w') as f:
            yaml.dump(ht_warmup, f, default_flow_style=False, allow_unicode=True)

        # Récupération HT standard (2 blocs @ 175-180W)
        ht_cooldown = {
            "steps": [
                {"cooldown": {"duration": "2:00", "target": {"power": "175-180W"}}},
                {"cooldown": {"duration": "2:00", "target": {"power": "175-180W"}}}
            ]
        }

        cooldown_path = self.include_dir / "cooldown_ht.yaml"
        with open(cooldown_path, 'w') as f:
            yaml.dump(ht_cooldown, f, default_flow_style=False, allow_unicode=True)

    def convert_cycling_to_yaml(self, workout: Dict) -> Dict:
        """
        Convertit un workout cyclisme JSON en format YAML garmin-workouts

        Args:
            workout: Dict avec structure {code, date, intervals, indoor, ...}

        Returns:
            Dict compatible YAML garmin-workouts
        """
        yaml_workout = {
            "name": f"{workout['code']} - {workout.get('description', 'Cyclisme')}",
            "sport": "cycling",
            "steps": []
        }

        # Grouper les intervalles par phase et gestion répétitions
        intervals = workout.get("intervals", [])
        i = 0

        while i < len(intervals):
            interval = intervals[i]
            phase = interval["phase"]

            # Échauffement : si HT, utiliser include, sinon générer steps
            if phase == "Echauffement" or phase == "Échauffement":
                if workout.get("indoor", False):
                    # Utiliser include HT warmup
                    yaml_workout["steps"].append({
                        "include": str(self.include_dir / "warmup_ht.yaml")
                    })
                    # Sauter les blocs d'échauffement
                    while i < len(intervals) and intervals[i]["phase"] in ["Echauffement", "Échauffement"]:
                        i += 1
                    continue
                else:
                    # Warmup normal
                    yaml_workout["steps"].append(
                        self._interval_to_yaml_step(interval, "warmup")
                    )

            # Corps de séance
            elif phase == "Corps de séance":
                # Détecter si répétition
                if "repetition_iteration" in interval and interval["repetition_iteration"] == 1:
                    # Début d'une répétition, collecter tous les intervalles de cette répétition
                    repeat_count = interval["repetition_total"]
                    repeat_steps = []

                    # Collecter les intervalles d'une itération
                    j = i
                    while j < len(intervals) and intervals[j].get("repetition_iteration") == 1:
                        repeat_steps.append(
                            self._interval_to_yaml_step(intervals[j], "interval")
                        )
                        j += 1

                    # Ajouter le bloc de répétition
                    yaml_workout["steps"].append({
                        "repeat": repeat_count,
                        "steps": repeat_steps
                    })

                    # Sauter tous les intervalles de répétition
                    while i < len(intervals) and "repetition_iteration" in intervals[i]:
                        i += 1
                    continue
                else:
                    # Intervalle simple
                    yaml_workout["steps"].append(
                        self._interval_to_yaml_step(interval, "interval")
                    )

            # Récupération
            elif phase == "Récupération":
                if workout.get("indoor", False):
                    # Utiliser include HT cooldown
                    yaml_workout["steps"].append({
                        "include": str(self.include_dir / "cooldown_ht.yaml")
                    })
                    # Sauter les blocs de récupération
                    while i < len(intervals) and intervals[i]["phase"] == "Récupération":
                        i += 1
                    continue
                else:
                    yaml_workout["steps"].append(
                        self._interval_to_yaml_step(interval, "cooldown")
                    )

            i += 1

        return yaml_workout

    def _interval_to_yaml_step(self, interval: Dict, step_type: str) -> Dict:
        """
        Convertit un intervalle JSON en step YAML

        Args:
            interval: Dict avec {duration, power_watts, cadence_rpm, ...}
            step_type: "warmup", "interval", "cooldown", "rest"

        Returns:
            Dict step YAML
        """
        # Convertir durée "mm:ss" en format garmin-workouts
        duration = interval.get("duration", "0:00")

        # Extraire puissance (format "235à245" → "235-245W")
        power = interval.get("power_watts", "")
        if power and "à" in power:
            power_clean = power.replace("à", "-") + "W"
        else:
            power_clean = power

        # NE PAS inclure la cadence (user requirement)
        step = {
            step_type: {
                "duration": duration,
                "target": {
                    "power": power_clean
                }
            }
        }

        return step

    def convert_running_to_yaml(self, workout: Dict) -> Dict:
        """
        Convertit un workout CAP JSON en format YAML garmin-workouts

        Args:
            workout: Dict avec structure {code, date, intervals, workout_type, ...}

        Returns:
            Dict compatible YAML garmin-workouts
        """

        # Si FARTLEK, créer workout libre
        if workout.get("workout_type") == "FARTLEK":
            return {
                "name": f"{workout['code']} - FARTLEK NATUREL",
                "sport": "running",
                "steps": [
                    {
                        "interval": {
                            "duration": workout.get("duration_total", "45:00"),
                            "target": "open"  # Libre, aux sensations
                        }
                    }
                ]
            }

        # Workout structuré
        yaml_workout = {
            "name": f"{workout['code']} - Course à pied",
            "sport": "running",
            "steps": []
        }

        for interval in workout.get("intervals", []):
            phase = interval["phase"]
            duration = interval.get("duration", "0:00")

            # Warmup
            if phase == "Echauffement" or phase == "Échauffement":
                if "pace_description" in interval:
                    # Allure libre
                    yaml_workout["steps"].append({
                        "warmup": {
                            "duration": duration,
                            "target": "open"
                        }
                    })
                else:
                    # Allure spécifique
                    pace = interval.get("pace_min_per_km", "")
                    pace_clean = pace.replace("à", "-") + " min/km" if pace else "open"

                    yaml_workout["steps"].append({
                        "warmup": {
                            "duration": duration,
                            "target": {"pace": pace_clean}
                        }
                    })

            # Corps de séance
            elif phase == "Corps de séance":
                pace = interval.get("pace_min_per_km", "")
                pace_clean = pace.replace("à", "-") + " min/km" if pace else "open"

                yaml_workout["steps"].append({
                    "interval": {
                        "duration": duration,
                        "target": {"pace": pace_clean}
                    }
                })

            # Récupération
            elif phase == "Récupération":
                if "pace_description" in interval:
                    yaml_workout["steps"].append({
                        "cooldown": {
                            "duration": duration,
                            "target": "open"
                        }
                    })
                else:
                    pace = interval.get("pace_min_per_km", "")
                    pace_clean = pace.replace("à", "-") + " min/km" if pace else "open"

                    yaml_workout["steps"].append({
                        "cooldown": {
                            "duration": duration,
                            "target": {"pace": pace_clean}
                        }
                    })

        return yaml_workout

    def upload_workout(self, yaml_data: Dict, workout_date: str = None) -> bool:
        """
        Upload un workout vers Garmin Connect via garmin-workouts CLI

        Args:
            yaml_data: Dict workout en format YAML
            workout_date: Date optionnelle pour programmer le workout (format YYYY-MM-DD)

        Returns:
            True si succès, False sinon
        """
        # Créer fichier YAML temporaire
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
            yaml_path = f.name

        try:
            # Commande garmin-workouts import
            cmd = ["garmin-workouts", "import", yaml_path]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                print(f"✅ Workout uploadé avec succès : {yaml_data['name']}")

                # TODO: Programmer à la date spécifique si fournie
                # Nécessite API Garmin Connect (pas dans garmin-workouts CLI)

                return True
            else:
                print(f"❌ Erreur upload workout : {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Timeout lors de l'upload")
            return False
        except FileNotFoundError:
            print("❌ garmin-workouts n'est pas installé. Installer avec: pip install git+https://github.com/mkuthan/garmin-workouts.git")
            return False
        finally:
            # Nettoyer fichier temporaire
            Path(yaml_path).unlink(missing_ok=True)

    def upload_from_json_file(self, json_path: str) -> Dict[str, bool]:
        """
        Upload tous les workouts depuis un fichier JSON parsé

        Args:
            json_path: Chemin vers le JSON de workouts parsés

        Returns:
            Dict {workout_code: success_bool}
        """
        with open(json_path, 'r') as f:
            data = json.load(f)

        results = {}

        for workout in data.get("workouts", []):
            code = workout["code"]
            workout_type = workout["type"]
            workout_date = workout.get("date")

            print(f"\n📤 Upload {code} ({workout_type}) prévu pour {workout_date}...")

            try:
                # Convertir en YAML selon le type
                if workout_type == "Cyclisme":
                    yaml_data = self.convert_cycling_to_yaml(workout)
                elif workout_type == "Course à pied":
                    yaml_data = self.convert_running_to_yaml(workout)
                elif workout_type == "Natation":
                    print(f"⚠️  Natation non supportée pour l'instant, skip {code}")
                    results[code] = False
                    continue
                else:
                    print(f"⚠️  Type inconnu: {workout_type}, skip {code}")
                    results[code] = False
                    continue

                # Upload vers Garmin
                success = self.upload_workout(yaml_data, workout_date)
                results[code] = success

            except Exception as e:
                print(f"❌ Erreur lors de l'upload de {code}: {e}")
                results[code] = False

        return results


def main():
    """Test standalone"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python garmin_uploader.py <path_to_workouts_json>")
        sys.exit(1)

    json_path = sys.argv[1]

    uploader = GarminWorkoutUploader()
    results = uploader.upload_from_json_file(json_path)

    print("\n" + "="*50)
    print("RÉSUMÉ UPLOAD")
    print("="*50)

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for code, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {code}")

    print(f"\nSuccès: {success_count}/{total_count}")


if __name__ == "__main__":
    main()
