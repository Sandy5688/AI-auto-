from supabase import create_client

# Replace these with your actual values
SUPABASE_URL = "https://hlphvrulcwlahwifmeur.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhscGh2cnVsY3dsYWh3aWZtZXVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE5OTM1NzQsImV4cCI6MjA2NzU2OTU3NH0._hPUFuM8OlKUSP2R093ZeNFr8WIpI2aJkygMeOkAb6A"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Use your test user’s email and password
email = "materwiler@gmail.com"
password = "futurepilot"

# Sign in and get the auth token
response = supabase.auth.sign_in_with_password({"email": email, "password": password})
access_token = response.session.access_token
print("Access Token:", access_token)