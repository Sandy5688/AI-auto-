import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

# Mock environment
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "FINGERPRINTJS_API_KEY": "test-fpjs-key",
    "TESTING_MODE": "1"
})

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

def test_fingerprint_collector():
    """Test fingerprint data collection"""
    from maf import FingerprintCollector
    
    collector = FingerprintCollector()
    
    request_data = {
        "ip_address": "203.0.113.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "screen_resolution": "1920x1080",
        "timezone": "America/New_York",
        "language": "en-US"
    }
    
    fingerprint = collector.collect_fingerprint("test_user", "signup", request_data)
    
    assert fingerprint.user_id == "test_user"
    assert fingerprint.event_type == "signup"
    assert fingerprint.ip_address == "203.0.113.100"
    assert len(fingerprint.device_hash) == 64  # SHA256 hash length

def test_same_ip_signup_pattern():
    """Test same IP signup pattern detection"""
    from maf import SameIPSignupPattern, FingerprintData
    
    pattern = SameIPSignupPattern()
    
    # Create test data with multiple signups from same IP
    now = datetime.now(timezone.utc)
    fingerprint_data = []
    
    for i in range(6):  # Exceeds threshold of 5
        fp = FingerprintData(
            ip_address="192.168.1.100",
            user_agent=f"Browser_{i}",
            device_hash=f"device_{i}",
            timestamp=now - timedelta(minutes=i*5),
            user_id=f"user_{i}",
            event_type="signup"
        )
        fingerprint_data.append(fp)
    
    anomalies = pattern.detect(fingerprint_data)
    
    assert len(anomalies) == 1
    assert anomalies[0]["pattern"] == "same_ip_signups"
    assert anomalies[0]["severity"] == "HIGH"
    assert len(anomalies[0]["affected_users"]) == 6

def test_rapid_action_pattern():
    """Test rapid action pattern detection"""
    from maf import RapidActionPattern, FingerprintData
    
    pattern = RapidActionPattern("wallet_connection")
    
    now = datetime.now(timezone.utc)
    fingerprint_data = []
    
    # Create 12 wallet connections within 4 minutes (within 5-minute window)
    for i in range(12):
        fp = FingerprintData(
            ip_address="203.0.113.50",
            user_agent="Test Browser",
            device_hash="test_device",
            timestamp=now - timedelta(seconds=i*20),  # 20 seconds apart instead of 1 minute
            user_id="rapid_user",
            event_type="wallet_connection"
        )
        fingerprint_data.append(fp)
    
    anomalies = pattern.detect(fingerprint_data)
    
    assert len(anomalies) == 1
    assert anomalies[0]["pattern"] == "rapid_wallet_connections"
    assert anomalies[0]["severity"] == "MEDIUM"


def test_login_velocity_pattern():
    """Test login velocity pattern detection"""
    from maf import LoginVelocityPattern, FingerprintData
    
    pattern = LoginVelocityPattern()
    
    now = datetime.now(timezone.utc)
    fingerprint_data = []
    
    # Create 12 logins from same IP within 4 minutes (within 5-minute window)
    for i in range(12):
        fp = FingerprintData(
            ip_address="10.0.0.1",
            user_agent="Test Browser",
            device_hash=f"device_{i}",
            timestamp=now - timedelta(seconds=i*20),  # 20 seconds apart instead of 1 minute
            user_id=f"user_{i}",
            event_type="login"
        )
        fingerprint_data.append(fp)
    
    anomalies = pattern.detect(fingerprint_data)
    
    assert len(anomalies) == 1
    assert anomalies[0]["pattern"] == "login_velocity_per_ip"
    assert anomalies[0]["severity"] == "HIGH"

def test_flag_color_determination():
    """Test flag color logic"""
    from maf import MultiLayerAnomalyFlagger
    
    maf = MultiLayerAnomalyFlagger()
    
    # Test GREEN flag
    velocity_metrics = {"velocity_score": "low"}
    flag = maf.determine_flag_color(85, velocity_metrics, [])
    assert flag == "GREEN"
    
    # Test YELLOW flag
    flag = maf.determine_flag_color(65, velocity_metrics, [])
    assert flag == "YELLOW"
    
    # Test RED flag - low score
    flag = maf.determine_flag_color(40, velocity_metrics, [])
    assert flag == "RED"
    
    # Test RED flag - high severity anomaly
    high_severity_anomaly = [{"severity": "HIGH", "pattern": "test"}]
    flag = maf.determine_flag_color(80, velocity_metrics, high_severity_anomaly)
    assert flag == "RED"

def test_device_hash_generation():
    """Test device hash generation consistency"""
    from maf import FingerprintCollector
    
    collector = FingerprintCollector()
    
    request_data = {
        "ip_address": "203.0.113.100",
        "user_agent": "Mozilla/5.0 Test",
        "screen_resolution": "1920x1080",
        "timezone": "UTC",
        "language": "en-US"
    }
    
    hash1 = collector.generate_device_hash("203.0.113.100", "Mozilla/5.0 Test", request_data)
    hash2 = collector.generate_device_hash("203.0.113.100", "Mozilla/5.0 Test", request_data)
    
    # Same input should generate same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 length
    
    # Different input should generate different hash
    request_data["user_agent"] = "Different Browser"
    hash3 = collector.generate_device_hash("203.0.113.100", "Different Browser", request_data)
    assert hash1 != hash3

@patch('maf.supabase')
def test_maf_integration_with_bse(mock_supabase):
    """Test MAF integration with BSE"""
    from maf import integrate_maf_with_bse
    
    # Mock supabase responses
    mock_supabase.table().select().gte().execute.return_value = MagicMock(data=[])
    mock_supabase.table().insert().execute.return_value = MagicMock(data=[])
    mock_supabase.table().eq().gte().execute.return_value = MagicMock(data=[])
    
    bse_result = {
        "user_id": "integration_test_user",
        "behavior_score": 75,
        "risk_level": "normal",
        "risk_flags": ["new_account"],
        "processed": True
    }
    
    request_data = {
        "event_type": "signup",
        "ip_address": "203.0.113.75",
        "user_agent": "Mozilla/5.0 Test Browser"
    }
    
    integrated_result = integrate_maf_with_bse(bse_result, request_data)
    
    # Check integration structure
    assert "maf_analysis" in integrated_result
    assert "final_risk_assessment" in integrated_result
    assert integrated_result["user_id"] == "integration_test_user"
    assert integrated_result["behavior_score"] == 75
    
    # Check MAF analysis structure
    maf_analysis = integrated_result["maf_analysis"]
    assert "flag_color" in maf_analysis
    assert "anomalies_detected" in maf_analysis
    assert "velocity_metrics" in maf_analysis
    assert "fingerprint_id" in maf_analysis

@patch('maf.supabase')  # Patch module-level supabase, not instance attribute
def test_velocity_metrics_calculation(mock_supabase):
    """Test velocity metrics calculation"""
    from maf import MultiLayerAnomalyFlagger
    
    maf = MultiLayerAnomalyFlagger()
    
    # Mock high velocity scenario
    mock_data = []
    now = datetime.now(timezone.utc)
    for i in range(20):  # High event count
        mock_data.append({
            "user_id": "velocity_test_user",
            "timestamp": (now - timedelta(minutes=i)).isoformat(),
            "ip_address": "203.0.113.50",
            "device_hash": f"device_{i % 3}"  # 3 different devices
        })
    
    mock_supabase.table().select().eq().gte().execute.return_value = MagicMock(data=mock_data)
    
    velocity_metrics = maf.calculate_velocity_metrics("velocity_test_user", "signup")
    
    assert velocity_metrics["events_last_hour"] == 20
    assert velocity_metrics["velocity_score"] == "high"
    assert velocity_metrics["unique_devices_last_hour"] == 3

def test_referral_spam_pattern():
    """Test referral spam detection with diversity analysis"""
    from maf import ReferralSpamPattern, FingerprintData
    
    pattern = ReferralSpamPattern()
    
    now = datetime.now(timezone.utc)
    fingerprint_data = []
    
    # Create 25 referrals (exceeds threshold of 20) with low diversity
    for i in range(25):
        fp = FingerprintData(
            ip_address="203.0.113.75",
            user_agent="Test Browser",
            device_hash="spam_device",
            timestamp=now - timedelta(minutes=i),
            user_id="spam_user",
            event_type="referral"
        )
        # Low diversity - mostly same referrer
        fp.browser_details = {"referrer_url": "same-source.com" if i < 23 else f"different-{i}.com"}
        fingerprint_data.append(fp)
    
    anomalies = pattern.detect(fingerprint_data)
    
    assert len(anomalies) == 1
    assert anomalies[0]["pattern"] == "referral_spam"
    assert anomalies[0]["severity"] == "HIGH"  # Low diversity should trigger HIGH severity
    assert anomalies[0]["fingerprint_data"]["diversity_score"] < 0.3

def test_edge_cases():
    """Test edge cases and error handling"""
    from maf import MultiLayerAnomalyFlagger
    
    maf = MultiLayerAnomalyFlagger()
    
    # Test with empty request data
    result = maf.process_event("edge_test_user", "test", {})
    assert result["user_id"] == "edge_test_user"
    assert "flag_color" in result
    
    # Test with None behavior score
    result = maf.process_event("edge_test_user", "test", {"ip_address": "127.0.0.1"}, None)
    assert result["behavior_score"] is None
    assert result["flag_color"] in ["GREEN", "YELLOW", "RED"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
