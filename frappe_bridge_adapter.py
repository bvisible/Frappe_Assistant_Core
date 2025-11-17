"""
Adaptateur Frappe pour le sandbox code execution.
Permet d'appeler les APIs Frappe depuis le code Python exécuté dans le sandbox.

Usage dans le sandbox:
    from frappe_bridge_adapter import FrappeProxyAdapter

    adapter = FrappeProxyAdapter()
    customers = adapter.search_documents('Customer', limit=5)
"""

import os
import json
from typing import Dict, List, Any, Optional

try:
    import httpx
except ImportError:
    # Fallback pour environnements sans httpx
    import urllib.request
    import urllib.parse
    httpx = None


class FrappeProxyAdapter:
    """
    Adaptateur pour proxifier appels Frappe via HTTP API.

    Utilise les credentials depuis les variables d'environnement:
    - FRAPPE_URL: URL de base Frappe (ex: http://localhost:8000)
    - FRAPPE_API_KEY: Clé API Frappe
    - FRAPPE_API_SECRET: Secret API Frappe
    """

    def __init__(self):
        self.base_url = os.getenv('FRAPPE_URL', 'http://localhost:8000')
        self.api_key = os.getenv('FRAPPE_API_KEY')
        self.api_secret = os.getenv('FRAPPE_API_SECRET')

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "FRAPPE_API_KEY et FRAPPE_API_SECRET requis. "
                "Assurez-vous que les variables d'environnement sont configurées."
            )

        # Utiliser httpx si disponible, sinon urllib
        if httpx:
            self.client = httpx.Client(
                base_url=self.base_url,
                auth=(self.api_key, self.api_secret),
                timeout=30.0
            )
            self._use_httpx = True
        else:
            self._use_httpx = False

    def _make_request(self, method: str, path: str, params: Optional[Dict] = None,
                     json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Helper pour faire des requêtes HTTP (httpx ou urllib)"""

        if self._use_httpx:
            # Utiliser httpx
            if method == 'GET':
                response = self.client.get(path, params=params)
            elif method == 'POST':
                response = self.client.post(path, json=json_data)
            elif method == 'PUT':
                response = self.client.put(path, json=json_data)
            elif method == 'DELETE':
                response = self.client.delete(path)
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")

            response.raise_for_status()
            return response.json()
        else:
            # Fallback urllib
            url = f"{self.base_url}{path}"

            if params:
                url += '?' + urllib.parse.urlencode(params)

            headers = {
                'Authorization': f'token {self.api_key}:{self.api_secret}',
                'Content-Type': 'application/json'
            }

            if json_data:
                data = json.dumps(json_data).encode('utf-8')
            else:
                data = None

            req = urllib.request.Request(url, data=data, headers=headers, method=method)

            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))

    def search_documents(
        self,
        doctype: str,
        filters: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Recherche documents via API Frappe.

        Args:
            doctype: Type de document (ex: 'Customer', 'Sales Order')
            filters: Filtres de recherche (ex: {'status': 'Open'})
            fields: Champs à retourner (défaut: tous)
            order_by: Ordre de tri (ex: 'modified desc')
            limit: Nombre max de résultats

        Returns:
            Liste de documents trouvés

        Example:
            customers = adapter.search_documents(
                doctype='Customer',
                filters={'customer_group': 'VIP'},
                fields=['name', 'customer_name', 'email_id'],
                limit=10
            )
        """
        params = {
            'filters': json.dumps(filters) if filters else '{}',
            'fields': json.dumps(fields) if fields else '["*"]',
            'order_by': order_by or 'modified desc',
            'limit_page_length': limit
        }

        result = self._make_request('GET', f'/api/resource/{doctype}', params=params)
        return result.get('data', [])

    def get_document(
        self,
        doctype: str,
        name: str,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Récupérer un document spécifique.

        Args:
            doctype: Type de document
            name: Nom/ID du document
            fields: Champs à retourner (défaut: tous)

        Returns:
            Document trouvé

        Example:
            customer = adapter.get_document('Customer', 'CUST-00001')
        """
        params = {}
        if fields:
            params['fields'] = json.dumps(fields)

        result = self._make_request(
            'GET',
            f'/api/resource/{doctype}/{name}',
            params=params if params else None
        )
        return result.get('data', {})

    def create_document(
        self,
        doctype: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Créer un nouveau document.

        Args:
            doctype: Type de document à créer
            data: Données du document

        Returns:
            Document créé avec son ID

        Example:
            customer = adapter.create_document(
                doctype='Customer',
                data={
                    'customer_name': 'Acme Corp',
                    'customer_type': 'Company'
                }
            )
        """
        payload = {
            'doctype': doctype,
            **data
        }

        result = self._make_request('POST', f'/api/resource/{doctype}', json_data=payload)
        return result.get('data', {})

    def update_document(
        self,
        doctype: str,
        name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Mettre à jour un document existant.

        Args:
            doctype: Type de document
            name: Nom/ID du document
            data: Nouvelles données

        Returns:
            Document mis à jour

        Example:
            customer = adapter.update_document(
                doctype='Customer',
                name='CUST-00001',
                data={'customer_name': 'Acme Corp Updated'}
            )
        """
        result = self._make_request('PUT', f'/api/resource/{doctype}/{name}', json_data=data)
        return result.get('data', {})

    def delete_document(
        self,
        doctype: str,
        name: str
    ) -> Dict[str, str]:
        """
        Supprimer un document.

        Args:
            doctype: Type de document
            name: Nom/ID du document

        Returns:
            Confirmation de suppression

        Example:
            result = adapter.delete_document('Customer', 'CUST-00001')
        """
        self._make_request('DELETE', f'/api/resource/{doctype}/{name}')
        return {'success': True, 'message': f'{doctype} {name} deleted'}

    def get_doctype_schema(self, doctype: str) -> Dict[str, Any]:
        """
        Récupérer les métadonnées d'un DocType.

        Args:
            doctype: Nom du DocType

        Returns:
            Schéma du DocType avec champs et permissions

        Example:
            schema = adapter.get_doctype_schema('Customer')
            for field in schema['fields']:
                print(f"{field['fieldname']}: {field['fieldtype']}")
        """
        result = self._make_request('GET', f'/api/resource/DocType/{doctype}')

        meta = result.get('data', {})
        return {
            'name': meta.get('name'),
            'fields': meta.get('fields', []),
            'permissions': meta.get('permissions', []),
            'is_submittable': meta.get('is_submittable', 0),
            'track_changes': meta.get('track_changes', 0)
        }

    def list_doctypes(self) -> List[str]:
        """
        Lister tous les DocTypes disponibles.

        Returns:
            Liste des noms de DocTypes

        Example:
            doctypes = adapter.list_doctypes()
            print(f"Trouvé {len(doctypes)} DocTypes")
        """
        result = self._make_request('GET', '/api/resource/DocType', params={'limit_page_length': 999})
        docs = result.get('data', [])
        return [doc.get('name') for doc in docs if doc.get('name')]

    def global_search(self, text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Recherche globale dans tous les documents.

        Args:
            text: Texte à rechercher
            limit: Nombre max de résultats

        Returns:
            Liste de résultats avec doctype et nom

        Example:
            results = adapter.global_search('acme', limit=10)
            for r in results:
                print(f"{r['doctype']}: {r['name']}")
        """
        params = {
            'text': text,
            'limit': limit
        }
        result = self._make_request('GET', '/api/method/frappe.desk.search.search_link', params=params)
        return result.get('message', [])

    def __del__(self):
        """Cleanup httpx client si utilisé"""
        if hasattr(self, '_use_httpx') and self._use_httpx and hasattr(self, 'client'):
            try:
                self.client.close()
            except:
                pass


# Pour import facile dans le sandbox
__all__ = ['FrappeProxyAdapter']
