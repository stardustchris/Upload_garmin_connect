# Status Session - 2026-02-08

## ✅ OBJECTIFS ATTEINTS

### 1. Authentification Garmin Connect avec MFA - RÉUSSI
**Problème** : L'utilisateur ne recevait pas les codes MFA par email/SMS

**Solution** :
- Utilisé le script `garmin_auth_file_mfa.py` qui lit le code MFA depuis un fichier temporaire
- Code MFA sauvegardé dans `/tmp/garmin_mfa_code.txt`
- Authentification réussie, tokens OAuth sauvegardés dans `~/.garth/`

**Résultat** :
```
✅ Tokens sauvegardés dans ~/.garth/
- oauth1_token.json : Token OAuth1 avec expiration MFA 2027-02-08
- oauth2_token.json : Token OAuth2 pour API calls
```

**Validité** : Tokens valides pendant ~1 an sans redemander MFA

---

### 2. Upload C16 vers Garmin Connect - RÉUSSI
**Action** : Test d'upload du workout C16 parsé depuis le PDF

**Mise à jour bibliothèque** :
- `garminconnect` : 0.2.23 → 0.2.38
- `garth` : 0.6.3 → 0.5.21
- Ajout du module `workout.py` avec modèles Pydantic `CyclingWorkout`

**Première tentative** :
- Workout ID : `1467524585`
- ❌ Problème : Zones affichées en km/h au lieu de watts
- Cause : `workoutTargetTypeId: 5` (SPEED) au lieu de `2` (POWER)

**Correction** :
- Analyse d'un workout existant (C15) pour identifier le bon targetTypeId
- Correction dans `src/garmin_workout_converter.py` : `workoutTargetTypeId: 5 → 2`

**Deuxième tentative** :
- Workout ID : `1467527604`
- ✅ Zones correctement affichées en **Watts**
- URL : https://connect.garmin.com/modern/workout/1467527604?workoutType=cycling

**Vérification** :
```
✅ C16 - sur HT
   Durée : 59:00
   Intervalles : 20

Échauffement (4 steps) :
- 2:30 → 96-106 Watts
- 2:30 → 130-136 Watts
- 5:00 → 156-166 Watts
- 5:00 → 180-190 Watts

Corps de séance (12 steps) :
- 8:00 → 215-225 Watts (Position aéro)
- 2:00 → 175-185 Watts
- 2:00 → 215-225 Watts (Position haute)
- ... (etc.)

Récupération (4 steps)
```

---

## 🔧 MODIFICATIONS TECHNIQUES

### Fichiers Modifiés

**1. `api/services/garmin_service.py`**
- ✅ Correction méthode `connect()` : Utilisation correcte de `garth.resume()` + `garmin.login(tokenstore_path)`
- ✅ Ajout sauvegarde session après connexion directe : `garmin.garth.dump()`

**Avant** :
```python
garth.resume(str(GARTH_DIR))
garth.client.username = self.email  # ❌ Erreur : pas de setter
self.client = Garmin()
self.client.login()
```

**Après** :
```python
# Approche 1 : Charger session garth existante
self.client = Garmin()
self.client.login(str(GARTH_DIR))  # ✅ Charge tokens depuis ~/.garth

# Approche 2 : Connexion directe + sauvegarde
self.client = Garmin(self.email, self.password)
self.client.login()
self.client.garth.dump(str(GARTH_DIR))  # ✅ Sauvegarde tokens
```

**2. `src/garmin_workout_converter.py`**
- ✅ Correction `workoutTargetTypeId` : 5 (SPEED) → 2 (POWER)

**Avant** :
```python
"targetType": {
    "workoutTargetTypeId": 5,  # SPEED (affichait km/h)
    "workoutTargetTypeKey": "power.zone"
}
```

**Après** :
```python
"targetType": {
    "workoutTargetTypeId": 2,  # POWER (affiche watts ✅)
    "workoutTargetTypeKey": "power.zone"
}
```

**3. Scripts créés**
- ✅ `scripts/garmin_auth_manual_mfa.py` : Authentification avec MFA via input()
- ✅ `scripts/garmin_auth_file_mfa.py` : Authentification avec MFA via fichier temporaire
- ✅ `scripts/extract_browser_tokens.py` : Extraction manuelle tokens depuis cookies navigateur
- ✅ `scripts/garmin_auth_no_mfa.py` : Connexion sans MFA (si désactivé)

---

## 📊 Mapping Garmin Workout Target Types

### Découverte importante

**Target Type IDs (d'après analyse C15 existant)** :
- `1` : NO_TARGET
- `2` : **POWER** (watts) ✅
- `3` : CADENCE
- `4` : SPEED
- `5` : ~~POWER~~ → En réalité SPEED ! ❌

**Note** : La documentation `garminconnect/workout.py` indique `POWER = 5`, mais en réalité l'API Garmin utilise `2` pour power.

**Target Type Keys** :
- `"power.zone"` : Zones de puissance en watts
- `"speed.zone"` : Zones de vitesse en km/h
- `"no.target"` : Pas d'objectif

---

## 🐛 Bugs Résolus

### Bug 1 : Authentification Garmin échouait
**Cause** : Tentative d'utiliser `garth.resume()` puis `Garmin().login()` sans credentials
**Fix** : Utiliser `Garmin().login(tokenstore_path)` pour charger session sauvegardée

### Bug 2 : Workout affiché en km/h au lieu de watts
**Cause** : `workoutTargetTypeId: 5` correspond à SPEED, pas POWER
**Fix** : Changer `workoutTargetTypeId` à `2` pour POWER

### Bug 3 : AttributeError 'Garmin' object has no attribute 'upload_workout'
**Cause** : Version 0.2.23 de garminconnect n'avait pas la méthode
**Fix** : Mise à jour vers 0.2.38

---

## 📚 Leçons Apprises

### 1. Garth Session Management
- Les tokens sont sauvegardés dans `~/.garth/` par défaut
- `garth.resume(path)` charge les tokens
- `garmin.garth.dump(path)` sauvegarde les tokens
- Ne JAMAIS utiliser `garth.client.username = email` (pas de setter)

### 2. Python-garminconnect Version
- Version 0.2.23 : Méthode `upload_workout()` commentée
- Version 0.2.38 : Méthode active + module `workout.py` avec Pydantic

### 3. Garmin Workout API
- Les `targetTypeId` ne correspondent pas toujours à la doc
- Toujours vérifier avec un workout existant via `get_workout_by_id()`
- L'API peut transformer certains champs (ex: power.zone → speed.zone si mauvais ID)

### 4. MFA Workarounds
- Si codes MFA non reçus : utiliser fichier temporaire
- Tokens valides ~1 an → authentification MFA nécessaire seulement une fois
- Alternative : désactiver temporairement MFA pour setup initial

---

## 🎯 Prochaines Étapes

### Immédiat
1. ✅ ~~Uploader C16 avec zones correctes~~
2. ⏳ Uploader C17, C18, C19 (autres workouts cyclisme S06)
3. ⏳ Vérifier que tous s'affichent correctement

### Court Terme
1. Implémenter convertisseurs CAP (Course à pied)
2. Implémenter convertisseur Natation
3. Upload batch de toute la semaine S06
4. Programmer workouts aux dates spécifiques

### Moyen Terme
1. API endpoint `/workouts/upload-week` pour upload batch
2. Tests automatisés (pytest)
3. CI/CD avec GitHub Actions

---

## 📁 Fichiers Clés

| Fichier | Rôle | Status |
|---------|------|--------|
| `api/services/garmin_service.py` | Service Garmin Connect | ✅ Corrigé |
| `src/garmin_workout_converter.py` | Convertisseur JSON→Garmin | ✅ Corrigé |
| `scripts/test_upload_c16.py` | Script test upload | ✅ Fonctionnel |
| `scripts/garmin_auth_file_mfa.py` | Authentification MFA | ✅ Utilisé avec succès |
| `~/.garth/oauth1_token.json` | Tokens OAuth1 | ✅ Valide jusqu'en 2027 |
| `~/.garth/oauth2_token.json` | Tokens OAuth2 | ✅ Auto-renouvelé |

---

## 🔗 Liens Utiles

- **Garmin Connect Workouts** : https://connect.garmin.com/modern/workouts
- **C16 Corrigé** : https://connect.garmin.com/modern/workout/1467527604?workoutType=cycling
- **python-garminconnect Repo** : https://github.com/cyberjunky/python-garminconnect
- **API Docs** : http://localhost:8000/docs (après `./start_api.sh`)

---

## 💡 Recommandations

### Documentation
- Mettre à jour `UPLOAD_GUIDE.md` avec le bon `targetTypeId: 2` pour power
- Ajouter section troubleshooting "Zones affichées en km/h au lieu de watts"

### Code
- Créer constantes pour Target Type IDs :
  ```python
  TARGET_TYPE_NO_TARGET = 1
  TARGET_TYPE_POWER = 2  # Watts
  TARGET_TYPE_CADENCE = 3
  TARGET_TYPE_SPEED = 4
  ```

### Tests
- Ajouter test unitaire : vérifier que targetTypeId=2 pour power
- Ajouter test intégration : upload + vérification affichage watts

---

**Session terminée** : 2026-02-08 11:30
**Prochain objectif** : Upload complet S06 (C17, C18, C19, CAP, Natation)
