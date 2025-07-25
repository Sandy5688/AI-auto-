import os
import logging
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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

def prepare_chart_data(data):
    """
    Converts Supabase analytics data into chart-compatible dicts.
    """
    scores = [entry["behavior_score"] for entry in data.get("scores", []) if "behavior_score" in entry]
    score_counts = pd.Series(scores).value_counts().sort_index().to_dict()

    flag_data = pd.DataFrame(data.get("flags", []))
    flag_trends_json = {}

    if not flag_data.empty and "timestamp" in flag_data.columns:
        flag_data["timestamp"] = pd.to_datetime(flag_data["timestamp"])
        grouped = flag_data.groupby([pd.Grouper(key="timestamp", freq="D"), "flag"]).size().unstack(fill_value=0)
        grouped = grouped.reset_index()  # Avoid IndexError for .to_dict()
        flag_trends_json = grouped.to_dict(orient="list")
    else:
        logger.info("No flag data to process.")

    return {
        "score_dist": score_counts,
        "flag_trends": flag_trends_json
    }

def generate_charts(chart_data):
    """
    Prepares JSON-compatible chart configurations for front-end Chart.js
    """
    score_chart = {
        "type": "bar",
        "data": {
            "labels": list(chart_data["score_dist"].keys()),
            "datasets": [{
                "label": "Behavior Score Distribution",
                "data": list(chart_data["score_dist"].values()),
                "backgroundColor": "#4CAF50",
                "borderColor": "#388E3C",
                "borderWidth": 1
            }]
        },
        "options": {
            "scales": {"y": {"beginAtZero": True}},
            "plugins": {"legend": {"position": "top"}}
        }
    }

    # Line chart for anomaly trends
    flag_chart = {
        "type": "line",
        "data": {
            "labels": chart_data["flag_trends"].get("timestamp", []),
            "datasets": [
                {
                    "label": flag,
                    "data": chart_data["flag_trends"].get(flag, []),
                    "borderColor": "#FF5722",
                    "backgroundColor": "#FF5722",
                    "fill": False,
                }
                for flag in chart_data["flag_trends"] if flag != "timestamp"
            ]
        },
        "options": {
            "scales": {"y": {"beginAtZero": True}},
            "plugins": {"legend": {"position": "top"}}
        }
    }

    return {
        "score_dist_chart": score_chart,
        "flag_trends_chart": flag_chart
    }

if __name__ == "__main__":
    data = fetch_analytics_data()
    chart_data = prepare_chart_data(data)
    charts = generate_charts(chart_data)
    logger.info("Score Distribution Chart:\n%s", charts["score_dist_chart"])
    logger.info("Anomaly Trends Chart:\n%s", charts["flag_trends_chart"])
