#!/bin/bash
# Script de configuration Frappe Assistant pour MCP
# À exécuter après setup_bridge.sh

set -e

echo "================================================"
echo "Configuration Frappe Assistant MCP"
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
prompt() { echo -e "${BLUE}[INPUT]${NC} $1"; }

# Répertoire du script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Information Projet ==="
info "Projet: Frappe Assistant Core"
info "Chemin: $PROJECT_ROOT"
echo ""

# Vérifier si frappe_assistant_stdio_bridge.py existe
STDIO_BRIDGE="$PROJECT_ROOT/frappe_assistant_stdio_bridge.py"

if [ ! -f "$STDIO_BRIDGE" ]; then
    warn "⚠️  frappe_assistant_stdio_bridge.py non trouvé"
    warn "Le bridge STDIO sera créé si nécessaire"
fi

# Collecter les informations Frappe
echo "=== Configuration Frappe ==="
echo ""
echo "Entrez les informations de votre installation Frappe:"
echo ""

# Site Frappe
read -p "$(echo -e ${BLUE}Site Frappe${NC} [mysite.localhost]: )" FRAPPE_SITE
FRAPPE_SITE=${FRAPPE_SITE:-mysite.localhost}

# URL Frappe
read -p "$(echo -e ${BLUE}URL Frappe${NC} [http://localhost:8000]: )" FRAPPE_URL
FRAPPE_URL=${FRAPPE_URL:-http://localhost:8000}

# API Key
echo ""
echo -e "${BLUE}API Key et Secret Frappe${NC}"
echo "Pour générer des credentials API dans Frappe:"
echo "1. Se connecter à Frappe"
echo "2. Aller dans: User > API Access > Generate Keys"
echo ""

read -p "$(echo -e ${BLUE}API Key${NC}: )" FRAPPE_API_KEY
read -p "$(echo -e ${BLUE}API Secret${NC}: )" FRAPPE_API_SECRET

# Validation
if [ -z "$FRAPPE_API_KEY" ] || [ -z "$FRAPPE_API_SECRET" ]; then
    error "❌ API Key et Secret requis"
    exit 1
fi

# Tester la connexion
echo ""
echo "=== Test Connexion Frappe ==="
info "Test de la connexion à $FRAPPE_URL..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: token $FRAPPE_API_KEY:$FRAPPE_API_SECRET" \
    "$FRAPPE_URL/api/method/ping" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    info "✅ Connexion réussie à Frappe"
elif [ "$HTTP_CODE" = "000" ]; then
    warn "⚠️  Impossible de se connecter à $FRAPPE_URL"
    warn "Vérifier que Frappe est démarré"
else
    warn "⚠️  Réponse HTTP $HTTP_CODE"
    warn "Vérifier les credentials API"
fi

# Créer configuration MCP pour Frappe Assistant
echo ""
echo "=== Création Configuration MCP ==="

CONFIG_FILE="$HOME/.config/mcp/servers/frappe-assistant.json"

cat > "$CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "frappe-assistant": {
      "type": "stdio",
      "command": "python3",
      "args": [
        "$STDIO_BRIDGE"
      ],
      "env": {
        "FRAPPE_SITE": "$FRAPPE_SITE",
        "FRAPPE_URL": "$FRAPPE_URL",
        "FRAPPE_API_KEY": "$FRAPPE_API_KEY",
        "FRAPPE_API_SECRET": "$FRAPPE_API_SECRET"
      }
    }
  }
}
EOF

info "✅ Configuration Frappe créée: $CONFIG_FILE"

# Créer fichier .env pour développement local
echo ""
echo "=== Création fichier .env ==="

ENV_FILE="$PROJECT_ROOT/.env"

cat > "$ENV_FILE" <<EOF
# Configuration Frappe Assistant
# NE PAS COMMITTER CE FICHIER !

FRAPPE_SITE=$FRAPPE_SITE
FRAPPE_URL=$FRAPPE_URL
FRAPPE_API_KEY=$FRAPPE_API_KEY
FRAPPE_API_SECRET=$FRAPPE_API_SECRET
EOF

# Ajouter .env au .gitignore si pas déjà fait
if [ -f "$PROJECT_ROOT/.gitignore" ]; then
    if ! grep -q "^\.env$" "$PROJECT_ROOT/.gitignore"; then
        echo ".env" >> "$PROJECT_ROOT/.gitignore"
        info "✅ .env ajouté au .gitignore"
    fi
fi

info "✅ Fichier .env créé: $ENV_FILE"
warn "⚠️  Ne commitez JAMAIS le fichier .env (contient les secrets)"

# Créer adaptateur Frappe pour le sandbox
echo ""
echo "=== Création Adaptateur Frappe ==="

ADAPTER_FILE="$PROJECT_ROOT/frappe_bridge_adapter.py"

if [ -f "$ADAPTER_FILE" ]; then
    warn "⚠️  $ADAPTER_FILE existe déjà, sauvegarde créée"
    cp "$ADAPTER_FILE" "$ADAPTER_FILE.bak"
fi

cat > "$ADAPTER_FILE" <<'EOFPYTHON'
"""
Adaptateur Frappe pour le sandbox code execution.
Permet d'appeler les APIs Frappe depuis le code Python exécuté dans le sandbox.
"""

import os
import httpx
from typing import Dict, List, Any, Optional


class FrappeProxyAdapter:
    """Adaptateur pour proxifier appels Frappe via HTTP API"""

    def __init__(self):
        self.base_url = os.getenv('FRAPPE_URL', 'http://localhost:8000')
        self.api_key = os.getenv('FRAPPE_API_KEY')
        self.api_secret = os.getenv('FRAPPE_API_SECRET')

        if not self.api_key or not self.api_secret:
            raise ValueError("FRAPPE_API_KEY et FRAPPE_API_SECRET requis")

        self.client = httpx.Client(
            base_url=self.base_url,
            auth=(self.api_key, self.api_secret),
            timeout=30.0
        )

    def search_documents(
        self,
        doctype: str,
        filters: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Recherche documents via API Frappe"""
        params = {
            'filters': filters or {},
            'fields': fields or ['*'],
            'order_by': order_by or 'modified desc',
            'limit_page_length': limit
        }

        response = self.client.get(f'/api/resource/{doctype}', params=params)
        response.raise_for_status()

        return response.json().get('data', [])

    def get_document(
        self,
        doctype: str,
        name: str,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Récupérer un document spécifique"""
        params = {'fields': fields or ['*']}

        response = self.client.get(
            f'/api/resource/{doctype}/{name}',
            params=params
        )
        response.raise_for_status()

        return response.json().get('data', {})

    def create_document(
        self,
        doctype: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Créer un document"""
        payload = {
            'doctype': doctype,
            **data
        }

        response = self.client.post(
            f'/api/resource/{doctype}',
            json=payload
        )
        response.raise_for_status()

        return response.json().get('data', {})

    def update_document(
        self,
        doctype: str,
        name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mettre à jour un document"""
        response = self.client.put(
            f'/api/resource/{doctype}/{name}',
            json=data
        )
        response.raise_for_status()

        return response.json().get('data', {})

    def delete_document(
        self,
        doctype: str,
        name: str
    ) -> Dict[str, str]:
        """Supprimer un document"""
        response = self.client.delete(f'/api/resource/{doctype}/{name}')
        response.raise_for_status()

        return {'success': True, 'message': f'{doctype} {name} deleted'}

    def get_doctype_schema(self, doctype: str) -> Dict[str, Any]:
        """Récupérer métadonnées DocType"""
        response = self.client.get(f'/api/resource/DocType/{doctype}')
        response.raise_for_status()

        meta = response.json().get('data', {})
        return {
            'name': meta.get('name'),
            'fields': meta.get('fields', []),
            'permissions': meta.get('permissions', [])
        }


# Pour import facile dans le sandbox
__all__ = ['FrappeProxyAdapter']
EOFPYTHON

info "✅ Adaptateur Frappe créé: $ADAPTER_FILE"

# Résumé
echo ""
echo "================================================"
echo "✅ Configuration Frappe Assistant Terminée!"
echo "================================================"
echo ""
echo "Fichiers créés:"
echo "  - Configuration MCP: $CONFIG_FILE"
echo "  - Variables env: $ENV_FILE"
echo "  - Adaptateur: $ADAPTER_FILE"
echo ""
echo "Configuration:"
echo "  Site: $FRAPPE_SITE"
echo "  URL: $FRAPPE_URL"
echo "  API Key: ${FRAPPE_API_KEY:0:10}..."
echo ""
echo "Prochaines étapes:"
echo "1. Tester la configuration: ./scripts/test_phase1.sh"
echo "2. Lire la documentation: PLAN_EXECUTION.md (Phase 2)"
echo ""
echo "Pour utiliser l'adaptateur dans le code execution:"
echo "  from frappe_bridge_adapter import FrappeProxyAdapter"
echo "  adapter = FrappeProxyAdapter()"
echo "  docs = adapter.search_documents('Customer', limit=5)"
echo ""
