import sys
import os
from unittest.mock import patch, MagicMock

# Mock environment for testing
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "TESTING_MODE": "1"
})

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

def test_validate_access_sufficient_score():
    """Test access validation with sufficient behavior score"""
    # Mock the create_client function and the resulting client
    with patch('agk.create_client') as mock_create_client:
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
            data={
                "behavior_score": 75,
                "role": "user",
                "is_anonymous": False
            }
        )
        
        from agk import validate_access
        result = validate_access("user_with_good_score", mock_supabase)
        assert result == True

def test_validate_access_insufficient_score():
    """Test access validation with insufficient behavior score"""
    with patch('agk.create_client') as mock_create_client:
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
            data={
                "behavior_score": 45,
                "role": "user",
                "is_anonymous": False
            }
        )
        
        from agk import validate_access
        result = validate_access("user_with_low_score", mock_supabase)
        assert result == False

def test_validate_access_user_not_found():
    """Test access validation when user is not found"""
    with patch('agk.create_client') as mock_create_client:
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(data=None)
        
        from agk import validate_access
        result = validate_access("nonexistent_user", mock_supabase)
        assert result == False

def test_validate_access_edge_case_threshold():
    """Test access validation at the threshold (60)"""
    with patch('agk.create_client') as mock_create_client:
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        # Exactly 60 should grant access
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
            data={
                "behavior_score": 60,
                "role": "user",
                "is_anonymous": False
            }
        )
        
        from agk import validate_access
        result = validate_access("user_at_threshold", mock_supabase)
        assert result == True

def test_validate_access_database_error():
    """Test access validation when database error occurs"""
    with patch('agk.create_client') as mock_create_client:
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        mock_supabase.table().select().eq().single().execute.side_effect = Exception("Database error")
        
        from agk import validate_access
        result = validate_access("user_with_db_error", mock_supabase)
        assert result == False

def test_validate_access_missing_behavior_score():
    """Test access validation when behavior_score is missing"""
    with patch('agk.create_client') as mock_create_client:
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
            data={
                "role": "user",
                "is_anonymous": False
                # behavior_score is missing
            }
        )
        
        from agk import validate_access
        result = validate_access("user_missing_score", mock_supabase)
        assert result == False  # Default score of 0 < 60

def test_validate_access_null_behavior_score():
    """Test access validation when behavior_score is null"""
    with patch('agk.create_client') as mock_create_client:
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
            data={
                "behavior_score": None,
                "role": "user",
                "is_anonymous": False
            }
        )
        
        from agk import validate_access
        result = validate_access("user_null_score", mock_supabase)
        assert result == False  # Default score of 0 < 60

def test_validate_access_different_roles():
    """Test access validation with different user roles"""
    test_cases = [
        {"role": "admin", "score": 70, "expected": True},
        {"role": "moderator", "score": 65, "expected": True},
        {"role": "user", "score": 70, "expected": True},
        {"role": None, "score": 70, "expected": True},  # Role doesn't affect current logic
    ]
    
    for case in test_cases:
        with patch('agk.create_client') as mock_create_client:
            mock_supabase = MagicMock()
            mock_create_client.return_value = mock_supabase
            
            mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
                data={
                    "behavior_score": case["score"],
                    "role": case["role"],
                    "is_anonymous": False
                }
            )
            
            from agk import validate_access
            result = validate_access(f"user_{case['role']}", mock_supabase)
            assert result == case["expected"], f"Failed for role {case['role']} with score {case['score']}"

def test_validate_access_anonymous_users():
    """Test access validation for anonymous users"""
    with patch('agk.create_client') as mock_create_client:
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        mock_supabase.table().select().eq().single().execute.return_value = MagicMock(
            data={
                "behavior_score": 70,
                "role": "user",
                "is_anonymous": True
            }
        )
        
        from agk import validate_access
        result = validate_access("anonymous_user", mock_supabase)
        assert result == True  # Currently, anonymous status doesn't affect validation
