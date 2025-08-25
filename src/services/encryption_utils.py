from cryptography.fernet import Fernet
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Load env from repo no matter the current working directory.
# We search upward for a "config/.env" and load the first one we find.
# -----------------------------------------------------------------------------
def _find_env_path(max_hops: int = 5) -> Path | None:
    here = Path(__file__).resolve()
    for p in [here.parent] + list(here.parents):
        env_candidate = p / "config" / ".env"
        if env_candidate.exists():
            return env_candidate
        if (here.parent - p).parts and len((here.parent - p).parts) > max_hops:
            break
    return None

_env_path = _find_env_path()
if _env_path:
    load_dotenv(_env_path)
else:
    # Fall back: allow system environment to provide the key
    load_dotenv()  # noop if no local .env; doesn't hurt

# -----------------------------------------------------------------------------
# Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Key load + validation (do NOT log the key)
# -----------------------------------------------------------------------------
KEY = os.getenv("TOKEN_ENCRYPTION_KEY")
if not KEY:
    raise ValueError("TOKEN_ENCRYPTION_KEY must be set (in config/.env or environment)")

try:
    fernet = Fernet(KEY.encode())
except Exception as e:
    raise ValueError(f"Invalid TOKEN_ENCRYPTION_KEY format for Fernet: {e}")

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _mask(s: str, keep: int = 4) -> str:
    """Mask a sensitive string for logs."""
    if not s:
        return ""
    if len(s) <= keep * 2:
        return "*" * len(s)
    return f"{s[:keep]}...{s[-keep:]}"

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
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
        encrypted_bytes = fernet.encrypt(token.encode("utf-8"))
        encrypted_token = encrypted_bytes.decode("utf-8")
        logger.debug("Token encrypted successfully (len=%d)", len(encrypted_token))
        return encrypted_token
    except Exception as e:
        logger.error("Token encryption failed: %s", e)
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
        decrypted_bytes = fernet.decrypt(encrypted_token.encode("utf-8"))
        decrypted_token = decrypted_bytes.decode("utf-8")
        logger.debug("Token decrypted successfully (len=%d)", len(decrypted_token))
        return decrypted_token
    except Exception as e:
        logger.error("Token decryption failed: %s", e)
        raise

def generate_new_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        str: Base64 encoded encryption key
    """
    new_key = Fernet.generate_key()
    return new_key.decode("utf-8")

def validate_token_format(token: str) -> bool:
    """
    Heuristic: consider a string "encrypted" if it can be decrypted with our key.

    Args:
        token: Token string to validate

    Returns:
        bool: True if token appears to be encrypted, False otherwise
    """
    if not token:
        return False
    try:
        # Will raise if not valid/forged/wrong key/etc.
        fernet.decrypt(token.encode("utf-8"))
        return True
    except Exception:
        return False

# -----------------------------------------------------------------------------
# Self-test (safe: no secret values printed)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Lightweight console logging for local testing
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger.info("🔐 Encryption utilities self-test (safe logging)")

    test_token = "test_api_token_12345"
    logger.info("Original token (masked): %s", _mask(test_token))

    try:
        encrypted = encrypt_token(test_token)
        logger.info("Encrypted (len only): %d", len(encrypted))

        decrypted = decrypt_token(encrypted)
        logger.info("Decrypted (masked): %s", _mask(decrypted))

        if test_token == decrypted:
            logger.info("✅ Encryption/decryption test PASSED")
        else:
            logger.error("❌ Encryption/decryption test FAILED")

        # Key generation example (do NOT print the key to stdout)
        new_key = generate_new_encryption_key()
        logger.info("🔑 New encryption key generated (masked): %s", _mask(new_key))
        logger.info("Store it securely as TOKEN_ENCRYPTION_KEY in your .env")

    except Exception as e:
        logger.error("❌ Encryption test failed: %s", e)
