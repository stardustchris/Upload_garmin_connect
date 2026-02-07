"""Workout management endpoints"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
import json

router = APIRouter()


@router.post("/parse")
async def parse_pdf(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Parse un PDF d'entraînement et retourne les workouts en JSON

    Args:
        file: PDF file to parse

    Returns:
        JSON with workouts data
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        # Lire le contenu du PDF
        pdf_content = await file.read()

        # TODO: Implémenter parser
        # from api.services.parser_service import ParserService
        # parser_service = ParserService()
        # workouts = parser_service.parse_pdf_bytes(pdf_content)

        return {
            "status": "success",
            "message": "Parser not yet implemented",
            "filename": file.filename,
            "size": len(pdf_content)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_workouts(workouts_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upload workouts vers Garmin Connect

    Args:
        workouts_data: JSON containing workouts to upload

    Returns:
        Upload results
    """
    try:
        # TODO: Implémenter upload Garmin
        # from api.services.garmin_service import GarminService
        # garmin_service = GarminService()
        # result = garmin_service.upload_workouts(workouts_data)

        return {
            "status": "success",
            "message": "Upload not yet implemented",
            "workouts_count": len(workouts_data.get("workouts", []))
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_workouts() -> Dict[str, Any]:
    """
    Liste tous les workouts en cache

    Returns:
        List of cached workouts
    """
    try:
        # Lire le fichier cache V6
        with open('/Users/aptsdae/Documents/Triathlon/garmin_automation/data/workouts_cache/S06_workouts_v6_near_final.json', 'r') as f:
            data = json.load(f)

        return {
            "status": "success",
            "week": data['week'],
            "period": data.get('period'),
            "workouts_count": len(data['workouts']),
            "workouts": data['workouts']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
