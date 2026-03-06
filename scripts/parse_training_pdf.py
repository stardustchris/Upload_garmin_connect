#!/usr/bin/env python3
"""
CLI de parsing PDF d'entrainements triathlon.

Exemples:
  python scripts/parse_training_pdf.py --input /data/in/S06.pdf --output /data/out/S06.json
  python scripts/parse_training_pdf.py --input /data/in/S06.pdf
"""

import argparse
import json
import sys
from pathlib import Path

# Ajoute la racine projet au PYTHONPATH pour importer src.*
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pdf_parser_v3 import parse_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse un PDF d'entrainements et sort un JSON.")
    parser.add_argument("--input", required=True, help="Chemin du PDF source")
    parser.add_argument("--output", help="Chemin du JSON de sortie")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Erreur: fichier introuvable: {input_path}", file=sys.stderr)
        return 1

    result = parse_pdf(str(input_path))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"JSON ecrit: {output_path}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
