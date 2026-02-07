# Guide Upload Workout vers Garmin Connect

## 📋 Prérequis

1. **Credentials Garmin** configurés dans `.env`:
   ```
   GARMIN_EMAIL=votre_email
   GARMIN_PASSWORD=votre_password
   ```

2. **Session Garth authentifiée** (si MFA activé)

---

## 🔐 Étape 1: Authentification Garmin (Une seule fois)

### Si MFA Activé (Recommandé)

Exécuter le script d'authentification interactive:

```bash
source venv/bin/activate
python scripts/garmin_auth.py
```

Le script va:
1. Se connecter à Garmin Connect
2. **Demander le code MFA** (SMS/App Authenticator)
3. Sauvegarder les tokens dans `~/.garth/`

**Sortie attendue**:
```
🔐 Authentification Garmin Connect
📧 Email: votre_email@example.com

🔑 Connexion en cours...
💡 Si MFA activé, entrer le code à l'invite

MFA code: [ENTRER CODE ICI]

✅ Authentification réussie!
📁 Tokens sauvegardés dans /Users/xxx/.garth
💡 L'API peut maintenant se connecter sans MFA
```

### Si MFA Désactivé

L'authentification se fait automatiquement lors du premier appel API.

---

## 📤 Étape 2: Upload de C16

### Via Script de Test

```bash
source venv/bin/activate
python scripts/test_upload_c16.py
```

**Sortie attendue**:
```
🚀 Test Upload C16 vers Garmin Connect
==================================================

📂 Chargement workout depuis S06_workouts_v6_near_final.json...
✅ C16 chargé: C16 - sur HT
   Date: 2026-02-02
   Durée: 1h00
   Intervalles: 20

🔐 Connexion à Garmin Connect...
✅ Connexion réussie

📤 Upload de C16...
✅ Upload réussi!
   Workout ID: 123456789
   Workout Name: C16 - sur HT

💡 Vérifier sur Garmin Connect:
   https://connect.garmin.com/modern/workouts
```

### Via API REST

1. **Démarrer l'API**:
   ```bash
   ./start_api.sh
   ```

2. **Uploader via curl**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/workouts/upload \
     -H "Content-Type: application/json" \
     -d @data/workouts_cache/S06_workouts_v6_near_final.json
   ```

3. **Ou via documentation interactive**:
   - Ouvrir http://localhost:8000/docs
   - Endpoint: `POST /api/v1/workouts/upload`
   - Coller le JSON de C16

---

## 🧪 Vérification sur Garmin Connect

1. Se connecter sur https://connect.garmin.com
2. Aller sur **Training** → **Workouts**
3. Vérifier que C16 apparaît dans la liste

**Informations attendues**:
- **Nom**: C16 - sur HT
- **Type**: Cycling
- **Durée**: ~59 minutes
- **Steps**: 20 intervalles
- **Zones**: Puissance (watts)

---

## 🐛 Dépannage

### Erreur: "OAuth1 token is required"

**Cause**: Session garth non établie ou expirée

**Solution**:
```bash
python scripts/garmin_auth.py
# Entrer le code MFA si demandé
```

### Erreur: "Credentials Garmin manquants"

**Cause**: Fichier `.env` manquant ou mal configuré

**Solution**:
```bash
# Vérifier .env
cat .env

# Devrait contenir:
GARMIN_EMAIL=votre_email
GARMIN_PASSWORD=votre_password
```

### Erreur: "Type de workout non supporté"

**Cause**: Le workout n'est pas de type Cyclisme

**Solution**: Actuellement, seuls les workouts cyclisme sont supportés. Pour CAP/Natation, implémenter les convertisseurs correspondants.

### Workout uploadé mais pas visible

**Vérifier**:
1. **ID retourné** : L'upload a bien retourné un `workoutId` ?
2. **Compte correct** : Connecté avec le bon compte Garmin ?
3. **Cache navigateur** : Faire Ctrl+F5 pour rafraîchir

---

## 📊 Structure Workout Garmin

Le JSON envoyé à Garmin Connect a cette structure:

```json
{
  "workoutName": "C16 - sur HT",
  "estimatedDurationInSecs": 3540,
  "sportType": {
    "sportTypeId": 2,
    "sportTypeKey": "cycling"
  },
  "workoutSegments": [
    {
      "segmentOrder": 1,
      "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
      "workoutSteps": [
        {
          "type": "ExecutableStepDTO",
          "stepOrder": 1,
          "stepType": {"stepTypeId": 1, "stepTypeKey": "warmup"},
          "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
          "endConditionValue": 150.0,
          "targetType": {"workoutTargetTypeId": 5, "workoutTargetTypeKey": "power.zone"},
          "targetValueOne": 96.0,
          "targetValueTwo": 106.0
        }
        // ... 19 autres steps
      ]
    }
  ]
}
```

**Correspondance Step Types**:
- `stepTypeId: 1` → Warmup (Échauffement)
- `stepTypeId: 3` → Interval (Corps de séance)
- `stepTypeId: 4` → Rest (Récupération entre intervalles)
- `stepTypeId: 5` → Cooldown (Retour au calme)

**Target Types**:
- `workoutTargetTypeId: 5` → Power (Puissance en watts)
- `workoutTargetTypeId: 1` → Heart Rate
- `workoutTargetTypeId: 3` → Speed
- `workoutTargetTypeId: 6` → Cadence

---

## 🔄 Workflow Complet

```
1. Parser PDF → JSON
   └─ python src/pdf_parser_v3.py

2. Convertir JSON → Format Garmin
   └─ src/garmin_workout_converter.py

3. Uploader vers Garmin Connect
   └─ GarminService.upload_workout()
       └─ client.upload_workout(garmin_json)

4. Vérifier sur Garmin Connect Web
   └─ https://connect.garmin.com/modern/workouts
```

---

## 💡 Prochaines Étapes

1. ✅ Upload Cyclisme (C16, C17, C18, C19)
2. ⏳ Implémenter convertisseur Course à Pied (CAP)
3. ⏳ Implémenter convertisseur Natation (N)
4. ⏳ Programmer workouts à des dates spécifiques
5. ⏳ API endpoint pour batch upload (toute la semaine S06)
