import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from bse import calculate_score

def test_calculate_score_login_high():
    payload = {
        "event_type": "login",
        "metadata": {"login_count": 12}
    }
    score, flags = calculate_score(payload)
    assert score < 100
    assert "frequent_logins" in flags

def test_calculate_score_bad_payload():
    score, flags = calculate_score({})
    assert score == 100
    assert flags == []

# Add more edge and valid cases as needed.
