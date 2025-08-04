import os
import logging
import requests
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from dotenv import load_dotenv
from supabase import create_client
from dataclasses import dataclass
import threading
import time

# Load environment configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, "config", ".env")
load_dotenv(env_path)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FINGERPRINTJS_API_KEY = os.getenv("FINGERPRINTJS_API_KEY")
FINGERPRINTJS_API_URL = "https://api.fpjs.io/events"

# Anomaly detection thresholds#
ANOMALY_THRESHOLDS = {
    "same_ip_signups": 5,  # Max signups per IP per hour
    "same_device_signups": 3,  # Max signups per device per hour
    "rapid_wallet_connections": 10,  # Max wallet connections per user per 5 minutes
    "rapid_nft_listings": 15,  # Max NFT listings per user per 5 minutes
    "referral_spam_rate": 20,  # Max referrals per user per hour
    "duplicate_meme_uploads": 3,  # Max same meme uploads per user
    "login_velocity_per_ip": 10,  # Max logins per IP per 5 minutes
    "device_switching_velocity": 5,  # Max different devices per user per hour
}

ANOMALY_THRESHOLDS = {
    "same_ip_signups": 5,  # Max signups per IP per hour
    "same_device_signups": 3,  # Max signups per device per hour
    "rapid_wallet_connections": 10,  # Max wallet connections per user per 5 minutes
    "rapid_nft_listings": 15,  # Max NFT listings per user per 5 minutes
    "referral_spam_rate": 20,  # Max referrals per user per hour
    "duplicate_meme_uploads": 3,  # Max same meme uploads per user
    "login_velocity_per_ip": 10,  # Max logins per IP per 5 minutes
    "device_switching_velocity": 5,  # Max different devices per user per hour
}


# Flag color criteria
FLAG_CRITERIA = {
    "GREEN": {"min_score": 80, "velocity": "low"},
    "YELLOW": {"score_range": (50, 79), "velocity": "medium"},
    "RED": {"max_score": 49, "velocity": "high"}
}

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@dataclass
class FingerprintData:
    """Standardized fingerprint data structure"""
    ip_address: str
    user_agent: str
    device_hash: str
    timestamp: datetime
    user_id: str
    event_type: str
    confidence_score: float = 0.0
    geolocation: dict = None
    browser_details: dict = None
    
class AnomalyPattern:
    """Base class for anomaly pattern detection"""
    def __init__(self, pattern_name: str, threshold: int, time_window_minutes: int = 60):
        self.pattern_name = pattern_name
        self.threshold = threshold
        self.time_window_minutes = time_window_minutes
    
    def detect(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Override this method in subclasses"""
        raise NotImplementedError


class SameIPSignupPattern(AnomalyPattern):
    """Detect multiple signups from same IP address"""
    
    def __init__(self):
        super().__init__("same_ip_signups", ANOMALY_THRESHOLDS["same_ip_signups"], 60)
    
    def detect(self, fingerprint_data: List[FingerprintData]) -> List[Dict[str, Any]]:
        anomalies = []
        now = datetime.now(timezone.utc)
        time_threshold = now - timedelta(minutes=self.time_window_minutes)
        
        # Filter recent signup events
        recent_signups = [
            fp for fp in fingerprint_data 
            if fp.event_type == "signup" and fp.timestamp >= time_threshold
        ]
        
        # Group by IP address
        ip_signups = defaultdict(list)
        for signup in recent_signups:
            ip_signups[signup.ip_address].append(signup)
        
        # Check threshold violations
        for ip_address, signups in ip_signups.items():
            if len(signups) > self.threshold:
                user_ids = [signup.user_id for signup in signups]
                anomalies.append({
                    "pattern": self.pattern_name,
                    "severity": "HIGH",
                    "description": f"{len(signups)} signups from IP {ip_address} in {self.time_window_minutes} minutes",
                    "affected_users": user_ids,
                    "fingerprint_data": {
                        "ip_address": ip_address,
                        "user_count": len(set(user_ids)),
                        "signup_count": len(signups),
                        "time_span": self.time_window_minutes
                    },
                    "detected_at": now.isoformat(),
                    "risk_score": min(100, (len(signups) / self.threshold) * 50)
                })
        
        return anomalies

class SameDeviceSignupPattern(AnomalyPattern):
    """Detect multiple signups from same device"""
    
    def __init__(self):
        super().__init__("same_device_signups", ANOMALY_THRESHOLDS["same_device_signups"], 60)
    
    def detect(self, fingerprint_data: List[FingerprintData]) -> List[Dict[str, Any]]:
        anomalies = []
        now = datetime.now(timezone.utc)
        time_threshold = now - timedelta(minutes=self.time_window_minutes)
        
        recent_signups = [
            fp for fp in fingerprint_data 
            if fp.event_type == "signup" and fp.timestamp >= time_threshold
        ]
        
        # Group by device hash
        device_signups = defaultdict(list)
        for signup in recent_signups:
            device_signups[signup.device_hash].append(signup)
        
        for device_hash, signups in device_signups.items():
            if len(signups) > self.threshold:
                user_ids = [signup.user_id for signup in signups]
                anomalies.append({
                    "pattern": self.pattern_name,
                    "severity": "HIGH",
                    "description": f"{len(signups)} signups from device {device_hash[:12]}... in {self.time_window_minutes} minutes",
                    "affected_users": user_ids,
                    "fingerprint_data": {
                        "device_hash": device_hash,
                        "user_count": len(set(user_ids)),
                        "signup_count": len(signups)
                    },
                    "detected_at": now.isoformat(),
                    "risk_score": min(100, (len(signups) / self.threshold) * 60)
                })
        
        return anomalies

class RapidActionPattern(AnomalyPattern):
    """Detect rapid wallet connections and NFT listings"""
    
    def __init__(self, action_type: str):
        self.action_type = action_type
        
        # Map action types to threshold keys and get thresholds
        if action_type == "wallet_connection":
            threshold_key = "rapid_wallet_connections"
            threshold = ANOMALY_THRESHOLDS["rapid_wallet_connections"]
        elif action_type == "nft_listing":
            threshold_key = "rapid_nft_listings"
            threshold = ANOMALY_THRESHOLDS["rapid_nft_listings"]
        else:
            threshold_key = f"rapid_{action_type.lower()}"
            threshold = ANOMALY_THRESHOLDS.get(threshold_key, 10)  # Default threshold
        
        # Call parent constructor with ALL required parameters
        super().__init__(threshold_key, threshold, 5)  # pattern_name, threshold, time_window_minutes
    
    def detect(self, fingerprint_data: List[FingerprintData]) -> List[Dict[str, Any]]:
        anomalies = []
        now = datetime.now(timezone.utc)
        time_threshold = now - timedelta(minutes=self.time_window_minutes)
        
        # Filter recent actions by type
        recent_actions = [
            fp for fp in fingerprint_data 
            if (fp.event_type == self.action_type and 
                fp.timestamp >= time_threshold and 
                fp.timestamp <= now)
        ]
        
        # Debug logging
        logger.debug(f"Time window: {time_threshold} to {now}")
        logger.debug(f"Found {len(recent_actions)} {self.action_type} actions in {len(fingerprint_data)} total events")
        
        # Group by user
        user_actions = defaultdict(list)
        for action in recent_actions:
            user_actions[action.user_id].append(action)
        
        for user_id, actions in user_actions.items():
            logger.debug(f"User {user_id} has {len(actions)} actions, threshold is {self.threshold}")
            if len(actions) > self.threshold:
                anomalies.append({
                    "pattern": self.pattern_name,
                    "severity": "MEDIUM",
                    "description": f"User {user_id} performed {len(actions)} {self.action_type} actions in {self.time_window_minutes} minutes",
                    "affected_users": [user_id],
                    "fingerprint_data": {
                        "user_id": user_id,
                        "action_count": len(actions),
                        "action_type": self.action_type,
                        "time_window": self.time_window_minutes
                    },
                    "detected_at": now.isoformat(),
                    "risk_score": min(100, (len(actions) / self.threshold) * 40)
                })
        
        return anomalies


class LoginVelocityPattern(AnomalyPattern):
    def detect(self, fingerprint_data: List[FingerprintData]) -> List[Dict[str, Any]]:
        anomalies = []
        now = datetime.now(timezone.utc)
        time_threshold = now - timedelta(minutes=self.time_window_minutes)
        
        # Filter recent logins - IMPROVED TIME LOGIC
        recent_logins = [
            fp for fp in fingerprint_data 
            if (fp.event_type == "login" and 
                fp.timestamp >= time_threshold and 
                fp.timestamp <= now)
        ]
        
        logger.debug(f"Found {len(recent_logins)} recent logins out of {len(fingerprint_data)} events")
        
        # Group by IP address
        ip_logins = defaultdict(list)
        for login in recent_logins:
            ip_logins[login.ip_address].append(login)
        
        for ip_address, logins in ip_logins.items():
            logger.debug(f"IP {ip_address} has {len(logins)} logins, threshold is {self.threshold}")
            if len(logins) > self.threshold:
                user_ids = list(set([login.user_id for login in logins]))
                
                anomalies.append({
                    "pattern": "login_velocity_per_ip",
                    "severity": "HIGH",
                    "description": f"{len(logins)} logins from IP {ip_address} in {self.time_window_minutes} minutes ({len(user_ids)} unique users)",
                    "affected_users": user_ids,
                    "fingerprint_data": {
                        "ip_address": str(ip_address),
                        "login_count": len(logins),
                        "unique_users": len(user_ids),
                        "velocity": len(logins) / self.time_window_minutes
                    },
                    "detected_at": now.isoformat(),
                    "risk_score": min(100, (len(logins) / self.threshold) * 70)
                })
        
        return anomalies

class ReferralSpamPattern(AnomalyPattern):
    """Detect referral link spamming"""
    
    def __init__(self):
        super().__init__("referral_spam", ANOMALY_THRESHOLDS["referral_spam_rate"], 60)
    
    def detect(self, fingerprint_data: List[FingerprintData]) -> List[Dict[str, Any]]:
        anomalies = []
        now = datetime.now(timezone.utc)
        time_threshold = now - timedelta(minutes=self.time_window_minutes)
        
        recent_referrals = [
            fp for fp in fingerprint_data 
            if fp.event_type == "referral" and fp.timestamp >= time_threshold
        ]
        
        # Group by user
        user_referrals = defaultdict(list)
        for referral in recent_referrals:
            user_referrals[referral.user_id].append(referral)
        
        for user_id, referrals in user_referrals.items():
            if len(referrals) > self.threshold:
                # Check for referral diversity (spamming same links)
                unique_sources = set()
                for ref in referrals:
                    if hasattr(ref, 'browser_details') and ref.browser_details:
                        unique_sources.add(ref.browser_details.get('referrer_url', 'unknown'))
                
                diversity_score = len(unique_sources) / len(referrals) if referrals else 0
                
                anomalies.append({
                    "pattern": self.pattern_name,
                    "severity": "MEDIUM" if diversity_score > 0.3 else "HIGH",
                    "description": f"User {user_id} sent {len(referrals)} referrals in {self.time_window_minutes} minutes (diversity: {diversity_score:.2f})",
                    "affected_users": [user_id],
                    "fingerprint_data": {
                        "user_id": user_id,
                        "referral_count": len(referrals),
                        "unique_sources": len(unique_sources),
                        "diversity_score": diversity_score
                    },
                    "detected_at": now.isoformat(),
                    "risk_score": min(100, (len(referrals) / self.threshold) * (60 if diversity_score < 0.3 else 35))
                })
        
        return anomalies

class DuplicateMemePattern(AnomalyPattern):
    """Detect same meme uploaded multiple times"""
    
    def __init__(self):
        super().__init__("duplicate_memes", ANOMALY_THRESHOLDS["duplicate_meme_uploads"], 1440)  # 24-hour window
    
    def detect(self, fingerprint_data: List[FingerprintData]) -> List[Dict[str, Any]]:
        anomalies = []
        now = datetime.now(timezone.utc)
        time_threshold = now - timedelta(minutes=self.time_window_minutes)
        
        # Get recent meme uploads
        recent_uploads = [
            fp for fp in fingerprint_data 
            if fp.event_type == "meme_upload" and fp.timestamp >= time_threshold
        ]
        
        # Group by user and meme hash
        user_memes = defaultdict(lambda: defaultdict(list))
        for upload in recent_uploads:
            meme_hash = getattr(upload, 'meme_hash', None)
            if meme_hash:
                user_memes[upload.user_id][meme_hash].append(upload)
        
        for user_id, memes in user_memes.items():
            for meme_hash, uploads in memes.items():
                if len(uploads) > self.threshold:
                    anomalies.append({
                        "pattern": self.pattern_name,
                        "severity": "LOW",
                        "description": f"User {user_id} uploaded same meme {len(uploads)} times in {self.time_window_minutes//60} hours",
                        "affected_users": [user_id],
                        "fingerprint_data": {
                            "user_id": user_id,
                            "meme_hash": meme_hash,
                            "upload_count": len(uploads),
                            "time_span_hours": self.time_window_minutes // 60
                        },
                        "detected_at": now.isoformat(),
                        "risk_score": min(100, (len(uploads) / self.threshold) * 25)
                    })
        
        return anomalies

class LoginVelocityPattern(AnomalyPattern):
    """Detect high login velocity from same IP"""
    
    def __init__(self):
        super().__init__("login_velocity_per_ip", ANOMALY_THRESHOLDS["login_velocity_per_ip"], 5)
    
    def detect(self, fingerprint_data: List[FingerprintData]) -> List[Dict[str, Any]]:
        anomalies = []
        now = datetime.now(timezone.utc)
        time_threshold = now - timedelta(minutes=self.time_window_minutes)
        
        recent_logins = [
            fp for fp in fingerprint_data 
            if fp.event_type == "login" and fp.timestamp >= time_threshold
        ]
        
        # Group by IP address
        ip_logins = defaultdict(list)
        for login in recent_logins:
            ip_logins[login.ip_address].append(login)
        
        for ip_address, logins in ip_logins.items():
            if len(logins) > self.threshold:
                user_ids = list(set([login.user_id for login in logins]))
                
                anomalies.append({
                    "pattern": "login_velocity_per_ip",  # Fixed pattern name
                    "severity": "HIGH",
                    "description": f"{len(logins)} logins from IP {ip_address} in {self.time_window_minutes} minutes ({len(user_ids)} unique users)",
                    "affected_users": user_ids,
                    "fingerprint_data": {
                        "ip_address": str(ip_address),  # Convert INET to string
                        "login_count": len(logins),
                        "unique_users": len(user_ids),
                        "velocity": len(logins) / self.time_window_minutes
                    },
                    "detected_at": now.isoformat(),
                    "risk_score": min(100, (len(logins) / self.threshold) * 70)
                })
        
        return anomalies

class FingerprintCollector:
    """Collect and manage fingerprint data"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(hours=2)
    
    def collect_fingerprint(self, user_id: str, event_type: str, request_data: Dict[str, Any]) -> FingerprintData:
        """Collect comprehensive fingerprint data"""
        
        # Extract basic fingerprint data
        ip_address = self.extract_ip_address(request_data)
        user_agent = request_data.get('user_agent', '')
        
        # Generate device hash
        device_hash = self.generate_device_hash(ip_address, user_agent, request_data)
        
        # Get enhanced fingerprint data from FingerprintJS if available
        enhanced_data = self.get_fingerprintjs_data(request_data.get('visitor_id'))
        
        fingerprint = FingerprintData(
            ip_address=ip_address,
            user_agent=user_agent,
            device_hash=device_hash,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            event_type=event_type,
            confidence_score=enhanced_data.get('confidence', 0.8),
            geolocation=enhanced_data.get('geolocation', {}),
            browser_details=enhanced_data.get('browser_details', {})
        )
        
        # Store in database
        self.store_fingerprint(fingerprint)
        
        return fingerprint
    
    def extract_ip_address(self, request_data: Dict[str, Any]) -> str:
        """Extract IP address from request data"""
        # Check various headers for real IP
        ip_headers = [
            'x_forwarded_for',
            'x_real_ip',
            'remote_addr',
            'client_ip',
            'x_client_ip'
        ]
        
        for header in ip_headers:
            ip = request_data.get(header)
            if ip and ip != '127.0.0.1':
                # Handle comma-separated IPs (X-Forwarded-For)
                return ip.split(',')[0].strip()
        
        return request_data.get('ip_address', 'unknown')
    
    def generate_device_hash(self, ip_address: str, user_agent: str, request_data: Dict[str, Any]) -> str:
        """Generate unique device hash from fingerprint data"""
        
        fingerprint_components = [
            ip_address,
            user_agent,
            request_data.get('screen_resolution', ''),
            request_data.get('timezone', ''),
            request_data.get('language', ''),
            request_data.get('platform', ''),
            str(request_data.get('canvas_fingerprint', '')),
            str(request_data.get('webgl_fingerprint', ''))
        ]
        
        fingerprint_string = '|'.join(str(comp) for comp in fingerprint_components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    def get_fingerprintjs_data(self, visitor_id: Optional[str]) -> Dict[str, Any]:
        """Get enhanced data from FingerprintJS Pro API"""
        
        if not visitor_id or not FINGERPRINTJS_API_KEY:
            return {}
        
        # Check cache first
        cache_key = f"fpjs_{visitor_id}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now(timezone.utc) - timestamp < self.cache_ttl:
                return cached_data
        
        try:
            headers = {
                'Auth-API-Key': FINGERPRINTJS_API_KEY,
                'Content-Type': 'application/json'
            }
            
            url = f"{FINGERPRINTJS_API_URL}/{visitor_id}"
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                enhanced_data = {
                    'confidence': data.get('products', {}).get('identification', {}).get('data', {}).get('confidence', {}).get('score', 0.8),
                    'geolocation': data.get('products', {}).get('geolocation', {}).get('data', {}),
                    'browser_details': {
                        'browser': data.get('products', {}).get('browserDetails', {}).get('data', {}),
                        'os': data.get('products', {}).get('os', {}).get('data', {}),
                        'device': data.get('products', {}).get('device', {}).get('data', {})
                    }
                }
                
                # Cache the result
                self.cache[cache_key] = (enhanced_data, datetime.now(timezone.utc))
                
                logger.info(f"Retrieved FingerprintJS data for visitor {visitor_id}")
                return enhanced_data
            
        except Exception as e:
            logger.warning(f"Failed to get FingerprintJS data for {visitor_id}: {e}")
        
        return {}
    
    def store_fingerprint(self, fingerprint: FingerprintData):
        """Store fingerprint data in database"""
        try:
            fingerprint_record = {
                "user_id": fingerprint.user_id,
                "event_type": fingerprint.event_type,
                "ip_address": fingerprint.ip_address,
                "user_agent": fingerprint.user_agent,
                "device_hash": fingerprint.device_hash,
                "timestamp": fingerprint.timestamp.isoformat(),
                "confidence_score": fingerprint.confidence_score,
                "geolocation": json.dumps(fingerprint.geolocation or {}),
                "browser_details": json.dumps(fingerprint.browser_details or {}),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("fingerprint_data").insert(fingerprint_record).execute()
            logger.debug(f"Stored fingerprint for user {fingerprint.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store fingerprint data: {e}")

class MultiLayerAnomalyFlagger:
    """Main MAF system orchestrator"""
    
    def __init__(self):
        self.fingerprint_collector = FingerprintCollector()
        
        # Initialize all anomaly patterns
        self.patterns = [
            SameIPSignupPattern(),
            SameDeviceSignupPattern(),
            RapidActionPattern("wallet_connection"),
            RapidActionPattern("nft_listing"),
            ReferralSpamPattern(),
            DuplicateMemePattern(),
            LoginVelocityPattern()
        ]
        
        logger.info(f"Initialized MAF with {len(self.patterns)} anomaly patterns")
    
    def process_event(self, user_id: str, event_type: str, request_data: Dict[str, Any], behavior_score: Optional[int] = None) -> Dict[str, Any]:
        """Process a single event and detect anomalies"""
        
        # Collect fingerprint data
        fingerprint = self.fingerprint_collector.collect_fingerprint(user_id, event_type, request_data)
        
        # Get recent fingerprint data for pattern detection
        recent_data = self.get_recent_fingerprint_data(hours=24)
        
        # Run anomaly detection
        all_anomalies = []
        for pattern in self.patterns:
            try:
                anomalies = pattern.detect(recent_data)
                all_anomalies.extend(anomalies)
            except Exception as e:
                logger.error(f"Error in pattern {pattern.pattern_name}: {e}")
        
        # Calculate velocity metrics
        velocity_metrics = self.calculate_velocity_metrics(user_id, event_type)
        
        # Determine flag color
        flag_color = self.determine_flag_color(behavior_score, velocity_metrics, all_anomalies)
        
        # Store anomalies
        for anomaly in all_anomalies:
            self.store_anomaly(anomaly)
        
        result = {
            "user_id": user_id,
            "event_type": event_type,
            "fingerprint_id": fingerprint.device_hash,
            "flag_color": flag_color,
            "anomalies_detected": len(all_anomalies),
            "anomalies": all_anomalies,
            "velocity_metrics": velocity_metrics,
            "behavior_score": behavior_score,
            "confidence_score": fingerprint.confidence_score,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "geolocation": fingerprint.geolocation
        }
        
        logger.info(f"MAF processed event for user {user_id}: {flag_color} flag, {len(all_anomalies)} anomalies detected")
        return result
    
    def get_recent_fingerprint_data(self, hours: int = 24) -> List[FingerprintData]:
        """Get recent fingerprint data for analysis"""
        try:
            since_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            
            response = supabase.table("fingerprint_data").select("*").gte("timestamp", since_time).execute()
            
            fingerprint_data = []
            for record in (response.data or []):
                try:
                    fingerprint = FingerprintData(
                        ip_address=record["ip_address"],
                        user_agent=record["user_agent"],
                        device_hash=record["device_hash"],
                        timestamp=datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")),
                        user_id=record["user_id"],
                        event_type=record["event_type"],
                        confidence_score=record.get("confidence_score", 0.8),
                        geolocation=json.loads(record.get("geolocation", "{}")),
                        browser_details=json.loads(record.get("browser_details", "{}"))
                    )
                    fingerprint_data.append(fingerprint)
                except Exception as e:
                    logger.warning(f"Error parsing fingerprint record: {e}")
            
            return fingerprint_data
            
        except Exception as e:
            logger.error(f"Error getting recent fingerprint data: {e}")
            return []
    
    def calculate_velocity_metrics(self, user_id: str, event_type: str) -> Dict[str, Any]:
        """Calculate velocity metrics for user behavior"""
        
        now = datetime.now(timezone.utc)
        metrics = {
            "events_last_hour": 0,
            "events_last_5_minutes": 0,
            "unique_ips_last_hour": set(),
            "unique_devices_last_hour": set(),
            "velocity_score": "low"
        }
        
        try:
            # Get user events in last hour
            hour_ago = (now - timedelta(hours=1)).isoformat()
            response = supabase.table("fingerprint_data").select("*").eq("user_id", user_id).gte("timestamp", hour_ago).execute()
            
            five_minutes_ago = now - timedelta(minutes=5)
            
            for record in (response.data or []):
                record_time = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
                
                metrics["events_last_hour"] += 1
                metrics["unique_ips_last_hour"].add(record["ip_address"])
                metrics["unique_devices_last_hour"].add(record["device_hash"])
                
                # Count events in last 5 minutes
                if record_time >= five_minutes_ago:
                    metrics["events_last_5_minutes"] += 1
            
            # Convert sets to counts
            metrics["unique_ips_last_hour"] = len(metrics["unique_ips_last_hour"])
            metrics["unique_devices_last_hour"] = len(metrics["unique_devices_last_hour"])
            
            # UPDATED velocity score calculation with lower thresholds for testing
            if (metrics["events_last_5_minutes"] > 10 or 
                metrics["events_last_hour"] > 15 or  # Lowered from 50 to 15
                metrics["unique_devices_last_hour"] > 2):
                metrics["velocity_score"] = "high"
            elif (metrics["events_last_5_minutes"] > 5 or 
                metrics["events_last_hour"] > 8 or
                metrics["unique_devices_last_hour"] > 1):
                metrics["velocity_score"] = "medium"
            else:
                metrics["velocity_score"] = "low"
                
            logger.debug(f"Velocity metrics for {user_id}: {metrics}")
            
        except Exception as e:
            logger.error(f"Error calculating velocity metrics: {e}")
        
        return metrics
    
    def determine_flag_color(self, behavior_score: Optional[int], velocity_metrics: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> str:
        """Determine flag color based on score, velocity, and anomalies"""
        
        # High-severity anomalies trigger RED flag immediately
        high_severity_anomalies = [a for a in anomalies if a.get("severity") == "HIGH"]
        if high_severity_anomalies:
            return "RED"
        
        # No behavior score provided - use velocity and anomalies only
        if behavior_score is None:
            if len(anomalies) > 0 or velocity_metrics["velocity_score"] == "high":
                return "YELLOW"
            return "GREEN"
        
        # RED: Score <50 or anomaly spike
        if behavior_score < 50:
            return "RED"
        
        # YELLOW: Score 50-79 with medium risk patterns
        if 50 <= behavior_score <= 79:
            if len(anomalies) > 0 or velocity_metrics["velocity_score"] in ["medium", "high"]:
                return "YELLOW"
        
        # GREEN: Score >80 with low velocity
        if behavior_score > 80 and velocity_metrics["velocity_score"] == "low" and len(anomalies) == 0:
            return "GREEN"
        
        # Default to YELLOW for edge cases
        return "YELLOW"
    
    def store_anomaly(self, anomaly: Dict[str, Any]):
        """Store detected anomaly in database"""
        try:
            anomaly_record = {
                "pattern_name": anomaly["pattern"],
                "severity": anomaly["severity"],
                "description": anomaly["description"],
                "affected_users": anomaly["affected_users"],
                "fingerprint_data": json.dumps(anomaly["fingerprint_data"]),
                "detected_at": anomaly["detected_at"],
                "risk_score": anomaly["risk_score"],
                "status": "active"
            }
            
            supabase.table("detected_anomalies").insert(anomaly_record).execute()
            logger.debug(f"Stored anomaly: {anomaly['pattern']}")
            
        except Exception as e:
            logger.error(f"Failed to store anomaly: {e}")
    
    def get_user_flag_history(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get user's flag history for analysis"""
        try:
            since_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            # Get user's fingerprint data and calculate flags over time
            response = supabase.table("fingerprint_data").select("*").eq("user_id", user_id).gte("timestamp", since_date).order("timestamp").execute()
            
            flag_history = []
            for record in (response.data or []):
                # Simple flag calculation based on event frequency
                # In production, you'd store flag results or recalculate with stored behavior scores
                flag_history.append({
                    "timestamp": record["timestamp"],
                    "event_type": record["event_type"],
                    "ip_address": record["ip_address"],
                    "device_hash": record["device_hash"][:12] + "...",
                })
            
            return flag_history
            
        except Exception as e:
            logger.error(f"Error getting flag history for user {user_id}: {e}")
            return []

# Integration with BSE
def integrate_maf_with_bse(bse_result: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Integrate MAF with Enhanced BSE results"""
    
    maf = MultiLayerAnomalyFlagger()
    
    user_id = bse_result.get("user_id")
    behavior_score = bse_result.get("behavior_score")
    event_type = request_data.get("event_type", "unknown")
    
    # Process through MAF
    maf_result = maf.process_event(user_id, event_type, request_data, behavior_score)
    
    # Combine results
    integrated_result = {
        **bse_result,  # Keep all BSE results
        "maf_analysis": {
            "flag_color": maf_result["flag_color"],
            "anomalies_detected": maf_result["anomalies_detected"],
            "anomalies": maf_result["anomalies"],
            "velocity_metrics": maf_result["velocity_metrics"],
            "fingerprint_id": maf_result["fingerprint_id"],
            "confidence_score": maf_result["confidence_score"],
            "geolocation": maf_result.get("geolocation", {})
        },
        "final_risk_assessment": determine_final_risk_level(bse_result, maf_result)
    }
    
    return integrated_result

def determine_final_risk_level(bse_result: Dict[str, Any], maf_result: Dict[str, Any]) -> str:
    """Determine final risk level combining BSE and MAF results"""
    
    bse_risk = bse_result.get("risk_level", "normal")
    maf_flag = maf_result.get("flag_color", "GREEN")
    
    # Risk escalation matrix
    risk_matrix = {
        ("suspicious", "RED"): "CRITICAL",
        ("suspicious", "YELLOW"): "HIGH", 
        ("suspicious", "GREEN"): "MEDIUM",
        ("normal", "RED"): "HIGH",
        ("normal", "YELLOW"): "MEDIUM",
        ("normal", "GREEN"): "LOW",
        ("highly_trusted", "RED"): "MEDIUM",
        ("highly_trusted", "YELLOW"): "LOW",
        ("highly_trusted", "GREEN"): "VERY_LOW"
    }
    
    return risk_matrix.get((bse_risk, maf_flag), "MEDIUM")

if __name__ == "__main__":
    logger.info("🔍 Multi-Layer Anomaly Flagger (MAF) System")
    
    # Example usage
    maf = MultiLayerAnomalyFlagger()
    
    # Test with sample data
    sample_request_data = {
        "ip_address": "203.0.113.50",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "screen_resolution": "1920x1080",
        "timezone": "America/New_York",
        "language": "en-US",
        "visitor_id": "sample_visitor_123"
    }
    
    result = maf.process_event("test_user_001", "signup", sample_request_data, 65)
    
    print(f"MAF Result: {json.dumps(result, indent=2)}")
