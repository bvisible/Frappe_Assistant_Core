#!/bin/bash
# Script de configuration du bridge mcp-server-code-execution-mode
# À exécuter après install_phase1.sh

set -e

echo "========================================="
echo "Configuration Bridge MCP Code Execution"
echo "========================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Vérifier Python 3.14
echo "=== Vérification Python ==="
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 14 ]; then
    info "✅ Python $PYTHON_VERSION (OK pour le bridge)"
elif [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 12 ]; then
    warn "⚠️  Python $PYTHON_VERSION détecté"
    warn "Le bridge recommande Python 3.14, mais 3.12+ devrait fonctionner"
    warn "Si vous rencontrez des problèmes, installez Python 3.14"
else
    error "❌ Python 3.14+ requis (actuellement: $PYTHON_VERSION)"
    error "Installer Python 3.14 depuis python.org ou via pyenv"
    exit 1
fi

# Vérifier uv
echo ""
echo "=== Vérification uv ==="
if ! command -v uv &> /dev/null; then
    error "❌ uv non trouvé. Exécuter install_phase1.sh d'abord"
    exit 1
fi
info "✅ uv disponible: $(uv --version)"

# Se placer dans le dossier bridge
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BRIDGE_DIR="$PROJECT_ROOT/mcp-server-code-execution-mode"

if [ ! -d "$BRIDGE_DIR" ]; then
    error "❌ Dossier bridge non trouvé: $BRIDGE_DIR"
    exit 1
fi

cd "$BRIDGE_DIR"
info "Dossier bridge: $BRIDGE_DIR"

# Configurer Python pour le projet
echo ""
echo "=== Configuration Environnement Python ==="

# Essayer de pinner la version Python disponible
if command -v python3.14 &> /dev/null; then
    info "Python 3.14 trouvé, configuration..."
    uv python pin 3.14
elif command -v python3.12 &> /dev/null; then
    warn "Python 3.14 non trouvé, utilisation de 3.12"
    warn "Vous devrez peut-être ajuster pyproject.toml"

    # Modifier temporairement requires-python
    if grep -q "requires-python = \">=3.14\"" pyproject.toml; then
        warn "Modification de requires-python pour Python 3.12"
        sed -i.bak 's/requires-python = ">=3.14"/requires-python = ">=3.12"/' pyproject.toml
    fi
    uv python pin 3.12
else
    # Utiliser python3 par défaut
    warn "Utilisation de python3 par défaut"
    uv python pin $(python3 --version | awk '{print $2}' | cut -d. -f1,2)
fi

# Synchroniser dépendances
echo ""
echo "=== Installation Dépendances ==="
info "Installation des dépendances du bridge..."
uv sync

if [ $? -eq 0 ]; then
    info "✅ Dépendances installées"
else
    error "❌ Échec installation dépendances"
    exit 1
fi

# Créer répertoires de configuration
echo ""
echo "=== Configuration Répertoires ==="
mkdir -p ~/.config/mcp/servers
mkdir -p ~/.mcp-bridge/{ipc,state}
info "✅ Répertoires créés"

# Déterminer le runtime à utiliser
echo ""
echo "=== Détection Container Runtime ==="
if command -v podman &> /dev/null; then
    RUNTIME="podman"
    info "Runtime détecté: Podman"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
    info "Runtime détecté: Docker"
else
    error "❌ Aucun container runtime trouvé"
    error "Installer Podman ou Docker avec install_phase1.sh"
    exit 1
fi

# Créer configuration MCP pour le bridge
echo ""
echo "=== Création Configuration MCP ==="

CONFIG_FILE="$HOME/.config/mcp/servers/mcp-server-code-execution-mode.json"

cat > "$CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "mcp-server-code-execution-mode": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "python",
        "$BRIDGE_DIR/mcp_server_code_execution_mode.py"
      ],
      "env": {
        "MCP_BRIDGE_RUNTIME": "$RUNTIME",
        "MCP_BRIDGE_IMAGE": "python:3.14-slim",
        "MCP_BRIDGE_TIMEOUT": "30",
        "MCP_BRIDGE_MAX_TIMEOUT": "120",
        "MCP_BRIDGE_MEMORY": "512m",
        "MCP_BRIDGE_PIDS": "128",
        "MCP_BRIDGE_STATE_DIR": "$HOME/.mcp-bridge",
        "MCP_BRIDGE_OUTPUT_MODE": "compact",
        "MCP_BRIDGE_LOG_LEVEL": "INFO"
      }
    }
  }
}
EOF

info "✅ Configuration créée: $CONFIG_FILE"

# Test du bridge en mode standalone
echo ""
echo "=== Test Bridge ==="
info "Test du bridge en mode standalone..."

# Créer un test simple
TEST_INPUT='{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}'

echo "$TEST_INPUT" | uv run python mcp_server_code_execution_mode.py > /tmp/bridge_test_output.json 2>&1 || true

if grep -q "result" /tmp/bridge_test_output.json 2>/dev/null; then
    info "✅ Bridge répond correctement"
    cat /tmp/bridge_test_output.json | head -5
else
    warn "⚠️  Réponse inattendue du bridge"
    cat /tmp/bridge_test_output.json
fi

echo ""
echo "========================================="
echo "✅ Configuration Bridge Terminée!"
echo "========================================="
echo ""
echo "Configuration MCP: $CONFIG_FILE"
echo "Runtime utilisé: $RUNTIME"
echo ""
echo "Prochaines étapes:"
echo "1. Configurer Frappe Assistant: ./scripts/setup_frappe_config.sh"
echo "2. Tester l'intégration complète"
echo ""
echo "Pour tester manuellement le bridge:"
echo "  cd $BRIDGE_DIR"
echo "  uv run python mcp_server_code_execution_mode.py"
echo ""
