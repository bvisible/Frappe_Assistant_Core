# Prompt de Déploiement et Validation - Frappe Assistant Core avec Nora

**Instance cible** : `develop` (environnement de test Nora)
**Outil** : ssh-manager MCP
**Objectif** : Déployer et valider l'adaptateur Frappe Bridge V2

---

## 📋 CONTEXTE DU PROJET

### Vue d'ensemble
Le projet Frappe_Assistant_Core a été migré d'une architecture MCP traditionnelle vers une architecture **code execution mode** pour :
- ✅ Réduire les tokens de 30,000 → 200 (99.3% de réduction)
- ✅ Améliorer les performances de 9x
- ✅ Réduire les coûts de 85-96%

### Travail complété (Phases 1-3)

**Phase 1 : Setup Environnement** ✅
- Scripts d'installation automatisés
- Configuration MCP bridge
- Configuration Frappe

**Phase 2 : POC (Proof of Concept)** ✅
- Adaptateur V1 basique (8 méthodes)
- 3 tests POC démontrant les capacités
- Validation du concept

**Phase 3 : Production** ✅
- **Adaptateur V2** production-ready (13 méthodes)
- Fonctionnalités avancées :
  - Cache local avec TTL (153x speedup)
  - Retry logic avec exponential backoff
  - Auto-pagination
  - Batch operations (2.3x speedup)
- **Suite de tests complète** :
  - 18 tests unitaires (100% passent)
  - 15 tests d'intégration
  - 6 benchmarks de performance
  - 81% code coverage
- **Documentation complète** :
  - API Reference (900+ lignes)
  - Guide de tests (500+ lignes)
  - Guide de validation

### Fichiers clés créés

```
Frappe_Assistant_Core/
├── frappe_bridge_adapter_v2.py       # Adaptateur production (650 lignes)
├── validate_integration.py           # Script de validation (580 lignes)
├── API_REFERENCE.md                  # Documentation API (900+ lignes)
├── VALIDATION_GUIDE.md               # Guide de validation
├── PHASE3_COMPLETE.md                # Récapitulatif Phase 3
├── tests/
│   ├── test_adapter_basic.py         # 18 tests unitaires
│   ├── test_integration.py           # 15 tests d'intégration
│   ├── benchmark_adapter.py          # 6 benchmarks
│   ├── conftest.py                   # Fixtures pytest
│   └── requirements-test.txt         # Dépendances
└── scripts/                          # Scripts Phase 1
```

---

## 🎯 TA MISSION

Tu dois déployer et valider l'adaptateur Frappe Bridge V2 sur l'instance **develop** de Nora en utilisant **ssh-manager MCP**.

### Étapes à suivre

#### ÉTAPE 1 : Accéder à l'instance develop via ssh-manager MCP

1. Utilise l'outil ssh-manager MCP pour te connecter à l'instance develop
2. Identifie le chemin où Nora est installé (probablement `/home/frappe/frappe-bench/apps/nora` ou similaire)
3. Identifie où déployer les fichiers de Frappe_Assistant_Core

**Commandes attendues** :
```bash
# Via ssh-manager MCP
ssh connect develop  # ou la commande appropriée
pwd
ls -la
find . -name "frappe-bench" -type d
```

#### ÉTAPE 2 : Installer Frappe_Assistant_Core via bench

**IMPORTANT** : Avant de déployer les fichiers manuellement, installe d'abord l'app Frappe_Assistant_Core via bench.

1. **Se positionner dans le répertoire bench** :
```bash
# Via ssh-manager MCP
cd /home/frappe/frappe-bench  # ou le chemin identifié à l'étape 1
```

2. **Installer l'app depuis le repo GitHub** :
```bash
# Récupérer l'app avec la branche de développement
bench get-app https://github.com/bvisible/Frappe_Assistant_Core.git \
  --branch claude/mcp-server-code-execution-mode-016mUfZLLAyeqSxR3GYPnrUZ

# Vérifier que l'app a été téléchargée
ls -la apps/frappe_assistant_core/
```

3. **Installer l'app sur le site develop** :
```bash
# Installer sur le site (remplace prod.local par le nom réel du site develop)
bench --site develop.local install-app frappe_assistant_core

# Vérifier l'installation
bench --site develop.local list-apps
```

**Résultat attendu** :
```
frappe
frappe_assistant_core
nora
...
```

4. **Redémarrer les services** :
```bash
bench restart

# Vérifier que tout fonctionne
bench status
```

**Note** : Si le site s'appelle différemment (ex: `prod.local`, `nora.local`), adapte la commande :
```bash
# Lister les sites disponibles
bench --site all list

# Installer sur le bon site
bench --site <nom_du_site> install-app frappe_assistant_core
```

#### ÉTAPE 3 : Explorer la configuration Nora

1. Comprends l'architecture de Nora :
   - Quels sont les DocTypes custom de Nora ?
   - Y a-t-il une configuration LLM spécifique ?
   - Comment Nora s'intègre avec Frappe ?

2. Identifie les credentials API :
   - URL de l'instance develop
   - Comment obtenir/créer une API Key + Secret ?

**Fichiers à explorer** :
```bash
# Dans Nora
cd apps/nora
cat nora/hooks.py
cat nora/config.py
ls -la nora/
find nora/ -name "*.json" | head -10

# Dans Frappe_Assistant_Core (maintenant installé)
cd ../frappe_assistant_core
ls -la
cat frappe_assistant_core/hooks.py
```

#### ÉTAPE 4 : Déployer les fichiers de test et validation

Les fichiers sont maintenant dans `apps/frappe_assistant_core/` grâce à bench get-app.

1. **Accéder au répertoire de l'app** :
```bash
cd /home/frappe/frappe-bench/apps/frappe_assistant_core
ls -la

# Vérifier que tous les fichiers Phase 3 sont présents
ls -la frappe_bridge_adapter_v2.py
ls -la validate_integration.py
ls -la tests/
```

2. **Créer la configuration .env** :
```bash
# Dans le répertoire de l'app
cat > .env << 'EOF'
FRAPPE_URL=http://localhost:8000
FRAPPE_API_KEY=<À_GÉNÉRER>
FRAPPE_API_SECRET=<À_GÉNÉRER>
EOF
```

**Note** : Si certains fichiers de test manquent (car pas dans l'app Frappe officielle), tu peux :
- Les copier manuellement depuis le repo
- Ou les créer sur place

#### ÉTAPE 5 : Générer les credentials API

1. Connecte-toi à l'interface Frappe de develop
2. Génère une API Key + Secret :
   - Setup → Users → [Ton user] → API Access
   - Ou via bench console :

```python
# Dans bench console
import frappe

# Créer un utilisateur API si nécessaire
user = frappe.get_doc('User', 'Administrator')

# Générer API key + secret
api_key = frappe.generate_hash(length=15)
api_secret = frappe.generate_hash(length=15)

user.api_key = api_key
user.api_secret = api_secret
user.save()

print(f"API Key: {api_key}")
print(f"API Secret: {api_secret}")
```

3. Met à jour `.env` avec les credentials générés

#### ÉTAPE 6 : Installer les dépendances de test

```bash
# Dans le répertoire de l'app
cd /home/frappe/frappe-bench/apps/frappe_assistant_core

# Installer pytest et dépendances
pip3 install pytest pytest-cov pytest-mock httpx

# Ou utiliser le fichier requirements
pip3 install -r tests/requirements-test.txt
```

#### ÉTAPE 7 : Exécuter les tests unitaires

```bash
# Tests unitaires (sans instance Frappe)
python3 -m pytest tests/test_adapter_basic.py -v

# Attendu : 18/18 tests passent
```

**Critères de succès** :
- ✅ 18 tests passent
- ✅ 0 échec
- ✅ Durée < 10s

#### ÉTAPE 8 : Exécuter le script de validation d'intégration

```bash
# Validation complète avec Nora develop
python3 validate_integration.py
```

**Ce que le script teste** :
1. 🌐 Connectivité à Nora
2. 🔍 Recherches (simple, filtrée, avec champs)
3. 💾 Performance du cache (mesure le speedup)
4. 📄 Pagination automatique
5. 📝 CRUD (Create → Read → Update → Delete sur ToDo)
6. 📦 Batch operations (création multiple)
7. ⚠️ Gestion d'erreurs
8. 📋 Opérations DocType

**Critères de succès** :
- ✅ Taux de succès ≥ 90% (16/18 tests minimum)
- ✅ Cache speedup ≥ 10x
- ✅ Connectivité fonctionne
- ✅ Rapport JSON généré (`validation_report.json`)

#### ÉTAPE 9 : Tests d'intégration approfondis

```bash
# Tests d'intégration (avec vraie instance)
python3 -m pytest tests/test_integration.py -v --integration
```

**Critères de succès** :
- ✅ 15/15 tests passent
- ✅ Pas d'erreurs de connexion
- ✅ CRUD complet fonctionne

#### ÉTAPE 10 : Exécuter les benchmarks

```bash
# Benchmarks de performance
python3 tests/benchmark_adapter.py
```

**Choisir dans le menu** :
- Option 1 : Cache hit vs miss
- Option 2 : Pagination
- Option 3 : Batch vs individuel
- Option 6 : Tout exécuter

**Métriques attendues** :
- Cache hit : 0.01-0.05s (vs 0.2-0.5s cache miss)
- Speedup : 10-150x
- Batch : 2-3x plus rapide qu'individuel

#### ÉTAPE 11 : Tests spécifiques à Nora

1. **Identifier les DocTypes Nora** :
```python
# Script Python
from frappe_bridge_adapter_v2 import FrappeProxyAdapter

adapter = FrappeProxyAdapter()
doctypes = adapter.list_doctypes()

# Filtrer les DocTypes custom Nora
nora_doctypes = [dt for dt in doctypes if 'nora' in dt.lower()]
print("DocTypes Nora:", nora_doctypes)
```

2. **Tester avec DocTypes Nora** :
```python
# Pour chaque DocType Nora identifié
for doctype in nora_doctypes:
    try:
        results = adapter.search_documents(doctype, limit=5)
        print(f"✅ {doctype}: {len(results)} documents")
    except Exception as e:
        print(f"❌ {doctype}: {e}")
```

3. **Tester la configuration LLM** (si applicable) :
   - Identifier comment Nora configure les LLM
   - Tester que l'adaptateur peut lire/écrire ces configs

#### ÉTAPE 12 : Créer un rapport de validation

Créer un fichier `NORA_VALIDATION_REPORT.md` avec :

```markdown
# Rapport de Validation - Nora develop

## Environnement
- Instance : develop
- URL : http://localhost:8000 (ou autre)
- Date : [DATE]
- Python : [VERSION]

## Tests Unitaires
- Exécutés : 18
- Réussis : [X]
- Échoués : [X]
- Statut : ✅ / ❌

## Validation d'Intégration
- Tests totaux : 18
- Taux de succès : [X]%
- Cache speedup : [X]x
- Statut : ✅ / ❌

## Tests d'Intégration
- Exécutés : 15
- Réussis : [X]
- Statut : ✅ / ❌

## Benchmarks
- Cache hit : [X]s
- Cache miss : [X]s
- Speedup : [X]x
- Batch vs individuel : [X]x

## DocTypes Nora Testés
[Liste des DocTypes custom Nora testés]

## Problèmes Identifiés
[Liste des problèmes, s'il y en a]

## Recommandations
[Recommandations pour améliorer l'intégration]

## Conclusion
✅ L'adaptateur V2 est fonctionnel avec Nora develop
OU
❌ Des corrections sont nécessaires avant production
```

#### ÉTAPE 13 : Tests de charge (optionnel)

Si tout fonctionne bien, teste la performance sous charge :

```python
# Script de test de charge
import time
from frappe_bridge_adapter_v2 import FrappeProxyAdapter

adapter = FrappeProxyAdapter(enable_cache=True)

# Test 1 : 100 requêtes identiques (cache hit)
start = time.time()
for i in range(100):
    adapter.search_documents('User', limit=10)
duration = time.time() - start
print(f"100 requêtes avec cache : {duration:.2f}s ({duration/100*1000:.1f}ms/requête)")

# Test 2 : Batch create 100 documents
docs = [{'description': f'Load test {i}'} for i in range(100)]
start = time.time()
result = adapter.batch_create_documents('ToDo', docs)
duration = time.time() - start
print(f"Batch create 100 docs : {duration:.2f}s")

# Cleanup
for doc in result['created']:
    adapter.delete_document('ToDo', doc['name'])
```

---

## 📊 CRITÈRES DE VALIDATION GLOBAUX

### ✅ Validation RÉUSSIE si :

1. **Tests unitaires** : 18/18 passent ✅
2. **Validation intégration** : ≥90% succès ✅
3. **Tests d'intégration** : ≥13/15 passent ✅
4. **Cache speedup** : ≥10x ✅
5. **Connectivité Nora** : Fonctionne ✅
6. **DocTypes Nora** : Au moins 1 testé avec succès ✅

### ⚠️ Validation PARTIELLE si :

1. Tests unitaires : 16-17/18 passent
2. Validation intégration : 70-89% succès
3. Quelques DocTypes Nora échouent
4. Cache speedup : 5-10x

### ❌ Validation ÉCHOUÉE si :

1. Tests unitaires : <16/18 passent
2. Connectivité Nora échoue
3. Cache ne fonctionne pas
4. Erreurs critiques sur CRUD

---

## 🔧 DÉPANNAGE

### Problème : Connexion à Nora échoue

**Symptômes** :
```
❌ Connexion à Frappe (2.35s)
   Erreur: Connection refused
```

**Solutions** :
1. Vérifier que Nora tourne : `bench status` ou `supervisorctl status all`
2. Vérifier l'URL dans `.env`
3. Tester manuellement :
```bash
curl -H "Authorization: token API_KEY:API_SECRET" \
     http://localhost:8000/api/method/frappe.auth.get_logged_user
```

### Problème : API Key invalide

**Symptômes** :
```
❌ Erreur: Insufficient Permission / Invalid credentials
```

**Solutions** :
1. Regénérer les credentials (voir ÉTAPE 4)
2. Vérifier les permissions de l'utilisateur
3. Donner rôle "System Manager" à l'utilisateur API

### Problème : Tests CRUD échouent

**Symptômes** :
```
❌ Création document (ToDo) (0.52s)
   Erreur: Insufficient Permission
```

**Solutions** :
1. Donner permissions Write sur DocType ToDo
2. Ou modifier le script pour utiliser un autre DocType avec permissions

### Problème : Import httpx échoue

**Symptômes** :
```
ModuleNotFoundError: No module named 'httpx'
```

**Solution** :
```bash
pip3 install httpx
# L'adaptateur a un fallback sur urllib, mais httpx est recommandé
```

---

## 📁 FICHIERS À RETOURNER

À la fin de la validation, fournis :

1. **`NORA_VALIDATION_REPORT.md`** : Rapport complet
2. **`validation_report.json`** : Export du script validate_integration.py
3. **Logs des tests** : Copie de tous les outputs
4. **Screenshots** (si possible) : Résultats des benchmarks

---

## 🚀 COMMANDES RÉSUMÉES

```bash
# 1. Connexion ssh-manager
ssh connect develop

# 2. Installer l'app via bench
cd /home/frappe/frappe-bench
bench get-app https://github.com/bvisible/Frappe_Assistant_Core.git \
  --branch claude/mcp-server-code-execution-mode-016mUfZLLAyeqSxR3GYPnrUZ
bench --site develop.local install-app frappe_assistant_core
bench restart

# 3. Explorer Nora
cd apps/nora
cat nora/hooks.py

# 4. Accéder aux fichiers de test
cd ../frappe_assistant_core
ls -la frappe_bridge_adapter_v2.py validate_integration.py tests/

# 5. Créer .env avec credentials
# [Générer API Key/Secret puis créer .env]

# 6. Installer dépendances test
pip3 install -r tests/requirements-test.txt

# 7. Tests unitaires
python3 -m pytest tests/test_adapter_basic.py -v

# 8. Validation intégration
python3 validate_integration.py

# 9. Tests d'intégration
python3 -m pytest tests/test_integration.py -v --integration

# 10. Benchmarks
python3 tests/benchmark_adapter.py

# 11. Tests Nora custom
# [Scripts Python pour DocTypes Nora]

# 12. Rapport
# [Créer NORA_VALIDATION_REPORT.md]
```

---

## ❓ QUESTIONS À RÉPONDRE

Dans ton rapport final, réponds à ces questions :

1. **Quelle est l'architecture de Nora ?**
   - Quels DocTypes custom ?
   - Comment est configuré le LLM ?
   - Intégration avec Frappe ?

2. **L'adaptateur V2 fonctionne-t-il avec Nora ?**
   - Tous les tests passent ?
   - Quels sont les speedup mesurés ?
   - Des problèmes spécifiques à Nora ?

3. **Recommandations pour la production ?**
   - L'adaptateur est-il prêt ?
   - Quelles optimisations suggérer ?
   - Des limitations découvertes ?

4. **Prochaines étapes ?**
   - Migration complète vers code execution mode ?
   - Autres DocTypes à tester ?
   - Intégration avec des workflows Nora ?

---

## 📚 DOCUMENTATION DE RÉFÉRENCE

Consulte ces fichiers dans Frappe_Assistant_Core :

- `API_REFERENCE.md` : Documentation complète de l'adaptateur V2
- `VALIDATION_GUIDE.md` : Guide détaillé de validation
- `PHASE3_COMPLETE.md` : Récapitulatif Phase 3
- `tests/README.md` : Guide des tests

---

**Version** : 1.0
**Date** : 2025-11-17
**Branche** : `claude/mcp-server-code-execution-mode-016mUfZLLAyeqSxR3GYPnrUZ`

---

## ✅ CHECKLIST FINALE

Avant de conclure, assure-toi que :

- [ ] ssh-manager MCP fonctionne
- [ ] Nora develop est accessible
- [ ] App installée via `bench get-app` ✅
- [ ] App installée sur le site via `bench install-app` ✅
- [ ] Services redémarrés (`bench restart`) ✅
- [ ] Fichiers de test présents dans apps/frappe_assistant_core/
- [ ] .env configuré avec credentials valides
- [ ] Tests unitaires : 18/18 ✅
- [ ] Validation intégration : ≥90% ✅
- [ ] Tests d'intégration : ≥13/15 ✅
- [ ] Benchmarks exécutés
- [ ] DocTypes Nora testés
- [ ] Rapport créé (NORA_VALIDATION_REPORT.md)
- [ ] Problèmes documentés
- [ ] Recommandations formulées

**Bonne chance ! 🚀**
