# 🤖 Intégration Clawdbot - Process Automatisé

## 📋 Vue d'ensemble

Clawdbot gère l'ensemble du workflow hebdomadaire:

```
Email reçu → Upload Garmin immédiat → Semaine entraînement → Dimanche 22h remplissage Excel → Relecture manuelle → Envoi email
```

## 🔧 Configuration Clawdbot

### 1. Google Drive

**Dossier partagé:**
- URL: https://drive.google.com/drive/folders/1pl25O92YdeAP_v1NBVGlzwCfPtuLKg4P
- ID: `1pl25O92YdeAP_v1NBVGlzwCfPtuLKg4P`

**Fichiers stockés:**
- `Séances S0X (DD_MM au DD_MM)_Delalain C_2026.pdf`
- `S0X_carnet_entrainement.xls` → `S0X_carnet_entrainement.xlsx` (après traitement)

### 2. Règles email

**Clawdbot surveille les emails de:**
- Expéditeur: `stephane.palazzetti@*` *(à remplacer par email exact)*

**Actions automatiques:**

#### Action 1: Nouveau PDF reçu
```yaml
Détection: Pièce jointe "Séances S*.pdf"
Action:
  1. Télécharge PDF vers Google Drive
  2. Exécute: clawdbot_workflow.py --action upload_workouts
  3. Parse PDF + Upload vers Garmin Connect
  4. Notification: "✅ S0X uploadé sur Garmin"
```

#### Action 2: Fichier Excel reçu
```yaml
Détection: Pièce jointe "S*_carnet*.xls"
Action:
  1. Télécharge XLS vers Google Drive
  2. Notification: "📊 Carnet Excel reçu"
```

### 3. Tâche planifiée (Cron)

**Dimanche 22:00 - Remplissage automatique:**

```yaml
Déclencheur: Dimanche 22:00
Action:
  1. Récupère dernier XLS depuis Drive
  2. Conversion XLS → XLSX
  3. Récupère données Garmin (semaine écoulée)
  4. Rempli le XLSX automatiquement
  5. Upload XLSX vers Drive (remplace XLS)
  6. Notification: "📊 S0X prêt pour relecture"
```

### 4. Commande manuelle

**Préparation email (après relecture):**

```bash
# Dans Clawdbot, tu tapes:
!prepare-email S07

# Résultat:
# - Génère brouillon email
# - Avec pièce jointe XLSX
# - Notification pour relecture
# - Tu envoies MANUELLEMENT après vérification
```

## 🚀 Installation

### Prérequis

```bash
cd ~/Documents/Triathlon/garmin_automation
source venv/bin/activate

# Installer dépendances supplémentaires
pip install pandas openpyxl xlrd google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Configuration Google Drive API

1. **Créer credentials Google:**
   - https://console.cloud.google.com/
   - Créer projet "Garmin Automation"
   - Activer Google Drive API
   - Créer OAuth 2.0 credentials
   - Télécharger `credentials.json`

2. **Placer credentials:**
   ```bash
   mkdir -p ~/.config/clawdbot
   mv ~/Downloads/credentials.json ~/.config/clawdbot/google_credentials.json
   ```

3. **Première authentification:**
   ```bash
   python scripts/test_google_drive.py
   # Ouvre navigateur pour autoriser accès
   # Token sauvegardé dans ~/.config/clawdbot/token.json
   ```

### Intégration Clawdbot

**Copier la configuration:**

```bash
# Ajouter au fichier de config Clawdbot
cat config/clawdbot_config.yaml >> ~/.clawdbot/config.yaml
```

**Ou intégrer manuellement selon ta config Clawdbot**

## 📱 Utilisation

### Workflow automatique

#### Étape 1: Réception email (automatique)
✅ Clawdbot détecte email de Stéphane
✅ Télécharge PDF + XLS vers Drive
✅ Upload séances vers Garmin immédiatement
✅ Notification: "Semaine S0X uploadée"

#### Étape 2: Entraînements (manuel)
🏃 Tu fais tes entraînements
📊 Données enregistrées sur Garmin

#### Étape 3: Dimanche 22h (automatique)
✅ Clawdbot récupère données Garmin
✅ Convertit XLS → XLSX
✅ Rempli Excel automatiquement
✅ Upload XLSX vers Drive
✅ Notification: "Carnet S0X prêt"

#### Étape 4: Lundi matin (manuel)
📝 Tu ouvres XLSX depuis Drive
👀 Vérification/corrections
✅ Quand OK, tu tapes: `!prepare-email S07`

#### Étape 5: Envoi email (manuel)
📧 Brouillon email généré
👀 Relecture finale
📤 **Tu envoies MANUELLEMENT**

### Commandes disponibles

```bash
# Clawdbot commandes

!parse-workouts /path/to/S07.pdf  # Parse PDF -> JSON via conteneur Docker
!prepare-email S07              # Prépare email pour semaine S07
!status                         # État de l'automation
!retry-upload S07               # Réessaye upload si échec
!fetch-garmin-data S07          # Récupère données Garmin manuellement
```

## 🔍 Monitoring

### Logs

```bash
# Voir logs en temps réel
tail -f ~/Documents/Triathlon/garmin_automation/logs/clawdbot_automation.log

# Logs par semaine
ls ~/Documents/Triathlon/garmin_automation/logs/S0*
```

### Vérifications

```bash
# Vérifier upload Garmin
cat data/workouts_cache/S07_upload_result.json

# Vérifier données récupérées
cat data/workouts_cache/S07_garmin_data.json

# Vérifier brouillon email
cat data/email_drafts/S07_email_draft.json
```

## ⚠️ Gestion erreurs

### Si upload Garmin échoue
```bash
# Clawdbot notifie l'échec
# Tu peux retry manuellement:
python scripts/clawdbot_workflow.py --action upload_workouts --file "Séances S07.pdf"
```

### Si remplissage Excel échoue
```bash
# Clawdbot notifie l'échec
# Tu peux forcer manuellement:
python scripts/clawdbot_workflow.py --action fill_excel --file "S07_carnet_entrainement.xls"
```

### Si Google Drive inaccessible
```bash
# Fallback: Fichiers en local
ls ~/Documents/Triathlon/inbox/
# Traiter manuellement puis uploader vers Drive
```

## 🎯 Checklist déploiement

- [ ] Installer dépendances (pandas, openpyxl, etc.)
- [ ] Configurer Google Drive API credentials
- [ ] Tester authentification Google Drive
- [ ] Intégrer config dans Clawdbot
- [ ] Vérifier email expéditeur Stéphane
- [ ] Tester upload workouts avec S07
- [ ] Tester conversion XLS → XLSX
- [ ] Tester récupération données Garmin
- [ ] Tester remplissage Excel
- [ ] Tester préparation email
- [ ] Configurer notifications
- [ ] Documenter procédure fallback manuelle

## 📧 Structure email généré

```
De: ton_email@gmail.com
À: stephane.palazzetti@*
Objet: Carnet d'entraînement S07 - Semaine du 09/02 au 15/02
Pièce jointe: S07_carnet_entrainement.xlsx

Bonjour Stéphane,

Voici mon carnet d'entraînement pour la semaine S07 (09/02 au 15/02).

📊 Résumé de la semaine:
- Cyclisme: 3 séances | 4h30 | 120 km | FC moy: 145 bpm
- Course à pied: 3 séances | 2h15 | 22 km | Allure moy: 5:05/km
- Natation: 2 séances | 1h30 | 4000m

💪 Charge totale: 8 séances | 8h15
🎯 Respect du programme: 95%

Remarques:
[Tes notes/ajustements manuels]

Cordialement,
Christophe

---
Généré automatiquement par Garmin Automation
```

## 🔐 Sécurité

- Credentials Garmin: stockés dans keychain macOS
- Google Drive: OAuth 2.0 (token refresh automatique)
- Email: aucun password en clair
- Logs: pas de données sensibles
- Backup: chiffrement optionnel

## 💡 Améliorations futures

1. **Dashboard web** (Streamlit)
   - Vue temps réel semaine en cours
   - Graphiques progression
   - Contrôle manuel actions

2. **Analyse IA**
   - Génération notes qualitatives
   - Détection surmenage
   - Suggestions ajustements

3. **Intégration calendrier**
   - Export Google Calendar
   - Rappels séances
   - Ajustement météo

4. **Multi-format Excel**
   - Support templates différents
   - Mapping configurable
   - Validation données
