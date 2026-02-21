#!/usr/bin/env python3
"""
Analyse le fichier Excel S06 pour comprendre sa structure

Usage:
    python scripts/analyze_excel.py
"""

import sys
from pathlib import Path

# Essayer d'importer xlrd pour lire les fichiers .xls
try:
    import xlrd
except ImportError:
    print("❌ xlrd n'est pas installé. Installation...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xlrd"])
    import xlrd

EXCEL_FILE = Path("/Users/aptsdae/Documents/Triathlon/S06_Delalain C_2026.xls")

print("📊 Analyse du fichier Excel S06")
print("=" * 70)
print()

# Ouvrir le fichier Excel
workbook = xlrd.open_workbook(str(EXCEL_FILE))

print(f"📁 Fichier: {EXCEL_FILE.name}")
print(f"📑 Nombre de feuilles: {workbook.nsheets}")
print()

# Analyser chaque feuille
for sheet_idx in range(workbook.nsheets):
    sheet = workbook.sheet_by_index(sheet_idx)

    print(f"📄 Feuille {sheet_idx + 1}: {sheet.name}")
    print(f"   Lignes: {sheet.nrows}")
    print(f"   Colonnes: {sheet.ncols}")
    print()

    # Afficher les 20 premières lignes pour comprendre la structure
    print("   Aperçu des données:")
    print("   " + "-" * 66)

    for row_idx in range(min(20, sheet.nrows)):
        row_data = []
        for col_idx in range(sheet.ncols):
            cell = sheet.cell(row_idx, col_idx)

            # Formater la valeur selon le type
            if cell.ctype == xlrd.XL_CELL_EMPTY:
                value = ""
            elif cell.ctype == xlrd.XL_CELL_TEXT:
                value = cell.value
            elif cell.ctype == xlrd.XL_CELL_NUMBER:
                value = str(cell.value)
            elif cell.ctype == xlrd.XL_CELL_DATE:
                value = f"DATE({cell.value})"
            else:
                value = str(cell.value)

            row_data.append(value)

        # Afficher la ligne
        print(f"   Ligne {row_idx + 1:2d}: {row_data}")

    if sheet.nrows > 20:
        print(f"   ... ({sheet.nrows - 20} lignes supplémentaires)")

    print()
    print()

print("=" * 70)
print("✅ Analyse terminée")
