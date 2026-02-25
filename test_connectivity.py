#!/usr/bin/env python3
"""
Test script to verify Docker and AdGuard connectivity
"""

import requests
import time
import json
from typing import Dict, Any


def test_backend_health():
    """Test if the backend is responding."""
    print("🔍 Testing Backend Health...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is healthy!")
            print(f"   Services: {data.get('services', {})}")
            print(f"   Rate Limiting: {data.get('rate_limiting', {})}")
            return True
        else:
            print(f"❌ Backend returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend at http://localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Backend request timed out")
        return False
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        return False


def test_adguard_connectivity():
    """Test AdGuard connectivity from different URLs."""
    print("\n🔍 Testing AdGuard Connectivity...")

    adguard_urls = [
        "http://localhost:3000/control/status",
        "http://127.0.0.1:3000/control/status",
        "http://adguard:80/control/status",
    ]

    adguard_auth = ("8o8w4ggt3@mozmail.com", "123456789")

    for url in adguard_urls:
        try:
            print(f"   Testing {url}...")
            response = requests.get(url, auth=adguard_auth, timeout=5)
            if response.status_code == 200:
                print(f"✅ AdGuard accessible at {url}")
                return True
            else:
                print(f"   Status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"   Connection failed")
        except requests.exceptions.Timeout:
            print(f"   Timeout")
        except Exception as e:
            print(f"   Error: {e}")

    print("❌ AdGuard not accessible from any URL")
    return False


def test_docker_services():
    """Test if Docker services are running."""
    print("\n🔍 Testing Docker Services...")
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("Docker Services Status:")
            print(result.stdout)

            if "network-guardian" in result.stdout:
                print("✅ Network Guardian service is running")
            else:
                print("❌ Network Guardian service not found")

            if "adguard" in result.stdout:
                print("✅ AdGuard service is running")
            else:
                print("❌ AdGuard service not found")

            return True
        else:
            print(f"❌ Docker command failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Docker command timed out")
        return False
    except FileNotFoundError:
        print("❌ Docker not found on system")
        return False
    except Exception as e:
        print(f"❌ Docker test failed: {e}")
        return False


def main():
    """Run all connectivity tests."""
    print("🚀 Network Guardian AI - Connectivity Test")
    print("=" * 50)

    tests = [
        ("Docker Services", test_docker_services),
        ("Backend Health", test_backend_health),
        ("AdGuard Connectivity", test_adguard_connectivity),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Network Guardian AI is ready.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")

    return all_passed


if __name__ == "__main__":
    main()
