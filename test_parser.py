#!/usr/bin/env python3
"""
Script de test du parser PDF
Affiche toutes les données extraites pour vérification manuelle
"""

import json
import sys
from pathlib import Path

# Ajouter le dossier src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pdf_parser import TriathlonPDFParser


def print_section(title: str, char: str = "="):
    """Affiche un titre de section"""
    print(f"\n{char * 70}")
    print(f"{title}")
    print(f"{char * 70}\n")


def test_parse_pdf(pdf_path: str):
    """Test complet du parser avec affichage détaillé"""

    print_section("🧪 TEST DU PARSER PDF D'ENTRAÎNEMENTS", "=")
    print(f"📄 Fichier: {Path(pdf_path).name}\n")

    with TriathlonPDFParser(pdf_path) as parser:
        result = parser.parse()

        # Afficher les infos générales
        print_section("📅 INFORMATIONS DE LA SEMAINE")
        print(f"Semaine       : {result['week']}")
        print(f"Période       : {result['period']}")
        print(f"Date début    : {result['start_date']}")
        print(f"Date fin      : {result['end_date']}")
        print(f"Total séances : {len(result['workouts'])}")

        # Résumé par discipline
        print_section("📊 RÉSUMÉ PAR DISCIPLINE")
        disciplines = {}
        for workout in result['workouts']:
            wtype = workout['type']
            disciplines[wtype] = disciplines.get(wtype, 0) + 1

        for discipline, count in sorted(disciplines.items()):
            print(f"{discipline:20} : {count} séance(s)")

        # Détails de chaque workout
        print_section("🏋️  DÉTAILS DES ENTRAÎNEMENTS")

        for i, workout in enumerate(result['workouts'], 1):
            print(f"\n{'─' * 70}")
            print(f"SÉANCE {i}/{len(result['workouts'])} : {workout['code']} - {workout['type']}")
            print(f"{'─' * 70}")

            print(f"📅 Date        : {workout['date']}")
            print(f"⏱️  Durée totale: {workout['duration_total']}")

            if workout.get('description'):
                print(f"📝 Description : {workout['description']}")

            # Détails selon le type
            if workout['type'] == 'Cyclisme':
                test_cycling_workout(workout)
            elif workout['type'] == 'Course à pied':
                test_running_workout(workout)
            elif workout['type'] == 'Natation':
                test_swimming_workout(workout)

            if workout.get('notes'):
                print(f"\n💡 CONSIGNES/NOTES:")
                print(f"   {workout['notes'][:200]}...")


def test_cycling_workout(workout: dict):
    """Affiche les détails d'une séance de cyclisme"""
    print(f"\n🚴 INTERVALLES CYCLISME ({len(workout.get('intervals', []))}):")

    if not workout.get('intervals'):
        print("   ⚠️  Aucun intervalle extrait")
        return

    for j, interval in enumerate(workout['intervals'], 1):
        position = f" [{interval['position']}]" if interval.get('position') else ""
        print(f"\n   {j}. {interval['phase']}{position}")
        print(f"      Durée    : {interval['duration']}")
        print(f"      Cadence  : {interval['cadence_rpm']} rpm")
        print(f"      Puissance: {interval['power_watts']} W")


def test_running_workout(workout: dict):
    """Affiche les détails d'une séance de CAP"""
    print(f"\n🏃 INTERVALLES CAP ({len(workout.get('intervals', []))}):")

    if not workout.get('intervals'):
        print("   ⚠️  Aucun intervalle extrait")
        return

    for j, interval in enumerate(workout['intervals'], 1):
        print(f"\n   {j}. {interval['phase']}")
        print(f"      Durée: {interval['duration']}")

        if interval.get('pace_min_per_km'):
            print(f"      Allure: {interval['pace_min_per_km']} min/km")
        elif interval.get('pace_description'):
            print(f"      Allure: {interval['pace_description']}")


def test_swimming_workout(workout: dict):
    """Affiche les détails d'une séance de natation"""
    print(f"\n🏊 SÉRIES NATATION ({len(workout.get('series', []))}):")

    if not workout.get('series'):
        print("   ⚠️  Aucune série extraite")
        return

    for j, serie in enumerate(workout['series'], 1):
        technique_marker = " [TECH]" if serie['technique'] else ""
        print(f"   {j}. {serie['description']}{technique_marker}")

    # Afficher les distances par nage
    if workout.get('distances'):
        print(f"\n🎯 DISTANCES PAR TYPE DE NAGE:")
        total_distance = sum(workout['distances'].values())

        if total_distance > 0:
            for stroke, distance in sorted(workout['distances'].items()):
                if distance > 0:
                    percentage = (distance / total_distance) * 100
                    print(f"   {stroke:15} : {distance:4} m ({percentage:5.1f}%)")
            print(f"   {'─' * 35}")
            print(f"   {'TOTAL':15} : {total_distance:4} m")
        else:
            print("   ⚠️  Aucune distance extraite")


def test_json_export(pdf_path: str):
    """Test de l'export JSON"""
    print_section("💾 TEST EXPORT JSON")

    output_path = Path(__file__).parent / "data/workouts_cache/test_S06_workouts.json"

    with TriathlonPDFParser(pdf_path) as parser:
        result_path = parser.save_json(str(output_path))

    print(f"✅ JSON sauvegardé: {result_path}")

    # Vérifier que le JSON est valide
    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"✅ JSON valide: {len(data['workouts'])} workouts")

    return result_path


def test_issues(result: dict):
    """Identifie les problèmes potentiels dans le parsing"""
    print_section("⚠️  VÉRIFICATION DES PROBLÈMES POTENTIELS", "-")

    issues = []

    for workout in result['workouts']:
        code = workout['code']

        # Vérifier date
        if not workout.get('date'):
            issues.append(f"{code}: Date non extraite")

        # Vérifier durée
        if not workout.get('duration_total'):
            issues.append(f"{code}: Durée non extraite")

        # Vérifier contenu selon type
        if workout['type'] == 'Cyclisme':
            if not workout.get('intervals'):
                issues.append(f"{code}: Aucun intervalle cyclisme")
            else:
                for interval in workout['intervals']:
                    if 'à' not in interval.get('cadence_rpm', ''):
                        issues.append(f"{code}: Cadence mal formatée: {interval.get('cadence_rpm')}")
                    if 'à' not in interval.get('power_watts', ''):
                        issues.append(f"{code}: Puissance mal formatée: {interval.get('power_watts')}")

        elif workout['type'] == 'Course à pied':
            if not workout.get('intervals'):
                issues.append(f"{code}: Aucun intervalle CAP")

        elif workout['type'] == 'Natation':
            if not workout.get('series'):
                issues.append(f"{code}: Aucune série natation")

    if issues:
        print("⚠️  Problèmes détectés:\n")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print("✅ Aucun problème détecté !")


def main():
    """Exécution du test complet"""
    pdf_path = "/Users/aptsdae/Documents/Triathlon/Séances S06 (02_02 au 08_02)_Delalain C_2026.pdf"

    # Vérifier que le fichier existe
    if not Path(pdf_path).exists():
        print(f"❌ Fichier non trouvé: {pdf_path}")
        return 1

    # Test principal
    test_parse_pdf(pdf_path)

    # Test export JSON
    test_json_export(pdf_path)

    # Vérification des problèmes
    with TriathlonPDFParser(pdf_path) as parser:
        result = parser.parse()
        test_issues(result)

    print_section("✅ TESTS TERMINÉS")
    print("Vérifiez les détails ci-dessus pour valider le parsing.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
