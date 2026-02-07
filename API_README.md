# Garmin Automation API

API REST pour automatiser l'upload et la récupération de workouts Garmin Connect.

## 🚀 Démarrage Rapide

```bash
# Démarrer l'API
./start_api.sh

# Ou manuellement
source venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

L'API sera disponible sur:
- **URL**: http://localhost:8000
- **Documentation interactive**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc

## 📋 Endpoints Disponibles

### Health Check
- `GET /api/v1/health` - Vérifier que l'API fonctionne

### Workouts
- `POST /api/v1/workouts/parse` - Parser un PDF d'entraînement
- `POST /api/v1/workouts/upload` - Upload workouts vers Garmin Connect
- `GET /api/v1/workouts/list` - Liste les workouts en cache

### Garmin Connect
- `GET /api/v1/garmin/activities?start_date=X&end_date=Y` - Récupérer activités
- `GET /api/v1/garmin/weight?date=X` - Récupérer poids
- `GET /api/v1/garmin/test-connection` - Tester connexion Garmin

## 🧪 Tester l'API

### Avec curl

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Lister les workouts
curl http://localhost:8000/api/v1/workouts/list | jq

# Parser un PDF
curl -X POST http://localhost:8000/api/v1/workouts/parse \
  -F "file=@/path/to/workout.pdf"
```

### Avec la documentation interactive

Ouvre http://localhost:8000/docs dans ton navigateur et teste directement les endpoints.

## 📦 Structure

```
api/
├── main.py              # Point d'entrée FastAPI
├── routes/
│   ├── health.py        # Health check
│   ├── workouts.py      # Gestion workouts
│   └── garmin.py        # Interaction Garmin Connect
├── models/              # Pydantic models (TODO)
└── services/            # Business logic (TODO)
```

## ✅ TODO

- [ ] Implémenter ParserService pour parsing PDF
- [ ] Implémenter GarminService pour interaction Garmin Connect
- [ ] Ajouter authentification (API keys)
- [ ] Implémenter upload vers Garmin
- [ ] Ajouter tests unitaires (pytest)

## 🔧 Développement

L'API utilise FastAPI avec hot-reload activé (`--reload`). Toute modification du code relancera automatiquement le serveur.

## 📝 Notes

- C19 a un bug connu: le parser ne détecte pas le corps de séance car "Corps de séance" n'est pas suivi de `:` dans le PDF
- Parser V6 fonctionne bien pour C16, C17, C18 mais manque les répétitions simples de C19
