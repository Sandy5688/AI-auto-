import os
import time
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from supabase import create_client
from dotenv import load_dotenv

# Try importing audit_logger (safe fallback if not available)
try:
    import audit_logger
except ImportError:
    audit_logger = None

# Load environment variables
load_dotenv("config/.env")

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Webhook / API settings
BSE_WEBHOOK_URL = os.getenv("BSE_WEBHOOK_URL", "http://localhost:5001/webhook")
WEBHOOK_MAX_RETRIES = int(os.getenv("WEBHOOK_MAX_RETRIES", 3))
WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", 5))
WEBHOOK_RETRY_DELAY = int(os.getenv("WEBHOOK_RETRY_DELAY", 2))
WEBHOOK_EXPONENTIAL_BACKOFF = os.getenv("WEBHOOK_EXPONENTIAL_BACKOFF", "true").lower() == "true"

# Bot detection settings
BOT_DETECTION_ENABLED = os.getenv("BOT_DETECTION_ENABLED", "false").lower() == "true"
FINGERPRINTJS_API_KEY = os.getenv("FINGERPRINTJS_API_KEY")
IPHUB_API_KEY = os.getenv("IPHUB_API_KEY")

# Score ranges
SCORE_RANGES = {
    "suspicious": (0, 40),
    "normal": (41, 70),
    "highly_trusted": (71, 100),
}

# -----------------------------
# (KEEP all your scoring functions as-is, only adjusted supabase/audit_logger safety)
# -----------------------------

def calculate_enhanced_score(payload: Dict[str, Any]) -> tuple[int, List[str]]:
    """Main scoring logic with bot detection, referral fraud, event rules, etc."""
    user_id = payload.get("user_id", "unknown")
    event_type = payload.get("event_type", "unknown")
    metadata = payload.get("metadata", {})
    base_score = 100
    risk_flags = []

    logger.info(f"🧮 Calculating enhanced score for user {user_id}, event: {event_type}")

    try:
        # Get user context
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
            base_score += 5

        # --- BOT DETECTION LOGIC (unchanged from your code) ---
        bot_analysis = metadata.get("bot_analysis", {})
        fingerprint_data = bot_analysis.get("fingerprint", {})
        bot_probability = fingerprint_data.get("bot_probability", 0.0)

        if bot_probability > 0.8:
            base_score -= 40
            risk_flags.append("high_bot_probability")
        elif bot_probability > 0.6:
            base_score -= 25
            risk_flags.append("medium_bot_probability")
        elif bot_probability > 0.4:
            base_score -= 10
            risk_flags.append("low_bot_probability")

        # ... [KEEP ALL YOUR OTHER SCORING RULES FROM THE ORIGINAL FILE HERE] ...

        final_score = max(0, min(100, base_score))
        risk_level = get_risk_level(final_score)

        logger.info(f"📊 Score calculated for {user_id}: {final_score}/100 ({risk_level})")

        # Audit logging (safe check)
        if audit_logger:
            audit_logger.log_user_scoring(
                user_id=payload.get("user_id"),
                old_score=get_current_user_score(payload.get("user_id")),
                new_score=final_score,
                flags=risk_flags,
                reason="BSE_calculation",
                source="enhanced_bse"
            )

        return final_score, risk_flags

    except Exception as e:
        logger.error(f"💥 Error calculating score for user {user_id}: {e}")
        return 50, ["calculation_error"]


# -----------------------------
# (KEEP ALL your helper functions exactly as before:
#  - score_login_activity
#  - score_meme_activity
#  - score_social_activity
#  - score_referral_activity
#  - score_form_activity
#  - analyze_behavioral_patterns
#  - analyze_device_patterns
#  - check_activity_velocity
#  - get_user_context
#  - get_recent_user_activity
#  - get_risk_level
#  - send_score_to_api
#  - main_processing_pipeline
#  - store_risk_flags
#  - update_user_score
# -----------------------------

if __name__ == "__main__":
    logger.info("🚀 Enhanced BSE - Multi-Source Behavioral Scoring Engine with Bot Detection")
    logger.info(f"🤖 Bot Detection: {'Enabled' if BOT_DETECTION_ENABLED else 'Disabled'}")
    logger.info(f"🔍 FingerprintJS: {'Configured' if FINGERPRINTJS_API_KEY else 'Not Configured'}")
    logger.info(f"🛡️ IPHub: {'Configured' if IPHUB_API_KEY else 'Not Configured'}")

    example_payloads = [
        {"source_type": "referral", "user_id": "user_123"},
        {"source_type": "login", "user_id": "user_456"},
    ]

    for i, payload in enumerate(example_payloads, 1):
        logger.info(f"\n--- Processing Example {i} ---")
        result = main_processing_pipeline(payload)
        logger.info(f"Result: {result}")
