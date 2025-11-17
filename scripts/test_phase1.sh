#!/bin/bash
# Script de test Phase 1
# Valide que l'installation est complète et fonctionnelle

set -e

echo "================================================"
echo "Tests Phase 1 : Validation Installation"
echo "================================================"
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

test_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((PASS++))
}

test_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((FAIL++))
}

test_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

# Test 1: Python version
echo "=== Test 1: Python Version ==="
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        test_pass "Python $PYTHON_VERSION (≥3.11)"
    else
        test_fail "Python $PYTHON_VERSION trop ancien (requis: ≥3.11)"
    fi
else
    test_fail "Python 3 non trouvé"
fi
echo ""

# Test 2: uv installé
echo "=== Test 2: uv ==="
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version | awk '{print $2}')
    test_pass "uv $UV_VERSION installé"
else
    test_fail "uv non installé"
fi
echo ""

# Test 3: Container runtime
echo "=== Test 3: Container Runtime ==="
RUNTIME_FOUND=false

if command -v podman &> /dev/null; then
    PODMAN_VERSION=$(podman --version | awk '{print $3}')
    test_pass "Podman $PODMAN_VERSION installé"
    RUNTIME="podman"
    RUNTIME_FOUND=true
fi

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    test_pass "Docker $DOCKER_VERSION installé"
    if [ "$RUNTIME_FOUND" = false ]; then
        RUNTIME="docker"
        RUNTIME_FOUND=true
    fi
fi

if [ "$RUNTIME_FOUND" = false ]; then
    test_fail "Aucun container runtime trouvé (Podman ou Docker)"
fi
echo ""

# Test 4: Image Python disponible
if [ "$RUNTIME_FOUND" = true ]; then
    echo "=== Test 4: Image Python ==="

    if [ "$RUNTIME" = "podman" ]; then
        if podman images | grep -q "python.*3.14"; then
            test_pass "Image python:3.14-slim disponible"
        elif podman images | grep -q "python.*3.12"; then
            test_warn "Image python:3.12 disponible (3.14 recommandée)"
        else
            test_fail "Aucune image Python trouvée"
        fi
    elif [ "$RUNTIME" = "docker" ]; then
        if docker images | grep -q "python.*3.14"; then
            test_pass "Image python:3.14-slim disponible"
        elif docker images | grep -q "python.*3.12"; then
            test_warn "Image python:3.12 disponible (3.14 recommandée)"
        else
            test_fail "Aucune image Python trouvée"
        fi
    fi
    echo ""
fi

# Test 5: Runtime fonctionnel
if [ "$RUNTIME_FOUND" = true ]; then
    echo "=== Test 5: Test Container Runtime ==="

    if [ "$RUNTIME" = "podman" ]; then
        if podman run --rm alpine echo "test" &> /dev/null; then
            test_pass "Podman rootless fonctionne"
        else
            test_fail "Podman ne peut pas exécuter de conteneurs"
        fi
    elif [ "$RUNTIME" = "docker" ]; then
        if docker run --rm alpine echo "test" &> /dev/null; then
            test_pass "Docker fonctionne"
        else
            test_fail "Docker ne peut pas exécuter de conteneurs"
        fi
    fi
    echo ""
fi

# Test 6: Répertoires de configuration
echo "=== Test 6: Répertoires ==="
if [ -d "$HOME/.config/mcp/servers" ]; then
    test_pass "Répertoire MCP servers existe"
else
    test_fail "Répertoire MCP servers manquant"
fi

if [ -d "$HOME/.mcp-bridge/ipc" ] && [ -d "$HOME/.mcp-bridge/state" ]; then
    test_pass "Répertoires bridge existent"
else
    test_fail "Répertoires bridge manquants"
fi
echo ""

# Test 7: Configuration bridge MCP
echo "=== Test 7: Configuration Bridge ==="
if [ -f "$HOME/.config/mcp/servers/mcp-server-code-execution-mode.json" ]; then
    test_pass "Configuration bridge existe"

    # Vérifier que le fichier est valide JSON
    if python3 -m json.tool "$HOME/.config/mcp/servers/mcp-server-code-execution-mode.json" &> /dev/null; then
        test_pass "Configuration bridge JSON valide"
    else
        test_fail "Configuration bridge JSON invalide"
    fi
else
    test_fail "Configuration bridge manquante"
fi
echo ""

# Test 8: Configuration Frappe Assistant
echo "=== Test 8: Configuration Frappe ==="
if [ -f "$HOME/.config/mcp/servers/frappe-assistant.json" ]; then
    test_pass "Configuration Frappe existe"

    # Vérifier JSON
    if python3 -m json.tool "$HOME/.config/mcp/servers/frappe-assistant.json" &> /dev/null; then
        test_pass "Configuration Frappe JSON valide"
    else
        test_fail "Configuration Frappe JSON invalide"
    fi
else
    test_warn "Configuration Frappe non créée (optionnel en Phase 1)"
fi
echo ""

# Test 9: Dépendances bridge
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BRIDGE_DIR="$PROJECT_ROOT/mcp-server-code-execution-mode"

echo "=== Test 9: Dépendances Bridge ==="
if [ -d "$BRIDGE_DIR" ]; then
    test_pass "Dossier bridge existe"

    if [ -f "$BRIDGE_DIR/.venv/pyvenv.cfg" ] || [ -f "$BRIDGE_DIR/.python-version" ]; then
        test_pass "Environnement Python bridge configuré"
    else
        test_warn "Environnement Python bridge non synchronisé (uv sync requis)"
    fi
else
    test_fail "Dossier bridge manquant"
fi
echo ""

# Test 10: Adaptateur Frappe
echo "=== Test 10: Adaptateur Frappe ==="
if [ -f "$PROJECT_ROOT/frappe_bridge_adapter.py" ]; then
    test_pass "Adaptateur Frappe créé"

    # Vérifier syntaxe Python
    if python3 -m py_compile "$PROJECT_ROOT/frappe_bridge_adapter.py" 2>/dev/null; then
        test_pass "Adaptateur Frappe syntaxe valide"
    else
        test_fail "Adaptateur Frappe erreurs de syntaxe"
    fi
else
    test_warn "Adaptateur Frappe non créé (sera créé en Phase 2)"
fi
echo ""

# Résumé
echo "================================================"
echo "Résumé Tests Phase 1"
echo "================================================"
echo ""
echo -e "Tests réussis: ${GREEN}$PASS${NC}"
echo -e "Tests échoués: ${RED}$FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ Phase 1 VALIDÉE - Prêt pour Phase 2${NC}"
    echo ""
    echo "Prochaines étapes:"
    echo "1. Lire PLAN_EXECUTION.md Phase 2"
    echo "2. Créer un POC (Proof of Concept)"
    echo "3. Tester l'intégration bridge + Frappe"
    exit 0
else
    echo -e "${RED}❌ Phase 1 INCOMPLÈTE${NC}"
    echo ""
    echo "Actions requises:"
    if [ $FAIL -gt 0 ]; then
        echo "- Corriger les tests échoués ci-dessus"
    fi
    echo "- Relancer les scripts d'installation:"
    echo "    ./scripts/install_phase1.sh"
    echo "    ./scripts/setup_bridge.sh"
    echo "    ./scripts/setup_frappe_config.sh"
    exit 1
fi
