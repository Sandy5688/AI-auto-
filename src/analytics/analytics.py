import os
import logging
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import traceback
import json
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Dynamically find the config/.env file regardless of current working directory

current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up from src/analytics/ to project root (two levels up)
project_root = os.path.dirname(os.path.dirname(current_dir))
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

# NEW: Dashboard Configuration
DASHBOARD_CONFIG = {
    "refresh_interval_seconds": 30,
    "max_leaderboard_users": 50,
    "score_zones": {
        "suspicious": (0, 49),
        "normal": (50, 79),
        "highly_trusted": (80, 100)
    },
    "time_ranges": {
        "1h": {"hours": 1, "interval": "5T"},    # 5-minute intervals
        "24h": {"hours": 24, "interval": "1H"},  # 1-hour intervals
        "7d": {"days": 7, "interval": "1D"},     # 1-day intervals
        "30d": {"days": 30, "interval": "1D"}    # 1-day intervals
    }
}

def fetch_analytics_data():
    """
    Fetches behavior scores and risk flag events from Supabase.
    Returns:
        dict: { "scores": [...], "flags": [...] }
    """
    try:
        score_resp = supabase.table("users").select("id, behavior_score, last_updated").execute()
        flag_resp = supabase.table("user_risk_flags").select("user_id, flag, timestamp").execute()
        
        logger.info(f"Fetched {len(score_resp.data or [])} user scores and {len(flag_resp.data or [])} risk flags")
        
        return {
            "scores": score_resp.data or [],
            "flags": flag_resp.data or []
        }
    except Exception as e:
        logger.error(f"Error fetching analytics data: {e}")
        return {
            "scores": [],
            "flags": []
        }

# NEW: Enhanced data fetching for dashboard components
def fetch_live_bse_data(time_range: str = "24h") -> Dict[str, Any]:
    """
    Fetch live BSE scoring trends for dashboard
    
    Args:
        time_range: "1h", "24h", "7d", or "30d"
        
    Returns:
        Dict containing live BSE trends data
    """
    try:
        config = DASHBOARD_CONFIG["time_ranges"].get(time_range, DASHBOARD_CONFIG["time_ranges"]["24h"])
        
        if "hours" in config:
            since_time = datetime.now() - timedelta(hours=config["hours"])
        else:
            since_time = datetime.now() - timedelta(days=config["days"])
        
        # Get users with recent score updates
        users_resp = supabase.table("users")\
            .select("id, behavior_score, last_updated")\
            .gte("last_updated", since_time.isoformat())\
            .order("last_updated", desc=True)\
            .execute()
        
        # Get risk flags for the same period
        flags_resp = supabase.table("user_risk_flags")\
            .select("user_id, flag, timestamp")\
            .gte("timestamp", since_time.isoformat())\
            .execute()
        
        return {
            "users": users_resp.data or [],
            "flags": flags_resp.data or [],
            "time_range": time_range,
            "since": since_time.isoformat(),
            "config": config
        }
    
    except Exception as e:
        logger.error(f"Error fetching live BSE data: {e}")
        return {"users": [], "flags": [], "time_range": time_range}

def fetch_flagged_user_counts() -> Dict[str, Any]:
    """
    Get real-time flagged user counts and statistics
    
    Returns:
        Dict with flagged user metrics
    """
    try:
        # Get all current risk flags
        flags_resp = supabase.table("user_risk_flags")\
            .select("user_id, flag, timestamp")\
            .execute()
        
        flags_data = flags_resp.data or []
        
        # Count unique flagged users
        flagged_users = set()
        flag_counts = defaultdict(int)
        recent_flags = 0
        
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        for flag in flags_data:
            flagged_users.add(flag["user_id"])
            flag_counts[flag["flag"]] += 1
            
            # Count recent flags (last hour)
            flag_time = safe_parse_timestamp(flag["timestamp"])
            if flag_time and flag_time > one_hour_ago:
                recent_flags += 1
        
        # Get total user count
        total_users_resp = supabase.table("users").select("id", count="exact").execute()
        total_users = total_users_resp.count or 0
        
        return {
            "total_flagged_users": len(flagged_users),
            "total_users": total_users,
            "flagged_percentage": round((len(flagged_users) / total_users * 100), 2) if total_users > 0 else 0,
            "flag_breakdown": dict(flag_counts),
            "recent_flags_1h": recent_flags,
            "top_flags": sorted(flag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    except Exception as e:
        logger.error(f"Error fetching flagged user counts: {e}")
        return {
            "total_flagged_users": 0,
            "total_users": 0,
            "flagged_percentage": 0,
            "flag_breakdown": {},
            "recent_flags_1h": 0,
            "top_flags": []
        }

def fetch_bot_patterns() -> Dict[str, Any]:
    """
    Analyze bot detection patterns from IP addresses and device hashes
    
    Returns:
        Dict with bot pattern analysis
    """
    try:
        # Get bot detection data
        bot_detections_resp = supabase.table("bot_detections")\
            .select("ip_address, user_agent, bot_probability, bot_signals, timestamp")\
            .execute()
        
        bot_data = bot_detections_resp.data or []
        
        # Analyze IP patterns
        ip_patterns = defaultdict(list)
        device_patterns = defaultdict(int)
        high_risk_ips = []
        
        for detection in bot_data:
            ip = detection.get("ip_address", "unknown")
            bot_prob = detection.get("bot_probability", 0)
            user_agent = detection.get("user_agent", "")
            signals = detection.get("bot_signals", [])
            
            ip_patterns[ip].append({
                "probability": bot_prob,
                "signals": signals,
                "user_agent": user_agent,
                "timestamp": detection.get("timestamp")
            })
            
            # Track device patterns (simplified hash of user agent)
            device_hash = str(hash(user_agent))[:8] if user_agent else "unknown"
            device_patterns[device_hash] += 1
            
            # High-risk IPs (>0.7 bot probability)
            if bot_prob > 0.7:
                high_risk_ips.append({
                    "ip": ip,
                    "probability": bot_prob,
                    "signals": signals
                })
        
        # Get most common patterns
        top_ips = sorted(
            [(ip, len(detections), max(d["probability"] for d in detections))
             for ip, detections in ip_patterns.items()],
            key=lambda x: x[2], reverse=True
        )[:10]
        
        top_devices = sorted(device_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_bot_detections": len(bot_data),
            "unique_ips": len(ip_patterns),
            "unique_devices": len(device_patterns),
            "high_risk_ips": len(high_risk_ips),
            "top_suspicious_ips": [
                {"ip": ip, "detections": count, "max_probability": prob}
                for ip, count, prob in top_ips
            ],
            "top_device_patterns": [
                {"device_hash": device, "count": count}
                for device, count in top_devices
            ],
            "recent_high_risk": high_risk_ips[-5:]  # Last 5 high-risk detections
        }
    
    except Exception as e:
        logger.error(f"Error analyzing bot patterns: {e}")
        return {
            "total_bot_detections": 0,
            "unique_ips": 0,
            "unique_devices": 0,
            "high_risk_ips": 0,
            "top_suspicious_ips": [],
            "top_device_patterns": [],
            "recent_high_risk": []
        }

def fetch_leaderboard_data(limit: int = 50) -> Dict[str, Any]:
    """
    Generate leaderboard with top and bottom scoring users
    
    Args:
        limit: Maximum number of users to return
        
    Returns:
        Dict with leaderboard data
    """
    try:
        # Get all users with scores, ordered by behavior_score
        users_resp = supabase.table("users")\
            .select("id, behavior_score, last_updated")\
            .not_.is_("behavior_score", "null")\
            .order("behavior_score", desc=True)\
            .limit(limit * 2)\
            .execute()  # Get extra to split into top/bottom
        
        users_data = users_resp.data or []
        
        if not users_data:
            return {"top_users": [], "bottom_users": [], "total_users": 0}
        
        # Split into top and bottom performers
        half_limit = limit // 2
        top_users = users_data[:half_limit]
        bottom_users = sorted(users_data, key=lambda x: x["behavior_score"])[:half_limit]
        
        # Add rankings
        for i, user in enumerate(top_users, 1):
            user["rank"] = i
            user["category"] = "top"
        
        for i, user in enumerate(bottom_users, 1):
            user["rank"] = len(users_data) - half_limit + i
            user["category"] = "bottom"
        
        # Get score zone distribution
        score_zones = {"suspicious": 0, "normal": 0, "highly_trusted": 0}
        for user in users_data:
            score = user["behavior_score"]
            if DASHBOARD_CONFIG["score_zones"]["suspicious"][0] <= score <= DASHBOARD_CONFIG["score_zones"]["suspicious"][1]:
                score_zones["suspicious"] += 1
            elif DASHBOARD_CONFIG["score_zones"]["normal"][0] <= score <= DASHBOARD_CONFIG["score_zones"]["normal"][1]:
                score_zones["normal"] += 1
            elif DASHBOARD_CONFIG["score_zones"]["highly_trusted"][0] <= score <= DASHBOARD_CONFIG["score_zones"]["highly_trusted"][1]:
                score_zones["highly_trusted"] += 1
        
        return {
            "top_users": top_users,
            "bottom_users": bottom_users,
            "total_users": len(users_data),
            "score_zones": score_zones,
            "avg_score": round(sum(u["behavior_score"] for u in users_data) / len(users_data), 1),
            "last_updated": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error fetching leaderboard data: {e}")
        return {"top_users": [], "bottom_users": [], "total_users": 0, "score_zones": {}}

def safe_parse_timestamp(timestamp_str, default_format="%Y-%m-%dT%H:%M:%S"):
    """
    Safely parse timestamp strings with fallback handling.
    """
    if not timestamp_str:
        return None
    
    try:
        return pd.to_datetime(timestamp_str, utc=True)
    except (ValueError, TypeError) as e:
        logger.warning(f"Pandas timestamp parsing failed for '{timestamp_str}': {e}")
        
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
        for idx, bad_ts in invalid_timestamps[:5]:
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
        logger.error(f"Sample of clean_flag_data:\n{clean_flag_data.head() if not clean_flag_data.empty else 'Empty DataFrame'}")
        flag_trends_json = {}

    return {
        "score_dist": score_counts,
        "flag_trends": flag_trends_json
    }

# NEW: Generate comprehensive dashboard charts
def generate_dashboard_charts(time_range: str = "24h") -> Dict[str, Any]:
    """
    Generate all charts needed for the real-time dashboard
    
    Args:
        time_range: Time range for live data
        
    Returns:
        Dict containing all chart configurations
    """
    try:
        # Fetch all necessary data
        live_data = fetch_live_bse_data(time_range)
        flagged_data = fetch_flagged_user_counts()
        bot_data = fetch_bot_patterns()
        leaderboard_data = fetch_leaderboard_data()
        
        # 1. Live BSE Scoring Trends (Line Chart)
        bse_trend_chart = generate_bse_trend_chart(live_data)
        
        # 2. Score Zone Distribution (Bar Chart)
        score_zone_chart = generate_score_zone_chart(leaderboard_data["score_zones"])
        
        # 3. Flag Breakdown (Pie Chart)
        flag_pie_chart = generate_flag_pie_chart(flagged_data["flag_breakdown"])
        
        # 4. Bot Pattern Heatmap (Bubble Chart)
        bot_pattern_chart = generate_bot_pattern_chart(bot_data)
        
        # 5. Leaderboard Table Data
        leaderboard_table = generate_leaderboard_table(leaderboard_data)
        
        return {
            "bse_trend_chart": bse_trend_chart,
            "score_zone_chart": score_zone_chart,
            "flag_pie_chart": flag_pie_chart,
            "bot_pattern_chart": bot_pattern_chart,
            "leaderboard_table": leaderboard_table,
            "summary_stats": {
                "total_users": leaderboard_data["total_users"],
                "avg_score": leaderboard_data["avg_score"],
                "flagged_users": flagged_data["total_flagged_users"],
                "bot_detections": bot_data["total_bot_detections"],
                "last_updated": datetime.now().isoformat()
            },
            "time_range": time_range
        }
    
    except Exception as e:
        logger.error(f"Error generating dashboard charts: {e}")
        return {"error": str(e)}

def generate_bse_trend_chart(live_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate BSE scoring trends line chart"""
    try:
        users = live_data.get("users", [])
        if not users:
            return {"type": "line", "data": {"labels": [], "datasets": []}}
        
        # Group by time intervals and calculate average scores
        df = pd.DataFrame(users)
        df["last_updated"] = pd.to_datetime(df["last_updated"])
        
        # Resample by hour and get average score
        df = df.set_index("last_updated")
        hourly_avg = df["behavior_score"].resample("H").mean().fillna(method="ffill")
        
        return {
            "type": "line",
            "data": {
                "labels": [ts.strftime("%H:%M") for ts in hourly_avg.index],
                "datasets": [{
                    "label": "Average Behavior Score",
                    "data": list(hourly_avg.values),
                    "borderColor": "#2196F3",
                    "backgroundColor": "#2196F320",
                    "fill": True,
                    "tension": 0.4
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {"display": True, "text": "Live BSE Scoring Trends"},
                    "legend": {"position": "top"}
                },
                "scales": {
                    "y": {"beginAtZero": True, "max": 100, "title": {"display": True, "text": "Score"}},
                    "x": {"title": {"display": True, "text": "Time"}}
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Error generating BSE trend chart: {e}")
        return {"type": "line", "data": {"labels": [], "datasets": []}}

def generate_score_zone_chart(score_zones: Dict[str, int]) -> Dict[str, Any]:
    """Generate score zone distribution bar chart"""
    zone_colors = {
        "suspicious": "#F44336",
        "normal": "#FF9800", 
        "highly_trusted": "#4CAF50"
    }
    
    return {
        "type": "bar",
        "data": {
            "labels": [zone.replace("_", " ").title() for zone in score_zones.keys()],
            "datasets": [{
                "label": "Users by Score Zone",
                "data": list(score_zones.values()),
                "backgroundColor": [zone_colors.get(zone, "#9E9E9E") for zone in score_zones.keys()],
                "borderWidth": 1
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": "User Distribution by Score Zones"},
                "legend": {"display": False}
            },
            "scales": {
                "y": {"beginAtZero": True, "title": {"display": True, "text": "Number of Users"}},
                "x": {"title": {"display": True, "text": "Score Zone"}}
            }
        }
    }

def generate_flag_pie_chart(flag_breakdown: Dict[str, int]) -> Dict[str, Any]:
    """Generate flag breakdown pie chart"""
    if not flag_breakdown:
        return {"type": "pie", "data": {"labels": [], "datasets": []}}
    
    colors = ["#FF5722", "#2196F3", "#FF9800", "#9C27B0", "#4CAF50", "#F44336", "#00BCD4", "#FFEB3B"]
    
    return {
        "type": "pie",
        "data": {
            "labels": [flag.replace("_", " ").title() for flag in flag_breakdown.keys()],
            "datasets": [{
                "data": list(flag_breakdown.values()),
                "backgroundColor": colors[:len(flag_breakdown)],
                "borderWidth": 2,
                "borderColor": "#fff"
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": "Risk Flag Breakdown"},
                "legend": {"position": "right"}
            }
        }
    }

def generate_bot_pattern_chart(bot_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate bot pattern bubble chart"""
    try:
        top_ips = bot_data.get("top_suspicious_ips", [])
        
        if not top_ips:
            return {"type": "bubble", "data": {"datasets": []}}
        
        bubble_data = []
        for i, ip_data in enumerate(top_ips[:10]):  # Top 10 IPs
            bubble_data.append({
                "x": i,
                "y": ip_data["max_probability"] * 100,
                "r": ip_data["detections"] * 2,  # Bubble size
                "ip": ip_data["ip"]
            })
        
        return {
            "type": "bubble",
            "data": {
                "datasets": [{
                    "label": "Bot Detection Patterns",
                    "data": bubble_data,
                    "backgroundColor": "#FF572250",
                    "borderColor": "#FF5722",
                    "borderWidth": 1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {"display": True, "text": "Bot Detection Patterns by IP"},
                    "tooltip": {
                        "callbacks": {
                            "label": "function(context) { return context.parsed.ip + ': ' + context.parsed.y + '% bot probability'; }"
                        }
                    }
                },
                "scales": {
                    "y": {"beginAtZero": True, "max": 100, "title": {"display": True, "text": "Bot Probability (%)"}},
                    "x": {"title": {"display": True, "text": "IP Address Rank"}}
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Error generating bot pattern chart: {e}")
        return {"type": "bubble", "data": {"datasets": []}}

def generate_leaderboard_table(leaderboard_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate leaderboard table data"""
    return {
        "top_users": leaderboard_data.get("top_users", []),
        "bottom_users": leaderboard_data.get("bottom_users", []),
        "columns": ["rank", "user_id", "behavior_score", "last_updated"],
        "total_users": leaderboard_data.get("total_users", 0)
    }

def format_chart_labels(chart_data):
    """
    Ensure all chart labels are properly formatted as strings for frontend compatibility.
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
            "labels": score_labels,
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
                "backgroundColor": colors[color_index % len(colors)] + "20",
                "fill": False,
                "tension": 0.1
            })
            color_index += 1

    flag_chart = {
        "type": "line",
        "data": {
            "labels": trend_labels,
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

# NEW: Real-time dashboard data endpoint
def get_dashboard_data(time_range: str = "24h", refresh: bool = False) -> Dict[str, Any]:
    """
    Get comprehensive dashboard data for real-time display
    
    Args:
        time_range: Time range for live data ("1h", "24h", "7d", "30d")
        refresh: Force refresh of cached data
        
    Returns:
        Complete dashboard data structure
    """
    try:
        logger.info(f"🚀 Generating dashboard data for time range: {time_range}")
        
        # Generate all dashboard charts
        dashboard_charts = generate_dashboard_charts(time_range)
        
        # Get additional metrics
        flagged_data = fetch_flagged_user_counts()
        bot_data = fetch_bot_patterns()
        summary = get_analytics_summary()
        
        return {
            "status": "success",
            "data": {
                "charts": dashboard_charts,
                "metrics": {
                    "flagged_users": flagged_data,
                    "bot_patterns": bot_data,
                    "summary": summary
                },
                "config": {
                    "time_range": time_range,
                    "refresh_interval": DASHBOARD_CONFIG["refresh_interval_seconds"],
                    "available_ranges": list(DASHBOARD_CONFIG["time_ranges"].keys())
                }
            },
            "generated_at": datetime.now().isoformat(),
            "cache_info": {
                "refresh_requested": refresh,
                "data_freshness": "live"
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return {
            "status": "error",
            "error": str(e),
            "generated_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    logger.info("🚀 Starting Real-Time Analytics Dashboard processing...")
    
    # Test dashboard data generation
    dashboard_data = get_dashboard_data("24h")
    
    if dashboard_data["status"] == "success":
        charts = dashboard_data["data"]["charts"]
        metrics = dashboard_data["data"]["metrics"]
        
        print("\n📊 REAL-TIME DASHBOARD RESULTS:")
        print(f"✅ BSE Trend Chart: {len(charts['bse_trend_chart']['data'].get('labels', []))} data points")
        print(f"✅ Score Zone Chart: {len(charts['score_zone_chart']['data'].get('labels', []))} zones")
        print(f"✅ Flag Pie Chart: {len(charts['flag_pie_chart']['data'].get('labels', []))} flag types")
        print(f"✅ Bot Pattern Chart: {len(charts['bot_pattern_chart']['data'].get('datasets', []))} datasets")
        print(f"✅ Leaderboard: {charts['leaderboard_table']['total_users']} users")
        
        print(f"\n📈 DASHBOARD METRICS:")
        print(f"Total Users: {metrics['summary']['total_users']}")
        print(f"Flagged Users: {metrics['flagged_users']['total_flagged_users']} ({metrics['flagged_users']['flagged_percentage']}%)")
        print(f"Bot Detections: {metrics['bot_patterns']['total_bot_detections']}")
        print(f"Average Score: {metrics['summary']['average_score']}")
        
    else:
        print(f"❌ Dashboard generation failed: {dashboard_data.get('error')}")
    
    logger.info("✅ Real-Time Analytics Dashboard processing completed")
