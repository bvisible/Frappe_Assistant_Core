#!/bin/bash
# Script pour exécuter les tests POC Phase 2
# Ces tests doivent être exécutés via le bridge MCP code execution

set -e

echo "================================================"
echo "Tests POC Phase 2 : Code Execution"
echo "================================================"
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
prompt() { echo -e "${BLUE}[TEST]${NC} $1"; }

# Répertoires
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
POC_DIR="$PROJECT_ROOT/poc"
BRIDGE_DIR="$PROJECT_ROOT/mcp-server-code-execution-mode"

# Vérifier que les fichiers POC existent
if [ ! -d "$POC_DIR" ]; then
    error "Dossier POC non trouvé: $POC_DIR"
    exit 1
fi

# Charger .env si disponible
if [ -f "$PROJECT_ROOT/.env" ]; then
    info "Chargement des variables d'environnement depuis .env"
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
else
    warn "Fichier .env non trouvé"
    warn "Les tests nécessitent FRAPPE_URL, FRAPPE_API_KEY, FRAPPE_API_SECRET"
fi

echo ""
echo "=== Configuration ==="
echo "Project Root: $PROJECT_ROOT"
echo "POC Directory: $POC_DIR"
echo "Bridge Directory: $BRIDGE_DIR"
echo "Frappe URL: ${FRAPPE_URL:-non définie}"
echo ""

# Fonction pour exécuter un test POC
run_poc_test() {
    local test_file=$1
    local test_name=$2

    prompt "Exécution: $test_name"
    echo ""

    # Lire le contenu du test
    local code=$(cat "$POC_DIR/$test_file")

    # Créer une requête JSON-RPC pour le bridge
    local request=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "run_python",
    "arguments": {
      "code": $(echo "$code" | jq -Rs .),
      "servers": ["frappe-assistant"],
      "timeout": 60
    }
  }
}
EOF
)

    # Exécuter via le bridge
    cd "$BRIDGE_DIR"

    echo "$request" | uv run python mcp_server_code_execution_mode.py 2>&1 | tee /tmp/poc_test_output.json

    echo ""
}

# Afficher le menu
echo "Choisissez un test POC à exécuter:"
echo ""
echo "1) Test 1: Découverte des serveurs MCP"
echo "2) Test 2: Recherche simple (search_documents)"
echo "3) Test 3: Workflow complexe (haute valeur)"
echo "4) Exécuter tous les tests"
echo "5) Test manuel (entrer du code Python)"
echo "q) Quitter"
echo ""

read -p "Choix [1-5/q]: " choice

case $choice in
    1)
        run_poc_test "test_01_discovery.py" "Découverte des serveurs"
        ;;
    2)
        run_poc_test "test_02_simple_search.py" "Recherche simple"
        ;;
    3)
        run_poc_test "test_03_complex_workflow.py" "Workflow complexe"
        ;;
    4)
        info "Exécution de tous les tests..."
        echo ""
        run_poc_test "test_01_discovery.py" "Test 1: Découverte"
        echo ""
        echo "================================================"
        echo ""
        run_poc_test "test_02_simple_search.py" "Test 2: Recherche simple"
        echo ""
        echo "================================================"
        echo ""
        run_poc_test "test_03_complex_workflow.py" "Test 3: Workflow complexe"
        ;;
    5)
        info "Mode test manuel"
        echo ""
        echo "Entrez votre code Python (terminer avec EOF ou Ctrl+D):"
        echo ""

        # Lire le code depuis stdin
        code=$(cat)

        if [ -z "$code" ]; then
            error "Aucun code fourni"
            exit 1
        fi

        # Créer requête
        request=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "run_python",
    "arguments": {
      "code": $(echo "$code" | jq -Rs .),
      "servers": ["frappe-assistant"],
      "timeout": 60
    }
  }
}
EOF
)

        cd "$BRIDGE_DIR"
        echo "$request" | uv run python mcp_server_code_execution_mode.py

        ;;
    q|Q)
        info "Au revoir!"
        exit 0
        ;;
    *)
        error "Choix invalide"
        exit 1
        ;;
esac

echo ""
echo "================================================"
echo "✅ Test terminé"
echo "================================================"
echo ""
echo "Sortie complète sauvegardée dans: /tmp/poc_test_output.json"
echo ""
