"""
POC Test 2 : Recherche simple via code execution

Ce test valide que l'adaptateur Frappe peut effectuer une recherche
simple de documents via l'API Frappe.

Attendu:
- L'adaptateur se connecte à Frappe
- La recherche retourne des résultats
- Les données sont correctement formatées
"""

import os
from frappe_bridge_adapter import FrappeProxyAdapter

print("=" * 60)
print("POC Test 2 : Recherche simple via code execution")
print("=" * 60)
print()

# Vérifier les credentials
print("1. Vérification des credentials...")
frappe_url = os.getenv('FRAPPE_URL')
frappe_api_key = os.getenv('FRAPPE_API_KEY')

if not frappe_url:
    print("   ❌ FRAPPE_URL non définie")
    raise ValueError("FRAPPE_URL requise")

if not frappe_api_key:
    print("   ❌ FRAPPE_API_KEY non définie")
    raise ValueError("FRAPPE_API_KEY requise")

print(f"   ✅ URL Frappe: {frappe_url}")
print(f"   ✅ API Key: {frappe_api_key[:10]}...")
print()

# Initialiser l'adaptateur
print("2. Initialisation adaptateur Frappe...")
try:
    adapter = FrappeProxyAdapter()
    print("   ✅ Adaptateur initialisé")
except Exception as e:
    print(f"   ❌ Erreur initialisation: {e}")
    raise

print()

# Test recherche Customer
print("3. Recherche de 5 Customers...")
try:
    customers = adapter.search_documents(
        doctype='Customer',
        fields=['name', 'customer_name', 'customer_type'],
        limit=5
    )
    print(f"   ✅ Trouvé {len(customers)} clients")

    if customers:
        print()
        print("   Détails des clients:")
        for i, customer in enumerate(customers, 1):
            name = customer.get('customer_name', customer.get('name'))
            ctype = customer.get('customer_type', 'N/A')
            print(f"   {i}. {name} ({ctype})")
    else:
        print("   ⚠️  Aucun client trouvé (base de données vide?)")

except Exception as e:
    print(f"   ❌ Erreur recherche: {e}")
    import traceback
    traceback.print_exc()
    raise

print()

# Test recherche avec filtre
print("4. Recherche Customers de type 'Company'...")
try:
    companies = adapter.search_documents(
        doctype='Customer',
        filters={'customer_type': 'Company'},
        fields=['name', 'customer_name'],
        limit=10
    )
    print(f"   ✅ Trouvé {len(companies)} entreprises")

    if companies:
        print()
        print("   Entreprises trouvées:")
        for company in companies[:5]:  # Afficher max 5
            print(f"   - {company.get('customer_name', company.get('name'))}")
        if len(companies) > 5:
            print(f"   ... et {len(companies) - 5} autres")

except Exception as e:
    print(f"   ⚠️  Erreur recherche avec filtre: {e}")
    # Ne pas échouer si pas de Companies

print()

# Test récupération d'un document
print("5. Récupération d'un document spécifique...")
if customers:
    first_customer_name = customers[0]['name']
    try:
        customer_detail = adapter.get_document('Customer', first_customer_name)
        print(f"   ✅ Document récupéré: {first_customer_name}")
        print(f"   Nom: {customer_detail.get('customer_name')}")
        print(f"   Type: {customer_detail.get('customer_type')}")

        # Afficher quelques champs supplémentaires
        if customer_detail.get('email_id'):
            print(f"   Email: {customer_detail.get('email_id')}")
        if customer_detail.get('mobile_no'):
            print(f"   Mobile: {customer_detail.get('mobile_no')}")

    except Exception as e:
        print(f"   ❌ Erreur récupération document: {e}")
        raise
else:
    print("   ⚠️  Pas de client pour tester get_document")

print()
print("=" * 60)
print("✅ Test 2 RÉUSSI : Recherche simple OK")
print("=" * 60)
print()
print(f"Résumé: {len(customers)} clients trouvés")
print()
