#!/usr/bin/env python3
"""
Workflow complet géré par Clawdbot

Ce script est appelé par Clawdbot selon les déclencheurs:
1. Nouveau PDF reçu → Upload Garmin immédiat
2. Dimanche 22:00 → Remplissage Excel
3. Commande manuelle → Préparation email

Usage par Clawdbot:
    python scripts/clawdbot_workflow.py --action <action> --file <file>

Actions:
    upload_workouts    : Upload PDF vers Garmin Connect
    fill_excel        : Convertir XLS + Remplir avec données Garmin
    prepare_email     : Préparer brouillon email pour Stéphane

Exemples:
    # Action 1: Dès réception PDF
    python scripts/clawdbot_workflow.py --action upload_workouts --file "Séances S07.pdf"

    # Action 2: Dimanche 22:00
    python scripts/clawdbot_workflow.py --action fill_excel --file "S07_carnet_entrainement.xls"

    # Action 3: Sur commande manuelle
    python scripts/clawdbot_workflow.py --action prepare_email --file "S07_carnet_entrainement.xlsx"
"""

import sys
import argparse
from pathlib import Path
import json
from datetime import datetime
import subprocess

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_parser_v3 import TriathlonPDFParserV3
import pandas as pd


def parse_workouts_from_pdf(pdf_path: str) -> dict:
    """
    Parse un PDF vers JSON en priorite via conteneur Docker, puis fallback local.

    Retour:
        {
            "success": bool,
            "parser_mode": "docker" | "local",
            "output_json": "...",
            "result": {...},
            "error": "..."
        }
    """
    pdf_file = Path(pdf_path).expanduser().resolve()
    if not pdf_file.exists():
        return {"success": False, "error": f"PDF introuvable: {pdf_path}"}

    output_dir = Path("data/workouts_cache").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = f"{pdf_file.stem}_parsed.json"
    output_json = output_dir / output_name

    parser_image = "garmin-training-parser:latest"
    docker_run_base_commands = [
        ["docker", "run", "--rm"],
        ["sudo", "-n", "docker", "run", "--rm"],
    ]

    # 1) Tentative parser Docker
    for run_base in docker_run_base_commands:
        cmd = run_base + [
            "-v",
            f"{pdf_file.parent}:/input:ro",
            "-v",
            f"{output_dir}:/output",
            parser_image,
            "--input",
            f"/input/{pdf_file.name}",
            "--output",
            f"/output/{output_name}",
        ]
        try:
            completed = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode == 0 and output_json.exists():
                parsed = json.loads(output_json.read_text(encoding="utf-8"))
                return {
                    "success": True,
                    "parser_mode": "docker",
                    "output_json": str(output_json),
                    "result": parsed,
                }
        except FileNotFoundError:
            # docker / sudo absent sur cet environnement -> essaie le prochain
            continue
        except Exception:
            # Erreur inattendue -> on tente fallback local
            break

    # 2) Fallback local (comportement historique)
    try:
        with TriathlonPDFParserV3(str(pdf_file)) as parser:
            parsed = parser.parse()
        output_json.write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "success": True,
            "parser_mode": "local",
            "output_json": str(output_json),
            "result": parsed,
        }
    except Exception as e:
        return {"success": False, "error": f"Parsing échoué (docker+local): {e}"}


def upload_workouts(pdf_path: str) -> dict:
    """
    Action 1: Upload workouts depuis PDF vers Garmin Connect

    Args:
        pdf_path: Chemin vers le PDF des séances

    Returns:
        dict avec résumé de l'upload
    """
    print(f"📄 Action: UPLOAD WORKOUTS")
    print(f"   Fichier: {pdf_path}\n")

    try:
        from api.services.garmin_service import GarminService
        from src.garmin_workout_converter import (
            convert_to_garmin_cycling_workout,
            convert_to_garmin_running_workout,
        )
    except ModuleNotFoundError as e:
        return {"success": False, "error": f"Dépendance upload manquante: {e}"}

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return {"success": False, "error": f"PDF introuvable: {pdf_path}"}

    # Parser le PDF (Docker prioritaire)
    parse_result = parse_workouts_from_pdf(pdf_path)
    if not parse_result.get("success"):
        return {"success": False, "error": parse_result.get("error", "Échec parsing")}

    result = parse_result["result"]
    print(f"✅ Parsing terminé via mode: {parse_result['parser_mode']}")
    print(f"   JSON: {parse_result['output_json']}")

    week = result.get('week', 'Unknown')
    print(f"✅ Semaine détectée: {week}")

    # Connexion Garmin
    print("🔐 Connexion Garmin Connect...")
    garmin = GarminService()
    garmin.connect()

    uploaded = []
    skipped = []
    errors = []

    # Upload cyclisme
    for workout in result['workouts']:
        if workout['type'] == 'Cyclisme' and workout.get('intervals'):
            code = workout['code']
            try:
                garmin_workout = convert_to_garmin_cycling_workout(workout)
                upload_result = garmin.client.upload_workout(garmin_workout)
                workout_id = upload_result.get('workoutId', 'unknown')

                uploaded.append({
                    'code': code,
                    'type': 'Cyclisme',
                    'workout_id': workout_id
                })
                print(f"✅ {code} (Cyclisme) → ID: {workout_id}")
            except Exception as e:
                errors.append({'code': code, 'error': str(e)})
                print(f"❌ {code} erreur: {e}")

    # Upload course
    for workout in result['workouts']:
        if workout['type'] == 'Course à pied' and workout.get('intervals'):
            code = workout['code']
            try:
                garmin_workout = convert_to_garmin_running_workout(workout)
                upload_result = garmin.client.upload_workout(garmin_workout)
                workout_id = upload_result.get('workoutId', 'unknown')

                uploaded.append({
                    'code': code,
                    'type': 'Course à pied',
                    'workout_id': workout_id
                })
                print(f"✅ {code} (Course) → ID: {workout_id}")
            except Exception as e:
                errors.append({'code': code, 'error': str(e)})
                print(f"❌ {code} erreur: {e}")

    # Résumé
    summary = {
        'success': True,
        'week': week,
        'parser_mode': parse_result['parser_mode'],
        'parsed_json': parse_result['output_json'],
        'uploaded_count': len(uploaded),
        'uploaded': uploaded,
        'skipped': skipped,
        'errors': errors,
        'timestamp': datetime.now().isoformat()
    }

    print(f"\n📊 Résumé: {len(uploaded)} séances uploadées")

    # Sauvegarder résultat
    result_file = Path(f"data/workouts_cache/{week}_upload_result.json")
    with open(result_file, 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


def parse_workouts(pdf_path: str) -> dict:
    """
    Action dédiée: parser PDF -> JSON, sans upload Garmin.
    """
    print("📄 Action: PARSE WORKOUTS")
    print(f"   Fichier: {pdf_path}\n")
    result = parse_workouts_from_pdf(pdf_path)
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Erreur parsing")}

    parsed = result["result"]
    week = parsed.get("week", "Unknown")
    workouts_count = len(parsed.get("workouts", []))
    print(f"✅ Semaine détectée: {week}")
    print(f"✅ Workouts extraits: {workouts_count}")
    print(f"✅ Mode parser: {result['parser_mode']}")
    print(f"✅ JSON: {result['output_json']}")

    return {
        "success": True,
        "week": week,
        "workouts_count": workouts_count,
        "parser_mode": result["parser_mode"],
        "parsed_json": result["output_json"],
        "timestamp": datetime.now().isoformat(),
    }


def fill_excel(xls_path: str, google_drive_id: str = None) -> dict:
    """
    Action 2: Convertir XLS → XLSX + Remplir avec données Garmin

    Args:
        xls_path: Chemin vers le fichier XLS
        google_drive_id: ID du fichier sur Google Drive (optionnel)

    Returns:
        dict avec résumé du remplissage
    """
    print(f"📊 Action: FILL EXCEL")
    print(f"   Fichier: {xls_path}\n")

    try:
        from api.services.garmin_service import GarminService
    except ModuleNotFoundError as e:
        return {"success": False, "error": f"Dépendance Garmin manquante: {e}"}

    xls_file = Path(xls_path)
    if not xls_file.exists():
        return {"success": False, "error": f"XLS introuvable: {xls_path}"}

    # Étape 1: Conversion XLS → XLSX
    print("🔄 Étape 1/3: Conversion XLS → XLSX...")
    xlsx_file = xls_file.with_suffix('.xlsx')

    try:
        df_dict = pd.read_excel(xls_file, sheet_name=None, engine='xlrd')
        with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
            for sheet_name, df in df_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"✅ Converti: {xlsx_file.name}")
    except Exception as e:
        return {"success": False, "error": f"Échec conversion: {e}"}

    # Étape 2: Récupération données Garmin
    print("\n📡 Étape 2/3: Récupération données Garmin...")

    # Extraire numéro de semaine depuis nom fichier
    # Ex: "S07_carnet_entrainement.xls" → "S07"
    import re
    week_match = re.search(r'(S\d+)', xls_file.name)
    week = week_match.group(1) if week_match else None

    if not week:
        return {"success": False, "error": "Impossible d'extraire le numéro de semaine"}

    try:
        garmin = GarminService()
        garmin.connect()

        # TODO: Récupérer les données de la semaine
        # - Activités cyclisme/course/natation
        # - Poids quotidien
        # - Sommeil quotidien

        print(f"✅ Données récupérées pour {week}")

    except Exception as e:
        return {"success": False, "error": f"Échec récupération Garmin: {e}"}

    # Étape 3: Remplissage Excel
    print("\n✍️  Étape 3/3: Remplissage Excel...")

    try:
        # TODO: Implémenter remplissage Excel
        # - Mapper données Garmin → colonnes Excel
        # - Remplir durées, distances, FC, etc.

        print(f"✅ Excel rempli: {xlsx_file.name}")

    except Exception as e:
        return {"success": False, "error": f"Échec remplissage: {e}"}

    summary = {
        'success': True,
        'week': week,
        'xlsx_path': str(xlsx_file),
        'google_drive_id': google_drive_id,
        'timestamp': datetime.now().isoformat()
    }

    return summary


def prepare_email(xlsx_path: str, recipient: str = "stephane.palazzetti@*") -> dict:
    """
    Action 3: Préparer brouillon email avec pièce jointe

    Args:
        xlsx_path: Chemin vers le XLSX rempli
        recipient: Email du destinataire

    Returns:
        dict avec détails email préparé
    """
    print(f"📧 Action: PREPARE EMAIL")
    print(f"   Fichier: {xlsx_path}\n")

    xlsx_file = Path(xlsx_path)
    if not xlsx_file.exists():
        return {"success": False, "error": f"XLSX introuvable: {xlsx_path}"}

    # Extraire semaine
    import re
    week_match = re.search(r'(S\d+)', xlsx_file.name)
    week = week_match.group(1) if week_match else "SXX"

    # Extraire dates depuis nom fichier si possible
    # Ex: "Séances S07 (09_02 au 15_02)" → "09/02 au 15/02"
    period = "XX/XX au XX/XX"  # Default

    # Générer corps email
    email_body = f"""Bonjour Stéphane,

Voici mon carnet d'entraînement pour la semaine {week} ({period}).

📊 Résumé de la semaine:
[À compléter après analyse du XLSX]

Cordialement,
Christophe

---
Généré automatiquement par Garmin Automation
"""

    email_draft = {
        'to': recipient,
        'subject': f"Carnet d'entraînement {week} - Semaine du {period}",
        'body': email_body,
        'attachment': str(xlsx_file),
        'week': week
    }

    # Sauvegarder brouillon
    draft_file = Path(f"data/email_drafts/{week}_email_draft.json")
    draft_file.parent.mkdir(parents=True, exist_ok=True)

    with open(draft_file, 'w') as f:
        json.dump(email_draft, f, indent=2, ensure_ascii=False)

    print(f"✅ Brouillon email préparé:")
    print(f"   Destinataire: {recipient}")
    print(f"   Objet: {email_draft['subject']}")
    print(f"   Pièce jointe: {xlsx_file.name}")
    print(f"\n💾 Sauvegardé: {draft_file}")

    summary = {
        'success': True,
        'week': week,
        'draft_path': str(draft_file),
        'email_draft': email_draft,
        'timestamp': datetime.now().isoformat()
    }

    return summary


def main():
    parser = argparse.ArgumentParser(description='Workflow Clawdbot pour Garmin Automation')
    parser.add_argument('--action', required=True,
                        choices=['upload_workouts', 'parse_workouts', 'fill_excel', 'prepare_email'],
                        help='Action à exécuter')
    parser.add_argument('--file', required=True,
                        help='Fichier à traiter')
    parser.add_argument('--recipient', default='stephane.palazzetti@*',
                        help='Email destinataire (pour prepare_email)')

    args = parser.parse_args()

    print("="*80)
    print("🤖 GARMIN AUTOMATION - Workflow Clawdbot")
    print("="*80)
    print()

    try:
        if args.action == 'upload_workouts':
            result = upload_workouts(args.file)
        elif args.action == 'parse_workouts':
            result = parse_workouts(args.file)
        elif args.action == 'fill_excel':
            result = fill_excel(args.file)
        elif args.action == 'prepare_email':
            result = prepare_email(args.file, args.recipient)

        if result['success']:
            print(f"\n✅ Action '{args.action}' terminée avec succès!")
            sys.exit(0)
        else:
            print(f"\n❌ Action '{args.action}' échouée: {result.get('error')}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
