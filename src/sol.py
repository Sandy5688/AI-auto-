import os
import logging
import traceback
import time
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

# Configure logger with unified format
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuration for retry logic
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
EXPONENTIAL_BACKOFF = True

def calculate_behavior_score(user_data: Dict[str, Any]) -> int:
    """
    Calculate behavior score based on user data and recent activity.
    This replaces the dummy score calculation with real logic.
    
    Args:
        user_data: Dictionary containing user information and recent activity
        
    Returns:
        int: Calculated behavior score (0-100)
    """
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
        
        # Apply gradual change to prevent score volatility
        if current_score is not None:
            # Limit daily score change to ±10 points for stability
            max_change = 10
            score_diff = calculated_score - current_score
            if abs(score_diff) > max_change:
                calculated_score = current_score + (max_change if score_diff > 0 else -max_change)
        
        # Ensure score stays within bounds
        final_score = max(0, min(100, calculated_score))
        
        logger.info(f"Score calculated for user {user_id}: {current_score} → {final_score} "
                   f"(flags: -{flag_penalty}, activity: +{activity_score}, "
                   f"tokens: +{token_usage_score}, stability: +{stability_bonus})")
        
        return final_score
        
    except Exception as e:
        logger.error(f"Error calculating behavior score for user {user_data.get('id', 'unknown')}: {e}")
        # Return current score or default if calculation fails
        return user_data.get("behavior_score", 75)  # Conservative default

def get_recent_risk_flags(user_id: str, hours: int = 24) -> List[Dict]:
    """Get recent risk flags for a user within specified hours."""
    try:
        since_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        flags_resp = supabase.table("user_risk_flags").select("*").eq("user_id", user_id).gte("timestamp", since_time).execute()
        return flags_resp.data or []
    except Exception as e:
        logger.warning(f"Failed to fetch recent risk flags for user {user_id}: {e}")
        return []

def calculate_activity_score(user_id: str) -> int:
    """Calculate activity score based on user engagement patterns."""
    try:
        # This could be expanded to analyze:
        # - Login frequency
        # - Feature usage patterns
        # - Time spent in application
        # - Interaction quality metrics
        
        # Simplified example - could be replaced with real analytics
        recent_activity = get_user_recent_activity(user_id)
        
        if not recent_activity:
            return -5  # Penalty for no activity
        
        # Reward consistent, moderate activity
        activity_count = len(recent_activity)
        if 5 <= activity_count <= 20:
            return 5  # Good activity level
        elif activity_count > 50:
            return -3  # Suspiciously high activity
        else:
            return 0  # Neutral
            
    except Exception as e:
        logger.warning(f"Failed to calculate activity score for user {user_id}: {e}")
        return 0

def calculate_token_usage_score(user_id: str) -> int:
    """Calculate score based on token usage patterns."""
    try:
        # Get recent token usage
        usage_resp = supabase.table("token_usage_history").select("*").eq("user_id", user_id).order("timestamp", desc=True).limit(10).execute()
        usage_data = usage_resp.data or []
        
        if not usage_data:
            return 0
        
        # Reward normal usage patterns
        total_usage = sum(entry.get("tokens_used", 0) for entry in usage_data)
        
        if 1 <= total_usage <= 10:
            return 3  # Normal usage
        elif total_usage > 50:
            return -5  # Excessive usage
        else:
            return 0
            
    except Exception as e:
        logger.warning(f"Failed to calculate token usage score for user {user_id}: {e}")
        return 0

def calculate_stability_bonus(user_data: Dict[str, Any]) -> int:
    """Calculate bonus based on account stability and history."""
    try:
        # Could analyze:
        # - Account age
        # - Consistency of behavior
        # - Verification status
        # - Historical score trends
        
        # Simplified example
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
        logger.warning(f"Failed to calculate stability bonus: {e}")
        return 0

def get_user_recent_activity(user_id: str) -> List[Dict]:
    """Get recent user activity for scoring."""
    try:
        # This would typically query an activity/events table
        # For now, we'll use a simplified approach
        since_time = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        
        # Could query multiple tables for comprehensive activity data
        # activity_resp = supabase.table("user_activity").select("*").eq("user_id", user_id).gte("timestamp", since_time).execute()
        # return activity_resp.data or []
        
        # Placeholder - return empty for now
        return []
        
    except Exception as e:
        logger.warning(f"Failed to get recent activity for user {user_id}: {e}")
        return []

def retry_operation(operation_func, operation_name: str, *args, **kwargs) -> bool:
    """
    Retry a database operation with exponential backoff.
    
    Args:
        operation_func: Function to retry
        operation_name: Name of operation for logging
        *args, **kwargs: Arguments to pass to operation_func
        
    Returns:
        bool: True if operation succeeded, False if all retries failed
    """
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            logger.info(f"Attempting {operation_name} (attempt {attempt}/{MAX_RETRY_ATTEMPTS})")
            operation_func(*args, **kwargs)
            logger.info(f"✅ {operation_name} succeeded on attempt {attempt}")
            return True
            
        except Exception as e:
            logger.warning(f"❌ {operation_name} failed on attempt {attempt}: {e}")
            
            if attempt == MAX_RETRY_ATTEMPTS:
                logger.error(f"💥 {operation_name} failed after {MAX_RETRY_ATTEMPTS} attempts")
                send_failure_alert(operation_name, str(e))
                return False
            
            # Calculate retry delay with exponential backoff
            if EXPONENTIAL_BACKOFF:
                delay = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
            else:
                delay = RETRY_DELAY_SECONDS
                
            logger.info(f"⏳ Retrying {operation_name} in {delay} seconds...")
            time.sleep(delay)
    
    return False

def send_failure_alert(operation_name: str, error_message: str):
    """
    Send alert when critical operations fail after all retries.
    This could be extended to send emails, Slack notifications, etc.
    """
    try:
        alert_data = {
            "alert_type": "job_failure",
            "operation": operation_name,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "high",
            "status": "unresolved"
        }
        
        # Store alert in database
        supabase.table("system_alerts").insert(alert_data).execute()
        logger.error(f"🚨 ALERT: {operation_name} failed - Alert stored in database")
        
        # Future enhancement: Send to external alerting systems
        # send_slack_alert(alert_data)
        # send_email_alert(alert_data)
        
    except Exception as alert_err:
        logger.critical(f"💥 Failed to send failure alert for {operation_name}: {alert_err}")

def log_job(job_name, status, payload=None, error_message=None):
    """Enhanced job logging with better error handling."""
    entry = {
        "job_name": job_name,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
        "error_message": error_message,
        "retry_count": payload.get("retry_count", 0) if payload else 0
    }
    try:
        supabase.table("job_logs").insert(entry).execute()
        logger.info(f"📝 Job log written for {job_name}, status: {status}")
    except Exception as e:
        logger.error(f"❌ Could not log job {job_name}: {e}")

def _execute_daily_refresh():
    """Internal function to execute daily refresh logic."""
    users_resp = supabase.table("users").select("id, behavior_score, is_verified, created_at").execute()
    users = users_resp.data or []
    
    updated_count = 0
    failed_count = 0
    
    for user in users:
        try:
            user_id = user["id"]
            
            # Add calculated account age for scoring
            if user.get("created_at"):
                created_date = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
                account_age_days = (datetime.now(timezone.utc) - created_date).days
                user["account_age_days"] = account_age_days
            
            # Calculate new score using real logic
            new_score = calculate_behavior_score(user)
            
            # Update user score
            supabase.table("users").update({"behavior_score": new_score}).eq("id", user_id).execute()
            updated_count += 1
            
        except Exception as user_error:
            failed_count += 1
            logger.error(f"Failed to update score for user {user.get('id', 'unknown')}: {user_error}")
    
    logger.info(f"Daily refresh completed: {updated_count} users updated, {failed_count} failed")
    
    if failed_count > len(users) * 0.1:  # If more than 10% failed
        raise Exception(f"High failure rate in daily refresh: {failed_count}/{len(users)} users failed")

def daily_refresh():
    """Daily refresh of user behavior scores with retry logic."""
    job_name = "daily_refresh"
    
    def execute_with_logging():
        _execute_daily_refresh()
        log_job(job_name, "success", payload={"execution_time": datetime.now(timezone.utc).isoformat()})
    
    try:
        success = retry_operation(execute_with_logging, job_name)
        if not success:
            log_job(job_name, "failed_after_retries", 
                   error_message="Daily refresh failed after all retry attempts")
    except Exception as e:
        tb = traceback.format_exc()
        log_job(job_name, "error", error_message=f"{str(e)}\n{tb}")

def _execute_weekly_ranks():
    """Internal function to execute weekly ranking logic."""
    # Get top users by behavior score
    users_resp = supabase.table("users").select("id, behavior_score").order("behavior_score", desc=True).limit(100).execute()
    top_users = users_resp.data or []
    
    # Calculate rank changes from previous week
    previous_ranks_resp = supabase.table("weekly_rankings").select("*").order("created_at", desc=True).limit(100).execute()
    previous_ranks = {entry["user_id"]: entry["rank"] for entry in (previous_ranks_resp.data or [])}
    
    # Prepare new rankings
    new_rankings = []
    rank_changes = {}
    
    for rank, user in enumerate(top_users, 1):
        user_id = user["id"]
        previous_rank = previous_ranks.get(user_id, None)
        
        rank_change = 0
        if previous_rank:
            rank_change = previous_rank - rank  # Positive means moved up
        
        new_rankings.append({
            "user_id": user_id,
            "rank": rank,
            "behavior_score": user["behavior_score"],
            "previous_rank": previous_rank,
            "rank_change": rank_change,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        rank_changes[user_id] = rank_change
    
    # Clear old rankings and insert new ones
    # Delete rankings older than 4 weeks
    four_weeks_ago = (datetime.now(timezone.utc) - timedelta(weeks=4)).isoformat()
    supabase.table("weekly_rankings").delete().lt("created_at", four_weeks_ago).execute()
    
    # Insert new rankings
    if new_rankings:
        supabase.table("weekly_rankings").insert(new_rankings).execute()
    
    logger.info(f"Weekly rankings updated: Top {len(new_rankings)} users ranked")

def weekly_ranks():
    """Weekly ranking calculation with retry logic."""
    job_name = "weekly_ranks"
    
    def execute_with_logging():
        _execute_weekly_ranks()
        log_job(job_name, "success", payload={"execution_time": datetime.now(timezone.utc).isoformat()})
    
    try:
        success = retry_operation(execute_with_logging, job_name)
        if not success:
            log_job(job_name, "failed_after_retries", 
                   error_message="Weekly ranks failed after all retry attempts")
    except Exception as e:
        tb = traceback.format_exc()
        log_job(job_name, "error", error_message=f"{str(e)}\n{tb}")

def _execute_hourly_anomaly_scan():
    """Internal function to execute hourly anomaly scanning."""
    # Get flags from the last hour
    since_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    flags_resp = supabase.table("user_risk_flags").select("*").gte("timestamp", since_time).execute()
    recent_flags = flags_resp.data or []
    
    # Analyze flag patterns
    flag_analysis = analyze_flag_patterns(recent_flags)
    
    # Check for anomalous patterns
    anomalies = detect_anomalies(flag_analysis)
    
    # Store anomaly results
    if anomalies:
        anomaly_records = []
        for anomaly in anomalies:
            anomaly_records.append({
                "anomaly_type": anomaly["type"],
                "description": anomaly["description"],
                "severity": anomaly["severity"],
                "affected_users": anomaly.get("affected_users", []),
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "metadata": anomaly.get("metadata", {})
            })
        
        supabase.table("detected_anomalies").insert(anomaly_records).execute()
        logger.warning(f"🚨 Detected {len(anomalies)} anomalies in recent flags")
    
    logger.info(f"Hourly anomaly scan completed: {len(recent_flags)} flags analyzed, {len(anomalies)} anomalies detected")

def analyze_flag_patterns(flags: List[Dict]) -> Dict[str, Any]:
    """Analyze patterns in risk flags."""
    analysis = {
        "total_flags": len(flags),
        "flag_types": {},
        "user_flag_counts": {},
        "time_patterns": []
    }
    
    for flag in flags:
        flag_type = flag.get("flag", "unknown")
        user_id = flag.get("user_id", "unknown")
        
        # Count flag types
        analysis["flag_types"][flag_type] = analysis["flag_types"].get(flag_type, 0) + 1
        
        # Count flags per user
        analysis["user_flag_counts"][user_id] = analysis["user_flag_counts"].get(user_id, 0) + 1
    
    return analysis

def detect_anomalies(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect anomalous patterns in flag analysis."""
    anomalies = []
    
    # Anomaly 1: Unusual spike in specific flag type
    for flag_type, count in analysis["flag_types"].items():
        if count > 10:  # Threshold for anomaly
            anomalies.append({
                "type": "flag_spike",
                "description": f"Unusual spike in {flag_type} flags: {count} occurrences",
                "severity": "medium",
                "metadata": {"flag_type": flag_type, "count": count}
            })
    
    # Anomaly 2: Users with excessive flags
    excessive_flag_users = [
        user_id for user_id, count in analysis["user_flag_counts"].items() 
        if count > 5
    ]
    
    if excessive_flag_users:
        anomalies.append({
            "type": "excessive_user_flags",
            "description": f"{len(excessive_flag_users)} users with excessive flags",
            "severity": "high",
            "affected_users": excessive_flag_users,
            "metadata": {"user_counts": {u: analysis["user_flag_counts"][u] for u in excessive_flag_users}}
        })
    
    # Anomaly 3: Overall flag volume anomaly
    if analysis["total_flags"] > 50:  # Threshold for total flags
        anomalies.append({
            "type": "high_flag_volume",
            "description": f"High flag volume detected: {analysis['total_flags']} flags in one hour",
            "severity": "high",
            "metadata": {"total_flags": analysis["total_flags"]}
        })
    
    return anomalies

def hourly_anomaly_scan():
    """Hourly anomaly detection with retry logic."""
    job_name = "hourly_anomaly_scan"
    
    def execute_with_logging():
        _execute_hourly_anomaly_scan()
        log_job(job_name, "success", payload={"execution_time": datetime.now(timezone.utc).isoformat()})
    
    try:
        success = retry_operation(execute_with_logging, job_name)
        if not success:
            log_job(job_name, "failed_after_retries", 
                   error_message="Hourly anomaly scan failed after all retry attempts")
    except Exception as e:
        tb = traceback.format_exc()
        log_job(job_name, "error", error_message=f"{str(e)}\n{tb}")

def get_job_health_status() -> Dict[str, Any]:
    """Get health status of scheduled jobs."""
    try:
        # Get recent job logs
        recent_logs_resp = supabase.table("job_logs").select("*").order("timestamp", desc=True).limit(50).execute()
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
        logger.error(f"Failed to get job health status: {e}")
        return {}

def run_scheduler():
    """Run the job scheduler with enhanced monitoring."""
    # Schedule jobs with retry logic
    schedule.every().day.at("00:01").do(daily_refresh)
    schedule.every().monday.at("00:10").do(weekly_ranks)
    schedule.every().hour.at(":00").do(hourly_anomaly_scan)
    
    logger.info("🚀 Enhanced scheduled tasks started with retry logic. Press Ctrl+C to exit.")
    logger.info(f"Configuration: Max retries: {MAX_RETRY_ATTEMPTS}, Retry delay: {RETRY_DELAY_SECONDS}s, "
               f"Exponential backoff: {EXPONENTIAL_BACKOFF}")

    while True:
        try:
            schedule.run_pending()
            time.sleep(10)
        except KeyboardInterrupt:
            logger.info("📝 Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"💥 Scheduler error: {e}")
            time.sleep(30)  # Wait before retrying

if __name__ == "__main__":
    logger.info("🔧 Sol.py - Enhanced Job Scheduler")
    
    # Display job health status
    health_status = get_job_health_status()
    if health_status:
        logger.info("📊 Recent job health status:")
        for job_name, stats in health_status.items():
            success_rate = stats["success"] / (stats["success"] + stats["failed"]) * 100
            logger.info(f"  {job_name}: {success_rate:.1f}% success rate, last run: {stats['last_run']}")
    
    # Start scheduler
    run_scheduler()
