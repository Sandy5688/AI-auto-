import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Mock environment
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "TESTING_MODE": "1"
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
        "user_agent": "Mozilla/5.0 Test Browser"
    }
    
    result = processor.process_payload(payload)
    
    assert result["user_id"] == "test_user"
    assert result["event_type"] == "page_view"
    assert result["metadata"]["session_duration"] == 300
    assert result["metadata"]["actions_per_minute"] == 5

def test_payload_processor_login_activity():
    """Test PayloadProcessor with login payload"""
    from bse import PayloadProcessor
    
    processor = PayloadProcessor()
    payload = {
        "source_type": "login",
        "user_id": "test_user",
        "login_method": "email",
        "success": True,
        "attempts": 1,
        "ip_address": "203.0.113.1"
    }
    
    result = processor.process_payload(payload)
    
    assert result["user_id"] == "test_user"
    assert result["event_type"] == "login"
    assert result["metadata"]["login_method"] == "email"
    assert result["metadata"]["login_success"] == True

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

def test_main_processing_pipeline():
    """Test the complete processing pipeline"""
    with patch('bse.supabase') as mock_supabase:
        with patch('bse.send_score_to_api', return_value=True):
            mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
                data={"created_at": "2025-01-01T00:00:00Z", "behavior_score": 80}
            )
            mock_supabase.table().select().eq().gte().execute.return_value = MagicMock(data=[])
            mock_supabase.table().upsert().execute.return_value = MagicMock(data=[{"id": "test_user"}])
            mock_supabase.table().insert().execute.return_value = MagicMock(data=[])
            
            from bse import main_processing_pipeline
            
            payload = {
                "source_type": "user_activity",
                "event_type": "page_view",
                "user_id": "test_user",
                "session_duration": 120
            }
            
            result = main_processing_pipeline(payload)
            
            assert result["processed"] == True
            assert result["user_id"] == "test_user"
            assert "behavior_score" in result
            assert result["api_sent"] == True
