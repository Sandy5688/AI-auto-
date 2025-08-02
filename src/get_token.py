import os
import logging
from supabase import create_client
from dotenv import load_dotenv
from encryption_utils import encrypt_token
from datetime import datetime, timezone

# Dynamically find the config/.env file
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, "config", ".env")

load_dotenv(env_path)

# UNIFIED LOGGING FORMAT
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validate that credentials are loaded
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env file")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_access_token():
    """
    Get access token for test user.
    Returns the access token or None if authentication fails.
    """
    # Get test credentials from environment variables
    TEST_EMAIL = os.getenv("TEST_EMAIL")
    TEST_PASSWORD = os.getenv("TEST_PASSWORD")

    if not TEST_EMAIL or not TEST_PASSWORD:
        logger.error("TEST_EMAIL and TEST_PASSWORD must be set in config/.env file")
        return None

    try:
        logger.info(f"Attempting to authenticate user: {TEST_EMAIL}")
        response = supabase.auth.sign_in_with_password({"email": TEST_EMAIL, "password": TEST_PASSWORD})
        access_token = response.session.access_token
        logger.info("✅ Successfully obtained access token")
        return access_token
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        return None

def store_encrypted_token(user_id: str, access_token: str) -> bool:
    """
    Store encrypted access token in the database.
    
    Args:
        user_id: User identifier
        access_token: Raw access token to encrypt and store
        
    Returns:
        bool: True if stored successfully, False otherwise
    """
    try:
        logger.info(f"Encrypting and storing access token for user: {user_id}")
        
        # Encrypt the access token
        encrypted_token = encrypt_token(access_token)
        logger.info("🔐 Access token encrypted successfully")
        
        # Prepare data for database
        token_data = {
            "id": user_id,
            "encrypted_token": encrypted_token,
            "token_updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "token_type": "access_token"
        }
        
        # Store in database
        result = supabase.table("users").upsert(token_data).execute()
        
        if result.data:
            logger.info(f"✅ Encrypted access token stored successfully for user: {user_id}")
            return True
        else:
            logger.error(f"❌ Failed to store encrypted token for user: {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Error storing encrypted token for user {user_id}: {e}")
        return False

def get_and_encrypt_token(user_id: str = None) -> dict:
    """
    Get access token and encrypt it for storage.
    
    Args:
        user_id: Optional user ID for storage. If None, uses email as ID.
        
    Returns:
        dict: Result with token info and storage status
    """
    result = {
        "success": False,
        "access_token": None,
        "encrypted_token": None,
        "stored": False,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Get the access token
        access_token = get_access_token()
        
        if not access_token:
            result["error"] = "Failed to obtain access token"
            return result
        
        result["access_token"] = access_token
        result["success"] = True
        
        # Encrypt the token
        try:
            encrypted_token = encrypt_token(access_token)
            result["encrypted_token"] = encrypted_token
            logger.info("🔐 Access token encrypted successfully")
        except Exception as encrypt_error:
            logger.warning(f"Failed to encrypt token: {encrypt_error}")
            result["encrypt_error"] = str(encrypt_error)
        
        # Store encrypted token if user_id provided
        if user_id and result["encrypted_token"]:
            stored = store_encrypted_token(user_id, access_token)
            result["stored"] = stored
            
            if stored:
                logger.info(f"🎯 Complete flow successful for user {user_id}: token obtained → encrypted → stored")
            else:
                logger.warning(f"⚠️  Token obtained and encrypted but storage failed for user {user_id}")
        elif user_id:
            logger.warning(f"⚠️  Cannot store token for user {user_id}: encryption failed")
        else:
            logger.info("ℹ️  Token obtained and encrypted, but not stored (no user_id provided)")
        
        return result
        
    except Exception as e:
        logger.error(f"💥 Unexpected error in get_and_encrypt_token: {e}")
        result["error"] = str(e)
        return result

# MOVED UNDER MAIN BLOCK
if __name__ == "__main__":
    logger.info("🔑 Starting enhanced token retrieval and encryption process...")
    
    # Example 1: Just get and display token (original behavior)
    logger.info("\n--- Example 1: Basic token retrieval ---")
    token = get_access_token()
    if token:
        logger.info(f"Raw Access Token: {token[:20]}...{token[-10:]}")  # Show partial token
    
    # Example 2: Get, encrypt, and store token
    logger.info("\n--- Example 2: Full encrypted token flow ---")
    test_user_id = "test_user_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    result = get_and_encrypt_token(user_id=test_user_id)
    
    logger.info("🎯 Final Result Summary:")
    logger.info(f"  Success: {result['success']}")
    logger.info(f"  Token obtained: {'Yes' if result['access_token'] else 'No'}")
    logger.info(f"  Token encrypted: {'Yes' if result['encrypted_token'] else 'No'}")
    logger.info(f"  Token stored: {'Yes' if result['stored'] else 'No'}")
    
    if result.get('error'):
        logger.error(f"  Error: {result['error']}")
    
    logger.info("Token processing completed")
