# AI-Powered Fraud Detection Systems


## Table of Contents
1. [Introduction](#introduction)  
2. [System Components](#system-components)  
3. [File/Folder Structure](#filefolder-structure)  
4. [Setup Instructions](#setup-instructions)  
5. [Supabase Table Creation](#supabase-table-creation)  
6. [Bubble.io Configuration](#bubbleio-configuration)  
7. [Deployment](#deployment)  
8. [Testing](#testing)  
9. [Known Limitations](#known-limitations)  


---


## Introduction  
This documentation provides a comprehensive guide to setting up, deploying, and maintaining the **Milestone2 system** — a production-grade solution featuring:


- Behavioral scoring  
- Anomaly detection  
- Access control  
- Scheduled operations  
- Meme generation  
- Real-time analytics  


Built with **Python + Supabase**, integrated with **Bubble.io** frontend functionality, designed for scalability and cloud deployment (AWS/GCP compatible) following infrastructure as code principles.


---


## System Components  


| Component                          | File                     | Description                                |
|----------------------------------|--------------------------|--------------------------------------------|
| Behavioral Scoring Engine (BSE)   | `src/bse.py`             | Assigns 0-100 score based on user behavior |
| Multi-Layer Anomaly Flagger (MAF) | `src/maf.py`            | Detects suspicious activity patterns       |
| Asset Gatekeeper (AGK)            | `src/agk.py`             | Validates content generation access         |
| Scheduled Operations Layer (SOL)  | `src/sol.py`             | Automates daily/weekly/hourly tasks          |
| Meme Generation                  | `src/meme_gen.py`         | Generates memes via user prompts             |
| Real-Time Analytics Dashboard    | `src/analytics.py`        | Visualizes trends with Chart.js              |
| Webhook Server                  | `src/webhook_server.py`   | Processes BSE webhook requests               |


---


## File/Folder Structure  


```
AI-Powered Fraud Detection Systems/


├──── README.md              # Main documentation
├── src/
│   ├── bse.py                 # Behavioral Scoring Engine
│   ├── maf.py                 # Multi-Layer Anomaly Flagger
│   ├── agk.py                 # Asset Gatekeeper
│   ├── sol.py                 # Scheduled Operations Layer
│   ├── meme_gen.py            # Meme Generation Service
│   ├── analytics.py           # Analytics Dashboard
│   └── webhook_server.py      # Webhook Handler
├── tests/
│   └── test_data.sql          # SQL scripts for test data setup
├── config/
│   └── .env.example           # Environment variables template
├── requirements.txt           # Python dependencies
└── LICENSE                   # MIT License
```


---


## Setup Instructions  


### Prerequisites  
- Python 3.10+  
- Terminal (macOS/Linux/Windows)  
- [Supabase Account](https://supabase.com)  
- [Bubble.io Account](https://bubble.io)  


### Installation  
1. **Clone Repository**  
   ```
   git clone 
   cd 
   ```


2. **Setup Virtual Environment**  
   ```
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```


3. **Install Dependencies**  
   ```
   pip install -r requirements.txt
   ```


4. **Configure Environment Variables**  
   Copy `.env.example` to `.env` and fill in your credentials securely:  
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   REPLICATE_API_TOKEN=your_replicate_token
   OPENAI_API_KEY=your_openai_key
   WEBHOOK_URL=http://localhost:5001/webhook
   REPLICATE_MODEL_VERSION=your_replicate_model_version_id
   
   # Encryption key for secure token storage
   TOKEN_ENCRYPTION_KEY=your_generated_base64_fernet_key
   ```


### Running Services  
- Start the webhook server:  
  ```
  python src/webhook_server.py
  ```
- Run scheduled jobs:  
  ```
  python src/sol.py
  ```
- Run behavioral scoring engine:  
  ```
  python src/bse.py
  ```
- Run meme generator:  
  ```
  python src/meme_gen.py
  ```
- Run analytics script:  
  ```
  python src/analytics.py
  ```
- Run asset gatekeeper (if standalone):  
  ```
  python src/agk.py
  ```


---


## Supabase Table Creation  


### Users Table  
```
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  behavior_score INT DEFAULT 100,
  token_used INT DEFAULT 0,
  role TEXT,
  is_anonymous BOOLEAN DEFAULT FALSE,
  risk_flags JSONB,
  last_updated TIMESTAMPTZ,
  encrypted_token TEXT
);
```


### User Risk Flags  
```
CREATE TABLE user_risk_flags (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL REFERENCES users(id),
  flag TEXT NOT NULL,  -- 'green', 'yellow', 'red'
  risk_score INT,
  anomalies TEXT[],
  timestamp TIMESTAMPTZ DEFAULT NOW()
);
```


### Token Usage History  
```
CREATE TABLE token_usage_history (
  id SERIAL PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  tokens_used INT,
  action TEXT,
  timestamp TIMESTAMPTZ DEFAULT now()
);
```


### Job Logs  
```
CREATE TABLE job_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_name TEXT NOT NULL,
  status TEXT NOT NULL,  -- 'success'/'failure'
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  payload JSONB,
  error_message TEXT
);
```


---


## Bubble.io Configuration  


1. **Add FingerprintJS Script** to the Bubble.io settings (SEO/Metatags header):  
   ```
   
     !function(){var e=window.fpPromise,t=document.createElement("script");t.src="https://cdn.jsdelivr.net/npm/@fingerprintjs/fingerprintjs@3/dist/fp.min.js",t.onload=function(){e=FingerprintJS.load()},document.head.appendChild(t)}();
     function sendFingerprint() {
       fpPromise.then(fp => fp.get()).then(result => {
         bubble_fn_sendFingerprint(result.visitorId);
       });
     }
   
   ```


2. **Create a Bubble workflow** to call `sendFingerprint()` on user login or page load to capture device fingerprints.


---


## Deployment  


### Cloud Setup  
- Deploy the webhook server and backend components with load balancing on AWS, GCP or similar.
- Use your existing Supabase project or migrate to a new one.
  
### Webhook Server (Gunicorn example)  
```
gunicorn --workers 4 --bind 0.0.0.0:5001 src.webhook_server:app
```


### Test Deployment with cURL  
```
curl -X POST http://your-server:5001/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "testuser", "behavior_score": 90}'
```


---


## Testing  


- ✅ Unit Tests: Validate scoring and flagging logic in isolation.  
- ✅ Integration: Verify data flows through to Supabase correctly.  
- ✅ Edge Cases: Test missing or malformed payload data handling.  
- ✅ Dashboard: Confirm analytics visualization loads expected data.
- ✅ track_token_usage(user_id) is already implemented — remove the comment in Phase 2 cleanup.

---


## Known Limitations  


- ⚠️ Meme Generation APIs (Replicate/OpenAI) require billing or API tokens.  
- ⚠️ FingerprintJS integration must be completed on the Bubble.io frontend side.  
- ⚠️ Production deployment requires caching layers and load balancing for scalability.


---


**For detailed usage and troubleshooting, please refer to source code comments and module-level documentation.**


---
