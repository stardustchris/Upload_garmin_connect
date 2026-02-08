#!/usr/bin/env python3
"""
Script d'authentification Garmin avec MFA via fichier

Le code MFA doit être écrit dans un fichier temporaire.

Usage:
    1. Lancer ce script (il va attendre le code MFA)
    2. Dans un autre terminal, écrire le code MFA dans /tmp/garmin_mfa_code.txt
    3. Le script va lire le code et continuer

    python scripts/garmin_auth_file_mfa.py
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
MFA_FILE = Path("/tmp/garmin_mfa_code.txt")

if not GARMIN_EMAIL or not GARMIN_PASSWORD:
    print("❌ GARMIN_EMAIL ou GARMIN_PASSWORD manquant dans .env")
    sys.exit(1)

print("🔐 Authentification Garmin Connect avec MFA via fichier")
print(f"📧 Email: {GARMIN_EMAIL}")
print()

def prompt_mfa_from_file():
    """
    Fonction custom pour lire le code MFA depuis un fichier

    Attend que l'utilisateur crée le fichier /tmp/garmin_mfa_code.txt
    avec le code MFA dedans.
    """
    print("\n" + "="*70)
    print("⏰ CODE MFA REQUIS")
    print("="*70)
    print()
    print("📱 Récupérez votre code MFA (SMS/App/Email)")
    print()
    print("📝 DANS UN AUTRE TERMINAL, exécutez:")
    print()
    print(f"    echo 'VOTRE_CODE_MFA' > {MFA_FILE}")
    print()
    print("   Exemple:")
    print(f"    echo '123456' > {MFA_FILE}")
    print()
    print("⏳ En attente du fichier...")
    print()

    # Supprimer le fichier s'il existe déjà (ancien code)
    if MFA_FILE.exists():
        MFA_FILE.unlink()

    # Attendre que le fichier soit créé (max 5 minutes)
    max_wait = 300  # 5 minutes
    start_time = time.time()

    while not MFA_FILE.exists():
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            print(f"\n❌ Timeout après {max_wait}s - fichier non créé")
            return None

        # Afficher un point toutes les 5 secondes
        if int(elapsed) % 5 == 0:
            print(".", end="", flush=True)

        time.sleep(1)

    # Lire le code du fichier
    time.sleep(0.5)  # Petit délai pour être sûr que l'écriture est finie
    mfa_code = MFA_FILE.read_text().strip()

    # Nettoyer le fichier
    MFA_FILE.unlink()

    if not mfa_code:
        print("\n❌ Fichier vide!")
        return None

    print(f"\n\n✅ Code MFA reçu: {mfa_code}")
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

    # Connexion avec MFA via fichier
    print("🔑 Connexion en cours...")
    print("💡 Le code MFA sera demandé via fichier si nécessaire")
    print()

    # Important: passer la fonction prompt_mfa à garth.login()
    garth.login(GARMIN_EMAIL, GARMIN_PASSWORD, prompt_mfa=prompt_mfa_from_file)

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

except KeyboardInterrupt:
    print("\n⚠️  Authentification annulée")
    if MFA_FILE.exists():
        MFA_FILE.unlink()
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
    if MFA_FILE.exists():
        MFA_FILE.unlink()
    sys.exit(1)
