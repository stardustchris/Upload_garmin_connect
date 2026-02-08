#!/usr/bin/env python3
"""
Script de vérification des mises à jour de dépendances

Vérifie si de nouvelles versions de python-garminconnect et autres
dépendances critiques sont disponibles.

Usage:
    python scripts/check_updates.py
"""

import subprocess
import sys
import json
from datetime import datetime


def get_installed_version(package: str) -> str:
    """Récupère la version installée d'un package."""
    try:
        result = subprocess.run(
            ["pip", "show", package],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                return line.split(':', 1)[1].strip()
    except subprocess.CalledProcessError:
        return "NOT_INSTALLED"
    return "UNKNOWN"


def get_latest_version(package: str) -> str:
    """Récupère la dernière version disponible sur PyPI."""
    try:
        result = subprocess.run(
            ["pip", "index", "versions", package],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.split('\n'):
            if 'LATEST:' in line:
                return line.split('LATEST:', 1)[1].strip()
    except subprocess.CalledProcessError:
        return "UNKNOWN"
    return "UNKNOWN"


def check_package_updates(packages: list[str]) -> dict:
    """
    Vérifie les mises à jour pour une liste de packages.

    Returns:
        Dict avec status de chaque package
    """
    results = {}

    for package in packages:
        installed = get_installed_version(package)
        latest = get_latest_version(package)

        needs_update = installed != latest and latest != "UNKNOWN"

        results[package] = {
            "installed": installed,
            "latest": latest,
            "needs_update": needs_update
        }

    return results


def main():
    print("🔍 Vérification des mises à jour de dépendances")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # Packages critiques à surveiller
    critical_packages = [
        "garminconnect",
        "garth",
        "pydantic",
        "fastapi",
        "PyPDF2"
    ]

    results = check_package_updates(critical_packages)

    has_updates = False

    for package, info in results.items():
        installed = info["installed"]
        latest = info["latest"]
        needs_update = info["needs_update"]

        status_emoji = "⚠️" if needs_update else "✅"

        print(f"{status_emoji} {package:20s} {installed:15s} → {latest:15s}")

        if needs_update:
            has_updates = True

    print()
    print("=" * 70)

    if has_updates:
        print()
        print("⚠️  MISES À JOUR DISPONIBLES")
        print()
        print("Pour mettre à jour :")
        print("  source venv/bin/activate")
        print("  pip install --upgrade garminconnect garth")
        print()
        print("Ou pour tout mettre à jour :")
        print("  pip install --upgrade -r requirements.txt")

        sys.exit(1)  # Exit code 1 pour indiquer des mises à jour disponibles
    else:
        print("✅ Toutes les dépendances sont à jour !")
        sys.exit(0)


if __name__ == '__main__':
    main()
