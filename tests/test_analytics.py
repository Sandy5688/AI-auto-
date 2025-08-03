import sys
import os
import pytest
from datetime import datetime
import pandas as pd

# Mock environment for testing
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "TESTING_MODE": "1"
})

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from analytics.analytics import safe_parse_timestamp, prepare_chart_data, format_chart_labels

def test_safe_parse_timestamp_valid():
    """Test timestamp parsing with valid formats"""
    valid_timestamps = [
        "2025-08-03T01:00:00Z",
        "2025-08-03T01:00:00.123Z",
        "2025-08-03 01:00:00",
        "2025-08-03"
    ]
    
    for ts in valid_timestamps:
        result = safe_parse_timestamp(ts)
        assert result is not None
        assert isinstance(result, pd.Timestamp)

def test_safe_parse_timestamp_invalid():
    """Test timestamp parsing with invalid formats"""
    invalid_timestamps = [
        "invalid-date",
        "2025-13-45T25:70:80Z",  # Invalid date/time
        "",
        None,
        "not-a-timestamp"
    ]
    
    for ts in invalid_timestamps:
        result = safe_parse_timestamp(ts)
        assert result is None

def test_prepare_chart_data_empty():
    """Test chart data preparation with empty input"""
    empty_data = {"scores": [], "flags": []}
    result = prepare_chart_data(empty_data)
    
    assert "score_dist" in result
    assert "flag_trends" in result
    assert result["score_dist"] == {}
    assert result["flag_trends"] == {}

def test_prepare_chart_data_invalid_timestamps():
    """Test chart data preparation with invalid timestamps"""
    data_with_bad_timestamps = {
        "scores": [{"behavior_score": 85}, {"behavior_score": 90}],
        "flags": [
            {"user_id": "user1", "flag": "test_flag", "timestamp": "invalid-timestamp"},
            {"user_id": "user2", "flag": "test_flag", "timestamp": "2025-13-45T25:70:80Z"}
        ]
    }
    
    result = prepare_chart_data(data_with_bad_timestamps)
    
    # Should still process scores successfully
    assert len(result["score_dist"]) == 2
    # Should handle invalid timestamps gracefully
    assert result["flag_trends"] == {}

def test_format_chart_labels():
    """Test that chart labels are converted to strings"""
    chart_data = {
        "score_dist": {85: 5, 90: 3, 75: 2},  # Numeric keys
        "flag_trends": {
            "timestamp": ["2025-08-01", "2025-08-02"],
            "test_flag": [1, 2]
        }
    }
    
    result = format_chart_labels(chart_data)
    
    # Check that score keys are now strings
    for key in result["score_dist"].keys():
        assert isinstance(key, str)
    
    # Check that original values are preserved
    assert result["score_dist"]["85"] == 5
    assert result["score_dist"]["90"] == 3

def test_prepare_chart_data_mixed_timestamps():
    """Test chart data with mix of valid and invalid timestamps"""
    data = {
        "scores": [{"behavior_score": 85}],
        "flags": [
            {"user_id": "user1", "flag": "good_flag", "timestamp": "2025-08-03T01:00:00Z"},
            {"user_id": "user2", "flag": "bad_flag", "timestamp": "invalid"},
            {"user_id": "user3", "flag": "good_flag", "timestamp": "2025-08-04T01:00:00Z"}
        ]
    }
    
    result = prepare_chart_data(data)
    
    # Should process valid timestamps and skip invalid ones
    assert result["score_dist"] == {85: 1}
    # Should have some flag trend data from valid timestamps
    if result["flag_trends"]:
        assert "timestamp" in result["flag_trends"]
