import sys
import os
import pytest
from unittest.mock import MagicMock
# Add the src directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from token_tracking import track_token_usage



def test_track_token_usage():
    # Create a MagicMock to simulate the Supabase client
    supabase_mock = MagicMock()

    # Simulate user found with previous token_used value of 5
    supabase_mock.table().select().eq().single().execute.return_value = MagicMock(data={"token_used": 5})
    supabase_mock.table().update().eq().execute.return_value = MagicMock()
    supabase_mock.table().insert().execute.return_value = MagicMock()

    # Call the token usage tracking function
    track_token_usage(supabase_mock, user_id="test_user", tokens_used=3, action="test_action")

    # Assert the user's token_used was updated correctly (5 + 3 = 8)
    supabase_mock.table().update.assert_called_with({"token_used": 8})

    # Assert insert was called with the correct token usage details
    args, kwargs = supabase_mock.table().insert.call_args
    inserted_data = args[0]

    assert inserted_data["user_id"] == "test_user"
    assert inserted_data["tokens_used"] == 3
    assert inserted_data["action"] == "test_action"
    assert "timestamp" in inserted_data  # timestamp should be present

    # Assert execute was called on insert to actually perform DB operation
    assert supabase_mock.table().insert().execute.called

if __name__ == "__main__":
    pytest.main(["-v", __file__])