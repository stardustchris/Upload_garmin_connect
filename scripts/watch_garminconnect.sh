#!/bin/bash
# Surveille les nouvelles issues, PRs et releases sur python-garminconnect
# Usage: ./scripts/watch_garminconnect.sh

REPO="cyberjunky/python-garminconnect"
CACHE_DIR="data/cache"
LAST_CHECK_FILE="$CACHE_DIR/last_github_check.txt"

# Créer le dossier cache si nécessaire
mkdir -p "$CACHE_DIR"

echo "🔍 Surveillance du repo: $REPO"
echo "=====================================\n"

# Vérifier si gh CLI est installé
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) n'est pas installé"
    echo "   Installation: brew install gh"
    echo "   Puis: gh auth login"
    exit 1
fi

# Dernières issues
echo "📋 Dernières issues (10):"
gh issue list --repo "$REPO" --limit 10 --state all --json number,title,createdAt,state | \
    jq -r '.[] | "  #\(.number) [\(.state)] \(.title) (créé: \(.createdAt[:10]))"'

echo ""

# Derniers PRs
echo "🔀 Derniers Pull Requests (5):"
gh pr list --repo "$REPO" --limit 5 --json number,title,createdAt,state | \
    jq -r '.[] | "  #\(.number) [\(.state)] \(.title) (créé: \(.createdAt[:10]))"'

echo ""

# Dernières releases
echo "🚀 Dernières releases (3):"
gh release list --repo "$REPO" --limit 3 | head -3

echo ""

# Sauvegarder le timestamp de la vérification
date '+%Y-%m-%d %H:%M:%S' > "$LAST_CHECK_FILE"
echo "✅ Vérification terminée à $(cat $LAST_CHECK_FILE)"

# Optionnel: Vérifier les issues récentes (dernières 24h)
echo ""
echo "🔥 Issues récentes (dernières 24h):"
gh issue list --repo "$REPO" --limit 20 --state all --json number,title,createdAt,state | \
    jq -r --arg date "$(date -u -v-1d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ)" \
    '.[] | select(.createdAt > $date) | "  #\(.number) [\(.state)] \(.title)"'

echo ""
echo "💡 Pour plus de détails:"
echo "   gh issue view <NUMBER> --repo $REPO"
echo "   gh pr view <NUMBER> --repo $REPO"
