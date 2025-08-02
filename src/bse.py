import os
import logging
from datetime import datetime, timezone
from supabase import create_client
from dotenv import load_dotenv

# Dynamically find the config/.env file regardless of current working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up from src/ to project root
env_path = os.path.join(project_root, "config", ".env")

load_dotenv(env_path)

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
known_ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]  # Add more suspicious IPs

def check_duplicate_risk_flag(user_id, flag, timestamp, supabase_client=supabase):
    """
    Check if the same risk flag already exists for the user within a time window.
    Returns True if duplicate exists, False otherwise.
    """
    try:
        # Convert timestamp to datetime for comparison
        if isinstance(timestamp, str):
            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            event_time = timestamp
        
        # Check for duplicates within 5 minutes window
        time_window_start = (event_time - timezone.utc.replace(microsecond=0)).total_seconds() - 300  # 5 minutes ago
        time_window_end = (event_time - timezone.utc.replace(microsecond=0)).total_seconds() + 300   # 5 minutes ahead
        
        # Query for existing flags
        existing_flags = supabase_client.table("user_risk_flags").select("*").eq("user_id", user_id).eq("flag", flag).execute()
        
        if existing_flags.data:
            for existing_flag in existing_flags.data:
                existing_time = datetime.fromisoformat(existing_flag["timestamp"].replace("Z", "+00:00"))
                time_diff = abs((event_time - existing_time).total_seconds())
                
                if time_diff <= 300:  # Within 5 minutes
                    logger.info(f"Duplicate risk flag detected for user {user_id}: {flag} within {time_diff}s")
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking duplicate risk flag: {e}")
        return False

def store_risk_flags(user_id, risk_flags, timestamp, supabase_client=supabase):
    """
    Store risk flags in database, preventing duplicates.
    """
    stored_flags = []
    
    for flag in risk_flags:
        if not check_duplicate_risk_flag(user_id, flag, timestamp, supabase_client):
            try:
                flag_entry = {
                    "user_id": user_id,
                    "flag": flag,
                    "timestamp": timestamp if isinstance(timestamp, str) else timestamp.isoformat().replace("+00:00", "Z")
                }
                supabase_client.table("user_risk_flags").insert(flag_entry).execute()
                stored_flags.append(flag)
                logger.info(f"Risk flag stored: {flag} for user {user_id}")
            except Exception as e:
                logger.error(f"Error storing risk flag {flag} for user {user_id}: {e}")
        else:
            logger.info(f"Skipped duplicate risk flag: {flag} for user {user_id}")
    
    return stored_flags

def calculate_score(payload):
    """
    Enhanced behavior score calculation with expanded fake behavior detection
    and proper payload validation.
    """
    score = 100
    risk_flags = []
    
    # Validate payload structure
    if not payload:
        logger.warning("Empty payload received in calculate_score()")
        return score, risk_flags
    
    if not isinstance(payload, dict):
        logger.warning(f"Invalid payload type: {type(payload)}. Expected dict.")
        return score, risk_flags
    
    try:
        user_id = payload.get("user_id")
        md = payload.get("metadata", {})
        evt = payload.get("event_type", "")
        timestamp = payload.get("timestamp")
        
        # Log missing critical fields
        missing_fields = []
        if not user_id:
            missing_fields.append("user_id")
        if not evt:
            missing_fields.append("event_type")
        if not timestamp:
            missing_fields.append("timestamp")
            
        if missing_fields:
            logger.warning(f"Payload missing critical fields: {missing_fields}. Payload: {payload}")
            return score, risk_flags
        
        # Existing detection rules
        if evt == "login" and md.get("login_count", 0) > 10:
            score -= 10
            risk_flags.append("frequent_logins")
            logger.info(f"Frequent logins detected for user {user_id}: {md.get('login_count')} logins")

        if evt == "referral" and md.get("ip") in known_ips and not md.get("activity", True):
            score -= 20
            risk_flags.append("fake_referral")
            logger.info(f"Fake referral detected for user {user_id} from IP {md.get('ip')}")

        if evt == "click" and md.get("click_rate", 0) > 30:
            score -= 15
            risk_flags.append("rapid_clicks")
            logger.info(f"Rapid clicks detected for user {user_id}: {md.get('click_rate')} clicks/min")

        # NEW ENHANCED DETECTION RULES
        
        # 1. Repeated referral link usage
        if evt == "referral":
            referral_count = md.get("daily_referral_count", 0)
            unique_referrals = md.get("unique_referral_sources", 1)
            
            if referral_count > 20 and unique_referrals < 3:
                score -= 25
                risk_flags.append("repeated_referral_abuse")
                logger.info(f"Repeated referral abuse detected for user {user_id}: {referral_count} referrals from {unique_referrals} sources")
        
        # 2. Idle click farms detection
        if evt == "click":
            click_rate = md.get("click_rate", 0)
            page_interaction_score = md.get("page_interaction_score", 0)  # 0-100 score
            session_duration = md.get("session_duration", 0)  # in seconds
            mouse_movement_variance = md.get("mouse_movement_variance", 0)  # variance in pixel movements
            
            # High click rate + low interaction + suspicious patterns = click farm
            if (click_rate > 25 and 
                page_interaction_score < 20 and 
                session_duration > 300 and  # More than 5 minutes
                mouse_movement_variance < 10):  # Very little mouse movement variety
                
                score -= 30
                risk_flags.append("idle_click_farm")
                logger.info(f"Idle click farm detected for user {user_id}: click_rate={click_rate}, interaction={page_interaction_score}, variance={mouse_movement_variance}")
        
        # 3. Suspicious login patterns
        if evt == "login":
            login_frequency = md.get("hourly_login_frequency", 0)
            different_devices = md.get("device_count_24h", 1)
            ip_changes = md.get("ip_changes_24h", 0)
            
            if login_frequency > 15 and different_devices > 5 and ip_changes > 10:
                score -= 20
                risk_flags.append("suspicious_login_pattern")
                logger.info(f"Suspicious login pattern for user {user_id}: {login_frequency} logins/hour from {different_devices} devices")
        
        # 4. Velocity-based detection
        if evt in ["click", "view", "interaction"]:
            action_velocity = md.get("actions_per_minute", 0)
            human_likelihood = md.get("human_behavior_score", 100)  # 0-100, higher = more human-like
            
            if action_velocity > 60 and human_likelihood < 30:
                score -= 25
                risk_flags.append("bot_like_velocity")
                logger.info(f"Bot-like velocity detected for user {user_id}: {action_velocity} actions/min, human_score={human_likelihood}")

    except Exception as e:
        logger.error(f"Exception in calculate_score for payload {payload}: {e}")
        return max(score, 0), []  # Return safe defaults on error
    
    final_score = max(score, 0)  # Ensure score doesn't go below 0
    logger.info(f"Score calculated for user {user_id}: {final_score}, flags: {risk_flags}")
    
    return final_score, risk_flags

def send_score_to_webhook(user_id, score, risk_flags, timestamp=None):
    """
    Enhanced webhook sender with better error handling and duplicate prevention.
    """
    import requests
    
    if not timestamp:
        timestamp = datetime.now(timezone.utc)
    elif isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    
    # Store risk flags in database (with duplicate prevention)
    if risk_flags:
        stored_flags = store_risk_flags(user_id, risk_flags, timestamp)
        logger.info(f"Stored {len(stored_flags)} new risk flags for user {user_id}")
    
    payload = {
        "user_id": user_id,
        "behavior_score": score,
        "risk_flags": risk_flags,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z")
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        if response.status_code == 200:
            logger.info(f"Score sent to webhook for user {user_id}")
        else:
            logger.warning(f"Failed to send score for user {user_id}: {response.status_code} {response.text}")
    except requests.exceptions.Timeout:
        logger.error(f"Webhook timeout for user {user_id}")
    except Exception as e:
        logger.error(f"Exception in send_score_to_webhook: {e}")

if __name__ == "__main__":
    # Enhanced test payloads with new detection scenarios
    payloads = [
        {
            "event_type": "login",
            "user_id": "abc123",
            "timestamp": "2025-08-03T01:00:00Z",
            "metadata": {
                "login_count": 12,
                "ip": "192.168.1.1",
                "activity": True,
                "click_rate": 25,
                "hourly_login_frequency": 20,
                "device_count_24h": 8,
                "ip_changes_24h": 15
            }
        },
        {
            "event_type": "referral",
            "user_id": "abc124",
            "timestamp": "2025-08-03T01:01:00Z",
            "metadata": {
                "ip": "192.168.1.1",
                "activity": False,
                "daily_referral_count": 50,
                "unique_referral_sources": 2
            }
        },
        {
            "event_type": "click",
            "user_id": "abc125",
            "timestamp": "2025-08-03T01:02:00Z",
            "metadata": {
                "click_rate": 35,
                "page_interaction_score": 15,
                "session_duration": 600,
                "mouse_movement_variance": 5,
                "actions_per_minute": 80,
                "human_behavior_score": 25
            }
        },
        # Test empty/invalid payloads
        {},
        None,
        {"user_id": "abc126"},  # Missing required fields
    ]

    for i, p in enumerate(payloads):
        logger.info(f"\n--- Processing payload {i+1} ---")
        if p:
            score, flags = calculate_score(p)
            logger.info(f"User {p.get('user_id', 'UNKNOWN')} scored {score} with flags {flags}")
            if p.get('user_id'):
                send_score_to_webhook(p["user_id"], score, flags, p.get("timestamp"))
        else:
            logger.info("Processing None payload")
            score, flags = calculate_score(p)
