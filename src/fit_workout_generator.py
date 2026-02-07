#!/usr/bin/env python3
"""
Générateur de fichiers FIT pour workouts Garmin

Convertit les workouts JSON en fichiers FIT pour upload vers Garmin Connect
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fitparse import FitFile
import struct


class FITWorkoutGenerator:
    """Générateur de fichiers FIT pour workouts cyclisme"""

    # Constants FIT pour workouts
    SPORT_CYCLING = 2
    SUB_SPORT_INDOOR_CYCLING = 6

    INTENSITY_ACTIVE = 0
    INTENSITY_REST = 1
    INTENSITY_WARMUP = 0
    INTENSITY_COOLDOWN = 1

    DURATION_TYPE_TIME = 0  # Secondes
    TARGET_TYPE_POWER = 1

    def __init__(self):
        self.messages = []

    def generate_cycling_workout(self, workout: Dict) -> bytes:
        """
        Génère un fichier FIT pour un workout cyclisme

        Args:
            workout: Dict avec structure JSON du workout

        Returns:
            bytes du fichier FIT
        """
        # File header
        fit_data = bytearray()

        # FIT file header (14 bytes)
        header_size = 14
        protocol_version = 0x20  # 2.0
        profile_version = 2132  # 21.32
        data_size = 0  # Will be calculated
        data_type = b'.FIT'

        # Créer workout file message
        workout_msg = self._create_workout_message(workout)

        # Créer workout step messages pour chaque intervalle
        step_messages = []
        for idx, interval in enumerate(workout['intervals']):
            step_msg = self._create_workout_step(idx, interval)
            step_messages.append(step_msg)

        # TODO: Encoder en format FIT binaire
        # Pour l'instant, retourner structure JSON pour debugging
        return {
            'workout': workout_msg,
            'steps': step_messages
        }

    def _create_workout_message(self, workout: Dict) -> Dict:
        """Crée le message workout principal"""
        return {
            'sport': self.SPORT_CYCLING,
            'sub_sport': self.SUB_SPORT_INDOOR_CYCLING if workout.get('indoor') else None,
            'capabilities': 0x00000020,  # Valid for scheduling
            'num_valid_steps': len(workout['intervals']),
            'wkt_name': workout['code']
        }

    def _create_workout_step(self, step_index: int, interval: Dict) -> Dict:
        """Crée un workout step pour un intervalle"""

        # Parser durée (format "MM:SS")
        duration_str = interval['duration']
        if ':' in duration_str:
            parts = duration_str.split(':')
            duration_seconds = int(parts[0]) * 60 + int(parts[1])
        else:
            duration_seconds = int(duration_str) * 60

        # Parser puissance (format "XXXàYYY")
        power_str = interval['power_watts']
        if 'à' in power_str:
            power_min, power_max = power_str.split('à')
            target_power_low = int(power_min)
            target_power_high = int(power_max)
        else:
            target_power_low = int(power_str)
            target_power_high = int(power_str)

        # Déterminer intensité
        phase = interval.get('phase', '')
        if 'chauffement' in phase.lower():
            intensity = self.INTENSITY_WARMUP
        elif 'cup' in phase.lower():
            intensity = self.INTENSITY_COOLDOWN
        elif 'repos' in phase.lower() or 'récup' in phase.lower():
            intensity = self.INTENSITY_REST
        else:
            intensity = self.INTENSITY_ACTIVE

        return {
            'message_index': step_index,
            'wkt_step_name': f"{interval.get('phase', 'Step')} {step_index+1}",
            'duration_type': self.DURATION_TYPE_TIME,
            'duration_value': duration_seconds,
            'target_type': self.TARGET_TYPE_POWER,
            'target_value': 0,  # Custom zone
            'custom_target_value_low': target_power_low,
            'custom_target_value_high': target_power_high,
            'intensity': intensity
        }


def create_fit_from_json(workout_json: Dict, output_path: str) -> str:
    """
    Crée un fichier FIT à partir du JSON workout

    Args:
        workout_json: Structure JSON du workout
        output_path: Chemin du fichier FIT à créer

    Returns:
        Chemin du fichier créé
    """
    generator = FITWorkoutGenerator()

    # Pour l'instant, on ne peut pas générer de vrais fichiers FIT
    # car fitparse est en lecture seule
    # Il faudrait utiliser une librairie d'écriture FIT

    print("⚠️  Génération FIT non disponible")
    print("💡 Utiliser garmin-workouts (YAML) ou API Garmin directe")

    return None


if __name__ == '__main__':
    # Test avec C16
    import json

    with open('data/workouts_cache/S06_workouts_v6_near_final.json') as f:
        data = json.load(f)

    c16 = [w for w in data['workouts'] if w['code'] == 'C16'][0]

    generator = FITWorkoutGenerator()
    result = generator.generate_cycling_workout(c16)

    print(json.dumps(result, indent=2))
