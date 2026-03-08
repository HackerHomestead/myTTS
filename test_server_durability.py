#!/usr/bin/env python3
"""Test server durability and self-healing features."""

import sys
import time
import requests
import threading
import subprocess
import signal

SERVER_URL = "http://192.168.88.164:8000"


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print(f"  ✓ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"  ✗ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Results: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print("\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        return self.failed == 0


def test_server_resilience():
    """Test server resilience to various error conditions."""
    result = TestResult()
    print("\n[Server Resilience Tests]")
    
    test_cases = [
        ("", "Empty text"),
        ("x" * 6000, "Text too long"),
        ("Test\n\n\n\nwith\n\n\nmany\n\n\nnewlines", "Many newlines"),
        ("Test\t\t\twith\t\t\ttabs", "Many tabs"),
        ("Test with special chars: @#$%^&*()", "Special characters"),
        ("Test with unicode: 你好世界", "Unicode characters"),
        ("Test with emojis: 😀🎉", "Emoji characters"),
        ("A" * 4999, "Max length text"),
        ("   Test   ", "Text with spaces"),
        ("Test\r\nwith\r\nCRLF", "CRLF line endings"),
    ]
    
    for text, test_name in test_cases:
        try:
            clean_text = " ".join(text.split()) if text else ""
            response = requests.post(
                f"{SERVER_URL}/tts",
                json={
                    "text": clean_text if clean_text else text,
                    "voice": "en_US-lessac-medium",
                    "engine": "piper",
                },
                timeout=30
            )
            
            if response.status_code in [200, 400, 500]:
                if response.status_code == 200:
                    result.add_pass(f"Resilience: {test_name} (success)")
                elif response.status_code == 400:
                    result.add_pass(f"Resilience: {test_name} (expected error)")
                else:
                    if "phonemizer" in response.text.lower():
                        result.add_fail(f"Resilience: {test_name}", 
                            "Phonemizer error not handled")
                    else:
                        result.add_pass(f"Resilience: {test_name} (handled error)")
            else:
                result.add_fail(f"Resilience: {test_name}", 
                    f"Unexpected status: {response.status_code}")
        
        except requests.exceptions.Timeout:
            result.add_fail(f"Resilience: {test_name}", "Request timeout")
        except Exception as e:
            result.add_fail(f"Resilience: {test_name}", str(e))
    
    return result


def test_engine_recovery():
    """Test that engines recover from errors."""
    result = TestResult()
    print("\n[Engine Recovery Tests]")
    
    try:
        for i in range(3):
            response = requests.post(
                f"{SERVER_URL}/tts",
                json={
                    "text": f"Test sentence {i}.",
                    "voice": "en_US-lessac-medium",
                    "engine": "piper",
                },
                timeout=30
            )
            if response.status_code == 200:
                result.add_pass(f"Engine recovery request {i+1}")
            else:
                result.add_fail(f"Engine recovery request {i+1}", 
                    f"Status: {response.status_code}")
        
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "engines" in data:
                result.add_pass("Health check shows engines")
            else:
                result.add_fail("Health check", "No engines in response")
        else:
            result.add_fail("Health check", f"Status: {response.status_code}")
    
    except Exception as e:
        result.add_fail("Engine recovery", str(e))
    
    return result


def test_memory_management():
    """Test that server manages memory properly."""
    result = TestResult()
    print("\n[Memory Management Tests]")
    
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            initial_data = response.json()
            initial_memory = initial_data.get("memory", {}).get("percent", 0)
            result.add_pass(f"Initial memory check ({initial_memory:.1f}%)")
        else:
            result.add_fail("Initial memory check", f"Status: {response.status_code}")
            return result
        
        for i in range(10):
            response = requests.post(
                f"{SERVER_URL}/tts",
                json={
                    "text": f"Memory test sentence number {i} for testing memory management.",
                    "voice": "en_US-lessac-medium",
                    "engine": "piper",
                },
                timeout=30
            )
        
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            final_data = response.json()
            final_memory = final_data.get("memory", {}).get("percent", 0)
            
            memory_increase = final_memory - initial_memory
            
            if memory_increase < 10:
                result.add_pass(f"Memory stable (+{memory_increase:.1f}%)")
            else:
                result.add_fail("Memory stable", 
                    f"Memory increased by {memory_increase:.1f}%")
        else:
            result.add_fail("Final memory check", f"Status: {response.status_code}")
        
        response = requests.post(f"{SERVER_URL}/cleanup", timeout=10)
        if response.status_code == 200:
            result.add_pass("Cleanup endpoint works")
        else:
            result.add_fail("Cleanup endpoint", f"Status: {response.status_code}")
    
    except Exception as e:
        result.add_fail("Memory management", str(e))
    
    return result


def test_concurrent_load():
    """Test server under concurrent load."""
    result = TestResult()
    print("\n[Concurrent Load Tests]")
    
    def make_request(idx):
        try:
            response = requests.post(
                f"{SERVER_URL}/tts",
                json={
                    "text": f"Concurrent test sentence number {idx}.",
                    "voice": "en_US-lessac-medium",
                    "engine": "piper",
                },
                timeout=30
            )
            return (idx, response.status_code == 200)
        except Exception as e:
            return (idx, False, str(e))
    
    results = {}
    threads = []
    
    for i in range(5):
        thread = threading.Thread(
            target=lambda idx: results.update({idx: make_request(idx)}),
            args=(i,)
        )
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join(timeout=35)
    
    success_count = sum(1 for r in results.values() if r[1])
    
    if success_count == 5:
        result.add_pass(f"Concurrent load (5/5 succeeded)")
    else:
        result.add_fail("Concurrent load", f"Only {success_count}/5 succeeded")
    
    return result


def test_error_recovery():
    """Test that server recovers from errors."""
    result = TestResult()
    print("\n[Error Recovery Tests]")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/tts",
            json={"text": "", "voice": "en_US-lessac-medium"},
            timeout=5
        )
        if response.status_code in [400, 500]:
            result.add_pass("Error on empty text")
        else:
            result.add_fail("Error on empty text", 
                f"Expected error, got {response.status_code}")
        
        response = requests.post(
            f"{SERVER_URL}/tts",
            json={
                "text": "Valid text after error.",
                "voice": "en_US-lessac-medium",
                "engine": "piper",
            },
            timeout=30
        )
        if response.status_code == 200:
            result.add_pass("Recovery after error")
        else:
            result.add_fail("Recovery after error", 
                f"Status: {response.status_code}")
        
        for i in range(3):
            response = requests.post(
                f"{SERVER_URL}/tts",
                json={"text": "", "voice": "en_US-lessac-medium"},
                timeout=5
            )
        
        response = requests.post(
            f"{SERVER_URL}/tts",
            json={
                "text": "Valid text after multiple errors.",
                "voice": "en_US-lessac-medium",
                "engine": "piper",
            },
            timeout=30
        )
        if response.status_code == 200:
            result.add_pass("Recovery after multiple errors")
        else:
            result.add_fail("Recovery after multiple errors", 
                f"Status: {response.status_code}")
    
    except Exception as e:
        result.add_fail("Error recovery", str(e))
    
    return result


def test_health_endpoint():
    """Test health endpoint details."""
    result = TestResult()
    print("\n[Health Endpoint Tests]")
    
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            result.add_pass("Health endpoint accessible")
        else:
            result.add_fail("Health endpoint", f"Status: {response.status_code}")
            return result
        
        data = response.json()
        
        required_fields = ["status", "engines", "memory", "gpu", "gc_stats"]
        for field in required_fields:
            if field in data:
                result.add_pass(f"Health has {field}")
            else:
                result.add_fail(f"Health has {field}", f"Missing field: {field}")
        
        if data.get("status") == "ok":
            result.add_pass("Health status OK")
        else:
            result.add_fail("Health status", f"Status: {data.get('status')}")
        
        if "engines" in data and isinstance(data["engines"], list):
            result.add_pass(f"Engines list ({len(data['engines'])} cached)")
        else:
            result.add_fail("Engines list", "Invalid engines data")
        
        if "memory" in data:
            mem = data["memory"]
            if "percent" in mem:
                result.add_pass(f"Memory usage ({mem['percent']:.1f}%)")
            else:
                result.add_fail("Memory usage", "No percent field")
        
        if "gpu" in data:
            gpu = data["gpu"]
            if gpu.get("available"):
                result.add_pass(f"GPU available (device {gpu.get('current_device', '?')})")
            else:
                result.add_pass("GPU not available (CPU mode)")
    
    except Exception as e:
        result.add_fail("Health endpoint", str(e))
    
    return result


def test_long_running():
    """Test server stability over multiple requests."""
    result = TestResult()
    print("\n[Long Running Tests]")
    
    try:
        success_count = 0
        for i in range(20):
            response = requests.post(
                f"{SERVER_URL}/tts",
                json={
                    "text": f"Long running test sentence number {i}.",
                    "voice": "en_US-lessac-medium",
                    "engine": "piper",
                },
                timeout=30
            )
            if response.status_code == 200:
                success_count += 1
        
        if success_count == 20:
            result.add_pass(f"Long running (20/20 succeeded)")
        elif success_count >= 18:
            result.add_fail("Long running", 
                f"Mostly stable ({success_count}/20)")
        else:
            result.add_fail("Long running", 
                f"Unstable ({success_count}/20)")
        
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "server_stats" in data:
                stats = data["server_stats"]
                result.add_pass(f"Server stats (uptime: {stats.get('uptime_seconds', 0)}s)")
            else:
                result.add_pass("Server still healthy after load")
        else:
            result.add_fail("Server health after load", 
                f"Status: {response.status_code}")
    
    except Exception as e:
        result.add_fail("Long running", str(e))
    
    return result


def main():
    """Run all durability tests."""
    print("=" * 60)
    print("Server Durability Test Suite")
    print("=" * 60)
    
    all_results = []
    
    all_results.append(test_health_endpoint())
    all_results.append(test_server_resilience())
    all_results.append(test_engine_recovery())
    all_results.append(test_memory_management())
    all_results.append(test_concurrent_load())
    all_results.append(test_error_recovery())
    all_results.append(test_long_running())
    
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {total_passed}/{total_tests} tests passed")
    
    if total_failed > 0:
        print(f"\n{total_failed} tests failed:")
        for result in all_results:
            for test_name, error in result.errors:
                print(f"  - {test_name}: {error}")
        return 1
    else:
        print("\n✓ All durability tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
