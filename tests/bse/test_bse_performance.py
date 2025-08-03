#!/usr/bin/env python3
import time
import sys
import os

# Add src to path - go up two directories  
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

def test_processing_performance():
    """Test BSE performance with multiple payloads"""
    try:
        from bse import main_processing_pipeline
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure bse.py exists in the src/ directory")
        return
    
    print("⚡ BSE Performance Testing")
    print("-" * 30)
    
    # Generate test payloads
    test_payloads = []
    for i in range(5):
        payload = {
            "source_type": "user_activity",
            "event_type": "page_view",
            "user_id": f"perf_test_user_{i:03d}",
            "session_duration": 120 + (i % 300),
            "actions_per_minute": 1 + (i % 10),
            "ip_address": f"203.0.113.{i % 255}"
        }
        test_payloads.append(payload)
    
    print("Testing sequential processing...")
    start_time = time.time()
    
    sequential_results = []
    for payload in test_payloads:
        try:
            result = main_processing_pipeline(payload)
            sequential_results.append(result)
        except Exception as e:
            print(f"Error: {e}")
            sequential_results.append({"error": str(e)})
    
    sequential_time = time.time() - start_time
    
    print(f"Sequential: {len(sequential_results)} payloads in {sequential_time:.2f}s")
    if sequential_results:
        print(f"Average: {sequential_time/len(sequential_results):.3f}s per payload")
    
    print(f"Sample result: {sequential_results[0] if sequential_results else 'None'}")

if __name__ == "__main__":
    test_processing_performance()
