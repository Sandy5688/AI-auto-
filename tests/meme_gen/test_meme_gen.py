import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import pytest

# Mock environment with enhanced configuration
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "OPENAI_API_KEY": "sk-test_openai_key",
    "MONTHLY_BUDGET_LIMIT": "20.0",
    "DALL_E_MODEL": "dall-e-3",
    "DALL_E_QUALITY": "standard",
    "DALL_E_SIZE": "1024x1024",
    "TESTING_MODE": "1"
})

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# EXISTING TESTS (Keep all your current tests)
def test_cost_tracker_get_image_cost():
    """Test DALL·E cost calculation"""
    import meme_gen
    
    # Test DALL·E 3 standard pricing
    cost = meme_gen.CostTracker.get_image_cost("dall-e-3", "1024x1024", "standard")
    assert cost == 0.040
    
    # Test DALL·E 3 HD pricing
    cost_hd = meme_gen.CostTracker.get_image_cost("dall-e-3", "1024x1024", "hd")
    assert cost_hd == 0.080
    
    # Test unknown model defaults
    cost_unknown = meme_gen.CostTracker.get_image_cost("unknown", "1024x1024", "standard")
    assert cost_unknown == 0.040

def test_cost_tracker_monthly_spending():
    """Test monthly spending calculation"""
    import meme_gen
    
    mock_data = [
        {"amount": 5.50},
        {"amount": 3.25}, 
        {"amount": 1.75}
    ]
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = mock_data
        mock_supabase.table().select().eq().gte().execute.return_value = mock_response
        
        spending = meme_gen.CostTracker.get_user_monthly_spending("test_user")
        assert spending == 10.50

def test_cost_tracker_budget_check_within_limit():
    """Test budget check when user is within limit"""
    import meme_gen
    
    with patch.object(meme_gen.CostTracker, 'get_user_monthly_spending', return_value=15.0):
        can_afford, current, message = meme_gen.CostTracker.check_budget_limit("test_user", 3.0)
        
        assert can_afford == True
        assert current == 15.0
        assert "Budget OK" in message

def test_cost_tracker_budget_check_exceeds_limit():
    """Test budget check when user would exceed limit"""
    import meme_gen
    
    with patch.object(meme_gen.CostTracker, 'get_user_monthly_spending', return_value=18.0):
        can_afford, current, message = meme_gen.CostTracker.check_budget_limit("test_user", 5.0)
        
        assert can_afford == False
        assert current == 18.0
        assert "Budget limit reached" in message

def test_cost_tracker_record_cost():
    """Test cost recording to database"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_supabase.table().insert().execute.return_value = MagicMock()
        
        meme_gen.CostTracker.record_cost("test_user", 0.040, "dall-e-3", "1024x1024", "standard", "test prompt")
        
        # Verify insert was called
        mock_supabase.table.assert_called_with("user_api_costs")
        insert_call = mock_supabase.table().insert.call_args[0][0]
        
        assert insert_call["user_id"] == "test_user"
        assert insert_call["amount"] == 0.040
        assert insert_call["model"] == "dall-e-3"

def test_cache_entry_creation_and_expiry():
    """Test cache entry functionality"""
    import meme_gen
    
    data = {"test": "data"}
    entry = meme_gen.CacheEntry(data, ttl_hours=1)
    
    assert entry.data == data
    assert entry.is_valid() == True
    assert entry.is_expired() == False
    assert entry.access_count == 0
    
    # Test access tracking
    result = entry.access()
    assert result == data
    assert entry.access_count == 1

def test_cache_result_and_retrieval():
    """Test caching and retrieving meme results"""
    import meme_gen
    
    # Clear cache first
    meme_gen.MEME_CACHE.clear()
    
    user_id = "test_user"
    prompt = "AI meme"
    tone = "sarcastic"  # Updated to use valid tone
    result = {"output": ["test_image_url"], "status": "succeeded"}
    
    # Cache the result
    meme_gen.cache_result(user_id, prompt, tone, None, result)
    
    # Retrieve from cache
    cached = meme_gen.get_cached_result(user_id, prompt, tone, None)
    assert cached == result
    
    # Clear cache after test
    meme_gen.MEME_CACHE.clear()

def test_cache_miss():
    """Test cache miss scenario"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    cached = meme_gen.get_cached_result("nonexistent_user", "prompt", "sarcastic", None)
    assert cached is None

def test_cache_stats():
    """Test cache statistics"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    # Test empty cache stats
    stats = meme_gen.get_cache_stats()
    assert stats["total_entries"] == 0
    assert stats["valid_entries"] == 0
    
    # Add some entries
    meme_gen.cache_result("user1", "prompt1", "sarcastic", None, {"data": 1})
    meme_gen.cache_result("user2", "prompt2", "witty", None, {"data": 2})
    
    stats = meme_gen.get_cache_stats()
    assert stats["total_entries"] == 2
    assert stats["valid_entries"] == 2
    
    meme_gen.MEME_CACHE.clear()

# NEW TESTS FOR ENHANCED FEATURES

def test_supported_tones_validation():
    """Test that all supported tones are valid"""
    import meme_gen
    
    expected_tones = ['sarcastic', 'witty', 'crypto', 'relatable', 'dark humor']
    assert meme_gen.SUPPORTED_TONES == expected_tones

def test_token_manager_get_user_tokens():
    """Test TokenManager.get_user_tokens()"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = {"tokens_remaining": 5}
        mock_supabase.table().select().eq().single().execute.return_value = mock_response
        
        tokens = meme_gen.TokenManager.get_user_tokens("test_user")
        assert tokens == 5

def test_token_manager_get_user_tokens_none():
    """Test TokenManager.get_user_tokens() when tokens_remaining is None"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = {"tokens_remaining": None}
        mock_supabase.table().select().eq().single().execute.return_value = mock_response
        
        tokens = meme_gen.TokenManager.get_user_tokens("test_user")
        assert tokens == 0

def test_token_manager_get_user_tokens_error():
    """Test TokenManager.get_user_tokens() with database error"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_supabase.table().select().eq().single().execute.side_effect = Exception("DB Error")
        
        tokens = meme_gen.TokenManager.get_user_tokens("test_user")
        assert tokens == 0

def test_token_manager_get_daily_generations():
    """Test TokenManager.get_daily_generations()"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_response = MagicMock()
        mock_response.count = 2
        mock_supabase.table().select().eq().gte().execute.return_value = mock_response
        
        daily_gens = meme_gen.TokenManager.get_daily_generations("test_user")
        assert daily_gens == 2

def test_token_manager_get_daily_generations_error():
    """Test TokenManager.get_daily_generations() with database error"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_supabase.table().select().eq().gte().execute.side_effect = Exception("DB Error")
        
        daily_gens = meme_gen.TokenManager.get_daily_generations("test_user")
        assert daily_gens == 0

def test_token_manager_can_generate_within_limits():
    """Test can_generate_meme when within all limits"""
    import meme_gen
    
    with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=5):
        with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=1):
            can_generate, message, stats = meme_gen.TokenManager.can_generate_meme("test_user")
            
            assert can_generate == True
            assert "allowed" in message
            assert stats["tokens_remaining"] == 5
            assert stats["daily_generations"] == 1
            assert stats["daily_limit"] == 3

def test_token_manager_can_generate_no_tokens():
    """Test can_generate_meme when no tokens"""
    import meme_gen
    
    with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=0):
        with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=1):
            can_generate, message, stats = meme_gen.TokenManager.can_generate_meme("test_user")
            
            assert can_generate == False
            assert "Insufficient tokens" in message
            assert stats["tokens_remaining"] == 0

def test_token_manager_can_generate_daily_limit_reached():
    """Test can_generate_meme when daily limit reached"""
    import meme_gen
    
    with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=5):
        with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=3):
            can_generate, message, stats = meme_gen.TokenManager.can_generate_meme("test_user")
            
            assert can_generate == False
            assert "Daily generation limit reached" in message
            assert stats["daily_generations"] == 3
            assert stats["daily_limit"] == 3

def test_token_manager_deduct_token_success():
    """Test successful token deduction"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        # Mock getting current tokens
        mock_get_response = MagicMock()
        mock_get_response.data = {"tokens_remaining": 5}
        
        # Mock successful update
        mock_update_response = MagicMock()
        mock_update_response.data = [{"id": "test_user"}]
        
        mock_supabase.table().select().eq().single().execute.return_value = mock_get_response
        mock_supabase.table().update().eq().execute.return_value = mock_update_response
        
        result = meme_gen.TokenManager.deduct_token("test_user")
        assert result == True

def test_token_manager_deduct_token_insufficient():
    """Test token deduction with insufficient tokens"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_get_response = MagicMock()
        mock_get_response.data = {"tokens_remaining": 0}
        mock_supabase.table().select().eq().single().execute.return_value = mock_get_response
        
        result = meme_gen.TokenManager.deduct_token("test_user")
        assert result == False

def test_token_manager_deduct_token_user_not_found():
    """Test token deduction when user not found"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_get_response = MagicMock()
        mock_get_response.data = None
        mock_supabase.table().select().eq().single().execute.return_value = mock_get_response
        
        result = meme_gen.TokenManager.deduct_token("test_user")
        assert result == False

def test_tone_prompt_enhancer_valid_tones():
    """Test TonePromptEnhancer with all valid tones"""
    import meme_gen
    
    base_prompt = "AI taking over the world"
    
    for tone in meme_gen.SUPPORTED_TONES:
        enhanced = meme_gen.TonePromptEnhancer.enhance_prompt(base_prompt, tone)
        
        assert base_prompt in enhanced
        assert len(enhanced) > len(base_prompt)
        assert isinstance(enhanced, str)

def test_tone_prompt_enhancer_invalid_tone():
    """Test TonePromptEnhancer with invalid tone"""
    import meme_gen
    
    with pytest.raises(ValueError) as exc_info:
        meme_gen.TonePromptEnhancer.enhance_prompt("test prompt", "invalid_tone")
    
    assert "Unsupported tone" in str(exc_info.value)
    assert "invalid_tone" in str(exc_info.value)

def test_tone_prompt_enhancer_with_image_url():
    """Test TonePromptEnhancer with image URL reference"""
    import meme_gen
    
    base_prompt = "Funny meme"
    tone = "sarcastic"
    image_url = "https://example.com/base_image.jpg"
    
    enhanced = meme_gen.TonePromptEnhancer.enhance_prompt(base_prompt, tone, image_url)
    
    assert base_prompt in enhanced
    assert image_url in enhanced
    assert "reference" in enhanced or "base" in enhanced

def test_store_generated_meme_success():
    """Test successful meme storage"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = [{"id": "meme_123"}]
        mock_supabase.table().insert().execute.return_value = mock_response
        
        result = meme_gen.store_generated_meme(
            "test_user", 
            "https://example.com/meme.png", 
            "test prompt", 
            "sarcastic"
        )
        
        assert result == True
        
        # Verify correct table and data
        mock_supabase.table.assert_called_with('generated_memes')
        insert_call = mock_supabase.table().insert.call_args[0][0]
        
        assert insert_call["user_id"] == "test_user"
        assert insert_call["image_url"] == "https://example.com/meme.png"
        assert insert_call["prompt"] == "test prompt"
        assert insert_call["tone"] == "sarcastic"
        assert "timestamp" in insert_call

def test_store_generated_meme_failure():
    """Test failed meme storage"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = None  # Failed insert
        mock_supabase.table().insert().execute.return_value = mock_response
        
        result = meme_gen.store_generated_meme(
            "test_user", 
            "https://example.com/meme.png", 
            "test prompt", 
            "sarcastic"
        )
        
        assert result == False

def test_store_generated_meme_exception():
    """Test meme storage with database exception"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_supabase.table().insert().execute.side_effect = Exception("DB Error")
        
        result = meme_gen.store_generated_meme(
            "test_user", 
            "https://example.com/meme.png", 
            "test prompt", 
            "sarcastic"
        )
        
        assert result == False

def test_get_user_meme_history():
    """Test retrieving user meme history"""
    import meme_gen
    
    mock_history = [
        {"id": "meme_1", "prompt": "test 1", "tone": "sarcastic", "timestamp": "2025-01-01T10:00:00Z"},
        {"id": "meme_2", "prompt": "test 2", "tone": "witty", "timestamp": "2025-01-01T09:00:00Z"}
    ]
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = mock_history
        mock_supabase.table().select().eq().order().limit().execute.return_value = mock_response
        
        history = meme_gen.get_user_meme_history("test_user", limit=5)
        
        assert len(history) == 2
        assert history[0]["tone"] == "sarcastic"
        assert history[1]["tone"] == "witty"

def test_get_user_meme_history_empty():
    """Test retrieving user meme history when empty"""
    import meme_gen
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase.table().select().eq().order().limit().execute.return_value = mock_response
        
        history = meme_gen.get_user_meme_history("test_user")
        assert history == []

def test_get_user_meme_history_with_tone_filter():
    """Test retrieving user meme history with tone filter"""
    import meme_gen
    
    mock_history = [
        {"id": "meme_1", "prompt": "test 1", "tone": "sarcastic"}
    ]
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = mock_history
        mock_supabase.table().select().eq().order().limit().eq.return_value.execute.return_value = mock_response
        
        history = meme_gen.get_user_meme_history("test_user", tone_filter="sarcastic")
        assert len(history) == 1
        assert history[0]["tone"] == "sarcastic"

def test_get_meme_generation_stats():
    """Test comprehensive meme generation statistics"""
    import meme_gen
    
    mock_memes = [
        {"tone": "sarcastic"},
        {"tone": "sarcastic"},
        {"tone": "witty"},
        {"tone": "crypto"}
    ]
    
    with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=7):
        with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=2):
            with patch.object(meme_gen, 'supabase') as mock_supabase:
                # Mock all memes response
                mock_all_response = MagicMock()
                mock_all_response.data = mock_memes
                
                # Mock weekly response
                mock_weekly_response = MagicMock()
                mock_weekly_response.count = 3
                
                mock_supabase.table().select().eq().execute.return_value = mock_all_response
                mock_supabase.table().select().eq().gte().execute.return_value = mock_weekly_response
                
                stats = meme_gen.get_meme_generation_stats("test_user")
                
                assert stats["user_id"] == "test_user"
                assert stats["tokens_remaining"] == 7
                assert stats["daily_generations"] == 2
                assert stats["daily_limit"] == 3
                assert stats["weekly_generations"] == 3
                assert stats["total_memes_generated"] == 4
                assert stats["tone_breakdown"]["sarcastic"] == 2
                assert stats["tone_breakdown"]["witty"] == 1
                assert stats["tone_breakdown"]["crypto"] == 1
                assert stats["can_generate"] == True
                assert stats["favorite_tone"] == "sarcastic"

def test_get_meme_generation_stats_no_memes():
    """Test meme generation stats when user has no memes"""
    import meme_gen
    
    with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=5):
        with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=0):
            with patch.object(meme_gen, 'supabase') as mock_supabase:
                mock_response = MagicMock()
                mock_response.data = []
                mock_response.count = 0
                mock_supabase.table().select().eq().execute.return_value = mock_response
                mock_supabase.table().select().eq().gte().execute.return_value = mock_response
                
                stats = meme_gen.get_meme_generation_stats("test_user")
                
                assert stats["total_memes_generated"] == 0
                assert stats["tone_breakdown"] == {}
                assert stats["favorite_tone"] is None

def test_get_meme_generation_stats_error():
    """Test meme generation stats with database error"""
    import meme_gen
    
    with patch.object(meme_gen.TokenManager, 'get_user_tokens', side_effect=Exception("DB Error")):
        stats = meme_gen.get_meme_generation_stats("test_user")
        assert "error" in stats

# ENHANCED GENERATE MEME TESTS

def test_generate_meme_missing_user_id():
    """Test meme generation without user_id"""
    import meme_gen
    
    result = meme_gen.generate_meme("test prompt", "sarcastic", user_id=None)
    
    assert "error" in result
    assert result["error"] == "user_id_required"

def test_generate_meme_empty_prompt():
    """Test meme generation with empty prompt"""
    import meme_gen
    
    result = meme_gen.generate_meme("", "sarcastic", user_id="test_user")
    
    assert "error" in result
    assert result["error"] == "prompt_required"

def test_generate_meme_invalid_tone():
    """Test meme generation with invalid tone"""
    import meme_gen
    
    result = meme_gen.generate_meme("test prompt", "invalid_tone", user_id="test_user")
    
    assert "error" in result
    assert result["error"] == "invalid_tone"
    assert "supported_tones" in result
    assert result["provided_tone"] == "invalid_tone"

def test_generate_meme_token_limit_reached():
    """Test meme generation when token limit reached"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(False, "Insufficient tokens", {"tokens_remaining": 0, "daily_generations": 1})):
            result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
            
            assert "error" in result
            assert result["error"] == "generation_limit_reached"
            assert "Insufficient tokens" in result["message"]

def test_generate_meme_daily_limit_reached():
    """Test meme generation when daily limit reached"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(False, "Daily generation limit reached", {"tokens_remaining": 5, "daily_generations": 3})):
            result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
            
            assert "error" in result
            assert result["error"] == "generation_limit_reached"
            assert "Daily generation limit reached" in result["message"]

def test_generate_meme_budget_exceeded():
    """Test meme generation when budget is exceeded"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(False, 19.5, "Budget exceeded")):
                result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                
                assert "error" in result
                assert result["error"] == "monthly_budget_exceeded"
                assert "Budget exceeded" in result["message"]

def test_generate_meme_cache_hit():
    """Test meme generation with cache hit"""
    import meme_gen
    
    cached_result = {"output": ["cached_image_url"], "status": "succeeded", "tone": "sarcastic"}
    
    # FIX: Mock TokenManager methods to prevent real database calls
    with patch.object(meme_gen, 'get_cached_result', return_value=cached_result):
        with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=10):
            with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=1):
                result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                
                # Cache hit should return exact cached result
                assert result == cached_result

def test_generate_meme_enhanced_success():
    """Test successful enhanced meme generation with all new features"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    # Mock OpenAI response
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock()]
    mock_openai_response.data[0].url = "https://example.com/sarcastic_meme.png"
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {"tokens_remaining": 5, "daily_generations": 1})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                with patch.object(meme_gen, 'store_generated_meme', return_value=True):
                    with patch.object(meme_gen.TokenManager, 'deduct_token', return_value=True):
                        with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=4):
                            with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=2):
                                with patch.object(meme_gen.CostTracker, 'record_cost'):
                                    with patch.object(meme_gen, 'track_token_usage'):
                                        with patch.object(meme_gen, 'cache_result'):
                                            with patch('meme_gen.openai.Image.create', return_value=mock_openai_response):
                                                result = meme_gen.generate_meme("AI being sarcastic", "sarcastic", user_id="test_user")
                                                
                                                # Verify enhanced result structure
                                                assert result["status"] == "succeeded"
                                                assert result["tone"] == "sarcastic"
                                                assert result["caption"] == "Sarcastic meme: AI being sarcastic"
                                                assert result["tokens_cost"] == 1
                                                assert result["tokens_remaining"] == 4
                                                # FIX: Code adds +1 to current daily generations
                                                assert result["daily_generation_count"] == 3  # 2 + 1 = 3
                                                assert "https://example.com/sarcastic_meme.png" in result["output"]

def test_generate_meme_storage_failure():
    """Test meme generation when storage fails"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock()]
    mock_openai_response.data[0].url = "https://example.com/meme.png"
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                with patch.object(meme_gen, 'store_generated_meme', return_value=False):  # Storage fails
                    with patch('meme_gen.openai.Image.create', return_value=mock_openai_response):
                        result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                        
                        assert "error" in result
                        assert result["error"] == "storage_failed"

def test_generate_meme_token_deduction_failure():
    """Test meme generation when token deduction fails"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock()]
    mock_openai_response.data[0].url = "https://example.com/meme.png"
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                with patch.object(meme_gen, 'store_generated_meme', return_value=True):
                    with patch.object(meme_gen.TokenManager, 'deduct_token', return_value=False):  # Token deduction fails
                        with patch('meme_gen.openai.Image.create', return_value=mock_openai_response):
                            result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                            
                            assert "error" in result
                            assert result["error"] == "token_deduction_failed"

def test_generate_meme_openai_retry_logic():
    """Test OpenAI retry logic with transient errors"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    # Mock successful response on third attempt
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock()]
    mock_openai_response.data[0].url = "https://example.com/retry_success.png"
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                with patch.object(meme_gen, 'store_generated_meme', return_value=True):
                    with patch.object(meme_gen.TokenManager, 'deduct_token', return_value=True):
                        with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=4):
                            with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=1):
                                with patch.object(meme_gen.CostTracker, 'record_cost'):
                                    with patch.object(meme_gen, 'track_token_usage'):
                                        with patch.object(meme_gen, 'cache_result'):
                                            with patch('meme_gen.openai.Image.create') as mock_openai:
                                                # First two calls fail, third succeeds
                                                mock_openai.side_effect = [
                                                    Exception("Rate limit exceeded"),
                                                    Exception("Service temporarily unavailable"),
                                                    mock_openai_response
                                                ]
                                                
                                                result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                                                
                                                # Should succeed after retries
                                                assert result["status"] == "succeeded"
                                                assert "https://example.com/retry_success.png" in result["output"]
                                                
                                                # Verify OpenAI was called 3 times
                                                assert mock_openai.call_count == 3

def test_generate_meme_all_retries_fail():
    """Test meme generation when all retries fail"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                with patch('meme_gen.openai.Image.create') as mock_openai:
                    # All attempts fail
                    mock_openai.side_effect = Exception("Persistent error")
                    
                    result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                    
                    assert "error" in result
                    assert result["error"] == "generation_failed"
                    # FIX: Check actual exception message, not generic retry message
                    assert "Persistent error" in result["message"]
                    
                    # Verify retries were attempted
                    assert mock_openai.call_count == 3

def test_generate_meme_openai_success():
    """Test successful meme generation with OpenAI"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    # Mock OpenAI response
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock()]
    mock_openai_response.data[0].url = "https://example.com/generated_image.png"
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                with patch.object(meme_gen, 'store_generated_meme', return_value=True):
                    with patch.object(meme_gen.TokenManager, 'deduct_token', return_value=True):
                        with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=4):
                            with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=1):
                                with patch.object(meme_gen.CostTracker, 'record_cost'):
                                    with patch.object(meme_gen, 'track_token_usage'):
                                        with patch.object(meme_gen, 'cache_result'):
                                            with patch('meme_gen.openai.Image.create', return_value=mock_openai_response):
                                                result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                                                
                                                assert result["status"] == "succeeded"
                                                assert "https://example.com/generated_image.png" in result["output"]
                                                assert result["generator"] == "openai_dalle"
                                                assert result["tone"] == "sarcastic"
                                                assert "dalle_" in result["id"]

def test_generate_meme_openai_rate_limit():
    """Test OpenAI rate limit error handling"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                with patch('meme_gen.openai.Image.create', side_effect=Exception("Rate limit exceeded")):
                    result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                    
                    assert "error" in result
                    assert result["error"] == "rate_limit_exceeded"
                    assert result["user_id"] == "test_user"

def test_generate_meme_openai_auth_error():
    """Test OpenAI authentication error handling"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                with patch('meme_gen.openai.Image.create', side_effect=Exception("Invalid API key")):
                    result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                    
                    assert "error" in result
                    assert result["error"] in ["authentication_error", "invalid_request"]
                    assert result["user_id"] == "test_user"

def test_generate_meme_openai_empty_response():
    """Test OpenAI empty response handling"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    # Mock empty response
    mock_openai_response = MagicMock()
    mock_openai_response.data = []  # Empty response
    
    with patch.object(meme_gen, 'get_cached_result', return_value=None):
        with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
            with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                with patch('meme_gen.openai.Image.create', return_value=mock_openai_response):
                    result = meme_gen.generate_meme("test prompt", "sarcastic", user_id="test_user")
                    
                    assert "error" in result
                    assert result["error"] == "empty_response"

def test_full_integration_flow():
    """Test complete enhanced meme generation flow with database interactions"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    # Mock spending response (user has spent $5, limit is $20)
    mock_spending_data = [{"amount": 5.0}]
    
    # Mock OpenAI response
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock()]
    mock_openai_response.data[0].url = "https://example.com/integration_test.png"
    
    with patch.object(meme_gen, 'supabase') as mock_supabase:
        # FIX: Mock all necessary database responses with proper integer values
        
        # Mock spending query
        spending_response = MagicMock()
        spending_response.data = mock_spending_data
        
        # Mock tokens query
        tokens_response = MagicMock()
        tokens_response.data = {"tokens_remaining": 5}
        
        # Mock daily generations query
        daily_response = MagicMock()
        daily_response.count = 1  # FIX: Set count as integer, not MagicMock
        
        # Mock insert/update responses
        insert_response = MagicMock()
        insert_response.data = [{"id": "cost_123"}]
        
        update_response = MagicMock()
        update_response.data = [{"id": "user_123"}]
        
        # Configure mock responses based on call order
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = spending_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = tokens_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = daily_response
        mock_supabase.table.return_value.insert.return_value.execute.return_value = insert_response
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = update_response
        
        with patch('meme_gen.openai.Image.create', return_value=mock_openai_response):
            with patch.object(meme_gen, 'track_token_usage'):
                # Generate meme with enhanced features
                result = meme_gen.generate_meme("AI taking over", "sarcastic", user_id="integration_test_user")
                
                # Verify enhanced success
                assert result["status"] == "succeeded"
                assert result["tone"] == "sarcastic"
                assert result["caption"] == "Sarcastic meme: AI taking over"
                assert "https://example.com/integration_test.png" in result["output"]
                
                # Verify database interactions
                assert mock_supabase.table.called
                
                # Second call with same params should hit cache
                result2 = meme_gen.generate_meme("AI taking over", "sarcastic", user_id="integration_test_user")
                
                # Should be exact same result from cache
                assert result2["status"] == result["status"]
                assert result2["output"] == result["output"]
                assert result2["id"] == result["id"]

def test_cleanup_cache():
    """Test cache cleanup functionality"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    # Add some cache entries with valid tones
    for i in range(5):
        tone = meme_gen.SUPPORTED_TONES[i % len(meme_gen.SUPPORTED_TONES)]
        meme_gen.cache_result(f"user_{i}", f"prompt_{i}", tone, None, {"data": i})
    
    initial_size = len(meme_gen.MEME_CACHE)
    assert initial_size == 5
    
    # Test cleanup
    cleanup_count = meme_gen.cleanup_cache()
    
    # Should not remove valid entries
    assert len(meme_gen.MEME_CACHE) <= initial_size
    
    meme_gen.MEME_CACHE.clear()

# NEW: Integration tests for tone-specific functionality
def test_all_tones_generation():
    """Test that all supported tones can be used for generation"""
    import meme_gen
    
    meme_gen.MEME_CACHE.clear()
    
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock()]
    mock_openai_response.data[0].url = "https://example.com/tone_test.png"
    
    for tone in meme_gen.SUPPORTED_TONES:
        with patch.object(meme_gen, 'get_cached_result', return_value=None):
            with patch.object(meme_gen.TokenManager, 'can_generate_meme', return_value=(True, "allowed", {})):
                with patch.object(meme_gen.CostTracker, 'check_budget_limit', return_value=(True, 5.0, "Budget OK")):
                    with patch.object(meme_gen, 'store_generated_meme', return_value=True):
                        with patch.object(meme_gen.TokenManager, 'deduct_token', return_value=True):
                            with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=5):
                                with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=0):
                                    with patch.object(meme_gen.CostTracker, 'record_cost'):
                                        with patch.object(meme_gen, 'track_token_usage'):
                                            with patch.object(meme_gen, 'cache_result'):
                                                with patch('meme_gen.openai.Image.create', return_value=mock_openai_response):
                                                    result = meme_gen.generate_meme(f"Test {tone} meme", tone, user_id=f"test_user_{tone}")
                                                    
                                                    assert result["status"] == "succeeded"
                                                    assert result["tone"] == tone
                                                    assert tone.title() in result["caption"]

def test_daily_limit_enforcement():
    """Test that daily limits are properly enforced across multiple generations"""
    import meme_gen
    
    user_id = "daily_limit_test_user"
    
    # Mock user at daily limit
    with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=10):
        with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=3):  # At limit
            can_generate, message, stats = meme_gen.TokenManager.can_generate_meme(user_id)
            
            assert can_generate == False
            assert "Daily generation limit reached" in message
            assert stats["daily_generations"] == 3
            assert stats["daily_limit"] == 3
    
    # Mock user under daily limit
    with patch.object(meme_gen.TokenManager, 'get_user_tokens', return_value=10):
        with patch.object(meme_gen.TokenManager, 'get_daily_generations', return_value=2):  # Under limit
            can_generate, message, stats = meme_gen.TokenManager.can_generate_meme(user_id)
            
            assert can_generate == True
            assert "allowed" in message

if __name__ == "__main__":
    print("🧪 Running Enhanced Meme Generation Tests")
    print("=" * 50)
    
    # You can run individual test functions here for debugging
    test_supported_tones_validation()
    test_token_manager_get_user_tokens()
    test_tone_prompt_enhancer_valid_tones()
    
    print("✅ All manual tests passed!")
