#!/usr/bin/env python3
"""
Performance testing for API endpoints
"""
import requests
import time
import statistics

base_url = "http://127.0.0.1:8000"  # Use IP address instead of localhost for better performance

# Authenticate first
owner_login = {
    "email": "owner1755850537@rbactest.com",
    "password": "TestOwner123!"
}

print("🚀 API PERFORMANCE TESTING")
print("=" * 50)

try:
    # Login to get token
    response = requests.post(f"{base_url}/api/v1/auth/login", json=owner_login, timeout=10)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        exit(1)
    
    data = response.json()
    headers = {"Authorization": f"Bearer {data.get('tokens', {}).get('access_token')}"}
    print(f"✅ Authenticated successfully")
    
    # Test endpoints
    endpoints = [
        "/api/v1/auth/me",
        "/api/v1/organizations", 
        "/api/v1/projects",
        "/api/v1/boards",
        "/api/v1/cards"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        print(f"\n📊 Testing {endpoint}")
        times = []
        
        # Run 5 tests for each endpoint
        for i in range(5):
            start_time = time.time()
            try:
                response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                times.append(response_time)
                print(f"   Test {i+1}: {response_time:.1f}ms (Status: {response.status_code})")
            except Exception as e:
                print(f"   Test {i+1}: ❌ Error: {e}")
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            results[endpoint] = {
                "average": avg_time,
                "min": min_time,
                "max": max_time,
                "times": times
            }
            
            status = "✅" if avg_time < 500 else "⚠️" if avg_time < 1000 else "❌"
            print(f"   {status} Average: {avg_time:.1f}ms (Min: {min_time:.1f}ms, Max: {max_time:.1f}ms)")
    
    # Summary
    print(f"\n📋 PERFORMANCE SUMMARY")
    print("=" * 50)
    
    total_avg = 0
    count = 0
    
    for endpoint, data in results.items():
        avg = data["average"]
        total_avg += avg
        count += 1
        
        status = "✅ GOOD" if avg < 500 else "⚠️ SLOW" if avg < 1000 else "❌ VERY SLOW"
        print(f"{status} {endpoint}: {avg:.1f}ms")
    
    if count > 0:
        overall_avg = total_avg / count
        print(f"\n🎯 Overall Average: {overall_avg:.1f}ms")
        print(f"🎯 Target: <500ms")
        
        if overall_avg < 500:
            print("✅ Performance target achieved!")
        else:
            print(f"❌ Performance needs improvement ({overall_avg:.1f}ms > 500ms)")
            improvement_needed = overall_avg - 500
            print(f"📈 Need to reduce by {improvement_needed:.1f}ms ({improvement_needed/overall_avg*100:.1f}%)")

except Exception as e:
    print(f"❌ Performance test failed: {e}")
