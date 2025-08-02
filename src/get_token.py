import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables from config folder
load_dotenv("config/.env")

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validate that credentials are loaded
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env file")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get test credentials from environment variables (no hardcoding)
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")

if not TEST_EMAIL or not TEST_PASSWORD:
    raise ValueError("TEST_EMAIL and TEST_PASSWORD must be set in config/.env file")

# Sign in and get the auth token
try:
    response = supabase.auth.sign_in_with_password({"email": TEST_EMAIL, "password": TEST_PASSWORD})
    access_token = response.session.access_token
    print("Access Token:", access_token)
except Exception as e:
    print(f"Error getting access token: {e}")
