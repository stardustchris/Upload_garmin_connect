#!/usr/bin/env python3
"""
Script pour extraire les tokens Garmin depuis le navigateur

Si vous êtes déjà connecté à Garmin Connect dans Chrome/Firefox,
ce script peut extraire les tokens OAuth pour les réutiliser.

IMPORTANT: Vous devez être DÉJÀ CONNECTÉ à https://connect.garmin.com
dans votre navigateur avant d'exécuter ce script.

Usage:
    python scripts/extract_browser_tokens.py
"""

import os
import sys
from pathlib import Path
import json

print("🔍 Extraction des tokens Garmin depuis le navigateur")
print()
print("⚠️  PRÉREQUIS:")
print("   Vous devez être DÉJÀ CONNECTÉ à https://connect.garmin.com")
print("   dans votre navigateur (Chrome, Firefox, Safari)")
print()

# Vérifier si déjà connecté
response = input("Êtes-vous actuellement connecté à Garmin Connect dans votre navigateur? (o/n): ").lower()
if response != 'o':
    print()
    print("📱 Pour contourner le problème MFA:")
    print()
    print("1. Ouvrez votre navigateur")
    print("2. Allez sur https://connect.garmin.com")
    print("3. Connectez-vous (même avec MFA qui ne fonctionne pas)")
    print("   - Si le MFA bloque, essayez:")
    print("     • Désactiver temporairement le MFA dans les paramètres du compte")
    print("     • Utiliser un autre appareil où vous êtes déjà connecté")
    print("     • Contacter le support Garmin pour le problème MFA")
    print()
    sys.exit(1)

print()
print("=" * 70)
print("MÉTHODE MANUELLE - Extraction des cookies")
print("=" * 70)
print()
print("Suivez ces étapes dans votre navigateur:")
print()
print("1. Allez sur https://connect.garmin.com (où vous êtes connecté)")
print()
print("2. Ouvrez les DevTools:")
print("   Chrome/Edge: Cmd+Option+I (Mac) ou F12 (Windows)")
print("   Firefox: Cmd+Option+I (Mac) ou F12 (Windows)")
print("   Safari: Cmd+Option+I (après avoir activé le menu Développeur)")
print()
print("3. Allez dans l'onglet 'Application' (Chrome) ou 'Storage' (Firefox)")
print()
print("4. Dans le menu de gauche:")
print("   → Cookies")
print("   → https://connect.garmin.com")
print()
print("5. Cherchez ces cookies et copiez leurs VALEURS:")
print()
print("   Cookie 'OAuth_token_secret' → Valeur: _____________")
print("   Cookie 'OAuth_token' → Valeur: _____________")
print()
print("6. Collez ces valeurs ci-dessous:")
print()

oauth_token = input("OAuth_token (valeur complète): ").strip()
oauth_token_secret = input("OAuth_token_secret (valeur complète): ").strip()

if not oauth_token or not oauth_token_secret:
    print("\n❌ Tokens manquants!")
    sys.exit(1)

print()
print("📝 Création de la session garth...")

# Créer la structure de tokens garth
garth_dir = Path.home() / ".garth"
garth_dir.mkdir(exist_ok=True)

# Format attendu par garth (simplifié)
tokens = {
    "oauth1_token": {
        "oauth_token": oauth_token,
        "oauth_token_secret": oauth_token_secret
    }
}

# Sauvegarder dans le format garth
tokens_file = garth_dir / "tokens.json"
with open(tokens_file, 'w') as f:
    json.dump(tokens, f, indent=2)

print(f"✅ Tokens sauvegardés dans {tokens_file}")
print()
print("⚠️  ATTENTION:")
print("   Cette méthode est partielle. Les tokens OAuth2 manquent.")
print("   Cela peut ne pas fonctionner pour toutes les opérations.")
print()
print("💡 Si l'upload échoue, il faudra:")
print("   - Désactiver temporairement le MFA sur le compte Garmin")
print("   - OU contacter le support Garmin pour le problème de réception MFA")
