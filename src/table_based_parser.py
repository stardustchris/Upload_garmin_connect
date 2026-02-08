#!/usr/bin/env python3
"""
Parser basé sur extract_table() de pdfplumber

Cette approche extrait les tableaux PDF correctement en gardant
la structure Durée | Cadence | Puissance intacte.
"""

import pdfplumber
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class TableBasedWorkoutParser:
    """Parser de workouts basé sur l'extraction de tableaux PDF"""

    # Échauffement HT standard (Home Trainer)
    HT_WARMUP_STANDARD = [
        {"duration": "2:30", "power": "96à106"},
        {"duration": "2:30", "power": "130à136"},
        {"duration": "5:00", "power": "156à166"},
        {"duration": "5:00", "power": "180à190"}
    ]

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.pdf = None

    def __enter__(self):
        self.pdf = pdfplumber.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pdf:
            self.pdf.close()

    def find_workout_page(self, workout_code: str) -> Optional[int]:
        """
        Trouve la page contenant le workout

        Args:
            workout_code: Code du workout (ex: "C19")

        Returns:
            Numéro de page (0-indexed) ou None
        """
        for page_num, page in enumerate(self.pdf.pages):
            text = page.extract_text()
            if workout_code in text and "Répartition de la séance" in text:
                return page_num
        return None

    def parse_cycling_workout(self, workout_code: str) -> Dict[str, Any]:
        """
        Parse un workout de cyclisme depuis le PDF

        Args:
            workout_code: Code du workout (ex: "C19")

        Returns:
            Dict avec la structure du workout
        """
        page_num = self.find_workout_page(workout_code)
        if page_num is None:
            raise ValueError(f"Workout {workout_code} non trouvé dans le PDF")

        page = self.pdf.pages[page_num]
        text = page.extract_text()

        # Extraire métadonnées
        workout = {
            "code": workout_code,
            "type": "Cyclisme",
            "date": self._parse_date(text),
            "indoor": "HT" in text or "home trainer" in text.lower(),
            "duration_total": self._parse_duration_total(text),
            "description": self._parse_description(text),
            "intervals": [],
            "notes": self._parse_notes(text)
        }

        # Extraire le tableau
        tables = page.extract_tables()
        if not tables:
            raise ValueError(f"Aucun tableau trouvé pour {workout_code}")

        # Le tableau principal est généralement le premier
        table = tables[0]

        # Parser le tableau
        intervals = self._parse_cycling_table(table, workout["indoor"])
        workout["intervals"] = intervals

        return workout

    def _parse_cycling_table(self, table: List[List[str]], is_home_trainer: bool) -> List[Dict]:
        """
        Parse le tableau de workout cyclisme

        Args:
            table: Tableau extrait par pdfplumber
            is_home_trainer: True si séance sur HT

        Returns:
            Liste d'intervalles
        """
        intervals = []

        # Header est généralement row 0: ['', 'Durée (min:ss)', 'Cadence (rpm)', 'Puissance (W)']
        # Données commencent à row 1

        for row_idx, row in enumerate(table[1:], start=1):  # Skip header
            phase = (row[0] or "").strip()
            durations_str = (row[1] or "").strip()
            cadences_str = (row[2] or "").strip()
            powers_str = (row[3] or "").strip()

            if not durations_str:
                continue  # Skip empty rows

            # Forcer échauffement HT standard
            if phase.lower() == "echauffement" and is_home_trainer:
                for idx, warmup_block in enumerate(self.HT_WARMUP_STANDARD):
                    intervals.append({
                        "phase": "Echauffement",
                        "duration": warmup_block["duration"],
                        "cadence_rpm": "libre",
                        "cadence_upload_to_garmin": False,
                        "power_watts": warmup_block["power"],
                        "power_watts_original": None,
                        "power_adjustment_w": "Forcé HT standard",
                        "forced_reason": f"Échauffement HT standard bloc {idx + 1}/4"
                    })
                continue

            # Parser le contenu selon la phase
            if "x (" in durations_str:  # Répétitions détectées
                rep_intervals = self._parse_repetition_block(
                    durations_str,
                    cadences_str,
                    powers_str,
                    phase
                )
                intervals.extend(rep_intervals)
            else:
                # Intervalles simples (multi-lignes avec \n)
                simple_intervals = self._parse_simple_multiline(
                    durations_str,
                    cadences_str,
                    powers_str,
                    phase,
                    is_home_trainer
                )
                intervals.extend(simple_intervals)

        return intervals

    def _parse_repetition_block(
        self,
        durations_str: str,
        cadences_str: str,
        powers_str: str,
        phase: str
    ) -> List[Dict]:
        """
        Parse un bloc avec répétitions (ex: "3 x (01:00-02:00-01:00-01:00)")

        Stratégie:
        1. Identifier TOUTES les lignes de déclaration de répétition
        2. Pour chaque répétition, extraire N intervalles depuis cadence/power
        3. Parser les intervalles entre les répétitions comme normaux

        Args:
            durations_str: Colonne durées (contient pattern "X x (...)")
            cadences_str: Colonne cadences (lignes séparées par \n)
            powers_str: Colonne puissances (lignes séparées par \n)
            phase: Phase du workout

        Returns:
            Liste d'intervalles avec metadata de répétition
        """
        intervals = []

        # Splitter les lignes
        duration_lines = [line.strip() for line in durations_str.split('\n') if line.strip()]
        cadence_lines = [line.strip() for line in cadences_str.split('\n') if line.strip()]
        power_lines = [line.strip() for line in powers_str.split('\n') if line.strip()]

        # PHASE 1: Identifier toutes les déclarations de répétition
        repetition_declarations = []
        for dur_idx, dur_line in enumerate(duration_lines):
            rep_match = re.match(r'(\d+)\s*x\s*\(([^)]+)\)\s*(?:\([^)]*\))?.*', dur_line)
            if rep_match:
                repeat_count = int(rep_match.group(1))
                repeat_format = rep_match.group(2)
                expected_count = len(repeat_format.split('-'))
                position_match = re.search(r'\(([^)]*Position[^)]*)\)', dur_line)
                position = position_match.group(1) if position_match else ""

                repetition_declarations.append({
                    "line_idx": dur_idx,
                    "repeat_count": repeat_count,
                    "expected_count": expected_count,
                    "position": position
                })

        # PHASE 2: Parser les intervalles en tenant compte des répétitions
        cadence_idx = 0  # Index dans cadence_lines/power_lines

        for dur_idx, dur_line in enumerate(duration_lines):
            # Vérifier si cette ligne est une déclaration de répétition
            rep_decl = next((r for r in repetition_declarations if r["line_idx"] == dur_idx), None)

            if rep_decl:
                # C'est une déclaration de répétition
                pattern_intervals = []

                # Extraire les expected_count intervalles suivants
                for i in range(rep_decl["expected_count"]):
                    if cadence_idx + i < len(cadence_lines):
                        # La durée est dans duration_lines[dur_idx + 1 + i]
                        dur_data = duration_lines[dur_idx + 1 + i] if (dur_idx + 1 + i) < len(duration_lines) else "00:00"

                        # Nettoyer (enlever position si présente)
                        duration_clean = re.sub(r'\s*\([^)]*\)', '', dur_data).strip()

                        # Ajuster la puissance pour HT si nécessaire
                        power_raw = power_lines[cadence_idx + i]
                        power_adjusted = self._adjust_power_for_ht(power_raw) if self._is_ht_adjustment_needed(phase) else power_raw

                        interval = {
                            "phase": phase,
                            "duration": duration_clean,
                            "cadence_rpm": cadence_lines[cadence_idx + i],
                            "cadence_upload_to_garmin": True,
                            "power_watts": power_adjusted,
                            "power_watts_original": power_raw,
                            "power_adjustment_w": "+15W (HT)" if self._is_ht_adjustment_needed(phase) else None,
                            "position": rep_decl["position"]
                        }
                        pattern_intervals.append(interval)

                # Répéter le pattern repeat_count fois
                for iteration in range(rep_decl["repeat_count"]):
                    for interval in pattern_intervals:
                        interval_copy = interval.copy()
                        interval_copy["repetition_iteration"] = iteration + 1
                        interval_copy["repetition_total"] = rep_decl["repeat_count"]
                        intervals.append(interval_copy)

                # Avancer cadence_idx
                cadence_idx += rep_decl["expected_count"]

            else:
                # Ligne normale (pas une déclaration de répétition)
                # Vérifier si ce n'est pas un intervalle déjà consommé par une répétition
                if dur_idx > 0:
                    # Vérifier si la ligne précédente était une déclaration de répétition
                    prev_rep = next((r for r in repetition_declarations if r["line_idx"] == dur_idx - 1), None)
                    if prev_rep:
                        # Skip car déjà consommé
                        continue

                    # Vérifier si on est dans la zone d'une répétition
                    in_repetition_zone = False
                    for rep_decl in repetition_declarations:
                        if rep_decl["line_idx"] < dur_idx < rep_decl["line_idx"] + rep_decl["expected_count"] + 1:
                            in_repetition_zone = True
                            break

                    if in_repetition_zone:
                        continue  # Skip car fait partie d'une répétition

                # Intervalle normal
                if cadence_idx < len(cadence_lines):
                    position_match = re.search(r'\(([^)]*Position[^)]*)\)', dur_line)
                    position = position_match.group(1) if position_match else ""
                    duration_clean = re.sub(r'\s*\([^)]*\)', '', dur_line).strip()

                    # Ajuster la puissance pour HT si nécessaire
                    power_raw = power_lines[cadence_idx]
                    power_adjusted = self._adjust_power_for_ht(power_raw) if self._is_ht_adjustment_needed(phase) else power_raw

                    interval = {
                        "phase": phase,
                        "duration": duration_clean,
                        "cadence_rpm": cadence_lines[cadence_idx],
                        "cadence_upload_to_garmin": True,
                        "power_watts": power_adjusted,
                        "power_watts_original": power_raw,
                        "power_adjustment_w": "+15W (HT)" if self._is_ht_adjustment_needed(phase) else None,
                        "position": position
                    }
                    intervals.append(interval)
                    cadence_idx += 1

        return intervals

    def _parse_simple_multiline(
        self,
        durations_str: str,
        cadences_str: str,
        powers_str: str,
        phase: str,
        is_home_trainer: bool
    ) -> List[Dict]:
        """
        Parse des intervalles simples (multi-lignes avec \n)

        Args:
            durations_str: Durées séparées par \n
            cadences_str: Cadences séparées par \n
            powers_str: Puissances séparées par \n
            phase: Phase du workout
            is_home_trainer: True si HT

        Returns:
            Liste d'intervalles
        """
        intervals = []

        duration_lines = [line.strip() for line in durations_str.split('\n') if line.strip()]
        cadence_lines = [line.strip() for line in cadences_str.split('\n') if line.strip()]
        power_lines = [line.strip() for line in powers_str.split('\n') if line.strip()]

        # Assurer que toutes les listes ont la même longueur
        max_len = max(len(duration_lines), len(cadence_lines), len(power_lines))

        for i in range(max_len):
            duration = duration_lines[i] if i < len(duration_lines) else "00:00"
            cadence = cadence_lines[i] if i < len(cadence_lines) else "libre"
            power = power_lines[i] if i < len(power_lines) else "0à0"

            # Extraire position si présente (ex: "01:00 (Position haute)")
            position_match = re.search(r'\(([^)]*Position[^)]*)\)', duration)
            position = position_match.group(1) if position_match else ""

            # Nettoyer duration (enlever position)
            duration_clean = re.sub(r'\s*\([^)]*\)', '', duration).strip()

            # Ajuster puissance si HT (sauf échauffement/récup qui sont déjà forcés)
            power_adjusted = power
            adjustment_needed = is_home_trainer and phase.lower() not in ["echauffement", "récupération"]
            if adjustment_needed:
                power_adjusted = self._adjust_power_for_ht(power)

            interval = {
                "phase": phase,
                "duration": duration_clean,
                "cadence_rpm": cadence,
                "cadence_upload_to_garmin": True,
                "power_watts": power_adjusted,
                "power_watts_original": power if adjustment_needed else None,
                "power_adjustment_w": "+15W (HT)" if adjustment_needed else None,
                "position": position
            }

            intervals.append(interval)

        return intervals

    def _is_ht_adjustment_needed(self, phase: str) -> bool:
        """
        Détermine si l'ajustement +15W HT est nécessaire

        Args:
            phase: Phase du workout

        Returns:
            True si ajustement nécessaire (ni échauffement ni récupération)
        """
        phase_lower = phase.lower()
        return phase_lower not in ["echauffement", "récupération"]

    def _adjust_power_for_ht(self, power_str: str) -> str:
        """
        Ajuste la puissance de +15W pour Home Trainer

        Args:
            power_str: Puissance (ex: "220à230")

        Returns:
            Puissance ajustée (ex: "235à245")
        """
        if 'à' in power_str:
            parts = power_str.split('à')
            try:
                low = int(parts[0].strip()) + 15
                high = int(parts[1].strip()) + 15
                return f"{low}à{high}"
            except ValueError:
                return power_str
        else:
            # Puissance simple
            try:
                power = int(power_str.strip()) + 15
                return str(power)
            except ValueError:
                return power_str

    def _parse_date(self, text: str) -> Optional[str]:
        """Parse la date (ex: 'Samedi 08/02')"""
        date_match = re.search(r'(\d{2})/(\d{2})', text)
        if date_match:
            day, month = date_match.groups()
            return f"2026-{month}-{day}"
        return None

    def _parse_duration_total(self, text: str) -> Optional[str]:
        """Parse la durée totale (ex: '1h00')"""
        duration_match = re.search(r'Durée\s*:\s*(\d+h\d+)', text)
        if duration_match:
            return duration_match.group(1)
        return None

    def _parse_description(self, text: str) -> Optional[str]:
        """Parse la description (ex: 'sur HT')"""
        desc_match = re.search(r'Séance\s+(.*?)[\n•]', text)
        if desc_match:
            return desc_match.group(1).strip()
        return None

    def _parse_notes(self, text: str) -> Optional[str]:
        """Parse les consignes"""
        notes_match = re.search(r'Consignes\s*:(.*?)(?=\n\s*\n|\Z)', text, re.DOTALL)
        if notes_match:
            return notes_match.group(1).strip()
        return None


if __name__ == '__main__':
    # Test avec C19
    pdf_path = "/Users/aptsdae/Documents/Triathlon/Séances S06 (02_02 au 08_02)_Delalain C_2026.pdf"

    with TableBasedWorkoutParser(pdf_path) as parser:
        c19 = parser.parse_cycling_workout("C19")

        print(f"📊 {c19['code']} - {c19['description']}")
        print(f"Durée: {c19['duration_total']}")
        print(f"Total intervalles: {len(c19['intervals'])}\n")

        for idx, interval in enumerate(c19['intervals'], 1):
            phase = interval['phase']
            duration = interval['duration']
            power = interval['power_watts']
            position = interval.get('position', '')
            rep_info = ""

            if 'repetition_total' in interval:
                rep_info = f" [{interval['repetition_iteration']}/{interval['repetition_total']}]"

            print(f"{idx:2d}. {phase:20s} {duration:8s} {power:12s} {position:20s} {rep_info}")
