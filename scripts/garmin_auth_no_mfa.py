#!/usr/bin/env python3
"""
Script d'authentification Garmin SANS MFA

Tente de se connecter en utilisant garth avec différentes méthodes
pour contourner le problème MFA.

Usage:
    python scripts/garmin_auth_no_mfa.py
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

print("🔐 Authentification Garmin Connect SANS MFA")
print(f"📧 Email: {GARMIN_EMAIL}")
print()
print("💡 Cette méthode utilise garth.login() sans prompt_mfa")
print("   Si le compte n'a PAS de MFA activé, cela devrait fonctionner")
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
            print(f"👤 Connecté en tant que: {garth.client.username}")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️  Session invalide ({e}), nouvelle connexion nécessaire...")
            print()

    # Connexion SANS MFA
    print("🔑 Tentative de connexion sans MFA...")
    print()

    # Si le compte a MFA désactivé, cela fonctionnera
    # Si le compte a MFA activé, cela échouera avec une erreur claire
    garth.login(GARMIN_EMAIL, GARMIN_PASSWORD)

    # Sauvegarder la session
    garth.save(str(garth_dir))

    print()
    print("="*70)
    print("✅ AUTHENTIFICATION RÉUSSIE!")
    print("="*70)
    print(f"📁 Tokens sauvegardés dans {garth_dir}")
    print()
    print("💡 L'API peut maintenant se connecter sans MFA")
    print("   Les tokens sont valides pendant ~1 an")
    print()
    print("🎯 Prochaine étape:")
    print("   python scripts/test_upload_c16.py")

except Exception as e:
    print()
    print("="*70)
    print("❌ ÉCHEC DE L'AUTHENTIFICATION")
    print("="*70)
    print(f"Erreur: {e}")
    print()

    error_str = str(e).lower()

    if "mfa" in error_str or "verification" in error_str:
        print("💡 Le compte a MFA ACTIVÉ")
        print()
        print("Solutions:")
        print()
        print("1. DÉSACTIVER LE MFA TEMPORAIREMENT:")
        print("   • Aller sur https://www.garmin.com/account")
        print("   • Sécurité → Authentification à deux facteurs → Désactiver")
        print("   • Relancer ce script")
        print("   • Réactiver le MFA après l'upload")
        print()
        print("2. CONTACTER GARMIN SUPPORT:")
        print("   • Signaler que vous ne recevez pas les codes MFA")
        print("   • Demander reset du MFA")
        print()
        print("3. UTILISER UN AUTRE COMPTE (si possible):")
        print("   • Créer un compte Garmin test sans MFA")
        print("   • Tester l'upload sur ce compte")
    else:
        print("💡 Vérifiez:")
        print("   1. Email/password corrects dans .env")
        print("   2. Connexion internet stable")
        print("   3. Compte Garmin actif et non bloqué")

    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)
