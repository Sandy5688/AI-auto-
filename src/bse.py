import requests
from datetime import datetime, timezone

def calculate_score(payload):
    score = 100  # Start with a perfect score
    # Rule 1: Frequent logins (>10/day)
    if payload['event_type'] == 'login' and payload['metadata']['login_count'] > 10:
        score -= 10
    # Rule 2: Fake referrals (known IP, no activity)
    if payload['event_type'] == 'referral' and payload['metadata']['ip'] in known_ips and not payload['metadata']['activity']:
        score -= 20
    # Rule 3: Rapid clicks (>30/minute)
    if payload['event_type'] == 'click' and payload['metadata']['click_rate'] > 30:
        score -= 15
    return max(score, 0)  # Ensure score stays non-negative

# Webhook URL (replace with your actual Bubble.io endpoint or a test URL)
WEBHOOK_URL = "http://localhost:5001/webhook"

def send_score_to_webhook(user_id, score, risk_flags):
    payload = {
        "user_id": user_id,
        "behavior_score": score,
        "risk_flags": risk_flags,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code == 200:
        print("Score sent to webhook successfully")
    else:
        print(f"Failed to send score: {response.status_code}")

# Add globally
score_cache = {}
def calculate_score(payload):
    key = payload['user_id']
    if key not in score_cache:
        score = 100  # Your logic...
        if payload['event_type'] == 'login' and payload['metadata']['login_count'] > 10:
            score -= 10
        if payload['event_type'] == 'referral' and payload['metadata']['ip'] in known_ips and not payload['metadata']['activity']:
            score -= 20
        if payload['event_type'] == 'click' and payload['metadata']['click_rate'] > 30:
            score -= 15
        score_cache[key] = max(score, 0)
    return score_cache[key]

# Placeholder for known IPs
known_ips = ["192.168.1.1"]

# Sample payload
sample_payload = {
  "event_type": "login",
  "user_id": "testuser",
  "timestamp": "2025-07-10T01:00:00Z",
  "metadata": {
    "login_count": 12,
    "ip": "192.168.1.1",
    "activity": True,
    "click_rate": 25
  }
}

# Additional test payloads
normal_login = {
    "event_type": "login",
    "user_id": "abc124",
    "timestamp": "2025-07-14T01:00:00Z",
    "metadata": {
        "login_count": 5,  # Normal behavior
        "ip": "192.168.1.2",
        "activity": True,
        "click_rate": 10
    }
}
fake_referral = {
    "event_type": "referral",
    "user_id": "abc125",
    "timestamp": "2025-07-14T01:00:00Z",
    "metadata": {
        "login_count": 1,
        "ip": "192.168.1.1",  # Known IP
        "activity": False,  # No activity
        "click_rate": 5
    }
}
rapid_clicks = {
    "event_type": "click",
    "user_id": "abc126",
    "timestamp": "2025-07-14T01:00:00Z",
    "metadata": {
        "login_count": 1,
        "ip": "192.168.1.3",
        "activity": True,
        "click_rate": 35  # High click rate
    }
}

# Test all payloads
payloads = [sample_payload, normal_login, fake_referral, rapid_clicks]
for payload in payloads:
    score = calculate_score(payload)
    print(f"Score for {payload['user_id']}: {score}")
    send_score_to_webhook(payload['user_id'], score, [])