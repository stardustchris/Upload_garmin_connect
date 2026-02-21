#!/usr/bin/env python3
"""
Parser PDF visuel - Extraction de workouts depuis screenshots

Cette approche utilise l'analyse visuelle d'images pour extraire les tableaux
de workouts, évitant les problèmes de parsing de texte mal structuré.

Usage:
    1. Faire screenshot de la page PDF du workout
    2. Appeler parse_workout_from_image(image_path, workout_code)
    3. Le parser utilise vision AI pour extraire la structure du tableau
"""

import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import re


def encode_image(image_path: str) -> str:
    """Encode une image en base64 pour l'API"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def parse_workout_from_image(
    image_path: str,
    workout_code: str,
    workout_type: str = "cycling"
) -> Dict[str, Any]:
    """
    Parse un workout depuis un screenshot de PDF

    Args:
        image_path: Chemin vers l'image du workout
        workout_code: Code du workout (ex: "C19", "CAP17")
        workout_type: Type de workout ("cycling", "running", "swimming")

    Returns:
        Dict avec la structure du workout parsée

    Note:
        Cette fonction nécessite une intégration avec Claude API
        pour l'analyse visuelle. Pour l'instant, elle retourne
        une structure vide à compléter manuellement.
    """

    # TODO: Intégrer avec Claude API pour analyse visuelle
    # Pour l'instant, retourner une structure à remplir manuellement

    workout = {
        "code": workout_code,
        "type": workout_type.capitalize(),
        "date": None,  # À extraire de l'image
        "duration_total": None,  # À extraire de l'image
        "description": None,  # À extraire de l'image
        "intervals": [],  # À extraire de l'image
        "notes": None,  # À extraire de l'image
        "source": "visual_extraction",
        "image_path": str(image_path)
    }

    print(f"""
    ⚠️  ANALYSE VISUELLE NON IMPLÉMENTÉE

    Pour parser {workout_code} depuis l'image:
    1. Ouvrir l'image: {image_path}
    2. Extraire manuellement les données du tableau
    3. Remplir la structure dans data/workouts_cache/

    Ou utiliser Claude Desktop avec vision pour analyser l'image.
    """)

    return workout


def create_workout_template(workout_code: str, workout_type: str = "cycling") -> Dict:
    """
    Crée un template vide de workout à remplir manuellement

    Args:
        workout_code: Code du workout
        workout_type: Type de workout

    Returns:
        Template de workout
    """

    if workout_type == "cycling":
        interval_template = {
            "phase": "Corps de séance",  # ou "Echauffement", "Récupération"
            "duration": "00:00",  # Format MM:SS
            "cadence_rpm": "90à95",  # ou "libre"
            "power_watts": "220à230",  # Puissance cible
            "position": "Position haute",  # ou "Position aéro.", etc.
            # Pour répétitions:
            # "repetition_iteration": 1,
            # "repetition_total": 3
        }
    elif workout_type == "running":
        interval_template = {
            "phase": "Corps de séance",
            "duration": "00:00",
            "pace_min_per_km": "4:30à4:35",  # ou None
            "pace_description": "Allure modérée"  # ou None
        }
    else:
        interval_template = {
            "phase": "Corps de séance",
            "duration": "00:00",
            "distance_m": 100
        }

    template = {
        "code": workout_code,
        "type": workout_type.capitalize(),
        "date": "2026-02-XX",
        "duration_total": "1h00",
        "description": "Description de la séance",
        "intervals": [
            interval_template
        ],
        "notes": "Consignes et notes",
        "indoor": True if workout_type == "cycling" else None
    }

    return template


def fix_c19_manually() -> Dict:
    """
    Fix manuel pour C19 qui est mal parsé

    Returns:
        Structure complète de C19
    """

    print("""
    ⚠️  C19 MAL PARSÉ - CORRECTION MANUELLE NÉCESSAIRE

    Le parser actuel ne détecte que 6 intervalles (échauffement + récup)
    et manque complètement le corps de séance.

    Actions requises:
    1. Faire un screenshot de la page C19 du PDF
    2. Extraire manuellement les données du tableau
    3. Compléter la structure ci-dessous
    """)

    c19 = {
        "code": "C19",
        "type": "Cyclisme",
        "date": "2026-02-08",  # À vérifier
        "indoor": True,
        "duration_total": "1h00",
        "description": "sur HT",
        "intervals": [
            # ÉCHAUFFEMENT HT (4 blocs)
            {"phase": "Echauffement", "duration": "2:30", "cadence_rpm": "libre", "power_watts": "96à106"},
            {"phase": "Echauffement", "duration": "2:30", "cadence_rpm": "libre", "power_watts": "130à136"},
            {"phase": "Echauffement", "duration": "5:00", "cadence_rpm": "libre", "power_watts": "156à166"},
            {"phase": "Echauffement", "duration": "5:00", "cadence_rpm": "libre", "power_watts": "180à190"},

            # CORPS DE SÉANCE - À COMPLÉTER AVEC LES VRAIES DONNÉES DU PDF
            # TODO: Extraire depuis le PDF
            # Ex: 3 x (interval_1, interval_2, ...)

            # RÉCUPÉRATION HT (2 blocs)
            {"phase": "Récupération", "duration": "2:00", "cadence_rpm": "libre", "power_watts": "175à180"},
            {"phase": "Récupération", "duration": "2:00", "cadence_rpm": "libre", "power_watts": "175à180"},
        ],
        "notes": "Adapter le développement en fonction des zones cadences et de puissances imposées ; consommer 850 mL d'eau au cours de la séance."
    }

    return c19


if __name__ == '__main__':
    # Exemple d'utilisation
    print("📊 Visual PDF Parser\n")

    # Créer un template pour C19
    template = create_workout_template("C19", "cycling")
    print("Template C19:")
    print(json.dumps(template, indent=2, ensure_ascii=False))

    print("\n" + "="*60)

    # Montrer le problème avec C19
    c19_partial = fix_c19_manually()
