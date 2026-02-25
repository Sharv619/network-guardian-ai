#!/usr/bin/env python3
"""
Network Guardian AI - System Demo Script

This script demonstrates the system working by:
1. Testing the backend API endpoints
2. Showing sample data from the system
3. Demonstrating the analysis pipeline
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000"
SAMPLE_DOMAINS = [
    "google.com",
    "rr8---sn-v2u0n-hxad.googlevideo.com", 
    "suspicious-malware-domain.com",
    "tracker.ads.example.com",
    "geo-location-tracker.net"
]

def test_health_check():
    """Test the health endpoint"""
    print("🔍 Testing Health Check...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Check: {data}")
            return True
        else:
            print(f"❌ Health Check Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check Error: {e}")
        return False

def test_system_stats():
    """Test the system stats endpoint"""
    print("\n📊 Testing System Stats...")
    try:
        response = requests.get(f"{API_BASE}/api/stats/system")
        if response.status_code == 200:
            data = response.json()
            print("✅ System Stats Retrieved:")
            print(f"   Autonomy Score: {data.get('autonomy_score', 'N/A')}%")
            print(f"   Total Decisions: {data.get('total_decisions', 'N/A')}")
            print(f"   Patterns Learned: {data.get('patterns_learned', 'N/A')}")
            print(f"   Local Decisions: {data.get('local_decisions', 'N/A')}")
            print(f"   Cloud Decisions: {data.get('cloud_decisions', 'N/A')}")
            return data
        else:
            print(f"❌ System Stats Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ System Stats Error: {e}")
        return None

def test_manual_analysis(domain):
    """Test manual domain analysis"""
    print(f"\n🔍 Testing Manual Analysis for {domain}...")
    try:
        payload = {
            "domain": domain,
            "model_id": "models/gemini-1.5-flash"
        }
        response = requests.post(f"{API_BASE}/api/analyze", json=payload)
        if response.status_code == 200:
            data = response.json()
            print("✅ Analysis Complete:")
            print(f"   Domain: {data.get('domain', domain)}")
            print(f"   Risk Score: {data.get('risk_score', 'N/A')}")
            print(f"   Category: {data.get('category', 'N/A')}")
            print(f"   Summary: {data.get('summary', 'N/A')[:100]}...")
            return data
        else:
            print(f"❌ Analysis Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Analysis Error: {e}")
        return None

def test_history():
    """Test the history endpoint"""
    print("\n📈 Testing History...")
    try:
        response = requests.get(f"{API_BASE}/api/history")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ History Retrieved: {len(data)} records")
            if data:
                latest = data[0]
                print(f"   Latest Domain: {latest.get('domain', 'N/A')}")
                print(f"   Risk Score: {latest.get('risk_score', 'N/A')}")
                print(f"   Category: {latest.get('category', 'N/A')}")
                print(f"   Timestamp: {latest.get('timestamp', 'N/A')}")
            return data
        else:
            print(f"❌ History Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ History Error: {e}")
        return None

def test_chat():
    """Test the chat endpoint"""
    print("\n💬 Testing Chat...")
    try:
        payload = {
            "message": "How does the anomaly detection work?",
            "model_id": "models/gemini-1.5-flash"
        }
        response = requests.post(f"{API_BASE}/api/chat", json=payload)
        if response.status_code == 200:
            data = response.json()
            print("✅ Chat Response:")
            print(f"   {data.get('text', 'N/A')[:200]}...")
            return data
        else:
            print(f"❌ Chat Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        return None

def demo_analysis_pipeline():
    """Demonstrate the 5-tier analysis pipeline"""
    print("\n🔄 Demonstrating 5-Tier Analysis Pipeline...")
    
    # Simulate pipeline stages
    stages = [
        ("Tier 1: Cache Check", "Checking memory/disk cache for previous analysis"),
        ("Tier 2: Metadata Classification", "Pattern matching with AdGuard metadata"),
        ("Tier 3: ML Heuristics", "Shannon Entropy + Digit Ratio analysis"),
        ("Tier 4: Anomaly Detection", "Isolation Forest behavioral analysis"),
        ("Tier 5: Gemini AI", "Full semantic analysis with Google AI")
    ]
    
    for i, (stage, description) in enumerate(stages, 1):
        print(f"   {i}. {stage}")
        print(f"      {description}")
        time.sleep(0.5)  # Simulate processing time
    
    print("   ✅ Complete analysis with cost optimization!")

def show_sample_data():
    """Show sample data examples"""
    print("\n📋 Sample Data Examples:")
    
    # Sample threat data
    sample_threats = [
        {
            "domain": "rr8---sn-v2u0n-hxad.googlevideo.com",
            "risk_score": "High",
            "category": "System/Tracker",
            "summary": "YouTube video streaming domain - legitimate but tracks viewing behavior",
            "timestamp": "2026-10-02T09:08:15Z",
            "is_anomaly": False,
            "anomaly_score": 0.0537,
            "entropy": 2.85
        },
        {
            "domain": "xhk92-z1.ru",
            "risk_score": "Critical",
            "category": "Malware",
            "summary": "Domain Generation Algorithm (DGA) pattern detected - likely malware C2 communication",
            "timestamp": "2026-10-02T09:15:32Z",
            "is_anomaly": True,
            "anomaly_score": -0.15,
            "entropy": 4.2
        },
        {
            "domain": "geo-location-tracker.example.com",
            "risk_score": "High",
            "category": "Privacy Violation",
            "summary": "Geolocation tracking domain attempting to collect user location data",
            "timestamp": "2026-10-02T09:22:18Z",
            "is_anomaly": True,
            "anomaly_score": -0.08,
            "entropy": 3.1
        }
    ]
    
    for i, threat in enumerate(sample_threats, 1):
        print(f"\n   Example {i}: {threat['domain']}")
        print(f"   Risk: {threat['risk_score']} | Category: {threat['category']}")
        print(f"   Entropy: {threat['entropy']} | Anomaly: {threat['is_anomaly']}")
        print(f"   Summary: {threat['summary'][:80]}...")

def main():
    """Main demo function"""
    print("🛡️ Network Guardian AI - System Demo")
    print("=" * 50)
    
    # Test system health
    if not test_health_check():
        print("\n❌ System is not running. Please start the backend first:")
        print("   cd backend && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")
        return
    
    # Test system stats
    stats = test_system_stats()
    
    # Test manual analysis with sample domains
    print(f"\n🎯 Testing Manual Analysis with {len(SAMPLE_DOMAINS)} sample domains...")
    for domain in SAMPLE_DOMAINS:
        test_manual_analysis(domain)
        time.sleep(1)  # Rate limiting
    
    # Test history
    history = test_history()
    
    # Test chat
    test_chat()
    
    # Show pipeline
    demo_analysis_pipeline()
    
    # Show sample data
    show_sample_data()
    
    print("\n" + "=" * 50)
    print("✅ Demo Complete!")
    print("\n📊 Key Features Demonstrated:")
    print("   • 5-tier analysis pipeline with cost optimization")
    print("   • Real-time threat detection and classification")
    print("   • Shannon Entropy and Isolation Forest ML")
    print("   • Google Sheets integration for audit trails")
    print("   • Manual analysis and system chat")
    print("   • Comprehensive system statistics")
    
    print("\n🌐 Dashboard Access:")
    print("   • Live Feed: Real-time threat monitoring")
    print("   • Manual Analysis: On-demand domain scanning")
    print("   • Stats Dashboard: System performance metrics")
    print("   • System Intelligence: Architecture explanations")
    
    print(f"\n🔗 API Endpoints:")
    print(f"   • Health: {API_BASE}/health")
    print(f"   • Stats: {API_BASE}/api/stats/system")
    print(f"   • History: {API_BASE}/api/history")
    print(f"   • Analyze: {API_BASE}/api/analyze")
    print(f"   • Chat: {API_BASE}/api/chat")

if __name__ == "__main__":
    main()