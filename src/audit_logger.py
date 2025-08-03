import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from supabase import create_client
from dotenv import load_dotenv
import traceback
import hashlib

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    Comprehensive audit logging system for all risky actions
    Ensures complete traceability for security and compliance
    """
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        # Risk action categories
        self.RISK_ACTIONS = {
            "HIGH_RISK": ["score_manipulation", "admin_override", "system_bypass"],
            "MEDIUM_RISK": ["config_change", "api_key_rotation", "user_flagging"],
            "LOW_RISK": ["data_export", "report_generation", "dashboard_access"]
        }
    
    def log_user_scoring(self, user_id: str, old_score: Optional[int], new_score: int, 
                        flags: List[str], reason: str, source: str = "system") -> str:
        """Log user behavior score changes"""
        audit_id = self._generate_audit_id()
        
        audit_data = {
            "audit_id": audit_id,
            "action_type": "user_scoring",
            "risk_level": "MEDIUM_RISK",
            "user_id": user_id,
            "details": {
                "old_score": old_score,
                "new_score": new_score,
                "score_change": (new_score - old_score) if old_score else new_score,
                "flags_applied": flags,
                "reason": reason,
                "source": source
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_system": "BSE"
        }
        
        self._store_audit_log(audit_data)
        return audit_id
    
    def log_bot_detection(self, user_id: str, detection_result: Dict[str, Any], 
                         ip_address: str, user_agent: str) -> str:
        """Log bot detection events"""
        audit_id = self._generate_audit_id()
        
        risk_level = "HIGH_RISK" if detection_result.get("bot_probability", 0) > 0.8 else "MEDIUM_RISK"
        
        audit_data = {
            "audit_id": audit_id,
            "action_type": "bot_detection",
            "risk_level": risk_level,
            "user_id": user_id,
            "details": {
                "bot_probability": detection_result.get("bot_probability"),
                "bot_signals": detection_result.get("bot_signals", []),
                "detection_method": detection_result.get("method", "unknown"),
                "ip_address": ip_address,
                "user_agent_hash": hashlib.sha256(user_agent.encode()).hexdigest()[:16],
                "confidence_score": detection_result.get("confidence", 0)
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_system": "Bot_Detection"
        }
        
        self._store_audit_log(audit_data)
        return audit_id
    
    def log_fake_referral(self, referrer_id: str, referred_id: str, detection_details: Dict[str, Any]) -> str:
        """Log fake referral detection"""
        audit_id = self._generate_audit_id()
        
        audit_data = {
            "audit_id": audit_id,
            "action_type": "fake_referral_detection",
            "risk_level": "HIGH_RISK",
            "user_id": referrer_id,
            "details": {
                "referred_user_id": referred_id,
                "is_fake": detection_details.get("is_fake_referral", False),
                "fake_signals": detection_details.get("fake_signals", []),
                "risk_score": detection_details.get("risk_score", 0),
                "detection_rules_triggered": detection_details.get("rules_triggered", [])
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_system": "Fake_Referral_Filter"
        }
        
        self._store_audit_log(audit_data)
        return audit_id
    
    def log_meme_generation(self, user_id: str, prompt: str, tone: str, 
                           tokens_used: int, success: bool, error: Optional[str] = None) -> str:
        """Log meme generation activities"""
        audit_id = self._generate_audit_id()
        
        audit_data = {
            "audit_id": audit_id,
            "action_type": "meme_generation",
            "risk_level": "LOW_RISK",
            "user_id": user_id,
            "details": {
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                "tone": tone,
                "tokens_used": tokens_used,
                "generation_success": success,
                "error_message": error,
                "prompt_length": len(prompt)
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_system": "Meme_Generator"
        }
        
        self._store_audit_log(audit_data)
        return audit_id
    
    def log_admin_action(self, admin_user_id: str, action: str, target_user_id: Optional[str],
                        details: Dict[str, Any], ip_address: str = "unknown") -> str:
        """Log administrative actions"""
        audit_id = self._generate_audit_id()
        
        # Determine risk level based on action
        risk_level = "HIGH_RISK"
        for level, actions in self.RISK_ACTIONS.items():
            if any(risk_action in action.lower() for risk_action in actions):
                risk_level = level
                break
        
        audit_data = {
            "audit_id": audit_id,
            "action_type": "admin_action",
            "risk_level": risk_level,
            "user_id": target_user_id,
            "admin_user_id": admin_user_id,
            "details": {
                "action": action,
                "action_details": details,
                "admin_ip": ip_address,
                "requires_approval": risk_level == "HIGH_RISK"
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_system": "Admin_Panel"
        }
        
        self._store_audit_log(audit_data)
        return audit_id
    
    def log_api_access(self, endpoint: str, user_id: Optional[str], ip_address: str,
                      success: bool, response_code: int, error: Optional[str] = None) -> str:
        """Log API access attempts"""
        audit_id = self._generate_audit_id()
        
        risk_level = "HIGH_RISK" if not success and response_code in [401, 403] else "LOW_RISK"
        
        audit_data = {
            "audit_id": audit_id,
            "action_type": "api_access",
            "risk_level": risk_level,
            "user_id": user_id,
            "details": {
                "endpoint": endpoint,
                "ip_address": ip_address,
                "success": success,
                "response_code": response_code,
                "error_message": error,
                "potential_attack": response_code in [401, 403, 429]
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_system": "API_Gateway"
        }
        
        self._store_audit_log(audit_data)
        return audit_id
    
    def log_system_event(self, event_type: str, details: Dict[str, Any], 
                        risk_level: str = "LOW_RISK") -> str:
        """Log general system events"""
        audit_id = self._generate_audit_id()
        
        audit_data = {
            "audit_id": audit_id,
            "action_type": "system_event",
            "risk_level": risk_level,
            "user_id": None,
            "details": {
                "event_type": event_type,
                "event_details": details,
                "system_state": self._get_system_state()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_system": "System_Monitor"
        }
        
        self._store_audit_log(audit_data)
        return audit_id
    
    def get_audit_trail(self, user_id: Optional[str] = None, hours: int = 24, 
                       risk_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve audit trail for analysis"""
        try:
            since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            query = self.supabase.table("audit_logs")\
                .select("*")\
                .gte("timestamp", since_time.isoformat())\
                .order("timestamp", desc=True)
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            if risk_level:
                query = query.eq("risk_level", risk_level)
            
            response = query.execute()
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error retrieving audit trail: {e}")
            return []
    
    def get_risk_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get risk activity summary"""
        try:
            audit_data = self.get_audit_trail(hours=hours)
            
            summary = {
                "total_events": len(audit_data),
                "risk_breakdown": {"HIGH_RISK": 0, "MEDIUM_RISK": 0, "LOW_RISK": 0},
                "action_types": {},
                "unique_users": set(),
                "suspicious_patterns": []
            }
            
            for event in audit_data:
                # Risk level counts
                risk_level = event.get("risk_level", "LOW_RISK")
                summary["risk_breakdown"][risk_level] += 1
                
                # Action type counts
                action_type = event.get("action_type", "unknown")
                summary["action_types"][action_type] = summary["action_types"].get(action_type, 0) + 1
                
                # Unique users
                if event.get("user_id"):
                    summary["unique_users"].add(event["user_id"])
            
            summary["unique_users"] = len(summary["unique_users"])
            
            # Detect suspicious patterns
            summary["suspicious_patterns"] = self._detect_suspicious_patterns(audit_data)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating risk summary: {e}")
            return {"error": str(e)}
    
    def _store_audit_log(self, audit_data: Dict[str, Any]) -> bool:
        """Store audit log in database"""
        try:
            response = self.supabase.table("audit_logs").insert(audit_data).execute()
            
            # Also log to file for backup
            self._log_to_file(audit_data)
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error storing audit log: {e}")
            
            # Fallback to file logging
            self._log_to_file(audit_data, error=str(e))
            return False
    
    def _log_to_file(self, audit_data: Dict[str, Any], error: Optional[str] = None):
        """Backup audit logging to file"""
        try:
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(log_dir, f"audit_{date_str}.log")
            
            log_entry = {
                "timestamp": audit_data["timestamp"],
                "audit_id": audit_data["audit_id"],
                "action_type": audit_data["action_type"],
                "risk_level": audit_data["risk_level"],
                "user_id": audit_data.get("user_id"),
                "details": audit_data["details"],
                "source_system": audit_data["source_system"]
            }
            
            if error:
                log_entry["storage_error"] = error
            
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Failed to log to file: {e}")
    
    def _generate_audit_id(self) -> str:
        """Generate unique audit ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_part = os.urandom(4).hex()
        return f"AUD_{timestamp}_{random_part}"
    
    def _get_system_state(self) -> Dict[str, Any]:
        """Get current system state for context"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "process_id": os.getpid(),
            "environment": os.getenv("ENVIRONMENT", "production")
        }
    
    def _detect_suspicious_patterns(self, audit_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect suspicious patterns in audit data"""
        patterns = []
        
        # Group by user and IP for pattern detection
        user_actions = {}
        ip_actions = {}
        
        for event in audit_data:
            user_id = event.get("user_id")
            ip_address = event.get("details", {}).get("ip_address")
            
            if user_id:
                if user_id not in user_actions:
                    user_actions[user_id] = []
                user_actions[user_id].append(event)
            
            if ip_address:
                if ip_address not in ip_actions:
                    ip_actions[ip_address] = []
                ip_actions[ip_address].append(event)
        
        # Detect high-frequency user actions
        for user_id, actions in user_actions.items():
            if len(actions) > 50:  # More than 50 actions in time period
                patterns.append({
                    "type": "high_frequency_user",
                    "user_id": user_id,
                    "action_count": len(actions),
                    "risk_level": "HIGH"
                })
        
        # Detect suspicious IP activity
        for ip_address, actions in ip_actions.items():
            high_risk_actions = [a for a in actions if a.get("risk_level") == "HIGH_RISK"]
            if len(high_risk_actions) > 5:
                patterns.append({
                    "type": "suspicious_ip_activity",
                    "ip_address": ip_address,
                    "high_risk_actions": len(high_risk_actions),
                    "risk_level": "HIGH"
                })
        
        return patterns

# Global instance
audit_logger = AuditLogger()
