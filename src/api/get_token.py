import os
import logging
from datetime import datetime, timezone
from pathlib import Path

from supabase import create_client
from dotenv import load_dotenv
from services.encryption_utils import encrypt_token  # uses src/services/encryption_utils.py

# -----------------------------------------------------------------------------
# Env loading (find config/.env regardless of CWD)
# -----------------------------------------------------------------------------
here = Path(__file__).resolve()
project_root = here.parent.parent  # .../src -> project root
env_path = project_root / "config" / ".env"
load_dotenv(env_path)  # falls back to system env if file missing

# -----------------------------------------------------------------------------
# Logging (no secrets in logs)
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def _mask(s: str, keep: int = 4) -> str:
    """Mask sensitive strings for logs (keep first/last N chars)."""
    if not s:
        return ""
    return s if len(s) <= keep * 2 else f"{s[:keep]}...{s[-keep:]}"

# -----------------------------------------------------------------------------
# Supabase client init (from env)
# -----------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env or environment")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------------------------------------------------------
# Auth & storage helpers
# -----------------------------------------------------------------------------
def get_access_token() -> str | None:
    """
    Get access token for test user.
    Returns:
        str | None: access token (JWT) if success, else None.
    """
    TEST_EMAIL = os.getenv("TEST_EMAIL")
    TEST_PASSWORD = os.getenv("TEST_PASSWORD")

    if not TEST_EMAIL or not TEST_PASSWORD:
        logger.error("TEST_EMAIL and TEST_PASSWORD must be set in config/.env")
        return None

    try:
        logger.info("Attempting to authenticate user: %s", TEST_EMAIL)
        response = supabase.auth.sign_in_with_password({"email": TEST_EMAIL, "password": TEST_PASSWORD})
        access_token = getattr(getattr(response, "session", None), "access_token", None)
        if not access_token:
            logger.error("No access token returned by Supabase")
            return None
        logger.info("✅ Successfully obtained access token")
        return access_token
    except Exception as e:
        logger.error("❌ Authentication failed: %s", e)
        return None

def store_encrypted_token(user_id: str, encrypted_token: str) -> bool:
    """
    Store an already-encrypted access token in the database.

    Args:
        user_id: User identifier (primary key in `users` table)
        encrypted_token: Encrypted token (Fernet base64 string)

    Returns:
        bool: True if upsert succeeded, else False.
    """
    if not user_id:
        logger.error("user_id is required to store encrypted token")
        return False
    if not encrypted_token:
        logger.error("encrypted_token is required to store")
        return False

    try:
        logger.info("Storing encrypted access token for user: %s", user_id)
        token_data = {
            "id": user_id,
            "encrypted_token": encrypted_token,
            "token_updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "token_type": "access_token",
        }
        result = supabase.table("users").upsert(token_data).execute()
        if getattr(result, "data", None):
            logger.info("✅ Encrypted access token stored for user: %s", user_id)
            return True
        logger.error("❌ Upsert returned no data for user: %s", user_id)
        return False
    except Exception as e:
        logger.error("💥 Error storing encrypted token for user %s: %s", user_id, e)
        return False

def get_and_encrypt_token(user_id: str | None = None) -> dict:
    """
    Get access token, encrypt it, and (optionally) store it.

    Args:
        user_id: If provided, upsert encrypted token into `users` table with this id.

    Returns:
        dict: {
          success, access_token, encrypted_token, stored, user_id, timestamp, error?
        }
    """
    result = {
        "success": False,
        "access_token": None,       # raw token (string) — do NOT log this
        "encrypted_token": None,    # encrypted token (string)
        "stored": False,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    try:
        access_token = get_access_token()
        if not access_token:
            result["error"] = "Failed to obtain access token"
            return result

        result["access_token"] = access_token
        result["success"] = True

        # Encrypt the token once here
        try:
            encrypted_token = encrypt_token(access_token)
            result["encrypted_token"] = encrypted_token
            logger.info("🔐 Access token encrypted successfully")
        except Exception as encrypt_error:
            logger.warning("Failed to encrypt token: %s", encrypt_error)
            result["encrypt_error"] = str(encrypt_error)

        # Optionally store encrypted token
        if user_id and result["encrypted_token"]:
            stored = store_encrypted_token(user_id, result["encrypted_token"])
            result["stored"] = stored
            if stored:
                logger.info("🎯 token obtained → encrypted → stored (user=%s)", user_id)
            else:
                logger.warning("⚠️  Token obtained and encrypted but storage failed (user=%s)", user_id)
        elif user_id:
            logger.warning("⚠️  Cannot store token for user %s: encryption failed", user_id)
        else:
            logger.info("ℹ️  Token obtained and encrypted, not stored (no user_id)")

        return result

    except Exception as e:
        logger.error("💥 Unexpected error in get_and_encrypt_token: %s", e)
        result["error"] = str(e)
        return result

# -----------------------------------------------------------------------------
# CLI self-run (safe: never prints full token)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("🔑 Starting enhanced token retrieval and encryption process...")

    # Example 1: Just get token (masked preview)
    logger.info("\n--- Example 1: Basic token retrieval ---")
    token = get_access_token()
    if token:
        logger.info("Raw Access Token (masked): %s", _mask(token))

    # Example 2: Get, encrypt, and store token
    logger.info("\n--- Example 2: Full encrypted token flow ---")
    test_user_id = "test_user_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    result = get_and_encrypt_token(user_id=test_user_id)

    logger.info("🎯 Final Result Summary:")
    logger.info("  Success: %s", result["success"])
    logger.info("  Token obtained: %s", "Yes" if result["access_token"] else "No")
    logger.info("  Token encrypted: %s", "Yes" if result["encrypted_token"] else "No")
    logger.info("  Token stored: %s", "Yes" if result["stored"] else "No")

    if result.get("error"):
        logger.error("  Error: %s", result["error"])

    logger.info("Token processing completed")
