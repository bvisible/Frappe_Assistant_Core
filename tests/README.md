# Tests - Frappe Bridge Adapter V2

Suite de tests complète pour le **Frappe Bridge Adapter V2** avec cache, pagination automatique, retry logic et batch operations.

## 📁 Structure

```
tests/
├── __init__.py                  # Module tests
├── conftest.py                  # Fixtures pytest partagées
├── test_adapter_basic.py        # Tests unitaires de base
├── test_integration.py          # Tests d'intégration (Frappe requis)
├── benchmark_adapter.py         # Benchmarks de performance
├── requirements-test.txt        # Dépendances tests
└── README.md                    # Ce fichier
```

## 🎯 Types de Tests

### 1. Tests Unitaires (`test_adapter_basic.py`)

Tests isolés avec mocks, sans dépendances externes.

**Couvre :**
- Initialisation adaptateur
- Système de cache (set, get, expiration, invalidation)
- Recherche documents (basique, avec filtres, pagination)
- Récupération documents
- Opérations batch
- Gestion d'erreurs
- Retry logic

**Exécution :**
```bash
pytest tests/test_adapter_basic.py -v
```

**Avec coverage :**
```bash
pytest tests/test_adapter_basic.py --cov=frappe_bridge_adapter_v2 --cov-report=html
```

### 2. Tests d'Intégration (`test_integration.py`)

Tests avec une vraie instance Frappe.

**⚠️ Prérequis :**
- Instance Frappe accessible
- Variables env configurées (FRAPPE_URL, FRAPPE_API_KEY, FRAPPE_API_SECRET)
- Permissions appropriées

**Couvre :**
- Recherche réelle
- Cycle CRUD complet (Create → Read → Update → Delete)
- Pagination automatique
- Batch operations
- Opérations DocType
- Cache avec vraies données
- Performance basique

**Exécution :**
```bash
# Les tests d'intégration sont skippés par défaut
# Pour les activer :
pytest tests/test_integration.py -v --integration
```

### 3. Benchmarks (`benchmark_adapter.py`)

Benchmarks de performance pour comparer différentes configurations.

**Couvre :**
- Recherche avec/sans cache
- Cache miss vs cache hit
- Pagination manuelle vs automatique
- Création individuelle vs batch
- Impact retry logic

**Exécution :**
```bash
python tests/benchmark_adapter.py

# Choisir dans le menu :
# 1) Recherche sans cache
# 2) Recherche avec cache (compare miss vs hit)
# 3) Pagination (manuelle vs auto)
# 4) Batch operations
# 5) Retry logic
# 6) TOUS les benchmarks
```

---

## 🚀 Installation

### Dépendances de test

```bash
# Installer toutes les dépendances de test
pip install -r tests/requirements-test.txt

# Ou avec uv (recommandé)
uv pip install -r tests/requirements-test.txt
```

### Configuration

```bash
# Copier .env.example vers .env (si disponible)
cp .env.example .env

# Éditer .env avec vos credentials
nano .env

# Variables requises :
# FRAPPE_URL=http://localhost:8000
# FRAPPE_API_KEY=your_api_key
# FRAPPE_API_SECRET=your_api_secret
```

---

## 📊 Exécution des Tests

### Tests Unitaires (Rapide, sans Frappe)

```bash
# Tous les tests unitaires
pytest tests/test_adapter_basic.py -v

# Test spécifique
pytest tests/test_adapter_basic.py::TestCaching::test_cache_set_and_get -v

# Avec output détaillé
pytest tests/test_adapter_basic.py -v -s
```

### Tests d'Intégration (Avec Frappe)

```bash
# Vérifier configuration
cat .env

# Exécuter tests d'intégration
pytest tests/test_integration.py -v --integration

# Test spécifique
pytest tests/test_integration.py::TestIntegrationCRUD::test_full_crud_cycle -v --integration
```

### Tous les Tests

```bash
# Unitaires uniquement (par défaut)
pytest tests/ -v

# Unitaires + Intégration
pytest tests/ -v --integration
```

### Coverage

```bash
# Coverage tests unitaires
pytest tests/test_adapter_basic.py --cov=frappe_bridge_adapter_v2 --cov-report=html

# Ouvrir rapport
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Benchmarks

```bash
# Mode interactif
python tests/benchmark_adapter.py

# Ou directement tous les benchmarks (attention: long)
# (modifier le script pour automatiser)
```

---

## 📈 Résultats Attendus

### Coverage

**Objectif :** ≥80% de coverage

```
Name                          Stmts   Miss  Cover
-------------------------------------------------
frappe_bridge_adapter_v2.py     350     70    80%
-------------------------------------------------
TOTAL                           350     70    80%
```

### Tests Unitaires

**Tous les tests doivent passer :**

```
tests/test_adapter_basic.py::TestAdapterInitialization::test_init_with_env_vars PASSED
tests/test_adapter_basic.py::TestCaching::test_cache_set_and_get PASSED
tests/test_adapter_basic.py::TestSearchDocuments::test_search_with_pagination PASSED
...
===================== 25 passed in 2.50s =====================
```

### Tests d'Intégration

**Avec instance Frappe :**

```
tests/test_integration.py::TestIntegrationSearch::test_search_existing_doctype PASSED
tests/test_integration.py::TestIntegrationCRUD::test_full_crud_cycle PASSED
...
===================== 15 passed in 12.30s =====================
```

### Benchmarks

**Exemple de résultats :**

```
🏆 Classement par vitesse:
   1. Recherche 10 clients (cache hit): 0.015s
   2. Recherche 10 clients (sans cache): 0.230s
   3. Création batch (10 docs): 1.520s
   4. Pagination automatique: 2.100s
   5. Création individuelle (10 docs): 3.450s

💡 Recommandations:
   ✅ Le cache améliore les performances de 93%
      → Activez le cache pour les workflows avec lectures répétées
```

---

## 🔧 Fixtures Disponibles

Définies dans `conftest.py` :

| Fixture | Description | Usage |
|---------|-------------|-------|
| `mock_env_vars` | Mock variables env Frappe | Tests sans credentials |
| `sample_customer` | Exemple document Customer | Tests avec données |
| `sample_customers_list` | Liste de customers | Tests pagination |
| `mock_httpx_client` | Mock client httpx | Tests requêtes HTTP |
| `mock_frappe_response` | Factory réponses Frappe | Tests API mockées |
| `integration_adapter` | Adaptateur pour intégration | Tests avec Frappe |

**Exemple d'utilisation :**

```python
def test_example(mock_env_vars, sample_customer):
    adapter = FrappeProxyAdapter()
    # mock_env_vars a configuré les variables
    # sample_customer est disponible
    assert sample_customer['name'] == 'CUST-00001'
```

---

## 🎯 Tests par Fonctionnalité

### Cache

```bash
# Tests cache uniquement
pytest tests/test_adapter_basic.py::TestCaching -v

# Tests :
# - cache_disabled_by_default
# - cache_enabled
# - cache_key_generation
# - cache_set_and_get
# - cache_expiration
# - clear_cache
```

### Pagination

```bash
# Tests pagination
pytest tests/test_adapter_basic.py::TestSearchDocuments::test_search_with_pagination -v

# Tests intégration
pytest tests/test_integration.py::TestIntegrationSearch::test_search_auto_paginate -v --integration
```

### Batch Operations

```bash
# Tests batch unitaires
pytest tests/test_adapter_basic.py::TestBatchOperations -v

# Tests batch intégration
pytest tests/test_integration.py::TestIntegrationBatch -v --integration
```

### Retry Logic

```bash
# Test retry
pytest tests/test_adapter_basic.py::TestErrorHandling::test_retry_logic -v
```

---

## 🐛 Dépannage

### Erreur : "No module named 'pytest'"

```bash
pip install -r tests/requirements-test.txt
```

### Erreur : "FRAPPE_API_KEY et FRAPPE_API_SECRET requis"

```bash
# Vérifier .env
cat .env

# Ou exporter manuellement
export FRAPPE_API_KEY=your_key
export FRAPPE_API_SECRET=your_secret

# Puis relancer
pytest tests/...
```

### Tests d'intégration échouent

**Vérifier :**
1. Frappe est démarré : `curl http://localhost:8000/api/method/ping`
2. Credentials valides : Test avec curl
3. Permissions suffisantes : Vérifier rôle utilisateur

```bash
# Test credentials
curl -H "Authorization: token $FRAPPE_API_KEY:$FRAPPE_API_SECRET" \
     http://localhost:8000/api/resource/Customer?limit=1
```

### Benchmarks lents

**Normal !** Les benchmarks incluent :
- Vraies requêtes HTTP
- Création/suppression de documents
- Itérations multiples

Attendu : 1-5 minutes selon benchmark.

---

## 📝 Ajouter Nouveaux Tests

### Test Unitaire

```python
# tests/test_adapter_basic.py

class TestNewFeature:
    """Tests pour nouvelle fonctionnalité"""

    def test_feature_works(self, mock_env_vars):
        """Test que la feature fonctionne"""
        adapter = FrappeProxyAdapter()

        # Votre test ici
        result = adapter.new_method()

        assert result == expected
```

### Test d'Intégration

```python
# tests/test_integration.py

class TestIntegrationNewFeature:
    """Tests d'intégration pour nouvelle fonctionnalité"""

    def test_feature_with_frappe(self, integration_adapter):
        """Test avec vraie instance Frappe"""
        result = integration_adapter.new_method()

        assert result
        # Validations...
```

### Nouveau Benchmark

```python
# tests/benchmark_adapter.py

def benchmark_new_feature():
    """Benchmark: Nouvelle fonctionnalité"""
    adapter = FrappeProxyAdapter()
    runner = BenchmarkRunner()

    def feature_v1():
        return adapter.feature_old()

    def feature_v2():
        return adapter.feature_new()

    runner.benchmark("Feature V1", feature_v1, iterations=5)
    runner.benchmark("Feature V2", feature_v2, iterations=5)

    runner.compare("Feature V1", "Feature V2")

    return runner
```

---

## 📊 CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/tests.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r tests/requirements-test.txt

    - name: Run tests
      run: |
        pytest tests/test_adapter_basic.py -v --cov=frappe_bridge_adapter_v2

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## 🎓 Bonnes Pratiques

### Isolation

✅ **DO:**
- Utiliser fixtures pour setup/teardown
- Mocker appels HTTP dans tests unitaires
- Nettoyer données créées dans tests d'intégration

❌ **DON'T:**
- Dépendre d'un ordre d'exécution spécifique
- Laisser des données de test dans Frappe
- Partager l'état entre tests

### Lisibilité

✅ **DO:**
- Noms descriptifs : `test_cache_invalidation_after_update`
- Docstrings explicatives
- Arrange-Act-Assert pattern
- Assertions claires

```python
def test_search_with_filters(self, mock_env_vars):
    """Test que les filtres sont appliqués correctement"""
    # Arrange
    adapter = FrappeProxyAdapter()

    # Act
    results = adapter.search_documents(
        'Customer',
        filters={'customer_type': 'Company'}
    )

    # Assert
    assert all(r['customer_type'] == 'Company' for r in results)
```

### Performance

- Tests unitaires : <5s total
- Tests intégration : <30s total
- Benchmarks : Information seulement

---

## 📚 Ressources

- **pytest docs** : https://docs.pytest.org/
- **pytest-cov** : https://pytest-cov.readthedocs.io/
- **httpx** : https://www.python-httpx.org/
- **Frappe API** : https://frappeframework.com/docs/user/en/api

---

## ✅ Checklist Tests Phase 3

Avant de marquer Phase 3 comme complète :

- [ ] Tests unitaires créés (≥20 tests)
- [ ] Coverage ≥80%
- [ ] Tests d'intégration créés (≥10 tests)
- [ ] Benchmarks implémentés (≥5 scenarios)
- [ ] Documentation tests complète
- [ ] CI/CD configuration (optionnel)
- [ ] Tous les tests passent
- [ ] Benchmarks exécutés et documentés

---

**Version:** 1.0
**Date:** 2025-11-17
**Auteur:** Claude Code Assistant
