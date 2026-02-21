#!/usr/bin/env python3
"""
Convertit un fichier XLS en XLSX (même nom de base)

Usage:
    python scripts/2_convert_xls_to_xlsx.py <xls_file>

Exemple:
    python scripts/2_convert_xls_to_xlsx.py "S07_carnet_entrainement.xls"
"""

import sys
from pathlib import Path
import pandas as pd


def convert_xls_to_xlsx(xls_path: str) -> str:
    """
    Convertit un fichier XLS en XLSX

    Args:
        xls_path: Chemin vers le fichier XLS

    Returns:
        Chemin vers le fichier XLSX créé

    Raises:
        FileNotFoundError: Si le fichier XLS n'existe pas
        Exception: Si la conversion échoue
    """

    xls_file = Path(xls_path)

    if not xls_file.exists():
        raise FileNotFoundError(f"Fichier XLS introuvable: {xls_path}")

    print(f"📄 Conversion de {xls_file.name}...")

    # Nouveau chemin XLSX (même nom, extension différente)
    xlsx_file = xls_file.with_suffix('.xlsx')

    try:
        # Lire le fichier XLS
        # engine='xlrd' pour lire les vieux formats .xls
        df_dict = pd.read_excel(xls_file, sheet_name=None, engine='xlrd')

        print(f"   - {len(df_dict)} feuille(s) trouvée(s)")

        # Écrire en XLSX
        # engine='openpyxl' pour écrire en .xlsx
        with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
            for sheet_name, df in df_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"   - Feuille '{sheet_name}': {len(df)} lignes")

        print(f"✅ Conversion réussie: {xlsx_file.name}")
        print(f"   Taille: {xlsx_file.stat().st_size / 1024:.1f} KB")

        return str(xlsx_file)

    except Exception as e:
        print(f"❌ Erreur lors de la conversion: {e}")
        raise


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/2_convert_xls_to_xlsx.py <xls_file>")
        print("\nExemple:")
        print('  python scripts/2_convert_xls_to_xlsx.py "S07_carnet_entrainement.xls"')
        sys.exit(1)

    xls_path = sys.argv[1]

    try:
        xlsx_path = convert_xls_to_xlsx(xls_path)
        print(f"\n💾 Fichier XLSX disponible: {xlsx_path}")
    except Exception as e:
        print(f"\n❌ Échec de la conversion: {e}")
        sys.exit(1)
