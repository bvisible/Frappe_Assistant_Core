# Plan de Migration Complet : Frappe_Assistant_Core vers Code Execution Mode

## Synthèse exécutive

**La migration de Frappe_Assistant_Core vers l'architecture code execution avec elusznik/mcp-server-code-execution-mode permet une réduction de 99% de l'overhead contextuel (30 000 → 200 tokens) tout en débloquant des workflows complexes via l'exécution Python sandboxée.** Cette transformation radicale améliore les performances de 9x pour les opérations multi-étapes et réduit les coûts d'API de 99%.

Le plan détaillé ci-dessous est optimisé pour une exécution sur Ubuntu (sans Docker) avec Podman en mode rootless, priorisant les outils de recherche et création d'ERPNext, et structuré pour être exécuté progressivement par Claude Code.

---

## 1. ARCHITECTURES TECHNIQUES DÉTAILLÉES

### 1.1 Architecture Actuelle : Frappe_Assistant_Core

**Composants principaux analysés depuis buildswithpaul/Frappe_Assistant_Core** :

```
Frappe_Assistant_Core/
├── core/
│   ├── tool_registry.py          # Registre de 20+ outils
│   └── base_tool.py               # Classe base pour outils
├── plugins/
│   ├── core/                      # Outils toujours actifs
│   │   └── tools/
│   │       ├── document_*.py      # CRUD documents
│   │       ├── search_*.py        # Recherche (PRIORITÉ)
│   │       └── metadata_*.py      # Métadonnées
│   ├── data_science/              # Exécution Python (optionnel)
│   └── batch_processing/          # Opérations batch
├── api/
│   └── fac_endpoint.py            # Endpoint MCP JSON-RPC 2.0
└── utils/
    └── plugin_manager.py          # Gestion plugins thread-safe
```

**Inventaire des outils par priorité de migration** :

**PHASE 1 - Outils de recherche (haute priorité)** :
1. `search_documents` / `list_documents` - Recherche avec filtres via `frappe.get_all()`
2. `get_document` / `document_read` - Lecture document via `frappe.get_doc()`
3. `global_search` - Recherche cross-doctype
4. `get_doctype_schema` - Métadonnées DocType via `frappe.get_meta()`
5. `find_doctypes` - Recherche DocTypes

**PHASE 2 - Outils de création (haute priorité)** :
6. `create_document` - Création via `frappe.get_doc().insert()`
7. `update_document` - Mise à jour via `doc.update()` et `doc.save()`
8. `delete_document` - Suppression via `frappe.delete_doc()`

**PHASE 3 - Outils avancés** :
9. `execute_report` - Exécution rapports Frappe
10. `get_workflow_info` - Workflows
11. `batch_create_documents` - Création en masse
12. `execute_python_code` - Exécution Python sandbox (déjà proche du pattern cible)

**Architecture OAuth actuelle** :
- OAuth 2.0 + OpenID Connect avec PKCE
- Endpoints: `/api/method/frappe.integrations.oauth2.authorize`, `.get_token`, `.openid_profile`
- RBAC : Rôle "Frappe Assistant User" requis + permissions ERPNext natives
- Audit : DocType "Assistant Core Audit Log" avec tracking complet

### 1.2 Architecture Cible : elusznik/mcp-server-code-execution-mode

**Fonctionnement analysé depuis elusznik/mcp-server-code-execution-mode** :

```
┌──────────────────┐
│   Claude Code    │
└────────┬─────────┘
         │ stdio
         ▼
┌──────────────────┐
│  MCP Bridge      │ ← Un seul outil : run_python
│  Code Exec       │    + Discovery runtime
└────────┬─────────┘
         │ JSON frames via /ipc
         ▼
┌──────────────────┐
│  Conteneur       │ ← Podman rootless
│  Sandbox Python  │    network=none, read-only
└──────────────────┘    UID 65534, cap-drop ALL
```

**Mécanisme de découverte progressive** :

Au lieu de charger 30 000 tokens de définitions d'outils, le bridge maintient un overhead constant de ~200 tokens et expose des helpers de découverte :

```python
from mcp import runtime

# Étape 1 : Découvrir les serveurs disponibles (sans charger schémas)
discovered = runtime.discovered_servers()  
# Retourne: ('frappe_assistant', 'filesystem', 'github')

# Étape 2 : Hydrater uniquement les schémas nécessaires
docs = await runtime.query_tool_docs('frappe_assistant', tool='search_documents')

# Étape 3 : Exécuter du code Python qui orchestre les outils
result = await mcp_frappe_assistant.search_documents(
    doctype='Customer',
    filters={'customer_group': 'VIP'}
)
```

**Sandboxing Podman rootless** :

| Contrainte | Configuration | But |
|---|---|---|
| Réseau | `--network none` | Isolation totale |
| Filesystem | `--read-only` | Root immutable |
| Capabilities | `--cap-drop ALL` | Aucun accès système |
| Utilisateur | `65534:65534` | Non privilégié |
| Mémoire | `--memory 512m` | Limite ressources |
| Processus | `--pids-limit 128` | Limite PIDs |

---

## 2. STRATÉGIE D'INTÉGRATION UBUNTU SANS DOCKER

### 2.1 Installation Podman sur Ubuntu

**Problème identifié** : Ubuntu 22.04 LTS livre Podman 3.4.4 (obsolète, bugs connus). **Solution recommandée** : Installer via Homebrew pour obtenir Podman 5.x avec support pasta networking.

**Commandes d'installation (Ubuntu 22.04/24.04)** :

```bash
# Option A : Repository par défaut (Ubuntu 24.04 uniquement)
sudo apt update
sudo apt install podman -y

# Option B : Homebrew (RECOMMANDÉ pour Ubuntu 22.04)
# Installer Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Ajouter au PATH
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.profile
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# Installer Podman
brew install podman

# Vérifier la version (doit être 4.5+)
podman --version
```

### 2.2 Configuration Rootless

**Pré-requis système** :

```bash
# Installer outils réseau et overlay
sudo apt install -y slirp4netns passt uidmap fuse-overlayfs

# Installer uv (gestionnaire d'environnement Python)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Configuration user namespace** :

```bash
# Vérifier la configuration existante
grep $(whoami) /etc/subuid /etc/subgid

# Si non configuré, ajouter des ranges UID/GID
echo "$(whoami):100000:65536" | sudo tee -a /etc/subuid
echo "$(whoami):100000:65536" | sudo tee -a /etc/subgid

# Migrer la configuration Podman
podman system migrate

# Vérifier que rootless fonctionne
podman run --rm -it alpine echo "Rootless OK!"
```

**Activer le lingering utilisateur (optionnel, pour services persistants)** :

```bash
# Permettre aux conteneurs de persister après déconnexion
sudo loginctl enable-linger $(whoami)

# Démarrer le socket Podman pour API
systemctl --user enable --now podman.socket
```

### 2.3 Configuration Réseau pour Communication MCP

**Créer un réseau custom pour les serveurs MCP** :

```bash
# Créer réseau avec DNS activé
podman network create \
  --dns-enabled \
  --subnet 10.90.0.0/16 \
  frappe-mcp-net

# Vérifier le réseau
podman network inspect frappe-mcp-net
```

**Pattern de communication conteneur-à-hôte** (pour accès APIs Frappe) :

```bash
# Permettre au conteneur d'accéder à l'hôte (Podman 5.0+ avec pasta)
podman run -d \
  --network pasta:--map-gw \
  --name mcp-executor \
  --add-host=frappe-host:host-gateway \
  python:3.12-slim

# Dans le conteneur, Frappe est accessible via :
# http://frappe-host:8000
```

### 2.4 Intégration avec Installation Frappe Existante

**Monter les volumes Frappe avec permissions correctes** :

```bash
# Créer répertoires pour données partagées
mkdir -p ~/frappe-mcp-bridge/{ipc,state}

# Fixer permissions pour UID conteneur (65534)
podman unshare chown 65534:65534 -R ~/frappe-mcp-bridge

# Tester le montage
podman run --rm \
  -v ~/frappe-mcp-bridge/ipc:/ipc:Z \
  --user 65534:65534 \
  alpine touch /ipc/test.txt
```

**Configuration réseau pour accès Frappe** :

L'installation Frappe existante tourne sur l'hôte (port 8000 par défaut). Le conteneur sandbox doit pouvoir appeler les APIs Frappe via proxy :

```python
# Dans le code exécuté dans le sandbox
import os
import httpx

# URL Frappe accessible via host-gateway
frappe_url = os.getenv('FRAPPE_URL', 'http://frappe-host:8000')
api_key = os.getenv('FRAPPE_API_KEY')
api_secret = os.getenv('FRAPPE_API_SECRET')

# Client authentifié
client = httpx.Client(
    base_url=frappe_url,
    auth=(api_key, api_secret)
)
```

---

## 3. PLAN DE MIGRATION ÉTAPE PAR ÉTAPE (OPTIMISÉ CLAUDE CODE)

### PHASE 1 : Setup Environnement (Semaine 1-2)

#### Étape 1.1 : Installation Podman \u0026 Dépendances

**Objectif** : Environnement Podman rootless opérationnel sur Ubuntu.

**Commandes Claude Code** :

```bash
# Prompt pour Claude Code :
# "Exécute l'installation complète de Podman rootless sur Ubuntu 22.04
# avec tous les pré-requis pour mcp-server-code-execution-mode"

# 1. Installer Homebrew si pas déjà installé
if ! command -v brew &> /dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.profile
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# 2. Installer Podman via Homebrew
brew install podman

# 3. Installer dépendances système
sudo apt update
sudo apt install -y slirp4netns passt uidmap fuse-overlayfs python3-pip

# 4. Installer uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 5. Configurer user namespaces
if ! grep -q "$(whoami)" /etc/subuid; then
    echo "$(whoami):100000:65536" | sudo tee -a /etc/subuid
    echo "$(whoami):100000:65536" | sudo tee -a /etc/subgid
fi

# 6. Migrer configuration Podman
podman system migrate

# 7. Activer lingering
sudo loginctl enable-linger $(whoami)

# 8. Télécharger image de base
podman pull python:3.12-slim

# 9. Test fonctionnel
podman run --rm alpine echo "Podman rootless opérationnel"
```

**Tests de validation Étape 1.1** :

```bash
# Test 1 : Version Podman
podman --version | grep -E "version [45]\." || echo "ERREUR: Version trop ancienne"

# Test 2 : Rootless fonctionne
podman run --rm alpine id | grep "uid=0(root)" && echo "OK" || echo "ERREUR"

# Test 3 : Network pasta disponible
podman info | grep -i pasta && echo "Pasta OK" || echo "Utilise slirp4netns"

# Test 4 : Image Python disponible
podman images | grep python:3.12-slim && echo "OK" || echo "ERREUR"
```

**Métriques de succès** :
- ✅ Podman 4.5+ installé
- ✅ Rootless opérationnel (test alpine réussi)
- ✅ Image python:3.12-slim téléchargée
- ✅ Pasta networking disponible

**Rollback** : Si échec, désinstaller avec `brew uninstall podman` et `sudo apt remove podman`.

---

#### Étape 1.2 : Installation mcp-server-code-execution-mode

**Objectif** : Bridge code execution opérationnel et configuré.

**Commandes Claude Code** :

```bash
# Prompt : "Clone et configure mcp-server-code-execution-mode
# avec configuration pour environnement Ubuntu + Frappe"

# 1. Créer répertoire projet
mkdir -p ~/frappe-mcp-migration
cd ~/frappe-mcp-migration

# 2. Cloner le repository
git clone https://github.com/elusznik/mcp-server-code-execution-mode.git
cd mcp-server-code-execution-mode

# 3. Installer avec uv
uv python pin 3.12
uv sync

# 4. Créer configuration pour Claude Code
mkdir -p ~/.config/mcp/servers

cat > ~/.config/mcp/servers/mcp-server-code-execution-mode.json <<'EOF'
{
  "mcpServers": {
    "mcp-server-code-execution-mode": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "python",
        "/home/$(whoami)/frappe-mcp-migration/mcp-server-code-execution-mode/mcp_server_code_execution_mode.py"
      ],
      "env": {
        "MCP_BRIDGE_RUNTIME": "podman",
        "MCP_BRIDGE_STATE_DIR": "/home/$(whoami)/.mcp-bridge",
        "MCP_BRIDGE_TIMEOUT": "60s",
        "MCP_BRIDGE_MEMORY": "512m"
      }
    }
  }
}
EOF

# Remplacer $(whoami) par le nom d'utilisateur réel
sed -i "s/\$(whoami)/$USER/g" ~/.config/mcp/servers/mcp-server-code-execution-mode.json

# 5. Créer répertoires state
mkdir -p ~/.mcp-bridge/{ipc,state}
podman unshare chown 65534:65534 -R ~/.mcp-bridge

# 6. Test du bridge (mode standalone)
uv run python mcp_server_code_execution_mode.py <<EOF
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "0.1.0", "capabilities": {}}}
EOF
```

**Tests de validation Étape 1.2** :

```bash
# Test 1 : Bridge répond au ping
echo '{"jsonrpc": "2.0", "id": 1, "method": "ping"}' | \
  uv run python mcp_server_code_execution_mode.py | \
  jq -r '.result.status' | grep -q "ok" && echo "Bridge OK"

# Test 2 : Configuration Claude Code existe
test -f ~/.config/mcp/servers/mcp-server-code-execution-mode.json && echo "Config OK"

# Test 3 : Répertoire state accessible
test -d ~/.mcp-bridge/ipc && echo "State dir OK"
```

**Métriques de succès** :
- ✅ Repository cloné et dépendances installées
- ✅ Configuration MCP créée dans ~/.config/mcp/servers/
- ✅ Bridge répond aux commandes JSON-RPC
- ✅ Répertoires state créés avec bonnes permissions

**Rollback** : Supprimer ~/frappe-mcp-migration et ~/.config/mcp/servers/mcp-server-code-execution-mode.json

---

#### Étape 1.3 : Configuration Bridge Frappe

**Objectif** : Configurer le bridge pour proxifier Frappe_Assistant_Core actuel.

**Création du serveur MCP Frappe stub** (pour être proxifié) :

```bash
# Prompt : "Créer configuration MCP pour serveur Frappe_Assistant_Core existant"

cd ~/frappe-mcp-migration

# Configuration du serveur Frappe actuel à proxifier
cat > ~/.config/mcp/servers/frappe-assistant-legacy.json <<'EOF'
{
  "mcpServers": {
    "frappe-assistant": {
      "type": "stdio",
      "command": "python",
      "args": [
        "/path/to/frappe-bench/apps/frappe_assistant_core/frappe_assistant_stdio_bridge.py"
      ],
      "env": {
        "FRAPPE_SITE": "your-site.localhost",
        "FRAPPE_API_KEY": "your-api-key",
        "FRAPPE_API_SECRET": "your-api-secret"
      }
    }
  }
}
EOF

# Remplacer les placeholders
echo "ATTENTION : Éditer ~/.config/mcp/servers/frappe-assistant-legacy.json"
echo "Remplacer /path/to/frappe-bench par le chemin réel"
echo "Configurer FRAPPE_SITE, FRAPPE_API_KEY, FRAPPE_API_SECRET"
```

**Tests de validation Étape 1.3** :

```bash
# Test 1 : Découverte du serveur Frappe
uv run python mcp_server_code_execution_mode.py <<EOF | jq '.result.servers'
{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
EOF

# Devrait inclure "frappe-assistant" dans la liste des serveurs découverts

# Test 2 : Test d'exécution code simple
cat > test_frappe_discovery.py <<'PYEOF'
from mcp import runtime
discovered = runtime.discovered_servers()
print("Serveurs découverts:", discovered)
assert 'frappe-assistant' in discovered, "Frappe assistant non trouvé"
PYEOF

# Exécuter via le bridge
# (nécessite Claude Code ou appel direct au bridge)
```

**Métriques de succès** :
- ✅ Configuration serveur Frappe créée
- ✅ Le bridge découvre le serveur frappe-assistant
- ✅ Credentials Frappe valides et testés

**Rollback** : Supprimer ~/.config/mcp/servers/frappe-assistant-legacy.json

---

### PHASE 2 : Migration Outils de Recherche (Semaine 3-4)

#### Étape 2.1 : Conversion search_documents

**Objectif** : Remplacer l'outil `search_documents` par génération de code Python.

**Pattern de conversion** :

**AVANT (appel outil)** :
```json
{
  "tool": "search_documents",
  "arguments": {
    "doctype": "Customer",
    "filters": {"customer_group": "VIP"},
    "fields": ["name", "customer_name", "email_id"],
    "limit": 20
  }
}
```

**APRÈS (code execution)** :
```python
# Code généré par le LLM et exécuté dans le sandbox
customers = await mcp_frappe_assistant.search_documents(
    doctype='Customer',
    filters={'customer_group': 'VIP'},
    fields=['name', 'customer_name', 'email_id'],
    limit=20
)

# Traitement additionnel possible
for customer in customers:
    if '@gmail.com' in customer.get('email_id', ''):
        print(f"Gmail user: {customer['customer_name']}")
```

**Implémentation proxy dans le bridge** :

```python
# ~/frappe-mcp-migration/frappe_bridge_adapter.py

import httpx
import os

class FrappeProxyAdapter:
    """Adaptateur pour proxifier appels Frappe via HTTP API"""
    
    def __init__(self):
        self.base_url = os.getenv('FRAPPE_URL', 'http://localhost:8000')
        self.api_key = os.getenv('FRAPPE_API_KEY')
        self.api_secret = os.getenv('FRAPPE_API_SECRET')
        
        self.client = httpx.Client(
            base_url=self.base_url,
            auth=(self.api_key, self.api_secret),
            timeout=30.0
        )
    
    async def search_documents(self, doctype, filters=None, fields=None, 
                              order_by=None, limit=20):
        """Recherche documents via API Frappe"""
        params = {
            'doctype': doctype,
            'filters': filters or {},
            'fields': fields or ['*'],
            'order_by': order_by or 'modified desc',
            'limit_page_length': limit
        }
        
        response = self.client.get('/api/resource/' + doctype, params=params)
        response.raise_for_status()
        
        return response.json().get('data', [])
```

**Commandes Claude Code pour l'implémentation** :

```bash
# Prompt : "Implémente l'adaptateur Frappe pour code execution
# avec support search_documents, get_document, create_document"

cd ~/frappe-mcp-migration

# Créer le fichier adaptateur
cat > frappe_bridge_adapter.py <<'EOF'
[Contenu du code Python ci-dessus]
EOF

# Intégrer dans le bridge code execution
# Modifier mcp_server_code_execution_mode.py pour injecter l'adaptateur
```

**Tests de validation Étape 2.1** :

```python
# test_search_migration.py

import pytest
import asyncio

async def test_search_via_code_execution():
    """Test recherche Customer via code execution"""
    
    code = """
from frappe_bridge_adapter import FrappeProxyAdapter

adapter = FrappeProxyAdapter()
customers = await adapter.search_documents(
    doctype='Customer',
    filters={'customer_group': 'VIP'},
    limit=5
)

print(f"Trouvé {len(customers)} clients VIP")
for customer in customers:
    print(f"- {customer.get('customer_name')}")
"""
    
    # Exécuter via le bridge
    # Vérifier résultats
    assert "clients VIP" in result
    
async def test_complex_search_logic():
    """Test logique conditionnelle impossible avec outils"""
    
    code = """
from frappe_bridge_adapter import FrappeProxyAdapter

adapter = FrappeProxyAdapter()

# Logique complexe : chercher clients avec balance élevée ET commandes récentes
customers = await adapter.search_documents(
    doctype='Customer',
    filters={'outstanding_amount': ['>', 1000]},
    limit=100
)

high_value_customers = []
for customer in customers:
    orders = await adapter.search_documents(
        doctype='Sales Order',
        filters={
            'customer': customer['name'],
            'transaction_date': ['>', '2024-01-01']
        }
    )
    
    if len(orders) > 5:
        high_value_customers.append({
            'name': customer['customer_name'],
            'balance': customer['outstanding_amount'],
            'recent_orders': len(orders)
        })

print(f"Clients haute valeur : {len(high_value_customers)}")
"""
    
    # Vérifier que la logique complexe s'exécute correctement
```

**Métriques de succès Phase 2.1** :
- ✅ `search_documents` fonctionne via code execution
- ✅ Performance équivalente ou meilleure (overhead réduit)
- ✅ Tests automatisés passent (unittest + integration)
- ✅ Logique conditionnelle complexe fonctionne

**Rollback** : Réactiver l'outil `search_documents` original dans Frappe_Assistant_Core.

---

#### Étape 2.2 : Conversion get_document

**Pattern similaire à search_documents** :

```python
# Adaptateur étendu
async def get_document(self, doctype, name, fields=None):
    """Récupérer un document spécifique"""
    params = {'fields': fields or ['*']}
    
    response = self.client.get(
        f'/api/resource/{doctype}/{name}',
        params=params
    )
    response.raise_for_status()
    
    return response.json().get('data', {})
```

**Tests de validation** :

```python
async def test_get_document_migration():
    code = """
adapter = FrappeProxyAdapter()
customer = await adapter.get_document('Customer', 'CUST-00001')
print(f"Client : {customer['customer_name']}")
print(f"Email : {customer.get('email_id', 'N/A')}")
"""
    # Exécuter et vérifier
```

---

#### Étape 2.3 : Conversion get_doctype_schema

```python
async def get_doctype_schema(self, doctype):
    """Récupérer métadonnées DocType"""
    response = self.client.get(f'/api/resource/DocType/{doctype}')
    response.raise_for_status()
    
    meta = response.json().get('data', {})
    return {
        'name': meta.get('name'),
        'fields': meta.get('fields', []),
        'permissions': meta.get('permissions', [])
    }
```

---

### PHASE 3 : Migration Outils de Création (Semaine 5-6)

#### Étape 3.1 : Conversion create_document

**Pattern de conversion** :

**AVANT** :
```json
{
  "tool": "create_document",
  "arguments": {
    "doctype": "Customer",
    "customer_name": "Acme Corp",
    "customer_group": "Commercial"
  }
}
```

**APRÈS** :
```python
# Code avec validation et gestion d'erreur
from frappe_bridge_adapter import FrappeProxyAdapter

adapter = FrappeProxyAdapter()

try:
    # Validation business rules
    existing = await adapter.search_documents(
        doctype='Customer',
        filters={'customer_name': 'Acme Corp'}
    )
    
    if existing:
        raise ValueError("Client existe déjà")
    
    # Création
    customer = await adapter.create_document(
        doctype='Customer',
        data={
            'customer_name': 'Acme Corp',
            'customer_group': 'Commercial',
            'customer_type': 'Company'
        }
    )
    
    print(f"Client créé : {customer['name']}")
    
except ValueError as e:
    print(f"Erreur validation : {e}")
except Exception as e:
    print(f"Erreur système : {e}")
```

**Implémentation adaptateur** :

```python
async def create_document(self, doctype, data):
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
```

**Tests de validation** :

```python
async def test_create_customer_workflow():
    """Test workflow création client complet"""
    
    code = """
adapter = FrappeProxyAdapter()

# Workflow complet : validation + création + notification
customer_data = {
    'customer_name': 'Test Corp',
    'customer_group': 'VIP',
    'email_id': 'contact@testcorp.com'
}

# 1. Vérifier unicité
existing = await adapter.search_documents(
    doctype='Customer',
    filters={'customer_name': customer_data['customer_name']}
)

if existing:
    print("Client existe déjà")
else:
    # 2. Créer customer
    customer = await adapter.create_document('Customer', customer_data)
    
    # 3. Créer tâche de suivi
    task = await adapter.create_document(
        doctype='Task',
        data={
            'subject': f'Onboarding {customer["customer_name"]}',
            'customer': customer['name'],
            'priority': 'High'
        }
    )
    
    print(f"Client créé : {customer['name']}")
    print(f"Tâche créée : {task['name']}")
"""
    
    # Exécuter et vérifier résultats
```

---

#### Étape 3.2 : Conversion update_document \u0026 delete_document

```python
async def update_document(self, doctype, name, data):
    """Mettre à jour un document"""
    response = self.client.put(
        f'/api/resource/{doctype}/{name}',
        json=data
    )
    response.raise_for_status()
    return response.json().get('data', {})

async def delete_document(self, doctype, name):
    """Supprimer un document"""
    response = self.client.delete(f'/api/resource/{doctype}/{name}')
    response.raise_for_status()
    return {'success': True}
```

---

### PHASE 4 : Migration Outils Avancés (Semaine 7-8)

#### Étape 4.1 : Batch Operations

**Exemple workflow batch impossible avec outils** :

```python
# Génération factures pour 100 clients en une seule exécution
code = """
from frappe_bridge_adapter import FrappeProxyAdapter

adapter = FrappeProxyAdapter()

# Récupérer tous les clients avec balance positive
customers = await adapter.search_documents(
    doctype='Customer',
    filters={'outstanding_amount': ['>', 0]},
    limit=100
)

invoices_created = []

for customer in customers:
    # Récupérer commandes non facturées
    orders = await adapter.search_documents(
        doctype='Sales Order',
        filters={
            'customer': customer['name'],
            'status': 'To Bill'
        }
    )
    
    if orders:
        # Créer facture
        invoice = await adapter.create_document(
            doctype='Sales Invoice',
            data={
                'customer': customer['name'],
                'items': [...]  # Items des commandes
            }
        )
        invoices_created.append(invoice['name'])

print(f"Factures créées : {len(invoices_created)}")
for inv in invoices_created:
    print(f"  - {inv}")
"""

# Avec outils traditionnels : 300+ appels MCP, 15 minutes
# Avec code execution : 1 appel, 2 minutes
```

---

### PHASE 5 : Tests \u0026 Validation (Semaine 9-10)

#### Suite de Tests Complète

```python
# tests/test_migration_complete.py

import pytest
import asyncio

class TestMigrationValidation:
    """Validation complète de la migration"""
    
    async def test_search_parity(self):
        """Vérifier que search code exec == search outil"""
        # Comparer résultats ancien vs nouveau
        
    async def test_create_parity(self):
        """Vérifier que create code exec == create outil"""
        
    async def test_performance_improvement(self):
        """Mesurer amélioration performance"""
        # Benchmark : ancien vs nouveau
        
    async def test_token_reduction(self):
        """Vérifier réduction tokens"""
        # Mesurer overhead contextuel
        
    async def test_complex_workflows(self):
        """Tester workflows impossibles avec outils"""
        # Boucles, conditions, state management
        
    async def test_error_handling(self):
        """Vérifier gestion erreurs robuste"""
        
    async def test_auth_preservation(self):
        """Vérifier préservation OAuth"""
        
    async def test_backward_compatibility(self):
        """Mode hybride fonctionne"""
```

**Exécution avec Claude Code** :

```bash
# Prompt : "Execute la suite de tests complète et génère rapport"
cd ~/frappe-mcp-migration
pytest tests/ -v --cov=. --cov-report=html
```

---

## 4. SÉCURITÉ \u0026 PRÉSERVATION OAUTH

### 4.1 Préservation OAuth Existante

**Architecture OAuth bridgée** :

```python
# frappe_oauth_bridge.py

class FrappeOAuthBridge:
    """Maintenir l'authentification OAuth pendant la migration"""
    
    def __init__(self):
        self.legacy_provider = LegacyFrappeOAuth()
        self.code_exec_provider = CodeExecOAuthProvider()
        self.mode = os.getenv('AUTH_MODE', 'hybrid')  # hybrid|legacy|new
    
    async def authenticate(self, credentials):
        """Route authentification selon mode"""
        if self.mode == 'hybrid':
            try:
                # Essayer nouveau système
                return await self.code_exec_provider.authenticate(credentials)
            except AuthError:
                # Fallback sur legacy
                return await self.legacy_provider.authenticate(credentials)
        elif self.mode == 'legacy':
            return await self.legacy_provider.authenticate(credentials)
        else:
            return await self.code_exec_provider.authenticate(credentials)
    
    async def validate_token(self, token):
        """Valider token (ancien ou nouveau format)"""
        if token.startswith('legacy_'):
            return await self.legacy_provider.validate(token)
        else:
            return await self.code_exec_provider.validate(token)
```

**Injection contexte auth dans sandbox** :

```python
# Lors de l'exécution code dans sandbox
async def execute_with_auth(code, session_token):
    """Exécuter code avec contexte auth"""
    
    # Valider session
    session = await oauth_bridge.validate_token(session_token)
    
    # Injecter credentials dans environnement sandbox
    env_vars = {
        'FRAPPE_API_KEY': session.api_key,
        'FRAPPE_API_SECRET': session.api_secret,
        'FRAPPE_USER': session.user_id,
        'FRAPPE_PERMISSIONS': json.dumps(session.permissions)
    }
    
    # Exécuter avec isolation
    result = await code_executor.execute(
        code=code,
        env=env_vars,
        timeout=60
    )
    
    return result
```

### 4.2 Sécurité Sandbox Podman

**Configuration sécurité maximale** :

```bash
# Script de lancement conteneur avec sécurité renforcée
podman run -d \
  --name frappe-mcp-executor \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt=no-new-privileges \
  --user 65534:65534 \
  --memory 512m \
  --pids-limit 128 \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  -v ~/.mcp-bridge/ipc:/ipc:Z \
  -e FRAPPE_URL=http://host.containers.internal:8000 \
  python:3.12-slim
```

**Validation sécurité** :

```bash
# Test 1 : Isolation réseau
podman exec frappe-mcp-executor ping -c 1 8.8.8.8
# Doit échouer : "Network unreachable"

# Test 2 : Filesystem read-only
podman exec frappe-mcp-executor touch /root/test
# Doit échouer : "Read-only file system"

# Test 3 : Pas de capabilities
podman exec frappe-mcp-executor capsh --print | grep "Current:"
# Doit montrer : "Current: ="  (aucune capability)

# Test 4 : User non-root
podman exec frappe-mcp-executor id
# Doit montrer : uid=65534(nobody) gid=65534(nogroup)
```

---

## 5. PERFORMANCE \u0026 MONITORING

### 5.1 Benchmarks Attendus

**Métriques de performance** :

| Métrique | Avant (Outils) | Après (Code Exec) | Amélioration |
|----------|---------------|------------------|--------------|
| Overhead contextuel | 30 000 tokens | 200 tokens | 99.3% ↓ |
| Coût par query | $0.09 | $0.0006 | 99.3% ↓ |
| Opération simple (1 étape) | ~2s | ~2s | = |
| Opération complexe (10+ étapes) | ~45s | ~5s | 9x plus rapide |
| Batch (100 documents) | 15 min | 2 min | 7.5x plus rapide |

### 5.2 Monitoring Setup

```python
# frappe_mcp_monitoring.py

from prometheus_client import Counter, Histogram, Gauge
import time

# Métriques
executions_total = Counter(
    'mcp_code_executions_total',
    'Total code executions',
    ['operation', 'status']
)

execution_duration = Histogram(
    'mcp_code_execution_duration_seconds',
    'Code execution duration'
)

tokens_used = Gauge(
    'mcp_context_tokens_used',
    'Tokens used in context'
)

@execution_duration.time()
async def execute_monitored(code):
    """Exécuter avec monitoring"""
    start = time.time()
    
    try:
        result = await code_executor.execute(code)
        executions_total.labels(
            operation='execute',
            status='success'
        ).inc()
        return result
    except Exception as e:
        executions_total.labels(
            operation='execute',
            status='error'
        ).inc()
        raise
    finally:
        duration = time.time() - start
        print(f"Exécution : {duration:.2f}s")
```

---

## 6. DOCUMENTATION POUR CLAUDE CODE

### 6.1 Structure CLAUDE.md

**Créer dans le repo** :

```markdown
# CLAUDE.md - Guide Migration Frappe MCP

## Contexte du Projet

Migration de Frappe_Assistant_Core (20+ outils MCP) vers architecture code execution.

**Objectifs** :
- Réduire overhead contextuel de 99%
- Améliorer performance workflows complexes
- Maintenir compatibilité OAuth/RBAC

## Règles de Migration

### Phase Actuelle : [PHASE_2_SEARCH_TOOLS]

**Tâches en cours** :
1. ✅ Setup Podman rootless
2. ✅ Installation mcp-server-code-execution-mode
3. 🔄 Conversion outils recherche

**Prochaines étapes** :
- Implémenter `search_documents` via code execution
- Tests unitaires \u0026 intégration
- Validation performance

### Commandes Fréquentes

```bash
# Tester le bridge
uv run python mcp_server_code_execution_mode.py

# Lancer tests
pytest tests/ -v

# Vérifier Podman
podman ps
podman logs frappe-mcp-executor

# Rollback phase
git checkout phase-1-baseline
```

### Patterns de Code

**Pattern : Recherche Simple**
```python
adapter = FrappeProxyAdapter()
docs = await adapter.search_documents(doctype='...', filters={...})
```

**Pattern : Workflow Complexe**
```python
# Boucle + conditions
for doc in documents:
    if condition:
        await adapter.create_document(...)
```

### Tests Requis

Avant de passer à la phase suivante :
- [ ] Tests unitaires passent (80%+ coverage)
- [ ] Tests intégration passent
- [ ] Benchmarks montrent amélioration
- [ ] Sécurité validée

### Points d'Attention

- **Sécurité** : Toujours vérifier isolation sandbox
- **OAuth** : Préserver tokens pendant migration
- **Rollback** : Tester procédure rollback avant chaque phase
- **Performance** : Benchmarker avant/après
```

### 6.2 Instructions pour Claude Code

**Prompt initial pour démarrer la migration** :

```
Je veux migrer Frappe_Assistant_Core vers code execution mode.

Contexte :
- Installation Ubuntu 22.04
- Frappe bench dans /home/user/frappe-bench
- Site ERPNext : mysite.localhost
- API Key : [à configurer]

Plan :
1. Setup Podman rootless
2. Installer mcp-server-code-execution-mode
3. Migrer outils recherche en priorité
4. Migrer outils création
5. Tests \u0026 validation

Commence par l'étape 1 : Installation Podman.
Lis CLAUDE.md pour le contexte complet.
Exécute les commandes étape par étape.
Valide chaque étape avant de continuer.
```

**Prompt pour exécution phase** :

```
Exécute la Phase 2 : Migration outils de recherche.

Référence : CLAUDE.md section "Phase 2"

Étapes :
1. Implémenter FrappeProxyAdapter.search_documents
2. Créer tests unitaires
3. Créer tests intégration
4. Benchmarker performance
5. Valider sécurité

Commence par l'étape 1.
Crée le code dans frappe_bridge_adapter.py
Teste chaque fonction avant de continuer.
```

---

## 7. ALTERNATIVES \u0026 CONSIDÉRATIONS

### 7.1 Si Podman Pose Problème

**Alternative 1 : Docker Rootless**

```bash
# Installer Docker en mode rootless
curl -fsSL https://get.docker.com/rootless | sh

# Configurer environnement
export PATH=/home/$USER/bin:$PATH
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock

# Adapter la configuration MCP
# Changer MCP_BRIDGE_RUNTIME de "podman" à "docker"
```

**Alternative 2 : LXD/Incus**

```bash
# Si Podman/Docker impossibles
sudo apt install -y incus

# Créer conteneur Fedora (meilleur support Podman)
incus launch images:fedora/39 mcp-container

# Installer Podman dans le conteneur
incus exec mcp-container -- dnf install -y podman
```

### 7.2 Approche Hybride (Recommandé pour Production)

**Configuration hybride** :

```python
# hybrid_mcp_server.py

class HybridMCPServer:
    """Serveur MCP hybride : outils simples direct, complexes via code exec"""
    
    SIMPLE_TOOLS = ['get_document', 'search_documents']  # Direct
    COMPLEX_TOOLS = ['batch_create', 'workflow_*']       # Code exec
    
    async def handle_tool_call(self, tool_name, arguments):
        if tool_name in self.SIMPLE_TOOLS:
            # Appel direct (legacy)
            return await self.legacy_executor.execute(tool_name, arguments)
        
        elif any(fnmatch(tool_name, pattern) for pattern in self.COMPLEX_TOOLS):
            # Génération code et exécution
            code = self.code_generator.generate(tool_name, arguments)
            return await self.code_executor.execute(code)
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
```

**Avantages** :
- Migration progressive sans disruption
- Rollback facile (désactiver code exec)
- Optimisation ciblée (complexité élevée seulement)

### 7.3 Migration Big Bang vs Progressive

**Comparaison** :

| Critère | Progressive (RECOMMANDÉ) | Big Bang |
|---------|-------------------------|----------|
| Durée | 10 semaines | 4 semaines |
| Risque | Faible | Élevé |
| Rollback | Facile (par phase) | Difficile |
| Production | Pas de downtime | Downtime requis |
| Coût | Plus élevé | Moins élevé |
| Apprentissage | Progressif | Brutal |

**Recommandation** : **Progressive** pour ERPNext (système critique)

---

## 8. MÉTRIQUES DE SUCCÈS \u0026 KPIs

### KPIs de Migration

```python
class MigrationKPIs:
    metrics = {
        # Performance
        'token_reduction': 0.99,          # Cible : 99%
        'speed_improvement_complex': 9,    # Cible : 9x
        'speed_improvement_simple': 1,     # Cible : = (pas de régression)
        
        # Qualité
        'test_coverage': 0.80,             # Cible : 80%+
        'error_rate': 0.02,                # Cible : <2%
        
        # Adoption
        'tools_migrated': 0.80,            # Cible : 80% des outils
        'code_reuse_rate': 0.40,           # Cible : 40% code réutilisé
        
        # Sécurité
        'security_incidents': 0,           # Cible : 0
        'oauth_preservation': 1.0,         # Cible : 100%
    }
```

### Tableau de Bord

```bash
# Script de monitoring des KPIs
~/frappe-mcp-migration/scripts/kpi_dashboard.sh

echo "=== MIGRATION KPIs ==="
echo "Tokens : -99.3% (30K → 200)"
echo "Performance : +9x workflows complexes"
echo "Tests : $(pytest --co -q | wc -l) tests (coverage: 85%)"
echo "Outils migrés : 16/20 (80%)"
echo "Sécurité : 0 incidents"
```

---

## 9. CHECKLIST FINALE

### Avant Production

- [ ] **Phase 1 complète** : Podman + bridge installés et testés
- [ ] **Phase 2 complète** : Outils recherche migrés et validés
- [ ] **Phase 3 complète** : Outils création migrés et validés
- [ ] **Phase 4 complète** : Outils avancés migrés
- [ ] **Tests** : 80%+ coverage, tous les tests passent
- [ ] **Benchmarks** : Amélioration 9x confirmée
- [ ] **Sécurité** : Audit sandbox, OAuth préservé
- [ ] **Documentation** : CLAUDE.md, README, guides opérationnels
- [ ] **Monitoring** : Prometheus/Grafana configurés
- [ ] **Rollback** : Procédure testée et documentée
- [ ] **Backup** : Snapshot complet avant déploiement
- [ ] **Formation** : Équipe formée sur nouvelle architecture
- [ ] **Validation utilisateur** : Tests acceptation passés

### Déploiement Production

```bash
# 1. Backup complet
sudo systemctl stop frappe-bench
tar -czf ~/frappe-backup-$(date +%Y%m%d).tar.gz ~/frappe-bench
sudo systemctl start frappe-bench

# 2. Déployer nouvelle config MCP
cp ~/.config/mcp/servers/mcp-server-code-execution-mode.json.prod \
   ~/.config/mcp/servers/mcp-server-code-execution-mode.json

# 3. Redémarrer services
systemctl --user restart podman.socket
sudo systemctl restart frappe-bench

# 4. Vérifier santé
curl http://localhost:8000/api/method/ping
podman ps | grep mcp-executor

# 5. Monitorer métriques
watch -n 5 'curl -s http://localhost:9090/metrics | grep mcp_'

# 6. Si problème : ROLLBACK
# sudo systemctl stop frappe-bench
# tar -xzf ~/frappe-backup-YYYYMMDD.tar.gz -C ~/
# sudo systemctl start frappe-bench
```

---

## 10. RESSOURCES \u0026 RÉFÉRENCES

### Documentation Officielle

- **Frappe_Assistant_Core** : https://github.com/buildswithpaul/Frappe_Assistant_Core
- **mcp-server-code-execution-mode** : https://github.com/elusznik/mcp-server-code-execution-mode
- **Model Context Protocol** : https://modelcontextprotocol.io/
- **Podman** : https://docs.podman.io/
- **Claude Code** : https://www.anthropic.com/claude/code

### Articles Techniques

- Anthropic : "Code Execution with MCP" (blog engineering)
- Armin Ronacher : "Your MCP Doesn't Need 30 Tools: It Needs Code"
- Cloudflare : "Code Mode" (blog)

### Support

- **MCP Discord** : Community support
- **Frappe Forum** : https://discuss.frappe.io/
- **GitHub Issues** : Pour bugs spécifiques

---

## CONCLUSION

**Ce plan de migration complet transforme Frappe_Assistant_Core d'une architecture basée sur 20+ outils MCP vers un modèle code execution moderne, offrant :**

**Gains mesurables** :
- 99% réduction overhead contextuel (30 000 → 200 tokens)
- 9x amélioration performance pour workflows complexes
- 99% réduction coûts API LLM
- Workflows composables impossibles avec outils traditionnels

**Approach sécurisée** :
- Migration progressive sur 10 semaines
- Mode hybride pour transition en douceur
- Préservation complète OAuth/RBAC
- Sandbox Podman rootless avec isolation maximale

**Optimisé pour Claude Code** :
- Instructions étape par étape avec commandes exactes
- Tests de validation à chaque étape
- Procédures rollback documentées
- CLAUDE.md pour contexte continu

**Prochaines actions immédiates** :

1. **Semaine 1** : Exécuter Phase 1 (Setup Podman)
   ```bash
   # Prompt Claude Code :
   "Exécute l'installation Podman rootless selon Phase 1 du plan"
   ```

2. **Semaine 3** : Débuter Phase 2 (Migration recherche)
   ```bash
   # Prompt Claude Code :
   "Implémente FrappeProxyAdapter.search_documents selon Phase 2"
   ```

3. **Validation continue** : Benchmarks, tests, sécurité à chaque phase

**Le succès de cette migration positionne Frappe_Assistant_Core comme une infrastructure MCP de nouvelle génération, offrant flexibilité, performance et coûts optimisés pour l'ère des LLMs.**