import os
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
from encryption_utils import encrypt_token, decrypt_token
from token_tracking import track_token_usage

# Load environment variables
load_dotenv("config/.env")

# Configuration constants
REPLICATE_API = "https://api.replicate.com/v1/predictions"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MODEL_VERSION = os.getenv("REPLICATE_MODEL_VERSION")

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

def migrate_plaintext_tokens():
    """
    This function migrates legacy plaintext tokens stored in 'users.encrypted_token' column by:
    1) Scanning all users.
    2) Identifying users with plaintext tokens (e.g., stored in 'token' or old column).
    3) Encrypting the plaintext token.
    4) Updating the record with the encrypted token and removing plaintext (optional).
    """
    logger.info("Starting legacy token migration")
    try:
        # Fetch users with potential plaintext tokens
        # Assuming legacy tokens were stored in `token` column, adjust as needed
        users = supabase.table("users").select("id, token, encrypted_token").execute().data
        migrated_count = 0
        for user in users:
            user_id = user.get("id")
            plaintext_token = user.get("token")
            encrypted_token = user.get("encrypted_token")

            # If user has plaintext token and no encrypted token yet
            if plaintext_token and not encrypted_token:
                logger.info(f"Migrating token for user {user_id}")
                encrypted = encrypt_token(plaintext_token)
                # Update encrypted_token and nullify plaintext for security
                supabase.table("users").update({
                    "encrypted_token": encrypted,
                    "token": None  # Optional: remove plaintext token after migration
                }).eq("id", user_id).execute()
                migrated_count += 1

        logger.info(f"Legacy token migration completed. Tokens migrated for {migrated_count} users.")
    except Exception as e:
        logger.error(f"Failed token migration: {e}")

def get_user_token(user_id):
    """
    Retrieve the decrypted API token for a given user from Supabase.
    Returns None if token is missing or cannot be decrypted.
    """
    try:
        resp = supabase.table("users").select("encrypted_token").eq("id", user_id).single().execute()
        if resp.data and resp.data.get("encrypted_token"):
            decrypted_token = decrypt_token(resp.data["encrypted_token"])
            return decrypted_token
        else:
            logger.warning(f"No encrypted_token found for user {user_id}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving/decrypting token for user {user_id}: {e}")
        return None

def generate_meme(prompt, tone, image_url=None, user_id=None):
    # First, check cache for repeated requests
    cache_hit = get_cached_result(user_id, prompt, tone, image_url)
    if cache_hit:
        return cache_hit

    # Retrieve decrypted token securely
    api_token = get_user_token(user_id)
    if not api_token:
        logger.error(f"API token missing or invalid for user {user_id}")
        return None

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
        response = requests.post(REPLICATE_API, headers=headers, json=data)
        if response.status_code != 201:
            logger.error(f"Replicate API error {response.status_code}: {response.text}")
            return None

        result = response.json()
        logger.info(f"Meme generated successfully for user {user_id}")

        # Cache the successful result to avoid repeated calls for same input
        cache_result(user_id, prompt, tone, image_url, result)

        # Token usage tracking logic should go here (already implemented)

        return result

    except Exception as e:
        logger.error(f"Exception during meme generation: {e}")
        return None


if __name__ == "__main__":
    # Run legacy token migration once at startup or trigger manually
    migrate_plaintext_tokens()

    # Example usage
    sample_prompt = "AI vs Humans"
    sample_tone = "sarcastic"
    sample_user = "abc123"
    meme = generate_meme(sample_prompt, sample_tone, user_id=sample_user)

    if meme:
        logger.info(f"Meme generation result: {meme}")
    else:
        logger.error("Failed to generate meme")
