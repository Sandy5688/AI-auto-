import sys
import os
from datetime import datetime, timezone
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

def test_sol_database_connection():
    """Test SOL can connect to database"""
    try:
        from sol import supabase, log_json
        
        # Test database connection
        response = supabase.table("users").select("id").limit(1).execute()
        
        log_json("info", "SOL database connection test successful", 
                records_found=len(response.data or []))
        print("✅ Database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_sol_logging_system():
    """Test SOL logging to required table"""
    try:
        from sol import log_scheduled_job, log_json
        
        # Test logging to logs_scheduled_jobs table
        log_scheduled_job("test_manual_job", "success", test_run=True, manual_test=True)
        
        log_json("info", "SOL logging system test completed")
        print("✅ Logging system test successful")
        return True
        
    except Exception as e:
        print(f"❌ Logging system test failed: {e}")
        return False

def test_sol_behavior_scoring():
    """Test SOL behavior score calculation"""
    try:
        from sol import calculate_behavior_score, log_json
        
        # Test with sample user data
        test_user = {
            "id": "manual_test_user",
            "behavior_score": 80,
            "is_verified": True,
            "account_age_days": 30
        }
        
        score = calculate_behavior_score(test_user)
        
        assert isinstance(score, int)
        assert 0 <= score <= 100
        
        log_json("info", "SOL behavior scoring test completed", 
                calculated_score=score, test_user=test_user["id"])
        print(f"✅ Behavior scoring test successful - Score: {score}")
        return True
        
    except Exception as e:
        print(f"❌ Behavior scoring test failed: {e}")
        return False

def test_sol_challenge_generation():
    """Test SOL weekly challenge generation"""
    try:
        from sol import create_weekly_meme_challenges, log_json
        
        challenges_count = create_weekly_meme_challenges()
        
        assert challenges_count >= 3
        assert challenges_count <= 5
        
        log_json("info", "SOL challenge generation test completed", 
                challenges_created=challenges_count)
        print(f"✅ Challenge generation test successful - Created: {challenges_count} challenges")
        return True
        
    except Exception as e:
        print(f"❌ Challenge generation test failed: {e}")
        return False

def test_sol_flag_analysis():
    """Test SOL flag analysis functionality"""
    try:
        from sol import analyze_flag_patterns, detect_high_risk_users, log_json
        
        # Create test flag data
        test_flags = [
            {"user_id": "test_user_1", "flag": "rapid_actions", "severity": "HIGH"},
            {"user_id": "test_user_1", "flag": "suspicious_login", "severity": "MEDIUM"},
            {"user_id": "test_user_2", "flag": "device_switch", "severity": "HIGH"},
        ]
        
        analysis = analyze_flag_patterns(test_flags)
        high_risk_users = detect_high_risk_users(analysis)
        
        log_json("info", "SOL flag analysis test completed", 
                total_flags=analysis["total_flags"], 
                high_risk_users=len(high_risk_users))
        print(f"✅ Flag analysis test successful - Analyzed: {analysis['total_flags']} flags, High risk: {len(high_risk_users)} users")
        return True
        
    except Exception as e:
        print(f"❌ Flag analysis test failed: {e}")
        return False

def test_sol_job_health_monitoring():
    """Test SOL job health monitoring"""
    try:
        from sol import get_job_health_status, log_json
        
        health_status = get_job_health_status()
        
        log_json("info", "SOL job health monitoring test completed", 
                jobs_monitored=len(health_status))
        print(f"✅ Job health monitoring test successful - Monitoring: {len(health_status)} jobs")
        
        for job_name, stats in health_status.items():
            success_rate = (stats["success"] / (stats["success"] + stats["failed"]) * 100) if (stats["success"] + stats["failed"]) > 0 else 0
            print(f"   📊 {job_name}: {success_rate:.1f}% success rate")
        
        return True
        
    except Exception as e:
        print(f"❌ Job health monitoring test failed: {e}")
        return False

def run_all_sol_tests():
    """Run all SOL manual tests"""
    print("🚀 SOL Manual Testing Suite")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_sol_database_connection),
        ("Logging System", test_sol_logging_system),
        ("Behavior Scoring", test_sol_behavior_scoring),
        ("Challenge Generation", test_sol_challenge_generation),
        ("Flag Analysis", test_sol_flag_analysis),
        ("Job Health Monitoring", test_sol_job_health_monitoring),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- Testing: {test_name} ---")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print(f"\n🎯 SOL Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All SOL tests passed! System is ready for production.")
    else:
        print("⚠️  Some SOL tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    run_all_sol_tests()
