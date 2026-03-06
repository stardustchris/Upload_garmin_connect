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
        {"duration": "2:30", "power": "95à100"},
        {"duration": "2:30", "power": "125à130"},
        {"duration": "5:00", "power": "155à160"},
        {"duration": "5:00", "power": "185à190"}
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
                    phase,
                    is_home_trainer
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
        phase: str,
        is_home_trainer: bool
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

        duration_lines = [line.strip() for line in durations_str.split('\n') if line.strip()]
        cadence_lines = [line.strip() for line in cadences_str.split('\n') if line.strip()]
        power_lines = [line.strip() for line in powers_str.split('\n') if line.strip()]

        c_idx = 0
        d_idx = 0

        while d_idx < len(duration_lines):
            line = duration_lines[d_idx]
            rep_match = re.match(r'(\d+)\s*x\s*\(([^)]+)\)\s*(?:\([^)]*\))?.*', line)

            if rep_match:
                repeat_count = int(rep_match.group(1))
                pattern_tokens = [t.strip() for t in rep_match.group(2).split('-') if t.strip()]
                pattern_intervals = []
                d_idx += 1

                for token in pattern_tokens:
                    token_duration = self._extract_duration_mmss(token)
                    if not token_duration:
                        continue

                    token_position = ""
                    if d_idx < len(duration_lines):
                        header_line = duration_lines[d_idx]
                        if token in header_line and 'décomposées en' in header_line:
                            pos_match = re.search(r'\(([^)]*Position[^)]*)\)', header_line)
                            token_position = pos_match.group(1) if pos_match else ""
                            d_idx += 1

                    if '*' in token:
                        target_secs = self._duration_to_seconds(token_duration)
                        consumed_secs = 0
                        while d_idx < len(duration_lines) and consumed_secs < target_secs and c_idx < len(cadence_lines):
                            sub_line = duration_lines[d_idx]
                            if re.match(r'(\d+)\s*x\s*\(', sub_line):
                                break
                            sub_dur = self._extract_duration_mmss(sub_line)
                            if not sub_dur:
                                d_idx += 1
                                continue

                            pos_match = re.search(r'\(([^)]*Position[^)]*)\)', sub_line)
                            sub_position = pos_match.group(1) if pos_match else token_position

                            power_raw = power_lines[c_idx] if c_idx < len(power_lines) else "0à0"
                            adjust = is_home_trainer and self._is_ht_adjustment_needed(phase)
                            power_adj = self._adjust_power_for_ht(power_raw) if adjust else power_raw

                            pattern_intervals.append({
                                "phase": phase,
                                "duration": sub_dur,
                                "cadence_rpm": cadence_lines[c_idx],
                                "cadence_upload_to_garmin": True,
                                "power_watts": power_adj,
                                "power_watts_original": power_raw if adjust else None,
                                "power_adjustment_w": "+15W (HT)" if adjust else None,
                                "position": sub_position
                            })

                            consumed_secs += self._duration_to_seconds(sub_dur)
                            c_idx += 1
                            d_idx += 1
                    else:
                        selected_line = token_duration
                        if d_idx < len(duration_lines):
                            candidate = self._extract_duration_mmss(duration_lines[d_idx])
                            if candidate == token_duration:
                                selected_line = duration_lines[d_idx]
                                d_idx += 1

                        if c_idx < len(cadence_lines):
                            pos_match = re.search(r'\(([^)]*Position[^)]*)\)', str(selected_line))
                            position = pos_match.group(1) if pos_match else token_position
                            power_raw = power_lines[c_idx] if c_idx < len(power_lines) else "0à0"
                            adjust = is_home_trainer and self._is_ht_adjustment_needed(phase)
                            power_adj = self._adjust_power_for_ht(power_raw) if adjust else power_raw

                            pattern_intervals.append({
                                "phase": phase,
                                "duration": token_duration,
                                "cadence_rpm": cadence_lines[c_idx],
                                "cadence_upload_to_garmin": True,
                                "power_watts": power_adj,
                                "power_watts_original": power_raw if adjust else None,
                                "power_adjustment_w": "+15W (HT)" if adjust else None,
                                "position": position
                            })
                            c_idx += 1

                for iteration in range(repeat_count):
                    for interval in pattern_intervals:
                        interval_copy = interval.copy()
                        interval_copy["repetition_iteration"] = iteration + 1
                        interval_copy["repetition_total"] = repeat_count
                        intervals.append(interval_copy)
                continue

            if 'décomposées en' in line:
                d_idx += 1
                continue

            duration_clean = self._extract_duration_mmss(line)
            if duration_clean and c_idx < len(cadence_lines):
                pos_match = re.search(r'\(([^)]*Position[^)]*)\)', line)
                position = pos_match.group(1) if pos_match else ""
                power_raw = power_lines[c_idx] if c_idx < len(power_lines) else "0à0"
                adjust = is_home_trainer and self._is_ht_adjustment_needed(phase)
                power_adj = self._adjust_power_for_ht(power_raw) if adjust else power_raw

                intervals.append({
                    "phase": phase,
                    "duration": duration_clean,
                    "cadence_rpm": cadence_lines[c_idx],
                    "cadence_upload_to_garmin": True,
                    "power_watts": power_adj,
                    "power_watts_original": power_raw if adjust else None,
                    "power_adjustment_w": "+15W (HT)" if adjust else None,
                    "position": position
                })
                c_idx += 1

            d_idx += 1

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
            duration_clean = self._extract_duration_mmss(duration_clean)
            if not duration_clean:
                continue

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

    def _extract_duration_mmss(self, text: str) -> Optional[str]:
        """
        Extrait un token de durée MM:SS depuis une cellule potentiellement bruitée.

        Exemples:
        - "08:00* décomposées en :" -> "08:00"
        - "REPETITIONS 1,3 : POSITION AERO." -> None
        """
        if not text:
            return None
        match = re.search(r'(\d{1,2}:\d{2})', text)
        if not match:
            return None
        return match.group(1)

    def _duration_to_seconds(self, duration_mmss: str) -> int:
        """Convertit MM:SS en secondes."""
        mm, ss = duration_mmss.split(":")
        return int(mm) * 60 + int(ss)

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
