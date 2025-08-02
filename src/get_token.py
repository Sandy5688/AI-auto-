import os
import logging
from supabase import create_client
from dotenv import load_dotenv

# Dynamically find the config/.env file regardless of current working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up from src/ to project root
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

# MOVED UNDER MAIN BLOCK
if __name__ == "__main__":
    logger.info("🔑 Starting token retrieval process...")
    
    token = get_access_token()
    if token:
        logger.info(f"Access Token: {token}")
        logger.info("Token retrieval completed successfully")
    else:
        logger.error("Failed to retrieve access token")
