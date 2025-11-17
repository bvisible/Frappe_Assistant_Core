"""
Adaptateur Frappe avancé pour le sandbox code execution.
Version améliorée avec pagination, cache, retry logic et batch operations.

Usage:
    from frappe_bridge_adapter_v2 import FrappeProxyAdapter

    adapter = FrappeProxyAdapter(enable_cache=True, max_retries=3)
    customers = adapter.search_documents('Customer', limit=100, auto_paginate=True)
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps

try:
    import httpx
except ImportError:
    import urllib.request
    import urllib.parse
    httpx = None


class CacheEntry:
    """Entry in the cache with TTL"""
    def __init__(self, data: Any, ttl: int = 300):
        self.data = data
        self.expires_at = datetime.now() + timedelta(seconds=ttl)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class FrappeAPIError(Exception):
    """Exception levée lors d'erreurs API Frappe"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


def with_retry(max_retries: int = 3, backoff_factor: float = 0.5):
    """
    Décorateur pour ajouter retry logic avec exponential backoff.

    Args:
        max_retries: Nombre max de tentatives
        backoff_factor: Facteur multiplicateur pour le délai (0.5, 1, 2, 4, ...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = backoff_factor * (2 ** attempt)
                        time.sleep(delay)
                    else:
                        raise last_exception
        return wrapper
    return decorator


class FrappeProxyAdapter:
    """
    Adaptateur avancé pour proxifier appels Frappe via HTTP API.

    Features:
    - Pagination automatique
    - Cache local avec TTL
    - Retry logic avec exponential backoff
    - Batch operations
    - Gestion d'erreurs robuste

    Args:
        enable_cache: Activer le cache local (défaut: False)
        cache_ttl: Durée de vie du cache en secondes (défaut: 300)
        max_retries: Nombre max de retries (défaut: 3)
        retry_backoff: Facteur backoff pour retry (défaut: 0.5)
        timeout: Timeout HTTP en secondes (défaut: 30)
    """

    def __init__(
        self,
        enable_cache: bool = False,
        cache_ttl: int = 300,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        timeout: int = 30
    ):
        self.base_url = os.getenv('FRAPPE_URL', 'http://localhost:8000')
        self.api_key = os.getenv('FRAPPE_API_KEY')
        self.api_secret = os.getenv('FRAPPE_API_SECRET')

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "FRAPPE_API_KEY et FRAPPE_API_SECRET requis. "
                "Configurez les variables d'environnement."
            )

        # Configuration
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.timeout = timeout

        # Cache local
        self._cache: Dict[str, CacheEntry] = {}

        # Client HTTP
        if httpx:
            self.client = httpx.Client(
                base_url=self.base_url,
                auth=(self.api_key, self.api_secret),
                timeout=self.timeout
            )
            self._use_httpx = True
        else:
            self._use_httpx = False

    def _get_cache_key(self, method: str, path: str, params: Optional[Dict] = None) -> str:
        """Générer clé de cache unique"""
        key_parts = [method, path]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        return ":".join(key_parts)

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Récupérer depuis le cache si disponible et valide"""
        if not self.enable_cache:
            return None

        entry = self._cache.get(cache_key)
        if entry and not entry.is_expired():
            return entry.data

        # Nettoyer entrée expirée
        if entry:
            del self._cache[cache_key]

        return None

    def _set_in_cache(self, cache_key: str, data: Any) -> None:
        """Stocker dans le cache"""
        if self.enable_cache:
            self._cache[cache_key] = CacheEntry(data, self.cache_ttl)

    def clear_cache(self) -> None:
        """Vider le cache"""
        self._cache.clear()

    @with_retry(max_retries=3, backoff_factor=0.5)
    def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Faire une requête HTTP avec retry et cache.

        Args:
            method: Méthode HTTP (GET, POST, PUT, DELETE)
            path: Chemin de l'endpoint
            params: Paramètres query string
            json_data: Données JSON pour POST/PUT
            use_cache: Utiliser le cache pour cette requête

        Returns:
            Réponse JSON parsée

        Raises:
            FrappeAPIError: Si erreur API
        """
        # Vérifier cache pour GET
        if method == 'GET' and use_cache:
            cache_key = self._get_cache_key(method, path, params)
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        # Faire la requête
        try:
            if self._use_httpx:
                response = self._make_httpx_request(method, path, params, json_data)
            else:
                response = self._make_urllib_request(method, path, params, json_data)

            # Mettre en cache si GET
            if method == 'GET' and use_cache:
                cache_key = self._get_cache_key(method, path, params)
                self._set_in_cache(cache_key, response)

            return response

        except Exception as e:
            raise FrappeAPIError(f"Erreur requête {method} {path}: {e}")

    def _make_httpx_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict],
        json_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """Requête avec httpx"""
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

    def _make_urllib_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict],
        json_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """Requête avec urllib (fallback)"""
        url = f"{self.base_url}{path}"

        if params:
            url += '?' + urllib.parse.urlencode(params)

        headers = {
            'Authorization': f'token {self.api_key}:{self.api_secret}',
            'Content-Type': 'application/json'
        }

        data = json.dumps(json_data).encode('utf-8') if json_data else None

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode('utf-8'))

    def search_documents(
        self,
        doctype: str,
        filters: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        auto_paginate: bool = False,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Recherche documents avec pagination automatique.

        Args:
            doctype: Type de document
            filters: Filtres de recherche
            fields: Champs à retourner
            order_by: Ordre de tri
            limit: Nombre de résultats par page
            offset: Offset de départ
            auto_paginate: Si True, récupère tous les résultats (attention: peut être lent)
            use_cache: Utiliser le cache

        Returns:
            Liste de documents

        Example:
            # Récupérer tous les clients (avec pagination auto)
            all_customers = adapter.search_documents(
                'Customer',
                auto_paginate=True,
                limit=100  # 100 par page
            )
        """
        if not auto_paginate:
            # Recherche simple
            params = {
                'filters': json.dumps(filters) if filters else '{}',
                'fields': json.dumps(fields) if fields else '["*"]',
                'order_by': order_by or 'modified desc',
                'limit_page_length': limit,
                'limit_start': offset
            }

            result = self._make_request('GET', f'/api/resource/{doctype}', params=params, use_cache=use_cache)
            return result.get('data', [])

        # Pagination automatique
        all_results = []
        current_offset = offset

        while True:
            params = {
                'filters': json.dumps(filters) if filters else '{}',
                'fields': json.dumps(fields) if fields else '["*"]',
                'order_by': order_by or 'modified desc',
                'limit_page_length': limit,
                'limit_start': current_offset
            }

            result = self._make_request('GET', f'/api/resource/{doctype}', params=params, use_cache=use_cache)
            batch = result.get('data', [])

            if not batch:
                break

            all_results.extend(batch)

            # Si moins de résultats que la limite, on a tout
            if len(batch) < limit:
                break

            current_offset += limit

        return all_results

    def get_document(
        self,
        doctype: str,
        name: str,
        fields: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Récupérer un document spécifique.

        Args:
            doctype: Type de document
            name: Nom/ID du document
            fields: Champs à retourner
            use_cache: Utiliser le cache

        Returns:
            Document
        """
        params = {}
        if fields:
            params['fields'] = json.dumps(fields)

        result = self._make_request(
            'GET',
            f'/api/resource/{doctype}/{name}',
            params=params if params else None,
            use_cache=use_cache
        )
        return result.get('data', {})

    def create_document(
        self,
        doctype: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Créer un document"""
        payload = {'doctype': doctype, **data}
        result = self._make_request('POST', f'/api/resource/{doctype}', json_data=payload, use_cache=False)

        # Invalider cache pour ce doctype
        if self.enable_cache:
            self._invalidate_cache_for_doctype(doctype)

        return result.get('data', {})

    def update_document(
        self,
        doctype: str,
        name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mettre à jour un document"""
        result = self._make_request('PUT', f'/api/resource/{doctype}/{name}', json_data=data, use_cache=False)

        # Invalider cache
        if self.enable_cache:
            self._invalidate_cache_for_doctype(doctype)

        return result.get('data', {})

    def delete_document(
        self,
        doctype: str,
        name: str
    ) -> Dict[str, str]:
        """Supprimer un document"""
        self._make_request('DELETE', f'/api/resource/{doctype}/{name}', use_cache=False)

        # Invalider cache
        if self.enable_cache:
            self._invalidate_cache_for_doctype(doctype)

        return {'success': True, 'message': f'{doctype} {name} deleted'}

    def batch_create_documents(
        self,
        doctype: str,
        documents: List[Dict[str, Any]],
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Créer plusieurs documents en batch.

        Args:
            doctype: Type de document
            documents: Liste de documents à créer
            stop_on_error: Si True, arrête au premier échec

        Returns:
            Dictionnaire avec résultats:
            {
                'created': [liste des docs créés],
                'failed': [liste des erreurs],
                'count': nombre créés,
                'errors': nombre d'erreurs
            }
        """
        results = {
            'created': [],
            'failed': [],
            'count': 0,
            'errors': 0
        }

        for i, doc_data in enumerate(documents):
            try:
                created = self.create_document(doctype, doc_data)
                results['created'].append(created)
                results['count'] += 1
            except Exception as e:
                results['failed'].append({
                    'index': i,
                    'data': doc_data,
                    'error': str(e)
                })
                results['errors'] += 1

                if stop_on_error:
                    break

        return results

    def get_doctype_schema(
        self,
        doctype: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Récupérer métadonnées d'un DocType"""
        result = self._make_request('GET', f'/api/resource/DocType/{doctype}', use_cache=use_cache)

        meta = result.get('data', {})
        return {
            'name': meta.get('name'),
            'fields': meta.get('fields', []),
            'permissions': meta.get('permissions', []),
            'is_submittable': meta.get('is_submittable', 0),
            'track_changes': meta.get('track_changes', 0)
        }

    def list_doctypes(
        self,
        limit: int = 999,
        use_cache: bool = True
    ) -> List[str]:
        """Lister tous les DocTypes"""
        result = self._make_request(
            'GET',
            '/api/resource/DocType',
            params={'limit_page_length': limit},
            use_cache=use_cache
        )
        docs = result.get('data', [])
        return [doc.get('name') for doc in docs if doc.get('name')]

    def global_search(
        self,
        text: str,
        limit: int = 20,
        use_cache: bool = False
    ) -> List[Dict[str, Any]]:
        """Recherche globale"""
        params = {'text': text, 'limit': limit}
        result = self._make_request(
            'GET',
            '/api/method/frappe.desk.search.search_link',
            params=params,
            use_cache=use_cache
        )
        return result.get('message', [])

    def _invalidate_cache_for_doctype(self, doctype: str) -> None:
        """Invalider toutes les entrées cache pour un doctype"""
        keys_to_delete = [
            key for key in self._cache.keys()
            if doctype in key
        ]
        for key in keys_to_delete:
            del self._cache[key]

    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        total = len(self._cache)
        expired = sum(1 for entry in self._cache.values() if entry.is_expired())
        active = total - expired

        return {
            'total_entries': total,
            'active_entries': active,
            'expired_entries': expired,
            'hit_rate': 'N/A'  # TODO: tracker hits/misses
        }

    def __del__(self):
        """Cleanup"""
        if hasattr(self, '_use_httpx') and self._use_httpx and hasattr(self, 'client'):
            try:
                self.client.close()
            except:
                pass


__all__ = ['FrappeProxyAdapter', 'FrappeAPIError']
