"""
Tests unitaires pour les fonctionnalités de base de FrappeProxyAdapter
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frappe_bridge_adapter_v2 import FrappeProxyAdapter, FrappeAPIError


class TestAdapterInitialization:
    """Tests d'initialisation de l'adaptateur"""

    def test_init_with_env_vars(self, mock_env_vars):
        """Test initialisation avec variables d'environnement"""
        adapter = FrappeProxyAdapter()

        assert adapter.base_url == 'http://test.localhost:8000'
        assert adapter.api_key == 'test_api_key'
        assert adapter.api_secret == 'test_api_secret'

    def test_init_without_credentials(self, monkeypatch):
        """Test qu'une erreur est levée sans credentials"""
        monkeypatch.delenv('FRAPPE_API_KEY', raising=False)
        monkeypatch.delenv('FRAPPE_API_SECRET', raising=False)

        with pytest.raises(ValueError, match="FRAPPE_API_KEY et FRAPPE_API_SECRET requis"):
            FrappeProxyAdapter()

    def test_init_with_custom_config(self, mock_env_vars):
        """Test initialisation avec configuration custom"""
        adapter = FrappeProxyAdapter(
            enable_cache=True,
            cache_ttl=600,
            max_retries=5,
            timeout=60
        )

        assert adapter.enable_cache is True
        assert adapter.cache_ttl == 600
        assert adapter.max_retries == 5
        assert adapter.timeout == 60


class TestCaching:
    """Tests du système de cache"""

    def test_cache_disabled_by_default(self, mock_env_vars):
        """Test que le cache est désactivé par défaut"""
        adapter = FrappeProxyAdapter()
        assert adapter.enable_cache is False

    def test_cache_enabled(self, mock_env_vars):
        """Test activation du cache"""
        adapter = FrappeProxyAdapter(enable_cache=True)
        assert adapter.enable_cache is True

    def test_cache_key_generation(self, mock_env_vars):
        """Test génération de clés de cache"""
        adapter = FrappeProxyAdapter()

        key1 = adapter._get_cache_key('GET', '/api/resource/Customer', {'limit': 10})
        key2 = adapter._get_cache_key('GET', '/api/resource/Customer', {'limit': 10})
        key3 = adapter._get_cache_key('GET', '/api/resource/Customer', {'limit': 20})

        assert key1 == key2  # Mêmes paramètres = même clé
        assert key1 != key3  # Paramètres différents = clés différentes

    def test_cache_set_and_get(self, mock_env_vars):
        """Test stockage et récupération du cache"""
        adapter = FrappeProxyAdapter(enable_cache=True)

        test_data = {'name': 'CUST-001', 'customer_name': 'Test'}
        cache_key = 'test_key'

        # Stocker
        adapter._set_in_cache(cache_key, test_data)

        # Récupérer
        cached = adapter._get_from_cache(cache_key)
        assert cached == test_data

    def test_cache_expiration(self, mock_env_vars):
        """Test expiration du cache"""
        adapter = FrappeProxyAdapter(enable_cache=True, cache_ttl=0)  # TTL = 0s

        test_data = {'test': 'data'}
        cache_key = 'test_key'

        adapter._set_in_cache(cache_key, test_data)

        import time
        time.sleep(0.1)  # Attendre expiration

        # Cache doit être expiré
        cached = adapter._get_from_cache(cache_key)
        assert cached is None

    def test_clear_cache(self, mock_env_vars):
        """Test vidage du cache"""
        adapter = FrappeProxyAdapter(enable_cache=True)

        adapter._set_in_cache('key1', {'data': 1})
        adapter._set_in_cache('key2', {'data': 2})

        assert len(adapter._cache) == 2

        adapter.clear_cache()

        assert len(adapter._cache) == 0


class TestSearchDocuments:
    """Tests de la méthode search_documents"""

    @patch('frappe_bridge_adapter_v2.httpx')
    def test_search_documents_basic(self, mock_httpx, mock_env_vars, sample_customers_list):
        """Test recherche basique"""
        # Mock httpx
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.json.return_value = {'data': sample_customers_list}
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        adapter = FrappeProxyAdapter()
        adapter.client = mock_client
        adapter._use_httpx = True

        # Rechercher
        results = adapter.search_documents('Customer', limit=10)

        assert len(results) == 3
        assert results[0]['name'] == 'CUST-00001'
        mock_client.get.assert_called_once()

    @patch('frappe_bridge_adapter_v2.httpx')
    def test_search_with_filters(self, mock_httpx, mock_env_vars, sample_customers_list):
        """Test recherche avec filtres"""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.json.return_value = {'data': [sample_customers_list[0]]}
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        adapter = FrappeProxyAdapter()
        adapter.client = mock_client
        adapter._use_httpx = True

        # Rechercher avec filtre
        results = adapter.search_documents(
            'Customer',
            filters={'customer_type': 'Company'},
            limit=10
        )

        assert len(results) == 1
        assert results[0]['customer_type'] == 'Company'

    @patch('frappe_bridge_adapter_v2.httpx')
    def test_search_with_pagination(self, mock_httpx, mock_env_vars):
        """Test pagination automatique"""
        mock_client = MagicMock()

        # Simuler 2 pages de résultats
        page1 = [{'name': f'CUST-{i:05d}'} for i in range(1, 101)]
        page2 = [{'name': f'CUST-{i:05d}'} for i in range(101, 151)]

        mock_response_1 = Mock()
        mock_response_1.json.return_value = {'data': page1}
        mock_response_1.raise_for_status = Mock()

        mock_response_2 = Mock()
        mock_response_2.json.return_value = {'data': page2}
        mock_response_2.raise_for_status = Mock()

        mock_client.get.side_effect = [mock_response_1, mock_response_2]
        mock_httpx.Client.return_value = mock_client

        adapter = FrappeProxyAdapter()
        adapter.client = mock_client
        adapter._use_httpx = True

        # Rechercher avec pagination auto
        results = adapter.search_documents(
            'Customer',
            auto_paginate=True,
            limit=100
        )

        assert len(results) == 150  # 100 + 50
        assert mock_client.get.call_count == 2  # 2 pages

class TestGetDocument:
    """Tests de la méthode get_document"""

    @patch('frappe_bridge_adapter_v2.httpx')
    def test_get_document_success(self, mock_httpx, mock_env_vars, sample_customer):
        """Test récupération d'un document"""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.json.return_value = {'data': sample_customer}
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        adapter = FrappeProxyAdapter()
        adapter.client = mock_client
        adapter._use_httpx = True

        result = adapter.get_document('Customer', 'CUST-00001')

        assert result['name'] == 'CUST-00001'
        assert result['customer_name'] == 'Test Customer'

    @patch('frappe_bridge_adapter_v2.httpx')
    def test_get_document_with_fields(self, mock_httpx, mock_env_vars, sample_customer):
        """Test récupération avec sélection de champs"""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.json.return_value = {'data': {'name': 'CUST-00001', 'customer_name': 'Test'}}
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        adapter = FrappeProxyAdapter()
        adapter.client = mock_client
        adapter._use_httpx = True

        result = adapter.get_document('Customer', 'CUST-00001', fields=['name', 'customer_name'])

        assert 'name' in result
        assert 'customer_name' in result


class TestBatchOperations:
    """Tests des opérations batch"""

    @patch('frappe_bridge_adapter_v2.httpx')
    def test_batch_create_success(self, mock_httpx, mock_env_vars):
        """Test création batch réussie"""
        mock_client = MagicMock()

        # Mock 3 créations réussies
        responses = []
        for i in range(1, 4):
            mock_response = Mock()
            mock_response.json.return_value = {'data': {'name': f'CUST-{i:05d}'}}
            mock_response.raise_for_status = Mock()
            responses.append(mock_response)

        mock_client.post.side_effect = responses
        mock_httpx.Client.return_value = mock_client

        adapter = FrappeProxyAdapter()
        adapter.client = mock_client
        adapter._use_httpx = True

        docs = [
            {'customer_name': 'Customer 1'},
            {'customer_name': 'Customer 2'},
            {'customer_name': 'Customer 3'}
        ]

        result = adapter.batch_create_documents('Customer', docs)

        assert result['count'] == 3
        assert result['errors'] == 0
        assert len(result['created']) == 3
        assert len(result['failed']) == 0

    @patch('frappe_bridge_adapter_v2.httpx')
    def test_batch_create_with_errors(self, mock_httpx, mock_env_vars):
        """Test création batch avec erreurs"""
        mock_client = MagicMock()

        # Mock: succès, échec, succès
        responses = [
            Mock(json=lambda: {'data': {'name': 'CUST-00001'}}, raise_for_status=Mock()),
            Mock(side_effect=Exception("Erreur création")),
            Mock(json=lambda: {'data': {'name': 'CUST-00003'}}, raise_for_status=Mock())
        ]

        mock_client.post.side_effect = responses
        mock_httpx.Client.return_value = mock_client

        adapter = FrappeProxyAdapter()
        adapter.client = mock_client
        adapter._use_httpx = True

        docs = [
            {'customer_name': 'Customer 1'},
            {'customer_name': 'Customer 2'},  # Va échouer
            {'customer_name': 'Customer 3'}
        ]

        result = adapter.batch_create_documents('Customer', docs, stop_on_error=False)

        assert result['count'] == 2  # 2 succès
        assert result['errors'] == 1  # 1 échec
        assert len(result['failed']) == 1
        assert result['failed'][0]['index'] == 1


class TestErrorHandling:
    """Tests de gestion d'erreurs"""

    @patch('frappe_bridge_adapter_v2.httpx')
    def test_http_error_handling(self, mock_httpx, mock_env_vars):
        """Test gestion erreurs HTTP"""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        adapter = FrappeProxyAdapter()
        adapter.client = mock_client
        adapter._use_httpx = True

        with pytest.raises(FrappeAPIError):
            adapter.search_documents('InvalidDocType')

    @patch('frappe_bridge_adapter_v2.httpx')
    def test_retry_logic(self, mock_httpx, mock_env_vars):
        """Test logique de retry"""
        mock_client = MagicMock()

        # Échec 2 fois, puis succès
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = Exception("Erreur temporaire")

        mock_response_success = Mock()
        mock_response_success.json.return_value = {'data': []}
        mock_response_success.raise_for_status = Mock()

        mock_client.get.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success
        ]
        mock_httpx.Client.return_value = mock_client

        adapter = FrappeProxyAdapter(max_retries=3)
        adapter.client = mock_client
        adapter._use_httpx = True

        # Devrait réussir au 3ème essai
        result = adapter.search_documents('Customer')

        assert result == []
        assert mock_client.get.call_count == 3  # 2 échecs + 1 succès


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
