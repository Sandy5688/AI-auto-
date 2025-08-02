from flask import Flask, request, jsonify, abort
from supabase import create_client
import os
import logging
import hmac
import hashlib
import json
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps

# Dynamically find the config/.env file
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, "config", ".env")

load_dotenv(env_path)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# FIXED: Updated Flask-Limiter initialization for newer versions
# Correct Flask-Limiter initialization (from docs)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


# Logger setup with unified format
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Webhook security configuration
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")
WEBHOOK_AUTH_METHOD = os.getenv("WEBHOOK_AUTH_METHOD", "signature")  # "signature" or "token"

# Validate environment variables
if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env")

if WEBHOOK_AUTH_METHOD == "signature" and not WEBHOOK_SECRET:
    raise ValueError("WEBHOOK_SECRET must be set when using signature authentication")

if WEBHOOK_AUTH_METHOD == "token" and not WEBHOOK_TOKEN:
    raise ValueError("WEBHOOK_TOKEN must be set when using token authentication")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Error response templates
ERROR_RESPONSES = {
    "MISSING_AUTH": {
        "status": "error",
        "error_code": "MISSING_AUTH",
        "message": "Missing authentication credentials"
    },
    "INVALID_AUTH": {
        "status": "error", 
        "error_code": "INVALID_AUTH",
        "message": "Invalid authentication credentials"
    },
    "INVALID_SIGNATURE": {
        "status": "error",
        "error_code": "INVALID_SIGNATURE", 
        "message": "Invalid webhook signature"
    },
    "INVALID_CONTENT_TYPE": {
        "status": "error",
        "error_code": "INVALID_CONTENT_TYPE",
        "message": "Content-Type must be application/json"
    },
    "INVALID_PAYLOAD": {
        "status": "error",
        "error_code": "INVALID_PAYLOAD",
        "message": "Invalid or missing payload data"
    },
    "VALIDATION_ERROR": {
        "status": "error",
        "error_code": "VALIDATION_ERROR", 
        "message": "Payload validation failed"
    },
    "DATABASE_ERROR": {
        "status": "error",
        "error_code": "DATABASE_ERROR",
        "message": "Database operation failed"
    },
    "INTERNAL_ERROR": {
        "status": "error",
        "error_code": "INTERNAL_ERROR",
        "message": "Internal server error"
    }
}

def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.
    
    Args:
        payload_body: Raw request body as bytes
        signature_header: Signature from request header
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("Missing signature header")
        return False
    
    try:
        # Extract signature from header (format: "sha256=<signature>")
        if not signature_header.startswith("sha256="):
            logger.warning(f"Invalid signature format: {signature_header}")
            return False
            
        provided_signature = signature_header[7:]  # Remove "sha256=" prefix
        
        # Calculate expected signature
        expected_signature = hmac.new(
            WEBHOOK_SECRET.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(provided_signature, expected_signature)
        
        if not is_valid:
            logger.warning(f"Signature mismatch: provided={provided_signature[:8]}..., expected={expected_signature[:8]}...")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False

def verify_webhook_token(token_header: str) -> bool:
    """
    Verify webhook using bearer token authentication.
    
    Args:
        token_header: Authorization header value
        
    Returns:
        bool: True if token is valid, False otherwise
    """
    if not token_header:
        logger.warning("Missing authorization header")
        return False
    
    try:
        # Extract token from header (format: "Bearer <token>")
        if not token_header.startswith("Bearer "):
            logger.warning(f"Invalid authorization format: {token_header}")
            return False
            
        provided_token = token_header[7:]  # Remove "Bearer " prefix
        
        # Use constant-time comparison
        is_valid = hmac.compare_digest(provided_token, WEBHOOK_TOKEN)
        
        if not is_valid:
            logger.warning(f"Token mismatch: provided={provided_token[:8]}...")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error verifying webhook token: {e}")
        return False

def require_webhook_auth(f):
    """
    Decorator to enforce webhook authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if WEBHOOK_AUTH_METHOD == "signature":
                # Signature-based authentication
                signature = request.headers.get("X-Webhook-Signature") or request.headers.get("X-Hub-Signature-256")
                
                if not signature:
                    logger.warning(f"Missing signature header from {request.remote_addr}")
                    return jsonify(ERROR_RESPONSES["MISSING_AUTH"]), 401
                
                # Get raw request body for signature verification
                payload_body = request.get_data()
                
                if not verify_webhook_signature(payload_body, signature):
                    logger.warning(f"Invalid signature from {request.remote_addr}")
                    return jsonify(ERROR_RESPONSES["INVALID_SIGNATURE"]), 401
                    
                logger.info(f"✅ Valid webhook signature from {request.remote_addr}")
                
            elif WEBHOOK_AUTH_METHOD == "token":
                # Token-based authentication
                auth_header = request.headers.get("Authorization")
                
                if not auth_header:
                    logger.warning(f"Missing authorization header from {request.remote_addr}")
                    return jsonify(ERROR_RESPONSES["MISSING_AUTH"]), 401
                
                if not verify_webhook_token(auth_header):
                    logger.warning(f"Invalid token from {request.remote_addr}")
                    return jsonify(ERROR_RESPONSES["INVALID_AUTH"]), 401
                    
                logger.info(f"✅ Valid webhook token from {request.remote_addr}")
                
            else:
                logger.error(f"Unknown webhook auth method: {WEBHOOK_AUTH_METHOD}")
                return jsonify(ERROR_RESPONSES["INTERNAL_ERROR"]), 500
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify(ERROR_RESPONSES["INTERNAL_ERROR"]), 500
            
        return f(*args, **kwargs)
    return decorated_function

def log_skipped_payload(payload, reason, error_code=None):
    """
    Log skipped/ignored payloads with detailed information.
    """
    logger.warning(f"🚫 PAYLOAD SKIPPED - Reason: {reason}")
    logger.warning(f"   Error Code: {error_code}")
    logger.warning(f"   Payload content: {payload}")
    logger.warning(f"   Request IP: {request.remote_addr}")
    logger.warning(f"   User Agent: {request.headers.get('User-Agent', 'Unknown')}")
    
    # Store in database for analysis
    try:
        supabase.table("skipped_payloads").insert({
            "payload": payload if isinstance(payload, dict) else str(payload),
            "reason": reason,
            "error_code": error_code,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "endpoint": "/webhook",
            "source_ip": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', 'Unknown')
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log skipped payload to database: {e}")

def classify_database_error(error_message: str) -> tuple:
    """
    Classify database errors and return appropriate HTTP status code and error type.
    
    Returns:
        tuple: (http_status_code, error_code, user_message)
    """
    error_lower = str(error_message).lower()
    
    # Connection/Network errors -> 502 Bad Gateway
    if any(term in error_lower for term in ["connection", "network", "timeout", "unreachable", "dns"]):
        return 502, "DATABASE_CONNECTION_ERROR", "Database connection failed"
    
    # Service unavailable -> 503 Service Unavailable  
    if any(term in error_lower for term in ["service unavailable", "maintenance", "overloaded"]):
        return 503, "DATABASE_UNAVAILABLE", "Database service temporarily unavailable"
    
    # Authentication/Permission errors -> 502 Bad Gateway (external service issue)
    if any(term in error_lower for term in ["authentication", "permission", "unauthorized", "access denied"]):
        return 502, "DATABASE_AUTH_ERROR", "Database authentication failed"
    
    # Constraint violations, invalid data -> 400 Bad Request
    if any(term in error_lower for term in ["constraint", "validation", "invalid", "duplicate key"]):
        return 400, "DATABASE_VALIDATION_ERROR", "Data validation failed"
    
    # Generic database errors -> 500 Internal Server Error
    return 500, "DATABASE_ERROR", "Database operation failed"

@app.route('/webhook', methods=['POST'])
@limiter.limit("100 per hour")
@require_webhook_auth
def handle_webhook():
    request_start_time = datetime.utcnow()
    
    try:
        # Validate content type
        if not request.content_type or 'application/json' not in request.content_type:
            log_skipped_payload(request.data, "Invalid content type", "INVALID_CONTENT_TYPE")
            return jsonify(ERROR_RESPONSES["INVALID_CONTENT_TYPE"]), 400
        
        # Parse JSON payload
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            log_skipped_payload(request.data, f"JSON parse error: {json_error}", "INVALID_PAYLOAD")
            return jsonify(ERROR_RESPONSES["INVALID_PAYLOAD"]), 400

        # Log received data
        logger.info(f"📥 Received authenticated webhook data from {request.remote_addr}: {len(str(data))} bytes")

        # Enhanced payload validation
        if not data:
            log_skipped_payload(data, "Empty payload", "INVALID_PAYLOAD")
            return jsonify(ERROR_RESPONSES["INVALID_PAYLOAD"]), 400
        
        if not isinstance(data, dict):
            log_skipped_payload(data, "Payload is not a JSON object", "INVALID_PAYLOAD")
            return jsonify(ERROR_RESPONSES["INVALID_PAYLOAD"]), 400

        # Validate required fields with detailed error messages
        validation_errors = []
        
        user_id = data.get("user_id")
        behavior_score = data.get("behavior_score")
        risk_flags = data.get("risk_flags", [])
        timestamp_str = data.get("timestamp")

        if not user_id or not isinstance(user_id, str) or len(user_id.strip()) == 0:
            validation_errors.append("user_id must be a non-empty string")
            
        if behavior_score is None or not isinstance(behavior_score, (int, float)) or not (0 <= behavior_score <= 100):
            validation_errors.append("behavior_score must be a number between 0 and 100")
            
        if not isinstance(risk_flags, list):
            validation_errors.append("risk_flags must be an array")
        elif len(risk_flags) > 20:  # Reasonable limit
            validation_errors.append("risk_flags array cannot exceed 20 items")
        
        if validation_errors:
            error_response = ERROR_RESPONSES["VALIDATION_ERROR"].copy()
            error_response["validation_errors"] = validation_errors
            log_skipped_payload(data, f"Validation failed: {', '.join(validation_errors)}", "VALIDATION_ERROR")
            return jsonify(error_response), 400

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
                        return jsonify({
                            "status": "duplicate", 
                            "message": "Recent submission already processed",
                            "user_id": user_id,
                            "time_diff_seconds": time_diff
                        }), 200
        except Exception as dup_check_error:
            # Log but don't fail the request for duplicate check errors
            logger.warning(f"Error checking for duplicates: {dup_check_error}")

        # Prepare payload for database
        payload = {
            "id": user_id,
            "behavior_score": int(behavior_score),
            "risk_flags": risk_flags,
            "last_updated": timestamp.isoformat()
        }

        # Update user behavior score with enhanced error handling
        try:
            response = supabase.table("users").upsert(payload).execute()
            if not response.data:
                logger.error(f"Supabase upsert returned no data: {response}")
                return jsonify(ERROR_RESPONSES["DATABASE_ERROR"]), 500

        except Exception as db_error:
            # Classify the database error and return appropriate status code
            status_code, error_code, user_message = classify_database_error(str(db_error))
            
            logger.error(f"Database error (HTTP {status_code}): {db_error}")
            
            error_response = {
                "status": "error",
                "error_code": error_code,
                "message": user_message,
                "user_id": user_id
            }
            
            return jsonify(error_response), status_code

        # Calculate processing time
        processing_time = (datetime.utcnow() - request_start_time).total_seconds()

        # Log successful processing
        logger.info(f"✅ User {user_id} updated - Score: {behavior_score}, Flags: {len(risk_flags)}, "
                   f"Processing time: {processing_time:.3f}s")
        
        return jsonify({
            "status": "success", 
            "user_id": user_id,
            "score": behavior_score,
            "flags_count": len(risk_flags),
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "processing_time_seconds": processing_time
        }), 200

    except Exception as e:
        logger.error(f"💥 Unexpected error handling webhook: {str(e)}")
        log_skipped_payload(
            request.data if hasattr(request, 'data') else None, 
            f"Unexpected server error: {str(e)}", 
            "INTERNAL_ERROR"
        )
        return jsonify(ERROR_RESPONSES["INTERNAL_ERROR"]), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint with database connectivity test"""
    try:
        # Test database connectivity
        db_test = supabase.table("users").select("id").limit(1).execute()
        db_status = "healthy" if db_test else "error"
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database": db_status,
            "auth_method": WEBHOOK_AUTH_METHOD,
            "version": "2.0.0"
        }
        
        return jsonify(health_data), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }), 503

@app.route('/webhook/stats', methods=['GET'])
def webhook_stats():
    """Get webhook processing statistics with enhanced metrics"""
    try:
        # Get recent activity stats
        recent_users = supabase.table("users").select("id, behavior_score, last_updated").order("last_updated", desc=True).limit(10).execute()
        skipped_count_resp = supabase.table("skipped_payloads").select("id", count="exact").execute()
        
        # Get error statistics
        recent_skipped = supabase.table("skipped_payloads").select("error_code").order("timestamp", desc=True).limit(100).execute()
        error_counts = {}
        for skip in (recent_skipped.data or []):
            error_code = skip.get("error_code", "UNKNOWN")
            error_counts[error_code] = error_counts.get(error_code, 0) + 1
        
        return jsonify({
            "recent_updates": len(recent_users.data) if recent_users.data else 0,
            "skipped_payloads_total": skipped_count_resp.count if hasattr(skipped_count_resp, 'count') else 0,
            "recent_users": recent_users.data[:5] if recent_users.data else [],
            "error_summary": error_counts,
            "auth_method": WEBHOOK_AUTH_METHOD,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting webhook stats: {e}")
        return jsonify({"error": "Could not fetch stats"}), 500

@app.route('/webhook/test-auth', methods=['POST'])
@require_webhook_auth
def test_webhook_auth():
    """Test endpoint to verify webhook authentication is working"""
    return jsonify({
        "status": "success",
        "message": "Authentication successful",
        "auth_method": WEBHOOK_AUTH_METHOD,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200

# Global error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded from {request.remote_addr}: {e}")
    return jsonify({
        "status": "error",
        "error_code": "RATE_LIMIT_EXCEEDED",
        "message": "Rate limit exceeded. Please slow down your requests."
    }), 429

@app.errorhandler(404)
def not_found_handler(e):
    logger.info(f"404 request from {request.remote_addr}: {request.path}")
    return jsonify({
        "status": "error",
        "error_code": "ENDPOINT_NOT_FOUND",
        "message": "Endpoint not found"
    }), 404

@app.errorhandler(405)
def method_not_allowed_handler(e):
    logger.info(f"405 request from {request.remote_addr}: {request.method} {request.path}")
    return jsonify({
        "status": "error",
        "error_code": "METHOD_NOT_ALLOWED",
        "message": f"Method {request.method} not allowed for this endpoint"
    }), 405

if __name__ == "__main__":
    logger.info("🚀 Starting enhanced webhook server with authentication...")
    logger.info(f"Authentication method: {WEBHOOK_AUTH_METHOD}")
    logger.info(f"Security features: Signature verification, Rate limiting, Input validation")
    
    app.run(debug=True, host="0.0.0.0", port=5001)
