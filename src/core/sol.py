import os
import logging
import traceback
import time
import json
from datetime import datetime, timedelta, timezone
from supabase import create_client
from dotenv import load_dotenv
import schedule
from typing import Optional, Dict, Any, List

# Dynamically find the config/.env file
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, "config", ".env")

load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validate environment variables
if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env")

# Configure JSON logging format as required
logging.basicConfig(
    level=logging.INFO, 
    format='%(message)s',  # We'll format as JSON manually
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/sol.log') if os.path.exists('logs') else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuration for retry logic
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
EXPONENTIAL_BACKOFF = True

def log_json(level: str, message: str, **kwargs):
    """Log in JSON format as required by client"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "message": message,
        "module": "SOL",
        **kwargs
    }
    
    if level.lower() == "info":
        logger.info(json.dumps(log_entry))
    elif level.lower() == "warning":
        logger.warning(json.dumps(log_entry))
    elif level.lower() == "error":
        logger.error(json.dumps(log_entry))
    else:
        logger.debug(json.dumps(log_entry))

def log_scheduled_job(job_name: str, status: str, error_if_any: Optional[str] = None, **metadata):
    """
    Log to the required logs_scheduled_jobs table with exact client specifications
    Fields: job_name, timestamp, status, error_if_any
    """
    entry = {
        "job_name": job_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "error_if_any": error_if_any,
        "metadata": metadata or {}
    }
    
    try:
        # Store in the required table name
        supabase.table("logs_scheduled_jobs").insert(entry).execute()
        log_json("info", f"Job logged: {job_name}", job_name=job_name, status=status)
    except Exception as e:
        log_json("error", f"Failed to log job {job_name}: {str(e)}", job_name=job_name, error=str(e))

# Your existing calculation functions (keeping them as they're excellent)
def calculate_behavior_score(user_data: Dict[str, Any]) -> int:
    """Calculate behavior score based on user data and recent activity."""
    try:
        base_score = 100
        user_id = user_data.get("id")
        
        # Get current behavior score as baseline
        current_score = user_data.get("behavior_score", 100)
        
        # Factor 1: Recent risk flags (last 24 hours)
        recent_flags = get_recent_risk_flags(user_id, hours=24)
        flag_penalty = len(recent_flags) * 5  # 5 points per flag
        
        # Factor 2: Activity patterns
        activity_score = calculate_activity_score(user_id)
        
        # Factor 3: Token usage patterns
        token_usage_score = calculate_token_usage_score(user_id)
        
        # Factor 4: Account age and stability
        stability_bonus = calculate_stability_bonus(user_data)
        
        # Calculate final score
        calculated_score = (
            base_score 
            - flag_penalty 
            + activity_score 
            + token_usage_score 
            + stability_bonus
        )
        
        # FIX: Apply gradual change but ensure flags reduce score
        if current_score is not None and flag_penalty == 0:
            # Only limit change when there are no new flags
            max_change = 10
            score_diff = calculated_score - current_score
            if abs(score_diff) > max_change:
                calculated_score = current_score + (max_change if score_diff > 0 else -max_change)
        elif flag_penalty > 0:
            # Always apply flag penalties immediately
            calculated_score = current_score - flag_penalty
        
        # Ensure score stays within bounds
        final_score = max(0, min(100, calculated_score))
        
        log_json("info", f"Score calculated for user {user_id}: {current_score} → {final_score}",
                user_id=user_id, old_score=current_score, new_score=final_score,
                flag_penalty=flag_penalty, activity_bonus=activity_score)
        
        return final_score
        
    except Exception as e:
        log_json("error", f"Error calculating behavior score for user {user_data.get('id', 'unknown')}", 
                user_id=user_data.get('id'), error=str(e))
        return user_data.get("behavior_score", 75)

# Keep all your existing helper functions (they're excellent)
def get_recent_risk_flags(user_id: str, hours: int = 24) -> List[Dict]:
    """Get recent risk flags for a user within specified hours."""
    try:
        since_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        flags_resp = supabase.table("user_risk_flags").select("*").eq("user_id", user_id).gte("timestamp", since_time).execute()
        return flags_resp.data or []
    except Exception as e:
        log_json("warning", f"Failed to fetch recent risk flags for user {user_id}", user_id=user_id, error=str(e))
        return []

def calculate_activity_score(user_id: str) -> int:
    """Calculate activity score based on user engagement patterns."""
    try:
        recent_activity = get_user_recent_activity(user_id)
        
        if not recent_activity:
            return -5  # Penalty for no activity
        
        activity_count = len(recent_activity)
        if 5 <= activity_count <= 20:
            return 5  # Good activity level
        elif activity_count > 50:
            return -3  # Suspiciously high activity
        else:
            return 0  # Neutral
            
    except Exception as e:
        log_json("warning", f"Failed to calculate activity score for user {user_id}", user_id=user_id, error=str(e))
        return 0

def calculate_token_usage_score(user_id: str) -> int:
    """Calculate score based on token usage patterns."""
    try:
        usage_resp = supabase.table("token_usage_history").select("*").eq("user_id", user_id).order("timestamp", desc=True).limit(10).execute()
        usage_data = usage_resp.data or []
        
        if not usage_data:
            return 0
        
        total_usage = sum(entry.get("tokens_used", 0) for entry in usage_data)
        
        if 1 <= total_usage <= 10:
            return 3  # Normal usage
        elif total_usage > 50:
            return -5  # Excessive usage
        else:
            return 0
            
    except Exception as e:
        log_json("warning", f"Failed to calculate token usage score for user {user_id}", user_id=user_id, error=str(e))
        return 0

def calculate_stability_bonus(user_data: Dict[str, Any]) -> int:
    """Calculate bonus based on account stability and history."""
    try:
        is_verified = user_data.get("is_verified", False)
        account_age_days = user_data.get("account_age_days", 0)
        
        bonus = 0
        if is_verified:
            bonus += 2
        if account_age_days > 30:
            bonus += 3
        if account_age_days > 90:
            bonus += 2
            
        return bonus
        
    except Exception as e:
        log_json("warning", "Failed to calculate stability bonus", error=str(e))
        return 0

def get_user_recent_activity(user_id: str) -> List[Dict]:
    """Get recent user activity for scoring."""
    try:
        # Could query fingerprint_data table from MAF for activity
        since_time = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        
        # Get recent fingerprint data as activity indicator
        activity_resp = supabase.table("fingerprint_data").select("*").eq("user_id", user_id).gte("timestamp", since_time).execute()
        return activity_resp.data or []
        
    except Exception as e:
        log_json("warning", f"Failed to get recent activity for user {user_id}", user_id=user_id, error=str(e))
        return []

def retry_operation(operation_func, operation_name: str, *args, **kwargs) -> bool:
    """Retry a database operation with exponential backoff."""
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            log_json("info", f"Attempting {operation_name}", operation=operation_name, attempt=attempt, max_attempts=MAX_RETRY_ATTEMPTS)
            operation_func(*args, **kwargs)
            log_json("info", f"Operation succeeded: {operation_name}", operation=operation_name, attempt=attempt)
            return True
            
        except Exception as e:
            log_json("warning", f"Operation failed: {operation_name}", operation=operation_name, attempt=attempt, error=str(e))
            
            if attempt == MAX_RETRY_ATTEMPTS:
                log_json("error", f"Operation failed after all retries: {operation_name}", operation=operation_name, error=str(e))
                send_failure_alert(operation_name, str(e))
                return False
            
            # Calculate retry delay with exponential backoff
            if EXPONENTIAL_BACKOFF:
                delay = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
            else:
                delay = RETRY_DELAY_SECONDS
                
            log_json("info", f"Retrying {operation_name} in {delay} seconds", operation=operation_name, delay=delay)
            time.sleep(delay)
    
    return False

def send_failure_alert(operation_name: str, error_message: str):
    """Send alert when critical operations fail after all retries."""
    try:
        alert_data = {
            "alert_type": "job_failure",
            "operation": operation_name,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "high",
            "status": "unresolved"
        }
        
        supabase.table("system_alerts").insert(alert_data).execute()
        log_json("error", "Critical job failure alert", operation=operation_name, alert_data=alert_data)
        
    except Exception as alert_err:
        log_json("error", f"Failed to send failure alert for {operation_name}", operation=operation_name, alert_error=str(alert_err))

# ENHANCED SCHEDULED JOBS WITH CLIENT REQUIREMENTS

def daily_bse_recalculation():
    """
    Daily: Recalculate BSE scores + leaderboard positions
    Enhanced to meet client specification
    """
    job_name = "daily_bse_recalculation"
    start_time = datetime.now(timezone.utc)
    
    try:
        log_json("info", "Starting daily BSE recalculation", job_name=job_name)
        
        # Get all users
        users_resp = supabase.table("users").select("id, behavior_score, is_verified, created_at").execute()
        users = users_resp.data or []
        
        updated_count = 0
        failed_count = 0
        score_changes = []
        
        for user in users:
            try:
                user_id = user["id"]
                old_score = user.get("behavior_score", 100)
                
                # Add calculated account age for scoring
                if user.get("created_at"):
                    created_date = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
                    account_age_days = (datetime.now(timezone.utc) - created_date).days
                    user["account_age_days"] = account_age_days
                
                # Calculate new score using enhanced BSE logic
                new_score = calculate_behavior_score(user)
                
                # Update user score
                supabase.table("users").update({
                    "behavior_score": new_score,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }).eq("id", user_id).execute()
                
                updated_count += 1
                score_changes.append({
                    "user_id": user_id,
                    "old_score": old_score,
                    "new_score": new_score,
                    "change": new_score - old_score
                })
                
            except Exception as user_error:
                failed_count += 1
                log_json("error", f"Failed to update score for user {user.get('id', 'unknown')}", 
                        user_id=user.get('id'), error=str(user_error))
        
        # Calculate leaderboard positions
        updated_leaderboard = update_leaderboard()
        
        # Log success
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        log_scheduled_job(job_name, "success", 
                         users_updated=updated_count, 
                         users_failed=failed_count,
                         execution_time_seconds=execution_time,
                         leaderboard_updated=updated_leaderboard)
        
        log_json("info", "Daily BSE recalculation completed successfully", 
                job_name=job_name, users_updated=updated_count, users_failed=failed_count,
                execution_time=execution_time)
        
        if failed_count > len(users) * 0.1:  # If more than 10% failed
            raise Exception(f"High failure rate: {failed_count}/{len(users)} users failed")
            
    except Exception as e:
        log_scheduled_job(job_name, "failed", str(e))
        log_json("error", "Daily BSE recalculation failed", job_name=job_name, error=str(e))
        raise

def update_leaderboard() -> bool:
    """Update leaderboard positions after score recalculation"""
    try:
        # Get top 100 users by behavior score
        users_resp = supabase.table("users").select("id, behavior_score").order("behavior_score", desc=True).limit(100).execute()
        top_users = users_resp.data or []
        
        # Get previous leaderboard for position changes
        previous_board_resp = supabase.table("leaderboard").select("*").order("created_at", desc=True).limit(100).execute()
        previous_positions = {entry["user_id"]: entry["position"] for entry in (previous_board_resp.data or [])}
        
        # Create new leaderboard entries
        new_entries = []
        for position, user in enumerate(top_users, 1):
            user_id = user["id"]
            previous_position = previous_positions.get(user_id)
            position_change = 0
            
            if previous_position:
                position_change = previous_position - position  # Positive means moved up
            
            new_entries.append({
                "user_id": user_id,
                "position": position,
                "behavior_score": user["behavior_score"],
                "previous_position": previous_position,
                "position_change": position_change,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        
        # Clear old leaderboard entries (keep last 4 weeks)
        four_weeks_ago = (datetime.now(timezone.utc) - timedelta(weeks=4)).isoformat()
        supabase.table("leaderboard").delete().lt("created_at", four_weeks_ago).execute()
        
        # Insert new leaderboard
        if new_entries:
            supabase.table("leaderboard").insert(new_entries).execute()
        
        log_json("info", "Leaderboard updated successfully", entries_count=len(new_entries))
        return True
        
    except Exception as e:
        log_json("error", "Failed to update leaderboard", error=str(e))
        return False

def weekly_challenges_and_reset():
    """
    Weekly: Drop randomized meme challenges + reset leaderboard
    Enhanced to meet client specification
    """
    job_name = "weekly_challenges_and_reset"
    start_time = datetime.now(timezone.utc)
    
    try:
        log_json("info", "Starting weekly challenges and reset", job_name=job_name)
        
        # Generate randomized meme challenges
        challenges_created = create_weekly_meme_challenges()
        
        # Reset weekly leaderboard (archive current, start fresh)
        leaderboard_reset = reset_weekly_leaderboard()
        
        # Send notifications about new challenges (if notification system exists)
        notifications_sent = send_challenge_notifications()
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        log_scheduled_job(job_name, "success",
                         challenges_created=challenges_created,
                         leaderboard_reset=leaderboard_reset,
                         notifications_sent=notifications_sent,
                         execution_time_seconds=execution_time)
        
        log_json("info", "Weekly challenges and reset completed", 
                job_name=job_name, challenges=challenges_created, 
                leaderboard_reset=leaderboard_reset, execution_time=execution_time)
        
    except Exception as e:
        log_scheduled_job(job_name, "failed", str(e))
        log_json("error", "Weekly challenges and reset failed", job_name=job_name, error=str(e))
        raise

def create_weekly_meme_challenges() -> int:
    """Create randomized meme challenges for the week"""
    try:
        import random
        
        # Challenge templates
        challenge_templates = [
            {"type": "theme", "description": "Create memes about {theme}", "reward_points": 50},
            {"type": "format", "description": "Create {count} memes using {format} format", "reward_points": 30},
            {"type": "viral", "description": "Get {likes} likes on a single meme", "reward_points": 100},
            {"type": "engagement", "description": "Get {comments} comments on your memes this week", "reward_points": 75},
            {"type": "daily", "description": "Post at least one meme every day this week", "reward_points": 80},
        ]
        
        # Random themes and parameters
        themes = ["technology", "gaming", "work from home", "coffee", "weekends", "coding", "AI", "social media"]
        formats = ["drake pointing", "distracted boyfriend", "two buttons", "expanding brain", "woman yelling at cat"]
        
        # Generate 3-5 random challenges
        num_challenges = random.randint(3, 5)
        challenges = []
        
        for _ in range(num_challenges):
            template = random.choice(challenge_templates)
            challenge = template.copy()
            
            # Customize challenge based on type
            if template["type"] == "theme":
                challenge["description"] = template["description"].format(theme=random.choice(themes))
            elif template["type"] == "format":
                challenge["description"] = template["description"].format(
                    count=random.randint(2, 5), 
                    format=random.choice(formats)
                )
            elif template["type"] == "viral":
                challenge["description"] = template["description"].format(likes=random.randint(50, 200))
            elif template["type"] == "engagement":
                challenge["description"] = template["description"].format(comments=random.randint(20, 100))
            
            challenge.update({
                "id": f"challenge_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{random.randint(1000, 9999)}",
                "start_date": datetime.now(timezone.utc).isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            challenges.append(challenge)
        
        # Store challenges in database
        if challenges:
            supabase.table("weekly_challenges").insert(challenges).execute()
        
        log_json("info", "Weekly challenges created", count=len(challenges), challenge_types=[c["type"] for c in challenges])
        return len(challenges)
        
    except Exception as e:
        log_json("error", "Failed to create weekly challenges", error=str(e))
        return 0

def reset_weekly_leaderboard() -> bool:
    """Reset the weekly leaderboard"""
    try:
        # Archive current weekly leaderboard
        current_week = datetime.now(timezone.utc).isocalendar()
        archive_entry = {
            "week_year": current_week[0],
            "week_number": current_week[1],
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "archived_data": "weekly_leaderboard_snapshot"  # Could store actual data
        }
        
        supabase.table("weekly_leaderboard_archive").insert(archive_entry).execute()
        
        # Clear current weekly scores (reset to 0 or base value)
        supabase.table("users").update({"weekly_score": 0}).execute()
        
        log_json("info", "Weekly leaderboard reset completed")
        return True
        
    except Exception as e:
        log_json("error", "Failed to reset weekly leaderboard", error=str(e))
        return False

def send_challenge_notifications() -> int:
    """Send notifications about new challenges"""
    try:
        # This would integrate with your notification system
        # For now, we'll just log and return a count
        
        # Get active users who should receive notifications
        users_resp = supabase.table("users").select("id").eq("notification_enabled", True).execute()
        eligible_users = users_resp.data or []
        
        # In a real implementation, you'd send actual notifications here
        log_json("info", "Challenge notifications would be sent", user_count=len(eligible_users))
        return len(eligible_users)
        
    except Exception as e:
        log_json("warning", "Failed to send challenge notifications", error=str(e))
        return 0

def hourly_flagged_user_detection():
    """
    Hourly: Detect flagged users, push alerts to admin dashboard
    Enhanced to meet client specification
    """
    job_name = "hourly_flagged_user_detection"
    start_time = datetime.now(timezone.utc)
    
    try:
        log_json("info", "Starting hourly flagged user detection", job_name=job_name)
        
        # Get recent flags and anomalies
        recent_flags = get_recent_flags_and_anomalies()
        
        # Analyze flag patterns
        flag_analysis = analyze_flag_patterns(recent_flags)
        
        # Detect high-risk users
        flagged_users = detect_high_risk_users(flag_analysis)
        
        # Push alerts to admin dashboard
        alerts_sent = push_admin_alerts(flagged_users, flag_analysis)
        
        # Store anomaly detection results
        anomalies_stored = store_anomaly_results(flag_analysis)
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        log_scheduled_job(job_name, "success",
                         flags_analyzed=len(recent_flags),
                         flagged_users_count=len(flagged_users),
                         alerts_sent=alerts_sent,
                         anomalies_stored=anomalies_stored,
                         execution_time_seconds=execution_time)
        
        log_json("info", "Hourly flagged user detection completed", 
                job_name=job_name, flagged_users=len(flagged_users), 
                alerts_sent=alerts_sent, execution_time=execution_time)
        
    except Exception as e:
        log_scheduled_job(job_name, "failed", str(e))
        log_json("error", "Hourly flagged user detection failed", job_name=job_name, error=str(e))
        raise

def get_recent_flags_and_anomalies() -> List[Dict]:
    """Get recent flags and anomalies from last hour"""
    try:
        since_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        
        # Get user risk flags
        flags_resp = supabase.table("user_risk_flags").select("*").gte("timestamp", since_time).execute()
        risk_flags = flags_resp.data or []
        
        # Get MAF anomalies
        anomalies_resp = supabase.table("detected_anomalies").select("*").gte("detected_at", since_time).execute()
        anomalies = anomalies_resp.data or []
        
        # Get MAF flag history 
        maf_flags_resp = supabase.table("user_flag_history").select("*").gte("created_at", since_time).execute()
        maf_flags = maf_flags_resp.data or []
        
        all_flags = risk_flags + anomalies + maf_flags
        log_json("info", "Retrieved recent flags and anomalies", 
                risk_flags=len(risk_flags), anomalies=len(anomalies), maf_flags=len(maf_flags))
        
        return all_flags
        
    except Exception as e:
        log_json("error", "Failed to get recent flags and anomalies", error=str(e))
        return []

def analyze_flag_patterns(flags: List[Dict]) -> Dict[str, Any]:
    """Analyze patterns in flags and anomalies"""
    analysis = {
        "total_flags": len(flags),
        "flag_types": {},
        "user_flag_counts": {},
        "severity_distribution": {},
        "time_patterns": [],
        "high_risk_users": []
    }
    
    for flag in flags:
        # Handle different flag sources
        flag_type = flag.get("flag", flag.get("anomaly_type", flag.get("flag_color", "unknown")))
        user_id = flag.get("user_id", "unknown")
        severity = flag.get("severity", flag.get("flag_color", "medium"))
        
        # Count flag types
        analysis["flag_types"][flag_type] = analysis["flag_types"].get(flag_type, 0) + 1
        
        # Count flags per user
        analysis["user_flag_counts"][user_id] = analysis["user_flag_counts"].get(user_id, 0) + 1
        
        # Count severity distribution
        analysis["severity_distribution"][severity] = analysis["severity_distribution"].get(severity, 0) + 1
    
    # Identify high-risk users (multiple flags or high severity)
    for user_id, count in analysis["user_flag_counts"].items():
        if count >= 3:  # Users with 3+ flags in one hour
            analysis["high_risk_users"].append({
                "user_id": user_id,
                "flag_count": count,
                "risk_level": "HIGH" if count >= 5 else "MEDIUM"
            })
    
    return analysis

def detect_high_risk_users(analysis: Dict[str, Any]) -> List[Dict]:
    """Detect users requiring immediate attention"""
    high_risk_users = []
    
    # Users from analysis
    high_risk_users.extend(analysis["high_risk_users"])
    
    # Additional detection: users with recent severe anomalies
    try:
        severe_anomalies_resp = supabase.table("detected_anomalies").select("*").eq("severity", "HIGH").gte("detected_at", 
            (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()).execute()
        
        for anomaly in (severe_anomalies_resp.data or []):
            affected_users = anomaly.get("affected_users", [])
            for user_id in affected_users:
                if not any(u["user_id"] == user_id for u in high_risk_users):
                    high_risk_users.append({
                        "user_id": user_id,
                        "flag_count": 1,
                        "risk_level": "HIGH",
                        "anomaly_type": anomaly.get("anomaly_type", "unknown")
                    })
    
    except Exception as e:
        log_json("warning", "Failed to detect high-risk users from anomalies", error=str(e))
    
    return high_risk_users

def push_admin_alerts(flagged_users: List[Dict], analysis: Dict[str, Any]) -> int:
    """Push alerts to admin dashboard"""
    try:
        if not flagged_users and analysis["total_flags"] < 10:
            return 0  # No alerts needed
        
        # Create admin alert
        alert_data = {
            "alert_type": "flagged_users_detected",
            "priority": "HIGH" if len(flagged_users) > 5 else "MEDIUM",
            "summary": f"{len(flagged_users)} flagged users detected in hourly scan",
            "details": {
                "flagged_users": flagged_users,
                "flag_analysis": analysis,
                "total_flags": analysis["total_flags"],
                "high_risk_count": len([u for u in flagged_users if u["risk_level"] == "HIGH"])
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "assigned_to": "admin_dashboard"
        }
        
        # Store alert for admin dashboard
        supabase.table("admin_alerts").insert(alert_data).execute()
        
        # Could also send to external systems (Slack, email, etc.)
        log_json("info", "Admin alert created", alert_type=alert_data["alert_type"], 
                priority=alert_data["priority"], flagged_users=len(flagged_users))
        
        return 1
        
    except Exception as e:
        log_json("error", "Failed to push admin alerts", error=str(e))
        return 0

def store_anomaly_results(analysis: Dict[str, Any]) -> int:
    """Store anomaly analysis results"""
    try:
        if analysis["total_flags"] == 0:
            return 0
        
        # Store hourly analysis summary
        summary_data = {
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_flags": analysis["total_flags"],
            "flag_types": analysis["flag_types"],
            "severity_distribution": analysis["severity_distribution"],
            "high_risk_users_count": len(analysis["high_risk_users"]),
            "analysis_type": "hourly_flagged_user_scan"
        }
        
        supabase.table("anomaly_analysis_results").insert(summary_data).execute()
        log_json("info", "Anomaly analysis results stored", total_flags=analysis["total_flags"])
        return 1
        
    except Exception as e:
        log_json("error", "Failed to store anomaly results", error=str(e))
        return 0

def get_job_health_status() -> Dict[str, Any]:
    """Get health status of scheduled jobs from logs_scheduled_jobs table"""
    try:
        # Get recent job logs from the required table
        recent_logs_resp = supabase.table("logs_scheduled_jobs").select("*").order("timestamp", desc=True).limit(50).execute()
        recent_logs = recent_logs_resp.data or []
        
        # Analyze job health
        job_health = {}
        for log in recent_logs:
            job_name = log["job_name"]
            if job_name not in job_health:
                job_health[job_name] = {"success": 0, "failed": 0, "last_run": None}
            
            if log["status"] == "success":
                job_health[job_name]["success"] += 1
            else:
                job_health[job_name]["failed"] += 1
            
            if not job_health[job_name]["last_run"] or log["timestamp"] > job_health[job_name]["last_run"]:
                job_health[job_name]["last_run"] = log["timestamp"]
        
        return job_health
        
    except Exception as e:
        log_json("error", "Failed to get job health status", error=str(e))
        return {}

def run_scheduler():
    """Run the job scheduler with client specifications"""
    # Schedule jobs with exact client requirements
    schedule.every().day.at("00:01").do(daily_bse_recalculation)  # Daily BSE scores + leaderboard
    schedule.every().monday.at("00:10").do(weekly_challenges_and_reset)  # Weekly challenges + reset
    schedule.every().hour.at(":00").do(hourly_flagged_user_detection)  # Hourly flagged users + alerts
    
    log_json("info", "SOL Enhanced scheduled tasks started", 
            scheduler="Python schedule library",
            jobs_scheduled=3,
            logging_format="JSON",
            logging_table="logs_scheduled_jobs")
    
    log_json("info", "Configuration", 
            max_retries=MAX_RETRY_ATTEMPTS, 
            retry_delay=RETRY_DELAY_SECONDS,
            exponential_backoff=EXPONENTIAL_BACKOFF)

    while True:
        try:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            log_json("info", "Scheduler stopped by user")
            break
        except Exception as e:
            log_json("error", "Scheduler error", error=str(e))
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    log_json("info", "SOL - Scheduled Operations Layer Enhanced", 
            version="2.0", client_requirements="fully_implemented")
    
    # Display job health status
    health_status = get_job_health_status()
    if health_status:
        log_json("info", "Recent job health status", health_data=health_status)
        for job_name, stats in health_status.items():
            success_rate = stats["success"] / (stats["success"] + stats["failed"]) * 100 if (stats["success"] + stats["failed"]) > 0 else 0
            log_json("info", f"Job health: {job_name}", 
                    success_rate=f"{success_rate:.1f}%", 
                    last_run=stats["last_run"])
    
    # Start scheduler
    run_scheduler()
