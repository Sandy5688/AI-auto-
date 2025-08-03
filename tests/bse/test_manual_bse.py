#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime, timezone

# Add src to path - go up two directories
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

def test_different_payload_types():
    """Test BSE with different payload types"""
    try:
        from bse import main_processing_pipeline
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure bse.py exists in the src/ directory")
        return
    
    # Rest of your test code...
    test_cases = [
        {
            "name": "Normal User Activity",
            "payload": {
                "source_type": "user_activity",
                "event_type": "page_view",
                "user_id": "normal_user_001",
                "session_duration": 240,
                "actions_per_minute": 3,
                "ip_address": "203.0.113.10",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        },
        {
            "name": "Suspicious Login Activity",
            "payload": {
                "source_type": "login",
                "user_id": "suspicious_user_001", 
                "login_method": "email",
                "success": True,
                "attempts": 4,
                "ip_address": "192.168.1.100",
                "user_agent": "bot crawler v1.0"
            }
        }
    ]
    
    print("🧪 Testing Enhanced BSE with Different Payload Types")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        
        try:
            result = main_processing_pipeline(test_case['payload'])
            
            print(f"✓ User ID: {result.get('user_id', 'N/A')}")
            print(f"✓ Score: {result.get('behavior_score', 'N/A')}/100")
            print(f"✓ Risk Level: {result.get('risk_level', 'N/A')}")
            print(f"✓ Risk Flags: {result.get('risk_flags', [])}")
            print(f"✓ API Sent: {result.get('api_sent', False)}")
            print(f"✓ Processed: {result.get('processed', False)}")
            
        except Exception as e:
            print(f"❌ Error: {e}")

def test_score_ranges():
    """Test different score ranges"""
    try:
        from bse import get_risk_level
    except ImportError:
        print("❌ Cannot import get_risk_level - check bse.py exists")
        return
    
    print("\n🎯 Testing Score Range Classifications")
    print("-" * 40)
    
    test_scores = [0, 25, 49, 50, 65, 79, 80, 95, 100]
    
    for score in test_scores:
        risk_level = get_risk_level(score)
        print(f"Score {score:3d} → {risk_level}")

if __name__ == "__main__":
    print("🚀 Enhanced BSE Manual Testing Suite")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    test_different_payload_types()
    test_score_ranges()
    
    print("\n✅ Manual testing completed!")
