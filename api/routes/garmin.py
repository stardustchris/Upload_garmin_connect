"""Garmin Connect interaction endpoints"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime
from api.services.garmin_service import GarminService

router = APIRouter()

# Instance du service Garmin (singleton)
garmin_service = None


def get_garmin_service() -> GarminService:
    """Retourne l'instance du service Garmin (singleton)"""
    global garmin_service
    if garmin_service is None:
        garmin_service = GarminService()
    return garmin_service


@router.get("/activities")
async def get_activities(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Récupère les activités depuis Garmin Connect

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum number of activities

    Returns:
        List of activities
    """
    try:
        service = get_garmin_service()
        activities = service.get_activities(start_date, end_date, limit)

        return {
            "status": "success",
            "start_date": start_date,
            "end_date": end_date,
            "count": len(activities),
            "activities": activities
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weight")
async def get_weight(date: Optional[str] = None) -> Dict[str, Any]:
    """
    Récupère le poids pour une date donnée

    Args:
        date: Date (YYYY-MM-DD), defaults to today

    Returns:
        Weight data
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        service = get_garmin_service()
        weight_kg = service.get_weight(date)

        if weight_kg is not None:
            return {
                "status": "success",
                "date": date,
                "weight_kg": weight_kg
            }
        else:
            return {
                "status": "success",
                "date": date,
                "weight_kg": None,
                "message": "Aucune donnée de poids pour cette date"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-connection")
async def test_garmin_connection() -> Dict[str, Any]:
    """
    Teste la connexion à Garmin Connect

    Returns:
        Connection status
    """
    try:
        service = get_garmin_service()
        result = service.test_connection()

        if result["connected"]:
            return {
                "status": "success",
                **result
            }
        else:
            return {
                "status": "error",
                **result
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
