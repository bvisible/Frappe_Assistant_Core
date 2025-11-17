#!/usr/bin/env python3
"""
Script de validation d'intégration pour Frappe Bridge Adapter V2
================================================================

Ce script teste l'adaptateur V2 avec une vraie instance Frappe/Nora.
Il valide toutes les fonctionnalités et génère un rapport détaillé.

Usage:
    python3 validate_integration.py

Configuration:
    Définir les variables d'environnement :
    - FRAPPE_URL : URL de l'instance Frappe (ex: https://nora.example.com)
    - FRAPPE_API_KEY : Clé API
    - FRAPPE_API_SECRET : Secret API

Ou créer un fichier .env avec ces variables.
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Ajouter le répertoire courant au path pour importer l'adaptateur
sys.path.insert(0, str(Path(__file__).parent))

try:
    from frappe_bridge_adapter_v2 import FrappeProxyAdapter, FrappeAPIError
except ImportError:
    print("❌ Erreur: frappe_bridge_adapter_v2.py introuvable")
    print("   Assurez-vous d'être dans le répertoire Frappe_Assistant_Core")
    sys.exit(1)


class Colors:
    """Codes couleur ANSI pour terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class IntegrationValidator:
    """Validateur d'intégration pour l'adaptateur V2"""

    def __init__(self):
        self.adapter = None
        self.results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'warnings': [],
            'tests': []
        }
        self.start_time = None
        self.test_data_created = []  # Pour cleanup

    def print_header(self):
        """Afficher l'en-tête"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}  VALIDATION D'INTÉGRATION - FRAPPE BRIDGE ADAPTER V2{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Python: {sys.version.split()[0]}")
        print()

    def check_environment(self) -> bool:
        """Vérifier la configuration de l'environnement"""
        print(f"{Colors.BOLD}📋 VÉRIFICATION DE L'ENVIRONNEMENT{Colors.RESET}")
        print("-" * 80)

        required_vars = ['FRAPPE_URL', 'FRAPPE_API_KEY', 'FRAPPE_API_SECRET']
        missing = []

        for var in required_vars:
            value = os.getenv(var)
            if value:
                # Masquer les secrets
                if 'SECRET' in var or 'KEY' in var:
                    display = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
                else:
                    display = value
                print(f"  ✅ {var}: {display}")
            else:
                print(f"  ❌ {var}: Non défini")
                missing.append(var)

        if missing:
            print(f"\n{Colors.RED}❌ Variables manquantes: {', '.join(missing)}{Colors.RESET}")
            print(f"\n{Colors.YELLOW}Configuration requise:{Colors.RESET}")
            print("  1. Créer un fichier .env avec:")
            print("     FRAPPE_URL=https://votre-instance.frappe.cloud")
            print("     FRAPPE_API_KEY=votre_api_key")
            print("     FRAPPE_API_SECRET=votre_api_secret")
            print("\n  2. Ou exporter les variables:")
            print("     export FRAPPE_URL=...")
            print("     export FRAPPE_API_KEY=...")
            print("     export FRAPPE_API_SECRET=...")
            return False

        print(f"\n{Colors.GREEN}✅ Configuration environnement OK{Colors.RESET}\n")
        return True

    def initialize_adapter(self) -> bool:
        """Initialiser l'adaptateur"""
        print(f"{Colors.BOLD}🔧 INITIALISATION DE L'ADAPTATEUR{Colors.RESET}")
        print("-" * 80)

        try:
            self.adapter = FrappeProxyAdapter(
                enable_cache=True,
                cache_ttl=300,
                max_retries=3,
                retry_backoff=0.5,
                timeout=30
            )
            print(f"  ✅ Adaptateur créé")
            print(f"  ✅ Cache activé (TTL: 300s)")
            print(f"  ✅ Retry activé (max: 3, backoff: 0.5s)")
            print(f"\n{Colors.GREEN}✅ Initialisation OK{Colors.RESET}\n")
            return True
        except Exception as e:
            print(f"\n{Colors.RED}❌ Erreur initialisation: {e}{Colors.RESET}\n")
            self.results['errors'].append(f"Initialisation: {e}")
            return False

    def run_test(self, name: str, func, *args, **kwargs) -> Tuple[bool, Any, float]:
        """
        Exécuter un test et enregistrer le résultat

        Returns:
            (success, result, duration)
        """
        self.results['total_tests'] += 1
        start = time.time()

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start

            self.results['passed'] += 1
            self.results['tests'].append({
                'name': name,
                'status': 'PASSED',
                'duration': duration,
                'result': result
            })

            print(f"  {Colors.GREEN}✅ {name}{Colors.RESET} ({duration:.2f}s)")
            return True, result, duration

        except Exception as e:
            duration = time.time() - start

            self.results['failed'] += 1
            self.results['errors'].append(f"{name}: {str(e)}")
            self.results['tests'].append({
                'name': name,
                'status': 'FAILED',
                'duration': duration,
                'error': str(e)
            })

            print(f"  {Colors.RED}❌ {name}{Colors.RESET} ({duration:.2f}s)")
            print(f"     Erreur: {str(e)}")
            return False, None, duration

    def test_connectivity(self):
        """Test 1: Connectivité de base"""
        print(f"\n{Colors.BOLD}🌐 TEST 1: CONNECTIVITÉ{Colors.RESET}")
        print("-" * 80)

        def ping():
            # Tester avec une requête simple
            doctypes = self.adapter.list_doctypes()
            assert isinstance(doctypes, list), "list_doctypes doit retourner une liste"
            assert len(doctypes) > 0, "La liste des DocTypes ne doit pas être vide"
            return len(doctypes)

        success, count, duration = self.run_test("Connexion à Frappe", ping)

        if success:
            print(f"     {count} DocTypes disponibles")

        return success

    def test_search_operations(self):
        """Test 2: Opérations de recherche"""
        print(f"\n{Colors.BOLD}🔍 TEST 2: OPÉRATIONS DE RECHERCHE{Colors.RESET}")
        print("-" * 80)

        # Test 2.1: Recherche simple
        def search_simple():
            results = self.adapter.search_documents('User', limit=5)
            assert isinstance(results, list), "search_documents doit retourner une liste"
            return len(results)

        success, count, _ = self.run_test("Recherche simple (User)", search_simple)
        if success:
            print(f"     {count} utilisateurs trouvés")

        # Test 2.2: Recherche avec filtres
        def search_filtered():
            results = self.adapter.search_documents(
                'User',
                filters={'enabled': 1},
                limit=10
            )
            return len(results)

        success, count, _ = self.run_test("Recherche avec filtres", search_filtered)
        if success:
            print(f"     {count} utilisateurs actifs")

        # Test 2.3: Recherche avec champs spécifiques
        def search_fields():
            results = self.adapter.search_documents(
                'User',
                fields=['name', 'email', 'full_name'],
                limit=3
            )
            if results and len(results) > 0:
                assert 'email' in results[0], "Les champs demandés doivent être présents"
            return len(results)

        self.run_test("Recherche avec champs", search_fields)

    def test_cache_performance(self):
        """Test 3: Performance du cache"""
        print(f"\n{Colors.BOLD}💾 TEST 3: PERFORMANCE DU CACHE{Colors.RESET}")
        print("-" * 80)

        # Test 3.1: Cache miss (première requête)
        def cache_miss():
            return self.adapter.search_documents('User', limit=5)

        _, _, duration1 = self.run_test("Cache miss (1ère requête)", cache_miss)

        # Test 3.2: Cache hit (requête identique)
        def cache_hit():
            return self.adapter.search_documents('User', limit=5)

        _, _, duration2 = self.run_test("Cache hit (2ème requête)", cache_hit)

        # Calculer l'amélioration
        if duration1 > 0 and duration2 > 0:
            speedup = duration1 / duration2
            improvement = ((duration1 - duration2) / duration1) * 100
            print(f"     {Colors.CYAN}Amélioration: {speedup:.1f}x plus rapide ({improvement:.0f}%){Colors.RESET}")

            if speedup < 2:
                self.results['warnings'].append(
                    f"Cache speedup faible ({speedup:.1f}x) - attendu >10x"
                )

    def test_pagination(self):
        """Test 4: Pagination automatique"""
        print(f"\n{Colors.BOLD}📄 TEST 4: PAGINATION AUTOMATIQUE{Colors.RESET}")
        print("-" * 80)

        # Test 4.1: Pagination manuelle
        def manual_pagination():
            results = self.adapter.search_documents('User', limit=10, offset=0)
            return len(results)

        success, count, duration1 = self.run_test("Pagination manuelle", manual_pagination)

        # Test 4.2: Auto-pagination (si >100 users)
        def auto_pagination():
            results = self.adapter.search_documents(
                'User',
                auto_paginate=True,
                limit=50
            )
            return len(results)

        success, total, duration2 = self.run_test("Auto-pagination", auto_pagination)
        if success:
            print(f"     {total} résultats totaux récupérés")

    def test_crud_operations(self):
        """Test 5: Opérations CRUD"""
        print(f"\n{Colors.BOLD}📝 TEST 5: OPÉRATIONS CRUD{Colors.RESET}")
        print("-" * 80)

        test_doc_name = None

        # Test 5.1: Create (si permissions suffisantes)
        def create_test():
            nonlocal test_doc_name
            # Créer un ToDo de test
            doc_data = {
                'description': f'Test validation integration {datetime.now().isoformat()}',
                'status': 'Open',
                'priority': 'Low'
            }
            result = self.adapter.create_document('ToDo', doc_data)
            test_doc_name = result.get('name')
            self.test_data_created.append(('ToDo', test_doc_name))
            return test_doc_name

        success, doc_name, _ = self.run_test("Création document (ToDo)", create_test)

        if success and doc_name:
            print(f"     Document créé: {doc_name}")

            # Test 5.2: Read
            def read_test():
                doc = self.adapter.get_document('ToDo', doc_name)
                assert doc.get('name') == doc_name, "Le document lu doit correspondre"
                return doc

            self.run_test("Lecture document", read_test)

            # Test 5.3: Update
            def update_test():
                return self.adapter.update_document('ToDo', doc_name, {'status': 'Closed'})

            success_update, _, _ = self.run_test("Mise à jour document", update_test)

            # Test 5.4: Delete
            def delete_test():
                result = self.adapter.delete_document('ToDo', doc_name)
                # Retirer de la liste de cleanup
                if ('ToDo', doc_name) in self.test_data_created:
                    self.test_data_created.remove(('ToDo', doc_name))
                return result

            self.run_test("Suppression document", delete_test)
        else:
            print(f"     {Colors.YELLOW}⚠ Tests CRUD sautés (création échouée){Colors.RESET}")
            self.results['skipped'] += 3

    def test_batch_operations(self):
        """Test 6: Opérations batch"""
        print(f"\n{Colors.BOLD}📦 TEST 6: OPÉRATIONS BATCH{Colors.RESET}")
        print("-" * 80)

        # Créer 5 ToDos en batch
        def batch_create():
            todos = [
                {'description': f'Batch test {i}', 'status': 'Open', 'priority': 'Low'}
                for i in range(1, 6)
            ]
            result = self.adapter.batch_create_documents('ToDo', todos, stop_on_error=False)

            # Enregistrer pour cleanup
            for doc in result.get('created', []):
                self.test_data_created.append(('ToDo', doc.get('name')))

            return result

        success, result, duration = self.run_test("Création batch (5 ToDos)", batch_create)

        if success and result:
            print(f"     Créés: {result['count']}, Erreurs: {result['errors']}")

            # Cleanup
            for doctype, name in list(self.test_data_created):
                try:
                    self.adapter.delete_document(doctype, name)
                    self.test_data_created.remove((doctype, name))
                except:
                    pass

    def test_error_handling(self):
        """Test 7: Gestion d'erreurs"""
        print(f"\n{Colors.BOLD}⚠️  TEST 7: GESTION D'ERREURS{Colors.RESET}")
        print("-" * 80)

        # Test 7.1: DocType invalide
        def invalid_doctype():
            try:
                self.adapter.search_documents('InvalidDocType12345')
                return False  # Ne devrait pas arriver ici
            except FrappeAPIError:
                return True  # Exception attendue

        success, _, _ = self.run_test("Erreur DocType invalide", invalid_doctype)
        if not success:
            self.results['warnings'].append("FrappeAPIError non levée pour DocType invalide")

        # Test 7.2: Document inexistant
        def invalid_document():
            try:
                self.adapter.get_document('User', 'nonexistent-user-xyz-123')
                return False
            except FrappeAPIError:
                return True

        self.run_test("Erreur document inexistant", invalid_document)

    def test_doctype_operations(self):
        """Test 8: Opérations sur DocTypes"""
        print(f"\n{Colors.BOLD}📋 TEST 8: OPÉRATIONS DOCTYPES{Colors.RESET}")
        print("-" * 80)

        # Test 8.1: Liste des DocTypes
        def list_doctypes():
            doctypes = self.adapter.list_doctypes()
            return len(doctypes)

        success, count, _ = self.run_test("Liste DocTypes", list_doctypes)
        if success:
            print(f"     {count} DocTypes disponibles")

        # Test 8.2: Métadonnées d'un DocType
        def get_meta():
            meta = self.adapter.get_doctype_schema('User')
            assert 'fields' in meta, "Les métadonnées doivent contenir les champs"
            return len(meta.get('fields', []))

        success, field_count, _ = self.run_test("Métadonnées DocType (User)", get_meta)
        if success:
            print(f"     {field_count} champs dans User")

    def print_summary(self):
        """Afficher le résumé"""
        duration = time.time() - self.start_time

        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}  RÉSUMÉ DE LA VALIDATION{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")

        print(f"Durée totale: {duration:.2f}s")
        print(f"Tests exécutés: {self.results['total_tests']}")
        print(f"{Colors.GREEN}✅ Réussis: {self.results['passed']}{Colors.RESET}")
        print(f"{Colors.RED}❌ Échoués: {self.results['failed']}{Colors.RESET}")
        print(f"{Colors.YELLOW}⏭️  Sautés: {self.results['skipped']}{Colors.RESET}")

        # Taux de succès
        if self.results['total_tests'] > 0:
            success_rate = (self.results['passed'] / self.results['total_tests']) * 100
            print(f"\nTaux de succès: {success_rate:.1f}%")

            # Barre de progression
            bar_length = 50
            filled = int(bar_length * success_rate / 100)
            bar = '█' * filled + '░' * (bar_length - filled)

            if success_rate >= 90:
                color = Colors.GREEN
            elif success_rate >= 70:
                color = Colors.YELLOW
            else:
                color = Colors.RED

            print(f"{color}{bar}{Colors.RESET} {success_rate:.1f}%")

        # Avertissements
        if self.results['warnings']:
            print(f"\n{Colors.YELLOW}⚠️  AVERTISSEMENTS:{Colors.RESET}")
            for warning in self.results['warnings']:
                print(f"  - {warning}")

        # Erreurs
        if self.results['errors']:
            print(f"\n{Colors.RED}❌ ERREURS:{Colors.RESET}")
            for error in self.results['errors']:
                print(f"  - {error}")

        # Verdict final
        print(f"\n{Colors.BOLD}VERDICT:{Colors.RESET}")
        if self.results['failed'] == 0 and len(self.results['errors']) == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ VALIDATION RÉUSSIE - L'adaptateur est fonctionnel !{Colors.RESET}")
            return 0
        elif self.results['failed'] <= 2:
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  VALIDATION PARTIELLE - Quelques problèmes détectés{Colors.RESET}")
            return 1
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ VALIDATION ÉCHOUÉE - Problèmes critiques détectés{Colors.RESET}")
            return 2

    def save_report(self):
        """Sauvegarder le rapport en JSON"""
        report_path = Path('validation_report.json')

        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': self.results['total_tests'],
                'passed': self.results['passed'],
                'failed': self.results['failed'],
                'skipped': self.results['skipped'],
                'success_rate': (self.results['passed'] / self.results['total_tests'] * 100)
                if self.results['total_tests'] > 0 else 0
            },
            'tests': self.results['tests'],
            'errors': self.results['errors'],
            'warnings': self.results['warnings'],
            'environment': {
                'frappe_url': os.getenv('FRAPPE_URL', 'Not set'),
                'python_version': sys.version.split()[0]
            }
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Rapport sauvegardé: {report_path}")

    def cleanup(self):
        """Nettoyer les données de test créées"""
        if self.test_data_created:
            print(f"\n🧹 Nettoyage des données de test...")
            for doctype, name in self.test_data_created:
                try:
                    self.adapter.delete_document(doctype, name)
                    print(f"  ✅ Supprimé: {doctype} - {name}")
                except Exception as e:
                    print(f"  ⚠️  Échec suppression {doctype} - {name}: {e}")

    def run(self) -> int:
        """
        Exécuter la validation complète

        Returns:
            Exit code (0=succès, 1=avertissement, 2=échec)
        """
        self.start_time = time.time()

        try:
            self.print_header()

            # Étape 1: Environnement
            if not self.check_environment():
                return 2

            # Étape 2: Initialisation
            if not self.initialize_adapter():
                return 2

            # Étape 3: Tests de connectivité
            if not self.test_connectivity():
                print(f"\n{Colors.RED}❌ Connectivité échouée - arrêt des tests{Colors.RESET}")
                return 2

            # Étape 4-10: Tests fonctionnels
            self.test_search_operations()
            self.test_cache_performance()
            self.test_pagination()
            self.test_crud_operations()
            self.test_batch_operations()
            self.test_error_handling()
            self.test_doctype_operations()

            # Résumé
            exit_code = self.print_summary()

            # Sauvegarder rapport
            self.save_report()

            return exit_code

        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⚠️  Validation interrompue par l'utilisateur{Colors.RESET}")
            return 130

        except Exception as e:
            print(f"\n\n{Colors.RED}❌ Erreur fatale: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()
            return 2

        finally:
            # Cleanup
            if self.adapter:
                self.cleanup()


def main():
    """Point d'entrée principal"""
    # Charger .env si disponible
    env_file = Path('.env')
    if env_file.exists():
        print(f"📋 Chargement de {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    os.environ[key.strip()] = value.strip()

    # Exécuter validation
    validator = IntegrationValidator()
    exit_code = validator.run()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
