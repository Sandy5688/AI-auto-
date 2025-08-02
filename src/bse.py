import os
import logging
from datetime import datetime, timezone
from supabase import create_client
from dotenv import load_dotenv

# Standardized path - load from config/.env
load_dotenv("config/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Validate environment variables
if not all([SUPABASE_URL, SUPABASE_KEY, WEBHOOK_URL]):
    raise ValueError("SUPABASE_URL, SUPABASE_KEY, and WEBHOOK_URL must be set in config/.env")

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define known IPs for fake referral detection
known_ips = ["192.168.1.1"]

def calculate_score(payload):
    score = 100
    risk_flags = []
    try:
        md = payload.get("metadata", {})
        evt = payload.get("event_type", "")

        if evt == "login" and md.get("login_count", 0) > 10:
            score -= 10
            risk_flags.append("frequent_logins")

        if evt == "referral" and md.get("ip") in known_ips and not md.get("activity", True):
            score -= 20
            risk_flags.append("fake_referral")

        if evt == "click" and md.get("click_rate", 0) > 30:
            score -= 15
            risk_flags.append("rapid_clicks")

    except Exception as e:
        logger.error(f"Exception in calculate_score: {e}")
    return max(score, 0), risk_flags

def send_score_to_webhook(user_id, score, risk_flags):
    import requests
    payload = {
        "user_id": user_id,
        "behavior_score": score,
        "risk_flags": risk_flags,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            logger.info(f"Score sent to webhook for user {user_id}")
        else:
            logger.warning(f"Failed to send score for user {user_id}: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"Exception in send_score_to_webhook: {e}")

if __name__ == "__main__":
    # Example/test payloads
    payloads = [
        {
            "event_type": "login",
            "user_id": "abc123",
            "timestamp": "2025-07-25T00:00:00Z",
            "metadata": {
                "login_count": 12,
                "ip": "192.168.1.1",
                "activity": True,
                "click_rate": 25
            }
        },
        {
            "event_type": "referral",
            "user_id": "abc124",
            "timestamp": "2025-07-25T00:01:00Z",
            "metadata": {
                "login_count": 2,
                "ip": "192.168.1.1",
                "activity": False,
                "click_rate": 5
            }
        },
        {
            "event_type": "click",
            "user_id": "abc125",
            "timestamp": "2025-07-25T00:02:00Z",
            "metadata": {
                "login_count": 1,
                "ip": "192.168.1.3",
                "activity": True,
                "click_rate": 35
            }
        }
    ]

    for p in payloads:
        score, flags = calculate_score(p)
        logger.info(f"User {p['user_id']} scored {score} with flags {flags}")
        send_score_to_webhook(p["user_id"], score, flags)
