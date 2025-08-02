import os
from dotenv import load_dotenv

load_dotenv("config/.env")

REQUIRED_VARS = [
    "SUPABASE_URL",
    "SUPABASE_KEY", 
    "WEBHOOK_URL",
    "TOKEN_ENCRYPTION_KEY",
    "REPLICATE_API_TOKEN",
    "REPLICATE_MODEL_VERSION"
]

OPTIONAL_VARS = [
    "TEST_EMAIL",
    "TEST_PASSWORD",
    "OPENAI_API_KEY"
]

def validate_environment():
    missing_required = []
    missing_optional = []
    
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in OPTIONAL_VARS:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        print("❌ CRITICAL: Missing required environment variables:")
        for var in missing_required:
            print(f"   - {var}")
        return False
    
    if missing_optional:
        print("⚠️  WARNING: Missing optional environment variables:")
        for var in missing_optional:
            print(f"   - {var}")
    
    print("✅ All required environment variables are set!")
    return True

if __name__ == "__main__":
    validate_environment()
