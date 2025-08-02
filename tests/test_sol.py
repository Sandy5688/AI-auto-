import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Mock environment
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "TESTING_MODE": "1"
})

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

def test_calculate_behavior_score():
    """Test behavior score calculation with real logic"""
    import sol
    
    user_data = {
        "id": "test_user",
        "behavior_score": 80,
        "is_verified": True,
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    with patch.object(sol, 'get_recent_risk_flags', return_value=[]):
        with patch.object(sol, 'get_user_recent_activity', return_value=[{"activity": "login"}]):
            with patch.object(sol, 'supabase') as mock_supabase:
                mock_supabase.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])
                
                score = sol.calculate_behavior_score(user_data)
                
                assert isinstance(score, int)
                assert 0 <= score <= 100

def test_retry_operation_success():
    """Test retry operation succeeds on first attempt"""
    import sol
    
    def mock_operation():
        return "success"
    
    result = sol.retry_operation(mock_operation, "test_operation")
    assert result == True

def test_retry_operation_failure_then_success():
    """Test retry operation succeeds after failures"""
    import sol
    
    attempt_count = 0
    def mock_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise Exception("Temporary failure")
        return "success"
    
    with patch('sol.time.sleep'):  # Skip actual sleep in tests
        result = sol.retry_operation(mock_operation, "test_operation")
        assert result == True
        assert attempt_count == 2

def test_retry_operation_all_failures():
    """Test retry operation fails after all attempts"""
    import sol
    
    def mock_operation():
        raise Exception("Persistent failure")
    
    with patch('sol.time.sleep'):
        with patch.object(sol, 'send_failure_alert'):
            result = sol.retry_operation(mock_operation, "test_operation")
            assert result == False

def test_analyze_flag_patterns():
    """Test flag pattern analysis"""
    import sol
    
    flags = [
        {"flag": "rapid_clicks", "user_id": "user1"},
        {"flag": "rapid_clicks", "user_id": "user2"},
        {"flag": "bot_like_velocity", "user_id": "user1"},
    ]
    
    analysis = sol.analyze_flag_patterns(flags)
    
    assert analysis["total_flags"] == 3
    assert analysis["flag_types"]["rapid_clicks"] == 2
    assert analysis["flag_types"]["bot_like_velocity"] == 1
    assert analysis["user_flag_counts"]["user1"] == 2
    assert analysis["user_flag_counts"]["user2"] == 1

def test_detect_anomalies():
    """Test anomaly detection"""
    import sol
    
    analysis = {
        "total_flags": 60,  # Above threshold
        "flag_types": {"rapid_clicks": 15},  # Above threshold
        "user_flag_counts": {"user1": 8}  # Above threshold
    }
    
    anomalies = sol.detect_anomalies(analysis)
    
    assert len(anomalies) == 3  # Should detect all three types
    anomaly_types = [a["type"] for a in anomalies]
    assert "flag_spike" in anomaly_types
    assert "excessive_user_flags" in anomaly_types
    assert "high_flag_volume" in anomaly_types
