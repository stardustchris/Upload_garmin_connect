#!/usr/bin/env python3
"""
Parser PDF d'entraînements Triathlon (format Delalain)
Extrait les séances de Cyclisme, CAP et Natation depuis le PDF

IMPORTANT : Les entraînements peuvent s'étendre sur 2 pages
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import pdfplumber

class TriathlonPDFParser:
    """Parse les PDFs d'entraînement au format Delalain"""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.full_text = ""
        self.pages_text = []

    def extract_text(self) -> str:
        """Extrait le texte complet du PDF (toutes les pages)"""
        print(f"📖 Lecture du PDF : {self.pdf_path.name}")

        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                self.pages_text.append(page_text)
                self.full_text += f"\n--- PAGE {i} ---\n{page_text}\n"

        print(f"✅ {len(pdf.pages)} pages lues")
        return self.full_text

    def extract_week_info(self) -> Dict:
        """Extrait les informations de la semaine (S06, dates)"""
        # Pattern : "S06 (02_02 au 08_02)_Delalain C_2026.pdf"
        filename = self.pdf_path.stem
        week_pattern = r'S(\d+)'
        date_pattern = r'\((\d{2}_\d{2}) au (\d{2}_\d{2})\)'

        week_match = re.search(week_pattern, filename)
        date_match = re.search(date_pattern, filename)

        week_number = int(week_match.group(1)) if week_match else None
        start_date = date_match.group(1) if date_match else None
        end_date = date_match.group(2) if date_match else None

        return {
            "week": f"S{week_number:02d}" if week_number else "Unknown",
            "start_date": start_date,
            "end_date": end_date,
            "period": f"{start_date} au {end_date}" if start_date and end_date else "Unknown"
        }

    def find_workouts(self) -> List[Dict]:
        """
        Trouve tous les entraînements dans le PDF
        Gère les cas où l'entraînement s'étend sur 2 pages

        Returns:
            Liste de workouts extraits
        """
        workouts = []

        # Patterns pour identifier les séances
        cycling_pattern = r'Cyclisme\s*\n\s*([A-Z]\d+)'  # C16, C18, etc.
        running_pattern = r'([A-Z]{3}\d+)\s*\(.*?le (matin|midi|après-midi|soir)\)'  # CAP19 (Samedi 07/02, le matin)
        swimming_pattern = r'Natation\s*\n\s*([A-Z]\d+)'  # N5

        # Recherche de séances de Cyclisme
        for match in re.finditer(cycling_pattern, self.full_text, re.MULTILINE):
            code = match.group(1)
            # Trouver le contexte autour (peut être sur 2 pages)
            workout = self._extract_cycling_workout(code, match.start())
            if workout:
                workouts.append(workout)

        # Recherche de séances de CAP
        for match in re.finditer(running_pattern, self.full_text, re.MULTILINE):
            code = match.group(1)
            workout = self._extract_running_workout(code, match.start())
            if workout:
                workouts.append(workout)

        # Recherche de séances de Natation
        for match in re.finditer(swimming_pattern, self.full_text, re.MULTILINE):
            code = match.group(1)
            workout = self._extract_swimming_workout(code, match.start())
            if workout:
                workouts.append(workout)

        print(f"🏋️  {len(workouts)} entraînements trouvés")
        return workouts

    def _extract_cycling_workout(self, code: str, position: int) -> Optional[Dict]:
        """Extrait une séance de cyclisme avec zones de puissance et cadence"""

        # Extraire le contexte (1000 caractères après la position)
        context = self.full_text[position:position + 2000]

        # Extraire la date
        date_match = re.search(r'\(([A-Z][a-z]+) (\d{2})/(\d{2})', context)
        date_str = None
        if date_match:
            day_name, day, month = date_match.groups()
            date_str = f"2026-{month}-{day}"

        # Extraire la durée
        duration_match = re.search(r'Durée\s*:\s*(\d+h?\d*)', context)
        duration = duration_match.group(1) if duration_match else "Unknown"

        # Extraire description
        desc_match = re.search(r'Séance (.*?)[\n\r]', context)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extraire les intervalles (tableau avec Durée, Cadence, Puissance)
        intervals = self._parse_cycling_intervals(context)

        # Extraire les notes/consignes
        notes_match = re.search(r'Consignes\s*:(.*?)(?=\n\n|\Z)', context, re.DOTALL)
        notes = notes_match.group(1).strip() if notes_match else ""

        return {
            "code": code,
            "date": date_str,
            "type": "Cyclisme",
            "duration_total": duration,
            "description": description,
            "intervals": intervals,
            "notes": notes
        }

    def _parse_cycling_intervals(self, context: str) -> List[Dict]:
        """Parse le tableau d'intervalles de cyclisme"""
        intervals = []

        # Pattern pour les lignes de tableau
        # Exemple: "Echauffement 02:30 80 à 85 70 à 80"
        table_pattern = r'(Echauffement|Corps de séance|Récupération)\s+([\d:]+)\s+([\d\sà]+)\s+([\d\sà]+)'

        for match in re.finditer(table_pattern, context):
            phase = match.group(1)
            duration = match.group(2)
            cadence = match.group(3).strip()
            power = match.group(4).strip()

            # Gérer les répétitions (2 x (08:00**-02:00))
            repetitions_match = re.search(r'(\d+)\s*x\s*\(([^)]+)\)', context)

            intervals.append({
                "phase": phase,
                "duration": duration,
                "cadence_rpm": cadence,
                "power_watts": power
            })

        return intervals

    def _extract_running_workout(self, code: str, position: int) -> Optional[Dict]:
        """Extrait une séance de course à pied avec allures"""

        context = self.full_text[position:position + 2000]

        # Extraire la date
        date_match = re.search(r'\(Samedi (\d{2})/(\d{2})', context)
        date_str = None
        if date_match:
            day, month = date_match.groups()
            date_str = f"2026-{month}-{day}"

        # Extraire la durée
        duration_match = re.search(r'Durée\s*:\s*(\d+h?\d*)', context)
        duration = duration_match.group(1) if duration_match else "Unknown"

        # Extraire les intervalles (Intensité et Durée)
        intervals = self._parse_running_intervals(context)

        # Extraire les notes
        notes_match = re.search(r'Indications\s*:(.*?)(?=\n\n|\Z)', context, re.DOTALL)
        notes = notes_match.group(1).strip() if notes_match else ""

        return {
            "code": code,
            "date": date_str,
            "type": "Course à pied",
            "duration_total": duration,
            "intervals": intervals,
            "notes": notes
        }

    def _parse_running_intervals(self, context: str) -> List[Dict]:
        """Parse les intervalles de course avec allures"""
        intervals = []

        # Pattern : "4:35 à 4:40  10:00"
        pace_pattern = r'(\d+:\d+\s*à\s*\d+:\d+)\s+(\d+:\d+)'

        for match in re.finditer(pace_pattern, context):
            pace = match.group(1).strip()
            duration = match.group(2).strip()

            intervals.append({
                "phase": "Corps de séance",
                "pace": pace,
                "duration": duration
            })

        return intervals

    def _extract_swimming_workout(self, code: str, position: int) -> Optional[Dict]:
        """Extrait une séance de natation avec distances par nage"""

        context = self.full_text[position:position + 2000]

        # Extraire la date
        date_match = re.search(r'\(Mercredi (\d{2})/(\d{2})', context)
        date_str = None
        if date_match:
            day, month = date_match.groups()
            date_str = f"2026-{month}-{day}"

        # Extraire la durée totale (Total : 2500 m)
        total_match = re.search(r'Total\s*:\s*(\d+)\s*m', context)
        total_distance = total_match.group(1) if total_match else "Unknown"

        # Extraire les séries
        series = self._parse_swimming_series(context)

        # Extraire les distances par nage (tableau en bas)
        distances = self._parse_swimming_distances(context)

        return {
            "code": code,
            "date": date_str,
            "type": "Natation",
            "duration_total": f"{total_distance}m" if total_distance != "Unknown" else "Unknown",
            "series": series,
            "distances": distances
        }

    def _parse_swimming_series(self, context: str) -> List[Dict]:
        """Parse les séries de natation"""
        series = []

        # Pattern : "3 x 100 3 N (CR, Brasse en battement de crawl, CR, Dos)"
        series_pattern = r'([•\d].*?)(?=\n[•\d]|\n\n|CR\s+Dos|\Z)'

        for match in re.finditer(series_pattern, context, re.DOTALL):
            description = match.group(1).strip()

            # Identifier les techniques appliquées
            technique = None
            if "TECHNIQUEMENT APPLIQUE" in description.upper():
                technique = "TECHNIQUEMENT APPLIQUE"

            series.append({
                "description": description,
                "technique": technique
            })

        return series

    def _parse_swimming_distances(self, context: str) -> Dict[str, int]:
        """Parse le tableau des distances par type de nage"""
        distances = {
            "CR": 0,  # Crawl
            "Dos": 0,
            "Brasse": 0,
            "Papillon": 0,
            "Pull": 0,
            "Pull+Plaq.": 0,
            "Educatifs": 0,
            "Pull+Elas.": 0,
            "Palmes": 0
        }

        # Pattern : "CR 1300"
        distance_pattern = r'(CR|Dos|Brasse|Papillon|Pull\+Plaq\.|Pull\+Elas\.|Pull|Educatifs|Palmes)\s+(\d+)'

        for match in re.finditer(distance_pattern, context):
            stroke_type = match.group(1)
            distance = int(match.group(2))
            distances[stroke_type] = distance

        return distances

    def parse(self) -> Dict:
        """
        Parse complet du PDF

        Returns:
            Dict contenant toutes les informations extraites
        """
        self.extract_text()
        week_info = self.extract_week_info()
        workouts = self.find_workouts()

        result = {
            **week_info,
            "workouts": workouts
        }

        return result

    def save_json(self, output_path: str = None):
        """Sauvegarde le résultat en JSON"""
        result = self.parse()

        if output_path is None:
            output_path = self.pdf_path.with_suffix('.json')

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"💾 JSON sauvegardé : {output_path}")
        return output_path


def main():
    """Test du parser avec le fichier S06"""
    pdf_path = "/Users/aptsdae/Documents/Triathlon/Séances S06 (02_02 au 08_02)_Delalain C_2026.pdf"

    parser = TriathlonPDFParser(pdf_path)
    result = parser.parse()

    # Afficher le résultat
    print("\n" + "="*60)
    print("RÉSULTAT DU PARSING")
    print("="*60)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Sauvegarder en JSON
    output_path = "/Users/aptsdae/Documents/Triathlon/garmin_automation/data/workouts_cache/S06_workouts.json"
    parser.save_json(output_path)


if __name__ == "__main__":
    main()
