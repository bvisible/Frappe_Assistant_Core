"""
Configuration pytest et fixtures partagées
"""

import pytest
import os
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock des variables d'environnement Frappe"""
    monkeypatch.setenv('FRAPPE_URL', 'http://test.localhost:8000')
    monkeypatch.setenv('FRAPPE_API_KEY', 'test_api_key')
    monkeypatch.setenv('FRAPPE_API_SECRET', 'test_api_secret')


@pytest.fixture
def sample_customer():
    """Exemple de document Customer"""
    return {
        'name': 'CUST-00001',
        'customer_name': 'Test Customer',
        'customer_type': 'Company',
        'email_id': 'test@example.com',
        'mobile_no': '+1234567890',
        'outstanding_amount': 5000.0
    }


@pytest.fixture
def sample_customers_list():
    """Liste d'exemples de customers"""
    return [
        {
            'name': 'CUST-00001',
            'customer_name': 'Customer One',
            'customer_type': 'Company'
        },
        {
            'name': 'CUST-00002',
            'customer_name': 'Customer Two',
            'customer_type': 'Individual'
        },
        {
            'name': 'CUST-00003',
            'customer_name': 'Customer Three',
            'customer_type': 'Company'
        }
    ]


@pytest.fixture
def mock_httpx_client():
    """Mock du client httpx"""
    client = MagicMock()
    client.get = Mock()
    client.post = Mock()
    client.put = Mock()
    client.delete = Mock()
    client.close = Mock()
    return client


@pytest.fixture
def mock_frappe_response():
    """Factory pour créer des réponses Frappe mockées"""
    def _create_response(data, status_code=200):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = {'data': data}
        response.raise_for_status = Mock()
        return response
    return _create_response
