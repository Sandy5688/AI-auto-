import sys
import os
import pytest
import requests_mock
from unittest.mock import patch, MagicMock
import threading
import time

# Mock environment
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "WEBHOOK_URL": "http://test-webhook.com/webhook",
    "TESTING_MODE": "1"
})

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

def test_webhook_retry_logic():
    """Test webhook retry with exponential backoff"""
    import bse
    
    with requests_mock.Mocker() as m:
        # First two attempts fail, third succeeds
        m.post('http://test-webhook.com/webhook', 
               [{'status_code': 503}, {'status_code': 502}, {'status_code': 200, 'json': {'status': 'success'}}])
        
        with patch('bse.time.sleep'):  # Skip actual sleep in tests
            result = bse.send_score_to_webhook("test_user", 75, ["test_flag"])
            
        assert result == True
        assert len(m.request_history) == 3  # Should have made 3 attempts

def test_webhook_all_retries_fail():
    """Test webhook when all retries fail"""
    import bse
    
    with requests_mock.Mocker() as m:
        # All attempts fail
        m.post('http://test-webhook.com/webhook', status_code=503)
        
        with patch('bse.time.sleep'):
            result = bse.send_score_to_webhook("test_user", 75, ["test_flag"])
            
        assert result == False
        assert len(m.request_history) == 3  # Should have made max attempts

def test_access_token_encryption():
    """Test access token encryption in get_token.py"""
    with patch('get_token.supabase') as mock_supabase:
        mock_auth = MagicMock()
        mock_auth.sign_in_with_password.return_value = MagicMock(session=MagicMock(access_token="test_token_123"))
        mock_supabase.auth = mock_auth
        mock_supabase.table().upsert().execute.return_value = MagicMock(data=[{"id": "test_user"}])
        
        from get_token import get_and_encrypt_token
        result = get_and_encrypt_token("test_user")
        
        assert result["success"] == True
        assert result["access_token"] == "test_token_123"
        assert result["encrypted_token"] is not None
        assert result["stored"] == True

def test_cache_expiry_cleanup():
    """Test cache expiry and cleanup functionality"""
    from meme_gen import CacheEntry, cleanup_cache, MEME_CACHE
    from datetime import datetime, timezone, timedelta
    
    # Clear existing cache
    MEME_CACHE.clear()
    
    # Create an entry that's already expired by setting created_at in the past
    expired_entry = CacheEntry({"result": "old"}, ttl_hours=1)
    # Manually set creation time to 2 hours ago to ensure it's expired
    expired_entry.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    expired_entry.expires_at = expired_entry.created_at + timedelta(hours=1)
    MEME_CACHE[("user1", "prompt1", "tone1", "")] = expired_entry
    
    # Add valid entry  
    valid_entry = CacheEntry({"result": "new"}, ttl_hours=24)
    MEME_CACHE[("user2", "prompt2", "tone2", "")] = valid_entry
    
    # Verify the expired entry is actually expired
    assert expired_entry.is_expired() == True
    assert valid_entry.is_expired() == False
    
    # Run cleanup
    expired_count = cleanup_cache()
    
    assert expired_count >= 1
    assert len(MEME_CACHE) == 1  # Should only have valid entry left
    assert ("user1", "prompt1", "tone1", "") not in MEME_CACHE  # Expired entry removed
    assert ("user2", "prompt2", "tone2", "") in MEME_CACHE      # Valid entry remains


def test_cache_size_limit():
    """Test cache size management"""
    from meme_gen import cache_result, MEME_CACHE, CACHE_MAX_SIZE
    
    # Clear existing cache
    MEME_CACHE.clear()
    
    # Add entries up to limit
    for i in range(5):  # Add a few entries
        cache_result(f"user_{i}", f"prompt_{i}", "tone", None, {"result": f"data_{i}"})
    
    initial_size = len(MEME_CACHE)
    assert initial_size == 5

def test_cache_stats():
    """Test cache statistics functionality"""
    from meme_gen import get_cache_stats, cache_result, MEME_CACHE
    
    # Clear cache and add test data
    MEME_CACHE.clear()
    cache_result("user1", "prompt1", "tone1", None, {"test": "data1"})
    cache_result("user2", "prompt2", "tone2", None, {"test": "data2"})
    
    stats = get_cache_stats()
    
    assert stats["total_entries"] == 2
    assert stats["valid_entries"] <= 2
    assert "cache_hit_potential" in stats
    assert "memory_usage_estimate_kb" in stats
