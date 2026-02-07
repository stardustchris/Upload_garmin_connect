#!/usr/bin/env python3
"""
Garmin Automation API - Point d'entrée FastAPI

Usage:
    uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import workouts, garmin, health

app = FastAPI(
    title="Garmin Automation API",
    description="API pour automatiser l'upload/fetch de workouts Garmin Connect",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(workouts.router, prefix="/api/v1/workouts", tags=["workouts"])
app.include_router(garmin.router, prefix="/api/v1/garmin", tags=["garmin"])


@app.get("/")
async def root():
    return {
        "message": "Garmin Automation API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
