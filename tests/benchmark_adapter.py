"""
Benchmarks de performance pour FrappeProxyAdapter.

Compare les performances entre :
- Avec/sans cache
- Avec/sans pagination automatique
- Opérations simples vs batch

Utilisation:
    python tests/benchmark_adapter.py
"""

import os
import sys
import time
from statistics import mean, stdev

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frappe_bridge_adapter_v2 import FrappeProxyAdapter


class BenchmarkRunner:
    """Runner pour les benchmarks"""

    def __init__(self):
        self.results = {}

    def benchmark(self, name: str, func, iterations: int = 5):
        """
        Exécuter un benchmark.

        Args:
            name: Nom du benchmark
            func: Fonction à benchmarker
            iterations: Nombre d'itérations
        """
        print(f"\n🔄 Benchmark: {name}")
        print(f"   Itérations: {iterations}")

        times = []
        for i in range(iterations):
            start = time.time()
            result = func()
            duration = time.time() - start
            times.append(duration)
            print(f"   Run {i+1}: {duration:.3f}s")

        avg = mean(times)
        std = stdev(times) if len(times) > 1 else 0

        print(f"   ✅ Moyenne: {avg:.3f}s (±{std:.3f}s)")

        self.results[name] = {
            'avg': avg,
            'std': std,
            'min': min(times),
            'max': max(times),
            'times': times
        }

        return avg

    def compare(self, name1: str, name2: str):
        """Comparer deux benchmarks"""
        if name1 not in self.results or name2 not in self.results:
            print("❌ Benchmarks manquants pour comparaison")
            return

        avg1 = self.results[name1]['avg']
        avg2 = self.results[name2]['avg']

        improvement = ((avg1 - avg2) / avg1) * 100
        faster = avg1 / avg2

        print(f"\n📊 Comparaison: {name1} vs {name2}")
        print(f"   {name1}: {avg1:.3f}s")
        print(f"   {name2}: {avg2:.3f}s")

        if improvement > 0:
            print(f"   ✅ {name2} est {faster:.1f}x plus rapide ({improvement:.1f}% plus rapide)")
        else:
            print(f"   ⚠️  {name2} est {abs(faster):.1f}x plus lent ({abs(improvement):.1f}% plus lent)")

    def report(self):
        """Afficher rapport complet"""
        print("\n" + "=" * 60)
        print("RAPPORT BENCHMARKS")
        print("=" * 60)

        sorted_results = sorted(self.results.items(), key=lambda x: x[1]['avg'])

        for name, stats in sorted_results:
            print(f"\n{name}:")
            print(f"  Moyenne: {stats['avg']:.3f}s")
            print(f"  Min: {stats['min']:.3f}s")
            print(f"  Max: {stats['max']:.3f}s")
            print(f"  Écart-type: {stats['std']:.3f}s")


def benchmark_search_without_cache():
    """Benchmark: Recherche sans cache"""
    print("\n" + "=" * 60)
    print("BENCHMARK 1: Recherche sans cache")
    print("=" * 60)

    adapter = FrappeProxyAdapter(enable_cache=False)
    runner = BenchmarkRunner()

    def search_10():
        return adapter.search_documents('Customer', limit=10)

    def search_100():
        return adapter.search_documents('Customer', limit=100)

    runner.benchmark("Recherche 10 clients (sans cache)", search_10, iterations=3)
    runner.benchmark("Recherche 100 clients (sans cache)", search_100, iterations=3)

    return runner


def benchmark_search_with_cache():
    """Benchmark: Recherche avec cache"""
    print("\n" + "=" * 60)
    print("BENCHMARK 2: Recherche avec cache")
    print("=" * 60)

    adapter = FrappeProxyAdapter(enable_cache=True, cache_ttl=300)
    runner = BenchmarkRunner()

    def search_10_first():
        """Premier appel (cache miss)"""
        adapter.clear_cache()  # S'assurer que cache est vide
        return adapter.search_documents('Customer', limit=10)

    def search_10_cached():
        """Deuxième appel (cache hit)"""
        return adapter.search_documents('Customer', limit=10)

    # Premier appel
    runner.benchmark("Recherche 10 clients (cache miss)", search_10_first, iterations=3)

    # Deuxième appel (cache hit)
    runner.benchmark("Recherche 10 clients (cache hit)", search_10_cached, iterations=5)

    runner.compare("Recherche 10 clients (cache miss)", "Recherche 10 clients (cache hit)")

    return runner


def benchmark_pagination():
    """Benchmark: Pagination automatique"""
    print("\n" + "=" * 60)
    print("BENCHMARK 3: Pagination")
    print("=" * 60)

    adapter = FrappeProxyAdapter(enable_cache=False)
    runner = BenchmarkRunner()

    def pagination_manual():
        """Pagination manuelle (simulée)"""
        all_results = []
        offset = 0
        limit = 50

        for _ in range(3):  # 3 pages
            results = adapter.search_documents('Customer', limit=limit, offset=offset)
            all_results.extend(results)
            if len(results) < limit:
                break
            offset += limit

        return all_results

    def pagination_auto():
        """Pagination automatique"""
        return adapter.search_documents('Customer', auto_paginate=True, limit=50)

    runner.benchmark("Pagination manuelle (3 pages)", pagination_manual, iterations=2)
    runner.benchmark("Pagination automatique", pagination_auto, iterations=2)

    runner.compare("Pagination manuelle (3 pages)", "Pagination automatique")

    return runner


def benchmark_batch_operations():
    """Benchmark: Opérations batch"""
    print("\n" + "=" * 60)
    print("BENCHMARK 4: Opérations batch")
    print("=" * 60)

    adapter = FrappeProxyAdapter(enable_cache=False)
    runner = BenchmarkRunner()

    # Préparer données test
    test_docs = [
        {'customer_name': f'BENCH_TEST_{i}', 'customer_type': 'Individual'}
        for i in range(10)
    ]

    def create_individual():
        """Création individuelle (10 docs)"""
        created = []
        for doc in test_docs:
            try:
                result = adapter.create_document('Customer', doc)
                created.append(result['name'])
            except:
                pass
        # Cleanup
        for name in created:
            try:
                adapter.delete_document('Customer', name)
            except:
                pass
        return len(created)

    def create_batch():
        """Création batch (10 docs)"""
        result = adapter.batch_create_documents('Customer', test_docs)
        # Cleanup
        for doc in result['created']:
            try:
                adapter.delete_document('Customer', doc['name'])
            except:
                pass
        return result['count']

    print("⚠️  Attention: Ce benchmark crée et supprime des documents")
    input("Appuyez sur Enter pour continuer...")

    runner.benchmark("Création individuelle (10 docs)", create_individual, iterations=2)
    runner.benchmark("Création batch (10 docs)", create_batch, iterations=2)

    runner.compare("Création individuelle (10 docs)", "Création batch (10 docs)")

    return runner


def benchmark_retry_logic():
    """Benchmark: Impact du retry logic"""
    print("\n" + "=" * 60)
    print("BENCHMARK 5: Retry logic")
    print("=" * 60)

    runner = BenchmarkRunner()

    def with_retries():
        adapter = FrappeProxyAdapter(max_retries=3, retry_backoff=0.1)
        return adapter.search_documents('Customer', limit=10)

    def without_retries():
        adapter = FrappeProxyAdapter(max_retries=0)
        return adapter.search_documents('Customer', limit=10)

    runner.benchmark("Avec retries (max=3)", with_retries, iterations=3)
    runner.benchmark("Sans retries", without_retries, iterations=3)

    runner.compare("Sans retries", "Avec retries (max=3)")

    return runner


def main():
    """Exécuter tous les benchmarks"""
    print("=" * 60)
    print("BENCHMARKS FRAPPE PROXY ADAPTER V2")
    print("=" * 60)

    # Vérifier credentials
    if not os.getenv('FRAPPE_API_KEY') or not os.getenv('FRAPPE_API_SECRET'):
        print("❌ Erreur: FRAPPE_API_KEY et FRAPPE_API_SECRET requis")
        print("   Configurez le fichier .env")
        return

    print("\n📋 Configuration:")
    print(f"   Frappe URL: {os.getenv('FRAPPE_URL', 'http://localhost:8000')}")
    print(f"   API Key: {os.getenv('FRAPPE_API_KEY', 'N/A')[:10]}...")

    # Menu
    print("\n🎯 Choisissez les benchmarks à exécuter:")
    print("   1) Recherche sans cache")
    print("   2) Recherche avec cache")
    print("   3) Pagination")
    print("   4) Opérations batch (ATTENTION: crée/supprime des docs)")
    print("   5) Retry logic")
    print("   6) TOUS les benchmarks")
    print("   q) Quitter")

    choice = input("\nChoix [1-6/q]: ").strip()

    runners = []

    if choice == '1' or choice == '6':
        runners.append(benchmark_search_without_cache())

    if choice == '2' or choice == '6':
        runners.append(benchmark_search_with_cache())

    if choice == '3' or choice == '6':
        runners.append(benchmark_pagination())

    if choice == '4' or choice == '6':
        runners.append(benchmark_batch_operations())

    if choice == '5' or choice == '6':
        runners.append(benchmark_retry_logic())

    if choice == 'q':
        print("Au revoir!")
        return

    # Rapport global
    if runners:
        print("\n" + "=" * 60)
        print("RAPPORT GLOBAL")
        print("=" * 60)

        all_results = {}
        for runner in runners:
            all_results.update(runner.results)

        sorted_results = sorted(all_results.items(), key=lambda x: x[1]['avg'])

        print("\n🏆 Classement par vitesse:")
        for i, (name, stats) in enumerate(sorted_results, 1):
            print(f"   {i}. {name}: {stats['avg']:.3f}s")

        # Recommandations
        print("\n💡 Recommandations:")

        cache_miss_avg = all_results.get('Recherche 10 clients (cache miss)', {}).get('avg')
        cache_hit_avg = all_results.get('Recherche 10 clients (cache hit)', {}).get('avg')

        if cache_miss_avg and cache_hit_avg:
            improvement = ((cache_miss_avg - cache_hit_avg) / cache_miss_avg) * 100
            print(f"   ✅ Le cache améliore les performances de {improvement:.0f}%")
            print("      → Activez le cache pour les workflows avec lectures répétées")

        print("\n✅ Benchmarks terminés!")


if __name__ == '__main__':
    main()
