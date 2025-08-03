import os
import logging
import requests
import time

from datetime import datetime, timedelta, timezone  

from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from supabase import create_client

# Load environment configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, "config", ".env")
load_dotenv(env_path)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BSE_WEBHOOK_URL = "https://api.memefihub.com/ai/bse/score-update"  # Client's endpoint

# Webhook retry configuration
WEBHOOK_MAX_RETRIES = 3
WEBHOOK_RETRY_DELAY = 2
WEBHOOK_EXPONENTIAL_BACKOFF = True
WEBHOOK_TIMEOUT = 30

# Scoring thresholds
SCORE_RANGES = {
    "suspicious": (0, 49),
    "normal": (50, 79), 
    "highly_trusted": (80, 100)
}

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class PayloadProcessor:
    """Multi-source payload processor for different data types"""
    
    def __init__(self):
        self.source_handlers = {
            "user_activity": self.handle_user_activity,
            "supabase_event": self.handle_supabase_event, 
            "frontend_form": self.handle_frontend_form,
            "login": self.handle_login_activity,
            "meme_upload": self.handle_meme_upload,
            "social_interaction": self.handle_social_interaction,
            "referral": self.handle_referral_activity
        }
    
    def process_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming payload based on source type
        
        Returns:
            Dict with processed data ready for scoring
        """
        try:
            source_type = payload.get("source_type", "unknown")
            event_type = payload.get("event_type", "generic")
            
            logger.info(f"📥 Processing {source_type} payload: {event_type}")
            
            # Route to appropriate handler
            handler = self.source_handlers.get(source_type, self.handle_generic_payload)
            processed_data = handler(payload)
            
            logger.info(f"✅ Payload processed successfully for user: {processed_data.get('user_id')}")
            return processed_data
            
        except Exception as e:
            logger.error(f"💥 Error processing payload: {e}")
            return self.create_error_response(payload, str(e))
    
    def handle_user_activity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user activity logs"""
        return {
            "user_id": payload.get("user_id"),
            "event_type": payload.get("event_type", "activity"),
            "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metadata": {
                "session_duration": payload.get("session_duration", 0),
                "actions_per_minute": payload.get("actions_per_minute", 1),
                "user_agent": payload.get("user_agent", ""),
                "ip_address": payload.get("ip_address", ""),
                "device_info": payload.get("device_info", {}),
                "activity_type": payload.get("activity_type", "general")
            }
        }
    
    def handle_supabase_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Supabase database events"""
        return {
            "user_id": payload.get("record", {}).get("user_id") or payload.get("user_id"),
            "event_type": payload.get("type", "database_event"),
            "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metadata": {
                "table": payload.get("table"),
                "operation": payload.get("type"),  # INSERT, UPDATE, DELETE
                "old_record": payload.get("old_record", {}),
                "record": payload.get("record", {}),
                "schema": payload.get("schema", "public")
            }
        }
    
    def handle_frontend_form(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle frontend form submissions"""
        return {
            "user_id": payload.get("user_id"),
            "event_type": "form_submission",
            "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metadata": {
                "form_type": payload.get("form_type"),
                "fields_filled": len(payload.get("form_data", {})),
                "submission_time": payload.get("submission_time", 0),
                "validation_errors": payload.get("validation_errors", []),
                "page_url": payload.get("page_url", ""),
                "referrer": payload.get("referrer", ""),
                "form_data": payload.get("form_data", {})  # Sanitized data
            }
        }
    
    def handle_login_activity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle login-specific activities"""
        return {
            "user_id": payload.get("user_id"),
            "event_type": "login",
            "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metadata": {
                "login_method": payload.get("login_method", "email"),
                "login_success": payload.get("success", True),
                "login_attempts": payload.get("attempts", 1),
                "ip_address": payload.get("ip_address", ""),
                "user_agent": payload.get("user_agent", ""),
                "location": payload.get("location", {}),
                "device_fingerprint": payload.get("device_fingerprint", ""),
                "session_id": payload.get("session_id", "")
            }
        }
    
    def handle_meme_upload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle meme upload activities"""
        return {
            "user_id": payload.get("user_id"),
            "event_type": "meme_upload",
            "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metadata": {
                "meme_id": payload.get("meme_id"),
                "file_size": payload.get("file_size", 0),
                "content_type": payload.get("content_type", ""),
                "upload_duration": payload.get("upload_duration", 0),
                "tags": payload.get("tags", []),
                "ai_generated": payload.get("ai_generated", False),
                "content_moderation": payload.get("content_moderation", {}),
                "quality_score": payload.get("quality_score", 0)
            }
        }
    
    def handle_social_interaction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle social interactions (likes, shares, comments)"""
        return {
            "user_id": payload.get("user_id"),
            "event_type": "social_interaction",
            "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metadata": {
                "interaction_type": payload.get("interaction_type"),  # like, share, comment
                "target_id": payload.get("target_id"),  # meme_id or user_id
                "target_type": payload.get("target_type"),  # meme, user, post
                "interaction_value": payload.get("value", 1),  # +1 for like, -1 for dislike
                "content_length": payload.get("content_length", 0),  # for comments
                "interaction_speed": payload.get("interaction_speed", 0)  # time on page before interaction
            }
        }
    
    def handle_referral_activity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle referral program activities"""
        return {
            "user_id": payload.get("user_id"),
            "event_type": "referral",
            "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metadata": {
                "referral_code": payload.get("referral_code"),
                "referred_user_id": payload.get("referred_user_id"),
                "referral_source": payload.get("source", ""),
                "campaign_id": payload.get("campaign_id"),
                "conversion_type": payload.get("conversion_type"),  # signup, first_purchase, etc.
                "reward_amount": payload.get("reward_amount", 0),
                "referrer_reward": payload.get("referrer_reward", 0)
            }
        }
    
    def handle_generic_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback handler for unknown payload types"""
        logger.warning(f"⚠️ Unknown payload source: {payload.get('source_type')}")
        return {
            "user_id": payload.get("user_id", "unknown"),
            "event_type": payload.get("event_type", "generic"),
            "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metadata": payload.get("metadata", payload)  # Use entire payload as metadata
        }
    
    def create_error_response(self, payload: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "user_id": payload.get("user_id", "unknown"),
            "event_type": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "error": error,
                "original_payload": payload
            }
        }

def calculate_enhanced_score(payload: Dict[str, Any]) -> tuple[int, List[str]]:
    """
    Enhanced rule-based scoring logic with multiple factors
    
    Returns:
        tuple: (score, risk_flags)
    """
    base_score = 100
    risk_flags = []
    user_id = payload.get("user_id")
    event_type = payload.get("event_type", "unknown")
    metadata = payload.get("metadata", {})
    
    logger.info(f"🧮 Calculating enhanced score for user {user_id}, event: {event_type}")
    
    try:
        # Get user history for contextual scoring
        user_context = get_user_context(user_id)
        account_age_days = user_context.get("account_age_days", 0)
        
        # RULE 1: Account Age Factor
        if account_age_days < 1:
            base_score -= 20
            risk_flags.append("new_account")
        elif account_age_days < 7:
            base_score -= 10
            risk_flags.append("recent_account")
        elif account_age_days > 365:
            base_score += 5  # Bonus for established accounts
        
        # RULE 2: Event-Specific Scoring
        if event_type == "login":
            score_adjustment, flags = score_login_activity(metadata, user_context)
            base_score += score_adjustment
            risk_flags.extend(flags)
        
        elif event_type == "meme_upload":
            score_adjustment, flags = score_meme_activity(metadata, user_context)
            base_score += score_adjustment
            risk_flags.extend(flags)
        
        elif event_type == "social_interaction":
            score_adjustment, flags = score_social_activity(metadata, user_context)
            base_score += score_adjustment
            risk_flags.extend(flags)
        
        elif event_type == "referral":
            score_adjustment, flags = score_referral_activity(metadata, user_context)
            base_score += score_adjustment
            risk_flags.extend(flags)
        
        elif event_type == "form_submission":
            score_adjustment, flags = score_form_activity(metadata, user_context)
            base_score += score_adjustment
            risk_flags.extend(flags)
        
        # RULE 3: Behavioral Patterns
        behavioral_adjustment, behavioral_flags = analyze_behavioral_patterns(user_id, event_type, metadata)
        base_score += behavioral_adjustment
        risk_flags.extend(behavioral_flags)
        
        # RULE 4: IP and Device Analysis
        device_adjustment, device_flags = analyze_device_patterns(metadata, user_context)
        base_score += device_adjustment
        risk_flags.extend(device_flags)
        
        # RULE 5: Velocity Checks
        velocity_adjustment, velocity_flags = check_activity_velocity(user_id, event_type, metadata)
        base_score += velocity_adjustment
        risk_flags.extend(velocity_flags)
        
        # Ensure score is within bounds
        final_score = max(0, min(100, base_score))
        
        # Determine risk level
        risk_level = get_risk_level(final_score)
        
        logger.info(f"📊 Score calculated for {user_id}: {final_score}/100 ({risk_level}) - Flags: {len(risk_flags)}")
        return final_score, risk_flags
        
    except Exception as e:
        logger.error(f"💥 Error calculating score for user {user_id}: {e}")
        return 50, ["calculation_error"]  # Default to neutral score

def score_login_activity(metadata: Dict[str, Any], user_context: Dict[str, Any]) -> tuple[int, List[str]]:
    """Score login-specific activities"""
    adjustment = 0
    flags = []
    
    # Multiple failed attempts
    attempts = metadata.get("login_attempts", 1)
    if attempts > 3:
        adjustment -= 15
        flags.append("multiple_login_attempts")
    elif attempts > 1:
        adjustment -= 5
        flags.append("retry_login")
    
    # Unusual location
    if metadata.get("location", {}) and user_context.get("usual_locations"):
        # Implementation for location anomaly detection
        pass
    
    # Device fingerprint analysis
    device_fingerprint = metadata.get("device_fingerprint")
    if device_fingerprint and device_fingerprint not in user_context.get("known_devices", []):
        adjustment -= 10
        flags.append("new_device")
    
    # Time-based analysis
    login_hour = datetime.fromisoformat(metadata.get("timestamp", "")).hour if metadata.get("timestamp") else 12
    if login_hour < 6 or login_hour > 23:  # Unusual hours
        adjustment -= 5
        flags.append("unusual_login_time")
    
    return adjustment, flags

def score_meme_activity(metadata: Dict[str, Any], user_context: Dict[str, Any]) -> tuple[int, List[str]]:
    """Score meme upload activities"""
    adjustment = 0
    flags = []
    
    # File size analysis
    file_size = metadata.get("file_size", 0)
    if file_size > 10_000_000:  # Very large files
        adjustment -= 5
        flags.append("large_file_upload")
    elif file_size < 1000:  # Suspiciously small files
        adjustment -= 5
        flags.append("tiny_file_upload")
    
    # Upload frequency
    daily_uploads = user_context.get("uploads_today", 0)
    if daily_uploads > 50:
        adjustment -= 20
        flags.append("excessive_uploads")
    elif daily_uploads > 20:
        adjustment -= 10
        flags.append("high_upload_frequency")
    
    # Content quality
    quality_score = metadata.get("quality_score", 50)
    if quality_score < 30:
        adjustment -= 10
        flags.append("low_quality_content")
    elif quality_score > 80:
        adjustment += 5
    
    # AI-generated content
    if metadata.get("ai_generated", False):
        adjustment += 2  # Bonus for using the service properly
    
    return adjustment, flags

def score_social_activity(metadata: Dict[str, Any], user_context: Dict[str, Any]) -> tuple[int, List[str]]:
    """Score social interactions"""
    adjustment = 0
    flags = []
    
    interaction_type = metadata.get("interaction_type")
    interaction_speed = metadata.get("interaction_speed", 5)  # seconds
    
    # Very fast interactions (bot-like)
    if interaction_speed < 1:
        adjustment -= 15
        flags.append("rapid_interactions")
    elif interaction_speed < 3:
        adjustment -= 8
        flags.append("fast_interactions")
    
    # Interaction patterns
    daily_interactions = user_context.get("interactions_today", 0)
    if daily_interactions > 1000:
        adjustment -= 25
        flags.append("excessive_interactions")
    elif daily_interactions > 100:
        adjustment -= 10
        flags.append("high_interaction_frequency")
    
    # Content engagement quality
    if interaction_type == "comment":
        content_length = metadata.get("content_length", 0)
        if content_length < 5:
            adjustment -= 5
            flags.append("low_effort_comment")
        elif content_length > 500:
            adjustment += 3  # Thoughtful engagement
    
    return adjustment, flags

def score_referral_activity(metadata: Dict[str, Any], user_context: Dict[str, Any]) -> tuple[int, List[str]]:
    """Score referral activities"""
    adjustment = 0
    flags = []
    
    # Daily referral limits
    daily_referrals = user_context.get("referrals_today", 0)
    if daily_referrals > 50:
        adjustment -= 30
        flags.append("excessive_referrals")
    elif daily_referrals > 10:
        adjustment -= 15
        flags.append("high_referral_frequency")
    
    # Referral source analysis
    referral_source = metadata.get("referral_source", "")
    if "bot" in referral_source.lower() or "automated" in referral_source.lower():
        adjustment -= 20
        flags.append("automated_referral")
    
    # Reward amount analysis
    reward_amount = metadata.get("reward_amount", 0)
    if reward_amount > user_context.get("average_reward", 0) * 3:
        adjustment -= 10
        flags.append("unusual_reward_amount")
    
    return adjustment, flags

def score_form_activity(metadata: Dict[str, Any], user_context: Dict[str, Any]) -> tuple[int, List[str]]:
    """Score form submissions"""
    adjustment = 0
    flags = []
    
    # Submission speed analysis
    submission_time = metadata.get("submission_time", 30)  # seconds
    fields_filled = metadata.get("fields_filled", 1)
    
    if submission_time < 5 and fields_filled > 3:
        adjustment -= 15
        flags.append("rapid_form_submission")
    elif submission_time < 10 and fields_filled > 5:
        adjustment -= 8
        flags.append("fast_form_submission")
    
    # Validation errors
    validation_errors = metadata.get("validation_errors", [])
    if len(validation_errors) > 5:
        adjustment -= 10
        flags.append("multiple_validation_errors")
    
    return adjustment, flags

def analyze_behavioral_patterns(user_id: str, event_type: str, metadata: Dict[str, Any]) -> tuple[int, List[str]]:
    """Analyze user behavioral patterns"""
    adjustment = 0
    flags = []
    
    try:
        # Get recent activity patterns
        recent_activity = get_recent_user_activity(user_id, hours=24)
        
        # Check for repetitive behavior
        if len(recent_activity) > 100:  # Very active user
            event_types = [activity.get("event_type") for activity in recent_activity]
            most_common_event = max(set(event_types), key=event_types.count)
            
            if event_types.count(most_common_event) / len(event_types) > 0.8:
                adjustment -= 15
                flags.append("repetitive_behavior_pattern")
        
        # Check for activity clustering
        timestamps = [activity.get("timestamp") for activity in recent_activity]
        if len(timestamps) > 10:
            # Simple clustering check - if too many activities in short bursts
            time_gaps = []
            for i in range(1, len(timestamps)):
                gap = (datetime.fromisoformat(timestamps[i].replace("Z", "+00:00")) - 
                      datetime.fromisoformat(timestamps[i-1].replace("Z", "+00:00"))).total_seconds()
                time_gaps.append(gap)
            
            avg_gap = sum(time_gaps) / len(time_gaps) if time_gaps else 0
            if avg_gap < 30:  # Less than 30 seconds between activities on average
                adjustment -= 20
                flags.append("activity_clustering")
    
    except Exception as e:
        logger.warning(f"Error analyzing behavioral patterns for {user_id}: {e}")
    
    return adjustment, flags

def analyze_device_patterns(metadata: Dict[str, Any], user_context: Dict[str, Any]) -> tuple[int, List[str]]:
    """Analyze device and IP patterns"""
    adjustment = 0
    flags = []
    
    ip_address = metadata.get("ip_address", "")
    user_agent = metadata.get("user_agent", "")
    
    # IP analysis
    if ip_address:
        # Check against known VPN/Proxy ranges (simplified)
        suspicious_ip_prefixes = ["10.0.", "192.168.", "172.16.", "127.0."]
        if any(ip_address.startswith(prefix) for prefix in suspicious_ip_prefixes):
            adjustment -= 5
            flags.append("private_ip_range")
    
    # User agent analysis
    if user_agent:
        if "bot" in user_agent.lower() or "crawler" in user_agent.lower():
            adjustment -= 25
            flags.append("bot_user_agent")
        elif len(user_agent) < 50:
            adjustment -= 10
            flags.append("suspicious_user_agent")
    
    return adjustment, flags

def check_activity_velocity(user_id: str, event_type: str, metadata: Dict[str, Any]) -> tuple[int, List[str]]:
    """Check activity velocity patterns"""
    adjustment = 0
    flags = []
    
    try:
        # Get recent activity for velocity check
        recent_activity = get_recent_user_activity(user_id, hours=1)
        
        # Count events of same type in last hour
        same_type_count = sum(1 for activity in recent_activity 
                             if activity.get("event_type") == event_type)
        
        # Define velocity thresholds per event type
        velocity_thresholds = {
            "login": 10,
            "meme_upload": 20,
            "social_interaction": 100,
            "referral": 5,
            "form_submission": 15
        }
        
        threshold = velocity_thresholds.get(event_type, 50)
        
        if same_type_count > threshold * 2:
            adjustment -= 25
            flags.append("extreme_velocity")
        elif same_type_count > threshold:
            adjustment -= 15
            flags.append("high_velocity")
        
    except Exception as e:
        logger.warning(f"Error checking velocity for {user_id}: {e}")
    
    return adjustment, flags

def get_user_context(user_id: str) -> Dict[str, Any]:
    """Get user context for scoring"""
    try:
        # Get user data
        user_resp = supabase.table("users").select("*").eq("id", user_id).single().execute()
        user_data = user_resp.data or {}
        
        # Calculate account age
        created_at = user_data.get("created_at")
        account_age_days = 0
        if created_at:
            created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            account_age_days = (datetime.now(timezone.utc) - created_date).days
        
        # Get recent activity counts
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Count today's activities by type
        activity_counts = {}
        recent_activity = get_recent_user_activity(user_id, hours=24)
        
        for activity in recent_activity:
            event_type = activity.get("event_type", "unknown")
            activity_counts[f"{event_type}s_today"] = activity_counts.get(f"{event_type}s_today", 0) + 1
        
        return {
            "account_age_days": account_age_days,
            "behavior_score": user_data.get("behavior_score", 100),
            "known_devices": [],  # Could be populated from device history
            "usual_locations": [],  # Could be populated from location history
            "average_reward": 10,  # Could be calculated from historical data
            **activity_counts
        }
        
    except Exception as e:
        logger.error(f"Error getting user context for {user_id}: {e}")
        return {"account_age_days": 0}

def get_recent_user_activity(user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
    """Get recent user activity from multiple sources"""
    try:
        since_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        activities = []
        
        # Get from user_risk_flags
        flags_resp = supabase.table("user_risk_flags").select("*").eq("user_id", user_id).gte("timestamp", since_time).execute()
        for flag in (flags_resp.data or []):
            activities.append({
                "event_type": "risk_flag",
                "timestamp": flag.get("timestamp"),
                "metadata": {"flag": flag.get("flag")}
            })
        
        # Get from generated_memes
        memes_resp = supabase.table("generated_memes").select("*").eq("user_id", user_id).gte("timestamp", since_time).execute()
        for meme in (memes_resp.data or []):
            activities.append({
                "event_type": "meme_upload",
                "timestamp": meme.get("timestamp"),
                "metadata": {"prompt": meme.get("prompt"), "tone": meme.get("tone")}
            })
        
        return activities
        
    except Exception as e:
        logger.error(f"Error getting recent activity for {user_id}: {e}")
        return []

def get_risk_level(score: int) -> str:
    """Get risk level based on score"""
    if SCORE_RANGES["suspicious"][0] <= score <= SCORE_RANGES["suspicious"][1]:
        return "suspicious"
    elif SCORE_RANGES["normal"][0] <= score <= SCORE_RANGES["normal"][1]:
        return "normal"
    elif SCORE_RANGES["highly_trusted"][0] <= score <= SCORE_RANGES["highly_trusted"][1]:
        return "highly_trusted"
    else:
        return "unknown"

def send_score_to_api(user_id: str, score: int, risk_flags: List[str], 
                      event_data: Dict[str, Any], timestamp: str = None) -> bool:
    """
    Send final score to client's API endpoint with retry logic
    """
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    
    risk_level = get_risk_level(score)
    
    payload = {
        "user_id": user_id,
        "behavior_score": score,
        "risk_level": risk_level,
        "risk_flags": risk_flags,
        "timestamp": timestamp,
        "event_data": {
            "event_type": event_data.get("event_type"),
            "source_type": event_data.get("source_type"),
            "processed_at": datetime.now(timezone.utc).isoformat()
        },
        "score_breakdown": {
            "base_score": 100,
            "adjustments": score - 100,
            "flag_count": len(risk_flags)
        }
    }
    
    # Retry logic with exponential backoff
    for attempt in range(1, WEBHOOK_MAX_RETRIES + 1):
        try:
            logger.info(f"📡 Sending score to API (attempt {attempt}/{WEBHOOK_MAX_RETRIES}): {user_id} = {score}")
            
            response = requests.post(
                BSE_WEBHOOK_URL,
                json=payload,
                timeout=WEBHOOK_TIMEOUT,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'BSE-ScoreEngine/1.0',
                    'X-BSE-Version': '1.0.0'
                }
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Score sent successfully for {user_id}: {score} ({risk_level})")
                return True
            elif response.status_code in [429, 502, 503, 504]:
                logger.warning(f"⚠️ API returned retriable error {response.status_code}: {response.text}")
                raise requests.exceptions.HTTPError(f"HTTP {response.status_code}")
            else:
                logger.error(f"❌ API returned non-retriable error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.warning(f"⏰ API timeout on attempt {attempt}")
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"🔌 API connection error on attempt {attempt}: {e}")
        except Exception as e:
            logger.error(f"💥 Unexpected error on attempt {attempt}: {e}")
        
        if attempt < WEBHOOK_MAX_RETRIES:
            delay = WEBHOOK_RETRY_DELAY * (2 ** (attempt - 1)) if WEBHOOK_EXPONENTIAL_BACKOFF else WEBHOOK_RETRY_DELAY
            logger.info(f"⏳ Retrying API call in {delay} seconds...")
            time.sleep(delay)
    
    logger.error(f"💥 Failed to send score after {WEBHOOK_MAX_RETRIES} attempts")
    return False

def main_processing_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main processing pipeline for incoming payloads
    """
    try:
        # Step 1: Process payload based on source
        processor = PayloadProcessor()
        processed_data = processor.process_payload(payload)
        
        user_id = processed_data.get("user_id")
        if not user_id or user_id == "unknown":
            logger.error("❌ Cannot process payload without valid user_id")
            return {"error": "Invalid user_id", "processed": False}
        
        # Step 2: Calculate behavior score
        score, risk_flags = calculate_enhanced_score(processed_data)
        
        # Step 3: Store risk flags if any
        if risk_flags:
            store_risk_flags(user_id, risk_flags, processed_data.get("timestamp"))
        
        # Step 4: Update user score in database
        update_user_score(user_id, score)
        
        # Step 5: Send to client API
        api_success = send_score_to_api(user_id, score, risk_flags, processed_data, processed_data.get("timestamp"))
        
        result = {
            "user_id": user_id,
            "behavior_score": score,
            "risk_level": get_risk_level(score),
            "risk_flags": risk_flags,
            "api_sent": api_success,
            "processed": True,
            "timestamp": processed_data.get("timestamp")
        }
        
        logger.info(f"🎯 Processing complete for {user_id}: {score}/100 ({get_risk_level(score)})")
        return result
        
    except Exception as e:
        logger.error(f"💥 Pipeline processing failed: {e}")
        return {"error": str(e), "processed": False}

def store_risk_flags(user_id: str, risk_flags: List[str], timestamp: str):
    """Store risk flags in database"""
    try:
        for flag in risk_flags:
            flag_entry = {
                "user_id": user_id,
                "flag": flag,
                "timestamp": timestamp,
                "metadata": {"auto_generated": True}
            }
            supabase.table("user_risk_flags").insert(flag_entry).execute()
        
        logger.info(f"💾 Stored {len(risk_flags)} risk flags for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to store risk flags for {user_id}: {e}")

def update_user_score(user_id: str, score: int):
    """Update user's behavior score in database"""
    try:
        supabase.table("users").upsert({
            "id": user_id,
            "behavior_score": score,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        logger.info(f"💾 Updated score for user {user_id}: {score}")
        
    except Exception as e:
        logger.error(f"❌ Failed to update score for {user_id}: {e}")

if __name__ == "__main__":
    # Example usage with different payload types
    logger.info("🚀 Enhanced BSE - Multi-Source Behavioral Scoring Engine")
    
    # Example payloads for different sources
    example_payloads = [
        {
            "source_type": "user_activity",
            "event_type": "page_view",
            "user_id": "user_123",
            "session_duration": 120,
            "actions_per_minute": 5,
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        {
            "source_type": "login",
            "user_id": "user_456", 
            "login_method": "email",
            "success": True,
            "attempts": 1,
            "ip_address": "203.0.113.1",
            "location": {"country": "US", "city": "New York"}
        },
        {
            "source_type": "meme_upload",
            "user_id": "user_789",
            "meme_id": "meme_001",
            "file_size": 2048576,
            "content_type": "image/jpeg", 
            "ai_generated": True,
            "quality_score": 85
        }
    ]
    
    # Process example payloads
    for i, payload in enumerate(example_payloads, 1):
        logger.info(f"\n--- Processing Example {i} ---")
        result = main_processing_pipeline(payload)
        logger.info(f"Result: {result}")
