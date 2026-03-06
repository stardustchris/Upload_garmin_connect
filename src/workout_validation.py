#!/usr/bin/env python3
"""Validation helpers for parsed workouts before Garmin conversion/upload."""

from __future__ import annotations

import re
from typing import Any, Dict, List


_DURATION_RE = re.compile(r"^\d{1,2}:\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_workout_for_upload(workout: Dict[str, Any]) -> List[str]:
    """
    Returns a list of validation errors.
    Empty list means the workout is acceptable for conversion/upload.
    """
    errors: List[str] = []
    code = workout.get("code", "<unknown>")
    workout_type = workout.get("type", "")
    intervals = workout.get("intervals", [])

    if not workout.get("date") or not _DATE_RE.match(str(workout.get("date", ""))):
        errors.append(f"{code}: date manquante ou invalide ({workout.get('date')!r})")

    if workout_type in ("Cyclisme", "Course à pied") and not intervals:
        errors.append(f"{code}: aucune intervalle structurée pour un workout {workout_type}")
        return errors

    for idx, interval in enumerate(intervals, start=1):
        duration = str(interval.get("duration", "")).strip()
        if not _DURATION_RE.match(duration):
            errors.append(f"{code}: intervalle {idx} durée invalide ({duration!r})")

        if workout_type == "Cyclisme":
            power = str(interval.get("power_watts", "")).strip()
            power_values = [int(v) for v in re.findall(r"\d+", power)]
            if not power_values:
                errors.append(f"{code}: intervalle {idx} puissance invalide ({power!r})")

    return errors

