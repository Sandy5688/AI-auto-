import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta



# Mock environment
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "TESTING_MODE": "1",
    "BOT_DETECTION_ENABLED": "true",
    "FINGERPRINTJS_API_KEY": "test_fingerprint_key",
    "IPHUB_API_KEY": "test_iphub_key"
})

# Fix the path - go up two directories from tests/bse/ to reach src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

def test_payload_processor_user_activity():
    """Test PayloadProcessor with user activity payload"""
    from bse import PayloadProcessor
    
    processor = PayloadProcessor()
    payload = {
        "source_type": "user_activity",
        "event_type": "page_view",
        "user_id": "test_user",
        "session_duration": 300,
        "actions_per_minute": 5,
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0 Test Browser",
        "fingerprint_id": "fp_test_123"  # NEW: FingerprintJS ID
    }
    
    result = processor.process_payload(payload)
    
    assert result["user_id"] == "test_user"
    assert result["event_type"] == "page_view"
    assert result["metadata"]["session_duration"] == 300
    assert result["metadata"]["actions_per_minute"] == 5
    assert result["metadata"]["fingerprint_id"] == "fp_test_123"

def test_payload_processor_referral_activity():
    """Test PayloadProcessor with referral payload (NEW)"""
    from bse import PayloadProcessor
    
    processor = PayloadProcessor()
    payload = {
        "source_type": "referral",
        "user_id": "referrer_user",
        "referred_user_id": "referred_user",
        "referral_code": "REF123",
        "ip_address": "203.0.113.100",
        "user_agent": "Mozilla/5.0 Test Browser"
    }
    
    with patch('bse.get_user_context', return_value={"account_age_days": 30}):
        with patch('bse.FakeReferralDetector.analyze_referral') as mock_analyze:
            mock_analyze.return_value = {
                "is_fake_referral": False,
                "fake_signals": [],
                "risk_score": 0
            }
            
            result = processor.process_payload(payload)
            
            assert result["user_id"] == "referrer_user"
            assert result["event_type"] == "referral"
            assert result["metadata"]["referred_user_id"] == "referred_user"
            assert result["metadata"]["ip_address"] == "203.0.113.100"

def test_enhanced_scoring_new_account():
    """Test scoring logic for new accounts"""
    with patch('bse.get_user_context') as mock_context:
        mock_context.return_value = {"account_age_days": 0}
        
        with patch('bse.get_recent_user_activity') as mock_activity:
            mock_activity.return_value = []
            
            from bse import calculate_enhanced_score
            
            payload = {
                "user_id": "new_user",
                "event_type": "login",
                "metadata": {"login_attempts": 1}
            }
            
            score, flags = calculate_enhanced_score(payload)
            
            assert score < 100  # Should be penalized
            assert "new_account" in flags

def test_enhanced_scoring_bot_detection():
    """Test scoring with bot detection penalties (NEW)"""
    with patch('bse.get_user_context') as mock_context:
        mock_context.return_value = {"account_age_days": 30}
        
        with patch('bse.get_recent_user_activity') as mock_activity:
            mock_activity.return_value = []
            
            from bse import calculate_enhanced_score
            
            payload = {
                "user_id": "bot_user",
                "event_type": "login",
                "metadata": {
                    "login_attempts": 1,
                    "bot_analysis": {
                        "fingerprint": {
                            "bot_probability": 0.9,
                            "bot_signals": ["browser_bot_flag", "datacenter_ip"]
                        }
                    },
                    "bot_detection_flags": ["browser_bot_flag", "datacenter_ip"]
                }
            }
            
            score, flags = calculate_enhanced_score(payload)
            
            assert score < 50  # Should be heavily penalized
            assert "high_bot_probability" in flags
            assert "browser_detected_bot" in flags
            assert "datacenter_ip_usage" in flags

def test_enhanced_scoring_fake_referral():
    """Test scoring with fake referral penalties (NEW)"""
    with patch('bse.get_user_context') as mock_context:
        mock_context.return_value = {"account_age_days": 30}
        
        with patch('bse.get_recent_user_activity') as mock_activity:
            mock_activity.return_value = []
            
            from bse import calculate_enhanced_score
            
            payload = {
                "user_id": "fake_referrer",
                "event_type": "referral",
                "metadata": {
                    "fake_referral_analysis": {
                        "is_fake_referral": True,
                        "fake_signals": ["same_ip_referral", "excessive_ip_referrals"]
                    }
                }
            }
            
            score, flags = calculate_enhanced_score(payload)
            
            assert score < 50  # Should be heavily penalized
            assert "fake_referral_same_ip" in flags
            assert "fake_referral_ip_abuse" in flags

def test_fingerprint_js_detector():
    """Test FingerprintJS detector (NEW)"""
    from bse import FingerprintJSDetector
    
    with patch('requests.get') as mock_get:
        # Mock successful FingerprintJS response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "visits": [{
                "incognito": True,
                "browserDetails": {"bot": True},
                "confidence": {"score": 0.5},
                "ip": {"datacenter": True}
            }]
        }
        mock_get.return_value = mock_response
        
        result = FingerprintJSDetector.analyze_visitor("test_visitor_id")
        
        assert result["bot_probability"] > 0.5
        assert "incognito_mode" in result["bot_signals"]
        assert "browser_bot_flag" in result["bot_signals"]
        assert "low_confidence" in result["bot_signals"]
        assert "datacenter_ip" in result["bot_signals"]

def test_iphub_detector():
    """Test IPHub detector (NEW)"""
    from bse import IPHubDetector
    
    with patch('requests.get') as mock_get:
        # Mock IPHub response for blacklisted IP
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "block": 2,  # Hosting Provider
            "countryCode": "US",
            "isp": "Example Hosting"
        }
        mock_get.return_value = mock_response
        
        result = IPHubDetector.check_ip("203.0.113.100")
        
        assert result["is_blacklisted"] == True
        assert result["block_type"] == 2
        assert result["country_code"] == "US"

def test_fake_referral_detector_same_ip():
    """Test fake referral detection - same IP rule (NEW)"""
    from bse import FakeReferralDetector
    
    referral_data = {
        "user_id": "referrer_123",
        "event_type": "referral",
        "metadata": {
            "referred_user_id": "referred_456", 
            "ip_address": "192.168.1.100"
        }
    }
    
    with patch('bse.supabase') as mock_supabase:
        # Mock database responses showing same IP usage
        mock_referrer_activity = MagicMock()
        mock_referrer_activity.data = [{"metadata": {"ip_address": "192.168.1.100"}}]
        
        mock_referred_activity = MagicMock()
        mock_referred_activity.data = [{"metadata": {"ip_address": "192.168.1.100"}}]
        
        mock_supabase.table().select().eq().gte().execute.side_effect = [
            mock_referrer_activity, mock_referred_activity
        ]
        
        result = FakeReferralDetector._check_same_ip_referral(
            "referrer_123", "referred_456", "192.168.1.100"
        )
        
        assert result == True

def test_fake_referral_detector_ip_velocity():
    """Test fake referral detection - IP velocity rule (NEW)"""
    from bse import FakeReferralDetector
    
    with patch('bse.supabase') as mock_supabase:
        # Mock 5 referrals from same IP in last hour
        mock_response = MagicMock()
        mock_response.data = [
            {"metadata": {"ip_address": "192.168.1.100"}},
            {"metadata": {"ip_address": "192.168.1.100"}},
            {"metadata": {"ip_address": "192.168.1.100"}},
            {"metadata": {"ip_address": "192.168.1.100"}},
            {"metadata": {"ip_address": "192.168.1.100"}}
        ]
        mock_supabase.table().select().eq().gte().execute.return_value = mock_response
        
        result = FakeReferralDetector._check_ip_referral_velocity("192.168.1.100")
        
        assert result == True

def test_fake_referral_detector_inactive_user():
    """Test fake referral detection - inactive user rule (NEW)"""
    from bse import FakeReferralDetector
    
    with patch('bse.supabase') as mock_supabase:
        # FIXED: Use timedelta correctly
        past_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        mock_user_response = MagicMock()
        mock_user_response.data = {"created_at": past_date}
        
        # Mock no activity for this user
        mock_activity_response = MagicMock()
        mock_activity_response.count = 0
        
        mock_supabase.table().select().eq().single().execute.return_value = mock_user_response
        mock_supabase.table().select().eq().execute.return_value = mock_activity_response
        
        result = FakeReferralDetector._check_referred_user_activity("referred_456")
        
        assert result == True

def test_enhanced_scoring_suspicious_activity():
    """Test scoring with suspicious patterns"""
    with patch('bse.get_user_context') as mock_context:
        mock_context.return_value = {"account_age_days": 30}
        
        with patch('bse.get_recent_user_activity') as mock_activity:
            # Mock high activity volume
            mock_activity.return_value = [{"event_type": "login", "timestamp": "2025-08-03T10:00:00Z"}] * 200
            
            from bse import calculate_enhanced_score
            
            payload = {
                "user_id": "suspicious_user",
                "event_type": "login",
                "metadata": {
                    "login_attempts": 5,
                    "user_agent": "bot crawler"
                }
            }
            
            score, flags = calculate_enhanced_score(payload)
            
            assert score < 50  # Should be suspicious
            assert len(flags) > 0

def test_risk_level_classification():
    """Test risk level classification"""
    from bse import get_risk_level
    
    assert get_risk_level(25) == "suspicious"
    assert get_risk_level(65) == "normal" 
    assert get_risk_level(90) == "highly_trusted"

def test_main_processing_pipeline_with_bot_detection():
    """Test the complete processing pipeline with bot detection (NEW)"""
    with patch('bse.supabase') as mock_supabase:
        with patch('bse.send_score_to_api', return_value=True):
            with patch('bse.FingerprintJSDetector.analyze_visitor') as mock_fingerprint:
                mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
                    data={"created_at": "2025-01-01T00:00:00Z", "behavior_score": 80}
                )
                mock_supabase.table().select().eq().gte().execute.return_value = MagicMock(data=[])
                mock_supabase.table().upsert().execute.return_value = MagicMock(data=[{"id": "test_user"}])
                mock_supabase.table().insert().execute.return_value = MagicMock(data=[])
                
                # Mock bot detection
                mock_fingerprint.return_value = {
                    "bot_probability": 0.3,
                    "confidence": 0.9,
                    "bot_signals": ["low_confidence"],
                    "visitor_id": "fp_test_123"
                }
                
                from bse import main_processing_pipeline
                
                payload = {
                    "source_type": "user_activity",
                    "event_type": "page_view",
                    "user_id": "test_user",
                    "session_duration": 120,
                    "fingerprint_id": "fp_test_123"
                }
                
                result = main_processing_pipeline(payload)
                
                assert result["processed"] == True
                assert result["user_id"] == "test_user"
                assert "behavior_score" in result
                assert result["api_sent"] == True
                assert result["bot_detection_enabled"] == True
                assert "bot_analysis" in result

def test_main_processing_pipeline_fake_referral():
    """Test the complete processing pipeline with fake referral detection (NEW)"""
    with patch('bse.supabase') as mock_supabase:
        with patch('bse.send_score_to_api', return_value=True):
            with patch('bse.FakeReferralDetector.analyze_referral') as mock_fake_referral:
                mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
                    data={"created_at": "2025-01-01T00:00:00Z", "behavior_score": 80}
                )
                mock_supabase.table().select().eq().gte().execute.return_value = MagicMock(data=[])
                mock_supabase.table().upsert().execute.return_value = MagicMock(data=[{"id": "test_user"}])
                mock_supabase.table().insert().execute.return_value = MagicMock(data=[])
                
                # Mock fake referral detection
                mock_fake_referral.return_value = {
                    "is_fake_referral": True,
                    "fake_signals": ["same_ip_referral"],
                    "risk_score": 30
                }
                
                from bse import main_processing_pipeline
                
                payload = {
                    "source_type": "referral",
                    "user_id": "referrer_user",
                    "referred_user_id": "referred_user",
                    "referral_code": "REF123",
                    "ip_address": "192.168.1.100"
                }
                
                result = main_processing_pipeline(payload)
                
                assert result["processed"] == True
                assert result["user_id"] == "referrer_user"
                assert "behavior_score" in result
                # Score should be lower due to fake referral penalty
                assert result["behavior_score"] < 70
                assert "fake_referral_same_ip" in result["risk_flags"]
