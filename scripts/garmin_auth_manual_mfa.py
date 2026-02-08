#!/usr/bin/env python3
"""
Script d'authentification Garmin avec MFA manuel

Le code MFA sera demandé via input() avec un délai plus long
pour vous laisser le temps de le récupérer.

Usage:
    python scripts/garmin_auth_manual_mfa.py
"""

import os
import sys
from pathlib import Path
import time

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

print("🔐 Authentification Garmin Connect avec MFA manuel")
print(f"📧 Email: {GARMIN_EMAIL}")
print()

def prompt_mfa_manual():
    """
    Fonction custom pour demander le code MFA

    Cette fonction sera appelée par garth quand le code MFA est nécessaire.
    Elle attend que vous entriez le code manuellement.
    """
    print("\n" + "="*60)
    print("⏰ CODE MFA REQUIS")
    print("="*60)
    print()
    print("📱 Vérifiez votre:")
    print("   - SMS")
    print("   - Application d'authentification (Google Authenticator, etc.)")
    print("   - Email")
    print()
    print("⌨️  Entrez le code MFA ci-dessous:")
    print()

    # Demander le code avec timeout généreux
    mfa_code = input("Code MFA (6 chiffres): ").strip()

    if not mfa_code:
        print("❌ Code vide!")
        return None

    print(f"\n✅ Code reçu: {mfa_code}")
    print("🔄 Validation en cours...\n")

    return mfa_code

try:
    # Tenter de reprendre session existante
    garth_dir = Path.home() / ".garth"
    if garth_dir.exists():
        print("📂 Session garth existante trouvée, tentative de reprise...")
        try:
            garth.resume(str(garth_dir))
            garth.client.username = GARMIN_EMAIL
            print("✅ Session garth reprise avec succès!")
            print(f"👤 Connecté en tant que: {garth.client.username}")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️  Session invalide ({e}), nouvelle connexion nécessaire...")
            print()

    # Connexion avec MFA manuel
    print("🔑 Connexion en cours...")
    print("💡 Un code MFA vous sera demandé si nécessaire")
    print()

    # Important: passer la fonction prompt_mfa à garth.login()
    garth.login(GARMIN_EMAIL, GARMIN_PASSWORD, prompt_mfa=prompt_mfa_manual)

    # Sauvegarder la session
    garth.save(str(garth_dir))

    print()
    print("="*60)
    print("✅ AUTHENTIFICATION RÉUSSIE!")
    print("="*60)
    print(f"📁 Tokens sauvegardés dans {garth_dir}")
    print()
    print("💡 L'API peut maintenant se connecter sans MFA")
    print("   Les tokens sont valides pendant ~1 an")
    print()
    print("🎯 Prochaine étape:")
    print("   python scripts/test_upload_c16.py")

except KeyboardInterrupt:
    print("\n⚠️  Authentification annulée")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Erreur: {e}")
    print()
    print("💡 Vérifiez:")
    print("   1. Email/password corrects dans .env")
    print("   2. Code MFA valide (essayez à nouveau)")
    print("   3. Connexion internet stable")
    import traceback
    traceback.print_exc()
    sys.exit(1)
