"""
Comprehensive API endpoint testing

Tests all endpoints for:
- Correct status codes
- Response format
- Error handling
- Performance
"""

import requests
import time
from typing import Dict, List, Optional
import json

BASE_URL = "http://127.0.0.1:8000"  # Use IP instead of 'localhost' to avoid Windows IPv6 DNS delay (~2 seconds)

class APITester:
    def __init__(self):
        self.results = []
        self.token = None
        self.user_id = None
    
    def test_endpoint(self, method: str, endpoint: str, expected_status: int = 200, 
                     data: Dict = None, auth: bool = False, timeout: int = 5) -> bool:
        """Test a single endpoint"""
        url = f"{BASE_URL}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            start = time.time()
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                print(f"✗ Unknown method: {method}")
                return False
            
            duration = (time.time() - start) * 1000
            
            success = response.status_code == expected_status
            status_icon = "✓" if success else "✗"
            perf_icon = "✓" if duration < 500 else "⚠" if duration < 1000 else "✗"
            
            # Try to parse JSON response
            try:
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            except:
                response_data = None
            
            result = {
                'endpoint': endpoint,
                'method': method,
                'status': response.status_code,
                'expected': expected_status,
                'success': success,
                'duration_ms': duration,
                'response': response_data
            }
            
            self.results.append(result)
            
            print(f"{status_icon} {perf_icon} {method:6} {endpoint:50} {response.status_code:3} ({duration:.0f}ms)")
            
            return success
            
        except requests.exceptions.Timeout:
            print(f"✗ ⏱  {method:6} {endpoint:50} TIMEOUT")
            self.results.append({
                'endpoint': endpoint,
                'method': method,
                'status': 0,
                'expected': expected_status,
                'success': False,
                'duration_ms': timeout * 1000,
                'response': None,
                'error': 'Timeout'
            })
            return False
        except requests.exceptions.ConnectionError:
            print(f"✗ 🔌 {method:6} {endpoint:50} CONNECTION ERROR")
            self.results.append({
                'endpoint': endpoint,
                'method': method,
                'status': 0,
                'expected': expected_status,
                'success': False,
                'duration_ms': 0,
                'response': None,
                'error': 'Connection Error'
            })
            return False
        except Exception as e:
            print(f"X [X] {method:6} {endpoint:50} ERROR: {str(e)[:50]}")
            self.results.append({
                'endpoint': endpoint,
                'method': method,
                'status': 0,
                'expected': expected_status,
                'success': False,
                'duration_ms': 0,
                'response': None,
                'error': str(e)
            })
            return False
    
    def run_all_tests(self):
        """Run all endpoint tests"""
        print("=" * 120)
        print("COMPREHENSIVE API TESTING - AgriProfit V1")
        print("=" * 120)
        print("Legend: ✓ = Success, ✗ = Failed | ✓ = Fast (<500ms), ⚠ = Slow (<1s), ✗ = Very slow")
        print("=" * 120)
        
        # Health check
        print("\n[Health & Status]")
        self.test_endpoint("GET", "/health", expected_status=200)
        self.test_endpoint("GET", "/sync/status", expected_status=200)
        
        # Authentication
        print("\n[Authentication]")
        self.test_endpoint("POST", "/auth/request-otp", data={"phone_number": "9876543210"}, expected_status=200)
        self.test_endpoint("POST", "/auth/request-otp", data={"phone": "invalid"}, expected_status=422)
        # Note: Cannot test verify-otp without actual OTP from logs
        
        # Commodities
        print("\n[Commodities]")
        self.test_endpoint("GET", "/commodities", expected_status=200)
        self.test_endpoint("GET", "/commodities?category=Grains", expected_status=200)
        self.test_endpoint("GET", "/commodities?search=wheat", expected_status=200)
        self.test_endpoint("GET", "/commodities?skip=0&limit=20", expected_status=200)
        self.test_endpoint("GET", "/commodities?is_active=true", expected_status=200)
        
        # Get a commodity ID for detail tests
        try:
            response = requests.get(f"{BASE_URL}/commodities?limit=1")
            if response.status_code == 200:
                commodities = response.json()
                if commodities:
                    commodity_id = commodities[0]['id']
                    self.test_endpoint("GET", f"/commodities/{commodity_id}", expected_status=200)
        except:
            pass
        
        # Mandis
        print("\n[Mandis]")
        self.test_endpoint("GET", "/mandis", expected_status=200)
        self.test_endpoint("GET", "/mandis?state=Punjab", expected_status=200)
        self.test_endpoint("GET", "/mandis?district=Ludhiana", expected_status=200)
        self.test_endpoint("GET", "/mandis?skip=0&limit=20", expected_status=200)
        
        # Get a mandi ID for detail tests
        try:
            response = requests.get(f"{BASE_URL}/mandis?limit=1")
            if response.status_code == 200:
                mandis = response.json()
                if mandis:
                    mandi_id = mandis[0]['id']
                    self.test_endpoint("GET", f"/mandis/{mandi_id}", expected_status=200)
                    self.test_endpoint("GET", f"/mandis/{mandi_id}/prices", expected_status=200)
        except:
            pass
        
        # Prices
        print("\n[Prices]")
        # Get commodity and mandi IDs for price history tests
        try:
            response = requests.get(f"{BASE_URL}/commodities?limit=1")
            if response.status_code == 200:
                commodities = response.json()
                if commodities:
                    commodity_id = commodities[0]['id']
                    # Test price listing with commodity filter
                    self.test_endpoint("GET", f"/prices/?commodity_id={commodity_id}&limit=50", expected_status=200)
                    self.test_endpoint("GET", f"/prices/?commodity_id={commodity_id}&limit=100", expected_status=200)
        except:
            pass
        
        # Test with mandi filter
        try:
            response = requests.get(f"{BASE_URL}/mandis?limit=1")
            if response.status_code == 200:
                mandis = response.json()
                if mandis:
                    mandi_id = mandis[0]['id']
                    self.test_endpoint("GET", f"/prices/?mandi_id={mandi_id}&limit=50", expected_status=200)
        except:
            pass
        
        self.test_endpoint("GET", "/prices/current", expected_status=200)
        
        # Transport
        print("\n[Transport]")
        self.test_endpoint("POST", "/api/v1/transport/calculate", data={
            "commodity": "Wheat",
            "quantity_kg": 1000,
            "distance_km": 50,
            "vehicle_type": "pickup"
        }, expected_status=200)
        
        self.test_endpoint("POST", "/api/v1/transport/calculate", data={
            "commodity": "Rice",
            "quantity_kg": 5000,
            "distance_km": 200,
            "vehicle_type": "truck_small"
        }, expected_status=200)
        
        # Invalid transport request
        self.test_endpoint("POST", "/api/v1/transport/calculate", data={
            "quantity_kg": -100
        }, expected_status=422)
        
        # Community (public endpoints - no auth required)
        print("\n[Community - Public Access]")
        self.test_endpoint("GET", "/community/posts", expected_status=200)
        self.test_endpoint("GET", "/community/posts?category=Crop Management", expected_status=200)
        self.test_endpoint("GET", "/community/posts?skip=0&limit=20", expected_status=200)
        
        # Forecasts
        print("\n[Forecasts]")
        try:
            response = requests.get(f"{BASE_URL}/commodities?limit=1")
            if response.status_code == 200:
                commodities = response.json()
                if commodities:
                    commodity_id = commodities[0]['id']
                    self.test_endpoint("GET", f"/forecasts/{commodity_id}", expected_status=200)
        except:
            pass
        
        # Analytics
        print("\n[Analytics]")
        # Get commodity_id for price-trends test
        try:
            response = requests.get(f"{BASE_URL}/commodities?limit=1")
            if response.status_code == 200:
                commodities = response.json()
                if commodities:
                    commodity_id = commodities[0]['id']
                    self.test_endpoint("GET", f"/analytics/price-trends?commodity_id={commodity_id}", expected_status=200)
        except:
            pass
        self.test_endpoint("GET", "/analytics/top-commodities", expected_status=200)
        
        # Admin endpoints (will fail without admin auth - expected)
        print("\n[Admin Endpoints - Unauthorized (Expected)]")
        self.test_endpoint("GET", "/admin/users", expected_status=401, auth=False)
        self.test_endpoint("GET", "/admin/stats", expected_status=401, auth=False)
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 120)
        print("TEST REPORT")
        print("=" * 120)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = total - passed
        
        if total > 0:
            avg_duration = sum(r['duration_ms'] for r in self.results) / total
            slow_requests = sum(1 for r in self.results if r['duration_ms'] > 500)
            very_slow = sum(1 for r in self.results if r['duration_ms'] > 1000)
            
            print(f"\n📊 COVERAGE")
            print(f"   Total Tests: {total}")
            print(f"   Passed: {passed} ({passed/total*100:.1f}%)")
            print(f"   Failed: {failed} ({failed/total*100:.1f}%)")
            
            print(f"\n[PERFORMANCE]")
            print(f"   Average Response Time: {avg_duration:.0f}ms")
            print(f"   Fast (<500ms): {total - slow_requests} ({(total - slow_requests)/total*100:.1f}%)")
            print(f"   Slow (500-1000ms): {slow_requests - very_slow} ({(slow_requests - very_slow)/total*100:.1f}%)")
            print(f"   Very Slow (>1000ms): {very_slow} ({very_slow/total*100:.1f}%)")
            
            if failed > 0:
                print(f"\n[FAILED TESTS]")
                for r in self.results:
                    if not r['success']:
                        error_info = r.get('error', f"got {r['status']}, expected {r['expected']}")
                        print(f"   • {r['method']} {r['endpoint']}")
                        print(f"     └─ {error_info}")
            
            # Performance warnings
            if very_slow > 0:
                print(f"\n[PERFORMANCE WARNINGS]")
                for r in self.results:
                    if r['duration_ms'] > 1000:
                        print(f"   • {r['method']} {r['endpoint']} - {r['duration_ms']:.0f}ms (VERY SLOW)")
            
            # Overall assessment
            print(f"\n{'[PASS]' if failed == 0 else '[FAIL]'} OVERALL")
            if failed == 0:
                print("   All tests passed! ✓")
                if very_slow == 0:
                    print("   Performance is excellent! ⚡")
                elif very_slow < 3:
                    print("   Performance is good, but a few endpoints are slow ⚠")
                else:
                    print("   Performance needs optimization ⚠")
            else:
                print(f"   {failed} test(s) failed - needs investigation ✗")
        
        print("\n" + "=" * 120)
        
        return passed, failed, total

def main():
    """Main test execution"""
    print("\n[*] Starting AgriProfit V1 API Testing...")
    print("[!] Make sure the backend server is running on http://127.0.0.1:8000\n")
    
    # Quick health check
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=2)  # Use 127.0.0.1 to avoid IPv6 DNS delay
        if response.status_code != 200:
            print("[ERROR] Backend server is not responding correctly!")
            print("   Start the server: cd backend && uvicorn app.main:app --reload")
            return
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to backend server!")
        print("   Start the server: cd backend && uvicorn app.main:app --reload")
        return
    except Exception as e:
        print(f"[ERROR] Error connecting to backend: {e}")
        return
    
    print("[OK] Backend server is running\n")
    
    tester = APITester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
