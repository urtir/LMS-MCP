# 📊 ANALISIS KONFIGURASI HARDCODED - LMS MCP PROJECT
## HASIL SCAN KOMPREHENSIF SELURUH CODEBASE

## 🔴 CRITICAL - Security Hardcoded Values

### 1. **Flask Secret Key**
**File**: `src/webapp/webapp_chatbot.py:59`
```python
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this-in-production')
```

### 2. **Wazuh API Credentials** 
**File**: `src/api/wazuh_fastmcp_server.py:75-77`
```python
self.base_url = os.getenv("WAZUH_API_URL", "https://localhost:55000")
self.username = os.getenv("WAZUH_USERNAME", "wazuh-wui")
self.password = os.getenv("WAZUH_PASSWORD", "MyS3cr37P450r.*-")
```

### 3. **Telegram Bot Token**
**File**: `src/utils/telegram_config.py:14`
```python
self.BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
```

## 🟡 WARNING - Network Configuration

### 4. **LM Studio URLs** (8 Files!)
- `src/webapp/webapp_chatbot.py:44`: `'base_url': os.getenv('LM_STUDIO_BASE_URL', 'http://192.168.56.1:1234/v1')`
- `src/utils/telegram_config.py:19`: `'base_url': os.getenv('LM_STUDIO_BASE_URL', 'http://192.168.56.1:1234/v1')`  
- `src/api/wazuh_fastmcp_server.py:88`: `self.base_url = os.getenv('LM_STUDIO_BASE_URL', 'http://192.168.56.1:1234/v1')`
- `docs/DOKUMENTASI LM STUDIO DENGAN TOOLS.py:20`: `client = OpenAI(base_url="http://0.0.0.0:1234/v1", api_key="lm-studio")`
- `config/telegram_bot_config.py:82`: `'base_url': "http://192.168.56.1:1234/v1"`

### 5. **Flask Host & Port**
- `src/webapp/webapp_chatbot.py:51-52`: Default `127.0.0.1:5000`
- `src/webapp/dashboard_app.py:281`: **❌ HARDCODED!** `app.run(debug=True, host='0.0.0.0', port=5000)`

### 6. **Wazuh Archives Path**
- `src/api/wazuh_realtime_server.py:238`: `self.archives_path = "/var/ossec/logs/archives/archives.json"`
- `src/api/wazuh_realtime_server.py:448`: `print("Fetching data from: /var/ossec/logs/archives/archives.json")`

### 7. **Docker Container Name**
- `src/api/wazuh_realtime_server.py:237`: `self.container_name = "single-node-wazuh.manager-1"`

## 🟢 INFO - Database Paths

### 8. **Database Hardcoded Paths**
**❌ Bad Examples:**
- `src/telegram/telegram_security_bot.py:634`: `conn = sqlite3.connect('wazuh_archives.db')` 
- `config/telegram_bot_config.py:91-92`: `'wazuh_db': 'wazuh_archives.db', 'chat_db': 'chat_history.db'`
- `check_db.py:4`: `conn = sqlite3.connect('data/wazuh_archives.db')`

**✅ Good Examples (Dynamic):**
- `src/database/database.py:18`: Dynamic path calculation
- `src/database/wazuh_database_utils.py:24`: Dynamic path calculation

### 9. **Log File Paths**
- `src/api/wazuh_realtime_server.py:26`: `logging.FileHandler(str(Path(__file__).parent.parent.parent / 'logs' / 'wazuh_realtime.log'))`

## 🔵 DEBUG - Development Settings

### 10. **Debug Mode Hardcoded**
- `src/webapp/webapp_chatbot.py:861`: `debug=True`
- `src/webapp/dashboard_app.py:281`: `debug=True`

## 🟠 MAGIC NUMBERS - Business Logic Constants

### 11. **Timeout & Limits**
- `src/api/wazuh_fastmcp_server.py:540`: `log['full_log'][:1000]` - Log truncation
- `src/telegram/telegram_security_bot.py:388`: `rag_content[:3000]` - RAG content limit

### 12. **Pagination & Query Limits**
- `src/webapp/dashboard_app.py:108`: `'status': 'active' if agent['count'] > 100 else 'inactive'`
- Multiple files: `LIMIT 10`, `LIMIT 50`, `LIMIT 100` in SQL queries

### 13. **Time Windows**
- Multiple files: `'-7 days'`, `'-1 day'`, `'-24 hours'` in SQL
- `config/telegram_bot_config.py:110`: `'analysis_context_window': 7` # Days

### 14. **Rule Level Thresholds**
- Multiple files: Rule levels `>= 6`, `>= 7`, `>= 8` for criticality
- `config/telegram_bot_config.py:49`: `'priority_levels': [6, 7]`

### 15. **File Generation Names**
- `src/telegram/telegram_security_bot.py:233`: `filename = f"security_report_{report_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"`

## 🟣 ADVANCED CONFIGURATION

### 16. **AI Model Settings**
- `config/telegram_bot_config.py:85`: `'max_tokens': 2000, 'temperature': 0.3`
- `src/webapp/webapp_chatbot.py:46`: `'model': os.getenv('LM_STUDIO_MODEL', 'qwen/qwen3-1.7b')`

### 17. **PDF Configuration**
- `config/telegram_bot_config.py:96-102`: Font sizes, margins, page settings

### 18. **Security Keywords Arrays**
- `config/telegram_bot_config.py:104-109`: Hardcoded threat detection keywords
- `config/telegram_bot_config.py:124-141`: Security pattern arrays

## 📋 PRIORITAS PERBAIKAN

### Priority 1 - CRITICAL (Immediate Action Required)
1. **🔴 Fix Telegram bot hardcoded database path**: `telegram_security_bot.py:634`
2. **🔴 Fix dashboard_app.py hardcoded host/port**: Line 281
3. **🔴 Update default passwords/secrets**
4. **🔴 Add environment validation on startup**

### Priority 2 - HIGH (Next Sprint)
5. **🟡 Centralize all LM Studio URLs** (8 files affected)
6. **🟡 Make Wazuh paths configurable**
7. **🟡 Extract Docker container name to config**
8. **🟡 Fix remaining hardcoded database paths**

### Priority 3 - MEDIUM (Future Enhancement)
9. **🔵 Convert debug flags to env vars**
10. **🟠 Create constants file for magic numbers**
11. **🟠 Make AI model parameters configurable**
12. **🟠 Extract time windows to configuration**

### Priority 4 - LOW (Nice to Have)
13. **🟣 Make PDF settings configurable**
14. **🟣 Extract security keywords to external file**
15. **🟣 Add configuration validation & error handling**

## 🎯 FILES YANG PERLU DIPERBAIKI

### Immediate Fixes (Priority 1)
1. `src/telegram/telegram_security_bot.py` - Line 634
2. `src/webapp/dashboard_app.py` - Line 281  
3. `check_db.py` - Line 4
4. `config/telegram_bot_config.py` - Lines 91-92

### Major Refactoring (Priority 2)
1. `src/api/wazuh_realtime_server.py` - Multiple hardcoded paths
2. `docs/DOKUMENTASI LM STUDIO DENGAN TOOLS.py` - Hardcoded URL
3. All files with LM Studio URL defaults

## 💡 SOLUSI YANG DISARANKAN

### 1. Buat Configuration Manager Class
```python
class ConfigManager:
    def __init__(self):
        self.validate_required_env_vars()
        self.load_all_configs()
    
    def validate_required_env_vars(self):
        required = ['FLASK_SECRET_KEY', 'TELEGRAM_BOT_TOKEN', 'WAZUH_PASSWORD']
        missing = [var for var in required if not os.getenv(var)]
        if missing:
            raise EnvironmentError(f"Missing required env vars: {missing}")
```

### 2. Update .env Template
```bash
# ====== SECURITY (REQUIRED) ======
FLASK_SECRET_KEY=your-ultra-secure-random-secret-key-here
TELEGRAM_BOT_TOKEN=your-real-bot-token
WAZUH_PASSWORD=your-secure-wazuh-password

# ====== NETWORK CONFIGURATION ======
LM_STUDIO_BASE_URL=http://192.168.56.1:1234/v1
WAZUH_API_URL=https://localhost:55000
WAZUH_ARCHIVES_PATH=/var/ossec/logs/archives/archives.json

# ====== APPLICATION SETTINGS ======
FLASK_DEBUG=false
DATABASE_DIR=./data
DOCKER_CONTAINER_NAME=single-node-wazuh.manager-1

# ====== BUSINESS LOGIC ======
MAX_LOG_LENGTH=1000
MAX_RAG_CONTENT=3000
AGENT_ACTIVE_THRESHOLD=100
ANALYSIS_DAYS=7
CRITICAL_RULE_LEVEL=6
```

### 3. Immediate Hotfixes
```python
# telegram_security_bot.py - URGENT FIX
- conn = sqlite3.connect('wazuh_archives.db')
+ db_path = self.config.DATABASE_CONFIG['wazuh_db']
+ conn = sqlite3.connect(db_path)

# dashboard_app.py - URGENT FIX  
- app.run(debug=True, host='0.0.0.0', port=5000)
+ debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
+ host = os.getenv('FLASK_HOST', '127.0.0.1')
+ port = int(os.getenv('FLASK_PORT', '5000'))
+ app.run(debug=debug_mode, host=host, port=port)
```

## ⚠️ DAMPAK PERUBAHAN

### High Risk Changes
- Database path changes (butuh update semua koneksi)
- Network endpoint changes (bisa break integrations)
- Secret key changes (invalidate sessions)

### Medium Risk Changes
- Debug flag changes (affect development workflow)
- Magic number changes (bisa affect business logic)

### Low Risk Changes
- PDF settings, keywords, documentation

## 📈 STATISTIK FINDINGS

- **Total Files Affected**: 20+ files
- **Critical Issues**: 3 (security-related)
- **Network Config Issues**: 8+ files  
- **Database Path Issues**: 5+ files
- **Magic Numbers**: 15+ instances
- **Debug Flags**: 2 instances

**CONCLUSION**: Project memiliki 20+ konfigurasi hardcoded yang tersebar di berbagai file. Priority tertinggi adalah fix 4 file dengan masalah critical/high risk, terutama database paths dan network configurations.