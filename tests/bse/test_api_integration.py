#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timezone

def test_api_endpoint():
    """Test sending data to the client's API endpoint"""
    
    # Mock client API endpoint (replace with actual when available)
    API_URL = "https://api.memefihub.com/ai/bse/score-update"
    
    test_payload = {
        "user_id": "integration_test_user",
        "behavior_score": 75,
        "risk_level": "normal",
        "risk_flags": ["test_flag"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_data": {
            "event_type": "test",
            "source_type": "integration_test",
            "processed_at": datetime.now(timezone.utc).isoformat()
        },
        "score_breakdown": {
            "base_score": 100,
            "adjustments": -25,
            "flag_count": 1
        }
    }
    
    print("🌐 Testing API Integration")
    print(f"Endpoint: {API_URL}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    
    try:
        response = requests.post(
            API_URL,
            json=test_payload,
            timeout=30,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'BSE-ScoreEngine/1.0',
                'X-BSE-Version': '1.0.0'
            }
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code in [200, 201]:
            print("✅ API integration successful!")
        else:
            print("⚠️ API returned non-success status")
            
    except requests.exceptions.ConnectionError:
        print("🔌 API endpoint not available (expected for testing)")
    except Exception as e:
        print(f"❌ API test error: {e}")

if __name__ == "__main__":
    test_api_endpoint()
