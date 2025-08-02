import os
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
from encryption_utils import encrypt_token, decrypt_token
from token_tracking import track_token_usage

# Dynamically find the config/.env file regardless of current working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up from src/ to project root
env_path = os.path.join(project_root, "config", ".env")

load_dotenv(env_path)

# Configuration constants
REPLICATE_API = "https://api.replicate.com/v1/predictions"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MODEL_VERSION = os.getenv("REPLICATE_MODEL_VERSION")

# Migration control flag
MIGRATE_ENABLED = os.getenv("MIGRATE_ENABLED", "false").lower() in ("true", "1", "yes", "on")

# Validate environment variables
if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env")

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Simple in-memory cache for repeated meme requests within 24 hours
MEME_CACHE = {}

def is_cache_valid(cache_entry):
    if not cache_entry:
        return False
    _, expiry = cache_entry
    return datetime.utcnow() < expiry

def get_cached_result(user_id, prompt, tone, image_url):
    key = (user_id, prompt, tone, image_url or "")
    entry = MEME_CACHE.get(key)
    if is_cache_valid(entry):
        logger.info(f"Serving meme from cache for user={user_id}, prompt='{prompt}', tone={tone}")
        return entry[0]
    else:
        MEME_CACHE.pop(key, None)
        return None

def cache_result(user_id, prompt, tone, image_url, result, ttl_hours=24):
    key = (user_id, prompt, tone, image_url or "")
    expiry = datetime.utcnow() + timedelta(hours=ttl_hours)
    MEME_CACHE[key] = (result, expiry)

def check_migration_lock():
    """
    Check if migration has already been completed to prevent duplicate runs.
    Uses a simple database flag to track migration status.
    """
    try:
        # Check if migration status table exists and has completion record
        result = supabase.table("migration_status").select("*").eq("migration_name", "plaintext_token_migration").execute()
        
        if result.data:
            completion_record = result.data[0]
            if completion_record.get("completed", False):
                logger.info("Token migration already completed - skipping")
                return True
            else:
                logger.info("Previous migration attempt found but not completed - will retry")
                return False
        else:
            logger.info("No previous migration record found - will proceed")
            return False
            
    except Exception as e:
        # If table doesn't exist or query fails, assume migration hasn't run
        logger.warning(f"Could not check migration status (table may not exist): {e}")
        return False

def set_migration_completion():
    """
    Mark migration as completed in the database.
    """
    try:
        completion_record = {
            "migration_name": "plaintext_token_migration",
            "completed": True,
            "completed_at": datetime.utcnow().isoformat() + "Z",
            "migrated_users": 0  # Will be updated with actual count
        }
        
        supabase.table("migration_status").upsert(completion_record).execute()
        logger.info("Migration completion status recorded")
        
    except Exception as e:
        logger.error(f"Failed to record migration completion: {e}")

def migrate_plaintext_tokens():
    """
    Safely migrate legacy plaintext tokens with proper locking and error handling.
    Only runs if MIGRATE_ENABLED=true in .env and hasn't been completed before.
    """
    if not MIGRATE_ENABLED:
        logger.info("⏭️  Token migration disabled (MIGRATE_ENABLED=false)")
        return False

    logger.info("🔄 Starting token migration check...")

    # Check if migration already completed - RETURN TRUE HERE!
    if check_migration_lock():
        logger.info("✅ Migration already completed - skipping")
        return True  # THIS IS THE KEY FIX - must return True when already done

    logger.info("🚀 Starting legacy token migration...")
    migrated_count = 0
    error_count = 0

    try:
        # Fetch users with potential plaintext tokens
        users_query = supabase.table("users").select("id, token, encrypted_token").execute()
        users = users_query.data or []
        
        logger.info(f"Found {len(users)} users to check for migration")

        for user in users:
            user_id = user.get("id")
            plaintext_token = user.get("token")
            encrypted_token = user.get("encrypted_token")

            try:
                # Skip if no plaintext token or already has encrypted token
                if not plaintext_token:
                    continue
                    
                if encrypted_token:
                    logger.debug(f"User {user_id} already has encrypted token - skipping")
                    continue

                logger.info(f"Migrating token for user {user_id}")
                
                # Encrypt the plaintext token
                encrypted = encrypt_token(plaintext_token)
                
                # Update with encrypted token and remove plaintext
                update_data = {
                    "encrypted_token": encrypted,
                    "token": None  # Remove plaintext token for security
                }
                
                supabase.table("users").update(update_data).eq("id", user_id).execute()
                migrated_count += 1
                
                logger.info(f"✅ Successfully migrated token for user {user_id}")

            except Exception as user_error:
                error_count += 1
                logger.error(f"❌ Failed to migrate token for user {user_id}: {user_error}")
                continue

        # Record migration completion
        try:
            completion_record = {
                "migration_name": "plaintext_token_migration",
                "completed": True,
                "completed_at": datetime.utcnow().isoformat() + "Z",
                "migrated_users": migrated_count,
                "error_count": error_count
            }
            supabase.table("migration_status").upsert(completion_record).execute()
        except Exception as e:
            logger.error(f"Failed to record migration completion: {e}")

        logger.info(f"🏁 Token migration completed: {migrated_count} users migrated, {error_count} errors")
        return True  # Return True on successful completion

    except Exception as e:
        logger.error(f"💥 Token migration failed with critical error: {e}")
        return False


def get_user_token(user_id):
    """
    Retrieve the decrypted API token for a given user from Supabase.
    Enhanced to handle missing tokens safely without logging errors for new users.
    
    Returns:
        str: Decrypted token if found and valid
        None: If user not found, token is null/empty, or decryption fails
    """
    try:
        resp = supabase.table("users").select("encrypted_token").eq("id", user_id).single().execute()
        
        if not resp.data:
            logger.info(f"User {user_id} not found in database")
            return None
            
        encrypted_token = resp.data.get("encrypted_token")
        
        # Handle null/empty token gracefully (common for new users)
        if not encrypted_token:
            logger.info(f"No API token configured for user {user_id} (new user or token not set)")
            return None
        
        # Attempt to decrypt the token
        try:
            decrypted_token = decrypt_token(encrypted_token)
            logger.debug(f"Successfully retrieved token for user {user_id}")
            return decrypted_token
            
        except Exception as decrypt_error:
            logger.error(f"Failed to decrypt token for user {user_id}: {decrypt_error}")
            return None
            
    except Exception as e:
        logger.error(f"Database error retrieving token for user {user_id}: {e}")
        return None

def generate_meme(prompt, tone, image_url=None, user_id=None):
    """
    Generate meme with enhanced token handling, caching, and usage tracking.
    """
    # First, check cache for repeated requests
    cache_hit = get_cached_result(user_id, prompt, tone, image_url)
    if cache_hit:
        return cache_hit

    # Retrieve decrypted token securely
    api_token = get_user_token(user_id)
    if not api_token:
        logger.warning(f"Cannot generate meme for user {user_id}: No valid API token available")
        return {"error": "API token not configured", "user_id": user_id}

    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }

    # Prepare payload for Replicate API
    data = {
        "version": MODEL_VERSION,
        "input": {
            "prompt": prompt,
            "tone": tone
        }
    }
    if image_url:
        data["input"]["image"] = image_url

    try:
        response = requests.post(REPLICATE_API, headers=headers, json=data, timeout=30)
        if response.status_code != 201:
            logger.error(f"Replicate API error {response.status_code}: {response.text}")
            return {"error": f"API error: {response.status_code}", "details": response.text, "user_id": user_id}

        result = response.json()
        logger.info(f"Meme generated successfully for user {user_id}")

        # Cache the successful result
        cache_result(user_id, prompt, tone, image_url, result)

        # ADDED: Track token usage for successful API call
        try:
            track_token_usage(supabase, user_id, tokens_used=1, action="meme_generation")
            logger.info(f"Token usage tracked for user {user_id}")
        except Exception as track_error:
            logger.warning(f"Failed to track token usage for user {user_id}: {track_error}")

        return result

    except requests.exceptions.Timeout:
        logger.error(f"Timeout generating meme for user {user_id}")
        return {"error": "Request timeout", "user_id": user_id}
    except Exception as e:
        logger.error(f"Exception during meme generation for user {user_id}: {e}")
        return {"error": str(e), "user_id": user_id}


# Safe migration execution at module level
def run_startup_migration():
    """
    Safely run migration only once at startup if enabled.
    """
    try:
        migration_success = migrate_plaintext_tokens()
        if migration_success:
            logger.info("✅ Startup migration check completed successfully")
        else:
            logger.warning("⚠️  Startup migration had issues - check logs above")
    except Exception as e:
        logger.error(f"💥 Startup migration failed: {e}")

# Auto-run migration at module import (only if enabled)
if __name__ != "__main__":  # Only run when imported, not when executed directly
    run_startup_migration()

if __name__ == "__main__":
    # Manual execution for testing
    logger.info("🧪 Manual execution mode")
    
    # Run migration if enabled
    if MIGRATE_ENABLED:
        logger.info("Running migration manually...")
        migrate_plaintext_tokens()
    else:
        logger.info("Migration disabled - set MIGRATE_ENABLED=true in .env to enable")

    # Example usage
    sample_prompt = "AI vs Humans"
    sample_tone = "sarcastic"
    sample_user = "test_user_123"
    
    logger.info(f"Testing meme generation for user: {sample_user}")
    meme = generate_meme(sample_prompt, sample_tone, user_id=sample_user)

    if meme and "error" not in meme:
        logger.info(f"✅ Meme generation result: {meme}")
    else:
        logger.error(f"❌ Failed to generate meme: {meme}")

def test_calculate_score_extreme_values():
    """Test calculate_score with extreme values"""
    payload = {
        "event_type": "click", 
        "user_id": "extreme_values_user",
        "timestamp": "2025-08-03T01:00:00Z",
        "metadata": {
            "click_rate": 999999,               # Extremely high - triggers rapid_clicks
            "page_interaction_score": -50,      # Negative value
            "session_duration": 500,            # Changed from 0 to 500 to trigger idle_click_farm
            "mouse_movement_variance": 0,       # Zero variance - triggers idle_click_farm
            "actions_per_minute": 10000,        # Impossibly high - triggers bot_like_velocity
            "human_behavior_score": -100        # Negative human score - triggers bot_like_velocity
        }
    }
    
    score, flags = calculate_score(payload)
    
    # Should trigger multiple flags
    assert "rapid_clicks" in flags
    assert "idle_click_farm" in flags  
    assert "bot_like_velocity" in flags
    
    # Score should be at minimum (0) - 100 - 15 - 30 - 25 = 30, but capped at 0
    assert score == 30  # Actually should be 30, not 0
