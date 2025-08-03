import os
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class EnvironmentManager:
    """
    Validates and manages environment variables
    Ensures all required API keys and configurations are present
    """
    
    REQUIRED_VARS = {
        "SUPABASE_URL": "Database connection URL",
        "SUPABASE_KEY": "Database authentication key",
        "OPENAI_API_KEY": "OpenAI API key for meme generation"
    }
    
    OPTIONAL_VARS = {
        "FINGERPRINTJS_API_KEY": "FingerprintJS API key for bot detection",
        "IPHUB_API_KEY": "IPHub API key for IP reputation checks",
        "WEBHOOK_URL": "Webhook URL for score updates",
        "SLACK_WEBHOOK_URL": "Slack webhook for alerts",
        "DISCORD_WEBHOOK_URL": "Discord webhook for alerts",
        "SMTP_USERNAME": "Email server username for notifications",
        "REDIS_URL": "Redis URL for caching"
    }
    
    def __init__(self, env_file_path: Optional[str] = None):
        if env_file_path:
            load_dotenv(env_file_path)
        else:
            # Auto-detect .env file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            env_path = os.path.join(project_root, "config", ".env")
            load_dotenv(env_path)
    
    def validate_environment(self) -> Dict[str, Any]:
        """
        Validate all environment variables
        Returns validation report
        """
        report = {
            "valid": True,
            "missing_required": [],
            "missing_optional": [],
            "invalid_values": [],
            "warnings": []
        }
        
        # Check required variables
        for var_name, description in self.REQUIRED_VARS.items():
            value = os.getenv(var_name)
            if not value:
                report["missing_required"].append({
                    "name": var_name,
                    "description": description
                })
                report["valid"] = False
        
        # Check optional variables
        for var_name, description in self.OPTIONAL_VARS.items():
            value = os.getenv(var_name)
            if not value:
                report["missing_optional"].append({
                    "name": var_name,
                    "description": description
                })
        
        # Validate specific variable formats
        self._validate_specific_vars(report)
        
        return report
    
    def _validate_specific_vars(self, report: Dict[str, Any]):
        """Validate specific variable formats and values"""
        
        # Validate URLs
        url_vars = ["SUPABASE_URL", "WEBHOOK_URL", "SLACK_WEBHOOK_URL", "DISCORD_WEBHOOK_URL", "REDIS_URL"]
        for var_name in url_vars:
            value = os.getenv(var_name)
            if value and not (value.startswith("http://") or value.startswith("https://") or value.startswith("redis://")):
                report["invalid_values"].append({
                    "name": var_name,
                    "value": value,
                    "issue": "Must be a valid URL"
                })
        
        # Validate numeric values
        numeric_vars = {
            "MONTHLY_BUDGET_LIMIT": float,
            "WEBHOOK_MAX_RETRIES": int,
            "WEBHOOK_TIMEOUT": int,
            "DASHBOARD_PORT": int,
            "MAX_REQUESTS_PER_HOUR": int
        }
        
        for var_name, var_type in numeric_vars.items():
            value = os.getenv(var_name)
            if value:
                try:
                    var_type(value)
                except ValueError:
                    report["invalid_values"].append({
                        "name": var_name,
                        "value": value,
                        "issue": f"Must be a valid {var_type.__name__}"
                    })
        
        # Validate boolean values
        bool_vars = ["BOT_DETECTION_ENABLED", "TESTING_MODE", "DEBUG_MODE", "RATE_LIMIT_ENABLED"]
        for var_name in bool_vars:
            value = os.getenv(var_name)
            if value and value.lower() not in ["true", "false", "1", "0", "yes", "no", "on", "off"]:
                report["invalid_values"].append({
                    "name": var_name,
                    "value": value,
                    "issue": "Must be a valid boolean (true/false)"
                })
        
        # Check for potentially sensitive values in logs
        sensitive_vars = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]
        for var_name in os.environ:
            if any(sensitive in var_name.upper() for sensitive in sensitive_vars):
                value = os.getenv(var_name)
                if value and len(value) < 10:
                    report["warnings"].append({
                        "name": var_name,
                        "issue": "Potentially weak API key/secret (too short)"
                    })
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            "database_configured": bool(os.getenv("SUPABASE_URL")),
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
            "bot_detection_enabled": os.getenv("BOT_DETECTION_ENABLED", "false").lower() == "true",
            "fingerprintjs_configured": bool(os.getenv("FINGERPRINTJS_API_KEY")),
            "iphub_configured": bool(os.getenv("IPHUB_API_KEY")),
            "webhook_configured": bool(os.getenv("WEBHOOK_URL")),
            "email_configured": bool(os.getenv("SMTP_USERNAME")),
            "slack_configured": bool(os.getenv("SLACK_WEBHOOK_URL")),
            "discord_configured": bool(os.getenv("DISCORD_WEBHOOK_URL")),
            "redis_configured": bool(os.getenv("REDIS_URL")),
            "testing_mode": os.getenv("TESTING_MODE", "false").lower() == "true",
            "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "true"
        }
    
    def generate_env_template(self) -> str:
        """Generate .env template with all variables"""
        template_lines = [
            "# BSE System Environment Configuration",
            "# Copy this file to .env and fill in your actual values",
            "",
            "# ======== REQUIRED VARIABLES ========",
            ""
        ]
        
        for var_name, description in self.REQUIRED_VARS.items():
            template_lines.extend([
                f"# {description}",
                f"{var_name}=your_value_here",
                ""
            ])
        
        template_lines.extend([
            "# ======== OPTIONAL VARIABLES ========",
            ""
        ])
        
        for var_name, description in self.OPTIONAL_VARS.items():
            template_lines.extend([
                f"# {description}",
                f"# {var_name}=your_value_here",
                ""
            ])
        
        return "\n".join(template_lines)

# Global instance
env_manager = EnvironmentManager()
