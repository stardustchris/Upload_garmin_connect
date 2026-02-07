#!/usr/bin/env python3
"""
Convertisseur JSON → Garmin CyclingWorkout

Convertit les workouts parsés (JSON) en format CyclingWorkout pour upload
"""

from typing import Dict, List, Any
from datetime import datetime


def convert_to_garmin_cycling_workout(workout_json: Dict) -> Dict[str, Any]:
    """
    Convertit un workout JSON en format Garmin CyclingWorkout

    Args:
        workout_json: Structure JSON du workout parsé

    Returns:
        Dict compatible avec GarminConnect.upload_cycling_workout()
    """

    # Calculer durée totale estimée
    total_seconds = sum(
        parse_duration_to_seconds(interval['duration'])
        for interval in workout_json['intervals']
    )

    # Créer les workout steps
    workout_steps = []
    for idx, interval in enumerate(workout_json['intervals']):
        step = create_cycling_step(idx + 1, interval)
        workout_steps.append(step)

    # Structure Garmin Workout
    garmin_workout = {
        "workoutName": f"{workout_json['code']} - {workout_json.get('description', '')}",
        "estimatedDurationInSecs": total_seconds,
        "sportType": {
            "sportTypeId": 2,
            "sportTypeKey": "cycling",
            "displayOrder": 2
        },
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": {
                    "sportTypeId": 2,
                    "sportTypeKey": "cycling"
                },
                "workoutSteps": workout_steps
            }
        ]
    }

    return garmin_workout


def create_cycling_step(step_order: int, interval: Dict) -> Dict[str, Any]:
    """
    Crée un workout step Garmin à partir d'un intervalle JSON

    Args:
        step_order: Ordre du step (1-indexed)
        interval: Dict de l'intervalle avec duration, power_watts, phase, etc.

    Returns:
        Dict ExecutableStep compatible Garmin
    """

    # Parser durée
    duration_seconds = parse_duration_to_seconds(interval['duration'])

    # Déterminer step type basé sur phase
    phase = interval.get('phase', '').lower()
    if 'chauffement' in phase or 'warmup' in phase:
        step_type_id = 1
        step_type_key = "warmup"
    elif 'cup' in phase.lower() or 'cooldown' in phase:
        step_type_id = 5
        step_type_key = "cooldown"
    elif 'repos' in phase or 'récup' in phase or 'rest' in phase:
        step_type_id = 4
        step_type_key = "rest"
    else:  # Corps de séance, interval
        step_type_id = 3
        step_type_key = "interval"

    # Parser puissance (format "XXXàYYY")
    power_str = interval['power_watts']
    if 'à' in power_str:
        power_parts = power_str.split('à')
        target_power_low = int(power_parts[0])
        target_power_high = int(power_parts[1])
    else:
        target_power_low = int(power_str)
        target_power_high = int(power_str)

    # Créer ExecutableStep
    step = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": {
            "stepTypeId": step_type_id,
            "stepTypeKey": step_type_key
        },
        "endCondition": {
            "conditionTypeId": 2,  # TIME
            "conditionTypeKey": "time"
        },
        "endConditionValue": float(duration_seconds),
        "targetType": {
            "workoutTargetTypeId": 5,  # POWER
            "workoutTargetTypeKey": "power.zone"
        },
        "targetValueOne": float(target_power_low),  # Min power
        "targetValueTwo": float(target_power_high),  # Max power
    }

    # Ajouter note pour position si présente
    if 'position' in interval and interval['position']:
        step["description"] = interval['position']

    return step


def parse_duration_to_seconds(duration_str: str) -> int:
    """
    Convertit durée "MM:SS" en secondes

    Args:
        duration_str: Format "2:30" ou "5:00"

    Returns:
        Secondes (int)
    """
    if ':' in duration_str:
        parts = duration_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    else:
        # Si pas de ":", assumer que c'est en minutes
        return int(duration_str) * 60


if __name__ == '__main__':
    # Test avec C16
    import json

    with open('data/workouts_cache/S06_workouts_v6_near_final.json') as f:
        data = json.load(f)

    c16 = [w for w in data['workouts'] if w['code'] == 'C16'][0]

    garmin_workout = convert_to_garmin_cycling_workout(c16)

    print(json.dumps(garmin_workout, indent=2, ensure_ascii=False))
    print(f"\nTotal steps: {len(garmin_workout['workoutSegments'][0]['workoutSteps'])}")
    print(f"Estimated duration: {garmin_workout['estimatedDurationInSecs'] // 60} minutes")
