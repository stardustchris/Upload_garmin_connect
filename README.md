# Automatisation Garmin Connect pour Triathlon

Système automatisé pour parser les PDFs d'entraînement (format Delalain), uploader les séances planifiées sur Garmin Connect, récupérer les données d'activités réalisées, et remplir automatiquement les fichiers Excel de suivi.

## 🎯 Fonctionnalités

- ✅ **Parser PDF** : Extraction des séances de cyclisme, course à pied et natation depuis PDF entraîneur
- ✅ **Upload Garmin** : Conversion JSON → YAML et upload vers Garmin Connect via garmin-workouts
- 🚧 **Fetch Garmin** : Récupération activités, poids, sommeil depuis Garmin Connect
- 🚧 **Remplissage Excel** : Population automatique des templates de suivi hebdomadaire
- 🚧 **Automatisation** : Exécution automatique via launchd (macOS, lundi 6h00)

## 📦 Installation

### 1. Créer un environnement virtuel Python

```bash
cd /Users/aptsdae/Documents/Triathlon/garmin_automation
python3 -m venv venv
source venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Installer garmin-workouts (optionnel, pour upload)

```bash
pip install git+https://github.com/mkuthan/garmin-workouts.git
```

## 🚀 Utilisation

### Parser un PDF d'entraînement

```bash
source venv/bin/activate
python3 src/pdf_parser_v3.py "Séances S06 (02_02 au 08_02)_Delalain C_2026.pdf" > data/workouts_cache/S06_workouts.json
```

### Uploader vers Garmin Connect

```bash
source venv/bin/activate
python3 src/garmin_uploader.py data/workouts_cache/S06_workouts.json
```

**Note** : L'upload nécessite l'authentification Garmin Connect. Au premier lancement, garmin-workouts demandera vos identifiants.

### Récupérer données Garmin (TODO)

```bash
source venv/bin/activate
python3 src/garmin_fetcher.py --week 2026-02-02
```

### Remplir Excel (TODO)

```bash
source venv/bin/activate
python3 src/excel_writer.py --input data/garmin_fetch_S06.json --template "S06_Delalain C_2026.xlsx"
```

## 📋 Structure du Projet

```
garmin_automation/
├── src/
│   ├── pdf_parser_v3.py       # Parser PDF → JSON ✅
│   ├── garmin_uploader.py     # Upload workouts → Garmin Connect ✅
│   ├── garmin_fetcher.py      # Fetch Garmin data → JSON 🚧
│   ├── excel_writer.py        # Write JSON → Excel 🚧
│   └── main.py                # Orchestrateur principal 🚧
├── data/
│   ├── workouts_cache/        # Cache JSON des workouts parsés
│   ├── yaml_includes/         # Includes YAML pour HT warmup/cooldown
│   └── logs/                  # Logs d'exécution
├── config/
│   ├── settings.yaml          # Configuration générale 🚧
│   └── .env                   # Variables d'environnement (gitignored) 🚧
├── requirements.txt           # Dépendances Python
├── venv/                      # Environnement virtuel Python
└── README.md                  # Ce fichier
```

## ⚙️ Configuration

### Règles Home Trainer (HT)

Le parser applique automatiquement les règles Home Trainer pour les séances indoor :

**Échauffement HT (TOUJOURS forcé)** :
- Bloc 1/4 : 2:30 @ 96-106W
- Bloc 2/4 : 2:30 @ 130-136W
- Bloc 3/4 : 5:00 @ 156-166W
- Bloc 4/4 : 5:00 @ 180-190W

**Corps de séance HT** :
- Ajout de +15W à TOUTES les zones de puissance
- Exemple : 130-140W (PDF) → 145-155W (Garmin)

**Récupération HT (TOUJOURS forcée)** :
- Bloc 1/2 : 2:00 @ 175-180W
- Bloc 2/2 : 2:00 @ 175-180W

**Cadence** :
- Gardée dans JSON pour référence
- **NE PAS uploader vers Garmin** (seules les zones de puissance)
- Récupérée depuis Garmin lors du fetch (cadence réelle)

## 🔧 Approche Hybride : Parser + Claude Code/Cowork

Le parser automatique gère la majorité des structures standard, mais pour les séances complexes ou nouvelles (répétitions imbriquées, blocs décomposés, etc.), utilisez **Claude Code** ou **Claude Cowork** pour :

1. **Assistance au parsing** : Identifier et extraire les structures complexes
2. **Validation** : Vérifier que le nombre d'intervalles correspond à la structure réelle
3. **Correction manuelle** : Ajuster les JSON pour les cas edge non couverts par le parser

**Workflow hebdomadaire avec Claude Code** :
1. Parser le nouveau PDF S0X automatiquement
2. Demander à Claude Code de valider les workouts complexes (C16, C17, C18...)
3. Claude Code corrige/améliore le JSON si nécessaire
4. Upload vers Garmin Connect
5. Fetch des données réalisées
6. Remplissage Excel

## 📊 Format JSON des Workouts

### Cyclisme (avec répétitions)

```json
{
  "code": "C17",
  "type": "Cyclisme",
  "indoor": true,
  "intervals": [
    {
      "phase": "Echauffement",
      "duration": "2:30",
      "power_watts": "96à106",
      "forced_reason": "Échauffement HT standard bloc 1/4"
    },
    {
      "phase": "Corps de séance",
      "duration": "03:00",
      "power_watts": "235à245",
      "power_adjustment_w": 15,
      "repetition_iteration": 1,
      "repetition_total": 3,
      "position": "Position haute"
    }
  ]
}
```

### Course à pied

```json
{
  "code": "CAP17",
  "type": "Course à pied",
  "workout_type": "STRUCTURED",
  "intervals": [
    {
      "phase": "Echauffement",
      "pace_description": "Allure faible à modérée",
      "duration": "20:00"
    },
    {
      "phase": "Corps de séance",
      "pace_min_per_km": "4:35à4:40",
      "duration": "10:00"
    }
  ]
}
```

### FARTLEK (séance libre)

```json
{
  "code": "CAP16",
  "type": "Course à pied",
  "workout_type": "FARTLEK",
  "structured": false,
  "duration_total": "0h45",
  "intervals": []
}
```

## 🔐 Authentification Garmin

**Premier lancement** : garmin-workouts demandera vos identifiants Garmin Connect.

**MFA activé** : L'outil utilise `garth` qui gère OAuth1/OAuth2 et stocke les tokens dans `~/.garth/` (durée ~1 an).

**Pas de ré-authentification** nécessaire pour les exécutions automatiques ultérieures (tant que les tokens sont valides).

## 🤖 Automatisation via launchd (macOS)

**TODO** : Configuration à venir pour exécution automatique tous les lundis à 6h00.

Fichier : `~/Library/LaunchAgents/com.triathlon.garmin.plist`

## 📝 Logs

Les logs d'exécution sont stockés dans `data/logs/` :
- `garmin_automation.log` : Log principal
- `stdout.log` : Sortie standard (launchd)
- `stderr.log` : Erreurs (launchd)

## 🛠️ Développement

### Activer l'environnement virtuel

```bash
source venv/bin/activate
```

### Tests manuels

```bash
# Parser
python3 src/pdf_parser_v3.py "<PDF_PATH>"

# Uploader (dry-run avec affichage YAML)
python3 -c "
from src.garmin_uploader import GarminWorkoutUploader
import json, yaml

with open('data/workouts_cache/S06_workouts.json') as f:
    data = json.load(f)

uploader = GarminWorkoutUploader()
c16 = [w for w in data['workouts'] if w['code'] == 'C16'][0]
yaml_c16 = uploader.convert_cycling_to_yaml(c16)
print(yaml.dump(yaml_c16, default_flow_style=False, allow_unicode=True))
"
```

## ❓ FAQ

**Q : Pourquoi la cadence n'est-elle pas uploadée vers Garmin ?**  
R : L'utilisateur souhaite que Garmin se concentre uniquement sur les zones de puissance. La cadence est indicative mais ne doit pas être imposée comme contrainte lors de l'entraînement.

**Q : Pourquoi +15W sur le corps de séance ?**  
R : Compensation entre puissance théorique (PDF coach) et puissance réelle nécessaire pour atteindre l'effet d'entraînement souhaité.

**Q : Comment gérer les nouvelles structures de séances ?**  
R : Utiliser Claude Code ou Claude Cowork pour assister le parsing des structures non couvertes par le parser automatique.

## 📚 Ressources

- [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) : API Garmin Connect
- [garmin-workouts](https://github.com/mkuthan/garmin-workouts) : Upload workouts via YAML
- [pdfplumber](https://github.com/jsvine/pdfplumber) : Extraction PDF
- [openpyxl](https://openpyxl.readthedocs.io/) : Manipulation Excel

## 📄 Licence

Projet personnel - Tous droits réservés
