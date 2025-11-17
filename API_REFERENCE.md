# API Reference : Frappe Bridge Adapter V2

Documentation complète de l'API **FrappeProxyAdapter V2** pour le sandbox code execution.

## 📚 Table des Matières

- [Installation](#installation)
- [Initialisation](#initialisation)
- [Méthodes de Recherche](#méthodes-de-recherche)
- [Méthodes CRUD](#méthodes-crud)
- [Méthodes Batch](#méthodes-batch)
- [Méthodes DocType](#méthodes-doctype)
- [Gestion du Cache](#gestion-du-cache)
- [Gestion d'Erreurs](#gestion-derreurs)
- [Examples](#examples)

---

## Installation

```bash
# Dans le sandbox code execution, l'adaptateur est automatiquement disponible
from frappe_bridge_adapter_v2 import FrappeProxyAdapter
```

---

## Initialisation

### `FrappeProxyAdapter()`

Créer une instance de l'adaptateur.

**Paramètres :**

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `enable_cache` | `bool` | `False` | Activer le cache local |
| `cache_ttl` | `int` | `300` | Durée de vie du cache (secondes) |
| `max_retries` | `int` | `3` | Nombre max de tentatives en cas d'erreur |
| `retry_backoff` | `float` | `0.5` | Facteur backoff pour retry (0.5 → 1s, 2s, 4s) |
| `timeout` | `int` | `30` | Timeout HTTP (secondes) |

**Retourne :** Instance de `FrappeProxyAdapter`

**Lève :** `ValueError` si FRAPPE_API_KEY ou FRAPPE_API_SECRET manquants

**Exemple :**

```python
# Configuration basique (sans cache)
adapter = FrappeProxyAdapter()

# Configuration avancée (avec cache et retry)
adapter = FrappeProxyAdapter(
    enable_cache=True,
    cache_ttl=600,       # 10 minutes
    max_retries=5,
    timeout=60
)
```

**Variables d'environnement requises :**
- `FRAPPE_URL` : URL de base Frappe (ex: http://localhost:8000)
- `FRAPPE_API_KEY` : Clé API Frappe
- `FRAPPE_API_SECRET` : Secret API Frappe

---

## Méthodes de Recherche

### `search_documents()`

Rechercher des documents avec filtres et pagination automatique.

**Signature :**

```python
def search_documents(
    doctype: str,
    filters: Optional[Dict] = None,
    fields: Optional[List[str]] = None,
    order_by: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    auto_paginate: bool = False,
    use_cache: bool = True
) -> List[Dict[str, Any]]
```

**Paramètres :**

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `doctype` | `str` | Requis | Type de document (ex: 'Customer') |
| `filters` | `Dict` | `None` | Filtres de recherche |
| `fields` | `List[str]` | `None` | Champs à retourner (None = tous) |
| `order_by` | `str` | `'modified desc'` | Ordre de tri |
| `limit` | `int` | `20` | Nombre max de résultats par page |
| `offset` | `int` | `0` | Offset de départ |
| `auto_paginate` | `bool` | `False` | Si True, récupère TOUS les résultats |
| `use_cache` | `bool` | `True` | Utiliser le cache (si activé) |

**Retourne :** Liste de documents (dictionnaires)

**Exemple simple :**

```python
# Rechercher les 10 premiers clients
customers = adapter.search_documents('Customer', limit=10)

for customer in customers:
    print(customer['customer_name'])
```

**Exemple avec filtres :**

```python
# Clients de type "Company" avec balance > 1000
customers = adapter.search_documents(
    doctype='Customer',
    filters={
        'customer_type': 'Company',
        'outstanding_amount': ['>', 1000]
    },
    fields=['name', 'customer_name', 'outstanding_amount'],
    order_by='outstanding_amount desc',
    limit=50
)
```

**Exemple pagination automatique :**

```python
# Récupérer TOUS les clients (attention: peut être lent)
all_customers = adapter.search_documents(
    doctype='Customer',
    auto_paginate=True,
    limit=100  # 100 par page
)

print(f"Total: {len(all_customers)} clients")
```

**Filtres supportés :**

```python
# Égalité
filters={'status': 'Open'}

# Comparaison
filters={'outstanding_amount': ['>', 1000]}
filters={'creation': ['between', ['2024-01-01', '2024-12-31']]}

# IN
filters={'customer_type': ['in', ['Company', 'Individual']]}

# LIKE
filters={'customer_name': ['like', '%Corp%']}

# Multiples
filters={
    'customer_type': 'Company',
    'outstanding_amount': ['>', 1000],
    'territory': 'France'
}
```

---

### `get_document()`

Récupérer un document spécifique par son nom/ID.

**Signature :**

```python
def get_document(
    doctype: str,
    name: str,
    fields: Optional[List[str]] = None,
    use_cache: bool = True
) -> Dict[str, Any]
```

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `doctype` | `str` | Type de document |
| `name` | `str` | Nom/ID du document |
| `fields` | `List[str]` | Champs à retourner (None = tous) |
| `use_cache` | `bool` | Utiliser le cache |

**Retourne :** Document (dictionnaire)

**Lève :** `FrappeAPIError` si document non trouvé

**Exemple :**

```python
# Récupérer un client par son ID
customer = adapter.get_document('Customer', 'CUST-00001')

print(f"Nom: {customer['customer_name']}")
print(f"Email: {customer.get('email_id', 'N/A')}")

# Récupérer seulement certains champs
customer = adapter.get_document(
    'Customer',
    'CUST-00001',
    fields=['name', 'customer_name', 'email_id']
)
```

---

### `global_search()`

Recherche globale dans tous les documents.

**Signature :**

```python
def global_search(
    text: str,
    limit: int = 20,
    use_cache: bool = False
) -> List[Dict[str, Any]]
```

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Texte à rechercher |
| `limit` | `int` | Nombre max de résultats |
| `use_cache` | `bool` | Utiliser le cache |

**Retourne :** Liste de résultats avec doctype et nom

**Exemple :**

```python
# Rechercher "acme" partout
results = adapter.global_search('acme', limit=10)

for result in results:
    print(f"{result['doctype']}: {result['value']}")
```

---

## Méthodes CRUD

### `create_document()`

Créer un nouveau document.

**Signature :**

```python
def create_document(
    doctype: str,
    data: Dict[str, Any]
) -> Dict[str, Any]
```

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `doctype` | `str` | Type de document à créer |
| `data` | `Dict` | Données du document |

**Retourne :** Document créé avec son ID

**Lève :** `FrappeAPIError` si création échoue

**Exemple :**

```python
# Créer un nouveau client
customer = adapter.create_document(
    doctype='Customer',
    data={
        'customer_name': 'Acme Corporation',
        'customer_type': 'Company',
        'territory': 'France',
        'customer_group': 'Commercial'
    }
)

print(f"Client créé: {customer['name']}")
```

**Note :** Invalide automatiquement le cache pour ce doctype.

---

### `update_document()`

Mettre à jour un document existant.

**Signature :**

```python
def update_document(
    doctype: str,
    name: str,
    data: Dict[str, Any]
) -> Dict[str, Any]
```

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `doctype` | `str` | Type de document |
| `name` | `str` | Nom/ID du document |
| `data` | `Dict` | Données à mettre à jour |

**Retourne :** Document mis à jour

**Exemple :**

```python
# Mettre à jour un client
updated = adapter.update_document(
    doctype='Customer',
    name='CUST-00001',
    data={
        'customer_type': 'Company',
        'territory': 'Spain'
    }
)

print(f"Client mis à jour: {updated['name']}")
```

**Note :** Seuls les champs fournis dans `data` sont modifiés.

---

### `delete_document()`

Supprimer un document.

**Signature :**

```python
def delete_document(
    doctype: str,
    name: str
) -> Dict[str, str]
```

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `doctype` | `str` | Type de document |
| `name` | `str` | Nom/ID du document |

**Retourne :** Dictionnaire de confirmation

**Lève :** `FrappeAPIError` si suppression échoue

**Exemple :**

```python
# Supprimer un client
result = adapter.delete_document('Customer', 'CUST-00001')

print(result['message'])  # "Customer CUST-00001 deleted"
```

---

## Méthodes Batch

### `batch_create_documents()`

Créer plusieurs documents en batch.

**Signature :**

```python
def batch_create_documents(
    doctype: str,
    documents: List[Dict[str, Any]],
    stop_on_error: bool = False
) -> Dict[str, Any]
```

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `doctype` | `str` | Type de documents à créer |
| `documents` | `List[Dict]` | Liste de documents |
| `stop_on_error` | `bool` | Arrêter au premier échec |

**Retourne :** Dictionnaire avec résultats :

```python
{
    'created': [  # Documents créés avec succès
        {'name': 'CUST-00001', ...},
        {'name': 'CUST-00002', ...}
    ],
    'failed': [   # Erreurs
        {
            'index': 2,
            'data': {...},
            'error': 'Message d\'erreur'
        }
    ],
    'count': 2,   # Nombre créés
    'errors': 1   # Nombre d'erreurs
}
```

**Exemple :**

```python
# Créer 10 clients en batch
customers_data = [
    {'customer_name': f'Customer {i}', 'customer_type': 'Individual'}
    for i in range(1, 11)
]

result = adapter.batch_create_documents(
    doctype='Customer',
    documents=customers_data,
    stop_on_error=False  # Continue même si erreurs
)

print(f"Créés: {result['count']}")
print(f"Erreurs: {result['errors']}")

# Traiter les succès
for doc in result['created']:
    print(f"✅ {doc['name']}")

# Traiter les erreurs
for error in result['failed']:
    print(f"❌ Index {error['index']}: {error['error']}")
```

---

## Méthodes DocType

### `get_doctype_schema()`

Récupérer les métadonnées d'un DocType.

**Signature :**

```python
def get_doctype_schema(
    doctype: str,
    use_cache: bool = True
) -> Dict[str, Any]
```

**Retourne :** Schéma du DocType :

```python
{
    'name': 'Customer',
    'fields': [
        {
            'fieldname': 'customer_name',
            'fieldtype': 'Data',
            'label': 'Customer Name',
            'reqd': 1,
            ...
        },
        ...
    ],
    'permissions': [...],
    'is_submittable': 0,
    'track_changes': 1
}
```

**Exemple :**

```python
# Récupérer schéma Customer
schema = adapter.get_doctype_schema('Customer')

print(f"DocType: {schema['name']}")
print(f"Submittable: {schema['is_submittable']}")

# Lister les champs
for field in schema['fields']:
    required = "✅" if field.get('reqd') else "  "
    print(f"{required} {field['fieldname']}: {field['fieldtype']}")
```

---

### `list_doctypes()`

Lister tous les DocTypes disponibles.

**Signature :**

```python
def list_doctypes(
    limit: int = 999,
    use_cache: bool = True
) -> List[str]
```

**Retourne :** Liste de noms de DocTypes

**Exemple :**

```python
# Lister tous les DocTypes
doctypes = adapter.list_doctypes()

print(f"Total: {len(doctypes)} DocTypes")

# Filtrer (ex: DocTypes commençant par 'Sales')
sales_doctypes = [dt for dt in doctypes if dt.startswith('Sales')]
print(sales_doctypes)
```

---

## Gestion du Cache

### `clear_cache()`

Vider complètement le cache.

**Signature :**

```python
def clear_cache() -> None
```

**Exemple :**

```python
# Vider le cache
adapter.clear_cache()

# Ou invalider pour un doctype spécifique (méthode privée)
# adapter._invalidate_cache_for_doctype('Customer')
```

---

### `get_cache_stats()`

Récupérer les statistiques du cache.

**Signature :**

```python
def get_cache_stats() -> Dict[str, Any]
```

**Retourne :**

```python
{
    'total_entries': 15,      # Entrées totales
    'active_entries': 12,     # Entrées valides
    'expired_entries': 3,     # Entrées expirées
    'hit_rate': 'N/A'         # TODO
}
```

**Exemple :**

```python
# Vérifier stats cache
stats = adapter.get_cache_stats()

print(f"Cache: {stats['active_entries']}/{stats['total_entries']} actives")
print(f"Expirées: {stats['expired_entries']}")
```

---

## Gestion d'Erreurs

### `FrappeAPIError`

Exception levée lors d'erreurs API Frappe.

**Attributs :**

| Attribut | Type | Description |
|----------|------|-------------|
| `message` | `str` | Message d'erreur |
| `status_code` | `int` | Code HTTP (si disponible) |
| `response` | `Dict` | Réponse complète (si disponible) |

**Exemple :**

```python
from frappe_bridge_adapter_v2 import FrappeAPIError

try:
    customer = adapter.get_document('Customer', 'INVALID-ID')
except FrappeAPIError as e:
    print(f"Erreur API: {e}")
    print(f"Code HTTP: {e.status_code}")
    print(f"Réponse: {e.response}")
```

**Retry automatique :**

L'adaptateur retente automatiquement en cas d'erreur temporaire (configurable via `max_retries`).

---

## Examples

### Exemple 1 : Recherche avec Traitement

```python
from frappe_bridge_adapter_v2 import FrappeProxyAdapter

# Initialiser
adapter = FrappeProxyAdapter(enable_cache=True)

# Rechercher clients VIP avec balance élevée
vip_customers = adapter.search_documents(
    doctype='Customer',
    filters={
        'customer_group': 'VIP',
        'outstanding_amount': ['>', 5000]
    },
    fields=['name', 'customer_name', 'outstanding_amount', 'email_id'],
    order_by='outstanding_amount desc',
    limit=50
)

# Traiter les résultats
total_balance = sum(c['outstanding_amount'] for c in vip_customers)

print(f"Clients VIP: {len(vip_customers)}")
print(f"Balance totale: {total_balance:,.2f}")

# Envoyer emails (hypothétique)
for customer in vip_customers:
    if customer.get('email_id'):
        print(f"Email à envoyer: {customer['email_id']}")
```

---

### Exemple 2 : Workflow Complexe

```python
from frappe_bridge_adapter_v2 import FrappeProxyAdapter
from datetime import datetime, timedelta

adapter = FrappeProxyAdapter()

# Date de coupure (6 mois)
cutoff_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')

# 1. Chercher clients avec balance
customers = adapter.search_documents(
    'Customer',
    filters={'outstanding_amount': ['>', 0]},
    limit=50
)

# 2. Pour chaque client, analyser ses commandes
high_value = []

for customer in customers:
    # Chercher commandes récentes
    orders = adapter.search_documents(
        'Sales Order',
        filters={
            'customer': customer['name'],
            'transaction_date': ['>', cutoff_date]
        }
    )

    # Logique métier
    if len(orders) >= 5:
        order_value = sum(float(o.get('grand_total', 0)) for o in orders)

        high_value.append({
            'customer': customer['customer_name'],
            'balance': customer['outstanding_amount'],
            'orders': len(orders),
            'order_value': order_value
        })

# 3. Trier et afficher
high_value.sort(key=lambda x: x['order_value'], reverse=True)

print(f"Clients haute valeur: {len(high_value)}")
for c in high_value[:10]:  # Top 10
    print(f"{c['customer']}: {c['orders']} commandes, {c['order_value']:,.2f}€")
```

---

### Exemple 3 : Batch avec Gestion d'Erreurs

```python
adapter = FrappeProxyAdapter()

# Données à importer
import_data = [
    {'customer_name': 'Company A', 'customer_type': 'Company'},
    {'customer_name': 'Company B', 'customer_type': 'Company'},
    {'customer_name': 'Invalid'},  # Manque customer_type (erreur)
    {'customer_name': 'Company C', 'customer_type': 'Company'},
]

# Import batch
result = adapter.batch_create_documents(
    'Customer',
    import_data,
    stop_on_error=False  # Continue malgré erreurs
)

# Rapport
print(f"\n✅ Succès: {result['count']}/{len(import_data)}")
print(f"❌ Erreurs: {result['errors']}")

if result['failed']:
    print("\nDétail des erreurs:")
    for error in result['failed']:
        print(f"  Ligne {error['index']}: {error['error']}")
        print(f"    Données: {error['data']}")
```

---

### Exemple 4 : Cache Performance

```python
import time

# Sans cache
adapter_no_cache = FrappeProxyAdapter(enable_cache=False)

start = time.time()
for i in range(10):
    adapter_no_cache.search_documents('Customer', limit=10)
duration_no_cache = time.time() - start

print(f"Sans cache (10 requêtes): {duration_no_cache:.2f}s")

# Avec cache
adapter_with_cache = FrappeProxyAdapter(enable_cache=True, cache_ttl=60)

start = time.time()
for i in range(10):
    adapter_with_cache.search_documents('Customer', limit=10)
duration_with_cache = time.time() - start

print(f"Avec cache (10 requêtes): {duration_with_cache:.2f}s")

improvement = ((duration_no_cache - duration_with_cache) / duration_no_cache) * 100
print(f"Amélioration: {improvement:.0f}%")

# Stats cache
stats = adapter_with_cache.get_cache_stats()
print(f"Entrées cache: {stats['active_entries']}")
```

---

## Performance Tips

### ✅ DO

**Activer le cache pour lectures répétées :**
```python
adapter = FrappeProxyAdapter(enable_cache=True, cache_ttl=300)
```

**Utiliser pagination automatique avec parcimonie :**
```python
# OK pour petits volumes (<1000)
all_docs = adapter.search_documents('Customer', auto_paginate=True)

# Mieux: paginer manuellement si gros volume
for page in range(0, 10):
    docs = adapter.search_documents('Customer', limit=100, offset=page*100)
    process(docs)
```

**Sélectionner seulement les champs nécessaires :**
```python
# Mieux
docs = adapter.search_documents('Customer', fields=['name', 'customer_name'])

# Moins bon (récupère tous les champs)
docs = adapter.search_documents('Customer')
```

**Utiliser batch operations :**
```python
# Mieux (1 appel)
result = adapter.batch_create_documents('Customer', docs)

# Moins bon (N appels)
for doc in docs:
    adapter.create_document('Customer', doc)
```

### ❌ DON'T

**Pagination automatique sur gros volumes :**
```python
# ÉVITER si >10K résultats
all = adapter.search_documents('Customer', auto_paginate=True)
```

**Boucles avec requêtes :**
```python
# ÉVITER: N+1 queries
customers = adapter.search_documents('Customer', limit=100)
for c in customers:
    # 100 requêtes!
    details = adapter.get_document('Customer', c['name'])
```

**Cache sur données volatiles :**
```python
# ÉVITER si les données changent souvent
adapter = FrappeProxyAdapter(enable_cache=True, cache_ttl=3600)  # 1h trop long
```

---

## Changelog

**v2.0.0** (Phase 3)
- ✅ Pagination automatique
- ✅ Cache local avec TTL
- ✅ Retry logic avec exponential backoff
- ✅ Batch operations
- ✅ Méthodes additionnelles (list_doctypes, global_search)
- ✅ Gestion d'erreurs améliorée
- ✅ Tests unitaires et intégration

**v1.0.0** (Phase 2)
- Méthodes CRUD de base
- Support httpx + fallback urllib
- Credentials via env vars

---

**Version:** 2.0.0
**Date:** 2025-11-17
**Python:** ≥3.11
**License:** AGPL-3.0
