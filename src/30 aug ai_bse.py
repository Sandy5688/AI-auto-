
# ------------------------------
# Behavioral Scoring Engine (BSE) with Bot Detection
# ------------------------------

import os
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from supabase import create_client, Client

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BSE_WEBHOOK_URL = os.getenv("BSE_WEBHOOK_URL", "http://localhost:8000/score")
WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "10"))
WEBHOOK_MAX_RETRIES = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))
WEBHOOK_RETRY_DELAY = int(os.getenv("WEBHOOK_RETRY_DELAY", "5"))
WEBHOOK_EXPONENTIAL_BACKOFF = os.getenv("WEBHOOK_EXPONENTIAL_BACKOFF", "true").lower() == "true"

BOT_DETECTION_ENABLED = os.getenv("BOT_DETECTION_ENABLED", "true").lower() == "true"
FINGERPRINTJS_API_KEY = os.getenv("FINGERPRINTJS_API_KEY")
IPHUB_API_KEY = os.getenv("IPHUB_API_KEY")

SCORE_RANGES = {
    "suspicious": (0, 49),
    "normal": (50, 79),
    "highly_trusted": (80, 100)
}

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bse")

# Connect Supabase
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")

# ------------------------------
# Core Scoring Functions
# ------------------------------

def calculate_enhanced_score(payload: Dict[str, Any]) -> tuple[int, List[str]]:
    """Calculate enhanced score for a given user payload."""
    user_id = payload.get("user_id")
    event_type = payload.get("event_type", "unknown")
    metadata = payload.get("metadata", {})

    base_score = 100
    risk_flags: List[str] = []

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
            base_score += 5

        # Bot Detection Penalties
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

        bot_flags = metadata.get("bot_detection_flags", [])
        for flag in bot_flags:
            if flag == "browser_bot_flag":
                base_score -= 35
                risk_flags.append("browser_detected_bot")
            elif flag == "datacenter_ip":
                base_score -= 20
                risk_flags.append("datacenter_ip_usage")
            elif flag == "blacklisted_ip":
                base_score -= 30
                risk_flags.append("blacklisted_ip_detected")
            elif flag in ["low_confidence", "incognito_mode"]:
                base_score -= 10
                risk_flags.append(f"bot_signal_{flag}")

        iphub_data = bot_analysis.get("iphub", {})
        if iphub_data.get("is_blacklisted", False):
            block_type = iphub_data.get("block_type", 0)
            if block_type == 1:
                base_score -= 25
                risk_flags.append("commercial_vpn")
            elif block_type == 2:
                base_score -= 30
                risk_flags.append("hosting_provider_ip")

        # Fake Referral Penalties
        fake_referral_analysis = metadata.get("fake_referral_analysis", {})
        if fake_referral_analysis.get("is_fake_referral", False):
            fake_signals = fake_referral_analysis.get("fake_signals", [])
            for signal in fake_signals:
                if signal == "same_ip_referral":
                    base_score -= 35
                    risk_flags.append("fake_referral_same_ip")
                elif signal == "excessive_ip_referrals":
                    base_score -= 30
                    risk_flags.append("fake_referral_ip_abuse")
                elif signal == "inactive_referred_user":
                    base_score -= 25
                    risk_flags.append("fake_referral_inactive_user")
                elif signal == "rapid_referrals":
                    base_score -= 20
                    risk_flags.append("fake_referral_velocity")

        # Event-specific scoring (delegated functions)
        if event_type == "login":
            adjustment, flags = score_login_activity(metadata, user_context)
        elif event_type == "meme_upload":
            adjustment, flags = score_meme_activity(metadata, user_context)
        elif event_type == "social_interaction":
            adjustment, flags = score_social_activity(metadata, user_context)
        elif event_type == "referral":
            adjustment, flags = score_referral_activity(metadata, user_context)
        elif event_type == "form_submission":
            adjustment, flags = score_form_activity(metadata, user_context)
        else:
            adjustment, flags = (0, [])

        base_score += adjustment
        risk_flags.extend(flags)

        # Behavioral, device, velocity analysis
        b_adj, b_flags = analyze_behavioral_patterns(user_id, event_type, metadata)
        base_score += b_adj
        risk_flags.extend(b_flags)

        d_adj, d_flags = analyze_device_patterns(metadata, user_context)
        base_score += d_adj
        risk_flags.extend(d_flags)

        v_adj, v_flags = check_activity_velocity(user_id, event_type, metadata)
        base_score += v_adj
        risk_flags.extend(v_flags)

        # Bound score
        final_score = max(0, min(100, base_score))
        risk_level = get_risk_level(final_score)

        logger.info(f"📊 Score calculated for {user_id}: {final_score}/100 ({risk_level}) - Flags: {risk_flags}")
        return final_score, risk_flags

    except Exception as e:
        logger.error(f"💥 Error calculating score for user {user_id}: {e}")
        return 50, ["calculation_error"]

# ------------------------------
# Additional Functions (shortened)
# ------------------------------
# [NOTE: Here you'd include the helper functions: score_login_activity, score_meme_activity, etc.
#  For brevity I won't paste the whole thing again unless you want full file output.]
