# 🤖 Process d'Automatisation Complet - Entraînement Triathlon

## 📊 Vue d'ensemble

Automatisation complète du flux hebdomadaire:
1. Réception des fichiers d'entraînement
2. Upload automatique vers Garmin Connect
3. Récupération des données de la semaine
4. Remplissage du carnet d'entraînement Excel
5. Envoi automatique à l'entraîneur

## 📁 Structure des répertoires

```
~/Documents/Triathlon/
├── inbox/                          # Fichiers reçus par Clawdbot
│   ├── S07_*.pdf
│   └── S07_carnet_entrainement.xls
├── processed/                      # Fichiers traités (archivage)
│   ├── 2026/
│   │   └── S07/
│   │       ├── Séances_S07.pdf
│   │       └── S07_carnet_COMPLET.xlsx
└── garmin_automation/
    ├── scripts/
    │   ├── 1_upload_weekly_workouts.py    # Upload PDF → Garmin
    │   ├── 2_convert_xls_to_xlsx.py       # Conversion Excel
    │   ├── 3_fetch_garmin_data.py         # Récup données Garmin
    │   ├── 4_fill_excel_report.py         # Remplissage Excel
    │   ├── 5_prepare_email.py             # Préparation email
    │   └── orchestrator.py                # Chef d'orchestre
    ├── config/
    │   └── automation_config.yaml         # Configuration
    └── logs/
        └── automation_S07.log             # Logs détaillés
```

## 🔧 Configuration requise

### 1. Clawdbot (Automatisation email)

```yaml
# ~/.clawdbot/config.yaml
email:
  imap_server: "imap.gmail.com"
  smtp_server: "smtp.gmail.com"
  username: "ton_email@gmail.com"

  filters:
    - sender: "stephane.palazzetti@*"
      attachments:
        - pattern: "Séances S*.pdf"
          destination: "~/Documents/Triathlon/inbox/"
        - pattern: "*carnet*.xls"
          destination: "~/Documents/Triathlon/inbox/"

  actions:
    - trigger: "new_attachment"
      script: "~/Documents/Triathlon/garmin_automation/scripts/orchestrator.py"
      args: ["--mode", "upload"]
```

### 2. Cron Jobs (Automatisation temporelle)

```bash
# Dimanche 22:00 - Remplissage carnet et envoi email
0 22 * * 0 cd ~/Documents/Triathlon/garmin_automation && source venv/bin/activate && python scripts/orchestrator.py --mode weekly_report

# Quotidien 23:00 - Backup Garmin
0 23 * * * cd ~/Documents/Triathlon/garmin_automation && source venv/bin/activate && python scripts/backup_garmin_data.py
```

## 🚀 Scripts à créer

### Script 1: `orchestrator.py` (Chef d'orchestre)

**Rôle:** Coordonne tous les scripts selon le mode

**Modes:**
- `upload`: Upload PDF → Garmin (déclenché par Clawdbot)
- `weekly_report`: Remplissage Excel + Email (déclenché dimanche 22:00)
- `manual`: Mode manuel pour tests

### Script 2: `1_upload_weekly_workouts.py`

✅ **DÉJÀ CRÉÉ**

### Script 3: `2_convert_xls_to_xlsx.py`

**Rôle:** Convertir XLS → XLSX

**Librairie:** `openpyxl` + `xlrd`

### Script 4: `3_fetch_garmin_data.py`

**Rôle:** Récupérer données Garmin de la semaine

**Données:**
- Activités (type, durée, distance, FC, puissance, allure)
- Poids quotidien
- Sommeil quotidien
- Statistiques hebdomadaires

### Script 5: `4_fill_excel_report.py`

**Rôle:** Remplir le carnet Excel avec données Garmin

**Colonnes à remplir:**
- Date
- Type séance (Cyclisme/Course/Natation)
- Durée réalisée vs. prévue
- Distance
- FC moyenne/max
- Puissance moyenne (cyclisme)
- Allure moyenne (course)
- Sensations (si notes Garmin)
- Poids
- Heures de sommeil

### Script 6: `5_prepare_email.py`

**Rôle:** Générer email avec résumé + pièce jointe

**Contenu email:**
```
Objet: Carnet d'entraînement S07 - Semaine du 09/02 au 15/02

Bonjour Stéphane,

Voici mon carnet d'entraînement pour la semaine S07.

📊 Résumé de la semaine:
- Cyclisme: 3 séances | 4h30 | 120 km
- Course à pied: 3 séances | 2h15 | 22 km
- Natation: 2 séances | 1h30 | 4000m

💪 Charge totale: 8 séances | 8h15

🎯 Respect du programme: 95%

Remarques: [Auto-générées depuis notes Garmin]

Cordialement,
[Ton nom]

---
Généré automatiquement par Garmin Automation
```

## 🎨 Améliorations proposées

### ✨ Améliorations Prioritaires

1. **Dashboard Web (Streamlit/Gradio)**
   - Visualisation hebdomadaire
   - Comparaison prévu vs. réalisé
   - Graphiques progression
   - Contrôle manuel si besoin

2. **Notifications Push**
   - Upload réussi → notification mobile
   - Email envoyé → confirmation
   - Erreurs → alerte immédiate

3. **Validation intelligente**
   - Vérifier cohérence données (durée aberrante, etc.)
   - Alerter si séance manquante
   - Suggérer corrections

4. **Historique et Analytics**
   - Base de données SQLite
   - Métriques long terme
   - Détection tendances (fatigue, progression)

### 🔮 Améliorations Futures

5. **IA pour notes qualitatives**
   - Générer commentaires depuis données Garmin
   - Analyse FC/puissance → "Séance difficile mais bien gérée"
   - Détection surmenage

6. **Synchronisation bidirectionnelle**
   - Modifier séances dans Excel → update Garmin
   - Notes Excel → notes Garmin

7. **Intégration calendrier**
   - Export Google Calendar
   - Rappels avant séances
   - Ajustement météo

8. **Multi-entraîneur**
   - Support plusieurs coachs
   - Formats Excel différents
   - Templates configurables

## 📝 Checklist avant production

- [ ] Tester avec vraie semaine S07
- [ ] Configurer Clawdbot
- [ ] Créer cron jobs
- [ ] Tester conversion XLS → XLSX
- [ ] Vérifier mapping colonnes Excel
- [ ] Configurer SMTP (Gmail App Password)
- [ ] Créer backup automatique
- [ ] Documenter procédure manuelle fallback
- [ ] Tester mode dégradé (Garmin offline)
- [ ] Créer monitoring/logs

## 🚨 Gestion des erreurs

**Si Garmin Connect indisponible:**
- Retry 3x avec backoff exponentiel
- Notification échec
- Mode manuel avec instructions

**Si email ne part pas:**
- Sauvegarder brouillon local
- Notification pour envoi manuel
- Log détaillé

**Si Excel corrompu:**
- Utiliser backup semaine précédente
- Alerter pour correction manuelle

## 🔒 Sécurité

- Credentials Garmin: keyring/keychain
- Email password: App Password Gmail
- Aucun credential en clair dans code
- Logs sans données sensibles
- Backup chiffré (optionnel)
