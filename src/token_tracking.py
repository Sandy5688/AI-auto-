import logging
from datetime import datetime, timezone

def track_token_usage(supabase, user_id: str, tokens_used: int = 1, action: str = "generic_action"):
    """
    Tracks token usage for a user by updating cumulative usage and inserting a history record.
    
    :param supabase: Supabase client instance
    :param user_id: ID of the user
    :param tokens_used: Number of tokens used in the action
    :param action: Description of the action performed
    """
    try:
        # Get current total tokens used
        resp = supabase.table("users").select("token_used").eq("id", user_id).single().execute()
        prev_total = 0
        if resp.data:
            prev_total = resp.data.get("token_used", 0) or 0
        else:
            logging.warning(f"track_token_usage: User {user_id} not found.")

        new_total = prev_total + tokens_used

        # Update cumulative token usage in users table
        supabase.table("users").update({"token_used": new_total}).eq("id", user_id).execute()

        # Insert detailed token usage event - FIXED: Use timezone-aware datetime
        supabase.table("token_usage_history").insert({
            "user_id": user_id,
            "tokens_used": tokens_used,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")  # Fixed deprecation
        }).execute()

        logging.info(f"Token usage updated: user={user_id}, tokens_used={tokens_used}, action={action}")

    except Exception as e:
        logging.error(f"Error tracking token usage for user {user_id}: {e}")
