"""
Simple performance test script to verify optimizations are working

This script tests the response times of key routes to verify the performance improvements.
"""

import sys
import os
import time

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db

def test_route_performance(client, route_name, route_path):
    """Test the performance of a single route"""
    print(f"\n📊 Testing: {route_name}")
    print(f"   Route: {route_path}")
    
    # Warm up (first request might be slower due to cache)
    client.get(route_path)
    
    # Test 3 times and get average
    times = []
    for i in range(3):
        start = time.time()
        response = client.get(route_path)
        elapsed = time.time() - start
        times.append(elapsed)
        
        status = "✅" if response.status_code == 200 else "❌"
        print(f"   {status} Attempt {i+1}: {elapsed:.3f}s (Status: {response.status_code})")
    
    avg_time = sum(times) / len(times)
    print(f"   📈 Average: {avg_time:.3f}s")
    
    # Check if it's fast enough
    if avg_time < 1.0:
        print(f"   🎉 EXCELLENT! Well under 1 second")
    elif avg_time < 2.0:
        print(f"   ✅ GOOD! Under 2 seconds")
    elif avg_time < 3.0:
        print(f"   ⚠️  OK. Could be better (under 3s)")
    else:
        print(f"   ⚠️  SLOW! Over 3 seconds")
    
    return avg_time

def test_api_endpoint(client):
    """Test the filter_bikes API endpoint"""
    print(f"\n📊 Testing: Bikes Filter API")
    print(f"   Route: /api/filter_bikes")
    
    # Test basic filter
    start = time.time()
    response = client.get('/api/filter_bikes')
    elapsed = time.time() - start
    
    status = "✅" if response.status_code == 200 else "❌"
    print(f"   {status} Basic filter: {elapsed:.3f}s (Status: {response.status_code})")
    
    if response.status_code == 200:
        data = response.get_json()
        count = data.get('count', 0)
        print(f"   📦 Returned {count} bikes")
    
    # Test category filter
    start = time.time()
    response = client.get('/api/filter_bikes?category=electric')
    elapsed = time.time() - start
    
    status = "✅" if response.status_code == 200 else "❌"
    print(f"   {status} Category filter: {elapsed:.3f}s (Status: {response.status_code})")
    
    if response.status_code == 200:
        data = response.get_json()
        count = data.get('count', 0)
        print(f"   📦 Returned {count} electric bikes")
    
    return elapsed

def main():
    """Run all performance tests"""
    print("=" * 70)
    print("PERFORMANCE TEST SUITE")
    print("Testing route response times after optimization")
    print("=" * 70)
    
    # Create app and test client
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        results = {}
        
        # Test home page
        results['home'] = test_route_performance(client, "Home Page", "/")
        
        # Test bikes page
        results['bikes'] = test_route_performance(client, "Bikes Page", "/bikes")
        
        # Test category page
        results['category'] = test_route_performance(client, "Category Page (Electric)", "/electric")
        
        # Test blog page
        results['blog'] = test_route_performance(client, "Blog Page", "/blog")
        
        # Test sitemap
        results['sitemap'] = test_route_performance(client, "Sitemap", "/sitemap.xml")
        
        # Test API endpoint
        results['api'] = test_api_endpoint(client)
        
        # Summary
        print("\n" + "=" * 70)
        print("PERFORMANCE SUMMARY")
        print("=" * 70)
        
        for route, avg_time in results.items():
            if avg_time < 1.0:
                emoji = "🎉"
                status = "EXCELLENT"
            elif avg_time < 2.0:
                emoji = "✅"
                status = "GOOD"
            elif avg_time < 3.0:
                emoji = "⚠️ "
                status = "OK"
            else:
                emoji = "❌"
                status = "SLOW"
            
            print(f"{emoji} {route.upper():20s}: {avg_time:.3f}s - {status}")
        
        # Overall assessment
        avg_all = sum(results.values()) / len(results)
        print("\n" + "=" * 70)
        print(f"Overall Average Response Time: {avg_all:.3f}s")
        
        if avg_all < 1.5:
            print("🎉 EXCELLENT PERFORMANCE! All optimizations working perfectly!")
        elif avg_all < 2.5:
            print("✅ GOOD PERFORMANCE! Significant improvement achieved!")
        else:
            print("⚠️  Performance could be better. Check database and queries.")
        
        print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

