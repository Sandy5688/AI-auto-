from flask import Flask, request, jsonify
from supabase import create_client
import os
import logging
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables
load_dotenv("config/.env")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def log_skipped_payload(payload, reason):
    """
    Log skipped/ignored payloads with detailed information.
    """
    logger.warning(f"🚫 PAYLOAD SKIPPED - Reason: {reason}")
    logger.warning(f"   Payload content: {payload}")
    
    # Optionally store in database for analysis
    try:
        supabase.table("skipped_payloads").insert({
            "payload": payload,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "endpoint": "/webhook"
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log skipped payload to database: {e}")

@app.route('/webhook', methods=['POST'])
@limiter.limit("100 per hour")
def handle_webhook():
    try:
        # Handle different content types
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json(force=True)
        else:
            log_skipped_payload(request.data, "Invalid content type")
            return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400
        
        # Log received data for debugging
        logger.info(f"📥 Received webhook data: {data}")

        # Enhanced payload validation
        if not data:
            log_skipped_payload(data, "Empty payload")
            return jsonify({"status": "error", "message": "Empty payload"}), 400
        
        if not isinstance(data, dict):
            log_skipped_payload(data, "Payload is not a JSON object")
            return jsonify({"status": "error", "message": "Payload must be a JSON object"}), 400

        # Validate required fields
        user_id = data.get("user_id")
        behavior_score = data.get("behavior_score")
        risk_flags = data.get("risk_flags", [])
        timestamp_str = data.get("timestamp")

        # Check for missing required fields
        missing_fields = []
        if not user_id or not isinstance(user_id, str):
            missing_fields.append("user_id (string)")
        if behavior_score is None or not isinstance(behavior_score, (int, float)):
            missing_fields.append("behavior_score (number)")
        if not isinstance(risk_flags, list):
            missing_fields.append("risk_flags (array)")
        
        if missing_fields:
            reason = f"Missing or invalid required fields: {', '.join(missing_fields)}"
            log_skipped_payload(data, reason)
            return jsonify({"status": "error", "message": reason}), 400

        # Validate and parse timestamp
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp_str}. Using current UTC time.")
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        # Check for duplicate submissions (within 1 minute)
        try:
            recent_submissions = supabase.table("users").select("last_updated").eq("id", user_id).execute()
            if recent_submissions.data:
                last_updated = recent_submissions.data[0].get("last_updated")
                if last_updated:
                    last_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    time_diff = (timestamp - last_time).total_seconds()
                    
                    if abs(time_diff) < 60:  # Within 1 minute
                        logger.info(f"⚠️  Duplicate submission detected for user {user_id} within {time_diff}s")
                        return jsonify({"status": "duplicate", "message": "Recent submission already processed"}), 200
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")

        # Prepare payload for database
        payload = {
            "id": user_id,
            "behavior_score": int(behavior_score),
            "risk_flags": risk_flags,
            "last_updated": timestamp.isoformat()
        }

        # Update user behavior score
        response = supabase.table("users").upsert(payload).execute()
        if not response.data:
            logger.error(f"Failed to upsert user data: {response}")
            return jsonify({"status": "error", "message": "Database update failed"}), 500

        # Log successful processing
        logger.info(f"✅ User {user_id} updated - Score: {behavior_score}, Flags: {len(risk_flags)}, Timestamp: {timestamp}")
        
        return jsonify({
            "status": "success", 
            "user_id": user_id,
            "score": behavior_score,
            "flags_count": len(risk_flags),
            "processed_at": datetime.utcnow().isoformat() + "Z"
        }), 200

    except Exception as e:
        logger.error(f"💥 Exception handling webhook: {str(e)}")
        log_skipped_payload(request.data if hasattr(request, 'data') else None, f"Server error: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}), 200

@app.route '/webhook/stats', methods=['GET'])
def webhook_stats():
    """Get webhook processing statistics"""
    try:
        # Get recent activity stats
        recent_users = supabase.table("users").select("id, behavior_score, last_updated").order("last_updated", desc=True).limit(10).execute()
        skipped_count = supabase.table("skipped_payloads").select("id", count="exact").execute()
        
        return jsonify({
            "recent_updates": len(recent_users.data) if recent_users.data else 0,
            "skipped_payloads": skipped_count.count if hasattr(skipped_count, 'count') else 0,
            "recent_users": recent_users.data[:5] if recent_users.data else []
        }), 200
    except Exception as e:
        logger.error(f"Error getting webhook stats: {e}")
        return jsonify({"error": "Could not fetch stats"}), 500

if __name__ == "__main__":
    logger.info("🚀 Starting enhanced webhook server with duplicate prevention...")
    app.run(debug=True, host="0.0.0.0", port=5001)
