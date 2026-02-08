"""
Garmin Connect Service - Interaction avec Garmin Connect via python-garminconnect

Basé sur: https://github.com/cyberjunky/python-garminconnect
Version: 0.2.38 (dernière release au 2026-01-04)
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectConnectionError
from dotenv import load_dotenv
import logging

# Charger variables d'environnement
load_dotenv()

logger = logging.getLogger(__name__)

# Chemin pour stocker les tokens garth
GARTH_DIR = Path.home() / ".garth"


class GarminService:
    """Service pour interagir avec Garmin Connect"""

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialise le service Garmin

        Args:
            email: Email Garmin (ou depuis .env GARMIN_EMAIL)
            password: Password Garmin (ou depuis .env GARMIN_PASSWORD)
        """
        self.email = email or os.getenv('GARMIN_EMAIL')
        self.password = password or os.getenv('GARMIN_PASSWORD')

        if not self.email or not self.password:
            raise ValueError("Credentials Garmin manquants. Définir GARMIN_EMAIL et GARMIN_PASSWORD dans .env")

        self.client: Optional[Garmin] = None
        self._is_authenticated = False

    def connect(self) -> bool:
        """
        Se connecte à Garmin Connect avec gestion tokens garth

        Returns:
            True si connexion réussie

        Raises:
            GarminConnectAuthenticationError: Si credentials invalides
            GarminConnectConnectionError: Si problème de connexion
        """
        try:
            logger.info(f"Connexion à Garmin Connect avec {self.email}...")

            # Approche 1 : Essayer de charger session garth existante
            if GARTH_DIR.exists():
                try:
                    # Créer client Garmin et charger la session depuis ~/.garth
                    self.client = Garmin()
                    self.client.login(str(GARTH_DIR))
                    self._is_authenticated = True
                    logger.info("✅ Connexion Garmin réussie (session garth)")
                    return True
                except Exception as e:
                    logger.warning(f"Session garth invalide: {e}, tentative connexion directe...")

            # Approche 2 : Connexion directe avec credentials (peut nécessiter MFA manuel)
            self.client = Garmin(self.email, self.password)
            self.client.login()

            # Sauvegarder la session pour utilisation future
            if not GARTH_DIR.exists():
                GARTH_DIR.mkdir(parents=True, exist_ok=True)
            self.client.garth.dump(str(GARTH_DIR))

            self._is_authenticated = True
            logger.info("✅ Connexion Garmin réussie")

            return True

        except GarminConnectAuthenticationError as e:
            logger.error(f"❌ Authentification Garmin échouée: {e}")
            logger.error("💡 Si MFA activé, exécuter script d'auth initial : python scripts/garmin_auth.py")
            raise
        except GarminConnectConnectionError as e:
            logger.error(f"❌ Erreur de connexion Garmin: {e}")
            raise

    def test_connection(self) -> Dict[str, Any]:
        """
        Teste la connexion Garmin et retourne les infos utilisateur

        Returns:
            Dict avec user info et statut connexion
        """
        try:
            if not self._is_authenticated:
                self.connect()

            # Récupérer les infos utilisateur pour tester
            user_info = self.client.get_full_name()

            return {
                "connected": True,
                "user_name": user_info,
                "message": "Connexion Garmin OK"
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "message": "Connexion Garmin échouée"
            }

    def get_activities(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Récupère les activités Garmin

        Args:
            start_date: Date début (YYYY-MM-DD), défaut: aujourd'hui - 7 jours
            end_date: Date fin (YYYY-MM-DD), défaut: aujourd'hui
            limit: Nombre max d'activités

        Returns:
            Liste des activités
        """
        if not self._is_authenticated:
            self.connect()

        # Dates par défaut
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_delta = datetime.now() - timedelta(days=7)
            start_date = start_delta.strftime('%Y-%m-%d')

        try:
            activities = self.client.get_activities(0, limit)

            # Filtrer par dates
            filtered = []
            for activity in activities:
                activity_date = activity.get('startTimeLocal', '')[:10]
                if start_date <= activity_date <= end_date:
                    filtered.append(activity)

            logger.info(f"✅ {len(filtered)} activités récupérées ({start_date} à {end_date})")
            return filtered

        except Exception as e:
            logger.error(f"❌ Erreur récupération activités: {e}")
            raise

    def get_weight(self, date: Optional[str] = None) -> Optional[float]:
        """
        Récupère le poids pour une date

        Args:
            date: Date (YYYY-MM-DD), défaut: aujourd'hui

        Returns:
            Poids en kg ou None
        """
        if not self._is_authenticated:
            self.connect()

        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        try:
            # get_daily_weigh_ins retourne les pesées du jour
            weight_data = self.client.get_daily_weigh_ins(date)

            if weight_data and 'dateWeightList' in weight_data and len(weight_data['dateWeightList']) > 0:
                # Prendre la dernière pesée du jour
                latest = weight_data['dateWeightList'][-1]
                weight_g = latest.get('weight', 0)
                weight_kg = weight_g / 1000.0  # Garmin retourne en grammes
                logger.info(f"✅ Poids récupéré: {weight_kg:.1f} kg pour {date}")
                return weight_kg

            return None

        except Exception as e:
            logger.error(f"❌ Erreur récupération poids: {e}")
            return None

    def get_sleep(self, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Récupère les données de sommeil

        Args:
            date: Date (YYYY-MM-DD), défaut: aujourd'hui

        Returns:
            Dict avec heures et qualité de sommeil
        """
        if not self._is_authenticated:
            self.connect()

        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        try:
            sleep_data = self.client.get_sleep_data(date)

            if sleep_data and 'dailySleepDTO' in sleep_data:
                daily = sleep_data['dailySleepDTO']

                # Extraire durée et qualité
                duration_seconds = daily.get('sleepTimeSeconds', 0)
                duration_hours = duration_seconds / 3600.0

                # Score de qualité depuis sleepScores si disponible
                quality_score = 0
                if 'sleepScores' in sleep_data:
                    quality_score = sleep_data['sleepScores'].get('overall', {}).get('value', 0)

                return {
                    "date": date,
                    "duration_hours": round(duration_hours, 1),
                    "quality_score": quality_score,
                    "deep_sleep_seconds": daily.get('deepSleepSeconds', 0),
                    "light_sleep_seconds": daily.get('lightSleepSeconds', 0),
                    "rem_sleep_seconds": daily.get('remSleepSeconds', 0)
                }

            return None

        except Exception as e:
            logger.error(f"❌ Erreur récupération sommeil: {e}")
            return None

    def upload_workout(self, workout_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload un workout vers Garmin Connect

        Args:
            workout_json: Structure JSON du workout (format parsé)

        Returns:
            Réponse Garmin avec workout ID

        Raises:
            ValueError: Si type de workout non supporté
        """
        if not self._is_authenticated:
            self.connect()

        try:
            # Convertir JSON → format Garmin
            from src.garmin_workout_converter import (
                convert_to_garmin_cycling_workout,
                convert_to_garmin_running_workout
            )

            workout_type = workout_json.get('type', '').lower()

            if 'cyclisme' in workout_type or 'cycling' in workout_type:
                garmin_workout = convert_to_garmin_cycling_workout(workout_json)
                logger.info(f"📤 Upload workout {workout_json['code']} vers Garmin...")
                result = self.client.upload_workout(garmin_workout)
                logger.info(f"✅ Workout uploadé: ID {result.get('workoutId', 'unknown')}")
                return result
            elif 'course à pied' in workout_type or 'running' in workout_type:
                garmin_workout = convert_to_garmin_running_workout(workout_json)
                logger.info(f"📤 Upload workout {workout_json['code']} vers Garmin...")
                result = self.client.upload_workout(garmin_workout)
                logger.info(f"✅ Workout uploadé: ID {result.get('workoutId', 'unknown')}")
                return result
            else:
                raise ValueError(f"Type de workout non supporté: {workout_type}")

        except Exception as e:
            logger.error(f"❌ Erreur upload workout: {e}")
            raise
