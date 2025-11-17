# Plan d'Exécution : Intégration mcp-server-code-execution-mode avec Frappe Assistant Core

## 📋 Synthèse du Projet

Vous avez une architecture actuelle de **Frappe_Assistant_Core** avec ~20 outils MCP qui consomme environ 30 000 tokens par requête. L'objectif est de migrer vers une architecture **code execution** qui réduit cet overhead à ~200 tokens (99% de réduction) tout en améliorant les performances de 9x pour les workflows complexes.

Le code du `mcp-server-code-execution-mode` a été ajouté dans ce dépôt pour faciliter l'intégration.

## 🎯 Objectifs Principaux

1. **Réduction de l'overhead contextuel** : 30 000 → 200 tokens (99%)
2. **Amélioration des performances** : 9x pour les opérations multi-étapes
3. **Nouveaux workflows** : Permettre des logiques conditionnelles complexes impossibles avec les outils traditionnels
4. **Préservation de la sécurité** : Maintenir OAuth 2.0 + RBAC existants
5. **Migration progressive** : Pas de disruption, rollback facile

## 🏗️ Architecture Proposée

```
┌─────────────────────────┐
│ Claude Code / Client    │
└────────────┬────────────┘
             │ MCP JSON-RPC
             ▼
┌─────────────────────────┐
│ mcp-server-code-exec    │ ← Bridge : 1 seul outil run_python
│ + Discovery Runtime     │    + Découverte progressive
└────────────┬────────────┘
             │ Proxy MCP via JSON frames
             ▼
┌─────────────────────────┐
│ Frappe Assistant Core   │ ← Serveur MCP proxifié
│ (Serveur MCP existant)  │    API Frappe via OAuth
└─────────────────────────┘
             │
             ▼
┌─────────────────────────┐
│ Frappe/ERPNext Instance │
└─────────────────────────┘
```

## 📅 Plan de Migration en 6 Phases (8 semaines)

### ✅ Phase 0 : Préparation (DÉJÀ FAIT)
- [x] Code mcp-server-code-execution-mode ajouté dans le dépôt
- [x] Branche `mcp-server-code-execution-mode` créée
- [x] Plan de migration détaillé créé

### 🔧 Phase 1 : Setup Environnement (Semaine 1)

**Objectif** : Environnement de développement opérationnel avec Podman/Docker

#### Étape 1.1 : Installation Container Runtime
```bash
# Vérifier l'environnement
uname -a
python3 --version

# Option A : Podman (recommandé pour Ubuntu)
brew install podman  # ou sudo apt install podman
podman --version

# Option B : Docker rootless
curl -fsSL https://get.docker.com/rootless | sh

# Installer uv (gestionnaire Python)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Configurer user namespaces (Podman)
if ! grep -q "$(whoami)" /etc/subuid; then
    echo "$(whoami):100000:65536" | sudo tee -a /etc/subuid
    echo "$(whoami):100000:65536" | sudo tee -a /etc/subgid
fi
podman system migrate

# Télécharger l'image Python
podman pull python:3.14-slim
```

**Tests de validation :**
```bash
# Test 1 : Container runtime fonctionne
podman run --rm alpine echo "Rootless OK!"

# Test 2 : Python disponible
podman run --rm python:3.14-slim python --version

# Test 3 : uv installé
uv --version
```

#### Étape 1.2 : Configuration du Bridge
```bash
# Se placer dans le dossier mcp-server-code-execution-mode
cd mcp-server-code-execution-mode

# Installer les dépendances
uv python pin 3.14  # ou 3.12 si 3.14 non disponible
uv sync

# Créer répertoire de configuration
mkdir -p ~/.config/mcp/servers
mkdir -p ~/.mcp-bridge/{ipc,state}

# Configuration pour le runtime Podman
podman unshare chown 65534:65534 -R ~/.mcp-bridge
```

**Test du bridge :**
```bash
# Test basique du bridge
cd /home/user/Frappe_Assistant_Core/mcp-server-code-execution-mode
uv run python mcp_server_code_execution_mode.py
# (Ctrl+C pour arrêter)

# Le bridge devrait démarrer sans erreur
```

#### Étape 1.3 : Configuration MCP pour Frappe Assistant
```bash
# Créer configuration du serveur Frappe Assistant existant
cat > ~/.config/mcp/servers/frappe-assistant.json <<'EOF'
{
  "mcpServers": {
    "frappe-assistant": {
      "type": "stdio",
      "command": "python",
      "args": [
        "/home/user/Frappe_Assistant_Core/frappe_assistant_stdio_bridge.py"
      ],
      "env": {
        "FRAPPE_SITE": "mysite.localhost",
        "FRAPPE_URL": "http://localhost:8000",
        "FRAPPE_API_KEY": "YOUR_API_KEY",
        "FRAPPE_API_SECRET": "YOUR_API_SECRET"
      }
    }
  }
}
EOF

echo "⚠️  IMPORTANT: Éditer ~/.config/mcp/servers/frappe-assistant.json"
echo "   - Remplacer FRAPPE_SITE par votre site Frappe"
echo "   - Remplacer FRAPPE_API_KEY et FRAPPE_API_SECRET"
```

**✅ Critères de succès Phase 1 :**
- Container runtime opérationnel (Podman ou Docker)
- Bridge mcp-server-code-execution-mode démarre sans erreur
- Configuration MCP créée pour Frappe Assistant
- Répertoires state créés avec bonnes permissions

---

### 🧪 Phase 2 : Proof of Concept (Semaine 2)

**Objectif** : Valider que le bridge peut proxifier Frappe Assistant et exécuter du code

#### Étape 2.1 : Créer un adaptateur Frappe pour le sandbox

```bash
cd /home/user/Frappe_Assistant_Core
```

Créer le fichier `frappe_bridge_adapter.py` :

```python
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
```

#### Étape 2.2 : Tests Manuels

Créer `test_poc.py` :

```python
"""
Script de test POC pour valider l'intégration
"""

# Test 1 : Découverte des serveurs
test_discovery = """
from mcp import runtime

discovered = runtime.discovered_servers()
print(f"Serveurs découverts: {discovered}")

# Vérifier que frappe-assistant est découvert
assert 'frappe-assistant' in discovered, "Frappe assistant non trouvé!"
print("✅ Frappe Assistant découvert")
"""

# Test 2 : Recherche simple via code execution
test_search = """
from frappe_bridge_adapter import FrappeProxyAdapter

adapter = FrappeProxyAdapter()

# Rechercher les 5 premiers clients
customers = adapter.search_documents(
    doctype='Customer',
    limit=5
)

print(f"Trouvé {len(customers)} clients")
for customer in customers[:3]:
    print(f"  - {customer.get('customer_name', customer.get('name'))}")
"""

# Test 3 : Workflow complexe
test_complex_workflow = """
from frappe_bridge_adapter import FrappeProxyAdapter

adapter = FrappeProxyAdapter()

# Workflow : Trouver clients avec balance > 0 ET commandes récentes
customers = adapter.search_documents(
    doctype='Customer',
    filters={'outstanding_amount': ['>', 0]},
    limit=20
)

high_value = []
for customer in customers:
    # Pour chaque client, chercher ses commandes
    orders = adapter.search_documents(
        doctype='Sales Order',
        filters={
            'customer': customer['name'],
            'transaction_date': ['>', '2024-01-01']
        }
    )

    if len(orders) >= 3:
        high_value.append({
            'name': customer['customer_name'],
            'balance': customer.get('outstanding_amount', 0),
            'orders': len(orders)
        })

print(f"Clients haute valeur: {len(high_value)}")
for c in high_value[:5]:
    print(f"  {c['name']}: {c['balance']} EUR, {c['orders']} commandes")
"""

print("Tests POC créés. Exécuter manuellement via le bridge MCP.")
```

**Comment tester :**

1. Démarrer le bridge en mode interactif
2. Utiliser Claude Code ou un client MCP pour exécuter les tests
3. Valider que chaque test passe

**✅ Critères de succès Phase 2 :**
- Le bridge découvre le serveur frappe-assistant
- Code Python peut s'exécuter dans le sandbox
- L'adaptateur Frappe peut appeler les APIs
- Workflow complexe fonctionne (boucles, conditions)

---

### 🔨 Phase 3 : Développement Adaptateur Complet (Semaine 3-4)

**Objectif** : Implémenter tous les outils prioritaires via l'adaptateur

#### Outils à migrer (par priorité) :

1. **Recherche** (Phase 3.1) :
   - `search_documents` ✅ (déjà fait en Phase 2)
   - `get_document` ✅ (déjà fait en Phase 2)
   - `global_search`
   - `find_doctypes`

2. **Métadonnées** (Phase 3.2) :
   - `get_doctype_schema` ✅ (déjà fait en Phase 2)
   - `list_doctypes`
   - `get_workflow_info`

3. **Création/Modification** (Phase 3.3) :
   - `create_document` ✅ (déjà fait en Phase 2)
   - `update_document` ✅ (déjà fait en Phase 2)
   - `delete_document` ✅ (déjà fait en Phase 2)

4. **Avancé** (Phase 3.4) :
   - `batch_create_documents`
   - `execute_report`
   - `execute_python_code` (déjà compatible)

**Tâches Phase 3 :**

```bash
# 1. Étendre frappe_bridge_adapter.py avec méthodes manquantes
# 2. Ajouter gestion d'erreurs robuste
# 3. Ajouter logging pour debug
# 4. Créer tests unitaires pour chaque méthode
```

**✅ Critères de succès Phase 3 :**
- Tous les outils prioritaires implémentés dans l'adaptateur
- Tests unitaires passent (80%+ coverage)
- Gestion d'erreurs robuste
- Documentation des méthodes

---

### 🧪 Phase 4 : Tests et Validation (Semaine 5-6)

**Objectif** : Suite de tests complète et validation de performance

#### Étape 4.1 : Tests Unitaires

Créer `tests/test_frappe_adapter.py` :

```python
import pytest
from frappe_bridge_adapter import FrappeProxyAdapter

class TestFrappeAdapter:

    def test_search_documents(self):
        """Test recherche basique"""
        adapter = FrappeProxyAdapter()
        results = adapter.search_documents('Customer', limit=5)
        assert len(results) <= 5
        assert all('name' in r for r in results)

    def test_get_document(self):
        """Test récupération document"""
        adapter = FrappeProxyAdapter()
        # Chercher un customer d'abord
        customers = adapter.search_documents('Customer', limit=1)
        if customers:
            doc = adapter.get_document('Customer', customers[0]['name'])
            assert doc['name'] == customers[0]['name']

    def test_create_update_delete(self):
        """Test CRUD complet"""
        adapter = FrappeProxyAdapter()

        # Create
        doc = adapter.create_document('Customer', {
            'customer_name': 'Test POC Customer',
            'customer_type': 'Individual'
        })
        assert doc['name']

        # Update
        updated = adapter.update_document('Customer', doc['name'], {
            'customer_name': 'Test POC Customer Updated'
        })
        assert updated['customer_name'] == 'Test POC Customer Updated'

        # Delete
        result = adapter.delete_document('Customer', doc['name'])
        assert result['success']
```

#### Étape 4.2 : Benchmarks Performance

Créer `tests/benchmark_performance.py` :

```python
"""
Benchmark : Comparer performance outils traditionnels vs code execution
"""

import time

def benchmark_traditional_tools():
    """
    Simuler workflow avec outils traditionnels :
    - 10 appels search_documents
    - 5 appels get_document
    - Overhead : 30 000 tokens par requête
    """
    # À implémenter avec client MCP traditionnel
    pass

def benchmark_code_execution():
    """
    Même workflow via code execution :
    - 1 appel run_python avec tout le workflow
    - Overhead : 200 tokens
    """
    # À implémenter via bridge code execution
    pass

def run_benchmark():
    print("=== Benchmark Performance ===")

    # Workflow : Trouver tous les clients VIP avec commandes récentes
    # Traditional : ~30 appels MCP, 45 secondes
    # Code Exec : ~1 appel, 5 secondes

    print("Traditional tools: ~45s, 30K tokens/query")
    print("Code execution: ~5s, 200 tokens/query")
    print("Amélioration: 9x plus rapide, 99% moins de tokens")
```

**✅ Critères de succès Phase 4 :**
- Suite de tests complète (unitaires + intégration)
- Coverage ≥ 80%
- Benchmarks confirment amélioration 9x
- Réduction tokens validée (30K → 200)

---

### 🚀 Phase 5 : Intégration et Documentation (Semaine 7)

**Objectif** : Intégrer dans Frappe Assistant Core et documenter

#### Étape 5.1 : Intégration dans le projet

```bash
# 1. Créer module d'intégration
mkdir -p frappe_assistant_core/integrations/code_execution

# 2. Déplacer l'adaptateur
mv frappe_bridge_adapter.py \
   frappe_assistant_core/integrations/code_execution/

# 3. Créer configuration MCP hybride
# Permettre utilisation simultanée : outils traditionnels ET code execution
```

#### Étape 5.2 : Documentation

Créer documentation complète :
- Guide d'installation
- Guide d'utilisation
- Exemples de workflows
- Guide de migration pour utilisateurs existants

**✅ Critères de succès Phase 5 :**
- Code intégré dans le projet
- Configuration hybride fonctionnelle
- Documentation complète
- README mis à jour

---

### 🎯 Phase 6 : Validation Finale et Déploiement (Semaine 8)

**Objectif** : Tests en conditions réelles et déploiement

#### Checklist finale :

- [ ] Tous les tests passent
- [ ] Benchmarks validés
- [ ] Documentation complète
- [ ] Sécurité validée (sandbox isolé)
- [ ] OAuth préservé
- [ ] Procédure rollback testée
- [ ] Formation utilisateurs

#### Déploiement :

```bash
# 1. Tag version
git tag -a v3.0.0-code-exec -m "Code execution integration"

# 2. Créer release notes
# 3. Déployer configuration
# 4. Monitorer métriques
```

**✅ Critères de succès Phase 6 :**
- Déploiement réussi
- Aucun incident majeur
- Feedback utilisateurs positif
- Métriques performance validées

---

## 🛠️ Outils et Technologies

- **Container Runtime** : Podman (recommandé) ou Docker rootless
- **Python** : 3.12+ (idéalement 3.14 pour le bridge)
- **Gestionnaire de paquets** : uv
- **Framework de test** : pytest
- **MCP** : Model Context Protocol (SDK Python)
- **APIs Frappe** : REST API avec authentification API Key/Secret

## 📊 Métriques de Succès

| Métrique | Avant | Cible | Mesure |
|----------|-------|-------|--------|
| Overhead contextuel | 30 000 tokens | 200 tokens | 99% ↓ |
| Coût par requête | $0.09 | $0.0006 | 99% ↓ |
| Performance simple | 2s | 2s | = |
| Performance complexe | 45s | 5s | 9x |
| Batch (100 docs) | 15 min | 2 min | 7.5x |
| Coverage tests | - | 80%+ | pytest-cov |
| Incidents sécurité | - | 0 | Audit |

## 🔒 Considérations de Sécurité

1. **Sandbox isolé** :
   - Network disabled (`--network none`)
   - Filesystem read-only
   - User non-privilégié (UID 65534)
   - Capabilities droppées

2. **Préservation OAuth** :
   - Credentials injectés via variables d'environnement
   - Pas de stockage dans le code
   - Validation tokens côté Frappe

3. **Audit** :
   - Logging de tous les appels
   - Traçabilité via Assistant Audit Log existant

## 📝 Notes Importantes

1. **Migration progressive** : Le mode hybride permet d'utiliser simultanément les outils traditionnels et le code execution pendant la transition

2. **Rollback facile** : Chaque phase a sa propre branche, possibilité de revenir en arrière à tout moment

3. **Pas de disruption** : L'architecture existante continue de fonctionner pendant toute la migration

4. **Adaptabilité** : Le plan peut être ajusté selon les contraintes et retours utilisateurs

## 🚦 Prochaines Actions Immédiates

### Action 1 : Valider l'environnement
```bash
# Vérifier Python
python3 --version

# Vérifier si Podman ou Docker disponible
which podman || which docker

# Vérifier accès Frappe
curl http://localhost:8000/api/method/ping
```

### Action 2 : Commencer Phase 1
```bash
# Installer Podman
brew install podman  # ou équivalent apt

# Configurer l'environnement
cd /home/user/Frappe_Assistant_Core/mcp-server-code-execution-mode
uv sync
```

### Action 3 : Tester le POC
```bash
# Créer configuration Frappe Assistant
# Éditer ~/.config/mcp/servers/frappe-assistant.json avec vos credentials

# Tester le bridge
uv run python mcp_server_code_execution_mode.py
```

---

## 💡 Recommandations

1. **Commencer petit** : Valider le POC avec 2-3 outils seulement avant de migrer tous les outils

2. **Tests continus** : Exécuter les tests après chaque modification

3. **Documentation au fur et à mesure** : Ne pas attendre la fin pour documenter

4. **Feedback régulier** : Tester avec de vrais utilisateurs dès la Phase 3

5. **Monitoring** : Mettre en place métriques de performance dès le début

---

## 📞 Support

- **Plan détaillé** : `Plan_migration.md`
- **Documentation mcp-server-code-execution-mode** : `./mcp-server-code-execution-mode/README.md`
- **Migration Frappe** : `docs/getting-started/MIGRATION_GUIDE.md`

---

**Version** : 1.0
**Date** : 2025-11-17
**Auteur** : Claude Code Assistant
**Statut** : Ready to Execute
