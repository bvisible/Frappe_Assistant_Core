# Guide de Validation d'Intégration

Ce guide explique comment valider que l'adaptateur Frappe Bridge V2 fonctionne correctement avec votre instance Frappe/Nora.

## 🎯 Objectif

Le script `validate_integration.py` teste **toutes** les fonctionnalités de l'adaptateur V2 avec une vraie instance Frappe :

- ✅ Connectivité
- ✅ Recherches (simples, filtrées, avec champs)
- ✅ Performance du cache
- ✅ Pagination automatique
- ✅ Opérations CRUD (Create, Read, Update, Delete)
- ✅ Opérations batch
- ✅ Gestion d'erreurs
- ✅ Opérations DocType

## 📋 Prérequis

### 1. Instance Frappe Accessible

Vous devez avoir accès à une instance Frappe (locale ou cloud) avec :
- URL accessible
- API Key + API Secret

### 2. Permissions Requises

L'utilisateur API doit avoir les permissions suivantes :
- **Lecture** : User, ToDo, DocType
- **Écriture** : ToDo (pour tests CRUD)
- **Suppression** : ToDo (pour cleanup)

> **Note** : Le script crée des documents ToDo de test et les supprime automatiquement.

## 🔧 Configuration

### Option 1 : Fichier .env (Recommandé)

Créer un fichier `.env` à la racine du projet :

```bash
# .env
FRAPPE_URL=https://votre-instance.frappe.cloud
FRAPPE_API_KEY=votre_api_key
FRAPPE_API_SECRET=votre_api_secret
```

### Option 2 : Variables d'environnement

Exporter les variables avant d'exécuter :

```bash
export FRAPPE_URL=https://votre-instance.frappe.cloud
export FRAPPE_API_KEY=votre_api_key
export FRAPPE_API_SECRET=votre_api_secret
```

### Configuration pour Nora

Si vous utilisez Nora (https://github.com/bvisible/nora), adaptez selon votre configuration :

```bash
# Exemple avec Nora local
FRAPPE_URL=http://localhost:8000
FRAPPE_API_KEY=<votre_clé>
FRAPPE_API_SECRET=<votre_secret>

# Exemple avec Nora en production
FRAPPE_URL=https://nora.example.com
FRAPPE_API_KEY=<votre_clé>
FRAPPE_API_SECRET=<votre_secret>
```

## 🚀 Exécution

### Méthode Simple

```bash
python3 validate_integration.py
```

### Depuis Claude Code

Vous pouvez appeler ce script directement depuis Claude Code :

```python
# Dans une conversation Claude Code
"Peux-tu exécuter validate_integration.py pour vérifier l'intégration ?"
```

Claude Code exécutera le script et vous montrera les résultats.

## 📊 Interprétation des Résultats

### Sortie du Script

Le script affiche :

```
================================================================================
  VALIDATION D'INTÉGRATION - FRAPPE BRIDGE ADAPTER V2
================================================================================

Date: 2025-11-17 10:30:45
Python: 3.11.14

📋 VÉRIFICATION DE L'ENVIRONNEMENT
--------------------------------------------------------------------------------
  ✅ FRAPPE_URL: https://nora.example.com
  ✅ FRAPPE_API_KEY: abc1...xyz9
  ✅ FRAPPE_API_SECRET: def2...uvw8

✅ Configuration environnement OK

🔧 INITIALISATION DE L'ADAPTATEUR
--------------------------------------------------------------------------------
  ✅ Adaptateur créé
  ✅ Cache activé (TTL: 300s)
  ✅ Retry activé (max: 3, backoff: 0.5s)

✅ Initialisation OK

🌐 TEST 1: CONNECTIVITÉ
--------------------------------------------------------------------------------
  ✅ Connexion à Frappe (0.45s)
     247 DocTypes disponibles

🔍 TEST 2: OPÉRATIONS DE RECHERCHE
--------------------------------------------------------------------------------
  ✅ Recherche simple (User) (0.32s)
     5 utilisateurs trouvés
  ✅ Recherche avec filtres (0.28s)
     3 utilisateurs actifs
  ✅ Recherche avec champs (0.25s)

💾 TEST 3: PERFORMANCE DU CACHE
--------------------------------------------------------------------------------
  ✅ Cache miss (1ère requête) (0.30s)
  ✅ Cache hit (2ème requête) (0.015s)
     Amélioration: 20.0x plus rapide (95%)

📄 TEST 4: PAGINATION AUTOMATIQUE
--------------------------------------------------------------------------------
  ✅ Pagination manuelle (0.28s)
  ✅ Auto-pagination (0.85s)
     127 résultats totaux récupérés

📝 TEST 5: OPÉRATIONS CRUD
--------------------------------------------------------------------------------
  ✅ Création document (ToDo) (0.42s)
     Document créé: TODO-2025-0123
  ✅ Lecture document (0.18s)
  ✅ Mise à jour document (0.35s)
  ✅ Suppression document (0.28s)

📦 TEST 6: OPÉRATIONS BATCH
--------------------------------------------------------------------------------
  ✅ Création batch (5 ToDos) (0.65s)
     Créés: 5, Erreurs: 0

⚠️  TEST 7: GESTION D'ERREURS
--------------------------------------------------------------------------------
  ✅ Erreur DocType invalide (0.12s)
  ✅ Erreur document inexistant (0.15s)

📋 TEST 8: OPÉRATIONS DOCTYPES
--------------------------------------------------------------------------------
  ✅ Liste DocTypes (0.38s)
     247 DocTypes disponibles
  ✅ Métadonnées DocType (User) (0.42s)
     58 champs dans User

================================================================================
  RÉSUMÉ DE LA VALIDATION
================================================================================

Durée totale: 8.25s
Tests exécutés: 18
✅ Réussis: 18
❌ Échoués: 0
⏭️  Sautés: 0

Taux de succès: 100.0%
██████████████████████████████████████████████████ 100.0%

VERDICT:
✅ VALIDATION RÉUSSIE - L'adaptateur est fonctionnel !

📄 Rapport sauvegardé: validation_report.json
```

### Codes de Retour

| Code | Signification | Action |
|------|---------------|---------|
| `0` | ✅ Succès complet | Tout fonctionne ! |
| `1` | ⚠️  Succès partiel | Quelques avertissements, mais fonctionnel |
| `2` | ❌ Échec | Problèmes critiques détectés |
| `130` | ⏹️  Interrompu | Ctrl+C pendant l'exécution |

### Rapport JSON

Un rapport détaillé est sauvegardé dans `validation_report.json` :

```json
{
  "timestamp": "2025-11-17T10:30:53.456789",
  "summary": {
    "total_tests": 18,
    "passed": 18,
    "failed": 0,
    "skipped": 0,
    "success_rate": 100.0
  },
  "tests": [
    {
      "name": "Connexion à Frappe",
      "status": "PASSED",
      "duration": 0.45,
      "result": 247
    },
    ...
  ],
  "errors": [],
  "warnings": [],
  "environment": {
    "frappe_url": "https://nora.example.com",
    "python_version": "3.11.14"
  }
}
```

## 🔍 Dépannage

### Erreur : "Variables manquantes"

```
❌ Variables manquantes: FRAPPE_URL, FRAPPE_API_KEY, FRAPPE_API_SECRET
```

**Solution** : Créez un fichier `.env` ou exportez les variables.

### Erreur : "Connexion à Frappe" échoue

```
❌ Connexion à Frappe (2.35s)
   Erreur: Connection refused
```

**Causes possibles** :
1. URL incorrecte → Vérifiez `FRAPPE_URL`
2. Instance arrêtée → Démarrez Frappe/Nora
3. Pare-feu → Vérifiez l'accès réseau
4. Credentials invalides → Vérifiez API Key/Secret

**Vérifications** :

```bash
# Test manuel de connexion
curl -H "Authorization: token API_KEY:API_SECRET" \
     https://votre-instance/api/method/frappe.auth.get_logged_user
```

### Erreur : "Permissions insuffisantes"

```
❌ Création document (ToDo) (0.52s)
   Erreur: Insufficient Permission
```

**Solution** : Donnez les permissions requises à l'utilisateur API :
- Frappe → User → [Votre utilisateur API] → Roles
- Ajoutez le rôle "System Manager" ou créez un rôle custom avec permissions ToDo

### Avertissement : "Cache speedup faible"

```
⚠️  Cache speedup faible (2.1x) - attendu >10x
```

**Causes** :
- Réseau très rapide (le cache apporte moins de gain)
- Cache désactivé par erreur
- TTL trop court

**Normal si** : Vous êtes en local (localhost)

### Tests CRUD sautés

```
⚠️ Tests CRUD sautés (création échouée)
```

**Cause** : Permissions insuffisantes pour créer des ToDo

**Solution** : Donnez permissions Write sur ToDo, ou ignorez (le reste fonctionne)

## 📝 Personnalisation

### Tester un autre DocType

Éditez `validate_integration.py` et modifiez les tests CRUD :

```python
# Ligne ~285 : Remplacer 'ToDo' par votre DocType
def create_test():
    doc_data = {
        'customer_name': 'Test Customer',  # Champs de votre DocType
        'customer_type': 'Individual'
    }
    result = self.adapter.create_document('Customer', doc_data)
    # ...
```

### Désactiver certains tests

Commentez les appels dans `run()` :

```python
def run(self) -> int:
    # ...
    # self.test_crud_operations()  # ← Désactivé
    self.test_batch_operations()
    # ...
```

## 🎯 Utilisation avec Nora

Si vous utilisez [Nora](https://github.com/bvisible/nora) comme LLM configuré :

1. **Démarrer Nora** :
   ```bash
   cd /path/to/nora
   bench start
   ```

2. **Configurer les credentials** :
   - Connectez-vous à Nora
   - Générez API Key/Secret : Setup → Users → [Votre user] → API Access

3. **Lancer la validation** :
   ```bash
   cd /path/to/Frappe_Assistant_Core
   export FRAPPE_URL=http://localhost:8000
   export FRAPPE_API_KEY=...
   export FRAPPE_API_SECRET=...
   python3 validate_integration.py
   ```

4. **Intégrer avec Claude Code** :
   - Claude Code peut maintenant utiliser l'adaptateur V2
   - Toutes les fonctionnalités sont validées
   - Performance optimale avec cache

## ✅ Validation Réussie - Et Après ?

Une fois la validation réussie :

1. **L'adaptateur V2 est opérationnel** ✅
2. **Toutes les fonctionnalités sont testées** ✅
3. **Les performances sont validées** ✅

### Prochaines étapes :

- ✅ Utilisez l'adaptateur V2 dans vos workflows
- ✅ Activez le cache pour de meilleures performances
- ✅ Utilisez batch operations pour les imports
- ✅ Profitez de l'auto-pagination

### Métriques attendues :

- **Cache** : 10-150x plus rapide pour requêtes répétées
- **Batch** : 2-3x plus rapide que création individuelle
- **Retry** : 95%+ de fiabilité sur réseaux instables

## 📞 Support

En cas de problème :

1. Vérifiez les logs : Le script affiche des erreurs détaillées
2. Consultez `validation_report.json` pour les détails
3. Vérifiez la connectivité réseau
4. Vérifiez les permissions Frappe
5. Testez manuellement avec `curl` ou Postman

## 🔗 Ressources

- [Frappe API Documentation](https://frappeframework.com/docs/user/en/api)
- [API Reference](./API_REFERENCE.md) - Documentation de l'adaptateur V2
- [Tests README](./tests/README.md) - Guide des tests unitaires
- [Phase 3 Complete](./PHASE3_COMPLETE.md) - Récapitulatif Phase 3

---

**Version** : 1.0
**Date** : 2025-11-17
**Compatibilité** : Frappe v13+, Python 3.11+
