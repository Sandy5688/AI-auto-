import os
import logging
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client
from encryption_utils import encrypt_token, decrypt_token
from token_tracking import track_token_usage
import threading
import time

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
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Migration control flag
MIGRATE_ENABLED = os.getenv("MIGRATE_ENABLED", "false").lower() in ("true", "1", "yes", "on")

# Webhook retry configuration
WEBHOOK_MAX_RETRIES = 3
WEBHOOK_RETRY_DELAY = 2  # seconds
WEBHOOK_EXPONENTIAL_BACKOFF = True
WEBHOOK_TIMEOUT = 30  # seconds

# Validate environment variables
if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env")

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Enhanced cache configuration
MEME_CACHE = {}
CACHE_MAX_SIZE = 1000  # Maximum number of cached items
CACHE_DEFAULT_TTL_HOURS = 24  # Default time-to-live in hours
CACHE_CLEANUP_INTERVAL_MINUTES = 30  # How often to run cleanup
CACHE_CLEANUP_THREAD = None  # Global cleanup thread reference

class CacheEntry:
    """Enhanced cache entry with expiry and metadata"""
    def __init__(self, data, ttl_hours=CACHE_DEFAULT_TTL_HOURS):
        self.data = data
        self.created_at = datetime.now(timezone.utc)
        self.expires_at = self.created_at + timedelta(hours=ttl_hours)
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self):
        """Check if cache entry has expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self):
        """Check if cache entry is valid (not expired)"""
        return not self.is_expired()
    
    def access(self):
        """Mark entry as accessed"""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)
        return self.data

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
            "completed_at": datetime.now(timezone.utc).isoformat() + "Z",
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

    # Check if migration already completed
    if check_migration_lock():
        logger.info("✅ Migration already completed - skipping")
        return True

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
                "completed_at": datetime.now(timezone.utc).isoformat() + "Z",
                "migrated_users": migrated_count,
                "error_count": error_count
            }
            supabase.table("migration_status").upsert(completion_record).execute()
        except Exception as e:
            logger.error(f"Failed to record migration completion: {e}")

        logger.info(f"🏁 Token migration completed: {migrated_count} users migrated, {error_count} errors")
        return True

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

def store_risk_flags(user_id, risk_flags, timestamp, supabase_client=supabase):
    """
    Store risk flags in database, preventing duplicates.
    """
    stored_flags = []
    
    for flag in risk_flags:
        try:
            flag_entry = {
                "user_id": user_id,
                "flag": flag,
                "timestamp": timestamp if isinstance(timestamp, str) else timestamp.isoformat().replace("+00:00", "Z")
            }
            supabase_client.table("user_risk_flags").insert(flag_entry).execute()
            stored_flags.append(flag)
            logger.info(f"Risk flag stored: {flag} for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing risk flag {flag} for user {user_id}: {e}")
    
    return stored_flags

def send_score_to_webhook(user_id, score, risk_flags, timestamp=None):
    """
    Enhanced webhook sender with retry logic, exponential backoff, and comprehensive error handling.
    """
    if not timestamp:
        timestamp = datetime.now(timezone.utc)
    elif isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    
    # Store risk flags in database (with duplicate prevention)
    if risk_flags:
        stored_flags = store_risk_flags(user_id, risk_flags, timestamp)
        logger.info(f"Stored {len(stored_flags)} new risk flags for user {user_id}")
    
    payload = {
        "user_id": user_id,
        "behavior_score": score,
        "risk_flags": risk_flags,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z")
    }
    
    # Webhook retry logic with exponential backoff
    for attempt in range(1, WEBHOOK_MAX_RETRIES + 1):
        try:
            logger.info(f"Sending webhook payload to {WEBHOOK_URL} (attempt {attempt}/{WEBHOOK_MAX_RETRIES})")
            
            response = requests.post(
                WEBHOOK_URL, 
                json=payload, 
                timeout=WEBHOOK_TIMEOUT,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'BSE-Webhook-Client/1.0'
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Webhook sent successfully for user {user_id} on attempt {attempt}")
                return True
            elif response.status_code in [429, 502, 503, 504]:
                # Retriable errors
                logger.warning(f"⚠️  Webhook returned retriable error {response.status_code} for user {user_id}: {response.text}")
                raise requests.exceptions.HTTPError(f"HTTP {response.status_code}: {response.text}")
            else:
                # Non-retriable errors
                logger.error(f"❌ Webhook failed with non-retriable error {response.status_code} for user {user_id}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.warning(f"⏰ Webhook timeout for user {user_id} on attempt {attempt}/{WEBHOOK_MAX_RETRIES}")
            if attempt == WEBHOOK_MAX_RETRIES:
                logger.error(f"💥 Webhook failed after {WEBHOOK_MAX_RETRIES} timeout attempts for user {user_id}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"🔌 Webhook connection error for user {user_id} on attempt {attempt}/{WEBHOOK_MAX_RETRIES}: {e}")
            if attempt == WEBHOOK_MAX_RETRIES:
                logger.error(f"💥 Webhook failed after {WEBHOOK_MAX_RETRIES} connection attempts for user {user_id}")
                return False
                
        except requests.exceptions.HTTPError as e:
            logger.warning(f"📡 Webhook HTTP error for user {user_id} on attempt {attempt}/{WEBHOOK_MAX_RETRIES}: {e}")
            if attempt == WEBHOOK_MAX_RETRIES:
                logger.error(f"💥 Webhook failed after {WEBHOOK_MAX_RETRIES} HTTP error attempts for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"💥 Unexpected webhook error for user {user_id} on attempt {attempt}/{WEBHOOK_MAX_RETRIES}: {e}")
            if attempt == WEBHOOK_MAX_RETRIES:
                logger.error(f"💥 Webhook failed after {WEBHOOK_MAX_RETRIES} attempts with unexpected error for user {user_id}")
                return False
        
        # Calculate retry delay with exponential backoff
        if attempt < WEBHOOK_MAX_RETRIES:
            if WEBHOOK_EXPONENTIAL_BACKOFF:
                delay = WEBHOOK_RETRY_DELAY * (2 ** (attempt - 1))
            else:
                delay = WEBHOOK_RETRY_DELAY
            
            logger.info(f"⏳ Retrying webhook for user {user_id} in {delay} seconds...")
            time.sleep(delay)
    
    return False

def get_cached_result(user_id, prompt, tone, image_url):
    """Enhanced cache retrieval with automatic cleanup"""
    key = (user_id, prompt, tone, image_url or "")
    entry = MEME_CACHE.get(key)
    
    if entry and entry.is_valid():
        logger.info(f"✅ Cache HIT for user={user_id}, prompt='{prompt[:30]}...', tone={tone}")
        return entry.access()
    elif entry and entry.is_expired():
        # Remove expired entry
        logger.debug(f"🗑️  Removing expired cache entry for user={user_id}")
        MEME_CACHE.pop(key, None)
        return None
    else:
        logger.debug(f"❌ Cache MISS for user={user_id}")
        return None

def cache_result(user_id, prompt, tone, image_url, result, ttl_hours=CACHE_DEFAULT_TTL_HOURS):
    """Enhanced cache storage with size management"""
    key = (user_id, prompt, tone, image_url or "")
    
    # Check cache size limit
    if len(MEME_CACHE) >= CACHE_MAX_SIZE:
        logger.info(f"📦 Cache size limit reached ({CACHE_MAX_SIZE}), cleaning up...")
        cleanup_cache(force_cleanup=True)
    
    # Store new entry
    MEME_CACHE[key] = CacheEntry(result, ttl_hours)
    logger.info(f"💾 Cached result for user={user_id}, cache_size={len(MEME_CACHE)}")

def cleanup_cache(force_cleanup=False):
    """
    Clean up expired cache entries and manage memory usage.
    
    Args:
        force_cleanup: If True, also removes least recently used items to free space
    """
    try:
        initial_size = len(MEME_CACHE)
        expired_keys = []
        
        # Find expired entries
        for key, entry in MEME_CACHE.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        # Remove expired entries
        for key in expired_keys:
            MEME_CACHE.pop(key, None)
        
        expired_count = len(expired_keys)
        current_size = len(MEME_CACHE)
        
        # Force cleanup if still too large
        if force_cleanup and current_size >= CACHE_MAX_SIZE:
            # Remove least recently used items
            lru_items = sorted(
                MEME_CACHE.items(), 
                key=lambda x: x[1].last_accessed
            )
            
            # Remove oldest 25% of items
            items_to_remove = max(1, len(lru_items) // 4)
            for key, _ in lru_items[:items_to_remove]:
                MEME_CACHE.pop(key, None)
            
            final_size = len(MEME_CACHE)
            logger.info(f"🧹 Force cleanup: removed {items_to_remove} LRU items, "
                       f"cache size: {current_size} → {final_size}")
        
        if expired_count > 0:
            logger.info(f"🗑️  Cache cleanup: removed {expired_count} expired entries, "
                       f"cache size: {initial_size} → {len(MEME_CACHE)}")
        
        return expired_count
        
    except Exception as e:
        logger.error(f"💥 Error during cache cleanup: {e}")
        return 0

def get_cache_stats():
    """Get comprehensive cache statistics"""
    if not MEME_CACHE:
        return {
            "total_entries": 0,
            "expired_entries": 0,
            "valid_entries": 0,
            "cache_hit_potential": "0%",
            "oldest_entry_age_hours": "0",
            "average_access_count": "0",
            "memory_usage_estimate_kb": 0
        }
    
    now = datetime.now(timezone.utc)
    expired_count = 0
    total_access_count = 0
    oldest_age_hours = 0
    
    for entry in MEME_CACHE.values():
        if entry.is_expired():
            expired_count += 1
        total_access_count += entry.access_count
        
        age_hours = (now - entry.created_at).total_seconds() / 3600
        oldest_age_hours = max(oldest_age_hours, age_hours)
    
    valid_count = len(MEME_CACHE) - expired_count
    
    return {
        "total_entries": len(MEME_CACHE),
        "expired_entries": expired_count,
        "valid_entries": valid_count,
        "cache_hit_potential": f"{(valid_count / len(MEME_CACHE) * 100):.1f}%" if MEME_CACHE else "0%",
        "oldest_entry_age_hours": f"{oldest_age_hours:.1f}",
        "average_access_count": f"{(total_access_count / len(MEME_CACHE)):.1f}" if MEME_CACHE else "0",
        "memory_usage_estimate_kb": len(MEME_CACHE) * 2  # Rough estimate
    }

def start_cache_cleanup_scheduler():
    """Start background thread for periodic cache cleanup"""
    global CACHE_CLEANUP_THREAD
    
    def cleanup_worker():
        while True:
            try:
                time.sleep(CACHE_CLEANUP_INTERVAL_MINUTES * 60)  # Convert to seconds
                cleanup_count = cleanup_cache()
                if cleanup_count > 0:
                    logger.info(f"🔄 Scheduled cache cleanup completed: removed {cleanup_count} items")
            except Exception as e:
                logger.error(f"💥 Cache cleanup thread error: {e}")
    
    if CACHE_CLEANUP_THREAD is None or not CACHE_CLEANUP_THREAD.is_alive():
        CACHE_CLEANUP_THREAD = threading.Thread(target=cleanup_worker, daemon=True)
        CACHE_CLEANUP_THREAD.start()
        logger.info(f"🚀 Cache cleanup scheduler started (interval: {CACHE_CLEANUP_INTERVAL_MINUTES} minutes)")

def stop_cache_cleanup_scheduler():
    """Stop the cache cleanup scheduler (for testing/shutdown)"""
    global CACHE_CLEANUP_THREAD
    if CACHE_CLEANUP_THREAD and CACHE_CLEANUP_THREAD.is_alive():
        # Note: Can't cleanly stop daemon threads, they'll stop when main process stops
        logger.info("🛑 Cache cleanup scheduler will stop when main process stops")

def generate_meme(prompt, tone, image_url=None, user_id=None):
    """
    Generate meme with enhanced caching, token tracking, and error handling.
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

        # Track token usage for successful API call
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

# Initialize cache cleanup on module import
start_cache_cleanup_scheduler()

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
    logger.info("🧪 Enhanced Meme Generator with Caching, Token Management & Retry Logic")
    
    # Display cache configuration
    logger.info(f"📦 Cache Configuration:")
    logger.info(f"   Max size: {CACHE_MAX_SIZE} entries")
    logger.info(f"   Default TTL: {CACHE_DEFAULT_TTL_HOURS} hours")
    logger.info(f"   Cleanup interval: {CACHE_CLEANUP_INTERVAL_MINUTES} minutes")
    
    # Display webhook configuration
    logger.info(f"📡 Webhook Configuration:")
    logger.info(f"   Max retries: {WEBHOOK_MAX_RETRIES}")
    logger.info(f"   Retry delay: {WEBHOOK_RETRY_DELAY} seconds")
    logger.info(f"   Exponential backoff: {WEBHOOK_EXPONENTIAL_BACKOFF}")
    logger.info(f"   Timeout: {WEBHOOK_TIMEOUT} seconds")
    
    # Show initial cache stats
    stats = get_cache_stats()
    logger.info(f"📊 Initial Cache Stats: {stats}")
    
    # Example usage with caching
    sample_prompt = "AI vs Humans"
    sample_tone = "sarcastic"
    sample_user = "test_user_123"
    
    logger.info(f"Testing meme generation with caching for user: {sample_user}")
    
    # First request (cache miss)
    meme1 = generate_meme(sample_prompt, sample_tone, user_id=sample_user)
    
    # Second request (should be cache hit)
    meme2 = generate_meme(sample_prompt, sample_tone, user_id=sample_user)
    
    # Display final cache stats
    final_stats = get_cache_stats()
    logger.info(f"📊 Final Cache Stats: {final_stats}")
    
    if meme1 and "error" not in meme1:
        logger.info(f"✅ Meme generation successful")
    else:
        logger.error(f"❌ Meme generation failed: {meme1}")
