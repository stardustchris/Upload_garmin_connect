#!/usr/bin/env python3
"""
Script de conversion Excel .xls → .xlsx
Convertit le template S06_Delalain C_2026.xls en format moderne .xlsx
"""

import sys
import shutil
from pathlib import Path

# On va utiliser libreoffice en ligne de commande car xlrd ne peut plus écrire
# Alternative : Utiliser pandas qui peut lire .xls et écrire .xlsx

try:
    import pandas as pd
except ImportError:
    print("❌ pandas non installé. Installation...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
    import pandas as pd

def convert_xls_to_xlsx(xls_path: str, output_path: str = None, backup: bool = True):
    """
    Convertit un fichier .xls en .xlsx

    Args:
        xls_path: Chemin vers le fichier .xls
        output_path: Chemin de sortie (optionnel, sinon même nom avec .xlsx)
        backup: Créer un backup du fichier original
    """
    xls_file = Path(xls_path)

    if not xls_file.exists():
        print(f"❌ Fichier non trouvé : {xls_path}")
        return False

    # Déterminer le chemin de sortie
    if output_path is None:
        output_path = xls_file.with_suffix('.xlsx')
    else:
        output_path = Path(output_path)

    print(f"📄 Conversion : {xls_file.name} → {output_path.name}")

    # Backup si demandé
    if backup and xls_file.exists():
        backup_path = xls_file.with_suffix('.xls.backup')
        shutil.copy2(xls_file, backup_path)
        print(f"💾 Backup créé : {backup_path.name}")

    try:
        # Lire le fichier .xls avec pandas
        # pandas utilise xlrd en arrière-plan pour .xls
        print("📖 Lecture du fichier .xls...")
        xls = pd.ExcelFile(xls_path, engine='xlrd')

        # Créer le fichier .xlsx avec openpyxl
        print(f"✍️  Écriture du fichier .xlsx ({len(xls.sheet_names)} feuilles)...")
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sheet_name in xls.sheet_names:
                print(f"   - Feuille: {sheet_name}")
                df = pd.read_excel(xls, sheet_name=sheet_name)
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        print(f"✅ Conversion réussie : {output_path}")
        return True

    except Exception as e:
        print(f"❌ Erreur lors de la conversion : {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Convertir le fichier S06
    xls_path = "/Users/aptsdae/Documents/Triathlon/S06_Delalain C_2026.xls"
    success = convert_xls_to_xlsx(xls_path, backup=True)

    if success:
        print("\n🎉 Conversion terminée avec succès !")
    else:
        print("\n❌ Échec de la conversion")
        sys.exit(1)
