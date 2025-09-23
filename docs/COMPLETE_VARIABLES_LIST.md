# 📋 COMPLETE VARIABLES LIST - LMS MCP PROJECT

## 🔐 ENVIRONMENT VARIABLES (Already Configured)

### **LM Studio Configuration**
```bash
LM_STUDIO_BASE_URL=http://192.168.56.1:1234/v1    # Used in 3+ files
LM_STUDIO_API_KEY=lm-studio                        # Used in 3+ files  
LM_STUDIO_MODEL=qwen/qwen3-1.7b                    # Used in 3+ files
```

### **Flask Configuration**
```bash
FLASK_HOST=127.0.0.1                               # webapp_chatbot.py
FLASK_PORT=5000                                    # webapp_chatbot.py
FLASK_DEBUG=true                                   # webapp_chatbot.py
FLASK_SECRET_KEY=your-secret-key-change-this       # webapp_chatbot.py
```

### **Wazuh API Configuration**
```bash
WAZUH_API_URL=https://localhost:55000              # wazuh_fastmcp_server.py
WAZUH_USERNAME=wazuh-wui                           # wazuh_fastmcp_server.py
WAZUH_PASSWORD=MyS3cr37P450r.*-                    # wazuh_fastmcp_server.py
WAZUH_VERIFY_SSL=false                             # wazuh_fastmcp_server.py
WAZUH_TIMEOUT=30                                   # wazuh_fastmcp_server.py
```

### **Telegram Bot Configuration**
```bash
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE             # telegram_config.py
```

## ❌ HARDCODED VARIABLES (Need to be Environment Variables)

### **Database Paths**
```python
# CURRENT HARDCODED VALUES:
'wazuh_archives.db'                    # telegram_security_bot.py:634
'data/wazuh_archives.db'              # check_db.py:4  
'wazuh_archives.db'                   # config/telegram_bot_config.py:91
'chat_history.db'                     # config/telegram_bot_config.py:92

# SHOULD BE:
DATABASE_DIR=./data
WAZUH_DB_NAME=wazuh_archives.db
CHAT_DB_NAME=chat_history.db
```

### **Network & Paths**
```python
# CURRENT HARDCODED VALUES:
"http://0.0.0.0:1234/v1"              # docs/DOKUMENTASI LM STUDIO DENGAN TOOLS.py:20
"http://192.168.56.1:1234/v1"         # config/telegram_bot_config.py:82
"/var/ossec/logs/archives/archives.json"  # wazuh_realtime_server.py:238
"single-node-wazuh.manager-1"         # wazuh_realtime_server.py:237

# SHOULD BE:
LM_STUDIO_DOCS_URL=http://0.0.0.0:1234/v1
WAZUH_ARCHIVES_PATH=/var/ossec/logs/archives/archives.json
DOCKER_CONTAINER_NAME=single-node-wazuh.manager-1
```

### **Flask App Settings**
```python
# CURRENT HARDCODED VALUES:
debug=True, host='0.0.0.0', port=5000  # dashboard_app.py:281

# SHOULD BE:
DASHBOARD_DEBUG=false
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=5000
```

### **Log File Paths**
```python
# CURRENT HARDCODED VALUES:
'logs/wazuh_realtime.log'             # wazuh_realtime_server.py:26

# SHOULD BE:
LOG_DIR=./logs
WAZUH_REALTIME_LOG=wazuh_realtime.log
```

## 🔢 BUSINESS LOGIC CONSTANTS (Should be Configurable)

### **Query & Search Limits**
```python
# CURRENT HARDCODED VALUES:
max_results=100                        # Multiple test files
max_results=5                          # Multiple test files  
k=3                                    # Search result limit
k=5                                    # Search result limit
k=10                                   # Search result limit
limit=100                              # Cache limit
limit=500                              # Cache limit
limit=1000                             # Cache limit

# SHOULD BE:
DEFAULT_MAX_RESULTS=100
TEST_MAX_RESULTS=5
SEARCH_TOP_K=5
CACHE_BUILD_LIMIT=1000
```

### **Text Processing Limits**
```python
# CURRENT HARDCODED VALUES:
[:1000]                                # Log truncation - wazuh_fastmcp_server.py:540
[:3000]                                # RAG content limit - telegram_security_bot.py:388
[:100]                                 # Preview length - Multiple files
[:2000]                                # Content truncation - test files

# SHOULD BE:
MAX_LOG_LENGTH=1000
MAX_RAG_CONTENT=3000
PREVIEW_LENGTH=100
MAX_CONTENT_LENGTH=2000
```

### **Time Windows**
```python
# CURRENT HARDCODED VALUES:
days_range=7                           # Multiple files
'-7 days'                              # SQL queries in multiple files
'-1 day'                               # SQL queries  
'-24 hours'                            # Time calculations

# SHOULD BE:
DEFAULT_DAYS_RANGE=7
DASHBOARD_DAYS_BACK=7
ALERT_WINDOW_HOURS=24
ANALYSIS_WINDOW_DAYS=7
```

### **Rule Level Thresholds**
```python
# CURRENT HARDCODED VALUES:
rule_level >= 6                        # Critical threshold - Multiple files
rule_level >= 7                        # High threshold - Multiple files
rule_level >= 8                        # Emergency threshold - Multiple files
'priority_levels': [6, 7]             # telegram_bot_config.py:49
'priority_levels': [3, 6, 7]          # telegram_bot_config.py:55

# SHOULD BE:
CRITICAL_RULE_LEVEL=6
HIGH_RULE_LEVEL=7
EMERGENCY_RULE_LEVEL=8
DAILY_PRIORITY_LEVELS=6,7
WEEKLY_PRIORITY_LEVELS=3,6,7
```

### **Agent & Status Thresholds**
```python
# CURRENT HARDCODED VALUES:
agent['count'] > 100                   # Active agent threshold - Multiple files
agent['alert_count'] > 100             # Active agent threshold

# SHOULD BE:
AGENT_ACTIVE_THRESHOLD=100
AGENT_ALERT_THRESHOLD=100
```

### **AI & Model Parameters**
```python
# CURRENT HARDCODED VALUES:
'max_tokens': 2000                     # config/telegram_bot_config.py:85
'temperature': 0.3                     # config/telegram_bot_config.py:86
max_tokens=500                         # test_sql_query.py:50

# SHOULD BE:
AI_MAX_TOKENS=2000
AI_TEMPERATURE=0.3
TEST_MAX_TOKENS=500
```

### **Report Configuration**
```python
# CURRENT HARDCODED VALUES:
'max_events': 50                       # Daily report - telegram_bot_config.py:52
'max_events': 100                      # 3-day report - telegram_bot_config.py:58
'max_events': 200                      # Weekly report - telegram_bot_config.py:64
'max_events': 500                      # Monthly report - telegram_bot_config.py:70

# SHOULD BE:
DAILY_MAX_EVENTS=50
THREE_DAY_MAX_EVENTS=100
WEEKLY_MAX_EVENTS=200
MONTHLY_MAX_EVENTS=500
```

### **PDF Configuration**
```python
# CURRENT HARDCODED VALUES:
'title_font_size': 24                  # telegram_bot_config.py:98
'header_font_size': 16                 # telegram_bot_config.py:99
'body_font_size': 12                   # telegram_bot_config.py:100
'margin': 72                           # telegram_bot_config.py:101

# SHOULD BE:
PDF_TITLE_FONT_SIZE=24
PDF_HEADER_FONT_SIZE=16
PDF_BODY_FONT_SIZE=12
PDF_MARGIN=72
```

### **Security Keywords & Patterns**
```python
# CURRENT HARDCODED VALUES:
'high_frequency_threshold': 10         # telegram_bot_config.py:108
'analysis_context_window': 7           # telegram_bot_config.py:109

# Arrays of keywords in telegram_bot_config.py:104-141
threat_keywords = ['failed', 'denied', 'blocked'...]
security_keywords = {...}

# SHOULD BE:
HIGH_FREQUENCY_THRESHOLD=10
ANALYSIS_CONTEXT_WINDOW_DAYS=7
THREAT_KEYWORDS_FILE=security_keywords.json
```

## 🔧 VERSION & PROJECT INFO
```python
# CURRENT VALUES:
__version__ = "1.0.0"                  # __init__.py:5
__author__ = "AI Assistant"            # Multiple files

# SHOULD BE:
PROJECT_VERSION=1.0.0
PROJECT_AUTHOR=AI Assistant
```

## 🎯 PRIORITY UNTUK ENVIRONMENT VARIABLES

### **Priority 1 - CRITICAL (Security)**
1. `FLASK_SECRET_KEY` - ✅ Already configured but needs strong default
2. `TELEGRAM_BOT_TOKEN` - ✅ Already configured
3. `WAZUH_PASSWORD` - ✅ Already configured but needs strong default

### **Priority 2 - HIGH (Application Breaking)**
4. `DATABASE_DIR` - ❌ Not configured, breaks app
5. `WAZUH_ARCHIVES_PATH` - ❌ Not configured, breaks Wazuh integration
6. `DOCKER_CONTAINER_NAME` - ❌ Not configured, breaks Docker integration
7. `DASHBOARD_HOST/PORT/DEBUG` - ❌ Not configured, hardcoded in dashboard_app.py

### **Priority 3 - MEDIUM (Feature Configuration)**  
8. `MAX_LOG_LENGTH` - ❌ Not configured, affects performance
9. `MAX_RAG_CONTENT` - ❌ Not configured, affects AI responses
10. `DEFAULT_DAYS_RANGE` - ❌ Not configured, affects query defaults
11. `CRITICAL_RULE_LEVEL` - ❌ Not configured, affects alerting

### **Priority 4 - LOW (Nice to Have)**
12. `PDF_*` settings - ❌ Not configured, affects report formatting
13. `AI_MAX_TOKENS` - ❌ Not configured, affects AI performance
14. Report limits and thresholds - ❌ Not configured, affects reporting

## 📊 SUMMARY STATISTICS

- **Environment Variables Already Configured**: 11 variables
- **Hardcoded Variables Need Env Vars**: 30+ variables
- **Business Logic Constants**: 40+ constants
- **Files Affected**: 20+ files
- **Most Critical Fix Needed**: Database paths (4 files)
- **Most Used Hardcoded Value**: `192.168.56.1:1234` (8+ files)

**TOTAL VARIABLES FOUND**: ~80+ variables across the entire codebase