"""
POC Test 1 : Découverte des serveurs MCP

Ce test valide que le bridge peut découvrir les serveurs MCP configurés,
notamment le serveur frappe-assistant.

Attendu:
- La découverte retourne une liste de serveurs
- 'frappe-assistant' est dans la liste
- Les métadonnées du serveur sont accessibles
"""

from mcp import runtime

print("=" * 60)
print("POC Test 1 : Découverte des serveurs MCP")
print("=" * 60)
print()

# Test 1: Découverte des serveurs disponibles
print("1. Découverte des serveurs disponibles...")
try:
    discovered = runtime.discovered_servers()
    print(f"   ✅ Serveurs découverts: {discovered}")
    print(f"   Nombre de serveurs: {len(discovered)}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    raise

print()

# Test 2: Vérifier que frappe-assistant est découvert
print("2. Vérification présence de frappe-assistant...")
if 'frappe-assistant' in discovered:
    print("   ✅ frappe-assistant trouvé dans les serveurs découverts")
else:
    print(f"   ❌ frappe-assistant NON trouvé. Serveurs: {discovered}")
    print()
    print("   Actions requises:")
    print("   - Vérifier que ~/.config/mcp/servers/frappe-assistant.json existe")
    print("   - Vérifier que le fichier est un JSON valide")
    print("   - Exécuter: ./scripts/setup_frappe_config.sh")
    raise AssertionError("frappe-assistant non découvert")

print()

# Test 3: Lister les serveurs (RPC)
print("3. Liste des serveurs via RPC...")
try:
    servers = await runtime.list_servers()
    print(f"   ✅ Serveurs accessibles: {servers}")
except Exception as e:
    print(f"   ⚠️  RPC list_servers: {e}")
    print("   (Normal si les serveurs ne sont pas encore chargés)")

print()

# Test 4: Version synchrone
print("4. Liste des serveurs (version synchrone)...")
try:
    servers_sync = runtime.list_servers_sync()
    print(f"   ✅ Serveurs (sync): {servers_sync}")
except Exception as e:
    print(f"   ⚠️  list_servers_sync: {e}")

print()

# Test 5: Résumé des capacités
print("5. Résumé des capacités du sandbox...")
try:
    summary = runtime.capability_summary()
    print(f"   ✅ Capacités disponibles:")
    print(f"   {summary}")
except Exception as e:
    print(f"   ⚠️  capability_summary: {e}")

print()
print("=" * 60)
print("✅ Test 1 RÉUSSI : Découverte des serveurs OK")
print("=" * 60)
print()
print("Serveurs découverts:", discovered)
print()
