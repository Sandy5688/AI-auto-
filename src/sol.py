import schedule
import time
from datetime import datetime, timezone
from supabase import create_client
import random

# Supabase setup (replace with your credentials)
SUPABASE_URL = "https://hlphvrulcwlahwifmeur.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhscGh2cnVsY3dsYWh3aWZtZXVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE5OTM1NzQsImV4cCI6MjA2NzU2OTU3NH0._hPUFuM8OlKUSP2R093ZeNFr8WIpI2aJkygMeOkAb6A"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Log job results to Supabase
def log_job(job_name, status, payload=None, error_message=None):
    # Format timestamp to ISO 8601 without microseconds and remove 'Z'
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    log_data = {
        "job_name": job_name,
        "status": status,
        "timestamp": timestamp,
        "payload": payload or {},
        "error_message": error_message or ""
    }
    supabase.table("job_logs").insert(log_data).execute()

# Daily score refresh (placeholder)
def daily_score_refresh():
    try:
        # Placeholder: Update scores in Supabase
        # Example: Reset scores or recalculate based on recent data
        payload = {"users_updated": random.randint(50, 100)}  # Mock data
        log_job("daily_score_refresh", "success", payload)
        print("Daily score refresh completed")
    except Exception as e:
        log_job("daily_score_refresh", "failure", error_message=str(e))
        print(f"Daily score refresh failed: {e}")

# Weekly rank recalculation (placeholder)
def weekly_rank_recalculation():
    try:
        # Placeholder: Update leaderboard ranks
        payload = {"ranks_updated": random.randint(10, 20)}  # Mock data
        log_job("weekly_rank_recalculation", "success", payload)
        print("Weekly rank recalculation completed")
    except Exception as e:
        log_job("weekly_rank_recalculation", "failure", error_message=str(e))
        print(f"Weekly rank recalculation failed: {e}")

# Hourly anomaly check (placeholder)
def hourly_anomaly_check():
    try:
        # Placeholder: Check for new anomalies
        payload = {"anomalies_flagged": random.randint(0, 5)}  # Mock data
        log_job("hourly_anomaly_check", "success", payload)
        print("Hourly anomaly check completed")
    except Exception as e:
        log_job("hourly_anomaly_check", "failure", error_message=str(e))
        print(f"Hourly anomaly check failed: {e}")

# Schedule jobs for testing
schedule.every(10).seconds.do(daily_score_refresh)
schedule.every(20).seconds.do(weekly_rank_recalculation)
schedule.every(30).seconds.do(hourly_anomaly_check)

# Main loop to run scheduled jobs
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)  # Changed to 1 second

if __name__ == "__main__":
    print("Starting scheduler...")
    run_scheduler()