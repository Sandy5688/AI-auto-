import os
from datetime import datetime, timezone
from supabase import create_client
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch data from Supabase
def fetch_analytics_data():
    # Get behavior scores and risk flags
    scores = supabase.table("users").select("id, behavior_score").execute()
    flags = supabase.table("user_risk_flags").select("user_id, flag, timestamp").execute()
    print(f"Debug: scores response = {scores}")  # Add this line
    print(f"Debug: flags response = {flags}")  # Add this line
    return {"scores": scores.data, "flags": flags.data}

# Prepare chart data
def prepare_chart_data(data):
    # Score distribution (bar chart)
    score_data = [entry["behavior_score"] for entry in data["scores"] if "behavior_score" in entry]
    score_counts = pd.Series(score_data).value_counts().sort_index().to_dict()

    # Anomaly trends (line chart) by flag over time
    print("Debug: flags data =", data["flags"])  # Add this line
    if data["flags"]:  # Check if flags list is not empty
        flag_data = pd.DataFrame(data["flags"])
        if "timestamp" in flag_data.columns:
            flag_data["timestamp"] = pd.to_datetime(flag_data["timestamp"])
            flag_trends = flag_data.groupby([pd.Grouper(key="timestamp", freq="D"), "flag"]).size().unstack(fill_value=0)
        else:
            print("Warning: 'timestamp' column not found in flags data")
            flag_trends = pd.DataFrame()
    else:
        print("Warning: No flags data found")
        flag_trends = pd.DataFrame()

    return {"score_dist": score_counts, "flag_trends": flag_trends.to_dict()}

# Generate chart configurations
def generate_charts(data):
    # Bar chart for score distribution
    score_chart = {
        "type": "bar",
        "data": {
            "labels": list(data["score_dist"].keys()),
            "datasets": [{
                "label": "Behavior Score Distribution",
                "data": list(data["score_dist"].values()),
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
    flag_trends = pd.DataFrame(data["flag_trends"]) if data["flag_trends"] else pd.DataFrame()
    if not flag_trends.empty:
        flag_chart = {
            "type": "line",
            "data": {
                "labels": flag_trends.index.strftime('%Y-%m-%d').tolist(),
                "datasets": [
                    {"label": flag, "data": flag_trends[flag].tolist(), "borderColor": "#FF5722", "backgroundColor": "#FF5722", "fill": False}
                    for flag in flag_trends.columns
                ]
            },
            "options": {
                "scales": {"y": {"beginAtZero": True}},
                "plugins": {"legend": {"position": "top"}}
            }
        }
    else:
        flag_chart = {
            "type": "line",
            "data": {"labels": [], "datasets": []},
            "options": {
                "scales": {"y": {"beginAtZero": True}},
                "plugins": {"legend": {"position": "top"}}
            }
        }

    return {"score_dist_chart": score_chart, "flag_trends_chart": flag_chart}

# Main execution
if __name__ == "__main__":
    data = fetch_analytics_data()
    chart_data = prepare_chart_data(data)
    charts = generate_charts(chart_data)
    
    # Output chart configs (to be used in frontend)
    print("Score Distribution Chart:")
    print(charts["score_dist_chart"])
    print("Anomaly Trends Chart:")
    print(charts["flag_trends_chart"])