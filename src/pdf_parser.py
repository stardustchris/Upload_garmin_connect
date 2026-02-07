#!/usr/bin/env python3
"""
Parser PDF d'entraînements Triathlon (format Delalain) - Version améliorée
Utilise pdfplumber pour extraction de tableaux et texte structuré

IMPORTANT : Les entraînements peuvent s'étendre sur 2 pages
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pdfplumber

class TriathlonPDFParser:
    """Parse les PDFs d'entraînement au format Delalain avec extraction de tableaux"""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.pdf = None
        self.pages = []

    def __enter__(self):
        self.pdf = pdfplumber.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pdf:
            self.pdf.close()

    def extract_week_info(self) -> Dict:
        """Extrait les informations de la semaine depuis le nom de fichier"""
        filename = self.pdf_path.stem

        # Pattern : "Séances S06 (02_02 au 08_02)_Delalain C_2026"
        week_match = re.search(r'S(\d+)', filename)
        date_match = re.search(r'\((\d{2}_\d{2}) au (\d{2}_\d{2})\)', filename)

        week_number = int(week_match.group(1)) if week_match else None
        start_date = date_match.group(1) if date_match else None
        end_date = date_match.group(2) if date_match else None

        return {
            "week": f"S{week_number:02d}" if week_number else "Unknown",
            "start_date": start_date,
            "end_date": end_date,
            "period": f"{start_date} au {end_date}" if start_date and end_date else "Unknown"
        }

    def find_workout_sections(self) -> List[Tuple[str, int, int, str]]:
        """
        Identifie toutes les sections de workout dans le PDF

        Returns:
            List de (code_workout, page_start, page_end, full_text)
        """
        sections = []

        # Patterns pour identifier les débuts de séances
        workout_patterns = {
            'cycling': r'Cyclisme\s*\n\s*([A-Z]\d+)\s*\(',
            'running': r'([A-Z]{3}\d+)\s*\(.*?(\d{2}/\d{2}).*?\)',
            'swimming': r'Natation\s*\n\s*([A-Z]\d+)\s*\('
        }

        for page_num, page in enumerate(self.pdf.pages):
            page_text = page.extract_text()

            for workout_type, pattern in workout_patterns.items():
                for match in re.finditer(pattern, page_text, re.MULTILINE):
                    code = match.group(1)

                    # Chercher la fin de la séance (prochain workout ou fin de page)
                    # On prend 2 pages pour gérer le cas où ça déborde
                    end_page = min(page_num + 2, len(self.pdf.pages))

                    # Extraire le texte complet de cette section
                    section_text = page_text[match.start():]

                    # Ajouter la page suivante si nécessaire
                    if end_page > page_num + 1 and page_num + 1 < len(self.pdf.pages):
                        next_page_text = self.pdf.pages[page_num + 1].extract_text()
                        section_text += "\n" + next_page_text

                    sections.append((code, page_num, end_page, section_text, workout_type))

        return sections

    def parse_date_from_text(self, text: str, year: int = 2026) -> Optional[str]:
        """Parse la date depuis le texte (ex: 'Lundi 02/02', 'Samedi 07/02')"""
        date_match = re.search(r'(\d{2})/(\d{2})', text)
        if date_match:
            day, month = date_match.groups()
            return f"{year}-{month}-{day}"
        return None

    def parse_cycling_workout(self, code: str, text: str) -> Dict:
        """Parse une séance de cyclisme avec extraction de tableau"""

        workout = {
            "code": code,
            "date": self.parse_date_from_text(text),
            "type": "Cyclisme",
            "duration_total": None,
            "description": None,
            "intervals": [],
            "notes": None
        }

        # Extraire la description
        desc_match = re.search(r'Séance\s+(.*?)[\n•]', text)
        if desc_match:
            workout["description"] = desc_match.group(1).strip()

        # Extraire la durée
        duration_match = re.search(r'Durée\s*:\s*(\d+h\d+)', text)
        if duration_match:
            workout["duration_total"] = duration_match.group(1)

        # Parser les intervalles depuis le tableau
        # Chercher le pattern du tableau : phase, durée, cadence, puissance
        table_section = re.search(
            r'Répartition de la séance\s*:.*?Consignes',
            text,
            re.DOTALL
        )

        if table_section:
            table_text = table_section.group(0)

            # Parser les lignes du tableau
            intervals = self._parse_cycling_table(table_text)
            workout["intervals"] = intervals

        # Extraire les notes/consignes
        notes_match = re.search(r'Consignes\s*:(.*?)(?=\n\s*\n|\Z)', text, re.DOTALL)
        if notes_match:
            workout["notes"] = notes_match.group(1).strip()

        return workout

    def _parse_cycling_table(self, table_text: str) -> List[Dict]:
        """Parse le tableau d'intervalles de cyclisme de manière robuste"""
        intervals = []

        # Chercher les blocs d'intervalles
        # Pattern pour une ligne de tableau: phase (optionnel) | durée | cadence | puissance

        # D'abord identifier les phases principales
        phases_blocks = {
            'Echauffement': [],
            'Corps de séance': [],
            'Récupération': []
        }

        current_phase = None

        lines = table_text.split('\n')
        for line in lines:
            line = line.strip()

            # Identifier le changement de phase
            if 'Echauffement' in line:
                current_phase = 'Echauffement'
            elif 'Corps de séance' in line:
                current_phase = 'Corps de séance'
            elif 'Récupération' in line:
                current_phase = 'Récupération'

            # Parser les valeurs (durée, cadence, puissance)
            # Pattern : MM:SS ou HH:MM:SS suivis de rpm et W
            interval_match = re.search(
                r'(\d{1,2}:\d{2})\s+(\d+\s*à\s*\d+)\s+(\d+\s*à\s*\d+)',
                line
            )

            if interval_match and current_phase:
                duration = interval_match.group(1)
                cadence = interval_match.group(2).replace(' ', '')
                power = interval_match.group(3).replace(' ', '')

                # Chercher des indications de position (aéro, haute)
                position = None
                if 'Position aéro' in line or 'aéro.' in line:
                    position = 'Position aéro'
                elif 'Position haute' in line:
                    position = 'Position haute'

                interval = {
                    "phase": current_phase,
                    "duration": duration,
                    "cadence_rpm": cadence,
                    "power_watts": power
                }

                if position:
                    interval["position"] = position

                intervals.append(interval)

        return intervals

    def parse_running_workout(self, code: str, text: str) -> Dict:
        """Parse une séance de course à pied"""

        workout = {
            "code": code,
            "date": self.parse_date_from_text(text),
            "type": "Course à pied",
            "duration_total": None,
            "intervals": [],
            "notes": None
        }

        # Extraire la durée
        duration_match = re.search(r'Durée\s*:\s*(\d+h\d+)', text)
        if duration_match:
            workout["duration_total"] = duration_match.group(1)

        # Parser le tableau d'intervalles
        table_section = re.search(
            r'Répartition de la séance\s*:.*?Indications',
            text,
            re.DOTALL
        )

        if table_section:
            table_text = table_section.group(0)
            intervals = self._parse_running_table(table_text)
            workout["intervals"] = intervals

        # Extraire les notes
        notes_match = re.search(r'Indications\s*:(.*?)(?=\n\s*\n|\Z)', text, re.DOTALL)
        if notes_match:
            workout["notes"] = notes_match.group(1).strip()

        return workout

    def _parse_running_table(self, table_text: str) -> List[Dict]:
        """Parse le tableau d'intervalles de CAP"""
        intervals = []

        current_phase = None

        lines = table_text.split('\n')
        for line in lines:
            line = line.strip()

            # Identifier les phases
            if 'Echauffement' in line:
                current_phase = 'Echauffement'
            elif 'Corps de séance' in line:
                current_phase = 'Corps de séance'
            elif 'Récupération' in line:
                current_phase = 'Récupération'

            # Parser les intervalles: allure (min:ss/km) et durée
            interval_match = re.search(
                r'(\d:\d{2}\s*à\s*\d:\d{2})\s+(\d{1,2}:\d{2})',
                line
            )

            if interval_match and current_phase:
                pace = interval_match.group(1).replace(' ', '')
                duration = interval_match.group(2)

                intervals.append({
                    "phase": current_phase,
                    "pace_min_per_km": pace,
                    "duration": duration
                })

            # Gérer les allures sans zone (ex: "Allure modérée à faible")
            elif current_phase and ('Allure' in line or 'allure' in line):
                duration_match = re.search(r'(\d{1,2}:\d{2})', line)
                if duration_match:
                    intervals.append({
                        "phase": current_phase,
                        "pace_description": line.split(duration_match.group(0))[0].strip(),
                        "duration": duration_match.group(1)
                    })

        return intervals

    def parse_swimming_workout(self, code: str, text: str) -> Dict:
        """Parse une séance de natation"""

        workout = {
            "code": code,
            "date": self.parse_date_from_text(text),
            "type": "Natation",
            "duration_total": None,
            "series": [],
            "distances": {}
        }

        # Extraire le volume total
        total_match = re.search(r'Total\s*:\s*(\d+)\s*m', text)
        if total_match:
            workout["duration_total"] = f"{total_match.group(1)}m"

        # Parser les séries (lignes commençant par •)
        series_section = re.search(
            r'Corps de séance(.*?)(?:CR\s+Dos\s+Brasse|Total\s*:)',
            text,
            re.DOTALL
        )

        if series_section:
            series_text = series_section.group(1)
            series = self._parse_swimming_series(series_text)
            workout["series"] = series

        # Parser les distances par type de nage
        distances_match = re.search(
            r'(CR|Pull\+Plaq\.|Pull|Dos|Brasse)\s+(\d+)',
            text
        )

        if distances_match:
            workout["distances"] = self._parse_swimming_distances(text)

        return workout

    def _parse_swimming_series(self, text: str) -> List[Dict]:
        """Parse les séries de natation"""
        series = []

        # Chercher les lignes commençant par •
        series_lines = re.findall(r'•\s*([^\n]+)', text)

        for line in series_lines:
            line = line.strip()

            # Identifier si c'est une série technique
            technique = "TECHNIQUEMENT APPLIQUE" if "TECHNIQUEMENT APPLIQUE" in line else None

            # Nettoyer la ligne
            clean_line = line.replace(", TECHNIQUEMENT APPLIQUE", "").strip()

            series.append({
                "description": clean_line,
                "technique": technique
            })

        return series

    def _parse_swimming_distances(self, text: str) -> Dict[str, int]:
        """Parse le tableau des distances par nage"""
        distances = {
            "CR": 0,
            "Dos": 0,
            "Brasse": 0,
            "Papillon": 0,
            "Pull": 0,
            "Pull+Plaq.": 0,
            "Educatifs": 0,
            "Pull+Elas.": 0,
            "Palmes": 0
        }

        # Chercher le tableau de distances (généralement en bas)
        # Pattern: type de nage suivi de distance
        for stroke_type in distances.keys():
            # Échapper les caractères spéciaux pour regex
            escaped_type = re.escape(stroke_type)
            pattern = f'{escaped_type}\\s+(\\d+)'

            match = re.search(pattern, text)
            if match:
                distances[stroke_type] = int(match.group(1))

        return distances

    def parse(self) -> Dict:
        """Parse complet du PDF"""

        print(f"📖 Lecture du PDF : {self.pdf_path.name}")

        week_info = self.extract_week_info()
        sections = self.find_workout_sections()

        print(f"🔍 {len(sections)} sections de workout trouvées")

        workouts = []

        for code, page_start, page_end, text, workout_type in sections:
            try:
                if workout_type == 'cycling':
                    workout = self.parse_cycling_workout(code, text)
                elif workout_type == 'running':
                    workout = self.parse_running_workout(code, text)
                elif workout_type == 'swimming':
                    workout = self.parse_swimming_workout(code, text)
                else:
                    continue

                workouts.append(workout)
                print(f"✅ {code} ({workout['type']}) parsé")

            except Exception as e:
                print(f"⚠️  Erreur parsing {code}: {e}")
                continue

        print(f"🏋️  {len(workouts)} entraînements parsés avec succès")

        return {
            **week_info,
            "workouts": workouts
        }

    def save_json(self, output_path: str = None) -> Path:
        """Sauvegarde le résultat en JSON"""
        result = self.parse()

        if output_path is None:
            output_path = self.pdf_path.with_suffix('.json')

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"💾 JSON sauvegardé : {output_path}")
        return output_path


def main():
    """Test du parser amélioré"""
    pdf_path = "/Users/aptsdae/Documents/Triathlon/Séances S06 (02_02 au 08_02)_Delalain C_2026.pdf"

    with TriathlonPDFParser(pdf_path) as parser:
        result = parser.parse()

        # Afficher résumé
        print("\n" + "="*60)
        print(f"SEMAINE: {result['week']} ({result['period']})")
        print("="*60)

        for workout in result['workouts']:
            print(f"\n{workout['code']} - {workout['type']}")
            print(f"  Date: {workout['date']}")
            print(f"  Durée: {workout['duration_total']}")
            print(f"  Intervalles: {len(workout.get('intervals', []))}")

        # Sauvegarder
        output_path = "/Users/aptsdae/Documents/Triathlon/garmin_automation/data/workouts_cache/S06_workouts.json"
        parser.save_json(output_path)


if __name__ == "__main__":
    main()
