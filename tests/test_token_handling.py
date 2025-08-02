import sys
import os
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

# Generate a valid Fernet key for testing
TEST_FERNET_KEY = Fernet.generate_key().decode()

# Mock environment for testing with a VALID Fernet key
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "TOKEN_ENCRYPTION_KEY": TEST_FERNET_KEY,
    "MIGRATE_ENABLED": "true",
    "TESTING_MODE": "1"
})

# Add path BEFORE importing meme_gen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

def test_migration_disabled():
    """Test that migration doesn't run when disabled"""
    with patch.dict(os.environ, {"MIGRATE_ENABLED": "false"}):
        import importlib
        import meme_gen
        importlib.reload(meme_gen)
        
        result = meme_gen.migrate_plaintext_tokens()
        assert result == False

def test_get_user_token_missing_user():
    """Test get_user_token with missing user"""
    with patch('meme_gen.supabase') as mock_supabase:
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(data=None)
        
        from meme_gen import get_user_token
        result = get_user_token("nonexistent_user")
        assert result is None

def test_get_user_token_null_token():
    """Test get_user_token with null encrypted_token (new user)"""
    with patch('meme_gen.supabase') as mock_supabase:
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
            data={"encrypted_token": None}
        )
        
        from meme_gen import get_user_token
        result = get_user_token("new_user")
        assert result is None

def test_get_user_token_empty_string_token():
    """Test get_user_token with empty string encrypted_token"""
    with patch('meme_gen.supabase') as mock_supabase:
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
            data={"encrypted_token": ""}
        )
        
        from meme_gen import get_user_token
        result = get_user_token("user_with_empty_token")
        assert result is None

def test_generate_meme_no_token():
    """Test meme generation when user has no token"""
    with patch('meme_gen.get_user_token', return_value=None):
        from meme_gen import generate_meme
        result = generate_meme("test prompt", "funny", user_id="user_without_token")
        
        assert "error" in result
        assert result["error"] == "API token not configured"
        assert result["user_id"] == "user_without_token"

def test_migration_already_completed():
    """Test that migration skips when already completed"""
    # Import inside the test function after path is set
    import meme_gen
    
    # PATCH BOTH the environment AND the function
    with patch.object(meme_gen, 'MIGRATE_ENABLED', True), \
         patch.object(meme_gen, 'check_migration_lock', return_value=True) as mock_lock:
        
        result = meme_gen.migrate_plaintext_tokens()
        
        # Verify the mock was called
        mock_lock.assert_called_once()
        assert result == True


def test_encryption_utils_valid_key():
    """Test that encryption utils work with valid key"""
    from encryption_utils import encrypt_token, decrypt_token
    
    test_token = "test_api_token_123"
    encrypted = encrypt_token(test_token)
    decrypted = decrypt_token(encrypted)
    
    assert encrypted != test_token
    assert decrypted == test_token

def test_encryption_utils_empty_token():
    """Test encryption with empty token"""
    from encryption_utils import encrypt_token
    
    try:
        encrypt_token("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Token cannot be empty or None" in str(e)
    
    try:
        encrypt_token(None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Token cannot be empty or None" in str(e)

def test_decryption_utils_empty_token():
    """Test decryption with empty encrypted token"""
    from encryption_utils import decrypt_token
    
    try:
        decrypt_token("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Encrypted token cannot be empty or None" in str(e)
    
    try:
        decrypt_token(None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Encrypted token cannot be empty or None" in str(e)

def test_get_user_token_decryption_error():
    """Test get_user_token when decryption fails"""
    with patch('meme_gen.supabase') as mock_supabase:
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
            data={"encrypted_token": "invalid_encrypted_token"}
        )
        
        from meme_gen import get_user_token
        result = get_user_token("user_with_bad_token")
        assert result is None
