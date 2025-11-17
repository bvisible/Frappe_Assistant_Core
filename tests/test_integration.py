"""
Tests d'intégration pour FrappeProxyAdapter.
Ces tests nécessitent une instance Frappe accessible.

Pour exécuter ces tests :
    pytest tests/test_integration.py -v --integration

Pour skipper ces tests :
    pytest tests/ -v (sans --integration)
"""

import pytest
import os
import sys

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frappe_bridge_adapter_v2 import FrappeProxyAdapter, FrappeAPIError


# Marker pour tests d'intégration
pytestmark = pytest.mark.skipif(
    not pytest.config.getoption("--integration", default=False),
    reason="Tests d'intégration désactivés (utiliser --integration pour les activer)"
)


def pytest_addoption(parser):
    """Ajouter option --integration"""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Exécuter les tests d'intégration (nécessite Frappe)"
    )


@pytest.fixture(scope="module")
def integration_adapter():
    """Adaptateur pour tests d'intégration (avec vraie instance Frappe)"""
    # Vérifier que les credentials sont configurés
    if not os.getenv('FRAPPE_API_KEY') or not os.getenv('FRAPPE_API_SECRET'):
        pytest.skip("Credentials Frappe non configurés")

    adapter = FrappeProxyAdapter(
        enable_cache=False,  # Pas de cache pour tests
        max_retries=1  # Retry minimal pour tests
    )

    return adapter


@pytest.fixture(scope="module")
def test_customer_name():
    """Nom du client de test (sera créé et nettoyé)"""
    return "TEST_CUSTOMER_INTEGRATION"


class TestIntegrationSearch:
    """Tests d'intégration pour recherche"""

    def test_search_existing_doctype(self, integration_adapter):
        """Test recherche sur un DocType existant"""
        results = integration_adapter.search_documents('Customer', limit=5)

        assert isinstance(results, list)
        # Peut être vide si pas de données
        if results:
            assert 'name' in results[0]

    def test_search_with_filters(self, integration_adapter):
        """Test recherche avec filtres"""
        results = integration_adapter.search_documents(
            'Customer',
            filters={'customer_type': 'Company'},
            limit=5
        )

        assert isinstance(results, list)
        # Si résultats, vérifier le filtre
        for result in results:
            assert result.get('customer_type') == 'Company'

    def test_search_pagination(self, integration_adapter):
        """Test pagination manuelle"""
        page1 = integration_adapter.search_documents('Customer', limit=5, offset=0)
        page2 = integration_adapter.search_documents('Customer', limit=5, offset=5)

        assert isinstance(page1, list)
        assert isinstance(page2, list)

        # Si assez de données, les pages doivent être différentes
        if len(page1) == 5 and len(page2) > 0:
            assert page1[0]['name'] != page2[0]['name']

    def test_search_auto_paginate(self, integration_adapter):
        """Test pagination automatique"""
        # Limiter à 10 par page pour le test
        results = integration_adapter.search_documents(
            'Customer',
            auto_paginate=True,
            limit=10
        )

        assert isinstance(results, list)
        # Vérifie que ça récupère plus de 10 si disponibles
        # (ou tous ceux disponibles)


class TestIntegrationCRUD:
    """Tests d'intégration CRUD (Create, Read, Update, Delete)"""

    def test_full_crud_cycle(self, integration_adapter, test_customer_name):
        """Test cycle complet : Créer → Lire → Modifier → Supprimer"""

        # 1. CREATE
        customer_data = {
            'customer_name': test_customer_name,
            'customer_type': 'Individual'
        }

        created = integration_adapter.create_document('Customer', customer_data)

        assert created['name']
        assert created['customer_name'] == test_customer_name
        customer_id = created['name']

        try:
            # 2. READ
            retrieved = integration_adapter.get_document('Customer', customer_id)

            assert retrieved['name'] == customer_id
            assert retrieved['customer_name'] == test_customer_name

            # 3. UPDATE
            updated = integration_adapter.update_document(
                'Customer',
                customer_id,
                {'customer_type': 'Company'}
            )

            assert updated['customer_type'] == 'Company'

            # Vérifier la mise à jour
            after_update = integration_adapter.get_document('Customer', customer_id)
            assert after_update['customer_type'] == 'Company'

        finally:
            # 4. DELETE (cleanup)
            try:
                integration_adapter.delete_document('Customer', customer_id)

                # Vérifier suppression
                with pytest.raises(FrappeAPIError):
                    integration_adapter.get_document('Customer', customer_id)

            except Exception as e:
                # Si erreur de suppression, logger mais ne pas échouer le test
                print(f"Erreur cleanup: {e}")


class TestIntegrationBatch:
    """Tests d'intégration pour opérations batch"""

    def test_batch_create(self, integration_adapter):
        """Test création batch"""

        docs = [
            {'customer_name': f'BATCH_TEST_{i}', 'customer_type': 'Individual'}
            for i in range(3)
        ]

        result = integration_adapter.batch_create_documents('Customer', docs)

        assert result['count'] > 0
        assert result['count'] <= 3  # Au moins 1 succès

        # Cleanup
        for created in result['created']:
            try:
                integration_adapter.delete_document('Customer', created['name'])
            except:
                pass


class TestIntegrationDocTypeOperations:
    """Tests d'intégration pour opérations DocType"""

    def test_get_doctype_schema(self, integration_adapter):
        """Test récupération schéma DocType"""
        schema = integration_adapter.get_doctype_schema('Customer')

        assert schema['name'] == 'Customer'
        assert 'fields' in schema
        assert len(schema['fields']) > 0

        # Vérifier quelques champs standard
        field_names = [f['fieldname'] for f in schema['fields']]
        assert 'customer_name' in field_names

    def test_list_doctypes(self, integration_adapter):
        """Test liste des DocTypes"""
        doctypes = integration_adapter.list_doctypes(limit=50)

        assert isinstance(doctypes, list)
        assert len(doctypes) > 0

        # Vérifier que quelques DocTypes standard existent
        assert 'Customer' in doctypes
        assert 'User' in doctypes

    def test_global_search(self, integration_adapter):
        """Test recherche globale"""
        # Rechercher "customer"
        results = integration_adapter.global_search('customer', limit=10)

        assert isinstance(results, list)
        # Peut être vide, mais devrait contenir des résultats normalement


class TestIntegrationCache:
    """Tests d'intégration du cache"""

    def test_cache_effectiveness(self):
        """Test efficacité du cache"""
        adapter_with_cache = FrappeProxyAdapter(
            enable_cache=True,
            cache_ttl=60
        )

        # Premier appel (miss)
        result1 = adapter_with_cache.search_documents('Customer', limit=5)

        # Deuxième appel (hit)
        result2 = adapter_with_cache.search_documents('Customer', limit=5)

        # Devraient être identiques (même si c'est difficile à vérifier sans instrumentation)
        assert result1 == result2

        # Vérifier stats cache
        stats = adapter_with_cache.get_cache_stats()
        assert stats['total_entries'] > 0

    def test_cache_invalidation(self):
        """Test invalidation cache après modification"""
        adapter_with_cache = FrappeProxyAdapter(
            enable_cache=True,
            cache_ttl=60
        )

        # Rechercher (met en cache)
        results_before = adapter_with_cache.search_documents('Customer', limit=5)

        # Créer un document (devrait invalider cache)
        try:
            created = adapter_with_cache.create_document(
                'Customer',
                {'customer_name': 'CACHE_TEST', 'customer_type': 'Individual'}
            )

            # Rechercher à nouveau (cache invalidé)
            results_after = adapter_with_cache.search_documents('Customer', limit=5)

            # Les résultats peuvent être différents
            # (difficile à tester sans contrôle complet de la DB)

            # Cleanup
            adapter_with_cache.delete_document('Customer', created['name'])

        except Exception as e:
            print(f"Erreur test cache: {e}")


class TestIntegrationPerformance:
    """Tests de performance basiques"""

    def test_search_performance(self, integration_adapter):
        """Test performance recherche"""
        import time

        start = time.time()
        results = integration_adapter.search_documents('Customer', limit=100)
        duration = time.time() - start

        # Devrait prendre moins de 5 secondes
        assert duration < 5.0

        print(f"\nRecherche de {len(results)} clients en {duration:.2f}s")

    def test_pagination_performance(self, integration_adapter):
        """Test performance pagination auto"""
        import time

        start = time.time()
        results = integration_adapter.search_documents(
            'Customer',
            auto_paginate=True,
            limit=50  # 50 par page
        )
        duration = time.time() - start

        print(f"\nPagination auto: {len(results)} clients en {duration:.2f}s")

        # Devrait être raisonnablement rapide même avec beaucoup de résultats
        # (dépend du nombre de clients dans la DB)


if __name__ == '__main__':
    # Exécuter avec tests d'intégration
    pytest.main([__file__, '-v', '--integration'])
