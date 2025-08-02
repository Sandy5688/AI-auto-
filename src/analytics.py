import os
import logging
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import traceback

# Dynamically find the config/.env file regardless of current working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up from src/ to project root
env_path = os.path.join(project_root, "config", ".env")

load_dotenv(env_path)

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validate environment variables
if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config/.env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_analytics_data():
    """
    Fetches behavior scores and risk flag events from Supabase.
    Returns:
        dict: { "scores": [...], "flags": [...] }
    """
    try:
        score_resp = supabase.table("users").select("id, behavior_score").execute()
        flag_resp = supabase.table("user_risk_flags").select("user_id, flag, timestamp").execute()
        
        logger.info(f"Fetched {len(score_resp.data or [])} user scores and {len(flag_resp.data or [])} risk flags")
        
        return {
            "scores": score_resp.data or [],
            "flags": flag_resp.data or []
        }
    except Exception as e:
        logger.error(f"Error fetching analytics data: {e}")
        # Fallback: return empty lists on failure
        return {
            "scores": [],
            "flags": []
        }

def safe_parse_timestamp(timestamp_str, default_format="%Y-%m-%dT%H:%M:%S"):
    """
    Safely parse timestamp strings with fallback handling.
    
    Args:
        timestamp_str: String representation of timestamp
        default_format: Default format to try if pandas parsing fails
    
    Returns:
        datetime object or None if parsing fails
    """
    if not timestamp_str:
        return None
    
    try:
        # Try pandas datetime parsing first (handles most formats)
        return pd.to_datetime(timestamp_str, utc=True)
    except (ValueError, TypeError) as e:
        logger.warning(f"Pandas timestamp parsing failed for '{timestamp_str}': {e}")
        
        # Try manual parsing with common formats
        formats_to_try = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ", 
            "%Y-%m-%d %H:%M:%S",
            default_format,
            "%Y-%m-%d"
        ]
        
        for fmt in formats_to_try:
            try:
                parsed_dt = datetime.strptime(timestamp_str.replace("Z", ""), fmt.replace("Z", ""))
                return pd.to_datetime(parsed_dt, utc=True)
            except ValueError:
                continue
        
        logger.error(f"Could not parse timestamp '{timestamp_str}' with any known format")
        return None

def prepare_chart_data(data):
    """
    Converts Supabase analytics data into chart-compatible dicts with enhanced error handling.
    """
    # Process behavior scores distribution
    scores = [entry["behavior_score"] for entry in data.get("scores", []) if "behavior_score" in entry and entry["behavior_score"] is not None]
    score_counts = pd.Series(scores).value_counts().sort_index().to_dict()
    
    logger.info(f"Processed {len(scores)} behavior scores into {len(score_counts)} unique score groups")

    # Process flag trends with enhanced timestamp handling
    flag_data = pd.DataFrame(data.get("flags", []))
    flag_trends_json = {}

    if flag_data.empty:
        logger.info("No flag data to process - returning empty trends")
        return {
            "score_dist": score_counts,
            "flag_trends": flag_trends_json
        }

    if "timestamp" not in flag_data.columns:
        logger.warning("Flag data missing 'timestamp' column - cannot generate trends")
        return {
            "score_dist": score_counts,
            "flag_trends": flag_trends_json
        }

    # Enhanced timestamp processing with fallback handling
    logger.info(f"Processing {len(flag_data)} flag entries for trends analysis")
    
    valid_timestamps = []
    invalid_timestamps = []
    
    for idx, timestamp_str in flag_data["timestamp"].items():
        parsed_ts = safe_parse_timestamp(timestamp_str)
        if parsed_ts:
            valid_timestamps.append((idx, parsed_ts))
        else:
            invalid_timestamps.append((idx, timestamp_str))
    
    if invalid_timestamps:
        logger.warning(f"Found {len(invalid_timestamps)} invalid timestamps that will be excluded from trends:")
        for idx, bad_ts in invalid_timestamps[:5]:  # Log first 5 for debugging
            logger.warning(f"  Row {idx}: '{bad_ts}'")
        if len(invalid_timestamps) > 5:
            logger.warning(f"  ... and {len(invalid_timestamps) - 5} more invalid timestamps")

    if not valid_timestamps:
        logger.error("No valid timestamps found - cannot generate flag trends")
        return {
            "score_dist": score_counts,
            "flag_trends": flag_trends_json
        }

    # Create clean dataframe with only valid timestamps
    valid_indices = [idx for idx, _ in valid_timestamps]
    clean_flag_data = flag_data.loc[valid_indices].copy()
    clean_flag_data["timestamp"] = [ts for _, ts in valid_timestamps]

    try:
        # Group by day and flag type
        grouped = clean_flag_data.groupby([
            pd.Grouper(key="timestamp", freq="D"), 
            "flag"
        ]).size().unstack(fill_value=0)
        
        if grouped.empty:
            logger.warning("Grouping resulted in empty data - no trends to generate")
            return {
                "score_dist": score_counts,
                "flag_trends": flag_trends_json
            }
        
        # Reset index to make timestamp a column
        grouped = grouped.reset_index()
        
        # Convert datetime objects to frontend-friendly string labels
        if "timestamp" in grouped.columns:
            grouped["timestamp"] = grouped["timestamp"].dt.strftime("%Y-%m-%d")
            logger.info(f"Generated trends for {len(grouped)} days with flags: {list(grouped.columns[1:])}")
        
        # Convert to dict format for JSON serialization
        flag_trends_json = grouped.to_dict(orient="list")
        
        logger.info(f"Successfully processed flag trends with {len(flag_trends_json.get('timestamp', []))} data points")

    except Exception as e:
        logger.error(f"Exception during flag trend processing: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Log the problematic data for debugging
        logger.error(f"Sample of clean_flag_data:\n{clean_flag_data.head() if not clean_flag_data.empty else 'Empty DataFrame'}")
        
        # Return fallback data
        flag_trends_json = {}

    return {
        "score_dist": score_counts,
        "flag_trends": flag_trends_json
    }

def format_chart_labels(chart_data):
    """
    Ensure all chart labels are properly formatted as strings for frontend compatibility.
    
    Args:
        chart_data: Dictionary containing chart data
    
    Returns:
        Dictionary with string-formatted labels
    """
    formatted_data = chart_data.copy()
    
    # Format score distribution labels (convert numeric scores to strings)
    if "score_dist" in formatted_data and formatted_data["score_dist"]:
        formatted_scores = {}
        for score, count in formatted_data["score_dist"].items():
            formatted_scores[str(score)] = count
        formatted_data["score_dist"] = formatted_scores
        logger.info(f"Formatted {len(formatted_scores)} score distribution labels as strings")
    
    # Flag trends labels are already handled in prepare_chart_data() via strftime()
    if "flag_trends" in formatted_data and formatted_data["flag_trends"]:
        trends = formatted_data["flag_trends"]
        if "timestamp" in trends:
            logger.info(f"Flag trends already have {len(trends['timestamp'])} string-formatted date labels")
    
    return formatted_data

def generate_charts(chart_data):
    """
    Prepares JSON-compatible chart configurations for front-end Chart.js with string labels.
    """
    # Ensure labels are formatted as strings
    formatted_data = format_chart_labels(chart_data)
    
    # Score distribution bar chart
    score_labels = list(formatted_data["score_dist"].keys())
    score_values = list(formatted_data["score_dist"].values())
    
    score_chart = {
        "type": "bar",
        "data": {
            "labels": score_labels,  # Now guaranteed to be strings
            "datasets": [{
                "label": "User Count by Behavior Score",
                "data": score_values,
                "backgroundColor": "#4CAF50",
                "borderColor": "#388E3C",
                "borderWidth": 1
            }]
        },
        "options": {
            "responsive": True,
            "scales": {
                "y": {"beginAtZero": True, "title": {"display": True, "text": "Number of Users"}},
                "x": {"title": {"display": True, "text": "Behavior Score"}}
            },
            "plugins": {
                "legend": {"position": "top"},
                "title": {"display": True, "text": "Behavior Score Distribution"}
            }
        }
    }

    # Flag trends line chart
    flag_datasets = []
    trend_labels = formatted_data["flag_trends"].get("timestamp", [])
    
    # Color palette for different flag types
    colors = ["#FF5722", "#2196F3", "#FF9800", "#9C27B0", "#4CAF50", "#F44336", "#00BCD4", "#FFEB3B"]
    color_index = 0
    
    for flag_type, flag_data in formatted_data["flag_trends"].items():
        if flag_type != "timestamp":
            flag_datasets.append({
                "label": flag_type.replace("_", " ").title(),
                "data": flag_data,
                "borderColor": colors[color_index % len(colors)],
                "backgroundColor": colors[color_index % len(colors)] + "20",  # Add transparency
                "fill": False,
                "tension": 0.1
            })
            color_index += 1

    flag_chart = {
        "type": "line",
        "data": {
            "labels": trend_labels,  # String-formatted dates
            "datasets": flag_datasets
        },
        "options": {
            "responsive": True,
            "scales": {
                "y": {"beginAtZero": True, "title": {"display": True, "text": "Flag Count"}},
                "x": {"title": {"display": True, "text": "Date"}}
            },
            "plugins": {
                "legend": {"position": "top"},
                "title": {"display": True, "text": "Risk Flag Trends Over Time"}
            }
        }
    }

    logger.info(f"Generated charts: Score distribution ({len(score_labels)} points), Flag trends ({len(trend_labels)} days, {len(flag_datasets)} flag types)")

    return {
        "score_dist_chart": score_chart,
        "flag_trends_chart": flag_chart,
        "summary": {
            "total_users": sum(score_values),
            "date_range": f"{trend_labels[0]} to {trend_labels[-1]}" if trend_labels else "No data",
            "flag_types": len(flag_datasets)
        }
    }

def get_analytics_summary():
    """
    Get a quick summary of analytics data for dashboard overview.
    """
    try:
        data = fetch_analytics_data()
        
        total_users = len(data["scores"])
        total_flags = len(data["flags"])
        
        if data["scores"]:
            avg_score = sum(entry["behavior_score"] for entry in data["scores"] if entry["behavior_score"] is not None) / len([s for s in data["scores"] if s["behavior_score"] is not None])
            low_score_users = len([s for s in data["scores"] if s["behavior_score"] and s["behavior_score"] < 60])
        else:
            avg_score = 0
            low_score_users = 0

        flag_types = set(entry["flag"] for entry in data["flags"] if entry.get("flag"))

        return {
            "total_users": total_users,
            "total_flags": total_flags,
            "average_score": round(avg_score, 1),
            "low_score_users": low_score_users,
            "unique_flag_types": len(flag_types),
            "flag_types": list(flag_types)
        }
    except Exception as e:
        logger.error(f"Error generating analytics summary: {e}")
        return {
            "total_users": 0,
            "total_flags": 0,
            "average_score": 0,
            "low_score_users": 0,
            "unique_flag_types": 0,
            "flag_types": []
        }

if __name__ == "__main__":
    logger.info("🚀 Starting analytics data processing...")
    
    # Fetch and process data
    data = fetch_analytics_data()
    logger.info(f"Fetched data: {len(data['scores'])} scores, {len(data['flags'])} flags")
    
    # Prepare chart data with enhanced error handling
    chart_data = prepare_chart_data(data)
    logger.info("Chart data preparation completed")
    
    # Generate charts with string labels
    charts = generate_charts(chart_data)
    logger.info("Chart generation completed") 
    
    # Display results
    print("\n📊 ANALYTICS RESULTS:")
    print(f"Score Distribution Chart: {len(charts['score_dist_chart']['data']['labels'])} data points")
    print(f"Flag Trends Chart: {len(charts['flag_trends_chart']['data']['labels'])} time periods")
    print(f"Summary: {charts['summary']}")
    
    # Get summary stats
    summary = get_analytics_summary()
    print(f"\n📈 QUICK STATS:")
    print(f"Total Users: {summary['total_users']}")
    print(f"Average Score: {summary['average_score']}")
    print(f"Low Score Users: {summary['low_score_users']}")
    print(f"Flag Types: {', '.join(summary['flag_types'])}")
    
    logger.info("✅ Analytics processing completed successfully")
