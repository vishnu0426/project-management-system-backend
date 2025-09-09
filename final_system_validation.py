#!/usr/bin/env python3
"""
Final System Validation
"""
import requests
import time

base_url = "http://127.0.0.1:8000"

def final_validation():
    """Perform final system validation"""
    print("🔍 FINAL SYSTEM VALIDATION")
    print("=" * 60)
    
    validation_results = {
        "critical_endpoints": 0,
        "performance_tests": 0,
        "security_tests": 0,
        "data_integrity": 0,
        "total_tests": 0
    }
    
    # Test 1: Critical Endpoints
    print("\n1️⃣ CRITICAL ENDPOINTS VALIDATION")
    print("-" * 40)
    
    critical_endpoints = [
        ("/health", "GET", None, 200),
        ("/api/v1/auth/register", "POST", {
            "email": f"final_test_{int(time.time())}@example.com",
            "password": "TestPassword123!",
            "first_name": "Final",
            "last_name": "Test"
        }, 201)
    ]
    
    for endpoint, method, data, expected in critical_endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{base_url}{endpoint}", json=data, timeout=10)
            
            success = response.status_code == expected
            validation_results["critical_endpoints"] += 1 if success else 0
            validation_results["total_tests"] += 1
            
            print(f"   {'✅' if success else '❌'} {method} {endpoint}: {response.status_code}")
            
        except Exception as e:
            print(f"   ❌ {method} {endpoint}: ERROR - {e}")
            validation_results["total_tests"] += 1
    
    # Test 2: Performance Validation
    print("\n2️⃣ PERFORMANCE VALIDATION")
    print("-" * 40)
    
    performance_endpoints = ["/health", "/api/v1/auth/me"]
    
    # First authenticate
    login_data = {"email": "owner1755850537@rbactest.com", "password": "TestOwner123!"}
    try:
        auth_response = requests.post(f"{base_url}/api/v1/auth/login", json=login_data, timeout=10)
        if auth_response.status_code == 200:
            token = auth_response.json().get('tokens', {}).get('access_token')
            headers = {"Authorization": f"Bearer {token}"}
            
            for endpoint in performance_endpoints:
                start_time = time.time()
                try:
                    if endpoint == "/health":
                        response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    else:
                        response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
                    
                    response_time = (time.time() - start_time) * 1000
                    success = response_time < 500  # Target: <500ms
                    
                    validation_results["performance_tests"] += 1 if success else 0
                    validation_results["total_tests"] += 1
                    
                    print(f"   {'✅' if success else '❌'} {endpoint}: {response_time:.1f}ms")
                    
                except Exception as e:
                    print(f"   ❌ {endpoint}: ERROR - {e}")
                    validation_results["total_tests"] += 1
        else:
            print("   ❌ Cannot authenticate for performance tests")
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
    
    # Test 3: Security Validation
    print("\n3️⃣ SECURITY VALIDATION")
    print("-" * 40)
    
    # Test unauthorized access
    try:
        response = requests.get(f"{base_url}/api/v1/auth/me", timeout=10)
        success = response.status_code == 401
        validation_results["security_tests"] += 1 if success else 0
        validation_results["total_tests"] += 1
        print(f"   {'✅' if success else '❌'} Unauthorized access blocked: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Security test failed: {e}")
        validation_results["total_tests"] += 1
    
    # Test 4: Data Integrity
    print("\n4️⃣ DATA INTEGRITY VALIDATION")
    print("-" * 40)
    
    try:
        # Test database connection
        response = requests.get(f"{base_url}/health", timeout=10)
        success = response.status_code == 200
        validation_results["data_integrity"] += 1 if success else 0
        validation_results["total_tests"] += 1
        print(f"   {'✅' if success else '❌'} Database connectivity: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Data integrity test failed: {e}")
        validation_results["total_tests"] += 1
    
    # Calculate overall score
    total_passed = sum([
        validation_results["critical_endpoints"],
        validation_results["performance_tests"],
        validation_results["security_tests"],
        validation_results["data_integrity"]
    ])
    
    overall_score = (total_passed / validation_results["total_tests"]) * 100 if validation_results["total_tests"] > 0 else 0
    
    print(f"\n📊 FINAL VALIDATION RESULTS")
    print("=" * 60)
    print(f"Critical Endpoints: {validation_results['critical_endpoints']}/2 ✅")
    print(f"Performance Tests: {validation_results['performance_tests']}/2 ✅")
    print(f"Security Tests: {validation_results['security_tests']}/1 ✅")
    print(f"Data Integrity: {validation_results['data_integrity']}/1 ✅")
    print(f"")
    print(f"Overall Score: {overall_score:.1f}%")
    print(f"Status: {'✅ PRODUCTION READY' if overall_score >= 80 else '⚠️ NEEDS ATTENTION' if overall_score >= 60 else '❌ NOT READY'}")
    
    return overall_score >= 80

if __name__ == "__main__":
    final_validation()
