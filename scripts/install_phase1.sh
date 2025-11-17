#!/bin/bash
# Script d'installation Phase 1 : Setup Environnement
# À exécuter sur votre machine hôte (pas dans Claude Code)

set -e

echo "========================================="
echo "Phase 1 : Installation Environnement"
echo "========================================="
echo ""

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher des messages
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Détection de l'OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            OS_VERSION=$VERSION_ID
        fi
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

OS_TYPE=$(detect_os)
info "OS détecté: $OS_TYPE"

echo ""
echo "=== Étape 1: Vérification Python ==="
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    info "Python installé: $PYTHON_VERSION"

    # Vérifier version minimale (3.11+)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        info "✅ Version Python OK (≥3.11)"
    else
        warn "⚠️  Python 3.11+ recommandé (actuellement: $PYTHON_VERSION)"
    fi
else
    error "❌ Python 3 non trouvé. Installation requise."
    exit 1
fi

echo ""
echo "=== Étape 2: Installation/Vérification uv ==="
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version | awk '{print $2}')
    info "✅ uv déjà installé: $UV_VERSION"
else
    info "Installation de uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Ajouter au PATH
    export PATH="$HOME/.local/bin:$PATH"

    if command -v uv &> /dev/null; then
        info "✅ uv installé avec succès"
    else
        error "❌ Échec installation uv"
        exit 1
    fi
fi

echo ""
echo "=== Étape 3: Installation Container Runtime ==="

install_podman_ubuntu() {
    info "Installation Podman sur Ubuntu/Debian..."

    # Vérifier si on peut utiliser apt
    if ! command -v apt &> /dev/null; then
        error "apt non disponible"
        return 1
    fi

    # Installer via apt (Ubuntu 24.04+) ou Homebrew (Ubuntu 22.04)
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        VERSION_NUM=$(echo $VERSION_ID | cut -d. -f1)

        if [ "$VERSION_NUM" -ge 24 ]; then
            info "Ubuntu 24.04+, installation via apt..."
            sudo apt update
            sudo apt install -y podman
        else
            warn "Ubuntu < 24.04, installation via Homebrew recommandée..."
            warn "Installer Homebrew puis: brew install podman"
            return 1
        fi
    fi

    # Installer dépendances
    sudo apt install -y slirp4netns passt uidmap fuse-overlayfs
}

install_podman_macos() {
    info "Installation Podman sur macOS..."

    if ! command -v brew &> /dev/null; then
        error "Homebrew requis. Installer depuis https://brew.sh"
        exit 1
    fi

    brew install podman
}

install_docker() {
    info "Installation Docker..."

    if [[ "$OS_TYPE" == "linux" ]]; then
        warn "Installation Docker rootless recommandée"
        info "Exécutez: curl -fsSL https://get.docker.com/rootless | sh"
    elif [[ "$OS_TYPE" == "macos" ]]; then
        if ! command -v brew &> /dev/null; then
            error "Homebrew requis"
            exit 1
        fi
        brew install --cask docker
    fi
}

# Vérifier si un runtime est déjà installé
if command -v podman &> /dev/null; then
    PODMAN_VERSION=$(podman --version | awk '{print $3}')
    info "✅ Podman déjà installé: $PODMAN_VERSION"
    RUNTIME="podman"
elif command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    info "✅ Docker déjà installé: $DOCKER_VERSION"
    RUNTIME="docker"
else
    warn "Aucun container runtime trouvé"

    echo ""
    echo "Choisissez un runtime à installer:"
    echo "1) Podman (recommandé, plus sécurisé)"
    echo "2) Docker"
    read -p "Choix [1/2]: " choice

    case $choice in
        1)
            if [[ "$OS_TYPE" == "linux" ]]; then
                install_podman_ubuntu
            elif [[ "$OS_TYPE" == "macos" ]]; then
                install_podman_macos
            fi
            RUNTIME="podman"
            ;;
        2)
            install_docker
            RUNTIME="docker"
            ;;
        *)
            error "Choix invalide"
            exit 1
            ;;
    esac
fi

echo ""
echo "=== Étape 4: Configuration User Namespaces (Podman uniquement) ==="
if [ "$RUNTIME" == "podman" ] && [[ "$OS_TYPE" == "linux" ]]; then
    info "Configuration des user namespaces..."

    # Vérifier configuration existante
    if ! grep -q "$(whoami)" /etc/subuid 2>/dev/null; then
        info "Ajout de la configuration subuid/subgid..."
        echo "$(whoami):100000:65536" | sudo tee -a /etc/subuid
        echo "$(whoami):100000:65536" | sudo tee -a /etc/subgid
    else
        info "✅ Configuration subuid/subgid déjà présente"
    fi

    # Migration Podman
    info "Migration de la configuration Podman..."
    podman system migrate

    info "✅ Configuration user namespaces terminée"
fi

echo ""
echo "=== Étape 5: Téléchargement Image Python ==="
info "Téléchargement de l'image python:3.14-slim..."

if [ "$RUNTIME" == "podman" ]; then
    podman pull python:3.14-slim || podman pull python:3.12-slim
elif [ "$RUNTIME" == "docker" ]; then
    docker pull python:3.14-slim || docker pull python:3.12-slim
fi

if [ $? -eq 0 ]; then
    info "✅ Image Python téléchargée"
else
    error "❌ Échec du téléchargement de l'image"
    exit 1
fi

echo ""
echo "=== Étape 6: Configuration Répertoires ==="
info "Création des répertoires de configuration..."

# Créer répertoires MCP
mkdir -p ~/.config/mcp/servers
mkdir -p ~/.mcp-bridge/{ipc,state}

# Fixer permissions pour Podman
if [ "$RUNTIME" == "podman" ]; then
    info "Configuration des permissions pour le sandbox..."
    podman unshare chown 65534:65534 -R ~/.mcp-bridge
fi

info "✅ Répertoires créés"

echo ""
echo "=== Étape 7: Test du Runtime ==="
info "Test du container runtime..."

if [ "$RUNTIME" == "podman" ]; then
    if podman run --rm alpine echo "✅ Rootless OK!"; then
        info "✅ Podman fonctionne correctement"
    else
        error "❌ Test Podman échoué"
        exit 1
    fi
elif [ "$RUNTIME" == "docker" ]; then
    if docker run --rm alpine echo "✅ Docker OK!"; then
        info "✅ Docker fonctionne correctement"
    else
        error "❌ Test Docker échoué"
        exit 1
    fi
fi

echo ""
echo "========================================="
echo "✅ Phase 1 Installation Terminée!"
echo "========================================="
echo ""
echo "Runtime installé: $RUNTIME"
echo "Python: $(python3 --version)"
echo "uv: $(uv --version)"
echo ""
echo "Prochaines étapes:"
echo "1. Configurer le bridge MCP: ./scripts/setup_bridge.sh"
echo "2. Créer la configuration Frappe Assistant"
echo "3. Tester l'installation"
echo ""
