#!/usr/bin/env python3
"""
Script d'authentification Garmin Connect avec support MFA
"""

import os
import sys
import garth
from pathlib import Path


def authenticate_garmin(email: str, password: str, mfa_code: str = None):
    """
    Authentifie avec Garmin Connect et sauvegarde les tokens

    Args:
        email: Email Garmin
        password: Mot de passe Garmin
        mfa_code: Code MFA optionnel (si déjà reçu par email)
    """

    print(f"🔐 Authentification Garmin Connect...")
    print(f"Email: {email}")

    try:
        # Tentative de connexion
        if mfa_code:
            print(f"Code MFA fourni: {mfa_code}")
            garth.login(email, password, prompt_mfa=lambda: mfa_code)
        else:
            print("⚠️  Si vous avez MFA activé, un code vous sera envoyé par email")
            print("Attendez de recevoir le code, puis relancez ce script avec:")
            print(f"  python garmin_auth.py {email} <mot_de_passe> <code_mfa>")

            # Tentative sans MFA d'abord
            garth.login(email, password)

        # Sauvegarder les tokens
        garth_dir = Path.home() / ".garth"
        garth.save(str(garth_dir))

        print(f"✅ Authentification réussie!")
        print(f"📁 Tokens sauvegardés dans: {garth_dir}")
        print("\nVous pouvez maintenant uploader des workouts sans redemander le code MFA.")
        print("Les tokens sont valables ~1 an.")

        return True

    except Exception as e:
        error_msg = str(e).lower()

        if "mfa" in error_msg or "verification" in error_msg:
            print("\n⚠️  AUTHENTIFICATION MFA REQUISE")
            print("Un code de vérification a été envoyé à votre email Garmin.")
            print("\nÉtapes:")
            print("1. Vérifiez votre email (cdelalain@hotmail.com)")
            print("2. Copiez le code de vérification")
            print("3. Relancez ce script avec:")
            print(f"   python garmin_auth.py {email} {password} <CODE_MFA>")
            return False

        elif "401" in str(e) or "unauthorized" in error_msg:
            print("❌ Email ou mot de passe incorrect")
            print(f"Email utilisé: {email}")
            return False

        else:
            print(f"❌ Erreur inattendue: {e}")
            print(f"Type: {type(e).__name__}")
            return False


def main():
    """Point d'entrée principal"""

    if len(sys.argv) < 3:
        print("Usage: python garmin_auth.py <email> <password> [mfa_code]")
        print("\nExemple:")
        print("  python garmin_auth.py cdelalain@hotmail.com monpassword")
        print("  python garmin_auth.py cdelalain@hotmail.com monpassword 123456")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    mfa_code = sys.argv[3] if len(sys.argv) > 3 else None

    success = authenticate_garmin(email, password, mfa_code)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
