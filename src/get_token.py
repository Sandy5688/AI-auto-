import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables from config folder
load_dotenv("../config/.env")

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validate that credentials are loaded
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env file")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Use your test user's email and password
email = "materwiler@gmail.com"
password = "futurepilot"

# Sign in and get the auth token
try:
    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
    access_token = response.session.access_token
    print("Access Token:", access_token)
except Exception as e:
    print(f"Error getting access token: {e}")
