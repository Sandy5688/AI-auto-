from cryptography.fernet import Fernet
import os
import logging
from dotenv import load_dotenv

# Dynamically find the config/.env file regardless of current working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up from src/ to project root
env_path = os.path.join(project_root, "config", ".env")

load_dotenv(env_path)

# Setup logger
logger = logging.getLogger(__name__)

KEY = os.getenv("TOKEN_ENCRYPTION_KEY")

if not KEY:
    raise ValueError("TOKEN_ENCRYPTION_KEY must be set in config/.env file")

# Validate the encryption key format
try:
    fernet = Fernet(KEY.encode())
    logger.debug("Encryption key loaded and validated successfully")
except Exception as e:
    raise ValueError(f"Invalid TOKEN_ENCRYPTION_KEY format: {e}")

def encrypt_token(token: str) -> str:
    """
    Encrypt a plaintext token.
    
    Args:
        token: Plaintext token to encrypt
        
    Returns:
        str: Base64 encoded encrypted token
        
    Raises:
        ValueError: If token is empty or None
        Exception: If encryption fails
    """
    if not token:
        raise ValueError("Token cannot be empty or None")
    
    try:
        encrypted_bytes = fernet.encrypt(token.encode('utf-8'))
        encrypted_token = encrypted_bytes.decode('utf-8')
        logger.debug("Token encrypted successfully")
        return encrypted_token
    except Exception as e:
        logger.error(f"Token encryption failed: {e}")
        raise

def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt an encrypted token.
    
    Args:
        encrypted_token: Base64 encoded encrypted token
        
    Returns:
        str: Decrypted plaintext token
        
    Raises:
        ValueError: If encrypted_token is empty or None
        Exception: If decryption fails (invalid token, wrong key, etc.)
    """
    if not encrypted_token:
        raise ValueError("Encrypted token cannot be empty or None")
    
    try:
        decrypted_bytes = fernet.decrypt(encrypted_token.encode('utf-8'))
        decrypted_token = decrypted_bytes.decode('utf-8')
        logger.debug("Token decrypted successfully")
        return decrypted_token
    except Exception as e:
        logger.error(f"Token decryption failed: {e}")
        raise

def generate_new_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        str: Base64 encoded encryption key
    """
    new_key = Fernet.generate_key()
    return new_key.decode('utf-8')

def validate_token_format(token: str) -> bool:
    """
    Validate if a string looks like an encrypted token.
    
    Args:
        token: Token string to validate
        
    Returns:
        bool: True if token appears to be encrypted, False otherwise
    """
    if not token:
        return False
    
    try:
        # Try to decrypt - if it works, it's encrypted
        decrypt_token(token)
        return True
    except:
        # If decryption fails, it might be plaintext
        return False

# Simple test and key generation utilities
if __name__ == "__main__":
    logger.info("🔐 Encryption utilities test mode")
    
    # Test encryption/decryption
    test_token = "test_api_token_12345"
    
    try:
        logger.info(f"Original token: {test_token}")
        
        # Encrypt
        encrypted = encrypt_token(test_token)
        logger.info(f"Encrypted: {encrypted}")
        
        # Decrypt
        decrypted = decrypt_token(encrypted)
        logger.info(f"Decrypted: {decrypted}")
        
        # Verify
        if test_token == decrypted:
            logger.info("✅ Encryption/decryption test PASSED")
        else:
            logger.error("❌ Encryption/decryption test FAILED")
            
    except Exception as e:
        logger.error(f"❌ Encryption test failed: {e}")
    
    # Generate new key example
    logger.info("\n🔑 Key generation example:")
    new_key = generate_new_encryption_key()
    logger.info(f"New encryption key: {new_key}")
    logger.info("Add this to your .env file as: TOKEN_ENCRYPTION_KEY=" + new_key)
