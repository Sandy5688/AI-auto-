import os
import logging
import traceback
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import schedule
import time

# Load environment variables
load_dotenv("config/.env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def log_job(job_name, status, payload=None, error_message=None):
    entry = {
        "job_name": job_name,
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload or {},
        "error_message": error_message
    }
    try:
        supabase.table("job_logs").insert(entry).execute()
        logger.info(f"Job log written for {job_name}, status: {status}")
    except Exception as e:
        logger.error(f"Could not log job {job_name}: {e}")

def daily_refresh():
    job_name = "daily_refresh"
    try:
        users = supabase.table("users").select("id").execute().data
        for user in users:
            # Dummy score recalculation – replace with your real logic
            user_id = user["id"]
            new_score = 100  # Replace with actual score calculation
            supabase.table("users").update({"behavior_score": new_score}).eq("id", user_id).execute()
        log_job(job_name, "success", payload={"affected_users": len(users)})
    except Exception as e:
        tb = traceback.format_exc()
        log_job(job_name, "error", error_message=f"{str(e)}\n{tb}")

def weekly_ranks():
    job_name = "weekly_ranks"
    try:
        users = supabase.table("users").select("id, behavior_score").order("behavior_score", desc=True).limit(100).execute().data
        # Example: Top 100 leaderboard ranking – add your leaderboard update here
        log_job(job_name, "success", payload={"top_users": [u["id"] for u in users]})
    except Exception as e:
        tb = traceback.format_exc()
        log_job(job_name, "error", error_message=f"{str(e)}\n{tb}")

def hourly_anomaly_scan():
    job_name = "hourly_anomaly_scan"
    try:
        # Query recent anomalies in user_risk_flags from the last hour
        since = datetime.utcnow().isoformat()[:13]  # Get current UTC hour
        flags = supabase.table("user_risk_flags").select("*").gte("timestamp", since).execute().data
        log_job(job_name, "success", payload={"anomaly_count": len(flags)})
    except Exception as e:
        tb = traceback.format_exc()
        log_job(job_name, "error", error_message=f"{str(e)}\n{tb}")

def run_scheduler():
    # Schedule jobs
    schedule.every().day.at("00:01").do(daily_refresh)
    schedule.every().monday.at("00:10").do(weekly_ranks)
    schedule.every().hour.at(":00").do(hourly_anomaly_scan)

    logger.info("Scheduled tasks started. Press Ctrl+C to exit.")

    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    run_scheduler()
