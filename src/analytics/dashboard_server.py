from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
import logging
import os
from datetime import datetime
from analytics import get_dashboard_data, DASHBOARD_CONFIG

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, origins=["*"])
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for real-time updates
dashboard_cache = {}
active_clients = set()

@app.route('/api/dashboard/data')
def get_dashboard():
    """REST endpoint for dashboard data"""
    try:
        time_range = request.args.get('time_range', '24h')
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        dashboard_data = get_dashboard_data(time_range, refresh)
        return jsonify(dashboard_data)
    
    except Exception as e:
        logger.error(f"Error in dashboard endpoint: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/dashboard/metrics')
def get_dashboard_metrics():
    """Get just the key metrics for quick updates"""
    try:
        from analytics import fetch_flagged_user_counts, fetch_bot_patterns, get_analytics_summary
        
        return jsonify({
            "status": "success",
            "metrics": {
                "flagged_users": fetch_flagged_user_counts(),
                "bot_patterns": fetch_bot_patterns(),
                "summary": get_analytics_summary(),
                "timestamp": datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# WebSocket events for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    active_clients.add(client_id)
    logger.info(f"Client {client_id} connected. Total clients: {len(active_clients)}")
    
    # Send initial dashboard data
    dashboard_data = get_dashboard_data("24h")
    emit('dashboard_data', dashboard_data)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    active_clients.discard(client_id)
    logger.info(f"Client {client_id} disconnected. Total clients: {len(active_clients)}")

@socketio.on('request_update')
def handle_update_request(data):
    """Handle explicit update request from client"""
    try:
        time_range = data.get('time_range', '24h')
        dashboard_data = get_dashboard_data(time_range, refresh=True)
        emit('dashboard_data', dashboard_data)
    except Exception as e:
        logger.error(f"Error handling update request: {e}")
        emit('error', {"message": str(e)})

def broadcast_updates():
    """Background task to broadcast updates to all connected clients"""
    while True:
        try:
            if active_clients:
                logger.info(f"Broadcasting updates to {len(active_clients)} clients")
                dashboard_data = get_dashboard_data("24h", refresh=True)
                socketio.emit('dashboard_update', dashboard_data)
            
            time.sleep(DASHBOARD_CONFIG["refresh_interval_seconds"])
        
        except Exception as e:
            logger.error(f"Error in broadcast updates: {e}")
            time.sleep(30)  # Wait 30 seconds on error

# Start background update thread
update_thread = threading.Thread(target=broadcast_updates, daemon=True)
update_thread.start()

if __name__ == '__main__':
    logger.info("🚀 Starting Real-Time Dashboard Server...")
    logger.info(f"Dashboard refresh interval: {DASHBOARD_CONFIG['refresh_interval_seconds']} seconds")
    
    socketio.run(app, 
                debug=True, 
                host='0.0.0.0', 
                port=5002,
                allow_unsafe_werkzeug=True)
