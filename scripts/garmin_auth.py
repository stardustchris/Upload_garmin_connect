#!/usr/bin/env python3
"""
Script d'authentification interactive Garmin Connect

Exécuter ce script UNE FOIS pour établir la session garth avec MFA.
Les tokens seront stockés dans ~/.garth/ pour réutilisation.

Usage:
    python scripts/garmin_auth.py
"""

import os
import sys
from pathlib import Path

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import garth

# Charger .env
load_dotenv()

GARMIN_EMAIL = os.getenv('GARMIN_EMAIL')
GARMIN_PASSWORD = os.getenv('GARMIN_PASSWORD')

if not GARMIN_EMAIL or not GARMIN_PASSWORD:
    print("❌ GARMIN_EMAIL ou GARMIN_PASSWORD manquant dans .env")
    sys.exit(1)

print("🔐 Authentification Garmin Connect")
print(f"📧 Email: {GARMIN_EMAIL}")
print()

try:
    # Tenter de reprendre session existante
    garth_dir = Path.home() / ".garth"
    if garth_dir.exists():
        print("📂 Session garth existante trouvée, tentative de reprise...")
        try:
            garth.resume(str(garth_dir))
            garth.client.username = GARMIN_EMAIL
            print("✅ Session garth reprise avec succès!")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️  Session invalide ({e}), nouvelle connexion nécessaire...")

    # Connexion interactive (MFA supporté)
    print("🔑 Connexion en cours...")
    print("💡 Si MFA activé, entrer le code à l'invite")
    print()

    garth.login(GARMIN_EMAIL, GARMIN_PASSWORD)
    garth.save(str(garth_dir))

    print()
    print("✅ Authentification réussie!")
    print(f"📁 Tokens sauvegardés dans {garth_dir}")
    print()
    print("💡 L'API peut maintenant se connecter sans MFA")

except KeyboardInterrupt:
    print("\n⚠️  Authentification annulée")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Erreur: {e}")
    sys.exit(1)
