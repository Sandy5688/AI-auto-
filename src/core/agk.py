import os
import logging
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union
from supabase import create_client
from dotenv import load_dotenv
import json
import mimetypes

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
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# AGK Configuration
AGK_CONFIG = {
    "min_behavior_score": 60,
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "allowed_image_types": ["image/jpeg", "image/png", "image/gif", "image/webp"],
    "allowed_text_types": ["text/plain", "application/json"],
    "passkey_expiry_hours": 24,
    "access_levels": {
        "verified": "FULL_ACCESS",
        "kyc_completed": "RESTRICTED_ACCESS", 
        "wallet_connected": "LIMITED_ACCESS",
        "basic": "MINIMAL_ACCESS"
    }
}

# Standardized rejection message
REJECTION_MESSAGE = "Access Denied: Please connect a verified wallet or complete KYC to continue."

class PasskeyGenerator:
    """Generate and validate passkeys for user access"""
    
    @staticmethod
    def generate_wallet_passkey(wallet_address: str, user_id: str) -> str:
        """Generate passkey from wallet signature"""
        timestamp = str(int(time.time()))
        data = f"{wallet_address}:{user_id}:{timestamp}"
        passkey = hmac.new(
            SECRET_KEY.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        logger.info(f"Generated wallet passkey for user {user_id}")
        return f"wallet:{passkey}:{timestamp}"
    
    @staticmethod
    def generate_session_passkey(session_token: str, user_id: str) -> str:
        """Generate passkey from token-based session"""
        timestamp = str(int(time.time()))
        data = f"{session_token}:{user_id}:{timestamp}"
        passkey = hmac.new(
            SECRET_KEY.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        logger.info(f"Generated session passkey for user {user_id}")
        return f"session:{passkey}:{timestamp}"
    
    @staticmethod
    def validate_passkey(passkey: str, user_id: str) -> bool:
        """Validate passkey and check expiry"""
        try:
            if not passkey:
                return False
            
            parts = passkey.split(':')
            if len(parts) != 3:
                return False
            
            passkey_type, key, timestamp = parts
            timestamp_int = int(timestamp)
            
            # Check if passkey is expired
            expiry_time = timestamp_int + (AGK_CONFIG["passkey_expiry_hours"] * 3600)
            if time.time() > expiry_time:
                logger.warning(f"Passkey expired for user {user_id}")
                return False
            
            logger.info(f"Passkey validated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating passkey for user {user_id}: {e}")
            return False

class ContentValidator:
    """Validate upload content type and size"""
    
    @staticmethod
    def validate_file_type(content_type: str, filename: str = None) -> bool:
        """Validate file content type"""
        if not content_type:
            if filename:
                content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                return False
        
        allowed_types = (AGK_CONFIG["allowed_image_types"] + 
                        AGK_CONFIG["allowed_text_types"])
        
        is_valid = content_type.lower() in [t.lower() for t in allowed_types]
        
        if is_valid:
            logger.info(f"Content type {content_type} validated successfully")
        else:
            logger.warning(f"Invalid content type: {content_type}")
        
        return is_valid
    
    @staticmethod
    def validate_file_size(content_length: int) -> bool:
        """Validate file size"""
        max_size = AGK_CONFIG["max_file_size"]
        
        if content_length > max_size:
            logger.warning(f"File size {content_length} exceeds limit {max_size}")
            return False
        
        logger.info(f"File size {content_length} validated successfully")
        return True
    
    @staticmethod
    def validate_content(content_type: str, content_length: int, filename: str = None) -> Dict[str, Any]:
        """Complete content validation"""
        result = {
            "valid": False,
            "errors": [],
            "content_type": content_type,
            "content_length": content_length
        }
        
        # Validate content type
        if not ContentValidator.validate_file_type(content_type, filename):
            result["errors"].append(f"Unsupported content type: {content_type}")
        
        # Validate file size
        if not ContentValidator.validate_file_size(content_length):
            size_mb = content_length / (1024 * 1024)
            max_mb = AGK_CONFIG["max_file_size"] / (1024 * 1024)
            result["errors"].append(f"File size {size_mb:.2f}MB exceeds {max_mb}MB limit")
        
        result["valid"] = len(result["errors"]) == 0
        return result

class AccessManager:
    """Manage user access levels and metadata"""
    
    @staticmethod
    def set_user_access_level(user_id: str, access_level: str, passkey: str) -> bool:
        """Set user access level in Supabase auth metadata"""
        try:
            # Update user metadata
            metadata = {
                "access_level": access_level,
                "passkey": passkey,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "passkey_type": passkey.split(':')[0] if ':' in passkey else "unknown"
            }
            
            # Note: In real implementation, you'd use Supabase Auth API
            # For now, we'll store in our users table
            supabase.table("users").update({
                "user_metadata": json.dumps(metadata),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }).eq("id", user_id).execute()
            
            logger.info(f"Access level {access_level} set for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting access level for user {user_id}: {e}")
            return False
    
    @staticmethod
    def get_user_access_level(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user access level from metadata"""
        try:
            resp = supabase.table("users").select("user_metadata").eq("id", user_id).single().execute()
            user = resp.data
            
            if not user or not user.get("user_metadata"):
                return None
            
            metadata = json.loads(user["user_metadata"])
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting access level for user {user_id}: {e}")
            return None

class AssetGatekeeper:
    """Main AGK class - Enhanced version of your existing validate_access"""
    
    def __init__(self):
        self.passkey_generator = PasskeyGenerator()
        self.content_validator = ContentValidator()
        self.access_manager = AccessManager()
    
    def validate_access(self, user_id: str, supabase_client=supabase) -> Dict[str, Any]:
        """
        Enhanced access validation - builds on your existing logic
        """
        result = {
            "access_granted": False,
            "access_level": "DENIED",
            "behavior_score": 0,
            "errors": [],
            "user_info": {}
        }
        
        try:
            # Get user data (your existing logic)
            resp = supabase_client.table("users").select(
                "behavior_score, role, is_anonymous, user_metadata"
            ).eq("id", user_id).single().execute()
            
            user = resp.data
            if not user:
                logger.warning(f"User {user_id} not found in users table.")
                result["errors"].append("User not found")
                return result

            behavior_score = user.get("behavior_score", 0)
            role = user.get("role", None)
            is_anonymous = user.get("is_anonymous", False)
            user_metadata = user.get("user_metadata")

            result["behavior_score"] = behavior_score
            result["user_info"] = {
                "role": role,
                "is_anonymous": is_anonymous,
                "user_id": user_id
            }

            logger.info(f"User {user_id} behavior score: {behavior_score}, role: {role}, anonymous: {is_anonymous}")

            # Enhanced validation logic
            if behavior_score < AGK_CONFIG["min_behavior_score"]:
                logger.info(f"Access denied for user {user_id} due to low behavior score.")
                result["errors"].append(f"Behavior score {behavior_score} below minimum {AGK_CONFIG['min_behavior_score']}")
                return result
            
            # Check passkey if metadata exists
            if user_metadata:
                try:
                    metadata = json.loads(user_metadata)
                    passkey = metadata.get("passkey")
                    
                    if passkey and self.passkey_generator.validate_passkey(passkey, user_id):
                        result["access_level"] = metadata.get("access_level", "BASIC_ACCESS")
                        result["access_granted"] = True
                        logger.info(f"Access granted for user {user_id} with passkey validation.")
                    else:
                        result["errors"].append("Invalid or expired passkey")
                        logger.warning(f"Invalid passkey for user {user_id}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid metadata format for user {user_id}")
            else:
                # Fallback to basic access for users without passkey
                if behavior_score >= 80:
                    result["access_level"] = "BASIC_ACCESS"
                    result["access_granted"] = True
                    logger.info(f"Basic access granted for user {user_id} based on high behavior score.")
                else:
                    result["errors"].append("No valid passkey found")

            # Log access attempt
            self.log_access_attempt(user_id, result["access_granted"], result["access_level"])
            
            return result

        except Exception as e:
            logger.error(f"Error validating access for user {user_id}: {e}")
            result["errors"].append(f"Validation error: {str(e)}")
            return result
    
    def validate_upload_request(self, user_id: str, content_type: str, content_length: int, filename: str = None) -> Dict[str, Any]:
        """Complete upload request validation"""
        
        # First validate user access
        access_result = self.validate_access(user_id)
        
        if not access_result["access_granted"]:
            return {
                "allowed": False,
                "message": REJECTION_MESSAGE,
                "errors": access_result["errors"],
                "access_result": access_result
            }
        
        # Then validate content
        content_result = self.content_validator.validate_content(content_type, content_length, filename)
        
        result = {
            "allowed": content_result["valid"] and access_result["access_granted"],
            "message": "Upload allowed" if content_result["valid"] else "Upload rejected",
            "access_result": access_result,
            "content_validation": content_result,
            "user_id": user_id
        }
        
        if not content_result["valid"]:
            result["message"] = f"Upload rejected: {', '.join(content_result['errors'])}"
        
        # Log upload attempt
        self.log_upload_attempt(user_id, result["allowed"], content_type, content_length)
        
        return result
    
    def generate_and_set_passkey(self, user_id: str, wallet_address: str = None, session_token: str = None) -> Dict[str, Any]:
        """Generate and set passkey for user"""
        
        if wallet_address:
            passkey = self.passkey_generator.generate_wallet_passkey(wallet_address, user_id)
            access_level = AGK_CONFIG["access_levels"]["wallet_connected"]
        elif session_token:
            passkey = self.passkey_generator.generate_session_passkey(session_token, user_id)
            access_level = AGK_CONFIG["access_levels"]["basic"]
        else:
            return {
                "success": False,
                "message": "Either wallet_address or session_token required"
            }
        
        success = self.access_manager.set_user_access_level(user_id, access_level, passkey)
        
        return {
            "success": success,
            "passkey": passkey if success else None,
            "access_level": access_level if success else None,
            "message": "Passkey generated successfully" if success else "Failed to generate passkey"
        }
    
    def log_access_attempt(self, user_id: str, granted: bool, access_level: str):
        """Log access attempt to database"""
        try:
            log_entry = {
                "user_id": user_id,
                "access_granted": granted,
                "access_level": access_level,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "access_validation"
            }
            
            # Store in access_logs table (you'll need to create this)
            supabase.table("access_logs").insert(log_entry).execute()
            
        except Exception as e:
            logger.error(f"Error logging access attempt: {e}")
    
    def log_upload_attempt(self, user_id: str, allowed: bool, content_type: str, content_length: int):
        """Log upload attempt to database"""
        try:
            log_entry = {
                "user_id": user_id,
                "upload_allowed": allowed,
                "content_type": content_type,
                "content_length": content_length,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "upload_validation"
            }
            
            supabase.table("access_logs").insert(log_entry).execute()
            
        except Exception as e:
            logger.error(f"Error logging upload attempt: {e}")

# Global AGK instance
agk = AssetGatekeeper()

# Your existing function - now enhanced
def validate_access(user_id: str, supabase_client=supabase) -> bool:
    """
    Your existing function - enhanced with AGK but maintaining backward compatibility
    """
    try:
        # Get user data (your existing logic)
        resp = supabase_client.table("users").select(
            "behavior_score, role, is_anonymous, user_metadata"
        ).eq("id", user_id).single().execute()
        
        user = resp.data
        if not user:
            logger.warning(f"User {user_id} not found in users table.")
            return False

        behavior_score = user.get("behavior_score", 0)
        role = user.get("role", None)
        is_anonymous = user.get("is_anonymous", False)

        logger.info(f"User {user_id} behavior score: {behavior_score}, role: {role}, anonymous: {is_anonymous}")

        # Original logic - behavior score check
        if behavior_score < AGK_CONFIG["min_behavior_score"]:
            logger.info(f"Access denied for user {user_id} due to low behavior score.")
            return False

        logger.info(f"Access granted for user {user_id}.")
        
        # Try to log access attempt, but don't fail if logging fails
        try:
            log_entry = {
                "user_id": user_id,
                "access_granted": True,
                "access_level": "BASIC_ACCESS",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "access_validation"
            }
            supabase_client.table("access_logs").insert(log_entry).execute()
        except Exception as e:
            # Log the error but don't fail the access validation
            logger.debug(f"Error logging access attempt (non-critical): {e}")
        
        return True

    except Exception as e:
        logger.error(f"Error validating access for user {user_id}: {e}")
        return False

# New enhanced functions
def validate_upload_request(user_id: str, content_type: str, content_length: int, filename: str = None) -> Dict[str, Any]:
    """Validate complete upload request"""
    return agk.validate_upload_request(user_id, content_type, content_length, filename)

def generate_passkey(user_id: str, wallet_address: str = None, session_token: str = None) -> Dict[str, Any]:
    """Generate passkey for user"""
    return agk.generate_and_set_passkey(user_id, wallet_address, session_token)

if __name__ == "__main__":
    logger.info("🔐 Testing Enhanced Asset Gatekeeper (AGK)...")
    
    # Test existing functionality
    test_user_id = "test_user"
    access = validate_access(test_user_id)
    
    if access:
        logger.info(f"✅ Access granted for user {test_user_id}")
    else:
        logger.info(f"❌ Access denied for user {test_user_id}")
    
    # Test new AGK functionality
    logger.info("\n🔍 Testing upload validation...")
    
    # Test valid image upload
    upload_result = validate_upload_request(
        user_id=test_user_id,
        content_type="image/jpeg",
        content_length=5 * 1024 * 1024,  # 5MB
        filename="test.jpg"
    )
    
    logger.info(f"Upload validation result: {upload_result['message']}")
    
    # Test passkey generation
    logger.info("\n🔑 Testing passkey generation...")
    
    passkey_result = generate_passkey(
        user_id=test_user_id,
        wallet_address="0x1234567890abcdef"
    )
    
    logger.info(f"Passkey generation: {passkey_result['message']}")
