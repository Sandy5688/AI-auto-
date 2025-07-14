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
This documentation provides a comprehensive guide to setting up, deploying, and maintaining the **Milestone2 system** - a production-grade solution featuring:  

- Behavioral scoring  
- Anomaly detection  
- Access control  
- Scheduled operations  
- Meme generation  
- Real-time analytics  

Built with **Python + Supabase** and integrated with **Bubble.io** for frontend functionality. Designed for scalability and cloud deployment (AWS/GCP compatible) following **Infrastructure as Code (IaC)** principles.

---

## System Components  

| Component | File | Description |
|-----------|------|-------------|
| **Behavioral Scoring Engine (BSE)** | `src/bse.py` | Assigns 0-100 score based on user behavior |
| **Multi-Layer Anomaly Flagger (MAF)** | `src/maf.py` | Detects suspicious patterns (green/yellow/red flags) |
| **Asset Gatekeeper (AGK)** | `src/agk.py` | Validates access for content generation |
| **Scheduled Operations Layer (SOL)** | `src/sol.py` | Automates daily/weekly/hourly tasks |
| **Meme Generation** | `src/meme_gen.py` | Generates memes from user prompts |
| **Real-Time Analytics Dashboard** | `src/analytics.py` | Visualizes trends with Chart.js |
| **Webhook Server** | `src/webhook_server.py` | Processes BSE webhook requests |

---

## File/Folder Structure  

```plaintext
AI-Powered Fraud Detection Systems/

├──── README.md              # Main documentation
├── src/
│   ├── bse.py                 # Behavioral Scoring
│   ├── maf.py                 # Anomaly Detection
│   ├── agk.py                 # Access Control
│   ├── sol.py                 # Scheduled Tasks
│   ├── meme_gen.py           # Meme Generator
│   ├── analytics.py           # Analytics Dashboard
│   └── webhook_server.py      # Webhook Handler
├── tests/
│   └── test_data.sql          # Test datasets
├── config/
│   └── .env.example           # Environment template
├── requirements.txt           # Python dependencies
└── LICENSE                    # MIT License
```

---

## Setup Instructions  

### Prerequisites  
- Python 3.10+  
- macOS/Linux/Windows terminal  
- [Supabase Account](https://supabase.com)  
- [Bubble.io Account](https://bubble.io)  

### Installation  
1. **Clone Repository**  
   ```bash
   git clone <repository-url>
   cd Milestone2
   ```

2. **Setup Virtual Environment**  
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**  
   Copy `config/.env.example` to `config/.env` and update:  
   ```ini
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   REPLICATE_API_TOKEN=r8_your_token
   OPENAI_API_KEY=sk-proj-your_key
   ```

### Running Components  
- Start webhook server:  
  ```bash
  python src/webhook_server.py
  ```
- Run individual modules:  
  ```bash
  python src/bse.py
  python src/sol.py
  ```

---

## Supabase Table Creation  

### Users Table  
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  behavior_score INT DEFAULT 100
);
```

### User Risk Flags  
```sql
CREATE TABLE user_risk_flags (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,
  flag TEXT NOT NULL,  -- 'green', 'yellow', 'red'
  risk_score INT,
  anomalies TEXT[],
  timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

### Job Logs  
```sql
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

1. **Add FingerprintJS Script** (Settings > SEO/Metatags):  
   ```html
   <script>
     !function(){var e=window.fpPromise,t=document.createElement("script");t.src="https://cdn.jsdelivr.net/npm/@fingerprintjs/fingerprintjs@3/dist/fp.min.js",t.onload=function(){e=FingerprintJS.load()},document.head.appendChild(t)}();
     function sendFingerprint() {
       fpPromise.then(fp => fp.get()).then(result => {
         bubble_fn_sendFingerprint(result.visitorId);
       });
     }
   </script>
   ```

2. **Create Workflow** to call `sendFingerprint()` on user login/page load.

---

## Deployment  

### Cloud Setup  
- **AWS/GCP**: Deploy with load balancing  
- **Supabase**: Use existing project or migrate  

### Webhook Server  
```bash
gunicorn --workers 4 --bind 0.0.0.0:5001 src.webhook_server:app
```

### Test Deployment  
```bash
curl -X POST http://your-server:5001/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "testuser", "behavior_score": 90}'
```

---

## Testing  
✅ **Unit Tests**: Validate individual modules  
✅ **Integration**: Verify Supabase updates  
✅ **Edge Cases**: Test missing/invalid data  
✅ **Dashboard**: Check analytics visualization  

---

## Known Limitations  
⚠️ **Meme Generation**: Requires Replicate/OpenAI billing  
⚠️ **FingerprintJS**: Pending Bubble.io integration  
⚠️ **Scalability**: Production needs caching/load balancing  

---
