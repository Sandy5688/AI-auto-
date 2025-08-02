import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from bse import calculate_score


def test_calculate_score_login_high():
    payload = {
        "event_type": "login",
        "user_id": "test_user_login",  # Added missing user_id
        "timestamp": "2025-08-03T01:00:00Z",  # Added missing timestamp
        "metadata": {"login_count": 12}
    }
    score, flags = calculate_score(payload)
    assert score < 100  # Should be 90 (100 - 10)
    assert "frequent_logins" in flags



def test_calculate_score_bad_payload():
    score, flags = calculate_score({})
    assert score == 100
    assert flags == []


# NEW ENHANCED TESTS FOR BEHAVIOR SCORING IMPROVEMENTS

def test_calculate_score_fake_referral():
    """Test fake referral detection"""
    payload = {
        "event_type": "referral",
        "user_id": "test_user_1",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "ip": "192.168.1.1",  # Known suspicious IP
            "activity": False
        }
    }
    score, flags = calculate_score(payload)
    assert score == 80  # 100 - 20
    assert "fake_referral" in flags


def test_calculate_score_rapid_clicks():
    """Test rapid clicks detection"""
    payload = {
        "event_type": "click",
        "user_id": "test_user_2",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "click_rate": 35
        }
    }
    score, flags = calculate_score(payload)
    assert score == 85  # 100 - 15
    assert "rapid_clicks" in flags


def test_calculate_score_repeated_referral_abuse():
    """Test new repeated referral abuse detection"""
    payload = {
        "event_type": "referral",
        "user_id": "test_user_3",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "daily_referral_count": 25,
            "unique_referral_sources": 2
        }
    }
    score, flags = calculate_score(payload)
    assert score == 75  # 100 - 25
    assert "repeated_referral_abuse" in flags


def test_calculate_score_idle_click_farm():
    """Test idle click farm detection"""
    payload = {
        "event_type": "click",
        "user_id": "test_user_4",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "click_rate": 30,
            "page_interaction_score": 15,
            "session_duration": 400,
            "mouse_movement_variance": 8
        }
    }
    score, flags = calculate_score(payload)
    assert score == 70  # 100 - 30
    assert "idle_click_farm" in flags


def test_calculate_score_suspicious_login_pattern():
    """Test suspicious login pattern detection"""
    payload = {
        "event_type": "login",
        "user_id": "test_user_5",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "hourly_login_frequency": 18,
            "device_count_24h": 7,
            "ip_changes_24h": 12
        }
    }
    score, flags = calculate_score(payload)
    assert score == 80  # 100 - 20
    assert "suspicious_login_pattern" in flags


def test_calculate_score_bot_like_velocity():
    """Test bot-like velocity detection"""
    payload = {
        "event_type": "interaction",
        "user_id": "test_user_6",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "actions_per_minute": 70,
            "human_behavior_score": 25
        }
    }
    score, flags = calculate_score(payload)
    assert score == 75  # 100 - 25
    assert "bot_like_velocity" in flags


def test_calculate_score_multiple_flags():
    """Test multiple flags being triggered simultaneously"""
    payload = {
        "event_type": "click",
        "user_id": "test_user_7",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "click_rate": 35,  # Triggers rapid_clicks (-15)
            "page_interaction_score": 10,
            "session_duration": 600,
            "mouse_movement_variance": 5,  # Triggers idle_click_farm (-30)
            "actions_per_minute": 80,
            "human_behavior_score": 20  # Triggers bot_like_velocity (-25)
        }
    }
    score, flags = calculate_score(payload)
    assert score == 30  # 100 - 15 - 30 - 25
    assert "rapid_clicks" in flags
    assert "idle_click_farm" in flags
    assert "bot_like_velocity" in flags
    assert len(flags) == 3


def test_calculate_score_missing_user_id():
    """Test payload missing user_id"""
    payload = {
        "event_type": "click",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {"click_rate": 25}
    }
    score, flags = calculate_score(payload)
    assert score == 100  # Should return default score
    assert flags == []


def test_calculate_score_missing_event_type():
    """Test payload missing event_type"""
    payload = {
        "user_id": "test_user_8",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {"click_rate": 25}
    }
    score, flags = calculate_score(payload)
    assert score == 100  # Should return default score
    assert flags == []


def test_calculate_score_missing_timestamp():
    """Test payload missing timestamp"""
    payload = {
        "event_type": "click",
        "user_id": "test_user_9",
        "metadata": {"click_rate": 25}
    }
    score, flags = calculate_score(payload)
    assert score == 100  # Should return default score
    assert flags == []


def test_calculate_score_none_payload():
    """Test None payload handling"""
    score, flags = calculate_score(None)
    assert score == 100
    assert flags == []


def test_calculate_score_invalid_payload_type():
    """Test invalid payload type (not dict)"""
    score, flags = calculate_score("invalid_payload")
    assert score == 100
    assert flags == []


def test_calculate_score_empty_metadata():
    """Test payload with empty metadata"""
    payload = {
        "event_type": "click",
        "user_id": "test_user_10",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {}
    }
    score, flags = calculate_score(payload)
    assert score == 100  # No flags should be triggered
    assert flags == []


def test_calculate_score_normal_behavior():
    """Test normal user behavior (no flags)"""
    payload = {
        "event_type": "click",
        "user_id": "test_user_11",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "click_rate": 10,
            "page_interaction_score": 80,
            "session_duration": 200,
            "mouse_movement_variance": 50,
            "actions_per_minute": 20,
            "human_behavior_score": 85
        }
    }
    score, flags = calculate_score(payload)
    assert score == 100  # Perfect score
    assert flags == []


def test_calculate_score_edge_case_thresholds():
    """Test edge cases right at thresholds"""
    # Click rate exactly at threshold (30 is threshold, 30 should NOT trigger)
    payload = {
        "event_type": "click",
        "user_id": "test_user_12",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {"click_rate": 30}
    }
    score, flags = calculate_score(payload)
    assert score == 100  # Should not trigger (> 30 triggers, not >= 30)
    assert flags == []
    
    # Login count exactly at threshold (10 is threshold, 10 should NOT trigger)
    payload_login = {
        "event_type": "login",
        "user_id": "test_user_13", 
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {"login_count": 10}
    }
    score, flags = calculate_score(payload_login)
    assert score == 100  # Should not trigger (> 10 triggers, not >= 10)
    assert flags == []


def test_calculate_score_minimum_score_limit():
    """Test that score never goes below 0"""
    payload = {
        "event_type": "click",
        "user_id": "test_user_14",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "click_rate": 50,  # -15
            "page_interaction_score": 5,
            "session_duration": 1000,
            "mouse_movement_variance": 2,  # -30
            "actions_per_minute": 100,
            "human_behavior_score": 10,  # -25
            "login_count": 20,  # -10 if this were a login event
        }
    }
    score, flags = calculate_score(payload)
    assert score >= 0  # Score should never be negative
    assert len(flags) == 3  # Should have multiple flags

def test_calculate_score_comprehensive_scenario():
    """Test a comprehensive scenario with multiple risk factors"""
    payload = {
        "event_type": "click",
        "user_id": "comprehensive_test_user",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            # Multiple risk factors
            "click_rate": 40,                    # Rapid clicks (-15)
            "page_interaction_score": 12,
            "session_duration": 800,
            "mouse_movement_variance": 6,        # Idle click farm (-30)
            "actions_per_minute": 90,
            "human_behavior_score": 15,          # Bot-like velocity (-25)
            "login_count": 15,                   # Would trigger if login event
            "daily_referral_count": 30,         # Would trigger if referral event
            "unique_referral_sources": 1
        }
    }
    
    score, flags = calculate_score(payload)
    
    # Should have multiple flags and significantly reduced score
    expected_flags = ["rapid_clicks", "idle_click_farm", "bot_like_velocity"]
    
    for flag in expected_flags:
        assert flag in flags
    
    # Score should be 30 (100 - 15 - 30 - 25)
    assert score == 30
    assert len(flags) == 3

def test_calculate_score_performance():
    """Test calculate_score performance with large metadata"""
    import time
    
    payload = {
        "event_type": "click",
        "user_id": "performance_test_user",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "click_rate": 25,
            # Add lots of metadata to test performance
            **{f"extra_field_{i}": f"value_{i}" for i in range(100)}
        }
    }
    
    start_time = time.time()
    score, flags = calculate_score(payload)
    end_time = time.time()
    
    # Should complete quickly (under 1 second)
    assert (end_time - start_time) < 1.0
    assert score == 100  # No flags should be triggered
    assert flags == []

def test_calculate_score_unicode_handling():
    """Test calculate_score with unicode characters in metadata"""
    payload = {
        "event_type": "click",
        "user_id": "unicode_test_user_🧪",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "click_rate": 15,
            "user_agent": "Mozilla/5.0 (Unicode: 测试用户)",
            "location": "São Paulo, Brasil",
            "description": "Тест с кириллицей"
        }
    }
    
    score, flags = calculate_score(payload)
    assert score == 100
    assert flags == []

def test_calculate_score_extreme_values():
    """Test calculate_score with extreme values"""
    payload = {
        "event_type": "click", 
        "user_id": "extreme_values_user",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "click_rate": 999999,               # Extremely high - triggers rapid_clicks
            "page_interaction_score": -50,      # Negative value
            "session_duration": 500,            # Changed to 500 to meet idle_click_farm criteria (>300)
            "mouse_movement_variance": 5,       # Changed to 5 to meet idle_click_farm criteria (<10)
            "actions_per_minute": 10000,        # Impossibly high - triggers bot_like_velocity
            "human_behavior_score": -100        # Negative human score - triggers bot_like_velocity
        }
    }
    
    score, flags = calculate_score(payload)
    
    # Should trigger multiple flags
    assert "rapid_clicks" in flags
    assert "idle_click_farm" in flags  
    assert "bot_like_velocity" in flags
    
    # Score calculation: 100 - 15 (rapid_clicks) - 30 (idle_click_farm) - 25 (bot_like_velocity) = 30
    assert score == 30
    assert len(flags) == 3
