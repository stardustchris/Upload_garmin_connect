#!/usr/bin/env python3
"""
Parser PDF d'entraînements Triathlon (format Delalain) - Version 3 (Corrections complètes)

CORRECTIONS MAJEURES V3:
1. Cadence cyclisme : gardée dans JSON mais NOT upload to Garmin
2. Puissance +15W pour Corps de séance uniquement
3. Parsing C16 corrigé (répétitions imbriquées, blocs décomposés)
4. Détection FARTLEK (CAP16) - séance libre
5. Phases CAP corrigées (échauffement = allure faible, corps = allures chiffrées)
6. Format allures CAP validé (mm:ssàmm:ss)
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pdfplumber


class TriathlonPDFParserV3:
    """Parser PDF d'entraînements avec corrections complètes"""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.pdf = None

    def __enter__(self):
        self.pdf = pdfplumber.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pdf:
            self.pdf.close()

    # ============================================================================
    # UTILITAIRES GÉNÉRAUX
    # ============================================================================

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

    def parse_date_from_text(self, text: str, year: int = 2026) -> Optional[str]:
        """Parse la date depuis le texte (ex: 'Lundi 02/02')"""
        date_match = re.search(r'(\d{2})/(\d{2})', text)
        if date_match:
            day, month = date_match.groups()
            return f"{year}-{month}-{day}"
        return None

    def find_workout_sections(self) -> List[Tuple[str, str, str]]:
        """
        Identifie toutes les sections de workout dans le PDF

        Returns:
            List de (code_workout, workout_type, full_text)
        """
        sections = []
        all_text = ""

        # Extraire tout le texte
        for page in self.pdf.pages:
            all_text += page.extract_text() + "\n\n"

        # Patterns pour identifier les débuts de séances détaillées
        workout_patterns = [
            (r'(C\d+)\s*\([^)]*le matin\)', 'cycling'),
            (r'(CAP\d+)\s*\([^)]*le matin\)', 'running'),
            (r'(N\d+)\s*\([^)]*\)', 'swimming')
        ]

        # Collecter toutes les positions de début de workout
        all_workout_positions = []
        for pattern, workout_type in workout_patterns:
            for match in re.finditer(pattern, all_text):
                code = match.group(1)
                start_idx = match.start()
                all_workout_positions.append((start_idx, code, workout_type))

        # Trier par position
        all_workout_positions.sort(key=lambda x: x[0])

        # Extraire chaque section jusqu'au prochain workout
        for i, (start_idx, code, workout_type) in enumerate(all_workout_positions):
            # Trouver la fin : prochain workout ou fin du texte
            if i + 1 < len(all_workout_positions):
                end_idx = all_workout_positions[i + 1][0]
            else:
                end_idx = len(all_text)

            section_text = all_text[start_idx:end_idx]
            sections.append((code, workout_type, section_text))

        return sections

    # ============================================================================
    # UTILITAIRES PUISSANCE CYCLISME (CORRECTION +15W)
    # ============================================================================

    # Constantes pour échauffement Home Trainer standard
    HT_WARMUP_STANDARD = [
        {"duration": "2:30", "power": "96à106"},
        {"duration": "2:30", "power": "130à136"},
        {"duration": "5:00", "power": "156à166"},
        {"duration": "5:00", "power": "180à190"}
    ]

    def adjust_power_for_garmin(self, power_str: str, phase: str, is_home_trainer: bool = False, warmup_index: int = None) -> dict:
        """
        Ajuste les zones de puissance selon les règles spécifiques

        Args:
            power_str: "130à140" ou "130 à 140 W"
            phase: "Echauffement", "Corps de séance", "Récupération"
            is_home_trainer: True si séance HT (Home Trainer)
            warmup_index: Index de l'intervalle d'échauffement (0-3) si applicable

        Returns:
            {
                "original": "130à140",
                "adjusted": "145à155" (si corps de séance) ou forcé selon règles,
                "adjustment": 15 ou 0 ou "forced",
                "forced_reason": optionnel
            }

        Règles Home Trainer (OPTION A) :
        - Échauffement : TOUJOURS forcer à la séquence standard (96-106, 130-136, 156-166, 180-190)
        - Corps de séance : +15W
        - Récupération : TOUJOURS forcer à 175à180
        """
        # Extraire min et max
        match = re.search(r'(\d+)\s*à\s*(\d+)', power_str)
        if not match:
            return {"original": power_str, "adjusted": power_str, "adjustment": 0}

        min_power = int(match.group(1))
        max_power = int(match.group(2))
        original = f"{min_power}à{max_power}"

        # RÈGLE 1 : Échauffement sur Home Trainer → TOUJOURS séquence standard
        if is_home_trainer and ("échauffement" in phase.lower() or "echauffement" in phase.lower()):
            # Si warmup_index fourni, utiliser les valeurs standard
            if warmup_index is not None and 0 <= warmup_index < len(self.HT_WARMUP_STANDARD):
                forced_power = self.HT_WARMUP_STANDARD[warmup_index]["power"]
                return {
                    "original": original,
                    "adjusted": forced_power,
                    "adjustment": "forced",
                    "forced_reason": f"Échauffement HT bloc {warmup_index + 1}/4 toujours {forced_power}W"
                }
            # Sinon, utiliser la première valeur par défaut
            forced_power = self.HT_WARMUP_STANDARD[0]["power"]
            return {
                "original": original,
                "adjusted": forced_power,
                "adjustment": "forced",
                "forced_reason": "Échauffement HT toujours selon séquence standard"
            }

        # RÈGLE 2 : Récupération sur Home Trainer → TOUJOURS 175à180
        if is_home_trainer and "récupération" in phase.lower():
            return {
                "original": original,
                "adjusted": "175à180",
                "adjustment": "forced",
                "forced_reason": "Récupération HT toujours 175-180W"
            }

        # RÈGLE 3 : Corps de séance → +15W
        if "corps de séance" in phase.lower():
            min_power += 15
            max_power += 15
            return {
                "original": original,
                "adjusted": f"{min_power}à{max_power}",
                "adjustment": 15
            }

        # RÈGLE 4 : Autres cas → Inchangé
        return {
            "original": original,
            "adjusted": original,
            "adjustment": 0
        }

    # ============================================================================
    # UTILITAIRES COURSE À PIED
    # ============================================================================

    def detect_running_phase(self, line: str) -> Optional[str]:
        """
        Détecte la phase d'un intervalle de course

        Règles :
        - "Allure faible à modérée" ou "Echauffement" → Echauffement
        - Format "X:XXàX:XX" (allure chiffrée) → Corps de séance
        - "Allure modérée à faible" ou "Récupération" → Récupération
        """
        if "Echauffement" in line:
            return "Echauffement"
        elif "Corps de séance" in line:
            return "Corps de séance"
        elif "Récupération" in line or "Récupération" in line:
            return "Récupération"
        elif "Allure faible" in line and "modérée" in line:
            return "Echauffement"
        elif "Allure modérée" in line and "faible" in line:
            return "Récupération"
        elif re.search(r'\d:\d{2}\s*à\s*\d:\d{2}', line):
            # Allure chiffrée = Corps de séance
            return "Corps de séance"

        return None

    def parse_pace(self, pace_str: str) -> dict:
        """
        Parse et valide format allure mm:ssàmm:ss

        Args:
            pace_str: "4:45à4:50" (minutes:secondes par km)

        Returns:
            {
                "raw": "4:45à4:50",
                "min_pace_sec_per_km": 285,
                "max_pace_sec_per_km": 290,
                "min_formatted": "4:45",
                "max_formatted": "4:50"
            }

        Raises:
            ValueError si format invalide ou secondes > 59
        """
        match = re.search(r'(\d):(\d{2})\s*à\s*(\d):(\d{2})', pace_str)
        if not match:
            raise ValueError(f"Format allure invalide : {pace_str}")

        min_min, min_sec = int(match.group(1)), int(match.group(2))
        max_min, max_sec = int(match.group(3)), int(match.group(4))

        # Validation secondes
        if min_sec > 59 or max_sec > 59:
            raise ValueError(f"Secondes invalides (>59) : {pace_str}")

        return {
            "raw": pace_str,
            "min_pace_sec_per_km": min_min * 60 + min_sec,
            "max_pace_sec_per_km": max_min * 60 + max_sec,
            "min_formatted": f"{min_min}:{min_sec:02d}",
            "max_formatted": f"{max_min}:{max_sec:02d}"
        }

    # ============================================================================
    # PARSING CYCLISME - GESTION RÉPÉTITIONS ET BLOCS DÉCOMPOSÉS
    # ============================================================================

    def detect_repetition_pattern(self, text: str) -> Optional[Tuple[int, str, int, int]]:
        """
        Détecte un pattern de répétition "X x (...) :"

        Args:
            text: Texte à analyser

        Returns:
            Tuple (repeat_count, pattern_matched, start_pos, end_pos) ou None
            Exemple: "3 x (04:00*-02:00-04:00**-02:00) :" → (3, "04:00*-02:00-04:00**-02:00", ...)
        """
        pattern = r'(\d+)\s*x\s*\(([\d:*-]+)\)\s*:'
        match = re.search(pattern, text)

        if match:
            repeat_count = int(match.group(1))
            pattern_matched = match.group(2)
            start_pos = match.start()
            end_pos = match.end()

            return (repeat_count, pattern_matched, start_pos, end_pos)

        return None

    def detect_decomposed_block(self, text: str) -> Optional[Tuple[str, str, int, int]]:
        """
        Détecte un bloc décomposé "08:00* (Position haute) décomposées en :"

        Args:
            text: Texte à analyser

        Returns:
            Tuple (duration, position, start_pos, end_pos) ou None
            Exemple: "08:00* (Position haute) décomposées en :" → ("08:00", "Position haute", ...)
        """
        pattern = r'(\d{2}:\d{2}[*]*)\s*\(([^)]+)\)\s*décomposées en\s*:'
        match = re.search(pattern, text)

        if match:
            duration = match.group(1).replace('*', '')
            position = match.group(2)
            start_pos = match.start()
            end_pos = match.end()

            return (duration, position, start_pos, end_pos)

        return None

    def parse_decomposed_sub_intervals(self, text: str, parent_position: str, is_home_trainer: bool, current_phase: str) -> List[Dict]:
        """
        Parse les sous-intervalles d'un bloc décomposé

        Args:
            text: Texte contenant les sous-intervalles
            parent_position: Position héritée du bloc parent (ex: "Position haute")
            is_home_trainer: True si séance HT
            current_phase: Phase actuelle (généralement "Corps de séance")

        Returns:
            Liste des sous-intervalles parsés
        """
        sub_intervals = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()

            # Parser format : durée | cadence | puissance
            # Exemple: "03:00 70 à 75 220 à 230"
            interval_match = re.search(
                r'(\d{1,2}:\d{2})\s+(\d+\s*à\s*\d+)\s+(\d+\s*à\s*\d+)',
                line
            )

            if interval_match:
                duration = interval_match.group(1)
                cadence = interval_match.group(2).replace(' ', '')
                power = interval_match.group(3).replace(' ', '')

                # Appliquer ajustements selon phase
                power_data = self.adjust_power_for_garmin(
                    power,
                    current_phase,
                    is_home_trainer
                )

                sub_interval = {
                    "phase": current_phase,
                    "duration": duration,
                    "cadence_rpm": cadence,
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": power_data["original"],
                    "power_watts": power_data["adjusted"],
                    "power_adjustment_w": power_data["adjustment"],
                    "position": parent_position,
                    "is_sub_interval": True
                }

                if "forced_reason" in power_data:
                    sub_interval["forced_reason"] = power_data["forced_reason"]

                sub_intervals.append(sub_interval)

        return sub_intervals

    # ============================================================================
    # PARSING CYCLISME (AVEC CORRECTION C16)
    # ============================================================================

    def parse_cycling_workout(self, code: str, text: str) -> Dict:
        """Parse une séance de cyclisme avec extraction correcte"""

        workout = {
            "code": code,
            "date": self.parse_date_from_text(text),
            "type": "Cyclisme",
            "indoor": "HT" in text or "home trainer" in text.lower(),
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

        # Parser les intervalles depuis le TEXTE COMPLET (pas juste le tableau)
        # Cela permet de détecter les répétitions et blocs décomposés
        table_section = re.search(
            r'Répartition de la séance\s*:(.*?)(?=Consignes|Récupération\s+\d|$)',
            text,
            re.DOTALL
        )

        if table_section:
            table_text = table_section.group(0)
            intervals = self._parse_cycling_full_text(table_text, workout["indoor"])
            workout["intervals"] = intervals

        # Extraire les notes
        notes_match = re.search(r'Consignes\s*:(.*?)(?=\n\s*\n|\Z)', text, re.DOTALL)
        if notes_match:
            workout["notes"] = notes_match.group(1).strip()

        return workout

    def _parse_cycling_full_text(self, text: str, is_home_trainer: bool) -> List[Dict]:
        """
        Parse le texte complet d'une séance cyclisme avec détection avancée

        Cette fonction remplace _parse_cycling_table_v3_with_ht_rules
        et gère les répétitions et blocs décomposés depuis le texte brut
        """
        intervals = []

        # RÈGLE HT : Forcer échauffement standard
        if is_home_trainer:
            for idx, warmup_block in enumerate(self.HT_WARMUP_STANDARD):
                intervals.append({
                    "phase": "Echauffement",
                    "duration": warmup_block["duration"],
                    "cadence_rpm": "libre",
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": "standard HT",
                    "power_watts": warmup_block["power"],
                    "power_adjustment_w": "forced",
                    "forced_reason": f"Échauffement HT standard bloc {idx + 1}/4"
                })

        # Détecter répétitions PARTOUT dans le texte (pas seulement après "Corps de séance")
        repetition_pattern = r'(\d+)\s*x\s*\(([^)]+)\)\s*:'
        rep_match = re.search(repetition_pattern, text)

        if rep_match:
            # Il y a des répétitions - parser toute la section autour
            # Extraire depuis le début de la répétition jusqu'à "Récupération"
            rep_start = rep_match.start()

            # Trouver le début du corps de séance (juste avant la répétition)
            # Remonter pour trouver les blocs avant
            before_text = text[:rep_start]

            # Extraire jusqu'à Récupération
            after_match = re.search(r'(.*?)Récupération', text[rep_start:], re.DOTALL)
            if after_match:
                corps_full_text = before_text[before_text.rfind('Echauffement'):] + text[rep_start:rep_start+after_match.end(1)]
            else:
                corps_full_text = before_text + text[rep_start:]
        else:
            # Pas de répétitions - chercher section normale
            corps_section_match = re.search(r'Corps de séance(.*?)Récupération', text, re.DOTALL)
            if corps_section_match:
                corps_full_text = corps_section_match.group(1)
            else:
                corps_full_text = None

        if corps_full_text:

            # Détecter si il y a des répétitions
            repetition_pattern = r'(\d+)\s*x\s*\(([^)]+)\)\s*:'
            rep_match = re.search(repetition_pattern, corps_full_text)

            if rep_match:
                repeat_count = int(rep_match.group(1))
                repeat_start_pos = rep_match.start()
                repeat_content_start = rep_match.end()

                # # print(f"DEBUG: Détecté {repeat_count} répétitions à position {repeat_start_pos}")

                # BLOCS AVANT LA RÉPÉTITION (peuvent être décomposés !)
                before_repeat_text = corps_full_text[:repeat_start_pos]
                # # print(f"DEBUG: Texte avant répétition (premiers 200 car): {before_repeat_text[:200]}")

                before_intervals = self._parse_mixed_intervals(
                    before_repeat_text,
                    "Corps de séance",
                    is_home_trainer
                )
                intervals.extend(before_intervals)
                # print(f"DEBUG: {len(before_intervals)} intervalles avant répétition")

                # BLOCS DE LA RÉPÉTITION
                # Trouver où se termine le contenu de répétition
                # Chercher le prochain bloc non-indenté avec durée (ex: "08:00***")
                remaining_text = corps_full_text[repeat_content_start:]

                # Trouver la fin de la répétition (prochain bloc avec * sans "décomposées en")
                end_repeat_match = re.search(r'\n(\d{2}:\d{2}[*]{3,})', remaining_text)

                if end_repeat_match:
                    repeat_content_end = end_repeat_match.start()
                    repeat_content = remaining_text[:repeat_content_end]
                    after_repeat_text = remaining_text[repeat_content_end:]
                else:
                    repeat_content = remaining_text
                    after_repeat_text = ""

                # Parser le contenu de la répétition
                repeat_intervals_single = self._parse_repeat_block_content(
                    repeat_content,
                    "Corps de séance",
                    is_home_trainer
                )

                # print(f"DEBUG: {len(repeat_intervals_single)} intervalles dans une itération")

                # Répéter X fois
                for iteration in range(repeat_count):
                    for interval in repeat_intervals_single:
                        interval_copy = interval.copy()
                        interval_copy["repetition_iteration"] = iteration + 1
                        interval_copy["repetition_total"] = repeat_count
                        intervals.append(interval_copy)

                # BLOCS APRÈS LA RÉPÉTITION (peuvent être décomposés !)
                if after_repeat_text:
                    # print(f"DEBUG: Texte après répétition (premiers 200 car): {after_repeat_text[:200]}")
                    after_intervals = self._parse_mixed_intervals(
                        after_repeat_text,
                        "Corps de séance",
                        is_home_trainer
                    )
                    intervals.extend(after_intervals)
                    # print(f"DEBUG: {len(after_intervals)} intervalles après répétition")

            else:
                # Pas de répétitions, parser normalement
                simple_intervals = self._parse_simple_intervals(
                    corps_full_text,
                    "Corps de séance",
                    is_home_trainer
                )
                intervals.extend(simple_intervals)

        # RÈGLE HT : Forcer récupération standard
        if is_home_trainer:
            intervals.append({
                "phase": "Récupération",
                "duration": "2:00",
                "cadence_rpm": "libre",
                "cadence_upload_to_garmin": False,
                "power_watts_original": "standard HT",
                "power_watts": "175à180",
                "power_adjustment_w": "forced",
                "forced_reason": "Récupération HT standard bloc 1/2"
            })
            intervals.append({
                "phase": "Récupération",
                "duration": "2:00",
                "cadence_rpm": "libre",
                "cadence_upload_to_garmin": False,
                "power_watts_original": "standard HT",
                "power_watts": "175à180",
                "power_adjustment_w": "forced",
                "forced_reason": "Récupération HT standard bloc 2/2"
            })

        return intervals

    def _parse_simple_intervals(self, text: str, phase: str, is_home_trainer: bool) -> List[Dict]:
        """
        Parse des intervalles simples (non-décomposés) du corps de séance

        Format attendu : "08:00* (Position aéro.) 80 à 85 200 à 210"
        """
        intervals = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()

            # Pattern : durée* (Position) cadence puissance
            match = re.search(
                r'(\d{2}:\d{2})[*]*\s*\(([^)]+)\)\s+(\d+\s*à\s*\d+)\s+(\d+\s*à\s*\d+)',
                line
            )

            if match:
                duration = match.group(1)
                position = match.group(2)
                cadence = match.group(3).replace(' ', '')
                power = match.group(4).replace(' ', '')

                power_data = self.adjust_power_for_garmin(power, phase, is_home_trainer)

                intervals.append({
                    "phase": phase,
                    "duration": duration,
                    "cadence_rpm": cadence,
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": power_data["original"],
                    "power_watts": power_data["adjusted"],
                    "power_adjustment_w": power_data["adjustment"],
                    "position": position
                })

        return intervals

    def _parse_mixed_intervals(self, text: str, phase: str, is_home_trainer: bool) -> List[Dict]:
        """
        Parse des intervalles qui peuvent être simples OU décomposés

        Gère :
        - "08:00* (Position) X à Y Z à W" → intervalle simple
        - "08:00* (Position) décomposées en :" → bloc décomposé avec sub-intervalles
        """
        intervals = []
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Détecter bloc décomposé
            decomposed_match = re.search(
                r'(\d{2}:\d{2})[*]*\s*\(([^)]+)\)\s*décomposées en\s*:',
                line
            )

            if decomposed_match:
                position = decomposed_match.group(2)

                # Parser sous-intervalles (lignes suivantes)
                i += 1
                while i < len(lines):
                    sub_line = lines[i].strip()

                    # Arrêter si nouvelle section
                    if 'décomposées en' in sub_line or ('(' in sub_line and 'Position' in sub_line):
                        break

                    # Parser sub-intervalle : durée cadence puissance
                    sub_match = re.search(
                        r'(\d{1,2}:\d{2})\s+(\d+\s*à\s*\d+)\s+(\d+\s*à\s*\d+)',
                        sub_line
                    )

                    if sub_match:
                        duration = sub_match.group(1)
                        cadence = sub_match.group(2).replace(' ', '')
                        power = sub_match.group(3).replace(' ', '')

                        power_data = self.adjust_power_for_garmin(power, phase, is_home_trainer)

                        intervals.append({
                            "phase": phase,
                            "duration": duration,
                            "cadence_rpm": cadence,
                            "cadence_upload_to_garmin": False,
                            "power_watts_original": power_data["original"],
                            "power_watts": power_data["adjusted"],
                            "power_adjustment_w": power_data["adjustment"],
                            "position": position,
                            "is_sub_interval": True
                        })

                    i += 1
                continue

            # Parser intervalle simple : durée* (Position) cadence puissance
            simple_match = re.search(
                r'(\d{2}:\d{2})[*]*\s*\(([^)]+)\)\s+(\d+\s*à\s*\d+)\s+(\d+\s*à\s*\d+)',
                line
            )

            if simple_match:
                duration = simple_match.group(1)
                position = simple_match.group(2)
                cadence = simple_match.group(3).replace(' ', '')
                power = simple_match.group(4).replace(' ', '')

                power_data = self.adjust_power_for_garmin(power, phase, is_home_trainer)

                intervals.append({
                    "phase": phase,
                    "duration": duration,
                    "cadence_rpm": cadence,
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": power_data["original"],
                    "power_watts": power_data["adjusted"],
                    "power_adjustment_w": power_data["adjustment"],
                    "position": position
                })

            i += 1

        return intervals

    def _parse_repeat_block_content(self, text: str, phase: str, is_home_trainer: bool) -> List[Dict]:
        """
        Parse le contenu d'un bloc de répétition (blocs décomposés)

        Exemple de texte :
        ```
        04:00* (Position haute) décomposées en :
        03:00 70 à 75 220 à 230
        01:00 90 à 95 260 à 270
        02:00 (Position aéro.) 80 à 85 160 à 170
        04:00** (Position haute) décomposées en :
        ...
        ```
        """
        intervals = []
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Détecter bloc décomposé
            decomposed_match = re.search(
                r'(\d{2}:\d{2})[*]*\s*\(([^)]+)\)\s*décomposées en\s*:',
                line
            )

            if decomposed_match:
                position = decomposed_match.group(2)

                # Parser les sous-intervalles (lignes suivantes)
                i += 1
                while i < len(lines):
                    sub_line = lines[i].strip()

                    # Arrêter si nouvelle section
                    if 'décomposées en' in sub_line or '(Position' in sub_line:
                        break

                    # Parser intervalle : durée cadence puissance
                    interval_match = re.search(
                        r'(\d{1,2}:\d{2})\s+(\d+\s*à\s*\d+)\s+(\d+\s*à\s*\d+)',
                        sub_line
                    )

                    if interval_match:
                        duration = interval_match.group(1)
                        cadence = interval_match.group(2).replace(' ', '')
                        power = interval_match.group(3).replace(' ', '')

                        # Appliquer +15W
                        power_data = self.adjust_power_for_garmin(power, phase, is_home_trainer)

                        intervals.append({
                            "phase": phase,
                            "duration": duration,
                            "cadence_rpm": cadence,
                            "cadence_upload_to_garmin": False,
                            "power_watts_original": power_data["original"],
                            "power_watts": power_data["adjusted"],
                            "power_adjustment_w": power_data["adjustment"],
                            "position": position,
                            "is_sub_interval": True
                        })

                    i += 1
                continue

            # Parser intervalle simple (pas décomposé)
            interval_match = re.search(
                r'(\d{1,2}:\d{2})\s+\(([^)]+)\)\s+(\d+\s*à\s*\d+)\s+(\d+\s*à\s*\d+)',
                line
            )

            if interval_match:
                duration = interval_match.group(1)
                position = interval_match.group(2)
                cadence = interval_match.group(3).replace(' ', '')
                power = interval_match.group(4).replace(' ', '')

                power_data = self.adjust_power_for_garmin(power, phase, is_home_trainer)

                intervals.append({
                    "phase": phase,
                    "duration": duration,
                    "cadence_rpm": cadence,
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": power_data["original"],
                    "power_watts": power_data["adjusted"],
                    "power_adjustment_w": power_data["adjustment"],
                    "position": position
                })

            i += 1

        return intervals

    def _parse_cycling_table_v3_with_ht_rules(self, table_text: str, is_home_trainer: bool) -> List[Dict]:
        """
        Parse avec règles Home Trainer appliquées + gestion répétitions et blocs décomposés

        RÈGLES :
        1. Si HT, REMPLACER l'échauffement par la séquence standard
        2. Détecter répétitions "X x (...) :"
        3. Détecter blocs décomposés "décomposées en :"
        4. Appliquer +15W aux corps de séance
        5. Forcer récupération HT à 175-180W
        """
        intervals = []
        current_phase = 'Echauffement'

        # Si Home Trainer : ajouter IMMÉDIATEMENT les 4 blocs d'échauffement standard
        if is_home_trainer:
            for idx, warmup_block in enumerate(self.HT_WARMUP_STANDARD):
                intervals.append({
                    "phase": "Echauffement",
                    "duration": warmup_block["duration"],
                    "cadence_rpm": "libre",
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": "standard HT",
                    "power_watts": warmup_block["power"],
                    "power_adjustment_w": "forced",
                    "forced_reason": f"Échauffement HT standard bloc {idx + 1}/4"
                })

        lines = table_text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Identifier le changement de phase
            if 'Echauffement' in line or 'Échauffement' in line:
                current_phase = 'Echauffement'
                i += 1
                continue
            elif 'Corps de séance' in line:
                current_phase = 'Corps de séance'
                i += 1
                continue
            elif 'Récupération' in line:
                current_phase = 'Récupération'
                i += 1
                continue

            # IGNORER les blocs d'échauffement du PDF si Home Trainer (déjà ajoutés)
            if current_phase == 'Echauffement' and is_home_trainer:
                i += 1
                continue

            # DÉTECTER RÉPÉTITIONS : "X x (...) :"
            repetition_info = self.detect_repetition_pattern(line)
            if repetition_info:
                repeat_count, pattern, start_pos, end_pos = repetition_info

                # Extraire le contenu à répéter (lignes suivantes jusqu'au prochain bloc non-décomposé)
                repeat_content_lines = []
                j = i + 1

                # Collecter les lignes qui font partie de la répétition
                # On s'arrête quand on trouve un nouveau bloc principal (sans indent ou nouvelle phase)
                while j < len(lines):
                    next_line = lines[j].strip()

                    # Arrêter si on trouve une nouvelle phase
                    if 'Récupération' in next_line or 'Echauffement' in next_line:
                        break

                    # Arrêter si on trouve un bloc qui n'est PAS indenté et n'est pas décomposé
                    if next_line and not next_line.startswith(' ') and 'décomposées en' not in next_line:
                        # Vérifier si c'est un nouveau bloc principal (durée au début de ligne)
                        if re.match(r'^\d{2}:\d{2}[*]*\s', next_line):
                            break

                    repeat_content_lines.append(lines[j])
                    j += 1

                repeat_content = '\n'.join(repeat_content_lines)

                # Parser le contenu à répéter UNE FOIS
                single_iteration_intervals = self._parse_repeat_content(
                    repeat_content,
                    current_phase,
                    is_home_trainer
                )

                # Répéter X fois
                for iteration in range(repeat_count):
                    for interval in single_iteration_intervals:
                        # Copier l'intervalle et ajouter metadata de répétition
                        interval_copy = interval.copy()
                        interval_copy["repetition_iteration"] = iteration + 1
                        interval_copy["repetition_total"] = repeat_count
                        intervals.append(interval_copy)

                # Sauter les lignes déjà traitées
                i = j
                continue

            # DÉTECTER BLOCS DÉCOMPOSÉS : "08:00* (Position haute) décomposées en :"
            decomposed_info = self.detect_decomposed_block(line)
            if decomposed_info:
                duration, position, start_pos, end_pos = decomposed_info

                # Extraire les sous-intervalles (lignes suivantes indentées)
                sub_content_lines = []
                j = i + 1

                while j < len(lines):
                    next_line = lines[j]

                    # Arrêter si on trouve une ligne non-indentée (nouveau bloc principal)
                    if next_line and not next_line.startswith(' ') and next_line.strip():
                        # Sauf si c'est encore un sous-intervalle (vérifier format durée|cadence|power)
                        if not re.search(r'^\s*\d{1,2}:\d{2}\s+\d+\s*à', next_line):
                            break

                    sub_content_lines.append(next_line)
                    j += 1

                sub_content = '\n'.join(sub_content_lines)

                # Parser les sous-intervalles
                sub_intervals = self.parse_decomposed_sub_intervals(
                    sub_content,
                    position,
                    is_home_trainer,
                    current_phase
                )

                intervals.extend(sub_intervals)

                # Sauter les lignes déjà traitées
                i = j
                continue

            # PARSER INTERVALLES SIMPLES : durée | cadence | puissance
            interval_match = re.search(
                r'(\d{1,2}:\d{2})\s+(\d+\s*à\s*\d+)\s+(\d+\s*à\s*\d+)',
                line
            )

            if interval_match:
                duration = interval_match.group(1)
                cadence = interval_match.group(2).replace(' ', '')
                power = interval_match.group(3).replace(' ', '')

                # Chercher position
                position = None
                if 'Position aéro' in line or 'aéro.' in line:
                    position = 'Position aéro'
                elif 'Position haute' in line:
                    position = 'Position haute'

                # Appliquer ajustements selon phase
                power_data = self.adjust_power_for_garmin(
                    power,
                    current_phase,
                    is_home_trainer
                )

                interval = {
                    "phase": current_phase,
                    "duration": duration,
                    "cadence_rpm": cadence,
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": power_data["original"],
                    "power_watts": power_data["adjusted"],
                    "power_adjustment_w": power_data["adjustment"]
                }

                if "forced_reason" in power_data:
                    interval["forced_reason"] = power_data["forced_reason"]

                if position:
                    interval["position"] = position

                intervals.append(interval)

            i += 1

        # FORCER RÉCUPÉRATION HT : Remplacer tous les intervalles de récupération par 2 blocs @ 175-180W
        if is_home_trainer:
            # Filtrer les intervalles de récupération
            non_recovery_intervals = [iv for iv in intervals if iv["phase"] != "Récupération"]

            # Ajouter 2 blocs de récupération HT standard
            recovery_intervals = [
                {
                    "phase": "Récupération",
                    "duration": "2:00",
                    "cadence_rpm": "libre",
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": "standard HT",
                    "power_watts": "175à180",
                    "power_adjustment_w": "forced",
                    "forced_reason": "Récupération HT standard bloc 1/2"
                },
                {
                    "phase": "Récupération",
                    "duration": "2:00",
                    "cadence_rpm": "libre",
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": "standard HT",
                    "power_watts": "175à180",
                    "power_adjustment_w": "forced",
                    "forced_reason": "Récupération HT standard bloc 2/2"
                }
            ]

            # Reconstruire la liste : non-récup + récup forcée
            intervals = non_recovery_intervals + recovery_intervals

        return intervals

    def _parse_repeat_content(self, content: str, current_phase: str, is_home_trainer: bool) -> List[Dict]:
        """
        Parse le contenu d'un bloc de répétition UNE FOIS

        Args:
            content: Texte contenant les intervalles à répéter
            current_phase: Phase actuelle
            is_home_trainer: True si HT

        Returns:
            Liste des intervalles pour UNE itération
        """
        intervals = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # DÉTECTER BLOCS DÉCOMPOSÉS dans le contenu de répétition
            decomposed_info = self.detect_decomposed_block(line)
            if decomposed_info:
                duration, position, start_pos, end_pos = decomposed_info

                # Extraire sous-intervalles
                sub_content_lines = []
                j = i + 1

                while j < len(lines):
                    next_line = lines[j]

                    if next_line and not next_line.startswith(' ') and next_line.strip():
                        if not re.search(r'^\s*\d{1,2}:\d{2}\s+\d+\s*à', next_line):
                            break

                    sub_content_lines.append(next_line)
                    j += 1

                sub_content = '\n'.join(sub_content_lines)

                # Parser les sous-intervalles
                sub_intervals = self.parse_decomposed_sub_intervals(
                    sub_content,
                    position,
                    is_home_trainer,
                    current_phase
                )

                intervals.extend(sub_intervals)
                i = j
                continue

            # PARSER INTERVALLE SIMPLE
            interval_match = re.search(
                r'(\d{1,2}:\d{2})\s+(\d+\s*à\s*\d+)\s+(\d+\s*à\s*\d+)',
                line
            )

            if interval_match:
                duration = interval_match.group(1)
                cadence = interval_match.group(2).replace(' ', '')
                power = interval_match.group(3).replace(' ', '')

                # Chercher position
                position = None
                if 'Position aéro' in line or 'aéro.' in line:
                    position = 'Position aéro'
                elif 'Position haute' in line:
                    position = 'Position haute'

                # Appliquer ajustements
                power_data = self.adjust_power_for_garmin(
                    power,
                    current_phase,
                    is_home_trainer
                )

                interval = {
                    "phase": current_phase,
                    "duration": duration,
                    "cadence_rpm": cadence,
                    "cadence_upload_to_garmin": False,
                    "power_watts_original": power_data["original"],
                    "power_watts": power_data["adjusted"],
                    "power_adjustment_w": power_data["adjustment"]
                }

                if "forced_reason" in power_data:
                    interval["forced_reason"] = power_data["forced_reason"]

                if position:
                    interval["position"] = position

                intervals.append(interval)

            i += 1

        return intervals

    # ============================================================================
    # PARSING COURSE À PIED (AVEC CORRECTION FARTLEK + PHASES)
    # ============================================================================

    def parse_running_workout(self, code: str, text: str) -> Dict:
        """Parse une séance de course à pied avec détection FARTLEK"""

        workout = {
            "code": code,
            "date": self.parse_date_from_text(text),
            "type": "Course à pied",
            "duration_total": None,
            "notes": None
        }

        # Extraire la durée
        duration_match = re.search(r'Durée\s*:\s*(\d+h\d+)', text)
        if duration_match:
            workout["duration_total"] = duration_match.group(1)

        # DÉTECTION FARTLEK
        if "FARTLEK" in text.upper() or "aux sensations" in text.lower():
            workout.update({
                "workout_type": "FARTLEK",
                "structured": False,
                "description": "FARTLEK NATUREL - Séance libre aux sensations",
                "intervals": []
            })

            # Extraire les notes
            notes_match = re.search(r'Indications\s*:(.*?)(?=\n\s*\n|\Z)', text, re.DOTALL)
            if notes_match:
                workout["notes"] = notes_match.group(1).strip()

            return workout

        # Sinon, parsing structuré
        workout["workout_type"] = "STRUCTURED"
        workout["structured"] = True

        # Parser le tableau
        table_section = re.search(
            r'Répartition de la séance\s*:.*?Indications',
            text,
            re.DOTALL
        )

        if table_section:
            table_text = table_section.group(0)
            intervals = self._parse_running_table_v3(table_text)
            workout["intervals"] = intervals
        else:
            workout["intervals"] = []

        # Extraire les notes
        notes_match = re.search(r'Indications\s*:(.*?)(?=\n\s*\n|\Z)', text, re.DOTALL)
        if notes_match:
            workout["notes"] = notes_match.group(1).strip()

        return workout

    def _parse_running_table_v3(self, table_text: str) -> List[Dict]:
        """
        Parse le tableau d'intervalles de CAP avec phases corrigées

        Règles :
        - Echauffement = UNIQUEMENT "Allure faible à modérée"
        - Corps de séance = Allures chiffrées (4:45à4:50)
        - Récupération = "Allure modérée à faible"
        """
        intervals = []
        current_phase = None

        lines = table_text.split('\n')

        for line in lines:
            line = line.strip()

            # Détecter phase depuis le label de ligne
            phase_detected = self.detect_running_phase(line)
            if phase_detected:
                current_phase = phase_detected

            # Parser allures chiffrées : X:XXàX:XX
            pace_match = re.search(r'(\d:\d{2}\s*à\s*\d:\d{2})', line)
            duration_match = re.search(r'(\d{1,2}:\d{2})(?!\s*à)', line)

            if pace_match and duration_match and current_phase:
                pace_str = pace_match.group(1).replace(' ', '')

                try:
                    pace_parsed = self.parse_pace(pace_str)

                    interval = {
                        "phase": current_phase,
                        "pace_min_per_km": pace_str,
                        "pace_parsed": pace_parsed,
                        "duration": duration_match.group(1)
                    }

                    intervals.append(interval)
                except ValueError as e:
                    # Allure invalide, ignorer
                    print(f"Warning: {e}")

            # Parser allures textuelles (échauffement/récup)
            elif ("Allure faible" in line or "Allure modérée" in line) and duration_match:
                pace_description = None
                if "faible à modérée" in line:
                    pace_description = "Allure faible à modérée"
                    if current_phase is None:
                        current_phase = "Echauffement"
                elif "modérée à faible" in line:
                    pace_description = "Allure modérée à faible"
                    if current_phase is None:
                        current_phase = "Récupération"

                if pace_description and current_phase:
                    interval = {
                        "phase": current_phase,
                        "pace_description": pace_description,
                        "duration": duration_match.group(1)
                    }
                    intervals.append(interval)

        return intervals

    # ============================================================================
    # PARSING NATATION (INCHANGÉ)
    # ============================================================================

    def parse_swimming_workout(self, code: str, text: str) -> Dict:
        """Parse une séance de natation"""

        workout = {
            "code": code,
            "date": self.parse_date_from_text(text),
            "type": "Natation",
            "duration_total": None,
            "series": [],
            "distances": {},
            "notes": None
        }

        # Extraire durée totale en mètres
        distance_match = re.search(r'(\d{4})m', text)
        if distance_match:
            workout["duration_total"] = distance_match.group(1) + "m"

        # Parsing des séries (simplifié pour l'instant)
        series_patterns = [
            r'(\d+\s*x\s*\d+.*?)(?=\n\d+\s*x|\nR\d+|\n\n|$)',
            r'(\d+\s+\w+.*?)(?=\n\d+|\nR\d+|\n\n|$)'
        ]

        for pattern in series_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                description = match.group(1).strip()

                serie = {
                    "description": description,
                    "technique": "TECHNIQUEMENT APPLIQUE" if "TECHNIQUE" in text else None
                }

                workout["series"].append(serie)

        return workout

    # ============================================================================
    # FONCTION PRINCIPALE DE PARSING
    # ============================================================================

    def parse(self) -> Dict:
        """Parse le PDF complet et retourne la structure JSON"""

        week_info = self.extract_week_info()
        workouts = []

        # Trouver toutes les sections de workouts
        sections = self.find_workout_sections()

        for code, workout_type, text in sections:
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

            except Exception as e:
                print(f"Error parsing {code}: {e}")
                continue

        result = {
            **week_info,
            "workouts": workouts
        }

        return result


# ============================================================================
# FONCTION STANDALONE
# ============================================================================

def parse_pdf(pdf_path: str) -> Dict:
    """Parse un PDF d'entraînement et retourne le JSON structuré"""
    with TriathlonPDFParserV3(pdf_path) as parser:
        return parser.parse()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_parser_v3.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    result = parse_pdf(pdf_path)

    # Afficher JSON
    print(json.dumps(result, indent=2, ensure_ascii=False))
