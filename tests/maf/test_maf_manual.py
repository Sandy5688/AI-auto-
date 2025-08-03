#!/usr/bin/env python3
import sys
import os
from datetime import datetime, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

def test_maf_scenarios():
    """Test MAF with different scenarios"""
    try:
        from maf import MultiLayerAnomalyFlagger
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return
    
    maf = MultiLayerAnomalyFlagger()
    
    print("🔍 Testing Multi-Layer Anomaly Flagger Scenarios")
    print("=" * 60)
    
    test_scenarios = [
        {
            "name": "Normal User Signup",
            "user_id": "normal_user_maf",
            "event_type": "signup",
            "request_data": {
                "ip_address": "203.0.113.50",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "screen_resolution": "1920x1080",
                "timezone": "America/New_York"
            },
            "behavior_score": 85
        },
        {
            "name": "Suspicious Multiple Device Login",
            "user_id": "suspicious_multi_device",
            "event_type": "login",
            "request_data": {
                "ip_address": "192.168.1.100",  # Private IP
                "user_agent": "Bot/1.0 Crawler",  # Bot-like agent
                "screen_resolution": "800x600",
                "timezone": "UTC"
            },
            "behavior_score": 45
        },
        {
            "name": "Rapid Wallet Connection",
            "user_id": "rapid_wallet_user",
            "event_type": "wallet_connection",
            "request_data": {
                "ip_address": "10.0.0.1",
                "user_agent": "MetaMask/1.0",
                "screen_resolution": "1366x768"
            },
            "behavior_score": 65
        },
        {
            "name": "High Confidence User",
            "user_id": "trusted_user_maf",
            "event_type": "meme_upload", 
            "request_data": {
                "ip_address": "8.8.8.8",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "visitor_id": "trusted_visitor_123"
            },
            "behavior_score": 95
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")
        
        try:
            result = maf.process_event(
                scenario["user_id"],
                scenario["event_type"],
                scenario["request_data"],
                scenario["behavior_score"]
            )
            
            print(f"✓ User ID: {result['user_id']}")
            print(f"✓ Event Type: {result['event_type']}")
            print(f"✓ Flag Color: {result['flag_color']}")
            print(f"✓ Anomalies Detected: {result['anomalies_detected']}")
            print(f"✓ Behavior Score: {result['behavior_score']}")
            print(f"✓ Velocity Score: {result['velocity_metrics']['velocity_score']}")
            print(f"✓ Confidence: {result['confidence_score']:.2f}")
            
            if result['anomalies']:
                print("⚠️ Detected Anomalies:")
                for anomaly in result['anomalies']:
                    print(f"   - {anomaly['pattern']}: {anomaly['description']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")

def test_integration_with_bse():
    """Test MAF integration with BSE"""
    try:
        from maf import integrate_maf_with_bse
    except ImportError:
        print("❌ Cannot import MAF integration")
        return
    
    print("\n🔄 Testing BSE + MAF Integration")
    print("-" * 40)
    
    # Simulate BSE result
    bse_result = {
        "user_id": "integration_test",
        "behavior_score": 55,
        "risk_level": "normal",
        "risk_flags": ["new_account", "rapid_interactions"],
        "processed": True
    }
    
    request_data = {
        "event_type": "signup",
        "ip_address": "203.0.113.100",
        "user_agent": "Mozilla/5.0 Chrome Browser",
        "screen_resolution": "1920x1080"
    }
    
    try:
        integrated_result = integrate_maf_with_bse(bse_result, request_data)
        
        print(f"✓ Original BSE Score: {integrated_result['behavior_score']}")
        print(f"✓ Original BSE Risk: {integrated_result['risk_level']}")
        print(f"✓ MAF Flag Color: {integrated_result['maf_analysis']['flag_color']}")
        print(f"✓ Final Risk Assessment: {integrated_result['final_risk_assessment']}")
        print(f"✓ Total BSE Flags: {len(integrated_result['risk_flags'])}")
        print(f"✓ Total MAF Anomalies: {integrated_result['maf_analysis']['anomalies_detected']}")
        
    except Exception as e:
        print(f"❌ Integration error: {e}")

if __name__ == "__main__":
    print("🚀 MAF Manual Testing Suite")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    test_maf_scenarios()
    test_integration_with_bse()
    
    print("\n✅ MAF manual testing completed!")
