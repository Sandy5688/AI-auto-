#!/usr/bin/env python3
import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

# Mock environment
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "TESTING_MODE": "1"
})

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

def test_fake_referral_same_ip_detection():
    """Test Rule 1: Same IP referral detection"""
    from bse import FakeReferralDetector
    
    with patch('bse.supabase') as mock_supabase:
        # Mock referrer activity with IP
        mock_referrer_response = MagicMock()
        mock_referrer_response.data = [
            {"metadata": {"ip_address": "192.168.1.100"}}
        ]
        
        # Mock referred user activity with same IP
        mock_referred_response = MagicMock()
        mock_referred_response.data = [
            {"metadata": {"ip_address": "192.168.1.100"}}
        ]
        
        mock_supabase.table().select().eq().gte().execute.side_effect = [
            mock_referrer_response, mock_referred_response
        ]
        
        result = FakeReferralDetector._check_same_ip_referral(
            "referrer_123", "referred_456", "192.168.1.100"
        )
        
        assert result == True

def test_fake_referral_different_ip_clean():
    """Test Rule 1: Different IP should be clean"""
    from bse import FakeReferralDetector
    
    with patch('bse.supabase') as mock_supabase:
        # Mock referrer activity with different IP
        mock_referrer_response = MagicMock()
        mock_referrer_response.data = [
            {"metadata": {"ip_address": "192.168.1.100"}}
        ]
        
        # Mock referred user activity with different IP
        mock_referred_response = MagicMock()
        mock_referred_response.data = [
            {"metadata": {"ip_address": "203.0.113.50"}}
        ]
        
        mock_supabase.table().select().eq().gte().execute.side_effect = [
            mock_referrer_response, mock_referred_response
        ]
        
        result = FakeReferralDetector._check_same_ip_referral(
            "referrer_123", "referred_456", "192.168.1.100"
        )
        
        assert result == False

def test_fake_referral_ip_velocity_exceeded():
    """Test Rule 2: IP velocity > 3 referrals/hour"""
    from bse import FakeReferralDetector
    
    with patch('bse.supabase') as mock_supabase:
        # Mock 5 referrals from same IP in last hour
        mock_response = MagicMock()
        mock_response.data = []
        for i in range(5):
            mock_response.data.append({
                "metadata": {"ip_address": "192.168.1.100"}
            })
        
        mock_supabase.table().select().eq().gte().execute.return_value = mock_response
        
        result = FakeReferralDetector._check_ip_referral_velocity("192.168.1.100")
        
        assert result == True

def test_fake_referral_ip_velocity_normal():
    """Test Rule 2: Normal IP velocity should be clean"""
    from bse import FakeReferralDetector
    
    with patch('bse.supabase') as mock_supabase:
        # Mock only 2 referrals from same IP
        mock_response = MagicMock()
        mock_response.data = [
            {"metadata": {"ip_address": "192.168.1.100"}},
            {"metadata": {"ip_address": "192.168.1.100"}}
        ]
        
        mock_supabase.table().select().eq().gte().execute.return_value = mock_response
        
        result = FakeReferralDetector._check_ip_referral_velocity("192.168.1.100")
        
        assert result == False

def test_fake_referral_inactive_user_detection():
    """Test Rule 3: Inactive referred user detection"""
    from bse import FakeReferralDetector
    
    with patch('bse.supabase') as mock_supabase:
        # Mock user created 2 days ago (past grace period)
        past_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        mock_user_response = MagicMock()
        mock_user_response.data = {"created_at": past_date}
        
        # Mock zero activity
        mock_activity_response = MagicMock()
        mock_activity_response.count = 0
        
        mock_supabase.table().select().eq().single().execute.return_value = mock_user_response
        mock_supabase.table().select().eq().execute.return_value = mock_activity_response
        
        result = FakeReferralDetector._check_referred_user_activity("referred_456")
        
        assert result == True

def test_fake_referral_active_user_clean():
    """Test Rule 3: Active referred user should be clean"""
    from bse import FakeReferralDetector
    
    with patch('bse.supabase') as mock_supabase:
        # Mock user created 2 days ago
        past_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        mock_user_response = MagicMock()
        mock_user_response.data = {"created_at": past_date}
        
        # Mock some activity
        mock_activity_response = MagicMock()
        mock_activity_response.count = 5
        
        mock_supabase.table().select().eq().single().execute.return_value = mock_user_response
        mock_supabase.table().select().eq().execute.return_value = mock_activity_response
        
        result = FakeReferralDetector._check_referred_user_activity("referred_456")
        
        assert result == False

def test_fake_referral_grace_period():
    """Test Rule 3: Users in grace period should be clean"""
    from bse import FakeReferralDetector
    
    with patch('bse.supabase') as mock_supabase:
        # Mock user created 2 hours ago (within grace period)
        recent_date = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        mock_user_response = MagicMock()
        mock_user_response.data = {"created_at": recent_date}
        
        mock_supabase.table().select().eq().single().execute.return_value = mock_user_response
        
        result = FakeReferralDetector._check_referred_user_activity("referred_456")
        
        assert result == False

def test_fake_referral_analyze_clean():
    """Test complete fake referral analysis - clean referral"""
    from bse import FakeReferralDetector
    
    referral_data = {
        "user_id": "referrer_123",
        "event_type": "referral",
        "metadata": {
            "referred_user_id": "referred_456",
            "ip_address": "203.0.113.100"
        }
    }
    
    user_context = {"account_age_days": 30}
    
    with patch.object(FakeReferralDetector, '_check_same_ip_referral', return_value=False):
        with patch.object(FakeReferralDetector, '_check_ip_referral_velocity', return_value=False):
            with patch.object(FakeReferralDetector, '_check_referred_user_activity', return_value=False):
                with patch.object(FakeReferralDetector, '_additional_referral_checks', return_value=([], 0)):
                    result = FakeReferralDetector.analyze_referral(referral_data, user_context)
                    
                    assert result["is_fake_referral"] == False
                    assert result["fake_signals"] == []
                    assert result["risk_score"] == 0

def test_fake_referral_analyze_multiple_violations():
    """Test complete fake referral analysis - multiple violations"""
    from bse import FakeReferralDetector
    
    referral_data = {
        "user_id": "referrer_123", 
        "event_type": "referral",
        "metadata": {
            "referred_user_id": "referred_456",
            "ip_address": "192.168.1.100"
        }
    }
    
    user_context = {"account_age_days": 30}
    
    with patch.object(FakeReferralDetector, '_check_same_ip_referral', return_value=True):
        with patch.object(FakeReferralDetector, '_check_ip_referral_velocity', return_value=True):
            with patch.object(FakeReferralDetector, '_check_referred_user_activity', return_value=False):
                with patch.object(FakeReferralDetector, '_additional_referral_checks', return_value=(["rapid_referrals"], 15)):
                    result = FakeReferralDetector.analyze_referral(referral_data, user_context)
                    
                    assert result["is_fake_referral"] == True
                    assert "same_ip_referral" in result["fake_signals"]
                    assert "excessive_ip_referrals" in result["fake_signals"] 
                    assert "rapid_referrals" in result["fake_signals"]
                    assert result["risk_score"] == 70  # 30 + 25 + 15

def test_fake_referral_scoring_integration():
    """Test fake referral penalties in scoring system"""
    from bse import calculate_enhanced_score
    
    with patch('bse.get_user_context', return_value={"account_age_days": 30}):
        with patch('bse.get_recent_user_activity', return_value=[]):
            payload = {
                "user_id": "fake_referrer",
                "event_type": "referral",
                "metadata": {
                    "fake_referral_analysis": {
                        "is_fake_referral": True,
                        "fake_signals": ["same_ip_referral", "excessive_ip_referrals", "inactive_referred_user"]
                    }
                }
            }
            
            score, flags = calculate_enhanced_score(payload)
            
            # Should have penalties for all 3 fake referral signals
            assert score < 50  # Heavy penalties
            assert "fake_referral_same_ip" in flags
            assert "fake_referral_ip_abuse" in flags
            assert "fake_referral_inactive_user" in flags

if __name__ == "__main__":
    print("🚨 Running Fake Referral Detection Tests")
    pytest.main([__file__, "-v"])
