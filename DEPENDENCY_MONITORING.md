# Surveillance des Dépendances

## 🎯 Objectif

Garder les dépendances à jour pour bénéficier :
- Des corrections de bugs
- Des nouvelles fonctionnalités
- Des améliorations de sécurité

## 📦 Dépendances Critiques

| Package | Rôle | Importance |
|---------|------|------------|
| `garminconnect` | API Garmin Connect | ⭐⭐⭐ Critique |
| `garth` | Authentification OAuth Garmin | ⭐⭐⭐ Critique |
| `fastapi` | API REST | ⭐⭐ Important |
| `pydantic` | Validation de données | ⭐⭐ Important |
| `PyPDF2` | Parsing PDF | ⭐⭐ Important |

## 🔍 Méthodes de Surveillance

### 1. Script Automatique (Recommandé)

Exécuter périodiquement :

```bash
source venv/bin/activate
python scripts/check_updates.py
```

**Fréquence recommandée** : Une fois par semaine

### 2. Surveillance GitHub

**python-garminconnect** :
- Repo : https://github.com/cyberjunky/python-garminconnect
- Watch → Custom → Releases ✅
- Issues → Surveillance des bugs critiques

**garth** :
- Repo : https://github.com/matin/garth
- Watch → Custom → Releases ✅

### 3. Vérification Manuelle PyPI

```bash
pip index versions garminconnect
pip index versions garth
```

## 🔄 Processus de Mise à Jour

### Avant de mettre à jour

1. **Lire le CHANGELOG** du package
2. **Vérifier les breaking changes**
3. **Créer une branche** : `git checkout -b update-dependencies`

### Mise à jour

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Mettre à jour un package spécifique
pip install --upgrade garminconnect

# Ou mettre à jour tous les packages
pip install --upgrade -r requirements.txt

# Geler les nouvelles versions
pip freeze > requirements.txt
```

### Après mise à jour

1. **Tester l'authentification** : `python scripts/garmin_auth_manual_mfa.py`
2. **Tester l'upload** : `python scripts/test_upload_c16.py`
3. **Vérifier sur Garmin Connect** : https://connect.garmin.com/modern/workouts
4. **Commit** : `git commit -am "chore: Update dependencies"`

## ⚠️ Cas Spéciaux

### garth Version Pinning

**Situation actuelle** : `garminconnect 0.2.38` nécessite `garth <0.6.0`

```bash
# Ne PAS upgrader garth au-delà de 0.5.x
pip install 'garth<0.6.0'
```

Si une nouvelle version de `garminconnect` supporte `garth 0.6+`, alors on pourra upgrader.

### Breaking Changes Connus

**garminconnect 0.2.x → 0.3.x** (futur) :
- Vérifier compatibilité API
- Tester toutes les méthodes : `upload_workout()`, `get_workout_by_id()`, etc.

## 📅 Calendrier de Vérification

| Action | Fréquence | Responsable |
|--------|-----------|-------------|
| Exécuter `check_updates.py` | Hebdomadaire (lundi) | Automatique |
| Vérifier Issues GitHub | Bi-hebdomadaire | Manuel |
| Lire Changelogs | À chaque release | Manuel |
| Mettre à jour dépendances | Mensuel ou si bug critique | Manuel |

## 🐛 Monitoring des Issues

### python-garminconnect Issues à Surveiller

Filtres GitHub utiles :
- **Bugs critiques** : `is:issue is:open label:bug`
- **API Changes** : `is:issue is:open label:enhancement`
- **Authentication** : `is:issue is:open auth OR mfa OR oauth`

### Signaux d'Alerte

⚠️ **Mettre à jour immédiatement si** :
- Bug de sécurité annoncé
- Authentification cassée
- Upload de workout échoue
- Changement d'API Garmin Connect

## 📊 Historique des Mises à Jour

| Date | Package | Version | Raison |
|------|---------|---------|--------|
| 2026-02-08 | `garminconnect` | 0.2.23 → 0.2.38 | Ajout méthode `upload_workout()` |
| 2026-02-08 | `garth` | 0.6.3 → 0.5.21 | Compatibilité avec garminconnect 0.2.38 |

## 🔗 Liens Utiles

- **python-garminconnect Repo** : https://github.com/cyberjunky/python-garminconnect
- **python-garminconnect Releases** : https://github.com/cyberjunky/python-garminconnect/releases
- **python-garminconnect PyPI** : https://pypi.org/project/garminconnect/
- **garth Repo** : https://github.com/matin/garth
- **Garmin Connect API Status** : (Pas de page officielle, surveiller les Issues)

## 💡 Bonnes Pratiques

1. **Ne jamais mettre à jour en production sans tester**
2. **Toujours lire le CHANGELOG avant de mettre à jour**
3. **Tester avec C16 après chaque mise à jour**
4. **Garder un historique des versions dans `requirements.txt`**
5. **Documenter les problèmes rencontrés dans LESSONS.md**

---

**Dernière vérification** : 2026-02-08
**Prochaine vérification recommandée** : 2026-02-15
