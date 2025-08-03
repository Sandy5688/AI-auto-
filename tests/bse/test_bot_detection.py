#!/usr/bin/env python3
import sys
import os
import pytest
import requests  # ADD THIS LINE
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


# Mock environment
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "BOT_DETECTION_ENABLED": "true",
    "FINGERPRINTJS_API_KEY": "test_fingerprint_key",
    "IPHUB_API_KEY": "test_iphub_key",
    "FINGERPRINT_CONFIDENCE_THRESHOLD": "0.8"
})

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

def test_fingerprintjs_bot_detection_high_confidence():
    """Test FingerprintJS with high bot confidence"""
    from bse import FingerprintJSDetector
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "visits": [{
                "incognito": False,
                "browserDetails": {"bot": True},
                "confidence": {"score": 0.95},
                "ip": {"datacenter": False}
            }]
        }
        mock_get.return_value = mock_response
        
        result = FingerprintJSDetector.analyze_visitor("test_visitor")
        
        assert result["bot_probability"] == 0.8  # Only browser bot flag
        assert "browser_bot_flag" in result["bot_signals"]
        assert result["confidence"] == 0.95

def test_fingerprintjs_multiple_bot_signals():
    """Test FingerprintJS with multiple bot signals"""
    from bse import FingerprintJSDetector
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "visits": [{
                "incognito": True,
                "browserDetails": {"bot": True},
                "confidence": {"score": 0.5},  # Low confidence
                "ip": {"datacenter": True}
            }]
        }
        mock_get.return_value = mock_response
        
        result = FingerprintJSDetector.analyze_visitor("test_visitor")
        
        # Should have all signals: incognito + bot + low_confidence + datacenter
        expected_probability = 0.2 + 0.8 + 0.3 + 0.4  # Capped at 1.0
        assert result["bot_probability"] == 1.0
        assert len(result["bot_signals"]) == 4

def test_fingerprintjs_api_error():
    """Test FingerprintJS API error handling"""
    from bse import FingerprintJSDetector
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 429  # Rate limited
        mock_response.text = "Rate limit exceeded"
        mock_get.return_value = mock_response
        
        result = FingerprintJSDetector.analyze_visitor("test_visitor")
        
        assert result["bot_probability"] == 0.5  # Default on error
        assert "error" in result
        assert "api_error_429" in result["error"]

def test_fingerprintjs_timeout():
    """Test FingerprintJS timeout handling"""
    from bse import FingerprintJSDetector
    
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result = FingerprintJSDetector.analyze_visitor("test_visitor")
        
        assert result["bot_probability"] == 0.5
        assert result["error"] == "timeout"

def test_iphub_commercial_vpn():
    """Test IPHub commercial VPN detection"""
    from bse import IPHubDetector
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "block": 1,  # Commercial VPN
            "countryCode": "US",
            "isp": "Example VPN Provider"
        }
        mock_get.return_value = mock_response
        
        result = IPHubDetector.check_ip("203.0.113.100")
        
        assert result["is_blacklisted"] == True
        assert result["block_type"] == 1
        assert result["isp"] == "Example VPN Provider"

def test_iphub_hosting_provider():
    """Test IPHub hosting provider detection"""
    from bse import IPHubDetector
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "block": 2,  # Hosting Provider
            "countryCode": "DE",
            "isp": "Example Hosting"
        }
        mock_get.return_value = mock_response
        
        result = IPHubDetector.check_ip("203.0.113.200")
        
        assert result["is_blacklisted"] == True
        assert result["block_type"] == 2

def test_iphub_clean_ip():
    """Test IPHub with clean IP"""
    from bse import IPHubDetector
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "block": 0,  # Clean IP
            "countryCode": "US",
            "isp": "Example ISP"
        }
        mock_get.return_value = mock_response
        
        result = IPHubDetector.check_ip("203.0.113.50")
        
        assert result["is_blacklisted"] == False
        assert result["block_type"] == 0

def test_bot_detection_integration():
    """Test bot detection integration in payload processing"""
    from bse import PayloadProcessor
    
    processor = PayloadProcessor()
    
    with patch('bse.FingerprintJSDetector.analyze_visitor') as mock_fingerprint:
        mock_fingerprint.return_value = {
            "bot_probability": 0.9,
            "confidence": 0.95,
            "bot_signals": ["browser_bot_flag"],
            "visitor_id": "test_visitor"
        }
        
        payload = {
            "source_type": "user_activity",
            "event_type": "page_view",
            "user_id": "test_user",
            "fingerprint_id": "test_visitor",
            "ip_address": "203.0.113.100"
        }
        
        result = processor.process_payload(payload)
        
        assert "bot_analysis" in result["metadata"]
        assert result["metadata"]["bot_analysis"]["fingerprint"]["bot_probability"] == 0.9
        assert "browser_bot_flag" in result["metadata"]["bot_detection_flags"]

def test_bot_detection_scoring_penalties():
    """Test bot detection penalties in scoring"""
    from bse import calculate_enhanced_score
    
    with patch('bse.get_user_context', return_value={"account_age_days": 30}):
        with patch('bse.get_recent_user_activity', return_value=[]):
            payload = {
                "user_id": "bot_user",
                "event_type": "login",
                "metadata": {
                    "bot_analysis": {
                        "fingerprint": {"bot_probability": 0.9},
                        "iphub": {"is_blacklisted": True, "block_type": 2}
                    },
                    "bot_detection_flags": ["browser_bot_flag", "hosting_provider_ip"]
                }
            }
            
            score, flags = calculate_enhanced_score(payload)
            
            # Should have severe penalties
            assert score < 40
            assert "high_bot_probability" in flags
            assert "browser_detected_bot" in flags
            assert "hosting_provider_ip" in flags

if __name__ == "__main__":
    print("🤖 Running Bot Detection Tests")
    pytest.main([__file__, "-v"])
