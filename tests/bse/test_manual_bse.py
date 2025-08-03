#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime, timezone

# Add src to path - go up two directories
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

def test_different_payload_types():
    """Test BSE with different payload types including bot detection and fake referrals"""
    try:
        from bse import main_processing_pipeline
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure bse.py exists in the src/ directory")
        return
    
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
        },
        {
            "name": "Bot-like Activity with FingerprintJS",
            "payload": {
                "source_type": "user_activity",
                "event_type": "page_view",
                "user_id": "bot_user_001",
                "session_duration": 5,
                "actions_per_minute": 50,
                "ip_address": "203.0.113.100",
                "user_agent": "HeadlessChrome/91.0",
                "fingerprint_id": "fp_bot_test_123"
            }
        },
        {
            "name": "Clean Referral Activity", 
            "payload": {
                "source_type": "referral",
                "user_id": "referrer_clean_001",
                "referred_user_id": "referred_clean_001",
                "referral_code": "CLEAN123",
                "ip_address": "203.0.113.50",
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6)"
            }
        },
        {
            "name": "Suspicious Referral (Same IP)",
            "payload": {
                "source_type": "referral", 
                "user_id": "referrer_suspicious_001",
                "referred_user_id": "referred_suspicious_001",
                "referral_code": "FAKE123",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
        }
    ]
    
    print("🧪 Testing Enhanced BSE with Bot Detection & Fake Referral Filter")
    print("=" * 70)
    
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
            
            # NEW: Show bot detection results
            if result.get('bot_detection_enabled', False):
                bot_analysis = result.get('bot_analysis', {})
                print(f"🤖 Bot Detection: {bool(bot_analysis)}")
                if bot_analysis:
                    fingerprint_data = bot_analysis.get('fingerprint', {})
                    if fingerprint_data:
                        print(f"   Bot Probability: {fingerprint_data.get('bot_probability', 0):.2f}")
                        print(f"   Bot Signals: {fingerprint_data.get('bot_signals', [])}")
            
        except Exception as e:
            print(f"❌ Error: {e}")

def test_bot_detection_scenarios():
    """Test various bot detection scenarios"""
    try:
        from bse import FingerprintJSDetector, IPHubDetector
    except ImportError:
        print("❌ Cannot import bot detection classes")
        return
    
    print("\n🤖 Testing Bot Detection Scenarios")
    print("-" * 40)
    
    # Test scenarios
    scenarios = [
        {"name": "Clean Human User", "fingerprint_id": "fp_human_123"},
        {"name": "Suspicious Bot", "fingerprint_id": "fp_bot_456"},
        {"name": "Datacenter IP", "ip": "203.0.113.100"},
        {"name": "Residential IP", "ip": "203.0.113.50"}
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        
        if 'fingerprint_id' in scenario:
            # Mock FingerprintJS test (would normally call API)
            print(f"  FingerprintJS ID: {scenario['fingerprint_id']}")
            print(f"  (API call would be made in real implementation)")
        
        if 'ip' in scenario:
            # Mock IPHub test
            print(f"  IP Address: {scenario['ip']}")
            print(f"  (IPHub API call would be made in real implementation)")

def test_fake_referral_scenarios():
    """Test various fake referral scenarios"""
    try:
        from bse import FakeReferralDetector
    except ImportError:
        print("❌ Cannot import FakeReferralDetector")
        return
    
    print("\n🚨 Testing Fake Referral Detection Scenarios")
    print("-" * 45)
    
    scenarios = [
        {
            "name": "Clean Referral",
            "referrer_ip": "203.0.113.10",
            "referred_ip": "203.0.113.20",
            "referral_count": 2,
            "user_active": True
        },
        {
            "name": "Same IP Referral (Suspicious)",
            "referrer_ip": "192.168.1.100", 
            "referred_ip": "192.168.1.100",
            "referral_count": 1,
            "user_active": True
        },
        {
            "name": "High Velocity Referrals",
            "referrer_ip": "203.0.113.50",
            "referred_ip": "203.0.113.60",
            "referral_count": 15,
            "user_active": True
        },
        {
            "name": "Inactive Referred User",
            "referrer_ip": "203.0.113.70",
            "referred_ip": "203.0.113.80",
            "referral_count": 1,
            "user_active": False
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        print(f"  Referrer IP: {scenario['referrer_ip']}")
        print(f"  Referred IP: {scenario['referred_ip']}")
        print(f"  Daily Referrals: {scenario['referral_count']}")
        print(f"  Referred User Active: {scenario['user_active']}")
        
        # Determine suspicion level
        suspicious_factors = 0
        if scenario['referrer_ip'] == scenario['referred_ip']:
            suspicious_factors += 1
            print(f"  ⚠️  Same IP detected")
        if scenario['referral_count'] > 10:
            suspicious_factors += 1
            print(f"  ⚠️  High velocity detected")
        if not scenario['user_active']:
            suspicious_factors += 1
            print(f"  ⚠️  Inactive user detected")
        
        if suspicious_factors == 0:
            print(f"  ✅ Clean referral")
        else:
            print(f"  🚨 Suspicious ({suspicious_factors} red flags)")

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
    print("🚀 Enhanced BSE Manual Testing Suite with Bot Detection & Fake Referral Filter")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    test_different_payload_types()
    test_bot_detection_scenarios()
    test_fake_referral_scenarios()
    test_score_ranges()
    
    print("\n✅ Manual testing completed!")
