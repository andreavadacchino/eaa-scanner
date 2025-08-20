#!/usr/bin/env python3
"""
EAA Scanner Frontend Test Suite
Tests the modern frontend functionality
"""

import json
import time
import unittest
import urllib.request
import urllib.parse
from pathlib import Path


class FrontendTestSuite:
    """Test suite for EAA Scanner frontend"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
    
    def run_all_tests(self):
        """Run all frontend tests"""
        print("🚀 Starting EAA Scanner Frontend Test Suite\n")
        
        tests = [
            ("Homepage Loading", self.test_homepage),
            ("Static Assets", self.test_static_assets),
            ("History Page", self.test_history_page),
            ("API Endpoints", self.test_api_endpoints),
            ("Form Validation", self.test_form_validation),
            ("Responsive Design", self.test_responsive_design),
            ("Accessibility", self.test_accessibility),
        ]
        
        for test_name, test_func in tests:
            print(f"🧪 Testing: {test_name}")
            try:
                result = test_func()
                self.test_results.append({
                    "name": test_name,
                    "status": "PASS" if result else "FAIL",
                    "details": result if isinstance(result, str) else "OK"
                })
                print(f"   ✅ PASS: {test_name}")
            except Exception as e:
                self.test_results.append({
                    "name": test_name,
                    "status": "ERROR",
                    "details": str(e)
                })
                print(f"   ❌ ERROR: {test_name} - {e}")
            print()
        
        self.print_summary()
    
    def test_homepage(self):
        """Test homepage loads correctly"""
        response = self.make_request("/")
        
        if response.status != 200:
            raise Exception(f"Homepage returned status {response.status}")
        
        content = response.read().decode('utf-8')
        
        # Check for key elements
        checks = [
            "EAA Scanner" in content,
            'id="scan-form"' in content,
            'id="start-btn"' in content,
            'id="progress-container"' in content,
            "/static/css/main.css" in content,
            "/static/js/scanner.js" in content,
        ]
        
        if not all(checks):
            raise Exception("Missing key elements in homepage")
        
        return True
    
    def test_static_assets(self):
        """Test static assets load correctly"""
        assets = [
            "/static/css/main.css",
            "/static/js/scanner.js",
            "/static/js/history.js",
            "/static/js/sw.js",
        ]
        
        for asset in assets:
            response = self.make_request(asset)
            if response.status != 200:
                raise Exception(f"Asset {asset} returned status {response.status}")
        
        # Check CSS contains key styles
        css_response = self.make_request("/static/css/main.css")
        css_content = css_response.read().decode('utf-8')
        
        css_checks = [
            ":root" in css_content,
            "--primary" in css_content,
            ".btn" in css_content,
            ".card" in css_content,
            "@media" in css_content,  # Responsive design
        ]
        
        if not all(css_checks):
            raise Exception("CSS missing key styles")
        
        # Check JS contains key functions
        js_response = self.make_request("/static/js/scanner.js")
        js_content = js_response.read().decode('utf-8')
        
        js_checks = [
            "class EAAScanner" in js_content,
            "startScan" in js_content,
            "pollStatus" in js_content,
            "validateForm" in js_content,
        ]
        
        if not all(js_checks):
            raise Exception("JavaScript missing key functions")
        
        return True
    
    def test_history_page(self):
        """Test history page loads correctly"""
        response = self.make_request("/history")
        
        if response.status != 200:
            raise Exception(f"History page returned status {response.status}")
        
        content = response.read().decode('utf-8')
        
        # Check for key elements
        checks = [
            "Storico Scansioni" in content,
            'id="search"' in content,
            'id="scans-tbody"' in content,
            "/static/js/history.js" in content,
        ]
        
        if not all(checks):
            raise Exception("Missing key elements in history page")
        
        return True
    
    def test_api_endpoints(self):
        """Test API endpoints respond correctly"""
        
        # Test health endpoint
        response = self.make_request("/health")
        if response.status != 200:
            raise Exception(f"Health endpoint returned status {response.status}")
        
        health_data = json.loads(response.read().decode('utf-8'))
        if not health_data.get('ok'):
            raise Exception("Health endpoint returned non-OK status")
        
        # Test history API
        response = self.make_request("/api/history")
        if response.status != 200:
            raise Exception(f"History API returned status {response.status}")
        
        history_data = json.loads(response.read().decode('utf-8'))
        if 'scans' not in history_data:
            raise Exception("History API missing scans data")
        
        return True
    
    def test_form_validation(self):
        """Test form validation logic in frontend"""
        # This would typically be done with browser automation
        # For now, we'll test that the validation JavaScript is present
        
        js_response = self.make_request("/static/js/scanner.js")
        js_content = js_response.read().decode('utf-8')
        
        validation_checks = [
            "validateForm" in js_content,
            "isValidUrl" in js_content,
            "isValidEmail" in js_content,
            "showNotification" in js_content,
        ]
        
        if not all(validation_checks):
            raise Exception("Form validation functions missing")
        
        return True
    
    def test_responsive_design(self):
        """Test responsive design elements"""
        css_response = self.make_request("/static/css/main.css")
        css_content = css_response.read().decode('utf-8')
        
        responsive_checks = [
            "@media (max-width: 768px)" in css_content,
            "grid-template-columns" in css_content,
            "flex-direction: column" in css_content,
            "min-width" in css_content,
        ]
        
        if not all(responsive_checks):
            raise Exception("Responsive design styles missing")
        
        return True
    
    def test_accessibility(self):
        """Test accessibility features"""
        homepage_response = self.make_request("/")
        content = homepage_response.read().decode('utf-8')
        
        accessibility_checks = [
            'aria-label=' in content,
            'aria-describedby=' in content,
            'role=' in content,
            'lang="it"' in content,
            '<label for=' in content,
        ]
        
        if not all(accessibility_checks):
            raise Exception("Accessibility attributes missing")
        
        return True
    
    def make_request(self, path):
        """Make HTTP request to the application"""
        url = self.base_url + path
        try:
            return urllib.request.urlopen(url, timeout=10)
        except urllib.error.HTTPError as e:
            return e
        except Exception as e:
            raise Exception(f"Request failed: {e}")
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("🏁 TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed = sum(1 for result in self.test_results if result["status"] == "FAIL")
        errors = sum(1 for result in self.test_results if result["status"] == "ERROR")
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"🚨 Errors: {errors}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0 or errors > 0:
            print("\n🚨 FAILED/ERROR TESTS:")
            for result in self.test_results:
                if result["status"] in ["FAIL", "ERROR"]:
                    print(f"   {result['status']}: {result['name']} - {result['details']}")
        
        print("\n" + "="*60)


def run_performance_test():
    """Run basic performance tests"""
    print("⚡ Running Performance Tests\n")
    
    base_url = "http://localhost:8000"
    
    # Test page load times
    pages = ["/", "/history", "/static/css/main.css", "/static/js/scanner.js"]
    
    for page in pages:
        start_time = time.time()
        try:
            response = urllib.request.urlopen(base_url + page, timeout=10)
            load_time = (time.time() - start_time) * 1000  # Convert to ms
            size = len(response.read())
            
            print(f"📄 {page}")
            print(f"   Load Time: {load_time:.2f}ms")
            print(f"   Size: {size:,} bytes")
            
            if load_time > 1000:  # > 1 second
                print(f"   ⚠️  Slow load time")
            else:
                print(f"   ✅ Good load time")
                
        except Exception as e:
            print(f"📄 {page}")
            print(f"   ❌ Error: {e}")
        
        print()


def main():
    """Main test runner"""
    print("🧪 EAA Scanner Frontend Test Suite")
    print("===================================\n")
    
    # Check if server is running
    try:
        response = urllib.request.urlopen("http://localhost:8000/health", timeout=5)
        if response.status != 200:
            print("❌ Server not responding properly")
            return
    except Exception:
        print("❌ Server not running on localhost:8000")
        print("   Please start the server with: python webapp/app.py")
        return
    
    print("✅ Server is running\n")
    
    # Run functional tests
    test_suite = FrontendTestSuite()
    test_suite.run_all_tests()
    
    # Run performance tests
    run_performance_test()
    
    print("🎉 Test suite completed!")


if __name__ == "__main__":
    main()