import requests
import hmac
import hashlib
import json
import os
from dotenv import load_dotenv

# Load from the correct path - adjust based on where you put this file
load_dotenv("config/.env")  # If file is in project root
# OR
# load_dotenv("../config/.env")  # If file is in tests folder

WEBHOOK_URL = "http://localhost:5001/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")
AUTH_METHOD = os.getenv("WEBHOOK_AUTH_METHOD", "signature")

# Add validation to make sure secrets are loaded
if not WEBHOOK_SECRET:
    print("❌ ERROR: WEBHOOK_SECRET not found in .env file")
    exit(1)

if not WEBHOOK_TOKEN:
    print("❌ ERROR: WEBHOOK_TOKEN not found in .env file") 
    exit(1)

print(f"✅ Loaded secrets - Secret: {WEBHOOK_SECRET[:8]}..., Token: {WEBHOOK_TOKEN[:8]}...")

def test_signature_auth():
    """Test webhook with signature authentication"""
    payload = {
        "user_id": "test_user_123",
        "behavior_score": 75,
        "risk_flags": ["test_flag"],
        "timestamp": "2025-08-03T12:00:00Z"
    }
    
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    
    # Generate signature
    signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}"
    }
    
    print(f"🔐 Testing signature authentication...")
    print(f"Payload: {payload_json}")
    print(f"Signature: sha256={signature}")
    
    response = requests.post(WEBHOOK_URL, data=payload_bytes, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.status_code == 200

def test_token_auth():
    """Test webhook with token authentication"""
    payload = {
        "user_id": "test_user_456",
        "behavior_score": 80,
        "risk_flags": ["test_flag"],
        "timestamp": "2025-08-03T12:00:00Z"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WEBHOOK_TOKEN}"
    }
    
    print(f"🔑 Testing token authentication...")
    print(f"Token: Bearer {WEBHOOK_TOKEN[:8]}...")
    
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.status_code == 200

def test_no_auth():
    """Test webhook without authentication (should fail)"""
    payload = {
        "user_id": "test_user_789",
        "behavior_score": 85,
        "risk_flags": [],
        "timestamp": "2025-08-03T12:00:00Z"
    }
    
    headers = {"Content-Type": "application/json"}
    
    print(f"❌ Testing without authentication (should fail)...")
    
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.status_code == 401

def test_invalid_auth():
    """Test webhook with invalid authentication (should fail)"""
    payload = {
        "user_id": "test_user_999",
        "behavior_score": 90,
        "risk_flags": [],
        "timestamp": "2025-08-03T12:00:00Z"
    }
    
    if AUTH_METHOD == "signature":
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": "sha256=invalid_signature"
        }
    else:
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_token"
        }
    
    print(f"🚫 Testing with invalid authentication (should fail)...")
    
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.status_code == 401

if __name__ == "__main__":
    print("🧪 Webhook Authentication Tests")
    print(f"Using {AUTH_METHOD} authentication method")
    print("-" * 50)
    
    # Test valid authentication
    if AUTH_METHOD == "signature":
        success = test_signature_auth()
    else:
        success = test_token_auth()
    
    print("-" * 50)
    
    # Test security (should fail)
    test_no_auth()
    print("-" * 30)
    test_invalid_auth()
    
    print("-" * 50)
    print(f"✅ Authentication test: {'PASSED' if success else 'FAILED'}")
