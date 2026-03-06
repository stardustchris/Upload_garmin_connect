#!/usr/bin/env python3
"""Regression checks for S09/S10 parsing and Garmin conversion."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.garmin_workout_converter import (
    convert_to_garmin_cycling_workout,
    convert_to_garmin_running_workout,
)
from src.pdf_parser_v3 import TriathlonPDFParserV3
from src.workout_validation import validate_workout_for_upload


PDFS = [
    Path("/Users/aptsdae/Downloads/Séances S09 (23_02 au 01_03)_Delalain C_2026.pdf"),
    Path("/Users/aptsdae/Downloads/Séances S10 (02_03 au 08_03)_Delalain C_2026.pdf"),
]


@unittest.skipUnless(all(p.exists() for p in PDFS), "S09/S10 PDFs not available locally")
class TestS09S10Regression(unittest.TestCase):
    def test_parse_and_convert_without_errors(self) -> None:
        for pdf in PDFS:
            with self.subTest(pdf=pdf.name):
                with TriathlonPDFParserV3(str(pdf)) as parser:
                    result = parser.parse()

                workouts = result.get("workouts", [])
                self.assertEqual(9, len(workouts), f"Unexpected workout count for {pdf.name}")

                for workout in workouts:
                    code = workout.get("code")
                    workout_type = workout.get("type")
                    intervals = workout.get("intervals", [])

                    # Structured workouts must keep clean MM:SS durations.
                    for idx, interval in enumerate(intervals, start=1):
                        duration = str(interval.get("duration", ""))
                        self.assertRegex(
                            duration,
                            r"^\d{1,2}:\d{2}$",
                            f"{code} interval {idx} invalid duration: {duration!r}",
                        )

                    if workout_type == "Cyclisme" and intervals:
                        self.assertEqual([], validate_workout_for_upload(workout), f"Validation failed for {code}")
                        garmin = convert_to_garmin_cycling_workout(workout)
                        self.assertTrue(
                            garmin["workoutSegments"][0]["workoutSteps"],
                            f"Empty Garmin steps for {code}",
                        )
                    elif workout_type == "Course à pied" and intervals:
                        self.assertEqual([], validate_workout_for_upload(workout), f"Validation failed for {code}")
                        garmin = convert_to_garmin_running_workout(workout)
                        self.assertTrue(
                            garmin["workoutSegments"][0]["workoutSteps"],
                            f"Empty Garmin steps for {code}",
                        )
                    elif workout_type == "Course à pied" and not intervals:
                        # FARTLEK workouts are intentionally unstructured.
                        self.assertEqual("FARTLEK", workout.get("workout_type"), f"{code} should be FARTLEK")


if __name__ == "__main__":
    unittest.main()
