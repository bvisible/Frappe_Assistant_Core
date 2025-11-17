# Email avec Pièces Jointes PDF

Cette fonctionnalité permet d'envoyer des emails avec des documents ERPNext joints en PDF (factures, devis, commandes, etc.).

## Fonctionnement

L'outil `send_email` a été enrichi avec trois nouveaux paramètres :

### 1. `attach_document` - Joindre un document comme PDF

Génère automatiquement un PDF du document et le joint à l'email.

**Paramètres :**
- `doctype` (requis) : Type de document (ex: "Sales Invoice", "Quotation", "Purchase Order")
- `name` (requis) : Nom du document (peut être partiel, ex: "143" au lieu de "SINV-2024-00143")
- `print_format` (optionnel) : Format d'impression à utiliser (utilise le format par défaut si omis)

### 2. `attachments` - Joindre des fichiers existants

Liste de noms de fichiers (File DocType) déjà présents dans le système.

### 3. `auto_find_recipient` - Trouver automatiquement le destinataire

Si activé avec `attach_document`, le système extrait automatiquement l'email du client/fournisseur du document.

## Exemples d'utilisation

### Exemple 1 : Envoyer une facture avec recherche automatique

**Commande utilisateur :**
> "Envoie la facture 143 au client"

**Appel LLM :**
```python
send_email(
    message="Bonjour,\n\nVeuillez trouver ci-joint votre facture.\n\nCordialement,\n[Votre nom]",
    attach_document={
        "doctype": "Sales Invoice",
        "name": "143"  # Recherche partielle - trouvera "SINV-2024-00143"
    },
    auto_find_recipient=True,  # Récupère l'email du client
    send_now=False
)
```

**Résultat :**
1. Recherche la facture contenant "143"
2. Génère le PDF de la facture
3. Extrait l'email du client depuis la facture
4. Crée un brouillon d'email avec le PDF joint
5. Retourne un aperçu pour confirmation

### Exemple 2 : Envoyer un devis avec destinataire manuel

```python
send_email(
    recipient="client@example.com",
    subject="Votre devis",
    message="Veuillez trouver ci-joint notre devis.",
    attach_document={
        "doctype": "Quotation",
        "name": "QTN-2024-00056"
    },
    send_now=False
)
```

### Exemple 3 : Plusieurs pièces jointes

```python
send_email(
    recipient="client@example.com",
    message="Documents joints.",
    attach_document={
        "doctype": "Sales Invoice",
        "name": "SINV-2024-00143"
    },
    attachments=["FILE-00001", "FILE-00002"],  # Fichiers existants
    send_now=False
)
```

### Exemple 4 : Format d'impression personnalisé

```python
send_email(
    recipient="client@example.com",
    message="Votre facture.",
    attach_document={
        "doctype": "Sales Invoice",
        "name": "SINV-2024-00143",
        "print_format": "Custom Invoice Format"
    },
    send_now=False
)
```

## Gestion des erreurs

### Document non trouvé

Si le document n'existe pas :

```json
{
  "success": false,
  "error": "No Sales Invoice found matching '143'. Please provide the exact document ID or use search_link tool to find it first."
}
```

### Plusieurs documents correspondants

Si plusieurs documents correspondent au nom partiel :

```json
{
  "success": false,
  "error": "Multiple Sales Invoice documents found matching '143'",
  "matches": ["SINV-2024-00143", "SINV-2024-01143", "SINV-2024-02143"],
  "message": "🤔 Found 3 Sales Invoice matching '143':\n\n  • SINV-2024-00143\n  • SINV-2024-01143\n  • SINV-2024-02143\n\n💡 Please specify the exact document ID."
}
```

**Action recommandée :** Demander à l'utilisateur de préciser le document exact.

### Email non trouvé dans le document

Si `auto_find_recipient=True` mais pas d'email dans le document :

```json
{
  "success": false,
  "error": "Could not find recipient email in Sales Invoice 'SINV-2024-00143'. Please specify recipient manually using the 'recipient' parameter."
}
```

**Action recommandée :** Utiliser le paramètre `recipient` manuellement.

### Échec de génération PDF

```json
{
  "success": false,
  "error": "Failed to generate PDF for Sales Invoice 'SINV-2024-00143': [error details]"
}
```

## Documents supportés

Tous les doctypes ERPNext avec un print format sont supportés :

### Documents de vente
- Sales Invoice
- Quotation
- Sales Order
- Delivery Note
- Proforma Invoice

### Documents d'achat
- Purchase Invoice
- Purchase Order
- Purchase Receipt
- Supplier Quotation
- Material Request

### Autres documents
- Payment Entry
- Stock Entry
- Job Card
- Work Order
- etc.

## Résolution automatique du destinataire

Le système cherche l'email dans les champs suivants selon le type de document :

| DocType | Champs recherchés | Fallback |
|---------|-------------------|----------|
| Sales Invoice | contact_email, customer_email | Customer.email_id |
| Quotation | contact_email, customer_email | Customer.email_id |
| Purchase Order | contact_email, supplier_email | Supplier.email_id |
| Purchase Invoice | contact_email, supplier_email | Supplier.email_id |
| Autres | contact_email, email_id, email | N/A |

## Workflow complet

```
Utilisateur: "Envoie la facture 143 au client"
    ↓
LLM appelle send_email avec:
  - attach_document: {doctype: "Sales Invoice", name: "143"}
  - auto_find_recipient: true
    ↓
1. Recherche document: "143" → trouve "SINV-2024-00143"
2. Vérifie permissions: user peut lire Sales Invoice ✓
3. Génère PDF: frappe.attach_print() → Invoice-143.pdf
4. Extrait email: Sales Invoice.contact_email → "client@acme.com"
5. Crée Communication avec PDF joint
6. Retourne aperçu
    ↓
LLM montre aperçu à l'utilisateur
    ↓
Utilisateur: "oui envoie"
    ↓
LLM appelle confirm_send_email(communication_id="COMM-XXX")
    ↓
Email envoyé avec PDF joint ✓
```

## Sécurité

### Vérifications de permissions

1. **DocType** : Vérifie que l'utilisateur a permission de lire le doctype
2. **Document** : Vérifie que l'utilisateur a permission de lire le document spécifique
3. **Frappe standard** : Les permissions ERPNext standards sont appliquées

### Protection des données

- Les PDF sont générés avec les permissions de l'utilisateur actuel
- Les documents privés restent privés
- Audit trail : tous les envois sont loggés dans Assistant Audit Log

## Performance

- **Génération PDF** : ~1-3 secondes selon la taille du document
- **Recherche document** : < 100ms (index sur le champ name)
- **Taille PDF typique** : 50-500 KB

## Limitations

1. **Recherche partielle** : Maximum 10 résultats retournés
2. **Taille PDF** : Dépend de la configuration email du système
3. **Print format** : Doit exister pour le doctype

## Dépannage

### "No print format found"

Le doctype doit avoir un print format par défaut défini.

**Solution :**
- Créer un print format dans Setup → Print Format
- Ou spécifier un print format existant avec le paramètre `print_format`

### "Permission denied"

L'utilisateur n'a pas les permissions de lire le document.

**Solution :**
- Vérifier les permissions ERPNext pour l'utilisateur
- S'assurer que l'utilisateur a le rôle approprié

### "PDF generation timeout"

Document très large avec beaucoup de lignes.

**Solution :**
- Optimiser le print format
- Augmenter le timeout dans site_config.json

## Compatibilité

- **Frappe Framework** : v14+
- **ERPNext** : v14+
- **Frappe Assistant Core** : v2.2+

## Tests

Exécuter les tests :

```bash
bench --site <site-name> run-tests --app frappe_assistant_core --module frappe_assistant_core.tests.test_email_with_attachments
```
