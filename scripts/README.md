# Scripts d'Installation Phase 1

Ce dossier contient les scripts d'installation et de configuration pour la Phase 1 du projet d'intégration **mcp-server-code-execution-mode** avec **Frappe Assistant Core**.

## 📁 Scripts Disponibles

### 1. `install_phase1.sh`
**Installation complète de l'environnement**

Ce script installe et configure tous les composants nécessaires :
- Vérification Python (≥3.11, idéalement 3.14)
- Installation de uv (gestionnaire de paquets Python)
- Installation du container runtime (Podman ou Docker)
- Configuration des user namespaces (Podman)
- Téléchargement de l'image Python
- Création des répertoires de configuration

**Usage:**
```bash
./scripts/install_phase1.sh
```

**Prérequis:**
- Linux (Ubuntu/Debian recommandé) ou macOS
- Accès sudo (pour installation système)
- Connexion internet

**Durée:** ~5-10 minutes (selon connexion)

---

### 2. `setup_bridge.sh`
**Configuration du bridge MCP code execution**

Configure le bridge mcp-server-code-execution-mode :
- Vérifie Python 3.14+ (ou adapte pour 3.12+)
- Installe les dépendances via uv
- Crée la configuration MCP
- Teste le bridge en mode standalone

**Usage:**
```bash
./scripts/setup_bridge.sh
```

**Prérequis:**
- `install_phase1.sh` exécuté avec succès
- Container runtime installé et fonctionnel

**Durée:** ~2-3 minutes

---

### 3. `setup_frappe_config.sh`
**Configuration Frappe Assistant**

Configure la connexion à votre instance Frappe :
- Collecte les informations Frappe (site, URL, API keys)
- Teste la connexion
- Crée la configuration MCP pour Frappe Assistant
- Génère le fichier .env avec les credentials
- Crée l'adaptateur Frappe (`frappe_bridge_adapter.py`)

**Usage:**
```bash
./scripts/setup_frappe_config.sh
```

**Prérequis:**
- Instance Frappe/ERPNext accessible
- API Key et Secret générés (voir ci-dessous)

**Durée:** ~2 minutes (interactif)

#### Génération des API Keys Frappe

1. Se connecter à Frappe
2. Aller dans **User > Votre Profil > API Access**
3. Cliquer sur **Generate Keys**
4. Copier API Key et API Secret

---

### 4. `test_phase1.sh`
**Validation complète Phase 1**

Exécute une suite de tests pour valider l'installation :
- ✅ Python version (≥3.11)
- ✅ uv installé
- ✅ Container runtime (Podman/Docker)
- ✅ Image Python disponible
- ✅ Runtime fonctionnel
- ✅ Répertoires créés
- ✅ Configurations MCP valides
- ✅ Dépendances bridge installées
- ✅ Adaptateur Frappe créé

**Usage:**
```bash
./scripts/test_phase1.sh
```

**Durée:** ~1 minute

**Sortie:**
- Liste des tests PASS/FAIL
- Résumé avec nombre de succès/échecs
- Instructions pour corriger les erreurs

---

## 🚀 Procédure d'Installation Complète

### Installation en 4 étapes

```bash
# 1. Installation environnement
cd /path/to/Frappe_Assistant_Core
./scripts/install_phase1.sh

# 2. Configuration bridge
./scripts/setup_bridge.sh

# 3. Configuration Frappe (interactif)
./scripts/setup_frappe_config.sh

# 4. Validation
./scripts/test_phase1.sh
```

### Résultat attendu

Après exécution complète, vous devriez avoir :

```
✅ Python 3.14+ (ou 3.12+)
✅ uv installé
✅ Podman ou Docker opérationnel
✅ Image python:3.14-slim téléchargée
✅ ~/.config/mcp/servers/mcp-server-code-execution-mode.json
✅ ~/.config/mcp/servers/frappe-assistant.json
✅ ~/.mcp-bridge/{ipc,state} créés
✅ frappe_bridge_adapter.py créé
✅ .env avec credentials Frappe
```

---

## 🔧 Dépannage

### Problème : "Python version too old"

**Solution:** Installer Python 3.14

```bash
# Via pyenv (recommandé)
curl https://pyenv.run | bash
pyenv install 3.14.0
pyenv global 3.14.0

# Ou télécharger depuis python.org
```

### Problème : "Container runtime not found"

**Solution:** Réexécuter `install_phase1.sh` et choisir le runtime

```bash
./scripts/install_phase1.sh
# Choisir Podman (1) ou Docker (2) quand demandé
```

### Problème : "Cannot connect to Frappe"

**Solutions:**
1. Vérifier que Frappe est démarré : `bench start` ou service actif
2. Vérifier l'URL (http://localhost:8000 par défaut)
3. Tester manuellement : `curl http://localhost:8000/api/method/ping`

### Problème : "API authentication failed"

**Solutions:**
1. Régénérer les API keys dans Frappe
2. Vérifier copier-coller (pas d'espaces)
3. Tester avec curl :
   ```bash
   curl -H "Authorization: token API_KEY:API_SECRET" \
        http://localhost:8000/api/method/ping
   ```

### Problème : "Permission denied" (Podman)

**Solution:** Configurer les user namespaces

```bash
echo "$(whoami):100000:65536" | sudo tee -a /etc/subuid
echo "$(whoami):100000:65536" | sudo tee -a /etc/subgid
podman system migrate
```

---

## 📋 Fichiers Générés

### Configuration MCP

**`~/.config/mcp/servers/mcp-server-code-execution-mode.json`**
```json
{
  "mcpServers": {
    "mcp-server-code-execution-mode": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "/path/to/mcp_server_code_execution_mode.py"],
      "env": {
        "MCP_BRIDGE_RUNTIME": "podman",
        "MCP_BRIDGE_IMAGE": "python:3.14-slim",
        ...
      }
    }
  }
}
```

**`~/.config/mcp/servers/frappe-assistant.json`**
```json
{
  "mcpServers": {
    "frappe-assistant": {
      "type": "stdio",
      "command": "python3",
      "args": ["/path/to/frappe_assistant_stdio_bridge.py"],
      "env": {
        "FRAPPE_SITE": "mysite.localhost",
        "FRAPPE_URL": "http://localhost:8000",
        "FRAPPE_API_KEY": "...",
        "FRAPPE_API_SECRET": "..."
      }
    }
  }
}
```

### Fichiers Projet

**`.env`** (NE PAS COMMITTER)
```bash
FRAPPE_SITE=mysite.localhost
FRAPPE_URL=http://localhost:8000
FRAPPE_API_KEY=...
FRAPPE_API_SECRET=...
```

**`frappe_bridge_adapter.py`**
- Adaptateur Python pour appeler APIs Frappe
- Utilisé dans le code exécuté par le sandbox
- Méthodes : `search_documents`, `get_document`, `create_document`, etc.

---

## 🔐 Sécurité

### Credentials API

- ⚠️ **NE JAMAIS** committer le fichier `.env`
- ⚠️ Les API keys donnent accès complet à Frappe
- ✅ Utiliser des API keys dédiées (pas admin)
- ✅ Révoquer les keys inutilisées
- ✅ `.env` est dans `.gitignore`

### Container Runtime

- ✅ Rootless par défaut (Podman)
- ✅ Network isolation (`--network none`)
- ✅ User non-privilégié (UID 65534)
- ✅ Filesystem read-only
- ✅ Capabilities droppées

---

## 📚 Documentation

- **Plan complet** : [`../PLAN_EXECUTION.md`](../PLAN_EXECUTION.md)
- **Migration détaillée** : [`../Plan_migration.md`](../Plan_migration.md)
- **Guide bridge** : [`../mcp-server-code-execution-mode/README.md`](../mcp-server-code-execution-mode/README.md)

---

## ✅ Checklist Phase 1

Avant de passer à la Phase 2, vérifier :

- [ ] `./scripts/test_phase1.sh` retourne 0 tests échoués
- [ ] Container runtime peut exécuter `alpine echo "test"`
- [ ] Configuration MCP bridge créée et valide
- [ ] Configuration Frappe Assistant créée
- [ ] Connexion Frappe testée et OK
- [ ] Adaptateur Frappe créé (`frappe_bridge_adapter.py`)
- [ ] `.env` créé et dans `.gitignore`

Si tous les items sont ✅, vous êtes prêt pour la **Phase 2 : Proof of Concept** !

---

## 🆘 Support

**Problèmes d'installation :**
- Consulter le dépannage ci-dessus
- Lire `PLAN_EXECUTION.md` section correspondante
- Vérifier les logs des scripts

**Prochaines étapes :**
- Phase 2 : Créer un POC avec découverte serveurs
- Phase 3 : Migrer tous les outils Frappe
- Phase 4 : Tests et validation

---

**Version:** 1.0
**Date:** 2025-11-17
**Auteur:** Claude Code Assistant
**Licence:** AGPL-3.0 (même que Frappe Assistant Core)
