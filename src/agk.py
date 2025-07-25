import os
import logging
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
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
        role = user.get("role", None)  # Optional: process role as needed
        is_anonymous = user.get("is_anonymous", False)  # Optional

        logger.info(f"User {user_id} behavior score: {behavior_score}, role: {role}, anonymous: {is_anonymous}")

        if behavior_score < 60:
            logger.info(f"Access denied for user {user_id} due to low behavior score.")
            return False

        # Add any other access policies based on role or is_anonymous if needed here

        logger.info(f"Access granted for user {user_id}.")
        return True

    except Exception as e:
        logger.error(f"Error validating access for user {user_id}: {e}")
        return False


# Example usage (for local testing)
if __name__ == "__main__":
    test_user_id = "abc123"
    access = validate_access(test_user_id)
    print(f"Access for user {test_user_id}: {access}")
