#!/usr/bin/env python3
"""
Convertisseur JSON → Garmin CyclingWorkout

Convertit les workouts parsés (JSON) en format CyclingWorkout pour upload
"""

from typing import Dict, List, Any
from datetime import datetime


def detect_repeat_groups(intervals: List[Dict]) -> List[Dict]:
    """
    Analyse les intervalles et groupe les répétitions consécutives

    Args:
        intervals: Liste des intervalles parsés

    Returns:
        Liste de groupes où chaque groupe est soit:
        - {"type": "single", "interval": {...}}
        - {"type": "repeat", "iterations": N, "steps": [...]}
    """
    groups = []
    i = 0

    while i < len(intervals):
        interval = intervals[i]

        # Vérifier si cet intervalle fait partie d'un groupe de répétition
        if "repetition_total" in interval and "repetition_iteration" in interval:
            # Début d'un groupe de répétition
            repeat_total = interval["repetition_total"]

            # Collecter tous les intervalles de ce groupe (toutes les itérations)
            group_intervals = []

            # Tant qu'on trouve des intervalles avec repetition_total et même total
            while (i < len(intervals) and
                   intervals[i].get("repetition_total") == repeat_total and
                   intervals[i].get("repetition_iteration") is not None):
                group_intervals.append(intervals[i])
                i += 1

            # Extraire le pattern (première itération seulement)
            steps_per_iteration = len(group_intervals) // repeat_total
            pattern_steps = group_intervals[:steps_per_iteration]

            groups.append({
                "type": "repeat",
                "iterations": repeat_total,
                "steps": pattern_steps
            })
        else:
            # Intervalle simple
            groups.append({
                "type": "single",
                "interval": interval
            })
            i += 1

    return groups


def create_repeat_group_step(
    step_order: int,
    child_step_id: int,
    iterations: int,
    nested_steps: List[Dict]
) -> Dict[str, Any]:
    """
    Crée un RepeatGroupDTO pour Garmin workout

    Args:
        step_order: Ordre du step dans le workout
        child_step_id: ID du child step pour les steps imbriqués
        iterations: Nombre de répétitions (numberOfIterations)
        nested_steps: Liste des ExecutableStepDTOs à répéter

    Returns:
        Structure RepeatGroupDTO
    """
    return {
        "type": "RepeatGroupDTO",
        "stepOrder": step_order,
        "stepType": {
            "stepTypeId": 6,  # REPEAT type
            "stepTypeKey": "repeat"
        },
        "childStepId": child_step_id,
        "numberOfIterations": iterations,
        "smartRepeat": False,
        "workoutSteps": nested_steps
    }


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

    # Détecter les groupes de répétition
    repeat_groups = detect_repeat_groups(workout_json['intervals'])

    # Créer les workout steps avec support RepeatGroups
    workout_steps = []
    step_order = 0
    child_step_id = 0

    for group in repeat_groups:
        if group["type"] == "single":
            # Step simple
            step_order += 1
            step = create_cycling_step(step_order, group["interval"])
            workout_steps.append(step)

        elif group["type"] == "repeat":
            # Groupe de répétition
            child_step_id += 1

            # Créer les steps imbriqués
            nested_steps = []
            nested_step_order = step_order

            for interval in group["steps"]:
                nested_step_order += 1
                nested_step = create_cycling_step(nested_step_order, interval)
                nested_step["childStepId"] = child_step_id
                nested_steps.append(nested_step)

            # Mettre à jour step_order
            step_order = nested_step_order

            # Créer le RepeatGroupDTO
            repeat_step = create_repeat_group_step(
                step_order=step_order,
                child_step_id=child_step_id,
                iterations=group["iterations"],
                nested_steps=nested_steps
            )
            workout_steps.append(repeat_step)

    # Structure Garmin Workout
    garmin_workout = {
        "workoutName": workout_json['code'],  # Just the code (e.g., "C16", not "C16 - sur HT")
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
            "workoutTargetTypeId": 2,  # POWER (2, not 5 which is SPEED!)
            "workoutTargetTypeKey": "power.zone"
        },
        "targetValueOne": float(target_power_low),  # Min power
        "targetValueTwo": float(target_power_high),  # Max power
    }

    # Ajouter description (position + cadence)
    description_parts = []

    if 'position' in interval and interval['position']:
        description_parts.append(interval['position'])

    if 'cadence_rpm' in interval and interval['cadence_rpm'] and interval['cadence_rpm'] != 'libre':
        description_parts.append(f"Cadence: {interval['cadence_rpm']} rpm")

    if description_parts:
        step["description"] = " - ".join(description_parts)

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


def convert_to_garmin_running_workout(workout_json: Dict) -> Dict[str, Any]:
    """
    Convertit un workout JSON de course à pied en format Garmin Running Workout

    Args:
        workout_json: Structure JSON du workout parsé

    Returns:
        Dict compatible avec GarminConnect.upload_workout()
    """

    # Calculer durée totale estimée
    total_seconds = sum(
        parse_duration_to_seconds(interval['duration'])
        for interval in workout_json['intervals']
    )

    # Détecter les groupes de répétition
    repeat_groups = detect_repeat_groups(workout_json['intervals'])

    # Créer les workout steps avec support RepeatGroups
    workout_steps = []
    step_order = 0
    child_step_id = 0

    for group in repeat_groups:
        if group["type"] == "single":
            # Step simple
            step_order += 1
            step = create_running_step(step_order, group["interval"])
            workout_steps.append(step)

        elif group["type"] == "repeat":
            # Groupe de répétition
            child_step_id += 1

            # Créer les steps imbriqués
            nested_steps = []
            nested_step_order = step_order

            for interval in group["steps"]:
                nested_step_order += 1
                nested_step = create_running_step(nested_step_order, interval)
                nested_step["childStepId"] = child_step_id
                nested_steps.append(nested_step)

            # Mettre à jour step_order
            step_order = nested_step_order

            # Créer le RepeatGroupDTO
            repeat_step = create_repeat_group_step(
                step_order=step_order,
                child_step_id=child_step_id,
                iterations=group["iterations"],
                nested_steps=nested_steps
            )
            workout_steps.append(repeat_step)

    # Structure Garmin Workout pour course à pied
    garmin_workout = {
        "workoutName": workout_json['code'],
        "estimatedDurationInSecs": total_seconds,
        "sportType": {
            "sportTypeId": 1,  # Running
            "sportTypeKey": "running",
            "displayOrder": 1
        },
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": {
                    "sportTypeId": 1,
                    "sportTypeKey": "running"
                },
                "workoutSteps": workout_steps
            }
        ]
    }

    return garmin_workout


def create_running_step(step_order: int, interval: Dict) -> Dict[str, Any]:
    """
    Crée un workout step Garmin pour course à pied à partir d'un intervalle JSON

    Note: Pour la CAP, on n'envoie que la durée, pas l'allure (pace)

    Args:
        step_order: Ordre du step (1-indexed)
        interval: Dict de l'intervalle avec duration, phase, etc.

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

    # Créer ExecutableStep (sans target pace, juste durée)
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
            "workoutTargetTypeId": 1,  # NO_TARGET
            "workoutTargetTypeKey": "no.target"
        }
    }

    # Ajouter la description de la phase si présente
    description_parts = []
    if interval.get('pace_description'):
        description_parts.append(interval['pace_description'])
    if interval.get('pace_min_per_km'):
        description_parts.append(f"Allure: {interval['pace_min_per_km']}")

    if description_parts:
        step["description"] = " - ".join(description_parts)

    return step


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
