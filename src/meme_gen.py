import os
import requests
from datetime import datetime, timezone
from supabase import create_client
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Debug prints to verify tokens
print(f"REPLICATE_API_TOKEN: {REPLICATE_API_TOKEN}")
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Store generation attempt in Supabase
def store_meme(user_id, prompt, tone, image_url, token_used):
    data = {
        "user_id": user_id,
        "prompt": prompt,
        "tone": tone,
        "image_url": image_url,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "token_used": token_used,
        "used_in_nft": False
    }
    supabase.table("generated_memes").insert(data).execute()

# Check retry limits
def check_retry_limit(user_id, max_retries=3):
    response = supabase.table("generated_memes").select("timestamp").eq("user_id", user_id).execute()
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_attempts = sum(1 for entry in response.data if datetime.fromisoformat(entry["timestamp"]) >= today)
    return daily_attempts < max_retries

# Generate meme using Replicate API
def generate_meme(prompt, tone, image_url=None):
    headers = {"Authorization": f"Token {REPLICATE_API_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "version": "prompthero/openjourney-v4:e8818682e72a8b25895c7d90e889b712b6edfc5151f145e3606f21c1e85c65bf",
        "input": {"prompt": f"{prompt} in {tone} style", "image": image_url}
    }
    response = requests.post(REPLICATE_API, headers=headers, json=payload)
    print(f"API Response Status: {response.status_code}")  # Debug print
    print(f"API Response Text: {response.text}")  # Debug print
    if response.status_code == 201:
        result = response.json()
        return result.get("output")  # URL or generated image data
    return None

# Handle generation request
def handle_meme_request(request_data):
    user_id = request_data.get("user_id")
    prompt = request_data.get("text_input")
    tone = request_data.get("meme_type", "sarcastic")
    image_url = request_data.get("image_url")

    if not check_retry_limit(user_id):
        return {"status": "error", "message": "Daily retry limit exceeded"}

    image_url = generate_meme(prompt, tone, image_url)
    if image_url:
        store_meme(user_id, prompt, tone, image_url, token_used=1)  # Mock token usage
        return {"status": "success", "image_url": image_url}
    return {"status": "error", "message": "Failed to generate meme"}

# Example usage
sample_request = {
    "user_id": "abc123",
    "text_input": "AI vs Humans",
    "meme_type": "sarcastic",
    "image_url": None
}

if __name__ == "__main__":
    response = handle_meme_request(sample_request)
    print(response)