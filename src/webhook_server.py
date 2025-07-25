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
    default_limits=["200 per day", "50 per hour"]  # adjust as needed
)


# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/webhook', methods=['POST'])
@limiter.limit("100 per hour")  # Optional: customize limit per route
def handle_webhook():
    try:
        data = request.get_json(force=True)
        logger.info(f"Received webhook data: {data}")

        # Validate required fields and types
        user_id = data.get("user_id")
        behavior_score = data.get("behavior_score")
        risk_flags = data.get("risk_flags", [])
        timestamp_str = data.get("timestamp")

        if not user_id or not isinstance(user_id, str):
            return jsonify({"status": "error", "message": "Missing or invalid 'user_id'"}), 400
        if behavior_score is None or not isinstance(behavior_score, int):
            return jsonify({"status": "error", "message": "Missing or invalid 'behavior_score'"}), 400
        if not isinstance(risk_flags, list):
            return jsonify({"status": "error", "message": "'risk_flags' must be a list"}), 400

        if timestamp_str:
            try:
                # Parse timestamp, fallback to now if invalid
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp_str}. Using current UTC time.")
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        # Upsert user behavior scores with risk flags and timestamp
        payload = {
            "id": user_id,
            "behavior_score": behavior_score,
            "risk_flags": risk_flags,
            "last_updated": timestamp.isoformat()
        }

        response = supabase.table("users").upsert(payload).execute()
        if response.status_code != 200 and response.status_code != 201:
            logger.error(f"Failed to upsert user data: {response.status_code} {response.data}")
            return jsonify({"status": "error", "message": "Database update failed"}), 500

        logger.info(f"User {user_id} updated with score {behavior_score} and flags {risk_flags}")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Exception handling webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
