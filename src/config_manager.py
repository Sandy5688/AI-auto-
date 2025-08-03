import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, "config", ".env")
load_dotenv(env_path)

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Centralized configuration manager for dynamic scoring rules and job intervals
    All configurations can be adjusted from admin panel without code changes
    """
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"), 
            os.getenv("SUPABASE_KEY")
        )
        self._config_cache = {}
        self._cache_timestamp = None
        self.cache_ttl_seconds = 300  # 5 minutes cache
        
    def get_scoring_rules(self) -> Dict[str, Any]:
        """Get current BSE scoring rules from database"""
        return self._get_config("scoring_rules", default={
            "base_score": 100,
            "penalties": {
                "new_account": 20,
                "high_velocity": 15,
                "suspicious_pattern": 25,
                "bot_detected": 40,
                "fake_referral": 30,
                "vpn_usage": 10,
                "multiple_accounts": 35
            },
            "bonuses": {
                "verified_email": 5,
                "long_term_user": 10,
                "consistent_behavior": 5
            },
            "thresholds": {
                "suspicious": 50,
                "trusted": 80,
                "high_risk": 30
            },
            "multipliers": {
                "repeat_offender": 1.5,
                "first_time_flag": 1.0,
                "escalation_factor": 1.2
            }
        })
    
    def get_job_intervals(self) -> Dict[str, Any]:
        """Get current job scheduling intervals"""
        return self._get_config("job_intervals", default={
            "analytics_refresh": 30,      # seconds
            "dashboard_update": 30,       # seconds
            "bot_detection_scan": 300,    # 5 minutes
            "fake_referral_check": 600,   # 10 minutes
            "user_score_recalc": 3600,    # 1 hour
            "cleanup_old_logs": 86400,    # 24 hours
            "backup_database": 86400,     # 24 hours
            "security_audit": 604800      # 7 days
        })
    
    def get_api_limits(self) -> Dict[str, Any]:
        """Get API rate limits and quotas"""
        return self._get_config("api_limits", default={
            "openai_requests_per_hour": 100,
            "fingerprintjs_requests_per_hour": 500,
            "iphub_requests_per_hour": 1000,
            "meme_generation_daily_limit": 3,
            "max_concurrent_requests": 10,
            "rate_limit_window_minutes": 60
        })
    
    def get_alert_thresholds(self) -> Dict[str, Any]:
        """Get alerting thresholds for admin notifications"""
        return self._get_config("alert_thresholds", default={
            "high_risk_users_spike": 10,     # users in 5 minutes
            "bot_detection_spike": 50,       # detections in 10 minutes
            "fake_referral_spike": 20,       # fake referrals in 1 hour
            "system_error_rate": 0.05,       # 5% error rate
            "api_failure_rate": 0.1,         # 10% API failure rate
            "score_drop_threshold": 20,      # average score drop
            "flagged_user_percentage": 15    # % of total users
        })
    
    def update_scoring_rules(self, new_rules: Dict[str, Any], admin_user_id: str) -> bool:
        """Update scoring rules (called from admin panel)"""
        try:
            success = self._update_config("scoring_rules", new_rules, admin_user_id)
            if success:
                self._invalidate_cache()
                self._log_config_change("scoring_rules", new_rules, admin_user_id)
            return success
        except Exception as e:
            logger.error(f"Failed to update scoring rules: {e}")
            return False
    
    def update_job_intervals(self, new_intervals: Dict[str, Any], admin_user_id: str) -> bool:
        """Update job intervals (called from admin panel)"""
        try:
            success = self._update_config("job_intervals", new_intervals, admin_user_id)
            if success:
                self._invalidate_cache()
                self._log_config_change("job_intervals", new_intervals, admin_user_id)
            return success
        except Exception as e:
            logger.error(f"Failed to update job intervals: {e}")
            return False
    
    def _get_config(self, config_type: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get configuration from cache or database"""
        # Check cache first
        if self._is_cache_valid() and config_type in self._config_cache:
            return self._config_cache[config_type]
        
        try:
            # Fetch from database
            response = self.supabase.table("system_configs")\
                .select("config_data")\
                .eq("config_type", config_type)\
                .eq("is_active", True)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                config_data = response.data[0]["config_data"]
                self._config_cache[config_type] = config_data
                self._cache_timestamp = datetime.now()
                return config_data
            else:
                # Use default and store in database
                if default:
                    self._create_default_config(config_type, default)
                    return default
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching config {config_type}: {e}")
            return default or {}
    
    def _update_config(self, config_type: str, config_data: Dict[str, Any], admin_user_id: str) -> bool:
        """Update configuration in database"""
        try:
            # Deactivate old config
            self.supabase.table("system_configs")\
                .update({"is_active": False})\
                .eq("config_type", config_type)\
                .execute()
            
            # Insert new config
            new_config = {
                "config_type": config_type,
                "config_data": config_data,
                "is_active": True,
                "created_by": admin_user_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            response = self.supabase.table("system_configs")\
                .insert(new_config)\
                .execute()
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error updating config {config_type}: {e}")
            return False
    
    def _create_default_config(self, config_type: str, default_data: Dict[str, Any]):
        """Create default configuration in database"""
        try:
            default_config = {
                "config_type": config_type,
                "config_data": default_data,
                "is_active": True,
                "created_by": "system",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            self.supabase.table("system_configs")\
                .insert(default_config)\
                .execute()
                
        except Exception as e:
            logger.error(f"Error creating default config {config_type}: {e}")
    
    def _is_cache_valid(self) -> bool:
        """Check if configuration cache is still valid"""
        if not self._cache_timestamp:
            return False
        
        age_seconds = (datetime.now() - self._cache_timestamp).total_seconds()
        return age_seconds < self.cache_ttl_seconds
    
    def _invalidate_cache(self):
        """Invalidate configuration cache"""
        self._config_cache.clear()
        self._cache_timestamp = None
    
    def _log_config_change(self, config_type: str, new_config: Dict[str, Any], admin_user_id: str):
        """Log configuration changes for audit trail"""
        try:
            audit_log = {
                "action": "config_update",
                "config_type": config_type,
                "admin_user_id": admin_user_id,
                "new_config": new_config,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ip_address": "admin_panel",  # This would come from request in real implementation
                "user_agent": "admin_interface"
            }
            
            self.supabase.table("audit_logs")\
                .insert(audit_log)\
                .execute()
                
        except Exception as e:
            logger.error(f"Error logging config change: {e}")

# Global instance
config_manager = ConfigManager()
