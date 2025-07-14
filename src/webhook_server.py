from flask import Flask, request
from supabase import create_client
import os
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    try:
        data = request.get_json()
        print(f"Received data: {data}")  # Debug incoming request
        if not data or 'user_id' not in data or 'behavior_score' not in data:
            return {"status": "error", "message": "Invalid payload"}, 400
        user_id = data['user_id']
        score = data['behavior_score']
        result = supabase.table('users').upsert({'id': user_id, 'behavior_score': score}).execute()
        print(f"Supabase result: {result}")  # Debug Supabase response
        return {"status": "success"}, 200
    except Exception as e:
        print(f"Error: {str(e)}")  # Debug any exceptions
        return {"status": "error", "message": str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)