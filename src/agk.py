import os
from supabase import create_client
import requests

# Supabase setup (replace with your credentials)
SUPABASE_URL = "https://hlphvrulcwlahwifmeur.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhscGh2cnVsY3dsYWh3aWZtZXVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE5OTM1NzQsImV4cCI6MjA2NzU2OTU3NH0._hPUFuM8OlKUSP2R093ZeNFr8WIpI2aJkygMeOkAb6A"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Function to validate user access
def validate_access(auth_token, user_id):
    try:
        # Verify the auth token with Supabase
        user = supabase.auth.get_user(auth_token)
        if user:
            # Placeholder for additional checks (e.g., behavior score, risk flags)
            # For now, assume access is granted if token is valid
            return True
        return False
    except Exception as e:
        print(f"Error validating access: {e}")
        return False

# Function to handle content generation requests
def handle_generation_request(request_data):
    auth_token = request_data.get('auth_token')
    user_id = request_data.get('user_id')
    if validate_access(auth_token, user_id):
        # Proceed with content generation (we’ll add this later)
        return {"status": "success", "message": "Access granted"}
    else:
        return {"status": "error", "message": "Access denied due to unusual activity. Please try again later or verify your account."}

# Example request data
sample_request = {
    "auth_token": "eyJhbGciOiJIUzI1NiIsImtpZCI6InN6NHo0eURyVndGdEp5dVAiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2hscGh2cnVsY3dsYWh3aWZtZXVyLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJmNGM2ZjFhYy0yYWU0LTQ2NzUtYWUwZS04M2U5MjA5ZWZkOTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzUyMDAwNjk5LCJpYXQiOjE3NTE5OTcwOTksImVtYWlsIjoibWF0ZXJ3aWxlckBnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc1MTk5NzA5OX1dLCJzZXNzaW9uX2lkIjoiODBlZjhhZWYtYzVlNi00OTVlLWIwZTAtNWY5MGFiMzc2NjliIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.82nDiaXztMbRUb3RTdazGnb3LBielukipXv-mPFoSGw",  # Replace with a real token for testing
    "user_id": "abc123",
    "meme_type": "sarcastic",
    "text_input": "AI vs Humans"
}

# Test the access validation
response = handle_generation_request(sample_request)
print(response)