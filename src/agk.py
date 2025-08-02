import os
import logging
from supabase import create_client
from dotenv import load_dotenv

# Dynamically find the config/.env file
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, "config", ".env")

load_dotenv(env_path)

# UNIFIED LOGGING FORMAT
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def validate_access(user_id, supabase_client=supabase):
    """
    Validate access based on user behavior score and other token claims.
    Access denied if behavior_score < 60.
    """
    try:
        resp = supabase_client.table("users").select("behavior_score, role, is_anonymous").eq("id", user_id).single().execute()
        user = resp.data
        if not user:
            logger.warning(f"User {user_id} not found in users table.")
            return False

        behavior_score = user.get("behavior_score", 0)
        role = user.get("role", None)
        is_anonymous = user.get("is_anonymous", False)

        logger.info(f"User {user_id} behavior score: {behavior_score}, role: {role}, anonymous: {is_anonymous}")

        if behavior_score < 60:
            logger.info(f"Access denied for user {user_id} due to low behavior score.")
            return False

        logger.info(f"Access granted for user {user_id}.")
        return True

    except Exception as e:
        logger.error(f"Error validating access for user {user_id}: {e}")
        return False

# MOVED UNDER MAIN BLOCK
if __name__ == "__main__":
    logger.info("🔐 Testing access validation...")
    
    test_user_id = "abc123"
    access = validate_access(test_user_id)
    
    if access:
        logger.info(f"✅ Access granted for user {test_user_id}")
    else:
        logger.info(f"❌ Access denied for user {test_user_id}")
