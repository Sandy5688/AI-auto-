import sys
import os
import pytest
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock

# Mock environment
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key",
    "WEBHOOK_SECRET": "test-secret-key",
    "WEBHOOK_TOKEN": "test-bearer-token",
    "WEBHOOK_AUTH_METHOD": "signature",
    "TESTING_MODE": "1"
})

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

@pytest.fixture
def client():
    """Create test client"""
    from webhook_server import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def generate_valid_signature(payload_bytes: bytes) -> str:
    """Generate valid signature for testing"""
    signature = hmac.new(
        "test-secret-key".encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def test_webhook_valid_signature(client):
    """Test webhook with valid signature"""
    payload = {
        "user_id": "test_user",
        "behavior_score": 75,
        "risk_flags": ["test"],
        "timestamp": "2025-08-03T12:00:00Z"
    }
    
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    signature = generate_valid_signature(payload_bytes)
    
    with patch('webhook_server.supabase') as mock_supabase:
        mock_supabase.table().select().eq().execute.return_value = MagicMock(data=[])
        mock_supabase.table().upsert().execute.return_value = MagicMock(data=[{"id": "test_user"}])
        
        response = client.post('/webhook',
                              data=payload_bytes,
                              headers={
                                  'Content-Type': 'application/json',
                                  'X-Webhook-Signature': signature
                              })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['user_id'] == 'test_user'

def test_webhook_invalid_signature(client):
    """Test webhook with invalid signature"""
    payload = {"user_id": "test", "behavior_score": 75}
    
    response = client.post('/webhook',
                          json=payload,
                          headers={
                              'Content-Type': 'application/json',
                              'X-Webhook-Signature': 'sha256=invalid'
                          })
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['error_code'] == 'INVALID_SIGNATURE'

def test_webhook_missing_signature(client):
    """Test webhook without signature"""
    payload = {"user_id": "test", "behavior_score": 75}
    
    response = client.post('/webhook',
                          json=payload,
                          headers={'Content-Type': 'application/json'})
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['error_code'] == 'MISSING_AUTH'

def test_webhook_validation_errors(client):
    """Test webhook validation errors"""
    payload = {"user_id": "", "behavior_score": 150}  # Invalid data
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    signature = generate_valid_signature(payload_bytes)
    
    response = client.post('/webhook',
                          data=payload_bytes,
                          headers={
                              'Content-Type': 'application/json',
                              'X-Webhook-Signature': signature
                          })
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error_code'] == 'VALIDATION_ERROR'
    assert 'validation_errors' in data

def test_database_error_classification(client):
    """Test database error classification"""
    from webhook_server import classify_database_error
    
    # Test connection error -> 502
    status, code, msg = classify_database_error("Connection timeout")
    assert status == 502
    assert code == "DATABASE_CONNECTION_ERROR"
    
    # Test constraint error -> 400
    status, code, msg = classify_database_error("Constraint violation")
    assert status == 400
    assert code == "DATABASE_VALIDATION_ERROR"
    
    # Test generic error -> 500
    status, code, msg = classify_database_error("Unknown database error")
    assert status == 500
    assert code == "DATABASE_ERROR"

def test_health_check(client):
    """Test health check endpoint"""
    with patch('webhook_server.supabase') as mock_supabase:
        mock_supabase.table().select().limit().execute.return_value = MagicMock(data=[])
        
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'auth_method' in data

def test_webhook_stats(client):
    """Test webhook stats endpoint"""
    with patch('webhook_server.supabase') as mock_supabase:
        mock_supabase.table().select().order().limit().execute.return_value = MagicMock(data=[])
        mock_supabase.table().select().execute.return_value = MagicMock(count=5, data=[])
        
        response = client.get('/webhook/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'recent_updates' in data
        assert 'auth_method' in data
