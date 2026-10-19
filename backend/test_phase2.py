"""
Phase 2 Integration Test Script
Tests Redis caching, connection pooling, and WebSocket functionality.
"""
import time
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# Get JWT token first
def get_auth_token():
    """Login and get JWT token."""
    response = requests.post(f"{API_V1}/auth/login", json={
        "username": "admin",
        "password": "admin"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code}")
        return None

def test_redis_caching(token):
    """Test Redis cache hit/miss performance."""
    print("\n" + "="*60)
    print("TEST 1: Redis Caching Performance")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    endpoint = f"{API_V1}/monitoring/database"
    
    # First request - should be cache MISS
    print("\n📊 Request 1 (Cache MISS expected)...")
    start = time.time()
    resp1 = requests.get(endpoint, headers=headers)
    time1 = (time.time() - start) * 1000
    
    if resp1.status_code == 200:
        print(f"✅ Response time: {time1:.1f}ms")
        print(f"   Connection status: {resp1.json().get('connection_status')}")
    else:
        print(f"❌ Request failed: {resp1.status_code}")
        return False
    
    # Second request - should be cache HIT
    print("\n📊 Request 2 (Cache HIT expected)...")
    time.sleep(0.5)  # Small delay
    start = time.time()
    resp2 = requests.get(endpoint, headers=headers)
    time2 = (time.time() - start) * 1000
    
    if resp2.status_code == 200:
        print(f"✅ Response time: {time2:.1f}ms")
        speedup = time1 / time2
        print(f"   🚀 Speedup: {speedup:.1f}x faster!")
        
        if time2 < 50:  # Sub-50ms indicates cache hit
            print("   ✅ Redis cache is working!")
            return True
        else:
            print("   ⚠️  Still slow, Redis might not be working")
            return False
    else:
        print(f"❌ Request failed: {resp2.status_code}")
        return False

def test_cache_stats(token):
    """Test Redis cache statistics endpoint."""
    print("\n" + "="*60)
    print("TEST 2: Redis Cache Statistics")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_V1}/monitoring/cache-stats", headers=headers)
    
    if response.status_code == 200:
        stats = response.json()
        print(f"\n✅ Cache Status: {stats.get('status')}")
        print(f"   Total Keys: {stats.get('total_keys', 0)}")
        print(f"   Hit Rate: {stats.get('hit_rate_percent', 0):.2f}%")
        print(f"   Memory Used: {stats.get('memory_used_mb', 0):.2f} MB")
        print(f"   Keyspace Hits: {stats.get('keyspace_hits', 0)}")
        print(f"   Keyspace Misses: {stats.get('keyspace_misses', 0)}")
        return stats.get('status') == 'connected'
    else:
        print(f"❌ Cache stats failed: {response.status_code}")
        print(f"   {response.text}")
        return False

def test_connection_pooling(token):
    """Test database connection pool statistics."""
    print("\n" + "="*60)
    print("TEST 3: Database Connection Pooling")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_V1}/monitoring/pool-stats", headers=headers)
    
    if response.status_code == 200:
        stats = response.json()
        print(f"\n✅ Pool Status: {stats.get('status')}")
        
        target = stats.get('target_database', {})
        print(f"\n   Target Database Pool:")
        print(f"   - Pool Size: {target.get('pool_size')}")
        print(f"   - Checked Out: {target.get('checked_out')}")
        print(f"   - Checked In: {target.get('checked_in')}")
        print(f"   - Overflow: {target.get('overflow')}")
        
        app = stats.get('app_database', {})
        print(f"\n   App Database Pool:")
        print(f"   - Pool Size: {app.get('pool_size')}")
        print(f"   - Checked Out: {app.get('checked_out')}")
        print(f"   - Checked In: {app.get('checked_in')}")
        print(f"   - Overflow: {app.get('overflow')}")
        
        return stats.get('status') == 'healthy'
    else:
        print(f"❌ Pool stats failed: {response.status_code}")
        return False

def test_websocket_stats(token):
    """Test WebSocket server statistics."""
    print("\n" + "="*60)
    print("TEST 4: WebSocket Server")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_V1}/monitoring/websocket-stats", headers=headers)
    
    if response.status_code == 200:
        stats = response.json()
        print(f"\n✅ WebSocket Status: {stats.get('status')}")
        print(f"   Total Connections: {stats.get('total_connections', 0)}")
        print(f"   Subscriptions: {stats.get('subscriptions', {})}")
        print(f"   Message: {stats.get('message')}")
        return True
    else:
        print(f"❌ WebSocket stats failed: {response.status_code}")
        print(f"   {response.text}")
        return False

def test_all_monitoring_endpoints(token):
    """Test all monitoring endpoints work with Redis caching."""
    print("\n" + "="*60)
    print("TEST 5: All Monitoring Endpoints with Redis")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = [
        "/monitoring/database",
        "/monitoring/server",
        "/monitoring/security",
        "/monitoring/notifications"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        print(f"\n📊 Testing {endpoint}...")
        url = f"{API_V1}{endpoint}"
        
        # First request
        start = time.time()
        resp1 = requests.get(url, headers=headers)
        time1 = (time.time() - start) * 1000
        
        # Second request (cache hit)
        start = time.time()
        resp2 = requests.get(url, headers=headers)
        time2 = (time.time() - start) * 1000
        
        if resp1.status_code == 200 and resp2.status_code == 200:
            speedup = time1 / time2 if time2 > 0 else 1
            print(f"   ✅ First: {time1:.1f}ms, Second: {time2:.1f}ms (speedup: {speedup:.1f}x)")
            results[endpoint] = True
        else:
            print(f"   ❌ Failed: {resp1.status_code}")
            results[endpoint] = False
    
    all_passed = all(results.values())
    return all_passed

def stress_test_pool(token):
    """Send concurrent requests to test connection pooling."""
    print("\n" + "="*60)
    print("TEST 6: Connection Pool Stress Test")
    print("="*60)
    
    import concurrent.futures
    
    headers = {"Authorization": f"Bearer {token}"}
    endpoint = f"{API_V1}/monitoring/database"
    
    print("\n🔥 Sending 30 concurrent requests...")
    
    def make_request(i):
        try:
            start = time.time()
            resp = requests.get(endpoint, headers=headers, timeout=10)
            elapsed = (time.time() - start) * 1000
            return (i, resp.status_code, elapsed)
        except Exception as e:
            return (i, 0, 0)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(make_request, i) for i in range(30)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    success = sum(1 for r in results if r[1] == 200)
    avg_time = sum(r[2] for r in results if r[1] == 200) / success if success > 0 else 0
    
    print(f"\n   ✅ Successful: {success}/30")
    print(f"   ⏱️  Average time: {avg_time:.1f}ms")
    
    # Check pool stats after stress test
    time.sleep(1)
    pool_resp = requests.get(f"{API_V1}/monitoring/pool-stats", headers=headers)
    if pool_resp.status_code == 200:
        pool_stats = pool_resp.json()
        target = pool_stats.get('target_database', {})
        print(f"\n   📊 Pool after stress test:")
        print(f"      Checked out: {target.get('checked_out')}")
        print(f"      Overflow used: {target.get('overflow')}")
        
        if 'warning' in target:
            print(f"      ⚠️  {target['warning']}")
    
    return success >= 28  # Allow 2 failures

def main():
    """Run all Phase 2 tests."""
    print("\n" + "="*60)
    print("🚀 PHASE 2 INTEGRATION TEST SUITE")
    print("="*60)
    print(f"Testing backend at: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get auth token
    print("\n🔐 Authenticating...")
    token = get_auth_token()
    if not token:
        print("\n❌ FAILED: Could not authenticate")
        return
    print("✅ Authentication successful")
    
    # Run all tests
    results = {
        "Redis Caching": test_redis_caching(token),
        "Cache Stats": test_cache_stats(token),
        "Connection Pooling": test_connection_pooling(token),
        "WebSocket Server": test_websocket_stats(token),
        "All Endpoints": test_all_monitoring_endpoints(token),
        "Stress Test": stress_test_pool(token),
    }
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print("\n" + "="*60)
    print(f"🎯 FINAL SCORE: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Phase 2 is working perfectly!")
    elif passed >= total * 0.8:
        print(f"\n⚠️  MOSTLY WORKING: {total - passed} test(s) failed")
    else:
        print(f"\n❌ ISSUES DETECTED: {total - passed} test(s) failed")
    
    print("\n💡 Next steps:")
    if results["Redis Caching"] and results["Cache Stats"]:
        print("   ✅ Redis is operational")
    else:
        print("   ⚠️  Check Redis: docker compose ps redis")
    
    if results["Connection Pooling"]:
        print("   ✅ Connection pooling is working")
    else:
        print("   ⚠️  Check database connection settings")
    
    if results["WebSocket Server"]:
        print("   ✅ WebSocket server is ready")
    else:
        print("   ℹ️  WebSocket requires Socket.IO client to test fully")

if __name__ == "__main__":
    main()
